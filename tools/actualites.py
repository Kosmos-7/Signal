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
    txt = (p.get("marches") or "").strip()
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

def depeches_recentes(fenetre_h):
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
    vues, par_source, retenues = set(), {}, []
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
        retenues.append({
            "titre": a["headline"].strip(),
            "resume": a["summary"].strip(),
            "source": src,
            "url": url,
            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
        })
        if len(retenues) >= MAX_DEPECHES:
            break
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
  "titre": "…(8-90 caractères, le fait dominant du jour)",
  "chapeau": "…(40-300 caractères, résumé pour la carte de la page d'accueil)",
  "sujet": "un parmi : {sujets}",{champ_marches}
  "sections": [
    {{"titre": "…", "texte": "…(3-6 phrases)", "sources": [indices des dépêches utilisées]}}
  ]
}}
{consigne_marches}
DÉPÊCHES ({n}) :
{corps}{bloc_marches}"""

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


def rediger(deps, marches=None, defauts=None):
    """`defauts` : ce que la tentative précédente a raté. Le commentaire de
    main() promettait depuis toujours que « le modèle reçoit ses défauts, pas
    nous » — c'était faux, la seconde tentative était un simple tirage au sort
    avec le même prompt. Elle est maintenant ce qu'elle prétendait être."""
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
    trous = []
    for chemin in sorted(glob.glob(os.path.join(POSTS, "*.json")), reverse=True)[:depuis]:
        try:
            d = json.load(open(chemin, encoding="utf-8"))
        except Exception:                                  # noqa: BLE001
            continue
        if d.get("type") == "quotidien" and d.get("sujet") and not d.get("photo"):
            trous.append(d["id"])
    return sorted(trous)


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

    deps = depeches_recentes(fenetre)
    print(f"{len(deps)} dépêches exploitables (fenêtre {fenetre} h)")
    if len(deps) < MIN_DEPECHES:
        raise SystemExit(f"Moins de {MIN_DEPECHES} dépêches : pas de post aujourd'hui. "
                         "Un post honnête ne se remplit pas, il s'annule.")

    # LE TABLEAU AVANT LE TEXTE. Le modèle doit commenter des clôtures qu'il a
    # sous les yeux ; les mesurer après coup produirait un commentaire écrit à
    # l'aveugle, exactement ce qu'on cherche à supprimer. Un relevé absent n'est
    # pas une panne : le post s'écrit sans tableau ni commentaire de marché.
    from marches import releve
    marches = None if a.sans_marches else releve()

    post = rediger(deps, marches)
    defauts = valider_post(post, len(deps), marches)
    if defauts:
        # Une seule seconde chance : le modèle reçoit ses défauts, pas nous.
        print("⚠ post rejeté :", "; ".join(defauts), "— nouvelle tentative")
        post = rediger(deps, marches, defauts)
        defauts = valider_post(post, len(deps), marches)
        if defauts:
            raise SystemExit("Post invalide après 2 tentatives : " + "; ".join(defauts))

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
    trous = posts_sans_photo(depuis=10)
    if trous:
        print(f"réparation : {len(trous)} post(s) quotidien(s) sans photo — {' '.join(trous)}")
        reillustrer(trous)
    print(f"index : {reconstruire_index()} posts")


if __name__ == "__main__":
    main()
