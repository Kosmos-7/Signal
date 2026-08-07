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
# Base d'actions : un cours ajusté des splits vit dans la base d'AUJOURD'HUI.
# Un BPA « tel que publié » (fenêtre Yahoo) antérieur à un split vit dans celle
# de son époque — leur quotient est faux du facteur du split.
SPL = [("2024-06-10", 10.0)]
an4 = [{"fin": "2023-12-31", "eps": 20.0}, {"fin": "2025-12-31", "eps": 3.0}]
screener.per_historique(an4, lambda d: 120.0, True, SPL)
check("BPA Yahoo antérieur à un split : retiré, pas approximé",
      "per" not in an4[0] and an4[1]["per"] == 40.0, str(an4))
an5 = [{"fin": "2023-12-31", "eps": 2.0, "src": "edgar"}]
screener.per_historique(an5, lambda d: 120.0, True, SPL)
check("BPA EDGAR déjà ramené à la base actuelle : le PER est calculé",
      an5[0]["per"] == 60.0, str(an5))
an6 = [{"fin": "2023-12-31", "eps": 20.0}]
screener.per_historique(an6, lambda d: 120.0, True, None)
check("sans split connu, rien n'est retiré", an6[0]["per"] == 6.0)

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
# Garde-fou générique : tout champ de `fonda` que la fusion ignore disparaît.
# Ce test échouera dès qu'un nouveau champ sera ajouté sans être traité ici.
CHAMPS = {"devise", "an", "tr", "pe_prev", "proj"}
plein = {"devise": "USD", "an": [{"fin": "2025-12-31", "ca": 1}], "tr": [],
         "pe_prev": [{"exercice": 2026, "per": 30.0}], "proj": PJ}
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
# Plafond : une croissance forte mais prolongeable (35 %/an) est bridée, pas refusée
AN_HYPER = [{"fin": f"{y}-12-31", "ca": c} for y, c in
            [(2022, 120), (2023, 160), (2024, 215), (2025, 290)]]
ph = screener.projections(AN_HYPER, None, {"0y": 390, "+1y": 525}, "2025-12-31")
g1 = (ph[2]["ca"] / ph[1]["ca"] - 1) * 100
check("croissance forte : le 1er pas extrapolé est bridé sous le plafond",
      g1 <= screener.PLAFOND_EXTRAPOLATION + 0.1, f"{g1:.1f} %")
check("le consensus, lui, n'est PAS bridé (525 conservé)", ph[1]["ca"] == 525)
# Un BPA en perte ne se prolonge pas — courbe qui ne veut rien dire (cas Nebius)
AN_PERTE = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
            [(2023, 100, -1.0), (2024, 150, -2.0), (2025, 220, -0.5)]]
pp = screener.projections(AN_PERTE, {"0y": -0.2, "+1y": 0.1}, {"0y": 300, "+1y": 400},
                          "2025-12-31")
check("BPA négatif : le chiffre d'affaires se projette, pas le bénéfice",
      all("eps" not in e for e in pp) and all("ca" in e for e in pp), str(pp[:2]))
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

# ── Le cône : deux branches quand l'avenir est incertain mais prolongeable ──
# Leçon du 06/08 (signalée par le propriétaire) : une branche unique plafonnée
# à 25 % écrasait une croissance forte sous un a priori de croissance ORGANIQUE.
# On ne tranche plus dans ce domaine : on publie les deux branches, l'écart
# mesurant notre ignorance.
cn = screener.projections(AN_HYPER, None, {"0y": 390, "+1y": 525}, "2025-12-31")
check("le consensus ne porte JAMAIS de borne haute (ce n'est pas une opinion à nous)",
      all("ca_haut" not in e for e in cn if e["nature"] == "consensus"))
check("les années extrapolées portent une fourchette",
      all("ca_haut" in e for e in cn if e["nature"] == "extrapolé"))
check("la borne haute est au-dessus de la prudente",
      all(e["ca_haut"] > e["ca"] for e in cn if e["nature"] == "extrapolé"))
g_h = (cn[-1]["ca_haut"] / cn[-2]["ca_haut"] - 1) * 100
check("la branche haute décélère aussi vers le taux terminal",
      g_h < screener.SEUIL_REFUS, f"{g_h:.1f} %")
# Sur un compounder régulier, les deux branches coïncident : pas de bruit
REGULIER = [{"fin": f"{y}-12-31", "ca": c} for y, c in
            [(2021, 168), (2022, 198), (2023, 212), (2024, 245), (2025, 282)]]
cr = screener.projections(REGULIER, None, {"0y": 315, "+1y": 352}, "2025-12-31")
check("compounder régulier : aucune fourchette publiée, les branches coïncident",
      all("ca_haut" not in e for e in cr), str(cr[-1]))

# ── Le refus de prolonger : une projection qu'on sait fausse ne s'affiche pas ─
# Leçon du 07/08 (signalée par le propriétaire, sur Nebius) : au-delà d'un
# certain rythme, les DEUX bornes du cône sont fausses — plafonner donnait
# 18 Md$ en 2030 quand le marché en discute 33 à 46, ne pas plafonner donnait
# 140 Md$. Élargir le cône n'est pas une réponse : on s'arrête, avec le motif.
CONTRACTE = [{"fin": f"{y}-12-31", "ca": c} for y, c in
             [(2022, 14), (2023, 10), (2024, 92), (2025, 530)]]
nb = screener.projections(CONTRACTE, None, {"0y": 3500, "+1y": 9000}, "2025-12-31")
check("hypercroissance : SEULS les deux exercices de consensus sortent",
      [e["exercice"] for e in nb] == [2026, 2027], str(nb))
check("et ils sont bien étiquetés consensus, repris tels quels",
      [e["nature"] for e in nb] == ["consensus"] * 2
      and [e["ca"] for e in nb] == [3500, 9000], str(nb))
check("aucune borne haute inventée quand on refuse de prolonger",
      all("ca_haut" not in e for e in nb))
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
check("une société sans consensus et en hypercroissance démontrée ne dit rien",
      screener.projections(CONTRACTE, None, None, "2025-12-31") == [])
# Le piège des ADR : le CA estimé est publié en devise COMPTABLE, le BPA estimé
# en devise de COTATION. TSM publiait 331,25 TWD de BPA et nous en projetions
# 16,82 — le « taux de croissance » n'était qu'un taux de change.
ADR = [{"fin": f"{y}-12-31", "ca": c, "eps": e} for y, c, e in
       [(2023, 2161736, 176.0), (2024, 2894308, 226.25), (2025, 3809054, 331.25)]]
adr = screener.projections(ADR, {"0y": 16.8, "+1y": 21.6},
                           {"0y": 5420352, "+1y": 7187439}, "2025-12-31",
                           meme_devise=False)
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

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
