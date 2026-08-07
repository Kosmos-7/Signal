"""Bouchons des modules lourds, partagés par toutes les suites.

POURQUOI CE FICHIER EXISTE. La liste vivait en double, recopiée dans
test_charts.py et test_themes.py, et aucune des deux n'était l'originale.
`numpy` manquait aux deux : sur une machine de développement où il est
installé, les suites passaient quand même — c'est l'environnement qui
comblait le trou, pas le bouchon. Le premier run du workflow de tests, sur un
runner propre, a fait tomber test_themes.py à l'import. Une liste recopiée
n'est pas une liste : c'est deux listes qui divergent.

Les suites testent des fonctions PURES (parsing, ratios, projections, tri).
Aucune ne fait tourner de régression ni de RSI, donc aucun bouchon n'a besoin
d'être fidèle — il doit seulement permettre à `import screener` d'aboutir.
Le jour où une suite éprouverait un calcul réel, elle installerait la vraie
bibliothèque plutôt que d'enrichir un faux.

`setdefault` et non `[...] =` : quand la vraie bibliothèque est présente, elle
gagne. Le bouchon n'est qu'un filet.
"""
import sys
import types

# (nom du module, attributs minimaux que le code importé va chercher)
BOUCHONS = [
    ("ta", {}),
    ("ta.momentum", {"RSIIndicator": object}),
    ("numpy", {"nan": float("nan")}),
    ("yfinance", {"Ticker": object}),
    ("requests", {"get": lambda *a, **k: None}),
    ("pandas", {"Series": object, "DataFrame": object}),
]


def poser():
    """Installe les bouchons manquants. Idempotent."""
    for nom, attrs in BOUCHONS:
        m = types.ModuleType(nom)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules.setdefault(nom, m)
    # `import ta.momentum` ne suffit pas : le code fait `from ta.momentum
    # import ...`, ce qui exige que le sous-module soit accroché au parent.
    sys.modules["ta"].momentum = sys.modules["ta.momentum"]
