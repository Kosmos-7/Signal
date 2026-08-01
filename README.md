# Signal

Screener d'actions + portefeuille fictif piloté par IA, publié sur GitHub Pages :
**https://kosmos-7.github.io/Signal/**

Posture : **neutre, aucune prétention d'alpha**. Signal applique avec discipline des méthodes
publiques (momentum Jegadeesh-Titman, value Graham-Dodd, analyse technique Murphy, base rates
Mauboussin) et met sa méthodologie à l'épreuve par l'observation d'un portefeuille IA **en réel**
— pas par des backtests. Voir [apprendre.html](https://kosmos-7.github.io/Signal/apprendre.html)
pour la pédagogie complète et [CHANGELOG.md](CHANGELOG.md) pour l'historique.

## Scoring v3 (gelé pour le trimestre — depuis 2026-06-01)

```
Qualité du business →  45 pts  (marge nette 8 + marge FCF 8 + ROE 12 + croissance CA 10 + dette 7)
Valorisation        →  30 pts  (PEG 15 + FCF yield 15)
Timing (garde-fou)  →  22 pts  (cross 10 + pente MM21 4 + volume 3 + RSI 2 + régression 3)
Analystes           →   3 pts
                       ─────
                       100 pts  ± ajustements (chase −6/−4 · death −5/−3 · décote +6/+4)
```

La qualité et le prix pilotent (75 pts) ; le timing borne le risque. `val_pts` (drawdown 52w),
le retracement Fibonacci et le VIX sont publiés à titre **informationnel** (hors score).

## Architecture

```
themes.py ────────────► taxonomie        (2 watchlists thématiques : infra-ia, financials ;
                                          les tickers déclarés entrent dans l'univers)
screener.py ──────────► watchlist.json   (210 tickers scorés → top 30, hebdo)
                        universe.json    (thèmes + carte compacte des titres tagués)
                        charts/<T>.json  (canal de régression par titre, chargé à la demande)
portfolio_agent.py ───► portfolio.json   (décisions Claude API + règles mécaniques, hebdo ;
                                          univers achetable = top 30 ∪ titres tagués)
update_prices.py ─────► portfolio.json   (refresh prix/VIX/benchmarks, quotidien, sans IA)
generate_analyses.py ─► analyses.json    (fiches éditoriales Claude — complètes pour le
                                          top 30, courtes pour les titres thématiques)

index.html      homepage des watchlists + fiches — lit watchlist.json, universe.json,
                analyses.json, et charts/<TICKER>.json à l'ouverture d'une fiche
portfolio.html  lit portfolio.json
apprendre.html  page pédagogique statique
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

- [config.py](config.py) — paramètres centralisés (frais 7,5 bps, PFU 30 %, WATCHLIST_SIZE, règles)
- [screener.py](screener.py) — scoring v3 + détection cross + régression log-linéaire (fenêtres 10/20/25 ans)
- [portfolio_agent.py](portfolio_agent.py) — agent Claude 2 passes (Haiku analyse → Sonnet décisions) + règles non négociables appliquées en code (stop-loss R07/R08, mode panique sticky, concentration sectorielle, weekend, ticker ∈ watchlist, cash ≥ 0). Gestes : ouvrir/fermer, **rotation** (ventes exécutées avant achats, max 1/run), **renforcement** (PRU pondéré, plafond 20 %) et **allègement** (`allegement_pct`, PFU au prorata) — cf. CHANGELOG 3.1.0/3.2.0
- [.claude/skills/portfolio-analyst/](.claude/skills/portfolio-analyst/) — skill d'analyse (méthodologie, biais, discipline de vente)

## Lancer localement

```bash
pip install -r requirements.txt
python screener.py            # FINNHUB_API_KEY optionnel (cross-validation fonda)
python update_prices.py       # refresh prix sans IA
python portfolio_agent.py     # nécessite ANTHROPIC_API_KEY
```
