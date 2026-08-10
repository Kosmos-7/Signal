#!/usr/bin/env python3
"""Demande à la source ce qu'elle rend vraiment d'une capitalisation. Ne décide rien.

POURQUOI. Cinq fiches (Allianz, Micron, Safran, Siemens, Western Digital)
publient leur marge de flux disponible mais pas son rendement : le rendement
demande une capitalisation, et le résumé du fournisseur n'en rend pas pour
elles. Un premier repli a déjà été posé le 09/08 — capitalisation = cours ×
actions en circulation, « ce n'est pas une estimation, c'est la définition ».
Le screener a tourné deux fois depuis, et les cinq trous sont toujours là : le
repli ne se déclenche donc pas, ce qui veut dire que le nombre d'actions manque
AUSSI. En poser un deuxième au jugé serait une troisième supposition.

Cette sonde ne branche rien et ne convertit rien : elle lit et recopie. Même
règle que sonde_cotation.py et sonde_consensus.py, née des erreurs d'unité
supposée du projet : PUBLIER BRUT, LIRE, PUIS DÉCIDER.

CE QU'ELLE DISTINGUE, ET QUI EST LE CŒUR DU SUJET : un champ ABSENT du
dictionnaire n'est pas un champ PRÉSENT À NULL. Le premier dit « je ne sers pas
cette donnée pour ce titre », le second « je la sers et elle est vide ». Les
deux se réparent différemment, et le résumé du fournisseur ne les distingue pas
à la lecture naïve : `info.get(x)` rend None dans les deux cas. Le rapport porte
donc `present` à côté de chaque valeur.

ELLE INTERROGE TROIS CHEMINS DIFFÉRENTS de la même bibliothèque, parce qu'ils
ne tapent pas le même service : le résumé (`info`), la voie rapide
(`fast_info`) et la série d'actions en circulation (`get_shares_full`). Un
champ vide sur l'un peut être servi par l'autre — c'est précisément ce qu'il
faut savoir avant de choisir un repli.

LES CIBLES SE DÉRIVENT DES FICHES PUBLIÉES, elles ne sont pas écrites ici. Une
liste de tickers recopiée à la main vieillit en silence : le jour où la source
se rétablit, elle continue de désigner des titres guéris, et le jour où un
sixième titre tombe, elle l'ignore. La sonde lit charts/ et prend les fiches qui
publient une marge de flux sans son rendement. Elle ajoute des TÉMOINS — des
fiches qui, elles, publient le rendement, sur les mêmes places de cotation :
sans eux, un rapport tout vide ne dirait pas si la source est muette pour ces
titres-là ou pour tout le monde.

Le proxy de développement bloque Yahoo : cette sonde tourne en intégration
continue, où le réseau est ouvert.

Usage : python3 tools/sonde_capitalisation.py [--cibles TICKER,TICKER] [--temoins N]
"""
import argparse
import glob
import json
import os
import sys

RAPPORT = "sonde_capitalisation.json"
CHARTS = "charts"

# BAE Systems est écartée des cibles et c'est ÉCRIT ailleurs aussi : elle cote
# en pence quand ses comptes sont en livres, et le fournisseur mélange les deux
# unités. Son rendement est un trou VOULU, pas un trou subi ; l'inclure ferait
# chercher une panne là où il y a une décision.
UNITE_AMBIGUE = {"BA.L"}

# Les champs du résumé qui portent, de près ou de loin, de quoi reconstituer une
# capitalisation. On les lit tous : c'est le rapport qui dira lesquels existent.
CHAMPS_INFO = (
    "marketCap", "sharesOutstanding", "impliedSharesOutstanding", "floatShares",
    "currentPrice", "regularMarketPrice", "previousClose",
    "bookValue", "priceToBook", "freeCashflow", "totalRevenue",
    "currency", "financialCurrency", "quoteType", "exchange",
)


def _num(v):
    """Rend un nombre lisible en JSON, ou None. Aucune conversion d'unité."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _champ(info, nom):
    """Présence ET valeur. `absent` et `présent à null` ne se réparent pas pareil."""
    if nom not in info:
        return {"present": False, "valeur": None}
    v = info[nom]
    if isinstance(v, str):
        return {"present": True, "valeur": v}
    return {"present": True, "valeur": _num(v)}


def cibles_et_temoins(dossier=CHARTS, n_temoins=2):
    """Dérive les cibles des fiches publiées. Rend (cibles, témoins).

    CIBLE : marge de flux publiée, rendement absent — le défaut lui-même.
    TÉMOIN : rendement publié, sur la MÊME place de cotation qu'une cible. Le
    suffixe du ticker fait office de place (« .DE », « .PA », « » pour les
    lignes américaines) : c'est la seule chose qui distingue ces marchés dans
    un nom de fichier, et elle suffit à répondre à « la source est-elle muette
    pour ce titre ou pour cette place ? »."""
    avec, sans = {}, []
    for chemin in sorted(glob.glob(os.path.join(dossier, "*.json"))):
        ticker = os.path.basename(chemin)[:-len(".json")]
        try:
            with open(chemin, encoding="utf-8") as f:
                b = (json.load(f) or {}).get("breakdown") or {}
        except (OSError, ValueError):
            continue
        marge, rdt = b.get("fcf_margin_pct"), b.get("fcf_yield_pct")
        place = ticker.split(".")[1] if "." in ticker else ""
        if marge is not None and rdt is None and ticker not in UNITE_AMBIGUE:
            sans.append((ticker, place))
        elif rdt is not None:
            avec.setdefault(place, []).append(ticker)

    cibles = [t for t, _ in sans]
    temoins, pris = [], {}
    for place in dict.fromkeys(place for _, place in sans):     # places, sans doublon
        for t in avec.get(place, []):
            if pris.get(place, 0) >= n_temoins:
                break
            temoins.append(t)
            pris[place] = pris.get(place, 0) + 1
    return cibles, temoins


def sonder(ticker):
    """Lit les trois chemins de la bibliothèque pour un titre. Ne calcule rien."""
    import yfinance as yf
    out = {"ticker": ticker}
    try:
        d = yf.Ticker(ticker)
    except Exception as e:                                       # noqa: BLE001
        return {"ticker": ticker, "erreur": f"{type(e).__name__}: {e}"[:160]}

    # ── Chemin 1 : le résumé, celui que le screener utilise aujourd'hui
    try:
        info = d.info or {}
        out["resume"] = {c: _champ(info, c) for c in CHAMPS_INFO}
        out["resume_nb_champs"] = len(info)
    except Exception as e:                                       # noqa: BLE001
        out["resume"] = {"erreur": f"{type(e).__name__}: {e}"[:160]}

    # ── Chemin 2 : la voie rapide, qui ne tape pas le même service
    try:
        fi = d.fast_info
        out["voie_rapide"] = {
            nom: _num(getattr(fi, nom, None))
            for nom in ("market_cap", "shares", "last_price", "previous_close")
        }
        out["voie_rapide"]["devise"] = getattr(fi, "currency", None)
    except Exception as e:                                       # noqa: BLE001
        out["voie_rapide"] = {"erreur": f"{type(e).__name__}: {e}"[:160]}

    # ── Chemin 3 : la série d'actions en circulation
    try:
        s = d.get_shares_full()
        if s is None or not len(s):
            out["serie_actions"] = {"present": False}
        else:
            out["serie_actions"] = {
                "present": True, "points": int(len(s)),
                "derniere": _num(s.iloc[-1]),
                "derniere_date": str(s.index[-1].date()),
            }
    except Exception as e:                                       # noqa: BLE001
        out["serie_actions"] = {"erreur": f"{type(e).__name__}: {e}"[:160]}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cibles", default="",
                   help="TICKER,TICKER — vide = dérivées des fiches publiées")
    p.add_argument("--temoins", type=int, default=2,
                   help="nombre de témoins par place de cotation (défaut 2)")
    a = p.parse_args()

    if a.cibles.strip():
        cibles = [t.strip().upper() for t in a.cibles.split(",") if t.strip()]
        temoins = []
    else:
        cibles, temoins = cibles_et_temoins(n_temoins=a.temoins)

    if not cibles:
        # Pas une panne : la source s'est peut-être rétablie. On le DIT, et on
        # écrit quand même un rapport — un fichier absent se lirait comme un
        # job qui n'a pas tourné.
        print("Aucune fiche ne publie une marge de flux sans son rendement.")
        with open(RAPPORT, "w", encoding="utf-8") as f:
            json.dump({"cibles": [], "temoins": [], "titres": [],
                       "_etat": "aucune cible : plus aucune fiche ne présente le défaut"},
                      f, ensure_ascii=False, indent=2)
        return 0

    print(f"Cibles  ({len(cibles)}) : {', '.join(cibles)}")
    print(f"Témoins ({len(temoins)}) : {', '.join(temoins) or '—'}")
    titres = []
    for t in cibles + temoins:
        print(f"  · {t}")
        r = sonder(t)
        r["role"] = "cible" if t in cibles else "temoin"
        titres.append(r)

    rapport = {
        "_mode_d_emploi":
            "Rapport BRUT, aucune décision. Lire dans cet ordre : (1) "
            "resume.marketCap.present — le champ est-il absent ou présent à "
            "null ? (2) resume.sharesOutstanding — le repli actuel en dépend, "
            "et s'il est absent le repli ne peut pas se déclencher. (3) "
            "voie_rapide.market_cap et serie_actions — deux autres chemins de "
            "la même bibliothèque, qui peuvent servir ce que le résumé tait. "
            "(4) comparer chaque cible à ses témoins de la MÊME place : un "
            "témoin renseigné là où la cible est vide écarte la panne de place.",
        "cibles": cibles,
        "temoins": temoins,
        "titres": titres,
    }
    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {RAPPORT} — {len(titres)} titre(s) sondé(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
