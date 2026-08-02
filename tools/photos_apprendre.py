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

FORMAT. 1700 × 531, soit un 16/5 volontairement bas. Ce n'est pas une image
d'illustration posée au milieu du texte mais une bande d'ouverture, répétée à
chaque section : une bande haute ferait douze pauses dans la lecture au lieu de
douze repères. Même assombrissement que les photos de fiches, pour que ces
images appartiennent visuellement au site et non à une banque d'images.

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
LARGEUR, HAUTEUR = 1700, 531

# Slot = l'ancre de la section que l'image ouvre. « cadrage » place le
# recadrage vertical : 0.0 garde le haut, 1.0 le bas, 0.5 le centre. En 16/5 il
# ne reste presque rien de la hauteur d'origine, donc ce réglage décide de ce
# qu'on voit et n'a rien d'accessoire.
# « luminosite » corrige l'exposition quand le sujet l'impose : une page de
# journal est un aplat blanc, et sur un fond sombre un aplat blanc n'aère pas,
# il éblouit. « contraste » sert au cas inverse, un document pâle dont le tracé
# disparaît une fois la bande assombrie. Les valeurs ne sont pas décoratives,
# elles ont été réglées en regardant le résultat.
# « alt » décrit l'image pour qui ne la voit pas ; « legende » dit ce qu'on
# regarde. Les deux sont écrits ici et nulle part ailleurs : c'est ce script qui
# pose les balises dans apprendre.html, pour qu'une légende et son image ne
# puissent pas diverger.
ILLUSTRATIONS = {
    "s1": {
        "fichier": "Wall Street - New York Stock Exchange.jpg",
        "cadrage": 0.32,
        "legende": "La façade du New York Stock Exchange, Wall Street",
        "credit": "Carlos Delgado · CC BY-SA 3.0",
        "alt": "Façade à colonnes du New York Stock Exchange, drapeaux "
               "américains et plaque de rue Wall St",
    },
    "s2": {
        "fichier": "Trading floor of the New York Stock Exchange, New York City "
                   "LCCN2011632435.tif",
        "cadrage": 0.55,
        "legende": "La corbeille du New York Stock Exchange",
        "credit": "Carol M. Highsmith, Library of Congress · domaine public",
        "alt": "Corbeille du New York Stock Exchange, agents en mouvement "
               "autour des postes de cotation",
    },
    "s3": {
        "fichier": "Stock Certficate SKF 1913.jpg",
        "cadrage": 0.35,
        "luminosite": 0.62,
        "legende": "Certificat de cinq actions SKF, 1913",
        "credit": "Aktiebolaget Svenska Kullagerfabriken · domaine public",
        "alt": "Certificat d'actions gravé de 1913, cinq actions de cent "
               "couronnes, signé à la main",
    },
    "s4": {
        "fichier": "002 Production line - car assembly line in General Motors "
                   "Manufacturing Poland - Gliwice, Poland.jpg",
        "cadrage": 0.5,
        "legende": "Chaîne d'assemblage automobile, Gliwice, Pologne",
        "credit": "Marek Ślusarczyk · CC BY 3.0",
        "alt": "Chaîne d'assemblage automobile, carrosseries alignées sur le "
               "convoyeur",
    },
    "s5": {
        "fichier": "Toledo Market Traditional Rice Stall.jpg",
        "cadrage": 0.5,
        "legende": "Étal de riz, marché de Toledo, Philippines",
        "credit": "QueenCityCebu · CC BY-SA 4.0",
        "alt": "Sacs de riz ouverts sur un étal de marché, chacun portant son "
               "prix inscrit sur une étiquette",
    },
    "s6": {
        "fichier": "Stock Price Listing Numbers on a Korean Newspaper.jpg",
        "cadrage": 0.5,
        "luminosite": 0.55,
        "legende": "Cotes de clôture dans un quotidien coréen",
        "credit": "Mk2010 · CC BY-SA 4.0",
        "alt": "Colonnes de cotes boursières imprimées dans un quotidien, "
               "flèches rouges et bleues de variation",
    },
    "s7": {
        "fichier": "Stacks of Canadian Coins (16269886909).jpg",
        "cadrage": 0.82,
        "legende": "Piles de pièces",
        "credit": "KMR Photography · CC BY 2.0",
        "alt": "Trois piles de pièces de monnaie de hauteurs inégales sur une "
               "table",
    },
    "s8": {
        "fichier": "Miss Cowell with Hollerith Machine, 1964.jpg",
        "cadrage": 0.45,
        "legende": "Opératrice d'une machine Hollerith, 1964",
        "credit": "LSE Library · sans restriction connue",
        "alt": "Femme actionnant une machine mécanographique à cartes "
               "perforées, photographie noir et blanc de 1964",
    },
    "s9": {
        "fichier": "NOAA Central Library Card Catalog 2.jpg",
        "cadrage": 0.5,
        "legende": "Fichier cartonné de la bibliothèque centrale de la NOAA",
        "credit": "Jennifer Fagan-Fry · CC BY-SA 4.0",
        "alt": "Meuble à tiroirs d'un fichier de bibliothèque, étiquettes et "
               "fiches cartonnées",
    },
    "s10": {
        "fichier": "Wide angle view of Mission Control Center during Apollo 14 "
                   "transmission (S71-17122).jpg",
        "cadrage": 0.5,
        "legende": "Salle de contrôle de mission, Apollo 14, 1971",
        "credit": "NASA Johnson Space Center · domaine public",
        "alt": "Salle de contrôle de mission de la NASA, rangées de consoles "
               "devant un grand écran de suivi",
    },
    "s11": {
        "fichier": "Logbook of the Almira (Ship) of Edgartown, mastered by "
                   "Charles M. Marchant on voyage from 5 Aug. 1869-1870 (1869) "
                   "(14774067644).jpg",
        "cadrage": 0.52,
        "luminosite": 0.62,
        "contraste": 1.45,
        "legende": "Journal de bord de l'Almira, 1869, calculs de route",
        "credit": "Nantucket Historical Association · sans restriction connue",
        "alt": "Page manuscrite d'un journal de bord de baleinier, colonnes de "
               "calculs à la plume",
    },
    "s12": {
        "fichier": "Suzzallo Reading Room University of Washington restoration "
                   "Seattle Washington 2026.jpg",
        "cadrage": 0.45,
        "legende": "Salle de lecture Suzzallo, université de Washington",
        "credit": "Guywelch2000 · CC BY 4.0",
        "alt": "Longue salle de lecture néogothique, tables alignées sous des "
               "voûtes et de hautes verrières",
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


def prepare(brut, chemin, cadrage, luminosite, contraste):
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
    if contraste != 1.0:
        im = ImageEnhance.Contrast(im).enhance(contraste)
    im = ImageEnhance.Color(im).enhance(0.85)
    im.save(chemin, "JPEG", quality=82, optimize=True, progressive=True)
    return os.path.getsize(chemin)


def echapper(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def injecter(page, registre):
    """Pose ou remplace la bande d'amorce en tête de chaque section illustrée.

    Idempotent : une amorce déjà présente est remplacée, jamais dupliquée. Les
    sections sans image conservées telles quelles, et une image retirée du
    dictionnaire voit sa balise disparaître — sans quoi le HTML garderait un
    <img> vers un fichier qui n'existe plus.
    """
    html = open(page, encoding="utf-8").read()
    avant = html
    amorce = re.compile(
        r'(<section class="section-block" id="(s\d+)">\n)'
        r'(?:    <figure class="sec-tete">\n(?:.*?\n)*?    </figure>\n)?')

    def poser(m):
        ouverture, slot = m.group(1), m.group(2)
        e = registre.get(slot)
        if not e:
            return ouverture
        cfg = ILLUSTRATIONS.get(slot, {})
        alt = echapper(cfg.get("alt") or e["legende"])
        return (f'{ouverture}'
                f'    <figure class="sec-tete">\n'
                f'      <img src="{SORTIE}/{slot}.jpg?v={e["v"]}" '
                f'alt="{alt}" loading="lazy" '
                f'width="{LARGEUR}" height="{HAUTEUR}">\n'
                f'      <figcaption>{echapper(e["legende"])}'
                f'<i>{echapper(e["credit"])}</i></figcaption>\n'
                f'    </figure>\n')

    html = amorce.sub(poser, html)
    if html != avant:
        open(page, "w", encoding="utf-8").write(html)
        print(f"{page} mis à jour")
    else:
        print(f"{page} inchangé")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="apprendre.html")
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
        poids = prepare(brut, chemin, cfg["cadrage"],
                        cfg.get("luminosite", 0.74), cfg.get("contraste", 1.0))
        registre[slot] = {
            "legende": cfg["legende"], "credit": cfg["credit"],
            "fichier": cfg["fichier"], "page": src["page"],
            "licence": src["licence"], "auteur": src["auteur"],
            "v": empreinte(chemin),
        }
        print(f"   → {chemin}  {poids // 1024} ko  [{src['licence']}]", flush=True)

    # Une entrée du registre dont le fichier a disparu ferait poser un <img>
    # cassé : on nettoie avant d'écrire quoi que ce soit dans le HTML.
    registre = {s: e for s, e in registre.items()
                if s in ILLUSTRATIONS and os.path.exists(
                    os.path.join(SORTIE, f"{s}.jpg"))}

    json.dump(dict(sorted(registre.items(), key=lambda kv: int(kv[0][1:]))),
              open(REGISTRE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{len(registre)} illustrations, registre écrit dans {REGISTRE}")
    injecter(a.page, registre)

    manquants = [s for s in ILLUSTRATIONS if s not in registre]
    if manquants:
        print(f"⚠ sans fichier : {', '.join(manquants)}")


if __name__ == "__main__":
    main()
