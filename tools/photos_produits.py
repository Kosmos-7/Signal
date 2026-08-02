#!/usr/bin/env python3
"""Photos de PRODUITS plutôt que de sièges sociaux.

LE PROBLÈME. Wikidata P18 donne, pour une entreprise, l'image que la communauté
a retenue pour la représenter. Dans neuf cas sur dix c'est le siège social. On
se retrouve donc avec une collection de façades de bureaux : elles identifient
l'entreprise, mais n'apprennent rien sur ce qu'elle fait. Un immeuble de verre
à Santa Clara ne dit pas si l'on regarde un fondeur, une banque ou un éditeur.

LA SOURCE. Chaque entreprise notable a une CATÉGORIE Commons (propriété P373 de
Wikidata), et cette catégorie contient bien plus que le siège : les produits,
les machines, les puces, les avions, les emballages. On liste donc la catégorie
et ses sous-catégories, puis on classe les fichiers par ce que leur nom promet.

LE CLASSEMENT. Un nom de fichier est un indice faible mais utile, et il est
gratuit. On note POSITIVEMENT ce qui ressemble à un produit ou à un outil de
production (puce, wafer, carte, module, machine, appareil), NÉGATIVEMENT ce qui
ressemble à un bâtiment, un logo, un portrait ou un document. Le classement ne
décide pas : il ordonne les candidats pour l'examen visuel, qui reste le seul
juge. On ne publie jamais sur la foi d'un nom de fichier.

Usage :
    python3 tools/photos_produits.py [--telecharger] [--limite N]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

WD_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UA = "SignalWatchlists/1.0 (https://github.com/Kosmos-7/Signal ; projet pédagogique)"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import entite, famille_licence, _get                # noqa: E402
from sonde_photos_titres import nom_usage                                # noqa: E402

# Ce qu'on CHERCHE : l'objet fabriqué ou l'outil qui le fabrique.
BONUS = {
    r"\b(chip|die|wafer|processor|cpu|gpu|soc|asic|fpga)\b": 6,
    r"\b(card|module|board|pcb|memory|ssd|drive|disk)\b": 5,
    r"\b(machine|equipment|scanner|lithograph|stepper|robot|tool)\b": 5,
    r"\b(product|device|hardware|terminal|console|server|rack)\b": 4,
    r"\b(engine|turbine|transformer|switchgear|cable|antenna)\b": 4,
    r"\b(package|packaging|bottle|can|box|dispenser)\b": 3,
    r"\b(interior|assembly|production|line|factory floor|cleanroom)\b": 3,
    r"\b(car|vehicle|aircraft|train|ship)\b": 3,
}
# Ce qu'on ÉVITE : ce dont on a déjà trop, et ce qui n'illustre rien.
MALUS = {
    r"\b(headquarters|hq|building|office|campus|tower|plaza|facade|entrance)\b": -8,
    r"\b(logo|wordmark|icon|symbol|sign|signage|billboard)\b": -9,
    r"\b(portrait|ceo|founder|chairman|president|speaking|interview)\b": -7,
    r"\b(map|chart|graph|diagram|timeline|share|certificate|document)\b": -6,
    r"\b(store|shop|branch|kiosk|booth|stand|exhibition)\b": -3,
    r"\.(svg|pdf)$": -12,
}


def score_nom(nom):
    n = nom.lower()
    s = 0
    for motif, poids in BONUS.items():
        if re.search(motif, n):
            s += poids
    for motif, poids in MALUS.items():
        if re.search(motif, n):
            s += poids
    return s


def categorie_de(qid):
    """Catégorie Commons (P373) de l'entité."""
    try:
        d = _get(WD_API, {"action": "wbgetentities", "format": "json",
                          "ids": qid, "props": "claims"})
    except Exception:
        return None
    claims = ((d.get("entities") or {}).get(qid) or {}).get("claims") or {}
    for c in claims.get("P373", []):
        val = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(val, str):
            return val
    return None


def fichiers_categorie(cat, profondeur=1, vus=None, budget=None):
    """Fichiers d'une catégorie Commons, sous-catégories incluses (1 niveau)."""
    vus = vus if vus is not None else set()
    budget = budget if budget is not None else [60]
    out = []
    if budget[0] <= 0:
        return out
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "list": "categorymembers",
                               "cmtitle": "Category:" + cat, "cmlimit": "60",
                               "cmtype": "file|subcat"})
    except Exception:
        return out
    budget[0] -= 1
    sous = []
    for m in (d.get("query", {}).get("categorymembers") or []):
        titre = m.get("title", "")
        if titre.startswith("File:"):
            if titre not in vus:
                vus.add(titre)
                out.append(titre[5:])
        elif titre.startswith("Category:") and profondeur > 0:
            sous.append(titre[9:])
    # Les sous-catégories qui parlent de produits d'abord : le budget d'appels
    # est limité, autant le dépenser là où l'on a une chance de trouver.
    sous.sort(key=lambda c: -score_nom(c))
    for c in sous[:4]:
        out += fichiers_categorie(c, profondeur - 1, vus, budget)
    return out


def infos(fichier):
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "titles": "File:" + fichier, "prop": "imageinfo",
                               "iiprop": "url|extmetadata|size", "iiurlwidth": "1600"})
    except Exception:
        return None
    page = next(iter((d.get("query", {}).get("pages") or {}).values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    if not info or (info.get("width") or 0) < 900:
        return None
    meta = info.get("extmetadata") or {}
    lic = (meta.get("LicenseShortName") or {}).get("value", "?")
    fam = famille_licence(lic + " " + (meta.get("UsageTerms") or {}).get("value", ""))
    if fam == "autre":
        return None
    return {"fichier": fichier, "url": info.get("thumburl") or info.get("url"),
            "page": info.get("descriptionurl", ""), "licence": lic, "famille": fam,
            "auteur": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:80]}


def prepare(brut, chemin):
    from PIL import Image, ImageEnhance
    im = Image.open(io.BytesIO(brut)).convert("RGB")
    rc, rs = 960 / 540, im.width / im.height
    if rs > rc:
        nw = int(im.height * rc)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width / rc)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    im = im.resize((960, 540), Image.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(0.74)
    im = ImageEnhance.Color(im).enhance(0.85)
    im.save(chemin, "JPEG", quality=82, optimize=True, progressive=True)
    return os.path.getsize(chemin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--telecharger", action="store_true")
    ap.add_argument("--sortie", default="assets/titres/produits")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=2,
                    help="candidats retenus par société (pour l'arbitrage visuel)")
    a = ap.parse_args()

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})
    cibles = sorted(noms)[: a.limite] if a.limite else sorted(noms)
    if a.telecharger:
        os.makedirs(a.sortie, exist_ok=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        qid, label = entite(nom)
        cat = categorie_de(qid) if qid else None
        if not cat:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:22]:22s} (pas de catégorie)", flush=True)
            time.sleep(0.2)
            continue
        fichiers = fichiers_categorie(cat)
        classes = sorted(((score_nom(f), f) for f in fichiers), reverse=True)
        gardes = []
        for sc, f in classes:
            if sc <= 0 or len(gardes) >= a.par_societe:
                break
            inf = infos(f)
            if not inf:
                continue
            inf["score"] = sc
            gardes.append(inf)
            if a.telecharger:
                try:
                    req = urllib.request.Request(inf["url"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=45) as r:
                        brut = r.read()
                    inf["poids"] = prepare(brut, os.path.join(a.sortie, f"{tk}_{len(gardes)-1}.jpg"))
                except Exception as e:
                    print(f"      ✗ téléchargement {type(e).__name__}")
        if gardes:
            rapport[tk] = {"nom": nom, "label": label, "categorie": cat, "candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} "
                  f"{len(fichiers):3d} fichiers → {gardes[0]['score']:2d} pts  "
                  f"{gardes[0]['fichier'][:44]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:20]:20s} "
                  f"{len(fichiers):3d} fichiers, aucun produit identifiable", flush=True)
        time.sleep(0.2)

    with open("photos_produits.json", "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"PRODUITS TROUVÉS : {len(rapport)}/{len(cibles)} sociétés")


if __name__ == "__main__":
    main()
