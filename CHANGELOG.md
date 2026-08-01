# Changelog — Signal

Toutes les évolutions notables du projet sont documentées ici.
Format inspiré de [keepachangelog.com](https://keepachangelog.com/fr/).

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
