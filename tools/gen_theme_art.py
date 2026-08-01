#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_theme_art.py — illustrations des watchlists thématiques (assets/themes/<id>.png)

Créations 100 % originales, générées par code : aucun asset externe, aucun logo,
aucune marque. Une seule grammaire visuelle pour les 13 planches (« atlas
d'instrumentation ») : substrat sombre + trame orthogonale, tracé fin en bleu
accent gradué sur 4 niveaux de présence, UNE seule note chaude (ambre ou violet)
par planche, réglure de bas de page, marques de repérage aux angles, numéro de
planche en monospace.

Charte (signal.css) : fond #0d0d16 · accent #74b6df · ambre #e0995e · violet
#b59bd6. Le vert et le rouge sont réservés au P&L factuel et n'apparaissent
jamais ici.

Usage :  python3 tools/gen_theme_art.py [id ...]
Sortie :  assets/themes/<id>.png  —  960x540, PNG-8 palettisé, < 60 Ko
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

# ── Géométrie ────────────────────────────────────────────────────────────────
W, H = 960, 540
S = 3                        # sur-échantillonnage (anticrénelage)
MARGIN = 46
BOX = (72, 74, 888, 452)     # zone de dessin utile (x0, y0, x1, y1)
RULE_Y = 494                 # réglure de bas de planche

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "themes")
FONT_DIR = "/root/.claude/skills/canvas-design/canvas-fonts"
FONT_MONO = os.path.join(FONT_DIR, "JetBrainsMono-Regular.ttf")

# ── Palette ──────────────────────────────────────────────────────────────────
BG        = (13, 13, 22)
BLUE      = (116, 182, 223)
AMBER     = (224, 153, 94)
VIOLET    = (181, 155, 214)
INK       = (138, 138, 166)

GRID      = BLUE + (15,)     # trame fine
GRID5     = BLUE + (32,)     # trame maîtresse
GHOST     = BLUE + (46,)     # tracé fantôme
SOFT      = BLUE + (100,)    # tracé secondaire
MID       = BLUE + (172,)    # tracé courant
LINE      = BLUE + (245,)    # tracé principal
BRIGHT    = (196, 226, 246, 240)


# ── Primitives (coordonnées en espace 960x540, mises à l'échelle S) ──────────
class Plate:
    def __init__(self, seed=0):
        self.img = Image.new("RGB", (W * S, H * S), BG)
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.rng = random.Random(seed)

    # -- helpers d'échelle
    def _p(self, pt):
        return (pt[0] * S, pt[1] * S)

    def _w(self, w):
        return max(1, int(round(w * S)))

    def line(self, p0, p1, color, w=1.0):
        self.d.line([self._p(p0), self._p(p1)], fill=color, width=self._w(w))

    def path(self, pts, color, w=1.0, joint="curve"):
        if len(pts) < 2:
            return
        self.d.line([self._p(p) for p in pts], fill=color, width=self._w(w), joint=joint)

    def circle(self, c, r, color, w=1.0):
        bb = [self._p((c[0] - r, c[1] - r)), self._p((c[0] + r, c[1] + r))]
        self.d.ellipse(bb, outline=color, width=self._w(w))

    def disc(self, c, r, color):
        bb = [self._p((c[0] - r, c[1] - r)), self._p((c[0] + r, c[1] + r))]
        self.d.ellipse(bb, fill=color)

    def rect(self, box, color, w=1.0):
        self.d.rectangle([self._p(box[:2]), self._p(box[2:])], outline=color, width=self._w(w))

    def fill(self, box, color):
        x0, y0, x1, y1 = box
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        if x1 - x0 < 0.4 or y1 - y0 < 0.4:
            return
        self.d.rectangle([self._p((x0, y0)), self._p((x1, y1))], fill=color)

    def arc(self, c, r, a0, a1, color, w=1.0):
        bb = [self._p((c[0] - r, c[1] - r)), self._p((c[0] + r, c[1] + r))]
        self.d.arc(bb, a0, a1, fill=color, width=self._w(w))

    def wedge(self, c, r, a0, a1, color):
        bb = [self._p((c[0] - r, c[1] - r)), self._p((c[0] + r, c[1] + r))]
        self.d.pieslice(bb, a0, a1, fill=color)

    def poly(self, pts, color):
        self.d.polygon([self._p(p) for p in pts], fill=color)

    def dash(self, p0, p1, color, w=1.0, on=7, off=6):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        if L == 0:
            return
        ux, uy = dx / L, dy / L
        t = 0.0
        while t < L:
            t2 = min(t + on, L)
            self.line((p0[0] + ux * t, p0[1] + uy * t),
                      (p0[0] + ux * t2, p0[1] + uy * t2), color, w)
            t += on + off

    def dashpath(self, pts, color, w=1.0, on=7, off=6):
        """Pointillé le long d'une polyligne, phase continue."""
        carry, drawing = 0.0, True
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            if L == 0:
                continue
            ux, uy = dx / L, dy / L
            t = 0.0
            while t < L:
                span = (on if drawing else off) - carry
                t2 = min(t + span, L)
                if drawing:
                    self.line((a[0] + ux * t, a[1] + uy * t),
                              (a[0] + ux * t2, a[1] + uy * t2), color, w)
                if t2 - t >= span - 1e-9:
                    drawing = not drawing
                    carry = 0.0
                else:
                    carry += t2 - t
                t = t2

    def cross(self, c, r, color, w=1.0):
        self.line((c[0] - r, c[1]), (c[0] + r, c[1]), color, w)
        self.line((c[0], c[1] - r), (c[0], c[1] + r), color, w)

    def node(self, c, r, color, w=1.2, fill=BG + (255,)):
        self.disc(c, r, fill)
        self.circle(c, r, color, w)

    def text(self, pos, s, size, color, track=0.0, anchor="ls"):
        f = ImageFont.truetype(FONT_MONO, int(size * S))
        if track == 0:
            self.d.text(self._p(pos), s, font=f, fill=color, anchor=anchor)
            return
        # lettrage espacé manuellement
        widths = [self.d.textlength(ch, font=f) / S for ch in s]
        total = sum(widths) + track * (len(s) - 1)
        x = pos[0] - (total if anchor[0] == "r" else total / 2 if anchor[0] == "m" else 0)
        for ch, wc in zip(s, widths):
            self.d.text(self._p((x, pos[1])), ch, font=f, fill=color, anchor="l" + anchor[1])
            x += wc + track

    def bezier(self, p0, p1, p2, p3, n=64):
        pts = []
        for i in range(n + 1):
            t = i / n
            u = 1 - t
            x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
            y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
            pts.append((x, y))
        return pts


# ── Chrome commun : ce qui fait la SÉRIE ─────────────────────────────────────
def substrate(pl):
    """Trame orthogonale : 24 px, maîtresse toutes les 5 cases."""
    for x in range(0, W + 1, 24):
        pl.line((x, 0), (x, H), GRID5 if x % 120 == 0 else GRID, 1)
    for y in range(0, H + 1, 24):
        pl.line((0, y), (W, y), GRID5 if y % 120 == 0 else GRID, 1)


def chrome(pl, index, code, caption, accent):
    """Repères de planche : angles, réglure graduée, index, légende."""
    m, t = MARGIN, 13
    for sx, sy, ax, ay in ((0, 0, 1, 1), (1, 0, -1, 1), (0, 1, 1, -1), (1, 1, -1, -1)):
        x = m if sx == 0 else W - m
        y = m if sy == 0 else H - m
        pl.line((x, y), (x + ax * t, y), SOFT, 1)
        pl.line((x, y), (x, y + ay * t), SOFT, 1)

    # réglure : graduation fine, repère majeur tous les 5
    x0, x1 = MARGIN, W - MARGIN
    pl.line((x0, RULE_Y), (x1, RULE_Y), BLUE + (46,), 1)
    n = 0
    x = x0
    while x <= x1 + 0.1:
        h = 7 if n % 5 == 0 else 3.5
        pl.line((x, RULE_Y), (x, RULE_Y - h), BLUE + (74 if n % 5 == 0 else 40,), 1)
        x += 17.0
        n += 1

    # index de planche + légende, en marge basse
    pl.text((MARGIN, RULE_Y + 22), code, 11.5, INK + (150,), track=2.6)
    pl.text((W - MARGIN, RULE_Y + 22), "PL·%02d" % index, 11.5, INK + (120,), anchor="rs")
    pl.text((W / 2, RULE_Y + 22), caption, 10.5, accent + (95,), track=2.4, anchor="ms")


# ── Les 13 motifs ────────────────────────────────────────────────────────────
def semis(pl, ac):
    """Wafer : disque méplat, champs d'insolation en pas-et-répète."""
    c, r = (480, 258), 172
    step = 30
    # champs d'insolation, clippés au disque
    k = -6
    while k <= 6:
        x = c[0] + k * step
        dy = r * r - (x - c[0]) ** 2
        if dy > 0:
            dy = math.sqrt(dy) * 0.988
            pl.line((x, c[1] - dy), (x, c[1] + dy), BLUE + (44,), 1)
        y = c[1] + k * step
        dx = r * r - (y - c[1]) ** 2
        if dx > 0:
            dx = math.sqrt(dx) * 0.988
            pl.line((c[0] - dx, y), (c[0] + dx, y), BLUE + (44,), 1)
        k += 1
    # champs déjà insolés : accumulation en pas-et-répète
    for gx, gy in ((-3, -2), (-2, -2), (-1, -2), (0, -2), (1, -2),
                   (-3, -1), (-2, -1), (2, -1),
                   (-3, 0), (-2, 0), (1, 1), (2, 1), (-1, 2), (0, 2)):
        pl.fill((c[0] + gx * step + 2, c[1] + gy * step + 2,
                 c[0] + (gx + 1) * step - 2, c[1] + (gy + 1) * step - 2), BLUE + (24,))
    # bord du wafer, avec méplat
    pl.arc(c, r, 124, 56, LINE, 2.2)
    a0, a1 = math.radians(124), math.radians(56)
    pl.line((c[0] + r * math.cos(a0), c[1] + r * math.sin(a0)),
            (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1)), LINE, 2.2)
    pl.circle(c, r - 13, BLUE + (66,), 1)
    # champ retenu : réticule
    fx0, fy0 = c[0] - step, c[1] - step
    fx1, fy1 = c[0] + step, c[1] + step
    pl.fill((fx0, fy0, fx1, fy1), ac + (26,))
    pl.rect((fx0, fy0, fx1, fy1), ac + (235,), 2.0)
    for px, py in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
        pl.line((px - 7, py), (px + 7, py), ac + (225,), 1.2)
        pl.line((px, py - 7), (px, py + 7), ac + (225,), 1.2)
    pl.cross(c, 11, ac + (185,), 1.2)
    # cotes d'alignement
    pl.dash((c[0] - r - 36, c[1]), (c[0] + r + 36, c[1]), BLUE + (40,), 1, 5, 8)
    pl.dash((c[0], c[1] - r - 36), (c[0], c[1] + r + 36), BLUE + (40,), 1, 5, 8)
    for s2 in (-1, 1):
        pl.line((c[0] + s2 * (r + 36), c[1] - 7), (c[0] + s2 * (r + 36), c[1] + 7), SOFT, 1.2)
        pl.line((c[0] - 7, c[1] + s2 * (r + 36)), (c[0] + 7, c[1] + s2 * (r + 36)), SOFT, 1.2)


def memoire(pl, ac):
    """Cycle : oscillation à enveloppe, échantillonnée en colonnes empilées."""
    axis = 226
    base = 444
    x0, x1 = 92, 868

    def amp(x):
        u = (x - x0) / (x1 - x0)
        return 104 * (0.28 + 0.72 * math.exp(-((u - 0.60) ** 2) / 0.055))

    def wave(x):
        u = (x - x0) / (x1 - x0)
        return axis - amp(x) * math.sin(2 * math.pi * (u * 2.15 - 0.08))

    pl.dash((x0, axis), (x1, axis), BLUE + (52,), 1, 6, 7)
    xs = [x0 + i * (x1 - x0) / 320 for i in range(321)]
    pl.path([(x, axis - amp(x)) for x in xs], BLUE + (46,), 1)
    pl.path([(x, axis + amp(x)) for x in xs], BLUE + (46,), 1)
    pl.path([(x, wave(x)) for x in xs], LINE, 2.4)

    # colonnes : le stock, échantillonné sur le cycle
    n = 26
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        v = (axis - wave(x)) / 104
        h = 18 + 76 * (v + 1) / 2
        cells = max(1, int(round(h / 13)))
        for j in range(cells):
            y = base - (j + 1) * 13
            a = 30 + int(78 * (j + 1) / cells)
            pl.fill((x - 9, y + 1.5, x + 9, y + 11.5), BLUE + (a,))
    pl.line((x0, base), (x1, base), BLUE + (76,), 1)

    # sommet du cycle
    px = max(xs, key=lambda x: axis - wave(x))
    py = wave(px)
    pl.dash((px, py + 9), (px, base), ac + (110,), 1, 4, 6)
    pl.dash((px + 12, py), (x1, py), ac + (78,), 1, 5, 7)
    pl.node((px, py), 6, ac + (250,), 1.8)
    pl.line((px - 30, py - 26), (px - 9, py - 9), ac + (140,), 1.2)
    pl.line((px - 40, py - 26), (px - 24, py - 26), ac + (140,), 1.2)


def ia(pl, ac):
    """Réseau : couches de nœuds, propagation d'un chemin."""
    cols = [(146, 4), (312, 6), (480, 7), (648, 5), (814, 3)]
    cy, gap = 256, 62
    layers = []
    for x, n in cols:
        ys = [cy + (i - (n - 1) / 2) * gap for i in range(n)]
        layers.append([(x, y) for y in ys])
    # liaisons : chaque nœud vers ses 3 plus proches voisins de la couche suivante
    for a, b in zip(layers, layers[1:]):
        for p in a:
            near = sorted(b, key=lambda q: abs(q[1] - p[1]))[:3]
            for q in near:
                pl.line(p, q, BLUE + (34,), 1)
    path = [layers[0][3], layers[1][1], layers[2][5], layers[3][1], layers[4][1]]
    for p, q in zip(path, path[1:]):
        pl.line(p, q, BLUE + (215,), 2.2)
    for L in layers:
        for p in L:
            pl.node(p, 6, SOFT, 1.3)
    for p in path[:-1]:
        pl.node(p, 6, LINE, 1.8, fill=BLUE + (80,))
    q = path[-1]
    pl.circle(q, 17, ac + (70,), 1.1)
    pl.node(q, 7, ac + (250,), 2.0, fill=ac + (90,))
    for i, (x, n) in enumerate(cols):
        pl.line((x, 442), (x, 452), BLUE + (90,), 1.2)
        for k in range(n):
            pl.line((x - 7, 436 - k * 4), (x + 7, 436 - k * 4), BLUE + (54,), 1)
    pl.dash((cols[0][0], 442), (cols[-1][0], 442), BLUE + (44,), 1, 4, 6)


def robotique(pl, ac):
    """Bras articulé : poses répétées, trajectoire de l'effecteur."""
    base = (322, 420)
    L1, L2, L3 = 196, 152, 54

    def pose(t):
        a1 = math.radians(-122 + 66 * t)
        a2 = math.radians(100 - 44 * t)
        j1 = (base[0] + L1 * math.cos(a1), base[1] + L1 * math.sin(a1))
        a2b = a1 + a2
        j2 = (j1[0] + L2 * math.cos(a2b), j1[1] + L2 * math.sin(a2b))
        a3 = a2b + math.radians(34)
        tip = (j2[0] + L3 * math.cos(a3), j2[1] + L3 * math.sin(a3))
        return j1, j2, tip

    # embase
    pl.fill((base[0] - 44, base[1] + 8, base[0] + 44, base[1] + 21), BLUE + (40,))
    pl.rect((base[0] - 44, base[1] + 8, base[0] + 44, base[1] + 21), MID, 1.3)
    for i in range(7):
        x = base[0] - 36 + i * 12
        pl.line((x, base[1] + 21), (x - 6, base[1] + 32), BLUE + (60,), 1)
    pl.line((base[0] - 58, base[1] + 32), (base[0] + 58, base[1] + 32), BLUE + (76,), 1)

    # poses fantômes
    for i in range(7):
        j1, j2, tip = pose(i / 7)
        pl.path([base, j1, j2, tip], BLUE + (34 + 6 * i,), 1.5)
        pl.node(j1, 4, BLUE + (44 + 6 * i,), 1)

    # poste de dépose
    st = pose(1.0)[2]
    pl.dash((st[0] - 6, st[1] + 34), (st[0] + 138, st[1] + 34), BLUE + (56,), 1, 6, 6)
    pl.rect((st[0] + 46, st[1] - 20, st[0] + 122, st[1] + 32), BLUE + (50,), 1.2)
    for k in range(4):
        yy = st[1] + 32 - k * 13
        pl.line((st[0] + 50, yy), (st[0] + 118, yy), BLUE + (32,), 1)
    pl.dash((st[0] + 14, st[1] + 6), (st[0] + 44, st[1] + 6), ac + (110,), 1, 5, 5)

    # trajectoire
    traj = [pose(i / 90)[2] for i in range(91)]
    pl.dashpath(traj, ac + (150,), 1.4, 9, 7)
    for i in range(0, 91, 15):
        p = traj[i]
        pl.line((p[0], p[1] - 5), (p[0], p[1] + 5), ac + (95,), 1)

    # pose courante
    j1, j2, tip = pose(1.0)
    pl.path([base, j1, j2], LINE, 3.4)
    pl.path([j2, tip], LINE, 2.6)
    pl.node(base, 12, LINE, 2.0)
    pl.node(base, 4.5, BLUE + (170,), 1.4, fill=BLUE + (110,))
    pl.node(j1, 10, LINE, 2.0)
    pl.node(j2, 8, LINE, 1.8)
    d = math.atan2(tip[1] - j2[1], tip[0] - j2[0])
    for s in (-1, 1):
        n = (math.cos(d + s * math.pi / 2) * 10, math.sin(d + s * math.pi / 2) * 10)
        pl.line((tip[0] + n[0] * 0.5, tip[1] + n[1] * 0.5),
                (tip[0] + n[0] + math.cos(d) * 15, tip[1] + n[1] + math.sin(d) * 15),
                ac + (245,), 2.2)
    # secteur angulaire
    pl.arc(base, 70, -122, -56, BLUE + (76,), 1.2)
    for k in range(7):
        a = math.radians(-122 + k * 66 / 6)
        pl.line((base[0] + 65 * math.cos(a), base[1] + 65 * math.sin(a)),
                (base[0] + 75 * math.cos(a), base[1] + 75 * math.sin(a)), BLUE + (76,), 1)


def finance(pl, ac):
    """Bilan et contrepartie : deux colonnes, flux croisés."""
    yc, hh = 252, 132
    cols = [(188, (0.34, 0.26, 0.40)), (772, (0.46, 0.30, 0.24))]
    for x, parts in cols:
        y = yc - hh
        acc = 0.0
        for i, p in enumerate(parts):
            acc += p
            pl.fill((x - 47, y + 1, x + 47, y + p * 2 * hh - 1), BLUE + (24 + i * 16,))
            y2 = yc - hh + acc * 2 * hh
            if i < len(parts) - 1:
                pl.line((x - 48, y2), (x + 48, y2), BLUE + (110,), 1.2)
            y = y2
        pl.rect((x - 48, yc - hh, x + 48, yc + hh), LINE, 1.8)
        for k in range(9):
            yy = yc - hh + k * 2 * hh / 8
            pl.line((x - 56, yy), (x - 48, yy), BLUE + (70,), 1)

    pl.dash((480, 98), (480, 418), BLUE + (56,), 1, 6, 8)
    pl.line((472, 98), (488, 98), BLUE + (76,), 1)
    pl.line((472, 418), (488, 418), BLUE + (76,), 1)

    flows = [(-84, -108, 1), (-20, -10, 1), (48, 70, -1), (112, 30, -1), (-132, 118, 1)]
    for i, (ya, yb, dirn) in enumerate(flows):
        p0 = (236, yc + ya) if dirn > 0 else (724, yc + ya)
        p3 = (724, yc + yb) if dirn > 0 else (236, yc + yb)
        k = 155 * dirn
        pts = pl.bezier(p0, (p0[0] + k, p0[1]), (p3[0] - k, p3[1]), p3)
        hot = (i == 2)
        col = ac + (235,) if hot else BLUE + (86 + 26 * (i % 3),)
        pl.path(pts, col, 2.1 if hot else 1.5)
        a, b = pts[-6], pts[-1]
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for s in (1, -1):
            pl.line(b, (b[0] - 11 * math.cos(ang + s * 0.42),
                        b[1] - 11 * math.sin(ang + s * 0.42)), col, 1.7)
        if hot:
            pl.node(pts[len(pts) // 2], 5, ac + (250,), 1.5, fill=ac + (110,))
    pl.text((188, 412), "A", 11.5, INK + (135,), anchor="ms")
    pl.text((772, 412), "B", 11.5, INK + (135,), anchor="ms")


def peages(pl, ac):
    """Point de passage obligé : faisceau contraint par une porte unique."""
    gx = 480
    slot = 27
    n = 13
    for i in range(n):
        y0 = 116 + i * (300 / (n - 1))
        y1 = 130 + i * (274 / (n - 1))
        yg = 258 + (i - (n - 1) / 2) * (slot * 2 / (n - 1))
        left = pl.bezier((74, y0), (250, y0), (330, yg), (gx - 8, yg))
        right = pl.bezier((gx + 8, yg), (630, yg), (710, y1), (886, y1))
        a = 66 + (30 if i % 3 == 0 else 0)
        pl.path(left, BLUE + (a,), 1.4)
        pl.path(right, BLUE + (a,), 1.4)
    # la porte
    pl.fill((gx - 7, 258 - slot - 3, gx + 7, 258 + slot + 3), BG + (255,))
    pl.line((gx, 168), (gx, 258 - slot - 5), ac + (235,), 2.4)
    pl.line((gx, 258 + slot + 5), (gx, 348), ac + (235,), 2.4)
    pl.rect((gx - 14, 258 - slot - 5, gx + 14, 258 + slot + 5), ac + (165,), 1.3)
    for yy in (258 - slot - 5, 258 + slot + 5):
        pl.line((gx - 22, yy), (gx + 22, yy), ac + (215,), 1.8)
    pl.circle((gx, 258), 46, ac + (56,), 1.1)
    pl.cross((gx, 258), 9, ac + (185,), 1.3)
    # cote du passage
    bx = gx - 82
    pl.dash((bx, 258 - slot - 5), (gx - 22, 258 - slot - 5), BLUE + (46,), 1, 4, 5)
    pl.dash((bx, 258 + slot + 5), (gx - 22, 258 + slot + 5), BLUE + (46,), 1, 4, 5)
    pl.line((bx, 258 - slot - 5), (bx, 258 + slot + 5), BLUE + (86,), 1.2)
    for yy in (258 - slot - 5, 258 + slot + 5):
        pl.line((bx - 6, yy), (bx + 6, yy), BLUE + (86,), 1.2)


def compounders(pl, ac):
    """Capitalisation : trajectoire composée contre référence linéaire."""
    x0, x1, base = 112, 866, 424
    top = 112

    def comp(u):
        return base - (base - top) * (math.exp(3.05 * u) - 1) / (math.exp(3.05) - 1)

    for i in range(31):
        u = i / 30
        x = x0 + u * (x1 - x0)
        y = comp(u)
        pl.fill((x - 5.5, y + 3, x + 5.5, base - 1), BLUE + (22 + int(40 * u),))
    pl.line((x0 - 10, base), (x1 + 10, base), BLUE + (90,), 1.2)
    pl.dash((x0, base), (x1, base - (base - top) * 0.42), BLUE + (76,), 1, 8, 7)
    for i in range(1, 7):
        u = 0.42 + i * 0.086
        x = x0 + u * (x1 - x0)
        yl = base - (base - top) * 0.42 * u
        pl.line((x, comp(u) + 2), (x, yl - 2), ac + (56 + i * 16,), 1.2)
    xs = [x0 + i * (x1 - x0) / 180 for i in range(181)]
    pl.path([(x, comp((x - x0) / (x1 - x0))) for x in xs], LINE, 2.6)
    for i in range(6):
        u = i / 5
        pl.node((x0 + u * (x1 - x0), comp(u)), 5, MID, 1.3)
    pl.node((x1, comp(1)), 7, ac + (250,), 2.0, fill=ac + (100,))
    pl.circle((x1, comp(1)), 17, ac + (66,), 1.1)
    for i in range(6):
        x = x0 + i * (x1 - x0) / 5
        pl.line((x, base), (x, base + 8), BLUE + (70,), 1)


def conso(pl, ac):
    """Répétition quotidienne : cadence constante, une unité retenue."""
    cw, gx = 52, 18
    ncol, nrow = 11, 2
    ch, gy = 132, 34
    tw = ncol * cw + (ncol - 1) * gx
    ox, oy = (W - tw) / 2, 106
    for r in range(nrow):
        shelf = oy + r * (ch + gy) + ch
        pl.line((ox - 26, shelf + 7), (ox + tw + 26, shelf + 7), BLUE + (86,), 1.4)
        for k in range(ncol + 1):
            x = ox + k * (cw + gx) - gx / 2
            pl.line((x, shelf + 7), (x, shelf + 14), BLUE + (46,), 1)
        for c in range(ncol):
            x, y = ox + c * (cw + gx), oy + r * (ch + gy)
            hot = (r == 0 and c == 7)
            col = ac + (240,) if hot else BLUE + (78 + 12 * ((r + c) % 3),)
            pl.fill((x, y, x + cw, y + ch), (ac + (30,)) if hot else BLUE + (16,))
            pl.rect((x, y, x + cw, y + ch), col, 1.9 if hot else 1.2)
            # cartouche : bandeau constant + graduations
            pl.line((x, y + 34), (x + cw, y + 34),
                    (ac + (170,)) if hot else BLUE + (58,), 1.2)
            for k in range(4):
                yy = y + 52 + k * 17
                wfr = (0.72, 0.50, 0.72, 0.34)[k]
                pl.line((x + 10, yy), (x + 10 + (cw - 20) * wfr, yy),
                        (ac + (130,)) if hot else BLUE + (40,), 1.1)
            if hot:
                pl.disc((x + cw / 2, y + 17), 5, ac + (245,))
                for px, py, sy in ((x, y, 1), (x + cw, y, 1),
                                   (x, y + ch, -1), (x + cw, y + ch, -1)):
                    pl.line((px, py - sy * 10), (px, py + sy * 10), ac + (145,), 1.2)
            else:
                pl.circle((x + cw / 2, y + 17), 5, BLUE + (60,), 1)


def sante(pl, ac):
    """Molécule et signal vital : structure liée, tracé rythmé."""
    c, r = (392, 216), 100
    ring = [(c[0] + r * math.cos(math.radians(-90 + k * 60)),
             c[1] + r * math.sin(math.radians(-90 + k * 60))) for k in range(6)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        pl.line(a, b, LINE, 2.2)
    for i in (0, 2, 4):
        a, b = ring[i], ring[(i + 1) % 6]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 9, dx / L * 9
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        sgn = 1 if (mx - c[0]) * nx + (my - c[1]) * ny < 0 else -1
        pl.line((a[0] + sgn * nx + dx * 0.20, a[1] + sgn * ny + dy * 0.20),
                (b[0] + sgn * nx - dx * 0.20, b[1] + sgn * ny - dy * 0.20), MID, 1.6)
    tips = []
    for idx, ln, off in ((1, 70, -20), (3, 74, 26), (5, 64, 4)):
        a = ring[idx]
        ang = math.atan2(a[1] - c[1], a[0] - c[0]) + math.radians(off)
        t = (a[0] + ln * math.cos(ang), a[1] + ln * math.sin(ang))
        pl.line(a, t, MID, 1.7)
        tips.append(t)
    for p in ring:
        pl.node(p, 7, LINE, 1.9)
    for t in tips:
        pl.node(t, 5.5, SOFT, 1.4)
    pl.circle(c, r + 38, BLUE + (32,), 1)

    # tracé vital
    yb = 404
    pts, x = [(88, yb)], 88
    seq = [(56, 0), (13, -10), (15, 10), (11, 0), (8, 14), (10, -52), (10, 28), (11, -10),
           (17, 0), (24, -22), (22, 22), (52, 0)]
    for _ in range(3):
        for dx, dy in seq:
            x += dx
            pts.append((x, yb + dy))
            if dy != 0:
                pts.append((x, yb))
    pts.append((872, yb))
    pl.dash((88, yb), (872, yb), BLUE + (40,), 1, 5, 7)
    pl.path([(min(max(p[0], 88), 872), p[1]) for p in pts], ac + (235,), 2.1)
    peak = (392, yb - 52)
    pl.node(peak, 5, ac + (215,), 1.4)
    pl.dash((392, 320), (392, yb - 62), BLUE + (56,), 1, 4, 6)
    pl.line((384, 320), (400, 320), BLUE + (70,), 1)


def defense(pl, ac):
    """Veille : périmètre balayé, contacts relevés."""
    c, R = (480, 262), 186
    pl.wedge(c, R, -106, -62, BLUE + (30,))
    for rr in (48, 94, 140, R):
        pl.circle(c, rr, BLUE + (70 if rr == R else 44,), 1.6 if rr == R else 1)
    for k in range(24):
        a = math.radians(k * 15)
        maj = (k % 3 == 0)
        L0 = R - (13 if maj else 7)
        pl.line((c[0] + L0 * math.cos(a), c[1] + L0 * math.sin(a)),
                (c[0] + R * math.cos(a), c[1] + R * math.sin(a)),
                BLUE + (110 if maj else 56,), 1.2 if maj else 1)
    for a in (0, 90):
        ar = math.radians(a)
        pl.dash((c[0] - R * math.cos(ar), c[1] - R * math.sin(ar)),
                (c[0] + R * math.cos(ar), c[1] + R * math.sin(ar)), BLUE + (34,), 1, 5, 8)
    a = math.radians(-62)
    pl.line(c, (c[0] + R * math.cos(a), c[1] + R * math.sin(a)), BLUE + (225,), 2.2)
    for ang, rad, hot in ((-84, 122, False), (-152, 158, False),
                          (-26, 92, False), (-70, 162, True)):
        ar = math.radians(ang)
        p = (c[0] + rad * math.cos(ar), c[1] + rad * math.sin(ar))
        col = ac + (250,) if hot else BLUE + (155,)
        pl.rect((p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6), col, 1.6)
        if hot:
            pl.circle(p, 15, ac + (95,), 1.1)
            pl.dash((p[0] + 17, p[1]), (p[0] + 68, p[1]), ac + (110,), 1, 4, 5)
            pl.line((p[0] + 68, p[1] - 7), (p[0] + 68, p[1] + 7), ac + (140,), 1.2)
    pl.node(c, 4.5, BLUE + (185,), 1.3, fill=BLUE + (110,))


def electrification(pl, ac):
    """Réseau : production, transformation, charge — schéma unifilaire."""
    y = 244
    gen, tr, load = (144, y), (472, y), (816, y)
    # production
    pl.circle(gen, 38, LINE, 2.2)
    xs = [gen[0] - 22 + i * 44 / 44 for i in range(45)]
    pl.path([(x, gen[1] - 14 * math.sin((x - gen[0] + 22) / 44 * 2 * math.pi))
             for x in xs], MID, 1.7)
    pl.line((gen[0], gen[1] + 38), (gen[0], gen[1] + 52), MID, 1.5)
    pl.line((gen[0] - 22, gen[1] + 52), (gen[0] + 22, gen[1] + 52), MID, 1.5)
    for k in range(5):
        xx = gen[0] - 18 + k * 9
        pl.line((xx, gen[1] + 52), (xx - 7, gen[1] + 63), BLUE + (80,), 1.2)

    # ligne haute tension + isolateurs
    pl.line((gen[0] + 38, y), (tr[0] - 34, y), LINE, 2.2)
    pl.line((tr[0] + 34, y), (load[0] - 78, y), LINE, 2.2)
    for x in (248, 352, 604, 704):
        pl.line((x, y - 10), (x, y + 10), BLUE + (86,), 1.2)
        pl.line((x - 5, y - 10), (x + 5, y - 10), BLUE + (86,), 1.2)
    # pylônes en treillis
    for x in (300, 654):
        h0, h1 = y + 14, y + 104
        pl.path([(x - 28, h1), (x, h0), (x + 28, h1)], BLUE + (62,), 1.3)
        pl.line((x, h0), (x, h1), BLUE + (40,), 1)
        for k in range(1, 4):
            t = k / 4
            hw = 28 * t
            yy = h0 + (h1 - h0) * t
            pl.line((x - hw, yy), (x + hw, yy), BLUE + (56,), 1)
        pl.line((x - 28, h1), (x + 28, h1), BLUE + (62,), 1.3)

    # transformateur
    pl.circle((tr[0] - 17, y), 34, ac + (245,), 2.3)
    pl.circle((tr[0] + 17, y), 34, ac + (245,), 2.3)
    pl.dash((tr[0], y - 58), (tr[0], y + 58), ac + (95,), 1, 4, 6)
    for s in (-1, 1):
        pl.line((tr[0] + s * 66, y - 48), (tr[0] + s * 66, y + 48), BLUE + (48,), 1)

    # charge
    for r in range(3):
        for c2 in range(3):
            x = load[0] - 64 + c2 * 46
            yy = y - 46 + r * 46
            pl.fill((x, yy, x + 34, yy + 34), BLUE + (30 + 22 * ((r + c2) % 3),))
            pl.rect((x, yy, x + 34, yy + 34), BLUE + (125,), 1.2)
    pl.line((load[0] - 78, y), (load[0] - 64, y), LINE, 2.2)
    pl.rect((load[0] - 72, y - 54, load[0] + 26, y + 44), BLUE + (58,), 1)
    step = [(660, 400), (712, 400), (712, 382), (764, 382), (764, 358), (816, 358), (862, 358)]
    pl.path(step, MID, 1.7)
    pl.dash((660, 414), (862, 414), BLUE + (36,), 1, 4, 6)


def decote(pl, ac):
    """Écart à la droite de tendance : résidu mesuré."""
    x0, x1 = 108, 868
    y0, y1 = 402, 136

    def trend(x):
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    pl.rng.seed(11)
    band = 48
    pl.dash((x0, trend(x0) - band), (x1, trend(x1) - band), BLUE + (40,), 1, 5, 8)
    pl.dash((x0, trend(x0) + band), (x1, trend(x1) + band), BLUE + (40,), 1, 5, 8)
    pl.dash((x0, trend(x0)), (x1, trend(x1)), BLUE + (185,), 1.8, 13, 8)

    pts = []
    for i in range(34):
        u = i / 33
        x = x0 + u * (x1 - x0)
        res = pl.rng.gauss(0, 20) + 15 * math.sin(u * 7.1)
        if u > 0.60:
            res += 96 * math.exp(-((u - 0.70) ** 2) / 0.006)
        pts.append((x, trend(x) + res))
    pl.path(pts, BLUE + (62,), 1.4)
    for p in pts:
        pl.node(p, 4, BLUE + (140,), 1.1)

    hx = pts[23][0]
    hy = pts[23][1]
    pl.node((hx, hy), 7.5, ac + (250,), 2.0, fill=ac + (100,))
    pl.circle((hx, hy), 19, ac + (70,), 1.1)
    bx = hx + 46
    pl.line((bx, trend(hx)), (bx, hy), ac + (190,), 1.5)
    for yy in (trend(hx), hy):
        pl.line((bx - 7, yy), (bx + 7, yy), ac + (190,), 1.5)
    pl.dash((hx, trend(hx)), (bx + 13, trend(hx)), BLUE + (66,), 1, 4, 5)
    pl.dash((hx, hy), (bx + 13, hy), BLUE + (66,), 1, 4, 5)
    pl.text((bx + 18, (trend(hx) + hy) / 2 + 5), "−1σ", 12, ac + (175,))
    for i in range(6):
        x = x0 + i * (x1 - x0) / 5
        pl.line((x, 434), (x, 442), BLUE + (66,), 1)
    pl.line((x0, 434), (x1, 434), BLUE + (40,), 1)


def qualite(pl, ac):
    """Sélection : densité de population, fenêtre retenue sur la queue."""
    x0, x1, base = 104, 872, 424
    n = 38
    bw = (x1 - x0) / n

    def dens(u):
        return (math.exp(-((u - 0.44) ** 2) / 0.052) * 0.92
                + math.exp(-((u - 0.80) ** 2) / 0.020) * 0.34)

    cut = 0.735
    for i in range(n):
        u = (i + 0.5) / n
        h = 24 + 272 * dens(u)
        x = x0 + i * bw
        hot = u >= cut
        col = ac + (205,) if hot else BLUE + (80,)
        pl.fill((x + 2, base - h, x + bw - 2, base), (ac + (40,)) if hot else BLUE + (26,))
        pl.rect((x + 2, base - h, x + bw - 2, base), col, 1.3)
        k = 1
        while base - k * 22 > base - h + 6:
            yy = base - k * 22
            pl.line((x + 6, yy), (x + bw - 6, yy),
                    (ac + (66,)) if hot else BLUE + (32,), 1)
            k += 1
    env = [(x0 + (i + 0.5) * (x1 - x0) / 240, base - 24 - 272 * dens((i + 0.5) / 240))
           for i in range(240)]
    pl.path(env, BLUE + (125,), 1.6)
    pl.line((x0, base), (x1, base), BLUE + (90,), 1.2)

    sx = x0 + cut * (x1 - x0)
    pl.dash((sx, 100), (sx, base + 16), ac + (185,), 1.6, 8, 6)
    wx0, wy0, wx1, wy1 = sx - 7, 112, x1 + 7, base + 12
    for px, py, dx, dy in ((wx0, wy0, 1, 1), (wx1, wy0, -1, 1),
                           (wx0, wy1, 1, -1), (wx1, wy1, -1, -1)):
        pl.line((px, py), (px + dx * 28, py), ac + (230,), 1.9)
        pl.line((px, py), (px, py + dy * 24), ac + (230,), 1.9)
    pl.dash((wx0, wy0), (wx1, wy0), ac + (80,), 1, 5, 7)
    pl.dash((wx0, wy1), (wx1, wy1), ac + (80,), 1, 5, 7)
    pl.line((sx - 6, 100), (sx + 6, 100), ac + (205,), 1.5)
    for i in range(6):
        x = x0 + i * (x1 - x0) / 5
        pl.line((x, base), (x, base + 9), BLUE + (66,), 1)


# ── Registre des planches ────────────────────────────────────────────────────
PLATES = [
    ("semis",           1,  semis,           AMBER,  "LITHOGRAPHIE / RETICULE"),
    ("memoire",         2,  memoire,         AMBER,  "CYCLE / STOCK"),
    ("ia",              3,  ia,              VIOLET, "PROPAGATION / COUCHES"),
    ("robotique",       4,  robotique,       AMBER,  "CINEMATIQUE / REPETITION"),
    ("finance",         5,  finance,         VIOLET, "BILAN / CONTREPARTIE"),
    ("peages",          6,  peages,          AMBER,  "PASSAGE OBLIGE / PEAGE"),
    ("compounders",     7,  compounders,     AMBER,  "COMPOSITION / DUREE"),
    ("conso",           8,  conso,           VIOLET, "MODULE / RECURRENCE"),
    ("sante",           9,  sante,           VIOLET, "STRUCTURE / SIGNAL"),
    ("defense",        10,  defense,         AMBER,  "PERIMETRE / VEILLE"),
    ("electrification", 11, electrification, AMBER,  "TRANSFORMATION / CHARGE"),
    ("decote",         12,  decote,          VIOLET, "RESIDU / TENDANCE"),
    ("qualite",        13,  qualite,         VIOLET, "DENSITE / SELECTION"),
]


def render(tid, index, fn, accent, caption):
    pl = Plate(seed=index * 17)
    substrate(pl)
    fn(pl, accent)
    chrome(pl, index, tid.upper(), caption, accent)
    img = pl.img.resize((W, H), Image.LANCZOS)
    out = os.path.join(OUT_DIR, "%s.png" % tid)
    q = img.quantize(colors=192, method=Image.MEDIANCUT, dither=Image.NONE)
    q.save(out, optimize=True)
    return out, os.path.getsize(out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    want = set(sys.argv[1:])
    total = 0
    for tid, index, fn, accent, caption in PLATES:
        if want and tid not in want:
            continue
        path, size = render(tid, index, fn, accent, caption)
        total += size
        print("%-16s %6.1f Ko  %s" % (tid, size / 1024, path))
    if not want:
        print("total %.1f Ko" % (total / 1024))


if __name__ == "__main__":
    main()
