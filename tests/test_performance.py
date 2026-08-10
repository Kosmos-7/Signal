#!/usr/bin/env python3
"""La performance pondérée par le temps : un virement n'est pas un rendement.

    python tests/test_performance.py
"""
import ast
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

print("\n— Retraits (montant négatif, effectif immédiatement) —")
# Convention : capital_initial est le total NET versé. 10 000 versés, 5 000
# retirés après +20 % : cap_depart = net(5 000) − (−5 000) = 10 000.
retrait = [{"date": "2026-06-01", "montant": -5000, "capital_post": 7000}]
check("un retrait ne change pas la performance du jour",
      twr(retrait, 7000, 10000) == 20.0)
check("les gains d'après-retrait portent sur la base réduite",
      twr(retrait, 7700, 10000) == 32.0)
check("dépôt puis retrait le même jour se chaînent dans l'ordre",
      twr([{"date": "2026-06-01", "montant": 5000, "capital_post": 15000},
           {"date": "2026-06-01", "montant": -3000, "capital_post": 12000}],
          12000, 10000) == 0.0)

print("\n— Drawdown sur l'indice, plus sur le capital —")
mdd = config.max_drawdown_indice
serie = [{"perf": 0.0}, {"perf": 10.0}, {"perf": -1.0}]
check("le drawdown se mesure du pic de l'indice", mdd(serie) == -10.0)
check("une injection ne masque plus un repli",
      # capital 10k -> 11k -> injection (+10k, capital 20.9k) -> les positions
      # continuent de baisser : l'indice TWR voit la baisse, le capital non.
      mdd([{"perf": 0.0}, {"perf": 10.0}, {"perf": 4.5}, {"perf": -1.0}]) == -10.0)
check("série vide ou sans perf : zéro", mdd([]) == 0.0 == mdd([{"capital": 5}]))

print("\n— Cohérence du portefeuille publié —")
d = json.load(open(os.path.join(RACINE, "portfolio.json"), encoding="utf-8"))
injections = d.get("injections", [])
check("le registre des injections existe, capital_post présent (None = en attente)",
      injections and all({"date", "montant", "capital_post", "effective_le"} <= set(i)
                         for i in injections))
cap_depart = d["capital_initial"] - sum(i["montant"] for i in injections)
check("capital de départ reconstruit = 10 000 €", cap_depart == 10000.0)
check("le drawdown publié est celui de l'indice",
      d["max_drawdown"] == config.max_drawdown_indice(d["performance_history"]))
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

print("\n— Aucun champ publié ne se perd à la réécriture —")
# POURQUOI CETTE GARDE EXISTE. Deux fois, un dictionnaire reconstruit de zéro a
# fait disparaître en silence des données déjà publiées : `proj` le 07/08 (96
# fiches sur 97 privées de leur trajectoire), puis `injections` le 10/08 (les
# deux versements de 10 000 €, seules données qui distinguent un virement d'un
# rendement). Les deux fois un commentaire prévenait — « tout nouveau champ doit
# être ajouté ICI » — et les deux fois l'avertissement n'a pas suffi, parce
# qu'un commentaire ne s'exécute pas.
#
# LES DEUX CÔTÉS SONT DÉRIVÉS, JAMAIS RECOPIÉS. Les clés publiées se lisent dans
# portfolio.json ; les clés réécrites s'extraient de l'arbre syntaxique du code.
# Une liste de noms de champs tenue à la main diverge — c'est exactement ce que
# _bouchons.py a appris à ses dépens, et trois diagnostics faux ont été produits
# dans une seule session en écrivant un nom de champ de mémoire.


def _cles_du_dict(chemin, nom_var):
    """Clés du dict littéral `nom_var = {...}`. Rend (clés, motif d'échec).

    FAIL-LOUD PLUTÔT QUE SILENCE : si le littéral est introuvable, en double, ou
    porte une clé calculée, la garde ne sait pas conclure et le DIT. Une garde
    qui sous-lit le code rendrait un vert qui ne prouve rien."""
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    trouves = [n.value for n in ast.walk(arbre)
               if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
               for t in n.targets if isinstance(t, ast.Name) and t.id == nom_var]
    if len(trouves) != 1:
        return None, f"{len(trouves)} littéral(aux) `{nom_var} = {{...}}` dans {chemin}"
    if any(k is None or not isinstance(k, ast.Constant) or not isinstance(k.value, str)
           for k in trouves[0].keys):
        return None, f"clé calculée dans `{nom_var}` de {chemin} — garde aveugle"
    return {k.value for k in trouves[0].keys}, None


def _cles_indicees(chemin, nom_var):
    """Clés écrites par `nom_var["X"] = ...`. Rend (clés, nb d'indices calculés)."""
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    cles, flous = set(), 0
    for n in ast.walk(arbre):
        for t in (n.targets if isinstance(n, ast.Assign) else []):
            if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                    and t.value.id == nom_var):
                if isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                    cles.add(t.slice.value)
                else:
                    flous += 1
    return cles, flous


_hebdo, _err = _cles_du_dict(os.path.join(RACINE, "portfolio_agent.py"), "output")
check("les clés réécrites par le run hebdomadaire sont lisibles", _err is None, _err or "")
if _hebdo:
    _publiees = set(d)
    _perdues = sorted(_publiees - _hebdo)
    check("aucun champ publié n'est perdu au prochain run hebdomadaire",
          not _perdues, f"perdus : {_perdues}")

    # L'AUTRE SENS COMPTE AUSSI : le run quotidien écrit dans le même fichier.
    # Un champ qu'il pose et que l'hebdomadaire ne reprend pas clignote — présent
    # six jours, absent le septième. C'est ainsi que `last_known_vix_updated_at`
    # a vécu, écrit chaque soir et jeté chaque lundi, sans que personne le lise.
    _quotidien, _flous = _cles_indicees(os.path.join(RACINE, "update_prices.py"),
                                        "portfolio")
    check("les clés écrites par le run quotidien sont toutes littérales",
          _flous == 0, f"{_flous} indice(s) calculé(s) — garde partielle")
    _clignotants = sorted(_quotidien - _hebdo)
    check("aucun champ du run quotidien n'est jeté par le run hebdomadaire",
          not _clignotants, f"clignotants : {_clignotants}")

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
