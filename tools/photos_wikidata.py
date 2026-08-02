#!/usr/bin/env python3
"""Photos de sociétés via WIKIDATA plutôt que par recherche textuelle.

POURQUOI CHANGER DE SOURCE. La recherche plein texte sur Commons cherche des
MOTS : « Bank of America headquarters » ramène le siège de la Banque mondiale,
« Eaton » un photographe du XIXe siècle, « Western Digital » un commissariat de
Cambridge. 43 % des correspondances étaient fausses (sonde du 02/08).

Wikidata ne cherche pas des mots, il désigne une ENTITÉ. La propriété P18
(« image ») porte l'illustration que la communauté a retenue pour cette
entreprise précise. On passe d'une recherche approximative à une correspondance
d'identité : soit l'entité existe et son image est la bonne, soit il n'y en a
pas. Le doute disparaît.

CE QUE ÇA NE RÉSOUT PAS. La licence. Beaucoup de P18 sont en CC-BY ou CC-BY-SA,
qui exigent un crédit visible. Cet outil ne décide pas à la place de l'humain :
il RAPPORTE la licence de chaque image trouvée, pour qu'on choisisse en
connaissance de cause entre « domaine public seulement » et « crédit affiché ».

Usage :
    python3 tools/photos_wikidata.py                  # rapport seul
    python3 tools/photos_wikidata.py --telecharger    # + images dans candidats/
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
from sonde_photos_titres import nom_usage                        # noqa: E402

# Familles de licences, pour un rapport lisible. On ne filtre PAS ici : la
# décision d'accepter une licence à attribution appartient à l'humain.
def famille_licence(txt):
    t = (txt or "").lower()
    if any(k in t for k in ("cc0", "public domain", "pd-", "publicdomain", "no restrictions")):
        return "libre"          # aucune obligation
    if "by-sa" in t:
        return "by-sa"          # crédit + partage à l'identique
    if re.search(r"\bby\b|cc by", t):
        return "by"             # crédit seulement
    return "autre"


def _get(api, params):
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def entite(nom):
    """Identifiant Wikidata d'une société à partir de son nom d'usage."""
    try:
        d = _get(WD_API, {"action": "wbsearchentities", "format": "json",
                          "language": "en", "uselang": "en", "type": "item",
                          "limit": "5", "search": nom})
    except Exception:
        return None, ""
    for res in d.get("search", []):
        desc = (res.get("description") or "").lower()
        # On veut l'ENTREPRISE, pas la ville ni le patronyme qui porte le même
        # nom : le descriptif de Wikidata suffit à trancher.
        if any(k in desc for k in ("company", "corporation", "manufacturer",
                                   "bank", "enterprise", "business", "firm",
                                   "conglomerate", "insurance", "exchange")):
            return res["id"], res.get("label", "")
    d2 = d.get("search") or []
    return (d2[0]["id"], d2[0].get("label", "")) if d2 else (None, "")


def image_de(qid):
    """Nom du fichier Commons porté par P18 (image) pour cette entité."""
    try:
        d = _get(WD_API, {"action": "wbgetentities", "format": "json",
                          "ids": qid, "props": "claims"})
    except Exception:
        return None
    claims = ((d.get("entities") or {}).get(qid) or {}).get("claims") or {}
    for p in ("P18",):                      # P154 = logo : volontairement exclu
        for c in claims.get(p, []):
            val = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
            if isinstance(val, str):
                return val
    return None


def infos_commons(fichier):
    """URL, licence, auteur et dimensions d'un fichier Commons."""
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "titles": "File:" + fichier, "prop": "imageinfo",
                               "iiprop": "url|extmetadata|size", "iiurlwidth": "1600"})
    except Exception:
        return None
    page = next(iter((d.get("query", {}).get("pages") or {}).values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    if not info:
        return None
    meta = info.get("extmetadata") or {}
    lic = (meta.get("LicenseShortName") or {}).get("value", "?")
    return {
        "fichier": fichier,
        "url": info.get("thumburl") or info.get("url"),
        "page": info.get("descriptionurl", ""),
        "licence": lic,
        "famille": famille_licence(lic + " " + (meta.get("UsageTerms") or {}).get("value", "")),
        "auteur": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:80],
        "largeur": info.get("width"), "hauteur": info.get("height"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--telecharger", action="store_true")
    ap.add_argument("--sortie", default="assets/titres/candidats")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--depuis-rapport", action="store_true",
                    help="ne pas réinterroger Wikidata : télécharger depuis "
                         "photos_wikidata.json (les requêtes sont lentes, les "
                         "téléchargements non — les rejouer gâchait le budget "
                         "temps du job et l'a fait expirer à 21 images sur 67)")
    a = ap.parse_args()

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})
    cibles = sorted(noms)[: a.limite] if a.limite else sorted(noms)

    print(f"Wikidata : {len(cibles)} sociétés\n", flush=True)
    rapport, familles = {}, {}
    if a.depuis_rapport and os.path.exists("photos_wikidata.json"):
        d = json.load(open("photos_wikidata.json", encoding="utf-8"))
        rapport, familles = d["detail"], d["familles"]
        print(f"rapport existant réutilisé : {len(rapport)} images\n", flush=True)
        cibles = []
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        qid, label = entite(nom)
        fichier = image_de(qid) if qid else None
        infos = infos_commons(fichier) if fichier else None
        if infos:
            infos.update({"qid": qid, "label": label, "nom": nom})
            rapport[tk] = infos
            familles[infos["famille"]] = familles.get(infos["famille"], 0) + 1
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {label[:24]:24s} "
                  f"{infos['famille']:6s} {infos['licence'][:16]:16s} {fichier[:44]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:24]:24s} "
                  f"{'(pas d image)' if qid else '(entité introuvable)'}", flush=True)
        time.sleep(0.25)

    with open("photos_wikidata.json", "w", encoding="utf-8") as f:
        json.dump({"trouvees": len(rapport), "familles": familles,
                   "detail": rapport}, f, ensure_ascii=False, indent=1)

    print(f"\n{'=' * 70}")
    print(f"IMAGES TROUVÉES : {len(rapport)}/{len(cibles)} ({len(rapport)/len(cibles):.0%})")
    for fam, n in sorted(familles.items(), key=lambda x: -x[1]):
        libelle = {"libre": "domaine public ou CC0, aucune obligation",
                   "by": "CC-BY, crédit à afficher",
                   "by-sa": "CC-BY-SA, crédit à afficher",
                   "autre": "licence à examiner"}[fam]
        print(f"  {fam:6s} {n:3d}  {libelle}")

    if a.telecharger:
        from PIL import Image, ImageEnhance
        os.makedirs(a.sortie, exist_ok=True)
        for tk, c in rapport.items():
            try:
                req = urllib.request.Request(c["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
                im = Image.open(io.BytesIO(brut)).convert("RGB")
                rc, rs = 960 / 540, im.width / im.height
                if rs > rc:
                    nw = int(im.height * rc)
                    im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
                else:
                    nh = int(im.width / rc)
                    im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
                im = im.resize((960, 540), Image.LANCZOS)
                im = ImageEnhance.Brightness(im).enhance(0.72)
                im = ImageEnhance.Color(im).enhance(0.80)
                im.save(os.path.join(a.sortie, f"{tk}.jpg"), "JPEG", quality=82,
                        optimize=True, progressive=True)
            except Exception as e:
                print(f"  ✗ {tk}: {type(e).__name__}")
        with open(os.path.join(a.sortie, "MANIFESTE.json"), "w", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, indent=1)
        print(f"\n{len(os.listdir(a.sortie)) - 1} images téléchargées dans {a.sortie}")


if __name__ == "__main__":
    main()
