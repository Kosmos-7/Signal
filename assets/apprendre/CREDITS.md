# Illustrations de la page « Apprendre » — provenance et licences

Trois photographies aèrent la page, à la fin des sections 02, 04 et 06.
Le registre machine est `SOURCES.json` ; ce fichier-ci dit ce qu'une
liste de champs ne dit pas.

## Ce ne sont pas des photos de fiches

La doctrine des photos de sociétés est stricte : une fiche ne s'illustre
que d'une photo réelle de cette société, jamais d'un logo ni d'une
illustration d'activité, et une fiche sans photo n'affiche rien. Ces
trois images-ci ne relèvent pas de cette règle et ne prétendent rien
prouver. Ce sont des respirations entre deux sections d'un cours.

Deux conséquences assumées. La légende décrit exactement ce qu'on voit,
sans jamais porter une information nécessaire à la compréhension du
texte : une image qui ne se charge pas ne casse rien. Et le sujet n'est
choisi que pour son rapport direct au propos de la section qu'il clôt —
la corbeille du NYSE après « qui fait le prix », une chaîne d'assemblage
après « il y a une société réelle derrière chaque ligne », des cotes de
journal après « ce qui fait bouger un cours, et quand ».

## Les trois fichiers

| Section | Sujet | Source | Licence |
|---|---|---|---|
| 02 · Le marché | Corbeille du New York Stock Exchange | Carol M. Highsmith, Library of Congress | domaine public |
| 04 · L'entreprise | Chaîne d'assemblage automobile, Gliwice | Marek Ślusarczyk | CC BY 3.0 |
| 06 · Le rythme | Cotes de clôture, quotidien coréen | Mk2010 | CC BY-SA 4.0 |

Les liens vers les pages Commons d'origine sont dans `SOURCES.json`. Le
crédit est affiché sous chaque image sur la page elle-même, ce qu'exigent
CC BY et CC BY-SA.

## Ces fichiers sont des œuvres dérivées

Aucun n'est publié tel quel. Chacun est recadré en 16/7, redimensionné en
1700 × 744 et assombri pour appartenir visuellement au site plutôt qu'à
une banque d'images. Ce sont donc des adaptations, pas de simples copies,
et il faut en tirer les conséquences :

- `s4.jpg` est diffusé sous **CC BY 3.0**, comme son original.
- `s6.jpg` est diffusé sous **CC BY-SA 4.0** : la clause de partage à
  l'identique s'applique à l'adaptation, pas seulement à l'original.
- `s2.jpg` vient du domaine public, aucune obligation ne s'y attache.

## Reproductibilité

Les fichiers ne sont pas déposés à la main. Le choix est humain — les
candidats viennent de `tools/photos_marques.py`, examinés à l'œil — mais
il est écrit dans `tools/photos_apprendre.py`, qui refabrique chaque
image à l'identique depuis Commons. Le recadrage vertical et l'exposition
y sont des réglages par image : une page de journal est un aplat blanc
que l'assombrissement standard laissait éblouissante.

Régénérer : workflow **Illustrations de la page Apprendre**, paramètre
`slots` vide pour tout refaire ou `s6` pour une seule. Le workflow relance
`tools/versionner_photos.py`, qui reporte l'empreinte de contenu dans le
`?v=` de `apprendre.html` — sans quoi une image remplacée resterait en
cache sous sa nouvelle légende.
