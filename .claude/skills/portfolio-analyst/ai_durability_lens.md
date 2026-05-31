# Lens durabilité IA (titres exposés au cycle capex)

Cadre de discipline pour juger si la **thèse de durabilité** d'un titre exposé au super-cycle IA tient — pas pour prédire un cours.

## Statut NEUTRE

Cette lens **ne prédit aucun cours** et ne dit pas « achète ». Elle juge une seule chose : la thèse implicite de durabilité d'un titre IA-exposé est-elle robuste, et à quel(s) scénario(s) ? Elle complète le scoring (`methodology.md`) et le filtre Moloch/douve (`frameworks.md` §9) ; elle ne les remplace pas.

## Mécanique du scaling (le moteur de fond du capex)

Empilement de résultats techniques paraphrasés (Transformer 2017, Chinchilla 2022, *Bitter Lesson* de Sutton, *Scaling Hypothesis* de Gwern) :

- **compute + données + paramètres → capacité**, selon une **loi de puissance** (les courbes de scaling). Plus de calcul et de données → modèles plus capables, de façon empiriquement régulière jusqu'ici.
- **Bitter Lesson** : sur ~70 ans d'IA, les méthodes qui exploitent le **calcul général** battent l'ingénierie de connaissance spécialisée. C'est un pattern structurel de fond, pas une mode → moteur durable de la demande de compute.
- Bascule progressive **training → inférence** : le coût se déplace de l'entraînement (one-shot) vers l'**inférence récurrente** (chaque requête), ce qui change la nature de la demande hardware.
- **Incertitude assumée sur le point d'inflexion** : sommes-nous sur une sigmoïde qui va plafonner, ou avant une accélération ? (*« sigmoid or singularity ? »*). Personne ne le sait — la lens **ne tranche pas**.

## MOTEURS du cycle (M)

Forces qui prolongent le super-cycle capex :

- **M1 — Pression compute structurelle** : la demande de calcul croît avec la capacité visée (Bitter Lesson).
- **M2 — Courbes de scaling non infléchies** : tant que plus de compute = plus de capacité, l'incitation à dépenser persiste.
- **M3 — Inférence récurrente** : déploiement en production → demande hardware **continue** (pas one-shot).
- **M4 — Architecture parallélisable** : le Transformer scale bien sur GPU/accélérateurs → l'investissement hardware reste utile.
- **M5 — Conviction / hardware-overhang** : les acteurs surinvestissent par peur de manquer la capacité (option sur l'upside).
- **M6 — Demande de données** : la course aux données (et à leur traitement) soutient la chaîne.

## CASSEURS / points de rupture (R)

Forces qui peuvent casser la thèse de continuation linéaire :

- **R1 — Mur de données** : épuisement des données de qualité → le scaling par les données cale.
- **R2 — Rendements décroissants du scaling** : la loi de puissance s'aplatit (plus de compute, gain marginal faible).
- **R3 — Efficience algorithmique** (type DeepSeek) : une rupture d'efficience réduit le compute requis → menace directe pour la thèse « toujours plus de capex ».
- **R4 — Puces maison des clients** : les hyperscalers conçoivent leurs propres accélérateurs → **menace sur la douve des designers** (érosion du pricing power).
- **R5 — Plafond énergie / réseau électrique** : disponibilité électrique et raccordement = **contrainte binding actuelle** la plus citée (le goulot s'est déplacé du silicium vers l'énergie).
- **R6 — ROI applicatif insuffisant** : si la monétisation applicative déçoit → **trou d'air** entre capex engagé et revenus → coupes d'investissement.

## 3 SCÉNARIOS à pondérer (ne pas en privilégier un)

| Scénario | Description | Risque dominant |
|---|---|---|
| **A — Buildout haussier** | Capex continue, scaling tient, monétisation suit | Sur-extrapolation (cf. §10 S-curve `frameworks.md`) |
| **B — Plateau / diffusion lente** | Adoption réelle mais lente ; capex en **avance** sur la monétisation | **Air-pocket** : digestion / coupe de capex avant que les revenus rattrapent |
| **C — Rupture exogène** | Choc hors-modèle | Taïwan, régulation, incident de sécurité majeur |

Discipline : **assigner des poids explicites** aux trois, ne pas raconter un seul futur. Le scénario B est le plus traître car il ressemble au A jusqu'au moment où le capex se contracte.

## Durabilité par type d'acteur (robustesse-aux-scénarios DÉCROISSANTE)

```
Énergie / infra  >  Équipement / fabs  >  Hyperscalers  ≈  Designers chers
(scenario-agnostic)  (douve durable,        (portent le capex)  (les + exposés
                      mais Taïwan binaire)                        au scénario B)
```

- **Énergie / infra électrique** : la plus **scenario-agnostic** — quel que soit le gagnant logiciel, il faut de l'électricité et des datacenters. Robuste même en B partiel.
- **Équipement / fabs** : **douve durable** (oligopole, barrières techno extrêmes) mais **risque Taïwan binaire** (R-scénario C).
- **Hyperscalers** : **portent** le capex (ils paient la facture) — exposés si le ROI applicatif (R6) déçoit, mais diversifiés.
- **Designers chers** : les **plus exposés au scénario B** et à R4 (puces maison des clients) ; valorisations qui pricent souvent une continuation linéaire.

**Cohérence avec le scoring v2.0.2** (`methodology.md` §1.4) : seul l'**équipement** (`Semiconductor Equipment & Materials` : AMAT, LRCX, KLAC, ASML) est traité en cyclique 25y ; les **designers** (NVDA, AMD, AVGO, MU) retombent en tech 10y. La hiérarchie de durabilité ci-dessus en est le pendant qualitatif.

## LE CADRE — 5 questions de durabilité

Pour tout titre IA-exposé, répondre :

1. **Position dans la chaîne** : énergie/infra, équipement/fabs, hyperscaler, ou designer ? (détermine la robustesse-aux-scénarios de base)
2. **Moteur** : la thèse repose-t-elle sur le **training** (one-shot, sensible à R2/R3) ou l'**inférence récurrente** (M3, plus durable) ?
3. **Nature de la douve** : est-elle menacée par **R4** (puces maison) ? Une douve attaquable par les propres clients est fragile.
4. **Casseur actif** : lequel de R1-R6 est **déjà à l'œuvre** sur ce titre précis ? (un seul casseur en cours suffit à invalider)
5. **Asymétrie / prix** : le cours **intègre-t-il déjà une continuation linéaire** du super-cycle ? (si oui, l'upside est borné et le downside scénario-B est sous-estimé)

**Verdict de durabilité** : thèse **solide si ≥3 questions favorables ET aucun casseur (R1-R6) en cours** sur ce titre. Sinon, décoter la conviction et réduire le sizing.

## Base rates super-cycle (indicatifs — à vérifier)

- Cycle semis classique : ~**3-4 ans** pic-à-pic.
- Expansions capex : typiquement **2-4 ans** avant digestion / surcapacité.
- Les booms d'investissement **finissent en surcapacité** (mécanique du **double-ordering** : commandes gonflées par peur de pénurie → annulations en cascade).
- **Durée du super-cycle IA = INCONNUE.** Toute thèse supposant **>3-4 ans de capex linéaire** est un **pari de conviction**, pas une base rate → **sizing prudent** et monitoring du capex guidance des hyperscalers comme signal avancé.

## CAVEATS DE NEUTRALITÉ (essentiels)

Le corpus IA optimiste (Aschenbrenner, Amodei, Kokotajlo, Hendrycks, Bubeck) est composé de **parties prenantes** :

- **Biais haussier structurel** : ces auteurs ont un intérêt direct (réputation, certains **gèrent ou conseillent des fonds long-IA**) → **décoter leur optimisme**, ne pas l'ancrer.
- **Prédictions datées déjà fragiles** : plusieurs timelines publiées vieillissent mal → traiter toute date précise avec scepticisme.
- **Le désaccord interne au corpus est un signal** : quand les experts ne s'accordent pas sur le timing/l'inflexion, c'est une information sur l'incertitude — **à pondérer, pas à suivre**.
- Appliquer le **pré-flight** (`SKILL.md`) : conviction conservative au premier passage, anti-auto-anchoring, re-dérivation à chaque info nouvelle.

**En somme** : cette lens structure le débat de durabilité d'un titre IA-exposé ; elle ne désigne pas de gagnant et ne donne pas de cible de cours. Une thèse IA solide doit survivre au scénario B, pas seulement briller dans le A.
