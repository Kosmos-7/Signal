/* Signal — sommaire de sections : surlignage de la section active au défilement (scroll-spy).
   Le saut vers une section utilise l'ancre native (#id) + scroll-behavior/scroll-margin en CSS.
   Requiert <nav class="toc"> avec des liens <a href="#id">. S'auto-initialise. */
(function () {
  var links = [].slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (!links.length) return;
  var pairs = links
    .map(function (a) { return { a: a, el: document.getElementById(a.getAttribute('href').slice(1)) }; })
    .filter(function (p) { return p.el; });
  if (!pairs.length) return;

  function setActive(a) {
    links.forEach(function (l) { l.classList.toggle('active', l === a); });
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
})();
