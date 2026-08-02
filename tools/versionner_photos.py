#!/usr/bin/env python3
"""Empreinte de contenu pour chaque photo, afin que son remplacement se voie.

LE DÉFAUT. Une photo remplacée garde le même chemin, « assets/titres/NVDA.jpg ».
Le navigateur et le CDN de GitHub Pages servent alors leur copie en cache, et le
visiteur voit l'ANCIENNE image sous la NOUVELLE légende : le registre JSON, lui,
est demandé avec « ?v=<date> » et se rafraîchit tous les jours. Constaté sur la
fiche NVDA, dont la légende annonçait le superchip GB200 au-dessus de la carte
HGX B200 qu'elle remplaçait.

LA CORRECTION. Chaque entrée du registre reçoit un champ « v », les huit
premiers caractères de l'empreinte SHA-256 du fichier. La fiche demande alors
« NVDA.jpg?v=3f2a… ». Une image inchangée garde son adresse, donc reste en
cache, ce qui préserve la performance ; une image remplacée change d'adresse et
est rechargée immédiatement. C'est le contraire d'un « ?v=<date> » global, qui
ferait tout retélécharger chaque jour pour rien.

À RELANCER après toute modification d'une photo. Le script est idempotent : il
n'écrit que si une empreinte a bougé, et signale les entrées orphelines.

Usage : python3 tools/versionner_photos.py [--verifier]
"""
import argparse
import hashlib
import json
import os
import sys

REGISTRES = [
    ("assets/titres/LEGENDES.json", "assets/titres"),
    ("assets/themes/LEGENDES.json", "assets/themes"),
]


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifier", action="store_true",
                    help="ne rien écrire, sortir en erreur si une empreinte "
                         "est absente ou périmée (utilisable en garde-fou)")
    a = ap.parse_args()

    perimes, orphelins, total = [], [], 0
    for registre, dossier in REGISTRES:
        if not os.path.exists(registre):
            continue
        d = json.load(open(registre, encoding="utf-8"))
        change = False
        for cle, entree in d.items():
            if not isinstance(entree, dict):
                continue
            f = os.path.join(dossier, f"{cle}.jpg")
            if not os.path.exists(f):
                orphelins.append(f"{registre}:{cle}")
                continue
            total += 1
            v = empreinte(f)
            if entree.get("v") != v:
                perimes.append(f"{cle} {entree.get('v') or '(aucune)'} -> {v}")
                entree["v"] = v
                change = True
        if change and not a.verifier:
            json.dump(dict(sorted(d.items())), open(registre, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"{registre} mis à jour")

    print(f"{total} photos, {len(perimes)} empreintes à corriger")
    for p in perimes[:20]:
        print("   ", p)
    if orphelins:
        # Une entrée sans fichier ferait afficher une image cassée : on le dit.
        print(f"⚠ {len(orphelins)} entrées sans fichier : {', '.join(orphelins[:8])}")
    if a.verifier and (perimes or orphelins):
        sys.exit(1)


if __name__ == "__main__":
    main()
