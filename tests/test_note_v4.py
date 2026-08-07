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

import note_v4
from note_v4 import rampe, cloche, calcule_note, _tcam

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

print("\n— Rupture de périmètre : on ne mesure pas à travers une marche —")
# Adyen sortait à « −33,3 % par an » (passage du volume traité au revenu net en
# 2023) et Western Digital à « −10,5 % » (séparation de SanDisk), tous deux
# publiés comme des FAITS sur leur fiche, tous deux à 0 sur 7. Les deux
# croissent de ~20 % sur leur périmètre actuel.
ADYEN = [(2022, 8936), (2023, 1863), (2024, 2226), (2025, 2647)]
g, n = _tcam(note_v4.apres_rupture(ADYEN))
check("un effondrement ÷4,8 tronque la série au périmètre actuel",
      round(g, 1) == 19.2 and n == 2, f"{g} % sur {n} ans")
check("la troncature retient bien les exercices postérieurs à la marche",
      note_v4.apres_rupture(ADYEN)[0][0] == 2023)
# Une marche MONTANTE est l'hypercroissance elle-même : la tronquer effacerait
# ce qu'on cherche à voir.
NBIS = [(2022, 14), (2023, 10), (2024, 92), (2025, 530)]
check("une marche montante ×9 est CONSERVÉE (hypercroissance, pas rupture)",
      note_v4.apres_rupture(NBIS) == NBIS)
check("un compounder régulier n'est jamais tronqué",
      note_v4.apres_rupture([(2021, 100), (2022, 112), (2023, 125), (2024, 140)])
      == [(2021, 100), (2022, 112), (2023, 125), (2024, 140)])
check("une baisse de moitié (cyclique violente) ne déclenche PAS la troncature",
      note_v4.apres_rupture([(2022, 100), (2023, 50), (2024, 60), (2025, 80)])[0][0] == 2022)
check("tronquée sous trois points, la croissance est retirée, pas devinée",
      _tcam(note_v4.apres_rupture([(2023, 900), (2024, 100), (2025, 130)]))
      == (None, None))
# Le BPA n'est JAMAIS tronqué : Broadcom passe de 2,84 à 0,64 en 2019 par pur
# amortissement d'acquisitions, sans rien céder — la règle du périmètre ne vaut
# que pour le chiffre d'affaires.
check("la règle du périmètre ne s'applique pas au bénéfice par action",
      _tcam([(2016, -4.86), (2017, 0.402), (2018, 2.844), (2019, 0.643),
             (2020, 0.633), (2021, 1.5), (2022, 2.653), (2023, 3.298),
             (2024, 1.23), (2025, 4.77)])[1] == 8)
# La régularité lit la MÊME série tronquée : compter une « année de recul » qui
# n'est qu'un changement de définition punirait deux fois la même illusion.
# Ici il ne reste que trois points : le critère est retiré avec son motif,
# jamais rempli par une valeur commode.
_c_adyen = calcule_note({"an": [{"fin": f"{y}-12-31", "ca": c, "rn": 10, "eps": 1.0}
                                for y, c in ADYEN],
                         "prix": 100.0, "banque": False, "meme_devise": True})["criteres"]
check("le taux de croissance publié devient vrai (+19,2 % au lieu de −33,3 %)",
      next(c for c in _c_adyen if c["id"] == "ca")["valeur"] == 19.2)
check("la régularité lit la même série, et se retire si elle devient trop courte",
      next(c["motif"] for c in _c_adyen if c["id"] == "regularite") == "historique trop court")

print("\n— Contexte témoin complet (compounder) —")
n = calcule_note(CTX_TEMOIN)
check("total dans [0,100]", 0 <= n["total"] <= 100, str(n["total"]))
check("compounder bien noté (≥70)", n["total"] >= 70, str(n["total"]))
check("couverture pleine", n["couverture"] == 100, str(n["couverture"]))
check("15 critères émis (le RSI a quitté la note le 07/08)",
      len(n["criteres"]) == 15, str(len(n["criteres"])))
check("le RSI n'est plus un critère noté",
      not any(c["id"] == "rsi" for c in n["criteres"]))
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
             price_to_book=1.4, roa_pct=0.95, levier_actifs=12.0)
nb = calcule_note(ctx_b)
check("plus AUCUN critère de qualité retiré : tout est substitué",
      all(c["pts"] is not None for c in nb["criteres"] if c["bloc"] == "q"),
      str([(c["id"], c["motif"]) for c in nb["criteres"]
           if c["bloc"] == "q" and c["pts"] is None]))
# La conversion vient d'un champ CALCULÉ par le screener (flux disponible et
# résultat net du même exercice), pas du quotient de deux marges glissantes de
# provenances différentes — c'est ce quotient qui donnait 12 % à Microsoft.
c_conv = next(c for c in calcule_note(dict(CTX_TEMOIN, conversion_pct=78.0))["criteres"]
              if c["id"] == "conversion")
check("la conversion calculée prime sur le quotient des marges",
      c_conv["valeur"] == 78 and "78 €" in c_conv["phrase"], str(c_conv))
c_repli = next(c for c in calcule_note(CTX_TEMOIN)["criteres"] if c["id"] == "conversion")
check("sans conversion calculée, le repli marge FCF / marge nette tient encore",
      c_repli["valeur"] == round(22.0 / 24.0 * 100), str(c_repli["valeur"]))
c_abs = next(c for c in calcule_note(dict(CTX_TEMOIN, fcf_margin_pct=None))["criteres"]
             if c["id"] == "conversion")
check("ni l'un ni l'autre : le critère est retiré avec son motif",
      c_abs["pts"] is None and c_abs["motif"], str(c_abs))
check("le rendement des actifs remplace la conversion en cash",
      any(c["id"] == "rendement_actifs" for c in nb["criteres"])
      and not any(c["id"] == "conversion" for c in nb["criteres"]))
check("le levier actifs/fonds propres remplace dette/CP",
      any(c["id"] == "levier_actifs" for c in nb["criteres"])
      and not any(c["id"] == "bilan" for c in nb["criteres"]))
check("le rendement du cash ne s'applique pas à un bilan bancaire",
      not any(c["id"] == "rdt_cash" for c in nb["criteres"]))
c_roa = next(c for c in nb["criteres"] if c["id"] == "rendement_actifs")
check("ROA 0,95 % noté sur la rampe 0,3-1,3", c_roa["pts"] == rampe(0.95, 0.3, 1.3, 7))
check("la phrase du ROA explique la substitution",
      "pendant bancaire" in c_roa["phrase"], c_roa["phrase"])
c_lev = next(c for c in nb["criteres"] if c["id"] == "levier_actifs")
check("levier 12× noté sur la rampe inversée 25→8",
      c_lev["pts"] == rampe(12.0, 25, 8, 5), str(c_lev["pts"]))
check("qualité bancaire mesurée en ENTIER : dispo 35/35, plus de renormalisation",
      nb["blocs"]["q"]["dispo"] == 35, str(nb["blocs"]["q"]))
# Sans les données de bilan : retrait motivé, pas de zéro muet
nb2 = calcule_note(dict(ctx_b, roa_pct=None, levier_actifs=None))
check("actifs non publiés : retraits motivés (« actifs au bilan non publiés »)",
      all("actifs au bilan" in (c["motif"] or "") for c in nb2["criteres"]
          if c["id"] in ("rendement_actifs", "levier_actifs")))
check("un levier négatif ou nul est refusé",
      next(c["pts"] for c in calcule_note(dict(ctx_b, levier_actifs=-3))["criteres"]
           if c["id"] == "levier_actifs") is None)
check("un assureur très capitalisé (levier 6×) prend le maximum",
      next(c["pts"] for c in calcule_note(dict(ctx_b, levier_actifs=6.0))["criteres"]
           if c["id"] == "levier_actifs") == 5.0)
check("une banque au levier Credit Suisse (26×) prend zéro",
      next(c["pts"] for c in calcule_note(dict(ctx_b, levier_actifs=26.0))["criteres"]
           if c["id"] == "levier_actifs") == 0.0)
check("le ROE bancaire utilise la rampe 6-15 %",
      next(c for c in nb["criteres"] if c["id"] == "roe")["pts"] == 9.0)
# (l'ancien test « renormalisée sur 23 » est obsolète : la substitution
# rend la qualité bancaire mesurable en entier, c'est tout son intérêt)
check("la qualité bancaire n'a plus besoin de renormalisation",
      nb["blocs"]["q"]["max"] == 35 and nb["blocs"]["q"]["dispo"] == 35
      and nb["blocs"]["q"]["pts"] is not None)
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
check("levier >200 % : ROE tempéré (17,5 % effectif sur rampe 8-30)",
      c_roe["pts"] == rampe(17.5, 8, 30, 9), str(c_roe))
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
# ±15 depuis le 07/08 : il faut un vrai écart de tendance pour le plein.
nm = calcule_note({"z": 0.0, "rsi": 50.0, "ecart_mm_pct": 20.0})
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
check("étirement haussier pénalisé (z=+2 → 4/8)", pz_haut == 4.0, str(pz_haut))
check("étirement baissier pénalisé (z=−2,25 → 4/8)", pz_bas == 4.0, str(pz_bas))

# ── Calibration mesurée sur l'univers publié (audit du 07/08) ──────────────
print("\n— Les rampes notent-elles vraiment, ou distribuent-elles ? —")
# Un critère dont la rampe est plus étroite que la dispersion de l'univers
# cesse de classer et devient un interrupteur. Ces trois-là ne notaient que
# 11 à 19 % des titres ; les seuils sont désormais ceux de la population.
_p = lambda ctx, cid: next(c["pts"] for c in calcule_note(ctx)["criteres"]
                           if c["id"] == cid)
check("tendance : la médiane de l'univers (+10 %) est NOTÉE, pas plafonnée",
      0 < _p(dict(CTX_TEMOIN, ecart_mm_pct=10.0), "tendance") < 7,
      str(_p(dict(CTX_TEMOIN, ecart_mm_pct=10.0), "tendance")))
check("tendance : ±15 % reste le plein et le zéro",
      _p(dict(CTX_TEMOIN, ecart_mm_pct=15.0), "tendance") == 7.0
      and _p(dict(CTX_TEMOIN, ecart_mm_pct=-15.0), "tendance") == 0.0)
# BPA publié 7,79 ; PER 28,7 sur un cours de 300 ⇒ BPA estimé 10,45, soit
# +34 % — exactement la médiane des attentes relevée sur l'univers publié.
_att = _p(dict(CTX_TEMOIN, pe_prev=[{"exercice": 2026, "per": 28.7}], prix=300.0),
          "attendu")
check("attendu : la médiane des attentes (+34 %) est NOTÉE, pas plafonnée",
      0 < _att < 7, str(_att))
check("le momentum reste sur 15 après le retrait du RSI",
      calcule_note(CTX_TEMOIN)["blocs"]["m"]["max"] == 15)
# Les trois autres rampes dont la borne haute finissait SOUS la médiane de
# l'univers publié : un critère qui donne son maximum au titre médian ne classe
# plus la moitié du peloton.
check("roe : la médiane de l'univers (23 %) est NOTÉE, pas plafonnée",
      0 < _p(dict(CTX_TEMOIN, roe=0.232), "roe") < 9,
      str(_p(dict(CTX_TEMOIN, roe=0.232), "roe")))
check("conversion : la médiane (107 %) est NOTÉE, pas plafonnée",
      0 < _p(dict(CTX_TEMOIN, conversion_pct=107.0), "conversion") < 7,
      str(_p(dict(CTX_TEMOIN, conversion_pct=107.0), "conversion")))
check("conversion : au-delà de 120 % la valeur reste bridée",
      _p(dict(CTX_TEMOIN, conversion_pct=200.0), "conversion")
      == _p(dict(CTX_TEMOIN, conversion_pct=120.0), "conversion"))
_an_h = [{"fin": f"{y}-12-31", "ca": 100, "rn": 20, "eps": 2.0, "per": 20.0}
         for y in range(2016, 2026)]
check("histoire : payer 1,3 fois son propre passé n'est plus un zéro",
      _p(dict(CTX_TEMOIN, an=_an_h, trailing_pe=26.0), "histoire") > 0,
      str(_p(dict(CTX_TEMOIN, an=_an_h, trailing_pe=26.0), "histoire")))
check("histoire : 2 fois son propre passé reste un zéro",
      _p(dict(CTX_TEMOIN, an=_an_h, trailing_pe=40.0), "histoire") == 0.0)

print(f"\n{len(ok)}/{len(ok) + len(ko)} tests passés")
if ko:
    print("ÉCHECS :", ", ".join(ko))
    sys.exit(1)
