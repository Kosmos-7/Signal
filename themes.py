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
            "refroidissement. Cette watchlist suit la chaîne complète, maillon par maillon, "
            "des puces jusqu'aux plateformes qui commandent et exploitent les centres de "
"données : c'est là que l'argent atterrit, quel que soit l'usage qui gagne. Et le "
            "vrai goulot n'est pas la gravure : c'est l'assemblage et les substrats, là où le "
            "pouvoir de prix est le plus fort."
        ),
        "inversion": (
            "Le retour sur investissement applicatif ne se matérialise pas et les hyperscalers "
            "digèrent leur capex : toute la chaîne se contracte en même temps, du silicium au "
            "transformateur. Supposer plus de trois à quatre ans de dépense linéaire est un pari "
            "de conviction, pas une base statistique. S'y ajoutent les contrôles à l'export et la "
            "dépendance à un seul fondeur avancé."
        ),
        "biais": (
            "C'est un thème de CONCENTRATION, pas de diversification : ses maillons montent "
            "et descendent ensemble, et il amplifie le pari tech déjà assumé par la watchlist "
            "principale. Il est aussi transverse aux secteurs (technologie, industrie, services "
"publics, matériaux), la règle de concentration sectorielle de l'agent ne le verra "
            "jamais comme un bloc, un calcul dédié s'en charge. Périmètre volontaire : la "
            "production d'électricité renouvelable en est exclue, c'est un pari de politique "
            "publique, pas d'infrastructure IA."
        ),
        # STRUCTURE PAR MAILLON (01/08/2026) : la chaîne était documentée en
        # commentaires — elle devient une DONNÉE, publiée dans universe.json,
        # pour que le site affiche la liste par couche. L'ordre des maillons
        # est l'ordre physique de la chaîne, c'est lui la pédagogie. Le champ
        # "tickers" attendu par tout le reste du code est dérivé plus bas
        # (concaténation dans l'ordre) — une seule source de vérité.
        "maillons": [
            {
                # Les processeurs de l'entraînement et de l'inférence.
                # ARM réintégré le 01/08/2026 (décision propriétaire, après
                # l'assouplissement de la règle des 5 ans) : 256 Md$, concepteur
                # de l'architecture CPU dominante — son absence amputait ce
                # maillon. IPO 2023, 2,9 ans : fiche avec avertissement
                # régression.
"label": "Compute · GPU, CPU & accélérateurs",
                "tickers": ["NVDA", "AVGO", "AMD", "ARM", "MRVL", "QCOM", "INTC"],
            },
            {
                # L'assemblage 2.5D/3D est le goulot le plus contraignant de la
                # chaîne : ce n'est pas la gravure qui rationne les livraisons
                # d'accélérateurs, c'est la capacité d'assemblage et les
                # substrats. Ce maillon était absent de la première version.
                "label": "Fonderie, équipement & packaging",
                "tickers": ["TSM", "ASML.AS", "AMAT", "LRCX", "KLAC", "TER", "ASM.AS",
                            "8035.T", "6857.T", "SNPS", "CDNS",
                            "ASX", "6146.T", "4062.T"],
            },
            {
                # La brique vendue au prix spot. SNDK (SanDisk) ajouté le
                # 01/08/2026 : scindé de WDC en février 2025 — WDC a gardé les
                # disques durs, la flash/NAND est repartie sous SNDK. La liste
                # datait d'avant la scission dans son esprit. ~180 Md$ au boom
                # NAND, 1,5 an d'historique : fiche avec avertissement
                # régression, comme les néoclouds.
                "label": "Mémoire & stockage",
                "tickers": ["MU", "000660.KS", "005930.KS", "WDC", "SNDK", "STX", "NTAP", "4063.T"],
            },
            {
                # Ce qui relie les accélérateurs entre eux, et limite la taille
                # des clusters d'entraînement autant que le nombre de puces.
                "label": "Réseau & optique",
                "tickers": ["ANET", "COHR", "LITE", "CIEN", "CSCO"],
            },
            {
                # Ce qu'on assemble et le bâtiment qui l'héberge — la dépense
                # atterrit littéralement là. S'y ajoutent les NÉOCLOUDS
                # (location de calcul GPU), entrés le 01/08/2026 sur décision
                # propriétaire, qui a supprimé la règle d'exclusion des
                # historiques < 5 ans : la fiche affiche à la place que la
                # droite de régression n'est pas exploitable en l'état.
                #   - CRWV  ~39 Md$, IPO mars 2025 (1,3 an)
                #   - NBIS  ~48 Md$, reprise oct. 2024 (1,8 an) — ex-Yandex
                #   - SHAZ  ~1,5 Md$, 0,4 an (~100 séances) : sous le plancher
                #     TECHNIQUE du screener (MM200/RSI exigent ~200 séances).
                #     Déclaré-non-scoré jusqu'à ~février 2027 — le run
                #     l'écartera proprement chaque semaine d'ici là. Exception
                #     assumée aussi sur le seuil des 25 Md$.
                # Ce maillon VEND de la capacité de calcul : Dell et HPE
                # vendent les serveurs, Equinix et Digital Realty louent le
                # mètre carré et le mégawatt, les néoclouds louent l'heure de
                # GPU. Leur client, c'est le maillon suivant, et c'est ce qui
                # justifie de ne pas fondre les deux.
                # Les libellés « vendeurs de capacité » et « acheteurs de
                # capacité » ont été essayés le 02/08/2026 pour rendre cette
                # opposition explicite, puis écartés : le propriétaire du dépôt
                # préfère les intitulés d'origine, plus descriptifs de ce que
                # les sociétés SONT que de la place qu'elles occupent dans la
                # chaîne. L'explication reste ici, où elle sert au lecteur du
                # code sans alourdir l'interface.
                "label": "Serveurs, data centers & néoclouds",
                "tickers": ["DELL", "HPE", "EQIX", "DLR",
                            "CRWV", "NBIS", "SHAZ"],
            },
            {
                # Les hyperscalers qui commandent et exploitent les centres de
                # données. Leur place est défendable parce que leurs capex SONT
                # la dépense d'infrastructure — ils possèdent les bâtiments.
                # La couche logicielle au-dessus (PLTR, SNOW, DDOG, MDB, NET)
                # est sortie le 01/08/2026 : c'est un pari sur les USAGES,
                # exactement ce que la thèse dit ne pas faire. Ces cinq titres
                # restent scorés comme candidats au top 30 et formeraient le
                # noyau d'un futur thème Cloud & Data.
                # Ce maillon ACHÈTE la capacité que le précédent vend, et
                # construit le reste lui-même. C'est le donneur d'ordre du
                # cycle : ses capex SONT le chiffre d'affaires des six autres
                # maillons. D'où l'intérêt de ne pas le fondre avec ses
                # fournisseurs, dont il ne partage ni le modèle ni le risque.
                "label": "Hyperscalers & cloud",
                "tickers": ["MSFT", "GOOGL", "AMZN", "META", "ORCL"],
            },
            {
                # Du réseau haute tension jusqu'à l'étage d'alimentation du
                # rack. NEE sorti le 01/08/2026 : premier développeur
                # renouvelable au monde, il contredisait frontalement le texte
                # des biais (« la production d'électricité renouvelable est
                # exclue — pari de politique publique »). VST reste : il vend
                # des électrons aux centres de données, c'est la thèse, pas un
                # pari réglementaire.
                # CEG et GEV réintégrés le 01/08/2026 (même décision que ARM) :
                # les deux acteurs les plus lisibles du raccordement électrique
                # de l'IA, écartés jusqu'ici par la règle des 5 ans (scissions
                # 2022 et 2024 — 4,5 et 2,3 ans d'historique). CEG vend des
                # électrons nucléaires aux data centers, comme VST : c'est la
                # thèse, pas le pari renouvelable que les biais excluent.
                "label": "Énergie & refroidissement",
                "tickers": ["VRT", "ETN", "SU.PA", "SIE.DE", "ABBN.SW", "ENR.DE",
                            "PWR", "VST", "CEG", "GEV", "CCJ",
                            "MPWR", "ON", "IFX.DE"],
            },
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
"contourner. Les voir côte à côte montre lequel de ces moteurs est payé cher, "
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
"sur la finance. Les péages se paient structurellement cher, le pilier valorisation "
            "les pénalise mécaniquement, un score moyen n'y signale pas une entreprise moyenne. "
            "À l'inverse les banques affichent des multiples optiquement bas qui reflètent un "
            "risque de bilan que le screener ne mesure pas."
        ),
        # Même structuration que le thème infra-IA : les familles étaient en
        # commentaires, elles deviennent une donnée publiée. Elles servent aussi
        # de clé d'illustration, chaque famille ayant sa photo.
        "maillons": [
            {"label": "Bilans · banques",
             "tickers": ["JPM", "BAC", "WFC", "GS", "MS", "TFC", "SCHW",
                         "HSBA.L", "BNP.PA", "UBSG.SW"]},
            {"label": "Bilans · assurance & courtage",
             "tickers": ["CB", "PGR", "ALV.DE", "CS.PA", "MUV2.DE", "MMC"]},
            {"label": "Flux · réseaux de paiement",
             "tickers": ["V", "MA", "AXP", "ADYEN.AS", "PYPL"]},
            {"label": "Gestion d'actifs & capital-investissement",
             "tickers": ["BLK", "BX", "KKR"]},
            {"label": "Péages · indices, notation & places de marché",
             "tickers": ["SPGI", "MCO", "MSCI", "ICE", "CME", "NDAQ",
                         "LSEG.L", "DB1.DE", "FICO"]},
        ],
    },
]

# Dérivation du champ "tickers" pour les thèmes structurés par maillon : tout
# le reste du code (univers, projection, agent, tests) lit th["tickers"] — la
# structure par couche ne doit pas créer une seconde source de vérité.
for _th in THEMES_CURES:
    if "maillons" in _th:
        _th["tickers"] = [t for _m in _th["maillons"] for t in _m["tickers"]]

# ── ÉLIGIBILITÉ AU PEA ───────────────────────────────────────────────────────
# LA RÈGLE. Une action est éligible au PEA si la société qui l'émet a son SIÈGE
# SOCIAL dans l'Union européenne ou dans un État de l'Espace économique
# européen ayant une convention d'assistance administrative avec la France
# (Islande, Norvège, Liechtenstein), et si elle est soumise à l'impôt sur les
# sociétés ou à un impôt équivalent. Article L221-31 du code monétaire et
# financier.
#
# CE QUE LA RÈGLE NE DIT PAS, et c'est tout l'intérêt de cette liste :
# ni la place de cotation, ni la devise, ni la nationalité perçue de
# l'entreprise n'entrent dans le critère. Nebius est une N.V. néerlandaise
# cotée au Nasdaq en dollars, dont l'activité est ailleurs : elle est éligible.
# Accenture est une plc irlandaise cotée à New York : éligible. Symétriquement,
# une société britannique reste inéligible depuis le Brexit quelle que soit son
# ancienneté à Londres, et une suisse ne l'a jamais été, la Suisse n'étant pas
# dans l'EEE.
#
# POURQUOI C'EST UNE DONNÉE ÉCRITE À LA MAIN. Aucune source du projet ne porte
# le siège social : Yahoo publie un pays qui est celui du siège opérationnel ou
# de la place de cotation, pas celui du siège statutaire. Les deux diffèrent
# précisément dans les cas qui nous intéressent. C'est le même constat que pour
# la table des marques dans photos_marques.py : le savoir qui manque est
# exactement celui qu'aucune API ne porte.
#
# DATE DE VÉRIFICATION : 2026-08-03. Un domicile se change — une redomiciliation
# fait perdre l'éligibilité du jour au lendemain, sans que rien dans les données
# de marché ne bouge. Cette liste se revérifie, elle ne se déduit pas.
#
# CE QUE CETTE LISTE N'EST PAS : une autorisation d'achat. L'éligibilité
# juridique du titre et l'acceptation de la ligne par le courtier sont deux
# choses différentes, en particulier pour les lignes cotées à New York que
# plusieurs courtiers français refusent au PEA ou n'offrent que sur leur ligne
# européenne. À vérifier avant de passer un ordre, jamais après.
PEA_VERIFIE_LE = "2026-08-03"

PEA_ELIGIBLES = {
    # ── Siège dans l'UE, cotée en Europe : le cas sans surprise ──────────────
    "AI.PA":     "France · Air Liquide SA",
    "AM.PA":     "France · Dassault Aviation SA",
    "BNP.PA":    "France · BNP Paribas SA",
    "CAP.PA":    "France · Capgemini SE",
    "CS.PA":     "France · AXA SA",
    "DSY.PA":    "France · Dassault Systèmes SE",
    "HO.PA":     "France · Thales SA",
    "MC.PA":     "France · LVMH SE",
    "OR.PA":     "France · L'Oréal SA",
    "RMS.PA":    "France · Hermès International SCA",
    "SAF.PA":    "France · Safran SA",
    "SU.PA":     "France · Schneider Electric SE",
    "TTE.PA":    "France · TotalEnergies SE",
    "ADS.DE":    "Allemagne · adidas AG",
    "ALV.DE":    "Allemagne · Allianz SE",
    "DB1.DE":    "Allemagne · Deutsche Börse AG",
    "ENR.DE":    "Allemagne · Siemens Energy AG",
    "FRE.DE":    "Allemagne · Fresenius SE & Co. KGaA",
    "IFX.DE":    "Allemagne · Infineon Technologies AG",
    "MRK.DE":    "Allemagne · Merck KGaA",
    "MUV2.DE":   "Allemagne · Münchener Rück AG",
    "RHM.DE":    "Allemagne · Rheinmetall AG",
    "RWE.DE":    "Allemagne · RWE AG",
    "SAP.DE":    "Allemagne · SAP SE",
    "SIE.DE":    "Allemagne · Siemens AG",
    "AD.AS":     "Pays-Bas · Koninklijke Ahold Delhaize N.V.",
    "ADYEN.AS":  "Pays-Bas · Adyen N.V.",
    "ASM.AS":    "Pays-Bas · ASM International N.V.",
    "ASML.AS":   "Pays-Bas · ASML Holding N.V.",
    "HEIA.AS":   "Pays-Bas · Heineken N.V.",
    "IMCD.AS":   "Pays-Bas · IMCD N.V.",
    "PHIA.AS":   "Pays-Bas · Koninklijke Philips N.V.",
    "RAND.AS":   "Pays-Bas · Randstad N.V.",
    # Airbus est l'illustration inverse des cas ci-dessous : cotée à Paris,
    # perçue comme franco-allemande, mais statutairement néerlandaise. Éligible
    # dans les deux lectures, ce qui la rend inoffensive — on la note quand même,
    # parce que « cotée à Paris » n'est jamais la raison de l'éligibilité.
    "AIR.PA":    "Pays-Bas · Airbus SE (siège à Leyde, cotée à Paris)",
    "IBE.MC":    "Espagne · Iberdrola SA",
    "LDO.MI":    "Italie · Leonardo S.p.A.",
    "NOVO-B.CO": "Danemark · Novo Nordisk A/S",
    "ORSTED.CO": "Danemark · Ørsted A/S",
    "VWS.CO":    "Danemark · Vestas Wind Systems A/S",
    "SAAB-B.ST": "Suède · Saab AB",

    # ── Siège dans l'UE, cotée aux États-Unis : la subtilité ─────────────────
    # Ces huit titres cotent en dollars à New York et n'ont rien d'européen au
    # premier regard. Ce sont pourtant des sociétés de droit néerlandais ou
    # irlandais, donc éligibles. C'est la moitié intéressante de cette liste :
    # celle qu'on ne trouve pas en filtrant sur la place de cotation.
    "NBIS":      "Pays-Bas · Nebius Group N.V. (Nasdaq)",
    "STM":       "Pays-Bas · STMicroelectronics N.V. (NYSE)",
    "NXPI":      "Pays-Bas · NXP Semiconductors N.V. (Nasdaq)",
    "RACE":      "Pays-Bas · Ferrari N.V. (NYSE)",
    "ACN":       "Irlande · Accenture plc (NYSE)",
    "ETN":       "Irlande · Eaton Corporation plc (NYSE)",
    "MDT":       "Irlande · Medtronic plc (NYSE)",
    "STX":       "Irlande · Seagate Technology Holdings plc (Nasdaq)",
}

# INÉLIGIBLES DE L'UNIVERS, avec le motif. Ils sont listés plutôt qu'omis :
# l'absence d'un titre qu'on croyait européen doit avoir une raison lisible,
# sans quoi on la reprend en boucle à chaque relecture.
PEA_INELIGIBLES = {
    # Le Brexit a fait sortir le Royaume-Uni de l'UE : aucune société de droit
    # britannique n'est plus éligible, quelle que soit son ancienneté à Londres.
    "AZN.L":   "Royaume-Uni, hors UE depuis le Brexit",
    "BA.L":    "Royaume-Uni, hors UE depuis le Brexit",
    "DGE.L":   "Royaume-Uni, hors UE depuis le Brexit",
    "HSBA.L":  "Royaume-Uni, hors UE depuis le Brexit",
    "LSEG.L":  "Royaume-Uni, hors UE depuis le Brexit",
    "REL.L":   "Royaume-Uni, hors UE depuis le Brexit",
    "RR.L":    "Royaume-Uni, hors UE depuis le Brexit",
    "ULVR.L":  "Royaume-Uni, hors UE depuis le Brexit",
    "ARM":     "Royaume-Uni (Arm Holdings plc) — et le titre coté est un ADR",
    # La Suisse n'est pas dans l'EEE : elle n'a jamais été éligible, ce qui
    # surprend plus d'un épargnant qui range Nestlé ou ABB parmi les valeurs
    # européennes.
    "ABBN.SW": "Suisse, hors EEE",
    "NESN.SW": "Suisse, hors EEE",
    "UBSG.SW": "Suisse, hors EEE",
    "CB":      "Suisse (Chubb Limited), hors EEE",
    "NVS":     "Suisse (Novartis AG), hors EEE",
    "RHHBY":   "Suisse (Roche) — et le titre coté est un ADR",
    "TRI":     "Canada (Thomson Reuters Corporation)",
    # Cas limite, et le seul de la liste : siège statutaire à Dublin, mais
    # résidence fiscale au Royaume-Uni revendiquée dans les documents déposés.
    # La condition « soumise à l'impôt sur les sociétés » devient discutable, et
    # les courtiers ne la tranchent pas tous pareil. Écarté par prudence plutôt
    # que publié avec une réserve que personne ne lira. Accessoirement le
    # symbole LIN.DE est mort depuis la sortie de cote de Francfort en 2023.
    "LIN.DE":  "Linde plc : siège en Irlande mais résidence fiscale au "
               "Royaume-Uni — éligibilité contestée, écarté par prudence",
    # Les certificats de dépôt (ADR) ne sont pas des actions : quel que soit le
    # siège de l'émetteur sous-jacent, ils ne sont pas logeables au PEA.
    "BABA":    "Chine, et titre coté sous forme d'ADR",
    "PDD":     "Chine, et titre coté sous forme d'ADR",
    "TCEHY":   "Chine, et titre coté sous forme d'ADR",
    "MUFG":    "Japon, et titre coté sous forme d'ADR",
    "TM":      "Japon, et titre coté sous forme d'ADR",
    "SONY":    "Japon, et titre coté sous forme d'ADR",
    "SE":      "Singapour / Îles Caïmans (Sea Limited), et ADR",
    "ASX":     "Taïwan, et titre coté sous forme d'ADR",
    "TSM":     "Taïwan, et titre coté sous forme d'ADR",
}

# Nombre de titres publiés par la watchlist PEA. Vingt : c'est ce qui a été
# demandé, et c'est aussi à peu près la moitié des éligibles, donc une sélection
# qui sélectionne vraiment.
TOP_PEA = 20

# Le thème est déclaré ICI et non dans le littéral THEMES_CURES plus haut :
# sa liste de titres EST le registre ci-dessus, et une liste recopiée serait une
# seconde source de vérité, donc une divergence à venir.
THEMES_CURES.append({
    "id": "pea",
    "label": "Éligibles PEA",
    "sous_titre": "Les 20 meilleurs scores logeables dans un PEA",
    # Ni thèse ni secteur : le critère d'entrée est JURIDIQUE. Un kind à part
    # évite de faire passer une contrainte fiscale pour une conviction
    # d'investissement — c'est la même exigence que le refus de « marge de
    # sécurité » rappelé en tête de ce fichier.
    "kind": "filtre",
    "regle_texte": (
        "Entrent dans la liste les sociétés dont le SIÈGE SOCIAL est situé dans "
        "l'Union européenne ou dans l'Espace économique européen et qui sont "
        "soumises à l'impôt sur les sociétés (article L221-31 du code monétaire "
        "et financier). Parmi elles, les vingt meilleurs scores du run sont "
        "publiés. Ni la place de cotation, ni la devise, ni la nationalité "
        "perçue de l'entreprise n'entrent dans le critère."
    ),
    "thesis": (
        "Le PEA exonère d'impôt sur le revenu les plus-values et les dividendes "
        "après cinq ans de détention, seuls les prélèvements sociaux restant dus. "
        "L'avantage est considérable et il a un prix : l'enveloppe n'accepte que "
        "les sociétés dont le siège social est européen. Cette liste montre ce "
        "que cette contrainte laisse réellement disponible, et surtout ce qu'un "
        "filtre par place de cotation ferait manquer. Huit des titres retenus "
        "cotent en dollars à New York — Nebius, STMicroelectronics, NXP, Ferrari "
        "sont des sociétés néerlandaises, Accenture, Eaton, Medtronic et Seagate "
        "des sociétés irlandaises. Aucune ne ressemble à une valeur européenne, "
        "toutes le sont au sens du code monétaire et financier."
    ),
    # Une contrainte fiscale ne s'invalide pas comme une thèse : ce qui la
    # périme, c'est un changement de droit ou de domicile, pas un retournement
    # de marché. Le champ garde son libellé sur le site, son contenu dit la
    # vérité du thème.
    "inversion": (
        "Cette liste ne se démode pas, elle se périme. Deux évènements la rendent "
        "fausse sans qu'aucun cours ne bouge : une société qui transfère son siège "
        "hors de l'UE perd son éligibilité du jour au lendemain, et une réforme du "
        "PEA peut déplacer le critère lui-même. Le registre porte donc une date de "
        "vérification, et une éligibilité ne se déduit jamais d'une donnée de "
        "marché. Vérification la plus récente : " + PEA_VERIFIE_LE + "."
    ),
    "biais": (
        "PIÈGE PRINCIPAL, à lire avant tout ordre : l'éligibilité juridique d'un "
        "titre et l'acceptation de la ligne par ton courtier sont deux choses "
        "différentes. Plusieurs courtiers français refusent au PEA les lignes "
        "cotées à New York, ou n'acceptent que la ligne européenne quand elle "
        "existe. À vérifier avant de passer l'ordre, jamais après. Les certificats "
        "de dépôt (ADR) ne sont en aucun cas logeables, quel que soit le siège de "
        "l'émetteur.\n\n"
        "Ce filtre est FISCAL, pas économique : rien ne dit qu'un univers "
        "restreint par le lieu du siège social se comporte mieux qu'un autre, et "
        "il n'y a aucune raison qu'il le fasse. Il optimise l'imposition, pas la "
        "sélection. Conséquence directe : la liste est presque vide de technologie "
        "américaine, qui domine la watchlist principale, et concentrée sur "
        "l'industrie, le luxe, la santé et la finance européennes. C'est le prix "
        "de l'enveloppe, pas un jugement sur ces secteurs.\n\n"
        "Enfin le PEA a ses propres exclusions, indépendantes du siège social : "
        "les foncières cotées de type SIIC en sont écartées, et le plafond de "
        "versements est de 150 000 €. Ce thème ne les modélise pas."
    ),
    "tickers": sorted(PEA_ELIGIBLES),
    "top": TOP_PEA,
})

# ── THÈMES CALCULÉS ──────────────────────────────────────────────────────────
# Aucun n'est publié dans cette version. Le mécanisme reste en place côté
# screener (règle sur le breakdown + tri dédié) : réactiver « décote vs
# tendance » ou « qualité durable » consiste à réintroduire une entrée ici.
THEMES_CALCULES = []

# ── ÉCARTÉS APRÈS VALIDATION (run CI du 2026-08-01, 81 symboles testés) ──────
# Ces titres avaient leur place dans une thèse mais échouent aux critères
# d'inclusion du projet. Ils sont listés ici plutôt que supprimés en silence :
# quelqu'un les cherchera, et l'absence doit avoir une raison lisible.
#
# HISTORIQUE DU REGISTRE — CEG, GEV et ARM y ont figuré quelques heures : tous
# trois écartés le matin du 01/08 par la règle « historique < 5 ans », tous
# trois RÉINTÉGRÉS le soir même, après que cette règle est devenue un simple
# avertissement (cf. note plus bas). ARM (256 Md$) rejoint le maillon calcul,
# CEG et GEV le maillon énergie — leurs fiches porteront l'avertissement
# régression tant que leurs historiques resteront courts.
ECARTES_VALIDATION = {
"ROG.SW": "symbole introuvable chez Yahoo, remplacé par l'ADR RHHBY",
    "BESI.AS": "capitalisation ~17 Md$ < seuil 25 Md$ (collage hybride)",
    "EFX":     "capitalisation ~20 Md$ < seuil 25 Md$",
    # Complément du 01/08 — recevables depuis l'assouplissement de la règle
    # des 5 ans, mais PAS réintégrés d'office : chacun attend une décision
    # explicite (contrairement à ARM/CEG/GEV, réintégrés sur demande).
"ALAB": "historique 2,4 ans (IPO 2024), recevable depuis le 01/08, en attente de décision",
"CRDO": "historique 4,5 ans, recevable depuis le 01/08, en attente de décision",
"GFS": "historique 4,8 ans, recevable depuis le 01/08, en attente de décision",
    "AMKR":    "capitalisation ~12 Md$ < seuil 25 Md$ (assemblage)",
    "6920.T":  "capitalisation ~23 Md$ < seuil 25 Md$ (inspection de masques EUV)",
    "FN":      "capitalisation ~16 Md$ < seuil 25 Md$ (sous-traitance optique)",
    "SMCI":    "capitalisation ~18 Md$ < seuil 25 Md$ (serveurs)",
"NVT": "capitalisation ~25 Md$, au seuil, écarté faute de marge",
"HUBB": "capitalisation ~25 Md$, au seuil, écarté faute de marge",
    "MOD":     "capitalisation ~11 Md$ < seuil 25 Md$ (refroidissement)",
    "8036.T":  "symbole introuvable chez Yahoo",
}
# NOTE 01/08/2026 — la règle « historique < 5 ans = exclusion » est SUPPRIMÉE
# (décision propriétaire, entrée des néoclouds CRWV/NBIS/SHAZ). Un historique
# court vaut désormais avertissement : la fiche affiche que la droite de
# régression n'est pas exploitable en l'état. Conséquence : les écartés
# ci-dessus pour ce seul motif (CEG, GEV, ARM, ALAB, CRDO, GFS) redeviennent
# des candidats recevables — ils ne sont PAS réintégrés d'office, chacun
# attend une décision explicite. Le plancher technique demeure : ~200 séances,
# sans quoi MM200/RSI sont incalculables et le screener écarte le titre au run.

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
            # Structure par couche (optionnelle) : le site groupe le rail par
            # maillon quand elle est présente. Tickers DÉCLARÉS — le front
            # n'affiche que ceux réellement scorés (membres publiés).
            **({"maillons": [{"label": m["label"], "tickers": list(m["tickers"])}
                             for m in th["maillons"]]} if "maillons" in th else {}),
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
