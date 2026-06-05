"""conftest.py — isolation du stockage d'historique procédé pendant les tests.

But UNIQUE : empêcher que la suite de tests (e2e Settings / pages Streamlit /
tout test exerçant le vrai commit « Enregistrer ») n'écrive dans le fichier de
PRODUCTION `data/history/process_history.json`.

Mécanisme : `app/history_store.py` résout son chemin via la variable
d'environnement `RONDOL_HISTORY_PATH` (lue dynamiquement) avant de retomber sur
le chemin par défaut. On positionne donc cette variable, AVANT toute collecte de
test, vers un fichier temporaire pytest. Hors pytest, la variable n'est pas
définie → l'application réelle continue d'utiliser `data/history/process_history.json`.

Ce fichier ne touche AUCUNE logique applicative : il ne fait que rediriger un
chemin d'écriture le temps des tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Nom de la variable d'environnement d'override (contrat public de history_store).
_HISTORY_PATH_ENV = "RONDOL_HISTORY_PATH"

# Redirection AU PLUS TÔT (import du conftest = avant toute collecte/import de
# page), pour couvrir même les modules qui liraient le chemin à l'import.
_ISOLATED_DIR = Path(tempfile.mkdtemp(prefix="rondol_hist_tests_"))
_ISOLATED_PATH = _ISOLATED_DIR / "process_history.json"
_PREVIOUS_ENV = os.environ.get(_HISTORY_PATH_ENV)
os.environ[_HISTORY_PATH_ENV] = str(_ISOLATED_PATH)


@pytest.fixture(scope="session", autouse=True)
def _isolate_history_store():
    """Garantit l'isolation pendant toute la session, restaure l'env ensuite.

    Garde-fou : on vérifie que la redirection est bien active (sinon on échoue
    explicitement plutôt que de risquer de polluer la production).
    """
    assert os.environ.get(_HISTORY_PATH_ENV) == str(_ISOLATED_PATH), (
        "L'isolation de l'historique procédé n'est pas active — "
        "les tests pourraient écrire dans le fichier de production."
    )
    yield
    # Restauration propre de l'environnement après la session de tests.
    if _PREVIOUS_ENV is None:
        os.environ.pop(_HISTORY_PATH_ENV, None)
    else:
        os.environ[_HISTORY_PATH_ENV] = _PREVIOUS_ENV
