"""
screener.py — Agent de sélection Signal
Génère watchlist.json avec les 30 meilleures actions par score (cf. WATCHLIST_SIZE).

Sources de données :
- Yahoo Finance (yfinance) : prix, indicateurs techniques, fondamentaux US
- Finnhub : validation croisée des fondamentaux (gratuit, 60 req/min)

Dépendances : pip install yfinance pandas ta numpy requests finnhub-python

─── NOTE v4 (100 pts, 08/2026) — le moteur vit dans note_v4.py ──────────────
Partition MECE par domaine de donnée, rampes CONTINUES partout, critère
incalculable RETIRÉ avec motif + renormalisation (jamais de zéro muet) :
Qualité      (35) = niveaux des comptes : marge médiane (9) + ROE (9)
                    + conversion cash (7) + bilan (5) + constance (5)
Croissance   (25) = dérivées des comptes : TCAM CA (7) + TCAM BPA (7)
                    + régularité (4) + attendu analystes (7, borné ≤ démontré)
Valorisation (25) = cours ÷ comptes : PER vs sa médiane d'époque (8)
                    + PEG maison (7) + rdt bénéfices (5) + rdt cash (5)
Momentum     (15) = cours ÷ cours : écart MM21/MM200 (6) + cloche z (6)
                    + cloche RSI (3)
Hors note    cross MM, val_pts (drawdown 52w), Fibonacci, VIX, consensus,
             confiance Finnhub : informationnels (l'IC du timing v3 était
             NÉGATIF, −0,33 — mesuré sur 24 archives hebdomadaires)

Annotation chartiste (informationnelle, hors scoring) :
  Retracement Fibonacci sur le dernier rally identifié — niveaux 23.6/38.2/50/61.8/78.6
  Permet de contextualiser le drawdown selon la taille du rally (cf opportunities.md)

Croisement MM21/MM200 — études de référence :
  Win rate moyen après Golden Cross : 66.7 % (S&P 500, 20 ans)
  Confirmation volume (+40 %) → 72 % de précision
  Signal le plus fort : 5-10 premiers jours de bourse après le cross
  RSI optimal à l'entrée : 40-60 (ni surachat ni survente)

Droite de régression log-linéaire :
  z-score = distance du cours à sa tendance long terme en écarts-types
  Zone saine : z ∈ [-0.5σ, +1.5σ] → position idéale pour entrer
  Fenêtre : 10 ans pour tech/IA (boom récent), 20 ans pour les autres secteurs
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import re
import sys
import time
import requests
from datetime import date, timedelta, datetime as _dt, timezone as _tz

import themes   # taxonomie des watchlists thématiques (source unique de vérité)
import edgar    # dépôts SEC : historique officiel des chiffres publiés (US)
import note_v4  # moteur de notation v4 : grille MECE, rampes continues, retraits motivés
from ta.momentum import RSIIndicator

# Paramètres centralisés (VIX dampener, etc.) — Phase 2
import config

# ── FINNHUB (validation croisée) ─────────────────────────────────────────────
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")

_NON_US_SUFFIXES = (".PA",".DE",".AS",".L",".CO",".BR",".MI",".MC",".AT",".IS",
                    ".HE",".ST",".OL",".OB",".SW",".VI",".LI",".T",".HK",".KS",".TO")

def _finnhub_appel_emis(ticker):
    """Un appel HTTP Finnhub est-il réellement émis pour ce ticker ?

    Même condition que le court-circuit de finnhub_fundamentals() ci-dessous —
    elle sert à ne temporiser QUE lorsqu'une requête a effectivement consommé
    du quota. Garder les deux alignées : si le court-circuit change, ici aussi.
    """
    return bool(FINNHUB_KEY) and not any(ticker.endswith(s) for s in _NON_US_SUFFIXES)


def finnhub_fundamentals(ticker):
    if not FINNHUB_KEY:
        return {}
    # Les tickers non-US n'existent pas sous leur symbole Yahoo chez Finnhub, et
    # retirer le suffixe renvoyait les métriques d'une AUTRE société US homonyme
    # (MC.PA → MC = Moelis & Co, AI.PA → AI = C3.ai…) : la « validation croisée »
    # comparait alors deux entreprises différentes et dégradait le score à tort.
    # → pas de validation Finnhub pour ces titres (yfinance seul fait foi).
    if any(ticker.endswith(sfx) for sfx in _NON_US_SUFFIXES):
        return {}
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/stock/metric",
            params={"symbol": ticker, "metric": "all"},
            headers={"X-Finnhub-Token": FINNHUB_KEY},
            timeout=5,
        )
        if r.status_code == 200:
            d = r.json().get("metric", {})
            # Seuls les champs réellement consommés par valider_fondamentaux :
            # pe_ttm, rev_growth_3y et roe étaient extraits depuis des mois
            # sans qu'aucune ligne du dépôt ne les lise (relecture 06/08).
            return {
                "net_margin":  d.get("netProfitMarginTTM"),
                "debt_equity": d.get("totalDebt/totalEquityAnnual"),
            }
        else:
            print(f"  ⚠️  Finnhub {ticker} — HTTP {r.status_code} ({'rate limit' if r.status_code==429 else 'token expiré?' if r.status_code==401 else 'erreur'})")
    except Exception as e:
        # Ne jamais logger l'exception brute : les erreurs requests embarquent l'URL
        # complète de la requête, et donc potentiellement des paramètres sensibles.
        print(f"  ⚠️  Finnhub {ticker} — exception : {type(e).__name__}")
    return {}

def valider_fondamentaux(yf_data, fh_data):
    """Contre-vérification Yahoo vs Finnhub → (confiance 0.7-1.0, alertes).

    DÉCISION (relecture du 06/08/2026) : Finnhub reste un VALIDATEUR, jamais
    une source de remplissage des trous Yahoo. Trois raisons, mesurées :
    ses champs (marge, ROE, dette) n'ont aucun trou observé sur 117 fiches
    alors que les vrais trous (FCF, marketCap, PEG) ne sont pas dans sa
    réponse ; ses unités diffèrent (ROE en %, dette en ratio — un remplissage
    naïf offrirait +12 et +7 pts) ; et remplir AVANT cette fonction ferait
    comparer Finnhub à Finnhub — plus aucune discordance détectable, le seul
    détecteur de mauvaise donnée du système s'éteindrait. Enfin Finnhub est
    réservé aux tickers US : remplir bonifierait les US pendant que l'Europe
    garde ses zéros — l'incident 3.5.0 inversé."""
    if not fh_data:
        return (1.0, [])
    confiance, alertes = 1.0, []
    try:
        yf_m_raw = yf_data.get("profitMargins")
        yf_m = yf_m_raw or 0
        fh_m = (fh_data.get("net_margin") or 0) / 100 if fh_data.get("net_margin") else 0
        if fh_m and yf_m_raw is None:
            # Un trou n'est pas une discordance : l'incertitude est réelle
            # (même décote), mais l'alerte publiée doit dire « absente »,
            # pas « discordante YF:0.0% » — ce zéro n'a jamais été mesuré.
            confiance -= 0.1
            alertes.append(f"Marge nette absente chez Yahoo (Finnhub : {fh_m:.1%})")
        elif fh_m and abs(yf_m - fh_m) > 0.15:
            confiance -= 0.1
            alertes.append(f"Marge nette discordante YF:{yf_m:.1%} vs FH:{fh_m:.1%}")
        yf_d = yf_data.get("debtToEquity") or 0
        fh_d = fh_data.get("debt_equity")  or 0
        if fh_d and yf_d and abs(yf_d - fh_d * 100) > 100:
            confiance -= 0.1
        rev = yf_data.get("revenueGrowth") or 0
        if rev > 3.0:
            confiance -= 0.15
            alertes.append(f"Croissance CA suspectement élevée : {rev:.0%}")
    except Exception:
        pass
    return (max(0.7, confiance), alertes)

# ── CROISEMENT MM21 / MM200 ───────────────────────────────────────────────────
def detect_cross(close_series, volume_series=None):
    """
    Détecte le dernier croisement MM21/MM200 (Golden Cross ou Death Cross).

    Golden Cross : MM21 croise MM200 à la hausse → signal haussier.
      Études : 66.7 % de win rate historique sur S&P 500 (350j de hausse moy.)
      Signal maximal dans les 5-10 premiers jours de bourse après le cross.
      Confirmation volume (+40 %) → précision portée à 72 %.

    Death Cross : MM21 croise MM200 à la baisse → signal baissier.
      Faux positifs fréquents en marché range (38 % win rate en phase choppy).

    Retourne un dict avec :
      regime            : 'golden' | 'death'
      cross_type        : type du dernier croisement observé
      days_since_cross  : jours DE BOURSE depuis ce croisement
      spread_pct        : (MM21-MM200)/MM200 en % → conviction de tendance
      slope_mm21_pct    : variation MM21 sur 5j en % → vélocité
      volume_confirmed  : True si volume > moyenne au moment du cross
    """
    try:
        mm21  = close_series.rolling(21).mean()
        mm200 = close_series.rolling(200).mean()

        # Aligner sur les points où les deux MAs sont disponibles
        valid = mm21.notna() & mm200.notna()
        mm21_v  = mm21[valid]
        mm200_v = mm200[valid]

        if len(mm21_v) < 2:
            return _cross_default()

        diff = mm21_v - mm200_v

        # Régime actuel
        regime = "golden" if float(diff.iloc[-1]) > 0 else "death"

        # Détection des croisements (changements de signe de diff)
        signs      = np.sign(diff.values)
        prev_signs = np.roll(signs, 1)
        prev_signs[0] = signs[0]
        cross_mask = (signs != prev_signs) & (prev_signs != 0)
        cross_idxs = np.where(cross_mask)[0]

        if len(cross_idxs) > 0:
            last_cross_pos  = cross_idxs[-1]
            last_cross_type = "golden" if signs[last_cross_pos] > 0 else "death"
            days_since_cross = len(diff) - 1 - last_cross_pos  # jours de bourse

            # Confirmation volume au moment du cross
            volume_confirmed = False
            if volume_series is not None:
                vol_valid = volume_series[valid]
                if last_cross_pos > 0 and len(vol_valid) > last_cross_pos:
                    vol_at_cross = float(vol_valid.iloc[last_cross_pos])
                    vol_avg      = float(vol_valid.iloc[max(0, last_cross_pos-50):last_cross_pos].mean())
                    volume_confirmed = (vol_at_cross > vol_avg * 1.40) if vol_avg > 0 else False
        else:
            last_cross_type  = regime
            days_since_cross = 999
            volume_confirmed = False

        # Spread actuel MM21 vs MM200 (% du cours) → mesure la conviction
        spread_pct = float((mm21_v.iloc[-1] - mm200_v.iloc[-1]) / mm200_v.iloc[-1] * 100)

        # Pente de MM21 sur 5 jours de bourse (%) → vélocité du signal
        slope_mm21_pct = 0.0
        if len(mm21_v) >= 6:
            slope_mm21_pct = float((mm21_v.iloc[-1] - mm21_v.iloc[-6]) / mm21_v.iloc[-6] * 100)

        return {
            "regime":           regime,
            "cross_type":       last_cross_type,
            "days_since_cross": int(days_since_cross),
            "spread_pct":       round(spread_pct, 2),
            "slope_mm21_pct":   round(slope_mm21_pct, 2),
            "volume_confirmed": volume_confirmed,
        }

    except Exception:
        return _cross_default()

def _cross_default():
    return {
        "regime": "unknown", "cross_type": None,
        "days_since_cross": 999, "spread_pct": 0.0,
        "slope_mm21_pct": 0.0, "volume_confirmed": False,
    }

# AUCUN APPELANT DANS LE DÉPÔT, ET C'EST NORMAL : NE PAS SUPPRIMER.
# `cross_score` est une SURFACE PUBLIQUE, documentée dans
# .claude/skills/portfolio-analyst/methodology.md, qui prescrit
# `from screener import score_ticker, detect_cross, cross_score,
# calcul_regression` pour que l'analyse manuelle note un titre exactement comme
# le screener. Tout détecteur de code mort la désignera donc, puisqu'elle n'est
# appelée nulle part ICI — un audit s'y est laissé prendre le 10/08/2026, sur un
# grep filtré par extension qui ne regardait pas les .md.
# `cross_label`, sa voisine, a été retirée le même jour : elle, personne ne
# l'appelait ni ne la documentait.
def cross_score(cross_info, rsi_val):
    """
    Score du croisement MM21/MM200 (0–20 pts).
    Intègre la fraîcheur du signal, le type de régime et la confirmation RSI.

    Golden Cross (signal haussier) :
      ≤ 10j de bourse : 20 pts — signal au plus fort (fenêtre optimale)
      11-30j          : 17 pts — signal frais, encore très actionnable
      31-60j          : 14 pts — confirmé, tendance qui se maintient
      61-180j         : 10 pts — régime haussier établi
      > 180j          :  7 pts — tendance durable, signal ancien
    Death Cross (signal baissier) :
      ≤ 30j de bourse :  0 pts — signal baissier actif
      31-90j          :  2 pts — baissier confirmé, éviter
      > 90j           :  4 pts — vieux régime, retournement possible

    Bonus : +2 pts si volume confirmé à la hausse au moment du cross.
    Bonus : +1 pt si RSI dans la zone idéale [40-65] au moment du scoring.
    """
    regime = cross_info.get("regime", "unknown")
    days   = cross_info.get("days_since_cross", 999)
    vol_ok = cross_info.get("volume_confirmed", False)

    if regime == "golden":
        if   days <= 10:  pts = 20
        elif days <= 30:  pts = 17
        elif days <= 60:  pts = 14
        elif days <= 180: pts = 10
        else:             pts = 7
        if vol_ok:        pts = min(pts + 2, 20)    # bonus volume
        if 40 <= rsi_val <= 65: pts = min(pts + 1, 20)  # bonus RSI zone idéale
    elif regime == "death":
        if   days <= 30:  pts = 0
        elif days <= 90:  pts = 2
        else:             pts = 4
    else:
        pts = 4  # inconnu → neutre prudent

    return pts

# ── RÉGRESSION LOG-LINÉAIRE ───────────────────────────────────────────────────
def calcul_regression(close_series, holdout_days=20):
    """
    Régression linéaire sur log(prix) — mesure l'écart du cours
    à sa tendance long terme en nombre d'écarts-types (z-score).

    Anti-bias in-sample : la régression est fittée sur l'historique SANS
    les `holdout_days` derniers jours (~1 mois de bourse). Le z-score
    du dernier point est ensuite mesuré contre cette droite "neutre".
    Sans ce holdout, inclure le point récent dans le fit tire mécaniquement
    la droite vers lui et sous-estime systématiquement |z|.

    z > +2  : surachat marqué (risque de retour vers la moyenne)
    +1..+2  : au-dessus de la tendance — normal pour actions en forte hausse
    -0.5..+1: zone neutre / saine — position idéale pour entrer
    < -1.5  : survente relative — rebond possible ou déclin structurel

    Retourne (z_score, pente_annuelle, prix_tendance, sigma) :
      prix_tendance = exp(droite au dernier point) — même unité que la série passée
      sigma         = écart-type des résidus in-sample (ddof=1)
    En échec : (0.0, 0.0, None, None) ; si résidus dégénérés (std < 1e-8) :
    (0.0, pente, None, None) — un z contre un σ quasi nul n'a pas de sens.
    """
    try:
        prices = close_series.values.astype(float)
        if len(prices) < 30:
            return 0.0, 0.0, None, None
        log_p = np.log(prices)

        # Holdout : on retire les N derniers jours du fit (mais pas si historique trop court)
        n_total = len(log_p)
        if n_total > holdout_days + 30:
            log_fit = log_p[:-holdout_days]
            x_fit   = np.arange(len(log_fit), dtype=float)
        else:
            log_fit = log_p
            x_fit   = np.arange(len(log_fit), dtype=float)

        slope, intercept = np.polyfit(x_fit, log_fit, 1)
        fitted_in_sample = intercept + slope * x_fit
        residuals_in     = log_fit - fitted_in_sample
        std_r            = float(np.std(residuals_in, ddof=1))
        if std_r < 1e-8:
            return 0.0, round(slope * 252 * 100, 1), None, None

        # Mesure du dernier point contre la droite extrapolée
        x_last           = float(n_total - 1)
        fitted_last      = intercept + slope * x_last
        residual_last    = float(log_p[-1] - fitted_last)
        z_score          = residual_last / std_r
        pente_annuelle   = slope * 252 * 100
        prix_tendance    = float(np.exp(fitted_last))   # valeur de la droite au dernier point (unité de la série)
        return round(z_score, 2), round(pente_annuelle, 1), prix_tendance, std_r
    except Exception:
        return 0.0, 0.0, None, None

def reg_signal_label(z):
    if   z >  2.0: return "surachat"
    elif z >  1.0: return "au-dessus"
    elif z > -0.5: return "neutre"
    elif z > -1.5: return "sous tendance"
    else:          return "survente"

def _decote_pct(prix, prix_tendance):
    """Décote vs droite de tendance : POSITIF = prix SOUS la tendance (décote),
    NÉGATIF = surcote. None si la tendance est indisponible ou aberrante (≤ 0)."""
    if prix_tendance is None or prix_tendance <= 0:
        return None
    return round((1 - prix / prix_tendance) * 100, 1)

# ── PAYLOAD GRAPHIQUE (charts/<TICKER>.json) ─────────────────────────────────
def _mois(ts):
    """Abscisse compacte des graphes : mois flottant (année*12 + mois 0-based
    + fraction du jour, base 31). 2 décales suffisent (~9h de résolution)."""
    return round(ts.year * 12 + (ts.month - 1) + (ts.day - 1) / 31, 2)

def _sample_series(s):
    """Échantillonne une série de prix pour le payload graphique :
    hebdo (W-FRI, last) sur les 730 derniers jours, mensuel (ME, last) au-delà —
    sur tout l'historique. Retourne [[t, valeur], ...] (t = _mois, valeurs 2 déc.).

    Deux pièges gérés explicitement :
    - le seau W-FRI en cours est étiqueté au vendredi FUTUR : le dernier point
      est ré-étiqueté à la date réelle de la dernière barre, avec sa vraie valeur ;
    - au raccord mensuel/hebdo, le dernier seau ME peut être étiqueté APRÈS le
      premier seau hebdo (étiquette fin de mois vs données arrêtées au cutoff)
      → on le supprime pour garder des abscisses strictement croissantes.
    """
    s = s.dropna()
    if s.empty:
        return []
    last_ts = s.index[-1]
    cutoff  = last_ts - pd.Timedelta(days=730)
    old     = s[s.index <= cutoff]
    recent  = s[s.index >  cutoff]
    mensuel = old.resample("ME").last().dropna()       if len(old)    else old
    hebdo   = recent.resample("W-FRI").last().dropna() if len(recent) else recent
    if len(mensuel) and len(hebdo):
        mensuel = mensuel[mensuel.index < hebdo.index[0]]
    combined = pd.concat([mensuel, hebdo])
    # Arrondi ADAPTATIF : round(v, 2) écrasait en 0.0 les cours ajustés
    # minuscules de l'historique lointain (AXA 1990 : 0,004 € après 35 ans
    # d'ajustements de dividendes) — et un zéro est invisible sur une échelle
    # log. Sous 1, on garde 4 décimales ; le filtre close>0 en amont a déjà
    # écarté les vrais artefacts.
    # 3 chiffres significatifs sous 1 : round(v, 4) écrasait encore en 0.0
    # les cours ajustés de 1990 tombés sous 0,00005 (AXA).
    _r = lambda v: round(float(v), 2) if v >= 1 else float(f"{float(v):.3g}")
    pts = [[_mois(ts), _r(v)] for ts, v in combined.items()]
    if pts:
        # Ré-étiquetage du dernier point à la date réelle de la dernière barre quotidienne
        pts[-1] = [_mois(last_ts), _r(s.iloc[-1])]
    return pts

# ── CHIFFRES PUBLIÉS (historique des états financiers) ──────────────────────
# Le score photographie un instant (marges TTM, un trimestre de croissance) ;
# la fiche doit montrer la TRAJECTOIRE publiée : CA, EBITDA et résultat net
# des derniers exercices et trimestres, comme sur une plateforme de courtage.
# Source : les états financiers yfinance (income_stmt), même robinet que le
# reste — ~4-5 exercices et ~5-6 trimestres, toutes places de cotation.
# ATTENTION devise : les états sont publiés dans la devise COMPTABLE
# (financialCurrency), pas celle de cotation — TSM cote en USD et publie en
# TWD. On stocke la devise comptable et le front l'affiche.

def extraire_fondamentaux(df_annuel, df_trim, devise, max_an=5, max_tr=6):
    """Bloc « chiffres publiés » pour charts/<TICKER>.json, en MILLIONS.

    Pure (DataFrames yfinance en entrée, dict JSON-sûr en sortie), fail-soft :
    lignes absentes tolérées (les banques n'ont pas d'EBITDA), None si rien.
    Clés courtes ("ca", "eb", "rn") : le payload part sur le réseau.
    """
    def serie(df, noms):
        if df is None or getattr(df, "empty", True):
            return {}
        for nom in noms:
            if nom in df.index:
                s = df.loc[nom]
                if getattr(s, "ndim", 1) > 1:      # libellé dupliqué → 1re ligne
                    s = s.iloc[0]
                return {c: float(v) for c, v in s.dropna().items() if v == v}
        return {}

    def bloc(df, n, avec_eps=False):
        ca = serie(df, ["Total Revenue", "Operating Revenue"])
        eb = serie(df, ["EBITDA", "Normalized EBITDA"])
        rn = serie(df, ["Net Income", "Net Income Common Stockholders"])
        # BPA dilué publié (annuel seulement) : le PER par exercice s'en déduit.
        # Par action, pas en millions — arrondi 4 décimales (actions à BPA
        # centimes : Sony pré-split, valeurs coréennes).
        eps = serie(df, ["Diluted EPS", "Basic EPS"]) if avec_eps else {}
        lignes = []
        # L'axe du temps est celui du CA ou du RN (l'EBITDA seul ne fait pas
        # une publication) ; ordre chronologique, bornés aux n plus récents.
        for d in sorted(set(ca) | set(rn))[-n:]:
            e = {"fin": str(d)[:10]}
            if d in ca: e["ca"] = int(round(ca[d] / 1e6))
            if d in eb: e["eb"] = int(round(eb[d] / 1e6))
            if d in rn: e["rn"] = int(round(rn[d] / 1e6))
            if d in eps and eps[d]: e["eps"] = round(eps[d], 4)
            if len(e) > 1:
                lignes.append(e)
        return lignes

    an, tr = bloc(df_annuel, max_an, avec_eps=True), bloc(df_trim, max_tr)
    if not an and not tr:
        return None
    return {"devise": devise or "?", "an": an, "tr": tr}


def etats_complements(df_cf, df_bs, df_is=None):
    """Flux de trésorerie disponible, dette totale et capitaux propres, lus
    DIRECTEMENT dans les états financiers.

    POURQUOI CETTE FONCTION EXISTE. Le dictionnaire de résumé de Yahoo
    (`info`) ne renseigne ni `freeCashflow`, ni `debtToEquity`, ni
    `returnOnEquity` pour une bonne part des titres non américains — Disco
    Corporation à Tokyo et SK Hynix à Séoul n'ont aucun des trois. Sur le run
    du 06/08, 26 retraits de critères (21 % du total) venaient de là, alors
    que la matière première était DÉJÀ en mémoire : on télécharge le tableau
    de flux et le bilan pour la section « Chiffres publiés ». On se contentait
    du résumé pré-mâché en ayant les états complets sous la main.

    Le procédé vaut pour TOUTES les places et toutes les devises — il ne
    réintroduit donc pas l'asymétrie américaine d'EDGAR — et ne coûte aucun
    appel réseau supplémentaire.

    Pure (DataFrames en entrée, dict en sortie), fail-soft : une ligne absente
    est omise, jamais devinée. Valeurs en unités BRUTES de la devise
    comptable ; les ratios sont l'affaire de l'appelant.
    """
    def dernier(df, noms):
        """Valeur la plus récente parmi les libellés donnés, par ordre de
        préférence. Les libellés varient d'un émetteur à l'autre."""
        if df is None or getattr(df, "empty", True):
            return None
        for nom in noms:
            if nom in getattr(df, "index", ()):
                s = df.loc[nom]
                if getattr(s, "ndim", 1) > 1:
                    s = s.iloc[0]
                vals = {c: float(v) for c, v in s.dropna().items() if v == v}
                if vals:
                    return vals[max(vals)]
        return None

    out = {}

    # Flux disponible : la ligne toute faite si l'émetteur la publie, sinon la
    # définition (exploitation − investissements industriels). Le capex est
    # déposé en négatif par convention comptable, d'où la valeur absolue.
    fcf = dernier(df_cf, ["Free Cash Flow"])
    if fcf is None:
        op = dernier(df_cf, ["Operating Cash Flow",
                             "Cash Flow From Continuing Operating Activities",
                             "Total Cash From Operating Activities"])
        capex = dernier(df_cf, ["Capital Expenditure", "Capital Expenditures",
                                "Purchase Of PPE"])
        if op is not None and capex is not None:
            fcf = op - abs(capex)
    if fcf is not None:
        out["fcf"] = fcf

    cp = dernier(df_bs, ["Stockholders Equity", "Total Stockholder Equity",
                         "Common Stock Equity"])
    # `cp > 0` explicitement : en Python un négatif est « vrai », et des
    # capitaux propres négatifs (report à nouveau déficitaire, rachats massifs)
    # donneraient un ROE et un levier inversés — donc trompeurs.
    if cp is not None and cp > 0:
        out["capitaux_propres"] = cp

    # Actifs totaux — nécessaires aux critères de substitution des métiers de
    # bilan (rendement des actifs, levier actifs/fonds propres).
    actifs = dernier(df_bs, ["Total Assets"])
    if actifs is not None and actifs > 0:
        out["actifs"] = actifs

    dette = dernier(df_bs, ["Total Debt"])
    if dette is None:
        lt = dernier(df_bs, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
        ct = dernier(df_bs, ["Current Debt", "Current Debt And Capital Lease Obligation",
                             "Short Long Term Debt"])
        if lt is not None or ct is not None:
            dette = (lt or 0) + (ct or 0)
    if dette is not None:
        out["dette"] = dette

    # Chiffre d'affaires et résultat net du MÊME exercice que le flux
    # disponible ci-dessus. Ils ne servent qu'à des RATIOS : la conversion du
    # bénéfice en cash et la marge de flux disponible. C'est toute la raison
    # de les lire ici plutôt que de reprendre les champs glissants du résumé
    # Yahoo — un quotient n'a de sens qu'entre deux grandeurs de la même
    # période, dans la même devise, issues du même document.
    ca = dernier(df_is, ["Total Revenue", "Operating Revenue", "Revenues"])
    if ca is not None and ca > 0:
        out["ca"] = ca
    rn = dernier(df_is, ["Net Income", "Net Income Common Stockholders",
                         "Net Income Continuous Operations",
                         "Net Income From Continuing Operation Net Minority Interest"])
    if rn is not None:
        out["rn"] = rn

    return out


# ── APPORT VÉRIFIÉ (étage 2 de l'historique profond) ─────────────────────────
# Les non-déposants SEC (Samsung, les domestiques japonaises, Hermès, Adyen…)
# n'ont aucune source officielle interrogeable par API : leurs exercices
# anciens entrent par ce fichier, constitué à la main depuis les rapports
# annuels publiés par les sociétés elles-mêmes, avec la source par bloc.
# Une fois absorbées par l'accumulateur inter-run, ces données vivent seules —
# le fichier n'est relu que pour les exercices encore absents (extend-only,
# mêmes gardes d'échelle et de dédoublonnage que l'apport EDGAR).
APPORT_PATH = "data/apport_historique.json"
_APPORT = None


def charger_apport(ticker, devise_comptable):
    """Bloc {an, tr} de l'apport pour un ticker, None si rien d'applicable.

    Refuse silencieusement un bloc dont la devise ne correspond pas à la
    devise comptable Yahoo du moment : si l'émetteur a changé de monnaie de
    présentation (ou si l'apport a été saisi dans la mauvaise), mélanger
    fabriquerait des variations absurdes. Chaque entrée est estampillée
    src:"apport" — la provenance voyage avec la donnée, comme pour EDGAR.
    """
    global _APPORT
    if _APPORT is None:
        try:
            with open(APPORT_PATH, encoding="utf-8") as f:
                _APPORT = {k: v for k, v in json.load(f).items()
                           if not k.startswith("_")}
        except FileNotFoundError:
            _APPORT = {}
        except Exception as e:
            print(f"  ⚠️  apport illisible ({type(e).__name__}) — ignoré pour ce run")
            _APPORT = {}
    bloc = _APPORT.get(ticker)
    if not bloc or not bloc.get("an"):
        return None
    if (bloc.get("devise") or "").upper() != (devise_comptable or "").upper():
        print(f"  ⚠️  apport {ticker} écarté : devise {bloc.get('devise')} ≠ comptable {devise_comptable}")
        return None
    return {"an": [dict(e, src="apport") for e in bloc["an"] if e.get("fin")],
            "tr": []}


def chainer_comptes(an, meme_devise, prix, net_margin_raw, trailing_pe_raw):
    """Troisième maillon de la chaîne : les COMPTES PUBLIÉS.

    Quand le résumé Yahoo et les états financiers sont tous deux muets, il
    reste l'historique déjà constitué pour la section « Chiffres publiés » —
    étendu par EDGAR pour les sociétés américaines. Deux grandeurs s'en
    déduisent sans aucune hypothèse :

      · la marge nette = résultat net ÷ chiffre d'affaires du dernier
        exercice publié (les deux sont dans la même devise comptable) ;
      · le PER courant = cours ÷ bénéfice par action du dernier exercice,
        à condition que la devise comptable soit celle de la cotation —
        sinon on diviserait des TWD par des USD (le piège des ADR).

    C'est un repli ANNUEL là où Yahoo publie du douze-mois-glissant : moins
    frais, mais exact et vérifiable. Rendu en fractions/multiples bruts, à
    l'image de ce que le résumé Yahoo aurait donné.

    Retourne (net_margin, trailing_pe, provenance[]) — les valeurs déjà
    connues sont rendues inchangées et n'apparaissent pas dans la provenance.
    """
    src = []
    nm, tpe = net_margin_raw, trailing_pe_raw
    dernier = next((e for e in reversed(an or []) if e.get("ca")), None)
    if nm is None and dernier and dernier.get("rn") is not None and dernier.get("ca"):
        nm = dernier["rn"] / dernier["ca"]
        src.append("marge")
    if tpe is None and meme_devise and prix:
        d_eps = next((e for e in reversed(an or [])
                      if e.get("eps") and e["eps"] > 0), None)
        if d_eps:
            tpe = prix / d_eps["eps"]
            src.append("per")
    return nm, tpe, src


def chainer_finnhub(fh_data, net_margin_raw, debt_eq_raw):
    """Quatrième et DERNIER maillon : Finnhub, titres américains seulement.

    Placé en bout de chaîne à dessein, pour deux raisons qui étaient les
    objections historiques à son usage comme source de remplissage.

    L'ASYMÉTRIE : Finnhub ne connaît pas les symboles non américains (et
    renvoie une société homonyme si l'on retire le suffixe — MC.PA donnerait
    Moelis). Le placer en dernier limite l'écart qu'il creuse : il ne sert
    que lorsque Yahoo ET les états financiers ET les comptes publiés ont tous
    échoué, ce qui est rare.

    LES UNITÉS : Finnhub rend la marge et le ROE en POURCENTS là où Yahoo
    rend des fractions, et le rapport dette/capitaux propres en RATIO là où
    Yahoo rend un pourcentage. Un remplissage naïf offrirait une vingtaine de
    points indus — la conversion est donc explicite et testée.

    L'ordre d'appel importe : la validation croisée Yahoo/Finnhub doit tourner
    AVANT ce remplissage, sinon elle comparerait Finnhub à lui-même et le seul
    détecteur de donnée douteuse du système s'éteindrait.
    """
    src = []
    nm, de = net_margin_raw, debt_eq_raw
    if not fh_data:
        return nm, de, src
    if nm is None and fh_data.get("net_margin") is not None:
        nm = fh_data["net_margin"] / 100          # % → fraction
        src.append("marge")
    if de is None and fh_data.get("debt_equity") is not None:
        de = fh_data["debt_equity"] * 100         # ratio → %
        src.append("dette")
    return nm, de, src


ECART_BASE_ACTIONS = 0.10   # 10 % — au-delà, la base d'actions a bougé, on n'interpole pas


def completer_eps(an, ecart_max=ECART_BASE_ACTIONS):
    """Reconstitue le bénéfice PAR ACTION des exercices qui n'ont que le
    bénéfice total, quand — et seulement quand — la base d'actions est stable
    autour du trou. Mutation en place, rend le nombre d'exercices complétés.

    LE TROU, ET SA TAILLE. Quarante-trois exercices sur seize fiches portent un
    résultat net publié sans BPA : la source donne l'un et pas l'autre. Chacun
    est un point manquant dans la courbe des multiples, au milieu d'une série
    par ailleurs continue — Alphabet 2015, Arista 2021, Dell 2022.

    CE QU'ON PEUT COMBLER, ET CE QU'ON NE PEUT PAS. Le nombre d'actions se
    déduit des exercices voisins qui portent les DEUX grandeurs : résultat net
    divisé par BPA. Si les voisins d'avant et d'après s'accordent à 10 % près,
    la base n'a pas bougé sur l'intervalle et le BPA manquant est une division,
    pas une hypothèse. S'ils divergent, la société a émis, racheté ou divisé ses
    actions entre-temps, et toute valeur interpolée serait inventée.

    LA MESURE, faite avant d'écrire cette fonction : cinq exercices sur
    quarante-trois passent ce test. Trente-sept sont au BORD de la série — le
    plus ancien exercice connu, sans voisin antérieur — et un seul est encadré
    par une base instable. Autrement dit la règle refuse 88 % des cas, et c'est
    le résultat attendu : le bord d'une série est précisément l'endroit où
    l'extrapolation ne repose sur rien. Symbotic affichait selon les exercices
    608, 65 puis 162 millions d'actions impliquées (le BPA ne porte qu'une
    classe, le résultat net la société entière) : y interpoler quoi que ce soit
    aurait produit un multiple faux d'un facteur dix.

    CE QUI EST COMBLÉ SE DIT : l'exercice porte `eps_derive`, et la fiche
    l'affiche — un multiple reconstitué n'a pas le même grain qu'un multiple lu.
    Pure et testable hors ligne."""
    faits = 0
    for i, e in enumerate(an):
        # UN RÉSULTAT NET À ZÉRO EST UNE ABSENCE, PAS UNE MESURE. Le premier jet
        # ne testait que `rn is None`, et le run du 09/08 l'a puni tout de
        # suite : Arista 2021 et Viasat 2020 portent `rn: 0` — la source n'a
        # rien rendu pour cet exercice — et la division a publié un bénéfice par
        # action de 0,0, c'est-à-dire l'affirmation qu'Arista n'a rien gagné en
        # 2021, quand elle a gagné 840 M$. Le multiple, lui, restait absent : le
        # faux ne se voyait que dans le chiffre. C'est la même leçon que le
        # consensus à zéro de Yahoo, tirée deux jours plus tôt sur les
        # projections — un zéro rendu par une source muette n'est pas un zéro.
        if e.get("eps") or not e.get("rn"):
            continue
        av = next((x for x in reversed(an[:i]) if x.get("rn") and x.get("eps")), None)
        ap = next((x for x in an[i + 1:] if x.get("rn") and x.get("eps")), None)
        if not av or not ap:
            continue                      # bord de série : rien pour encadrer
        a, b = av["rn"] / av["eps"], ap["rn"] / ap["eps"]
        if a <= 0 or b <= 0 or abs(a / b - 1) > ecart_max:
            continue                      # la base d'actions a bougé
        actions = (a + b) / 2
        e["eps"] = round(e["rn"] / actions, 4)
        e["eps_derive"] = True
        faits += 1
    return faits


def per_historique(an, prix_a_la_date, meme_devise, actions_actuelles=None,
                   taux=None, rapport=None):
    """Ajoute le PER de chaque exercice : cours de clôture de l'exercice / BPA
    dilué publié. UNIQUEMENT quand la devise comptable est celle de cotation :
    un ADR comme TSM cote en USD mais publie son BPA en TWD (et représente
    plusieurs actions ordinaires) — le quotient serait un non-sens, on omet.
    Mutation en place des entrées ; BPA négatif ou nul → pas de PER (une perte
    n'a pas de multiple).

    `prix_a_la_date` doit rendre le cours AJUSTÉ DES SPLITS SEULEMENT — celui
    que le marché cotait vraiment. Un cours ajusté des dividendes déflate le
    passé et sous-estime tous les multiples anciens.

    LA BASE D'ACTIONS, et comment on la VÉRIFIE au lieu de la supposer.

    Un cours ajusté des splits vit dans la base d'actions d'aujourd'hui ; le
    BPA doit y vivre aussi, sinon le multiple est faux du facteur du split.

    Le premier jet de cette garde SUPPOSAIT que les BPA de la fenêtre Yahoo
    étaient « tels que publiés », donc dans la base de leur époque, et retirait
    tout exercice antérieur à un split. C'était faux, et c'est le propriétaire
    qui l'a vu : « le PER de Booking est beugué ». Les faits, relevés sur les
    fiches publiées — le nombre d'actions impliqué (résultat net ÷ BPA) est
    CONTINU au passage d'EDGAR à Yahoo : Booking 1 034 M puis 1 001 M, NVIDIA
    25 330 M puis 25 103 M, Broadcom 4 291 M puis 4 333 M. Yahoo retraite donc
    ses BPA comme EDGAR. La garde supprimait des multiples parfaitement bons.

    Elle est remplacée par une MESURE, la même qu'edgar._normalise_eps : le
    nombre d'actions impliqué doit être du même ordre que le nombre d'actions
    actuel (facteur 3 en log). Au-delà, la base est incompatible quelle qu'en
    soit la raison, et le multiple est retiré. Sans résultat net ou sans
    nombre d'actions actuel, rien n'est vérifiable et le multiple est calculé —
    on ne retire pas sur un soupçon.

    DEVISES DIFFÉRENTES : ON CONVERTIT LE COURS, ON NE RENONCE PLUS.
    Jusqu'au 08/08/2026 cette fonction rendait la main dès que les comptes et
    la cotation n'étaient pas dans la même monnaie, et cinq fiches n'avaient
    aucun multiple historique. `taux` — une fonction date → change, fournie par
    l'appelant — permet de ramener le cours dans la devise des comptes au jour
    de la clôture. Sans elle (paire introuvable, réseau en panne), on retombe
    exactement sur l'ancien comportement : le trou assumé, jamais un multiple
    calculé avec un taux inventé.

    ET LE CERTIFICAT N'EST PAS TOUJOURS L'ACTION. Convertir le cours règle le
    change et laisse entier un second décalage possible : un ADR représente
    plusieurs actions ordinaires, et son cours est donc un multiple du cours de
    l'action. `rapport`, mesuré par `rapport_adr` et jamais supposé, ramène le
    cours à l'unité du bénéfice publié. Sur toutes les fiches observées il vaut
    un — le fournisseur exprime le bénéfice par titre coté, comme le cours — et
    cette division n'a donc encore rien changé à un multiple : elle est là pour
    le jour où les deux unités divergeront. Sans mesure on ne divise pas : un
    rapport inventé ferait un multiple faux."""
    if not meme_devise and taux is None:
        return an
    if rapport is not None and rapport <= 0:
        return an
    import math
    for e in an:
        eps = e.get("eps")
        if not eps or eps <= 0:
            continue
        rn = e.get("rn")
        if actions_actuelles and rn and rn > 0:
            implique = rn * 1e6 / eps
            if abs(math.log(implique / actions_actuelles)) > math.log(3):
                continue              # base d'actions incompatible : pas de PER
        prix = prix_a_la_date(e["fin"])
        if prix and prix > 0 and not meme_devise:
            # Cours ramené dans la devise des COMPTES, au change du jour de
            # clôture. Un exercice dont le taux manque est sauté : mieux vaut
            # un point absent qu'un point faux au milieu d'une courbe juste.
            fx = taux(e["fin"])
            prix = prix * fx if fx and fx > 0 else None
        if prix and prix > 0 and rapport:
            prix = prix / rapport      # cours du certificat → cours de l'action
        if prix and prix > 0:
            e["per"] = round(prix / eps, 1)
    return an


_FX_HIST = {}


def taux_historique(de, vers):
    """Série de change quotidienne `de` → `vers`, rendue comme une fonction
    date ISO → taux (dernier cours connu à cette date), ou None si la paire est
    introuvable.

    POURQUOI CETTE FONCTION EXISTE. Cinq sociétés du site publient leurs comptes
    dans une devise et cotent dans une autre : ABB (comptes en dollars, cotée en
    francs suisses), ASE, Cameco, Ferrari, Vestas. Le quotient cours ÷ bénéfice
    y était refusé — à raison, un cours en francs divisé par un bénéfice en
    dollars donne un taux de change déguisé en multiple — et la fiche affichait
    un trou assumé sur trente et un exercices au total.

    Le refus était bon, la conclusion trop courte : ce qui manquait n'était pas
    une raison de s'abstenir, c'était le TAUX. On ramène donc le cours dans la
    devise des comptes, au change du jour de clôture de l'exercice, et le
    quotient redevient ce qu'il doit être — deux montants dans la même monnaie à
    la même date.

    POURQUOI CONVERTIR LE COURS ET NON LE BÉNÉFICE. Le cours est un prix à un
    INSTANT : il se convertit au taux de cet instant, sans convention. Un
    bénéfice est un flux sur douze mois ; le traduire demanderait un taux moyen
    d'exercice, c'est-à-dire une convention comptable de plus, discutable et
    invisible au lecteur. On convertit donc le terme qui n'en réclame aucune.

    Le résultat reste un ORDRE DE GRANDEUR juste, pas une comptabilité : la
    société elle-même publie ses comparatifs à des taux qui ne sont pas les
    nôtres. C'est très au-dessus de la valeur d'un trou, et très en dessous de
    la précision d'un rapport annuel."""
    # LE PENNY, ET POURQUOI ON N'Y TOUCHE PAS. Londres cote en GBp — des pence —
    # quand les comptes sont en GBP, et il serait tentant d'en faire une
    # conversion : le rapport vaut cent, il est fixe, il n'a pas de cours.
    # ESSAYÉ LE 09/08/2026, ET RETIRÉ LE JOUR MÊME. Le facteur cent ne s'applique
    # pas aux mêmes grandeurs partout : le fournisseur cote BAE Systems en pence
    # mais publie sa CAPITALISATION en livres — c'est écrit noir sur blanc dans
    # validate_tickers.py depuis qu'elle est sortie à 0,8 Md$ le 01/08. Diviser
    # cette capitalisation par cent a publié un rendement du flux disponible de
    # 358 % et un PER prévisionnel de 0,3. Deux nombres faux là où il n'y avait
    # qu'un trou.
    # La leçon est celle du projet, retournée contre moi : le trou plutôt que le
    # faux. Tant que chaque grandeur du fournisseur n'aura pas été mesurée une à
    # une — cours en pence, capitalisation en livres, bénéfice estimé à
    # déterminer —, GBp reste traité comme GBP et les ratios concernés restent
    # absents. La mesure d'abord, la conversion ensuite.
    de, vers = (de or "").upper(), (vers or "").upper()
    if not de or not vers or de == vers:
        return None
    cle = de + vers
    if cle in _FX_HIST:
        return _FX_HIST[cle]
    serie = None
    try:
        h = yf.Ticker(f"{de}{vers}=X").history(period="max", auto_adjust=False)
        if h is not None and len(h) and "Close" in h:
            serie = h["Close"].dropna()
            if not len(serie):
                serie = None
    except Exception as e:                                       # noqa: BLE001
        print(f"  ⚠️  change {de}→{vers} indisponible ({type(e).__name__})")
        serie = None
    if serie is None:
        _FX_HIST[cle] = None
        return None

    def taux(iso):
        try:
            avant = serie[serie.index <= pd.Timestamp(iso, tz=serie.index.tz)]
            return float(avant.iloc[-1]) if len(avant) else None
        except Exception:                                        # noqa: BLE001
            return None

    _FX_HIST[cle] = taux
    return taux


# Bande de croissance annuelle du bénéfice par action jugée POSSIBLE. Elle est
# volontairement large : un bénéfice qui triple ou qui tombe aux deux tiers en
# un exercice existe (reprise post-crise, année de charges). Elle ne sert pas à
# juger une société, seulement à écarter l'absurde — un facteur sept ou trente
# n'est pas une croissance, c'est un changement d'unité.
BANDE_CROISSANCE_BPA = (1 / 3, 3)


def per_previsionnel(prix, estimations, dernier_exercice, taux=None,
                     eps_publie=None, devise_estimations=None,
                     devise_cotation=None, devise_comptes=None):
    """PER des deux exercices À VENIR : cours ACTUEL / BPA moyen estimé par les
    analystes (Yahoo, lignes 0y et +1y). Étiquettes = exercice fiscal suivant le
    dernier clos. estimations : {"0y": eps, "+1y": eps} (None/absent tolérés).

    LA DEVISE DES ESTIMATIONS EST DÉCLARÉE — NOUS NE LA LISIONS PAS.
    Cette fonction a d'abord AFFIRMÉ que « les estimations sont publiées dans la
    devise de cotation », ce qui donnait un PER prévisionnel de 2,0× sur Tencent
    (cours en dollars, bénéfice estimé en yuans) et de 154× sur Vestas. Elle a
    ensuite tenté de DEVINER la devise par la croissance implicite du bénéfice,
    ce qui tranchait deux cas sur six et laissait quatre trous.

    La sonde du 08/08 a montré que la question n'avait pas à être devinée : les
    tables `earnings_estimate` et `revenue_estimate` portent une COLONNE
    `currency` que nous jetions. Elle est fiable, et surtout elle dit ce
    qu'aucune règle n'aurait trouvé — la convention N'EST PAS UNIFORME :

        ticker    comptes  cotation  currency(BPA)  currency(CA)
        TSM       TWD      USD       USD            TWD
        ASX       TWD      USD       USD            TWD
        RACE      EUR      USD       EUR            EUR
        CCJ       CAD      USD       CAD            CAD

    Sur TSM et ASE le bénéfice estimé est libellé PAR ADR et en dollars ; sur
    Ferrari et Cameco il est libellé dans la devise des comptes alors que le
    titre cote en dollars. Une même situation apparente, deux conventions. Le
    départage par la croissance ne pouvait donc pas être « affiné » : il était
    faux dans son principe, et il l'aurait été en silence.

    LA RÈGLE EST MAINTENANT CELLE DE LA SOURCE :
      · devise déclarée == devise de cotation → aucun change. C'est le cas ADR,
        et il se règle tout seul : un bénéfice par ADR divise un cours d'ADR.
      · devise déclarée == devise des comptes → on ramène le COURS dans cette
        devise, exactement comme pour le PER historique.
      · devise déclarée absente → on retombe sur le départage par la croissance
        implicite, décrit plus bas, qui vaut mieux que rien.
      · devise déclarée tierce, ou change indisponible → aucun multiple.

    LE DÉPARTAGE DE SECOURS, quand la source ne déclare rien. Le BPA estimé de
    l'exercice à venir succède au dernier BPA publié, dont nous connaissons la
    devise : leur rapport est une croissance annuelle. Lue dans la bonne monnaie
    elle est plausible ; lue dans l'autre elle vaut le taux de change. Il ne
    tranche que si le change est loin de 1 (Tencent 1,3 contre 9,1) et s'abstient
    sinon (Ferrari 1,08) — d'où son rang de secours.

    UN DÉPARTAGE A ÉTÉ ESSAYÉ ET ÉCARTÉ, noté ici pour qu'on ne le retente pas.
    Le PER courant du fournisseur, pris comme ancrage, a le défaut même qu'il
    devait arbitrer : sur ABB il vaut 37,3 quand notre multiple 2025 en vaut
    28,9, soit le change CHF→USD — la source commet parfois le mélange qu'on
    cherchait à détecter. La place de cotation ne prédit rien non plus, et le
    tableau ci-dessus dit pourquoi : Ferrari et TSM cotent toutes deux à New
    York et ne suivent pas la même convention."""
    if not prix or prix <= 0 or not dernier_exercice:
        return []
    try:
        annee = int(str(dernier_exercice)[:4])
    except (TypeError, ValueError):
        return []
    convertir = False
    if taux is not None:
        t = taux(dernier_exercice) if callable(taux) else taux
        eps0 = (estimations or {}).get("0y")
        if devise_estimations:
            # LA SOURCE DÉCLARE : on obéit, on ne mesure plus.
            if devise_estimations == devise_cotation:
                convertir = False
            elif devise_estimations == devise_comptes:
                if not t or t <= 0:
                    return []      # la devise est connue, le change ne l'est pas
                convertir = True
            else:
                return []          # devise tierce : hors de ce que nous savons lire
        else:
            if not t or t <= 0 or not eps0 or eps0 <= 0 \
                    or not eps_publie or eps_publie <= 0:
                return []          # rien à quoi comparer : on ne devine pas
            bas, haut = BANDE_CROISSANCE_BPA
            # Croissance implicite selon chacune des deux lectures possibles.
            g_comptes = eps0 / eps_publie            # estimation déjà en devise des comptes
            g_cotation = eps0 * t / eps_publie       # estimation en devise de cotation
            ok_c, ok_q = bas <= g_comptes <= haut, bas <= g_cotation <= haut
            if ok_c == ok_q:
                return []          # les deux plausibles, ou aucune : indécidable
            convertir = ok_c
    out = []
    for i, cle in enumerate(("0y", "+1y")):
        eps = (estimations or {}).get(cle)
        if eps and eps > 0:
            p = prix * (taux(dernier_exercice) if callable(taux) else taux) \
                if convertir else prix
            out.append({"exercice": annee + 1 + i, "per": round(p / eps, 1)})
    return out


# Rapports d'ADR usuels : un certificat représente 1, 2, 3, 4, 5 ou 10 actions
# ordinaires, ou une fraction d'action pour les titres à cours élevé.
RAPPORTS_ADR = (10, 5, 4, 3, 2, 1, 1 / 2, 1 / 4, 1 / 5, 1 / 10)
TOLERANCE_ADR = 0.12      # 12 % — un rapport d'ADR est un entier simple, pas un ajustement


def rapport_adr(bpa_estime_an_dernier, eps_publie, taux,
                devise_estimations=None, devise_cotation=None):
    """Le bénéfice publié et le cours lu parlent-ils du même titre ?

    LE RISQUE. Le PER historique divise le cours du titre COTÉ par le bénéfice
    par action des COMPTES. Un certificat TSMC vaut cinq actions de Taipei, un
    certificat ASE en vaut deux : si le cours est celui du certificat et le
    bénéfice celui de l'action, le multiple est faux d'autant — et convertir la
    devise, ce que nous faisons depuis le 08/08, n'y change rien.

    CE QUE LA MESURE A RÉPONDU, et pourquoi cette fonction n'est PAS une
    correction. Nous avons d'abord cru tenir un multiple faux d'un facteur deux
    sur ASE. La mesure dit le contraire : le fournisseur exprime le bénéfice par
    TITRE COTÉ, comme le cours. ASE publie 18,74 sur sa ligne américaine et 8,89
    sur celle de Taipei — le rapport de son ADR exactement —, si bien que le
    quotient est cohérent des deux côtés. Sur les sept fiches concernées le
    rapport vaut UN, et rien n'est divisé. Ce qui reste est une GARDE : le jour
    où une ligne mélangera les deux unités, elle sera vue au lieu d'être publiée.

    COMMENT ON LE MESURE, sans le supposer. La table des estimations porte
    `yearAgoEps` : le bénéfice du dernier exercice clos, dans l'unité et la
    devise du titre coté, telles que la source les déclare. Les comptes portent
    le même exercice. Leur rapport, une fois le change appliqué, EST le facteur
    cherché. Le seul a priori est qu'il vaut un entier simple ou son inverse —
    vrai par construction : un dépositaire ne crée pas de certificat à 1,37 action.

    ET ON S'ABSTIENT SI ÇA NE TOMBE PAS JUSTE. Un rapport à 12 % d'aucune valeur
    usuelle signale que l'une des deux grandeurs n'est pas ce qu'on croit — un
    exercice décalé, un retraitement, une devise mal déclarée. Retourner None
    laisse alors le cours intact plutôt que le corriger d'un facteur inventé."""
    if devise_estimations and devise_cotation \
            and devise_estimations != devise_cotation:
        # Estimations déjà libellées en devise des comptes : le bénéfice estimé
        # et le bénéfice publié parlent de la même action, le rapport vaut 1.
        return 1.0
    if not bpa_estime_an_dernier or not eps_publie or eps_publie <= 0:
        return None
    if not taux or taux <= 0:
        return None
    mesure = bpa_estime_an_dernier * taux / eps_publie
    if mesure <= 0:
        return None
    proche = min(RAPPORTS_ADR, key=lambda r: abs(mesure / r - 1))
    return proche if abs(mesure / proche - 1) <= TOLERANCE_ADR else None


HORIZON_PROJECTION = 2030
CROISSANCE_TERMINALE = 3.0     # % — croissance nominale de long terme d'une économie développée
#
# UNE SEULE COURBE, ASSUMÉE (décision du propriétaire, 07/08 : « je préfère
# qu'on assume une position, on ne parle pas de haut de fourchette »).
#
# Il y avait ici un PLAFOND_EXTRAPOLATION à 25 % qui donnait une branche
# « prudente », doublée d'une branche « haute » au rythme du consensus — et le
# front dessinait le cône entre les deux. Deux choses ont fait tomber ce
# dispositif.
#
# 1. LA MESURE. Sur TSMC, un concurrent qui publie du consensus multi-annuel
#    annonce +25,8 % puis +28,0 % pour 2028-2029. Notre branche prudente
#    disait +13,0 % et +9,6 % — 24 % sous leur chiffre en fin d'horizon. Notre
#    branche haute, elle, tombait à 1 % près sur 2028. Ce n'était donc pas une
#    fourchette encadrant la vérité : c'était une bonne réponse et une
#    mauvaise, publiées ensemble.
#
# 2. LE DIAGNOSTIC. Le plafond n'était presque jamais ce qui mordait (2 fiches
#    sur 93 changent si on le retire seul). Le vrai frein était `min(g_att,
#    g_dem)` : brider le consensus par le TCAM historique. C'est de la prudence
#    empilée sur de la prudence — la décroissance vers 3 % assure déjà qu'on ne
#    prolonge pas un rythme record éternellement ; y ajouter un a priori tiré
#    d'un passé d'avant-cycle fait systématiquement sous-tirer.
#
# La règle est donc : ON PART DU RYTHME DU CONSENSUS et on décroît vers 3 %.
# Le TCAM démontré reste un CRITÈRE DE REFUS (voir plus bas) — s'il est sous le
# taux terminal, on ne prolonge pas du tout —, mais il ne rabote plus le point
# de départ. Les deux séparations comptent : refuser est une position, raboter
# était une pudeur.
#
# SEUIL DE REFUS — au-delà, on ne prolonge plus DU TOUT.
#
# Ce seuil n'est pas un plafond : c'est une frontière de compétence. Quand le
# consensus implique plus de 50 % par an (Nebius : +312 % entre 2025 et 2027),
# toute réponse arithmétique est fausse et nous l'avons vérifié sur ce titre :
# plafonner donnait 18 Md$ en 2030 quand le marché en discute 33 à 46 ; ne pas
# plafonner donnait 140 Md$. Un tel rythme signale une trajectoire portée par
# des ENGAGEMENTS CONTRACTUELS — un carnet pluriannuel signé — que ni les
# comptes publiés ni le consensus à deux ans ne décrivent. Aucune donnée dont
# nous disposons ne permet de la prolonger honnêtement.
#
# On applique donc aux projections la règle déjà en vigueur pour la note : ce
# qu'on ne sait pas calculer n'est pas approximé, il est RETIRÉ AVEC SON MOTIF.
# Le consensus reste affiché — c'est un fait publié — et la courbe s'arrête là,
# en disant pourquoi. C'est CE seuil qui protège des cas extrêmes, pas le
# plafond qu'il a remplacé : refuser franchement vaut mieux que publier une
# valeur amortie qu'on sait fausse.
SEUIL_REFUS = 50.0


def projections(an, estimations_bpa, estimations_ca, dernier_exercice,
                bpa_comparable=True,
                horizon=HORIZON_PROJECTION, g_terminale=CROISSANCE_TERMINALE,
                seuil_refus=SEUIL_REFUS):
    """Trajectoire attendue du CA et du BPA jusqu'à `horizon`.

    DEUX NATURES DE VALEURS, JAMAIS CONFONDUES — c'est tout l'objet de cette
    fonction, et la raison pour laquelle chaque SÉRIE porte la sienne
    (`ca_nature`, `eps_nature`), l'année ne portant qu'un résumé prudent :

      · « consensus » : les DEUX seuls exercices que les analystes couvrent
        réellement (exercice en cours et suivant, publiés par Yahoo). Ce sont
        des estimations d'humains qui suivent la société.
      · « extrapolé » : tout ce qui va au-delà. Ces lignes sont une
        PROLONGATION ARITHMÉTIQUE de notre fait, pas une opinion de marché.
        Le front doit les distinguer visuellement, et elles n'entrent JAMAIS
        dans la note.

        CE COMMENTAIRE A LONGTEMPS DIT « aucun analyste ne publie à cinq ans
        par société ». C'EST FAUX, et la vérification l'a montré : sur
        Alphabet, un concurrent affiche +19,1 %, +13,0 %, +14,8 % pour
        2028-2030 — un profil IRRÉGULIER, donc des estimations réelles, là où
        le nôtre décroît lissé parce que c'est une formule. Ce que nous
        pouvons dire est plus étroit : NOTRE source (Yahoo, `earnings_estimate`
        / `revenue_estimate`) ne couvre que deux exercices. Le reste est notre
        arithmétique faute de données, pas faute de données existantes. Yahoo
        expose par ailleurs `growth_estimates` (dont un taux annuel à cinq
        ans) que nous ne lisons pas encore — piste ouverte, à publier brut
        avant d'y brancher quoi que ce soit : deux erreurs d'unité supposée
        (dividendes, devise du consensus) ont déjà coûté cher ici.

    LA RÈGLE DE PROLONGATION, en une phrase : la croissance part du dernier
    rythme attendu et décroît linéairement vers 3 % à l'horizon — parce
    qu'aucune entreprise ne croît à 30 % éternellement, et qu'une projection
    à taux constant est le mensonge le plus courant de l'exercice. Le taux de
    départ est borné par la croissance DÉMONTRÉE quand elle est plus basse
    (même prudence que le PEG : l'estimé ne dépasse pas le prouvé).

    Le BPA n'est projeté que s'il est POSITIF au départ : prolonger une perte
    produirait une courbe qui ne veut rien dire (cas Nebius). Le CA, lui, se
    projette dès qu'il croît — c'est souvent la seule trajectoire lisible
    d'une société en phase d'investissement.

    ET QUAND ON NE SAIT PAS, ON S'ARRÊTE. Si le rythme attendu dépasse
    `seuil_refus`, la série n'est PAS prolongée du tout : seuls les exercices
    de consensus sortent, et le dernier porte `<cle>_arret`, le motif à
    afficher. Une projection qu'on sait fausse ne vaut pas mieux qu'un blanc :
    elle vaut moins, parce qu'elle se donne l'air d'un fait.

    LE PIÈGE DES DEVISES, et pourquoi `bpa_comparable` existe. Le chiffre
    d'affaires estimé est toujours publié dans la devise COMPTABLE — vérifié
    ligne à ligne le 08/08 : TSM et 2330.TW rendent le MÊME nombre, à l'unité
    près. Le bénéfice par action estimé, lui, suit une convention qui VARIE
    d'un titre à l'autre : par ADR et en dollars sur TSM et ASE, en devise
    comptable sur Ferrari et Cameco. C'est la colonne `currency` de la table
    qui le dit, et c'est à l'appelant de la lire.

    Ce paramètre s'appelait `meme_devise` et cette docstring AFFIRMAIT que le
    BPA estimé était « publié dans la devise de cotation ». La moitié des cas
    observés dit le contraire. Le nom disait une comparaison de devises ; ce
    qui compte est plus simple et plus juste : le BPA estimé est-il libellé
    comme la série publiée ? Si oui on le projette, si non on l'ignore et le
    bénéfice reste prolongeable depuis le seul historique, cohérent avec
    lui-même. Sur TSM le mélange donnait 331,25 TWD publiés prolongés en 16,82 :
    le taux de croissance n'était pas une opinion de marché, c'était un taux de
    change.

    On n'essaie PAS de rapatrier un BPA estimé libellé en devise de cotation :
    il faudrait un taux de change FUTUR, que personne n'a. Le trou est ici la
    seule réponse honnête, et il ne concerne que le bénéfice.

    Pure et testable hors ligne. Rend [] si rien n'est projetable.
    """
    if not dernier_exercice:
        return []
    if not bpa_comparable:
        estimations_bpa = None
    try:
        an0 = int(str(dernier_exercice)[:4])
    except (TypeError, ValueError):
        return []
    if an0 >= horizon:
        return []

    def _dernier(cle):
        for e in reversed(an or []):
            if e.get(cle) is not None:
                return e[cle]
        return None

    def _tcam_demontre(cle):
        pts = [(int(e["fin"][:4]), e[cle]) for e in (an or [])
               if e.get(cle) and e[cle] > 0]
        # MÊME série que la note. Sans cette ligne, la fiche se contredisait
        # elle-même : le bloc croissance annonçait « +19,2 % par an » (série
        # tronquée à la rupture de périmètre) pendant que les projections
        # refusaient de prolonger « faute de rythme constaté » — en mesurant,
        # elles, à travers la marche. Un même chiffre d'affaires ne peut pas
        # avoir deux trajectoires sur la même page. (Le bénéfice n'est jamais
        # tronqué : cf. note_v4.apres_rupture.)
        if cle == "ca":
            pts = note_v4.apres_rupture(pts)
        if len(pts) < 3 or pts[-1][0] <= pts[0][0]:
            return None
        return ((pts[-1][1] / pts[0][1]) ** (1 / (pts[-1][0] - pts[0][0])) - 1) * 100

    lignes = {}

    def _poser(cle, vals, arret=None):
        """Écrit une série dans `lignes`. `arret` = motif d'arrêt, porté par la
        DERNIÈRE année de CETTE série (le CA peut s'arrêter là où le BPA
        continue). `nature` existe en deux exemplaires : par série
        (`<cle>_nature`, exacte) et par année (prudente, la plus incertaine des
        deux séries) — sans la version par série, un BPA extrapolé ferait
        passer pour « extrapolé » un chiffre d'affaires qui est du consensus."""
        arr = 4 if cle == "eps" else 0
        for annee in sorted(vals):
            t = vals[annee]
            ligne = lignes.setdefault(annee, {"exercice": annee})
            ligne[cle] = round(t[0], arr)
            ligne[cle + "_nature"] = t[1]
            if ligne.get("nature") != "extrapolé":
                ligne["nature"] = t[1]
        if arret and vals:
            lignes[max(vals)][cle + "_arret"] = arret

    for cle, est in (("ca", estimations_ca), ("eps", estimations_bpa)):
        base = _dernier(cle)
        # 1) LES DEUX EXERCICES DE CONSENSUS, TELS QUE PUBLIÉS — quel que soit
        #    leur SIGNE.
        #
        #    Ces deux gardes filtraient les valeurs négatives (`base <= 0` en
        #    sortie de boucle, `v > 0` ici) : une société dont les analystes
        #    attendent des PERTES n'affichait donc aucun bénéfice attendu, pas
        #    même le consensus. C'était contraire à notre propre règle — « le
        #    consensus reste affiché, c'est un fait déposé, pas une opinion à
        #    nous » — et ça se voyait : sur Nebius et CoreWeave, un concurrent
        #    affiche les barres de pertes attendues là où nos fiches ne
        #    montraient rien du tout (constaté par le propriétaire, 07/08).
        #
        #    Une perte attendue EST une information, et souvent la principale.
        #    Ce qu'on continue de refuser, c'est de la PROLONGER : faire
        #    décroître une perte vers +3 % de croissance n'a aucun sens, et le
        #    refus est posé juste en dessous avec son motif.
        #    UN ZÉRO EXACT N'EST PAS UNE ESTIMATION, C'EST UNE ABSENCE. Le
        #    fournisseur rend `0` là où il n'a pas de consensus, et rien ne
        #    distingue les deux dans la réponse. Constaté le 08/08/2026 sur
        #    Rainbow Robotics à l'entrée de la watchlist robotique : chiffre
        #    d'affaires 2026 ET 2027 publiés à 0,0 en « consensus », contre
        #    34 milliards de wons réalisés en 2025 — la fiche aurait montré des
        #    barres de revenus s'effondrant à zéro, en affirmant que c'est ce
        #    que les analystes attendent.
        #    Ce filtre ne revient PAS sur la règle du dessus : les valeurs
        #    NÉGATIVES restent publiées, une perte attendue est une information.
        #    Il ne retire que le zéro exact, qu'aucune société cotée n'atteint
        #    réellement et qui ne peut donc être qu'un trou de données. Retiré
        #    plutôt qu'approximé, comme un critère de la note.
        vals, dernier_val, dernier_an = {}, base, an0
        for i, k in enumerate(("0y", "+1y")):
            v = (est or {}).get(k)
            if v is not None and v != 0:
                vals[an0 + 1 + i] = (v, "consensus")
                dernier_val, dernier_an = v, an0 + 1 + i
        # 2) PROLONGER EXIGE UNE BASE ET UNE ARRIVÉE POSITIVES. Le taux de
        #    croissance composé n'est pas défini autrement : élever un rapport
        #    négatif à une puissance fractionnaire donne un nombre complexe.
        if base is None or base <= 0 or dernier_val is None or dernier_val <= 0:
            _poser(cle, vals,
                   "la série est en perte : une perte ne se prolonge pas vers "
                   "un taux de croissance, et nous n'inventons pas de retour "
                   "à l'équilibre")
            continue
        if dernier_an > an0:
            g_att = ((dernier_val / base) ** (1 / (dernier_an - an0)) - 1) * 100
        else:
            g_att = _tcam_demontre(cle)
            if g_att is None:
                continue                  # ni consensus ni historique : on ne prolonge pas
        g_dem = _tcam_demontre(cle)
        # `g_plancher` ne sert QU'AUX REFUS : c'est le plus bas des deux
        # rythmes, et s'il passe sous le taux terminal, prolonger n'a pas de
        # sens. Il ne sert plus à rabaisser le point de départ — voir le
        # commentaire de CROISSANCE_TERMINALE.
        g_plancher = min(g_att, g_dem) if g_dem is not None else g_att
        # ── LES DEUX REFUS DE PROLONGER ──────────────────────────────────
        # Ce qu'on ne sait pas calculer n'est pas approximé : il est RETIRÉ
        # AVEC SON MOTIF, exactement comme un critère de la note. Le consensus,
        # lui, reste publié — c'est un fait déposé, pas une opinion à nous.
        #
        #  · PAR LE HAUT (au-delà de SEUIL_REFUS) : toute prolongation est
        #    fausse, amortir sous-estime et ne pas amortir délire.
        #  · PAR LE BAS (sous le taux terminal) : le modèle DÉCROÎT vers 3 %,
        #    il suppose donc un départ au-dessus. Partir d'un rythme démontré
        #    négatif et le « faire décroître » vers +3 % inventerait une
        #    inflexion que rien n'annonce — c'est le cas du BPA de Nebius,
        #    −36 % par an constatés, qu'on publiait en hausse jusqu'en 2030.
        # Motifs rédigés comme des PROPOSITIONS, sans sujet ni ponctuation
        # finale : le front les enchâsse dans sa phrase (« Au-delà de 2027,
        # nous n'avançons rien : … »).
        if g_att > seuil_refus:
            _poser(cle, vals,
                   "la suite dépend d'engagements contractuels que nos sources "
                   "ne décrivent pas, et une projection qu'on sait fausse ne "
                   "vaut pas mieux qu'un blanc")
            continue
        if g_plancher < g_terminale:
            _poser(cle, vals,
                   "le rythme constaté ne soutient aucune prolongation "
                   "crédible, et nous n'inventons pas d'inflexion")
            continue
        # LE TAUX DE DÉPART, ASSUMÉ : celui du consensus, tel que les analystes
        # le projettent. Il est sous le seuil de refus et au-dessus du taux
        # terminal, sinon on ne serait pas arrivé ici.
        g = g_att
        # 3) prolongation à croissance décroissante vers le taux terminal
        n = horizon - dernier_an
        v = dernier_val
        for i in range(1, n + 1):
            fade = 1 - i / (n + 1)
            v *= 1 + (g_terminale + (g - g_terminale) * fade) / 100
            vals[dernier_an + i] = (v, "extrapolé")
        _poser(cle, vals)
    return [lignes[a] for a in sorted(lignes)]


def _nombre(v):
    """Convertit en float ce que Yahoo sérialise parfois en texte.

    Relevé par la sonde du 07/08 : dans `revenue_estimate`, `avg`, `low`, `high`
    et `numberOfAnalysts` arrivent en CHAÎNES ("5420351505550"), alors que les
    mêmes colonnes de `earnings_estimate` arrivent en flottants. Supposer l'un
    ou l'autre casse une fois sur deux."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None            # NaN → None


def _solidite_consensus(table, cle="0y"):
    """Sur quoi repose le consensus : combien d'analystes, et quel désaccord.

    POURQUOI C'EST PUBLIÉ. Depuis que la trajectoire est une courbe unique et
    assumée, elle a l'autorité d'une affirmation. Or la sonde a mesuré des
    fondations très inégales : 50 analystes sur Alphabet contre DEUX sur
    Constellation Energy, une fourchette de ±1 % sur Booking contre ±16 % sur
    Nebius. Le lecteur a besoin de savoir laquelle il regarde.

    `ecart_pct` est la DEMI-fourchette rapportée à la moyenne : « ±4 % » se lit
    directement comme le désaccord entre analystes, alors qu'un rapport
    haut/bas demande un calcul mental.
    """
    try:
        if table is None or cle not in table.index:
            return None
        cols = getattr(table, "columns", [])
        n = _nombre(table.loc[cle, "numberOfAnalysts"]) if "numberOfAnalysts" in cols else None
        lo = _nombre(table.loc[cle, "low"]) if "low" in cols else None
        hi = _nombre(table.loc[cle, "high"]) if "high" in cols else None
        av = _nombre(table.loc[cle, "avg"]) if "avg" in cols else None
        dev = table.loc[cle, "currency"] if "currency" in cols else None
    except Exception:
        return None
    out = {}
    if n is not None and n > 0:
        out["analystes"] = int(n)
    if lo is not None and hi is not None and av and av > 0 and hi >= lo:
        out["ecart_pct"] = round((hi - lo) / 2 / av * 100, 1)
    if isinstance(dev, str) and dev:
        out["devise"] = dev
    return out or None


def croissance_ca_trimestrielle(tr):
    """Croissance du CA du dernier trimestre publié, en glissement annuel (%).

    POURQUOI NOUS LA CALCULONS AU LIEU DE LIRE `revenueGrowth` DE YAHOO.
    Question du propriétaire, 07/08 : « Croiss CA · a/a +12,7 %, ça correspond
    à quoi ? ». Le recoupement contre notre PROPRE historique trimestriel — les
    barres qu'on dessine juste au-dessus de la tuile — a montré que la réponse
    n'était pas celle qu'on croyait, sur 18 fiches publiées sur 83 :

      · DÉSYNCHRONISATION (30 fiches). `revenueGrowth` porte sur le trimestre
        que le bloc `info` de Yahoo estimait le plus récent. Notre série, elle,
        s'ACCUMULE d'un run à l'autre (fusionner_fonda) et va souvent plus loin.
        La tuile parlait donc d'un trimestre que le graphique ne montrait plus
        comme le dernier — SNDK annonçait +371,6 % là où le dernier trimestre
        dessiné en donne +251,0.
      · DÉFINITION DU REVENU (6 fiches). Même en recalculant sur le trimestre
        que Yahoo désigne, l'écart persiste sur des assureurs et des services
        aux collectivités : Constellation Energy annonçait +23,0 % quand ses
        propres comptes trimestriels donnent −4,2 %. Le « revenue » de Yahoo
        n'y recouvre pas la ligne que nous portons au graphique.

    Un chiffre qui contredit la barre juste au-dessus de lui n'est pas une
    approximation, c'est une contradiction. On le calcule donc sur la série
    qu'on publie, avec la RÈGLE DU TABLEAU : le même trimestre un an plus tôt,
    jamais le précédent, qui ne raconterait que la saisonnalité.

    Retourne None si la comparaison n'est pas possible (moins de deux
    trimestres, pas d'homologue à un an, base nulle ou négative) — auquel cas
    l'appelant garde la valeur de Yahoo, faute de mieux, plutôt qu'un blanc.
    """
    pts = [r for r in (tr or []) if r.get("ca") is not None]
    if len(pts) < 2:
        return None
    dernier = pts[-1]
    try:
        d0 = _dt.strptime(dernier["fin"], "%Y-%m-%d")
    except (ValueError, KeyError, TypeError):
        return None
    # Fenêtre 330–400 jours : un exercice décalé ou un trimestre publié avec
    # quelques jours d'écart reste apparié, un semestre ne l'est pas.
    for p in pts:
        try:
            j = (d0 - _dt.strptime(p["fin"], "%Y-%m-%d")).days
        except (ValueError, KeyError, TypeError):
            continue
        if 330 < j < 400 and p["ca"] > 0:
            return round((dernier["ca"] / p["ca"] - 1) * 100, 1)
    return None


def fusionner_fonda(ancien, nouveau, max_an=edgar.MAX_EXERCICES,
                    max_tr=edgar.MAX_TRIMESTRES):
    """Accumule l'historique des chiffres publiés entre les runs.

    Yahoo ne conserve que ~5 trimestres : sans mémoire, un trimestre sorti de
    sa fenêtre disparaîtrait du site, et la variation « vs même trimestre un
    an plus tôt » resterait éternellement cantonnée à la dernière ligne. On
    fusionne donc par date de clôture — le run le plus récent fait foi à date
    égale (chiffres révisés par l'émetteur). Bornes larges (12 exercices,
    20 trimestres, ~50 octets l'entrée) : le front affiche TOUT ce qui est
    accumulé, la borne n'est qu'un garde-fou de croissance. Pure."""
    if not nouveau:
        return ancien or None
    if not ancien:
        return nouveau
    from datetime import date as _date

    def _j(iso):
        return _date(*map(int, iso.split("-"))).toordinal()

    out = {"devise": nouveau.get("devise") or ancien.get("devise")}
    # LE PER EST CALCULÉ, PAS PUBLIÉ — il ne se conserve donc que si la façon
    # de le calculer n'a pas bougé. Les exercices anciens ne sont plus produits
    # par le run courant (Yahoo n'en garde que quatre) : leur multiple traverse
    # la fusion tel quel, avec le change et le rapport d'ADR du jour où il a été
    # écrit. Quand cette base change — une paire de change qui apparaît, un
    # rapport d'ADR mesuré pour la première fois — les vieux multiples deviennent
    # faux en silence à côté des nouveaux, corrects. ASE en portait sept, tous
    # doubles de leur vraie valeur, sous quatre exercices justes.
    # C'est la même leçon que la marge nette lue hors de la série dessinée : une
    # valeur dérivée ne se garde pas, elle se refait — ou elle se retire.
    _b_av, _b_ap = (ancien.get("per_converti") or {}), (nouveau.get("per_converti") or {})
    _meme_base = ((_b_av.get("de"), _b_av.get("vers"), _b_av.get("rapport"))
                  == (_b_ap.get("de"), _b_ap.get("vers"), _b_ap.get("rapport")))
    for cle, borne in (("an", max_an), ("tr", max_tr)):
        frais = {e["fin"] for e in (nouveau.get(cle) or [])}
        par_fin = {e["fin"]: (e if (_meme_base or "per" not in e)
                              else {k: v for k, v in e.items() if k != "per"})
                   for e in (ancien.get(cle) or [])}
        par_fin.update({e["fin"]: e for e in (nouveau.get(cle) or [])})
        tri = [par_fin[k] for k in sorted(par_fin)]
        # Dédoublonnage à ±7 jours ENTRE runs : Yahoo et EDGAR peuvent dater le
        # même trimestre à quelques jours près selon le run (ON : 2025-03-31 vs
        # 2025-04-04, calendrier fiscal en semaines de 52/53). À date proche,
        # l'entrée du run COURANT fait foi ; à défaut, la plus récente.
        dedup = []
        for e in tri:
            if dedup and _j(e["fin"]) - _j(dedup[-1]["fin"]) <= 7:
                if e["fin"] in frais or dedup[-1]["fin"] not in frais:
                    dedup[-1] = e
                continue
            dedup.append(e)
        # Un exercice fantôme déjà PUBLIÉ (AMZN, frame CY2026 arrêté fin juin)
        # survivrait indéfiniment à la fusion : le run courant ne le produit
        # plus, donc ne l'écrase jamais. Le filtre de clôture majoritaire est
        # rejoué sur l'union — par APPEL à edgar, plus par recopie : la règle
        # vivait ici en double et deux copies d'une règle sont deux règles qui
        # divergent. Ses limites connues (tâche #83) sont écrites à sa source.
        if cle == "an":
            dedup = edgar.filtrer_cloture_majoritaire(dedup)
        out[cle] = dedup[-borne:]
    # PER prévisionnels : ce sont des estimations COURANTES, le run le plus
    # récent fait foi ; à défaut (Yahoo muet un jour), on garde les anciennes,
    # leurs étiquettes d'exercice rendent tout vieillissement visible.
    #
    # SAUF QUAND L'ABSENCE EST UNE DÉCISION. Ce repli a été écrit pour une
    # PANNE — la source muette un jour — et il ne sait pas la distinguer d'un
    # REFUS. Depuis le 09/08/2026 nous refusons de publier un multiple
    # prévisionnel quand la devise des estimations reste indécidable ; le run
    # rendait donc une liste vide, et la fusion ressuscitait aussitôt les
    # valeurs de la veille, celles-là mêmes qu'on venait d'écarter. Quatre
    # fiches ont continué d'afficher leur ancien multiple après le correctif,
    # `pe_prev_indecis` posé juste à côté.
    # C'est mot pour mot la leçon déjà tirée sur `proj` deux lignes plus bas :
    # un retrait est une décision, et reprendre celle d'hier l'annule.
    pe = nouveau.get("pe_prev") or (
        None if nouveau.get("pe_prev_indecis") else ancien.get("pe_prev"))
    if pe:
        out["pe_prev"] = pe
    # Trajectoire attendue : le run COURANT fait foi, SANS repli sur l'ancienne.
    #
    # Contrairement au PER prévisionnel, une projection périmée n'est pas
    # seulement vieille, elle peut être RÉTRACTÉE : depuis que le screener
    # refuse de prolonger ce qu'il ne sait pas calculer, l'absence de
    # projection est une DÉCISION, pas un silence de Yahoo. Reprendre celle du
    # run précédent ressusciterait exactement la courbe qu'on vient de retirer.
    #
    # Cette fonction reconstruit le bloc `fonda` de zéro (elle ne part pas de
    # `nouveau`) : tout champ qu'elle ignore est SILENCIEUSEMENT PERDU à la
    # publication. C'est ce qui est arrivé à `proj` le 07/08 — 96 fiches sur 97
    # publiées sans trajectoire, seule la fiche créée ce jour-là (RMS.PA, donc
    # sans ancien à fusionner) en portait une. Tout nouveau champ de `fonda`
    # doit être ajouté ICI.
    if nouveau.get("proj"):
        out["proj"] = nouveau["proj"]
    # Même règle que `proj`, et pour la même raison : la solidité du consensus
    # décrit le run COURANT (combien d'analystes suivent la société
    # aujourd'hui, de combien ils divergent). Reprendre celle d'hier
    # attribuerait à la trajectoire d'aujourd'hui des fondations qui ne sont
    # plus les siennes.
    if nouveau.get("consensus"):
        out["consensus"] = nouveau["consensus"]
    # Même règle encore : la mention « multiples obtenus en convertissant le
    # cours » décrit la façon dont les PER de CE run ont été calculés. Elle
    # suit donc le run courant et disparaît si la paire de change redevient
    # indisponible — auquel cas les multiples disparaissent avec elle.
    if nouveau.get("per_converti"):
        out["per_converti"] = nouveau["per_converti"]
    # Même règle : l'indécision sur la devise des estimations décrit le run
    # courant. Si la source publiait demain des chiffres départageables, la
    # mention doit disparaître avec eux.
    if nouveau.get("pe_prev_indecis"):
        out["pe_prev_indecis"] = nouveau["pe_prev_indecis"]
    return out


# ── ÉCLATEMENT DU PAYLOAD GRAPHIQUE (charts/<TICKER>.json) ───────────────────
# POURQUOI un fichier par titre plutôt qu'un monolithe : le graphe pèse ~19 Ko
# par titre. Tant qu'on n'en publiait que 30, un charts.json de 561 Ko passait.
# Depuis que 184 titres sont tagués par un thème et méritent donc une fiche
# complète, le monolithe atteindrait ~3,5 Mo — téléchargés intégralement au
# premier rendu pour n'afficher, au mieux, UN graphe. Le front charge désormais
# charts/<TICKER>.json à l'ouverture de la fiche : le coût est proportionnel à
# ce qui est réellement regardé.
CHARTS_DIR = "charts"

# CONVENTION DE NOMMAGE : charts/<TICKER>.json, ticker VERBATIM, sans encodage.
# Les tickers Yahoo comportent des points (ASML.AS, 000660.KS) et des tirets
# (SAAB-B.ST, NOVO-B.CO). Ni l'un ni l'autre n'a de signification particulière
# dans un nom de fichier (POSIX comme NTFS) ni dans un segment de chemin d'URL
# — aucun échappement n'est donc nécessaire, et « ASML.AS.json » reste servi en
# application/json par GitHub Pages, qui se fie à la DERNIÈRE extension.
# Le garde-fou ci-dessous n'est pas cosmétique : un ticker contenant « / » ou
# « .. » écrirait hors du dossier. Le jeu autorisé est exactement celui de
# l'univers actuel ([A-Z0-9.-], vérifié sur les 210 tickers). Il interdit aussi
# les minuscules, ce qui rend impossible la collision de deux tickers ne
# différant que par la casse sur un système de fichiers insensible (macOS).
_TICKER_FICHIER = re.compile(r"[A-Z0-9][A-Z0-9.-]*\Z")


def publier_charts(charts, a_publier, dossier=CHARTS_DIR, breakdowns=None):
    """Écrit charts/<TICKER>.json pour chaque fiche ouvrable, purge les orphelins.

    charts     : ticker → payload graphique, pour TOUT l'univers scoré.
    a_publier  : tickers dont le site sait ouvrir une fiche (titres tagués par un
                 thème + top 30). Le reste de l'univers n'a pas de fiche, donc
                 pas de graphe à servir.
    breakdowns : ticker → breakdown COMPLET du scoring (optionnel). Embarqué
                 dans chaque fichier sous la clé "breakdown", il donne aux
                 fiches thématiques les mêmes données que les fiches du top 30
                 (fondamentaux, marges, fibo…) sans alourdir universe.json, qui
                 est téléchargé en bloc au premier rendu : le breakdown ne pèse
                 que sur la fiche réellement ouverte (~2 Ko par fichier). Le
                 payload est copié, jamais muté — les dicts de `charts` sont
                 partagés avec l'appelant, qui les réutilise pour l'archive.

    POURQUOI la purge : un titre qui quitte tous ses thèmes n'est plus jamais
    réécrit. Sans suppression explicite son graphe resterait indéfiniment dans
    le dépôt — et surtout resterait SERVI, donc affichable via une URL périmée
    portant des données figées à la semaine de sa sortie.

    Même contrat d'écriture que le reste du projet : tmp + os.replace (jamais de
    fichier tronqué visible par le front), allow_nan=False (un NaN fait échouer
    le run bruyamment plutôt que de publier un token illisible par JSON.parse),
    séparateurs compacts.

    Retourne (écrits, purgés, sans_graphe, refusés) — quatre listes de tickers.
    """
    os.makedirs(dossier, exist_ok=True)

    ecrits, refuses = [], []
    for ticker in sorted(a_publier):
        if ticker not in charts:
            continue                      # journalisé plus bas via sans_graphe
        if not _TICKER_FICHIER.match(ticker):
            refuses.append(ticker)
            continue
        chemin = os.path.join(dossier, f"{ticker}.json")
        tmp = chemin + ".tmp"
        payload = charts[ticker]
        if breakdowns and ticker in breakdowns:
            payload = {**payload, "breakdown": breakdowns[ticker]}
        # Chiffres publiés : fusion avec l'historique déjà sur disque — c'est
        # ici que la mémoire s'accumule d'un run à l'autre (cf. fusionner_fonda).
        # Fail-soft : un ancien fichier illisible ne bloque pas la publication.
        if payload.get("fonda"):
            try:
                with open(chemin, encoding="utf-8") as anc:
                    fusion = fusionner_fonda(json.load(anc).get("fonda"),
                                             payload["fonda"])
                if fusion:
                    payload = {**payload, "fonda": fusion}
            except FileNotFoundError:
                pass
            except Exception:
                pass
            # LA CROISSANCE TRIMESTRIELLE SE RECALCULE ICI, et pas plus tôt :
            # c'est APRÈS la fusion que la série définitive est connue, et
            # c'est elle que le graphique dessine. Calculer avant reviendrait à
            # commenter une série qui n'est pas celle qu'on publie.
            #
            # `mrq` N'EST PAS TOUCHÉ, et c'est délibéré. La désynchronisation
            # va dans le sens inverse de l'intuition : le bloc `info` de Yahoo
            # est PLUS FRAIS que son propre endpoint d'états financiers (SNDK :
            # `mrq` au 03/07, notre dernier trimestre accumulé au 31/03). Or
            # `mrq` date aussi les marges TTM, qui viennent bien de ce bloc
            # frais. Le réécrire aurait reculé la date des marges pour arranger
            # celle de la croissance — on aurait déplacé l'incohérence au lieu
            # de la corriger. Chaque chiffre porte donc SA date.
            _tr = (payload.get("fonda") or {}).get("tr") or []
            _g = croissance_ca_trimestrielle(_tr)
            if _g is not None and payload.get("breakdown"):
                payload = {**payload,
                           "breakdown": {**payload["breakdown"],
                                         "rev_growth_pct": _g,
                                         "rev_growth_fin": _tr[-1]["fin"]}}
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
            os.replace(tmp, chemin)
        except Exception:
            # Un .tmp abandonné dans un dossier suivi par git serait committé au
            # run suivant : on nettoie avant de laisser remonter l'échec.
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        ecrits.append(ticker)

    attendus = {f"{t}.json" for t in ecrits}
    purges = []
    for nom in sorted(os.listdir(dossier)):
        if not nom.endswith(".json") or nom in attendus:
            continue
        os.remove(os.path.join(dossier, nom))
        purges.append(nom[:-len(".json")])

    # Doctrine anti-troncature : tout ce qui est omis est journalisé. Une fiche
    # sans graphe est un manque VISIBLE sur le site — s'il n'est pas tracé côté
    # run, on l'impute au front et on cherche au mauvais endroit.
    sans_graphe = sorted(t for t in a_publier if t not in charts)

    print(f"📈 {dossier}/ — {len(ecrits)} graphes écrits"
          + (f", {len(purges)} purgé(s)" if purges else ""))
    if purges:
        print(f"   🧹 purgés (fiche plus ouvrable) : {', '.join(purges)}")
    if sans_graphe:
        print(f"   ⚠️  {len(sans_graphe)} fiche(s) sans graphe (payload en échec au "
              f"scoring) : {', '.join(sans_graphe)}")
    if refuses:
        print(f"   ⚠️  {len(refuses)} ticker(s) au nom non écrivable, graphe non publié : "
              f"{', '.join(refuses)}")
    return ecrits, purges, sans_graphe, refuses

# ── RETRACEMENT DE FIBONACCI ─────────────────────────────────────────────────
def fibonacci_retracement(close_series, lookback=252):
    """
    Identifie le swing low avant le plus haut de la fenêtre, calcule les niveaux
    Fibo 23.6 / 38.2 / 50 / 61.8 et la position actuelle dans le retracement.

    Annotation INFORMATIONNELLE — n'entre pas dans le scoring (qui reste sur
    drawdown 52w simple). Donne le contexte chartiste classique pour interpréter
    si le repli actuel est un retracement sain ou une trend cassée.

    Retourne dict ou None si pas de rally identifiable :
      swing_low      : prix du plus bas avant le plus haut
      swing_high     : plus haut de la fenêtre (≈ high_52w)
      rally_pct      : taille du rally (high-low)/low en %
      retrace_pct    : retracement actuel en % du rally (0=top, 100=swing_low)
      closest_fibo   : niveau Fibo le plus proche du cours actuel (label)
      fibo_levels    : dict {label → prix} des 4 niveaux classiques
    """
    try:
        if len(close_series) < 50:
            return None
        window = close_series.iloc[-lookback:] if len(close_series) >= lookback else close_series
        if len(window) < 30:
            return None

        # Plus haut de la fenêtre
        high_idx = window.idxmax()
        high_pos = window.index.get_loc(high_idx)
        if high_pos == 0:
            return None  # high au tout début → pas de swing low identifiable

        # Swing low : plus bas avant le plus haut (dans la même fenêtre)
        pre_high   = window.iloc[:high_pos + 1]
        swing_low  = float(pre_high.min())
        swing_high = float(window.iloc[high_pos])
        rally      = swing_high - swing_low

        # Rally minimum 15% pour que le retracement Fibo ait du sens chartistement
        # (en-dessous, on est dans le bruit, pas dans une trend identifiable)
        if swing_low <= 0 or rally / swing_low < 0.15:
            return None

        rally_pct  = rally / swing_low * 100
        current    = float(close_series.iloc[-1])
        retrace_pct = (swing_high - current) / rally * 100 if rally > 0 else 0

        fibo_levels = {
            "23.6": round(swing_high - 0.236 * rally, 2),
            "38.2": round(swing_high - 0.382 * rally, 2),
            "50.0": round(swing_high - 0.500 * rally, 2),  # Dow/Gann, pas Fibonacci stricto sensu
            "61.8": round(swing_high - 0.618 * rally, 2),  # "Golden Zone" — ratio Φ inversé
            "78.6": round(swing_high - 0.786 * rally, 2),  # ultime rempart de la trend
        }

        # Label de zone — couvre les cas pathologiques (cours au-dessus du swing
        # high, ou cours sous le swing low → trend déstructurée)
        if   retrace_pct < 0:      label = "nouveau plus haut"
        elif retrace_pct < 23.6:   label = "< Fibo 23.6%"
        elif retrace_pct < 38.2:   label = "zone Fibo 23.6%"
        elif retrace_pct < 50.0:   label = "zone Fibo 38.2%"
        elif retrace_pct < 61.8:   label = "zone Fibo 50%"
        elif retrace_pct < 78.6:   label = "zone Fibo 61.8%"
        elif retrace_pct < 100:    label = "rally annulé (> 78.6%)"
        else:                      label = "trend déstructurée (sous swing low)"

        return {
            "swing_low":     round(swing_low, 2),
            "swing_high":    round(swing_high, 2),
            "rally_pct":     round(rally_pct, 1),
            "retrace_pct":   round(retrace_pct, 1),
            "closest_fibo":  label,
            "fibo_levels":   fibo_levels,
        }
    except Exception:
        return None

# ── UNIVERS ──────────────────────────────────────────────────────────────────
# Phase 4 light (2026-05-23) — élargissement raisonné de 90 → 125 tickers (+35)
# Méthodologie : l'univers initial couvrait déjà l'essentiel des grandes
# capitalisations (pas de bruit structurel). Les 35 ajouts
# comblent 10 trous thématiques précis identifiés (cloud infra, cybersec, REITs,
# Asie directe, etc.), tous validés via yfinance (history 5y + cap > 25B + liquidité OK).
#
# Assurance rotation (juin 2026, +8 → 133 tickers) : on GARDE le tilt tech (pari momentum
# assumé) et on ajoute 8 leaders non-tech ultra-liquides (énergie/industrie/matériaux/staples
# + Nestlé), DORMANTS tant que la tech mène — ils n'entrent dans le top 30 que si leur secteur
# prend le leadership. Tous validés via yfinance (cap > 25B / liquidité / 5 ans).
UNIVERS = [
    # ─── EUROPE ───────────────────────────────────────────────────────────────
    # CAC 40 — 12 valeurs (liquidité + compatibilité modèle momentum)
    "AIR.PA","AI.PA","CAP.PA","CS.PA","DSY.PA","HO.PA",
    "MC.PA","OR.PA","RMS.PA","SAF.PA","SU.PA","TTE.PA",
    # DAX 40 — 10 valeurs (tech/industrie/finance, vieille industrie exclue)
    "ADS.DE","ALV.DE","DB1.DE","FRE.DE","IFX.DE",
    "LIN.DE","MRK.DE","MUV2.DE","SAP.DE","SIE.DE",
    # AEX 25 — 7 valeurs
    "ADYEN.AS","ASM.AS","ASML.AS","HEIA.AS","IMCD.AS","PHIA.AS","RAND.AS",
    # OMX Nordics — 2 valeurs
    "NOVO-B.CO","VWS.CO",
    # Suisse (assurance rotation, comble un gap géo) — 1 valeur : Nestlé
    "NESN.SW",
    # LSE — 4 valeurs
    "REL.L","LSEG.L","AZN.L","ULVR.L",
    # Énergie verte EU (Phase 4 light, +3) — Iberdrola Espagne, Orsted Danemark, RWE Allemagne
    "IBE.MC","ORSTED.CO","RWE.DE",

    # ─── ÉTATS-UNIS (S&P 100 + élargissements Phase 4 light) ───────────────────
    # S&P 100 — 52 valeurs initiales (tech, finance, santé, conso, industrie)
    "AAPL","NVDA","MSFT","GOOGL","AMZN","META","AVGO","TSLA","LLY",
    "V","MA","JPM","UNH","XOM","PG","HD","MRK","ABBV","COST",
    "CRM","NFLX","AMD","ORCL","ACN","TMO","ABT","ISRG","GS",
    "BLK","QCOM","TXN","AMAT","NOW","PANW","INTU","AXP","SPGI",
    "HON","ETN","SYK","VRTX","ADI","REGN","MMC","CI","PLD",
    "ADBE","MCD","NEE","PFE","WMT","AMGN",
    # Cloud infrastructure pure-play (Phase 4 light, +4) — complète les hyperscalers
    "DDOG","SNOW","MDB","NET",
    # Cybersécurité pure-play (Phase 4 light, +3) — PANW déjà présent
    "CRWD","ZS","FTNT",
    # Biotech mid-cap (Phase 4 light, +2) — REGN/VRTX/AMGN déjà présents
    "GILD","BIIB",
    # Finance : brokers + IB + banque régionale (Phase 4 light, +3)
    "SCHW","MS","TFC",
    # REITs (Phase 4 light, +4) — PLD logistique déjà présent
    "EQIX","AMT","O","WELL",
    # Semi-conducteurs équipements US (Phase 4 light, +2) — AMAT/ASML/ASM/IFX déjà présents
    "KLAC","LRCX",
    # Aérospatial/Défense US (Phase 4 light, +3) — AIR.PA/HO.PA/SAF.PA EU déjà présents
    "LMT","RTX","NOC",
    # Luxe US (Phase 4 light, +2)
    "RACE","EL",
    # Énergie solaire US (Phase 4 light, +1) — FSLR seul retenu (volatilité ENPH/SEDG)
    "FSLR",
    # Fintech crypto (Phase 4 light, +1) — seule expo crypto regulated large-cap
    "COIN",
    # Conso discrétionnaire (Phase 4 light, +2)
    "BKNG","NKE",

    # Assurance rotation (juin 2026, +7 US) — leaders non-tech ultra-liquides, dormants tant
    # que la tech mène, prêts si le leadership tourne (énergie / industrie / matériaux / staples).
    "CVX","COP","CAT","GE","DE","SHW","KO",

    # ─── ASIE ──────────────────────────────────────────────────────────────────
    # TSMC suit sa cotation de Taipei (2330.TW) depuis le 08/08/2026 : sur
    # l'ADR, comptes en TWD et cours en USD interdisaient tout PER historique
    # — onze exercices, aucun multiple. SE (Asie du Sud-Est) et SONY restent
    # des ADR, faute d'équivalent local exploitable chez notre fournisseur.
    "2330.TW","SE","SONY",
    # Asie directe via ADR — Chine (Phase 4 light, +3, prudent vs risque géopol)
    "BABA","TCEHY","PDD",
    # Japon via ADR (Phase 4 light, +2) — Toyota + Mitsubishi UFJ
    "TM","MUFG",

    # ─── ÉLARGISSEMENT AOÛT 2026 (+39) ─────────────────────────────────────
    # Ces titres sont entrés dans l'univers pour alimenter des watchlists
    # thématiques (santé, conso, défense, robotique, compounders) qui ne sont
    # plus publiées. Ils RESTENT scorés : ce sont de bons candidats au top 30,
    # et les retirer rétrécirait la watchlist principale sans rien simplifier.
    # Ils ont tous passé la validation Yahoo du 01/08 (historique, devise,
    # secteur, capitalisation).
    "AME","CPRT","CTAS","DHR","EMR","FAST","ITW","PH","ROK","ROP","RSG","TDG","UNP","WM",
    "BSX","MDT","NVS","RHHBY","ZTS",
    "CL","HSY","MDLZ","PEP","PM","AD.AS","DGE.L",
    "AM.PA","BA.L","LDO.MI","RHM.DE","RR.L","SAAB-B.ST",
    "NXPI","STM","TRI",
    "6273.T","6501.T","6861.T","6954.T",
    # PLTR est sorti du thème infra-ia le 01/08 (couche logicielle = pari sur
    # les usages, pas sur l'infrastructure) mais figurait au top 30 : il reste
    # scoré ici comme n'importe quel candidat, sinon il aurait disparu de la
    # watchlist principale par simple effet de bord d'une décision de périmètre.
    "PLTR",

    # ─── EX-WATCHLIST « FINANCIALS » (retirée le 06/08/2026) ───────────────
    # Même décision que pour les watchlists d'août : le thème n'est plus
    # publié mais ses titres restent scorés (candidats au top 30, et le
    # portefeuille détient JPM, V, BLK, DB1.DE, SPGI, LSEG.L, ADYEN.AS —
    # déjà dans l'univers historique). Ne figurent ici que les 16 tickers
    # qui n'existaient qu'à travers le thème.
    "BAC","WFC","HSBA.L","BNP.PA","UBSG.SW",
    "CB","PGR","PYPL","BX","KKR",
    "MCO","MSCI","ICE","CME","NDAQ","FICO",
]

# ── Élargissement thématique (août 2026) ─────────────────────────────────────
# L'univers historique ci-dessus reste la base ; themes.py y ajoute les titres
# nécessaires aux watchlists thématiques. Un ticker déclaré dans un thème est
# automatiquement scoré — c'est ce qui garantit qu'aucun thème ne référence un
# titre absent de l'univers. Les symboles recalés par la validation Yahoo sont
# documentés dans themes.ECARTES_VALIDATION.
# ── HÉRITAGE DE LA CHAÎNE QUANTIQUE (08/08/2026) ──────────────────────────────
# Ces douze titres sont entrés dans l'univers avec la watchlist quantique, qui
# couvrait alors toute la chaîne — des fondeurs aux cryogénistes. Le même jour,
# la watchlist a été resserrée sur les seuls PURE PLAYERS (décision
# propriétaire), et sans cette liste ils sortiraient de l'univers : douze
# sociétés validées contre Yahoo perdraient leur note, et sept fiches déjà
# publiées deviendraient orphelines.
#
# C'est le même choix qu'au retrait du thème « financials » le 06/08 : on retire
# une LISTE, pas des sociétés. Elles restent scorées et candidates au top 30.
UNIVERS += [
    "IBM",            # opérateur du cloud quantique, feuille de route publiée
    "KEYS", "MKSI", "FORM",     # instruments, vide, cryogénie
    "OXIG.L",                   # graveurs des puces supraconductrices
    "GFS", "STMPA.PA", "SOI.PA",  # fonderie et substrats
    "6701.T", "6702.T",         # NEC, Fujitsu
    "6965.T", "6302.T",         # Hamamatsu, Sumitomo Heavy
]

# Même geste pour la watchlist ROBOTIQUE du 08/08/2026, et pour la même raison.
# Ces deux industriels japonais fabriquent réellement des robots et des
# servomoteurs, mais au milieu de climatiseurs et d'équipements automobiles :
# la règle d'entrée du thème (les comptes doivent bouger avec le nombre de
# robots vendus) les écarte de la LISTE. Elle ne dit rien de leur qualité, et
# tous deux dépassent largement le seuil de 25 Md$ du projet après une
# validation sans erreur — les laisser dehors reviendrait à les avoir examinés
# puis perdus. Ils sont donc scorés et candidats au top 30, comme les douze
# titres de la chaîne quantique juste au-dessus.
UNIVERS += [
    "6503.T",                   # Mitsubishi Electric — robots, servos, et le reste
    "6902.T",                   # Denso — équipementier automobile, actionneurs
]

# Troisième fois le même geste, pour la watchlist ESPACE devenue NEWSPACE le
# 12/08/2026 (décision propriétaire). Le mot NewSpace désigne la génération
# d'acteurs apparue au milieu des années 2000, donc PAS les maîtres d'œuvre
# historiques ni les opérateurs de satellites qui les précédaient : quatorze
# titres sont sortis de la LISTE. Huit d'entre eux (LMT, RTX, NOC, BA.L, AIR.PA,
# HO.PA, SAF.PA, LDO.MI) appartiennent à l'univers historique ci-dessus et n'ont
# besoin de rien. Les six autres n'y existaient QUE par le thème : sans cette
# liste, six sociétés validées perdraient leur note et six fiches déjà publiées
# deviendraient orphelines. On retire une liste, pas des sociétés.
UNIVERS += [
    "LHX", "KTOS",              # charges utiles militaires, systèmes sol
    "IRDM", "VSAT",             # opérateurs historiques : IoT, voix de secours, haut débit
    "SESG.PA", "ETL.PA",        # géostationnaires européens — Eutelsat porte OneWeb
]

UNIVERS = sorted(set(UNIVERS) | set(themes.univers_thematique()))

# ── HISTORIQUE PARTIEL ADMIS, TITRE PAR TITRE ────────────────────────────────
# Un titre introduit depuis moins de 200 séances n'a pas de MM200, et la garde
# technique du scoring l'écartait entièrement. Les titres listés ici sont notés
# QUAND MÊME : le critère de tendance (7 points sur 100) est retiré, la note se
# renormalise sur le reste, exactement comme pour une banque sans FCF.
#
# CE QUE ÇA COÛTE, ET IL FAUT LE SAVOIR : la note repose sur moins de mesures,
# et le momentum d'un titre sans MM200 n'est mesuré que par sa position dans un
# canal de régression encore court. Une note haute y est moins vérifiée qu'une
# note haute obtenue sur dix-huit exercices et deux cents séances.
#
# L'ENTRÉE SE PÉRIME TOUTE SEULE : le jour où le titre atteint ses 200 séances,
# la MM200 se calcule, le critère revient, et cette ligne ne sert plus à rien.
# On la retire alors — elle ne fait jamais entrer un titre qui n'y est pas.
HIST_PARTIEL_OK = {
    # Demande du propriétaire (15/08/2026). Plus grosse introduction de la
    # décennie et sujet même de la watchlist NewSpace : l'absence de la société
    # qui a donné sa forme au phénomène coûtait plus à la liste que sept points
    # de momentum non mesurés. Éligible sans dérogation vers avril 2027.
    "SPCX",
}

# ── JUSTIFICATION ─────────────────────────────────────────────────────────────
def generer_justification(nom, score, details, alertes):
    points = []

    # Signal de croisement (priorité haute)
    regime = details.get("cross_regime", "")
    days   = details.get("cross_days_ago", 999)
    vol_c  = details.get("cross_vol_confirmed", False)
    vol_txt = " (volume confirmé)" if vol_c else ""

    if regime == "golden":
        if days <= 10:
            points.append(f"Golden Cross frais ({days}j){vol_txt} — fenêtre signal optimale")
        elif days <= 30:
            points.append(f"Golden Cross récent ({days}j){vol_txt}")
        elif days <= 60:
            points.append(f"Golden Cross confirmé ({days}j)")
    elif regime == "death" and days <= 30:
        points.append(f"⚠ Death Cross récent ({days}j) — signal baissier actif")

    # Signal dynamics — surface la transition du cross quand détectée
    # (cross apparemment baissier en résorption, golden en affaiblissement,
    # rebond mean-reversion sur cross stale, etc.) Priorité haute en visibilité.
    dyn_warn = details.get("signal_dynamics_warning", "")
    if dyn_warn:
        # Forme abrégée pour la justification (le warning complet est dans le breakdown JSON)
        if "résorption" in dyn_warn:
            points.append("⚠ cross en résorption — signal en transition (pas exploitable seul)")
        elif "affaiblissement" in dyn_warn and "post-rally" not in dyn_warn:
            points.append("⚠ cross en affaiblissement — signal en transition (pas exploitable seul)")
        elif "mean-reversion" in dyn_warn:
            points.append("rebond mean-reversion sur cross stale (setup B opportunities)")
        elif "post-rally" in dyn_warn:
            points.append("⚠ affaiblissement post-rally sur cross stale")

    # Régression
    reg_sig = details.get("reg_signal", "")
    reg_z   = details.get("reg_z", 0)
    if reg_sig == "neutre":
        points.append("cours proche de sa droite de régression")
    elif reg_sig == "au-dessus":
        points.append(f"légèrement au-dessus de sa régression (+{reg_z:.1f}σ)")
    elif reg_sig == "surachat":
        points.append(f"prix en surachat régression (+{reg_z:.1f}σ) — prudence")
    elif reg_sig in ("sous tendance", "survente"):
        points.append(f"prix sous sa droite de régression ({reg_z:.1f}σ)")

    # RSI
    if details.get("rsi_ok"):
        points.append("RSI en zone favorable")

    # Valorisation actuelle (timing d'entrée, INFORMATIF — hors score depuis v3)
    # Le wording dépend du mode : en barème inversé (GC frais), val_pts=5 signifie
    # chute profonde purgée, PAS pullback léger.
    val_pts  = details.get("val_pts")
    dd52w    = details.get("drawdown_52w_pct")
    val_mode = details.get("val_pts_mode", "normal")
    fibo    = details.get("fibo") or {}
    fibo_zone = fibo.get("closest_fibo", "")
    if val_mode == "gc_fresh_inverted" and dd52w is not None:
        if val_pts == 5:
            points.append(f"chute purgée ({dd52w:+.1f}% sous le top 52w) + Golden Cross frais — setup mean-reversion premium")
        elif val_pts == 0:
            points.append(f"⚠ collé au top 52w ({dd52w:+.1f}%) malgré le Golden Cross frais — extension à surveiller")
    elif val_pts == 5 and dd52w is not None:
        # Pullback sain — zone d'entrée favorable
        zone_str = f", {fibo_zone}" if fibo_zone and "Fibo" in fibo_zone else ""
        points.append(f"pullback sain {dd52w:+.1f}% sous le top 52w (zone d'entrée favorable{zone_str})")
    elif val_pts == 0 and dd52w is not None and dd52w >= -3:
        # Près du top — risque de chase (la note v4 le paie en continu via la cloche z du bloc momentum)
        points.append(f"⚠ près du top 52w ({dd52w:+.1f}%) — risque de chase")
    elif val_pts == 0 and dd52w is not None and dd52w <= -30:
        # Chute libre
        points.append(f"⚠ {dd52w:+.1f}% sous le top 52w — trend probablement cassée")
    elif val_pts == 3 and dd52w is not None:
        zone_str = f" ({fibo_zone})" if fibo_zone and "Fibo" in fibo_zone else ""
        points.append(f"correction modérée {dd52w:+.1f}% sous le top{zone_str}")

    # Fondamentaux
    rev = details.get("rev_growth", 0)
    if rev > 0.15:
        points.append(f"croissance CA solide ({rev:.0%} a/a)")
    elif rev > 0.05:
        points.append(f"croissance CA modérée ({rev:.0%} a/a)")

    margin = details.get("net_margin", 0)
    if margin > 0.15:
        points.append(f"marges excellentes ({margin:.0%})")
    elif margin > 0:
        points.append("marges positives")

    reco = details.get("reco", 3)
    if reco < 2.0:
        points.append("consensus analystes très favorable")
    elif reco < 2.5:
        points.append("consensus analystes positif")

    if not points:
        return f"Score de {score}/100 — données partielles disponibles."

    justif = f"Score {score}/100 — " + ", ".join(points[:6]) + "."
    if alertes:
        justif += f" ⚠ {alertes[0]}"
    return justif

# Taille de la watchlist : nombre de titres retenus (top N par score) parmi l'univers.
WATCHLIST_SIZE = config.WATCHLIST_SIZE   # source unique : config.py (30)

# Fenêtres de régression (en jours de bourse, 252/an)
_REG_DAYS_TECH     = 10 * 252   # 10 ans pour tech/IA (boom récent biaiserait une fenêtre plus longue)
_REG_DAYS_STD      = 20 * 252   # 20 ans pour les autres secteurs
_REG_DAYS_CYCLICAL = 25 * 252   # 25 ans pour cycliques matures (capture plusieurs cycles)
_TECH_SECTORS      = {"Technology", "Communication Services",
                      "Consumer Cyclical"}  # Amazon, Alphabet, Meta classés ici par yfinance

# Industries cycliques matures : cycles 7-15 ans → fenêtre 10y trop courte (un seul cycle),
# biais massif vers la phase observée. Documenté dans methodology.md section 1.4.
# Exemple : Valeo z 10y = +2,11σ (capture chute 2021-2025) vs z 25y = -1,12σ (vraie pente LT +6%/an).
#
# IMPORTANT v2.0.2 : "Semiconductors" (designers : NVDA, AMD, AVGO, ADI, TXN, QCOM, MU, INTC, TSM)
# RETIRÉ car yfinance ne distingue pas designers AI-secular (NVDA) vs memory cyclique (MU).
# Traiter NVDA comme cyclique 25y est artificiel (NVDA n'existait quasi pas dans son business
# actuel il y a 25 ans). On garde uniquement "Semiconductor Equipment & Materials" (AMAT,
# LRCX, KLAC, ASML) qui ont un cycle capex clairement défini (~7 ans).
# Cas extrêmes (MU, SK Hynix au pic du cycle mémoire) restent attrapés par CHASE z>2,5σ.
_CYCLICAL_INDUSTRIES = {
    # Auto (cycles 10-15 ans)
    "Auto Parts", "Auto Manufacturers", "Auto & Truck Dealerships",
    # Semi EQUIPMENT uniquement (capex cyclique ~7 ans)
    # Designers (NVDA, AMD, AVGO, MU, ...) restent en 10y/20y standard
    "Semiconductor Equipment & Materials",
    # Banques (cycles taux + crédit)
    "Banks - Diversified", "Banks - Regional", "Banks—Diversified", "Banks—Regional",
    # Materials / Energy / Industrials cycliques
    "Steel", "Aluminum", "Copper", "Other Industrial Metals & Mining",
    "Oil & Gas E&P", "Oil & Gas Equipment & Services", "Oil & Gas Refining & Marketing",
    "Oil & Gas Integrated", "Oil & Gas Midstream",
    "Airlines", "Marine Shipping",
    "Building Materials", "Building Products & Equipment",
    "Chemicals", "Specialty Chemicals",
    "Lumber & Wood Production", "Paper & Paper Products",
}

# ── MÉTIERS DE BILAN ─────────────────────────────────────────────────────────
# Les activités dont le BILAN EST L'OUTIL DE PRODUCTION : la dette y est la
# matière première, pas un financement, et le « flux de trésorerie disponible »
# calculé à la manière industrielle n'y mesure rien — il suit les mouvements de
# dépôts et de portefeuille de négociation, pas la capacité bénéficiaire.
#
# POURQUOI UNE LISTE EXPLICITE ET NON « le FCF est absent ». C'est la leçon du
# 06/08 : le drapeau était déduit de l'absence de FCF chez Yahoo, un raccourci
# qui confondait « la métrique n'a pas de sens » et « la donnée manque ». Le
# jour où l'on est allé chercher la donnée dans les états financiers, le
# drapeau s'est éteint pour TOUS les titres, la rampe bancaire du ROE et le
# critère cours/actifs nets sont devenus du code mort, et HSBC s'est retrouvée
# notée 0,7/5 sur un levier qui EST son métier. Un critère de métier se déduit
# du métier, jamais de l'état d'une source de données.
#
# Hors périmètre, à dessein : les réseaux de paiement (Visa, Mastercard), les
# places de marché et agences de notation (SPGI, MSCI, ICE), les gérants
# d'actifs (BLK) et les courtiers d'assurance — tous dégagent un vrai flux de
# trésorerie disponible et se notent comme n'importe quelle entreprise.
_INDUSTRIES_BILAN = {
    "Banks - Diversified", "Banks—Diversified",
    "Banks - Regional", "Banks—Regional",
    "Capital Markets",
    "Mortgage Finance",
    "Insurance - Life", "Insurance—Life",
    "Insurance - Property & Casualty", "Insurance—Property & Casualty",
    "Insurance - Reinsurance", "Insurance—Reinsurance",
    "Insurance - Specialty", "Insurance—Specialty",
    "Insurance - Diversified", "Insurance—Diversified",
    "Financial Conglomerates",
}

# ── SCORING ──────────────────────────────────────────────────────────────────
def score_ticker(ticker, vix=None):
    """Score 0-100 d'un ticker.

    Args:
        ticker: symbole yfinance (ex: 'NVDA', 'ASML.AS')
        vix: niveau VIX actuel — INFORMATIONNEL uniquement depuis v3 (publié dans
             breakdown["vix_value"], aucun multiplier appliqué au score).
             None accepté (appels standalone : tests, scoring ad-hoc).
    """
    try:
        data = yf.Ticker(ticker)
        # Fetch max pour avoir suffisamment d'historique pour la régression long terme
        # auto_adjust=False pour disposer des DEUX bases de cours dans le même
        # appel (aucun coût réseau supplémentaire) :
        #   · « Adj Close » — ajusté des splits ET des dividendes. C'est la
        #     série de RENDEMENT TOTAL : la seule honnête pour une tendance,
        #     un z-score, une moyenne mobile, un RSI. Elle reste `close`.
        #   · « Close » — ajusté des splits SEULEMENT. C'est le cours que le
        #     marché COTAIT réellement à cette date, et c'est celui-là qu'il
        #     faut pour un PER d'époque.
        #
        # POURQUOI CETTE SÉPARATION : le PER historique divisait un cours
        # dividendes-déduits par un BPA publié. L'ajustement rétroactif des
        # dividendes déflate tout le passé — d'autant plus qu'on remonte loin
        # et que le rendement est élevé — donc les multiples d'époque
        # sortaient SYSTÉMATIQUEMENT trop bas, et leur MÉDIANE avec eux. Or
        # cette médiane pilote le critère « histoire » (8 points sur les 25 de
        # la valorisation) : chaque société distributrice se voyait comparée à
        # un passé artificiellement bon marché, donc jugée chère aujourd'hui.
        # Un titre à 3 % de rendement sur quinze ans encaissait ~35 % de
        # sous-estimation sur ses exercices les plus anciens.
        hist = data.history(period="max", auto_adjust=False)
        if len(hist) < 50:
            return None

        # Purge des barres sans cours AVANT tout calcul (même correctif que
        # last_valid_close() côté portfolio/update_prices, incident 3.0.1) :
        # un run pré-ouverture (8h-13h30 UTC) peut recevoir de Yahoo une barre
        # du jour avec Close=NaN pour les places pas encore ouvertes — sans ce
        # dropna, MM21/MM200/RSI deviennent NaN et le titre est écarté à tort
        # (incident du 27/07/2026 : les 94 titres US évincés, watchlist 100% EU).
        # Repli fail-soft : une version de yfinance qui ne rendrait pas
        # « Adj Close » ramène au comportement d'avant (une seule base).
        _col = "Adj Close" if "Adj Close" in getattr(hist, "columns", []) else "Close"
        close  = hist[_col].squeeze().dropna()
        # Un cours nul ou NÉGATIF est toujours un artefact (ajustements Yahoo
        # aberrants sur l'historique lointain : 35 barres négatives sur
        # 000660.KS en 2000, deux zéros sur CS.PA). L'échelle log du front ne
        # peut pas les montrer et un seul point rendait le graphe MAX
        # invisible — écartés à la source, en plus de la défense côté front.
        close  = close[close > 0]
        # Cours COTÉ (splits seuls), aligné sur les mêmes dates et soumis aux
        # mêmes gardes : il ne sert qu'aux PER d'époque.
        brut   = hist["Close"].squeeze().reindex(close.index)
        brut   = brut[brut > 0]
        volume = hist["Volume"].squeeze().reindex(close.index).fillna(0)
        if len(close) < 50:
            return None
        # yfinance retourne les prix UK en pence (GBp) — convertir en GBP
        try:
            info_curr = getattr(data.fast_info, 'currency', '') or ''
        except Exception:
            info_curr = ''
        if info_curr == 'GBp':
            close = close / 100
            brut = brut / 100

        # Indicateurs techniques sur les 2 dernières années (MM21/MM200/RSI/volume)
        close_2y  = close.iloc[-504:]  if len(close)  > 504 else close
        volume_2y = volume.iloc[-504:] if len(volume) > 504 else volume

        prix   = float(close.iloc[-1])
        mm21   = float(close_2y.rolling(21).mean().iloc[-1])
        mm200  = float(close_2y.rolling(200).mean().iloc[-1])
        rsi    = float(RSIIndicator(close=close_2y, window=14).rsi().iloc[-1])
        vol_recent = float(volume_2y.tail(20).mean())   # volume des 20 derniers jours
        vol_annual  = float(volume_2y.mean())            # moyenne sur 2 ans

        # HISTORIQUE PARTIEL AUTORISÉ, TITRE PAR TITRE (décision du propriétaire,
        # 15/08/2026). Un titre récemment introduit n'a pas ses 200 séances : la
        # MM200 sort NaN et la garde ci-dessous l'écartait entièrement. Or la
        # note sait déjà faire : note_v4 RETIRE le critère « tendance » quand
        # `ecart_mm_pct` est absent et renormalise prudemment sur le reste,
        # exactement comme pour une banque sans FCF. Ce n'était donc pas une
        # règle éditoriale mais une garde technique, et elle bloquait plus large
        # que nécessaire.
        #
        # L'OUVERTURE EST NOMMÉE, PAS GÉNÉRALE, et c'est délibéré : lever le
        # plancher pour tous les titres jeunes ferait entrer d'un coup dans
        # l'univers des dizaines d'introductions récentes et changerait toutes
        # les watchlists en silence. Ici chaque titre est inscrit à la main,
        # avec sa raison, et il perd 7 points de momentum sur 100 : sa note est
        # renormalisée, donc comparable, mais elle repose sur moins de mesures.
        # L'entrée se retire d'elle-même quand le titre atteint ses 200 séances.
        _partiel = ticker in HIST_PARTIEL_OK and mm200 != mm200
        if _partiel:
            print(f"  ⚠ {ticker}: {len(close_2y)} barres < 200, MM200 indisponible "
                  f"— critère de tendance retiré, note renormalisée")
            mm200 = None

        # Garde NaN : le garde d'entrée n'exige que 50 barres alors que la MM200 en
        # demande 200 ; entre les deux, rolling() renvoie NaN, qui traverserait
        # float()/round() sans lever et finirait sérialisé dans watchlist.json
        # (token NaN → JSON.parse échoue côté site, incident classe 3.0.1).
        # `mm200` vaut ici soit un flottant valide, soit None (jamais NaN) :
        # None se sérialise en `null`, que le site sait déjà lire.
        _a_verifier = (prix, mm21, rsi, vol_recent, vol_annual) if _partiel else \
                      (prix, mm21, mm200, rsi, vol_recent, vol_annual)
        if any(v != v for v in _a_verifier):
            print(f"  ✗ {ticker}: historique insuffisant pour MM200/RSI ({len(close_2y)} barres), écarté")
            return None

        # ── Croisement MM21/MM200 (2 ans suffisent) — informationnel depuis v4
        cross_info = detect_cross(close_2y, volume_2y)

        info = data.info

        # ── Régression log-linéaire long terme
        # Cycliques matures (auto, semi, banks) : 25 ans pour capturer plusieurs cycles
        # Tech/IA : 10 ans (le boom IA biaiserait une droite sur 20 ans)
        # Autres  : 20 ans, ou tout l'historique disponible si moins
        yf_sector   = info.get("sector", "") or ""
        yf_industry = info.get("industry", "") or ""
        if yf_industry in _CYCLICAL_INDUSTRIES:
            reg_days = _REG_DAYS_CYCLICAL  # 25y pour cycliques (cf Valeo, Micron, banks)
            reg_window_reason = "cyclical_25y"
        elif yf_sector in _TECH_SECTORS:
            reg_days = _REG_DAYS_TECH      # 10y pour tech pure
            reg_window_reason = "tech_10y"
        else:
            reg_days = _REG_DAYS_STD       # 20y par défaut
            reg_window_reason = "standard_20y"
        close_reg   = close.iloc[-reg_days:] if len(close) >= reg_days else close
        regression_z, reg_pente, prix_tendance, reg_sigma = calcul_regression(close_reg)
        # Fallback si NaN (cas observé sur SK Hynix avec fenêtre 25y) : retomber sur fenêtres plus courtes
        if regression_z is None or (isinstance(regression_z, float) and np.isnan(regression_z)):
            for fb_days in (_REG_DAYS_STD, _REG_DAYS_TECH):
                if fb_days < reg_days:
                    close_fb = close.iloc[-fb_days:] if len(close) >= fb_days else close
                    z_fb, p_fb, pt_fb, sg_fb = calcul_regression(close_fb)
                    if z_fb is not None and not (isinstance(z_fb, float) and np.isnan(z_fb)):
                        regression_z, reg_pente = z_fb, p_fb
                        prix_tendance, reg_sigma = pt_fb, sg_fb  # même fenêtre effective que le z publié
                        reg_days  = fb_days
                        close_reg = close_fb   # fenêtre EFFECTIVE — le breakdown publie len(close_reg)
                        reg_window_reason += f"_fallback_{round(fb_days / 252)}y"  # honnêteté : le z publié n'est PAS celui de la fenêtre doctrine
                        break
        # Si toujours NaN après fallbacks, force à 0 pour éviter propagation —
        # et une droite invalide ne peut produire ni prix de tendance ni sigma.
        if regression_z is None or (isinstance(regression_z, float) and np.isnan(regression_z)):
            regression_z  = 0.0
            prix_tendance = None
            reg_sigma     = None
        # reg_pente suit le même contrat : un NaN résiduel serait publié tel quel
        # dans regression_pente_pct et invaliderait le JSON (cf. garde MM200).
        if reg_pente is None or (isinstance(reg_pente, float) and np.isnan(reg_pente)):
            reg_pente = 0.0
        # Sanitize prix_tendance/sigma : exp() peut déborder (inf) et NaN traverserait
        # round() sans lever — allow_nan=False ferait alors échouer tout le run.
        if prix_tendance is not None and not (np.isfinite(prix_tendance) and prix_tendance > 0):
            prix_tendance = None
        if reg_sigma is not None and not np.isfinite(reg_sigma):
            reg_sigma = None
        reg_signal              = reg_signal_label(regression_z)
        reg_zone_saine          = -0.5 <= regression_z <= 1.5

        rev_growth_raw = info.get("revenueGrowth")   # None conservé pour la publication
        margins_raw    = info.get("profitMargins")   # (breakdown : trou → null → « — »)
        rev_growth   = rev_growth_raw or 0
        margins      = margins_raw or 0
        forward_pe   = info.get("forwardPE")             # PER forward (bénéfices attendus)
        trailing_pe  = info.get("trailingPE")            # PER courant (PER courant ≫ forward = bénéfices au creux de cycle)
        market_cap   = info.get("marketCap") or 0
        # LA CAPITALISATION MANQUE PARFOIS, et elle se recalcule. Le résumé du
        # fournisseur ne la porte pas sur cinq fiches (Allianz, Micron, Safran,
        # Siemens, Western Digital) — sans raison apparente, et sans que rien
        # ne le signale : le rendement du flux disponible y était simplement
        # absent. Or une capitalisation est un cours multiplié par un nombre
        # d'actions, tous deux présents, tous deux dans la devise de cotation.
        # Ce n'est pas une estimation, c'est la définition.
        if not market_cap:
            _act = info.get("sharesOutstanding")
            if _act and prix:
                market_cap = prix * _act
        debt_eq_raw  = info.get("debtToEquity")          # garde None pour distinguer net-cash (=0) vs missing
        reco         = info.get("recommendationMean") or 3.5
        roe          = info.get("returnOnEquity")        # ROE — proxy qualité du capital ; None si absent
        # Cours / actifs nets comptables — le multiple de référence des métiers
        # de BILAN, où les fonds propres ont un sens économique réel. Il
        # remplace le rendement du cash dans la note des banques et assureurs
        # (cf. note_v4). Publié par Yahoo pour toutes les places, donc sans
        # l'asymétrie géographique qu'aurait introduite une source US.
        price_to_book = info.get("priceToBook")
        # Un multiple NÉGATIF n'est pas un multiple. Des capitaux propres
        # négatifs (rachats massifs financés par dette : Dell −202, Booking
        # −14,6, MSCI −15,3) donnent un « prix sur actif net » qui n'a aucun
        # sens économique et qui, sur la rampe du critère bancaire, passerait
        # pour la meilleure note possible. Même règle que le PER prévisionnel
        # négatif et que les capitaux propres d'etats_complements : on retire.
        if isinstance(price_to_book, (int, float)) and price_to_book <= 0:
            price_to_book = None

        # Période de réf. des fondamentaux (dernier trimestre publié ; mostRecentQuarter = epoch s).
        # Temporalités Yahoo : rev_growth = trimestriel a/a (MRQ vs même trim. N-1) ;
        # net_margin & fcf_margin = TTM (12 mois glissants).
        _mrq_ts = info.get("mostRecentQuarter")
        try:
            mrq_iso = _dt.fromtimestamp(int(_mrq_ts), tz=_tz.utc).strftime("%Y-%m-%d") if _mrq_ts else None
        except Exception:
            mrq_iso = None

        fh_data    = finnhub_fundamentals(ticker)
        confiance, alertes = valider_fondamentaux(info, fh_data)

        # ── Signaux informationnels ─────────────────────────────────────────
        # Depuis la note v4, le momentum est un BLOC DE LA NOTE (rampes
        # continues dans note_v4.py : écart MM21/MM200, cloche z, cloche RSI).
        # Les sous-points de timing v3 (cross 10, pente 4, volume 3, RSI 2,
        # zone saine 3) et leurs pénalités/bonus (chase, death, décote) ont
        # disparu du calcul — l'audit des 24 archives avait mesuré un IC de
        # timing NÉGATIF (-0,33). Les signaux restent publiés et nourrissent
        # justification, fiches et agent.
        details = {}
        rsi_ok = 35 <= rsi <= 65

        # Valorisation actuelle (5 pts) — drawdown vs plus haut 52 semaines,
        # CONDITIONNÉ AU RÉGIME CROSS depuis test empirique du 23/05/2026 sur
        # 43 145 events Golden Cross frais 2017-2024 (32 tickers).
        #
        # Résultat clé : avec Golden Cross frais (<=30j), la perf forward médiane 12m
        # est MONOTONE CROISSANTE avec la profondeur du drawdown :
        #     top (0 à -3%)             : +16.8%
        #     pullback_sain (-3 à -10%) : +19.9%
        #     correction (-10 à -20%)   : +24.3%
        #     drawdown_modere (-20 à -30%): +44.3%
        #     chute_profonde (>-30%)    : +86.1%  ← PREMIUM
        # → Le barème val_pts est INVERSÉ en présence d'un GC frais (le cross
        #   matérialise la "réinitialisation propre" = Setup A renforcé dans opportunities.md).
        # Sans GC frais, le barème original (chute = risque de continuation) reste valide.
        #
        # Caveat : barème de calibration, à revalider périodiquement. Le pattern
        # "GC frais + chute profonde -> rebond" s'observe sur des cas publics récents
        # mais peut s'inverser en cycle séculaire bear.
        close_52w = close.iloc[-252:] if len(close) >= 252 else close
        high_52w  = float(close_52w.max())
        drawdown_52w_pct = (prix / high_52w - 1) * 100 if high_52w > 0 else 0
        gc_fresh = (cross_info.get("regime") == "golden"
                    and cross_info.get("days_since_cross") is not None
                    and cross_info.get("days_since_cross") <= 30)
        if gc_fresh:
            # GC frais → barème INVERSÉ (test empirique 43k events 2017-2024)
            if   drawdown_52w_pct >= -3:                      val_pts = 0  # top = chase de rally
            elif drawdown_52w_pct >= -10:                     val_pts = 2  # pullback sain (correct mais pas premium)
            elif drawdown_52w_pct >= -20:                     val_pts = 3  # correction
            elif drawdown_52w_pct >= -30:                     val_pts = 4  # drawdown modéré
            else:                                              val_pts = 5  # chute profonde + GC frais = PREMIUM
            val_pts_mode = "gc_fresh_inverted"
        else:
            # Pas de GC frais → barème original (chute = risque)
            if   drawdown_52w_pct >= -3:                      val_pts = 0   # proche du top → chase
            elif -10 <= drawdown_52w_pct < -3:                val_pts = 5   # pullback sain → zone idéale
            elif -20 <= drawdown_52w_pct < -10:               val_pts = 3   # correction modérée
            elif -30 <= drawdown_52w_pct < -20:               val_pts = 1   # momentum cassé
            else:                                              val_pts = 0   # chute libre
            val_pts_mode = "normal"

        # ── Retracement Fibonacci (annotation informationnelle, hors scoring)
        fibo = fibonacci_retracement(close, lookback=252)

        details["cross_regime"]        = cross_info["regime"]
        details["cross_days_ago"]      = cross_info["days_since_cross"]
        details["cross_vol_confirmed"] = cross_info["volume_confirmed"]
        details["cross_slope_mm21"]    = cross_info["slope_mm21_pct"]
        details["cross_spread"]        = cross_info["spread_pct"]
        details["rsi_ok"]              = rsi_ok
        details["rsi"]                 = round(rsi, 1)
        details["reg_z"]               = regression_z
        details["reg_signal"]          = reg_signal
        # v2.0 — valorisation actuelle (timing d'entrée) + retracement Fibonacci
        details["val_pts"]             = val_pts
        details["val_pts_mode"]        = val_pts_mode   # le wording de la justification en dépend (barème inversé GC frais)
        details["drawdown_52w_pct"]    = drawdown_52w_pct
        details["fibo"]                = fibo

        # Détection signal en transition (4 cas, cf v1.10) — disponible pour
        # generer_justification et raison_sortie. Recomputed dans le breakdown
        # plus bas pour cohérence (pas de coût significatif, lisibilité préservée).
        _ct_d = cross_info["cross_type"]
        _sl_d = cross_info["slope_mm21_pct"]
        _sp_d = cross_info["spread_pct"]
        _dy_d = cross_info["days_since_cross"]
        _warn_d = ""
        if _ct_d == "death" and _sl_d > 0 and -3 < _sp_d < 0 and _dy_d is not None and _dy_d < 90:
            _warn_d = "Death Cross en cours de résorption — pente MM21 positive, spread tendu, signal possiblement en transition"
        elif _ct_d == "golden" and _sl_d < 0 and 0 < _sp_d < 3 and _dy_d is not None and _dy_d < 90:
            _warn_d = "Golden Cross en cours d'affaiblissement — pente MM21 négative, signal possiblement en transition"
        elif _ct_d == "death" and _sl_d > 3 and _sp_d < -5 and _dy_d is not None and _dy_d > 90:
            _warn_d = "Rebond mean-reversion en cours sur cross stale — pente MM21 fortement positive, cours encore largement sous MM200"
        elif _ct_d == "golden" and _sl_d < -3 and _sp_d > 5 and _dy_d is not None and _dy_d > 90:
            _warn_d = "Affaiblissement post-rally sur cross stale — pente MM21 fortement négative malgré cours largement au-dessus de MM200"
        details["signal_dynamics_warning"] = _warn_d

        # Bruts AVANT tout `or` : « absent » et « zéro » sont deux informations
        # différentes. Le score reste prudent (0 pt sur un trou), mais la
        # PUBLICATION ne transforme plus un trou en mesure « 0,0 % » — la
        # relecture du 06/08 a compté 21 financières affichant une fausse
        # marge FCF nulle (Yahoo ne publie pas de FCF pour les banques).
        fcf_raw       = info.get("freeCashflow")
        total_rev_raw = info.get("totalRevenue")

        # ── Repli sur les ÉTATS FINANCIERS quand le résumé Yahoo est muet ──
        # Le résumé ne renseigne ni FCF, ni dette/capitaux propres, ni ROE pour
        # une large part des titres non américains. Plutôt que de retirer les
        # critères correspondants — ce qui revient à noter sur une donnée qu'on
        # n'est pas allé chercher — on les recalcule depuis le tableau de flux
        # et le bilan, déjà téléchargés pour la section « Chiffres publiés ».
        # Universel (toutes places, toutes devises), aucun appel de plus.
        # PROVENANCE : `fonda_source` dit lesquels ont été reconstruits.
        # Un métier de bilan ne reçoit JAMAIS de flux disponible reconstitué :
        # son flux d'exploitation suit les dépôts et le portefeuille de
        # négociation, pas la capacité bénéficiaire. Le calculer produirait un
        # « 113 % de conversion du bénéfice en cash » chez HSBC — un chiffre
        # flatteur et vide de sens. Les capitaux propres et la dette, eux, se
        # lisent normalement.
        _metier_bilan = yf_industry in _INDUSTRIES_BILAN
        fonda_source = []
        # Critères de substitution des métiers de bilan : le rendement des
        # actifs remplace la conversion en cash, le levier actifs/fonds
        # propres remplace dette/CP (cf. note_v4). Les deux se lisent au
        # bilan — toujours téléchargé pour ces titres.
        roa_pct = levier_actifs = None
        if _metier_bilan:
            try:
                _ecb = etats_complements(None, data.balance_sheet)
                _cp_b, _actifs = _ecb.get("capitaux_propres"), _ecb.get("actifs")
                _ni = info.get("netIncomeToCommon")
                if _actifs and _ni is not None and _ni == _ni:
                    roa_pct = _ni / _actifs * 100
                if _actifs and _cp_b:
                    levier_actifs = _actifs / _cp_b
            except Exception as e:
                print(f"  ⚠️  {ticker}: bilan illisible pour ROA/levier ({type(e).__name__})")
        # Les états financiers sont lus SYSTÉMATIQUEMENT (et non plus en
        # dernier recours) : ils sont déjà téléchargés pour la section
        # « Chiffres publiés », et ils portent la seule version VÉRIFIABLE du
        # flux disponible. Voir juste en dessous pourquoi celle de Yahoo ne
        # convient pas.
        try:
            _ec = etats_complements(data.cashflow, data.balance_sheet,
                                    data.income_stmt)
        except Exception as e:
            print(f"  ⚠️  {ticker}: états financiers illisibles ({type(e).__name__})")
            _ec = {}
        _cp = _ec.get("capitaux_propres")
        # LE FLUX DISPONIBLE VIENT DES COMPTES, PAS DU RÉSUMÉ.
        #
        # `info["freeCashflow"]` de Yahoo ne mesure pas ce que notre phrase
        # annonce (« sur 100 € de bénéfice, X € finissent en cash réel »). Le
        # relevé du 07/08 sur les fiches publiées est sans appel : Microsoft
        # 4,9 % de marge de flux disponible, Alphabet 5,1 %, Meta 9,4 %,
        # Amazon 0,4 % — aucun de ces chiffres n'est une marge de flux
        # disponible au sens usuel (exploitation − investissements
        # industriels), et le critère « conversion » mettait 0 sur 7 aux
        # meilleurs générateurs de trésorerie de l'univers. La définition est
        # donc reprise en main : elle est CALCULÉE, pas récupérée.
        _fcf_comptes = (_ec.get("fcf") is not None and not _metier_bilan)
        if _fcf_comptes:
            fonda_source.append("fcf:comptes" if fcf_raw is not None else "fcf")
            fcf_raw = _ec["fcf"]
        if debt_eq_raw is None and _cp and _ec.get("dette") is not None:
            debt_eq_raw = _ec["dette"] / _cp * 100; fonda_source.append("dette")
        # ROE = résultat net du dernier exercice publié ÷ capitaux propres.
        # Les deux sont en devise COMPTABLE : le ratio est homogène.
        if roe is None and _cp:
            _ni = info.get("netIncomeToCommon")
            if _ni is not None and _ni == _ni:
                roe = _ni / _cp; fonda_source.append("roe")

        fcf        = fcf_raw or 0
        # Le DÉNOMINATEUR suit le numérateur. Un flux disponible lu dans les
        # comptes se divise par le chiffre d'affaires DU MÊME EXERCICE, pas par
        # le douze-mois-glissant du résumé : sinon le ratio compare deux
        # périodes et deux documents. Repli sur `totalRevenue` seulement quand
        # le flux vient lui aussi du résumé.
        # Bug corrigé (latent) : `totalRevenue or 1` faisait de fcf/1 une
        # « marge » astronomique quand le CA manquait — la donnée absente
        # OFFRAIT les 8 points au lieu d'en priver.
        _rev_fcf = _ec.get("ca") if _fcf_comptes else total_rev_raw
        fcf_margin = (fcf / _rev_fcf) if (fcf_raw is not None and _rev_fcf) else 0
        # CONVERSION DU BÉNÉFICE EN CASH — calculée ici, et non plus déduite
        # dans note_v4 du quotient de deux marges glissantes de provenances
        # différentes. Numérateur et dénominateur sortent du même exercice, du
        # même document et de la même devise : c'est la seule façon d'écrire
        # « sur 100 € de bénéfice, X € finissent en cash » sans mentir.
        conversion_pct = None
        if _fcf_comptes and _ec.get("rn") and _ec["rn"] > 0:
            conversion_pct = fcf_raw / _ec["rn"] * 100
        # Rendement du FCF : le FCF est publié en devise COMPTABLE, la
        # capitalisation en devise de COTATION. Quand elles diffèrent (ADR :
        # TSM cotait un « FCF yield » de 34 % — TWD divisés par des USD), le
        # ratio était un non-sens et on publiait null.
        #
        # LE REFUS ÉTAIT BON, LA CONCLUSION TROP COURTE — exactement comme pour
        # le PER historique le 08/08. Ce qui manquait n'était pas une raison de
        # s'abstenir, c'était le TAUX. Une capitalisation est un montant à un
        # instant : la convertir ne demande aucune convention, contrairement à
        # un flux annuel qu'il faudrait convertir à un taux moyen. Sept fiches
        # (ABB, ASE, Cameco, Ferrari, Tencent, UBTech, Vestas) retrouvent ainsi
        # leur rendement du flux disponible. Sans taux — paire introuvable,
        # réseau en panne — on retombe sur le trou assumé, jamais sur un chiffre
        # calculé avec un taux inventé.
        _meme_devise = (((info.get("financialCurrency") or "") ==
                         (info.get("currency") or ""))
                        if info.get("financialCurrency") else True)
        fcf_yield = None
        if fcf_raw is not None and market_cap:
            if _meme_devise:
                fcf_yield = fcf / market_cap * 100
            else:
                try:
                    _tx = taux_historique(info.get("currency") or "",
                                          info.get("financialCurrency") or "")
                    _r = _tx(date.today().isoformat()) if _tx else None
                    if _r and _r > 0:
                        fcf_yield = fcf / (market_cap * _r) * 100
                except Exception:
                    fcf_yield = None

        details["rev_growth"] = rev_growth
        details["net_margin"] = margins
        details["reco"]       = reco

        # ── Décote vs tendance + objectif analystes (informationnels, hors scoring) ──
        # decote_pct : POSITIF = prix sous la droite de régression (décote), NÉGATIF = surcote.
        decote_pct = _decote_pct(prix, prix_tendance)

        # targetMeanPrice : yfinance peut renvoyer NaN (float) — le laisser passer
        # invaliderait watchlist.json (allow_nan=False). Piège pence : les targets UK
        # arrivent en GBp comme les cours → même conversion /100 que close (famille ×100).
        _tgt = info.get("targetMeanPrice")
        try:
            _tgt = float(_tgt) if _tgt is not None else None
        except (TypeError, ValueError):
            _tgt = None
        if _tgt is not None and not (np.isfinite(_tgt) and _tgt > 0):
            _tgt = None
        if _tgt is not None and info_curr == 'GBp':
            _tgt = _tgt / 100
        target_mean_price = round(_tgt, 2) if _tgt is not None else None
        target_upside_pct = round((_tgt / prix - 1) * 100, 1) if (_tgt is not None and prix > 0) else None
        _n_ana = info.get("numberOfAnalystOpinions")
        try:
            # NaN != NaN → écarte les NaN float avant int()
            target_analysts = int(_n_ana) if (_n_ana is not None and _n_ana == _n_ana) else None
        except (TypeError, ValueError):
            target_analysts = None

        exchange = info.get("exchange") or ""   # `or` : la clé peut exister avec None
        ex_up    = exchange.upper()
        MARKET_BADGE = {
            # Zone euro + UE ("GER" = code Yahoo effectif pour Xetra, cf. SAP.DE)
            "PAR":"EU","EPA":"EU","AMS":"EU","FRA":"EU","XETRA":"EU","GER":"EU",
            "ETR":"EU","AEB":"EU","MIL":"EU","BIT":"EU","MCE":"EU",
            "BME":"EU","HEL":"EU","CPH":"EU","OMX":"EU","WSE":"EU",
            "VIE":"EU","ATH":"EU","LIS":"EU","OSL":"EU",
            # UK (post-Brexit)
            "LSE":"GB","IOB":"GB",
            # Suisse
            "EBS":"CH","SWX":"CH",
            # Canada
            "TSX":"CA","CVE":"CA","TOR":"CA",
            # Japon
            "TYO":"JP","TSE":"JP","OSA":"JP",
            # Hong Kong
            "HKG":"HK","HKSE":"HK",
            # Australie
            "ASX":"AU",
            # Corée
            "KSC":"KR","KOE":"KR",
            # Inde
            "BSE":"IN","NSI":"IN",
            # Brésil
            "SAO":"BR",
            # US (détection par sous-chaîne dans market, géré frontend)
        }
        badge = next((v for k, v in MARKET_BADGE.items() if k in ex_up), None)

        sector_map = {
            "Technology": "Technologie", "Healthcare": "Santé",
            "Industrials": "Industrie", "Financial Services": "Finance",
            "Consumer Cyclical": "Conso. cycl.", "Consumer Defensive": "Conso. staples",
            "Energy": "Énergie", "Basic Materials": "Matériaux",
            "Communication Services": "Médias & IA", "Real Estate": "Immobilier",
            "Utilities": "Services pub.",
        }
        sector_fr = sector_map.get(yf_sector, yf_sector[:14] if yf_sector else "—")

        # Détection d'un signal en transition (cross historique mais dynamique inverse)
        _ct      = cross_info["cross_type"]
        _slope   = cross_info["slope_mm21_pct"]
        _spread  = cross_info["spread_pct"]
        _days    = cross_info["days_since_cross"]
        _signal_warning = ""
        if _ct == "death" and _slope > 0 and -3 < _spread < 0 and _days is not None and _days < 90:
            _signal_warning = "Death Cross en cours de résorption — pente MM21 positive, spread tendu, signal possiblement en transition"
        elif _ct == "golden" and _slope < 0 and 0 < _spread < 3 and _days is not None and _days < 90:
            _signal_warning = "Golden Cross en cours d'affaiblissement — pente MM21 négative, signal possiblement en transition"
        elif _ct == "death" and _slope > 3 and _spread < -5 and _days is not None and _days > 90:
            _signal_warning = "Rebond mean-reversion en cours sur cross stale — pente MM21 fortement positive, cours encore largement sous MM200 (setup B opportunities.md)"
        elif _ct == "golden" and _slope < -3 and _spread > 5 and _days is not None and _days > 90:
            _signal_warning = "Affaiblissement post-rally sur cross stale — pente MM21 fortement négative malgré cours largement au-dessus de MM200"

        breakdown = {
            # La note v4 (breakdown["note"]) est ajoutée après le bloc fonda,
            # plus bas : total /100, blocs Q/C/V/M, 16 critères phrasés,
            # motifs de retrait, couverture. Les anciens agrégats v3
            # (qualite/valorisation/timing/analystes, sous-points, pénalités)
            # ont disparu avec le scoring v3.
            "vix_value":             vix,
            # Croisement MM21/MM200 — informationnel (hors note depuis v4)
            "cross_regime":          cross_info["regime"],
            "cross_type":            cross_info["cross_type"],
            "cross_days_ago":        cross_info["days_since_cross"],
            "cross_spread_pct":      cross_info["spread_pct"],
            "cross_slope_mm21_pct":  cross_info["slope_mm21_pct"],
            "cross_volume_confirmed":cross_info["volume_confirmed"],
            "signal_dynamics_warning": _signal_warning,
            "val_pts":               val_pts,       # lu par l'agent (timing d'entrée) et la justification
            "val_pts_mode":          val_pts_mode,  # "gc_fresh_inverted" si GC frais (barème inversé), "normal" sinon
            "drawdown_52w_pct":      round(drawdown_52w_pct, 1),
            "high_52w":              round(high_52w, 2),
            # Retracement Fibonacci — annotation informationnelle (hors scoring)
            "fibo":                  fibo,  # dict ou None si pas de rally identifiable
            # Indicateurs techniques
            "rsi":                   round(rsi, 1),
            "mm21":                  round(mm21, 2),
            # None quand l'historique n'atteint pas 200 séances (HIST_PARTIEL_OK) :
            # `null` dans le JSON, jamais NaN, et la fiche affiche « — ».
            "mm200":                 round(mm200, 2) if mm200 is not None else None,
            # Régression
            "regression_z":          regression_z,
            "regression_signal":     reg_signal,
            "regression_pente_pct":  reg_pente,
            "regression_sigma":      round(reg_sigma, 4) if reg_sigma is not None else None,
            "prix_tendance":         round(prix_tendance, 2) if prix_tendance is not None else None,  # devise native (GBp déjà → GBP)
            "decote_pct":            decote_pct,   # POSITIF = décote (prix sous tendance), NÉGATIF = surcote
            # Fenêtre EFFECTIVE de la régression (après éventuel fallback NaN) —
            # avant, on republiait la fenêtre doctrine même quand le z venait d'un fallback
            "regression_window_years":  round(len(close_reg) / 252),
            "regression_window_reason": reg_window_reason,
            # Cours et devise natifs — nécessaires aux vues thématiques, qui
            # affichent des titres hors top 30 (donc absents de watchlist.json).
            # GBp est déjà converti en GBP plus haut : la devise publiée ici est
            # celle dans laquelle `prix` est réellement exprimé.
            "prix":                  round(prix, 2),
            "devise":                "GBP" if info_curr == "GBp" else (info_curr or ""),
            # Raison sociale NON tronquée — le champ "name" du résultat est
            # coupé à 22 caractères pour les listes ; la fiche, elle, affiche
            # le nom complet (les listes du site utilisent un nom d'usage).
            # Nom d'usage quand les deux formes de Yahoo échouent (themes.NOMS_AFFICHES).
            "nom_complet":           themes.NOMS_AFFICHES.get(
                ticker, info.get("longName") or info.get("shortName") or ticker),
            # Fondamentaux
            # Trou de donnée → null → « — » au front. Un 0.0 publié est une
            # MESURE (croissance nulle, marge nulle), plus jamais un défaut.
            "rev_growth_pct":        round(rev_growth * 100, 1) if rev_growth_raw is not None else None,   # trimestriel, glissement annuel (MRQ vs même trim. N-1)
            "net_margin_pct":        round(margins * 100, 1) if margins_raw is not None else None,         # TTM (12 mois glissants)
            "fcf_margin_pct":        round(fcf_margin * 100, 1) if (fcf_raw is not None and _rev_fcf) else None,  # exercice publié (ou TTM en repli)
            "mrq":                   mrq_iso,                      # date du dernier trimestre publié — réf. période fondamentaux
            # Valorisation (alimente la note v4 et la prose éditoriale)
            "forward_pe":            round(forward_pe, 1) if forward_pe else None,
            "trailing_pe":           round(trailing_pe, 1) if trailing_pe else None,
            "fcf_yield_pct":         round(fcf_yield, 2) if fcf_yield is not None else None,
            # ROE et dette/CP : publiés depuis la v4 (ils vivaient dans le
            # calcul sans jamais être montrés — les phrases de la note les citent).
            "roe_pct":               round(roe * 100, 1) if isinstance(roe, (int, float)) and roe == roe else None,
            "debt_eq_pct":           round(debt_eq_raw) if isinstance(debt_eq_raw, (int, float)) and debt_eq_raw == debt_eq_raw else None,
            "price_to_book":         round(price_to_book, 2) if isinstance(price_to_book, (int, float)) and price_to_book == price_to_book else None,
            # Champs reconstruits depuis les états financiers faute de résumé
            # Yahoo — la provenance voyage avec la donnée, comme pour EDGAR.
            "fonda_source":          fonda_source or None,
            # Objectif de cours analystes (informationnel)
            "target_mean_price":     target_mean_price,
            "target_upside_pct":     target_upside_pct,
            "target_analysts":       target_analysts,
            "confiance":             round(confiance, 2),   # validation croisée Yahoo/Finnhub — informationnel depuis v4 (ne multiplie plus la note)
            "sources":               ["Yahoo Finance"] + (["Finnhub"] if fh_data else []),
        }

        nom = themes.NOMS_AFFICHES.get(
            ticker, info.get("shortName") or info.get("longName") or ticker)

        # ── Payload graphique (charts/) — fail-soft : un graphe raté ne doit
        # JAMAIS faire échouer le scoring du ticker (le try englobant retournerait None).
        try:
            chart = {
                "points": _sample_series(close),
                "mm21":   _sample_series(close.rolling(21).mean().dropna()),
                "mm200":  _sample_series(close.rolling(200).mean().dropna()),
                "t_win0": _mois(close_reg.index[0]),   # début de la fenêtre de régression effective
                "t_last": _mois(close.index[-1]),
            }
        except Exception as e:
            print(f"  ⚠️  {ticker}: payload graphique en échec ({type(e).__name__}) — graphe omis")
            chart = None

        # ── Chiffres publiés (historique CA/EBITDA/RN) — même contrat fail-soft :
        # deux requêtes Yahoo de plus par titre, jamais bloquantes pour le score.
        fonda = None
        if chart is not None:
            try:
                fonda = extraire_fondamentaux(
                    data.income_stmt, data.quarterly_income_stmt,
                    info.get("financialCurrency") or info.get("currency"))
            except Exception as e:
                print(f"  ⚠️  {ticker}: chiffres publiés en échec ({type(e).__name__}) — omis")
                fonda = None
            if fonda:
                # Les splits servent DEUX fois et sont donc lus une seule fois,
                # ici : ramener les BPA d'EDGAR dans la base d'actions actuelle,
                # et écarter du calcul des PER les BPA de la fenêtre Yahoo qui
                # vivent encore dans la base de leur époque.
                try:
                    spl = [(str(ts.date()), float(v))
                           for ts, v in data.splits.items() if v and v > 0]
                except Exception:
                    spl = []
                # Historique officiel SEC : étend la fenêtre Yahoo
                # (~4 exercices, ~5 trimestres) à dix ans et plus, AVANT le
                # calcul des PER pour que les exercices ajoutés reçoivent le
                # leur. Extend-only (jamais d'écrasement Yahoo), provenance
                # src:"edgar" par entrée. Depuis le chantier « historique
                # profond » (06/08), les DÉPOSANTS ÉTRANGERS (20-F, IFRS)
                # sont couverts aussi, dans leur devise comptable — ASML,
                # SAP, TotalEnergies, Sony, Pinduoduo… La gate n'est plus
                # « US en USD » mais « connu du greffe » (edgar.eligible).
                if edgar.eligible(ticker):
                    try:
                        avant = (len(fonda["an"]), len(fonda["tr"]))
                        ed = edgar.chiffres(
                            ticker,
                            devise=(info.get("financialCurrency")
                                    or info.get("currency") or "USD"))
                        if ed:
                            # BPA déposés à l'époque → base d'actions actuelle
                            # (sinon les PER pré-splits sortent absurdes).
                            edgar.ajuster_eps_splits(ed, spl,
                                                     info.get("sharesOutstanding"))
                            edgar.completer_fonda(fonda, ed)
                        gagne = (len(fonda["an"]) - avant[0], len(fonda["tr"]) - avant[1])
                        if any(gagne):
                            print(f"   EDGAR {ticker}: +{gagne[0]} exercices, +{gagne[1]} trimestres")
                    except Exception as e:
                        print(f"  ⚠️  {ticker}: EDGAR en échec ({type(e).__name__}) — fenêtre Yahoo seule")
                # Apport vérifié (non-déposants SEC) — mêmes gardes que
                # l'apport EDGAR, via completer_fonda : extend-only,
                # dédoublonnage ±7 j, garde d'échelle vs la fenêtre Yahoo.
                try:
                    ap = charger_apport(ticker, fonda.get("devise"))
                    if ap:
                        avant_a = len(fonda["an"])
                        edgar.completer_fonda(fonda, ap)
                        if len(fonda["an"]) > avant_a:
                            print(f"   Apport {ticker}: +{len(fonda['an']) - avant_a} exercices (source au fichier)")
                except Exception as e:
                    print(f"  ⚠️  {ticker}: apport en échec ({type(e).__name__})")
                # PER par exercice + deux exercices à venir. Fail-soft aussi.
                try:
                    # Cours COTÉ à l'époque (`brut`, splits seuls), jamais la
                    # série de rendement total : voir per_historique().
                    def prix_fin(iso):
                        try:
                            avant = brut[brut.index <= pd.Timestamp(iso, tz=brut.index.tz)]
                            return float(avant.iloc[-1]) if len(avant) else None
                        except Exception:
                            return None
                    _d_compta = info.get("financialCurrency") or ""
                    _d_cote = info.get("currency") or ""
                    meme_devise = (_d_compta == _d_cote)
                    # Cotation → comptes : c'est le COURS qu'on ramène dans la
                    # devise du bénéfice, jamais l'inverse (cf. taux_historique).
                    _fx = None if meme_devise else taux_historique(_d_cote, _d_compta)
                    # LES ESTIMATIONS SE LISENT AVANT LES MULTIPLES, parce que
                    # c'est leur colonne `currency` — la seule déclaration de
                    # devise de toute la source — qui dit comment lire les deux.
                    est = None
                    _d_est = None
                    _bpa_an_dernier = None
                    try:
                        ee = data.earnings_estimate
                        if ee is not None and "avg" in getattr(ee, "columns", []):
                            est = {k: (float(ee.loc[k, "avg"]) if k in ee.index
                                       and ee.loc[k, "avg"] == ee.loc[k, "avg"] else None)
                                   for k in ("0y", "+1y")}
                            # LA COLONNE QU'ON JETAIT. Elle existe depuis
                            # toujours et nous avons passé deux jours à
                            # DEVINER ce qu'elle déclare (cf. per_previsionnel).
                            if "currency" in getattr(ee, "columns", []) and "0y" in ee.index:
                                _v = ee.loc["0y", "currency"]
                                _d_est = str(_v) if _v == _v and _v else None
                            # Bénéfice du dernier exercice clos, PAR TITRE COTÉ :
                            # l'autre moitié de la mesure du rapport d'ADR.
                            if "yearAgoEps" in getattr(ee, "columns", []) and "0y" in ee.index:
                                _v = ee.loc["0y", "yearAgoEps"]
                                _bpa_an_dernier = float(_v) if _v == _v else None
                    except Exception:
                        est = None
                    _eps_pub = next((e["eps"] for e in reversed(fonda["an"])
                                     if (e.get("eps") or 0) > 0), None)
                    # LE CERTIFICAT N'EST PAS L'ACTION. Mesuré, jamais supposé ;
                    # vaut 1 pour une action ordinaire, None quand la mesure ne
                    # tombe sur aucun rapport usuel — auquel cas on ne divise pas.
                    _rapport = None
                    if not meme_devise:
                        _t_dernier = _fx(fonda["an"][-1]["fin"]) if (_fx and fonda["an"]) else None
                        _rapport = rapport_adr(_bpa_an_dernier, _eps_pub, _t_dernier,
                                               _d_est, _d_cote)
                    # Le BPA manquant se reconstitue AVANT les multiples, et
                    # seulement là où la base d'actions est stable — sinon le
                    # trou reste (cf. completer_eps). La marque est portée par
                    # l'EXERCICE, pas par le bloc : un champ de plus au niveau
                    # de `fonda` serait un champ de plus à ne pas oublier dans
                    # fusionner_fonda, et c'est exactement ainsi que `proj` a
                    # disparu de 96 fiches le 07/08.
                    completer_eps(fonda["an"])
                    per_historique(fonda["an"], prix_fin, meme_devise,
                                   info.get("sharesOutstanding"), _fx, _rapport)
                    # LA CONVERSION SE DIT. Un multiple obtenu en passant par un
                    # taux de change n'est pas du même grain qu'un quotient
                    # direct : la société publie ses propres comparatifs à des
                    # taux qui ne sont pas les nôtres. La fiche l'affiche donc,
                    # plutôt que de laisser croire à une mesure sans couture.
                    if _fx and any(e.get("per") is not None for e in fonda["an"]):
                        fonda["per_converti"] = {"de": _d_cote, "vers": _d_compta}
                        if _rapport and _rapport != 1:
                            fonda["per_converti"]["rapport"] = _rapport
                    dernier = fonda["an"][-1]["fin"] if fonda["an"] else None
                    # Le taux est pris à la date du dernier exercice clos, comme
                    # pour l'historique — le cours, lui, est celui du jour, et
                    # l'écart de quelques mois entre les deux est sans effet sur
                    # un multiple dont l'enjeu est un facteur 1,08 à 31.
                    prev = per_previsionnel(float(close.iloc[-1]), est, dernier,
                                            _fx, _eps_pub, _d_est, _d_cote, _d_compta)
                    # L'ABSENCE SE DIT — MAIS SEULEMENT QUAND C'EST LA DEVISE
                    # QUI L'A CAUSÉE. Le drapeau était posé dès que le change
                    # entrait en jeu et que rien ne sortait, y compris sur une
                    # société DÉFICITAIRE, qui n'a pas de PER prévisionnel pour
                    # une raison qui n'a rien à voir : UBTech portait ainsi une
                    # mention d'abstention sur devise alors que son bénéfice
                    # estimé est négatif. Un motif faux vaut moins qu'un silence.
                    # … ET SEULEMENT QUAND LA SOURCE S'EST TUE. Le run du 09/08
                    # au soir a montré la seconde moitié du problème : Tencent a
                    # perdu son multiple parce que la PAIRE DE CHANGE n'a rien
                    # rendu ce jour-là, et la fiche a expliqué au lecteur que
                    # « notre source n'a pas déclaré la monnaie » — ce qui est
                    # faux, elle l'a déclarée (CNY). Une panne de taux est un
                    # accident de run, pas une position éditoriale : on ne dit
                    # rien, et le repli de fusionner_fonda conserve alors le
                    # multiple de la veille, dont l'étiquette d'exercice rend
                    # tout vieillissement visible. C'est exactement ce pour quoi
                    # ce repli avait été écrit.
                    if _fx and not prev and not _d_est and any(
                            (est or {}).get(k) and (est or {}).get(k) > 0
                            for k in ("0y", "+1y")):
                        fonda["pe_prev_indecis"] = True
                    if prev:
                        fonda["pe_prev"] = prev
                    # Trajectoire attendue jusqu'à 2030 : consensus analystes
                    # sur deux exercices, prolongation à croissance
                    # décroissante au-delà. Hors note, purement informationnel.
                    est_ca = None
                    solidite = None
                    try:
                        re_ = data.revenue_estimate
                        if re_ is not None and "avg" in getattr(re_, "columns", []):
                            est_ca = {k: (float(re_.loc[k, "avg"]) / 1e6
                                          if k in re_.index
                                          and re_.loc[k, "avg"] == re_.loc[k, "avg"] else None)
                                      for k in ("0y", "+1y")}
                            # SUR QUOI REPOSE LE CONSENSUS. Relevé par la sonde
                            # du 07/08 : ces tables portent aussi le NOMBRE
                            # D'ANALYSTES et la fourchette basse/haute, que nous
                            # n'avions jamais lus. L'écart est considérable —
                            # 50 analystes sur Alphabet, DEUX sur Constellation
                            # Energy ; une fourchette de ±1 % sur Booking, ±16 %
                            # sur Nebius. Publier une trajectoire sans dire sur
                            # quoi elle repose donne la même autorité apparente
                            # aux deux. Les valeurs arrivent parfois en CHAÎNES
                            # (le CA est sérialisé en texte, pas le BPA), d'où
                            # la conversion défensive.
                            solidite = _solidite_consensus(re_)
                    except Exception:
                        est_ca = None
                        solidite = None
                    # LE BPA ESTIMÉ SE COMPARE-T-IL À LA SÉRIE PUBLIÉE ? La
                    # source le déclare ; à défaut de déclaration on retombe
                    # sur la seule chose qu'on sache alors — comptes et
                    # cotation dans la même monnaie.
                    _bpa_comparable = (_d_est == _d_compta) if _d_est else meme_devise
                    proj = projections(fonda["an"], est, est_ca, dernier,
                                       _bpa_comparable)
                    if proj:
                        fonda["proj"] = proj
                        # Porté à côté de la trajectoire, jamais dedans : c'est
                        # une qualité de la SOURCE, pas une valeur projetée.
                        if solidite:
                            fonda["consensus"] = solidite
                except Exception as e:
                    print(f"  ⚠️  {ticker}: PER historique/prévisionnel en échec ({type(e).__name__})")
                chart["fonda"] = fonda

        # ── NOTE v4 — le score EST la note (grille MECE, note_v4.py) ────────
        # Calculée en dernier : elle consomme l'historique fonda (marges
        # médianes, TCAM, PER d'époque, prévisionnels) en plus des champs TTM
        # et du momentum. Chaque intrant manquant retire son critère avec
        # motif et renormalise — un trou de donnée n'est jamais un zéro muet.
        def _n(v):
            """Nombre fini ou None — les NaN Yahoo ne doivent pas entrer dans la note."""
            return v if isinstance(v, (int, float)) and v == v and np.isfinite(v) else None
        _f = fonda if isinstance(fonda, dict) else {}

        # ── Fin de la CHAÎNE DES SOURCES ────────────────────────────────────
        # 1. résumé Yahoo → 2. états financiers (plus haut) → 3. comptes
        # publiés (Yahoo + EDGAR) → 4. Finnhub, US seulement, en dernier.
        # Chaque maillon ne remplit que ce que les précédents ont laissé vide,
        # et inscrit sa provenance : une donnée reconstituée ne se fait jamais
        # passer pour une donnée de première main.
        _nm_raw = margins_raw
        _nm_raw, trailing_pe, _src3 = chainer_comptes(
            _f.get("an"), _meme_devise, prix, _nm_raw, trailing_pe)
        fonda_source += [s + ":comptes" for s in _src3]
        _nm_raw, debt_eq_raw, _src4 = chainer_finnhub(fh_data, _nm_raw, debt_eq_raw)
        fonda_source += [s + ":finnhub" for s in _src4]
        if _nm_raw is not None and margins_raw is None:
            margins = _nm_raw          # le score consomme la valeur chaînée
        breakdown["net_margin_pct"] = (round(_nm_raw * 100, 1)
                                       if _nm_raw is not None else None)
        breakdown["trailing_pe"] = round(trailing_pe, 1) if trailing_pe else None
        breakdown["debt_eq_pct"] = (round(debt_eq_raw)
                                    if _n(debt_eq_raw) is not None else None)
        breakdown["fonda_source"] = fonda_source or None
        # DEVISE DE COTATION, publiée à côté de la devise comptable qui vit
        # dans `fonda.devise`. Sans elle, impossible de vérifier après coup
        # qu'un bénéfice par action projeté n'a pas glissé d'une monnaie à
        # l'autre — le défaut TSM (331 TWD publiés, 16,8 « projetés » en
        # dollars) ne se détecte QUE si l'on sait que les deux diffèrent.
        breakdown["devise_cotation"] = info.get("currency") or None
        # Publiée pour que la fiche puisse montrer d'où sort la conversion, et
        # pour qu'un audit puisse la recalculer sans relancer le screener.
        breakdown["conversion_pct"] = (round(conversion_pct)
                                       if conversion_pct is not None else None)
        # Marge nette du DERNIER EXERCICE PUBLIÉ, à côté de la glissante.
        # Les deux divergent parfois beaucoup — Micron 55,9 % en glissant contre
        # 22,8 % sur l'exercice, SanDisk +34,2 % contre −22,3 % — et c'est
        # légitime : un retournement de cycle met douze mois à traverser un
        # exercice clos. Ce n'est un défaut que tant qu'on n'a qu'un des deux
        # chiffres à l'écran sans dire lequel on regarde.
        #
        # ELLE SE LIT DANS LA SÉRIE PUBLIÉE, PAS DANS LES ÉTATS DU JOUR. Cette
        # marge sortait de `_ec`, c'est-à-dire des états financiers du
        # fournisseur ; le graphique juste en dessous, lui, dessine `fonda.an`,
        # qui accumule EDGAR et va plus loin. Les deux divergent dès qu'un
        # exercice vient de clore : le 09/08/2026, Applied Digital affichait une
        # marge de −160 % (exercice clos en mai 2025) au-dessus d'un graphique
        # montrant l'exercice clos en mai 2026, à −41 %. Deux exercices
        # différents sur la même fiche, sans que rien ne le dise.
        # Deux fiches sur cent vingt-sept, toutes deux à exercice décalé — c'est
        # peu, et c'est exactement pour ça que personne ne l'avait vu.
        # On lit donc la MÊME série que le dessin : un seul « dernier exercice
        # publié » sur la page.
        _der_ex = next((e for e in reversed(_f.get("an") or [])
                        if e.get("ca") and e.get("rn") is not None), None)
        breakdown["net_margin_exercice_pct"] = (
            round(_der_ex["rn"] / _der_ex["ca"] * 100, 1) if _der_ex else None)
        note = note_v4.calcule_note({
            "an":             _f.get("an") or [],
            "pe_prev":        _f.get("pe_prev"),
            "prix":           prix,
            "trailing_pe":    _n(trailing_pe),
            "forward_pe":     _n(forward_pe),
            "net_margin_pct": round(_nm_raw * 100, 1) if _nm_raw is not None else None,
            "fcf_margin_pct": round(fcf_margin * 100, 1) if (fcf_raw is not None and _rev_fcf) else None,
            "conversion_pct": _n(conversion_pct),
            "fcf_yield_pct":  _n(fcf_yield),   # déjà gardé par la devise plus haut
            "roe":            _n(roe),
            "debt_eq":        _n(debt_eq_raw),
            "price_to_book":  _n(price_to_book),
            "roa_pct":        _n(roa_pct),
            "levier_actifs":  _n(levier_actifs),
            # Métier de bilan, déduit de l'INDUSTRIE et non de l'absence de
            # donnée (cf. _INDUSTRIES_BILAN et la leçon du 06/08 : le raccourci
            # « FCF absent » s'est éteint dès qu'on est allé chercher le FCF).
            "banque":         (yf_industry in _INDUSTRIES_BILAN),
            "meme_devise":    _meme_devise,
            "z":              _n(regression_z),
            "rsi":            _n(rsi),
            # mm200 à None (historique partiel) rend le critère NON NOTABLE :
            # note_v4 le retire et renormalise, il ne vaut surtout pas zéro.
            "ecart_mm_pct":   (mm21 / mm200 - 1) * 100 if (mm200 and mm200 > 0) else None,
        })
        score = note["total"]
        breakdown["note"] = note

        return {
            "ticker":        ticker,
            "name":          nom[:22],
            "market":        (info.get("exchange") or "—")[:10],
            "sector":        sector_fr,
            "score":         score,
            "badge":         badge,
            "change":        "stable",
            "breakdown":     breakdown,
            "justification": generer_justification(nom, score, details, alertes),
            "chart":         chart,   # retiré par main() avant écriture — ne fuit jamais dans watchlist.json
        }

    except Exception as e:
        print(f"  ✗ {ticker}: {e}")
        return None

# ── CHANGELOG ────────────────────────────────────────────────────────────────
def raison_sortie(prev_stock, current_stock=None):
    """
    Génère une raison de sortie narrative.

    Distingue trois cas :
      A) Score en chute → la qualité du titre s'est dégradée
      B) Score stable mais dépassé → d'autres titres ont mieux scoré
      C) Données indisponibles cette semaine (rare : yfinance failed)

    Puis ajoute les signaux concrets responsables de la dégradation s'il y en a.
    Reformulé pour être lisible par un non-spécialiste, pas juste informatif.
    """
    prev_score = prev_stock.get("score", 0)
    # Si le titre a été re-scoré cette semaine, on utilise le breakdown frais ;
    # sinon on retombe sur celui de la semaine d'avant (vue dégradée mais utile).
    if current_stock:
        new_score = current_stock.get("score", 0)
        bd        = current_stock.get("breakdown", {})
    else:
        new_score = None
        bd        = prev_stock.get("breakdown", {})

    parts = []

    # 1) Lecture narrative de l'évolution du score ─────────────────────────
    if new_score is not None:
        delta = new_score - prev_score
        if delta <= -8:
            parts.append(f"Score en forte baisse : {prev_score} → {new_score} ({delta:+d} pts)")
        elif delta <= -3:
            parts.append(f"Score en baisse : {prev_score} → {new_score} ({delta:+d} pts)")
        elif delta >= 3:
            parts.append(f"Score stable/en hausse ({prev_score} → {new_score}) mais dépassé par d'autres titres mieux placés cette semaine")
        else:
            parts.append(f"Score stable ({prev_score} → {new_score}) — d'autres titres ont simplement mieux scoré cette semaine")
    else:
        parts.append(f"Données indisponibles cette semaine (était {prev_score}/100)")

    # 2) Signaux techniques responsables (s'il y en a) ─────────────────────
    regime = bd.get("cross_regime", "")
    days   = bd.get("cross_days_ago", 999)
    dyn_warn = bd.get("signal_dynamics_warning", "")

    # Si le cross est en transition, le sortie peut être discutable — on le mentionne
    # pour la transparence (le screener est mécanique mais le signal était nuancé).
    if dyn_warn:
        if "résorption" in dyn_warn:
            parts.append("nuance : le death cross était en cours de résorption (pente MM21 positive) — sortie sur dégradation fonda/momentum global, pas sur le seul cross")
        elif "mean-reversion" in dyn_warn:
            parts.append(f"nuance : rebond mean-reversion en cours, mais score global insuffisant pour rester dans le top {WATCHLIST_SIZE}")
        elif "affaiblissement" in dyn_warn:
            parts.append(f"nuance : {dyn_warn.split(' — ')[0].lower()} — confirme la sortie")

    if regime == "death":
        if days <= 30:
            parts.append(f"Death Cross très récent ({days}j) — bascule en tendance baissière, signal négatif fort")
        elif days <= 60:
            parts.append(f"Death Cross récent ({days}j) — momentum cassé")
        elif days <= 180:
            parts.append(f"Death Cross confirmé ({days}j) — régime baissier persistant")

    # Blocs de la note v4 (breakdown["note"]["blocs"]) — un bloc absent (None)
    # signifie « non notable », pas « nul » : on ne le commente pas.
    _blocs = (bd.get("note") or {}).get("blocs") or {}
    def _bloc(b):
        return (_blocs.get(b) or {}).get("pts")
    mo = _bloc("m")
    if mo is not None:
        if mo < 4:
            parts.append(f"Momentum quasi-nul ({mo:.0f}/15) — tendance qui s'essouffle")
        elif mo < 7 and new_score is not None and new_score < prev_score:
            parts.append(f"Momentum dégradé ({mo:.0f}/15)")

    _fond = [p for p in (_bloc("q"), _bloc("c"), _bloc("v")) if p is not None]
    if _fond and sum(_fond) < 40:
        parts.append(f"Qualité + croissance + valorisation insuffisantes ({sum(_fond):.0f}/85)")

    reg = bd.get("regression_signal", "")
    if reg == "surachat":
        z = bd.get("regression_z", 0)
        parts.append(f"Cours largement au-dessus de sa trajectoire long terme (+{z:.1f}σ) — risque de correction vers la moyenne")

    rsi_v = bd.get("rsi", 50)
    if rsi_v > 75:
        parts.append(f"RSI en surachat marqué ({rsi_v:.0f}) — souvent suivi d'une correction technique")

    return " · ".join(parts) + "."

def load_previous(path="watchlist.json"):
    try:
        with open(path, encoding="utf-8") as f:
            return {s["ticker"]: s for s in json.load(f).get("stocks", [])}
    except FileNotFoundError:
        return {}
    except Exception as e:
        # Fichier présent mais illisible (JSON tronqué…) : on repart d'un précédent
        # vide MAIS on le dit — sinon le changelog fabrique 30 fausses « entrées ».
        print(f"   ⚠️  watchlist précédente illisible ({type(e).__name__}) — changelog reparti de zéro")
        return {}

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Analyse de {len(UNIVERS)} actions…")
    print(f"   Modèle : Golden/Death Cross MM21/MM200 + Régression + RSI + Fondamentaux")
    if FINNHUB_KEY:
        print(f"✓ Finnhub activé (validation croisée)")
    else:
        print(f"⚠ Finnhub non configuré — ajoutez FINNHUB_API_KEY dans les secrets GitHub")

    # VIX dampener (Phase 2) — fetch unique en début de run pour pondérer le momentum
    # de tous les tickers de manière homogène. Fallback à 18 si fetch échoue
    # (médiane historique du VIX, neutre — multiplier ≈ 1.0).
    vix_now = 18.0
    vix_source = "fallback_18"
    try:
        vh = yf.Ticker("^VIX").history(period="5d")["Close"].dropna()
        if not vh.empty:
            vix_now = round(float(vh.iloc[-1]), 2)
            vix_source = "live"
    except Exception as e:
        print(f"   ⚠️  ^VIX fetch failed ({e}) — fallback 18.0 (médiane historique)")
    print(f"   VIX : {vix_now} ({vix_source}) [informationnel — hors scoring depuis v3]")

    previous  = load_previous()
    resultats = []
    COUVERTURE_MIN = 0.60   # part minimale de l'univers scorée pour accepter de publier

    for i, ticker in enumerate(UNIVERS):
        print(f"  [{i+1}/{len(UNIVERS)}] {ticker}…", end=" ")
        r = score_ticker(ticker, vix=vix_now)
        if r:
            resultats.append(r)
            bd      = r["breakdown"]
            conf    = bd.get("confiance", 1.0)
            src     = "+".join(bd.get("sources", ["YF"]))
            z       = bd.get("regression_z", 0)
            regime  = bd.get("cross_regime", "?")
            days    = bd.get("cross_days_ago", "?")
            spread  = bd.get("cross_spread_pct", 0)
            regime_icon = "🟢" if regime == "golden" else "🔴" if regime == "death" else "⚪"
            print(f"score {r['score']} | {regime_icon} {regime} {days}j ({spread:+.1f}%) | z={z:+.2f}σ | {conf:.0%} conf | {src}")
        else:
            print("ignoré")

        # 1 appel Finnhub par ticker (fundamentals) → 0.5s suffit largement sous 60 req/min.
        # Conditionné à un appel RÉELLEMENT émis : finnhub_fundamentals() court-circuite
        # sur les tickers non-US (suffixe de place), pour lesquels aucune requête HTTP
        # n'est faite. Attendre pour eux ne protégeait d'aucun quota — avec 77 titres
        # non-US dans l'univers élargi, c'était ~39 s de run gaspillées chaque semaine.
        if FINNHUB_KEY and _finnhub_appel_emis(ticker):
            time.sleep(0.5)

    resultats.sort(key=lambda x: -x["score"])
    top = resultats[:WATCHLIST_SIZE]

    if not top:
        print("❌ Aucune action scorée — vérifiez la connexion réseau ou les tickers.")
        return

    # ── Garde de couverture (fail-loud) ─────────────────────────────────────
    # Si une trop grande part de l'univers n'a pas pu être scorée (panne de
    # source, rate-limit, barres NaN massives), publier le classement des
    # survivants serait mensonger : le 27/07/2026, 94 titres US évincés ont
    # produit une watchlist 100% EU publiée en silence, job vert. On préfère
    # échouer bruyamment : la watchlist précédente reste en ligne, le job CI
    # passe rouge et alerte (même philosophie que allow_nan=False).
    couverture = len(resultats) / len(UNIVERS)
    if couverture < COUVERTURE_MIN:
        print(f"❌ Couverture insuffisante : {len(resultats)}/{len(UNIVERS)} tickers scorés "
              f"({couverture:.0%} < {COUVERTURE_MIN:.0%}) — watchlist NON publiée.")
        print("   Panne de source de données probable — la version précédente reste en ligne.")
        raise SystemExit(1)

    current_tickers = {s["ticker"] for s in top}
    entrees = [s for s in top if s["ticker"] not in previous]
    sorties = [t for t in previous if t not in current_tickers]

    # Rangs de la semaine précédente, pour publier un MOUVEMENT DE CLASSEMENT.
    # Le champ `change` mesurait auparavant un écart de SCORE (±3 points), ce qui
    # ne dit rien de la place occupée : un titre pouvait gagner 4 points et
    # reculer de six rangs le même jour. Dans une liste ordonnée, c'est le rang
    # qui est l'information. Le score reste affiché à côté, personne ne le perd.
    for i, s in enumerate(top):
        s["rank"] = i + 1
        prev = previous.get(s["ticker"])
        rp = prev.get("rank") if prev else None
        if not prev:
            s["change"] = "new"
            s["rank_prev"] = None
            s["rank_delta"] = None
        elif isinstance(rp, int) and rp > 0:
            # Positif = a MONTÉ (rang 12 → 5 vaut +7).
            s["rank_prev"] = rp
            s["rank_delta"] = rp - s["rank"]
            s["change"] = "up" if s["rank_delta"] > 0 else "down" if s["rank_delta"] < 0 else "stable"
        else:
            # Titre déjà présent mais sans rang exploitable (archive d'avant ce
            # champ) : on ne devine pas un mouvement, on le dit stable.
            s["rank_prev"] = None
            s["rank_delta"] = None
            s["change"] = "stable"

    # Index des résultats actuels pour permettre au narratif de sortie
    # de comparer prev_score vs new_score (cf. raison_sortie)
    results_by_ticker = {r["ticker"]: r for r in resultats}

    changelog = []
    for s in entrees[:5]:
        changelog.append({"action":"in","ticker":s["ticker"],"name":s["name"],"score":s["score"],"reason":s["justification"]})
    for t in sorties[:5]:
        prev = previous[t]
        current = results_by_ticker.get(t)  # peut être None si scoring failed cette semaine
        changelog.append({
            "action": "out",
            "ticker": t,
            "name":   prev.get("name", t),
            "score":  prev.get("score", 0),
            "new_score": current.get("score") if current else None,
            "reason": raison_sortie(prev, current),
        })

    # ── Composition de la sélection : exhaustif, tous secteurs triés desc ────
    from collections import Counter
    sector_counts = Counter(s["sector"] for s in top)
    concentration_alerts = [
        f"{sector} : {n} titre{'s' if n > 1 else ''} sur {WATCHLIST_SIZE}"
        for sector, n in sector_counts.most_common()
    ]
    if concentration_alerts:
        print("\nℹ Composition sectorielle de la sélection :")
        for alert in concentration_alerts:
            print(f"   · {alert}")

    # ── Extraction du payload graphique ─────────────────────────────────────
    # "chart" ne doit fuiter ni dans watchlist.json ni dans l'archive : on le
    # collecte puis on le retire de TOUS les résultats — top inclus, ce sont les
    # mêmes dicts.
    # On collecte désormais TOUT l'univers scoré, pas seulement le top 30 : le
    # payload était déjà calculé pour chaque titre (le coût est payé dans
    # score_ticker) puis jeté pour 180 d'entre eux, ce qui produisait des fiches
    # thématiques sans canal de régression. Le tri de ce qui est PUBLIÉ se fait
    # plus bas, une fois les thèmes connus.
    charts_tous = {r["ticker"]: r["chart"] for r in resultats if r.get("chart") is not None}
    charts = {s["ticker"]: charts_tous[s["ticker"]]
              for s in top if s["ticker"] in charts_tous}
    for r in resultats:
        r.pop("chart", None)

    d = date.today()

    # ── Projection thématique (universe.json) ───────────────────────────────
    # Principe : « un seul scoring, N projections ». Chaque titre a été scoré
    # exactement une fois ci-dessus ; une watchlist thématique n'est qu'un
    # filtre + tri sur ces mêmes résultats. Coût API marginal : zéro.
    # watchlist.json n'est PAS touché — trois consommateurs lisent son contrat
    # en dur (portfolio_agent, generate_analyses, index.html).
    inv_curés   = themes.themes_par_ticker()
    top_tickers = {s["ticker"] for s in top}
    par_ticker  = {}          # ticker → objet compact publié
    themes_de   = {}          # ticker → tous ses thèmes (curés + calculés)

    def _bloc_pts(bd, b):
        """Points arrondis (1 déc.) d'un bloc de la note v4, None si non notable."""
        pts = ((bd.get("note") or {}).get("blocs", {}).get(b) or {}).get("pts")
        return round(pts, 1) if pts is not None else None

    for r in resultats:
        t  = r["ticker"]
        bd = r.get("breakdown", {}) or {}
        ths = list(inv_curés.get(t, [])) + themes.themes_calcules_pour(bd)
        themes_de[t] = ths
        if not ths:
            continue          # titre de l'univers historique sans thème : hors universe.json
        # Un titre sans secteur exploitable est le symptôme d'une collecte ratée
        # (Linde le 01/08 : secteur absent, qualité 0, score 6/100). Le publier
        # dans un thème afficherait une ligne vide de sens, et il échapperait à
        # la règle de concentration sectorielle s'il devenait achetable.
        if not r.get("sector") or r["sector"] == "—":
            print(f"  ⚠️  {t} exclu des thèmes — secteur absent (collecte incomplète)")
            themes_de[t] = []
            continue
        z = bd.get("regression_z")
        par_ticker[t] = {
            "nom":          r.get("name", t),
            "score":        r.get("score", 0),
            "secteur":      r.get("sector", "—"),
            "market":       r.get("market", "—"),
            "devise":       bd.get("devise", ""),
            "prix":         bd.get("prix"),
            "z":            round(z, 1) if z is not None else None,
            "fenetre":      bd.get("regression_window_years"),
            "decote_pct":   bd.get("decote_pct"),
            "rsi":          bd.get("rsi"),
            "cross":        bd.get("cross_regime", ""),
            "cross_j":      bd.get("cross_days_ago"),
            "upside_pct":   bd.get("target_upside_pct"),
            "analystes":    bd.get("target_analysts"),
            # Blocs de la note v4, compacts (points arrondis ; None = bloc non
            # notable). Le détail des critères vit dans charts/<T>.json.
            "q":            _bloc_pts(bd, "q"),
            "c":            _bloc_pts(bd, "c"),
            "v":            _bloc_pts(bd, "v"),
            "m":            _bloc_pts(bd, "m"),
            "couverture":   (bd.get("note") or {}).get("couverture"),
            # ── MULTIPLES, MARGES ET CROISSANCE (12/08/2026) ──────────────
            # Le contrat compact n'en portait aucun : les 118 fiches thématiques
            # étaient rédigées sans un chiffre de valorisation, leur signature
            # éditoriale rendait « na » stablement (donc muette), et le modèle
            # écrivait des multiples de mémoire. Ces champs referment les deux
            # trous, et rendent une publication de résultats VISIBLE par la
            # signature : trimestre publié → paliers déplacés → fiche réécrite.
            # Récit complet : CHANGELOG du 12/08. Garde : test_themes (AST,
            # producteur/lecteurs) + test_donnees (signature non aveugle).
            "per_fwd":          bd.get("forward_pe"),
            "per_cur":          bd.get("trailing_pe"),
            "fcf_yield_pct":    bd.get("fcf_yield_pct"),
            "marge_nette_pct":  bd.get("net_margin_pct"),
            "marge_fcf_pct":    bd.get("fcf_margin_pct"),
            "croissance_ca_pct": bd.get("rev_growth_pct"),
            "croissance_ca_fin": bd.get("rev_growth_fin"),
            # Présence/absence seulement : la signature ne lit que le booléen,
            # et le libellé complet vit dans charts/<T>.json.
            "alerte":       bd.get("signal_dynamics_warning") or "",
            "themes":       ths,
            "top30":        t in top_tickers,
        }

    scores_par_ticker = {r["ticker"]: r.get("score", 0) for r in resultats}
    themes_publies, degrades = [], []

    for th in themes.THEMES:
        if th["kind"] == "calcule":
            membres = [t for t, ths in themes_de.items() if th["id"] in ths]
            tri = th["tri"]
            bd_de = {r["ticker"]: (r.get("breakdown", {}) or {}) for r in resultats}
            membres.sort(key=lambda t: (tri(bd_de[t]), t))
            # Une règle large peut sélectionner la moitié de l'univers : on borne
            # la liste publiée, sinon ce n'est plus une watchlist mais un filtre.
            # `eligibles` garde le compte AVANT troncature — le site affiche donc
            # « 12 retenus sur 48 éligibles », jamais un total silencieusement tronqué.
            eligibles = len(membres)
            membres = membres[:themes.TOP_PAR_THEME]
            # Un thème calculé n'a pas de liste déclarée : la notion de couverture
            # ne s'y applique pas. La rapporter à `eligibles` produisait un taux de
            # 25 % et un faux « thème dégradé » alors que le bornage est voulu.
            declares = len(membres)
            couverts = len(membres)
        elif th["kind"] == "filtre":
            # Troisième forme, ni curée ni calculée. L'appartenance est une
            # PROPRIÉTÉ DÉCLARÉE du titre — pour le PEA, le pays du siège social,
            # que le breakdown ne porte pas et ne portera jamais : ce n'est pas
            # une mesure de marché. Mais la liste publiée est bornée aux N
            # meilleurs scores, comme un thème calculé, sinon « top 20 » n'aurait
            # pas de sens.
            membres = [t for t in th["tickers"] if t in par_ticker]
            membres.sort(key=lambda t: (-scores_par_ticker.get(t, 0), t))
            # `declares` reste le nombre d'éligibles DÉCLARÉS, pas la taille de
            # la liste publiée : c'est lui qui fait de la couverture un vrai
            # garde-fou. Un thème calculé n'a pas de liste déclarée et doit
            # neutraliser ce calcul ; ici on en a une, donc si la moitié des
            # éligibles cesse d'être scorée, la bannière doit le dire — même si
            # les vingt lignes publiées, elles, restent pleines.
            declares = len(th["tickers"])
            eligibles = len(membres)
            # La couverture se mesure sur les titres SCORÉS, avant bornage. La
            # mesurer sur la liste publiée donnerait 20/48 à chaque run, donc un
            # thème perpétuellement « dégradé » par sa propre définition — un
            # garde-fou qui hurle en permanence ne garde plus rien.
            couverts = eligibles
            membres = membres[: th.get("top", themes.TOP_PAR_THEME)]
        else:
            eligibles = None
            declares = len(th["tickers"])
            membres = [t for t in th["tickers"] if t in par_ticker]
            # Tri par score décroissant, départage par ticker croissant :
            # l'ordre publié doit être reproductible d'un run à l'autre.
            membres.sort(key=lambda t: (-scores_par_ticker.get(t, 0), t))
            # La couverture se mesure AVANT bornage, comme pour un filtre : sinon
            # un thème qui publie dix titres sur vingt-deux déclarés afficherait
            # 45 % de couverture à chaque run, donc « dégradé » en permanence par
            # sa propre définition.
            couverts = len(membres)
            # BORNAGE `top`, DÉSORMAIS GÉNÉRAL. Il n'existait que pour le kind
            # « filtre », où il portait le « top 20 » du PEA. Un thème de thèse
            # peut vouloir la même chose : déclarer un périmètre honnête et n'en
            # publier que les meilleurs. Le secteur du quantique en est le cas
            # d'école — une vingtaine de sociétés cotées y sont défendables, dix
            # font une liste qu'on lit.
            if th.get("top"):
                membres = membres[: th["top"]]

        couv = (couverts / declares) if declares else 1.0
        # Garde de couverture PAR THÈME. Le seuil global (60 % de l'univers) ne
        # protège plus rien à cette échelle : il faudrait perdre 84 titres sur
        # 210 avant d'échouer, donc un thème entièrement vidé par une panne de
        # place de cotation passerait sous le radar et serait publié vide, job
        # vert. C'est exactement le mode de panne de l'incident du 27/07.
        status = "ok" if couv >= 0.70 else "degraded"
        if status == "degraded":
            degrades.append(th["id"])
            print(f"   ⚠️  Thème {th['id']} dégradé : {couverts}/{declares} titres ({couv:.0%})")

        meta = next(m for m in themes.meta_publique() if m["id"] == th["id"])
        themes_publies.append({**meta,
                               "declares":   declares,
                               "eligibles":  eligibles,   # thèmes calculés seulement
                               "scores":     len(membres),
                               "couverture": round(couv, 3),
                               "status":     status,
                               "members":    membres})

    # Un thème isolé qui se dégrade est publié avec sa bannière — échouer tout
    # le run pour ça serait pire que le mal. Une proportion notable de thèmes
    # dégradés, ou un thème entièrement vide, signalent une panne de source.
    #
    # Le seuil est PROPORTIONNEL : il valait 3 quand treize thèmes étaient
    # publiés, ce qui le rendait inatteignable une fois le périmètre resserré à
    # deux — les deux thèmes auraient pu se vider à moitié sans que rien
    # n'échoue. Un garde-fou dont le seuil dépend du nombre d'éléments surveillés
    # doit suivre ce nombre.
    seuil_degrades = max(2, round(len(themes_publies) * 0.25))
    if len(degrades) >= seuil_degrades or any(t["scores"] == 0 for t in themes_publies):
        print(f"❌ {len(degrades)} thème(s) dégradé(s) sur {len(themes_publies)} "
              f"(seuil {seuil_degrades}) : {', '.join(degrades)} — "
              f"panne de source probable, publication interrompue.")
        raise SystemExit(1)

    # Ne publier que les titres RÉELLEMENT listés par au moins un thème. Un titre
    # retenu par la règle d'un thème calculé mais recalé hors des 12 publiés se
    # retrouvait dans `stocks` sans figurer dans aucune liste de membres :
    # inatteignable depuis le site, mais suffisant pour déclencher la génération
    # d'une fiche éditoriale payante et pour entrer dans l'univers achetable de
    # l'agent. Tout ce qui est publié ici doit être joignable.
    publies = {t for th in themes_publies for t in th["members"]}
    ecartes = sorted(set(par_ticker) - publies)
    if ecartes:
        print(f"  ℹ️  {len(ecartes)} titre(s) retenus par une règle mais hors des listes "
              f"publiées — non exposés : {', '.join(ecartes)}")
    par_ticker = {k: v for k, v in par_ticker.items() if k in publies}

    universe = {
        "updated_at":        str(d),
        "week":              f"Sem. {d.isocalendar()[1]} · {d.year}",
        "universe_declared": len(UNIVERS),
        "universe_scored":   len(resultats),
        "themes":            themes_publies,
        "stocks":            par_ticker,
    }
    # ── Illustrations par activité ──────────────────────────────────────────
    tmp_u = "universe.json.tmp"
    with open(tmp_u, "w", encoding="utf-8") as f:
        json.dump(universe, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    os.replace(tmp_u, "universe.json")
    print(f"🗂  universe.json — {len(themes_publies)} thèmes, {len(par_ticker)} titres tagués"
          + (f", {len(degrades)} dégradé(s)" if degrades else ""))
    output = {
        "updated_at":              str(d),
        "week":                    f"Sem. {d.isocalendar()[1]} · {d.year}",
        "universe_size":           len(resultats),
        "finnhub_active":          bool(FINNHUB_KEY),
        "stocks":                  top,
        "changelog":               changelog,
        "concentration_alerts":    concentration_alerts,
        "sector_distribution":     dict(sector_counts.most_common()),
    }

    # Écriture atomique + stricte (même contrat que save_json_atomic de
    # portfolio_agent.py) : allow_nan=False fait échouer le run bruyamment plutôt
    # que de publier un token NaN illisible par JSON.parse ; tmp + os.replace
    # garantit qu'un crash mid-write ne laisse jamais un fichier tronqué.
    tmp_path = "watchlist.json.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, allow_nan=False)
    os.replace(tmp_path, "watchlist.json")

    # charts.json — RETIRÉ LE 10/08/2026. Ce monolithe du top 30 était annoncé
    # « TRANSITOIRE : index.html le charge encore au démarrage ». Il ne le
    # chargeait plus : les six points de chargement d'index.html ont été
    # énumérés un par un, aucun ne le demandait, et la seule occurrence restante
    # du nom dans le front était un commentaire racontant l'époque où il servait.
    # La transition s'était terminée sans que personne referme la porte, et le
    # fichier continuait d'être régénéré et commité — 645 Ko à chaque run de
    # données, pour personne. Les fiches sont servies par charts/<TICKER>.json,
    # écrit juste en dessous, à la demande et par titre.

    # ── charts/<TICKER>.json — un fichier par fiche ouvrable ────────────────
    # Périmètre : les titres tagués par un thème (par_ticker) UNION le top 30.
    # L'union n'est pas redondante : un titre peut être très bien noté sans
    # appartenir à aucun thème, et sa fiche aurait perdu son graphe le jour du
    # retrait de charts.json — retrait effectué le 10/08/2026, cette union est
    # donc désormais la SEULE source des graphiques du site.
    # Le breakdown complet voyage avec le graphe : une fiche thématique affiche
    # ainsi les MÊMES données qu'une fiche du top 30 dès que son graphique est
    # chargé (l'écart TSM/BLK constaté le 01/08 venait de là — universe.json ne
    # porte qu'un extrait compact de 19 champs, par choix de poids du fetch
    # bloquant, pas par manque de données).
    bd_par_ticker = {r["ticker"]: r["breakdown"] for r in resultats if r.get("breakdown")}
    publier_charts(charts_tous, set(par_ticker) | top_tickers, breakdowns=bd_par_ticker)

    # ── Archive snapshot point-in-time ──
    # Capture l'état des fondamentaux/analystes à la date du run (les données fonda
    # historiques point-in-time n'étant pas exposées par Yahoo).
    try:
        # PAS de `import os` local ici : il rendrait `os` local à TOUTE la fonction
        # et casserait le os.replace() de l'écriture atomique plus haut
        # (UnboundLocalError — incident du run 2026-07-20).
        import shutil
        archive_dir = os.path.join("notes", "watchlist_archive")
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, f"{d}.json")
        shutil.copy("watchlist.json", archive_path)
        print(f"📦 Snapshot archivé → {archive_path}")
    except Exception as e:
        print(f"⚠️  Échec archive snapshot : {e}")

    top1 = top[0]
    print(f"\n✅ watchlist.json — {len(top)} actions")
    print(f"   #1 : {top1['name']} ({top1['score']}/100)")
    print(f"   {top1['justification']}")

if __name__ == "__main__":
    main()
