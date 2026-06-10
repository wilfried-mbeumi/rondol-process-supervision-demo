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
# Idem pour le store opérateur persistant (operator_store) — isolation disque.
_RUN_STATE_PATH_ENV = "RONDOL_RUN_STATE_PATH"

# Redirection AU PLUS TÔT (import du conftest = avant toute collecte/import de
# page), pour couvrir même les modules qui liraient le chemin à l'import.
_ISOLATED_DIR = Path(tempfile.mkdtemp(prefix="rondol_hist_tests_"))
_ISOLATED_PATH = _ISOLATED_DIR / "process_history.json"
_PREVIOUS_ENV = os.environ.get(_HISTORY_PATH_ENV)
os.environ[_HISTORY_PATH_ENV] = str(_ISOLATED_PATH)

# Store opérateur : chemin disque isolé en test (jamais le fichier de prod).
_RUN_STATE_PATH = _ISOLATED_DIR / "current_run_state.json"
_PREVIOUS_RUN_STATE_ENV = os.environ.get(_RUN_STATE_PATH_ENV)
os.environ[_RUN_STATE_PATH_ENV] = str(_RUN_STATE_PATH)

# Miroir disque du snapshot validé (applied_state) — même isolation.
_APPLIED_PATH_ENV = "RONDOL_APPLIED_STATE_PATH"
_APPLIED_PATH = _ISOLATED_DIR / "applied_state.json"
_PREVIOUS_APPLIED_ENV = os.environ.get(_APPLIED_PATH_ENV)
os.environ[_APPLIED_PATH_ENV] = str(_APPLIED_PATH)


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
    assert os.environ.get(_RUN_STATE_PATH_ENV) == str(_RUN_STATE_PATH), (
        "L'isolation du store opérateur n'est pas active."
    )
    yield
    # Restauration propre de l'environnement après la session de tests.
    if _PREVIOUS_ENV is None:
        os.environ.pop(_HISTORY_PATH_ENV, None)
    else:
        os.environ[_HISTORY_PATH_ENV] = _PREVIOUS_ENV
    if _PREVIOUS_RUN_STATE_ENV is None:
        os.environ.pop(_RUN_STATE_PATH_ENV, None)
    else:
        os.environ[_RUN_STATE_PATH_ENV] = _PREVIOUS_RUN_STATE_ENV
    if _PREVIOUS_APPLIED_ENV is None:
        os.environ.pop(_APPLIED_PATH_ENV, None)
    else:
        os.environ[_APPLIED_PATH_ENV] = _PREVIOUS_APPLIED_ENV


@pytest.fixture(autouse=True)
def _clear_run_state_file():
    """Vide le store opérateur disque AVANT chaque test (isolation inter-tests).

    La persistance INTRA-test (Profile écrit → Moteur lit) reste valable ;
    seul le report d'un test à l'autre est empêché.
    """
    try:
        if _RUN_STATE_PATH.exists():
            _RUN_STATE_PATH.unlink()
    except Exception:
        pass
    try:
        if _APPLIED_PATH.exists():
            _APPLIED_PATH.unlink()
    except Exception:
        pass
    yield
