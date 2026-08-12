/* maison-moteur.js — La Maison : LA SIMULATION ENTIÈRE, ET RIEN QU'ELLE.
   ============================================================================
   Zéro DOM, zéro fetch, zéro horloge murale : ce fichier tourne à l'identique
   dans la page et sous node (les tests le rejouent pour de vrai, ils ne le
   relisent pas). Tout le hasard passe par un générateur à graine — même graine
   + mêmes décisions = même partie au centime, et c'est ce qui rend possibles
   la sauvegarde, le partage d'URL et l'audit du lot ④.

   Périmètre : MVP (lot ①, cf. PROMPT_jeu_simulation.md §25). Les
   simplifications assumées sont marquées « ⚠ MVP » là où elles vivent.

   Unités : les montants sont en euros, les cours du pack en millièmes de la
   première cote (base 1000), le temps en JOURS OUVRÉS (20 = un mois). */
(function () {
  'use strict';

  var VERSION = 1;
  var CLE_SAUVEGARDE = 'signal.maison.v1';

  /* ── Constantes économiques ────────────────────────────────────────────
     Les deux premières RECOPIENT config.py (TRANSACTION_COST_BPS,
     MIN_TRADE_EUR) : test_maison.py parse les deux fichiers et compare —
     un doublon qui dérive fait échouer la CI, pas une lecture. */
  var FRAIS_EXEC_BPS = 7.5;          // avec gérant d'exécution (= config.py)
  var ORDRE_MIN_EUR = 50;            // en dessous, l'ordre est refusé (= config.py)
  var FRAIS_EXEC_SANS_GERANT_BPS = 30; // sans lui : exécution amateur
  var FRAIS_GESTION_PCT = 2.0;       // grille fixe en MVP (le choix arrive au lot ②)
  var RETRO_HOTE_PCT = 0.30;         // ⚠ MVP approximation, non vérifiée : part de
                                     // l'hôte qui porte l'agrément (mode hébergé)
  var LOYER_MOIS_EUR = 3600;         // 96 m² × 450 €/m²/an (1ʳᵉ couronne, §23)
  var JOURS_PAR_MOIS = 20;           // jours ouvrés
  var TRESO_DEPART_EUR = 500000;     // l'apport personnel du fondateur
  var COLLECTE_INITIALE_EUR = 3000000;
  var VL_INITIALE = 100;
  var IS_SOCIETE_PCT = 0.25;         // impôt sur le résultat de la société (annuel)

  /* Abonnement de données — niveaux réels (§23), au niveau société (⚠ MVP :
     par poste au lot ②). `notes` divise l'intervalle de production. */
  var ABONNEMENTS = {
    base: { prix: 280, label: 'Flux de base', facteur: 1 },
    lseg: { prix: 1700, label: 'LSEG Workspace', facteur: 1.35 },
    bloomberg: { prix: 2500, label: 'Terminal Bloomberg', facteur: 1.8 }
  };

  /* Rôles recrutables du MVP. `cout` = brut × 1,45 (charges patronales cadre,
     §23) arrondi — LES DEUX s'affichent, c'est le point pédagogique. */
  var ROLES = {
    analyste_junior: { label: 'Analyste junior', brut: 3800, cout: 5500, joursParNote: 20 },
    analyste: { label: 'Analyste confirmé', brut: 5500, cout: 8000, joursParNote: 8 },
    execution: { label: 'Gérant d’exécution', brut: 6500, cout: 9400, joursParNote: 0 }
  };
  var RAMPE_JOURS = 60;              // 3 mois avant la pleine productivité
  var PRIME_ARRIVEE_MOIS_BRUT = 1;   // prime d'arrivée = 1 mois de brut

  /* Meubles posables. Chaque type = 1 tuile (le MVP n'a pas de meuble large) ;
     la salle de réunion et le reste arrivent au lot ②. Revente à 50 %. */
  var MEUBLES = {
    poste: { label: 'Poste de travail', prix: 1200, recurrent: 0 },
    cafe: { label: 'Machine à café', prix: 400, recurrent: 60 },
    plante: { label: 'Plante', prix: 150, recurrent: 0 }
  };

  /* ── Noms masqués ──────────────────────────────────────────────────────
     LISTE FIXE, jamais un assemblage de syllabes : un générateur finirait par
     produire le nom d'une vraie société, à laquelle le jeu collerait alors
     des faits inventés (règle §2 ③). L'attribution nom↔ticker est un
     mélange déterministe par graine. */
  var NOMS_FICTIFS = [
    'Ardyne', 'Nordvale', 'Ligne Bleue', 'Kervalec', 'Ostrelane', 'Vireloup',
    'Maison Andrieu', 'Solferane', 'Brumaire & Cie', 'Ateliers Verlon',
    'Quercinor', 'Halvassen', 'Tramontane SA', 'Ferelith', 'Groupe Ombeline',
    'Vantorre', 'Escaldia', 'Mireval Industrie', 'Corvessant', 'Aubrelane',
    'Pellerose', 'Stromvik', 'Delverane', 'Ixoline', 'Cap Mordant',
    'Ganelor', 'Ystrelle', 'Fonderies Barvaux', 'Ouvelane', 'Torgane',
    'Sarrelune', 'Vindaire', 'Maison Quenard', 'Elverstad', 'Roncevault',
    'Bruyanne', 'Caldorive', 'Merengard', 'Sylvebourg', 'Antrevine',
    'Groupe Falberic', 'Odessane', 'Luthomer', 'Warvellec', 'Pontverdier',
    'Iskavold', 'Chandrelle', 'Morvezen', 'Ateliers Rosnay', 'Talberine',
    'Ussandre', 'Grevalone', 'Herbeline', 'Comptoirs Malzieu', 'Norrfelt',
    'Vaucrelan', 'Estangard', 'Pierjolane', 'Kolvestre', 'Amberieu & Fils',
    'Drovelane', 'Cisterval', 'Maubrelin', 'Orvasson', 'Quintarelle',
    'Fjellmark', 'Sabreloup', 'Vernissac', 'Haldergrun', 'Trescandie',
    'Blanchefort SA', 'Ruthavel', 'Gomessane', 'Ylverton', 'Passemarine',
    'Corbelune', 'Manufacture Ardaux', 'Sellivane', 'Thorbecke & Cie',
    'Ivrelonde', 'Waldemine', 'Fressanges', 'Ocreville', 'Lumescande',
    'Barvolane', 'Nestergaard', 'Prunavel', 'Skardheim', 'Verdolier',
    'Maison Cathelan'
  ];
  var PRENOMS = ['Anna', 'Bastien', 'Chloé', 'David', 'Elsa', 'Farid', 'Gaëlle',
    'Hugo', 'Inès', 'Jonas', 'Karim', 'Léa', 'Marc', 'Nadia', 'Oscar', 'Priya',
    'Quentin', 'Rita', 'Samuel', 'Théa', 'Ulysse', 'Véra', 'William', 'Yasmine'];
  var NOM_HOTE = 'Carmine & Associés'; // la société de gestion qui nous héberge (fictive)

  /* ── Hasard reproductible ──────────────────────────────────────────────
     mulberry32 : 5 lignes, une graine 32 bits, état sérialisable. Interdit
     d'appeler Math.random() où que ce soit ici — un test le grep. */
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return { etat: a, valeur: ((t ^ t >>> 14) >>> 0) / 4294967296 };
    };
  }
  function tirer(state) {
    var r = mulberry32(state.rng)();
    state.rng = r.etat;
    return r.valeur;
  }
  function tirerEntier(state, n) { return Math.floor(tirer(state) * n); }

  /* Hachage de chaîne → graine 32 bits (FNV-1a). Sert aux graines d'URL. */
  function hash(str) {
    var h = 0x811c9dc5;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    return h >>> 0;
  }

  /* ── Marché ────────────────────────────────────────────────────────────
     L'état ne stocke JAMAIS la matrice de prix : il porte un index de mois,
     et toute lecture passe par prixTitre(), qui refuse le futur. Le test
     anti-fuite empoisonne les mois au-delà de l'index et vérifie que rien
     ne change. */
  function packMoisCourant(state) { return state.marcheDepart + state.mois; }

  function prixTitre(state, pack, ticker, moisSim) {
    if (moisSim === undefined) moisSim = state.mois;
    if (moisSim > state.mois) { throw new Error('lecture du futur : ' + ticker); }
    var t = pack.parTicker[ticker];
    if (!t) return null;
    var m = state.marcheDepart + moisSim - t.i0;
    if (m < 0) return null;              // pas encore coté à cette date
    if (m < t.px.length) return t.px[m];
    /* ⚠ MVP : au-delà des 240 mois réels, REBOUCLAGE des rendements depuis le
       début de la série (continuité de prix assurée : on enchaîne des ratios,
       jamais des niveaux). Provisoire — le block bootstrap honnête est au
       lot ④, et le carnet le dira au joueur le moment venu. */
    var n = t.px.length;
    var p = t.px[n - 1];
    for (var k = n; k <= m; k++) {
      var i = ((k - 1) % (n - 1)) + 1;   // rejoue les rendements 1..n-1 en boucle
      p = p * (t.px[i] / t.px[i - 1]);
    }
    return p;
  }

  /* Faits de prix pour les thèses — même garde anti-futur que prixTitre.
     RÈGLE §2 ③ : une thèse ne cite QUE des faits de cours. Jamais une marge,
     un carnet de commandes, une actualité : les cours sont réels, inventer un
     fait reviendrait à l'attribuer plus tard à une société réelle.

     Le recul se prend sur le PACK, pas sur l'horloge de la partie : la
     simulation démarre au moins 24 mois après t0 (marcheDepart), donc un
     moisSim NÉGATIF est un cours d'avant la fondation — parfaitement
     licite à regarder. Sans ça, les analystes de la première année
     n'avaient « pas d'historique » et ne proposaient rien : un an de jeu
     muet, constaté à la première partie jouée au navigateur. */
  function faitsPrix(state, pack, ticker) {
    var p0 = prixTitre(state, pack, ticker);
    if (p0 === null) return null;
    function perf(mois) {
      var p = prixTitre(state, pack, ticker, state.mois - mois);
      return p === null ? null : (p0 / p - 1) * 100;
    }
    var haut = 0;
    for (var k = state.mois - 60; k <= state.mois; k++) {
      var p = prixTitre(state, pack, ticker, k);
      if (p !== null && p > haut) haut = p;
    }
    return {
      p3m: perf(3), p12m: perf(12),
      sousHaut5a: haut > 0 ? (p0 / haut - 1) * 100 : null
    };
  }

  function indexerPack(pack) {
    if (!pack.parTicker) {
      pack.parTicker = {};
      for (var i = 0; i < pack.titres.length; i++) {
        pack.parTicker[pack.titres[i].t] = pack.titres[i];
      }
    }
    return pack;
  }

  /* ── Plateau : pose, retrait, connexité ────────────────────────────────
     La règle qui fait la boucle du jeu : trésorerie → poste posé → recrutement.
     Un meuble ne peut pas enfermer un poste (ni la porte) : on vérifie par
     BFS AVANT d'accepter la pose — refuser après coup serait un piège. */
  function tuileLibre(plateau, x, y) {
    if (x < 0 || y < 0 || x >= plateau.w || y >= plateau.h) return false;
    for (var i = 0; i < plateau.meubles.length; i++) {
      if (plateau.meubles[i].x === x && plateau.meubles[i].y === y) return false;
    }
    return true;
  }
  function connexiteOk(plateau) {
    /* BFS depuis la porte sur les tuiles libres ; chaque meuble « cible »
       (poste, café) doit avoir AU MOINS un voisin libre atteint. */
    var libres = {}, file = [], vus = {};
    var cle = function (x, y) { return x + ',' + y; };
    if (!tuileLibre(plateau, plateau.porte.x, plateau.porte.y)) return false;
    file.push([plateau.porte.x, plateau.porte.y]);
    vus[cle(plateau.porte.x, plateau.porte.y)] = true;
    while (file.length) {
      var c = file.shift();
      libres[cle(c[0], c[1])] = true;
      var voisins = [[1, 0], [-1, 0], [0, 1], [0, -1]];
      for (var v = 0; v < 4; v++) {
        var nx = c[0] + voisins[v][0], ny = c[1] + voisins[v][1];
        if (!vus[cle(nx, ny)] && tuileLibre(plateau, nx, ny)) {
          vus[cle(nx, ny)] = true;
          file.push([nx, ny]);
        }
      }
    }
    for (var m = 0; m < plateau.meubles.length; m++) {
      var mb = plateau.meubles[m];
      if (mb.type !== 'poste' && mb.type !== 'cafe' && mb.type !== 'fondateur') continue;
      var ok = false;
      var autour = [[1, 0], [-1, 0], [0, 1], [0, -1]];
      for (var a = 0; a < 4; a++) {
        if (libres[cle(mb.x + autour[a][0], mb.y + autour[a][1])]) { ok = true; break; }
      }
      if (!ok) return false;
    }
    return true;
  }

  function poserMeuble(state, type, x, y) {
    var def = MEUBLES[type];
    if (!def) return { ok: false, err: 'meuble inconnu' };
    if (state.societe.treso < def.prix) return { ok: false, err: 'trésorerie insuffisante' };
    if (!tuileLibre(state.plateau, x, y)) return { ok: false, err: 'tuile occupée' };
    var essai = {
      w: state.plateau.w, h: state.plateau.h, porte: state.plateau.porte,
      meubles: state.plateau.meubles.concat([{ id: state.plateau.prochainId, type: type, x: x, y: y }])
    };
    if (!connexiteOk(essai)) return { ok: false, err: 'la pose enfermerait un poste ou la porte' };
    state.plateau.meubles.push({ id: state.plateau.prochainId++, type: type, x: x, y: y });
    state.societe.treso -= def.prix;
    journal(state, def.label + ' installé (' + fmtEur(def.prix) + ').');
    return { ok: true };
  }

  function retirerMeuble(state, id) {
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      var m = state.plateau.meubles[i];
      if (m.id !== id) continue;
      if (m.type === 'fondateur') return { ok: false, err: 'ton bureau reste' };
      if (m.type === 'poste') {
        for (var e = 0; e < state.equipe.length; e++) {
          if (state.equipe[e].posteId === id) return { ok: false, err: 'quelqu’un y travaille' };
        }
      }
      state.plateau.meubles.splice(i, 1);
      var remb = Math.round(MEUBLES[m.type].prix * 0.5); // revente à 50 % (§5)
      state.societe.treso += remb;
      journal(state, MEUBLES[m.type].label + ' revendu (' + fmtEur(remb) + ').');
      return { ok: true, remboursement: remb };
    }
    return { ok: false, err: 'meuble introuvable' };
  }

  function postesLibres(state) {
    var libres = [];
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      var m = state.plateau.meubles[i];
      if (m.type !== 'poste') continue;
      var pris = false;
      for (var e = 0; e < state.equipe.length; e++) {
        if (state.equipe[e].posteId === m.id) { pris = true; break; }
      }
      if (!pris) libres.push(m);
    }
    return libres;
  }

  /* ── Équipe et recrutement ─────────────────────────────────────────────
     Pas de poste libre → pas de recrutement : c'est la chaîne du §5, et elle
     ne se contourne pas. Un mois de recherche, une prime d'arrivée, trois
     mois de rampe : embaucher n'est jamais un clic gratuit. */
  function lancerRecrutement(state, role) {
    if (!ROLES[role]) return { ok: false, err: 'rôle inconnu' };
    if (state.recrutement) return { ok: false, err: 'une recherche est déjà en cours' };
    if (!postesLibres(state).length) return { ok: false, err: 'aucun poste de travail libre' };
    state.recrutement = { role: role, joursRestants: JOURS_PAR_MOIS };
    journal(state, 'Recherche lancée : ' + ROLES[role].label + ' (un mois environ).');
    return { ok: true };
  }

  function presenterCandidat(state) {
    var role = state.recrutement.role;
    var def = ROLES[role];
    var nom = PRENOMS[tirerEntier(state, PRENOMS.length)];
    var competence = 2 + tirerEntier(state, 3);              // 2..4
    var brut = Math.round(def.brut * (0.95 + tirer(state) * 0.2) / 50) * 50;
    var cout = Math.round(brut * 1.45 / 50) * 50;            // charges patronales §23
    state.recrutement = null;
    pousserDialogue(state, {
      type: 'candidat', auteur: nom, role: role,
      texte: nom + ' se présente pour le poste de ' + def.label.toLowerCase() +
        '. Compétence estimée : ' + competence + '/5. Prétention : ' +
        fmtEur(brut) + ' brut/mois — soit ' + fmtEur(cout) +
        ' chargés, plus une prime d’arrivée d’un mois.',
      options: [
        { label: 'Embaucher', action: 'embaucher' },
        { label: 'Renoncer', action: 'renoncer' }
      ],
      meta: { nom: nom, role: role, competence: competence, brut: brut, cout: cout }
    });
  }

  function embaucher(state, meta) {
    var libre = postesLibres(state)[0];
    if (!libre) return { ok: false, err: 'plus de poste libre' };
    var prime = meta.brut * PRIME_ARRIVEE_MOIS_BRUT;
    if (state.societe.treso < prime) return { ok: false, err: 'pas de quoi payer la prime d’arrivée' };
    state.societe.treso -= prime;
    state.equipe.push({
      id: state.prochainPersoId++, nom: meta.nom, role: meta.role,
      competence: meta.competence, moral: 70, brut: meta.brut, cout: meta.cout,
      posteId: libre.id, arriveJour: state.jour, progression: 0,
      etat: 'entre', pos: { x: state.plateau.porte.x, y: state.plateau.porte.y },
      but: { x: libre.x, y: libre.y }
    });
    journal(state, meta.nom + ' rejoint la maison (' + ROLES[meta.role].label + ').');
    return { ok: true };
  }

  function aUnGerantExecution(state) {
    for (var i = 0; i < state.equipe.length; i++) {
      if (state.equipe[i].role === 'execution') return true;
    }
    return false;
  }

  /* ── Le fonds : VL, parts, ordres, frais ───────────────────────────────
     La VL est LA grandeur du jeu : (lignes + trésorerie du fonds) ÷ parts.
     Souscriptions et rachats passent par les parts À LA VL DU MOIS — jamais
     en diluant les porteurs existants (test 3). */
  function valeurLignes(state, pack) {
    var total = 0;
    for (var t in state.fonds.positions) {
      var pos = state.fonds.positions[t];
      var p = prixTitre(state, pack, t);
      if (p !== null) total += pos.qte * p;
    }
    return total;
  }
  function encours(state, pack) { return valeurLignes(state, pack) + state.fonds.cash; }
  function vl(state, pack) {
    return state.fonds.parts > 0 ? encours(state, pack) / state.fonds.parts : VL_INITIALE;
  }

  function souscrire(state, pack, montant) {
    var v = vl(state, pack);
    state.fonds.parts += montant / v;
    state.fonds.cash += montant;
  }
  function racheterParts(state, pack, montant) {
    var v = vl(state, pack);
    var m = Math.min(montant, encours(state, pack));
    /* ⚠ MVP : si le cash ne couvre pas, on vend au prorata — la vraie vente
       forcée (ordre de liquidité, trace VL) est la leçon du lot ②. */
    if (m > state.fonds.cash) {
      var manque = m - state.fonds.cash;
      var lignes = valeurLignes(state, pack);
      for (var t in state.fonds.positions) {
        var pos = state.fonds.positions[t];
        var p = prixTitre(state, pack, t);
        if (p === null) continue;
        var part = (pos.qte * p) / lignes;
        var aVendre = Math.min(pos.qte, (manque * part) / p);
        pos.qte -= aVendre;
        state.fonds.cash += aVendre * p;
        if (pos.qte < 1e-9) delete state.fonds.positions[t];
      }
      journal(state, 'Rachats supérieurs à la trésorerie du fonds : ventes au prorata.');
    }
    state.fonds.cash -= m;
    state.fonds.parts -= m / v;
    return m;
  }

  /* Un ordre : montant en € au cours du mois affiché (hypothèse assumée,
     favorable au joueur : on ne dispose que de clôtures mensuelles). Frais
     d'exécution 7,5 bps avec gérant, 30 sans — la différence EST le salaire. */
  function passerOrdre(state, pack, ticker, montant, sens) {
    if (Math.abs(montant) < ORDRE_MIN_EUR) {
      journal(state, 'Ordre refusé : ' + fmtEur(Math.abs(montant)) +
        ' < minimum de ' + fmtEur(ORDRE_MIN_EUR) + '.');
      return { ok: false, err: 'sous le minimum de ' + ORDRE_MIN_EUR + ' €' };
    }
    var p = prixTitre(state, pack, ticker);
    if (p === null) return { ok: false, err: 'titre non coté' };
    var bps = aUnGerantExecution(state) ? FRAIS_EXEC_BPS : FRAIS_EXEC_SANS_GERANT_BPS;
    var frais = Math.abs(montant) * bps / 10000;
    var pos = state.fonds.positions[ticker];
    if (sens === 'achat') {
      if (montant + frais > state.fonds.cash) return { ok: false, err: 'trésorerie du fonds insuffisante' };
      var qte = montant / p;
      if (!pos) pos = state.fonds.positions[ticker] = { qte: 0, pru: 0, moisEntree: state.mois };
      pos.pru = (pos.pru * pos.qte + montant) / (pos.qte + qte);
      pos.qte += qte;
      state.fonds.cash -= montant + frais;
    } else {
      if (!pos) return { ok: false, err: 'ligne inconnue' };
      var qteV = Math.min(pos.qte, montant / p);
      pos.qte -= qteV;
      state.fonds.cash += qteV * p - frais;
      if (pos.qte < 1e-9) {
        /* La ligne se solde : si on l'a portée plus d'un an, l'identité
           réelle se révèle (§12.4) — après coup, jamais pendant. */
        if (state.mois - pos.moisEntree >= 12) state.reveles[ticker] = true;
        delete state.fonds.positions[ticker];
      }
    }
    state.fonds.fraisTransaction += frais;
    state.stats.ordres++;
    return { ok: true, frais: frais, bps: bps };
  }

  /* ── Thèses : la seule famille d'arbitrage du MVP ──────────────────────
     Le texte ne cite QUE des faits de prix (règle §2 ③) ; l'avis de
     l'analyste est un avis, formulé comme tel. */
  function produireThese(state, pack, perso) {
    var tenus = Object.keys(state.fonds.positions);
    var sortie = tenus.length > 0 && tirer(state) < 0.35;
    if (sortie) {
      var ticker = tenus[tirerEntier(state, tenus.length)];
      var pos = state.fonds.positions[ticker];
      var p = prixTitre(state, pack, ticker);
      var pv = (p / pos.pru - 1) * 100;
      pousserDialogue(state, {
        type: 'these', auteur: perso.nom, sens: 'sortie', ticker: ticker,
        texte: perso.nom + ' : « ' + nomAffiche(state, pack, ticker) + ' fait ' +
          fmtPct(pv) + ' depuis notre entrée. ' +
          (pv > 15 ? 'La thèse a payé — je propose d’en prendre une partie.'
            : pv < -15 ? 'La thèse ne se déroule pas. On tranche, ou on assume.'
              : 'Rien d’urgent, mais je préfère qu’on en reparle.') + ' »',
        options: [
          { label: 'Conserver', action: 'rien' },
          { label: 'Alléger de moitié', action: 'vendre', part: 0.5 },
          { label: 'Solder la ligne', action: 'vendre', part: 1 }
        ],
        meta: { ticker: ticker }
      });
      return;
    }
    /* Entrée : un candidat hors portefeuille, coté — l'histoire nécessaire
       au recul de 12 mois vient du pack (cf. faitsPrix), elle existe donc
       dès le premier jour de la partie. */
    var essais = 0, choix = null;
    while (essais++ < 12 && !choix) {
      var t = pack.titres[tirerEntier(state, pack.titres.length)];
      if (state.fonds.positions[t.t]) continue;
      if (prixTitre(state, pack, t.t) === null) continue;
      choix = t;
    }
    if (!choix) return;
    var f = faitsPrix(state, pack, choix.t);
    if (!f || f.p3m === null || f.p12m === null) return;
    var lecture = f.p3m < -12
      ? 'Le repli me semble excessif au vu du reste du secteur — c’est un avis, pas un fait.'
      : f.p3m > 15
        ? 'La dynamique est forte ; le risque, c’est d’acheter le sommet.'
        : 'Rien de spectaculaire, mais la trajectoire est régulière.';
    pousserDialogue(state, {
      type: 'these', auteur: perso.nom, sens: 'entree', ticker: choix.t,
      texte: perso.nom + ' : « J’ai regardé ' + nomAffiche(state, pack, choix.t) +
        ' (' + choix.sec + '). Le titre fait ' + fmtPct(f.p3m) + ' sur trois mois, ' +
        fmtPct(f.p12m) + ' sur un an, et se paie ' + fmtPct(f.sousHaut5a) +
        ' par rapport à son plus haut de cinq ans. ' + lecture + ' On entre à combien ? »',
      options: [
        { label: 'On n’entre pas', action: 'rien' },
        { label: 'Entrer à 2 % du fonds', action: 'acheter', poids: 0.02 },
        { label: 'Entrer à 5 % du fonds', action: 'acheter', poids: 0.05 }
      ],
      meta: { ticker: choix.t }
    });
  }

  function nomAffiche(state, pack, ticker) {
    if (state.reveles[ticker]) {
      return indexerPack(pack).parTicker[ticker].n + ' (' + ticker + ')';
    }
    return state.masques[ticker] || ticker;
  }

  /* ── Dialogues ─────────────────────────────────────────────────────────
     UNE file, UN dialogue actif. Tant qu'il attend, son auteur ne produit
     rien (le coût de l'indécision se voit sur le plateau). */
  function pousserDialogue(state, d) {
    d.id = state.prochainDialogueId++;
    if (state.dialogue) state.fileDialogues.push(d);
    else state.dialogue = d;
  }

  function decider(state, pack, choixIdx) {
    var d = state.dialogue;
    if (!d) return { ok: false, err: 'aucune décision en attente' };
    var opt = d.options[choixIdx];
    if (!opt) return { ok: false, err: 'option inconnue' };
    state.decisions.push({ jour: state.jour, dlg: d.id, choix: choixIdx });
    var evts = [];
    if (d.type === 'these' && opt.action === 'acheter') {
      var montant = encours(state, pack) * opt.poids;
      var r = passerOrdre(state, pack, d.meta.ticker, montant, 'achat');
      if (r.ok) {
        journal(state, 'Entrée sur ' + nomAffiche(state, pack, d.meta.ticker) + ' : ' +
          fmtEur(montant) + ' (frais ' + fmtEur(r.frais) + ', ' + r.bps + ' bps).');
        apprendre(state, 'taille_position');
        if (!aUnGerantExecution(state)) apprendre(state, 'cout_execution');
      } else {
        journal(state, 'Ordre non exécuté : ' + r.err + '.');
      }
    } else if (d.type === 'these' && opt.action === 'vendre') {
      var pos = state.fonds.positions[d.meta.ticker];
      if (pos) {
        var p = prixTitre(state, pack, d.meta.ticker);
        var mv = pos.qte * p * opt.part;
        var rv = passerOrdre(state, pack, d.meta.ticker, mv, 'vente');
        if (rv.ok) {
          journal(state, (opt.part === 1 ? 'Ligne soldée : ' : 'Allègement : ') +
            nomAffiche(state, pack, d.meta.ticker) + ', ' + fmtEur(mv) + '.');
        }
      }
    } else if (d.type === 'candidat' && opt.action === 'embaucher') {
      var re = embaucher(state, d.meta);
      if (!re.ok) journal(state, 'Embauche impossible : ' + re.err + '.');
      else evts.push({ t: 'arrive' });
    } else if (d.type === 'candidat' && opt.action === 'renoncer') {
      journal(state, d.meta.nom + ' poursuivra sa route ailleurs.');
    }
    state.dialogue = state.fileDialogues.shift() || null;
    if (state.dialogue) evts.push({ t: 'dialogue' });
    return { ok: true, evts: evts };
  }

  /* ── Le carnet : les concepts, nommés quand ils arrivent ───────────────
     Jamais de leçon avant l'expérience (§11.1) : chaque entrée cite la
     situation de LA partie qui l'a déclenchée, puis renvoie vers Apprendre. */
  var CONCEPTS = {
    valeur_liquidative: {
      titre: 'La valeur liquidative',
      lien: 'apprendre.html#s2',
      texte: 'Ton fonds vaut : ses lignes au cours du jour, plus sa trésorerie, ' +
        'divisé par le nombre de parts. C’est LA grandeur du métier : les ' +
        'souscriptions entrent à ce prix, les rachats sortent à ce prix, et ta ' +
        'performance est celle de la part — pas celle de l’encours.'
    },
    frais_trainee: {
      titre: 'Les frais, une traînée permanente',
      lien: 'apprendre.html#s7',
      texte: 'Chaque mois, 1/12 des 2 % annuels quitte le fonds pour la société ' +
        '— que le marché monte ou baisse. Sur dix ans, cette traînée se compose ' +
        'comme le reste : c’est l’écart entre la performance brute et la nette.'
    },
    taille_position: {
      titre: 'La taille de position',
      lien: 'apprendre.html#s10',
      texte: 'Tu viens de choisir un poids, pas un titre. À 2 %, une erreur coûte ' +
        'peu et une réussite rapporte peu ; à 5 %, tout compte davantage. La ' +
        'conviction se dose — c’est souvent la vraie décision, avant le titre.'
    },
    cout_execution: {
      titre: 'Le coût d’exécution',
      lien: 'apprendre.html#s7',
      texte: 'Sans gérant d’exécution, tes ordres coûtent 30 points de base — ' +
        'quatre fois le tarif d’un professionnel (7,5 bps). Son salaire se ' +
        'compare à ce qu’il fait économiser : c’est un calcul, pas un principe.'
    },
    achat_abonnement: {
      titre: 'Achat ou abonnement',
      lien: 'apprendre.html#s4',
      texte: 'Un poste de travail s’achète une fois ; un flux de données se paie ' +
        'tous les mois, que les revenus suivent ou non. La charge récurrente est ' +
        'plus dangereuse que l’immobilisation quand la collecte se retourne.'
    },
    point_mort: {
      titre: 'Le point mort',
      lien: 'apprendre.html#s4',
      texte: 'Tes charges sont fixes, tes revenus proportionnels à l’encours : il ' +
        'existe un encours en dessous duquel la société perd de l’argent chaque ' +
        'mois. Calcule-le — c’est le chiffre qui décide de tout le reste.'
    },
    ecart_brut_net: {
      titre: 'Brut, net : l’écart, c’est toi',
      lien: 'apprendre.html#s7',
      texte: 'La performance brute est celle du portefeuille ; la nette est celle ' +
        'du client, après tes frais. L’écart entre les deux est exactement ce que ' +
        'la société encaisse. Les deux chiffres sont vrais — mais un seul est le sien.'
    }
  };
  function apprendre(state, id) {
    for (var i = 0; i < state.carnet.length; i++) {
      if (state.carnet[i].id === id) return;
    }
    var c = CONCEPTS[id];
    if (!c) return;
    state.carnet.push({ id: id, mois: state.mois, titre: c.titre, texte: c.texte, lien: c.lien });
  }

  /* ── Registre : le plateau raconté en texte ────────────────────────────
     Borné : un jeu sans fin qui journalise sans fin finit par ne plus se
     charger (test « 50 ans < 1 Mo »). */
  function journal(state, texte) {
    state.registre.push({ jour: state.jour, texte: texte });
    if (state.registre.length > 120) state.registre.splice(0, state.registre.length - 120);
  }

  /* ── Clôture mensuelle : marché, frais, flux, paie ─────────────────────
     L'ordre est celui du §8.1 et il compte : le marché bouge, PUIS les frais
     se prélèvent sur l'encours revalorisé, PUIS les flux entrent/sortent à
     la VL nouvelle, PUIS la société paie ce qu'elle doit. */
  function cloturerMois(state, pack, evts) {
    state.mois++;

    /* 1. Frais de gestion : prorata mensuel sur l'encours revalorisé.
       La même ligne, deux signes : elle SORT du fonds et ENTRE (moins la
       rétrocession de l'hôte) dans la société. */
    var enc = encours(state, pack);
    var frais = enc * (FRAIS_GESTION_PCT / 100) / 12;
    if (frais > state.fonds.cash) racheterParts(state, pack, 0); // force la vente prorata via le garde
    state.fonds.cash -= frais;
    state.fonds.fraisPreleves += frais;
    var recette = frais * (1 - RETRO_HOTE_PCT);
    state.societe.treso += recette;
    state.societe.fraisEncaisses += recette;
    if (state.mois === 1) { apprendre(state, 'valeur_liquidative'); apprendre(state, 'frais_trainee'); }

    /* 2. Flux investisseurs — ⚠ MVP approximation : les flux suivent la
       performance avec DEUX TRIMESTRES de retard (ils suivent, ils
       n'anticipent jamais), bornés à ±3 %/mois, plus un petit bruit. */
    var vlh = state.fonds.vlHist;
    if (vlh.length > 9) {
      var vFin = vlh[vlh.length - 1 - 6].vl;      // il y a 2 trimestres
      var vDeb = vlh[Math.max(0, vlh.length - 1 - 12)].vl;
      var perfLag = vFin / vDeb - 1;
      var fluxPct = Math.max(-0.03, Math.min(0.03, perfLag * 0.12)) +
        (tirer(state) - 0.5) * 0.006;
      var flux = encours(state, pack) * fluxPct;
      if (flux > 1000) {
        souscrire(state, pack, flux);
        journal(state, 'Collecte du mois : ' + fmtEur(flux) + '.');
      } else if (flux < -1000) {
        racheterParts(state, pack, -flux);
        journal(state, 'Rachats du mois : ' + fmtEur(-flux) + '.');
      }
    }

    /* 3. La société paie : salaires chargés, loyer, données. */
    var salaires = 0;
    for (var i = 0; i < state.equipe.length; i++) salaires += state.equipe[i].cout;
    var abo = ABONNEMENTS[state.societe.abonnement].prix;
    var recurrentMeubles = 0;
    for (var mm = 0; mm < state.plateau.meubles.length; mm++) {
      recurrentMeubles += (MEUBLES[state.plateau.meubles[mm].type] || { recurrent: 0 }).recurrent || 0;
    }
    var depenses = salaires + LOYER_MOIS_EUR + abo + recurrentMeubles;
    state.societe.treso -= depenses;
    state.societe.chargesPayees += depenses;
    if (state.equipe.length && depenses > recette) apprendre(state, 'point_mort');

    /* 4. Trace mensuelle (bornée par nature : une ligne par mois). */
    var v = vl(state, pack);
    state.fonds.vlHist.push({ m: state.mois, vl: arrondi(v, 4) });
    state.societe.histo.push({
      m: state.mois, recettes: Math.round(recette), depenses: Math.round(depenses),
      treso: Math.round(state.societe.treso)
    });

    /* 5. Cessation de paiement : trésorerie négative deux mois de suite.
       La seule fin du jeu — factuelle, jamais morale (§10.4). */
    var h = state.societe.histo;
    if (h.length >= 2 && h[h.length - 1].treso < 0 && h[h.length - 2].treso < 0) {
      state.fin = {
        mois: state.mois, raison: 'cessation',
        texte: 'La société ne paie plus ses charges depuis deux mois. ' +
          'Le fonds, lui, vaut ' + fmtEur(encours(state, pack)) +
          ' — ce n’est pas lui qui a lâché, ce sont tes coûts fixes.'
      };
      evts.push({ t: 'fin' });
    }

    /* 6. Bilan de janvier : l'hôte fait le point, une fois par an. */
    if (state.mois % 12 === 0 && !state.fin) {
      var an = state.mois / 12;
      var vAvant = vlh.length > 12 ? vlh[vlh.length - 12].vl : VL_INITIALE;
      var perfNette = (v / vAvant - 1) * 100;
      var encMoy = encours(state, pack);
      var traineeFrais = FRAIS_GESTION_PCT;
      var resultat = state.societe.fraisEncaisses - state.societe.chargesPayees;
      pousserDialogue(state, {
        type: 'bilan', auteur: NOM_HOTE,
        texte: NOM_HOTE + ' : « Année ' + an + '. La part fait ' + fmtPct(perfNette) +
          ' en net ; en brut, avant tes frais, ' + fmtPct(perfNette + traineeFrais) +
          ' — l’écart, c’est ta grille. Encours : ' + fmtEur(encMoy) +
          '. Côté société, résultat cumulé ' + fmtEur(resultat) +
          (resultat < 0 ? ' : tu vis encore sur ton apport.' : '.') + ' »',
        options: [{ label: 'Bien reçu', action: 'rien' }],
        meta: {}
      });
      apprendre(state, 'ecart_brut_net');
      evts.push({ t: 'bilan', an: an });
    }
    evts.push({ t: 'mois', m: state.mois });
  }

  /* ── Le tic quotidien : les gens vivent en jours ouvrés ────────────────
     Rien ici ne touche au marché — il ne bouge qu'à la clôture du mois. */
  function tickJour(state, pack) {
    indexerPack(pack);
    if (state.fin) return [];
    if (state.dialogue) return [];       // pause de fait : une décision attend
    var evts = [];
    state.jour++;

    /* Recrutement en cours. */
    if (state.recrutement && --state.recrutement.joursRestants <= 0) {
      presenterCandidat(state);
      evts.push({ t: 'dialogue' });
    }

    /* Chaque personne avance : rampe, production, pauses café. */
    for (var i = 0; i < state.equipe.length; i++) {
      var p = state.equipe[i];
      if (p.etat === 'entre') { p.etat = 'poste'; p.pos = p.but; continue; }
      var def = ROLES[p.role];
      if (!def.joursParNote) continue;   // l'exécution ne produit pas de notes
      var rampe = (state.jour - p.arriveJour) < RAMPE_JOURS ? 0.5 : 1;
      var facteur = ABONNEMENTS[state.societe.abonnement].facteur;
      var vitesse = (0.7 + p.competence * 0.15) * rampe * facteur;
      p.progression += vitesse / def.joursParNote;
      if (tirer(state) < 0.04 && aMachineCafe(state)) {
        p.etat = 'cafe'; p.but = tuileMeuble(state, 'cafe');
      } else if (p.etat === 'cafe') {
        p.etat = 'poste'; p.but = tuilePoste(state, p);
      }
      if (p.progression >= 1) {
        p.progression = 0;
        state.stats.notesProduites++;
        p.etat = 'attend';               // il vient te voir, et il attendra
        p.but = tuileMeuble(state, 'fondateur');
        produireThese(state, pack, p);
        evts.push({ t: 'dialogue' });
      }
    }
    /* Celui dont la question est résolue retourne travailler. */
    if (!state.dialogue) {
      for (var j = 0; j < state.equipe.length; j++) {
        if (state.equipe[j].etat === 'attend') {
          state.equipe[j].etat = 'poste';
          state.equipe[j].but = tuilePoste(state, state.equipe[j]);
        }
      }
    }

    if (state.jour % JOURS_PAR_MOIS === 0) cloturerMois(state, pack, evts);
    if (state.dialogue) evts.push({ t: 'pause' });
    return evts;
  }

  function aMachineCafe(state) { return tuileMeuble(state, 'cafe') !== null; }
  function tuileMeuble(state, type) {
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      var m = state.plateau.meubles[i];
      if (m.type === type) return { x: m.x, y: m.y };
    }
    return null;
  }
  function tuilePoste(state, perso) {
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      var m = state.plateau.meubles[i];
      if (m.id === perso.posteId) return { x: m.x, y: m.y };
    }
    return { x: state.plateau.porte.x, y: state.plateau.porte.y };
  }

  function changerAbonnement(state, niveau) {
    if (!ABONNEMENTS[niveau]) return { ok: false, err: 'niveau inconnu' };
    var avant = state.societe.abonnement;
    state.societe.abonnement = niveau;
    if (ABONNEMENTS[niveau].prix > ABONNEMENTS[avant].prix) apprendre(state, 'achat_abonnement');
    journal(state, 'Données : ' + ABONNEMENTS[niveau].label + ' (' +
      fmtEur(ABONNEMENTS[niveau].prix) + '/mois).');
    return { ok: true };
  }

  /* ── Création, sérialisation ───────────────────────────────────────────
     La partie démarre HÉBERGÉE (⚠ MVP, décision #8 du prompt) : l'acte I —
     agrément, capital de 125 000 €, fonds propres — est le début du lot ②. */
  function creerPartie(seed, pack) {
    indexerPack(pack);
    var state = {
      v: VERSION, seed: seed >>> 0, rng: seed >>> 0,
      jour: 0, mois: 0,
      /* Le départ dans l'historique varie avec la graine : entre 2 et 8 ans
         après t0, pour garder 12 mois de recul aux thèses et des années de
         marché devant. */
      marcheDepart: 0,
      plateau: {
        w: 8, h: 6, porte: { x: 0, y: 3 }, prochainId: 2,
        meubles: [{ id: 1, type: 'fondateur', x: 6, y: 1 }]
      },
      societe: {
        treso: TRESO_DEPART_EUR, abonnement: 'base',
        fraisEncaisses: 0, chargesPayees: 0, histo: []
      },
      fonds: {
        parts: COLLECTE_INITIALE_EUR / VL_INITIALE, cash: COLLECTE_INITIALE_EUR,
        positions: {}, fraisPreleves: 0, fraisTransaction: 0,
        vlHist: [{ m: 0, vl: VL_INITIALE }]
      },
      equipe: [], recrutement: null,
      dialogue: null, fileDialogues: [],
      masques: {}, reveles: {},
      carnet: [], registre: [], decisions: [],
      stats: { notesProduites: 0, ordres: 0 },
      prochainPersoId: 1, prochainDialogueId: 1,
      fin: null
    };
    state.marcheDepart = 24 + tirerEntier(state, 96);
    /* Attribution des noms masqués : mélange de Fisher-Yates à la graine. */
    var noms = NOMS_FICTIFS.slice();
    for (var i = noms.length - 1; i > 0; i--) {
      var j = tirerEntier(state, i + 1);
      var tmp = noms[i]; noms[i] = noms[j]; noms[j] = tmp;
    }
    for (var k = 0; k < pack.titres.length; k++) {
      state.masques[pack.titres[k].t] = noms[k % noms.length];
    }
    /* L'ouverture : une seule chose à faire, dite en une phrase (§24.3). */
    pousserDialogue(state, {
      type: 'intro', auteur: 'Toi',
      texte: 'Premier jour. ' + NOM_HOTE + ' nous héberge — l’agrément viendra ' +
        'plus tard. On a ' + fmtEur(TRESO_DEPART_EUR) + ' d’apport, ' +
        fmtEur(COLLECTE_INITIALE_EUR) + ' confiés par les premiers clients, et ' +
        'une pièce presque vide. Il nous faut quelqu’un qui sache lire un bilan ' +
        '— et d’abord, un poste où l’asseoir.',
      options: [{ label: 'Au travail', action: 'rien' }],
      meta: {}
    });
    return state;
  }

  function serialiser(state) { return JSON.stringify(state); }
  function charger(json, pack) {
    var state = JSON.parse(json);
    if (state.v !== VERSION) {
      /* Place réservée aux migrations : v1 est la première version. */
      throw new Error('sauvegarde v' + state.v + ' inconnue');
    }
    indexerPack(pack);
    return state;
  }

  /* ── Formatage ─────────────────────────────────────────────────────────
     Les montants du jeu sont des nombres ; le texte les met en forme au
     moment de parler (même choix qu'Actualités : on ne stocke jamais une
     chaîne formatée). */
  function arrondi(v, d) { var f = Math.pow(10, d); return Math.round(v * f) / f; }
  function fmtEur(v) {
    var n = Math.round(v);
    var s = String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (n < 0 ? '−' : '') + s + ' €';
  }
  function fmtPct(v) {
    if (v === null || v === undefined) return '—';
    return (v > 0 ? '+' : v < 0 ? '−' : '') +
      String(arrondi(Math.abs(v), 1)).replace('.', ',') + ' %';
  }

  var MAISON = {
    VERSION: VERSION, CLE_SAUVEGARDE: CLE_SAUVEGARDE,
    FRAIS_EXEC_BPS: FRAIS_EXEC_BPS, ORDRE_MIN_EUR: ORDRE_MIN_EUR,
    FRAIS_EXEC_SANS_GERANT_BPS: FRAIS_EXEC_SANS_GERANT_BPS,
    FRAIS_GESTION_PCT: FRAIS_GESTION_PCT, JOURS_PAR_MOIS: JOURS_PAR_MOIS,
    ROLES: ROLES, MEUBLES: MEUBLES, ABONNEMENTS: ABONNEMENTS,
    mulberry32: mulberry32, hash: hash,
    creerPartie: creerPartie, tickJour: tickJour, decider: decider,
    poserMeuble: poserMeuble, retirerMeuble: retirerMeuble,
    lancerRecrutement: lancerRecrutement, changerAbonnement: changerAbonnement,
    postesLibres: postesLibres, connexiteOk: connexiteOk,
    prixTitre: prixTitre, faitsPrix: faitsPrix, nomAffiche: nomAffiche,
    encours: encours, vl: vl, valeurLignes: valeurLignes,
    souscrire: souscrire, racheterParts: racheterParts, passerOrdre: passerOrdre,
    serialiser: serialiser, charger: charger,
    fmtEur: fmtEur, fmtPct: fmtPct
  };

  if (typeof module !== 'undefined') module.exports = MAISON;
  if (typeof window !== 'undefined') window.MAISON = MAISON;
})();
