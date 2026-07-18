"""
portfolio_agent.py — Agent de portefeuille piloté par Claude API
C'est Claude qui raisonne sur les décisions d'achat/vente chaque semaine.

Il reçoit :
- L'état actuel du portefeuille (positions, performance, liquidités)
- La watchlist de la semaine (30 actions scorées)
- Le contexte de marché (CAC40, performances sectorielles)
- Les règles non négociables (patience, taille, panique, stop-loss)

Il décide :
- Quoi acheter, quoi vendre, quoi conserver — et pourquoi

Dépendances : pip install yfinance pandas ta requests anthropic
"""

import yfinance as yf
import json
import os
import re
import requests
from collections import Counter
from datetime import date, datetime, timedelta, timezone as _timezone
from anthropic import Anthropic

# Paramètres centralisés (frais transaction, PFU, VIX, …) — Phase 1+
import config

# ── CONFIG ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
FINNHUB_KEY          = os.getenv("FINNHUB_API_KEY", "")
CAPITAL_INITIAL_DEF  = 10000.0   # valeur par défaut uniquement pour portefeuille vide
CAPITAL_INITIAL      = CAPITAL_INITIAL_DEF  # sera écrasé au runtime par la valeur du JSON
POIDS_MAX            = 0.20
STOP_LOSS_PCT        = -15.0     # seuil de stop-loss standard (Règle 07, ≥ 90j détenus)
STOP_LOSS_CATASTROPHE_PCT = -25.0  # stop-loss catastrophe (Règle 08, sans condition de durée)
MAX_POSITIONS        = 20        # nb max de lignes simultanées (15→20 : ~5%/ligne, plafond appliqué à l'achat)
TICKER_CAC40         = "^FCHI"
# MSCI World — ETF EUR-denominated (iShares Core MSCI World UCITS, Xetra)
# Évite le mismatch de devise vs portfolio EUR : avant on utilisait URTH (USD)
# ce qui faussait la comparaison au benchmark selon le mouvement EUR/USD.
TICKER_MSCI          = "EUNL.DE"

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ── UTILITAIRES ──────────────────────────────────────────────────────────────
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def load_portfolio_strict(path="portfolio.json"):
    """Charge portfolio.json en échouant BRUYAMMENT s'il est corrompu.

    L'ancien fallback silencieux (load_json → portefeuille vide à 10 000 €)
    aurait ÉCRASÉ tout le portefeuille au run suivant un fichier corrompu.
    Fichier absent = premier run légitime → portefeuille vide.
    """
    if not os.path.exists(path):
        return portfolio_vide()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise SystemExit(f"❌ {path} illisible ({e}) — abandon SANS écrire pour préserver l'état existant")

def semaine():
    d = date.today()
    return f"Sem. {d.isocalendar()[1]} · {d.year}"

def last_valid_close(close_series):
    """Dernier Close non-NaN d'une série yfinance.

    Yahoo ajoute parfois une dernière ligne avec Close=NaN pour les places
    européennes après leur clôture (observé à partir du 2026-06-02 : le cron
    de 22h UTC a corrompu toutes les positions EU à NaN, rendant le JSON
    illisible par le navigateur). On ne retient que les closes valides.
    """
    try:
        closes = close_series.dropna()
        return float(closes.iloc[-1]) if not closes.empty else None
    except Exception:
        return None

def save_json_atomic(path, data):
    """Écriture atomique (tmp + os.replace) et stricte (allow_nan=False).

    allow_nan=False fait échouer le job BRUYAMMENT si un NaN/Infinity se
    glisse dans les données : un NaN écrit en silence produit un JSON que
    JSON.parse côté navigateur rejette — site figé sans aucun signal CI.
    """
    import tempfile
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

def get_prix(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            print(f"  ⚠️  get_prix({ticker}) — historique vide (marché fermé ou ticker invalide)")
            return None
        prix = last_valid_close(hist["Close"])
        if prix is None:
            print(f"  ⚠️  get_prix({ticker}) — aucun close valide sur 5j (closes NaN)")
            return None
        try:
            info_curr = getattr(t.fast_info, 'currency', '') or ''
        except Exception:
            info_curr = ''
        if info_curr == 'GBp':
            prix = prix / 100
        return round(prix, 4)
    except Exception as e:
        print(f"  ⚠️  get_prix({ticker}) — erreur fetch : {e}")
        return None

def get_eur_usd_rate():
    """Taux EUR/USD du jour via Yahoo Finance (EURUSD=X). Fallback 1.10."""
    try:
        v = last_valid_close(yf.Ticker("EURUSD=X").history(period="2d")["Close"])
        return round(v, 4) if v else 1.10
    except:
        return 1.10

def get_eur_gbp_rate():
    """Taux EUR/GBP du jour via Yahoo Finance (EURGBP=X). Fallback 0.86."""
    try:
        v = last_valid_close(yf.Ticker("EURGBP=X").history(period="2d")["Close"])
        return round(v, 4) if v else 0.86
    except:
        return 0.86

def detect_currency(ticker, market=""):
    """Détermine la devise native d'un ticker (EUR / USD / GBP / DKK / SEK / NOK / CHF).

    Correction 2026-06-10 : Copenhague (.CO), Stockholm (.ST) et Oslo (.OL)
    étaient mappés EUR alors qu'ils cotent en couronnes — ORSTED.CO a été
    acheté avec un prix DKK traité comme EUR (quantité 7 au lieu de 52).
    """
    t = ticker.upper()
    m = (market or "").upper()
    # Couronnes nordiques (hors zone euro)
    if t.endswith(".CO") or "CPH" in m:
        return "DKK"
    if t.endswith(".ST") or "OMX" in m or "STO" in m:
        return "SEK"
    if t.endswith(".OL") or "OSL" in m:
        return "NOK"
    # Franc suisse — sans cette branche, un titre .SW était traité en USD :
    # conversion via EUR/USD (~1.10) au lieu de EUR/CHF (~0.93), ~15-18% d'écart
    # sur toutes les valeurs (le code CHF de to_eur était inatteignable).
    if t.endswith(".SW") or "EBS" in m or "SWX" in m:
        return "CHF"
    # Suffixes Yahoo Finance → EUR (zone euro uniquement)
    if any(t.endswith(s) for s in [".AS", ".PA", ".DE", ".BR", ".MI", ".MC", ".AT",
                                    ".HE", ".VI", ".LI"]):
        return "EUR"
    # Codes marché → EUR (zone euro)
    EUR_MARKETS = {
        "PAR", "EPA", "AMS", "EURONEXT", "FRA", "XETRA", "ETR", "GER",
        "MIL", "BIT", "MCE", "BME", "HEL", "WSE",
        "VIE", "ATH", "LIS",
    }
    if any(k in m for k in EUR_MARKETS):
        return "EUR"
    # GBP
    if t.endswith(".L") or "LSE" in m or "IOB" in m:
        return "GBP"
    return "USD"

# FX à la volée pour les devises hors USD/GBP (passées en paramètres historiques).
# Cache par run — un seul fetch par devise.
_FX_PAIRS    = {"DKK": "EURDKK=X", "SEK": "EURSEK=X", "NOK": "EURNOK=X", "CHF": "EURCHF=X"}
_FX_FALLBACK = {"DKK": 7.46, "SEK": 11.3, "NOK": 11.6, "CHF": 0.93}
_fx_cache    = {}

def get_eur_rate(currency):
    """Taux EUR→devise (convention Yahoo : EURXXX=X = nb XXX pour 1 EUR)."""
    if currency in _fx_cache:
        return _fx_cache[currency]
    try:
        v = last_valid_close(yf.Ticker(_FX_PAIRS[currency]).history(period="2d")["Close"])
        rate = round(v, 4) if v else _FX_FALLBACK[currency]
    except Exception:
        rate = _FX_FALLBACK.get(currency, 1.0)
    _fx_cache[currency] = rate
    return rate

def to_eur(montant, currency, eur_usd, eur_gbp=0.86):
    """Convertit un montant en devise native vers EUR.

    Conventions FX (Yahoo) :
      EURUSD=X = nb USD pour 1 EUR (ex: 1.18) → USD→EUR : montant / eur_usd
      EURGBP=X = nb GBP pour 1 EUR (ex: 0.86) → GBP→EUR : montant / eur_gbp
    Anciennement la formule GBP utilisait `montant * eur_gbp` (sous-évaluation
    de ~26%) puis avant ça `montant / (eur_usd * 0.86)` (proche de 1:1, aussi
    incorrect). Les positions GBP stockées avec ces formules sont migrées
    automatiquement dans maj_position().
    """
    if currency == "USD":
        return round(montant / eur_usd, 2)
    if currency == "GBP":
        return round(montant / eur_gbp, 2)
    if currency in _FX_PAIRS:   # DKK / SEK / NOK / CHF — fetch à la volée (cache par run)
        return round(montant / get_eur_rate(currency), 2)
    return round(montant, 2)

def maj_position(pos, eur_usd, eur_gbp=0.86):
    """
    Met à jour une position : valeur_actuelle en EUR, migre montant_investi
    si stocké avec une ancienne formule GBP, recalcule performance en EUR.
    Retourne True si le prix a pu être récupéré.
    """
    prix = get_prix(pos["ticker"])
    if not prix or prix != prix:   # None, 0 ou NaN (NaN != NaN) → garde la valeur précédente
        return False
    # Garde de sanité : un prix qui varie de plus de ×3 / ÷3 d'un run à l'autre est
    # presque toujours une erreur de données (GBp non converti = ×100, split non
    # ajusté, devise) — on refuse la maj et on alerte plutôt que de corrompre.
    prev = pos.get("prix_actuel")
    if prev and prev == prev and prev > 0:
        ratio = prix / prev
        if ratio > 3 or ratio < 1 / 3:
            print(f"  🚨 {pos['ticker']} : prix {prix} aberrant vs précédent {prev} (×{ratio:.2f}) — maj refusée (split ? devise ?)")
            return False
    currency = pos.get("currency") or detect_currency(pos["ticker"], pos.get("market", ""))
    pos["currency"]        = currency
    pos["prix_actuel"]     = prix
    pos["valeur_actuelle"] = to_eur(prix * pos["quantite"], currency, eur_usd, eur_gbp)

    # ── Migration GBP : 2 anciennes formules incorrectes existent dans les positions
    # historiques. La formule correcte (montant / eur_gbp) donne ~1.16× la valeur
    # GBP native. Toute position GBP dont montant_investi est strictement inférieur
    # à 0.97× la valeur correcte a été stockée avec une ancienne formule → recompute.
    if currency == "GBP":
        native_gbp  = round(pos["prix_achat"] * pos["quantite"], 2)
        correct_eur = round(native_gbp / eur_gbp, 2)
        stored      = pos.get("montant_investi", 0)
        if stored > 0 and stored < correct_eur * 0.97:
            print(f"  🔧 {pos['ticker']} montant_investi migré : {stored:.2f}€ → {correct_eur:.2f}€ (ancienne formule GBP)")
            pos["montant_investi"] = correct_eur

    # ── Correction legacy USD : montant_investi stocké en USD natif
    elif currency == "USD":
        LEGACY_CUTOFF = "2026-05-05"
        if pos.get("date_achat", "9999") < LEGACY_CUTOFF:
            native = round(pos["prix_achat"] * pos["quantite"], 2)
            stored = pos.get("montant_investi", 0)
            if stored > 0 and abs(stored - native) / (native + 1) < 0.05:
                pos["montant_investi"] = to_eur(native, currency, eur_usd, eur_gbp)

    # Performance en € — cohérent avec valeur_actuelle et montant_investi (tous deux en EUR)
    if pos.get("montant_investi", 0) > 0:
        pos["performance"] = round(
            (pos["valeur_actuelle"] - pos["montant_investi"]) / pos["montant_investi"] * 100, 2
        )
    return True

def market_status(now_utc=None):
    """Statut d'ouverture des marchés majeurs au moment du run.

    Heures approximatives (winter UTC, ne tient pas compte du DST exact) :
      Euronext (Paris/AMS/Bruxelles) + Xetra (DAX) : 8h-16h30 UTC
      LSE (Londres)                                : 8h-16h30 UTC
      US (NYSE/NASDAQ)                             : 14h30-21h UTC

    Tokyo (TSM ADR négocié à NYSE — donc traité comme US).
    Weekends : tous fermés.
    Jours fériés non gérés (rare et imprévisible sans calendrier dédié).
    """
    if now_utc is None:
        now_utc = datetime.utcnow()
    h = now_utc.hour + now_utc.minute / 60
    weekday = now_utc.weekday()  # 0=lundi, 6=dimanche
    if weekday >= 5:
        return {
            "EU":  "fermé (weekend)",
            "LSE": "fermé (weekend)",
            "US":  "fermé (weekend)",
        }
    return {
        "EU":  "ouvert" if 8 <= h < 16.5 else f"fermé (ouverture à 8h UTC)",
        "LSE": "ouvert" if 8 <= h < 16.5 else f"fermé (ouverture à 8h UTC)",
        "US":  "ouvert" if 14.5 <= h < 21 else f"fermé (ouverture à 14h30 UTC)",
    }


def get_contexte_marche(last_known_vix=None, prev_mode_panique=False):
    """Récupère le contexte macro de la semaine + statut temporel et marchés.

    `last_known_vix` : valeur de cache du VIX (en cas de fetch échoué). Si None,
    fallback ultime à 18 (médiane historique du VIX). Passé depuis portfolio.json
    pour permettre une persistance entre runs.
    `prev_mode_panique` : état persisté du run précédent — si le benchmark est
    infetchable, le mode panique est CONSERVÉ au lieu d'être désarmé (fail-open) :
    une panne Yahoo pendant un krach est précisément le scénario où la Règle 03
    doit tenir.
    """
    ctx = {}
    annee = date.today().year
    debut = f"{annee}-01-01"

    for label, ticker in [("cac40", TICKER_CAC40), ("msci", TICKER_MSCI)]:
        try:
            hist = yf.Ticker(ticker).history(start=debut)["Close"].dropna()
            if len(hist) >= 2:
                perf_ytd    = round((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0] * 100, 2)
                # 5 séances de bourse = iloc[-6] (iloc[-5] ne couvrait que 4 intervalles
                # → le seuil panique -5% « sur la semaine » était mesuré sur une fenêtre tronquée)
                perf_1sem   = round((hist.iloc[-1] - hist.iloc[-6]) / hist.iloc[-6] * 100, 2) if len(hist) >= 6 else 0
                ctx[label] = {"perf_ytd": perf_ytd, "perf_semaine": perf_1sem}
        except Exception as e:
            # Ne PAS écrire de 0 : main() retombe alors sur les valeurs persistées de
            # portfolio.json (même comportement qu'update_prices.py, qui conserve la
            # valeur précédente) au lieu de publier un benchmark écrasé à zéro.
            print(f"   ⚠️  Benchmark {label} indisponible ({type(e).__name__}) — valeurs précédentes conservées")

    # ── VIX — indicateur contextuel (affichage dashboard + prompt) ; hors scoring depuis v3
    # Stratégie de fallback en 3 niveaux :
    #   1. Fetch yfinance ^VIX (close du jour)
    #   2. last_known_vix (= dernier VIX en cache dans portfolio.json)
    #   3. 18.0 (médiane historique VIX 2000-2024)
    vix_value  = None
    vix_source = "fallback"
    try:
        vix_hist = yf.Ticker("^VIX").history(period="5d")["Close"].dropna()
        if not vix_hist.empty:
            vix_value  = round(float(vix_hist.iloc[-1]), 2)
            vix_source = "live"
    except Exception as e:
        print(f"   ⚠️  ^VIX fetch failed ({e}) — fallback cache ou médiane historique")
    if vix_value is None:
        if last_known_vix is not None and last_known_vix > 0:
            vix_value  = last_known_vix
            vix_source = "cache"
        else:
            vix_value  = 18.0
            vix_source = "median_historique"
    ctx["vix"]        = vix_value
    ctx["vix_source"] = vix_source
    ctx["vix_multiplier"] = round(config.vix_multiplier(vix_value), 3)

    # Mode panique — sticky si le benchmark est indisponible (jamais fail-open)
    if "cac40" in ctx:
        ctx["mode_panique"] = ctx["cac40"]["perf_semaine"] < -5.0
    else:
        ctx["mode_panique"] = bool(prev_mode_panique)
        if prev_mode_panique:
            print("   ⚠️  Mode panique CONSERVÉ du run précédent (benchmark indisponible)")

    # Conscience temporelle
    now_utc = datetime.utcnow()
    jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    ctx["date"]         = str(date.today())
    ctx["jour_semaine"] = jours_fr[now_utc.weekday()]
    ctx["heure_utc"]    = now_utc.strftime("%Hh%M")
    ctx["semaine"]      = semaine()
    ctx["marches"]      = market_status(now_utc)

    return ctx

_TAG_RE = re.compile(r"<[^>]*>")

def _texte_externe_sain(s):
    """Neutralise tout balisage HTML d'une chaîne d'origine externe (news Finnhub).

    Ces textes sont injectés (1) dans les prompts Claude et (2) dans portfolio.json,
    rendu par le dashboard : aucune balise tierce ne doit survivre en amont.
    """
    return _TAG_RE.sub("", str(s or "")).replace("<", "‹").replace(">", "›").strip()

_MACRO_KEYWORDS = [
    # US monetary
    "federal reserve", "fed rate", "fed cuts", "fed hikes", "fomc", "powell",
    "interest rate", "rate cut", "rate hike", "rate decision",
    # Inflation / activity
    "inflation", "cpi", "ppi", "pce", "pmi", "ism",
    "unemployment", "nonfarm payroll", "jobless claims", "jobs report",
    "gdp", "recession", "soft landing", "stagflation",
    # EU / UK / Asia central banks
    "ecb", "european central bank", "bce", "lagarde",
    "bank of england", "boe rate", "bailey",
    "boj", "bank of japan", "ueda",
    "pboc", "people's bank of china",
    # Geopol / commodities / FX
    "tariff", "trade war", "trade deal", "sanctions",
    "treasury yield", "yield curve", "10-year", "bond market",
    "dollar index", "dxy", "yen", "yuan",
    "opec", "crude oil", "brent", "wti",
    # Markets-wide
    "vix", "volatility index", "earnings season",
]

# Sources structurellement biaisées (thèses promo non journalistiques) — autorisées
# mais déprimées dans le scoring pour qu'elles ne phagocytent pas la sélection
_LOW_QUALITY_SOURCES = {"SeekingAlpha", "Seeking Alpha"}
_PER_SOURCE_CAP = 2   # max 2 articles par source pour forcer la diversité

def get_macro_news():
    """Récupère les ~6 titres macro les plus pertinents via Finnhub /news.

    Diversification :
      - Pool élargi (200 articles parcourus, vs 60 avant)
      - Cap de 2 articles par source (pas 4 articles Reuters)
      - Sources low-quality (Seeking Alpha) déprimées dans le scoring
      - Keyword set élargi (BoJ, PBoC, FX, commodités, VIX)

    Retourne une liste de dicts {headline, summary, date, source, url}."""
    if not FINNHUB_KEY:
        return []
    try:
        # Clé en header (pas en query-string) : une exception requests loggue l'URL
        # complète — le token ne doit jamais y figurer.
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "minId": 0},
            headers={"X-Finnhub-Token": FINNHUB_KEY},
            timeout=5,
        )
        if r.status_code != 200:
            return []
        articles = r.json()
        if not isinstance(articles, list):
            return []

        # Pass 1 : filtre keyword + dédup par URL
        candidates = []
        seen_urls = set()
        for article in articles[:200]:
            url_a = article.get("url", "")
            if url_a and url_a in seen_urls:
                continue
            text = ((article.get("headline") or "") + " " + (article.get("summary") or "")).lower()
            if not any(kw in text for kw in _MACRO_KEYWORDS):
                continue
            if url_a:
                seen_urls.add(url_a)
            # Score = nb de keywords matchés (proxy de "macro-density")
            kw_score = sum(1 for kw in _MACRO_KEYWORDS if kw in text)
            source = article.get("source", "")
            if source in _LOW_QUALITY_SOURCES:
                kw_score -= 1  # déprime mais n'élimine pas
            candidates.append({
                "kw_score":  kw_score,
                "datetime":  article.get("datetime", 0),
                "headline":  _texte_externe_sain(article.get("headline"))[:140],
                "summary":   _texte_externe_sain(article.get("summary"))[:600],
                "source":    _texte_externe_sain(source)[:60],
                "url":       url_a,
            })

        # Pass 2 : tri par (kw_score desc, datetime desc) — pertinence puis fraîcheur
        candidates.sort(key=lambda c: (-c["kw_score"], -c["datetime"]))

        # Pass 3 : sélection avec cap par source pour forcer diversité
        selected = []
        per_source_count = {}
        for c in candidates:
            src = c["source"] or "unknown"
            if per_source_count.get(src, 0) >= _PER_SOURCE_CAP:
                continue
            art_date = datetime.fromtimestamp(c["datetime"], tz=_timezone.utc).strftime("%Y-%m-%d") if c["datetime"] else ""
            selected.append({
                "headline": c["headline"],
                "summary":  c["summary"],
                "date":     art_date,
                "source":   c["source"],
                "url":      c["url"],
            })
            per_source_count[src] = per_source_count.get(src, 0) + 1
            if len(selected) >= 6:
                break

        return selected
    except Exception as e:
        # type seul — l'exception requests peut contenir l'URL de la requête
        print(f"  ⚠️  Macro news — exception : {type(e).__name__}")
        return []

def portfolio_vide():
    return {
        "updated_at": str(date.today()), "week": semaine(),
        "capital_initial": CAPITAL_INITIAL_DEF, "capital_actuel": CAPITAL_INITIAL_DEF,
        "performance": 0.0, "benchmark_cac40": 0.0, "benchmark_msci": 0.0,
        "vs_benchmark": 0.0, "positions": [],
        "liquidites": CAPITAL_INITIAL_DEF, "ordres": [], "biais_detectes": [],
        "analyse_claude": None, "performance_history": [], "max_drawdown": 0.0,
    }

def calc_max_drawdown(history):
    """Drawdown sur valeur absolue du capital (en %).
    Utilise le champ 'capital' si disponible, sinon 'perf' en fallback.
    Évite de compter les injections de capital comme des gains."""
    if not history:
        return 0.0
    peak = float('-inf')
    max_dd = 0.0
    for h in history:
        if h.get("capital") is not None:
            v = h["capital"]
        else:
            # Fallback : 'perf' est en %, on reconstitue la valeur sur CAPITAL_INITIAL
            v = CAPITAL_INITIAL * (1 + h.get("perf", 0) / 100)
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak * 100
            if dd < max_dd:
                max_dd = dd
    return round(max_dd, 2)

# ── FEEDBACK LOOP : BIAIS → RÈGLES AUTO ──────────────────────────────────────

# Familles sectorielles — les libellés yfinance fragmentent le tech (Semi-conducteurs,
# Équip. semi., Médias & IA…) qui sont en réalité fortement corrélés (cycle, supply chain).
# On regroupe en clusters pour que R1 voie le risque réel.
SECTOR_CLUSTERS = {
    "Technologie":       "Tech & IA",
    "Semi-conducteurs":  "Tech & IA",
    "Équip. semi.":      "Tech & IA",
    "Médias & IA":       "Tech & IA",
    # Les autres secteurs restent eux-mêmes (Finance, Santé, Industrie, etc.)
}

def cluster_for(sector):
    """Renvoie le cluster d'un secteur, ou le secteur lui-même s'il n'est pas regroupé."""
    return SECTOR_CLUSTERS.get(sector, sector)

def calculer_regles_auto(portfolio):
    """
    Règles mécaniques — s'appliquent AVANT Claude et dans executer_decisions().
    Basées sur la valeur du portfolio, pas sur le comptage arbitraire de titres.

    R1 : Concentration sectorielle GRADUÉE (passage du binaire au soft penalty)
         - < 30%               : aucune restriction
         - 30-65%              : sizing réduit proportionnellement (factor 1.0 → 0.1)
                                 Forte conviction bypasse à 50% minimum.
         - > 65%               : blocage strict (concentration excessive)
    R2 : 1 position > 20% du capital → renforcement bloqué
    R3 : Liquidités < 5% du capital → achats bloqués
    """
    positions  = portfolio.get("positions", [])
    liquidites = portfolio.get("liquidites", CAPITAL_INITIAL)
    capital    = portfolio.get("capital_actuel", CAPITAL_INITIAL)
    regles     = []

    if capital <= 0:
        return regles

    # R1 — Concentration par cluster sectoriel (regroupe les secteurs corrélés)
    # Soft penalty graduée : informationnelle si 30-65%, blocage strict si >65%.
    # Le sizing factor effectif est calculé dans executer_decisions() à partir
    # du pct_concentration exposé ici.
    valeur_par_cluster = {}
    for p in positions:
        s = p.get("sector", "—")
        if s and s != "—":
            cl = cluster_for(s)
            valeur_par_cluster[cl] = valeur_par_cluster.get(cl, 0) + p.get("valeur_actuelle", 0)
    for cl, val in valeur_par_cluster.items():
        pct = val / capital * 100
        if pct > 65:
            # Blocage strict — concentration excessive
            regles.append({
                "type":         "concentration_sectorielle",
                "secteur":      cl,
                "pct":          round(pct, 1),
                "regime":       "strict",
                "message":      f"Cluster {cl} : {pct:.0f}% > 65% — concentration excessive, achats bloqués",
                "bloque":       True,
            })
        elif pct > 30:
            # Soft penalty : sizing réduit progressivement, bypass partiel si conviction forte
            # factor = clip(1 - (pct-30)/35, 0.1, 1.0)
            #   → 30% : 1.00 (intact)
            #   → 40% : 0.71
            #   → 50% : 0.43
            #   → 60% : 0.14
            #   → 65% : 0.10 (plancher)
            factor = max(0.1, 1.0 - (pct - 30) / 35.0)
            regles.append({
                "type":         "concentration_sectorielle",
                "secteur":      cl,
                "pct":          round(pct, 1),
                "regime":       "soft",
                "sizing_factor": round(factor, 2),
                "message":      f"Cluster {cl} : {pct:.0f}% > 30% — sizing réduit ×{factor:.2f} (achats possibles avec conviction forte ou taille réduite)",
                "bloque":       False,  # n'empêche pas l'achat, juste le sizing
            })

    # R2 — Position individuelle > 20% du capital (déjà en portefeuille)
    for p in positions:
        pct = p.get("valeur_actuelle", 0) / capital * 100
        if pct > 20:
            regles.append({
                "type":    "position_oversized",
                "ticker":  p["ticker"],
                "message": f"{p['ticker']} représente {pct:.0f}% du capital > 20% — renforcement bloqué",
                "bloque":  True,
            })

    # R3 — Liquidités < 5% du capital
    pct_liq = liquidites / capital * 100
    if pct_liq < 5:
        regles.append({
            "type":    "liquidites_faibles",
            "message": f"Liquidités {pct_liq:.1f}% < 5% du capital ({liquidites:.0f}€) — achats bloqués",
            "bloque":  True,
        })

    return regles


# ── SKILL INJECTION (single source of truth : skill project-level committable) ──
def load_skill_discipline():
    """Lit le SKILL.md depuis le project-level skill (.claude/skills/portfolio-analyst/).

    Architecture (cf décisions 2026-05-10) :
    - Le skill est versionné dans le repo Git, déployé avec le code.
    - Sur runner GitHub Actions : lecture via chemin relatif, marche partout où le repo est cloné.
    - En local Claude Code : Claude Code charge automatiquement la version user-level
      (~/.claude/skills/) qui est synchronisée vers project-level via `python sync_skill.py`.
    - Hiérarchie Claude Code : personal > project — donc en local le user-level prime,
      et le project-level (committable) est l'artefact pour la production.

    Returns:
        str: contenu markdown du skill (sans frontmatter YAML), ou "" si introuvable.
    """
    from pathlib import Path
    skill_path = Path(__file__).parent / ".claude" / "skills" / "portfolio-analyst" / "SKILL.md"
    if not skill_path.exists():
        print(f"  ⚠️  load_skill_discipline — skill absent à {skill_path} (sync_skill.py exécuté ?)")
        return ""
    try:
        content = skill_path.read_text(encoding="utf-8")
        # Strip frontmatter YAML (--- ... ---)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content
    except Exception as e:
        print(f"  ⚠️  load_skill_discipline — exception : {e}")
        return ""


# ── PROMPT CLAUDE ────────────────────────────────────────────────────────────
def construire_prompt_analyse(portfolio, watchlist, contexte, macro_news=None):
    """
    Passe 1 — Analyse neutre, SANS décision d'achat/vente.
    Sépare l'analyse du raisonnement décisionnel pour éviter la rationalisation LLM :
    un modèle qui analyse et décide en même temps peut rationnaliser n'importe quelle position
    avec les mêmes données selon l'angle de lecture du moment.
    """
    positions = portfolio.get("positions", [])
    today     = str(date.today())

    pos_lines = []
    for p in positions:
        date_achat   = p.get("date_achat", today)
        jours        = (datetime.today() - datetime.strptime(date_achat, "%Y-%m-%d")).days if date_achat else 0
        raison_achat = p.get("raison_achat", "Non documentée")
        pos_lines.append(
            f"  {p['ticker']} ({p['nom']}) — perf {p.get('performance',0):+.1f}% — {jours}j détenus\n"
            f"    Thèse d'achat originale : {raison_achat[:250]}"
        )

    top10_lines = []
    for s in watchlist.get("stocks", [])[:10]:
        bd     = s.get("breakdown", {})
        z      = bd.get("regression_z")
        regime = bd.get("cross_regime", "")
        days   = bd.get("cross_days_ago")
        dyn_warn = bd.get("signal_dynamics_warning", "")
        val_pts = bd.get("val_pts")
        dd52w   = bd.get("drawdown_52w_pct")
        fibo    = bd.get("fibo") or {}
        icon   = "🟢" if regime == "golden" else "🔴" if regime == "death" else "⚪"
        cross_str = f" {icon} {regime.upper()} {days}j" if days is not None and regime in ("golden","death") else ""
        z_str = f" z={z:+.1f}σ" if z is not None else ""
        # Timing d'entrée : drawdown 52w + zone Fibo (annotation chartiste)
        val_str = f" val={val_pts}/5 (DD{dd52w:+.1f}%)" if val_pts is not None and dd52w is not None else ""
        fibo_str = f" [{fibo['closest_fibo']}]" if fibo.get("closest_fibo") else ""
        warn_str = f"\n      ⚠ {dyn_warn}" if dyn_warn else ""
        top10_lines.append(
            f"  #{s['rank']} {s['ticker']} score={s['score']}/100{cross_str}{z_str}{val_str}{fibo_str} — {s.get('justification','')[:100]}{warn_str}"
        )

    macro_section = ""
    if macro_news:
        news_lines = "\n".join(
            f"  - [{n['date']}] **{n['headline']}** ({n['source']})\n    → {n.get('summary','')[:400]}"
            for n in macro_news  # plus de cap [:4] — get_macro_news() retourne déjà ≤6 articles diversifiés
        )
        macro_section = f"\n## MACRO (titres + contenu de la dépêche, exploite-les pour ton analyse)\n{news_lines}\n"

    # Conscience temporelle
    derniere_maj = portfolio.get("updated_at", "—")
    try:
        delta_j = (date.today() - datetime.strptime(derniere_maj, "%Y-%m-%d").date()).days
        delta_str = f"il y a {delta_j} jour{'s' if delta_j > 1 else ''}" if delta_j else "aujourd'hui (déjà run plus tôt)"
    except Exception:
        delta_str = "inconnu"
    marches = contexte.get("marches", {})
    marches_str = f"EU {marches.get('EU','?')} | LSE {marches.get('LSE','?')} | US {marches.get('US','?')}"

    return f"""Analyse le portefeuille Signal de façon neutre et factuelle.
Tu es ANALYSTE — PAS décideur. N'émets aucune recommandation d'achat ou de vente.

## DATE & MARCHÉS
- Run actuel       : {contexte.get('jour_semaine','?')} {today} {contexte.get('heure_utc','?')} UTC ({contexte.get('semaine','?')})
- Dernière mise à jour : {derniere_maj} ({delta_str})
- Marchés au moment du run : {marches_str}

## POSITIONS EN COURS
{chr(10).join(pos_lines) if pos_lines else "  Aucune position"}

## WATCHLIST TOP 10
{chr(10).join(top10_lines)}

## MARCHÉ
- CAC40 semaine : {contexte.get('cac40',{}).get('perf_semaine',0):+.1f}% | MSCI : {contexte.get('msci',{}).get('perf_semaine',0):+.1f}%
{macro_section}
Pour chaque position : identifie forces, risques actuels, et surtout ce qui a changé vs la thèse d'achat.
Pour les 5 meilleures opportunités watchlist : évalue qualité du signal et timing.

🕒 **Ancre tes observations dans le temps** : "ce qui a changé depuis l'achat [date]" ou "depuis le dernier run [derniere_maj]". La synthèse_marche doit explicitement nommer la fenêtre couverte (ex : "sur la semaine écoulée"), pas "actuellement" sans repère.

JSON uniquement :
{{
  "positions_analyse": {{
    "TICKER": {{
      "forces": ["..."],
      "risques": ["..."],
      "delta_these": "Ce qui a concrètement changé depuis l'achat vs la thèse initiale (ou 'Rien de fondamental')",
      "etat": "solide" | "surveiller" | "deteriore"
    }}
  }},
  "opportunites_analyse": {{
    "TICKER": {{
      "signal_qualite": "forte" | "moderee" | "faible",
      "timing": "optimal" | "acceptable" | "premature",
      "resume": "..."
    }}
  }},
  "synthese_marche": "Contexte macro en 1-2 phrases"
}}"""


def construire_prompt(portfolio, watchlist, contexte, analyse=None, macro_news=None, regles_auto=None):
    """Construit le prompt envoyé à Claude avec tout le contexte.

    `regles_auto` : liste des règles mécaniques actuellement actives (R01/R03)
    — injectées dans le prompt pour que Claude SACHE quelles actions seront
    automatiquement bloquées et n'en propose plus.
    """

    positions = portfolio.get("positions", [])
    liquidites = portfolio.get("liquidites", CAPITAL_INITIAL)
    capital = portfolio.get("capital_actuel", CAPITAL_INITIAL)
    perf = portfolio.get("performance", 0)            # nette de frais + impôts
    perf_brute = portfolio.get("performance_brute", perf)  # ce qu'on aurait sans friction
    bench = portfolio.get("benchmark_msci", 0)  # MSCI World est le benchmark primaire (vs_benchmark = perf - bench_msci)
    vs = portfolio.get("vs_benchmark", 0)
    # Compteurs cumulatifs frais + fiscalité (Phase 1)
    frais_cum  = portfolio.get("total_frais_payes", 0)
    impots_cum = portfolio.get("total_impots_payes", 0)
    pertes_cum = portfolio.get("total_pertes_reportables", 0)

    today = str(date.today())

    # Conscience temporelle : date du run + délai depuis la dernière mise à jour
    # Permet à Claude de raisonner différemment si le run vient après 7j (cron normal)
    # ou après quelques heures (run manuel) — dans ce dernier cas, peu de raison d'agir.
    derniere_maj = portfolio.get("updated_at", "—")
    try:
        delta_j = (date.today() - datetime.strptime(derniere_maj, "%Y-%m-%d").date()).days
        if delta_j == 0:
            derniere_maj_str = f"{derniere_maj} (aujourd'hui — déjà run plus tôt, peu de raison d'agir à nouveau sauf événement)"
        elif delta_j == 1:
            derniere_maj_str = f"{derniere_maj} (hier)"
        else:
            derniere_maj_str = f"{derniere_maj} (il y a {delta_j} jours)"
    except Exception:
        derniere_maj_str = derniere_maj

    # Format positions — inclut la thèse d'achat originale pour éviter les contradictions
    pos_lines = []
    for p in positions:
        date_achat   = p.get("date_achat", "")
        jours        = (datetime.today() - datetime.strptime(date_achat, "%Y-%m-%d")).days if date_achat else 0
        raison_achat = p.get("raison_achat", "Non documentée")
        # Enrichi avec l'analyse passe 1 si disponible
        analyse_pos  = (analyse or {}).get("positions_analyse", {}).get(p["ticker"], {})
        delta_these  = analyse_pos.get("delta_these", "")
        etat         = analyse_pos.get("etat", "")
        etat_str     = f" | état : {etat}" if etat else ""
        delta_str    = f"\n    → Delta thèse : {delta_these}" if delta_these else ""
        qte = max(p["quantite"], 1)
        px_achat_eur = round(p.get("montant_investi", p["prix_achat"]) / qte, 2)
        px_actuel_eur = round(p.get("valeur_actuelle", 0) / qte, 2)
        pos_lines.append(
            f"  - {p['ticker']} ({p['nom']}) : {p['quantite']} titres, "
            f"acheté à {px_achat_eur}€/titre ({p.get('montant_investi',0):.0f}€ investis), "
            f"actuel {px_actuel_eur}€/titre ({p.get('valeur_actuelle',0):.0f}€), "
            f"perf {p.get('performance', 0):+.1f}% (€), {jours}j détenus, "
            f"score watchlist actuel: {p.get('score_entree', '?')}/100{etat_str}\n"
            f"    → Thèse d'achat : {raison_achat[:200]}{delta_str}"
        )

    # Synthèse marché issue de la passe 1
    synthese_marche = (analyse or {}).get("synthese_marche", "")
    synthese_str    = f"\n## ANALYSE MARCHÉ (passe 1)\n{synthese_marche}\n" if synthese_marche else ""

    # Format watchlist top 10 avec signaux cross + régression + analyse passe 1
    # + dynamique du signal (pente MM21, spread, signal_dynamics_warning) — anti-statique
    opportunites_analyse = (analyse or {}).get("opportunites_analyse", {})
    top10_lines = []
    for s in watchlist.get("stocks", [])[:10]:
        bd = s.get("breakdown", {})
        regime = bd.get("cross_regime", "")
        cross_days = bd.get("cross_days_ago")
        z = bd.get("regression_z")
        vol_conf = bd.get("cross_volume_confirmed", False)
        slope = bd.get("cross_slope_mm21_pct")
        spread = bd.get("cross_spread_pct")
        dyn_warn = bd.get("signal_dynamics_warning", "")

        regime_icon = "🟢" if regime == "golden" else "🔴" if regime == "death" else "⚪"
        cross_str = f" | {regime_icon} {regime.upper()} {cross_days}j" if cross_days is not None and regime in ("golden","death") else ""
        vol_str   = " vol✓" if vol_conf else ""
        z_str     = f" | z={z:+.1f}σ" if z is not None else ""
        # Dynamique : spread + pente MM21 → permet à l'agent de lire le signal en mouvement
        dyn_str = f" | spread {spread:+.1f}% pente {slope:+.1f}%" if slope is not None and spread is not None else ""

        # Timing d'entrée — valorisation actuelle (val_pts) + zone Fibo annotée
        val_pts = bd.get("val_pts")
        dd52w   = bd.get("drawdown_52w_pct")
        fibo    = bd.get("fibo") or {}
        val_str = f" | val={val_pts}/5 (DD{dd52w:+.1f}%)" if val_pts is not None and dd52w is not None else ""
        fibo_str = f" [{fibo['closest_fibo']}]" if fibo.get("closest_fibo") else ""

        opp_a    = opportunites_analyse.get(s["ticker"], {})
        opp_str  = f" | signal {opp_a['signal_qualite']}, timing {opp_a['timing']}" if opp_a else ""
        # Warning de transition (death cross qui se résorbe, golden qui s'affaiblit, mean-reversion)
        warn_str = f"\n      ⚠ {dyn_warn}" if dyn_warn else ""
        top10_lines.append(
            f"  #{s['rank']} {s['ticker']} ({s['name']}) — score {s['score']}/100 — {s['sector']}"
            f"{cross_str}{vol_str}{z_str}{val_str}{fibo_str}{dyn_str}{opp_str} — {s.get('justification', '')[:100]}{warn_str}"
        )

    # Tickers watchlist complète
    tickers_watchlist = [s["ticker"] for s in watchlist.get("stocks", [])]

    # Historique des ordres — Claude doit voir ses décisions passées (ventes notamment)
    # pour éviter les flip-flops (vendre puis racheter sans nouvelle thèse) et apprendre
    # de ses erreurs. Les positions ouvertes sont déjà dans la section précédente avec
    # leur thèse d'achat — ici on liste les VENTES et les ACHATS clôturés.
    ordres_passes = portfolio.get("ordres", [])
    if ordres_passes:
        hist_lines = []
        for o in ordres_passes[:50]:
            t = o.get("type", "?")
            tk = o.get("ticker", "?")
            d = o.get("date", "?")
            if t == "VENTE":
                # Note : variable locale renommée pour éviter de shadower `perf` (la perf totale du portfolio)
                # déclarée plus haut dans la fonction. Bug historique : perf était écrasée par la dernière
                # itération de la boucle, et la f-string "Performance portefeuille = {perf}%" affichait alors
                # la perf de la dernière vente (souvent ~0% ou la valeur de stop-loss).
                ord_perf = o.get("perf", 0)
                jours = o.get("jours", 0)
                raison = (o.get("raison", "") or "")[:120]
                hist_lines.append(f"  [{d}] VENTE {tk} perf {ord_perf:+.1f}% après {jours}j — {raison}")
            elif t == "ACHAT":
                raison = (o.get("raison", "") or "")[:120]
                hist_lines.append(f"  [{d}] ACHAT {tk} — {raison}")
            elif t == "APPORT":
                hist_lines.append(f"  [{d}] APPORT capital {o.get('montant', 0):.0f}€")
        ordres_section = (
            "\n## HISTORIQUE DE TES DÉCISIONS (50 dernières, plus récent en premier)\n"
            "Cet historique inclut tes ventes et achats passés. Important :\n"
            "- Évite de racheter un titre que tu viens de vendre sauf si une thèse réellement nouvelle le justifie\n"
            "- Apprends de tes erreurs (ventes en perte, aller-retours, biais récurrents)\n"
            + "\n".join(hist_lines) + "\n"
        )
    else:
        ordres_section = ""

    # Section macro news — indexée pour permettre à Claude de fournir des résumés FR alignés
    # Inclut maintenant le SUMMARY de la dépêche (pas juste le headline) pour permettre une vraie analyse
    if macro_news:
        news_lines = "\n".join(
            f"  [{i}] [{n['date']}] **{n['headline']}** ({n['source']})\n      → {n.get('summary','')[:500]}"
            for i, n in enumerate(macro_news)
        )
        macro_news_section = f"\n## ACTUALITÉS MACRO RÉCENTES (titres + contenu réel de la dépêche)\nCes news ont été pré-filtrées pour leur pertinence macro (Fed, inflation, BCE, géopol, taux, etc.). Le contenu de la dépêche est fourni pour que tu puisses l'analyser, pas seulement la titrer.\n{news_lines}\n"
    else:
        macro_news_section = ""

    # ── Règles mécaniques actives ce run (R01 concentration / R03 liquidités)
    # Injecté pour que Claude SACHE quelles actions seront automatiquement bloquées
    # par le layer mécanique post-décision — évite de proposer des décisions vouées
    # à l'échec (cause des dissonances "analyse_macro parle d'achat PANW mais
    # le journal n'a aucun ordre" qu'on a vues sur les runs précédents).
    regles_section = ""
    if regles_auto:
        def _regle_icon(r):
            # strict blocage : 🚫 ; soft cap : ⚠️ ; le reste : 🚫
            if r.get("type") == "concentration_sectorielle" and r.get("regime") == "soft":
                return "⚠️"
            return "🚫"
        regles_lignes = "\n".join(
            f"  {_regle_icon(r)} [{r.get('type','?')}] {r.get('message','')}" for r in regles_auto
        )
        regles_section = (
            "\n## ⚠ RÈGLES MÉCANIQUES ACTIVES — INTÈGRE-LES DANS TES DÉCISIONS\n"
            "Ces règles s'appliquent AUTOMATIQUEMENT après ton output JSON.\n"
            "Deux régimes possibles :\n"
            "  🚫 BLOCAGE STRICT : la décision sera REJETÉE et n'apparaîtra PAS dans le journal.\n"
            "  ⚠️ SOFT CAP : la décision PASSE mais avec un sizing réduit automatiquement (proportionnel\n"
            "     au dépassement). Avec conviction='forte' le sizing est plancher à 50% du normal.\n"
            f"{regles_lignes}\n"
            "\n"
            "⏳ RAPPEL VENTES : R01 (Règles non négociables ci-dessous) bloque toute vente sur position\n"
            "détenue < 90 jours, SAUF si tu mets `conviction: \"forte\"` ET cites dans `raison` un\n"
            "signal fondamental majeur documenté (résultats, scandale, M&A) — pas juste \"perte\" ou\n"
            "\"Death Cross\". Ne propose pas de vente sur position récente sans ce niveau de justification.\n"
            "\n"
            "🌡 CONCENTRATION SECTORIELLE (R01 graduée depuis fix du 23/05) :\n"
            "  - < 30%   : pas de restriction, sizing normal\n"
            "  - 30-65%  : soft cap, sizing réduit proportionnellement (à 40%→×0.71, 50%→×0.43, 60%→×0.14)\n"
            "             → tu PEUX acheter un titre du cluster sursaturé si tu mets conviction='forte'\n"
            "               (plancher de sizing à 50% du normal) ET justifies l'opportunité exceptionnelle\n"
            "  - > 65%   : blocage strict (concentration excessive)\n"
            "\n"
            "📝 COHÉRENCE NEWSLETTER : si tu envisages réellement une action que les règles vont bloquer\n"
            "(p. ex. tu trouves PANW excellent mais R01 cluster Tech&IA est saturée), tu peux la\n"
            "mentionner naturellement dans `analyse_macro` comme une frustration assumée — c'est de la\n"
            "transparence éditoriale. Tournure type : 'PANW avait le meilleur setup du tableau cette\n"
            "semaine — Golden Cross Day-0, pente MM21 à +6.6% — mais la règle R01 plafonne mon cluster\n"
            "Tech&IA à 30% et nous sommes à 62%. Frustrant mais c'est la discipline.' Ne pas en\n"
            "soumettre l'action dans `decisions` (elle sera bloquée et créera une dissonance avec le\n"
            "journal). L'idée : le lecteur de la newsletter comprend ce que tu aurais voulu faire ET\n"
            "pourquoi tu ne l'as pas fait, sans qu'on ait besoin d'un bandeau d'alerte sur le site.\n"
        )

    # Injection du skill portfolio-analyst — single source of truth
    # Le skill local définit la persona analyste, les mantras, la pré-flight discipline.
    # Si modifié localement (~/.claude/skills/portfolio-analyst/SKILL.md), le prochain run
    # voit automatiquement les changements. Évite la duplication contenu skill ↔ code.
    skill_discipline = load_skill_discipline()
    skill_section = f"""## DISCIPLINE D'ANALYSE (skill portfolio-analyst — autorité méthodologique)
Les sections "Persona", "5 mantras", "Pré-flight avant tout verdict" et "Ce que tu NE FAIS PAS"
ci-dessous sont l'autorité méthodologique. Les sections sur les outils (Données disponibles,
WebSearch, etc.) ne s'appliquent pas à ton contexte d'agent — ignore-les. Les triggers
ne s'appliquent pas non plus, tu es invoqué automatiquement chaque semaine.

{skill_discipline}

---

""" if skill_discipline else ""

    prompt = f"""{skill_section}Tu es l'IA qui gère le portefeuille fictif Signal. Ton objectif : battre le MSCI World (en euros, via EUNL.DE) sur la durée. La performance et l'écart au benchmark sont publiés en transparence à chaque mise à jour hebdomadaire.

## RÈGLES NON NÉGOCIABLES
1. Aucune vente avant 90 jours de détention — sauf signal fondamental majeur documenté
2. Maximum 20% du capital sur un seul titre (renforcement bloqué au-delà)
3. Zéro ajustement en mode panique (CAC40 < -5% sur la semaine) — sauf stop-loss catastrophe
4. Chaque décision doit être expliquée avec les données qui la motivent
5. Les retours utilisateurs et les erreurs passées doivent influencer les décisions
6. Stop-loss automatique : -15% après 90 jours, ou -25% sans condition de durée
7. **Signal en transition** : si un titre watchlist a un `signal_dynamics_warning` non-vide (death cross qui se résorbe, golden cross qui s'affaiblit, rebond mean-reversion sur cross stale, affaiblissement post-rally), traiter le cross technique comme **ambigu** — ne pas vendre/acheter sur ce signal seul. Croiser avec fonda et delta_these.
8. **Cross-validation analystes / cours** : pour les titres en zone d'incertitude (score 30-65), si le consensus analystes est très favorable mais le cours en dégradation 6-12m, suspecter une dégradation des données screener (effet change, périmètre M&A, désync data) — ne pas conclure trop vite sur la base du score seul. Re-lire la justification.
9. **Heures de marché** : tes décisions sont enregistrées au moment du run, mais l'exécution réelle attend l'ouverture du marché du titre. Si tu décides un ACHAT NVDA (US) à 8h UTC un lundi, l'ordre attendra 14h30 UTC (+6h30) pour s'exécuter — le prix peut bouger entre temps. Tiens-en compte : ne pas paniquer sur des données pré-ouverture, et si tous les marchés concernés sont fermés (weekend, jour férié), privilégier l'attente de la prochaine ouverture sauf urgence (stop-loss catastrophe).
10. **Friction fiscale (PFU 30%)** : Signal est sur compte-titres ordinaire français. Chaque VENTE en plus-value paye 30% de PFU sur le gain. Conséquence : une vente "neutre" pour réinvestir ailleurs PERD 30% du gain réalisé. Avant de proposer une vente sur position en gain, vérifie que l'alternative a un avantage attendu net suffisant pour couvrir cette friction (règle empirique : ne pas vendre un +20% pour acheter un titre dont l'edge espéré est < 10%). Les positions en perte ne sont PAS pénalisées fiscalement et la perte devient même un crédit d'impôt utilisable 10 ans. Les plus-values LATENTES (positions non vendues) ne sont JAMAIS imposées — le buy & hold long terme est structurellement avantagé.
11. **VIX = indicateur contextuel non scoré** : le VIX est désormais affiché dans la section CONTEXTE DE MARCHÉ comme indicateur d'ambiance macro, MAIS il n'influence plus mécaniquement le scoring du screener (choix de neutralité — on n'applique aucune mécanique de régime de marché au scoring). Tu es libre de t'en servir comme contexte qualitatif dans `analyse_macro` ("VIX à 22 cette semaine, vigilance modérée — j'ai privilégié les positions qualité"), mais ne traite pas le VIX comme une règle d'enforcement. Les scores du screener sont ce qu'ils sont, indépendamment du VIX.

## DATE & MOMENT DU RUN
- Run actuel       : {contexte.get('jour_semaine','?')} {today} {contexte.get('heure_utc','?')} UTC ({contexte.get('semaine','?')})
- Dernière mise à jour : {derniere_maj_str}
- Marchés au moment du run : EU {contexte.get('marches',{}).get('EU','?')} | LSE {contexte.get('marches',{}).get('LSE','?')} | US {contexte.get('marches',{}).get('US','?')}

## ÉTAT ACTUEL DU PORTEFEUILLE
- Capital initial (création) : {CAPITAL_INITIAL:.0f}€
- Capital actuel (net)       : {capital:.0f}€
- **Performance NETTE (depuis création) = {perf:+.2f}%**  (= {capital - CAPITAL_INITIAL:+.0f}€ vs {CAPITAL_INITIAL:.0f}€ initial — après frais et impôts réalisés)
- Performance brute (sans coûts) : {perf_brute:+.2f}%  (différence = {perf_brute - perf:+.2f}pp = friction réelle)
- Benchmark MSCI World (YTD 2026) = {bench:+.2f}%
- **Écart au benchmark vs MSCI = {vs:+.2f} points de pourcentage** (= perf portefeuille − MSCI YTD ; observation, pas une revendication d'alpha)
- Liquidités disponibles      : {liquidites:.0f}€

## FRICTION RÉELLE (frais transaction + fiscalité française)
- Frais transaction cumulés depuis création : {frais_cum:.2f}€ ({config.TRANSACTION_COST_BPS} bps one-way × turnover)
- Impôts PFU cumulés versés au fisc        : {impots_cum:.2f}€ (30% sur plus-values réalisées sur compte-titres)
- Pertes reportables fiscalement (10 ans)  : {pertes_cum:.2f}€ → crédit d'impôt théorique = {pertes_cum * 0.30:.0f}€ utilisable sur futurs gains
- Signal est un COMPTE-TITRES ORDINAIRE français : 30% PFU sur chaque plus-value réalisée à la VENTE.
  Les plus-values LATENTES (positions non vendues) ne sont PAS imposées.
  → Conséquence directe : buy & hold long terme est structurellement favorisé. Une vente "neutre"
    (sortir d'une position correcte pour réinvestir ailleurs) perd 30% sur le gain → la position
    de remplacement doit avoir un avantage attendu suffisant pour compenser cette friction fiscale.

🔢 IMPORTANT — chiffres à recopier EXACTEMENT :
  · Performance portefeuille NETTE : "{perf:+.2f}%" (NE PAS dire +0.0%, NE PAS dire YTD pour le portefeuille — c'est la perf cumulée depuis la création, après coûts et impôts)
  · Performance brute (référence)  : "{perf_brute:+.2f}%"
  · Écart vs MSCI                  : "{vs:+.2f}pp"
  · Capital actuel                 : "{capital:.0f}€"
  · Frais + impôts payés à ce jour : "{frais_cum + impots_cum:.0f}€"
Si tu cites ces chiffres dans `analyse_macro` ou `message_utilisateurs`, recopie-les depuis cette section, ne les recalcule pas toi-même.

Positions ouvertes ({len(positions)}) :
{chr(10).join(pos_lines) if pos_lines else "  Aucune position"}

## CONTEXTE DE MARCHÉ CETTE SEMAINE
- CAC40 : {contexte.get('cac40', {}).get('perf_semaine', 0):+.1f}% sur la semaine, {contexte.get('cac40', {}).get('perf_ytd', 0):+.1f}% YTD
- MSCI World : {contexte.get('msci', {}).get('perf_semaine', 0):+.1f}% sur la semaine, {contexte.get('msci', {}).get('perf_ytd', 0):+.1f}% YTD
- VIX : {contexte.get('vix','?')} — {"régime calme (<20)" if contexte.get('vix', 18) < 20 else "vigilance (20-25)" if contexte.get('vix', 18) < 25 else "stress modéré (25-35)" if contexte.get('vix', 18) < 35 else "panique (>35)"}. Indicateur contextuel uniquement, n'influence PAS les scores du screener (dampener mécanique désactivé — choix de neutralité). Tu peux le citer dans ton analyse si pertinent (ex: justifier une prudence accrue en VIX>25), mais sans le traiter comme une règle d'enforcement.
- Mode panique : {"OUI — Règle 03 active, aucun ordre possible" if contexte.get('mode_panique') else "NON — ordres possibles"}
{regles_section}
{ordres_section}{macro_news_section}{synthese_str}## WATCHLIST CETTE SEMAINE (top 10 sur {len(tickers_watchlist)})
{chr(10).join(top10_lines)}
Tickers watchlist complète : {', '.join(tickers_watchlist)}

## TA MISSION
Décide des actions à prendre cette semaine en t'appuyant sur l'analyse ci-dessus.
Pour chaque décision, explique ton raisonnement en tenant compte :
- Des thèses d'achat originales et du delta identifié en passe 1
- Du contexte macro de la semaine
- Des règles non négociables
- Des erreurs passées (positions perdantes, biais identifiés)

🔍 **SURFACE TON RAISONNEMENT MÉTHODOLOGIQUE** (transparence pour les lecteurs du site) :
- Si un titre watchlist a un `signal_dynamics_warning` non-vide qui a influencé ta décision (achat, vente, ou conservation), **cite le warning** dans `raison` et explique comment tu l'as croisé avec d'autres signaux.
- Si tu appliques R7 (signal en transition) ou R8 (cross-validation analystes/cours), **mentionne-le explicitement** dans `raison` (ex : "R8 déclenchée : score 42 + 11 buy + cours -38% sur 1 an, suspect données screener — j'ai croisé avec dernier trimestriel publié").
- Si la pré-flight a révélé un drapeau notable (M&A récente, divergence screener/réalité organique, signal en transition), **mentionne-le dans `analyse_macro`** comme élément de contexte pour les lecteurs.
- **Timing d'entrée (val_pts) — TOUJOURS commenter quand significatif** :
  · Si tu décides d'ACHETER un titre avec `val=5/5` (pullback −3 à −10%, zone d'entrée idéale), **dis-le** dans `raison` (ex: "Setup d'entrée propre : pullback −7% sous le top 52w en zone Fibo 38.2%, conviction renforcée").
  · Si tu REFUSES un achat tentant à cause de `val=0/5` près du top 52w (DD ≥ −3%), **dis-le** (ex: "Score 84/100 mais val=0/5 — collé au top 52w, attendre consolidation à −5/−10%").
  · Si tu décides d'ACHETER malgré `val=1/5` ou `val=0/5` en chute libre, **justifie pourquoi tu passes outre** (mean-reversion thesis, fonda exceptionnels, etc.).
  · Si la zone Fibo est notable (`zone Fibo 38.2%` = retracement standard, `zone Fibo 61.8%` = Golden Zone, `rally annulé` = trend cassée), **cite-la** comme contexte chartiste.
- L'idée : que les utilisateurs du site puissent comprendre POURQUOI tu as décidé, pas juste QUE tu as décidé. La méthodologie doit être visible, pas implicite.

🕒 **ANCRE LE RAISONNEMENT DANS LE TEMPS** (un lecteur lit ton output 7 jours plus tard) :
- L'`analyse_macro` doit **inclure un repère temporel** quelque part dans les 2 premières phrases (ex : "cette semaine du X au Y", "ces 7 derniers jours", "depuis le dernier run mardi"). PAS d'ouverture bureaucratique du type "Sur la semaine écoulée du XXXX-XX-XX au XXXX-XX-XX..." — ça casse le ton newsletter. Préfère une accroche éditoriale qui glisse la date naturellement.
- Les pourcentages cités (perf positions, perf marché) doivent **toujours** être accompagnés de leur fenêtre : "JPM à -4% **depuis l'achat il y a 11 jours**" ou "MSCI +1.8% **sur la semaine**".
- Le `message_utilisateurs` est lu sur le site avec un `updated_at` visible, mais **pas tout le monde calcule** — donne le contexte temporel explicitement.
- Si le run actuel est le même jour qu'un précédent (delta_j=0), **mentionne-le** ("run de contrôle de [heure] UTC, peu de changement vs run de ce matin").
- Pour chaque décision dans `raison`, ancrer la durée : "détenu depuis 47 jours" plutôt que "récemment".

⚠️ RÈGLE ANTI-CONTRADICTION : Pour toute VENTE sur une position détenue < 90 jours,
tu DOIS dans le champ "raison" :
  1. Citer la thèse d'achat originale
  2. Expliquer précisément ce qui a CONCRÈTEMENT changé (pas les mêmes signaux relus différemment)
  3. Si le delta_these de la passe 1 indique "Rien de fondamental", la vente est interdite

Réponds UNIQUEMENT en JSON valide, sans texte avant ou après, selon ce format exact :

{{
  "decisions": [
    {{
      "action": "ACHAT" | "VENTE" | "CONSERVER",
      "ticker": "XXXX",
      "nom": "Nom de l'action",
      "raison": "Explication détaillée en 2-3 phrases",
      "conviction": "forte" | "modérée" | "faible",
      "score_watchlist": 0
    }}
  ],
  "analyse_macro": "TEXTE NEWSLETTER (200-350 mots, 4-6 paragraphes courts SÉPARÉS PAR UN DOUBLE SAUT DE LIGNE `\\n\\n` — c'est NON-NÉGOCIABLE, sinon le rendu HTML produit un mur de texte illisible). Chaque paragraphe = 2 à 4 phrases, une idée par paragraphe. C'est CE QUE LE LECTEUR LIT chaque semaine sur le site. Adresse-toi DIRECTEMENT à lui ('vous', pas 'on' ni 'l'investisseur'). Ton : analyste rigoureux mais avec un brin d'humour décalé pour contraster avec les chiffres sérieux — pense à un Howard Marks qui aurait lu Charlie Munger ET aurait un sens de la formule. Tu peux te permettre une métaphore, une vanne fine sur les marchés, un clin d'œil. Pas de sarcasme méchant, pas de blagues lourdes. Reste pro mais vivant. STRUCTURE en paragraphes distincts (chacun séparé par `\\n\\n`) : §1 accroche sur l'événement de la semaine (cite EXPLICITEMENT le contenu des news macro reçues plus haut — pas juste le titre, le chiffre : si CPI à 2.4%, dis 2.4%, pas 'inflation reste centrale') ; §2 ce que ça veut dire concrètement pour le portefeuille + chiffres clés (perf {perf:+.2f}%, écart au benchmark {vs:+.2f}pp recopiés depuis ÉTAT ACTUEL) ; §3 éléments méthodologiques qui ont guidé tes décisions (R7, val_pts, signal_dynamics_warning si pertinent — sinon zappe) ; §4 biais ou learning de la semaine (s'il y en a un saillant, sinon zappe) ; §5 mot pour la semaine à venir (ce que vous surveillerez). NE PAS commencer par 'Sur la semaine écoulée du X au Y' (trop bureaucratique — préfère une accroche éditoriale qui glisse la date naturellement) mais l'ancrage temporel reste obligatoire dans les 2 premières phrases. Évite les formulations creuses ('le marché reste un paramètre central', 'l'attention est portée à...') — sois précis et concret. RAPPEL CRITIQUE : DOUBLE SAUT DE LIGNE `\\n\\n` entre chaque paragraphe, sinon le site rend un bloc compact.",
  "biais_detectes": ["biais 1", "biais 2"],
  "conviction_globale": "haussier" | "neutre" | "baissier",
  "message_utilisateurs": "Message transparent aux utilisateurs sur les décisions de cette semaine",
  "news_resumes_fr": ["Résumé en français de la news [0] en 1 phrase claire et factuelle", "Résumé de [1]", "…", "un résumé pour CHAQUE news fournie plus haut (0 à 6 selon le run)"]
}}

Pour `news_resumes_fr` : un résumé français concis (1 phrase, 15-25 mots max, factuel, neutre) pour CHAQUE news listée plus haut, dans l'ordre des indices [0], [1], etc. Le nombre exact de résumés DOIT correspondre au nombre de news fournies (variable selon le run — typiquement 4 à 6, mais peut être 0). Si une news est trop technique ou marginale, garde-la mais résume sa pertinence pour les marchés. Si aucune news n'a été fournie, retourne un tableau vide [].

N'inclus que les décisions actionnables (achats et ventes). Les positions conservées sans changement n'ont pas besoin d'apparaître, sauf si tu veux commenter spécifiquement leur situation.
"""
    return prompt

# ── EXÉCUTION DES DÉCISIONS ──────────────────────────────────────────────────
def executer_decisions(decisions_claude, portfolio, watchlist, contexte, eur_usd=1.10, eur_gbp=0.86, regles_auto=None):
    """
    Prend les décisions de Claude et les exécute.
    Toutes les valeurs monétaires sont stockées en EUR (conversion USD→EUR via eur_usd).
    Les prix unitaires restent en devise native pour l'affichage.
    Les règles mécaniques (Niveau 2) sont appliquées ici — elles bloquent les achats
    même si Claude a décidé d'acheter, garantissant leur caractère non négociable.

    Retourne : (positions, liquidites, nouveaux_ordres, decisions_bloquees)
      - decisions_bloquees : liste des décisions que Claude a proposées mais que les
        règles mécaniques ont rejetées. Surfacé sur le site pour transparence
        (sinon le lecteur voit Claude parler d'achats/ventes inexistants dans le journal).
    """
    positions   = portfolio.get("positions", [])
    liquidites  = portfolio.get("liquidites", CAPITAL_INITIAL)
    ordres      = portfolio.get("ordres", [])
    capital     = portfolio.get("capital_actuel", CAPITAL_INITIAL)
    nouveaux_ordres = []
    decisions_bloquees = []  # transparence : Claude a tenté ces actions, les règles ont bloqué
    today = str(date.today())

    stock_map = {s["ticker"]: s for s in watchlist.get("stocks", [])}
    mode_panique = contexte.get("mode_panique", False)

    # ── Guard : marchés fermés (weekend) ───────────────────────────────────
    # Physiquement aucun ordre ne peut être exécuté samedi/dimanche.
    # Y compris les stop-loss R07/R08 qui se reporteront au prochain run ouvré.
    # Pour Phase 4+ : étendre avec calendrier jours fériés US (Thanksgiving,
    # July 4, MLK Day, etc.) — actuellement seulement weekend.
    weekday = datetime.utcnow().weekday()  # 0=lundi … 5=samedi 6=dimanche
    jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    if weekday >= 5:
        decisions = decisions_claude.get("decisions", [])
        for dec in decisions:
            action = dec.get("action", "").upper()
            if action in ("ACHAT", "VENTE"):
                decisions_bloquees.append({
                    "date":              today,
                    "action_tentee":     action,
                    "ticker":            dec.get("ticker", ""),
                    "nom":               dec.get("nom", dec.get("ticker", "")),
                    "raison_claude":     dec.get("raison", ""),
                    "conviction":        dec.get("conviction", "modérée"),
                    "bloque_par":        "marche_ferme_weekend",
                    "explication_blocage": f"Run du {today} ({jours_fr[weekday]}) — tous les marchés sont fermés (weekend). Aucun ordre n'est physiquement exécutable. La décision est reportée au prochain run ouvré (lundi 8h UTC).",
                })
        print(f"  🛑 Weekend ({jours_fr[weekday]}) — {sum(1 for d in decisions if d.get('action','').upper() in ('ACHAT','VENTE'))} décision(s) reportée(s) au prochain jour ouvré (aucun ordre exécutable hors marchés)")
        return positions, liquidites, [], decisions_bloquees

    # Mise à jour des prix actuels — valeur_actuelle et performance en EUR
    for pos in positions:
        maj_position(pos, eur_usd, eur_gbp)

    # ── Règle 07 / 08 : Stop-loss automatiques ──────────────────────────────
    # R07 standard      : perf ≤ -15% ET ≥ 90 jours ET hors mode panique
    # R08 catastrophe   : perf ≤ -25% sans condition de durée (s'applique même
    #                     en mode panique — protège contre l'effondrement rapide
    #                     dans les 89 premiers jours qui était le trou de R07)
    stop_loss_tickers = {}  # ticker -> ('std' | 'catastrophe', perf, jours)
    for pos in positions:
        date_achat = pos.get("date_achat", today)
        jours = (datetime.today() - datetime.strptime(date_achat, "%Y-%m-%d")).days
        perf_pos = pos.get("performance", 0)
        # R08 — catastrophe : prioritaire, ignore mode panique et durée
        if perf_pos <= STOP_LOSS_CATASTROPHE_PCT:
            stop_loss_tickers[pos["ticker"]] = ("catastrophe", perf_pos, jours)
            print(f"  🆘 STOP-LOSS CATASTROPHE {pos['ticker']} — {perf_pos:.1f}% depuis {jours}j → vente forcée (Règle 08, ignore durée et panique)")
        # R07 — standard
        elif not mode_panique and perf_pos <= STOP_LOSS_PCT and jours >= 90:
            stop_loss_tickers[pos["ticker"]] = ("std", perf_pos, jours)
            print(f"  🛑 STOP-LOSS {pos['ticker']} — {perf_pos:.1f}% depuis {jours}j → ordre de vente forcé (Règle 07)")

    decisions = decisions_claude.get("decisions", [])

    # Injecter les ventes stop-loss en tête (conviction forte pour bypasser Règle 01)
    # Les stop-loss catastrophe (R08) ignorent en plus le mode panique (cf. boucle ci-dessous).
    for ticker_sl, (sl_type, perf_sl, jours_sl) in stop_loss_tickers.items():
        pos_sl = next((p for p in positions if p["ticker"] == ticker_sl), None)
        if pos_sl and not any(d.get("ticker") == ticker_sl and d.get("action","").upper() == "VENTE" for d in decisions):
            if sl_type == "catastrophe":
                raison_sl = (f"Stop-loss CATASTROPHE Règle 08 — {perf_sl:.1f}% depuis l'achat ({jours_sl}j). "
                             f"Seuil −25% atteint, vente forcée sans condition de durée ni mode panique.")
            else:
                raison_sl = f"Stop-loss automatique Règle 07 — {perf_sl:.1f}% depuis {jours_sl}j. Seuil −15% atteint après 90+ jours."
            decisions.insert(0, {
                "action": "VENTE",
                "ticker": ticker_sl,
                "nom": pos_sl.get("nom", ticker_sl),
                "raison": raison_sl,
                "conviction": "forte",
                "_stop_loss_type": sl_type,  # marqueur pour bypass mode panique côté VENTE
            })

    for dec in decisions:
        action = dec.get("action", "").upper()
        ticker = dec.get("ticker", "")
        raison = dec.get("raison", "")
        nom    = dec.get("nom", ticker)

        # ── VENTE
        if action == "VENTE":
            # Stop-loss catastrophe (R08) bypasse le mode panique
            is_catastrophe = dec.get("_stop_loss_type") == "catastrophe"
            if mode_panique and not is_catastrophe:
                print(f"  ⚠️  VENTE {ticker} bloquée — mode panique (Règle 03)")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "VENTE", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "R03", "explication_blocage": "Mode panique actif (CAC40 < -5% semaine) — aucune vente non-catastrophe possible",
                })
                continue

            pos = next((p for p in positions if p["ticker"] == ticker), None)
            if not pos:
                print(f"  ⚠️  VENTE {ticker} — position introuvable")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "VENTE", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "position_introuvable", "explication_blocage": f"Aucune position {ticker} dans le portefeuille — Claude a proposé une vente sur un titre non détenu",
                })
                continue

            date_achat = pos.get("date_achat", today)
            jours = (datetime.today() - datetime.strptime(date_achat, "%Y-%m-%d")).days

            # Règle 01 : 90 jours minimum
            if jours < 90:
                conviction = dec.get("conviction", "modérée")
                if conviction != "forte":
                    print(f"  ⏳ VENTE {ticker} bloquée — {jours}j < 90j et conviction non forte (Règle 01)")
                    raison = f"[BLOQUÉ — Règle 01 : {jours}j détenus < 90j requis] " + raison
                    dec["raison"] = raison
                    decisions_bloquees.append({
                        "date": today, "action_tentee": "VENTE", "ticker": ticker, "nom": nom,
                        "raison_claude": dec.get("raison", "").replace("[BLOQUÉ — Règle 01 : ", "").split("] ", 1)[-1] if "[BLOQUÉ" in dec.get("raison", "") else dec.get("raison", ""),
                        "conviction": conviction,
                        "bloque_par": "R01", "explication_blocage": f"{jours}j détenus < 90j requis (R01) — la vente nécessite conviction='forte' avec un signal fondamental documenté pour bypasser",
                        "jours_detention": jours,
                    })
                    continue

            prix_vente = get_prix(ticker) or pos.get("prix_actuel", pos["prix_achat"])

            # Garde anti-aberration (même contrat que maj_position) : un prix ×3/÷3
            # vs le dernier connu est presque toujours une erreur de données (GBp non
            # converti, split) — on refuse la vente plutôt que de créditer un cash
            # fantôme irrécupérable.
            prev_connu = pos.get("prix_actuel")
            if prev_connu and prev_connu == prev_connu and prev_connu > 0 and prix_vente:
                ratio = prix_vente / prev_connu
                if ratio > 3 or ratio < 1 / 3:
                    print(f"  🚨 VENTE {ticker} bloquée — prix {prix_vente} aberrant vs {prev_connu} (×{ratio:.2f})")
                    decisions_bloquees.append({
                        "date": today, "action_tentee": "VENTE", "ticker": ticker, "nom": nom,
                        "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                        "bloque_par": "prix_aberrant",
                        "explication_blocage": f"Prix de vente {prix_vente} incohérent avec le dernier prix connu {prev_connu} (×{ratio:.2f}) — probable erreur de données (devise/split), vente refusée par sécurité",
                    })
                    continue

            currency   = pos.get("currency") or detect_currency(ticker, pos.get("market", ""))
            perf       = round((prix_vente - pos["prix_achat"]) / pos["prix_achat"] * 100, 2)
            brut_vente_eur    = to_eur(prix_vente * pos["quantite"], currency, eur_usd, eur_gbp)
            # Base fiscale (achat + frais d'achat). Fallback position legacy sans le
            # champ : reconstitution depuis prix_achat×quantité — l'ancien défaut de 0
            # taxait 100% du produit de vente comme plus-value.
            montant_achat_eur = pos.get("montant_investi") or to_eur(
                pos["prix_achat"] * pos["quantite"], currency, eur_usd, eur_gbp)

            # Application frais vente + PFU sur la plus-value en EUR
            r = config.apply_sell_cost_and_tax(brut_vente_eur, montant_achat_eur)
            cash_recupere      = r["cash_recupere_eur"]
            frais_vente_eur    = r["frais_vente_eur"]
            plus_value_eur     = r["plus_value_eur"]
            impot_pfu_eur      = r["impot_pfu_eur"]
            perte_reportable   = r["perte_reportable_eur"]

            liquidites = round(liquidites + cash_recupere, 2)
            positions  = [p for p in positions if p["ticker"] != ticker]

            ordre = {
                "date":              today,
                "type":              "VENTE",
                "ticker":            ticker,
                "nom":                nom,
                "qte":                pos["quantite"],
                "prix":               prix_vente,
                "currency":           currency,
                "montant":            cash_recupere,       # cash effectivement reçu (compatibilité dashboard)
                "montant_brut_eur":   brut_vente_eur,      # brut sans frais ni impôt
                "frais_vente_eur":    frais_vente_eur,
                "plus_value_eur":     plus_value_eur,      # ce sur quoi le PFU est calculé
                "impot_pfu_eur":      impot_pfu_eur,
                "perte_reportable_eur": perte_reportable,
                "perf":               perf,                # en % devise native (inchangé)
                "pnl_eur":            plus_value_eur,      # alias pour rétrocompat dashboard (plus-value nette de frais)
                "jours":              jours,
                "raison":             raison,
                "conviction":         dec.get("conviction", "modérée"),
                "source":             "Claude AI",
            }
            nouveaux_ordres.append(ordre)
            sym = "€" if currency == "EUR" else "$" if currency == "USD" else "£"
            tax_str = f", PFU {impot_pfu_eur:.0f}€" if impot_pfu_eur > 0 else ""
            print(f"  🔴 VENTE {ticker} — {pos['quantite']} titres à {prix_vente}{sym} = {brut_vente_eur:.0f}€ brut, plus-value {plus_value_eur:+.0f}€{tax_str}, cash récupéré {cash_recupere:.0f}€")

        # ── ACHAT
        elif action == "ACHAT":
            if mode_panique:
                print(f"  ⚠️  ACHAT {ticker} bloqué — mode panique (Règle 03)")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "R03", "explication_blocage": "Mode panique actif (CAC40 < -5% sur la semaine) — aucun achat possible",
                })
                continue

            # Garde anti-hallucination : la consigne « tickers watchlist uniquement »
            # n'existait que dans le prompt. En code : un ticker hors watchlist passait
            # avec sector="—" et échappait définitivement à la règle de concentration R1.
            if ticker not in stock_map:
                print(f"  ✗ ACHAT {ticker} bloqué — hors watchlist (ticker inconnu ou halluciné)")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "hors_watchlist",
                    "explication_blocage": f"{ticker} ne figure pas dans la watchlist de la semaine — seuls les titres screenés sont achetables",
                })
                continue

            # Déjà en portefeuille ?
            if any(p["ticker"] == ticker for p in positions):
                print(f"  ⚠️  ACHAT {ticker} — déjà en portefeuille, ignoré")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "deja_en_portefeuille", "explication_blocage": f"{ticker} déjà détenu — Claude a proposé un achat sur une position existante (renforcement ?)",
                })
                continue

            # ── Règles mécaniques (enforcement — indépendant du raisonnement Claude)
            conviction    = dec.get("conviction", "modérée")
            cluster_sizing_factor = 1.0  # facteur multiplicatif appliqué au sizing (soft cap R01)
            if regles_auto:
                bloque_motif = None  # capture le motif de blocage pour log + transparence
                # R3 — Liquidités < 5% (toujours blocage strict)
                if any(r["type"] == "liquidites_faibles" for r in regles_auto):
                    print(f"  🚫 ACHAT {ticker} bloqué — liquidités < 5% (R3)")
                    bloque_motif = ("R03", "Liquidités < 5% du capital — achats bloqués jusqu'à reconstitution de la marge de manœuvre")
                else:
                    # R1 — Concentration sectorielle GRADUÉE :
                    #   - regime=strict  → blocage total
                    #   - regime=soft    → sizing réduit, bypass partiel si conviction forte
                    stock_tmp = stock_map.get(ticker, {})
                    sect_tick = stock_tmp.get("sector", "")
                    cluster_tick = cluster_for(sect_tick) if sect_tick else ""
                    cluster_rule = next(
                        (r for r in regles_auto
                         if r["type"] == "concentration_sectorielle" and r.get("secteur") == cluster_tick),
                        None
                    )
                    if cluster_rule:
                        regime = cluster_rule.get("regime", "strict")
                        pct = cluster_rule.get("pct", "?")
                        if regime == "strict":
                            print(f"  🚫 ACHAT {ticker} bloqué — cluster {cluster_tick} à {pct}% > 65% (R1 strict)")
                            bloque_motif = ("R01", f"Cluster {cluster_tick} à {pct}% > 65% — concentration excessive, achat refusé (R1 blocage strict)")
                        else:
                            # Soft : appliquer le sizing_factor
                            base_factor = cluster_rule.get("sizing_factor", 0.5)
                            # Conviction forte bypasse partiellement : plancher à 0.5
                            cluster_sizing_factor = max(base_factor, 0.5) if conviction == "forte" else base_factor
                            print(f"  ⚠️  ACHAT {ticker} — R1 soft (cluster {cluster_tick} à {pct}%) : sizing × {cluster_sizing_factor:.2f}")
                if bloque_motif:
                    rule_id, expl = bloque_motif
                    decisions_bloquees.append({
                        "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                        "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                        "bloque_par": rule_id, "explication_blocage": expl,
                    })
                    continue

            # Plafond de positions (MAX_POSITIONS) : refuser un NOUVEL achat si le portefeuille
            # est plein (un renforcement d'une ligne déjà ouverte reste autorisé).
            tickers_ouverts = {p.get("ticker") for p in positions}
            if ticker not in tickers_ouverts and len(positions) >= MAX_POSITIONS:
                print(f"  🚫 ACHAT {ticker} — portefeuille plein ({len(positions)}/{MAX_POSITIONS} lignes)")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "max_positions", "explication_blocage": f"Plafond {MAX_POSITIONS} positions atteint ({len(positions)} ouvertes) — nouvel achat refusé",
                })
                continue

            # Allocation dynamique : slots calculés sur l'ensemble des achats décidés (order-independent)
            nb_open       = len(positions)
            nb_achats_total = sum(1 for d2 in decisions if d2.get("action","").upper() == "ACHAT")
            slots_restants  = max(1, MAX_POSITIONS - nb_open - nb_achats_total)
            equal_weight   = liquidites / slots_restants

            if conviction == "forte":
                poids_cible = 0.07
            elif conviction == "modérée":
                poids_cible = 0.05
            else:
                poids_cible = 0.03

            # Application du soft cap R01 (cluster_sizing_factor ≤ 1.0)
            poids_cible *= cluster_sizing_factor

            budget = min(capital * poids_cible, capital * POIDS_MAX, equal_weight, liquidites)
            if budget < 50:
                print(f"  💰 ACHAT {ticker} — liquidités insuffisantes ({liquidites:.0f}€)")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "budget_insuffisant", "explication_blocage": f"Budget calculé {budget:.0f}€ < seuil 50€ — liquidités {liquidites:.0f}€ trop faibles pour cet achat",
                })
                continue

            prix = get_prix(ticker)
            if not prix or prix <= 0:
                print(f"  ✗ ACHAT {ticker} — prix indisponible")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "prix_indisponible", "explication_blocage": f"yfinance n'a pas renvoyé de prix valide pour {ticker} — achat impossible à exécuter",
                })
                continue

            stock    = stock_map.get(ticker, {})
            currency = detect_currency(ticker, stock.get("market", ""))
            prix_eur = to_eur(prix, currency, eur_usd, eur_gbp)

            # Budget en EUR → quantité (en réservant marge pour les frais d'achat)
            # On dimensionne pour que (brut + frais) ≤ budget plutôt que brut ≤ budget,
            # sinon les frais font légèrement dépasser le budget alloué.
            budget_apres_frais_anticipes = budget / (1 + config.TRANSACTION_COST_BPS / 10000.0)
            quantite     = int(budget_apres_frais_anticipes / prix_eur)
            if quantite < 1:
                # L'ancien max(1, …) forçait ici l'achat d'un titre plus cher que le
                # budget ET que les liquidités → liquidités négatives dans le JSON.
                print(f"  💰 ACHAT {ticker} bloqué — prix unitaire {prix_eur:.2f}€ > budget {budget:.0f}€")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "prix_unitaire_trop_eleve",
                    "explication_blocage": f"Prix unitaire {prix_eur:.2f}€ supérieur au budget alloué {budget:.0f}€ — impossible d'acheter un seul titre sans dépasser l'allocation",
                })
                continue
            brut_eur     = round(prix_eur * quantite, 2)

            # Application des frais d'achat (one-way) — inclus dans la base fiscale
            # à la revente conformément à la règle française.
            montant_eur, frais_achat = config.apply_buy_cost(brut_eur)
            if montant_eur > liquidites:
                # Ceinture + bretelles : quel que soit le chemin de sizing, un ordre
                # ne doit jamais laisser les liquidités négatives.
                print(f"  💰 ACHAT {ticker} bloqué — coût total {montant_eur:.2f}€ > liquidités {liquidites:.2f}€")
                decisions_bloquees.append({
                    "date": today, "action_tentee": "ACHAT", "ticker": ticker, "nom": nom,
                    "raison_claude": raison, "conviction": dec.get("conviction", "modérée"),
                    "bloque_par": "liquidites_insuffisantes",
                    "explication_blocage": f"Coût total frais inclus {montant_eur:.2f}€ supérieur aux liquidités {liquidites:.2f}€",
                })
                continue
            liquidites = round(liquidites - montant_eur, 2)

            nouvelle_pos = {
                "ticker":          ticker,
                "nom":             nom,
                "market":          stock.get("market", "—"),
                "sector":          stock.get("sector", "—"),
                "currency":        currency,
                "date_achat":      today,
                "prix_achat":      prix,       # devise native (affichage)
                "prix_actuel":     prix,
                "quantite":        quantite,
                "montant_investi": montant_eur,  # en EUR, INCLUT les frais d'achat (= base fiscale)
                "frais_achat_eur": frais_achat,  # journalisation séparée
                "valeur_actuelle": brut_eur,     # valeur de marché (sans les frais payés)
                "performance":     0.0,
                "score_entree":    stock.get("score", dec.get("score_watchlist", 0)),
                "raison_achat":    raison,      # thèse d'achat originale — réinjectée si vente envisagée
            }
            positions.append(nouvelle_pos)

            sym = "€" if currency == "EUR" else "$" if currency == "USD" else "£"
            ordre = {
                "date":      today,
                "type":      "ACHAT",
                "ticker":    ticker,
                "nom":       nom,
                "qte":       quantite,
                "prix":      prix,
                "currency":  currency,
                "montant":   montant_eur,       # en EUR (= cash débité = brut + frais)
                "montant_brut_eur": brut_eur,   # brut sans les frais (pour transparence)
                "frais_achat_eur": frais_achat, # journalisation
                "raison":    raison,
                "conviction": conviction,
                "source":    "Claude AI",
                "score_watchlist": stock.get("score", 0),
                "breakdown": stock.get("breakdown", {}),
            }
            nouveaux_ordres.append(ordre)
            print(f"  🟢 ACHAT {ticker} — {quantite} titres à {prix}{sym} = {brut_eur:.0f}€ + {frais_achat:.2f}€ frais (conviction {conviction})")

    if decisions_bloquees:
        print(f"  ℹ️  {len(decisions_bloquees)} décision(s) Claude bloquée(s) par les règles mécaniques (cf. portfolio.json → decisions_bloquees)")

    return positions, liquidites, nouveaux_ordres, decisions_bloquees

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    if not client:
        print("❌ ANTHROPIC_API_KEY manquante — ajoutez-la dans les secrets GitHub")
        return

    today     = str(date.today())
    watchlist = load_json("watchlist.json", {})
    portfolio = load_portfolio_strict("portfolio.json")

    # Lire capital_initial depuis le JSON (pas hardcodé) — corrige le bug post-injection
    global CAPITAL_INITIAL
    CAPITAL_INITIAL = portfolio.get("capital_initial", CAPITAL_INITIAL_DEF)

    if not watchlist.get("stocks"):
        print("❌ watchlist.json vide ou manquant")
        return

    print(f"🧠 Appel à Claude API — architecture deux passes — {semaine()}")

    # ── Contexte de marché + taux de change + macro news
    contexte    = get_contexte_marche(
        last_known_vix=portfolio.get("last_known_vix"),
        prev_mode_panique=portfolio.get("mode_panique", False),
    )
    eur_usd     = get_eur_usd_rate()
    eur_gbp     = get_eur_gbp_rate()
    macro_news  = get_macro_news()
    print(f"   CAC40 semaine : {contexte.get('cac40', {}).get('perf_semaine', 0):+.1f}%")
    print(f"   Mode panique  : {contexte.get('mode_panique')}")
    print(f"   VIX           : {contexte.get('vix')} ({contexte.get('vix_source')}) [contextuel, hors scoring]")
    print(f"   EUR/USD       : {eur_usd} · EUR/GBP : {eur_gbp}")
    print(f"   Macro news    : {len(macro_news)} article(s) macro sélectionné(s)")

    # ── Mise à jour des prix avant de soumettre à Claude (valeur_actuelle et performance en EUR)
    for pos in portfolio.get("positions", []):
        maj_position(pos, eur_usd, eur_gbp)

    val_pos = sum(p.get("valeur_actuelle", 0) for p in portfolio.get("positions", []))
    portfolio["capital_actuel"] = round(val_pos + portfolio.get("liquidites", CAPITAL_INITIAL), 2)
    portfolio["performance"]    = round((portfolio["capital_actuel"] - CAPITAL_INITIAL) / CAPITAL_INITIAL * 100, 2)

    # ── Niveau 2 : règles mécaniques calculées avant d'appeler Claude
    regles_auto = calculer_regles_auto(portfolio)
    if regles_auto:
        print(f"   Règles auto actives : {len(regles_auto)}")
        for r in regles_auto:
            print(f"     🚫 {r['message']}")

    # ── Passe 1 : analyse neutre (Haiku — rapide et économique)
    analyse = {}
    print(f"   Passe 1 — analyse neutre (Haiku)…")
    try:
        prompt_analyse = construire_prompt_analyse(portfolio, watchlist, contexte, macro_news)
        resp_analyse = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4000,
            system="Tu es un analyste financier neutre. Réponds UNIQUEMENT en JSON valide, sans texte avant ou après, sans backticks.",
            messages=[{"role": "user", "content": prompt_analyse}]
        )
        raw_analyse = resp_analyse.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        analyse = json.loads(raw_analyse)
        nb_pos_analysees = len(analyse.get("positions_analyse", {}))
        print(f"   ✅ Passe 1 — {nb_pos_analysees} position(s) analysée(s)")
    except Exception as e:
        print(f"   ⚠️  Passe 1 échouée ({e}) — passe 2 sans analyse préalable")

    # ── Passe 2 : décisions (Sonnet — raisonnement complet avec contexte enrichi)
    print(f"   Passe 2 — décisions (Sonnet)…")
    prompt = construire_prompt(portfolio, watchlist, contexte, analyse, macro_news, regles_auto=regles_auto)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=5000,
            system="""Tu es l'IA de gestion du portefeuille fictif Signal.
Tu raisonnes sur des décisions d'investissement fictives à partir de données réelles.
Tu es analytique, honnête sur tes erreurs, et transparent sur ton raisonnement.
Tu as reçu une analyse neutre en passe 1 — tu dois t'en servir pour décider, sans rationaliser a posteriori.
Tu réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après.
Ne jamais inclure de balises markdown ou de backticks.""",
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        decisions_claude = json.loads(raw)
        print(f"   ✅ Passe 2 — {len(decisions_claude.get('decisions', []))} décision(s)")
        print(f"   Conviction globale : {decisions_claude.get('conviction_globale', '?')}")

    except json.JSONDecodeError as e:
        # Échec BRUYANT sans écrire : avant, on publiait "Erreur parsing" en
        # analyse_macro sur le site (masqué par continue-on-error). Le site garde
        # l'analyse de la semaine précédente, daily-prices garde les prix frais.
        print(f"❌ Erreur parsing JSON Claude passe 2 : {e}")
        print(f"   Réponse brute : {raw[:200]}")
        raise SystemExit("❌ Passe 2 inexploitable — abandon SANS écrire portfolio.json")
    except Exception as e:
        print(f"❌ Erreur appel Claude passe 2 : {e}")
        raise SystemExit("❌ API indisponible (quota ?) — abandon SANS écrire portfolio.json")

    # ── Exécution des décisions (avec enforcement mécanique Niveau 2)
    positions, liquidites, nouveaux_ordres, decisions_bloquees = executer_decisions(
        decisions_claude, portfolio, watchlist, contexte, eur_usd, eur_gbp, regles_auto=regles_auto
    )

    # ── Recalcul final — valeur_actuelle et performance en EUR
    for pos in positions:
        maj_position(pos, eur_usd, eur_gbp)

    val_positions  = sum(p.get("valeur_actuelle", 0) for p in positions)
    capital_actuel = round(val_positions + liquidites, 2)
    performance    = round((capital_actuel - CAPITAL_INITIAL) / CAPITAL_INITIAL * 100, 2)

    for pos in positions:
        pos["poids"] = round(pos["valeur_actuelle"] / capital_actuel * 100, 1) if capital_actuel > 0 else 0

    # Benchmarks — MSCI World comme référence primaire (portefeuille ~70% US, global)
    bench_cac  = contexte.get("cac40", {}).get("perf_ytd", portfolio.get("benchmark_cac40", 0))
    bench_msci = contexte.get("msci",  {}).get("perf_ytd", portfolio.get("benchmark_msci", 0))
    vs_bench   = round(performance - bench_msci, 2)

    tous_ordres = nouveaux_ordres + portfolio.get("ordres", [])

    # ── Compteurs cumulatifs frais + impôts (Phase 1) ───────────────────────
    # Récupérés depuis le portefeuille précédent (rétro-compat : 0 si absent)
    # puis incrémentés des nouveaux ordres de ce run.
    total_frais_payes      = portfolio.get("total_frais_payes", 0.0)
    total_impots_payes     = portfolio.get("total_impots_payes", 0.0)
    total_pertes_reportables = portfolio.get("total_pertes_reportables", 0.0)
    for o in nouveaux_ordres:
        total_frais_payes      += o.get("frais_achat_eur", 0) + o.get("frais_vente_eur", 0)
        total_impots_payes     += o.get("impot_pfu_eur", 0)
        total_pertes_reportables += o.get("perte_reportable_eur", 0)
    total_frais_payes      = round(total_frais_payes, 2)
    total_impots_payes     = round(total_impots_payes, 2)
    total_pertes_reportables = round(total_pertes_reportables, 2)

    # Performance brute (pédagogique) : ce qu'on aurait sans aucune friction
    performance_brute  = round((capital_actuel + total_frais_payes + total_impots_payes - CAPITAL_INITIAL) / CAPITAL_INITIAL * 100, 2)

    # ── Capital post-liquidation virtuelle (réponse honnête à "combien j'aurais en cash si je vendais tout aujourd'hui ?") ──
    # capital_actuel = liquidités + valeur marché des positions (mark-to-market).
    # Mais les positions ouvertes contiennent des plus-values latentes NON TAXÉES.
    # Si on liquidait tout aujourd'hui, on paierait :
    #   - frais de vente (15bps × 0.5) sur chaque position
    #   - PFU 30% sur chaque plus-value latente (les pertes latentes créent du crédit fiscal)
    # → capital_post_liquidation = liquidités + Σ(brut - frais_vente - PFU_latent)
    cash_post_liq               = float(liquidites)
    frais_si_liquidation        = 0.0
    pfu_latent_si_liquidation   = 0.0
    pertes_si_liquidation       = 0.0
    for pos in positions:
        brut = pos.get("valeur_actuelle", 0)
        # Même fallback de base fiscale que le chemin de vente (cohérence du PFU) :
        # reconstitution depuis prix_achat×quantité si le champ legacy manque.
        base = pos.get("montant_investi") or to_eur(
            pos["prix_achat"] * pos["quantite"],
            pos.get("currency") or detect_currency(pos["ticker"], pos.get("market", "")),
            eur_usd, eur_gbp)
        r = config.apply_sell_cost_and_tax(brut, base)
        cash_post_liq             += r["cash_recupere_eur"]
        frais_si_liquidation      += r["frais_vente_eur"]
        pfu_latent_si_liquidation += r["impot_pfu_eur"]
        pertes_si_liquidation     += r["perte_reportable_eur"]
    capital_post_liquidation   = round(cash_post_liq, 2)
    frais_si_liquidation       = round(frais_si_liquidation, 2)
    pfu_latent_si_liquidation  = round(pfu_latent_si_liquidation, 2)
    pertes_si_liquidation      = round(pertes_si_liquidation, 2)
    performance_post_liquidation = round((capital_post_liquidation - CAPITAL_INITIAL) / CAPITAL_INITIAL * 100, 2)

    # ── Historique de performance (upsert : toujours la valeur finale du jour) ──
    history = portfolio.get("performance_history", [])
    today_entry = {
        "date": today, "perf": performance, "capital": capital_actuel,
        "benchmark_cac40": bench_cac, "benchmark_msci": bench_msci
    }
    idx_today = next((i for i, h in enumerate(history) if h.get("date") == today), None)
    if idx_today is not None:
        # Préserve la note (injection, etc.) si elle existait
        if "note" in history[idx_today]:
            today_entry["note"] = history[idx_today]["note"]
        history[idx_today] = today_entry
    else:
        history.append(today_entry)
    history = history[-260:]  # ~1 an de jours ouvrés (le cap 52 datait de l'époque hebdo)
    max_dd = calc_max_drawdown(history)

    # ── Combine les news macro Finnhub avec les résumés FR de Claude
    news_resumes = decisions_claude.get("news_resumes_fr", []) or []
    macro_news_enriched = []
    for i, news in enumerate(macro_news or []):
        resume = news_resumes[i] if i < len(news_resumes) else ""
        macro_news_enriched.append({**news, "resume_fr": resume})

    output = {
        "updated_at":          today,
        "week":                semaine(),
        "capital_initial":     CAPITAL_INITIAL,
        "capital_actuel":      capital_actuel,           # net de frais + impôts (cash + valeurs)
        "performance":         performance,              # nette de frais + impôts (= performance "réelle")
        "performance_brute":   performance_brute,        # ce qu'on aurait sans frais ni impôts (pédagogique)
        "total_frais_payes":   total_frais_payes,        # cumulé depuis création
        "total_impots_payes":  total_impots_payes,       # cumulé depuis création (PFU)
        "total_pertes_reportables": total_pertes_reportables,  # pertes utilisables fiscalement sur 10 ans
        # Post-liquidation : cash réel si tout vendu maintenant (= réponse honnête au gain net)
        "capital_post_liquidation":     capital_post_liquidation,
        "performance_post_liquidation": performance_post_liquidation,
        "frais_si_liquidation":         frais_si_liquidation,
        "pfu_latent_si_liquidation":    pfu_latent_si_liquidation,
        "pertes_si_liquidation":        pertes_si_liquidation,
        # Phase 2 — Cache VIX pour fallback si fetch échoue au run suivant
        "last_known_vix":      contexte.get("vix"),
        "last_known_vix_source": contexte.get("vix_source"),
        "benchmark_cac40":     bench_cac,
        "benchmark_msci":      bench_msci,
        "vs_benchmark":        vs_bench,
        "mode_panique": bool(contexte.get("mode_panique", False)),
        "perf_cac_semaine": float(contexte.get("cac40", {}).get("perf_semaine", 0)),
        "positions":           sorted(positions, key=lambda x: -x.get("performance", 0)),
        "liquidites":          round(liquidites, 2),
        "pct_liquidites":      round(liquidites / capital_actuel * 100, 1) if capital_actuel > 0 else 0,
        "ordres":              tous_ordres[:50],
        "biais_detectes":      decisions_claude.get("biais_detectes", []),
        "regles_actives":      regles_auto,
        # Décisions tentées par Claude mais rejetées par les règles mécaniques.
        # Surfacé sur le site pour éviter la dissonance entre l'analyse_macro
        # (qui peut mentionner des décisions) et le journal des ordres (qui ne montre
        # que les actions exécutées). Reset à chaque run — pas d'accumulation.
        "decisions_bloquees":  decisions_bloquees,
        "nb_positions":        len(positions),
        "nb_positives":        len([p for p in positions if p.get("performance", 0) > 0]),
        "nb_negatives":        len([p for p in positions if p.get("performance", 0) < 0]),
        "nb_neutres":          len([p for p in positions if p.get("performance", 0) == 0.0]),
        # Actus macro de la semaine (titres EN + résumés FR par Claude)
        "macro_news": macro_news_enriched,
        # Analyse Claude — affiché dans le site
        "analyse_claude": {
            "analyse_macro":        decisions_claude.get("analyse_macro", ""),
            "conviction_globale":   decisions_claude.get("conviction_globale", "neutre"),
            "message_utilisateurs": decisions_claude.get("message_utilisateurs", ""),
            "nb_decisions":         len(decisions_claude.get("decisions", [])),
        },
        "performance_history": history,
        "max_drawdown":         max_dd,
    }

    save_json_atomic("portfolio.json", output)

    print(f"\n✅ portfolio.json généré par Claude")
    print(f"   Capital mark-to-market : {capital_actuel:.0f}€  (net : {performance:+.1f}% · brut : {performance_brute:+.1f}%)")
    print(f"   Capital post-liquidation : {capital_post_liquidation:.0f}€  ({performance_post_liquidation:+.1f}% net après cession totale)")
    print(f"   PFU latent à payer si liquidation : {pfu_latent_si_liquidation:.0f}€  ·  Frais vente : {frais_si_liquidation:.0f}€")
    print(f"   vs MSCI   : {vs_bench:+.1f}pp")
    print(f"   Frais cumulés : {total_frais_payes:.0f}€  ·  Impôts cumulés : {total_impots_payes:.0f}€  ·  Pertes reportables : {total_pertes_reportables:.0f}€")
    print(f"   Ordres : {len(nouveaux_ordres)} ({sum(1 for o in nouveaux_ordres if o['type']=='ACHAT')} achats, {sum(1 for o in nouveaux_ordres if o['type']=='VENTE')} ventes)")
    if decisions_bloquees:
        print(f"   Bloquées : {len(decisions_bloquees)} décision(s) Claude rejetée(s) par les règles :")
        for db in decisions_bloquees:
            print(f"     ✗ {db['action_tentee']} {db['ticker']} — {db['bloque_par']} ({db['explication_blocage'][:80]})")
    print(f"   Analyse : {decisions_claude.get('conviction_globale','?')} — {decisions_claude.get('analyse_macro','')[:100]}…")

if __name__ == "__main__":
    main()
