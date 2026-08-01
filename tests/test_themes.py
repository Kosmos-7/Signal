#!/usr/bin/env python3
"""Tests de non-régression des watchlists thématiques.

Aucun accès réseau : les modules lourds (ta, yfinance, requests) sont bouchés,
et les données sont simulées. On teste le contrat, pas les données de marché.

    python tests/test_themes.py
"""
import json
import os
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
check("11 curés + 2 calculés", len(themes.THEMES_CURES) == 11 and len(themes.THEMES_CALCULES) == 2)
check("chaque thème a thèse, inversion et biais",
      all(t.get("thesis") and t.get("inversion") and t.get("biais") for t in themes.THEMES))
check("les thèmes calculés publient leur règle en clair",
      all(t.get("regle_texte") for t in themes.THEMES_CALCULES))
check("aucun thème curé vide", all(len(t["tickers"]) >= 10 for t in themes.THEMES_CURES))

# Doctrine de nommage : ne jamais emprunter le vocabulaire d'un concept non calculé
interdits = ["moat", "douve", "marge de sécurité", "valeur intrinsèque"]
textes = " ".join(f"{t['label']} {t['sous_titre']} {t['thesis']}" for t in themes.THEMES).lower()
fautes = [m for m in interdits if m in textes]
check("aucun vocabulaire emprunté dans les libellés et thèses", not fautes, f"trouvé : {fautes}")

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

print("\n— Règles calculées —")
check("décote : retenue sous −1σ avec qualité intacte",
      themes._regle_decote({"regression_z": -2.0, "qualite": 30}))
check("décote : écartée si la qualité s'effondre (pas de couteau qui tombe)",
      not themes._regle_decote({"regression_z": -3.0, "qualite": 12}))
check("décote : écartée au-dessus du seuil",
      not themes._regle_decote({"regression_z": -0.5, "qualite": 40}))
check("décote : z absent ne plante pas", not themes._regle_decote({"qualite": 40}))
check("qualité : retenue au-dessus du seuil", themes._regle_qualite({"qualite": 35}))
check("qualité : écartée sous le seuil", not themes._regle_qualite({"qualite": 20}))
check("breakdown vide ne plante pas", themes.themes_calcules_pour({}) == [] and
      themes.themes_calcules_pour(None) == [])

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

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
