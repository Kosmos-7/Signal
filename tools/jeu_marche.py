#!/usr/bin/env python3
"""jeu_marche.py — pack de marché compact pour La Maison (jeu/marche.json).

POURQUOI CE FICHIER EXISTE. Le jeu se joue au mois sur des cours réels, mais
il ne peut pas charger les 150 charts/<TICKER>.json (~3,9 Mo) pour démarrer :
son budget de données est de 250 Ko. Ce script relit les charts déjà publiés
et en extrait UNE matrice mensuelle commune, rebasée, compacte — la seule
donnée que la page télécharge.

Ce qu'il ne fait PAS : aucun accès réseau, aucun recalcul de marché. Il ne
fait que rééchantillonner ce que le screener a déjà publié — si un cours est
faux ici, il est faux dans la fiche aussi, et c'est là-bas qu'on le corrige.

Conventions héritées de screener.py (§ PAYLOAD GRAPHIQUE) :
  - abscisse « mois flottant » : année*12 + (mois-1) + (jour-1)/31 ;
    int(t) identifie donc le mois calendaire, quel que soit l'échantillonnage ;
  - le payload mélange mensuel (ancien) et hebdo (730 derniers jours) : on
    NE suppose jamais un pas régulier, on regroupe par int(t) et on garde la
    dernière valeur de chaque mois — même règle pour les deux segments.

Choix assumé, en écart avec le prompt (« rebasés à 100, arrondis à l'entier ») :
  rebasage à 1000, entiers. À base 100, l'entier écrase tout mouvement
  mensuel < 1 % — fréquent sur les titres peu volatils. À base 1000 la
  résolution est de 0,1 % pour le même poids (4-5 chiffres par valeur).

    python tools/jeu_marche.py
"""
import glob
import json
import os
import sys
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Paramètres du pack ───────────────────────────────────────────────────────
FENETRE_MOIS = 240      # 20 ans de jeu sur données réelles
MIN_POINTS_TOTAL = 150  # éligibilité : profondeur d'historique mensuel (prompt §12.2)
MIN_POINTS_FENETRE = 24 # au moins 2 ans DANS la fenêtre, sinon le titre ne sert à rien
MAX_TITRES = 80         # budget de poids (~90-120 Ko)
BASE = 1000             # rebasage (cf. docstring)
MAX_TROUS_PCT = 5       # au-delà, la série est trop trouée pour être honnête


def serie_mensuelle(points):
    """[[t, prix], ...] (pas irrégulier) → {mois_int: dernier prix du mois}.

    Regrouper par int(t) traite d'un même geste le segment mensuel et le
    segment hebdo : dans les deux cas on retient la dernière cote du mois.
    """
    par_mois = {}
    for t, v in points:
        if not isinstance(v, (int, float)) or v <= 0:
            continue
        par_mois[int(t)] = float(v)
    return par_mois


def colonne(par_mois, m0, m1):
    """Série continue sur [m0, m1] : trous comblés en report du dernier cours.

    Un mois sans cote (suspension, jour férié au cutoff) recopie le mois
    précédent — c'est un report, pas une invention, et on le compte pour
    rejeter les séries trop trouées.
    """
    px, trous, dernier = [], 0, None
    for m in range(m0, m1 + 1):
        if m in par_mois:
            dernier = par_mois[m]
        elif dernier is not None:
            trous += 1
        if dernier is None:
            return None, 0          # la série ne commence pas encore
        px.append(dernier)
    return px, trous


def construire(racine=RACINE, aujourd_hui=None):
    """Construit le dict du pack (pur : pas d'écriture ici, testable à sec)."""
    with open(os.path.join(racine, "universe.json"), encoding="utf-8") as f:
        stocks = json.load(f).get("stocks") or {}

    candidats = []
    for chemin in sorted(glob.glob(os.path.join(racine, "charts", "*.json"))):
        ticker = os.path.basename(chemin)[:-len(".json")]
        meta = stocks.get(ticker)
        if not meta or not meta.get("secteur") or not meta.get("devise"):
            continue                # identité incomplète : pas de révélation possible
        with open(chemin, encoding="utf-8") as f:
            pts = json.load(f).get("points") or []
        mensuel = serie_mensuelle(pts)
        if len(mensuel) < MIN_POINTS_TOTAL:
            continue
        candidats.append((ticker, meta, mensuel))

    if not candidats:
        raise SystemExit("aucun titre éligible : charts/ ou universe.json vides ?")

    fin = max(max(m) for _, _, m in candidats)
    t0 = fin - (FENETRE_MOIS - 1)

    titres = []
    for ticker, meta, mensuel in candidats:
        debut = max(t0, min(mensuel))
        px, trous = colonne(mensuel, debut, fin)
        if px is None or len(px) < MIN_POINTS_FENETRE:
            continue
        if trous * 100 > len(px) * MAX_TROUS_PCT:
            continue
        base = px[0]
        vals = [round(v * BASE / base) for v in px]
        # L'amplitude doit tenir dans l'entier : un cours tombé sous 1/2000e
        # de sa base arrondirait à ZÉRO — et un zéro n'est pas un cours, c'est
        # une faillite inventée. Constaté sur QUBT (penny stock multiplié par
        # plusieurs milliers) : on ÉCARTE la série plutôt que de la déformer,
        # même choix que le screener pour ses propres bornes.
        if min(vals) < 1:
            continue
        titres.append({
            "t": ticker,
            "n": meta.get("nom", ticker),
            "sec": meta["secteur"],
            "d": meta["devise"],
            "i0": debut - t0,
            "px": vals,
        })

    # Les plus profonds d'abord (le jeu a besoin de longues histoires), puis
    # l'ordre alphabétique fige le pack : deux runs sur les mêmes charts
    # produisent le même fichier, diff git lisible.
    titres.sort(key=lambda x: (-len(x["px"]), x["t"]))
    titres = sorted(titres[:MAX_TITRES], key=lambda x: x["t"])

    return {
        "updated_at": (aujourd_hui or date.today()).isoformat(),
        "t0": t0,
        "mois": FENETRE_MOIS,
        "base": BASE,
        "titres": titres,
    }


def verifier(pack):
    """Le contrat que test_maison.py rejouera : échec bruyant, jamais silencieux."""
    assert pack["titres"], "pack vide"
    for t in pack["titres"]:
        assert 0 <= t["i0"] < pack["mois"], f"{t['t']}: i0 hors grille"
        assert t["i0"] + len(t["px"]) <= pack["mois"], f"{t['t']}: série qui déborde"
        assert all(isinstance(v, int) and v > 0 for v in t["px"]), \
            f"{t['t']}: valeur non finie ou négative"
        assert t["px"][0] == BASE, f"{t['t']}: rebasage faux"


def ecrire(pack, racine=RACINE):
    dossier = os.path.join(racine, "jeu")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, "marche.json")
    tmp = chemin + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)
        os.replace(tmp, chemin)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)          # un .tmp au sol serait committé (cf. .gitignore)
        raise
    # Purge des orphelins : jeu/ ne contient que ce que ce script produit.
    for nom in sorted(os.listdir(dossier)):
        if nom.endswith(".json") and nom != "marche.json":
            os.remove(os.path.join(dossier, nom))
            print(f"purgé : jeu/{nom}")
    return chemin


if __name__ == "__main__":
    pack = construire()
    verifier(pack)
    chemin = ecrire(pack)
    poids = os.path.getsize(chemin)
    print(f"{len(pack['titres'])} titres · grille {pack['mois']} mois "
          f"(t0={pack['t0']}) · {poids/1024:.0f} Ko → {chemin}")
    if poids > 250 * 1024:
        print("::error::pack au-dessus du budget de 250 Ko", file=sys.stderr)
        sys.exit(1)
