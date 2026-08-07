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

def cross_label(regime, days, cross_type):
    """Label lisible pour l'affichage frontend."""
    if regime == "golden":
        if days <= 10:  return f"Golden Cross · {days}j — Signal fort"
        if days <= 30:  return f"Golden Cross · {days}j"
        if days <= 60:  return f"Golden Cross confirmé · {days}j"
        return f"Régime haussier · {days}j"
    elif regime == "death":
        if days <= 30:  return f"Death Cross · {days}j — Baissier"
        if days <= 90:  return f"Death Cross confirmé · {days}j"
        return f"Régime baissier · {days}j"
    return "Données insuffisantes"

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

# ── PAYLOAD GRAPHIQUE (charts.json) ──────────────────────────────────────────
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


def etats_complements(df_cf, df_bs):
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


def per_historique(an, prix_a_la_date, meme_devise):
    """Ajoute le PER de chaque exercice : cours de clôture de l'exercice / BPA
    dilué publié. UNIQUEMENT quand la devise comptable est celle de cotation :
    un ADR comme TSM cote en USD mais publie son BPA en TWD (et représente
    plusieurs actions ordinaires) — le quotient serait un non-sens, on omet.
    Mutation en place des entrées ; BPA négatif ou nul → pas de PER (une perte
    n'a pas de multiple). prix_a_la_date : date iso → cours, None si inconnu."""
    if not meme_devise:
        return an
    for e in an:
        eps = e.get("eps")
        if not eps or eps <= 0:
            continue
        prix = prix_a_la_date(e["fin"])
        if prix and prix > 0:
            e["per"] = round(prix / eps, 1)
    return an


def per_previsionnel(prix, estimations, dernier_exercice):
    """PER des deux exercices À VENIR : cours ACTUEL / BPA moyen estimé par les
    analystes (Yahoo, lignes 0y et +1y). Les estimations sont publiées dans la
    devise de COTATION de la place interrogée — le quotient est donc valide
    même pour un ADR. Étiquettes = exercice fiscal suivant le dernier clos.
    estimations : {"0y": eps, "+1y": eps} (None/absent tolérés)."""
    if not prix or prix <= 0 or not dernier_exercice:
        return []
    try:
        annee = int(str(dernier_exercice)[:4])
    except (TypeError, ValueError):
        return []
    out = []
    for i, cle in enumerate(("0y", "+1y")):
        eps = (estimations or {}).get(cle)
        if eps and eps > 0:
            out.append({"exercice": annee + 1 + i, "per": round(prix / eps, 1)})
    return out


HORIZON_PROJECTION = 2030
CROISSANCE_TERMINALE = 3.0     # % — croissance nominale de long terme d'une économie développée
# Plafond du taux de départ de la BRANCHE PRUDENTE de la prolongation.
#
# CE QUE CE PLAFOND SUPPOSE, ET QUAND IL A TORT. Au-delà de ~25 % par an, la
# littérature classe l'hypothèse en « très spéculative » — pour une croissance
# ORGANIQUE. Mais une société dont le chiffre d'affaires est déjà contracté
# (carnet de commandes pluriannuel signé) n'obéit pas à cette base statistique :
# le premier jet de cette fonction projetait Nebius à 3,8 Md$ en 2030 quand le
# marché en discute 33 à 46, parce que le plafond écrasait un carnet signé sous
# un a priori de croissance organique. Aucune donnée dont nous disposons ne
# permet de distinguer les deux régimes automatiquement.
#
# D'où la réponse : ne PAS trancher, et publier les DEUX branches. La prudente
# (plafonnée, ci-dessous) et la haute, qui prolonge le rythme que les analystes
# eux-mêmes projettent. L'écart entre les deux N'EST PAS un défaut d'affichage :
# c'est la mesure de notre ignorance, et le lecteur a le droit de la voir.
# Ce cône ne vaut toutefois que dans un domaine où PROLONGER a encore un sens ;
# au-delà, on ne l'élargit pas indéfiniment, on s'arrête (voir SEUIL_REFUS).
PLAFOND_EXTRAPOLATION = 25.0
# SEUIL DE REFUS — au-delà, on ne prolonge plus DU TOUT.
#
# Ce seuil n'est pas un plafond : c'est une frontière de compétence. Quand le
# consensus implique plus de 50 % par an (Nebius : +312 % entre 2025 et 2027),
# les deux réponses arithmétiques sont fausses et nous l'avons vérifié sur ce
# titre : plafonner donnait 18 Md$ en 2030 quand le marché en discute 33 à 46 ;
# ne pas plafonner donnait 140 Md$. Un tel rythme signale une trajectoire portée
# par des ENGAGEMENTS CONTRACTUELS — un carnet pluriannuel signé — que ni les
# comptes publiés ni le consensus à deux ans ne décrivent. Aucune donnée dont
# nous disposons ne permet de la prolonger honnêtement.
#
# On applique donc aux projections la règle déjà en vigueur pour la note : ce
# qu'on ne sait pas calculer n'est pas approximé, il est RETIRÉ AVEC SON MOTIF.
# Le consensus reste affiché — c'est un fait publié — et la courbe s'arrête là,
# en disant pourquoi. Entre 25 % et 50 %, en revanche, le cône garde tout son
# sens : la fourchette est large mais les deux bornes restent défendables.
SEUIL_REFUS = 50.0


def projections(an, estimations_bpa, estimations_ca, dernier_exercice,
                horizon=HORIZON_PROJECTION, g_terminale=CROISSANCE_TERMINALE,
                plafond=PLAFOND_EXTRAPOLATION, seuil_refus=SEUIL_REFUS):
    """Trajectoire attendue du CA et du BPA jusqu'à `horizon`.

    DEUX NATURES DE VALEURS, JAMAIS CONFONDUES — c'est tout l'objet de cette
    fonction, et la raison pour laquelle chaque SÉRIE porte la sienne
    (`ca_nature`, `eps_nature`), l'année ne portant qu'un résumé prudent :

      · « consensus » : les DEUX seuls exercices que les analystes couvrent
        réellement (exercice en cours et suivant, publiés par Yahoo). Ce sont
        des estimations d'humains qui suivent la société.
      · « extrapolé » : tout ce qui va au-delà. AUCUN analyste ne publie de
        prévision à cinq ans par société ; ces lignes sont une PROLONGATION
        ARITHMÉTIQUE de notre fait, pas une opinion de marché. Le front doit
        les distinguer visuellement, et elles n'entrent JAMAIS dans la note.

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

    Pure et testable hors ligne. Rend [] si rien n'est projetable.
    """
    if not dernier_exercice:
        return []
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
            # La borne haute n'est publiée que si elle DIFFÈRE : sur un
            # compounder régulier les deux branches coïncident, et afficher
            # une fourchette large de zéro serait du bruit.
            if len(t) > 2 and round(t[2], arr) != round(t[0], arr):
                ligne[cle + "_haut"] = round(t[2], arr)
            if ligne.get("nature") != "extrapolé":
                ligne["nature"] = t[1]
        if arret and vals:
            lignes[max(vals)][cle + "_arret"] = arret

    for cle, est in (("ca", estimations_ca), ("eps", estimations_bpa)):
        base = _dernier(cle)
        if base is None or base <= 0:
            continue                      # perte ou absence : rien à prolonger
        # 1) les deux exercices de consensus, tels que publiés
        vals, dernier_val, dernier_an = {}, base, an0
        for i, k in enumerate(("0y", "+1y")):
            v = (est or {}).get(k)
            if v and v > 0:
                vals[an0 + 1 + i] = (v, "consensus")
                dernier_val, dernier_an = v, an0 + 1 + i
        # 2) le rythme de départ, en DEUX branches
        if dernier_an > an0:
            g_att = ((dernier_val / base) ** (1 / (dernier_an - an0)) - 1) * 100
        else:
            g_att = _tcam_demontre(cle)
            if g_att is None:
                continue                  # ni consensus ni historique : on ne prolonge pas
        g_dem = _tcam_demontre(cle)
        # Rythme de départ de la branche PRUDENTE, AVANT bornage : c'est lui
        # qui dit si prolonger a un sens (l'estimé ne dépasse pas le prouvé,
        # même prudence que le PEG).
        g_dep = min(g_att, g_dem) if g_dem is not None else g_att
        # ── LES DEUX REFUS DE PROLONGER ──────────────────────────────────
        # Ce qu'on ne sait pas calculer n'est pas approximé : il est RETIRÉ
        # AVEC SON MOTIF, exactement comme un critère de la note. Le consensus,
        # lui, reste publié — c'est un fait déposé, pas une opinion à nous.
        #
        #  · PAR LE HAUT (au-delà de SEUIL_REFUS) : les deux bornes du cône
        #    sont fausses, plafonner sous-estime et ne pas plafonner délire.
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
        if g_dep < g_terminale:
            _poser(cle, vals,
                   "le rythme constaté ne soutient aucune prolongation "
                   "crédible, et nous n'inventons pas d'inflexion")
            continue
        # Branche PRUDENTE : le rythme de départ, plafonné. Branche HAUTE : le
        # rythme que les analystes projettent eux-mêmes, tel quel (il est sous
        # le seuil de refus, sinon on ne serait pas ici).
        g_bas = max(min(g_dep, plafond), g_terminale)
        g_haut = max(g_att, g_bas)
        # 3) prolongation à croissance décroissante vers le taux terminal
        n = horizon - dernier_an
        v_bas = v_haut = dernier_val
        for i in range(1, n + 1):
            fade = 1 - i / (n + 1)
            v_bas *= 1 + (g_terminale + (g_bas - g_terminale) * fade) / 100
            v_haut *= 1 + (g_terminale + (g_haut - g_terminale) * fade) / 100
            vals[dernier_an + i] = (v_bas, "extrapolé", v_haut)
        _poser(cle, vals)
    return [lignes[a] for a in sorted(lignes)]


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
    for cle, borne in (("an", max_an), ("tr", max_tr)):
        frais = {e["fin"] for e in (nouveau.get(cle) or [])}
        par_fin = {e["fin"]: e for e in (ancien.get(cle) or [])}
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
        # plus, donc ne l'écrase jamais. Le filtre de clôture majoritaire de
        # construire_fonda est rejoué sur l'union.
        if cle == "an" and len(dedup) >= 3:
            mois = [int(e["fin"][5:7]) for e in dedup]
            maj = max(set(mois), key=mois.count)
            emois = lambda m: min(abs(m - maj), 12 - abs(m - maj))
            dedup = [e for e in dedup if emois(int(e["fin"][5:7])) <= 1]
        out[cle] = dedup[-borne:]
    # PER prévisionnels : ce sont des estimations COURANTES, le run le plus
    # récent fait foi ; à défaut (Yahoo muet un jour), on garde les anciennes,
    # leurs étiquettes d'exercice rendent tout vieillissement visible.
    pe = nouveau.get("pe_prev") or ancien.get("pe_prev")
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
                 partagés avec le monolithe charts.json transitionnel.

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
    # ADR US existants (TSM Taiwan semis, SE Asie SEA, SONY Japon)
    "TSM","SE","SONY",
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
UNIVERS = sorted(set(UNIVERS) | set(themes.univers_thematique()))

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
        hist = data.history(period="max", auto_adjust=True)
        if len(hist) < 50:
            return None

        # Purge des barres sans cours AVANT tout calcul (même correctif que
        # last_valid_close() côté portfolio/update_prices, incident 3.0.1) :
        # un run pré-ouverture (8h-13h30 UTC) peut recevoir de Yahoo une barre
        # du jour avec Close=NaN pour les places pas encore ouvertes — sans ce
        # dropna, MM21/MM200/RSI deviennent NaN et le titre est écarté à tort
        # (incident du 27/07/2026 : les 94 titres US évincés, watchlist 100% EU).
        close  = hist["Close"].squeeze().dropna()
        # Un cours nul ou NÉGATIF est toujours un artefact (ajustements Yahoo
        # aberrants sur l'historique lointain : 35 barres négatives sur
        # 000660.KS en 2000, deux zéros sur CS.PA). L'échelle log du front ne
        # peut pas les montrer et un seul point rendait le graphe MAX
        # invisible — écartés à la source, en plus de la défense côté front.
        close  = close[close > 0]
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

        # Indicateurs techniques sur les 2 dernières années (MM21/MM200/RSI/volume)
        close_2y  = close.iloc[-504:]  if len(close)  > 504 else close
        volume_2y = volume.iloc[-504:] if len(volume) > 504 else volume

        prix   = float(close.iloc[-1])
        mm21   = float(close_2y.rolling(21).mean().iloc[-1])
        mm200  = float(close_2y.rolling(200).mean().iloc[-1])
        rsi    = float(RSIIndicator(close=close_2y, window=14).rsi().iloc[-1])
        vol_recent = float(volume_2y.tail(20).mean())   # volume des 20 derniers jours
        vol_annual  = float(volume_2y.mean())            # moyenne sur 2 ans

        # Garde NaN : le garde d'entrée n'exige que 50 barres alors que la MM200 en
        # demande 200 — entre les deux, rolling() renvoie NaN, qui traverserait
        # float()/round() sans lever et finirait sérialisé dans watchlist.json
        # (token NaN → JSON.parse échoue côté site, incident classe 3.0.1).
        if any(v != v for v in (prix, mm21, mm200, rsi, vol_recent, vol_annual)):
            print(f"  ✗ {ticker}: historique insuffisant pour MM200/RSI ({len(close_2y)} barres) — écarté")
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
        debt_eq_raw  = info.get("debtToEquity")          # garde None pour distinguer net-cash (=0) vs missing
        reco         = info.get("recommendationMean") or 3.5
        roe          = info.get("returnOnEquity")        # ROE — proxy qualité du capital ; None si absent
        # Cours / actifs nets comptables — le multiple de référence des métiers
        # de BILAN, où les fonds propres ont un sens économique réel. Il
        # remplace le rendement du cash dans la note des banques et assureurs
        # (cf. note_v4). Publié par Yahoo pour toutes les places, donc sans
        # l'asymétrie géographique qu'aurait introduite une source US.
        price_to_book = info.get("priceToBook")

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
        if (fcf_raw is None and not _metier_bilan) or debt_eq_raw is None or roe is None:
            try:
                _ec = etats_complements(data.cashflow, data.balance_sheet)
            except Exception as e:
                print(f"  ⚠️  {ticker}: états financiers illisibles ({type(e).__name__})")
                _ec = {}
            _cp = _ec.get("capitaux_propres")
            if fcf_raw is None and _ec.get("fcf") is not None:
                fcf_raw = _ec["fcf"]; fonda_source.append("fcf")
            if debt_eq_raw is None and _cp and _ec.get("dette") is not None:
                debt_eq_raw = _ec["dette"] / _cp * 100; fonda_source.append("dette")
            # ROE = résultat net du dernier exercice publié ÷ capitaux propres.
            # Les deux sont en devise COMPTABLE : le ratio est homogène.
            if roe is None and _cp:
                _ni = info.get("netIncomeToCommon")
                if _ni is not None and _ni == _ni:
                    roe = _ni / _cp; fonda_source.append("roe")

        fcf        = fcf_raw or 0
        # Bug corrigé (latent) : `totalRevenue or 1` faisait de fcf/1 une
        # « marge » astronomique quand le CA manquait — la donnée absente
        # OFFRAIT les 8 points au lieu d'en priver.
        fcf_margin = (fcf / total_rev_raw) if (fcf_raw is not None and total_rev_raw) else 0
        # Rendement du FCF : le FCF est publié en devise COMPTABLE, la
        # capitalisation en devise de COTATION. Quand elles diffèrent (ADR :
        # TSM cotait un « FCF yield » de 34 % — TWD divisés par des USD), le
        # ratio est un non-sens : on publie null plutôt qu'un chiffre faux.
        _meme_devise = (((info.get("financialCurrency") or "") ==
                         (info.get("currency") or ""))
                        if info.get("financialCurrency") else True)
        fcf_yield  = (fcf / market_cap * 100) \
            if (fcf_raw is not None and market_cap and _meme_devise) else None

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
            "mm200":                 round(mm200, 2),
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
            "nom_complet":           (info.get("longName") or info.get("shortName") or ticker),
            # Fondamentaux
            # Trou de donnée → null → « — » au front. Un 0.0 publié est une
            # MESURE (croissance nulle, marge nulle), plus jamais un défaut.
            "rev_growth_pct":        round(rev_growth * 100, 1) if rev_growth_raw is not None else None,   # trimestriel, glissement annuel (MRQ vs même trim. N-1)
            "net_margin_pct":        round(margins * 100, 1) if margins_raw is not None else None,         # TTM (12 mois glissants)
            "fcf_margin_pct":        round(fcf_margin * 100, 1) if (fcf_raw is not None and total_rev_raw) else None,  # TTM (12 mois glissants)
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

        nom = info.get("shortName") or info.get("longName") or ticker

        # ── Payload graphique (charts.json) — fail-soft : un graphe raté ne doit
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
                            try:
                                spl = [(str(ts.date()), float(v))
                                       for ts, v in data.splits.items() if v and v > 0]
                            except Exception:
                                spl = []
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
                    def prix_fin(iso):
                        try:
                            avant = close[close.index <= pd.Timestamp(iso, tz=close.index.tz)]
                            return float(avant.iloc[-1]) if len(avant) else None
                        except Exception:
                            return None
                    meme_devise = ((info.get("financialCurrency") or "") ==
                                   (info.get("currency") or ""))
                    per_historique(fonda["an"], prix_fin, meme_devise)
                    est = None
                    try:
                        ee = data.earnings_estimate
                        if ee is not None and "avg" in getattr(ee, "columns", []):
                            est = {k: (float(ee.loc[k, "avg"]) if k in ee.index
                                       and ee.loc[k, "avg"] == ee.loc[k, "avg"] else None)
                                   for k in ("0y", "+1y")}
                    except Exception:
                        est = None
                    dernier = fonda["an"][-1]["fin"] if fonda["an"] else None
                    prev = per_previsionnel(float(close.iloc[-1]), est, dernier)
                    if prev:
                        fonda["pe_prev"] = prev
                    # Trajectoire attendue jusqu'à 2030 : consensus analystes
                    # sur deux exercices, prolongation à croissance
                    # décroissante au-delà. Hors note, purement informationnel.
                    est_ca = None
                    try:
                        re_ = data.revenue_estimate
                        if re_ is not None and "avg" in getattr(re_, "columns", []):
                            est_ca = {k: (float(re_.loc[k, "avg"]) / 1e6
                                          if k in re_.index
                                          and re_.loc[k, "avg"] == re_.loc[k, "avg"] else None)
                                      for k in ("0y", "+1y")}
                    except Exception:
                        est_ca = None
                    proj = projections(fonda["an"], est, est_ca, dernier)
                    if proj:
                        fonda["proj"] = proj
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
        note = note_v4.calcule_note({
            "an":             _f.get("an") or [],
            "pe_prev":        _f.get("pe_prev"),
            "prix":           prix,
            "trailing_pe":    _n(trailing_pe),
            "forward_pe":     _n(forward_pe),
            "net_margin_pct": round(_nm_raw * 100, 1) if _nm_raw is not None else None,
            "fcf_margin_pct": round(fcf_margin * 100, 1) if (fcf_raw is not None and total_rev_raw) else None,
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
            "ecart_mm_pct":   (mm21 / mm200 - 1) * 100 if mm200 > 0 else None,
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
            couverts = len(membres)

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

    # charts.json — payload graphique du top 30, monolithique. TRANSITOIRE :
    # index.html le charge encore au démarrage ; il fait doublon avec charts/
    # (mêmes données, top 30 uniquement) et sera retiré une fois le front
    # bascule sur le chargement paresseux. Séparateurs compacts, pas d'indent.
    # Même contrat d'écriture atomique + allow_nan=False.
    tmp_charts = "charts.json.tmp"
    with open(tmp_charts, "w", encoding="utf-8") as f:
        json.dump(charts, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    os.replace(tmp_charts, "charts.json")
    print(f"📈 charts.json — {len(charts)} graphes (top 30, transitoire)")

    # ── charts/<TICKER>.json — un fichier par fiche ouvrable ────────────────
    # Périmètre : les titres tagués par un thème (par_ticker) UNION le top 30.
    # L'union n'est pas redondante : un titre peut être très bien noté sans
    # appartenir à aucun thème, et sa fiche perdrait son graphe le jour où
    # charts.json sera retiré.
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
