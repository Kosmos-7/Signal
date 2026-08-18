#!/usr/bin/env python3
"""Réallocation (Règle 13) : allègement partiel, renforcement, et leur pilotage.

POURQUOI CETTE SUITE EXISTE. La mécanique d'allègement/renforcement a vécu
plus d'un mois en production (v3.2.0, 2026-07-20) avec ZÉRO utilisation en
42 ordres — et zéro test. Trois découvertes de l'audit du 17/08/2026 :

  · un `allegement_pct` illisible ("50%" en string) devenait une vente TOTALE
    silencieuse — le journal aurait contredit la raison publiée sur le site ;
  · le renforcement d'un titre détenu sorti du top 30 hebdo était rejeté
    comme « ticker halluciné » — 10 lignes sur 20 étaient hors d'atteinte
    pendant que le prompt promettait le contraire ;
  · le poids (%) de chaque ligne, déclencheur canonique du trim, n'était
    montré nulle part au modèle.

Cette suite fige le contrat corrigé : proratisation fiscale, PRU conservé,
anti-poussière JOURNALISÉ, rejets fail-loud, paliers de surpoids, et la
présence effective des données de pilotage dans les prompts.

Aucun accès réseau : get_prix est remplacé par une table locale, l'horloge
est figée sur un lundi (le garde weekend est lui-même sous test).

    python tests/test_portfolio_reallocation.py
"""
import datetime as _vraie_datetime
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bouchons              # noqa: E402
_bouchons.poser()

import config                    # noqa: E402
import portfolio_agent as pa     # noqa: E402

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


# ── Horloge figée : lundi 17/08/2026 (les marchés sont ouvrables) ───────────
class _DateLundi(_vraie_datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 8, 17)


class _DatetimeLundi(_vraie_datetime.datetime):
    @classmethod
    def today(cls):
        return cls(2026, 8, 17, 10, 0)

    @classmethod
    def utcnow(cls):
        return cls(2026, 8, 17, 10, 0)


class _DatetimeSamedi(_DatetimeLundi):
    @classmethod
    def today(cls):
        return cls(2026, 8, 15, 10, 0)

    @classmethod
    def utcnow(cls):
        return cls(2026, 8, 15, 10, 0)


pa.date = _DateLundi
pa.datetime = _DatetimeLundi

# ── Prix locaux : get_prix ne touche jamais le réseau ici ───────────────────
PRIX = {}
pa.get_prix = lambda t: PRIX.get(t)


def ligne(ticker, qte, prix, investi, date_achat="2026-01-02", currency="EUR",
          sector="Technology", **extra):
    p = {
        "ticker": ticker, "nom": ticker, "quantite": qte,
        "prix_achat": prix, "prix_actuel": prix,
        "montant_investi": investi, "valeur_actuelle": round(prix * qte, 2),
        "date_achat": date_achat, "currency": currency, "sector": sector,
        "market": "EU", "performance": 0.0, "raison_achat": "thèse de test",
    }
    p.update(extra)
    return p


def portefeuille(positions, liquidites=1000.0, capital=10000.0):
    return {"capital_actuel": capital, "liquidites": liquidites,
            "positions": positions, "ordres": [], "updated_at": "2026-08-10"}


WATCHLIST = {"stocks": [
    {"ticker": "BBB", "name": "BBB", "rank": 1, "score": 80, "sector": "Technology",
     "market": "EU", "breakdown": {}, "justification": "fixture de test"},
]}
CONTEXTE = {"mode_panique": False, "marches": {}, "cac40": {}, "msci": {}}


def executer(decisions, pf, watchlist=WATCHLIST, analyse=None):
    return pa.executer_decisions({"decisions": decisions}, pf, watchlist,
                                 CONTEXTE, eur_usd=1.0, eur_gbp=0.86, analyse=analyse)


def vente(ticker, pct=None, conviction="modérée"):
    d = {"action": "VENTE", "ticker": ticker, "nom": ticker,
         "raison": "vente de test", "conviction": conviction}
    if pct is not None:
        d["allegement_pct"] = pct
    return d


# ═════════════════════════════════════════════════════════════════════════════
print("— Allègement : proratisation, PRU, honnêteté du journal —")

# Ligne de 10 titres à 20€ (achetée 10€, +100%), détenue 227j : allègement 40%.
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", pct=40)], portefeuille([ligne("AAA", 10, 10.0, 100.0)]))
o = ordres[0] if ordres else {}
p = pos[0] if pos else {}
check("allègement 40% de 10 titres : 4 vendus", o.get("qte") == 4)
check("l'ordre porte le drapeau allegement", o.get("allegement") is True)
check("pct réalisé journalisé (40%)", o.get("allegement_pct") == 40.0)
check("pct demandé journalisé (40%)", o.get("allegement_demande_pct") == 40.0)
check("qte_restante journalisée (6)", o.get("qte_restante") == 6)
check("la ligne survit avec 6 titres", p.get("quantite") == 6)
check("PRU d'origine conservé (10€)", p.get("prix_achat") == 10.0)
check("date de détention d'origine conservée", p.get("date_achat") == "2026-01-02")
check("base fiscale résiduelle proratisée (60€)",
      abs(p.get("montant_investi", 0) - 60.0) < 0.01)
# PFU au prorata : brut 4×20=80€, frais 7.5bps, base 40% de 100€ = 40€
_brut, _base = 80.0, 40.0
_frais = round(_brut * config.TRANSACTION_COST_BPS / 10000.0, 4)
_pv_attendue = round(_brut - _frais - _base, 2)
check("plus-value calculée sur la SEULE fraction vendue",
      abs(o.get("plus_value_eur", 0) - _pv_attendue) < 0.01,
      f"attendu {_pv_attendue}, obtenu {o.get('plus_value_eur')}")
check("PFU = 31,4% de cette plus-value proratisée",
      abs(o.get("impot_pfu_eur", 0) - round(_pv_attendue * config.PFU_RATE, 2)) < 0.01)

# Arrondi au titre entier : 2 titres, 25% demandé → 1 titre vendu = 50% réalisé.
PRIX.clear(); PRIX["AAA"] = 200.0
pos, liq, ordres, _ = executer(
    [vente("AAA", pct=25)], portefeuille([ligne("AAA", 2, 100.0, 200.0)]))
o = ordres[0] if ordres else {}
check("2 titres, 25% demandé : le réalisé (50%) est journalisé",
      o.get("allegement") is True and o.get("allegement_pct") == 50.0)
check("… et le demandé (25%) aussi — l'écart est assumé, pas caché",
      o.get("allegement_demande_pct") == 25.0)

# Parse robuste : "50%" en string est une demande LISIBLE.
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", pct="50%")], portefeuille([ligne("AAA", 10, 10.0, 100.0)]))
check("allegement_pct='50%' (string) est compris comme 50",
      ordres and ordres[0].get("allegement_pct") == 50.0)

print("— Allègement : rejets fail-loud (l'ancien code vendait TOUT en silence) —")
for brut_pct, libelle in [("cinquante", "illisible"), (150, "hors bornes >100"),
                          (0, "zéro"), (-5, "négatif")]:
    PRIX.clear(); PRIX["AAA"] = 20.0
    pf = portefeuille([ligne("AAA", 10, 10.0, 100.0)])
    pos, liq, ordres, bloques = executer([vente("AAA", pct=brut_pct)], pf)
    check(f"allegement_pct {libelle} ({brut_pct!r}) : vente REFUSÉE, pas totale",
          not ordres and bloques
          and bloques[0].get("bloque_par") == "allegement_pct_invalide")
    check(f"… et la position est intacte ({brut_pct!r})",
          pos and pos[0]["quantite"] == 10)

# 100 exactement = vente totale explicite, sans marqueur d'allègement.
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", pct=100)], portefeuille([ligne("AAA", 10, 10.0, 100.0)]))
check("allegement_pct=100 : vente totale acceptée",
      ordres and ordres[0].get("qte") == 10 and not pos)
check("… sans drapeau allegement ni conversion",
      not ordres[0].get("allegement") and not ordres[0].get("allegement_converti_total"))

print("— Anti-poussière et ligne indivisible : la conversion est JOURNALISÉE —")
# Reliquat < 100€ : 10 titres à 10€, allègement 50% → reliquat 50€ → vente totale.
PRIX.clear(); PRIX["AAA"] = 10.0
pos, liq, ordres, _ = executer(
    [vente("AAA", pct=50)], portefeuille([ligne("AAA", 10, 10.0, 100.0)]))
o = ordres[0] if ordres else {}
check("reliquat 50€ < 100€ : vente totale (position fermée)",
      o.get("qte") == 10 and not pos)
check("la conversion anti-poussière est écrite dans l'ordre",
      "100€" in str(o.get("allegement_converti_total", "")))
check("le pct demandé (50%) reste journalisé", o.get("allegement_demande_pct") == 50.0)

# Ligne d'un titre : indivisible par construction.
PRIX.clear(); PRIX["AAA"] = 500.0
pos, liq, ordres, _ = executer(
    [vente("AAA", pct=30)], portefeuille([ligne("AAA", 1, 400.0, 400.0)]))
o = ordres[0] if ordres else {}
check("ligne d'1 titre : allègement 30% converti en vente totale",
      o.get("qte") == 1 and not pos)
check("… avec le motif « indivisible » journalisé",
      "indivisible" in str(o.get("allegement_converti_total", "")))

print("— Un allègement reste une VENTE : Règle 01 s'applique —")
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", pct=40)],
    portefeuille([ligne("AAA", 10, 10.0, 100.0, date_achat="2026-07-20")]))
check("allègement à 28j de détention, conviction modérée : bloqué R01",
      not ordres and bloques and bloques[0].get("bloque_par") == "R01")

print("— Verrou anti-contradiction : la passe 1 a enfin un droit de veto —")
# Vente <90j, conviction FORTE, mais la passe 1 dit « Rien de fondamental » :
# l'ancien code laissait passer sur la seule conviction — la règle du prompt
# (« la vente est interdite ») n'était jamais vérifiée.
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", conviction="forte")],
    portefeuille([ligne("AAA", 10, 10.0, 100.0, date_achat="2026-07-20")]),
    analyse={"positions_analyse": {"AAA": {"delta_these": "Rien de fondamental, les mêmes signaux relus"}}})
check("vente <90j conviction forte + passe 1 « Rien de fondamental » : bloquée",
      not ordres and bloques and bloques[0].get("bloque_par") == "R01_delta")

# Même vente quand la passe 1 documente un vrai changement : elle passe.
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", conviction="forte")],
    portefeuille([ligne("AAA", 10, 10.0, 100.0, date_achat="2026-07-20")]),
    analyse={"positions_analyse": {"AAA": {"delta_these": "Perte du contrat principal annoncée hier"}}})
check("même vente avec delta documenté par la passe 1 : autorisée",
      len(ordres) == 1 and not bloques)

# Les stop-loss restent mécaniques : -30% à 28j → vente forcée MÊME si la
# passe 1 (lagging) disait « Rien de fondamental ».
PRIX.clear(); PRIX["AAA"] = 14.0
pos, liq, ordres, bloques = executer(
    [], portefeuille([ligne("AAA", 10, 20.0, 200.0, date_achat="2026-07-20")]),
    analyse={"positions_analyse": {"AAA": {"delta_these": "Rien de fondamental"}}})
check("stop-loss catastrophe (-30%) : exempté du verrou, la vente passe",
      len(ordres) == 1 and ordres[0]["type"] == "VENTE")

print("— Garde prix aberrant sur RENFORT : le PRU n'est plus empoisonnable —")
PRIX.clear(); PRIX["BBB"] = 100.0   # ×10 vs le dernier prix connu de la ligne
pf = portefeuille([ligne("BBB", 10, 10.0, 100.0)], liquidites=500.0)
pos, liq, ordres, bloques = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "renfort sur prix corrompu",
      "conviction": "modérée", "montant_eur": 200}], pf)
check("renfort à un prix ×10 vs dernier connu : bloqué prix_aberrant",
      not ordres and bloques and bloques[0].get("bloque_par") == "prix_aberrant")
check("… et la ligne n'est pas touchée (PRU intact)",
      pos[0]["prix_achat"] == 10.0 and pos[0]["quantite"] == 10)

print("— Renforcement : PRU pondéré, date conservée, watchlist non requise —")
# Renfort d'une ligne watchlist : 10 titres PRU 10€, +90€ au prix de 10€.
PRIX.clear(); PRIX["BBB"] = 10.0
pf = portefeuille([ligne("BBB", 10, 10.0, 100.0)], liquidites=500.0)
pos, liq, ordres, _ = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "renfort test",
      "conviction": "modérée", "montant_eur": 100}], pf)
o = ordres[0] if ordres else {}
p = pos[0] if pos else {}
check("renfort exécuté et journalisé comme tel", o.get("renforcement") is True)
check("PRU moyen pondéré inchangé à prix constant (10€)", p.get("prix_achat") == 10.0)
check("quantité cumulée (10+9 au même prix, marge frais réservée)",
      p.get("quantite") == 19 and o.get("qte_totale") == 19)
check("date d'origine conservée : le compteur des 90j ne repart pas",
      p.get("date_achat") == "2026-01-02")
check("base fiscale cumulée (100€ + achat frais inclus)",
      abs(p.get("montant_investi", 0) - (100.0 + o.get("montant", 0))) < 0.01)

# LE FIX CENTRAL : un titre détenu ABSENT de la watchlist reste renforçable.
PRIX.clear(); PRIX["ZZZ"] = 10.0
pf = portefeuille([ligne("ZZZ", 10, 10.0, 100.0)], liquidites=500.0)
pos, liq, ordres, bloques = executer(
    [{"action": "ACHAT", "ticker": "ZZZ", "nom": "ZZZ", "raison": "renfort hors watchlist",
      "conviction": "modérée", "montant_eur": 100}], pf)
check("titre DÉTENU hors watchlist hebdo : renforcement AUTORISÉ (10/20 lignes "
      "étaient hors d'atteinte au moment du constat)",
      ordres and ordres[0].get("renforcement") is True)

# Le garde anti-hallucination tient toujours pour un ticker NON détenu.
PRIX.clear(); PRIX["QQQ"] = 10.0
pos, liq, ordres, bloques = executer(
    [{"action": "ACHAT", "ticker": "QQQ", "nom": "QQQ", "raison": "hallucination",
      "conviction": "modérée", "montant_eur": 100}],
    portefeuille([], liquidites=500.0))
check("ticker inconnu ET non détenu : toujours bloqué hors_watchlist",
      not ordres and bloques and bloques[0].get("bloque_par") == "hors_watchlist")

# R2 : renfort d'une ligne déjà à 25% du capital → bloqué.
PRIX.clear(); PRIX["BBB"] = 250.0
pf = portefeuille([ligne("BBB", 10, 250.0, 2500.0)], liquidites=500.0)
pos, liq, ordres, bloques = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "renfort interdit",
      "conviction": "forte", "montant_eur": 200}], pf)
check("renfort d'une ligne à 25% du capital : bloqué R02",
      not ordres and bloques and bloques[0].get("bloque_par") == "R02")

print("— Rotation : les ventes créditent le cash AVANT les achats —")
PRIX.clear(); PRIX.update({"AAA": 100.0, "BBB": 50.0})
pf = portefeuille([ligne("AAA", 10, 100.0, 1000.0)], liquidites=10.0)
pos, liq, ordres, bloques = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "rotation entrante",
      "conviction": "modérée", "montant_eur": 500},
     vente("AAA")], pf)
types_ordres = [o["type"] for o in ordres]
check("l'achat listé AVANT la vente s'exécute quand même (tri ventes d'abord)",
      types_ordres == ["VENTE", "ACHAT"],
      f"ordres obtenus : {types_ordres}, bloqués : {[b.get('bloque_par') for b in bloques]}")

print("— Conditions de vente pré-définies : stockées, bornées, non écrasées —")
PRIX.clear(); PRIX["BBB"] = 10.0
pf = portefeuille([], liquidites=500.0)
pos, liq, ordres, _ = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "achat avec contrat de sortie",
      "conviction": "modérée", "montant_eur": 200,
      "conditions_vente": ["Perte du contrat X", "", "Score < 50 trois semaines",
                           "C" * 500, 4, "cinq", "six"]}], pf)
cv = pos[0].get("conditions_vente", []) if pos else []
check("conditions vides filtrées, non-strings converties, cap à 5",
      len(cv) == 5 and "Perte du contrat X" in cv and "4" in cv)
check("chaque condition tronquée à 220 caractères", all(len(c) <= 220 for c in cv))

PRIX.clear(); PRIX["BBB"] = 10.0
pf = portefeuille([ligne("BBB", 10, 10.0, 100.0, conditions_vente=["condition d'origine"])],
                  liquidites=500.0)
pos, liq, ordres, _ = executer(
    [{"action": "ACHAT", "ticker": "BBB", "nom": "BBB", "raison": "renfort",
      "conviction": "modérée", "montant_eur": 100,
      "conditions_vente": ["tentative d'écrasement"]}], pf)
check("un renfort n'écrase pas les conditions de vente d'origine",
      pos and pos[0].get("conditions_vente") == ["condition d'origine"])

print("— Garde weekend : aucun ordre un samedi, réallocation comprise —")
pa.datetime = _DatetimeSamedi
PRIX.clear(); PRIX["AAA"] = 20.0
pos, liq, ordres, bloques = executer(
    [vente("AAA", pct=40)], portefeuille([ligne("AAA", 10, 10.0, 100.0)]))
check("allègement proposé un samedi : reporté (marche_ferme_weekend)",
      not ordres and bloques
      and bloques[0].get("bloque_par") == "marche_ferme_weekend")
pa.datetime = _DatetimeLundi

print("— Paliers de surpoids : le déclencheur du trim est signalé AVANT le mur —")
regles = pa.calculer_regles_auto(portefeuille([ligne("AAA", 10, 160.0, 1600.0)]))
surpoids = [r for r in regles if r.get("type") == "position_surpoids"]
check("ligne à 16% : palier informatif position_surpoids",
      len(surpoids) == 1 and surpoids[0].get("regime") == "info"
      and not surpoids[0].get("bloque"))
check("… le message pointe vers l'allègement (Règle 13)",
      "13" in surpoids[0].get("message", ""))

regles = pa.calculer_regles_auto(portefeuille([ligne("AAA", 10, 220.0, 2200.0)]))
oversized = [r for r in regles if r.get("type") == "position_oversized"]
check("ligne à 22% : blocage dur position_oversized, et le message donne le levier",
      len(oversized) == 1 and oversized[0].get("bloque")
      and "allège" in oversized[0].get("message", ""))

regles = pa.calculer_regles_auto(portefeuille([ligne("AAA", 10, 140.0, 1400.0)]))
check("ligne à 14% : aucun signal de poids (sous les paliers)",
      not any(r.get("type") in ("position_surpoids", "position_oversized") for r in regles))

print("— Pilotage : les prompts montrent enfin le poids et les conditions —")
pf = portefeuille([
    ligne("AAA", 10, 160.0, 1000.0, conditions_vente=["Perte du contrat X"]),
    ligne("CCC", 1, 400.0, 400.0),
])
pf.update({"performance": 5.0, "performance_brute": 6.0, "benchmark_msci": 3.0,
           "vs_benchmark": 2.0, "total_frais_payes": 10.0, "total_impots_payes": 5.0,
           "total_pertes_reportables": 0.0})
prompt2 = pa.construire_prompt(pf, WATCHLIST, dict(CONTEXTE, vix=18),
                               regles_auto=pa.calculer_regles_auto(pf))
check("passe 2 : le poids de chaque ligne est affiché (16.0%)",
      "poids 16.0% du capital" in prompt2)
check("passe 2 : le PFU latent d'une cession est chiffré par ligne",
      "PFU ~" in prompt2)
check("passe 2 : la ligne d'1 titre est marquée non allégeable",
      "ligne d'1 titre" in prompt2)
check("passe 2 : les conditions de vente pré-définies sont réinjectées",
      "Perte du contrat X" in prompt2)
check("passe 2 : le palier surpoids 15-20% est dans les règles actives",
      "position_surpoids" in prompt2)
check("passe 2 : le secteur de chaque position est visible (lecture R1)",
      "[Technology]" in prompt2)
check("passe 2 : un titre détenu hors watchlist est signalé comme tel (et renforçable)",
      "hors watchlist cette semaine" in prompt2)
check("passe 2 : le contrat annonce le REJET d'un allegement_pct invalide",
      "REJETÉE par le moteur" in prompt2)

prompt1 = pa.construire_prompt_analyse(pf, WATCHLIST, CONTEXTE)
check("passe 1 : le poids est visible pour l'analyste aussi",
      "poids 16.0%" in prompt1)
check("passe 1 : les conditions de vente sont soumises au contrôle de déclenchement",
      "DÉCLENCHÉE" in prompt1)

# ═════════════════════════════════════════════════════════════════════════════
print()
if ko:
    print(f"❌ {len(ko)} échec(s) / {ok + len(ko)} : " + " · ".join(ko))
    sys.exit(1)
print(f"✅ {ok}/{ok} vérifications passées")
