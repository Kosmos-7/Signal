#!/usr/bin/env python3
"""La performance pondérée par le temps : un virement n'est pas un rendement.

    python tests/test_performance.py
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config                                                       # noqa: E402

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


twr = config.perf_ponderee_temps

print("— Propriétés de la mesure —")
check("sans injection : rendement simple", twr([], 12000, 10000) == 20.0)
check("capital de départ nul ne plante pas", twr([], 5000, 0) == 0.0)

# LA propriété qui a motivé le changement : le jour du versement, la
# performance affichée ne bouge pas d'un centième.
inj = [{"date": "2026-05-05", "montant": 10000, "capital_post": 22107.39}]
check("une injection ne change pas la performance du jour",
      twr(inj, 22107.39, 10000) == twr([], 12107.39, 10000) == 21.07)

check("de l'argent frais sans croissance = 0 %",
      twr([{"date": "2026-02-01", "montant": 5000, "capital_post": 15000}],
          15000, 10000) == 0.0)

deux = inj + [{"date": "2026-08-03", "montant": 10000, "capital_post": 33509.90}]
check("le chaînage à deux injections reproduit le cas réel",
      twr(deux, 33509.90, 10000) == 28.75, twr(deux, 33509.90, 10000))
check("l'ordre de la liste n'importe pas (tri par date interne)",
      twr(list(reversed(deux)), 33509.90, 10000) == 28.75)
check("la perte reste une perte malgré une injection",
      twr([{"date": "2026-03-01", "montant": 10000, "capital_post": 18000}],
          17000, 10000) < 0)

print("\n— Versement en attente : hors périmètre jusqu'à disposition —")
attente = inj + [{"date": "2026-08-03", "montant": 10000, "capital_post": None}]
check("un versement en attente ne change pas la performance",
      twr(attente, 33509.90, 10000) == twr(inj, 23509.90, 10000) == 28.75)
# La propriété qui a motivé le raffinement : pendant l'attente, les gains des
# positions ne sont pas dilués par le cash parqué.
gain = 33509.90 + 2315.78          # positions +10 %, cash inchangé
check("les gains pendant l'attente ne sont pas dilués",
      twr(attente, gain, 10000) > twr(
          inj + [{"date": "2026-08-03", "montant": 10000, "capital_post": 33509.90}],
          gain, 10000))
# L'estampille (capital_post figé au capital du moment) ne fait pas sauter la
# mesure d'un centième : la période se ferme exactement où elle en était.
c = 34100.0
check("l'estampille est sans discontinuité",
      twr(attente, c, 10000) == twr(
          inj + [{"date": "2026-08-03", "montant": 10000, "capital_post": c}], c, 10000))

print("\n— Cohérence du portefeuille publié —")
d = json.load(open(os.path.join(RACINE, "portfolio.json"), encoding="utf-8"))
injections = d.get("injections", [])
check("le registre des injections existe, capital_post présent (None = en attente)",
      injections and all({"date", "montant", "capital_post", "effective_le"} <= set(i)
                         for i in injections))
cap_depart = d["capital_initial"] - sum(i["montant"] for i in injections)
check("capital de départ reconstruit = 10 000 €", cap_depart == 10000.0)
check("le champ performance est bien la mesure pondérée par le temps",
      d["performance"] == twr(injections, d["capital_actuel"], cap_depart),
      f"{d['performance']} vs {twr(injections, d['capital_actuel'], cap_depart)}")
h = d["performance_history"]
dernier = next(x for x in reversed(h) if x.get("capital") is not None)
check("le dernier point de l'historique porte la même mesure",
      abs(dernier["perf"] - d["performance"]) < 0.011,
      f"{dernier['perf']} vs {d['performance']}")
premiers = [x for x in h if x["date"] < "2026-05-05" and x.get("capital")]
check("les points d'avant la première injection sont inchangés",
      all(abs(x["perf"] - round((x["capital"] / 10000 - 1) * 100, 2)) < 0.011
          for x in premiers))

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
