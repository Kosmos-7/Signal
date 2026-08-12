#!/usr/bin/env python3
"""Invariants des DONNÉES PUBLIÉES — la suite qui aurait attrapé les bugs du jour.

POURQUOI ELLE EXISTE. Les quatre autres suites testent le CODE sur des données
inventées. Elles passaient toutes, à 100 %, pendant que le site affichait
« sur 100 € de bénéfice comptable, 12 € finissent en cash réel » pour Microsoft,
« chiffre d'affaires en croissance de −33,3 % par an » pour Adyen, et un
bénéfice par action taïwanais projeté en dollars pour TSM. Aucun de ces défauts
n'était un bug de logique : c'étaient des BASES fausses — mauvaise période,
mauvaise devise, mauvaise définition — et une base fausse produit un code qui
marche parfaitement sur un chiffre qui ne veut rien dire.

Cette suite lit ce qui est RÉELLEMENT publié dans le dépôt et vérifie que les
grandeurs sont cohérentes ENTRE ELLES. C'est le seul niveau où une base fausse
se voit : un flux disponible qui ne colle pas à sa marge, une conversion qui ne
colle pas à ses deux termes, un bénéfice projeté sans rapport avec le dernier
publié.

DEUX SÉVÉRITÉS, à dessein :

  · les invariants STRUCTURELS sont des impossibilités logiques (un bloc au-delà
    de son maximum, un multiple négatif publié comme un multiple). Un seul cas
    fait échouer.
  · les SENTINELLES sont des bandes de vraisemblance. Une entreprise réelle
    peut légitimement en sortir — Nebius a vendu une participation et affiche
    93 % de marge nette sur douze mois. On ne fait donc échouer qu'au-delà d'un
    NOMBRE de cas : un titre est une exception, quinze sont une régression.

    python tests/test_donnees.py
"""
import glob
import json
import os
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


def sentinelle(nom, cas, tolerance, total):
    """Échoue quand une bande de vraisemblance est franchie TROP SOUVENT.

    `cas` : liste des titres hors bande. Un titre est une exception qui a le
    droit d'exister ; en franchir `tolerance` est le signe qu'une base a
    changé sous nos pieds."""
    detail = f"{len(cas)}/{total} — {', '.join(str(c) for c in cas[:6])}"
    check(f"{nom} (tolérance {tolerance})", len(cas) <= tolerance, detail)



# ── DÉFAUTS CONNUS : documentés, datés, et qui ne se taisent PAS ─────────────
#
# POURQUOI CE REGISTRE EXISTE. Quatre invariants ont été laissés ROUGES le
# 09/08/2026, au motif honorable qu'ils disaient la vérité sur l'état des
# données. Conséquence : la CI est passée au rouge à CHAQUE push, et le
# propriétaire a reçu une notification d'échec par commit. Une alarme qui sonne
# en permanence n'est plus une alarme — elle ne distingue plus le défaut connu
# de la régression du jour, et on finit par ne plus la lire. C'était une
# mauvaise décision d'ingénierie, pas un choix de rigueur.
#
# LA BONNE FORME EST CELLE QUE LE PROJET UTILISE DÉJÀ (registre ECARTES_
# VALIDATION, sentinelles à tolérance) : on n'éteint pas le contrôle, on NOMME
# ce qu'on sait. Chaque exception porte un motif et le numéro de la tâche qui la
# suit.
#
# ET LE REGISTRE NE PEUT PAS POURRIR : une entrée qui n'apparaît plus dans les
# faits FAIT ÉCHOUER le test à son tour. Sans cette moitié-là, un registre
# devient un cimetière de silencieux — on y ajoute au fil des pannes et on n'en
# retire jamais rien.
CONNUS = {
    "la marge d'exercice vient de la série que le graphique dessine": {
        # CAUSE IDENTIFIÉE le 10/08 : ce n'est pas le changement d'exercice qui
        # tronque la série, c'est le filtre de clôture majoritaire
        # (edgar.filtrer_cloture_majoritaire) qui le prend pour un artefact.
        # L3Harris est passée de juin à décembre à la fusion de 2019 ; les dix
        # exercices juin/juillet font la majorité, donc c'est le NOUVEAU régime
        # qui est écarté. La marge affichée est celle de l'exercice réel, la
        # dernière barre celle de 2019 : l'écart en découle. Tâche #83.
        "LHX": "filtre de clôture majoritaire : le régime post-2019 est écarté "
               "comme un fantôme — tâche #83",
    },
    # Les trois barres fausses de L3Harris, distinctes de la troncature
    # ci-dessus : erreur d'échelle au dépôt XBRL, que la SEC ne corrige pas. La
    # cause exacte (quel concept a produit 102) demande de lire le greffe, que
    # le proxy de développement bloque. Tâche #83.
    "aucun chiffre d'affaires ne plonge d'un ordre de grandeur entre deux "
    "exercices normaux": {
        "LHX": "2010:102, 2011:189, 2013:420 entre 5 005 et 5 012 — erreur "
               "d'échelle au dépôt XBRL, tâche #83",
    },
    # TÂCHE #84 — L'INTERMITTENCE, PRISE SUR LE FAIT LE 12/08/2026. Ces cinq
    # entrées ont été retirées ce matin-là parce que les cinq fiches publiaient
    # leur rendement et que plus aucune du corpus n'en manquait : le contrôle
    # « registre à jour » l'exigeait, et le constat était exact. Une demi-heure
    # plus tard, un run du screener a rendu son rendement à Allianz et l'a repris
    # aux quatre autres. Le défaut ne s'était pas résolu, il avait cligné.
    # LES CINQ RESTENT DONC INSCRITES, y compris celles qui publient à cet
    # instant : la liste nomme les titres que la source sert MAL, pas ceux qui
    # sont en panne à la seconde où le test tourne. Le contrôle est marqué
    # `intermittent` pour cette raison — voir check_connus.
    # ON N'A TOUJOURS RIEN RÉPARÉ, et c'est écrit : le repli du 09/08 (cours ×
    # actions en circulation) n'avait rien changé les 09 et 10/08, donc le nombre
    # d'actions manque aussi quand la capitalisation manque. Lequel des deux
    # revient, on l'ignore encore — tools/sonde_capitalisation.py est là pour le
    # dire, et elle est faite pour ça : elle distingue un champ ABSENT d'un champ
    # PRÉSENT À NULL et interroge trois chemins de la bibliothèque.
    "une fiche qui publie une marge de flux publie aussi son rendement": {
        "ALV.DE": "capitalisation servie par intermittence par la source — tâche #84",
        "MU":     "idem — tâche #84",
        "SAF.PA": "idem — tâche #84",
        "SIE.DE": "idem — tâche #84",
        "WDC":    "idem — tâche #84",
    },
    # Ces textes datent d'AVANT l'entrée des multiples dans la signature : rien ne
    # les réveillait quand le multiple bougeait. Ils seront tous réécrits au
    # prochain run éditorial, et ces entrées devront alors disparaître — le
    # contrôle « registre à jour » s'en assurera.
    # VIDÉS LE 09/08 AU SOIR : le run hebdomadaire a réécrit les textes avec les
    # multiples désormais dans la signature, et les cinq écarts ont disparu.
    # C'est le contrôle « registre à jour » qui l'a exigé — un registre qui ne se
    # vide jamais est un cimetière de silencieux.
    # 2330.TW inscrit le 12/08/2026. La prose citait un PER courant de 32,3 ; la
    # fiche en publie 28,2. CE N'EST PAS UNE DÉRIVE DE COURS, et la distinction
    # compte : entre les deux runs le cours a MONTÉ (2 395 → 2 415) pendant que le
    # multiple chutait de 13 %. Un PER qui baisse quand le prix monte, c'est le
    # bénéfice qui bondit — TSMC a publié entre-temps.
    # C'est donc la péremption structurelle que le projet connaît et n'a pas
    # tranchée : la prose est HEBDOMADAIRE, les chiffres des fiches sont
    # QUOTIDIENS, et un texte qui STOCKE un multiple vieillit dès que la donnée
    # bouge. Le chantier « la prose référence au lieu de stocker » est la seule
    # forme qui rendrait ce défaut impossible plutôt que surveillé ; il attend
    # l'accord du propriétaire. En attendant, l'entrée disparaîtra d'elle-même au
    # prochain run éditorial du lundi, qui réécrit les textes — et le contrôle
    # « registre à jour » exigera alors de la retirer. C'est le comportement voulu.
    "aucun multiple cité ne diverge de la fiche": {
        "2330.TW": "PER courant cité 32,3 vs 28,2 en fiche — résultats publiés "
                   "entre deux runs, texte hebdomadaire non réécrit depuis",
    },
    "aucun texte ne dit indisponible un chiffre que la fiche affiche": {},
    # VIDÉ LE 10/08 : les quinze n'étaient pas inatteignables, c'est le contrôle
    # qui ne regardait pas la watchlist principale. Elles sont le top 30 non
    # tagué par un thème, ouvertes depuis la page d'accueil. Le registre n'avait
    # pas tort de les nommer — il datait d'avant le diagnostic — mais les garder
    # ici aurait fini par légitimer leur suppression. Tâche #85.
    "aucune fiche publiée n'est inatteignable depuis le site": {},
    # CELUI-CI RESTE, et le motif est désormais le bon. Ce ne sont pas des
    # fiches manquantes mais des CHEMINS manquants : une fiche s'adresse
    # `#/w/<watchlist>/<TICKER>` et ces neuf lignes n'appartiennent à aucune
    # watchlist. Le screener ne lit pas portfolio.json, `a_publier` valant
    # `thèmes ∪ top 30` ; mais les ajouter à ce périmètre publierait des
    # fichiers que rien ne pourrait ouvrir. Il manque une route, ou une
    # watchlist « portefeuille » — décision de conception, pas correctif.
    "chaque ligne détenue au portefeuille a sa fiche": {
        t: "détenue hors de toute watchlist : aucune URL de fiche ne la désigne "
           "— tâches #48 et #85"
        for t in ("BLK", "CRM", "DDOG", "JPM", "LLY", "LSEG.L", "NOW",
                  "ORSTED.CO", "SPGI")
    },
}


def check_connus(nom, cas, intermittent=False):
    """Comme check(), mais avec un registre de défauts connus.

    `cas` : dict {clé -> détail lisible}. Échoue sur toute clé absente du
    registre (c'est une régression) ET sur toute entrée du registre qui n'est
    plus constatée (c'est un registre périmé, à nettoyer).

    `intermittent` : le défaut VA ET VIENT, et la moitié « registre périmé » est
    alors désactivée. AJOUTÉ LE 12/08/2026, APRÈS S'ÊTRE FAIT PRENDRE. Les cinq
    capitalisations de la tâche #84 sont apparues COMPLÈTES un matin ; le registre
    a donc été vidé, motif écrit à l'appui — « plus aucune fiche du corpus n'en
    manque », ce qui était vrai à la seconde près. Le run du screener suivant, une
    demi-heure plus tard, en a fait disparaître quatre sur cinq et rendu la
    cinquième. Le motif d'origine disait pourtant exactement ce qu'il fallait
    lire : « rendue par INTERMITTENCE par la source ».
    Pour un défaut de cette nature, l'ensemble observé change à chaque run et la
    garde anti-cimetière se retourne : elle exige de nettoyer un registre qui
    redeviendra vrai au run d'après, et l'alarme sonne en permanence — ce que ce
    fichier reproche par ailleurs à une CI rouge en continu.
    LA MOITIÉ QUI COMPTE RESTE ENTIÈRE : toute occurrence NOUVELLE échoue. On ne
    renonce qu'à exiger la disparition d'un défaut qui, par définition, ne
    disparaît pas franchement.
    """
    connus = CONNUS.get(nom, {})
    nouveaux = {k: v for k, v in cas.items() if k not in connus}
    disparus = [] if intermittent else [k for k in connus if k not in cas]
    if nouveaux:
        check(nom, False, "NOUVEAUX : " + ", ".join(f"{k} ({v})" for k, v in
                                                    list(nouveaux.items())[:5]))
    elif disparus:
        check(f"{nom} — registre à jour", False,
              f"corrigés, à retirer de CONNUS : {disparus}")
    else:
        suffixe = f" ({len(connus)} connu{'s' if len(connus) > 1 else ''}, cf. CONNUS)" if connus else ""
        check(nom + suffixe, True)


FICHES = {}
for _p in sorted(glob.glob("charts/*.json")):
    try:
        FICHES[_p.split("/")[-1][:-5]] = json.load(open(_p, encoding="utf-8"))
    except Exception as e:                       # noqa: BLE001
        ko.append(f"{_p} illisible ({e})")

N = len(FICHES)
print(f"— {N} fiches publiées lues —")
if not N:
    print("Aucune fiche publiée : rien à vérifier (dépôt neuf ou run jamais passé).")
    sys.exit(0)


def crit(b, cid):
    for c in ((b.get("note") or {}).get("criteres") or []):
        if c["id"] == cid:
            return c
    return None


# ── 1. STRUCTURE DE LA NOTE ─────────────────────────────────────────────────
print("\n— La note se recompose-t-elle à partir de son propre détail ? —")
MAXB = {"q": 35, "c": 25, "v": 25, "m": 15}
bad_somme, bad_bloc, bad_crit, bad_max = [], [], [], []
for t, d in FICHES.items():
    n = (d.get("breakdown") or {}).get("note")
    if not n:
        continue
    bl = n.get("blocs") or {}
    # LA SOMME SE COMPARE SUR LA BASE RÉELLEMENT NOTÉE, pas sur cent points.
    # Quand un critère est incalculable il est RETIRÉ et la note se renormalise
    # sur le reste — c'est la doctrine du projet, écrite dans le lexique du site
    # (« un trou de donnée n'est jamais compté zéro »). Tant qu'aucune fiche
    # n'avait perdu un bloc ENTIER, sommer les quatre blocs et comparer au total
    # revenait au même et ce contrôle passait. Quantum Computing Inc. est la
    # première : sans historique exploitable ni estimation, ses quatre critères
    # de croissance tombent, le bloc vaut None, et 13,8 + 11 + 8 = 32,8 pour un
    # total de 44. Les deux nombres sont justes — 32,8 sur les 75 points
    # réellement notés font bien 43,7. C'est l'invariant qui était trop étroit.
    dispo = [k for k in MAXB if (bl.get(k) or {}).get("pts") is not None]
    somme = sum((bl[k] or {}).get("pts") or 0 for k in dispo)
    base = sum(MAXB[k] for k in dispo)
    attendu = somme / base * 100 if base else 0
    if abs(attendu - n["total"]) > 0.6:
        bad_somme.append(f"{t}:{attendu:.1f}≠{n['total']}")
    for k, mx in MAXB.items():
        p = (bl.get(k) or {}).get("pts")
        if p is not None and not (-0.01 <= p <= mx + 0.01):
            bad_bloc.append(f"{t}.{k}={p}")
        if (bl.get(k) or {}).get("max") not in (None, mx):
            bad_max.append(f"{t}.{k}max={bl[k]['max']}")
    for c in n.get("criteres") or []:
        if c.get("pts") is not None and not (-0.01 <= c["pts"] <= c["max"] + 0.01):
            bad_crit.append(f"{t}.{c['id']}={c['pts']}/{c['max']}")
        if c.get("pts") is None and not c.get("motif"):
            bad_crit.append(f"{t}.{c['id']} retiré SANS motif")
check("le total est la somme des blocs renormalisée sur la base notée",
      not bad_somme, str(bad_somme[:4]))
check("aucun bloc hors de son barème", not bad_bloc, str(bad_bloc[:4]))
check("les barèmes de blocs sont ceux de la doctrine (35/25/25/15)",
      not bad_max, str(bad_max[:4]))
check("aucun critère hors de son maximum, aucun retrait sans motif",
      not bad_crit, str(bad_crit[:4]))

# ── 2. LES BASES : chaque ratio recolle-t-il à ses deux termes ? ────────────
print("\n— Les ratios recollent-ils à leurs propres termes ? —")
# La conversion est calculée sur les valeurs BRUTES ; les marges publiées sont
# arrondies au dixième. On tolère donc l'arrondi, amplifié quand le
# dénominateur est petit — mais pas un facteur.
inc = []
for t, d in FICHES.items():
    b = d.get("breakdown") or {}
    c, nm, fm = b.get("conversion_pct"), b.get("net_margin_exercice_pct"), b.get("fcf_margin_pct")
    if c is None or not nm or fm is None or nm <= 0:
        continue
    att = fm / nm * 100
    if att and abs(att - c) / max(abs(c), 1) > 0.30:
        inc.append(f"{t}:{c}vs{att:.0f}")
sentinelle("la conversion recolle à marge FCF / marge nette d'exercice", inc, 8, N)

# Le PER d'un exercice DOIT être le cours de l'époque divisé par le BPA : on ne
# peut pas le revérifier sans le cours, mais on peut vérifier qu'il n'existe
# jamais sans BPA positif, et qu'il n'est jamais négatif.
absurde = []
for t, d in FICHES.items():
    for e in (d.get("fonda") or {}).get("an") or []:
        if e.get("per") is not None:
            if e["per"] <= 0:
                absurde.append(f"{t}/{e['fin'][:4]} PER={e['per']}")
            if not e.get("eps") or e["eps"] <= 0:
                absurde.append(f"{t}/{e['fin'][:4]} PER sans BPA positif")
check("aucun multiple négatif ni sans bénéfice au dénominateur",
      not absurde, str(absurde[:4]))

# Un multiple négatif n'est jamais un multiple, quel qu'il soit.
neg = [f"{t}:{k}={(d.get('breakdown') or {}).get(k)}"
       for t, d in FICHES.items()
       for k in ("trailing_pe", "price_to_book")
       if (d.get("breakdown") or {}).get(k) is not None
       and (d.get("breakdown") or {})[k] <= 0]
check("aucun multiple négatif publié comme un multiple", not neg, str(neg[:4]))

# ── 3. LES DEVISES : le piège qui a produit « TSM projeté à 16,8 » ──────────
print("\n— Les devises : un ordre de grandeur qui saute est un taux de change —")
# LE VRAI PIÈGE est l'ADR : le chiffre d'affaires estimé de Yahoo est en devise
# COMPTABLE, le bénéfice par action estimé en devise de COTATION. Quand les deux
# diffèrent, un rapport aberrant N'EST PAS une croissance, c'est un taux de
# change — TSM publiait 331 TWD et nous en projetions 16,8, soit exactement le
# cours du dollar taïwanais. Là, aucune tolérance.
#
# Quand les deux devises sont ÉGALES, un grand écart est une information
# d'entreprise : Lumentum sort de deux exercices de pertes et le consensus la
# voit à 8,23 après 0,37. Ce n'est pas notre affaire de le censurer.
adr, meme = [], []
for t, d in FICHES.items():
    f = d.get("fonda") or {}
    an, proj = f.get("an") or [], f.get("proj") or []
    der = next((e["eps"] for e in reversed(an) if e.get("eps") and e["eps"] > 0), None)
    prem = next((l["eps"] for l in proj if l.get("eps") is not None and l["eps"] > 0), None)
    if not (der and prem):
        continue
    cot = (d.get("breakdown") or {}).get("devise_cotation")
    est_adr = bool(cot and f.get("devise") and cot != f["devise"])
    r = prem / der
    if est_adr and not (0.2 < r < 5):
        adr.append(f"{t}:{der}→{prem}")
    elif not est_adr and not (0.05 < r < 20):
        meme.append(f"{t}:{der}→{prem}")
check("ADR : le bénéfice projeté reste dans la devise COMPTABLE",
      not adr, str(adr[:4]))
# GARDE ANTI-SOMMEIL. Le test ci-dessus ne vérifie RIEN si la devise de
# cotation n'est pas publiée : `est_adr` serait faux partout et l'invariant
# passerait sans jamais rien regarder. Un test endormi est pire qu'un test
# absent — il rassure. On exige donc le champ sur toute fiche produite par le
# code COURANT (repérée à `conversion_pct`, apparu le même jour) ; les fiches
# figées d'un run antérieur sont exemptées, sans quoi la garde virerait au
# rouge entre la poussée du code et le run qui produit la donnée.
avec = [t for t, d in FICHES.items() if (d.get("breakdown") or {}).get("devise_cotation")]
if not avec:
    # Le champ n'a encore JAMAIS été produit : le code vient d'être poussé et
    # aucun run n'a tourné depuis. On le dit fort plutôt que de faire échouer
    # une intégration continue qui n'y peut rien.
    print("  ⏳ devise de cotation absente de TOUTES les fiches : la garde ADR "
          "dort jusqu'au prochain run du screener")
else:
    manquantes = sorted(set(FICHES) - set(avec))
    check(f"la devise de cotation est publiée partout ({len(avec)}/{N}) "
          "— sans elle la garde ADR ne regarde rien",
          not manquantes, str(manquantes[:6]))
sentinelle("hors ADR, un bond du bénéfice projeté reste un fait d'entreprise",
           meme, 5, N)

saut_ca = []
for t, d in FICHES.items():
    f = d.get("fonda") or {}
    an, proj = f.get("an") or [], f.get("proj") or []
    der = next((e["ca"] for e in reversed(an) if e.get("ca") and e["ca"] > 0), None)
    prem = next((l["ca"] for l in proj if l.get("ca") is not None and l["ca"] > 0), None)
    if der and prem and not (0.3 < prem / der < 12):
        saut_ca.append(f"{t}:{der}→{prem}")
sentinelle("le chiffre d'affaires projeté reste dans l'ordre de grandeur du publié",
           saut_ca, 3, N)

# ── 4. LES PROJECTIONS : le contrat de nature et d'arrêt ────────────────────
print("\n— Les projections disent-elles ce qu'elles sont ? —")
mauvais = []
for t, d in FICHES.items():
    for l in (d.get("fonda") or {}).get("proj") or []:
        for k in ("ca", "eps"):
            nat = l.get(k + "_nature")
            if l.get(k) is not None and nat not in ("consensus", "extrapolé"):
                mauvais.append(f"{t}/{l['exercice']}/{k} nature={nat}")
            # Le cône est mort le 07/08 : une seule courbe, assumée. Ce champ
            # ne doit plus exister NULLE PART — ni sur le consensus, ni sur
            # l'extrapolé. Une fiche non régénérée le trahirait ici.
            if l.get(k + "_haut") is not None:
                mauvais.append(f"{t}/{l['exercice']}/{k} borne haute résiduelle")
            if l.get(k + "_arret") and not l.get(k):
                mauvais.append(f"{t}/{l['exercice']}/{k} motif d'arrêt sans valeur")
check("chaque valeur projetée porte sa nature, aucune borne haute résiduelle",
      not mauvais, str(mauvais[:4]))

# ── LA MARGE AFFICHÉE EST-ELLE CELLE DU GRAPHIQUE D'À CÔTÉ ? ───────────────
# La marge « d'exercice » sortait des états financiers du fournisseur, tandis
# que le graphique des chiffres publiés dessine la série accumulée, qui intègre
# EDGAR et va plus loin. Les deux divergent dès qu'un exercice vient de clore :
# le 09/08/2026, Applied Digital annonçait −160 % (exercice clos en mai 2025)
# au-dessus d'un graphique montrant mai 2026, à −41 %. Deux exercices sur la
# même page, sans que rien ne le dise.
# Deux fiches sur cent vingt-sept, toutes deux à exercice décalé — assez rare
# pour n'avoir jamais été vu, assez faux pour valoir un test permanent.
print("\n— La marge d'exercice est-elle celle du dernier exercice publié ? —")
_decales = {}
for _t, _d in FICHES.items():
    _m = (_d.get("breakdown") or {}).get("net_margin_exercice_pct")
    _an = [e for e in ((_d.get("fonda") or {}).get("an") or [])
           if e.get("ca") and e.get("rn") is not None]
    if _m is None or not _an:
        continue
    _attendu = round(_an[-1]["rn"] / _an[-1]["ca"] * 100, 1)
    if abs(_m - _attendu) > 0.6:
        _decales[_t] = f"{_m} vs {_attendu} ({_an[-1]['fin'][:7]})"
check_connus("la marge d'exercice vient de la série que le graphique dessine",
             _decales)

# ── UN CREUX D'ORDRE DE GRANDEUR QUI SE REFERME EST UNE ERREUR DE TAGAGE ─────
# Trois barres de L3Harris valent 102, 189 et 420 M$ de chiffre d'affaires entre
# des exercices à 5 005 et 5 012 : une erreur d'échelle au dépôt XBRL, que la
# SEC ne corrige pas. Aucun contrôle ne la voyait.
#
# LE GARDE EXISTANT NE POUVAIT PAS LA VOIR : edgar.py écarte un résultat net
# « 100 fois plus petit que ses DEUX voisins », et il n'a pas de symétrique sur
# le chiffre d'affaires. Il serait de toute façon aveugle ici, deux des trois
# valeurs fausses étant voisines l'une de l'autre — une règle de voisinage
# immédiat ne voit pas un creux de trois ans.
#
# CE QUI DISTINGUE L'ERREUR DE LA CROISSANCE, et qui a demandé trois essais :
# comparer chaque CA à la médiane de sa propre série dénonce Meta 2010, Tesla
# 2009-2012, PDD, Regeneron — neuf titres dont la jeunesse est RÉELLE. Une
# société qui grandit ne redescend pas. Le signal n'est donc pas « bas », c'est
# « bas ENTRE DEUX HAUTS » : un creux INTÉRIEUR, encadré des deux côtés par des
# exercices dix fois plus gros. Sur les 148 fiches publiées, cette forme ne
# désigne que L3Harris.
#
# LES ZÉROS SONT HORS SUJET, et c'est écrit plutôt que passé sous silence :
# zéro n'est pas « un ordre de grandeur en dessous », il n'a pas d'échelle. AST
# SpaceMobile publie 0 en 2023 entre 14 et 4 — une société pré-revenu dont le
# chiffre d'affaires est réellement nul cette année-là. La question du zéro est
# celle du trou compté zéro, et elle se traite ailleurs.
def _creux_interieurs(an, facteur=10):
    """Runs de CA strictement positifs, `facteur` fois sous leurs DEUX bornes."""
    ca = [e.get("ca") for e in an]
    res, k, n = [], 1, len(ca)
    while k < n:
        avant = ca[k - 1]
        if not avant or not ca[k] or ca[k] <= 0 or ca[k] * facteur >= avant:
            k += 1
            continue
        deb = k
        while k < n and ca[k] and ca[k] > 0 and ca[k] * facteur < avant:
            k += 1
        apres = ca[k] if k < n else None
        if apres and all(ca[x] * facteur < apres for x in range(deb, k)):
            res.append((deb, k - 1))
    return res


_echelle = {}
for _t, _d in FICHES.items():
    _an = [e for e in ((_d.get("fonda") or {}).get("an") or []) if e.get("ca") is not None]
    for _deb, _fin in _creux_interieurs(_an):
        _echelle[_t] = ", ".join(f"{_an[x]['fin'][:4]}:{_an[x]['ca']}"
                                 for x in range(_deb, _fin + 1))
check_connus("aucun chiffre d'affaires ne plonge d'un ordre de grandeur "
             "entre deux exercices normaux", _echelle)
# Le détecteur se teste lui-même : une sentinelle dont on ne connaît pas les
# fausses alarmes n'est pas une sentinelle. Les formes viennent des titres réels
# sur lesquels les deux premières versions de la règle se sont trompées.
_A = lambda *v: [{"fin": f"20{10 + i:02d}-12-31", "ca": x} for i, x in enumerate(v)]
for _nom, _serie, _attendu in (
    ("un creux intérieur est vu (forme LHX)",          _A(5000, 100, 180, 400, 5100), True),
    ("une croissance réelle ne l'est pas (forme TSLA)", _A(112, 117, 204, 413, 2000), False),
    ("un début de série bas ne l'est pas (forme META)", _A(50, 5000, 5100, 5200), False),
    ("une fin de série basse ne l'est pas",             _A(5000, 5100, 5200, 50), False),
    ("un zéro n'est pas un creux d'échelle (ASTS)",     _A(14, 0, 4), False),
    ("une baisse de moitié n'en est pas un",            _A(5000, 2500, 5100), False),
):
    check(_nom, bool(_creux_interieurs(_serie)) == _attendu)

# ── 5. SENTINELLES DE VRAISEMBLANCE ────────────────────────────────────────
print("\n— Bandes de vraisemblance : une exception est permise, une dérive non —")
# LES DEUX TOLÉRANCES RELEVÉES LE 08/08/2026 le sont pour une raison écrite,
# et non parce qu'elles gênaient. La watchlist robotique fait entrer deux
# fabricants de robots humanoïdes et de cobots, plus un logisticien, dont le
# modèle est le même que celui des sociétés quantiques déjà tolérées ici :
# revenus réels mais bénéfice quasi nul, trésorerie consommée pour financer la
# croissance. Vérifié pièce par pièce contre les comptes publiés avant de
# toucher au seuil — le PER de 6 370 de Rainbow Robotics se retrouve à
# l'identique dans sa série annuelle (BPA 73 wons pour un cours de 465 000), et
# celui de Harmonic Drive tient à un bénéfice de bas de cycle, pas à une erreur
# d'unité. Ce sont des nombres justes portant sur des sociétés que la grille
# mesure mal, ce que le champ `biais` du thème annonce au lecteur.
# RELEVÉES UNE SECONDE FOIS LE 09/08/2026, avec le maillon des bailleurs de
# capacité et les deux thèmes de la veille. Le motif est le même qu'alors et il
# est structurel, pas accidentel : le site suit désormais des sociétés qui
# CONSTRUISENT avant d'encaisser — bailleurs IA en chantier, quantiques sans
# client, fabricants de cobots. Leurs marges sont très négatives et leurs
# multiples très élevés parce que le dénominateur est petit, pas parce qu'une
# base a glissé. Vérifiées une à une contre la série publiée avant de toucher
# au seuil.
# RELEVÉES UNE TROISIÈME FOIS LE 09/08/2026 AU SOIR, à la publication de la
# watchlist spatiale. Dix-neuf sociétés entrent d'un coup, dont une majorité
# construit une constellation ou un lanceur AVANT d'avoir un client : AST
# SpaceMobile affiche −1 682 % de marge de flux et −482 % de marge nette parce
# qu'elle finance des satellites sans chiffre d'affaires, pas parce qu'une base
# a glissé d'un facteur mille. C'est le même motif qu'aux deux relèvements
# précédents, et il est structurel : la population suivie n'est plus celle sur
# laquelle ces bandes ont été calées. Vérifiées une à une contre la série
# publiée — les marges tiennent au dénominateur, jamais à l'unité.
# La sentinelle garde tout son mordant : elle est calée sur le compte EXACT du
# jour, donc le prochain titre qui sortira de la bande la fera tomber.
BANDES = [
    ("marge nette d'exercice", "net_margin_exercice_pct", -60, 70, 13),
    ("marge de flux disponible", "fcf_margin_pct", -60, 70, 14),
    ("conversion du bénéfice en cash", "conversion_pct", -200, 400, 8),
    ("PER courant", "trailing_pe", 1, 200, 10),
    ("rendement des capitaux propres", "roe_pct", -100, 150, 6),
    ("RSI", "rsi", 5, 95, 0),
]
for lib, cle, lo, hi, tol in BANDES:
    hors = [f"{t}:{(d.get('breakdown') or {})[cle]}" for t, d in FICHES.items()
            if (d.get("breakdown") or {}).get(cle) is not None
            and not (lo <= (d.get("breakdown") or {})[cle] <= hi)]
    sentinelle(f"{lib} dans [{lo}, {hi}]", hors, tol, N)

# RUPTURES DE DÉFINITION DANS LA SÉRIE DE CA. Le préambule de ce fichier cite
# « chiffre d'affaires en croissance de −33,3 % par an » pour Adyen ; rien ici
# ne le vérifiait, et la phrase est restée publiée. Le défaut n'est PAS que le
# chiffre baisse — une entreprise réelle recule (Booking en 2020, ASML en 2009,
# Micron en 2023, et ces trois-là sont vraies). Le défaut est le CHANGEMENT DE
# DÉFINITION au milieu de la série : Adyen publie son volume traité en 2022
# (8 936) puis son revenu net à partir de 2023 (1 863), Western Digital publie
# un CA retraité des activités cédées à partir de 2023 (6 255) mais un résultat
# net qui, lui, ne l'est pas. Dans les deux cas nous racontons comme une
# trajectoire d'entreprise ce qui n'est qu'un changement de ligne comptable.
#
# La signature mesurable d'une rupture, et non d'un mauvais exercice : la chute
# n'est PAS suivie d'un retour. Un creux cyclique remonte vers son niveau
# d'avant (Micron 30,8 → 15,5 → 25,1 → 37,4) ; une redéfinition ne remonte
# jamais (Adyen 8 936 → 1 863 → 2 226 → 2 647, la suite entière vit sous la
# moitié du point de départ). C'est ce test-là, et il n'accuse aucun des cas
# légitimes.
print("\n— Le CA garde-t-il la même définition d'un bout à l'autre ? —")
ruptures = []
for _t, _d in FICHES.items():
    _an = [r for r in ((_d.get("fonda") or {}).get("an") or []) if r.get("ca")]
    for _i in range(len(_an) - 1):
        _av, _ap = _an[_i]["ca"], _an[_i + 1]["ca"]
        if _av <= 0 or _ap / _av > 0.5:
            continue
        # tous les exercices suivants restent sous la moitié : pas un creux.
        if all(r["ca"] < _av * 0.5 for r in _an[_i + 1:]):
            ruptures.append(f"{_t}:{_an[_i]['fin'][:4]}→{_an[_i+1]['fin'][:4]}"
                            f" {_av}→{_ap}")
            break
# Tolérance 1 : Adyen est le cas connu, non corrigé (il faudrait une source qui
# distingue volume traité et revenu net, Yahoo ne le fait pas). Western Digital
# est un cas LIMITE que la règle ne réclame pas — son CA remonte à 9 520 en 2025
# contre 18 793 en 2022, soit 124 M au-dessus du seuil de moitié. Le retraitement
# y est réel mais partiellement réversible, et on préfère ne pas l'accuser.
sentinelle("séries de CA sans rupture de définition", ruptures, 1, N)

# POINTS HORS ÉCHELLE DU GRAPHIQUE PER. La fiche écarte de sa règle graduée un
# multiple ISOLÉ — un sommet qui vaut cinq fois le point suivant — parce qu'un
# exercice à bénéfice quasi nul (Cisco 2018, charge fiscale ; Booking 2020,
# covid) écrase toute la courbe même en échelle logarithmique. Le point reste
# dessiné, avec sa valeur écrite ; seule la graduation l'ignore.
#
# Ce que ce test protège n'est PAS le seuil, c'est ce que le seuil ne doit
# jamais toucher : une société durablement chère. ARM vit à 175–431×, Equinix à
# 56–200×, Netflix à 19–288× — leurs multiples élevés ont des voisins, ce sont
# de vraies valorisations. Si l'une d'elles se met à sortir du cadre, la règle
# a cessé de distinguer l'accident de la trajectoire.
print("\n— Le graphique PER n'écarte-t-il que des accidents isolés ? —")


def _hors_echelle(pub, seuil=5, maxi=2):
    """Réplique de la règle du front : épluche par le haut tant que le sommet
    vaut `seuil` fois le point suivant, `maxi` exercices au plus.

    Sur les seuls exercices PUBLIÉS : une estimation n'est jamais un accident
    comptable passé, et le multiple prévisionnel est ce que le lecteur vient
    chercher — il ne sort jamais du cadre."""
    s = sorted(pub)
    ecartes = []
    while len(s) >= 4 and len(ecartes) < maxi and s[-2] > 0 and s[-1] / s[-2] >= seuil:
        ecartes.append(s.pop())
    return ecartes


FD_ANS = 10                       # même fenêtre dessinée que la fiche
ecarte_par = {}
for _t, _d in FICHES.items():
    _f = _d.get("fonda") or {}
    _pub = [r["per"] for r in (_f.get("an") or [])[-FD_ANS:] if r.get("per") is not None]
    if len(_pub) < 2:
        continue
    _e = _hors_echelle(_pub)
    if _e:
        ecarte_par[_t] = [round(v) for v in _e]
check("aucune fiche ne voit deux exercices sortir du cadre",
      all(len(v) == 1 for v in ecarte_par.values()), str(ecarte_par))
DURABLEMENT_CHERES = ["ARM", "EQIX", "NFLX", "NBIS", "CDNS", "ADBE"]
touchees = [t for t in DURABLEMENT_CHERES if t in ecarte_par]
check("aucune société durablement chère n'est écartée", not touchees, str(touchees))
sentinelle("fiches avec un multiple hors échelle", sorted(ecarte_par), 9, N)

# Un critère mesuré pour presque personne ne mesure rien : la couverture d'un
# critère est elle-même une donnée à surveiller.
print("\n— Couverture des critères : un critère rarement mesuré est un critère mort —")
compte = {}
for t, d in FICHES.items():
    for c in ((d.get("breakdown") or {}).get("note") or {}).get("criteres") or []:
        v = compte.setdefault(c["id"], [0, 0])
        v[1] += 1
        if c.get("pts") is not None:
            v[0] += 1
# Les critères de substitution des métiers de bilan ne concernent qu'une poignée
# de titres : ils sont exclus de la garde, leur rareté est voulue.
BILAN = {"rendement_actifs", "levier_actifs", "actifs_nets"}
faibles = [f"{c}:{v[0]}/{v[1]}" for c, v in compte.items()
           if c not in BILAN and v[1] >= 20 and v[0] / v[1] < 0.60]
check("chaque critère généraliste est mesuré pour au moins 60 % des titres",
      not faibles, str(faibles))

# CHAQUE TROU DOIT AVOIR UNE RAISON, et les raisons se vérifient sur les données.
# Ces gardes-ci ne demandent pas qu'un champ soit toujours là : elles demandent
# que son absence soit COHÉRENTE avec ce que la fiche publie par ailleurs. Une
# absence qui contredit le reste de la fiche est un défaut de collecte déguisé
# en donnée manquante — c'est ainsi que douze fiches ont perdu leur rendement du
# flux disponible pendant des semaines, sept par différence de devise et cinq
# parce que le fournisseur ne renvoyait pas de capitalisation.
# BAE Systems est la seule exception, et elle est ÉCRITE. Elle cote en pence
# quand ses comptes sont en livres, et le fournisseur mélange les deux unités —
# cours en pence, capitalisation en livres. Convertir a été essayé le 09/08 et
# retiré le jour même : le rendement sortait à 358 %. Tant que chaque grandeur
# n'aura pas été mesurée une à une, le trou est la bonne réponse.
_UNITE_AMBIGUE = {"BA.L"}
_sans_rdt = [t for t, d in FICHES.items()
             if t not in _UNITE_AMBIGUE
             and (d.get("breakdown") or {}).get("fcf_margin_pct") is not None
             and (d.get("breakdown") or {}).get("fcf_yield_pct") is None]
check_connus("une fiche qui publie une marge de flux publie aussi son rendement",
             {t: "marge publiée, rendement absent" for t in _sans_rdt},
             # La source sert ces capitalisations un run sur deux : l'ensemble
             # observé change d'une exécution à l'autre, et exiger qu'il soit
             # exactement celui du registre ferait rougir la CI en permanence
             # pour un défaut déjà nommé. Cf. check_connus et la tâche #84.
             intermittent=True)
# Un multiple prévisionnel retiré pour cause de devise ne doit l'être QUE là où
# la devise pose vraiment question : une société déficitaire n'a pas de PER
# prévisionnel pour une raison qui n'a rien à voir, et le motif serait faux.
_faux_motif = [t for t, d in FICHES.items()
               if (d.get("fonda") or {}).get("pe_prev_indecis")
               and ((d.get("fonda") or {}).get("devise")
                    == ((d.get("breakdown") or {}).get("devise_cotation")))]
check("l'abstention sur devise ne vise que des fiches en devises différentes",
      not _faux_motif, str(_faux_motif))
# Un bénéfice par action reconstitué doit rester encadré : la règle ne comble
# que les trous intérieurs, jamais le premier ni le dernier exercice.
_derives_au_bord = []
for t, d in FICHES.items():
    _an = (d.get("fonda") or {}).get("an") or []
    for i, e in enumerate(_an):
        if e.get("eps_derive") and (i == 0 or i == len(_an) - 1):
            _derives_au_bord.append(f"{t}:{e['fin'][:4]}")
check("aucun bénéfice reconstitué au bord de la série",
      not _derives_au_bord, str(_derives_au_bord))
# Et aucun reconstitué à zéro : un résultat net absent est rendu `0` par la
# source, et le diviser publiait « cette société n'a rien gagné » — Arista 2021,
# 840 M$ de bénéfice réel, affichait 0,0.
_derives_nuls = [f"{t}:{e['fin'][:4]}" for t, d in FICHES.items()
                 for e in ((d.get("fonda") or {}).get("an") or [])
                 if e.get("eps_derive") and not e.get("eps")]
check("aucun bénéfice reconstitué à zéro", not _derives_nuls, str(_derives_nuls))

# ── 6. COHÉRENCE ENTRE LES FICHIERS PUBLIÉS ────────────────────────────────
print("\n— Les fichiers publiés racontent-ils la même histoire ? —")
try:
    U = json.load(open("universe.json", encoding="utf-8"))["stocks"]
    W = {s["ticker"]: s for s in json.load(open("watchlist.json", encoding="utf-8"))["stocks"]}
except Exception as e:                           # noqa: BLE001
    U, W = {}, {}
    ko.append(f"universe/watchlist illisibles ({e})")
ecarts = [f"{t}:{U[t]['score']}vs{FICHES[t]['breakdown']['note']['total']}"
          for t in U if t in FICHES
          and (FICHES[t].get("breakdown") or {}).get("note")
          and abs(U[t]["score"] - FICHES[t]["breakdown"]["note"]["total"]) > 0.51]
check("le score de l'univers est celui de la fiche", not ecarts, str(ecarts[:4]))
manque = sorted(set(W) - set(FICHES))
check("chaque titre de la watchlist a sa fiche", not manque, str(manque))
# Les fiches orphelines ne sont pas une erreur en soi, mais leur nombre dit
# combien de données figées le dépôt transporte.
orph = sorted(set(FICHES) - set(U))
sentinelle("fiches publiées sans entrée dans l'univers (données figées)",
           orph, 25, N)

# ── 7. L'ÉDITORIAL NE RECOPIE PAS LE TABLEAU DE BORD ───────────────────────
print("\n— L'éditorial recopie-t-il des chiffres qui bougent chaque semaine ? —")
# Le 07/08/2026 : 104 résumés sur 104 citaient le score en toutes lettres, 73
# citaient un score PÉRIMÉ (NVIDIA « 74/100 » sous un anneau affichant 86) et 78
# un barème v3 (« qualité 39/45, timing 9/22 ») disparu depuis la v4. Un texte
# qui recopie un tableau de bord ment dès que le tableau de bord bouge.
import re                                              # noqa: E402
try:
    ANALYSES = json.load(open("analyses.json", encoding="utf-8"))
except Exception:                                      # noqa: BLE001
    ANALYSES = {}
cite_score, cite_bareme = [], []
for t, a in ANALYSES.items():
    for k, v in a.items():
        if k.startswith("_") or not v:
            continue
        txt = v if isinstance(v, str) else " ".join(str(x) for x in v)
        if re.search(r"\d{1,3}\s*/\s*100", txt):
            cite_score.append(f"{t}.{k}")
        if re.search(r"\d{1,3}\s*/\s*(?:45|30|22|35|25|15)\b", txt):
            cite_bareme.append(f"{t}.{k}")
check(f"aucune analyse ne recopie le score ({len(ANALYSES)} lues)",
      not cite_score, str(cite_score[:6]))
# DETTE DATÉE, mesurée et assumée. 46 citations d'un sous-score v3 (« qualité
# 42/45 », « valorisation 10/30 ») subsistent dans les rubriques bull, bear et
# futur. Contrairement aux résumés, elles ne sont PAS réécrivables à la machine :
# le chiffre y porte le jugement de l'auteur, et le remplacer par un
# qualificatif déduit de la fraction produit des contresens — « le score de
# qualité SOLIDE indique que les fondamentaux ne valident pas la valorisation »
# était le résultat de l'essai. Elles disparaîtront au prochain run éditorial
# complet, sous le prompt qui interdit désormais de recopier la note. La
# tolérance ne doit donc que DESCENDRE : si elle remonte, c'est que le garde du
# générateur a lâché.
sentinelle("citations d'un sous-score v3 restant dans bull/bear/futur",
           cite_bareme, 48, len(ANALYSES) or 1)

# MÊME MALADIE, AUTRE HORLOGE. Le score ne bouge qu'au run hebdomadaire ; le RSI et
# le drawdown 52 semaines, eux, sont recalculés à CHAQUE rafraîchissement des cours,
# tous les jours. Un « RSI à 30 » écrit dans un texte qui n'est réécrit que si le
# score, le croisement ou le z-score changent est donc périmé en quelques séances :
# mesuré le 08/08/2026, 37 citations de RSI et 15 de drawdown, dont aucune inventée
# et la quasi-totalité désynchronisée de la fiche. Le générateur fournit désormais
# les deux grandeurs marquées « NE PAS CHIFFRER » et l'interdit explicitement.
# Ces deux tolérances ne doivent que DESCENDRE : si elles remontent, le garde a lâché.
cite_rsi, cite_dd = [], []
for t, a in ANALYSES.items():
    for k, v in a.items():
        if k.startswith("_") or not v:
            continue
        txt = v if isinstance(v, str) else " ".join(str(x) for x in v)
        if re.search(r"RSI[^.;)]{0,25}?\d", txt):
            cite_rsi.append(f"{t}.{k}")
        if re.search(r"drawdown[^.;]{0,25}?[-–]?\s?<?b?>?\s?\d", txt, re.I):
            cite_dd.append(f"{t}.{k}")
check("le générateur interdit de chiffrer RSI et drawdown",
      "NE PAS CHIFFRER" in open("generate_analyses.py", encoding="utf-8").read(), "")
sentinelle("citations chiffrées du RSI (recalculé chaque jour)",
           cite_rsi, 37, len(ANALYSES) or 1)
sentinelle("citations chiffrées du drawdown 52s (recalculé chaque jour)",
           cite_dd, 15, len(ANALYSES) or 1)

# ── 8. LE TEXTE PUBLIÉ EST-IL CELUI DE LA SOURCE ? ─────────────────────────
# universe.json est un ARTEFACT : le screener le régénère depuis themes.py à
# chaque run. Entre deux runs, une correction de texte dans themes.py ne se voit
# donc PAS sur le site — et rien ne le disait. Constaté le 08/08/2026 : le
# libellé « Pure-players · leur seul métier » a été corrigé dans la source
# (IonQ a racheté une fonderie, ce n'est plus son seul métier) et le site a
# continué de l'afficher, tests au vert. Ce contrôle-là ne coûte rien et ferme
# l'écart : il échoue tant que l'artefact n'a pas rattrapé sa source.
print("\n— Le texte affiché est-il celui de themes.py ? —")
sys.path.insert(0, RACINE)
import themes                                              # noqa: E402
_pub = {t["id"]: t for t in themes.meta_publique()}
_ecarts = []
try:
    _themes_publies = json.load(open("universe.json", encoding="utf-8")).get("themes", [])
except Exception:                                          # noqa: BLE001
    _themes_publies = []
for _t in _themes_publies:
    _m = _pub.get(_t["id"])
    if not _m:
        _ecarts.append(f"{_t['id']} : publié mais absent de themes.py")
        continue
    for _k, _v in _m.items():
        if _k in _t and _t[_k] != _v:
            _ecarts.append(f"{_t['id']}.{_k}")
check("universe.json publie exactement les textes de themes.py",
      not _ecarts, str(_ecarts[:4]))
# LA BOUCLE CI-DESSUS NE REGARDE QUE DANS UN SENS : elle compare les thèmes
# PUBLIÉS à leur source. Un thème déclaré dans themes.py et absent de
# l'artefact — parce qu'aucun run n'a eu lieu depuis son ajout — passait donc
# inaperçu, alors que c'est le mode de panne le plus coûteux des deux : la
# watchlist existe dans le code, ses tests sont au vert, et le site ne la montre
# pas. Constaté en ajoutant le thème robotique le 08/08/2026, quelques minutes
# après avoir fermé l'écart symétrique.
# Ce contrôle échoue légitimement entre l'ajout d'un thème et le run qui le
# publie : c'est ce qu'il doit dire, et le remède est de lancer le screener.
_absents = sorted(set(_pub) - {t["id"] for t in _themes_publies})
check("chaque thème déclaré est réellement publié dans universe.json",
      not _absents, f"jamais publiés (lancer le screener) : {_absents}")

# ── 9. LE TEXTE DIT-IL LES MÊMES CHIFFRES QUE LA FICHE ? ─────────────────────
print("\n— La prose et les chiffres racontent-ils la même chose ? —")
# LE DÉFAUT QUE CE TEST EXISTE POUR ATTRAPER. Le guide de rédaction impose de
# chiffrer toute affirmation de valorisation ; la signature éditoriale, qui
# décide des réécritures, ignorait ces mêmes multiples. Un texte pouvait donc
# citer un PER qui bougeait sous lui sans jamais être réécrit. Samsung annonçait
# « PER forward 4,0× (PER courant indisponible) » quand la fiche affichait 3,4×
# et un PER courant de 35,0× — le texte affirmait au lecteur qu'un chiffre
# n'existait pas alors qu'il était affiché juste au-dessus.
#
# La correction est dans generate_analyses.py (les multiples entrent dans la
# signature, par paliers). Ce test-ci est la GARDE : il relit les nombres de la
# prose PUBLIÉE et les confronte à la fiche. Il est volontairement grossier —
# quelques tournures, pas toutes — parce qu'un test qui attrape la moitié des
# cas vaut infiniment mieux que la relecture humaine qui n'en attrapait aucun.
import re as _re
_INTER = r"\s*(?:de |à |:)?\s*(?:<[^>]+>\s*)?"
_MOTIFS = [
    # LES TOURNURES COMPTENT AUTANT QUE LES SEUILS, et il a fallu DEUX essais.
    # Le premier jet n'acceptait que « PER forward 15,6x » ; NVIDIA écrit « le PER
    # forward de 15,6x » et passait à travers — c'est le propriétaire qui a vu le
    # chiffre, pas le test. Le deuxième acceptait « de » mais pas la balise <b>
    # dont la prose entoure chaque nombre, et ratait donc encore NVIDIA. C'est le
    # contrôle « registre à jour » qui l'a dit : une entrée inscrite mais jamais
    # constatée signalait que le test ne voyait rien. Un registre qui refuse les
    # fantômes vérifie aussi le test lui-même.
    (_re.compile(r"PER forward" + _INTER + r"(\d+[,.]?\d*)"),        "forward_pe",   0.10),
    (_re.compile(r"PER pr[ée]visionnel" + _INTER + r"(\d+[,.]?\d*)"), "forward_pe",   0.10),
    (_re.compile(r"PER courant" + _INTER + r"(\d+[,.]?\d*)"),         "trailing_pe",  0.10),
    (_re.compile(r"marge nette (?:de |à )?(\d+[,.]?\d*)\s*%"),  "net_margin_pct", 0.20),
]
_perimes, _lus = {}, 0
for _t, _e in (ANALYSES.items() if isinstance(ANALYSES, dict) else []):
    if not isinstance(_e, dict):
        continue
    _txt = json.dumps(_e, ensure_ascii=False)
    _b = (FICHES.get(_t) or {}).get("breakdown") or {}
    for _rx, _cle, _tol in _MOTIFS:
        for _m in _rx.finditer(_txt):
            _lus += 1
            _v = float(_m.group(1).replace(",", "."))
            _ref = _b.get(_cle)
            if _ref is None or _ref == 0:
                continue
            if abs(_v - _ref) / abs(_ref) > _tol:
                _perimes[_t] = f"{_cle} : texte {_v} vs fiche {round(_ref, 1)}"
print(f"  ({_lus} nombres lus dans la prose publiée)")
check_connus("aucun multiple cité ne diverge de la fiche", _perimes)
# Et l'inverse, plus insidieux : le texte déclare un chiffre INDISPONIBLE alors
# que la fiche l'affiche. C'est le cas exact de Samsung, et aucun contrôle de
# valeur ne l'aurait vu puisqu'il n'y a pas de nombre à comparer.
_absents = {}
for _t, _e in (ANALYSES.items() if isinstance(ANALYSES, dict) else []):
    if not isinstance(_e, dict):
        continue
    _txt = json.dumps(_e, ensure_ascii=False)
    _b = (FICHES.get(_t) or {}).get("breakdown") or {}
    for _lib, _cle in (("PER courant indisponible", "trailing_pe"),
                       ("PER forward indisponible", "forward_pe")):
        if _lib in _txt and _b.get(_cle) is not None:
            _absents[_t] = f"« {_lib} » mais la fiche affiche {_b[_cle]}"
check_connus("aucun texte ne dit indisponible un chiffre que la fiche affiche",
             _absents)

# LES PALIERS DE VALORISATION, éprouvés sur la fonction elle-même. Le pas est
# calé sur la TOLÉRANCE DU TEST ci-dessus, et ce couplage est le cœur du
# dispositif : tout écart que ce test signalerait a, par construction, déjà
# changé le palier — donc déclenché une réécriture. Si les deux se désaccordent,
# on retrouve la situation d'avant, un texte périmé qu'aucune règle ne réveille.
try:
    # LES BOUCHONS D'ABORD. generate_analyses.py importe `anthropic`, que le
    # runner n'installe pas — cette suite se contentait jusqu'ici de lire du
    # JSON et n'en avait jamais eu besoin. Sans cette ligne, le contrôle des
    # paliers échouait en intégration continue tout en passant en local : la
    # panne même qu'on vient de corriger sur PIL, reproduite le jour même par
    # celui qui la corrigeait.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _bouchons
    _bouchons.poser()
    import importlib.util as _u
    _sp = _u.spec_from_file_location("_ga", "generate_analyses.py")
    _ga = _u.module_from_spec(_sp)
    _sys_mod = __import__("sys").modules
    _sys_mod["_ga"] = _ga
    _sp.loader.exec_module(_ga)
except Exception as _e:                                       # noqa: BLE001
    check("generate_analyses.py est importable", False, f"{type(_e).__name__}: {_e}")
else:
    check("le pas des multiples est celui de la tolérance du test",
          dict((c, p) for c, _m, p in _ga.CHAMPS_VALO)["forward_pe"] == 0.10)
    _base = {"forward_pe": 20.0, "trailing_pe": 30.0,
             "fcf_yield_pct": 4.0, "net_margin_pct": 22.0}
    _s0 = _ga.bucket_valorisation(_base)
    check("un multiple stable garde son palier",
          _ga.bucket_valorisation({**_base, "forward_pe": 20.4}) == _s0)
    check("un multiple qui double change de palier",
          _ga.bucket_valorisation({**_base, "forward_pe": 40.0}) != _s0)
    check("une marge qui bouge de dix points change de palier",
          _ga.bucket_valorisation({**_base, "net_margin_pct": 32.0}) != _s0)
    check("un multiple absent ou négatif ne fait pas exploser la fonction",
          _ga.bucket_valorisation({"forward_pe": None, "trailing_pe": -3.0})[:2]
          == ["na", "neg"])
    check("les deux niveaux de fiche ont désormais le même socle de rubriques",
          _ga.CHAMPS_PAR_NIVEAU[_ga.NIVEAU_COMPLET]
          == _ga.CHAMPS_PAR_NIVEAU[_ga.NIVEAU_THEMATIQUE])

# ── 10. AUCUNE FICHE ORPHELINE, AUCUNE POSITION ORPHELINE ───────────────────
print("\n— Chaque fiche publiée est-elle atteignable, chaque ligne détenue a-t-elle sa fiche ? —")
# DEUX TROUS SYMÉTRIQUES relevés le 09/08/2026 — dont UN SEUL était réel.
#
# UNE FICHE N'EXISTE QUE DANS UNE WATCHLIST. Le front route sur
# `#/w/<watchlist>/<TICKER>` : l'adresse d'une fiche porte la liste qui la
# contient. Les chemins du site sont donc les watchlists — la principale
# (watchlist.json, top 30) ET les thématiques (universe.json) — et le périmètre
# de publication du screener dit exactement la même chose, `a_publier` valant
# `thèmes ∪ top 30`.
#
# CE CONTRÔLE OUBLIAIT LA WATCHLIST PRINCIPALE, donc la page d'accueil. Les
# quinze fiches qu'il dénonçait comme inatteignables étaient les membres du top
# 30 non tagués par un thème : republiées à chaque run, ouvertes d'un clic
# depuis la page principale. La purge de `publier_charts` ne les avait pas
# « épargnées » — elle est totale, tout .json non réécrit disparaît ; elles
# étaient là parce qu'elles avaient leur place. Les supprimer aurait vidé le top
# 30 de ses graphes et de quinze textes éditoriaux payés à l'API.
#
# LE SECOND TROU, LUI, EST RÉEL et le registre le garde : neuf lignes détenues
# n'appartiennent à AUCUNE watchlist, donc aucune URL de fiche ne peut les
# désigner. Leur donner un fichier dans charts/ ne les rendrait pas atteignables
# pour autant — il manque un chemin, pas un fichier. Cf. CONNUS.
try:
    _U = json.load(open("universe.json", encoding="utf-8"))
    _st = _U["stocks"]
    _publies = set(_st) if isinstance(_st, dict) else {x["c"] for x in _st if isinstance(x, dict)}
    for _th in _U.get("themes") or []:
        _publies |= set(_th.get("members") or [])
except Exception:                                            # noqa: BLE001
    _publies = set(FICHES)
try:
    _W = json.load(open("watchlist.json", encoding="utf-8"))
    _publies |= {x["ticker"] for x in (_W.get("stocks") or []) if isinstance(x, dict)}
except Exception:                                            # noqa: BLE001
    _publies = set(FICHES)
try:
    _P = json.load(open("portfolio.json", encoding="utf-8"))
    _detenues = {x["ticker"] for x in (_P.get("positions") or []) if isinstance(x, dict)}
except Exception:                                            # noqa: BLE001
    _detenues = set()
check_connus("aucune fiche publiée n'est inatteignable depuis le site",
             {t: "ni watchlist principale, ni thème, ni portefeuille"
              for t in sorted(set(FICHES) - _publies - _detenues)})
check_connus("chaque ligne détenue au portefeuille a sa fiche",
             {t: "position ouverte sans fiche" for t in sorted(_detenues - set(FICHES))})

# ── 11. LES ILLUSTRATIONS : UNE OBLIGATION LÉGALE, ET AUCUN CADRE CASSÉ ─────
print("\n— Les illustrations tiennent-elles leurs promesses ? —")
# RIEN NE VÉRIFIAIT CECI, et l'une des trois est une obligation légale, pas une
# préférence : le front n'affiche l'attribution que si le champ `credit` existe
# (« const cr=P.credit?… »), et les licences CC-BY et CC-BY-SA l'EXIGENT. Une
# entrée sous CC-BY sans crédit publierait une photo en violation de sa licence,
# en silence, sans que rien ne casse à l'écran.
#
# LES DEUX ENSEMBLES DOIVENT COÏNCIDER. Une légende sans image affiche un cadre
# vide, une image sans légende n'est jamais rendue — le front sort avant
# (« if(!P) return '' »), et l'octet téléchargé l'a été pour rien. Le contrôle
# ne les rattache PAS aux fiches : `assets/titres/` n'est pas purgé quand
# `charts/` l'est, et c'est voulu — le top 30 tourne, et une illustration
# conservée évite de re-solliciter la source quand le titre revient.
try:
    _LEG = {k: v for k, v in json.load(
        open("assets/titres/LEGENDES.json", encoding="utf-8")).items()
        if isinstance(v, dict)}
except Exception as _e:                                      # noqa: BLE001
    _LEG = {}
    ko.append(f"assets/titres/LEGENDES.json illisible ({_e})")
_JPG = {os.path.basename(p)[:-len(".jpg")] for p in glob.glob("assets/titres/*.jpg")}
check("chaque illustration a son image ET sa légende",
      set(_LEG) == _JPG,
      f"image sans légende : {sorted(_JPG - set(_LEG))[:5]} · "
      f"légende sans image : {sorted(set(_LEG) - _JPG)[:5]}")
# « BY » dans le nom de la licence = paternité exigée. La règle se lit sur les
# licences RÉELLEMENT présentes (CC BY 2.0/2.5/3.0/4.0, CC BY-SA 2.0/3.0/4.0,
# « CC BY-SA 3.0 de »), et laisse dehors celles qui ne l'exigent pas — domaine
# public, CC0, marque du domaine public.
_sans_credit = sorted(t for t, v in _LEG.items()
                      if "BY" in (v.get("licence") or "").upper() and not v.get("credit"))
check("toute licence exigeant la paternité porte son crédit",
      not _sans_credit, str(_sans_credit))
# Le nom du fichier d'origine est la SEULE pièce qui permette de vérifier qu'une
# vignette illustre bien la société : quatre fois une image plausible s'est
# révélée être le produit d'un concurrent (carte Supermicro pour Astera Labs,
# boîtier Netgear pour Fortinet, bras Universal Robots pour Doosan, caméra IDS
# pour Cognex). Sans ce champ, la vérification n'est plus possible du tout.
_sans_source = sorted(t for t, v in _LEG.items() if not v.get("source"))
check("chaque illustration nomme son fichier source", not _sans_source, str(_sans_source))

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
