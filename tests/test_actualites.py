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
finally:
    os.chdir(cwd)
    shutil.rmtree(tmp, ignore_errors=True)

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
