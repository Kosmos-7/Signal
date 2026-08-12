# Prompt — « La Table » : jeu de simulation d'investissement pour Signal

> **Comment s'en servir.** Ce fichier est un prompt à coller tel quel dans Claude Code, à la
> racine du dépôt Signal. Tout ce qui suit s'adresse à l'agent qui va écrire le code.
> Les sections **§0 à §3** posent l'intention, **§4 à §11** sont des contraintes dures
> (le code sera refusé s'il les viole), **§12 à §15** disent quand c'est fini.

---

## §0 — Rôle et posture

Tu travailles sur **Signal** (https://kosmos-7.github.io/Signal/), un site statique publié sur
GitHub Pages : screener d'actions, portefeuille fictif piloté par IA, page pédagogique.
Posture éditoriale du projet, à ne jamais trahir : **neutre, aucune prétention d'alpha**, on
applique des méthodes publiques avec discipline et **on publie ses erreurs**.

Tu ajoutes un **cinquième onglet** : un jeu de simulation d'investissement. Fun, éducatif,
et doté d'une interface qui ne ressemble à aucune autre page du site — tout en restant
manifestement du même site.

**Lis ces fichiers AVANT d'écrire une ligne** (ils contiennent les règles que tu dois respecter,
et l'esprit dans lequel elles ont été écrites) :

| Fichier | Ce que tu y cherches |
|---|---|
| `README.md` | l'architecture, les workflows, la posture |
| `signal.css` | le design system entier — tokens, chrome, composants réutilisables |
| `actualites.html` (20 Ko) | le gabarit d'une page : `<head>`, chrome, footer, script inline |
| `tests/test_chrome.py` | **les règles que ta page devra passer** — lis-le en entier |
| `tests/_sans_bibliotheques.py` | pourquoi un test vert en local peut être rouge en CI |
| `config.py` | frais de transaction, PFU, seuil minimal d'ordre |
| `screener.py` §« PAYLOAD GRAPHIQUE » (~l.362) | le format exact de `charts/<TICKER>.json` |
| `CHANGELOG.md` (les 100 premières lignes) | la **voix** du projet — tu écriras dedans |
| `.claude/skills/portfolio-analyst/biases.md` | le vocabulaire des biais, que le jeu réutilise |

---

## §1 — Mission en une phrase

Ajouter à Signal **« La Table »** : un simulateur jouable en trente secondes, qui rejoue de
**vraies séries de prix anonymisées** et qui, à la fin, montre au joueur **ce que ses propres
gestes lui ont coûté** — frais, impôt, biais — comparé à ne rien faire du tout.

---

## §2 — Ce que le jeu doit être, et ce qu'il ne doit surtout pas être

**Il doit être :**
- **honnête** : les prix sont réels, les frais et l'impôt sont ceux de `config.py`, la
  comparaison « toi vs ne rien faire » est toujours affichée, jamais optionnelle ;
- **court** : une partie = 2 à 4 minutes, pas de tutoriel de dix écrans, pas de compte, pas
  d'inscription, pas de backend ;
- **rejouable** : un défi du jour identique pour tout le monde, un résultat partageable en
  texte ;
- **pédagogique par la démonstration, jamais par le sermon** : le jeu ne dit pas « attention au
  sur-trading », il te montre ta facture de frais à côté de ta performance.

**Il ne doit pas être :**
- ❌ un entraînement au trading ni une promesse de compétence transférable — le message final
  d'une partie n'est jamais « bien joué, tu as le nez » ;
- ❌ un casino déguisé : pas d'argent réel, pas d'achat, pas de monnaie premium, pas de
  mise qui grandit pour « se refaire », pas de récompense à la fréquence de jeu ;
- ❌ un simulateur de CFD, de turbos ou de levier vendus comme normaux ;
- ❌ un classement mondial (il n'y a pas de backend, et l'absence de classement est aussi le
  bon choix : un tableau des scores transforme un exercice de lucidité en concours de chance).

**Le mot « gambling » de la demande est traité ainsi : le hasard est le SUJET du jeu, pas son
moteur commercial.** Le mode « La Pièce » (§3.2) est une démonstration mathématique du risque
de ruine — le joueur y perd presque toujours, et il comprend pourquoi. C'est la seule forme
sous laquelle un site d'information financière peut honnêtement mettre un casino sur une page.

---

## §3 — Le concept : « La Table », trois modes

Le nom joue sur le double sens : **la table de marché** et **la table de jeu**. La question que
la page pose au visiteur, et à laquelle les trois modes répondent, est : *à laquelle des deux
es-tu assis ?*

### §3.1 — Mode 1 : « Le Rideau » (mode principal)

Rejeu à l'aveugle d'une vraie série de prix.

- Un titre est tiré au sort (graine reproductible, cf. §7.4) parmi ceux de `jeu/index.json`.
- **Anonymat total pendant la partie** : ni nom, ni ticker, ni secteur, ni devise, ni dates.
  La série est **rebasée à 100** au premier point (sinon le NVDA ajusté de 1999 à 0,036 $ vend
  la mèche). L'axe du temps est en **semaines relatives** : `S+1`, `S+2`… jamais « mars 2020 ».
- **104 semaines**, révélées une par une. À chaque semaine, le joueur ajuste son **exposition**
  par crans de 25 % (0 / 25 / 50 / 75 / 100 % du capital), ou ne fait rien.
- Capital de départ : **10 000 €** fictifs. Chaque changement d'exposition est un ordre :
  **frais de 7,5 bps** appliqués au montant échangé (`config.py`), ordre refusé sous
  **50 €** (`MIN_TRADE_EUR`).
- À la fin : liquidation, **PFU de 31,4 %** sur la plus-value nette réalisée (§7.2).
- **La révélation** (le moment de la partie) :
  1. l'identité du titre, la vraie période, et son graphe en entier ;
  2. **trois chiffres côte à côte** : ta performance nette · l'achat-conservation sur la
     même fenêtre · le cash qui n'a rien fait ;
  3. ce que tes gestes ont coûté : total des frais, impôt, et **l'écart entre ta performance
     brute et nette** ;
  4. **les 26 semaines suivantes**, celles que tu n'as pas jouées — pour que le joueur voie
     que « avoir eu raison » a une date de péremption ;
  5. un lien vers la fiche du titre (`index.html`) si le ticker est dans la watchlist.

### §3.2 — Mode 2 : « La Pièce » (le mode hasard)

Une pièce truquée **en ta faveur**, et qui te ruine quand même.

- Règle : à chaque lancer, tu choisis la **fraction `f`** de ton capital que tu engages.
  Pile → cette fraction fait **+50 %**. Face → elle fait **−40 %**. Pièce équilibrée.
- L'espérance est **positive** (+5 % par lancer sur la fraction engagée) ; la **médiane** est
  ruineuse : à `f = 100 %`, la croissance géométrique vaut √(1,5 × 0,6) − 1 ≈ **−5,1 % par
  lancer**. Le maximum de croissance long terme est atteint à **`f* = 25 %`** (calcul de
  Kelly : `0,25/(1+0,5f) = 0,20/(1−0,4f)` ⟹ `f = 0,25`). **Ces trois nombres doivent apparaître
  dans le débriefing du mode, démontrés, pas assénés.**
- **100 lancers.** Pendant que le joueur joue, **1 000 joueurs fantômes** jouent la même
  fraction en parallèle, dessinés en nuage translucide derrière sa courbe. On voit en direct
  la **moyenne** du nuage monter pendant que sa **médiane** s'effondre. C'est la leçon
  centrale — moyenne d'ensemble ≠ moyenne temporelle — et elle se voit, elle ne se lit pas.
- Écran de ruine (capital < 1 % du départ) : sobre, factuel, sans humour. Il dit combien de
  lancers ont suffi, et rappelle que la pièce était favorable.
- Lien explicite vers `apprendre.html` (sections risque / base rates).

### §3.3 — Mode 3 : « Le Miroir » (le rapport, pas un mode jouable)

Agrège **les parties du joueur** (stockées en `localStorage`, cf. §7.5) et lui renvoie son
propre portrait, avec le vocabulaire exact de `.claude/skills/portfolio-analyst/biases.md` et
du champ `biais_detectes` de `portfolio.json` :

| Mesuré | Biais nommé si… |
|---|---|
| durée moyenne de détention des gagnants ÷ celle des perdants | ratio < 1 → **effet de disposition** |
| nombre de gestes par partie, croisé avec la performance nette | gestes ↑ et perf ↓ → **sur-trading** (chiffrer les frais) |
| part des hausses d'exposition qui suivent 3 semaines de hausse | > 60 % → **chasse au momentum** |
| part des liquidations totales après une baisse hebdo > 8 % | > 50 % → **vente de panique** |
| taux de survie et perte maximale en mode Pièce | — → **risque de ruine mal dimensionné** |

Un biais n'est **jamais** nommé sous 5 parties : le dire sur 2 parties, c'est du bruit
présenté comme un diagnostic — exactement ce que le projet reproche par ailleurs.
Affiche le compteur : « 3 parties sur 5 avant le premier diagnostic ».

### §3.4 — Le Défi du jour

- Graine = la date du jour (UTC) → **tout le monde joue la même série**, sans backend.
- **Une partie par jour** en mode défi (le mode libre reste illimité : la limite est là pour
  que le défi veuille dire quelque chose, pas pour créer un rendez-vous compulsif).
- Résultat **partageable en texte** (presse-papier), sans image, sans lien de tracking :

```
Signal · La Table — Défi du 12/08
S1 ▁▂▃▅▇▇▅▃  net +4,2 %   ne rien faire +11,8 %
▲▬▬▼▲▬▬▬  6 gestes · 34 € de frais
```

---

## §4 — L'interface singulière : **le ruban**

C'est la partie que tu ne dois pas rendre générique. Signal n'a pas besoin d'un dashboard de
plus : la page entière est **un seul objet**, un ruban horizontal, et tout se joue dessus.

**Le ruban**
- Une bande pleine largeur, ~50 vh, fond sombre, **rayures de balayage** héritées de `.scan`.
- Le prix **arrive par la droite**, une semaine par tic, et le ruban **défile vers la gauche**,
  comme un sismographe. Fenêtre glissante de ~60 semaines ; ce qui sort à gauche est perdu de
  vue (c'est voulu : le joueur doit décider avec ce qu'il voit, pas relire l'historique).
- **Deux traces sur la même bande** : le prix (trait fin, `--text2`) et **la valeur du
  portefeuille du joueur** (trait `--ac`, avec la lueur du design system). Elles partent du même
  point : l'écart entre les deux EST le jeu.
- L'**exposition** est une aire ombrée sous la trace du joueur — 0 % : rien ; 100 % : pleine.
  Le joueur voit son engagement, il n'a pas à s'en souvenir.
- Au bord droit, un **curseur vertical** avec la pastille clignotante du design system
  (`.ring .rl::before`).
- Sous le ruban, **une seule ligne de console** en `--mono`, factuelle, mise à jour à chaque
  tic : `S+42 · exposition 50 % · frais payés 3,20 € · latent +4,1 %`.
- **Aucune fenêtre modale pendant la partie.** Rien ne recouvre le ruban.

**Les gestes**
- Clavier d'abord : `A` monter d'un cran · `V` descendre d'un cran · `0` tout vendre ·
  `4` tout acheter · `Espace` pause/reprise · `→` avancer d'une semaine en pause · `R` rejouer.
- Tactile : trois grandes cibles sous le ruban (`−`, `pause`, `+`) d'au moins **44 × 44 px**,
  plus un glissement vertical sur le ruban pour changer l'exposition.
- Défilement automatique à **1,2 s par semaine** par défaut, mise en pause instantanée.
  Le rythme fait la tension : ne le remplace pas par un bouton « suivant » à cliquer 104 fois.

**La révélation** (au lieu d'un écran de résultats classique)
- **Le ruban se rembobine** en accéléré vers la gauche, puis **se déroule en entier**, compressé
  pour tenir à l'écran ; **tes gestes apparaissent en place**, annotés (`▲ +25 %`, `▼ tout`),
  avec le prix auquel ils sont partis. Le nom du titre s'écrit alors en haut, en `--serif`.
- Les chiffres du §3.1 s'empilent **sous** le ruban, dans les composants existants
  (`.metrics`, `.meter`, `.ring`) — c'est là que la page redevient du Signal pur.

**`prefers-reduced-motion`** : pas de défilement animé (le ruban avance par pas discrets), pas
de pulsation de lueur, pas de rembobinage — la révélation s'affiche d'un coup. `signal-fx.js`
respecte déjà ce réglage : fais pareil, ce n'est pas négociable.

---

## §5 — Contraintes techniques dures

1. **Site statique, zéro backend, zéro build.** HTML + CSS + JavaScript classique (pas de
   modules ES imposés, pas de bundler, pas de framework, pas de TypeScript).
2. **Aucune dépendance externe au runtime.** Pas de CDN, pas de bibliothèque de graphes.
   Seule exception, déjà en place sur les quatre onglets : la police Inter de Google Fonts,
   avec **exactement la même requête** que les autres pages (un test le vérifie).
3. **Le rendu est fait main** en `<canvas>` (le ruban défile : c'est le bon outil) ou en SVG.
   `signal-fx.js` montre le niveau de canvas attendu dans ce dépôt.
4. **Budget de poids** : la page doit être jouable après avoir téléchargé **moins de 150 Ko**
   de données. Donc : **ne charge jamais** `analyses.json` (956 Ko), ni `watchlist.json`
   (220 Ko), ni tout `charts/` (3,9 Mo). Tu charges **un manifeste léger** (§6) puis
   **un seul** `charts/<TICKER>.json` par partie, à la demande — c'est déjà le motif d'`index.html`.
5. **Deux fichiers de code**, pas un :
   - `jeu-moteur.js` — **logique pure, zéro DOM, zéro `fetch`** : tirage, exécution des ordres,
     frais, impôt, statistiques, détection de biais, format de partage. Se termine par
     `if (typeof module !== 'undefined') module.exports = JEU;` pour être **testable sous node**.
   - `jeu.html` — le gabarit + le script inline de rendu et d'entrées.
   Cette séparation n'est pas cosmétique : elle est ce qui rend §11 possible.
6. **Pas de fuite du futur.** La boucle de rendu ne doit **jamais** avoir accès au tableau
   complet de la série. Le moteur expose une fonction qui **consomme** la série et ne rend que
   la tranche `[0, i]` ; le rendu ne reçoit que cette tranche. Un test l'éprouve pour de vrai (§11).
7. **Compatibilité** : navigateurs à jour, mobile inclus. Pas de `Date.now()` dans les calculs
   de partie autre que la graine (§7.4) — sinon une partie n'est plus reproductible.

---

## §6 — Contrat de données

### Ce qui existe déjà

`charts/<TICKER>.json` (150 fichiers) contient, entre autres :

```jsonc
{
  "points": [[23988.97, 0.0362], ...],   // [abscisse, cours de clôture AJUSTÉ]
  "mm21": [...], "mm200": [...],
  "fonda": { "devise": "USD", "an": [...], "tr": [...] },
  "breakdown": { ... }
}
```

**Trois pièges, tous documentés dans `screener.py` (~l.362) — relis-le :**
- L'abscisse est un **mois flottant** : `année × 12 + (mois − 1) + (jour − 1)/31`.
  Donc `24319.32` ≈ août 2026. Convertis-la, ne l'invente pas.
- L'échantillonnage est **mixte** : **hebdomadaire** sur les 730 derniers jours,
  **mensuel** au-delà. Le mode Rideau se joue à la semaine → **n'utilise que le segment
  hebdomadaire**, détecté par l'écart d'abscisse (≈ 0,23 entre deux points hebdo, ≈ 1,0 entre
  deux points mensuels). Ne suppose jamais un pas régulier sur toute la série.
- Les cours sont **ajustés** (splits, dividendes) et arrondis à 3 chiffres significatifs sous 1.
  Rebaser à 100 règle le problème d'affichage ; ne le règle pas en multipliant par 1 000.

⚠️ **Le segment hebdomadaire ne fait que ~104 points.** Une partie de 104 semaines consomme
donc toute la fenêtre récente, et toutes les parties se ressemblent. **Décision par défaut à
appliquer :** partie de **52 semaines** tirée dans le segment hebdomadaire, et **le mode « Long
Rideau » (104 semaines) se joue sur le segment mensuel** (donc 104 mois ≈ 8 ans, un tic = un
mois). Le libellé de l'axe suit (`S+n` ou `M+n`). Si tu trouves mieux, dis-le avant de coder.

### Ce que tu ajoutes : `jeu/index.json`

Un manifeste **minuscule** (< 15 Ko), produit par `tools/jeu_index.py`, contenant seulement ce
qu'il faut pour tirer une partie et révéler l'identité à la fin :

```json
{
  "updated_at": "2026-08-12",
  "series": [
    {"t": "NVDA", "n": "NVIDIA", "s": "Semiconducteurs", "h": 104, "m": 312, "d": "USD"}
  ]
}
```

`h` = points hebdo disponibles, `m` = points mensuels. **N'entrent que les titres** avec
`h ≥ 60` (mode court) ou `m ≥ 130` (mode long). Le script :
- lit `charts/*.json` et `watchlist.json` / `universe.json` pour les noms et secteurs ;
- écrit **atomiquement** (motif `save_json_atomic`, `allow_nan=False` — voir `screener.py`) ;
- **purge les orphelins** : un titre disparu de `charts/` sort du manifeste (même garde que la
  purge de `charts/`) ;
- est branché dans `.github/workflows/watchlist.yml`, **après** le screener, avant le commit.

---

## §7 — Règles de simulation (le cœur, à tester)

### §7.1 — Exécution
- Un changement d'exposition s'exécute **au cours de clôture de la semaine affichée**, jamais
  à celui de la suivante, jamais à un cours intra-semaine (on ne l'a pas). Écris-le en
  commentaire : c'est une hypothèse favorable au joueur, elle doit être assumée, pas cachée.
- **Frais** : `montant_échangé × 7,5 / 10000`, à l'achat **et** à la vente séparément.
- Ordre **refusé** si le montant échangé < 50 € (`MIN_TRADE_EUR`) — avec un retour visible
  dans la ligne de console, sinon le joueur croit que le jeu a raté son geste.
- Pas de vente à découvert, pas de levier, pas de position fractionnée par titre : **une seule
  ligne**, celle de la série jouée. Le jeu porte sur la décision d'exposition, pas sur
  l'allocation.

### §7.2 — Impôt
- **PFU de 31,4 %** sur la plus-value nette réalisée, appliqué **à la liquidation finale**.
- ⚠️ **Piège connu du dépôt : le `README.md` dit encore « PFU 30 % », `config.py` dit 31,4 %.**
  `config.py` a raison (`PFU_RATE = 0.314`, LFSS 2026, vérifié le 08/08/2026). **La source de
  vérité est `config.py`, jamais le README.** Profites-en pour corriger le README (§13).
- Les moins-values de la partie s'imputent sur les plus-values de la **même partie**, jamais
  d'une partie à l'autre.

### §7.3 — Les repères imposés à l'écran
Toute partie affiche, au même endroit et au même format : **ta performance nette**,
**l'achat-conservation** sur la même fenêtre, **le cash**. Les trois, toujours, y compris quand
le joueur gagne. C'est la promesse pédagogique du jeu ; ce n'est pas une option d'affichage.

### §7.4 — Hasard reproductible
- **Générateur pseudo-aléatoire à graine, écrit à la main** (mulberry32 ou xorshift32, ~5
  lignes). `Math.random()` est **interdit** dans le moteur : une partie doit se rejouer à
  l'identique à partir de sa graine.
- Graine du **défi du jour** = hachage de la date UTC `AAAA-MM-JJ` (fonction de hachage
  déterministe, écrite dans le moteur, testée).
- Graine d'une partie libre = aléatoire, mais **écrite dans l'URL** : `jeu.html#/p/<graine>`.
  Ouvrir ce lien rejoue exactement la même partie. C'est le partage, sans backend.
- Le tirage doit couvrir **le titre ET la fenêtre de départ** : deux parties de graines
  différentes sur le même titre ne doivent pas commencer au même endroit.

### §7.5 — Persistance
- `localStorage`, une seule clé : `signal.table.v1`, un objet **versionné** (`{v:1, parties:[…]}`)
  avec migration silencieuse si `v` change plus tard.
- **Plafond de 200 parties** conservées (les plus anciennes tombent) — sinon la clé grossit
  sans fin.
- Une partie stockée = graine, mode, date, gestes, performance nette/brute, frais, impôt,
  repères. **Pas de données personnelles**, jamais rien envoyé nulle part.
- **Toute lecture de `localStorage` est enveloppée dans un `try/catch`** : en navigation privée
  Safari, un `setItem` peut lever, et le jeu doit rester jouable sans mémoire.
- Un bouton **« effacer mon historique »**, visible, dans Le Miroir.

---

## §8 — Design system : ce que tu réutilises, ce que tu n'as pas le droit de redéfinir

**Tu réutilises tel quel** (`signal.css` est déjà chargé) : `.card`, `.sec` / `.sec-h`,
`.eyebrow`, `.tag`, `.metrics`, `.meter`, `.ring`, `.gauge`, `.bar-track` / `.bar-fill`,
`.sep`, `.pos` / `.neg` / `.neu`, `.type-cur`, les keyframes `blink` / `rise` / `ringglow`.

**Grammaire de couleur — la règle la plus facile à violer sans s'en rendre compte :**
- `--ac` (#74b6df, cyan) est **le seul accent**. Tout ce qui est interactif, actif, sélectionné,
  en cours : cyan.
- `--green` et `--red` sont **réservés au P&L factuel chiffré**. Interdits pour : un bouton
  d'achat, un bouton de vente, une pastille de mode, un état de victoire, un fond de gain, une
  trace de graphe. Un bouton « acheter » vert serait la faute la plus visible de toute la
  livraison.
- `--gold` : le badge « fictif » et lui seul.
- **Aucune information ne passe par la couleur seule** (le dépôt le dit noir sur blanc à propos
  des pastilles d'Actualités : « la flèche est REDONDANTE avec la couleur, et c'est voulu »).
  Une hausse porte un signe et/ou une flèche, pas seulement une teinte.

**Tu ne redéfinis JAMAIS** dans `jeu.html` les sélecteurs nus du chrome partagé —
`.brand`, `.brand-name`, `.brand-icon`, `nav`, `nav a`, `nav a svg`, `.footer-legal`,
`.footer-right`. **`tests/test_chrome.py` fait échouer la CI si tu le fais.**
`header { position: … }` reste permis (ta page défile → `sticky`, avec `html,body{height:auto}`,
comme `actualites.html` — recopie ce motif **en entier**, pas à moitié : c'est un bug déjà
survenu et documenté dans le CSS).

---

## §9 — Accessibilité et mobile

- **Jouable au clavier de bout en bout**, sans souris. Focus visible sur tous les contrôles.
- Le ruban est un `<canvas>` **décoratif du point de vue de l'assistance** (`aria-hidden`) :
  l'état du jeu est porté en parallèle par un `aria-live="polite"` **discret et poli** — il
  annonce le résultat des gestes du joueur, **pas chaque semaine qui passe** (sinon un lecteur
  d'écran parle en continu pendant deux minutes).
- Cibles tactiles ≥ 44 px. Aucun geste indispensable qui n'ait pas d'équivalent bouton.
- `prefers-reduced-motion` : cf. §4.
- La page doit rester lisible et jouable à **360 px de large**. Le ruban se réduit en hauteur,
  il ne se replie pas en tableau.
- Contraste : le texte de la console sur le ruban doit tenir le **4,5:1**. Vérifie, ne suppose pas.

---

## §10 — Le cinquième onglet : la checklist exacte

C'est ici qu'on casse des choses sans le voir. `tests/test_chrome.py` compare **les quatre
onglets entre eux** ; en ajouter un cinquième touche **tous** les fichiers ci-dessous.

1. **`jeu.html`** — nouvelle page. Doit porter, sous peine d'échec CI :
   `rel="icon"` (le favicon en data-URI, **identique** aux autres) · `name="description"` ·
   la **même** requête `fonts.googleapis.com/css2?family=Inter…` · `signal.css` ·
   `signal-fx.js` · `.footer-legal` avec la mention AMF **au mot près** · `.footer-right`.
   Plus le décor : `#fx`, `<canvas id="bg">`, `.scan`, `.frame` (les quatre `<i>`).
2. **La nav, dans les CINQ pages** — même ordre, mêmes libellés partout, et
   **« Portefeuille IA » doit rester la dernière entrée** (un test l'exige nommément).
   Ordre cible :
   `Watchlists · Actualités · Apprendre · La Table · Portefeuille IA`
   Le lien : `<a href="jeu.html">`, avec un `<svg viewBox="0 0 24 24" aria-hidden="true">` en
   **tracé** (`stroke:currentColor`, jamais de `fill`) et le libellé dans un `<span>` — sinon le
   test de nav ne le trouve pas et l'icône ne prend pas la couleur de l'onglet actif.
   *Suggestion de glyphe : un jeton — cercle, cercle intérieur, quatre encoches. Lisible à 19 px,
   et il dit « table de jeu » sans dire « casino ».*
3. **`tests/test_chrome.py`** — ajouter `"jeu.html"` à `PAGES`, et **corriger les libellés qui
   disent « les 4 onglets »**. Les contrôles spécifiques à `index.html` (`.home-h`, `top:5.6rem`,
   `FD_RUPTURE`, colonne de repos) restent tels quels : ils ne concernent pas ta page.
4. **`README.md`** — bloc « Architecture » (la page, `jeu-moteur.js`, `jeu/index.json`,
   `tools/jeu_index.py`), « Fichiers clés », et la correction du PFU (§7.2).
5. **`.github/workflows/watchlist.yml`** — appel de `tools/jeu_index.py` et `git add jeu/`.
6. **`CHANGELOG.md`** — une entrée en tête (§13).

---

## §11 — Tests : ce qu'il faut écrire, et comment le projet les écrit

**Les tests de ce dépôt tournent HORS LIGNE, sans aucune dépendance installée**, sur chaque
poussée (`.github/workflows/tests.yml`). Le style de la maison, à respecter :
- un fichier `tests/test_jeu.py`, exécutable seul (`python tests/test_jeu.py`) ;
- un **docstring qui explique POURQUOI le fichier existe** — pas ce qu'il fait, pourquoi ;
- la fonction `check(nom, cond, detail)`, les `✅` / `❌`, le décompte final et
  `sys.exit(1)` si rouge ;
- **avant de croire un « tout est vert » local** : `PYTHONPATH=tests python3 tests/test_jeu.py`
  (cf. `tests/_sans_bibliotheques.py`).

**Le moteur se teste POUR DE VRAI, sous node** — c'est le motif déjà utilisé par
`test_chrome.py`, `test_charts.py` et `test_actualites.py` : on exécute le code livré, on ne le
relit pas. Et comme eux, **si node manque, on l'écrit** (`⚠️ non vérifié (node indisponible)`),
on ne fait pas semblant.

Propriétés à éprouver, au minimum :

| # | Propriété | Pourquoi elle compte |
|---|---|---|
| 1 | **Reproductibilité** : même graine ⟹ même titre, même fenêtre, même suite de tirages | c'est ce qui rend le défi du jour et le partage d'URL possibles |
| 2 | **Aucun `Math.random()`** dans `jeu-moteur.js` | une seule occurrence casse (1) en silence |
| 3 | **Frais** : un aller-retour de 1 000 € coûte 1,50 € (15 bps), au centime | la promesse d'honnêteté du jeu |
| 4 | **Le taux de frais et le PFU du JS égalent ceux de `config.py`** — parsés des deux fichiers et comparés | motif `FD_RUPTURE` de `test_chrome.py` : un doublon dérive toujours |
| 5 | **PFU** : moins-value ⟹ impôt nul ; plus-value de 1 000 € ⟹ 314 € | idem |
| 6 | **Ordre < 50 € refusé**, et l'exposition n'a pas bougé | un refus muet ferait croire à un bug |
| 7 | **Pas de fuite du futur** : sur une série marquée, la tranche rendue au tic `i` ne contient aucun point > `i` | le mode entier perd son sens si le futur transpire |
| 8 | **Buy & hold** recalculé indépendamment en Python ⟹ même résultat que le JS | le repère doit être juste, c'est le juge de la partie |
| 9 | **Détection de biais** : jeux de gestes fabriqués ⟹ biais attendu ; et **aucun biais nommé sous 5 parties** | ne pas diagnostiquer du bruit |
| 10 | **Pièce** : sur 10 000 lancers à graine fixe, moyenne > capital initial **et** médiane < capital initial | c'est la leçon du mode ; si elle ne tient pas, la démo ment |
| 11 | **Manifeste** : tout ticker de `jeu/index.json` a un `charts/<T>.json`, et aucun orphelin | même garde que la purge de `charts/` |
| 12 | **Segment hebdo/mensuel** correctement séparé sur des séries fabriquées (pas régulières) | le piège n°2 du §6 |
| 13 | **Le script inline de `jeu.html` se parse** (`node --check`) | une erreur de syntaxe a déjà mis le site entier en panne (09/08/2026) |
| 14 | **Format de partage** stable et sans donnée personnelle | ce qui part au presse-papier est public |

---

## §12 — Textes et pédagogie

- **Langue : français.** Ton du projet : précis, factuel, posé, une pointe d'esprit
  pince-sans-rire **occasionnelle**, jamais de hype, jamais de reco déguisée
  (cf. `GUIDE_redaction_analyses.md`).
- **Chaque mode ouvre sur trois lignes maximum** : ce qu'on fait, comment on joue, ce qu'on
  apprend. Personne ne lit le quatrième paragraphe d'un jeu.
- **Le débriefing enseigne un point, un seul**, choisi selon ce qui s'est passé dans LA partie
  jouée : coût des frais · effet de disposition · chasse au momentum · risque de ruine ·
  « ne rien faire était mieux ». Renvoie vers la section correspondante d'`apprendre.html`
  (ancres `#s1`…`#s12`) — **vérifie l'ancre, ne la devine pas**.
- **Ce qu'on n'écrit jamais** : « bien joué, tu as du flair », un score de compétence, une
  projection en euros réels, « avec cette stratégie tu aurais gagné X € ».
- **Ce qu'on écrit à la place, quand le joueur gagne** : de combien il a battu l'achat-conservation,
  et sur combien de parties ce résultat tiendrait du hasard.
- **Le badge « fictif »** (`--gold`) est visible en permanence, et la page reprend la formule
  éprouvée de `portfolio.html` : *« Capital 100 % fictif. Aucune somme réelle investie. Prix
  réels du marché. »*

---

## §13 — Livrables

```
jeu.html                    la page (gabarit + rendu + entrées)
jeu-moteur.js               logique pure, testable sous node, zéro DOM
jeu/index.json              manifeste des séries jouables (généré, committé)
tools/jeu_index.py          le générateur, atomique, avec purge des orphelins
tests/test_jeu.py           la suite (§11)
index.html                  + 5ᵉ entrée de nav
actualites.html             + 5ᵉ entrée de nav
apprendre.html              + 5ᵉ entrée de nav
portfolio.html              + 5ᵉ entrée de nav
tests/test_chrome.py        PAGES + libellés
.github/workflows/watchlist.yml   génération du manifeste
README.md                   architecture, fichiers clés, correction du PFU
CHANGELOG.md                l'entrée
```

**Commits** : français, préfixés à la manière du dépôt (`feat(jeu): …`, `fix(chrome): …`),
**une phrase qui dit ce qui change pour le lecteur**, pas ce que fait le code.
Regarde `git log --oneline -20` : le style y est sans ambiguïté.

**CHANGELOG** : une entrée en tête, titrée comme les autres — une phrase qui **raconte le
problème ou la décision**, pas « ajout du jeu ». Ce dépôt écrit ses entrées comme des constats
(« Le maillon mémoire décrivait un oligopole en oubliant un de ses membres ») : tiens ce niveau.

**Branche** : `claude/signal-investment-game-prompt-rvkkyo` — développe, commit, pousse
(`git push -u origin …`). **N'ouvre pas de pull request** sauf demande explicite.

---

## §14 — Définition du « terminé »

- [ ] `python tests/test_jeu.py` : vert, et **`PYTHONPATH=tests python3 tests/test_jeu.py`
      aussi** (le runner n'a aucune bibliothèque tierce).
- [ ] `for f in tests/test_*.py; do python $f; done` : **toutes** les suites vertes, y
      compris `test_chrome.py` après l'ajout du cinquième onglet.
- [ ] La nav est identique sur les cinq pages, « Portefeuille IA » toujours en dernier, et
      le bandeau ne change pas de hauteur d'un onglet à l'autre.
- [ ] Une partie complète se joue **au clavier seul**, et une autre **au doigt seul** à 360 px.
- [ ] `prefers-reduced-motion` activé : la page reste jouable et n'anime rien.
- [ ] Recharger `jeu.html#/p/<graine>` rejoue **exactement** la même partie.
- [ ] Aucun `--green` / `--red` ailleurs que sur un chiffre de P&L. Relis ton CSS pour ça.
- [ ] Poids des données téléchargées pour une partie : **< 150 Ko**, mesuré, pas estimé.
- [ ] Le README décrit le jeu et **le PFU y est à 31,4 %**.
- [ ] Aucune donnée ne quitte le navigateur. Aucun appel réseau autre que `jeu/index.json`,
      `charts/<T>.json` et la police.

---

## §15 — Hors périmètre, et décisions à confirmer

**Hors périmètre** (ne le fais pas, même si c'est tentant) : classement en ligne · comptes
utilisateurs · multijoueur · portefeuille multi-titres · vente à découvert et levier ·
génération d'images de partage · intégration au portefeuille IA réel · notifications ·
sons (aucun son : le site est lu au bureau).

**Décisions à confirmer avant de coder** — propose ces valeurs par défaut, applique-les si on
ne te répond pas, et **écris dans ta livraison ce que tu as tranché** :

| # | Question | Défaut proposé |
|---|---|---|
| 1 | Libellé de l'onglet : « La Table » (singulier, un peu cryptique) ou « Simulateur » (clair, plat) ? | **La Table**, avec un chapô qui l'explique dès la première ligne |
| 2 | Durée d'une partie courte | **52 semaines** (cf. la contrainte du §6) |
| 3 | Livrer les trois modes d'un coup, ou par lots ? | **Trois lots** : ① Le Rideau + chrome + tests ② La Pièce ③ Le Miroir + défi du jour. Chaque lot est livrable et testé seul. |
| 4 | Capital fictif de départ | **10 000 €** — délibérément différent du capital du portefeuille IA, pour qu'on ne confonde jamais les deux |
| 5 | Le mode Pièce en `−40 %/+50 %` | oui — c'est la seule paramétrisation qui donne à la fois EV positive, ruine médiane et un `f*` propre à 25 % |

**Une dernière chose.** Si en cours de route tu découvres qu'une de ces contraintes rend le jeu
mauvais, **dis-le et argumente** au lieu de la contourner en silence. Ce dépôt documente ses
erreurs et ses angles morts dans son CHANGELOG ; un désaccord motivé y a plus de valeur qu'une
livraison qui fait semblant que tout allait de soi.
