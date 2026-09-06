#!/usr/bin/env python3
"""La performance pondérée par le temps : un virement n'est pas un rendement.

    python tests/test_performance.py
"""
import ast
import glob
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Les bouchons sont posés AVANT d'importer les deux écrivains de portfolio.json :
# tous deux tirent yfinance et anthropic, absents du runner.
import _bouchons                                                    # noqa: E402
_bouchons.poser()

import config                                                       # noqa: E402
import portfolio_agent                                              # noqa: E402
import update_prices                                                # noqa: E402

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

print("\n— Une règle qui peut rejeter une décision doit être ANNONCÉE à l'agent —")
# LE 10/08/2026, LE TEXTE PUBLIÉ A MENTI SANS QUE PERSONNE MENTE. Le portefeuille
# portait 19 lignes sur 20 ; l'agent a proposé trois achats de nouveaux titres.
# Le premier (BKNG) a pris la dernière place, les deux autres ont été rejetés par
# le plafond — et `analyse_macro`, écrite AVANT l'exécution, annonçait au lecteur
# « Trois décisions d'achat cette semaine » quand le journal n'en montrait qu'une.
#
# La cause n'est pas le modèle : c'est que `MAX_POSITIONS` était vérifié dans
# executer_decisions et JAMAIS dit dans le prompt. Le prompt prévenait déjà pour
# R01, R03 et la concentration — sa propre consigne dit « évite de proposer des
# décisions vouées à l'échec » et « ne soumets pas l'action si tu sais qu'elle
# sera bloquée ». L'agent ne pouvait pas savoir.
_p = json.load(open(os.path.join(RACINE, "portfolio.json"), encoding="utf-8"))
_w = json.load(open(os.path.join(RACINE, "watchlist.json"), encoding="utf-8"))
_ctx = {"cac40": {}, "msci": {}}
_cas = []
for _n in (portfolio_agent.MAX_POSITIONS - 1, portfolio_agent.MAX_POSITIONS, 0):
    _q = dict(_p)
    _q["positions"] = _p["positions"][:_n]
    _txt = portfolio_agent.construire_prompt(_q, _w, _ctx, analyse={}, macro_news=[])
    _attendu = max(0, portfolio_agent.MAX_POSITIONS - _n)
    _cas.append((_n, f"{_n}/{portfolio_agent.MAX_POSITIONS}" in _txt
                 and f"reste {_attendu} place" in _txt))
check("le prompt annonce les places restantes, quel que soit l'état",
      all(v for _, v in _cas), str([n for n, v in _cas if not v]))
# Et la donnée publiée respecte le plafond qu'elle annonce.
check("le portefeuille publié ne dépasse pas son propre plafond",
      len(_p["positions"]) <= portfolio_agent.MAX_POSITIONS,
      f"{len(_p['positions'])} lignes pour un plafond de {portfolio_agent.MAX_POSITIONS}")
# Une décision bloquée ne doit jamais avoir produit d'ordre le même jour : c'est
# ce qui distingue « refusée » de « passée quand même ».
_ordres = {(o.get("date"), o.get("ticker")) for o in _p.get("ordres") or []}
_fantomes = [f"{b.get('ticker')}@{b.get('date')}" for b in _p.get("decisions_bloquees") or []
             if (b.get("date"), b.get("ticker")) in _ordres]
check("aucune décision bloquée n'a malgré tout produit un ordre", not _fantomes, str(_fantomes))

print("\n— Les deux écrivains de portfolio.json tiennent-ils la même formule ? —")
# POURQUOI CETTE SECTION EXISTE. portfolio.json a DEUX auteurs : l'agent le lundi,
# `update_prices.py` chaque soir ouvré. Tous deux publient le champ `performance`,
# et `update_prices.py` n'était couvert par AUCUNE des sept suites — alors que
# c'est LUI qui réécrit chaque nuit le nombre le plus important du site. C'est ce
# chemin-là qui aurait republié 32,94 % le soir où le registre des versements
# avait été restauré depuis un commit périmé.
#
# La reconstitution du capital de départ — `capital_initial` moins la somme des
# versements — était écrite TROIS fois : une dans `_perf_twr`, deux dans
# `update_prices`. Trois copies d'une règle sont trois règles qui divergent.
check("update_prices s'importe dans les conditions du runner",
      hasattr(update_prices, "main"))
# L'IDENTITÉ D'OBJET, PAS UNE ÉGALITÉ DE RÉSULTAT : deux fonctions qui rendent
# aujourd'hui le même nombre peuvent diverger demain. Ici il n'y en a qu'une.
check("les deux modules tiennent la MÊME fonction de performance",
      update_prices._perf_twr is portfolio_agent._perf_twr)
# Et personne ne refait le calcul à la main ailleurs. La source de vérité est le
# dépôt, pas une liste de fichiers écrite ici : on balaie tous les modules de la
# racine, et la reconstitution ne doit apparaître qu'à UN endroit.
_MOTIF = re.compile(r"-\s*\\?\s*\n?\s*sum\(\s*i\[[\"']montant[\"']\]", re.M)
_refont = {os.path.basename(p): len(_MOTIF.findall(open(p, encoding="utf-8").read()))
           for p in glob.glob(os.path.join(RACINE, "*.py"))}
_refont = {k: v for k, v in _refont.items() if v}
check("le capital de départ ne se reconstitue qu'à un seul endroit",
      sum(_refont.values()) == 1 and _refont.get("portfolio_agent.py") == 1,
      f"{_refont}")

print("\n— Un taux de change absent arrête le run, il ne s'invente pas —")
# 64 % du portefeuille est libellé en USD : le taux EUR/USD multiplie la valeur
# de quinze positions sur vingt, donc capital_actuel, donc la performance
# publiée. Le repli à 1,10 était servi EN SILENCE — rien ne distinguait « le
# taux vaut vraiment 1,10 » de « la source n'a pas répondu ». Décision du
# propriétaire du 10/08/2026 : le run échoue plutôt que de publier une
# valorisation fondée sur un chiffre non mesuré. Le site garde alors les
# chiffres de la veille, ce que update_prices fait déjà quand aucun prix n'est
# récupéré.
#
# Les bouchons rendent yfinance inutilisable : ici la source est donc toujours
# en panne, et c'est exactement le cas qu'on veut éprouver.


def _echoue(fn, *a):
    try:
        fn(*a)
    except SystemExit:
        return True
    except Exception:                                            # noqa: BLE001
        return False
    return False


check("sans taux mesuré, EUR/USD arrête le run",
      _echoue(portfolio_agent.get_eur_usd_rate))
check("sans taux mesuré, EUR/GBP arrête le run",
      _echoue(portfolio_agent.get_eur_gbp_rate))
check("sans taux mesuré, une devise secondaire arrête le run",
      _echoue(portfolio_agent.get_eur_rate, "DKK"))
# Le passage au pair était implicite : toute devise inconnue rendait le montant
# inchangé, donc traitait des yens comme des euros. L'euro, lui, passe.
check("une devise sans conversion connue arrête le run",
      _echoue(portfolio_agent.to_eur, 100.0, "XYZ", 1.1))
check("l'euro, lui, traverse sans conversion",
      portfolio_agent.to_eur(100.0, "EUR", 1.1) == 100.0)
# Plus aucune table de taux écrits en dur : c'est elle qui rendait le silence
# possible, et `\.get(devise, 1.0)` traitait une devise absente comme de l'euro.
check("aucune table de taux de repli ne subsiste",
      not hasattr(portfolio_agent, "_FX_FALLBACK"))
# `except:` nu : il attrape aussi KeyboardInterrupt et SystemExit. Trois
# subsistaient dans le module qui publie les nombres du portefeuille.
_nus = {os.path.basename(p): len(re.findall(r"^\s*except\s*:",
                                            open(p, encoding="utf-8").read(), re.M))
        for p in (os.path.join(RACINE, "portfolio_agent.py"),
                  os.path.join(RACINE, "update_prices.py"),
                  os.path.join(RACINE, "config.py"))}
check("aucun except nu dans les modules qui publient des nombres",
      not any(_nus.values()), str({k: v for k, v in _nus.items() if v}))

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


# ─────────────────────────────────────────────────────────────────────────────
print("\n— Le livre boucle : liquidités + bases = versé + réalisé —")
# CETTE IDENTITÉ EST VRAIE PAR CONSTRUCTION, ET ELLE ÉTAIT FAUSSE DE 374,10 €.
# Deux migrations de change ont réécrit `montant_investi` sur sept lignes sans
# jamais corriger le cash débité à l'achat. Rien ne l'a vu, parce que le
# dashboard DÉDUISAIT le résultat réalisé par soustraction : l'écart y tombait,
# étiqueté « résultat réalisé sur les ventes passées » — −1 311,87 € affichés
# quand les douze ventes du journal totalisaient −937,77 €. Un chiffre déduit
# d'un autre n'est le contrôle de personne.
_verse   = d["capital_initial"]
_realise = d.get("total_resultat_realise")
check("le résultat réalisé est publié, pas déduit à l'affichage", _realise is not None)
_ecart = portfolio_agent.ecart_tresorerie(_verse, d["liquidites"], d["positions"],
                                          _realise or 0)
check("l'identité de trésorerie tient à moins de 2 centimes",
      abs(_ecart) < 0.02, f"écart {_ecart:+.2f} €")
check("l'écart de trésorerie est publié, donc recoupable",
      abs(d.get("ecart_tresorerie", 99)) < 0.02, str(d.get("ecart_tresorerie")))
# Tant que le journal n'est pas tronqué (plafond 50), il recoupe le compteur.
if len(d["ordres"]) <= 50:
    check("le compteur de résultat réalisé recoupe le journal des ordres",
          abs(portfolio_agent.resultat_realise_net(d["ordres"]) - _realise) < 0.05,
          f"{portfolio_agent.resultat_realise_net(d['ordres'])} vs {_realise}")
check("le capital publié est bien liquidités + valeur des positions",
      d["capital_actuel"] == round(
          sum(p["valeur_actuelle"] for p in d["positions"]) + d["liquidites"], 2))

print("\n— La plus-value latente ne survit jamais à la ligne qu'elle décrit —")
# Le champ n'était écrit que par maj_position(), qui rend False sans rien
# toucher quand un prix manque. Un allègement ou un renfort passé ce jour-là
# laissait la plus-value de l'ANCIENNE ligne, et le dashboard préfère le champ
# stocké au calcul : il publiait le faux.
_perime = [p["ticker"] for p in d["positions"]
           if p.get("plus_value_latente_eur") is not None
           and abs(p["plus_value_latente_eur"]
                   - round(p["valeur_actuelle"] - p["montant_investi"], 2)) > 0.011]
check("chaque plus-value latente vaut valeur − base", not _perime, f"périmées : {_perime}")
_perf_ko = [p["ticker"] for p in d["positions"]
            if p["montant_investi"] > 0
            and abs(p["performance"] - round(
                (p["valeur_actuelle"] - p["montant_investi"]) / p["montant_investi"] * 100, 2)) > 0.011]
check("chaque performance de ligne est celle de sa base en euros", not _perf_ko, f"{_perf_ko}")
check("le total de plus-value latente est publié et exact",
      d.get("plus_value_latente_totale") == round(
          sum(p["plus_value_latente_eur"] for p in d["positions"]), 2))
check("le total investi publié est la somme des bases, pas la valeur de marché",
      d.get("total_investi") == round(
          sum(p["montant_investi"] for p in d["positions"]), 2))

_pos_test = [{"ticker": "X", "quantite": 2, "montant_investi": 100.0,
              "valeur_actuelle": 150.0, "plus_value_latente_eur": 999.0,
              "performance": 999.0}]
portfolio_agent.sync_plus_value_latente(_pos_test)
check("sync_plus_value_latente répare une valeur périmée",
      _pos_test[0]["plus_value_latente_eur"] == 50.0 and _pos_test[0]["performance"] == 50.0)

print("\n— Une base fiscale n'est jamais réécrite au taux du jour —")
# La migration GBP décidait avec le taux DU JOUR : `prix_achat × qte / eur_gbp`
# recalculé à chaque run, comparé au seuil 0,97. LSEG.L était à 0,9934 du seuil.
# Une hausse de 2,4 % de la livre rallumait la migration sur une base DÉJÀ
# correcte, amputait la plus-value latente de 46 € et changeait une base fiscale
# sans qu'aucune transaction ait eu lieu. Les deux migrations sont retirées :
# on signale, on ne réécrit plus.
_src_agent = open(os.path.join(RACINE, "portfolio_agent.py"), encoding="utf-8").read()
check("plus aucune migration ne réécrit montant_investi dans maj_position",
      "pos[\"montant_investi\"] = correct_eur" not in _src_agent
      and "pos[\"montant_investi\"] = to_eur(native" not in _src_agent)
# Le détecteur qui la remplace : une base à moins de 40 % de son estimation au
# taux du jour est presque sûrement de la devise native prise pour des euros.
_natif = []
for _p in d["positions"]:
    if _p.get("currency") in ("EUR", "", None):
        continue
    _est = config.perf_ponderee_temps and _p["montant_investi"]  # garde le linter tranquille
    _brut = _p["prix_achat"] * _p["quantite"]
    _impl = _brut / _p["montant_investi"] if _p["montant_investi"] else 0
    # taux implicite d'achat plausible : entre 0,1 (DKK) et 2 ; jamais ~1 pour
    # une devise dont le taux courant est loin de 1.
    if abs(_impl - 1) < 0.02 and _p["currency"] in ("USD", "GBP"):
        _natif.append(_p["ticker"])
check("aucune base fiscale ne ressemble à de la devise native non convertie",
      not _natif, f"suspectes : {_natif}")

print("\n— Le PFU d'une liquidation porte sur le résultat NET —")
_liq = config.apply_liquidation_cost_and_tax
check("une liquidation en perte ne paie aucun impôt",
      _liq([(100.0, 200.0)], 0.0)["impot_pfu_eur"] == 0.0)
check("une moins-value en compense une plus-value dans la même cession",
      _liq([(200.0, 100.0), (100.0, 200.0)], 0.0)["impot_pfu_eur"] == 0.0)
check("sans perte à imputer, une ligne unique retombe sur le calcul de vente",
      _liq([(1000.0, 500.0)], 0.0)["impot_pfu_eur"]
      == config.apply_sell_cost_and_tax(1000.0, 500.0)["impot_pfu_eur"])
_r = _liq([(1000.0, 500.0)], 200.0)
check("les pertes reportables s'imputent avant l'impôt",
      _r["pertes_imputees_eur"] == 200.0
      and _r["impot_pfu_eur"] == round(_r["base_imposable_eur"] * config.PFU_RATE, 2))
check("une liquidation en perte alimente le stock de pertes reportables",
      _liq([(100.0, 200.0)], 50.0)["pertes_reportables_restantes_eur"] > 50.0)
check("le portefeuille publié impute bien ses pertes reportables",
      d.get("pertes_imputees_si_liquidation", 0) > 0
      if d.get("total_pertes_reportables", 0) > 0
         and d.get("plus_value_nette_si_liquidation", 0) > 0 else True)
_agr = portfolio_agent.agregats_derives(d["positions"], d["liquidites"],
                                        d["total_pertes_reportables"])
check("le capital post-liquidation publié est celui du calcul groupé",
      d["capital_post_liquidation"] == _agr["capital_post_liquidation"],
      f"{d['capital_post_liquidation']} vs {_agr['capital_post_liquidation']}")
check("le PFU latent publié est celui du calcul groupé",
      d["pfu_latent_si_liquidation"] == _agr["pfu_latent_si_liquidation"])
check("la performance brute suit le capital du jour",
      d["performance_brute"] == twr(injections,
                                    d["capital_actuel"] + d["total_frais_payes"]
                                    + d["total_impots_payes"], cap_depart),
      f"{d['performance_brute']}")

print("\n— Ce que le graphique de performance ne montre plus —")
_html = open(os.path.join(RACINE, "portfolio.html"), encoding="utf-8").read()
check("le graphique ne trace plus de marqueur d'injection",
      "pts.filter(p => p.note)" not in _html
      and "'⊕ injection '" not in _html)
check("le graphique bascule entre pourcents et euros",
      "setChartUnit('pct'" in _html and "setChartUnit('eur'" in _html)

check("la carte « Valeur du portefeuille » a laissé la place à la plus-value latente",
      "Valeur du portefeuille <span" not in _html and "Plus-value latente <span" in _html)
check("le verdict « en avance sur le marché » ne double plus les deux cartes",
      "En avance sur le marché" not in _html and "status-pill\" style" not in _html)
check("le graphe n'affiche plus de graduations d'axes",
      "function fmtAxe" not in _html and "'text-anchor':'end'" not in _html)
check("la série en euros trace le montant des lignes, hors liquidités",
      "h.valeur_positions" in _html and "verseALaDate" not in _html)
check("le site lit le résultat réalisé au lieu de le déduire",
      "d.total_resultat_realise" in _html
      and "gainLatent - pvLatenteTotale" not in _html)
check("le taux du PFU n'est plus redéclaré en dur dans la page",
      "* 0.30" not in _html)
check("l'infobulle n'est plus rognée par le bloc qui la contient",
      ".survival-block { background: var(--surface); border: 1px solid var(--border); "
      "border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.75rem; "
      "position: relative; box-shadow" in _html)


print("\n— Le journal des ordres est le registre de trésorerie —")
# IL N'Y AVAIT NI LE CAPITAL DE DÉPART NI LE VERSEMENT D'AOÛT. Seul celui du
# 05/05 était journalisé : le registre des versements et le journal des ordres
# racontaient deux histoires différentes du même compte. Reconstituer les
# liquidités d'une date passée demandait alors de rustiner deux trous à la main.
_apports = [o for o in d["ordres"] if o.get("type") == "APPORT"]
check("chaque versement du registre a son entrée au journal",
      len(_apports) == len(d["injections"]) + 1,
      f"{len(_apports)} apports pour {len(d['injections'])} injections + le départ")
check("les versements journalisés totalisent le capital versé",
      abs(sum(o["montant"] for o in _apports) - d["capital_initial"]) < 0.01,
      f"{sum(o['montant'] for o in _apports)} vs {d['capital_initial']}")
_dates_inj = {i["date"] for i in d["injections"]}
check("chaque injection datée retrouve son apport au journal",
      _dates_inj <= {o["date"] for o in _apports})
# Le plafond ne doit JAMAIS emporter un mouvement de caisse : c'est lui qui
# porte la structure du compte, et il est rare et minuscule.
_faux = ([{"type": "ACHAT", "date": "2026-01-%02d" % (i % 28 + 1)} for i in range(300)]
         + [{"type": "APPORT", "date": "2020-01-01"},
            {"type": "CORRECTION", "date": "2020-01-02"}])
_garde = portfolio_agent.tronquer_ordres(_faux)
check("la troncature du journal épargne les versements et régularisations",
      sum(1 for o in _garde if o["type"] in ("APPORT", "CORRECTION")) == 2
      and len(_garde) == portfolio_agent.PLAFOND_ORDRES + 2)
check("le journal publié tient sous son plafond",
      sum(1 for o in d["ordres"] if o["type"] not in ("APPORT", "CORRECTION"))
      <= portfolio_agent.PLAFOND_ORDRES)

print("\n— Chaque point d'historique porte sa décomposition —")
# `capital` seul ne permettait pas de tracer la valeur des lignes hors cash : il
# a fallu reconstituer huit mois de trésorerie à rebours depuis le journal. Un
# total dont on ne garde pas les termes est un total qu'on ne saura pas
# redécouper plus tard.
_h = d["performance_history"]
check("tous les points portent valeur_positions et liquidites",
      all("valeur_positions" in x and "liquidites" in x for x in _h),
      str([x["date"] for x in _h if "valeur_positions" not in x][:3]))
_incoh = [x["date"] for x in _h
          if abs(x["valeur_positions"] + x["liquidites"] - x["capital"]) > 0.011]
check("positions + liquidités = capital, à chaque point", not _incoh, str(_incoh[:3]))
check("ni cash ni positions négatifs dans l'historique",
      all(x["liquidites"] >= 0 and x["valeur_positions"] >= 0 for x in _h))
check("le dernier point porte les grandeurs MESURÉES du jour",
      _h[-1]["valeur_positions"] == d["valeur_positions"]
      and _h[-1]["liquidites"] == d["liquidites"]
      and "valeur_positions_source" not in _h[-1])
check("les points reconstitués sont marqués comme tels",
      all(x.get("valeur_positions_source") == "reconstituee" for x in _h[:-1]))
check("la valeur des positions publiée est la somme des lignes",
      d["valeur_positions"] == round(sum(p["valeur_actuelle"] for p in d["positions"]), 2))


total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
