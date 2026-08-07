#!/usr/bin/env python3
"""Le bandeau et le pied de page sont-ils LE MÊME objet sur les quatre onglets ?

POURQUOI CE FICHIER EXISTE. signal.css s'ouvre sur « une seule source de
vérité ». Ce n'était pas vrai. Mesuré au navigateur le 07/08/2026, sur les
quatre onglets d'un site qui n'en a que quatre :

  · le logo faisait 28 px sur Watchlists et 30 px partout ailleurs ;
  · le nom de la marque 1,3 rem ici, 1,4 rem là ;
  · le bandeau donc 64 px, 69 px ou 72 px selon l'onglet — il sautait à chaque
    changement de page ;
  · les liens de navigation tombaient à 10,6 px et 12 px de haut sur deux
    onglets (28 px sur les deux autres) : sur mobile, une cible intouchable ;
  · Actualités déclarait font-family:'Inter' sans jamais charger la police, et
    n'avait ni pied de page normalisé ni badge « Bêta » ;
  · trois onglets sur quatre n'avaient pas de favicon.

Aucun de ces défauts n'était visible sur une page prise seule : ils ne se
voient qu'en COMPARANT. C'est exactement ce que fait ce fichier, sur le texte
des fichiers, sans navigateur — la règle étant qu'une page ne redéfinit pas ce
que le design system définit déjà.

    python tests/test_chrome.py
"""
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RACINE)

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


PAGES = ["index.html", "actualites.html", "apprendre.html", "portfolio.html"]
SRC = {p: open(p, encoding="utf-8").read() for p in PAGES}
CSS = open("signal.css", encoding="utf-8").read()

print(f"— {len(PAGES)} onglets lus —")

# ── 1. AUCUNE PAGE NE REDÉFINIT LE CHROME PARTAGÉ ──────────────────────────
# Le test porte sur les sélecteurs NUS du design system. Une page garde le
# droit de styler ses propres composants (.pos-header, .sec-tete…) : seul le
# chrome commun est verrouillé. `header{position:…}` reste permis — une page
# qui défile a besoin de sticky là où une vue en SPA veut fixed — donc on ne
# refuse que les propriétés de FORME.
print("\n— Le chrome partagé est-il redéfini quelque part ? —")
INTERDITS = [
    (r"\.brand-name\s*\{", ".brand-name"),
    (r"\.brand\s*\{", ".brand"),
    (r"\.brand-icon\s*\{", ".brand-icon"),
    (r"(?<![\w.\-])nav\s*\{", "nav"),
    (r"(?<![\w.\-])nav\s+a\s*\{", "nav a"),
    (r"\.footer-legal\s*\{", ".footer-legal"),
    (r"\.footer-right\s*\{", ".footer-right"),
]
for motif, lib in INTERDITS:
    coupables = [p for p in PAGES if re.search(motif, SRC[p])]
    check(f"« {lib} » n'est défini que dans signal.css",
          not coupables, str(coupables))

# ── 2. CE QUE CHAQUE ONGLET DOIT PORTER ────────────────────────────────────
print("\n— Chaque onglet porte-t-il le même attirail ? —")
ATTENDUS = [
    ('rel="icon"', "un favicon"),
    ('class="footer-legal"', "la mention légale dans .footer-legal"),
    ('class="footer-right"', "le badge de droite du pied de page"),
    ('rel="stylesheet" href="signal.css"', "signal.css"),
    ("signal-fx.js", "signal-fx.js"),
    ('name="description"', "une meta description"),
    ("fonts.googleapis.com/css2", "la police Inter chargée"),
]
for motif, lib in ATTENDUS:
    manquants = [p for p in PAGES if motif not in SRC[p]]
    check(f"{lib} : présent sur les 4 onglets", not manquants, str(manquants))

# Une page qui déclare Inter sans la charger tombe en police système : c'était
# le cas d'Actualités, et rien ne le signalait.
declare = [p for p in PAGES if "'Inter'" in SRC[p] or '"Inter"' in SRC[p]]
charge = [p for p in PAGES if "family=Inter" in SRC[p]]
check("aucune page ne déclare Inter sans la charger",
      not set(declare) - set(charge), str(sorted(set(declare) - set(charge))))

# Le faux gras et le faux italique fabriqués par le navigateur ne ressemblent
# pas aux vraies graisses : la même requête de police partout, ou rien.
requetes = {re.search(r"family=Inter[^\"']*", SRC[p]).group(0)
            for p in PAGES if "family=Inter" in SRC[p]}
check("la même requête de police sur tous les onglets",
      len(requetes) <= 1, str(sorted(requetes)))

# ── 3. LA NAVIGATION : MÊME ORDRE, MÊMES CIBLES, UN SEUL ACTIF ─────────────
print("\n— La navigation dit-elle la même chose partout ? —")
navs = {}
for p in PAGES:
    bloc = re.search(r"<nav>(.*?)</nav>", SRC[p], re.S)
    liens = re.findall(r'href="([^"]+)"[^>]*>([^<]+)<', bloc.group(1)) if bloc else []
    navs[p] = liens
check("les 4 onglets ont une nav", all(navs[p] for p in PAGES),
      str([p for p in PAGES if not navs[p]]))
ordres = {tuple(l for l, _ in v) for v in navs.values()}
check("même ordre de liens partout", len(ordres) == 1, str(sorted(ordres)))
libelles = {tuple(t.strip() for _, t in v) for v in navs.values()}
check("mêmes libellés partout", len(libelles) == 1, str(sorted(libelles)))
check("« Portefeuille IA » est la dernière entrée",
      all(v and v[-1][1].strip() == "Portefeuille IA" for v in navs.values()),
      str({p: v[-1][1] for p, v in navs.items() if v}))
for p in PAGES:
    bloc = re.search(r"<nav>(.*?)</nav>", SRC[p], re.S).group(1)
    check(f"{p} : exactement un lien actif", bloc.count('class="active"') == 1)

# ── 4. LE PIED DE PAGE DIT LA MÊME CHOSE ───────────────────────────────────
print("\n— Le pied de page est-il le même texte partout ? —")
legals = {re.search(r'class="footer-legal">(.*?)</div>', SRC[p], re.S).group(1).strip()
          for p in PAGES if 'class="footer-legal"' in SRC[p]}
check("une seule mention légale, mot pour mot", len(legals) == 1,
      f"{len(legals)} variantes")

# ── 5. LE PLANCHER DE LISIBILITÉ ───────────────────────────────────────────
# 10,56 px pour la navigation principale (.66rem) : c'était le réglage sous
# 400 px. La police descend, jamais le rembourrage — c'est lui la cible.
print("\n— Le plancher de lisibilité de la nav tient-il ? —")
tailles = [float(m) for m in re.findall(r"nav a\{font-size:\.(\d+)rem", CSS)]
tailles += [float(m) for m in re.findall(r"nav a\{[^}]*font-size:\.(\d+)rem", CSS)]
check("aucune taille de nav sous .72rem dans signal.css",
      all(t >= 72 for t in tailles), str(tailles))
check("les liens de nav gardent un rembourrage à chaque palier",
      len(re.findall(r"nav a\{[^}]*padding:", CSS)) >= 3,
      str(len(re.findall(r"nav a\{[^}]*padding:", CSS))))

# ── 6. LES RÈGLES RECOPIÉES ENTRE PYTHON ET JAVASCRIPT ─────────────────────
# La fiche tronque une série de chiffre d'affaires à sa dernière marche
# descendante, exactement comme `note_v4.apres_rupture` le fait pour la note.
# Deux implémentations de la même règle, dans deux langages : c'est le genre de
# doublon qui dérive en silence, et le jour où il dérive la fiche note une
# trajectoire et en dessine une autre — c'était précisément le bug d'Adyen.
print("\n— Le seuil de rupture est-il le même des deux côtés ? —")
NOTE = open("note_v4.py", encoding="utf-8").read()
py = re.search(r"RUPTURE_PERIMETRE\s*=\s*(\S+(?:\s*/\s*\S+)?)", NOTE)
js = re.search(r"FD_RUPTURE\s*=\s*(\S+?);", SRC["index.html"])
check("les deux constantes existent", bool(py and js),
      f"python={bool(py)} js={bool(js)}")
if py and js:
    check("même seuil de rupture de périmètre (note_v4 ↔ fiche)",
          abs(eval(py.group(1)) - eval(js.group(1))) < 1e-9,
          f"python={py.group(1)} js={js.group(1)}")

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
