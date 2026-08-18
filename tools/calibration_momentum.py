"""Calibration du bloc momentum (note v4.1, recomposé le 17/08/2026).

Mesure la distribution des intrants des quatre critères du bloc m sur
l'univers, pour vérifier — ou re-fixer, décision propriétaire — les bornes
figées dans note_v4.py :

    momentum  : cloche(mom_ratio, −1,5, 0,3, 2,0, 3,5)   ≈ p5/p35/p85/p97
    sommet    : rampe(drawdown_52w_pct, −40, −5)          ≈ p10/p85
    position  : cloche z inchangée, garde fenêtre ≥ 1260 séances
    dynamique : rampe(pente_mm21_pct, −3,5, +4,5)         ≈ p10/p90

et les seuils de raison_sortie (screener.py, « quasi-nul » < 4,
« dégradé » < 7), calibrés sur une moyenne de bloc ~10.

Deux sources :

    python3 tools/calibration_momentum.py --source yfinance
        La référence : cours QUOTIDIENS de tout l'univers déclaré, passés
        dans les fonctions de PRODUCTION (screener.calcul_momentum_intrants).
        Nécessite le réseau et les dépendances du screener.

    python3 tools/calibration_momentum.py --source charts
        Approximation hors ligne sur charts/*.json : la zone récente des
        fiches est un resample W-FRI (cf. _sample_series), donc le σ
        hebdomadaire y est le même estimateur qu'en production, au dernier
        point près (semaine partielle, exclue ici). Les percentiles peuvent
        dévier de quelques centièmes — suffisant pour surveiller une dérive,
        pas pour re-fixer une borne.

RÈGLE DE REVISITE (décision du 17/08/2026) : re-mesurer à chaque changement
de composition de l'univers dépassant ~10 titres, ou tous les six mois. Si la
médiane de mom_ratio sort du plateau [0,3, 2,0], le régime de marché a changé
et les bornes sont à re-discuter — jamais à déplacer en silence.
"""
import argparse
import glob
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pc(vals, p):
    v = sorted(vals)
    return v[min(len(v) - 1, int(p * (len(v) - 1)))]


def _cloche(x, a, b, c, d, mx):
    if x is None:
        return None
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return float(mx)
    return round(mx * ((x - a) / (b - a) if x < b else (d - x) / (d - c)), 1)


def _rampe(x, a, b, mx):
    if x is None:
        return None
    return round(mx * max(0.0, min(1.0, (x - a) / (b - a))), 1)


def _bloc(mom, dd, z, seances, pente, neutre=0.55):
    crit = [(6, _cloche(mom, -1.5, 0.3, 2.0, 3.5, 6)),
            (4, _rampe(dd, -40, -5, 4)),
            (3, _cloche(z, -3, -1.5, 1, 3, 3)
                if (z is not None and (seances or 0) >= 1260) else None),
            (2, _rampe(pente, -3.5, 4.5, 2))]
    got = [(m, p) for m, p in crit if p is not None]
    if not got:
        return None
    dispo = sum(m for m, _ in got)
    taux = sum(p for _, p in got) / dispo
    part = dispo / 15
    return round((taux * part + neutre * (1 - part)) * 15, 2)


def _source_charts():
    rows = []
    for f in sorted(glob.glob(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "charts", "*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        b = d.get("breakdown") or {}
        pts = d.get("points") or []
        tl = d.get("t_last")
        if not pts or tl is None:
            continue
        rets = []
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i - 1][0]
            if 0.15 < dx <= 0.35 and pts[i][1] > 0 and pts[i - 1][1] > 0:
                rets.append(math.log(pts[i][1] / pts[i - 1][1]))
        rets = rets[-104:]
        sig = statistics.stdev(rets) * math.sqrt(52) if len(rets) >= 40 else None

        def at(t, tol):
            best = None
            for x, y in pts:
                dd_ = abs(x - t)
                if best is None or dd_ < best[0]:
                    best = (dd_, y)
            return best[1] if best and best[0] <= tol else None

        p1, p13 = at(tl - 1, 0.4), at(tl - 13, 1.2)
        mom = None
        if sig and p1 and p13 and p13 > 0:
            mom = math.log(min(pts[-1][1], p1) / p13) / max(sig, 0.10)
        w = b.get("regression_window_years")
        rows.append(dict(
            t=os.path.basename(f)[:-5], mom=mom, sig=sig,
            dd=b.get("drawdown_52w_pct"),
            pente=b.get("pente_mm21_5j_pct", b.get("cross_slope_mm21_pct")),
            z=b.get("regression_z"),
            seances=(w * 252 if w is not None else None)))
    return rows


def _source_yfinance():
    # Les fonctions de PRODUCTION, sur les cours quotidiens réels. Le z et sa
    # fenêtre exigent la classification sectorielle (appel réseau par titre) :
    # ils ne sont PAS recalculés ici — la cloche z est inchangée depuis le
    # 07/08, seule sa garde de fenêtre est nouvelle et elle se lit dans les
    # breakdowns publiés. On calibre les trois critères NOUVEAUX.
    import yfinance as yf
    from screener import UNIVERS, calcul_momentum_intrants
    rows = []
    for i, tk in enumerate(sorted(UNIVERS)):
        try:
            h = yf.Ticker(tk).history(period="2y", auto_adjust=True)
            close = h["Close"].dropna()
            if len(close) < 50:
                continue
            mom, _, sig = calcul_momentum_intrants(close)
            mm21 = close.rolling(21).mean().dropna()
            pente = (float((mm21.iloc[-1] - mm21.iloc[-6]) / mm21.iloc[-6] * 100)
                     if len(mm21) >= 6 else None)
            c52 = close.iloc[-252:] if len(close) >= 252 else None
            dd = (float(close.iloc[-1] / c52.max() - 1) * 100
                  if c52 is not None else None)
            rows.append(dict(t=tk, mom=mom, sig=(sig / 100 if sig else None),
                             dd=dd, pente=pente, z=None, seances=None))
        except Exception as e:
            print(f"  ⚠ {tk}: {type(e).__name__}", file=sys.stderr)
        if i % 25 == 24:
            print(f"  … {i + 1} titres", file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", choices=["charts", "yfinance"], default="yfinance")
    args = ap.parse_args()
    rows = _source_charts() if args.source == "charts" else _source_yfinance()
    print(f"source={args.source}  n={len(rows)}")

    for nom, key in (("mom_ratio", "mom"), ("drawdown_52w_pct", "dd"),
                     ("pente_mm21_pct", "pente")):
        v = [r[key] for r in rows if r.get(key) is not None]
        if not v:
            continue
        print(f"\n{nom} (n={len(v)})")
        for p in (5, 10, 25, 35, 50, 75, 85, 90, 95, 97):
            print(f"  p{p:<3} {_pc(v, p / 100):8.2f}")

    blocs = [b for b in (_bloc(r["mom"], r["dd"], r["z"], r["seances"],
                               r["pente"]) for r in rows) if b is not None]
    if blocs:
        print(f"\nbloc m /15 (n={len(blocs)}) : moyenne {statistics.mean(blocs):.2f}"
              f"  dispersion/max {statistics.pstdev(blocs) / 15:.3f}"
              f"  p5 {_pc(blocs, .05):.1f}  p10 {_pc(blocs, .10):.1f}"
              f"  p25 {_pc(blocs, .25):.1f}"
              f"  au max {sum(1 for x in blocs if x >= 14.95)}"
              f"  à zéro {sum(1 for x in blocs if x <= 0.05)}")
        print("rappel raison_sortie : « quasi-nul » < 4 (≈ p5),"
              " « dégradé » < 7 (≈ p20) — recalibrer si la moyenne quitte ~10.")


if __name__ == "__main__":
    main()
