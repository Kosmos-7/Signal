"""
backtest_compare.py — Comparaison des 3 variants de backtest (Phase 3).

Lance séquentiellement :
  1. baseline   : screener brut, sans frais, sans VIX dampener (référence historique)
  2. costs_only : ajoute frais transaction + PFU 30% (mesure l'impact friction)
  3. costs_vix  : ajoute VIX dampener (mesure la défensivité régime)

Puis affiche une table comparative et le verdict go/no-go pour la Phase 4.

Critères go/no-go (cumulés sur 2019-2024) :
  G1. Alpha CAGR net (costs_vix) > +1pp/an
  G2. Sharpe net (costs_vix) > 0.5
  G3. Drawdown bear 2022 (costs_vix) < -20% (en valeur absolue moins pire)
  G4. Deflated Sharpe (costs_vix) > 0.3
  G5. VIX dampener IMPROVES Sharpe vs costs_only (sinon il n'apporte rien)

Si G1-G5 tous OK → GO Phase 4 (univers élargi)
Sinon → recalibrer ou abandonner Phase 2

Usage : python backtest_compare.py
"""

import subprocess
import sys
import json
import os
from pathlib import Path


VARIANTS = ["baseline", "costs_only", "costs_vix"]


def run_variant(variant):
    """Lance backtest.py --variant=X et attend la fin. Retourne True si succès."""
    print(f"\n{'=' * 72}")
    print(f"▸ LAUNCHING variant: {variant}")
    print(f"{'=' * 72}")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "backtest.py", "--variant", variant],
        cwd=Path(__file__).parent,
    )
    return result.returncode == 0


def load_variant(variant):
    path = f"backtest_results_{variant}.json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt(v, suffix="", w=8, prec=2):
    if v is None:
        return f"{'—':>{w}s}"
    s = f"{v:+.{prec}f}{suffix}"
    return f"{s:>{w}s}"


def print_comparison_table(results):
    """Tableau comparatif des 3 variants."""
    print("\n\n" + "=" * 84)
    print("📊 COMPARAISON DES 3 VARIANTS")
    print("=" * 84)
    print()

    rows = [
        ("Total return",                "portfolio_total",       "%"),
        ("CAGR",                        "portfolio_cagr",        "%"),
        ("Alpha vs SPY (total)",        "alpha_total",           "pp"),
        ("Alpha vs SPY (CAGR)",         "alpha_cagr",            "pp"),
        ("→ Alpha post-liq (total)",    "alpha_post_liq_total",  "pp"),
        ("→ Alpha post-liq (CAGR)",     "alpha_post_liq_cagr",   "pp"),
        ("Sharpe",                      "portfolio_sharpe",      ""),
        ("Deflated Sharpe",             "deflated_sharpe",       ""),
        ("Max DD",                      "portfolio_mdd",         "%"),
        ("Volatilité ann.",             "portfolio_vol",         "%"),
        ("# trades",                    "n_trades",              ""),
        ("Win rate",                    "win_rate",              "%"),
    ]

    # Header
    print(f"  {'Métrique':<22s} {'baseline':>14s} {'costs_only':>14s} {'costs_vix':>14s}")
    print(f"  {'-' * 22:<22s} {'-' * 14:>14s} {'-' * 14:>14s} {'-' * 14:>14s}")
    for label, key, suffix in rows:
        vals = []
        for v in VARIANTS:
            r = results.get(v)
            if r is None:
                vals.append(None)
            else:
                vals.append(r.get("metrics", {}).get(key))
        line = f"  {label:<22s} "
        for v in vals:
            line += fmt(v, suffix, w=14)
            line += " "
        print(line)

    # Totals (frais, impôts, pertes reportables)
    print()
    print(f"  {'Friction':<22s} {'baseline':>14s} {'costs_only':>14s} {'costs_vix':>14s}")
    print(f"  {'-' * 22:<22s} {'-' * 14:>14s} {'-' * 14:>14s} {'-' * 14:>14s}")
    for label, key in [
        ("Frais cumulés ($)", "total_frais_cum"),
        ("Impôts PFU ($)",    "total_impots_cum"),
        ("Pertes report. ($)","total_pertes_rep"),
    ]:
        vals = [results.get(v, {}).get("totals", {}).get(key) for v in VARIANTS]
        line = f"  {label:<22s} "
        for v in vals:
            line += fmt(v, "", w=14, prec=2) if v is not None else f"{'—':>14s}"
            line += " "
        print(line)

    # Régimes — focus sur bear_2022 et covid_crash
    print()
    print(f"  {'Régime alpha (pp)':<22s} {'baseline':>14s} {'costs_only':>14s} {'costs_vix':>14s}")
    print(f"  {'-' * 22:<22s} {'-' * 14:>14s} {'-' * 14:>14s} {'-' * 14:>14s}")
    all_regime_labels = set()
    for v in VARIANTS:
        r = results.get(v)
        if r:
            for rm in r.get("regime_metrics", []):
                all_regime_labels.add(rm["label"])
    for rl in sorted(all_regime_labels):
        line = f"  {rl:<22s} "
        for v in VARIANTS:
            r = results.get(v)
            rm = next((x for x in (r.get("regime_metrics", []) if r else []) if x["label"] == rl), None)
            if rm:
                line += fmt(rm.get("alpha"), "pp", w=14)
            else:
                line += f"{'—':>14s}"
            line += " "
        print(line)

    print()
    print(f"  {'Régime DD max (%)':<22s} {'baseline':>14s} {'costs_only':>14s} {'costs_vix':>14s}")
    print(f"  {'-' * 22:<22s} {'-' * 14:>14s} {'-' * 14:>14s} {'-' * 14:>14s}")
    for rl in sorted(all_regime_labels):
        line = f"  {rl:<22s} "
        for v in VARIANTS:
            r = results.get(v)
            rm = next((x for x in (r.get("regime_metrics", []) if r else []) if x["label"] == rl), None)
            if rm:
                line += fmt(rm.get("portfolio_mdd"), "%", w=14)
            else:
                line += f"{'—':>14s}"
            line += " "
        print(line)


def verdict(results):
    """Évalue les critères go/no-go pour Phase 4."""
    print("\n\n" + "=" * 72)
    print("🎯 VERDICT — Critères go/no-go Phase 4 (univers élargi)")
    print("=" * 72)

    cvx = results.get("costs_vix")
    cos = results.get("costs_only")
    if not cvx or not cos:
        print("  ❌ Backtest costs_vix ou costs_only manquant — verdict impossible")
        return

    m_cvx = cvx.get("metrics", {})
    m_cos = cos.get("metrics", {})

    # G1 utilise l'alpha post-liquidation (Option A — comparaison équitable PFU des deux côtés)
    alpha_eq_cagr  = m_cvx.get("alpha_post_liq_cagr")
    alpha_eq_total = m_cvx.get("alpha_post_liq_total")
    sharpe_net     = m_cvx.get("portfolio_sharpe", 0)
    deflated       = m_cvx.get("deflated_sharpe", 0)

    # Drawdown sur bear_2022
    bear_rm_cvx = next((rm for rm in cvx.get("regime_metrics", []) if rm["label"] == "bear_2022"), None)
    dd_bear_cvx = bear_rm_cvx.get("portfolio_mdd") if bear_rm_cvx else None

    # VIX dampener doit IMPROVER Sharpe vs costs_only
    sharpe_cos = m_cos.get("portfolio_sharpe", 0)
    vix_aide   = sharpe_net > sharpe_cos + 0.01

    checks = [
        ("G1. Alpha CAGR équitable > +1pp/an",   alpha_eq_cagr  if alpha_eq_cagr  is not None else "?", alpha_eq_cagr is not None and alpha_eq_cagr > 1.0),
        ("G2. Sharpe net > 0.5",                 sharpe_net, sharpe_net > 0.5),
        ("G3. DD bear 2022 > -20%",              dd_bear_cvx if dd_bear_cvx is not None else None, (dd_bear_cvx is not None and dd_bear_cvx > -20)),
        ("G4. Deflated Sharpe > 0.3",            deflated, deflated > 0.3),
        ("G5. VIX dampener améliore Sharpe",     f"{sharpe_cos:.2f} → {sharpe_net:.2f}", vix_aide),
    ]
    all_ok = True
    for label, value, ok in checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {label:<40s} : {value}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  🟢 GO Phase 4 — l'edge tient sous coûts/PFU, le VIX dampener améliore la résilience.")
    else:
        print("  🟡 NO-GO — au moins un critère manque. Options :")
        print("     - Recalibrer les paramètres VIX (intercept/slope/min)")
        print("     - Réviser les pondérations 45/50/5")
        print("     - Investiguer pourquoi alpha s'effondre sous coûts (turnover trop élevé ?)")


def main():
    results = {}
    for v in VARIANTS:
        if not run_variant(v):
            print(f"❌ Variant {v} a échoué")
            return
        results[v] = load_variant(v)

    print_comparison_table(results)
    verdict(results)


if __name__ == "__main__":
    main()
