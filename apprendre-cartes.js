/* Signal — « Apprendre » : un catalogue de cartes, une section à la fois.

   CE QUE CE FICHIER REMPLACE. La page portait douze sections dans un seul
   rouleau de près de deux mille lignes, et un sommaire pour s'y déplacer :
   une colonne fixe à gauche au-dessus de 1300 px, une barre dépliante en
   dessous (signal-toc.js). Le sommaire disait où aller, il ne montrait
   jamais où l'on allait — douze libellés de trois mots, et les douze images
   d'ouverture, déjà présentes dans la page, ne servaient qu'une fois qu'on
   était arrivé.

   CE QU'IL FAIT À LA PLACE. Les mêmes douze sections deviennent douze cartes
   illustrées, rangées en deux rails qui défilent à l'horizontale, à la
   souris comme au doigt. Une carte ouvre SA section, seule : la page cesse
   d'être un rouleau et devient un chapitre à la fois. À la fin du chapitre,
   les cartes reviennent, la suivante en tête, pour enchaîner sans remonter.

   AUCUNE DONNÉE N'EST RECOPIÉE. Le numéro, le titre et l'image d'une carte
   sont LUS dans la section qu'elle ouvre (.section-label, .section-title,
   .sec-tete img). C'est la règle que suivait déjà le sommaire mobile : deux
   listes écrites à la main finissent toujours par diverger, et ici la
   deuxième aurait divergé au premier passage de tools/photos_apprendre.py,
   qui réécrit les images et leurs légendes sans rien savoir des cartes.
   Ajouter une section reste donc un travail d'un seul endroit : la section
   elle-même, plus son ancre dans le `data-sections` du rail qui l'accueille.

   SI CE SCRIPT TOMBE, LA PAGE RESTE LISIBLE. Le masquage des sections vient
   d'une classe `jsc` posée par un script en tête de document ; tout ce qui
   suit est sous `try`, et le moindre échec retire la classe : la page
   redevient le rouleau complet de douze sections. Un lecteur sans
   JavaScript, lui, ne voit jamais la classe et lit la page entière. */
(function () {
  var racine = document.documentElement;
  try {
    var sections = [].slice.call(
      document.querySelectorAll('main .section-block[id]'));
    if (!sections.length) throw new Error('aucune section à mettre en carte');

    /* La fiche d'une carte est lue DANS sa section. Une section sans image
       reste légitime : la carte se replie sur un cartouche sans photo plutôt
       que de disparaître du catalogue. */
    var chapitres = sections.map(function (s) {
      var img = s.querySelector('.sec-tete img');
      var num = s.querySelector('.section-label');
      var tit = s.querySelector('.section-title');
      return {
        id: s.id,
        el: s,
        src: img ? img.getAttribute('src') : '',
        num: num ? num.textContent.trim() : '',
        titre: tit ? tit.textContent.trim() : s.id
      };
    });
    var parId = {};
    chapitres.forEach(function (c) { parId[c.id] = c; });

    // ── LA CARTE ────────────────────────────────────────────────────────
    // L'image est décorative ICI : le numéro et le titre sont juste en
    // dessous, en texte. Un alt repris de la section ferait annoncer deux
    // fois la même carte par un lecteur d'écran.
    function carte(c, badge) {
      var a = document.createElement('a');
      a.className = 'carte';
      a.href = '#' + c.id;
      a.setAttribute('data-id', c.id);
      var vue = document.createElement('span');
      vue.className = 'carte-vue';
      if (c.src) {
        var im = document.createElement('img');
        im.src = c.src;
        im.alt = '';
        im.loading = 'lazy';
        im.width = 1700;
        im.height = 531;
        im.draggable = false;
        vue.appendChild(im);
      }
      if (badge) {
        var b = document.createElement('span');
        b.className = 'carte-b';
        b.textContent = badge;
        vue.appendChild(b);
      }
      var n = document.createElement('span');
      n.className = 'carte-n';
      n.textContent = c.num;
      var t = document.createElement('span');
      t.className = 'carte-t';
      t.textContent = c.titre;
      a.appendChild(vue);
      a.appendChild(n);
      a.appendChild(t);
      return a;
    }

    // ── LE RAIL ─────────────────────────────────────────────────────────
    /* Trois façons de le parcourir, parce qu'aucune ne couvre tout le monde :
       le doigt (défilement natif, on ne s'en mêle pas), la souris qui glisse
       (pointer events, ci-dessous), et deux flèches pour qui ne glisse pas.
       Les flèches sautent d'un nombre ENTIER de cartes : un demi-vignette
       coupée au bord n'est pas un repère, c'est un doute. */
    function garnir(rail, liste, badgePremiere) {
      var boite = document.createElement('div');
      boite.className = 'rail-c';
      var gauche = document.createElement('button');
      gauche.type = 'button';
      gauche.className = 'rail-f rail-g';
      gauche.setAttribute('aria-label', 'Voir les cartes précédentes');
      gauche.innerHTML = '<span aria-hidden="true">‹</span>';
      var droite = document.createElement('button');
      droite.type = 'button';
      droite.className = 'rail-f rail-d';
      droite.setAttribute('aria-label', 'Voir les cartes suivantes');
      droite.innerHTML = '<span aria-hidden="true">›</span>';
      var piste = document.createElement('div');
      piste.className = 'rail-p';
      liste.forEach(function (c, i) {
        piste.appendChild(carte(c, i === 0 ? badgePremiere : ''));
      });
      boite.appendChild(gauche);
      boite.appendChild(piste);
      boite.appendChild(droite);
      rail.appendChild(boite);

      function pas() {
        var c = piste.querySelector('.carte');
        if (!c) return piste.clientWidth;
        var large = c.getBoundingClientRect().width + 14;   // 14 = gap du CSS
        return Math.max(1, Math.floor(piste.clientWidth / large)) * large;
      }
      function bouger(sens) {
        // Le glissement animé est une animation comme une autre : qui a
        // demandé moins de mouvement au système reçoit un saut net.
        var doux = !matchMedia('(prefers-reduced-motion: reduce)').matches;
        piste.scrollBy({ left: sens * pas(), behavior: doux ? 'smooth' : 'auto' });
      }
      gauche.addEventListener('click', function () { bouger(-1); });
      droite.addEventListener('click', function () { bouger(1); });

      /* Une flèche qui ne mène nulle part est un bouton mort : les deux
         disparaissent quand le rail touche son bord, et le rail entier
         s'efface s'il tient déjà en entier à l'écran. */
      function etat() {
        var reste = piste.scrollWidth - piste.clientWidth;
        var mobile = reste > 4;
        boite.classList.toggle('fixe', !mobile);
        gauche.hidden = !mobile || piste.scrollLeft <= 2;
        droite.hidden = !mobile || piste.scrollLeft >= reste - 2;
      }
      piste.addEventListener('scroll', etat, { passive: true });
      /* MESURER LA PISTE ET NON LA FENÊTRE. Un rail masqué mesure zéro : les
         rangées du catalogue passent par là chaque fois qu'on ouvre une
         section, et si l'on ne remesurait qu'au `resize` de la fenêtre, elles
         reviendraient sans flèches, persuadées de tenir en entier.
         `ResizeObserver` se déclenche aussi quand la piste repasse de zéro à
         sa largeur réelle, donc au retour au catalogue. */
      var ro = null;
      if (window.ResizeObserver) {
        ro = new ResizeObserver(etat);
        ro.observe(piste);
      } else {
        addEventListener('resize', etat);
      }
      // Le rail du bas est reconstruit à chaque chapitre : sans ce décrochage,
      // douze navigations laisseraient douze observateurs derrière elles,
      // chacun mesurant un rail qui n'est plus dans la page.
      boite.detacher = function () {
        if (ro) ro.disconnect(); else removeEventListener('resize', etat);
      };
      etat();

      /* GLISSER À LA SOURIS. Le doigt est exclu volontairement : le
         défilement natif d'un écran tactile a de l'inertie et une accroche
         que rien de réécrit à la main n'égale, et s'y substituer le dégrade.
         Le glissé se termine par un clic que le navigateur envoie au lien
         survolé : sans le garde-fou `bouge`, chaque déplacement du rail
         ouvrirait la carte sur laquelle on relâche. */
      var depart = null, origine = 0, bouge = false;
      piste.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'touch' || e.button !== 0) return;
        depart = e.clientX;
        origine = piste.scrollLeft;
        bouge = false;
      });
      piste.addEventListener('pointermove', function (e) {
        if (depart === null) return;
        var d = e.clientX - depart;
        if (!bouge && Math.abs(d) > 5) {
          bouge = true;
          piste.classList.add('prise');
          try { piste.setPointerCapture(e.pointerId); } catch (err) { /* rien */ }
        }
        if (bouge) {
          piste.scrollLeft = origine - d;
          e.preventDefault();
        }
      });
      function relacher() {
        depart = null;
        piste.classList.remove('prise');
      }
      piste.addEventListener('pointerup', relacher);
      piste.addEventListener('pointercancel', relacher);
      piste.addEventListener('click', function (e) {
        if (bouge) { e.preventDefault(); e.stopPropagation(); }
      }, true);
      piste.addEventListener('dragstart', function (e) { e.preventDefault(); });

      // Amener une carte sous les yeux sans toucher au défilement VERTICAL
      // de la page : scrollIntoView() ferait les deux.
      rail.montrer = function (id) {
        var c = piste.querySelector('.carte[data-id="' + id + '"]');
        if (!c) return;
        var cible = c.offsetLeft - (piste.clientWidth - c.offsetWidth) / 2;
        piste.scrollLeft = Math.max(0, cible);
        etat();
      };
      return rail;
    }

    // ── LE CATALOGUE ────────────────────────────────────────────────────
    /* Les groupes éditoriaux (« La bourse », « Signal en application »)
       restent écrits dans la page, comme ils l'étaient dans le sommaire.
       Une section oubliée d'un `data-sections` n'est pas perdue pour
       autant : elle rejoint le dernier rail. Un chapitre injoignable serait
       la seule panne vraiment grave de ce fichier. */
    var rails = [].slice.call(document.querySelectorAll('.hub .rail'));
    var places = {};
    rails.forEach(function (r) {
      var ids = (r.getAttribute('data-sections') || '').split(/\s+/)
        .filter(function (x) { return x && parId[x]; });
      ids.forEach(function (x) { places[x] = 1; });
      r.liste = ids.map(function (x) { return parId[x]; });
    });
    if (rails.length) {
      var oublies = chapitres.filter(function (c) { return !places[c.id]; });
      rails[rails.length - 1].liste =
        rails[rails.length - 1].liste.concat(oublies);
      rails.forEach(function (r) { garnir(r, r.liste); });
    }

    // ── LE FIL (haut de chapitre) ET LA SUITE (bas de chapitre) ─────────
    var fil = document.querySelector('.fil');
    var retour = null, position = null;
    if (fil) {
      retour = document.createElement('a');
      retour.className = 'fil-r';
      retour.href = '#';
      retour.innerHTML = '<span aria-hidden="true">←</span> Toutes les sections';
      position = document.createElement('span');
      position.className = 'fil-p';
      fil.appendChild(retour);
      fil.appendChild(position);
    }

    var suite = document.querySelector('.suite');
    var railSuite = null;
    if (suite) {
      var entete = document.createElement('div');
      entete.className = 'rail-h';
      var k = document.createElement('span');
      k.className = 'rail-k';
      k.textContent = 'La suite';
      var s = document.createElement('span');
      s.className = 'rail-s';
      s.textContent = 'Reprenez où vous voulez, chaque section se lit seule.';
      entete.appendChild(k);
      entete.appendChild(s);
      railSuite = document.createElement('section');
      railSuite.className = 'rail';
      railSuite.appendChild(entete);
      suite.appendChild(railSuite);
    }

    // ── LE ROUTEUR ──────────────────────────────────────────────────────
    /* Une ancre, une vue. `#s5` ouvre la cinquième section, tout le reste
       ramène au catalogue : un signet périmé (`#s99`) affiche les cartes au
       lieu d'une page blanche. Les liens gardent leur `href="#s5"`, donc le
       clic milieu, le « copier l'adresse » et le bouton Précédent du
       navigateur fonctionnent sans une ligne de code. */
    var hubY = 0;
    var courant = null;
    var titrePage = document.title;

    function ouvrir(c) {
      chapitres.forEach(function (x) {
        x.el.classList.toggle('ouvert', !!c && x === c);
      });
      racine.classList.toggle('vue-chapitre', !!c);
      /* Le titre du document suit la section ouverte : c'est ce que lit
         l'onglet du navigateur, et surtout l'historique. Douze entrées
         « Apprendre, Signal » ne se distinguent pas les unes des autres. */
      document.title = c ? c.titre + ', ' + titrePage : titrePage;
      if (c && position) {
        var i = chapitres.indexOf(c) + 1;
        position.textContent = 'Section ' + i + ' sur ' + chapitres.length;
      }
      if (c && railSuite) {
        // La suivante d'abord, puis les autres dans l'ordre, en repassant
        // par le début : à la douzième, « la suite » est la première.
        var i2 = chapitres.indexOf(c);
        var ordre = [];
        for (var j = 1; j < chapitres.length; j++) {
          ordre.push(chapitres[(i2 + j) % chapitres.length]);
        }
        var vieux = railSuite.querySelector('.rail-c');
        if (vieux) {
          if (vieux.detacher) vieux.detacher();
          vieux.remove();
        }
        garnir(railSuite, ordre, 'À suivre');
      }
      if (!c) {
        rails.forEach(function (r) {
          if (courant && r.montrer) r.montrer(courant);
        });
      }
      courant = c ? c.id : courant;
    }

    function rendre() {
      var id = location.hash.replace(/^#/, '');
      var c = parId[id] || null;
      var avant = racine.classList.contains('vue-chapitre');
      if (!c && avant) {
        ouvrir(null);
        // Retour au catalogue : on le retrouve là où on l'avait quitté.
        scroller(hubY);
        return;
      }
      if (c && !avant) hubY = scrollY;
      ouvrir(c);
      if (c) scroller(0);
    }

    function scroller(y) {
      try { scrollTo({ top: y, behavior: 'instant' }); }
      catch (e) { scrollTo(0, y); }
    }

    /* OUVRIR `#s3` DOIT OUVRIR LE HAUT DE LA SECTION 3, PAS SON MILIEU. Le
       navigateur, lui, voit une ancre et veut l'amener sous les yeux : au
       chargement il ne trouve rien (la section est encore masquée), puis il
       réessaie une fois la page complète, cette fois avec succès, et la page
       s'ouvrait quatre-vingts pixels trop bas, le fil de lecture coincé sous
       l'en-tête. On lui retire donc la main : plus de restauration
       automatique, et un dernier recadrage après `load`, le seul moment où
       l'on est sûr d'avoir le dernier mot. */
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    addEventListener('hashchange', rendre);
    addEventListener('load', function () {
      if (racine.classList.contains('vue-chapitre')) scroller(0);
    });
    rendre();
  } catch (e) {
    // Le rouleau complet vaut mieux qu'une page vide.
    racine.classList.remove('jsc');
    if (window.console) console.error('catalogue Apprendre :', e);
  }
})();
