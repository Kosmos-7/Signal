#!/usr/bin/env python3
"""Mesure la disponibilité de photos LIBRES pour chaque société couverte.

Pourquoi une sonde avant un chantier : illustrer les trois watchlists a demandé
deux campagnes et un changement de stratégie de recherche. Le faire pour 104
sociétés est un ordre de grandeur au-dessus, et la contrainte de licence
(domaine public ou CC0 uniquement) est beaucoup plus mordante sur des sujets
précis que sur des thèmes génériques. On mesure donc le taux de couverture
RÉEL avant de décider, plutôt que de découvrir à mi-parcours que la moitié des
fiches resteraient sans image.

Cette sonde ne télécharge RIEN : elle interroge l'API et compte. Sortie :
un rapport JSON avec, par ticker, le nombre de candidats libres trouvés et le
meilleur titre de fichier, pour juger de la pertinence autant que du volume.

Usage : python3 tools/sonde_photos_titres.py [--limite N]
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "SignalWatchlists/1.0 (https://github.com/Kosmos-7/Signal ; projet pédagogique)"

LICENCES_OK = ("cc0", "public domain", "pd-", "no restrictions", "publicdomain")
LICENCES_KO = ("by-sa", "by-nc", "nd", "fair use", "non-free", "copyright")

# Suffixes juridiques : « NVIDIA Corporation headquarters » trouve moins que
# « NVIDIA headquarters ». On cherche sur le nom d'usage.
_SUFX = re.compile(
    r"[,\s]+(incorporated|inc\.?|corporation|corp\.?|company|co\.?|limited|ltd\.?|plc|"
    r"n\.?v\.?|s\.?e\.?|a\.?g\.?|s\.?a\.?|llc|holdings?|group|technologies|technology)\s*$",
    re.I)

# Noms d'usage là où la raison sociale publiée est tronquée ou trompeuse.
NOMS = {
    "2330.TW": "TSMC", "000660.KS": "SK Hynix", "005930.KS": "Samsung Electronics",
    "4063.T": "Shin-Etsu Chemical", "6146.T": "Disco Corporation",
    "8035.T": "Tokyo Electron", "6857.T": "Advantest", "4062.T": "Ibiden",
    "ASX": "ASE Group", "MUV2.DE": "Munich Re", "CS.PA": "AXA",
    "SU.PA": "Schneider Electric", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "ABBN.SW": "ABB", "IFX.DE": "Infineon", "ALV.DE": "Allianz",
    "HSBA.L": "HSBC", "UBSG.SW": "UBS", "LSEG.L": "London Stock Exchange Group",
    "DB1.DE": "Deutsche Boerse", "BNP.PA": "BNP Paribas", "ADYEN.AS": "Adyen",
    "ASML.AS": "ASML", "ASM.AS": "ASM International", "ON": "onsemi",
    "MPWR": "Monolithic Power Systems", "SNDK": "SanDisk", "GEV": "GE Vernova",
    "CEG": "Constellation Energy", "PWR": "Quanta Services", "VST": "Vistra",
    # La raison sociale publiée est tronquée à 22 caractères par le fournisseur
    # de données : sans ces entrées, on chercherait « Hewlett Packard Enterp ».
    "HPE": "Hewlett Packard Enterprise", "JPM": "JPMorgan Chase",
    "AMAT": "Applied Materials", "LRCX": "Lam Research", "MU": "Micron Technology",
    "WDC": "Western Digital", "STX": "Seagate Technology", "CDNS": "Cadence Design Systems",
    "AXP": "American Express", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "SCHW": "Charles Schwab", "TFC": "Truist Financial",
    "PGR": "Progressive Corporation", "MCO": "Moody's", "ICE": "Intercontinental Exchange",
    "DLR": "Digital Realty", "MRVL": "Marvell Technology", "NTAP": "NetApp",
    "TER": "Teradyne", "KLAC": "KLA Corporation", "SNPS": "Synopsys", "COHR": "Coherent",
    "LITE": "Lumentum", "CIEN": "Ciena", "ANET": "Arista Networks", "EQIX": "Equinix",
    "CRWV": "CoreWeave", "NBIS": "Nebius", "SHAZ": "Sharon AI", "CCJ": "Cameco",
    "VRT": "Vertiv", "ETN": "Eaton", "AVGO": "Broadcom", "QCOM": "Qualcomm",
}


def nom_usage(ticker, brut):
    if ticker in NOMS:
        return NOMS[ticker]
    n = (brut or ticker).strip().rstrip(" ,.&-")
    while True:
        court = _SUFX.sub("", n).strip()
        court = court.rstrip(" ,.&-")
        if court == n or len(court) < 3:
            return n
        n = court


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def libre(meta):
    champs = " ".join(str((meta.get(k) or {}).get("value", "")).lower()
                      for k in ("LicenseShortName", "UsageTerms", "License"))
    if any(k in champs for k in LICENCES_KO):
        return False
    return any(k in champs for k in LICENCES_OK)


def compter(terme, largeur_min=1200):
    """Candidats libres et exploitables pour un terme. Retourne (n, exemples)."""
    try:
        d = _get({"action": "query", "format": "json", "generator": "search",
                  "gsrsearch": f"filetype:bitmap {terme}", "gsrnamespace": "6",
                  "gsrlimit": "14", "prop": "imageinfo",
                  "iiprop": "url|extmetadata|size"})
    except Exception:
        return 0, []
    ok = []
    for page in (d.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if not libre(info.get("extmetadata") or {}):
            continue
        if (info.get("width") or 0) < largeur_min:
            continue
        ok.append(page.get("title", "").replace("File:", "")[:64])
    return len(ok), ok[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0, help="ne sonder que les N premiers")
    a = ap.parse_args()

    w = json.load(open("watchlist.json"))
    u = json.load(open("universe.json"))
    noms = {t: v["nom"] for t, v in u["stocks"].items()}
    noms.update({s["ticker"]: s["name"] for s in w["stocks"]})
    secteurs = {t: v.get("secteur", "") for t, v in u["stocks"].items()}
    secteurs.update({s["ticker"]: s.get("sector", "") for s in w["stocks"]})

    cibles = sorted(noms)
    if a.limite:
        cibles = cibles[:a.limite]
    print(f"Sonde sur {len(cibles)} sociétés couvertes\n", flush=True)

    rapport, avec, sans = {}, 0, []
    for i, tk in enumerate(cibles, 1):
        nom = nom_usage(tk, noms[tk])
        total, exemples = 0, []
        # Le siège social est le sujet le plus souvent photographié ET le plus
        # neutre : c'est un bâtiment, pas une marque ni un produit vanté.
        for terme in (f"{nom} headquarters", f"{nom} building", f"{nom} company"):
            n, ex = compter(terme)
            total += n
            exemples += ex
            if total >= 3:
                break
            time.sleep(0.25)
        rapport[tk] = {"nom": nom, "secteur": secteurs.get(tk, ""),
                       "candidats": total, "exemples": exemples[:3]}
        if total:
            avec += 1
        else:
            sans.append(tk)
        etat = f"{total:2d}" if total else " —"
        print(f"[{i:3d}/{len(cibles)}] {etat}  {tk:12s} {nom[:28]:28s} "
              f"{(exemples[0][:44] if exemples else '')}", flush=True)

    with open("sonde_photos_titres.json", "w", encoding="utf-8") as f:
        json.dump({"sondes": len(cibles), "avec_candidat": avec,
                   "sans_candidat": sans, "detail": rapport}, f,
                  ensure_ascii=False, indent=1)

    taux = avec / len(cibles) if cibles else 0
    print(f"\n{'=' * 70}")
    print(f"COUVERTURE : {avec}/{len(cibles)} sociétés ont au moins un candidat libre ({taux:.0%})")
    print(f"SANS AUCUN CANDIDAT ({len(sans)}) : {', '.join(sans[:40])}")
    riches = sum(1 for v in rapport.values() if v["candidats"] >= 3)
    print(f"AVEC 3 CANDIDATS OU PLUS (choix réel possible) : {riches}/{len(cibles)} ({riches/len(cibles):.0%})")


if __name__ == "__main__":
    main()
