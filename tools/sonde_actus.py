#!/usr/bin/env python3
"""Sonde de sources d'actualités : laquelle répond, avec quoi dedans.

POURQUOI UNE SONDE PLUTÔT QU'UN CHOIX. Le point du matin ne lit qu'une source,
`finnhub /news?category=general`, qui a rendu SIX dépêches exploitables le
7 août 2026. Six dépêches ne portent pas une lettre matinale : elles portent
trois paragraphes. Il faut donc d'autres sources, et la tentation est d'en
choisir une liste « qui a l'air bien ». C'est exactement ce qu'il ne faut pas
faire : la moitié des flux RSS de la presse économique ont été fermés,
transformés en murs payants ou déplacés depuis dix ans, et une URL qui existait
en 2019 rend un 404 aujourd'hui sans que personne ne s'en aperçoive.

On mesure donc AVANT de choisir. Cette sonde prend une liste de candidats, tape
chacun une fois, et écrit un rapport chiffré : code HTTP, nombre d'articles,
combien datent de moins de 24 h, combien portent un résumé, combien portent une
image, et trois titres en échantillon. Le rapport est commité pour qu'on puisse
le relire, et le choix des sources se fait sur ces chiffres.

ELLE NE TOUCHE À RIEN. Aucun post n'est écrit, aucune source n'est branchée :
cette sonde n'a qu'un effet, produire `sonde_actus.json`. C'est délibéré —
brancher une source sur le point du matin est une décision éditoriale, pas le
sous-produit d'un test technique.

POURQUOI EN ACTIONS. Les flux d'actualité sont inaccessibles depuis l'atelier
de développement (proxy sortant) : huit flux testés, huit à zéro. La mesure ne
peut être faite que depuis un runner, comme les sondes consensus et cotation.

Usage :
    python3 tools/sonde_actus.py                  # tous les candidats
    python3 tools/sonde_actus.py --genre rss      # les flux seuls
    python3 tools/sonde_actus.py --sortie x.json
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

UA = ("Mozilla/5.0 (compatible; SignalBot/1.0; +https://kosmos-7.github.io/Signal/) "
      "sonde de sources, lecture seule")
# Deux cents candidats en série, à vingt secondes de patience chacun, font plus
# d'une heure si la liste est morte — au-delà du délai du job. Douze secondes
# suffisent largement à un flux vivant, et huit requêtes en parallèle ramènent
# le tout à une poignée de minutes. Huit et pas trente : la sonde lit des sites
# d'information, elle n'a aucune raison de leur ressembler à une attaque.
DELAI = 12
PARALLELE = 8
SORTIE = "sonde_actus.json"

# ── Candidats ────────────────────────────────────────────────────────────────
# Une entrée = un GET. `cle` marque les endpoints qui exigent une clé d'API :
# ils sont sautés (et notés comme tels) si la variable d'environnement manque,
# plutôt que comptés en échec — un 401 faute de secret ne dit rien de la source.
#
# La liste est VOLONTAIREMENT trop large. Un candidat mort coûte une seconde de
# runner ; un candidat jamais testé coûte une source qu'on n'aura pas.
CANDIDATS = [
    # — Presse économique française et francophone —
    ("boursorama-bourse",  "https://www.boursorama.com/bourse/actualites/rss/", "rss", "fr"),
    ("boursorama-eco",     "https://www.boursorama.com/actualite-economique/feed/", "rss", "fr"),
    ("latribune",          "https://www.latribune.fr/feed.xml", "rss", "fr"),
    ("latribune-eco",      "https://www.latribune.fr/economie/rss.html", "rss", "fr"),
    ("lesechos-finance",   "https://services.lesechos.fr/rss/les-echos-finance-marches.xml", "rss", "fr"),
    ("lesechos-eco",       "https://services.lesechos.fr/rss/les-echos-economie.xml", "rss", "fr"),
    ("lemonde-eco",        "https://www.lemonde.fr/economie/rss_full.xml", "rss", "fr"),
    ("lefigaro-eco",       "https://www.lefigaro.fr/rss/figaro_economie.xml", "rss", "fr"),
    ("lefigaro-flash-eco", "https://www.lefigaro.fr/rss/figaro_flash-eco.xml", "rss", "fr"),
    ("liberation-eco",     "https://www.liberation.fr/arc/outboundfeeds/rss-all/category/economie/", "rss", "fr"),
    ("capital",            "https://www.capital.fr/rss", "rss", "fr"),
    ("challenges",         "https://www.challenges.fr/rss.xml", "rss", "fr"),
    ("usinenouvelle",      "https://www.usinenouvelle.com/rss", "rss", "fr"),
    ("zonebourse",         "https://www.zonebourse.com/rss/actualite/", "rss", "fr"),
    ("abcbourse",          "https://www.abcbourse.com/rss/actus.xml", "rss", "fr"),
    ("francetvinfo-eco",   "https://www.francetvinfo.fr/economie.rss", "rss", "fr"),
    ("rfi-eco",            "https://www.rfi.fr/fr/%C3%A9conomie/rss", "rss", "fr"),
    ("rtbf-eco",           "https://rss.rtbf.be/article/rss/highlight_rtbfinfo_economie.xml", "rss", "fr"),
    ("lecho-be",           "https://www.lecho.be/rss/top_stories.xml", "rss", "fr"),
    ("radiocanada-eco",    "https://ici.radio-canada.ca/rss/4159", "rss", "fr"),

    # — Presse et agences internationales —
    ("yahoo-finance",      "https://finance.yahoo.com/news/rssindex", "rss", "en"),
    ("yahoo-ticker-aapl",  "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US", "rss", "en"),
    ("marketwatch-top",    "https://feeds.content.dowjones.io/public/rss/mw_topstories", "rss", "en"),
    ("marketwatch-mkt",    "https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "rss", "en"),
    ("cnbc-finance",       "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "rss", "en"),
    ("cnbc-top",           "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "rss", "en"),
    ("guardian-business",  "https://www.theguardian.com/uk/business/rss", "rss", "en"),
    ("bbc-business",       "https://feeds.bbci.co.uk/news/business/rss.xml", "rss", "en"),
    ("npr-business",       "https://feeds.npr.org/1006/rss.xml", "rss", "en"),
    ("investing-news",     "https://www.investing.com/rss/news.rss", "rss", "en"),
    ("investing-stock",    "https://www.investing.com/rss/news_25.rss", "rss", "en"),
    ("seekingalpha",       "https://seekingalpha.com/market_currents.xml", "rss", "en"),
    ("nasdaq-original",    "https://www.nasdaq.com/feed/rssoutbound?category=Markets", "rss", "en"),
    ("scmp-business",      "https://www.scmp.com/rss/92/feed", "rss", "en"),
    ("aljazeera-eco",      "https://www.aljazeera.com/xml/rss/all.xml", "rss", "en"),

    # — Sources primaires : chiffres et citations verbatim —
    ("bce-press",          "https://www.ecb.europa.eu/rss/press.html", "rss", "en"),
    ("fed-press",          "https://www.federalreserve.gov/feeds/press_all.xml", "rss", "en"),
    ("boe-news",           "https://www.bankofengland.co.uk/rss/news", "rss", "en"),
    ("banque-france",      "https://www.banque-france.fr/fr/rss.xml", "rss", "fr"),
    ("insee",              "https://www.insee.fr/fr/information/rss/1", "rss", "fr"),
    ("eurostat",           "https://ec.europa.eu/eurostat/api/dissemination/rss/en/euro-indicators.rss", "rss", "en"),
    ("bls",                "https://www.bls.gov/feed/bls_latest.rss", "rss", "en"),
    ("globenewswire",      "https://www.globenewswire.com/RssFeed/subjectcode/22-Earnings%20Releases%20And%20Operating%20Results/feedTitle/GlobeNewswire%20-%20Earnings", "rss", "en"),
    ("businesswire",       "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVtRWQ==", "rss", "en"),
    ("amf",                "https://www.amf-france.org/fr/rss.xml", "rss", "fr"),
    ("euronext",           "https://live.euronext.com/en/rss/news", "rss", "en"),

    # — Hors marchés : l'accroche du matin et le « fun fact » —
    ("boxofficemojo",      "https://www.boxofficemojo.com/rss/", "rss", "en"),
    ("variety-boxoffice",  "https://variety.com/v/film/feed/", "rss", "en"),
    ("hollywoodreporter",  "https://www.hollywoodreporter.com/feed/", "rss", "en"),
    ("theverge",           "https://www.theverge.com/rss/index.xml", "atom", "en"),
    ("arstechnica",        "https://feeds.arstechnica.com/arstechnica/index", "rss", "en"),
    ("sciencedaily",       "https://www.sciencedaily.com/rss/top/science.xml", "rss", "en"),
    ("lesnumeriques",      "https://www.lesnumeriques.com/rss.xml", "rss", "fr"),

    # — API (clé requise) —
    ("finnhub-general",    "https://finnhub.io/api/v1/news?category=general", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-forex",      "https://finnhub.io/api/v1/news?category=forex", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-crypto",     "https://finnhub.io/api/v1/news?category=crypto", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-merger",     "https://finnhub.io/api/v1/news?category=merger", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-company",    "https://finnhub.io/api/v1/company-news?symbol=NVDA&from={hier}&to={jour}", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-earnings",   "https://finnhub.io/api/v1/calendar/earnings?from={jour}&to={jour}", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-economic",   "https://finnhub.io/api/v1/calendar/economic", "api", "en", "FINNHUB_API_KEY"),
    ("finnhub-ipo",        "https://finnhub.io/api/v1/calendar/ipo?from={hier}&to={jour}", "api", "en", "FINNHUB_API_KEY"),

    # — Recensement du 08/08/2026 : cent quarante-deux flux ouverts de plus,
    #   rapportés par cinq recherches menées en parallèle sur des angles
    #   distincts (presse française, agences anglophones, sources primaires,
    #   API, hors-marchés) puis passés à un critique de complétude. Aucune
    #   n'a pu être vérifiée depuis l'atelier : c'est TOUT l'objet de la sonde.
    ("le-monde-conomie-fran-aise", "https://www.lemonde.fr/economie-francaise/rss_full.xml", "rss", "fr"),
    ("le-monde-conomie-mondiale", "https://www.lemonde.fr/economie-mondiale/rss_full.xml", "rss", "fr"),
    ("le-figaro-bourse", "https://www.lefigaro.fr/rss/figaro_bourse.xml", "rss", "fr"),
    ("bfm-business-bfmtv-conomie", "https://www.bfmtv.com/rss/economie/", "rss", "fr"),
    ("bfm-business-entreprises", "https://www.bfmtv.com/rss/economie/entreprises/", "rss", "fr"),
    ("bfm-conomie-internationale", "https://www.bfmtv.com/rss/economie/international/", "rss", "fr"),
    ("capital-fr-flux-prisma-afp-aof-reu", "https://feed.prismamediadigital.com/v1/cap/rss?sources=capital,polemik,xerfi,management,capital-avec-agence-france-presse,capital-avec-aof,capital-avec-reuters,capital-avec-optimaretraite,aeronewstv", "rss", "fr"),
    ("challenges-conomie", "https://www.challenges.fr/economie/rss.xml", "rss", "fr"),
    ("l-usine-nouvelle-industrie-usines", "http://rss.usinenouvelle.com/industrie-usines", "rss", "fr"),
    ("l-usine-nouvelle-infographies", "https://www.usinenouvelle.com/infographie/?rss=1", "rss", "fr"),
    ("abc-bourse-actualit-s", "https://www.abcbourse.com/rss/displaynewsrss", "rss", "fr"),
    ("abc-bourse-analyses", "https://www.abcbourse.com/rss/lastanalysisrss", "rss", "fr"),
    ("abc-bourse-chroniques", "https://www.abcbourse.com/rss/chroniquesrss", "rss", "fr"),
    ("les-echos-investir-conseils-boursi", "https://services.lesechos.fr/rss/investir-conseils-boursiers.xml", "rss", "fr"),
    ("les-echos-start-up-conomie", "https://services.lesechos.fr/rss/les-echos-start-up.xml", "rss", "fr"),
    ("les-echos-france-syndication", "https://syndication.lesechos.fr/rss/rss_france.xml", "rss", "fr"),
    ("google-news-conomie-edition-france", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr&gl=FR&ceid=FR:fr", "rss", "fr"),
    ("google-news-recherche-bourse-cac-4", "https://news.google.com/rss/search?q=bourse+OR+%22CAC+40%22+OR+march%C3%A9s&hl=fr&gl=FR&ceid=FR:fr", "rss", "fr"),
    ("la-presse-qu-bec-affaires", "https://www.lapresse.ca/affaires/rss", "rss", "fr"),
    ("radio-canada-conomie-et-affaires", "http://rss.radio-canada.ca/fils/nouvelles/economieaffaires.xml", "rss", "fr"),
    ("rtbf-info-conomie", "https://rss.rtbf.be/article/rss/highlight_rtbf_info-economie.xml?source=internal", "rss", "fr"),
    ("rts-info-conomie-suisse", "https://www.rts.ch/info/economie/?format=rss/news", "rss", "fr"),
    ("le-temps-conomie-suisse", "https://www.letemps.ch/economie.rss", "rss", "fr"),
    ("la-tribune-actualit", "https://www.latribune.fr/rss/rubriques/actualite.html", "rss", "fr"),
    ("la-tribune-entreprises-finance", "https://www.latribune.fr/rss/rubriques/entreprises-finance.html", "rss", "fr"),
    ("marketwatch-real-time-headlines", "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines", "rss", "en"),
    ("cnbc-top-news", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "rss", "en"),
    ("cnbc-economy", "https://www.cnbc.com/id/20910258/device/rss/rss.html", "rss", "en"),
    ("cnbc-finance-2", "https://www.cnbc.com/id/10001147/device/rss/rss.html", "rss", "en"),
    ("cnbc-earnings", "https://www.cnbc.com/id/15839135/device/rss/rss.html", "rss", "en"),
    ("the-guardian-economics", "https://www.theguardian.com/business/economics/rss", "rss", "en"),
    ("yahoo-finance-flux-par-ticker-mult", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,NVDA,AMZN,GOOGL&region=US&lang=en-US", "rss", "en"),
    ("nikkei-asia-flux-principal", "https://asia.nikkei.com/rss/feed/nar", "rss", "en"),
    ("business-insider-markets", "https://markets.businessinsider.com/rss/news", "rss", "en"),
    ("benzinga-flux-general", "https://feeds.benzinga.com/benzinga", "rss", "en"),
    ("google-news-rss-substitut-reuters", "https://news.google.com/rss/search?q=site:reuters.com+markets+OR+stocks+when:1d&hl=en-US&gl=US&ceid=US:en", "rss", "en"),
    ("google-news-rss-substitut-ap", "https://news.google.com/rss/search?q=site:apnews.com+business+OR+economy+when:1d&hl=en-US&gl=US&ceid=US:en", "rss", "en"),
    ("google-news-topic-business-filet-d", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en", "rss", "en"),
    ("financial-times-home-international", "https://www.ft.com/rss/home/international", "rss", "en"),
    ("sky-news-business", "https://feeds.skynews.com/feeds/rss/business.xml", "rss", "en"),
    ("bce-taux-de-change-de-reference-du", "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml", "api", "en"),
    ("bce-communiques-de-presse", "https://www.ecb.europa.eu/rss/pr.html", "rss", "en"),
    ("fed-communiques-de-politique-monet", "https://www.federalreserve.gov/feeds/press_monetary.xml", "rss", "en"),
    ("fed-discours-des-gouverneurs", "https://www.federalreserve.gov/feeds/speeches.xml", "rss", "en"),
    ("bank-of-england-publications", "https://www.bankofengland.co.uk/rss/publications", "rss", "en"),
    ("banque-du-japon-nouveautes-anglais", "https://www.boj.or.jp/en/rss/whatsnew.xml", "rss", "en"),
    ("banque-nationale-suisse-actualites", "https://www.snb.ch/public/en/rss/news", "rss", "en"),
    ("bri-bis-communiques-de-presse", "https://www.bis.org/list/pressrels/index.rss", "rss", "en"),
    ("banque-de-france-communiques-de-pr", "https://www.banque-france.fr/fr/communiques-de-presse/rss", "rss", "fr"),
    ("eurostat-communiques-de-presse-new", "https://ec.europa.eu/eurostat/cache/RSS/rss_estat_news.xml", "rss", "en"),
    ("eurostat-mises-a-jour-de-donnees", "https://ec.europa.eu/eurostat/api/dissemination/catalogue/rss/en/statistics-update.rss", "rss", "en"),
    ("bls-employment-situation-emploi-am", "https://www.bls.gov/feed/empsit.rss", "rss", "en"),
    ("bls-consumer-price-index-inflation", "https://www.bls.gov/feed/cpi.rss", "rss", "en"),
    ("bea-communiques-pib-revenus-depens", "https://apps.bea.gov/rss/rss.xml", "rss", "en"),
    ("destatis-communiques-de-presse-all", "https://www.destatis.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed_Pressemitteilungen.xml", "rss", "autre"),
    ("eia-today-in-energy", "https://www.eia.gov/rss/todayinenergy.xml", "rss", "en"),
    ("sec-communiques-de-presse", "https://www.sec.gov/news/pressreleases.rss", "rss", "en"),
    ("sec-edgar-derniers-depots-8-k", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom", "rss", "en"),
    ("amf-communiques-de-presse-et-sanct", "https://www.amf-france.org/fr/flux-rss/display/23", "rss", "fr"),
    ("amf-toutes-les-actualites-et-publi", "https://www.amf-france.org/fr/flux-rss/display/21", "rss", "fr"),
    ("esma-actualites-du-regulateur-euro", "https://www.esma.europa.eu/flux-rss", "rss", "en"),
    ("business-wire-tous-les-communiques", "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkpaGVlYXg==", "rss", "en"),
    ("globenewswire-communiques-des-soci", "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20about%20Public%20Companies", "rss", "en"),
    ("pr-newswire-tous-les-communiques", "https://www.prnewswire.com/rss/news-releases-list.rss", "rss", "en"),
    ("nasdaq-resultats-trimestriels", "https://www.nasdaq.com/feed/rssoutbound?category=Earnings", "rss", "en"),
    ("stooq-quotes-csv-indices", "https://stooq.com/q/l/?s=^spx+^ndq+^dji+^dax+^cac+^ftm&f=sd2t2ohlcv&h&e=csv", "api", "autre"),
    ("deadline-vertical-box-office", "https://deadline.com/v/box-office/feed/", "rss", "en"),
    ("boxoffice-pro", "https://www.boxofficepro.com/feed/", "rss", "en"),
    ("allocine-news-cinema", "https://www.allocine.fr/rss/news-cine.xml", "rss", "fr"),
    ("gamesindustry-biz", "https://www.gamesindustry.biz/feed", "rss", "en"),
    ("eurogamer", "https://www.eurogamer.net/feed", "rss", "en"),
    ("polygon", "https://www.polygon.com/rss/index.xml", "rss", "en"),
    ("jeuxvideo-com-actualites", "https://www.jeuxvideo.com/rss/rss-news.xml", "rss", "fr"),
    ("steam-web-api-isteamnews-getnewsfo", "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=730&count=10&maxlength=400&format=json", "api", "en"),
    ("l-equipe-flux-edito-ligue-1", "https://dwh.lequipe.fr/api/edito/rss?path=/Football/Ligue-1/", "rss", "fr"),
    ("front-office-sports", "https://frontofficesports.com/feed/", "rss", "en"),
    ("the-guardian-film", "https://www.theguardian.com/uk/film/rss", "rss", "en"),
    ("new-york-times-books", "https://rss.nytimes.com/services/xml/rss/nyt/Books.xml", "rss", "en"),
    ("franceinfo-culture", "https://www.francetvinfo.fr/culture.rss", "rss", "fr"),
    ("numerama", "https://www.numerama.com/feed/", "rss", "fr"),
    ("phys-org", "https://phys.org/rss-feed/", "rss", "en"),
    ("sciences-et-avenir", "https://www.sciencesetavenir.fr/rss.xml", "rss", "fr"),
    ("nasa-actualites", "https://www.nasa.gov/feed/", "rss", "en"),
    ("our-world-in-data-data-insights", "https://ourworldindata.org/atom-data-insights.xml", "rss", "en"),
    ("pew-research-center", "https://www.pewresearch.org/feed/", "rss", "en"),
    ("wikimedia-analytics-api-articles-l", "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/fr.wikipedia/all-access/2026/08/07", "api", "fr"),
    ("bri-central-bankers-speeches", "https://www.bis.org/doclist/cbspeeches.rss", "rss", "en"),
    ("fmi-communiques-et-discours", "https://www.imf.org/en/News/RSS?language=eng", "rss", "en"),
    ("commission-europeenne-press-corner", "https://ec.europa.eu/commission/presscorner/api/rss?language=fr", "rss", "fr"),
    ("bce-discours-et-interventions", "https://www.ecb.europa.eu/rss/speeches.html", "rss", "en"),
    ("ocde-salle-de-presse", "https://www.oecd.org/newsroom/rss.xml", "rss", "en"),
    ("bercy-communiques-du-ministere-de-", "https://www.economie.gouv.fr/rss/presse", "rss", "fr"),
    ("maison-blanche-decrets-et-actions-", "https://www.whitehouse.gov/presidential-actions/feed/", "rss", "en"),
    ("the-straits-times-business-singapo", "https://www.straitstimes.com/news/business/rss.xml", "rss", "en"),
    ("the-economic-times-markets-inde", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "rss", "en"),
    ("moneycontrol-dernieres-actualites-", "https://www.moneycontrol.com/rss/latestnews.xml", "rss", "en"),
    ("mint-markets-inde", "https://www.livemint.com/rss/markets", "rss", "en"),
    ("china-daily-business-china", "https://www.chinadaily.com.cn/rss/bizchina_rss.xml", "rss", "en"),
    ("yonhap-news-economy-coree-du-sud", "https://en.yna.co.kr/RSS/economy.xml", "rss", "en"),
    ("the-japan-times-business", "https://www.japantimes.co.jp/news/business/feed/", "rss", "en"),
    ("reserve-bank-of-australia-communiq", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "rss", "en"),
    ("abc-news-australia-business", "https://www.abc.net.au/news/feed/51892/rss.xml", "rss", "en"),
    ("g1-economia-bresil", "https://g1.globo.com/rss/g1/economia/", "rss", "autre"),
    ("infomoney-bresil-marches", "https://www.infomoney.com.br/feed/", "rss", "autre"),
    ("agencia-brasil-economia-agence-pub", "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml", "rss", "autre"),
    ("infobae-flux-general-argentine-ame", "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml", "rss", "autre"),
    ("the-national-emirats-business", "https://www.thenationalnews.com/arc/outboundfeeds/rss/category/business/?outputType=xml", "rss", "en"),
    ("the-times-of-israel-flux-general", "https://www.timesofisrael.com/feed/", "rss", "en"),
    ("arab-news-flux-general-arabie-saou", "https://www.arabnews.com/rss.xml", "rss", "en"),
    ("agence-ecofin-economie-africaine-e", "https://www.agenceecofin.com/rss", "rss", "fr"),
    ("moneyweb-afrique-du-sud-marches", "https://www.moneyweb.co.za/feed/", "rss", "en"),
    ("businessday-nigeria", "https://businessday.ng/feed/", "rss", "en"),
    ("rfi-economie-francophone-internati", "https://www.rfi.fr/fr/economie/rss", "rss", "fr"),
    ("oilprice-com-flux-principal-energi", "https://oilprice.com/rss/main", "rss", "en"),
    ("mining-com-metaux-et-mines", "https://www.mining.com/feed/", "rss", "en"),
    ("usda-communiques-agriculture-wasde", "https://www.usda.gov/rss/latest-releases.xml", "rss", "en"),
    ("freightwaves-fret-et-logistique", "https://www.freightwaves.com/feed", "rss", "en"),
    ("gcaptain-transport-maritime", "https://gcaptain.com/feed/", "rss", "en"),
    ("the-loadstar-supply-chain-et-fret-", "https://theloadstar.com/feed/", "rss", "en"),
    ("supply-chain-dive", "https://www.supplychaindive.com/feeds/news/", "rss", "en"),
    ("banking-dive-banques-et-credit", "https://www.bankingdive.com/feeds/news/", "rss", "en"),
    ("utility-dive-electricite-et-energi", "https://www.utilitydive.com/feeds/news/", "rss", "en"),
    ("us-treasury-courbe-des-taux-quotid", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=2026", "api", "en"),
    ("treasurydirect-adjudications-annon", "https://www.treasurydirect.gov/TA_WS/securities/announced?format=json&days=7", "json", "en"),
    ("bce-data-portal-rendement-10-ans-z", "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?lastNObservations=1&format=csvdata", "api", "en"),
    ("freddie-mac-pmms-taux-hypothecaire", "https://www.freddiemac.com/pmms/docs/PMMS_history.csv", "api", "en"),
    ("coindesk-actualites-crypto", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml", "rss", "en"),
    ("cointelegraph-crypto-fort-volume", "https://cointelegraph.com/rss", "rss", "en"),
    ("coingecko-prix-crypto-api-publique", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur,usd&include_24hr_change=true", "api", "en"),
    ("journal-du-coin-crypto-en-francais", "https://journalducoin.com/feed/", "rss", "fr"),
    ("breaking-defense", "https://breakingdefense.com/feed/", "rss", "en"),
    ("defense-news", "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "rss", "en"),
    ("departement-de-la-guerre-ex-dod-co", "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=9", "rss", "en"),
    ("opex360-defense-en-francais", "https://www.opex360.com/feed/", "rss", "fr"),
    ("openverse-recherche-d-images-libre", "https://api.openverse.org/v1/images/?q=stock%20market&license=cc0,pdm&page_size=5", "api", "en"),
    ("wikimedia-commons-api-images-licen", "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=filetype%3Abitmap%20stock%20exchange&gsrlimit=5&prop=imageinfo&iiprop=url%7Cextmetadata&format=json", "api", "en"),
    ("wikipedia-fr-api-resume-et-vignett", "https://fr.wikipedia.org/api/rest_v1/page/summary/CAC_40", "api", "fr"),
    ("calendrier-economique-hebdomadaire", "https://nfs.faireconomy.media/ff_calendar_thisweek.json", "json", "en"),
    ("nasdaq-calendrier-des-resultats-du", "https://api.nasdaq.com/api/calendar/earnings?date=2026-08-07", "json", "en"),
    ("gdelt-doc-2-0-api-agregateur-mondi", "https://api.gdeltproject.org/api/v2/doc/doc?query=(bourse%20OR%20inflation%20OR%20%22banque%20centrale%22)%20sourcelang:french&mode=ArtList&maxrecords=75&format=json&timespan=24h", "json", "fr"),
    ("boursier-com-fil-de-depeches-march", "https://www.boursier.com/syndication/rss/news/", "rss", "fr"),
    ("insee-page-d-index-des-flux-rss-a-", "https://www.insee.fr/fr/information/2381941", "rss", "fr"),
]


# CE QU'ON NE PEUT PAS MESURER, ON LE DIT. Ces services d'actualité exigent une
# inscription et une clé que le dépôt n'a pas : les sonder rendrait un 401 qui
# ne dirait rien de leur qualité. Ils sont listés ici pour que la décision les
# ait sous les yeux — plusieurs ont un palier gratuit généreux, et c'est le
# genre d'arbitrage qui se perd s'il n'est écrit nulle part.
A_CLE_MANQUANTE = [
    ("Alpaca Market Data News API", "https://data.alpaca.markets/v1beta1/news"),
    ("Alpha Vantage NEWS_SENTIMENT", "https://www.alphavantage.co/query"),
    ("Currents API", "https://api.currentsapi.services/v1/latest-news"),
    ("EODHD Financial News API", "https://eodhd.com/api/news"),
    ("FMP", "https://financialmodelingprep.com/stable/news/general-latest"),
    ("FRED series", "https://api.stlouisfed.org/fred/series/observations"),
    ("FRED \u2014 calendrier des publications statistiques US", "https://api.stlouisfed.org/fred/releases/dates"),
    ("GNews.io", "https://gnews.io/api/v4/top-headlines"),
    ("Marketaux", "https://api.marketaux.com/v1/news/all"),
    ("NewsAPI.org", "https://newsapi.org/v2/top-headlines"),
    ("Polygon.io", "https://api.polygon.io/v2/reference/news"),
    ("StockData.org", "https://api.stockdata.org/v1/news/all"),
    ("The News API", "https://api.thenewsapi.com/v1/news/top"),
    ("Tiingo News API", "https://api.tiingo.com/tiingo/news"),
    ("newsdata.io", "https://newsdata.io/api/1/latest"),
]


# ── Lecture (pure : on donne les octets, elle rend le compte rendu) ──────────

def _texte(el):
    return (el.text or "").strip() if el is not None else ""


def lire_flux(octets, maintenant=None):
    """Compte rendu d'un flux RSS/Atom : combien d'articles, quelle fraîcheur.

    Pure et testable hors ligne : c'est elle qui décide si une source est
    exploitable, donc c'est elle qu'il faut pouvoir vérifier sans réseau.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    seuil = maintenant - timedelta(hours=24)
    try:
        racine = ElementTree.fromstring(octets)
    except ElementTree.ParseError as e:
        return {"lisible": False, "motif": f"XML illisible : {e.msg[:60]}"}

    ns = {"atom": "http://www.w3.org/2005/Atom",
          "media": "http://search.yahoo.com/mrss/",
          "content": "http://purl.org/rss/1.0/modules/content/",
          "dc": "http://purl.org/dc/elements/1.1/",
          "rss1": "http://purl.org/rss/1.0/"}
    # RSS 1.0 (RDF) met ses <item> dans un espace de noms : `.//item` ne les
    # voyait pas et toute cette famille de flux — encore utilisée par des sites
    # institutionnels — était comptée MORTE dans le rapport qui sert à décider.
    items = (racine.findall(".//item") or racine.findall(".//rss1:item", ns)
             or racine.findall(".//atom:entry", ns))
    if not items:
        return {"lisible": False, "motif": "aucun <item> ni <entry>"}

    recents = resumes = images = dates_lues = 0
    titres = []
    for it in items:
        titre = (_texte(it.find("title")) or _texte(it.find("rss1:title", ns))
                 or _texte(it.find("atom:title", ns)))
        if titre and len(titres) < 3:
            titres.append(titre[:90])
        desc = (_texte(it.find("description"))
                or _texte(it.find("rss1:description", ns))
                or _texte(it.find("atom:summary", ns))
                or _texte(it.find("content:encoded", ns)))
        # Un titre sans corps ne permet que de broder : c'est déjà la règle du
        # point du matin (`depeches_recentes` jette les dépêches sans résumé).
        if len(re.sub(r"<[^>]+>", "", desc).strip()) >= 80:
            resumes += 1
        if (it.find("enclosure") is not None
                or it.find("media:content", ns) is not None
                or it.find("media:thumbnail", ns) is not None
                or "<img" in desc):
            images += 1
        # <dc:date> est la façon dont datent RSS 1.0 et une partie des flux
        # institutionnels : sans elle, ils sortaient à recents_24h=0, donc
        # exclus du classement alors qu'ils publient tous les jours.
        brut = (_texte(it.find("pubDate")) or _texte(it.find("dc:date", ns))
                or _texte(it.find("atom:updated", ns))
                or _texte(it.find("atom:published", ns)))
        quand = _date(brut)
        if quand:
            dates_lues += 1
            if quand >= seuil:
                recents += 1
    return {"lisible": True, "articles": len(items), "recents_24h": recents,
            "dates_lues": dates_lues, "avec_resume": resumes,
            "avec_image": images, "titres": titres}


def _date(brut):
    """RFC 822 (RSS) ou ISO 8601 (Atom). None si illisible : une source qui ne
    date pas ses articles est inutilisable pour un point du MATIN, on veut
    pouvoir le voir dans le rapport plutôt que le deviner."""
    if not brut:
        return None
    try:
        d = parsedate_to_datetime(brut)
    except (TypeError, ValueError, IndexError):
        try:
            d = datetime.fromisoformat(brut.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def lire_json(octets, maintenant=None):
    """Compte rendu d'un endpoint JSON. Les formes varient (liste nue, objet à
    clé), on ne cherche donc pas un schéma : on compte des éléments et on
    regarde s'ils portent les trois choses qui comptent (titre, corps, date)."""
    maintenant = maintenant or datetime.now(timezone.utc)
    seuil = maintenant - timedelta(hours=24)
    try:
        d = json.loads(octets)
    except ValueError as e:
        return {"lisible": False, "motif": f"JSON illisible : {str(e)[:60]}"}
    if isinstance(d, dict):
        listes = [v for v in d.values() if isinstance(v, list) and v]
        d = max(listes, key=len) if listes else []
    if not isinstance(d, list) or not d:
        return {"lisible": False, "motif": "aucun élément"}

    CLES_T = ("headline", "title", "name", "symbol")
    CLES_C = ("summary", "description", "content")
    CLES_D = ("datetime", "date", "publishedDate", "time")
    recents = resumes = images = dates_lues = 0
    titres = []
    for a in d:
        if not isinstance(a, dict):
            continue
        t = next((str(a[k]) for k in CLES_T if a.get(k)), "")
        if t and len(titres) < 3:
            titres.append(t[:90])
        if len(str(next((a[k] for k in CLES_C if a.get(k)), ""))) >= 80:
            resumes += 1
        if a.get("image"):
            images += 1
        brut = next((a[k] for k in CLES_D if a.get(k)), None)
        quand = None
        if isinstance(brut, (int, float)) and brut > 1e8:
            # Certaines API datent en MILLISECONDES : passé tel quel,
            # fromtimestamp lève ValueError (année hors bornes) et emportait
            # tout le run. Au-delà de l'an 5000 en secondes, c'est des ms.
            try:
                quand = datetime.fromtimestamp(
                    brut / 1000.0 if brut > 1e11 else brut, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                quand = None
        elif isinstance(brut, str):
            quand = _date(brut)
        if quand:
            dates_lues += 1
            if quand >= seuil:
                recents += 1
    return {"lisible": True, "articles": len(d), "recents_24h": recents,
            "dates_lues": dates_lues, "avec_resume": resumes,
            "avec_image": images, "titres": titres}


# ── Sondage (impur : réseau) ────────────────────────────────────────────────

class _SansSecretHorsSite(urllib.request.HTTPRedirectHandler):
    """Redirection suivie, mais sans emporter l'en-tête d'authentification si
    l'hôte change. C'est la seule façon d'avoir les deux : mesurer les sources
    qui redirigent (elles sont nombreuses) sans offrir la clé au premier
    domaine venu."""

    def redirect_request(self, req, fp, code, msg, entetes, url):
        neuf = super().redirect_request(req, fp, code, msg, entetes, url)
        if neuf is not None and urllib.parse.urlsplit(url).netloc != req.host:
            for h in ("X-Finnhub-Token", "Authorization"):
                neuf.remove_header(h)
        return neuf


_OUVREUR = urllib.request.build_opener(_SansSecretHorsSite)


def sonder(cand, maintenant=None):
    nom, url, genre, langue = cand[:4]
    secret = cand[4] if len(cand) > 4 else None
    fiche = {"nom": nom, "url": url, "genre": genre, "langue": langue}
    if secret and not os.environ.get(secret):
        fiche.update(statut="sautee", motif=f"{secret} absent")
        return fiche

    jour = (maintenant or datetime.now(timezone.utc)).date()
    url = url.format(jour=jour, hier=jour - timedelta(days=3))
    entetes = {"User-Agent": UA, "Accept": "*/*"}
    if secret == "FINNHUB_API_KEY":
        entetes["X-Finnhub-Token"] = os.environ[secret]
    try:
        r = urllib.request.Request(url, headers=entetes)
        # UN SECRET NE FRANCHIT PAS UN CHANGEMENT D'HÔTE. urllib recopie les
        # en-têtes de la requête d'origine dans les redirections : une source
        # qui renvoyait vers un autre domaine recevait notre clé Finnhub en
        # clair. Elle est retirée dès que l'hôte change.
        with _OUVREUR.open(r, timeout=DELAI) as rep:
            code, octets = rep.status, rep.read()
    except urllib.error.HTTPError as e:
        fiche.update(statut="http", code=e.code, motif=e.reason)
        return fiche
    except Exception as e:                                     # noqa: BLE001
        fiche.update(statut="erreur", motif=f"{type(e).__name__}: {str(e)[:80]}")
        return fiche

    fiche["code"] = code
    fiche["octets"] = len(octets)
    # ON LIT CE QUI ARRIVE, PAS CE QU'ON AVAIT ÉTIQUETÉ. Quatre sources vivantes
    # étaient notées « illisibles » parce qu'elles rendent du XML ou du CSV sous
    # un genre déclaré « api ». Le rapport sert à DÉCIDER : une source rejetée
    # sur une erreur d'étiquette est une source qu'on n'aura pas.
    tete = octets.lstrip()[:1]
    json_probable = tete in (b"{", b"[")
    lecture = (lire_json(octets, maintenant)
               if (json_probable or (genre in ("api", "json") and tete != b"<"))
               else lire_flux(octets, maintenant))
    fiche.update(lecture)
    fiche["statut"] = "ok" if lecture.get("lisible") else "illisible"
    return fiche


def resume(fiches):
    """Le classement qui sert à décider : d'abord ce qui est frais et étoffé."""
    utiles = [f for f in fiches if f.get("statut") == "ok" and f.get("recents_24h")]
    utiles.sort(key=lambda f: (-f["recents_24h"], -f.get("avec_resume", 0)))
    return {
        "teste": len(fiches),
        "ok": sum(1 for f in fiches if f.get("statut") == "ok"),
        "sautees": sum(1 for f in fiches if f.get("statut") == "sautee"),
        "morts": sum(1 for f in fiches if f.get("statut") in ("http", "erreur")),
        "frais_24h": len(utiles),
        "articles_24h_cumules": sum(f["recents_24h"] for f in utiles),
        "meilleures": [f["nom"] for f in utiles[:15]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=SORTIE)
    ap.add_argument("--genre", default="", help="ne tester qu'un genre (rss, atom, api)")
    a = ap.parse_args()

    cands = [c for c in CANDIDATS if not a.genre or c[2] == a.genre]
    maintenant = datetime.now(timezone.utc)
    print(f"{len(cands)} candidats, {PARALLELE} en parallèle…\n")
    # Les résultats sont RÉORDONNÉS comme la liste : un rapport dont les lignes
    # arrivent dans l'ordre des latences réseau n'est pas relisible d'un run à
    # l'autre, et c'est un rapport fait pour être relu et comparé.
    def _sonder_sans_casse(c):
        """UNE SONDE QUI LÈVE NE DOIT PAS EMPORTER LES DEUX CENTS AUTRES.
        `ex.map` propage la première exception au moment de l'itération : un seul
        candidat exotique et le rapport n'était jamais écrit, après avoir pourtant
        mesuré tout le reste. Ici l'accident devient une fiche comme une autre."""
        try:
            return sonder(c, maintenant)
        except Exception as e:                             # noqa: BLE001
            return {"nom": c[0], "url": c[1], "genre": c[2], "langue": c[3],
                    "statut": "erreur", "motif": f"sonde : {type(e).__name__}: {str(e)[:80]}"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLELE) as ex:
        fiches = list(ex.map(_sonder_sans_casse, cands))
    for f in fiches:
        etat = f.get("statut")
        detail = (f"{f.get('recents_24h', 0)}/{f.get('articles', 0)} en 24 h, "
                  f"{f.get('avec_resume', 0)} résumés, {f.get('avec_image', 0)} images"
                  if etat == "ok" else f.get("motif") or f.get("code") or "")
        print(f"  {'✅' if etat == 'ok' else '·' if etat == 'sautee' else '❌'} "
              f"{f['nom']:<34} {detail}")

    r = resume(fiches)
    # UN RUN PARTIEL LE DIT DANS SON NOM. Sans ça, `--genre rss` écrivait
    # sonde_actus.json avec les seuls flux, le workflow le commitait, et le
    # rapport complet du run précédent disparaissait sans que personne ne le
    # voie — un rapport de mesure qui s'écrase lui-même vaut moins que rien.
    sortie = a.sortie
    if a.genre and sortie == SORTIE:
        sortie = SORTIE.replace(".json", f"_{a.genre}.json")
        print(f"   run filtré : rapport écrit dans {sortie}, "
              f"le rapport complet n'est pas touché")
    rapport = {"genere_le": maintenant.strftime("%Y-%m-%d %H:%M UTC"),
               "genre_filtre": a.genre or None,
               "resume": r, "sources": fiches,
               "a_cle_manquante": [{"nom": n, "url": u} for n, u in A_CLE_MANQUANTE]}
    json.dump(rapport, open(sortie, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{r['ok']}/{r['teste']} sources lisibles, {r['frais_24h']} avec du frais, "
          f"{r['articles_24h_cumules']} articles de moins de 24 h cumulés "
          f"({r['morts']} mortes, {r['sautees']} sautées faute de clé)")
    print("  meilleures : " + ", ".join(r["meilleures"]))
    print(f"  non testées faute de clé : {len(A_CLE_MANQUANTE)} services "
          "(voir A_CLE_MANQUANTE dans ce fichier)")
    print(f"→ {sortie}")
    # Aucune sortie en erreur : une source morte est une INFORMATION, pas une
    # panne de la sonde. Le rapport la note, le job reste vert, on décide après.
    return 0


if __name__ == "__main__":
    sys.exit(main())
