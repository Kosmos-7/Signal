#!/usr/bin/env python3
"""Tests de non-régression des watchlists thématiques.

Aucun accès réseau : les modules lourds (ta, yfinance, requests) sont bouchés,
et les données sont simulées. On teste le contrat, pas les données de marché.

    python tests/test_themes.py
"""
import json
import os
import re
import sys
import types

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

# ── Bouchons : screener importe des modules absents de l'env de test ────────
# La liste est UNIQUE (tests/_bouchons.py) : recopiée, elle divergeait — c'est
# ainsi que `numpy` a manqué aux deux suites sans que rien ne le signale.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bouchons              # noqa: E402
_bouchons.poser()

import themes                    # noqa: E402
import screener                  # noqa: E402
import portfolio_agent as pa     # noqa: E402

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


print("— Taxonomie —")
ids = [t["id"] for t in themes.THEMES]
check("identifiants uniques", len(ids) == len(set(ids)))
check("5 thèmes curés publiés (quantique et robotique le 08/08, espace le 09/08)",
      len(themes.THEMES_CURES) == 5)
check("chaque thème a thèse, inversion et biais",
      all(t.get("thesis") and t.get("inversion") and t.get("biais") for t in themes.THEMES))
check("les thèmes calculés publient leur règle en clair",
      all(t.get("regle_texte") for t in themes.THEMES_CALCULES))
# UNE SEULE EXCEPTION À LA RÈGLE DES VINGT, et elle est nommée. La règle
# protège contre le thème alibi, bricolé avec trois titres pour faire nombre.
# « quantique » est le cas inverse : son périmètre est petit parce que le
# SECTEUR l'est — dix pure players cotés au monde, dont six pas encore
# notables — et le dire est l'information principale de la page. Nommer
# l'exception plutôt que baisser le seuil garde la règle mordante pour tous
# les autres, et oblige la prochaine à être justifiée elle aussi.
ETRIQUE_ADMIS = {"quantique"}
check("aucun thème curé étriqué, hors exception nommée",
      all(len(t["tickers"]) >= 20 for t in themes.THEMES_CURES
          if t["id"] not in ETRIQUE_ADMIS),
      str([t["id"] for t in themes.THEMES_CURES
           if t["id"] not in ETRIQUE_ADMIS and len(t["tickers"]) < 20]))
# Un thème de chaîne de valeur ne vaut que si chaque maillon a un représentant.
# On ne peut pas tester la sémantique, mais on peut tester la taille minimale
# qui rend une chaîne à six maillons crédible.
_infra = themes.THEMES_BY_ID.get("infra-ia")
check("infra-ia couvre assez de titres pour six maillons",
      _infra and len(_infra["tickers"]) >= 40, f"{len(_infra['tickers']) if _infra else 0}")

# ── LE THÈME QUANTIQUE ─────────────────────────────────────────────────────
# Il déroge à deux conventions du projet, et une dérogation qui n'est pas dite
# est une erreur qui attend. Ces vérifications tiennent la promesse écrite dans
# son champ `biais` : les dérogations existent, elles sont bornées aux
# pure-players, et le texte les annonce.
print("\n— Le thème quantique —")
_q = themes.THEMES_BY_ID.get("quantique")
check("le thème quantique existe et publie un top borné",
      _q and _q.get("top") == 10, str(_q and _q.get("top")))
# LE PLAFOND EST UN RENDEZ-VOUS, PAS UNE FICTION. La liste publie quatre titres
# et son plafond en vaut dix : c'est voulu. Les cinq introductions de 2026
# franchiront les 200 séances entre décembre et avril, et entreront sans que
# personne ne touche à ce fichier. Le plafond doit donc rester au-dessus du
# déclaré — s'il descendait à sa taille, la liste cesserait de pouvoir grandir.
check("le plafond laisse la place aux entrées à venir",
      _q and _q["top"] >= len(_q["tickers"]),
      f"{len(_q['tickers']) if _q else 0} déclarés, plafond {_q['top'] if _q else 0}")
check("la liste ne contient QUE des pure players",
      _q and set(_q["tickers"]) == {"IONQ", "RGTI", "QBTS", "QUBT"},
      str(sorted(_q["tickers"]) if _q else []))
# Les douze titres de la chaîne (fondeurs, cryogénistes, instrumentistes) sont
# sortis du THÈME le 08/08 mais restent dans l'UNIVERS du screener — même choix
# qu'au retrait de « financials ». Sans cela, douze sociétés validées perdraient
# leur note et sept fiches publiées deviendraient orphelines.
_chaine = {"IBM", "KEYS", "MKSI", "FORM", "OXIG.L", "GFS", "STMPA.PA",
           "SOI.PA", "6701.T", "6702.T", "6965.T", "6302.T"}
check("la chaîne quittée reste dans l'univers du screener",
      _chaine <= set(screener.UNIVERS), str(sorted(_chaine - set(screener.UNIVERS))))
# La dérogation au seuil de taille et celle à l'historique doivent être ÉCRITES
# dans le texte que le lecteur voit, pas seulement dans un commentaire de code.
check("les deux dérogations sont annoncées au lecteur",
      _q and "25 milliards" in _q["biais"] and "cinq ans de cotation" in _q["biais"])
check("le biais prévient que la note ne s'applique pas à ces sociétés",
      _q and "la grille ne s'applique pas" in _q["biais"])
# LES QUATRE INTRODUCTIONS DE 2026 (QNT, INFQ, XNDU, HQ) ont été mesurées le
# 08/08 : toutes sous les 200 séances exigées par la MM200 et le RSI. Les
# déclarer produirait un thème amputé publié en silence — le mode de panne que
# validate_tickers.py existe précisément pour éviter.
_jeunes = {"QNT", "INFQ", "XNDU", "HQ", "IQMX.HE"}
check("les cinq introductions de 2026 sont au registre, avec leur motif",
      all(t in themes.ECARTES_VALIDATION and "200" in themes.ECARTES_VALIDATION[t]
          for t in _jeunes),
      str(sorted(t for t in _jeunes if t not in themes.ECARTES_VALIDATION)))
check("aucune introduction de 2026 n'est déclarée avant d'avoir 200 séances",
      not (_jeunes & set(themes.univers_thematique())),
      str(sorted(_jeunes & set(themes.univers_thematique()))))

print("\n— Le thème espace —")
_e = themes.THEMES_BY_ID.get("espace")
_et = set(_e["tickers"]) if _e else set()
check("le thème espace existe et publie toute sa liste",
      _e is not None and "top" not in _e)
# LE PARADOXE DE CETTE LISTE, et son information principale : la plus grande
# société spatiale du monde n'y figure pas. SpaceX cote depuis juin 2026 pour
# ~1 755 Md$ — plus, à elle seule, que tout le reste de la watchlist réunie —
# mais 39 séances contre 200 exigées par la MM200 et le RSI. La déclarer
# produirait un thème amputé publié en silence ; on l'inscrit au registre avec
# la date où son historique suffira, comme les cinq introductions quantiques.
check("SpaceX est au registre, avec ses séances et sa date",
      "SPCX" in themes.ECARTES_VALIDATION
      and "200" in themes.ECARTES_VALIDATION["SPCX"]
      and "2027" in themes.ECARTES_VALIDATION["SPCX"])
check("SpaceX n'est pas déclarée avant d'avoir ses 200 séances",
      "SPCX" not in _et)
# ... et son absence doit être DITE au lecteur, en tête des biais. Un trou muet
# sur le titre le plus attendu du thème serait le pire des silences.
check("l'absence de SpaceX est expliquée dans les biais",
      _e and "SpaceX" in _e["biais"] and "avril 2027" in _e["biais"])
# LES DEUX MOITIÉS. Le spatial cotable oppose des pure players trop petits pour
# le seuil du projet à des groupes de défense où l'espace est un département.
# Comparer leurs scores n'a pas de sens, et le texte doit le dire.
_me = {m["label"]: set(m["tickers"]) for m in (_e["maillons"] if _e else [])}
_primes = next((v for k, v in _me.items() if "défense" in k.lower()), set())
check("le maillon des maîtres d'œuvre porte les primes",
      {"LMT", "NOC", "LHX"} <= _primes, str(sorted(_primes)))
# Comparaison insensible à la casse : le texte met ses avertissements en
# capitales, et un test calé sur la casse se casse au premier reformatage.
_biais_e = (_e["biais"] if _e else "").lower()
check("le biais prévient qu'on ne compare pas les deux moitiés",
      "coupée en deux" in _biais_e)
check("la dérogation de taille est annoncée",
      _e and "25 milliards" in _e["biais"])
# Le calcul en orbite est le sujet du moment ; il n'est presque pas achetable,
# et la liste ne doit pas laisser croire l'inverse.
check("le biais dit que le calcul en orbite n'est pas achetable",
      "en orbite" in _biais_e and "privées" in _biais_e
      and "presque pas achetable" in _biais_e)

print("\n— Infrastructure de l'IA : le maillon des bailleurs —")
_i = themes.THEMES_BY_ID.get("infra-ia")
_mi = {m["label"]: set(m["tickers"]) for m in (_i["maillons"] if _i else [])}
_bail = next((v for k, v in _mi.items() if "bailleur" in k.lower()), set())
# LE MAILLON EST NÉ D'UNE QUESTION DU PROPRIÉTAIRE : « Applied Digital n'est pas
# dans la liste, pourquoi ? ». La réponse était : aucune raison — le titre
# n'était ni dans l'univers ni au registre des écartés, alors que ce registre
# existe pour que toute absence ait un motif lisible. L'angle mort en cachait
# quatre autres, tous d'anciens mineurs de bitcoin devenus bailleurs de
# capacité pour hyperscalers.
check("le maillon des bailleurs existe et porte Applied Digital",
      "APLD" in _bail, str(sorted(_bail)))
check("les cinq bailleurs y sont",
      {"APLD", "WULF", "CIFR", "IREN", "CORZ"} <= _bail,
      str(sorted({"APLD", "WULF", "CIFR", "IREN", "CORZ"} - _bail)))
# La dérogation de taille doit être ÉCRITE pour le lecteur, comme sur les deux
# autres thèmes qui en usent — sans quoi elle serait un passe-droit silencieux.
check("la dérogation de taille des bailleurs est annoncée",
      _i and "25 milliards" in _i["biais"])
# ... et l'avertissement que la note lit mal ces sociétés-là : elles ont vendu
# ce qu'elles n'ont pas construit, leurs comptes ne montrent que la dépense.
check("le biais prévient qu'un score bas n'y dit pas la même chose",
      _i and "carnet de commandes" in _i["biais"])
# ALAB et CRDO ont dormi huit jours au registre en « attente de décision ».
# Tranchés le 09/08, ils doivent en SORTIR : un titre ne peut pas être à la
# fois publié et écarté — c'est la leçon GlobalFoundries.
check("aucun titre du thème ne reste au registre des écartés",
      not (set(_i["tickers"]) & set(themes.ECARTES_VALIDATION)) if _i else False,
      str(sorted(set(_i["tickers"]) & set(themes.ECARTES_VALIDATION))))
check("plus aucune décision ne dort au registre",
      not [t for t, m in themes.ECARTES_VALIDATION.items()
           if "attente de décision" in m],
      str([t for t, m in themes.ECARTES_VALIDATION.items()
           if "attente de décision" in m]))

print("\n— Le thème robotique —")
_r = themes.THEMES_BY_ID.get("robotique")
_rt = set(_r["tickers"]) if _r else set()
check("le thème robotique existe et publie toute sa liste",
      _r is not None and "top" not in _r, str(_r and _r.get("top")))
check("il déclare assez de titres pour ne pas invoquer la dérogation d'étroitesse",
      _r and len(_r["tickers"]) >= 20 and "robotique" not in ETRIQUE_ADMIS,
      f"{len(_rt)} déclarés")
# LA RÈGLE D'ENTRÉE EST LE THÈME. Elle retient les sociétés dont les comptes
# bougent avec le nombre de robots vendus, et elle écarte les industriels dont
# l'exposition est réelle mais noyée. Les douze titres ci-dessous ont tous été
# examinés le 08/08/2026 et écartés sur ce seul motif — quatre après une
# validation sans erreur le jour même (Teradyne, Mitsubishi Electric, Denso,
# Sumitomo Heavy, Novanta). Ils sont la pente naturelle de ce sujet : sans ce
# garde-fou, la liste redevient un panier de conglomérats industriels.
_DILUES = {"EMR", "PH", "AME", "ADI", "IFX.DE", "NVDA",
           "TER", "6503.T", "6902.T", "6302.T"}
check("aucun industriel à exposition diluée n'est entré dans la liste",
      not (_rt & _DILUES), str(sorted(_rt & _DILUES)))
# ... mais l'exclusion du THÈME n'est pas un rejet du PROJET : ces titres
# restent scorés et candidats à la watchlist principale. C'est la distinction
# que l'incident GlobalFoundries du 08/08 a rendue explicite — un titre ne peut
# pas être à la fois publié et « écarté ».
check("les dilués restent scorés par le screener",
      _DILUES <= set(screener.UNIVERS), str(sorted(_DILUES - set(screener.UNIVERS))))
check("aucun dilué n'est au registre des écartés",
      not (_DILUES & set(themes.ECARTES_VALIDATION)),
      str(sorted(_DILUES & set(themes.ECARTES_VALIDATION))))
# DEUX MOTIFS DIFFÉRENTS, deux sorts différents — les confondre est ce que la
# première version de ce test a fait. Novanta et Zebra ne sont pas écartés pour
# dilution mais pour TAILLE : sous le seuil de 25 Md$, comme AMKR ou SMCI avant
# eux. Ceux-là vont au registre, précisément pour ne pas disparaître après avoir
# été validés — c'est le mode de panne « examiné puis perdu ».
_SOUS_SEUIL = {"NOVT", "ZBRA"}
check("les validés sous le seuil sont au registre, avec leur capitalisation",
      all(t in themes.ECARTES_VALIDATION and "seuil 25 Md$" in themes.ECARTES_VALIDATION[t]
          for t in _SOUS_SEUIL),
      str(sorted(t for t in _SOUS_SEUIL if t not in themes.ECARTES_VALIDATION)))
check("aucun titre sous le seuil n'est entré dans la liste",
      not (_rt & _SOUS_SEUIL), str(sorted(_rt & _SOUS_SEUIL)))
# KUKA n'est pas écarté, il n'est plus cotable : racheté par Midea, sorti de
# Francfort en 2022, son ADR ne rend plus d'historique. Le maillon des
# constructeurs en compte trois au lieu de quatre pour cette seule raison, et
# c'est une information, pas un trou.
check("KUKA est au registre avec le motif de sa disparition",
      "KUKAY" in themes.ECARTES_VALIDATION
      and "Midea" in themes.ECARTES_VALIDATION["KUKAY"])
# LA THÈSE REPOSE SUR LE GOULOT : « ces pièces-là sortent d'une poignée
# d'ateliers ». Si les deux réducteurs de précision quittaient la liste, ce
# texte deviendrait un slogan sans objet — le thème doit tomber avec eux.
_maillons = {m["label"]: set(m["tickers"]) for m in (_r["maillons"] if _r else [])}
_goulot = next((v for k, v in _maillons.items() if "goulot" in k.lower()), set())
check("le maillon du goulot porte les deux réducteurs de précision",
      {"6324.T", "6268.T"} <= _goulot, str(sorted(_goulot)))
# Le biais annonce qu'il reste « deux pure players asiatiques » sur les
# humanoïdes : si les deux sortaient, le maillon ne contiendrait plus que des
# constructeurs automobiles et le texte mentirait au lecteur.
_humain = next((v for k, v in _maillons.items() if "humano" in k.lower()), set())
check("le maillon humanoïde garde au moins un pure player coté",
      bool(_humain & {"9880.HK", "277810.KQ"}), str(sorted(_humain)))
# La dérogation de taille doit être ÉCRITE pour le lecteur, comme sur le
# quantique : plusieurs titres du goulot pèsent moins de dix milliards.
check("la dérogation de taille est annoncée au lecteur",
      _r and "25 milliards" in _r["biais"])
check("le pari de change est annoncé au lecteur",
      _r and "yen" in _r["biais"].lower())

# UN THÈME SANS ILLUSTRATION SE PUBLIE QUAND MÊME — le front a un repli
# textuel — donc rien ne signale l'oubli. C'est le mode de panne silencieuse
# habituel du projet : on l'attrape ici plutôt qu'en regardant la page.
sys.path.insert(0, os.path.join(RACINE, "tools"))
import fetch_theme_photos as ftp   # noqa: E402
_sans_image = [t["id"] for t in themes.THEMES_CURES if not ftp.REQUETES.get(t["id"])]
check("chaque thème publié a ses requêtes d'illustration", not _sans_image, str(_sans_image))

# Doctrine de nommage : ne jamais emprunter le vocabulaire d'un concept non calculé
interdits = ["moat", "douve", "marge de sécurité", "valeur intrinsèque"]
textes = " ".join(f"{t['label']} {t['sous_titre']} {t['thesis']}" for t in themes.THEMES).lower()
fautes = [m for m in interdits if m in textes]
check("aucun vocabulaire emprunté dans les libellés et thèses", not fautes, f"trouvé : {fautes}")

# Un texte qui cite les titres retenus devient faux tout seul la semaine
# suivante, la liste etant recalculee a chaque run. Le cas reel etait un nom de
# societe et un compte, que ce test ne peut pas voir ; il attrape au moins la
# forme la plus tentante, le ticker cite en exemple dans sa propre these.
fautifs = []
for t in themes.THEMES:
    texte = " ".join(str(t.get(c) or "") for c in ("thesis", "sous_titre", "biais",
                                                   "inversion", "regle_texte"))
    for tk in t.get("tickers", []):
        # Frontieres de mot : « V » ou « ON » matcheraient n'importe quoi.
        if re.search(r"(?<![\w.])" + re.escape(tk) + r"(?![\w.])", texte):
            fautifs.append(f"{t['id']}→{tk}")
check("aucune description ne cite un ticker de sa propre liste", not fautifs, str(fautifs))

print("\n— Univers dérivé —")
u = set(themes.univers_thematique())
check("les titres recalés par la validation sont absents",
      not (u & set(themes.ECARTES_VALIDATION)), f"{u & set(themes.ECARTES_VALIDATION)}")
check("chaque titre de thème est dans l'univers du screener",
      u <= set(screener.UNIVERS), f"manquants : {sorted(u - set(screener.UNIVERS))[:5]}")
check("l'univers historique est préservé",
      {"AAPL", "NVDA", "MC.PA", "ASML.AS", "ORSTED.CO"} <= set(screener.UNIVERS))
check("univers dans un ordre déterministe", screener.UNIVERS == sorted(set(screener.UNIVERS)))

print("\n— Devises —")
for t, attendu in [("6954.T", "JPY"), ("8035.T", "JPY"), ("000660.KS", "KRW"),
                   ("005930.KS", "KRW"), ("LDO.MI", "EUR"), ("SAAB-B.ST", "SEK"),
                   ("ABBN.SW", "CHF"), ("BA.L", "GBP"), ("RHHBY", "USD"),
                   ("ORSTED.CO", "DKK"), ("NVDA", "USD"),
                   # TAIPEI ET HONG KONG, ajoutés le 08/08/2026. TSMC est passé
                   # de son ADR à sa ligne de Taipei le matin même : sans cette
                   # branche il cotait 2 370 « dollars », soit trente-deux fois
                   # sa valeur. C'est la panne d'ORSTED.CO à un ordre de
                   # grandeur près, et elle n'a été vue qu'en préparant une
                   # AUTRE watchlist. Le HKD est plus sournois : arrimé au
                   # dollar, il ne se trompe que d'un facteur 7,8.
                   ("2330.TW", "TWD"), ("2049.TW", "TWD"), ("9880.HK", "HKD")]:
    check(f"{t} → {attendu}", pa.detect_currency(t) == attendu, f"obtenu {pa.detect_currency(t)}")
# TOUTE devise non-euro rendue par detect_currency doit être convertible, sinon
# la conversion en euros échoue en silence sur un titre déjà acheté. On teste
# l'invariant plutôt que la liste, pour qu'il tienne au prochain ajout.
# L'ÉCHANTILLON EST DÉRIVÉ DE L'UNIVERS RÉEL, pas écrit à la main. Une liste
# de tickers choisie par le rédacteur du test ne contient jamais le cas qu'il
# n'a pas vu venir : c'est ainsi que .TW et .HK ont manqué jusqu'au 08/08/2026,
# alors qu'un thème allait les introduire. En balayant tous les titres déclarés
# par les thèmes, l'invariant couvre par construction le prochain ajout.
# Les trois symboles ajoutés à la main sont des places que les thèmes ne citent
# pas encore : ils vérifient la détection, pas la couverture.
#
# CORRECTION DU 09/08/2026 — L'ÉCHANTILLON ÉTAIT ENCORE TROP ÉTROIT. Dériver
# des thèmes couvre le prochain ajout THÉMATIQUE, pas le prochain ajout tout
# court : le validateur a signalé CCO.TO (Toronto, CAD) inconnu des quatre
# tables, et cet invariant ne l'a pas vu parce qu'aucun titre de thème ne cote
# au Canada. La source de vérité est donc maintenant la table des places
# elle-même — toute devise que detect_currency PEUT rendre est couverte, qu'un
# titre l'atteigne aujourd'hui ou demain.
_devises = set(pa.SUFFIXES_CONNUS.values()) | {"USD"}
# Et la table des places doit dire vrai : chaque suffixe rend bien la devise
# annoncée. Sinon la garde ci-dessus vérifierait une liste que le code
# n'applique pas.
for _suf, _dev in sorted(pa.SUFFIXES_CONNUS.items()):
    check(f"le suffixe {_suf} est bien lu comme {_dev}",
          pa.detect_currency("XYZ" + _suf) == _dev,
          f"obtenu {pa.detect_currency('XYZ' + _suf)}")
# LE REPLI FINAL EST UN DÉFAUT, PAS UNE DÉDUCTION. `detect_currency` rend "USD"
# pour tout ce qu'elle ne reconnaît pas : juste pour une valeur américaine, faux
# et silencieux pour une place inconnue. Aucun titre manipulé par le projet ne
# doit donc porter un suffixe absent de la table. C'est le test qui aurait
# arrêté CCO.TO à l'écriture plutôt qu'au run de validation.
_manipules = set(themes.univers_thematique()) | set(themes.ECARTES_VALIDATION)
_manipules |= screener.UNIVERS_BASE if hasattr(screener, "UNIVERS_BASE") else set(screener.UNIVERS)
_inconnus = sorted(t for t in _manipules
                   if "." in t and "." + t.rsplit(".", 1)[1] not in pa.SUFFIXES_CONNUS)
check("aucun titre manipulé ne cote sur une place inconnue de la table",
      not _inconnus, str(_inconnus))
_convertibles = _devises - {"EUR", "USD", "GBP"}
# LA TABLE DE REPLI A DISPARU LE 10/08/2026, et ce contrôle ne lui survit qu'à
# moitié : il exigeait « sa paire ET son repli ». Les taux écrits en dur ont été
# retirés — ils étaient servis en silence dès que la source se taisait, et
# `.get(devise, 1.0)` traitait une devise absente comme de l'euro. Le run échoue
# désormais plutôt que d'inventer. Reste l'autre moitié, qui elle est toujours
# vraie et toujours nécessaire : une devise que `detect_currency` sait produire
# doit avoir sa paire de change, sinon la conversion s'arrête sur une devise que
# le projet manipule pour de bon.
check("chaque devise détectée hors EUR/USD/GBP a sa paire de change",
      _convertibles <= set(pa._FX_PAIRS),
      str(sorted(_convertibles - set(pa._FX_PAIRS))))
# LE VALIDATEUR AUSSI convertit des devises, et il l'a payé le 08/08/2026 :
# TWD et HKD avaient été ajoutés à BORNES_PRIX et oubliés dans la table des
# capitalisations, où le défaut silencieux à 1.0 les traitait à la parité du
# dollar. HIWIN ressortait à 136,9 Md$ au lieu de ~4,4 et UBTech à 45,3 au lieu
# de ~5,8 : l'erreur SUPPRIMAIT l'avertissement « sous le seuil des 25 Md$ »,
# c'est-à-dire précisément le contrôle qu'on croyait exercer. Une devise
# détectée par detect_currency doit donc être connue des DEUX tables du
# validateur, sans quoi son garde-fou ment sans le dire.
import validate_tickers as vt   # noqa: E402
check("le validateur borne le prix de chaque devise détectée",
      _devises <= set(vt.BORNES_PRIX),
      str(sorted(_devises - set(vt.BORNES_PRIX))))
check("le validateur sait convertir la capitalisation de chaque devise détectée",
      _devises <= set(vt.CONV_CAP_USD),
      str(sorted(_devises - set(vt.CONV_CAP_USD))))
# Les deux tables du validateur doivent couvrir le même jeu de devises : c'est
# leur divergence, pas leur contenu, qui a produit le bug.
check("les deux tables de devises du validateur couvrent le même jeu",
      set(vt.BORNES_PRIX) <= set(vt.CONV_CAP_USD),
      str(sorted(set(vt.BORNES_PRIX) - set(vt.CONV_CAP_USD))))
# Le code TSE est ambigu (Tokyo vs Toronto) : il ne doit pas décider seul
check("le code marché TSE ne bascule pas en JPY", pa.detect_currency("XYZ", "TSE") != "JPY")

print("\n— Sleep Finnhub —")
_k = screener.FINNHUB_KEY
screener.FINNHUB_KEY = "test"
check("appel émis pour un titre US", screener._finnhub_appel_emis("NVDA"))
check("court-circuit pour un titre japonais", not screener._finnhub_appel_emis("6954.T"))
check("court-circuit pour un titre européen", not screener._finnhub_appel_emis("ASML.AS"))
screener.FINNHUB_KEY = ""
check("aucun appel sans clé", not screener._finnhub_appel_emis("NVDA"))
screener.FINNHUB_KEY = _k

print("\n— Thèmes calculés (mécanisme conservé, aucun publié) —")
check("aucun thème calculé publié", themes.THEMES_CALCULES == [])
check("breakdown vide ne plante pas", themes.themes_calcules_pour({}) == [] and
      themes.themes_calcules_pour(None) == [])
check("breakdown complet ne rattache à rien",
      themes.themes_calcules_pour({"regression_z": -3.0, "qualite": 40}) == [])

print("\n— Union de l'univers achetable —")
universe = {
    "themes": [
        {"id": "ia", "label": "Intelligence artificielle", "scores": 3, "status": "ok",
         "members": ["NVDA", "VRT", "ETN"]},
        {"id": "electrification", "label": "Électrification & réseaux", "scores": 3, "status": "ok",
         "members": ["VRT", "ETN", "NEE"]},
    ],
    "stocks": {
        "NVDA": {"nom": "NVIDIA", "score": 92, "secteur": "Technologie", "market": "NMS",
                 "themes": ["ia"], "prix": 180.0, "devise": "USD", "qualite": 40},
        "VRT": {"nom": "Vertiv", "score": 78, "secteur": "Industrie", "market": "NYQ",
                "themes": ["ia", "electrification"], "prix": 120.0, "devise": "USD"},
        "NEE": {"nom": "NextEra", "score": 70, "secteur": "Services pub.", "market": "NYQ",
                "themes": ["electrification"], "prix": 80.0, "devise": "USD"},
        "SANS": {"nom": "Sans secteur", "score": 88, "secteur": "—", "market": "NYQ",
                 "themes": ["ia"], "prix": 10.0, "devise": "USD"},
    },
}
wl = {"stocks": [{"ticker": "NVDA", "name": "NVIDIA", "sector": "Technologie",
                  "market": "NMS", "score": 92, "breakdown": {"rsi": 52}}]}
fusion = pa.fusionner_univers_achetable(wl, universe)
tick = {s["ticker"] for s in fusion}
check("union du top 30 et des titres thématiques", tick == {"NVDA", "VRT", "NEE"}, tick)
check("un titre sans secteur n'est jamais rendu achetable", "SANS" not in tick)
nvda = next(s for s in fusion if s["ticker"] == "NVDA")
check("le top 30 prime sur la version compacte",
      nvda["origine"] == "top30" and nvda["breakdown"].get("rsi") == 52)
check("le top 30 est enrichi de ses thèmes", nvda["themes"] == ["ia"])
vrt = next(s for s in fusion if s["ticker"] == "VRT")
check("un titre thématique est marqué comme tel", vrt["origine"] == "theme")
check("son breakdown compact est exploitable", vrt["breakdown"]["prix"] == 120.0)
check("univers vide = aucun ajout, pas de plantage",
      len(pa.fusionner_univers_achetable({"stocks": []}, {})) == 0)

print("\n— Concentration thématique —")
positions = [{"ticker": "VRT", "valeur_actuelle": 3000, "sector": "Industrie"},
             {"ticker": "ETN", "valeur_actuelle": 2500, "sector": "Industrie"},
             {"ticker": "NEE", "valeur_actuelle": 2000, "sector": "Services pub."}]
cl = pa.clusters_thematiques(positions, 20000, universe)
elec = next((c for c in cl if c["theme"] == "electrification"), None)
check("une thèse transverse à 2 secteurs est vue comme un bloc",
      elec and elec["pct"] == 37.5, elec)
check("tri par poids décroissant", [c["pct"] for c in cl] == sorted([c["pct"] for c in cl], reverse=True))
check("capital nul ne plante pas", pa.clusters_thematiques(positions, 0, universe) == [])
check("univers absent ne plante pas", pa.clusters_thematiques(positions, 20000, {}) == [])

print("\n— Sérialisation —")
meta = themes.meta_publique()
check("les métadonnées publiques sont sérialisables (pas de callable)",
      json.dumps(meta, ensure_ascii=False, allow_nan=False) and
      all("regle" not in m and "tri" not in m for m in meta))
check("un identifiant par thème dans les métadonnées", len(meta) == len(themes.THEMES))
# ── Éligibilité PEA ─────────────────────────────────────────────────────────
# Le critère est JURIDIQUE, pas mesuré : ces tests protègent une donnée écrite
# à la main, là où le reste du fichier protège du code. C'est justement la
# donnée qui se périme en silence — une redomiciliation ne fait bouger aucun
# cours.
print("\n— Éligibilité PEA —")

pea = themes.THEMES_BY_ID["pea"]
check("le thème PEA est de kind « filtre »", pea["kind"] == "filtre")
check("il publie sa règle en clair", bool(pea.get("regle_texte")))
check("il borne sa liste", pea.get("top") == themes.TOP_PEA == 20)

check("aucun ticker n'est à la fois éligible et inéligible",
      not (set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES)),
      str(sorted(set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES))))
check("chaque éligible porte son pays de siège",
      all(isinstance(v, str) and "·" in v for v in themes.PEA_ELIGIBLES.values()))
check("chaque inéligible porte son motif",
      all(isinstance(v, str) and len(v) > 8 for v in themes.PEA_INELIGIBLES.values()))
check("les tickers du thème sont exactement le registre",
      set(pea["tickers"]) == set(themes.PEA_ELIGIBLES))
check("assez d'éligibles pour que « top 20 » sélectionne vraiment",
      len(themes.PEA_ELIGIBLES) >= 2 * themes.TOP_PEA,
      f"{len(themes.PEA_ELIGIBLES)} éligibles")

# Le piège que ce thème existe pour montrer : une place de cotation américaine
# n'empêche pas l'éligibilité. Si ce test tombe, c'est que quelqu'un a « nettoyé »
# le registre en filtrant sur le suffixe du ticker.
hors_europe = [t for t in themes.PEA_ELIGIBLES if "." not in t]
check("des titres cotés hors d'Europe figurent parmi les éligibles",
      len(hors_europe) >= 5, str(sorted(hors_europe)))
check("Nebius est éligible malgré sa cotation au Nasdaq", "NBIS" in themes.PEA_ELIGIBLES)

# Les inéligibilités qui coûtent cher si on les oublie.
for tk, motif in [("ARM", "Royaume-Uni"), ("HSBA.L", "Royaume-Uni"),
                  ("ABBN.SW", "Suisse"), ("CB", "Suisse")]:
    check(f"{tk} est explicitement écarté ({motif})", tk in themes.PEA_INELIGIBLES)

# Un éligible absent de l'univers scoré ne serait jamais publié : le thème
# afficherait un trou sans que rien ne le signale.
_univers = set(screener.UNIVERS)
absents = sorted(set(themes.PEA_ELIGIBLES) - _univers)
check("tous les éligibles sont dans l'univers scoré", not absents, str(absents))

# ── Bornage et couverture du kind « filtre » ────────────────────────────────
# Reproduit la logique de publication du screener sur des scores simulés, pour
# vérifier les deux propriétés qui se sont contredites à l'écriture : la liste
# est bornée à 20, mais la COUVERTURE se mesure avant bornage — sinon le thème
# serait « dégradé » à chaque run par sa propre définition.
def _publier(scores, top):
    membres = sorted([t for t in pea["tickers"] if t in scores],
                     key=lambda t: (-scores[t], t))
    declares, couverts = len(pea["tickers"]), len(membres)
    return membres[:top], couverts / declares


tous = {t: i for i, t in enumerate(sorted(pea["tickers"]))}
liste, couv = _publier(tous, themes.TOP_PEA)
check("la liste publiée est bornée à 20", len(liste) == 20, str(len(liste)))
check("couverture pleine quand tout est scoré", couv == 1.0, f"{couv:.0%}")
check("triée par score décroissant",
      liste == sorted(liste, key=lambda t: (-tous[t], t)))

moitie = {t: i for i, t in enumerate(sorted(pea["tickers"])[:len(pea["tickers"]) // 2])}
liste2, couv2 = _publier(moitie, themes.TOP_PEA)
check("une panne de source dégrade la couverture", couv2 < 0.70, f"{couv2:.0%}")
check("mais les 20 lignes restent remplies", len(liste2) == 20,
      "le bornage masquerait la panne sans la mesure avant troncature")


# ── Écart à la trajectoire : la formule n'est bornée que d'un côté ──────────
print("\n— Écart à la trajectoire, dans l'unité où il se lit —")
# Un titre SOUS sa tendance ne peut pas l'être de plus de 100 % ; AU-DESSUS,
# aucune limite : Advantest sortait à « surcote tendance 1244 % » (13,4 fois sa
# trajectoire) et 27 fiches sur 95 dépassaient 100 %. Ce nombre entrait tel quel
# dans le prompt de l'agent.
check("une décote normale reste en pourcentage",
      pa._ecart_tendance(28.9).strip() == "décote tendance 29%",
      pa._ecart_tendance(28.9))
check("une surcote normale aussi",
      pa._ecart_tendance(-45.0).strip() == "surcote tendance 45%",
      pa._ecart_tendance(-45.0))
check("au-delà de 100 %, on énonce le MULTIPLE, pas le pourcentage",
      pa._ecart_tendance(-1244.5).strip() == "13.4\u00d7 sa tendance",
      pa._ecart_tendance(-1244.5))
check("la bascule se fait exactement à −100 %",
      "%" in pa._ecart_tendance(-99.9) and "\u00d7" in pa._ecart_tendance(-100.1))
check("aucun écart : aucune mention", pa._ecart_tendance(None) == "")

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)


# ── Éligibilité PEA ─────────────────────────────────────────────────────────
# Le critère est JURIDIQUE, pas mesuré : ces tests protègent une donnée écrite
# à la main, là où le reste du fichier protège du code. C'est justement la
# donnée qui se périme en silence — une redomiciliation ne fait bouger aucun
# cours.
print("\n— Éligibilité PEA —")

pea = themes.THEMES_BY_ID["pea"]
check("le thème PEA est de kind « filtre »", pea["kind"] == "filtre")
check("il publie sa règle en clair", bool(pea.get("regle_texte")))
check("il borne sa liste", pea.get("top") == themes.TOP_PEA == 20)

check("aucun ticker n'est à la fois éligible et inéligible",
      not (set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES)),
      str(sorted(set(themes.PEA_ELIGIBLES) & set(themes.PEA_INELIGIBLES))))
check("chaque éligible porte son pays de siège",
      all(isinstance(v, str) and "·" in v for v in themes.PEA_ELIGIBLES.values()))
check("chaque inéligible porte son motif",
      all(isinstance(v, str) and len(v) > 8 for v in themes.PEA_INELIGIBLES.values()))
check("les tickers du thème sont exactement le registre",
      set(pea["tickers"]) == set(themes.PEA_ELIGIBLES))
check("assez d'éligibles pour que « top 20 » sélectionne vraiment",
      len(themes.PEA_ELIGIBLES) >= 2 * themes.TOP_PEA,
      f"{len(themes.PEA_ELIGIBLES)} éligibles")

# Le piège que ce thème existe pour montrer : une place de cotation américaine
# n'empêche pas l'éligibilité. Si ce test tombe, c'est que quelqu'un a « nettoyé »
# le registre en filtrant sur le suffixe du ticker.
hors_europe = [t for t in themes.PEA_ELIGIBLES if "." not in t]
check("des titres cotés hors d'Europe figurent parmi les éligibles",
      len(hors_europe) >= 5, str(sorted(hors_europe)))
check("Nebius est éligible malgré sa cotation au Nasdaq", "NBIS" in themes.PEA_ELIGIBLES)

# Les inéligibilités qui coûtent cher si on les oublie.
for tk, motif in [("ARM", "Royaume-Uni"), ("HSBA.L", "Royaume-Uni"),
                  ("ABBN.SW", "Suisse"), ("CB", "Suisse")]:
    check(f"{tk} est explicitement écarté ({motif})", tk in themes.PEA_INELIGIBLES)

# Un éligible absent de l'univers scoré ne serait jamais publié : le thème
# afficherait un trou sans que rien ne le signale.
_univers = set(screener.UNIVERS)
absents = sorted(set(themes.PEA_ELIGIBLES) - _univers)
check("tous les éligibles sont dans l'univers scoré", not absents, str(absents))

# ── Bornage et couverture du kind « filtre » ────────────────────────────────
# Reproduit la logique de publication du screener sur des scores simulés, pour
# vérifier les deux propriétés qui se sont contredites à l'écriture : la liste
# est bornée à 20, mais la COUVERTURE se mesure avant bornage — sinon le thème
# serait « dégradé » à chaque run par sa propre définition.
def _publier(scores, top):
    membres = sorted([t for t in pea["tickers"] if t in scores],
                     key=lambda t: (-scores[t], t))
    declares, couverts = len(pea["tickers"]), len(membres)
    return membres[:top], couverts / declares


tous = {t: i for i, t in enumerate(sorted(pea["tickers"]))}
liste, couv = _publier(tous, themes.TOP_PEA)
check("la liste publiée est bornée à 20", len(liste) == 20, str(len(liste)))
check("couverture pleine quand tout est scoré", couv == 1.0, f"{couv:.0%}")
check("triée par score décroissant",
      liste == sorted(liste, key=lambda t: (-tous[t], t)))

moitie = {t: i for i, t in enumerate(sorted(pea["tickers"])[:len(pea["tickers"]) // 2])}
liste2, couv2 = _publier(moitie, themes.TOP_PEA)
check("une panne de source dégrade la couverture", couv2 < 0.70, f"{couv2:.0%}")
check("mais les 20 lignes restent remplies", len(liste2) == 20,
      "le bornage masquerait la panne sans la mesure avant troncature")

total = ok + len(ko)
print(f"\n{ok}/{total} tests passés")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
