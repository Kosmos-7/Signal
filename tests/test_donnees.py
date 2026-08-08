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
    somme = sum((bl.get(k) or {}).get("pts") or 0 for k in MAXB)
    if abs(somme - n["total"]) > 0.51:
        bad_somme.append(f"{t}:{somme:.1f}≠{n['total']}")
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
check("le total est la somme des blocs, à l'arrondi près", not bad_somme, str(bad_somme[:4]))
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

# ── 5. SENTINELLES DE VRAISEMBLANCE ────────────────────────────────────────
print("\n— Bandes de vraisemblance : une exception est permise, une dérive non —")
BANDES = [
    ("marge nette d'exercice", "net_margin_exercice_pct", -60, 70, 6),
    ("marge de flux disponible", "fcf_margin_pct", -60, 70, 6),
    ("conversion du bénéfice en cash", "conversion_pct", -200, 400, 8),
    ("PER courant", "trailing_pe", 1, 200, 4),
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

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + ", ".join(ko))
sys.exit(1 if ko else 0)
