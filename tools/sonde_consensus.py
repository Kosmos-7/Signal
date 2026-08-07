#!/usr/bin/env python3
"""Relève BRUT ce que Yahoo publie comme estimations d'analystes.

POURQUOI CETTE SONDE EXISTE. Nos projections s'arrêtent à deux exercices puis
deviennent notre propre arithmétique, parce que `revenue_estimate` et
`earnings_estimate` ne portent que `0y` et `+1y`. Un service concurrent affiche
cinq exercices avec un profil IRRÉGULIER (CoreWeave : +60 %, +38 %, +45 %) —
donc de vraies estimations, pas une formule. Yahoo expose par ailleurs
`growth_estimates`, dont l'index contient un `+5y` que nous n'avons JAMAIS lu.

CE QUE CETTE SONDE FAIT, ET CE QU'ELLE NE FAIT PAS. Elle lit et recopie. Elle
n'interprète pas, ne convertit pas, ne branche rien. C'est délibéré : deux
suppositions d'unité ont déjà coûté cher sur ce projet — les dividendes inclus
dans les cours (`auto_adjust`), et la devise du consensus de chiffre d'affaires
(comptable) opposée à celle du bénéfice (cotation). Les deux avaient l'air
évidentes. La règle qui en sort : PUBLIER BRUT, LIRE, PUIS DÉCIDER.

Le rapport donne donc, par ticker et sans retouche : l'index et les colonnes de
chaque table, et les valeurs telles quelles. Les questions auxquelles il doit
répondre avant tout branchement —

  · `+5y` existe-t-il vraiment, et sur combien de sociétés ?
  · est-ce un POURCENTAGE (25.4) ou une FRACTION (0.254) ?
  · est-ce une croissance de BÉNÉFICE ou de chiffre d'affaires ?
  · est-il cohérent avec le `+1y` de la même table, dont nous savons déjà
    reconstituer l'équivalent depuis `earnings_estimate` ?

Aucune de ces réponses ne se devine : elles se lisent.

Le proxy de l'environnement de développement bloque Yahoo ; cette sonde tourne
donc en intégration continue, où le réseau est ouvert.

Usage : python3 tools/sonde_consensus.py [--tickers A,B,C] [--limite N]
"""
import argparse
import json
import sys

RAPPORT = "sonde_consensus.json"

# Douze sociétés choisies pour COUVRIR LES CAS, pas pour faire nombre : deux
# hypercroissances déficitaires (le cas qui nous a manqué), un fondeur, des
# compounders, un cyclique, deux non-US et un titre en devise non-USD — si le
# champ se comporte différemment selon la place ou le signe, ça se verra ici.
DEFAUT = ["NBIS", "CRWV", "TSM", "GOOGL", "ADBE", "NVDA",
          "MU", "ASML.AS", "SAP.DE", "8035.T", "BKNG", "CEG"]

TABLES = ("growth_estimates", "revenue_estimate", "earnings_estimate")


def _table_brute(obj):
    """Recopie une table pandas en structure JSON, sans rien convertir.

    On garde l'index ET les colonnes : c'est l'index qui dira si `+5y` existe,
    et les colonnes qui diront si la valeur lue est une moyenne, un nombre
    d'analystes ou autre chose. Un `repr` du type est joint parce qu'une
    fraction et un pourcentage se ressemblent, mais pas un float et une chaîne.
    """
    if obj is None:
        return {"present": False}
    try:
        index = [str(i) for i in obj.index]
        cols = [str(c) for c in obj.columns]
    except Exception as e:
        return {"present": True, "illisible": f"{type(e).__name__}: {e}"[:200]}
    lignes = {}
    for i in obj.index:
        ligne = {}
        for c in obj.columns:
            try:
                v = obj.loc[i, c]
            except Exception:
                continue
            # NaN != NaN : le seul test qui ne dépend d'aucun import.
            if v != v:
                ligne[str(c)] = None
            elif isinstance(v, (int, float)):
                ligne[str(c)] = float(v)
            else:
                ligne[str(c)] = str(v)
        lignes[str(i)] = ligne
    return {"present": True, "index": index, "colonnes": cols, "valeurs": lignes}


def sonder(tickers):
    import yfinance as yf
    out = {}
    for t in tickers:
        fiche = {}
        try:
            d = yf.Ticker(t)
        except Exception as e:
            out[t] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
            continue
        for nom in TABLES:
            try:
                fiche[nom] = _table_brute(getattr(d, nom, None))
            except Exception as e:
                fiche[nom] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        # Deux repères pour juger la cohérence des taux sans quitter le rapport :
        # la devise comptable et la devise de cotation, dont la divergence nous
        # a déjà piégés une fois sur le consensus de chiffre d'affaires.
        try:
            info = d.info or {}
            fiche["reperes"] = {
                "devise_comptable": info.get("financialCurrency"),
                "devise_cotation": info.get("currency"),
                "croissance_ca_yahoo": info.get("revenueGrowth"),
                "croissance_bpa_yahoo": info.get("earningsGrowth"),
            }
        except Exception as e:
            fiche["reperes"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        out[t] = fiche
        print(f"  {t:<10} " + " · ".join(
            f"{n}={'oui' if fiche.get(n, {}).get('present') else 'non'}" for n in TABLES))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default="", help="liste séparée par des virgules")
    ap.add_argument("--limite", type=int, default=0, help="0 = tous")
    a = ap.parse_args()
    tickers = [x.strip() for x in a.tickers.split(",") if x.strip()] or DEFAUT
    if a.limite:
        tickers = tickers[:a.limite]
    print(f"Sonde du consensus Yahoo sur {len(tickers)} sociétés :")
    res = sonder(tickers)
    # Un résumé en tête du fichier : combien de sociétés portent réellement un
    # `+5y`, et sous quel nom exact. C'est LA question qui décide de la suite.
    porteurs = sorted(t for t, f in res.items()
                      if any(k.lower().replace(" ", "") in ("+5y", "5y")
                             for k in (f.get("growth_estimates") or {}).get("index", []) or []))
    rapport = {
        "sondes": len(tickers),
        "avec_5y": porteurs,
        "index_growth_estimates_observes": sorted({
            tuple((f.get("growth_estimates") or {}).get("index") or [])
            for f in res.values()}, key=len),
        "detail": res,
    }
    # Les tuples ne sont pas sérialisables tels quels en clés lisibles.
    rapport["index_growth_estimates_observes"] = [
        list(x) for x in rapport["index_growth_estimates_observes"]]
    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    print(f"\n→ {RAPPORT}")
    print(f"   sociétés portant un '+5y' : {len(porteurs)}/{len(tickers)} {porteurs}")
    for idx in rapport["index_growth_estimates_observes"]:
        print(f"   index observé : {idx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
