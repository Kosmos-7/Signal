"""
⚠️  SCRIPT ARCHIVÉ (2026-09-06) — NE PLUS EXÉCUTER.

Un second run repasserait un ordre CORRECTION sur un livre déjà bouclé et
rouvrirait l'écart qu'il vient de fermer. `portfolio_agent.ecart_tresorerie`
vaut 0,00 € depuis cette régularisation, et les deux écrivains de
portfolio.json refusent désormais de publier tant qu'il n'y est pas.

regularisation_tresorerie_2026_09_06.py — le cash rattrape les bases fiscales.

CE QUI S'EST PASSÉ. Deux migrations de change (portfolio_agent.maj_position,
retirées le même jour) ont réécrit `montant_investi` sur sept lignes achetées
avant le 05/05/2026, quand la devise native était encore enregistrée comme si
c'étaient des euros. Les bases ont été réparées. Le CASH DÉBITÉ À L'ACHAT, lui,
n'a jamais bougé.

    NVDA, 02/01/2026 : 20 titres à 115 $. Le journal débite 2 301,72 « € »
    pour 2 300 $. La migration ramène la base à 1 981,90 €. Personne ne rend
    les 319,82 € au compte espèces.

Six lignes USD (NVDA, JPM, V, BLK, AMZN, AVGO) sous-évaluaient le cash de
776,15 € ; LSEG.L, migrée dans l'autre sens, le surévaluait de 377,68 €.

CE QUE ÇA PRODUISAIT. L'identité comptable du modèle

    liquidités + Σ bases ouvertes = versé + résultat réalisé

était fausse de 374,10 €. Le dashboard ne la vérifiait pas : il DÉDUISAIT le
résultat réalisé par soustraction (écart au capital versé moins plus-value
latente). L'écart tombait donc dedans sans bruit — le site annonçait
« −1 311,87 € de résultat réalisé sur les ventes passées » quand les douze
ventes du journal totalisaient −937,77 €.

CE QUE FAIT CE SCRIPT. Il crédite les 374,10 € au compte espèces par un ordre
CORRECTION daté, visible dans le journal du site, et recalcule tout ce qui en
dépend. Il ne touche à aucun prix : `updated_at` reste au 04/09/2026, date des
cours. Le dernier point d'historique est RESTATÉ à cette même date — les
374,10 € étaient déjà sur le compte ce jour-là, seul le livre ne les montrait
pas ; c'est une correction d'écriture, pas un mouvement de marché.

CE QU'IL NE FAIT PAS. Les taux de change historiques du 02/01 et du 30/04/2026
ne sont pas récupérables (Yahoo hors d'atteinte depuis le runner). Le montant
retenu aligne donc le cash sur les bases DÉJÀ PUBLIÉES, au taux que les
migrations ont elles-mêmes employé (EUR/USD 1,1605). Deux artefacts d'unité
subsistent dans le journal et ne sont pas réécrits, faute de taux :
  · ADI, vendue le 05/05/2026 — achetée en dollars comptés comme des euros,
    revendue en euros convertis : la perte de 62,20 € publiée est presque
    entièrement un écart d'unité (vraie perte ≈ −3,40 €) ;
  · MSFT, aller-retour 02/01 → 30/04/2026 entièrement en dollars comptés comme
    des euros : la perte de 4,25 € vaut ≈ 3,66 € réels.
Ces deux écarts rendent le résultat réalisé du journal LÉGÈREMENT trop négatif,
donc la régularisation ci-dessous plutôt conservatrice.

    python notes/archive/regularisation_tresorerie_2026_09_06.py
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RACINE)

import config                                                        # noqa: E402
from portfolio_agent import (                                        # noqa: E402
    agregats_derives, calc_max_drawdown, ecart_tresorerie,
    resultat_realise_net, save_json_atomic, sync_plus_value_latente,
    _perf_twr,
)

DATE_CORRECTION = "2026-09-06"
CHEMIN = os.path.join(RACINE, "portfolio.json")


def main():
    with open(CHEMIN, encoding="utf-8") as f:
        pf = json.load(f)

    if any(o.get("type") == "CORRECTION" for o in pf.get("ordres", [])):
        raise SystemExit("❌ Une régularisation est déjà passée — abandon.")

    positions   = pf["positions"]
    verse       = pf["capital_initial"]
    liq_avant   = pf["liquidites"]
    realise     = resultat_realise_net(pf["ordres"])
    bases       = round(sum(p["montant_investi"] for p in positions), 2)

    ecart = ecart_tresorerie(verse, liq_avant, positions, realise)
    delta = round(-ecart, 2)
    print(f"versé {verse:.2f} · réalisé {realise:.2f} · bases {bases:.2f} · "
          f"liquidités {liq_avant:.2f}")
    print(f"écart de trésorerie : {ecart:+.2f} € → correction {delta:+.2f} €")
    if delta == 0:
        raise SystemExit("Le livre boucle déjà — rien à faire.")

    liq = round(liq_avant + delta, 2)

    pf["ordres"].insert(0, {
        "date":     DATE_CORRECTION,
        "type":     "CORRECTION",
        "ticker":   "—",
        "nom":      "Régularisation de trésorerie",
        "qte":      0,
        "prix":     0,
        "montant":  abs(delta),
        "sens":     "credit" if delta > 0 else "debit",
        "raison": (
            f"Le compte espèces rattrape les bases fiscales. Deux migrations de "
            f"change ont réparé le montant investi de sept lignes achetées avant "
            f"le 05/05/2026, quand la devise native était encore enregistrée comme "
            f"si c'étaient des euros, sans jamais corriger le cash débité à "
            f"l'achat. Six lignes en dollars (NVDA, JPM, V, BLK, AMZN, AVGO) "
            f"sous-évaluaient les liquidités de 776,15 €, LSEG.L les surévaluait "
            f"de 377,68 €. L'identité liquidités + bases ouvertes = capital versé "
            f"+ résultat réalisé était donc fausse de {abs(ecart):.2f} €, et le "
            f"site publiait cet écart comme une perte sur les ventes passées. "
            f"Liquidités portées de {liq_avant:.2f} € à {liq:.2f} €. Aucun titre "
            f"n'a changé de main, aucun cours n'a bougé : c'est une correction "
            f"d'écriture, datée du jour où elle a été passée."),
        "source":   "Régularisation comptable",
    })

    pf["liquidites"] = liq
    sync_plus_value_latente(positions)
    agr = agregats_derives(positions, liq, pf["total_pertes_reportables"])

    cap = agr["capital_actuel"]
    pf["capital_actuel"]  = cap
    pf["performance"]     = _perf_twr(pf, cap)
    pf["performance_brute"] = _perf_twr(
        pf, cap + pf["total_frais_payes"] + pf["total_impots_payes"])
    pf["pct_liquidites"]  = round(liq / cap * 100, 1)
    for p in positions:
        p["poids"] = round(p["valeur_actuelle"] / cap * 100, 1)
    pf["positions"] = sorted(positions, key=lambda x: -x["performance"])

    pf["capital_post_liquidation"]     = agr["capital_post_liquidation"]
    pf["performance_post_liquidation"] = _perf_twr(pf, agr["capital_post_liquidation"])
    pf["frais_si_liquidation"]         = agr["frais_si_liquidation"]
    pf["pfu_latent_si_liquidation"]    = agr["pfu_latent_si_liquidation"]
    pf["pertes_si_liquidation"]        = agr["pertes_si_liquidation"]
    pf["plus_value_nette_si_liquidation"] = agr["plus_value_nette_si_liquidation"]
    pf["pertes_imputees_si_liquidation"] = agr["pertes_imputees_si_liquidation"]

    pf["total_investi"]             = agr["total_investi"]
    pf["plus_value_latente_totale"] = agr["plus_value_latente_totale"]
    pf["total_resultat_realise"]    = realise
    pf["pfu_rate"]                  = config.PFU_RATE
    pf["nb_positives"] = len([p for p in positions if p["performance"] > 0])
    pf["nb_negatives"] = len([p for p in positions if p["performance"] < 0])
    pf["nb_neutres"]   = len([p for p in positions if p["performance"] == 0.0])
    pf["vs_benchmark"] = round(pf["performance"] - pf["benchmark_msci"], 2)

    # Le dernier point d'historique porte la valeur du 04/09 : c'est CE point qui
    # se restate, pas un nouveau qui s'ajoute. Ajouter un point au 06/09 daterait
    # de samedi des cours de vendredi.
    dernier = pf["performance_history"][-1]
    assert dernier["date"] == pf["updated_at"], (dernier["date"], pf["updated_at"])
    dernier["capital"] = cap
    dernier["perf"]    = pf["performance"]
    dernier["note"]    = (f"Régularisation de trésorerie {delta:+.2f} € "
                          f"(bases de change réparées sans le cash)")
    pf["max_drawdown"] = calc_max_drawdown(pf["performance_history"])

    pf["ecart_tresorerie"] = ecart_tresorerie(
        verse, liq, positions, pf["total_resultat_realise"])
    assert abs(pf["ecart_tresorerie"]) < 0.02, pf["ecart_tresorerie"]

    save_json_atomic(CHEMIN, pf)
    print(f"✅ liquidités {liq_avant:.2f} → {liq:.2f} €")
    print(f"   capital     {cap:.2f} € · performance {pf['performance']:+.2f} %")
    print(f"   post-liq    {pf['capital_post_liquidation']:.2f} € "
          f"({pf['performance_post_liquidation']:+.2f} %)")
    print(f"   écart de trésorerie résiduel : {pf['ecart_tresorerie']:+.2f} €")


if __name__ == "__main__":
    main()
