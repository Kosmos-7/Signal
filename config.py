"""
config.py — Paramètres centralisés de Signal.

Single source of truth pour les constantes utilisées par portfolio_agent.py,
screener.py et update_prices.py. Modifier ici se propage partout.

Sections :
  - COÛTS DE TRANSACTION (Phase 1)
  - FISCALITÉ FRANÇAISE (Phase 1)
  - VIX DAMPENER (Phase 2 — futurs paramètres, déjà déclarés)
  - UNIVERS DU SCREENER (Phase 4 — futurs paramètres)

Toute modification doit être documentée par un commentaire indiquant la source
ou le rationale du choix (ex : "Euronext + Saxo retail : 5bps broker + 10bps slippage estimé").
"""

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — COÛTS DE TRANSACTION
# ─────────────────────────────────────────────────────────────────────────────

# Frais de transaction one-way en basis points (bps = 1/100 de %).
# Appliqués à l'achat ET à la vente séparément (donc round-trip = 2 × TRANSACTION_COST_BPS).
# Ordre de grandeur retail réaliste sur courtiers européens :
#   - Broker fee Saxo/Bourse Direct/DEGIRO : 2-5 bps sur les actions liquides
#   - Slippage marché (bid-ask + impact) sur ordres market : 3-8 bps en moyenne
#   - Total one-way conservateur : 7-8 bps
#   - Total round-trip conservateur : 15 bps (= 0.15%)
# Référence académique : Frazzini, Israel, Moskowitz (2018) — "Trading Costs", AQR
# Note : NE PAS confondre bps avec % — 15 bps = 0.15%, PAS 15%.
TRANSACTION_COST_BPS = 7.5  # one-way ; round-trip = 15 bps

# Seuil minimal en EUR en-dessous duquel un achat est rejeté (budget trop faible
# pour absorber les coûts fixes). Cohérent avec le seuil 50€ déjà présent dans
# executer_decisions(), mais on le centralise ici.
MIN_TRADE_EUR = 50.0

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — FISCALITÉ FRANÇAISE (PFU sur compte-titres ordinaire)
# ─────────────────────────────────────────────────────────────────────────────

# Prélèvement Forfaitaire Unique (flat tax) sur les plus-values mobilières.
# Décomposition légale, VÉRIFIÉE LE 08/08/2026 :
#   - 12,8 % impôt sur le revenu
#   - 18,6 % prélèvements sociaux
#   - TOTAL : 31,4 %
# Source : article 200 A du CGI pour l'assiette ; loi de financement de la
# Sécurité sociale pour 2026 (promulguée le 30/12/2025, validée pour
# l'essentiel par le Conseil constitutionnel) pour le taux social.
#
# LE TAUX A CHANGÉ, et ce fichier a porté l'ancien pendant sept mois. La LFSS
# 2026 crée une contribution financière pour l'autonomie de 1,4 point : la CSG
# sur les revenus du capital passe de 9,2 à 10,6 %, donc les prélèvements
# sociaux de 17,2 à 18,6 % et le PFU de 30 à 31,4 %, au 1er janvier 2026.
# Le piège est que la hausse ne touche PAS tout : assurance-vie, PEL, CEL, PEP,
# revenus fonciers et plus-values immobilières restent à 17,2 %. Elle touche
# bien les plus-values de cession de valeurs mobilières — notre cas.
#
# CE QUE CE CHANGEMENT NE FAIT PAS : rejouer le passé. Les impôts déjà
# comptabilisés sur les ventes de 2026 l'ont été à 30 % ; les recalculer
# changerait un historique publié, ce qui est une décision éditoriale et non
# une correction de taux. Le sujet est ouvert, à trancher explicitement.
#
# S'applique uniquement à la PLUS-VALUE RÉALISÉE (à la vente), pas aux plus-values latentes.
PFU_RATE = 0.314

# Variante PEA après 5 ans de détention : prélèvements sociaux seuls. Eux aussi
# passent à 18,6 % au 01/01/2026, et le nouveau taux s'applique au retrait sur
# tout le gain, y compris la part constituée avant 2026.
# Non utilisé actuellement (Signal détient des US stocks → compte-titres obligatoire),
# mais déclaré pour permettre un éventuel toggle PEA dans le futur.
PEA_TAX_RATE_AFTER_5Y = 0.186

# Régime fiscal actif (un seul à la fois pour le moment).
# Valeurs possibles : "PFU" (compte-titres, défaut) | "PEA_5Y" (PEA après 5 ans)
TAX_REGIME = "PFU"


def cost_one_way_eur(montant_eur: float) -> float:
    """Frais one-way sur un montant en EUR (achat OU vente, pas les deux).

    Exemple : trade de 1 000€ → 1 000 × 15/2 / 10000 = 0.75€ one-way,
              soit 1.50€ round-trip.
    """
    return round(montant_eur * TRANSACTION_COST_BPS / 10000.0, 4)


def tax_on_gain_eur(plus_value_eur: float) -> float:
    """Calcule l'impôt PFU sur une plus-value en EUR.

    - Si plus_value_eur <= 0 (perte ou breakeven) : impôt = 0
    - Sinon : impôt = plus_value_eur × PFU_RATE

    Note : on ne modélise pas le report de pertes des années antérieures
    (les pertes peuvent compenser des gains sur 10 ans en France).
    À la place, on enregistre les pertes dans `total_pertes_reportables`
    pour une future implémentation.
    """
    if plus_value_eur <= 0:
        return 0.0
    rate = PFU_RATE if TAX_REGIME == "PFU" else PEA_TAX_RATE_AFTER_5Y
    return round(plus_value_eur * rate, 2)


def apply_buy_cost(montant_brut_eur: float) -> tuple[float, float]:
    """Applique les frais à un achat.

    Args:
        montant_brut_eur: montant brut (prix × quantité en EUR)

    Returns:
        (cash_debite_des_liquidites, frais_eur)
        - cash_debite : ce qui sort des liquidités = brut + frais
        - frais_eur   : montant des frais (pour journalisation)

    Note : la base fiscale (= montant_investi) inclut les frais d'achat
    pour réduire la plus-value à la revente. C'est la règle française.
    """
    frais = cost_one_way_eur(montant_brut_eur)
    return round(montant_brut_eur + frais, 2), frais


def apply_sell_cost_and_tax(
    montant_brut_vente_eur: float,
    montant_investi_eur: float,
) -> dict:
    """Applique frais + PFU sur une vente.

    Args:
        montant_brut_vente_eur: prix × quantité au moment de la vente (en EUR)
        montant_investi_eur: base fiscale (achat + frais achat, en EUR)

    Returns:
        dict avec :
          - frais_vente_eur : frais de vente
          - brut_net_frais_eur : brut moins frais de vente
          - plus_value_eur : brut_net_frais - montant_investi (peut être négatif)
          - impot_pfu_eur : PFU sur plus-value (0 si perte)
          - cash_recupere_eur : ce qui revient en liquidités (brut - frais - impôt)
          - perte_reportable_eur : abs(plus-value) si négative, sinon 0
    """
    frais_vente = cost_one_way_eur(montant_brut_vente_eur)
    brut_net_frais = round(montant_brut_vente_eur - frais_vente, 2)
    plus_value = round(brut_net_frais - montant_investi_eur, 2)
    impot = tax_on_gain_eur(plus_value)
    cash_recupere = round(brut_net_frais - impot, 2)
    perte_reportable = round(abs(plus_value), 2) if plus_value < 0 else 0.0
    return {
        "frais_vente_eur": frais_vente,
        "brut_net_frais_eur": brut_net_frais,
        "plus_value_eur": plus_value,
        "impot_pfu_eur": impot,
        "cash_recupere_eur": cash_recupere,
        "perte_reportable_eur": perte_reportable,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — VIX (indicateur contextuel, dampener DÉSACTIVÉ)
# ─────────────────────────────────────────────────────────────────────────────
#
# Décision : le dampener est DÉSACTIVÉ. Approche neutre — on n'ajoute aucune
# mécanique post-LLM qui modifie les scores selon un régime de marché.
# Le VIX reste FETCHÉ et AFFICHÉ comme simple information contextuelle.
#
# Décision actuelle : le VIX continue d'être FETCHÉ et AFFICHÉ pour transparence
# (dashboard + prompt Claude) mais n'INFLUENCE PLUS le scoring (multiplier = 1.0).
# Claude peut le citer comme contexte macro dans son analyse éditoriale, sans
# qu'il y ait une mécanique post-LLM qui dampene les scores.
#
# NOTE v3 (2026-06) : le point d'application dans score_ticker a été RETIRÉ par la
# refonte v3 — flipper VIX_DAMPENER_ENABLED = True ne changerait plus que des logs.
# Réactiver le dampener exigerait de réintroduire l'application du multiplier dans
# le bucket timing de screener.score_ticker. Les paramètres restent calibrés ci-dessous.

VIX_DAMPENER_INTERCEPT = 1.5
VIX_DAMPENER_SLOPE     = 0.025
VIX_DAMPENER_MIN       = 0.20
VIX_DAMPENER_ENABLED   = False  # désactivé Phase 3 — VIX reste info contextuelle


def vix_multiplier(vix: float | None) -> float:
    """Valeur PUREMENT CONTEXTUELLE — n'est appliquée à AUCUN score.

    Son point d'application dans score_ticker a été retiré par la refonte v3
    (cf. note ci-dessus) ; seul portfolio_agent.py la lit encore, comme
    information de régime passée au prompt. Doctrine depuis le 17/08/2026 :
    le risque entre dans la note UNE seule fois, par la volatilité du titre au
    dénominateur du critère momentum (note_v4, bloc m) — rebrancher ce
    multiplier sur le bloc compterait le risque deux fois. Si vix est
    None/invalide ou le dampener désactivé → 1.0 (no-op).
    """
    if not VIX_DAMPENER_ENABLED:
        return 1.0
    if vix is None or vix <= 0:
        return 1.0
    raw = VIX_DAMPENER_INTERCEPT - VIX_DAMPENER_SLOPE * float(vix)
    return max(VIX_DAMPENER_MIN, min(1.0, raw))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — (section retirée : approche neutre, validation via le portefeuille IA)
# ─────────────────────────────────────────────────────────────────────────────

# (Les définitions de régime de backtest ont été retirées — plus de backtest.)


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — UNIVERS DU SCREENER (à activer après validation)
# ─────────────────────────────────────────────────────────────────────────────

# Sources d'index pour construire l'univers dynamiquement.
# Chacun est une liste Wikipedia parsable via pandas.read_html.
UNIVERSE_INDEX_SOURCES = [
    {"name": "sp500",      "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"},
    {"name": "nasdaq100",  "url": "https://en.wikipedia.org/wiki/Nasdaq-100"},
    {"name": "stoxx600",   "url": "https://en.wikipedia.org/wiki/STOXX_Europe_600"},
    {"name": "cac40",      "url": "https://en.wikipedia.org/wiki/CAC_40"},
    {"name": "dax40",      "url": "https://en.wikipedia.org/wiki/DAX"},
]

# Pré-filtres avant scoring complet (Stage 1)
UNIVERSE_MIN_MARKET_CAP_USD  = 500_000_000   # 500M$ — exclut microcaps illiquides
UNIVERSE_MIN_ADV_USD         = 5_000_000     # 5M$ ADV 20j — exclut illiquide
UNIVERSE_MIN_LISTING_YEARS   = 3             # exclut IPO récentes (MM200 + z-score fiables)

# Cache fondamentaux (les fondamentaux ne bougent que trimestriellement)
FUNDAMENTALS_CACHE_TTL_DAYS  = 90

# Watchlist finale (taille de la sortie du screener) — SOURCE UNIQUE, lue par screener.py
WATCHLIST_SIZE = 30

# Contraintes de diversification sur la watchlist
WATCHLIST_MAX_PER_SECTOR     = 5
WATCHLIST_MAX_PER_COUNTRY    = 12

# Date du premier point du portefeuille. Les benchmarks s'ancrent ICI et non au
# 1er janvier de l'année courante : ancrés à l'année, ils seraient repartis de
# zéro au 1er janvier 2027 pendant que la performance du portefeuille continue
# depuis la création — l'écart au benchmark serait devenu un non-sens sans
# qu'aucun test ne le voie venir. Constante et non premier point de
# performance_history : l'historique est plafonné à ~260 entrées.
PORTFOLIO_DEBUT = "2026-01-02"

# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE PONDÉRÉE PAR LE TEMPS (03/08/2026)
# ─────────────────────────────────────────────────────────────────────────────
# Décision propriétaire : « de la liquidité ne doit pas rentrer dans le calcul
# de la performance ». L'ancienne formule (capital / capital_initial − 1)
# faisait grossir le dénominateur à chaque injection : +10 k€ versés le
# 03/08/2026 faisaient passer la performance affichée de +17,55 % à +11,70 %
# sans qu'aucune position n'ait bougé — un virement se lisait comme une
# contre-performance. Symétriquement, ne PAS grossir la base aurait transformé
# le virement en gain. Les deux lectures étaient fausses.
#
# La méthode des fonds règle ça : on chaîne les rendements des sous-périodes
# séparées par les injections. Chaque injection fige le rendement acquis
# (facteur) et ouvre une nouvelle base ; l'argent frais ne compte ni comme
# gain ni comme perte, il ne fait que s'ajouter à la base de la période
# suivante.
#
# RAFFINEMENT (03/08/2026, seconde décision du même jour) : un versement reste
# HORS du périmètre de mesure tant que la stratégie n'a pas pu en disposer.
# Entre le virement et le run hebdomadaire suivant de l'agent, le cash est un
# dépôt administratif : le compter aurait dilué la performance des positions
# (des positions à +10 % sur la semaine n'auraient affiché que +6,9 %). Il
# entre dans le périmètre au premier run de l'agent qui suit — INVESTI OU NON.
# « Ou non » est délibéré : à partir du moment où l'agent a vu le cash, le
# garder liquide est un choix de stratégie, et sa traînée doit compter. Ne
# compter le cash qu'une fois investi ouvrirait une échappatoire — un
# portefeuille paraîtrait brillant en n'investissant jamais — et se heurterait
# à la fongibilité : quand l'agent vend 2 k€ et achète 5 k€ la même semaine,
# personne ne peut dire quels euros viennent du versement.
#
# Chaque entrée de `injections` (portfolio.json) porte donc :
#   date          — jour du versement
#   montant       — somme versée
#   capital_post  — None TANT QUE le versement attend ; au premier run de
#                   l'agent, celui-ci l'estampille avec le capital TOTAL du
#                   moment, FIGÉ là. On ne le relit pas dans
#                   performance_history : l'historique est plafonné à ~260
#                   points, et le jour où la date en serait sortie, la
#                   performance aurait silencieusement changé de valeur.
#   effective_le  — date de l'estampille (traçabilité).
#
# RETRAITS. Une entrée à montant NÉGATIF est un retrait. Deux différences avec
# un dépôt : il est effectif immédiatement (le cash part, il n'y a rien à
# « mettre à disposition »), donc capital_post se fige à l'écriture, jamais
# None ; et capital_initial — qui est par convention le TOTAL NET VERSÉ —
# se décrémente du montant retiré. Le chaînage est le même : la période se
# ferme sur le capital d'avant le retrait, la suivante ouvre sur la base
# réduite, et la performance ne bouge pas d'un centième au moment du retrait.

def perf_ponderee_temps(injections, capital_actuel, capital_depart):
    """Performance (%) chaînée entre injections, insensible aux versements.

    Un versement en attente (capital_post is None) est soustrait du capital
    mesuré : il n'est ni un gain, ni une perte, ni même encore une base."""
    base, facteur, en_attente = float(capital_depart), 1.0, 0.0
    for inj in sorted(injections or [], key=lambda i: i["date"]):
        if inj.get("capital_post") is None:
            en_attente += float(inj["montant"])
            continue
        if base <= 0:
            return 0.0
        facteur *= (float(inj["capital_post"]) - float(inj["montant"])) / base
        base = float(inj["capital_post"])
    if base <= 0:
        return 0.0
    return round((facteur * ((float(capital_actuel) - en_attente) / base) - 1) * 100, 2)


def max_drawdown_indice(history):
    """Drawdown maximal (%) mesuré sur l'INDICE de performance (série `perf`).

    Sur le capital, un retrait creuserait un faux plongeon et une injection
    rehausserait le pic sans qu'aucune position n'ait bougé. La série `perf`
    étant pondérée par le temps donc insensible aux flux, c'est elle qui
    mesure ce que la stratégie a réellement fait subir au capital investi."""
    pic, dd = float("-inf"), 0.0
    for h in history or []:
        p = h.get("perf")
        if p is None:
            continue
        v = 1 + float(p) / 100
        if v > pic:
            pic = v
        if pic > 0:
            dd = min(dd, (v - pic) / pic * 100)
    return round(dd, 2)
