"""
update_prices.py — Refresh quotidien des prix portfolio (M-V après close US).

NE FAIT PAS :
  - Pas de scoring (screener pas relancé)
  - Pas de décisions Claude (zéro appel API Anthropic)
  - Pas d'achat/vente
  - Pas de modification de positions ouvertes ni de liquidités

FAIT UNIQUEMENT :
  - Récupère les prix actuels des positions ouvertes (yfinance)
  - Met à jour valeur_actuelle, performance, prix_actuel par position
  - Recalcule capital_actuel et performance globale
  - Met à jour le benchmark MSCI World et l'écart au benchmark
  - Upsert l'entrée du jour dans performance_history
  - Recalcule max_drawdown
  - Persiste dans portfolio.json

But : le site reflète la performance la plus récente chaque jour ouvré, sans
toucher à la méthodologie hebdomadaire (décisions Claude, watchlist, scoring).

Usage : python update_prices.py
"""

import json
import yfinance as yf
from datetime import date, datetime

# Réutilise les fonctions du portfolio_agent pour cohérence stricte
import config
from portfolio_agent import (
    get_eur_usd_rate, get_eur_gbp_rate, maj_position,
    calc_max_drawdown, save_json_atomic,
    # Les grandeurs dérivées sont calculées par l'agent ET par ce script. Toute
    # formule recopiée finit par diverger : performance_brute l'a fait pendant
    # quatre jours en septembre 2026 parce que seul l'agent la rafraîchissait.
    sync_plus_value_latente, agregats_derives, ecart_tresorerie,
    resultat_realise_net,
    # `_perf_twr` est importée malgré son souligné : c'est la SEULE formule de
    # performance du projet, et la partager vaut mieux que respecter une marque
    # de privauté en la recopiant. Un test vérifie que les deux modules tiennent
    # bien le même objet.
    _perf_twr,
    TICKER_CAC40, TICKER_MSCI, CAPITAL_INITIAL_DEF,
)


def main():
    today = str(date.today())

    # ── Charge portfolio
    try:
        with open("portfolio.json", encoding="utf-8") as f:
            portfolio = json.load(f)
    except FileNotFoundError:
        print("❌ portfolio.json introuvable — abandon")
        return
    except json.JSONDecodeError as e:
        print(f"❌ portfolio.json invalide : {e} — abandon")
        return

    capital_initial = portfolio.get("capital_initial", CAPITAL_INITIAL_DEF)
    positions       = portfolio.get("positions", [])
    liquidites      = portfolio.get("liquidites", capital_initial)

    if not positions:
        print("ℹ️  Aucune position ouverte — refresh inutile, sortie")
        return

    print(f"💱 Refresh quotidien des prix — {today}")
    print(f"   {len(positions)} position(s) ouverte(s)")

    # ── Taux de change
    eur_usd = get_eur_usd_rate()
    eur_gbp = get_eur_gbp_rate()
    print(f"   EUR/USD : {eur_usd} · EUR/GBP : {eur_gbp}")

    # ── Refresh des prix par position (réutilise maj_position : EUR cohérent)
    success = 0
    for pos in positions:
        if maj_position(pos, eur_usd, eur_gbp):
            success += 1
        else:
            print(f"   ⚠️  {pos['ticker']} : prix indisponible (gardé valeur précédente)")

    print(f"   ✓ {success}/{len(positions)} prix mis à jour")
    if success == 0:
        # Échec bruyant : bumper updated_at sans AUCUNE donnée fraîche maquillerait
        # une panne de feed en "mise à jour réussie".
        raise SystemExit(f"❌ 0/{len(positions)} prix récupérés — abandon sans écrire")

    # `plus_value_latente_eur` est dérivée de valeur_actuelle et montant_investi :
    # on la redérive après le refresh plutôt que de faire confiance au stocké,
    # que maj_position laisse intact quand un prix n'est pas récupérable.
    sync_plus_value_latente(positions)

    # ── Recalcule capital et performance globale
    agr             = agregats_derives(positions, liquidites,
                                       portfolio.get("total_pertes_reportables", 0.0))
    capital_actuel  = agr["capital_actuel"]
    # Performance ponderee par le temps : les injections de capital n'y entrent
    # pas (decision proprietaire du 03/08/2026, methode dans config.py).
    #
    # UNE SEULE FORMULE POUR LES DEUX ÉCRIVAINS. portfolio.json a deux auteurs —
    # l'agent le lundi, ce script chaque soir ouvré — et tous deux publient le
    # champ `performance`. La reconstitution du capital de départ
    # (`capital_initial` moins la somme des versements) était écrite TROIS fois :
    # une dans _perf_twr, deux ici. Trois copies d'une règle sont trois règles
    # qui divergent, et celle-ci porte le nombre le plus important du site — le
    # même qui a affiché 34,73 % contre 32,94 % pendant que le registre des
    # versements manquait. On appelle donc la fonction de l'agent au lieu de
    # refaire son calcul.
    performance     = _perf_twr(portfolio, capital_actuel)

    # ── Met à jour les poids
    for pos in positions:
        pos["poids"] = round(pos["valeur_actuelle"] / capital_actuel * 100, 1) if capital_actuel > 0 else 0

    # ── Benchmarks YTD (rerécupère pour fraîcheur)
    # Ancré au lancement (cf. config.PORTFOLIO_DEBUT) et non au 1er janvier de
    # l'année courante : au changement d'année le benchmark serait reparti de
    # zéro pendant que la performance continue depuis la création.
    debut = config.PORTFOLIO_DEBUT
    bench_cac, bench_msci = portfolio.get("benchmark_cac40", 0), portfolio.get("benchmark_msci", 0)
    for label, ticker in [("cac40", TICKER_CAC40), ("msci", TICKER_MSCI)]:
        try:
            hist = yf.Ticker(ticker).history(start=debut)["Close"].dropna()
            if len(hist) >= 2:
                ytd = round((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0] * 100, 2)
                if label == "cac40":
                    bench_cac = ytd
                else:
                    bench_msci = ytd
        except Exception as e:
            print(f"   ⚠️  Benchmark {label} : {e} — valeur précédente conservée")

    # ── VIX quotidien (Phase 2 — info contextuelle uniquement, n'influence pas le scoring)
    # Affiché sur le dashboard sous forme de pill colorée. Refresh quotidien pour que la
    # valeur affichée reflète la réalité du marché du jour (sinon stale jusqu'à 6j entre
    # 2 runs hebdo).
    vix_value      = portfolio.get("last_known_vix")
    vix_source     = portfolio.get("last_known_vix_source", "cache")
    try:
        vix_hist = yf.Ticker("^VIX").history(period="5d")["Close"].dropna()
        if not vix_hist.empty:
            vix_value  = round(float(vix_hist.iloc[-1]), 2)
            vix_source = "live"
            print(f"   VIX (live) : {vix_value}")
    except Exception as e:
        print(f"   ⚠️  ^VIX : {e} — valeur précédente conservée ({vix_value})")

    vs_benchmark = round(performance - bench_msci, 2)

    # ── Trie les positions par performance EUR (cohérent avec portfolio_agent)
    positions_sorted = sorted(positions, key=lambda x: -x.get("performance", 0))

    # ── Upsert performance_history pour aujourd'hui
    history = portfolio.get("performance_history", [])
    # Le point porte sa décomposition, pas seulement son total : `capital` seul ne
    # permettait pas de tracer la valeur des lignes hors liquidités.
    today_entry = {
        "date":            today,
        "perf":            performance,
        "capital":         capital_actuel,
        "valeur_positions": agr["valeur_positions"],
        "liquidites":      round(liquidites, 2),
        "benchmark_cac40": bench_cac,
        "benchmark_msci":  bench_msci,
    }
    idx_today = next((i for i, h in enumerate(history) if h.get("date") == today), None)
    if idx_today is not None:
        # Préserve la note (injection de capital, etc.) si elle existait
        if "note" in history[idx_today]:
            today_entry["note"] = history[idx_today]["note"]
        history[idx_today] = today_entry
    else:
        history.append(today_entry)
    history = history[-260:]  # cap à 260 entrées (~1 an de jours OUVRÉS — upsert quotidien depuis daily-prices)

    max_dd = calc_max_drawdown(history)

    # ── Capital post-liquidation (cash réel si tout vendu aujourd'hui — recalculé chaque jour)
    # Voir portfolio_agent.main() pour la logique détaillée.
    capital_post_liquidation     = agr["capital_post_liquidation"]
    performance_post_liquidation = _perf_twr(portfolio, capital_post_liquidation)

    # ── Le livre boucle-t-il ? liquidités + Σ bases = versé + réalisé ────────
    # Le compteur cumulé fait foi : `ordres` est plafonné, un invariant assis
    # dessus casserait le jour où le journal se tronque.
    total_resultat_realise = portfolio.get(
        "total_resultat_realise", resultat_realise_net(portfolio.get("ordres", [])))
    ecart = ecart_tresorerie(capital_initial, liquidites, positions, total_resultat_realise)
    if abs(ecart) > 1.0:
        raise SystemExit(
            f"❌ Trésorerie incohérente de {ecart:+.2f}€ — abandon SANS écrire.\n"
            f"   liquidités {liquidites:.2f} + bases {agr['total_investi']:.2f} "
            f"≠ versé {capital_initial:.2f} + réalisé {total_resultat_realise:.2f}")

    # ── Met à jour le portfolio (sans toucher aux champs hebdo)
    portfolio["updated_at"]      = today
    portfolio["capital_actuel"]  = capital_actuel
    portfolio["performance"]     = performance
    portfolio["benchmark_cac40"] = bench_cac
    portfolio["benchmark_msci"]  = bench_msci
    portfolio["vs_benchmark"]    = vs_benchmark
    portfolio["positions"]       = positions_sorted
    portfolio["pct_liquidites"]  = round(liquidites / capital_actuel * 100, 1) if capital_actuel > 0 else 0
    portfolio["nb_positives"]    = len([p for p in positions if p.get("performance", 0) > 0])
    portfolio["nb_negatives"]    = len([p for p in positions if p.get("performance", 0) < 0])
    portfolio["nb_neutres"]      = len([p for p in positions if p.get("performance", 0) == 0.0])
    portfolio["performance_history"] = history
    # Post-liquidation virtuel (mis à jour quotidiennement car positions fluctuent)
    portfolio["capital_post_liquidation"]     = capital_post_liquidation
    portfolio["performance_post_liquidation"] = performance_post_liquidation
    portfolio["frais_si_liquidation"]         = agr["frais_si_liquidation"]
    portfolio["pfu_latent_si_liquidation"]    = agr["pfu_latent_si_liquidation"]
    portfolio["pertes_si_liquidation"]        = agr["pertes_si_liquidation"]
    portfolio["plus_value_nette_si_liquidation"] = agr["plus_value_nette_si_liquidation"]
    portfolio["pertes_imputees_si_liquidation"] = agr["pertes_imputees_si_liquidation"]
    # Grandeurs que le site LIT au lieu de les déduire par soustraction
    portfolio["total_investi"]             = agr["total_investi"]
    portfolio["valeur_positions"]          = agr["valeur_positions"]
    portfolio["plus_value_latente_totale"] = agr["plus_value_latente_totale"]
    portfolio["total_resultat_realise"]    = round(total_resultat_realise, 2)
    portfolio["ecart_tresorerie"]          = ecart
    portfolio["pfu_rate"]                  = config.PFU_RATE
    # performance_brute n'était rafraîchie que par le run hebdomadaire : publiée
    # à 36,35 % le 04/09 quand sa propre formule en donnait 35,71 sur le capital
    # du jour. Un chiffre à deux auteurs a besoin de deux mises à jour.
    portfolio["performance_brute"] = _perf_twr(
        portfolio,
        capital_actuel + portfolio.get("total_frais_payes", 0.0)
                       + portfolio.get("total_impots_payes", 0.0))
    # VIX (quotidien) — info contextuelle, n'influence pas le scoring (cf config.VIX_DAMPENER_ENABLED)
    if vix_value is not None:
        portfolio["last_known_vix"]            = vix_value
        portfolio["last_known_vix_source"]     = vix_source
        portfolio["last_known_vix_updated_at"] = today
    portfolio["max_drawdown"]    = max_dd
    # Note : on ne touche PAS à : week, ordres, biais_detectes, regles_actives,
    # analyse_claude, macro_news, nb_positions (= len(positions), inchangé)

    # ── Persiste (atomique + strict : NaN → échec bruyant du job, cf. incident 2026-06-02)
    save_json_atomic("portfolio.json", portfolio)

    print(f"\n✓ portfolio.json refreshé")
    print(f"  Capital m2m  : {capital_actuel:.0f}€ ({performance:+.2f}% YTD)")
    print(f"  Capital post-liq : {capital_post_liquidation:.0f}€ ({performance_post_liquidation:+.2f}%)")
    print(f"  vs MSCI   : {vs_benchmark:+.2f}pp (MSCI {bench_msci:+.2f}%)")
    print(f"  Max DD    : {max_dd:+.2f}%")
    if vix_value is not None:
        print(f"  VIX       : {vix_value} ({vix_source})")


if __name__ == "__main__":
    main()
