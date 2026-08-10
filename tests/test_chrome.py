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
    (r"(?<![\w.\-])nav\s+a\s+svg\s*\{", "nav a svg"),
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
    # Le libellé vit dans un <span> depuis que chaque onglet porte un
    # pictogramme : l'ancien motif « le texte suit immédiatement le > » ne
    # trouvait plus rien, et un test qui ne trouve rien ne dit plus rien.
    liens = re.findall(r'href="([^"]+)"[^>]*>.*?<span>([^<]+)</span>',
                       bloc.group(1), re.S) if bloc else []
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

# ── 3 bis. LES PICTOGRAMMES ────────────────────────────────────────────────
# Ils ont été ajoutés le 08/08 au-dessus de chaque libellé. Trois choses
# peuvent se casser en silence : un onglet oublié lors d'une reprise de la
# barre, une icône qui cesse de suivre la couleur de son onglet (un `fill`
# codé en dur au lieu de `currentColor`), et un SVG annoncé aux lecteurs
# d'écran, qui liraient « image » à la place du nom de la section.
print("\n— Les pictogrammes de la nav —")
navsvg = {p: re.search(r"<nav>(.*?)</nav>", SRC[p], re.S).group(1) for p in PAGES}
check("les quatre onglets ont chacun leur pictogramme",
      all(v.count("<svg") == 4 for v in navsvg.values()),
      str({p: v.count("<svg") for p, v in navsvg.items()}))
check("chaque pictogramme est masqué aux lecteurs d'écran",
      all(v.count('aria-hidden="true"') == 4 for v in navsvg.values()),
      str({p: v.count('aria-hidden="true"') for p, v in navsvg.items()}))
check("les mêmes quatre pictogrammes sur les quatre onglets",
      len({tuple(re.findall(r'<svg[^>]*>(.*?)</svg>', v, re.S))
           for v in navsvg.values()}) == 1)
check("aucun pictogramme ne fige sa couleur dans le balisage",
      not any(re.search(r"<svg[^>]*>.*?(?:fill=\"#|stroke=\"#)", v, re.S)
              for v in navsvg.values()))
check("la couleur vient de currentColor, dans signal.css",
      "nav a svg{" in CSS and "stroke:currentColor" in CSS)
# L'EN-TÊTE EST FIXE ET DES RÉGLAGES EN DÉPENDENT. `.rail` et `.stage` se
# posent juste dessous dans index.html, les ancres se calent sur lui dans
# signal.css. Les pictogrammes l'ont fait passer de 72 à 81 px (16 px au
# premier jet, 19 px après retour du propriétaire) : ces quatre valeurs ont
# suivi, et elles doivent rester au-dessus de la hauteur mesurée.
check("les décalages sous l'en-tête suivent sa hauteur (81 px mesurés)",
      all(v in SRC["index.html"] for v in ("top:5.6rem", "top:5.7rem"))
      and "scroll-margin-top:6.1rem" in CSS)
# ET CE CONTRÔLE NE REGARDAIT QU'UNE PAGE. signal.css pose `header{position:
# fixed}` : un en-tête fixe ne prend AUCUNE place dans le flux, donc une page
# qui empile son contenu dans un <main> démarre au ras de la fenêtre et passe
# SOUS l'en-tête. index.html vit très bien avec, mais parce qu'il compense
# explicitement (les `top:5.6rem`/`5.7rem` ci-dessus) ; les pages qui défilent,
# elles, repassent l'en-tête en `sticky` pour qu'il occupe sa place.
#
# actualites.html avait le `html,body{height:auto}` qui accompagne le sticky
# mais PAS le sticky : le motif avait été recopié à moitié, et son texte
# commençait 33 px trop haut — 48 px de `padding` sous un en-tête de 81. Seule
# des quatre, et rien ne le disait.
_sans_place = [p for p in PAGES if "<main" in SRC[p]
               and not re.search(r"header\s*\{[^}]*position:\s*sticky", SRC[p])]
check("une page qui pose son contenu dans <main> donne sa place à l'en-tête",
      not _sans_place,
      f"{_sans_place} : en-tête fixe sans compensation, le texte passe dessous")

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


# ── LE SCRIPT DE CHAQUE PAGE SE PARSE-T-IL ? ────────────────────────────────
# LE 09/08/2026, UNE ERREUR DE SYNTAXE EST PARTIE EN PRODUCTION. Une phrase
# insérée dans un ternaire imbriqué y a laissé un « :'') » en double ; le script
# entier ne se parsait plus et AUCUNE page ne rendait — bandeau et pied de page
# seuls. Les 36 vérifications de ce fichier étaient au vert, parce qu'elles
# comparent des TEXTES de fichiers et n'exécutent jamais rien.
#
# C'est le mode de panne le plus grave possible sur un site statique : total,
# instantané, et invisible à tout contrôle qui ne fait que lire. Une seule
# ligne de test le rend impossible — on donne le script à un analyseur.
print("\n— Les scripts inline se parsent-ils ? —")
try:
    import subprocess, tempfile                                    # noqa: E402
    for page in ("index.html", "actualites.html", "portfolio.html", "apprendre.html"):
        chemin = os.path.join(RACINE, page)
        if not os.path.exists(chemin):
            continue
        html = open(chemin, encoding="utf-8").read()
        # Les scripts de type non-JS (JSON-LD par exemple) ne se parsent pas
        # comme du JavaScript : on ne prend que les blocs sans `type` ou
        # explicitement JavaScript.
        blocs = re.findall(r"<script(?![^>]*\btype\s*=\s*[\"\']application/ld\+json)"
                           r"(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", html, re.S | re.I)
        mauvais = []
        for i, code in enumerate(blocs):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            os.unlink(tmp)
            if r.returncode != 0:
                premiere = [l for l in r.stderr.splitlines() if l.strip()][:3]
                mauvais.append(f"bloc {i} : " + " / ".join(premiere))
        check(f"{page} — {len(blocs)} bloc(s) de script se parsent",
              not mauvais, " ;; ".join(mauvais)[:400])
except (OSError, subprocess.SubprocessError) as _e:
    print(f"  \u26a0\ufe0f  syntaxe JS non vérifiée (node indisponible : {type(_e).__name__})")

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
