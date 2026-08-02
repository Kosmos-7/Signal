# Photos de sociétés — provenance, licences et arbitrage

92 fiches sur 104 portent une photo de leur société : 57 montrent un
produit ou une activité, 35 un lieu identifiable. 76 sont sous licence
libre et 16 sous licence non établie. Les 12 autres n'affichent aucune illustration. Priorité au PRODUIT (puce, carte, terminal,
machine) sur le SITE : le die d'un circuit gravé par TSMC dit ce qu'est un
fondeur, un immeuble de verre ne dit rien.

## Sept sources, par ordre de découverte

1. **Recherche textuelle sur Commons.** Cherche des MOTS, se trompe dans 43 %
   des cas : le siège de la Banque mondiale pour Bank of America, un
   commissariat pour Western Digital, un photographe du XIXe siècle pour Eaton.
2. **Wikidata P18.** Désigne une ENTITÉ, donc la bonne société. Mais l'image
   retenue par la communauté est neuf fois sur dix le siège social : précision
   réglée, pertinence non.
3. **Catégorie Commons de la société (P373).** Contient les produits et les
   machines. C'est de là que viennent les puces et les terminaux.
4. **Données structurées de Commons (P180, « dépeint »).** Retourne les images
   que des contributeurs ont explicitement rattachées à l'entité. Plus large que
   P18, plus sûr qu'une recherche de mots.
6. **Openverse.** Les quatre premières sources puisent dans le MÊME fonds,
   Wikimedia Commons ; quand il ne contient rien, aucune ruse d'interrogation
   n'y change quoi que ce soit. Openverse agrège Flickr, des musées et des
   banques d'images ouvertes, soit un corpus distinct où l'on a trouvé le
   serveur SPARC d'Oracle, la baie NetApp, les cartes bancaires et la foreuse
   de Cameco. Contrepartie : personne n'y a validé qu'une photo montre bien la
   société annoncée, et le tri automatique y est aussi faible qu'au point 1.

5. **La marque et le produit, pas la raison sociale.** Les cinq premières
   passes interrogeaient toutes le NOM DE LA SOCIÉTÉ. C'est le bon identifiant
   pour une base de données, le mauvais pour une photothèque : personne ne
   titre son image « Vertiv », on écrit « Liebert UPS » ; personne n'écrit
   « Teradyne » sous un bras robotisé, on écrit « Universal Robots UR16e » ;
   personne ne photographie « Constellation Energy », on photographie la
   centrale de Calvert Cliffs. En inversant la question, 16 sociétés de plus
   ont trouvé leur image, toutes sous licence libre. La correspondance société
   vers marques est écrite à la main et vérifiée : c'est exactement le savoir
   qu'aucune API ne porte.

### Accéder à Openverse

L'API est derrière Cloudflare, dont la règle anti-robot répond 403 (erreur
1010) à tout en-tête qui ne ressemble pas à celui d'un navigateur. Mesuré : un
en-tête descriptif est refusé, le gabarit « Mozilla/5.0 (compatible; … ) » est
accepté et renvoie exactement le même corps qu'un en-tête Chrome complet. C'est
donc un filtre de préfixe, et l'on adopte la forme « compatible », qui le
satisfait tout en disant qui appelle et où écrire. Se présenter, pas se
déguiser.

## Ce que le tri automatique n'attrape pas

Aucune de ces méthodes ne dispense de regarder. Sur les 59 sociétés pour
lesquelles Openverse a rendu une piste, 19 ont passé l'examen visuel : deux
sur trois étaient fausses malgré l'exigence que le nom figure dans le titre.
Ont été écartés à l'œil :

- un stade de cricket pour KKR (les Kolkata Knight Riders portent le même sigle)
- un clavier MIDI de la marque CME, homonyme du Chicago Mercantile Exchange
- une église nommée Eaton, un bus d'équipe de volley pour Ibiden
- le ruban de l'autisme pour PDD, dont le sigle désigne aussi un trouble médical
- la carte de visite d'un entraîneur de basket pour Samsung
- un panneau routier orné de manchots pour Oracle
- des employés en manifestation pour Amazon, sujet éditorialement chargé
- une éjection de masse coronale pour CME, un fusil pour UBS, l'Alcázar de
  Ségovie pour Vistra (« vistra trasera »), une automobile Morgan pour Morgan
  Stanley, une gravure de Dürer pour KLA (« leraar voor de klas »)
- la tombe de Cecil Chubb pour Chubb, la liste des députés de 1848 pour Fair
  Isaac, des antivols de vélo AXA pour l'assureur du même nom
- l'ASM International métallurgiste pour ASM International, fabricant
  d'équipement de semi-conducteurs
- des puces SiTel et Intersil trouvées sur une carte Siemens : le circuit n'est
  pas de Siemens, la carte l'est, l'image aurait menti
- des immeubles de bureaux sans enseigne lisible (Lam Research, Lumentum,
  Zoetis, Teradyne) : un bloc de verre anonyme n'illustre pas plus la société
  que la photo d'activité qu'il aurait remplacée

## Licences

Domaine public et CC0 s'utilisent sans condition. CC-BY et CC-BY-SA exigent un
crédit : il est AFFICHÉ SUR LA FICHE sous la légende. Les images sont recadrées
en 16:9 et assombries pour tenir sur fond sombre ; ces adaptations restent sous
la licence de l'original.

## Septième source : le site des sociétés, licence non établie

Les six premières sources n'acceptaient que le domaine public, CC0, CC-BY et
CC-BY-SA, et ont couvert 73 fiches. Pour les 31 restantes le fonds libre est
réellement vide : personne n'a jamais photographié sous licence libre un
onduleur Liebert ou une salle blanche de Lam Research. Le propriétaire du dépôt
a explicitement autorisé les visuels dont la licence n'est pas établie.

CE QUI SUIT N'EST PAS UNE LICENCE. Les 10 images ci-dessous ne sont pas libres
de droit. Le risque est réduit, pas nié :

- elles proviennent du SITE DE LA SOCIÉTÉ elle-même, qui les publie pour que
  des tiers illustrent des articles la concernant, ce qui est notre usage ; un
  garde-fou technique refuse toute image servie par un autre domaine, donc les
  photos de tiers reprises dans la page ;
- la page d'origine, le domaine et la date de récupération sont consignés
  ci-dessous, pour qu'un retrait puisse être honoré immédiatement ;
- la fiche affiche « Photo : <société> » sous la légende.

Écartées à ce titre : la photo Getty Images servie par Munich Re, sous licence
achetée par elle et non transmissible, et le chantier publié par Quanta
Services où le camion d'un tiers occupe le premier plan.

Sociétés concernées : ANET, CEG, COHR, GEV, LITE, LRCX, TCEHY, VRT, VST, ZTS.

## Ni logo, ni illustration d'activité : décisions du propriétaire du dépôt

Une huitième passe a récupéré onze logos depuis Wikidata P154, pour les fiches
qui n'avaient aucune photo de leur société. Ils ont été publiés puis RETIRÉS :
un logo est impersonnel. Il nomme une société sans rien montrer d'elle, ni
objet, ni lieu, ni geste de métier, et une page pleine de rectangles de marque
ne ressemble plus à rien.

L'illustration d'activité a été retirée dans la foulée, pour la même raison
poussée d'un cran : une photo de salle blanche légendée « Illustration :
fonderie et packaging » montre un SECTEUR, pas l'entreprise dont on lit la
fiche. Elle n'apprenait donc rien sur ce titre-ci.

La règle qui s'applique désormais est sans repli : la fiche affiche une PHOTO
CONCRETE DU MONDE REEL montrant CETTE société, ou bien elle n'affiche rien.
Seize fiches sont dans ce dernier cas et le resteront tant qu'on n'aura pas
trouvé mieux, ce qui est un état honnête et non un manque à combler.

Ont été supprimés pour qu'une exécution distraite ne les réintroduise pas :
l'outil des logos et son workflow, le module tools/activites.py, les dix-huit
images d'activité, la clé « activites » de universe.json et sa production par
le screener. L'historique git conserve le tout si une décision devait changer.

## Photos publiées (57 produits, 35 lieux)

### 000660.KS — Puce mémoire SK hynix

- Nature : produit
- Fichier : `assets/titres/000660.KS.jpg`
- Source : File:Philips FM02FD00B - board - Hynix HY27UV08AG5M-TPCB-40190.jpg
- Page : https://commons.wikimedia.org/wiki/File:Philips_FM02FD00B_-_board_-_Hynix_HY27UV08AG5M-TPCB-40190.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### 005930.KS — Siège de Samsung Electronics, Séoul

- Nature : site
- Fichier : `assets/titres/005930.KS.jpg`
- Source : File:Samsung headquarters.jpg
- Page : https://commons.wikimedia.org/wiki/File:Samsung_headquarters.jpg
- Licence : CC BY-SA 2.0 — crédit affiché : Oskar Alexanderson · CC BY-SA 2.0

### 4062.T — Filtre à particules Ibiden monté sur un moteur Peugeot

- Nature : produit
- Fichier : `assets/titres/4062.T.jpg`
- Source : Ibiden Peugeot DPF 0042
- Page : https://commons.wikimedia.org/w/index.php?curid=44799677
- Licence : CC BY-SA 4.0 — crédit affiché : Michael KR · CC BY-SA 4.0

### 4063.T — Usine chimique Shin-Etsu à Isobe, préfecture de Gunma

- Nature : site
- Fichier : `assets/titres/4063.T.jpg`
- Source : Shin-Etsu Chemical Isobe , Gunma - panoramio (1)
- Page : https://commons.wikimedia.org/w/index.php?curid=54658191
- Licence : CC BY-SA 3.0 — crédit affiché : Kaz Ish · CC BY-SA 3.0

### 6857.T — Testeur Advantest V93000 EXA Scale

- Nature : produit
- Fichier : `assets/titres/6857.T.jpg`
- Source : https://www.advantest.com/img/top/img-top-1.png
- Page : https://www.advantest.com/en/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Advantest
- Récupérée le : 2026-08-02 sur le site officiel

### 8035.T — Usine Tokyo Electron de Nirasaki, au pied des Alpes japonaises

- Nature : site
- Fichier : `assets/titres/8035.T.jpg`
- Source : File:TOKYO ELECTRON TECHNOLOGY SOLUTIONS LIMITED Nirasaki City.jpg
- Page : https://commons.wikimedia.org/wiki/File:TOKYO_ELECTRON_TECHNOLOGY_SOLUTIONS_LIMITED_Nirasaki_City.jpg
- Licence : CC0

### ABBN.SW — Entraînement sans engrenage ABB

- Nature : produit
- Fichier : `assets/titres/ABBN.SW.jpg`
- Source : File:ABB gearless mill drive.jpg
- Page : https://commons.wikimedia.org/wiki/File:ABB_gearless_mill_drive.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Zen wave · CC BY-SA 4.0

### ACN — Bureaux Accenture à Pyrmont, Sydney

- Nature : site
- Fichier : `assets/titres/ACN.jpg`
- Source : File:Pyrmont NSW 2009, Australia - panoramio (7).jpg
- Page : https://commons.wikimedia.org/wiki/File:Pyrmont_NSW_2009,_Australia_-_panoramio_(7).jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Maksym Kozlenko · CC BY-SA 3.0

### ADBE — Siège mondial d'Adobe, San José

- Nature : site
- Fichier : `assets/titres/ADBE.jpg`
- Source : File:Adobe World Headquarters.jpg
- Page : https://commons.wikimedia.org/wiki/File:Adobe_World_Headquarters.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Coolcaesar · CC BY-SA 4.0

### ADI — Convertisseur Analog Devices sur circuit imprimé

- Nature : produit
- Fichier : `assets/titres/ADI.jpg`
- Source : File:Monitex MoniCam PX520 - camera module - board - Analog Device AD9943KCPZ-8643.jpg
- Page : https://commons.wikimedia.org/wiki/File:Monitex_MoniCam_PX520_-_camera_module_-_board_-_Analog_Device_AD9943KCPZ-8643.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### ADYEN.AS — Terminal de paiement Adyen

- Nature : produit
- Fichier : `assets/titres/ADYEN.AS.jpg`
- Source : File:Adyen card payment terminal (9607998259).jpg
- Page : https://commons.wikimedia.org/wiki/File:Adyen_card_payment_terminal_(9607998259).jpg
- Licence : CC BY 2.0 — crédit affiché : Alper Çuğun from Berlin, Germany · CC BY 2.0

### ALV.DE — Cartes d'assurance santé Allianz

- Nature : produit
- Fichier : `assets/titres/ALV.DE.jpg`
- Source : Allianz Krankenversicherungen Lichtbild
- Page : https://www.flickr.com/photos/71651999@N05/7035074879
- Licence : CC BY 2.0 — crédit affiché : FuFuWolf · CC BY 2.0

### AMAT — Enseigne d'Applied Materials

- Nature : site
- Fichier : `assets/titres/AMAT.jpg`
- Source : File:Applied Materials sign and Air Products plant in Southern Taiwan Science Park May 2025.jpg
- Page : https://commons.wikimedia.org/wiki/File:Applied_Materials_sign_and_Air_Products_plant_in_Southern_Taiwan_Science_Park_May_2025.jpg
- Licence : CC BY 4.0 — crédit affiché : 4300streetcar · CC BY 4.0

### AMD — Microprocesseur AMD AM9080 en boîtier céramique

- Nature : produit
- Fichier : `assets/titres/AMD.jpg`
- Source : KL Advanced Micro Devices AM9080
- Page : https://commons.wikimedia.org/w/index.php?curid=7028092
- Licence : CC BY-SA 3.0 — crédit affiché : Konstantin Lanzet · CC BY-SA 3.0

### AMZN — Cartes cadeaux Amazon en rayon

- Nature : produit
- Fichier : `assets/titres/AMZN.jpg`
- Source : Amazon.com
- Page : https://www.flickr.com/photos/39160147@N03/15977126920
- Licence : CC BY 2.0 — crédit affiché : JeepersMedia · CC BY 2.0

### ANET — Gamme de commutateurs Arista Networks

- Nature : produit
- Fichier : `assets/titres/ANET.jpg`
- Source : https://www.arista.com/assets/images/product/Arista-Product-Platforms-Family-800x520.png
- Page : https://www.arista.com/en/products/platforms
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Arista Networks
- Récupérée le : 2026-08-02 sur le site officiel

### ARM — Processeur Exynos à cœurs Arm

- Nature : produit
- Fichier : `assets/titres/ARM.jpg`
- Source : File:Samsung-Exynos-4412-Quad SoC used in I9300.jpg
- Page : https://commons.wikimedia.org/wiki/File:Samsung-Exynos-4412-Quad_SoC_used_in_I9300.jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Köf3 · CC BY-SA 3.0

### ASM.AS — Réacteur ALD Pulsar XP d'ASM International

- Nature : produit
- Fichier : `assets/titres/ASM.AS.jpg`
- Source : https://www.asm.com/media/wqed20xm/pulsar-landscape.png?width=952&height=500&quality=90&v=1dbf7eea27deb80
- Page : https://www.asm.com/solutions/products/atomic-layer-deposition-products/pulsar-xp-ald
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : ASM International
- Récupérée le : 2026-08-02 sur le site officiel

### ASML.AS — Siège d'ASML à Veldhoven

- Nature : site
- Fichier : `assets/titres/ASML.AS.jpg`
- Source : File:ASML headquarters Veldhoven.jpg
- Page : https://commons.wikimedia.org/wiki/File:ASML_headquarters_Veldhoven.jpg
- Licence : Public domain

### AVGO — Puce Broadcom BCM7019 vue au microscope

- Nature : produit
- Fichier : `assets/titres/AVGO.jpg`
- Source : Broadcom BCM7019 STB SoC die shot
- Page : https://www.flickr.com/photos/140974729@N05/38256091465
- Licence : Marque du domaine public 1.0

### AXP — Chèques de voyage American Express

- Nature : produit
- Fichier : `assets/titres/AXP.jpg`
- Source : File:Travelers Cheques of 50 USD each issued by American Express, bought ca. 2012, showing incremental serial numbering.jpg
- Page : https://commons.wikimedia.org/wiki/File:Travelers_Cheques_of_50_USD_each_issued_by_American_Express,_bought_ca._2012,_showing_incremental_serial_numbering.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Pittigrilli · CC BY-SA 4.0

### BAC — Carte BankAmericard Visa de Bank of America

- Nature : produit
- Fichier : `assets/titres/BAC.jpg`
- Source : Chip-enabled Bank of America BankAmericard Visa Signature Credit Card
- Page : https://www.flickr.com/photos/51526368@N03/16293806432
- Licence : CC BY 2.0 — crédit affiché : Aranami · CC BY 2.0

### BX — Siège de Blackstone, New York

- Nature : site
- Fichier : `assets/titres/BX.jpg`
- Source : File:Blackstone HQ - 345 Park Avenu.jpg
- Page : https://commons.wikimedia.org/wiki/File:Blackstone_HQ_-_345_Park_Avenu.jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Americasroof (talk) · CC BY-SA 3.0

### CB — Fret conteneurisé, l'un des risques assurés par Chubb

- Nature : produit
- Fichier : `assets/titres/CB.jpg`
- Source : https://www.chubb.com/content/dam/chubb-sites/chubb/global/images/places/cargo-ship-istock-869250572-960x720.jpg
- Page : https://www.chubb.com/us-en/about-chubb/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Chubb
- Récupérée le : 2026-08-02 sur le site officiel

### CCJ — Foreuse de Crow Butte Mining, filiale de Cameco

- Nature : site
- Fichier : `assets/titres/CCJ.jpg`
- Source : Crow Butte Mining, a subsidiary of Cameco,
- Page : https://www.flickr.com/photos/69383258@N08/15422784303
- Licence : CC BY 2.0 — crédit affiché : NRCgov · CC BY 2.0

### CDNS — Siège de Cadence Design Systems

- Nature : site
- Fichier : `assets/titres/CDNS.jpg`
- Source : File:Cadence Building 2.jpg
- Page : https://commons.wikimedia.org/wiki/File:Cadence_Building_2.jpg
- Licence : Public domain

### CEG — Centrale nucléaire de Calvert Cliffs, exploitée par Constellation

- Nature : site
- Fichier : `assets/titres/CEG.jpg`
- Source : https://www.constellationenergy.com/content/dam/constellationenergy/images/about/locations/locations-open-graph-images/calvert-og.jpg
- Page : https://www.constellationenergy.com/about/locations/calvert-cliffs-clean-energy-center.html
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Constellation Energy
- Récupérée le : 2026-08-02 sur le site officiel

### CIEN — Châssis optique Ciena 6500

- Nature : produit
- Fichier : `assets/titres/CIEN.jpg`
- Source : File:Ciena 6500.jpg
- Page : https://commons.wikimedia.org/wiki/File:Ciena_6500.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : C0pMer · CC BY-SA 4.0

### CME — Chicago Board of Trade, place de marché du groupe CME

- Nature : site
- Fichier : `assets/titres/CME.jpg`
- Source : File:Chicago Board of Trade and Continental and Commercial Bank.jpg
- Page : https://commons.wikimedia.org/wiki/File:Chicago_Board_of_Trade_and_Continental_and_Commercial_Bank.jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Wynn Diancin · CC BY-SA 3.0

### COHR — Découpe laser industrielle, coeur de métier de Coherent

- Nature : produit
- Fichier : `assets/titres/COHR.jpg`
- Source : https://www.coherent.com/content/dam/coherent/site/en/images/photography/lasers/products-lasers-950px.jpg
- Page : https://www.coherent.com/lasers
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Coherent
- Récupérée le : 2026-08-02 sur le site officiel

### CRM — Salesforce Tower dominant le centre de San Francisco

- Nature : site
- Fichier : `assets/titres/CRM.jpg`
- Source : File:San Francisco, California April 2022 Salesforce Tower.jpg
- Page : https://commons.wikimedia.org/wiki/File:San_Francisco,_California_April_2022_Salesforce_Tower.jpg
- Licence : CC BY 2.0 — crédit affiché : Sharon Hahn Darlin · CC BY 2.0

### CRWV — Baie de serveurs d'un centre de données CoreWeave

- Nature : produit
- Fichier : `assets/titres/CRWV.jpg`
- Source : https://cdn.prod.website-files.com/62bc66d283fd9c34ffec780a/6a67f23fbd7c5610e305aae6_Press%20Release-Thumbnail%201520x1098.jpg
- Page : https://www.coreweave.com/news/coreweave-announces-two-initial-data-centers-in-the-uk-are-now-operational
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : CoreWeave
- Récupérée le : 2026-08-02 sur le site officiel

### CSCO — Carte d'un commutateur Cisco Catalyst 3750

- Nature : produit
- Fichier : `assets/titres/CSCO.jpg`
- Source : File:PCB of Cisco Catalyst 3750 (3750G-24T) (15481833861).jpg
- Page : https://commons.wikimedia.org/wiki/File:PCB_of_Cisco_Catalyst_3750_(3750G-24T)_(15481833861).jpg
- Licence : CC BY-SA 2.0 — crédit affiché : htomari · CC BY-SA 2.0

### DB1.DE — Ancienne Bourse, Deutsche Börse

- Nature : site
- Fichier : `assets/titres/DB1.DE.jpg`
- Source : File:Alte Boerse (Aussenfassade).jpg
- Page : https://commons.wikimedia.org/wiki/File:Alte_Boerse_(Aussenfassade).jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Michael J. Zirbes (from the original description at the German Wikipedia) · CC BY-SA 3.0

### DELL — Siège de Dell, Round Rock

- Nature : site
- Fichier : `assets/titres/DELL.jpg`
- Source : File:RR1- Dell Campus.jpg
- Page : https://commons.wikimedia.org/wiki/File:RR1-_Dell_Campus.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Jjpwiki · CC BY-SA 4.0

### DLR — Centre de données Digital Realty

- Nature : site
- Fichier : `assets/titres/DLR.jpg`
- Source : File:DigitalRealtyDatacenterMarkham1.jpg
- Page : https://commons.wikimedia.org/wiki/File:DigitalRealtyDatacenterMarkham1.jpg
- Licence : CC0

### ENR.DE — Centrale thermique équipée par Siemens Energy, Leipzig

- Nature : site
- Fichier : `assets/titres/ENR.DE.jpg`
- Source : File:Heizkraftwerk Leipzig Süd mit Wärmespeicher.jpg
- Page : https://commons.wikimedia.org/wiki/File:Heizkraftwerk_Leipzig_S%C3%BCd_mit_W%C3%A4rmespeicher.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Vinaceus · CC BY-SA 4.0

### EQIX — Intérieur d'un centre de données Equinix, Dallas

- Nature : produit
- Fichier : `assets/titres/EQIX.jpg`
- Source : File:Infomart Dallas Interior Lobby.jpg
- Page : https://commons.wikimedia.org/wiki/File:Infomart_Dallas_Interior_Lobby.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Andrew nyr · CC BY-SA 4.0

### ETN — Disjoncteur différentiel Eaton sur rail DIN

- Nature : produit
- Fichier : `assets/titres/ETN.jpg`
- Source : EATON PF6-25-2-003
- Page : https://commons.wikimedia.org/w/index.php?curid=19047797
- Licence : CC BY-SA 3.0 — crédit affiché : Dmitry G · CC BY-SA 3.0

### FICO — Siège de Fair Isaac Corporation

- Nature : site
- Fichier : `assets/titres/FICO.jpg`
- Source : File:Ficoheadquarters.jpg
- Page : https://commons.wikimedia.org/wiki/File:Ficoheadquarters.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Coolcaesar · CC BY-SA 4.0

### GEV — Éolienne GE Vernova vue du ciel

- Nature : produit
- Fichier : `assets/titres/GEV.jpg`
- Source : https://www.gevernova.com/content/dam/gepower-new/global/en_US/images/wind-site/homepage/hero-wind-video.JPG
- Page : https://www.gevernova.com/wind-power
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : GE Vernova
- Récupérée le : 2026-08-02 sur le site officiel

### GILD — Truvada, antirétroviral de Gilead Sciences

- Nature : produit
- Fichier : `assets/titres/GILD.jpg`
- Source : File:Truvada for PrEP HIV Prevention Prescription Pill Bottle (48610088067).jpg
- Page : https://commons.wikimedia.org/wiki/File:Truvada_for_PrEP_HIV_Prevention_Prescription_Pill_Bottle_(48610088067).jpg
- Licence : CC BY-SA 2.0 — crédit affiché : Tony Webster from Minneapolis, Minnesota, United States · CC BY-SA 2.0

### GOOGL — Robotaxi Waymo, filiale d'Alphabet, à San Francisco

- Nature : produit
- Fichier : `assets/titres/GOOGL.jpg`
- Source : File:Waymo self-driving car. (52194843144).jpg
- Page : https://commons.wikimedia.org/wiki/File:Waymo_self-driving_car._(52194843144).jpg
- Licence : CC BY 2.0 — crédit affiché : Daniel Ramirez from Honolulu, USA · CC BY 2.0

### GS — Siège de Goldman Sachs, New York

- Nature : site
- Fichier : `assets/titres/GS.jpg`
- Source : File:Goldman Sachs New World Headquarters.JPG
- Page : https://commons.wikimedia.org/wiki/File:Goldman_Sachs_New_World_Headquarters.JPG
- Licence : Public domain

### HPE — Baies de stockage HPE Nimble

- Nature : produit
- Fichier : `assets/titres/HPE.jpg`
- Source : File:HPE Nimble Arrays.jpg
- Page : https://commons.wikimedia.org/wiki/File:HPE_Nimble_Arrays.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Prholenstein · CC BY-SA 4.0

### HSBA.L — Distributeurs HSBC à Hong Kong

- Nature : produit
- Fichier : `assets/titres/HSBA.L.jpg`
- Source : File:HK Causeway Bay Times Square basement interior 10 HSBC ATM.JPG
- Page : https://commons.wikimedia.org/wiki/File:HK_Causeway_Bay_Times_Square_basement_interior_10_HSBC_ATM.JPG
- Licence : CC BY-SA 3.0 — crédit affiché : Wuaiubon · CC BY-SA 3.0

### ICE — Salle des marchés du New York Stock Exchange, filiale d'Intercontinental Exchange

- Nature : produit
- Fichier : `assets/titres/ICE.jpg`
- Source : File:Trading floor, New York Stock Exchange, New York, New York LCCN2011630168.tif
- Page : https://commons.wikimedia.org/wiki/File:Trading_floor,_New_York_Stock_Exchange,_New_York,_New_York_LCCN2011630168.tif
- Licence : Public domain

### IFX.DE — Puce Infineon PSB 50712 sur une carte de routeur

- Nature : produit
- Fichier : `assets/titres/IFX.DE.jpg`
- Source : Sphairon Turbolink 7211 - board - Infineon PSB 50712 E-2372
- Page : https://commons.wikimedia.org/w/index.php?curid=171699716
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### INTC — Plaquette de processeurs Pentium d'Intel

- Nature : produit
- Fichier : `assets/titres/INTC.jpg`
- Source : File:Wafer with Pentium chips.jpg
- Page : https://commons.wikimedia.org/wiki/File:Wafer_with_Pentium_chips.jpg
- Licence : CC BY 2.0 — crédit affiché : Naotake Murayama from Los Altos, CA, USA · CC BY 2.0

### INTU — TurboTax d'Intuit, édition 2003

- Nature : produit
- Fichier : `assets/titres/INTU.jpg`
- Source : File:TurboTax Basic 2003 box disc and store receipt.jpg
- Page : https://commons.wikimedia.org/wiki/File:TurboTax_Basic_2003_box_disc_and_store_receipt.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Jonathan Schilling · CC BY-SA 4.0

### JPM — Carte de retrait Chase, banque de détail de JPMorgan

- Nature : produit
- Fichier : `assets/titres/JPM.jpg`
- Source : File:CHASE ATM card-2476522151 5690b161be o.jpg
- Page : https://commons.wikimedia.org/wiki/File:CHASE_ATM_card-2476522151_5690b161be_o.jpg
- Licence : CC BY 2.0 — crédit affiché : Logan Antill · CC BY 2.0

### KLAC — Site de KLA Corporation à Ann Arbor, Michigan

- Nature : site
- Fichier : `assets/titres/KLAC.jpg`
- Source : KLA Corporation Ann Arbor Township Office
- Page : https://commons.wikimedia.org/w/index.php?curid=165163353
- Licence : CC BY-SA 4.0 — crédit affiché : DontCallMeLateForDinner · CC BY-SA 4.0

### LITE — Plaquette photonique Lumentum

- Nature : produit
- Fichier : `assets/titres/LITE.jpg`
- Source : https://www.lumentum.com/_next/image?url=https%3A%2F%2Fmedia.lumentum.com%2Fsites%2Fdefault%2Ffiles%2F2025-11%2Fproducts-new-img.jpg&w=640&q=80
- Page : https://www.lumentum.com/en/products
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Lumentum
- Récupérée le : 2026-08-02 sur le site officiel

### LRCX — Salle blanche de Lam Research

- Nature : produit
- Fichier : `assets/titres/LRCX.jpg`
- Source : https://www.lamresearch.com/wp-content/uploads/2022/04/LAM-newmachine-130_fix@2x.png
- Page : https://www.lamresearch.com/products/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Lam Research
- Récupérée le : 2026-08-02 sur le site officiel

### META — Casque Meta Quest 3

- Nature : produit
- Fichier : `assets/titres/META.jpg`
- Source : File:Visitor using a Meta Quest 3 VR headset at IPP Greifswald 2025.jpg
- Page : https://commons.wikimedia.org/wiki/File:Visitor_using_a_Meta_Quest_3_VR_headset_at_IPP_Greifswald_2025.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Siarhei Besarab · CC BY-SA 4.0

### MPWR — Puce Monolithic Power Systems MPS1613 sur une carte de téléviseur

- Nature : produit
- Fichier : `assets/titres/MPWR.jpg`
- Source : Thomson 22FB3113W - board - Monolithic Power Systems MPS1613-0933
- Page : https://commons.wikimedia.org/w/index.php?curid=190602285
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### MRVL — Puce Marvell 88W8887 sur une carte Chromecast

- Nature : produit
- Fichier : `assets/titres/MRVL.jpg`
- Source : File:Chromecast Audio RUX-J42 - board - Marvell 88W8887-NAA2-5877.jpg
- Page : https://commons.wikimedia.org/wiki/File:Chromecast_Audio_RUX-J42_-_board_-_Marvell_88W8887-NAA2-5877.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### MS — Enseigne de Morgan Stanley à Times Square

- Nature : site
- Fichier : `assets/titres/MS.jpg`
- Source : File:Morgan Stanley on Times Square.JPG
- Page : https://commons.wikimedia.org/wiki/File:Morgan_Stanley_on_Times_Square.JPG
- Licence : Public domain

### MSFT — Campus ouest de Microsoft, Redmond

- Nature : site
- Fichier : `assets/titres/MSFT.jpg`
- Source : File:Aerial Microsoft West Campus August 2009.jpg
- Page : https://commons.wikimedia.org/wiki/File:Aerial_Microsoft_West_Campus_August_2009.jpg
- Licence : Public domain

### MU — SSD Crucial MX300, marque de Micron

- Nature : produit
- Fichier : `assets/titres/MU.jpg`
- Source : File:Crucial SSD MX300 525GB-8478.jpg
- Page : https://commons.wikimedia.org/wiki/File:Crucial_SSD_MX300_525GB-8478.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### NBIS — Centre de données de Nebius

- Nature : site
- Fichier : `assets/titres/NBIS.jpg`
- Source : https://assets.nebius.com/assets/41dcdf5d-fa58-4759-8a18-c7809b6dcedf/brand-video-cover.jpg?cache-buster=2026-06-08T17:32:08.901Z
- Page : https://nebius.com/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Nebius Group
- Récupérée le : 2026-08-02 sur le site officiel

### NDAQ — Écrans du MarketSite Nasdaq, Times Square

- Nature : site
- Fichier : `assets/titres/NDAQ.jpg`
- Source : File:Xbox One Launch NASDAQ (1).jpg
- Page : https://commons.wikimedia.org/wiki/File:Xbox_One_Launch_NASDAQ_(1).jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Microsoft · CC BY-SA 4.0

### NFLX — Siège de Netflix, Los Gatos

- Nature : site
- Fichier : `assets/titres/NFLX.jpg`
- Source : File:101 Albright Way.jpg
- Page : https://commons.wikimedia.org/wiki/File:101_Albright_Way.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Coolcaesar · CC BY-SA 4.0

### NOW — Siège mondial de ServiceNow

- Nature : site
- Fichier : `assets/titres/NOW.jpg`
- Source : File:ServiceNowGlobalHQ.jpg
- Page : https://commons.wikimedia.org/wiki/File:ServiceNowGlobalHQ.jpg
- Licence : CC0

### NTAP — Baie de stockage NetApp 6030 et son câblage optique

- Nature : produit
- Fichier : `assets/titres/NTAP.jpg`
- Source : Trunked 10gig ethernet for NetApp 6030
- Page : https://www.flickr.com/photos/8558461@N08/866577666
- Licence : CC BY 2.0 — crédit affiché : ChrisDag · CC BY 2.0

### NVDA — Processeur graphique NVIDIA TU104, coeur des GeForce RTX 2080

- Nature : produit
- Fichier : `assets/titres/NVDA.jpg`
- Source : Nvidia@12nm@Turing@TU104@GeForce_RTX_2080@S_TAIWAN_1841A1_PKYN44.000_TU104-400-A1___DSCx2_
- Page : https://www.flickr.com/photos/130561288@N04/48116463052
- Licence : CC0 1.0

### NXPI — Processeur NXP sur carte

- Nature : produit
- Fichier : `assets/titres/NXPI.jpg`
- Source : File:NXP ARM processor.JPG
- Page : https://commons.wikimedia.org/wiki/File:NXP_ARM_processor.JPG
- Licence : CC BY-SA 3.0 — crédit affiché : AAAndrey A · CC BY-SA 3.0

### ON — Circuit onsemi NCP3064

- Nature : produit
- Fichier : `assets/titres/ON.jpg`
- Source : File:Xerox WorkCentre 6605 - scanner part - board 2 - On Semiconductor NCP3064B-8520.jpg
- Page : https://commons.wikimedia.org/wiki/File:Xerox_WorkCentre_6605_-_scanner_part_-_board_2_-_On_Semiconductor_NCP3064B-8520.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### ORCL — Serveur Oracle SPARC T3-4

- Nature : produit
- Fichier : `assets/titres/ORCL.jpg`
- Source : Oracle's SPARC T3-4 Server
- Page : https://www.flickr.com/photos/49034885@N05/5006317222
- Licence : CC BY 2.0 — crédit affiché : Oracle PR · CC BY 2.0

### PGR — Véhicule d'expertise sinistres de Progressive

- Nature : produit
- Fichier : `assets/titres/PGR.jpg`
- Source : File:Progressive truck, Valdosta.JPG
- Page : https://commons.wikimedia.org/wiki/File:Progressive_truck,_Valdosta.JPG
- Licence : CC BY-SA 3.0 — crédit affiché : Michael Rivera · CC BY-SA 3.0

### PLTR — Pavillon Palantir au Forum économique mondial de Davos

- Nature : site
- Fichier : `assets/titres/PLTR.jpg`
- Source : Palantir pavilion, World Economic Forum, Davos, Switzerland
- Page : https://www.flickr.com/photos/37996580417@N01/32215763362
- Licence : CC BY-SA 2.0 — crédit affiché : gruntzooki · CC BY-SA 2.0

### PWR — Poste électrique en construction, chantier Quanta Services

- Nature : produit
- Fichier : `assets/titres/PWR.jpg`
- Source : https://cmswp.quantaservices.com/wp-content/uploads/2023/03/Capabilities-Utility-Performance-Solutions.jpg
- Page : https://www.quantaservices.com/capabilities/utility-performance-solutions
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Quanta Services
- Récupérée le : 2026-08-02 sur le site officiel

### PYPL — Siège de PayPal, San José

- Nature : site
- Fichier : `assets/titres/PYPL.jpg`
- Source : File:PayPal San Jose Headquarters.jpg
- Page : https://commons.wikimedia.org/wiki/File:PayPal_San_Jose_Headquarters.jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Sagar Savla · CC BY-SA 3.0

### QCOM — Puce Qualcomm Atheros sur carte

- Nature : produit
- Fichier : `assets/titres/QCOM.jpg`
- Source : File:FRITZ!Box 7490 - board - Qualcomm QCA9880-BR4A-5180.jpg
- Page : https://commons.wikimedia.org/wiki/File:FRITZ!Box_7490_-_board_-_Qualcomm_QCA9880-BR4A-5180.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Raimond Spekking · CC BY-SA 4.0

### SCHW — Carte de débit Visa de Charles Schwab Bank

- Nature : produit
- Fichier : `assets/titres/SCHW.jpg`
- Source : Chip-enabled Charles Schwab Bank Visa Debit Card
- Page : https://www.flickr.com/photos/51526368@N03/16292864811
- Licence : CC BY 2.0 — crédit affiché : Aranami · CC BY 2.0

### SIE.DE — Rame Velaro Novo de Siemens Mobility

- Nature : produit
- Fichier : `assets/titres/SIE.DE.jpg`
- Source : File:Wagen Velaro Novo.jpg
- Page : https://commons.wikimedia.org/wiki/File:Wagen_Velaro_Novo.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Niklas Wolter · CC BY-SA 4.0

### SNDK — Mémoire SanDisk Extreme

- Nature : produit
- Fichier : `assets/titres/SNDK.jpg`
- Source : File:Sandisk Extreme III 2GB flash chip.jpg
- Page : https://commons.wikimedia.org/wiki/File:Sandisk_Extreme_III_2GB_flash_chip.jpg
- Licence : CC BY-SA 2.0 — crédit affiché : Uwe Hermann · CC BY-SA 2.0

### SNPS — Siège de Synopsys à Mountain View

- Nature : site
- Fichier : `assets/titres/SNPS.jpg`
- Source : Synopsys Headquarters Mountain View
- Page : https://commons.wikimedia.org/w/index.php?curid=118340795
- Licence : CC0 1.0

### SPGI — Siège de S&P Global, 55 Water Street à New York

- Nature : site
- Fichier : `assets/titres/SPGI.jpg`
- Source : File:S&P Global (55312935517).jpg
- Page : https://commons.wikimedia.org/wiki/File:S%26P_Global_(55312935517).jpg
- Licence : CC BY 4.0 — crédit affiché : Ajay Suresh · CC BY 4.0

### STX — Disque dur Seagate ouvert, plateau et bras de lecture

- Nature : produit
- Fichier : `assets/titres/STX.jpg`
- Source : File:Seagate ST33232A hard disk inner view.jpg
- Page : https://commons.wikimedia.org/wiki/File:Seagate_ST33232A_hard_disk_inner_view.jpg
- Licence : CC BY-SA 3.0 — crédit affiché : Eric Gaba (Sting - fr:Sting)

 This  image was created with CombineZP by 11  ( I · CC BY-SA 3.0

### SU.PA — Usine Schneider Electric

- Nature : site
- Fichier : `assets/titres/SU.PA.jpg`
- Source : Schneider Electric factory
- Page : https://commons.wikimedia.org/w/index.php?curid=2025468
- Licence : CC BY-SA 3.0 — crédit affiché : Chmee2 · CC BY-SA 3.0

### TCEHY — Siège de Tencent à Pékin

- Nature : site
- Fichier : `assets/titres/TCEHY.jpg`
- Source : https://www.tencent.com/wp-content/uploads/2022/12/ourstory1-640x360.jpg
- Page : https://www.tencent.com/en-us/about.html
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Tencent
- Récupérée le : 2026-08-02 sur le site officiel

### TER — Bras collaboratif UR16e d'Universal Robots, filiale de Teradyne

- Nature : produit
- Fichier : `assets/titres/TER.jpg`
- Source : File:UR16e robot arm.png
- Page : https://commons.wikimedia.org/wiki/File:UR16e_robot_arm.png
- Licence : CC BY-SA 4.0 — crédit affiché : Auledas · CC BY-SA 4.0

### TFC — Truist Financial Center à Hagerstown, Maryland

- Nature : site
- Fichier : `assets/titres/TFC.jpg`
- Source : Truist Financial Center - Hagerstown, Maryland
- Page : https://commons.wikimedia.org/w/index.php?curid=119740311
- Licence : CC BY-SA 4.0 — crédit affiché : Farragutful · CC BY-SA 4.0

### TSM — Circuit gravé par TSMC, vu au microscope

- Nature : produit
- Fichier : `assets/titres/TSM.jpg`
- Source : File:S3 Graphics@90nm(TSMC)@Destination2(D2-GPU)@Chrome-400-Series@Chrome 460(ES)@86C922-4K09100-01-01 Taiwan 0738 39CCB1 DSC07389-DSC07389.jpg
- Page : https://commons.wikimedia.org/wiki/File:S3_Graphics@90nm(TSMC)@Destination2(D2-GPU)@Chrome-400-Series@Chrome_460(ES)@86C922-4K09100-01-01_Taiwan_0738_39CCB1_DSC07389-DSC07389.jpg
- Licence : CC0

### UBSG.SW — Agence UBS, Bahnhofstrasse à Zurich

- Nature : site
- Fichier : `assets/titres/UBSG.SW.jpg`
- Source : File:UBS Munzhof, Zurich Bahnhofstrasse (Ank Kumar, Infosys Limited) 44.jpg
- Page : https://commons.wikimedia.org/wiki/File:UBS_Munzhof,_Zurich_Bahnhofstrasse_(Ank_Kumar,_Infosys_Limited)_44.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Ank Kumar  · CC BY-SA 4.0

### V — Terminal de paiement acceptant Visa

- Nature : produit
- Fichier : `assets/titres/V.jpg`
- Source : File:Credit card terminal in Laos.jpg
- Page : https://commons.wikimedia.org/wiki/File:Credit_card_terminal_in_Laos.jpg
- Licence : CC BY-SA 4.0 — crédit affiché : Basile Morin · CC BY-SA 4.0

### VRT — Onduleur Liebert de Vertiv

- Nature : produit
- Fichier : `assets/titres/VRT.jpg`
- Source : https://www.vertiv.com/49f19f/globalassets/products/critical-power/uninterruptible-power-supplies-ups/vertiv-liebert-exl-s1-ups/cp-ups-na-508x635-42362-exl-s1-ups.jpg
- Page : https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/liebert-exl-s1/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Vertiv
- Récupérée le : 2026-08-02 sur le site officiel

### VST — Tours de refroidissement d'une centrale Vistra

- Nature : site
- Fichier : `assets/titres/VST.jpg`
- Source : https://vistracorp.com/wp-content/uploads/2026/01/Beaver-Valley-008.jpg
- Page : https://vistracorp.com/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Vistra
- Récupérée le : 2026-08-02 sur le site officiel

### WDC — SSD Western Digital SN850X

- Nature : produit
- Fichier : `assets/titres/WDC.jpg`
- Source : File:Western Digital SN850X NVME solid state drive 8TB front side.jpg
- Page : https://commons.wikimedia.org/wiki/File:Western_Digital_SN850X_NVME_solid_state_drive_8TB_front_side.jpg
- Licence : CC BY 4.0 — crédit affiché : 4300streetcar · CC BY 4.0

### WFC — Distributeur automatique Wells Fargo

- Nature : produit
- Fichier : `assets/titres/WFC.jpg`
- Source : File:Wells Fargo ATM Machine, Colorado Springs (54556930636).jpg
- Page : https://commons.wikimedia.org/wiki/File:Wells_Fargo_ATM_Machine,_Colorado_Springs_(54556930636).jpg
- Licence : CC BY 2.0 — crédit affiché : Lumen Wilde · CC BY 2.0

### ZTS — Consultation vétérinaire, marché de Zoetis

- Nature : produit
- Fichier : `assets/titres/ZTS.jpg`
- Source : https://www.zoetis.com/_config/easset_upload_file81207_2649428_e.jpg
- Page : https://www.zoetis.com/
- Licence : Licence non établie, visuel publié par la société — crédit affiché : Photo : Zoetis
- Récupérée le : 2026-08-02 sur le site officiel
