# themes.py — Taxonomie des watchlists thématiques (source unique de vérité)
#
# Signal publie CINQ listes : la watchlist principale (top 30 de l'univers,
# toutes catégories) et quatre vues thématiques.
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
# ajout depuis ce resserrement. Il a changé trois fois de forme dans la journée
# — dix publiés sur vingt-quatre déclarés, puis vingt sur vingt-neuf, puis les
# seuls pure players — et c'est la dernière version qui dit le mieux le secteur :
# il n'existe que dix sociétés cotées dont le quantique soit le métier, et six
# ne sont pas encore notables. Une watchlist a le droit d'être courte quand son
# sujet l'est.
# Le thème « robotique » (08/08/2026, demande du propriétaire) revient le même
# jour, mais ce n'est PAS le thème du même nom retiré au resserrement : celui-là
# regroupait des industriels autour d'un pari de capex, celui-ci répond à une
# question précise — qui est le mieux placé pour bénéficier de l'essor des
# robots — et il y répond par une règle d'exposition, pas par un secteur. La
# différence se voit dans ce qu'il EXCLUT (cf. sa règle d'entrée) autant que
# dans ce qu'il retient.
# Les thèmes retirés (santé, conso, défense, compounders, mémoire
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
        "sous_titre": "Les sociétés dont c'est le seul métier",
        "kind": "these",
        "thesis": (
            "À quoi ressemble un secteur qui n'a pas encore de client ? À cette "
            "liste : les sociétés cotées dont l'informatique quantique est le "
            "métier, et rien d'autre. Aucune n'est rentable, et c'est le sujet."
        ),
        "inversion": (
            "La correction d'erreurs ne descend pas assez vite en coût : il faut toujours "
            "des milliers de qubits physiques pour un seul qubit logique, l'horizon d'un "
            "avantage utile recule d'une décennie, et le financement se retire d'un secteur "
            "sans clients. Deux inversions plus discrètes guettent aussi : un algorithme "
            "classique qui rattrape le meilleur résultat quantique publié, ce qui s'est déjà "
            "produit plusieurs fois, et une technologie de qubit qui écrase les autres, ce "
            "qui rendrait sans objet la moitié des paris de cette liste."
        ),
        "biais": (
            "LA NOTE NE SAIT PAS NOTER CES SOCIÉTÉS, et il faut le savoir avant de lire "
            "le classement. La grille mesure la qualité d'un business et le prix payé pour "
            "elle : marge, rentabilité du capital, multiple de bénéfices. Une société sans "
            "bénéfice n'a pas de multiple, une société sans chiffre d'affaires n'a pas de "
            "marge. Les scores de cette liste ne disent donc pas « bonne » ou « mauvaise "
            "société », ils disent surtout à quel point la grille ne s'applique pas. Un "
            "écart de cinq points n'y signifie rien.\n\n"
            "C'est le thème le plus CONCENTRÉ et le plus volatil du site, de très loin. "
            "Ces sociétés montent et descendent ensemble, sur des annonces plus que sur "
            "des résultats, avec des amplitudes que rien dans la watchlist principale "
            "n'approche. Plusieurs vivent de commande publique.\n\n"
            "Deux dérogations assumées, écrites plutôt que cachées. Le projet n'inclut "
            "d'ordinaire que des sociétés de plus de 25 milliards de dollars : elle est "
            "levée ici, sans quoi la liste serait vide. Et ces titres ont moins de cinq ans "
            "de cotation : leur droite de tendance longue n'est pas exploitable, et leur "
            "fiche le dit.\n\n"
            "Enfin, la liste ne dit rien de ceux qui VENDENT au secteur — cryogénie, "
            "lasers, instruments, substrats — et qui sont pourtant les seuls à facturer "
            "aujourd'hui. Plusieurs figurent dans la watchlist principale."
        ),
        # POURQUOI CETTE LISTE EST COURTE, ET POURQUOI ELLE VA S'ALLONGER.
        # Il n'existe au monde que DIX pure players quantiques cotés, et six
        # d'entre eux sont innotables en août 2026 : cinq se sont introduits en
        # bourse cette année et n'ont pas les 200 séances qu'exigent la moyenne
        # mobile 200 jours et le RSI, le sixième (Arqit) pèse 0,4 Md$ sans
        # objectif de cours consensus. Tous sont au registre des écartés avec
        # la date à laquelle leur historique suffira. La liste passera donc
        # d'elle-même de quatre à neuf titres entre décembre 2026 et avril 2027,
        # sans que personne ne touche à ce fichier — d'où un plafond fixé à dix
        # dès maintenant, qui n'est pas une fiction mais un rendez-vous.
        #
        # ELLE DÉROGE À LA RÈGLE DES VINGT TITRES DÉCLARÉS, et c'est le seul
        # thème qui la mérite : un secteur qui compte dix sociétés cotées ne
        # peut pas en déclarer vingt sans mentir. La règle protégeait contre le
        # thème alibi, bricolé avec trois titres ; ici c'est l'inverse, le
        # périmètre est petit parce que le SECTEUR est petit, et le dire est
        # l'information principale de la page.
        #
        # Pas de maillons : à quatre titres, une structure en couches serait un
        # décor. Elle reviendra si la liste se remplit.
        "tickers": ["IONQ", "RGTI", "QBTS", "QUBT"],
        "top": 10,
    },
    {
        "id": "robotique",
        "label": "Robots",
        # Le sous-titre énonce la RÈGLE d'entrée, pas un état du classement :
        # c'est la doctrine de description rappelée en tête de fichier.
        "sous_titre": "Ceux dont les comptes bougent quand le nombre de robots bouge",
        "kind": "these",
        "thesis": (
            "Qui encaisse si les robots se multiplient ? Pas d'abord ceux qui les "
            "assemblent. Un bras d'usine et un humanoïde partagent les mêmes "
            "articulations, et ces pièces-là sortent d'une poignée d'ateliers. "
            "La liste va du réducteur au robot fini."
        ),
        "inversion": (
            "Deux façons d'avoir tort, et elles sont opposées. Que l'humanoïde reste une "
            "démonstration : les volumes annoncés restent des diapositives, et il ne se "
            "vend jamais que des robots d'usine. Ou l'inverse, plus perfide pour cette "
            "liste : que le goulot s'ouvre. Les constructeurs conçoivent déjà leurs "
            "propres actionneurs pour cesser de dépendre de leurs fournisseurs, et des "
            "concurrents chinois attaquent le réducteur de précision sur son propre "
            "terrain — le jour où la pièce rare devient banale, la rente change de mains "
            "sans qu'un seul robot de moins ne soit vendu. S'y ajoute un rappel qu'aucun "
            "récit n'annule : le robot industriel est un marché d'équipement, adossé à "
            "l'automobile et à l'électronique, et il sait reculer de trente pour cent en "
            "un exercice."
        ),
        "biais": (
            "CE THÈME EST AUSSI UN PARI SUR LE JAPON, et mieux vaut le voir avant d'y "
            "entrer : l'essentiel des pièces critiques du robot cote à Tokyo, en yens, "
            "et relève d'un savoir-faire national tenu par quelques sociétés. Une "
            "variation du yen se lit directement dans les performances, sans qu'aucune "
            "de ces entreprises n'ait rien fait ni rien vendu de plus.\n\n"
            "Dérogation assumée sur la taille. Le projet ne retient d'ordinaire que des "
            "sociétés de plus de 25 milliards de dollars ; plusieurs des spécialistes "
            "de cette liste en sont très loin. Ce n'est pas un relâchement, c'est le "
            "sujet : celui qui détient la pièce que tout le monde doit lui acheter est "
            "une petite société, et un plancher de capitalisation aurait masqué "
            "exactement l'information qu'on cherchait.\n\n"
            "Sur les humanoïdes, la liste dit surtout ce qu'on NE PEUT PAS acheter. Les "
            "constructeurs les plus avancés ne sont pas cotés, et celui qui s'est "
            "introduit en bourse en août 2026 l'a fait à Shanghai, hors de portée d'un "
            "courtier européen. Restent quelques pure players asiatiques de taille "
            "modeste et des constructeurs automobiles chez qui le robot ne pèse encore "
            "rien au compte de résultat. C'est une exposition de conviction, pas une "
            "exposition mesurable — et sur ces quelques titres, la note vaut moins que "
            "sur le reste de la liste : une société dont le bénéfice frôle zéro affiche "
            "un multiple de plusieurs milliers, que la grille lit comme une valorisation "
            "extrême alors qu'il ne dit rien du tout. Le classement les place en bas, "
            "ce qui est honnête, mais l'écart de points n'y a pas de sens.\n\n"
            "Enfin ce thème recoupe l'infrastructure de l'IA sur ses couches basses : "
            "quelques titres figurent dans les deux listes, et les détenir deux fois "
            "n'est pas se diversifier."
        ),
        # RÈGLE D'ENTRÉE, écrite ici parce qu'elle est le seul rempart contre la
        # pente naturelle de ce sujet — remplir la liste de conglomérats.
        # Entre un titre si une hausse du NOMBRE DE ROBOTS VENDUS se lit dans ses
        # comptes. C'est un critère de concentration, pas de taille, et il coupe
        # dans les deux sens :
        #   - il fait entrer des sociétés de 4 Md$ que le seuil du projet
        #     écarterait, parce qu'elles ne font que ça ;
        #   - il fait SORTIR des industriels considérables dont l'exposition est
        #     réelle mais diluée — Emerson, Parker Hannifin, AMETEK, Zebra,
        #     Analog Devices, Infineon, et jusqu'à Nvidia dont la gamme robotique
        #     est un rayon de magasin à côté du centre de données.
        # Ces sorties ne sont PAS des rejets : aucun de ces titres n'entre au
        # registre des écartés plus bas, tous restent scorés et candidats à la
        # watchlist principale, et plusieurs y figurent. Ils ne sont simplement
        # pas « les mieux placés », qui est la question posée à cette liste.
        #
        # QUATRE CAS TRANCHÉS DANS CE SENS le 08/08/2026, tous validés sans
        # erreur le même jour et écartés sur le seul critère de dilution — ils
        # sont notés ici pour que la décision se relise :
        #   - Teradyne (~59 Md$) possède Universal Robots, premier fabricant
        #     mondial de cobots, et MiR. Mais le test de semi-conducteurs fait
        #     l'essentiel de ses ventes : un doublement des robots ne se verrait
        #     pas dans ses comptes. Il reste dans le thème infrastructure de l'IA,
        #     à sa vraie place.
        #   - Mitsubishi Electric (~80 Md$) et Denso (~32 Md$) fabriquent
        #     réellement robots et servomoteurs, au milieu de climatiseurs et
        #     d'équipements automobiles.
        #   - Sumitomo Heavy (~4,7 Md$) a inventé le réducteur Cyclo et compte
        #     parmi les trois grands du réducteur de précision — mais vend aussi
        #     des navires et des engins de chantier. Cas le plus disputé du lot :
        #     retenu sur le sujet, écarté sur la règle.
        #   - Novanta (~6,3 Md$), mouvement de précision et photonique, partagé
        #     entre médical et industrie sans que la robotique s'y isole.
        # Sans cette règle, le thème redevient une liste de méga-capitalisations
        # industrielles, c'est-à-dire une liste qui ne répond à rien.
        "maillons": [
            {
                # LE MAILLON LE PLUS PAUVRE DU SITE, et c'est le résultat, pas un
                # oubli. En août 2026 les constructeurs d'humanoïdes les plus
                # avancés sont privés (Figure, 1X, Apptronik), Unitree s'est
                # introduit au STAR Market de Shanghai le 06/08/2026 — deux
                # séances, et une place qu'un courtier européen n'atteint pas.
                # Restent deux pure players asiatiques modestes — l'un à Hong
                # Kong, l'autre au KOSDAQ, contrôlé par Samsung — et deux
                # constructeurs automobiles qui portent un programme humanoïde :
                # Tesla fabrique Optimus pour ses propres usines, sans vente
                # externe avant 2027 sur son propre calendrier, et Hyundai
                # contrôle Boston Dynamics. Dans les deux cas le robot est
                # invisible au compte de résultat — ils sont ici pour ce qu'ils
                # construisent, et le lecteur doit savoir qu'il n'achète pas ça.
                "label": "Humanoïdes · le pari, et le peu qui s'achète",
                "tickers": ["9880.HK", "277810.KQ", "TSLA", "005380.KS"],
            },
            {
                # Les quatre grands du robot industriel étaient Fanuc, Yaskawa,
                # ABB et KUKA. Trois se tiennent ici ; le quatrième a été racheté
                # par le chinois Midea puis sorti de la cote de Francfort — son
                # symbole ADR ne rend plus rien (cf. registre des écartés). Un
                # secteur qui perd un de ses quatre leaders pour la bourse est
                # une information en soi sur ce qui reste accessible.
                # S'y ajoute un pure player coréen du robot collaboratif, entré
                # en bourse en 2023 : 2,8 ans d'historique, donc une fiche qui
                # portera l'avertissement de régression, mais c'est l'un des
                # rares titres dont le cobot EST le métier.
                "label": "Robots industriels · les constructeurs",
                "tickers": ["6954.T", "6506.T", "ABBN.SW", "454910.KS"],
            },
            {
                # LE CŒUR DE LA THÈSE. Une articulation de robot, c'est un moteur,
                # un réducteur qui transforme sa vitesse en couple, un guidage et
                # des roulements. Le réducteur est le point le plus étroit de
                # toute la chaîne : Harmonic Drive tient l'essentiel du marché
                # mondial du réducteur harmonique — celui des articulations fines,
                # donc de tout humanoïde — et Nabtesco celui du réducteur
                # cycloïdal des bras lourds. Ces positions ne se contournent pas
                # en un exercice : elles tiennent à la métallurgie et à la
                # rectification, pas à un brevet qui expire.
                # C'est aussi le maillon qui justifie la dérogation de taille :
                # ces sociétés pèsent quelques milliards de dollars et fournissent
                # le monde entier.
                "label": "Le goulot · réducteurs, guidage & moteurs",
                "tickers": ["6324.T", "6268.T", "6481.T", "2049.TW", "6471.T",
                            "6594.T", "6273.T", "SKF-B.ST"],
            },
            {
                # Un robot qui ne voit pas ne fait que répéter un geste. La vision
                # industrielle et les capteurs sont ce qui sépare le bras
                # programmé de la machine qui s'adapte, et ce maillon vend à
                # TOUS les constructeurs sans dépendre d'aucun. Rockwell y est
                # pour le pilotage : automatisation d'usine à cent pour cent de
                # son activité, donc conforme à la règle d'entrée là où d'autres
                # conglomérats ne le sont pas.
                "label": "Voir, mesurer & piloter",
                "tickers": ["6861.T", "6645.T", "CGNX", "ROK"],
            },
            {
                # LE CONTRE-EXEMPLE UTILE : les seuls robots qui, hors de l'usine,
                # se vendent déjà en volume et dégagent des marges. Le robot
                # chirurgical rappelle à quoi ressemble un marché qui a fini de
                # se chercher — base installée, consommables, formation des
                # opérateurs — c'est-à-dire tout ce que l'humanoïde n'a pas
                # encore. L'entrepôt est l'autre débouché prouvé : y livrer des
                # robots ne suppose aucune percée technique, seulement des
                # commandes.
                "label": "Robots de service · médical & logistique",
                "tickers": ["ISRG", "SYM", "KGX.DE"],
            },
        ],
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
    # ── Robotique ─────────────────────────────────────────────────────────────
    # Validés sans erreur le 08/08/2026 mais SOUS LE SEUIL de 25 Md$, et aucune
    # thèse ne les réclame assez fort pour justifier la dérogation accordée aux
    # spécialistes du goulot : ceux-là détiennent une pièce que le monde entier
    # doit leur acheter, ce qui n'est le cas ni de l'un ni de l'autre.
"NOVT": "Novanta, capitalisation ~6,3 Md$ < seuil 25 Md$ — mouvement de précision partagé entre médical et industrie, la robotique ne s'y isole pas",
"ZBRA": "Zebra, capitalisation ~17,8 Md$ < seuil 25 Md$ — les robots d'entrepôt (Fetch) sont un appoint dans une activité de codes-barres",
    # KUKA était l'un des quatre grands du robot industriel avec Fanuc, Yaskawa
    # et ABB. Racheté par le chinois Midea en 2016, puis sorti de la cote de
    # Francfort en 2022 : il n'existe plus de ligne cotée, et l'ADR ne rend plus
    # d'historique. Ce n'est donc pas un titre qu'on écarte, c'est un titre qui
    # n'est plus achetable — et le maillon « constructeurs » de la watchlist
    # robotique en compte trois au lieu de quatre pour cette seule raison.
"KUKAY": "KUKA, sorti de la cote après le rachat par Midea — history(max) vide, plus de ligne cotée",
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
