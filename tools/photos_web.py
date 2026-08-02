#!/usr/bin/env python3
"""Septième passe : le web ouvert, images non libres de droit assumées.

DÉCISION DU PROPRIÉTAIRE DU DÉPÔT. Les six passes précédentes n'acceptaient que
le domaine public, CC0, CC-BY et CC-BY-SA. Elles ont couvert 57 fiches sur 104 ;
pour les 47 autres, le corpus libre est vide, non par défaut d'interrogation
mais parce que personne n'a jamais photographié sous licence libre un testeur
Advantest ou une baie CoreWeave. Le propriétaire du dépôt a explicitement
autorisé les images dont la licence n'est pas établie. Cet outil met en oeuvre
cette décision ; il ne la prend pas.

CE QUI SUIT N'EST PAS UNE LICENCE. Aucune des images rapportées ici n'est libre
de droit. On réduit le risque au lieu de le nier, par trois choix :

1. ON VISE LA SOURCE OFFICIELLE. Une photo publiée par la société dans son
   espace presse ou sa fiche produit est mise en ligne pour que des tiers
   illustrent des articles la concernant, ce qui est exactement notre usage.
   La photo d'un particulier reprise sans son accord est une contrefaçon envers
   un auteur identifiable. Les deux sont « non libres », le risque n'a rien à
   voir, et seul le premier cas est retenu : le domaine de la page doit
   appartenir à la société.
2. ON TRACE TOUT. Page d'origine, domaine, date de récupération et conditions
   annoncées sont consignés pour chaque image, et publiés dans CREDITS.md. Une
   demande de retrait doit pouvoir être honorée en une minute.
3. ON CRÉDITE. La fiche affiche « Photo : <société> » sous la légende, comme
   elle affiche déjà le crédit des images sous licence à attribution.

CONTRAINTE TECHNIQUE. Les sites d'entreprise renvoient 403 aux clients qui ne
ressemblent pas à un navigateur, exactement comme Openverse. Même réponse que
là-bas : le gabarit « Mozilla/5.0 (compatible; … ) », qui satisfait le filtre
de préfixe sans prétendre être Chrome.

POURQUOI ON EXPLORE AU LIEU DE LIRE UNE PAGE. Le premier passage ne lisait que
l'accueil et une page produit, et n'en tirait que les trois premières images :
il ramenait donc des bandeaux marketing à texte incrusté et des photos
d'illustration achetées. Or les vraies images de métier, une salle blanche, un
chantier, une équipe au travail, sont plus bas dans le site, dans « nos
métiers », « salle de presse » ou « nous rejoindre ». On suit donc quelques
liens internes dont l'adresse promet ce genre de page, et l'on ramasse
largement pour que l'examen visuel ait de quoi choisir. Les garde-fous ne
changent pas : même domaine, et rien n'est publié sans être regardé.

Usage : python3 tools/photos_web.py [--limite N] [--par-societe N]
"""
import argparse
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_produits import score_nom, prepare                       # noqa: E402

UA = ("Mozilla/5.0 (compatible; SignalWatchlists/1.0; "
      "+https://github.com/Kosmos-7/Signal)")

# Société → pages de son propre site où chercher un visuel. Le domaine sert de
# garde-fou : on ne retient une image que si elle est servie depuis le site de
# la société, ce qui écarte les photos de tiers reprises dans la page.
PAGES = {}
if os.path.exists("tools/photos_web_pages.json"):
    PAGES = json.load(open("tools/photos_web_pages.json", encoding="utf-8"))

MIN_OCTETS = 25_000          # sous ce poids c'est un logo ou une icône
MIN_L, MIN_H = 700, 380      # sous ces dimensions, inutilisable en 960x540
PAGES_MAX = 9                # pages visitees par societe, politesse et budget
IMAGES_MAX = 45              # URLs d'images retenues avant telechargement
IGNORE = re.compile(r"(logo|icon|favicon|sprite|placeholder|avatar|badge|"
                    r"flag|arrow|bullet|spacer|pixel)", re.I)

# Adresses de pages qui, sur un site d'entreprise, contiennent les photos de
# metier. « career » et « press » valent mieux que l'accueil, dont le visuel est
# presque toujours un bandeau avec du texte incruste.
PROMETTEUR = re.compile(
    r"(what-we-do|nos-metiers|our-business|our-work|operations|solutions|"
    r"products|technolog|newsroom|press|media|news|stories|about|company|"
    r"who-we-are|career|jobs|join|sustainab|responsib|innovation|research|"
    r"manufactur|facilit|network|data-cent|datacenter)", re.I)


def lire(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*",
        "Accept-Language": "en,fr;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), r.headers.get("Content-Type", "")


def liens_internes(page_html, base, domaine):
    """Liens du site dont l'adresse promet une page de metier."""
    t = page_html.decode("utf-8", "replace")
    out, vus = [], set()
    for m in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)["\']', t, re.I):
        u = urllib.parse.urljoin(base, html.unescape(m.group(1)))
        p = urllib.parse.urlparse(u)
        if p.scheme not in ("http", "https") or domaine not in p.netloc:
            continue
        if re.search(r"\.(pdf|zip|docx?|xlsx?|mp4|jpe?g|png)$", p.path, re.I):
            continue
        u = u.split("?")[0]
        if u in vus or not PROMETTEUR.search(p.path):
            continue
        vus.add(u)
        out.append(u)
    return out


def images_de(page_html, base, domaine, cdn=()):
    """URLs d'images de la page, celles du domaine de la société d'abord.

    On lit og:image en priorité : c'est le visuel que la société a elle-même
    désigné comme représentatif de la page, donc son meilleur candidat.
    """
    t = page_html.decode("utf-8", "replace")
    trouve, vus = [], set()

    for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content='
                         r'["\']([^"\']+)["\']', t, re.I):
        u = urllib.parse.urljoin(base, html.unescape(m.group(1)))
        if u not in vus:
            vus.add(u)
            trouve.append((100, u))          # og:image passe devant tout

    for m in re.finditer(r'<img[^>]+?(?:data-src|srcset|src)=["\']([^"\']+)["\']',
                         t, re.I):
        brut = html.unescape(m.group(1)).split()[0].split(",")[0]
        if not re.search(r"\.(jpe?g|png|webp)", brut, re.I) or IGNORE.search(brut):
            continue
        u = urllib.parse.urljoin(base, brut)
        if u in vus:
            continue
        vus.add(u)
        trouve.append((score_nom(u), u))

    # Une image servie par un tiers n'a pas la légitimité qu'on cherche :
    # publiée par la société, sur le site de la société. Exception nommée : de
    # nombreux sites servent leurs propres visuels depuis le CDN de leur
    # constructeur (CoreWeave depuis website-files.com). Refuser ce cas revenait
    # à écarter les photos que la société publie bel et bien elle-même ; on
    # autorise donc les domaines explicitement déclarés pour elle, et eux seuls.
    permis = (domaine,) + tuple(cdn)
    trouve = [(s, u) for s, u in trouve
              if any(d in urllib.parse.urlparse(u).netloc for d in permis)]
    trouve.sort(key=lambda x: -x[0])
    return [u for _, u in trouve]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/web")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=6)
    ap.add_argument("--tickers", default="",
                    help="tickers a traiter, separes par des virgules, meme "
                         "s'ils sont deja illustres")
    a = ap.parse_args()

    if not PAGES:
        print("tools/photos_web_pages.json absent : rien à faire.")
        return

    deja = set()
    if os.path.exists("assets/titres/LEGENDES.json"):
        deja = set(json.load(open("assets/titres/LEGENDES.json", encoding="utf-8")))
    # « _lisez_moi » est de la documentation, pas une société. Sans ce filtre on
    # itère dessus et l'on meurt d'un TypeError au dernier tour, après avoir
    # fait tout le travail et avant d'avoir écrit le rapport.
    cibles = [t for t in sorted(PAGES) if not t.startswith("_") and t not in deja]
    if a.tickers:
        # Repasse ciblee, y compris sur des fiches deja illustrees : c'est le
        # seul moyen de chercher mieux que ce qu'on a deja.
        vises = [t.strip() for t in a.tickers.split(",") if t.strip()]
        inconnus = [t for t in vises if t not in PAGES]
        if inconnus:
            raise SystemExit(f"aucune page connue pour : {inconnus}")
        cibles = vises
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(cibles)} sociétés, sources officielles\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        entrees = PAGES[tk]
        domaine = entrees[0]["domaine"]
        cdn = entrees[0].get("cdn", [])
        # File d'exploration : les pages fournies d'abord, puis les liens
        # internes qu'elles offrent et dont l'adresse promet une page de metier.
        file = [e["page"] for e in entrees]
        vues, urls_images, page_de = set(), [], {}
        while file and len(vues) < PAGES_MAX and len(urls_images) < IMAGES_MAX:
            page = file.pop(0)
            if page in vues:
                continue
            vues.add(page)
            try:
                corps, _ = lire(page)
            except urllib.error.HTTPError as e:
                print(f"      ✗ {page[:62]} HTTP {e.code}", flush=True)
                continue
            except Exception as e:
                print(f"      ✗ {page[:62]} {type(e).__name__}", flush=True)
                continue
            for u in images_de(corps, page, domaine, cdn):
                if u not in page_de:
                    page_de[u] = page
                    urls_images.append(u)
            # On n'explore qu'a partir des pages fournies a la main : suivre les
            # liens des liens ferait deriver vers le reste du site.
            if page in [e["page"] for e in entrees]:
                for u in liens_internes(corps, page, domaine):
                    if u not in vues and len(file) < PAGES_MAX * 2:
                        file.append(u)
            time.sleep(0.4)

        gardes = []
        for u in urls_images:
            if len(gardes) >= a.par_societe:
                break
            try:
                brut, ctype = lire(u)
            except Exception:
                continue
            if len(brut) < MIN_OCTETS or "image" not in ctype:
                continue
            try:
                from PIL import Image
                dims = Image.open(io.BytesIO(brut)).size
            except Exception:
                continue
            # Une image plus petite que la vignette finale ne peut qu'etre
            # etiree : autant la refuser tout de suite.
            if dims[0] < MIN_L or dims[1] < MIN_H:
                continue
            chemin = os.path.join(a.sortie, f"{tk}_{len(gardes)}.jpg")
            try:
                poids = prepare(brut, chemin)
            except Exception:
                continue
            e0 = entrees[0]
            gardes.append({"image": u, "page": page_de.get(u, ""), "domaine": domaine,
                           "dimensions": f"{dims[0]}x{dims[1]}",
                           "conditions": e0.get("conditions", "non établies"),
                           "credit": e0.get("credit", ""), "poids": poids})
            time.sleep(0.25)

        if gardes:
            rapport[tk] = {"candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(vues)} pages, "
                  f"{len(urls_images):3d} images vues, {len(gardes)} gardees  "
                  f"{gardes[0]['image'][:52]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(vues)} pages, "
                  f"{len(urls_images):3d} images vues, rien d'exploitable", flush=True)

    with open("photos_web.json", "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"IMAGES RÉCUPÉRÉES : {len(rapport)}/{len(cibles)} sociétés")
    print("Aucune n'est libre de droit. Provenance consignée pour chacune.")


if __name__ == "__main__":
    main()
