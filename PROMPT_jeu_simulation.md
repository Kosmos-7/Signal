# Prompt — « La Maison » : simuler la création et la gestion d'un fonds, pour Signal

> **Comment s'en servir.** Ce fichier est un prompt à coller tel quel dans Claude Code, à la
> racine du dépôt Signal. Tout ce qui suit s'adresse à l'agent qui va écrire le code.
> **§0–§3** posent l'intention et l'objet visuel · **§4–§10** décrivent le jeu, mécanique par
> mécanique · **§11–§16** sont des contraintes dures (le code sera refusé s'il les viole) ·
> **§17–§20** disent quand c'est fini.
>
> ⚠️ **Ce jeu est un gros morceau** — compte 3 000 à 5 000 lignes au total. Il est découpé en
> **trois lots** (§18) dont **le premier est jouable seul**. Ne commence pas par le milieu.

---

## §0 — Rôle, et ce qu'il faut lire avant d'écrire une ligne

Tu travailles sur **Signal** (https://kosmos-7.github.io/Signal/) : site statique sur GitHub
Pages, screener d'actions, portefeuille fictif piloté par IA, page pédagogique. Posture du
projet, à ne jamais trahir : **neutre, aucune prétention d'alpha**, méthodes publiques
appliquées avec discipline, **erreurs publiées**.

Tu ajoutes un **cinquième onglet** : un simulateur où l'on **fonde une société de gestion**,
qu'on **voit en coupe**, qu'on peuple de petits bonhommes qui travaillent, se déplacent,
proposent, objectent, et posent des questions auxquelles il faut répondre.

| Fichier | Ce que tu y cherches |
|---|---|
| `README.md` | architecture, workflows, posture |
| `signal.css` | le design system entier — tokens, chrome, composants |
| `actualites.html` (20 Ko) | le gabarit d'une page : `<head>`, chrome, footer, script inline |
| `tests/test_chrome.py` | **les règles que ta page devra passer** — lis-le en entier |
| `tests/_sans_bibliotheques.py` | pourquoi un test vert en local peut être rouge en CI |
| `config.py` | frais de transaction (7,5 bps), PFU (31,4 %), seuil d'ordre (50 €) |
| `screener.py` §« PAYLOAD GRAPHIQUE » (~l.362) | format exact de `charts/<TICKER>.json` |
| `universe.json` | `stocks` : 133 titres avec `nom`, `secteur`, `devise` — ta source d'identité |
| `portfolio.html` | le vocabulaire déjà employé pour un portefeuille fictif |
| `.claude/skills/portfolio-analyst/` | biais, discipline de vente, frameworks — le fond pédagogique |
| `CHANGELOG.md` (100 premières lignes) | la **voix** du projet — tu écriras dedans |

---

## §1 — Mission en une phrase

**« La Maison »** : on fonde une société de gestion, on l'installe dans un immeuble qu'on voit
**en coupe**, on l'agrandit, on l'équipe de gens qui produisent le travail — et on découvre en
dix ans que **gérer l'argent des autres est deux métiers à la fois**, qui ne tirent pas dans le
même sens.

---

## §2 — La tension centrale (c'est le sujet du jeu, pas un détail d'équilibrage)

Le joueur tient **deux comptabilités séparées**, affichées côte à côte en permanence :

| **Le fonds** (l'argent des clients) | **La société de gestion** (ton argent) |
|---|---|
| valeur liquidative, performance nette, drawdown | frais encaissés − salaires − loyer − données − audit |
| ce que gagnent les investisseurs | ce que tu gagnes, toi |

Et elles s'opposent. Doubler l'encours double tes revenus **et** dégrade tes rendements (tu ne
peux plus entrer et sortir sans bouger les prix, tu dois acheter des lignes que tu aimes moins).
Un an de mauvaise performance ne te ruine pas — mais une vague de rachats, oui, parce que tes
charges sont fixes et tes revenus proportionnels à un encours qui fond.

**On peut donc perdre de deux façons, et il faut les deux à l'écran :** le fonds peut être bon
pendant que la société fait faillite, et la société peut prospérer sur un fonds médiocre. La
seconde est le cas le plus fréquent dans la vraie vie ; le jeu doit le rendre atteignable, et
le débrief doit le nommer. **C'est là que ce jeu appartient à Signal et à aucun autre site.**

**Ce n'est pas un jeu où l'on gagne.** Il n'y a pas de score final unique, pas d'étoiles, pas
de « rang de gérant ». Il y a un bilan à dix ans, à plusieurs colonnes, et une distribution qui
te dit ce que le hasard seul aurait produit à ta place (§10.4).

---

## §3 — L'objet visuel : la maison en coupe

C'est la partie que tu ne dois pas rendre générique. Signal n'a pas besoin d'un tableau de bord
de plus. **Toute la page est un immeuble vu en coupe**, dessiné au trait, et tout se passe
dedans.

### §3.1 — Le dessin

- **Un plan de coupe en fil de fer**, comme un plan d'architecte ou un schéma de HUD : traits
  fins `--ac` et `--line`, aucun aplat, aucune texture, aucun pixel-art coloré. Les rayures de
  balayage de `.scan` passent par-dessus. Le résultat doit ressembler à **une page de Signal qui
  aurait pris du volume**, jamais à un jeu mobile posé sur un site de finance.
- **`<canvas>` 2D**, rendu à la main. Pas de bibliothèque, pas de moteur de jeu, pas de sprites
  bitmap. Les meubles et les gens sont des tracés (`stroke`), donc ils héritent de la couleur —
  exactement le raisonnement déjà écrit dans `signal.css` pour les icônes de nav.
- **Résolution des figures : ~16 px de haut.** Une tête (cercle r≈2,5), un corps, deux jambes,
  deux bras. L'animation de marche est un balancement, pas un cycle d'images. C'est assez pour
  qu'on lise « quelqu'un traverse le plateau », et c'est tout ce qu'il faut.

### §3.2 — Les étages, qui sont la progression

L'immeuble **pousse vers le haut** au fur et à mesure. Chaque étage ouvert coûte un loyer
mensuel et abrite une fonction :

```
   ┌──────────────────────────────┐
   │  R+4  Ton bureau             │  toi · le mandat · les arbitrages
   ├──────────────────────────────┤
   │  R+3  Risque & conformité    │  débloque : volatilité, drawdown, contrôle du mandat
   ├──────────────────────────────┤
   │  R+2  La table               │  exécution des ordres · le carnet
   ├──────────────────────────────┤
   │  R+1  La recherche           │  les notes sur les sociétés
   ├──────────────────────────────┤
   │  RDC  Accueil & relation LP  │  souscriptions, rachats, reporting
   └──────────────────────────────┘
      sous-sol  Back-office        règlement-livraison, réconciliation
```

Au démarrage : **le RDC et rien d'autre**, deux chaises, une plante, et toi. Un immeuble
presque vide qui se remplit est la meilleure barre de progression jamais inventée — n'en ajoute
pas une deuxième.

### §3.3 — Ce qui bouge

- Chaque bonhomme suit une **machine à états** : `au poste` · `en marche vers X` ·
  `en réunion` · `à la machine à café` · `t'attend devant ton bureau` · `absent`.
- Les déplacements suivent des **rails fixes** (couloirs + une cage d'escalier), avec des
  points de passage. **Pas de recherche de chemin** : c'est un immeuble, pas un labyrinthe.
- Un travail en cours = **un petit arc de progression** au-dessus du poste (le vocabulaire de
  `.ring`, en miniature). Un travail fini = **une feuille qui monte l'escalier** jusqu'à ton
  bureau. On doit pouvoir comprendre l'état de la boîte **sans lire un seul chiffre**.
- Quand quelqu'un a une question pour toi, il **se lève, traverse, monte, et attend**. Une
  bulle discrète au-dessus de la tête. Tant que tu ne réponds pas, **il attend et ne produit
  rien** — c'est le coût de l'indécision, et il est visible, pas écrit.

### §3.4 — Le panneau

À droite (en bas sur mobile), **un seul panneau contextuel** en typo Signal :
le mois en cours, les deux comptabilités du §2, et le détail de ce qu'on a cliqué (une personne,
un poste, une ligne du portefeuille, un événement). Rien d'autre. **Aucune fenêtre modale**
sauf pour un arbitrage qui exige une réponse — et alors elle est sobre, centrée, et ne recouvre
jamais l'immeuble en entier.

### §3.5 — Le temps

- **1 tic = 1 mois** (c'est le pas de la donnée réelle, cf. §9). Vitesses : **pause**, **×1**
  (1 mois ≈ 2 s), **×3**. Barre d'espace = pause. Le jeu se met **automatiquement en pause**
  quand quelqu'un attend une décision depuis plus d'un mois.
- **Trimestre** = reporting aux investisseurs. **Année** = cristallisation des frais de
  performance, entretiens, revalorisation des salaires, bilan de la société.
- Une partie = **120 mois (10 ans)**, soit ~25 à 40 minutes avec les pauses.

---

## §4 — Les bonhommes : chacun débloque un métier ET un chiffre

**La règle de conception la plus importante du jeu : un chiffre n'existe à l'écran que si
quelqu'un, dans la maison, le calcule.** Tant que tu n'as pas de risk manager, tu ne sais pas
quelle est ta volatilité — pas « elle est masquée », **elle n'est pas là**. C'est la meilleure
leçon d'organisation qu'un jeu de gestion puisse donner, et c'est ta mécanique de progression.

| Recrue | Salaire indicatif | Ce qu'elle produit | Ce qu'elle **débloque à l'écran** |
|---|---|---|---|
| **Analyste** | 4 500 €/mois | 1 à 3 notes par mois selon compétence | la fiche société : qualité, valorisation, thèse. **Sans analyste, tu n'as que le prix.** |
| **Gérant d'exécution** | 5 500 €/mois | passe les ordres | le coût d'exécution tombe de **30 bps à 7,5 bps** (`config.py`) ; le carnet d'ordres |
| **Risk manager** | 5 000 €/mois | contrôle a posteriori | volatilité, drawdown, exposition sectorielle, poids max |
| **RCCI (conformité)** | 4 000 €/mois | contrôle du mandat | l'alerte de dérive **avant** la faute ; divise par 4 le coût d'une inspection |
| **Relation investisseurs** | 4 500 € + variable | reporting, collecte | +40 % de collecte à performance égale ; **sans elle, rédiger le reporting te coûte un mois d'arbitrages** |
| **Back-office** | 3 500 €/mois | règlement-livraison | supprime les erreurs de règlement (sinon 0,5 %/mois de chance d'un incident coûteux) |
| **Quant** (tardif) | 7 000 €/mois | attribution de performance | **la décomposition bêta / secteur / sélection** — cf. §10.3 |

Chaque personne porte : **compétence (1-5)**, **moral (0-100)**, **ancienneté**, **salaire**.

- Le moral baisse si on la surcharge, si on la contredit systématiquement, si les augmentations
  ne viennent pas, ou si le fonds va mal et qu'on ne lui dit rien.
- Sous 25 de moral, elle peut **partir** — et emporter la métrique qu'elle débloquait. Voir
  disparaître son propre drawdown de l'écran parce que le risk manager a démissionné est une
  leçon que personne n'oublie.
- Un concurrent peut **débaucher** un bon élément : tu surenchéris ou tu le laisses partir.

**Recruter n'est pas gratuit, et le jeu ne le laisse pas croire :** un mois de recherche, une
prime d'arrivée, trois mois avant la pleine productivité. Embaucher au pire moment (après une
grosse collecte, juste avant un retournement) est l'erreur classique du métier, et le jeu doit
permettre de la commettre.

---

## §5 — La boucle : ce que le joueur fait vraiment

Chaque mois, dans l'ordre où ça arrive à l'écran :

1. **Le marché bouge** (données réelles, §9). Le portefeuille se revalorise. La ligne de vie du
   fonds avance d'un pas.
2. **Les gens produisent** : notes de recherche, contrôles de risque, reporting, exécution.
3. **Des gens montent te voir** avec des propositions, des objections, des questions (§6).
4. **Tu arbitres** : accepter/refuser une thèse, dimensionner une ligne, alléger, recruter,
   licencier, ouvrir un étage, changer la grille de frais, accepter ou refuser de l'argent.
5. **Les flux tombent** : souscriptions, rachats, frais prélevés, salaires payés.
6. **Trimestre / année** : reporting, cristallisation, entretiens, bilan.

**Ce que le joueur ne fait jamais** : cliquer sur des boutons « acheter » toute la journée. Le
jeu ne récompense pas la fréquence. Un mois où l'on ne fait rien est un mois **valide et
souvent bon**, et le débrief final doit pouvoir le dire.

---

## §6 — Le mandat, et les questions qu'on te pose

### §6.1 — Le mandat, écrit à la création

Avant le premier mois, le joueur rédige son mandat en **cinq clauses**, choisies dans des listes
(pas de champ libre) :

1. **Univers** — Europe / États-Unis / Monde développé / un thème du site (`universe.json` en
   propose déjà cinq, réutilise-les).
2. **Concentration** — nombre maximum de lignes (8 / 15 / 30) et poids maximum par ligne
   (5 / 10 / 20 %).
3. **Style** — qualité-croissance / décote / momentum / mixte. Le style **filtre les thèses**
   que tes analystes te proposent : un fonds décote ne verra pas passer les mêmes dossiers.
4. **Liquidité** — préavis de rachat (aucun / 30 jours / 90 jours) et poche de trésorerie
   minimale (0 / 5 / 10 %). **Ce choix décide de ta survie en cas de panique** ; le joueur ne
   le comprendra qu'au premier choc, et c'est exactement le but.
5. **Grille de frais** — gestion 0 / 1 / 1,5 / 2 % et performance 0 / 10 / 20 % avec
   *high-water mark*. Une grille chère finance la maison mais freine la collecte et pèse sur la
   performance nette affichée. Arbitrage central, posé dès la première minute.

**Le mandat te contraint et te protège.** Les investisseurs pardonnent une mauvaise année si tu
es resté fidèle à ce qui est écrit ; ils partent si tu as dérivé, **même en gagnant** — c'est
la *style drift*, et c'est une mécanique de premier plan, pas une note de bas de page.
Changer le mandat en cours de route est possible, coûte de la confiance, et doit être justifié
devant les LP au trimestre suivant.

### §6.2 — Les questions

Elles arrivent **portées par quelqu'un**, jamais par une notification anonyme. Six familles :

| Famille | Qui | Exemple | Ce qu'on apprend |
|---|---|---|---|
| **Thèse** | analyste | « J'ai une ligne pour vous : marge à 34 %, dette nulle, le titre a baissé de 22 % sur un trimestre. On entre à combien ? » | dimensionner, prix ≠ valeur |
| **Objection** | risk manager | « Trois lignes sur quatre sont dans le même secteur. Le mandat dit 25 %, on est à 41 %. » | corrélation, concentration |
| **Mandat** | RCCI | « Ce dossier est hors univers. On l'écarte, ou on modifie le mandat ? » | dérive de style, discipline |
| **Client** | RI | « Un investisseur menace de sortir : il ne comprend pas pourquoi on a raté la hausse. » | pression court terme, horizon |
| **Équipe** | n'importe qui | « On me propose 30 % de plus ailleurs. » | coût du capital humain |
| **Agence** | toi-même | « Un institutionnel apporte 50 M€. Notre stratégie ne passe pas cette taille. » | capacité, conflit d'intérêt |

**Règles de rédaction des arbitrages, non négociables :**
- **2 à 4 options, aucune évidente.** Si une option est objectivement meilleure, ce n'est pas un
  arbitrage, c'est un quiz — supprime-la ou dégrade-la.
- Chaque option affiche **son raisonnement**, pas son résultat. Jamais « +5 % de performance ».
- **L'effet est en partie différé et bruité** : une bonne décision peut mal finir, et le jeu doit
  parfois le faire. C'est le cœur de la pédagogie (Mauboussin, base rates) et le débrief final
  l'expliquera (§10.4). **Ne triche pas dans l'autre sens non plus : ne fais pas systématiquement
  échouer le joueur pour donner une leçon.** Le hasard est un vrai hasard, à graine reproductible.
- Chaque option porte une **étiquette de concept** (`concentration`, `liquidité`, `frais`,
  `dérive`, `capacité`, `biais_disposition`…) qui alimente le bilan.

---

## §7 — Les événements

Trois portées, et **une interdiction absolue**.

- **Portée marché** — les vrais chocs, dérivés **des données réelles** : « le marché a perdu
  14 % en un mois », « ton secteur dominant a doublé en un an ». On **constate** ce que la série
  a fait ; on ne l'invente pas.
- **Portée fonds / société** — rachats en chaîne, gros investisseur qui arrive, inspection AMF,
  incident de règlement, augmentation de loyer, démission, débauchage, procès d'un LP mécontent.
  Générés par le moteur, à graine reproductible, avec des conditions de déclenchement lisibles
  (ex. : une inspection devient possible après 3 ans d'existence ou 50 M€ d'encours).
- **Portée ligne** — **uniquement des faits calculés** à partir de la série : variation, perte
  maximale, poids devenu excessif, ligne devenue illiquide au vu de sa taille.

🚫 **INTERDIT : fabriquer une actualité d'entreprise.** Les sociétés du jeu portent des **noms
masqués** (§9.3) mais leurs **cours sont réels**, et l'identité est révélée à la fin. Inventer
« cette société est visée par une enquête » reviendrait donc à coller, en différé, une fausse
nouvelle sur une entreprise cotée réelle. **Aucun texte d'événement ne décrit ce qu'a fait une
société : il ne décrit que ce que son cours a fait.** Un test vérifie cette règle (§16).

---

## §8 — Apprendre, progressivement

Le jeu ne fait **jamais** de leçon avant l'expérience. L'ordre est : *ça t'arrive → tu réagis →
on nomme ce qui vient de se passer → tu peux aller lire*.

- **Le carnet** (un onglet du panneau) se remplit tout seul : chaque concept **rencontré** y
  entre, daté, avec **la situation exacte de TA partie** qui l'a déclenché, une explication de
  cinq lignes, et un lien vers la section correspondante d'`apprendre.html`
  (ancres `#s1`…`#s12` — **vérifie l'ancre, ne la devine pas**).
- Concepts à couvrir sur une partie complète, dans cet ordre d'apparition naturel :
  `valeur liquidative` · `frais de gestion et effet de traînée` · `high-water mark` ·
  `écart brut/net` · `diversification et corrélation` · `taille de position` ·
  `drawdown` · `volatilité` · `illiquidité et rachats` · `vente forcée` ·
  `dérive de style` · `bêta vs alpha` · `capacité d'une stratégie` ·
  `conflit d'intérêt` · `biais de disposition` · `chance vs compétence`.
- **Aucun texte pédagogique ne bloque le jeu.** Il s'ajoute au carnet, une pastille signale
  qu'il y a du neuf, et c'est tout.

---

## §9 — Le modèle financier (à écrire juste, et à tester)

### §9.1 — La valeur liquidative
Parts de 100 € à l'ouverture. VL = (valeur des lignes + trésorerie − dettes) ÷ nombre de parts.
Souscriptions et rachats se font **à la VL du mois**, en créant/annulant des parts — jamais en
diluant les porteurs existants. **La performance affichée est celle de la part, pas de l'encours** :
un fonds dont l'encours triple pendant que la part baisse est une situation banale, et le jeu
doit pouvoir la produire.

### §9.2 — Les frais
- **Gestion** : taux annuel choisi, prélevé **mensuellement au prorata** sur l'encours moyen.
  Il sort du fonds et entre dans la société : la même ligne, deux signes.
- **Performance** : taux choisi, sur la hausse de la VL **au-dessus du plus haut historique**
  (*high-water mark*), **cristallisée en fin d'année**. Après une perte, aucun frais de
  performance tant que le plus haut n'est pas repassé. À implémenter exactement — c'est le point
  où toutes les implémentations naïves se trompent, et c'est un test dédié.
- **Transaction** : 7,5 bps par sens avec un gérant d'exécution, **30 bps sans** (§4).
  Ordre refusé sous 50 € (`MIN_TRADE_EUR`).
- **Impact de marché** : au-delà de 2 % de l'encours sur une ligne peu liquide, ajoute un coût
  croissant. C'est ce qui rend la capacité (§6.2 « agence ») réelle plutôt que déclarative.
- **Fiscalité** : le fonds n'est pas imposé sur ses plus-values ; **la société de gestion est
  imposée sur son résultat** (25 %). Ne mélange pas les deux. Le PFU de `config.py` concerne le
  portefeuille personnel du site, **pas ce jeu** — ne le recopie pas ici par réflexe.

### §9.3 — La collecte et les rachats
- La collecte suit la performance **avec deux trimestres de retard** — les flux suivent, ils
  n'anticipent pas. Modulée par : ancienneté, présence d'un RI, régularité, fidélité au mandat.
- Les rachats se déclenchent sur : drawdown > seuil, deux trimestres négatifs de suite, dérive
  constatée, événement de marché, départ d'une figure connue de la maison.
- **Si la trésorerie ne couvre pas les rachats, le moteur vend — de force, au cours du mois, en
  commençant par le plus liquide.** Le joueur ne choisit pas. Cette ligne de code est la leçon
  la plus chère du jeu : c'est la raison pour laquelle la clause de liquidité du §6.1 existait.

### §9.4 — La société de gestion
Recettes = frais encaissés. Charges = salaires (+ ~45 % de charges sociales) + loyer par étage
+ données + audit/dépositaire (fixe) + commissariat. **Trésorerie négative deux mois de suite =
cessation de paiement**, fin de partie, avec un bilan qui explique laquelle des deux
comptabilités a lâché.

---

## §10 — La fin de partie : le seul moment où le jeu parle franchement

À 120 mois (ou à la faillite), un bilan en quatre écrans, dans l'ordre :

### §10.1 — Les deux colonnes
Ce que les investisseurs ont gagné (VL, net de tout) · ce que tu as gagné (résultat cumulé de
la société). Plus **le rapport entre les deux** : combien d'euros de valeur créée pour un euro
encaissé. La phrase peut être dure, elle doit rester factuelle.

### §10.2 — Brut, net, indice
Performance brute · nette de frais · celle d'un indice large sur la même période, et **l'écart
imputable aux seuls frais**. Trois barres, la grammaire de couleur du §12, aucun commentaire.

### §10.3 — L'attribution *(débloquée seulement si tu as embauché un quant)*
Décomposition de la performance en **marché (bêta) / secteur / sélection / inexpliqué**.
Pour beaucoup de parties, la sélection sera petite et le marché énorme. **Ne l'adoucis pas.**
Si le joueur n'a jamais embauché de quant, l'écran affiche à la place : *« Personne ici n'a
jamais calculé d'où venait la performance. C'était une décision, elle a un prix : celui de ne
pas savoir. »*

### §10.4 — Le contrefactuel (le clou)
Le moteur **rejoue 500 parties** sur exactement le même marché, le même mandat et les mêmes
événements, en décidant **au hasard** à chaque arbitrage. Il place le joueur dans la
distribution obtenue :

> *« Ta part a fait +47 % en dix ans. 500 gérants décidant au hasard avec ton mandat ont fait
> entre −18 % et +96 %, médiane +39 %. Tu es au 61ᵉ centile. Sur dix ans et 43 décisions, cet
> écart ne suffit pas à distinguer la compétence de la chance. »*

C'est la conclusion la plus honnête qu'un jeu d'investissement puisse offrir, et c'est
littéralement la posture affichée du site. **Elle n'est pas optionnelle.**
Techniquement : le moteur est **sans DOM et rejouable sans interface** (§11), les 500 parties
tournent **par tranches** avec une barre de progression — le calcul lui-même est un moment de
jeu (« on rejoue 500 gérants… »).

---

## §11 — Contraintes techniques dures

1. **Statique, zéro backend, zéro build.** HTML + CSS + JavaScript classique. Pas de framework,
   pas de bundler, pas de TypeScript, pas de moteur de jeu, pas de CDN. Seule exception, déjà en
   place sur les quatre onglets : la police Inter, avec **exactement la même requête**.
2. **Trois fichiers de code**, et cette découpe n'est pas cosmétique — c'est ce qui rend §10.4
   et §16 possibles :
   - `maison-moteur.js` — **la simulation entière, sans DOM, sans `fetch`, sans horloge** :
     marché, portefeuille, frais, flux, équipe, événements, arbitrages, bilan. Se termine par
     `if (typeof module !== 'undefined') module.exports = MAISON;` pour tourner **sous node**.
     Doit pouvoir jouer 500 parties de 120 mois **en moins de 2 secondes**.
   - `maison-rendu.js` — le canvas : immeuble, mobilier, bonhommes, rails, animations. Ne
     décide rien ; il **lit** un état et le dessine.
   - `maison.html` — le gabarit, le panneau, les entrées clavier/tactile, la colle.
3. **Le moteur est déterministe.** Générateur pseudo-aléatoire **à graine, écrit à la main**
   (mulberry32, ~5 lignes). **`Math.random()` est interdit dans le moteur** et dans le rendu (les
   scintillements décoratifs inclus : un décor non reproductible casse les captures de test).
   Une partie = `graine + suite des décisions`. `maison.html#/p/<graine>` rejoue le même monde.
4. **Aucune fuite du futur** : la boucle ne reçoit que la tranche `[0, mois]` de la matrice de
   marché. Testé (§16).
5. **Budget de données : < 250 Ko** pour démarrer une partie. Donc **ne charge jamais**
   `analyses.json` (956 Ko), ni `watchlist.json` (220 Ko), ni les 150 `charts/*.json` (3,9 Mo).
6. **Budget d'image : 60 fps sur un portable de 2020**, jusqu'à 25 bonhommes. Un seul `<canvas>`,
   un seul `requestAnimationFrame`, aucun DOM créé dans la boucle de rendu. Le rendu se met en
   **pause quand l'onglet est caché**.
7. **Sauvegarde** : `localStorage`, clé unique `signal.maison.v1`, objet **versionné**
   (`{v:1,…}`), sauvegarde automatique **à chaque trimestre** + bouton manuel, **une seule partie
   en cours** + les bilans des 20 dernières terminées. **Tout accès enveloppé dans un
   `try/catch`** (en navigation privée Safari, `setItem` lève, et le jeu doit rester jouable
   sans mémoire). Bouton **« effacer mes données »** visible. Rien ne quitte le navigateur.

---

## §12 — Le contrat de données

### §12.1 — Ce qui existe
`charts/<TICKER>.json` (150 fichiers, ~24 Ko pièce). Mesuré sur le dépôt :
**segment hebdomadaire = 104 points max** (730 jours), **segment mensuel : médiane 284 points,
jusqu'à 752**. Le jeu se joue **au mois** : c'est le segment mensuel qui l'alimente, et il est
largement assez profond pour une partie de 120 mois.

Trois pièges, tous documentés dans `screener.py` (~l.362) — relis-le :
- l'abscisse est un **mois flottant** (`année×12 + (mois−1) + (jour−1)/31`) ;
- l'échantillonnage est **mixte** (hebdo sur 730 j, mensuel avant) : sépare les deux par l'écart
  d'abscisse (≈ 0,23 entre deux points hebdo, ≈ 1,0 entre deux mensuels), ne suppose jamais un
  pas régulier ;
- les cours sont **ajustés** (splits, dividendes) et arrondis à 3 chiffres significatifs sous 1.

`universe.json` → `stocks` : 133 tickers avec `nom`, `secteur`, `devise`. C'est ta source
d'identité pour la révélation finale.

### §12.2 — Ce que tu ajoutes : `jeu/marche.json`
Un **pack de marché compact**, produit par `tools/jeu_marche.py` :

```jsonc
{
  "updated_at": "2026-08-12",
  "t0": 22812,                 // abscisse du premier mois de la grille
  "mois": 240,                 // longueur de la grille
  "titres": [
    {"t":"NVDA","sec":"Technologie","d":"USD","i0":0,"px":[100,104,97, …]}
  ]
}
```

- **Grille de mois commune**, alignée sur l'abscisse `_mois`. Un titre entré en cours de route
  porte son `i0` et une série plus courte : le moteur doit gérer les titres **non cotés au début
  de la partie** (ils apparaissent, c'est réaliste et c'est gratuit).
- Prix **rebasés à 100 au premier point du titre**, arrondis à l'entier. Sur 80 titres × 240
  mois ≈ 19 200 nombres de 3-4 caractères → **~90 Ko**, très en dessous du budget, et bien moins
  une fois servi compressé par GitHub Pages.
- **Critère d'entrée** : au moins 150 points mensuels, un secteur connu, une devise connue.
- Le script écrit **atomiquement** (`save_json_atomic`, `allow_nan=False` — voir `screener.py`),
  **purge les orphelins**, et il est branché dans `.github/workflows/watchlist.yml` après le
  screener, avant le commit, avec `git add jeu/`.

### §12.3 — Le masquage des sociétés
Pendant la partie, les sociétés portent **un nom fictif** et **leur vrai secteur**. Les cours
sont réels. À la fin, la correspondance est révélée.

- Les noms viennent d'une **liste fictive fixe** écrite dans le moteur (ex. `Ardyne Semiconducteurs`,
  `Ligne Bleue Santé`, `Nordvale Énergie`…), **jamais générés par assemblage de syllabes** : un
  générateur finira par produire le nom d'une vraie entreprise, et le jeu lui collera alors une
  faillite inventée. L'attribution nom↔ticker est déterministe à partir de la graine.
- Cette liste, et l'interdiction du §7, forment **une seule et même règle éditoriale** : le jeu
  n'invente aucun fait sur aucune entreprise réelle.

---

## §13 — Design system : réutiliser, et ne pas redéfinir

**Réutilise tel quel** (`signal.css` est déjà chargé) : `.card`, `.sec`/`.sec-h`, `.eyebrow`,
`.tag`, `.metrics`, `.meter`, `.ring`, `.gauge`, `.bar-track`/`.bar-fill`, `.sep`,
`.pos`/`.neg`/`.neu`, `.type-cur`, et les keyframes `blink`/`rise`/`ringglow`.

**Grammaire de couleur — la règle la plus facile à violer sans s'en apercevoir :**
- `--ac` (#74b6df) est **le seul accent**. L'immeuble, les gens, les meubles, les traits : cyan
  et niveaux de gris. **Un immeuble multicolore serait la faute la plus visible de la livraison.**
- `--green` / `--red` sont **réservés au P&L factuel chiffré**. Interdits pour : un moral, une
  jauge, un bouton, un état d'employé, une alerte, un mur, un bonhomme.
- `--gold` : le badge « fictif », et lui seul.
- **Aucune information ne passe par la couleur seule.** Le dépôt l'écrit noir sur blanc à propos
  des pastilles d'Actualités (« la flèche est REDONDANTE avec la couleur, et c'est voulu »).
  Un employé démoralisé se voit à sa **posture** et à une **icône**, pas à sa teinte.

**Ne redéfinis JAMAIS** dans `maison.html` les sélecteurs nus du chrome partagé — `.brand`,
`.brand-name`, `.brand-icon`, `nav`, `nav a`, `nav a svg`, `.footer-legal`, `.footer-right`.
**`tests/test_chrome.py` fait échouer la CI si tu le fais.** `header{position:…}` reste permis :
ta page ne défile pas (l'immeuble occupe l'écran), donc **header `fixed`**, comme `index.html`
— et alors tu compenses explicitement la hauteur, comme `index.html` le fait (`top:5.6rem`).
Recopie le motif **en entier**, jamais à moitié : c'est un bug déjà survenu et documenté.

---

## §14 — Accessibilité, mobile, et le registre

Un jeu fait de petits bonhommes qui bougent est **par nature un jeu visuel**. On ne peut pas
faire semblant du contraire ; on peut refuser d'en faire un jeu **exclusivement** visuel.

- **Le registre** : un onglet du panneau qui donne, **en texte et en permanence**, tout ce que
  l'immeuble raconte en images — qui fait quoi, qui attend, ce qui vient de se passer, l'état des
  deux comptabilités. **Toute la partie doit être jouable depuis le registre seul.** Ce n'est pas
  un mode dégradé : c'est aussi la vue que préféreront les joueurs pressés.
- **Clavier de bout en bout** : `Espace` pause · `1`/`2` vitesse · `Tab` circule entre les
  personnes en attente · `Entrée` ouvre l'arbitrage · `1`-`4` choisissent une option ·
  `C` le carnet · `R` le registre. Focus toujours visible.
- Le `<canvas>` est `aria-hidden`. Un `aria-live="polite"` **sobre** annonce les arbitrages en
  attente et les événements majeurs — **pas chaque mois qui passe**, sinon un lecteur d'écran
  parle en continu pendant trente minutes.
- **`prefers-reduced-motion`** : personne ne marche (les gens se **téléportent** entre leurs
  états), pas de balancement, pas de lueur pulsée, pas de défilement. Le jeu reste entier.
  `signal-fx.js` respecte déjà ce réglage — fais pareil, ce n'est pas négociable.
- **Mobile ≥ 360 px** : l'immeuble passe en pile verticale à un étage visible à la fois (bandeau
  d'étages en haut), le panneau devient une feuille dépliable — même motif que `.tocm` dans
  `signal.css`, va le lire. Cibles tactiles ≥ 44 px. Aucun geste sans équivalent bouton.
- Contraste ≥ 4,5:1 pour tout texte, y compris posé sur l'immeuble. Vérifie, ne suppose pas.

---

## §15 — Le cinquième onglet : la checklist exacte

`tests/test_chrome.py` compare **les quatre onglets entre eux** ; en ajouter un cinquième touche
tous les fichiers ci-dessous.

1. **`maison.html`** — nouvelle page. Doit porter, sous peine d'échec CI : `rel="icon"` (le
   favicon en data-URI, **identique** aux autres) · `name="description"` · la **même** requête
   `fonts.googleapis.com/css2?family=Inter…` · `signal.css` · `signal-fx.js` · `.footer-legal`
   avec la mention AMF **au mot près** · `.footer-right`. Plus le décor : `#fx`,
   `<canvas id="bg">`, `.scan`, `.frame` (les quatre `<i>`).
2. **La nav, dans les CINQ pages** — même ordre, mêmes libellés partout, et **« Portefeuille IA »
   doit rester la dernière entrée** (un test l'exige nommément). Ordre cible :
   `Watchlists · Actualités · Apprendre · La Maison · Portefeuille IA`
   Le lien : `<a href="maison.html">`, avec un `<svg viewBox="0 0 24 24" aria-hidden="true">` en
   **tracé** (`stroke:currentColor`, jamais de `fill`) et le libellé dans un `<span>` — sinon le
   test de nav ne le trouve pas et l'icône ne prend pas la couleur de l'onglet actif.
   *Glyphe suggéré : un immeuble en coupe — un rectangle et deux lignes d'étage. Lisible à 19 px,
   et il annonce exactement ce qu'on va voir.*
3. **`tests/test_chrome.py`** — ajouter `"maison.html"` à `PAGES` et **corriger les libellés qui
   disent « les 4 onglets »**. Les contrôles propres à `index.html` (`.home-h`, `top:5.6rem`,
   `FD_RUPTURE`, colonne de repos) restent tels quels.
4. **`README.md`** — bloc « Architecture » (la page, les deux JS, `jeu/marche.json`,
   `tools/jeu_marche.py`) et « Fichiers clés ». Au passage : **le README annonce encore
   « PFU 30 % » alors que `config.py` est à 31,4 %** depuis la LFSS 2026 — corrige-le.
5. **`.github/workflows/watchlist.yml`** — génération du pack, `git add jeu/`.
6. **`CHANGELOG.md`** — une entrée en tête (§17).

---

## §16 — Tests

**Les tests de ce dépôt tournent HORS LIGNE, sans aucune dépendance installée**, sur chaque
poussée (`.github/workflows/tests.yml`). Style de la maison, à respecter : un fichier
`tests/test_maison.py`, exécutable seul (`python tests/test_maison.py`), **un docstring qui
explique POURQUOI le fichier existe** (pas ce qu'il fait), la fonction `check(nom, cond, detail)`,
les `✅`/`❌`, le décompte final, `sys.exit(1)` si rouge. Et avant de croire un « tout est vert »
local : **`PYTHONPATH=tests python3 tests/test_maison.py`** (cf. `tests/_sans_bibliotheques.py`).

**Le moteur se teste POUR DE VRAI, sous node** — motif déjà employé par `test_chrome.py`,
`test_charts.py` et `test_actualites.py` : on exécute le code livré, on ne le relit pas. Et comme
eux, **si node manque, on l'écrit** (`⚠️ non vérifié (node indisponible)`), on ne fait pas semblant.

| # | Propriété | Pourquoi elle compte |
|---|---|---|
| 1 | **Reproductibilité** : même graine + mêmes décisions ⟹ bilan identique au centime | tout le reste en dépend, à commencer par le contrefactuel |
| 2 | **Aucun `Math.random()`** dans les deux JS | une seule occurrence casse (1) en silence |
| 3 | **VL** : souscription et rachat à la VL du mois ne changent pas la VL des porteurs existants | la dilution est le bug classique, invisible à l'œil |
| 4 | **High-water mark** : après −20 % puis +15 %, **aucun** frais de performance ; le HWM n'est franchi qu'au-delà de l'ancien plus haut | l'implémentation naïve se trompe ici à tous les coups |
| 5 | **Frais de gestion** : 2 % l'an sur encours constant ⟹ 2 % ± 0,01 sur douze mois | le prorata mensuel est vite faux |
| 6 | **Exécution** : 7,5 bps avec gérant, 30 bps sans ; refus sous 50 € | la promesse d'honnêteté du jeu |
| 7 | **Les constantes du JS égalent celles de `config.py`** (parsées des deux fichiers, comparées) | motif `FD_RUPTURE` de `test_chrome.py` : un doublon dérive toujours |
| 8 | **Rachat > trésorerie ⟹ vente forcée**, dans l'ordre de liquidité, et la VL en porte la trace | c'est la leçon centrale : si elle n'est pas juste, le jeu ment |
| 9 | **Pas de fuite du futur** : sur une matrice marquée, l'état au mois `m` ne contient aucune donnée > `m` | sans ça, tout le jeu perd son sens |
| 10 | **Faillite de la société** : trésorerie négative deux mois ⟹ fin de partie, même si le fonds performe | le §2 doit être atteignable, pas théorique |
| 11 | **Contrefactuel** : 500 parties « au hasard » sur graine fixe ⟹ distribution stable, et un joueur qui ne fait rien tombe près de la médiane des « ne rien faire » | un contrefactuel biaisé produit une conclusion fausse et péremptoire |
| 12 | **Performance** : 500 parties × 120 mois en **< 2 s** sous node | sinon l'écran final est injouable |
| 13 | **Graphe de déblocage** : sans cycle, chaque métrique rattachée à un rôle, chaque concept du §8 atteignable en partie normale | un concept inatteignable est une promesse pédagogique non tenue |
| 14 | **Événements** : chaque modèle porte une `portee` ; **aucun modèle de portée `ligne` ne contient de texte narratif** — uniquement des champs calculés | c'est la règle du §7, et elle est trop importante pour reposer sur la vigilance |
| 15 | **Noms masqués** : la liste est fixe, sans doublon, et l'attribution nom↔ticker est déterministe | idem |
| 16 | **Intégrité du pack** : tout titre de `jeu/marche.json` existe dans `charts/`, aucune valeur non finie, grille de mois strictement croissante, aucun orphelin | même garde que la purge de `charts/` |
| 17 | **Sauvegarde** : un état v1 se relit ; un `localStorage` indisponible ne casse pas la partie | Safari privé |
| 18 | **Les scripts inline de `maison.html` se parsent** (`node --check`) | une erreur de syntaxe a déjà mis le site entier en panne (09/08/2026) |

---

## §17 — Livrables, commits, changelog

```
maison.html                 gabarit, panneau, entrées, colle
maison-moteur.js            la simulation — pure, sans DOM, rejouable sous node
maison-rendu.js             le canvas — immeuble, meubles, bonhommes, rails
jeu/marche.json             pack de marché compact (généré, committé)
tools/jeu_marche.py         le générateur — atomique, avec purge des orphelins
tests/test_maison.py        la suite (§16)
index.html · actualites.html · apprendre.html · portfolio.html   + 5ᵉ entrée de nav
tests/test_chrome.py        PAGES + libellés
.github/workflows/watchlist.yml   génération du pack
README.md                   architecture, fichiers clés, correction du PFU
CHANGELOG.md                l'entrée
```

**Commits** : français, préfixés comme le dépôt (`feat(maison): …`, `fix(chrome): …`), **une
phrase qui dit ce qui change pour le lecteur**, jamais ce que fait le code. Regarde
`git log --oneline -20` : le style y est sans ambiguïté.

**CHANGELOG** : une entrée en tête, titrée comme les autres — une phrase qui **raconte le
problème ou la décision**, pas « ajout du jeu ». Ce dépôt écrit ses entrées comme des constats
(« Le maillon mémoire décrivait un oligopole en oubliant un de ses membres ») : tiens ce niveau.

**Branche** : `claude/signal-investment-game-prompt-rvkkyo` — développe, commit, pousse
(`git push -u origin …`). **N'ouvre pas de pull request** sauf demande explicite.

---

## §18 — Les trois lots (respecte l'ordre)

### Lot ① — « La coupe » *(jouable et livrable seul)*
Le RDC + un étage. Toi + **deux recrues** (analyste, exécution). Le temps qui passe, le marché
réel, la VL, les frais de gestion, **un** type d'arbitrage (la thèse de l'analyste), les
bonhommes qui marchent et qui montent te voir. Le pack de marché, le chrome à cinq onglets, le
registre, la sauvegarde, et les tests 1-3, 5-7, 9, 16, 18.
**Critère de fin de lot : on peut jouer dix ans et voir une VL, sans que ce soit ennuyeux.**

### Lot ② — « La maison »
Tous les rôles et le déblocage des métriques. Le mandat et la dérive de style. Les deux
comptabilités et la faillite. Collecte, rachats, **vente forcée**. Moral, départs, débauchage.
Les six familles d'arbitrages. Les étages qui s'ouvrent. Tests 4, 8, 10, 13-15, 17.

### Lot ③ — « Le bilan »
Le carnet et les seize concepts. Les quatre écrans de fin. L'attribution. **Le contrefactuel à
500 parties.** Le partage en texte du bilan. Tests 11-12.

---

## §19 — Définition du « terminé » (par lot)

- [ ] `python tests/test_maison.py` vert, **et** `PYTHONPATH=tests python3 tests/test_maison.py`
      vert (le runner n'a aucune bibliothèque tierce).
- [ ] `for f in tests/test_*.py; do python $f; done` : **toutes** les suites vertes, y compris
      `test_chrome.py` après l'ajout du cinquième onglet.
- [ ] Nav identique sur les cinq pages, « Portefeuille IA » toujours en dernier, bandeau de
      hauteur constante d'un onglet à l'autre.
- [ ] Une partie complète se joue **au clavier seul**, une autre **au doigt seul à 360 px**, une
      troisième **depuis le registre seul**.
- [ ] `prefers-reduced-motion` activé : rien ne bouge, tout reste jouable.
- [ ] Recharger `maison.html#/p/<graine>` rejoue le même monde.
- [ ] 60 fps avec 25 bonhommes ; le rendu s'arrête quand l'onglet est caché.
- [ ] Aucun `--green` / `--red` ailleurs que sur un chiffre de P&L. Relis ton CSS pour ça.
- [ ] Données téléchargées pour démarrer : **< 250 Ko**, mesuré, pas estimé.
- [ ] Aucun appel réseau autre que `jeu/marche.json` et la police. Rien ne quitte le navigateur.
- [ ] **Aucun texte du jeu n'attribue un fait à une entreprise réelle** (§7, §12.3).

---

## §20 — Hors périmètre, et décisions à confirmer

**Hors périmètre** (ne le fais pas, même si c'est tentant) : classement en ligne · comptes
utilisateurs · multijoueur · vente à découvert, levier, dérivés · marchés privés · crypto ·
génération d'images de partage · lien avec le portefeuille IA réel · notifications · **sons**
(aucun : ce site se lit au bureau) · animation d'ambiance coûteuse (météo, jour/nuit, foule).

**Décisions à confirmer avant de coder** — propose ces valeurs par défaut, applique-les faute de
réponse, et **écris dans ta livraison ce que tu as tranché** :

| # | Question | Défaut proposé |
|---|---|---|
| 1 | Libellé de l'onglet : « La Maison » (le terme métier français, et l'objet qu'on voit) ou « Le Fonds » (plus explicite, plus plat) ? | **La Maison**, avec un chapô qui l'explique dès la première ligne |
| 2 | Durée d'une partie | **120 mois**. Prévois un mode **48 mois** dès le lot ① : dix ans, c'est long pour une première partie |
| 3 | Vue : coupe **plein écran** ou coupe + panneau latéral fixe ? | **Coupe + panneau**, panneau repliable ; sur mobile, feuille dépliable (motif `.tocm`) |
| 4 | Sociétés masquées, ou vrais noms ? | **Masquées**, révélées à la fin — sinon celui qui connaît l'histoire de NVDA joue avec les réponses, et la règle du §7 devient intenable |
| 5 | Capital de départ | **500 000 €** d'apport personnel + une première collecte de 2 à 5 M€ selon le mandat |
| 6 | Nombre de titres dans le pack | **80** (~90 Ko). Monte à 120 si le poids le permet |

**Une dernière chose.** Si tu découvres en chemin qu'une de ces contraintes rend le jeu mauvais,
**dis-le et argumente** au lieu de la contourner en silence. Ce dépôt documente ses erreurs et
ses angles morts dans son CHANGELOG ; un désaccord motivé y a plus de valeur qu'une livraison
qui fait comme si tout allait de soi.
