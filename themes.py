# themes.py — Taxonomie des watchlists thématiques (source unique de vérité)
#
# Depuis août 2026, Signal ne publie plus une seule watchlist mais une homepage
# de watchlists : la principale (top 30 toutes catégories, inchangée) et des
# vues thématiques.
#
# ARCHITECTURE — « un seul scoring, N projections »
# Chaque titre est scoré EXACTEMENT UNE FOIS par screener.py. Une watchlist
# thématique n'est qu'un filtre + tri sur ces mêmes résultats : coût API
# marginal nul pour tout titre déjà présent dans l'univers. UNIVERS (screener.py)
# est DÉRIVÉ de ce module — ajouter un ticker à un thème l'ajoute à l'univers.
#
# DEUX NATURES DE THÈMES
#   - « curé »   : liste de titres maintenue à la main (semis, santé…). Le
#                  jugement est humain et donc contestable — il est publié.
#   - « calculé » : sélection produite par une RÈGLE CHIFFRÉE sur le breakdown du
#                  screener, recalculée à chaque run (décote, qualité). Zéro
#                  maintenance, et surtout : personne d'autre ne peut les
#                  produire, puisqu'elles sortent de notre propre moteur.
#
# DOCTRINE DE NOMMAGE (cf. apprendre.html — refus de « marge de sécurité »)
# On ne colle jamais sur une mesure l'étiquette d'un concept qu'on ne calcule
# pas. Le screener mesure marge nette, marge FCF, ROE, croissance et dette : il
# ne mesure NI la durabilité NI l'avantage concurrentiel. D'où « Qualité
# durable » et non « moat » ; « secteur » et non « thèse » quand le thème n'est
# qu'un regroupement sectoriel.
#
# CE QUE LES THÈMES NE SONT PAS
# Ils ne sont justifiés par aucun backtest et ne prétendent améliorer aucune
# performance. Ils structurent la lecture d'un univers devenu trop large pour
# une seule liste de 30 lignes — rien de plus.

# ── THÈMES CURÉS ─────────────────────────────────────────────────────────────
# Chaque thème : id (slug immuable, sert d'URL), label, kind, thesis, inversion
# (ce qui invaliderait la thèse — obligatoire, c'est le garde-fou anti-promotion),
# biais (ce que le thème concentre), tickers.

THEMES_CURES = [
    {
        "id": "semis",
        "label": "Semi-conducteurs",
        "sous_titre": "Logique, fonderie, équipement",
        "kind": "these",
        "thesis": "Le calcul et la fabrication du silicium sont l'infrastructure physique de l'IA, et la demande transite par un nombre très réduit d'acteurs non substituables à court terme : lithographie EUV, nœuds avancés, équipement de production, outils de conception. C'est un pari sur la PERSISTANCE du capex, pas sur son accélération.",
        "inversion": "Digestion du capex des hyperscalers, contrôles à l'export, ou concentration excessive du risque sur un seul fondeur taïwanais.",
        "biais": "Ce thème CONCENTRE le tilt tech déjà assumé de la watchlist principale — il ne diversifie rien. Deux fenêtres de régression y cohabitent (25 ans pour les équipementiers cycliques, 10 ans pour les concepteurs) : les z-scores ne sont pas directement comparables entre eux, la fenêtre est affichée à côté.",
        "tickers": [
            "NVDA", "AVGO", "TSM", "AMD", "INTC", "QCOM", "ADI", "TXN", "MRVL",
            "NXPI", "STM", "IFX.DE", "SNPS", "CDNS",
            "ASML.AS", "AMAT", "LRCX", "KLAC", "TER", "ASM.AS", "BESI.AS",
            "8035.T", "6857.T",
        ],
    },
    {
        "id": "memoire",
        "label": "Mémoire & stockage",
        "sous_titre": "Le cycle commodity du silicium",
        "kind": "these",
        "thesis": "La mémoire est la seule brique du silicium vendue au prix spot d'une commodité : hors pénurie, aucun pouvoir de prix, et des marges qui passent de négatives à plus de 40 % en dix-huit mois. Le moteur n'est pas la qualité des entreprises mais la POSITION DANS LE CYCLE.",
        "inversion": "Retournement des prix contrats et ajouts de capacité 2027-2028 : la surcapacité est le mode de panne historique de ce marché.",
        "biais": "Statut « observation », pas thèse d'achat : le catalyseur de ce cycle est largement consommé. Le screener ne sait PAS distinguer la mémoire cyclique des concepteurs à croissance séculaire — c'est précisément pourquoi ce thème existe séparément des semi-conducteurs, avec lesquels il partage ses équipementiers.",
        "tickers": [
            "MU", "000660.KS", "005930.KS", "STX", "WDC", "NTAP",
            "LRCX", "AMAT", "KLAC", "ASM.AS", "BESI.AS",
            "8035.T", "6857.T", "4063.T",
        ],
    },
    {
        "id": "ia",
        "label": "Intelligence artificielle",
        "sous_titre": "La chaîne de dépendance du capex",
        "kind": "these",
        "thesis": "Suivre la dépense IA là où elle atterrit physiquement, maillon par maillon : silicium, réseau, énergie et refroidissement, plateformes de données, puis applicatif. Le thème n'est PAS « les grandes valeurs tech qui parlent d'IA » — c'est la chaîne qui encaisse le chèque.",
        "inversion": "Le retour sur investissement applicatif ne se matérialise pas et la dépense s'arrête en amont. Toute thèse supposant plus de trois à quatre ans de capex linéaire est un pari de conviction, pas une base statistique.",
        "biais": "Recouvrement massif avec les semi-conducteurs et la watchlist principale. Surtout : ses membres se dispersent sur quatre secteurs différents, donc la règle de concentration sectorielle de l'agent ne les verra JAMAIS comme un bloc alors qu'ils baissent ensemble.",
        "tickers": [
            "NVDA", "AVGO", "TSM", "ASML.AS", "MU", "MRVL", "ANET",
            "MSFT", "GOOGL", "AMZN", "META", "ORCL", "PLTR", "NOW", "CRM", "ADBE",
            "VRT", "ETN", "SU.PA", "CEG", "PWR",
        ],
    },
    {
        "id": "robotique",
        "label": "Robotique & automatisation",
        "sous_titre": "Base installée et cycle capex industriel",
        "kind": "these",
        "thesis": "L'automatisation comme réponse structurelle au coût et à la rareté du travail industriel, doublée de la relocalisation des chaînes de production. Les leaders de la robotique industrielle sont massivement japonais, avec des bases installées difficiles à déloger.",
        "inversion": "Un cycle de capex industriel classique déguisé en thème séculaire : le carnet de commandes suit la production manufacturière, pas une tendance de long terme.",
        "biais": "Forte exposition au Japon et au yen. Les valeurs japonaises entrent pour la première fois dans l'univers de Signal — leurs données fondamentales via Yahoo sont moins complètes que pour les valeurs américaines.",
        "tickers": [
            "6954.T", "6861.T", "6501.T", "6273.T",
            "ABBN.SW", "SIE.DE", "SU.PA", "DSY.PA",
            "ROK", "EMR", "HON", "PH", "AME", "TER", "ISRG", "IFX.DE", "ADI", "DE",
        ],
    },
    {
        "id": "finance",
        "label": "Finance",
        "sous_titre": "Banques, assurance, paiements, gestion d'actifs",
        "kind": "secteur",
        "thesis": "Regroupement SECTORIEL, pas thèse d'investissement : les métiers de bilan (banques, assureurs) parient sur les taux et le risque de crédit, les réseaux de paiement encaissent un volume sans porter ce risque. Deux moteurs très différents sous un même libellé — les péages d'infrastructure ont leur propre thème.",
        "inversion": "Sans objet : un secteur ne s'invalide pas. Le risque propre est la sensibilité commune aux taux et au cycle de crédit.",
        "biais": "Le libellé « Finance » vient de la classification sectorielle, pas d'une conviction. Ne pas le lire comme une recommandation de surpondérer le secteur.",
        "tickers": [
            "JPM", "BAC", "WFC", "GS", "MS", "TFC", "SCHW", "AXP",
            "HSBA.L", "BNP.PA", "UBSG.SW",
            "CB", "PGR", "ALV.DE", "CS.PA", "MUV2.DE", "MMC",
            "BLK", "BX", "KKR",
            "V", "MA", "ADYEN.AS", "PYPL",
        ],
    },
    {
        "id": "peages",
        "label": "Monopoles d'information",
        "sous_titre": "Indices, notation, places de marché, référentiels",
        "kind": "these",
        "thesis": "Des péages sur le fonctionnement des marchés : indices, notations, données de référence, chambres de compensation. Ces sociétés facturent un abonnement ou une commission sur des flux qu'elles ne financent pas, avec des coûts de changement élevés et des besoins en capital faibles. Le profil de qualité le plus régulier de l'univers.",
        "inversion": "Régulation des tarifs (le sujet revient périodiquement sur les indices et la notation), ou désintermédiation par des données ouvertes.",
        "biais": "Ces titres se paient structurellement cher — le pilier valorisation du score les pénalise mécaniquement. Un score moyen ne signifie pas ici une entreprise moyenne.",
        "tickers": [
            "SPGI", "MCO", "MSCI", "ICE", "CME", "NDAQ",
            "LSEG.L", "DB1.DE", "REL.L", "TRI", "FICO", "EFX", "V", "MA",
        ],
    },
    {
        "id": "compounders",
        "label": "Compounders industriels",
        "sous_titre": "Rentabilité élevée et régulière sur la durée",
        "kind": "these",
        "thesis": "Des industriels et sociétés de services dont la rentabilité du capital reste élevée cycle après cycle : bases installées, pièces détachées et contrats de maintenance, positions locales difficiles à attaquer. La composition du capital sur longue période plutôt que la croissance rapide.",
        "inversion": "La régularité passée n'est pas un avantage concurrentiel prouvé — elle peut n'être que le reflet d'un cycle industriel favorable prolongé.",
        "biais": "Ce thème s'appelait « moat » dans sa première formulation, et ne s'appelle plus ainsi : le screener mesure des marges, un ROE et un endettement, il ne mesure NI la durabilité NI l'avantage concurrentiel. Nous ne collons pas sur un tri de ratios l'étiquette d'un concept que nous ne calculons pas.",
        "tickers": [
            "ROP", "DHR", "ITW", "PH", "ETN", "HON", "EMR", "AME",
            "UNP", "WM", "RSG", "CPRT", "FAST", "CTAS", "TDG",
            "SU.PA", "SIE.DE", "SAF.PA", "LIN.DE", "SHW", "CAT", "DE",
        ],
    },
    {
        "id": "conso",
        "label": "Consommation & marques durables",
        "sous_titre": "Pouvoir de fixation des prix",
        "kind": "these",
        "thesis": "Des marques capables de répercuter l'inflation sans perdre de volume, sur une demande peu corrélée au cycle économique. C'est le prolongement visible de la « poche d'assurance » déjà présente dans l'univers depuis juin 2026 : des leaders non-tech ultra-liquides, dormants tant que la tech mène.",
        "inversion": "Érosion des marques par les marques de distributeur et les nouveaux canaux de vente, et volumes structurellement plats masqués par la hausse des prix.",
        "biais": "Ces titres scoreront structurellement bas sur le timing tant que la tech mène le marché — c'est le principe même d'une poche d'assurance, pas un défaut du thème. Beaucoup sont sous leur tendance longue depuis 2022.",
        "tickers": [
            "KO", "PEP", "PG", "CL", "MDLZ", "HSY", "PM", "MCD", "COST", "WMT",
            "NESN.SW", "OR.PA", "ULVR.L", "DGE.L", "HEIA.AS", "AD.AS", "EL", "NKE",
        ],
    },
    {
        "id": "sante",
        "label": "Santé & longévité",
        "sous_titre": "Thérapies, dispositifs, outils de recherche",
        "kind": "these",
        "thesis": "La démographie et l'innovation thérapeutique portent une demande peu cyclique. Les fabricants d'outils, d'équipements et de dispositifs captent la dépense de santé sans porter le risque binaire d'un essai clinique — c'est le maillon le moins spéculatif de la chaîne.",
        "inversion": "Pression politique sur les prix des médicaments, falaises de brevets, et concentration croissante du secteur sur une seule classe thérapeutique.",
        "biais": "Périmètre volontairement limité aux grandes capitalisations : la biotech en phase précoce est hors du champ de compétence assumé du projet. C'est le meilleur apport de diversification de l'ensemble des thèmes.",
        "tickers": [
            "LLY", "NOVO-B.CO", "AMGN", "VRTX", "REGN", "GILD", "BIIB",
            "AZN.L", "ROG.SW", "NVS", "MRK", "ABBV", "PFE",
            "ISRG", "SYK", "MDT", "BSX", "DHR", "TMO", "ABT", "ZTS",
            "UNH", "CI", "FRE.DE", "MRK.DE", "PHIA.AS",
        ],
    },
    {
        "id": "defense",
        "label": "Défense & souveraineté",
        "sous_titre": "Réarmement européen",
        "kind": "these",
        "thesis": "Des budgets pluriannuels votés créent une demande politiquement contrainte, peu sensible au cycle économique, avec des carnets de commandes visibles sur plusieurs années. L'Europe est passée en quelques années d'un sous-investissement chronique à un rattrapage financé.",
        "inversion": "Le catalyseur est en grande partie derrière nous : les multiples intègrent déjà plusieurs années de hausse des budgets. Un apaisement géopolitique ou un arbitrage budgétaire défavorable invaliderait la thèse.",
        "biais": "Statut « observation » plutôt que thèse d'achat, pour la même raison que la mémoire : la revalorisation a déjà eu lieu. Thème sensible pour certains lecteurs — il est publié comme les autres, sans jugement moral implicite.",
        "tickers": [
            "RHM.DE", "BA.L", "HO.PA", "LDO.MI", "SAAB-B.ST", "AM.PA",
            "AIR.PA", "SAF.PA", "RR.L", "SIE.DE", "LMT", "RTX", "NOC",
        ],
    },
    {
        "id": "electrification",
        "label": "Électrification & réseaux",
        "sous_titre": "Le débouché physique de l'IA et de la transition",
        "kind": "these",
        "thesis": "Tout ce qui transporte, transforme et refroidit l'électricité : réseau, transformateurs, production pilotable, nucléaire, refroidissement de centres de données. La contrainte de la décennie n'est plus la puce, c'est le mégawatt disponible et le délai de raccordement.",
        "inversion": "Un cycle de capex de service public classique, exposé au coût du capital et au calendrier réglementaire — deux facteurs qui ont déjà lourdement pénalisé l'éolien offshore.",
        "biais": "Le thème le plus transverse de tous : ses membres se répartissent sur quatre secteurs distincts (services publics, industrie, matériaux, énergie). Un portefeuille entièrement construit dessus serait invisible à la règle de concentration sectorielle — c'est documenté et corrigé côté agent.",
        "tickers": [
            "GEV", "CEG", "VST", "PWR", "VRT", "ETN", "EMR",
            "SU.PA", "SIE.DE", "ABBN.SW", "ENR.DE", "CCJ",
            "NEE", "IBE.MC", "RWE.DE", "ORSTED.CO", "VWS.CO", "FSLR", "LIN.DE", "TTE.PA",
        ],
    },
]

# ── THÈMES CALCULÉS ──────────────────────────────────────────────────────────
# Aucune liste à maintenir : la sélection est une règle sur le breakdown,
# réévaluée à chaque run sur l'univers entier. La règle est publiée telle quelle
# sur la carte du thème — c'est ce qui la rend vérifiable.

def _regle_decote(b):
    """Titres nettement sous leur trajectoire longue, fondamentaux intacts.

    Le seuil de -1σ et le garde-fou qualité reprennent exactement la logique du
    bonus « décote-qualité » du screener : on ne surface pas un couteau qui
    tombe. La décote reste une INFORMATION — la référence est une trajectoire
    de prix passée, pas une valeur intrinsèque (cf. règle 14 de l'agent).
    """
    z = b.get("regression_z")
    return z is not None and z <= -1.0 and b.get("qualite", 0) >= 25

def _regle_qualite(b):
    """Le haut du panier sur le seul pilier qualité, tous secteurs confondus.

    32/45 est le seuil qui sélectionne le quintile supérieur de l'univers.
    Mesure des marges, du ROE, de la croissance et du bilan — PAS de la
    durabilité ni de l'avantage concurrentiel.
    """
    return b.get("qualite", 0) >= 32

THEMES_CALCULES = [
    {
        "id": "decote",
        "label": "Décote vs tendance",
        "sous_titre": "Le prix s'écarte à la baisse de sa propre trajectoire",
        "kind": "calcule",
        "regle_texte": "z-score de régression ≤ −1,0σ et score qualité ≥ 25/45",
        "thesis": "Les titres dont le cours s'écarte le plus à la baisse de leur propre trajectoire longue, filtrés sur des fondamentaux intacts, triés du plus décoté au moins décoté. Cette vue expose une information que le tri par score global noie.",
        "inversion": "Une décote extrême signifie souvent que le marché price un changement STRUCTUREL réel : disruption, nouvelle concurrence, régulation. Si le business est durablement altéré, la trajectoire passée ne reviendra jamais.",
        "biais": "Ce n'est PAS une mesure de valeur et ne doit jamais être appelée « marge de sécurité » : la référence est une trajectoire de prix passée, pas une valeur intrinsèque issue de l'analyse des profits et du bilan.",
        "regle": _regle_decote,
        "tri": lambda b: b.get("regression_z", 0),   # croissant : le plus décoté d'abord
    },
    {
        "id": "qualite",
        "label": "Qualité durable",
        "sous_titre": "Le haut du panier sur le pilier qualité",
        "kind": "calcule",
        "regle_texte": "score qualité ≥ 32/45 (marges, ROE, croissance, bilan)",
        "thesis": "Les entreprises les mieux notées sur le seul pilier qualité du score, tous secteurs confondus : marge nette, marge de free cash flow, rentabilité du capital, régularité de la croissance et solidité du bilan.",
        "inversion": "La qualité passée persiste mieux que la croissance passée, mais elle se paie — un titre de qualité acheté trop cher reste un mauvais investissement.",
        "biais": "Mesure ce que le screener sait calculer : des ratios comptables sur les exercices publiés. Ni la durabilité de l'avantage, ni la qualité du management, ni la solidité de la culture d'entreprise n'entrent dans ce chiffre.",
        "regle": _regle_qualite,
        "tri": lambda b: -b.get("qualite", 0),        # décroissant : le meilleur d'abord
    },
]

THEMES = THEMES_CURES + THEMES_CALCULES
THEMES_BY_ID = {t["id"]: t for t in THEMES}

# Nombre de titres affichés par vue thématique (les autres membres restent
# accessibles, mais le « top » publié est borné pour rester lisible).
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
