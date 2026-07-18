# Changelog — Signal

Toutes les évolutions notables du projet sont documentées ici.
Format inspiré de [keepachangelog.com](https://keepachangelog.com/fr/).

---

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
