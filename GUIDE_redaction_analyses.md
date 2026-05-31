# Guide de rédaction des analyses (watchlist)

> Le **design ne change pas**. La qualité d'une fiche tient à ce que la **prose** réponde aux
> vraies questions d'un propriétaire d'entreprise (cadre tiré des lettres Buffett). 4 axes, zéro
> chrome en plus. Voir aussi `SYNTHESE_Principes_Buffett.md` (dossier Berkshire).

---

## 1. Les champs de `analyses.json` et ce qu'ils doivent répondre

| Champ | Ce qu'il DOIT répondre |
|---|---|
| **`resume`** (1-2 §) | Ce que fait la boîte en une phrase + le **débat central** (le point de tension n°1). Relier le score à la *qualité à un instant T*, jamais au timing. |
| **`biz`** (Business & Moat) | (1) comment elle **gagne de l'argent** ; (2) quel **type de douve** ; (3) **est-elle durable** et **qu'est-ce qui la menace**. La durabilité est une *hypothèse*, jamais un acquis (leçon Dexter Shoe). |
| **`futur`** (Perspectives) | Les **drivers** de croissance + un **cadrage prix vs valeur** (cher / correct / décoté, en relatif). **Pas d'objectif de cours.** |
| **`actu`** (Actu) | Faits récents **datés, chiffrés, vérifiables**. Pas d'interprétation déguisée en fait. |
| **`bull`** (3 puces) | La **thèse** : pourquoi ça marche, chiffré. |
| **`bear`** (3 puces) | L'**inversion** : qu'est-ce qui ferait **échouer** la thèse (pas seulement « c'est cher »). |

### Les 5 types de douve (à nommer explicitement dans `biz`)
Marque / réputation · Avantage de coût (producteur le moins cher) · Effet de réseau · Coûts de
transfert (verrouillage client) · Actif réglementaire ou de localisation. Si aucun n'est
identifiable → ce n'est **pas** une franchise, c'est un « business » (souvent cyclique/fragile).

---

## 2. Règles (do / don't)

**Ton** — précis, factuel, clair et **posé** ; plume vivante avec une pointe d'esprit pince-sans-rire *occasionnelle* (jamais lourde, jamais de hype, jamais de reco déguisée). Le fond prime toujours sur le trait d'esprit.

**DO**
- Raisonner en **propriétaire**, horizon long ("would I buy the whole company today?").
- **Nommer** le type de douve et **questionner sa durabilité** (qu'est-ce qui la tuerait ?).
- Traiter le **momentum comme du timing** (déclencheur), jamais comme une thèse.
- **Chiffrer** (CA, marges, FCF, PER forward vs historique) ; privilégier le **FCF** au bénéfice « ajusté ».
- **Toujours préciser la temporalité** d'un chiffre fondamental : la croissance du CA fournie est *trimestrielle en glissement annuel* (dernier trimestre publié vs même trimestre N-1), les marges nette & FCF sont en *TTM* (12 mois glissants). Ne jamais écrire « croissance du CA de X % » sans la période.
- **Chiffrer TOUTE affirmation de valorisation** : PER forward, PER courant, FCF yield, PEG, z-score. Les qualificatifs vagues seuls (« fourchette haute », « cher », « tendu ») sont **interdits** sans nombre à l'appui. Ne jamais inventer un multiple historique ou de pair non fourni ; pour le relatif-historique, s'appuyer sur le **z-score** (seule mesure sourcée). Un PER courant ≫ PER forward = bénéfices au creux de cycle (l'expliquer, ne pas le lire comme « cher »).
- Rester dans le **cercle de compétence** : dire clairement quand la durabilité n'est **pas** évaluable.

**DON'T**
- ❌ Objectif de cours / valeur intrinsèque inventée (Buffett raisonne en *fourchette*, pas en cible).
- ❌ « Ça a monté, donc on achète » — le momentum n'est jamais la raison d'une thèse.
- ❌ Présenter une douve comme **éternelle** (surtout en secteur à changement rapide : tech, semi).
- ❌ S'appuyer sur EBITDA / chiffres « ajustés » non corroborés par le cash.
- ❌ Storytelling séduisant mais non vérifiable.

---

## 3. Mini-checklist par fiche (5 questions)

1. Qu'est-ce que la boîte, et **comment gagne-t-elle de l'argent** ?
2. **Quelle douve**, est-elle **durable**, **qu'est-ce qui la menace** ?
3. Le prix est-il **cher / correct / décoté** vs la qualité ? *(sans cible chiffrée)*
4. **Qu'est-ce qui ferait échouer** la thèse ? *(= contenu du `bear`)*
5. Le momentum est-il un **déclencheur**, ou la **seule** raison d'acheter ? *(si seule raison → méfiance)*

---

## 4. Exemple appliqué — NVDA

- **`resume`** — « Concepteur dominant des GPU/plateformes de calcul IA. Le score de 90 reflète des
  fondamentaux exceptionnels (CA +85 % a/a au dernier trim., marge nette 63 % TTM) — une note de *qualité*, pas un timing.
  Débat central : valorisation forward raisonnable (PER 16,7) vs durabilité du cycle IA. »
- **`biz`** — *(comment)* vente de GPU haut de gamme + réseau + logiciel ; marge brute ~74 % =
  fort pricing power. *(type de douve)* **coûts de transfert** (écosystème CUDA) + effet de réseau
  développeurs. *(durabilité + menace)* « sa durabilité reste l'hypothèse la plus fragile, menacée
  par les puces maison des clients (Google, Amazon, OpenAI via Broadcom). »
- **`futur`** — drivers Blackwell/Rubin + clients souverains ; *prix vs valeur* : raisonnable en
  forward (PER 16,7), tendu sur l'historique (32) — pas d'objectif de cours.
- **`bear` (inversion)** — concentration de la demande + puces maison (la douve), restrictions Chine,
  valorisation totale laissant peu de place à la déception. → ce sont les **menaces de perte
  permanente**, pas la volatilité.

---

## 5. Application

Progressive, fiche par fiche — aucune migration de masse nécessaire. Le seul changement de
présentation déjà fait : « Signaux techniques » → « **Signaux de timing** » (fiche + lexique).
