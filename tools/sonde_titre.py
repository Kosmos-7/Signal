#!/usr/bin/env python3
"""Score un titre HORS UNIVERS avec le scoring du projet. Ne décide rien.

POURQUOI. Le screener note les ~190 titres de l'univers, et le skill
portfolio-analyst prescrit d'importer `score_ticker` pour analyser un titre
« de façon strictement consistante avec ce qui pilote le portefeuille ». Mais
l'environnement de développement n'atteint pas Yahoo : demander une analyse sur
un titre absent de l'univers laissait le choix entre ne rien rendre et écrire des
chiffres de mémoire. La seconde option est exactement ce que la doctrine du
projet interdit. Cette sonde ferme le trou : elle fait tourner LE scorer du
dépôt, sur un runner qui a le réseau, et recopie ce qu'il rend.

CE QU'ELLE N'EST PAS. Elle ne modifie aucune donnée publiée, n'inscrit le titre
dans aucun thème et ne rend aucun verdict. Elle produit la matière d'une décision
qui, elle, se prend ailleurs — et à la main.

LES DEUX PREMIÈRES COUCHES DU SKILL, DANS UN SEUL PASSAGE :
  · couche 1 — `screener.score_ticker` : score /100 et breakdown complet
    (technique, fondamentaux, régression, signal_dynamics_warning) ;
  · couche 2 — `yfinance.info` et les états financiers : ROCE et EV/EBITDA, que
    le scoring n'utilise pas mais que la méthode demande de lire pour situer le
    titre dans la matrice qualité × valorisation, plus la date du dernier
    trimestriel et la trajectoire trimestrielle récente.

LA DATE DU DERNIER TRIMESTRIEL EST LA PIÈCE MAÎTRESSE, et c'est écrit dans le
pré-flight du skill : le scoring s'appuie sur l'ANNUEL, qui retarde de 60 à 120
jours. La sonde publie donc `mostRecentQuarter` et les quatre derniers trimestres
de chiffre d'affaires et de résultat, pour qu'une divergence entre la croissance
annuelle et la dynamique récente se VOIE au lieu de se deviner. Le skill cite
précisément ce cas sur Reply — screener +0,6 % de CA contre +8 % en réalité.

Le proxy de développement bloque Yahoo : cette sonde tourne en intégration
continue, où le réseau est ouvert.

Usage : python3 tools/sonde_titre.py --tickers REY.MI[,AUTRE.MI]
"""
import argparse
import json
import os
import sys

# LA RACINE DU DÉPÔT SUR LE CHEMIN — sans quoi `import screener` échoue.
# Lancée par `python tools/sonde_titre.py`, l'interpréteur met `tools/` en tête
# du chemin, pas la racine : le premier run a rendu « ModuleNotFoundError: No
# module named 'screener' » après avoir installé toutes les dépendances. Les
# autres outils de tools/ n'ajoutaient que leur PROPRE dossier, parce qu'aucun
# n'importait le cœur du projet — cette sonde est la première, et le motif
# n'existait donc nulle part à recopier.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAPPORT = "sonde_titre.json"


def _num(v):
    """Rend un nombre lisible en JSON, ou None. Aucune conversion d'unité."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _ligne(table, noms):
    """Première ligne trouvée parmi `noms` dans un tableau financier yfinance.

    Les libellés varient d'un émetteur et d'une version de la bibliothèque à
    l'autre : on essaie les alias plutôt que d'en supposer un."""
    if table is None or not hasattr(table, "index"):
        return None
    for n in noms:
        if n in table.index:
            try:
                s = table.loc[n].dropna()
                if len(s):
                    return s
            except Exception:                                    # noqa: BLE001
                continue
    return None


def _roce(d):
    """EBIT / (actif total − passif courant), la formule du module methodology.

    Rend aussi ses TROIS termes : un ratio dont on ne peut pas voir les
    composants ne se vérifie pas, et c'est un ratio de qualité qu'on va citer."""
    try:
        fin, bil = d.financials, d.balance_sheet
    except Exception as e:                                       # noqa: BLE001
        return {"erreur": f"{type(e).__name__}: {e}"[:120]}
    ebit = _ligne(fin, ["EBIT", "Operating Income", "OperatingIncome"])
    act = _ligne(bil, ["Total Assets", "TotalAssets"])
    pas = _ligne(bil, ["Current Liabilities", "Total Current Liabilities",
                       "TotalCurrentLiabilities"])
    if ebit is None or act is None or pas is None:
        return {"present": False,
                "manquant": [n for n, v in (("ebit", ebit), ("actif", act),
                                            ("passif_courant", pas)) if v is None]}
    e, a, p = _num(ebit.iloc[0]), _num(act.iloc[0]), _num(pas.iloc[0])
    if not e or not a or p is None or (a - p) <= 0:
        return {"present": False, "motif": "capital employé nul ou négatif"}
    return {"present": True, "ebit": e, "actif_total": a, "passif_courant": p,
            "capital_employe": a - p, "roce_pct": round(e / (a - p) * 100, 1),
            "exercice": str(ebit.index[0])[:10]}


def _trimestres(d):
    """Quatre derniers trimestres de CA et de résultat net. Bruts, non retraités."""
    try:
        q = d.quarterly_financials
    except Exception as e:                                       # noqa: BLE001
        return {"erreur": f"{type(e).__name__}: {e}"[:120]}
    ca = _ligne(q, ["Total Revenue", "TotalRevenue", "Operating Revenue"])
    rn = _ligne(q, ["Net Income", "NetIncome",
                    "Net Income Common Stockholders"])
    if ca is None:
        return {"present": False}
    out = []
    for i in range(min(4, len(ca))):
        out.append({"fin": str(ca.index[i])[:10], "ca": _num(ca.iloc[i]),
                    "rn": _num(rn.iloc[i]) if rn is not None and i < len(rn) else None})
    return {"present": True, "trimestres": out}


def sonder(ticker):
    """Couches 1 et 2 pour un titre. Ne calcule aucun verdict."""
    import yfinance as yf
    import screener

    out = {"ticker": ticker}
    # ── Couche 1 : LE scorer du dépôt, celui qui pilote le portefeuille
    try:
        r = screener.score_ticker(ticker)
    except Exception as e:                                       # noqa: BLE001
        r = None
        out["score_erreur"] = f"{type(e).__name__}: {e}"[:200]
    if r:
        out["nom"] = r.get("name")
        out["secteur"] = r.get("sector")
        out["market"] = r.get("market")
        out["score"] = r.get("score")
        out["badge"] = r.get("badge")
        out["justification"] = r.get("justification")
        out["breakdown"] = r.get("breakdown")
    else:
        out.setdefault("score_erreur", "score_ticker n'a rien rendu "
                                       "(historique trop court ? ticker inconnu ?)")

    # ── Couche 2 : ce que le scoring n'utilise pas mais que la méthode lit
    try:
        d = yf.Ticker(ticker)
        info = d.info or {}
    except Exception as e:                                       # noqa: BLE001
        out["info_erreur"] = f"{type(e).__name__}: {e}"[:160]
        return out
    out["devise_cotation"] = info.get("currency")
    out["devise_comptable"] = info.get("financialCurrency")
    out["capitalisation"] = _num(info.get("marketCap"))
    out["ev_ebitda"] = _num(info.get("enterpriseToEbitda"))
    out["per_courant"] = _num(info.get("trailingPE"))
    out["per_prevu"] = _num(info.get("forwardPE"))
    out["dernier_trimestriel"] = info.get("mostRecentQuarter")
    out["objectif_moyen"] = _num(info.get("targetMeanPrice"))
    out["analystes"] = info.get("numberOfAnalystOpinions")
    out["reco_moyenne"] = _num(info.get("recommendationMean"))
    out["roce"] = _roce(d)
    out["trimestriels"] = _trimestres(d)
    try:
        rec = d.recommendations
        if rec is not None and len(rec):
            out["recommandations"] = json.loads(rec.head(4).to_json(orient="records"))
    except Exception as e:                                       # noqa: BLE001
        out["recommandations"] = {"erreur": f"{type(e).__name__}: {e}"[:120]}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tickers", default="", help="TICKER,TICKER (obligatoire)")
    a = p.parse_args()
    cibles = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    if not cibles:
        print("❌ aucun ticker : --tickers REY.MI")
        return 2

    titres = []
    for t in cibles:
        print(f"· {t}")
        r = sonder(t)
        titres.append(r)
        b = r.get("breakdown") or {}
        if r.get("score") is not None:
            print(f"    score {r['score']}/100 · {r.get('secteur')} · "
                  f"{r.get('devise_cotation')} · cross {b.get('cross_regime')} "
                  f"({b.get('cross_days_ago')}j) · z={b.get('regression_z')} "
                  f"(fenêtre {b.get('regression_window_years')}a)")
            roce = r.get("roce") or {}
            print(f"    ROCE {roce.get('roce_pct')}% · EV/EBITDA {r.get('ev_ebitda')} "
                  f"· dernier trimestriel {r.get('dernier_trimestriel')}")
            if b.get("signal_dynamics_warning"):
                print(f"    ⚠ {b['signal_dynamics_warning']}")
        else:
            print(f"    ❌ {r.get('score_erreur')}")

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump({"_mode_d_emploi":
                   "Rapport BRUT, aucun verdict. `breakdown` est le même objet que "
                   "celui qui pilote les fiches du site. Lire dans cet ordre : "
                   "(1) dernier_trimestriel — si <90 jours, la croissance annuelle "
                   "du breakdown retarde et `trimestriels` dit ce qu'elle ne dit pas ; "
                   "(2) breakdown.signal_dynamics_warning avant toute lecture du "
                   "cross ; (3) regression_window_years — sous 7 ans le z-score ne "
                   "vaut pas comme critère de setup B ; (4) roce et ev_ebitda pour "
                   "situer dans la matrice qualité × valorisation.",
                   "titres": titres}, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {RAPPORT} — {len(titres)} titre(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
