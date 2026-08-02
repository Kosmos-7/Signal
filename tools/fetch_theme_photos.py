#!/usr/bin/env python3
"""Cherche des photographies libres pour illustrer les watchlists thématiques.

Pourquoi ce script tourne en CI et pas en local : l'environnement de
développement n'a pas accès aux hébergeurs d'images (proxy). Le runner GitHub
Actions, lui, a un réseau ouvert.

LICENCES — contrainte non négociable. Le site est public : on ne retient que les
images du **domaine public** ou en **CC0**, c'est-à-dire celles qui n'imposent
aucune attribution et aucune condition de réutilisation. Les CC-BY et CC-BY-SA
sont écartées volontairement : elles seraient utilisables, mais au prix d'un
crédit visible par image, et une carte de watchlist n'est pas le bon support
pour ça. Toute image retenue voit sa provenance et sa licence journalisées dans
un manifeste versionné — vérifiable, pas déclaratif.

Source : Wikimedia Commons (API ouverte, sans clé, licences explicites par
fichier). Unsplash et Pexels exigent une clé d'API que le projet n'a pas.

Usage :
    python3 tools/fetch_theme_photos.py [--candidats N] [--sortie DOSSIER]
"""
import argparse
import io
import json
import os
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageEnhance

API = "https://commons.wikimedia.org/w/api.php"
UA = "SignalWatchlists/1.0 (https://github.com/Kosmos-7/Signal ; projet pédagogique)"

# Licences acceptées : aucune attribution requise, aucune condition de partage.
LICENCES_OK = ("cc0", "public domain", "pd-", "no restrictions", "publicdomain")
# Termes qui trahissent une licence contraignante malgré un libellé ambigu.
LICENCES_KO = ("by-sa", "by-nc", "nd", "fair use", "non-free", "copyright")

# Requêtes par thème. Plusieurs formulations : Commons est inégalement fourni,
# et une seule requête donne souvent des résultats hors sujet.
REQUETES = {
    # Périmètre resserré à trois watchlists (août 2026). Les requêtes visent des
    # objets PHOTOGRAPHIABLES et non des concepts : « salle de marché » donne des
    # photos, « finance » donne des logos et des graphiques de synthèse. On tente
    # plusieurs formulations parce que Commons est très inégalement fourni.
    "principale": [
        "stock exchange trading floor traders",
        "stock market display board airport",
        "financial data terminal screens",
        "new york stock exchange interior",
        "trading desk multiple monitors",
    ],
    "infra-ia": [
        # Les centres de données commerciaux sont presque tous sous licence
        # contraignante sur Commons. Les laboratoires fédéraux américains, eux,
        # produisent des œuvres du domaine public par statut : c'est là que se
        # trouvent les vraies salles de calcul libres de droits.
        "Oak Ridge supercomputer Summit",
        "Argonne National Laboratory supercomputer",
        "NASA supercomputer facility",
        "Lawrence Livermore supercomputer Sequoia",
        "NERSC Cori supercomputer",
        "supercomputer racks hall",
        "data center server room aisle",
        "silicon wafer semiconductor",
        "cleanroom semiconductor fabrication",
        "electrical substation transformer high voltage",
    ],
    "financials": [
        "stock exchange building facade columns",
        "bank headquarters building facade",
        "financial district skyline towers",
        "trading floor exchange hall",
        "wall street street sign buildings",
        "bank vault door",
    ],
}


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def licence_libre(meta):
    """Vrai si la licence n'impose ni attribution ni condition de partage."""
    champs = " ".join(str((meta.get(k) or {}).get("value", "")).lower()
                      for k in ("LicenseShortName", "UsageTerms", "License", "Copyrighted"))
    if any(k in champs for k in LICENCES_KO):
        return False, champs[:80]
    return any(k in champs for k in LICENCES_OK), champs[:80]


def chercher(terme, limite=12):
    """Images de Commons correspondant à un terme, filtrées sur la licence."""
    try:
        d = _get({
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f'filetype:bitmap {terme}', "gsrnamespace": "6",
            "gsrlimit": str(limite), "prop": "imageinfo",
            "iiprop": "url|extmetadata|size", "iiurlwidth": "1600",
        })
    except Exception as e:
        print(f"    ✗ recherche « {terme} » : {type(e).__name__}: {e}")
        return []
    out = []
    for page in (d.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        libre, detail = licence_libre(meta)
        if not libre:
            continue
        if (info.get("width") or 0) < 1200:
            continue
        out.append({
            "titre":   page.get("title", ""),
            "url":     info.get("thumburl") or info.get("url"),
            "page":    info.get("descriptionurl", ""),
            "licence": (meta.get("LicenseShortName") or {}).get("value", "?"),
            "auteur":  (meta.get("Artist") or {}).get("value", "")[:120],
            "largeur": info.get("width"), "hauteur": info.get("height"),
        })
    return out


def preparer(donnees, chemin, largeur=960, hauteur=540):
    """Recadre en 16:9, assombrit légèrement pour tenir sur un fond sombre.

    L'assombrissement n'est pas cosmétique : le site est en fond très sombre et
    une photo brute au contraste normal y fait une tache lumineuse qui écrase
    tout le reste de la carte. On reste loin d'un traitement qui rendrait le
    sujet méconnaissable — l'image doit encore illustrer quelque chose.
    """
    im = Image.open(io.BytesIO(donnees)).convert("RGB")
    r_cible, r_src = largeur / hauteur, im.width / im.height
    if r_src > r_cible:                       # trop large → rogner les côtés
        nw = int(im.height * r_cible)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:                                     # trop haute → rogner haut/bas
        nh = int(im.width / r_cible)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    im = im.resize((largeur, hauteur), Image.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(0.72)
    im = ImageEnhance.Color(im).enhance(0.80)
    im.save(chemin, "JPEG", quality=82, optimize=True, progressive=True)
    return os.path.getsize(chemin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", type=int, default=3,
                    help="nombre de candidats téléchargés par thème (pour arbitrage visuel)")
    ap.add_argument("--sortie", default="assets/themes/candidats")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)

    manifeste = {}
    for theme, termes in REQUETES.items():
        print(f"\n▸ {theme}")
        retenus, vus = [], set()
        for terme in termes:
            if len(retenus) >= a.candidats:
                break
            for c in chercher(terme):
                if len(retenus) >= a.candidats:
                    break
                if c["url"] in vus:
                    continue
                vus.add(c["url"])
                nom = f"{theme}_{len(retenus)}.jpg"
                dest = os.path.join(a.sortie, nom)
                try:
                    req = urllib.request.Request(c["url"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=45) as r:
                        brut = r.read()
                    poids = preparer(brut, dest)
                except Exception as e:
                    print(f"    ✗ {c['titre'][:52]} — {type(e).__name__}")
                    continue
                c.update({"fichier": nom, "poids": poids, "terme": terme})
                retenus.append(c)
                print(f"    ✓ {nom:22s} {poids // 1024:3d} Ko  [{c['licence']}]  {c['titre'][:46]}")
                time.sleep(0.5)          # courtoisie envers l'API Commons
        manifeste[theme] = retenus
        if not retenus:
            print("    ⚠ aucun candidat libre trouvé pour ce thème")

    chemin_manifeste = os.path.join(a.sortie, "MANIFESTE.json")
    with open(chemin_manifeste, "w", encoding="utf-8") as f:
        json.dump(manifeste, f, ensure_ascii=False, indent=1)

    total = sum(len(v) for v in manifeste.values())
    vides = [k for k, v in manifeste.items() if not v]
    print(f"\n{total} candidats pour {len(REQUETES)} thèmes → {a.sortie}/")
    if vides:
        print(f"⚠ thèmes sans candidat : {', '.join(vides)}")
    print(f"Provenance et licence de chaque image : {chemin_manifeste}")


if __name__ == "__main__":
    main()
