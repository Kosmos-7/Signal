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
    silencieusement) — chaque entrée ajoutée porte src:"edgar" ;
  · il ne remplit aucun champ du SCORE : périmètre = section « Chiffres
    publiés » des fiches, uniquement ;
  · pas d'IFRS : les émetteurs étrangers cotés US (20-F, taxonomie ifrs-full)
    sont hors périmètre v1 — leurs concepts us-gaap sont vides, le module
    rend simplement None et la fiche garde sa fenêtre Yahoo.

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
    """CIK d'un ticker US, via le registre officiel. None si inconnu."""
    global _CIK
    if _CIK is None:
        brut = _get("https://www.sec.gov/files/company_tickers.json")
        _CIK = {v["ticker"].upper(): int(v["cik_str"]) for v in brut.values()}
    return _CIK.get((ticker or "").upper())


def concept(cik, tag):
    """companyconcept us-gaap d'une société. None si la balise n'existe pas."""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{tag}.json"
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
    an = an[-max_an:]

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


def ajuster_eps_splits(bloc, splits):
    """Ramène les BPA « tels que déposés » dans la base d'actions ACTUELLE.

    Un dépôt 10-K de 2015 publie le BPA de l'époque ; si l'action a été
    divisée depuis (NVIDIA : 4:1 en 2021 puis 10:1 en 2024, ÷40 au total),
    le cours ajusté d'aujourd'hui ne peut pas lui être rapporté — les PER
    historiques sortaient à 0,4×. Chaque BPA est divisé par le produit des
    ratios de splits survenus APRÈS sa date de clôture. splits : liste
    [(date_iso, ratio)] (ratio 4.0 pour un 4:1). Pure, mutation en place."""
    if not bloc or not splits:
        return bloc
    for e in bloc.get("an") or []:
        if not e.get("eps"):
            continue
        facteur = 1.0
        for d, ratio in splits:
            if ratio and ratio > 0 and d > e["fin"]:
                facteur *= ratio
        if facteur != 1.0:
            e["eps"] = round(e["eps"] / facteur, 4)
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
    for cle, borne in (("an", 12), ("tr", 20)):
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

def chiffres(ticker, pause=0.12):
    """Bloc {an, tr} EDGAR pour un ticker US, None si indisponible."""
    cik = cik_de(ticker)
    if not cik:
        return None
    docs = {}
    for nom, tags in (("ca", TAGS_CA), ("rn", TAGS_RN), ("eps", TAGS_EPS)):
        unite = "USD/shares" if nom == "eps" else "USD"
        # TOUS les alias sont lus puis fusionnés : les émetteurs changent de
        # balise au fil des normes, chaque époque vit sous la sienne.
        series = []
        for tag in tags:
            doc = concept(cik, tag)
            time.sleep(pause)
            series.append(series_frames(doc, unite))
        docs[nom] = fusion_series(series)
    return construire_fonda(docs["ca"], docs["rn"], docs["eps"])
