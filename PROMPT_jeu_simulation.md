# Prompt — « La Maison » : simulation isométrique d'une société de gestion, pour Signal

> **Comment s'en servir.** Ce fichier est un prompt à coller tel quel dans Claude Code, à la
> racine du dépôt Signal. Tout ce qui suit s'adresse à l'agent qui va écrire le code.
> **§0–§4** posent l'intention, l'objet visuel et la direction artistique · **§5–§12** décrivent
> le jeu mécanique par mécanique · **§13–§18** sont des contraintes dures (le code sera refusé
> s'il les viole) · **§19–§22** disent quand c'est fini · **§23 donne les chiffres réels avec
> leurs sources, et dit lesquels ne sont pas vérifiés** · **§24 est le contrat de plaisir** :
> lis-le avant §5, il gouverne tous les arbitrages entre réalisme et jouabilité.
>
> ⚠️ **C'est un gros morceau** — 4 000 à 6 000 lignes au total. Il est découpé en **quatre lots**
> (§20) dont **le premier est jouable seul**. Ne commence pas par le milieu.

---

## §0 — Rôle, et ce qu'il faut lire avant d'écrire une ligne

Tu travailles sur **Signal** (https://kosmos-7.github.io/Signal/) : site statique sur GitHub
Pages, screener d'actions, portefeuille fictif piloté par IA, page pédagogique. Posture du
projet, à ne jamais trahir : **neutre, aucune prétention d'alpha**, méthodes publiques
appliquées avec discipline, **erreurs publiées**.

Tu ajoutes un **cinquième onglet** : un jeu de simulation **sans fin**, en **vue isométrique**,
où l'on monte une société de gestion, où l'on aménage ses bureaux, où l'on recrute quand on en
a les moyens, où l'on parle aux gens, et où l'on apprend l'investissement **par les décisions
qu'on prend et les tuiles qu'on pose**, pas par des leçons.

| Fichier | Ce que tu y cherches |
|---|---|
| `README.md` | architecture, workflows, posture |
| `signal.css` | le design system entier — tokens, chrome, composants |
| `actualites.html` (20 Ko) | le gabarit d'une page : `<head>`, chrome, footer, script inline |
| `tests/test_chrome.py` | **les règles que ta page devra passer** — lis-le en entier |
| `tests/_sans_bibliotheques.py` | pourquoi un test vert en local peut être rouge en CI |
| `config.py` | frais de transaction (7,5 bps), seuil d'ordre (50 €), et le PFU (31,4 %) |
| `screener.py` §« PAYLOAD GRAPHIQUE » (~l.362) | format exact de `charts/<TICKER>.json` |
| `universe.json` | `stocks` : 133 titres avec `nom`, `secteur`, `devise` |
| `signal-fx.js` | le niveau de canvas attendu ici, et le respect de `prefers-reduced-motion` |
| `.claude/skills/portfolio-analyst/` | biais, discipline de vente, frameworks — le fond pédagogique |
| `CHANGELOG.md` (100 premières lignes) | la **voix** du projet — tu écriras dedans |

---

## §1 — Mission en une phrase

**« La Maison »** : on obtient le droit d'exister, on loue une adresse, on remplit un bureau
isométrique tuile par tuile, on embauche quand la trésorerie le permet, on parle aux gens, le
fonds grandit — et **la partie ne se termine jamais**, sauf par la faillite, qui est toujours
possible.

**Les chiffres du jeu sont des chiffres réels**, vérifiés et sourcés en **§23**. Ce n'est pas de
la décoration : c'est ce qui fait que ce qu'on y comprend est transposable.

---

## §2 — Les trois choses qui font que ce jeu appartient à Signal

**① Deux comptabilités qui ne tirent pas dans le même sens.** Le joueur tient à la fois
**le fonds** (l'argent des clients : valeur liquidative, performance nette, perte maximale) et
**la société de gestion** (le sien : frais encaissés − salaires − loyer − données − audit).
Elles s'opposent. Doubler l'encours double tes revenus **et** dégrade tes rendements. On peut
donc **faire faillite avec un excellent fonds**, et **prospérer avec un fonds médiocre** — le
second cas étant le plus courant dans la vraie vie. Les deux colonnes sont à l'écran en
permanence, et le jeu doit rendre les deux issues atteignables.

**② Un chiffre n'existe que si quelqu'un, dans le bureau, le calcule.** Tant que tu n'as pas
embauché de risk manager, tu ne connais pas ta volatilité — pas « elle est floutée » : **elle
n'est nulle part**. Et si ce risk manager démissionne, le chiffre **disparaît de l'écran**.
C'est la mécanique de progression, et c'est la meilleure leçon d'organisation qu'un jeu de
gestion puisse donner.

**③ Le jeu n'invente aucun fait sur aucune entreprise réelle.** Les cours sont vrais, les noms
des sociétés du portefeuille sont **masqués** (§12.3). Conséquence non négociable : **aucun texte
ne décrit ce qu'a fait une société — seulement ce qu'a fait son cours.** Un test le vérifie.

**Il n'y a pas de score.** Pas d'étoiles, pas de rang de gérant, pas de fin victorieuse. Il y a
un bureau qui grandit, des paliers qui apportent chacun leurs nouveaux problèmes, une revue
annuelle qui dit la vérité, et un audit qu'on peut commander pour savoir **ce que le hasard seul
aurait produit à ta place** (§11.3).

---

## §3 — L'objet visuel : un bureau isométrique

**Références assumées : Habbo Hotel pour la vue et l'aménagement, Pokémon première génération
pour la boîte de dialogue et le rythme des échanges.** On en reprend **la grammaire**, jamais les
ressources : aucun sprite extrait d'un jeu existant, aucune imitation de leur marque. Tout le
dessin est original et produit par le code (§4).

### §3.1 — La géométrie

- **Isométrie 2:1 (dimétrique)** — la projection des jeux de tuiles classiques, celle qui donne
  des losanges deux fois plus larges que hauts et qui se code en trois lignes.
- **Tuile de 32 × 16 px** (à `dpr` 1), **une tuile = 2 m²**. Personnage **~26 px de haut**, soit
  un peu plus d'une tuile et demie : assez pour lire une posture, assez petit pour en tenir
  vingt à l'écran.
- **Plateau de départ : 8 × 6 tuiles = 96 m²** (la taille réelle d'une boutique qui démarre,
  cf. §5). Extensible jusqu'à **12 × 9** en louant des rangées de tuiles au même bailleur.
- **Un plateau par étage**, jamais plusieurs à la fois. On change d'étage par un sélecteur
  vertical à gauche (RDC → R+1 → R+2…). Chaque étage ouvert a son loyer.
- **Caméra fixe**, pas de rotation, pas de zoom libre — seulement deux échelles (×1, ×2) pour les
  petits écrans et les grands. La rotation double le travail pour un gain nul ici.
- **Tri de profondeur** : dessin par ordre `x + y` croissant, personnages et meubles dans la même
  passe. C'est tout ce qu'il faut pour que quelqu'un passe **derrière** une plante et **devant**
  un bureau.

### §3.2 — La boîte de dialogue (l'hommage Pokémon, et l'interface centrale)

**Toute parole du jeu passe par une seule boîte, toujours au même endroit : en bas, pleine
largeur, bord fin, fond opaque.** Elle affiche le nom de qui parle, sa vignette, le texte qui
**s'écrit lettre à lettre** (réutilise `.type-cur` du design system), et l'on avance avec
`Espace` / clic / tape. Quand une décision est demandée, **les options apparaissent dans la même
boîte**, numérotées `1` à `4`.

C'est le geste identitaire du jeu : on ne clique pas dans des fenêtres, **on parle aux gens**.
Aucune fenêtre modale flottante nulle part. Le panneau de droite (§3.4) sert à consulter, jamais
à décider.

### §3.3 — Ce qui bouge

- Chaque personne suit une **machine à états** : `au poste` · `se déplace` · `en réunion` ·
  `à la machine à café` · `te cherche` · `absent`. Déplacement en **A\* sur la grille** (le
  plateau change quand on pose des meubles — des rails fixes ne suffisent plus ici), vitesse ~2
  tuiles/seconde, animation de marche en 4 directions par simple balancement, pas de planches
  d'images.
- **Un travail en cours** = petit arc de progression au-dessus du poste (le vocabulaire de
  `.ring`, en miniature). **Un travail fini** = une feuille qui part vers ton bureau.
- **Quelqu'un qui a une question vient te chercher et attend**, bulle au-dessus de la tête. Tant
  que tu n'as pas répondu, **il ne produit rien**. Le coût de l'indécision se voit, il ne s'écrit
  pas.
- **On peut cliquer n'importe qui, n'importe quand** : la boîte de dialogue s'ouvre, la personne
  dit une phrase vraie sur l'état du fonds ou sur le sien (« On est deux pour dix-huit lignes, je
  n'ai pas rouvert la n°6 depuis mars »). C'est un vrai canal d'information, pas de la
  figuration — et **c'est gratuit et sans limite**, parce que parler à son équipe doit être le
  geste le moins cher du jeu.
- **Avant un arbitrage, on peut aller consulter quelqu'un d'autre** : ça coûte quelques jours,
  ça révèle un élément, et parfois ça contredit celui qui a proposé.

### §3.4 — Le panneau

À droite (feuille dépliable en bas sur mobile), **un seul panneau à onglets** : `Fonds` ·
`Société` · `Équipe` · `Registre` · `Carnet`. Il consulte et il ne décide pas. La date, la
trésorerie de la société et l'encours du fonds restent visibles en permanence au-dessus.

### §3.5 — Le temps, dans un jeu sans fin

- **Deux horloges emboîtées** : les gens vivent en **jours ouvrés** (marche, travail, dialogues),
  le marché et l'argent se règlent au **mois** (20 jours ouvrés). À vitesse ×1, **un jour ≈ 2 s**,
  donc un mois ≈ 40 s, une année ≈ 8 minutes.
- Vitesses : **pause** · **×1** · **×2** · **×4**. `Espace` met en pause. Le jeu **se met en
  pause tout seul** quand quelqu'un attend une décision depuis plus de cinq jours, et à chaque
  imprévu majeur.
- **Aucune durée limite. Aucune fin.** Le jeu s'arrête quand le joueur ferme l'onglet, et il
  reprend exactement où il en était. La seule fin possible est la **cessation de paiement**
  (§10.4) — et même elle propose de recommencer en gardant le carnet.
- Le rythme long est donné par : **le mois** (frais, flux, marché), **le trimestre** (reporting),
  **l'année** (assemblée des investisseurs, cristallisation, entretiens, revue).

---

## §4 — Direction artistique : comment on obtient Habbo sans dessinateur

**Décision, à assumer et à écrire dans le code : tout est dessiné par géométrie, aucun fichier
image.** Un meuble est un empilement de **boîtes isométriques** à trois faces — dessus clair,
face gauche moyenne, face droite sombre — plus deux ou trois traits de détail. Un personnage est
un corps, une tête, deux bras, avec la même règle d'éclairage.

Pourquoi : il n'y a pas d'illustrateur sur ce projet, une planche de sprites cohérente représente
des semaines de travail, et un jeu à moitié dessiné est pire qu'un jeu géométrique assumé. La
géométrie procédurale donne un rendu **net, cohérent, redimensionnable, et modifiable en une
ligne** — et elle ressemble beaucoup plus à Habbo qu'on ne le croit.
*(Si un jeu de sprites arrive un jour, il se posera dans `assets/maison/` sans rien changer au
moteur : la fonction de dessin d'un meuble doit être remplaçable, une par type.)*

### §4.1 — La palette : une exception argumentée au design system

`signal.css` impose `--ac` comme accent unique. **Un décor de bureau entièrement cyan serait
illisible et laid** — un diorama a besoin de matières. La règle est donc étendue **pour le décor
seulement**, et elle est stricte :

- **Le décor a droit à une palette. L'information n'y a pas droit.**
- **Palette du décor : 7 teintes fixes, déclarées en variables CSS**, toutes désaturées et
  sombres, dérivées du fond `#06060b` : sol, cloison, bois, métal, papier, verdure, verre. Plus
  les trois valeurs d'éclairage (dessus / gauche / droite) de chaque teinte, calculées, jamais
  écrites à la main.
- **`--ac` (#74b6df) reste réservé à ce qui compte** : sélection, interaction possible, personne
  qui t'attend, tuile survolée, arc de progression.
- **`--green` et `--red` restent réservés au P&L factuel chiffré.** Interdits pour un moral, une
  jauge, un bouton, un meuble, un mur, un vêtement, une alerte.
- **Aucune information ne passe par la couleur seule** (le dépôt l'écrit noir sur blanc à propos
  des pastilles d'Actualités : « la flèche est REDONDANTE avec la couleur, et c'est voulu »). Un
  employé à bout se lit à sa **posture** et à une **icône**, jamais à sa teinte.

Le résultat visé : **un diorama sombre, éclairé de l'intérieur**, qui a l'air d'appartenir au
même site que le reste — pas une page de jeu collée sur un site de finance. Les rayures de
`.scan` passent par-dessus le canvas, comme partout ailleurs.

---

## §5 — Le bureau : la surface, les meubles, et pourquoi ça enseigne

C'est la boucle Habbo, et c'est aussi la meilleure leçon de comptabilité du jeu.

**La chaîne est stricte, et elle ne se contourne pas :**

```
trésorerie → surface louée → mobilier posé → poste de travail libre → recrutement possible
```

On ne peut **pas** embaucher sans poste libre. On ne peut pas poser de poste sans place. On ne
peut pas prendre de place sans payer le loyer tous les mois, que le fonds gagne ou perde.

**Une tuile vaut 2 m².** Plateau de départ **8 × 6 = 48 tuiles = 96 m²** — la taille réelle d'une
boutique de gestion qui démarre à quatre ou cinq. Le loyer se calcule **au m² et par an**, comme
en immobilier d'entreprise, à partir de l'adresse choisie à l'ouverture (§7.1) :

| Adresse | Loyer réel | Sur 96 m² | Effet |
|---|---|---|---|
| **Paris QCA** (8ᵉ, 2ᵉ, 9ᵉ) | ~1 080 €/m²/an | **8 640 €/mois** | crédibilité auprès des institutionnels : +collecte |
| **Paris hors QCA / 1ʳᵉ couronne** | ~450 €/m²/an | **3 600 €/mois** | neutre |
| **2ᵉ couronne / région** | ~250 €/m²/an | **2 000 €/mois** | −collecte institutionnelle, +marge |

*(Sources en §23. L'adresse est le premier arbitrage coût fixe / crédibilité du jeu, et il est
irréversible pendant trois ans — c'est un bail.)*

| Objet | Achat | Récurrent | Ce qu'il apporte |
|---|---|---|---|
| **Poste de travail** | 1 200 € | — | **obligatoire par personne employée** |
| **Terminal Bloomberg** | — | **2 500 €/mois par poste** | +2 notes/mois par analyste, données de qualité institutionnelle |
| **LSEG Workspace** | — | **1 700 €/mois** | +1 note/mois par analyste |
| **Flux de données de base** | — | **280 €/mois** | le minimum vital ; sans lui, l'analyste travaille à l'aveugle |
| **Salle de réunion** (4 tuiles + table) | 3 500 € | — | débloque le **comité d'investissement** (§8.3) |
| **Machine à café** | 400 € | 60 €/mois | +moral, et le lieu où circulent les rumeurs |
| **Armoire d'archives** | 800 € | — | divise par deux le coût d'une inspection |
| **Baie serveur** | 6 000 € | 200 €/mois | réduit fortement le risque d'incident informatique (§9) |
| **Étage supplémentaire** | 15 000 € | son propre loyer | 8 × 6 tuiles de plus |

**Le terminal de données est l'exemple à traiter avec soin** : les trois niveaux existent
vraiment, leurs prix sont réels, et l'écart entre le premier et le troisième — **2 220 €/mois,
soit un demi-salaire** — est exactement le genre d'arbitrage que fait une vraie boutique. À
écrire dans le carnet la première fois que le joueur souscrit : achat (immobilisation) contre
abonnement (charge récurrente), et pourquoi le second est plus dangereux quand les revenus
baissent.

**À écrire dans le carnet la première fois que le joueur signe un abonnement :** achat
(immobilisation) contre abonnement (charge récurrente), et pourquoi le second est plus dangereux
quand les revenus baissent.

**L'aménagement se fait en pause** (mode « plan »), à la souris ou au clavier, avec aperçu de la
tuile, rotation du meuble sur `R`, et **remboursement à 50 %** à la revente. Un meuble ne peut
pas boucher un passage : le moteur refuse la pose si elle enferme un poste (vérification de
connexité, testée).

---

## §6 — Les gens : rôles, dialogue, et le chiffre qu'ils font exister

**Deux colonnes de salaire, et c'est délibéré** : le brut que la personne négocie, et **ce qu'elle
te coûte vraiment** (+45 % de charges patronales pour un cadre — chiffre réel, §23). Le jeu
affiche les deux, côte à côte, dès la première embauche. Beaucoup de joueurs découvriront le
sujet ici avant de le découvrir ailleurs.

| Recrue | Brut mensuel | **Coût employeur** | Ce qu'elle produit | Ce qu'elle **fait apparaître à l'écran** |
|---|---|---|---|---|
| **Analyste junior** | 3 800 € | **5 500 €** | 1 note/mois | la fiche société : qualité, valorisation, thèse. **Sans analyste, tu n'as que le prix.** |
| **Analyste confirmé** | 5 500 € | **8 000 €** | 2 à 3 notes/mois | idem, en mieux et plus vite |
| **Gérant d'exécution** | 6 500 € | **9 400 €** | passe les ordres | coût d'exécution de **30 bps → 7,5 bps** (`config.py`) ; le carnet d'ordres |
| **Risk manager** | 5 500 € | **8 000 €** | contrôle a posteriori | volatilité, perte maximale, exposition sectorielle, poids par ligne |
| **RCCI (conformité)** | 4 500 € | **6 500 €** | contrôle du mandat | l'alerte de dérive **avant** la faute ; divise par 4 le coût d'une inspection. **Obligatoire pour être agréé** (§7.1) |
| **Relation investisseurs** | 4 500 € + variable | **6 500 €** + variable | reporting, collecte | +40 % de collecte à performance égale ; **sans elle, le reporting te coûte une semaine d'arbitrages par trimestre** |
| **Back-office** | 3 200 € | **4 600 €** | règlement-livraison | supprime les erreurs de règlement (sinon 0,5 %/mois d'incident coûteux) |
| **Quant** | 7 000 € | **10 100 €** | attribution, audit | **la décomposition marché / secteur / sélection**, et l'audit du §11.3 |
| **Assistant·e** | 2 600 € | **3 800 €** | logistique | +moral collectif, absorbe une partie des imprévus administratifs |

⚠️ **Fais le calcul avant d'équilibrer quoi que ce soit.** Cinq personnes ≈ **35 000 €/mois** de
masse salariale chargée, plus le loyer, plus les données : une maison de cinq coûte autour de
**500 000 € par an**. À 2 % de frais de gestion, il faut donc **~25 M€ d'encours pour payer
l'équipe**, et davantage pour dégager un résultat. **C'est la contrainte qui gouverne tout le
jeu** — et c'est la vraie (§23, marge d'exploitation du secteur : 21,2 % en 2024).

Chacun porte : **compétence 1-5**, **moral 0-100**, **ancienneté**, **salaire**, et **une voix**
(quelques traits qui font qu'on la reconnaît en trois répliques : le prudent, l'enthousiaste, le
sec, l'anxieux).

- **Recruter n'est pas instantané** : un mois de recherche, une prime d'arrivée, **trois mois
  avant la pleine productivité**. Embaucher au sommet du cycle, juste avant le retournement, est
  l'erreur classique du métier : le jeu doit permettre de la commettre, sans la souligner à
  l'avance.
- **Le moral** baisse avec la surcharge, les désaccords systématiques, l'absence d'augmentation,
  et le silence quand le fonds va mal. Sous 25, **la personne part** — et emporte le chiffre
  qu'elle faisait exister.
- **Un concurrent débauche** : surenchérir, ou laisser partir.
- **Salaires : +45 % de charges sociales**, affichées séparément la première fois. C'est une
  découverte que beaucoup de joueurs feront ici avant de la faire ailleurs.

---

## §7 — Acte I : obtenir le droit d'exister, puis écrire son mandat

### §7.1 — L'agrément (le premier acte, et il manquait complètement)

**On ne crée pas une société de gestion en cliquant.** En France, gérer l'argent d'autrui exige
un **agrément AMF de société de gestion de portefeuille**. Le jeu s'ouvre donc sur un choix réel,
que tout fondateur de boutique affronte pour de bon :

| Voie | Ce qu'il faut | Délai | Ce qu'on perd |
|---|---|---|---|
| **L'agrément en propre** | **125 000 € de capital social libéré en numéraire**, deux dirigeants, un programme d'activité, un RCCI, un dépositaire, un commissaire aux comptes, une RC pro | **3 mois** d'instruction AMF à compter du dossier complet — et il faut le monter avant | ta trésorerie de départ, et des mois |
| **L'hébergement** chez une société de gestion tierce | un accord, une rétrocession sur les frais | quelques semaines | **une part de tes frais, et le fait de ne pas être maître chez toi** — l'hôte peut te dire non |

*(Les deux existent réellement ; sources en §23.)* **Ce choix d'ouverture est excellent parce
qu'il n'a pas de bonne réponse** : l'agrément coûte cher et lent mais te rend libre et crédible ;
l'hébergement te met en marché en trois semaines mais ampute durablement ton économie et te
soumet à quelqu'un. Les deux voies restent jouables jusqu'au bout, et **passer de l'hébergement à
l'agrément plus tard est un objectif de milieu de partie** (§11.4).

**Le dossier d'agrément est le tutoriel**, et il ne ressemble pas à un tutoriel : on remplit un
dossier en répondant à des questions dans la boîte de dialogue — qui dirige, quelle stratégie,
quels moyens, qui contrôle — et **ces réponses sont le mandat du §7.2**. On apprend le métier en
le déclarant. L'AMF peut demander des compléments (une manche de plus) si le dossier est bâclé.

**L'adresse se choisit ici aussi** (§5) : elle engage un bail de trois ans et pèse tous les mois.

### §7.2 — Le mandat : ce que le joueur écrit, et qui le tient

Cinq clauses choisies dans des listes (pas de champ libre) :

1. **Univers** — Europe / États-Unis / Monde développé / un des cinq thèmes déjà écrits dans
   `universe.json` (réutilise-les, ils existent).
2. **Concentration** — nombre maximum de lignes (8 / 15 / 30), poids maximum par ligne (5/10/20 %).
3. **Style** — qualité-croissance / décote / momentum / mixte. **Le style filtre les thèses que
   tes analystes te proposent** : un fonds décote ne verra jamais passer les mêmes dossiers.
4. **Liquidité** — préavis de rachat (aucun / 30 j / 90 j) et poche de trésorerie minimale
   (0 / 5 / 10 %). **Ce choix décide de ta survie au premier choc**, et le joueur ne le comprendra
   qu'à ce moment-là. C'est voulu.
5. **Grille de frais** — gestion 0/1/1,5/2 % et performance 0/10/20 % avec *high-water mark*. Une
   grille chère finance la maison, freine la collecte, et pèse sur la performance nette affichée.

**Le mandat contraint et protège.** Les investisseurs pardonnent une mauvaise année si tu es
resté fidèle à ce qui est écrit ; ils partent si tu as dérivé, **même en gagnant**. La *dérive de
style* est une mécanique de premier plan. Modifier le mandat est possible, coûte de la confiance,
et devra être justifié à l'assemblée annuelle (§11.2).

---

## §8 — Ce que le joueur fait vraiment

### §8.1 — La boucle courte (chaque mois)
1. **Le marché bouge** (données réelles, §12), le portefeuille se revalorise.
2. **Les gens produisent** : notes, contrôles, reporting, exécution.
3. **Quelqu'un monte te voir** : proposition, objection, question, imprévu (§9).
4. **Tu arbitres** dans la boîte de dialogue.
5. **Les flux tombent** : souscriptions, rachats, frais prélevés, salaires payés, loyer.

**Un mois où l'on ne fait rien est un mois valide, et souvent un bon mois.** Le jeu ne récompense
jamais la fréquence des gestes ; la revue annuelle doit pouvoir dire au joueur que ses frais de
transaction ont mangé sa sélection.

### §8.2 — Les six familles d'arbitrages

| Famille | Qui | Exemple | Ce qu'on apprend |
|---|---|---|---|
| **Thèse** | analyste | « Marge à 34 %, dette nulle, le titre a perdu 22 % en un trimestre. On entre à combien ? » | dimensionner, prix ≠ valeur |
| **Objection** | risk manager | « Trois lignes sur quatre dans le même secteur. Le mandat dit 25 %, on est à 41 %. » | corrélation, concentration |
| **Mandat** | RCCI | « Ce dossier est hors univers. On l'écarte, ou on change le mandat ? » | dérive de style, discipline |
| **Client** | RI | « Un investisseur menace de partir : il ne comprend pas qu'on ait raté la hausse. » | pression court terme, horizon |
| **Équipe** | n'importe qui | « On me propose 30 % de plus ailleurs. » | coût du capital humain |
| **Capacité** | toi | « Un institutionnel apporte 50 M€. Notre stratégie ne passe pas cette taille. » | capacité, conflit d'intérêt |

**Règles de rédaction, non négociables :**
- **2 à 4 options, aucune évidente.** Si une option est objectivement meilleure, ce n'est pas un
  arbitrage, c'est un quiz : supprime-la ou dégrade-la.
- Chaque option affiche **son raisonnement**, jamais son résultat. Pas de « +5 % de performance ».
- **L'effet est différé et bruité.** Une bonne décision peut mal finir, et le jeu doit parfois le
  faire — c'est le cœur du sujet (chance contre compétence). **Mais ne triche pas dans l'autre
  sens non plus** : ne fais pas systématiquement échouer le joueur pour lui donner une leçon. Le
  hasard est un vrai hasard, à graine reproductible.
- Chaque option porte une **étiquette de concept** (`concentration`, `liquidité`, `frais`,
  `dérive`, `capacité`, `biais_disposition`…) qui alimente le carnet et la revue annuelle.

### §8.3 — Le comité d'investissement *(débloqué par la salle de réunion)*
Une fois par mois, réunir l'équipe : chacun donne un avis motivé sur les lignes en portefeuille,
les désaccords apparaissent, tu tranches. **Coût : une demi-journée de tout le monde.** Bénéfice :
tu vois les objections **avant** de te tromper, au lieu de les lire après. Et sur la durée, le
joueur observe **qui avait raison** — avec l'avertissement de base rate qui va avec : sur douze
avis, on ne peut rien conclure.

---

## §9 — Les imprévus : le paquet de cartes

Le joueur a demandé du Monopoly, il en aura — mais un Monopoly **honnête**, où le paquet n'est
pas une punition aléatoire : **c'est une probabilité qu'on influence**.

### §9.1 — La règle qui donne son sens au paquet
**Chaque carte a un ou plusieurs atténuateurs**, qui sont des décisions que le joueur a prises ou
non : un RCCI, une armoire d'archives, une baie serveur, un back-office, six mois de trésorerie
d'avance, une poche de liquidité, un mandat prudent. Une carte qui frappe une maison préparée
coûte peu ; la même carte sur une maison à découvert peut la tuer.

**Après coup, le carnet nomme l'atténuateur** — jamais avant : *« Une inspection coûte en moyenne
quatre fois moins cher avec un RCCI. Tu n'en avais pas. »* C'est la leçon d'assurance, et elle ne
s'apprend qu'en la payant une fois.

### §9.2 — Le paquet (à étendre, ceci est le socle)

**Coups durs**
| Carte | Atténuateur |
|---|---|
| Contrôle URSSAF / redressement de charges | assistant·e, comptabilité à jour |
| Inspection AMF | RCCI, armoire d'archives |
| Rançongiciel, données bloquées deux semaines | baie serveur, back-office |
| Erreur de saisie sur un ordre (*fat finger*) | gérant d'exécution compétent, back-office |
| Burn-out d'une personne clé | moral, effectif suffisant, machine à café |
| Le fournisseur de données augmente de 40 % | plusieurs sources, marge de trésorerie |
| Le dépositaire durcit ses conditions | encours, ancienneté |
| Un investisseur mécontent attaque | reporting régulier, fidélité au mandat |
| Dégât des eaux à l'étage | assurance (elle-même une charge, donc un arbitrage) |
| Départ groupé après une mauvaise année | moral, communication interne |
| Clause d'homme clé déclenchée par un LP | équipe étoffée, pas de dépendance à une personne |
| Krach de marché | poche de liquidité, préavis de rachat, diversification |

**Coups de chance** *(le paquet doit en contenir, sinon il devient une punition)*
| Carte | Ce que ça donne |
|---|---|
| Un family office te découvre | collecte inattendue — **et le problème de capacité qui va avec** |
| Un journaliste écrit un papier flatteur | notoriété, collecte, attentes plus hautes |
| Un très bon analyste devient disponible | recrutement rare, si tu as le poste **et** l'argent |
| Renégociation du bail | loyer en baisse |
| Une ligne fait l'objet d'une offre | plus-value, et la question de quoi faire du cash |

### §9.3 — Les garde-fous du paquet
- **Aucune carte fatale pendant les 12 premiers mois** (le temps d'apprendre à jouer).
- **Jamais deux cartes majeures à moins de 6 mois d'écart.**
- **Le tirage est conditionné à l'état** : pas d'inspection AMF avant 3 ans d'existence ou 50 M€,
  pas de rançongiciel sans informatique, pas de départ groupé si le moral est haut.
- **Tirage à graine reproductible.** Une même graine + les mêmes décisions = la même histoire.
- **Une carte n'invente jamais un fait sur une société cotée** (§2 ③). Les cartes frappent la
  maison, l'équipe, les clients, le marché — jamais une entreprise du portefeuille.

---

## §10 — Le modèle financier (à écrire juste, et à tester)

### §10.1 — La valeur liquidative
Parts de 100 € à l'ouverture. VL = (valeur des lignes + trésorerie − dettes) ÷ nombre de parts.
Souscriptions et rachats **à la VL du mois**, en créant/annulant des parts — **jamais en diluant
les porteurs existants**. La performance affichée est **celle de la part**, pas de l'encours :
un fonds dont l'encours triple pendant que la part baisse est une situation banale, et le jeu
doit pouvoir la produire.

### §10.2 — Les frais
- **Gestion** : taux annuel choisi, prélevé **mensuellement au prorata** sur l'encours moyen.
  Il sort du fonds et entre dans la société : une seule ligne, deux signes.
- **Performance** : sur la hausse de la VL **au-dessus du plus haut historique** (*high-water
  mark*), **cristallisée en fin d'année**. Après une perte, aucun frais de performance tant que
  l'ancien plus haut n'est pas repassé. **C'est le point où toutes les implémentations naïves se
  trompent** : test dédié.
- **Transaction** : 7,5 bps par sens avec un gérant d'exécution, **30 bps sans**. Ordre refusé
  sous 50 € (`MIN_TRADE_EUR`).
- **Impact de marché** : au-delà de 2 % de l'encours sur une ligne peu liquide, coût croissant.
  C'est ce qui rend la **capacité** réelle plutôt que déclarative.
- **Fiscalité** : le fonds n'est pas imposé sur ses plus-values ; **la société est imposée sur son
  résultat (25 %)**. Ne mélange pas les deux. Le PFU de `config.py` concerne le portefeuille
  personnel du site, **pas ce jeu** — ne le recopie pas par réflexe.

### §10.3 — Collecte, rachats, et la vente forcée
- La collecte suit la performance **avec deux trimestres de retard** — les flux suivent, ils
  n'anticipent pas. Modulée par ancienneté, présence d'un RI, régularité, fidélité au mandat.
- Les rachats se déclenchent sur : perte maximale au-delà d'un seuil, deux trimestres négatifs de
  suite, dérive constatée, imprévu de marché, départ d'une figure connue de la maison.
- **Si la trésorerie ne couvre pas les rachats, le moteur vend — de force, au cours du mois, en
  commençant par le plus liquide. Le joueur ne choisit pas.** Cette ligne de code est la leçon la
  plus chère du jeu : c'est la raison pour laquelle la clause de liquidité du §7 existait.

### §10.4 — La société, et la seule fin possible
Recettes = frais encaissés. Charges = salaires (+45 %) + loyer + abonnements + audit/dépositaire
+ assurance. **Trésorerie négative deux mois de suite = cessation de paiement.** Écran sobre,
factuel, qui dit **laquelle des deux comptabilités a lâché** — et propose de recommencer **en
gardant le carnet** (§11.1). C'est la seule fin du jeu, et elle n'est jamais une défaite morale :
c'est le métier.

### §10.5 — Les fonds propres réglementaires : la contrainte qui punit la croissance
**C'est la meilleure mécanique du jeu, et elle est entièrement réelle.** Une société de gestion
agréée doit maintenir en permanence des fonds propres au moins égaux au plus élevé de :

- **125 000 €**, majorés de **0,02 % de l'encours au-delà de 250 M€** (plafonné à 10 M€) ;
- **le quart des frais généraux annuels de l'exercice précédent.**

Plus une **RC professionnelle**, ou des fonds propres supplémentaires d'au moins **0,01 % des
encours** *(sources en §23)*.

Lis la deuxième ligne deux fois : **chaque embauche augmente tes frais généraux, donc le capital
que tu dois immobiliser l'année suivante.** Grandir consomme mécaniquement ta propre trésorerie,
avant même que le premier salaire soit versé. Un joueur qui recrute cinq personnes sur une bonne
année se retrouve douze mois plus tard en manque de fonds propres — et **c'est exactement ce qui
arrive dans la vraie vie.**

En cas de manquement : alerte du RCCI (si tu en as un), puis **injonction de l'AMF** — recapitaliser
sur tes deniers, ou réduire la voilure. Le carnet nomme alors le concept `fonds propres
réglementaires` et explique pourquoi il existe : il ne protège pas ton fonds, il protège **tes
clients contre ta faillite à toi**.

*(Voie hébergée : cette contrainte ne s'applique pas — c'est l'hôte qui la porte. C'est le
principal avantage de l'hébergement, et il ne se révèle qu'ici, quand le joueur agréé souffre.)*

---

## §11 — Apprendre, dans un jeu qui ne finit jamais

Un jeu sans fin ne peut pas ranger son enseignement dans un écran final. Il le distribue en
trois endroits.

### §11.1 — Le carnet (permanent, cumulatif)
Un onglet du panneau, qui se remplit tout seul. Chaque concept **rencontré** y entre, daté, avec
**la situation exacte de TA partie** qui l'a déclenché, cinq lignes d'explication, et un lien vers
la section correspondante d'`apprendre.html` (ancres `#s1`…`#s12` — **vérifie l'ancre, ne la
devine pas**). **Le carnet survit à la faillite et aux nouvelles parties** : c'est la seule chose
qui se conserve, et c'est cohérent avec ce que le jeu prétend enseigner.

Concepts à couvrir, dans leur ordre d'apparition naturel : `valeur liquidative` ·
`charge fixe et point mort` · `achat vs abonnement` · `frais de gestion et effet de traînée` ·
`high-water mark` · `écart brut/net` · `diversification et corrélation` · `taille de position` ·
`perte maximale` · `volatilité` · `illiquidité et rachats` · `vente forcée` · `dérive de style` ·
`bêta vs alpha` · `capacité d'une stratégie` · `conflit d'intérêt` · `biais de disposition` ·
`chance contre compétence`.

**Aucun texte pédagogique ne bloque le jeu.** Il entre au carnet, une pastille signale du neuf.

### §11.2 — L'assemblée annuelle (le rendez-vous)
Une fois par an, **les investisseurs viennent au bureau** — de nouveaux personnages entrent par
le RDC, traversent, s'assoient. Tu présentes l'année, ils posent trois questions tirées de ce qui
s'est réellement passé dans ta partie (« pourquoi 41 % sur un seul secteur ? », « pourquoi ces
frais de transaction ? »), tu réponds dans la boîte de dialogue, et ils décident d'ajouter ou de
retirer de l'argent. C'est le moment où **le jeu te met face à ce que tu as fait**, une fois par
an, sans jamais avoir à finir.

L'écran d'année affiche : les deux comptabilités · brut / net / indice large sur l'année et depuis
l'origine · **l'écart imputable aux seuls frais** · et, si tu as un quant, **l'attribution
marché / secteur / sélection / inexpliqué**. Sans quant : *« Personne ici n'a jamais calculé d'où
venait la performance. C'était une décision, elle a un prix : celui de ne pas savoir. »*

### §11.3 — L'audit (à commander, quand on ose)
**Débloqué par le quant, payant, et disponible à tout moment.** Le moteur rejoue **500 histoires**
sur ton propre passé — même marché, même mandat, mêmes imprévus — en décidant **au hasard** à
chaque arbitrage, et te place dans la distribution :

> *« Ta part a fait +47 % en sept ans. 500 gérants décidant au hasard avec ton mandat ont fait
> entre −18 % et +96 %, médiane +39 %. Tu es au 61ᵉ centile. Sur sept ans et 43 décisions, cet
> écart ne suffit pas à distinguer la compétence de la chance. »*

C'est la conclusion la plus honnête qu'un jeu d'investissement puisse offrir, et c'est
littéralement la posture affichée du site. **Elle n'est pas optionnelle** — mais dans un jeu sans
fin, elle devient un **service qu'on paie**, ce qui est encore plus juste.
Techniquement : le moteur tourne **sans DOM et sans interface** (§13), les 500 rejeux se font
**par tranches** avec une barre de progression, et le calcul lui-même est un moment de jeu.

### §11.4 — Les paliers (ce qui remplace les niveaux)
Pas de fin, donc des **seuils d'encours** qui apportent chacun **un pouvoir et un problème** :

Les seuils ci-dessous sont **calés sur l'économie réelle du métier** (§23), pas choisis pour être
jolis. À 2 % de frais, l'encours × 2 % = ton chiffre d'affaires annuel — garde cette règle de
trois à l'esprit en lisant la colonne de gauche.

| Encours | Ce que ça rapporte | Ce qui s'ouvre | Ce qui se complique |
|---|---|---|---|
| **5 M€** | 100 k€/an | rien : **tu ne te paies pas** | tu vis sur ton capital. C'est la phase la plus dure, et elle est normale |
| **25 M€** | 500 k€/an | l'équipe de cinq est payée | **le point mort**, tout juste. Un trimestre de rachats et tu repasses dessous |
| **50 M€** | 1 M€/an | premier vrai résultat, clients institutionnels envisageables | reporting exigé, dépositaire plus cher, premières inspections possibles |
| **100 M€** | 2 M€/an | notoriété, recrutements de haut niveau, 2ᵉ étage | **la capacité commence à mordre** sur les petites lignes |
| **250 M€** | 5 M€/an | pouvoir de négociation sur tous tes prestataires | **le seuil réglementaire** : tes fonds propres exigés se majorent de 0,02 % de l'encours au-delà (§10.5) |
| **1 Md€** | 20 M€/an | tu as gagné, au sens du métier | **ta stratégie ne passe plus cette taille — il faut choisir : fermer le fonds aux souscriptions, ou accepter de moins bien gérer** |

**Le dernier palier est le sommet du jeu** : c'est le moment où « faire grandir le fonds » et
« bien gérer » deviennent ouvertement incompatibles, et où le joueur doit choisir. Il n'y a pas de
bonne réponse, et le carnet le dit.

---

## §12 — Le contrat de données

### §12.1 — Ce qui existe
`charts/<TICKER>.json` (150 fichiers, ~24 Ko pièce). Mesuré sur le dépôt : **segment hebdomadaire
= 104 points max** (730 jours), **segment mensuel : médiane 284 points, jusqu'à 752**. Le jeu se
joue au mois : c'est le segment mensuel qui l'alimente.

Trois pièges, tous documentés dans `screener.py` (~l.362) — relis-le :
- l'abscisse est un **mois flottant** (`année×12 + (mois−1) + (jour−1)/31`) ;
- l'échantillonnage est **mixte** : sépare hebdo et mensuel par l'écart d'abscisse (≈ 0,23 contre
  ≈ 1,0), ne suppose **jamais** un pas régulier ;
- les cours sont **ajustés** (splits, dividendes), 3 chiffres significatifs sous 1.

`universe.json` → `stocks` : 133 tickers avec `nom`, `secteur`, `devise`. Source d'identité pour
la révélation.

### §12.2 — Ce que tu ajoutes : `jeu/marche.json`
Pack compact produit par `tools/jeu_marche.py` :

```jsonc
{
  "updated_at": "2026-08-12",
  "t0": 22812,            // abscisse du premier mois de la grille
  "mois": 240,
  "titres": [ {"t":"NVDA","sec":"Technologie","d":"USD","i0":0,"px":[100,104,97, …]} ]
}
```

Grille de mois commune ; un titre entré en cours de route porte son `i0` (le moteur doit gérer
les titres **non cotés au début de la partie** : ils apparaissent, c'est réaliste et gratuit).
Prix **rebasés à 100** au premier point du titre, arrondis à l'entier. 80 titres × 240 mois
≈ 19 200 nombres → **~90 Ko**, bien en dessous du budget et bien moins servi compressé.
Entrée : ≥ 150 points mensuels, secteur connu, devise connue. Écriture **atomique**
(`save_json_atomic`, `allow_nan=False`), **purge des orphelins**, branché dans
`.github/workflows/watchlist.yml` après le screener, avec `git add jeu/`.

### §12.3 — Un jeu sans fin sur une histoire finie
240 mois de données = 20 ans de jeu. Après, le jeu continue quand même :

- **Années 1 à 20 : l'histoire réelle**, dans l'ordre.
- **Au-delà : un tirage par blocs** (*block bootstrap*) — on tire au sort des **blocs de 12 mois
  consécutifs** dans l'historique réel et on les enchaîne. Les rendements restent réels, les
  corrélations entre titres à l'intérieur d'un bloc aussi ; seule la **suite** des années est
  rebattue. C'est la méthode standard, elle est honnête, et elle est infinie.
- **Le jeu le dit au joueur**, dans le carnet, à l'entrée de la 21ᵉ année. On n'invente pas des
  marchés en douce.

### §12.4 — Le masquage des sociétés
Pendant la partie : **nom fictif + vrai secteur + cours réels**. La correspondance se révèle
quand une ligne est vendue depuis plus d'un an, et dans la revue annuelle.

Les noms viennent d'une **liste fictive fixe écrite dans le moteur** (`Ardyne Semiconducteurs`,
`Ligne Bleue Santé`, `Nordvale Énergie`…), **jamais assemblés par un générateur de syllabes** :
un générateur finira par produire le nom d'une vraie entreprise, et le jeu lui collera alors un
événement inventé. L'attribution nom↔ticker est déterministe à partir de la graine.

---

## §13 — Contraintes techniques dures

1. **Statique, zéro backend, zéro build.** HTML + CSS + JavaScript classique. Pas de framework,
   pas de bundler, pas de TypeScript, pas de moteur de jeu, pas de CDN, **aucun fichier image**.
   Seule exception, déjà en place sur les quatre onglets : la police Inter, avec **exactement la
   même requête**.
2. **Quatre fichiers**, et cette découpe est ce qui rend §11.3 et §18 possibles :
   - `maison-moteur.js` — **la simulation entière : sans DOM, sans `fetch`, sans horloge.**
     Marché, portefeuille, frais, flux, équipe, meubles, imprévus, arbitrages, bilans. Termine par
     `if (typeof module !== 'undefined') module.exports = MAISON;` pour tourner **sous node**.
     Doit rejouer **500 histoires de 10 ans en moins de 2 secondes**.
   - `maison-iso.js` — le rendu isométrique : projection, tri de profondeur, boîtes, meubles,
     personnages, A\*, caméra. **Ne décide rien**, il lit un état et le dessine.
   - `maison-ui.js` — la boîte de dialogue, le panneau, le mode plan, le clavier, le tactile.
   - `maison.html` — le gabarit et la colle.
3. **Déterminisme.** Générateur pseudo-aléatoire **à graine, écrit à la main** (mulberry32, ~5
   lignes). **`Math.random()` est interdit** dans les quatre fichiers, y compris pour les
   scintillements de décor. `maison.html#/p/<graine>` rejoue le même monde.
4. **Aucune fuite du futur** : l'état au mois `m` ne contient aucune donnée de marché > `m`.
5. **Budget de données : < 250 Ko** au démarrage. **Ne charge jamais** `analyses.json` (956 Ko),
   `watchlist.json` (220 Ko), ni les 150 `charts/*.json` (3,9 Mo).
6. **Budget d'image : 60 fps sur un portable de 2020**, avec 25 personnages et un plateau plein.
   Un seul `<canvas>` de jeu, un seul `requestAnimationFrame`, **aucun DOM créé dans la boucle**.
   **Le décor statique est dessiné une fois dans un canvas hors écran** et recomposé — seuls les
   personnages et les arcs de progression sont redessinés à chaque image. Le rendu **s'arrête
   quand l'onglet est caché**.
7. **Sauvegarde, et c'est critique dans un jeu sans fin** : `localStorage`, clé
   `signal.maison.v1`, objet **versionné** avec migration. **Sauvegarde automatique à chaque fin
   de mois** et à chaque fermeture d'onglet (`visibilitychange`). **L'état doit rester borné** :
   agrège l'historique au-delà de 5 ans (une ligne par mois, pas une par jour), plafonne les
   journaux, et **teste qu'une partie de 50 ans tient sous 1 Mo**. Tout accès en `try/catch`
   (en navigation privée Safari, `setItem` lève, et le jeu doit rester jouable sans mémoire).
   Bouton **« exporter ma partie »** (fichier JSON) et **« effacer mes données »**. Rien ne quitte
   le navigateur.

---

## §14 — Le design system : réutiliser, et ne pas redéfinir

**Réutilise tel quel** : `.card`, `.sec`/`.sec-h`, `.eyebrow`, `.tag`, `.metrics`, `.meter`,
`.ring`, `.gauge`, `.bar-track`/`.bar-fill`, `.sep`, `.pos`/`.neg`/`.neu`, `.type-cur`, et les
keyframes `blink`/`rise`/`ringglow`. La palette du décor est une **exception argumentée et
bornée** — relis le §4.1, c'est la seule licence accordée.

**Ne redéfinis JAMAIS** dans `maison.html` les sélecteurs nus du chrome partagé : `.brand`,
`.brand-name`, `.brand-icon`, `nav`, `nav a`, `nav a svg`, `.footer-legal`, `.footer-right`.
**`tests/test_chrome.py` fait échouer la CI si tu le fais.** `header{position:…}` reste permis :
ta page ne défile pas (le plateau occupe l'écran), donc **header `fixed`** — et alors **tu
compenses explicitement sa hauteur**, comme `index.html` le fait (`top:5.6rem`). Recopie le motif
**en entier**, jamais à moitié : c'est un bug déjà survenu et documenté dans le CSS.

---

## §15 — Accessibilité, mobile, et le registre

Un jeu de petits personnages est **par nature visuel**. On ne peut pas faire semblant du
contraire ; on peut refuser d'en faire un jeu **exclusivement** visuel.

- **Le registre** : un onglet du panneau qui donne **en texte et en permanence** tout ce que le
  plateau raconte en images — qui fait quoi, qui attend, ce qui vient de se passer, l'état des
  deux comptabilités, les meubles posés. **Toute la partie doit être jouable depuis le registre
  seul**, aménagement compris. Ce n'est pas un mode dégradé : c'est aussi la vue que préféreront
  les joueurs pressés.
- **Clavier de bout en bout** : `Espace` pause / avancer le dialogue · `1`-`4` choisir une option
  · `Tab` circuler entre les personnes · `Entrée` interagir · `P` mode plan · `R` rotation d'un
  meuble · `C` carnet · `L` registre · `1`/`2`/`3` vitesses. Focus toujours visible.
- Le `<canvas>` est `aria-hidden`. Un `aria-live="polite"` **sobre** annonce les arbitrages en
  attente et les imprévus — **pas chaque jour qui passe**, sinon un lecteur d'écran parle en
  continu pendant des heures.
- **`prefers-reduced-motion`** : personne ne marche (les gens changent d'état **sans
  interpolation**), pas de balancement, pas de lueur pulsée, le texte du dialogue **s'affiche d'un
  coup**. Le jeu reste entier. `signal-fx.js` respecte déjà ce réglage : fais pareil, ce n'est pas
  négociable.
- **Mobile ≥ 360 px** : plateau en échelle ×1 avec défilement à un doigt, panneau en feuille
  dépliable (même motif que `.tocm` dans `signal.css` — va le lire), boîte de dialogue pleine
  largeur, cibles ≥ 44 px. **Le mode plan doit rester utilisable au doigt** : sélection du meuble,
  puis tape sur la tuile, jamais de glisser-déposer fin.
- Contraste ≥ 4,5:1 pour tout texte, y compris posé sur le plateau. Vérifie, ne suppose pas.

---

## §16 — Le cinquième onglet : la checklist exacte

`tests/test_chrome.py` compare **les quatre onglets entre eux** ; en ajouter un cinquième touche
tous les fichiers ci-dessous.

1. **`maison.html`** — doit porter, sous peine d'échec CI : `rel="icon"` (favicon en data-URI,
   **identique** aux autres) · `name="description"` · la **même** requête
   `fonts.googleapis.com/css2?family=Inter…` · `signal.css` · `signal-fx.js` · `.footer-legal`
   avec la mention AMF **au mot près** · `.footer-right`. Plus le décor commun : `#fx`,
   `<canvas id="bg">`, `.scan`, `.frame` (les quatre `<i>`).
2. **La nav, dans les CINQ pages** — même ordre, mêmes libellés partout, et **« Portefeuille IA »
   doit rester la dernière entrée** (un test l'exige nommément) :
   `Watchlists · Actualités · Apprendre · La Maison · Portefeuille IA`
   Le lien : `<a href="maison.html">`, `<svg viewBox="0 0 24 24" aria-hidden="true">` en **tracé**
   (`stroke:currentColor`, jamais de `fill`), libellé dans un `<span>` — sinon le test de nav ne
   le trouve pas et l'icône ne prend pas la couleur de l'onglet actif.
   *Glyphe suggéré : une tuile isométrique — un losange et deux arêtes verticales. Lisible à
   19 px, et il annonce exactement ce qu'on va voir.*
3. **`tests/test_chrome.py`** — ajouter `"maison.html"` à `PAGES`, **corriger les libellés qui
   disent « les 4 onglets »**. Les contrôles propres à `index.html` restent intacts.
4. **`README.md`** — « Architecture » (la page, les trois JS, `jeu/marche.json`,
   `tools/jeu_marche.py`) et « Fichiers clés ». Au passage : **le README annonce encore
   « PFU 30 % » alors que `config.py` est à 31,4 %** depuis la LFSS 2026 — corrige-le.
5. **`.github/workflows/watchlist.yml`** — génération du pack, `git add jeu/`.
6. **`CHANGELOG.md`** — une entrée en tête (§19).

---

## §17 — Tests

**Les tests de ce dépôt tournent HORS LIGNE, sans aucune dépendance installée**, à chaque poussée
(`.github/workflows/tests.yml`). Style de la maison : un fichier `tests/test_maison.py`,
exécutable seul, **un docstring qui explique POURQUOI le fichier existe** (pas ce qu'il fait), la
fonction `check(nom, cond, detail)`, les `✅`/`❌`, le décompte final, `sys.exit(1)` si rouge. Et
avant de croire un « tout est vert » local : **`PYTHONPATH=tests python3 tests/test_maison.py`**
(cf. `tests/_sans_bibliotheques.py`).

**Le moteur se teste POUR DE VRAI, sous node** — motif déjà employé par `test_chrome.py`,
`test_charts.py` et `test_actualites.py` : on exécute le code livré, on ne le relit pas. Et comme
eux, **si node manque, on l'écrit** (`⚠️ non vérifié (node indisponible)`), on ne fait pas semblant.

| # | Propriété | Pourquoi elle compte |
|---|---|---|
| 1 | **Reproductibilité** : même graine + mêmes décisions ⟹ état identique au centime, à 10 ans | tout le reste en dépend, l'audit le premier |
| 2 | **Aucun `Math.random()`** dans les quatre fichiers | une seule occurrence casse (1) en silence |
| 3 | **VL** : souscription et rachat à la VL du mois ne changent pas la VL des porteurs existants | la dilution est le bug classique, invisible à l'œil |
| 4 | **High-water mark** : après −20 % puis +15 %, **aucun** frais de performance | toutes les implémentations naïves se trompent ici |
| 5 | **Frais de gestion** : 2 %/an sur encours constant ⟹ 2 % ± 0,01 sur douze mois | le prorata mensuel est vite faux |
| 6 | **Exécution** : 7,5 bps avec gérant, 30 bps sans ; refus sous 50 € | la promesse d'honnêteté |
| 7 | **Les constantes du JS égalent celles de `config.py`** (parsées des deux côtés, comparées) | motif `FD_RUPTURE` de `test_chrome.py` : un doublon dérive toujours |
| 8 | **Rachat > trésorerie ⟹ vente forcée**, par ordre de liquidité, tracée dans la VL | la leçon centrale : si elle est fausse, le jeu ment |
| 9 | **Pas de fuite du futur** : sur une matrice marquée, l'état au mois `m` ne contient rien de > `m` | sans ça, tout le jeu perd son sens |
| 10 | **Cessation de paiement** : trésorerie négative deux mois ⟹ fin, **même si le fonds performe** | le §2 ① doit être atteignable, pas théorique |
| 11 | **Chaîne d'aménagement** : pas d'embauche sans poste libre ; pas de pose qui enferme un poste (connexité) | c'est la boucle du jeu ; un contournement la vide |
| 12 | **A\*** : chemin trouvé sur plateau encombré, échec propre si la cible est inatteignable | un personnage coincé bloque la production, en silence |
| 13 | **Paquet d'imprévus** : aucune carte fatale avant 12 mois, jamais deux majeures à < 6 mois, conditions d'état respectées sur 1 000 tirages | un paquet mal bridé rend le jeu injouable ou risible |
| 14 | **Atténuateurs** : la même carte, même graine, coûte strictement moins cher avec son atténuateur | c'est ce qui distingue ce paquet d'une punition aléatoire |
| 15 | **Bootstrap par blocs** : au-delà du réel, blocs de 12 mois issus de l'historique, moyenne et écart-type dans les bornes de la série d'origine | on prolonge le marché, on ne l'invente pas |
| 16 | **Audit** : 500 rejeux à graine fixe ⟹ distribution stable ; un joueur inactif tombe près de la médiane des inactifs | un contrefactuel biaisé produit une conclusion fausse et péremptoire |
| 17 | **Performance moteur** : 500 histoires × 120 mois en **< 2 s** sous node | sinon l'audit est injouable |
| 18 | **Sauvegarde** : partie de **50 ans < 1 Mo** ; état v1 relu ; `localStorage` indisponible ⟹ jeu jouable quand même | un jeu sans fin qui gonfle sans fin finit par ne plus se charger |
| 19 | **Graphe de déblocage** : sans cycle, chaque métrique rattachée à un rôle, chaque concept du §11.1 atteignable | un concept inatteignable est une promesse non tenue |
| 20 | **Imprévus et lignes** : aucun modèle de carte ne contient de texte narratif sur une société ; les événements de ligne ne portent que des champs calculés | la règle du §2 ③ est trop importante pour reposer sur la vigilance |
| 21 | **Noms masqués** : liste fixe, sans doublon, attribution déterministe | idem |
| 22 | **Intégrité du pack** : tout titre de `jeu/marche.json` existe dans `charts/`, aucune valeur non finie, grille strictement croissante, aucun orphelin | même garde que la purge de `charts/` |
| 23 | **Les scripts inline de `maison.html` se parsent** (`node --check`) | une erreur de syntaxe a déjà mis le site entier en panne (09/08/2026) |
| 24 | **Fonds propres réglementaires** : le plancher vaut bien `max(125 000 € + 0,02 % de l'encours au-delà de 250 M€, ¼ des frais généraux N−1)` ; une embauche en année N **relève le plancher en N+1** | c'est la mécanique du §10.5, et une formule fausse la transforme en décor |
| 25 | **Voie hébergée** : aucune exigence de fonds propres, mais la rétrocession s'applique à **chaque** encaissement de frais | les deux voies doivent rester jouables jusqu'au bout, et différentes |
| 26 | **Point mort** : avec l'équipe de cinq du §6 et un loyer QCA, la société est déficitaire sous ~25 M€ d'encours et bénéficiaire au-dessus | test d'**équilibrage**, pas de règle métier : il protège contre une dérive silencieuse des barèmes |

---

## §18 — Textes et pédagogie

- **Français.** Ton du projet : précis, factuel, posé, une pointe d'esprit pince-sans-rire
  **occasionnelle**, jamais de hype, jamais de reco déguisée (cf. `GUIDE_redaction_analyses.md`).
  Les personnages ont le droit d'être vivants ; le jeu, lui, ne blague jamais sur un chiffre.
- **Trois lignes maximum** pour présenter quoi que ce soit. Personne ne lit le quatrième
  paragraphe d'un jeu.
- **Ce qu'on n'écrit jamais** : « bien joué, tu as du flair », un score de compétence, une
  projection en euros réels, « avec cette stratégie tu aurais gagné X € ».
- **Ce qu'on écrit quand le joueur gagne** : de combien il a battu l'indice, et sur combien
  d'années ce résultat tiendrait encore du hasard.
- **Le badge « fictif »** (`--gold`) est visible en permanence, et la page reprend la formule
  éprouvée de `portfolio.html` : *« Société et fonds 100 % fictifs. Aucune somme réelle investie.
  Cours réels du marché. »*

---

## §19 — Livrables, commits, changelog

```
maison.html                 gabarit et colle
maison-moteur.js            la simulation — pure, sans DOM, rejouable sous node
maison-iso.js               le rendu isométrique — projection, tri, meubles, personnages, A*
maison-ui.js                boîte de dialogue, panneau, mode plan, clavier, tactile
jeu/marche.json             pack de marché compact (généré, committé)
tools/jeu_marche.py         le générateur — atomique, avec purge des orphelins
tests/test_maison.py        la suite (§17)
index.html · actualites.html · apprendre.html · portfolio.html   + 5ᵉ entrée de nav
tests/test_chrome.py        PAGES + libellés
.github/workflows/watchlist.yml   génération du pack
README.md                   architecture, fichiers clés, correction du PFU
CHANGELOG.md                l'entrée
```

**Commits** : français, préfixés comme le dépôt (`feat(maison): …`, `fix(chrome): …`), **une
phrase qui dit ce qui change pour le lecteur**, jamais ce que fait le code. Regarde
`git log --oneline -20`.

**CHANGELOG** : une entrée en tête, titrée comme les autres — une phrase qui **raconte le problème
ou la décision**, pas « ajout du jeu ». Ce dépôt écrit ses entrées comme des constats (« Le maillon
mémoire décrivait un oligopole en oubliant un de ses membres ») : tiens ce niveau.

**Branche** : `claude/signal-investment-game-prompt-rvkkyo` — développe, commit, pousse
(`git push -u origin …`). **N'ouvre pas de pull request** sauf demande explicite.

---

## §20 — Les quatre lots (respecte l'ordre)

### Lot ① — « Le plateau » *(jouable et livrable seul)*
Le rendu isométrique : plateau 12×9, boîtes, tri de profondeur, caméra, échelle ×1/×2. **Toi seul
dans un bureau vide**, puis **deux recrues** (analyste, exécution) avec postes à acheter et à
poser. A\*, machine à états, marche. **La boîte de dialogue.** Le temps à deux horloges. Le
marché réel, la VL, les frais de gestion, **un** type d'arbitrage (la thèse). Le registre, la
sauvegarde, le chrome à cinq onglets. Tests 1-3, 5-7, 9, 11-12, 18, 22-23.
**Critère de fin de lot : on peut jouer trois ans sans s'ennuyer, et fermer l'onglet sans rien perdre.**

### Lot ② — « La maison »
**L'acte I complet** (§7.1) : le choix agrément / hébergement, le dossier AMF comme tutoriel,
l'adresse et son bail. Tous les rôles et le déblocage des métriques. Le mandat et la dérive de
style. Les meubles et l'étage supplémentaire. Les deux comptabilités, **les fonds propres
réglementaires** (§10.5) et la cessation de paiement. Collecte, rachats, **vente forcée**. Moral,
départs, débauchage. Les six familles d'arbitrages. Le comité d'investissement.
Tests 4, 8, 10, 19, 24-26.

### Lot ③ — « Les imprévus »
Le paquet complet, les atténuateurs, les garde-fous, les cartes de chance. Les paliers d'encours
et leurs complications. Le carnet et ses dix-huit concepts. Tests 13-14, 20-21.

### Lot ④ — « Le miroir »
L'assemblée annuelle avec les investisseurs qui entrent dans le bureau. La revue d'année et
l'attribution. **L'audit à 500 rejeux.** Le *block bootstrap* au-delà de la vingtième année.
Tests 15-17.

---

## §21 — Définition du « terminé » (à vérifier lot par lot)

- [ ] `python tests/test_maison.py` vert, **et** `PYTHONPATH=tests python3 tests/test_maison.py`
      vert (le runner n'a aucune bibliothèque tierce).
- [ ] `for f in tests/test_*.py; do python $f; done` : **toutes** les suites vertes, y compris
      `test_chrome.py` après l'ajout du cinquième onglet.
- [ ] Nav identique sur les cinq pages, « Portefeuille IA » toujours en dernier, bandeau de
      hauteur constante d'un onglet à l'autre.
- [ ] Une partie se joue **au clavier seul**, une autre **au doigt seul à 360 px**, une troisième
      **depuis le registre seul** — aménagement compris.
- [ ] `prefers-reduced-motion` activé : rien ne bouge, tout reste jouable.
- [ ] `maison.html#/p/<graine>` rejoue le même monde.
- [ ] 60 fps avec 25 personnages et un plateau plein ; rendu arrêté quand l'onglet est caché.
- [ ] Fermer l'onglet en pleine partie et revenir : **rien n'est perdu**. Une partie de 50 ans
      pèse moins de 1 Mo.
- [ ] Aucun `--green` / `--red` ailleurs que sur un chiffre de P&L ; la palette du décor est celle
      du §4.1 et pas une autre.
- [ ] Données au démarrage : **< 250 Ko**, mesuré, pas estimé. Aucun appel réseau autre que
      `jeu/marche.json` et la police. Rien ne quitte le navigateur.
- [ ] **Aucun texte du jeu n'attribue un fait à une entreprise réelle.**
- [ ] **Tout chiffre du §23.2 porte un `// approximation, non vérifiée` dans le code**, et aucun
      n'est énoncé en jeu comme un fait du métier.
- [ ] Les trois premières minutes se déroulent comme au §24.3, chronomètre en main.

---

## §22 — Hors périmètre, et décisions à confirmer

**Hors périmètre** (ne le fais pas, même si c'est tentant) : classement en ligne · comptes
utilisateurs · multijoueur · personnalisation d'avatar · vente à découvert, levier, dérivés ·
marchés privés · crypto · rotation de caméra · éclairage dynamique, cycle jour/nuit, météo ·
génération d'images de partage · lien avec le portefeuille IA réel · notifications · **sons**
(aucun : ce site se lit au bureau).

**Décisions à confirmer avant de coder** — propose ces valeurs par défaut, applique-les faute de
réponse, et **écris dans ta livraison ce que tu as tranché** :

| # | Question | Défaut proposé |
|---|---|---|
| 1 | Libellé de l'onglet : « La Maison » (le terme métier français, et l'objet qu'on voit) ou « Le Fonds » ? | **La Maison** |
| 2 | Dessin : géométrie procédurale ou planche de sprites pixel ? | **Géométrie procédurale** (§4) — pas d'illustrateur sur ce projet, et un jeu à moitié dessiné est pire qu'un jeu géométrique assumé |
| 3 | La palette du décor s'écarte de la règle « `--ac` seul » | **Oui, et seulement pour le décor** (§4.1). C'est la seule licence demandée sur le design system : à valider explicitement |
| 4 | Sociétés masquées, ou vrais noms ? | **Masquées**, révélées après coup — sinon celui qui connaît l'histoire de NVDA joue avec les réponses, et la règle du §2 ③ devient intenable |
| 5 | Capital de départ | **500 000 €** d'apport personnel + une première collecte de 2 à 5 M€ selon le mandat |
| 6 | Vitesse : un mois ≈ 40 s à ×1 | à régler à la main au lot ① : c'est le réglage qui décide si le jeu est vivant ou pesant |
| 7 | Nombre de titres dans le pack | **80** (~90 Ko), jusqu'à 120 si le poids le permet |
| 8 | Le lot ① démarre-t-il par l'acte I (agrément) ? | **Non** : le lot ① démarre **déjà hébergé**, pour qu'on soit dans le bureau en trente secondes. L'acte I complet arrive au lot ② et devient alors le vrai début de partie |
| 9 | Quand réalisme et plaisir s'opposent | **On garde le chiffre réel, on comprime le temps** (§24). Les trois mois d'instruction AMF durent une minute ; les 125 000 € en coûtent 125 000 |

**Une dernière chose.** Si tu découvres en chemin qu'une de ces contraintes rend le jeu mauvais,
**dis-le et argumente** au lieu de la contourner en silence. Ce dépôt documente ses erreurs et ses
angles morts dans son CHANGELOG ; un désaccord motivé y a plus de valeur qu'une livraison qui fait
comme si tout allait de soi.

---

## §23 — Le réalisme : ce qui est vérifié, ce qui ne l'est pas

**Ce dépôt distingue partout ce qu'il a mesuré de ce qu'il suppose.** Ce jeu doit faire pareil.
Les valeurs ci-dessous ont été vérifiées en août 2026 ; celles marquées ⚠️ ne l'ont pas été et
**doivent porter un commentaire `// approximation, non vérifiée` dans le code**, ne jamais être
présentées en jeu comme un fait, et être corrigées dès qu'une source sérieuse est trouvée.

### §23.1 — Vérifié

| Fait | Valeur | Source |
|---|---|---|
| Capital social minimum d'une SGP | **125 000 €**, libéré en numéraire | [Légifrance, RG AMF art. 317-2](https://www.legifrance.gouv.fr/codes/section_lc/JORFTEXT000000606599/LEGISCTA000027836030/2023-02-12) |
| Fonds propres exigés | le plus élevé de : **125 000 € + 0,02 % de l'encours au-delà de 250 M€** (plafond 10 M€), ou **¼ des frais généraux de l'exercice précédent** | [Guide AIFM — Société de gestion, AMF](https://www.amf-france.org/sites/institutionnel/files/contenu_simple/guide/guide_professionnel/Guide%20AIFM%20-%20Societe%20de%20gestion.pdf) · [Légifrance](https://www.legifrance.gouv.fr/codes/section_lc/JORFTEXT000000606599/LEGISCTA000027836030/2023-02-12) |
| Responsabilité civile professionnelle | RC pro **ou** fonds propres supplémentaires ≥ **0,01 % des encours** | Guide AIFM, AMF |
| Délai d'instruction de l'agrément | **3 mois** à compter du dépôt du dossier complet | [Procédure d'agrément SGP — instruction AMF DOC-2008-03](https://www.amf-france.org/sites/institutionnel/files/private/2024-04/doc-2008-03_vf17_lancement_rosa_mu.pdf) |
| Gérer pour compte de tiers **exige** l'agrément | oui ; pour compte propre, non | [AMF — Créer une société de gestion en France](https://www.amf-france.org/en/professionals/management-companies/my-relations-amf/create-investment-management-company-france) |
| L'hébergement de fonds chez une SGP tierce existe | pratique courante, sociétés dédiées | [Wagram Fund Services](https://www.wagram-fs.com/) |
| Nombre de SGP entrepreneuriales | **463** fin 2024 (−1 % sur un an) ; 106 filiales d'établissements de crédit (+4 %) | [Chiffres clés 2024 de la gestion d'actifs, AMF](https://www.amf-france.org/sites/institutionnel/files/private/2025-12/chiffres-cles-2024-gestion-actifs.pdf) |
| Marge d'exploitation du secteur | **21,2 %** en 2024 | Chiffres clés 2024, AMF |
| Terminal Bloomberg | **31 980 $/an/poste** (2025) ; ~28 320 $ en multi-poste, bail de 2 ans | [Bloomberg Terminal Pricing 2026](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/) |
| LSEG Workspace (ex-Refinitiv) | ~**22 000 $/an** ; version réduite dès ~3 600 $ | [Comparatif terminaux financiers](https://godeldiscount.com/blog/financial-terminal-pricing-comparison) |
| Loyer de bureaux — Paris QCA | **~1 080 €/m²/an**, prime 1 230-1 250 | [Cushman & Wakefield, valeurs locatives 2025-2026](https://immobilier.cushmanwakefield.fr/nos-conseils/etude/valeurs-locatives-2025-bureaux-paris-idf-metro-rer) |
| Loyer — 1ʳᵉ couronne / 2ᵉ couronne | **~450** / **~250 €/m²/an** | idem |
| Charges patronales, cadre | **40 à 45 %** du brut hors allègements | [L'Expert-Comptable — charges patronales](https://www.l-expert-comptable.com/a/37341-les-charges-sociales-patronales.html) |
| Salaire — analyste financier | ~**78 k€** brut/an en moyenne ; 3 800 € (débutant) à 8 200 €/mois (senior) | [Estimsalaire — analyste financier](https://estimsalaire.com/metiers/finance/analyste-financier.html) |
| Salaire — gérant de portefeuille | **45 k€ à 120 k€**/an selon expérience et taille | [Journal du Net — portfolio manager](https://www.journaldunet.com/business/salaire/portfolio-manager/salaire-01184) |

### §23.2 — ⚠️ Non vérifié — à marquer comme approximation dans le code

| Fait supposé | Valeur employée | Ce qu'il faudrait |
|---|---|---|
| Frais de dépositaire | 2 à 5 bps de l'encours, avec un minimum forfaitaire | un barème réel ; les prospectus déposés à l'AMF (base GECO) les publient |
| Valorisateur / administration de fonds | 2 à 4 bps, minimum forfaitaire | idem |
| Commissaire aux comptes du fonds | 8 000 à 15 000 €/an | un barème réel |
| Contribution annuelle AMF | proportionnelle à l'encours, avec un plancher | le barème officiel en vigueur |
| Fréquence des contrôles SPOT / inspections | conditionnée à l'ancienneté et à l'encours | les rapports d'activité de l'AMF donnent le nombre de contrôles par an |
| Part des SGP déficitaires | non trouvée | elle figure dans les Chiffres clés de l'AMF, dont le PDF n'était pas accessible depuis cet environnement |
| Prix du mobilier de bureau | 1 200 € le poste, 3 500 € la salle de réunion | sans importance pour le réalisme ; à garder tel quel |

**Règle générale :** un chiffre non vérifié n'a pas le droit d'apparaître dans une phrase du jeu
qui l'énonce comme un fait du métier. Il peut gouverner l'équilibrage ; il ne peut pas enseigner.

### §23.3 — La tension que ces chiffres créent, et comment la tenir

**Le réalisme financier rend le début de partie très pauvre**, et il faut le savoir avant de
coder. Un fonds de 5 M€ rapporte 100 000 € par an : **moins qu'un salaire chargé**. Les vraies
boutiques vivent deux à quatre ans sur leur capital avant le point mort. Un jeu qui simule cela
au rythme réel est injouable.

**Trois leviers, dans cet ordre, et aucun autre :**
1. **Comprimer le temps, jamais les montants** (§24). Les années maigres passent en quelques
   minutes ; leur douleur reste chiffrée juste.
2. **Ouvrir des revenus précoces qui existent vraiment** : mandats de gestion pour quelques
   clients privés, conseil, gestion sous délégation. C'est ce que font les vraies boutiques, et
   ça donne au joueur de quoi tenir sans qu'on lui offre d'argent gratuit.
3. **L'hébergement** (§7.1) comme voie « facile » assumée : moins de capital immobilisé, mise en
   marché rapide, au prix d'une rétrocession permanente.

**Ce qu'il ne faut pas faire :** gonfler les frais de gestion, réduire les salaires, inventer une
collecte initiale généreuse. Ce serait échanger la seule chose que ce jeu a à offrir — **des
ordres de grandeur transposables** — contre un confort qu'on peut obtenir autrement.

---

## §24 — Le contrat de plaisir

Le réalisme sans plaisir donne un tableur ; le plaisir sans réalisme donne un jeu de plus. Voici
la règle d'arbitrage, et les trois boucles à tenir.

### §24.1 — La règle
> **Quand réalisme et plaisir s'opposent, on garde le chiffre et on comprime le temps.**

Les 125 000 € coûtent 125 000 €. Les trois mois d'instruction AMF durent **une minute**. Le point
mort arrive à 25 M€ d'encours pour de vrai, mais les trois années nécessaires passent en **vingt
minutes**. On ne ment jamais sur un montant, on ment tout le temps sur la durée — et c'est
exactement ce que fait n'importe quel bon jeu de gestion.

### §24.2 — Les trois boucles
- **30 secondes** — *je regarde et je comprends.* Quelqu'un traverse la pièce, un arc de
  progression se remplit, une feuille monte l'escalier, un chiffre bouge dans le panneau.
  **Aucune décision requise.** C'est le fond sonore visuel du jeu, et il doit être agréable à
  regarder sans rien faire.
- **5 minutes** — *je décide.* Une thèse arrive, une objection la contredit, je tranche dans la
  boîte de dialogue ; j'achète un poste, j'embauche, je pose un meuble. **Il doit se passer
  quelque chose qui demande un choix au moins une fois toutes les deux minutes**, sinon on
  décroche.
- **1 heure** — *j'ai construit quelque chose.* Un étage de plus, une personne de plus, un palier
  franchi, une assemblée annuelle traversée, un concept compris qu'on n'avait pas au début.

### §24.3 — Les trois premières minutes (à écrire au mot près, elles décident de tout)
1. **0 s** — on est déjà dans le bureau, pas dans un menu. Un plateau presque vide, une personne :
   toi. Le curseur clignote dans la boîte de dialogue.
2. **20 s** — la première réplique donne **une chose à faire**, pas un cours : *« On a 500 000 €
   et une pièce vide. Il nous faut quelqu'un qui sache lire un bilan. »*
3. **60 s** — on achète un poste, on le pose, quelqu'un arrive **et traverse la pièce pour s'y
   asseoir.** Ce moment-là est le crochet : la dépense a produit un corps qui bouge.
4. **2 min** — la première note de recherche arrive, la première thèse, le premier choix.
5. **3 min** — la première ligne en portefeuille, le premier mois qui passe, le premier chiffre
   qui bouge tout seul.

**Aucun texte pédagogique avant la cinquième minute.** Le carnet se remplit en silence ; on le
lit quand on veut.

### §24.4 — Les six règles anti-ennui
1. **Rien n'attend le joueur sans le lui dire.** Une décision en attente met le jeu en pause et
   la personne concernée est visible à l'écran.
2. **Jamais deux minutes sans qu'il se passe quelque chose** — même minuscule : une réplique à la
   machine à café, un cours qui décroche, une candidature spontanée.
3. **Toute dépense produit un effet visible dans les cinq secondes.** On achète un poste : il
   apparaît. On embauche : quelqu'un entre par la porte. Un chiffre qui bouge tout seul ne
   récompense personne.
4. **Aucun écran ne dépasse trois lignes** avant qu'on puisse agir.
5. **Le joueur peut toujours dire « je ne fais rien ».** C'est une option, elle est souvent bonne,
   et le jeu ne la punit jamais par principe.
6. **L'échec est court et relançable.** La cessation de paiement (§10.4) tient en un écran, garde
   le carnet, et propose de rouvrir une maison en gardant ce qu'on a compris.

### §24.5 — Ce qui doit faire sourire
Le jeu est sérieux sur les chiffres et **vivant sur les gens**. Les répliques peuvent avoir de
l'humeur, du caractère, une pointe de sécheresse — un analyste qui répond « je vous l'avais mis
en gras » quand vous rouvrez un dossier qu'il avait signalé six mois plus tôt vaut mieux que trois
paragraphes de pédagogie. **Le fond ne blague jamais, les gens si.** C'est très exactement la
consigne de ton du dépôt (`GUIDE_redaction_analyses.md` : « plume vivante avec une pointe d'esprit
pince-sans-rire occasionnelle »), appliquée à des personnages.

---

## §25 — Le MVP : le périmètre exact de la première mise en production

Le MVP est **le lot ① tel quel**, avec les précisions suivantes — figées ici pour qu'aucune ne
se décide en silence pendant l'implémentation.

### §25.1 — Ce qui est DANS le MVP
- Le plateau 8×6 isométrique, les meubles (poste, machine à café, plante), le mode plan avec
  contrôle de connexité, l'échelle ×1/×2, le pan tactile.
- Toi + recrutements **analyste junior / analyste confirmé / gérant d'exécution**, avec la chaîne
  complète : trésorerie → poste posé → candidature → arrivée par la porte.
- Machine à états + A\* + marche, boîte de dialogue lettre à lettre, clic sur n'importe qui.
- Le temps à deux horloges (jour ≈ 2 s à ×1, mois = 20 jours ouvrés), vitesses ×1/×2/×4, pause
  auto quand une décision attend.
- Le marché réel (`jeu/marche.json`), la VL, les frais de gestion 2 % prélevés au prorata
  mensuel, l'exécution 7,5/30 bps, le refus < 50 €.
- **Une seule famille d'arbitrage : la thèse** (entrée ET allègement/sortie d'une ligne),
  fondée UNIQUEMENT sur des faits de prix + le secteur — jamais un fondamental inventé (§2 ③).
- Les noms masqués (liste fixe), la révélation d'identité à la vente (> 1 an) et au bilan de
  janvier.
- Un bilan de janvier minimal (dialogue de l'hôte : brut / net / écart de frais, P&L société).
- Le panneau (Fonds · Société · Équipe · Registre · Carnet), le carnet avec ~6 concepts
  (`valeur liquidative`, `frais et traînée`, `écart brut/net`, `taille de position`,
  `achat vs abonnement`, `point mort`).
- Sauvegarde localStorage versionnée + export JSON + effacer ; reprise exacte au rechargement.
- Chrome 5 onglets, tests du lot ①, accessibilité §15 (registre jouable, clavier, reduced-motion).

### §25.2 — Les simplifications ASSUMÉES du MVP (chacune commentée dans le code)
- **Démarrage hébergé d'office** (décision #8) : pas d'acte I, rétrocession **30 % ⚠️
  approximation** sur les frais encaissés, pas de fonds propres réglementaires. Adresse fixe
  1ʳᵉ couronne (450 €/m²/an sur 96 m² = 3 600 €/mois).
- **Flux investisseurs simplifiés** : collecte/rachats mensuels = fonction bornée de la
  performance décalée de 2 trimestres, ⚠️ approximation ; la vraie mécanique arrive au lot ②.
- **Abonnement de données au niveau société** (base 280 € / LSEG 1 700 € / Bloomberg 2 500 €
  par mois), pas encore par poste.
- **Au-delà du pack (240 mois) : rebouclage modulo** sur l'historique, commenté comme provisoire
  — le block bootstrap honnête est au lot ④.
- Moral affiché mais sans départ ; pas de débauchage, pas d'imprévus (lot ③), pas d'audit (lot ④).

### §25.3 — Mise en production
Le MVP se livre sur la branche de travail, tests verts, puis passe en prod par **pull request
vers `main`** (GitHub Pages sert `main`). La PR ne s'ouvre que sur demande explicite du
propriétaire — c'est sa décision de mise en ligne, pas celle de l'agent.
