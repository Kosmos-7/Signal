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
from portfolio_agent import (
    get_eur_usd_rate, get_eur_gbp_rate, maj_position,
    calc_max_drawdown, save_json_atomic,
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

    # ── Recalcule capital et performance globale
    val_positions   = sum(p.get("valeur_actuelle", 0) for p in positions)
    capital_actuel  = round(val_positions + liquidites, 2)
    performance     = round((capital_actuel - capital_initial) / capital_initial * 100, 2)

    # ── Met à jour les poids
    for pos in positions:
        pos["poids"] = round(pos["valeur_actuelle"] / capital_actuel * 100, 1) if capital_actuel > 0 else 0

    # ── Benchmarks YTD (rerécupère pour fraîcheur)
    annee = date.today().year
    debut = f"{annee}-01-01"
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
    today_entry = {
        "date":            today,
        "perf":            performance,
        "capital":         capital_actuel,
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
    import config
    cash_post_liq             = float(liquidites)
    frais_si_liquidation      = 0.0
    pfu_latent_si_liquidation = 0.0
    pertes_si_liquidation     = 0.0
    for pos in positions:
        brut = pos.get("valeur_actuelle", 0)
        base = pos.get("montant_investi", brut)
        r = config.apply_sell_cost_and_tax(brut, base)
        cash_post_liq             += r["cash_recupere_eur"]
        frais_si_liquidation      += r["frais_vente_eur"]
        pfu_latent_si_liquidation += r["impot_pfu_eur"]
        pertes_si_liquidation     += r["perte_reportable_eur"]
    capital_post_liquidation     = round(cash_post_liq, 2)
    performance_post_liquidation = round((capital_post_liquidation - capital_initial) / capital_initial * 100, 2)

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
    portfolio["frais_si_liquidation"]         = round(frais_si_liquidation, 2)
    portfolio["pfu_latent_si_liquidation"]    = round(pfu_latent_si_liquidation, 2)
    portfolio["pertes_si_liquidation"]        = round(pertes_si_liquidation, 2)
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
