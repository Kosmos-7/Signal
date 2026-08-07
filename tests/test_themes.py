#!/usr/bin/env python3
"""Tests de non-régression des watchlists thématiques.

Aucun accès réseau : les modules lourds (ta, yfinance, requests) sont bouchés,
et les données sont simulées. On teste le contrat, pas les données de marché.

    python tests/test_themes.py
"""
import json
import os
import re
import sys
import types

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

# ── Bouchons : screener importe des modules absents de l'env de test ────────
for nom, attrs in [("ta", {}), ("ta.momentum", {"RSIIndicator": object}),
                   ("yfinance", {"Ticker": object}),
                   ("requests", {"get": lambda *a, **k: None}),
                   ("pandas", {"Series": object, "DataFrame": object})]:
    m = types.ModuleType(nom)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(nom, m)
sys.modules["ta"].momentum = sys.modules["ta.momentum"]

import themes                    # noqa: E402
import screener                  # noqa: E402
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


print("— Taxonomie —")
ids = [t["id"] for t in themes.THEMES]
check("identifiants uniques", len(ids) == len(set(ids)))
check("2 thèmes curés publiés (financials retirée le 06/08)",
      len(themes.THEMES_CURES) == 2)
check("chaque thème a thèse, inversion et biais",
      all(t.get("thesis") and t.get("inversion") and t.get("biais") for t in themes.THEMES))
check("les thèmes calculés publient leur règle en clair",
      all(t.get("regle_texte") for t in themes.THEMES_CALCULES))
check("aucun thème curé étriqué", all(len(t["tickers"]) >= 20 for t in themes.THEMES_CURES))
# Un thème de chaîne de valeur ne vaut que si chaque maillon a un représentant.
# On ne peut pas tester la sémantique, mais on peut tester la taille minimale
# qui rend une chaîne à six maillons crédible.
_infra = themes.THEMES_BY_ID.get("infra-ia")
check("infra-ia couvre assez de titres pour six maillons",
      _infra and len(_infra["tickers"]) >= 40, f"{len(_infra['tickers']) if _infra else 0}")

# Doctrine de nommage : ne jamais emprunter le vocabulaire d'un concept non calculé
interdits = ["moat", "douve", "marge de sécurité", "valeur intrinsèque"]
textes = " ".join(f"{t['label']} {t['sous_titre']} {t['thesis']}" for t in themes.THEMES).lower()
fautes = [m for m in interdits if m in textes]
check("aucun vocabulaire emprunté dans les libellés et thèses", not fautes, f"trouvé : {fautes}")

# Un texte qui cite les titres retenus devient faux tout seul la semaine
# suivante, la liste etant recalculee a chaque run. Le cas reel etait un nom de
# societe et un compte, que ce test ne peut pas voir ; il attrape au moins la
# forme la plus tentante, le ticker cite en exemple dans sa propre these.
fautifs = []
for t in themes.THEMES:
    texte = " ".join(str(t.get(c) or "") for c in ("thesis", "sous_titre", "biais",
                                                   "inversion", "regle_texte"))
    for tk in t.get("tickers", []):
        # Frontieres de mot : « V » ou « ON » matcheraient n'importe quoi.
        if re.search(r"(?<![\w.])" + re.escape(tk) + r"(?![\w.])", texte):
            fautifs.append(f"{t['id']}→{tk}")
check("aucune description ne cite un ticker de sa propre liste", not fautifs, str(fautifs))

print("\n— Univers dérivé —")
u = set(themes.univers_thematique())
check("les titres recalés par la validation sont absents",
      not (u & set(themes.ECARTES_VALIDATION)), f"{u & set(themes.ECARTES_VALIDATION)}")
check("chaque titre de thème est dans l'univers du screener",
      u <= set(screener.UNIVERS), f"manquants : {sorted(u - set(screener.UNIVERS))[:5]}")
check("l'univers historique est préservé",
      {"AAPL", "NVDA", "MC.PA", "ASML.AS", "ORSTED.CO"} <= set(screener.UNIVERS))
check("univers dans un ordre déterministe", screener.UNIVERS == sorted(set(screener.UNIVERS)))

print("\n— Devises —")
for t, attendu in [("6954.T", "JPY"), ("8035.T", "JPY"), ("000660.KS", "KRW"),
                   ("005930.KS", "KRW"), ("LDO.MI", "EUR"), ("SAAB-B.ST", "SEK"),
                   ("ABBN.SW", "CHF"), ("BA.L", "GBP"), ("RHHBY", "USD"),
                   ("ORSTED.CO", "DKK"), ("NVDA", "USD")]:
    check(f"{t} → {attendu}", pa.detect_currency(t) == attendu, f"obtenu {pa.detect_currency(t)}")
check("JPY et KRW ont une paire de change et un repli",
      {"JPY", "KRW"} <= set(pa._FX_PAIRS) and {"JPY", "KRW"} <= set(pa._FX_FALLBACK))
# Le code TSE est ambigu (Tokyo vs Toronto) : il ne doit pas décider seul
check("le code marché TSE ne bascule pas en JPY", pa.detect_currency("XYZ", "TSE") != "JPY")

print("\n— Sleep Finnhub —")
_k = screener.FINNHUB_KEY
screener.FINNHUB_KEY = "test"
check("appel émis pour un titre US", screener._finnhub_appel_emis("NVDA"))
check("court-circuit pour un titre japonais", not screener._finnhub_appel_emis("6954.T"))
check("court-circuit pour un titre européen", not screener._finnhub_appel_emis("ASML.AS"))
screener.FINNHUB_KEY = ""
check("aucun appel sans clé", not screener._finnhub_appel_emis("NVDA"))
screener.FINNHUB_KEY = _k

print("\n— Thèmes calculés (mécanisme conservé, aucun publié) —")
check("aucun thème calculé publié", themes.THEMES_CALCULES == [])
check("breakdown vide ne plante pas", themes.themes_calcules_pour({}) == [] and
      themes.themes_calcules_pour(None) == [])
check("breakdown complet ne rattache à rien",
      themes.themes_calcules_pour({"regression_z": -3.0, "qualite": 40}) == [])

print("\n— Union de l'univers achetable —")
universe = {
    "themes": [
        {"id": "ia", "label": "Intelligence artificielle", "scores": 3, "status": "ok",
         "members": ["NVDA", "VRT", "ETN"]},
        {"id": "electrification", "label": "Électrification & réseaux", "scores": 3, "status": "ok",
         "members": ["VRT", "ETN", "NEE"]},
    ],
    "stocks": {
        "NVDA": {"nom": "NVIDIA", "score": 92, "secteur": "Technologie", "market": "NMS",
                 "themes": ["ia"], "prix": 180.0, "devise": "USD", "qualite": 40},
        "VRT": {"nom": "Vertiv", "score": 78, "secteur": "Industrie", "market": "NYQ",
                "themes": ["ia", "electrification"], "prix": 120.0, "devise": "USD"},
        "NEE": {"nom": "NextEra", "score": 70, "secteur": "Services pub.", "market": "NYQ",
                "themes": ["electrification"], "prix": 80.0, "devise": "USD"},
        "SANS": {"nom": "Sans secteur", "score": 88, "secteur": "—", "market": "NYQ",
                 "themes": ["ia"], "prix": 10.0, "devise": "USD"},
    },
}
wl = {"stocks": [{"ticker": "NVDA", "name": "NVIDIA", "sector": "Technologie",
                  "market": "NMS", "score": 92, "breakdown": {"rsi": 52}}]}
fusion = pa.fusionner_univers_achetable(wl, universe)
tick = {s["ticker"] for s in fusion}
check("union du top 30 et des titres thématiques", tick == {"NVDA", "VRT", "NEE"}, tick)
check("un titre sans secteur n'est jamais rendu achetable", "SANS" not in tick)
nvda = next(s for s in fusion if s["ticker"] == "NVDA")
check("le top 30 prime sur la version compacte",
      nvda["origine"] == "top30" and nvda["breakdown"].get("rsi") == 52)
check("le top 30 est enrichi de ses thèmes", nvda["themes"] == ["ia"])
vrt = next(s for s in fusion if s["ticker"] == "VRT")
check("un titre thématique est marqué comme tel", vrt["origine"] == "theme")
check("son breakdown compact est exploitable", vrt["breakdown"]["prix"] == 120.0)
check("univers vide = aucun ajout, pas de plantage",
      len(pa.fusionner_univers_achetable({"stocks": []}, {})) == 0)

print("\n— Concentration thématique —")
positions = [{"ticker": "VRT", "valeur_actuelle": 3000, "sector": "Industrie"},
             {"ticker": "ETN", "valeur_actuelle": 2500, "sector": "Industrie"},
             {"ticker": "NEE", "valeur_actuelle": 2000, "sector": "Services pub."}]
cl = pa.clusters_thematiques(positions, 20000, universe)
elec = next((c for c in cl if c["theme"] == "electrification"), None)
check("une thèse transverse à 2 secteurs est vue comme un bloc",
      elec and elec["pct"] == 37.5, elec)
check("tri par poids décroissant", [c["pct"] for c in cl] == sorted([c["pct"] for c in cl], reverse=True))
check("capital nul ne plante pas", pa.clusters_thematiques(positions, 0, universe) == [])
check("univers absent ne plante pas", pa.clusters_thematiques(positions, 20000, {}) == [])

print("\n— Sérialisation —")
meta = themes.meta_publique()
check("les métadonnées publiques sont sérialisables (pas de callable)",
      json.dumps(meta, ensure_ascii=False, allow_nan=False) and
      all("regle" not in m and "tri" not in m for m in meta))
check("un identifiant par thème dans les métadonnées", len(meta) == len(themes.THEMES))
# ── Éligibilité PEA ─────────────────────────────────────────────────────────
# Le critère est JURIDIQUE, pas mesuré : ces tests protègent une donnée écrite
# à la main, là où le reste du fichier protège du code. C'est justement la
# donnée qui se périme en silence — une redomiciliation ne fait bouger aucun
# cours.
print("\n— Éligibilité PEA —")

pea = themes.THEMES_BY_ID["pea"]
check("le thème PEA est de kind « filtre »", pea["kind"] == "filtre")
check("il publie sa règle en clair", bool(pea.get("regle_texte")))
check("il borne sa liste", pea.get("top") == themes.TOP_PEA == 20)

check("aucun ticker n'est à la fois éligible et inéligible",
      not (set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES)),
      str(sorted(set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES))))
check("chaque éligible porte son pays de siège",
      all(isinstance(v, str) and "·" in v for v in themes.PEA_ELIGIBLES.values()))
check("chaque inéligible porte son motif",
      all(isinstance(v, str) and len(v) > 8 for v in themes.PEA_INELIGIBLES.values()))
check("les tickers du thème sont exactement le registre",
      set(pea["tickers"]) == set(themes.PEA_ELIGIBLES))
check("assez d'éligibles pour que « top 20 » sélectionne vraiment",
      len(themes.PEA_ELIGIBLES) >= 2 * themes.TOP_PEA,
      f"{len(themes.PEA_ELIGIBLES)} éligibles")

# Le piège que ce thème existe pour montrer : une place de cotation américaine
# n'empêche pas l'éligibilité. Si ce test tombe, c'est que quelqu'un a « nettoyé »
# le registre en filtrant sur le suffixe du ticker.
hors_europe = [t for t in themes.PEA_ELIGIBLES if "." not in t]
check("des titres cotés hors d'Europe figurent parmi les éligibles",
      len(hors_europe) >= 5, str(sorted(hors_europe)))
check("Nebius est éligible malgré sa cotation au Nasdaq", "NBIS" in themes.PEA_ELIGIBLES)

# Les inéligibilités qui coûtent cher si on les oublie.
for tk, motif in [("ARM", "Royaume-Uni"), ("HSBA.L", "Royaume-Uni"),
                  ("ABBN.SW", "Suisse"), ("CB", "Suisse")]:
    check(f"{tk} est explicitement écarté ({motif})", tk in themes.PEA_INELIGIBLES)

# Un éligible absent de l'univers scoré ne serait jamais publié : le thème
# afficherait un trou sans que rien ne le signale.
_univers = set(screener.UNIVERS)
absents = sorted(set(themes.PEA_ELIGIBLES) - _univers)
check("tous les éligibles sont dans l'univers scoré", not absents, str(absents))

# ── Bornage et couverture du kind « filtre » ────────────────────────────────
# Reproduit la logique de publication du screener sur des scores simulés, pour
# vérifier les deux propriétés qui se sont contredites à l'écriture : la liste
# est bornée à 20, mais la COUVERTURE se mesure avant bornage — sinon le thème
# serait « dégradé » à chaque run par sa propre définition.
def _publier(scores, top):
    membres = sorted([t for t in pea["tickers"] if t in scores],
                     key=lambda t: (-scores[t], t))
    declares, couverts = len(pea["tickers"]), len(membres)
    return membres[:top], couverts / declares


tous = {t: i for i, t in enumerate(sorted(pea["tickers"]))}
liste, couv = _publier(tous, themes.TOP_PEA)
check("la liste publiée est bornée à 20", len(liste) == 20, str(len(liste)))
check("couverture pleine quand tout est scoré", couv == 1.0, f"{couv:.0%}")
check("triée par score décroissant",
      liste == sorted(liste, key=lambda t: (-tous[t], t)))

moitie = {t: i for i, t in enumerate(sorted(pea["tickers"])[:len(pea["tickers"]) // 2])}
liste2, couv2 = _publier(moitie, themes.TOP_PEA)
check("une panne de source dégrade la couverture", couv2 < 0.70, f"{couv2:.0%}")
check("mais les 20 lignes restent remplies", len(liste2) == 20,
      "le bornage masquerait la panne sans la mesure avant troncature")


# ── Écart à la trajectoire : la formule n'est bornée que d'un côté ──────────
print("\n— Écart à la trajectoire, dans l'unité où il se lit —")
# Un titre SOUS sa tendance ne peut pas l'être de plus de 100 % ; AU-DESSUS,
# aucune limite : Advantest sortait à « surcote tendance 1244 % » (13,4 fois sa
# trajectoire) et 27 fiches sur 95 dépassaient 100 %. Ce nombre entrait tel quel
# dans le prompt de l'agent.
check("une décote normale reste en pourcentage",
      pa._ecart_tendance(28.9).strip() == "décote tendance 29%",
      pa._ecart_tendance(28.9))
check("une surcote normale aussi",
      pa._ecart_tendance(-45.0).strip() == "surcote tendance 45%",
      pa._ecart_tendance(-45.0))
check("au-delà de 100 %, on énonce le MULTIPLE, pas le pourcentage",
      pa._ecart_tendance(-1244.5).strip() == "13.4\u00d7 sa tendance",
      pa._ecart_tendance(-1244.5))
check("la bascule se fait exactement à −100 %",
      "%" in pa._ecart_tendance(-99.9) and "\u00d7" in pa._ecart_tendance(-100.1))
check("aucun écart : aucune mention", pa._ecart_tendance(None) == "")

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)


# ── Éligibilité PEA ─────────────────────────────────────────────────────────
# Le critère est JURIDIQUE, pas mesuré : ces tests protègent une donnée écrite
# à la main, là où le reste du fichier protège du code. C'est justement la
# donnée qui se périme en silence — une redomiciliation ne fait bouger aucun
# cours.
print("\n— Éligibilité PEA —")

pea = themes.THEMES_BY_ID["pea"]
check("le thème PEA est de kind « filtre »", pea["kind"] == "filtre")
check("il publie sa règle en clair", bool(pea.get("regle_texte")))
check("il borne sa liste", pea.get("top") == themes.TOP_PEA == 20)

check("aucun ticker n'est à la fois éligible et inéligible",
      not (set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES)),
      str(sorted(set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES))))
check("chaque éligible porte son pays de siège",
      all(isinstance(v, str) and "·" in v for v in themes.PEA_ELIGIBLES.values()))
check("chaque inéligible porte son motif",
      all(isinstance(v, str) and len(v) > 8 for v in themes.PEA_INELIGIBLES.values()))
check("les tickers du thème sont exactement le registre",
      set(pea["tickers"]) == set(themes.PEA_ELIGIBLES))
check("assez d'éligibles pour que « top 20 » sélectionne vraiment",
      len(themes.PEA_ELIGIBLES) >= 2 * themes.TOP_PEA,
      f"{len(themes.PEA_ELIGIBLES)} éligibles")

# Le piège que ce thème existe pour montrer : une place de cotation américaine
# n'empêche pas l'éligibilité. Si ce test tombe, c'est que quelqu'un a « nettoyé »
# le registre en filtrant sur le suffixe du ticker.
hors_europe = [t for t in themes.PEA_ELIGIBLES if "." not in t]
check("des titres cotés hors d'Europe figurent parmi les éligibles",
      len(hors_europe) >= 5, str(sorted(hors_europe)))
check("Nebius est éligible malgré sa cotation au Nasdaq", "NBIS" in themes.PEA_ELIGIBLES)

# Les inéligibilités qui coûtent cher si on les oublie.
for tk, motif in [("ARM", "Royaume-Uni"), ("HSBA.L", "Royaume-Uni"),
                  ("ABBN.SW", "Suisse"), ("CB", "Suisse")]:
    check(f"{tk} est explicitement écarté ({motif})", tk in themes.PEA_INELIGIBLES)

# Un éligible absent de l'univers scoré ne serait jamais publié : le thème
# afficherait un trou sans que rien ne le signale.
_univers = set(screener.UNIVERS)
absents = sorted(set(themes.PEA_ELIGIBLES) - _univers)
check("tous les éligibles sont dans l'univers scoré", not absents, str(absents))

# ── Bornage et couverture du kind « filtre » ────────────────────────────────
# Reproduit la logique de publication du screener sur des scores simulés, pour
# vérifier les deux propriétés qui se sont contredites à l'écriture : la liste
# est bornée à 20, mais la COUVERTURE se mesure avant bornage — sinon le thème
# serait « dégradé » à chaque run par sa propre définition.
def _publier(scores, top):
    membres = sorted([t for t in pea["tickers"] if t in scores],
                     key=lambda t: (-scores[t], t))
    declares, couverts = len(pea["tickers"]), len(membres)
    return membres[:top], couverts / declares


tous = {t: i for i, t in enumerate(sorted(pea["tickers"]))}
liste, couv = _publier(tous, themes.TOP_PEA)
check("la liste publiée est bornée à 20", len(liste) == 20, str(len(liste)))
check("couverture pleine quand tout est scoré", couv == 1.0, f"{couv:.0%}")
check("triée par score décroissant",
      liste == sorted(liste, key=lambda t: (-tous[t], t)))

moitie = {t: i for i, t in enumerate(sorted(pea["tickers"])[:len(pea["tickers"]) // 2])}
liste2, couv2 = _publier(moitie, themes.TOP_PEA)
check("une panne de source dégrade la couverture", couv2 < 0.70, f"{couv2:.0%}")
check("mais les 20 lignes restent remplies", len(liste2) == 20,
      "le bornage masquerait la panne sans la mesure avant troncature")

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
