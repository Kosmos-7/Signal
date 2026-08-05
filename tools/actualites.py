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
SUJETS = {
    "banques-centrales": ["Federal Reserve Eccles Building",
                          "European Central Bank Frankfurt tower",
                          "Bank of Japan headquarters"],
    "marches":           ["New York Stock Exchange trading floor",
                          "stock exchange display board",
                          "Wall Street street sign"],
    "resultats":         ["corporate skyline La Defense",
                          "office towers financial district",
                          "annual general meeting hall"],
    "tech":              ["data center server racks",
                          "semiconductor wafer cleanroom",
                          "electronics assembly line"],
    "energie":           ["oil refinery at dusk",
                          "LNG tanker ship",
                          "high voltage transmission lines"],
    "geopolitique":      ["container port cranes",
                          "cargo ship containers sea",
                          "customs border trucks"],
    "macro":             ["supermarket shelf prices",
                          "construction site tower cranes",
                          "shipping containers stacked port"],
}

# Un post quotidien ne recommande rien. Ces deux racines n'ont aucune raison
# honnête d'apparaître dans un compte rendu factuel.
INTERDITS = ("recommand", "conseill")


# ── Validation (pure, testable hors ligne) ───────────────────────────────────

def valider_post(p, nb_depeches):
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
        if not (s.get("titre") and s.get("texte")):
            d.append(f"section {i} incomplète")
        src = s.get("sources")
        # C'est ICI que « on n'invente rien » devient structurel : une section
        # qui ne cite aucune dépêche n'a pas de provenance, donc pas de place.
        if not (isinstance(src, list) and src
                and all(isinstance(x, int) and 0 <= x < nb_depeches for x in src)):
            d.append(f"section {i} sans source valide")
    texte_total = " ".join((s.get("texte") or "") + (s.get("titre") or "")
                           for s in sections) + titre + chapeau
    bas = texte_total.lower()
    for m in INTERDITS:
        if m in bas:
            d.append(f"vocabulaire de conseil détecté : « {m}… »")
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
  "sujet": "un parmi : {sujets}",
  "sections": [
    {{"titre": "…", "texte": "…(3-6 phrases)", "sources": [indices des dépêches utilisées]}}
  ]
}}

DÉPÊCHES ({n}) :
{corps}"""


def rediger(deps):
    from anthropic import Anthropic
    corps = "\n".join(f"[{i}] {d['titre']} — {d['resume']} ({d['source']}, {d['date']})"
                      for i, d in enumerate(deps))
    msg = Anthropic().messages.create(
        model=MODELE, max_tokens=2200,
        messages=[{"role": "user", "content": PROMPT.format(
            sujets=", ".join(SUJETS), n=len(deps), corps=corps)}])
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


def choisir_candidats(candidats, deja):
    """Candidats (score, fichier, requête) triés, les images déjà parues
    écartées. Si tout le vivier a déjà servi, on rend le tri complet :
    mieux vaut une redite qu'un post sans photo. Pure, testée hors ligne."""
    tri = sorted(candidats, reverse=True)
    frais = [c for c in tri if c[1] not in deja]
    return frais or tri


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
    for score, fichier, req in choisir_candidats(candidats, deja)[:6]:
        meta = infos(fichier)
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
        # Le nom de fichier Commons sert de legende faute de mieux, mais brut
        # il se coupe en plein mot et garde ses numeros d'archive. On nettoie,
        # et on coupe au dernier mot entier.
        legende = re.sub(r"\s*\([^)]*\)\s*", " ", os.path.splitext(fichier)[0])
        legende = re.sub(r"\s+", " ", legende.replace("_", " ")).strip()
        if len(legende) > 70:
            legende = legende[:70].rsplit(" ", 1)[0] + "…"
        return {"src": f"{PHOTOS}/{post_id}.jpg", "v": v, "legende": legende,
                "credit": (meta.get("auteur") or "").strip(),
                "licence": meta["licence"], "page": meta["page"],
                "fichier": fichier, "requete": req}
    return None


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
    ap.add_argument("--force", action="store_true",
                    help="réécrire le post du jour (jamais un autre)")
    a = ap.parse_args()

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

    post = rediger(deps)
    defauts = valider_post(post, len(deps))
    if defauts:
        # Une seule seconde chance : le modèle reçoit ses défauts, pas nous.
        print("⚠ post rejeté :", "; ".join(defauts), "— nouvelle tentative")
        post = rediger(deps)
        defauts = valider_post(post, len(deps))
        if defauts:
            raise SystemExit("Post invalide après 2 tentatives : " + "; ".join(defauts))

    pid = aujourdhui.isoformat()
    utilises = sorted({i for s in post["sections"] for i in s["sources"]})
    complet = {
        "id": pid, "type": "quotidien", "date": pid,
        "titre": post["titre"], "chapeau": post["chapeau"], "sujet": post["sujet"],
        "photo": None if a.sans_photo else
                 illustrer(pid, post["sujet"], photos_deja_utilisees()),
        "sections": post["sections"],
        # Seules les dépêches réellement citées sont publiées comme sources :
        # lister les autres habillerait le post d'une provenance qu'il n'a pas.
        "sources": [deps[i] for i in utilises],
        "genere_le": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    chemin = ecrire_post(complet, force=a.force)
    print(f"post écrit : {chemin} ({len(post['sections'])} sections, "
          f"{len(utilises)} sources, photo {'oui' if complet['photo'] else 'non'})")
    print(f"index : {reconstruire_index()} posts")


if __name__ == "__main__":
    main()
