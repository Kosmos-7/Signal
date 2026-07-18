"""
⚠️  SCRIPT ARCHIVÉ (2026-07-18) — NE PLUS EXÉCUTER.

La migration v2 a été appliquée : tous les ordres de portfolio.json portent les
champs v2 (vérifié lors de l'audit du 2026-07-18 : 27 ACHAT avec frais_achat_eur,
9 VENTE avec frais_vente_eur). Un re-run recalculerait total_frais_payes /
performance / performance_brute et écraserait les valeurs maintenues depuis par
portfolio_agent.py — risque de divergence si les formules ont évolué.
Conservé dans notes/archive/ pour la traçabilité méthodologique uniquement.

migrate_orders_v2.py — Migration des ordres historiques vers le modèle v2.

Phase 1 du plan : applique rétroactivement aux 34 ordres existants
  - frais d'achat (one-way, ~7.5 bps)
  - frais de vente (one-way, ~7.5 bps)
  - PFU 30% sur les plus-values réalisées

Pour les ventes partielles : FIFO (First In, First Out) — la convention par défaut
en France pour les ventes partielles d'une même ligne sans option PRMP. Comme Signal
n'a jamais fait de vente partielle (toutes les ventes ont liquidé la position entière),
le FIFO est trivial : la base fiscale = somme des achats de cette ligne (incluant frais).

Sortie :
  - portfolio.backup-pre-v2.json : snapshot du portfolio avant migration
  - portfolio.json : mis à jour avec ordres + compteurs cumulatifs v2
  - migration_v2_report.txt : récap de ce qui a été changé

Idempotence :
  - Si un ordre a déjà un champ `frais_achat_eur` (resp `frais_vente_eur`),
    on le considère comme déjà migré et on ne re-calcule pas.
  - Possibilité de re-run sans risque.

Usage : python migrate_orders_v2.py [--dry-run]
"""

import json
import sys
import copy
from datetime import date
from collections import defaultdict
import config


DRY_RUN = "--dry-run" in sys.argv


def is_already_migrated(ordre):
    """Un ordre est considéré comme déjà migré v2 s'il contient au moins
    un des champs introduits par Phase 1."""
    if ordre.get("type") == "ACHAT":
        return "frais_achat_eur" in ordre
    if ordre.get("type") == "VENTE":
        return "frais_vente_eur" in ordre
    return True  # APPORT et autres types : pas concernés


def migrate_achat(ordre):
    """Applique les frais d'achat rétroactivement.

    Logique : le `montant` actuel représente le brut (prix × qté en EUR).
    On le retransforme en (brut + frais) pour avoir la base fiscale correcte.
    """
    brut = ordre.get("montant", 0)
    if brut <= 0:
        return ordre, 0
    new_montant, frais = config.apply_buy_cost(brut)
    ordre["montant_brut_eur"] = brut
    ordre["frais_achat_eur"]  = frais
    ordre["montant"]          = new_montant  # désormais inclut frais (base fiscale)
    return ordre, frais


def migrate_vente(ordre, base_fiscale_eur):
    """Applique frais vente + PFU rétroactivement.

    Args:
        ordre: l'ordre VENTE
        base_fiscale_eur: somme des montants_investis (post-migration des achats)
                          des achats liés à cette vente

    Le `montant` original représentait le brut de vente. On le retransforme.
    """
    brut = ordre.get("montant", 0)
    if brut <= 0:
        return ordre, 0, 0, 0
    r = config.apply_sell_cost_and_tax(brut, base_fiscale_eur)
    ordre["montant_brut_eur"]    = brut
    ordre["frais_vente_eur"]     = r["frais_vente_eur"]
    ordre["plus_value_eur"]      = r["plus_value_eur"]
    ordre["impot_pfu_eur"]       = r["impot_pfu_eur"]
    ordre["perte_reportable_eur"]= r["perte_reportable_eur"]
    ordre["montant"]             = r["cash_recupere_eur"]  # cash effectivement reçu
    ordre["pnl_eur"]             = r["plus_value_eur"]      # update : plus-value après frais
    return ordre, r["frais_vente_eur"], r["impot_pfu_eur"], r["perte_reportable_eur"]


def main():
    try:
        with open("portfolio.json", encoding="utf-8") as f:
            portfolio = json.load(f)
    except FileNotFoundError:
        print("❌ portfolio.json introuvable")
        return

    # Backup brut avant toute modification
    if not DRY_RUN:
        with open("portfolio.backup-pre-v2.json", "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        print("✓ Backup créé : portfolio.backup-pre-v2.json")

    ordres = portfolio.get("ordres", [])
    print(f"\n▸ {len(ordres)} ordres à examiner")

    # On trie chrono croissant pour respecter FIFO sur les bases fiscales
    ordres_chrono = sorted(ordres, key=lambda o: (o.get("date", ""), o.get("ticker", "")))

    # Tracking par ticker des achats restants (pour le FIFO sur les ventes)
    # Format : achats_par_ticker[ticker] = [(date, montant_post_migration), ...]
    achats_par_ticker = defaultdict(list)

    # Compteurs cumulatifs
    total_frais   = 0.0
    total_impots  = 0.0
    total_pertes  = 0.0
    nb_migres     = 0
    nb_skipped    = 0
    report_lines  = []

    for o in ordres_chrono:
        t = o.get("type", "")
        ticker = o.get("ticker", "?")
        dte = o.get("date", "?")

        if is_already_migrated(o):
            nb_skipped += 1
            # Mais on tient quand même la compta cumulative à jour pour la cohérence
            total_frais  += o.get("frais_achat_eur", 0) + o.get("frais_vente_eur", 0)
            total_impots += o.get("impot_pfu_eur", 0)
            total_pertes += o.get("perte_reportable_eur", 0)
            if t == "ACHAT":
                achats_par_ticker[ticker].append((dte, o.get("montant", 0)))
            elif t == "VENTE":
                # Consomme les achats FIFO
                achats_par_ticker[ticker] = []  # signal a toujours liquidé en entier
            continue

        if t == "ACHAT":
            o, frais = migrate_achat(o)
            total_frais += frais
            achats_par_ticker[ticker].append((dte, o["montant"]))
            report_lines.append(f"  ACHAT {dte} {ticker}: brut {o['montant_brut_eur']:.2f}€ + frais {frais:.2f}€ → montant_investi {o['montant']:.2f}€")
            nb_migres += 1

        elif t == "VENTE":
            # Base fiscale = somme des achats FIFO (Signal a toujours liquidé entier)
            base = sum(m for _, m in achats_par_ticker[ticker])
            if base <= 0:
                # Vente sans achat tracé (cas anormal — vente d'une position initiale ?)
                # Fallback : utilise pnl_eur original pour reconstituer une base
                base = o.get("montant", 0) - o.get("pnl_eur", 0)
            o, frais_v, impot, perte = migrate_vente(o, base)
            total_frais  += frais_v
            total_impots += impot
            total_pertes += perte
            achats_par_ticker[ticker] = []  # vidé
            report_lines.append(f"  VENTE {dte} {ticker}: brut {o['montant_brut_eur']:.2f}€, +/-value {o['plus_value_eur']:+.2f}€, PFU {impot:.2f}€, cash {o['montant']:.2f}€")
            nb_migres += 1

        elif t == "APPORT":
            # Apports de capital : pas concernés par les frais/impôts
            continue

    total_frais  = round(total_frais, 2)
    total_impots = round(total_impots, 2)
    total_pertes = round(total_pertes, 2)

    print(f"\n▸ {nb_migres} ordres migrés, {nb_skipped} déjà à jour (skipped)")
    print(f"▸ Frais cumulés rétroactifs   : {total_frais:.2f} €")
    print(f"▸ Impôts cumulés rétroactifs  : {total_impots:.2f} €")
    print(f"▸ Pertes reportables cumulées : {total_pertes:.2f} €")

    # Mettre à jour les compteurs racine du portfolio
    portfolio["total_frais_payes"]        = total_frais
    portfolio["total_impots_payes"]       = total_impots
    portfolio["total_pertes_reportables"] = total_pertes

    # Mettre à jour montants_investis dans les positions ouvertes
    # (= post-migration, inclut les frais d'achat)
    for pos in portfolio.get("positions", []):
        ticker = pos.get("ticker", "")
        # Somme des achats post-migration de ce ticker
        achats_actifs = achats_par_ticker.get(ticker, [])
        if achats_actifs:
            nouveau_montant_investi = round(sum(m for _, m in achats_actifs), 2)
            ancien = pos.get("montant_investi", 0)
            if abs(nouveau_montant_investi - ancien) > 0.01:
                pos["montant_investi"] = nouveau_montant_investi
                # Recalcule la perf €  (en %) avec la nouvelle base
                if nouveau_montant_investi > 0 and "valeur_actuelle" in pos:
                    pos["performance"] = round((pos["valeur_actuelle"] - nouveau_montant_investi) / nouveau_montant_investi * 100, 2)

    # Recalcul des champs de performance
    capital_actuel = portfolio.get("capital_actuel", 0)
    capital_initial = portfolio.get("capital_initial", 1)
    portfolio["performance"] = round((capital_actuel - capital_initial) / capital_initial * 100, 2)
    portfolio["performance_brute"] = round((capital_actuel + total_frais + total_impots - capital_initial) / capital_initial * 100, 2)

    # Préserve l'ordre original (le plus récent en premier) — on a juste muté les dicts
    # in-place via les références dans `ordres_chrono`. La liste `portfolio["ordres"]` est
    # déjà à jour.

    # Sauvegarde le rapport
    report = (
        f"Migration v2 — {date.today()}\n"
        f"{'=' * 60}\n"
        f"Ordres examinés    : {len(ordres)}\n"
        f"Ordres migrés      : {nb_migres}\n"
        f"Ordres déjà v2     : {nb_skipped}\n"
        f"Frais cumulés      : {total_frais:.2f} €\n"
        f"Impôts cumulés     : {total_impots:.2f} €\n"
        f"Pertes reportables : {total_pertes:.2f} €\n"
        f"\nDétail :\n"
        + "\n".join(report_lines)
    )

    if DRY_RUN:
        print("\n🔬 DRY-RUN : portfolio.json non écrit.")
        print(f"\n--- Aperçu rapport ---\n{report[:1500]}...")
    else:
        with open("portfolio.json", "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        with open("migration_v2_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✓ portfolio.json mis à jour")
        print(f"✓ migration_v2_report.txt écrit")


if __name__ == "__main__":
    main()
