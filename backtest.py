"""
backtest.py — Backtest momentum-only du screener Signal.

Rejoue les 40 points de Momentum (Golden Cross + RSI + Volume + Régression)
sur l'univers Signal US, avec les mêmes règles de portefeuille qu'en prod
(max 20% par titre, 15 positions max, hold 90j, stop-loss R07/R08).

Périmètre : US uniquement (univers + benchmark SPY) pour éviter les
complications de change. Aucun look-ahead bias : à chaque date, seules
les données antérieures sont utilisées pour scorer.

Limitation honnête : 60 % du score Signal (Fondamentaux + Analystes) NON
testé — Yahoo n'expose pas les fondamentaux historiques point-in-time.
Ce backtest mesure uniquement la composante technique.

Usage : python backtest.py
Output : backtest_results.json + console
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import time
from datetime import date, datetime, timedelta
from ta.momentum import RSIIndicator

# Réutilisation du screener pour garantir la cohérence avec la prod
from screener import detect_cross, cross_score, calcul_regression

# Paramètres centralisés (coûts, PFU, VIX, régimes) — Phases 1-3
import config

# ── CONFIG ───────────────────────────────────────────────────────────────────
YEAR_START          = 2019    # début du backtest
YEAR_END            = 2025    # fin (exclusif)
INITIAL_CAPITAL     = 20000.0  # USD pour cohérence avec benchmark US
MAX_POSITIONS       = 15
POIDS_MAX           = 0.20
TOP_N_BUY           = 25      # top N scores éligibles à l'achat
HOLD_DAYS_MIN       = 90
STOP_LOSS_PCT       = -15.0
STOP_LOSS_CATA_PCT  = -25.0
BENCHMARK_TICKER    = "SPY"   # S&P 500 ETF — proxy MSCI USA, USD natif

# Univers US uniquement (filtré depuis screener.UNIVERS — pas de suffixes)
UNIVERS_US = [
    "AAPL","NVDA","MSFT","GOOGL","AMZN","META","AVGO","TSLA","LLY",
    "V","MA","JPM","UNH","XOM","PG","HD","MRK","ABBV","COST",
    "CRM","NFLX","AMD","ORCL","ACN","TMO","ABT","ISRG","GS",
    "BLK","QCOM","TXN","AMAT","NOW","PANW","INTU","AXP","SPGI",
    "HON","ETN","SYK","VRTX","ADI","REGN","MMC","CI","PLD",
    "ADBE","MCD","NEE","PFE","WMT","AMGN",
    "TSM","SE","SONY",
]

# ── FETCH ────────────────────────────────────────────────────────────────────
def fetch_all_history(tickers, start, end):
    """Télécharge tout l'historique en une fois — accès séquentiel par ticker.
    Retourne dict {ticker: DataFrame}."""
    data = {}
    print(f"📥 Téléchargement de {len(tickers)} tickers ({start} → {end})...")
    for i, t in enumerate(tickers):
        try:
            df = yf.Ticker(t).history(start=start, end=end, auto_adjust=True)
            if len(df) > 200:
                data[t] = df
                print(f"  [{i+1}/{len(tickers)}] {t} — {len(df)} jours OK")
            else:
                print(f"  [{i+1}/{len(tickers)}] {t} — IGNORÉ (historique trop court)")
        except Exception as e:
            print(f"  [{i+1}/{len(tickers)}] {t} — ERREUR : {e}")
    return data

# ── SCORING MOMENTUM POINT-IN-TIME ───────────────────────────────────────────
def score_momentum_at(df, target_date, vix=None):
    """Calcule le score momentum (0-45) pour un ticker à une date précise.

    Args:
        df: DataFrame yfinance complet du ticker
        target_date: date pivot (Timestamp), utilise UNIQUEMENT les données ≤ cette date (anti look-ahead)
        vix: niveau VIX à cette date pour le dampener (None = pas de dampener)

    Returns:
        (momentum_dampened_pts, prix_close, val_pts) ou None si données insuffisantes
        - momentum_dampened_pts : 0-45 après application du VIX multiplier
        - val_pts inclus dans le total (cf v2 alignement avec live)
    """
    hist = df[df.index <= target_date]
    if len(hist) < 250:  # min 1 an d'historique
        return None

    close = hist["Close"]
    volume = hist["Volume"]

    # Indicateurs court terme : 2 ans glissants
    close_2y = close.iloc[-504:] if len(close) > 504 else close
    volume_2y = volume.iloc[-504:] if len(volume) > 504 else volume

    try:
        rsi = float(RSIIndicator(close=close_2y, window=14).rsi().iloc[-1])
        if not np.isfinite(rsi):
            return None
    except Exception:
        return None

    cross_info = detect_cross(close_2y, volume_2y)
    cross_pts = cross_score(cross_info, rsi)

    # RSI gradué (10 pts max)
    if 40 <= rsi <= 60:
        rsi_pts = 10
    elif 35 <= rsi <= 65:
        rsi_pts = 5
    else:
        rsi_pts = 0

    # Volume récent vs moyen (5 pts)
    vol_recent = float(volume_2y.tail(20).mean())
    vol_annual = float(volume_2y.mean())
    vol_pts = 5 if vol_recent > vol_annual else 0

    # Régression long terme (5 pts) — la fonction screener applique déjà holdout 20j
    z, _ = calcul_regression(close)
    reg_pts = 5 if -0.5 <= z <= 1.5 else 0

    # Valorisation actuelle (5 pts) — drawdown vs 52w high, aligné avec score_ticker() v2
    close_52w = close.iloc[-252:] if len(close) >= 252 else close
    high_52w  = float(close_52w.max())
    prix_now  = float(close.iloc[-1])
    dd_52w    = (prix_now / high_52w - 1) * 100 if high_52w > 0 else 0
    if   dd_52w >= -3:                          val_pts = 0
    elif -10 <= dd_52w < -3:                    val_pts = 5
    elif -20 <= dd_52w < -10:                   val_pts = 3
    elif -30 <= dd_52w < -20:                   val_pts = 1
    else:                                       val_pts = 0

    momentum_raw = cross_pts + rsi_pts + vol_pts + reg_pts + val_pts

    # Pénalité Death Cross récent (non compensable, appliquée AVANT dampener pour cohérence)
    if cross_info["regime"] == "death":
        d = cross_info["days_since_cross"]
        if d <= 30:
            momentum_raw -= 5
        elif d <= 60:
            momentum_raw -= 3
    momentum_raw = max(0, momentum_raw)

    # VIX dampener (Phase 2)
    vix_mult = config.vix_multiplier(vix)
    momentum_dampened = round(momentum_raw * vix_mult)

    return momentum_dampened, prix_now, val_pts

# ── PORTFOLIO ENGINE ─────────────────────────────────────────────────────────
def get_price_at(df, target_date):
    """Prix de clôture le jour target_date (ou jour ouvré précédent le plus proche)."""
    hist = df[df.index <= target_date]
    if hist.empty:
        return None
    return float(hist["Close"].iloc[-1])

def _close_position(cash, pos, ticker, rebal_date, raison, trades):
    """Ferme une position : frais de vente + PFU sur plus-value, ajoute trade au log.

    Applique la fiscalité française PFU 30% sur la plus-value réalisée.
    Returns: (new_cash, frais_vente, impot_pfu, perte_reportable)
    """
    brut_vente = pos.get("valeur", 0)
    base_fiscale = pos.get("montant_investi", pos.get("valeur", 0))  # brut + frais achat
    r = config.apply_sell_cost_and_tax(brut_vente, base_fiscale)
    cash_recupere   = r["cash_recupere_eur"]   # en USD ici (devise du backtest)
    frais_vente     = r["frais_vente_eur"]
    plus_value      = r["plus_value_eur"]
    impot_pfu       = r["impot_pfu_eur"]
    perte_reportable= r["perte_reportable_eur"]
    new_cash = cash + cash_recupere

    jours = (rebal_date - pos["date_achat"]).days
    trades.append({
        "date":             str(rebal_date.date()),
        "type":             "VENTE",
        "ticker":           ticker,
        "perf":             round(pos.get("perf", 0), 2),
        "raison":           raison,
        "jours":            jours,
        "montant_brut":     round(brut_vente, 2),
        "frais_vente":      round(frais_vente, 4),
        "plus_value":       round(plus_value, 2),
        "impot_pfu":        round(impot_pfu, 2),
        "perte_reportable": round(perte_reportable, 2),
        "cash_recupere":    round(cash_recupere, 2),
    })
    return new_cash, frais_vente, impot_pfu, perte_reportable


def simulate_backtest(data, vix_df=None):
    """Simule la stratégie momentum-only sur l'univers + comparaison benchmark.

    Args:
        data: dict {ticker: DataFrame} de l'univers + benchmark
        vix_df: DataFrame VIX historique (optionnel — si None, pas de dampener appliqué)
    """
    bench_df = data.get(BENCHMARK_TICKER)
    if bench_df is None:
        print(f"❌ Benchmark {BENCHMARK_TICKER} indisponible — abandon")
        return None

    universe_tickers = [t for t in UNIVERS_US if t in data]
    print(f"\n🎯 Univers exploitable : {len(universe_tickers)}/{len(UNIVERS_US)} tickers")

    # VIX point-in-time helper (None si pas de série fournie ou avant 1ère date dispo)
    def vix_at(target_date):
        if vix_df is None or vix_df.empty:
            return None
        hist = vix_df[vix_df.index <= target_date]
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])

    # Dates de rebalancement : tous les lundis dans la fenêtre
    bench_dates = bench_df.index
    rebal_dates = [
        d for d in bench_dates
        if YEAR_START <= d.year < YEAR_END and d.weekday() == 0
    ]
    print(f"📅 {len(rebal_dates)} rebalancements hebdomadaires ({rebal_dates[0].date()} → {rebal_dates[-1].date()})")

    # État du portefeuille
    cash = INITIAL_CAPITAL
    positions = {}  # ticker -> dict(qty, prix_achat, date_achat, montant_investi, ...)
    history = []    # snapshots hebdo
    trades = []     # historique des ordres (avec coûts + PFU)
    # Compteurs cumulatifs frais + fiscalité (Phase 1)
    total_frais_cum   = 0.0
    total_impots_cum  = 0.0
    total_pertes_rep  = 0.0

    # Valeur initiale du benchmark pour normalisation
    bench_initial = get_price_at(bench_df, rebal_dates[0])
    bench_units = INITIAL_CAPITAL / bench_initial  # achat virtuel buy & hold

    for i, rebal_date in enumerate(rebal_dates):
        # ── Mise à jour des prix actuels
        for ticker, pos in list(positions.items()):
            prix = get_price_at(data[ticker], rebal_date)
            if prix is not None:
                pos["prix_actuel"] = prix
                pos["valeur"] = prix * pos["qty"]
                pos["perf"] = (prix - pos["prix_achat"]) / pos["prix_achat"] * 100

        capital = cash + sum(p.get("valeur", 0) for p in positions.values())

        # ── R08 — Stop-loss catastrophe (sans condition de durée)
        for ticker in list(positions.keys()):
            pos = positions[ticker]
            if pos.get("perf", 0) <= STOP_LOSS_CATA_PCT:
                cash, frais_v, impot_v, perte_rep = _close_position(cash, pos, ticker, rebal_date, "R08 catastrophe", trades)
                total_frais_cum  += frais_v
                total_impots_cum += impot_v
                total_pertes_rep += perte_rep
                del positions[ticker]

        # ── R07 — Stop-loss standard (≥ 90j)
        for ticker in list(positions.keys()):
            pos = positions[ticker]
            jours = (rebal_date - pos["date_achat"]).days
            if pos.get("perf", 0) <= STOP_LOSS_PCT and jours >= HOLD_DAYS_MIN:
                cash, frais_v, impot_v, perte_rep = _close_position(cash, pos, ticker, rebal_date, "R07 stop-loss", trades)
                total_frais_cum  += frais_v
                total_impots_cum += impot_v
                total_pertes_rep += perte_rep
                del positions[ticker]

        # ── Score tous les tickers de l'univers à cette date (avec VIX dampener si activé)
        vix_now = vix_at(rebal_date)
        scores = []
        for ticker in universe_tickers:
            r = score_momentum_at(data[ticker], rebal_date, vix=vix_now)
            if r is not None:
                score, prix, _val_pts = r
                if prix > 0:
                    scores.append((ticker, score, prix))
        scores.sort(key=lambda x: -x[1])
        top_buy = scores[:TOP_N_BUY]

        # ── Vente : titres qui ne sont plus dans le top et détenus ≥ 90j
        top_tickers = {t for t, _, _ in top_buy}
        for ticker in list(positions.keys()):
            pos = positions[ticker]
            jours = (rebal_date - pos["date_achat"]).days
            # Vente si sorti du top + détenu ≥ 90j (Règle 01 simulée)
            if ticker not in top_tickers and jours >= HOLD_DAYS_MIN:
                cash, frais_v, impot_v, perte_rep = _close_position(cash, pos, ticker, rebal_date, "rotation", trades)
                total_frais_cum  += frais_v
                total_impots_cum += impot_v
                total_pertes_rep += perte_rep
                del positions[ticker]

        # ── Achat : top scores non détenus, jusqu'à MAX_POSITIONS
        capital = cash + sum(p.get("valeur", 0) for p in positions.values())
        slots = MAX_POSITIONS - len(positions)
        if slots > 0 and cash > 100:
            candidates = [(t, s, p) for t, s, p in top_buy if t not in positions]
            achats = candidates[:slots]
            if achats:
                budget_par_titre = min(
                    cash / len(achats),
                    capital * POIDS_MAX,
                )
                for ticker, score, prix in achats:
                    if budget_par_titre < 100 or prix <= 0:
                        continue
                    # Le budget réservé doit inclure les frais (= cash débité)
                    budget_apres_frais = budget_par_titre / (1 + config.TRANSACTION_COST_BPS / 10000.0)
                    qty = int(budget_apres_frais / prix)
                    if qty < 1:
                        continue
                    brut = qty * prix
                    cash_debite, frais_achat = config.apply_buy_cost(brut)
                    if cash_debite > cash:
                        continue
                    cash -= cash_debite
                    total_frais_cum += frais_achat
                    positions[ticker] = {
                        "qty": qty, "prix_achat": prix, "prix_actuel": prix,
                        "valeur": brut,                   # valeur de marché (sans frais)
                        "montant_investi": cash_debite,   # base fiscale (brut + frais achat)
                        "frais_achat": frais_achat,
                        "perf": 0.0,
                        "date_achat": rebal_date, "score_entree": score,
                    }
                    trades.append({
                        "date": str(rebal_date.date()), "type": "ACHAT",
                        "ticker": ticker, "score": score, "prix": round(prix, 2),
                        "qty": qty, "montant_brut": round(brut, 2),
                        "frais_achat": round(frais_achat, 4),
                        "cash_debite": round(cash_debite, 2),
                    })

        # ── Snapshot
        total_value = cash + sum(p.get("valeur", 0) for p in positions.values())
        bench_value = bench_units * get_price_at(bench_df, rebal_date)
        history.append({
            "date": str(rebal_date.date()),
            "portfolio": round(total_value, 2),
            "benchmark": round(bench_value, 2),
            "n_positions": len(positions),
            "cash": round(cash, 2),
            "total_frais_cum":  round(total_frais_cum, 2),
            "total_impots_cum": round(total_impots_cum, 2),
            "total_pertes_rep": round(total_pertes_rep, 2),
            "vix":              round(vix_now, 2) if vix_now is not None else None,
        })

        if i % 26 == 0 or i == len(rebal_dates) - 1:
            perf_p = (total_value / INITIAL_CAPITAL - 1) * 100
            perf_b = (bench_value / INITIAL_CAPITAL - 1) * 100
            print(f"  {rebal_date.date()} | Portfolio ${total_value:>9,.0f} ({perf_p:+5.1f}%) "
                  f"| {BENCHMARK_TICKER} ${bench_value:>9,.0f} ({perf_b:+5.1f}%) "
                  f"| α={perf_p-perf_b:+5.1f}pp | {len(positions)} pos")

    # ── Liquidation virtuelle finale (Option A — comparaison équitable post-PFU) ─
    # Simule la sortie totale des positions ouvertes au dernier prix pour
    # connaître le cash réellement disponible après frais + PFU sur plus-values
    # latentes. Permet de comparer apples-to-apples avec un SPY également liquidé.
    cash_apres_liquidation = cash
    pertes_liquidation     = 0.0
    impots_liquidation     = 0.0
    frais_liquidation      = 0.0
    for ticker, pos in list(positions.items()):
        brut = pos.get("valeur", 0)
        base = pos.get("montant_investi", brut)
        r = config.apply_sell_cost_and_tax(brut, base)
        cash_apres_liquidation += r["cash_recupere_eur"]
        frais_liquidation      += r["frais_vente_eur"]
        impots_liquidation     += r["impot_pfu_eur"]
        pertes_liquidation     += r["perte_reportable_eur"]

    return {
        "history": history,
        "trades": trades,
        "final_positions": [
            {"ticker": t, **{k: (str(v) if isinstance(v, datetime) else v) for k, v in p.items()}}
            for t, p in positions.items()
        ],
        "total_frais_cum":   round(total_frais_cum, 2),
        "total_impots_cum":  round(total_impots_cum, 2),
        "total_pertes_rep":  round(total_pertes_rep, 2),
        # Option A — valeurs si on liquidait tout à la dernière date du backtest
        "portfolio_post_liquidation":  round(cash_apres_liquidation, 2),
        "frais_liquidation_virtuelle": round(frais_liquidation, 2),
        "impots_liquidation_virtuelle": round(impots_liquidation, 2),
        "pertes_liquidation_virtuelle": round(pertes_liquidation, 2),
    }

# ── MÉTRIQUES ────────────────────────────────────────────────────────────────
def compute_metrics(history, trades, result=None):
    """Calcule les métriques de performance standard.

    Si `result` est fourni, ajoute aussi les métriques post-liquidation (Option A) :
    comparaison équitable Signal vs SPY après application du PFU 30% sur les
    plus-values (latentes côté SPY buy-and-hold, latentes côté Signal sur les
    positions ouvertes).
    """
    if not history:
        return {}
    p_values = np.array([h["portfolio"] for h in history])
    b_values = np.array([h["benchmark"] for h in history])

    # Returns weekly
    p_returns = np.diff(p_values) / p_values[:-1]
    b_returns = np.diff(b_values) / b_values[:-1]

    # Total return
    p_total = (p_values[-1] / p_values[0] - 1) * 100
    b_total = (b_values[-1] / b_values[0] - 1) * 100

    # Annualized (52 weeks)
    n_weeks = len(history)
    n_years = n_weeks / 52
    p_cagr = ((p_values[-1] / p_values[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    b_cagr = ((b_values[-1] / b_values[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0

    # Volatility (annualized)
    p_vol = float(np.std(p_returns, ddof=1) * np.sqrt(52) * 100) if len(p_returns) > 1 else 0
    b_vol = float(np.std(b_returns, ddof=1) * np.sqrt(52) * 100) if len(b_returns) > 1 else 0

    # Sharpe (rf=0 simplification)
    p_sharpe = (p_cagr / p_vol) if p_vol > 0 else 0
    b_sharpe = (b_cagr / b_vol) if b_vol > 0 else 0

    # Max drawdown
    def max_dd(values):
        peaks = np.maximum.accumulate(values)
        dd = (values - peaks) / peaks * 100
        return float(dd.min())
    p_mdd = max_dd(p_values)
    b_mdd = max_dd(b_values)

    # Trades stats
    ventes = [t for t in trades if t["type"] == "VENTE" and "perf" in t]
    n_trades = len(ventes)
    if n_trades > 0:
        wins = [t for t in ventes if t["perf"] > 0]
        win_rate = len(wins) / n_trades * 100
        avg_perf = float(np.mean([t["perf"] for t in ventes]))
        avg_winner = float(np.mean([t["perf"] for t in wins])) if wins else 0
        losers = [t for t in ventes if t["perf"] <= 0]
        avg_loser = float(np.mean([t["perf"] for t in losers])) if losers else 0
    else:
        win_rate = avg_perf = avg_winner = avg_loser = 0

    # Deflated Sharpe (Bailey-Lopez de Prado 2014) — discount le Sharpe par le nombre
    # de trials testés implicitement (5 signaux momentum + pondérations + seuils RSI/reg etc.)
    # Formule simplifiée : DSR = SR × (1 - (skewness_correction))
    # Approximation pratique : DSR ≈ SR / √(1 + 0.5×N_trials/N_weeks) où N_trials ≈ 10 (5 signaux × 2 réglages chacun)
    n_trials_implicit = 10
    deflator = np.sqrt(1 + 0.5 * n_trials_implicit / max(n_weeks, 1))
    deflated_sharpe = p_sharpe / deflator if deflator > 0 else 0

    # ── Option A : métriques post-liquidation (comparaison équitable Signal vs SPY) ──
    # Signal paye PFU à chaque vente pendant la période ; SPY (buy-and-hold) ne paye
    # rien dans le backtest courant. Mais si l'investisseur SPY voulait sortir son
    # cash à la fin, il devrait payer PFU sur ses plus-values latentes. Idem pour
    # Signal sur ses positions encore ouvertes en fin de période.
    portfolio_post_liq = None
    benchmark_post_liq = None
    alpha_post_liq_total = None
    alpha_post_liq_cagr  = None
    if result is not None and "portfolio_post_liquidation" in result:
        portfolio_post_liq = result["portfolio_post_liquidation"]
        # Benchmark : appliquer PFU sur la plus-value SPY totale (frais négligeable pour ETF liquide)
        b_pl_brut = b_values[-1]
        bench_dict = config.apply_sell_cost_and_tax(b_pl_brut, INITIAL_CAPITAL)
        benchmark_post_liq = bench_dict["cash_recupere_eur"]
        # Recompute returns post-liquidation
        p_total_pl = (portfolio_post_liq / INITIAL_CAPITAL - 1) * 100
        b_total_pl = (benchmark_post_liq / INITIAL_CAPITAL - 1) * 100
        alpha_post_liq_total = p_total_pl - b_total_pl
        p_cagr_pl = ((portfolio_post_liq / INITIAL_CAPITAL) ** (1 / max(n_years, 0.01)) - 1) * 100 if portfolio_post_liq > 0 else 0
        b_cagr_pl = ((benchmark_post_liq / INITIAL_CAPITAL) ** (1 / max(n_years, 0.01)) - 1) * 100 if benchmark_post_liq > 0 else 0
        alpha_post_liq_cagr = p_cagr_pl - b_cagr_pl

    return {
        "n_weeks":          n_weeks,
        "n_years":          round(n_years, 2),
        "portfolio_total":  round(p_total, 2),
        "benchmark_total":  round(b_total, 2),
        "alpha_total":      round(p_total - b_total, 2),
        "portfolio_cagr":   round(p_cagr, 2),
        "benchmark_cagr":   round(b_cagr, 2),
        "alpha_cagr":       round(p_cagr - b_cagr, 2),
        "portfolio_vol":    round(p_vol, 2),
        "benchmark_vol":    round(b_vol, 2),
        "portfolio_sharpe": round(p_sharpe, 2),
        "benchmark_sharpe": round(b_sharpe, 2),
        "deflated_sharpe":  round(deflated_sharpe, 2),  # Bailey-Lopez de Prado, anti-data-mining
        "portfolio_mdd":    round(p_mdd, 2),
        "benchmark_mdd":    round(b_mdd, 2),
        "n_trades":         n_trades,
        "win_rate":         round(win_rate, 1),
        "avg_perf":         round(avg_perf, 2),
        "avg_winner":       round(avg_winner, 2),
        "avg_loser":        round(avg_loser, 2),
        # Option A — métriques post-liquidation virtuelle (comparaison équitable PFU)
        "portfolio_post_liq":  round(portfolio_post_liq, 2) if portfolio_post_liq is not None else None,
        "benchmark_post_liq":  round(benchmark_post_liq, 2) if benchmark_post_liq is not None else None,
        "alpha_post_liq_total":round(alpha_post_liq_total, 2) if alpha_post_liq_total is not None else None,
        "alpha_post_liq_cagr": round(alpha_post_liq_cagr, 2) if alpha_post_liq_cagr is not None else None,
    }


def compute_regime_metrics(history, trades):
    """Décompose les métriques par régime de marché (cf config.REGIME_DEFINITIONS).

    Pour chaque régime, calcule : n_weeks, portfolio_total, benchmark_total,
    alpha, Sharpe, max DD, n_trades. Permet de valider que l'edge tient
    en bear/stress (pas seulement en bull).
    """
    if not history:
        return {}
    regimes_out = []
    for rg in config.REGIME_DEFINITIONS:
        d_from = rg["from"]
        d_to   = rg["to"]
        # Filtre history pour ce régime
        h_rg = [h for h in history if d_from <= h["date"] <= d_to]
        if len(h_rg) < 4:  # min 4 semaines pour être significatif
            continue
        p = np.array([h["portfolio"] for h in h_rg])
        b = np.array([h["benchmark"] for h in h_rg])
        p_ret = np.diff(p) / p[:-1]
        b_ret = np.diff(b) / b[:-1]
        p_total = (p[-1] / p[0] - 1) * 100
        b_total = (b[-1] / b[0] - 1) * 100
        p_vol = float(np.std(p_ret, ddof=1) * np.sqrt(52) * 100) if len(p_ret) > 1 else 0
        n_weeks_rg = len(h_rg)
        n_years_rg = max(n_weeks_rg / 52, 0.05)
        p_cagr = ((p[-1] / p[0]) ** (1 / n_years_rg) - 1) * 100 if p[0] > 0 else 0
        b_cagr = ((b[-1] / b[0]) ** (1 / n_years_rg) - 1) * 100 if b[0] > 0 else 0
        p_sharpe = (p_cagr / p_vol) if p_vol > 0 else 0
        # MDD intra-régime
        if len(p) > 0:
            peaks = np.maximum.accumulate(p)
            dd_series = (p - peaks) / peaks * 100
            p_mdd = float(np.min(dd_series))
        else:
            p_mdd = 0.0
        # Trades dans ce régime
        n_tr_rg = sum(1 for t in trades if t.get("type") == "VENTE" and d_from <= t["date"] <= d_to)
        regimes_out.append({
            "label":           rg["label"],
            "from":            d_from,
            "to":              d_to,
            "desc":            rg["desc"],
            "n_weeks":         n_weeks_rg,
            "portfolio_total": round(p_total, 2),
            "benchmark_total": round(b_total, 2),
            "alpha":           round(p_total - b_total, 2),
            "portfolio_cagr":  round(p_cagr, 2),
            "benchmark_cagr":  round(b_cagr, 2),
            "alpha_cagr":      round(p_cagr - b_cagr, 2),
            "portfolio_vol":   round(p_vol, 2),
            "portfolio_sharpe":round(p_sharpe, 2),
            "portfolio_mdd":   round(p_mdd, 2),
            "n_trades":        n_tr_rg,
        })
    return regimes_out

def print_report(metrics, history, result=None, regime_metrics=None):
    print("\n" + "=" * 72)
    print(f"📊 BACKTEST RESULTS — Momentum-only ({YEAR_START} → {YEAR_END})")
    print(f"   VIX dampener: {'ON' if config.VIX_DAMPENER_ENABLED else 'OFF'} | "
          f"Costs: {config.TRANSACTION_COST_BPS} bps one-way | PFU: {config.PFU_RATE*100:.0f}%")
    print("=" * 72)
    print(f"  Période               : {metrics['n_years']} ans ({metrics['n_weeks']} semaines)")
    print(f"  Capital initial       : ${INITIAL_CAPITAL:,.0f}")
    print()
    print(f"  Portfolio total       : {metrics['portfolio_total']:+8.2f}%   (CAGR {metrics['portfolio_cagr']:+5.2f}%)")
    print(f"  {BENCHMARK_TICKER} total              : {metrics['benchmark_total']:+8.2f}%   (CAGR {metrics['benchmark_cagr']:+5.2f}%)")
    print(f"  ALPHA                 : {metrics['alpha_total']:+8.2f}pp  (CAGR {metrics['alpha_cagr']:+5.2f}pp)")
    print()
    print(f"  Volatilité Portfolio  : {metrics['portfolio_vol']:5.2f}%   (annualisée)")
    print(f"  Volatilité Benchmark  : {metrics['benchmark_vol']:5.2f}%")
    print(f"  Sharpe Portfolio      : {metrics['portfolio_sharpe']:5.2f}")
    print(f"  Sharpe Benchmark      : {metrics['benchmark_sharpe']:5.2f}")
    print(f"  Deflated Sharpe       : {metrics['deflated_sharpe']:5.2f}   (Bailey-LdP, ajusté trials)")
    print()
    print(f"  Max Drawdown Portfolio: {metrics['portfolio_mdd']:+8.2f}%")
    print(f"  Max Drawdown Benchmark: {metrics['benchmark_mdd']:+8.2f}%")
    print()
    print(f"  Trades fermés         : {metrics['n_trades']}")
    print(f"  Win rate              : {metrics['win_rate']:5.1f}%")
    print(f"  Perf moy / trade      : {metrics['avg_perf']:+5.2f}%   (gagnants {metrics['avg_winner']:+.1f}% / perdants {metrics['avg_loser']:+.1f}%)")
    print()
    if result:
        print(f"  Frais cumulés         : ${result.get('total_frais_cum',0):,.2f}")
        print(f"  Impôts PFU cumulés    : ${result.get('total_impots_cum',0):,.2f}")
        print(f"  Pertes reportables    : ${result.get('total_pertes_rep',0):,.2f}  (crédit fiscal théorique = ${result.get('total_pertes_rep',0)*0.30:,.2f})")
    print("=" * 72)

    # ── Option A : comparaison équitable post-liquidation ──
    if metrics.get("portfolio_post_liq") is not None:
        print(f"\n💰 COMPARAISON ÉQUITABLE POST-LIQUIDATION (PFU 30% appliqué aux deux)")
        print("-" * 72)
        p_pl = metrics["portfolio_post_liq"]
        b_pl = metrics["benchmark_post_liq"]
        ap_t = metrics["alpha_post_liq_total"]
        ap_c = metrics["alpha_post_liq_cagr"]
        n_years = metrics["n_years"]
        print(f"  Portfolio si liquidé aujourd'hui    : ${p_pl:>10,.0f}  ({(p_pl/INITIAL_CAPITAL-1)*100:+.2f}% total, CAGR {(((p_pl/INITIAL_CAPITAL)**(1/max(n_years,0.01))-1)*100):+.2f}%)")
        print(f"  {BENCHMARK_TICKER} si liquidé aujourd'hui          : ${b_pl:>10,.0f}  ({(b_pl/INITIAL_CAPITAL-1)*100:+.2f}% total, CAGR {(((b_pl/INITIAL_CAPITAL)**(1/max(n_years,0.01))-1)*100):+.2f}%)")
        print(f"  ALPHA équitable                     : {ap_t:+8.2f}pp total / {ap_c:+5.2f}pp CAGR")
        if result:
            print(f"  Liquidation virtuelle additionnelle : ${result.get('frais_liquidation_virtuelle',0):,.2f} frais + ${result.get('impots_liquidation_virtuelle',0):,.2f} PFU sur plus-values latentes")
        print("-" * 72)

    # ── Décomposition par régime
    if regime_metrics:
        print(f"\n📅 PERFORMANCE PAR RÉGIME DE MARCHÉ")
        print("-" * 72)
        print(f"  {'Régime':<22s} {'Période':<22s} {'Alpha':>10s} {'Sharpe':>8s} {'MDD':>8s} {'N':>4s}")
        for rm in regime_metrics:
            period_str = f"{rm['from']} → {rm['to']}"
            print(f"  {rm['label']:<22s} {period_str:<22s} {rm['alpha']:>+8.2f}pp {rm['portfolio_sharpe']:>+7.2f} {rm['portfolio_mdd']:>+7.2f}% {rm['n_trades']:>4d}")
        print("-" * 72)

    # Verdict
    alpha_cagr = metrics["alpha_cagr"]
    sharpe_diff = metrics["portfolio_sharpe"] - metrics["benchmark_sharpe"]
    print("\n🎯 VERDICT")
    if alpha_cagr > 1.0 and sharpe_diff > 0:
        print(f"  ✅ Le momentum produit de l'alpha : +{alpha_cagr:.2f}pp/an avec Sharpe supérieur (+{sharpe_diff:.2f}).")
        print(f"     Le scoring technique seul (40/100) bat {BENCHMARK_TICKER} sur la période.")
    elif abs(alpha_cagr) < 1.0:
        print(f"  ⚠️  Performance équivalente au benchmark (alpha {alpha_cagr:+.2f}pp/an).")
        print(f"     Le scoring n'apporte ni ne détruit de valeur — un ETF ferait pareil.")
    else:
        print(f"  ❌ Sous-performance : {alpha_cagr:+.2f}pp/an vs {BENCHMARK_TICKER}.")
        print(f"     Le scoring momentum seul détruit de la valeur sur la période. À réviser.")
    print()

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Signal backtest — Phase 3 (régimes + coûts + PFU + VIX)")
    parser.add_argument(
        "--variant",
        choices=["baseline", "costs_only", "costs_vix"],
        default="costs_vix",
        help="baseline = sans frais ni VIX | costs_only = +coûts +PFU | costs_vix = +coûts +PFU +VIX dampener (défaut)"
    )
    parser.add_argument("--output", default=None, help="Chemin du JSON output (défaut: backtest_results_<variant>.json)")
    args = parser.parse_args()

    # Configure les overrides selon le variant
    if args.variant == "baseline":
        config.TRANSACTION_COST_BPS = 0.0
        config.PFU_RATE              = 0.0
        config.VIX_DAMPENER_ENABLED  = False
        print(f"🧪 VARIANT: baseline (no costs, no PFU, no VIX dampener) — référence historique")
    elif args.variant == "costs_only":
        # Garde les valeurs de config.py par défaut (15 bps round-trip, PFU 30%)
        config.VIX_DAMPENER_ENABLED  = False
        print(f"🧪 VARIANT: costs_only (frais {config.TRANSACTION_COST_BPS}bps one-way + PFU {config.PFU_RATE*100:.0f}%, no VIX)")
    else:  # costs_vix
        config.VIX_DAMPENER_ENABLED  = True
        print(f"🧪 VARIANT: costs_vix (frais {config.TRANSACTION_COST_BPS}bps + PFU {config.PFU_RATE*100:.0f}% + VIX dampener)")

    output_path = args.output or f"backtest_results_{args.variant}.json"

    t0 = time.time()
    start_str = f"{YEAR_START - 2}-01-01"  # buffer 2 ans pour MM200 + régression
    end_str = f"{YEAR_END}-01-01"

    data = fetch_all_history(UNIVERS_US + [BENCHMARK_TICKER], start_str, end_str)
    if not data:
        print("❌ Aucune donnée récupérée")
        return

    # VIX historique (Phase 2) — pour appliquer le dampener point-in-time
    vix_df = None
    if config.VIX_DAMPENER_ENABLED:
        print(f"\n📥 Téléchargement historique ^VIX pour dampener point-in-time...")
        try:
            vix_df = yf.Ticker("^VIX").history(start=start_str, end=end_str, auto_adjust=False)
            if not vix_df.empty:
                print(f"  ✓ ^VIX {len(vix_df)} jours ({vix_df.index[0].date()} → {vix_df.index[-1].date()})")
                vmean = float(vix_df["Close"].mean())
                vmax  = float(vix_df["Close"].max())
                vmin  = float(vix_df["Close"].min())
                print(f"  ✓ Distribution : min {vmin:.1f} / mean {vmean:.1f} / max {vmax:.1f}")
            else:
                print(f"  ⚠️  ^VIX history vide — backtest sans dampener")
                vix_df = None
        except Exception as e:
            print(f"  ⚠️  ^VIX fetch failed ({e}) — backtest sans dampener")

    print(f"\n⚙️  Simulation rebalancements hebdomadaires...")
    result = simulate_backtest(data, vix_df=vix_df)
    if not result:
        return

    metrics = compute_metrics(result["history"], result["trades"], result=result)
    regime_metrics = compute_regime_metrics(result["history"], result["trades"])
    print_report(metrics, result["history"], result=result, regime_metrics=regime_metrics)

    output = {
        "config": {
            "year_start": YEAR_START, "year_end": YEAR_END,
            "initial_capital": INITIAL_CAPITAL, "max_positions": MAX_POSITIONS,
            "poids_max": POIDS_MAX, "top_n_buy": TOP_N_BUY,
            "hold_days_min": HOLD_DAYS_MIN, "stop_loss_pct": STOP_LOSS_PCT,
            "stop_loss_cata_pct": STOP_LOSS_CATA_PCT,
            "benchmark": BENCHMARK_TICKER, "universe_size": len(UNIVERS_US),
            "transaction_cost_bps":   config.TRANSACTION_COST_BPS,
            "pfu_rate":               config.PFU_RATE,
            "vix_dampener_enabled":   config.VIX_DAMPENER_ENABLED,
            "vix_dampener_intercept": config.VIX_DAMPENER_INTERCEPT,
            "vix_dampener_slope":     config.VIX_DAMPENER_SLOPE,
            "vix_dampener_min":       config.VIX_DAMPENER_MIN,
        },
        "metrics": metrics,
        "regime_metrics": regime_metrics,
        "totals": {
            "total_frais_cum":  result.get("total_frais_cum", 0),
            "total_impots_cum": result.get("total_impots_cum", 0),
            "total_pertes_rep": result.get("total_pertes_rep", 0),
        },
        "history": result["history"],
        "trades": result["trades"],
        "final_positions": result["final_positions"],
        "generated_at": str(date.today()),
        "duration_seconds": round(time.time() - t0, 1),
    }
    output["variant"] = args.variant
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"💾 Résultats détaillés → {output_path}")
    print(f"⏱️  Durée totale : {output['duration_seconds']}s")

if __name__ == "__main__":
    main()
