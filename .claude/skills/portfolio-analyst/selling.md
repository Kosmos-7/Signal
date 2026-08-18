# Discipline de vente

La vente est statistiquement la décision où le retail détruit le plus de valeur. Cause #1 : le **disposition effect** (vendre les gagnants trop tôt, garder les perdants trop longtemps).

## Le test fondamental : "Would I buy at current price today?"

**La question seule qui compte**, posée systématiquement avant toute décision de garder/vendre une position :

> *"Si je n'avais pas cette position, achèterais-je cette action au prix actuel ?"*

- Si **oui** → garder, voire renforcer si la pondération le permet
- Si **non** → vendre

Cette question élimine l'anchoring sur le prix d'achat. Le marché ne sait pas et ne se soucie pas de ton prix d'entrée.

**Pourquoi c'est puissant** : sépare la décision d'investissement présente du regret/satisfaction passé. Force à raisonner forward-looking.

## Règles de vente à pré-définir AVANT l'achat

L'erreur classique : décider de vendre **après** que la position commence à bouger contre toi (loss aversion en plein action). La discipline : écrire les conditions de vente **avant** d'acheter.

**Template** :
```
Achat XYZ à 100€ — date YYYY-MM-DD
Thèse: [résumé en 2-3 phrases]
Vente déclenchée si:
  1. Stop-loss à -15% (technique)
  2. Catastrophe à -25% (sans condition de durée)
  3. Earnings miss avec révision baissière du consensus analystes
  4. Rupture de la thèse fondamentale (ex: perte du leader sectoriel)
  5. Score watchlist tombe sous 50/100 trois semaines consécutives
Horizon minimum de hold: 90 jours sauf événement fondamental majeur
```

Si la position bouge et que **aucune** des conditions de vente n'est déclenchée, **garder** — peu importe la douleur émotionnelle ou la tentation.

## Hiérarchie des stop-loss (inspiré Signal)

1. **R07 — Stop-loss standard** : -15% après 90 jours de détention. Rationalité : si après 3 mois la thèse n'a pas tenu et la perte est significative, accepter l'erreur.

2. **R08 — Stop-loss catastrophe** : -25% sans condition de durée. Rationalité : protège contre les effondrements rapides dans les 89 premiers jours (le "trou" entre R01 et R07).

Les deux sont **mécaniques** — pas de discussion possible. C'est précisément l'absence de jugement émotionnel qui les rend efficaces.

## Anti-disposition concrète

### Symptôme 1 : tentation de vendre un gagnant

**Question test** : *"Pourquoi exactement je veux vendre ?"*
- *"Pour sécuriser mes gains"* → loss aversion inversée. Le marché n'a pas vu ces gains, ils ne sont pas "tiens" tant que tu n'as pas une meilleure utilisation du capital.
- *"Parce que je pense que ça va baisser"* → tu as une **thèse de retournement** documentée ? Si oui, OK. Sinon c'est de l'intuition.
- *"Parce que c'est devenu trop gros dans mon portefeuille"* → légitime, mais c'est une question de **rebalancing**, pas de vente. Vendre une fraction (25-50%) suffit.

### Symptôme 2 : refus de vendre un perdant

**Question test** : *"Si la thèse d'achat était formulée aujourd'hui, l'achèterais-je ?"*
- *"Pas vraiment, mais je veux attendre que ça remonte"* → drapeau rouge. **Le marché ne te doit rien.** Vendre.
- *"Oui, la thèse tient encore"* → garder, et même éventuellement renforcer (si le scoring est meilleur maintenant qu'à l'achat). Mais pas par devoir d'averaging down.

### Symptôme 3 : sentiment d'urgence

Quand la pulsion de vendre vient d'une **émotion** (panique, regret, euphorie), **attendre 24-48h** avant d'agir. Si après ce délai tu peux articuler la décision en termes techniques (signal, fondamental, règle), elle est sans doute valide. Sinon, elle vient du système 1 (Kahneman).

## Disposition effect en chiffres

Odean (1998) — *Are Investors Reluctant to Realize Their Losses?*, Journal of Finance — étude sur 10 000 comptes brokerage :

> *"Investors demonstrated a strong preference for realizing winners rather than losers. The subsequent return of the prior winners they sold was, on average, higher than the subsequent return of the prior losers they held."*

Les gagnants vendus continuent de monter. Les perdants gardés continuent de baisser. Le pattern moyen est **statistiquement confirmé**.

Cela ne veut pas dire "ne jamais vendre les gagnants" ou "toujours vendre les perdants" — ce serait une caricature. Cela veut dire : **la pulsion par défaut** des retail va **dans la mauvaise direction**, donc il faut une discipline pour la contrer.

## Quand vendre légitimement

Liste des raisons valables, par ordre de robustesse :

1. **Stop-loss mécanique déclenché** (R07/R08) — pas de discussion
2. **Thèse fondamentale rompue** (changement de management, nouveau concurrent disruptif, scandale comptable) — vente totale rapide
3. **Allocation devenue déséquilibrée** (>20% du capital) — vente partielle pour rebalancer
4. **Meilleure opportunité identifiée** (score significativement supérieur ailleurs ET pas de cash dispo) — vente pour rotation
5. **Besoin de liquidité hors investissement** (achat immobilier, etc.) — vente programmée
6. **Tax-loss harvesting** (en fin d'année fiscale) — vente technique avec rachat compatible règles fiscales

**Ce qui n'est PAS une raison valable** :
- *"Le marché va baisser"* — timing de marché, statistiquement perdant
- *"J'ai assez gagné"* — anchoring sur P&L, pas sur valeur
- *"Je m'ennuie"* — action bias
- *"Mon ami a vendu"* — herding
- *"Death Cross frais"* si `signal_dynamics_warning` indique transition — attendre confirmation (golden cross qui se reforme OU cours qui repasse durablement sous MM200) avant de trancher

## Allègement partiel (trim) — la vente qui n'est pas une sortie

Le trim était mentionné en creux (« vendre une fraction (25-50%) suffit ») sans jamais être formalisé — résultat mesuré côté Signal : 0 allègement en 42 ordres, alors que la mécanique existait. La doctrine, maintenant explicite :

### Déclencheurs légitimes (au moins un requis, à nommer dans la justification)

1. **Poids ≥ 15% du capital** après un rally — problème de concentration, pas d'opinion sur le titre. C'est le déclencheur canonique : le rebalancing de la raison valable n°3 ci-dessus, appliqué AVANT le mur des 20%
2. **Surcote extrême** (z > +2σ vs tendance) avec fondamentaux intacts — dégonfler l'exposition au re-rating sans sortir de la thèse
3. **Thèse partiellement affaiblie** — un pilier sur trois a cédé : réduire est plus honnête que sortir (sur-réaction) ou tenir à 100% (déni)
4. **Financement d'une opportunité nettement supérieure** quand le cash manque et qu'aucune position n'a de thèse cassée

### Tailles

| Fraction | Cas |
|---|---|
| 25% | Ajustement de poids, thèse intacte |
| 33% | Surpoids net (≥ 15%), rally étendu |
| 50% | Thèse abîmée mais vivante |

Jamais moins de 25% : frais + fiscalité rendent le geste symbolique. Jamais de trim sur une ligne d'un titre — indivisible, toute vente y est totale.

### Le test net d'impôt (compte-titres)

Sur compte-titres ordinaire, chaque euro de plus-value RÉALISÉE paye ~31,4% de PFU ; la plus-value LATENTE ne paye rien, indéfiniment. L'allègement est donc un outil de **gestion du risque de concentration**, jamais de « prise de gains » :

> Alléger 33% d'une ligne à +100% qui pèse 16% du capital = payer ~31,4% d'impôt sur un tiers du gain, CONTRE une réduction mesurable du risque de concentration (16% → ~11%). Le coût est certain, le bénéfice est une réduction de variance — le trade est défendable.
>
> « Sécuriser ses gains » sans usage alternatif du capital identifié = payer le même impôt certain contre un bénéfice **hypothétique** (la peur que ça baisse). C'est le disposition effect en habits respectables — voir Symptôme 1 ci-dessus.

### Ce qu'un trim n'est PAS

- **Pas un demi-stop-loss** : alléger un perdant pour « soulager la douleur » combine le pire des deux mondes (on garde le risque ET on cristallise une partie de la perte sans la discipline mécanique de R07/R08)
- **Pas un timing de marché** : « ça a trop monté, ça va corriger » sans thèse de retournement documentée reste du market timing, en fraction comme en totalité
- **Pas un compromis émotionnel** : si l'analyse dit vendre, vendre ; trimmer parce qu'on n'ose pas trancher est une non-décision déguisée

## Test du miroir

Pour chaque vente envisagée, écrire dans un journal :
- Date
- Ticker, prix de vente, prix d'achat, perf
- Raison (en 1 phrase précise)
- Catégorie : mécanique / thèse / rebalance / rotation / fiscal / **émotionnel**

Si la catégorie "émotionnel" représente >20% des ventes sur 12 mois, il y a un problème de discipline qu'il faut adresser structurellement (peut-être : ajouter des règles plus contraignantes ou réduire la fréquence de check du portefeuille).
