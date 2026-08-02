# Amorces de la page « Apprendre » — provenance et licences

Chacune des douze sections s'ouvre sur une bande d'image, avant son
numéro et son titre. Le registre machine est `SOURCES.json` ; ce
fichier-ci dit ce qu'une liste de champs ne dit pas.

## Ce ne sont pas des photos de fiches

La doctrine des photos de sociétés est stricte : une fiche ne s'illustre
que d'une photo réelle de cette société, jamais d'un logo ni d'une
illustration d'activité, et une fiche sans photo n'affiche rien. Ces
douze images-ci ne relèvent pas de cette règle et ne prétendent rien
prouver. Ce sont des amorces : elles annoncent le sujet d'un chapitre.

Deux conséquences assumées. La légende décrit exactement ce qu'on voit,
sans jamais porter une information nécessaire à la compréhension du
texte : une image qui ne se charge pas ne casse rien, et une section sans
amorce reste une section complète. Et le sujet est choisi pour son
rapport direct au propos de la section, littéral quand c'est possible
(une corbeille de bourse, un certificat d'actions, des cotes de journal),
analogique quand le propos n'a pas d'objet photographiable (un fichier
cartonné pour « la fiche action », une salle de contrôle pour un
portefeuille sous surveillance).

## Les douze bandes

| Section | Sujet | Source | Licence |
|---|---|---|---|
| 01 · Principes | Façade du NYSE, Wall Street | Carlos Delgado | CC BY-SA 3.0 |
| 02 · Le marché | Corbeille du NYSE | Carol M. Highsmith, Library of Congress | domaine public |
| 03 · Fondamentaux | Certificat de cinq actions SKF, 1913 | Svenska Kullagerfabriken | domaine public |
| 04 · L'entreprise | Chaîne d'assemblage automobile, Gliwice | Marek Ślusarczyk | CC BY 3.0 |
| 05 · Valorisation | Étal de riz, marché de Toledo | QueenCityCebu | CC BY-SA 4.0 |
| 06 · Le rythme | Cotes de clôture, quotidien coréen | Mk2010 | CC BY-SA 4.0 |
| 07 · Friction réelle | Piles de pièces | KMR Photography | CC BY 2.0 |
| 08 · L'algorithme | Opératrice d'une machine Hollerith, 1964 | LSE Library | sans restriction connue |
| 09 · La fiche action | Fichier cartonné, bibliothèque de la NOAA | Jennifer Fagan-Fry | CC BY-SA 4.0 |
| 10 · Portefeuille IA | Salle de contrôle Apollo 14, 1971 | NASA Johnson Space Center | domaine public |
| 11 · Méthodologie | Journal de bord de l'Almira, 1869 | Nantucket Historical Association | sans restriction connue |
| 12 · Pour aller plus loin | Salle de lecture Suzzallo | Guywelch2000 | CC BY 4.0 |

Les liens vers les pages Commons d'origine sont dans `SOURCES.json`. Le
crédit est affiché sous chaque bande sur la page elle-même, ce qu'exigent
CC BY et CC BY-SA.

## Ces fichiers sont des œuvres dérivées

Aucun n'est publié tel quel. Chacun est recadré en 16/5, redimensionné en
1700 × 531 et retouché pour appartenir visuellement au site plutôt qu'à
une banque d'images. Ce sont donc des adaptations, pas des copies, et il
faut en tirer les conséquences : chaque fichier est diffusé sous la
licence de son original. Pour `s6`, `s9` et `s5`, la clause de partage à
l'identique de CC BY-SA s'applique à **notre** version, pas seulement à
l'originale. Les images de `s2`, `s3` et `s10` viennent du domaine
public : aucune obligation ne s'y attache.

## Le format contraint le choix, pas l'inverse

Le 16/5 est bien plus étroit que le 16/9 sur lequel les candidats sont
examinés en planche contact, et trois bandes ont raté leur sujet au
premier tirage : la façade du NYSE perdait la plaque de rue, les pièces
se réduisaient à trois points au bas d'un aplat gris, les calculs du
journal de bord disparaissaient une fois la bande assombrie. D'où trois
réglages par image dans `tools/photos_apprendre.py` — cadrage vertical,
luminosité, contraste — et la règle qui va avec : **on regarde le
résultat en 16/5, jamais la vignette d'origine**.

## Reproductibilité

Les fichiers ne sont pas déposés à la main. Le choix est humain — les
candidats viennent de `tools/photos_marques.py`, examinés à l'œil — mais
il est écrit dans `tools/photos_apprendre.py`, qui refabrique chaque
image à l'identique depuis Commons **et pose lui-même les balises dans
`apprendre.html`**. Légende, texte alternatif, crédit et empreinte n'ont
qu'une seule source : à douze images, maintenir les balises à la main
garantissait de voir tôt ou tard une légende sous la mauvaise photo.

Régénérer : workflow **Illustrations de la page Apprendre**, paramètre
`slots` vide pour tout refaire ou `s1,s7` pour quelques-unes. Le workflow
relance `tools/versionner_photos.py`, qui vérifie que l'empreinte de
contenu du `?v=` correspond bien au fichier — sans quoi une image
remplacée resterait en cache sous sa nouvelle légende.
