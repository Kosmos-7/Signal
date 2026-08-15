# themes.py — Taxonomie des watchlists thématiques (source unique de vérité)
#
# Signal publie SIX listes : la watchlist principale (top 30 de l'univers,
# toutes catégories) et cinq vues thématiques.
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
# Le thème « espace » (09/08/2026, demande du propriétaire) arrive au moment où
# son sujet devient achetable : SpaceX s'est introduite en bourse en juin, et
# c'est la première fois qu'un lanceur dominant est cotable. Le paradoxe est
# qu'elle n'y figure pas — trente-neuf séances de cotation, quand la moyenne
# mobile 200 jours en exige deux cents. Une watchlist qui s'ouvre en disant ce
# qu'elle ne sait pas encore noter.
# Il est devenu « NewSpace » le 12/08/2026 (demande du propriétaire), et le
# changement n'est pas d'étiquette. « Espace » nomme un SECTEUR ; NewSpace nomme
# la génération d'acteurs apparue au milieu des années 2000 — technologies et
# procédés nouveaux, débouchés nouveaux, financements nouveaux — c'est-à-dire un
# sous-ensemble de ce secteur, et un sous-ensemble défini CONTRE ce qui le
# précédait. Prendre le mot au sérieux, c'est donc sortir de la liste les dix
# maîtres d'œuvre historiques et les quatre opérateurs de satellites
# historiques : quatorze titres, et la liste passe de vingt à sept. Elle mesure
# en échange un seul objet, ce que sa version « espace » avouait ne pas faire
# (« la liste est coupée en deux, et ses deux moitiés ne se comportent pas du
# tout pareil »). Les quatorze restent scorés dans l'univers du screener, comme
# la chaîne quantique et l'ex-thème financials avant eux.
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
# Complétée le 15/08 (passe éditoriale du propriétaire) : la thèse se FERME
# sur le pari. La dernière phrase dit à quoi l'on s'expose en entrant — c'est
# elle qui répond « est-ce moi ? », pas la description du périmètre.
# Et le site vouvoie, partout : le « ton courtier » du PEA était une coquille.
#
# PONCTUATION — PAS DE TIRET CADRATIN (15/08). La règle existait déjà, mais
# seulement pour l'IA : generate_analyses.py l'interdit dans le prompt des
# fiches (« la signature la plus reconnaissable d'un texte de machine »), et
# les 148 fiches publiées n'en portent aucun. La copie écrite à la main, elle,
# en comptait dix-huit dans ces seuls champs. Même règle pour tout le monde :
# virgule pour une apposition, deux-points pour une explication, parenthèses
# pour une incise, ou deux phrases. Le demi-cadratin « – » est proscrit aussi.
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
            "c'est un pari de politique publique, pas d'infrastructure IA.\n\n"
            "UN MAILLON SE LIT AUTREMENT QUE LES AUTRES, celui des bailleurs de capacité. "
            "Ces sociétés ne possèdent ni puces ni serveurs : elles détiennent de "
            "l'électricité sous contrat et des bâtiments, qu'elles louent dix à vingt-cinq "
            "ans à un seul locataire, sur des baux non résiliables. Elles ont donc déjà "
            "VENDU ce qu'elles n'ont pas fini de construire, et leurs comptes d'aujourd'hui "
            "ne montrent que la dépense : la note lit une société en perte là où le carnet "
            "de commandes dit autre chose. C'est le seul endroit de cette liste où un score "
            "bas ne veut pas dire ce qu'il dit ailleurs.\n\n"
            "Deux dérogations les accompagnent, écrites plutôt que cachées. Le projet ne "
            "retient d'ordinaire que des sociétés de plus de 25 milliards de dollars : "
            "aucun bailleur n'atteint ce seuil, et l'appliquer reviendrait à supprimer le "
            "maillon plutôt qu'à le filtrer. Et la plupart sont d'anciens mineurs de "
            "bitcoin reconvertis depuis peu : leur historique de cotation raconte un métier "
            "qu'ils ont quitté, et leur fiche prévient que la droite de tendance longue n'y "
            "est pas exploitable."
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
                #
                # 285A.T (Kioxia) ajouté le 12/08/2026, signalé absent par le
                # propriétaire. C'est le MÊME OUBLI que SNDK, vu de l'autre côté :
                # Kioxia et SanDisk exploitent EN COMMUN les usines NAND de
                # Yokkaichi et Kitakami, et la liste retenait le partenaire coté
                # à New York en laissant de côté celui coté à Tokyo. Les trois
                # autres producteurs mondiaux — Micron, SK hynix, Samsung —
                # étaient déjà là : le maillon décrivait un oligopole en oubliant
                # un de ses membres.
                # Profil quasi identique à celui de SanDisk, ce qui rend la
                # décision d'alors directement applicable : ~182 Md$ et 1,6 an
                # d'historique (introduite à Tokyo fin 2024), donc fiche avec
                # avertissement de régression. Validé contre Yahoo AVANT d'être
                # écrit ici — 1/1, JPY conforme au suffixe .T, secteur exploitable
                # — ce qui est l'ordre que validate_tickers.py prescrit.
                "label": "Mémoire & stockage",
                "tickers": ["MU", "000660.KS", "005930.KS", "WDC", "SNDK", "STX", "NTAP", "4063.T",
                            "285A.T"],
            },
            {
                # Ce qui relie les accélérateurs entre eux, et limite la taille
                # des clusters d'entraînement autant que le nombre de puces.
                # ALAB et CRDO tranchés le 09/08/2026 (décision du
                # propriétaire) après huit jours au registre en « attente de
                # décision ». Ils sortent donc du registre : un titre ne peut
                # pas être à la fois publié et écarté — leçon GlobalFoundries.
                # Ce sont les puces de CONNEXION des baies : Astera Labs pour
                # les liens PCIe/CXL entre accélérateurs et mémoire, Credo pour
                # les câbles actifs qui remplacent l'optique sur les courtes
                # distances. Le maillon disait déjà que ce qui relie les
                # accélérateurs limite la taille des clusters autant que le
                # nombre de puces ; il lui manquait précisément ces deux-là.
                # 58,0 et 46,6 Md$, tous deux très au-dessus du seuil ; seul
                # l'avertissement de régression s'applique (2,4 et 4,5 ans).
                "label": "Réseau & optique",
                "tickers": ["ANET", "COHR", "LITE", "CIEN", "CSCO",
                            "ALAB", "CRDO"],
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
                # UN MODÈLE ENTIER MANQUAIT À LA CHAÎNE, et c'est le
                # propriétaire qui l'a vu, en demandant simplement pourquoi
                # Applied Digital n'y était pas. La réponse honnête était :
                # aucune raison. Il n'était ni dans l'univers, ni au registre
                # des écartés — or ce registre existe précisément pour qu'une
                # absence ait un motif lisible. Ce n'était pas un arbitrage,
                # c'était un angle mort, et il en cachait quatre autres.
                #
                # CE QUE CE MAILLON N'EST PAS. Ni une foncière ni un néocloud,
                # bien qu'il ressemble aux deux :
                #   · Equinix et Digital Realty louent le mètre carré à des
                #     locataires diversifiés, sur des baux courts ;
                #   · CoreWeave et Nebius vendent l'HEURE DE GPU et possèdent
                #     les GPU, donc portent le risque technologique ;
                #   · ceux-ci ne possèdent ni les puces ni les serveurs. Ils
                #     détiennent de l'ÉLECTRICITÉ SOUS CONTRAT et une coque,
                #     et les louent dix à vingt-cinq ans, en take-or-pay, à un
                #     seul locataire de qualité bancaire. Leur métier est
                #     foncier ; leur risque est celui d'un promoteur.
                #
                # L'ÉCART ENTRE LE CARNET ET LE REVENU EST TOUTE LA THÈSE.
                # Applied Digital porte 1 410 MW sous contrat et 36,2 Md$ de
                # revenus non annulables sur quinze ans, pour 611 M$ de chiffre
                # d'affaires réalisé en 2026 et une perte nette. TeraWulf a
                # ~13 Md$ de carnet, dont 3,2 Md$ garantis par Google, qui en
                # détient environ 14 %. Ce sont des sociétés qui ont déjà VENDU
                # ce qu'elles n'ont pas encore construit — la note ne sait pas
                # lire cela, et le champ `biais` le dit au lecteur.
                #
                # DÉROGATION DE TAILLE (décision du propriétaire, 09/08/2026).
                # Les cinq pèsent de 6,8 à 14,7 Md$, sous le plancher habituel
                # de 25 Md$. Le lever ici est le même choix que sur le
                # quantique et la robotique : le seuil protège d'ordinaire
                # contre l'illiquidité, il masquerait ici les seuls titres
                # qui portent ce modèle. Aucun acteur de plus de 25 Md$ ne le
                # porte, la dérogation n'a donc pas d'alternative.
                #
                # Quatre des cinq ont moins de cinq ans d'historique exploitable
                # — ce sont d'anciens mineurs de bitcoin reconvertis, et leur
                # passé de mineur ne dit rien de leur avenir de bailleur. Leur
                # fiche porte l'avertissement de régression.
                "label": "Bailleurs de capacité IA",
                "tickers": ["APLD", "WULF", "CIFR", "IREN", "CORZ"],
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
                # QUATRE OMISSIONS COMBLÉES LE 09/08/2026, aucune ne demandant
                # de dérogation — elles n'avaient tout simplement jamais été
                # examinées. La plus gênante est Legrand : une valeur de la cote
                # parisienne, éligible au PEA, sur la couche même qu'occupe
                # Vertiv — barres d'alimentation haute intensité, chemins de
                # câbles, confinement thermique — et qui a relevé ses prévisions
                # deux fois sur la demande des centres de données.
                # Comfort Systems et EMCOR ne fabriquent rien : ils CONSTRUISENT
                # le bâtiment électromécanique, et c'est une façon de tenir le
                # cycle sans porter le risque technologique d'aucune puce. Le
                # carnet de Comfort Systems a presque doublé, à ~12 Md$, dont
                # 45 % de technologie.
                # Bloom Energy vend la pile à combustible posée SUR LE SITE,
                # pour les campus que le réseau ne sait pas raccorder à temps —
                # le goulot dont ce maillon porte le nom.
                "tickers": ["VRT", "ETN", "SU.PA", "SIE.DE", "ABBN.SW", "ENR.DE",
                            "PWR", "VST", "CEG", "GEV", "CCJ",
                            "MPWR", "ON", "IFX.DE",
                            "LR.PA", "FIX", "EME", "BE"],
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
            "Enfin, la liste ne dit rien de ceux qui VENDENT au secteur (cryogénie, "
            "lasers, instruments, substrats), et qui sont pourtant les seuls à facturer "
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
        "sous_titre": "Les comptes qui bougent quand le nombre de robots bouge",
        "kind": "these",
        "thesis": (
            "Qui encaisse si les robots se multiplient ? Pas d'abord ceux qui les "
            "assemblent. Un bras d'usine et un humanoïde partagent les mêmes "
            "articulations, et ces pièces-là sortent d'une poignée d'ateliers. "
            "Le pari des pièces communes, pas celui du robot vedette."
        ),
        "inversion": (
            "Deux façons d'avoir tort, et elles sont opposées. Que l'humanoïde reste une "
            "démonstration : les volumes annoncés restent des diapositives, et il ne se "
            "vend jamais que des robots d'usine. Ou l'inverse, plus perfide pour cette "
            "liste : que le goulot s'ouvre. Les constructeurs conçoivent déjà leurs "
            "propres actionneurs pour cesser de dépendre de leurs fournisseurs, et des "
            "concurrents chinois attaquent le réducteur de précision sur son propre "
            "terrain : le jour où la pièce rare devient banale, la rente change de mains "
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
            "exposition mesurable, et sur ces quelques titres, la note vaut moins que "
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
    {
        "id": "newspace",
        "label": "NewSpace",
        "sous_titre": "La génération née après 2000, et elle seule",
        "kind": "these",
        "thesis": (
            "Qu'achète-t-on quand on achète le NewSpace ? Pas le spatial, mais la "
            "génération de sociétés apparue au milieu des années 2000 (procédés, "
            "débouchés et financements nouveaux), qui a fait tomber le coût du kilo "
            "en orbite et vend des abonnements là où les agences signaient des "
            "contrats. De l'accès à l'orbite à la station, la liste suit cette "
            "génération, pas les maisons qui la précédaient."
        ),
        "inversion": (
            "Le NewSpace a une dépendance dont ses carnets de commandes ne disent rien : il "
            "est né d'un argent bon marché (capital-risque, sociétés d'acquisition, "
            "introductions), et la plupart de ces sociétés brûlent encore de la trésorerie. "
            "Ce qui les tue n'est pas un client perdu, c'est une levée qui ne se fait pas. "
            "S'y ajoute le paradoxe du leader : un seul acteur lance la majorité de la masse "
            "mise en orbite et opère la première constellation, et ses concurrents lui "
            "achètent leurs lancements en même temps qu'ils lui disputent ses clients : si "
            "son avantage de coût se creuse encore, cette liste devient un ensemble de "
            "sous-traitants. L'inversion symétrique existe : un échec de vol prolongé ou une "
            "collision majeure en orbite basse renchérirait l'assurance et retarderait tout le "
            "monde. Et la demande publique (défense, agences) décide encore de la plupart "
            "des carnets : c'est une industrie dont le premier client vote son budget."
        ),
        "biais": (
            "CE QUE LE MOT EXCLUT est la première chose à savoir, parce que c'est ce qui "
            "sépare cette liste d'une liste « spatial ». Le NewSpace se définit CONTRE "
            "l'organisation qui le précédait : entre ici une société née de la vague : le "
            "spatial pour métier, un procédé qui casse un coût, des clients qui ne sont pas "
            "seulement des agences, et une arrivée en bourse par les financements de cette "
            "vague. En sortent les maîtres d'œuvre historiques (Lockheed, Northrop, "
            "L3Harris, RTX, BAE, Airbus, Thales, Safran, Leonardo, Kratos), pour qui "
            "l'espace est un département dont le cours suit des budgets militaires, et les "
            "opérateurs de satellites historiques (SES, Eutelsat, Viasat, Iridium), qui "
            "sont ce que le NewSpace a pris de vitesse. Ce ne sont pas des rejets : ces "
            "quatorze titres restent scorés, candidats à la watchlist principale, et leurs "
            "fiches restent en ligne : on retire une liste, pas des sociétés.\n\n"
            "LA NOTE DE SPACEX EST INCOMPLÈTE, et c'est la deuxième chose à savoir. "
            "Introduite en juin 2026, elle n'a pas encore les deux cents séances de "
            "cotation qu'exige la moyenne mobile 200 jours : son critère de tendance "
            "est donc RETIRÉ, et sa note se renormalise sur les points restants, "
            "comme pour une banque dont le flux de trésorerie n'est pas calculable. "
            "Sa note reste comparable aux autres, mais elle repose sur moins de "
            "mesures : le momentum d'un titre sans moyenne longue n'est apprécié que "
            "par sa position dans un canal de régression encore court. Le critère "
            "revient de lui-même vers avril 2027, sans que personne n'ait à y "
            "toucher. Nous préférons l'écrire que laisser croire à une note pleine.\n\n"
            "LA LISTE EST COURTE PARCE QUE SON SUJET L'EST EN BOURSE. Le NewSpace compte des "
            "centaines de sociétés ; celles qui sont cotées, notables et pas encore "
            "microscopiques tiennent en quelques lignes. Dérogation de taille assumée, comme "
            "sur la watchlist quantique : le projet ne retient d'ordinaire que des sociétés "
            "de plus de 25 milliards de dollars, et ces pure players pèsent entre un et "
            "quelques dizaines. Appliquer le seuil ne filtrerait pas la liste, il la "
            "supprimerait. Sous le milliard en revanche on s'arrête, et le registre des "
            "écartés nomme ceux qui n'y arrivent pas, capitalisation mesurée à l'appui.\n\n"
            "LA NOTE LIT MAL CES SOCIÉTÉS, et mieux vaut le savoir avant de comparer des "
            "scores. La plupart n'ont pas de bénéfice : leurs multiples sont vides ou "
            "absurdes, leur marge de flux disponible est négative de plusieurs centaines de "
            "pour cent, et la grille les classe en bas, ce qui est honnête sur le risque, "
            "mais ne dit rien de l'exécution. Ce qui les pilote est ailleurs : un carnet de "
            "commandes, une cadence de vol, un contrat d'agence. Depuis que les maîtres "
            "d'œuvre en sont sortis, au moins la liste ne mélange plus deux objets ; elle "
            "en mesure un seul, mal.\n\n"
            "LE NEWSPACE ACHETABLE EST AMÉRICAIN, et ce n'est pas un choix de périmètre. Le "
            "phénomène s'est propagé en Europe et en Chine, mais ses acteurs européens sont "
            "restés privés à deux micro-capitalisations près, cotées à Stockholm et hors "
            "d'échelle pour ce site, et ses acteurs chinois s'introduisent sur des places "
            "qu'un courtier européen n'atteint pas, le mur que la watchlist robotique a "
            "rencontré en août devant le premier constructeur d'humanoïdes coté à Shanghai. "
            "Un cas mérite d'être connu : la constellation OneWeb n'a "
            "pas été introduite en bourse, elle a été absorbée par un opérateur historique : "
            "on ne l'achète donc qu'en achetant Eutelsat, qui n'est plus dans cette liste.\n\n"
            "Enfin le calcul EN ORBITE, dont on parle beaucoup depuis 2026, n'est presque pas "
            "achetable : les sociétés qui y travaillent sont privées, et les cotées n'y "
            "participent que comme transporteurs ou fournisseurs de plateforme."
        ),
        # RÈGLE D'ENTRÉE, écrite ici parce que le mot NewSpace ne veut rien dire
        # sans elle — et qu'elle est ce qui empêche la liste de redevenir une
        # liste « aérospatial et défense ». Entre un titre s'il réunit les
        # quatre traits par lesquels le phénomène se définit :
        #   - le spatial est son MÉTIER, pas un département ;
        #   - il est né de la vague (fondé au milieu des années 2000 ou après,
        #     ou créé par elle) ;
        #   - il apporte un procédé ou un débouché que l'organisation
        #     précédente n'avait pas — réutilisation, cadence, abonnement,
        #     station privée ;
        #   - il est arrivé en bourse par les financements de cette vague.
        # La règle coupe dans les deux sens, et c'est à cela qu'on la reconnaît :
        # elle fait entrer des sociétés de 1 à 3 Md$ que le seuil du projet
        # écarterait, et elle fait SORTIR des groupes considérables dont
        # l'exposition spatiale est réelle mais ancienne.
        #
        # QUATRE CANDIDATS TRANCHÉS DANS CE SENS le 12/08/2026, tous validés
        # sans erreur contre Yahoo le même jour et écartés sur la seule règle —
        # notés ici pour que la décision se relise. Aucun n'entre au registre
        # des écartés plus bas : ce registre est celui des critères d'inclusion
        # du projet (taille, historique, données manquantes), pas celui des
        # choix de périmètre.
        #   - Globalstar (~10,8 Md$), opérateur de constellation en orbite
        #     basse — mais fondé en 1991, et c'est un client historique qui lui
        #     a donné son second souffle, pas un procédé nouveau.
        #   - AeroVironment (~9,8 Md$), drones et systèmes spatiaux depuis son
        #     rachat de BlueHalo : société de 1971, dont le client est la
        #     défense américaine.
        #   - Karman (~8,4 Md$), structures et propulsion pour lanceurs et
        #     missiles, introduite en 2025 mais formée par regroupement
        #     d'ateliers anciens — une cotation neuve ne fait pas une
        #     génération neuve.
        #   - Avio (~1,7 Md$), le cas le plus disputé : c'est le lanceur
        #     européen coté, mais héritier de Fiat Aviazione et bâti sur la
        #     commande institutionnelle, c'est-à-dire l'exact contraire de ce
        #     que le mot désigne.
        # Tous quatre sont par ailleurs sous le seuil de 25 Md$ ; c'est la règle
        # qui tranche, la taille ne fait que ne pas les rattraper.
        "maillons": [
            {
                # ACCÈS À L'ORBITE. Le maillon qui commande tous les autres : sans
                # lanceur, rien ne vole. Il est aussi le plus concentré du site :
                # SpaceX met en orbite l'essentiel de la masse mondiale, et ses
                # concurrents lui achètent des lancements.
                #
                # SPCX ENTRE LE 15/08/2026, sur décision du propriétaire, alors
                # qu'elle n'a pas ses 200 séances de cotation. Elle est donc
                # notée SANS son critère de tendance (MM200 incalculable) : la
                # note se renormalise sur les 93 points restants, comme pour une
                # banque sans FCF. Le mécanisme est celui du projet, pas une
                # exception fabriquée pour elle ; ce qui est propre à ce titre,
                # c'est l'autorisation nommée dans screener.HIST_PARTIEL_OK, et
                # elle se périme d'elle-même vers avril 2027.
                # Firefly, l'autre lanceur coté né de la vague, reste au registre
                # des écartés : son fournisseur de données ne rend aucune
                # capitalisation, et plusieurs points de la note se calculent
                # dessus. Son cas n'est PAS celui de SpaceX : il manque une
                # donnée de base, pas une profondeur d'historique qui viendra.
                "label": "Accès à l'orbite",
                "tickers": ["SPCX", "RKLB"],
            },
            {
                # CONSTELLATIONS ET CONNECTIVITÉ. Le seul endroit du spatial qui
                # facture des abonnements plutôt que des contrats — c'est le
                # « nouveau débouché » de la définition, pris au mot.
                # Les historiques géostationnaires (SES, Eutelsat, Viasat) et
                # Iridium sont sortis d'ici le 12/08 avec la règle d'entrée : ils
                # sont ce que l'orbite basse a pris de vitesse, pas ce qu'elle a
                # fait naître, et l'européen IRIS² qui court en arrière-plan est
                # une commande publique portée par deux d'entre eux.
                # Reste le pari le plus pur de la liste : un téléphone ordinaire
                # qui se connecte directement au satellite, sans antenne,
                # qu'AST SpaceMobile porte avec une soixantaine d'opérateurs
                # partenaires.
                "label": "Constellations & connectivité",
                "tickers": ["ASTS"],
            },
            {
                # OBSERVER LA TERRE. L'imagerie est la première application
                # spatiale à avoir trouvé des clients récurrents — défense,
                # renseignement, assurance, agriculture. Planet Labs est aussi le
                # seul titre coté associé à un projet de CALCUL EN ORBITE :
                # Google a annoncé Suncatcher, des grappes de satellites porteurs
                # de TPU, avec lui comme partenaire de plateforme. C'est la seule
                # façon d'approcher ce sujet en bourse ; Starcloud et Axiom, qui
                # ont fait voler les premiers nœuds, ne sont pas cotés.
                "label": "Observer la Terre & calculer en orbite",
                "tickers": ["PL", "BKSY"],
            },
            {
                # TRAVAILLER EN ORBITE. Le débouché que la station spatiale
                # internationale laissera vacant à son retrait : des laboratoires
                # et des stations privés, vendus à des agences comme à des
                # industriels. Redwire fournit les composants et les expériences
                # en microgravité ; Voyager construit Starlab, l'une des stations
                # candidates à la succession, et s'est introduite en bourse en
                # juin 2025 — moins de cinq ans d'historique, donc une fiche qui
                # portera l'avertissement de régression, comme les néoclouds.
                # C'est le maillon le plus jeune de la liste, et celui qui dépend
                # le plus d'un calendrier public.
                "label": "Travailler en orbite · infrastructure & stations",
                "tickers": ["RDW", "VOYG"],
            },
            {
                # ALLER SUR LA LUNE. Un maillon d'un seul titre, et assumé comme
                # tel : c'est le seul acteur coté dont l'alunissage est le métier.
                # On le distingue de l'observation parce que son client est une
                # agence, son horizon une mission, et son risque binaire.
                "label": "Exploration lunaire",
                "tickers": ["LUNR"],
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
               "Royaume-Uni, éligibilité contestée, écarté par prudence",
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
        "de la ligne par votre courtier sont deux choses différentes. Plusieurs "
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
    # ── NewSpace ──────────────────────────────────────────────────────────────
    # SPCX EST SORTIE DE CE REGISTRE LE 15/08/2026, sur décision du propriétaire.
    # Elle y figurait depuis son introduction du 16/06/2026 : 39 séances mesurées
    # le 09/08, contre les 200 qu'exige la moyenne mobile 200 jours, et le
    # screener l'écartait au run. Ce n'était pas un jugement sur la société mais
    # une garde technique, et elle bloquait plus large que nécessaire : la note
    # sait retirer un critère incalculable et se renormaliser sur le reste.
    # SpaceX est donc notée sans son critère de tendance, via l'autorisation
    # nommée `screener.HIST_PARTIEL_OK` ; ce que la liste y gagne (la société qui
    # a donné sa forme au phénomène) vaut mieux que sept points de momentum non
    # mesurés, et le biais du thème le dit au lecteur. L'autorisation se périme
    # d'elle-même vers avril 2027, quand la MM200 redeviendra calculable.
    # Firefly a été REVALIDÉE le 12/08/2026 au moment du passage à NewSpace : son
    # historique n'est plus l'obstacle (un an de cotation dépasse les 200 séances,
    # et moins de cinq ans n'est plus qu'un avertissement depuis le 01/08). Ce qui
    # bloque est la capitalisation, que le fournisseur ne rend pas — or le
    # rendement du flux disponible se calcule dessus, et le seuil de taille se
    # vérifie dessus. Précédent Arqit : on n'entre pas un titre dont une colonne
    # de la fiche serait vide, à plus forte raison quand elle nourrit la note.
"FLY":  "Firefly Aerospace, introduite en 2025 — capitalisation absente chez le fournisseur (revalidé le 12/08/2026), donc ni seuil vérifiable ni rendement du flux calculable",
    # SOUS LE PLANCHER DU MILLIARD, mesuré le 12/08/2026. Ces cinq-là passent la
    # règle d'entrée du thème sans discussion — le NewSpace est leur métier — et
    # échouent sur la seule TAILLE. Le thème déroge déjà au seuil de 25 Md$ ; il
    # s'arrête ici, au voisinage du milliard, parce qu'en dessous une société
    # n'est plus dans la même classe de risque que le reste du site. Le titre le
    # plus léger de la liste publiée en pèse 1,3.
"SPIR":    "Spire Global, capitalisation ~0,6 Md$ — NewSpace par la règle, écarté sur la taille",
"SATL":    "Satellogic, capitalisation ~0,9 Md$ — idem, et le plus proche du plancher",
"SPCE":    "Virgin Galactic, capitalisation ~0,5 Md$ — idem",
    # LES DEUX SEULS NEWSPACE EUROPÉENS COTÉS, et ils tiennent dans une PME.
    # Ce n'est pas une lacune de ce registre, c'est le fait principal du sujet
    # côté européen : la vague y est restée privée (Isar, Exotrail, ICEYE, The
    # Exploration Company), et ce qui cote pèse le dixième du plus petit titre
    # de la liste publiée. Le champ `biais` du thème le dit au lecteur.
"GOMX.ST": "GomSpace, capitalisation ~0,2 Md$ — nanosatellites, Stockholm",
"AAC.ST":  "AAC Clyde Space, capitalisation ~0,1 Md$ — idem",
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
