#!/usr/bin/env python3
"""Le tableau « Sur les marchés » du point du matin.

POURQUOI CE FICHIER EXISTE. Le point du matin racontait les marchés sans jamais
les CHIFFRER : on lisait « les indices ont bien terminé » sans savoir de combien.
Les dépêches ne le disent pas non plus de façon fiable (elles datent d'heures
différentes et se contredisent d'une agence à l'autre). Le seul moyen honnête
d'écrire un niveau est de le mesurer soi-même.

LE SNAPSHOT VIT DANS LE POST, PAS À CÔTÉ. Un post publié est immuable : c'est la
doctrine de tout le dossier `actualites/`. Un tableau de marchés servi depuis un
fichier partagé se réécrirait chaque matin et rendrait FAUX tous les posts
archivés, qui affichent « à la clôture de la veille » sous des chiffres d'un
autre jour. Le tableau est donc écrit DANS le post, comme la photo, et gelé avec
lui.

JAMAIS DE DEMI-TABLEAU. Même règle que MIN_DEPECHES : si moins de MIN_LIGNES
instruments répondent, il n'y a pas de tableau du tout. Une ligne manquante dans
un tableau de marchés ne se voit pas — le lecteur croit que le Nasdaq n'a pas
bougé, pas qu'on n'a pas su le lire.

L'ORDRE EST FIXE. Les lignes s'affichent dans l'ordre de PANIER, jamais dans
l'ordre d'arrivée des réponses : un tableau dont les lignes dansent d'un jour à
l'autre oblige à le relire en entier chaque matin.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Panier, dans l'ordre d'affichage. `pts` pour les taux (un rendement se compare
# en points, pas en pourcentage de lui-même : un 10 ans qui passe de 4,00 % à
# 4,04 % a pris 4 points de base, écrire « +1 % » serait juste et illisible).
#
# LE 10 ANS EST AMÉRICAIN, PAS FRANÇAIS, et c'est dit dans le libellé. L'OAT
# serait plus parlante pour un lecteur français, mais aucune source gratuite ne
# la donne de façon fiable ; annoncer « OAT 10 ans » avec un Treasury dedans
# serait un mensonge d'étiquette pour gagner en couleur locale.
PANIER = [
    {"cle": "sp500",   "libelle": "S&P 500",         "ticker": "^GSPC",    "type": "pct", "dec": 2},
    {"cle": "cac40",   "libelle": "CAC 40",          "ticker": "^FCHI",    "type": "pct", "dec": 2},
    {"cle": "nasdaq",  "libelle": "Nasdaq",          "ticker": "^IXIC",    "type": "pct", "dec": 2},
    {"cle": "stoxx",   "libelle": "Euro Stoxx 50",   "ticker": "^STOXX50E", "type": "pct", "dec": 2},
    {"cle": "t10",     "libelle": "Treasury 10 ans", "ticker": "^TNX",     "type": "pts", "dec": 3, "unite": "%"},
    {"cle": "or",      "libelle": "Or",              "ticker": "GC=F",     "type": "pct", "dec": 2, "unite": "$"},
    {"cle": "petrole", "libelle": "Brent",           "ticker": "BZ=F",     "type": "pct", "dec": 2, "unite": "$"},
    {"cle": "eurusd",  "libelle": "Euro / dollar",   "ticker": "EURUSD=X", "type": "pct", "dec": 4, "unite": "$"},
    {"cle": "bitcoin", "libelle": "Bitcoin",         "ticker": "BTC-USD",  "type": "pct", "dec": 0, "unite": "$"},
]

# En dessous, pas de tableau. Quatre lignes, c'est le minimum pour qu'on lise un
# marché et pas une anecdote.
MIN_LIGNES = 4
# Au-dessus, le tableau devient un écran de terminal : on affiche les premières
# lignes du panier qui ont répondu.
MAX_LIGNES = 6


def variation(avant, apres, type_):
    """Variation d'un instrument, dans son unité de lecture.

    `pct` en pourcentage, `pts` en points bruts. Rend None si la veille vaut
    zéro (division impossible) plutôt qu'un infini qui s'afficherait.
    """
    if avant is None or apres is None:
        return None
    if type_ == "pts":
        return apres - avant
    if not avant:
        return None
    return (apres - avant) / avant * 100.0


def ligne(spec, closes, dates):
    """Une ligne du tableau à partir de deux clôtures. None si inexploitable.

    `closes` : les clôtures de l'instrument, de la plus ancienne à la plus
    récente. Il en faut DEUX : un niveau sans variation ne dit rien du jour.
    """
    valides = [(c, d) for c, d in zip(closes, dates) if c is not None]
    if len(valides) < 2:
        return None
    (avant, _), (apres, ref) = valides[-2], valides[-1]
    var = variation(avant, apres, spec["type"])
    if var is None:
        return None
    return {"cle": spec["cle"], "libelle": spec["libelle"], "valeur": apres,
            "dec": spec["dec"], "unite": spec.get("unite", ""),
            "type": spec["type"], "variation": var, "ref": ref}


def choisir(lignes):
    """Les lignes retenues, dans l'ordre du panier, ou [] s'il en manque trop.

    Pure : c'est elle qui porte la règle du demi-tableau, donc c'est elle qu'on
    teste hors ligne.
    """
    ordre = {s["cle"]: i for i, s in enumerate(PANIER)}
    gardees = sorted((l for l in lignes if l), key=lambda l: ordre.get(l["cle"], 99))
    if len(gardees) < MIN_LIGNES:
        return []
    return gardees[:MAX_LIGNES]


# TYPOGRAPHIE FRANÇAISE, ÉCRITE EN ÉCHAPPEMENTS. Ces deux espaces sont
# invisibles dans un éditeur et se font écraser par un espace ordinaire au
# premier copier-coller : nommées, elles survivent. U+202F (fine insécable)
# sépare les milliers, U+00A0 (insécable) précède le signe % — c'est la règle de
# l'Imprimerie nationale, et c'est ce que le reste du site applique déjà.
# `actualites.html` refait le même formatage en JS : les deux sont comparés
# valeur par valeur dans tests/test_actualites.py.
FINE, INSEC = "\u202f", "\u00a0"


def fmt_nombre(v, dec):
    """Format français : fine insécable pour les milliers, virgule décimale."""
    return f"{v:,.{dec}f}".replace(",", FINE).replace(".", ",")


def fmt_variation(l):
    """« +1,79 % », « -0,022 pts » — et « 0,00 % » sans signe.

    Le signe est écrit dès qu'il y a un sens, JAMAIS sur un zéro : « +0,00 % »
    annonce une hausse et n'en montre pas, c'est le seul cas où le signe ment.
    (Écart trouvé par le test qui compare ce formatage à celui de la page :
    le JS ne signait pas le zéro, Python si.)
    """
    v = l["variation"]
    dec = 3 if l["type"] == "pts" else 2
    signe = "+" if v > 0 else ("-" if v < 0 else "")
    corps = f"{abs(v):.{dec}f}".replace(".", ",")
    return signe + corps + INSEC + ("pts" if l["type"] == "pts" else "%")


def bloc_prompt(marches):
    """Le tableau tel qu'il est donné au modèle. Il n'a le droit de citer QUE
    ces nombres-là pour les marchés : ils viennent de notre mesure, pas d'une
    dépêche, et ce sont les seuls que la page affichera juste à côté du texte."""
    if not marches or not marches.get("lignes"):
        return ""
    lignes = "\n".join(
        f"- {l['libelle']} : {fmt_nombre(l['valeur'], l['dec'])}{(INSEC + l['unite']) if l['unite'] else ''}"
        f" ({fmt_variation(l)})" for l in marches["lignes"])
    mv = marches.get("mouvement")
    if mv:
        lignes += (f"\n- Plus fort mouvement de notre liste : {mv['nom']} "
                   f"{fmt_nombre(mv['valeur'], 2)} ({fmt_variation(mv)})")
    return ("\n## CLÔTURES MESURÉES (notre propre relevé, pas une dépêche)\n"
            f"Référence : clôture du {marches.get('ref', '?')}.\n" + lignes + "\n")


# ── Collecte (impure : réseau) ───────────────────────────────────────────────

def _closes(tickers):
    """{ticker: ([clôtures], [dates ISO])} sur les 7 derniers jours ouvrés.

    Un SEUL appel yfinance pour tout le panier : à 05h45 UTC le job a mieux à
    faire que d'ouvrir dix connexions. Un ticker qui ne répond pas est ABSENT du
    dictionnaire, il n'est pas à None : l'appelant ne peut pas confondre
    « pas de réponse » et « réponse vide ».
    """
    import yfinance as yf
    out = {}
    try:
        d = yf.download(tickers, period="7d", interval="1d",
                        auto_adjust=False, progress=False, group_by="ticker",
                        threads=True)
    except Exception as e:                                     # noqa: BLE001
        print(f"   marchés ✗ téléchargement groupé : {type(e).__name__} {e}")
        return out
    for t in tickers:
        try:
            col = d[t]["Close"] if len(tickers) > 1 else d["Close"]
            col = col.dropna()
            if col.empty:
                print(f"   marchés ✗ {t} : aucune clôture sur 7 jours")
                continue
            out[t] = ([float(v) for v in col.values],
                      [str(i)[:10] for i in col.index])
        except Exception as e:                                 # noqa: BLE001
            print(f"   marchés ✗ {t} : {type(e).__name__}")
    return out


def plus_fort_mouvement(closes_par_ticker, noms):
    """La plus grosse variation de séance parmi les titres fournis.

    C'EST L'AVANTAGE QU'UNE NEWSLETTER GÉNÉRALISTE N'A PAS. Sa sixième ligne est
    une action choisie à la main ; la nôtre sort des sociétés que le site suit
    vraiment, et elle est cliquable vers sa fiche. On la prend dans la watchlist
    principale et nulle part ailleurs : c'est la seule liste dont la route de
    fiche est garantie valide (#/w/principale/TICKER).
    """
    meilleur = None
    for t, (closes, dates) in closes_par_ticker.items():
        l = ligne({"cle": t, "libelle": noms.get(t, t), "ticker": t,
                   "type": "pct", "dec": 2}, closes, dates)
        if not l:
            continue
        if meilleur is None or abs(l["variation"]) > abs(meilleur["variation"]):
            meilleur = l
    if meilleur:
        meilleur["ticker"] = meilleur.pop("cle")
        meilleur["nom"] = meilleur["libelle"]
    return meilleur


def releve():
    """Le snapshot du matin, ou None si le panier n'a pas assez répondu."""
    par_ticker = _closes([s["ticker"] for s in PANIER])
    lignes = choisir([ligne(s, *par_ticker.get(s["ticker"], ([], [])))
                      for s in PANIER])
    if not lignes:
        print(f"   marchés ✗ {len(par_ticker)} instruments lus, "
              f"{MIN_LIGNES} lignes minimum : pas de tableau")
        return None

    mouvement = None
    try:
        w = json.load(open("watchlist.json", encoding="utf-8"))
        titres = {s["ticker"]: s.get("name") or s["ticker"] for s in w.get("stocks", [])}
        if titres:
            mouvement = plus_fort_mouvement(_closes(sorted(titres)), titres)
    except Exception as e:                                     # noqa: BLE001
        print(f"   marchés ✗ mouvement de la liste : {type(e).__name__}")

    # La référence affichée est celle des ACTIONS : le bitcoin cote le week-end
    # et le dimanche sa date serait en avance d'un jour sur tout le reste.
    actions = [l for l in lignes if l["cle"] in ("sp500", "cac40", "nasdaq", "stoxx")]
    ref = max((l["ref"] for l in actions), default=lignes[0]["ref"])
    print(f"   marchés : {len(lignes)} lignes, clôture du {ref}"
          + (f", mouvement {mouvement['nom']} {fmt_variation(mouvement)}" if mouvement else ""))
    return {"ref": ref, "lignes": lignes, "mouvement": mouvement}


if __name__ == "__main__":
    r = releve()
    print(json.dumps(r, ensure_ascii=False, indent=1) if r else "aucun relevé")
