#!/usr/bin/env python3
"""Les respirations de la page « Apprendre ».

POURQUOI UN SCRIPT ET PAS QUATRE FICHIERS DÉPOSÉS À LA MAIN. Une image posée à
la main est une image dont plus personne ne sait, six mois plus tard, d'où elle
vient ni sous quelle licence elle est publiée. Le choix reste humain — les
candidats sont récoltés par photos_marques.py puis examinés à l'œil — mais une
fois le choix fait, il s'écrit ici, et le fichier se régénère à l'identique.

CE QUI DIFFÈRE DES PHOTOS DE FICHES. Une photo de fiche doit montrer la société
dont elle porte le nom : c'est une pièce d'archive, et la doctrine est stricte.
Ces quatre images-là ne prétendent rien de tel. Ce sont des respirations entre
deux sections d'un cours, et leur légende dit exactement ce qu'on voit, sans
jamais porter une information nécessaire à la compréhension du texte. Une image
qui ne se charge pas ne doit rien casser.

FORMAT. 1700 × 744, soit un 16/7 volontairement bas : une image haute coupe le
fil de lecture au lieu de l'aérer. Même assombrissement que les fiches, pour que
ces photos appartiennent visuellement au site et non à une banque d'images.

Usage : python3 tools/photos_apprendre.py [--slots s2,s4]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import _get, COMMONS_API, UA                     # noqa: E402

SORTIE = "assets/apprendre"
REGISTRE = os.path.join(SORTIE, "SOURCES.json")
LARGEUR, HAUTEUR = 1700, 744

# Slot = l'ancre de la section que l'image vient clore. « cadrage » place le
# recadrage vertical : 0.0 garde le haut, 1.0 le bas, 0.5 le centre.
# « luminosite » corrige l'exposition quand le sujet l'impose : une page de
# journal est un aplat blanc, et sur un fond sombre un aplat blanc en 16/7
# n'aère pas, il éblouit. Les valeurs ne sont pas décoratives, elles ont été
# réglées en regardant le résultat.
ILLUSTRATIONS = {
    "s2": {
        "fichier": "Trading floor of the New York Stock Exchange, New York City "
                   "LCCN2011632435.tif",
        "cadrage": 0.55,
        "legende": "La corbeille du New York Stock Exchange",
        "credit": "Carol M. Highsmith, Library of Congress · domaine public",
    },
    "s4": {
        "fichier": "002 Production line - car assembly line in General Motors "
                   "Manufacturing Poland - Gliwice, Poland.jpg",
        "cadrage": 0.5,
        "legende": "Chaîne d'assemblage automobile, Gliwice, Pologne",
        "credit": "Marek Ślusarczyk · CC BY 3.0",
    },
    "s6": {
        "fichier": "Stock Price Listing Numbers on a Korean Newspaper.jpg",
        "cadrage": 0.5,
        "luminosite": 0.55,
        "legende": "Cotes de clôture dans un quotidien coréen",
        "credit": "Mk2010 · CC BY-SA 4.0",
    },
}


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()[:8]


def source(fichier):
    """URL de rendu large + métadonnées de licence, via l'API Commons."""
    d = _get(COMMONS_API, {"action": "query", "format": "json",
                           "titles": "File:" + fichier, "prop": "imageinfo",
                           "iiprop": "url|extmetadata|size",
                           "iiurlwidth": str(LARGEUR * 2)})
    page = next(iter((d.get("query", {}).get("pages") or {}).values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    if not info:
        raise SystemExit(f"introuvable sur Commons : {fichier}")
    meta = info.get("extmetadata") or {}
    return {
        "url": info.get("thumburl") or info.get("url"),
        "page": info.get("descriptionurl", ""),
        "licence": (meta.get("LicenseShortName") or {}).get("value", "?"),
        "auteur": re.sub(r"<[^>]+>", "",
                         (meta.get("Artist") or {}).get("value", ""))[:90].strip(),
        "largeur_origine": info.get("width"),
    }


def prepare(brut, chemin, cadrage, luminosite):
    from PIL import Image, ImageEnhance
    im = Image.open(io.BytesIO(brut)).convert("RGB")
    cible = LARGEUR / HAUTEUR
    if im.width / im.height > cible:
        nw = int(im.height * cible)
        g = (im.width - nw) // 2
        im = im.crop((g, 0, g + nw, im.height))
    else:
        nh = int(im.width / cible)
        # Le cadrage vertical est le seul réglage qui compte ici : une corbeille
        # vue de haut se coupe par le bas, une devanture se coupe par le haut.
        h = int((im.height - nh) * min(max(cadrage, 0.0), 1.0))
        im = im.crop((0, h, im.width, h + nh))
    im = im.resize((LARGEUR, HAUTEUR), Image.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(luminosite)
    im = ImageEnhance.Color(im).enhance(0.85)
    im.save(chemin, "JPEG", quality=82, optimize=True, progressive=True)
    return os.path.getsize(chemin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default="",
                    help="ne régénérer que ces ancres, séparées par des virgules")
    a = ap.parse_args()

    cibles = [s.strip() for s in a.slots.split(",") if s.strip()] or list(ILLUSTRATIONS)
    inconnus = [s for s in cibles if s not in ILLUSTRATIONS]
    if inconnus:
        raise SystemExit(f"ancre inconnue : {', '.join(inconnus)}")

    os.makedirs(SORTIE, exist_ok=True)
    registre = {}
    if os.path.exists(REGISTRE):
        registre = json.load(open(REGISTRE, encoding="utf-8"))

    for slot in cibles:
        cfg = ILLUSTRATIONS[slot]
        print(f"{slot} · {cfg['fichier'][:70]}", flush=True)
        src = source(cfg["fichier"])
        req = urllib.request.Request(src["url"], headers={"User-Agent": UA})
        brut = urllib.request.urlopen(req, timeout=60).read()
        chemin = os.path.join(SORTIE, f"{slot}.jpg")
        poids = prepare(brut, chemin, cfg["cadrage"], cfg.get("luminosite", 0.74))
        registre[slot] = {
            "legende": cfg["legende"], "credit": cfg["credit"],
            "fichier": cfg["fichier"], "page": src["page"],
            "licence": src["licence"], "auteur": src["auteur"],
            "v": empreinte(chemin),
        }
        print(f"   → {chemin}  {poids // 1024} ko  [{src['licence']}]", flush=True)

    json.dump(dict(sorted(registre.items())), open(REGISTRE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{len(registre)} illustrations, registre écrit dans {REGISTRE}")
    print("Pense à lancer : python3 tools/versionner_photos.py")


if __name__ == "__main__":
    main()
