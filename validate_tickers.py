#!/usr/bin/env python3
"""Valide contre Yahoo Finance les tickers déclarés dans themes.py.

Pourquoi ce script existe : les symboles des thèmes ont été établis hors ligne
(l'environnement de développement n'a pas accès à Yahoo). Un symbole faux ou une
place mal servie ne se voit qu'à l'exécution — et se traduirait en production par
un thème amputé, publié en silence. On valide donc AVANT d'élargir l'univers.

Contrôles par ticker :
  - history(period="max") non vide, et profondeur suffisante (5 ans requis)
  - devise renvoyée par Yahoo, comparée à celle que detect_currency() déduit
    du suffixe : un désaccord est une erreur de conversion en puissance
  - secteur exploitable (sinon le titre échappe à la règle de concentration)
  - capitalisation > 25 Md$ (critère d'inclusion public du projet)
  - présence d'un objectif de cours consensus

Usage : python validate_tickers.py [--all]
        (par défaut : seulement les tickers ABSENTS de l'univers actuel)

        python validate_tickers.py --tickers COHR,CSCO,ASX,6146.T
        (liste explicite — sert à éprouver des CANDIDATS avant de les inscrire
        dans themes.py, ce qui est l'ordre correct : on ne déclare un ticker
        qu'une fois qu'on sait qu'il existe et qu'il passe les filtres)
"""
import json
import sys
import time
import re
from datetime import datetime, timezone

import yfinance as yf

import themes
from portfolio_agent import detect_currency

SEUIL_CAP_USD = 25e9
ANNEES_MIN = 5

# Ordres de grandeur attendus par devise — un prix hors bornes trahit une
# erreur d'unité (le piège des pence GBp, ×100, a déjà frappé ce projet).
BORNES_PRIX = {
    "USD": (1, 5000), "EUR": (1, 5000), "GBP": (0.5, 500),
    "CHF": (1, 5000), "DKK": (5, 5000), "SEK": (5, 5000), "NOK": (5, 5000),
    "JPY": (100, 100000), "KRW": (1000, 2000000),
}


def univers_actuel():
    src = open("screener.py").read()
    bloc = re.search(r"^UNIVERS = \[(.*?)^\]", src, re.S | re.M).group(1)
    return set(re.findall(r'"([^"]+)"', bloc))


def valide(ticker):
    r = {"ticker": ticker, "ok": False, "erreurs": [], "avertissements": []}
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="max")
        if hist is None or hist.empty:
            r["erreurs"].append("history(max) vide — symbole probablement invalide")
            return r
        close = hist["Close"].squeeze().dropna()
        if close.empty:
            r["erreurs"].append("aucune clôture valide")
            return r

        jours = (close.index[-1] - close.index[0]).days
        r["annees_historique"] = round(jours / 365.25, 1)
        r["dernier_cours"] = round(float(close.iloc[-1]), 2)
        r["derniere_date"] = str(close.index[-1].date())
        if jours < ANNEES_MIN * 365:
            r["erreurs"].append(f"historique {r['annees_historique']} ans < {ANNEES_MIN} ans requis")

        # Devise : Yahoo vs déduction par suffixe — le désaccord est critique
        try:
            devise_yahoo = getattr(tk.fast_info, "currency", "") or ""
        except Exception:
            devise_yahoo = ""
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            r["avertissements"].append("info() indisponible")
        devise_yahoo = devise_yahoo or info.get("currency", "") or ""
        devise_deduite = detect_currency(ticker, info.get("exchange", ""))
        r["devise_yahoo"] = devise_yahoo
        r["devise_deduite"] = devise_deduite
        r["exchange"] = info.get("exchange", "")
        # GBp (pence) est un cas connu et déjà traité en aval : GBp ⇒ GBP après /100
        equivalent = devise_yahoo == devise_deduite or (devise_yahoo == "GBp" and devise_deduite == "GBP")
        if devise_yahoo and not equivalent:
            r["erreurs"].append(
                f"DÉSACCORD DEVISE : Yahoo dit {devise_yahoo}, detect_currency déduit "
                f"{devise_deduite} — conversion EUR fausse garantie")

        # Ordre de grandeur du prix, dans la devise réellement renvoyée
        ref = "GBP" if devise_yahoo == "GBp" else (devise_yahoo or devise_deduite)
        prix_ref = r["dernier_cours"] / 100 if devise_yahoo == "GBp" else r["dernier_cours"]
        if ref in BORNES_PRIX:
            lo, hi = BORNES_PRIX[ref]
            if not (lo <= prix_ref <= hi):
                r["avertissements"].append(
                    f"prix {prix_ref} hors bornes attendues pour {ref} ({lo}-{hi}) — vérifier l'unité")

        r["secteur"] = info.get("sector", "") or ""
        if not r["secteur"]:
            r["erreurs"].append("secteur absent — le titre échapperait à la règle de concentration")

        cap = info.get("marketCap")
        r["cap_musd"] = round(cap / 1e6) if cap else None
        if cap:
            # Capitalisation renvoyée en devise locale : conversion grossière
            # suffisante pour un contrôle de seuil.
            approx = {"JPY": 150, "KRW": 1350, "GBp": 79, "GBP": 0.79,
                      "EUR": 0.92, "CHF": 0.88, "DKK": 6.9, "SEK": 10.5, "NOK": 10.8}
            cap_usd = cap / approx.get(devise_yahoo, 1.0)
            r["cap_usd_approx_md"] = round(cap_usd / 1e9, 1)
            if cap_usd < SEUIL_CAP_USD:
                r["avertissements"].append(
                    f"capitalisation ~{r['cap_usd_approx_md']} Md$ < seuil 25 Md$ du projet")
        else:
            r["avertissements"].append("capitalisation absente")

        r["nom"] = info.get("longName") or info.get("shortName") or ""
        r["target_mean"] = info.get("targetMeanPrice")
        if not r["target_mean"]:
            r["avertissements"].append("pas d'objectif consensus (colonne vide sur la fiche)")

        r["ok"] = not r["erreurs"]
    except Exception as e:
        r["erreurs"].append(f"exception : {type(e).__name__}: {e}")
    return r


def main():
    tout = "--all" in sys.argv
    explicites = ""
    for i, arg in enumerate(sys.argv):
        if arg == "--tickers" and i + 1 < len(sys.argv):
            explicites = sys.argv[i + 1]
        elif arg.startswith("--tickers="):
            explicites = arg.split("=", 1)[1]

    declares = themes.univers_thematique()
    actuel = univers_actuel()
    if explicites:
        # Mode CANDIDATS : on éprouve une liste avant de l'inscrire dans
        # themes.py. C'est l'ordre correct — un ticker ne se déclare qu'une fois
        # qu'on sait qu'il existe chez Yahoo et qu'il passe les filtres.
        cibles = sorted({t.strip().upper() for t in explicites.split(",") if t.strip()})
        deja = sorted(set(cibles) & actuel)
        if deja:
            print(f"Déjà dans l'univers (validés quand même) : {', '.join(deja)}")
    else:
        cibles = declares if tout else sorted(set(declares) - actuel)

    print(f"Univers actuel : {len(actuel)} tickers")
    print(f"Déclarés par les thèmes : {len(declares)}")
    print(f"À valider : {len(cibles)}\n", flush=True)

    resultats = []
    for i, t in enumerate(cibles, 1):
        r = valide(t)
        resultats.append(r)
        etat = "OK  " if r["ok"] else "ÉCHEC"
        detail = ""
        if r.get("annees_historique"):
            detail = (f"{r['annees_historique']:>5} ans · {r.get('devise_yahoo','?'):>4} · "
                      f"{str(r.get('secteur',''))[:22]:22} · ~{r.get('cap_usd_approx_md','?')} Md$")
        print(f"[{i:3d}/{len(cibles)}] {etat} {t:14s} {detail}", flush=True)
        for e in r["erreurs"]:
            print(f"            ✗ {e}", flush=True)
        for a in r["avertissements"]:
            print(f"            ⚠ {a}", flush=True)
        time.sleep(0.4)

    ok = [r for r in resultats if r["ok"]]
    ko = [r for r in resultats if not r["ok"]]
    warn = [r for r in ok if r["avertissements"]]

    rapport = {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "univers_actuel": len(actuel),
        "declares_par_themes": len(declares),
        "valides": len(ok),
        "echecs": len(ko),
        "resultats": resultats,
    }
    with open("validation_tickers.json", "w") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1, allow_nan=False)

    print(f"\n{'='*70}")
    print(f"VALIDÉS : {len(ok)}/{len(cibles)}   ÉCHECS : {len(ko)}   AVERTISSEMENTS : {len(warn)}")
    if ko:
        print("\nÀ RETIRER des thèmes (ou à corriger) :")
        for r in ko:
            print(f"  {r['ticker']:14s} {' ; '.join(r['erreurs'])}")
    if warn:
        print("\nÀ examiner (validés mais suspects) :")
        for r in warn:
            print(f"  {r['ticker']:14s} {' ; '.join(r['avertissements'])}")

    # Couverture par thème après retrait des échecs — c'est le chiffre qui décide
    invalides = {r["ticker"] for r in ko}
    print("\nCouverture par thème après retrait des échecs :")
    for th in themes.THEMES_CURES:
        restants = [t for t in th["tickers"] if t not in invalides]
        taux = len(restants) / len(th["tickers"]) if th["tickers"] else 0
        flag = "  ⚠ THÈME DÉGRADÉ" if taux < 0.7 else ""
        print(f"  {th['id']:16s} {len(restants):3d}/{len(th['tickers']):3d}  ({taux*100:3.0f}%){flag}")


if __name__ == "__main__":
    main()
