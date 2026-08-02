#!/usr/bin/env python3
"""Activité illustrée d'un titre : le maillon dont il relève, sinon son secteur.

POURQUOI PAS UNE PHOTO PAR SOCIÉTÉ. La sonde du 02/08 a mesuré ce que donne une
recherche automatique de photos libres société par société : 43 % des
correspondances sont hors sujet, et les erreurs sont du type le plus grave pour
un site financier — le siège d'Asahi Mutual Life pour Shin-Etsu, une caserne de
pompiers pour Applied Materials, une photo d'Apollo 14 pour ASE Group. Publier
le bâtiment d'une entreprise sur la fiche d'une autre est un fait faux, pas une
imperfection esthétique.

L'illustration porte donc sur l'ACTIVITÉ, pas sur la société : une photo de
salle blanche illustre le maillon « fonderie et packaging », et la fiche le dit
en légende. C'est vrai par construction, quel que soit le titre affiché, et
c'est en prime pédagogique — l'image rappelle où le titre se situe dans la
chaîne. Une photo de société vérifiée à la main peut ensuite la remplacer au
cas par cas.

Ce module est la source unique de la correspondance titre → activité. Il est lu
par l'outil de récolte (quelles photos chercher) et par le screener (quelle clé
publier pour le front).
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import themes                                                    # noqa: E402

# Secteurs publiés par le screener → clé d'illustration. Les titres qui
# relèvent d'un maillon n'arrivent jamais ici : c'est le filet pour le reste
# du top 30 (éditeurs de logiciels, santé, consommation…).
SECTEURS = {
    "Technologie":   "tech-logiciel",
    "Médias & IA":   "medias",
    "Finance":       "finance-generale",
    "Industrie":     "industrie",
    "Santé":         "sante",
    "Conso. cycl.":  "conso",
    "Conso. base":   "conso",
    "Services pub.": "energie-reseau",
    "Énergie":       "energie-reseau",
    "Matériaux":     "materiaux",
    "Immobilier":    "immobilier",
}

# Requêtes Commons par activité. Mêmes principes que pour les watchlists :
# des objets photographiables, plusieurs formulations, et pour les sujets
# techniques on vise les laboratoires fédéraux américains dont les images sont
# dans le domaine public par statut.
REQUETES = {
    # ── Maillons infra-IA ────────────────────────────────────────────────
    "compute":        ["computer processor die shot", "microprocessor chip macro",
                       "CPU integrated circuit closeup", "graphics card circuit board"],
    "fonderie":       ["cleanroom semiconductor fabrication", "silicon wafer",
                       "photolithography equipment cleanroom", "wafer inspection microscope"],
    "memoire":        ["DRAM memory module", "computer memory chips",
                       "hard disk drive platter", "NAND flash package"],
    "reseau":         ["fiber optic cables bundle", "optical fiber connectors",
                       "network switch rack ports", "submarine cable landing"],
    "serveurs":       ["Oak Ridge supercomputer Summit", "Argonne supercomputer",
                       "NASA supercomputer facility", "data center server room aisle"],
    "cloud":          ["NERSC data center", "server room network cabling",
                       "computer room raised floor", "mainframe computer room"],
    "energie":        ["electrical substation transformer high voltage",
                       "high voltage transmission towers", "power plant turbine hall",
                       "cooling towers power station"],
    # ── Familles financials ──────────────────────────────────────────────
    "banques":        ["bank vault door", "bank counter interior historic",
                       "banking hall interior", "bank building facade columns"],
    "assurance":      ["insurance company building", "actuarial ledger book",
                       "fire insurance mark plaque", "lloyd's building london"],
    "paiements":      ["credit card magnetic stripe", "payment terminal card reader",
                       "cash register machine", "cheque clearing house"],
    "gestion":        ["stock certificate engraving", "portfolio ledger book",
                       "financial documents desk", "safe deposit boxes"],
    "peages":         ["stock ticker tape machine", "stock exchange display board",
                       "financial newspaper stock listings", "exchange building interior"],
    # ── Secteurs, pour les titres hors thèmes ────────────────────────────
    "tech-logiciel":  ["computer keyboard closeup", "punched card computing",
                       "computer terminal screen code", "circuit board macro"],
    "medias":         ["television studio camera", "film reel projector",
                       "broadcast control room", "radio transmitter tower"],
    "finance-generale": ["stock exchange trading floor", "financial district skyline",
                         "banking hall interior"],
    "industrie":      ["factory production line machinery", "industrial turbine",
                       "steel mill interior", "freight locomotive"],
    "sante":          ["laboratory microscope research", "pharmaceutical production line",
                       "medical imaging scanner", "laboratory glassware"],
    "conso":          ["supermarket shelves products", "grocery store aisle",
                       "bottling plant production line"],
    "energie-reseau": ["power grid pylons", "nuclear power plant cooling towers",
                       "electrical substation"],
    "materiaux":      ["chemical plant pipes", "industrial gas tanks", "refinery towers"],
    "immobilier":     ["data center building exterior", "office tower facade",
                       "warehouse interior racking"],
}

# Libellé lisible affiché en légende sous l'image.
LIBELLES = {
    "compute":        "Compute · processeurs et accélérateurs",
    "fonderie":       "Fonderie, équipement et packaging",
    "memoire":        "Mémoire et stockage",
    "reseau":         "Réseau et interconnexion optique",
    "serveurs":       "Serveurs et centres de données",
    "cloud":          "Plateformes et cloud",
    "energie":        "Énergie et refroidissement",
    "banques":        "Banques et bilans",
    "assurance":      "Assurance et courtage",
    "paiements":      "Réseaux de paiement",
    "gestion":        "Gestion d'actifs",
    "peages":         "Indices, notation et places de marché",
    "tech-logiciel":  "Technologie et logiciel",
    "medias":         "Médias et plateformes",
    "finance-generale": "Finance",
    "industrie":      "Industrie",
    "sante":          "Santé",
    "conso":          "Consommation",
    "energie-reseau": "Énergie et réseaux",
    "materiaux":      "Matériaux",
    "immobilier":     "Immobilier et centres de données",
}

# Maillon (libellé dans themes.py) → clé d'activité. On dérive par mot-clé
# plutôt que par correspondance exacte : renommer un maillon pour le rendre
# plus lisible ne doit pas casser silencieusement les illustrations.
# ORDRE SIGNIFIANT : le premier mot trouvé gagne. « paiement » DOIT passer avant
# « réseau », sinon « Flux · réseaux de paiement » est capturé par le maillon
# optique et Visa hériterait d'une photo de fibre. Les libellés se recouvrent,
# la table doit aller du plus spécifique au plus général.
_MOTS = [
    ("paiement", "paiements"), ("compute", "compute"), ("fonderie", "fonderie"),
    ("mémoire", "memoire"), ("réseau", "reseau"), ("serveurs", "serveurs"),
    ("hyperscalers", "cloud"), ("énergie", "energie"), ("banques", "banques"),
    ("assurance", "assurance"), ("gestion", "gestion"), ("péages", "peages"),
]


def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"[̀-ͯ]", "", s)


def cle_maillon(label):
    """Clé d'activité d'un libellé de maillon, ou None s'il n'en évoque aucune."""
    n = _norm(label)
    for mot, cle in _MOTS:
        if _norm(mot) in n:
            return cle
    return None


def par_ticker():
    """ticker → clé d'activité, pour tous les titres déclarés par un maillon."""
    out = {}
    for th in themes.THEMES_CURES:
        for m in th.get("maillons", []):
            cle = cle_maillon(m["label"])
            if not cle:
                continue
            for t in m["tickers"]:
                out.setdefault(t, cle)      # premier maillon gagnant, ordre = chaîne
    return out


def activite(ticker, secteur, _cache={}):
    """Activité d'un titre : son maillon, sinon son secteur, sinon rien."""
    if not _cache:
        _cache.update(par_ticker())
    return _cache.get(ticker) or SECTEURS.get(secteur or "")


if __name__ == "__main__":
    m = par_ticker()
    from collections import Counter
    print(f"{len(m)} titres rattachés à un maillon")
    for cle, n in Counter(m.values()).most_common():
        print(f"  {cle:18s} {n:3d}  {LIBELLES[cle]}")
    manquantes = [c for c in LIBELLES if c not in REQUETES]
    assert not manquantes, f"activités sans requête : {manquantes}"
    print(f"\n{len(REQUETES)} activités à illustrer, toutes pourvues d'une requête")
