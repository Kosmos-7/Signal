#!/usr/bin/env python3
"""Actualités — un post quotidien factuel, un post hebdomadaire d'analyse.

LA RÈGLE QUI GOUVERNE TOUT : on n'invente jamais rien, on n'interprète pas.
Elle ne s'applique pas par une consigne de politesse dans un prompt, mais par
l'architecture : le modèle ne reçoit QUE des dépêches réelles (Finnhub /news,
le même flux que l'analyse hebdomadaire du portefeuille) et chaque section du
post doit citer les dépêches dont elle sort. Une section sans source est
rejetée à la validation, pas corrigée.

LES DEUX GENRES, ET POURQUOI ILS N'ONT PAS LES MÊMES RÈGLES.
  · Le post QUOTIDIEN est factuel : ce qui s'est passé, qui a dit quoi, ce qui
    a bougé. Aucun conseil, aucune prédiction, aucune mention de Signal ni du
    portefeuille. Publié le matin des jours de bourse, il couvre la veille et
    la nuit (clôture US, Asie). Le TON, lui, est léger (décision propriétaire
    du 03/08/2026) : l'humour fluidifie la lecture, il ne porte que sur les
    formulations, jamais sur l'exactitude, et jamais aux dépens d'une personne.
    Limite ajoutée le jour même, sur retour propriétaire : aucun humour sur
    les sujets graves (guerre, menace militaire, catastrophe, victimes), ces
    sections gardent le ton sobre, titre compris.
  · Le post HEBDO est l'analyse de l'IA sur son portefeuille, déplacée depuis
    la page Portefeuille. C'est de l'interprétation PAR NATURE, assumée et
    étiquetée comme telle. Il n'est pas généré ici : il est MATÉRIALISÉ depuis
    portfolio.json, la seule source de vérité, pour que l'archive persiste
    quand portfolio.json passe à la semaine suivante.

LE JOUR CREUX. Quand Finnhub renvoie trop peu de dépêches (jour férié, panne),
la tentation est de meubler. Règle inverse : moins de MIN_DEPECHES dépêches
exploitables, pas de post du tout et sortie en erreur — le CI devient rouge,
la page sert les posts existants. Jamais de demi-post.

LA REDITE, ET POURQUOI ELLE N'ÉTAIT PAS UN BOGUE MAIS UN DÉFAUT DE CONCEPTION.
Constat propriétaire du 16/08/2026 : quatre matins d'affilée, quatre titres qui
disaient la même chose — « L'or flambe, l'Iran conditionne Ormuz », « l'or en
forme et le pétrole surveille l'Iran », « Pétrole et or en hausse », « l'or
brille ». Les CORPS, eux, étaient variés (Intel, CoreWeave, Verizon, Meta,
Cardinal Health) : c'est le titre, et lui seul, qui retombait chaque jour sur la
même couche. Trois mécanismes l'y poussaient, aucun n'était accidentel.
  · Le prompt demandait « le fait dominant du jour ». Le fait dominant d'un
    marché est une histoire LENTE : l'or monte pendant trois semaines, l'Iran
    négocie pendant deux mois. Le fait dominant d'aujourd'hui est celui d'hier.
  · Le tableau des clôtures est sous les yeux du modèle, et ses lignes matières
    premières bougent mécaniquement plus que les indices (l'or fait 1,5 % quand
    le S&P fait 0,3 %). « Cite les deux ou trois chiffres qui portent l'histoire
    du jour » désignait donc l'or et le brut TOUS LES MATINS, par construction.
  · Rien ne se souvenait de la veille. Les photos, elles, avaient déjà leur
    mémoire (`photos_deja_utilisees`) et jusqu'à un détecteur de quasi-doublons,
    précisément parce que la répétition visuelle avait été vue et corrigée. Le
    texte n'avait jamais reçu le même traitement.
Le correctif est de même nature que le reste du fichier : structurel, pas une
consigne de politesse. Le modèle reçoit les titres déjà parus ET la liste des
mots qui les portaient, un garde relit son titre, et les dépêches déjà citées
sont écartées du tirage. Une seule prudence, qui prime sur tout : la redite
n'est JAMAIS bloquante. Un post honnête qui répète vaut mieux que pas de post,
et un vrai titre (décrochage, record) ne se sacrifie pas pour éviter un mot.

IMMUABILITÉ. Un post publié ne se régénère pas, comme l'historique du
portefeuille : le fichier existant fait échouer l'écriture (sauf --force,
réservé au jour même). L'index, lui, se RECONSTRUIT à chaque run depuis les
fichiers de posts : il ne peut pas diverger de ce qu'il liste.

PHOTO. Cherchée automatiquement sur Commons selon le sujet du post (décision
propriétaire du 03/08/2026 — la doctrine de revue humaine des photos de fiches
ne s'applique pas ici). Garde-fous : licences libres uniquement, provenance
complète enregistrée dans le post, et un post sans photo est un post valide.

Usage :
    python3 tools/actualites.py                 # post du jour + hebdo si absent
    python3 tools/actualites.py --hebdo-seulement
    python3 tools/actualites.py --sans-photo --force
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DOSSIER = "actualites"
POSTS = os.path.join(DOSSIER, "posts")
PHOTOS = os.path.join(DOSSIER, "photos")
INDEX = os.path.join(DOSSIER, "index.json")

MIN_DEPECHES = 5          # en dessous : pas de post, échec explicite
MAX_DEPECHES = 14         # au-delà : le prompt se dilue
MAX_PAR_SOURCE = 3        # anti écho de chambre, même logique que get_macro_news
MODELE = "claude-sonnet-4-6"

# Sujet du post → requêtes Commons pour l'illustration. Le modèle choisit le
# sujet, la table choisit les requêtes : l'automatisation est bornée par une
# liste écrite à la main, pas par une recherche libre.
# VIVIER : SIX REQUÊTES PAR SUJET, PAS TROIS. Cause démontrée du post du 07/08
# publié sans photo : cinq matins d'affilée sur le sujet « marches » (3, 4, 5,
# 6 et 7 août). Les trois requêtes avaient donné leurs bonnes images les quatre
# premiers jours ; le cinquième, la mémoire des photos parues les écartait
# toutes, elles ET leurs quasi-doublons, et il ne restait que du fond de panier
# que `infos()` a refusé (trop petit ou licence non libre). Un sujet qui domine
# quatre séances de suite n'est pas un cas rare : c'est la situation NORMALE
# d'un marché qui vit une même histoire une semaine durant. Trois requêtes ne
# tiennent pas la semaine, six oui.
SUJETS = {
    "banques-centrales": ["Federal Reserve Eccles Building",
                          "European Central Bank Frankfurt tower",
                          "Bank of Japan headquarters",
                          "Bank of England Threadneedle Street",
                          "central bank press conference podium",
                          "Federal Open Market Committee room"],
    "marches":           ["New York Stock Exchange trading floor",
                          "stock exchange display board",
                          "Wall Street street sign",
                          "London Stock Exchange Paternoster Square",
                          "Tokyo Stock Exchange Arrows",
                          "Frankfurt Boerse trading hall"],
    "resultats":         ["corporate skyline La Defense",
                          "office towers financial district",
                          "annual general meeting hall",
                          "Canary Wharf towers London",
                          "Manhattan Midtown office towers",
                          "shareholders meeting auditorium"],
    "tech":              ["data center server racks",
                          "semiconductor wafer cleanroom",
                          "electronics assembly line",
                          "silicon wafer inspection microscope",
                          "network cabling data centre aisle",
                          "robotic arm factory automation"],
    "energie":           ["oil refinery at dusk",
                          "LNG tanker ship",
                          "high voltage transmission lines",
                          "offshore wind farm turbines sea",
                          "solar power plant panels desert",
                          "oil drilling rig platform"],
    "geopolitique":      ["container port cranes",
                          "cargo ship containers sea",
                          "customs border trucks",
                          "Strait of Hormuz tanker",
                          "Suez Canal ship transit",
                          "freight railway container yard"],
    "macro":             ["supermarket shelf prices",
                          "construction site tower cranes",
                          "shipping containers stacked port",
                          "employment office queue",
                          "housing construction suburb aerial",
                          "warehouse logistics forklift pallets"],
}

# Un post quotidien ne recommande rien. Ces deux racines n'ont aucune raison
# honnête d'apparaître dans un compte rendu factuel.
INTERDITS = ("recommand", "conseill")

# ── Mémoire éditoriale : ce que le lecteur a déjà lu ─────────────────────────
# Les trois nombres qui règlent l'anti-redite. MEMOIRE : combien de titres parus
# le modèle voit. REDITE_FENETRE / REDITE_MIN : un mot est « épuisé » quand il a
# porté REDITE_MIN des REDITE_FENETRE derniers titres — deux fois en trois
# matins, ce n'est plus une nouvelle, c'est le décor. La fenêtre est courte
# exprès : une histoire qui revient une semaine après avoir disparu est
# redevenue une information.
MEMOIRE = 5
REDITE_FENETRE = 3
REDITE_MIN = 2

# LES FAMILLES DE MOTS, ÉCRITES À LA MAIN, COMME LA TABLE DES SUJETS. Sans
# elles, le garde s'esquive au synonyme : interdire « or » ferait écrire « le
# métal jaune », interdire « pétrole » ferait écrire « le brut », et le lecteur
# lirait le même titre en croyant en lire un autre. On ne cherche pas à couvrir
# la langue, seulement les poignées d'expressions qui reviennent réellement dans
# un point marchés. Forme canonique : libellé lisible, puis ce qui la dit
# autrement (sans accents, en minuscules : la comparaison se fait après
# `_canoniser`).
FAMILLES = {
    "or":         ("l'or",        ("metal jaune", "once d or", "lingot")),
    "petrole":    ("le pétrole",  ("or noir", "brent", "wti", "baril", "brut")),
    "iran":       ("l'Iran",      ("teheran", "ormuz", "hormuz", "iranienne",
                                   "iranien", "perse")),
    "wallstreet": ("Wall Street", ("wall street", "s&p 500", "s&p", "nasdaq",
                                   "dow jones", "dow")),
    "fed":        ("la Fed",      ("reserve federale", "powell", "fomc")),
    "inflation":  ("l'inflation", ("prix a la consommation", "hausse des prix",
                                   "cpi")),
    "bitcoin":    ("le bitcoin",  ("cryptomonnaie", "crypto", "btc")),
    "dollar":     ("le dollar",   ("billet vert", "greenback")),
}
# Le remplacement se fait du plus long au plus court : « dow jones » avant
# « dow », sinon la moitié de l'expression survit et ne se reconnaît plus.
_VARIANTES = sorted(((v, c) for c, (_, vs) in FAMILLES.items() for v in vs),
                    key=lambda x: -len(x[0]))

# Grammaire pure : ces mots sont dans tous les titres et ne disent rien d'aucun.
# Les verbes de mouvement (« monte », « recule », « hésite ») n'y sont PAS, et
# c'est voulu : trois matins de « hausse » sont aussi une redite, même quand le
# sujet change.
VIDES = frozenset("""
au aux avec ce ces cet cette comme dans de des du elle en encore entre est et
etre eux il ils la le les leur leurs lui ma mais me mes moins mon ne nos notre
nous on ont ou par pas plus pour qu que qui sa sans se ses si son sont sous sur
ta tes ton tout toute toutes tous un une vos votre vous y
""".split())


def _sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def _canoniser(texte):
    """Un titre ramené à sa langue de comparaison : sans accents, sans
    apostrophes, les familles réduites à leur forme unique."""
    t = re.sub(r"[’'`]", " ", _sans_accents(texte))
    for variante, canon in _VARIANTES:
        t = re.sub(rf"(?<![\w&]){re.escape(variante)}(?![\w&])", canon, t)
    return t


def mots_titre(titre):
    """Les mots d'un titre qui disent de QUOI il parle. Pure.

    Le pluriel tombe au-delà de quatre lettres (« marchés » et « marché » sont
    le même mot ; « taux » et « gaz » ne sont pas des pluriels).
    """
    out = set()
    for m in re.findall(r"[a-z0-9&]{2,}", _canoniser(titre)):
        if len(m) > 4 and m.endswith("s"):
            m = m[:-1]
        if m not in VIDES and not m.isdigit():
            out.add(m)
    return frozenset(out)


def mots_epuises(titres):
    """Les mots qui ont porté REDITE_MIN des REDITE_FENETRE derniers titres. Pure."""
    compte = {}
    for t in titres[:REDITE_FENETRE]:
        for m in mots_titre(t):
            compte[m] = compte.get(m, 0) + 1
    return frozenset(m for m, n in compte.items() if n >= REDITE_MIN)


def libelles(canons, titres):
    """Les mots épuisés dans la graphie que le lecteur a sous les yeux. Pure.

    On parle au modèle en français, pas en jetons internes : « le pétrole »,
    pas « petrole ». Les regroupements tiennent leur libellé de FAMILLES, les
    autres mots le tiennent des titres eux-mêmes, là où ils ont été écrits.
    """
    vus = {}
    for t in titres:
        for brut in re.findall(r"[^\W\d_]{2,}", t, re.UNICODE):
            for c in mots_titre(brut):
                vus.setdefault(c, brut)
    return [FAMILLES[c][0] if c in FAMILLES else vus.get(c, c)
            for c in sorted(canons)]


def defauts_redite(post, epuises, titres=()):
    """Ce que le titre re-sert des matins précédents. Pure, et NON BLOQUANT.

    Séparé de `valider_post` par principe, pas par commodité : les défauts de
    validation portent sur la VÉRITÉ du post (une section sans source, un
    chiffre inventé) et un post faux ne se publie pas. Une redite, elle, ne
    rend le post ni faux ni malhonnête, seulement ennuyeux. Elle vaut une
    seconde tentative, jamais un matin sans post.
    """
    if not isinstance(post, dict) or not epuises:
        return []
    revenus = mots_titre(post.get("titre") or "") & epuises
    if not revenus:
        return []
    return ["le titre reprend " + ", ".join(f"« {l} »" for l in libelles(revenus, titres))
            + " : ces mots portaient déjà les titres des derniers matins. Change "
              "d'ANGLE, pas de synonyme — un autre fait des dépêches, pas le même "
              "fait dit autrement"]


# ── Validation (pure, testable hors ligne) ───────────────────────────────────

def valider_post(p, nb_depeches, marches=None):
    """Liste des défauts d'un post quotidien produit par le modèle. Vide = bon."""
    d = []
    if not isinstance(p, dict):
        return ["le modèle n'a pas rendu un objet JSON"]
    titre, chapeau = p.get("titre") or "", p.get("chapeau") or ""
    if not (8 <= len(titre) <= 90):
        d.append(f"titre hors bornes ({len(titre)} car.)")
    if not (40 <= len(chapeau) <= 300):
        d.append(f"chapeau hors bornes ({len(chapeau)} car.)")
    if p.get("sujet") not in SUJETS:
        d.append(f"sujet inconnu : {p.get('sujet')!r}")
    sections = p.get("sections")
    if not isinstance(sections, list) or not (2 <= len(sections) <= 5):
        d.append("2 à 5 sections attendues")
        sections = []
    for i, s in enumerate(sections):
        # Un modèle qui rend une liste de CHAÎNES au lieu d'objets faisait planter
        # la validation sur .get() — or une exception ici n'est pas un défaut de
        # plus, c'est la perte de la seconde tentative et du post du jour.
        if not isinstance(s, dict):
            d.append(f"section {i} n'est pas un objet")
            continue
        if not (s.get("titre") and s.get("texte")):
            d.append(f"section {i} incomplète")
        src = s.get("sources")
        # C'est ICI que « on n'invente rien » devient structurel : une section
        # qui ne cite aucune dépêche n'a pas de provenance, donc pas de place.
        if not (isinstance(src, list) and src
                and all(isinstance(x, int) and 0 <= x < nb_depeches for x in src)):
            d.append(f"section {i} sans source valide")
    d += _defauts_marches(p, marches)
    texte_total = " ".join((s.get("texte") or "") + (s.get("titre") or "")
                           for s in sections if isinstance(s, dict)) \
        + titre + chapeau + (p.get("marches") or "")
    bas = texte_total.lower()
    for m in INTERDITS:
        if m in bas:
            d.append(f"vocabulaire de conseil détecté : « {m}… »")
    return d


# Un pourcentage écrit dans le commentaire de marché : « +1,79 % », « -0,022 pts »,
# « 2,3% », « 22 points de base ». Le signe est optionnel, la virgule française et
# le point sont acceptés. On capture l'unité : « 22 points de base » vaut 0,22 %,
# et comparer 22 à 0,22 rejetait une phrase juste.
_POURCENT = re.compile(
    r"([+-]?\d+(?:[.,]\d+)?)\s*(%|pts\b|points? de base\b|pb\b)")
_EN_POINTS = 0.01          # un point de base vaut un centième de point


def _tolerance(c):
    """Ce qu'on accepte comme arrondi autour d'une valeur connue.

    Cinq centièmes en plancher : le modèle a le droit d'écrire « 1,8 % » pour
    1,79 %. Plus un pour cent de la valeur, parce qu'un gros mouvement s'arrondit
    plus grossièrement — « 29,5 % » pour 29,45 % est du français correct, et
    un plancher fixe l'aurait refusé.
    """
    return max(0.05, abs(c) * 0.011)


def _defauts_marches(p, marches):
    """Le commentaire de marché ne cite que des chiffres qu'on a mesurés.

    C'EST LA MÊME RÈGLE QUE POUR LES SECTIONS, APPLIQUÉE À UN BLOC QUI N'A PAS
    DE DÉPÊCHE POUR LE TENIR. Une section sans source est rejetée parce que sa
    provenance est vérifiable ; le paragraphe `marches`, lui, commente NOTRE
    relevé, alors on vérifie la seule chose qui compte : que chaque pourcentage
    qu'il écrit existe dans le tableau affiché juste au-dessus. Un lecteur qui
    lit « le CAC a pris 2,3 % » sous une pastille à +0,61 % ne se demande pas
    lequel des deux a raison, il cesse de croire les deux.
    """
    attendu = bool(marches and marches.get("lignes"))
    brut = p.get("marches")
    # Même leçon qu'une section rendue en texte nu : une exception ici n'est pas
    # un défaut de plus, c'est la perte de la seconde tentative et du post.
    if brut is not None and not isinstance(brut, str):
        return [f"champ `marches` rendu en {type(brut).__name__}, pas en texte"]
    txt = (brut or "").strip()
    if not attendu:
        return ["champ `marches` rendu alors qu'aucun tableau n'a été fourni"] if txt else []
    if not (60 <= len(txt) <= 700):
        return [f"commentaire de marché hors bornes ({len(txt)} car.)"]
    lignes = list(marches["lignes"]) + ([marches["mouvement"]] if marches.get("mouvement") else [])
    connus = [l["variation"] for l in lignes]
    # LE NIVEAU D'UN TAUX S'ÉCRIT AUSSI AVEC UN « % », et le prompt demande
    # explicitement de citer les niveaux. « Le Treasury 10 ans termine à
    # 3,872 % » est donc une phrase PARFAITEMENT correcte que la première
    # version de ce garde rejetait, faute d'avoir mis les niveaux en pourcentage
    # dans les valeurs connues : deux rejets d'affilée, sortie en erreur, pas de
    # post du matin. Un garde qui refuse le juste coûte plus cher que pas de
    # garde du tout. Seuls les niveaux dont l'UNITÉ est « % » sont concernés :
    # un indice à 8 666,63 ne se lit jamais suivi d'un signe pourcent.
    connus += [l["valeur"] for l in lignes if l.get("unite") == "%"]
    d = []
    for brut, unite in _POURCENT.findall(txt):
        try:
            v = float(brut.replace(",", "."))
        except ValueError:                                     # noqa: PERF203
            continue
        if unite.startswith(("point", "pb")):
            v *= _EN_POINTS
        # LE SIGNE ÉCRIT ENGAGE, LE SIGNE SOUS-ENTENDU NON. « le Nasdaq recule
        # de 3,46 % » est juste pour une variation de -3,46 : c'est le VERBE qui
        # porte le signe, et exiger le « - » rejetterait du bon français. Mais
        # « +3,46 % » sur cette même ligne est une inversion, pas une tournure :
        # dès que le modèle écrit un signe, il doit être le bon. La première
        # version comparait tout en valeur absolue et laissait passer les deux.
        signe_ecrit = brut[0] in "+-"
        if not any(abs(v - c) <= _tolerance(c) or
                   (not signe_ecrit and abs(abs(v) - abs(c)) <= _tolerance(c))
                   for c in connus):
            d.append(f"chiffre « {brut} {unite} » absent du tableau mesuré")
    return d


def reconstruire_index():
    """L'index se dérive des fichiers de posts : aucune divergence possible."""
    entrees = []
    if os.path.isdir(POSTS):
        for f in os.listdir(POSTS):
            if not f.endswith(".json"):
                continue
            p = json.load(open(os.path.join(POSTS, f), encoding="utf-8"))
            entrees.append({k: p.get(k) for k in
                            ("id", "type", "date", "titre", "chapeau", "photo")})
    entrees.sort(key=lambda e: (e.get("date") or "", e.get("id") or ""), reverse=True)
    os.makedirs(DOSSIER, exist_ok=True)
    json.dump({"posts": entrees}, open(INDEX, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    return len(entrees)


def _quotidiens_recents(n):
    """Les n derniers posts quotidiens parus, du plus récent au plus ancien.

    ON FILTRE AVANT DE TRONQUER, comme `posts_sans_photo` a dû apprendre à le
    faire : trié à l'envers, « hebdo-2026-33 » passe devant « 2026-08-13 », et
    couper les n premiers FICHIERS rendrait une mémoire vide un lundi sur deux.
    """
    out = []
    for chemin in sorted(glob.glob(os.path.join(POSTS, "*.json")), reverse=True):
        try:
            d = json.load(open(chemin, encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            continue
        if d.get("type") == "quotidien":
            out.append(d)
        if len(out) >= n:
            break
    return out


def titres_recents(n=MEMOIRE):
    """Ce que le lecteur a lu ces derniers matins : date, titre, sujet."""
    return [{"date": d.get("date") or d.get("id"), "titre": d.get("titre") or "",
             "sujet": d.get("sujet")} for d in _quotidiens_recents(n)]


def depeches_deja_citees(n=REDITE_FENETRE):
    """Les URL des dépêches citées par les n derniers posts quotidiens.

    Le 11/08, « China is balancing Asia's crude oil demand by itself » a été
    publiée deux matins de suite : la fenêtre Finnhub de 24 h chevauche celle de
    la veille, et rien ne s'en souvenait. Une dépêche déjà servie n'est pas une
    information, c'est une archive. Une SUITE d'histoire, elle, arrive sous une
    autre URL et passe sans encombre : on n'écarte que le littéralement déjà lu.
    """
    return frozenset(s.get("url") for d in _quotidiens_recents(n)
                     for s in (d.get("sources") or []) if s.get("url"))


def ecrire_post(post, force=False):
    os.makedirs(POSTS, exist_ok=True)
    chemin = os.path.join(POSTS, f"{post['id']}.json")
    if os.path.exists(chemin) and not force:
        # L'immuabilité n'est pas une option de confort : une régénération
        # silencieuse réécrirait l'histoire sans que rien ne le signale.
        raise SystemExit(f"{chemin} existe déjà — un post publié ne se régénère pas "
                         f"(--force uniquement pour le jour même)")
    json.dump(post, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return chemin


# ── Dépêches ─────────────────────────────────────────────────────────────────

def trier_depeches(candidates, deja):
    """Les dépêches inédites d'abord, les déjà servies en RÉSERVE. Pure.

    La mémoire ne jette pas, elle déclasse. Écarter sèchement les dépêches de la
    veille pourrait faire passer un matin creux sous MIN_DEPECHES et annuler un
    post qui avait de quoi s'écrire : le remède serait pire que la redite. Elles
    ne remontent donc que si les inédites ne suffisent pas, et dans cet ordre.
    """
    inedites = [d for d in candidates if d["url"] not in deja]
    revues = [d for d in candidates if d["url"] in deja]
    if len(inedites) >= MIN_DEPECHES:
        return inedites[:MAX_DEPECHES], len(revues)
    return (inedites + revues[:MIN_DEPECHES - len(inedites)])[:MAX_DEPECHES], 0


def depeches_recentes(fenetre_h, deja=frozenset()):
    import requests
    cle = os.environ.get("FINNHUB_API_KEY", "")
    if not cle:
        raise SystemExit("FINNHUB_API_KEY absent — pas de dépêches, pas de post")
    r = requests.get("https://finnhub.io/api/v1/news",
                     params={"category": "general", "minId": 0},
                     headers={"X-Finnhub-Token": cle}, timeout=10)
    if r.status_code != 200:
        raise SystemExit(f"Finnhub HTTP {r.status_code} — pas de post")
    seuil = datetime.now(timezone.utc) - timedelta(hours=fenetre_h)
    vues, par_source, candidates = set(), {}, []
    for a in r.json()[:200] if isinstance(r.json(), list) else []:
        url = a.get("url") or ""
        if not url or url in vues:
            continue
        ts = a.get("datetime") or 0
        if datetime.fromtimestamp(ts, tz=timezone.utc) < seuil:
            continue
        src = a.get("source") or "?"
        if par_source.get(src, 0) >= MAX_PAR_SOURCE:
            continue
        if not (a.get("headline") and a.get("summary")):
            continue          # un titre sans contenu ne permet que de broder
        vues.add(url)
        par_source[src] = par_source.get(src, 0) + 1
        candidates.append({
            "titre": a["headline"].strip(),
            "resume": a["summary"].strip(),
            "source": src,
            "url": url,
            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
        })
        # ON NE S'ARRÊTE PLUS À MAX_DEPECHES ICI. Le plafond borne ce qui part
        # dans le prompt, pas ce qu'on regarde : couper le tirage avant la
        # mémoire ferait choisir parmi quatorze dépêches dont la moitié a déjà
        # servi, et la variété se jouerait sur ce qui reste.
        if len(candidates) >= MAX_DEPECHES * 2:
            break
    retenues, ecartees = trier_depeches(candidates, deja)
    if ecartees:
        print(f"   {ecartees} dépêche(s) déjà citée(s) ces jours-ci, écartée(s)")
    return retenues


# ── Rédaction ────────────────────────────────────────────────────────────────

PROMPT = """Tu écris le point marchés du matin d'un site d'information financière \
français, à partir des dépêches numérotées ci-dessous, et de RIEN d'autre.

Règles absolues :
- Chaque fait, chiffre et citation vient d'une dépêche. Tu n'ajoutes aucune \
connaissance extérieure, aucun contexte de mémoire, aucune estimation.
- Aucun conseil, aucune recommandation, aucune prédiction, aucun « il faut ».
- Tu ne mentionnes ni Signal, ni un portefeuille, ni une watchlist.
- Français clair. Les sociétés par leur nom, pas par leur ticker.
- Si les dépêches sont maigres, écris court : un post honnêtement mince vaut \
mieux qu'un post gonflé.

Le ton : léger, complice, un sourire en coin. Le lecteur prend son café. Les \
titres et le chapeau peuvent jouer, les images amusantes sont bienvenues, tant \
que quatre limites tiennent :
- L'humour porte sur les FORMULATIONS et les situations, jamais sur les faits \
ni les chiffres, qui restent exacts et sourcés.
- Jamais de moquerie envers une personne, une entreprise ou ceux qui perdent \
de l'argent. On sourit du théâtre des marchés, pas des acteurs.
- AUCUN humour sur les sujets graves : guerre, menace militaire, conflit \
géopolitique, catastrophe, victimes. Une section qui touche à l'un de ces \
sujets s'écrit au ton sobre et factuel, titre compris. On peut sourire de la \
RÉACTION des marchés dans une section dédiée aux marchés, jamais du contexte \
grave lui-même ni en l'utilisant comme ressort comique.
- La clarté gagne toujours : si un trait d'esprit obscurcit l'information, \
il saute. Pas de tiret cadratin (—) dans les textes.

Réponds UNIQUEMENT avec un objet JSON :
{{
  "titre": "…(8-90 caractères, ce que CE matin apporte de neuf)",
  "chapeau": "…(40-300 caractères, résumé pour la carte de la page d'accueil)",
  "sujet": "un parmi : {sujets}",{champ_marches}
  "sections": [
    {{"titre": "…", "texte": "…(3-6 phrases)", "sources": [indices des dépêches utilisées]}}
  ]
}}
Le `sujet` suit ce dont le post PARLE, pas le genre de l'exercice : il choisit \
l'illustration, et un post dont le cœur est une puce, un baril ou une banque \
centrale ne s'illustre pas d'une corbeille.
{consigne_marches}{bloc_memoire}
DÉPÊCHES ({n}) :
{corps}{bloc_marches}"""

# LE BLOC QUI CASSE LA BOUCLE. Il ne dit pas « varie un peu » : il montre au
# modèle ce que le lecteur a déjà lu, nomme les mots usés, et rappelle où vit
# le décor permanent des marchés — dans le tableau, qui est déjà affiché.
BLOC_MEMOIRE = """
## LES MATINS PRÉCÉDENTS (le lecteur les a lus)
{lignes}{uses}
Un titre dit ce qui a CHANGÉ. Les cours de l'or, du brut, l'état de Wall Street \
et les tensions au long cours reviennent tous les matins : ils ont déjà leur \
place, le tableau des clôtures et le paragraphe `marches` juste en dessous. Le \
titre et le chapeau, eux, portent ce que les dépêches d'AUJOURD'HUI apportent \
de neuf. Un titre qui aurait pu être écrit hier soir n'est pas un titre.
UNE EXCEPTION, ET UNE SEULE : si le fait du jour EST le mouvement de marché \
lui-même (un décrochage, un record, un renversement de tendance), c'est le \
titre, et tu l'écris sans hésiter. On ne renonce jamais à un vrai titre pour \
éviter une répétition. Ce qu'on refuse, c'est le titre par défaut.
"""


def bloc_memoire(recents, epuises):
    """Le bloc de prompt qui porte la mémoire des matins passés. Pure."""
    if not recents:
        return ""
    lignes = "\n".join(
        f"- {r['date']} · {r['titre']}"
        + (f"  [illustré en « {r['sujet']} »]" if r.get("sujet") else "")
        for r in recents)
    uses = ""
    if epuises:
        mots = ", ".join(libelles(epuises, [r["titre"] for r in recents]))
        uses = ("\n\nCes mots ont porté au moins deux des trois derniers titres : "
                f"{mots}. Ils ont fait leur temps en tête d'affiche. Ne les "
                "reprends pas dans le titre du jour, et ne les remplace pas par "
                "un synonyme : va chercher un AUTRE fait dans les dépêches.")
    return BLOC_MEMOIRE.format(lignes=lignes, uses=uses)

# Le paragraphe qui accompagne le tableau. Il n'existe QUE si le tableau existe :
# demander un commentaire de marché sans chiffres reviendrait à demander du vent,
# et c'est précisément ce qu'on reprochait à l'ancienne version.
CHAMP_MARCHES = '\n  "marches": "…(2-4 phrases sur le tableau des clôtures ci-dessous)",'
CONSIGNE_MARCHES = """
Le champ `marches` commente le TABLEAU DES CLÔTURES donné plus bas. Règles :
- Tu peux et tu dois citer ces niveaux et ces variations : ce sont NOS mesures, \
affichées juste au-dessus de ton texte sur la page.
- Tu n'en inventes aucun autre. Aucun indice absent du tableau, aucun niveau de \
séance, aucun plus haut historique qui n'y figure pas.
- Tu peux relier ces chiffres aux dépêches quand elles l'expliquent, sans jamais \
faire dire à une dépêche ce qu'elle ne dit pas. Mais dans CE champ, tout \
POURCENTAGE que tu écris doit venir du tableau ci-dessous. Un pourcentage tiré \
d'une dépêche (« ses ventes ont progressé de 26 % ») a sa place dans une \
section, pas ici : le lecteur lit ce paragraphe juste sous le tableau, et un \
chiffre qui n'y figure pas se lit comme une ligne qu'on aurait oubliée.
- Ne recopie pas le tableau ligne à ligne : il est déjà affiché. Dis ce qu'il \
raconte, et cite les deux ou trois chiffres qui portent l'histoire du jour.
"""


_RETOUR = """

## TA TENTATIVE PRÉCÉDENTE A ÉTÉ REJETÉE
Corrige EXACTEMENT ces points, sans rien changer d'autre à ta démarche :
{defauts}
"""


def rediger(deps, marches=None, defauts=None, memoire=""):
    """`defauts` : ce que la tentative précédente a raté. Le commentaire de
    main() promettait depuis toujours que « le modèle reçoit ses défauts, pas
    nous » — c'était faux, la seconde tentative était un simple tirage au sort
    avec le même prompt. Elle est maintenant ce qu'elle prétendait être.
    `memoire` : le bloc des matins déjà parus, rendu par `bloc_memoire`."""
    from anthropic import Anthropic
    from marches import bloc_prompt
    corps = "\n".join(f"[{i}] {d['titre']} — {d['resume']} ({d['source']}, {d['date']})"
                      for i, d in enumerate(deps))
    bloc = bloc_prompt(marches)
    msg = Anthropic().messages.create(
        model=MODELE, max_tokens=2200,
        messages=[{"role": "user", "content": PROMPT.format(
            sujets=", ".join(SUJETS), n=len(deps), corps=corps,
            champ_marches=CHAMP_MARCHES if bloc else "",
            consigne_marches=CONSIGNE_MARCHES if bloc else "",
            bloc_memoire=memoire,
            bloc_marches=bloc) + (_RETOUR.format(defauts="\n".join(
                "- " + x for x in defauts)) if defauts else "")}])
    brut = msg.content[0].text.strip()
    brut = re.sub(r"^```(?:json)?\s*|\s*```$", "", brut)
    return json.loads(brut)


# ── Photo ────────────────────────────────────────────────────────────────────

def photos_deja_utilisees(n=10):
    """Fichiers Commons illustrant les n posts quotidiens les plus récents.

    C'est la mémoire qui fait TOURNER les illustrations : sans elle, le tri
    par score est déterministe, la même image re-gagne chaque matin pour un
    même sujet, et la page d'accueil affiche une colonne de photos identiques.
    """
    fichiers = []
    for chemin in sorted(glob.glob(os.path.join(POSTS, "*.json")), reverse=True):
        try:
            d = json.load(open(chemin, encoding="utf-8"))
        except Exception:
            continue
        if d.get("type") != "quotidien":
            continue
        f = (d.get("photo") or {}).get("fichier")
        if f:
            fichiers.append(f)
        if len(fichiers) >= n:
            break
    return frozenset(fichiers)


def posts_sans_photo(depuis=10):
    """IDs des posts quotidiens récents publiés sans illustration, du plus
    ancien au plus récent (on répare dans l'ordre de parution)."""
    # ON TRONQUE APRÈS AVOIR FILTRÉ, PAS AVANT. Trié à l'envers, « hebdo-2026-31 »
    # passe devant « 2026-08-07 » : couper les dix premiers FICHIERS laissait
    # passer dix posts hebdomadaires et éteignait la réparation sans rien dire.
    quotidiens = []
    for chemin in sorted(glob.glob(os.path.join(POSTS, "*.json")), reverse=True):
        try:
            d = json.load(open(chemin, encoding="utf-8"))
        except Exception:                                  # noqa: BLE001
            continue
        if d.get("type") == "quotidien" and d.get("sujet"):
            quotidiens.append(d)
        if len(quotidiens) >= depuis:
            break
    return sorted(d["id"] for d in quotidiens if not d.get("photo"))


def _mots(nom):
    """Mots significatifs (≥3 lettres) du nom d'un fichier Commons."""
    return frozenset(re.findall(r"[a-zà-ÿ]{3,}", os.path.splitext(nom)[0].lower()))


# Vocabulaire générique des requêtes : ces mots matchent n'importe quoi dans la
# recherche plein-texte de Commons (« Wall Street street sign » a rapporté une
# plaque de rue de ministères londoniens, via « street sign » seul). Un
# candidat n'est pertinent que s'il partage un mot DISTINCTIF de sa requête.
GENERIQUES = frozenset(
    "street sign board display stock exchange market trading floor building "
    "headquarters tower towers district financial corporate office".split())


def _pertinent(fichier, requete):
    anc = _mots(requete) - GENERIQUES
    return not anc or bool(_mots(fichier) & anc)


def nettoyer_legende(fichier):
    """Le nom de fichier Commons sert de légende faute de mieux, mais brut il
    garde ses parenthèses d'archive, ses codes d'appareil (IMG 7517), ses
    dates de tri en tête (« 06 2023 ... ») et se coupe en plein mot."""
    l = re.sub(r"\s*\([^)]*\)\s*", " ", os.path.splitext(fichier)[0])
    l = l.replace("_", " ")
    l = re.sub(r"\b(?:IMG|DSCN?|DSCF|PXL|DJI|GOPR|LCCN)[ _-]?\d+\b", " ", l, flags=re.I)
    l = re.sub(r"^\W*\d[\d\s./-]*", "", l)          # « 06 2023 ... » en tête
    l = re.sub(r"\s+", " ", l).strip(" ,·-")
    if len(l) > 70:
        l = l[:70].rsplit(" ", 1)[0] + "…"
    return l


def choisir_candidats(candidats, deja):
    """Candidats (score, fichier, requête) triés, les images déjà parues
    écartées, AINSI QUE leurs quasi-doublons : Commons regorge de reprises
    de la même scène sous des noms voisins (le même tableau de cotations de
    Yaesu photographié en 2007, en 2009…), l'exclusion par nom exact ne
    change donc pas l'image vue par le lecteur. Deux noms qui partagent
    l'essentiel de leurs mots (coefficient de recouvrement ≥ 0,6 sur le
    plus petit) sont la même scène. Si tout le vivier a déjà servi, on rend
    le tri complet : mieux vaut une redite qu'un post sans photo. Pure."""
    vus = [m for m in (_mots(f) for f in deja) if m]
    def meme_scene(fichier):
        t = _mots(fichier)
        return bool(t) and any(len(t & v) / min(len(t), len(v)) >= 0.6 for v in vus)
    tri = sorted(candidats, reverse=True)
    inedits = [c for c in tri if c[1] not in deja and not meme_scene(c[1])]
    # Pertinence d'abord ; si elle vide le vivier (requête aux résultats tous
    # hors sujet), on retombe sur les inédits plutôt que sur rien.
    frais = [c for c in inedits if _pertinent(c[1], c[2])]
    return frais or inedits or tri


def illustrer(post_id, sujet, deja=frozenset()):
    """Meilleure image libre de Commons pour le sujet, hors images déjà
    parues dans les posts récents (deja). None si rien de probant."""
    from photos_wikidata import UA                                  # noqa
    from photos_produits import infos, prepare, score_nom           # noqa
    from photos_marques import chercher_commons                     # noqa
    candidats = []
    for req in SUJETS.get(sujet, []):
        for f in chercher_commons(req, limite=8):
            candidats.append((score_nom(f), f, req))
        time.sleep(0.25)
    # DOUZE ESSAIS, PAS SIX, ET UN JOURNAL. Le 07/08, `illustrer` a rendu None
    # en n'imprimant RIEN : les trois refus de `infos()` (échec réseau, image de
    # moins de 900 px, licence non libre) étaient muets, et le job est resté
    # vert en publiant un post sans image. Un échec silencieux dans un cron
    # quotidien ne se voit que des semaines plus tard, sur la page.
    retenus = choisir_candidats(candidats, deja)
    print(f"   photo : {len(candidats)} candidats, {len(retenus)} retenus après mémoire")
    for score, fichier, req in retenus[:12]:
        meta = infos(fichier, bavard=True)
        if not meta:
            continue
        try:
            r = urllib.request.Request(meta["url"], headers={"User-Agent": UA})
            brut = urllib.request.urlopen(r, timeout=45).read()
            os.makedirs(PHOTOS, exist_ok=True)
            chemin = os.path.join(PHOTOS, f"{post_id}.jpg")
            prepare(brut, chemin)
            v = hashlib.sha256(open(chemin, "rb").read()).hexdigest()[:8]
        except Exception as e:
            print(f"   photo ✗ {fichier[:50]} — {type(e).__name__}")
            continue
        return {"src": f"{PHOTOS}/{post_id}.jpg", "v": v,
                "legende": nettoyer_legende(fichier),
                "credit": (meta.get("auteur") or "").strip(),
                "licence": meta["licence"], "page": meta["page"],
                "fichier": fichier, "requete": req}
    return None


def reillustrer(ids, illustrateur=None):
    """Remplace la photo de posts quotidiens déjà publiés, texte intact.

    L'immuabilité protège le CONTENU éditorial (titre, sections, sources) :
    remplacer l'habillage photo ne réécrit pas l'histoire. La mémoire des
    photos parues est relue avant chaque post traité, donc un lot reste
    varié : l'image donnée au premier compte pour le second."""
    illustrateur = illustrateur or illustrer
    faits = []
    for pid in ids:
        chemin = os.path.join(POSTS, f"{pid}.json")
        if not os.path.exists(chemin):
            print(f"   ✗ {pid} : introuvable")
            continue
        d = json.load(open(chemin, encoding="utf-8"))
        if d.get("type") != "quotidien" or not d.get("sujet"):
            print(f"   ✗ {pid} : pas un post quotidien illustrable")
            continue
        photo = illustrateur(pid, d["sujet"], photos_deja_utilisees())
        if not photo:
            print(f"   ✗ {pid} : aucun candidat probant")
            continue
        d["photo"] = photo
        json.dump(d, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        faits.append(pid)
        print(f"   ✓ {pid} → {photo['fichier'][:60]}")
    return faits


# ── Hebdo ────────────────────────────────────────────────────────────────────

def materialiser_hebdo():
    """Copie l'analyse de la semaine de portfolio.json en post immuable."""
    if not os.path.exists("portfolio.json"):
        return None
    d = json.load(open("portfolio.json", encoding="utf-8"))
    a = d.get("analyse_claude") or {}
    if not a.get("analyse_macro"):
        return None
    m = re.search(r"Sem\. (\d+) · (\d+)", d.get("week", ""))
    if not m:
        return None
    pid = f"hebdo-{m.group(2)}-{int(m.group(1)):02d}"
    if os.path.exists(os.path.join(POSTS, f"{pid}.json")):
        return None          # déjà matérialisé : l'immuabilité vaut aussi ici
    sources = [{"titre": n.get("headline", ""), "source": n.get("source", ""),
                "url": n.get("url", ""), "date": n.get("date", ""),
                "resume": n.get("resume_fr") or n.get("summary", "")}
               for n in (d.get("macro_news") or [])]
    sections = [{"titre": "Le raisonnement de la semaine",
                 "texte": a["analyse_macro"], "sources": []}]
    if a.get("message_utilisateurs"):
        sections.append({"titre": "Le mot aux lecteurs",
                         "texte": a["message_utilisateurs"], "sources": []})
    chapeau = re.sub(r"\s+", " ", a["analyse_macro"]).strip()
    chapeau = chapeau[:277] + "…" if len(chapeau) > 280 else chapeau
    post = {"id": pid, "type": "hebdo", "date": d.get("updated_at", ""),
            "titre": f"L'analyse du portefeuille · {d.get('week', '')}",
            "chapeau": chapeau, "sujet": None, "photo": None,
            "conviction": a.get("conviction_globale"),
            "sections": sections, "sources": sources,
            "genere_le": d.get("updated_at", "")}
    ecrire_post(post)
    print(f"hebdo matérialisé : {pid}")
    return pid


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hebdo-seulement", action="store_true")
    ap.add_argument("--sans-photo", action="store_true")
    ap.add_argument("--sans-marches", action="store_true",
                    help="publier sans le tableau des clôtures (yfinance muet, "
                         "ou essai qui n'a pas besoin du réseau de marché)")
    ap.add_argument("--force", action="store_true",
                    help="réécrire le post du jour (jamais un autre)")
    ap.add_argument("--reillustrer", nargs="+", metavar="ID",
                    help="remplacer la photo de posts publiés, texte intact")
    a = ap.parse_args()

    if a.reillustrer:
        faits = reillustrer(a.reillustrer)
        print(f"index : {reconstruire_index()} posts, {len(faits)} réillustré(s)")
        return

    materialiser_hebdo()
    if a.hebdo_seulement:
        print(f"index : {reconstruire_index()} posts")
        return

    aujourdhui = date.today()
    if aujourdhui.weekday() >= 5:
        print("Week-end : pas de post quotidien.")
        print(f"index : {reconstruire_index()} posts")
        return
    # Le lundi matin couvre le vendredi et le week-end ; les autres jours, la
    # veille et la nuit. La fenêtre suit le calendrier, pas l'inverse.
    fenetre = 72 if aujourdhui.weekday() == 0 else 24

    deps = depeches_recentes(fenetre, depeches_deja_citees())
    print(f"{len(deps)} dépêches exploitables (fenêtre {fenetre} h)")
    if len(deps) < MIN_DEPECHES:
        raise SystemExit(f"Moins de {MIN_DEPECHES} dépêches : pas de post aujourd'hui. "
                         "Un post honnête ne se remplit pas, il s'annule.")

    recents = titres_recents()
    epuises = mots_epuises([r["titre"] for r in recents])
    memoire = bloc_memoire(recents, epuises)
    if epuises:
        print(f"   mémoire : {len(recents)} titres parus, mots épuisés — "
              + ", ".join(libelles(epuises, [r["titre"] for r in recents])))

    # LE TABLEAU AVANT LE TEXTE. Le modèle doit commenter des clôtures qu'il a
    # sous les yeux ; les mesurer après coup produirait un commentaire écrit à
    # l'aveugle, exactement ce qu'on cherche à supprimer. Un relevé absent n'est
    # pas une panne : le post s'écrit sans tableau ni commentaire de marché.
    from marches import releve
    marches = None if a.sans_marches else releve()

    post = rediger(deps, marches, memoire=memoire)
    defauts = valider_post(post, len(deps), marches)
    redites = defauts_redite(post, epuises, [r["titre"] for r in recents])
    if defauts or redites:
        # Une seule seconde chance : le modèle reçoit ses défauts, pas nous.
        print("⚠ post rejeté :", "; ".join(defauts + redites), "— nouvelle tentative")
        second = rediger(deps, marches, defauts + redites, memoire)
        d2 = valider_post(second, len(deps), marches)
        if not d2:
            # La seconde est juste : elle gagne, redite corrigée ou non.
            post, defauts = second, d2
            redites = defauts_redite(second, epuises, [r["titre"] for r in recents])
        elif defauts:
            raise SystemExit("Post invalide après 2 tentatives : " + "; ".join(d2))
        else:
            # LA PREMIÈRE ÉTAIT VRAIE, SEULEMENT REDONDANTE, ET LA SECONDE EST
            # FAUSSE. On garde la première : renoncer au post du matin parce
            # qu'un mot revenait serait payer une gêne au prix d'une panne.
            print(f"::warning::seconde tentative invalide ({'; '.join(d2)}) — "
                  "la première est publiée telle quelle")

    pid = aujourdhui.isoformat()
    utilises = sorted({i for s in post["sections"] for i in s["sources"]})
    complet = {
        "id": pid, "type": "quotidien", "date": pid,
        "titre": post["titre"], "chapeau": post["chapeau"], "sujet": post["sujet"],
        "photo": None if a.sans_photo else
                 illustrer(pid, post["sujet"], photos_deja_utilisees()),
        # Le relevé est GELÉ dans le post, comme la photo : un tableau servi
        # depuis un fichier partagé se réécrirait chaque matin et rendrait faux
        # tous les posts archivés, qui annoncent « à la clôture de la veille ».
        "marches": marches,
        "marches_texte": post.get("marches"),
        "sections": post["sections"],
        # Seules les dépêches réellement citées sont publiées comme sources :
        # lister les autres habillerait le post d'une provenance qu'il n'a pas.
        "sources": [deps[i] for i in utilises],
        "genere_le": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    chemin = ecrire_post(complet, force=a.force)
    print(f"post écrit : {chemin} ({len(post['sections'])} sections, "
          f"{len(utilises)} sources, photo {'oui' if complet['photo'] else 'non'})")
    if redites:
        # Jaune dans l'onglet Actions, comme le post sans photo : la redite
        # passée n'est pas une panne, mais elle ne doit pas s'installer en
        # silence — c'est exactement ainsi qu'on a tenu quatre matins.
        print("::warning::redite de titre publiée — " + "; ".join(redites))
    if not (complet["photo"] or a.sans_photo):
        # ::warning:: est rendu en jaune dans l'onglet Actions et remonte dans le
        # résumé du run. Sans lui, un post sans photo se lit « success » comme un
        # autre : c'est exactement ce qui a laissé passer le 07/08.
        print(f"::warning::post {pid} publié SANS PHOTO (sujet {post['sujet']})")
    # RÉPARATION DU LENDEMAIN. Un matin sans photo n'a aucune raison de rester
    # sans photo à vie : le vivier a bougé, la mémoire des photos parues a
    # tourné, la même recherche relancée demain trouve souvent. `--reillustrer`
    # existait déjà mais demandait qu'un humain remarque le trou — et le 07/08
    # montre que personne ne le remarque avant plusieurs jours.
    # DEUX EXCLUSIONS. `--sans-photo` est une volonté, pas un raté : la réparer
    # rendrait l'option inopérante. Et le post du jour vient d'échouer il y a
    # trente secondes, avec le même vivier et la même mémoire : le relancer
    # garantit un second échec et double le coût réseau pour rien. Il sera
    # repris demain, quand la mémoire aura tourné.
    trous = [t for t in posts_sans_photo(depuis=10) if t != pid] if not a.sans_photo else []
    if trous:
        print(f"réparation : {len(trous)} post(s) quotidien(s) sans photo — {' '.join(trous)}")
        reillustrer(trous)
    print(f"index : {reconstruire_index()} posts")


if __name__ == "__main__":
    main()
