"""
generate_analyses.py — Génère/rafraîchit le contenu ÉDITORIAL par ticker (analyses.json)

Contexte
--------
Le terminal (index.html) fusionne au render() TROIS fichiers :
  - watchlist.json : 30 tickers + breakdown chiffré COMPLET   (produit par screener.py)
  - universe.json  : les titres TAGUÉS par un thème, sous forme COMPACTE (screener.py,
                     watchlists thématiques) — `themes[]` + une carte `stocks{TICKER: {...}}`
  - analyses.json  : le contenu éditorial par ticker (ce script)

Jusqu'en v3.5.0 ce script ne couvrait que les 30 titres de watchlist.json. Depuis
l'arrivée des watchlists thématiques, le site publie ~184 titres : ceux qui n'étaient
pas dans le top 30 ouvraient une fiche quasi vide (« À générer. » partout). Ce script
couvre désormais l'UNION des deux sources.

Deux niveaux de fiche, honnêtement distingués
---------------------------------------------
Un titre du top 30 dispose d'un breakdown complet (fondamentaux, multiples, Fibo,
news). Un titre seulement thématique n'a qu'un breakdown compact (score et ses trois
composantes, RSI, z-score, décote, cross, consensus). On ne fabrique RIEN à partir de
ce qui manque : la fiche thématique est plus courte, et le prompt n'énonce que les
métriques réellement disponibles.

  niveau « complet »    : resume · biz · futur · actu · bull · bear   (6 champs)
  niveau « thematique » : resume · biz · futur · bull · bear          (5 champs, pas d'`actu`
                          faute de source d'actualité datée pour ces titres)

Schéma de sortie (consommé par render() dans index.html) :
  analyses.json = { "<TICKER>": {
      "resume": [str, ...],   # 1-2 paragraphes  -> paras()  -> <p>
      "biz":    [str, ...],   # Business & Moat   -> paras()  -> <p>
      "futur":  [str, ...],   # Perspectives      -> paras()  -> <p>
      "actu":   [str, ...],   # Actu datée/chiffrée -> paras() -> <p>   (niveau complet seulement)
      "bull":   [str, ...],   # 3 puces thèse     -> bblist() -> <li>
      "bear":   [str, ...],   # 3 puces inversion -> bblist() -> <li>
      "_niveau": "complet" | "thematique"   # niveau de la fiche — EXPLOITABLE par le site
                              # (il sait ainsi si l'absence d'`actu` est un trou ou un choix)
      "_sig":   "<signature>" # interne — détection de changement
      "_perime": "AAAA-MM-JJ" # optionnel : la fiche AURAIT dû être régénérée mais le
                              # budget wall-clock a été atteint. Date de la 1re
                              # péremption (pas de la dernière) — donne l'ancienneté
                              # réelle du décalage entre le texte et le breakdown.
  }, ... }

render() lit a.resume / a.biz / a.futur / a.actu / a.bull / a.bear et n'itère JAMAIS
sur les clés de l'entrée : `_niveau`, `_sig` et `_perime` sont donc invisibles au front
tant que celui-ci ne décide pas de les exploiter.

Parallélisme
------------
À ~45 s par fiche, 184 fiches en séquentiel = 138 min, contre un timeout CI de 45 min :
la boucle séquentielle n'était plus tenable. La génération passe donc par un pool de
threads (ANALYSES_MAX_WORKERS, défaut 8) — le travail est 100 % I/O (appel API + news),
le GIL n'est pas un obstacle. Voir la section « ÉTAT PARTAGÉ » pour le verrou qui protège
le dictionnaire commun, et « BUDGET » pour la garde wall-clock adaptée à N workers.

Mise en cache du préfixe
------------------------
Le guide de rédaction (~1 600 tokens) est identique sur les 184 fiches. Il est isolé
dans un bloc de contenu propre, marqué `cache_control: ephemeral` : les fiches suivantes
lisent ce préfixe au dixième du prix d'entrée. Voir `build_prompt()`.

Dépendances : anthropic, yfinance (déjà dans requirements.txt). Python 3.13.
"""

import os
import re
import sys
import html
import json
import time
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from datetime import date, datetime, timezone
from pathlib import Path

import yfinance as yf
from anthropic import Anthropic

# Les logs contiennent des emojis (✍️/✅/🧹…) comme le reste du projet (portfolio_agent.py).
# Sur Windows, stdout est en cp1252 par défaut et lève UnicodeEncodeError ; on force UTF-8.
# No-op sur le runner CI Linux (déjà UTF-8). reconfigure() existe depuis Python 3.7.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Même modèle que la passe décisionnelle (Sonnet) de portfolio_agent.py — la
# rédaction éditoriale est une tâche de qualité/raisonnement, on reste cohérent.
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 3000

# Tarif public du modèle, en dollars par million de tokens. Sert UNIQUEMENT au
# rapport de coût en fin de run : le projet dépense ici de l'argent réel toutes
# les semaines, ce chiffre ne doit pas rester invisible.
# Écriture de cache = 1,25× l'entrée ; lecture de cache = 0,1× l'entrée.
PRIX_IN_USD_MTOK          = 3.00
PRIX_OUT_USD_MTOK         = 15.00
PRIX_CACHE_WRITE_USD_MTOK = 3.75
PRIX_CACHE_READ_USD_MTOK  = 0.30

WATCHLIST_PATH = Path(__file__).parent / "watchlist.json"
UNIVERSE_PATH  = Path(__file__).parent / "universe.json"
ANALYSES_PATH  = Path(__file__).parent / "analyses.json"
GUIDE_PATH     = Path(__file__).parent / "GUIDE_redaction_analyses.md"

# ── NIVEAUX DE FICHE ─────────────────────────────────────────────────────────
NIVEAU_COMPLET    = "complet"
NIVEAU_THEMATIQUE = "thematique"

# Champs éditoriaux attendus par render(), PAR NIVEAU (ordre = ordre d'affichage).
# `actu` est absent du niveau thématique : aucune source d'actualité datée n'est
# collectée pour ces titres, et un paragraphe d'actu sans faits sourcés serait
# exactement le genre de remplissage que ce projet refuse d'écrire.
CHAMPS_PAR_NIVEAU = {
    NIVEAU_COMPLET:    ["resume", "biz", "futur", "actu", "bull", "bear"],
    NIVEAU_THEMATIQUE: ["resume", "biz", "futur", "bull", "bear"],
}
BULLET_FIELDS = ["bull", "bear"]                       # tableaux de puces -> <li>
ALL_FIELDS    = CHAMPS_PAR_NIVEAU[NIVEAU_COMPLET]      # surensemble, pour la purge/lecture

# ── PARALLÉLISME ─────────────────────────────────────────────────────────────
# 8 workers : à ~45 s la fiche, 184 fiches passent de 138 min à ~17 min, ce qui
# tient dans le budget wall-clock (1500 s) ET dans le timeout CI de 45 min.
# Au-delà de ~16 on ne gagne plus rien : on ne fait que multiplier les 429.
MAX_WORKERS_ENV = os.getenv("ANALYSES_MAX_WORKERS", "8")
MAX_WORKERS_PLAFOND = 16

# Écriture périodique plutôt qu'à chaque ticker : réécrire 184 fois un fichier de
# 250 Ko sous verrou coûte plus cher que le crash qu'on cherche à couvrir. On borne
# la perte des DEUX côtés — en nombre de fiches ET en temps — pour qu'un run lent ne
# puisse pas accumuler des minutes de travail non persisté.
WRITE_EVERY_N = 20
WRITE_EVERY_S = 60.0

# ── BUDGET WALL-CLOCK ─────────────────────────────────────────────────────────
# Le job CI (.github/workflows/watchlist.yml) a timeout-minutes: 45, et l'étape
# « Commit JSON files » vient APRÈS cette génération. Si la boucle déborde, le job
# est tué avant le commit : rien n'est poussé, le checkout du run suivant repart du
# même état, et chaque run hebdomadaire remeurt exactement au même endroit — panne
# permanente et silencieuse, pas un simple retard. On s'arrête donc nous-mêmes AVANT
# la limite CI, pour rendre la main à l'étape de commit : c'est le commit, et lui
# seul, qui rend la reprise incrémentale possible au run suivant.
#
# 1500 s ≈ 25 min : le reste des 45 min couvre screener.py, portfolio_agent.py, pip
# install et le commit/push. Le workflow ne définit pas la variable, c'est donc ce
# défaut qui s'applique aujourd'hui ; la surcharger permet un run local complet.
# Valeur <= 0 = budget désactivé (explicitement journalisé, jamais par accident).
TIME_BUDGET_S = os.getenv("ANALYSES_TIME_BUDGET_S", "1500")

# Coût supposé d'une fiche tant qu'on n'en a mesuré aucune (observé ~45 s : news
# yfinance + un appel Sonnet de 3000 tokens). Sert uniquement au premier tour.
FIRST_TICKER_COST_S = 60.0

# Ordre de service du budget : ce qui manque au site passe avant ce qui y est déjà.
# Un ticker NOUVEAU affiche « À générer. » (trou visible) ; une fiche MODIFIÉE reste
# lisible, juste décalée par rapport au breakdown ; une COMPLÉTION est un rattrapage
# d'entrée legacy partielle, qui a déjà attendu des semaines sans gêner personne.
PRIORITY = {"nouveau": 0, "modifié": 1, "complétion": 2}

# À priorité égale, le top 30 passe avant les titres thématiques : c'est la page
# d'accueil du site, la plus consultée, et la seule dont la fiche est complète.
RANG_NIVEAU = {NIVEAU_COMPLET: 0, NIVEAU_THEMATIQUE: 1}

# Même init que portfolio_agent.py : client None si pas de clé (géré dans main()).
# max_retries relevé : avec 8 requêtes en vol, un 429 ponctuel est attendu et le SDK
# le rejoue avec backoff — sans ça, une rafale de limites de débit se transformerait
# en fiches perdues alors que la seule chose à faire était d'attendre deux secondes.
client = Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=5) if ANTHROPIC_API_KEY else None


# ── UTILITAIRES ───────────────────────────────────────────────────────────────
def load_json(path, default):
    """Même helper que portfolio_agent.py.load_json (lecture tolérante)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_guide():
    """Charge GUIDE_redaction_analyses.md pour l'injecter dans le prompt (spec éditoriale)."""
    try:
        return GUIDE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️  Guide de rédaction introuvable ({e}) — prompt sans la spec détaillée")
        return ""


def fmt(v, suffix="", dec=1):
    """Formate un nombre breakdown de façon robuste (None -> 'n/d')."""
    if v is None:
        return "n/d"
    try:
        return f"{float(v):.{dec}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


# Suffixe de place de cotation -> région, même table que region() dans index.html.
# Le breakdown compact n'a AUCUN badge : sans ça, toute valeur européenne ou
# asiatique thématique serait présentée au modèle comme américaine.
_REGIONS = {"PA": "EU", "DE": "EU", "AS": "EU", "BR": "EU", "MI": "EU", "MC": "EU",
            "AT": "EU", "HE": "EU", "VI": "EU", "LI": "EU", "IS": "EU",
            "L": "UK", "SW": "CH", "CO": "DK", "ST": "SE", "OL": "NO",
            "T": "JP", "KS": "KR", "KQ": "KR", "HK": "HK", "TO": "CA", "AX": "AU"}


def region(stock):
    """Région d'un titre : badge du screener, sinon suffixe du ticker, sinon US."""
    if stock.get("badge"):
        return stock["badge"]
    parts = str(stock.get("ticker", "")).split(".")
    if len(parts) > 1:
        return _REGIONS.get(parts[-1].upper(), "INT")
    return "US"


# ── SOURCES : watchlist.json (complet) + universe.json (compact) ──────────────
def stock_depuis_universe(ticker, u, labels):
    """Convertit une entrée COMPACTE de universe.json en objet de forme watchlist.

    Même conversion que fusionner_univers_achetable() dans portfolio_agent.py — un
    seul contrat compact dans le projet, une seule table de correspondance à relire.
    Tout ce qui manque vaut None : c'est breakdown_block() qui décide de ne PAS en
    parler, plutôt que d'écrire « n/d » partout et d'inviter le modèle à broder.

    Le prix n'est volontairement PAS injecté dans le prompt : il n'apporte rien à la
    prose (le front l'affiche déjà) et il ne peut qu'encourager un objectif de cours,
    que la charte interdit.
    """
    return {
        "ticker": ticker,
        "name":   u.get("nom") or ticker,
        "sector": u.get("secteur") or "",
        "market": u.get("market") or "",
        "badge":  None,
        "score":  u.get("score"),
        # Libellés lisibles plutôt qu'identifiants techniques : c'est du contexte de
        # prompt, « Électrification » parle au modèle, « elec_infra » non.
        "themes": [labels.get(t, t) for t in (u.get("themes") or [])],
        "justification": "",
        "breakdown": {
            "qualite":                 u.get("qualite"),
            "valorisation":            u.get("valorisation"),
            "timing":                  u.get("timing"),
            "rsi":                     u.get("rsi"),
            "regression_z":            u.get("z"),
            "regression_window_years": u.get("fenetre"),
            "decote_pct":              u.get("decote_pct"),
            # cross_type ET cross_regime : signature() lit le premier, le contrat
            # compact publie le second. On aligne les deux plutôt que de dupliquer
            # la logique de signature par niveau.
            "cross_type":              u.get("cross") or "",
            "cross_regime":            u.get("cross") or "",
            "cross_days_ago":          u.get("cross_j"),
            "target_upside_pct":       u.get("upside_pct"),
            "target_analysts":         u.get("analystes"),
        },
    }


def collecter_sources():
    """Union des deux sources -> [(stock, niveau)] + libellés de thèmes.

    Le top 30 PRIME : si un ticker est dans les deux, on garde l'objet complet de
    watchlist.json (breakdown riche) et le niveau « complet ».

    Retourne (items, univers_lisible) où `univers_lisible` dit si universe.json a pu
    être lu — la purge des orphelins en dépend (cf. main()).
    """
    watchlist = load_json(WATCHLIST_PATH, {})
    stocks = watchlist.get("stocks", []) if isinstance(watchlist, dict) else []

    universe = load_json(UNIVERSE_PATH, {})
    if not isinstance(universe, dict):
        universe = {}
    compacts = universe.get("stocks") or {}
    if not isinstance(compacts, dict):
        compacts = {}
    labels = {}
    for th in (universe.get("themes") or []):
        if isinstance(th, dict) and th.get("id"):
            labels[th["id"]] = th.get("label", th["id"])

    items = []
    vus = set()
    for s in stocks:
        tk = s.get("ticker")
        if not tk or tk in vus:
            continue
        vus.add(tk)
        items.append((s, NIVEAU_COMPLET))

    ajoutes = 0
    sans_secteur = []
    for tk, u in compacts.items():
        if tk in vus or not isinstance(u, dict):
            continue
        if not (u.get("secteur") or "").strip() or u.get("secteur") == "—":
            # Un titre sans secteur exploitable est le symptôme d'une collecte ratée
            # (même garde que screener.py). On ne rédige pas sur une donnée douteuse,
            # mais on le DIT nommément plutôt que de le laisser tomber en silence.
            sans_secteur.append(tk)
            continue
        vus.add(tk)
        items.append((stock_depuis_universe(tk, u, labels), NIVEAU_THEMATIQUE))
        ajoutes += 1

    univers_lisible = bool(compacts)
    if univers_lisible:
        print(f"🗂  Sources : {len(stocks)} titre(s) watchlist (fiche complète) "
              f"+ {ajoutes} titre(s) thématique(s) (fiche courte) = {len(items)} au total.")
    else:
        print("⚠️  universe.json absent ou vide — seule la watchlist principale sera couverte.")
        print("   Les fiches thématiques déjà écrites sont CONSERVÉES (aucune purge : "
              "sans universe.json on ne peut pas distinguer un orphelin d'un titre thématique).")
    if sans_secteur:
        print(f"   ⚠️  {len(sans_secteur)} titre(s) thématique(s) écarté(s) — secteur absent "
              f"(collecte incomplète) : {', '.join(sorted(sans_secteur))}")

    return items, univers_lisible


# ── SIGNATURE / DÉTECTION DE CHANGEMENT ──────────────────────────────────────
def bucket_cross_days(d):
    """Range cross_days_ago en paliers. Un cross qui passe de 24 à 26 jours ne
    change pas la thèse éditoriale ('récent'), mais passer de frais à ancien
    (stale) est éditorialement significatif."""
    if d is None:
        return "na"
    try:
        d = int(d)
    except (TypeError, ValueError):
        return "na"
    if d <= 10:
        return "frais"      # signal frais (fenêtre optimale)
    if d <= 40:
        return "recent"     # récent
    if d <= 120:
        return "etabli"     # établi
    return "ancien"         # ancien / stale


def bucket_score(score):
    """Range le score par tranches de 5 points.

    Le score bouge de quelques points chaque semaine (RSI, drawdown, multiples qui
    respirent) sans que la thèse change d'un mot : réinjecter le score BRUT faisait
    de la signature un quasi-hash du run, et régénérait 79 % des fiches par semaine
    pour des textes qui auraient été identiques à la virgule près. Mesuré sur
    notes/watchlist_archive/ : le score expliquait 185 des 194 changements de
    signature, dont 153 à lui seul, alors que 87 % des variations hebdomadaires de
    score sont < 5 points.
    5 points = la granularité en dessous de laquelle le discours ne change pas
    (un 68 et un 72 se rédigent pareil), au-dessus de laquelle il change vraiment
    (un 68 et un 78 n'ont pas la même thèse). Même idiome que rev_bucket.

    Effet mesuré en rejouant les signatures sur les 6 transitions hebdomadaires des
    archives : 23,8 -> 15,2 fiches régénérées par semaine sur 30 (79 % -> 51 %).
    Le résidu n'est PAS du bruit résiduel de score : la moitié vient du
    franchissement de frontière de palier (cf. note dans signature()).
    """
    try:
        return str(int(round(float(score) / 5.0) * 5))
    except (TypeError, ValueError):
        return "na"


# Version du style/prompt éditorial — bumper FORCE la régénération de toutes les fiches
# (la signature change), p.ex. après un changement de ton ou d'exigence de chiffrage.
PROMPT_VERSION = "2026-08-univers-2niveaux"   # union watchlist+univers, prompt à 2 niveaux


def signature(stock, niveau):
    """Signature éditoriale stable d'un ticker. On régénère SEULEMENT si elle change.

    Composantes = ce qui modifie le *fond* de l'analyse, pas le bruit :
      - niveau           : complet / thematique. Un titre qui entre dans le top 30 doit
                           voir sa fiche courte remplacée par une fiche complète (et
                           inversement) — c'est un changement de fond, pas cosmétique.
      - score bucket     : note de synthèse par paliers de 5 (pilote resume + bull/bear)
      - cross_type       : golden / death / neutre  (régime narratif)
      - cross_days bucket: frais/recent/etabli/ancien (poids du signal, pas le J exact)
      - regression bucket: survente / neutre / surchauffe (cadrage prix vs valeur)
      - rev_growth arrondi à 5% près : la dynamique de croissance change le discours
      - signal_dynamics_warning présent/absent : nuance "signal en transition"
    Volontairement EXCLUS : rsi, fibo, drawdown au point de base près, val_pts —
    trop volatils d'un run à l'autre pour justifier un appel API coûteux (testé : un
    RSI 49->72 + cross +1j + z +0.1σ + drawdown -99% ne change PAS la signature).
    Également exclus : l'appartenance thématique. Un titre qui gagne ou perd un thème
    reste la même entreprise avec les mêmes chiffres — sa fiche n'a pas à être réécrite.

    Sur un breakdown compact, rev_growth et le warning sont simplement absents : la
    signature vaut "na"/"ok" de façon STABLE (elle ne clignote pas d'un run à l'autre),
    et le churn reste piloté par score/cross/z.

    NB : le score passe par bucket_score(). Il reste une part de churn de frontière
    (un score qui oscille 72/73 traverse le palier 70/75) — assumée : la corriger
    demanderait de l'hystérésis, donc de faire dépendre la signature de la signature
    précédente, ce qui la rendrait non reproductible hors historique.
    """
    b = stock.get("breakdown", {}) or {}

    z = b.get("regression_z")
    if z is None:
        z_bucket = "na"
    elif z <= -2.0:
        z_bucket = "survente"
    elif z >= 2.0:
        z_bucket = "surchauffe"
    else:
        z_bucket = "neutre"

    rev = b.get("rev_growth_pct")
    try:
        rev_bucket = int(round(float(rev) / 5.0) * 5) if rev is not None else "na"
    except (TypeError, ValueError):
        rev_bucket = "na"

    warn = "warn" if (b.get("signal_dynamics_warning") or "").strip() else "ok"

    parts = [
        PROMPT_VERSION,
        niveau,
        bucket_score(stock.get("score")),
        str(b.get("cross_type", "")),
        bucket_cross_days(b.get("cross_days_ago")),
        z_bucket,
        str(rev_bucket),
        warn,
    ]
    return "|".join(parts)


def entry_is_complete(entry, niveau):
    """True si une entrée analyses.json porte tous les champs de SON niveau, non vides.
    Sert à rattraper une entrée manuelle/legacy incomplète même si _sig coïncide."""
    if not isinstance(entry, dict):
        return False
    return all(entry.get(f) for f in CHAMPS_PAR_NIVEAU.get(niveau, ALL_FIELDS))


# ── INPUT PAR TICKER ─────────────────────────────────────────────────────────
def fetch_news(ticker, limit=5):
    """Récupère quelques titres récents via yfinance .news (best-effort).

    Aucune fonction de fetch news PAR TITRE n'existe dans le projet : get_macro_news()
    de portfolio_agent.py est macro/Finnhub (general feed), pas par ticker. On s'appuie
    donc sur yfinance .news. Robuste : toute erreur -> []. Retourne une liste de strings
    "AAAA-MM-JJ — Titre (éditeur)".

    Appelé UNIQUEMENT pour les fiches de niveau complet : le niveau thématique n'a pas
    de champ `actu`, et lancer 154 requêtes yfinance de plus ne servirait qu'à allonger
    le run et à multiplier les occasions de se faire limiter.
    """
    out = []
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception as e:
        print(f"    · news {ticker} indisponibles ({e})")
        return out

    for item in raw[: limit + 5]:
        if not isinstance(item, dict):
            continue
        # yfinance a deux schémas selon la version : plat, ou imbriqué sous "content".
        content = item.get("content")
        if isinstance(content, dict):
            title = content.get("title") or ""
            pub = (content.get("provider") or {}).get("displayName", "")
            ts = content.get("pubDate") or content.get("displayTime") or ""
            datestr = str(ts)[:10] if ts else ""
        else:
            title = item.get("title", "")
            pub = item.get("publisher", "")
            ts = item.get("providerPublishTime")
            datestr = ""
            if ts:
                try:
                    # tz-aware (utcfromtimestamp est déprécié en 3.12+ et warn en 3.13)
                    datestr = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    datestr = ""

        # Neutralise tout balisage dans des textes d'origine externe avant injection
        # dans le prompt (défense en profondeur avec _sanitize_html côté sortie).
        title = re.sub(r"<[^>]*>", "", (title or "")).strip()
        pub   = re.sub(r"<[^>]*>", "", (pub or "")).strip()
        if not title:
            continue
        prefix = f"{datestr} — " if datestr else ""
        suffix = f" ({pub})" if pub else ""
        out.append(f"{prefix}{title}{suffix}")
        if len(out) >= limit:
            break
    return out


def _ligne_decomposition(b):
    """Décomposition du score, en n'annonçant que les composantes réellement présentes.

    Le breakdown compact ne publie pas `analystes` : l'écrire « analystes ?/3 » ferait
    croire à une donnée manquante alors qu'elle n'existe simplement pas à ce niveau.
    """
    morceaux = []
    for cle, libelle, total in (("qualite", "qualité", 45), ("valorisation", "valorisation", 30),
                                ("timing", "timing", 22), ("analystes", "analystes", 3)):
        v = b.get(cle)
        if v is not None:
            morceaux.append(f"{libelle} {v}/{total}")
    return "- Décomposition : " + " · ".join(morceaux) if morceaux else ""


def breakdown_block(stock, niveau):
    """Rend le breakdown chiffré d'un ticker en bloc lisible pour le prompt.

    Règle unique et non négociable : une ligne n'est écrite QUE si la donnée existe.
    Un breakdown compact n'a ni fondamentaux, ni multiples, ni Fibo, ni drawdown ; ces
    lignes disparaissent au lieu d'afficher « n/d » — sans quoi le modèle aurait sous les
    yeux une liste de trous à commenter, et « None » finirait dans la prose publiée.
    """
    b = stock.get("breakdown", {}) or {}
    lines = [
        f"- Nom / secteur / région : {stock.get('name','')} · {stock.get('sector','')} · {region(stock)}",
    ]

    score = stock.get("score")
    if score is not None:
        lines.append(f"- Score Signal : {score}/100")

    ligne_decomp = _ligne_decomposition(b)
    if ligne_decomp:
        lines.append(ligne_decomp)

    if b.get("cross_type"):
        jours = b.get("cross_days_ago")
        depuis = f" (il y a {jours} jours)" if jours is not None else ""
        pente = b.get("cross_slope_mm21_pct")
        pente_txt = f", pente MM21 {fmt(pente,'%')}" if pente is not None else ""
        lines.append(f"- Croisement : {b['cross_type']}{depuis}{pente_txt}")

    techniques = []
    if b.get("rsi") is not None:
        techniques.append(f"RSI : {fmt(b.get('rsi'),'',0)}")
    if b.get("regression_z") is not None:
        fenetre = f" (fenêtre {b['regression_window_years']} ans)" if b.get("regression_window_years") else ""
        techniques.append(f"Z-score régression : {fmt(b.get('regression_z'),'σ',1)}{fenetre}")
    if techniques:
        lines.append("- " + "   |   ".join(techniques))

    fibo = (b.get("fibo") or {}).get("closest_fibo") if isinstance(b.get("fibo"), dict) else None
    if b.get("drawdown_52w_pct") is not None or fibo:
        bouts = []
        if b.get("drawdown_52w_pct") is not None:
            bouts.append(f"Drawdown 52s : {fmt(b.get('drawdown_52w_pct'),'%')}")
        if fibo:
            bouts.append(f"Zone Fibo : {fibo}")
        lines.append("- " + "   |   ".join(bouts))

    # Fondamentaux — niveau complet uniquement (le compact ne les publie pas).
    if any(b.get(k) is not None for k in ("rev_growth_pct", "net_margin_pct", "fcf_margin_pct")):
        lines.append(
            f"- Fondamentaux (PRÉCISE toujours la période dans la prose) : croissance CA "
            f"{fmt(b.get('rev_growth_pct'),'%')} = dernier trimestre publié en glissement annuel (a/a)"
            f"{(' au ' + b['mrq']) if b.get('mrq') else ''} · marge nette {fmt(b.get('net_margin_pct'),'%')} "
            f"= TTM, 12 mois glissants · marge FCF {fmt(b.get('fcf_margin_pct'),'%')} = TTM"
        )

    if any(b.get(k) is not None for k in ("forward_pe", "trailing_pe", "fcf_yield_pct", "peg")):
        lines.append(
            f"- Valorisation (CHIFFRE-la dans la prose ; n'invente AUCUN multiple absent) : PER forward "
            f"{fmt(b.get('forward_pe'),'x',1)} · PER courant {fmt(b.get('trailing_pe'),'x',1)} · FCF yield "
            f"{fmt(b.get('fcf_yield_pct'),'%',1)} · PEG {fmt(b.get('peg'),'',2)} · z-score "
            f"{fmt(b.get('regression_z'),'σ',1)}. NB : un PER courant nettement supérieur au PER forward "
            f"= bénéfices au creux de cycle (à expliquer, pas à confondre avec « cher »)."
        )

    # Décote/surcote vs tendance + consensus (v3.3.0) — avec les garde-fous d'écriture :
    # jamais « marge de sécurité », caveat structurel obligatoire sur les extrêmes.
    dc = b.get("decote_pct")
    if dc is not None:
        sens = "décote" if dc >= 0 else "surcote"
        z_ext = b.get("regression_z")
        caveat = ""
        if z_ext is not None and z_ext <= -2:
            caveat = " ⚠ écart extrême : évoque le risque de piège de valeur (le marché price peut-être un changement structurel) — ne présente JAMAIS la décote comme une opportunité en soi"
        elif z_ext is not None and z_ext >= 2:
            caveat = " ⚠ écart extrême : évoque le risque de chasse au rally (payer très au-dessus de la trajectoire historique)"
        lines.append(
            f"- {sens.capitalize()} vs tendance ({b.get('regression_window_years','?')} ans) : {abs(dc):.0f}% "
            + (f"(prix tendance {fmt(b.get('prix_tendance'),'',0)}). " if b.get("prix_tendance") is not None else "")
            + f"Tu PEUX la commenter dans `futur` ou `resume`, "
              f"mais appelle-la « {sens} vs tendance », JAMAIS « marge de sécurité » (la référence est une trajectoire "
              f"historique, pas une valeur intrinsèque).{caveat}"
        )

    if b.get("target_upside_pct") is not None:
        lines.append(
            f"- Objectif consensus analystes : {fmt(b.get('target_upside_pct'),'%',0)} de potentiel "
            f"({b.get('target_analysts') or '?'} analystes) — indicatif, biais optimiste structurel documenté ; "
            f"si consensus et tendance long terme divergent fortement, ce désaccord mérite une phrase."
        )

    warn = (b.get("signal_dynamics_warning") or "").strip()
    if warn:
        lines.append(f"- ⚠ Signal en transition : {warn}")

    just = stock.get("justification", "")
    if just:
        lines.append(f"- Justification screener : {just}")

    return "\n".join(lines)


# ── PROMPT ────────────────────────────────────────────────────────────────────
# Taille minimale d'un préfixe mis en cache : 1024 tokens sur claude-sonnet-4-6.
# En dessous, l'API ignore silencieusement `cache_control` (aucune erreur, aucun
# gain). Le guide fait ~5 400 caractères ≈ 1 600 tokens (français ≈ 3,4 car/token) :
# on garde une marge et on REFUSE de poser le marqueur si le guide a rétréci, plutôt
# que de croire à un cache qui n'existe pas.
CACHE_MIN_CHARS = 4000
_GUIDE_ENTETE = "## GUIDE DE RÉDACTION (autorité éditoriale — applique-le scrupuleusement)\n"

SYSTEM_PROMPT = (
    "Tu es un analyste financier éditorial, neutre et factuel, pour un service "
    "d'information (Bêta/fictif). Tu ne donnes jamais de conseil ni d'objectif de "
    "cours. Tu réponds UNIQUEMENT en JSON valide, sans texte avant ou après, sans "
    "balises markdown ni backticks."
)


def bloc_guide(guide):
    """Bloc de tête IDENTIQUE d'une fiche à l'autre — c'est LUI qu'on met en cache.

    La mise en cache est un match de PRÉFIXE : tout ce qui précède le marqueur doit
    être identique au bit près d'un appel à l'autre. Ici l'ordre de rendu est
    system -> messages, et le system prompt est une constante : le préfixe caché
    couvre donc system + guide, ~1 700 tokens facturés au dixième du prix à partir
    de la deuxième fiche. Retourne None si le guide est absent ou trop court pour
    être éligible au cache (l'appelant journalise).
    """
    if not guide or len(guide) < CACHE_MIN_CHARS:
        return None
    return {
        "type": "text",
        "text": _GUIDE_ENTETE + guide,
        # TTL par défaut (5 min) : à 8 workers une fiche se termine toutes les ~6 s,
        # le cache ne retombe jamais froid au cours d'un run. Le TTL 1 h coûterait
        # 2× en écriture pour un bénéfice nul ici.
        "cache_control": {"type": "ephemeral"},
    }


def build_prompt(stock, guide, news, niveau):
    """Construit le prompt de rédaction éditoriale d'un ticker, en blocs de contenu.

    Retourne la liste `content` du message user :
      [ bloc guide (mis en cache) , bloc variable ]
    Le bloc variable porte tout ce qui change d'un ticker à l'autre — il doit rester
    APRÈS le marqueur de cache, sinon plus rien n'est mutualisé.
    """
    ticker = stock["ticker"]
    today = str(date.today())
    champs = CHAMPS_PAR_NIVEAU[niveau]

    if niveau == NIVEAU_COMPLET:
        news_block = (
            "Titres de presse récents (à recouper, ne JAMAIS inventer au-delà de ces faits) :\n"
            + "\n".join(f"  - {n}" for n in news)
            if news else
            "Aucune actualité fraîche récupérée pour ce ticker. Pour le champ `actu`, reste "
            "factuel et général (dernier trimestriel connu, faits structurels datés si tu en "
            "as) ; n'invente AUCUN chiffre ni AUCUNE date précise non vérifiable."
        )
        bloc_actu = f"\n## ACTUALITÉ\n{news_block}\n"
        cadre_donnees = ""
        schema = (
            '  "resume": ["§1 : ce que fait la boîte en une phrase + le débat central. Relie le score '
            f'{stock.get("score","?")}/100 à la qualité, pas au timing.", "§2 (optionnel) : cadrage valorisation en relatif."],\n'
            '  "biz":    ["§ comment la boîte gagne de l\'argent + marges.", "§ type de douve nommé + durabilité/menace."],\n'
            '  "futur":  ["§ drivers de croissance.", "§ cadrage prix vs valeur (cher/correct/décoté en relatif, SANS cible chiffrée) + risques."],\n'
            '  "actu":   ["§ faits récents datés et chiffrés (1 paragraphe dense)."],\n'
            '  "bull":   ["puce 1 chiffrée", "puce 2 chiffrée", "puce 3 chiffrée"],\n'
            '  "bear":   ["puce 1 (inversion)", "puce 2 (inversion)", "puce 3 (inversion)"]'
        )
        longueurs = ("Contraintes de longueur : resume 1-2 §, biz 2 §, futur 2 §, actu 1 § dense, "
                     "bull et bear EXACTEMENT 3 puces chacun. Chaque § = 2 à 4 phrases.")
    else:
        bloc_actu = ""
        themes = [t for t in (stock.get("themes") or []) if t]
        ligne_themes = (
            f"Ce titre est publié dans les watchlists thématiques suivantes : {', '.join(themes)}. "
            "C'est un FILTRE du screener (secteur/règle), pas un jugement de qualité : ne bâtis "
            "aucune thèse sur cette appartenance.\n\n" if themes else ""
        )
        # Le cadrage le plus important de tout ce prompt : dire au modèle ce qu'il N'A PAS.
        cadre_donnees = (
            f"\n## PÉRIMÈTRE DES DONNÉES (LIS CECI AVANT D'ÉCRIRE)\n{ligne_themes}"
            "Ce titre ne fait pas partie de la watchlist principale : le screener n'en publie "
            "qu'un jeu de données RÉDUIT — celui listé ci-dessus, rien de plus. Tu ne disposes "
            "NI du chiffre d'affaires, NI des marges, NI d'un PER, d'un PEG ou d'un FCF yield, "
            "NI d'actualité datée pour ce titre.\n"
            "En conséquence, RÈGLE ABSOLUE : ne cite, n'estime et n'évoque AUCUNE de ces "
            "métriques — pas même de mémoire, pas même approximativement, pas même en la "
            "qualifiant (« marges élevées », « valorisation à 30x »). Tout jugement chiffré doit "
            "s'appuyer exclusivement sur les nombres fournis plus haut. Ce que tu ignores, tu ne "
            "l'écris pas : une fiche courte et sourcée vaut mieux qu'une fiche complète et devinée.\n"
            "Tu PEUX en revanche décrire qualitativement l'activité de l'entreprise, son modèle "
            "économique, son type de douve et les forces qui la menacent — c'est de la "
            "connaissance générale, pas une donnée financière inventée.\n"
        )
        schema = (
            '  "resume": ["§ unique : ce que fait la boîte en une phrase + le débat central. Relie le score '
            f'{stock.get("score","?")}/100 à la qualité, pas au timing."],\n'
            '  "biz":    ["§ comment la boîte gagne de l\'argent + type de douve nommé et sa durabilité."],\n'
            '  "futur":  ["§ drivers de croissance + cadrage prix vs valeur à partir des SEULS chiffres fournis (score, z-score, décote vs tendance, RSI, consensus), SANS cible chiffrée."],\n'
            '  "bull":   ["puce 1", "puce 2", "puce 3"],\n'
            '  "bear":   ["puce 1 (inversion)", "puce 2 (inversion)", "puce 3 (inversion)"]'
        )
        longueurs = ("Contraintes de longueur (fiche COURTE) : resume 1 §, biz 1 §, futur 1 §, "
                     "bull et bear EXACTEMENT 3 puces chacun. Chaque § = 2 à 3 phrases, chaque puce 1 phrase.")

    variable = f"""Tu rédiges la fiche éditoriale du titre {ticker} pour « Signal », un screener
d'actions présenté comme un service éditorial d'information financière (statut Bêta/fictif).
Date du jour : {today}.

## DONNÉES QUANTITATIVES DU TITRE (issues du screener — source de vérité pour les chiffres techniques)
{breakdown_block(stock, niveau)}
{cadre_donnees}{bloc_actu}
## TON & CONTRAINTES (NON NÉGOCIABLES)
- Ton PRÉCIS, FACTUEL, CLAIR et posé — analyste rigoureux. Plume vivante mais sobre : une
  pointe d'esprit pince-sans-rire est bienvenue de loin en loin, JAMAIS lourde, jamais un
  calembour gratuit, jamais de hype ni de ton promotionnel. Le fond prime sur le trait d'esprit.
- AUCUNE prétention d'alpha, AUCUN conseil d'achat/vente, AUCUN objectif de cours chiffré.
- Le score reflète une QUALITÉ à un instant T, JAMAIS un timing. Le timing technique est un
  GARDE-FOU (il pénalise chase/couteau), jamais une thèse d'achat.
- Nomme EXPLICITEMENT le type de douve (marque / coût / réseau / coûts de transfert /
  actif réglementaire) et QUESTIONNE sa durabilité (qu'est-ce qui la tuerait ?).
- CHIFFRE TOUT jugement de valorisation avec les NOMBRES FOURNIS CI-DESSUS, et eux seuls.
  Les qualificatifs vagues SEULS sont interdits (« fourchette haute », « cher », « tendu »
  sans chiffre). N'invente JAMAIS un multiple, une marge ou une croissance qui ne figure pas
  dans les données ci-dessus : pour le relatif-historique, appuie-toi sur le z-score.
- `bear` = la VRAIE inversion de thèse (ce qui ferait échouer la thèse / perte permanente),
  PAS seulement « c'est cher ».
- Reste dans le cercle de compétence : si la durabilité n'est pas évaluable, dis-le.
- Tu peux utiliser des balises <b>…</b> inline pour mettre en relief un chiffre clé
  (comme les fiches existantes), mais avec parcimonie. Pas d'autre HTML.
- Écris en FRANÇAIS.
- INTERDIT : le tiret cadratin « — » comme ponctuation. C'est la signature la plus
  reconnaissable d'un texte de machine, et elle décrédibilise la fiche entière.
  Utilise une virgule pour une apposition, deux-points pour une explication, ou
  coupe en deux phrases. Le tiret demi-cadratin « – » est proscrit de la même façon.

## FORMAT DE SORTIE — JSON STRICT, RIEN D'AUTRE
Réponds UNIQUEMENT par un objet JSON valide (pas de texte avant/après, pas de backticks)
avec EXACTEMENT ces {len(champs)} clés, chacune un tableau de chaînes :
{{
{schema}
}}

{longueurs}"""

    guide_bloc = bloc_guide(guide)
    if guide_bloc is None:
        # Pas de cache possible : on remet le guide en tête du bloc unique s'il existe,
        # pour ne pas perdre la spec éditoriale — seul le bénéfice de coût est perdu.
        entete = (_GUIDE_ENTETE + guide + "\n\n") if guide else ""
        return [{"type": "text", "text": entete + variable}]
    return [guide_bloc, {"type": "text", "text": variable}]


# ── VALIDATION / PARSING ──────────────────────────────────────────────────────
def _sanitize_html(text):
    """Neutralise tout HTML sauf <b>…</b> (le seul balisage du contrat éditorial).

    La contrainte « balises <b> uniquement, pas d'autre HTML » n'existait qu'au
    niveau du prompt — jamais appliquée en code. Or ces champs sont rendus en
    innerHTML par index.html sur un site public : sans ce filtre, une injection
    de prompt via un titre de presse pouvait faire émettre au modèle une balise
    active (XSS stockée, servie à tous les visiteurs via GitHub Pages).
    """
    s = html.escape(str(text), quote=False)
    return s.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")


def parse_and_validate(raw, niveau):
    """Parse la réponse Claude et valide le schéma DU NIVEAU. Lève ValueError si invalide.

    Même nettoyage que portfolio_agent.py (strip ```json / ```), plus un filet de
    sécurité qui isole le 1er objet {...} si Claude entoure le JSON de prose.
    Chaque chaîne validée passe par _sanitize_html (allowlist <b> seulement).
    Les clés hors périmètre du niveau sont ignorées : si le modèle rédige un `actu`
    sur une fiche thématique, on ne le publie pas (il ne serait sourcé par rien).
    """
    cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("aucun objet JSON détecté dans la réponse")
        data = json.loads(cleaned[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("la réponse n'est pas un objet JSON")

    out = {}
    for field in CHAMPS_PAR_NIVEAU[niveau]:
        val = data.get(field)
        if val is None:
            raise ValueError(f"champ manquant : {field}")
        # Tolérance : si une chaîne unique est renvoyée, on l'enveloppe en tableau.
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list):
            raise ValueError(f"champ {field} n'est pas un tableau")
        items = [_sanitize_html(str(x).strip()) for x in val if str(x).strip()]
        if not items:
            raise ValueError(f"champ {field} vide")
        out[field] = items

    # Garde-fou éditorial : bull/bear doivent porter une vraie thèse (≥ 2 puces).
    for field in BULLET_FIELDS:
        if len(out[field]) < 2:
            raise ValueError(f"champ {field} doit contenir au moins 2 puces")

    return out


def generate_one(stock, guide, niveau):
    """Génère l'analyse d'un seul ticker. Retourne (dict, usage) ou lève.

    Le dict porte les champs du niveau + `_sig` + `_niveau`. `usage` est l'objet
    d'usage renvoyé par l'API (tokens entrée/sortie/cache) — agrégé en fin de run
    pour publier le coût réel.
    """
    news = fetch_news(stock["ticker"]) if niveau == NIVEAU_COMPLET else []
    content = build_prompt(stock, guide, news, niveau)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    # Diagnostics explicites : sans ces gardes, une réponse tronquée produisait un
    # « aucun objet JSON détecté » trompeur, et une réponse vide un IndexError opaque.
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise ValueError(f"réponse tronquée à {MAX_TOKENS} tokens (stop_reason=max_tokens) — augmenter MAX_TOKENS ?")
    if not response.content:
        raise ValueError("réponse vide du modèle (content=[])")
    raw = response.content[0].text
    analysis = parse_and_validate(raw, niveau)
    analysis["_niveau"] = niveau
    analysis["_sig"] = signature(stock, niveau)
    return analysis, getattr(response, "usage", None)


def prechauffer_cache(guide):
    """Écrit le préfixe partagé dans le cache AVANT de lancer le pool.

    Sans ça, les 8 premières requêtes partent simultanément avec un cache vide :
    aucune ne peut lire ce que les autres sont en train d'écrire, et on paie 8
    écritures de cache au lieu d'une. Une requête max_tokens=0 fait le préremplissage
    (donc l'écriture du cache) et rend la main immédiatement, sans facturer de sortie.
    Best-effort : toute erreur est journalisée et le run continue — un préchauffage
    raté coûte quelques centimes, pas une fiche.
    """
    bloc = bloc_guide(guide)
    if bloc is None:
        print("  ⚠️  Préfixe non éligible au cache (guide absent ou < "
              f"{CACHE_MIN_CHARS} caractères) — chaque fiche paiera son entrée plein tarif.")
        return False
    # max_tokens=0 d'abord (préremplissage seul, zéro token de sortie facturé) ; si le
    # SDK ou l'API refuse la valeur, 1 token de sortie fait le même travail pour ~0 $.
    for plafond in (0, 1):
        try:
            client.messages.create(
                model=MODEL,
                max_tokens=plafond,
                system=SYSTEM_PROMPT,
                # Le marqueur reste sur le DERNIER bloc partagé avec les vraies requêtes :
                # le texte de remplissage vient après, il n'entre pas dans le préfixe caché.
                messages=[{"role": "user",
                           "content": [bloc, {"type": "text", "text": "prechauffage"}]}],
            )
            print("  ♨️  Préfixe de prompt préchauffé (guide de rédaction mis en cache).")
            return True
        except Exception as e:                                    # noqa: BLE001
            derniere = e
    print(f"  ⚠️  Préchauffage du cache impossible ({derniere}) — les premières fiches "
          f"paieront l'écriture du cache, sans autre conséquence.")
    return False


# ── ÉTAT PARTAGÉ (protégé par verrou) ────────────────────────────────────────
class Etat:
    """Dictionnaire d'analyses partagé par N workers + compteurs + persistance.

    Pourquoi un verrou : `analyses` est muté par le thread principal à chaque fiche
    terminée ET sérialisé sur disque périodiquement. `os.replace` garantit
    l'atomicité du FICHIER, pas la cohérence du DICTIONNAIRE : sans verrou, une
    sérialisation concurrente d'un dict en cours de mutation lève un
    « dictionary changed size during iteration » — ou pire, publie un instantané
    incohérent. Le verrou couvre donc la mutation ET l'écriture.

    Le coût de contention est nul en pratique : une écriture prend ~10 ms là où une
    fiche prend ~45 s.
    """

    def __init__(self, analyses):
        self.lock = threading.Lock()
        self.analyses = analyses
        self.ok = 0
        self.fail = 0
        self.echecs = []          # (ticker, niveau, raison) — journalisés nominativement
        self.usage = {"in": 0, "out": 0, "cache_write": 0, "cache_read": 0, "fiches": 0}
        self._depuis_ecriture = 0
        self._derniere_ecriture = time.monotonic()

    def enregistrer(self, ticker, niveau, analysis, erreur, usage):
        """Enregistre le résultat d'une fiche. APPELÉE DEPUIS LES WORKERS.

        Retourne (fichier_ecrit, ancienne_conservee) — les deux calculés sous le
        verrou, pour que l'appelant n'ait jamais à relire le dict partagé sans
        protection juste pour composer sa ligne de log.
        """
        with self.lock:
            ancienne_conservee = False
            if analysis is not None:
                self.analyses[ticker] = analysis
                self.ok += 1
            else:
                self.fail += 1
                self.echecs.append((ticker, niveau, str(erreur)))
                ancienne_conservee = ticker in self.analyses
            self._cumuler_usage(usage)
            self._depuis_ecriture += 1
            trop_de_fiches = self._depuis_ecriture >= WRITE_EVERY_N
            trop_de_temps = (time.monotonic() - self._derniere_ecriture) >= WRITE_EVERY_S
            ecrit = trop_de_fiches or trop_de_temps
            if ecrit:
                self._ecrire_verrou_tenu()
            return ecrit, ancienne_conservee

    def _cumuler_usage(self, usage):
        """Agrège les compteurs de tokens (appelé SOUS le verrou)."""
        if usage is None:
            return
        self.usage["fiches"] += 1
        for cle, attr in (("in", "input_tokens"), ("out", "output_tokens"),
                          ("cache_write", "cache_creation_input_tokens"),
                          ("cache_read", "cache_read_input_tokens")):
            try:
                self.usage[cle] += int(getattr(usage, attr, 0) or 0)
            except (TypeError, ValueError):
                pass

    def _ecrire_verrou_tenu(self):
        _write(self.analyses)
        self._depuis_ecriture = 0
        self._derniere_ecriture = time.monotonic()

    def ecrire(self):
        """Écriture forcée (fin de run, purge, marques de péremption)."""
        with self.lock:
            self._ecrire_verrou_tenu()

    def marquer(self, fn):
        """Applique une mutation arbitraire au dict sous verrou (ex. _mark_stale)."""
        with self.lock:
            fn(self.analyses)


# ── BUDGET / ORDONNANCEMENT ───────────────────────────────────────────────────
def _budget_seconds():
    """Lit ANALYSES_TIME_BUDGET_S.

    Une valeur illisible retombe sur le défaut plutôt que sur « illimité » : une
    faute de frappe dans le workflow ne doit pas ressusciter en silence la panne
    permanente que ce budget existe précisément pour empêcher.
    """
    try:
        return float(str(TIME_BUDGET_S).strip())
    except (TypeError, ValueError):
        print(f"  ⚠️  ANALYSES_TIME_BUDGET_S illisible ({TIME_BUDGET_S!r}) — défaut 1500 s")
        return 1500.0


def _nb_workers():
    """Lit ANALYSES_MAX_WORKERS, borné à [1, 16].

    Même doctrine que le budget : une valeur illisible retombe sur le défaut, et le
    bornage est journalisé. 1 worker redonne exactement l'ancien comportement
    séquentiel, ce qui rend le parallélisme désactivable sans toucher au code.
    """
    try:
        n = int(str(MAX_WORKERS_ENV).strip())
    except (TypeError, ValueError):
        print(f"  ⚠️  ANALYSES_MAX_WORKERS illisible ({MAX_WORKERS_ENV!r}) — défaut 8")
        return 8
    if n < 1:
        print(f"  ⚠️  ANALYSES_MAX_WORKERS={n} invalide — ramené à 1 (séquentiel).")
        return 1
    if n > MAX_WORKERS_PLAFOND:
        print(f"  ⚠️  ANALYSES_MAX_WORKERS={n} au-dessus du plafond — ramené à {MAX_WORKERS_PLAFOND}.")
        return MAX_WORKERS_PLAFOND
    return n


def _neg_score(stock):
    """Clé de tri « score décroissant ». Score absent/illisible -> traité comme 0,
    donc servi en dernier : on ne dépense pas le budget sur une donnée douteuse."""
    try:
        return -float(stock.get("score"))
    except (TypeError, ValueError):
        return 0.0


def _mark_stale(analyses, skipped, elapsed, budget):
    """Marque et JOURNALISE les fiches non régénérées faute de budget.

    Deux invariants :
      - on ne touche PAS `_sig`. C'est l'ancienne signature qui fera re-détecter la
        fiche comme « modifié » au prochain run : toute la reprise tient à ça.
      - `_perime` retient la date de la PREMIÈRE péremption (setdefault), pas de la
        dernière : si une fiche sort du budget trois semaines d'affilée, le site voit
        l'ancienneté réelle du décalage et non une date perpétuellement fraîche.

    Le listing est exhaustif et nominatif : le projet ne tronque pas en silence, et
    une file de report qui s'allonge run après run est le symptôme à voir venir.
    """
    today = str(date.today())
    print(f"\n⏳ Budget wall-clock atteint ({elapsed:.0f}s / {budget:.0f}s) — "
          f"{len(skipped)} fiche(s) NON régénérée(s) ce run :")
    for stock, reason, niveau in skipped:
        tk = stock["ticker"]
        entry = analyses.get(tk)
        if isinstance(entry, dict):
            entry.setdefault("_perime", today)
            depuis = entry["_perime"]
            etat = "périmée depuis " + depuis if depuis != today else "marquée périmée"
        else:
            # Aucune entrée à marquer : le front affiche déjà « À générer. », le trou
            # est visible sans qu'on ait à le signaler dans le JSON.
            etat = "absente — le front affichera « À générer. »"
        print(f"     · {tk} ({reason}, {niveau}, score {stock.get('score','?')}) — {etat}")
    print("   Ces fiches gardent leur ancienne signature : le prochain run les reprendra,\n"
          "   en tête de file à priorité égale (watchlist d'abord, puis score décroissant).")
    if os.getenv("GITHUB_ACTIONS"):
        # Annotation visible dans le résumé du run sans faire échouer l'étape : un
        # report est un fonctionnement nominal, pas une panne — mais il doit se voir.
        print(f"::warning::{len(skipped)} fiche(s) éditoriale(s) reportées faute de budget "
              f"({elapsed:.0f}s / {budget:.0f}s) : "
              f"{', '.join(s['ticker'] for s, _, _ in skipped)}")


# ── COÛT ──────────────────────────────────────────────────────────────────────
def cout_usd(usage):
    """Coût réel du run à partir des compteurs de tokens renvoyés par l'API."""
    return (usage["in"] * PRIX_IN_USD_MTOK
            + usage["out"] * PRIX_OUT_USD_MTOK
            + usage["cache_write"] * PRIX_CACHE_WRITE_USD_MTOK
            + usage["cache_read"] * PRIX_CACHE_READ_USD_MTOK) / 1_000_000.0


def rapport_cout(usage, total_couvert):
    """Publie le coût du run et son extrapolation. Un run hebdomadaire dépense de
    l'argent réel : ce chiffre doit apparaître dans le log, pas dans une facture
    découverte trois mois plus tard."""
    if not usage["fiches"]:
        return
    total = cout_usd(usage)
    par_fiche = total / usage["fiches"]
    print(f"\n💰 Coût de ce run : {total:.2f} $ pour {usage['fiches']} fiche(s) "
          f"({par_fiche:.4f} $/fiche).")
    print(f"   Tokens — entrée {usage['in']:,} · sortie {usage['out']:,} · "
          f"cache écrit {usage['cache_write']:,} · cache lu {usage['cache_read']:,}"
          .replace(",", " "))
    if usage["cache_read"]:
        # Économie = ce que ces tokens auraient coûté plein tarif, moins le tarif cache.
        economie = usage["cache_read"] * (PRIX_IN_USD_MTOK - PRIX_CACHE_READ_USD_MTOK) / 1_000_000.0
        print(f"   Mise en cache du préfixe : {economie:.2f} $ économisés sur ce run "
              f"({economie / total * 100:.0f} % du coût total).")
    else:
        # Anti-panne silencieuse : un cache qui ne se lit jamais ne se voit pas
        # autrement que sur la facture.
        print("   ⚠️  AUCUNE lecture de cache sur ce run — le préfixe partagé n'est pas "
              "mutualisé (guide trop court, préfixe instable, ou fiches trop espacées).")
    if total_couvert:
        print(f"   Extrapolation : régénération complète des {total_couvert} fiches ≈ "
              f"{par_fiche * total_couvert:.2f} $ ; "
              f"régime établi (~51 % de churn/semaine) ≈ {par_fiche * total_couvert * 0.51:.2f} $/semaine, "
              f"soit ≈ {par_fiche * total_couvert * 0.51 * 52:.0f} $/an.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not client:
        print("❌ ANTHROPIC_API_KEY manquante — impossible de générer les analyses.")
        print("   Ajoutez-la dans l'environnement / les secrets CI, puis relancez.")
        print("   (analyses.json laissé INCHANGÉ — aucune écriture, sortie propre.)")
        sys.exit(1)

    items, univers_lisible = collecter_sources()
    if not any(n == NIVEAU_COMPLET for _, n in items):
        print("❌ watchlist.json vide ou manquant — rien à générer. Lancez screener.py d'abord.")
        sys.exit(1)

    analyses = load_json(ANALYSES_PATH, {})
    if not isinstance(analyses, dict):
        print("  ⚠️  analyses.json illisible/mal formé — on repart d'un objet vide.")
        analyses = {}

    guide = load_guide()
    current_tickers = {s["ticker"] for s, _ in items}

    # 1) PURGE des orphelins (tickers qui ne sont plus publiés nulle part)
    #    Garde-fou : sans universe.json, on ne peut pas distinguer un orphelin d'un
    #    titre thématique — purger reviendrait à détruire 150 fiches sur une lecture
    #    ratée. On s'abstient et on le dit.
    orphans = []
    if univers_lisible:
        orphans = [t for t in analyses if t not in current_tickers]
        for t in orphans:
            del analyses[t]
        if orphans:
            print(f"🧹 Purge {len(orphans)} orphelin(s) : {', '.join(sorted(orphans))}")

    # 2) DÉTECTION nouveau / modifié via signature
    #    - pas d'entrée               -> "nouveau"
    #    - signature changée          -> "modifié"  (inclut un changement de NIVEAU)
    #    - signature absente (legacy) -> capturée par "modifié" (None != sig calculée)
    #    - signature identique mais entrée incomplète -> "complétion"
    #    - signature identique ET entrée complète     -> on garde tel quel (0 appel API)
    todo = []
    unmarked = 0
    niveaux_poses = 0
    for s, niveau in items:
        tk = s["ticker"]
        existing = analyses.get(tk)
        new_sig = signature(s, niveau)
        if not existing:
            todo.append((s, "nouveau", niveau))
        elif existing.get("_sig") != new_sig:
            todo.append((s, "modifié", niveau))
        elif not entry_is_complete(existing, niveau):
            todo.append((s, "complétion", niveau))
        else:
            # À jour et complet. On (re)pose le niveau au cas où une entrée legacy ne
            # le porterait pas encore — le front doit toujours savoir à quoi s'attendre.
            # C'est compté : une mutation qui ne déclencherait pas d'écriture serait
            # perdue en silence au prochain chargement.
            if "_niveau" not in existing:
                existing["_niveau"] = niveau
                niveaux_poses += 1
            if existing.pop("_perime", None):
                # Elle portait une marque de péremption d'un run précédent : soit elle a
                # été régénérée depuis, soit sa signature est revenue à sa valeur
                # d'origine. Dans les deux cas le texte publié correspond de nouveau au
                # breakdown — la marque doit disparaître, sinon le site afficherait un
                # avertissement de péremption indéfiniment.
                unmarked += 1

    # File de priorité : le budget ci-dessous ne servira peut-être pas tout le monde,
    # il doit donc servir d'abord ce qui manque au site. Puis la watchlist principale
    # avant les vues thématiques. À rang égal, score décroissant.
    todo.sort(key=lambda it: (PRIORITY.get(it[1], 9), RANG_NIVEAU.get(it[2], 9), _neg_score(it[0])))

    kept = len(current_tickers) - len(todo)
    n_complets = sum(1 for _, _, n in todo if n == NIVEAU_COMPLET)
    print(f"📋 Couverture : {len(current_tickers)} tickers — "
          f"{len(todo)} à (re)générer ({n_complets} complète(s), {len(todo) - n_complets} thématique(s)), "
          f"{kept} inchangé(s) conservé(s)"
          + (f", {unmarked} marque(s) de péremption levée(s)" if unmarked else "")
          + (f", {niveaux_poses} niveau(x) renseigné(s) sur des entrées legacy" if niveaux_poses else "")
          + ".")

    etat = Etat(analyses)

    if not todo:
        # Rien à régénérer ; on réécrit si on a purgé des orphelins, levé des marques
        # ou complété des entrées legacy — sinon la mutation en mémoire serait perdue.
        if orphans or unmarked or niveaux_poses:
            etat.ecrire()
            print("✅ analyses.json mis à jour (purge orphelins / péremptions levées / niveaux posés).")
        else:
            print("✅ Rien à faire — analyses.json déjà à jour.")
        return

    # 3) GÉNÉRATION incrémentale et PARALLÈLE, robuste par ticker, sous budget wall-clock
    budget = _budget_seconds()
    workers = _nb_workers()
    started = time.monotonic()
    if budget <= 0:
        print("⏱️  Budget wall-clock DÉSACTIVÉ (ANALYSES_TIME_BUDGET_S <= 0) — "
              "la boucle ira au bout, y compris au-delà du timeout CI de 45 min.")
    else:
        projection = len(todo) * FIRST_TICKER_COST_S / workers
        print(f"⏱️  Budget wall-clock : {budget:.0f}s · {workers} worker(s) en parallèle · "
              f"{len(todo)} fiche(s) — projection initiale ≈ {projection / 60:.0f} min "
              f"(hypothèse pessimiste {FIRST_TICKER_COST_S:.0f}s/fiche, réajustée en cours de run).")

    durations = []
    i = 0                      # index de la 1re fiche NON soumise -> todo[i:] = reportées
    stop_soumission = False

    def _tache(stock, niveau):
        """Exécutée dans un worker : génère la fiche PUIS l'enregistre elle-même.

        NE LÈVE JAMAIS : une exception avalée par le pool ferait disparaître une fiche
        sans le moindre message. Toute la mutation de l'état partagé passe par
        Etat.enregistrer(), donc par le verrou — c'est le seul point de contact entre
        les workers et le dictionnaire commun.
        """
        t0 = time.monotonic()
        tk = stock["ticker"]
        try:
            analysis, usage = generate_one(stock, guide, niveau)
            erreur = None
        except Exception as e:                                    # noqa: BLE001
            analysis, usage, erreur = None, None, e
        duree = time.monotonic() - t0

        ecrit, ancienne = etat.enregistrer(tk, niveau, analysis, erreur, usage)
        # Un print = une écriture : les lignes de N workers s'entrelacent entre elles,
        # jamais à l'intérieur d'une ligne.
        if analysis is not None:
            print(f"     ✅ {tk} généré ({duree:.0f}s)" + (" · analyses.json écrit" if ecrit else ""))
        elif ancienne:
            # On garde l'ancienne analyse — mieux qu'un trou affichant « À générer ».
            print(f"     ⚠️  {tk} échec ({erreur}) — ANCIENNE analyse conservée.")
        else:
            print(f"     ✗ {tk} échec ({erreur}) — pas d'analyse, le front affichera « À générer ».")
        return duree

    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fiche")
    en_vol = {}
    prechauffe_faite = len(todo) < 2      # une seule fiche : rien à mutualiser
    try:
        while True:
            # Remplissage du pool. On n'ENTAME une fiche que si on estime pouvoir la
            # FINIR : une fiche commencée puis tuée par le timeout CI n'emporte pas
            # qu'elle-même, elle emporte l'étape de commit, donc tout le run.
            #
            # Avec N workers la garde reste per-tâche et cela reste correct : une tâche
            # soumise MAINTENANT démarre immédiatement (un worker vient de se libérer),
            # donc elle se termine vers `écoulé + estimation`. Le parallélisme change le
            # DÉBIT, pas la latence unitaire — la queue de fin est bornée par une fiche,
            # pas par N. L'estimation reste la pire durée observée (volontairement
            # pessimiste : l'asymétrie est totale entre « une fiche de moins » et « le
            # run entier perdu »), et sous parallélisme les durées unitaires s'allongent
            # un peu (429 rejoués par le SDK) — la pire durée les capture déjà.
            while not stop_soumission and len(en_vol) < workers and i < len(todo):
                if budget > 0:
                    ecoule = time.monotonic() - started
                    estimation = max(durations) if durations else FIRST_TICKER_COST_S
                    if ecoule + estimation > budget:
                        stop_soumission = True
                        break
                if not prechauffe_faite:
                    # Juste avant la PREMIÈRE requête, et pas plus tôt : si le budget
                    # était déjà épuisé, on ne veut pas avoir payé une écriture de
                    # cache pour un run qui ne génère rien.
                    prechauffer_cache(guide)
                    prechauffe_faite = True
                s, reason, niveau = todo[i]
                i += 1
                print(f"  ✍️  {s['ticker']} ({reason}, {niveau}) — score {s.get('score','?')}…",
                      flush=True)
                en_vol[executor.submit(_tache, s, niveau)] = (s, reason, niveau)

            if not en_vol:
                break

            termines, _ = wait(list(en_vol), return_when=FIRST_COMPLETED)
            for fut in termines:
                en_vol.pop(fut)
                # _tache ne lève jamais : ce result() ne peut pas exploser ici, et la
                # durée qu'il renvoie alimente l'estimation du budget ci-dessus.
                durations.append(fut.result())
    finally:
        # wait=True : on ne quitte JAMAIS en laissant des requêtes en vol dont le
        # résultat serait perdu après avoir été payé.
        executor.shutdown(wait=True)

    skipped = todo[i:]
    elapsed = time.monotonic() - started
    if skipped:
        etat.marquer(lambda a: _mark_stale(a, skipped, elapsed, budget))
    # Écriture finale : persiste les dernières fiches et les marques de péremption,
    # y compris dans le cas limite où le budget était épuisé avant la première fiche.
    etat.ecrire()

    if etat.echecs:
        # Doctrine anti-troncature silencieuse : un échec par ticker est déjà tracé
        # au fil de l'eau, mais noyé dans 184 lignes. On le rappelle nominativement.
        print(f"\n⚠️  {len(etat.echecs)} fiche(s) en échec ce run :")
        for tk, niveau, raison in etat.echecs:
            print(f"     · {tk} ({niveau}) — {raison}")

    print(f"\n✅ analyses.json écrit — {etat.ok} généré(s), {etat.fail} échec(s), {kept} conservé(s), "
          f"{len(orphans)} purgé(s), {len(skipped)} reporté(s) — {elapsed:.0f}s écoulées"
          + (f" / {budget:.0f}s de budget." if budget > 0 else " (budget désactivé)."))
    if durations:
        print(f"   Débit : {len(durations)} fiche(s) en {elapsed:.0f}s avec {workers} worker(s) — "
              f"{sum(durations) / len(durations):.0f}s par fiche en moyenne "
              f"(pire cas {max(durations):.0f}s), soit un facteur d'accélération de "
              f"{sum(durations) / elapsed:.1f}× sur le séquentiel.")
    print(f"   Total entrées : {len(etat.analyses)} (== {len(current_tickers)} si aucun échec sur un nouveau ticker).")
    rapport_cout(etat.usage, len(current_tickers))
    # Sortie en SUCCÈS même avec des fiches reportées ou en échec : un exit non nul
    # déclencherait l'étape « Signale les échecs IA » du workflow et rendrait le job
    # rouge chaque semaine pour un fonctionnement nominal — l'alarme finirait par
    # n'être plus lue. Seule une panne dure (clé absente, watchlist vide) sort en 1.


def _write(analyses):
    """Écrit analyses.json en UTF-8, ensure_ascii=False, indent=2 — écriture ATOMIQUE.

    On écrit dans un fichier temporaire du même dossier puis os.replace() : une
    interruption (crash, kill CI) ne peut pas laisser analyses.json tronqué/corrompu,
    ce qui casserait le fetch() JSON du front.

    allow_nan=False comme screener.py / portfolio_agent.py : un NaN sérialisé en
    `NaN` est refusé par JSON.parse() et casserait le rendu de TOUTES les fiches.
    Mieux vaut échouer ici, bruyamment, que publier un fichier illisible.

    ATTENTION : sous parallélisme, cette fonction doit être appelée avec le verrou
    d'Etat tenu. os.replace rend l'écriture du FICHIER atomique, il ne protège en
    rien le dictionnaire pendant sa sérialisation.
    """
    ANALYSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(ANALYSES_PATH.parent), prefix=".analyses.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(tmp, ANALYSES_PATH)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
