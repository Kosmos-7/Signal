#!/usr/bin/env python3
"""Huitième passe : le logo, quand c'est le visuel le plus parlant qu'on ait.

POURQUOI. Sept campagnes ont couvert 83 fiches sur 104, dont 52 avec un objet
fabriqué. Restent deux populations pour lesquelles la photo est un pis-aller :
les 21 fiches sans rien, et les 31 illustrées par un immeuble de bureaux qui
n'apprend rien. Or pour un fournisseur d'indices, une agence de notation ou un
gestionnaire d'actifs, il n'existe tout simplement pas d'objet à photographier.
Le logo est alors le seul visuel qui dise immédiatement de quelle société il
s'agit, et c'est à ce titre qu'il est plus pertinent qu'une façade anonyme.

LA SOURCE. Wikidata P154, la propriété « logo », que la campagne P18 excluait
volontairement parce qu'on cherchait alors des photographies. On ne retient que
ce que Commons héberge : Commons n'accepte pas les logos non libres, donc tout
ce qui en sort est soit sous le seuil d'originalité (PD-textlogo), soit sous
licence libre. La licence est rapportée telle quelle, jamais devinée.

CE QUE ÇA NE RÉSOUT PAS. Un logo reste une MARQUE. Le droit d'auteur n'est pas
le droit des marques : même un logo dans le domaine public ne peut pas être
utilisé pour laisser croire à un lien commercial. Notre usage est nominatif,
c'est-à-dire qu'il désigne la société sur une page qui parle d'elle, ce que
fait toute encyclopédie ; il est signalé comme tel dans CREDITS.md.

LA PRÉPARATION EST DIFFÉRENTE. La chaîne des photos recadre en 16:9 et
assombrit à 74 % pour tenir sur fond sombre. Appliquée à un logo, elle le
tronquerait et le noierait. Ici on fait l'inverse : logo entier, centré, jamais
recadré, sur un fond choisi selon SA PROPRE luminosité, parce qu'un logo noir
sur fond sombre est invisible et un logo blanc sur fond clair aussi.

Usage : python3 tools/photos_logos.py --tickers AAA,BBB [--tous]
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import entite, famille_licence, _get, WD_API, COMMONS_API, UA  # noqa: E402
from sonde_photos_titres import nom_usage                                          # noqa: E402

LARGEUR, HAUTEUR = 960, 540
# Le logo n'occupe pas toute la vignette : une marge le fait lire comme une
# plaque de marque plutot que comme une image tronquee.
PART_L, PART_H = 0.66, 0.52


def logo_de(qid):
    """Fichier Commons porté par P154 (logo) pour cette entité."""
    try:
        d = _get(WD_API, {"action": "wbgetentities", "format": "json",
                          "ids": qid, "props": "claims"})
    except Exception:
        return None
    claims = ((d.get("entities") or {}).get(qid) or {}).get("claims") or {}
    for c in claims.get("P154", []):
        val = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(val, str):
            return val
    return None


def infos_logo(fichier):
    """URL de rendu, licence et auteur. Pas de plancher de taille : un logo
    vectoriel n'a pas de dimension propre, Commons le rend à la demande."""
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "titles": "File:" + fichier, "prop": "imageinfo",
                               "iiprop": "url|extmetadata|size", "iiurlwidth": "1200"})
    except Exception:
        return None
    page = next(iter((d.get("query", {}).get("pages") or {}).values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    if not info:
        return None
    meta = info.get("extmetadata") or {}
    lic = (meta.get("LicenseShortName") or {}).get("value", "?")
    fam = famille_licence(lic + " " + (meta.get("UsageTerms") or {}).get("value", ""))
    if fam == "autre":
        return None
    return {"fichier": fichier,
            # thumburl rend le SVG en PNG : c'est ce qu'on veut, PIL ne lit pas le SVG.
            "url": info.get("thumburl") or info.get("url"),
            "page": info.get("descriptionurl", ""),
            "licence": lic, "famille": fam}


def _luminosite(im):
    """Luminosité moyenne des pixels NON transparents.

    Sur la moyenne globale, un logo noir entouré de transparence passerait pour
    clair et l'on choisirait un fond blanc, sur lequel il disparaitrait.
    """
    from PIL import Image
    rgba = im.convert("RGBA")
    gris = rgba.convert("L")
    alpha = rgba.getchannel("A")
    total = somme = 0
    for g, a in zip(gris.getdata(), alpha.getdata()):
        if a > 40:
            somme += g
            total += 1
    return (somme / total) if total else 128


def preparer_logo(brut, chemin):
    """Logo entier, centré, sur un fond qui le fait ressortir."""
    from PIL import Image
    im = Image.open(io.BytesIO(brut))
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    logo_clair = _luminosite(im) > 128
    fond = (18, 20, 26) if logo_clair else (242, 243, 246)
    toile = Image.new("RGB", (LARGEUR, HAUTEUR), fond)

    e = min(LARGEUR * PART_L / im.width, HAUTEUR * PART_H / im.height)
    nl, nh = max(1, int(im.width * e)), max(1, int(im.height * e))
    im = im.resize((nl, nh), Image.LANCZOS)
    toile.paste(im, ((LARGEUR - nl) // 2, (HAUTEUR - nh) // 2), im)
    toile.save(chemin, "JPEG", quality=88, optimize=True, progressive=True)
    # On renvoie la couleur du FOND, pas celle du logo : c'est le fond qu'on
    # decrit dans le rapport, et confondre les deux le rendait illisible.
    return os.path.getsize(chemin), "sombre" if logo_clair else "clair"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/logos")
    ap.add_argument("--tickers", default="")
    ap.add_argument("--tous", action="store_true",
                    help="toutes les fiches sans photo ou illustrées par un site")
    a = ap.parse_args()

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})
    leg = {}
    if os.path.exists("assets/titres/LEGENDES.json"):
        leg = json.load(open("assets/titres/LEGENDES.json", encoding="utf-8"))

    if a.tickers:
        cibles = [t.strip() for t in a.tickers.split(",") if t.strip()]
    elif a.tous:
        # Celles qui n'ont rien, et celles dont l'image est un site : jamais
        # celles qui montrent deja un objet fabrique, ou le logo serait un recul.
        cibles = sorted([t for t in noms if t not in leg]
                        + [t for t, v in leg.items() if v.get("type") != "produit"])
    else:
        raise SystemExit("préciser --tickers ou --tous")
    inconnus = [t for t in cibles if t not in noms]
    if inconnus:
        raise SystemExit(f"tickers absents de l'univers : {inconnus}")

    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(cibles)} sociétés\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        qid, label = entite(nom)
        fichier = logo_de(qid) if qid else None
        inf = infos_logo(fichier) if fichier else None
        if not inf:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} {nom[:22]:22s} "
                  f"{'(pas de logo)' if qid else '(entité introuvable)'}", flush=True)
            time.sleep(0.25)
            continue
        try:
            req = urllib.request.Request(inf["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                brut = r.read()
            inf["poids"], inf["fond"] = preparer_logo(brut, os.path.join(a.sortie, f"{tk}.jpg"))
        except Exception as e:
            print(f"[{i:3d}/{len(cibles)}] {tk:10s} ✗ {type(e).__name__}", flush=True)
            time.sleep(0.25)
            continue
        inf.update({"qid": qid, "label": label, "nom": nom})
        rapport[tk] = inf
        print(f"[{i:3d}/{len(cibles)}] {tk:10s} {label[:20]:20s} {inf['famille']:5s} "
              f"{inf['licence'][:18]:18s} fond {inf['fond']:6s} {inf['fichier'][:34]}", flush=True)
        time.sleep(0.25)

    with open("photos_logos.json", "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"LOGOS RÉCUPÉRÉS : {len(rapport)}/{len(cibles)} sociétés")
    fams = {}
    for v in rapport.values():
        fams[v["famille"]] = fams.get(v["famille"], 0) + 1
    print("par famille de licence :", fams)


if __name__ == "__main__":
    main()
