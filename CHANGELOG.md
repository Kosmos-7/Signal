# Changelog — Signal

Toutes les évolutions notables du projet sont documentées ici.
Format inspiré de [keepachangelog.com](https://keepachangelog.com/fr/).

---

### Un cinquième onglet a vécu quelques heures, et c'est l'historique qui le garde

Le jeu de simulation « La Maison » (#5), fusionné et déployé le 12/08 au soir,
est retiré le même jour à la demande du propriétaire : le site n'embarque pas
de jeu. Le retrait est un revert propre du merge — la page, le moteur, le
rendu isométrique, le pack de marché, ses 48 tests et sa spécification
restent dans l'historique git, prêts à revenir si la décision change.

Les quatre onglets retrouvent leur chrome d'avant, y compris les retouches
qui n'existaient que pour loger le cinquième (le nom de la marque qui
s'effaçait sous 480 px). Une correction survit au retrait, parce qu'elle
n'appartenait pas au jeu : le README annonçait encore « PFU 30 % » alors que
config.py porte 31,4 % depuis la LFSS 2026.

### La watchlist « Espace » nommait un secteur, pas son sujet

Le propriétaire l'a signalé : le vrai terme est **NewSpace** — « un sous-ensemble
du secteur spatial qui fait son apparition au milieu de la décennie 2000 et qui
se caractérise par l'apparition d'une nouvelle génération d'acteurs industriels,
l'utilisation de technologies et de processus innovants, la recherche de nouveaux
débouchés et de nouvelles méthodes de financement ». Un sous-ensemble, et un
sous-ensemble défini **contre** ce qui le précédait.

**Le changement n'est donc pas d'étiquette, il est de périmètre.** Prendre le mot
au sérieux fait sortir de la liste les dix maîtres d'œuvre historiques (Lockheed,
Northrop, L3Harris, RTX, BAE, Airbus, Thales, Safran, Leonardo, Kratos) et les
quatre opérateurs de satellites qui les accompagnaient (SES, Eutelsat, Viasat,
Iridium) : quatorze titres sur vingt.

**Le texte de la liste l'avouait déjà** — « LA LISTE EST COUPÉE EN DEUX, et ses
deux moitiés ne se comportent pas du tout pareil […] comparer les scores d'une
moitié à l'autre n'a pas de sens ». Une watchlist qui écrit qu'elle mesure deux
objets en mesure un de trop.

**On retire une liste, pas des sociétés** : troisième emploi de cette phrase après
la chaîne quantique et l'ex-thème financials. Les quatorze restent dans l'univers
du screener, scorés et candidats au top 30 — six d'entre eux n'y existaient que
par ce thème et sont désormais déclarés explicitement dans `screener.py`.

**Un titre entre**, validé avant d'être écrit comme le prescrit
`validate_tickers.py` : Voyager Technologies (~2,6 Md$, 1,2 an de cotation), qui
construit Starlab — le débouché que la station spatiale internationale laissera
vacant. Il ouvre avec Redwire un maillon « travailler en orbite ».

**Onze candidats éprouvés contre Yahoo le 12/08, aucun deviné.** Quatre écartés
sur la règle et non sur la taille — Globalstar, AeroVironment, Karman, Avio :
une cotation neuve ne fait pas une génération neuve. Cinq écartés sous le
milliard — Spire, Satellogic, Virgin Galactic, GomSpace, AAC Clyde — dont les
deux seuls NewSpace européens cotés, qui pèsent le dixième du plus petit titre de
la liste. Firefly reste au registre : son fournisseur ne rend aucune
capitalisation, et plusieurs points de la note se calculent dessus.

**Sept titres, donc, et une deuxième exception nommée** à la règle des vingt, à
côté de « quantique ». Baisser le seuil aurait été plus simple ; nommer
l'exception oblige la suivante à se justifier aussi.

L'identifiant a suivi le nom, illustration et légendes comprises :
`espace` → `newspace`.

### Audit du 12/08 : les chiffres cités que rien ne surveillait

Point de départ : « les fiches de CoreWeave et Nebius se mettent-elles à jour
toutes seules ? » Les chiffres oui, chaque soir ; les textes non — et en
cherchant pourquoi, l'audit a trouvé trois trous du même genre, un défaut dans
son propre garde-fou, et un bug dans son propre instrument de mesure.

**1. Le contrat compact ne portait aucun chiffre de valorisation.** 118 des 148
fiches publiées sont rédigées depuis `universe.json`, sans PER, sans marge, sans
croissance. Leur signature éditoriale calculait « donnée absente » quatre fois de
suite, stablement, donc sans jamais rien signaler : le garde-fou du 09/08 ne
protégeait que 30 fiches sur 148. Et privé de chiffres, le modèle en écrivait de
mémoire — neuf fiches citent une marge brute, une marge opérationnelle ou un
cours/ventes, grandeurs que le dépôt ne calcule nulle part et qu'aucun contrôle
ne pourra jamais infirmer ; Teradyne va jusqu'à nommer une source jamais
consultée. Le contrat porte désormais les sept grandeurs (test AST
producteur/lecteurs à l'appui), et une publication de résultats déplace la
signature, donc réécrit la fiche au run suivant — ce qui répond à la question de
départ.

Le cas Micron fixe le critère : « multiple forward autour de 6x, exercice 2027 »
sans qu'aucun des deux figure dans son prompt — et les deux sont JUSTES (5,6x,
2027). Rien ce jour-là n'aurait distingué ce 6 juste d'un 9 faux. Le critère
n'est pas d'avoir raison, c'est d'avoir une source ; le guide le dit maintenant
en ces termes.

**2. Trois grandeurs vivaient dans l'entre-deux que la règle interdit.**
La *décote vs tendance* (355 citations chiffrées, dix fois le RSI) passe hors
chiffre : dirigée par le cours, non bornée, 14 fiches sur 144 avec plus de dix
points d'écart en deux jours — la surveiller coûtait 46 réécritures/2 jours.
Le *potentiel consensus* (145 citations, le chiffre le plus cité du site) passe
hors chiffre AUSSI, mais son SIGNE entre dans la signature par tranches larges :
« consensus modestement positif (8 %) » écrit sur Vestas face à −8,9 % est faux
en mots, et retirer le nombre ne répare pas la phrase — quatre bascules de signe
en deux jours, douze potentiels négatifs au 12/08. La *marge FCF* (27 citations)
entre dans la signature pour zéro palier franchi en deux jours : une marge TTM ne
bouge que quand l'entreprise publie. Le z-score passe au demi-sigma (la prose le
cite au dixième, « neutre » couvrait ]−2σ, +2σ[).

La règle générale que ces trois cas dégagent : **on surveille une grandeur à la
finesse à laquelle la prose l'exprime.** Chiffrée → paliers serrés ; qualifiée →
tranches ; tue → rien.

**3. Le garde-fou et l'instrument avaient chacun leur défaut.** Le seuil du test
prose/fiche valait `pas/2` en absolu — juste sur la distance au centre d'un
palier, faux entre deux valeurs : une marge de 2,56 % → 5,09 % était dénoncée
sans changement de palier, un rouge sans remède. Seuil au pas entier, propriété
vérifiée par balayage (bornes négatives incluses) et non plus sur un point choisi
par l'auteur du test. Et le motif `\d+[,.]?\d*` devant « surcote de 1 300 % »
capturait « 300 » : le relevé accusait Advantest de 1 036 points d'écart qu'il a
lui-même fabriqués. Tous les motifs passent par un lecteur de nombres français
unique (séparateurs de milliers compris). Les tolérances descendent de
`CHAMPS_VALO`, écrites une seule fois.

**Conséquences d'exploitation.** `PROMPT_VERSION` est bumpé : le prochain run
hebdomadaire réécrit les 148 fiches d'un coup (~14 min, ~4,50 $), puis le churn
s'établit vers ~50 % du corpus par semaine (~2,30 $) — c'est le prix de textes
qui suivent leurs chiffres. Registre CONNUS : 9 fiches hors périmètre inscrites,
à vider au prochain run éditorial.

### Le maillon mémoire décrivait un oligopole en oubliant un de ses membres

Kioxia manquait à l'infrastructure de l'IA, signalé par le propriétaire. Elle
n'avait jamais été écartée non plus : ni dans le thème, ni dans l'univers, ni
dans le registre des recalés à la validation. Ce n'était pas une décision,
c'était un trou.

**C'est le même oubli que SanDisk, vu de l'autre côté.** Kioxia et SanDisk
exploitent **en commun** les usines NAND de Yokkaichi et Kitakami ; la liste
retenait le partenaire coté à New York et laissait de côté celui coté à Tokyo.
Les trois autres producteurs mondiaux — Micron, SK hynix, Samsung — y étaient
déjà : le maillon décrivait un oligopole en oubliant un de ses membres.

Le profil rend la décision d'alors directement applicable : **~182 Md$ et 1,6 an
d'historique**, contre « ~180 Md$ au boom NAND, 1,5 an d'historique » écrit pour
SanDisk en août. Même traitement, donc — fiche avec avertissement de régression.

**Validée avant d'être écrite**, ce qui est l'ordre que `validate_tickers.py`
prescrit noir sur blanc : « on ne déclare un ticker qu'une fois qu'on sait qu'il
existe et qu'il passe les filtres ». Le runner a rendu 1/1, devise JPY conforme
au suffixe `.T`, secteur exploitable, capitalisation très au-dessus du seuil.

### Tâche #84 : j'ai cru la clore, elle avait cligné

Les cinq capitalisations d'Allianz, Micron, Safran, Siemens et Western Digital
publiaient toutes leur rendement du flux disponible, et plus aucune fiche du
corpus n'en manquait. Le contrôle « registre à jour » a donc exigé de vider ces
cinq entrées, et le constat était exact — à la seconde près.

**Une demi-heure plus tard, un run du screener a rendu son rendement à Allianz et
l'a repris aux quatre autres.** Le défaut ne s'était pas résolu : il avait cligné.
Le motif d'origine disait pourtant exactement ce qu'il fallait lire — « rendue par
**intermittence** par la source ».

**Les cinq sont réinscrites, y compris celles qui publient à cet instant** : la
liste nomme les titres que la source sert mal, pas ceux qui sont en panne à la
seconde où le test tourne.

**Et le mécanisme du registre a été corrigé, pas contourné.** La garde
anti-cimetière — celle qui exige de nettoyer une entrée qu'on ne constate plus —
se retourne contre un défaut intermittent : elle réclame un nettoyage qui
redeviendra faux au run suivant, et l'alarme sonne alors en permanence, ce que ce
registre reproche par ailleurs à une CI rouge en continu. Un contrôle peut
désormais se déclarer `intermittent`, ce qui désactive cette moitié-là **et elle
seule** : toute occurrence nouvelle échoue toujours. Vérifié en rejouant la
fonction sur les trois cas.

On n'a toujours rien réparé, et c'est écrit : le repli du 09/08 n'avait rien
changé les 09 et 10/08, donc le nombre d'actions manque aussi quand la
capitalisation manque. Lequel des deux revient, on l'ignore — la sonde est faite
pour le dire.

### Un PER qui baisse pendant que le cours monte

La prose de TSMC citait un PER courant de 32,3 ; la fiche en publie 28,2. Ce
n'est pas une dérive de cours, et la distinction fait tout : entre les deux runs
le cours a **monté** (2 395 → 2 415) pendant que le multiple chutait de 13 %. Un
PER qui baisse quand le prix monte, c'est le bénéfice qui bondit — TSMC a publié
entre-temps.

C'est la péremption structurelle que le projet connaît et n'a pas tranchée : la
prose est hebdomadaire, les chiffres des fiches sont quotidiens, et un texte qui
**stocke** un multiple vieillit dès que la donnée bouge. Le chantier « la prose
référence au lieu de stocker » est la seule forme qui rendrait ce défaut
impossible au lieu de surveillé ; il attend une décision. En attendant, l'entrée
disparaîtra d'elle-même au run éditorial du lundi, et le contrôle « registre à
jour » exigera alors de la retirer.

### « Chiffres publiés » s'ouvrait sur 2030

La section ouvrait sur sa **dernière** colonne. En vue annuelle, la dernière
colonne est la projection la plus lointaine — 2030 : le chiffre le moins sûr de
tout le graphique était celui qu'on lisait en arrivant. Elle s'ouvre désormais
sur l'année en cours, celle qui intéresse au premier coup d'œil et dont le
consensus est le plus dense.

**La colonne se cherche dans les données, jamais par un décalage compté à la
main.** Selon la fiche, l'année courante est déjà publiée ou encore attendue, et
les deux ne rangent pas leur millésime au même endroit — `fin` pour un exercice
déposé, `exercice` pour une projection. Vérifié au navigateur : NVIDIA ouvre sur
un FY26 **publié**, TSMC et ASML sur un FY26 **attendu**, avec la mention
« consensus des analystes ». Quand deux exercices se closent la même année civile
— un changement de calendrier fiscal —, c'est le plus récent qui décrit l'état
courant.

**Le trimestriel ne change pas** : douze colonnes y partagent trois ou quatre
millésimes, « l'année en cours » n'y désigne aucune colonne en particulier, et le
dernier trimestre reste le repère naturel.

**Le test exécute le code livré, il ne le relit pas.** Le bloc est extrait
d'`index.html` et rejoué dans node sur des colonnes fabriquées — la règle est une
fonction pure de (colonnes, mode, année). Un test qui aurait cherché
`new Date().getFullYear()` dans le fichier serait resté vert avec un décalage
d'un cran dans la boucle. Les cas sont construits **à partir** de l'année
courante et non d'un millésime écrit en dur, sans quoi ils tomberaient seuls au
1<sup>er</sup> janvier. Neutraliser la règle fait échouer les trois cas concernés
et laisse verts les deux qui attendaient la dernière colonne de toute façon.

### Quatre pages, quatre écarts sous l'en-tête

Mesuré au navigateur, la distance entre l'en-tête et le premier titre valait
**25 px** pour « Watchlists », **40** pour « Une IA contre l'indice », **48** pour
« Actualités » et **56** pour « Comprendre la bourse ». Quatre valeurs pour un
réglage qui n'a qu'une raison d'être.

**Ce n'était pas un désaccord de conception.** Les trois pages à `<main>`
déclarent toutes `padding: 3rem` en base ; deux passes « plus d'air » sont
ensuite venues poser chacune leur nombre par-dessus — 2,5 rem sur le portefeuille,
3,5 rem sur apprendre. Même intention, deux chiffres, et personne pour les
comparer. Les quatre sont désormais à 48 px.

**La page d'accueil, elle, dérivait avec la largeur** : 48 px sur grand écran,
42 à 900, 54 sous 700. Son en-tête est `fixed` — il ne prend pas de place — donc
le dégagement est un nombre écrit à la main, et ce nombre ne suivait pas
l'en-tête quand `signal.css` le resserre à 700 px (81 → 69). Il est maintenant
reposé à chaque hauteur. Les trois autres pages n'ont pas ce calcul : leur
en-tête est `sticky`, il occupe sa place et le décalage vient tout seul.

**Le portefeuille et apprendre restent à 83 px sous 1300 px, et c'est juste** :
une barre de sommaire collante s'intercale alors entre l'en-tête et le contenu.
Le titre y est à 46-47 px **sous cette barre** — soit le même écart, mesuré depuis
l'élément qui le précède réellement.

**Le premier test écrit pour figer tout ça ne pouvait pas rougir**, et il l'a
prouvé : il ramassait toutes les valeurs déclarées dans les blocs `main{}` et se
contentait d'y trouver « 3rem » — or la règle de base en déclare toujours un, si
bien qu'une surcharge à 2,5 rem juste en dessous le laissait vert. Il lit
désormais la valeur EFFECTIVE, la dernière au niveau racine, celle que la cascade
retient. Vérifié en réintroduisant 2,5 rem : il échoue et nomme la valeur.

### « Trois décisions d'achat » quand le journal n'en montrait qu'une

Le texte hebdomadaire du 10 août annonçait trois achats — BKNG, ADBE, FTNT —
chacun avec sa justification. Le journal des ordres n'en portait qu'un. Personne
n'avait menti : **le portefeuille comptait 19 lignes sur un plafond de 20.** BKNG
a pris la dernière place, ADBE et FTNT ont été refusés par la règle
`max_positions`, et les deux refus sont bien enregistrés et affichés sur la page.

La cause n'est pas le modèle, c'est le prompt. `MAX_POSITIONS` était vérifié dans
`executer_decisions`, **après** la réponse de l'agent, et n'était dit nulle part
avant. Le prompt prévenait pourtant déjà pour R01, R03 et la concentration
sectorielle — avec ces mots exacts : « évite de proposer des décisions vouées à
l'échec » et « ne soumets pas l'action dans `decisions` si tu sais qu'elle sera
bloquée ». L'agent ne pouvait pas savoir : la seule règle qui allait le bloquer
était la seule qu'on ne lui annonçait pas.

Et comme `analyse_macro` est écrite **avant** l'exécution, la newsletter décrivait
des intentions au passé composé. L'état du portefeuille est désormais annoncé
dans le prompt — lignes ouvertes, plafond, places restantes — avec la consigne de
ne pas proposer plus d'achats que de places, ni d'en raconter davantage.

Trois gardes : que le prompt annonce les places restantes quel que soit l'état du
portefeuille, que la donnée publiée respecte le plafond qu'elle annonce, et
qu'aucune décision bloquée n'ait malgré tout produit un ordre — ce qui distingue
« refusée » de « passée quand même ».

### 645 Ko régénérés à chaque run, pour personne

`charts.json` était annoncé dans le code comme « TRANSITOIRE : `index.html` le
charge encore au démarrage ». Il ne le chargeait plus : les six points de
chargement du front ont été énumérés un par un, aucun ne le demandait, et la
seule occurrence restante du nom dans `index.html` était un commentaire racontant
l'époque où il servait. **La transition s'était terminée sans que personne
referme la porte.** Le monolithe continuait d'être régénéré à chaque run et
commité — 645 Ko dans chaque commit de données, pour aucun lecteur.

Il est retiré : le screener ne l'écrit plus, les deux workflows ne le commitent
plus, le fichier sort du dépôt. Les fiches sont servies par
`charts/<TICKER>.json`, à la demande et par titre — ce qui était précisément le
but de la transition. Les commentaires qui le décrivaient encore au présent ont
été corrigés plutôt que supprimés : celui qui raconte sa perte en v3.3.0 reste,
c'est de l'histoire, pas une description.

### Le repli de change devient un échec

Suite de la décision du propriétaire : le repli n'est plus seulement bruyant, il
n'existe plus. Quand le taux n'est pas mesurable, **le run s'arrête sans
écrire** — le site garde les chiffres de la veille plutôt que d'en publier de
faux, exactement comme `update_prices` le fait déjà quand aucun prix n'est
récupéré.

La table `_FX_FALLBACK` disparaît avec : elle portait un taux écrit en dur par
devise (DKK 7,46, JPY 170, KRW 1550…) servi en silence, et son
`.get(devise, 1.0)` traitait une devise absente de la table **comme de l'euro**.
Le même trou existait à la fin de `to_eur`, où un `return round(montant, 2)`
implicite laissait passer au pair toute devise inconnue — des yens comptés comme
des euros, un facteur 170. Aucune devise de l'univers publié n'était hors table,
donc le trou n'était pas ouvert ; il l'était en puissance, et rien ne l'aurait
signalé.

Une nuance est assumée et écrite : les deux paires majeures sont demandées avant
qu'on sache quelles devises sont détenues, donc une panne sur la livre fera
échouer un run même sans position britannique. Les deux paires viennent de la
même source, et le dollar pèse 64 % du portefeuille — rendre l'appel paresseux
pour épargner ce cas rare ajouterait une logique conditionnelle qui, elle,
pourrait se tromper.

### Un taux de change inventé, servi en silence, sous 64 % du portefeuille

`get_eur_usd_rate()` repliait sur **1,10** dès que Yahoo ne répondait pas — sans
un mot. Quinze positions sur vingt sont libellées en dollars, soit 64 % du
capital : ce taux multiplie leur valorisation, donc `capital_actuel`, donc la
performance publiée. Un repli à 1,10 pendant que le marché est à 1,05 déplace le
capital d'environ 3 % et le chiffre de couverture du site d'autant, et **rien ne
distinguait « le taux vaut vraiment 1,10 » de « la source n'a pas répondu »**.

C'est précisément ce que `screener.py` refuse de faire, à deux fichiers de là,
pour le rendement du flux disponible : « Sans taux — paire introuvable, réseau en
panne — on retombe sur le trou assumé, jamais sur un chiffre calculé avec un taux
inventé. » La doctrine du projet était écrite là et violée ici.

Le repli est **conservé** : le supprimer ferait échouer le run du soir sur une
panne de change, ce qui est une décision d'exploitation et pas de nettoyage. Mais
il crie désormais, et il laisse une trace que l'appelant peut lire. Deux tests le
figent : que le repli rende bien la valeur documentée, et qu'il ne puisse plus
servir sans se déclarer.

**Trois `except:` nus** subsistaient dans le module qui publie les nombres du
portefeuille — ils attrapaient aussi l'interruption au clavier et l'arrêt du
processus. Ils sont tous typés, et un test vérifie qu'il n'en revient pas.

### Le script qui réécrit la performance chaque nuit n'était testé par rien

`portfolio.json` a deux auteurs : l'agent le lundi, `update_prices.py` chaque
soir ouvré. Tous deux publient le champ `performance`. Le second n'était importé
par **aucune** des sept suites — alors que c'est lui qui réécrit chaque nuit le
nombre le plus important du site, et que c'est ce chemin-là qui aurait republié
32,94 % le soir où le registre des versements avait été restauré depuis un commit
périmé.

**La formule était écrite trois fois.** La reconstitution du capital de départ —
`capital_initial` moins la somme des versements — vivait dans `_perf_twr` et
deux fois dans `update_prices`. Trois copies d'une règle sont trois règles qui
divergent, et celle-ci porte le chiffre de couverture du site. `update_prices`
appelle désormais la fonction de l'agent au lieu de refaire son calcul.

L'équivalence a été prouvée avant d'être annoncée, sur les données réelles et
sur le cas limite qui compte : performance 34,72, post-liquidation 27,36, et un
versement en attente — identiques des deux côtés.

**Trois gardes.** Que le module s'importe dans les conditions du runner ; que les
deux modules tiennent la **même fonction**, vérifiée par identité d'objet et non
par égalité de résultat — deux fonctions qui rendent le même nombre aujourd'hui
peuvent diverger demain ; et que la reconstitution du capital de départ
n'apparaisse qu'à un seul endroit dans tous les modules de la racine. La
troisième a été éprouvée en réintroduisant la copie : elle nomme les deux
fichiers.

### Treize entrées de dispatch tombaient dans un shell

`photos-marques.yml` porte la leçon, écrite après coup : « les `|` de
`TICKER=a|b` avaient été pris pour des tubes et bash avait tenté d'exécuter les
termes comme des commandes. Au-delà du bug, c'est une injection : n'importe
quelle valeur d'entrée s'exécutait. » La parade — passer l'entrée par
l'environnement et la citer — y est appliquée à `termes`, **et oubliée deux
lignes plus bas** pour `limite` et `par_societe`, qui sont `type: string`
exactement comme elle.

Treize sites dans huit workflows étaient dans ce cas, dont `sonde-cotation.yml`
où les guillemets donnaient une fausse impression de sûreté : une entrée
contenant elle-même un guillemet referme la chaîne et la suite s'exécute. Tous
passent désormais par l'environnement.

**Quatre autres sites restent interpolés, et c'est écrit.** Une expression
`${{ inputs.x && '--drapeau' || '' }}` ne rend jamais l'entrée : elle rend l'un
de deux littéraux écrits dans le fichier. Une entrée `type: boolean` est rendue
`true` ou `false` par GitHub, jamais du texte libre. Les interdire aurait été
tracer une règle au hasard plutôt qu'à la mesure.

**Un test remplace le commentaire.** Il lit les dix-huit workflows par
expressions régulières — surtout pas par un parseur YAML, que le runner
n'installe pas et dont l'import tuerait la suite comme `PIL` l'a fait — et
échoue sur toute entrée libre interpolée dans un `run:`. Éprouvé en
réintroduisant une interpolation nue : il nomme le fichier et la ligne.

### Une fonction morte, une fausse morte

`cross_label` a été retirée : aucun appelant, et son format exact
(`Golden Cross · 12j`) n'apparaît dans aucune donnée publiée ni archivée. La
seule occurrence dans le dépôt est un exemple pédagogique en dur dans
`apprendre.html`.

`cross_score`, sa voisine immédiate, a failli partir avec elle. Elle n'a elle non
plus **aucun appelant dans le dépôt** — parce que c'est une surface publique :
`.claude/skills/portfolio-analyst/methodology.md` prescrit
`from screener import score_ticker, detect_cross, cross_score, calcul_regression`
pour qu'une analyse manuelle note un titre exactement comme le screener. Le
premier passage l'avait classée morte, sur un `grep` filtré par extension qui ne
regardait pas les `.md`. Un commentaire le dit maintenant à l'endroit où le
prochain détecteur de code mort la désignera.

### Actualités passait sous l'en-tête : un motif recopié à moitié

Le texte de la page Actualités démarrait trop haut par rapport aux trois autres.
`signal.css` pose `header{position:fixed}`, et un en-tête fixe **ne prend aucune
place dans le flux** : le `padding:3rem` de `main` partait donc du haut de la
fenêtre — 48 px — sous un en-tête qui en fait 81. La page commençait 33 px trop
haut, et son premier texte passait dessous.

Les trois autres pages s'en sortaient chacune à leur façon. `index.html` garde un
en-tête fixe parce que c'est une vue en SPA, mais il compense explicitement, et
ces valeurs sont surveillées depuis longtemps (`top:5.6rem`, `top:5.7rem`).
`portfolio.html` et `apprendre.html` repassent l'en-tête en `sticky` : il occupe
alors sa place, et le décalage vient tout seul.

**Actualités avait déjà la moitié du motif.** Elle porte le `html,body{height:
auto}` dont le commentaire, dans `portfolio.html`, dit explicitement « rétablit le
scroll naturel (header sticky) » — mais la ligne `header{position:sticky}` qui va
avec n'avait jamais suivi. Une page copiée d'une autre, moins une ligne.

**Le contrôle qui existait ne regardait qu'une page.** Il vérifiait les
compensations d'`index.html` contre la hauteur mesurée de l'en-tête, et rien
d'autre. L'invariant est maintenant général : une page qui pose son contenu dans
un `<main>` doit donner sa place à l'en-tête. Éprouvé en retirant la ligne — le
contrôle nomme la page fautive.

### Les illustrations : « 89 candidats » n'en font pas 89 d'utilisables

Vingt-neuf fiches sur cent quarante-huit n'ont pas d'illustration. Le dossier est
par ailleurs sain : cent trente-neuf images, cent trente-neuf légendes, aucun
cadre vide, aucune image téléchargée pour n'être jamais rendue.

**Le rapport de sonde surestime ce qui est exploitable.** Il compte 89 titres
« avec candidat », mais un candidat est un résultat de recherche, pas une
illustration. Il suffit de lire les noms de fichiers — la seule chose qui permette
de vérifier qu'une vignette illustre bien la société — pour voir ce que ces
candidats valent : *Arastra Gulch, Baker's Park. Silverton Quadrangle* pour Arista
Networks, une photo de la mission *Apollo 14* pour ASE Group, un *recensement de
1940* pour Blackstone, une carte marine du XVII<sup>e</sup> siècle pour Ibiden,
*Buildings in Ōmori 10.jpg* pour Disco Corporation. Sur les 89, 37 n'ont aucun
mot commun entre le nom de la société et le fichier proposé — mesure grossière,
qui compte quelques faux négatifs (*Chicago.Mercantile.Exchange.jpg* pour CME est
la bonne image), mais l'ordre de grandeur est là.

C'est le piège qui a déjà coûté quatre fois : une carte Supermicro pour Astera
Labs, un boîtier Netgear pour Fortinet, un bras Universal Robots pour Doosan, une
caméra IDS pour Cognex. **Vingt-cinq des vingt-neuf fiches sans illustration n'ont
par ailleurs jamais été sondées** — le rapport n'en couvre que 104.

**Trois invariants figés, dont un légal.** Le front n'affiche l'attribution que si
le champ `credit` existe, et les licences CC-BY et CC-BY-SA l'exigent : une entrée
sous CC-BY sans crédit publierait une photo en violation de sa licence, en
silence, sans que rien ne casse à l'écran. Rien ne le vérifiait. La vérification
est rassurante — les 98 entrées sous licence BY sont toutes créditées, les 19
visuels d'entreprise aussi, et les 14 sans crédit sont toutes en domaine public ou
CC0, qui ne l'exigent pas — mais elle ne tenait à rien. Les deux autres contrôles
exigent que les images et les légendes coïncident, et que chaque entrée nomme son
fichier source, sans quoi la vérification de provenance devient impossible.

Aucune illustration n'a été promue : Wikimedia est bloqué par le proxy de
développement, et promouvoir sans lire le nom du fichier source est précisément
l'erreur à ne pas refaire.

### L3Harris : ce n'est pas le changement d'exercice qui tronque, c'est le filtre

La série de L3Harris s'arrête en 2019 pendant que ses trimestres vont jusqu'en
2026, et le registre attribuait la troncature au changement d'exercice fiscal.
Le changement est réel — juin devient décembre à la fusion de 2019 — mais il
n'explique rien à lui seul. **La cause est le filtre de clôture majoritaire**,
qui écarte tout exercice dont la clôture s'éloigne de plus d'un mois du mois
majoritaire. Les dix exercices juin/juillet de 2008 à 2019 font la majorité :
c'est donc le régime POSTÉRIEUR, décembre, à six mois d'écart, qui est jeté. Le
filtre garde l'ancien monde et supprime le nouveau.

Son propre commentaire énonçait l'hypothèse qu'il viole : « un vrai changement
de calendrier fiscal reste à ±1 mois, il passe ». Vrai pour un décalage de
quelques jours, faux pour une fusion. Et l'écart de marge déjà enregistré au
registre — 7,3 % affiché, dernière barre à 13,9 % — n'est pas un défaut distinct
mais la **conséquence** de cette troncature : la marge vient de l'exercice réel,
la barre de 2019.

**La règle vivait en double** et n'a plus qu'une source. Recopiée dans
`edgar.construire_fonda` et dans `screener.fusionner_fonda`, c'est la panne des
listes recopiées de `_bouchons.py` appliquée à un filtre. L'extraction a été
vérifiée sans effet : les 148 blocs publiés ressortent identiques au caractère
près. Ses limites sont désormais écrites là où elle est écrite, et un test fige
le comportement d'aujourd'hui pour qu'un correctif ait à le regarder en face —
trancher demande de savoir ce que le greffe rend après 2019, et cette source est
bloquée ici.

### Trois barres fausses que rien ne regardait

Les trois autres défauts de L3Harris — 102, 189 et 420 M$ de chiffre d'affaires
entre des exercices à 5 005 et 5 012 — sont une erreur d'échelle au dépôt XBRL,
que la SEC ne corrige pas. **Aucun contrôle ne les voyait.** Le garde existant
écarte un résultat net « cent fois plus petit que ses DEUX voisins » et n'a pas
de symétrique sur le chiffre d'affaires ; il serait de toute façon aveugle ici,
deux des trois valeurs fausses étant voisines l'une de l'autre.

**Trouver la bonne forme a demandé trois essais, et les deux premiers sont
instructifs.** Comparer chaque chiffre d'affaires à la médiane de sa propre série
dénonce neuf titres — Meta 2010, Tesla 2009-2012, PDD, Regeneron : des jeunesses
parfaitement réelles. Une règle de voisinage immédiat, elle, ne voit pas un creux
de trois ans. Ce qui distingue l'erreur de la croissance n'est pas d'être bas,
c'est d'être **bas entre deux hauts** : une société qui grandit ne redescend pas.
Le contrôle cherche donc un creux INTÉRIEUR, encadré des deux côtés par des
exercices dix fois plus gros. Sur les 148 fiches, cette forme ne désigne que
L3Harris.

Les zéros en sont exclus, et c'est écrit plutôt que tu : zéro n'est pas un ordre
de grandeur en dessous, il n'a pas d'échelle. AST SpaceMobile publie 0 en 2023
entre 14 et 4, et c'est une société pré-revenu dont le chiffre d'affaires est
réellement nul cette année-là. Le détecteur se teste lui-même sur ces six
formes : une sentinelle dont on ne connaît pas les fausses alarmes n'en est pas
une.

### Les quinze fiches « inatteignables » étaient la page d'accueil

Le registre des défauts connus portait quinze fiches complètes — note, série
d'exercices, texte éditorial payé à l'API — qu'aucun chemin du site n'était censé
atteindre. La consigne était de comprendre pourquoi le nettoyage les avait
épargnées avant d'en supprimer une seule. Il ne les avait pas épargnées : **la
purge de `publier_charts` est totale**, tout `.json` que le run ne réécrit pas
est supprimé. Ces quinze-là étaient présentes parce qu'elles avaient leur place.

**Ce sont les membres du top 30 qui n'appartiennent à aucun thème.** Le périmètre
de publication du screener vaut `thèmes ∪ top 30` ; le dossier `charts/` contient
exactement 148 fichiers, soit cette union au titre près, sans orphelin ni
manquant. Le contrôle, lui, ne lisait que `universe.json` — les thèmes — et
ignorait `watchlist.json`, c'est-à-dire la watchlist principale, c'est-à-dire la
page d'accueil. Il dénonçait comme inatteignable ce qui s'ouvre d'un clic depuis
l'écran d'entrée du site. Les supprimer aurait privé le top 30 de ses graphes et
de quinze textes à repayer.

**Une fiche n'existe que dans une watchlist.** Le front route sur
`#/w/<watchlist>/<TICKER>` : l'adresse d'une fiche porte la liste qui la
contient. C'est la clé des deux moitiés du défaut, et le contrôle le dit
désormais dans ces termes.

**Le second trou, lui, est réel — et le motif était faux.** Neuf lignes détenues
n'ont pas de fiche : non pas parce qu'un fichier manque, mais parce qu'elles
n'appartiennent à aucune watchlist et qu'aucune URL ne peut donc les désigner.
Les ajouter au périmètre de publication produirait des fichiers que rien
n'ouvrirait. Il manque une route, ou une watchlist « portefeuille » — c'est une
décision de conception, pas un correctif, et le registre la garde en attendant
avec le bon diagnostic.

### Un commentaire ne s'exécute pas : la perte silencieuse de champs devient un test

Deux fois, un dictionnaire reconstruit de zéro a fait disparaître des données
déjà publiées. `proj` le 07/08 : 96 fiches sur 97 privées de leur trajectoire.
`injections` le 10/08 : les deux versements de 10 000 €, seules données qui
distinguent un virement d'un rendement. Les deux fois, un commentaire prévenait
juste au-dessus du code fautif — « tout nouveau champ doit être ajouté ICI ».
Les deux fois, l'avertissement n'a pas suffi. Un commentaire ne s'exécute pas.

**Deux gardes, et les deux côtés sont dérivés.** Pour `portfolio.json`, les clés
publiées se lisent dans le fichier et les clés réécrites s'extraient de l'arbre
syntaxique de `portfolio_agent.py` : aucune liste de noms de champs n'est tenue à
la main. Pour les blocs `fonda`, la garde est comportementale — on rejoue
`fusionner_fonda` sur chacun des 148 blocs réellement publiés, passé comme ancien
*et* comme nouveau, et ce que le run courant produit doit ressortir intact.

**Pourquoi la seconde n'est pas un doublon.** Un garde-fou générique existait
déjà pour `fonda`, mais il éprouve un bloc écrit à la main contre une liste
`CHAMPS` elle aussi écrite à la main : il prouve que la fusion conserve les
champs dont quelqu'un s'est souvenu. Le jour où un champ apparaît dans les
données sans que cette liste soit mise à jour, il reste vert pendant que le champ
se perd. C'est exactement la leçon de `tests/_bouchons.py` — « une liste recopiée
n'est pas une liste : c'est deux listes qui divergent ».

**Les deux gardes ont été éprouvées en retirant la ligne fautive.** Sans la
recopie de `injections`, la première rougit sur `perdus : ['injections']` ; sans
celle de `proj`, la seconde rougit sur les 148 fiches. Un test vert qui ne peut
pas rougir ne prouve rien.

**Une fuite trouvée au passage.** `last_known_vix_updated_at` était écrit chaque
soirée ouvrée par `update_prices.py` et jeté chaque lundi par le run
hebdomadaire : le champ clignotait, présent six jours sur sept, sans que personne
le lise. Le run hebdomadaire le reporte désormais, avec la convention exacte de
son autre écrivain — on date le run qui a constaté une valeur, et à défaut on
reporte l'estampille précédente plutôt que d'en inventer une.

### Le registre des versements avait été restauré depuis le mauvais commit

La performance publiée affichait 34,73 % quand le calcul du projet lui-même
donnait 32,94 %. L'écart avait été attribué au registre des versements manquant
au moment du calcul, et le chiffre laissé en l'état — prudence justifiée : c'est
le nombre le plus important du site. La reconstitution commit par commit montre
que la conclusion était inversée. **C'est 32,94 % qui était faux, et 34,73 % qui
avait raison.**

**Deux commits du 03/08, dans cet ordre, expliquent tout.** `acb77ed` introduit
la pondération par le temps ; le versement du 3 août y porte `capital_post:
33509.9`, sous la sémantique d'alors — un versement compte immédiatement. Puis,
le même jour, `457c23d` introduit « un versement reste hors périmètre jusqu'à
disposition » et **rétracte explicitement cette valeur** : `capital_post` repasse
à `null`, et `effective_le` apparaît. Les deux relevés suivants (30,64 % le 3
août, 33,93 % le 8) se recalculent au centime avec le versement en attente : le
registre était sain.

Le run hebdomadaire du 10/08 est le premier run d'agent après le versement.
Il a donc fait ce que la doctrine prescrit — estampiller le versement, qui entre
dans le périmètre à partir du moment où l'agent peut en disposer — et publié
34,73 %. C'est au moment d'écrire qu'il a perdu le registre.

**La restauration est allée chercher `acb77ed`, c'est-à-dire l'état d'avant la
rétractation.** Elle a réintroduit une valeur que le projet avait retirée le jour
même. Le message de commit dit « ce sont les originales » : elles le sont, mais
d'une sémantique périmée. 32,94 % n'était pas la révélation d'une erreur, c'était
la conséquence d'une restauration à la mauvaise source.

**`effective_le` n'était pas introuvable non plus.** La valeur d'`inj1`,
`2026-05-05`, est écrite dans le dépôt de `457c23d` jusqu'au relevé du 8 août.
Celle d'`inj2` est la date du run qui l'estampille — `2026-08-10`, exactement ce
que `_inj["effective_le"] = today` aurait inscrit. Rien n'a été inventé : les
deux valeurs sont relevées, pas reconstituées.

**Il reste un centime, et il est assumé.** L'agent estampille sur le capital
*pré-transactions* mais publie la performance sur le capital *post-transactions*,
et un relevé de prix sépare les deux. Le capital de l'estampille n'a jamais été
persisté ; les données publiées le bornent à `[34600,77 ; 34607,08]`. La seule
valeur mesurée et publiée disponible pour cette date est le capital de clôture,
`34599.69`, qui donne 34,72 %. Choisir dans la borne une valeur qui retombe sur
34,73 % aurait été fabriquer un nombre pour qu'il colle — le trou plutôt que le
faux, y compris quand le trou vaut un centime. Les grandeurs dérivées suivent
dans le même mouvement : performance brute 35,08 → 35,07, écart au MSCI 19,04 →
19,03. Le drawdown et la performance post-liquidation ne bougent pas. La tuile du
site affiche une décimale : le lecteur ne verra pas la différence.

**Ce que ça a évité.** `update_prices.py` recalcule la performance depuis le
registre à chaque soirée ouvrée. Le registre erroné étant déjà sur `main`, le run
de 22:00 aurait publié 32,9 % sur le site.

### Une watchlist robotique : la question n'était pas « qui fabrique des robots »

Cinquième liste du site. La demande était double — humanoïdes et robotique
industrielle avancée — puis précisée d'une phrase qui change tout : **« qui sont
les acteurs les mieux placés pour bénéficier de l'essor des robots ».** Ce n'est
pas la même question que « qui fabrique des robots », et la liste ne s'écrit pas
pareil.

**La règle d'entrée est le thème.** Entre une société si une hausse du nombre de
robots vendus se lit dans ses comptes. C'est un critère de concentration, pas de
taille, et il coupe dans les deux sens. Il fait entrer des spécialistes de
quelques milliards de dollars que le seuil habituel du projet écarterait ; il
fait sortir Emerson, Parker Hannifin, AMETEK, Analog Devices, Infineon, et
jusqu'à Nvidia dont la gamme robotique est un rayon de magasin à côté du centre
de données. Quatre cas ont été tranchés dans ce sens après une validation sans
erreur le jour même : Teradyne — qui possède pourtant Universal Robots, premier
fabricant mondial de cobots — Mitsubishi Electric, Denso et Sumitomo Heavy,
inventeur du réducteur Cyclo. Sans ce garde-fou, le thème redevient un panier de
conglomérats industriels, c'est-à-dire une liste qui ne répond à rien. Un test
le vérifie, et un autre vérifie qu'aucun de ces exclus n'est pour autant
« écarté » du projet : tous restent scorés et candidats à la watchlist
principale, distinction que l'incident GlobalFoundries avait rendue explicite.

**Le cœur de la thèse est mécanique.** Une articulation de robot, c'est un
moteur, un réducteur qui transforme sa vitesse en couple, un guidage et des
roulements — et le réducteur est le point le plus étroit de toute la chaîne.
Ces positions-là ne se contournent pas en un exercice : elles tiennent à la
métallurgie et à la rectification, pas à un brevet qui expire. C'est ce maillon
qui justifie la dérogation de taille, écrite dans le texte que le lecteur voit :
celui qui détient la pièce que tout le monde doit lui acheter est une petite
société, et un plancher de capitalisation aurait masqué exactement
l'information qu'on cherchait.

**Sur les humanoïdes, la liste dit surtout ce qu'on ne peut pas acheter.** Les
constructeurs les plus avancés ne sont pas cotés ; celui qui s'est introduit en
bourse le 6 août 2026 l'a fait à Shanghai, hors de portée d'un courtier
européen. Restent deux pure players asiatiques de taille modeste et deux
constructeurs automobiles chez qui le robot ne pèse rien au compte de résultat.
C'est une exposition de conviction, et le champ `biais` le dit avant lecture.

Deux autres avertissements y figurent, pour la même raison : le thème est
**aussi un pari sur le yen**, puisque l'essentiel des pièces critiques cote à
Tokyo, et il **recoupe l'infrastructure de l'IA** sur ses couches basses — les
détenir deux fois n'est pas se diversifier.

Un titre manque et son absence est une information : **KUKA**, l'un des quatre
grands du robot industriel, racheté par Midea puis sorti de la cote de Francfort
en 2022. Son symbole ne rend plus d'historique. Le maillon des constructeurs en
compte trois au lieu de quatre pour cette seule raison.

### Deux tables de devises côte à côte, une seule tenue à jour

Le support de Taipei et Hong Kong avait été ajouté le matin même au contrôle de
l'ordre de grandeur des prix — et **oublié dans la table de conversion des
capitalisations, six lignes plus bas.** Le défaut silencieux à la parité du
dollar rendait l'oubli invisible : HIWIN ressortait à 136,9 Md$ au lieu de ~4,4
et UBTech à 45,3 au lieu de ~5,8.

L'erreur allait **dans le sens qui supprime l'avertissement** : deux titres sous
le seuil des 25 Md$ passaient pour assez gros, c'est-à-dire exactement le
contrôle qu'on croyait exercer. Même famille que le bug ORSTED.CO. Trois
correctifs : la table monte au niveau du module pour être lisible par un test,
une devise inconnue devient une **erreur** au lieu d'une parité implicite, et
trois invariants exigent que toute devise détectée soit bornée *et* convertible,
les deux tables couvrant le même jeu.

Le test qui les porte a lui aussi changé de nature : son échantillon de tickers
n'est plus écrit à la main mais **dérivé de l'univers réel des thèmes**. Une
liste choisie par le rédacteur du test ne contient jamais le cas qu'il n'a pas
vu venir — c'est ainsi que `.TW` et `.HK` ont manqué jusqu'au 8 août, alors
qu'un thème allait les introduire.

### Une watchlist quantique, et ce qu'elle a d'inconfortable

Quatrième liste du site. Elle a changé trois fois de forme dans la journée —
dix titres publiés sur vingt-quatre déclarés, puis vingt sur vingt-neuf, puis
les seuls **pure players**, sur demande du propriétaire — et c'est la dernière
version qui dit le mieux le secteur.

**Il n'existe au monde que dix pure players quantiques cotés, et six ne sont pas
encore notables.** Cinq se sont introduits en bourse en 2026 et n'ont pas les
200 séances qu'exigent la moyenne mobile 200 jours et le RSI ; le sixième pèse
0,4 Md$ sans objectif de cours consensus. La liste en publie donc **quatre**, et
son plafond reste à dix : ce n'est pas une fiction, c'est un rendez-vous. Les
cinq introductions franchiront le seuil entre décembre 2026 et avril 2027 et
entreront sans que personne ne touche au fichier. Une watchlist a le droit
d'être courte quand son sujet l'est — c'est le seul thème qui déroge à la règle
des vingt titres déclarés, et il la mérite : un secteur qui compte dix sociétés
cotées ne peut pas en déclarer vingt sans mentir.

**Le passage par vingt titres n'aura pas été inutile**, et il vaut d'être noté
pour la mécanique qu'il a révélée. Le propriétaire avait signalé qu'« il manque
pas mal d'acteurs clés ». Le diagnostic était juste, la cause
instructive : les acteurs ne manquaient pas au périmètre, ils étaient déclarés
et **masqués par le bornage**. À dix, la coupe tombait à 51 points et emportait
d'un seul geste trois des quatre sociétés dont le quantique est le métier, IBM,
les deux japonais et le seul fabricant coté de réfrigérateurs à dilution. Un
bornage trop serré ne sélectionne plus, il ampute — un test encadre désormais
le rapport entre déclaré et publié. Cinq titres sont venus s'ajouter, dont un
maillon neuf, *matériaux et fonderie* : le silicium 28 purifié isotopiquement
de Soitec, sans lequel un qubit de spin perd sa cohérence, et la fonderie qui
grave les puces photoniques 300 mm de PsiQuantum.

Le secteur pose un problème que les autres n'ont pas : **il n'y a presque rien
à noter.** Les sociétés dont c'est le métier perdent de l'argent et ne pèsent
pas les 25 milliards de dollars que le projet exige d'ordinaire ; celles qui
construisent vraiment des machines sont des conglomérats où le quantique ne
fait pas un centième de l'activité. La version finale tranche en faveur des
premières et **assume de ne montrer qu'elles** : à quatre titres, une structure
en maillons serait un décor, et elle reviendra si la liste se remplit. Ceux qui
vendent au secteur — cryogénie, lasers, instruments, fonderie — sont sortis du
thème mais **restent dans l'univers du screener**, sans quoi douze sociétés
validées perdraient leur note et sept fiches publiées deviendraient orphelines.
Le champ `biais` dit au lecteur qu'ils existent et qu'ils sont, aujourd'hui, les
seuls du sujet à facturer quelque chose.

Le champ `biais` prévient avant lecture que **la grille ne s'applique pas** aux
sociétés sans bénéfice : un score bas n'y dit pas « mauvaise société », il dit
« rien à mesurer ». Et les deux dérogations sont écrites plutôt que cachées —
le seuil de taille levé pour les seuls pure-players, l'historique de moins de
cinq ans de plusieurs titres. Deux tests vérifient que ces phrases restent
dans le texte.

**Quatre absences mesurées, pas oubliées.** Le secteur a connu quatre
introductions en bourse en 2026 : Quantinuum le 4 juin, Xanadu le 23 mars,
Horizon Quantum le 20 mars, Infleqtion le 17 février. Confrontées à Yahoo le
8 août, toutes les quatre sont sous les **200 séances** qu'exigent la moyenne
mobile 200 jours et le RSI — Quantinuum n'en a que 45. Le screener les
écarterait au run et la liste serait publiée amputée, en silence. Elles sont
inscrites au registre des écartés avec la date où leur historique suffira, la
première en décembre 2026. Quantinuum est l'absence la plus coûteuse : c'est le
plus gros pure-play coté, et son actionnaire Honeywell reste dans la liste.

Côté mécanique, le bornage `top` devient général. Il n'existait que pour le
filtre PEA ; un thème de thèse peut vouloir la même chose. La couverture
continue de se mesurer **avant** bornage, sinon le thème se déclarerait
« dégradé » par sa propre définition.

---

### Vingt-six défauts trouvés avant le premier vrai run

Le code du tableau des marchés et de la sonde n'avait jamais tourné : il devait
s'exécuter pour la première fois à 05h45 UTC, dans une Action, sans personne
pour le regarder. Cinq relectures adverses en parallèle, chaque défaut ensuite
attaqué par un sceptique chargé de le réfuter : **26 confirmés sur 33**.

**Ce qui aurait tué le post du matin**

- `import yfinance` était placé **au-dessus** du `try` : une résolution pip
  malheureuse et l'ImportError remontait jusqu'à `main()`, tuant le post entier
  alors que la doctrine dit qu'un relevé absent n'est pas une panne. Le
  workflow n'aidait pas, il installait ses dépendances sans version au lieu de
  lire `requirements.txt` comme tous les autres. Les deux sont corrigés.
- L'étape *Publier* n'avait pas `if: always()` : le post est écrit sur le
  disque **avant** elle, et un échec de la réparation photo (réseau, sans borne
  de temps) jetait un post déjà écrit et validé.
- Un champ `marches` rendu en liste plutôt qu'en texte faisait *planter* la
  validation, donc perdre la seconde tentative.

**Ce qui aurait publié un chiffre faux, et pour toujours**

Le job tourne à **05h45 UTC**. Taipei a clôturé quinze minutes plus tôt, le
bitcoin cote sans interruption depuis minuit, New York et Paris en sont encore
à la veille. Prendre partout « les deux dernières clôtures » mélangeait donc
**deux séances sous un seul en-tête de date** : un −6 % de TSMC du matin même
aurait remporté le concours du plus fort mouvement contre les +1 % de la veille
à Wall Street, et le post, gelé, l'aurait attribué à vendredi pour toujours. Le
même mécanisme faisait gagner un titre suspendu tous les matins, avec sa
dernière variation d'avant suspension.

Le relevé aligne maintenant **tout sur une seule séance** : la dernière clôture
des indices actions fixe la référence, chaque instrument est ramené à cette
date, et toute ligne qui n'a pas de clôture ce jour-là est écartée. Une place
fermée pour un jour férié n'a pas de niveau à donner ce matin. En prime, une
variation calculée à travers un trou de plus de six jours n'est plus une
variation du jour : c'est une ligne en moins.

**Ce qui se contredisait à l'écran**

La pastille annonçait « plate » en dessous de 0,005 % — flèche « — », gris — et
le texte à côté affichait `+0,00 %`, exactement le signe que le code refusait
par ailleurs de mettre sur un zéro. Le seuil est maintenant nommé et partagé
par les deux implémentations, et le test qui les compare le couvre.

**La sonde**

Une seule sonde qui levait détruisait les 202 autres et le rapport n'était
jamais écrit. Un horodatage en millisecondes tuait le run entier. Un run filtré
par `--genre` écrivait le rapport **complet**, que le workflow commitait
par-dessus les 203 fiches du run précédent. Les flux RSS 1.0 et ceux qui datent
en Dublin Core étaient comptés morts. Le genre déclaré primait sur le contenu
réel, donc quatre sources vivantes ressortaient « illisibles ». La clé Finnhub
suivait les redirections vers d'autres domaines. Et l'entrée `genre` du
dispatch était interpolée directement dans un `run:` doté de `contents: write`.
Tout est corrigé.

---

### Le garde qui aurait supprimé un matin

Une relecture adverse du code de la veille, avant son premier vrai run, a
trouvé un défaut **bloquant** dans le garde que je venais d'écrire.

Le prompt demande de citer les niveaux du tableau. Or le niveau d'un taux
s'écrit avec un pourcent : « le Treasury 10 ans termine à **3,872 %** ». Le
garde ne connaissait que les *variations*, il aurait rejeté cette phrase
parfaitement juste. Deux rejets d'affilée, sortie en erreur, **pas de post du
matin**. Un garde qui refuse le juste coûte plus cher que pas de garde du tout.

Quatre autres défauts de la même famille, corrigés dans la foulée et chacun
couvert par un test qui vire au rouge si on retire la correction :

- **« Le Nasdaq recule de 3,46 % » est juste pour −3,46** : c'est le verbe qui
  porte le signe, l'exiger en chiffres rejetterait du bon français. Mais
  « +3,46 % » sur la même ligne est une inversion, pas une tournure. Le signe
  **écrit** engage, le signe sous-entendu non.
- Les **points de base** étaient reconnus mais jamais convertis : « 22 points de
  base » était comparé à 0,22 et rejeté.
- La tolérance d'arrondi est devenue **relative** : un gros mouvement s'arrondit
  plus grossièrement, « 29,5 % » pour 29,45 % est du français correct.
- Une **section rendue en texte nu** au lieu d'un objet faisait *planter* la
  validation — donc perdre la seconde tentative et le post.

Et une promesse tenue avec deux mois de retard : le commentaire de `main()`
annonçait depuis toujours que la seconde tentative « transmet ses défauts au
modèle ». C'était faux, elle relançait le même prompt à l'identique et jouait
au tirage au sort. Elle fait maintenant ce qu'elle disait.

---

### Le point du matin chiffre enfin les marchés

Il les racontait sans jamais les mesurer : on lisait « les indices ont bien
terminé » sans savoir de combien. Les dépêches ne le disent pas de façon
fiable non plus, elles datent d'heures différentes et se contredisent d'une
agence à l'autre. Le seul moyen honnête d'écrire un niveau est de le relever
soi-même, alors le post relève désormais neuf instruments (S&P 500, CAC 40,
Nasdaq, Euro Stoxx 50, Treasury 10 ans, or, Brent, euro/dollar, bitcoin) et en
affiche les six premiers qui ont répondu.

**La septième ligne est celle qu'une newsletter généraliste ne peut pas
écrire** : le plus fort mouvement de la watchlist principale ce jour-là,
cliquable vers sa fiche.

Quatre décisions structurent le bloc :

- **Le tableau est gelé dans le post.** Servi depuis un fichier partagé, il se
  réécrirait chaque matin et rendrait faux tous les posts archivés, qui
  annoncent « à la clôture de la veille » sous des chiffres d'un autre jour.
- **Jamais de demi-tableau.** Sous quatre instruments, pas de tableau du tout :
  une ligne manquante ne se voit pas, le lecteur croit que le Nasdaq n'a pas
  bougé, pas qu'on n'a pas su le lire.
- **Le commentaire ne cite que des chiffres mesurés.** Le modèle reçoit le
  tableau et l'ordre de le commenter ; un pourcentage qui ne correspond à
  aucune ligne, à cinq centièmes près, fait rejeter le post. C'est la règle des
  sections sans source, appliquée au seul bloc qui n'a pas de dépêche pour le
  tenir.
- **Le 10 ans est américain et le libellé le dit.** L'OAT parlerait davantage à
  un lecteur français, mais aucune source gratuite ne la donne de façon fiable,
  et écrire « OAT » au-dessus d'un Treasury serait un mensonge d'étiquette pour
  gagner en couleur locale.

Le formatage français (fine insécable, virgule décimale) existe des deux côtés,
en Python pour le prompt et en JavaScript pour la page, parce que le post
stocke des **nombres** et non des chaînes déjà mises en forme — sinon un post
archivé garderait à jamais la typographie du jour de sa parution. Un test
exécute réellement le JS de la page et compare les deux, valeur par valeur. Il
a trouvé sa première divergence en naissant : Python écrivait « +0,00 % », un
signe qui annonce une hausse et n'en montre pas.

---

### Deux cent trois sources d'actualité, et une sonde pour trancher

Le point du matin lit **une** source. Le 7 août, elle a rendu **six** dépêches
exploitables : de quoi écrire trois paragraphes, pas une lettre matinale. Il en
faut d'autres, et la tentation est d'en choisir une liste qui a l'air bien.
C'est exactement ce qu'il ne faut pas faire : la moitié des flux RSS de la
presse économique ont été fermés, mis derrière un mur payant ou déplacés depuis
dix ans, et une URL de 2019 rend un 404 aujourd'hui sans que personne ne s'en
aperçoive.

On mesure donc avant de choisir. `tools/sonde_actus.py` tape **203 candidats**
sur 144 domaines (presse française et francophone, agences anglophones, sources
primaires de banques centrales et d'instituts statistiques, fils de communiqués,
et du hors-marchés pour l'accroche du matin), et écrit un rapport chiffré par
source : code HTTP, articles, combien datent de moins de 24 h, combien portent
un vrai résumé, combien portent une image, trois titres en échantillon.

Elle **ne branche rien**. Choisir une source est une décision éditoriale, pas
le sous-produit d'un test technique. Et elle **ne sort jamais en erreur** :
une source morte est une information, pas une panne. Quinze services à clé
d'API (Alpha Vantage, marketaux, Polygon, Tiingo, FRED…) sont listés à part,
non testés et dits comme tels — les sonder sans clé rendrait un 401 qui ne
dirait rien de leur qualité.

Elle existe comme workflow parce que le proxy de l'atelier bloque tout :
203 candidats testés en local, **203 à zéro**.

---

### Un pictogramme au-dessus de chaque onglet

Quatre glyphes au trait, dessinés à la main dans un `viewBox` de 24 : une liste
pour Watchlists, un journal pour Actualités, un livre ouvert pour Apprendre,
une mallette pour Portefeuille IA. Trois décisions les gouvernent.

Le **trait, pas l'aplat** : ils sont en `stroke:currentColor`, donc ils prennent
automatiquement la couleur de leur onglet, gris au repos et blanc sur l'actif.
Une icône en `fill` aurait demandé quatre règles de couleur de plus et aurait
divergé du reste au premier changement de palette. Un test refuse désormais
toute couleur figée dans le balisage.

La **hauteur est un budget** : l'en-tête est fixe, et quatre réglages se calent
dessous (`.rail`, `.stage`, et les marges d'ancre des deux pages longues). Le
libellé est donc passé en `line-height:1`, et l'icône à 19 px après un premier
jet à 16 px jugé trop discret : l'en-tête gagne **neuf pixels**, pas
vingt-cinq, et les quatre décalages ont suivi.

L'**icône est décorative, le nom porte le sens** : `aria-hidden` sur le SVG, le
libellé reste du texte. Un lecteur d'écran annonce « Watchlists », pas
« image ».

Le journal a perdu une de ses trois lignes de texte en cours de route : à 16 px
elles étaient à 2,3 px l'une de l'autre et fusionnaient en pâté gris sur un
écran non rétina.

---

### « FY25 » plutôt que « 25 » sur les axes

Les années à deux chiffres gagnaient de la place mais perdaient leur nature :
rien ne disait que « 25 » était un exercice comptable. Le préfixe **FY**, la
notation standard des rapports financiers, ne coûte rien ici : le pas
d'affichage budgétait déjà quatre caractères depuis « 2025 » et n'avait jamais
été réduit. « FY25 » en fait exactement quatre. Mesure sur les 93 fiches à
390 px, 269 vues (annuel, trimestriel, PER) : **aucun chevauchement, aucun
débordement, aucune étiquette perdue**. En trimestriel, rien à ajouter :
« T1 25 » se désigne déjà lui-même.

---

### Le point du matin publié sans photo, dans le silence

Le post du 7 août est sorti sans image, le job vert, et rien dans les journaux.
Cause démontrée : **cinq matins d'affilée sur le sujet « marches »** (3, 4, 5,
6 et 7 août). Les trois requêtes Commons du sujet avaient donné leurs bonnes
images les quatre premiers jours ; le cinquième, la mémoire des photos parues
les écartait toutes, elles et leurs quasi-doublons, et il ne restait que du
fond de panier. Un sujet qui domine quatre séances n'est pas un cas rare :
c'est un marché qui vit la même histoire une semaine durant.

Le pire n'était pas le trou, c'était le silence. `infos()` refuse une image
pour trois raisons (échec réseau, moins de 900 px, licence non libre) et
n'en disait **aucune** ; `illustrer()` abandonnait après six essais sans
imprimer une ligne. Quatre corrections :

- **six requêtes par sujet** au lieu de trois, pour tenir la semaine ;
- **douze candidats essayés** au lieu de six, avec le compte des candidats
  trouvés et retenus ;
- `infos(..., bavard=True)` **dit lequel des trois refus** s'applique, image
  par image (le silence reste le défaut : les balayages de fiches l'appellent
  des centaines de fois) ;
- un `::warning::` dans le job **et une réparation automatique** : chaque run
  reprend les posts quotidiens des dix derniers jours restés sans photo. Un
  matin sans image n'a aucune raison de le rester à vie, le vivier a bougé.

---

### L'analyse IA et la fiche ne parlaient pas au même rythme

Question posée : ce que dit l'IA doit coller aux données de la fiche, sinon
« on se trompe quelque part ou la manière de calculer n'est pas la même ».
Vérification faite sur les 104 fiches, **216 nombres confrontés** un à un à ce
que la fiche affiche, avec les archives hebdomadaires comme arbitre :

| verdict | nombre |
|---|---|
| identiques | 116 |
| **périmés** (justes le jour où ils ont été écrits) | 95 |
| invérifiables (grandeur absente des archives) | 20 |
| **inventés** | **0** |

Aucune des deux causes soupçonnées n'est la bonne. Le générateur envoie à l'IA
**exactement les champs que la fiche affiche**, avec la période collée à chaque
grandeur (« croissance CA = dernier trimestre publié en glissement annuel »,
« marge nette = TTM ») et la consigne de n'inventer aucun multiple absent : il
n'y a pas de divergence de définition. Et l'IA recopie fidèlement : zéro nombre
inventé sur 216.

La vraie cause est une troisième, plus banale et plus tenace : **le texte et la
donnée se rafraîchissent sur deux horloges différentes.** Le texte n'est réécrit
que si le score, le croisement ou le z-score bougent — décision de coût
délibérée, un appel API par point de RSI n'aurait aucun sens. Mais le RSI et le
drawdown, eux, sont recalculés **tous les jours** avec les cours. Un « RSI à
30 » juste le jour où il est écrit affronte un RSI à 39 trois séances plus tard.
Quant aux 78 fiches sur 104 dont le palier de score a bougé depuis leur
rédaction (écart médian 9 points, maximum 43 : Goldman Sachs 30 → 73, Allianz
30 → 71), elles datent toutes d'avant la note v4 et le prochain run éditorial
complet les reprendra.

Correction de fond : **ce qui est trop volatil pour déclencher une réécriture
est trop volatil pour être chiffré.** Le RSI et le drawdown restent fournis à
l'IA — ils cadrent le ton, survente ou surchauffe, proche ou loin des plus hauts
— mais ils sont désormais marqués « NE PAS CHIFFRER » et explicitement interdits
de nombre dans la prose. Deux sentinelles de test comptent les citations
restantes (37 RSI, 15 drawdowns) et n'autorisent que la descente.

---

### La fiche d'Adyen se contredisait elle-même

Elle notait la croissance à **+19,2 % par an** et écrivait, deux centimètres
plus haut, « le chiffre d'affaires a **reculé de 33,3 % par an** ». Le même
fichier disait deux choses contraires, et la fausse était celle qu'on lisait.

Le fichier se dénonce tout seul :

| exercice | CA | résultat net | BPA | actions impliquées |
|---|---|---|---|---|
| 2022 | **8 936** | 564 | 18,17 | 31,0 M |
| 2023 | **1 863** | 698 | 22,41 | 31,1 M |
| 2024 | 2 226 | 925 | 29,59 | 31,3 M |
| 2025 | 2 647 | 1 063 | 33,61 | 31,6 M |

Bénéfice, BPA et nombre d'actions sont parfaitement continus : il n'y a **ni
scission ni changement d'entité**, sinon eux aussi sauteraient. Seule la ligne
du haut change de sens. Adyen publie son volume encaissé en 2022 — qui inclut
l'interchange et les frais de réseau reversés aux banques et aux schémas — puis
son revenu net à partir de 2023. Preuve décisive, dans le même fichier : le
consensus attend **2 858** en 2026. La source place donc elle-même « le »
chiffre d'affaires d'Adyen sur l'échelle basse ; sa ligne 2022 contredit ses
propres estimations.

Le garde existait déjà — `note_v4.apres_rupture`, seuil d'un tiers — mais il ne
protégeait que **le calcul de la note**. Le dessin et les phrases, eux, ne
s'en servaient pas. Ils s'en servent maintenant, avec le même seuil, la même
asymétrie (une marche montante est conservée, c'est la signature de
l'hypercroissance) et la même restriction au seul chiffre d'affaires. Une
série tronquée le **dit** désormais, avec ses deux chiffres.

Deux séries concernées sur 93 : Adyen et Western Digital (retraitement de la
cession de SanDisk). Aucun vrai recul touché — Micron 2023, Booking 2020,
ASML 2009 passent intacts.

### Un accident comptable ne décide plus de l'échelle du PER

Cisco 2018 sort à **2 129×** au milieu d'un historique compris entre 14 et 28×.
Le chiffre est exact : la réforme fiscale américaine a fait tomber son bénéfice
de 9,6 Md$ à 110 M$ pendant que son chiffre d'affaires montait. Ce n'est pas une
donnée fausse, c'est un dénominateur disparu un an.

L'échelle logarithmique était déjà là et ne suffisait pas : mesuré, la courbe
qu'on vient lire se tassait sur **13 % de la hauteur** (Booking, 1 547× en 2020,
sur 36 %).

**Seuil par l'écart, jamais par la valeur.** Un plafond du genre « au-dessus de
100× » serait faux : ARM vit à 175–431× avec 20 % de marge nette, Nebius à 208×,
Equinix à 56–200× — ce sont de vraies valorisations. Ce qui trahit l'accident,
c'est l'**isolement** : le sommet vaut cinq fois le point suivant, quand une
valorisation chère est entourée de valorisations chères. Deux points au plus
peuvent sortir du cadre.

**Pas de symbole de plus.** Deux essais écartés avant le bon. Le premier
dessinait le point hors cadre à la hauteur du plus haut point mesuré — 2 129× et
28× au même niveau, pire que le problème d'origine. Le second lui donnait un
chevron, une bande réservée et une entrée de légende à lui : *« c'est du bruit,
on normalise avec le reste »*, et c'est juste — un exercice dont le multiple est
inexploitable a **déjà** sa convention ici, la croix rouge de l'axe, posée pour
les pertes et les BPA manquants.

Cisco 2018 rejoint donc Micron 2023 : même croix, même entrée de légende, même
coupure du trait. Seul le motif change, et il est dans la bulle avec la valeur
exacte — « 2018 : multiple de 2 129× — le bénéfice de cet exercice est tombé
près de zéro ». Le graphique de Cisco se lit maintenant de 15 à 28× sur toute
la hauteur, et la légende porte une entrée de moins qu'avant.

Six graphiques concernés sur 84, un seul exercice chacun : Cisco, Booking,
Intel, Lumentum, Micron, NetApp — tous à moins de 3,2 % de marge nette cette
année-là. Aucune société durablement chère touchée : ARM, Equinix, Netflix,
Nebius, Adobe et Cadence gardent tous leurs points.

### Six fiches disaient un trou sans dire pourquoi

TSMC affiche onze exercices de comptes et **aucun multiple historique** : sa
courbe de PER se réduisait à deux points estimés, sans un mot. Idem pour ASE,
Ferrari, Cameco, ABB et Vestas.

Le refus est le bon — ces sociétés publient leurs comptes dans une devise et
cotent dans une autre, et diviser un cours en dollars par un bénéfice en dollars
taïwanais donne un taux de change déguisé en multiple. Mais un trou muet se lit
comme une négligence. Il est maintenant énoncé, avec les deux devises nommées.

### Les légendes de photo redeviennent lisibles

Le même objet — la légende sous une illustration — sortait en **sept tailles
différentes** selon la page : de 0,40 rem à 0,58 rem, soit **6,9 px** au plus
petit. La ligne de crédit, celle qui porte l'obligation CC-BY, était la plus
petite de toutes.

Toutes ramenées à deux valeurs. Premier réglage à 0,62 / 0,55 rem, jugé trop
gros par le propriétaire — c'est la LÉGENDE d'une image, elle n'a pas à
concurrencer le texte. Réglage retenu : **0,54 rem pour la légende, 0,50 rem
pour le crédit**, mesuré à 8,64 px et 8 px, identiques sur bureau et sur
mobile, identiques sur les trois pages. Toujours nettement au-dessus des
6,9 px d'origine, sans peser dans la page. Balayage de contrôle : 93 fiches
× 3 largeurs, aucun débordement, aucun texte rogné.

### Le bandeau est enfin le même objet sur les quatre onglets

signal.css s'ouvre sur « une seule source de vérité ». Ce n'était pas vrai.
Mesuré au navigateur sur les quatre onglets :

| | Watchlists | Actualités | Apprendre | Portefeuille |
|---|---|---|---|---|
| hauteur du bandeau | 64 px | 69 px | 72 px | 72 px |
| logo | 28 px | 30 px | 30 px | 30 px |
| nom de la marque | 1,3 rem | 1,3 rem | 1,4 rem | 1,4 rem |
| nav sur mobile | 10,6 px | 10,6 px | 11,5 px | 11,5 px |
| hauteur d'un lien de nav, mobile | **12 px** | 17 px | 28 px | 28 px |

Le logo changeait donc de taille et le bandeau sautait de 8 px à chaque
changement d'onglet. Et sur mobile, les liens de navigation de deux onglets
faisaient **12 et 17 px de haut** : la police descendait avec la largeur, mais
rien ne tenait la cible tactile. C'est le rembourrage qui fait la cible, pas la
police — il est désormais posé à tous les paliers, et le plancher de taille
remonte de 0,66 à 0,72 rem.

Deux pages recopiaient localement `.brand`, `.brand-name`, `nav` et `nav a` ;
ces copies sont supprimées, les valeurs remontées dans signal.css. Le bandeau
mesure maintenant **72 px partout** sur bureau, **57 px partout** sur mobile,
avec des liens de **28 px** sur les quatre onglets.

Trois autres écarts trouvés en comparant, invisibles page par page :

- **Actualités déclarait `font-family:'Inter'` sans jamais charger la police.**
  Seul onglet rendu dans la police système depuis sa création.
- **Watchlists chargeait Inter sans la graisse 700 ni l'italique**, qu'elle
  utilise pourtant seize fois : le navigateur fabriquait un faux gras.
- **Trois onglets sur quatre n'avaient pas de favicon**, et la page d'accueil
  — l'URL la plus partagée — n'avait pas de `meta description`. Le pied de page
  d'Actualités n'avait ni la classe commune (donc 16 px au lieu de 11,8) ni le
  badge « Bêta ».

`tests/test_chrome.py` (27 vérifications) verrouille l'ensemble : aucune page ne
peut redéfinir le chrome partagé, les quatre doivent porter le même attirail, la
même requête de police, le même ordre de nav, la même mention légale.

### Une rupture de définition n'est pas une trajectoire

Le préambule de `tests/test_donnees.py` cite depuis sa création
« chiffre d'affaires en croissance de −33,3 % par an » pour Adyen. Rien ne le
vérifiait, et la phrase est **toujours publiée sur la fiche**.

Le défaut n'est pas que le chiffre baisse — Booking en 2020, ASML en 2009,
Micron en 2023 reculent pour de vrai. C'est un **changement de ligne comptable**
au milieu de la série : Adyen publie son volume traité en 2022 (8 936) puis son
revenu net à partir de 2023 (1 863). Nous racontons ce saut comme une
trajectoire d'entreprise.

La signature mesurable, qui n'accuse aucun des cas légitimes : la chute n'est
pas suivie d'un retour. Un creux cyclique remonte vers son niveau d'avant
(Micron 30,8 → 15,5 → 25,1 → 37,4) ; une redéfinition ne remonte jamais (Adyen
8 936 → 1 863 → 2 226 → 2 647). Le test est en place, tolérance 1 — le cas
connu passe, un deuxième fait échouer.

### Le PER « aujourd'hui » est retiré — il faussait vraiment

« Je trouve que ça fausse tout. » C'est exact, et au sens le plus concret.

Le losange ambre valait le cours du jour divisé par le bénéfice des **douze
derniers mois**. Sur une société qui sort à peine des pertes, ce dénominateur
glissant est minuscule et le multiple explose : Coherent affichait **158×** au
milieu d'un historique compris entre 22 et 35×. Un seul point pareil étire
l'échelle et écrase toute la courbe qu'on venait lire — les trois points
historiques se retrouvaient collés au bas du cadre. Le repère déformait ce
qu'il était censé éclairer.

Sans lui, la même fiche se lit de 22× à 61× et les points se distinguent. Le
losange avait été ajouté pour signaler le changement de base de cours entre les
exercices publiés (au cours de l'époque) et les estimations (au cours du
jour) : ce changement reste **énoncé dans la bulle de la légende**, là où il
n'a aucun effet sur l'échelle.

Le connecteur pointillé conserve sa règle : il ne part du dernier exercice
publié que si celui-ci est le dernier exercice **connu**. Sur Coherent, il
relie donc les deux estimations entre elles sans enjamber les trois années de
pertes — pas de continuité inventée.

### Trois textes de moins sur les chiffres publiés

**« publié en USD »** : la devise est déjà portée par chaque montant — « 403
Md$ » au survol des barres, dans les phrases de synthèse, dans les tuiles. La
répéter en tête de section était un doublon.

**« échelle log »** : elle se lit dans les graduations ; la nommer n'aidait que
celui qui savait déjà. Le choix de l'échelle, lui, reste documenté dans le
code, là où il se règle.

**La phrase « Trajectoire attendue »** disait quels exercices venaient du
consensus, lesquels de notre prolongation, et le motif de notre refus d'aller
plus loin. L'essentiel subsiste sans elle : le trait vertical sépare le publié
de l'attendu, les hachures distinguent les deux natures, et le relevé au survol
nomme chaque colonne — « consensus des analystes » ou « notre prolongation
arithmétique ».

**Ce qui est perdu, et il faut le dire** : le MOTIF du refus. Quand nous nous
arrêtons — Nebius, CoreWeave —, les barres cessent simplement, sans que rien
n'explique pourquoi. Le motif reste dans la donnée publiée (`ca_arret`), prêt à
revenir si l'absence gêne. Deuxième conséquence : la solidité du consensus
(nombre d'analystes, désaccord), ajoutée le matin même, n'a plus d'endroit où
s'afficher — elle continue d'être collectée, mais elle n'est plus lue.

### La note permanente sous le graphique de cours disparaît

« Trajectoire historique, pas une valeur intrinsèque. Méthode → » s'affichait
sous **chaque** graphique, sur chaque fiche. Un rappel qui ne varie jamais
finit par ne plus être lu.

La mise en garde n'est pas perdue pour autant, elle est portée là où elle
mord : la ligne de métriques dit « **si retour à la tendance** », au
conditionnel, et l'avertissement de surcote s'affiche vraiment — 260 caractères
sur Samsung, 346 sur Adobe — quand le cours s'écarte assez pour que ça compte.
La classe CSS qui n'habillait plus que cette phrase part avec elle.

### L'illustration reste en tête de fiche

Essayée sous l'en-tête, remise au-dessus dans la foulée : le propriétaire
préfère entrer dans la fiche par l'image. Aller-retour assumé — c'est le genre
de choix qui se juge à l'écran, pas sur un raisonnement.

### Le graphique s'élargit — et découvre deux fiches sans axe des prix

« Le graph peut prendre plus de largeur pour s'aligner au reste. » Le SVG
occupait déjà toute la laisse de la fiche, mais son **dessin** s'arrêtait à
22 unités du bord gauche et 23 du bord droit — deux bandes vides d'une
trentaine de pixels chacune, exactement celles entourées sur la capture.

Les marges ne sont plus arrondies au jugé, elles sont **calculées sur ce
qu'elles contiennent** : à gauche, le plus long prix d'axe fait 24 unités et se
termine 6 avant le cadre, d'où 34 ; à droite, « +2σ » fait 16 unités et
commence 5 après, d'où 24. **Trente-deux unités récupérées, 4,5 % de tracé en
plus**, et le graphique s'aligne enfin sur les barres et le texte.

**Et en vérifiant qu'aucune étiquette ne dépassait, un trou est apparu.**
L'échelle des prix s'arrêtait à 10 000. Samsung cote entre 19 000 et
354 000 wons, SK Hynix jusqu'à 2,8 millions : leur fourchette passait
**entièrement au-dessus du dernier échelon**, le filtre ne renvoyait aucun
repère, et l'axe des prix disparaissait en silence — un graphique sans
ordonnée, sur deux fiches, depuis l'ouverture aux places asiatiques. L'échelle
poursuit désormais le même motif jusqu'aux millions, et les grands nombres sont
abrégés (« 150k », « 2,5M ») : sans cela « 2500000 » ferait sept caractères et
rendrait au bord gauche tout ce que le resserrement venait d'y gagner. Quatre
caractères au maximum, quelle que soit la place de cotation — vérifié sur
seize sociétés à deux largeurs, aucune étiquette hors cadre, aucune fiche sans
axe.

### Le relevé du graphique de cours tenait sur une ligne, pas sur quatre

« Le rectangle avec les metrics est beaucoup trop grand pour la quantité
d'infos. » Mesuré : **1 010 px de large et 100 de haut pour une quarantaine de
caractères**. Deux causes cumulées — le contenu était découpé en quatre lignes
par des `<br>`, et un bloc statique prend toute la largeur disponible par
défaut, si bien que `width:auto` ne bornait rien du tout.

Les retours à la ligne deviennent des séparateurs `·` et la boîte épouse son
contenu (`width:fit-content`). Résultat mesuré : **577 × 30 px** sur écran
large, et sur mobile elle se replie d'elle-même sur deux lignes en occupant la
largeur disponible. Rien n'est perdu : la date, le cours, la tendance avec son
potentiel de retour, les deux moyennes mobiles sont toutes là.

### La piste des cinq ans est morte, la sonde a trouvé mieux

Je proposais d'ancrer notre prolongation sur le taux de croissance à cinq ans
de Yahoo. La sonde a lu la table brute, et le résultat est **négatif** :
l'index n'est pas `+5y` comme je l'annonçais, mais
`['0q','+1q','0y','+1y','LTG']` — et `LTG` (*Long Term Growth*) est **vide sur
les douze sociétés**. `revenue_estimate` et `earnings_estimate` s'arrêtent bien
à `+1y`. **Il n'existe aucun horizon multi-annuel dans notre source.** C'est
exactement pourquoi la règle était « publier brut, lire, puis décider » : la
supposition était fausse jusque dans le nom du champ.

Mais la sonde a trouvé deux choses que je ne cherchais pas.

**Le piège des devises est étiqueté dans l'API.** TSMC : consensus de chiffre
d'affaires en **TWD**, consensus de bénéfice en **USD**, dans la même réponse.
Notre inférence (`financialCurrency == currency`) tombe juste sur les douze,
mais lire l'étiquette vaut mieux que la déduire.

**Sur quoi repose le consensus.** Les tables portent le **nombre d'analystes**
et la **fourchette basse/haute**, jamais lus jusqu'ici. L'écart est
considérable : 50 analystes sur Alphabet contre **deux** sur Constellation
Energy ; un désaccord de ±1 % sur Booking contre **±16 %** sur Nebius. Depuis
que la trajectoire est une courbe unique et assumée, elle a l'autorité d'une
affirmation — la fiche dit désormais sur quelles fondations elle repose, en six
mots : *« 50 analystes, ils divergent de ±2,8 % »*.

Détail qui aurait mordu : dans `revenue_estimate`, `avg`, `low`, `high` et
`numberOfAnalysts` arrivent en **chaînes** là où les mêmes colonnes
d'`earnings_estimate` arrivent en flottants. Et `fusionner_fonda` reconstruit
`fonda` de zéro : le nouveau champ aurait été perdu en silence — exactement ce
qui avait coûté 96 fiches avec `proj`. La garde générique de jeu de champs le
couvre.

### Une tête coupée et deux centres décalés

**« Sur NVIDIA, tête de Jensen coupée. »** Mesuré : une source 960×540 mise à
la largeur d'une fiche fait 568 px de haut, ramenés à 300 par le plafond — on
jetait 268 px, moitié en haut, moitié en bas, parce que `object-fit:cover`
centre par défaut. Or le sujet d'une photo de presse est presque toujours dans
le tiers **supérieur** : c'est la moitié qu'on jetait. Le plafond monte à
360 px et l'ancrage passe à 30 % de haut ; la fenêtre visible remonte de 72 px
dans la source. La règle vaut pour les cent et quelques illustrations, pas pour
une image particulière — vérifié sur cinq autres sujets (circuit, terminal de
paiement) sans dégradation.

**« La décomposition pas bien alignée avec le score. »** Elle et l'anneau
étaient tous deux calés en haut ; comme ils n'ont pas la même hauteur (92 px
contre 138), leurs centres tombaient à **17 px** l'un de l'autre — assez pour
que l'œil le voie. Centrés sur la même ligne, ils partagent maintenant le même
axe au pixel près. Le titre, lui, reste en haut : c'est le point d'entrée de la
fiche.

### Les pertes attendues étaient censurées, sans qu'on l'ait décidé

En comparant nos fiches Nebius et CoreWeave à celles d'un concurrent, le
propriétaire a relevé que celui-ci affiche des **barres de bénéfice négatives**
sur les exercices à venir, là où nos fiches ne montrent **rien du tout**.

C'était un défaut, pas un choix. Deux gardes de `projections()` filtraient les
valeurs négatives — `base <= 0` sortait de la boucle, `v > 0` rejetait chaque
estimation. Résultat : une société dont les analystes attendent des pertes
n'affichait **aucun** bénéfice attendu, pas même le consensus. Cela contredisait
notre propre règle, écrite quelques lignes plus bas : *« le consensus reste
affiché — c'est un fait déposé, pas une opinion à nous »*.

Le consensus est désormais publié **quel que soit son signe**. Ce qu'on continue
de refuser, c'est de le **prolonger** : faire décroître une perte vers +3 % de
croissance n'a aucun sens, et le refus est posé avec son motif. Le front
apprend au passage à déduire un nombre d'actions d'un exercice en perte — le
rapport de deux nombres négatifs donne le même compte de titres (CoreWeave
2025 : −1 167 ÷ −2,81 = 415 millions), et l'exiger positif privait de barres
toutes les sociétés déficitaires.

*Effet visible au prochain run du screener : les estimations négatives n'ont
jamais été stockées, elles ne peuvent pas être reconstituées hors ligne.*

### Où nous en sommes face à un concurrent, sur deux dossiers difficiles

Mesuré exercice par exercice sur Nebius et CoreWeave :

| | nous | eux |
|---|---|---|
| historique du CA | identique (≤ 1,3 %) | — |
| consensus à 2 ans | identique (≤ 1,2 %) | — |
| exercices 3 à 5 | **absents** | +60 %, +38 %, +45 % (CoreWeave) |

Leur profil à trois-cinq ans est **irrégulier** — aucune formule de
décroissance ne produit cela : ce sont de vraies estimations d'analystes,
issues d'un flux de consensus multi-annuel que nous n'avons pas. Notre refus
au-delà de 50 %/an reste **juste au regard de notre source** : abaisser le
seuil ne nous donnerait pas leurs chiffres, mais notre formule appliquée à un
rythme délirant — précisément le désastre documenté (18 Md$ contre 140 Md$
selon le réglage, quand le marché en discutait 33 à 46).

La seule piste réelle dans notre source actuelle reste `growth_estimates` de
Yahoo, qui porte un taux de croissance annualisé à cinq ans que nous ne lisons
toujours pas. Il donnerait une courbe lisse, pas leur irrégularité — mais
ancrée sur un chiffre d'analyste au lieu de notre décroissance. Il sera publié
**brut** sur un run avant tout branchement (le proxy de développement bloque
Yahoo, la lecture doit passer par un run GitHub).

### « Croiss CA · a/a, ça correspond à quoi ? » — pas à ce qu'on croyait

La question a valu un recoupement, et il a trouvé une vraie faute. Le chiffre
était `revenueGrowth` de Yahoo, repris tel quel. Comparé à **notre propre
historique trimestriel** — les barres dessinées juste au-dessus de la tuile —
il divergeait sur **18 fiches sur 83**, pour deux raisons distinctes :

- **Désynchronisation (30 fiches).** Le résumé de Yahoo porte sur le trimestre
  que son bloc `info` estime le plus récent ; notre série s'accumule d'un run à
  l'autre et n'a pas toujours le même dernier point. SanDisk annonçait
  **+371,6 %** quand le dernier trimestre dessiné en donne **+251,0**.
- **Définition du revenu (6 fiches).** Même recalculé sur le trimestre que
  Yahoo désigne, l'écart persiste chez des assureurs et des services aux
  collectivités : Constellation Energy annonçait **+23,0 %** là où ses propres
  comptes trimestriels donnent **−4,2 %**.

La croissance est désormais **calculée sur la série que nous publions**, avec
la règle du tableau : le même trimestre un an plus tôt, jamais le précédent.
25 valeurs corrigées.

**Un piège évité en cours de route.** Le premier correctif alignait aussi la
date de référence `mrq` sur notre dernier trimestre. C'était une erreur : la
désynchronisation va dans le sens *inverse* de l'intuition — le résumé de Yahoo
est **plus frais** que son propre endpoint d'états financiers — et `mrq` date
aussi les marges TTM, qui viennent bien de ce résumé frais. L'aligner aurait
reculé la date des marges pour arranger celle de la croissance : on aurait
déplacé l'incohérence au lieu de la corriger. Chaque chiffre porte donc sa
propre date, et la bulle « i » les énonce toutes les deux quand elles diffèrent.

### Les deux dépliants disparaissent des fiches

« Ça fait doublon avec le graph. » Depuis que chaque colonne livre ses montants
au survol et au doigt — chiffre d'affaires, résultat net, variation et nature
de la valeur — « Dérouler les chiffres » et « Dérouler la trajectoire
attendue » répétaient le dessin.

**Ce que ça coûte, et c'est assumé** : le tableau des publiés montrait tout
l'historique accumulé là où le graphique s'arrête à dix exercices. Au-delà de
dix ans, les chiffres ne sont plus lisibles sur la fiche — ils restent
collectés et continuent d'alimenter la note (marge médiane, TCAM, médiane des
multiples se calculent sur tout l'accumulé). L'hypothèse du **nombre d'actions
constant**, qui vivait sous le tableau de trajectoire, a été déplacée dans la
bulle « i » : les barres de bénéfice attendu en dépendent entièrement, elle ne
pouvait pas partir avec lui.

### La décomposition passe dans l'en-tête, entre l'identité et le score

Croquis du propriétaire à l'appui. C'est sa place logique : elle est la
ventilation du nombre affiché juste à sa droite, et les deux se lisent
maintenant d'un seul regard, avant même le résumé.

Deux réglages trouvés **en mesurant, pas en regardant** : le bloc de titre
devait céder la place (`flex:1 1 0`), faute de quoi le nom de la société
poussait la décomposition à 180 px et la colonne de barre tombait à **zéro** —
quatre valeurs alignées sans aucune barre ; et le conteneur `#dzone` devait
passer en `display:contents`, sinon c'était lui, div nu, qui devenait l'enfant
flex et coinçait le bloc à sa largeur minimale. Sur mobile, identité et anneau
restent côte à côte, la décomposition passe dessous en pleine largeur.

### La décomposition remonte en tête, les tuiles orphelines rentrent chez elles

Trois retours du propriétaire sur la fiche épurée le matin même.

**« Je préférais la manière juste avant. »** Les quatre jauges avaient été
mises sur deux colonnes en récupérant la place des jauges supprimées. Retour
à la **colonne unique**, largeur bornée à 520 px : étalées sur toute la
laisse de texte, quatre barres de longueurs voisines deviennent
indistinguables — c'est leur comparaison qui porte l'information.

**« Autant la mettre tout au début. »** Elle est désormais **juste sous le
résumé**, avant les graphiques. Elle justifie le chiffre affiché dans
l'anneau quelques centimètres plus haut : la lire après trois graphiques
obligeait à remonter pour faire le lien. (La variante « au survol de
l'anneau » a été écartée : elle cache la justification derrière un geste, et
sur mobile ce geste ne s'annonce pas.)

**« Les quatre infos se baladent un peu toutes seules. »** Exact — c'était le
reliquat d'un bandeau qui en comptait six, sans plus aucun voisin pour les
expliquer. Chacune est partie là où elle a un contexte : le **repli sur 52
semaines** rejoint la ligne sous le graphique de cours, à côté de l'écart à
la tendance, du z-score et du RSI ; la **croissance du CA**, la **marge
nette** et la **marge FCF** passent sous le graphique des chiffres publiés,
avec la date de référence qui les accompagnait. Elles y disent où en est la
société *aujourd'hui*, là où le graphique raconte plusieurs années. Plus
aucune rangée orpheline sur la fiche.

### Apprendre : la lecture des comptes passe de l'abstrait au concret

« J'aimerais qu'on puisse y enseigner les bases pour la lecture des comptes.
On le fait déjà ? » Oui — la section 04 décrivait déjà les trois états
financiers, la rentabilité du capital et où trouver les documents. Mais tout
y était **abstrait** : aucun chiffre réel, et aucun des pièges qui font mal
lire des comptes pourtant justes.

Deux blocs s'ajoutent. **Une lecture complète d'Alphabet sur l'exercice 2025**,
en cinq temps : le compte de résultat de haut en bas (402,8 Md$ de ventes →
132,2 Md$ de bénéfice, marge nette de 32,8 %, situé face aux 2 % d'un
distributeur), le bilan en une question (dette à 19 % des capitaux propres),
les flux comme épreuve de vérité (55 % du bénéfice comptable finit en cash),
le recoupement du nombre d'actions (132 200 ÷ 10,81 ≈ 12,2 Md de titres, le
calcul même que fait Signal pour convertir un consensus par action en
montant), et la durée (bénéficiaire 13 années sur 13). **Tous ces chiffres
sortent de nos propres données publiées** et ont été recoupés un à un ; ils
portent sur un exercice clos, donc ils ne périment pas.

Et **six pièges qui font mal lire des comptes justes** : le bénéfice
« ajusté » non normalisé, la rémunération en actions qui dilue sans sortir de
cash, les éléments exceptionnels (d'où nos médianes sur dix ou quinze
exercices), le besoin en fonds de roulement d'une croissance rapide, les
amortissements (le cas Broadcom 2019, BPA de 2,84 à 0,64 $ sans que
l'activité bouge), et les périodes qu'on compare.

### Un sommaire navigable sur mobile, au lieu d'un rouleau de texte

« J'aimerais que les sections soient facilement navigables sur mobile, pas un
bloc de texte qu'on scrolle. » Sous 1300 px, le sommaire en colonne était
purement et simplement **caché** : douze sections et près de deux mille lignes
d'Apprendre devenaient un seul rouleau.

Une barre collante apparaît maintenant sous le header : elle dit toujours dans
quelle section on est, et s'ouvre d'une tape sur la liste complète. Elle est
**construite depuis le même balisage** que la colonne de gauche — ajouter une
section au `<nav class="toc">` suffit, les deux rendus suivent, et il n'y a
pas deux listes à maintenir. Le décalage sous le header est **mesuré** au
chargement plutôt que codé en dur (58 px sous 700 px de large, 72 au-dessus),
de sorte que les sauts d'ancre dégagent toujours les deux barres. Vaut pour
Apprendre comme pour le Portefeuille.

### Portefeuille IA à droite, détail de la note retiré

Deux décisions d'ergonomie. Le lien **Portefeuille IA passe en dernière
position** du header, tout à droite, sur les quatre pages : c'est le seul qui
mène à de l'argent engagé, il mérite la position d'ancrage plutôt que le
milieu du peloton.

Et le dépliant **« Détail de la note » disparaît des fiches**. Il déroulait
les quinze critères phrasés un à un, sous les quatre jauges qui disent déjà où
la note se gagne et se perd. Le raisonnement complet reste public — la grille
est décrite au lexique, et le code qui la calcule est ouvert — mais la fiche
n'a pas à le dérouler pour être lue.

### Une seule courbe, assumée — le cône est mort

« Je préfère qu'on assume une position, on ne parle pas de haut de
fourchette. » La mesure a montré que le cône n'était pas une fourchette
encadrant la vérité, mais **une bonne réponse et une mauvaise publiées
ensemble**.

Sur TSMC, contre un concurrent qui publie du consensus multi-annuel — nos
exercices publiés sont identiques aux siens à la décimale :

| exercice | notre branche prudente | notre branche haute | eux |
|---|---|---|---|
| 2026 | 5 420 | — | 5 426 |
| 2027 | 7 187 | — | 7 280 |
| 2028 | 8 118 (**−11 %**) | 9 256 (**+1 %**) | 9 161 |
| 2029 | 8 901 (**−24 %**) | 11 124 (−5 %) | 11 730 |

Leur profil (+25,8 % puis +28,0 %) remonte en fin de période : aucune formule
de décroissance ne fait ça, ce sont de vraies estimations d'analystes. Notre
branche haute tombe à 1 % près sur 2028 ; la prudente sous-tire de 24 %.

**Le diagnostic n'était pas celui qu'on croyait.** Le plafond de 25 % n'était
presque jamais ce qui mordait — le retirer seul ne change que 2 fiches sur 93.
Le vrai frein était `min(consensus, TCAM historique)` : brider les analystes
par le passé de la société. C'est de la prudence empilée sur de la prudence,
puisque la décroissance vers 3 % assure déjà qu'on ne prolonge pas un rythme
record éternellement.

La règle est donc : **on part du rythme du consensus et on décroît vers 3 %**.
Le TCAM démontré garde son rôle de **critère de refus** — sous le taux
terminal, on ne prolonge pas du tout, ce qui préserve le garde-fou du BPA de
Nebius — mais il ne rabote plus le point de départ. Refuser est une position ;
raboter était une pudeur.

Les 27 motifs d'arrêt sont intacts, Nebius reste refusé au-delà du consensus,
et 47 fiches voient leur horizon relevé (jusqu'à ×1,55 sur Teradyne). Les
tests interdisent désormais le champ `_haut` **partout** — sur toutes les
natures, pas seulement le consensus : une fiche non régénérée se trahirait.

### Trois corrections d'un même après-midi de relecture

Le propriétaire a relu les fiches déployées et posé trois questions ; chacune
révélait un vrai défaut.

**« Sur Coherent j'ai un PER aujourd'hui avant 2023. »** Le losange
« aujourd'hui » se posait une demi-année après le dernier exercice *coté* —
pas après le dernier exercice *publié*. Coherent aligne trois exercices de
pertes après 2022 : le losange se plaçait après 2022, avant les croix de
2023-2025 — un aujourd'hui dans le passé. Il se place désormais
chronologiquement, et le connecteur pointillé ne part du dernier point coté
que s'il n'y a pas de trou entre lui et aujourd'hui : relier 2022 au losange
par-dessus trois ans de pertes dessinerait une continuité qui n'existe pas.
Les croix de Coherent, elles, sont justes : pertes réelles en 2020, 2023 et
2024, BPA ordinaire négatif en 2025 (résultat positif mais préférentielles
servies d'abord).

**« Pourquoi il y a encore la valeur affichée au-dessus des barres ? »**
L'étiquette datait d'avant la carte au survol, qui donne le même montant avec
sa variation et sa nature. Retirée — elle affichait le chiffre deux fois sur
les grands écrans et zéro fois sur les étroits, où elle ne tenait pas.

**« Un ajout au-dessus de certaines barres du prévisionnel — carnet de
commandes ?? comment on le calcule ?? »** On ne le calcule pas, et c'est
l'ancienne phrase qui était fautive : elle laissait croire qu'une donnée de
carnet existait. Le contour en pointillé est la **seconde branche de la
prolongation** : quand le rythme du consensus dépasse 25 %/an, la barre
hachurée repart du plafond de 25 % (ce qu'une croissance organique tient
rarement) et le contour repart du rythme des analystes tel quel — les deux
décroissant vers 3 %. Rien dans nos données ne distingue un carnet signé d'un
emballement, alors on montre les deux ; l'écart mesure notre ignorance. La
bulle « i » dit maintenant ce mécanisme, chiffres à l'appui.

### Échelle log sur les barres quand le linéaire écrase tout

Signalé par le propriétaire sur NVIDIA : « de 2017 à 2023 tout est presque
plat alors qu'on parle en milliards ». C'est mathématique — un CA multiplié
par 80 sur la fenêtre (7 → 562 Md$ attendus) ne laisse aux premières années
que quelques pixels en linéaire.

Même doctrine que la courbe des PER, avec deux garde-fous : le log exige que
**tout soit positif** (une perte n'a pas de logarithme — Nebius reste en
linéaire), et ne se déclenche qu'à partir d'un **rapport de 15** entre le plus
grand et le plus petit CA dessinés — Alphabet (×9) garde l'échelle linéaire,
où les hauteurs se comparent en différence, la lecture la plus naturelle.
L'échelle en vigueur est écrite à côté de la devise (« échelle log », avec un
« i » qui explique : les hauteurs se comparent en rapport, une croissance
régulière en % donne des marches régulières). La conversion valeur→pixels est
UNE fonction partagée par le CA, sa borne haute et le résultat net — deux
conversions auraient fini par diverger.

### La colonne EBITDA quitte le tableau des chiffres

« On supprime la colonne EBITDA car pas assez d'historique. » La mesure donne
raison à l'intuition : sur les 93 fiches publiées, l'EBITDA ne couvre que
**31 % des exercices annuels** — c'est une mesure non-GAAP, absente des dépôts
XBRL de la SEC, donc Yahoo n'en donne que quatre ans là où EDGAR pousse CA et
résultat net à dix-huit ou dix-neuf. Sur toute fiche à historique profond, la
colonne était une colonne de tirets.

La donnée reste **collectée** chaque semaine : l'accumulateur la profondit
tout seul, et le jour où elle couvrira une vraie décennie, la colonne pourra
revenir. La page Apprendre est mise à jour dans le même sens.

### La fiche à l'épure : cinq décisions du propriétaire, appliquées d'un bloc

L'après-midi du 07/08, en regardant la fiche déployée le matin même, cinq
consignes — toutes dans le sens « simple, épuré mais complet » :

**« Il manque le bénéfice net prévisionnel dans les graphs. »** Il y est : en
barres hachurées grises à côté du CA attendu, mêmes hachures que lui (plein =
déposé, hachuré = attendu). Le montant est BPA consensus × nombre d'actions
déduit du dernier exercice publié — le nombre d'actions est calculé UNE fois
et partagé avec le tableau de trajectoire, deux calculs auraient fini par
diverger.

**« Regarde comment Baggr affiche le résultat au survol, je veux pareil. »**
Le bandeau docké de la matinée est remplacé sur le graphique des barres par
une carte flottante posée à côté de la colonne visée, du côté où il y a de la
place, cachée au repos. Elle suit la colonne en X, jamais le pointeur en Y —
sinon elle tremble sous le doigt. Au doigt elle reste après qu'on a levé le
doigt : on le lève précisément pour lire ce qu'il cachait. La variation
affichée est celle du tableau (même trimestre un an plus tôt en trimestriel).

**« Ça sert à rien l'info au survol sur le graph PER »** et **« Dérouler les
PER n'a pas d'utilité, tout doit apparaître sur le graph. »** Le relevé et le
tableau dépliable des PER sont partis ; en échange, CHAQUE point porte sa
valeur sur le dessin. L'ancien tri (quatre points remarquables) supposait un
tableau en secours qui n'existe plus. Le chevauchement autour du losange est
résolu autrement : une étiquette trop proche de la précédente passe SOUS son
point au lieu d'être omise.

**« Supprime tout ce qui n'est pas vital, mets en "déplier" ou "i" le
secondaire. »** Sont partis : les jauges « Signaux de marché » (le RSI ne note
plus rien depuis la v4 ; sa valeur et le z-score vivent en toutes lettres sous
le graphique de cours, où on lit le marché), la tuile Cross (copie du badge de
tête de fiche), la tuile Pente MM21 (micro-technique qui n'alimente rien).
Sont passées derrière un « i » : l'explication de la base de cours des PER et
la pédagogie de la prolongation (décroissance vers 3 %, borne haute). Restent
visibles : la provenance (consensus jusqu'où, nous ensuite) et les refus de
prolonger — des positions que nous prenons, pas de la pédagogie. Sur mobile,
les bulles « i » deviennent des feuilles pleine largeur posées en bas de
l'écran : ancrées à leur icône, elles débordaient dès que l'icône touchait un
bord.

**Vérification de fraîcheur demandée en tête de consigne** : les 93 fiches
publiées ont été régénérées à 11 h 34, APRÈS le dernier changement de barème
(11 h 18) ; les nouveaux maxima (ROE /9, conversion /7) sont dans les données
publiées, et les scores watchlist = scores fiches, zéro écart.

### Le montant sous le doigt : un relevé sur les deux graphiques de chiffres

*(Entrée du matin, en partie remplacée l'après-midi même par « La fiche à
l'épure » ci-dessus : le relevé docké est devenu une carte flottante façon
Baggr sur les barres, et a été retiré du graphique des PER au profit
d'étiquettes sur chaque point.)*

« Quand je passe la souris ou le doigt sur un pilier des graphs je veux pouvoir
voir le montant ». Les barres ne portaient aucune valeur (sauf les projections,
et seulement quand la place le permettait) ; les points de la courbe des PER
portaient un `<title>` SVG, qui n'apparaît qu'après une seconde de survol et
**jamais au doigt** — sur l'écran principal du propriétaire, l'information
n'existait pas.

Le principe posé ce matin-là et toujours en vigueur : la colonne la plus
proche du pointeur est sélectionnée (viser une barre de 34 unités dans un slot
qui peut en faire 18 est impossible au doigt) ; le relevé ne dit que ce que le
dessin dessine ; et il reprend **la même variation que le tableau** — en
trimestriel, le même trimestre un an plus tôt, pas le trimestre précédent :
deux « ▲ 15 % » différents pour la même barre selon qu'on la survole ou qu'on
la lit auraient été une incohérence pure.

### Le relevé du graphique de cours est docké partout

« Je veux que le petit rectangle avec les metrics s'affiche en bas du graph
comme sur mobile ». Il flottait sur écran large, collé au réticule : il
recouvrait la courbe qu'on venait justement lire et sautait d'un bord à l'autre
au passage du milieu. Sous le dessin, dans le flux, il ne cache rien et ne
bouge jamais. Trois branches de positionnement disparaissent avec lui, et les
deux tailles d'écran se lisent enfin de la même façon.

### PER : plus de tuile, plus de décimale

Deux décisions du propriétaire. « Ne pas afficher la carte PER prévisionnel
puisqu'il y a le graph des PER » : la rangée de métriques n'en porte plus
aucun, ni courant ni prévisionnel. Un chiffre nu dans une tuile n'apprend rien ;
le même chiffre au milieu de dix ans de multiples dit s'il est cher.

Un seul cas ne se lit pas sur la courbe : des **bénéfices attendus négatifs**
ne produisent aucun point, donc la courbe s'arrête sans rien dire. La tuile le
disait (« pertes attendues ») ; la phrase est maintenant écrite sous le
graphique, y compris quand il n'y a pas de graphique du tout. Deux sociétés
concernées aujourd'hui : Nebius et CoreWeave.

« Arrondir les PER, pas de virgule » : entre 20,8× et 21× il n'y a aucune
information. Le graphique arrondissait déjà, le tableau s'aligne.

### Correction : « aucun analyste ne publie à cinq ans » était faux

Cette affirmation vivait dans trois fichiers (`screener.py`, `index.html`,
ce journal). La comparaison avec Baggr sur Alphabet la contredit : leur profil
2028-2030 est **+19,1 %, +13,0 %, +14,8 %** — irrégulier, donc issu
d'estimations réelles, là où le nôtre décroît lissé parce que c'est une
formule. Ce que nous pouvons dire est plus étroit et suffit au lecteur :
**notre source de consensus s'arrête à deux exercices**. Le reste est notre
arithmétique faute de données, pas faute de données existantes.

Piste ouverte, pas encore branchée : Yahoo expose `growth_estimates` (dont un
taux annuel à cinq ans) que nous ne lisons jamais. Elle sera publiée **brute**
sur un run avant d'être utilisée — deux erreurs d'unité supposée (les
dividendes dans les cours, la devise du consensus) ont déjà coûté cher ici, et
la règle qui en sort est de mesurer avant de croire.

### Nos chiffres contre ceux de Baggr, ligne à ligne

Question du propriétaire : « je veux surtout revenus et bénéfices, nous on met
résultat net, c'est pas pareil ? ». C'est exactement pareil, et c'est vérifié
sur Alphabet, exercice par exercice :

| exercice | CA nous | CA Baggr | résultat net nous | « Bénéfices » Baggr |
|---|---|---|---|---|
| 2021 | 257,6 | 257,6 | 76,0 | 76,0 |
| 2023 | 307,4 | 307,4 | 73,8 | 73,8 |
| 2025 | 402,8 | 402,8 | 132,2 | 132,2 |

Écart maximal : **0,05 %**. Leur libellé « Bénéfices » désigne le résultat net.
Le nombre d'actions que nous DÉDUISONS (résultat net ÷ bénéfice par action)
tombe à 12,2 milliards là où ils publient 12,1 — la déduction est bonne à 1 %.

Sur l'attendu, le consensus concorde aussi (chiffre d'affaires 2026 à 0,5 %,
2027 à 0,1 %). La divergence n'apparaît QUE là où nos méthodes diffèrent : à
partir de 2028 nous extrapolons en décélérant vers 3 %, eux prolongent plus
généreusement, et l'écart atteint 12,7 % en 2030 (817 contre 936 Md$). Ce n'est
pas une donnée qui diverge, c'est une hypothèse.

### Le bénéfice attendu passe en montant, à côté du par-action

« Dans notre "dérouler la trajectoire attendue" on a Bénéfice par action,
pourquoi ? ». Parce que c'est ce que notre source donne : le consensus de Yahoo
est par action, il n'existe pas de consensus en montant. Mais le graphique
juste au-dessus parle en millions, et passer au par-action dans le tableau
obligeait à changer d'unité en cours de route.

Les deux colonnes coexistent désormais. Le montant est le produit du bénéfice
par action et du nombre d'actions déduit du dernier exercice publié — une
déduction vérifiée à 1 % contre le chiffre publié d'Alphabet. L'hypothèse d'un
nombre d'actions CONSTANT est écrite sous le tableau, parce qu'elle est fausse
pour toute société qui rachète ses titres.

### Une échelle de lecture sous le score

Validée par le propriétaire, inspirée de la leur (« sous 8 dégradé, 8-12 moyen,
12+ solide » sur 20). Un /100 sans repère ne dit rien : 62 est-il bon ?

Sous 50 **dégradé**, de 50 à 70 **moyen**, 70 et plus **solide**. Les seuils
sont ABSOLUS — des jugements sur l'entreprise, pas des centiles de notre liste,
sinon la note changerait de sens à chaque rotation d'univers. Sur les 94 fiches
publiées ils répartissent 18 / 45 / 36 %, ce qui trie sans écraser.

### Pérennité : deux dates confondues en une sur le portefeuille

Angle mort que la question ne nommait pas, et qui touche la page où l'argent
est réel. `updated_at` est rafraîchi CHAQUE JOUR par la mise à jour des cours ;
`week` ne bouge que quand l'agent tourne, le lundi. La page les concaténait :
« Mis à jour · 2026-08-07 · Sem. 31 · 2026 » — une date du jour collée à une
analyse d'il y a une semaine, sur une seule ligne, sans rien pour les
distinguer. Un lecteur y lit que les arbitrages sont d'aujourd'hui.

La ligne dit désormais « Cours au 2026-08-07 · analyse Sem. 31 · 2026 », et
ajoute explicitement le décalage quand il existe. Le cas n'est pas théorique :
c'est l'état actuel du site, l'étape agent du workflow étant en
`continue-on-error` — elle peut échouer sans que rien ne s'arrête.

**Ce qui tient déjà, vérifié** : le screener a une garde de couverture
fail-loud (sous 85 % de titres scorés il refuse de publier et laisse la
version précédente en ligne, leçon du 27/07 où 94 titres US évincés avaient
produit une watchlist 100 % européenne, job vert) ; l'étape screener n'est PAS
en `continue-on-error`, donc l'agent ne peut pas tourner sur une watchlist qui
vient d'échouer ; l'agent refuse d'écrire `portfolio.json` quand sa passe 2 est
inexploitable ou l'API indisponible, plutôt que d'écrire un état dégradé.

### Audit de la grille### Audit de la grille : seize points sur cent ne notaient rien

Demandé par le propriétaire — « ce que l'on calcule, comment, et pourquoi on
l'affiche ; fiable, pérenne, simple et utile ». La mesure d'abord, sur les
94 fiches publiées : pour chaque critère, quelle part de l'univers touche le
plancher ou le plafond, et quelle part du CLASSEMENT il explique réellement
(covariance avec le total rapportée à la variance du total).

Le verdict est net. **Trois critères pesaient NÉGATIVEMENT dans le classement**,
c'est-à-dire qu'ils poussaient vers le bas les titres que le reste de la grille
poussait vers le haut, tout en étant quasi constants :

| critère | part du barème | notait réellement | part du classement |
|---|---|---|---|
| tendance | 6 % | 18 % des titres | **−3,1 %** |
| attendu | 7 % | 11 % des titres | **−1,2 %** |
| rsi | 3 % | 19 % des titres | **−0,5 %** |

**Le RSI quitte la note.** Sa cloche 35-65 couvre jusqu'au huitième décile d'un
univers qui va de 35 à 78 : 82 % des titres touchaient le maximum. Sa dispersion
rapportée à son maximum était la plus faible de la grille (0,17). Et un
oscillateur à quatorze jours n'a pas de pouvoir prédictif établi sur l'horizon
de ce portefeuille, qui se juge en mois. Il reste AFFICHÉ avec ses repères
30/70 — c'est une information de marché légitime, elle n'entre simplement pas
dans un score qu'on prétend défendable. Le momentum reste sur 15 : tendance 7,
position 8 (le meilleur critère du bloc hérite du point libéré).

**Cinq rampes finissaient sous la médiane de l'univers.** Une rampe dont la
borne haute est dépassée par le titre médian ne classe plus la moitié du
peloton — elle distribue. Les seuils gardent leur sens économique, ils couvrent
désormais la population qu'ils sont censés trier :

| critère | avant | après | notait → note |
|---|---|---|---|
| tendance (écart MM21/MM200) | ±5 % | **±15 %** | 18 % → 53 % |
| attendu (croissance estimée) | 0-20 % | **0-40 %** | 11 % → 57 % |
| roe | 8-20 % | **8-30 %** | 31 % → 53 % |
| conversion en cash | 40-100 % | **40-120 %** | 33 % → 51 % |
| histoire (PER vs son passé) | 1,3→0,7 | **2,0→0,7** | 39 % → 56 % |

Sur `histoire`, le défaut était l'inverse des autres : 46 % de l'univers était
à ZÉRO, la rampe ne distinguant plus « un peu cher » (1,35 fois son propre
multiple historique) de « absurdement cher » (18,4 fois).

Effet mesuré sur le classement publié : déplacement médian de 4 places, neuvième
décile à 12, maximum 21 sur 94 titres. La dispersion des scores est inchangée
(σ = 13) — ce n'est pas elle qu'on cherchait à gonfler, c'est la part du score
qui mesure quelque chose.

**Constaté, non corrigé** — ce sont des choix de conception, pas des défauts :
la croissance du bénéfice est comptée deux fois (critère `bpa` et, à l'intérieur
du PEG, la même croissance : leurs points corrèlent à +0,70) ; `tendance` et
`position` regardent le même axe à deux horizons (+0,63 sur les valeurs) ;
`constance` est binaire par nature et c'est voulu. Les corrélations ENTRE BLOCS
restent basses (+0,06 à +0,27), ce qui est le signe qu'une partition MECE tient.

### Une suite qui teste les DONNÉES, pas seulement le code

Les quatre suites existantes passaient à 100 % pendant que le site affichait
« sur 100 € de bénéfice, 12 € finissent en cash » pour Microsoft et un bénéfice
taïwanais projeté en dollars pour TSM. Elles testaient le code sur des données
inventées ; aucun de ces défauts n'était un bug de logique, c'étaient des BASES
fausses, et une base fausse produit un code qui marche parfaitement sur un
chiffre qui ne veut rien dire.

`tests/test_donnees.py` lit ce qui est RÉELLEMENT publié et vérifie que les
grandeurs se recollent entre elles. Deux sévérités à dessein : les invariants
STRUCTURELS sont des impossibilités logiques (un seul cas fait échouer), les
SENTINELLES sont des bandes de vraisemblance qu'une entreprise réelle a le droit
de franchir (on n'échoue qu'au-delà d'un nombre de cas — un titre est une
exception, quinze sont une régression).

Elle a trouvé un défaut à son premier passage : la garde sur les devises ne
pouvait rien vérifier, faute de publier la devise de COTATION à côté de la
devise comptable. Le champ est ajouté, et la garde porte désormais une
**garde anti-sommeil** : un test qui passe sans rien regarder est pire qu'un
test absent, parce qu'il rassure.


## [4.1.0] — 2026-08-06

### Les métiers de bilan cessent d'être notés sur moins de critères

Le premier run v4 a fait remonter onze financières dans le top 30, contre
cinq auparavant — la renormalisation faisait exactement son travail, en
supprimant la pénalité artificielle que l'ancien barème infligeait aux
banques dépourvues de flux de trésorerie disponible. Mais leur couverture
moyenne restait à 89 % contre 93 % pour les autres titres : elles étaient
jugées sur moins de critères, ce que la renormalisation compense sans le
corriger.

- **Nouveau critère « cours / actifs nets »** (5 pts, bloc Valorisation) :
  pour les métiers de bilan uniquement, il REMPLACE le rendement du cash
  (retiré à juste titre, sans objet) au lieu de laisser un trou. C'est le
  multiple de référence des banques et assureurs, dont les fonds propres
  ont une valeur économique réelle. Rampe continue : 5 pts à 0,8× les
  actifs nets, 0 pt à 3×.
- **Pourquoi une rampe simple et non une cloche** : un multiple bas peut
  trahir un bilan douteux, mais ce jugement appartient déjà au bloc
  Qualité (ROE sur rampe bancaire, constance). Le bloc Valorisation ne
  répond qu'à « qu'est-ce que je paie » — y remettre de la qualité
  compterait deux fois la même information et casserait la partition MECE.
- **Source universelle**, sans l'asymétrie géographique d'EDGAR : Yahoo
  publie le ratio pour toutes les places et toutes les devises. Publié
  aussi tel quel dans le breakdown (`price_to_book`).
- Effet : la valorisation des financières redevient pleinement mesurée,
  quatre critères sur quatre. 10 tests ajoutés (52 au total sur le moteur).

### La renormalisation devient prudente — l'ignorance n'est plus une prime

Le propriétaire sentait le nouveau classement « moins bien » sans pouvoir
dire pourquoi. Mesure faite, l'intuition était juste : la renormalisation
préservait la moyenne (aucun biais — +0,3 pt d'écart entre titres partiels
et complets) mais gonflait la DISPERSION de 49 %. Les titres à couverture
partielle — 33 % de la population — occupaient 67 % du décile supérieur et
78 % du décile inférieur : un bloc jugé sur trois critères au lieu de cinq
sature plus facilement (14,5 % des blocs partiels au maximum, contre 6,6 %
des blocs complets). PDD dominait la watchlist à 91 en n'étant mesuré que
sur 81 % de la grille.

- La part NON MESURÉE d'un bloc est désormais présumée MOYENNE (55 % des
  points), au lieu d'hériter de la performance observée sur le reste. Un
  titre excellent sur ce qu'on sait mesurer reste bien noté, mais ne dépasse
  plus un titre également excellent et intégralement vérifié. Symétriquement,
  un titre médiocre partiellement mesuré ne coule plus au fond — pas de
  retour des zéros muets.
- Un bloc mesuré en entier n'est PAS touché (invariant testé).
- Effet simulé sur les données du 06/08 : l'écart-type des titres partiels
  rejoint celui des complets (19,7 → 13,9 contre 12,3), le décile supérieur
  retombe à leur poids démographique. PDD 91 → 82, HSBC 80 → 72, et les
  invisibles injustement coulés remontent (INTC 28 → 44, couverture 69 %).

### Croissance : la mesure démarre au premier exercice exploitable

Seize retraits « mathématiquement indéfinis » venaient d'un calcul qui
renonçait trop tôt : Broadcom ouvre son historique à −4,86 de BPA puis
atteint 4,77, et un taux de croissance n'existe pas depuis une base
négative — la formule abandonnait dix exercices lisibles. Le TCAM démarre
désormais au premier exercice positif (trois points minimum), la fenêtre
réellement retenue est rendue avec le taux, et la phrase de la fiche
signale la sortie de pertes (« depuis le premier exercice bénéficiaire,
sur 8 ans »). Arriver en perte reste sans multiple ni croissance. 9 tests.

### La projection s'arrête là où nous ne savons plus : le refus de prolonger

Deux corrections successives, toutes deux sur signalement du propriétaire, et
c'est la seconde qui tranche.

**Premier temps — le cône.** La version initiale plafonnait la prolongation à
25 % par an et projetait Nebius à 3,8 Md$ de chiffre d'affaires en 2030, quand
le marché en discute 33 à 46. Le plafond encodait un a priori de croissance
**organique** — statistiquement fondé — appliqué à une société dont le chiffre
d'affaires est largement **contracté** d'avance. La réponse fut de publier deux
branches, l'écart mesurant notre ignorance.

**Second temps — l'aveu.** « Oui mais du coup c'est faux sur Nebius. » Le cône
ne réparait rien : élargi, il donnait 18 Md$ d'un côté et 140 Md$ de l'autre.
Les DEUX bornes étaient fausses, et une fourchette de fausses valeurs reste une
fausse valeur — en pire, parce qu'elle a l'air d'un travail d'analyse. La règle
appliquée à la note depuis toujours vaut donc aussi pour les projections : **ce
qu'on ne sait pas calculer n'est pas approximé, il est retiré avec son motif.**

- **Deux refus explicites, par série.** *Par le haut* (rythme attendu > 50 %/an,
  `SEUIL_REFUS`) : la trajectoire dépend d'engagements contractuels que ni les
  comptes déposés ni le consensus à deux ans ne décrivent. *Par le bas* (rythme
  de départ sous les 3 % terminaux) : le modèle DÉCROÎT vers 3 %, il suppose
  donc un départ au-dessus — partir d'un rythme démontré négatif et le « faire
  décroître » vers +3 % inventait une inflexion que rien n'annonce. C'est
  exactement ce que nous publiions pour le BPA de Nebius : −36 % par an
  constatés, affichés en hausse jusqu'en 2030.
- **Le consensus, lui, reste affiché** — c'est un fait déposé. Nebius publie
  donc 2026 et 2027, puis la courbe s'arrête, et la fiche dit pourquoi. Les
  compounders réguliers vont toujours jusqu'en 2030.
- **Le refus est par SÉRIE, pas par fiche** : un chiffre d'affaires
  incalculable ne condamne pas un bénéfice prolongeable, et réciproquement.
- **`nature` existe désormais en deux exemplaires** — par série (exacte) et par
  année (la plus prudente des deux). Sans la version par série, un BPA extrapolé
  faisait passer pour « extrapolé » un chiffre d'affaires qui était du
  consensus publié : le bug était visible sur la fiche NBIS.
- **Le cône survit là où il garde un sens**, entre 25 % et 50 % : la fourchette
  est large mais ses deux bornes restent défendables.
- 20 tests sur la fonction, plus une vérification navigateur sur NBIS (arrêt à
  2027, motif affiché) et MSFT (trajectoire complète, cône intact).

**Ce que cela coûte, assumé** : nous n'affichons plus de trajectoire à cinq ans
pour les sociétés les plus spectaculaires du portefeuille. C'est le prix d'un
chiffre en lequel on peut avoir confiance.

### Les projections n'arrivaient jamais sur le site : un champ perdu à la fusion

Trouvé en vérifiant le run de population plutôt qu'en le supposant réussi.
Le run s'était terminé « success », et **96 fiches sur 97 étaient publiées sans
aucune trajectoire**. La seule qui en portait une était la fiche créée ce
jour-là (RMS.PA) — donc la seule sans historique à fusionner.

`fusionner_fonda()` **reconstruit** le bloc `fonda` de zéro au lieu de partir du
nouveau : elle recopie `devise`, `an`, `tr` et `pe_prev`, et tout champ qu'elle
ignore est silencieusement perdu à la publication. `proj` avait été ajouté au
bloc sans être ajouté à la fusion. Aucun test ne couvrait la conservation des
champs, et le run ne pouvait pas échouer sur une donnée absente.

- `proj` est désormais recopié — mais **sans repli sur l'ancienne valeur**,
  contrairement au PER prévisionnel : depuis le refus de prolonger, l'absence
  de projection est une DÉCISION, pas un silence de Yahoo. Reprendre celle du
  run précédent ressusciterait la courbe qu'on vient de retirer.
- **Un garde-fou générique** compare l'ensemble des champs conservés à une
  liste explicite : le prochain champ ajouté à `fonda` sans être traité dans la
  fusion fera échouer les tests au lieu de disparaître en silence.

### Le PER de Booking : ma garde supprimait des multiples justes

Signalé par le propriétaire — « j'ai l'impression que le PER de Booking est
beugué ». Il l'était, et c'est moi qui l'avais cassé le matin même.

La garde de base d'actions ajoutée avec le correctif des dividendes SUPPOSAIT
que les BPA de la fenêtre Yahoo étaient « tels que publiés », donc exprimés
dans la base d'actions de leur époque, et retirait le multiple de tout exercice
antérieur à un split. Les données publiées disent le contraire : le nombre
d'actions impliqué (résultat net ÷ BPA) est **continu** au passage d'EDGAR à
Yahoo — Booking 1 034 M puis 1 001 M, NVIDIA 25 330 M puis 25 103 M, Broadcom
4 291 M puis 4 333 M. Yahoo retraite ses BPA comme EDGAR. Booking perdait ses
quatre derniers multiples, NVIDIA et Broadcom deux chacun.

La supposition est remplacée par une **mesure**, la même qu'`edgar._normalise_eps` :
le nombre d'actions impliqué doit être du même ordre que le nombre d'actions
actuel (facteur 3 en log). Au-delà, la base est incompatible quelle qu'en soit
la cause. Sans résultat net ou sans nombre d'actions actuel, rien n'est
vérifiable et le multiple est calculé — on ne retire pas sur un soupçon.

Booking retrouve ses dix-huit multiples.

### Les graphiques passent à dix ans

Décision du propriétaire. L'accumulateur est monté à dix-neuf exercices et le
graphique les montrait tous : vingt-quatre colonnes avec les projections, des
barres de trois pixels, un axe où les années se marchaient dessus.

- **Dix exercices dessinés** sur les chiffres publiés comme sur la courbe des
  PER (douze trimestres en vue trimestrielle).
- **Rien n'est perdu** : les tableaux dépliables montrent tout l'accumulé, et
  la note continue de mesurer marges, croissance et médiane des multiples sur
  la totalité. On réduit ce qu'on dessine, jamais ce qu'on calcule.
- **La médiane tracée reste celle de tout l'historique** — c'est elle que le
  critère « histoire » compare au multiple du jour, et deux médianes
  différentes sur la même page seraient un contresens. Le nombre d'exercices
  est écrit sous le trait pour qu'il ne semble pas sortir de nulle part.

### Les chiffres se marchaient dessus, et le PER courant était dit trois fois

Deux captures d'écran du propriétaire, prises sur son téléphone : « les
chiffres se superposent ça fait trop » et « est-ce vraiment utile le PER
courant ? ».

**Les étiquettes ne mesuraient pas la place dont elles disposaient.** Le pas de
l'axe des exercices était deviné (« une sur deux au-delà de huit ») — bon à
douze colonnes, faux à vingt-quatre, et « 2024 2025 2026 » se recouvrait. Les
valeurs écrites au-dessus des barres projetées faisaient de même : « 409 Md$ »
mordait sur « 442 Md$ ». Sur la courbe des PER, trois points tiennent dans une
demi-année d'abscisse autour du losange, et « 28× 22× 19× 17× » se chevauchait.

- Le pas de l'axe se **déduit** désormais de la largeur d'un libellé (six
  unités par caractère, police à chasse fixe) rapportée au slot disponible.
- Une valeur au-dessus d'une barre n'est écrite **que si elle tient**. Sinon
  rien : le chiffre exact est de toute façon dans le tableau dépliable, et une
  étiquette illisible ne vaut pas mieux qu'une absence.
- Sur la courbe des PER, une étiquette cède la place quand la précédente est
  trop proche — sauf celle du jour, qui est celle qu'on vient lire. Les
  libellés d'axe ont leur propre écart, plus large : ils font quatre caractères
  (« auj. ») là où les valeurs en font trois.
- Le libellé de la **dernière colonne** sortait rogné du viewBox (« 2030 »
  coupé au bord droit) : aux deux extrémités le texte s'ancre au bord plutôt
  qu'à son centre.

**Le PER courant, lui, disparaît des tuiles.** La question était juste : le
multiple du jour apparaissait TROIS fois sur la même page — en chiffre nu dans
les métriques, en losange ambre au milieu de son propre historique, et dans le
détail de la note avec sa médiane en regard. Les deux derniers le donnent avec
sa référence ; la tuile était la seule à ne rien dire. Elle est retirée. Le
multiple reste affiché en toutes lettres sur les fiches sans courbe, où il n'a
pas d'autre porteur. Le PER **prévisionnel** reste : il ne figure nulle part
ailleurs et dit autre chose — ce que les analystes attendent.

### Deux contradictions vues à l'écran, sur la page elle-même

Trouvées en relisant les fiches produites plutôt qu'en relisant le code.

**La fiche Adyen se contredisait.** Le bloc croissance annonçait « chiffre
d'affaires en croissance de +19,2 % par an » — série tronquée à la rupture de
périmètre — pendant que la trajectoire attendue, trois centimètres plus bas,
refusait de prolonger « faute de rythme constaté », en mesurant, elle, à
travers la marche. La troncature avait été posée dans `note_v4` et pas dans
`projections()`. Elle est désormais partagée : un même chiffre d'affaires ne
peut pas avoir deux trajectoires sur la même page.

**La fiche TSM affichait « 2026e » sous une phrase disant « 2026 d'après le
consensus ».** L'étiquette « e » de l'année venait de la nature de LA LIGNE,
alors que la ligne porte deux séries : chiffre d'affaires de consensus,
bénéfice déjà extrapolé (les estimations de BPA étant ignorées pour un ADR).
L'année ne porte plus de marque ; la nature se lit dans la cellule, là où elle
est vraie, et la ligne entière n'est grisée que si toutes ses séries sont
extrapolées.

### Ce que l'audit a mesuré une fois les correctifs en production

Vérifié sur les données réellement publiées, après trois runs successifs.

| | avant | après |
|---|---|---|
| marge de flux disponible, Microsoft | 4,9 % | **20,2 %** |
| — Alphabet | 5,1 % | **18,2 %** |
| — NVIDIA | 18,3 % | **44,8 %** |
| croissance du CA, Adyen | −33,3 % (0/7) | **+19,2 % (7/7)** |
| — Western Digital | −10,5 % (0/7) | **+23,4 % (7/7)** |
| bénéfice par action projeté, TSM | 16,8 (USD) | **385,7 (TWD)** |
| fiches avec projections | 1 / 97 | **94 / 94** |
| fiches bloquées à 12 exercices | 44 | **0** (médiane 13, max 19) |
| prix sur actif net négatif publié | 3 | **0** |

Une confirmation en passant : la conversion publiée pour HPE vaut 1 100 %, alors
que le quotient de ses deux marges ARRONDIES donnerait 900 %. C'est exactement
la raison pour laquelle elle est calculée sur les valeurs brutes et non déduite
à l'affichage — sur une marge nette de 0,2 %, l'arrondi du dénominateur pilote
le résultat.

### Aucun CI n'exécutait les 396 tests

Le dépôt portait 396 tests et rien ne les lançait : le filet ne tenait que si
l'auteur pensait à le tendre avant de pousser. Un run du screener coûte
quarante minutes et écrit dans les données publiées ; y découvrir une
régression, c'est la découvrir trop tard.

Le workflow ajouté a fait **deux prises sur ses deux premières exécutions** :
`numpy` puis `anthropic` n'étaient pas bouchés, et les suites ne passaient en
local que parce que la machine de développement les avait installés. Trois
semaines de « 396 tests passés » reposaient en partie sur cet accident.

- La cause n'était pas un oubli mais une DUPLICATION : la liste des bouchons
  vivait recopiée dans deux suites, et aucune n'était l'originale.
- Elle est désormais unique, et une garde la compare à `requirements.txt` :
  la source de vérité est le fichier de dépendances, plus la mémoire de celui
  qui écrit le test.

### Audit complet : le flux disponible ne mesurait pas ce qu'on annonçait

Demandé par le propriétaire (« on a fait ajout sur ajout »). L'audit a suivi le
fil des trois bugs de la veille — tous des **bases implicites jamais
vérifiées** — et en a trouvé deux autres du même sang, dont un qui faussait le
score de tout l'univers.

**Le critère « conversion en cash » mettait 0 sur 7 aux meilleurs générateurs
de trésorerie.** Relevé sur les fiches publiées : Microsoft 4,9 % de marge de
flux disponible, Alphabet 5,1 %, Meta 9,4 %, Amazon 0,4 %. Aucun de ces
chiffres n'est une marge de flux disponible au sens usuel. La fiche de
Microsoft affirmait « sur 100 € de bénéfice comptable, 12 € finissent en cash
réel ». `info["freeCashflow"]` de Yahoo ne mesure pas ce que notre phrase
annonce — et nous téléchargions déjà le tableau de flux qui, lui, le dit.

- Le flux disponible est désormais **calculé** (exploitation − investissements
  industriels), plus récupéré. Yahoo ne sert qu'en repli.
- Le **dénominateur suit le numérateur** : la marge se calcule sur le chiffre
  d'affaires du MÊME exercice, pas sur un douze-mois-glissant d'une autre
  provenance.
- La **conversion est calculée dans le screener**, flux disponible ÷ résultat
  net du même exercice, du même document, dans la même devise. `note_v4` ne la
  déduit plus du quotient de deux marges hétérogènes — c'est ce quotient qui
  donnait 12 % à Microsoft.

**Deux fiches publiaient un fait faux sur leur croissance.** Adyen : « chiffre
d'affaires en croissance de −33,3 % par an ». Western Digital : « −10,5 % par
an ». Toutes deux à 0 sur 7. Toutes deux fausses : Adyen est passée du volume
traité au revenu net en 2023 (÷4,8 en une année), Western Digital a séparé
SanDisk (÷3,0). On mesurait à travers une marche de périmètre.

- Une série de chiffre d'affaires est **tronquée à sa dernière marche
  descendante d'un facteur 3** : on mesure sur le périmètre qui est encore
  celui de la société. Adyen passe à +19,2 %, Western Digital à +23,4 %,
  Blackstone à +20,3 %.
- Une marche **montante** est conservée : c'est la signature de
  l'hypercroissance (Nebius ×9 puis ×6, CoreWeave ×14 puis ×8), et la tronquer
  effacerait ce qu'on veut voir.
- **Réservé au chiffre d'affaires**, et c'est essentiel : Broadcom passe de
  2,84 à 0,64 € de bénéfice par action en 2019 par pur amortissement
  d'acquisitions, sans rien céder. Le chiffre d'affaires mesure le périmètre,
  le bénéfice ne mesure que lui-même.
- La régularité lit la même série tronquée, et se retire quand il ne reste plus
  assez d'années — plutôt que de compter une fausse année de recul.

**Marge nette glissante contre marge d'exercice.** 27 fiches sur 95 écartent de
plus de 5 points, 6 de plus de 20 (Micron 55,9 % contre 22,8 %, SanDisk +34,2 %
contre −22,3 %). Ce ne sont PAS des erreurs : un retournement de cycle met
douze mois à traverser un exercice clos. La marge d'exercice est désormais
publiée à côté, et l'infobulle le dit quand l'écart dépasse 20 points.

**Constaté, non corrigé** — ce sont des décisions de produit, pas des bugs :
19 fiches restent publiées sans entrée dans `universe.json` (dont CRM, cité par
le propriétaire dans la tâche des positions détenues) ; elles sont
inatteignables depuis le front, donc inoffensives, mais leur nombre grandit à
chaque rotation de thème.

### Le PER d'époque était faussé par les dividendes — et la note avec lui

Question du propriétaire : « je ne comprends pas le PER courant vs la valeur du
tableau PER pour cette année ». Elle a mis au jour trois défauts distincts,
dont un qui touchait directement le score.

**1. Le cours historique était le mauvais.** Le screener tirait tout d'une
seule série de prix, `auto_adjust=True` — ajustée des splits ET des dividendes.
C'est la bonne base pour une tendance, un z-score, un RSI : c'est du rendement
total. C'est la MAUVAISE pour un PER, parce que l'ajustement rétroactif des
dividendes déflate tout le passé, d'autant plus qu'on remonte loin et que le
rendement est élevé. Les multiples d'époque sortaient donc systématiquement
trop bas, et leur **médiane** avec eux — or cette médiane pilote le critère
« histoire », 8 points sur les 25 de la valorisation. Chaque société
distributrice était comparée à un passé artificiellement bon marché, donc
jugée chère aujourd'hui. Un titre à 3 % de rendement sur quinze ans encaissait
~35 % de sous-estimation sur ses exercices les plus anciens.
Le même appel rend désormais les deux séries (`Adj Close` pour la tendance,
`Close` pour les PER) — aucun coût réseau supplémentaire.

**2. Un BPA Yahoo antérieur à un split donnait un multiple faux.** Un cours
ajusté des splits vit dans la base d'actions d'aujourd'hui ; les BPA d'EDGAR y
sont ramenés explicitement, ceux de la fenêtre Yahoo sont « tels que publiés »,
donc dans la base de leur époque. Leur quotient était faux du facteur du split.
Ces exercices sont maintenant RETIRÉS du calcul, pas approximés.

**3. Le graphique changeait de base de cours en silence** — c'est la confusion
que le propriétaire a vue. Les exercices publiés valent au cours de leur
clôture, les estimations au cours du jour ; le saut entre les deux se lisait
comme un saut de bénéfices. Un point **« aujourd'hui »** (losange ambre) est
posé entre les deux, à sa place, et une phrase dit ce qui change.

### Les projections de bénéfice mélangeaient deux monnaies

Trouvé en inspectant les données publiées après le run. Les deux jeux
d'estimations de Yahoo ne vivent pas dans la même devise : le chiffre
d'affaires estimé est en devise COMPTABLE, le bénéfice par action estimé en
devise de COTATION (c'est ce qui rend `per_previsionnel` valide pour un ADR).

**TSM publiait 331,25 TWD de bénéfice par action et nous en projetions 16,82.**
Le taux de croissance qui en sortait n'était pas une opinion de marché, c'était
un taux de change. Six fiches étaient touchées (TSM, ASX, CCJ, RACE, ABBN.SW,
VWS.CO) — et RACE est le cas le plus dangereux, parce que 9,01 → 9,80 avait
l'air parfaitement plausible.

Les estimations de BPA sont désormais ignorées quand les deux devises diffèrent
(le bénéfice reste prolongeable depuis le seul historique, cohérent avec
lui-même) ; le chiffre d'affaires n'était pas concerné.

### La trajectoire attendue devient lisible, et le bénéfice s'affiche

Deux manques signalés le même jour : « on ne voit pas combien exactement » et
« est-ce qu'on sait aussi projeter le bénéfice ? ». Le bénéfice par action ÉTAIT
projeté par le screener depuis le premier jour — il n'était affiché nulle part.

- **Le chiffre est écrit au-dessus de chaque barre projetée** (fourchette
  comprise), au lieu d'être réservé au tableau replié.
- **Un tableau « trajectoire attendue »** dépliable donne CA et bénéfice par
  action, avec la nature **par cellule** : une année peut porter un consensus
  de chiffre d'affaires et déjà notre arithmétique sur le bénéfice. Une case
  vide ou le signe ⌁ dit qu'on a refusé de prolonger, et le motif est au survol.

### La troncature oubliée : il y en avait trois, pas deux

Symptôme relevé sur le même run : **44 fiches plafonnaient toujours à
EXACTEMENT 12 exercices, toutes éligibles EDGAR**, alors que le plafond était
passé à 20 et que d'autres fiches atteignaient 13 à 16.

L'entrée « on se tronquait soi-même » avait nommé DEUX points de troncature et
les avait branchés sur les constantes. Il y en avait un troisième, en amont des
deux autres : `construire_fonda()`, qui transforme les faits du greffe en bloc
`fonda`, gardait `max_an=12, max_tr=20` écrits en dur dans sa signature. Elle
coupe **avant** que quiconque ait vu les données — et dans une chaîne de
troncatures, la plus étroite gagne toujours. Relever les deux suivantes ne
pouvait rien changer.

- Les trois bornes lisent désormais `MAX_EXERCICES` / `MAX_TRIMESTRES`.
- Un test compare la signature aux constantes, pour que la prochaine borne
  écrite en dur échoue au lieu de brider silencieusement l'historique.
- Trouvé sans réseau, en relisant la chaîne d'appel : le conteneur de
  développement n'atteint pas `data.sec.gov` (proxy), et attendre un run pour
  diagnostiquer aurait coûté une demi-heure de plus.

### On se tronquait soi-même : le plafond d'historique passe de 12 à 20 exercices

Trouvé en cherchant comment un concurrent affiche quarante ans d'historique.
Relevé sur les fiches publiées : **52 sur 97 comptaient EXACTEMENT 12
exercices**, le plafond de l'accumulateur. Elles n'étaient pas limitées par la
source — le greffe de la SEC nous rendait déjà des exercices jusqu'à 2008 —
mais coupées par notre propre garde-fou de taille, hérité de l'époque où
seule la fenêtre Yahoo de 4 exercices existait.

- `MAX_EXERCICES` (20) et `MAX_TRIMESTRES` (24) nommés dans `edgar.py`,
  partagés par les DEUX points de troncature (l'apport EDGAR et
  l'accumulateur inter-run) qui les codaient en dur chacun de son côté.
- Coût : ~50 octets par exercice et par fiche. Gain : jusqu'à huit exercices
  de plus pour les 52 titres concernés, donc des médianes de PER et des
  taux de croissance calculés sur une vraie durée.

### Trajectoire attendue jusqu'à 2030, et les multiples enfin affichés

Deux manques signalés par le propriétaire sur la fiche Nebius : le PER
n'apparaissait nulle part alors qu'il pilote un quart de la note, et aucune
projection n'était visible.

- **PER courant et PER prévisionnel** rejoignent le bloc métriques de toutes
  les fiches. Un prévisionnel NÉGATIF n'est pas affiché comme un multiple —
  il dit « pertes attendues », ce qui est son sens réel (Nebius : PER 77,6×,
  prévisionnel négatif car les analystes attendent une perte).
- **`projections()`** — trajectoire du CA et du BPA jusqu'en 2030, avec une
  frontière que rien ne doit brouiller : les DEUX exercices que les analystes
  couvrent réellement portent `nature:"consensus"` et sont repris tels quels ;
  tout ce qui va au-delà porte `nature:"extrapolé"` et n'est QUE de
  l'arithmétique. *(Cette entrée disait « aucun analyste ne publie par société
  à cinq ans ». C'est faux — voir la correction en tête de journal. Ce qui est
  vrai : notre source s'arrête à deux exercices.)*
- **Trois gardes contre le mensonge classique de l'exercice** : la croissance
  DÉCROÎT linéairement vers 3 % (le taux nominal de long terme d'une économie
  développée) au lieu d'être prolongée à taux constant ; le taux de départ est
  borné par la croissance démontrée (même prudence que le PEG) puis plafonné
  à 25 % — sans ce plafond, Nebius projetait un chiffre d'affaires multiplié
  par vingt en cinq ans ; et un BPA en perte n'est jamais prolongé, seul le
  chiffre d'affaires l'est (cas Nebius, encore). *Ces gardes se sont révélées
  insuffisantes le lendemain : voir « le refus de prolonger » ci-dessus.*
- **Affichage** : barres hachurées, trait vertical séparant le publié de
  l'attendu, et une phrase sous le graphique qui dit où s'arrête l'opinion
  des analystes et où commence notre prolongation. Hors note, toujours.
  14 tests + vérification navigateur en 1440 px et 390 px.

### Les métiers de bilan n'ont plus AUCUN critère de qualité retiré

Question du propriétaire, qui a mis le doigt sur la faiblesse restante :
« une banque ne devrait pas être tirée vers la moyenne sur une métrique qui
n'existe pas pour elle — comment faire alors ? ». La réponse n'est ni la
renormalisation pure (le sans-faute en trois épreuves de Schwab, 35/35 sur
23 points mesurés), ni la pondération prudente (présumer 55 % sur une
métrique qui n'existe pas est incohérent) : c'est la SUBSTITUTION, comme
pour le cours/actifs nets en valorisation.

- **La conversion en cash → le rendement des actifs (ROA)** : combien les
  actifs au bilan produisent de bénéfice — l'étalon bancaire classique.
  Rampe continue 0,3 % → 1,3 % (7 pts).
- **Dette/capitaux propres → le levier actifs/fonds propres** : combien
  d'euros d'actifs reposent sur un euro de fonds propres. Rampe inversée
  25× → 8× (5 pts) : un assureur très capitalisé sature, un levier de
  territoire Credit Suisse prend zéro. Le levier cesse d'être « la matière
  première du métier » qu'on refuse de juger : il est jugé à l'aune du
  métier.
- Les deux se lisent au bilan déjà téléchargé (Total Assets), aucun appel
  de plus. Sans donnée : retrait motivé « actifs au bilan non publiés ».
- Conséquence de doctrine : la pondération prudente de la renormalisation
  ne s'applique plus, pour les métiers de bilan, qu'aux VRAIES données
  manquantes — plus jamais aux métriques sans objet, qui ont désormais
  toutes leur équivalent-métier (ROA, levier, cours/actifs nets).
  15 tests.

### Historique profond : le greffe de la SEC parle aussi IFRS

Le déséquilibre de mesure le plus profond de la note v4 : onze exercices
pour juger NVIDIA, trois pour TotalEnergies — non parce que la donnée
n'existe pas, mais parce que Yahoo ne garde que quatre ans et qu'EDGAR
était limité aux sociétés US en US GAAP. Or la moitié de nos titres
« courts » DÉPOSENT à la SEC : les émetteurs étrangers cotés aux
États-Unis y déposent leur 20-F sous la taxonomie ifrs-full, dans leur
devise comptable d'origine.

- **edgar.py v2** : quand les concepts us-gaap sont vides, les mêmes
  séries sont relues sous ifrs-full (CA, résultat — part des actionnaires
  de la mère de préférence, pour ne pas gonfler la marge des groupes à
  minoritaires — et BPA), exclusivement dans l'unité de la devise
  comptable annoncée par Yahoo : un 20-F allemand se lit en EUR, un
  taïwanais en TWD, jamais autre chose.
- **Table US_EQUIV** pour les cotations d'origine dont le programme 20-F
  est actif et vérifié : ASML.AS→ASML, SAP.DE→SAP, TTE.PA→TTE, AZN.L→AZN,
  HSBA.L→HSBC, UBSG.SW→UBS. Les tickers déjà américains (Pinduoduo,
  TSMC, Sony, Toyota, Alibaba, ARM…) passent sans mapping. La gate du
  screener n'est plus « US en USD » mais « connu du greffe ».
- **Étage 2 — l'apport vérifié** (`data/apport_historique.json`) pour les
  non-déposants (Samsung, les domestiques japonaises, Hermès, Adyen…) :
  un bloc par ticker avec source citée, montants en devise comptable,
  refus au chargement si la devise ne correspond pas, mêmes gardes
  d'extension que l'EDGAR, provenance src:"apport" par entrée. Créé vide :
  le conteneur de développement n'atteint pas les sites IR et la doctrine
  interdit de saisir des chiffres de mémoire — il se remplit depuis les
  rapports annuels, titre par titre, et l'accumulateur conserve ensuite.
- 15 tests. Reste hors de portée à ce stade : les non-déposants sans
  apport saisi — leur fenêtre s'allonge d'un exercice par an via
  l'accumulateur, comme avant.

### L'écart à la trajectoire cesse de s'appeler « décote »

Le libellé « Décote vs tendance » empruntait le vocabulaire de la
valorisation pour une mesure de momentum — le cours comparé à sa propre
trajectoire décennale, pas à la valeur de l'entreprise. La confusion
était inévitable (cas vécu : Hermès à −45 % de sa trajectoire ET 8,3/25
en valorisation, deux affirmations parfaitement compatibles mais
illisibles sous le même mot). Les fiches disent désormais « sous sa
trajectoire / au-dessus de sa trajectoire », et l'entrée du lexique
explique le renommage.

### Les sources se chaînent enfin

Jusqu'ici chaque donnée avait UNE source et un trou restait un trou. Elles
s'enchaînent désormais, chaque maillon ne comblant que ce que les précédents
ont laissé vide, et inscrivant sa provenance dans `fonda_source` :

1. **résumé Yahoo** (`info`) — inchangé, source de première main ;
2. **états financiers** (bilan, tableau de flux) — flux disponible, capitaux
   propres, dette, ROE ;
3. **comptes publiés** (Yahoo + EDGAR pour les US) — marge nette du dernier
   exercice, PER courant déduit du cours et du BPA publié ;
4. **Finnhub**, titres américains uniquement, en dernier recours.

- **`chainer_comptes()`** : deux grandeurs se déduisent des comptes sans
  aucune hypothèse — la marge nette (résultat ÷ chiffre d'affaires du dernier
  exercice) et le PER courant (cours ÷ BPA publié). Repli annuel là où Yahoo
  donne du douze-mois-glissant : moins frais, mais exact et vérifiable. Garde
  ADR : pas de PER quand la devise comptable diffère de la cotation, sinon on
  diviserait des dollars par des dollars taïwanais.
- **`chainer_finnhub()`** : placé en BOUT de chaîne, pour limiter l'asymétrie
  américaine qu'il crée — il ne sert que lorsque les trois maillons universels
  ont tous échoué. Les unités sont converties explicitement (marge en pourcents
  chez Finnhub contre fraction chez Yahoo, dette en ratio contre pourcentage) :
  c'était le piège qui aurait offert une vingtaine de points indus. L'ordre est
  préservé — la validation croisée tourne AVANT le remplissage, sans quoi elle
  comparerait Finnhub à lui-même et le seul détecteur de donnée douteuse du
  système s'éteindrait.
- 12 tests, dont la conversion d'unités et le piège ADR.

### Régression corrigée : le métier de bilan se déduit du métier

Défaut introduit puis rattrapé le même jour, et la leçon vaut d'être écrite.
Le drapeau « métier de bilan » — qui déclenche la rampe bancaire du ROE, le
retrait motivé de la conversion de cash et du ratio d'endettement, et le
critère cours/actifs nets — valait `secteur financier ET FCF absent`. Ce
raccourci confondait deux choses très différentes : « la métrique n'a pas de
sens pour ce métier » et « la donnée manque chez notre fournisseur ».

Le correctif de couverture publié une heure plus tôt est allé chercher le
flux disponible dans les états financiers. Le drapeau s'est donc éteint pour
**tous** les titres : le critère cours/actifs nets est devenu du code mort
(zéro titre concerné), la rampe bancaire n'a plus jamais été appliquée, et
HSBC s'est retrouvée notée **0,7/5 sur un levier qui EST son métier** et
**7/7 de conversion du cash** sur un flux qui ne suit que les mouvements de
dépôts. La couverture montait — ce qui ressemblait à un succès — pendant que
la justesse baissait.

- **Table `_INDUSTRIES_BILAN`** : banques, marchés de capitaux, crédit
  hypothécaire et assurance, par industrie Yahoo (les deux graphies du tiret).
  Restent hors périmètre, à dessein, les réseaux de paiement, les places de
  marché et agences de notation, les gérants d'actifs et les courtiers
  d'assurance — tous dégagent un vrai flux disponible.
- **Aucun flux disponible n'est reconstitué pour un métier de bilan** : mieux
  vaut un champ vide qu'un « 113 % de conversion » flatteur et vide de sens.
- Effet mesuré sur HSBC : le ROE repasse de 2,7/9 à 5,6/9, et ses deux
  critères sans objet redeviennent des retraits motivés.
- **Règle générale, désormais testée** : un critère de métier se déduit du
  métier, jamais de l'état d'une source de données. 4 tests de non-régression.

### Couverture : on cesse de noter sur des données qu'on n'est pas allé chercher

Doctrine posée par le propriétaire : un critère retiré faute de donnée est un
défaut, pas une fatalité — sauf quand la métrique n'a réellement pas de sens
pour le métier. L'audit des 125 retraits du run v4 a classé les causes :
38 % mathématiquement indéfinis (croissance depuis une base négative),
**21 % récupérables dans des données déjà téléchargées**, 18 % fenêtre
historique trop courte, 17 % métier de bilan (légitimes), 7 % devise
comptable différente de la cotation.

- **Nouvelle fonction `etats_complements()`** : le résumé Yahoo (`info`) ne
  renseigne ni `freeCashflow`, ni `debtToEquity`, ni `returnOnEquity` pour
  une large part des titres non américains — Disco Corporation à Tokyo et
  SK Hynix à Séoul n'ont aucun des trois. Or le tableau de flux et le bilan
  sont DÉJÀ téléchargés pour la section « Chiffres publiés ». On y lit
  désormais le flux disponible (ligne publiée, sinon exploitation moins
  investissements), les capitaux propres et la dette totale, avec repli sur
  les libellés alternatifs. Universel — toutes places, toutes devises, donc
  sans l'asymétrie américaine d'EDGAR — et sans un seul appel réseau de plus.
- **Provenance publiée** (`fonda_source`) : la fiche dira lesquels des trois
  champs ont été reconstruits, comme `src:"edgar"` le fait pour l'historique.
- Gardes : capitaux propres négatifs refusés (un levier inversé serait
  trompeur), dette omise plutôt que mise à zéro quand le bilan n'en porte
  pas, capex pris en valeur absolue quel que soit son signe de dépôt.
  13 tests ajoutés — dont un qui a attrapé un vrai défaut, les capitaux
  propres négatifs passant le test de vérité de Python.

### Correctif d'affichage

- **Les valeurs des jauges débordaient de leur colonne.** La note v4 publie
  des points décimaux (« 23,5/25 », sept caractères) là où la v3 tenait en
  cinq, et la classe `.mv` des jauges entrait en collision avec le badge de
  mouvement au classement, dont elle héritait bordure et marges intérieures.
  Classe renommée en `.mval`, colonne élargie, chiffres tabulaires. Vérifié
  au navigateur en 1440 px et en 390 px.

### Correctif d'exploitation

- **Déploiement GitHub Pages** : les publications de 12h00 et 12h14 ont
  échoué en `deployment_queued` puis expiré, deux déploiements concurrents
  s'étant mutuellement bloqués — le site est resté trois commits en
  arrière, servant les scores v3 alors que la v4 était publiée sur `main`.
  Relancé manuellement. Leçon, symétrique de celle des runs de screener :
  ne pas pousser deux commits à quelques minutes d'intervalle, et vérifier
  la conclusion du déploiement plutôt que la présence du commit sur la
  branche — ce dernier contrôle ne prouve rien.

## [4.0.0] — 2026-08-06

### Note v4 : la refonte du scoring — informer, pas prédire

Refonte complète de la notation, décidée après un audit chiffré de
24 semaines d'archives : les piliers v3 étaient orthogonaux (bien), mais le
timing notait à contretemps (IC **négatif**, −0,33), les barèmes en
escalier fabriquaient des faux mouvements (NOW : 81 → 66 → 72 en trois
semaines pour des variations minuscules), et 8 banques sur 9 plafonnaient
au même 10/30 de valorisation faute de FCF. Aucun backtest d'optimisation :
la doctrine est de noter factuellement une entreprise, son prix et sa
dynamique, avec une logique financière empirique.

- **Nouveau moteur `note_v4.py`**, pur et testé (41 tests) — partition
  MECE par domaine de donnée, chaque information comptée UNE fois :
  **Qualité 35** (niveaux des comptes : marge nette médiane 9, ROE 9 avec
  garde anti-levier et rampe bancaire dédiée, conversion cash 7, bilan 5,
  constance 5) · **Croissance 25** (dérivées : TCAM CA 7, TCAM BPA 7
  dilution comprise, régularité 4, attendu analystes 7 — l'estimé ne
  dépasse jamais le démontré) · **Valorisation 25** (cours÷comptes : PER
  face à sa médiane d'époque 8, PEG maison 7 = PER prévisionnel ÷ min des
  deux croissances, rendement des bénéfices 5, rendement du cash 5) ·
  **Momentum 15** (cours÷cours : écart MM21/MM200 en continu 6, position z
  en cloche symétrique 6, RSI en cloche 3).
- **Rampes continues partout** : plus un seul seuil-falaise. Les pénalités
  chase/death, le bonus décote, les points de cross et le multiplicateur
  de confiance disparaissent — leurs effets utiles sont absorbés par les
  cloches (l'étirement pénalise désormais dans les DEUX sens).
- **Retrait motivé + renormalisation** : un critère incalculable est
  retiré avec son motif affiché (« le FCF n'a pas de sens pour un bilan
  bancaire », « devise comptable différente de la cotation »…) et la note
  se renormalise. Chaque fiche publie sa **couverture**. Fin de la
  pathologie bancaire.
- **Pondérations dérivées de cinq principes** (documentés dans Apprendre) :
  un point = de la confiance dans la mesure ; l'estimé ≤ le démontré ; la
  redondance se paie ; l'asymétrie se respecte ; le discriminant réel
  compte. Propriétés systémiques : ~58 % de la note sur l'historique
  comptable vérifié, marché (V+M) plafonné à 40 pts.
- **Consensus analystes sorti de la note** (biais acheteur structurel,
  signal retardataire) — reste affiché en objectif de cours. Un système de
  lettres A+…D a été conçu, testé, puis écarté : le /100 continu dit plus.
- **Gardes de données** : marge médiane bornée à ±100 % (l'artefact de
  holding NBIS à 1764 % ne note pas), FCF yield refusé quand la devise
  comptable diffère de la cotation (le « 34 % » de TSM divisait des TWD
  par des USD), NaN Yahoo filtrés à l'entrée du moteur.
- **Publication** : `breakdown["note"]` complet (blocs, 16 critères avec
  une phrase en français chacun, motifs, couverture) dans watchlist.json
  et charts/<T>.json ; blocs compacts q/c/v/m + couverture dans
  universe.json ; ROE et dette/CP enfin publiés (`roe_pct`,
  `debt_eq_pct`). Fiches : 4 jauges proportionnelles, dépliant « Détail de
  la note », « — » pour un bloc non notable. Agent et fiches éditoriales
  alignés. Avant/après sur 10 témoins : JPM 46 → 75 (la correction
  bancaire), NVDA 77 → 84, TTE 71 → 56 (CA en recul depuis le pic 2022,
  payé de sa décroissance), NBIS 45 → 36 malgré un momentum parfait — le
  plafond marché fonctionne.

## [3.13.0] — 2026-08-06

### L'historique officiel : les dépôts SEC entrent dans les fiches

- **Nouveau module `edgar.py`** : pour les sociétés américaines publiant en
  dollars, la section « Chiffres publiés » est étendue par les dépôts
  officiels 10-K/10-Q (EDGAR, la SEC) — dix ans et plus de CA, résultat net
  et BPA, donc un PER par exercice profond et des variations trimestrielles
  complètes immédiatement, sans attendre que l'accumulateur hebdomadaire se
  remplisse. Ce n'est pas un troisième vendeur : c'est le document déposé
  par la société sous responsabilité légale, la matière première que les
  vendeurs retraitent.
- **Extend-only et provenance** : EDGAR n'écrase jamais une valeur Yahoo
  (les retraitements peuvent différer, on ne mélange pas à date égale) ;
  chaque entrée ajoutée porte `src:"edgar"` et la fiche l'affiche («
  Historique étendu par les dépôts officiels SEC »). Q4 dérivé (exercice
  moins trois trimestres) pour CA et résultat net, jamais pour le BPA, qui
  n'est pas additif. Garde de vraisemblance contre les erreurs d'échelle de
  tagage (rapport > 5 entre exercices adjacents → tout l'apport refusé).
- Hors périmètre, à dessein : les émetteurs étrangers cotés US (20-F, IFRS)
  gardent leur fenêtre Yahoo ; aucun champ du score ne vient d'EDGAR.
- **Leçons du premier jour d'EDGAR**, corrigées dans la journée : la SEC
  exige un User-Agent avec contact (0/117 en silence sinon — tout échec
  réseau est désormais loggé en clair) ; les BPA déposés sont « tels que
  déposés », jamais réajustés des splits postérieurs (NVIDIA ÷40 → PER à
  0,4×, chaque BPA est ramené dans la base d'actions actuelle via les dates
  de splits) ; les émetteurs changent de balise XBRL au fil des normes (les
  alias sont fusionnés entre époques, sinon 2015-2016 perdaient leur CA).
- **PER par exercice et deux exercices à venir** sur les fiches : multiple
  d'époque (cours de clôture de l'exercice / BPA dilué publié — jamais pour
  un ADR, devise comptable ≠ cotation) et lignes « e » au cours actuel /
  BPA estimé par les analystes. Convention assumée face aux tableaux de
  consensus type Hiboo, qui rapportent TOUT au cours du jour : notre
  colonne dit ce que le marché payait réellement à l'époque.
- **Phrases de synthèse** sous les chiffres publiés : TCAm du CA avec ses
  exercices de baisse, marge nette moyenne et son évolution, multiple payé
  en MÉDIANE (une année de bulle écrase une moyenne). Purement factuel,
  minimum 4 exercices, une période en pertes dit ses pertes.
- Confort de lecture : le relevé du graphe de cours s'affiche dès
  l'ouverture (dernier point) et se recale à chaque changement de fenêtre ;
  l'historique des chiffres publiés s'affiche en entier ; la note
  pédagogique sous la table est retirée (sur-explication).
- Robustesse des données : la vue MAX ne disparaît plus sur un cours nul ou
  négatif (artefacts Yahoo de l'historique lointain, purgés à la source et
  écartés au front) ; arrondi adaptatif des petits cours ; dédoublonnage
  inter-runs des trimestres datés à quelques jours d'écart ; fiches
  versionnées par l'horodatage du run (plus de cache périmé le jour d'une
  sortie) ; le won affiché pour les places coréennes.
- **Verdict de la relecture sources** (même journée) : le remplissage des
  trous Yahoo par Finnhub est abandonné — champs sans trous observés,
  unités incompatibles, auto-concordance qui aurait tué la validation,
  asymétrie US/Europe. Finnhub reste un validateur. Corrigés au passage :
  le bug latent `totalRevenue or 1` (une donnée absente offrait 8 pts), les
  21 fausses « Marge FCF 0,0 % » des financières (trou → « — » désormais),
  l'alerte « discordante YF:0.0% » sur un champ jamais mesuré, et deux
  textes qui contredisaient la période réelle de la croissance CA.

## [3.12.0] — 2026-08-05

### Les fiches montrent la trajectoire, plus seulement l'instant

- **Nouvelle section « Chiffres publiés » sur chaque fiche** : CA, EBITDA et
  résultat net des ~5 derniers exercices et ~6 derniers trimestres, barres +
  table avec variations, bascule Annuel/Trimestres — le format des plateformes
  de courtage. Le score photographie un instant (marges TTM, un trimestre de
  croissance) ; la fiche montre désormais d'où vient la société.
- Les montants sont affichés dans la **devise comptable** (`financialCurrency`),
  pas celle de cotation : TSM cote en dollars et publie en dollars taïwanais,
  on montre ce qui est publié, sans conversion silencieuse.
- Variations honnêtes : exercice vs exercice précédent ; trimestre vs **même
  trimestre un an plus tôt** (comparer T4 à T3 raconterait la saisonnalité).
  Pas de pourcentage quand la base est négative ou absente. Un trimestre en
  perte se voit : barre rouge sous la ligne de zéro.
- Source : les états financiers yfinance (`income_stmt`), même robinet que le
  reste du screener, toutes places de cotation — deux requêtes de plus par
  titre, fail-soft, jamais bloquantes pour le score. Banques sans EBITDA :
  la colonne disparaît, l'entrée reste.
- Côté Actualités le même jour : rotation des illustrations (mémoire des
  photos parues + filtre de quasi-doublons + filtre de pertinence des
  requêtes Commons), mode maintenance `--reillustrer` (photo remplacée,
  texte intact), et interdiction de l'humour sur les sujets graves.
- **Le mode plein écran des graphiques est retiré une seconde fois** : la
  version réintroduite la veille (calque + paysage forcé sur mobile) ne
  fonctionnait pas sur appareil réel. Retrait complet — bouton, calque,
  portail DOM, rotation, remappage tactile ; le graphe, ses presets, le
  double-curseur et le relevé sous le dessin sont inchangés.

## [3.11.0] — 2026-08-03

### Le plein écran revient, et se couche dans le bon sens

- **Retour du mode plein écran des graphiques de fiches** (retiré plus tôt le
  même jour), avec la nouveauté qui le justifie : **sur téléphone tenu en
  portrait, le calque pivote de 90° et s'affiche directement en paysage** —
  plus besoin de tourner l'appareil pour lire dix ans de cours. L'API Screen
  Orientation exigerait le vrai plein écran navigateur, refusé par iOS : la
  rotation CSS, elle, marche partout.
- Dans ce repère tourné, tout reste utilisable : le réticule suit le doigt
  (coordonnées écran retraduites dans le repère du calque), l'infobulle
  flotte d'un seul côté du réticule, le double-curseur et les presets
  répondent au doigt. Tourner physiquement le téléphone lève la rotation CSS
  et repasse au paysage naturel.
- **Dimensionnement en deux passes** : premier rendu sur une estimation, puis
  redessin calé sur la boîte réellement laissée par la mise en page — un
  budget fixe se trompait toujours quelque part et le graphe recouvrait la
  barre de boutons. Garde-fou CSS en plus : le dessin ne peint jamais
  par-dessus « Quitter ».
- Ton du point du matin d'Actualités : léger et complice, sur les
  formulations uniquement — jamais sur les faits ni aux dépens de qui perd de
  l'argent. Le post du 3 août a été réécrit dans ce ton (réécriture permise
  le jour même seulement).

## [3.10.0] — 2026-08-03

### La performance ne compte plus les virements

- **Le graphique « Performance depuis le lancement » trace désormais l'indice
  de performance**, plus le capital : un virement de +10 k€ faisait sauter la
  courbe d'un graphe intitulé « Performance » — un flux n'est pas un
  rendement. Axe en %, courbe continue à travers les injections, marqueurs ⊕
  conservés comme annotations de date.
- **La bande de cinq cartes disparaît**, ses informations rejoignent leurs
  sections : la valeur du portefeuille (et la plus-value latente) en tête, à
  côté des deux performances, comme sur une plateforme classique ; le partage
  investi/liquidités et le compte de positions en en-tête du tableau des
  positions. Le « +11,7 % du capital versé » disparaît avec elle.

- **Injection de +10 000 € de liquidités** (deuxième après celle du 5 mai).
  Elle a révélé le défaut de la mesure : l'ancienne formule divisait par le
  capital total versé, donc le virement faisait « chuter » la performance de
  +17,6 % à +11,7 % sans qu'aucune position n'ait bougé. Symétriquement, ne
  pas grossir la base l'aurait transformé en gain. Les deux lectures étaient
  fausses.
- **Passage à la performance pondérée par le temps**, la méthode des fonds :
  les rendements sont chaînés entre injections, l'argent frais ne compte ni
  comme gain ni comme perte. Résultat : **+28,8 % depuis janvier**, soit
  +17,1 pp au-dessus du MSCI World — et le jour d'un versement, le
  pourcentage affiché ne bouge pas d'un centième (c'est testé).
- Un **registre `injections`** entre dans portfolio.json : date, montant, et
  capital constaté juste après, figé à l'écriture — l'historique étant
  plafonné à ~260 points, le relire aurait fait changer la performance en
  silence le jour où une date d'injection en serait sortie.
- **Raffinement le jour même** : un versement reste **hors périmètre tant
  que l'IA n'a pas pu en disposer** — entre le virement et son run
  hebdomadaire suivant, le cash est un dépôt administratif qui ne dilue pas
  la performance des positions. Il entre dans le périmètre au premier run de
  l'agent, investi ou non : « ou non » est délibéré, ne compter le cash
  qu'une fois investi permettrait de paraître brillant en n'investissant
  jamais, et la fongibilité rend « investi » indécidable de toute façon.
- **Audit tous scénarios** (à la demande du propriétaire, « comme une
  plateforme d'investissement ») : trois trous fermés. Les **retraits** sont
  désormais spécifiés — montant négatif, effectif immédiatement, la
  performance ne bouge pas d'un centième au moment du retrait. Le
  **changement d'année** aurait cassé l'écart au benchmark au 1er janvier
  2027 : les indices étaient ancrés au 1er janvier de l'année courante, ils
  le sont maintenant au lancement du portefeuille (config.PORTFOLIO_DEBUT).
  Le **drawdown maximal** se mesure sur l'indice de performance et non plus
  sur le capital : la mesure capital comptait un retrait comme un plongeon
  et laissait une injection masquer un vrai repli — le drawdown publié
  passe honnêtement de −5,2 % à **−8,5 %**, l'injection de mai avait
  rehaussé la courbe en plein repli.
- La colonne `perf` de l'historique est migrée (la série de capitaux, le fait
  brut, ne bouge pas) ; les producteurs (agent, update_prices) partagent la
  même fonction dans config.py ; le prompt de l'agent décrit la nouvelle
  mesure pour qu'il ne raconte pas des écarts en euros qui ne correspondent
  plus au pourcentage ; le lexique explique la méthode. 12 tests dédiés.

---

## [3.9.0] — 2026-08-03

### Actualités — l'éditorial quitte le portefeuille et devient un journal

- **Nouvelle page** : un post quotidien les matins de bourse (le point de la
  veille et de la nuit), et chaque semaine l'analyse du portefeuille IA,
  déplacée depuis la page Portefeuille. Cartes photo + résumé, clic pour lire.
- **« On n'invente jamais rien » est structurel, pas déclaratif.** Le modèle
  ne reçoit que des dépêches réelles (Finnhub, le flux déjà utilisé par
  l'analyse hebdo) et chaque section doit citer les dépêches dont elle sort :
  une section sans source est rejetée à la validation. Les dépêches citées
  sont publiées en bas de chaque post, avec lien.
- **Deux genres, deux règles.** Le quotidien est factuel : aucun conseil,
  aucune prédiction, aucune mention de Signal — le vocabulaire de
  recommandation fait échouer la validation. L'hebdo est une interprétation
  par nature, étiquetée comme telle.
- **Le jour creux ne se meuble pas.** Moins de cinq dépêches exploitables :
  pas de post, CI rouge, la page sert l'existant. Il n'existe pas de
  demi-post.
- **Un post publié est immuable**, comme l'historique du portefeuille.
  L'index se reconstruit depuis les fichiers : il ne peut pas diverger.
- **Photo automatique par sujet** (décision propriétaire) : requêtes Commons
  bornées par une table écrite à la main, licences libres uniquement,
  provenance complète dans le post, et un post sans photo reste valide.
- La page Portefeuille garde un résumé de trois lignes du raisonnement, avec
  lien vers l'archive. Le run hebdomadaire matérialise le post hebdo — sans
  ça, l'archive n'existerait pas, portfolio.json ne gardant que la semaine
  courante.

---

## [3.8.0] — 2026-08-03

### Une watchlist dont le critère est juridique, et une page Apprendre illustrée

#### Éligibles PEA — le siège social, pas la place de cotation

- Troisième watchlist thématique : les **vingt meilleurs scores parmi les
  titres logeables dans un PEA**. Le critère d'entrée n'est pas une mesure de
  marché mais une propriété juridique de l'émetteur — son siège social doit
  être dans l'UE ou l'EEE (art. L221-31 du code monétaire et financier).
- C'est tout l'intérêt de la liste : **huit des quarante-huit éligibles cotent
  en dollars à New York**. Nebius, STMicroelectronics, NXP et Ferrari sont des
  sociétés néerlandaises ; Accenture, Eaton, Medtronic et Seagate des sociétés
  irlandaises. Un filtre par place de cotation les manquerait toutes.
  Symétriquement, le Royaume-Uni est sorti au Brexit et la Suisse n'a jamais
  été dans l'EEE : HSBC, ABB, Nestlé et Chubb sont écartés.
- Les **inéligibilités sont listées avec leur motif** plutôt que passées sous
  silence. Sans ça, l'absence d'un titre qu'on croyait européen se reprend à
  chaque relecture. Linde est le seul cas limite : siège à Dublin mais
  résidence fiscale britannique revendiquée dans ses dépôts, éligibilité
  discutée — écarté par prudence, motif écrit.
- **Coût API nul.** Les quarante-huit éligibles étaient déjà tous scorés,
  l'univers reste à 229 titres. La watchlist n'est qu'une projection de plus
  sur un scoring inchangé.

#### Une troisième forme de thème

- `kind: "filtre"`, à côté de « curé » et « calculé ». Un thème curé publie
  toute sa liste ; un thème calculé applique une règle au breakdown — qui ne
  porte pas le siège social et ne le portera jamais, ce n'est pas une mesure de
  marché. Le filtre déclare l'appartenance et borne la publication aux N
  meilleurs scores.
- Piège corrigé à l'écriture : **la couverture se mesure avant le bornage**.
  Rapportée aux vingt lignes publiées, elle vaudrait 20/48 à chaque run et le
  thème serait perpétuellement « dégradé » par sa propre définition. Un
  garde-fou qui hurle en permanence ne garde plus rien.
- Front : le libellé « ce qui invaliderait cette thèse » devient « ce qui
  périmerait cette liste » pour ce kind — une liste d'éligibilité ne
  s'invalide pas, elle se périme, par une redomiciliation ou une réforme.
  Les textes de thèse acceptent désormais plusieurs paragraphes.

#### L'avertissement qui compte

- Le champ « biais » du thème et la section 07 d'Apprendre portent la même
  mise en garde : **l'éligibilité juridique du titre et l'acceptation de la
  ligne par le courtier sont deux choses différentes**, en particulier pour
  les lignes new-yorkaises. Et un certificat de dépôt (ADR) n'est jamais
  logeable, quel que soit le siège de l'émetteur.
- Apprendre disait « la plupart des valeurs suivies sont américaines, donc non
  éligibles ». Le raccourci était faux et c'est exactement celui que cette
  watchlist corrige : il est réécrit.

#### Apprendre — une amorce visuelle par section

- Les douze sections s'ouvrent sur une bande d'image, avant leur numéro et leur
  titre. Format 16/5 : répétée douze fois, une bande haute ferait douze pauses
  dans la lecture au lieu de douze repères.
- `tools/photos_apprendre.py` fabrique les images depuis Commons **et pose
  lui-même les balises** dans `apprendre.html` : légende, texte alternatif,
  crédit et empreinte de contenu n'ont qu'une seule source. À douze images,
  les maintenir à la main garantissait de voir tôt ou tard une légende sous la
  mauvaise photo.
- Le bas de chaque bande se dissout par un masque et non par un dégradé peint :
  la page porte un fond animé dont un dégradé vers une couleur fixe se
  décrocherait.
- Trois bandes ont raté leur sujet au premier tirage, les candidats étant jugés
  en planche contact au format 16/9, bien plus large. D'où trois réglages par
  image — cadrage vertical, luminosité, contraste — et la règle qui va avec :
  on regarde le résultat au format final.

---

## [3.7.0] — 2026-08-02

### L'infrastructure de l'IA prend sa forme, et le site se met à parler humain

Journée de retours utilisateur, presque tous portant sur la même chose : ce
que le site DIT, et ce qu'il montre sans le dire.

#### Le thème infra-IA, resserré puis structuré

- Cinq éditeurs de logiciels (PLTR, SNOW, DDOG, MDB, NET) sortent : le titre
  promettait de l'infrastructure, la liste contenait un pari sur les usages,
  ce que la thèse dit explicitement ne pas faire. NextEra sort aussi, en
  contradiction frontale avec le texte des biais qui exclut la production
  renouvelable. Les hyperscalers restent, et la thèse l'assume désormais.
- La chaîne devient une DONNÉE et non un commentaire : sept maillons publiés
  dans universe.json, affichés comme en-têtes de groupe dans la liste. Ordre
  physique de la chaîne, score décroissant à l'intérieur de chaque couche.
- Entrées : ARM au maillon Compute, Constellation Energy et GE Vernova à
  l'énergie, SanDisk à la mémoire (scindé de Western Digital en février 2025,
  la liste datait d'avant), CoreWeave, Nebius et Sharon AI aux néoclouds.
  De 46 à 60 titres déclarés.
- Nommage des couches : anglicisme quand c'est le terme de métier (Compute,
  hyperscalers, packaging), français partout ailleurs.

#### La règle des 5 ans d'historique devient un avertissement

Un titre coté depuis moins de cinq ans n'est plus exclu. À la place, sa fiche
affiche que la droite de régression n'est pas exploitable en l'état. Seul
reste bloquant le plancher technique de ~200 séances, sans lequel MM200 et RSI
sont incalculables. Conséquence assumée : CoreWeave (1,3 an) est publié avec
un score, et l'avertissement dit ce que ce score ne vaut pas.

#### Ce que le site montrait sans le dire

- **Mouvement au classement** : la watchlist principale marque les entrants et
  les rangs gagnés ou perdus. Le champ existant mesurait un écart de SCORE, ce
  qui ne dit rien de la place occupée.
- **Suite de liste** : « ▾ 54 autres valeurs » sous le rail. Il défilait depuis
  toujours, mais son seul indice était un dégradé de 12 px.
- **Parité des fiches** : le breakdown complet voyage dans le fichier graphique,
  donc une fiche thématique affiche les mêmes données qu'une fiche du top 30.
- **Actualité pour tous les titres** : la revue d'actualité n'était réservée au
  top 30 que par règle de catégorie, pas par manque de source. Une fiche sans
  actualité porte désormais une marque qui distingue « on a cherché, il n'y
  avait rien » de « on n'a jamais cherché ».

#### Le texte

- **Plus de tirets cadratins** : 1 295 occurrences retirées des textes publiés,
  et la règle inscrite dans les deux prompts pour que les prochains n'en
  contiennent pas. C'est la ponctuation qui trahit le plus une machine.
- **Les étoiles disparaissent de la source** : retirées de l'affichage il y a
  quelque temps, elles étaient toujours calculées par le screener et injectées
  dans le prompt éditorial, qui les recopiait dans la prose publiée.
- **Noms d'usage dans les listes** : TSMC, SK hynix, Munich Re plutôt que la
  raison sociale tronquée à 22 caractères par le fournisseur de données.
- Descriptions des watchlists réécrites, plus courtes et plus directes.

#### Interface

- **Graphique en plein écran**, y compris sur iPhone (calque CSS et non l'API
  Fullscreen, que Safari refuse hors vidéo). Le dessin épouse la forme de
  l'écran, le zoom choisi est conservé.
- **Mobile** : ouvrir un thème laisse la liste visible au lieu de sauter à la
  première fiche. Le libellé « Sections » n'est plus coupé. Les badges décoratifs
  sont retirés.

#### Illustrations

Trois photographies du domaine public remplacent les planches générées : la
salle des marchés du NYSE des années 1960, le supercalculateur Sierra du
laboratoire Lawrence Livermore, une chambre forte de 1967. Aucune ne montre le
logo d'une société détenue par la watchlist qu'elle illustre — le siège de HSBC
a été écarté pour cette raison. Provenance et licences dans
assets/themes/CREDITS.md.

#### Correctifs

- Le plein écran passait SOUS le rail et l'en-tête sur mobile : `.stage` est un
  contexte d'empilement, un enfant en position:fixed y reste prisonnier quel que
  soit son z-index. Le bloc est déplacé dans `<body>` le temps du plein écran.
- La taille de l'univers était écrite en dur dans la page Apprendre et mentait
  depuis le premier élargissement (210 annoncés, 229 réels). Elle est désormais
  lue dans les données.

---

## [3.6.0] — 2026-08-01

### Chaque titre a sa fiche — et les watchlists prennent leur forme définitive

Suite directe des retours utilisateur sur la 3.5.0 : les vues thématiques
étaient des coquilles (une phrase, pas de graphique, pas d'analyse) et la
homepage tassait quatre cartes par ligne.

- **Une fiche rédigée pour chacun des ~180 titres tagués**, plus seulement le
  top 30. Génération parallélisée (8 appels simultanés : 138 min → ~17 min,
  sous le plafond CI) avec mise en cache du préambule commun — jamais activée
  jusqu'ici. Deux niveaux honnêtement distingués : fiche complète pour le
  top 30 ; fiche courte (résumé, business, perspectives, thèses) pour les
  titres thématiques, SANS rubrique Actu — aucune source datée n'est collectée
  pour eux, l'afficher « à générer » aurait promis un contenu qui ne viendrait
  jamais. Coût annuel : ~29 $ → ~80 $, désormais mesuré et publié à chaque run.
- **Un graphique par titre** (`charts/<TICKER>.json`), chargé à l'ouverture de
  la fiche. Le payload était déjà calculé pour tout l'univers puis jeté pour
  tout ce qui n'était pas top 30. Fini le monolithe bloquant : 561 Ko au
  premier rendu → 0, ~19 Ko par fiche ouverte.
- **Homepage** : une carte par ligne (le texte était illisible à quatre par
  ligne), toutes STRICTEMENT identiques — la principale perd son traitement à
  part et gagne sa planche (« classement / seuil »). Ouvrir une watchlist
  affiche directement sa première valeur : la vue liste intermédiaire
  dupliquait le rail de gauche. La thèse du thème, son inversion et ses biais
  vivent dans un bandeau repliable au-dessus de la fiche.
- **Incident évité en audit** : le front « graphiques à la demande » a été
  déployé avant le run de données qui produit `charts/` — le site a servi des
  fiches sans aucun graphique jusqu'au run correctif. Même famille que
  l'incident universe.json : publier du code qui attend des données pas encore
  produites. Leçon consignée.
- **Photos réelles** : outillage de récolte sur Wikimedia Commons (domaine
  public/CC0 uniquement, manifeste de provenance versionné) via le runner CI.
  Verdict de la première récolte : ~41 candidats, qualité insuffisante pour
  couvrir 13 thèmes avec cohérence — décision d'illustration documentée dans
  l'audit.
- Nettoyages d'audit : README (pipeline à jour), apprendre.html (« uniquement
  de la watchlist » → univers publié ; 125 → 210 tickers), CHANGELOG rattrapé.

## [3.5.0] — 2026-08-01

### Watchlists thématiques — une homepage, treize vues, un seul moteur

Jusqu'ici Signal publiait une liste : le top 30 d'un univers de 133 titres.
L'univers passe à 210 titres et se lit désormais par thèse d'investissement,
sans qu'aucun titre ne soit scoré deux fois.

- **Architecture « un seul scoring, N projections »** : `themes.py` devient la
  source unique de vérité, l'univers du screener en est dérivé, et une
  watchlist thématique n'est qu'un filtre + tri sur les mêmes résultats. Coût
  API marginal : zéro pour tout titre déjà présent. `watchlist.json` est
  strictement inchangé — trois consommateurs lisent son contrat en dur.
- **13 watchlists** : 11 curées (semi-conducteurs, mémoire & stockage, IA,
  robotique, finance, monopoles d'information, compounders industriels,
  consommation, santé, défense, électrification) et 2 **calculées** par une
  règle chiffrée sur le breakdown, donc sans aucune liste à maintenir : décote
  vs tendance et qualité durable. Ces deux-là sortent de notre propre moteur.
- **Chaque thème publie sa thèse, son inversion et ses biais.** L'inversion
  — ce qui invaliderait la thèse — est obligatoire : c'est le garde-fou
  anti-promotion. Mémoire et défense sont publiés en statut « observation »,
  leur catalyseur étant largement consommé.
- **Nommage** : le thème « moat » demandé devient *Compounders industriels*.
  Le screener mesure des marges, un ROE et un endettement — ni la durabilité,
  ni l'avantage concurrentiel. Même refus d'emprunt de vocabulaire que pour
  « marge de sécurité ». *Tech* est écarté (c'est le pool par défaut : 15 des
  30 titres actuels) et *Water* aussi (4 titres éligibles au-dessus de 25 Md$).
- **Univers achetable élargi** : l'agent peut acheter les ~190 titres tagués,
  via une union explicite — la garde anti-hallucination n'est pas assouplie, et
  un titre sans secteur n'est pas rendu achetable. Le prompt explicite le piège
  du choix élargi (Barber & Odean) : plus de candidats n'autorise pas plus de
  décisions.
- **Concentration thématique**, angle mort de la règle R1 : les thèmes
  transverses se répartissent sur quatre secteurs Yahoo, donc R1 ne les voit
  jamais comme un bloc alors que leurs composants baissent ensemble. Toute
  thèse pesant plus de 25 % du capital est signalée.
- **Devises JPY et KRW** (places de Tokyo et Séoul), jamais gérées jusqu'ici :
  sans elles un titre japonais était traité en dollars, soit un facteur ~150
  d'erreur. Le code « TSE » est volontairement écarté de la détection — il
  désigne Tokyo chez certains fournisseurs et Toronto chez d'autres.
- **Validation préalable des symboles** (`validate_tickers.py` + workflow
  dédié) : l'environnement de développement n'ayant pas accès à Yahoo, les 81
  nouveaux symboles ont été confrontés à l'API réelle depuis un runner avant
  tout élargissement. 78 validés ; CEG, GEV (historique trop court), ROG.SW
  (symbole introuvable, remplacé par l'ADR RHHBY), BESI.AS et EFX
  (capitalisation sous le seuil) écartés — avec leur motif publié.
- **Garde de couverture par thème** : le seuil global de 60 % ne protégeait
  plus rien à 210 titres (il faudrait en perdre 84 avant d'échouer), donc un
  thème vidé par une panne de place serait publié vide, job vert — le mode de
  panne exact de l'incident du 27/07. Un thème sous 70 % est publié avec sa
  bannière ; trois thèmes dégradés font échouer le run.
- **Sleep Finnhub conditionné** aux appels réellement émis : 61 titres non-US
  court-circuitent la requête sans consommer de quota, soit 30 s de run
  récupérées chaque semaine.

## [3.4.0] — 2026-07-31

### L'agent dimensionne ses achats — règles assouplies, prose fiabilisée

Déclencheur : l'achat SPGI du 31/07 annonçait « 1 titre ~env. 400-500€ » dans sa
justification alors que le moteur exécutait 3 titres pour 1 078 € — le sizing était
une formule mécanique (conviction → % du capital) que l'agent ne connaissait pas,
et sa prose inventait des chiffres. Le plancher de liquidités (5 %) affiché comme
respecté était en réalité franchi (1,5 % post-trade).

- **Sizing par l'agent (`montant_eur`)** : chaque décision ACHAT porte désormais le
  montant en euros choisi par l'agent lui-même — nouvelle ligne comme renforcement.
  Le moteur borne mais ne choisit plus : cash jamais négatif, 20 % max par ligne
  renforts compris (R2), 100 € minimum (anti-poussière). Fallback conviction
  (7/4/2 %) si le champ manque. Le montant visé est journalisé dans l'ordre
  (`montant_vise_eur`) pour comparer demande/exécution.
- **Discipline de justification** : interdiction explicite dans le prompt d'annoncer
  un nombre de titres ou un prix unitaire estimé (l'agent ne les connaît pas —
  quantité et prix d'exécution sont calculés par le moteur) ; il cite à la place le
  montant engagé et son poids (« j'engage ~1 200 € soit 5 % du capital »).
- **R1 concentration assouplie** : plus aucune réduction automatique de taille entre
  30 et 65 % (information injectée dans le contexte, l'agent arbitre). Au-delà de
  65 %, l'achat reste possible avec `conviction="forte"` et un pari sectoriel
  explicitement assumé — l'agent peut être bull sur un secteur, publiquement.
- **R3 plancher de liquidités supprimé** : l'agent peut investir jusqu'à 100 % du
  cash si l'opportunité le justifie (descendre sous ~5 % doit être motivé dans la
  justification). Seul garde-fou dur conservé : les liquidités ne peuvent jamais
  devenir négatives.
- **Plus-value latente en €** : colonne dédiée sur chaque ligne du portefeuille
  (sur mobile elle remplace la colonne Valeur), recalculée quotidiennement, injectée
  dans le contexte de l'agent, et stockée dans `positions[].plus_value_latente_eur`.
- **Fiche watchlist — lisibilité du canal** : les pastilles de valeurs au bout du
  graphe sont supprimées (elles masquaient les repères σ une fois sur deux — les
  valeurs restent dans la ligne de métriques et l'infobulle au survol) ; les 4
  repères σ sont garantis dans la marge droite ; l'intensité du canal (fonds +
  liserés) s'adapte à sa hauteur à l'écran — sur 20 ans/MAX, l'échelle log étirait
  le tunnel jusqu'à le rendre presque invisible, il reste désormais net.
- Tests : 14 scénarios moteur (all-in, caps R2, cluster forte/modérée, fallback,
  montant invalide, renforcement, anti-poussière, PV latente) — 14/14.

## [3.3.0] — 2026-07-28

### Canal de régression interactif + décote vs tendance sur les fiches

- **Graphique de fiche (nouveau)** : chaque fiche de la watchlist ouvre désormais sur
  le cours en échelle log avec sa droite de régression long terme et son canal ±1σ/±2σ,
  MM21/MM200, pastilles de valeurs, survol (réticule, 4 points, infobulle) compatible
  tactile. Périodes : fenêtre officielle (10/20/25 ans selon profil) + 20 ans si
  l'historique le permet + MAX, et curseur libre début/fin. Le canal est **re-fitté sur
  la période affichée** (exploration, méthode identique au screener — rééchantillonnage
  mensuel uniforme, fit sur l'axe du temps, holdout 1 mois) ; la légende distingue
  toujours la vue « fenêtre officielle du score » de l'exploration.
- **Décote/surcote vs tendance** : écart du cours au prix de tendance, en % de la valeur
  de tendance (convention Graham). Nommage délibérément honnête — PAS « marge de
  sécurité » : la référence est une trajectoire historique, pas une valeur intrinsèque
  (section pédagogique dédiée dans Apprendre + lexique). Avertissement automatique
  au-delà de 2σ : value trap (décote) / rally chase (surcote).
- **Objectif consensus analystes** : affiché en potentiel (%), à titre indicatif
  (correction pence→livres pour les cotations LSE — famille de bug ×100 connue).
- **charts.json** : payload graphique du top 30 généré par le screener depuis les
  données déjà téléchargées (zéro appel API supplémentaire) — échantillonnage hebdo
  (2 ans) + mensuel (au-delà), dernier point à la date réelle de cotation, écriture
  atomique `allow_nan=False`, fail-soft par titre. Les nouveaux champs du breakdown
  (`prix_tendance`, `decote_pct`, `regression_sigma`, `target_*`) sont hors signature
  éditoriale (pas de régénération des fiches Claude).
- **Agent** : décote/surcote et consensus injectés dans les prompts (passes 1 et 2)
  avec la règle 14 — « information, jamais un signal seul » (value trap / rally chase /
  biais optimiste du consensus).

## [3.2.1] — 2026-07-28

### Hotfix : watchlist 100 % EU publiée le 27/07 (barre Yahoo vide en pré-ouverture US)

- **Incident** : le run hebdo du 27/07 (11h30 UTC, marchés US fermés) a reçu de Yahoo
  une barre du jour avec Close=NaN pour les titres US. Sans dropna côté screener,
  MM21/MM200/RSI devenaient NaN et le garde anti-NaN (3.1.0) écartait le titre —
  94 titres évincés « données indisponibles », watchlist publiée : 30/30 valeurs
  EU/GB sur les 39 survivants, job CI vert. Même famille que l'incident 3.0.1,
  corrigé à l'époque dans portfolio/update_prices (`last_valid_close`) mais jamais
  dans le screener. Détecté par un utilisateur ; aucun impact portefeuille (zéro
  ordre passé ce jour-là).
- **Fix** : `dropna` sur les cours avant tout calcul (volume réaligné sur l'index),
  et **garde de couverture** : si moins de 60 % de l'univers est scoré, le run
  échoue bruyamment SANS publier — la watchlist précédente reste en ligne et le
  job passe rouge (même philosophie fail-loud que `allow_nan=False`).

## [3.2.0] — 2026-07-20

### Réallocation : renforcement et allègement des lignes existantes

L'agent ne connaissait que deux gestes — ouvrir une ligne, la fermer entièrement.
Il sait désormais ajuster les TAILLES (complément naturel des rotations de 3.1.0) :

- **Renforcement** : un ACHAT sur un titre déjà détenu renforce la ligne (PRU moyen
  pondéré, base fiscale cumulée, date d'origine conservée — le compteur R01 ne repart
  pas). Plafond R2 (20 % du capital) enfin appliqué en code : blocage si la ligne y est
  déjà, budget plafonné à la marge restante sinon. L'ancien blocage
  `deja_en_portefeuille` disparaît — la règle R2 et le plafond de positions, écrits
  comme si le renforcement existait, cessent d'être du code mort.
- **Allègement** : une VENTE avec `allegement_pct` (1-99) ne cède que ce pourcentage
  (arrondi au titre entier). Base fiscale proratisée — le PFU ne porte que sur la
  fraction vendue ; PRU, date et thèse d'origine conservés sur le reliquat.
  Anti-poussière : reliquat < 100 € → vente totale. R01 et friction s'appliquent
  comme à toute vente.
- **Doctrine (règle 13)** : renforcer uniquement sur éléments nouveaux (jamais
  « moyenner à la baisse » sans catalyseur documenté) ; alléger typiquement pour
  dégonfler une position proche des 20 % après un rally, sans sortir de la thèse.

## [3.1.0] — 2026-07-18

### Rotations de portefeuille + correctifs d'audit complet

- **Rotations (nouveau)** : l'agent peut désormais vendre une position jugée moins
  attractive pour financer une meilleure opportunité watchlist quand le cash manque.
  Mécanique : les VENTES d'un run s'exécutent avant les ACHATS (tri stable, stop-loss
  toujours en tête) et la règle R3 « liquidités < 5 % » est réévaluée dynamiquement en
  cours de run (l'état pré-run figé bloquait l'achat même après la vente). Doctrine
  stricte côté prompt (règle 12) : R01 respectée, comparaison explicite sortant/entrant
  dans les `raison`, friction (frais + PFU) à couvrir, max 1 rotation par run.
- **Audit complet (4 volets : screener, agent, CI/scripts, frontend/données)** :
  - screener : watchlist.json écrit de façon atomique + `allow_nan=False` (un NaN
    faisait planter JSON.parse côté site — classe d'incident 3.0.1) ; gardes NaN
    MM200/RSI/régression/VIX ; la validation croisée Finnhub est réservée aux tickers
    US (le strip des suffixes comparait LVMH aux métriques de Moelis & Co et dégradait
    la confiance jusqu'à ×0.7 sur les valeurs européennes) ; badge `GER` (SAP.DE
    s'affichait « US ») ; `load_previous` ne fabrique plus un changelog fantôme.
  - agent : gardes d'exécution en code (achat hors watchlist rejeté, plus de
    liquidités négatives via `max(1,…)`, coût total ≤ cash, prix de vente aberrant
    ×3/÷3 refusé, base fiscale reconstituée si `montant_investi` absent — l'ancien
    défaut taxait 100 % du produit) ; mode panique sticky si le benchmark est
    infetchable (le fail-open désarmait la Règle 03 pendant les pannes Yahoo) ;
    fenêtre panique sur 5 vraies séances ; devise CHF (.SW) supportée.
  - sécurité : sortie IA filtrée en code (allowlist `<b>` seulement) + échappement
    systématique côté front (news Finnhub, raisons d'ordres, biais, règles) + URLs
    restreintes à http(s) → fermeture du vecteur XSS stockée via injection de prompt ;
    clés API Finnhub en header (plus jamais dans une URL loggable).
  - CI : le job hebdo devient rouge si une étape IA échoue (la watchlist reste
    publiée) — fini les données figées des semaines sans alerte ; `.gitignore`
    complété (`.env*`, venv, settings locaux).
  - divers : `index.html` affiche un message si le JSON est illisible (au lieu d'une
    page vide), Copenhague classée Europe, libellé « mis à jour chaque lundi »
    corrigé, `migrate_orders_v2.py` archivé dans `notes/archive/`.

## [3.0.1] — 2026-06-10

### Hotfix incident NaN + audit complet (6 auditeurs) — site portfolio figé du 02 au 09/06

- **Incident** : depuis le 02/06, Yahoo renvoie une dernière ligne Close=NaN pour les places
  EU au moment du cron 22h UTC. Le NaN corrompait portfolio.json (6 positions EU + benchmarks),
  `json.dump` l'écrivait (non-standard), `JSON.parse` navigateur le rejetait → page figée,
  CI 100 % verte. Fix : `last_valid_close()` (dropna) sur tous les fetchs + `save_json_atomic()`
  (tmp+rename, `allow_nan=False` = échec bruyant) + backfill de l'historique 02→09/06.
- **Ledger corrigé** : 3 ventes de début mai (NOW, INTU, LSEG.L) comptaient le rachat même-jour
  dans la base de coût → pertes reportables 4 005,77 € → **778,29 €** (−3 227,48 € fictifs).
  Bug de la version de code de l'époque, non reproductible avec le code actuel.
- **Devises nordiques** : ORSTED.CO coté en DKK était traité en EUR (`detect_currency` mappait
  .CO/.ST/.OL → EUR). Support DKK/SEK/NOK ajouté (`get_eur_rate`), position requantifiée 7 → 52
  actions (impact valeur ≈ nul : l'erreur s'auto-annulait, la quantité dérivant du même prix).
- **Robustesse** : load strict de portfolio.json (plus de reset silencieux à 10 k€ sur JSON
  corrompu), erreur API Claude → exit 1 SANS écrire (plus de « Erreur : … » publié sur le site),
  garde 0/N prix dans update_prices, garde sanité prix ×3 (GBp ×100, splits), cap historique
  52 → 260 entrées, workflows sérialisés (concurrency) + échec explicite sur conflit de rebase.
- **Screener (hors scoring, gelé)** : le breakdown publie la fenêtre de régression **effective**
  après fallback NaN (avant : un z 20y pouvait être étiqueté « cyclical_25y ») ; la justification
  gère le mode val_pts inversé (GC frais) et ne prétend plus qu'une « chase de rally » est
  pénalisée par val_pts (la pénalité réelle est z-based) ; textes VIX périmés nettoyés.
- **Docs alignées v3** : docstring screener, methodology.md (sections détaillées), apprendre.html
  (val_pts hors-score, RSI 2 pts, footer), SKILL.md, lexique index.html (analystes 3 pts),
  WATCHLIST_SIZE unifié (config.py = source unique, 30), learning v3.0.1 publié sur portfolio.html.

## [3.0.0] — 2026-06-01

### Scoring v3 — refonte en 4 composantes (Qualité 45 / Valorisation 30 / Timing 22 / Analystes 3)

La qualité et le prix pilotent le score (75 pts) ; le timing devient un **garde-fou** (22 pts).

- **Qualité (45)** : marge nette 8 + marge FCF 8 + **ROE 12 (nouveau)** + croissance CA plafonnée 10 + dette 7.
- **Valorisation (30)** : PEG 15 + **FCF yield 15 (nouveau)**. PER absolu exclu (pénaliserait la qualité).
- **Timing (22)** : cross 10 (échelle interne /20 ÷ 2) + pente MM21 4 + volume 3 + RSI 2 + régression 3.
- **Analystes** : 5 → 3 pts. Ajustements chase/death/décote inchangés ; gate décote → qualité ≥ 30/45.
- **val_pts (drawdown 52w) et VIX : informationnels, hors score.**
- ⚠️ **Breaking change JSON** : clés breakdown renommées — `momentum`/`fondamentaux`/`vix_multiplier`
  supprimées ; `qualite`/`valorisation`/`timing` ajoutées ; `cross_pts` passe de l'échelle 0-20 à 0-10
  et `analystes` de max 5 à max 3. Les archives `notes/watchlist_archive/` antérieures au 2026-06-01
  sont sur l'ancien schéma — ne pas comparer les sous-scores entre schémas.
- Propagation : index.html (4 meters + lexique), generate_analyses.py, apprendre.html, methodology.md.
- Scoring **gelé pour le trimestre** — mise à l'épreuve par le portefeuille IA en réel (anti-resulting).

## [2.2.1] — 2026-06-01

- CHASE / décote-qualité : retrait du palier léger ±2 (1,5σ) — ne garder que les extrêmes
  (un compounder vit le plus souvent au-dessus de sa tendance). Magnitudes finales −6/−4 et +6/+4.

## [2.2.0] — 2026-05-31

- CHASE / décote-qualité renforcés : pénalités/bonus doublés (−3/−2 → −6/−4, +3/+2 → +6/+4) —
  choix « le timing prime », appliqué aux extrêmes seulement. Ajout puis retrait du 3e palier ±2 (cf. 2.2.1).

---

## [2.1.0] — 2026-05-31

### Repositionnement éditorial — posture neutre, retrait du discours de backtest

Recentrage de tout le frontend et de la documentation sur une posture **neutre et honnête** :
Signal applique de façon disciplinée des **méthodes établies et publiques** (analyse technique
façon Murphy, momentum Jegadeesh-Titman 1993, value Graham-Dodd, régression vers la moyenne),
**sans aucune prétention d'alpha**. C'est une **expérimentation** : la méthodologie est mise à
l'épreuve par l'**observation du portefeuille IA en réel**, pas par des backtests.

- **Retrait de l'infrastructure backtest du récit produit** : la section 6 d'`apprendre.html`
  (« Comment Signal se mesure honnêtement » → « Sur quoi repose la méthode ») ne s'appuie plus
  sur `backtest.py` / `backtest_compare.py`, la décomposition par régime, le Deflated Sharpe ni
  les chiffres d'alpha CAGR. Elle explique désormais les méthodes publiques sous-jacentes et
  pose la validation **en avant, en conditions réelles** comme choix méthodologique central.
- **Suppression des revendications d'alpha backtesté** dans le discours : plus aucun « +13,5pp/an »
  ni « alpha CAGR équitable » présenté comme preuve de surperformance. La friction (frais + PFU)
  reste documentée, mais comme exigence d'une comparaison honnête, pas comme générateur d'alpha.
- **`portfolio.html`** : l'entrée de lexique « Alpha MSCI » devient « Écart au benchmark » —
  on conserve l'observation de performance relative vs MSCI World, on retire le cadrage « alpha »
  et l'objectif de surperformance. Le bloc de performance et les KPI étaient déjà neutres.
- **`apprendre.html`** : le barème valorisation conditionné au cross est reformulé sur la logique
  publique de mean-reversion (plus de claim « +86% médiane » issu d'un test empirique). Tout le
  socle pédagogique (analyse technique/fondamentale, schémas SVG) est conservé tel quel.
- **`notes/ad_line_evaluation.md`** : références backtest/alpha neutralisées (voir ci-dessous).

> Note (corrigée 2026-06-10) : `backtest.py` / `backtest_compare.py` ont été **retirés du repo**
> lors de ce repositionnement (ils n'existent plus dans l'arbre tracké). Leur logique de scoring
> était restée à l'échelle v2 — toute comparaison avec les scores v3 serait invalide de toute façon.
> L'historique factuel des versions antérieures est conservé tel quel ci-dessous.

---

## [1.10.0] — 2026-05-10

> NB : les versions v1.6 → v1.9 ont été tracées dans `portfolio.html` learnings (07 mai 2026)
> sans être reportées ici à l'époque (FX bug GBP, sector bonus caché, order memory dans le prompt,
> z-score holdout 20j, stop-loss catastrophe R08, MSCI EUR-denominated). On reprend à 1.10.0
> pour maintenir la cohérence avec le versioning learnings.

### Architecture (portfolio_agent.py + sync_skill.py) — alignement skill ↔ prod

**Le skill `portfolio-analyst` existe désormais à 2 niveaux** :
- **User-level** : `~/.claude/skills/portfolio-analyst/` — master éditable. Claude Code en local le charge en priorité (hiérarchie personal > project) pour toutes les questions portfolio, dans ou hors repo Signal.
- **Project-level** : `<repo>/.claude/skills/portfolio-analyst/` — copie synchronisée, committée dans Git, déployée avec le code. Lue par `portfolio_agent.py` sur le runner GitHub Actions où le user-level n'existe pas.

**Synchronisation user-level → project-level via `sync_skill.py`** :
- Direction : user-level (master éditable) → project-level (copie déployable)
- Usage : `python sync_skill.py` avant chaque commit qui touche le skill
- Mode `--check` pour CI / pre-commit hook (échoue si désynchronisé)
- Pourquoi cette direction : tu édites naturellement le user-level via Claude Code, et Claude Code en local prime sur project-level de toute façon (hiérarchie)

**`load_skill_discipline()` (portfolio_agent.py)** :
- Lit désormais le project-level via chemin **relatif** : `Path(__file__).parent / ".claude" / "skills" / "portfolio-analyst" / "SKILL.md"`
- Marche partout où le repo est cloné (runner GitHub Actions inclus)
- Bug d'architecture v1.6.0-rc1 corrigé : la version initiale lisait `Path.home()` qui n'existe pas sur le runner

### Prompt agent (portfolio_agent.py)
- **Injection skill au début du prompt passe 2** via `load_skill_discipline()` — single source of truth
- **Watchlist top 10 enrichie** (passes 1 et 2) : ajout de `cross_slope_mm21_pct`, `cross_spread_pct` et **`signal_dynamics_warning`** (death cross qui se résorbe, golden qui s'affaiblit, rebond mean-reversion sur cross stale, affaiblissement post-rally). L'agent peut désormais lire le signal **en mouvement**, plus statiquement.
- **Règles non négociables 7 et 8** ajoutées :
  - R7 — Signal en transition : si `signal_dynamics_warning` non-vide, traiter le cross technique comme ambigu, ne pas vendre/acheter sur ce signal seul
  - R8 — Cross-validation analystes/cours : pour titres en zone d'incertitude (score 30-65), si consensus très favorable mais cours en dégradation 6-12m, suspecter une dégradation des données screener (effet change, périmètre M&A, désync data)
- **Watchlist top 10 enrichie** (passes 1 et 2) : ajout de `cross_slope_mm21_pct`, `cross_spread_pct` et **`signal_dynamics_warning`** (death cross qui se résorbe, golden qui s'affaiblit, rebond mean-reversion sur cross stale, affaiblissement post-rally). L'agent peut désormais lire le signal **en mouvement**, plus statiquement.
- **Règles non négociables 7 et 8** ajoutées :
  - R7 — Signal en transition : si `signal_dynamics_warning` non-vide, traiter le cross technique comme ambigu, ne pas vendre/acheter sur ce signal seul
  - R8 — Cross-validation analystes/cours : pour titres en zone d'incertitude (score 30-65), si consensus très favorable mais cours en dégradation 6-12m, suspecter une dégradation des données screener (effet change, périmètre M&A, désync data)

### Scoring (screener.py)
- **`signal_dynamics_warning`** étendu : 4 conditions désormais détectées
  - Death Cross en cours de résorption (récent + pente MM21 positive + spread tendu)
  - Golden Cross en cours d'affaiblissement (récent + pente MM21 négative + spread tendu)
  - **Rebond mean-reversion sur cross stale** (death stale + pente MM21 forte + cours largement sous MM200) — setup B opportunities.md
  - **Affaiblissement post-rally sur cross stale** (golden stale + pente MM21 négative + cours largement au-dessus MM200)
- **Archive snapshot hebdo** : `notes/watchlist_archive/YYYY-MM-DD.json` créé à chaque run du screener. Permet dans 6+ mois de reconstituer un historique fonda point-in-time pour backtester les 60% du score (Fondamentaux + Analystes) actuellement non testés (limitation reconnue ligne 12-14 de backtest.py).

### Validation
- À l'époque, un backtest baseline (2019-2024, 281 semaines) était utilisé comme garde-fou de non-régression du moteur de scoring. **Repositionné en v2.1.0** : ces chiffres ne sont plus présentés comme une preuve de surperformance ni un « alpha » revendiqué (cf. note honnête ci-dessous, déjà présente à l'époque).
- Note honnête : `backtest.py` simule la stratégie momentum-only (top N → achat mécanique). **Il ne simule pas Claude.** Les modifs prompt agent n'apparaîtront pas dans ce backtest. La validation réelle des règles 7/8 passe par l'observation live du portefeuille IA.

---

## [1.5.0] — 2026-05-06

### Architecture (portfolio_agent.py)
- **Deux passes Claude** : séparation analyste / décideur pour éviter la rationalisation LLM
  - Passe 1 (Claude Haiku) : analyse neutre de chaque position et opportunité — sans décision
  - Passe 2 (Claude Sonnet) : décisions basées sur l'analyse + thèses d'achat originales
- **Mémoire de la thèse d'achat** : `raison_achat` stockée dans chaque position au moment de l'achat
- **Obligation de delta documenté** : pour toute vente < 90j, le modèle doit citer la thèse d'achat originale et expliquer ce qui a concrètement changé — même signal relu différemment = vente refusée
- Analyse passe 1 injectée dans le prompt passe 2 (delta_these, état, qualité signal watchlist)

---

## [1.4.0] — 2026-05-06

### Scoring (screener.py)
- **Free Cash Flow margin** ajouté aux fondamentaux : +5 pts si FCF/CA > 15 %, +3 pts si > 5 %
  - Complémentaire à la marge nette — cap fondamentaux maintenu à 50 pts
- **Pénalité Death Cross** : −5 pts si Death Cross ≤ 30j, −3 pts si ≤ 60j (appliqué post-confiance, non compensable)
- **Changelog enrichi** : raisons de sortie spécifiques (Death Cross, momentum faible, fondamentaux insuffisants, surachat régression) au lieu du message générique
- `fcf_margin_pct` et `death_pen` ajoutés au breakdown JSON

### UX (index.html)
- **Tri alternatif** : boutons Score global / Fondamentaux / Momentum, actifs en temps réel et compatibles avec les filtres existants

### UX (portfolio.html)
- **Journal enrichi** : badge P&L réalisé + jours détenus sur les VENTE, badge score d'entrée sur les ACHAT
- **Stats P&L réalisé** : bloc résumé (trades clôturés, win rate, performance moyenne, P&L € cumulé)
- 20 ordres affichés par défaut avec bouton "voir les suivants"

---

## [1.3.0] — 2026-05-05

### Scoring (screener.py)
- **RSI gradué** : 10 pts en zone 40–60, 5 pts en 35–65, 0 sinon (remplace le binaire 10/0)
- **Fondamentaux 50 pts** (était 40) : redistribution depuis les analystes
  - PEG ratio : nouveau palier PEG < 1 → 15 pts (était 10 max)
  - EPS growth (`earningsGrowth` Yahoo Finance) ajouté : +5 pts si > 15 %, +2 pts si > 5 %
- **Analystes 10 pts** (était 20) : biais haussier structurel sell-side documenté (Barber 2001, Jegadeesh 2004)
- `min(50, fund_pts)` et `min(10, ana_pts)` dans le breakdown

### Contenu (index.html)
- Section "Comment fonctionne le scoring" mise à jour : RSI gradué, Analystes 10 pts, détail PEG
- **Section Lexique** ajoutée : 17 définitions en 4 catégories (Signaux techniques, Régression, Fondamentaux, Score & Consensus)

---

## [1.2.0] — 2026-05-05

### Refonte visuelle (portfolio.html)
- Thème dark complet aligné sur index.html (palette `#08080d` / `#0f0f16` / or `#e8a820`)
- Header frosted glass, card glow au survol
- SVG graphique de performance : gold `#e8a820`, grid `#2a2a38`, MSCI `#44445a`
- Correction couleurs SVG hardcodées (étaient `#d97706`)

---

## [1.1.0] — 2026-05-04

### Renommage WatchRadar → Signal
- Nom du projet, titres de pages, brand header, prompts Claude
- Email fictif `contact@watchradar.fr` supprimé (HTML statique + JS)
- Git bot identity : `bot@signal.fr` / `Signal Bot`
- Repo GitHub renommé `Kosmos-7/Signal`

### Refonte visuelle (index.html)
- Palette dark modernisée : `--bg: #08080d`, `--surface: #0f0f16`, or `#e8a820`
- Header sticky frosted glass (`rgba(8,8,13,0.88)` + `backdrop-filter: blur(20px)`)
- Hover cards : inset glow + `box-shadow` extérieur
- Score bars fondamentaux et analystes corrigés (`/50` et `/10`)

---

## [1.0.0] — Lancement initial

### Screener (screener.py)
- Univers de 90 valeurs (CAC40, DAX, AEX, OMX, LSE, S&P100, APAC)
- Scoring : Momentum (Golden/Death Cross MM21/MM200, RSI, volume, régression) + Fondamentaux + Analystes
- Régression log-linéaire avec z-score et fenêtres adaptées (10 ans tech, 20 ans autres)
- Validation croisée Finnhub + alertes news (guidance, M&A, réglementaire)
- Bonus sectoriel +3 pts (Technologie, Santé, Industrie, Finance)
- Concentration sectorielle alertée si > 5 titres dans un même secteur
- Export `watchlist.json` avec breakdown complet, changelog, distribution sectorielle

### Portfolio agent (portfolio_agent.py)
- Agent piloté par Claude Sonnet via Anthropic API
- Capital fictif 20 000 €, règles de survie (patience 90j, taille max 30 %, mode panique, stop-loss −15 %)
- Conversion multi-devises EUR/USD/GBP temps réel
- Historique de performance (52 semaines), max drawdown, trimestres négatifs
- Macro news via Finnhub, contexte CAC40 + MSCI World
- Export `portfolio.json`

### Interface (index.html + portfolio.html)
- Watchlist : fiches détaillées avec breakdown scoring, croisement MM21/MM200, régression, alertes news
- Portfolio : statut de survie, KPI, graphique SVG de performance, journal des ordres
- Filtres régime (Golden/Death Cross) et zone de régression
- GitHub Actions : workflow `watchlist.yml`, cron lundi 8h UTC, déploiement GitHub Pages
