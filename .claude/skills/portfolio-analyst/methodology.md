# Méthodologie d'évaluation d'un titre

Approche en 3 piliers, validée empiriquement sur des décennies de recherche académique.

## Scoring synthétique : 100 points

```
Momentum technique  →  45 pts  (cross 20 + RSI 10 + vol 5 + reg 5 + valorisation 5)
Fondamentaux        →  50 pts
Analystes           →  5 pts
                       ─────
                       100 pts
```

Pondération calibrée par l'expérience (le projet Signal applique cette logique en production sur 90 tickers, backtest 2019-2024 : +13.5pp/an d'alpha vs SPY sur les 40 pts de momentum seuls — version actuelle ajoute 5 pts de timing d'entrée).

## Pilier 1 — Momentum technique (45 pts)

### 1.1 Croisement MM21 / MM200 (20 pts)

**Golden Cross** (MM21 passe au-dessus de MM200) → signal haussier.
**Death Cross** (MM21 passe en-dessous de MM200) → signal baissier.

Pondération par fraîcheur du signal :
- Cross 0-30 jours : signal frais, prime maximale
- Cross 30-90 jours : encore valide, prime modérée
- Cross 90-180 jours : trend mature, prime faible
- Cross >180 jours : signal stale, négligeable

**Source** : Murphy *Technical Analysis of the Financial Markets* (2e éd., 1999) — référence standard. Win rate historique du Golden Cross ~72% à 6 mois quand pris dans les 30 premiers jours.

**Lecture dynamique obligatoire** : un cross n'est pas un état figé. Le screener calcule automatiquement un champ `signal_dynamics_warning` dans le breakdown quand le signal est en transition (death cross avec pente MM21 redevenue positive et spread tendu, ou golden cross s'affaiblissant). **Toujours lire ce champ avant de pondérer le cross dans le verdict.** Quand il est non-vide, traiter le signal comme ambigu — pas exploitable seul.

### 1.2 RSI (10 pts)

Mesure de momentum 0-100 sur 14 périodes :
- Zone idéale 40-60 → 10 pts (momentum sain, ni surachat ni survente)
- Zone élargie 35-65 → 5 pts
- Zone surachat (>70) ou survente (<30) → 0 pt (signal extrême, mean-reversion probable)

Combiné au Cross : Golden Cross + RSI 50 = setup propre. Golden Cross + RSI 75 = signal mature, hausse probablement priced in.

### 1.3 Volume (5 pts)

`vol_recent (20 derniers jours) > vol_annual (2 ans glissants)` → 5 pts, sinon 0.

Logique Murphy : un mouvement sans volume est suspect. Volume confirme la conviction collective.

### 1.4 Régression long terme z-score (5 pts)

Position du cours actuel vs sa droite de tendance log-linéaire long terme, exprimée en écarts-types :
- z entre -0.5σ et +1.5σ → zone saine, 5 pts
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
4. Sectoriels concernés : Auto (Valeo, Forvia, Stellantis), Semi (LRCX, AMAT, KLAC sur cycles 7y), Banks EU/US, Materials (Arkema, Croda), Energy, Shipping, REITs cycliques

**Cas contrasté** :
- Compounders tech matures (MSFT, GOOGL, V, MA, etc.) : 10y suffit car trend LT généralement stable
- Quality compounders matures multi-cycles (KO, JNJ, PG) : 15-20y idéal
- **Cycliques matures : 20-25y obligatoire**

### 1.5 Valorisation actuelle / timing d'entrée (5 pts) — barème CONDITIONNÉ au régime cross

Le barème val_pts dépend de la présence ou non d'un **Golden Cross frais** (≤30j depuis le cross). Calibration depuis test empirique du 23/05/2026 sur 43 145 events GC frais 2017-2024 (32 tickers).

**Cas 1 — Avec Golden Cross frais (≤30j)** : barème INVERSÉ. La chute profonde + GC frais représente une "réinitialisation propre" (Setup A renforcé, cf opportunities.md) avec perf forward 12m MONOTONE CROISSANTE :

| Drawdown vs 52w high | val_pts | Perf 12m médiane mesurée |
|---|---|---|
| 0 à -3% (top, chase) | 0 | +16.8% |
| -3 à -10% (pullback) | 2 | +19.9% |
| -10 à -20% (correction) | 3 | +24.3% |
| -20 à -30% (drawdown modéré) | 4 | +44.3% |
| < -30% (chute profonde) | **5** | **+86.1%** ← premium |

**Cas 2 — Sans Golden Cross frais** : barème original (chute = risque de continuation).

| Drawdown vs 52w high | val_pts | Lecture |
|---|---|---|
| 0 à -3% (top, chase) | 0 | mauvais timing, mean-reversion court terme probable |
| -3 à -10% (pullback) | 5 | zone d'entrée idéale (sweet spot) |
| -10 à -20% (correction) | 3 | entrée agressive possible si trend intacte |
| -20 à -30% (momentum cassé) | 1 | risque élevé sans signal de reprise |
| < -30% (chute libre) | 0 | trend probablement perdue |

**Logique** :
- Sans GC frais → le drawdown profond signale un risque de continuation (value trap potentiel)
- Avec GC frais → le drawdown profond signale une réinitialisation que le marché a déjà commencé à corriger techniquement (rebond V-shape mesurable)

**Cas historiques validant le barème inversé** :
- META 2023 : DD -75% T4 2022, Golden Cross début 2023 → +200% 12m
- NVDA 2020 : DD -38% covid mars 2020, Golden Cross fin avril → +400% 24m
- ASML 2023 : DD -45% T4 2022, Golden Cross début 2023 → +120% 24m
- AMD 2023, NFLX 2023 : profils similaires, performances exceptionnelles

**Caveats à revalider Q3-Q4 2026** :
- Sample 2017-2024 biaisé vers les rebonds V-shape post-COVID / post-correction 2022
- 32 tickers large caps : survivorship bias (les delistings invisibles)
- Le pattern peut s'inverser en cycle séculaire bear (style Japon 1990s ou US 1966-1982)

**Champ exposé dans le breakdown** : `val_pts_mode` = `"gc_fresh_inverted"` (barème inversé appliqué) ou `"normal"` (barème original). Permet de distinguer ce qui motive le score.

C'est un proxy systématique du **range d'entrée** détaillé dans `opportunities.md` (entre MM21 et Fibo 38.2% en mode normal, et en mode "réinitialisation" pour le GC frais sur chute profonde).

## Pilier 2 — Fondamentaux (50 pts)

50 pts répartis sur :

- **Croissance du chiffre d'affaires** (15 pts) : >15%/an = max
- **Marges nettes** (10 pts) : >20% = max
- **PEG ratio** (15 pts) : <1 = excellent (15 pts), <2 = correct (10 pts)
- **Croissance EPS** (5 pts) : >10%/an = max
- **Endettement** (5 pts) : Debt/Equity < 0.5 = max

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

---

## Pilier 3 — Consensus analystes (5 pts)

Recommandation moyenne sur échelle 1-5 :
- < 2.0 (strong buy) → 5 pts
- < 2.5 (buy) → 3 pts
- < 3.0 (hold) → 1 pt
- ≥ 3.0 → 0 pt

**Pondération volontairement faible** car signal lagging (les analystes réagissent souvent aux mouvements de prix, plus qu'ils ne les précèdent) avec biais haussier structurel (~80% des recommandations sont buy/hold). Réduit de 10 à 5 pts pour libérer la place à la valorisation actuelle (timing d'entrée), plus actionnable et moins biaisée.

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

| Conviction | Cap par position |
|---|---|
| Forte | 7-10% du capital |
| Modérée | 4-6% |
| Faible | 2-3% |
| Pas d'avis | 0% (skip) |

**Cap absolu** : 20% sur un seul titre (Règle Signal R02) — au-delà, le risque idiosyncratique domine la performance.

**Diversification minimale** : 12-15 positions pour réduire le risque spécifique sans diluer l'edge.

### Liquidités

Maintenir au moins 5% en liquidités même en bull market. Donne :
- Optionalité (capacité à acheter sur correction)
- Coussin psychologique (réduit pulsions de vente forcée)

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
Score: 78/100 (momentum 35, fonda 39, analystes 4)
Profile: momentum frais + value modéré + quality solide
Verdict: ACHAT — conviction modérée
Sizing: 5% du capital max
Risque principal: [le risque concret le plus pertinent]
Pre-mortem: [scénario d'échec plausible]
```

Pas de fluff. Pas de "Disclaimer: this is not financial advice" à chaque réponse. Le verdict, les chiffres, les caveats techniques, fini.

## Backtest par régime (Signal — Phase 3)

Depuis Phase 3, le backtest historique (`backtest.py`) reproduit fidèlement les conditions live :
- Coûts de transaction (15 bps round-trip)
- PFU 30% sur plus-values réalisées (modélisé en USD pour simplicité)
- VIX dampener point-in-time (multiplier appliqué au moment de chaque rebalancement)
- VAL_pts aligné avec le live (drawdown vs 52w high)

### Outils

- **`backtest.py --variant=baseline`** : référence sans coûts ni VIX (mesure pure technique)
- **`backtest.py --variant=costs_only`** : ajoute frais + PFU (mesure l'impact friction)
- **`backtest.py --variant=costs_vix`** : ajoute VIX dampener (défaut, mesure défensivité régime)
- **`backtest_compare.py`** : lance les 3 séquentiellement + table comparative + verdict go/no-go

### Métriques par régime

Le backtest décompose les résultats sur 5 régimes (déclarés ex-ante dans `config.REGIME_DEFINITIONS`) :
- `bull_2019` (2019-01 → 2020-02) : bull market pré-COVID
- `covid_crash` (2020-02-19 → 2020-04-30) : choc COVID -34% S&P puis V-shape
- `bull_post_covid` (2020-05 → 2021-12) : bull post-COVID +50% S&P
- `bear_2022` (2022-01 → 2022-10-13) : bear 2022 taux + tech -25%
- `recovery_2023_24` (2022-10-14 → 2024-12) : récupération + IA rally

L'edge doit tenir en bear/stress, pas seulement en bull. Si Signal a un alpha massif en bull et nul en bear, c'est du momentum factor tilt déguisé en alpha (cf FINSABER §5).

### Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014)

Le Sharpe brut est sur-estimé quand on teste plusieurs configurations (5 signaux momentum + pondérations + seuils RSI/régression/val_pts = ~10 trials implicites). Le Deflated Sharpe corrige : `DSR ≈ SR / √(1 + 0.5×N_trials/N_weeks)`.

**Critère santé** : Deflated Sharpe > 0.3 pour considérer que l'edge est statistiquement défendable (pas du data mining).

### Critères go/no-go Phase 4

Avant d'investir dans l'élargissement de l'univers (Phase 4, 2000 tickers), vérifier que :
1. Alpha CAGR net > +1pp/an sur 2019-2024 cumulé
2. Sharpe net > 0.5
3. Drawdown bear 2022 > -20% (en absolu moins pire que SPY)
4. Deflated Sharpe > 0.3
5. VIX dampener améliore le Sharpe vs costs_only (sinon il n'apporte rien)

Si NO-GO, deux options : recalibrer les paramètres VIX (intercept/slope/plancher) ou réviser les pondérations 45/50/5.

## VIX : indicateur contextuel non scoré (Phase 2 mise en pause)

Le VIX (indice de volatilité implicite S&P 500, CBOE) est **fetché chaque semaine et affiché** dans le dashboard et le prompt Claude. Mais **il n'influence plus le scoring du screener** depuis Phase 3.

### Pourquoi le dampener mécanique a été désactivé

Le backtest comparatif 2019-2024 (`backtest_compare.py`) a testé l'effet du VIX dampener sur la performance :

| Variant | Sharpe net | Alpha équitable CAGR |
|---|---|---|
| costs_only (sans VIX) | 0.92 | +2.56pp |
| costs_vix (avec VIX dampener) | 0.87 | +1.71pp |

Sur cette période, le dampener **dégrade** légèrement le Sharpe et l'alpha. Raison probable : 2019-2024 a connu un seul vrai épisode de stress (COVID en V-shape), trop court pour que le dampener prouve sa valeur défensive. Pendant le rebond post-COVID, le dampener a bloqué des achats de qualité qui auraient été extrêmement rentables.

Honnêteté méthodologique : on ne maintient pas un mécanisme par croyance théorique alors que les données disent l'inverse. **Décision Phase 3 : désactiver le dampener** (`config.VIX_DAMPENER_ENABLED = False`).

### Ce qui reste actif

Le VIX continue d'être :
- **Fetché** chaque semaine via `^VIX` yfinance (avec fallback cache puis 18.0 médiane historique)
- **Persisté** dans `portfolio.json:last_known_vix` pour transparence
- **Affiché** sur le dashboard sous forme d'une pill colorée (calme/vigilance/stress/panique)
- **Communiqué à Claude** dans la section CONTEXTE DE MARCHÉ du prompt

Mais le multiplier est forcé à **1.0 pour tous les tickers** → aucun impact sur les scores.

### Usage par Claude

Le VIX devient un **indicateur de contexte qualitatif** que Claude peut citer dans `analyse_macro` quand pertinent :

> *"VIX à 22 cette semaine, vigilance modérée — j'ai privilégié les positions fondamentaux solides plutôt que de chasser le momentum frais."*

Ce n'est PAS une règle d'enforcement. Claude est libre de l'ignorer si non pertinent, ou de s'en servir pour justifier une prudence éditoriale. Les scores du screener restent inchangés.

### Réactivation future

Les paramètres `VIX_DAMPENER_INTERCEPT=1.5 / SLOPE=0.025 / MIN=0.20` restent déclarés dans `config.py`. Pour réactiver, flipper `VIX_DAMPENER_ENABLED = True`. À considérer après :
- Un backtest 2007-2024 incluant le GFC 2008 (vrai stress test)
- OU une recalibration moins agressive (intercept=1.7, slope=0.018, min=0.30)

### Champs exposés dans le breakdown

- `vix_value` : niveau VIX utilisé au moment du scoring (toujours rempli)
- `vix_multiplier` : facteur appliqué (toujours 1.0 tant que dampener désactivé)
- `momentum` : points momentum (= `momentum_raw` × 1.0 = `momentum_raw`)
- `momentum_raw` : points momentum bruts (identique à `momentum` tant que dampener off)

## R01 Concentration sectorielle — soft penalty graduée (depuis 23/05/2026)

R01 ne fonctionne plus en mode binaire blocage-ou-rien. C'est maintenant une pénalité progressive sur le sizing :

| Concentration cluster | Comportement |
|---|---|
| < 30% | Aucune restriction, sizing normal |
| 30-65% | **Soft cap** : sizing réduit par un facteur `clip(1 - (pct-30)/35, 0.1, 1.0)`. À 40% → ×0.71. À 50% → ×0.43. À 60% → ×0.14. |
| > 65% | **Blocage strict** — concentration excessive, achat refusé |

**Bypass conviction forte (régime soft uniquement)** : si `conviction="forte"`, le sizing factor a un plancher à 0.5. Cela permet l'achat exceptionnel d'un titre dans un cluster sursaturé sans annihiler le sizing.

**Exemple** : Cluster Tech & IA à 58.8% du portefeuille, achat candidat tech avec conviction modérée. Sans bypass, sizing = 0.18 × 5% = 0.9% du capital. Avec conviction forte + bypass, sizing = 0.5 × 7% = 3.5% du capital — taille raisonnable pour saisir une opportunité exceptionnelle.

**Implications éditoriales** : tu peux désormais proposer un achat dans un cluster saturé. Mais tu dois (a) le justifier sérieusement dans `raison`, (b) marquer `conviction: "forte"` pour bénéficier du sizing plancher 50%. Sinon le sizing automatique sera très petit (souvent <1% du capital) et l'achat peu pertinent. La règle reste de ne PAS forcer si la position de remplacement n'a pas un alpha attendu clairement supérieur aux positions tech déjà détenues.

**Champs exposés** dans `regles_actives` du portfolio.json :
- `regime` : "soft" ou "strict"
- `pct` : concentration mesurée du cluster
- `sizing_factor` : facteur appliqué (uniquement régime soft)
- `bloque` : true (strict) | false (soft, sizing réduit mais possible)

## Friction fiscale et coûts de transaction (Signal — compte-titres FR)

Depuis Phase 1 du plan d'amélioration, Signal modélise explicitement les coûts réels d'un investisseur retail français sur compte-titres ordinaire.

### Coûts de transaction
- **7.5 bps one-way** (broker + slippage estimé), soit **15 bps round-trip** = 0.15% par aller-retour
- Appliqués automatiquement à chaque ACHAT (déduit des liquidités, ajouté à la base fiscale) et chaque VENTE (réduit le cash récupéré)
- Référence : Frazzini, Israel, Moskowitz (2018) — "Trading Costs", AQR Working Paper

### Fiscalité française — PFU 30%
- **Prélèvement Forfaitaire Unique = 30%** (12.8% IR + 17.2% prélèvements sociaux), s'applique sur les **plus-values RÉALISÉES à la vente uniquement**
- Article 200 A du Code général des impôts
- **Pas d'impôt sur les plus-values latentes** (positions non vendues) → buy & hold long terme structurellement favorisé
- Pertes réalisées → **crédit d'impôt utilisable sur 10 ans** contre des futurs gains (article 150-0 D du CGI)

### Conséquences sur la discipline de décision

**Vente d'une position en gain — règle empirique** :
Une vente avec +X% de plus-value récupère 0.7 × X (après PFU 30%) + frais de vente. Pour qu'une rotation soit fiscalement justifiée :
- L'alpha attendu de la position de remplacement doit être supérieur à `0.30 × plus-value courante` ÷ taille position
- En pratique : ne pas vendre un +20% pour un titre dont l'edge espéré est < 8-10%

**Vente d'une position en perte — pas de pénalité fiscale** :
Le PFU s'applique uniquement aux gains. Une vente en perte génère 0€ d'impôt ET crée un crédit fiscal reportable. C'est l'inverse de la disposition effect classique : couper rapidement les pertes a un bénéfice fiscal réel.

**Plus-values latentes vs réalisées** :
NVDA +95% détenu depuis 140j = 0€ d'impôt tant qu'on ne vend pas. C'est cette propriété qui rend les positions gagnantes longtemps détenues si précieuses — chaque jour de hold supplémentaire est un crédit d'impôt différé qui peut grossir indéfiniment.

### Lecture du portfolio.json

Champs Phase 1 à connaître :
- `total_frais_payes` : cumulé depuis création
- `total_impots_payes` : cumulé PFU versé au fisc
- `total_pertes_reportables` : crédit fiscal théorique disponible (à multiplier par 30% pour l'impôt évité)
- `performance` : NETTE de frais + impôts (= la vraie perf)
- `performance_brute` : sans coûts, pour référence pédagogique uniquement
- Sur chaque ordre VENTE : `plus_value_eur`, `impot_pfu_eur`, `perte_reportable_eur`, `frais_vente_eur`
- Sur chaque ordre ACHAT : `frais_achat_eur`, `montant_brut_eur`, et `montant` = base fiscale (= brut + frais)

Quand tu commentes une vente dans `analyse_macro` ou `message_utilisateurs`, mentionne explicitement le PFU si applicable : *"Vente AIR.PA à +12.6%, plus-value 196€ → PFU 59€ → cash net 1689€ ajouté aux liquidités."* C'est la transparence éditoriale.
