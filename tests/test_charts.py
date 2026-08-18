#!/usr/bin/env python3
"""Tests de non-régression de l'éclatement du payload graphique (charts/).

Aucun accès réseau : les modules lourds (ta, yfinance) sont bouchés et les
résultats du screener sont SIMULÉS — on teste le contrat de publication, pas les
données de marché. Le garde anti-oubli du workflow CI est lui aussi éprouvé, en
extrayant sa commande du YAML et en la rejouant dans un dépôt git jetable créé
hors du projet (jamais dans le dépôt Signal).

    python tests/test_charts.py
"""
import copy
import glob
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
# La liste est UNIQUE (tests/_bouchons.py) : recopiée, elle divergeait — c'est
# ainsi que `numpy` a manqué aux deux suites sans que rien ne le signale.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bouchons              # noqa: E402
_bouchons.poser()

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


# ── Garde : la liste des bouchons couvre-t-elle requirements.txt ? ──────────
# Deux exécutions de CI ont été nécessaires pour découvrir `numpy` puis
# `anthropic` : la liste était devinée de mémoire, et la machine de
# développement comblait les trous. La source de vérité est le fichier de
# dépendances, plus le souvenir de qui écrit le test.
_oublies = _bouchons.manquants(os.path.join(RACINE, "requirements.txt"))
check("chaque dépendance déclarée a son bouchon", not _oublies, str(_oublies))


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
print("\n— Un outil qui importe le cœur du projet met la racine sur son chemin —")
# UN RUN DE CI PERDU POUR UNE LIGNE. tools/sonde_titre.py a été écrit pour scorer
# un titre hors univers ; lancé par `python tools/sonde_titre.py`, l'interpréteur
# met `tools/` en tête du chemin et PAS la racine. Le job a installé toutes les
# dépendances, appelé Yahoo, puis rendu « ModuleNotFoundError: No module named
# 'screener' ». Les autres outils de tools/ n'ajoutaient que leur propre dossier,
# parce qu'aucun n'importait le cœur du projet : le motif n'existait nulle part à
# recopier, et rien ne signalait son absence.
# Le contrôle est STATIQUE et se dérive du dossier : il ne connaît pas la liste
# des outils, il la lit.
_CŒUR = ("screener", "themes", "config", "portfolio_agent", "edgar", "note_v4",
         "validate_tickers", "update_prices")
_sans_racine = []
for _p in sorted(glob.glob(os.path.join(RACINE, "tools", "*.py"))):
    _src = open(_p, encoding="utf-8").read()
    if not re.search(r"^\s*(?:import|from)\s+(?:%s)\b" % "|".join(_CŒUR), _src, re.M):
        continue                                  # n'importe pas le cœur : rien à exiger
    # la racine, c'est le PARENT du dossier du fichier — deux `dirname` imbriqués
    if not re.search(r"sys\.path\.insert\([^)]*dirname\([^)]*dirname\(", _src):
        _sans_racine.append(os.path.basename(_p))
check("chaque outil important le cœur ajoute la racine à sys.path",
      not _sans_racine, f"{_sans_racine} : ModuleNotFoundError au runtime")

print("\n— Aucune entrée de dispatch ne tombe dans un shell —")
# POURQUOI CETTE GARDE EXISTE. photos-marques.yml porte la leçon, écrite après
# coup : « les "|" de "TICKER=a|b" avaient été pris pour des tubes et bash avait
# tenté d'exécuter les termes comme des commandes. Au-delà du bug, c'est une
# injection : n'importe quelle valeur d'entrée s'exécutait. » La parade — passer
# l'entrée par l'environnement et la citer — y était appliquée à `termes`… et
# oubliée DEUX LIGNES PLUS BAS pour `limite` et `par_societe`, qui sont
# `type: string` exactement comme elle. Treize sites dans huit workflows étaient
# dans ce cas le 10/08/2026. Un motif appliqué à moitié ne protège pas à moitié,
# et un commentaire ne s'exécute pas.
#
# CE QUI EST TOLÉRÉ, ET POURQUOI. Une expression du type
# `${{ inputs.x && '--drapeau' || '' }}` ne rend jamais l'entrée : elle rend l'un
# de deux littéraux écrits dans le fichier. Une entrée `type: boolean` est rendue
# `true` ou `false` par GitHub, jamais du texte libre. Ces deux formes restent
# donc interpolées, et le test le dit plutôt que de les interdire au hasard.
#
# LECTURE PAR EXPRESSIONS RÉGULIÈRES, PAS PAR PARSEUR YAML : le workflow de tests
# n'installe RIEN, et `pyyaml` n'est pas garanti sur le runner. Importer un
# parseur ferait mourir la suite à l'import, exactement comme `PIL` l'a fait.
_WF = os.path.join(RACINE, ".github", "workflows")
_fichiers = sorted(glob.glob(os.path.join(_WF, "*.yml")))
check("des workflows à inspecter", len(_fichiers) >= 10, f"{len(_fichiers)} trouvés")
_nus = []
for _p in _fichiers:
    _src = open(_p, encoding="utf-8").read()
    _types = dict(re.findall(r"^\s{6}(\w+):\s*\n(?:.*\n)*?\s{8}type:\s*(\w+)", _src, re.M))
    _dans, _ind = False, 0
    for _i, _l in enumerate(_src.splitlines(), 1):
        if re.match(r"\s*run:", _l):
            _dans, _ind = True, len(_l) - len(_l.lstrip())
        elif _dans and _l.strip() and (len(_l) - len(_l.lstrip())) <= _ind:
            _dans = False
        if not _dans:
            continue
        for _nom in re.findall(r"\$\{\{\s*(?:inputs|github\.event)\.([\w.]+)", _l):
            if re.search(r"\.%s\s*[=!]=|\.%s\s*&&\s*'" % (re.escape(_nom), re.escape(_nom)), _l):
                continue                      # rend un littéral écrit dans le fichier
            if _types.get(_nom) == "boolean":
                continue                      # GitHub rend true/false, jamais du texte
            _nus.append(f"{os.path.basename(_p)}:L{_i} {_nom}")
check("aucune entrée libre n'est interpolée dans un run:",
      not _nus, f"{len(_nus)} site(s) — " + ", ".join(_nus[:6]))

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
# BASE D'ACTIONS : on la VÉRIFIE, on ne la suppose pas.
# Le premier jet supposait que les BPA Yahoo étaient « tels que publiés » et
# retirait tout exercice antérieur à un split. Faux : le nombre d'actions
# impliqué (résultat net ÷ BPA) est CONTINU au passage d'EDGAR à Yahoo — Booking
# 1 034 M puis 1 001 M, NVIDIA 25 330 M puis 25 103 M. La garde supprimait des
# multiples bons, et c'est ce que le propriétaire a vu sur Booking.
ACT = 1_000_000_000          # nombre d'actions actuel
an4 = [{"fin": "2023-12-31", "eps": 2.0, "rn": 2000},      # 1 000 M implicites
       {"fin": "2024-12-31", "eps": 60.0, "rn": 2000}]     # 33 M : autre base
screener.per_historique(an4, lambda d: 120.0, True, ACT)
check("base d'actions cohérente : le multiple est calculé", an4[0]["per"] == 60.0)
check("base d'actions incompatible (facteur 30) : le multiple est retiré",
      "per" not in an4[1], str(an4[1]))
an5 = [{"fin": "2023-12-31", "eps": 2.0, "rn": 2400}]      # 1 200 M : ×1,2, toléré
screener.per_historique(an5, lambda d: 120.0, True, ACT)
check("un simple rachat d'actions ne fait pas retirer le multiple",
      an5[0]["per"] == 60.0, str(an5))
an6 = [{"fin": "2023-12-31", "eps": 20.0}]                 # pas de résultat net
screener.per_historique(an6, lambda d: 120.0, True, ACT)
check("sans résultat net, rien n'est vérifiable : on ne retire pas sur un soupçon",
      an6[0]["per"] == 6.0)
an7 = [{"fin": "2023-12-31", "eps": 20.0, "rn": 2000}]
screener.per_historique(an7, lambda d: 120.0, True, None)
check("sans nombre d'actions actuel non plus", an7[0]["per"] == 6.0)

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
        "tr": [{"fin": f"20{10+i//4}-{(3*(i%4)+3):02d}-30", "ca": i} for i in range(30)]}
f = screener.fusionner_fonda(GROS, {"devise": "USD", "an": [], "tr": []})
check("garde-fou de croissance : le plafond de trimestres borne, les plus récents survivent",
      len(f["tr"]) == screener.edgar.MAX_TRIMESTRES and f["tr"][-1]["ca"] == 29,
      f'{len(f["tr"])} trimestres')
# Le plafond est un garde-fou de TAILLE, pas une limite de profondeur : il a
# été relevé le 06/08 après avoir constaté que 52 fiches sur 97 butaient
# exactement dessus — elles étaient tronquées par nous, pas par la source.
check("les deux points de troncature partagent le même plafond nommé",
      screener.fusionner_fonda.__defaults__[0] == screener.edgar.MAX_EXERCICES)
# LE PER TRAVERSAIT LA FUSION AVEC LA BASE DE CALCUL DE LA VEILLE. Les exercices
# anciens ne sont plus produits par le run courant : leur multiple est repris tel
# quel. Tant que le change et le rapport d'ADR sont les mêmes, c'est juste ; dès
# qu'ils changent, sept vieux multiples faux se rangent sous quatre neufs justes.
_VIEUX = {"devise": "TWD", "per_converti": {"de": "USD", "vers": "TWD"},
          "an": [{"fin": "2015-12-31", "ca": 10, "eps": 1.0, "per": 26.8},
                 {"fin": "2016-12-31", "ca": 11, "eps": 1.1, "per": 25.0}]}
_NEUF = {"devise": "TWD", "per_converti": {"de": "USD", "vers": "TWD", "rapport": 2},
         "an": [{"fin": "2016-12-31", "ca": 11, "eps": 1.1, "per": 12.5}]}
_fb = screener.fusionner_fonda(_VIEUX, _NEUF)
check("base de calcul changée : le multiple ancien est retiré, pas conservé",
      "per" not in _fb["an"][0] and _fb["an"][1]["per"] == 12.5, str(_fb["an"]))
check("et les chiffres publiés de cet exercice, eux, survivent",
      _fb["an"][0]["ca"] == 10 and _fb["an"][0]["eps"] == 1.0, str(_fb["an"][0]))
_fm = screener.fusionner_fonda(_VIEUX, {**_NEUF, "per_converti": _VIEUX["per_converti"]})
check("base inchangée : le multiple ancien traverse la fusion",
      _fm["an"][0]["per"] == 26.8, str(_fm["an"][0]))
_sans = screener.fusionner_fonda({"devise": "USD", "an": [{"fin": "2015-12-31", "per": 20.0}]},
                                 {"devise": "USD", "an": [{"fin": "2016-12-31", "per": 21.0}]})
check("aucune conversion des deux côtés : rien n'est retiré",
      _sans["an"][0]["per"] == 20.0, str(_sans["an"]))
# 07/08 : la chaîne a TROIS troncatures (construire_fonda, completer_fonda,
# fusionner_fonda) et la plus étroite gagne. `construire_fonda` gardait 12 et 20
# en dur après le relèvement des constantes — 44 fiches sont restées bloquées à
# EXACTEMENT 12 exercices, toutes éligibles EDGAR, alors que les deux
# troncatures suivantes étaient déjà larges. Aucune ne doit écrire sa borne.
check("aucune troncature ne code sa borne en dur : toutes lisent les constantes",
      screener.edgar.construire_fonda.__defaults__ ==
      (screener.edgar.MAX_EXERCICES, screener.edgar.MAX_TRIMESTRES),
      str(screener.edgar.construire_fonda.__defaults__))
GROS_AN = {"devise": "USD", "tr": [],
           "an": [{"fin": f"{2000+i}-12-31", "ca": i} for i in range(26)]}
fa = screener.fusionner_fonda(GROS_AN, {"devise": "USD", "an": [], "tr": []})
check("l'historique annuel est borné au plafond, les exercices récents gardés",
      len(fa["an"]) == screener.edgar.MAX_EXERCICES and fa["an"][-1]["ca"] == 25)
f = screener.fusionner_fonda({"devise": "USD", "an": [], "tr": [],
                              "pe_prev": [{"exercice": 2026, "per": 30.0}]},
                             {"devise": "USD", "an": [], "tr": []})
check("estimations PER : le run muet n'efface pas les précédentes",
      f["pe_prev"] == [{"exercice": 2026, "per": 30.0}])
# 07/08 : `proj` avait été ajouté à `fonda` sans être ajouté ICI. La fusion
# reconstruit le bloc de zéro, donc le champ était SILENCIEUSEMENT PERDU à la
# publication — 96 fiches sur 97 sont sorties sans trajectoire, seule celle
# créée ce jour-là (sans ancien à fusionner) en portait une.
PJ = [{"exercice": 2027, "ca": 500, "ca_nature": "extrapolé", "nature": "extrapolé"}]
f = screener.fusionner_fonda({"devise": "USD", "an": [], "tr": []},
                             {"devise": "USD", "an": [], "tr": [], "proj": PJ})
check("la trajectoire attendue SURVIT à la fusion (bug du 07/08)", f.get("proj") == PJ)
# ... mais sans repli sur l'ancienne : depuis le refus de prolonger, l'absence
# de projection est une DÉCISION, et reprendre celle d'hier la ressusciterait.
f = screener.fusionner_fonda({"devise": "USD", "an": [], "tr": [], "proj": PJ},
                             {"devise": "USD", "an": [], "tr": []})
check("une trajectoire retirée ne revient pas par la fusion", "proj" not in f)
# MÊME LEÇON POUR LE PER PRÉVISIONNEL, apprise le 09/08/2026 en la revivant.
# Son repli sur l'ancien run avait été écrit pour une PANNE — la source muette
# un jour — et ne savait pas la distinguer d'un REFUS. Depuis qu'on refuse de
# publier un multiple dont la devise est indécidable, le run rendait une liste
# vide et la fusion ressuscitait aussitôt les valeurs de la veille, celles-là
# mêmes qu'on venait d'écarter : quatre fiches ont continué d'afficher leur
# ancien multiple APRÈS le correctif, avec le drapeau d'indécision à côté.
_PE = [{"exercice": 2026, "per": 30.0}]
_base = {"devise": "USD", "an": [], "tr": [], "pe_prev": _PE}
_f = screener.fusionner_fonda(_base, {"devise": "USD", "an": [], "tr": []})
check("source muette : l'ancien multiple prévisionnel est conservé",
      _f.get("pe_prev") == _PE, str(_f.get("pe_prev")))
_f = screener.fusionner_fonda(_base, {"devise": "USD", "an": [], "tr": [],
                                      "pe_prev_indecis": True})
check("refus délibéré : l'ancien multiple ne revient PAS",
      "pe_prev" not in _f, str(_f.get("pe_prev")))
check("et le motif du refus, lui, est publié",
      _f.get("pe_prev_indecis") is True)
# Même règle pour la solidité du consensus : elle décrit le run courant.
fc = screener.fusionner_fonda(
    {"devise": "USD", "an": [], "tr": [], "consensus": {"analystes": 9}},
    {"devise": "USD", "an": [], "tr": [], "consensus": {"analystes": 38}})
check("la solidité du consensus est celle du run courant, jamais d'hier",
      fc["consensus"] == {"analystes": 38}, str(fc.get("consensus")))
check("un consensus disparu ne ressuscite pas",
      "consensus" not in screener.fusionner_fonda(
          {"devise": "USD", "an": [], "tr": [], "consensus": {"analystes": 9}},
          {"devise": "USD", "an": [], "tr": []}))
# Garde-fou générique : tout champ de `fonda` que la fusion ignore disparaît.
# Ce test échouera dès qu'un nouveau champ sera ajouté sans être traité ici.
CHAMPS = {"devise", "an", "tr", "pe_prev", "proj", "consensus", "per_converti", "pe_prev_indecis"}
plein = {"devise": "USD", "an": [{"fin": "2025-12-31", "ca": 1}], "tr": [],
         "pe_prev": [{"exercice": 2026, "per": 30.0}], "proj": PJ,
         "consensus": {"analystes": 38, "ecart_pct": 3.7},
         "per_converti": {"de": "CHF", "vers": "USD"}, "pe_prev_indecis": True}
check("aucun champ de fonda n'est perdu en silence par la fusion",
      set(screener.fusionner_fonda(plein, plein)) == CHAMPS,
      str(CHAMPS ^ set(screener.fusionner_fonda(plein, plein))))
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

# ── Compléments lus dans les états financiers (couverture 100 %) ────────────
print("\n— États financiers : combler ce que le résumé Yahoo ne dit pas —")
CF = FDF({
    "Operating Cash Flow": {"2024-12-31": 8_000_000_000, "2025-12-31": 9_500_000_000},
    "Capital Expenditure": {"2024-12-31": -2_000_000_000, "2025-12-31": -2_500_000_000},
})
BS = FDF({
    "Stockholders Equity": {"2024-12-31": 40_000_000_000, "2025-12-31": 44_000_000_000},
    "Total Debt":          {"2024-12-31": 12_000_000_000, "2025-12-31": 11_000_000_000},
})
ec = screener.etats_complements(CF, BS)
check("flux disponible = exploitation − investissements, exercice le plus récent",
      ec.get("fcf") == 7_000_000_000, str(ec.get("fcf")))
check("capitaux propres et dette lus au dernier bilan",
      ec.get("capitaux_propres") == 44_000_000_000 and ec.get("dette") == 11_000_000_000,
      str(ec))
check("dette / capitaux propres exploitable (25 %)",
      round(ec["dette"] / ec["capitaux_propres"] * 100) == 25)
# La ligne toute faite prime sur le calcul quand l'émetteur la publie
ec2 = screener.etats_complements(
    FDF({"Free Cash Flow": {"2025-12-31": 6_600_000_000},
         "Operating Cash Flow": {"2025-12-31": 9_500_000_000},
         "Capital Expenditure": {"2025-12-31": -2_500_000_000}}), BS)
check("« Free Cash Flow » publié prime sur la reconstitution",
      ec2["fcf"] == 6_600_000_000, str(ec2["fcf"]))
# Libellés alternatifs (les émetteurs ne nomment pas leurs lignes pareil)
ec3 = screener.etats_complements(
    FDF({"Total Cash From Operating Activities": {"2025-12-31": 5_000_000_000},
         "Capital Expenditures": {"2025-12-31": -1_000_000_000}}),
    FDF({"Common Stock Equity": {"2025-12-31": 20_000_000_000},
         "Long Term Debt": {"2025-12-31": 6_000_000_000},
         "Current Debt": {"2025-12-31": 1_000_000_000}}))
check("libellés alternatifs reconnus (flux, capitaux propres)",
      ec3["fcf"] == 4_000_000_000 and ec3["capitaux_propres"] == 20_000_000_000)
check("dette recomposée long terme + court terme",
      ec3["dette"] == 7_000_000_000, str(ec3.get("dette")))
# Compte de résultat du MÊME exercice : sans lui, la conversion du bénéfice en
# cash divisait un flux annuel par une marge glissante d'une autre provenance —
# c'est ce qui donnait 12 % de conversion à Microsoft et 0 sur 7 aux meilleurs
# générateurs de trésorerie de l'univers (relevé du 07/08).
IS = FDF({"Total Revenue": {"2024-12-31": 30_000_000_000, "2025-12-31": 34_000_000_000},
          "Net Income":    {"2024-12-31":  7_000_000_000, "2025-12-31":  8_000_000_000}})
eci = screener.etats_complements(CF, BS, IS)
check("chiffre d'affaires et résultat net lus au MÊME exercice que le flux",
      eci["ca"] == 34_000_000_000 and eci["rn"] == 8_000_000_000, str(eci))
check("la conversion se calcule alors sur des grandeurs homogènes (88 %)",
      round(eci["fcf"] / eci["rn"] * 100) == 88)
check("la marge de flux disponible aussi (21 %)",
      round(eci["fcf"] / eci["ca"] * 100) == 21)
check("libellé alternatif du résultat net reconnu",
      screener.etats_complements(CF, BS, FDF({
          "Net Income Common Stockholders": {"2025-12-31": 5_000_000_000}}))["rn"]
      == 5_000_000_000)
check("un chiffre d'affaires nul ou absent n'est jamais inventé",
      "ca" not in screener.etats_complements(CF, BS, FDF({"Total Revenue": {"2025-12-31": 0}})))
# Fail-soft : rien ne doit être deviné
check("états vides → dict vide, aucune valeur inventée",
      screener.etats_complements(None, None) == {}
      and screener.etats_complements(FDF({}), FDF({}), FDF({})) == {})
check("capitaux propres négatifs : pas de ratio trompeur",
      "capitaux_propres" not in screener.etats_complements(
          CF, FDF({"Stockholders Equity": {"2025-12-31": -3_000_000_000}})))
check("bilan sans ligne de dette : la dette est omise, pas mise à zéro",
      "dette" not in screener.etats_complements(
          CF, FDF({"Stockholders Equity": {"2025-12-31": 1_000_000_000}})))
check("capex déposé en positif : la valeur absolue est prise",
      screener.etats_complements(
          FDF({"Operating Cash Flow": {"2025-12-31": 5_000_000_000},
               "Capital Expenditure": {"2025-12-31": 1_000_000_000}}), BS)["fcf"]
      == 4_000_000_000)

# ── Projections jusqu'à 2030 : consensus puis prolongation ──────────────────
print("\n— Projections : deux natures de lignes, jamais confondues —")
AN_P = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
        [(2021, 100, 1.0), (2022, 112, 1.2), (2023, 125, 1.4),
         (2024, 140, 1.6), (2025, 157, 1.85)]]
pr = screener.projections(AN_P, {"0y": 2.1, "+1y": 2.4},
                          {"0y": 176, "+1y": 197}, "2025-12-31")
check("la trajectoire va bien jusqu'à 2030",
      [e["exercice"] for e in pr] == [2026, 2027, 2028, 2029, 2030], str(pr))
check("les deux exercices couverts par les analystes sont dits « consensus »",
      [e["nature"] for e in pr[:2]] == ["consensus"] * 2)
check("au-delà, tout est dit « extrapolé » — aucun analyste ne va à 5 ans",
      [e["nature"] for e in pr[2:]] == ["extrapolé"] * 3)
check("le consensus est repris tel quel, jamais recalculé",
      pr[0]["ca"] == 176 and pr[1]["eps"] == 2.4)
check("la trajectoire est croissante et sans rupture",
      all(pr[i]["ca"] < pr[i + 1]["ca"] for i in range(len(pr) - 1)))
# La croissance doit DÉCROÎTRE : c'est la règle d'or de tout exercice de projection
g = [(pr[i + 1]["ca"] / pr[i]["ca"] - 1) * 100 for i in range(1, len(pr) - 1)]
check("la croissance décélère d'année en année vers le taux terminal",
      all(g[i] > g[i + 1] for i in range(len(g) - 1)), str([round(x, 1) for x in g]))
check("le dernier pas approche les 3 % terminaux", g[-1] < 10, str(round(g[-1], 1)))
# Croissance forte mais prolongeable (~35 %/an) : on PART de ce rythme et on
# décroît, on ne le rabote pas. Le plafond de 25 % qui vivait ici est mort le
# 07/08 : mesuré sur TSMC contre un concurrent qui publie du consensus
# multi-annuel, la branche plafonnée sous-tirait de 24 % en fin d'horizon.
AN_HYPER = [{"fin": f"{y}-12-31", "ca": c} for y, c in
            [(2022, 120), (2023, 160), (2024, 215), (2025, 290)]]
ph = screener.projections(AN_HYPER, None, {"0y": 390, "+1y": 525}, "2025-12-31")
g_att = ((525 / 290) ** 0.5 - 1) * 100
g1 = (ph[2]["ca"] / ph[1]["ca"] - 1) * 100
check("croissance forte : le 1er pas extrapolé part du rythme du consensus",
      g_att * 0.7 < g1 < g_att, f"{g1:.1f} % pour un consensus à {g_att:.1f} %")
check("le consensus, lui, est repris tel quel (525 conservé)", ph[1]["ca"] == 525)
# UNE PERTE ATTENDUE EST UNE INFORMATION. Le consensus est publié quel que soit
# son signe (correction du 07/08 : nos fiches Nebius et CoreWeave n'affichaient
# AUCUN bénéfice attendu là où un concurrent montre les barres de pertes) ; ce
# qu'on refuse, c'est de PROLONGER une perte vers un taux de croissance.
AN_PERTE = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
            [(2023, 100, -1.0), (2024, 150, -2.0), (2025, 220, -0.5)]]
pp = screener.projections(AN_PERTE, {"0y": -0.2, "+1y": -0.1}, {"0y": 300, "+1y": 400},
                          "2025-12-31")
cons = [e for e in pp if e.get("eps_nature") == "consensus"]
check("BPA en perte : le consensus des analystes est PUBLIÉ, signe compris",
      [e["eps"] for e in cons] == [-0.2, -0.1], str(cons))
check("mais il n'est jamais prolongé au-delà du consensus",
      all(e.get("eps_nature") != "extrapolé" for e in pp), str(pp))
check("le motif du refus dit la perte, sans jargon",
      "en perte" in (cons[-1].get("eps_arret") or ""), cons[-1].get("eps_arret", ""))
check("le chiffre d'affaires, lui, continue de se projeter",
      any(e.get("ca_nature") == "extrapolé" for e in pp), str(pp[-1]))
# Une base positive qui bascule en perte attendue : même traitement.
BASCULE = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
           [(2023, 100, 1.0), (2024, 150, 0.8), (2025, 220, 0.4)]]
bp = screener.projections(BASCULE, {"0y": -0.3, "+1y": -0.9}, {"0y": 300, "+1y": 400},
                          "2025-12-31")
check("bénéfice qui bascule en perte : publié, non prolongé",
      [e.get("eps") for e in bp if e.get("eps") is not None] == [-0.3, -0.9], str(bp))

# UN ZÉRO EXACT N'EST PAS UNE ESTIMATION, C'EST UNE ABSENCE. Le fournisseur rend
# `0` là où il n'a pas de consensus, et rien ne distingue les deux dans sa
# réponse. Trouvé le 08/08/2026 en publiant la watchlist robotique : Rainbow
# Robotics sortait avec un chiffre d'affaires 2026 ET 2027 à 0,0 étiqueté
# « consensus », contre 34 milliards de wons réalisés en 2025 — la fiche aurait
# montré des barres de revenus s'effondrant à zéro en affirmant que c'est ce que
# les analystes attendent. C'est le seul cas de tout l'univers, et il n'existait
# aucun test pour le voir : c'est la sentinelle des projections qui a parlé.
ZERO = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
        [(2022, 150, 0.8), (2023, 180, 1.0), (2024, 216, 1.1), (2025, 260, 1.3)]]
pz = screener.projections(ZERO, {"0y": 0, "+1y": 0}, {"0y": 0, "+1y": 0}, "2025-12-31")
check("un consensus à zéro exact n'est jamais publié comme consensus",
      all(l.get("ca") != 0 and l.get("eps") != 0 for l in pz), str(pz[:2]))
check("aucune ligne ne se dit « consensus » sur la foi d'un zéro",
      all(l.get("ca_nature") != "consensus" and l.get("eps_nature") != "consensus"
          for l in pz), str(pz[:2]))
# ... et le zéro écarté, l'historique reprend la main : la série de CA est bien
# réelle, elle se prolonge donc normalement, en « extrapolé ».
check("le zéro écarté, l'historique prolonge le chiffre d'affaires",
      any(l.get("ca_nature") == "extrapolé" and l.get("ca", 0) > 300 for l in pz),
      str(pz[:2]))
# Le zéro est écarté, PAS le négatif : la règle du 07/08 tient toujours.
pn = screener.projections(ZERO, {"0y": -0.4, "+1y": 0}, {"0y": 0, "+1y": 410},
                          "2025-12-31")
check("le filtre du zéro ne mange pas les pertes attendues",
      any(l.get("eps") == -0.4 and l.get("eps_nature") == "consensus" for l in pn),
      str(pn[:2]))
check("ni le consensus valide qui suit un zéro",
      any(l.get("ca") == 410 and l.get("ca_nature") == "consensus" for l in pn),
      str(pn[:2]))

check("sans dernier exercice, rien n'est projeté",
      screener.projections(AN_P, None, None, None) == [])
check("un horizon déjà atteint ne projette rien",
      screener.projections(AN_P, None, None, "2031-12-31") == [])
check("ni consensus ni historique exploitable : aucune ligne inventée",
      screener.projections([{"fin": "2025-12-31", "ca": 100}], None, None,
                           "2025-12-31") == [])
check("une année mixte est prudemment dite extrapolée",
      all(e["nature"] == "extrapolé" for e in
          screener.projections(AN_P, None, {"0y": 176, "+1y": 197}, "2025-12-31")[2:]))

# ── UNE SEULE COURBE, ASSUMÉE ────────────────────────────────────────────────
# Le cône à deux branches est mort le 07/08 (« je préfère qu'on assume une
# position, on ne parle pas de haut de fourchette »). Ces vérifications sont
# des ANTI-RÉGRESSIONS : plus aucune borne haute nulle part, et le TCAM
# historique ne rabote plus le départ — il ne sert qu'aux refus.
cn = screener.projections(AN_HYPER, None, {"0y": 390, "+1y": 525}, "2025-12-31")
check("aucune borne haute publiée, nulle part",
      all(not any(k.endswith("_haut") for k in e) for e in cn), str(cn[-1]))
# Un passé LENT (7 %/an) sous un consensus RAPIDE : autrefois `min(g_att,g_dem)`
# ramenait le départ à 7 % — c'est exactement le biais mesuré sur TSMC.
LENT_PUIS_VITE = [{"fin": f"{y}-12-31", "ca": c} for y, c in
                  [(2021, 220), (2022, 235), (2023, 251), (2024, 269), (2025, 288)]]
lv = screener.projections(LENT_PUIS_VITE, None, {"0y": 400, "+1y": 555}, "2025-12-31")
g_dem = ((288 / 220) ** 0.25 - 1) * 100          # ~7 %/an démontrés
g_lv = (lv[2]["ca"] / lv[1]["ca"] - 1) * 100     # 1er pas extrapolé
check("un passé lent ne rabote plus un consensus rapide",
      g_lv > g_dem * 2, f"1er pas {g_lv:.1f} % pour un passé à {g_dem:.1f} %")
# Le TCAM démontré garde son rôle de REFUS : sous le taux terminal, on s'arrête.
DECLIN = [{"fin": f"{y}-12-31", "ca": c} for y, c in
          [(2021, 400), (2022, 380), (2023, 350), (2024, 330), (2025, 310)]]
dc = screener.projections(DECLIN, None, {"0y": 340, "+1y": 380}, "2025-12-31")
check("un passé en déclin fait toujours REFUSER la prolongation",
      all(e["nature"] == "consensus" for e in dc)
      and any("ca_arret" in e for e in dc), str(dc[-1]))

# ── Sur quoi repose le consensus (relevé par la sonde du 07/08) ──────────────
# Les tables d'estimations portent le nombre d'analystes et la fourchette
# basse/haute, jamais lus jusqu'ici. L'écart est considérable — 50 analystes
# sur Alphabet, DEUX sur Constellation Energy — et depuis que la trajectoire
# est une courbe unique et assumée, elle a l'autorité d'une affirmation.
class _TableEst:
    """Imite juste ce que le code lit d'une table yfinance."""
    def __init__(self, index, columns, data):
        self.index, self.columns, self._d = index, columns, data
    @property
    def loc(self):
        d = self._d
        class _L:
            def __getitem__(self, k): return d[k[0]][k[1]]
        return _L()

# Valeurs telles que Yahoo les renvoie RÉELLEMENT pour TSMC : le chiffre
# d'affaires arrive en CHAÎNES là où le bénéfice arrive en flottants, et la
# devise du consensus de CA est la devise COMPTABLE (TWD), pas la cotation.
TSM_RE = _TableEst(["0q", "+1q", "0y", "+1y"],
                   ["avg", "low", "high", "numberOfAnalysts", "currency"],
                   {"0y": {"avg": "5420351505550", "low": "5157000000000",
                           "high": "5557455540670", "numberOfAnalysts": "38",
                           "currency": "TWD"}})
s = screener._solidite_consensus(TSM_RE)
check("le nombre d'analystes est lu même sérialisé en texte", s["analystes"] == 38, str(s))
check("le désaccord est une DEMI-fourchette rapportée à la moyenne",
      s["ecart_pct"] == 3.7, str(s))
check("la devise du consensus est lue TELLE QU'ÉTIQUETÉE (TWD, pas la cotation)",
      s["devise"] == "TWD", str(s))
check("une table sans colonnes ne lève pas, elle se tait",
      screener._solidite_consensus(_TableEst(["0y"], [], {"0y": {}})) is None)
check("une table absente se tait aussi", screener._solidite_consensus(None) is None)
# Une fourchette incohérente ne doit pas produire un écart négatif : on garde
# ce qui est lisible et on jette ce qui ne l'est pas.
INCO = _TableEst(["0y"], ["avg", "low", "high", "numberOfAnalysts"],
                 {"0y": {"avg": 100, "low": 120, "high": 80, "numberOfAnalysts": 2}})
check("fourchette inversée : l'écart est écarté, le compte d'analystes reste",
      screener._solidite_consensus(INCO) == {"analystes": 2},
      str(screener._solidite_consensus(INCO)))
check("NaN et texte non numérique donnent None, pas une exception",
      screener._nombre(float("nan")) is None and screener._nombre("n/a") is None
      and screener._nombre("38") == 38.0)

# ── Croissance trimestrielle : calculée sur NOTRE série, pas lue chez Yahoo ──
# Question du propriétaire, 07/08 : « Croiss CA · a/a +12,7 %, ça correspond à
# quoi ? ». Le recoupement a montré que `revenueGrowth` de Yahoo ne portait pas
# toujours sur le trimestre que le graphique dessine (30 fiches désynchronisées)
# ni toujours sur la même définition du revenu (6 fiches d'assureurs et de
# services aux collectivités). On la calcule donc sur la série qu'on publie.
TRIMS = [{"fin": f, "ca": c} for f, c in
         [("2025-03-31", 100), ("2025-06-30", 110), ("2025-09-30", 120),
          ("2025-12-31", 130), ("2026-03-31", 125)]]
check("croissance trimestrielle : dernier trimestre vs MÊME trimestre un an plus tôt",
      screener.croissance_ca_trimestrielle(TRIMS) == 25.0,
      str(screener.croissance_ca_trimestrielle(TRIMS)))
check("ce n'est PAS le trimestre précédent (qui donnerait -3,8 %)",
      screener.croissance_ca_trimestrielle(TRIMS) != -3.8)
check("moins de deux trimestres : rien n'est inventé",
      screener.croissance_ca_trimestrielle([TRIMS[0]]) is None)
check("aucun homologue à un an : on se tait plutôt que de comparer n'importe quoi",
      screener.croissance_ca_trimestrielle(TRIMS[:3]) is None)
check("base nulle ou négative : pas de division absurde",
      screener.croissance_ca_trimestrielle(
          [{"fin": "2025-03-31", "ca": 0}, {"fin": "2026-03-31", "ca": 50}]) is None)
check("un trimestre sans CA ne casse pas l'appariement",
      screener.croissance_ca_trimestrielle(
          [{"fin": "2025-03-31", "ca": 100}, {"fin": "2025-06-30", "ca": None},
           {"fin": "2026-03-31", "ca": 150}]) == 50.0)
# Le décalage de quelques jours d'un calendrier fiscal reste apparié ; un
# semestre, non — sinon on comparerait des durées différentes.
check("un exercice décalé de quelques jours reste apparié",
      screener.croissance_ca_trimestrielle(
          [{"fin": "2025-03-28", "ca": 100}, {"fin": "2026-04-03", "ca": 120}]) == 20.0)
check("un semestre n'est jamais apparié comme un an",
      screener.croissance_ca_trimestrielle(
          [{"fin": "2025-09-30", "ca": 100}, {"fin": "2026-03-31", "ca": 120}]) is None)

# ── Le refus de prolonger : une projection qu'on sait fausse ne s'affiche pas ─
# Leçon du 07/08 (signalée par le propriétaire, sur Nebius) : au-delà d'un
# certain rythme, toute prolongation est fausse — amortir donnait 18 Md$ en
# 2030 quand le marché en discute 33 à 46, ne pas amortir donnait 140 Md$.
# Aucun réglage n'est une réponse : on s'arrête, avec le motif.
CONTRACTE = [{"fin": f"{y}-12-31", "ca": c} for y, c in
             [(2022, 14), (2023, 10), (2024, 92), (2025, 530)]]
nb = screener.projections(CONTRACTE, None, {"0y": 3500, "+1y": 9000}, "2025-12-31")
check("hypercroissance : SEULS les deux exercices de consensus sortent",
      [e["exercice"] for e in nb] == [2026, 2027], str(nb))
check("et ils sont bien étiquetés consensus, repris tels quels",
      [e["nature"] for e in nb] == ["consensus"] * 2
      and [e["ca"] for e in nb] == [3500, 9000], str(nb))
check("aucune borne haute inventée quand on refuse de prolonger",
      all(not any(k.endswith("_haut") for k in e) for e in nb))
check("le motif d'arrêt est porté par la dernière ligne de la série",
      "ca_arret" in nb[-1] and "ca_arret" not in nb[0], str(nb))
check("le motif dit pourquoi, en français, sans jargon",
      "engagements contractuels" in nb[-1]["ca_arret"], nb[-1].get("ca_arret", ""))
# L'arrêt est PAR SÉRIE : un CA incalculable ne condamne pas un BPA prolongeable
MIXTE = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
         [(2023, 100, 1.0), (2024, 200, 1.2), (2025, 530, 1.4)]]
mx = screener.projections(MIXTE, {"0y": 1.6, "+1y": 1.8}, {"0y": 3500, "+1y": 9000},
                          "2025-12-31")
check("série par série : le CA s'arrête, le BPA va quand même à 2030",
      [e["exercice"] for e in mx] == [2026, 2027, 2028, 2029, 2030], str(mx))
check("au-delà de l'arrêt, plus aucune valeur de CA n'est publiée",
      all("ca" not in e for e in mx if e["exercice"] > 2027)
      and all("eps" in e for e in mx), str(mx))
check("le motif d'arrêt du CA ne prétend rien sur le BPA",
      "ca_arret" in mx[1] and "eps_arret" not in mx[1], str(mx[1]))
# La MÊME série que la note. Sans cette cohérence, la fiche Adyen se
# contredisait : le bloc croissance annonçait « +19,2 % par an » (série
# tronquée à la rupture de périmètre de 2023) pendant que les projections
# refusaient de prolonger « faute de rythme constaté », en mesurant, elles, à
# travers la marche. Un même chiffre d'affaires ne peut pas avoir deux
# trajectoires sur la même page.
RUPTURE = [{"fin": f"{y}-12-31", "ca": c} for y, c in
           [(2022, 8936), (2023, 1863), (2024, 2226), (2025, 2647)]]
rp = screener.projections(RUPTURE, None, None, "2025-12-31")
check("les projections tronquent la même rupture de périmètre que la note",
      len(rp) == 5 and rp[0]["ca"] > 2647, str(rp[:1]))
g_rp = (rp[0]["ca"] / 2647 - 1) * 100
check("et prolongent donc le périmètre actuel, pas la marche",
      0 < g_rp < 25, f"{g_rp:.1f} %")
check("une société sans consensus et en hypercroissance démontrée ne dit rien",
      screener.projections(CONTRACTE, None, None, "2025-12-31") == [])
# Le piège des ADR : le CA estimé est toujours publié en devise COMPTABLE (TSM
# et 2330.TW rendent le même nombre à l'unité près), tandis que le BPA estimé
# suit une convention qui VARIE — par ADR et en dollars sur TSM, en devise
# comptable sur Ferrari. TSM publiait 331,25 TWD de BPA et nous en projetions
# 16,82 : le « taux de croissance » n'était qu'un taux de change.
ADR = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
       [(2023, 2161736, 176.0), (2024, 2894308, 226.25), (2025, 3809054, 331.25)]]
adr = screener.projections(ADR, {"0y": 16.8, "+1y": 21.6},
                           {"0y": 5420352, "+1y": 7187439}, "2025-12-31",
                           bpa_comparable=False)
check("ADR : aucune estimation de BPA en devise étrangère n'entre dans la série",
      all(e.get("eps") is None or e["eps"] > 100 for e in adr), str(adr[:2]))
check("ADR : le chiffre d'affaires, lui, se projette normalement",
      adr[0]["ca"] == 5420352 and adr[0]["ca_nature"] == "consensus")
mm = screener.projections(ADR, {"0y": 16.8, "+1y": 21.6},
                          {"0y": 5420352, "+1y": 7187439}, "2025-12-31")
check("même devise : les estimations de BPA sont bien prises",
      mm[0]["eps"] == 16.8, str(mm[0]))
# La nature est publiée PAR SÉRIE : sans elle, un BPA extrapolé ferait passer
# pour « extrapolé » un chiffre d'affaires qui est du consensus (bug vu sur NBIS)
mixte = screener.projections(AN_P, None, {"0y": 176, "+1y": 197}, "2025-12-31")[0]
check("chaque série porte sa propre nature, exacte",
      mixte["ca_nature"] == "consensus" and mixte["eps_nature"] == "extrapolé", str(mixte))
check("la nature de l'année reste la plus prudente des deux séries",
      mixte["nature"] == "extrapolé", str(mixte))
# Refus PAR LE BAS : le modèle décroît vers 3 %, il suppose un départ au-dessus.
# Cas réel : le BPA de Nebius, −36 %/an constatés, était publié en HAUSSE à 2030.
DECLIN = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
          [(2022, 14, 1.59), (2023, 10, 0.60), (2024, 92, -2.28), (2025, 530, 0.40)]]
dc = screener.projections(DECLIN, None, {"0y": 700, "+1y": 900}, "2025-12-31")
check("un BPA au rythme démontré négatif n'est JAMAIS relevé à +3 %",
      all("eps" not in e for e in dc), str(dc))
check("le CA, lui, se projette normalement (les séries sont indépendantes)",
      [e["exercice"] for e in dc] == [2026, 2027, 2028, 2029, 2030], str(dc))
check("aucun motif d'arrêt inventé pour une série jamais commencée",
      all("eps_arret" not in e for e in dc))

# ── Historique profond, étage 1 : EDGAR parle aussi IFRS ────────────────────
print("\n— EDGAR IFRS : les déposants étrangers entrent au greffe —")
check("un ticker US natif est éligible", edgar.eligible("NVDA"))
check("une cotation d'origine mappée est éligible (ASML.AS → ASML)",
      edgar.eligible("ASML.AS") and edgar.US_EQUIV["ASML.AS"] == "ASML")
check("un non-déposant reste hors périmètre (Disco, Tokyo)",
      not edgar.eligible("6146.T"))
check("les six mappings 20-F sont présents et pointent vers des symboles US",
      all(edgar.US_EQUIV.get(k) == v for k, v in
          [("SAP.DE", "SAP"), ("TTE.PA", "TTE"), ("AZN.L", "AZN"),
           ("HSBA.L", "HSBC"), ("UBSG.SW", "UBS")]))
DOC_EUR = {"units": {"EUR": [
    {"frame": "CY2023", "end": "2023-12-31", "val": 31_207_000_000},
    {"frame": "CY2024", "end": "2024-12-31", "val": 34_176_000_000},
    {"end": "2022-12-31", "val": 999},                  # sans frame : ignoré
]}}
s_eur = edgar.series_frames(DOC_EUR, "EUR")
check("les faits IFRS se lisent dans la devise comptable demandée",
      s_eur.get("CY2024") == ("2024-12-31", 34_176_000_000) and len(s_eur) == 2)
check("demander une autre unité ne rend rien (pas de mélange de monnaies)",
      edgar.series_frames(DOC_EUR, "USD") == {})
check("le BPA IFRS vit sous l'unité <devise>/shares",
      edgar.series_frames({"units": {"EUR/shares": [
          {"frame": "CY2024", "end": "2024-12-31", "val": 5.44}]}},
          "EUR/shares").get("CY2024") == ("2024-12-31", 5.44))
check("le résultat IFRS préfère la part des actionnaires de la mère",
      edgar.TAGS_RN_IFRS[0] == "ProfitLossAttributableToOwnersOfParent")

# ── Historique profond, étage 2 : l'apport vérifié des non-déposants ────────
print("\n— Apport vérifié : le fichier des non-déposants —")
import tempfile
_ap_avant, _path_avant = screener._APPORT, screener.APPORT_PATH
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
    json.dump({"_mode_d_emploi": "doc",
               "005930.KS": {"devise": "KRW", "source": "rapport annuel 2020, p.12",
                             "an": [{"fin": "2016-12-31", "ca": 201_866_745,
                                     "rn": 22_726_092, "eps": 2_735.0}]},
               "RMS.PA": {"devise": "USD",   # devise fausse exprès
                          "an": [{"fin": "2016-12-31", "ca": 5_202}]}}, tf)
    tf.flush(); screener.APPORT_PATH = tf.name
screener._APPORT = None
ap = screener.charger_apport("005930.KS", "KRW")
check("un bloc à devise conforme est rendu, estampillé src:'apport'",
      ap and ap["an"][0]["src"] == "apport" and ap["an"][0]["ca"] == 201_866_745)
check("la clé de documentation n'est pas un ticker",
      screener.charger_apport("_mode_d_emploi", "KRW") is None)
check("devise non conforme : bloc écarté (pas de mélange de monnaies)",
      screener.charger_apport("RMS.PA", "EUR") is None)
check("ticker absent du fichier : rien", screener.charger_apport("NVDA", "USD") is None)
FONDA_AP = {"devise": "KRW",
            "an": [{"fin": "2024-12-31", "ca": 300_870_903, "rn": 34_451_351}], "tr": []}
edgar.completer_fonda(FONDA_AP, ap)
check("l'apport étend l'historique par les mêmes gardes que l'EDGAR",
      len(FONDA_AP["an"]) == 2 and FONDA_AP["an"][0]["src"] == "apport")
screener._APPORT, screener.APPORT_PATH = _ap_avant, _path_avant
import os as _os; _os.unlink(tf.name)
check("le fichier d'apport du dépôt est un JSON valide",
      isinstance(json.load(open("data/apport_historique.json")), dict))

# ── Chaîne des sources : Yahoo → états financiers → comptes publiés → Finnhub
print("\n— Chaîne des sources : chaque maillon ne comble que ce qui reste —")
AN_CH = [{"fin": "2023-12-31", "ca": 10_000, "rn": 1_500, "eps": 3.0},
         {"fin": "2024-12-31", "ca": 12_000, "rn": 2_400, "eps": 4.0}]
nm, tpe, src = screener.chainer_comptes(AN_CH, True, 80.0, None, None)
check("marge nette déduite du dernier exercice (2 400/12 000 = 20 %)",
      abs(nm - 0.20) < 1e-9, str(nm))
check("PER courant déduit du cours et du dernier BPA (80/4 = 20×)",
      abs(tpe - 20.0) < 1e-9, str(tpe))
check("provenance des deux valeurs enregistrée", src == ["marge", "per"], str(src))
nm2, tpe2, src2 = screener.chainer_comptes(AN_CH, True, 80.0, 0.31, 44.0)
check("une valeur déjà connue n'est jamais écrasée",
      nm2 == 0.31 and tpe2 == 44.0 and src2 == [], str(src2))
# Piège des ADR : cours en USD, BPA en TWD → aucun PER déductible
_, tpe3, src3 = screener.chainer_comptes(AN_CH, False, 80.0, None, None)
check("devise comptable ≠ cotation : pas de PER déduit (piège ADR)",
      tpe3 is None and "per" not in src3, str(src3))
check("BPA négatif ou nul : pas de PER (une perte n'a pas de multiple)",
      screener.chainer_comptes([{"fin": "2024-12-31", "ca": 9, "rn": -2, "eps": -1.5}],
                               True, 80.0, None, None)[1] is None)
check("historique vide : rien n'est inventé",
      screener.chainer_comptes([], True, 80.0, None, None) == (None, None, []))

# Finnhub, dernier maillon — la conversion d'unités est le vrai piège
fnm, fde, fsrc = screener.chainer_finnhub(
    {"net_margin": 18.5, "debt_equity": 0.74}, None, None)
check("marge Finnhub convertie de % en fraction (18,5 → 0,185)",
      abs(fnm - 0.185) < 1e-9, str(fnm))
check("dette/CP Finnhub convertie de ratio en % (0,74 → 74)",
      abs(fde - 74.0) < 1e-9, str(fde))
check("provenance Finnhub enregistrée", fsrc == ["marge", "dette"], str(fsrc))
check("Finnhub n'écrase jamais une valeur déjà obtenue",
      screener.chainer_finnhub({"net_margin": 18.5, "debt_equity": 0.74},
                               0.22, 61.0) == (0.22, 61.0, []))
check("Finnhub muet (titre non US) : la chaîne s'arrête sans rien changer",
      screener.chainer_finnhub({}, None, None) == (None, None, []))

# ── Métier de bilan : le drapeau se déduit du MÉTIER, jamais d'une donnée ───
# Régression du 06/08 : le drapeau valait « secteur financier ET FCF absent ».
# Dès qu'on a su reconstituer le FCF depuis les états financiers, il s'est
# éteint pour TOUS les titres — rampe bancaire du ROE et critère cours/actifs
# nets devenus code mort, HSBC notée 0,7/5 sur un levier qui EST son métier.
print("\n— Métiers de bilan : drapeau déduit de l'industrie —")
check("les banques et l'assurance sont dans la table",
      {"Banks - Diversified", "Banks—Regional", "Capital Markets",
       "Insurance - Property & Casualty"} <= screener._INDUSTRIES_BILAN)
check("les deux graphies Yahoo du tiret sont couvertes",
      all(("Banks - " + s in screener._INDUSTRIES_BILAN)
          and ("Banks—" + s in screener._INDUSTRIES_BILAN)
          for s in ("Diversified", "Regional")))
check("réseaux de paiement, places de marché et gérants d'actifs EXCLUS "
      "(ils dégagent un vrai flux disponible)",
      not ({"Credit Services", "Financial Data & Stock Exchanges",
            "Asset Management", "Insurance Brokers"} & screener._INDUSTRIES_BILAN))
check("le drapeau ne dépend d'aucun champ de données",
      "fcf" not in " ".join(screener._INDUSTRIES_BILAN).lower())

# ── Intégration note v4 dans le screener ────────────────────────────────────
print("\n— Note v4 : raison_sortie et projections lisent les nouveaux blocs —")
BD_V4 = {"note": {"total": 41, "couverture": 88,
                  "blocs": {"q": {"pts": 12.0, "max": 35, "dispo": 35},
                            "c": {"pts": 8.0,  "max": 25, "dispo": 25},
                            "v": {"pts": 15.0, "max": 25, "dispo": 25},
                            "m": {"pts": 2.5,  "max": 15, "dispo": 15}},
                  "criteres": []},
         "cross_regime": "neutral", "regression_signal": "neutre", "rsi": 50}
txt = screener.raison_sortie({"ticker": "XX", "score": 55},
                             {"ticker": "XX", "score": 41, "breakdown": BD_V4})
check("raison_sortie commente le momentum v4 (2,5/15)", "Momentum quasi-nul" in txt, txt)
check("raison_sortie somme Q+C+V sur 85", "35/85" in txt, txt)
BD_BANQUE = {"note": {"total": 70, "couverture": 81,
                      "blocs": {"q": {"pts": 30.0, "max": 35, "dispo": 23},
                                "c": {"pts": 14.0, "max": 25, "dispo": 25},
                                "v": {"pts": 12.0, "max": 25, "dispo": 20},
                                "m": {"pts": None, "max": 15, "dispo": 0}},
                      "criteres": []},
             "cross_regime": "neutral", "regression_signal": "neutre", "rsi": 50}
txt2 = screener.raison_sortie({"ticker": "YY", "score": 72},
                              {"ticker": "YY", "score": 70, "breakdown": BD_BANQUE})
check("un bloc momentum non notable (None) n'est pas commenté",
      "Momentum" not in txt2, txt2)
check("l'ancien breakdown sans note ne fait pas planter raison_sortie",
      isinstance(screener.raison_sortie({"ticker": "ZZ", "score": 50},
                                        {"ticker": "ZZ", "score": 44,
                                         "breakdown": {"qualite": 20}}), str))

# ── L'ÉCHELLE DU GRAPHIQUE DES CHIFFRES PUBLIÉS ────────────────────────────
# On exécute LE VRAI CODE de la page sous node, comme test_actualites.py le
# fait déjà pour le formatage : réécrire la formule dans le test la ferait
# diverger du dessin, et c'est précisément une divergence qu'on traque ici.
#
# LE DÉFAUT. Le haut de l'échelle comptait le bénéfice ATTENDU (déduit du BPA
# consensus, `rnAtt`) ; le bas ne lisait que le résultat PUBLIÉ (`rn`). Une
# société dont la perte attendue creuse sous toutes ses pertes passées voyait
# donc ses barres projetées sortir du cadre, par-dessus les étiquettes FY.
# Trois fiches touchées au 08/08/2026 — IonQ (débordement de 79 % de la
# hauteur du dessin), CoreWeave (44 %), Nebius (35 %) — signalé par le
# propriétaire sur téléphone.
print("\n— Le graphique des chiffres publiés tient-il dans son cadre ? —")
def _echelle(cols):
    """Rejoue le calcul d'échelle d'index.html et rend le bas de chaque barre."""
    src = open(os.path.join(RACINE, "index.html"), encoding="utf-8").read()
    deb = src.index("const maxV=Math.max(")
    fin = src.index("const slot=W/n,")
    prog = ("const H=170,PB=22;"
            "const cols=" + json.dumps(cols) + ";"
            "const val=(o,k)=>o.v[k]==null?null:o.v[k];"
            "const rnAtt=p=>p.rnAtt==null?null:p.rnAtt;"
            + src[deb:fin] +
            "const bas=cols.map(o=>{const v=o.pr?rnAtt(o.v):o.v.rn;"
            "  if(v==null)return null;const h=hVal(v);"
            "  return (h>=0?y0-h:y0)+Math.max(2,Math.abs(h));});"
            "const haut=cols.map(o=>{const v=o.v.ca;if(v==null)return null;"
            "  const h=hVal(v);return h>=0?y0-h:y0;});"
            "console.log(JSON.stringify({bas:bas,haut:haut,y0:y0,fond:H-PB}));")
    return json.loads(subprocess.run(["node", "-e", prog], capture_output=True,
                                     text=True, timeout=30, check=True).stdout)

try:
    # Données réelles d'IonQ au 08/08/2026 : quatre exercices publiés en perte,
    # puis deux exercices de consensus dont la perte est cinq fois plus creuse.
    _IONQ = [{"v": {"ca": 22, "rn": -158}, "pr": False},
             {"v": {"ca": 43, "rn": -158}, "pr": False},
             {"v": {"ca": 96, "rn": -332}, "pr": False},
             {"v": {"ca": 121, "rn": -510}, "pr": False},
             {"v": {"ca": 180, "rnAtt": -2486}, "pr": True},
             {"v": {"ca": 290, "rnAtt": -2100}, "pr": True}]
    _r = _echelle(_IONQ)
    _deborde = [i for i, b in enumerate(_r["bas"]) if b is not None and b > _r["fond"]]
    check("aucune barre de perte ne sort du cadre, projetée comprise",
          not _deborde, f"colonnes hors cadre : {_deborde} (fond={_r['fond']}, bas={_r['bas']})")
    check("aucune barre de chiffre d'affaires ne sort par le haut",
          all(h is None or h >= 0 for h in _r["haut"]), str(_r["haut"]))
    # La perte attendue doit VRAIMENT tirer le plancher : sans quoi le test
    # ci-dessus passerait aussi avec une échelle qui ignore les projections mais
    # dont les pertes publiées se trouvent être les plus profondes.
    check("le zéro descend pour faire de la place à la perte attendue",
          _r["y0"] < _r["fond"] * 0.5,
          f"y0={_r['y0']:.1f} pour un fond à {_r['fond']}")
    # Contrôle symétrique : une société sans perte attendue ne doit pas voir son
    # échelle bouger — le correctif ne devait rien changer au cas courant.
    _SAIN = [{"v": {"ca": 100, "rn": 10}, "pr": False},
             {"v": {"ca": 120, "rn": 14}, "pr": False},
             {"v": {"ca": 140, "rnAtt": 18}, "pr": True}]
    _s = _echelle(_SAIN)
    check("sans perte, le zéro reste posé au bas du dessin",
          _s["y0"] > _s["fond"] * 0.8, f"y0={_s['y0']:.1f}")
    check("et aucune barre ne sort du cadre non plus",
          all(b is None or b <= _s["fond"] + 0.01 for b in _s["bas"]), str(_s["bas"]))
except (OSError, subprocess.SubprocessError, ValueError) as _e:
    print(f"  \u26a0\ufe0f  échelle du graphique non vérifiée (node indisponible : {type(_e).__name__})")

# ── L'AXE DES ANNÉES : chaque exercice étiqueté, aucun chevauchement ────────
# Demande du propriétaire (08/08/2026) : « je veux voir apparaître chaque année
# FY21 FY22 etc. Pas de trou une année sur deux ». L'ancien code gardait une
# police FIXE et sautait des colonnes dès que ça serrait ; c'est désormais la
# TAILLE qui cède, et le saut n'est qu'un repli sous le plancher de lisibilité.
#
# DEUX PIÈGES, tous deux trouvés au navigateur et tous deux invisibles au
# relecteur :
#   1. une règle CSS l'emporte sur un attribut de présentation SVG, donc
#      `.chx-axis{font-size:10px}` annulait silencieusement tout calcul — les
#      étiquettes restaient à 10 px pendant que le code croyait les réduire.
#      La taille DOIT donc se poser en `style`, et ce test l'exige ;
#   2. la chasse de la fonte vaut 0,61 cadratin et non 0,6 : 2 % d'erreur
#      suffisaient à faire se toucher deux étiquettes voisines.
print("\n— L'axe des années montre-t-il chaque exercice ? —")
_ix = open(os.path.join(RACINE, "index.html"), encoding="utf-8").read()
check("le budget de colonnes est de douze",
      re.search(r"const FD_ANS=12\b", _ix) is not None)
# LE BUDGET PORTE SUR CE QU'ON DESSINE, projections comprises — précision du
# propriétaire (« 12 ans au total prévisionnel compris ») après une première
# lecture qui budgétait douze exercices PUBLIÉS plus cinq projetés, soit
# dix-sept colonnes. Les deux graphiques retranchent donc leurs colonnes vers
# l'avant avant de découper le passé, chacun le sien : cinq projections pour
# les barres, deux estimations pour le PER.
check("les barres retranchent les projections du budget",
      re.search(r"Math\.max\(4,FD_ANS-projC\.length\)", _ix) is not None,
      "le découpage doit tenir compte des colonnes projetées")
check("le PER retranche ses estimations du budget",
      re.search(r"slice\(-Math\.max\(4,FD_ANS-est\.length\)\)", _ix) is not None,
      "le découpage doit tenir compte des points estimés")
# Le plancher existe pour qu'un horizon lointain ne vide jamais le passé.
check("un plancher garde quatre exercices publiés quoi qu'il arrive",
      _ix.count("Math.max(4,FD_ANS-") == 2)
# La taille calculée doit atterrir dans un `style` : en attribut, le CSS gagne.
check("les deux axes posent leur taille, et la posent en style",
      _ix.count('style="font-size:\'+_ax.px+\'px"') == 1
      and _ix.count('style="font-size:\'+_axP.px+\'px"') == 1,
      "une taille posée en attribut font-size serait écrasée par .chx-axis")
check("aucune taille d'axe ne subsiste en attribut de présentation",
      'class="chx-axis" font-size=' not in _ix)
try:
    _prog = _ix[_ix.index("const AX_MIN="):_ix.index("function fondaRender(")]
    _cas = [[25.88, 4], [24.77, 4], [60, 4], [12, 4], [40, 6], [8, 4]]
    _out = json.loads(subprocess.run(
        ["node", "-e", _prog + "console.log(JSON.stringify("
         + json.dumps(_cas) + ".map(c=>axeAnnees(c[0],c[1]))));"],
        capture_output=True, text=True, timeout=30, check=True).stdout)
    # Le contrat : tant que la police reste au-dessus du plancher, le pas vaut 1
    # — c'est-à-dire que TOUTES les années sont étiquetées.
    check("aux largeurs réelles des fiches, chaque année est étiquetée",
          all(r["pas"] == 1 for r in _out[:3]), str(_out[:3]))
    check("l'étiquette tient dans son slot, gouttière comprise",
          all(c[1] * r["px"] * 0.61 <= c[0] - 2 + 1e-9
              for c, r in zip(_cas, _out) if r["pas"] == 1),
          str([(c, r) for c, r in zip(_cas, _out)]))
    check("la police ne descend jamais sous le plancher de lisibilité",
          all(r["px"] >= 7.4 - 1e-9 for r in _out), str(_out))
    check("elle ne dépasse pas non plus la taille de référence",
          all(r["px"] <= 10 + 1e-9 for r in _out), str(_out))
    # Sous le plancher, on saute des années PLUTÔT que de rendre l'axe illisible
    # ou chevauchant : le repli doit exister, sinon la garde ne sert à rien.
    check("trop serré : on saute des années au lieu de chevaucher",
          _out[-1]["pas"] > 1 and _out[-1]["px"] == 7.4, str(_out[-1]))
except (OSError, subprocess.SubprocessError, ValueError) as _e:
    print(f"  \u26a0\ufe0f  axe non vérifié (node indisponible : {type(_e).__name__})")

# ── PER HISTORIQUE QUAND COMPTES ET COTATION DIFFÈRENT DE DEVISE ───────────
# Cinq fiches publiaient leurs comptes dans une monnaie et cotaient dans une
# autre : ABB (USD/CHF), ASE (TWD/USD), Cameco (CAD/USD), Ferrari (EUR/USD),
# Vestas (EUR/DKK). Le quotient était refusé — à raison — et TRENTE ET UN
# exercices n'avaient aucun multiple. Le refus était bon, la conclusion trop
# courte : ce qui manquait n'était pas une raison de s'abstenir, c'était le
# taux. Depuis le 08/08/2026 on ramène le COURS dans la devise des comptes au
# change du jour de clôture — le terme qui se convertit sans convention, un
# prix étant un montant à un instant.
print("\n— Le multiple quand la devise des comptes n'est pas celle du cours —")
_AN_FX = [{"fin": "2023-12-31", "eps": 2.0, "rn": 2000},
          {"fin": "2024-12-31", "eps": 2.5, "rn": 2500},
          {"fin": "2025-12-31", "eps": 3.0, "rn": 3000}]
def _neuf():
    return [dict(e) for e in _AN_FX]
_prix = lambda iso: 100.0          # cours constant, en devise de COTATION
_tx = lambda iso: 1.25             # 1 unité cotée = 1,25 unité comptable

_a = screener.per_historique(_neuf(), _prix, False, None, _tx)
check("devises différentes AVEC taux : le multiple est calculé",
      [e.get("per") for e in _a] == [62.5, 50.0, 41.7], str([e.get("per") for e in _a]))
# 100 × 1,25 = 125 en devise comptable ; 125 / 2,0 = 62,5. Le multiple est bien
# celui du cours CONVERTI, pas celui du cours brut (qui aurait donné 50,0).
check("c'est bien le cours converti, pas le cours brut",
      _a[0]["per"] != round(100 / 2.0, 1))
# LE REPLI EST LA MOITIÉ IMPORTANTE : sans taux, on retombe sur le trou assumé.
# Un multiple calculé avec un taux inventé serait pire que pas de multiple.
_b = screener.per_historique(_neuf(), _prix, False, None, None)
check("devises différentes SANS taux : aucun multiple, comme avant",
      all(e.get("per") is None for e in _b), str([e.get("per") for e in _b]))
# Un taux manquant sur UN exercice ne doit pas contaminer les autres : le point
# est sauté, la courbe garde les siens.
_troue = lambda iso: (None if iso.startswith("2024") else 1.25)
_c = screener.per_historique(_neuf(), _prix, False, None, _troue)
check("un exercice sans taux est sauté, les autres restent",
      [e.get("per") for e in _c] == [62.5, None, 41.7], str([e.get("per") for e in _c]))
# Même devise : le taux ne doit JAMAIS s'appliquer, même s'il est fourni.
_d = screener.per_historique(_neuf(), _prix, True, None, _tx)
check("même devise : le cours n'est pas converti",
      [e.get("per") for e in _d] == [50.0, 40.0, 33.3], str([e.get("per") for e in _d]))
# Un taux nul ou négatif est une donnée cassée, pas un change : on saute.
for _mauvais, _nom in [(lambda i: 0.0, "nul"), (lambda i: -1.2, "négatif")]:
    _e = screener.per_historique(_neuf(), _prix, False, None, _mauvais)
    check(f"un taux {_nom} ne produit aucun multiple",
          all(x.get("per") is None for x in _e), str([x.get("per") for x in _e]))

# ── LE MULTIPLE PRÉVISIONNEL QUAND LES DEVISES DIFFÈRENT ───────────────────
# `per_previsionnel` AFFIRMAIT que les estimations d'analystes sont libellées
# dans la devise de cotation, sans jamais le vérifier. C'est faux au moins deux
# fois : Vestas affichait 154× (cours en couronnes, bénéfice estimé en euros) et
# Tencent 2,0× (cours en dollars, bénéfice estimé en yuans) — ce dernier repéré
# par le propriétaire sur la fiche publiée.
#
# ON TRANCHE PAR LA CROISSANCE IMPLICITE, quand elle tranche : le BPA estimé
# succède au dernier BPA publié, dont la devise est connue. Lu dans la bonne
# monnaie leur rapport est une croissance ; lu dans l'autre il vaut le taux de
# change. Et on s'abstient quand les deux lectures sont plausibles, c'est-à-dire
# dès que le change est proche de 1.
print("\n— Le multiple attendu quand les devises diffèrent —")
_EST = {"0y": 2.0, "+1y": 2.4}
check("devises identiques : les deux exercices attendus sont publiés",
      [(e["exercice"], e["per"]) for e in
       screener.per_previsionnel(60.0, _EST, "2025-12-31")] == [(2026, 30.0), (2027, 25.0)])
# LA SOURCE DÉCLARE LA DEVISE, ET NOUS NE LA LISIONS PAS. La sonde du 08/08 a
# relevé une colonne `currency` dans `earnings_estimate` — et surtout que la
# convention N'EST PAS UNIFORME d'un titre à l'autre. Ces quatre lignes sont des
# RELEVÉS, pas des cas inventés : c'est ce qui rend le test capable de contredire
# une règle plausible.
#
#   ticker   comptes  cotation  currency déclarée   lecture juste
#   TSM      TWD      USD       USD (par ADR)       cours tel quel
#   ASX      TWD      USD       USD (par ADR)       cours tel quel
#   RACE     EUR      USD       EUR                 cours converti
#   CCJ      CAD      USD       CAD                 cours converti
#
# Aucune règle déductible de la place de cotation, du sens du change ou de la
# croissance implicite ne produit ces quatre réponses : RACE et TSM cotent toutes
# deux à New York et ne suivent pas la même convention.
#           prix     BPA est.  taux   BPA publié comptes cotation déclarée attendu
_DECLARE = [("TSM",   295.0,  16.82,  31.0,  73.71, "TWD", "USD", "USD", "direct"),
            ("ASX",    37.39,  1.119, 31.0,  18.74, "TWD", "USD", "USD", "direct"),
            ("RACE",  412.26,  9.792,  0.926, 9.01, "EUR", "USD", "EUR", "converti"),
            ("CCJ",    97.39,  1.514,  1.37,  1.35, "CAD", "USD", "CAD", "converti")]
for _t, _p, _e, _tx, _ep, _dcompta, _dc, _de, _att in _DECLARE:
    _r = screener.per_previsionnel(_p, {"0y": _e, "+1y": _e * 1.08}, "2025-12-31",
                                   (lambda i, _x=_tx: _x), _ep, _de, _dc, _dcompta)
    _per = _r[0]["per"] if _r else None
    _got = ("trou" if _per is None
            else "converti" if abs(_per - _p * _tx / _e) < 0.05 else "direct")
    check(f"{_t} : devise déclarée {_de} → {_att}", _got == _att,
          f"obtenu {_got} ({_per})")
# Une devise déclarée qui n'est NI celle des comptes NI celle de la cotation est
# hors de ce que nous savons lire : aucun multiple plutôt qu'un multiple au
# hasard. Le cas n'a jamais été observé — raison de plus pour ne pas l'improviser.
check("devise déclarée tierce : aucun multiple",
      screener.per_previsionnel(100.0, _EST, "2025-12-31", (lambda i: 1.2),
                                2.0, "JPY", "USD", "EUR") == [])
# Devise déclarée = devise des comptes, mais change indisponible : on se tait.
check("devise connue, change absent : aucun multiple",
      screener.per_previsionnel(100.0, _EST, "2025-12-31", (lambda i: None),
                                2.0, "EUR", "USD", "EUR") == [])
# LE DÉPARTAGE DE SECOURS, quand la source ne déclare rien. Il ne tranche que si
# le change est loin de 1, et s'abstient sinon. Ces six lignes sont les chiffres
# réels du 09/08/2026 — elles restent le test du repli.
#            prix     BPA est.  taux    BPA publié  attendu
_REELS = [("TCEHY",  61.92,  30.96,  7.10,  24.153, "converti"),
          ("VWS.CO", 178.05,  1.153, 0.134,  0.77,  "converti"),
          ("ASX",     37.39,  1.119, 31.0,  18.74,  "direct"),
          ("ABBN.SW", 81.76,  3.194, 1.25,   2.59,  "trou"),
          ("RACE",   412.26,  9.792, 0.926,  9.01,  "trou"),
          ("CCJ",     97.39,  1.514, 1.37,   1.35,  "trou")]
for _t, _p, _e, _tx, _ep, _att in _REELS:
    _r = screener.per_previsionnel(_p, {"0y": _e, "+1y": _e * 1.08}, "2025-12-31",
                                   (lambda i, _x=_tx: _x), _ep)
    _per = _r[0]["per"] if _r else None
    _got = ("trou" if _per is None
            else "converti" if abs(_per - _p * _tx / _e) < 0.05 else "direct")
    check(f"sans déclaration, {_t} : {_att}", _got == _att, f"obtenu {_got} ({_per})")
# ET LE DÉPARTAGE DE SECOURS SE TROMPE SUR RACE ET CCJ — il s'abstient là où la
# déclaration donne une réponse. C'est la mesure de ce que la colonne apporte, et
# la raison pour laquelle elle passe AVANT : deux trous publiés en moins.
check("la déclaration comble ce que la croissance n'arbitrait pas",
      screener.per_previsionnel(412.26, {"0y": 9.792}, "2025-12-31",
                                (lambda i: 0.926), 9.01) == []
      and screener.per_previsionnel(412.26, {"0y": 9.792}, "2025-12-31",
                                    (lambda i: 0.926), 9.01,
                                    "EUR", "USD", "EUR") != [])

print("\n— Le bénéfice par action reconstitué, et seulement quand il se mesure —")
# QUARANTE-TROIS EXERCICES portent un résultat net publié sans BPA. Le nombre
# d'actions se déduit des voisins qui portent les deux ; s'ils s'accordent, le
# BPA manquant est une division. S'ils divergent, ce serait une invention.
# Chiffres relevés le 09/08/2026 sur les fiches publiées.
_GOOGL = [{"fin": "2013-12-31", "rn": 12920, "eps": 0.95},
          {"fin": "2014-12-31", "rn": 14136, "eps": 1.03},
          {"fin": "2015-12-31", "rn": 16348},
          {"fin": "2016-12-31", "rn": 19478, "eps": 1.40}]
check("un trou encadré par une base stable est comblé",
      screener.completer_eps(_GOOGL) == 1 and _GOOGL[2].get("eps"), str(_GOOGL[2]))
check("et il porte la marque de sa reconstitution",
      _GOOGL[2].get("eps_derive") is True, str(_GOOGL[2]))
check("la valeur reconstituée tient entre celles de ses voisins",
      1.03 < _GOOGL[2]["eps"] < 1.40, str(_GOOGL[2]["eps"]))
# Symbotic : 608, 65 puis 162 millions d'actions impliquées d'un exercice à
# l'autre — le BPA ne porte qu'une classe, le résultat net la société entière.
# Interpoler y aurait produit un multiple faux d'un facteur dix.
_SYM = [{"fin": "2022-09-30", "rn": -140, "eps": -0.23},
        {"fin": "2023-09-30", "rn": -206},
        {"fin": "2024-09-30", "rn": -84, "eps": -0.52}]
check("une base d'actions instable n'est PAS interpolée",
      screener.completer_eps(_SYM) == 0 and "eps" not in _SYM[1], str(_SYM[1]))
# Le bord de série est l'endroit où l'extrapolation ne repose sur rien : c'est
# le cas de 37 des 43 trous, et la règle doit les refuser tous.
_BORD = [{"fin": "2008-12-31", "rn": 100},
         {"fin": "2009-12-31", "rn": 110, "eps": 1.1}]
check("le plus ancien exercice, sans voisin antérieur, reste vide",
      screener.completer_eps(_BORD) == 0 and "eps" not in _BORD[0], str(_BORD[0]))
_FIN = [{"fin": "2024-12-31", "rn": 100, "eps": 1.0}, {"fin": "2025-12-31", "rn": 110}]
check("le dernier exercice non plus, sans voisin postérieur",
      screener.completer_eps(_FIN) == 0 and "eps" not in _FIN[1], str(_FIN[1]))
check("un exercice sans résultat net n'est pas davantage inventé",
      screener.completer_eps([{"fin": "2023-12-31", "rn": 10, "eps": 1.0},
                              {"fin": "2024-12-31"},
                              {"fin": "2025-12-31", "rn": 11, "eps": 1.1}]) == 0)
# UN RÉSULTAT NET À ZÉRO EST UNE ABSENCE, PAS UNE MESURE — et cette règle-là
# manquait au premier jet. Le run du 09/08 a publié un bénéfice par action de
# 0,0 pour Arista 2021 et Viasat 2020, dont la source rend `rn: 0` : c'était
# affirmer qu'Arista n'avait rien gagné en 2021, quand elle a gagné 840 M$.
# Le multiple restait absent, donc le faux ne se voyait que dans le chiffre.
_ZERO = [{"fin": "2019-12-31", "rn": 860, "eps": 0.665},
         {"fin": "2020-12-31", "rn": 635, "eps": 0.5},
         {"fin": "2021-12-31", "rn": 0},
         {"fin": "2022-12-31", "rn": 1352, "eps": 1.0675}]
check("un résultat net à zéro ne donne pas un bénéfice par action à zéro",
      screener.completer_eps(_ZERO) == 0 and "eps" not in _ZERO[2], str(_ZERO[2]))
check("le seuil de stabilité reste serré : une base ne bouge pas de 10 % sans raison",
      screener.ECART_BASE_ACTIONS <= 0.10, str(screener.ECART_BASE_ACTIONS))

print("\n— Le certificat n'est pas toujours l'action —")
# UN ADR REPRÉSENTE PLUSIEURS ACTIONS, et si le cours est celui du certificat
# tandis que le bénéfice est celui de l'action, le multiple est faux d'autant.
# LA MESURE DIT QUE CE N'EST PAS LE CAS ICI : le fournisseur exprime le bénéfice
# par titre coté, comme le cours — ASE publie 18,74 sur sa ligne américaine et
# 8,89 sur celle de Taipei, soit exactement le rapport de son ADR. Ces deux
# lignes-là sont donc le test de la GARDE, pas d'une correction.
# (Chiffres relevés le 09/08/2026 : ASX yearAgoEps 0,571 USD par certificat,
#  3711.TW yearAgoEps 8,89 TWD par action, TSM 10,65 USD, 2330.TW 66,25 TWD.)
check("ASE : le bénéfice publié suit le titre coté, rien à diviser",
      screener.rapport_adr(0.571, 18.74, 31.0, "USD", "USD") == 1)
check("et les deux lignes d'ASE portent bien, elles, un écart de deux",
      abs(0.571 * 31.0 / 8.89 - 2) < 0.12)
check("TSM : cinq actions par certificat entre les deux lignes",
      screener.rapport_adr(10.65, 66.25, 31.8, "USD", "USD") == 5)
check("une valeur sans certificat donne un rapport de 1",
      screener.rapport_adr(2.55, 2.59, 1.0, "USD", "USD") == 1)
# Estimations libellées en devise des comptes : les deux bénéfices parlent déjà
# de la même action, il n'y a pas de rapport à mesurer.
check("devise déclarée = comptes : rapport de 1 sans mesure",
      screener.rapport_adr(None, None, None, "EUR", "USD") == 1.0)
# ET ON S'ABSTIENT SI ÇA NE TOMBE PAS JUSTE. Un rapport à 12 % d'aucune valeur
# usuelle signale qu'une des deux grandeurs n'est pas ce qu'on croit.
check("un rapport de 1,6 ne ressemble à aucun rapport d'ADR",
      screener.rapport_adr(1.6, 1.0, 1.0, "USD", "USD") is None)
check("sans bénéfice de référence, aucun rapport",
      screener.rapport_adr(None, 18.74, 31.0, "USD", "USD") is None
      and screener.rapport_adr(1.21, 0, 31.0, "USD", "USD") is None)
check("sans change, aucun rapport",
      screener.rapport_adr(1.21, 18.74, None, "USD", "USD") is None)
# Le rapport mordu par le PER historique : le multiple d'ASE doit être divisé par
# deux, pas laissé tel quel.
_AN_ADR = [{"fin": "2025-12-31", "eps": 18.74}]
screener.per_historique(_AN_ADR, lambda d: 16.2, False, None,
                        (lambda d: 31.0), 2.0)
check("le PER historique d'un ADR est ramené à l'action ordinaire",
      _AN_ADR[0]["per"] == 13.4, str(_AN_ADR))
_AN_ORD = [{"fin": "2025-12-31", "eps": 18.74}]
screener.per_historique(_AN_ORD, lambda d: 16.2, False, None,
                        (lambda d: 31.0), None)
check("sans rapport mesuré, on ne divise pas — le trou vaut mieux qu'un facteur inventé",
      _AN_ORD[0]["per"] == 26.8, str(_AN_ORD))
# Sans BPA publié positif, rien à quoi comparer — on ne devine pas.
check("sans bénéfice publié, aucun multiple attendu",
      screener.per_previsionnel(60.0, _EST, "2025-12-31", 7.0, None) == [])
check("un bénéfice publié négatif ne sert pas de référence",
      screener.per_previsionnel(60.0, _EST, "2025-12-31", 7.0, -1.2) == [])
# Le cas mono-devise ne doit RIEN changer pour les 95 % de fiches concernées.
check("l'argument taux est optionnel et neutre",
      screener.per_previsionnel(60.0, _EST, "2025-12-31")
      == screener.per_previsionnel(60.0, _EST, "2025-12-31", None, 1.9))
# La bande de croissance est le seul réglage de la règle : elle doit rester
# large, sinon on écarterait des reprises réelles en les prenant pour des
# erreurs de devise.
check("la bande de croissance reste large",
      screener.BANDE_CROISSANCE_BPA[0] <= 1 / 3
      and screener.BANDE_CROISSANCE_BPA[1] >= 3,
      str(screener.BANDE_CROISSANCE_BPA))
# Et la fiche doit DIRE pourquoi les points manquent quand ils manquent.
_ixp = open(os.path.join(RACINE, "index.html"), encoding="utf-8").read()
check("la fiche explique l'absence, et seulement quand elle a lieu",
      "pe_prev_indecis" in _ixp and "également plausibles" in _ixp)

print("\n— Le penny : pourquoi on n'y touche pas —")
# Londres cote en GBp — des pence — quand les comptes sont en GBP, et le rapport
# vaut cent, fixe. La conversion a été ESSAYÉE le 09/08/2026 et retirée le jour
# même : le facteur ne s'applique pas aux mêmes grandeurs partout. Le fournisseur
# cote BAE Systems en pence mais publie sa CAPITALISATION en livres — c'est écrit
# dans validate_tickers.py depuis qu'elle est sortie à 0,8 Md$ le 01/08. Diviser
# cette capitalisation par cent a publié un rendement du flux de 358 % et un PER
# prévisionnel de 0,3 : deux nombres faux là où il n'y avait qu'un trou.
# Ce test fige le retrait, pour que la bonne idée ne revienne pas sans la mesure.
check("GBp reste traité comme GBP tant que chaque grandeur n'est pas mesurée",
      screener.taux_historique("GBp", "GBP") is None
      and screener.taux_historique("GBP", "GBp") is None)
check("deux vraies mêmes devises ne donnent toujours rien",
      screener.taux_historique("USD", "USD") is None)

print("\n— Clôture fiscale : le fantôme, le décalage, et le vrai changement —")
# La règle vivait en DOUBLE, recopiée dans edgar.construire_fonda et dans
# screener.fusionner_fonda. Elle n'a plus qu'une source ; ces tests la visent
# directement, là où elle est écrite.
_filtre = screener.edgar.filtrer_cloture_majoritaire
_dec = [{"fin": f"{a}-12-31", "ca": 100, "rn": 10} for a in range(2016, 2026)]
check("un exercice fantôme isolé est écarté (AMZN, frame CY2026 arrêté en juin)",
      [e["fin"] for e in _filtre(_dec + [{"fin": "2026-06-30", "ca": 50, "rn": 5}])]
      == [e["fin"] for e in _dec])
check("un décalage de calendrier de ±1 mois passe (CDNS : janvier → décembre)",
      len(_filtre(_dec + [{"fin": "2026-01-02", "ca": 100, "rn": 10}])) == len(_dec) + 1)
check("sous trois exercices, la règle ne tranche pas",
      len(_filtre([{"fin": "2024-12-31"}, {"fin": "2025-06-30"}])) == 2)
# LIMITE CONNUE, ET FIGÉE ICI EXPRÈS — tâche #83. Un VRAI changement d'exercice
# fiscal de grande amplitude fait basculer la règle du mauvais côté : L3Harris
# est passée d'une clôture en juin à une clôture en décembre à la fusion de
# 2019. Les dix exercices juin/juillet forment la majorité, donc c'est le
# NOUVEAU régime qui est écarté et la série s'arrête en 2019 — pendant que les
# trimestres vont jusqu'en 2026 et que la marge affichée est celle de
# l'exercice réel. Ce test ne dit pas que c'est bien : il dit que c'est le
# comportement d'aujourd'hui, pour qu'un correctif ait à le regarder en face.
# Le trancher demande de savoir ce que le greffe rend après 2019, et cette
# source est bloquée par le proxy de développement.
_lhx = ([{"fin": f"{a}-06-30", "ca": 5000, "rn": 500} for a in range(2010, 2020)]
        + [{"fin": f"{a}-12-31", "ca": 20000, "rn": 1500} for a in range(2020, 2026)])
_apres = _filtre(_lhx)
check("limite connue (#83) : un changement d'exercice de six mois écarte le "
      "NOUVEAU régime, pas l'ancien",
      len(_apres) == 10 and all(e["fin"][5:7] == "06" for e in _apres),
      f"{len(_apres)} exercices retenus, mois {sorted({e['fin'][5:7] for e in _apres})}")

print("\n— Un exercice contredit par ses propres trimestres —")
# LE CAS RÉEL, chiffres du dépôt tel qu'il a été publié le 17/08/2026 : le
# greffe rend −6 935 M$ pour l'exercice clos le 27/06 quand les trois
# trimestres du même exercice disent +4, +78 et +144. Le trimestre qui reste
# perdrait 7 161 M$ sur 1 006 M$ de ventes. La marge nette de la fiche est
# passée de +17,7 % à −230,1 % en un jour, la note de 31 à 27, et la fiche
# éditoriale a bâti sa thèse dessus.
_LITE_AN = [{"fin": "2023-06-30", "ca": 1767, "rn": -132, "eps": -1.93},
            {"fin": "2024-06-30", "ca": 1359, "rn": -546, "eps": -8.12},
            {"fin": "2025-06-30", "ca": 1645, "rn": 26, "eps": 0.37, "per": 256.9},
            {"fin": "2026-06-27", "src": "edgar", "ca": 3014, "rn": -6935,
             "eps": -92.96}]
_LITE = {"devise": "USD", "an": _LITE_AN,
         "tr": [{"fin": "2025-09-30", "ca": 534, "rn": 4},
                {"fin": "2025-12-31", "ca": 666, "rn": 78},
                {"fin": "2026-03-31", "ca": 808, "rn": 144}]}
_ecartes = screener.ecarter_resultat_contredit(_LITE)
check("le résultat contredit par ses trimestres est écarté",
      len(_ecartes) == 1 and "rn" not in _LITE_AN[3], str(_LITE_AN[3]))
check("le bénéfice par action part avec lui : il portait le même résultat",
      "eps" not in _LITE_AN[3], str(_LITE_AN[3]))
check("le chiffre d'affaires reste : les trimestres le corroborent",
      _LITE_AN[3]["ca"] == 3014, str(_LITE_AN[3]))
check("les deux valeurs refusées restent lisibles dans l'entrée",
      _LITE_AN[3]["ecarte"]["rn"] == -6935
      and _LITE_AN[3]["ecarte"]["eps"] == -92.96, str(_LITE_AN[3].get("ecarte")))
check("le motif nomme le chiffre refusé et ce qui le contredit",
      all(m in _LITE_AN[3]["ecarte"]["motif"]
          for m in ("−6,9 Md$", "+226 M$", "−7,2 Md$")),
      _LITE_AN[3]["ecarte"]["motif"])
check("les exercices antérieurs ne sont pas touchés",
      _LITE_AN[2]["rn"] == 26 and _LITE_AN[1]["rn"] == -546)
check("la règle est idempotente : un exercice déjà écarté ne l'est pas deux fois",
      screener.ecarter_resultat_contredit(_LITE) == [])
# LES DEUX SEUILS SONT EXIGÉS ENSEMBLE, et voici les deux cas qui le prouvent —
# tous deux réels, tous deux publiés aujourd'hui. Applied Digital perd quatre
# fois le chiffre d'affaires de son trimestre résiduel (exercice clos en mai
# 2024) : c'est une petite société qui perd beaucoup, pas une donnée fausse —
# l'ordre de grandeur reste le sien.
_APLD = {"devise": "USD",
         "an": [{"fin": "2023-05-31", "ca": 55, "rn": -45},
                {"fin": "2024-05-31", "ca": 137, "rn": -149},
                {"fin": "2025-05-31", "ca": 144, "rn": -231}],
         "tr": [{"fin": "2023-08-31", "ca": 36, "rn": -11},
                {"fin": "2023-11-30", "ca": 42, "rn": -11},
                {"fin": "2024-02-29", "ca": 43, "rn": -63}]}
check("perdre quatre fois son CA trimestriel ne suffit pas à être écarté",
      screener.ecarter_resultat_contredit(_APLD) == []
      and _APLD["an"][1]["rn"] == -149)
# SanDisk, à l'inverse : son quatrième trimestre pèse trois fois le plus gros
# résultat annuel de son histoire (+6 903 M$), mais il reste très en deçà de
# son propre chiffre d'affaires (8 965 M$). Un trimestre exceptionnel n'est pas
# une donnée fausse.
_SNDK = {"devise": "USD",
         "an": [{"fin": "2024-06-30", "ca": 6663, "rn": -672},
                {"fin": "2025-06-30", "ca": 7355, "rn": -1641},
                {"fin": "2026-07-03", "ca": 20248, "rn": 11433, "eps": 73.76}],
         "tr": [{"fin": "2025-09-30", "ca": 2308, "rn": 112},
                {"fin": "2025-12-31", "ca": 3025, "rn": 803},
                {"fin": "2026-03-31", "ca": 5950, "rn": 3615}]}
check("un trimestre exceptionnel mais proportionné à son CA reste publié",
      screener.ecarter_resultat_contredit(_SNDK) == []
      and _SNDK["an"][2]["rn"] == 11433)
# LE TEST SE TAIT QUAND IL NE PEUT PAS CONCLURE. Une série trimestrielle qui
# couvre déjà tout l'exercice ne laisse aucun trimestre résiduel à mesurer :
# l'écart qu'on lirait alors accuserait la série trimestrielle (échelle fausse,
# SCHW ×1000) autant que l'exercice, et on ne sait pas laquelle.
_COUVERT = {"devise": "USD",
            "an": [{"fin": "2024-12-31", "ca": 100, "rn": 10},
                   {"fin": "2025-12-31", "ca": 300, "rn": 5000}],
            "tr": [{"fin": "2025-03-31", "ca": 100, "rn": 1},
                   {"fin": "2025-06-30", "ca": 100, "rn": 1},
                   {"fin": "2025-09-30", "ca": 100, "rn": 1}]}
check("un exercice déjà couvert par ses trimestres n'est pas jugé",
      screener.ecarter_resultat_contredit(_COUVERT) == []
      and _COUVERT["an"][1]["rn"] == 5000)
check("deux trimestres et demi ne font pas un exercice : rien n'est écarté",
      screener.ecarter_resultat_contredit(
          {"devise": "USD",
           "an": [{"fin": "2024-12-31", "ca": 100, "rn": 10},
                  {"fin": "2025-12-31", "ca": 400, "rn": -9000}],
           "tr": [{"fin": "2025-03-31", "ca": 100, "rn": 1},
                  {"fin": "2025-06-30", "ca": 100, "rn": 1}]}) == [])
# Les seuils sont MESURÉS puis FIGÉS : les desserrer sans mesurer à nouveau
# ferait rentrer les 118 autres exercices testables un à un.
check("les deux seuils restent ceux qui ont été mesurés",
      (screener.RESIDU_SUR_CA, screener.RESIDU_SUR_HISTORIQUE) == (3, 10),
      f"{screener.RESIDU_SUR_CA} / {screener.RESIDU_SUR_HISTORIQUE}")
# LA RÈGLE EST REJOUÉE À LA FUSION. Sans ça, l'exercice écarté aujourd'hui
# ressusciterait le jour où le run courant ne le produit plus (EDGAR muet) :
# l'ancienne entrée, elle, porte encore son résultat.
_ANCIEN = {"devise": "USD",
           "an": [{"fin": "2025-06-30", "ca": 1645, "rn": 26},
                  {"fin": "2026-06-27", "ca": 3014, "rn": -6935, "eps": -92.96}],
           "tr": [{"fin": "2025-09-30", "ca": 534, "rn": 4},
                  {"fin": "2025-12-31", "ca": 666, "rn": 78},
                  {"fin": "2026-03-31", "ca": 808, "rn": 144}]}
_fus = screener.fusionner_fonda(copy.deepcopy(_ANCIEN), {"devise": "USD", "an": [],
                                                         "tr": []})
check("un exercice écarté ne ressuscite pas par la fusion",
      "rn" not in _fus["an"][-1] and _fus["an"][-1].get("ecarte"),
      str(_fus["an"][-1]))

print("\n— La fusion ne perd rien de ce qui est déjà publié —")
# LA PANNE DU 07/08, ÉPROUVÉE SUR LES DONNÉES RÉELLES. `fusionner_fonda`
# reconstruit le bloc de zéro : tout champ qu'elle ne recopie pas explicitement
# disparaît à la publication. `proj` en a fait les frais — 96 fiches sur 97
# publiées sans trajectoire, seule celle créée ce jour-là (donc sans ancien à
# fusionner) en portait une. Le commentaire de la fonction prévient depuis ;
# un commentaire ne s'exécute pas.
#
# LA GARDE EST COMPORTEMENTALE, PAS SYNTAXIQUE. On rejoue la fusion sur chaque
# bloc RÉELLEMENT publié, en le passant comme ancien ET comme nouveau : ce que
# le run courant produit doit ressortir intact. Lire la fonction à l'analyse
# syntaxique aurait demandé de résoudre `out[cle]` dans une boucle — une garde
# qui devine le code rend un vert qui ne prouve rien.
#
# ET CE N'EST PAS UN DOUBLON du garde-fou générique plus haut. Celui-là éprouve
# un bloc ÉCRIT À LA MAIN contre une liste `CHAMPS` elle aussi écrite à la main :
# il prouve que la fusion conserve les champs dont quelqu'un s'est souvenu. Le
# jour où un champ apparaît dans les données publiées sans que cette liste soit
# mise à jour, il reste vert pendant que le champ se perd. Ici les deux côtés
# viennent du dépôt : c'est la moitié que la liste recopiée ne peut pas couvrir.
_blocs = {}
for _p in sorted(glob.glob(os.path.join(RACINE, "charts", "*.json"))):
    try:
        _f = json.load(open(_p, encoding="utf-8")).get("fonda")
    except Exception:                                        # noqa: BLE001
        continue
    if isinstance(_f, dict) and _f:
        _blocs[os.path.basename(_p)[:-5]] = _f

check("des blocs fonda publiés à éprouver", len(_blocs) > 0, f"{len(_blocs)} bloc(s)")
_perdants = {}
for _t, _bloc in _blocs.items():
    _out = screener.fusionner_fonda(copy.deepcopy(_bloc), copy.deepcopy(_bloc)) or {}
    _manque = sorted(set(_bloc) - set(_out))
    if _manque:
        _perdants[_t] = _manque
check("aucun champ d'un bloc publié ne disparaît à la fusion",
      not _perdants,
      f"{len(_perdants)} fiche(s) — " + ", ".join(f"{t}:{k}" for t, k in
                                                  list(_perdants.items())[:5]))

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
