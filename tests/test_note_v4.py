"""Tests du moteur de notation v4 (note_v4.py) — script autonome, hors ligne.

    python3 tests/test_note_v4.py

Couvre : rampes et cloches (bornes, inversion), retraits avec motif +
renormalisation (par bloc et entre blocs), gardes de plausibilité (marge NBIS),
devise comptable différente (TSM), PEG prudent (min des deux croissances),
et un contexte complet type témoin.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from note_v4 import rampe, cloche, calcule_note

ok, ko = [], []


def check(nom, cond, detail=""):
    if cond:
        ok.append(nom)
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


# ── Un historique annuel synthétique de compounder (8 exercices) ─────────────
def _an_compounder():
    out = []
    ca, rn, eps, per = 50000, 10000, 4.0, 22.0
    for i, annee in enumerate(range(2018, 2026)):
        out.append({"fin": f"{annee}-12-31", "ca": round(ca), "rn": round(rn),
                    "eps": round(eps, 2), "per": round(per, 1), "src": "sec"})
        ca *= 1.12; rn *= 1.14; eps *= 1.13; per += 0.5
    return out


# Un compounder payé À SON PRIX : trailing 24× contre ~23,8× de médiane
# historique. (À 32× le même dossier tombe à 68 — c'est voulu, la valorisation
# pèse 25 pts : le premier jet de ce fixture l'a vérifié malgré lui.)
CTX_TEMOIN = {
    "an": _an_compounder(),
    "pe_prev": [{"exercice": 2026, "per": 24.0}, {"exercice": 2027, "per": 21.0}],
    "prix": 300.0,
    "trailing_pe": 24.0, "forward_pe": 24.0,
    "net_margin_pct": 24.0, "fcf_margin_pct": 22.0, "fcf_yield_pct": 3.0,
    "roe": 0.28, "debt_eq": 45.0,
    "banque": False, "meme_devise": True,
    "z": 0.4, "rsi": 55.0, "ecart_mm_pct": 2.5,
}


print("— Rampes et cloches —")
check("rampe : sous la borne basse → 0", rampe(1, 2, 20, 9) == 0.0)
check("rampe : au-dessus de la borne haute → max", rampe(25, 2, 20, 9) == 9.0)
check("rampe : milieu exact → moitié", rampe(11, 2, 20, 9) == 4.5)
check("rampe inversée (x1<x0) : bas = bon", rampe(0, 150, 0, 5) == 5.0)
check("rampe inversée : haut = mauvais", rampe(200, 150, 0, 5) == 0.0)
check("rampe inversée : milieu", rampe(75, 150, 0, 5) == 2.5)
check("rampe : None traverse", rampe(None, 0, 10, 5) is None)
check("cloche : plateau plein", cloche(0, -3, -1.5, 1, 3, 6) == 6.0)
check("cloche : bornes extrêmes → 0",
      cloche(-3, -3, -1.5, 1, 3, 6) == 0.0 and cloche(3.5, -3, -1.5, 1, 3, 6) == 0.0)
check("cloche : rampe montante à mi-chemin", cloche(-2.25, -3, -1.5, 1, 3, 6) == 3.0)
check("cloche : rampe descendante à mi-chemin", cloche(2, -3, -1.5, 1, 3, 6) == 3.0)
check("cloche : None traverse", cloche(None, 20, 35, 65, 80, 3) is None)

print("\n— Contexte témoin complet (compounder) —")
n = calcule_note(CTX_TEMOIN)
check("total dans [0,100]", 0 <= n["total"] <= 100, str(n["total"]))
check("compounder bien noté (≥70)", n["total"] >= 70, str(n["total"]))
check("couverture pleine", n["couverture"] == 100, str(n["couverture"]))
check("16 critères émis", len(n["criteres"]) == 16, str(len(n["criteres"])))
check("4 blocs, tous notés",
      set(n["blocs"]) == {"q", "c", "v", "m"} and
      all(v["pts"] is not None for v in n["blocs"].values()))
check("aucun retrait", all(c["motif"] is None for c in n["criteres"]))
check("chaque critère noté porte une phrase",
      all(c["phrase"] for c in n["criteres"] if c["pts"] is not None))
check("pts ≤ max partout",
      all(c["pts"] <= c["max"] for c in n["criteres"] if c["pts"] is not None))
check("total = somme des blocs (couverture pleine)",
      n["total"] == round(sum(v["pts"] for v in n["blocs"].values())),
      str(n["total"]))
check("la note ne publie pas de lettre (décision : /100 conservé)",
      "lettre" not in n)

print("\n— Banque (type JPM) : retraits + renormalisation du bloc —")
ctx_b = dict(CTX_TEMOIN, banque=True, fcf_margin_pct=None, fcf_yield_pct=None,
             roe=0.16, debt_eq=None, trailing_pe=12.0, forward_pe=11.0)
nb = calcule_note(ctx_b)
retires = {c["id"]: c["motif"] for c in nb["criteres"] if c["pts"] is None}
check("conversion, bilan et rdt_cash retirés avec motif",
      {"conversion", "bilan", "rdt_cash"} <= set(retires)
      and all(retires[k] for k in ("conversion", "bilan", "rdt_cash")),
      str(retires))
check("le ROE bancaire utilise la rampe 6-15 %",
      next(c for c in nb["criteres"] if c["id"] == "roe")["pts"] == 9.0)
check("qualité renormalisée sur 35 malgré les retraits",
      nb["blocs"]["q"]["max"] == 35 and nb["blocs"]["q"]["pts"] is not None
      and nb["blocs"]["q"]["dispo"] == 23)
check("une banque rentable et bon marché reste bien notée (≥60)",
      nb["total"] >= 60, str(nb["total"]))

print("\n— Gardes de plausibilité et cas dégradés —")
# NBIS : marges de holding aberrantes → le critère marge ne note pas
an_nbis = [{"fin": f"{y}-12-31", "ca": 100, "rn": 1764, "eps": 1.0} for y in (2021, 2022, 2023, 2024)]
nn = calcule_note({"an": an_nbis})
c_marge = next(c for c in nn["criteres"] if c["id"] == "marge")
check("marge >100 % implausible → critère retiré",
      c_marge["pts"] is None and c_marge["motif"], str(c_marge))
check("mais la constance note (4 exercices rn connus)",
      next(c for c in nn["criteres"] if c["id"] == "constance")["pts"] is not None)

# ROE dopé au levier : tempéré, pas cru
ctx_lev = dict(CTX_TEMOIN, roe=0.35, debt_eq=320.0)
c_roe = next(c for c in calcule_note(ctx_lev)["criteres"] if c["id"] == "roe")
check("levier >200 % : ROE tempéré (17,5 % effectif sur rampe 8-20)",
      c_roe["pts"] == rampe(17.5, 8, 20, 9), str(c_roe))
check("mais la valeur affichée reste le ROE réel", c_roe["valeur"] == 35.0)

# Devise comptable différente (TSM) : pas d'estimé, motif explicite
ctx_tsm = dict(CTX_TEMOIN, meme_devise=False)
c_att = next(c for c in calcule_note(ctx_tsm)["criteres"] if c["id"] == "attendu")
check("devise différente : croissance attendue retirée",
      c_att["pts"] is None and "devise" in c_att["motif"], str(c_att["motif"]))

print("\n— PEG prudent —")
# g_att (déduit de pe_prev) et g_bpa démontré : le PEG prend le PLUS PETIT
n2 = calcule_note(CTX_TEMOIN)
c_peg = next(c for c in n2["criteres"] if c["id"] == "peg")
c_bpa = next(c for c in n2["criteres"] if c["id"] == "bpa")
c_att = next(c for c in n2["criteres"] if c["id"] == "attendu")
# Les valeurs affichées sont arrondies à 1 décimale : tolérance de 0,02
g_min = min(c_bpa["valeur"], c_att["valeur"])
check("PEG = forward PE ÷ min(attendu, démontré)",
      abs(c_peg["valeur"] - 24.0 / g_min) <= 0.02, f"{c_peg['valeur']} vs {24.0/g_min:.3f}")
check("la croissance retenue est bien la plus petite des deux",
      c_bpa["valeur"] != c_att["valeur"], f"bpa={c_bpa['valeur']} att={c_att['valeur']}")
# Sans estimé : le PEG retombe sur la croissance démontrée seule
n3 = calcule_note(dict(CTX_TEMOIN, pe_prev=None))
c_peg3 = next(c for c in n3["criteres"] if c["id"] == "peg")
check("sans estimation, le PEG utilise la croissance démontrée",
      c_peg3["pts"] is not None and abs(c_peg3["valeur"] - 24.0 / c_bpa["valeur"]) <= 0.02)

print("\n— Renormalisation entre blocs (données minimales) —")
# Seulement du momentum PLEIN (écart ≥+5 % = haut de rampe) : Q, C, V vides
# → total = momentum renormalisé sur 100
nm = calcule_note({"z": 0.0, "rsi": 50.0, "ecart_mm_pct": 6.0})
check("blocs sans donnée → pts None",
      all(nm["blocs"][b]["pts"] is None for b in ("q", "c", "v")))
check("total renormalisé sur les blocs restants (momentum plein → 100)",
      nm["total"] == 100, str(nm["total"]))
check("couverture basse le signale", nm["couverture"] < 25, str(nm["couverture"]))
# Rien du tout : total 0, pas d'exception
nz = calcule_note({})
check("contexte vide → total 0 sans exception", nz["total"] == 0)
check("contexte vide → couverture 0", nz["couverture"] == 0)

print("\n— Momentum : symétrie de la cloche z —")
haut = calcule_note(dict(CTX_TEMOIN, z=2.0))
bas = calcule_note(dict(CTX_TEMOIN, z=-2.25))
pz_haut = next(c for c in haut["criteres"] if c["id"] == "position")["pts"]
pz_bas = next(c for c in bas["criteres"] if c["id"] == "position")["pts"]
check("étirement haussier pénalisé (z=+2 → 3/6)", pz_haut == 3.0, str(pz_haut))
check("étirement baissier pénalisé (z=−2,25 → 3/6)", pz_bas == 3.0, str(pz_bas))

print(f"\n{len(ok)}/{len(ok) + len(ko)} tests passés")
if ko:
    print("ÉCHECS :", ", ".join(ko))
    sys.exit(1)
