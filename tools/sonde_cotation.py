#!/usr/bin/env python3
"""Compare un ADR à sa LIGNE D'ORIGINE, champ par champ, sans rien décider.

POURQUOI. Six fiches publient leurs comptes dans une devise et cotent dans une
autre, et le PER historique y est vide en entier — TSMC : onze exercices, aucun
multiple. La piste retenue par le propriétaire est de remplacer l'ADR par la
ligne d'origine : le cours et le bénéfice reviennent alors dans la même monnaie
et le multiple redevient calculable, sans taux de change ni rapport d'ADR.

L'idée est juste. Ce qu'elle coûte ne se devine pas : une ligne locale peut
très bien ne PAS porter les estimations d'analystes qui alimentent nos
projections, notre PER prévisionnel et notre objectif de cours. Remplacer un
ticker qui a le consensus par un ticker qui ne l'a pas, ce serait échanger un
trou contre un autre.

Cette sonde ne branche rien et ne convertit rien : elle lit les deux lignes
côte à côte et recopie. Même règle que sonde_consensus.py, née des deux erreurs
d'unité supposée du projet : PUBLIER BRUT, LIRE, PUIS DÉCIDER.

Ce qu'il faut lire dans le rapport, dans cet ordre :

  1. `devises.identiques` — si la ligne locale ne résout pas le décalage, tout
     le reste est sans objet (c'est le cas d'ABB et de Vestas, déjà sur leur
     place d'origine et pourtant décalés : leurs COMPTES sont en monnaie
     étrangère, ce n'est pas un problème d'ADR).
  2. `estimations` — bénéfice et chiffre d'affaires attendus. Sans elles, plus
     de projections, plus de PER prévisionnel.
  3. `objectif` — cours cible et nombre d'analystes.
  4. `historique` — profondeur de la série de cours ; une ligne locale récente
     ne permettrait pas de remonter aussi loin que l'ADR.
  5. `rapport_adr` — actions en circulation de chaque ligne. Leur quotient EST
     le rapport de l'ADR ; il se mesure, il ne se suppose pas.

Le proxy de développement bloque Yahoo : cette sonde tourne en intégration
continue, où le réseau est ouvert.

Usage : python3 tools/sonde_cotation.py [--paires ADR=LOCAL,ADR=LOCAL]
"""
import argparse
import json
import sys

RAPPORT = "sonde_cotation.json"

# Les six fiches décalées, avec la ligne d'origine à tester. ABB et Vestas sont
# dans la liste SANS ligne de remplacement : elles y figurent pour que le
# rapport montre noir sur blanc que le remplacement ne les concerne pas — leurs
# comptes sont publiés en USD et en EUR alors qu'elles cotent à Zurich et à
# Copenhague, et aucune place ne les cote dans leur monnaie comptable.
DEFAUT = {
    "TSM": "2330.TW",      # TSMC — comptes TWD, ADR en USD
    "ASX": "3711.TW",      # ASE Technology — comptes TWD, ADR en USD
    "RACE": "RACE.MI",     # Ferrari — comptes EUR, ligne NYSE en USD
    "CCJ": "CCO.TO",       # Cameco — comptes CAD, ligne NYSE en USD
    "ABBN.SW": "ABB",      # ABB — comptes USD ; la ligne de New York est la
                           # seule cotée dans la monnaie des comptes
    "VWS.CO": "",          # Vestas — comptes EUR, aucune cotation en EUR
}


def _num(v):
    """Rend un nombre lisible en JSON, ou None. Aucune conversion d'unité."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _estim(data, nom):
    """Présence et valeurs brutes d'une table d'estimations, sans retouche."""
    try:
        t = getattr(data, nom)
    except Exception as e:                                       # noqa: BLE001
        return {"present": False, "erreur": f"{type(e).__name__}: {e}"[:120]}
    if t is None or not hasattr(t, "index"):
        return {"present": False}
    try:
        idx = [str(i) for i in t.index]
        col = "avg" if "avg" in getattr(t, "columns", []) else None
        vals = {k: _num(t.loc[k, col]) for k in idx if col} if col else {}
        return {"present": True, "index": idx,
                "colonnes": [str(c) for c in getattr(t, "columns", [])],
                "avg": vals}
    except Exception as e:                                       # noqa: BLE001
        return {"present": True, "erreur": f"{type(e).__name__}: {e}"[:120]}


def sonder_ligne(ticker):
    import yfinance as yf
    out = {"ticker": ticker}
    try:
        d = yf.Ticker(ticker)
        info = d.info or {}
    except Exception as e:                                       # noqa: BLE001
        return {"ticker": ticker, "erreur": f"{type(e).__name__}: {e}"[:160]}
    out["devise_cotation"] = info.get("currency")
    out["devise_comptable"] = info.get("financialCurrency")
    out["memes_devises"] = (info.get("currency") is not None
                            and info.get("currency") == info.get("financialCurrency"))
    out["objectif"] = {"cours_cible": _num(info.get("targetMeanPrice")),
                       "analystes": info.get("numberOfAnalystOpinions")}
    out["actions"] = _num(info.get("sharesOutstanding"))
    out["capitalisation"] = _num(info.get("marketCap"))
    out["bpa_ttm"] = _num(info.get("trailingEps"))
    out["per_courant"] = _num(info.get("trailingPE"))
    out["per_prevu"] = _num(info.get("forwardPE"))
    out["estimations"] = {n: _estim(d, n)
                          for n in ("earnings_estimate", "revenue_estimate")}
    try:
        h = d.history(period="max", auto_adjust=False)
        out["historique"] = {"points": int(len(h)),
                             "debut": str(h.index[0].date()) if len(h) else None,
                             "fin": str(h.index[-1].date()) if len(h) else None}
    except Exception as e:                                       # noqa: BLE001
        out["historique"] = {"erreur": f"{type(e).__name__}: {e}"[:120]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paires", default="",
                    help="ADR=LOCAL,ADR=LOCAL (vide = les six fiches décalées)")
    a = ap.parse_args()
    if a.paires.strip():
        paires = {}
        for bloc in a.paires.split(","):
            if "=" in bloc:
                k, v = bloc.split("=", 1)
                paires[k.strip()] = v.strip()
    else:
        paires = DEFAUT

    rapport = {"paires": {}}
    for adr, local in paires.items():
        print(f"— {adr} vs {local or '(aucune ligne équivalente)'}", flush=True)
        bloc = {"cote": sonder_ligne(adr)}
        bloc["origine"] = sonder_ligne(local) if local else None
        # LA question, isolée en tête de chaque bloc pour ne pas avoir à
        # relire tout le reste : la ligne d'origine résout-elle le décalage,
        # et à quel prix en données d'analystes ?
        o = bloc["origine"]
        bloc["verdict"] = {
            "resout_le_decalage": bool(o and o.get("memes_devises")),
            "garde_le_benefice_attendu": bool(
                o and (o.get("estimations") or {}).get("earnings_estimate", {}).get("present")),
            "garde_le_ca_attendu": bool(
                o and (o.get("estimations") or {}).get("revenue_estimate", {}).get("present")),
            "garde_l_objectif": bool(o and (o.get("objectif") or {}).get("cours_cible")),
            "rapport_adr": (round(bloc["cote"].get("actions") and o and o.get("actions")
                                  and o["actions"] / bloc["cote"]["actions"], 3)
                            if (o and o.get("actions") and bloc["cote"].get("actions"))
                            else None),
        }
        rapport["paires"][adr] = bloc

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    print(f"\n→ {RAPPORT}")
    for adr, b in rapport["paires"].items():
        v = b["verdict"]
        print(f"  {adr:9} décalage résolu={v['resout_le_decalage']!s:5} "
              f"bénéfice={v['garde_le_benefice_attendu']!s:5} "
              f"CA={v['garde_le_ca_attendu']!s:5} "
              f"objectif={v['garde_l_objectif']!s:5} rapport={v['rapport_adr']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
