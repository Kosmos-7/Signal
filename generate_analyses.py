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
  }, ... }

render() lit a.resume / a.biz / a.futur / a.actu / a.bull / a.bear et n'itère JAMAIS
sur les clés de l'entrée : `_sig` est donc invisible au front (vérifié index.html).
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


# Version du style/prompt éditorial — bumper FORCE la régénération de toutes les fiches
# (la signature change), p.ex. après un changement de ton ou d'exigence de chiffrage.
PROMPT_VERSION = "2026-06-sobre-chiffree"


def signature(stock):
    """Signature éditoriale stable d'un ticker. On régénère SEULEMENT si elle change.

    Composantes = ce qui modifie le *fond* de l'analyse, pas le bruit :
      - score            : note de synthèse (pilote resume + bull/bear)
      - cross_type       : golden / death / neutre  (régime narratif)
      - cross_days bucket: frais/recent/etabli/ancien (poids du signal, pas le J exact)
      - regression bucket: survente / neutre / surchauffe (cadrage prix vs valeur)
      - rev_growth arrondi à 5% près : la dynamique de croissance change le discours
      - signal_dynamics_warning présent/absent : nuance "signal en transition"
    Volontairement EXCLUS : rsi, fibo, drawdown au point de base près, val_pts —
    trop volatils d'un run à l'autre pour justifier un appel API coûteux (testé : un
    RSI 49->72 + cross +1j + z +0.1σ + drawdown -99% ne change PAS la signature).
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
        str(stock.get("score", "")),
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
        f"- RSI : {fmt(b.get('rsi'),'',0)}   |   Z-score régression : {fmt(b.get('regression_z'),'σ',2)}"
        + (f" (fenêtre {b.get('regression_window_years')} ans)" if b.get("regression_window_years") else ""),
        f"- Drawdown 52s : {fmt(b.get('drawdown_52w_pct'),'%')}"
        + (f"   |   Zone Fibo : {fibo}" if fibo else ""),
        f"- Fondamentaux (PRÉCISE toujours la période dans la prose) : croissance CA {fmt(b.get('rev_growth_pct'),'%')} = dernier trimestre publié en glissement annuel (a/a){(' au ' + b['mrq']) if b.get('mrq') else ''} · marge nette {fmt(b.get('net_margin_pct'),'%')} = TTM, 12 mois glissants · marge FCF {fmt(b.get('fcf_margin_pct'),'%')} = TTM",
        f"- Valorisation (CHIFFRE-la dans la prose ; n'invente AUCUN multiple absent) : PER forward {fmt(b.get('forward_pe'),'x',1)} · PER courant {fmt(b.get('trailing_pe'),'x',1)} · FCF yield {fmt(b.get('fcf_yield_pct'),'%',1)} · PEG {fmt(b.get('peg'),'',2)} · z-score {fmt(b.get('regression_z'),'σ',2)}. NB : un PER courant nettement supérieur au PER forward = bénéfices au creux de cycle (à expliquer, pas à confondre avec « cher »).",
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
        # sinon : à jour et complet -> conservé.

    kept = len(current_tickers) - len(todo)
    print(f"📋 Watchlist : {len(current_tickers)} tickers — "
          f"{len(todo)} à (re)générer, {kept} inchangé(s) conservé(s).")

    if not todo:
        # Rien à régénérer ; on réécrit seulement si on a purgé des orphelins.
        if orphans:
            _write(analyses)
            print("✅ analyses.json mis à jour (purge orphelins uniquement).")
        else:
            print("✅ Rien à faire — analyses.json déjà à jour.")
        return

    # 3) GÉNÉRATION incrémentale, robuste par ticker
    ok, fail = 0, 0
    for s, reason in todo:
        tk = s["ticker"]
        print(f"  ✍️  {tk} ({reason}) — score {s.get('score','?')}…", flush=True)
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
        # Écriture (atomique) après chaque ticker : un crash en cours de run ne perd
        # pas le travail déjà fait, et le prochain run reprend où on s'est arrêté.
        _write(analyses)

    print(f"\n✅ analyses.json écrit — {ok} généré(s), {fail} échec(s), {kept} conservé(s), "
          f"{len(orphans)} purgé(s).")
    print(f"   Total entrées : {len(analyses)} (== {len(current_tickers)} si aucun échec sur un nouveau ticker).")


def _write(analyses):
    """Écrit analyses.json en UTF-8, ensure_ascii=False, indent=2 — écriture ATOMIQUE.

    On écrit dans un fichier temporaire du même dossier puis os.replace() : une
    interruption (crash, kill CI) ne peut pas laisser analyses.json tronqué/corrompu,
    ce qui casserait le fetch() JSON du front.
    """
    ANALYSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(ANALYSES_PATH.parent), prefix=".analyses.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ANALYSES_PATH)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
