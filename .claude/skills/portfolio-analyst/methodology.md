# Méthodologie d'évaluation d'un titre

Approche en 4 composantes (refonte v3, juin 2026). **Philosophie : la qualité et le prix pilotent le score (75 pts) ; le timing technique n'est qu'un garde-fou (22 pts) qui borne le downside — il pénalise fort les 2 pièges d'entrée (chaser un sommet, rattraper un couteau) mais n'apporte que peu en positif.** Validée empiriquement sur des décennies de recherche académique.

## Scoring synthétique : 100 points

```
Qualité du business →  45 pts  (marge nette 8 + marge FCF 8 + ROE 12 + croissance CA 10 + dette 7)
Valorisation        →  30 pts  (PEG 15 + FCF yield 15)
Timing (garde-fou)  →  22 pts  (cross 10 + pente MM21 4 + volume 3 + RSI 2 + régression 3)
Analystes           →   3 pts
                       ─────
                       100 pts   ± pénalités (chase −6/−4, death −5/−3) / bonus (décote +6/+4)
```

Pondération calibrée par l'expérience (le projet Signal applique cette logique en production sur 133 tickers).

> **Note v3 (juin 2026)** — La structure est passée de 3 piliers (Momentum 45 / Fondamentaux 50 / Analystes 5) à 4 composantes (Qualité 45 / Valorisation 30 / Timing 22 / Analystes 3). Les sections détaillées ci-dessous sont alignées sur l'échelle v3 (mise à jour 2026-06-10). La philosophie : qualité + prix pilotent, le timing borne le risque. `val_pts` et le VIX sont informationnels (hors score).

> ⚠️ **LA NOTE EN PRODUCTION EST LA v4 (Qualité 35 / Croissance 25 / Valorisation 25 / Momentum 15), moteur `note_v4.calcule_note`** — les barèmes v3 ci-dessous (cross 10, RSI 2, volume 3…) sont conservés comme grille de LECTURE manuelle des signaux, plus comme barème. Pour noter un titre exactement comme le screener : `from screener import score_ticker`. Hors dépôt, appliquer les formules du bloc ci-dessous.

## Bloc Momentum de la note v4.1 (15 pts — recomposé le 17/08/2026)

Quatre critères, calculés par `screener.score_ticker` et notés par `note_v4.calcule_note`. Principe : **chaque référence est observée** (un cours d'il y a 13 mois, un plus haut 52 semaines), jamais ajustée sur les données du titre — une droite de régression refittée court après le cours (pathologie mesurée : Kioxia 15/15 en plein krach de −43 %, fenêtre 2 ans, pente refittée +279 %/an).

| Critère | Pts | Formule | Garde |
|---|---|---|---|
| `momentum` | 6 | `cloche(ln(min(P, P₋₁ₘ)/P₋₁₃ₘ) / max(σ, 0.10) ; −1,5 ; 0,3 ; 2,0 ; 3,5)` — σ = écart-type des rendements log hebdo (W-FRI) sur ~2 ans × √52 | retiré sous 274 séances |
| `sommet` | 4 | `rampe(drawdown_52w_pct ; −40 ; −5)` | retiré sous 252 séances |
| `position` | 3 | `cloche(z ; −3 ; −1,5 ; 1 ; 3)` — le z de `calcul_regression`, inchangé | retiré si fenêtre effective < 1260 séances (5 ans) |
| `dynamique` | 2 | `rampe(pente MM21 sur 5 séances ; −3,5 ; +4,5)` | retiré si incalculable (jamais un 0 silencieux) |

Sources : Jegadeesh & Titman (1993) et Carhart (1997) pour le 12-1 ; Jegadeesh (1990) pour la réversion du dernier mois — d'où le `min()` : le saut du dernier mois protège du bruit de la *hausse* récente, mais un krach récent compte immédiatement ; MSCI Momentum Indexes pour la division par σ ; George & Hwang (2004) pour le plus haut 52 semaines (critère assumé asymétrique — l'anti-chase vit dans les deux cloches) ; Barroso & Santa-Clara (2015), Daniel & Moskowitz (2016) pour les krachs du momentum non ajusté du risque. Bornes figées sur les percentiles de l'univers du 17/08/2026 (`tools/calibration_momentum.py`) ; un critère incalculable est **retiré avec motif** et le bloc se renormalise (NEUTRE 0,55). La section 1.4 ci-dessous (fiabilité du z selon la fenêtre) reste valable — la note l'applique désormais **mécaniquement** via la garde 5 ans.

**Approche neutre — aucune prétention d'alpha.** Méthodes publiques appliquées avec discipline ; mise à l'épreuve par l'observation du portefeuille IA en réel, pas par backtest. Le scoring est un **outil de discipline et d'attention sélective** (filtrage chase de rally, identification Setup B, structuration des décisions), pas un générateur d'alpha.

### Risque = perte permanente de capital, pas volatilité (Marks / Buffett)

Le risque qui compte n'est **pas** la volatilité (déviation académique). C'est la **perte permanente et irréversible** de capital. Distinguer :
- **Baisse temporaire traversable** : le cours chute mais la thèse fondamentale reste intacte → pas une perte tant qu'on ne vend pas. Traversable.
- **Perte définitive** : soit on **vend au creux par panique** (perte réalisée d'un drawdown qui se serait résorbé), soit la **détérioration fondamentale** est réelle (la valeur intrinsèque a baissé, pas juste le cours).

**Inverse de la relation académique** : plus la marge de sécurité (décote vs valeur intrinsèque) est grande, plus le risque baisse **ET** le rendement potentiel monte — les deux dans le même sens, contrairement au dogme « plus de rendement = plus de risque ». Parabole du billet : un actif valant 1$ acheté à 40¢ est **moins** risqué *et* offre **plus** d'upside que le même acheté à 60¢ (la décote plus profonde absorbe davantage l'erreur). Buffett, Washington Post : ~80 M$ de capitalisation pour ~400 M$ d'actifs sous-jacents → la décote massive *était* la protection.

**Caveat décisif** : une décote n'est une *vraie* marge de sécurité que si la **valeur intrinsèque est solidement estimée**. Si l'estimation est creuse (fenêtre régression courte, business en mutation, value trap), la « décote » est illusoire et le risque de perte permanente est intact. La marge de sécurité protège contre l'erreur d'estimation seulement quand l'ancre est fiable (cf. section 1.4 fenêtre courte + value trap dans `opportunities.md`).

## Pilier 1 — Timing technique (22 pts — garde-fou, pas moteur, v3)

Le timing n'apporte que peu de points en positif (22 max) ; son vrai rôle est de
**borner le downside** via les pénalités (CHASE §1.6, death cross) et le bonus décote (§1.7).

### 1.1 Croisement MM21 / MM200 (10 pts v3)

La mécanique interne `cross_score` note le cross sur /20 (fraîcheur + volume + RSI bonus),
puis le score v3 la ramène à **/10** (`round(cross_score / 2)`).

**Golden Cross** (MM21 passe au-dessus de MM200) → signal haussier.
**Death Cross** (MM21 passe en-dessous de MM200) → signal baissier.

Pondération par fraîcheur du signal :
- Cross 0-30 jours : signal frais, prime maximale
- Cross 30-90 jours : encore valide, prime modérée
- Cross 90-180 jours : trend mature, prime faible
- Cross >180 jours : signal stale, négligeable

**Source** : Murphy *Technical Analysis of the Financial Markets* (2e éd., 1999) — référence standard. Win rate historique du Golden Cross ~72% à 6 mois quand pris dans les 30 premiers jours.

**Lecture dynamique obligatoire** : un cross n'est pas un état figé. Le screener calcule automatiquement un champ `signal_dynamics_warning` dans le breakdown quand le signal est en transition (death cross avec pente MM21 redevenue positive et spread tendu, ou golden cross s'affaiblissant). **Toujours lire ce champ avant de pondérer le cross dans le verdict.** Quand il est non-vide, traiter le signal comme ambigu — pas exploitable seul.

### 1.2 RSI (2 pts — v3, réduit 10 → 5 → 2)

Mesure de momentum 0-100 sur 14 périodes :
- Zone idéale 40-60 → 2 pts (momentum sain, ni surachat ni survente)
- Zone élargie 35-65 → 1 pt
- Zone surachat (>70) ou survente (<30) → 0 pt (signal extrême, mean-reversion probable)

**Pourquoi si peu** : le RSI mesure surtout l'*extension* (titre épuisé ou non), déjà couverte par la régression (1.4) — et en v3 le timing entier n'est qu'un garde-fou. L'historique : 10 pts (v1) → 5 (v2.1, triple-comptage) → 2 (v3).

Combiné au Cross : Golden Cross + RSI 50 = setup propre. Golden Cross + RSI 75 = signal mature, hausse probablement priced in.

### 1.2bis Pente MM21 (4 pts — v3, force de tendance)

Variation de la MM21 sur 5 séances (`slope_mm21_pct`, qui ne servait avant que dans les warnings). Mesure la **vélocité / qualité de la tendance courte**, là où le cross ne donne que sa *direction* :
- pente ≥ +0,8 % → 4 pts (accélération franche)
- pente ≥ +0,3 % → 2 pts (hausse nette)
- pente ≥ 0 % → 1 pt (légèrement positive / s'aplatit)
- pente < 0 % → 0 pt (MM21 qui dévisse)

Récompense un trend qui *accélère*, pas seulement « au-dessus de la MM200 ».

### 1.3 Volume (3 pts — v3)

`vol_recent (20 derniers jours) > vol_annual (2 ans glissants)` → 3 pts, sinon 0.

Logique Murphy : un mouvement sans volume est suspect. Volume confirme la conviction collective.

### 1.4 Régression long terme z-score (3 pts — v3)

Position du cours actuel vs sa droite de tendance log-linéaire long terme, exprimée en écarts-types :
- z entre -0.5σ et +1.5σ → zone saine, 3 pts
- z < -1σ → titre en décote vs sa propre tendance (potentielle opportunité mean-reversion)
- z > +2σ → titre tendu, retracement statistiquement probable

**Référence empirique** : Jegadeesh & Titman (1993) montrent que le momentum 3-12 mois fonctionne, mais Asness (AQR) note que l'effet s'inverse aux extrêmes par mean-reversion.

**⚠ Fiabilité conditionnelle à la fenêtre de régression**. La régression log-linéaire suppose qu'une trend long terme stable existe et que la fenêtre disponible la capture. Le screener applique 10y (tech) ou 20y (autres), mais retombe sur l'historique disponible quand il est plus court (champ `regression_window_years` dans le breakdown).

**Calibration de confiance** :
- **Fenêtre ≥15 ans** : z-score fiable, applicable tel quel
- **Fenêtre 7-14 ans** : z-score utile mais à pondérer (cycles régionaux ou sectoriels peuvent biaiser)
- **Fenêtre <7 ans** : z-score **peu fiable** — ne PAS appliquer comme critère setup B "z<-2σ"

Cas typiques de fenêtre <7 ans :
- Spin-offs récents (Kenvue 2023, GE Vernova 2024, **Constellation Energy 2022 — exemple session 2026-05-13** où z=-3σ sur 4y était mathématiquement creux : pente extrapolée +50.9%/an capturait quasi-exclusivement la phase de boom AI 2022-2024)
- IPOs <10 ans
- Restructurations majeures (post-mergers, scissions) qui modifient le périmètre

Sur ces cas, retomber sur les autres signaux (cross, RSI, fonda, consensus) et flagger explicitement *"z-score à pondérer — fenêtre régression courte"* dans la décision.

**⚠️ Calibration symétrique pour cycliques matures — la fenêtre par défaut 10y peut être TROP COURTE** :

Pour les titres cycliques matures (auto, semi, banques, materials, énergie, shipping, REITs cycliques), les cycles sectoriels durent typiquement 7-10 ans. Une fenêtre 10y capture **un seul cycle ou moins**, ce qui biaise la régression vers la phase observée (généralement la chute si on est en fin de cycle).

**Règle** : pour les cycliques matures avec historique listing >15 ans, utiliser la fenêtre **20-25 ans minimum** (ou max disponible) pour le z-score.

**Exemple Valeo (session 2026-05-21)** :
| Fenêtre | Pente trend | Z-score | Interprétation |
|---|---|---|---|
| 5y | -16.9%/an | +2.08σ | "Surchauffe" (capture uniquement la chute 2021-2025) |
| 10y | -15.7%/an | +1.67σ | "Surchauffe" (capture peak 2018 + chute) |
| 15y | -2.2%/an | -0.51σ | Quasi neutre |
| 20y | +6.2%/an | -1.12σ | Décote modérée |
| 25y | +6.6%/an | -1.27σ | Décote modérée |

→ Le z-score s'**inverse complètement** entre 10y et 25y. Sur fenêtre longue qui capture les cycles 2007-2009 (crise) et 2009-2018 (boom), Valeo apparaît **décoté de -1.23σ** vs sa tendance LT positive (+6.2%/an) au lieu de "surchauffe".

**Discipline d'application** :
1. Pour tout cyclique mature → **calculer z-score sur 20-25y** (ou max listing), pas 10y
2. Quand divergence majeure (>1σ) entre fenêtres → **flagger explicitement** et utiliser la fenêtre longue
3. Comparer plusieurs fenêtres systématiquement pour valider la robustesse du signal
4. Sectoriels concernés : Auto (Valeo, Forvia, Stellantis), **Semi EQUIPMENT uniquement** (LRCX, AMAT, KLAC, ASML sur cycles capex 7y), Banks EU/US, Materials (Arkema, Croda), Energy, Shipping

**Cas contrasté** :
- Compounders tech matures (MSFT, GOOGL, V, MA, etc.) : 10y suffit car trend LT généralement stable
- Quality compounders matures multi-cycles (KO, JNJ, PG) : 15-20y idéal
- **Cycliques matures : 20-25y obligatoire**

**⚠️ Granularité semi designers vs equipment (v2.0.2)** : yfinance utilise "Semiconductors" pour TOUS les designers (NVDA, AMD, AVGO, MU, INTC, TSM, ADI, TXN, QCOM) sans distinguer :
- **Memory chips** (Micron, SK Hynix) : ultra-cyclique 7 ans
- **AI accelerators** (NVDA) : secular winner — pas cyclique au sens classique
- **Analog industrial** (ADI, TXN) : modérément cyclique
- **Foundries** (TSM) : capex cyclique

Le screener Signal v2.0.2 ne traite comme cycliques 25y QUE l'industrie `"Semiconductor Equipment & Materials"` (AMAT, LRCX, KLAC, ASML). Les designers retombent en `tech_10y` standard. NVDA et autres secular winners ne sont plus artificiellement pénalisés. Les bulles memory au pic (MU, SK Hynix à z>+5σ) restent attrapées par la **pénalité CHASE** (section 1.6) qui ne dépend pas de la fenêtre.

**Implémentation production** : voir `_CYCLICAL_INDUSTRIES` dans `screener.py`. Le breakdown JSON expose le champ `regression_window_reason` (`cyclical_25y` / `tech_10y` / `standard_20y`) pour transparence.

### 1.5 Valorisation actuelle / timing d'entrée (val_pts — INFORMATIF, hors score depuis v3)

⚠️ **v3 : val_pts ne compte plus dans le score.** Il reste calculé et publié (breakdown
`val_pts` + `val_pts_mode`, affichage « val=X/5 ») comme **annotation de timing d'entrée**
— l'extension est couverte par la régression (1.4), la décote profonde par le bonus (1.7).

Drawdown du cours actuel vs plus haut 52 semaines (barème de l'annotation) :
- 0% à -3% (proche du top) → 0 pt — chase de rally, mauvais timing
- -3% à -10% (pullback sain) → 5 pts — zone d'entrée idéale
- -10% à -20% (correction modérée) → 3 pts — entrée agressive possible si trend intacte
- -20% à -30% (momentum cassé) → 1 pt
- < -30% (chute libre) → 0 pt — la trend est probablement perdue

C'est un proxy systématique du **range d'entrée** détaillé dans `opportunities.md` (entre MM21 et Fibo 38.2%). Pénalise les achats au plus haut, récompense les achats sur pullback sain.

**Logique** : un Golden Cross frais a beau être un bon signal, l'acheter quand le cours est collé à son plus haut 52w est statistiquement défavorable (mean-reversion à court terme). Un Golden Cross frais avec un pullback de -7% est le sweet spot.

### 1.6 Pénalité CHASE de rally (v2.0.2)

**Bug historique** : le z-score binaire des sections 1.4 donnait 0 pt hors zone saine, mais ne **pénalisait pas activement** les surextensions extrêmes. Conséquence : des titres en bulle technique (Micron z=+5σ, Alphabet z=+2,9σ post-rally +124%, Goldman Sachs z=+2,6σ) pouvaient obtenir 3 étoiles si leurs fondamentaux étaient bons et les analystes optimistes. Le screener disait implicitement "achetable" sur des chases de rally évidentes.

**Mécanique du fix** (additionnel au scoring 100 pts, appliqué avant le floor à 0) :

```
chase_pen = 0   # v2.2.1 : magnitudes renforcées (palier léger ±2 retiré)
z > 2,5σ                                  → chase_pen = -6 (chase extrême)
z > 2,0σ ET (RSI > 70 OU drawdown > -3%)  → chase_pen = -4 (chase confirmé)
```

**Logique** :
- z > 2,5σ seul suffit (surextension statistique massive, indépendamment du contexte court terme)
- z > 2,0σ + confirmation court terme (RSI surachat OU cours collé au top) = chase confirmé
- Sinon : 0 pt — le danger est aux EXTRÊMES ; pénaliser +1,5σ écarterait les compounders sains (qui vivent le plus souvent au-dessus de leur tendance)

**Effet attendu** (validé sur 124 tickers session 2026-05-27) :
- 10-15 tickers déclenchent une pénalité (5-10% de l'univers)
- CHASE extrême détecté : MU, INTC, CSCO, CAT, GOOGL, GS, WMT, LRCX, KLAC, ADI, MUFG, TSM, SAN.MC, BNP.PA, AMAT
- CHASE modéré : SIE.DE, TXN, etc.

**Magnitudes renforcées (v2.2.1)** : pénalités doublées (−3/−2 → −6/−4) — choix utilisateur « **le timing prime sur la qualité** », mais SEULEMENT aux extrêmes. Le palier léger ±2 à 1,5σ, d'abord ajouté, a été **retiré** : un compounder vit le plus souvent au-dessus de sa tendance, le pénaliser pour ça écarterait les meilleurs (le risque Nifty-Fifty est à 80×, pas à +1,5σ). Ex. GOOGL z=+2,8σ → −6 (73→67), GS z=+2,7σ → −6. Caveat : aucun backtest ne valide ces niveaux — choix éditorial « timing-first », pas un optimum prouvé.

**Lecture en pratique** :
- Le breakdown JSON expose `chase_pen` (-6, -4, ou 0) — toujours vérifier ce champ avant de pondérer le score
- Un score 65+ avec `chase_pen ≤ -4` signale : "business OK mais entrée actuelle dangereuse — attendre pullback"
- Combiné au champ `regression_window_reason`, permet de différencier chase légitime (cyclical 25y) vs chase tech (10y)

**Limites** : la pénalité ne couvre que les surextensions z-score. Un titre en **tendance très pentue** peut être à RSI 80+ au plus haut absolu avec un z encore modéré (cas FSLR 2026-06 : RSI 83, z +0,9σ → aucune pénalité) — le garde-fou est alors **aveugle** et c'est au jugement analyste de lire `rsi` + `drawdown_52w_pct` + l'annotation `val_pts` (1.5, informationnelle).

### 1.7 Bonus « décote-qualité » (v2.1 — miroir symétrique du CHASE)

**Asymétrie corrigée** : la pénalité CHASE (1.6) punit la surextension (z > 2σ), mais la **décote** (z < −2σ) ne touchait aucun point — le z-score binaire (1.4) notait un compounder de qualité 2σ *sous* sa tendance comme une bulle 2σ *au-dessus* (0 pt dans les deux cas). Or une décote sur un titre de qualité qui **ne tombe plus** est précisément le **Setup B** (mean-reversion, `opportunities.md`). D'où le bonus symétrique.

**Mécanique** (additionnel au score 100 pts, plafond 100, appliqué avant le floor à 0) :

```
value_bonus = 0   # v2.2.1 : magnitudes renforcées (palier léger ±2 retiré)
SI qualité ≥ 30/45 (échelle v3)  ET  pas un couteau qui tombe :
    z ≤ -2,5σ  → value_bonus = +6  (décote forte)
    z ≤ -2,0σ  → value_bonus = +4  (décote modérée)
```

**Garde-fous « pas un couteau qui tombe »** (cf. `selling.md`, pré-flight) — le bonus ne se déclenche QUE si les trois conditions tiennent :
- **qualité solide** : bucket qualité ≥ 30/45 (échelle v3 ; le bucket est désormais pur-qualité, sans PEG) — sinon = simple value trap, pas un Setup B ;
- **pas de death cross frais** (≤ 60j) : décote en plein cassage de tendance = on attend la confirmation, on ne rattrape pas ;
- **MM21 qui ne dévisse pas** : pente 5j > −2 % (la moyenne courte s'aplatit/se redresse = début de résorption).

**Logique** : contrepartie disciplinée du CHASE. CHASE dit « trop cher, attends un pullback » ; le bonus dit « décoté ET de qualité ET en stabilisation = Setup B à surveiller ». Il ne récompense **jamais** une décote seule — un titre cheap qui chute encore reste à 0.

**Lecture en pratique** :
- Le breakdown JSON expose `value_bonus` (+6, +4, ou 0) — un `value_bonus > 0` = candidat mean-reversion sur qualité, à mettre sur le radar.
- Exemple (2026-06, échelle v3) : **MSFT** z=−2,06σ, qualité 42/45, death cross vieux + pente MM21 qui s'aplatit → **+4** ; idem **V** (Visa) z=−2,03σ → +4, **ADBE** z=−2,43σ → +4, **CRM** z=−2,25σ → +4. NVDA (z sain) intact ; GOOGL/GS (z > 2,5σ) → CHASE **−6**.
- **Pas un signal d'achat** : le bonus remonte un titre sur le radar (Setup B), il ne dit pas « achète ». La confirmation du retournement reste à valider (`selling.md` : death cross frais → attendre).

## Pilier 2 — Qualité du business (45 pts, v3)

La durabilité — *ce que tu possèdes*. Le signal le plus persistant (Mauboussin : qualité r≈0,9, croissance r≈0).

- **Marge nette** (8 pts) : >15% → 8 | >8% → 5 | >0 → 2
- **Marge de Free Cash Flow** (8 pts) : >15% → 8 | >8% → 5 | >0 → 2

  > **FCF > BPA (Bezos)** : quand FCF/action et BPA **divergent**, privilégier le FCF/action. Le BPA est flattable par la comptabilité (provisions, amortissements) et les buybacks (mécanique au dénominateur) ; le FCF mesure le cash réellement disponible. Un cours est la **prévision actualisée des flux futurs**, pas un multiple du bénéfice passé.
- **ROE** (12 pts) : ≥25% → 12 | ≥15% → 9 | ≥8% → 5 | >0 → 2 — proxy de douve / qualité du capital employé
- **Croissance du CA, plafonnée** (10 pts) : >10% → 10 | >5% → 6 | >2% → 3 — plafonnée car la croissance ne persiste pas (base rates Mauboussin) ; on ne sur-récompense pas l'hyper-croissance
- **Dette / bilan** (7 pts) : D/E < 50 → 7 | < 100 → 4 (yfinance scale ×100 ; net-cash D/E=0 inclus depuis v2.0.2 ; `None` = donnée manquante → 0)

> **Cap** : `min(45, …)` — la somme brute (8+8+12+10+7 = 45) ne peut pas dépasser le bucket.

## Pilier 2bis — Valorisation (30 pts, v3)

La marge de sécurité — *le prix payé*. Vrai pilier depuis v3 (avant : noyé dans les fondamentaux).

- **PEG ratio** (15 pts) : 0<PEG<1 → 15 | <2 → 10 | <3 → 5 — valo relative à la croissance, ne pénalise pas un multiple élevé justifié
- **FCF yield** (15 pts) : ≥8% → 15 | ≥5% → 11 | ≥3% → 7 | ≥1,5% → 3 — cher/pas cher, robuste et comparable entre secteurs

**PER absolu volontairement EXCLU** : il pénaliserait mécaniquement la qualité, qui se paie toujours plus cher (« ce qui est intelligent à un certain prix devient stupide à un autre »).

> **Caveat sectoriel** : les métriques FCF collent mal à la compta bancaire/assurance (GS, banques → valo sous-estimée) et aux foncières. À lire avec ce biais en tête.

Sources de données : Yahoo Finance + Finnhub (cross-validation). Quand divergence importante, baisse de la confiance globale.

## Métriques de qualité business — lecture qualitative (hors scoring)

Le scoring 100pts ci-dessus est calibré et testé. Pour **enrichir la lecture qualitative** (sans modifier le scoring), deux métriques supplémentaires sont à consulter systématiquement lors des analyses ponctuelles via le skill :

### ROCE — Return on Capital Employed

**Formule** : `EBIT / (Total Assets − Current Liabilities)`

**Question répondue** : *"Pour chaque euro de capital employé dans le business, combien de profit opérationnel est généré ?"*

**Référence** : Buffett, Munger, Greenblatt (Magic Formula : EBIT/EV + ROCE backtestée 1988-2009 surperforme S&P). C'est **la métrique principale de qualité business** dans le value investing classique.

**Seuils universels** :
| ROCE | Lecture |
|---|---|
| **>30%** | Qualité exceptionnelle (NVDA 81%, AAPL 69%) — moat fort, scaling efficient |
| **15-30%** | Solide (MSFT 26%, Reply 21%) |
| **8-15%** | Moyen (Dassault 14%) — business normal |
| **<5%** | Faible OU cyclique en bas de cycle (Arkema 2%, Croda 4%) |

**Ratio Current/Mean pour distinguer cyclique vs structurel** :
Quand ROCE actuel <10%, comparer au max historique disponible (4-5y via yfinance) :
- **Max historique >15%** + current ratio <0.5× → **cyclique bas probable** (recovery play)
- **Max historique <10%** + current stable → **dégradation structurelle** (value trap risk)

Exemples session 2026-05 :
- Arkema : current 2%, max 11.4% → cycle bas (recovery candidate)
- Croda : current 4%, max 25.8% → cycle bas (recovery candidate)
- EssilorLuxottica : current 6.6%, range étroit 6.1-6.6% → structurel faible (PAS recovery)

**Caveat** : avec 4-5y d'historique seulement, on peut louper le vrai max du cycle. Ratio = indicateur directionnel, pas seuil mécanique.

### Trajectoire de la douve (champ qualitatif)

Une douve n'est jamais statique : Buffett rappelle qu'elle est « presque toujours en train de s'élargir ou de se rétrécir ». Au-delà de *nommer* le type de douve (cf. les 5 types du `GUIDE_redaction_analyses.md`), classer sa **direction** :

| Trajectoire | Lecture (signaux) |
|---|---|
| **S'élargit** | ROIC/ROCE en hausse tendancielle, part de marché qui gagne, pricing power croissant |
| **Stable** | ROCE plat à haut niveau, parts stables (±2%/5 ans), pas de disruption visible |
| **S'érode** | ROCE qui décline, parts instables/perdues, signaux d'overshoot ou de disruption (nouvel entrant, substitut technologique) |

**Alignement avec le ratio ROCE Current/Mean** : une douve qui *s'élargit* se voit dans un ratio Current/Mean >1 soutenu (pas juste un rebond cyclique) ; une douve qui *s'érode* donne un ROCE en baisse séculaire (à distinguer du cycle bas — cf. ci-dessus). À reporter dans le champ `biz` de l'analyse comme qualificatif de durabilité, pas comme score.

### Cas spécial — Management turnaround bet (pattern hybride)

Le ratio Current/Mean ROCE classe en "structurel faible" tout titre avec ROCE bas stable. **Mais ce cadre regarde le passé** — il rate une catégorie importante : les titres qui sont structurellement faibles **selon leur historique récent** mais où le management a annoncé **un plan de transformation explicite et chiffré** qui n'est pas encore reflété dans les chiffres historiques.

**Identifier le pattern** :
- ROCE actuel bas (5-10%) + stable sur 3-4 ans (ratio Current/Mean ≈ 1)
- ET plan de transformation **chiffré, daté, communiqué officiellement** par le management
- ET résultats trimestriels récents confirment trajectoire conforme au plan

**Distinguer narratif basique vs plan crédible** :

| ❌ Narratif basique (ignorer) | ✅ Plan crédible (à intégrer dans la lecture) |
|---|---|
| "Le management va améliorer les marges" | "Marge opérationnelle de 5% → 6-7% à horizon 2028" |
| "On prend le virage EV" | "12 plateformes technologiques, €50M EBITDA additionnel/an" |
| "On va se diversifier" | "Partenariats signés (entreprise X pour datacenters, Y pour Chine) avec timelines" |
| "On est confiant dans l'avenir" | "FCF >500M€ en 2028, ratio dette/EBITDA <1.0x, investment grade visé" |

**Validation continue obligatoire** (couches 3-4) :
1. Lire le **plan stratégique officiel** (slide deck investor day, communiqué annuel, page IR)
2. Vérifier que les **2-3 derniers trimestriels** confirment exécution conforme au plan
3. Identifier les **milestones court terme** mesurables (margin trajectory, contrats annoncés)
4. Vérifier que le **consensus analystes n'a pas encore intégré** le succès du plan (target mean ≈ cours actuel = bon signe contrarian, marché pas encore convaincu)

**Base rate empirique** des plans 3 ans transformation industrie :
- ~30-35% atteignent la fourchette haute (Bosch pivot EV, Aptiv, Magna)
- ~35-40% atteignent la fourchette basse (objectifs partiellement atteints)
- ~25-30% sous-livrent significativement (Continental 2019-2023, certains banks 2010s)

**Calibration de conviction** :
- **Conviction faible par défaut** (probabilité succès <50%)
- **Asymétrie potentiellement favorable** mais haute variance
- Sizing très petit (1-3% du capital max)
- Monitoring trimestriel obligatoire

Exemple session 2026-05 : **Valeo plan Elevate 2028** (marge op 5% → 6-7%, FCF >500M€, investment grade) + Q1 2026 confirme exécution (+3pts surperformance vs marché, guidance maintenue). Sans intégrer Elevate, le cadre v1.10.6 aurait classé Valeo "SKIP / structurel faible" — avec intégration, c'est un management turnaround bet spéculatif léger défendable.

**Anti-pattern à éviter** :
Si le plan est uniquement narratif (pas de chiffres précis, pas de milestones datés) OU si les trimestriels récents **ne montrent pas** de progression → c'est un **value trap déguisé**, pas un turnaround. Skip.

### EV/EBITDA — Multiple d'entreprise

**Formule** : `Enterprise Value / EBITDA`
- EV = Market Cap + Total Debt − Cash
- EBITDA = Earnings Before Interest, Taxes, Depreciation, Amortization

**Question répondue** : *"Combien d'années d'EBITDA il faut pour rembourser l'achat complet de l'entreprise (incluant les dettes) ?"*

**Avantages vs PEG (déjà dans scoring)** :
- Cross-sectoral comparable (neutralise structure capital + fiscalité)
- Cross-country comparable (différents régimes fiscaux)
- Pas affecté par les choix d'amortissement comptables

**Seuils** :
| EV/EBITDA | Lecture |
|---|---|
| **<8** | Cheap absolu — industriels en bas de cycle, mid-caps value EU |
| **8-15** | Normal — zone d'équilibre |
| **15-25** | Tendu — premium qualité ou growth |
| **>25** | Extrême — pari croissance future (NVDA 43, Tesla, AAPL 27) |

**Source** : direct via `yfinance.info["enterpriseToEbitda"]`.

### Combinaison ROCE × EV/EBITDA — matrice qualité × valorisation

```
                  EV/EBITDA BAS (cheap)     EV/EBITDA HAUT (cher)
                  ────────────────────      ────────────────────
ROCE HAUT        🟢 IDÉAL                   🟡 QUALITÉ PREMIUM
(qualité)         "Bargain quality"          "Tu paies pour le top"

ROCE BAS         🟠 VALUE TRAP RISQUE        🔴 À ÉVITER
(qualité faible) "Cheap pour une raison"     "Cher ET pas bon"
```

Cas pédagogiques session 2026-05 :
- **Reply** : ROCE 21% + EV/EBITDA 7 → 🟢 Idéal (qualité + value combo rare)
- **NVDA** : ROCE 81% + EV/EBITDA 43 → 🟡 Premium pur
- **Arkema** : ROCE 2% + EV/EBITDA 7 → 🟠 mais cycle bas (recovery, pas trap)
- **Croda** : ROCE 4% + EV/EBITDA 19 → 🔴 prima facie, **mais cycle bas** (recovery possible si confirmé par max historique 25.8%)

### Quand utiliser ces métriques

À **lire systématiquement** dans la couche 2 (yfinance.info) pour toute analyse ponctuelle de titre :
1. Score screener donne le verdict initial
2. Lire ROCE absolu + EV/EBITDA absolu pour situer dans la matrice qualité×valorisation
3. Si ROCE actuel suspect (très bas), calculer ratio Current/Mean pour distinguer cycle vs structurel
4. Mentionner explicitement dans la synthèse comme **éléments de calibration de conviction** (pas comme score additionnel)

**Pas ajouté au scoring 100pts** car :
- Calibration scoring testée empiriquement, ne pas perturber
- Métriques utilisées comme outils de **lecture qualitative**, pas comme indicateurs mécaniques
- Cohérent avec discipline anti-overengineering (cf décision A/D Line dans repo Signal)

### Caveat persistance — une douve identifiée ≠ rendement garanti (Mauboussin)

La persistance d'un ROIC élevé est **rare et régresse vite**. Ordre de grandeur Mauboussin : ~½ de l'excès de rendement sur capital disparaît en ~5 ans (plus vite encore en *energy* / *materials*, plus cyclique) ; et environ **½ des résultats corporate s'expliquent par la chance** ou restent inexpliqués. Conséquence directe :
- Un ROCE élevé *aujourd'hui* n'est pas extrapolable mécaniquement — d'où l'utilité de la **trajectoire de la douve** (s'élargit/stable/s'érode) plutôt que du seul niveau.
- Une douve correctement *identifiée* ne **garantit pas** un rendement futur : la régression vers la moyenne joue contre les meilleurs comme contre les pires.

Cohérent avec l'**honnêteté empirique** du skill (posture neutre, pas de prétention d'alpha) : ces métriques calibrent la conviction, elles ne promettent pas la surperformance.

### Pointeurs — modules complémentaires

- **`capital_allocation.md`** : lecture de l'**allocation du capital** (buybacks vs M&A vs dette vs dividende vs réinvestissement) comme signal de **qualité du management** — complément naturel du turnaround bet et de la trajectoire de douve.
- **`ai_durability_lens.md`** : grille de durabilité spécifique aux titres **IA-exposés** (où la douve peut se déplacer vite — cf. caveat persistance accéléré en secteurs à changement rapide).

---

## Pilier 3 — Consensus analystes (3 pts, v3)

Recommandation moyenne sur échelle 1-5 :
- < 2.0 (strong buy) → 3 pts
- < 2.5 (buy) → 2 pts
- < 3.0 (hold) → 1 pt
- ≥ 3.0 → 0 pt

**Pondération volontairement minime** car signal lagging (les analystes réagissent souvent aux mouvements de prix, plus qu'ils ne les précèdent) avec biais haussier structurel (~80% des recommandations sont buy/hold). Trajectoire : 10 pts → 5 (v2) → 3 (v3) — simple cross-check, pas un pilier.

## Le facteur lens : croiser momentum / value / quality

Une fois le score calculé, regarder le profil du titre :

- **Momentum** = fraîcheur du Golden Cross + RSI sain + volume confirmé
- **Value** = z-score régression négatif + PEG raisonnable
- **Quality** = marges + croissance + endettement

**Le best setup** = momentum frais + value attractif + quality solide. Rare. Quand il se présente, conviction forte.

**Setup mixte** : momentum mature + value en place → opportunité moyenne, conviction modérée.
**Setup faible** : momentum fort + value tendu → chase de rally, conviction faible voire skip.

## Position sizing

### Principe : Kelly fractionnaire

Formule Kelly théorique : `f* = (bp - q) / b` où b = ratio gain/perte, p = proba succès, q = 1-p.

**Problème pratique** : on ne connaît jamais p exactement. Surestimer p mène à overbetting et drawdowns sévères.

**Demi-Kelly comme standard** : ~75% du growth rate de Kelly complet pour ~50% du drawdown maximal. Compromis empiriquement validé pour le retail.

### Sizing par conviction (heuristique simple)

**⚠️ TABLE DE RÉFÉRENCE UNIQUE pour tout le skill.** `frameworks.md` §6 (définition des niveaux de conviction) renvoie ici pour les bandes chiffrées — ne dupliquer ces chiffres nulle part ailleurs. Calibrée 2026-06 sur la pratique réelle des sessions (cap single-stock vécu ~4-6%) et les memories (Setup D 1-3%).

| Conviction | Cap par position |
|---|---|
| Forte | 5-8% du capital |
| Modérée | 3-5% |
| Faible | 1-2% |
| Setup D / pari spéculatif (turnaround, cyclical recovery) | 1-3% max (cf. memory `feedback_turnaround_bet`) |
| Moonshot (pre-profit, quantum, IPO récente) | ≤1% |
| Pas d'avis | 0% (skip) |

**Cap absolu** : 20% sur un seul titre (Règle Signal R02) — au-delà, le risque idiosyncratique domine la performance.

**Cluster thématique** : des positions corrélées sur une même thèse (ex : 2 titres agentic SaaS, 3 titres auto/EV) se **cumulent** — sizer le THÈME, pas chaque titre isolément. Un cluster corrélé baisse ensemble : appliquer le cap de conviction au cluster entier (leçon session 2026-06, NOW + CRM ≈ 7% sur un seul thème).

**Diversification minimale** : 12-15 positions pour réduire le risque spécifique sans diluer l'edge.

### Liquidités

Recommandation (pas une règle mécanique — le plancher bloquant a été retiré en juillet 2026) : garder ~5% en liquidités même en bull market. Donne :
- Optionalité (capacité à acheter sur correction)
- Coussin psychologique (réduit pulsions de vente forcée)

Descendre en dessous — jusqu'à 100% investi — est un choix légitime si l'opportunité le justifie, mais il se motive explicitement : à cash nul, toute nouvelle entrée exige une vente ou une rotation.

## Intégration Signal (si applicable)

Si l'utilisateur travaille dans le repo Signal, tu peux importer directement :

```python
from screener import score_ticker, detect_cross, cross_score, calcul_regression
```

`score_ticker(ticker)` retourne un dict avec score 0-100 + breakdown détaillé. Utiliser cette fonction pour avoir un scoring strictement consistant avec ce qui pilote le portfolio Signal.

Si pas dans le repo Signal, tu appliques la même logique manuellement via yfinance + les formules ci-dessus.

## Synthèse de l'analyse

Après scoring + factor lens + sizing, formule canonique d'output :

```
Score: 78/100 (qualité 38/45, valorisation 22/30, timing 14/22, analystes 2/3 ± ajustements)
Ajustements: chase_pen / value_bonus / death_pen — TOUJOURS les citer s'ils sont non-nuls
Profile: qualité solide + valo correcte + timing en garde-fou
Verdict: ACHAT — conviction modérée
Sizing: 5% du capital max
Risque principal: [le risque concret le plus pertinent]
Pre-mortem: [scénario d'échec plausible]
```

Pas de fluff. Pas de "Disclaimer: this is not financial advice" à chaque réponse. Le verdict, les chiffres, les caveats techniques, fini.
