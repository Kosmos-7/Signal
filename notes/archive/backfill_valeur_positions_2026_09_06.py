"""
⚠️  SCRIPT ARCHIVÉ (2026-09-06) — NE PLUS EXÉCUTER.

Les 95 points d'historique portent leur `valeur_positions` depuis ce passage, et
les deux écrivains de portfolio.json l'écrivent désormais à chaque run. Un
second passage réécrirait par reconstitution des valeurs devenues MESURÉES.

backfill_valeur_positions_2026_09_06.py — huit mois de trésorerie à rebours.

LE BESOIN. Le graphe « Performance depuis le lancement » doit pouvoir tracer le
montant du portefeuille HORS LIQUIDITÉS. `performance_history` ne portait que
`capital` (positions + cash) : la valeur des lignes seule n'y était nulle part,
et aucun fichier du dépôt ne la conservait.

LA MÉTHODE. Le cash ne bouge QUE sur un ordre. On part donc des liquidités
d'aujourd'hui, MESURÉES, et on remonte le journal :

    liquidités(t) = liquidités(aujourd'hui) − Σ { flux des ordres de date > t }
    valeur_positions(t) = capital(t) − liquidités(t)

Ce n'est pas un modèle, c'est de l'arithmétique sur le registre du site.

LES DEUX TROUS DU JOURNAL, COMBLÉS PAR DES VALEURS MESURÉES AILLEURS.
  · Le versement du 03/08/2026 n'a jamais reçu d'entrée APPORT (celui du 05/05
    en a une). Montant et date sont dans `injections`.
  · L'achat SAP.DE d'amorçage n'est pas journalisé. Sa base est déductible au
    centime de sa vente du 15/02 : brut_net_frais − plus_value = 1 984,00 €.

L'ORDRE CORRECTION N'ENTRE PAS DANS LE CALCUL. Les 374,10 € régularisés le
06/09 étaient déjà sur le compte à chaque date passée ; seul le livre ne les
montrait pas. Les retrancher du passé reproduirait exactement l'erreur qu'on
venait de corriger.

CE QUI VALIDE LE RÉSULTAT. Le dernier point retombe AU CENTIME sur les deux
grandeurs mesurées du jour : liquidités 5 120,38 € et positions 30 010,78 €.
Une chaîne de 48 flux sur huit mois qui atterrit exactement sur sa cible n'est
pas une coïncidence. C'est le seul point d'ancrage disponible, et il tient.

CE QUI NE TIENT PAS, ET QUI EST BORNÉ. Le livre d'amorçage est incohérent avec
lui-même : le 02/01/2026, le journal porte 9 006,74 € d'achats plus les
1 984,00 € de SAP.DE, soit 10 984 € engagés pour un capital de 10 000 €. La
reconstitution donne donc −530,82 € de liquidités ce jour-là. Le cash ne peut
JAMAIS être négatif — c'est une règle que le moteur applique partout ailleurs,
au point de refuser un achat plutôt que de l'enfreindre. On la fait respecter
ici aussi : ce seul point est borné à 0 € de liquidités, donc positions =
capital. L'incohérence est antérieure à tout ce qui est vérifiable et n'est pas
inventée ici, elle est seulement empêchée de sortir en négatif.

TRAÇABILITÉ. Chaque point reconstitué porte `valeur_positions_source:
"reconstituee"`. Les points écrits par un run ne portent pas ce champ : la
distinction entre mesuré et reconstitué reste lisible dans le fichier, pour
toujours.

    python notes/archive/backfill_valeur_positions_2026_09_06.py
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RACINE)

from portfolio_agent import save_json_atomic                        # noqa: E402

CHEMIN = os.path.join(RACINE, "portfolio.json")
# APPORT et VENTE créditent, ACHAT débite. CORRECTION est délibérément absent.
SENS = {"ACHAT": -1, "VENTE": +1, "APPORT": +1}


def main():
    with open(CHEMIN, encoding="utf-8") as f:
        pf = json.load(f)

    historique = pf["performance_history"]
    if any("valeur_positions" in h for h in historique[:-1]):
        raise SystemExit("❌ L'historique porte déjà la décomposition — abandon.")

    flux = [(o["date"], SENS[o["type"]] * o["montant"])
            for o in pf["ordres"] if o["type"] in SENS]

    # Trou 1 : le versement du 03/08, jamais journalisé.
    journalises = {(o["date"], o["montant"]) for o in pf["ordres"] if o["type"] == "APPORT"}
    for inj in pf["injections"]:
        if (inj["date"], inj["montant"]) not in journalises:
            flux.append((inj["date"], float(inj["montant"])))
            print(f"  versement non journalisé réintégré : {inj['date']} {inj['montant']:+.2f} €")

    # Trou 2 : l'achat SAP.DE d'amorçage, base déduite de sa vente.
    vente_sap = next((o for o in pf["ordres"]
                      if o["ticker"] == "SAP.DE" and o["type"] == "VENTE"), None)
    if vente_sap and not any(o["ticker"] == "SAP.DE" and o["type"] == "ACHAT"
                             for o in pf["ordres"]):
        base = round(vente_sap["montant_brut_eur"] - vente_sap["frais_vente_eur"]
                     - vente_sap["plus_value_eur"], 2)
        flux.append((historique[0]["date"], -base))
        print(f"  achat SAP.DE d'amorçage réintégré : {base:.2f} € (base déduite de sa vente)")

    liq_mesuree = pf["liquidites"]

    def liquidites_a(date):
        return round(liq_mesuree - sum(m for d, m in flux if d > date), 2)

    bornes = 0
    for h in historique:
        liq = liquidites_a(h["date"])
        if liq < 0:
            # Le cash ne peut jamais être négatif : règle du moteur, appliquée ici.
            print(f"  ⚠️  {h['date']} : liquidités reconstituées {liq:.2f} € bornées à 0 "
                  f"(livre d'amorçage incohérent de {-liq:.2f} €)")
            liq, bornes = 0.0, bornes + 1
        h["liquidites"] = liq
        h["valeur_positions"] = round(h["capital"] - liq, 2)
        h["valeur_positions_source"] = "reconstituee"

    # Le dernier point est MESURÉ, pas reconstitué : il sert d'ancrage et doit
    # retomber exactement sur les grandeurs du jour.
    dernier = historique[-1]
    attendu_liq = pf["liquidites"]
    attendu_pos = round(pf["capital_actuel"] - pf["liquidites"], 2)
    assert dernier["liquidites"] == attendu_liq, (dernier["liquidites"], attendu_liq)
    assert dernier["valeur_positions"] == attendu_pos, (dernier["valeur_positions"], attendu_pos)
    dernier.pop("valeur_positions_source")

    negatifs = [h["date"] for h in historique if h["valeur_positions"] < 0]
    assert not negatifs, negatifs

    pf["valeur_positions"] = attendu_pos
    save_json_atomic(CHEMIN, pf)

    vals = [h["valeur_positions"] for h in historique]
    print(f"\n✅ {len(historique)} points décomposés ({bornes} borné(s) à cash nul)")
    print(f"   ancrage au {dernier['date']} : liquidités {attendu_liq:.2f} € · "
          f"positions {attendu_pos:.2f} € — exact")
    print(f"   valeur des positions : de {min(vals):.2f} € à {max(vals):.2f} €")


if __name__ == "__main__":
    main()
