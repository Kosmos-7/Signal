/* maison-ui.js — La Maison : LA COLLE, ET RIEN QU'ELLE.
   ============================================================================
   Tout ce qui touche au navigateur vit ici : fetch du pack, horloge murale,
   DOM, clavier, tactile, localStorage. Le partage des rôles est strict et
   c'est lui qui rend le reste testable : maison-moteur.js ne sait pas qu'un
   navigateur existe, maison-iso.js lit un état et le dessine sans rien
   décider — ce fichier est le seul autorisé à faire du temps réel et des
   effets de bord.

   Date.now() n'apparaît que deux fois, et c'est un contrat : le cache-busting
   du pack, et la graine d'une partie neuve. L'horloge du jeu, elle, vient de
   requestAnimationFrame — jamais de l'heure murale, sinon un onglet endormi
   rattraperait des mois en une seule image. Tout le hasard du jeu vit dans le
   moteur, à graine : rien ne se tire ici. */
(function () {
  'use strict';

  /* ── Constantes d'interface ────────────────────────────────────────────
     ms par jour ouvré : ×1 = 2 s/jour, donc un mois ≈ 40 s (§3.5 du prompt). */
  var VITESSES = { 1: 2000, 2: 1000, 4: 500 };
  var MS_PAR_LETTRE = 18;          // l'hommage Pokémon (§3.2)
  var MAX_JOURS_PAR_IMAGE = 8;     // garde-fou : une image ne rejoue jamais une semaine
  /* Le loyer n'est pas exporté par le moteur (il n'en a besoin qu'en interne).
     Recopié ici UNIQUEMENT pour l'affichage du panneau Société — même valeur,
     96 m² × 450 €/m²/an (§23). Si les deux divergent un jour, c'est l'écran
     qui ment, pas la comptabilité : le moteur reste la référence. */
  var LOYER_MOIS_EUR = 3600;
  var ETATS = {
    poste: 'Au poste', cafe: 'À la machine à café',
    attend: 'T’attend pour une décision', entre: 'Vient d’arriver'
  };

  var reduire = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── État de l'interface — jamais sérialisé : tout se reconstruit ────── */
  var pack = null, state = null, iso = null;
  var vitesse = 1, enPause = false;
  var enPlan = false, typeChoisi = null, propositionRevente = null;
  var planMsg = '', planXY = { x: 0, y: 0 };
  var survol = null, selection = null;
  var panX = 0, panY = 0, echelle = 2;
  var ongletActif = 'fonds';
  var carnetVu = 0;                // pastille « nouveau concept » sur l'onglet
  var ctxPerso = '';               // la phrase du dernier personnage cliqué
  var memoireOk = true;            // navigation privée : setItem lève
  var sauvegardeCoupee = false;    // après « effacer mes données »
  var finAffichee = false;
  var dlgAfficheId = null;
  var rafId = null, tPrec = null, accumulateur = 0;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function borner(v, min, max) {
    v = Math.round(+v || 0);
    return Math.max(min, Math.min(max, v));
  }
  /* La VL s'affiche au centime : c'est LA grandeur du jeu, l'arrondi du
     fmtEur (à l'euro) l'écraserait à trois chiffres près. */
  function fmtVL(v) { return v.toFixed(2).replace('.', ',') + ' €'; }
  function fmtPoids(v) { return v.toFixed(1).replace('.', ',') + ' %'; }
  /* .pos/.neg UNIQUEMENT sur du P&L factuel chiffré — la règle du site. Le
     seuil évite un vert affiché sur un « +0,0 % » qui ne montre rien. */
  function clPct(v) { return v > 0.05 ? 'pos' : v < -0.05 ? 'neg' : 'neu'; }
  function graineParDefaut() {
    /* Seul recours du jeu à l'heure murale : une graine « du moment » pour
       une partie neuve. Elle part aussitôt dans le hash, donc elle reste
       partageable et rejouable comme n'importe quelle autre. */
    return (Date.now() % 4294967296) >>> 0;
  }

  /* ── Boot ──────────────────────────────────────────────────────────────
     Le pack d'abord : sans cours, pas de partie. Le ?v= force le
     rafraîchissement du pack régénéré chaque nuit par la CI. */
  fetch('jeu/marche.json?v=' + Date.now())
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (p) { pack = p; demarrer(); })
    .catch(function () {
      $('jm-dlg-texte').textContent = 'Le pack de marché (jeu/marche.json) ne se ' +
        'charge pas — sans lui, pas de cours, donc pas de partie. Recharge la page.';
    });

  function lireSauvegarde() {
    try { return localStorage.getItem(window.MAISON.CLE_SAUVEGARDE); }
    catch (e) { memoireOk = false; return null; }
  }

  function demarrer() {
    var MAISON = window.MAISON;
    var m = /^#\/p\/(.+)$/.exec(location.hash || '');
    var graineHash = null;
    if (m) {
      var brut = decodeURIComponent(m[1]);
      graineHash = /^\d+$/.test(brut) ? (parseInt(brut, 10) >>> 0) : MAISON.hash(brut);
    }
    var json = lireSauvegarde();
    var sauve = null;
    if (json) {
      try { sauve = MAISON.charger(json, pack); }
      catch (e) { sauve = null; /* version inconnue : on repart proprement */ }
    }
    if (graineHash !== null && (!sauve || sauve.seed !== graineHash)) {
      /* Un lien partagé rejoue le monde depuis le premier jour. MAIS si la
         sauvegarde locale EST déjà ce monde-là, on la reprend au lieu de
         l'écraser : recharger la page ne doit jamais coûter une partie —
         d'autant que la graine d'une partie neuve est écrite dans le hash. */
      state = MAISON.creerPartie(graineHash, pack);
    } else if (sauve) {
      state = sauve;
    } else {
      state = MAISON.creerPartie(graineParDefaut(), pack);
    }
    if (location.hash !== '#/p/' + state.seed) location.replace('#/p/' + state.seed);

    carnetVu = state.carnet.length;
    iso = window.MaisonIso.creer($('jm-jeu'));
    echelle = window.innerWidth < 700 ? 1 : 2;   // petit écran : ×1 d'office (§15)
    iso.definirEchelle(echelle);
    $('jm-echelle').textContent = '×' + echelle;
    iso.redimensionner();
    brancher();
    majPanneau();
    syncDialogue();
    demarrerBoucle();
  }

  /* ── L'horloge : rAF + accumulateur ────────────────────────────────────
     Le moteur avance par jours entiers ; l'accumulateur transforme le temps
     d'image (irrégulier) en pas réguliers. Un dialogue en attente vide
     l'accumulateur : quand on répond dix minutes plus tard, la partie repart
     du même pas, elle ne « rattrape » rien. */
  function demarrerBoucle() {
    if (rafId !== null) return;
    tPrec = null;
    rafId = requestAnimationFrame(image);
  }
  function arreterBoucle() {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
  }
  function image(t) {
    rafId = requestAnimationFrame(image);
    if (tPrec === null) tPrec = t;
    var dt = Math.min(t - tPrec, 500);
    tPrec = t;
    if (!state.dialogue && !state.fin && !enPause && !enPlan) {
      accumulateur += dt;
      var pas = VITESSES[vitesse], n = 0, evtsVus = 0;
      while (accumulateur >= pas && n < MAX_JOURS_PAR_IMAGE) {
        accumulateur -= pas; n++;
        var evts = window.MAISON.tickJour(state, pack);
        for (var i = 0; i < evts.length; i++) traiterEvt(evts[i]);
        evtsVus += evts.length;
        if (state.dialogue || state.fin) { accumulateur = 0; break; }
      }
      if (n) {
        majBarre();
        syncDialogue();
        /* Le panneau ne se reconstruit que s'il s'est passé quelque chose :
           reconstruire ses boutons toutes les deux secondes volerait le
           focus à quiconque est en train de cliquer dedans. */
        if (evtsVus) majPanneau();
      }
    } else {
      accumulateur = 0;
    }
    iso.dessiner(state, t, optsRendu());
  }

  function optsRendu() {
    var fantome = null;
    if (enPlan && typeChoisi && survol) {
      fantome = {
        type: typeChoisi, x: survol.x, y: survol.y,
        ok: poseOk(typeChoisi, survol.x, survol.y)
      };
    }
    return { selection: selection, survol: survol, reduireMouvement: reduire, fantome: fantome };
  }

  /* ── Événements du moteur ────────────────────────────────────────────── */
  function traiterEvt(e) {
    if (e.t === 'mois') {
      sauvegarder(false);            // la sauvegarde auto vit au rythme du mois (§13)
      if (e.m % 12 === 0) {
        /* L'annonce est ANNUELLE, pas mensuelle : un lecteur d'écran qui
           parle toutes les quarante secondes rend le jeu infréquentable (§15). */
        annoncer('Année ' + (e.m / 12) + ' : la part vaut ' +
          fmtVL(window.MAISON.vl(state, pack)) + ', encours ' +
          window.MAISON.fmtEur(window.MAISON.encours(state, pack)) + '.');
      }
    } else if (e.t === 'fin') {
      annoncer(state.fin.texte);
    } else if (e.t === 'arrive') {
      var der = state.registre[state.registre.length - 1];
      if (der) annoncer(der.texte);
    }
  }

  /* ── La boîte de dialogue (§3.2) ───────────────────────────────────────
     UNE boîte, en bas, et c'est la seule surface de décision du jeu. Le
     panneau consulte, les gens parlent ici. */
  function syncDialogue() {
    if (finAffichee) return;
    if (state.fin) { rendreFin(); return; }
    var d = state.dialogue;
    if (!d) {
      if (dlgAfficheId !== null) { dlgAfficheId = null; if (!enPlan) rendreRepos(); }
      return;
    }
    if (d.id === dlgAfficheId) return;
    dlgAfficheId = d.id;
    if (enPlan) fermerPlan();       // une décision prime sur l'aménagement
    rendreDialogue(d);
    annoncer((d.auteur ? d.auteur + ' — ' : '') + premierePhrase(d.texte));
  }
  function premierePhrase(t) {
    var m = /^[^.!?]*[.!?]/.exec(t || '');
    return m ? m[0] : (t || '');
  }
  function rendreDialogue(d) {
    $('jm-dlg-auteur').textContent = d.auteur || '';
    $('jm-dlg-opts').innerHTML = '';
    taper(d.texte, function () { montrerOptions(d.options); });
  }
  function montrerOptions(options) {
    var h = '';
    for (var i = 0; i < options.length; i++) {
      h += '<button type="button" class="jm-opt" data-opt="' + i + '"><b>' +
        (i + 1) + '</b><span>' + esc(options[i].label) + '</span></button>';
    }
    $('jm-dlg-opts').innerHTML = h;
    var prem = $('jm-dlg-opts').querySelector('button');
    if (prem) prem.focus({ preventScroll: true });
  }
  function rendreRepos() {
    arreterFrappe();
    $('jm-dlg-auteur').textContent = '';
    $('jm-dlg-opts').innerHTML = '';
    $('jm-dlg-texte').textContent =
      'Le bureau vit sa journée. Espace : pause · P : aménager · V : vitesse.';
  }

  /* La frappe lettre à lettre. Un clic pendant l'écriture livre tout d'un
     coup ; prefers-reduced-motion la court-circuite entièrement — le jeu
     reste le même, seul le théâtre disparaît (§15). */
  var frappe = { active: false, plein: '', apres: null, minuteur: null };
  function taper(texte, apres) {
    arreterFrappe();
    var el = $('jm-dlg-texte');
    if (reduire) {
      el.textContent = texte;
      if (apres) apres();
      return;
    }
    frappe.active = true; frappe.plein = texte; frappe.apres = apres || null;
    var i = 0;
    el.textContent = '';
    el.classList.add('type-cur');
    frappe.minuteur = setInterval(function () {
      i++;
      el.textContent = frappe.plein.slice(0, i);
      if (i >= frappe.plein.length) completerFrappe();
    }, MS_PAR_LETTRE);
  }
  function arreterFrappe() {
    if (frappe.minuteur) { clearInterval(frappe.minuteur); frappe.minuteur = null; }
    frappe.active = false;
    $('jm-dlg-texte').classList.remove('type-cur');
  }
  function completerFrappe() {
    if (!frappe.active) return;
    var apres = frappe.apres;
    $('jm-dlg-texte').textContent = frappe.plein;
    arreterFrappe();
    if (apres) apres();
  }

  function choisir(idx) {
    if (finAffichee) { if (idx === 0) recommencer(); return; }
    if (!state.dialogue) return;
    if (frappe.active) { completerFrappe(); return; }
    var r = window.MAISON.decider(state, pack, idx);
    if (!r.ok) return;
    dlgAfficheId = null;
    var evts = r.evts || [];
    for (var i = 0; i < evts.length; i++) traiterEvt(evts[i]);
    /* Une décision perdue serait la pire perte possible : on sauve tout de
       suite, sans attendre la fin du mois. */
    sauvegarder(false);
    syncDialogue();
    if (!state.dialogue && !state.fin) rendreRepos();
    majBarre();
    majPanneau();
  }

  /* ── La fin — factuelle, jamais morale (§10.4), et relançable (§24.4) ── */
  function rendreFin() {
    if (finAffichee) return;
    finAffichee = true;
    if (enPlan) fermerPlan();
    $('jm-dlg-auteur').textContent = 'Fin de partie';
    $('jm-dlg-opts').innerHTML = '';
    taper(state.fin.texte, function () {
      $('jm-dlg-opts').innerHTML = '<button type="button" class="jm-opt" data-opt="0">' +
        '<b>1</b><span>Recommencer en gardant le carnet</span></button>';
      var b = $('jm-dlg-opts').querySelector('button');
      if (b) b.focus({ preventScroll: true });
    });
  }
  function recommencer() {
    /* Nouvelle graine, mais le carnet suit : on perd la maison, pas ce qu'on
       y a compris. Les entrées copiées gardent leur mois d'origine, et le
       moteur ne les redéclenchera pas — il vérifie par identifiant. */
    var carnet = state.carnet.slice();
    state = window.MAISON.creerPartie(graineParDefaut(), pack);
    state.carnet = carnet;
    carnetVu = carnet.length;
    finAffichee = false;
    dlgAfficheId = null;
    enPause = false; vitesse = 1; ctxPerso = ''; selection = null; survol = null;
    location.replace('#/p/' + state.seed);
    sauvegarder(false);
    majBarre();
    majPanneau();
    syncDialogue();
  }

  /* ── Sauvegarde : localStorage, toujours sous try/catch ────────────────
     En navigation privée Safari, setItem LÈVE. Le jeu doit rester jouable
     sans mémoire : on le dit une fois dans le registre, et on n'en reparle
     plus (§13). */
  function sauvegarder(manuelle) {
    if (sauvegardeCoupee && !manuelle) return;  // « effacer » vaut jusqu'à nouvel ordre
    if (manuelle) sauvegardeCoupee = false;
    try {
      localStorage.setItem(window.MAISON.CLE_SAUVEGARDE, window.MAISON.serialiser(state));
      memoireOk = true;
    } catch (e) {
      if (memoireOk) {
        memoireOk = false;
        state.registre.push({
          jour: state.jour,
          texte: 'Navigation privée : la partie ne sera pas mémorisée. ' +
            'Exporte-la (panneau Registre) pour la garder.'
        });
      }
    }
  }
  function exporter() {
    var a = document.createElement('a');
    var url = URL.createObjectURL(new Blob([window.MAISON.serialiser(state)],
      { type: 'application/json' }));
    a.href = url;
    a.download = 'maison-' + state.seed + '-mois' + state.mois + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  function effacer() {
    if (!confirm('Effacer la sauvegarde locale de La Maison ? La partie en cours ' +
      'reste à l’écran, mais plus rien ne sera retenu — jusqu’à une sauvegarde manuelle.')) return;
    try { localStorage.removeItem(window.MAISON.CLE_SAUVEGARDE); } catch (e) { /* déjà sans mémoire */ }
    sauvegardeCoupee = true;
    state.registre.push({
      jour: state.jour,
      texte: 'Données locales effacées. L’auto-sauvegarde est coupée ' +
        '(le bouton « Sauvegarder » la réactive).'
    });
    majPanneau();
  }

  /* ── La barre permanente : date, vitesse, encours, trésorerie ────────── */
  function majBarre() {
    var etat = state.fin ? ' · terminé'
      : state.dialogue ? ' · décision en attente'
        : enPlan ? ' · plan' : enPause ? ' · pause' : '';
    $('jm-date').textContent = 'Mois ' + (state.mois % 12 + 1) + ' · Année ' +
      (Math.floor(state.mois / 12) + 1) + etat;
    $('jm-encours').textContent = window.MAISON.fmtEur(window.MAISON.encours(state, pack));
    $('jm-treso').textContent = window.MAISON.fmtEur(state.societe.treso);
    var btns = document.querySelectorAll('.jm-vit');
    for (var i = 0; i < btns.length; i++) {
      var v = +btns[i].getAttribute('data-vit');
      btns[i].classList.toggle('on', v === 0 ? enPause : (!enPause && vitesse === v));
    }
  }
  function basculerPause() { enPause = !enPause; majBarre(); }
  function cyclerVitesse() {
    enPause = false;
    vitesse = vitesse === 1 ? 2 : vitesse === 2 ? 4 : 1;
    majBarre();
  }

  /* ── Le panneau à onglets : il consulte, il ne décide pas (§3.4) ─────── */
  function majPanneau() {
    majBarre();
    var dot = document.querySelector('.jm-tab[data-tab="carnet"] .jm-dot');
    if (dot) dot.hidden = !(state.carnet.length > carnetVu && ongletActif !== 'carnet');
    if (ongletActif === 'fonds') $('jm-dyn-fonds').innerHTML = htmlFonds();
    else if (ongletActif === 'societe') $('jm-dyn-societe').innerHTML = htmlSociete();
    else if (ongletActif === 'equipe') $('jm-dyn-equipe').innerHTML = htmlEquipe();
    else if (ongletActif === 'registre') $('jm-dyn-registre').innerHTML = htmlRegistre();
    else if (ongletActif === 'carnet') $('jm-dyn-carnet').innerHTML = htmlCarnet();
  }
  function ouvrirOnglet(nom) {
    ongletActif = nom;
    if (nom === 'carnet') carnetVu = state.carnet.length;
    var tabs = document.querySelectorAll('.jm-tab');
    for (var i = 0; i < tabs.length; i++) {
      var on = tabs[i].getAttribute('data-tab') === nom;
      tabs[i].classList.toggle('on', on);
      tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
    }
    var vues = document.querySelectorAll('.jm-vue');
    for (var j = 0; j < vues.length; j++) {
      vues[j].hidden = vues[j].id !== 'jm-t-' + nom;
    }
    basculerFeuille(true);   // sur mobile, C ou L doivent OUVRIR la feuille, pas juste la peupler
    majPanneau();
  }
  function basculerFeuille(ouvrir) {
    var pan = $('jm-panneau');
    var on = ouvrir === undefined ? !pan.classList.contains('on') : ouvrir;
    pan.classList.toggle('on', on);
    var b = $('jm-depli');
    b.setAttribute('aria-expanded', on ? 'true' : 'false');
    b.setAttribute('aria-label', on ? 'Replier le panneau' : 'Ouvrir le panneau');
    b.textContent = on ? '▾' : '▴';
  }

  function met(k, vHtml) {
    return '<div><span class="k">' + k + '</span><span class="v">' + vHtml + '</span></div>';
  }

  function htmlFonds() {
    var MAISON = window.MAISON;
    var enc = MAISON.encours(state, pack);
    var v = MAISON.vl(state, pack);
    var v0 = state.fonds.vlHist[0].vl;
    var perf = (v / v0 - 1) * 100;
    var frais = state.fonds.fraisPreleves + state.fonds.fraisTransaction;
    var h = '<div class="sec-h">Le fonds</div><div class="metrics">' +
      met('VL', fmtVL(v)) +
      met('Depuis l’origine', '<span class="' + clPct(perf) + '">' + MAISON.fmtPct(perf) + '</span>') +
      met('Encours', MAISON.fmtEur(enc)) +
      met('Trésorerie du fonds', MAISON.fmtEur(state.fonds.cash)) +
      met('Frais cumulés', MAISON.fmtEur(frais)) +
      met('Lignes', String(Object.keys(state.fonds.positions).length)) +
      '</div>';
    var tickers = Object.keys(state.fonds.positions);
    if (!tickers.length) {
      h += '<p class="stub">Aucune ligne : le fonds est en trésorerie. Les idées viendront des analystes.</p>';
    } else {
      h += '<div class="sec-h">Lignes</div>';
      for (var i = 0; i < tickers.length; i++) {
        var t = tickers[i];
        var pos = state.fonds.positions[t];
        var p = MAISON.prixTitre(state, pack, t);
        if (p === null) continue;
        var poids = enc > 0 ? (pos.qte * p / enc) * 100 : 0;
        var latent = (p / pos.pru - 1) * 100;
        h += '<div class="jm-ligne"><span class="jm-l-nom">' +
          esc(MAISON.nomAffiche(state, pack, t)) + '</span>' +
          '<span class="jm-l-poids">' + fmtPoids(poids) + '</span>' +
          '<span class="jm-l-pv ' + clPct(latent) + '">' + MAISON.fmtPct(latent) + '</span>' +
          '<span class="jm-l-sec">' + esc((pack.parTicker[t] || {}).sec || '') + '</span></div>';
      }
      h += '<p class="jm-note-panneau">Consulter, pas vendre : les décisions passent par les dialogues.</p>';
    }
    return h;
  }

  function htmlSociete() {
    var MAISON = window.MAISON;
    var histo = state.societe.histo;
    var der = histo.length ? histo[histo.length - 1] : null;
    var salaires = 0;
    for (var i = 0; i < state.equipe.length; i++) salaires += state.equipe[i].cout;
    var abo = MAISON.ABONNEMENTS[state.societe.abonnement];
    var h = '<div class="sec-h">La société</div><div class="metrics">' +
      met('Trésorerie', MAISON.fmtEur(state.societe.treso)) +
      met('Recettes (dernier mois)', der ? MAISON.fmtEur(der.recettes) : '—') +
      met('Dépenses (dernier mois)', der ? MAISON.fmtEur(der.depenses) : '—') +
      met('Loyer', MAISON.fmtEur(LOYER_MOIS_EUR) + '/mois') +
      met('Masse salariale', MAISON.fmtEur(salaires) + '/mois') +
      met('Données', esc(abo.label)) +
      '</div>';
    h += '<div class="sec-h">Abonnement de données</div>';
    for (var k in MAISON.ABONNEMENTS) {
      var a = MAISON.ABONNEMENTS[k];
      h += '<label class="jm-abo"><input type="radio" name="jm-abo" value="' + k + '"' +
        (state.societe.abonnement === k ? ' checked' : '') + '><span><b>' + esc(a.label) +
        '</b> — ' + MAISON.fmtEur(a.prix) + '/mois · notes ×' +
        String(a.facteur).replace('.', ',') + '</span></label>';
    }
    h += '<p class="jm-note-panneau">Un abonnement se paie tous les mois, que la collecte ' +
      'suive ou non — c’est toute la différence avec un meuble, qu’on achète une fois.</p>';
    return h;
  }

  function htmlEquipe() {
    var MAISON = window.MAISON;
    var h = '';
    if (ctxPerso) h += '<div class="card jm-ctx">' + esc(ctxPerso) + '</div>';
    h += '<div class="sec-h">L’équipe</div>';
    h += '<div class="card jm-perso"><div class="jm-p-h"><b>Toi</b>' +
      '<span class="tag">Fondateur</span></div>' +
      '<div class="jm-p-l">Tu ne produis pas de notes : tu tranches. Ton bureau est ' +
      'la tuile où l’on vient t’attendre.</div></div>';
    for (var i = 0; i < state.equipe.length; i++) {
      var p = state.equipe[i];
      var def = MAISON.ROLES[p.role];
      var anc = Math.floor((state.jour - p.arriveJour) / MAISON.JOURS_PAR_MOIS);
      h += '<div class="card jm-perso"><div class="jm-p-h"><b>' + esc(p.nom) + '</b>' +
        '<span class="tag">' + esc(def.label) + '</span></div>' +
        '<div class="jm-p-l">Compétence ' + p.competence + '/5 · ' +
        (anc < 1 ? 'arrivé ce mois-ci' : anc + ' mois de maison') + ' · ' +
        esc(ETATS[p.etat] || p.etat) + '</div>';
      if (def.joursParNote) {
        var prog = Math.round(p.progression * 100);
        h += '<div class="meter"><span>Note</span><span class="t"><span class="f" ' +
          'style="width:' + prog + '%"></span></span><span class="mval">' + prog + ' %</span></div>';
      } else {
        h += '<div class="jm-p-l">Passe les ordres du fonds : 7,5 bps au lieu de 30.</div>';
      }
      h += '<div class="gauge"><div class="gl"><span>Moral</span><b>' + p.moral +
        '/100</b></div><div class="gtrack"><span class="gmark" style="left:' +
        p.moral + '%"></span></div></div>';
      /* Brut ET chargé, côte à côte : c'est LE point pédagogique du recrutement. */
      h += '<div class="jm-p-l">' + MAISON.fmtEur(p.brut) + ' brut · <b>' +
        MAISON.fmtEur(p.cout) + ' chargés</b>/mois</div></div>';
    }
    if (!state.equipe.length) {
      h += '<p class="stub">Personne encore. Un poste de travail posé, et le recrutement s’ouvre.</p>';
    }
    h += '<div class="sec-h">Recruter</div>';
    var raison = state.recrutement ? 'une recherche est déjà en cours'
      : (!MAISON.postesLibres(state).length
        ? 'aucun poste de travail libre — pose d’abord un poste (mode plan, touche P)' : '');
    if (raison) h += '<p class="jm-raison">Indisponible : ' + esc(raison) + '.</p>';
    for (var k in MAISON.ROLES) {
      var r = MAISON.ROLES[k];
      h += '<button type="button" class="jm-btn" data-act="recruter" data-role="' + k + '"' +
        (raison ? ' disabled' : '') + '>' + esc(r.label) + ' — ' + MAISON.fmtEur(r.brut) +
        ' brut · ' + MAISON.fmtEur(r.cout) + ' chargés</button> ';
    }
    h += '<p class="jm-note-panneau">Un mois de recherche, une prime d’arrivée d’un mois ' +
      'de brut, trois mois de rampe : embaucher n’est jamais un clic gratuit.</p>';
    return h;
  }

  function htmlRegistre() {
    var h = '<div class="sec-h">Registre</div>';
    if (!state.registre.length) {
      h += '<p class="stub">Rien encore.</p>';
    } else {
      /* Les plus récentes en haut : le registre se lit comme un fil, et il
         raconte en texte tout ce que le plateau montre en images (§15). */
      for (var i = state.registre.length - 1; i >= 0; i--) {
        var e = state.registre[i];
        h += '<div class="jm-reg"><b>J' + e.jour + '</b><span>' + esc(e.texte) + '</span></div>';
      }
    }
    h += '<div class="sec-h">Ma partie</div>';
    h += '<p class="jm-note-panneau">Graine ' + state.seed +
      ' — l’adresse de cette page rejoue le même monde depuis le premier jour.</p>';
    if (!memoireOk) {
      h += '<p class="jm-raison">Pas de mémoire locale (navigation privée ?) : ' +
        'exporte ta partie pour la garder.</p>';
    }
    h += '<div class="jm-actions">' +
      '<button type="button" class="jm-btn" data-act="sauver">Sauvegarder</button>' +
      '<button type="button" class="jm-btn" data-act="exporter">Exporter (JSON)</button>' +
      '<button type="button" class="jm-btn" data-act="effacer">Effacer mes données</button></div>';
    return h;
  }

  function htmlCarnet() {
    var h = '<div class="sec-h">Carnet</div>';
    if (!state.carnet.length) {
      return h + '<p class="stub">Vide pour l’instant : les concepts s’écrivent ici au ' +
        'moment où la partie te les fait rencontrer, jamais avant.</p>';
    }
    for (var i = state.carnet.length - 1; i >= 0; i--) {
      var c = state.carnet[i];
      h += '<div class="card jm-note"><h3>' + esc(c.titre) + '</h3><p>' + esc(c.texte) +
        '</p><a href="' + esc(c.lien) + '">Approfondir dans Apprendre →</a></div>';
    }
    return h;
  }

  /* ── Le mode plan (§5, §15) : clic sur le meuble PUIS sur la tuile —
     jamais de glisser-déposer, il est infaisable au doigt. Le plan met le
     temps en pause et vit DANS la boîte de dialogue : pas de fenêtre
     flottante nulle part. ── */
  function basculerPlan() {
    if (enPlan) { fermerPlan(); return; }
    if (state.dialogue || finAffichee) return;   // une décision d'abord
    enPlan = true;
    typeChoisi = null;
    propositionRevente = null;
    planMsg = 'Choisis un meuble, puis une tuile — au clic, ou aux coordonnées ci-dessous.';
    $('jm-plan-btn').setAttribute('aria-pressed', 'true');
    $('jm-plan-btn').classList.add('on');
    rendrePlan();
    majBarre();
  }
  function fermerPlan() {
    enPlan = false;
    typeChoisi = null;
    propositionRevente = null;
    selection = null;
    $('jm-plan-btn').setAttribute('aria-pressed', 'false');
    $('jm-plan-btn').classList.remove('on');
    if (!finAffichee) {
      dlgAfficheId = null;
      syncDialogue();
      if (!state.dialogue && !state.fin) rendreRepos();
    }
    majBarre();
  }
  function rendrePlan() {
    var MAISON = window.MAISON;
    arreterFrappe();
    $('jm-dlg-auteur').textContent = 'Mode plan — le temps est en pause';
    $('jm-dlg-texte').textContent = planMsg;
    var h = '';
    if (propositionRevente) {
      /* La revente se confirme ici même : proposer, jamais exécuter sur un
         simple clic de plateau — un doigt qui glisse ne doit rien vendre. */
      h += '<button type="button" class="jm-opt" data-act="revente-oui"><b>1</b><span>Revendre ' +
        esc(propositionRevente.label) + ' pour ' + MAISON.fmtEur(propositionRevente.remb) +
        '</span></button>' +
        '<button type="button" class="jm-opt" data-act="revente-non"><b>2</b><span>Annuler</span></button>';
    } else {
      for (var k in MAISON.MEUBLES) {
        var m = MAISON.MEUBLES[k];
        h += '<button type="button" class="jm-opt' + (typeChoisi === k ? ' on' : '') +
          '" data-meuble="' + k + '"><b>' + esc(m.label) + '</b><span>' + MAISON.fmtEur(m.prix) +
          (m.recurrent ? ' +' + MAISON.fmtEur(m.recurrent) + '/mois' : '') + '</span></button>';
      }
      /* Les coordonnées au clavier : le jeu entier reste jouable sans la
         souris ni le plateau, aménagement compris (§15). */
      h += '<span class="jm-plan-coord"><label>x <input type="number" id="jm-px" min="0" max="' +
        (state.plateau.w - 1) + '" value="' + planXY.x + '"></label>' +
        '<label>y <input type="number" id="jm-py" min="0" max="' + (state.plateau.h - 1) +
        '" value="' + planXY.y + '"></label>' +
        '<button type="button" class="jm-btn" data-act="poser-xy">Poser ici</button></span>';
      var aRevendre = '';
      for (var i = 0; i < state.plateau.meubles.length; i++) {
        var mb = state.plateau.meubles[i];
        if (mb.type === 'fondateur') continue;
        aRevendre += '<button type="button" class="jm-opt" data-revente="' + mb.id + '"><b>' +
          esc(MAISON.MEUBLES[mb.type].label) + '</b><span>(' + mb.x + ',' + mb.y +
          ') · revente ' + MAISON.fmtEur(Math.round(MAISON.MEUBLES[mb.type].prix * 0.5)) +
          '</span></button>';
      }
      h += aRevendre;
    }
    h += '<button type="button" class="jm-btn" data-act="plan-fermer">Fermer<span class="jm-k">Échap</span></button>';
    $('jm-dlg-opts').innerHTML = h;
  }
  function meubleSurTuile(x, y) {
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      var m = state.plateau.meubles[i];
      if (m.x === x && m.y === y) return m;
    }
    return null;
  }
  function meubleParId(id) {
    for (var i = 0; i < state.plateau.meubles.length; i++) {
      if (state.plateau.meubles[i].id === id) return state.plateau.meubles[i];
    }
    return null;
  }
  /* Recopie de la règle de pose du moteur, qui ne l'exporte pas : le fantôme
     doit dire vrai AVANT le clic. Le moteur revérifie de toute façon — un
     fantôme qui mentirait serait un bug d'affichage, jamais une triche. */
  function tuileLibreUI(x, y) {
    if (x < 0 || y < 0 || x >= state.plateau.w || y >= state.plateau.h) return false;
    return meubleSurTuile(x, y) === null;
  }
  function poseOk(type, x, y) {
    var def = window.MAISON.MEUBLES[type];
    if (!def || state.societe.treso < def.prix) return false;
    if (!tuileLibreUI(x, y)) return false;
    var essai = {
      w: state.plateau.w, h: state.plateau.h, porte: state.plateau.porte,
      meubles: state.plateau.meubles.concat([{ id: -1, type: type, x: x, y: y }])
    };
    return window.MAISON.connexiteOk(essai);
  }
  function poser(type, x, y) {
    var r = window.MAISON.poserMeuble(state, type, x, y);
    /* Le refus du moteur s'affiche TEL QUEL : c'est lui qui décide, et ses
       messages sont déjà écrits pour être lus. */
    planMsg = r.ok
      ? window.MAISON.MEUBLES[type].label + ' posé en (' + x + ',' + y + ').'
      : 'Refusé : ' + r.err + '.';
    rendrePlan();
    majBarre();
    majPanneau();
  }
  function proposerRevente(mb) {
    if (mb.type === 'fondateur') {
      planMsg = 'Ton bureau reste — c’est là qu’on vient te chercher.';
      propositionRevente = null;
    } else {
      propositionRevente = {
        id: mb.id,
        label: window.MAISON.MEUBLES[mb.type].label,
        remb: Math.round(window.MAISON.MEUBLES[mb.type].prix * 0.5)
      };
      planMsg = 'Revente à 50 % du prix d’achat — le mobilier d’occasion ne pardonne pas.';
      selection = { x: mb.x, y: mb.y };
    }
    rendrePlan();
  }
  function planClicTuile(t) {
    var mb = meubleSurTuile(t.x, t.y);
    if (mb) { proposerRevente(mb); return; }
    if (!typeChoisi) {
      planMsg = 'Choisis d’abord un meuble dans la palette.';
      rendrePlan();
      return;
    }
    poser(typeChoisi, t.x, t.y);
  }

  /* ── Le plateau : survol, clic, pan à un doigt ───────────────────────── */
  function personneSurTuile(t) {
    for (var i = 0; i < state.equipe.length; i++) {
      var p = state.equipe[i];
      if (Math.round(p.pos.x) === t.x && Math.round(p.pos.y) === t.y) return p;
    }
    return null;
  }
  function montrerContexte(p) {
    var def = window.MAISON.ROLES[p.role];
    var anc = Math.floor((state.jour - p.arriveJour) / window.MAISON.JOURS_PAR_MOIS);
    /* Une phrase VRAIE, tirée de l'état — jamais de la figuration (§3.3). */
    ctxPerso = p.nom + ' — ' + def.label + ', ' +
      (anc < 1 ? 'arrivé ce mois-ci' : anc + ' mois de maison') + '. ' +
      (def.joursParNote ? 'Note en cours : ' + Math.round(p.progression * 100) + ' %. '
        : 'Passe les ordres du fonds. ') +
      'Moral ' + p.moral + '/100. ' + (ETATS[p.etat] || p.etat) + '.';
    ouvrirOnglet('equipe');
  }
  function clicPlateau(px, py) {
    var t = iso.tuileDepuisPixel(px, py);
    if (!t) { if (!enPlan) selection = null; return; }
    if (enPlan) { planClicTuile(t); return; }
    if (state.dialogue || finAffichee) return;  // une décision attend : le plateau se tait
    var p = personneSurTuile(t);
    if (p) {
      selection = { x: t.x, y: t.y };
      montrerContexte(p);
    } else {
      selection = null;
    }
  }

  /* ── Annonces lecteur d'écran : sobres, jamais un fil continu (§15) ──── */
  function annoncer(texte) { $('jm-annonce').textContent = texte; }

  /* ── Branchements — une seule fois, au boot ──────────────────────────── */
  function brancher() {
    var cv = $('jm-jeu');

    /* Pan à un doigt : au-delà de 8 px de glisse, c'est un déplacement de
       caméra ; en deçà, un tap. Le même code sert à la souris. */
    var pt = { actif: false, x0: 0, y0: 0, panX0: 0, panY0: 0, bouge: false };
    cv.addEventListener('pointerdown', function (e) {
      pt.actif = true; pt.bouge = false;
      pt.x0 = e.clientX; pt.y0 = e.clientY;
      pt.panX0 = panX; pt.panY0 = panY;
      if (cv.setPointerCapture) { try { cv.setPointerCapture(e.pointerId); } catch (err) { } }
    });
    cv.addEventListener('pointermove', function (e) {
      var r = cv.getBoundingClientRect();
      survol = iso.tuileDepuisPixel(e.clientX - r.left, e.clientY - r.top);
      if (!pt.actif) return;
      var dx = e.clientX - pt.x0, dy = e.clientY - pt.y0;
      if (!pt.bouge && Math.abs(dx) + Math.abs(dy) > 8) pt.bouge = true;
      if (pt.bouge) {
        panX = pt.panX0 + dx; panY = pt.panY0 + dy;
        iso.definirPan(panX, panY);
      }
    });
    cv.addEventListener('pointerup', function (e) {
      if (pt.actif && !pt.bouge) {
        var r = cv.getBoundingClientRect();
        clicPlateau(e.clientX - r.left, e.clientY - r.top);
      }
      pt.actif = false;
    });
    cv.addEventListener('pointerleave', function () { survol = null; pt.actif = false; });

    /* La boîte de dialogue : boutons délégués + le clic « suivant ». */
    $('jm-dlg').addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button') : null;
      if (b) {
        if (b.hasAttribute('data-opt')) { choisir(+b.getAttribute('data-opt')); return; }
        if (b.hasAttribute('data-meuble')) {
          typeChoisi = b.getAttribute('data-meuble');
          propositionRevente = null;
          planMsg = window.MAISON.MEUBLES[typeChoisi].label +
            ' : clique une tuile libre — le fantôme dit si la pose passera.';
          rendrePlan();
          return;
        }
        if (b.hasAttribute('data-revente')) {
          var mb = meubleParId(+b.getAttribute('data-revente'));
          if (mb) proposerRevente(mb);
          return;
        }
        var act = b.getAttribute('data-act');
        if (act === 'poser-xy') {
          var x = borner($('jm-px') ? $('jm-px').value : 0, 0, state.plateau.w - 1);
          var y = borner($('jm-py') ? $('jm-py').value : 0, 0, state.plateau.h - 1);
          planXY.x = x; planXY.y = y;
          if (typeChoisi) poser(typeChoisi, x, y);
          else { planMsg = 'Choisis d’abord un meuble dans la palette.'; rendrePlan(); }
        } else if (act === 'revente-oui') {
          var r = window.MAISON.retirerMeuble(state, propositionRevente.id);
          planMsg = r.ok ? 'Revendu : +' + window.MAISON.fmtEur(r.remboursement) + '.'
            : 'Refusé : ' + r.err + '.';
          propositionRevente = null;
          selection = null;
          rendrePlan();
          majBarre();
          majPanneau();
        } else if (act === 'revente-non') {
          propositionRevente = null;
          selection = null;
          planMsg = 'Rien de vendu.';
          rendrePlan();
        } else if (act === 'plan-fermer') {
          fermerPlan();
        }
        return;
      }
      /* Clic dans la boîte : pendant la frappe, tout arrive d'un coup (§3.2) ;
         ensuite, s'il n'y a qu'une réponse possible, le clic vaut « suivant ». */
      if (frappe.active) { completerFrappe(); return; }
      if (finAffichee || enPlan) return;
      if (state.dialogue && state.dialogue.options.length === 1) choisir(0);
    });
    $('jm-dlg').addEventListener('change', function (e) {
      if (e.target.id === 'jm-px') planXY.x = borner(e.target.value, 0, state.plateau.w - 1);
      if (e.target.id === 'jm-py') planXY.y = borner(e.target.value, 0, state.plateau.h - 1);
    });

    /* Le panneau : boutons et radios délégués — le contenu est reconstruit
       à chaque rafraîchissement, les écouteurs ne doivent PAS l'être. */
    $('jm-corps').addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-act]') : null;
      if (!b) return;
      var act = b.getAttribute('data-act');
      if (act === 'recruter') {
        var r = window.MAISON.lancerRecrutement(state, b.getAttribute('data-role'));
        if (!r.ok) annoncer('Recrutement impossible : ' + r.err + '.');
        majPanneau();
      } else if (act === 'sauver') {
        sauvegarder(true);
        annoncer(memoireOk ? 'Partie sauvegardée.' : 'Sauvegarde impossible (navigation privée ?).');
        majPanneau();
      } else if (act === 'exporter') {
        exporter();
      } else if (act === 'effacer') {
        effacer();
      }
    });
    $('jm-corps').addEventListener('change', function (e) {
      if (e.target && e.target.name === 'jm-abo') {
        window.MAISON.changerAbonnement(state, e.target.value);
        majPanneau();
      }
    });

    var tabs = document.querySelectorAll('.jm-tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () {
        ouvrirOnglet(this.getAttribute('data-tab'));
      });
    }
    $('jm-depli').addEventListener('click', function () { basculerFeuille(); });

    $('jm-echelle').addEventListener('click', function () {
      echelle = echelle === 1 ? 2 : 1;
      iso.definirEchelle(echelle);
      iso.redimensionner();
      this.textContent = '×' + echelle;
    });
    $('jm-plan-btn').addEventListener('click', basculerPlan);

    /* Clavier de bout en bout (§15). Un bouton focalisé garde Espace/Entrée
       pour lui : le navigateur sait déjà cliquer, on ne double pas. */
    document.addEventListener('keydown', function (e) {
      if (!state || e.metaKey || e.ctrlKey || e.altKey) return;
      var cible = e.target;
      if (cible && (cible.tagName === 'INPUT' || cible.tagName === 'TEXTAREA' ||
        cible.tagName === 'SELECT')) return;
      var k = e.key;
      if (k === ' ' || k === 'Enter') {
        if (cible && cible.closest && cible.closest('button')) return;
        e.preventDefault();
        if (frappe.active) { completerFrappe(); return; }
        if (finAffichee) { choisir(0); return; }
        if (state.dialogue) {
          /* Une seule issue : Espace avance. Plusieurs : on choisit au
             chiffre, jamais à l'aveugle. */
          if (state.dialogue.options.length === 1) choisir(0);
          return;
        }
        if (enPlan) return;
        basculerPause();
      } else if (k >= '1' && k <= '4') {
        if (frappe.active) { completerFrappe(); return; }
        if (finAffichee) { if (k === '1') choisir(0); return; }
        if (state.dialogue) choisir(+k - 1);
      } else if (k === 'p' || k === 'P') {
        e.preventDefault();
        basculerPlan();
      } else if (k === 'c' || k === 'C') {
        ouvrirOnglet('carnet');
      } else if (k === 'l' || k === 'L') {
        ouvrirOnglet('registre');
      } else if (k === 'v' || k === 'V') {
        cyclerVitesse();
      } else if (k === 'Escape' && enPlan) {
        fermerPlan();
      }
    });

    $('jm-barre').addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-vit]') : null;
      if (!b) return;
      var v = +b.getAttribute('data-vit');
      if (v === 0) enPause = true;
      else { vitesse = v; enPause = false; }
      majBarre();
    });

    /* Onglet caché : la boucle s'arrête (rien à montrer, rien à brûler) et
       la partie se sauve — c'est la fermeture d'onglet la plus fréquente. */
    document.addEventListener('visibilitychange', function () {
      if (!state) return;
      if (document.hidden) { arreterBoucle(); sauvegarder(false); }
      else demarrerBoucle();
    });

    window.addEventListener('resize', function () { if (iso) iso.redimensionner(); });
  }
})();
