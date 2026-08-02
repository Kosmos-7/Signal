#!/usr/bin/env python3
"""Photos de sociétés via OPENVERSE : sortir du corpus Wikimedia.

POURQUOI UNE QUATRIÈME SOURCE. Les trois premières passes (recherche textuelle,
Wikidata P18, catégories Commons) puisent toutes dans le MÊME fonds : Wikimedia
Commons. Quand il ne contient rien sur une société, aucune ruse d'interrogation
n'y changera quoi que ce soit. C'est le cas de la moitié des titres couverts.

Openverse est l'agrégateur de la Fondation Wikimedia : il indexe Flickr, des
musées, des banques d'images ouvertes, soit plusieurs centaines de millions de
fichiers sous licence libre, dont l'immense majorité n'est pas sur Commons.
Flickr en particulier est riche en photos de produits, de salons professionnels
et de centres de données que Commons n'a jamais reçues.

CE QU'IL FAUT SURVEILLER. Openverse indexe des sources hétérogènes : la
description est libre, personne n'a validé que la photo montre bien la société
annoncée, et l'on retombe donc sur le risque de la recherche par mots. Trois
garde-fous : le nom de la société doit figurer dans le titre du fichier, le
barème de pertinence de la campagne « produits » s'applique, et rien n'est
publié sans examen visuel.

Usage : python3 tools/photos_openverse.py [--limite N] [--par-societe N]
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/images/"
UA = "SignalWatchlists/1.0 (https://github.com/Kosmos-7/Signal ; projet pédagogique)"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_produits import score_nom, prepare                    # noqa: E402
from sonde_photos_titres import nom_usage                         # noqa: E402

# Licences acceptées. « pdm » = marque du domaine public, « cc0 » = renonciation.
# by et by-sa exigent un crédit, qui est affiché sur la fiche.
LICENCES = {"cc0": "libre", "pdm": "libre", "by": "by", "by-sa": "by-sa"}

# Mots à accoler au nom de la société pour viser le produit plutôt que le siège.
# Un seul mot par requête : Openverse fait un ET implicite, et une requête trop
# longue ne ramène rien.
ANGLES = ["chip", "processor", "product", "card", "device", "server",
          "factory", "machine", "store", ""]


def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"[̀-ͯ]", "", s)


def chercher(terme, page_size=20):
    params = {"q": terme, "license": "cc0,pdm,by,by-sa", "page_size": str(page_size)}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("results") or []
    except urllib.error.HTTPError as e:
        # Le code ET le corps : un 400 d'Openverse nomme le paramètre fautif,
        # un 401 dit qu'il faut s'authentifier, un 429 qu'il faut ralentir.
        # Sans ça on ne voit qu'« HTTPError » et l'on diagnostique à l'aveugle.
        try:
            corps = e.read(400).decode("utf-8", "replace").replace("\n", " ")
        except Exception:
            corps = ""
        print(f"      ✗ Openverse « {terme} » : HTTP {e.code} {corps[:200]}")
        return []
    except Exception as e:
        print(f"      ✗ Openverse « {terme} » : {type(e).__name__}")
        return []


def diagnostic():
    """Interroge l'API de sept manières pour savoir laquelle passe.

    Le premier passage a échoué sur les 740 requêtes avec un simple
    « HTTPError ». Plutôt que deviner quel paramètre gêne, on essaie chaque
    hypothèse une fois et on lit le code de retour.
    """
    essais = [
        ("nu", API + "?q=nvidia", {"User-Agent": UA}),
        ("sans UA", API + "?q=nvidia", {}),
        ("navigateur", API + "?q=nvidia",
         {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126 Safari/537.36"}),
        ("+ licence", API + "?q=nvidia&license=cc0,pdm,by,by-sa", {"User-Agent": UA}),
        ("+ mature", API + "?q=nvidia&mature=false", {"User-Agent": UA}),
        ("+ page_size", API + "?q=nvidia&page_size=20", {"User-Agent": UA}),
        ("ancien hôte", "https://api.openverse.engineering/v1/images/?q=nvidia",
         {"User-Agent": UA}),
        ("racine", "https://api.openverse.org/v1/", {"User-Agent": UA}),
    ]
    for nom, url, entetes in essais:
        req = urllib.request.Request(url, headers={**entetes, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read(4000).decode("utf-8", "replace") or "{}")
                n = d.get("result_count", d.get("results") and len(d["results"]))
                print(f"  ✓ {nom:12s} HTTP {r.status}  résultats={n}")
        except urllib.error.HTTPError as e:
            try:
                corps = e.read(300).decode("utf-8", "replace").replace("\n", " ")
            except Exception:
                corps = ""
            print(f"  ✗ {nom:12s} HTTP {e.code}  {corps[:220]}")
        except Exception as e:
            print(f"  ✗ {nom:12s} {type(e).__name__}: {e}")
        time.sleep(1.0)


def retenir(res, nom):
    """Le titre doit nommer la société : Openverse n'a validé aucun rattachement."""
    titre = res.get("title") or ""
    if _norm(nom.split()[0]) not in _norm(titre):
        return None
    lic = (res.get("license") or "").lower()
    if lic not in LICENCES:
        return None
    if (res.get("width") or 0) < 900:
        return None
    return {
        "fichier": titre[:90],
        "url": res.get("url"),
        "page": res.get("foreign_landing_url") or res.get("detail_url") or "",
        "licence": f"CC {lic.upper()} {res.get('license_version') or ''}".strip(),
        "famille": LICENCES[lic],
        "auteur": (res.get("creator") or "")[:80],
        "source": res.get("source") or "",
        "score": score_nom(titre),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/openverse")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=2)
    ap.add_argument("--diag", action="store_true",
                    help="tester l'API sous plusieurs formes et sortir")
    a = ap.parse_args()

    if a.diag:
        diagnostic()
        return

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})
    deja = set()
    if os.path.exists("assets/titres/LEGENDES.json"):
        deja = set(json.load(open("assets/titres/LEGENDES.json", encoding="utf-8")))
    cibles = [t for t in sorted(noms) if t not in deja]
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(deja)} déjà illustrées, {len(cibles)} à chercher sur Openverse\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        trouves, vus = [], set()
        for angle in ANGLES:
            if len(trouves) >= a.par_societe * 3:
                break
            for res in chercher(f"{nom} {angle}".strip()):
                c = retenir(res, nom)
                if not c or c["url"] in vus:
                    continue
                vus.add(c["url"])
                trouves.append(c)
            time.sleep(0.35)

        trouves.sort(key=lambda c: -c["score"])
        gardes = []
        for c in trouves:
            if len(gardes) >= a.par_societe:
                break
            try:
                req = urllib.request.Request(c["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
                c["poids"] = prepare(brut, os.path.join(a.sortie, f"{tk}_{len(gardes)}.jpg"))
            except Exception as e:
                print(f"      ✗ téléchargement {type(e).__name__}")
                continue
            gardes.append(c)

        if gardes:
            rapport[tk] = {"nom": nom, "candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} "
                  f"{len(trouves):3d} pistes → {gardes[0]['score']:3d} pts "
                  f"[{gardes[0]['source'][:10]:10s}] {gardes[0]['fichier'][:38]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} rien", flush=True)

    with open("photos_openverse.json", "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"TROUVÉES SUR OPENVERSE : {len(rapport)}/{len(cibles)} sociétés")
    srcs = {}
    for e in rapport.values():
        s = e["candidats"][0]["source"]
        srcs[s] = srcs.get(s, 0) + 1
    print("par banque d'images :", srcs)


if __name__ == "__main__":
    main()
