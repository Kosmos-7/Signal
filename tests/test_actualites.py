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
check("un trou dans la série est sauté, pas comblé",
      (M.ligne(M.PANIER[0], [100.0, None, 101.79], ["a"] + D2) or {}).get("ref") == "2026-08-07")

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
    {"NVDA": "NVIDIA", "SAP.DE": "SAP"})
check("le plus fort mouvement se juge en VALEUR ABSOLUE (une chute compte)",
      _mv["ticker"] == "SAP.DE" and _mv["nom"] == "SAP")

# LE MÊME FORMATAGE EXISTE DEUX FOIS, EN PYTHON ET EN JS, et c'est assumé : le
# post stocke des NOMBRES, pas des chaînes déjà mises en forme, sinon un post
# archivé garderait à jamais la convention typographique du jour de sa parution.
# La contrepartie d'une duplication est qu'elle dérive en silence. On la compare
# donc valeur par valeur, en exécutant réellement le JS de la page.
_CAS = [(8666.63, 2), (101.79, 2), (63940.0, 0), (3.872, 3), (1.0847, 4),
        (-0.5, 2), (0.0, 2), (1234567.891, 2), (999.995, 2)]
_VARS = [{"variation": 1.79, "type": "pct"}, {"variation": -0.022, "type": "pts"},
         {"variation": 0.0, "type": "pct"}, {"variation": -3.456, "type": "pct"},
         {"variation": 29.45, "type": "pct"}, {"variation": 0.05, "type": "pts"}]
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
check("une variation absente du tableau est rejetée",
      any("absente du tableau" in d for d in A.valider_post(
          {**BON, "marches": "Le CAC 40 a bondi de 4,20 % hier soir, un record "
                             "absolu pour la place parisienne cette année."}, 3, _snap)))
check("un tableau sans commentaire est un défaut",
      any("commentaire de marché" in d for d in A.valider_post(BON, 3, _snap)))
check("un commentaire sans tableau est un défaut",
      any("aucun tableau" in d for d in A.valider_post(_BONM, 3, None)))
check("sans tableau ni commentaire, rien à redire",
      A.valider_post(BON, 3, None) == [])
check("le vocabulaire de conseil est traqué aussi dans le commentaire de marché",
      any("conseil" in d for d in A.valider_post(
          {**BON, "marches": "Le S&P 500 a pris 1,79 %, nous recommandons donc "
                             "la prudence sur les valeurs technologiques."}, 3, _snap)))

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
