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
    ("fonts.googleapis.com/css2", "les polices du design system chargées"),
]
for motif, lib in ATTENDUS:
    manquants = [p for p in PAGES if motif not in SRC[p]]
    check(f"{lib} : présent sur les 4 onglets", not manquants, str(manquants))

# LES DEUX FAMILLES DU DESIGN SYSTEM SONT CHARGÉES PARTOUT. Une page qui
# déclare une police sans la charger tombe en police système : c'était le cas
# d'Actualités, et rien ne le signalait.
FAMILLES = [("family=Outfit", "Outfit"), ("Google+Sans+Code", "Google Sans Code")]
for motif, lib in FAMILLES:
    manquants = [p for p in PAGES if motif not in SRC[p]]
    check(f"{lib} : chargée sur les 4 onglets", not manquants, str(manquants))

# Le faux gras et le faux italique fabriqués par le navigateur ne ressemblent
# pas aux vraies graisses : la même requête de police partout, ou rien. Le
# motif ne cite plus une famille en particulier — il compare la requête ENTIÈRE,
# et survit donc au prochain changement de police.
requetes = {re.search(r"css2\?[^\"']*", SRC[p]).group(0)
            for p in PAGES if "fonts.googleapis.com/css2" in SRC[p]}
check("la même requête de police sur tous les onglets",
      len(requetes) == 1, str(sorted(requetes)))

# AUCUNE PAGE NE FIGE UNE POLICE EN DUR. Les familles ne sont nommées qu'une
# fois, dans les tokens de signal.css (--sans / --serif / --mono) ; une page qui
# réécrit « Georgia » ou « Courier New » ne suivra pas le prochain changement,
# et c'est exactement ainsi que le site s'est retrouvé avec quatre typographies
# légèrement différentes avant le 15/08/2026.
for nom in ("Courier New", "Georgia", "'Inter'"):
    coupables = [p for p in PAGES if nom in SRC[p]]
    check(f"aucune page ne fige « {nom} » en dur", not coupables, str(coupables))

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

# ── LE MÊME ÉCART ENTRE L'EN-TÊTE ET LE PREMIER TITRE, SUR LES QUATRE PAGES ───
# Mesuré au navigateur le 10/08/2026 : « Watchlists » se posait 25 px sous
# l'en-tête, « Une IA contre l'indice » 40, « Actualités » 48, « Comprendre la
# bourse » 56. Quatre valeurs pour un réglage qui n'a qu'une raison d'être.
# L'origine n'était pas un désaccord de conception mais deux passes « plus d'air »
# ayant choisi chacune leur nombre (2,5rem ici, 3,5rem là) par-dessus le 3rem que
# les trois pages déclarent pourtant en base.
#
# LE TEST EST STATIQUE ET IL LE DIT : le runner n'a pas de navigateur, donc on
# vérifie la VALEUR DÉCLARÉE, pas la distance rendue. C'est un filet contre la
# régression d'écriture (« remettons 2,5rem ici »), pas une preuve de rendu —
# celle-là se refait au navigateur, et elle l'a été.
ECART = "3rem"      # 48 px sous un en-tête de 81 px


def _padding_haut_effectif(source):
    """Dernier `padding-top` de `main` déclaré HORS media query. Rend None si aucun.

    LA PREMIÈRE VERSION DE CE TEST NE POUVAIT PAS ROUGIR, et l'a prouvé : elle
    ramassait toutes les valeurs de tous les blocs `main{}` et se contentait d'y
    trouver « 3rem ». Or la règle de base en déclare toujours un — le test restait
    vert avec une surcharge à 2,5rem juste en dessous. Il faut la valeur EFFECTIVE,
    donc la dernière au niveau racine : celle que la cascade retient sur grand
    écran. Les surcharges mobiles, elles, vivent dans un @media et sont un réglage
    distinct, assumé."""
    style = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", source, re.S))
    profondeur, i, dernier, n = 0, 0, None, len(style)
    while i < n:
        c = style[i]
        if c == "{":
            # sélecteur = ce qui précède, depuis le dernier délimiteur de règle
            debut = max(style.rfind("}", 0, i), style.rfind("{", 0, i)) + 1
            sel = style[debut:i].strip().split("\n")[-1].strip()
            fin = style.find("}", i)
            if profondeur == 0 and re.fullmatch(r"main", sel) and fin != -1:
                corps = style[i + 1:fin]
                m = re.search(r"padding-top:\s*([0-9.]+rem)", corps) or \
                    re.search(r"padding:\s*([0-9.]+rem)", corps)
                if m:
                    dernier = m.group(1)
            profondeur += 1
        elif c == "}":
            profondeur -= 1
        i += 1
    return dernier


for _p in ("actualites.html", "portfolio.html", "apprendre.html"):
    _eff = _padding_haut_effectif(SRC[_p])
    check(f"{_p} : l'écart au titre reste {ECART}", _eff == ECART, f"effectif : {_eff}")
# index.html n'a pas de <main> : son écart vient d'une chaîne de trois boîtes, et
# son en-tête étant `fixed` à toutes les largeurs, le dégagement doit être REPOSÉ
# à chaque hauteur d'en-tête — 81 px au-dessus de 700, 69 px en dessous, où
# signal.css resserre le rembourrage. Sans le second, l'écart passait de 48 à 54.
check("index.html : le rembourrage du titre d'accueil vaut le complément mesuré",
      ".home-h{padding:1.875rem 0 0}" in SRC["index.html"])
check("index.html : le dégagement mobile suit les DEUX hauteurs d'en-tête",
      "margin-top:91px" in SRC["index.html"] and "margin-top:79px" in SRC["index.html"],
      "91px = 81+48−38 ; 79px = 69+48−38")
check("et le resserrage de l'en-tête est bien à 700 px dans la feuille partagée",
      re.search(r"@media\(max-width:700px\)\{\s*header\{padding:", CSS) is not None)

# ── 3 ter. LE SITE VOUVOIE, PARTOUT ────────────────────────────────────────
# Décision du propriétaire (15/08/2026). L'accueil disait « les opportunités
# qui vous ressemblent » pendant qu'Apprendre tutoyait sur trente-neuf
# passages — deux voix pour un seul site, et personne ne l'avait vu parce que
# ça ne se remarque qu'en passant d'un onglet à l'autre. Trente-neuf tournures
# ont été reprises ; ce test empêche la quarantième.
#
# DEUX EXCEPTIONS LÉGITIMES, et elles sont nommées plutôt que devinées :
# le `ton:` d'index.html est une CLÉ JavaScript (le palier de lecture d'un
# score), et portfolio.html CITE mot pour mot le prompt envoyé à l'IA dans sa
# section Transparence — le corriger falsifierait la citation. Les prompts
# eux-mêmes (generate_analyses.py, portfolio_agent.py) tutoient le modèle et
# non le lecteur : ils ne sont pas dans le périmètre.
print("\n— Le site vouvoie-t-il partout ? —")
_EXCEPTIONS = [
    "ton:'bas'", "ton:'moyen'", "ton:'haut'", "p.ton",          # clés JS
    "Historique de tes décisions",                              # prompt cité
    "Évite de racheter un titre que tu viens de vendre",        # prompt cité
]
_TU = re.compile(r"(?<![\w'’-])(tu|ton|ta|tes|toi)(?![\w'’-])", re.I)
for p in PAGES:
    texte = SRC[p]
    for exc in _EXCEPTIONS:
        texte = texte.replace(exc, "")
    trouve = [m.group(0) for m in _TU.finditer(texte)]
    check(f"{p} : aucun tutoiement", not trouve, str(sorted(set(trouve))))

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

# ── « CHIFFRES PUBLIÉS » S'OUVRE SUR L'ANNÉE EN COURS ───────────────────────
# La colonne de repos valait toujours la dernière : en vue annuelle, la fiche
# s'ouvrait donc sur 2030, la prolongation la plus lointaine et la moins sûre.
#
# LE TEST EXÉCUTE LE CODE LIVRÉ, il ne le relit pas. Le bloc est extrait
# d'index.html et rejoué dans node sur des colonnes fabriquées — la règle est
# une fonction pure de (colonnes, mode, année), donc elle se teste vraiment.
# Un test qui aurait cherché « new Date().getFullYear() » dans le fichier aurait
# été vert avec un décalage d'un cran dans la boucle.
#
# LES CAS SONT CONSTRUITS À PARTIR DE L'ANNÉE COURANTE, jamais d'un millésime
# écrit en dur : sinon ce test tomberait tout seul au 1er janvier prochain.
print("\n— La section « Chiffres publiés » s'ouvre-t-elle sur l'année en cours ? —")
_m = re.search(r"let fdRepos=cols\.length-1;.*?(?=\n\s*releveSvg\()",
               SRC["index.html"], re.S)
check("le calcul de la colonne de repos est extractible", _m is not None)
if _m:
    _CAS = [
        ("l'année en cours est une PROJECTION", "an",
         "[{v:{fin:(A-2)+'-12-31'}},{v:{fin:(A-1)+'-12-31'}},"
         "{v:{exercice:''+A},pr:1},{v:{exercice:''+(A+1)},pr:1}]", 2),
        ("l'année en cours est DÉJÀ PUBLIÉE", "an",
         "[{v:{fin:(A-1)+'-12-31'}},{v:{fin:A+'-06-30'}},{v:{exercice:''+(A+1)},pr:1}]", 1),
        ("deux exercices clos la même année : le plus récent", "an",
         "[{v:{fin:A+'-01-03'}},{v:{fin:A+'-12-31'}},{v:{exercice:''+(A+1)},pr:1}]", 1),
        ("aucune colonne pour l'année en cours : repli sur la dernière", "an",
         "[{v:{fin:(A-3)+'-12-31'}},{v:{fin:(A-2)+'-12-31'}}]", 1),
        ("en trimestriel, le dernier trimestre reste le repère", "tr",
         "[{v:{fin:A+'-03-31'}},{v:{fin:A+'-06-30'}},{v:{fin:A+'-09-30'}}]", 2),
    ]
    try:
        import subprocess, tempfile                                # noqa: E402
        for _nom, _mode, _cols, _attendu in _CAS:
            _js = (f"const A=new Date().getFullYear();const FD_MODE={_mode!r};"
                   f"const cols={_cols};\n{_m.group(0)}\nconsole.log(fdRepos);")
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                             encoding="utf-8") as _f:
                _f.write(_js)
                _tmp = _f.name
            _r = subprocess.run(["node", _tmp], capture_output=True, text=True)
            os.unlink(_tmp)
            _got = _r.stdout.strip()
            check(_nom, _got == str(_attendu),
                  f"obtenu {_got or _r.stderr.strip()[:80]!r}, attendu {_attendu}")
    except (OSError, subprocess.SubprocessError) as _e:
        print(f"  ⚠️  colonne de repos non vérifiée (node indisponible : {type(_e).__name__})")
# Et le relevé doit accepter cette colonne : sans le paramètre, le calcul
# ci-dessus serait mort-né.
check("le relevé reçoit bien la colonne de repos",
      re.search(r"function releveSvg\([^)]*,\s*repos\s*\)", SRC["index.html"]) is not None
      and "releveSvg(" in SRC["index.html"] and "fdRepos)" in SRC["index.html"])

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
