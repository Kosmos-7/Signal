# themes.py — Taxonomie des watchlists thématiques (source unique de vérité)
#
# Signal publie TROIS listes : la watchlist principale (top 30 de l'univers,
# toutes catégories) et deux vues thématiques.
#
# ARCHITECTURE — « un seul scoring, N projections »
# Chaque titre est scoré EXACTEMENT UNE FOIS par screener.py. Une watchlist
# thématique n'est qu'un filtre + tri sur ces mêmes résultats : coût API
# marginal nul. L'univers du screener est l'union de sa liste historique et des
# titres déclarés ici — ajouter un ticker à un thème l'ajoute à l'univers.
#
# POURQUOI SEULEMENT DEUX THÈMES (août 2026)
# Une première version en publiait treize. Trop : les thèses se recouvraient,
# plusieurs n'étaient que des regroupements sectoriels déguisés, et l'ensemble
# demandait une maintenance sans rapport avec ce qu'il apportait. On garde les
# deux chaînes sur lesquelles le projet a réellement quelque chose à dire, et
# on assume de ne pas couvrir le reste plutôt que de le couvrir mal.
# Les thèmes retirés (santé, conso, défense, robotique, compounders, mémoire
# et électrification en tant que thèses autonomes, décote et qualité calculées)
# restent dans l'historique git — leur restauration est un revert, pas un
# chantier.
#
# DOCTRINE DE NOMMAGE (cf. apprendre.html — refus de « marge de sécurité »)
# On ne colle jamais sur une mesure l'étiquette d'un concept qu'on ne calcule
# pas : le screener mesure des marges, un ROE, un endettement — ni la
# durabilité d'un avantage, ni la valeur intrinsèque.
#
# CE QUE LES THÈMES NE SONT PAS
# Ils ne sont justifiés par aucun backtest et ne prétendent améliorer aucune
# performance. Ils structurent la lecture d'un univers trop large pour une
# seule liste de trente lignes — rien de plus.

# ── THÈMES CURÉS ─────────────────────────────────────────────────────────────
# Chaque thème : id (slug immuable, sert d'URL), label, kind, thesis, inversion
# (ce qui invaliderait la thèse — obligatoire, c'est le garde-fou
# anti-promotion), biais (ce que le thème concentre), tickers.
#
# Les listes sont ordonnées par MAILLON DE CHAÎNE, pas par ordre alphabétique :
# c'est la structure qui porte la thèse, et un maillon vide se voit tout de
# suite. L'ordre d'affichage sur le site reste celui du score.

THEMES_CURES = [
    {
        "id": "infra-ia",
        "label": "Infrastructure de l'IA",
        "sous_titre": "Du silicium au mégawatt",
        "kind": "these",
        "thesis": (
            "Chaque dollar investi dans l'IA finit en objets physiques : puces, machines de "
            "gravure et d'assemblage, mémoire, fibre, serveurs, bâtiments, électricité, "
            "refroidissement. Cette watchlist suit la chaîne complète, maillon par maillon — "
            "c'est là que l'argent atterrit, quel que soit l'usage qui gagne. Et le vrai goulot "
            "n'est pas la gravure : c'est l'assemblage et les substrats, là où le pouvoir de "
            "prix est le plus fort."
        ),
        "inversion": (
            "Le retour sur investissement applicatif ne se matérialise pas et les hyperscalers "
            "digèrent leur capex : toute la chaîne se contracte en même temps, du silicium au "
            "transformateur. Supposer plus de trois à quatre ans de dépense linéaire est un pari "
            "de conviction, pas une base statistique. S'y ajoutent les contrôles à l'export et la "
            "dépendance à un seul fondeur avancé."
        ),
        "biais": (
            "C'est un thème de CONCENTRATION, pas de diversification : ses six maillons montent "
            "et descendent ensemble, et il amplifie le pari tech déjà assumé par la watchlist "
            "principale. Il est aussi transverse aux secteurs (technologie, industrie, services "
            "publics, matériaux) — la règle de concentration sectorielle de l'agent ne le verra "
            "jamais comme un bloc, un calcul dédié s'en charge. Périmètre volontaire : la "
            "production d'électricité renouvelable en est exclue, c'est un pari de politique "
            "publique, pas d'infrastructure IA."
        ),
        "tickers": [
            # 1 — Calcul : les processeurs de l'entraînement et de l'inférence
            "NVDA", "AVGO", "AMD", "MRVL", "QCOM", "INTC",
            # 2 — Fonderie, équipement, outils de conception ET PACKAGING AVANCÉ.
            #     L'assemblage 2.5D/3D est le goulot le plus contraignant de la
            #     chaîne : ce n'est pas la gravure qui rationne les livraisons
            #     d'accélérateurs, c'est la capacité d'assemblage et les
            #     substrats. Ce maillon était absent de la première version.
            "TSM", "ASML.AS", "AMAT", "LRCX", "KLAC", "TER", "ASM.AS",
            "8035.T", "6857.T", "SNPS", "CDNS",
            "ASX", "6146.T", "4062.T",
            # 3 — Mémoire et stockage : la brique vendue au prix spot
            "MU", "000660.KS", "005930.KS", "WDC", "STX", "NTAP", "4063.T",
            # 4 — Réseau et interconnexion optique : ce qui relie les
            #     accélérateurs entre eux, et limite la taille des clusters
            #     d'entraînement autant que le nombre de puces.
            "ANET", "COHR", "LITE", "CIEN", "CSCO",
            # 5 — Serveurs et immobilier de centre de données : ce qu'on
            #     assemble et le bâtiment qui l'héberge — la dépense atterrit
            #     littéralement là.
            "DELL", "HPE", "EQIX", "DLR",
            # 6 — Plateformes, données et cloud : qui commande et qui exploite
            "MSFT", "GOOGL", "AMZN", "META", "ORCL", "PLTR",
            "SNOW", "DDOG", "MDB", "NET",
            # 7 — Énergie, conversion et refroidissement : du réseau haute
            #     tension jusqu'à l'étage d'alimentation du rack.
            "VRT", "ETN", "SU.PA", "SIE.DE", "ABBN.SW", "ENR.DE",
            "PWR", "VST", "NEE", "CCJ",
            "MPWR", "ON", "IFX.DE",
        ],
    },
    {
        "id": "financials",
        "label": "Financials",
        "sous_titre": "Bilans, flux et péages de marché",
        "kind": "secteur",
        "thesis": (
            "Trois métiers, trois moteurs. Les BILANS (banques, assureurs) gagnent quand les "
            "taux sont hauts et les défauts rares. Les FLUX (réseaux de paiement) prennent une "
            "commission sur chaque transaction, sans porter le risque de crédit. Les PÉAGES "
            "(indices, notation, places de marché) facturent un accès que personne ne peut "
            "contourner. Les voir côte à côte montre lequel de ces moteurs est payé cher — "
            "et pourquoi."
        ),
        "inversion": (
            "Pour les bilans : une récession de crédit, ou une baisse rapide des taux qui écrase "
            "la marge d'intérêt. Pour les flux et les péages : la régulation des tarifs, qui "
            "revient périodiquement sur les commissions d'interchange comme sur les indices et la "
            "notation. Un secteur ne s'invalide pas comme une thèse, mais ces trois moteurs "
            "peuvent caler séparément."
        ),
        "biais": (
            "Étiqueté SECTEUR et non thèse : c'est un regroupement par métier, pas une conviction "
            "sur la finance. Les péages se paient structurellement cher — le pilier valorisation "
            "les pénalise mécaniquement, un score moyen n'y signale pas une entreprise moyenne. "
            "À l'inverse les banques affichent des multiples optiquement bas qui reflètent un "
            "risque de bilan que le screener ne mesure pas."
        ),
        "tickers": [
            # 1 — Bilans : banques universelles et de financement
            "JPM", "BAC", "WFC", "GS", "MS", "TFC", "SCHW",
            "HSBA.L", "BNP.PA", "UBSG.SW",
            # 2 — Bilans : assurance et courtage
            "CB", "PGR", "ALV.DE", "CS.PA", "MUV2.DE", "MMC",
            # 3 — Flux : réseaux de paiement et acquisition
            "V", "MA", "AXP", "ADYEN.AS", "PYPL",
            # 4 — Gestion d'actifs et capital-investissement
            "BLK", "BX", "KKR",
            # 5 — Péages : indices, notation, places de marché, scoring
            "SPGI", "MCO", "MSCI", "ICE", "CME", "NDAQ", "LSEG.L", "DB1.DE", "FICO",
        ],
    },
]

# ── THÈMES CALCULÉS ──────────────────────────────────────────────────────────
# Aucun n'est publié dans cette version. Le mécanisme reste en place côté
# screener (règle sur le breakdown + tri dédié) : réactiver « décote vs
# tendance » ou « qualité durable » consiste à réintroduire une entrée ici.
THEMES_CALCULES = []

# ── ÉCARTÉS APRÈS VALIDATION (run CI du 2026-08-01, 81 symboles testés) ──────
# Ces titres avaient leur place dans une thèse mais échouent aux critères
# d'inclusion publics du projet. Ils sont listés ici plutôt que supprimés en
# silence : quelqu'un les cherchera, et l'absence doit avoir une raison lisible.
#
#   CEG      Constellation Energy — 4,5 ans d'historique (scission 2022) < 5 ans
#   GEV      GE Vernova          — 2,3 ans d'historique (scission 2024) < 5 ans
#   ROG.SW   Roche               — symbole introuvable côté Yahoo ; remplacé par
#                                  l'ADR américain RHHBY, servi normalement
#   BESI.AS  BE Semiconductor    — ~17 Md$ de capitalisation < seuil 25 Md$
#   EFX      Equifax             — ~20 Md$ de capitalisation < seuil 25 Md$
#
# CEG et GEV sont les deux acteurs les plus lisibles du raccordement électrique
# de l'IA, et leur absence ampute le maillon « énergie » du thème infra-IA.
# CEG franchira les 5 ans en 2027, GEV en 2029.
#
# Complément du 01/08 (26 candidats éprouvés pour combler les maillons réseau,
# packaging, serveurs et conversion de puissance) : 21 retenus, 5 recalés.
# La perte la plus sensible est ARM — 256 Md$ de capitalisation, mais introduit
# en bourse en 2023, donc 2,9 ans d'historique. Le maillon « calcul » se prive
# ainsi du concepteur de l'architecture CPU dominante. Il sera éligible en 2028.
ECARTES_VALIDATION = {
    "CEG":     "historique 4,5 ans < 5 ans requis (scission 2022)",
    "GEV":     "historique 2,3 ans < 5 ans requis (scission 2024)",
    "ROG.SW":  "symbole introuvable chez Yahoo — remplacé par l'ADR RHHBY",
    "BESI.AS": "capitalisation ~17 Md$ < seuil 25 Md$ (collage hybride)",
    "EFX":     "capitalisation ~20 Md$ < seuil 25 Md$",
    # Complément du 01/08
    "ARM":     "historique 2,9 ans < 5 ans requis (IPO 2023) — éligible en 2028",
    "ALAB":    "historique 2,4 ans < 5 ans requis (IPO 2024)",
    "CRDO":    "historique 4,5 ans < 5 ans requis — éligible en 2027",
    "GFS":     "historique 4,8 ans < 5 ans requis — éligible fin 2026",
    "AMKR":    "capitalisation ~12 Md$ < seuil 25 Md$ (assemblage)",
    "6920.T":  "capitalisation ~23 Md$ < seuil 25 Md$ (inspection de masques EUV)",
    "FN":      "capitalisation ~16 Md$ < seuil 25 Md$ (sous-traitance optique)",
    "SMCI":    "capitalisation ~18 Md$ < seuil 25 Md$ (serveurs)",
    "NVT":     "capitalisation ~25 Md$, au seuil — écarté faute de marge",
    "HUBB":    "capitalisation ~25 Md$, au seuil — écarté faute de marge",
    "MOD":     "capitalisation ~11 Md$ < seuil 25 Md$ (refroidissement)",
    "8036.T":  "symbole introuvable chez Yahoo",
}

THEMES = THEMES_CURES + THEMES_CALCULES
THEMES_BY_ID = {t["id"]: t for t in THEMES}

# Nombre de titres affichés par vue thématique calculée (les thèmes curés
# publient l'intégralité de leur liste).
TOP_PAR_THEME = 12

# ── UNIVERS DÉRIVÉ ───────────────────────────────────────────────────────────

def univers_thematique():
    """Tous les tickers cités par au moins un thème curé, dédoublonnés et triés."""
    return sorted({t for th in THEMES_CURES for t in th["tickers"]})

def themes_par_ticker():
    """Table inverse ticker → [ids de thèmes curés]. Les thèmes calculés sont
    attribués à l'exécution, à partir du breakdown."""
    inv = {}
    for th in THEMES_CURES:
        for t in th["tickers"]:
            inv.setdefault(t, []).append(th["id"])
    return inv

def themes_calcules_pour(breakdown):
    """Ids des thèmes calculés auxquels un titre appartient, vu son breakdown."""
    if not breakdown:
        return []
    out = []
    for th in THEMES_CALCULES:
        try:
            if th["regle"](breakdown):
                out.append(th["id"])
        except Exception:
            pass          # un breakdown incomplet n'appartient simplement pas au thème
    return out

def meta_publique():
    """Métadonnées des thèmes destinées au site (sans les callables)."""
    out = []
    for th in THEMES:
        out.append({
            "id":         th["id"],
            "label":      th["label"],
            "sous_titre": th["sous_titre"],
            "kind":       th["kind"],
            "thesis":     th["thesis"],
            "inversion":  th["inversion"],
            "biais":      th["biais"],
            "regle_texte": th.get("regle_texte", ""),
            "declares":   len(th.get("tickers", [])),
        })
    return out


if __name__ == "__main__":
    u = univers_thematique()
    print(f"{len(THEMES_CURES)} thèmes curés + {len(THEMES_CALCULES)} calculés")
    print(f"{len(u)} tickers distincts cités par les thèmes curés")
    inv = themes_par_ticker()
    multi = {k: v for k, v in inv.items() if len(v) > 1}
    print(f"{len(multi)} titres appartiennent à plusieurs thèmes")
    for th in THEMES_CURES:
        print(f"  {th['id']:16s} {len(th['tickers']):3d} titres")
