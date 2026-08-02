#!/usr/bin/env python3
"""Sixième passe : chercher la MARQUE et le PRODUIT, pas la raison sociale.

CE QUE LES CINQ CAMPAGNES PRÉCÉDENTES ONT TOUTES FAIT PAREIL. Recherche
textuelle, Wikidata P18, catégorie Commons, données structurées, Openverse :
toutes interrogeaient le nom de la société. C'est le bon identifiant pour une
base de données, c'est le mauvais pour une photothèque. Personne ne titre son
image « Vertiv » : on écrit « Liebert UPS », du nom de la marque. Personne
n'écrit « Teradyne » sous un bras robotisé : on écrit « Universal Robots UR5 »,
du nom de la filiale. Personne ne photographie « Constellation Energy » : on
photographie la centrale de Calvert Cliffs.

D'où cette passe, qui inverse la question. Au lieu de demander à Commons ce
qu'il a sur une société, on lui demande ce qu'il a sur les objets que cette
société fabrique, les marques sous lesquelles elle les vend, les filiales qui
les produisent et les sites qu'elle exploite. La correspondance société →
marques est écrite à la main et vérifiée, parce que c'est précisément le savoir
qu'aucune API ne porte.

CE QUE ÇA NE RÉSOUT PAS. La justesse. « Liebert UPS » peut ramener la photo
d'une salle serveurs où l'onduleur n'est pas visible ; « Waymo » ramène aussi
des manifestations contre Waymo. Le barème ordonne, l'examen visuel décide,
comme aux cinq passes précédentes.

PIÈGE DE LICENCE. Rien ne change : domaine public et CC0 sans condition, CC-BY
et CC-BY-SA seulement avec le crédit affiché sur la fiche.

Usage : python3 tools/photos_marques.py [--limite N] [--par-societe N]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from photos_wikidata import _get, COMMONS_API, UA                     # noqa: E402
from photos_produits import score_nom, infos, prepare                 # noqa: E402

# Société → ce sous quoi ses objets sont réellement titrés dans une photothèque.
# Marques commerciales, filiales, modèles, sites exploités. Les filiations non
# évidentes ont été vérifiées : Universal Robots et Mobile Industrial Robots
# appartiennent à Teradyne depuis 2015 et 2018, Liebert est la marque d'onduleurs
# de Vertiv (ex-Emerson Network Power), Comanche Peak et Moss Landing sont
# exploités par Vistra via Luminant, Calvert Cliffs et Byron par Constellation.
MARQUES = {
    # Équipement et composants : le produit porte le nom du modèle.
    "6146.T":  ["wafer dicing saw", "wafer dicing machine", "dicing blade wafer"],
    "6857.T":  ["Advantest", "semiconductor test handler", "IC test system"],
    "8035.T":  ["Tokyo Electron", "coater developer semiconductor",
                "wafer track system"],
    "ASM.AS":  ["ASM International semiconductor", "atomic layer deposition reactor",
                "ALD reactor"],
    "LRCX":    ["Lam Research", "plasma etch chamber", "etch system semiconductor"],
    "TER":     ["Universal Robots UR5", "Universal Robots UR10",
                "Universal Robots collaborative robot", "Mobile Industrial Robots"],
    "MRVL":    ["Marvell semiconductor", "Marvell 88E", "Marvell chip board"],
    "ANET":    ["Arista Networks switch", "Arista 7050", "Arista DCS switch"],
    "CSCO":    ["Cisco Catalyst switch", "Cisco router", "Cisco IP Phone",
                "Cisco ASR router"],
    "CIEN":    ["Ciena optical", "Ciena 6500", "Ciena WaveLogic"],
    "LITE":    ["optical transceiver module", "JDSU laser", "Lumentum laser"],
    "COHR":    ["Coherent laser", "II-VI Incorporated", "laser head industrial"],
    "ASX":     ["Advanced Semiconductor Engineering", "ASE Group Kaohsiung",
                "semiconductor packaging plant"],
    "VRT":     ["Liebert UPS", "Liebert precision cooling", "Emerson Network Power",
                "data center UPS cabinet"],
    "SIE.DE":  ["Siemens Vectron", "Siemens Velaro", "SIMATIC S7",
                "Siemens gas turbine", "Siemens Desiro"],
    "GEV":     ["GE Haliade wind turbine", "General Electric wind turbine",
                "GE gas turbine", "GE Vernova"],

    # Énergie : on photographie le site, pas la holding.
    "CEG":     ["Calvert Cliffs Nuclear Power Plant", "Byron Nuclear Generating Station",
                "Braidwood Nuclear Generating Station", "Nine Mile Point Nuclear",
                "Limerick Generating Station"],
    "VST":     ["Comanche Peak Nuclear Power Plant", "Moss Landing Power Plant",
                "Martin Lake Power Plant"],
    "PWR":     ["Quanta Services", "transmission line construction",
                "power line construction crew"],

    # Santé : le médicament porte son nom, pas celui du laboratoire.
    "GILD":    ["remdesivir", "Veklury", "Truvada", "sofosbuvir", "Gilead Sciences"],
    "ZTS":     ["Zoetis", "veterinary vaccine vial", "animal health vaccine"],

    # Logiciel et internet : produits, filiales, tours qui portent l'enseigne.
    "GOOGL":   ["Waymo self-driving car", "Waymo Jaguar I-Pace", "Google data center",
                "Google Nest thermostat"],
    "CRM":     ["Salesforce Tower San Francisco", "Salesforce Tower"],
    "INTU":    ["TurboTax", "QuickBooks", "Intuit Dome", "Mailchimp"],
    "PDD":     ["Pinduoduo", "Temu package", "Temu app"],
    "TCEHY":   ["Tencent Binhai Mansion", "Tencent Seafront Towers", "WeChat app"],
    "ACN":     ["Accenture Tower", "Accenture building"],
    "NBIS":    ["Nebius data center", "Yandex data center Mantsala"],
    "CRWV":    ["CoreWeave data center"],
    "FICO":    ["Fair Isaac Corporation"],
    "MSCI":    ["MSCI headquarters"],

    # Finance : la place de marché, le distributeur, la carte, le siège nommé.
    "ICE":     ["New York Stock Exchange building", "New York Stock Exchange trading floor"],
    "CME":     ["Chicago Board of Trade Building", "Chicago Mercantile Exchange",
                "CME Group trading floor"],
    "LSEG.L":  ["London Stock Exchange building", "London Stock Exchange Paternoster"],
    "MA":      ["Mastercard credit card", "Mastercard payment terminal", "Maestro card"],
    "JPM":     ["Chase Bank ATM", "Chase Bank branch", "JPMorgan Chase Tower"],
    "MS":      ["Morgan Stanley Building", "1585 Broadway"],
    "BLK":     ["BlackRock headquarters", "iShares"],
    "KKR":     ["30 Hudson Yards", "KKR headquarters"],
    "MCO":     ["7 World Trade Center", "Moody's Corporation"],
    "SPGI":    ["Standard and Poor's", "S&P Global headquarters"],
    "UBSG.SW": ["UBS Bahnhofstrasse", "UBS bank branch", "UBS headquarters Zurich"],
    "CS.PA":   ["Tour AXA La Defense", "AXA insurance building", "AXA headquarters"],
    "BNP.PA":  ["BNP Paribas headquarters", "BNP Paribas branch", "BNP Paribas agence"],
    "MUV2.DE": ["Munich Re headquarters", "Muenchener Rueckversicherung"],
    "CB":      ["Chubb Limited", "Chubb insurance building"],
    "PGR":     ["Progressive Insurance", "Progressive Corporation campus"],
}


# Fiches DEJA illustrees dont la revue d'ensemble a juge l'image faible. Le
# defaut est presque toujours le meme : un siege social anonyme la ou la societe
# fabrique un objet identifiable. NVIDIA, premiere valeur de la watchlist, etait
# illustree par une carte de developpement Jetson ; Intel par un parking a
# Tsukuba ; ASML, l'entreprise de la lithographie EUV, par un immeuble delave.
# On applique ici la methode qui a marche : chercher le PRODUIT.
#
# Rien n'est remplace automatiquement. Le job propose, la revue visuelle
# compare l'ancienne et la nouvelle, et l'on ne substitue que si c'est mieux.
AMELIORATIONS = {
    "NVDA":      ["Nvidia GeForce graphics card", "Nvidia Tesla GPU",
                  "Nvidia die shot", "GeForce RTX graphics card"],
    "INTC":      ["Intel wafer", "Intel Core processor", "Intel Xeon die",
                  "silicon wafer cleanroom"],
    "ASML.AS":   ["ASML lithography", "wafer stepper", "photolithography machine",
                  "EUV lithography"],
    "META":      ["Meta Quest headset", "Oculus Quest", "Meta data center"],
    "MSFT":      ["Xbox Series X", "Microsoft Surface", "Microsoft data center"],
    "005930.KS": ["Samsung Galaxy smartphone", "Samsung DRAM module",
                  "Samsung memory chip"],
    "AMAT":      ["Applied Materials machine", "semiconductor deposition system",
                  "wafer processing equipment"],
    "HSBA.L":    ["HSBC branch", "HSBC bank sign", "HSBC ATM"],
    "AXP":       ["American Express card", "American Express centurion card"],
    "MU":        ["Micron DRAM module", "Crucial SSD", "Micron memory chip"],
    "DELL":      ["Dell PowerEdge server", "Dell XPS laptop", "Dell rack server"],
    "ADBE":      ["Adobe Photoshop box", "Adobe Creative Suite box"],
    "NFLX":      ["Netflix Open Connect appliance", "Netflix DVD envelope"],
    "PYPL":      ["PayPal card reader", "PayPal Zettle terminal"],
    "STX":       ["Seagate hard disk drive", "Seagate Barracuda"],
    "CSCO":      ["Cisco Catalyst switch", "Cisco IP Phone"],
}


# Quinze fiches sans illustration. Elles n'ont ni produit ni marque
# photographiables : ce sont des banques, des assureurs, des fournisseurs
# d'indices, des agences de notation. Reste le LIEU, qui est une photo du monde
# reel attachee a CETTE societe et non a son secteur, exactement comme l'agence
# UBS de la Bahnhofstrasse ou l'usine Schneider Electric deja publiees.
#
# Le premier passage avait echoue faute de connaitre le nom des lieux :
# « BlackRock headquarters » rend un phare, leur siege s'appelle 50 Hudson
# Yards ; « London Stock Exchange building » rend le Royal Exchange, qui est un
# autre batiment. On interroge donc les adresses et les enseignes.
LIEUX = {
    "ACN":     ["Accenture Tower Chicago", "Accenture building Dublin",
                "Accenture office building"],
    "BLK":     ["50 Hudson Yards", "BlackRock office building"],
    "BNP.PA":  ["BNP Paribas agence", "BNP Paribas bank branch",
                "BNP Paribas Fortis branch"],
    "CS.PA":   ["Tour AXA Puteaux", "AXA agence", "AXA insurance office sign"],
    "KKR":     ["30 Hudson Yards", "KKR office New York"],
    "LSEG.L":  ["London Stock Exchange Paternoster Square",
                "Stock Exchange Tower London", "London Stock Exchange Group office"],
    "MA":      ["Mastercard office Purchase New York", "Mastercard sign building",
                "Mastercard acceptance sign"],
    "MCO":     ["7 World Trade Center", "Moody's headquarters New York"],
    "MSCI":    ["MSCI office London", "MSCI building"],
    "MUV2.DE": ["Muenchener Rueckversicherung Koeniginstrasse",
                "Munich Re headquarters Munich", "Munich Re building"],
    "PDD":     ["Pinduoduo headquarters Shanghai", "Pinduoduo office"],
    "SPGI":    ["55 Water Street", "S&P Global office building"],
    "8035.T":  ["Tokyo Electron headquarters", "Akasaka Biz Tower",
                "Tokyo Electron Miyagi", "Tokyo Electron Yamanashi"],
    "6146.T":  ["Disco Corporation Ota Tokyo", "Disco Corporation Hiroshima"],
    "ASX":     ["ASE Kaohsiung plant", "Advanced Semiconductor Engineering Kaohsiung",
                "Nanzih Technology Industrial Park"],
}


def chercher_commons(terme, limite=14):
    """Recherche plein texte de Commons, restreinte aux fichiers."""
    try:
        d = _get(COMMONS_API, {"action": "query", "format": "json",
                               "list": "search", "srnamespace": "6",
                               "srsearch": terme, "srlimit": str(limite)})
    except Exception as e:
        print(f"      ✗ « {terme} » : {type(e).__name__}")
        return []
    return [m["title"][5:] for m in (d.get("query", {}).get("search") or [])
            if m.get("title", "").startswith("File:")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="assets/titres/marques")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--par-societe", type=int, default=3)
    ap.add_argument("--termes", default="",
                    help="recherche ponctuelle, format TICKER=terme|terme ; "
                         "separer plusieurs societes par des virgules. Evite "
                         "d'ajouter une carte figee au fichier pour un essai.")
    ap.add_argument("--lieux", action="store_true",
                    help="chercher le LIEU des quinze fiches sans illustration")
    ap.add_argument("--ameliorer", action="store_true",
                    help="repasser sur des fiches DEJA illustrees dont la revue "
                         "d'ensemble a juge l'image faible")
    a = ap.parse_args()

    deja = set()
    if os.path.exists("assets/titres/LEGENDES.json"):
        deja = set(json.load(open("assets/titres/LEGENDES.json", encoding="utf-8")))
    if a.termes:
        carte = {}
        for bloc in a.termes.split(","):
            tk, _, liste = bloc.partition("=")
            termes = [t.strip() for t in liste.split("|") if t.strip()]
            if not tk.strip() or not termes:
                raise SystemExit(f"terme mal forme : « {bloc} », attendu TICKER=a|b")
            carte[tk.strip()] = termes
    else:
        carte = LIEUX if a.lieux else (AMELIORATIONS if a.ameliorer else MARQUES)
    # En mode amelioration on vise justement celles qui ont deja une image.
    cibles = ([t for t in sorted(carte)] if (a.ameliorer or a.lieux or a.termes)
              else [t for t in sorted(carte) if t not in deja])
    if a.limite:
        cibles = cibles[: a.limite]
    os.makedirs(a.sortie, exist_ok=True)
    print(f"{len(cibles)} sociétés à chercher par marque et par produit\n", flush=True)

    rapport = {}
    for i, tk in enumerate(cibles, 1):
        propositions, vus = [], set()
        for terme in carte[tk]:
            for f in chercher_commons(terme):
                if f in vus:
                    continue
                vus.add(f)
                # Le terme qui a trouvé le fichier est conservé : c'est lui qui
                # dira, à la relecture, pourquoi cette image est censée montrer
                # cette société. Sans ça on ne sait plus ce qu'on regarde.
                propositions.append((score_nom(f), f, terme))
            time.sleep(0.25)

        propositions.sort(reverse=True)
        gardes = []
        for sc, f, terme in propositions:
            if len(gardes) >= a.par_societe:
                break
            inf = infos(f)
            if not inf:
                continue
            inf.update({"score": sc, "terme": terme})
            try:
                req = urllib.request.Request(inf["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
                inf["poids"] = prepare(brut, os.path.join(a.sortie,
                                                          f"{tk}_{len(gardes)}.jpg"))
            except Exception as e:
                print(f"      ✗ téléchargement {type(e).__name__}")
                continue
            gardes.append(inf)

        if gardes:
            rapport[tk] = {"candidats": gardes}
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(propositions):3d} pistes → "
                  f"{gardes[0]['score']:3d} pts  « {gardes[0]['terme'][:24]:24s} »  "
                  f"{gardes[0]['fichier'][:40]}", flush=True)
        else:
            print(f"[{i:3d}/{len(cibles)}] {tk:9s} {len(propositions):3d} pistes, "
                  f"rien d'exploitable", flush=True)

    sortie_json = ("photos_termes.json" if a.termes
                   else "photos_lieux.json" if a.lieux
                   else "photos_ameliorer.json" if a.ameliorer else "photos_marques.json")
    with open(sortie_json, "w", encoding="utf-8") as f:
        json.dump({"societes": len(rapport), "detail": rapport}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n{'=' * 70}")
    print(f"PISTES TROUVÉES : {len(rapport)}/{len(cibles)} sociétés")


if __name__ == "__main__":
    main()
