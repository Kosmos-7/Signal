#!/usr/bin/env python3
"""Tests hors ligne d'Actualités : le contrat, pas les dépêches.

Ce qu'on protège ici n'est pas du code mais des PROMESSES faites au lecteur :
un post sans source n'existe pas, un post publié ne change plus, et l'index
dit exactement ce que contiennent les fichiers.

    python tests/test_actualites.py
"""
import json
import os
import shutil
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "tools"))

import actualites as A                                              # noqa: E402

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


BON = {
    "titre": "La Fed maintient ses taux, les marchés hésitent",
    "chapeau": "Le point de la nuit : décision de la Fed, résultats en Europe "
               "et repli du pétrole après les chiffres de stocks américains.",
    "sujet": "banques-centrales",
    "sections": [
        {"titre": "La décision", "texte": "La Fed a maintenu ses taux.", "sources": [0]},
        {"titre": "Les marchés", "texte": "Les indices ont peu bougé.", "sources": [1, 2]},
    ],
}

print("— Validation : on n'invente rien, structurellement —")
check("un post conforme passe", A.valider_post(BON, 3) == [])
check("une section sans source est rejetée",
      any("sans source" in d for d in A.valider_post(
          {**BON, "sections": [{**BON["sections"][0], "sources": []}] * 2}, 3)))
check("un indice de dépêche inexistant est rejeté",
      any("sans source" in d for d in A.valider_post(
          {**BON, "sections": [{**BON["sections"][0], "sources": [7]}] * 2}, 3)))
check("le vocabulaire de conseil est rejeté",
      any("conseil" in d for d in A.valider_post(
          {**BON, "sections": [dict(BON["sections"][0],
                                    texte="Nous recommandons la prudence."),
                               BON["sections"][1]]}, 3)))
check("un sujet hors liste est rejeté",
      any("sujet inconnu" in d for d in A.valider_post({**BON, "sujet": "crypto"}, 3)))
check("zéro ou six sections sont rejetées",
      A.valider_post({**BON, "sections": []}, 3)
      and A.valider_post({**BON, "sections": [BON["sections"][0]] * 6}, 3))
check("chaque sujet a ses requêtes d'illustration",
      all(isinstance(v, list) and v for v in A.SUJETS.values()))

print("\n— Anti-redite : un titre dit ce qui a CHANGÉ —")
# LES QUATRE VRAIS TITRES DU 10 AU 13 AOÛT 2026, dans l'ordre de parution.
# C'est le constat propriétaire qui a ouvert le sujet : quatre matins, quatre
# fois l'or, trois fois le pétrole ou l'Iran. Ils servent de banc d'essai, parce
# qu'un garde anti-redite qui ne rattrape pas la redite constatée ne sert à rien.
REDITE = [
    "L'or flambe, l'Iran conditionne Ormuz : matinée chargée",
    "Marchés à l'arrêt, l'or en forme et le pétrole surveille l'Iran",
    "Pétrole et or en hausse, Wall Street dans le rouge avant l'inflation",
    "Wall Street en légère hausse, l'or brille, l'Europe hésite",
]
_avant = list(reversed(REDITE[:3]))          # du plus récent au plus ancien


def _redite(titre, passes):
    return A.defauts_redite({"titre": titre}, A.mots_epuises(passes), passes)


check("l'apostrophe et la capitale ne font pas deux mots différents",
      A.mots_titre("L'or flambe") == A.mots_titre("l’or flambe") == {"or", "flambe"},
      f"→ {sorted(A.mots_titre(chr(76) + chr(39) + 'or flambe'))}")
check("le pluriel ne fait pas un mot neuf au-delà de quatre lettres",
      "marche" in A.mots_titre("Marchés à l'arrêt") and "taux" in A.mots_titre("Les taux"))
check("la grammaire ne compte pas comme sujet",
      not (A.mots_titre("Le pétrole dans le rouge") & {"le", "dans"}))
check("un mot qui porte deux des trois derniers titres est épuisé",
      A.mots_epuises(_avant) == {"or", "iran", "petrole"},
      f"→ {sorted(A.mots_epuises(_avant))}")
check("un mot vu une seule fois reste disponible",
      "inflation" not in A.mots_epuises(_avant))
check("la fenêtre s'arrête à trois titres, une histoire qui revient plus tard "
      "est redevenue une information",
      A.mots_epuises(["Or", "X", "Y", "Or"]) == frozenset())
check("le quatrième titre réel est bien vu comme une redite",
      _redite(REDITE[3], _avant))
check("le troisième aussi, avec deux titres seulement derrière lui",
      _redite(REDITE[2], list(reversed(REDITE[:2]))))
# L'ESQUIVE PAR SYNONYME EST LA SEULE FAÇON DONT CE GARDE POUVAIT ÊTRE INUTILE :
# interdire « or » sans interdire « métal jaune », c'est demander une réécriture,
# pas un autre sujet, et le lecteur relit le même titre en croyant en lire un autre.
check("« le métal jaune » et « le brut » ne passent pas là où « or » et "
      "« pétrole » sont bloqués",
      _redite("Le métal jaune s'envole, le brut suit à Téhéran", _avant))
check("Ormuz, Téhéran et l'Iran sont la même tête d'affiche",
      A.mots_titre("Ormuz") == A.mots_titre("Téhéran") == A.mots_titre("l'Iran"))
check("Nasdaq et S&P 500 sont Wall Street, pas trois sujets",
      A.mots_titre("Le Nasdaq grimpe") == A.mots_titre("Le S&P 500 grimpe")
      == A.mots_titre("Wall Street grimpe"))
check("un vrai autre sujet passe sans encombre",
      not _redite("Intel : le PDG achète, CoreWeave défend ses puces", _avant))
check("sans mémoire, aucun titre n'est une redite",
      not A.defauts_redite({"titre": REDITE[0]}, frozenset(), []))
check("le garde ne plante pas sur un post malformé",
      A.defauts_redite("texte nu", {"or"}, []) == []
      and A.defauts_redite({}, {"or"}, []) == [])
check("les mots épuisés sont nommés en français, pas en jetons internes",
      A.libelles(A.mots_epuises(_avant), _avant) == ["l'Iran", "l'or", "le pétrole"],
      f"→ {A.libelles(A.mots_epuises(_avant), _avant)}")
check("un mot hors famille garde la graphie du titre où il a été lu",
      A.libelles({"europe"}, ["l'Europe hésite"]) == ["Europe"])

_recents = [{"date": "2026-08-13", "titre": REDITE[3], "sujet": "marches"},
            {"date": "2026-08-12", "titre": REDITE[2], "sujet": "marches"}]
_bloc = A.bloc_memoire(_recents, A.mots_epuises([r["titre"] for r in _recents]))
check("le bloc de prompt montre les titres parus et leur sujet",
      REDITE[3] in _bloc and "2026-08-12" in _bloc and "marches" in _bloc)
check("le bloc nomme les mots usés",
      "l'or" in _bloc and "Wall Street" in _bloc)
check("le bloc réserve le cas du vrai titre de marché",
      "décrochage" in _bloc and "record" in _bloc)
check("pas d'archive, pas de bloc", A.bloc_memoire([], frozenset()) == "")
check("des titres sans mot usé donnent un bloc sans liste d'interdits",
      "ont porté au moins deux" not in A.bloc_memoire(
          [{"date": "d", "titre": "Intel achète", "sujet": "tech"}], frozenset()))
# Le bloc part dans un `str.format` : un accolade oubliée casserait le post du
# matin sans qu'aucun test hors ligne ne l'ait vu.
check("le prompt se rend entièrement, mémoire comprise",
      "LES MATINS PRÉCÉDENTS" in A.PROMPT.format(
          sujets="marches", n=1, corps="[0] x", champ_marches="",
          consigne_marches="", bloc_memoire=_bloc, bloc_marches=""))

print("\n— Une dépêche déjà servie n'est pas une information —")
_deps = [{"url": f"u{i}", "titre": f"T{i}"} for i in range(8)]
_gardees, _ecartees = A.trier_depeches(_deps, {"u0", "u3"})
check("les dépêches déjà citées sortent du tirage",
      [d["url"] for d in _gardees] == ["u1", "u2", "u4", "u5", "u6", "u7"]
      and _ecartees == 2)
check("l'ordre des inédites est conservé (la plus fraîche d'abord)",
      A.trier_depeches(_deps, frozenset())[0] == _deps)
# LA MÉMOIRE DÉCLASSE, ELLE NE JETTE PAS. Un matin creux où la moitié des
# dépêches a déjà servi ne doit pas passer sous MIN_DEPECHES et annuler un post
# qui avait de quoi s'écrire : le remède serait pire que la redite.
_maigre, _ = A.trier_depeches(_deps[:6], {"u0", "u1", "u2"})
check("sous le minimum, les déjà servies remontent plutôt que d'annuler le post",
      len(_maigre) == A.MIN_DEPECHES
      and [d["url"] for d in _maigre[:3]] == ["u3", "u4", "u5"])
check("le plafond du prompt tient toujours",
      len(A.trier_depeches([{"url": f"v{i}"} for i in range(40)],
                           frozenset())[0]) == A.MAX_DEPECHES)

print("\n— Immuabilité et index —")
tmp = tempfile.mkdtemp()
cwd = os.getcwd()
os.chdir(tmp)
try:
    p1 = {"id": "2026-08-01", "type": "quotidien", "date": "2026-08-01",
          "titre": "T1", "chapeau": "C1", "photo": None, "sections": [], "sources": []}
    p2 = {"id": "2026-08-02", "type": "quotidien", "date": "2026-08-02",
          "titre": "T2", "chapeau": "C2", "photo": {"src": "x.jpg", "v": "abc"},
          "sections": [], "sources": []}
    A.ecrire_post(p1)
    A.ecrire_post(p2)
    try:
        A.ecrire_post(dict(p1, titre="RÉÉCRIT"))
        check("réécrire un post publié échoue", False)
    except SystemExit:
        check("réécrire un post publié échoue", True)
    A.ecrire_post(dict(p1, titre="corrigé le jour même"), force=True)
    check("--force reste possible", json.load(open(
        os.path.join(A.POSTS, "2026-08-01.json"), encoding="utf-8"))["titre"]
        == "corrigé le jour même")

    n = A.reconstruire_index()
    idx = json.load(open(A.INDEX, encoding="utf-8"))["posts"]
    check("l'index compte tous les posts", n == 2 and len(idx) == 2)
    check("l'index est trié du plus récent au plus ancien",
          [e["id"] for e in idx] == ["2026-08-02", "2026-08-01"])
    check("l'index ne porte que les champs de carte",
          set(idx[0]) == {"id", "type", "date", "titre", "chapeau", "photo"})
    check("l'index reflète les fichiers, pas la mémoire",
          idx[1]["titre"] == "corrigé le jour même")

    print("\n— Matérialisation du post hebdo —")
    json.dump({"week": "Sem. 31 · 2026", "updated_at": "2026-08-01",
               "analyse_claude": {"analyse_macro": "Semaine calme. " * 30,
                                  "message_utilisateurs": "Patience.",
                                  "conviction_globale": "neutre"},
               "macro_news": [{"headline": "H", "source": "Reuters",
                               "url": "https://x", "date": "2026-07-30",
                               "resume_fr": "Résumé."}]},
              open("portfolio.json", "w", encoding="utf-8"))
    pid = A.materialiser_hebdo()
    check("le post hebdo est matérialisé", pid == "hebdo-2026-31")
    hebdo = json.load(open(os.path.join(A.POSTS, f"{pid}.json"), encoding="utf-8"))
    check("le chapeau est borné pour la carte", len(hebdo["chapeau"]) <= 280)
    check("les sources de l'agent sont conservées",
          hebdo["sources"] and hebdo["sources"][0]["source"] == "Reuters")
    check("la seconde matérialisation ne réécrit rien",
          A.materialiser_hebdo() is None)

    print("\n— Rotation des illustrations —")
    # p2 (ci-dessus) n'a pas de champ fichier ; on publie deux posts illustrés.
    A.ecrire_post({"id": "2026-08-04", "type": "quotidien", "date": "2026-08-04",
                   "titre": "T4", "chapeau": "C4",
                   "photo": {"src": "a.jpg", "v": "1", "fichier": "Bourse A.jpg"},
                   "sections": [], "sources": []})
    A.ecrire_post({"id": "2026-08-05", "type": "quotidien", "date": "2026-08-05",
                   "titre": "T5", "chapeau": "C5",
                   "photo": {"src": "b.jpg", "v": "2", "fichier": "Bourse B.jpg"},
                   "sections": [], "sources": []})
    deja = A.photos_deja_utilisees()
    check("les photos des posts récents sont mémorisées",
          deja == {"Bourse A.jpg", "Bourse B.jpg"}, f"→ {sorted(deja)}")
    check("la mémoire est bornée aux n plus récents",
          A.photos_deja_utilisees(n=1) == {"Bourse B.jpg"})
    check("le post hebdo (sans photo) n'entre pas dans la mémoire",
          not any("hebdo" in f for f in deja))

    cands = [(9, "Bourse B.jpg", "q1"), (7, "NYSE trading floor.jpg", "q1"),
             (5, "Bourse A.jpg", "q2")]
    check("le meilleur candidat FRAIS gagne, pas le meilleur absolu",
          A.choisir_candidats(cands, deja)[0][1] == "NYSE trading floor.jpg")
    check("sans mémoire, le tri par score reste inchangé",
          A.choisir_candidats(cands, frozenset())[0][1] == "Bourse B.jpg")
    check("vivier épuisé : la redite vaut mieux que le post nu",
          A.choisir_candidats(cands, {"Bourse A.jpg", "Bourse B.jpg",
                                      "NYSE trading floor.jpg"})[0][1] == "Bourse B.jpg")

    # Le cas réel du 5 août : même tableau de Yaesu, autre année, autre nom.
    yaesu09 = ("Shinko Securities's electronic stock board nearby Yaesu side "
               "of Tokyo Station in March 2009.jpg")
    cands2 = [(9, "Electronic stock board in Yaesu, Tokyo 2007.jpg", "q"),
              (7, "New York Stock Exchange trading floor 2008.jpg", "q")]
    check("un quasi-doublon de scène déjà parue est écarté",
          A.choisir_candidats(cands2, {yaesu09})[0][1]
          == "New York Stock Exchange trading floor 2008.jpg")
    check("une scène réellement différente n'est pas confondue",
          A.choisir_candidats([(7, "Frankfurt Boerse display board.jpg", "q")],
                              {"New York Stock Exchange trading floor.jpg"})[0][1]
          == "Frankfurt Boerse display board.jpg")

    # Le raté du 4 août : « Wall Street street sign » a rapporté une plaque de
    # rue de ministères londoniens, appariée sur les seuls mots génériques.
    check("un candidat sans mot distinctif de sa requête est écarté",
          A.choisir_candidats(
              [(9, "06 2023 King Charles Street, London IMG 7517.jpg",
                "Wall Street street sign"),
               (7, "Wall Street sign New York.jpg", "Wall Street street sign")],
              frozenset())[0][1] == "Wall Street sign New York.jpg")
    check("une requête toute générique n'applique pas le filtre",
          A.choisir_candidats([(9, "Big Board of Trade.jpg",
                                "stock exchange display board")],
                              frozenset())[0][1] == "Big Board of Trade.jpg")
    check("pertinence sans candidat : retomber sur les inédits, pas sur rien",
          A.choisir_candidats([(9, "Random alley.jpg", "Wall Street street sign")],
                              frozenset())[0][1] == "Random alley.jpg")
    check("la légende perd dates de tri et codes d'appareil",
          A.nettoyer_legende("06 2023 King Charles Street, London IMG 7517.jpg")
          == "King Charles Street, London")
    check("la légende garde les noms propres et coupe au mot entier",
          A.nettoyer_legende("Trading floor, New York Stock Exchange, New York, "
                             "New York LCCN2011630168.tif")
          == "Trading floor, New York Stock Exchange, New York, New York")

    print("\n— Réillustration des posts publiés (photo seule, texte intact) —")
    A.ecrire_post({"id": "2026-08-06", "type": "quotidien", "date": "2026-08-06",
                   "titre": "T6", "chapeau": "C6", "sujet": "marches",
                   "photo": {"src": "t.jpg", "v": "3", "fichier": "Tokyo board.jpg"},
                   "sections": [{"titre": "S", "texte": "X.", "sources": [0]}],
                   "sources": [{"titre": "dep"}]})
    recus = []
    def fake(pid, sujet, deja):
        recus.append((pid, sujet, set(deja)))
        return {"src": f"actualites/photos/{pid}.jpg", "v": "n", "legende": "l",
                "fichier": "NYSE floor.jpg", "credit": "", "licence": "CC0",
                "page": "", "requete": "q"}
    faits = A.reillustrer(["2026-08-06", "hebdo-2026-31", "inexistant"],
                          illustrateur=fake)
    apres = json.load(open(os.path.join(A.POSTS, "2026-08-06.json"),
                           encoding="utf-8"))
    check("la photo est remplacée", faits == ["2026-08-06"]
          and apres["photo"]["fichier"] == "NYSE floor.jpg")
    check("le texte n'est pas touché",
          apres["titre"] == "T6" and apres["sections"][0]["texte"] == "X.")
    check("l'ancienne photo du post traité est dans la mémoire transmise",
          recus and "Tokyo board.jpg" in recus[0][2])
    check("hebdo et post inexistant sont refusés sans casser le lot",
          len(recus) == 1)
finally:
    os.chdir(cwd)
    shutil.rmtree(tmp, ignore_errors=True)

print("\n— Sur les marchés : le tableau ne se remplit pas tout seul —")
import marches as M                                                 # noqa: E402

D2 = ["2026-08-06", "2026-08-07"]
check("une variation en % se calcule sur les deux dernières clôtures",
      abs(M.variation(100.0, 101.79, "pct") - 1.79) < 1e-9)
check("un taux se compare en POINTS, pas en pourcentage de lui-même",
      abs(M.variation(3.894, 3.872, "pts") + 0.022) < 1e-9)
check("une veille à zéro ne rend pas un infini",
      M.variation(0.0, 1.0, "pct") is None)
check("une seule clôture ne fait pas une ligne : un niveau sans variation ne dit rien",
      M.ligne(M.PANIER[0], [100.0], D2[:1]) is None)
check("une clôture manquante au milieu est sautée, pas comblée",
      (M.ligne(M.PANIER[0], [99.0, None, 100.0, 101.79],
               ["2026-08-04", "2026-08-05"] + D2) or {}).get("ref") == "2026-08-07")

_l = M.ligne(M.PANIER[0], [100.0, 101.79], D2)
check("le format est français : fine insécable, virgule décimale",
      M.fmt_nombre(8666.63, 2) == "8" + M.FINE + "666,63"
      and M.fmt_variation(_l) == "+1,79" + M.INSEC + "%")
check("le signe est toujours écrit, même à la hausse",
      M.fmt_variation(M.ligne(M.PANIER[0], [101.79, 100.0], D2)).startswith("-"))

# LA RÈGLE DU DEMI-TABLEAU. Une ligne manquante dans un tableau de marchés ne se
# voit pas : le lecteur croit que le Nasdaq n'a pas bougé, pas qu'on n'a pas su
# le lire. En dessous de MIN_LIGNES il n'y a donc pas de tableau du tout.
_faux = [dict(_l, cle=c) for c in ("nasdaq", "sp500", "cac40", "stoxx", "or", "petrole", "bitcoin")]
check("moins de quatre instruments : pas de tableau du tout",
      M.choisir(_faux[:3]) == [])
check("l'ordre affiché est celui du panier, jamais celui des réponses",
      [l["cle"] for l in M.choisir(_faux)][:3] == ["sp500", "cac40", "nasdaq"])
check("le tableau est plafonné pour ne pas devenir un écran de terminal",
      len(M.choisir(_faux)) == M.MAX_LIGNES)

_snap = {"ref": "2026-08-07", "lignes": M.choisir(_faux), "mouvement": None}
check("le bloc de prompt porte les niveaux ET les variations",
      ("+1,79" + M.INSEC + "%") in M.bloc_prompt(_snap) and "101,79" in M.bloc_prompt(_snap))
check("pas de tableau, pas de bloc de prompt", M.bloc_prompt(None) == "")

_mv = M.plus_fort_mouvement(
    {"NVDA": ([100.0, 102.0], D2), "SAP.DE": ([100.0, 94.0], D2)},
    {"NVDA": "NVIDIA", "SAP.DE": "SAP"}, D2[1])
check("le plus fort mouvement se juge en VALEUR ABSOLUE (une chute compte)",
      _mv["ticker"] == "SAP.DE" and _mv["nom"] == "SAP")

# LE PIÈGE DE TAIPEI. Le job tourne à 05h45 UTC, quinze minutes après la clôture
# de Taipei et bien avant celle de New York ou Paris. Sans alignement, un -6 %
# de TSMC du MATIN MÊME battait les +1 % de la veille à Wall Street, et le post,
# gelé, attribuait pour toujours un mouvement de lundi à la séance de vendredi.
_LUNDI, _VEND = "2026-08-10", "2026-08-07"
check("un mouvement d'une AUTRE séance ne gagne pas le concours",
      (M.plus_fort_mouvement({"2330.TW": ([1000.0, 940.0], [_VEND, _LUNDI]),
                              "NVDA": ([100.0, 101.0], D2)},
                             {"2330.TW": "TSMC", "NVDA": "NVIDIA"}, _VEND) or {}
       ).get("nom") == "NVIDIA")
check("la séance de référence est celle des indices actions, pas du bitcoin",
      M.seance_de_reference({"^GSPC": ([1.0, 2.0], D2), "^FCHI": ([1.0, 2.0], D2),
                             "BTC-USD": ([1.0, 2.0, 3.0], D2 + [_LUNDI])}) == D2[1])
check("chaque instrument est ramené à la séance de référence",
      (M.ligne(M.PANIER[8], *M.jusqua([63000.0, 63800.0, 64500.0],
                                      D2 + [_LUNDI], D2[1])) or {}).get("ref") == D2[1])
check("un trou dans la série ne devient pas la variation du jour",
      M.ligne(M.PANIER[0], [100.0, 120.0], ["2026-07-20", D2[1]]) is None)
check("un week-end de trois jours reste une séance à l'autre",
      M.ligne(M.PANIER[0], [100.0, 101.0], [_VEND, _LUNDI]) is not None)

# Le second écart Python/JS trouvé par la relecture adverse : les deux signaient
# « +0,004 % » sous une pastille grise annoncée « plate ».
check("une variation sous le seuil de platitude ne porte pas de signe",
      M.fmt_variation({"variation": 0.004, "type": "pct"}) == "0,00" + M.INSEC + "%"
      and M.plat({"variation": 0.004, "type": "pct"}))

# LE MÊME FORMATAGE EXISTE DEUX FOIS, EN PYTHON ET EN JS, et c'est assumé : le
# post stocke des NOMBRES, pas des chaînes déjà mises en forme, sinon un post
# archivé garderait à jamais la convention typographique du jour de sa parution.
# La contrepartie d'une duplication est qu'elle dérive en silence. On la compare
# donc valeur par valeur, en exécutant réellement le JS de la page.
_CAS = [(8666.63, 2), (101.79, 2), (63940.0, 0), (3.872, 3), (1.0847, 4),
        (-0.5, 2), (0.0, 2), (1234567.891, 2), (999.995, 2)]
_VARS = [{"variation": 1.79, "type": "pct"}, {"variation": -0.022, "type": "pts"},
         {"variation": 0.0, "type": "pct"}, {"variation": -3.456, "type": "pct"},
         {"variation": 29.45, "type": "pct"}, {"variation": 0.05, "type": "pts"},
         {"variation": 0.004, "type": "pct"}, {"variation": -0.0003, "type": "pts"},
         {"variation": 0.006, "type": "pct"}]
try:
    import subprocess                                                # noqa: E402
    _js = open(os.path.join(RACINE, "actualites.html"), encoding="utf-8").read()
    _deb = _js.index("const FINE=")
    _fin = _js.index("function ligneMarche")
    _prog = _js[_deb:_fin] + (
        "const cas=" + json.dumps(_CAS) + ", vars=" + json.dumps(_VARS) + ";"
        "console.log(JSON.stringify({n:cas.map(c=>nbFr(c[0],c[1])),"
        "v:vars.map(varFr)}));")
    _out = json.loads(subprocess.run(["node", "-e", _prog], capture_output=True,
                                     text=True, timeout=30, check=True).stdout)
    check("Python et JS formatent les niveaux à l'identique",
          _out["n"] == [M.fmt_nombre(v, d) for v, d in _CAS],
          f"\n     js={_out['n']}\n     py={[M.fmt_nombre(v, d) for v, d in _CAS]}")
    check("Python et JS formatent les variations à l'identique",
          _out["v"] == [M.fmt_variation(l) for l in _VARS],
          f"\n     js={_out['v']}\n     py={[M.fmt_variation(l) for l in _VARS]}")
except (OSError, subprocess.SubprocessError, ValueError) as _e:
    # Sans node, on ne fait pas semblant d'avoir vérifié : on le dit.
    print(f"  ⚠️  formatage JS non comparé (node indisponible : {type(_e).__name__})")

print("\n— Le commentaire de marché ne cite que des chiffres mesurés —")
_BONM = {**BON, "marches": "Le S&P 500 a pris 1,79 % et entraîne le reste de la cote "
                           "dans son sillage, sans qu'aucune statistique ne l'explique."}
check("un commentaire adossé au tableau passe",
      A.valider_post(_BONM, 3, _snap) == [])
check("l'arrondi à la décimale est admis (1,8 % pour 1,79 %)",
      A.valider_post({**BON, "marches": "Le S&P 500 a pris 1,8 % sur la séance, "
                                        "et le mouvement s'est fait sans à-coups."}, 3, _snap) == [])
# LE CAS QUI A FAILLI COÛTER UN MATIN. Le niveau d'un taux s'écrit avec un
# « % » et le prompt demande de citer les niveaux : « le Treasury 10 ans termine
# à 3,872 % » est juste, et la première version du garde la rejetait — deux
# rejets, sortie en erreur, pas de post. Trouvé par une relecture adverse avant
# le premier run réel.
_T10 = M.ligne({"cle": "t10", "libelle": "Treasury 10 ans", "ticker": "^TNX",
                "type": "pts", "dec": 3, "unite": "%"}, [3.894, 3.872], D2)
_SNAPT = {"ref": D2[1], "mouvement": None,
          "lignes": M.choisir([_l, dict(_l, cle="cac40"), dict(_l, cle="nasdaq"),
                               _T10, dict(_l, cle="or")])}
check("le NIVEAU d'un taux, écrit en %, est une citation légitime",
      A.valider_post({**BON, "marches": "Le rendement du Treasury 10 ans termine à "
                                        "3,872 %, pendant que le S&P 500 prend 1,79 %."},
                     3, _SNAPT) == [])
check("mais un niveau inventé au même endroit reste rejeté",
      any("absent du tableau" in d for d in A.valider_post(
          {**BON, "marches": "Le rendement du Treasury 10 ans termine à 4,510 %, "
                             "un plus haut de l'année pour la dette américaine."}, 3, _SNAPT)))
check("la variation du plus fort mouvement compte parmi les chiffres connus",
      A.valider_post({**BON, "marches": "Palantir signe la plus forte hausse du jour "
                                        "avec 29,45 %, loin devant les indices."},
                     3, {**_snap, "mouvement": {"ticker": "PLTR", "nom": "Palantir",
                                                "libelle": "Palantir", "valeur": 162.66,
                                                "dec": 2, "unite": "$", "type": "pct",
                                                "variation": 29.45, "ref": D2[1]}}) == [])
check("une variation absente du tableau est rejetée",
      any("absent du tableau" in d for d in A.valider_post(
          {**BON, "marches": "Le CAC 40 a bondi de 4,20 % hier soir, un record "
                             "absolu pour la place parisienne cette année."}, 3, _snap)))
check("un tableau sans commentaire est un défaut",
      any("commentaire de marché" in d for d in A.valider_post(BON, 3, _snap)))
check("un commentaire sans tableau est un défaut",
      any("aucun tableau" in d for d in A.valider_post(_BONM, 3, None)))
check("sans tableau ni commentaire, rien à redire",
      A.valider_post(BON, 3, None) == [])
check("« recule de 3,46 % » est juste pour -3,46 : c'est le verbe qui porte le signe",
      A.valider_post({**BON, "marches": "Le Nasdaq recule de 3,46 % et entraîne les "
                                        "autres indices dans son repli du jour."},
                     3, {**_snap, "lignes": [dict(l, variation=-3.46)
                                             for l in _snap["lignes"]]}) == [])
check("mais un signe ÉCRIT à l'envers est une inversion, pas une tournure",
      any("absent du tableau" in d for d in A.valider_post(
          {**BON, "marches": "Le Nasdaq gagne +3,46 % et entraîne les autres "
                             "indices dans son sillage sur la séance du jour."},
          3, {**_snap, "lignes": [dict(l, variation=-3.46) for l in _snap["lignes"]]})))
check("les points de base sont convertis avant comparaison (22 pb = 0,22 pt)",
      A.valider_post({**BON, "marches": "Le rendement du Treasury 10 ans cède "
                                        "2,2 points de base sur la séance, sans bruit."},
                     3, _SNAPT) == [])
check("un gros mouvement s'arrondit plus grossièrement (29,5 % pour 29,45 %)",
      A.valider_post({**BON, "marches": "Palantir signe la plus forte hausse du jour "
                                        "avec 29,5 %, loin devant les indices."},
                     3, {**_snap, "mouvement": {"ticker": "PLTR", "nom": "Palantir",
                                                "libelle": "Palantir", "valeur": 162.66,
                                                "dec": 2, "unite": "$", "type": "pct",
                                                "variation": 29.45, "ref": D2[1]}}) == [])
check("une section qui n'est pas un objet est un défaut, pas un plantage",
      any("n'est pas un objet" in d
          for d in A.valider_post({**BON, "sections": ["texte nu", "autre"]}, 3)))
check("le vocabulaire de conseil est traqué aussi dans le commentaire de marché",
      any("conseil" in d for d in A.valider_post(
          {**BON, "marches": "Le S&P 500 a pris 1,79 %, nous recommandons donc "
                             "la prudence sur les valeurs technologiques."}, 3, _snap)))

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
