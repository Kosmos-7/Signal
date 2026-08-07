/* Signal — sommaire de sections.

   DEUX RENDUS, UNE SEULE SOURCE. Le balisage d'origine est le même partout :
   un <nav class="toc"> de liens <a href="#id">, écrit à la main dans
   apprendre.html et portfolio.html. Sur grand écran il vit en colonne fixe à
   gauche ; sous 1300 px il était purement et simplement CACHÉ, et les pages
   devenaient le « bloc de texte qu'on scrolle » signalé par le propriétaire
   le 07/08 — apprendre.html fait douze sections et près de deux mille lignes.

   Le rendu mobile est donc CONSTRUIT ICI, à partir des mêmes liens : une
   barre collante sous le header qui dit toujours où l'on est, et qui s'ouvre
   d'une tape sur la liste complète. Rien à recopier dans les pages : ajouter
   une section au <nav class="toc"> suffit, les deux rendus suivent.

   Le scroll-spy alimente les deux : c'est lui qui écrit le libellé de la
   barre. S'auto-initialise. */
(function () {
  var toc = document.querySelector('.toc');
  var links = [].slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (!links.length) return;
  var pairs = links
    .map(function (a) { return { a: a, el: document.getElementById(a.getAttribute('href').slice(1)) }; })
    .filter(function (p) { return p.el; });
  if (!pairs.length) return;

  // ── Rendu mobile : barre collante + feuille dépliable ──────────────────
  // Construite à partir des liens existants, jamais d'un second sommaire
  // écrit à la main — deux listes finiraient par diverger.
  var bar = document.createElement('div');
  bar.className = 'tocm';
  bar.innerHTML =
    '<button class="tocm-b" type="button" aria-expanded="false">' +
      '<span class="tocm-k">Sommaire</span>' +
      '<span class="tocm-v"></span>' +
      '<span class="tocm-c" aria-hidden="true">▾</span>' +
    '</button>' +
    '<div class="tocm-p" hidden></div>';
  var bouton = bar.querySelector('.tocm-b');
  var valeur = bar.querySelector('.tocm-v');
  var panneau = bar.querySelector('.tocm-p');

  // Les entrées du panneau CLONENT les liens : même libellé, même ancre, même
  // numéro. Un groupe de tête (« La bourse », « Signal en application ») est
  // repris tel quel pour ne pas aplatir la structure éditoriale.
  if (toc) {
    [].slice.call(toc.children).forEach(function (n) {
      if (n.classList.contains('toc-h')) {
        var h = document.createElement('div');
        h.className = 'tocm-h';
        h.textContent = n.textContent;
        panneau.appendChild(h);
      } else if (n.tagName === 'A') {
        var a = document.createElement('a');
        a.href = n.getAttribute('href');
        a.innerHTML = n.innerHTML;
        panneau.appendChild(a);
      }
    });
  }

  function ouvrir(o) {
    bouton.setAttribute('aria-expanded', o ? 'true' : 'false');
    panneau.hidden = !o;
    bar.classList.toggle('on', o);
  }
  bouton.addEventListener('click', function () {
    ouvrir(bouton.getAttribute('aria-expanded') !== 'true');
  });
  // Une tape sur une entrée ferme la feuille : le saut est natif (ancre +
  // scroll-margin), on n'a qu'à ne pas rester devant.
  panneau.addEventListener('click', function (e) {
    if (e.target.closest('a')) ouvrir(false);
  });
  // Une tape à côté referme aussi — sinon la feuille masque la page qu'on
  // vient d'atteindre sur les petits écrans.
  document.addEventListener('click', function (e) {
    if (!bar.contains(e.target)) ouvrir(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') ouvrir(false);
  });

  /* PLACÉE JUSTE APRÈS LE HEADER, PAS EN FIN DE <body>. `position:sticky` ne
     colle que dans le flux qui la suit : appendue au corps, la barre était le
     dernier élément du document et n'apparaissait qu'une fois arrivé en bas —
     exactement l'inverse du service rendu. */
  var entete = document.querySelector('header');
  if (entete && entete.parentNode) entete.parentNode.insertBefore(bar, entete.nextSibling);
  else document.body.insertBefore(bar, document.body.firstChild);

  /* Le décalage haut est MESURÉ, pas codé en dur : le header fait 58 px sous
     700 px de large et 72 au-dessus, et ces valeurs bougeront. Deux variables
     CSS suffisent — l'une pour coller la barre sous le header, l'autre pour
     que les sauts d'ancre dégagent les deux. */
  function mesurer() {
    var h = entete ? Math.round(entete.getBoundingClientRect().height) : 0;
    var b = Math.round(bar.getBoundingClientRect().height) || 40;
    var r = document.documentElement.style;
    r.setProperty('--tocm-top', h + 'px');
    r.setProperty('--tocm-off', (h + b + 8) + 'px');
  }
  mesurer();
  addEventListener('resize', mesurer);

  function setActive(a) {
    links.forEach(function (l) { l.classList.toggle('active', l === a); });
    var h = a.getAttribute('href');
    [].slice.call(panneau.querySelectorAll('a')).forEach(function (l) {
      l.classList.toggle('active', l.getAttribute('href') === h);
    });
    // Le libellé de la barre = le texte du lien SANS son numéro, qui vit dans
    // un <span class="tn"> à part.
    var tn = a.querySelector('.tn');
    valeur.textContent = (tn ? tn.textContent + ' · ' : '') +
      a.textContent.replace(tn ? tn.textContent : '', '').trim();
  }

  // Feedback immédiat au clic (le défilement reste géré nativement par l'ancre)
  links.forEach(function (a) {
    a.addEventListener('click', function () { setActive(a); });
  });

  // Scroll-spy : la section dont le haut franchit ~25 % du viewport devient active
  var obs = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) {
        var p = pairs.find(function (x) { return x.el === en.target; });
        if (p) setActive(p.a);
      }
    });
  }, { rootMargin: '-25% 0px -65% 0px', threshold: 0 });
  pairs.forEach(function (p) { obs.observe(p.el); });

  // Avant le premier franchissement, la barre afficherait un libellé vide :
  // on l'amorce sur la première section.
  setActive(pairs[0].a);
})();
