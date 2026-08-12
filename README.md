# Signal

Screener d'actions + portefeuille fictif piloté par IA, publié sur GitHub Pages :
**https://kosmos-7.github.io/Signal/**

Posture : **neutre, aucune prétention d'alpha**. Signal applique avec discipline des méthodes
publiques (momentum Jegadeesh-Titman, value Graham-Dodd, analyse technique Murphy, base rates
Mauboussin) et met sa méthodologie à l'épreuve par l'observation d'un portefeuille IA **en réel**
— pas par des backtests. Voir [apprendre.html](https://kosmos-7.github.io/Signal/apprendre.html)
pour la pédagogie complète et [CHANGELOG.md](CHANGELOG.md) pour l'historique.

## Note v4 (2026-08-06) — moteur : note_v4.py

```
Qualité      →  35 pts  niveaux des comptes   (marge médiane 9 + ROE 9 + conversion cash 7
                                               + bilan 5 + constance 5)
Croissance   →  25 pts  dérivées des comptes  (TCAM CA 7 + TCAM BPA 7 + régularité 4
                                               + attendu 7, borné ≤ démontré)
Valorisation →  25 pts  cours ÷ comptes       (PER vs sa médiane d'époque 8 + PEG maison 7
                                               + rdt bénéfices 5 + rdt cash 5)
Momentum     →  15 pts  cours ÷ cours         (écart MM21/MM200 6 + cloche z 6 + cloche RSI 3)
                ─────
                100 pts  rampes continues partout ; critère incalculable = retiré avec motif
                         + renormalisation (jamais de zéro muet) ; ni pénalité ni bonus
```

Partition MECE par domaine de donnée : chaque information n'est comptée qu'une fois.
~58 % de la note repose sur l'historique comptable vérifié ; le marché (V+M) est plafonné à
40 pts. Le cross MM, `val_pts` (drawdown 52w), Fibonacci, le consensus analystes et le VIX
sont publiés à titre **informationnel** (hors note — l'IC du timing v3 était négatif, −0,33).

## Architecture

```
themes.py ────────────► taxonomie        (2 watchlists : infra-ia + le filtre PEA ;
                                          les tickers déclarés entrent dans l'univers)
screener.py ──────────► watchlist.json   (210 tickers scorés → top 30, hebdo)
                        universe.json    (thèmes + carte compacte des titres tagués)
                        charts/<T>.json  (canal de régression par titre, chargé à la demande)
portfolio_agent.py ───► portfolio.json   (décisions Claude API + règles mécaniques, hebdo ;
                                          univers achetable = top 30 ∪ titres tagués)
update_prices.py ─────► portfolio.json   (refresh prix/VIX/benchmarks, quotidien, sans IA)
generate_analyses.py ─► analyses.json    (fiches éditoriales Claude — complètes pour le
                                          top 30, courtes pour les titres thématiques)
tools/jeu_marche.py ──► jeu/marche.json  (pack de marché du jeu La Maison : 80 titres
                                          rééchantillonnés au mois depuis charts/, hebdo)

index.html      homepage des watchlists + fiches — lit watchlist.json, universe.json,
                analyses.json, et charts/<TICKER>.json à l'ouverture d'une fiche
portfolio.html  lit portfolio.json
apprendre.html  page pédagogique statique
maison.html     jeu de simulation « La Maison » (société de gestion fictive, cours réels,
                noms masqués) — lit jeu/marche.json, sauvegarde en localStorage uniquement
```

## Workflows GitHub Actions

| Workflow | Cron | Fait | Secrets |
|---|---|---|---|
| `daily-prices.yml` | L-V 22h UTC | `update_prices.py` → commit portfolio.json | aucun |
| `watchlist.yml` | lundi 8h UTC | screener + portfolio_agent + analyses → commit | `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY` |

Les deux partagent un groupe `concurrency` (pas d'écritures concurrentes). Les JSON sont écrits
de façon **atomique et stricte** (`save_json_atomic`, `allow_nan=False`) : une donnée corrompue
fait échouer le job bruyamment au lieu de casser le site en silence (leçon de l'incident NaN
du 02-09/06/2026, cf. CHANGELOG 3.0.1).

## Fichiers clés

- [config.py](config.py) — paramètres centralisés (frais 7,5 bps, PFU 31,4 % depuis la LFSS 2026, WATCHLIST_SIZE, règles)
- [screener.py](screener.py) — scoring v3 + détection cross + régression log-linéaire (fenêtres 10/20/25 ans)
- [portfolio_agent.py](portfolio_agent.py) — agent Claude 2 passes (Haiku analyse → Sonnet décisions) + règles non négociables appliquées en code (stop-loss R07/R08, mode panique sticky, concentration sectorielle, weekend, ticker ∈ watchlist, cash ≥ 0). Gestes : ouvrir/fermer, **rotation** (ventes exécutées avant achats, max 1/run), **renforcement** (PRU pondéré, plafond 20 %) et **allègement** (`allegement_pct`, PFU au prorata) — cf. CHANGELOG 3.1.0/3.2.0
- [.claude/skills/portfolio-analyst/](.claude/skills/portfolio-analyst/) — skill d'analyse (méthodologie, biais, discipline de vente)
- [maison-moteur.js](maison-moteur.js) — moteur de simulation du jeu, pur (zéro DOM, zéro fetch), rejouable sous node par les tests ; même graine + mêmes décisions = même partie
- [tools/jeu_marche.py](tools/jeu_marche.py) — génère jeu/marche.json (écriture atomique, purge des orphelins) ; la spécification complète du jeu vit dans [PROMPT_jeu_simulation.md](PROMPT_jeu_simulation.md)

## Lancer localement

```bash
pip install -r requirements.txt
python screener.py            # FINNHUB_API_KEY optionnel (cross-validation fonda)
python update_prices.py       # refresh prix sans IA
python portfolio_agent.py     # nécessite ANTHROPIC_API_KEY
```
