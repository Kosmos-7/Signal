"""
generate_analyses.py — Génère/rafraîchit le contenu ÉDITORIAL par ticker (analyses.json)

Contexte
--------
Le terminal watchlist (index.html) fusionne DEUX fichiers au render() :
  - watchlist.json  : 30 tickers + breakdown chiffré (généré par screener.py)
  - analyses.json   : contenu éditorial par ticker (resume / biz / futur / actu / bull / bear)

Jusqu'ici analyses.json était un artefact MANUEL figé : quand le screener faisait
tourner la watchlist, les nouveaux tickers n'avaient pas d'entrée et le front
affichait "À générer." (fallback de render()).

Ce script comble ce trou : après le screener, il génère via Claude (API Anthropic)
les analyses des tickers NOUVEAUX ou MODIFIÉS, garde celles inchangées (économie API),
et purge les orphelins (tickers sortis de la watchlist).

À lancer APRÈS screener.py (qui produit watchlist.json), p. ex. dans le même job CI.

Schéma de sortie (consommé par render() dans index.html, lignes ~153-168) :
  analyses.json = { "<TICKER>": {
      "resume": [str, ...],   # 1-2 paragraphes  -> paras()  -> <p>
      "biz":    [str, ...],   # Business & Moat   -> paras()  -> <p>
      "futur":  [str, ...],   # Perspectives      -> paras()  -> <p>
      "actu":   [str, ...],   # Actu datée/chiffrée -> paras() -> <p>
      "bull":   [str, ...],   # 3 puces thèse     -> bblist() -> <li>
      "bear":   [str, ...],   # 3 puces inversion -> bblist() -> <li>
      "_sig":   "<signature>" # interne, non lu par render() — détection de changement
      "_perime": "AAAA-MM-JJ" # optionnel : la fiche AURAIT dû être régénérée mais le
                              # budget wall-clock a été atteint. Date de la 1re
                              # péremption (pas de la dernière) — donne l'ancienneté
                              # réelle du décalage entre le texte et le breakdown.
  }, ... }

render() lit a.resume / a.biz / a.futur / a.actu / a.bull / a.bear et n'itère JAMAIS
sur les clés de l'entrée : `_sig` et `_perime` sont donc invisibles au front (vérifié
index.html) tant que celui-ci ne décide pas de les exploiter.
Les strings peuvent contenir des balises inline simples (<b>…</b>) comme les entrées
existantes — render() les injecte en innerHTML via paras()/bblist().

Dépendances : anthropic, yfinance (déjà dans requirements.txt). Pas de nouvelle dépendance.
Python 3.13.
"""

import os
import re
import sys
import html
import json
import time
import tempfile
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

WATCHLIST_PATH = Path(__file__).parent / "watchlist.json"
ANALYSES_PATH  = Path(__file__).parent / "analyses.json"
GUIDE_PATH     = Path(__file__).parent / "GUIDE_redaction_analyses.md"

# Les 6 champs éditoriaux attendus par render() (ordre = ordre d'affichage).
PARA_FIELDS   = ["resume", "biz", "futur", "actu"]   # tableaux de paragraphes -> <p>
BULLET_FIELDS = ["bull", "bear"]                       # tableaux de puces      -> <li>
ALL_FIELDS    = PARA_FIELDS + BULLET_FIELDS

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

# Même init que portfolio_agent.py : client None si pas de clé (géré dans main()).
client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


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
PROMPT_VERSION = "2026-07-decote-z1dec"   # z cité à 1 décimale + commentaire décote vs tendance


def signature(stock):
    """Signature éditoriale stable d'un ticker. On régénère SEULEMENT si elle change.

    Composantes = ce qui modifie le *fond* de l'analyse, pas le bruit :
      - score bucket     : note de synthèse par paliers de 5 (pilote resume + bull/bear)
      - cross_type       : golden / death / neutre  (régime narratif)
      - cross_days bucket: frais/recent/etabli/ancien (poids du signal, pas le J exact)
      - regression bucket: survente / neutre / surchauffe (cadrage prix vs valeur)
      - rev_growth arrondi à 5% près : la dynamique de croissance change le discours
      - signal_dynamics_warning présent/absent : nuance "signal en transition"
    Volontairement EXCLUS : rsi, fibo, drawdown au point de base près, val_pts —
    trop volatils d'un run à l'autre pour justifier un appel API coûteux (testé : un
    RSI 49->72 + cross +1j + z +0.1σ + drawdown -99% ne change PAS la signature).

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
        bucket_score(stock.get("score")),
        str(b.get("cross_type", "")),
        bucket_cross_days(b.get("cross_days_ago")),
        z_bucket,
        str(rev_bucket),
        warn,
    ]
    return "|".join(parts)


def entry_is_complete(entry):
    """True si une entrée analyses.json porte les 6 champs éditoriaux non vides.
    Sert à rattraper une entrée manuelle/legacy incomplète même si _sig coïncide."""
    if not isinstance(entry, dict):
        return False
    return all(entry.get(f) for f in ALL_FIELDS)


# ── INPUT PAR TICKER ─────────────────────────────────────────────────────────
def fetch_news(ticker, limit=5):
    """Récupère quelques titres récents via yfinance .news (best-effort).

    Aucune fonction de fetch news PAR TITRE n'existe dans le projet : get_macro_news()
    de portfolio_agent.py est macro/Finnhub (general feed), pas par ticker. On s'appuie
    donc sur yfinance .news. Robuste : toute erreur -> []. Retourne une liste de strings
    "AAAA-MM-JJ — Titre (éditeur)".
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


def breakdown_block(stock):
    """Rend le breakdown chiffré d'un ticker en bloc lisible pour le prompt."""
    b = stock.get("breakdown", {}) or {}
    warn = (b.get("signal_dynamics_warning") or "").strip()
    fibo = (b.get("fibo") or {}).get("closest_fibo") if isinstance(b.get("fibo"), dict) else None
    lines = [
        f"- Nom / secteur / région : {stock.get('name','')} · {stock.get('sector','')} · {stock.get('badge') or 'US'}",
        f"- Score Signal : {stock.get('score','?')}/100  ({stock.get('stars','?')}★)",
        f"- Décomposition : qualité {b.get('qualite','?')}/45 · valorisation {b.get('valorisation','?')}/30 · timing {b.get('timing','?')}/22 · analystes {b.get('analystes','?')}/3",
        f"- Croisement : {b.get('cross_type','?')} (il y a {b.get('cross_days_ago','?')} jours), pente MM21 {fmt(b.get('cross_slope_mm21_pct'),'%')}",
        f"- RSI : {fmt(b.get('rsi'),'',0)}   |   Z-score régression : {fmt(b.get('regression_z'),'σ',1)}"
        + (f" (fenêtre {b.get('regression_window_years')} ans)" if b.get("regression_window_years") else ""),
        f"- Drawdown 52s : {fmt(b.get('drawdown_52w_pct'),'%')}"
        + (f"   |   Zone Fibo : {fibo}" if fibo else ""),
        f"- Fondamentaux (PRÉCISE toujours la période dans la prose) : croissance CA {fmt(b.get('rev_growth_pct'),'%')} = dernier trimestre publié en glissement annuel (a/a){(' au ' + b['mrq']) if b.get('mrq') else ''} · marge nette {fmt(b.get('net_margin_pct'),'%')} = TTM, 12 mois glissants · marge FCF {fmt(b.get('fcf_margin_pct'),'%')} = TTM",
        f"- Valorisation (CHIFFRE-la dans la prose ; n'invente AUCUN multiple absent) : PER forward {fmt(b.get('forward_pe'),'x',1)} · PER courant {fmt(b.get('trailing_pe'),'x',1)} · FCF yield {fmt(b.get('fcf_yield_pct'),'%',1)} · PEG {fmt(b.get('peg'),'',2)} · z-score {fmt(b.get('regression_z'),'σ',1)}. NB : un PER courant nettement supérieur au PER forward = bénéfices au creux de cycle (à expliquer, pas à confondre avec « cher »).",
    ]
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
            f"(prix tendance {fmt(b.get('prix_tendance'),'',0)}). Tu PEUX la commenter dans `futur` ou `resume`, "
            f"mais appelle-la « {sens} vs tendance », JAMAIS « marge de sécurité » (la référence est une trajectoire "
            f"historique, pas une valeur intrinsèque).{caveat}"
        )
    if b.get("target_upside_pct") is not None:
        lines.append(
            f"- Objectif consensus analystes : {fmt(b.get('target_upside_pct'),'%',0)} de potentiel "
            f"({b.get('target_analysts') or '?'} analystes) — indicatif, biais optimiste structurel documenté ; "
            f"si consensus et tendance long terme divergent fortement, ce désaccord mérite une phrase."
        )
    if warn:
        lines.append(f"- ⚠ Signal en transition : {warn}")
    just = stock.get("justification", "")
    if just:
        lines.append(f"- Justification screener : {just}")
    return "\n".join(lines)


# ── PROMPT ────────────────────────────────────────────────────────────────────
def build_prompt(stock, guide, news):
    """Construit le prompt de rédaction éditoriale pour un ticker.

    Intègre : le GUIDE de rédaction (autorité éditoriale), le breakdown chiffré,
    les news récentes si dispo, le schéma JSON EXACT attendu par le front.
    """
    ticker = stock["ticker"]
    today = str(date.today())

    news_block = (
        "Titres de presse récents (à recouper, ne JAMAIS inventer au-delà de ces faits) :\n"
        + "\n".join(f"  - {n}" for n in news)
        if news else
        "Aucune actualité fraîche récupérée pour ce ticker. Pour le champ `actu`, reste "
        "factuel et général (dernier trimestriel connu, faits structurels datés si tu en "
        "as) ; n'invente AUCUN chiffre ni AUCUNE date précise non vérifiable."
    )

    guide_block = (
        f"## GUIDE DE RÉDACTION (autorité éditoriale — applique-le scrupuleusement)\n{guide}\n\n"
        if guide else ""
    )

    return f"""{guide_block}Tu rédiges la fiche éditoriale du titre {ticker} pour « Signal », un screener
d'actions présenté comme un service éditorial d'information financière (statut Bêta/fictif).
Date du jour : {today}.

## DONNÉES QUANTITATIVES DU TITRE (issues du screener — source de vérité pour les chiffres techniques)
{breakdown_block(stock)}

## ACTUALITÉ
{news_block}

## TON & CONTRAINTES (NON NÉGOCIABLES)
- Ton PRÉCIS, FACTUEL, CLAIR et posé — analyste rigoureux. Plume vivante mais sobre : une
  pointe d'esprit pince-sans-rire est bienvenue de loin en loin, JAMAIS lourde, jamais un
  calembour gratuit, jamais de hype ni de ton promotionnel. Le fond prime sur le trait d'esprit.
- AUCUNE prétention d'alpha, AUCUN conseil d'achat/vente, AUCUN objectif de cours chiffré.
- Le score reflète une QUALITÉ à un instant T, JAMAIS un timing. Le timing technique est un
  GARDE-FOU (il pénalise chase/couteau), jamais une thèse d'achat.
- Nomme EXPLICITEMENT le type de douve (marque / coût / réseau / coûts de transfert /
  actif réglementaire) et QUESTIONNE sa durabilité (qu'est-ce qui la tuerait ?).
- CHIFFRE TOUT jugement de valorisation avec le NOMBRE fourni (PER forward, PER courant, FCF
  yield, PEG, z-score). Les qualificatifs vagues SEULS sont interdits (« fourchette haute »,
  « cher », « tendu » sans chiffre). N'invente JAMAIS un multiple historique ou de pair non
  fourni : pour le relatif-historique, appuie-toi sur le z-score (seule mesure sourcée ici).
- `bear` = la VRAIE inversion de thèse (ce qui ferait échouer la thèse / perte permanente),
  PAS seulement « c'est cher ».
- Reste dans le cercle de compétence : si la durabilité n'est pas évaluable, dis-le.
- Tu peux utiliser des balises <b>…</b> inline pour mettre en relief un chiffre clé
  (comme les fiches existantes), mais avec parcimonie. Pas d'autre HTML.
- Écris en FRANÇAIS.

## FORMAT DE SORTIE — JSON STRICT, RIEN D'AUTRE
Réponds UNIQUEMENT par un objet JSON valide (pas de texte avant/après, pas de backticks)
avec EXACTEMENT ces 6 clés, chacune un tableau de chaînes :
{{
  "resume": ["§1 : ce que fait la boîte en une phrase + le débat central. Relie le score {stock.get('score','?')}/100 à la qualité, pas au timing.", "§2 (optionnel) : cadrage valorisation en relatif."],
  "biz":    ["§ comment la boîte gagne de l'argent + marges.", "§ type de douve nommé + durabilité/menace."],
  "futur":  ["§ drivers de croissance.", "§ cadrage prix vs valeur (cher/correct/décoté en relatif, SANS cible chiffrée) + risques."],
  "actu":   ["§ faits récents datés et chiffrés (1 paragraphe dense)."],
  "bull":   ["puce 1 chiffrée", "puce 2 chiffrée", "puce 3 chiffrée"],
  "bear":   ["puce 1 (inversion)", "puce 2 (inversion)", "puce 3 (inversion)"]
}}

Contraintes de longueur : resume 1-2 §, biz 2 §, futur 2 §, actu 1 § dense,
bull et bear EXACTEMENT 3 puces chacun. Chaque § = 2 à 4 phrases."""


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


def parse_and_validate(raw):
    """Parse la réponse Claude et valide le schéma. Lève ValueError si invalide.

    Même nettoyage que portfolio_agent.py (strip ```json / ```), plus un filet de
    sécurité qui isole le 1er objet {...} si Claude entoure le JSON de prose.
    Chaque chaîne validée passe par _sanitize_html (allowlist <b> seulement).
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
    for field in ALL_FIELDS:
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


def generate_one(stock, guide):
    """Génère l'analyse d'un seul ticker. Retourne dict (6 champs + _sig) ou lève.

    Même pattern d'appel que portfolio_agent.py : client.messages.create(model, max_tokens,
    system, messages), puis response.content[0].text -> nettoyage -> json.loads.
    """
    news = fetch_news(stock["ticker"])
    prompt = build_prompt(stock, guide, news)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Tu es un analyste financier éditorial, neutre et factuel, pour un service "
            "d'information (Bêta/fictif). Tu ne donnes jamais de conseil ni d'objectif de "
            "cours. Tu réponds UNIQUEMENT en JSON valide, sans texte avant ou après, sans "
            "balises markdown ni backticks."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    # Diagnostics explicites : sans ces gardes, une réponse tronquée produisait un
    # « aucun objet JSON détecté » trompeur, et une réponse vide un IndexError opaque.
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise ValueError(f"réponse tronquée à {MAX_TOKENS} tokens (stop_reason=max_tokens) — augmenter MAX_TOKENS ?")
    if not response.content:
        raise ValueError("réponse vide du modèle (content=[])")
    raw = response.content[0].text
    analysis = parse_and_validate(raw)
    analysis["_sig"] = signature(stock)
    return analysis


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
    for stock, reason in skipped:
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
        print(f"     · {tk} ({reason}, score {stock.get('score','?')}) — {etat}")
    print("   Ces fiches gardent leur ancienne signature : le prochain run les reprendra,\n"
          "   en tête de file à priorité égale (score décroissant).")
    if os.getenv("GITHUB_ACTIONS"):
        # Annotation visible dans le résumé du run sans faire échouer l'étape : un
        # report est un fonctionnement nominal, pas une panne — mais il doit se voir.
        print(f"::warning::{len(skipped)} fiche(s) éditoriale(s) reportées faute de budget "
              f"({elapsed:.0f}s / {budget:.0f}s) : "
              f"{', '.join(s['ticker'] for s, _ in skipped)}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not client:
        print("❌ ANTHROPIC_API_KEY manquante — impossible de générer les analyses.")
        print("   Ajoutez-la dans l'environnement / les secrets CI, puis relancez.")
        print("   (analyses.json laissé INCHANGÉ — aucune écriture, sortie propre.)")
        sys.exit(1)

    watchlist = load_json(WATCHLIST_PATH, {})
    stocks = watchlist.get("stocks", []) if isinstance(watchlist, dict) else []
    if not stocks:
        print("❌ watchlist.json vide ou manquant — rien à générer. Lancez screener.py d'abord.")
        sys.exit(1)

    analyses = load_json(ANALYSES_PATH, {})
    if not isinstance(analyses, dict):
        print("  ⚠️  analyses.json illisible/mal formé — on repart d'un objet vide.")
        analyses = {}

    guide = load_guide()

    current_tickers = {s["ticker"] for s in stocks if s.get("ticker")}

    # 1) PURGE des orphelins (tickers qui ne sont plus dans la watchlist)
    orphans = [t for t in analyses if t not in current_tickers]
    for t in orphans:
        del analyses[t]
    if orphans:
        print(f"🧹 Purge {len(orphans)} orphelin(s) : {', '.join(sorted(orphans))}")

    # 2) DÉTECTION nouveau / modifié via signature
    #    - pas d'entrée               -> "nouveau"
    #    - signature changée          -> "modifié"
    #    - signature absente (legacy) -> capturée par "modifié" (None != sig calculée)
    #    - signature identique mais entrée incomplète -> "complétion"
    #    - signature identique ET entrée complète     -> on garde tel quel (0 appel API)
    todo = []
    unmarked = 0
    for s in stocks:
        tk = s.get("ticker")
        if not tk:
            continue
        existing = analyses.get(tk)
        new_sig = signature(s)
        if not existing:
            todo.append((s, "nouveau"))
        elif existing.get("_sig") != new_sig:
            todo.append((s, "modifié"))
        elif not entry_is_complete(existing):
            todo.append((s, "complétion"))
        elif existing.pop("_perime", None):
            # À jour et complet, mais elle portait une marque de péremption d'un run
            # précédent : soit elle a été régénérée depuis, soit sa signature est
            # revenue à sa valeur d'origine. Dans les deux cas le texte publié
            # correspond de nouveau au breakdown — la marque doit disparaître, sinon
            # le site afficherait un avertissement de péremption indéfiniment.
            unmarked += 1
        # sinon : à jour et complet -> conservé.

    # File de priorité : le budget ci-dessous ne servira peut-être pas tout le monde,
    # il doit donc servir d'abord ce qui manque au site. À priorité égale, score
    # décroissant — c'est le haut de watchlist qui est consulté.
    todo.sort(key=lambda item: (PRIORITY.get(item[1], 9), _neg_score(item[0])))

    kept = len(current_tickers) - len(todo)
    print(f"📋 Watchlist : {len(current_tickers)} tickers — "
          f"{len(todo)} à (re)générer, {kept} inchangé(s) conservé(s)"
          + (f", {unmarked} marque(s) de péremption levée(s)." if unmarked else "."))

    if not todo:
        # Rien à régénérer ; on réécrit si on a purgé des orphelins ou levé des marques.
        if orphans or unmarked:
            _write(analyses)
            print("✅ analyses.json mis à jour (purge orphelins / péremptions levées).")
        else:
            print("✅ Rien à faire — analyses.json déjà à jour.")
        return

    # 3) GÉNÉRATION incrémentale, robuste par ticker, sous budget wall-clock
    budget = _budget_seconds()
    started = time.monotonic()
    if budget <= 0:
        print("⏱️  Budget wall-clock DÉSACTIVÉ (ANALYSES_TIME_BUDGET_S <= 0) — "
              "la boucle ira au bout, y compris au-delà du timeout CI de 45 min.")
    else:
        print(f"⏱️  Budget wall-clock : {budget:.0f}s pour {len(todo)} fiche(s) à générer.")

    ok, fail = 0, 0
    durations = []
    skipped = []
    for i, (s, reason) in enumerate(todo):
        # On n'entame une fiche que si on estime pouvoir la FINIR. Une fiche commencée
        # puis tuée par le timeout CI ne coûte pas qu'elle-même : elle emporte l'étape
        # de commit, donc tout le travail déjà fait dans ce run, donc la reprise.
        # Estimation = pire durée observée, volontairement pessimiste : l'asymétrie est
        # totale entre « une fiche de moins cette semaine » et « le run entier perdu ».
        if budget > 0:
            elapsed = time.monotonic() - started
            estimate = max(durations) if durations else FIRST_TICKER_COST_S
            if elapsed + estimate > budget:
                skipped = todo[i:]
                break

        tk = s["ticker"]
        print(f"  ✍️  {tk} ({reason}) — score {s.get('score','?')}…", flush=True)
        t_start = time.monotonic()
        try:
            analyses[tk] = generate_one(s, guide)
            ok += 1
            print(f"     ✅ {tk} généré.")
        except Exception as e:
            fail += 1
            if tk in analyses:
                # On garde l'ancienne analyse — mieux qu'un trou affichant « À générer ».
                print(f"     ⚠️  {tk} échec ({e}) — ANCIENNE analyse conservée.")
            else:
                print(f"     ✗ {tk} échec ({e}) — pas d'analyse, le front affichera « À générer ».")
        # Un échec consomme du temps lui aussi : il compte dans le budget.
        durations.append(time.monotonic() - t_start)
        # Écriture (atomique) après chaque ticker : un crash en cours de run ne perd
        # pas le travail déjà fait. Attention, ce n'est vrai d'un run à l'autre que si
        # le job atteint son étape de commit — d'où le budget ci-dessus.
        _write(analyses)

    elapsed = time.monotonic() - started
    if skipped:
        _mark_stale(analyses, skipped, elapsed, budget)
    # Écriture finale : persiste les marques de péremption, y compris dans le cas
    # limite où le budget était déjà épuisé avant la première fiche.
    _write(analyses)

    print(f"\n✅ analyses.json écrit — {ok} généré(s), {fail} échec(s), {kept} conservé(s), "
          f"{len(orphans)} purgé(s), {len(skipped)} reporté(s) — {elapsed:.0f}s écoulées"
          + (f" / {budget:.0f}s de budget." if budget > 0 else " (budget désactivé)."))
    print(f"   Total entrées : {len(analyses)} (== {len(current_tickers)} si aucun échec sur un nouveau ticker).")
    # Sortie en SUCCÈS même avec des fiches reportées : un exit non nul déclencherait
    # l'étape « Signale les échecs IA » du workflow et rendrait le job rouge chaque
    # semaine pour un fonctionnement nominal — l'alarme finirait par n'être plus lue.


def _write(analyses):
    """Écrit analyses.json en UTF-8, ensure_ascii=False, indent=2 — écriture ATOMIQUE.

    On écrit dans un fichier temporaire du même dossier puis os.replace() : une
    interruption (crash, kill CI) ne peut pas laisser analyses.json tronqué/corrompu,
    ce qui casserait le fetch() JSON du front.

    allow_nan=False comme screener.py / portfolio_agent.py : un NaN sérialisé en
    `NaN` est refusé par JSON.parse() et casserait le rendu de TOUTES les fiches.
    Mieux vaut échouer ici, bruyamment, que publier un fichier illisible.
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
