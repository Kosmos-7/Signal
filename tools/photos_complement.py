#!/usr/bin/env python3
"""Troisième passe sur les sociétés encore sans photo.

ÉTAT AVANT CETTE PASSE : 30 sociétés sur 104 ont une photo. Deux gisements
restent inexploités, et c'est ce que fait cet outil.

1. LES CANDIDATS P18 JAMAIS RAPATRIÉS. La campagne Wikidata avait identifié 67
   images ; le job a expiré après 21 téléchargements. Les 46 autres sont déjà
   dans photos_wikidata.json, il suffit de les chercher.

2. LA RECHERCHE PAR « DÉPEINT » (P180). Commons porte des données structurées :
   une image peut déclarer qu'elle DÉPEINT telle entité. `haswbstatement:P180=Q…`
   retourne donc les photos que des contributeurs ont explicitement rattachées à
   cette société. C'est plus large que P18, qui n'en retient qu'une, et plus sûr
   qu'une recherche de mots, qui ne comprend pas de quoi elle parle.

Les deux gisements sont fusionnés, classés par le même barème que la campagne
« produits » (bonus aux objets fabriqués, malus aux bâtiments, logos, portraits
et diagrammes), puis téléchargés pour examen visuel. Comme toujours : le
classement ordonne, il ne décide pas.

Usage : python3 tools/photos_complement.py [--limite N] [--par-societe N]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import entite, famille_licence, _get, COMMONS_API, UA   # noqa: E402
from photos_produits import score_nom, infos, prepare                        # noqa: E402
from sonde_photos_titres import nom_usage                                    # noqa: E402


def depeint(qid, limite=25):
    """Fichiers Commons déclarant DÉPEINDRE cette entité (données structurées)."""
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "list": "search", "srnamespace": "6",
                               "srsearch": f"haswbstatement:P180={qid}",
                               "srlimit": str(limite)})
    except Exception:
        return []
    return [m["title"][5:] for m in (d.get("query", {}).get("search") or [])
            if m.get("title", "").startswith("File:")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/complement")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=2)
    a = ap.parse_args()

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})

    # On ne retravaille QUE les sociétés encore sans photo publiée.
    deja = set()
    if os.path.exists("assets/titres/LEGENDES.json"):
        deja = set(json.load(open("assets/titres/LEGENDES.json", encoding="utf-8")))
    p18 = {}
    if os.path.exists("photos_wikidata.json"):
        p18 = json.load(open("photos_wikidata.json", encoding="utf-8"))["detail"]

    cibles = [t for t in sorted(noms) if t not in deja]
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(deja)} sociétés déjà illustrées, {len(cibles)} à compléter\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        propositions = []

        # Gisement 1 : le P18 déjà identifié, jamais téléchargé.
        if tk in p18:
            propositions.append((score_nom(p18[tk]["fichier"]) + 2, p18[tk]["fichier"], "P18"))

        # Gisement 2 : les images qui déclarent dépeindre l'entité.
        qid = p18.get(tk, {}).get("qid")
        if not qid:
            qid, _ = entite(nom)
            time.sleep(0.2)
        if qid:
            for f in depeint(qid):
                propositions.append((score_nom(f), f, "P180"))

        propositions.sort(reverse=True)
        gardes, vus = [], set()
        for sc, f, src in propositions:
            if len(gardes) >= a.par_societe:
                break
            if f in vus:
                continue
            vus.add(f)
            inf = infos(f)
            if not inf:
                continue
            inf.update({"score": sc, "gisement": src})
            try:
                req = urllib.request.Request(inf["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
                inf["poids"] = prepare(brut, os.path.join(a.sortie, f"{tk}_{len(gardes)}.jpg"))
            except Exception as e:
                print(f"      ✗ {type(e).__name__}")
                continue
            gardes.append(inf)

        if gardes:
            rapport[tk] = {"nom": nom, "qid": qid, "candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} "
                  f"{len(propositions):3d} pistes → {gardes[0]['gisement']:4s} "
                  f"{gardes[0]['score']:3d} pts  {gardes[0]['fichier'][:40]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} rien d'exploitable", flush=True)
        time.sleep(0.2)

    with open("photos_complement.json", "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"NOUVELLES PISTES : {len(rapport)}/{len(cibles)} sociétés")


if __name__ == "__main__":
    main()
