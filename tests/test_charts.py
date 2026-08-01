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

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
