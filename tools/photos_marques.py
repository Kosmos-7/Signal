#!/usr/bin/env python3
"""Sixième passe : chercher la MARQUE et le PRODUIT, pas la raison sociale.

CE QUE LES CINQ CAMPAGNES PRÉCÉDENTES ONT TOUTES FAIT PAREIL. Recherche
textuelle, Wikidata P18, catégorie Commons, données structurées, Openverse :
toutes interrogeaient le nom de la société. C'est le bon identifiant pour une
base de données, c'est le mauvais pour une photothèque. Personne ne titre son
image « Vertiv » : on écrit « Liebert UPS », du nom de la marque. Personne
n'écrit « Teradyne » sous un bras robotisé : on écrit « Universal Robots UR5 »,
du nom de la filiale. Personne ne photographie « Constellation Energy » : on
photographie la centrale de Calvert Cliffs.

D'où cette passe, qui inverse la question. Au lieu de demander à Commons ce
qu'il a sur une société, on lui demande ce qu'il a sur les objets que cette
société fabrique, les marques sous lesquelles elle les vend, les filiales qui
les produisent et les sites qu'elle exploite. La correspondance société →
marques est écrite à la main et vérifiée, parce que c'est précisément le savoir
qu'aucune API ne porte.

CE QUE ÇA NE RÉSOUT PAS. La justesse. « Liebert UPS » peut ramener la photo
d'une salle serveurs où l'onduleur n'est pas visible ; « Waymo » ramène aussi
des manifestations contre Waymo. Le barème ordonne, l'examen visuel décide,
comme aux cinq passes précédentes.

PIÈGE DE LICENCE. Rien ne change : domaine public et CC0 sans condition, CC-BY
et CC-BY-SA seulement avec le crédit affiché sur la fiche.

Usage : python3 tools/photos_marques.py [--limite N] [--par-societe N]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import _get, COMMONS_API, UA                     # noqa: E402
from photos_produits import score_nom, infos, prepare                 # noqa: E402

# Société → ce sous quoi ses objets sont réellement titrés dans une photothèque.
# Marques commerciales, filiales, modèles, sites exploités. Les filiations non
# évidentes ont été vérifiées : Universal Robots et Mobile Industrial Robots
# appartiennent à Teradyne depuis 2015 et 2018, Liebert est la marque d'onduleurs
# de Vertiv (ex-Emerson Network Power), Comanche Peak et Moss Landing sont
# exploités par Vistra via Luminant, Calvert Cliffs et Byron par Constellation.
MARQUES = {
    # Équipement et composants : le produit porte le nom du modèle.
    "6146.T":  ["wafer dicing saw", "wafer dicing machine", "dicing blade wafer"],
    "6857.T":  ["Advantest", "semiconductor test handler", "IC test system"],
    "8035.T":  ["Tokyo Electron", "coater developer semiconductor",
                "wafer track system"],
    "ASM.AS":  ["ASM International semiconductor", "atomic layer deposition reactor",
                "ALD reactor"],
    "LRCX":    ["Lam Research", "plasma etch chamber", "etch system semiconductor"],
    "TER":     ["Universal Robots UR5", "Universal Robots UR10",
                "Universal Robots collaborative robot", "Mobile Industrial Robots"],
    "MRVL":    ["Marvell semiconductor", "Marvell 88E", "Marvell chip board"],
    "ANET":    ["Arista Networks switch", "Arista 7050", "Arista DCS switch"],
    "CSCO":    ["Cisco Catalyst switch", "Cisco router", "Cisco IP Phone",
                "Cisco ASR router"],
    "CIEN":    ["Ciena optical", "Ciena 6500", "Ciena WaveLogic"],
    "LITE":    ["optical transceiver module", "JDSU laser", "Lumentum laser"],
    "COHR":    ["Coherent laser", "II-VI Incorporated", "laser head industrial"],
    "ASX":     ["Advanced Semiconductor Engineering", "ASE Group Kaohsiung",
                "semiconductor packaging plant"],
    "VRT":     ["Liebert UPS", "Liebert precision cooling", "Emerson Network Power",
                "data center UPS cabinet"],
    "SIE.DE":  ["Siemens Vectron", "Siemens Velaro", "SIMATIC S7",
                "Siemens gas turbine", "Siemens Desiro"],
    "GEV":     ["GE Haliade wind turbine", "General Electric wind turbine",
                "GE gas turbine", "GE Vernova"],

    # Énergie : on photographie le site, pas la holding.
    "CEG":     ["Calvert Cliffs Nuclear Power Plant", "Byron Nuclear Generating Station",
                "Braidwood Nuclear Generating Station", "Nine Mile Point Nuclear",
                "Limerick Generating Station"],
    "VST":     ["Comanche Peak Nuclear Power Plant", "Moss Landing Power Plant",
                "Martin Lake Power Plant"],
    "PWR":     ["Quanta Services", "transmission line construction",
                "power line construction crew"],

    # Santé : le médicament porte son nom, pas celui du laboratoire.
    "GILD":    ["remdesivir", "Veklury", "Truvada", "sofosbuvir", "Gilead Sciences"],
    "ZTS":     ["Zoetis", "veterinary vaccine vial", "animal health vaccine"],

    # Logiciel et internet : produits, filiales, tours qui portent l'enseigne.
    "GOOGL":   ["Waymo self-driving car", "Waymo Jaguar I-Pace", "Google data center",
                "Google Nest thermostat"],
    "CRM":     ["Salesforce Tower San Francisco", "Salesforce Tower"],
    "INTU":    ["TurboTax", "QuickBooks", "Intuit Dome", "Mailchimp"],
    "PDD":     ["Pinduoduo", "Temu package", "Temu app"],
    "TCEHY":   ["Tencent Binhai Mansion", "Tencent Seafront Towers", "WeChat app"],
    "ACN":     ["Accenture Tower", "Accenture building"],
    "NBIS":    ["Nebius data center", "Yandex data center Mantsala"],
    "CRWV":    ["CoreWeave data center"],
    "FICO":    ["Fair Isaac Corporation"],
    "MSCI":    ["MSCI headquarters"],

    # Finance : la place de marché, le distributeur, la carte, le siège nommé.
    "ICE":     ["New York Stock Exchange building", "New York Stock Exchange trading floor"],
    "CME":     ["Chicago Board of Trade Building", "Chicago Mercantile Exchange",
                "CME Group trading floor"],
    "LSEG.L":  ["London Stock Exchange building", "London Stock Exchange Paternoster"],
    "MA":      ["Mastercard credit card", "Mastercard payment terminal", "Maestro card"],
    "JPM":     ["Chase Bank ATM", "Chase Bank branch", "JPMorgan Chase Tower"],
    "MS":      ["Morgan Stanley Building", "1585 Broadway"],
    "BLK":     ["BlackRock headquarters", "iShares"],
    "KKR":     ["30 Hudson Yards", "KKR headquarters"],
    "MCO":     ["7 World Trade Center", "Moody's Corporation"],
    "SPGI":    ["Standard and Poor's", "S&P Global headquarters"],
    "UBSG.SW": ["UBS Bahnhofstrasse", "UBS bank branch", "UBS headquarters Zurich"],
    "CS.PA":   ["Tour AXA La Defense", "AXA insurance building", "AXA headquarters"],
    "BNP.PA":  ["BNP Paribas headquarters", "BNP Paribas branch", "BNP Paribas agence"],
    "MUV2.DE": ["Munich Re headquarters", "Muenchener Rueckversicherung"],
    "CB":      ["Chubb Limited", "Chubb insurance building"],
    "PGR":     ["Progressive Insurance", "Progressive Corporation campus"],

    # ── INFRASTRUCTURE DE L'IA, complément du 09/08/2026 ────────────────────
    # Onze titres entrés le même jour : le maillon des bailleurs de capacité et
    # six omissions. La leçon de la veille est appliquée tout de suite — une
    # fiche sans entrée ici est une fiche qu'aucune campagne ne pourra jamais
    # illustrer.
    #
    # LES BAILLEURS N'ONT RIEN À PHOTOGRAPHIER, ou presque : leur métier est un
    # bail. Ce qui existe en image, c'est le CAMPUS — la halle, les
    # transformateurs, la ligne haute tension — et c'est d'ailleurs le sujet
    # juste, puisque leur actif est du béton et des mégawatts.
    "APLD":   ["Applied Digital data center", "Ellendale North Dakota data center",
               "Polaris Forge data center", "hyperscale data center construction"],
    "WULF":   ["TeraWulf Lake Mariner", "Nautilus Cryptomine",
               "Lake Mariner data center", "Somerset New York power plant"],
    "CIFR":   ["Cipher Mining data center", "Odessa Texas data center",
               "Black Pearl data center"],
    "IREN":   ["IREN Childress Texas", "Iris Energy data center",
               "Prince George British Columbia data center"],
    "CORZ":   ["Core Scientific data center", "Denton Texas data center"],
    # Les six autres vendent des OBJETS, eux, et des objets nommés.
    "LR.PA":  ["Legrand socket", "Legrand busbar", "Legrand Mosaic", "Legrand PDU",
               "Legrand cable tray"],
    "FIX":    ["HVAC rooftop unit", "chiller plant mechanical room",
               "modular mechanical skid data center"],
    "EME":    ["electrical switchgear installation", "mechanical contractor pipefitting",
               "electrical conduit installation"],
    "BE":     ["Bloom Energy Server", "Bloom Box fuel cell", "solid oxide fuel cell"],
    "ALAB":   ["Astera Labs Aries retimer", "PCIe retimer", "CXL memory controller"],
    "CRDO":   ["Credo active electrical cable", "AEC cable data center",
               "SerDes chip"],

    # ── ESPACE (watchlist du 09/08/2026) ────────────────────────────────────
    # Le domaine où la table sert le MOINS : ici les engins portent le nom de la
    # société, et les agences publiques photographient tout. On nomme donc
    # directement le lanceur, le satellite ou la mission.
    "RKLB":    ["Rocket Lab Electron", "Rocket Lab Neutron", "Electron rocket launch",
                "Rocket Lab Photon"],
    "ASTS":    ["AST SpaceMobile BlueBird", "BlueWalker 3 satellite",
                "AST SpaceMobile satellite"],
    "IRDM":    ["Iridium satellite", "Iridium NEXT", "Iridium satellite phone"],
    "VSAT":    ["Viasat satellite", "ViaSat-3", "Inmarsat satellite",
                "satellite ground terminal"],
    "SESG.PA": ["SES satellite", "O3b mPOWER", "SES Astra satellite"],
    "ETL.PA":  ["Eutelsat satellite", "OneWeb satellite", "Eutelsat Konnect"],
    "PL":      ["Planet Labs Dove satellite", "SkySat satellite", "Planet Dove cubesat"],
    "RDW":     ["Redwire Space", "roll out solar array space station"],
    "BKSY":    ["BlackSky satellite", "Gen-3 satellite imaging"],
    "LUNR":    ["Intuitive Machines Nova-C", "Odysseus lunar lander",
                "IM-1 lunar lander"],
    "LHX":     ["L3Harris satellite", "L3Harris radio", "Aerojet Rocketdyne engine"],
    "KTOS":    ["Kratos Valkyrie drone", "XQ-58 Valkyrie", "Kratos target drone"],

    # ── ROBOTIQUE (watchlist du 08/08/2026) ─────────────────────────────────
    # C'est le domaine où l'écart entre la raison sociale et le nom de l'objet
    # est le plus grand de tout le fichier, et où cette table sert donc le
    # plus. Personne ne légende une photo « Yaskawa » : on écrit « Motoman »,
    # du nom de la gamme. Personne n'écrit « Rockwell Automation » sous un
    # automate : on écrit « Allen-Bradley ». Et surtout, les trois sociétés du
    # goulot ne vendent pas un produit qui porte leur nom mais une PIÈCE dont
    # le nom est technique — réducteur à onde de déformation, réducteur
    # cycloïdal, guidage linéaire. C'est ce nom-là qu'il faut chercher.
    "6954.T":    ["FANUC robot", "FANUC industrial robot arm", "FANUC CNC controller",
                  "FANUC M-710", "FANUC LR Mate"],
    "6506.T":    ["Motoman robot", "Yaskawa Motoman", "Motoman welding robot",
                  "Yaskawa servo drive"],
    "454910.KS": ["Doosan Robotics cobot", "Doosan Robotics collaborative robot",
                  "Doosan M0609"],
    # Le seul pure player humanoïde de Hong Kong ; sa gamme s'appelle Walker.
    "9880.HK":   ["UBTECH Walker robot", "UBTECH humanoid robot", "Walker X robot",
                  "UBTECH Alpha robot"],
    # HUBO, l'humanoïde du KAIST, est l'objet que cette société commercialise —
    # et il est bien plus photographié que la société elle-même.
    "277810.KQ": ["Rainbow Robotics HUBO", "HUBO humanoid robot",
                  "Rainbow Robotics cobot"],
    # Hyundai contrôle Boston Dynamics : Spot et Atlas sont, de très loin, les
    # robots les plus photographiés au monde. On les cherche avant les voitures.
    "005380.KS": ["Boston Dynamics Spot", "Boston Dynamics Atlas",
                  "Boston Dynamics Stretch", "Hyundai Motor assembly robot"],
    "TSLA":      ["Tesla Optimus robot", "Tesla factory robotic arm",
                  "Tesla Gigafactory assembly line", "Tesla Model Y production"],
    # LE GOULOT. Ces noms sont ceux de la PIÈCE, pas de la société : c'est la
    # seule façon d'en trouver une image, et c'est aussi ce que la thèse du
    # thème demande de montrer.
    "6324.T":    ["strain wave gearing", "harmonic drive gear", "Harmonic Drive reducer",
                  "robot joint gearbox cutaway"],
    "6268.T":    ["cycloidal drive", "cycloidal gear reducer", "Nabtesco RV reducer",
                  "robot speed reducer"],
    "6481.T":    ["THK LM guide", "linear motion guide rail", "linear guideway",
                  "THK ball screw"],
    "2049.TW":   ["HIWIN linear guideway", "HIWIN ball screw", "ball screw actuator",
                  "linear motion module"],
    "6471.T":    ["NSK bearing", "NSK ball screw", "rolling bearing", "deep groove ball bearing"],
    "SKF-B.ST":  ["SKF bearing", "SKF spherical roller bearing", "roller bearing SKF",
                  "SKF Gothenburg"],
    "6594.T":    ["Nidec motor", "brushless DC motor", "electric motor stator",
                  "hard disk drive spindle motor"],
    "6273.T":    ["SMC pneumatic cylinder", "pneumatic actuator", "solenoid valve manifold",
                  "pneumatic cylinder industrial"],
    # Voir et piloter : le capteur et l'automate portent des noms de gamme.
    "6861.T":    ["Keyence sensor", "Keyence laser sensor", "Keyence vision system",
                  "photoelectric sensor industrial"],
    "6645.T":    ["Omron PLC", "Omron industrial automation", "Omron proximity sensor",
                  "Omron safety light curtain"],
    "CGNX":      ["Cognex In-Sight", "Cognex DataMan", "machine vision camera industrial",
                  "industrial barcode reader"],
    "ROK":       ["Allen-Bradley PLC", "Allen-Bradley ControlLogix",
                  "Allen-Bradley control panel", "industrial control cabinet PLC"],
    # Service : le da Vinci est le robot le plus photographié après ceux de
    # Boston Dynamics, et le seul de cette liste qu'un lecteur ait pu voir.
    "ISRG":      ["da Vinci Surgical System", "da Vinci surgical robot",
                  "robotic surgery console", "Intuitive Surgical da Vinci"],
    "SYM":       ["Symbotic warehouse robot", "automated storage and retrieval system",
                  "warehouse automation robot", "goods to person robot"],
    # KION ne vend rien sous son nom : trois marques, dont Dematic pour
    # l'entrepôt automatisé et Linde pour le chariot élévateur.
    "KGX.DE":    ["Linde forklift", "STILL forklift", "Dematic warehouse automation",
                  "Dematic conveyor system"],

    # ── QUANTIQUE (watchlist du 08/08/2026) ─────────────────────────────────
    # Le cryostat à dilution est l'objet le plus photogénique du secteur, mais
    # il appartient au laboratoire plus qu'au constructeur : on cherche d'abord
    # la machine nommée, ensuite la technologie de qubit.
    "IONQ":      ["IonQ quantum computer", "trapped ion quantum computer",
                  "ion trap chip", "linear Paul trap"],
    "RGTI":      ["Rigetti quantum computer", "superconducting quantum processor",
                  "Rigetti Aspen chip", "superconducting qubit chip"],
    "QBTS":      ["D-Wave quantum computer", "D-Wave Advantage",
                  "D-Wave Systems cabinet", "quantum annealer"],
    "QUBT":      ["photonic quantum computer", "thin film lithium niobate photonic chip",
                  "integrated photonic circuit"],

    # ── FICHES ANCIENNES RESTÉES SANS IMAGE ─────────────────────────────────
    # Elles ne datent pas d'aujourd'hui, mais la campagne passe une fois : les
    # laisser dehors serait rouvrir le sujet pour rien. Toutes sont des
    # sociétés dont le PRODUIT est célèbre alors que la raison sociale ne l'est
    # pas — exactement le cas que cette table traite.
    "AM.PA":     ["Dassault Rafale", "Dassault Falcon 8X", "Rafale fighter jet"],
    "HO.PA":     ["Thales Ground Master radar", "Thales radar antenna",
                  "Thales metro signalling"],
    "SAF.PA":    ["CFM LEAP engine", "CFM56 engine", "Safran landing gear"],
    "RHM.DE":    ["Rheinmetall Boxer", "Rheinmetall Skyranger", "Rheinmetall Leopard 2"],
    "NOVO-B.CO": ["Ozempic pen", "Novo Nordisk insulin pen", "FlexPen insulin"],
    "RACE":      ["Ferrari 296 GTB", "Ferrari SF90 Stradale", "Ferrari Maranello factory"],
    "VWS.CO":    ["Vestas wind turbine", "Vestas V164", "wind turbine nacelle"],
    "DSY.PA":    ["Dassault Systemes campus Velizy", "CATIA", "SolidWorks"],
    "SAP.DE":    ["SAP headquarters Walldorf", "SAP building"],
    # AJOUTS DU 09/08/2026, après le tri des 204 candidats de la campagne.
    # Quatre sociétés n'avaient AUCUNE entrée : aucune campagne ne pouvait donc
    # les trouver, et leur fiche serait restée sans image indéfiniment.
    "BKNG":      ["hotel reception desk", "airport departure board",
                  "hotel booking website"],
    "CI":        ["health insurance card", "pharmacy prescription counter",
                  "medical claim form"],
    "FTNT":      ["network firewall appliance", "rack mounted network appliance",
                  "data center network security"],
    "REGN":      ["monoclonal antibody vial", "antibody ribbon diagram",
                  "biotechnology laboratory pipetting"],
    # Et huit termes revus, parce que Commons ne porte AUCUNE photo de ces
    # marques : la recherche retombait alors sur des livres numérisés dont le
    # texte contient les mots cherchés. On vise désormais l'OBJET du métier
    # plutôt que la marque — un lecteur de codes-barres illustre Cognex, même
    # sans logo, mieux qu'un frontispice du XIXe siècle.
    "CGNX":      ["machine vision camera", "industrial inspection camera",
                  "barcode scanner conveyor belt"],
    "CIFR":      ["bitcoin mining container", "ASIC miner rack",
                  "cryptocurrency mining farm"],
    "CORZ":      ["bitcoin mining facility", "cryptocurrency mining rig rack"],
    "APLD":      ["data center server hall", "hyperscale data center building",
                  "immersion cooling server"],
    "QUBT":      ["photonic integrated circuit", "optical waveguide chip",
                  "silicon photonics die"],
    "CRDO":      ["SerDes transceiver chip", "QSFP-DD cable",
                  "active electrical cable data center"],
    "MSCI":      ["stock index display board", "financial market data screen"],
    "ALAB":      ["PCIe retimer chip", "CXL memory module"],
    # LA WATCHLIST SPATIALE, publiée le 09/08 : seize sociétés qui n'avaient
    # aucune entrée de recherche, donc aucune chance d'être illustrées un jour.
    # On vise l'ENGIN quand il porte un nom — un lanceur, un satellite, un
    # atterrisseur se photographient et se nomment —, et le métier sinon.
    "RKLB":      ["Electron rocket launch", "Rocket Lab Electron",
                  "Photon spacecraft bus"],
    "ASTS":      ["BlueWalker 3 satellite", "phased array satellite antenna",
                  "direct to cell satellite"],
    "BKSY":      ["Earth observation smallsat", "satellite imagery ground station",
                  "cubesat imaging satellite"],
    "PL":        ["SkySat satellite", "Dove cubesat", "Planet Labs satellite"],
    "LUNR":      ["Nova-C lunar lander", "lunar lander spacecraft",
                  "Moon lander module"],
    "RDW":       ["roll out solar array spacecraft", "in space manufacturing",
                  "spacecraft solar array deployment"],
    "KTOS":      ["target drone unmanned aerial", "satellite ground station antenna",
                  "jet powered target drone"],
    "VSAT":      ["satellite internet terminal", "geostationary communications satellite",
                  "VSAT ground terminal"],
    "SESG.PA":   ["O3b mPOWER satellite", "geostationary communications satellite",
                  "satellite teleport antenna"],
    "ETL.PA":    ["OneWeb satellite", "low earth orbit communications satellite"],
    "LMT":       ["F-35 Lightning II", "Lockheed Martin spacecraft",
                  "Orion crew module"],
    "NOC":       ["James Webb Space Telescope", "Northrop Grumman Antares",
                  "Cygnus cargo spacecraft"],
    "RTX":       ["Patriot missile launcher", "Pratt and Whitney jet engine",
                  "geared turbofan engine"],
    "LHX":       ["military tactical radio", "satellite communications terminal",
                  "airborne electronic warfare pod"],
    "AIR.PA":    ["Airbus A350", "Ariane 6 launcher", "Airbus final assembly line"],
    "LDO.MI":    ["AW139 helicopter", "Leonardo helicopter", "Eurofighter Typhoon"],
    # Et cinq termes revus, dont les campagnes ont rendu le produit d'un TIERS :
    # « network firewall appliance » a proposé à Fortinet un boîtier Netgear,
    # exactement la faute de l'actionneur « SMC » portant la marque Automax.
    "FTNT":      ["Fortinet FortiGate", "data center security rack",
                  "network operations center"],
    "IREN":      ["Childress Texas data center", "bitcoin mining data centre",
                  "immersion cooled mining rig"],
    "WULF":      ["Lake Mariner data center", "bitcoin mining hall",
                  "hydroelectric powered data center"],
    "454910.KS": ["Doosan Robotics collaborative robot", "cobot robotic arm",
                  "collaborative robot arm factory"],
    "MSCI":      ["stock index display board", "financial market data terminal"],
    "BA.L":      ["Eurofighter Typhoon", "Type 26 frigate", "BAE Systems Astute submarine"],
}


# Fiches DEJA illustrees dont la revue d'ensemble a juge l'image faible. Le
# defaut est presque toujours le meme : un siege social anonyme la ou la societe
# fabrique un objet identifiable. NVIDIA, premiere valeur de la watchlist, etait
# illustree par une carte de developpement Jetson ; Intel par un parking a
# Tsukuba ; ASML, l'entreprise de la lithographie EUV, par un immeuble delave.
# On applique ici la methode qui a marche : chercher le PRODUIT.
#
# Rien n'est remplace automatiquement. Le job propose, la revue visuelle
# compare l'ancienne et la nouvelle, et l'on ne substitue que si c'est mieux.
AMELIORATIONS = {
    "NVDA":      ["Nvidia GeForce graphics card", "Nvidia Tesla GPU",
                  "Nvidia die shot", "GeForce RTX graphics card"],
    "INTC":      ["Intel wafer", "Intel Core processor", "Intel Xeon die",
                  "silicon wafer cleanroom"],
    "ASML.AS":   ["ASML lithography", "wafer stepper", "photolithography machine",
                  "EUV lithography"],
    "META":      ["Meta Quest headset", "Oculus Quest", "Meta data center"],
    "MSFT":      ["Xbox Series X", "Microsoft Surface", "Microsoft data center"],
    "005930.KS": ["Samsung Galaxy smartphone", "Samsung DRAM module",
                  "Samsung memory chip"],
    "AMAT":      ["Applied Materials machine", "semiconductor deposition system",
                  "wafer processing equipment"],
    "HSBA.L":    ["HSBC branch", "HSBC bank sign", "HSBC ATM"],
    "AXP":       ["American Express card", "American Express centurion card"],
    "MU":        ["Micron DRAM module", "Crucial SSD", "Micron memory chip"],
    "DELL":      ["Dell PowerEdge server", "Dell XPS laptop", "Dell rack server"],
    "ADBE":      ["Adobe Photoshop box", "Adobe Creative Suite box"],
    "NFLX":      ["Netflix Open Connect appliance", "Netflix DVD envelope"],
    "PYPL":      ["PayPal card reader", "PayPal Zettle terminal"],
    "STX":       ["Seagate hard disk drive", "Seagate Barracuda"],
    "CSCO":      ["Cisco Catalyst switch", "Cisco IP Phone"],
}


# Quinze fiches sans illustration. Elles n'ont ni produit ni marque
# photographiables : ce sont des banques, des assureurs, des fournisseurs
# d'indices, des agences de notation. Reste le LIEU, qui est une photo du monde
# reel attachee a CETTE societe et non a son secteur, exactement comme l'agence
# UBS de la Bahnhofstrasse ou l'usine Schneider Electric deja publiees.
#
# Le premier passage avait echoue faute de connaitre le nom des lieux :
# « BlackRock headquarters » rend un phare, leur siege s'appelle 50 Hudson
# Yards ; « London Stock Exchange building » rend le Royal Exchange, qui est un
# autre batiment. On interroge donc les adresses et les enseignes.
LIEUX = {
    "ACN":     ["Accenture Tower Chicago", "Accenture building Dublin",
                "Accenture office building"],
    "BLK":     ["50 Hudson Yards", "BlackRock office building"],
    "BNP.PA":  ["BNP Paribas agence", "BNP Paribas bank branch",
                "BNP Paribas Fortis branch"],
    "CS.PA":   ["Tour AXA Puteaux", "AXA agence", "AXA insurance office sign"],
    "KKR":     ["30 Hudson Yards", "KKR office New York"],
    "LSEG.L":  ["London Stock Exchange Paternoster Square",
                "Stock Exchange Tower London", "London Stock Exchange Group office"],
    "MA":      ["Mastercard office Purchase New York", "Mastercard sign building",
                "Mastercard acceptance sign"],
    "MCO":     ["7 World Trade Center", "Moody's headquarters New York"],
    "MSCI":    ["MSCI office London", "MSCI building"],
    "MUV2.DE": ["Muenchener Rueckversicherung Koeniginstrasse",
                "Munich Re headquarters Munich", "Munich Re building"],
    "PDD":     ["Pinduoduo headquarters Shanghai", "Pinduoduo office"],
    "SPGI":    ["55 Water Street", "S&P Global office building"],
    "8035.T":  ["Tokyo Electron headquarters", "Akasaka Biz Tower",
                "Tokyo Electron Miyagi", "Tokyo Electron Yamanashi"],
    "6146.T":  ["Disco Corporation Ota Tokyo", "Disco Corporation Hiroshima"],
    "ASX":     ["ASE Kaohsiung plant", "Advanced Semiconductor Engineering Kaohsiung",
                "Nanzih Technology Industrial Park"],
}


# SCÈNES DE PRÉSENTATION : le dirigeant montrant le produit, sur scène.
# C'est le registre de la photo retenue pour NVIDIA, Jensen Huang tenant le
# superchip GB200 devant le logo. On cherche donc les noms des dirigeants
# associés aux grands rendez-vous où les gammes se dévoilent : Computex, CES,
# les keynotes maison.
#
# CRITÈRE DE SÉLECTION, plus exigeant que d'habitude. Le PRODUIT doit être
# visible dans l'image. Un dirigeant seul devant un micro reste un portrait, et
# les portraits ont été refusés tout au long de ce travail, de Larry Fink au
# fondateur de Marvell : un visage n'illustre pas une entreprise. Ce qui change
# ici, c'est la présence de l'objet dans la main.
#
# Les noms couvrent aussi les prédécesseurs récents, parce que les photothèques
# sont pleines de clichés d'il y a trois ou cinq ans.
SCENES = {
    "AMD":       ["Lisa Su Computex", "Lisa Su CES", "Lisa Su AMD keynote"],
    "INTC":      ["Pat Gelsinger keynote", "Lip-Bu Tan Intel", "Intel keynote wafer"],
    "2330.TW":   ["C. C. Wei TSMC", "Mark Liu TSMC"],
    "QCOM":      ["Cristiano Amon", "Qualcomm CES keynote"],
    "AVGO":      ["Hock Tan Broadcom"],
    "ARM":       ["Rene Haas Arm"],
    "MU":        ["Sanjay Mehrotra Micron"],
    "005930.KS": ["Samsung Galaxy Unpacked", "Samsung CES keynote"],
    "000660.KS": ["SK hynix CES", "SK hynix exhibition"],
    "ASML.AS":   ["Christophe Fouquet ASML", "Peter Wennink ASML"],
    "AMAT":      ["Gary Dickerson Applied Materials"],
    "LRCX":      ["Tim Archer Lam Research"],
    "KLAC":      ["Rick Wallace KLA"],
    "CSCO":      ["Chuck Robbins Cisco keynote"],
    "DELL":      ["Michael Dell keynote", "Michael Dell Dell Technologies World"],
    "ANET":      ["Jayshree Ullal"],
    "MRVL":      ["Matt Murphy Marvell"],
    "ORCL":      ["Larry Ellison keynote", "Safra Catz Oracle"],
    "CRM":       ["Marc Benioff Dreamforce"],
    "MSFT":      ["Satya Nadella keynote"],
    "META":      ["Mark Zuckerberg Connect", "Mark Zuckerberg keynote"],
    "GOOGL":     ["Sundar Pichai keynote", "Google I/O keynote"],
    "AMZN":      ["Andy Jassy re:Invent", "Amazon re:Invent keynote"],
    "SIE.DE":    ["Roland Busch Siemens"],
}


# LIVRES NUMÉRISÉS : la recherche plein texte de Commons fouille le CONTENU des
# ouvrages scannés, pas seulement les titres d'images. « industrial barcode
# reader » a ainsi rendu, pour Cognex, « With the Russians in Mongolia.djvu »,
# « Origin and spread of the Tamils.djvu » et « Mexico And Its Heritage.djvu » —
# trois livres où ces mots apparaissent quelque part. Applied Digital, Cipher
# Mining, MSCI et Quantum Computing ont reçu le même traitement : des pages
# blanches et des frontispices du XIXe siècle occupant tous les emplacements de
# candidats, sans qu'aucune vraie image n'ait sa chance.
#
# Un .djvu ou un .pdf n'est JAMAIS une illustration utilisable ici. On les écarte
# à la source plutôt qu'au tri : un emplacement de candidat pris par un livre est
# un emplacement perdu pour une photo.
EXT_REFUSEES = (".djvu", ".pdf", ".tif", ".tiff", ".ogv", ".webm", ".svg")


def chercher_commons(terme, limite=14):
    """Recherche plein texte de Commons, restreinte aux fichiers illustrables."""
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "list": "search", "srnamespace": "6",
                               "srsearch": terme, "srlimit": str(limite)})
    except Exception as e:
        print(f"      ✗ « {terme} » : {type(e).__name__}")
        return []
    return [m["title"][5:] for m in (d.get("query", {}).get("search") or [])
            if m.get("title", "").startswith("File:")
            and not m["title"].lower().endswith(EXT_REFUSEES)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/marques")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=3)
    ap.add_argument("--scenes", action="store_true",
                    help="dirigeants presentant le produit sur scene")
    ap.add_argument("--termes", default="",
                    help="recherche ponctuelle, format TICKER=terme|terme ; "
                         "separer plusieurs societes par des virgules. Evite "
                         "d'ajouter une carte figee au fichier pour un essai.")
    ap.add_argument("--lieux", action="store_true",
                    help="chercher le LIEU des quinze fiches sans illustration")
    ap.add_argument("--ameliorer", action="store_true",
                    help="repasser sur des fiches DEJA illustrees dont la revue "
                         "d'ensemble a juge l'image faible")
    a = ap.parse_args()

    deja = set()
    if os.path.exists("assets/titres/LEGENDES.json"):
        deja = set(json.load(open("assets/titres/LEGENDES.json", encoding="utf-8")))
    if a.termes:
        carte = {}
        for bloc in a.termes.split(","):
            tk, _, liste = bloc.partition("=")
            termes = [t.strip() for t in liste.split("|") if t.strip()]
            if not tk.strip() or not termes:
                raise SystemExit(f"terme mal forme : « {bloc} », attendu TICKER=a|b")
            carte[tk.strip()] = termes
    else:
        carte = (SCENES if a.scenes else LIEUX if a.lieux
                 else AMELIORATIONS if a.ameliorer else MARQUES)
    # En mode amelioration on vise justement celles qui ont deja une image.
    cibles = ([t for t in sorted(carte)] if (a.ameliorer or a.lieux or a.termes or a.scenes)
              else [t for t in sorted(carte) if t not in deja])
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(cibles)} sociétés à chercher par marque et par produit\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        propositions, vus = [], set()
        for terme in carte[tk]:
            for f in chercher_commons(terme):
                if f in vus:
                    continue
                vus.add(f)
                # Le terme qui a trouvé le fichier est conservé : c'est lui qui
                # dira, à la relecture, pourquoi cette image est censée montrer
                # cette société. Sans ça on ne sait plus ce qu'on regarde.
                propositions.append((score_nom(f), f, terme))
            time.sleep(0.25)

        propositions.sort(reverse=True)
        gardes = []
        for sc, f, terme in propositions:
            if len(gardes) >= a.par_societe:
                break
            inf = infos(f)
            if not inf:
                continue
            inf.update({"score": sc, "terme": terme})
            try:
                req = urllib.request.Request(inf["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
                inf["poids"] = prepare(brut, os.path.join(a.sortie,
                                                          f"{tk}_{len(gardes)}.jpg"))
            except Exception as e:
                print(f"      ✗ téléchargement {type(e).__name__}")
                continue
            gardes.append(inf)

        if gardes:
            rapport[tk] = {"candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(propositions):3d} pistes → "
                  f"{gardes[0]['score']:3d} pts  « {gardes[0]['terme'][:24]:24s} »  "
                  f"{gardes[0]['fichier'][:40]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(propositions):3d} pistes, "
                  f"rien d'exploitable", flush=True)

    sortie_json = ("photos_scenes.json" if a.scenes
                   else "photos_termes.json" if a.termes
                   else "photos_lieux.json" if a.lieux
                   else "photos_ameliorer.json" if a.ameliorer else "photos_marques.json")
    with open(sortie_json, "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"PISTES TROUVÉES : {len(rapport)}/{len(cibles)} sociétés")


if __name__ == "__main__":
    main()
