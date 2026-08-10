"""Reproduit l'environnement du runner : aucune bibliothèque tierce installée.

POURQUOI CE FICHIER EXISTE. Le workflow de tests n'installe RIEN, délibérément :
« installer les vraies dépendances masquerait au contraire une importation
oubliée ». La machine de développement, elle, les a toutes — et pendant des
jours les six suites ont affiché 100 % en local pendant que l'intégration
continue échouait en huit secondes, sur `ModuleNotFoundError: No module named
'PIL'`. Les mails d'échec sont partis à chaque commit, j'ai diagnostiqué depuis
mes résultats locaux au lieu de lire le journal du runner, et j'ai annoncé au
propriétaire que c'était réglé. Ça ne l'était pas.

S'EN SERVIR AVANT DE CROIRE UN « TOUT EST VERT » :

    PYTHONPATH=tests python3 tests/test_themes.py

Placé sur le PYTHONPATH, ce module est chargé automatiquement par Python
(mécanisme `sitecustomize`) et rend introuvables les bibliothèques que le runner
n'a pas. Une suite qui passe ainsi passera en intégration continue ; une suite
qui n'y passe pas ne prouve rien, quoi qu'elle affiche ailleurs.
"""
import sys

# Les six de requirements.txt, plus Pillow que les workflows photo installent à
# la volée et que les suites atteignent en important un module de tools/.
BLOQUEES = {"PIL", "pandas", "numpy", "yfinance", "ta", "requests", "anthropic"}


class _Interdit:
    def find_module(self, nom, chemin=None):
        return self if nom.split(".")[0] in BLOQUEES else None

    def load_module(self, nom):
        raise ImportError(f"No module named '{nom}' — bloqué : simulation du runner")


sys.meta_path.insert(0, _Interdit())
