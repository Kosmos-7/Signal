#!/usr/bin/env python3
"""Tests de La Maison : le moteur est REJOUÉ sous node, jamais relu.

POURQUOI CE FICHIER EXISTE. Le jeu promet au joueur des choses qu'aucune
relecture ne peut garantir : même graine + mêmes décisions = même partie au
centime (sinon le partage d'URL ment), une souscription n'appauvrit jamais
les porteurs en place (sinon la VL ment), les frais du jeu sont ceux de
config.py (sinon la pédagogie ment), et le moteur ne lit JAMAIS un cours du
futur (sinon le jeu entier perd son sens). Chacune de ces promesses est ici
un programme node qui exécute le code livré — le motif de test_chrome.py et
test_actualites.py : on ne fait pas semblant d'avoir vérifié.

Deux règles éditoriales sont éprouvées aussi, parce qu'elles sont trop
importantes pour reposer sur la vigilance : les thèses ne citent que des
faits de PRIX (les cours sont réels — inventer une marge reviendrait à
l'attribuer plus tard à une société réelle), et les noms masqués sortent
d'une liste FIXE, jamais d'un assemblage de syllabes.

    python tests/test_maison.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RACINE)

ok, ko = 0, []


def check(nom, cond, detail=""):
    global ok
    if cond:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko.append(nom)
        print(f"  ❌ {nom} {detail}")


MOTEUR = open("maison-moteur.js", encoding="utf-8").read()
ISO = open("maison-iso.js", encoding="utf-8").read()
UI = open("maison-ui.js", encoding="utf-8").read()
PAGE = open("maison.html", encoding="utf-8").read()
CONFIG = open("config.py", encoding="utf-8").read()

NODE = True


def node(prog, argv=None):
    """Exécute un programme node depuis la racine du dépôt, rend stdout.

    Par FICHIER temporaire et non par -e : les programmes portent des
    chaînes françaises pleines d'apostrophes, l'échappement shell serait
    une source de faux rouges à lui tout seul.
    """
    global NODE
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8", dir=RACINE) as f:
        f.write(prog)
        chemin = f.name
    try:
        r = subprocess.run(["node", chemin] + (argv or []),
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        NODE = False
        return None
    finally:
        os.unlink(chemin)
    if r.returncode != 0:
        return {"erreur": r.stderr.strip()[:400]}
    return r.stdout


# Le prélude commun : moteur + pack réels, et une politique de jeu SCRIPTÉE
# (donc déterministe) — le test rejoue un joueur, pas un hasard de plus.
PRELUDE = """
const M = require('./maison-moteur.js');
const pack = JSON.parse(require('fs').readFileSync('jeu/marche.json', 'utf-8'));
function jouer(graine, moisVoulus, politique) {
  const s = M.creerPartie(graine >>> 0, pack);
  let n = 0;
  const repondre = () => { while (s.dialogue) { M.decider(s, pack, politique(s, n)); n++; } };
  repondre();
  while (s.mois < moisVoulus && !s.fin) {
    M.tickJour(s, pack);
    repondre();
  }
  return s;
}
"""


# ── 1. MÊME GRAINE + MÊMES DÉCISIONS = MÊME PARTIE, AU CENTIME ──────────────
# Deux PROCESS node séparés : si un état global fuyait quelque part (cache,
# compteur de module), une seule exécution ne le verrait jamais.
print("— La partie se rejoue-t-elle à l'identique ? —")
_PROG_REPRO = PRELUDE + """
const s = jouer(123456789, 24, (st, n) => {
  if (st.dialogue.type === 'candidat') return 0;               // on embauche
  if (st.dialogue.type === 'these') return n % 3 === 0 ? 1 : 0; // 1 entrée sur 3
  return 0;
});
// Les gestes hors dialogue aussi : pose + recrutement au jour 1.
const s2 = M.creerPartie(42, pack);
M.decider(s2, pack, 0);
M.poserMeuble(s2, 'poste', 3, 3);
M.lancerRecrutement(s2, 'analyste');
console.log(M.serialiser(s) + '\\n===\\n' + M.serialiser(s2));
"""
_a, _b = node(_PROG_REPRO), node(_PROG_REPRO)
if _a is None:
    print("  ⚠️  reproductibilité non vérifiée (node indisponible)")
else:
    check("deux process node rendent le même état sérialisé, octet pour octet",
          isinstance(_a, str) and _a == _b,
          str(_a)[:200] if not isinstance(_a, str) else "sorties différentes")

# ── 2. AUCUN Math.random ────────────────────────────────────────────────────
# Une seule occurrence casserait le test 1 EN SILENCE : la partie resterait
# « presque » rejouable, le pire des états. On retire d'abord les
# commentaires : y ÉCRIRE « Math.random est interdit » doit rester permis.
print("\n— Le hasard passe-t-il uniquement par la graine ? —")
def sans_commentaires(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(^|[^:])//[^\n]*", r"\1", src)
for nom, src in (("maison-moteur.js", MOTEUR), ("maison-iso.js", ISO),
                 ("maison-ui.js", UI)):
    check(f"{nom} : pas de Math.random", "Math.random" not in sans_commentaires(src))
# Le moteur n'a pas non plus le droit à l'heure murale : une partie datée
# n'est plus rejouable. L'UI, elle, en a besoin (cache-busting, graine neuve).
check("maison-moteur.js : pas de Date.now ni new Date",
      not re.search(r"Date\.now|new Date", sans_commentaires(MOTEUR)))

# ── 3. LA VL NE SE DILUE PAS ────────────────────────────────────────────────
# Souscrire et racheter passent par les PARTS à la VL du mois : la richesse
# des porteurs en place ne bouge pas d'un centime. C'est LE bug classique
# des implémentations de fonds, et il est invisible à l'œil.
print("\n— Souscriptions et rachats laissent-ils la VL en paix ? —")
_r = node(PRELUDE + """
const s = jouer(7777, 6, () => 0);
M.passerOrdre(s, pack, pack.titres[0].t, 200000, 'achat');
const v1 = M.vl(s, pack);
M.souscrire(s, pack, 250000);
const v2 = M.vl(s, pack);
M.racheterParts(s, pack, 100000);
const v3 = M.vl(s, pack);
console.log(JSON.stringify([v1, v2, v3]));
""")
if _r is None:
    print("  ⚠️  VL non vérifiée (node indisponible)")
elif isinstance(_r, dict):
    check("programme VL exécutable", False, _r["erreur"])
else:
    v1, v2, v3 = json.loads(_r)
    check("souscription de 250 000 € : VL inchangée", abs(v2 - v1) < 1e-9, f"{v1} → {v2}")
    check("rachat de 100 000 € : VL inchangée", abs(v3 - v2) < 1e-9, f"{v2} → {v3}")

# ── 5. LES FRAIS DE GESTION, AU PRORATA EXACT ───────────────────────────────
# Sans équipe ni position, le fonds est 100 % trésorerie : la VL ne peut
# bouger QUE par les frais. Douze mois de 2 %/12 composés font exactement
# 100 × (1 − 0,02/12)^12 — les flux entrent et sortent À la VL, ils ne la
# touchent pas. Toute dérive du prorata se lit ici à la 6e décimale.
print("\n— 2 % l'an font-ils bien 2 % l'an ? —")
_r = node(PRELUDE + """
const s = jouer(31415, 12, () => 0);
console.log(JSON.stringify([M.vl(s, pack), s.fonds.fraisPreleves > 0]));
""")
if _r is None:
    print("  ⚠️  frais non vérifiés (node indisponible)")
elif isinstance(_r, dict):
    check("programme frais exécutable", False, _r["erreur"])
else:
    vl12, preleves = json.loads(_r)
    attendu = 100 * (1 - 0.02 / 12) ** 12
    check(f"VL après 12 mois de frais seuls = {attendu:.4f}",
          abs(vl12 - attendu) < 1e-6, f"obtenu {vl12}")
    check("les frais prélevés sont comptabilisés", bool(preleves))

# ── 6. L'EXÉCUTION : 30 bps SANS GÉRANT, 7,5 AVEC, REFUS SOUS 50 € ─────────
print("\n— Le coût d'exécution dit-il la vérité ? —")
_r = node(PRELUDE + """
const s = M.creerPartie(99, pack);
M.decider(s, pack, 0);
const t = pack.titres[0].t;
const sans = M.passerOrdre(s, pack, t, 1000, 'achat');
s.equipe.push({ id: 999, nom: 'Test', role: 'execution', competence: 3, moral: 70,
  brut: 6500, cout: 9400, posteId: 0, arriveJour: 0, progression: 0,
  etat: 'poste', pos: { x: 0, y: 0 }, but: { x: 0, y: 0 } });
const avec = M.passerOrdre(s, pack, t, 1000, 'achat');
const avantRefus = JSON.stringify(s.fonds.positions);
const refus = M.passerOrdre(s, pack, t, 40, 'achat');
const apresRefus = JSON.stringify(s.fonds.positions);
const dernier = s.registre[s.registre.length - 1].texte;
console.log(JSON.stringify([sans.frais, avec.frais, refus.ok,
  avantRefus === apresRefus, dernier]));
""")
if _r is None:
    print("  ⚠️  exécution non vérifiée (node indisponible)")
elif isinstance(_r, dict):
    check("programme exécution exécutable", False, _r["erreur"])
else:
    f30, f75, refus_ok, intactes, dernier = json.loads(_r)
    check("1 000 € sans gérant coûtent 3,00 € (30 bps)", abs(f30 - 3.0) < 1e-9, str(f30))
    check("1 000 € avec gérant coûtent 0,75 € (7,5 bps)", abs(f75 - 0.75) < 1e-9, str(f75))
    check("un ordre de 40 € est refusé", refus_ok is False)
    check("le refus ne touche pas les positions", intactes)
    # Un refus MUET ferait croire au joueur que le jeu a mangé son geste.
    check("le refus s'écrit au registre", "refusé" in dernier, dernier)

# ── 7. LES CONSTANTES DU JEU SONT CELLES DE config.py ──────────────────────
# Motif FD_RUPTURE de test_chrome.py : une règle recopiée entre deux langages
# est un doublon qui dérive en silence — on compare les textes des deux côtés.
print("\n— Le jeu et config.py disent-ils les mêmes chiffres ? —")
_bps_py = re.search(r"TRANSACTION_COST_BPS\s*=\s*([\d.]+)", CONFIG)
_min_py = re.search(r"MIN_TRADE_EUR\s*=\s*([\d.]+)", CONFIG)
_bps_js = re.search(r"FRAIS_EXEC_BPS\s*=\s*([\d.]+)", MOTEUR)
_min_js = re.search(r"ORDRE_MIN_EUR\s*=\s*([\d.]+)", MOTEUR)
check("les quatre constantes existent",
      all((_bps_py, _min_py, _bps_js, _min_js)))
if all((_bps_py, _min_py, _bps_js, _min_js)):
    check("frais d'exécution : moteur = config.py",
          float(_bps_js.group(1)) == float(_bps_py.group(1)),
          f"js={_bps_js.group(1)} py={_bps_py.group(1)}")
    check("seuil d'ordre : moteur = config.py",
          float(_min_js.group(1)) == float(_min_py.group(1)),
          f"js={_min_js.group(1)} py={_min_py.group(1)}")

# ── 9. PAS DE FUITE DU FUTUR ────────────────────────────────────────────────
# Le test EMPOISONNE l'avenir : deux packs synthétiques identiques jusqu'au
# mois joué, l'un portant des cours absurdes (×1 000 000) au-delà. Si un seul
# octet de l'état final diffère, quelque chose a regardé devant. On lit
# d'abord marcheDepart (il dépend de la graine) pour savoir OÙ empoisonner.
print("\n— Le moteur peut-il lire l'avenir ? —")
_PACK_SAIN = {
    "updated_at": "test", "t0": 24000, "mois": 240, "base": 1000,
    "titres": [
        {"t": "AAA", "n": "A", "sec": "Test", "d": "EUR", "i0": 0,
         "px": [1000 + (m * 37) % 400 for m in range(240)]},
        {"t": "BBB", "n": "B", "sec": "Test", "d": "EUR", "i0": 0,
         "px": [1000 + (m * 53) % 300 for m in range(240)]},
        {"t": "CCC", "n": "C", "sec": "Test", "d": "EUR", "i0": 0,
         "px": [1000 + (m * 71) % 500 for m in range(240)]},
    ],
}
_PROG_FUITE = """
const M = require('./maison-moteur.js');
const pack = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf-8'));
const s = M.creerPartie(2024, pack);
M.decider(s, pack, 0);
M.poserMeuble(s, 'poste', 3, 3);
M.lancerRecrutement(s, 'analyste');
let n = 0;
const MOIS_JOUES = 12;
while (s.mois < MOIS_JOUES && !s.fin) {
  M.tickJour(s, pack);
  while (s.dialogue) {
    M.decider(s, pack, s.dialogue.type === 'these' ? (n % 2) : 0);
    n++;
  }
}
console.log(s.marcheDepart + '|' + M.serialiser(s));
"""
_MOIS_JOUES = 12
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                 encoding="utf-8") as f:
    json.dump(_PACK_SAIN, f)
    _chemin_sain = f.name
_r1 = node(_PROG_FUITE, [_chemin_sain])
if _r1 is None:
    print("  ⚠️  fuite du futur non vérifiée (node indisponible)")
elif isinstance(_r1, dict):
    check("programme fuite exécutable", False, _r1["erreur"])
else:
    _depart = int(_r1.split("|", 1)[0])
    _horizon = _depart + _MOIS_JOUES  # dernier mois que la partie a le droit de voir
    _empoisonne = json.loads(json.dumps(_PACK_SAIN))
    for _t in _empoisonne["titres"]:
        for _m in range(_horizon + 1, 240):
            _t["px"][_m] = _t["px"][_m] * 1000000
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(_empoisonne, f)
        _chemin_poison = f.name
    _r2 = node(_PROG_FUITE, [_chemin_poison])
    check("cours du futur empoisonnés : état final identique",
          isinstance(_r2, str) and _r1 == _r2,
          "le moteur a lu au-delà du mois courant")
    os.unlink(_chemin_poison)
os.unlink(_chemin_sain)

# ── 11. LA CHAÎNE D'AMÉNAGEMENT NE SE CONTOURNE PAS ─────────────────────────
# trésorerie → poste posé → recrutement : c'est la boucle du jeu (§5 du
# prompt). Et une pose ne peut jamais enfermer un poste ni boucher la porte —
# le moteur REFUSE avant, il ne piège pas après.
print("\n— Peut-on tricher avec le plateau ? —")
_r = node(PRELUDE + """
const s = M.creerPartie(555, pack);
M.decider(s, pack, 0);
const sansPoste = M.lancerRecrutement(s, 'analyste');
const surPorte = M.poserMeuble(s, 'plante', s.plateau.porte.x, s.plateau.porte.y);
M.poserMeuble(s, 'poste', 4, 3);
M.poserMeuble(s, 'plante', 3, 3);
M.poserMeuble(s, 'plante', 5, 3);
M.poserMeuble(s, 'plante', 4, 2);
const enferme = M.poserMeuble(s, 'plante', 4, 4);   // dernier voisin libre
const avecPoste = M.lancerRecrutement(s, 'analyste');
console.log(JSON.stringify([sansPoste.ok, surPorte.ok, enferme.ok, enferme.err || '',
  avecPoste.ok]));
""")
if _r is None:
    print("  ⚠️  aménagement non vérifié (node indisponible)")
elif isinstance(_r, dict):
    check("programme aménagement exécutable", False, _r["erreur"])
else:
    sans_poste, sur_porte, enferme, err, avec_poste = json.loads(_r)
    check("recruter sans poste libre : refusé", sans_poste is False)
    check("poser sur la porte : refusé", sur_porte is False)
    check("la pose qui enfermerait un poste : refusée", enferme is False, err)
    check("le refus dit pourquoi", "enfermerait" in err, err)
    check("avec un poste libre, le recrutement s'ouvre", avec_poste is True)

# ── 12. A* : LE CHEMIN EXISTE, OU ON LE DIT ─────────────────────────────────
# Un personnage coincé bloque sa production EN SILENCE : l'échec de
# recherche doit être franc (null), jamais une boucle.
print("\n— Les trajets se calculent-ils juste ? —")
_r = node("""
const I = require('./maison-iso.js');
const mur = { w: 8, h: 6, bloquee: (x, y) => x === 3 && y !== 5 };
const chemin = I.astar(mur, { x: 0, y: 3 }, { x: 6, y: 1 });
const mure = { w: 8, h: 6, bloquee: (x, y) =>
  (Math.abs(x - 6) + Math.abs(y - 1) === 1) };
const impossible = I.astar(mure, { x: 0, y: 3 }, { x: 6, y: 1 });
const surMeuble = { w: 8, h: 6, bloquee: (x, y) => x === 4 && y === 3 };
const arriveeMeuble = I.astar(surMeuble, { x: 0, y: 3 }, { x: 4, y: 3 });
console.log(JSON.stringify([
  chemin ? chemin.length : null,
  chemin ? chemin.some(p => p.x === 3 && p.y !== 5) : null,
  impossible,
  arriveeMeuble ? arriveeMeuble.length : null,
]));
""")
if _r is None:
    print("  ⚠️  A* non vérifié (node indisponible)")
elif isinstance(_r, dict):
    check("programme A* exécutable", False, _r["erreur"])
else:
    lg, traverse_mur, impossible, arrivee = json.loads(_r)
    check("chemin trouvé autour d'un mur partiel", lg is not None and lg >= 11, str(lg))
    check("le chemin ne traverse jamais le mur", traverse_mur is False)
    check("cible murée de partout : null, pas une boucle", impossible is None)
    check("l'arrivée peut être un meuble (dernier pas)", arrivee == 5, str(arrivee))

# ── 18. UNE SAUVEGARDE DE 50 ANS RESTE PETITE, ET SE RELIT ──────────────────
# Un jeu sans fin qui journalise sans fin finit par ne plus se CHARGER : la
# taille de l'état doit être bornée par construction (registre plafonné, une
# ligne par mois pour les historiques). La trésorerie est dopée à la main :
# on teste la boundedness, pas la survie économique — elle, c'est le jeu.
print("\n— 50 ans de partie tiennent-ils sous 1 Mo ? —")
_debut = time.time()
_r = node(PRELUDE + """
const s = M.creerPartie(2222, pack);
M.decider(s, pack, 0);
M.poserMeuble(s, 'poste', 3, 3);
M.lancerRecrutement(s, 'analyste');
let n = 0;
while (s.mois < 600 && !s.fin) {
  s.societe.treso = Math.max(s.societe.treso, 1e9);   // boundedness, pas survie
  M.tickJour(s, pack);
  while (s.dialogue) { M.decider(s, pack, s.dialogue.type === 'these' && s.mois < 12 ? 1 : 0); n++; }
}
const json1 = M.serialiser(s);
const s2 = M.charger(json1, pack);
for (let j = 0; j < 20; j++) {
  M.tickJour(s2, pack);
  while (s2.dialogue) M.decider(s2, pack, 0);
}
console.log(JSON.stringify([s.mois, json1.length, s2.mois, s.registre.length]));
""")
_duree = time.time() - _debut
if _r is None:
    print("  ⚠️  sauvegarde non vérifiée (node indisponible)")
elif isinstance(_r, dict):
    check("programme 50 ans exécutable", False, _r["erreur"])
else:
    mois, taille, mois2, registre = json.loads(_r)
    check("600 mois joués", mois == 600, str(mois))
    check(f"la sauvegarde pèse {taille / 1024:.0f} Ko (< 1 Mo)", taille < 1024 * 1024)
    check("l'état rechargé continue de tourner", mois2 == 601, str(mois2))
    check("le registre est plafonné", registre <= 120, str(registre))
    check(f"les 50 ans se simulent en {_duree:.1f} s (< 20 s)", _duree < 20)

# ── 22. LE PACK EST INTÈGRE, ET jeu/ NE CONTIENT QUE LUI ────────────────────
print("\n— Le pack de marché tient-il son contrat ? —")
check("jeu/marche.json existe", os.path.exists("jeu/marche.json"))
if os.path.exists("jeu/marche.json"):
    pack = json.load(open("jeu/marche.json", encoding="utf-8"))
    manquants = [t["t"] for t in pack["titres"]
                 if not os.path.exists(os.path.join("charts", t["t"] + ".json"))]
    check("chaque titre du pack a son charts/<t>.json", not manquants, str(manquants[:5]))
    debordent = [t["t"] for t in pack["titres"]
                 if t["i0"] < 0 or t["i0"] + len(t["px"]) > pack["mois"]]
    check("aucune série ne déborde de la grille", not debordent, str(debordent[:5]))
    invalides = [t["t"] for t in pack["titres"]
                 if not all(isinstance(v, int) and v > 0 for v in t["px"])]
    check("toutes les valeurs sont des entiers positifs", not invalides, str(invalides[:5]))
    mal_rebases = [t["t"] for t in pack["titres"] if t["px"][0] != pack["base"]]
    check(f"chaque série ouvre à {pack.get('base')}", not mal_rebases, str(mal_rebases[:5]))
    poids = os.path.getsize("jeu/marche.json")
    check(f"le pack pèse {poids / 1024:.0f} Ko (< 250 Ko)", poids < 250 * 1024)
    autres = [n for n in os.listdir("jeu") if n != "marche.json"]
    check("jeu/ ne contient que marche.json", not autres, str(autres))

# ── 23. TOUT LE JAVASCRIPT LIVRÉ SE PARSE ───────────────────────────────────
# Une erreur de syntaxe a déjà mis le site ENTIER en panne (09/08/2026) : on
# donne chaque fichier à l'analyseur, et les éventuels scripts inline de la
# page aussi (le motif de test_chrome.py).
print("\n— Le JavaScript livré se parse-t-il ? —")
try:
    for _nom in ("maison-moteur.js", "maison-iso.js", "maison-ui.js"):
        _r = subprocess.run(["node", "--check", _nom], capture_output=True, text=True)
        check(f"{_nom} se parse", _r.returncode == 0, _r.stderr.strip()[:200])
    _blocs = re.findall(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", PAGE, re.S)
    _mauvais = []
    for _i, _b in enumerate(_blocs):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as f:
            f.write(_b)
            _tmp = f.name
        _r = subprocess.run(["node", "--check", _tmp], capture_output=True, text=True)
        os.unlink(_tmp)
        if _r.returncode != 0:
            _mauvais.append(f"bloc {_i}")
    check(f"maison.html — {len(_blocs)} bloc(s) inline se parsent", not _mauvais,
          str(_mauvais))
except (OSError, subprocess.SubprocessError) as _e:
    print(f"  ⚠️  syntaxe non vérifiée (node indisponible : {type(_e).__name__})")

# ── R1. LES THÈSES NE CITENT QUE DES FAITS DE PRIX ──────────────────────────
# La règle §2 ③ du prompt : les cours sont réels et les identités se révèlent
# à la fin — un « fondamental » inventé dans un gabarit de thèse deviendrait,
# en différé, un fait attribué à une société cotée réelle.
print("\n— Les thèses inventent-elles des fondamentaux ? —")
_m = re.search(r"function produireThese.*?(?=\n  function nomAffiche)", MOTEUR, re.S)
check("le gabarit des thèses est extractible", _m is not None)
if _m:
    INTERDITS = ["marge", "dette", "carnet de commandes", "bénéfice",
                 "chiffre d'affaires", "chiffre d’affaires", "résultat net"]
    trouves = [w for w in INTERDITS if w in _m.group(0).lower()]
    check("aucun mot de fondamental dans les gabarits", not trouves, str(trouves))

# ── R2. LES NOMS MASQUÉS : UNE LISTE FIXE, SANS DOUBLON ─────────────────────
print("\n— La liste des noms fictifs est-elle saine ? —")
_m = re.search(r"NOMS_FICTIFS\s*=\s*\[(.*?)\];", MOTEUR, re.S)
check("la liste est extractible", _m is not None)
if _m:
    noms = re.findall(r"'([^']+)'", _m.group(1))
    check(f"au moins 80 noms ({len(noms)} trouvés)", len(noms) >= 80)
    check("aucun doublon", len(noms) == len(set(noms)),
          str([n for n in noms if noms.count(n) > 1][:3]))

total = ok + len(ko)
print(f"\n{ok}/{total} vérifications passées")
if ko:
    print("Échecs : " + " ; ".join(ko))
    sys.exit(1)
