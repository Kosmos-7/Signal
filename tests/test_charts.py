#!/usr/bin/env python3
"""Tests de non-régression de l'éclatement du payload graphique (charts/).

Aucun accès réseau : les modules lourds (ta, yfinance) sont bouchés et les
résultats du screener sont SIMULÉS — on teste le contrat de publication, pas les
données de marché. Le garde anti-oubli du workflow CI est lui aussi éprouvé, en
extrayant sa commande du YAML et en la rejouant dans un dépôt git jetable créé
hors du projet (jamais dans le dépôt Signal).

    python tests/test_charts.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

import screener                  # noqa: E402

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


# ── Simulation de résultats de screener ─────────────────────────────────────
# Forme et échelle réelles : ~560 points par série, abscisse en mois flottant à
# 2 décimales, valeurs à 2 décimales (cf. _mois / _sample_series).
def faux_chart(graine, n=560):
    def serie(decalage):
        return [[round(23800 + i * 0.25, 2), round(10 + graine + i * 0.13 + decalage, 2)]
                for i in range(n)]
    return {"points": serie(0), "mm21": serie(-0.4), "mm200": serie(-1.1),
            "t_win0": 24198.68, "t_last": 24318.97}


# Tickers représentatifs des pièges de nommage réels de l'univers.
TICKERS = ["AAPL", "ASML.AS", "000660.KS", "SAAB-B.ST", "NOVO-B.CO", "8035.T", "BRK-B"]
CHARTS = {t: faux_chart(i) for i, t in enumerate(TICKERS)}
CHARTS["ORPHELIN.PA"] = faux_chart(99)     # tagué cette semaine, sorti la suivante
CHARTS["HORS_FICHE"] = faux_chart(98)      # scoré mais dans aucun thème ni le top 30


def fichiers(d):
    return sorted(os.listdir(d))


tmpdir = tempfile.mkdtemp(prefix="signal-charts-")
DOSSIER = os.path.join(tmpdir, "charts")

print("— Éclatement par ticker —")
a_publier = set(TICKERS) | {"ORPHELIN.PA", "SANS_PAYLOAD"}
ecrits, purges, sans_graphe, refuses = screener.publier_charts(CHARTS, a_publier, DOSSIER)

check("un fichier par ticker publiable, et aucun autre",
      fichiers(DOSSIER) == sorted(f"{t}.json" for t in list(TICKERS) + ["ORPHELIN.PA"]),
      fichiers(DOSSIER))
check("le point du ticker n'est pas échappé (ASML.AS.json)",
      os.path.isfile(os.path.join(DOSSIER, "ASML.AS.json")))
check("ticker purement numérique + suffixe (000660.KS.json)",
      os.path.isfile(os.path.join(DOSSIER, "000660.KS.json")))
check("ticker à tiret (SAAB-B.ST.json)",
      os.path.isfile(os.path.join(DOSSIER, "SAAB-B.ST.json")))
check("un titre scoré hors fiche n'est pas publié",
      not os.path.exists(os.path.join(DOSSIER, "HORS_FICHE.json")))
check("aucun .tmp au sol après un run nominal",
      not any(f.endswith(".tmp") for f in fichiers(DOSSIER)), fichiers(DOSSIER))
check("le retour liste les écrits", ecrits == sorted(list(TICKERS) + ["ORPHELIN.PA"]), ecrits)
check("une fiche sans payload est journalisée, pas silencieuse",
      sans_graphe == ["SANS_PAYLOAD"], sans_graphe)
check("rien à purger au premier run", purges == [], purges)
check("aucun ticker refusé sur l'univers réel", refuses == [], refuses)

print("\n— Contenu identique au format monolithique —")
# Référence : ce que charts.json portait pour ces mêmes tickers.
mono = json.dumps({t: CHARTS[t] for t in TICKERS},
                  ensure_ascii=False, separators=(",", ":"), allow_nan=False)
ref = json.loads(mono)
relus = {t: json.load(open(os.path.join(DOSSIER, f"{t}.json"), encoding="utf-8"))
         for t in TICKERS}
check("chaque fichier porte exactement la valeur qu'avait charts.json[TICKER]",
      relus == ref)
check("les clés du payload sont inchangées",
      all(set(v) == {"points", "mm21", "mm200", "t_win0", "t_last"} for v in relus.values()))
check("aucun champ supplémentaire sérialisé (pas de nom, ticker, secteur…)",
      all(len(v) == 5 for v in relus.values()))
brut = open(os.path.join(DOSSIER, "AAPL.json"), encoding="utf-8").read()
check("séparateurs compacts (ni indent ni espace après , ou :)",
      ", " not in brut and ": " not in brut and "\n" not in brut)
check("le fichier unitaire est bien plus léger que le monolithe",
      len(brut) < len(mono) / 5, f"{len(brut)} vs {len(mono)}")
check("les valeurs restent à 2 décimales max (rien de dé-arrondi à l'écriture)",
      max(len(m.group(1)) for m in re.finditer(r"\d+\.(\d+)", brut)) <= 2)

print("\n— Breakdown embarqué (parité de données des fiches thématiques) —")
# Le breakdown complet voyage avec le graphe pour que les fiches hors top 30
# affichent les mêmes données que les fiches du top 30. Le dict du chart est
# copié, jamais muté : il est partagé avec le monolithe charts.json.
FAUX_BD = {"AAPL": {"qualite": 40, "rev_growth_pct": 12.3, "fibo": None},
           "ASML.AS": {"qualite": 38, "net_margin_pct": 28.1}}
d2 = os.path.join(tmpdir, "charts-bd")
screener.publier_charts(CHARTS, set(TICKERS), d2, breakdowns=FAUX_BD)
aapl_bd = json.load(open(os.path.join(d2, "AAPL.json"), encoding="utf-8"))
check("le fichier porte le breakdown fourni sous la clé dédiée",
      aapl_bd.get("breakdown") == FAUX_BD["AAPL"])
check("le payload graphique reste intact à côté du breakdown",
      {k: aapl_bd[k] for k in ("points", "mm21", "mm200", "t_win0", "t_last")} == CHARTS["AAPL"])
check("un ticker sans breakdown fourni est publié sans la clé (dégradation douce)",
      "breakdown" not in json.load(open(os.path.join(d2, "8035.T.json"), encoding="utf-8")))
check("le dict du chart n'est PAS muté (le monolithe partagé reste sans breakdown)",
      "breakdown" not in CHARTS["AAPL"])
check("breakdowns=None conserve exactement l'ancien format",
      json.load(open(os.path.join(DOSSIER, "AAPL.json"), encoding="utf-8")) == CHARTS["AAPL"])
shutil.rmtree(d2)

print("\n— Purge des orphelins —")
# Semaine suivante : ORPHELIN.PA a quitté tous ses thèmes et sort du top 30.
avant = len(fichiers(DOSSIER))
ecrits2, purges2, _, _ = screener.publier_charts(CHARTS, set(TICKERS), DOSSIER)
check("le fichier du titre sorti est supprimé",
      not os.path.exists(os.path.join(DOSSIER, "ORPHELIN.PA.json")))
check("la purge est retournée (donc journalisable)", purges2 == ["ORPHELIN.PA"], purges2)
check("le dossier ne grossit pas d'un run à l'autre",
      len(fichiers(DOSSIER)) == avant - 1 == len(TICKERS))
check("les titres restants sont intacts",
      json.load(open(os.path.join(DOSSIER, "AAPL.json"), encoding="utf-8")) == CHARTS["AAPL"])

# Un résidu déposé à la main est traité comme un orphelin : le dossier est une
# sortie entièrement dérivée du run, rien n'y survit sans raison.
open(os.path.join(DOSSIER, "ZOMBIE.json"), "w").write("{}")
_, purges3, _, _ = screener.publier_charts(CHARTS, set(TICKERS), DOSSIER)
check("un fichier inconnu déposé dans charts/ est purgé", purges3 == ["ZOMBIE"], purges3)

print("\n— Écriture atomique et fail-loud —")
avant_aapl = open(os.path.join(DOSSIER, "AAPL.json"), encoding="utf-8").read()
pourri = dict(CHARTS)
pourri["AAPL"] = {**CHARTS["AAPL"], "t_last": float("nan")}
try:
    screener.publier_charts(pourri, set(TICKERS), DOSSIER)
    leve = False
except ValueError:
    leve = True
check("un NaN fait échouer le run (allow_nan=False), il n'est jamais publié", leve)
check("le fichier précédent est intact — jamais tronqué par un échec",
      open(os.path.join(DOSSIER, "AAPL.json"), encoding="utf-8").read() == avant_aapl)
check("aucun .tmp abandonné après un échec d'écriture",
      not any(f.endswith(".tmp") for f in fichiers(DOSSIER)), fichiers(DOSSIER))

print("\n— Noms de fichiers refusés —")
piege = {"../../evil": faux_chart(1, 3), "a/b": faux_chart(2, 3),
         ".hidden": faux_chart(3, 3), "minuscule": faux_chart(4, 3),
         "AAPL": CHARTS["AAPL"]}
_, _, _, refuses2 = screener.publier_charts(piege, set(piege), DOSSIER)
check("tout ticker hors [A-Z0-9.-] est refusé, pas écrit",
      refuses2 == sorted(["../../evil", "a/b", ".hidden", "minuscule"]), refuses2)
check("aucune écriture hors du dossier charts/",
      not os.path.exists(os.path.join(tmpdir, "evil")) and fichiers(DOSSIER) == ["AAPL.json"],
      fichiers(DOSSIER))
check("un refus est retourné, donc journalisé (jamais silencieux)", len(refuses2) == 4)

# ── Garde anti-oubli du workflow CI ─────────────────────────────────────────
# La commande n'est PAS recopiée ici : on l'extrait du YAML, sinon le test
# validerait une garde qui aurait pu diverger de celle réellement exécutée.
print("\n— Garde anti-oubli du CI (dépôt git jetable) —")
YML = open(os.path.join(RACINE, ".github/workflows/watchlist.yml"), encoding="utf-8").read()
bloc = re.search(r"^( +)OUBLIES=\$\(.*?^\1fi$", YML, re.S | re.M)
GARDE = None
if bloc:
    indent = len(bloc.group(1))
    GARDE = "\n".join(l[indent:] if l.startswith(" " * indent) else l
                      for l in bloc.group(0).split("\n"))
check("la garde est bien extraite du workflow", GARDE is not None)
GIT_ADD = re.search(r"^ +git add (.+)$", YML, re.M)
check("charts/ est présent dans le git add du workflow",
      GIT_ADD and "charts/" in GIT_ADD.group(1).split(), GIT_ADD and GIT_ADD.group(1))


def git(repo, *args):
    return subprocess.run(("git",) + args, cwd=repo, capture_output=True, text=True)


def garde_passe(repo):
    """Rejoue la garde du CI. Retourne True si le run passerait."""
    r = subprocess.run(["bash", "-c", GARDE], cwd=repo, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


if GARDE and GIT_ADD:
    repo = os.path.join(tmpdir, "depot")
    os.makedirs(repo)
    git(repo, "init", "-q", ".")
    git(repo, "config", "user.email", "t@t.t")
    git(repo, "config", "user.name", "t")
    # Squelette dérivé de la ligne `git add` du workflow : un pathspec manquant
    # ferait échouer git add EN BLOC (rien de mis en scène), ce qui déguiserait
    # un faux positif de la garde en vrai positif.
    cibles = GIT_ADD.group(1).split()
    for cible in cibles:
        if cible.endswith("/"):
            os.makedirs(os.path.join(repo, cible), exist_ok=True)
            if cible != "charts/":
                open(os.path.join(repo, cible, "x.json"), "w").write("{}")
        else:
            open(os.path.join(repo, cible), "w").write("{}")
    ADD = ["add"] + cibles

    # 1er run : 190 fichiers charts/ créés, rien encore mis en scène. Contenus
    # tous distincts, sinon la détection de renommage de git transforme une
    # suppression + une création en un R100 et masque ce qu'on veut observer.
    for i in range(190):
        open(os.path.join(repo, "charts", f"T{i}.json"), "w").write('{"points":[[1,%d]]}' % i)
    passe, msg = garde_passe(repo)
    check("un charts/ non mis en scène FAIT ÉCHOUER le run", not passe)
    check("le message nomme un fichier de charts/", "charts/T" in msg, msg[:160])

    git(repo, *ADD)
    passe, msg = garde_passe(repo)
    check("aucun faux positif une fois les 190 fichiers stagés", passe, msg[:200])
    git(repo, "commit", "-qm", "run 1")

    # 2e run : un titre modifié, un titre purgé, un titre nouveau.
    open(os.path.join(repo, "charts", "T0.json"), "w").write('{"points":[[9,9]]}')
    os.remove(os.path.join(repo, "charts", "T1.json"))
    open(os.path.join(repo, "charts", "T190.json"), "w").write('{"points":[[7,7]]}')
    passe, msg = garde_passe(repo)
    check("modif + purge + création non stagées : échec", not passe)
    git(repo, *ADD)
    passe, msg = garde_passe(repo)
    check("git add <dossier> met la SUPPRESSION en scène → garde verte", passe, msg[:200])
    etat = git(repo, "diff", "--staged", "--name-status").stdout
    check("la purge part bien dans le commit (D charts/T1.json)",
          "D\tcharts/T1.json" in etat, etat[:200])
    git(repo, "commit", "-qm", "run 2")

    # Non-régression : le cas d'origine (JSON de la racine oublié) échoue toujours.
    open(os.path.join(repo, "portfolio.json"), "w").write('{"maj":1}')
    passe, msg = garde_passe(repo)
    check("un JSON racine oublié échoue toujours (non-régression)",
          not passe and "portfolio.json" in msg, msg[:160])

shutil.rmtree(tmpdir, ignore_errors=True)

# ── Chiffres publiés : extraire_fondamentaux (pur, duck-typing, sans pandas) ─
print("\n— Chiffres publiés (extraire_fondamentaux) —")


class FDF:
    """Faux DataFrame yfinance : lignes {libellé: {date_iso: valeur}}."""
    class _S:
        ndim = 1
        def __init__(self, d): self.d = d
        def dropna(self): return self
        def items(self):
            return [(k, v) for k, v in self.d.items() if v is not None and v == v]

    def __init__(self, rows):
        self.rows, self.empty, self.index = rows, not rows, list(rows)
        parent = self
        self.loc = type("L", (), {"__getitem__":
                                  lambda _s, k: FDF._S(parent.rows[k])})()


AN = FDF({
    "Total Revenue": {"2023-12-31": 22_000_000_000, "2024-12-31": 21_500_000_000,
                      "2025-12-31": 20_900_000_000},
    "EBITDA":        {"2023-12-31": 2_650_000_000, "2024-12-31": 2_860_000_000,
                      "2025-12-31": 3_080_000_000},
    "Net Income":    {"2023-12-31": 221_000_000, "2024-12-31": 162_000_000,
                      "2025-12-31": 200_000_000},
})
f = screener.extraire_fondamentaux(AN, None, "EUR")
check("bloc annuel : devise + lignes chronologiques",
      f and f["devise"] == "EUR" and [e["fin"] for e in f["an"]]
      == ["2023-12-31", "2024-12-31", "2025-12-31"])
check("montants convertis en millions entiers",
      f["an"][-1] == {"fin": "2025-12-31", "ca": 20900, "eb": 3080, "rn": 200})
check("pas de trimestres → liste vide, pas d'erreur", f["tr"] == [])

BANQUE = FDF({"Total Revenue": {"2025-12-31": 44_400_000_000},
              "Net Income":    {"2025-12-31": 1_640_000_000}})
f = screener.extraire_fondamentaux(BANQUE, None, "EUR")
check("banque sans EBITDA : la ligne manque, l'entrée reste",
      f["an"] == [{"fin": "2025-12-31", "ca": 44400, "rn": 1640}])

f = screener.extraire_fondamentaux(FDF({}), FDF({}), "USD")
check("aucune donnée → None (le front n'affiche rien)", f is None)

TROUS = FDF({"Total Revenue": {"2024-12-31": 1_000_000_000, "2025-12-31": None},
             "Net Income":    {"2025-12-31": -50_000_000}})
f = screener.extraire_fondamentaux(TROUS, None, "USD")
check("trous et pertes : CA absent toléré, RN négatif conservé",
      f["an"] == [{"fin": "2024-12-31", "ca": 1000},
                  {"fin": "2025-12-31", "rn": -50}])

VIEUX = FDF({"Total Revenue": {f"20{i:02d}-12-31": i * 1e9 for i in range(10, 26)},
             "Net Income":    {f"20{i:02d}-12-31": i * 1e8 for i in range(10, 26)}})
f = screener.extraire_fondamentaux(VIEUX, None, "USD")
check("borné aux 5 exercices les plus récents",
      len(f["an"]) == 5 and f["an"][0]["fin"] == "2021-12-31")

print("\n— Contre-vérification des fondamentaux (valider_fondamentaux) —")
c, a = screener.valider_fondamentaux({"profitMargins": 0.25}, {"net_margin": 25.3})
check("sources concordantes : confiance pleine, aucune alerte", c == 1.0 and a == [])
c, a = screener.valider_fondamentaux({"profitMargins": 0.05}, {"net_margin": 40.0})
check("discordance réelle : décote + alerte « discordante »",
      c == 0.9 and "discordante" in a[0])
c, a = screener.valider_fondamentaux({}, {"net_margin": 20.0})
check("trou Yahoo : décote mais alerte « absente », jamais « YF:0.0% »",
      c == 0.9 and "absente" in a[0] and "YF:" not in a[0])
c, a = screener.valider_fondamentaux({"profitMargins": 0.25}, {})
check("Finnhub muet : confiance pleine (validateur absent ≠ défaut)",
      c == 1.0 and a == [])
c, a = screener.valider_fondamentaux({"profitMargins": 0.2, "revenueGrowth": 4.2},
                                     {"net_margin": 20.0})
check("croissance > 300 % : suspecte, décote 0.15", abs(c - 0.85) < 1e-9 and a)

print("\n— PER par exercice et exercices à venir —")
EPSDF = FDF({
    "Total Revenue": {"2024-12-31": 2_000_000_000, "2025-12-31": 2_200_000_000},
    "Net Income":    {"2024-12-31": 300_000_000, "2025-12-31": 360_000_000},
    "Diluted EPS":   {"2024-12-31": 3.0, "2025-12-31": 3.6},
})
f = screener.extraire_fondamentaux(EPSDF, None, "EUR")
check("le BPA dilué annuel est extrait (jamais en trimestre)",
      f["an"][0]["eps"] == 3.0 and f["an"][1]["eps"] == 3.6)

prix = {"2024-12-31": 90.0, "2025-12-31": 108.0}
an = [dict(e) for e in f["an"]]
screener.per_historique(an, lambda d: prix.get(d), meme_devise=True)
check("PER par exercice = cours de clôture / BPA publié",
      an[0]["per"] == 30.0 and an[1]["per"] == 30.0)
an2 = [dict(e) for e in f["an"]]
screener.per_historique(an2, lambda d: prix.get(d), meme_devise=False)
check("ADR (devise comptable ≠ cotation) : aucun PER historique",
      all("per" not in e for e in an2))
an3 = [{"fin": "2025-12-31", "eps": -2.0}, {"fin": "2024-12-31"}]
screener.per_historique(an3, lambda d: 100.0, meme_devise=True)
check("perte ou BPA absent : pas de multiple", all("per" not in e for e in an3))

prev = screener.per_previsionnel(120.0, {"0y": 4.0, "+1y": 5.0}, "2025-12-31")
check("deux exercices à venir, étiquetés après le dernier clos",
      prev == [{"exercice": 2026, "per": 30.0}, {"exercice": 2027, "per": 24.0}])
check("estimation manquante ou négative sautée",
      screener.per_previsionnel(120.0, {"0y": None, "+1y": -1}, "2025-12-31") == []
      and screener.per_previsionnel(120.0, None, "2025-12-31") == [])

print("\n— Fusion de l'historique entre runs (fusionner_fonda) —")
ANCIEN = {"devise": "USD",
          "an": [{"fin": "2022-12-31", "ca": 100, "rn": 10}],
          "tr": [{"fin": "2024-06-30", "ca": 25, "rn": 2},
                 {"fin": "2024-09-30", "ca": 26, "rn": 3}]}
NOUVEAU = {"devise": "USD",
           "an": [{"fin": "2022-12-31", "ca": 101, "rn": 11},   # révisé
                  {"fin": "2023-12-31", "ca": 110, "rn": 12}],
           "tr": [{"fin": "2024-09-30", "ca": 26, "rn": 3},
                  {"fin": "2025-09-30", "ca": 30, "rn": 4}]}
f = screener.fusionner_fonda(ANCIEN, NOUVEAU)
check("union par date : le trimestre sorti de la fenêtre Yahoo survit",
      [e["fin"] for e in f["tr"]] == ["2024-06-30", "2024-09-30", "2025-09-30"])
check("à date égale le run récent fait foi (chiffres révisés)",
      f["an"][0] == {"fin": "2022-12-31", "ca": 101, "rn": 11})
check("premier run (pas d'ancien) : le nouveau passe tel quel",
      screener.fusionner_fonda(None, NOUVEAU) is NOUVEAU)
check("extraction en échec : l'ancien historique n'est PAS perdu",
      screener.fusionner_fonda(ANCIEN, None) is ANCIEN)
GROS = {"devise": "USD", "an": [],
        "tr": [{"fin": f"20{15+i//4}-{(3*(i%4)+3):02d}-30", "ca": i} for i in range(28)]}
f = screener.fusionner_fonda(GROS, {"devise": "USD", "an": [], "tr": []})
check("garde-fou de croissance : 20 trimestres conservés au plus, les plus récents",
      len(f["tr"]) == 20 and f["tr"][-1]["ca"] == 27)
f = screener.fusionner_fonda({"devise": "USD", "an": [], "tr": [],
                              "pe_prev": [{"exercice": 2026, "per": 30.0}]},
                             {"devise": "USD", "an": [], "tr": []})
check("estimations PER : le run muet n'efface pas les précédentes",
      f["pe_prev"] == [{"exercice": 2026, "per": 30.0}])
# Le cas ON : l'ancien run datait le trimestre au 31/03 (EDGAR), le nouveau au
# 04/04 (Yahoo, calendrier fiscal 52/53 semaines) — même trimestre, deux dates.
f = screener.fusionner_fonda(
    {"devise": "USD", "an": [], "tr": [{"fin": "2025-03-31", "ca": 1400, "src": "edgar"}]},
    {"devise": "USD", "an": [], "tr": [{"fin": "2025-04-04", "ca": 1402}]})
check("dates voisines entre runs : une seule entrée, le run courant fait foi",
      f["tr"] == [{"fin": "2025-04-04", "ca": 1402}])
f = screener.fusionner_fonda(
    {"devise": "USD", "an": [], "tr": [{"fin": "2025-03-28", "ca": 1}, {"fin": "2025-04-02", "ca": 2}]},
    {"devise": "USD", "an": [], "tr": []})
check("deux anciennes voisines : la plus récente survit",
      f["tr"] == [{"fin": "2025-04-02", "ca": 2}])
# Un exercice fantôme déjà publié ne survit pas à la fusion : le filtre de
# clôture majoritaire est rejoué sur l'union (cas AMZN, CY2026 fin juin).
f = screener.fusionner_fonda(
    {"devise": "USD", "an": [{"fin": f"{y}-12-31", "ca": 100 + y} for y in (2023, 2024, 2025)]
     + [{"fin": "2026-06-30", "rn": 135281, "src": "edgar"}], "tr": []},
    {"devise": "USD", "an": [{"fin": "2025-12-31", "ca": 2125}], "tr": []})
check("exercice fantôme publié : purgé par la fusion, plus de zombie",
      all(e["fin"] != "2026-06-30" for e in f["an"]) and len(f["an"]) == 3)

print("\n— EDGAR : parsing des dépôts SEC (pur, hors ligne) —")
import edgar                                                     # noqa: E402

DOC_CA = {"units": {"USD": [
    {"frame": "CY2023", "end": "2023-12-31", "val": 22_000_000_000},
    {"frame": "CY2024", "end": "2024-12-31", "val": 24_000_000_000},
    {"frame": "CY2024Q1", "end": "2024-03-31", "val": 5_000_000_000},
    {"frame": "CY2024Q2", "end": "2024-06-30", "val": 6_000_000_000},
    {"frame": "CY2024Q3", "end": "2024-09-30", "val": 6_500_000_000},
    {"end": "2024-12-31", "val": 99},                # sans frame : redondant, ignoré
    {"frame": "CY2022", "end": "2022-12-31", "val": None},        # val nulle : ignorée
]}}
DOC_RN = {"units": {"USD": [
    {"frame": "CY2024", "end": "2024-12-31", "val": 3_000_000_000},
    {"frame": "CY2024Q1", "end": "2024-03-31", "val": 700_000_000},
    {"frame": "CY2024Q2", "end": "2024-06-30", "val": 750_000_000},
    {"frame": "CY2024Q3", "end": "2024-09-30", "val": 800_000_000},
]}}
DOC_EPS = {"units": {"USD/shares": [
    {"frame": "CY2024", "end": "2024-12-31", "val": 3.25},
], "USD": [{"frame": "CY2024", "end": "2024-12-31", "val": 999}]}}

sca = edgar.series_frames(DOC_CA, "USD")
check("seuls les faits porteurs de frame et de valeur sont lus",
      set(sca) == {"CY2023", "CY2024", "CY2024Q1", "CY2024Q2", "CY2024Q3"})
check("le filtre d'unité tient (USD/shares ≠ USD)",
      edgar.series_frames(DOC_EPS, "USD/shares") == {"CY2024": ("2024-12-31", 3.25)})

ed = edgar.construire_fonda(sca, edgar.series_frames(DOC_RN, "USD"),
                            edgar.series_frames(DOC_EPS, "USD/shares"))
check("annuels en millions, BPA conservé, provenance tracée",
      ed["an"][-1] == {"fin": "2024-12-31", "src": "edgar",
                       "ca": 24000, "rn": 3000, "eps": 3.25})
q4 = [e for e in ed["tr"] if e["fin"] == "2024-12-31"]
check("Q4 dérivé = exercice − (Q1+Q2+Q3), CA et RN, jamais l'EPS",
      q4 and q4[0].get("ca") == 24000 - 17500 and q4[0].get("rn") == 3000 - 2250
      and "eps" not in q4[0])
check("2023 sans trimestres : pas de Q4 inventé",
      not any(e["fin"] == "2023-12-31" for e in ed["tr"]))

FY = {"an": [{"fin": "2024-12-31", "ca": 24100, "rn": 3010},
             {"fin": "2025-12-31", "ca": 26000, "rn": 3300}], "tr": []}
edgar.completer_fonda(FY, ed)
check("extend-only : la date déjà connue de Yahoo n'est pas écrasée",
      [e for e in FY["an"] if e["fin"] == "2024-12-31"][0]["ca"] == 24100)
check("les dates absentes arrivent, triées, avec leur provenance",
      FY["an"][0] == {"fin": "2023-12-31", "src": "edgar", "ca": 22000}
      and [e["fin"][:4] for e in FY["an"]] == ["2023", "2024", "2025"])
check("les trimestres EDGAR remplissent la fenêtre",
      len(FY["tr"]) == 4 and FY["tr"][-1]["fin"] == "2024-12-31")

ECHELLE = {"an": [{"fin": "2023-12-31", "src": "edgar", "ca": 22_000_000}], "tr": []}
FY2 = {"an": [{"fin": "2024-12-31", "ca": 24000}], "tr": []}
edgar.completer_fonda(FY2, ECHELLE)
check("erreur d'échelle sur exercices adjacents : tout l'apport est refusé",
      len(FY2["an"]) == 1)
LOIN = {"an": [{"fin": "2014-12-31", "src": "edgar", "ca": 2000}], "tr": []}
FY3 = {"an": [{"fin": "2024-12-31", "ca": 24000}], "tr": []}
edgar.completer_fonda(FY3, LOIN)
check("hypercroissance : un exercice lointain ×12 n'est PAS confondu avec une erreur",
      len(FY3["an"]) == 2)
check("les alias d'une balise fusionnent, priorité au premier sur conflit",
      edgar.fusion_series([{"CY2020": ("2020-12-31", 100)},
                           {"CY2015": ("2015-12-31", 40), "CY2020": ("2020-12-31", 999)}])
      == {"CY2020": ("2020-12-31", 100), "CY2015": ("2015-12-31", 40)})

# NVDA : BPA « tels que déposés » (base d'origine) — splits 4:1 (2021) et
# 10:1 (2024), ~24,4 Md d'actions aujourd'hui.
NVDAISH = {"an": [{"fin": "2015-01-25", "src": "edgar", "rn": 631, "eps": 1.14},
                  {"fin": "2022-01-30", "src": "edgar", "rn": 9752, "eps": 3.91},
                  {"fin": "2025-01-26", "src": "edgar", "rn": 72880, "eps": 2.94}],
           "tr": []}
SPL = [("2021-07-20", 4.0), ("2024-06-10", 10.0)]
edgar.ajuster_eps_splits(NVDAISH, SPL, actions_actuelles=24.4e9)
check("BPA déposé en base d'origine : détecté, ramené en base actuelle (÷40)",
      NVDAISH["an"][0]["eps"] == round(1.14 / 40, 4))
check("BPA en base intermédiaire (post-4:1, pré-10:1) : détecté (÷10)",
      NVDAISH["an"][1]["eps"] == round(3.91 / 10, 4))
check("BPA postérieur au dernier split : intact",
      NVDAISH["an"][2]["eps"] == 2.94)
# GOOGL : le 10-K post-split republie ses comparatifs DÉJÀ retraités — le
# frame 2020 porte 2.93 (base actuelle), diviser encore donnerait 592× de PER.
GOOGLISH = {"an": [{"fin": "2020-12-31", "src": "edgar", "rn": 40269, "eps": 2.93}],
            "tr": []}
edgar.ajuster_eps_splits(GOOGLISH, [("2022-07-18", 20.0)], actions_actuelles=12.3e9)
check("BPA comparatif DÉJÀ retraité : détecté, laissé intact (bug GOOGL 592×)",
      GOOGLISH["an"][0]["eps"] == 2.93)
# Donnée incohérente quelle que soit la base : rn ET eps retirés (on ne
# devine pas lequel ment) — même SANS split (SCHW 2021, rn déposé à 6 M$).
FAUX = {"an": [{"fin": "2021-12-31", "src": "edgar", "ca": 18520, "rn": 6, "eps": 2.83}],
        "tr": []}
edgar.ajuster_eps_splits(FAUX, [], actions_actuelles=1.8e9)
check("paire rn/eps incompatible avec le nombre d'actions : les deux retirés",
      "eps" not in FAUX["an"][0] and "rn" not in FAUX["an"][0]
      and FAUX["an"][0]["ca"] == 18520)
# Sans rn ni nombre d'actions, base indéterminable + split postérieur → retiré.
INDET = {"an": [{"fin": "2020-12-31", "src": "edgar", "eps": 5.0}], "tr": []}
edgar.ajuster_eps_splits(INDET, [("2022-01-01", 2.0)], actions_actuelles=None)
check("base indéterminable avec split postérieur : BPA retiré par prudence",
      "eps" not in INDET["an"][0])
check("sans splits : aucun changement",
      edgar.ajuster_eps_splits({"an": [{"fin": "2020-12-31", "eps": 5.0}]}, [],
                               actions_actuelles=1e9)["an"][0]["eps"] == 5.0)

# B2/B3 : garde-fous de construire_fonda (RN aberrant, exercice fantôme).
CA9 = {f"CY{y}": (f"{y}-12-31", (1000 + 10 * (y - 2018)) * 1e6) for y in range(2018, 2026)}
RN9 = {f"CY{y}": (f"{y}-12-31", 5000e6) for y in range(2018, 2026)}
RN9["CY2021"] = ("2021-12-31", 6e6)                    # SCHW : mauvaise balise
CA9["CY2026"] = ("2026-06-30", 999e6)                  # AMZN : frame fantôme mi-année
f = edgar.construire_fonda(CA9, RN9, {})
check("exercice fantôme hors du mois de clôture majoritaire : écarté",
      all(e["fin"] != "2026-06-30" for e in f["an"]))
sch = [e for e in f["an"] if e["fin"] == "2021-12-31"][0]
check("RN 100× sous ses deux voisins : retiré (le CA de l'entrée survit)",
      "rn" not in sch and sch.get("ca") == 1030)

check("dates voisines (30 vs 31 déc.) : doublon évité",
      len(edgar.completer_fonda(
          {"an": [{"fin": "2024-12-30", "ca": 24100}], "tr": []},
          {"an": [{"fin": "2024-12-31", "src": "edgar", "ca": 24000}], "tr": []}
      )["an"]) == 1)

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
