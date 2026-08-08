# themes.py — Taxonomie des watchlists thématiques (source unique de vérité)
#
# Signal publie QUATRE listes : la watchlist principale (top 30 de l'univers,
# toutes catégories) et trois vues thématiques.
#
# ARCHITECTURE — « un seul scoring, N projections »
# Chaque titre est scoré EXACTEMENT UNE FOIS par screener.py. Une watchlist
# thématique n'est qu'un filtre + tri sur ces mêmes résultats : coût API
# marginal nul. L'univers du screener est l'union de sa liste historique et des
# titres déclarés ici — ajouter un ticker à un thème l'ajoute à l'univers.
#
# POURQUOI SI PEU DE THÈMES (août 2026)
# Une première version en publiait treize. Trop : les thèses se recouvraient,
# plusieurs n'étaient que des regroupements sectoriels déguisés, et l'ensemble
# demandait une maintenance sans rapport avec ce qu'il apportait. On ne garde
# que les listes sur lesquelles le projet a réellement quelque chose à dire, et
# on assume de ne pas couvrir le reste plutôt que de le couvrir mal.
# Le thème « quantique » (08/08/2026, demande du propriétaire) est le premier
# ajout depuis ce resserrement, et le premier à publier MOINS qu'il ne déclare :
# vingt-quatre titres portent le périmètre, dix seulement sont lus.
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
# DOCTRINE DE DESCRIPTION — un texte ne doit pas dépendre du run
# Les champs thesis, sous_titre et biais sont écrits une fois et lus pendant des
# mois, alors que la liste publiée est recalculée chaque semaine. Un texte qui
# cite des titres retenus ou qui les compte devient donc faux tout seul, sans
# que personne n'ait rien touché, et le mensonge est d'autant plus crédible
# qu'il était vrai le jour où il a été écrit.
# Constaté deux fois sur le thème PEA : « huit des titres retenus cotent à New
# York » — huit était le compte des ÉLIGIBLES, trois seulement figuraient dans
# les vingt publiés ; et « la liste est presque vide de technologie américaine »
# — démentie au run suivant, où cinq valeurs technologiques occupaient le haut
# du tableau.
# Règle : une description énonce la RÈGLE d'entrée et ce qu'elle implique
# structurellement, jamais l'état d'un classement. « Des sociétés irlandaises
# cotées à New York y entrent » est vrai tant que le droit ne change pas ;
# « huit des titres retenus » est vrai un mardi.
#
# FORME (08/2026) : chaque thèse OUVRE SUR LA QUESTION à laquelle la liste
# répond, puis y répond court. Le lecteur sait en une ligne si cette liste le
# concerne — c'est le « pourquoi cette page », pas le « comment c'est fait ».
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
            "Qui encaisse les milliards investis dans l'IA ? Toute la chaîne physique, "
            "des puces à l'électricité. Le pari de la dépense, pas celui du vainqueur."
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
            "et descendent ensemble, et il amplifie le pari tech de la watchlist principale. "
            "Il traverse les secteurs classiques : on y trouve de la technologie, de "
            "l'industrie, des services publics et des matériaux qui vivent du même cycle. "
            "Périmètre volontaire : la production d'électricité renouvelable en est exclue, "
            "c'est un pari de politique publique, pas d'infrastructure IA."
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
                "tickers": ["2330.TW", "ASML.AS", "AMAT", "LRCX", "KLAC", "TER", "ASM.AS",
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
        "id": "quantique",
        "label": "Informatique quantique",
        "sous_titre": "Les 20 meilleurs scores d'un secteur qui ne gagne pas encore d'argent",
        "kind": "these",
        "thesis": (
            "Qui vend quelque chose aujourd'hui dans le quantique ? Presque personne. "
            "Cette liste montre les deux réponses qui existent : quelques sociétés qui "
            "ne font QUE ça et perdent de l'argent, et de grands groupes qui construisent "
            "des machines sans que cela pèse sur leurs comptes."
        ),
        # L'INVERSION D'UN THÈME DE RECHERCHE N'EST PAS UN RETOURNEMENT DE
        # MARCHÉ, c'est un verdict scientifique. Écrit comme tel.
        "inversion": (
            "La correction d'erreurs ne descend pas assez vite en coût : il faut toujours "
            "des milliers de qubits physiques pour un seul qubit logique, l'horizon d'un "
            "avantage utile recule d'une décennie, et le financement se retire d'un secteur "
            "sans clients. Deux inversions plus discrètes guettent aussi : un algorithme "
            "classique qui rattrape le meilleur résultat quantique publié, ce qui s'est déjà "
            "produit plusieurs fois, et une technologie de qubit qui écrase les autres, ce "
            "qui rendrait sans objet la moitié des paris de cette liste."
        ),
        # LE BIAIS EST ICI PLUS IMPORTANT QUE LA THÈSE, parce que la note ne
        # sait pas mesurer ce qu'on lui donne. On le dit avant qu'on le lise.
        "biais": (
            "LA NOTE NE SAIT PAS NOTER CES SOCIÉTÉS, et il faut le savoir avant de lire "
            "le classement. La grille mesure la qualité d'un business et le prix payé pour "
            "elle : marge, rentabilité du capital, multiple de bénéfices. Une société sans "
            "bénéfice n'a pas de multiple, une société sans chiffre d'affaires n'a pas de "
            "marge. Les scores les plus bas de cette liste ne disent donc pas « mauvaise "
            "société », ils disent « la grille ne s'applique pas ». À l'inverse, les scores "
            "les plus hauts récompensent des groupes dont le quantique ne représente pas "
            "un centième de l'activité : ils sont bien notés pour tout le reste.\n\n"
            "C'est aussi le thème le plus CONCENTRÉ et le plus volatil du site. Les "
            "sociétés qui ne font que du quantique montent et descendent ensemble, sur des "
            "annonces plus que sur des résultats, et avec des amplitudes que rien dans la "
            "watchlist principale n'approche.\n\n"
            "Deux dérogations assumées, écrites plutôt que cachées. Le projet n'inclut "
            "d'ordinaire que des sociétés de plus de 25 milliards de dollars : elle est "
            "levée ici pour les seules sociétés dont le quantique est le métier, sans quoi "
            "la liste n'aurait contenu aucune d'entre elles. Et plusieurs de ces titres ont "
            "moins de cinq ans de cotation : leur droite de tendance longue n'est pas "
            "exploitable, et leur fiche le dit."
        ),
        # LES QUATRE INTRODUCTIONS EN BOURSE DE 2026 SONT ABSENTES, ET CE N'EST
        # PAS UN OUBLI. Mesuré le 08/08/2026 contre Yahoo : Quantinuum (QNT,
        # 45 séances), Infleqtion (INFQ, 120), Xanadu (XNDU, 96) et Horizon
        # Quantum (HQ, 97) n'ont pas les 200 séances que réclament la moyenne
        # mobile 200 jours et le RSI. Le screener les écarterait au run, et une
        # fiche sans momentum serait une fiche à trois quarts vide. Elles
        # entreront d'elles-mêmes, sans rien changer ici, dès que leur
        # historique suffira — la première vers avril 2027 pour Infleqtion.
        # Quantinuum est de loin l'absence la plus coûteuse : c'est le plus gros
        # pure-player coté (~15 Md$), issu de Honeywell, qui reste dans la liste
        # au maillon des constructeurs et porte donc encore l'exposition.
        "maillons": [
            {
                # Le secteur au sens strict : le quantique est leur métier, pas
                # une ligne de recherche. Aucune n'est rentable, aucune
                # n'atteint le seuil de taille habituel du projet — c'est pour
                # elles que la dérogation existe.
                #
                # « MÉTIER PRINCIPAL » ET NON « SEUL MÉTIER » : le libellé a été
                # corrigé le 08/08/2026, le jour même où il a été écrit. IonQ a
                # bouclé le 31/07/2026 le rachat de SkyWater (1,8 Md$, feu vert
                # après partage des voix à la FTC), une fonderie de semi-
                # conducteurs dont l'essentiel du carnet — ASIC pour la défense
                # et l'aérospatial — n'a rien de quantique. S'y ajoutent ID
                # Quantique, Capella et Vector Atomic, qui relèvent du réseau,
                # du spatial et des horloges atomiques. Le premier titre de ce
                # maillon n'est donc DÉJÀ plus un pur pari quantique, et écrire
                # « leur seul métier » aurait été faux dès la publication.
                "label": "Le quantique comme métier principal",
                "tickers": ["IONQ", "RGTI", "QBTS", "QUBT"],
            },
            {
                # Ceux qui construisent vraiment des machines et les opèrent.
                # Pour tous, le quantique est une ligne de recherche : Honeywell
                # a fait coter Quantinuum en juin 2026 et en reste actionnaire,
                # Fujitsu et Hitachi opèrent des machines avec RIKEN, Intel
                # poursuit la voie des qubits de silicium.
                "label": "Constructeurs · machines et laboratoires",
                "tickers": ["IBM", "GOOGL", "MSFT", "AMZN", "HON", "INTC",
                            "6702.T", "6501.T", "6701.T"],
            },
            {
                # AVANT LA MACHINE, LE SUBSTRAT. Un qubit de spin se grave dans
                # du silicium 28 isotopiquement purifié — le silicium naturel
                # contient un isotope à spin nucléaire qui détruit la cohérence.
                # Un qubit photonique se grave, lui, dans une fonderie 300 mm
                # classique. Ce maillon est le plus concret du thème : ces
                # sociétés livrent aujourd'hui, sur des références nommées.
                "label": "Matériaux & fonderie · le substrat des qubits",
                "tickers": ["STMPA.PA", "GFS", "SOI.PA"],
            },
            {
                # LE MAILLON QUI VEND DES PELLES. Un ordinateur quantique est
                # d'abord un objet de physique expérimentale : un cryostat à
                # dilution, des lasers, de l'optique, des instruments de mesure
                # et un vide poussé. Ces sociétés-là facturent aujourd'hui, à
                # tous les acteurs du secteur, gagnants comme perdants.
                #
                # DEUX PIÈGES DE CE MAILLON, vérifiés le 08/08/2026, à ne pas
                # « corriger » plus tard de bonne foi :
                # · Oxford Instruments n'est PLUS le cryogéniste qu'on croit.
                #   NanoScience, qui fabriquait ses réfrigérateurs à dilution
                #   (59 M£ de CA), a été cédée à Quantum Design le 05/01/2026.
                #   Ce qui reste est plus pertinent, pas moins : Plasma
                #   Technology vend les graveurs qui FABRIQUENT les puces
                #   supraconductrices — Rigetti lui en a acheté un en mai 2026.
                # · FormFactor est, depuis cette cession, le SEUL fabricant coté
                #   de réfrigérateurs à dilution : Bluefors, Janis, Lake Shore
                #   et Maybell sont tous en mains privées.
                "label": "Cryogénie, lasers & instruments",
                "tickers": ["KEYS", "COHR", "LITE", "MKSI", "FORM",
                            "OXIG.L", "6965.T", "6302.T", "AI.PA"],
            },
            {
                # La simulation classique de circuits quantiques, les ponts
                # entre calculateur classique et calculateur quantique, et le
                # réseau qui reliera un jour les machines entre elles —
                # l'intrication à distance est le prérequis d'un calculateur
                # distribué, et c'est un problème de télécoms autant que de
                # physique.
                "label": "Simulation, réseau & logiciel",
                "tickers": ["NVDA", "CSCO"],
            },
            {
                # L'AUTRE MOITIÉ DU SUJET, celle qui a déjà des clients : se
                # protéger d'une machine qui n'existe pas encore. Les normes
                # NIST de cryptographie post-quantique sont publiées, les
                # migrations sont budgétées, et ces deux-là les vendent.
                "label": "Sécurité post-quantique",
                "tickers": ["HO.PA", "IFX.DE"],
            },
        ],
        # VINGT PUBLIÉS SUR VINGT-NEUF DÉCLARÉS. Le périmètre déclaré doit être
        # honnête — c'est lui qui mesure la couverture et qui alerte si une
        # place de cotation tombe. La liste lue, elle, doit tenir sur un écran.
        #
        # DIX AU DÉPART, VINGT DEPUIS LE 08/08 (retour du propriétaire : « il
        # manque pas mal d'acteurs clés »). Le diagnostic était juste et la
        # cause instructive : les acteurs ne manquaient pas au PÉRIMÈTRE, ils
        # étaient déclarés et masqués par le bornage. À dix, la liste coupait
        # sous 51 points et perdait d'un coup les trois quarts des sociétés dont
        # le quantique est le métier, IBM, les deux japonais et le seul
        # fabricant coté de réfrigérateurs à dilution. Un bornage trop serré ne
        # sélectionne plus, il ampute.
        "top": 20,
    },
    # « Financials » retirée le 06/08/2026 (décision propriétaire, « pour le
    # moment ») : la watchlist secteur n'est plus publiée. Ses 33 tickers
    # restent dans l'UNIVERS du screener (screener.py) — ils demeurent scorés
    # et candidats au top 30, et le portefeuille en détient plusieurs (JPM, V,
    # BLK, DB1.DE, SPGI, LSEG.L, ADYEN.AS). Les illustrations et légendes
    # (assets/themes/financials*) sont conservées pour une réintroduction.
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
    "2330.TW": "Taïwan, hors EEE",
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
    # RÈGLE D'ÉCRITURE, apprise ici. Une description de watchlist ne doit
    # contenir AUCUN fait qui dépende du run : la version précédente annonçait
    # « huit des titres retenus cotent à New York » alors que huit était le
    # compte des ÉLIGIBLES et que trois seulement figuraient dans les vingt
    # publiés. Un texte qui cite des noms et des nombres devient faux tout seul,
    # la semaine suivante, sans que personne ne touche à rien.
    "thesis": (
        "Que peut-on loger dans un PEA, l'enveloppe qui efface l'impôt sur le "
        "revenu après cinq ans ? Bien plus que des actions françaises : jusqu'à "
        "des valeurs cotées à New York. Les vingt meilleurs scores réellement "
        "éligibles."
    ),
    # Une contrainte fiscale ne s'invalide pas comme une thèse : ce qui la
    # périme, c'est un changement de droit ou de domicile, pas un retournement
    # de marché. Le champ garde son libellé sur le site, son contenu dit la
    # vérité du thème.
    "inversion": (
        "Cette liste ne se démode pas, elle se périme. Deux évènements la rendent "
        "fausse sans qu'aucun cours ne bouge : une société qui transfère son siège "
        "hors de l'UE perd son éligibilité du jour au lendemain, et une réforme du "
        "PEA peut déplacer le critère lui-même. Dernière vérification des "
        "éligibilités : " + PEA_VERIFIE_LE + "."
    ),
    # Même règle que pour la thèse : que des faits qui tiennent d'une semaine
    # sur l'autre. La version précédente décrivait la liste comme « presque vide
    # de technologie américaine, concentrée sur l'industrie, le luxe et la
    # santé » — une caractérisation d'un run, démentie par le suivant, où NXP,
    # Accenture, Adyen, SAP et ASML occupaient la moitié du haut de tableau.
    "biais": (
        "À vérifier avant tout ordre : l'éligibilité d'un titre et l'acceptation "
        "de la ligne par ton courtier sont deux choses différentes. Plusieurs "
        "courtiers français refusent au PEA les lignes cotées à New York, ou "
        "n'acceptent que la ligne européenne. Et un certificat de dépôt (ADR) "
        "n'est jamais logeable, quel que soit le siège de l'émetteur.\n\n"
        "Ce filtre est fiscal, pas économique. Rien ne dit qu'un univers "
        "restreint par le lieu d'un siège social se comporte mieux qu'un autre : "
        "il optimise l'imposition, pas la sélection. Il écarte par construction "
        "les sociétés américaines, britanniques et suisses, soit l'essentiel de "
        "la watchlist principale.\n\n"
        "Le PEA a enfin ses exclusions propres, indépendantes du siège social : "
        "les foncières cotées de type SIIC, et un plafond de versements de "
        "150 000 €. Ce thème ne les modélise pas."
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
# HISTORIQUE DU REGISTRE — GlobalFoundries en est sorti le 08/08/2026. Il y
# attendait une décision depuis le 01/08 (« recevable depuis l'assouplissement
# de la règle des 5 ans, en attente de décision ») ; la watchlist quantique la
# tranche, parce qu'elle lui donne une raison d'être précise que le thème
# infra-ia ne lui donnait pas : c'est la fonderie qui grave les puces
# photoniques 300 mm de PsiQuantum. 29,6 Md$, 4,8 ans d'historique — sa fiche
# portera l'avertissement de régression jusqu'en 2027, comme les néoclouds.
# ALAB et CRDO restent en attente, aucune thèse ne les réclame aujourd'hui.
#
# CEG, GEV et ARM y ont figuré quelques heures : tous
# trois écartés le matin du 01/08 par la règle « historique < 5 ans », tous
# trois RÉINTÉGRÉS le soir même, après que cette règle est devenue un simple
# avertissement (cf. note plus bas). ARM (256 Md$) rejoint le maillon calcul,
# CEG et GEV le maillon énergie — leurs fiches porteront l'avertissement
# régression tant que leurs historiques resteront courts.
# NOM D'AFFICHAGE, quand celui du fournisseur ne va pas. Yahoo rend deux
# formes et aucune n'est utilisable telle quelle pour TSMC : `shortName` sort
# « TAIWAN SEMICONDUCTOR M », tronqué en plein mot, et `longName` sort
# « Taiwan Semiconductor Manufacturing Company Limited », cinquante caractères
# qui poussent le secteur et la mention de cotation hors de l'en-tête.
#
# On ne corrige donc pas une erreur du fournisseur, on choisit un nom d'usage :
# celui sous lequel la société est connue et cherchée. Le nom légal complet
# n'est pas perdu pour autant — il ouvre la fiche éditoriale, où il a la place.
#
# Registre volontairement court : n'y entre un titre que si les deux formes de
# Yahoo échouent, jamais par préférence de style.
NOMS_AFFICHES = {
    "2330.TW": "TSMC",
}


ECARTES_VALIDATION = {
    # ── Introductions en bourse quantiques de 2026 ────────────────────────────
    # Mesuré le 08/08/2026 contre Yahoo, pas déduit : les quatre sont trop
    # jeunes pour que la MM200 et le RSI existent, donc le screener les
    # écarterait au run et le thème serait publié amputé, en silence. Elles
    # n'attendent AUCUNE décision : leur historique les fera entrer tout seul.
    # La date indiquée est celle où elles franchiront les 200 séances.
"QNT":  "Quantinuum, IPO du 04/06/2026 — 45 séances < 200 (MM200/RSI), éligible vers avril 2027",
"INFQ": "Infleqtion, IPO du 17/02/2026 — 120 séances < 200 (MM200/RSI), éligible vers décembre 2026",
"XNDU": "Xanadu, IPO du 23/03/2026 — 96 séances < 200 (MM200/RSI), éligible vers janvier 2027",
"HQ":   "Horizon Quantum, IPO du 20/03/2026 — 97 séances < 200 (MM200/RSI), éligible vers janvier 2027",
    # IQM est le premier constructeur quantique EUROPÉEN coté (Espoo, Finlande,
    # supraconducteur). Deux lignes existent depuis le 02-03/07/2026 : les ADS
    # au Nasdaq et l'action à Helsinki. C'est la ligne d'ORIGINE qu'on prendra
    # le moment venu, précédent TSMC du 08/08 — un certificat de dépôt ne donne
    # ni le bon historique de prix ni le bon PER. Environ 26 séances au 08/08.
"IQMX.HE": "IQM, cotée le 03/07/2026 à Helsinki — ~26 séances < 200 (MM200/RSI), éligible vers avril 2027",
    # Sécurité post-quantique : écartées sur la TAILLE, pas sur le sujet. À
    # 0,4 et 0,6 Md$ elles ne sont pas dans la même classe de risque que le
    # reste du site, et Arqit n'a même pas d'objectif de cours consensus — la
    # colonne serait vide sur sa fiche. Thales et Infineon portent le maillon.
"ARQQ": "Arqit, capitalisation ~0,4 Md$ et aucun objectif consensus (colonne vide sur la fiche)",
"LAES": "SEALSQ, capitalisation ~0,6 Md$ et 3,2 ans d'historique",
"ROG.SW": "symbole introuvable chez Yahoo, remplacé par l'ADR RHHBY",
    "BESI.AS": "capitalisation ~17 Md$ < seuil 25 Md$ (collage hybride)",
    "EFX":     "capitalisation ~20 Md$ < seuil 25 Md$",
    # Complément du 01/08 — recevables depuis l'assouplissement de la règle
    # des 5 ans, mais PAS réintégrés d'office : chacun attend une décision
    # explicite (contrairement à ARM/CEG/GEV, réintégrés sur demande).
"ALAB": "historique 2,4 ans (IPO 2024), recevable depuis le 01/08, en attente de décision",
"CRDO": "historique 4,5 ans, recevable depuis le 01/08, en attente de décision",

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
