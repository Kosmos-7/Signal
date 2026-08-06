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
             roe=0.16, debt_eq=None, trailing_pe=12.0, forward_pe=11.0,
             price_to_book=1.4)
nb = calcule_note(ctx_b)
retires = {c["id"]: c["motif"] for c in nb["criteres"] if c["pts"] is None}
check("conversion et bilan retirés avec motif",
      {"conversion", "bilan"} <= set(retires)
      and all(retires[k] for k in ("conversion", "bilan")),
      str(retires))
check("le rendement du cash ne s'applique pas à un bilan bancaire",
      not any(c["id"] == "rdt_cash" for c in nb["criteres"]))
check("le ROE bancaire utilise la rampe 6-15 %",
      next(c for c in nb["criteres"] if c["id"] == "roe")["pts"] == 9.0)
check("qualité renormalisée sur 35 malgré les retraits",
      nb["blocs"]["q"]["max"] == 35 and nb["blocs"]["q"]["pts"] is not None
      and nb["blocs"]["q"]["dispo"] == 23)
check("une banque rentable et bon marché reste bien notée (≥60)",
      nb["total"] >= 60, str(nb["total"]))

print("\n— Cours / actifs nets : la mesure qui manquait aux métiers de bilan —")
c_an = next(c for c in nb["criteres"] if c["id"] == "actifs_nets")
check("le critère remplace le rendement du cash pour une banque",
      c_an["pts"] is not None and c_an["max"] == 5 and c_an["bloc"] == "v")
check("1,4× les actifs nets se note sur la rampe 3 → 0,8",
      c_an["pts"] == rampe(1.4, 3, 0.8, 5), str(c_an["pts"]))
check("la phrase énonce le multiple payé",
      "actifs nets comptables" in c_an["phrase"], c_an["phrase"])
check("valorisation pleinement mesurée : 4 critères sur 4",
      nb["blocs"]["v"]["dispo"] == nb["blocs"]["v"]["max"],
      f"{nb['blocs']['v']['dispo']}/{nb['blocs']['v']['max']}")
# Le grief d'origine : une banque était jugée sur moins de critères que le reste
c_ref = calcule_note(CTX_TEMOIN)["couverture"]
check("la couverture d'une banque rejoint celle d'un industriel (écart ≤ 15 pts)",
      c_ref - nb["couverture"] <= 15, f"{nb['couverture']}% vs {c_ref}%")
# Moins cher = plus de points, la qualité du bilan étant notée ailleurs (MECE)
cher = calcule_note(dict(ctx_b, price_to_book=3.5))
bon  = calcule_note(dict(ctx_b, price_to_book=0.7))
p_cher = next(c["pts"] for c in cher["criteres"] if c["id"] == "actifs_nets")
p_bon  = next(c["pts"] for c in bon["criteres"] if c["id"] == "actifs_nets")
check("3,5× les actifs nets → 0 point", p_cher == 0.0, str(p_cher))
check("0,7× les actifs nets → 5 points", p_bon == 5.0, str(p_bon))
# Sans la donnée, retrait motivé plutôt que zéro muet
sans = calcule_note(dict(ctx_b, price_to_book=None))
c_sans = next(c for c in sans["criteres"] if c["id"] == "actifs_nets")
check("actifs nets absents : critère retiré avec motif",
      c_sans["pts"] is None and c_sans["motif"], str(c_sans))
# Le critère est réservé aux bilans financiers
c_ind = calcule_note(CTX_TEMOIN)
check("un industriel garde le rendement du cash, pas les actifs nets",
      any(c["id"] == "rdt_cash" for c in c_ind["criteres"])
      and not any(c["id"] == "actifs_nets" for c in c_ind["criteres"]))
check("un cours/actifs nets négatif ou nul est refusé",
      next(c["pts"] for c in calcule_note(dict(ctx_b, price_to_book=-0.5))["criteres"]
           if c["id"] == "actifs_nets") is None)

print("\n— Prudence de la renormalisation : l'ignorance n'est ni prime ni punition —")
# Un bloc mesuré en ENTIER et parfait doit atteindre son maximum
plein = calcule_note(CTX_TEMOIN)
# Une banque parfaite sur ses 3 critères de qualité ne doit PLUS saturer à 35/35
_bq = dict(CTX_TEMOIN, banque=True, fcf_margin_pct=None, fcf_yield_pct=None,
           roe=0.30, debt_eq=None, price_to_book=1.0)
part = calcule_note(_bq)
check("un bloc partiel et parfait ne sature plus comme un bloc complet",
      part["blocs"]["q"]["pts"] < part["blocs"]["q"]["max"],
      f"{part['blocs']['q']['pts']}/{part['blocs']['q']['max']}")
check("mais il reste bien noté (au-dessus des deux tiers)",
      part["blocs"]["q"]["pts"] > 0.66 * part["blocs"]["q"]["max"],
      str(part["blocs"]["q"]["pts"]))
# Symétrie : un bloc partiel et NUL ne doit pas tomber à zéro non plus
_nul = dict(_bq, roe=0.0, net_margin_pct=0.0,
            an=[{"fin": f"{y}-12-31", "ca": 100, "rn": 0, "eps": 0.01}
                for y in range(2019, 2026)])
bas = calcule_note(_nul)
check("un bloc partiel et médiocre ne tombe pas à zéro (pas de zéro muet)",
      bas["blocs"]["q"]["pts"] > 0, str(bas["blocs"]["q"]["pts"]))
check("les deux extrêmes se resserrent vers le milieu",
      part["blocs"]["q"]["pts"] - bas["blocs"]["q"]["pts"]
      < plein["blocs"]["q"]["max"],
      f"{part['blocs']['q']['pts']} vs {bas['blocs']['q']['pts']}")
# Invariant : bloc mesuré en entier → points = somme brute des critères,
# la prudence ne s'applique qu'à la part NON mesurée (ici nulle).
_somme_c = sum(c["pts"] for c in plein["criteres"]
               if c["bloc"] == "c" and c["pts"] is not None)
check("un bloc intégralement mesuré n'est pas touché par la prudence",
      plein["blocs"]["c"]["dispo"] == plein["blocs"]["c"]["max"]
      and abs(plein["blocs"]["c"]["pts"] - round(_somme_c, 1)) < 0.05,
      f"{plein['blocs']['c']['pts']} vs somme {_somme_c}")

print("\n— Croissance : on démarre au premier exercice exploitable —")
from note_v4 import _tcam
# Cas Broadcom : base négative puis dix ans de trajectoire lisible
BRCM = [(2016, -4.86), (2017, 0.402), (2018, 2.844), (2019, 0.643), (2020, 0.633),
        (2021, 1.5), (2022, 2.653), (2023, 3.298), (2024, 1.23), (2025, 4.77)]
g, n = _tcam(BRCM)
check("base négative : la mesure démarre au premier exercice positif",
      g is not None and n == 8, f"g={g} n={n}")
check("le taux est celui de la fenêtre retenue, pas de l'historique entier",
      abs(g - ((4.77 / 0.402) ** (1 / 8) - 1) * 100) < 1e-9, str(g))
check("la fenêtre rendue sert à écrire la phrase",
      _tcam([(2020, 1.0), (2021, 2.0), (2022, 3.0), (2023, 4.0)])[1] == 3)
check("arriver en perte n'est pas une croissance",
      _tcam([(2021, 1.0), (2022, 2.0), (2023, 3.0), (2024, -1.0)]) == (None, None))
check("moins de trois points exploitables après la base négative : on renonce",
      _tcam([(2021, -5.0), (2022, -2.0), (2023, 1.0), (2024, 2.0)]) == (None, None))
check("série trop courte : inchangé", _tcam([(2023, 1.0), (2024, 2.0)]) == (None, None))
check("série entièrement négative : rien à mesurer",
      _tcam([(2021, -1.0), (2022, -2.0), (2023, -3.0)]) == (None, None))
# La note doit désormais compter le critère au lieu de le retirer
n_brcm = calcule_note({"an": [{"fin": f"{y}-12-31", "ca": 1000 + 100 * i, "rn": 500,
                               "eps": v} for i, (y, v) in enumerate(BRCM)]})
c_bpa = next(c for c in n_brcm["criteres"] if c["id"] == "bpa")
check("le critère BPA est noté au lieu d'être retiré",
      c_bpa["pts"] is not None, str(c_bpa.get("motif")))
check("la phrase signale la sortie de pertes",
      "premier exercice bénéficiaire" in (c_bpa["phrase"] or ""), c_bpa["phrase"])

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
