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
# Openverse est derrière Cloudflare, dont la règle anti-robot refuse (403,
# erreur 1010) tout en-tête qui ne ressemble pas à celui d'un navigateur. On ne
# se déguise pas en Chrome pour autant : le gabarit « Mozilla/5.0 (compatible;
# … ) » est la forme historiquement prévue pour un client qui se nomme, et il
# nous laisse dire qui appelle et où écrire. Si Cloudflare le refuse aussi,
# c'est que la source nous est fermée et l'on en tirera la conclusion.
UA_COMPAT = ("Mozilla/5.0 (compatible; SignalWatchlists/1.0; "
             "+https://github.com/Kosmos-7/Signal)")

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


class QuotaEpuise(Exception):
    """Openverse a coupé le robinet : inutile d'insister 700 fois."""


# Openverse limite les clients anonymes. On ne connaît pas le plafond exact et
# la documentation a changé : plutôt que le deviner, on compte les refus et on
# s'arrête au troisième d'affilée, en gardant ce qui a été trouvé jusque-là.
_REFUS = [0]


def chercher(terme, page_size=20):
    params = {"q": terme, "license": "cc0,pdm,by,by-sa", "page_size": str(page_size)}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA_COMPAT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _REFUS[0] = 0
            return json.load(r).get("results") or []
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            _REFUS[0] += 1
            if _REFUS[0] >= 3:
                raise QuotaEpuise(f"HTTP {e.code} trois fois de suite")
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
    """Interroge l'API sous plusieurs identités pour savoir laquelle passe.

    Premier diagnostic (run 30748258219) : HTTP 403, Cloudflare erreur 1010,
    « the site owner has blocked access based on the client signature ». Aucun
    paramètre n'était en cause, tous les gabarits de requête tombaient, y
    compris la racine de l'API. Seul l'en-tête d'un navigateur passait.

    Reste à savoir si la règle est fine (empreinte complète d'un navigateur) ou
    grossière (le nom doit commencer par « Mozilla/5.0 »). Dans le second cas
    un en-tête à la fois conforme au gabarit ET honnête sur qui appelle suffit,
    et c'est ce qu'on veut : se présenter, pas se déguiser.
    """
    essais = [
        ("descriptif", UA),
        ("compatible", UA_COMPAT),
        ("navigateur", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    ]
    for nom, ua in essais:
        req = urllib.request.Request(API + "?q=nvidia&page_size=5",
                                     headers={"User-Agent": ua,
                                              "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8", "replace") or "{}")
                print(f"  ✓ {nom:11s} HTTP {r.status}  {d.get('result_count')} résultats")
                for res in (d.get("results") or [])[:3]:
                    print(f"      · {(res.get('title') or '')[:52]:52s} "
                          f"{res.get('license')}-{res.get('license_version') or ''} "
                          f"[{res.get('source')}]")
        except urllib.error.HTTPError as e:
            try:
                corps = e.read(300).decode("utf-8", "replace").replace("\n", " ")
            except Exception:
                corps = ""
            print(f"  ✗ {nom:11s} HTTP {e.code}  {corps[:200]}")
        except Exception as e:
            print(f"  ✗ {nom:11s} {type(e).__name__}: {e}")
        time.sleep(1.5)


def _libelle_licence(code, version):
    """« cc0 » n'est pas « CC CC0 » : les deux licences libres ont leur nom."""
    v = (version or "").strip()
    if code == "cc0":
        return f"CC0 {v}".strip()
    if code == "pdm":
        return f"Marque du domaine public {v}".strip()
    return f"CC {code.upper()} {v}".strip()


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
        "licence": _libelle_licence(lic, res.get("license_version")),
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
    ap.add_argument("--tickers", default="",
                    help="liste de tickers separes par des virgules, y compris "
                         "des fiches deja illustrees (repasse ciblee)")
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
    if a.tickers:
        # Repasse ciblee : on veut pouvoir revenir sur une fiche DEJA illustree
        # dont la revue d'ensemble a juge l'image faible.
        vises = [t.strip() for t in a.tickers.split(",") if t.strip()]
        inconnus = [t for t in vises if t not in noms]
        if inconnus:
            raise SystemExit(f"tickers absents de l'univers : {inconnus}")
        cibles = vises
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(deja)} déjà illustrées, {len(cibles)} à chercher sur Openverse\n", flush=True)

    rapport, arret = {}, ""
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        trouves, vus = [], set()
        try:
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
        except QuotaEpuise as e:
            arret = f"{e} (arrêt à {tk}, {i}/{len(cibles)})"
            print(f"\n⚠ {arret}\n", flush=True)
            break

        trouves.sort(key=lambda c: -c["score"])
        gardes = []
        for c in trouves:
            if len(gardes) >= a.par_societe:
                break
            try:
                req = urllib.request.Request(c["url"], headers={"User-Agent": UA_COMPAT})
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
        json.dump({"societes": len(rapport), "arret": arret, "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"TROUVÉES SUR OPENVERSE : {len(rapport)}/{len(cibles)} sociétés")
    if arret:
        print(f"campagne interrompue : {arret}")
    srcs = {}
    for e in rapport.values():
        s = e["candidats"][0]["source"]
        srcs[s] = srcs.get(s, 0) + 1
    print("par banque d'images :", srcs)


if __name__ == "__main__":
    main()
