"""EDGAR — l'historique OFFICIEL des chiffres publiés, pour les sociétés US.

POURQUOI cette source s'ajoute à Yahoo (décision propriétaire du 06/08/2026,
après relecture critique du flux des fondamentaux) :
  · Yahoo ne conserve que ~4 exercices et ~5 trimestres ; les variations
    trimestrielles « vs même trimestre N-1 » restaient donc cantonnées à la
    dernière ligne pendant un an, le temps que notre accumulateur se remplisse.
    Les dépôts 10-K/10-Q remontent à plus de dix ans, immédiatement.
  · Ce n'est pas un troisième vendeur : c'est le greffe de la SEC, le document
    déposé par la société sous responsabilité légale — la matière première que
    Yahoo et Finnhub retraitent.

CE QUE CE MODULE NE FAIT PAS, à dessein :
  · il n'ÉCRASE jamais une valeur Yahoo : il n'ajoute que les dates absentes
    (les deux bases peuvent différer sur les retraitements, on ne mélange pas
    silencieusement) — chaque entrée ajoutée porte src:"edgar".

IFRS (v2, 06/08/2026 — chantier « historique profond ») : les émetteurs
ÉTRANGERS déposent aussi à la SEC, en 20-F/40-F sous la taxonomie ifrs-full
et dans leur devise comptable d'origine (SAP en euros, Sony en yens, TSMC en
dollars taïwanais). L'exclusion v1 (« leurs concepts us-gaap sont vides »)
est levée : quand us-gaap ne rend rien, on relit les mêmes séries sous
ifrs-full, dans l'unité de la devise comptable annoncée par Yahoo — jamais
une autre, pour ne pas mélanger deux monnaies dans un même historique.
C'est la moitié du chantier « historique profond » : la source reste le
greffe officiel, aucune asymétrie de fiabilité n'est introduite — seuls les
non-déposants (Samsung, les domestiques japonaises, Hermès…) relèvent de
l'autre moitié (apport vérifié, cf. screener).

MÉCANIQUE : companyconcept (un petit JSON par balise) plutôt que companyfacts
(jusqu'à 15 Mo par société). Seuls les faits porteurs d'un « frame » sont lus :
c'est la vue DÉDUPLIQUÉE par la SEC (un même trimestre est redéposé dans
plusieurs rapports ; le frame n'existe qu'une fois). Le Q4 n'est jamais déposé
en durée trimestrielle : il est DÉRIVÉ (exercice − Q1 − Q2 − Q3), pour le CA et
le résultat net seulement — jamais le BPA, qui n'est pas additif (le nombre
d'actions bouge en cours d'année).

Le tagage XBRL est fait par l'émetteur et la SEC ne le corrige pas : les
montants aberrants (erreur d'échelle ×1000 documentée dans la littérature)
sont écartés par un garde de vraisemblance vs la fenêtre Yahoo quand elle
existe (même ordre de grandeur exigé sur l'exercice le plus proche).
"""
import json
import re
import time
import urllib.request

# La SEC exige un User-Agent au format « Nom contact@domaine » et bloque les
# requêtes anonymes (403). Le contact est celui du bot du projet, déjà public
# dans l'historique git. Sans email, le premier run a rendu 0/117 en silence.
UA = {"User-Agent": "Signal stock screener bot@signal.fr"}

_PANNE_VUE = False     # premier échec réseau du run : loggé UNE fois, en clair

# Balises us-gaap, par ordre de préférence. Le CA se dépose sous plusieurs
# concepts selon l'entreprise et l'époque — liste d'alias à entretenir.
TAGS_CA = ("RevenueFromContractWithCustomerExcludingAssessedTax",
           "Revenues",
           "SalesRevenueNet",
           "RevenueFromContractWithCustomerIncludingAssessedTax")
TAGS_RN = ("NetIncomeLoss",
           "NetIncomeLossAvailableToCommonStockholdersBasic")
TAGS_EPS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")

# Balises ifrs-full équivalentes, pour les 20-F/40-F. Le résultat net IFRS
# préfère la part des ACTIONNAIRES DE LA MÈRE quand elle existe : ProfitLoss
# inclut les minoritaires, ce qui gonflerait la marge nette d'un groupe à
# filiales partagées.
TAGS_CA_IFRS = ("Revenue", "RevenueFromContractsWithCustomers",
                "RevenueFromSaleOfGoods")
TAGS_RN_IFRS = ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss")
TAGS_EPS_IFRS = ("DilutedEarningsLossPerShare", "BasicEarningsLossPerShare")

# Tickers de cotation d'origine → symbole US déposant à la SEC. Seuls figurent
# ici des émetteurs dont le programme 20-F est ACTIF et vérifié — un mauvais
# mapping ferait entrer les comptes d'une autre société (leçon MC.PA → Moelis
# côté Finnhub). Les tickers déjà américains (PDD, TSM, SONY, ARM…) n'ont pas
# besoin d'entrée : le registre de la SEC les connaît directement.
US_EQUIV = {
    "ASML.AS": "ASML",   # ASML Holding — 20-F, comptes en EUR
    "SAP.DE":  "SAP",    # SAP SE — 20-F, EUR
    "TTE.PA":  "TTE",    # TotalEnergies — 20-F, comptes en USD
    "AZN.L":   "AZN",    # AstraZeneca — 20-F, USD
    "HSBA.L":  "HSBC",   # HSBC Holdings — 20-F, USD
    "UBSG.SW": "UBS",    # UBS Group — 20-F, USD
}


def eligible(ticker):
    """Ce ticker peut-il avoir un dossier à la SEC ? (US natif ou 20-F mappé)"""
    return "." not in (ticker or "") or ticker in US_EQUIV

# Profondeur conservée par titre. Relevé de 12 à 20 exercices le 06/08/2026 :
# le relevé du soir a montré que 52 fiches sur 97 butaient EXACTEMENT sur
# l'ancien plafond — elles n'étaient pas limitées par la source mais tronquées
# par nous, alors que le greffe remonte jusqu'à 2008 pour certains émetteurs.
# Coût : ~50 octets par exercice et par fiche, négligeable.
MAX_EXERCICES = 20
MAX_TRIMESTRES = 24

_CIK = None            # cache du mapping ticker → CIK, un fetch par run
_FRAME_AN = re.compile(r"CY\d{4}\Z")
_FRAME_TR = re.compile(r"CY\d{4}Q[1-4]\Z")


def _get(url):
    global _PANNE_VUE
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    except Exception as e:
        # Le premier échec du run est loggé en clair : le run précédent a
        # rendu 0/117 sans un mot, un échec silencieux ne doit plus arriver.
        if not _PANNE_VUE:
            _PANNE_VUE = True
            print(f"  ⚠️  EDGAR premier échec du run : {type(e).__name__} ({e}) — {url[:90]}")
        raise


def cik_de(ticker):
    """CIK d'un ticker, via le registre officiel. None si inconnu.

    Les cotations d'origine mappées (US_EQUIV) sont résolues via leur
    symbole US : le registre de la SEC ne connaît qu'eux."""
    global _CIK
    if _CIK is None:
        brut = _get("https://www.sec.gov/files/company_tickers.json")
        _CIK = {v["ticker"].upper(): int(v["cik_str"]) for v in brut.values()}
    t = US_EQUIV.get(ticker, ticker)
    return _CIK.get((t or "").upper())


def concept(cik, tag, taxo="us-gaap"):
    """companyconcept d'une société sous la taxonomie donnée (us-gaap ou
    ifrs-full). None si la balise n'existe pas chez cet émetteur."""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/{taxo}/{tag}.json"
    try:
        return _get(url)
    except Exception:
        return None


# ── Parsing pur (testé hors ligne) ───────────────────────────────────────────

def series_frames(doc, unite):
    """{frame: (date_fin, valeur)} des faits porteurs de frame, dans l'unité
    demandée (USD pour les montants, USD/shares pour le BPA)."""
    out = {}
    for u, faits in ((doc or {}).get("units") or {}).items():
        if u != unite:
            continue
        for f in faits:
            fr, val, fin = f.get("frame"), f.get("val"), f.get("end")
            if fr and fin and val is not None:
                out[fr] = (fin, val)
    return out


def fusion_series(series_liste):
    """Union de séries {frame: (fin, val)} issues des ALIAS d'une même balise.

    Les émetteurs changent de concept au fil des normes : NVIDIA dépose son CA
    sous SalesRevenueNet jusqu'en 2017 puis RevenueFromContractWithCustomer…
    ensuite. S'arrêter au premier alias non vide tronquait l'historique (2015
    et 2016 sans CA). Priorité au premier alias de la liste sur un frame en
    conflit — l'ordre des alias est l'ordre de préférence."""
    out = {}
    for s in series_liste:
        for fr, v in s.items():
            out.setdefault(fr, v)
    return out


def construire_fonda(ca_fr, rn_fr, eps_fr, max_an=12, max_tr=20):
    """Bloc {an, tr} au format fonda (millions entiers, src:"edgar").

    Entrées : dicts {frame: (fin, val)}. Annuels = frames CYxxxx ; trimestres =
    frames CYxxxxQn, complétés du Q4 dérivé quand l'exercice et ses trois
    premiers trimestres sont connus. Le BPA n'apparaît qu'en annuel.
    """
    def cast(v):
        return int(round(v / 1e6))

    an = []
    annuels_ca = {fr: v for fr, v in ca_fr.items() if _FRAME_AN.match(fr)}
    annuels_rn = {fr: v for fr, v in rn_fr.items() if _FRAME_AN.match(fr)}
    annuels_eps = {fr: v for fr, v in (eps_fr or {}).items() if _FRAME_AN.match(fr)}
    for fr in sorted(set(annuels_ca) | set(annuels_rn)):
        fin = (annuels_ca.get(fr) or annuels_rn.get(fr))[0]
        e = {"fin": fin, "src": "edgar"}
        if fr in annuels_ca:
            e["ca"] = cast(annuels_ca[fr][1])
        if fr in annuels_rn:
            e["rn"] = cast(annuels_rn[fr][1])
        if fr in annuels_eps and annuels_eps[fr][1]:
            e["eps"] = round(annuels_eps[fr][1], 4)
        if len(e) > 2:
            an.append(e)
    # Cohérence de clôture fiscale : un frame annuel dont la fin s'écarte de
    # plus d'un mois du mois de clôture majoritaire est un artefact (AMZN :
    # frame CY2026 arrêté au 30 juin, un « exercice » fantôme qui décalait
    # les étiquettes prévisionnelles). Un vrai changement de calendrier
    # fiscal (CDNS : début janvier → fin décembre) reste à ±1 mois, il passe.
    if len(an) >= 3:
        mois = [int(e["fin"][5:7]) for e in an]
        maj = max(set(mois), key=mois.count)
        ecart = lambda m: min(abs(m - maj), 12 - abs(m - maj))
        an = [e for e in an if ecart(int(e["fin"][5:7])) <= 1]
    # Résultat net aberrant : un RN positif 100 fois plus petit que ses DEUX
    # voisins est une erreur de tagage (SCHW 2021 déposé à 6 M$ au lieu de
    # ~5 855), pas une mauvaise année — une vraie chute de cette ampleur
    # passe par les pertes. Le champ est retiré, l'entrée garde son CA.
    for i, e in enumerate(an):
        rn = e.get("rn")
        if not rn or rn <= 0:
            continue
        voisins = [abs(an[j]["rn"]) for j in (i - 1, i + 1)
                   if 0 <= j < len(an) and an[j].get("rn")]
        if len(voisins) == 2 and all(v / rn > 100 for v in voisins):
            e.pop("rn", None)
            e.pop("eps", None)
    an = [e for e in an if len(e) > 2][-max_an:]

    tr = []
    trims_ca = {fr: v for fr, v in ca_fr.items() if _FRAME_TR.match(fr)}
    trims_rn = {fr: v for fr, v in rn_fr.items() if _FRAME_TR.match(fr)}
    for fr in sorted(set(trims_ca) | set(trims_rn)):
        fin = (trims_ca.get(fr) or trims_rn.get(fr))[0]
        e = {"fin": fin, "src": "edgar"}
        if fr in trims_ca:
            e["ca"] = cast(trims_ca[fr][1])
        if fr in trims_rn:
            e["rn"] = cast(trims_rn[fr][1])
        if len(e) > 2:
            tr.append(e)
    # Q4 dérivé : exercice − (Q1+Q2+Q3), CA et RN seulement. La date de fin du
    # trimestre dérivé est celle de l'exercice. On ne dérive que si les trois
    # trimestres sont là : deux trimestres et demi ne font pas un Q4.
    for fr_an in sorted(set(annuels_ca) | set(annuels_rn)):
        annee = fr_an[2:6]
        qs = [f"CY{annee}Q{i}" for i in (1, 2, 3)]
        e = {"fin": None, "src": "edgar"}
        for champ, annuels, trims in (("ca", annuels_ca, trims_ca),
                                      ("rn", annuels_rn, trims_rn)):
            if fr_an in annuels and all(q in trims for q in qs):
                e[champ] = cast(annuels[fr_an][1]) - sum(cast(trims[q][1]) for q in qs)
                e["fin"] = annuels[fr_an][0]
        if e["fin"] and len(e) > 2:
            tr.append(e)
    tr = sorted(tr, key=lambda x: x["fin"])[-max_tr:]

    if not an and not tr:
        return None
    return {"an": an, "tr": tr}


def ajuster_eps_splits(bloc, splits, actions_actuelles=None):
    """Ramène les BPA EDGAR dans la base d'actions ACTUELLE — en DÉTECTANT
    la base de chaque valeur, jamais en la devinant.

    Le piège est en deux temps. Un 10-K de 2015 publie le BPA de l'époque :
    après les splits NVIDIA (×4 en 2021, ×10 en 2024), il faut le diviser
    par 40. MAIS le 10-K qui suit un split republie ses deux exercices
    COMPARATIFS déjà retraités, et le frame SEC garde cette valeur-là :
    diviser aveuglément double alors l'ajustement (GOOGL 2020 sortait à
    592× de PER au lieu de ~35×). La base d'un frame est donc inconnue.

    Détection : rn ÷ BPA donne le nombre d'actions impliqué. On essaie
    chaque base possible (valeur d'origine, chaque base intermédiaire,
    base actuelle) et on garde celle qui rapproche le plus ce nombre du
    nombre d'actions ACTUEL — les rachats font ±2×, les splits ×4 à ×40,
    les ordres de grandeur ne se confondent pas (comparaison en log,
    rejet si même le meilleur candidat reste à plus de 3×). Sans rn ou
    sans nombre d'actions actuel, prudence : le BPA est RETIRÉ dès qu'un
    split postérieur existe — pas de multiple plutôt qu'un multiple faux.
    Pure, mutation en place. splits : [(date_iso, ratio)]."""
    import math
    if not bloc:
        return bloc
    spl = sorted((d, float(r)) for d, r in (splits or []) if r and r > 0)
    for e in bloc.get("an") or []:
        eps = e.get("eps")
        if not eps or eps <= 0:
            continue
        posterieurs = [r for d, r in spl if d > e["fin"]]
        rn = e.get("rn")
        if not rn or rn <= 0 or not actions_actuelles:
            if posterieurs:
                e.pop("eps", None)      # base indéterminable
            continue
        candidats, f = [1.0], 1.0
        for r in reversed(posterieurs):
            f *= r
            candidats.append(f)         # bases intermédiaires puis d'origine
        mieux, ecart_min = None, None
        for c in candidats:
            actions = rn * 1e6 * c / eps
            ecart = abs(math.log(actions / actions_actuelles))
            if ecart_min is None or ecart < ecart_min:
                mieux, ecart_min = c, ecart
        if ecart_min > math.log(3):
            # rn/eps incompatibles avec le nombre d'actions quel que soit le
            # candidat : l'un des deux ment (SCHW 2021, rn déposé à 6 M$) et
            # on ne devine pas lequel — les deux champs sont retirés.
            e.pop("eps", None)
            e.pop("rn", None)
        elif mieux != 1.0:
            e["eps"] = round(eps / mieux, 4)
    return bloc


def _proches(a, b, jours=7):
    """Deux dates ISO à moins de `jours` d'écart (2023-12-30 vs 12-31…)."""
    from datetime import date
    da = date(*map(int, a.split("-")))
    db = date(*map(int, b.split("-")))
    return abs((da - db).days) <= jours


def completer_fonda(fonda, ed):
    """Étend fonda avec les entrées EDGAR aux dates que Yahoo n'a pas.

    Extend-only : jamais d'écrasement d'une entrée Yahoo (les retraitements
    peuvent différer entre bases, on ne mélange pas silencieusement à date
    égale). Garde de vraisemblance : quand un exercice EDGAR est ADJACENT
    (±1 an) d'un exercice Yahoo, leurs CA doivent être du même ordre de
    grandeur (rapport < 5), sinon TOUT l'apport EDGAR est refusé — symptôme
    classique d'une erreur d'échelle de tagage, on préfère la fenêtre courte
    au faux profond. Le garde ne compare JAMAIS des exercices éloignés : une
    hypercroissance fait ×10 en dix ans sans que rien ne soit faux.
    Mutation en place, retourne fonda.
    """
    if not fonda or not ed:
        return fonda
    ref = [(int(e["fin"][:4]), e["ca"]) for e in fonda.get("an", []) if e.get("ca")]
    for cle, borne in (("an", MAX_EXERCICES), ("tr", MAX_TRIMESTRES)):
        ajouts = []
        for e in ed.get(cle) or []:
            if any(_proches(e["fin"], x["fin"]) for x in fonda.get(cle, [])):
                continue
            if cle == "an" and e.get("ca") and ref:
                annee_e = int(e["fin"][:4])
                voisins = [ca for a, ca in ref if abs(a - annee_e) <= 1]
                for ca_ref in voisins:
                    rapport = max(e["ca"], ca_ref) / max(1, min(e["ca"], ca_ref))
                    if rapport > 5:
                        return fonda      # échelle incohérente : on refuse tout
            ajouts.append(e)
        if ajouts:
            fonda[cle] = sorted(fonda.get(cle, []) + ajouts,
                                key=lambda x: x["fin"])[-borne:]
    return fonda


# ── Fetch complet pour un ticker (réseau, fail-soft) ─────────────────────────

def _collecte(cik, plan, devise, pause):
    """Séries {ca, rn, eps} pour un plan [(nom, tags, taxo), ...], dans la
    devise comptable. TOUS les alias sont lus puis fusionnés : les émetteurs
    changent de balise au fil des normes, chaque époque vit sous la sienne."""
    docs = {}
    for nom, tags, taxo in plan:
        unite = f"{devise}/shares" if nom == "eps" else devise
        series = []
        for tag in tags:
            doc = concept(cik, tag, taxo)
            time.sleep(pause)
            series.append(series_frames(doc, unite))
        docs[nom] = fusion_series(series)
    return docs


def chiffres(ticker, devise="USD", pause=0.12):
    """Bloc {an, tr} EDGAR pour un déposant SEC, None si indisponible.

    `devise` est la devise COMPTABLE annoncée par Yahoo : les faits sont lus
    exclusivement dans cette unité. Un 20-F allemand tague en EUR, un
    taïwanais en TWD — lire une autre unité mélangerait deux monnaies dans
    le même historique, le poison silencieux des ADR.

    Ordre des taxonomies : us-gaap d'abord (tous les domestiques, plus les
    étrangers qui déposent en US GAAP comme MUFG), puis ifrs-full si le CA
    est resté vide — c'est le cas général des 20-F européens et asiatiques.
    """
    cik = cik_de(ticker)
    if not cik:
        return None
    devise = (devise or "USD").upper()
    docs = _collecte(cik, (("ca", TAGS_CA, "us-gaap"),
                           ("rn", TAGS_RN, "us-gaap"),
                           ("eps", TAGS_EPS, "us-gaap")), devise, pause)
    if not docs["ca"]:
        docs = _collecte(cik, (("ca", TAGS_CA_IFRS, "ifrs-full"),
                               ("rn", TAGS_RN_IFRS, "ifrs-full"),
                               ("eps", TAGS_EPS_IFRS, "ifrs-full")), devise, pause)
    return construire_fonda(docs["ca"], docs["rn"], docs["eps"])
