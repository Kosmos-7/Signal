# Prompt — « La Maison » : simulation isométrique d'une société de gestion, pour Signal

> **Comment s'en servir.** Ce fichier est un prompt à coller tel quel dans Claude Code, à la
> racine du dépôt Signal. Tout ce qui suit s'adresse à l'agent qui va écrire le code.
> **§0–§4** posent l'intention, l'objet visuel et la direction artistique · **§5–§12** décrivent
> le jeu mécanique par mécanique · **§13–§18** sont des contraintes dures (le code sera refusé
> s'il les viole) · **§19–§22** disent quand c'est fini.
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

**« La Maison »** : un bureau isométrique qu'on remplit tuile par tuile, des gens qu'on embauche
quand la trésorerie le permet et à qui on peut parler, un fonds qui grandit, et **une partie qui
ne se termine jamais** — sauf par la faillite, qui est toujours possible.

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
- **Tuile de 32 × 16 px** (à `dpr` 1). Personnage **~26 px de haut**, soit un peu plus d'une
  tuile et demie : assez pour lire une posture, assez petit pour en tenir vingt à l'écran.
- **Plateau de départ : 12 × 9 tuiles.** Extensible jusqu'à **20 × 14** en louant de la surface.
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

| Objet | Coût | Récurrent | Ce qu'il apporte |
|---|---|---|---|
| **Surface** | — | **18 €/tuile/mois** | la place. Le loyer est le coût fixe qui tue les sociétés de gestion en bas de cycle |
| **Poste de travail** | 1 200 € | — | **obligatoire par personne employée** |
| **Terminal de données** | 0 € | **900 €/mois** | +1 note de recherche par mois et par analyste. **Un abonnement, pas un achat** — c'est là qu'on découvre la différence |
| **Salle de réunion** (4 tuiles + table) | 3 500 € | — | débloque le **comité d'investissement** (§8.3) |
| **Machine à café** | 400 € | 60 €/mois | +moral, et le lieu où circulent les rumeurs |
| **Armoire d'archives** | 800 € | — | divise par deux le coût d'une inspection |
| **Baie serveur** | 6 000 € | 200 €/mois | réduit fortement le risque d'incident informatique (§9) |
| **Étage supplémentaire** | 15 000 € | loyer du plateau | 12 × 9 tuiles de plus |

**À écrire dans le carnet la première fois que le joueur signe un abonnement :** achat
(immobilisation) contre abonnement (charge récurrente), et pourquoi le second est plus dangereux
quand les revenus baissent.

**L'aménagement se fait en pause** (mode « plan »), à la souris ou au clavier, avec aperçu de la
tuile, rotation du meuble sur `R`, et **remboursement à 50 %** à la revente. Un meuble ne peut
pas boucher un passage : le moteur refuse la pose si elle enferme un poste (vérification de
connexité, testée).

---

## §6 — Les gens : rôles, dialogue, et le chiffre qu'ils font exister

| Recrue | Salaire indicatif | Ce qu'elle produit | Ce qu'elle **fait apparaître à l'écran** |
|---|---|---|---|
| **Analyste** | 4 500 €/mois | 1 à 3 notes/mois selon compétence et terminal | la fiche société : qualité, valorisation, thèse. **Sans analyste, tu n'as que le prix.** |
| **Gérant d'exécution** | 5 500 €/mois | passe les ordres | coût d'exécution de **30 bps → 7,5 bps** (`config.py`) ; le carnet d'ordres |
| **Risk manager** | 5 000 €/mois | contrôle a posteriori | volatilité, perte maximale, exposition sectorielle, poids par ligne |
| **RCCI (conformité)** | 4 000 €/mois | contrôle du mandat | l'alerte de dérive **avant** la faute ; divise par 4 le coût d'une inspection |
| **Relation investisseurs** | 4 500 € + variable | reporting, collecte | +40 % de collecte à performance égale ; **sans elle, le reporting te coûte une semaine d'arbitrages par trimestre** |
| **Back-office** | 3 500 €/mois | règlement-livraison | supprime les erreurs de règlement (sinon 0,5 %/mois d'incident coûteux) |
| **Quant** | 7 000 €/mois | attribution, audit | **la décomposition marché / secteur / sélection**, et l'audit du §11.3 |
| **Assistant·e** | 2 800 €/mois | logistique | +moral collectif, absorbe une partie des imprévus administratifs |

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

## §7 — Le mandat : ce que le joueur écrit, et qui le tient

Avant le premier mois, cinq clauses choisies dans des listes (pas de champ libre) :

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

| Encours | Ce qui s'ouvre | Ce qui se complique |
|---|---|---|
| **5 M€** | frais de gestion viables, 2ᵉ recrutement | le point mort de la société |
| **25 M€** | clients institutionnels, 2ᵉ étage | reporting exigé, dépositaire plus cher |
| **100 M€** | notoriété, recrutements de haut niveau | **capacité** : l'impact de marché devient sensible |
| **500 M€** | pouvoir de négociation | contraintes réglementaires, inspections plus probables |
| **1 Md€** | ta stratégie ne passe plus à cette taille | **il faut choisir : fermer le fonds, ou accepter de moins bien gérer** |

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
Tous les rôles et le déblocage des métriques. Le mandat et la dérive de style. Les meubles et
l'étage supplémentaire. Les deux comptabilités et la cessation de paiement. Collecte, rachats,
**vente forcée**. Moral, départs, débauchage. Les six familles d'arbitrages. Le comité
d'investissement. Tests 4, 8, 10, 19.

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

**Une dernière chose.** Si tu découvres en chemin qu'une de ces contraintes rend le jeu mauvais,
**dis-le et argumente** au lieu de la contourner en silence. Ce dépôt documente ses erreurs et ses
angles morts dans son CHANGELOG ; un désaccord motivé y a plus de valeur qu'une livraison qui fait
comme si tout allait de soi.
