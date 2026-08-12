/* maison-iso.js — La Maison : le RENDU isométrique, et rien que lui.
   ============================================================================
   Ce fichier ne décide RIEN : il lit l'état du moteur (maison-moteur.js) et le
   dessine. Pas de Math.random() (un test le grep), pas d'horloge murale : le
   temps arrive en paramètre (tMs), fourni par l'appelant — même état + même
   tMs = même image au pixel, ce qui rend le rendu comparable et débogable.

   Tout est GÉOMÉTRIE (§4 du prompt) : aucun fichier image. Un meuble est un
   empilement de boîtes isométriques à trois faces (dessus clair, gauche moyen,
   droite sombre), un personnage un corps, une tête, deux jambes. Si des
   sprites arrivent un jour, seules les fonctions de DESSINS changent — la
   projection, le tri et l'animation restent.

   Le fichier entier se charge sous node SANS DOM : window/document ne sont
   touchés que dans creer(), jamais au niveau module — c'est ce qui rend
   MaisonIso.astar testable en CI sans navigateur. */
(function () {
  'use strict';

  /* ── La tuile de référence (§3.1) : 32 × 16 px à l'échelle 1 ──
     px = (x − y)·TW/2 + origine ; py = (x + y)·TH/2 + origine. Deux échelles
     seulement (×1, ×2) : le zoom libre doublerait le travail pour rien. */
  var TW = 32, TH = 16;
  var VITESSE_TUILES_S = 2.2;      // marche (§3.3) : lisible sans être lente

  /* ── Palette du décor (§4.1) — l'exception argumentée au design system.
     Sept teintes fixes, sombres et désaturées, dérivées du fond #06060b. Ces
     constantes sont le REPLI : si :root déclare des variables --jm-*, elles
     gagnent (creer() les lit) — le CSS reste la source de vérité quand il y a
     un DOM, et node n'a pas besoin de DOM pour charger le fichier. */
  var TEINTES_DEFAUT = {
    sol: '#12141d', cloison: '#1a1e2b', bois: '#2b2620', metal: '#232733',
    papier: '#3a3d4d', verdure: '#1e2f26', verre: '#1d2a38'
  };
  /* Le SEUL droit à une couleur vive : l'accent --ac, pour ce qui compte —
     sélection, survol, bulle d'attente, arc de progression, trait d'écran.
     --green et --red n'existent pas ici : réservés au P&L factuel chiffré. */
  var ACCENT = '#74b6df';
  function accentA(a) { return 'rgba(116,182,223,' + a + ')'; }

  function hexVersRgb(hex) {
    var m = /^#([0-9a-f]{6})$/i.exec(String(hex).trim());
    if (!m) return null;
    var n = parseInt(m[1], 16);
    return [n >> 16 & 255, n >> 8 & 255, n & 255];
  }
  /* Les trois valeurs d'éclairage d'une teinte sont CALCULÉES (dessus ×1.35,
     gauche ×0.95, droite ×0.62), jamais écrites à la main : changer une
     matière = changer UNE valeur, et l'éclairage suit tout seul. */
  function multiplier(c, k) {
    return 'rgb(' + Math.min(255, Math.round(c[0] * k)) + ',' +
      Math.min(255, Math.round(c[1] * k)) + ',' +
      Math.min(255, Math.round(c[2] * k)) + ')';
  }
  function eclairer(hex) {
    var c = hexVersRgb(hex) || [128, 128, 128];
    return { dessus: multiplier(c, 1.35), gauche: multiplier(c, 0.95), droite: multiplier(c, 0.62) };
  }

  /* ── A* sur la grille du plateau ───────────────────────────────────────
     Fonction PURE (testée sous node) : grille = {w, h, bloquee(x,y)}. Les
     pas sont cardinaux, l'heuristique Manhattan est donc exacte à un facteur
     près — jamais surestimante, le chemin trouvé est optimal. Deux libertés
     voulues : le DÉPART peut être une tuile bloquée (on est assis au poste,
     il faut bien en partir), et l'ARRIVÉE aussi (aller à un meuble, c'est
     arriver dessus : elle n'est acceptée que comme dernier pas). */
  function astar(grille, depart, arrivee) {
    if (!grille || !depart || !arrivee) return null;
    var w = grille.w, h = grille.h;
    function dedans(x, y) { return x >= 0 && y >= 0 && x < w && y < h; }
    if (!dedans(depart.x, depart.y) || !dedans(arrivee.x, arrivee.y)) return null;
    if (depart.x === arrivee.x && depart.y === arrivee.y) {
      return [{ x: depart.x, y: depart.y }];
    }
    /* Tas binaire minimal sur f = g + h : sur un plateau 12 × 9 une liste
       triée suffirait, mais le tas tient en douze lignes et ne trahira pas
       le jour où le plateau grandit. */
    var tas = [];
    function pousser(f, x, y) {
      tas.push([f, x, y]);
      var i = tas.length - 1;
      while (i > 0) {
        var p = (i - 1) >> 1;
        if (tas[p][0] <= tas[i][0]) break;
        var t = tas[p]; tas[p] = tas[i]; tas[i] = t; i = p;
      }
    }
    function retirer() {
      var min = tas[0], fin = tas.pop();
      if (tas.length) {
        tas[0] = fin;
        var i = 0;
        for (;;) {
          var a = 2 * i + 1, b = 2 * i + 2, m = i;
          if (a < tas.length && tas[a][0] < tas[m][0]) m = a;
          if (b < tas.length && tas[b][0] < tas[m][0]) m = b;
          if (m === i) break;
          var t = tas[m]; tas[m] = tas[i]; tas[i] = t; i = m;
        }
      }
      return min;
    }
    function manhattan(x, y) { return Math.abs(x - arrivee.x) + Math.abs(y - arrivee.y); }
    var idx = function (x, y) { return y * w + x; };
    var g = {}, parent = {}, clos = {};
    var PAS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    g[idx(depart.x, depart.y)] = 0;
    pousser(manhattan(depart.x, depart.y), depart.x, depart.y);
    while (tas.length) {
      var n = retirer();
      var x = n[1], y = n[2], k = idx(x, y);
      if (clos[k]) continue;
      clos[k] = true;
      if (x === arrivee.x && y === arrivee.y) {
        var chemin = [{ x: x, y: y }];
        while (parent[k] !== undefined) {
          k = parent[k];
          chemin.push({ x: k % w, y: (k / w) | 0 });
        }
        chemin.reverse();
        return chemin;
      }
      for (var i = 0; i < 4; i++) {
        var nx = x + PAS[i][0], ny = y + PAS[i][1];
        if (!dedans(nx, ny)) continue;
        var estArrivee = nx === arrivee.x && ny === arrivee.y;
        if (!estArrivee && grille.bloquee(nx, ny)) continue; // l'arrivée-meuble reste permise
        var nk = idx(nx, ny);
        if (clos[nk]) continue;
        var cout = g[k] + 1;
        if (g[nk] === undefined || cout < g[nk]) {
          g[nk] = cout;
          parent[nk] = k;
          pousser(cout + manhattan(nx, ny), nx, ny);
        }
      }
    }
    return null;
  }

  /* ── Le rendu ──────────────────────────────────────────────────────────
     Tout ce qui touche au DOM vit ici, dans la fermeture de creer(). */
  function creer(canvas) {
    var ctx = canvas.getContext('2d');

    /* La palette effective : les défauts JS, surchargés par --jm-* si la page
       les déclare. Lu UNE fois à la création — la palette du décor ne change
       pas en cours de partie, inutile d'interroger le CSS à chaque image. */
    var teintes = {}, faces = {}, k;
    for (k in TEINTES_DEFAUT) teintes[k] = TEINTES_DEFAUT[k];
    if (typeof document !== 'undefined' && typeof getComputedStyle !== 'undefined') {
      var cs = getComputedStyle(document.documentElement);
      for (k in TEINTES_DEFAUT) {
        var v = cs.getPropertyValue('--jm-' + k).trim();
        if (v && hexVersRgb(v)) teintes[k] = v;
      }
    }
    for (k in teintes) faces[k] = eclairer(teintes[k]);

    var echelle = 1, panX = 0, panY = 0, dpr = 1;
    var cssW = 0, cssH = 0;
    var origineX = 0, origineY = 0;
    var plateauW = 8, plateauH = 6;   // repli avant le premier dessiner()

    /* Le sol HORS ÉCRAN : tuiles + cloisons du fond, retracé seulement quand
       sa signature change (plateau, échelle, taille, dpr). Les cloisons y
       vivent aussi : collées aux bords arrière, leur profondeur x+y est
       minimale — rien de mobile ne peut jamais passer derrière elles. Tout
       le reste (meubles ET personnages) part dans UNE liste triée par x+y à
       chaque image : à 25 persos et ~30 meubles c'est loin sous le budget
       60 fps, et le derrière/devant est juste par construction, sans
       retraçage de voisinage. */
    var sol = null, sigSol = '';

    function tw() { return TW * echelle; }
    function th() { return TH * echelle; }
    function proj(x, y) {
      return {
        x: (x - y) * tw() / 2 + origineX,
        y: (x + y) * th() / 2 + origineY
      };
    }
    /* L'origine centre le plateau dans le canvas. Recalculée à chaque image :
       quatre multiplications, et elle est toujours juste après un
       redimensionner(), un changement d'échelle ou d'étage. */
    function majOrigine() {
      origineX = cssW / 2 - (plateauW - plateauH) * tw() / 4;
      origineY = cssH / 2 - (plateauW + plateauH) * th() / 4 + 4 * echelle;
    }

    /* La brique de TOUT le mobilier : une boîte isométrique à trois faces.
       (x, y, w, h) en tuiles ; z et hauteurPx en px d'échelle 1, multipliés
       ici — chaque meuble ne se décrit donc qu'une seule fois. */
    function boite(c, x, y, z, w, h, hauteurPx, teinte) {
      var f = faces[teinte] || faces.metal;
      var zb = z * echelle, zh = (z + hauteurPx) * echelle;
      var n = proj(x, y), e = proj(x + w, y), s = proj(x + w, y + h), o = proj(x, y + h);
      c.fillStyle = f.dessus;
      c.beginPath();
      c.moveTo(n.x, n.y - zh); c.lineTo(e.x, e.y - zh);
      c.lineTo(s.x, s.y - zh); c.lineTo(o.x, o.y - zh);
      c.closePath(); c.fill();
      c.fillStyle = f.gauche;
      c.beginPath();
      c.moveTo(o.x, o.y - zh); c.lineTo(s.x, s.y - zh);
      c.lineTo(s.x, s.y - zb); c.lineTo(o.x, o.y - zb);
      c.closePath(); c.fill();
      c.fillStyle = f.droite;
      c.beginPath();
      c.moveTo(s.x, s.y - zh); c.lineTo(e.x, e.y - zh);
      c.lineTo(e.x, e.y - zb); c.lineTo(s.x, s.y - zb);
      c.closePath(); c.fill();
    }

    function losange(c, x, y) {
      var n = proj(x, y), e = proj(x + 1, y), s = proj(x + 1, y + 1), o = proj(x, y + 1);
      c.beginPath();
      c.moveTo(n.x, n.y); c.lineTo(e.x, e.y);
      c.lineTo(s.x, s.y); c.lineTo(o.x, o.y);
      c.closePath();
    }

    function majSol(plateau) {
      var sig = plateau.w + 'x' + plateau.h + ':' + plateau.porte.x + ',' + plateau.porte.y +
        '|' + echelle + '|' + cssW + 'x' + cssH + '|' + dpr;
      if (sig === sigSol && sol) return;
      sigSol = sig;
      if (!sol) sol = document.createElement('canvas');
      sol.width = Math.max(1, Math.round(cssW * dpr));
      sol.height = Math.max(1, Math.round(cssH * dpr));
      var c = sol.getContext('2d');
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.clearRect(0, 0, cssW, cssH);
      for (var y = 0; y < plateau.h; y++) {
        for (var x = 0; x < plateau.w; x++) {
          losange(c, x, y);
          /* Le seuil de la porte est « plus clair » par la MÊME loi que le
             reste (dessus ×1.35) : aucune valeur d'éclairage à la main. */
          c.fillStyle = (x === plateau.porte.x && y === plateau.porte.y)
            ? faces.sol.dessus : teintes.sol;
          c.fill();
          c.strokeStyle = 'rgba(255,255,255,.05)'; // le trait fin du quadrillage
          c.lineWidth = 1;
          c.stroke();
        }
      }
      /* Les deux cloisons du fond, avec un trou là où la porte donne sur le
         bord — c'est ce trou qui dit « on entre par ici » avant même le
         seuil clair (la couleur seule ne porte jamais l'info). */
      var ep = 0.16, hMur = 26;
      for (var i = 0; i < plateau.w; i++) {
        if (plateau.porte.y === 0 && i === plateau.porte.x) continue;
        boite(c, i, -ep, 0, 1, ep, hMur, 'cloison');
      }
      for (var j = 0; j < plateau.h; j++) {
        if (plateau.porte.x === 0 && j === plateau.porte.y) continue;
        boite(c, -ep, j, 0, ep, 1, hMur, 'cloison');
      }
      boite(c, -ep, -ep, 0, ep, ep, hMur, 'cloison'); // le poteau d'angle
    }

    /* ── Les meubles : une fonction par type, remplaçable un jour par des
       sprites sans toucher au reste (§4). Chaque dessin n'est que des
       boites() et deux traits de détail. ── */
    var DESSINS = {
      fondateur: function (c, m) {
        boite(c, m.x + 0.14, m.y + 0.2, 0, 0.72, 0.56, 6, 'metal');   // le caisson
        boite(c, m.x + 0.04, m.y + 0.12, 6, 0.92, 0.74, 3, 'bois');   // le grand plateau
        boite(c, m.x + 0.3, m.y + 0.02, 0, 0.4, 0.1, 19, 'papier');   // le dossier haut du fauteuil
        boite(c, m.x + 0.16, m.y + 0.4, 9, 0.26, 0.2, 1, 'papier');   // la pile de dossiers
      },
      poste: function (c, m) {
        boite(c, m.x + 0.2, m.y + 0.26, 0, 0.6, 0.46, 6, 'metal');
        boite(c, m.x + 0.12, m.y + 0.18, 6, 0.76, 0.62, 2, 'bois');
        boite(c, m.x + 0.3, m.y + 0.22, 8, 0.4, 0.06, 8, 'verre');    // l'écran : fin panneau vertical
        /* L'écran est allumé : un trait cyan léger sur sa face avant. C'est
           du décor à la limite de l'info — assumé, il dit « ce poste vit ». */
        var a = proj(m.x + 0.3, m.y + 0.28), b = proj(m.x + 0.7, m.y + 0.28);
        var zh = 15 * echelle;
        c.strokeStyle = accentA(0.35);
        c.lineWidth = 1;
        c.beginPath(); c.moveTo(a.x, a.y - zh); c.lineTo(b.x, b.y - zh); c.stroke();
      },
      cafe: function (c, m) {
        boite(c, m.x + 0.16, m.y + 0.16, 0, 0.68, 0.68, 7, 'bois');   // le meuble bas
        boite(c, m.x + 0.28, m.y + 0.28, 7, 0.4, 0.4, 7, 'metal');    // la machine
        /* Le voyant : une pastille NEUTRE. L'accent est réservé à ce qui
           attend le joueur — une machine à café n'a rien à lui demander. */
        var v = proj(m.x + 0.58, m.y + 0.68);
        c.fillStyle = 'rgba(255,255,255,.4)';
        c.beginPath(); c.arc(v.x, v.y - 10 * echelle, 1.2 * echelle, 0, 6.2832); c.fill();
      },
      plante: function (c, m) {
        boite(c, m.x + 0.36, m.y + 0.36, 0, 0.28, 0.28, 5, 'bois');   // le pot
        /* 3 à 5 feuilles, variées SANS hasard : la position de la plante
           décide (Math.random est interdit, et deux rendus du même état
           doivent être identiques au pixel). */
        var t = proj(m.x + 0.5, m.y + 0.5);
        var yPot = t.y - 5 * echelle;
        var nb = 3 + ((m.x * 7 + m.y * 13) % 3);
        var verts = [faces.verdure.dessus, faces.verdure.gauche, faces.verdure.droite];
        for (var i = 0; i < nb; i++) {
          var ang = -Math.PI / 2 + (i - (nb - 1) / 2) * 0.55;
          var lg = (9 + ((m.x + m.y + i) % 3) * 2) * echelle;
          c.fillStyle = verts[i % 3];
          c.beginPath();
          c.moveTo(t.x - 2 * echelle, yPot);
          c.lineTo(t.x + 2 * echelle, yPot);
          c.lineTo(t.x + Math.cos(ang) * lg, yPot + Math.sin(ang) * lg);
          c.closePath(); c.fill();
        }
      }
    };
    function dessinerMeuble(c, m) {
      /* Type inconnu (un meuble du lot ② avant son dessin) : une caisse
         neutre plutôt qu'un trou dans le décor. */
      (DESSINS[m.type] || function (cc, mm) {
        boite(cc, mm.x + 0.15, mm.y + 0.15, 0, 0.7, 0.7, 8, 'metal');
      })(c, m);
    }

    /* Le buste : une mini-boîte en px écran, même règle des trois faces. */
    function buste(c, cx, yBas, larg, haut, f) {
      var yH = yBas - haut, d = larg / 4;
      c.fillStyle = f.gauche;
      c.beginPath();
      c.moveTo(cx - larg / 2, yH); c.lineTo(cx, yH + d);
      c.lineTo(cx, yBas + d); c.lineTo(cx - larg / 2, yBas);
      c.closePath(); c.fill();
      c.fillStyle = f.droite;
      c.beginPath();
      c.moveTo(cx + larg / 2, yH); c.lineTo(cx, yH + d);
      c.lineTo(cx, yBas + d); c.lineTo(cx + larg / 2, yBas);
      c.closePath(); c.fill();
      c.fillStyle = f.dessus;
      c.beginPath();
      c.moveTo(cx, yH - d); c.lineTo(cx + larg / 2, yH);
      c.lineTo(cx, yH + d); c.lineTo(cx - larg / 2, yH);
      c.closePath(); c.fill();
    }

    /* Un personnage ~26 px : deux jambes en traits, un buste, une tête.
       Quatre directions par simple miroir x — la tête se décale du côté où
       l'on regarde, et c'est assez pour lire le sens de la marche. */
    function dessinerPerso(c, p, a, tMs, reduire) {
      var e = echelle;
      var s = proj(a.x + 0.5, a.y + 0.5);
      var marche = !!a.chemin && !reduire;
      /* Le balancement : un sinus sur tMs, déphasé par l'id pour que deux
         marcheurs ne soient jamais synchrones (et jamais de hasard). */
      var osc = marche ? Math.sin(tMs / 110 + p.id * 1.7) : 0;
      c.fillStyle = 'rgba(0,0,0,.28)';   // l'ombre : le contact au sol, lisible
      c.beginPath(); c.ellipse(s.x, s.y, 6 * e, 3 * e, 0, 0, 6.2832); c.fill();
      var hanche = s.y - 8 * e;
      c.strokeStyle = faces.metal.droite;
      c.lineWidth = Math.max(1, 1.4 * e);
      c.beginPath();
      c.moveTo(s.x - 1.6 * e, hanche); c.lineTo(s.x - 1.6 * e + osc * 2 * e, s.y);
      c.moveTo(s.x + 1.6 * e, hanche); c.lineTo(s.x + 1.6 * e - osc * 2 * e, s.y);
      c.stroke();
      var bx = s.x + osc * 1.1 * e;
      buste(c, bx, hanche, 8 * e, 10 * e, faces.papier);
      /* La tête : une teinte de la palette (bois éclairé), pas une couleur
         de peau inventée — le décor n'a droit qu'à ses sept matières. */
      var fx = a.fx || 1;
      c.fillStyle = faces.bois.dessus;
      c.beginPath();
      c.arc(bx + fx * 0.8 * e, hanche - 14.5 * e, 4 * e, 0, 6.2832);
      c.fill();
      c.strokeStyle = faces.bois.droite;
      c.lineWidth = 1;
      c.stroke();
    }

    /* La bulle d'attente : un losange cyan et un « ? » au-dessus de la tête.
       Elle clignote au sinus ; FIGÉE si reduireMouvement — la bulle reste
       (c'est une info), seul le battement disparaît. */
    function dessinerBulle(c, a, tMs, reduire) {
      var e = echelle;
      var s = proj(a.x + 0.5, a.y + 0.5);
      var y = s.y - 33 * e;
      c.save();
      c.globalAlpha = reduire ? 0.9 : 0.55 + 0.4 * Math.sin(tMs / 280);
      c.strokeStyle = ACCENT;
      c.fillStyle = ACCENT;
      c.lineWidth = 1;
      c.beginPath();
      c.moveTo(s.x, y - 6 * e); c.lineTo(s.x + 6 * e, y);
      c.lineTo(s.x, y + 6 * e); c.lineTo(s.x - 6 * e, y);
      c.closePath(); c.stroke();
      c.font = (8 * e) + 'px "Courier New",monospace';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText('?', s.x, y + 0.5 * e);
      c.restore();
    }

    /* L'arc de progression : le vocabulaire de .ring en miniature, au-dessus
       du poste — une piste neutre, l'avancement en accent. */
    function dessinerArc(c, tuile, progression) {
      var e = echelle;
      var s = proj(tuile.x + 0.5, tuile.y + 0.5);
      var y = s.y - 26 * e;
      c.lineWidth = 2;
      c.strokeStyle = 'rgba(255,255,255,.12)';
      c.beginPath(); c.arc(s.x, y, 6 * e, 0, Math.PI * 2); c.stroke();
      c.strokeStyle = ACCENT;
      c.beginPath();
      c.arc(s.x, y, 6 * e, -Math.PI / 2, -Math.PI / 2 + progression * Math.PI * 2);
      c.stroke();
    }

    /* Le fantôme de pose. Valide : tuile teintée accent + meuble translucide.
       Refusé : hachures GRISES — pas de rouge (réservé au P&L), et le motif
       porte l'info pour que la couleur ne soit jamais seule à le faire. */
    function dessinerFantome(c, f) {
      if (f.ok) {
        losange(c, f.x, f.y);
        c.fillStyle = accentA(0.16); c.fill();
        c.strokeStyle = accentA(0.6); c.lineWidth = 1; c.stroke();
        if (f.type) {
          c.save();
          c.globalAlpha = 0.5;
          dessinerMeuble(c, { type: f.type, x: f.x, y: f.y });
          c.restore();
        }
        return;
      }
      c.save();
      losange(c, f.x, f.y);
      c.clip();
      c.strokeStyle = 'rgba(255,255,255,.2)';
      c.lineWidth = 1;
      var o = proj(f.x, f.y + 1), dr = proj(f.x + 1, f.y);
      var haut = proj(f.x, f.y).y, bas = proj(f.x + 1, f.y + 1).y;
      c.beginPath();
      for (var gx = o.x - (bas - haut); gx < dr.x; gx += 4 * echelle) {
        c.moveTo(gx, bas); c.lineTo(gx + (bas - haut), haut);
      }
      c.stroke();
      c.restore();
      losange(c, f.x, f.y);
      c.strokeStyle = 'rgba(255,255,255,.35)';
      c.lineWidth = 1;
      c.stroke();
    }

    /* ── L'animation : la table PROPRE au rendu (id → position animée).
       Le moteur téléporte pos/but d'un tick à l'autre ; c'est ici qu'on
       fabrique le trajet — A* sur la grille des meubles, ~2.2 tuiles/s,
       cadencé par le tMs de l'appelant, jamais par une horloge à nous. ── */
    var animes = new Map();

    function grilleDe(plateau) {
      var bloc = {};
      for (var i = 0; i < plateau.meubles.length; i++) {
        bloc[plateau.meubles[i].x + ',' + plateau.meubles[i].y] = true;
      }
      return {
        w: plateau.w, h: plateau.h,
        bloquee: function (x, y) { return !!bloc[x + ',' + y]; }
      };
    }

    function majAnimes(state, tMs, reduire) {
      var vivants = {}, grille = null;
      for (var i = 0; i < state.equipe.length; i++) {
        var p = state.equipe[i];
        vivants[p.id] = true;
        var but = p.but || p.pos;
        var a = animes.get(p.id);
        if (!a) {
          a = { x: p.pos.x, y: p.pos.y, chemin: null, pas: 0, cible: '', fx: 1, t: tMs };
          animes.set(p.id, a);
        }
        var cible = but.x + ',' + but.y;
        if (reduire) {
          /* reduireMouvement : on arrive, on ne voyage pas. */
          a.x = but.x; a.y = but.y; a.chemin = null; a.cible = cible; a.t = tMs;
          continue;
        }
        if (cible !== a.cible) {
          a.cible = cible;
          a.pas = 0;
          if (!grille) grille = grilleDe(state.plateau);
          a.chemin = astar(grille, { x: Math.round(a.x), y: Math.round(a.y) }, but);
          /* Sans chemin (le plateau a changé sous ses pieds) : téléportation
             assumée, plutôt qu'un personnage coincé pour toujours. */
          if (!a.chemin) { a.x = but.x; a.y = but.y; }
        }
        /* dt borné à 100 ms : au retour d'un onglet caché, personne ne
           traverse la pièce d'un seul bond. */
        var dt = Math.min(0.1, Math.max(0, (tMs - a.t) / 1000));
        a.t = tMs;
        var reste = VITESSE_TUILES_S * dt;
        while (a.chemin && reste > 0) {
          var prochain = a.chemin[a.pas + 1];
          if (!prochain) { a.x = but.x; a.y = but.y; a.chemin = null; break; }
          var dx = prochain.x - a.x, dy = prochain.y - a.y;
          var d = Math.abs(dx) + Math.abs(dy);  // pas cardinaux : Manhattan suffit
          if (d < 1e-9) { a.pas++; continue; }
          /* Le miroir x : l'écran va vers la droite quand x − y augmente. */
          var ecranDx = dx - dy;
          if (ecranDx > 1e-9) a.fx = 1;
          else if (ecranDx < -1e-9) a.fx = -1;
          if (d <= reste) { a.x = prochain.x; a.y = prochain.y; a.pas++; reste -= d; }
          else { a.x += (dx / d) * reste; a.y += (dy / d) * reste; reste = 0; }
        }
      }
      /* On oublie les partis (démissions du lot ②) : la table ne fuit pas. */
      animes.forEach(function (valeur, id) { if (!vivants[id]) animes.delete(id); });
    }

    function tuileDuPoste(plateau, posteId) {
      for (var i = 0; i < plateau.meubles.length; i++) {
        if (plateau.meubles[i].id === posteId) return plateau.meubles[i];
      }
      return null;
    }

    /* ── La passe par image ── */
    function dessiner(state, tMs, opts) {
      opts = opts || {};
      var plateau = state.plateau;
      plateauW = plateau.w; plateauH = plateau.h;
      if (cssW < 2 || cssH < 2) return;   // canvas replié : rien à dessiner
      var reduire = !!opts.reduireMouvement;

      majOrigine();
      majSol(plateau);
      majAnimes(state, tMs, reduire);

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssW, cssH);
      ctx.save();
      ctx.translate(panX, panY);   // le doigt déplace la caméra, pas le monde

      /* 1. Le sol, recomposé depuis le hors-écran — jamais retracé tuile à
         tuile dans la boucle. */
      ctx.drawImage(sol, 0, 0, sol.width, sol.height, 0, 0, cssW, cssH);

      /* 2. Les surbrillances, au ras du sol : sous les meubles, comme une
         lumière posée sur la moquette. */
      if (opts.survol) {
        losange(ctx, opts.survol.x, opts.survol.y);
        ctx.fillStyle = accentA(0.07); ctx.fill();
        ctx.strokeStyle = accentA(0.4); ctx.lineWidth = 1; ctx.stroke();
      }
      if (opts.selection) {
        losange(ctx, opts.selection.x, opts.selection.y);
        ctx.fillStyle = accentA(0.12); ctx.fill();
        ctx.strokeStyle = accentA(0.9); ctx.lineWidth = 2; ctx.stroke();
      }
      if (opts.fantome) dessinerFantome(ctx, opts.fantome);

      /* 3. UNE liste triée par x+y, meubles et personnages confondus : le
         derrière/devant tombe juste par construction (§3.1). */
      var scene = [];
      for (var i = 0; i < plateau.meubles.length; i++) {
        scene.push({ prof: plateau.meubles[i].x + plateau.meubles[i].y, meuble: plateau.meubles[i] });
      }
      for (var j = 0; j < state.equipe.length; j++) {
        var p = state.equipe[j];
        var a = animes.get(p.id);
        if (!a) continue;
        /* +0.01 : à profondeur égale (assis AU poste), la personne se dessine
           par-dessus son meuble, jamais dessous. */
        scene.push({ prof: a.x + a.y + 0.01, perso: p, anim: a });
      }
      scene.sort(function (u, v) { return u.prof - v.prof; });
      for (var s = 0; s < scene.length; s++) {
        if (scene[s].meuble) dessinerMeuble(ctx, scene[s].meuble);
        else dessinerPerso(ctx, scene[s].perso, scene[s].anim, tMs, reduire);
      }

      /* 4. Par-dessus tout : les arcs de travail et les bulles d'attente —
         ce sont des informations, rien ne doit pouvoir les masquer. */
      for (var q = 0; q < state.equipe.length; q++) {
        var pq = state.equipe[q];
        var aq = animes.get(pq.id);
        if (!aq) continue;
        if (pq.etat === 'poste' && pq.progression > 0 && pq.progression < 1) {
          var tuile = tuileDuPoste(plateau, pq.posteId);
          if (tuile) dessinerArc(ctx, tuile, pq.progression);
        }
        if (pq.etat === 'attend') dessinerBulle(ctx, aq, tMs, reduire);
      }

      ctx.restore();
    }

    /* ── La caméra ── */
    function redimensionner() {
      var r = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : null;
      cssW = (r && r.width) || canvas.clientWidth || canvas.width || 640;
      cssH = (r && r.height) || canvas.clientHeight || canvas.height || 360;
      /* dpr plafonné à 2 : au-delà, quatre fois plus de pixels pour un gain
         invisible sur des aplats géométriques. */
      dpr = Math.min(2, (typeof window !== 'undefined' && window.devicePixelRatio) || 1);
      canvas.width = Math.max(1, Math.round(cssW * dpr));
      canvas.height = Math.max(1, Math.round(cssH * dpr));
      majOrigine();
      sigSol = '';   // le sol dépend de la taille : à retracer
    }

    function definirEchelle(n) {
      echelle = n === 2 ? 2 : 1;   // deux échelles, pas de zoom libre (§3.1)
      majOrigine();
      sigSol = '';
    }

    function definirPan(dx, dy) { panX = dx; panY = dy; }

    /* L'inverse exact de proj() : d'abord x−y et x+y, puis floor — le point
       tombe dans LE losange qui le contient, pas dans le plus proche. */
    function tuileDepuisPixel(px, py) {
      var ax = (px - panX - origineX) / (tw() / 2);
      var ay = (py - panY - origineY) / (th() / 2);
      var x = Math.floor((ax + ay) / 2);
      var y = Math.floor((ay - ax) / 2);
      if (x < 0 || y < 0 || x >= plateauW || y >= plateauH) return null;
      return { x: x, y: y };
    }

    redimensionner();
    return {
      dessiner: dessiner,
      tuileDepuisPixel: tuileDepuisPixel,
      definirEchelle: definirEchelle,
      definirPan: definirPan,
      redimensionner: redimensionner
    };
  }

  var MaisonIso = { creer: creer, astar: astar };

  if (typeof module !== 'undefined') module.exports = MaisonIso;
  if (typeof window !== 'undefined') window.MaisonIso = MaisonIso;
})();
