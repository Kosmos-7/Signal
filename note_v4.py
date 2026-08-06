"""Note d'entreprise Signal v4 — le moteur de notation, pur et testable.

DOCTRINE (décisions propriétaires des 06-07/08/2026) :
  · la note INFORME, elle ne prédit pas : notation factuelle d'une entreprise,
    de son prix et de sa dynamique, fondée sur la logique financière établie —
    aucun backtest, aucun fit sur les rendements ;
  · partition MECE par domaine de donnée, chaque information comptée UNE fois :
      Qualité 35      = NIVEAUX des comptes (marges, capital, cash, bilan)
      Croissance 25   = DÉRIVÉES des comptes (+ estimé, borné sous le démontré)
      Valorisation 25 = COURS ÷ COMPTES (prix payé)
      Momentum 15     = COURS ÷ COURS (dynamique de marché)
  · rampes CONTINUES partout : les seuils sont des points de passage, jamais
    des murs (l'anti-NOW 81→66→72) ;
  · un critère incalculable est RETIRÉ avec motif affiché et la note se
    renormalise — jamais de zéro silencieux ;
  · la note reste un /100 (décision du 06/08/2026 : le système de lettres
    A+…D a été conçu, testé, puis écarté — le chiffre continu dit plus).

Pondérations : dérivées de cinq principes (un point = de la confiance dans la
mesure ; l'estimé ne dépasse jamais le démontré ; la redondance se paie ;
l'asymétrie se respecte ; le discriminant réel compte). La dérivation complète
est documentée dans apprendre.html et le CHANGELOG 4.0.0.
"""
import statistics


# ── Outils de rampe ──────────────────────────────────────────────────────────

def rampe(x, x0, x1, pts):
    """Interpolation linéaire bornée : x0 → 0 pt, x1 → pts. Inversée si x1<x0."""
    if x is None:
        return None
    if x1 < x0:
        return rampe(-x, -x0, -x1, pts)
    t = (x - x0) / (x1 - x0)
    return round(pts * max(0.0, min(1.0, t)), 1)


def cloche(x, bas0, bas1, haut1, haut0, pts):
    """Plateau à pts sur [bas1, haut1], rampes vers 0 à bas0 et haut0.
    La « zone saine » en continu : ni mur, ni falaise, symétrique par choix."""
    if x is None:
        return None
    if x <= bas0 or x >= haut0:
        return 0.0
    if x < bas1:
        return round(pts * (x - bas0) / (bas1 - bas0), 1)
    if x > haut1:
        return round(pts * (haut0 - x) / (haut0 - haut1), 1)
    return float(pts)


def _fr(v, d=1):
    s = f"{v:.{d}f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


# ── Extraction des grandeurs pluriannuelles ──────────────────────────────────

def _marges_annuelles(an):
    """Marges nettes annuelles plausibles (%). Garde : |marge| < 100 % — les
    artefacts comptables de holding (NBIS à 1764 %) ne notent pas."""
    out = []
    for e in an:
        if e.get("rn") is not None and e.get("ca"):
            m = e["rn"] / e["ca"] * 100
            if -100 < m < 100:
                out.append(m)
    return out


def _tcam(serie):
    """TCAM (%) sur [(annee, valeur), ...], mesuré sur la plus longue fenêtre
    exploitable qui se termine au dernier exercice.

    POURQUOI ON NE PART PAS TOUJOURS DU PREMIER POINT. Un taux de croissance
    annuel n'existe pas depuis une base négative : Broadcom ouvre son
    historique à −4,86 € de bénéfice par action puis atteint 4,77 €, et la
    formule renvoyait simplement « incalculable » — abandonnant dix exercices
    de trajectoire parfaitement lisible. C'était 16 retraits sur le run du
    06/08, classés à tort « mathématiquement indéfinis » : ce n'était pas la
    donnée qui manquait, c'était le calcul qui renonçait trop tôt.

    On démarre donc au PREMIER EXERCICE POSITIF, en exigeant qu'il reste au
    moins trois points — sinon la mesure porterait sur un rebond de sortie de
    pertes, pas sur une trajectoire. La fenêtre réellement retenue est rendue
    avec le taux, pour que la phrase affichée dise la vérité (« sur 8 ans »
    et non « sur 11 ans »).

    Retourne (taux, nombre d'années) ou (None, None).
    """
    if len(serie) < 3:
        return None, None
    (_, v_fin) = serie[-1]
    if v_fin <= 0:
        return None, None                     # arriver en perte n'est pas une croissance
    depart = next((i for i, (_, v) in enumerate(serie) if v > 0), None)
    if depart is None or len(serie) - depart < 3:
        return None, None
    (y0, v0), (y1, v1) = serie[depart], serie[-1]
    if y1 <= y0:
        return None, None
    return ((v1 / v0) ** (1 / (y1 - y0)) - 1) * 100, y1 - y0


# ── La grille ────────────────────────────────────────────────────────────────

def calcule_note(ctx):
    """ctx : dictionnaire des intrants — tout est optionnel, l'absence retire.

      an              liste fonda annuelle [{fin, ca, rn, eps, per}, ...]
      pe_prev         [{exercice, per}, ...] (PER prévisionnels)
      prix            cours actuel (devise de cotation)
      trailing_pe / forward_pe
      net_margin_pct / fcf_margin_pct / fcf_yield_pct   (TTM)
      roe             fraction (0.18) — TTM, repli tant que l'historique bilan
                      n'est pas collecté
      debt_eq         dette/CP en % (échelle yfinance ×100)
      banque          bool — banque/assurance : FCF et levier sans objet
      meme_devise     bool — devise comptable == cotation (ADR : False)
      z / rsi         position vs tendance 10 ans (σ) / RSI
      ecart_mm_pct    (MM21/MM200 − 1) × 100 — le régime de tendance en continu

    Retourne {total, blocs:{q,c,v,m:{pts,max,dispo}}, criteres:[...],
    couverture} — criteres porte (id, bloc, pts, max, valeur, phrase) et les
    retraits ont pts=None + motif.
    """
    an = ctx.get("an") or []
    banque = bool(ctx.get("banque"))
    crit = []

    def ajoute(bloc, cid, maxi, pts, valeur, phrase, motif=None):
        crit.append({"bloc": bloc, "id": cid, "max": maxi, "pts": pts,
                     "valeur": valeur, "phrase": phrase, "motif": motif})

    # ═ QUALITÉ /35 — niveaux des comptes ═
    marges = _marges_annuelles(an)
    if len(marges) >= 3:
        m = statistics.median(marges)
        ajoute("q", "marge", 9, rampe(m, 2, 20, 9), round(m, 1),
               f"Sur 100 € de ventes, il reste {_fr(m)} € de bénéfice net "
               f"(médiane de {len(marges)} exercices)")
    else:
        ajoute("q", "marge", 9, None, None, None,
               f"historique trop court ({len(marges)} exercice(s) exploitables)")

    roe = ctx.get("roe")
    if roe is not None and (ctx.get("debt_eq") is None or ctx["debt_eq"] <= 200) \
            and not banque:
        r = roe * 100
        ajoute("q", "roe", 9, rampe(r, 8, 20, 9), round(r, 1),
               f"Chaque 100 € de capitaux propres rapportent {_fr(r)} € par an")
    elif banque and roe is not None:
        r = roe * 100
        ajoute("q", "roe", 9, rampe(r, 6, 15, 9), round(r, 1),
               f"Rendement des capitaux propres {_fr(r)} % (rampe bancaire 6-15 %)")
    elif roe is not None:
        # levier > 200 % : le ROE est dopé, on le tempère au lieu de le croire
        r = roe * 100 / 2
        ajoute("q", "roe", 9, rampe(r, 8, 20, 9), round(roe * 100, 1),
               f"Rendement des capitaux propres {_fr(roe*100)} %, tempéré : "
               f"le levier dépasse 200 % des fonds propres")
    else:
        ajoute("q", "roe", 9, None, None, None, "rendement du capital non disponible")

    nm, fm = ctx.get("net_margin_pct"), ctx.get("fcf_margin_pct")
    if banque:
        ajoute("q", "conversion", 7, None, None, None,
               "le FCF n'a pas de sens pour un bilan bancaire")
    elif fm is not None and nm and nm > 0:
        c = fm / nm * 100
        ajoute("q", "conversion", 7, rampe(min(c, 120), 40, 100, 7), round(c),
               f"Sur 100 € de bénéfice comptable, {_fr(min(c,120),0)} € "
               f"finissent en cash réel")
    else:
        ajoute("q", "conversion", 7, None, None, None,
               "conversion en cash non calculable")

    de = ctx.get("debt_eq")
    if banque:
        ajoute("q", "bilan", 5, None, None, None,
               "le levier est la matière première du métier bancaire")
    elif de is not None:
        ajoute("q", "bilan", 5, rampe(de, 150, 0, 5), round(de),
               f"Dette à {_fr(de,0)} % des capitaux propres")
    else:
        ajoute("q", "bilan", 5, None, None, None, "bilan non disponible")

    rns = [e for e in an if e.get("rn") is not None]
    if len(rns) >= 4:
        part = sum(1 for e in rns if e["rn"] > 0) / len(rns) * 100
        ajoute("q", "constance", 5, rampe(part, 60, 100, 5), round(part),
               f"Bénéficiaire {sum(1 for e in rns if e['rn']>0)} années "
               f"sur les {len(rns)} connues")
    else:
        ajoute("q", "constance", 5, None, None, None,
               f"historique trop court ({len(rns)} exercice(s))")

    # ═ CROISSANCE /25 — dérivées des comptes ═
    cas = [(int(e["fin"][:4]), e["ca"]) for e in an if e.get("ca")]
    g_ca, n_ca = _tcam(cas)
    if g_ca is not None:
        ajoute("c", "ca", 7, rampe(g_ca, 0, 15, 7), round(g_ca, 1),
               f"Chiffre d'affaires en croissance de {_fr(g_ca)} % par an "
               f"sur {n_ca} ans")
    else:
        ajoute("c", "ca", 7, None, None, None, "croissance du CA non calculable")

    epss = [(int(e["fin"][:4]), e["eps"]) for e in an if e.get("eps")]
    g_bpa, n_bpa = _tcam(epss)
    if g_bpa is not None:
        # La fenêtre est dite quand elle diffère de l'historique complet :
        # « depuis le premier exercice bénéficiaire » est une information, pas
        # un détail — elle signale une sortie de pertes.
        _dep = (f" (depuis le premier exercice bénéficiaire, sur {n_bpa} ans)"
                if epss and n_bpa < epss[-1][0] - epss[0][0] else f" sur {n_bpa} ans")
        ajoute("c", "bpa", 7, rampe(g_bpa, 0, 15, 7), round(g_bpa, 1),
               f"Bénéfice par action en croissance de {_fr(g_bpa)} % par an, "
               f"dilution comprise{_dep}")
    else:
        ajoute("c", "bpa", 7, None, None, None,
               "trajectoire du bénéfice par action non calculable")

    if len(cas) >= 4:
        prog = sum(1 for i in range(1, len(cas)) if cas[i][1] > cas[i-1][1])
        part = prog / (len(cas) - 1) * 100
        ajoute("c", "regularite", 4, rampe(part, 50, 100, 4), round(part),
               f"Le CA progresse {prog} années sur {len(cas)-1}")
    else:
        ajoute("c", "regularite", 4, None, None, None, "historique trop court")

    g_att = None
    if ctx.get("meme_devise", True) and ctx.get("prix") and epss:
        est = [(p["exercice"], ctx["prix"] / p["per"])
               for p in (ctx.get("pe_prev") or []) if p.get("per")]
        if est and epss[-1][1] > 0:
            y1, e1 = est[-1]
            if y1 > epss[-1][0]:
                g_att = ((e1 / epss[-1][1]) ** (1 / (y1 - epss[-1][0])) - 1) * 100
    if g_att is not None:
        ajoute("c", "attendu", 7, rampe(g_att, 0, 20, 7), round(g_att, 1),
               f"Les analystes attendent {_fr(g_att)} % de croissance annuelle "
               f"du bénéfice (estimation, pas une publication)")
    else:
        ajoute("c", "attendu", 7, None, None, None,
               "pas d'estimation exploitable"
               + ("" if ctx.get("meme_devise", True)
                  else " (devise comptable différente de la cotation)"))

    # ═ VALORISATION /25 — cours ÷ comptes ═
    pers = [e["per"] for e in an if e.get("per")]
    tpe = ctx.get("trailing_pe")
    if len(pers) >= 3 and tpe and tpe > 0:
        med = statistics.median(pers)
        ratio = tpe / med
        ajoute("v", "histoire", 8, rampe(ratio, 1.3, 0.7, 8), round(ratio, 2),
               f"Payée {_fr(tpe)}× ses bénéfices, contre {_fr(med)}× en médiane "
               f"sur {len(pers)} exercices")
    else:
        ajoute("v", "histoire", 8, None, None, None,
               "pas assez de multiples historiques comparables")

    fpe = ctx.get("forward_pe")
    g_ref = None
    if g_att is not None and g_bpa is not None:
        g_ref = min(g_att, g_bpa)
    elif g_att is not None or g_bpa is not None:
        g_ref = g_att if g_att is not None else g_bpa
    if fpe and fpe > 0 and g_ref and g_ref > 0:
        peg = fpe / g_ref
        ajoute("v", "peg", 7, rampe(peg, 3, 1, 7), round(peg, 2),
               f"PER prévisionnel {_fr(fpe)}× pour {_fr(g_ref)} % de croissance "
               f"retenue (la plus prudente des deux) : PEG {_fr(peg,2)}")
    else:
        ajoute("v", "peg", 7, None, None, None,
               "croissance de référence ou PER prévisionnel indisponible")

    if fpe and fpe > 0:
        ry = 100 / fpe
        ajoute("v", "rdt_benefices", 5, rampe(ry, 3, 8, 5), round(ry, 1),
               f"100 € investis achètent {_fr(ry)} € de bénéfices attendus")
    else:
        ajoute("v", "rdt_benefices", 5, None, None, None,
               "bénéfices attendus négatifs ou inconnus")

    # Quatrième critère de valorisation. Pour une activité de BILAN (banque,
    # assureur), le FCF n'a pas de sens — mais renoncer à mesurer reviendrait à
    # juger ces titres sur moins de critères que les autres, ce que la
    # renormalisation compense sans le corriger. On leur substitue donc le
    # multiple qui fait référence dans leur métier : le cours rapporté aux
    # ACTIFS NETS comptables, dont la valeur est réelle pour un bilan là où
    # elle est vide de sens pour un éditeur de logiciels.
    #
    # POURQUOI UNE RAMPE SIMPLE (« moins cher = mieux ») ET PAS UNE CLOCHE.
    # Un multiple bas peut trahir un bilan que le marché juge douteux — mais
    # la QUALITÉ de ce bilan est déjà notée ailleurs, dans le bloc Qualité
    # (ROE sur rampe bancaire, constance des bénéfices). Le bloc Valorisation
    # ne répond qu'à une seule question, « qu'est-ce que je paie » ; y
    # réintroduire un jugement de qualité compterait la même information deux
    # fois et violerait la partition MECE. C'est exactement le traitement déjà
    # réservé au rendement des bénéfices.
    fy = ctx.get("fcf_yield_pct")
    pb = ctx.get("price_to_book")
    if banque and pb is not None and pb > 0:
        ajoute("v", "actifs_nets", 5, rampe(pb, 3, 0.8, 5), round(pb, 2),
               f"Payée {_fr(pb, 2)} fois ses actifs nets comptables")
    elif banque:
        ajoute("v", "actifs_nets", 5, None, None, None,
               "actifs nets comptables non publiés")
    elif fy is not None:
        ajoute("v", "rdt_cash", 5, rampe(fy, 1.5, 7, 5), round(fy, 2),
               f"L'entreprise génère {_fr(fy)} % de sa capitalisation en cash "
               f"chaque année")
    else:
        ajoute("v", "rdt_cash", 5, None, None, None, "FCF non publié")

    # ═ MOMENTUM /15 — cours ÷ cours ═
    em = ctx.get("ecart_mm_pct")
    if em is not None:
        ajoute("m", "tendance", 6, rampe(em, -5, 5, 6), round(em, 1),
               f"Moyenne 21 jours à {_fr(em)} % de la moyenne 200 jours")
    else:
        ajoute("m", "tendance", 6, None, None, None, "tendance non calculable")

    z = ctx.get("z")
    if z is not None:
        # cloche SYMÉTRIQUE : plein entre −1,5σ et +1σ, nul à ±3σ — l'excès
        # d'étirement pénalise dans les deux sens, l'asymétrie pro-momentum
        # mesurée en v3 disparaît.
        ajoute("m", "position", 6, cloche(z, -3, -1.5, 1, 3, 6), round(z, 2),
               f"À {_fr(z)}σ de sa tendance décennale")
    else:
        ajoute("m", "position", 6, None, None, None, "régression indisponible")

    rsi = ctx.get("rsi")
    if rsi is not None:
        ajoute("m", "rsi", 3, cloche(rsi, 20, 35, 65, 80, 3), round(rsi),
               f"RSI {_fr(rsi,0)}, "
               + ("zone neutre" if 35 <= rsi <= 65 else "zone tendue"))
    else:
        ajoute("m", "rsi", 3, None, None, None, "RSI indisponible")

    # ═ Agrégation : renormalisation par bloc, puis sur les blocs notés ═
    #
    # LA PRUDENCE DE LA RENORMALISATION. Projeter tels quels les points d'une
    # base partielle sur le maximum du bloc préserve la MOYENNE mais gonfle la
    # DISPERSION : mesuré sur le run du 06/08, l'écart-type des titres à
    # couverture partielle dépassait de 49 % celui des titres complets, et ces
    # titres occupaient 67 % du décile supérieur pour 33 % de la population.
    # La raison est arithmétique : avec trois critères au lieu de cinq, on a
    # trois occasions de perdre des points au lieu de cinq, donc saturer est
    # plus facile — un bloc partiel atteignait son maximum 14,5 % du temps
    # contre 6,6 % pour un bloc mesuré en entier.
    #
    # On rapproche donc la part NON MESURÉE de la moyenne du bloc plutôt que
    # de lui prêter la performance observée. Un titre excellent sur ce qu'on
    # sait mesurer reste bien noté, mais ne dépasse plus un titre également
    # excellent et intégralement vérifié : l'ignorance ne se transforme plus
    # en avantage. Symétriquement, elle ne se transforme pas non plus en
    # punition — c'était la pathologie de la v3, celle des zéros muets.
    NEUTRE = 0.55           # performance présumée de la part non mesurée
    BLOCS = {"q": 35, "c": 25, "v": 25, "m": 15}
    blocs = {}
    for b, maxi in BLOCS.items():
        notes = [c for c in crit if c["bloc"] == b and c["pts"] is not None]
        dispo = sum(c["max"] for c in notes)
        if dispo:
            sur = sum(c["max"] for c in crit if c["bloc"] == b)
            part = dispo / sur                       # fraction réellement mesurée
            taux = sum(c["pts"] for c in notes) / dispo
            pts = (taux * part + NEUTRE * (1 - part)) * maxi
            blocs[b] = {"pts": round(pts, 1), "max": maxi, "dispo": dispo,
                        "sur": sur}
        else:
            blocs[b] = {"pts": None, "max": maxi, "dispo": 0,
                        "sur": sum(c["max"] for c in crit if c["bloc"] == b)}
    max_notable = sum(v["max"] for v in blocs.values() if v["pts"] is not None)
    total = (round(sum(v["pts"] for v in blocs.values() if v["pts"] is not None)
                   / max_notable * 100) if max_notable else 0)
    non_notes = sum(1 for c in crit if c["pts"] is None)
    return {"total": total, "blocs": blocs, "criteres": crit,
            "couverture": round((len(crit) - non_notes) / len(crit) * 100)}
