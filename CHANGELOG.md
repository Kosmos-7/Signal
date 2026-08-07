# Changelog — Signal

Toutes les évolutions notables du projet sont documentées ici.
Format inspiré de [keepachangelog.com](https://keepachangelog.com/fr/).

---

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
  l'arithmétique — aucun analyste ne publie par société à cinq ans.
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
