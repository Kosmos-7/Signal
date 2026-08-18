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


# Facteur d'effondrement au-delà duquel on cesse de croire à une trajectoire
# d'entreprise et où l'on soupçonne un changement de périmètre ou de définition
# (cf. _tcam). Un tiers en un an : les cycliques les plus violentes reculent de
# moitié, pas de deux tiers.
RUPTURE_PERIMETRE = 1 / 3


def apres_rupture(serie):
    """Tronque une série de CHIFFRE D'AFFAIRES à sa dernière marche descendante.

    Un effondrement d'un facteur 3 ou plus entre deux exercices consécutifs
    n'est presque jamais une trajectoire d'entreprise : c'est une cession, une
    scission, ou un changement de définition qui n'a retraité que les exercices
    récents. Mesurer « à travers » cette marche produit une contre-vérité
    publiée comme un fait — Adyen sortait à « −33,3 % par an » (passage du
    volume traité au revenu net en 2023) et Western Digital à « −10,5 % »
    (séparation de SanDisk), alors que les deux croissent de ~20 % sur leur
    périmètre actuel, et les deux prenaient 0 sur 7 pour cela.

    RÉSERVÉ AU CHIFFRE D'AFFAIRES, et c'est essentiel. Le bénéfice est une
    grandeur bien plus volatile : Broadcom passe de 2,84 à 0,64 € de BPA en
    2019 par pur amortissement d'acquisitions, sans rien céder. Appliquer la
    même règle au BPA effacerait des trajectoires vraies. Le chiffre
    d'affaires, lui, mesure le PÉRIMÈTRE : c'est la seule série où une marche
    descendante d'un facteur 3 accuse la définition plutôt que l'entreprise.

    Une marche MONTANTE est conservée — c'est la signature de
    l'hypercroissance (Nebius ×9 puis ×6, CoreWeave ×14 puis ×8), et la
    tronquer effacerait justement ce qu'on veut voir. Pure."""
    for i in range(len(serie) - 1, 0, -1):
        pre, post = serie[i - 1][1], serie[i][1]
        if pre and pre > 0 and post and post > 0 and post / pre < RUPTURE_PERIMETRE:
            return serie[i:]
    return serie


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
      mom_ratio       rendement 12-1 (numérateur min(P, P−1m)/P−13m) ÷ σ hebdo
                      annualisé — le scalaire noté par la cloche « momentum »
      mom_pct / mom_vol_pct   ses deux composantes, pour la phrase (%)
      drawdown_52w_pct  distance au plus haut 52 semaines (négatif ou 0) —
                      None sous 252 séances de cotation
      z               position vs sa droite de régression log (σ)
      reg_seances     fenêtre EFFECTIVE de cette régression, en séances non
                      arrondies — la cloche du z exige ≥ 1260 (5 ans)
      pente_mm21_pct  vélocité de la MM21 sur 5 séances (%)

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
        # Rampe portée de 8-20 à 8-30 : mesurée sur l'univers publié, la borne
        # haute tombait sous le 40e centile (médiane 23,2 %) et 60 % des titres
        # touchaient le maximum. 30 % de rendement des capitaux propres reste
        # une franchise exceptionnelle ; 8 % couvre à peine le coût du capital.
        ajoute("q", "roe", 9, rampe(r, 8, 30, 9), round(r, 1),
               f"Chaque 100 € de capitaux propres rapportent {_fr(r)} € par an")
    elif banque and roe is not None:
        r = roe * 100
        ajoute("q", "roe", 9, rampe(r, 6, 15, 9), round(r, 1),
               f"Rendement des capitaux propres {_fr(r)} % (rampe bancaire 6-15 %)")
    elif roe is not None:
        # levier > 200 % : le ROE est dopé, on le tempère au lieu de le croire
        r = roe * 100 / 2
        ajoute("q", "roe", 9, rampe(r, 8, 30, 9), round(roe * 100, 1),
               f"Rendement des capitaux propres {_fr(roe*100)} %, tempéré : "
               f"le levier dépasse 200 % des fonds propres")
    else:
        ajoute("q", "roe", 9, None, None, None, "rendement du capital non disponible")

    # Conversion en cash — SUBSTITUÉE pour les métiers de bilan (06/08 soir).
    # Retirer une métrique sans objet était un pis-aller : la banque se
    # retrouvait jugée sur trois critères de qualité au lieu de cinq, et la
    # renormalisation — même prudente — devait présumer quelque chose à la
    # place. On ne présume plus : on MESURE l'équivalent-métier. Pour un
    # bilan bancaire, le pendant de « combien de bénéfice devient du cash »
    # est « combien les ACTIFS produisent de bénéfice » — le rendement des
    # actifs (ROA), l'étalon classique : ≥1,2 % excellent, ≤0,3 % faible.
    nm, fm = ctx.get("net_margin_pct"), ctx.get("fcf_margin_pct")
    if banque:
        roa = ctx.get("roa_pct")
        if roa is not None:
            ajoute("q", "rendement_actifs", 7, rampe(roa, 0.3, 1.3, 7),
                   round(roa, 2),
                   f"Chaque 100 € d'actifs au bilan produisent "
                   f"{_fr(roa, 2)} € de bénéfice par an (le pendant bancaire "
                   f"de la conversion en cash)")
        else:
            ajoute("q", "rendement_actifs", 7, None, None, None,
                   "actifs au bilan non publiés")
    else:
        # `conversion_pct` est calculée par le screener à partir du flux
        # disponible et du résultat net DU MÊME EXERCICE, lus dans le même
        # document. Le repli `fm / nm` ne vaut que faute de mieux : il divise
        # deux marges glissantes qui peuvent venir de sources différentes, et
        # c'est ce qui donnait 12 % de conversion à Microsoft. On le garde
        # pour ne pas retirer le critère quand les comptes sont illisibles,
        # mais il n'est plus le chemin normal.
        c = ctx.get("conversion_pct")
        if c is None and fm is not None and nm and nm > 0:
            c = fm / nm * 100
        if c is not None:
            # Borne haute portée de 100 à 120 % : la médiane de l'univers est à
            # 107 %, donc l'ancienne rampe s'arrêtait AVANT le titre médian et
            # 55 % des sociétés touchaient le plafond. Au-delà de 120 % la
            # valeur reste bridée : convertir plus que son bénéfice comptable
            # traduit un amortissement supérieur aux investissements ou une
            # reprise de besoin en fonds de roulement, pas une qualité de plus.
            ajoute("q", "conversion", 7, rampe(min(c, 120), 40, 120, 7), round(c),
                   f"Sur 100 € de bénéfice comptable, {_fr(min(c,120),0)} € "
                   f"finissent en cash réel")
        else:
            ajoute("q", "conversion", 7, None, None, None,
                   "conversion en cash non calculable")

    # Bilan — même substitution. Dette/capitaux propres n'a pas de sens quand
    # la dette est la matière première ; le pendant-métier est le LEVIER
    # total : combien d'euros d'actifs reposent sur un euro de fonds propres.
    # 8× = très capitalisé (la plupart des assureurs), ~12× = banque saine,
    # 25× = territoire Credit Suisse. Rampe inversée, continue.
    de = ctx.get("debt_eq")
    if banque:
        lev = ctx.get("levier_actifs")
        if lev is not None and lev > 0:
            ajoute("q", "levier_actifs", 5, rampe(lev, 25, 8, 5),
                   round(lev, 1),
                   f"Le bilan porte {_fr(lev, 1)} € d'actifs pour 1 € de "
                   f"fonds propres")
        else:
            ajoute("q", "levier_actifs", 5, None, None, None,
                   "actifs au bilan non publiés")
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
    cas = apres_rupture([(int(e["fin"][:4]), e["ca"]) for e in an if e.get("ca")])
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

    # `cas` est DÉJÀ tronquée au périmètre actuel : compter une « année de
    # recul » qui n'est qu'un changement de définition punirait deux fois la
    # même illusion.
    cas_r = cas
    if len(cas_r) >= 4:
        prog = sum(1 for i in range(1, len(cas_r)) if cas_r[i][1] > cas_r[i-1][1])
        part = prog / (len(cas_r) - 1) * 100
        ajoute("c", "regularite", 4, rampe(part, 50, 100, 4), round(part),
               f"Le CA progresse {prog} années sur {len(cas_r)-1}")
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
        # Rampe portée de 0-20 à 0-40 : mesurée sur l'univers publié, l'ancienne
        # ne NOTAIT que 11 % des titres — 86 % butaient au plafond, la médiane
        # des attentes étant à 33,8 % et le neuvième décile à 122 %. Un critère
        # qui donne le maximum à six titres sur sept ne classe plus rien.
        # 40 % par an reste une attente exceptionnelle ; 0 % est la stagnation.
        ajoute("c", "attendu", 7, rampe(g_att, 0, 40, 7), round(g_att, 1),
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
        # Borne basse portée de 1,3 à 2,0 : le titre MÉDIAN de l'univers se paie
        # 1,3 fois son propre multiple historique — l'ancienne rampe mettait
        # donc zéro à toute la moitié supérieure et ne distinguait plus « un peu
        # cher » de « absurdement cher » (le maximum relevé est 18,4 fois).
        # 2 fois son propre passé reste une cherté franche.
        ajoute("v", "histoire", 8, rampe(ratio, 2.0, 0.7, 8), round(ratio, 2),
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
    #
    # QUATRE CRITÈRES DEPUIS LE 17/08/2026. La recomposition part d'un cas
    # mesuré : Kioxia à 15/15 en plein krach de −43 %, parce que les deux
    # anciens critères (écart MM21/MM200, cloche z) mesuraient une ALTITUDE
    # contre des références qui suivent le cours — une droite de régression
    # refittée sur 20 mois de rampe post-IPO montait plus vite que le titre ne
    # chutait. Corrélation du bloc avec la seule mesure de vitesse du
    # pipeline : −0,15. Un bloc nommé « momentum » notait l'inverse.
    #
    # LA MÉTHODE DE LA REFONTE, pour la prochaine fois : les SIGNAUX viennent
    # de la littérature (Jegadeesh & Titman 1993 et Carhart 1997 pour le
    # rendement 12 mois hors dernier mois ; Jegadeesh 1990 pour la réversion
    # du dernier mois ; George & Hwang 2004 pour le plus haut 52 semaines ;
    # MSCI Momentum pour la division par la volatilité ; Barroso &
    # Santa-Clara 2015 et Daniel & Moskowitz 2016 pour les krachs du momentum
    # nu) — jamais d'un backtest sur nos 140 survivants corrélés, qui ne peut
    # rien prouver (data-snooping : Sullivan, Timmermann & White 1999). Les
    # SEUILS viennent de la population mesurée puis sont FIGÉS ici (l'idiome
    # des rampes du 07/08) : pas de percentile vivant, la note d'un titre ne
    # dépend jamais des autres. L'univers ne sert qu'à VÉRIFIER la mécanique.
    # Calibration du 17/08/2026 : 140 fiches, zone hebdomadaire W-FRI des
    # charts — à re-vérifier sur cours quotidiens complets via
    # tools/calibration_momentum.py (le réseau de la session ne portait pas
    # Yahoo). Moyenne du bloc mesurée : 9,9/15 (10,2 avant), dispersion/max
    # 0,203 (0,219 avant) — plus faible, et c'est ASSUMÉ : le RSI a été retiré
    # pour dispersion 0,17 ET contribution négative au classement ; ici la
    # dispersion cède 0,016 parce que les extrêmes artificiels disparaissent,
    # pas parce que le critère cesse de classer.
    #
    # LE PRINCIPE UNIFICATEUR : chaque référence est OBSERVÉE (un cours d'il y
    # a treize mois, un plus haut de 52 semaines), jamais AJUSTÉE sur les
    # données du titre — une référence ajustée court après le cours, c'est le
    # défaut qui a produit Kioxia. Le canal de régression survit, mais bridé
    # aux fenêtres qui veulent dire quelque chose.

    # 1. Le rendement réalisé, par unité de risque, EN CLOCHE (6 pts). Le
    # numérateur min(P, P−1m)/P−13m et le σ sont calculés par le screener
    # (calcul_momentum_intrants, où les choix sont documentés). La cloche —
    # plein de 0,3 à 2,0, nul sous −1,5 et au-delà de 3,5 (p5/p35/p85/p97 de
    # la population) — donne le plein à 47 % de l'univers, comme la cloche z
    # qu'elle remplace en critère principal. Au-delà de +2 par unité de
    # risque, on ne mesure plus une tendance mais un événement (rampe
    # post-IPO, squeeze) : l'excès redescend vers zéro, doctrine anti-chase
    # inchangée, référence changée.
    mr = ctx.get("mom_ratio")
    if mr is not None:
        mp, mv = ctx.get("mom_pct"), ctx.get("mom_vol_pct")
        if mp is not None and mv is not None:
            ph = (f"{'+' if mp >= 0 else ''}{_fr(mp, 0)} % en douze mois "
                  f"(dernier mois écarté) pour {_fr(mv, 0)} % de volatilité annuelle")
        else:
            ph = f"Rendement annuel à {_fr(mr, 2)} par unité de risque"
        ajoute("m", "momentum", 6, cloche(mr, -1.5, 0.3, 2.0, 3.5, 6),
               round(mr, 2), ph)
    else:
        ajoute("m", "momentum", 6, None, None, None,
               "moins de treize mois de cotation — rendement annuel non mesurable")

    # 2. La distance au plus haut 52 semaines (4 pts) — l'ancre d'altitude
    # LÉGITIME : observée, elle ne se déplace pas quand le titre monte
    # (George & Hwang 2004, qui bat le 12-1 dans leur échantillon). Rampe
    # −40 %/−5 % ≈ p10/p85 de la population. Critère ASSUMÉ asymétrique —
    # l'anti-chase du bloc vit dans les deux cloches, pas ici. Le screener
    # passe None sous 252 séances : le « plus haut 52 semaines » d'un titre
    # coté huit mois est le plus haut de sa courte vie, un post-IPO y serait
    # toujours « près de son sommet ».
    dd = ctx.get("drawdown_52w_pct")
    if dd is not None:
        ajoute("m", "sommet", 4, rampe(dd, -40, -5, 4), round(dd, 1),
               "Au plus haut de ses 52 dernières semaines" if dd >= 0 else
               f"À {_fr(abs(dd))} % sous son plus haut de 52 semaines")
    else:
        ajoute("m", "sommet", 4, None, None, None,
               "moins d'un an de cotation — plus haut 52 semaines non représentatif")

    # 3. La position dans le canal de régression (3 pts) — cloche symétrique
    # inchangée, mais retenue SEULEMENT si la fenêtre effective atteint 5 ans
    # (1260 séances, non arrondies : 4 ans et demi ne « passent » pas par
    # round()). C'est le seuil que la fiche affichait déjà (« droite non
    # utilisable en l'état, 5 ans minimum ») pendant que la note, elle,
    # donnait 8/8 dessus — la note s'aligne enfin sur son propre bandeau.
    z = ctx.get("z")
    seances = ctx.get("reg_seances")
    if z is not None and seances is not None and seances >= 1260:
        ajoute("m", "position", 3, cloche(z, -3, -1.5, 1, 3, 3), round(z, 2),
               f"À {_fr(z)}σ de sa tendance sur {round(seances / 252)} ans")
    elif z is not None:
        if seances is None:
            _motif_pos = "fenêtre de régression inconnue — canal non retenu"
        else:
            _annees = seances / 252
            _motif_pos = (f"fenêtre de régression de {_fr(_annees)} "
                          f"an{'s' if _annees >= 2 else ''} — canal non "
                          "significatif sous 5 ans")
        ajoute("m", "position", 3, None, None, None, _motif_pos)
    else:
        ajoute("m", "position", 3, None, None, None, "régression indisponible")

    # 4. La vélocité de la MM21 sur cinq séances (2 pts) — le détecteur de
    # retournement RÉCENT, complément exact du rendement 12-1 qui est aveugle
    # au dernier mois par construction. Poids faible : la fenêtre d'un mois
    # est la zone de réversion documentée, ce critère confirme ou coupe, il
    # ne porte pas le bloc. Rampe −3,5 %/+4,5 % = p10/p90 de la population.
    # L'intrant est un champ dédié et nullable — jamais le slope_mm21_pct de
    # detect_cross, qui vaut 0.0 par défaut (zéro silencieux, interdit ici).
    pente = ctx.get("pente_mm21_pct")
    if pente is not None:
        ajoute("m", "dynamique", 2, rampe(pente, -3.5, 4.5, 2), round(pente, 2),
               f"Moyenne 21 jours en {'hausse' if pente >= 0 else 'baisse'} de "
               f"{_fr(abs(pente))} % sur cinq séances")
    else:
        ajoute("m", "dynamique", 2, None, None, None,
               "vélocité court terme non calculable")

    # Le RSI, retiré le 07/08/2026, reste hors note : cloche 35-65 qui donnait
    # le maximum à 82 % des titres, dispersion 0,17, contribution NÉGATIVE au
    # classement. L'écart MM21/MM200 l'a rejoint le 17/08 : son information
    # (l'altitude de moyen terme) est portée par le rendement 12-1 et le
    # sommet, avec de meilleures références. Tous deux restent affichés sur
    # la fiche, comme information de marché.

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
