"""Tests P3.5 — barrière anti-legacy : aucune lecture métier brute hors adapter.

Principe :
  - pages CONSOMMATRICES (Supervision, Analyse_run, Historique, Moteur_Procede)
    NE lisent PAS les clés métier brutes de session_state : elles passent par
    current_run_state / run_state_adapter (opérateur) ou demo_ml_run (ML demo).
  - pages de SAISIE (Profile, Settings) possèdent leurs widgets : elles écrivent
    les clés (et lisent leurs propres widgets) — c'est la couche d'entrée, qui
    projette ensuite vers current_run_state (P3.2).
  - couche opérateur (current_run_state, run_state_adapter, rules, recommendations)
    n'importe NI le dataset ML NI history_store.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

# Pages consommatrices : interdiction de lecture métier brute.
CONSUMER_PAGES = {
    "Supervision": APP / "Supervision.py",
    "Analyse_run": APP / "pages" / "3_Analyse_run.py",
    "Historique": APP / "pages" / "4_Historique.py",
    "Moteur_Procede": APP / "pages" / "5_Moteur_Procede.py",
}
ALL_PAGES = {
    "/": APP / "Supervision.py",
    "/Profile": APP / "pages" / "1_Profile.py",
    "/Settings": APP / "pages" / "2_Settings.py",
    "/Analyse_run": APP / "pages" / "3_Analyse_run.py",
    "/Historique": APP / "pages" / "4_Historique.py",
    "/Moteur_Procede": APP / "pages" / "5_Moteur_Procede.py",
}

BUSINESS_KEYS = (
    "screw_rpm", "screw_config", "feeder_g_per_min", "feeder_rpm",
    "feeder_calib_g_h_per_rpm", "bulk_density", "side_feeder_zone", "n_die_zones",
)


def _business_read_violations(src: str) -> list[str]:
    """Retourne les lectures métier brutes (≠ écritures) trouvées dans `src`."""
    violations: list[str] = []
    for key in BUSINESS_KEYS:
        # .get("key"...) = toujours une lecture.
        if re.search(r'st\.session_state\.get\(\s*["\']' + re.escape(key) + r'["\']', src):
            violations.append(f'session_state.get("{key}")')
        # ["key"] : lecture si PAS suivi de « = » (écriture) — « == » reste lecture.
        for m in re.finditer(r'st\.session_state\[\s*["\']' + re.escape(key) + r'["\']\s*\]', src):
            after = src[m.end():m.end() + 4].lstrip()
            is_write = after.startswith("=") and not after.startswith("==")
            if not is_write:
                violations.append(f'session_state["{key}"] (lecture)')
    return violations


# ---------------------------------------------------------------------------
# Barrière : pages consommatrices sans lecture métier brute
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(CONSUMER_PAGES))
def test_no_raw_business_session_state_read_outside_adapter(name):
    src = CONSUMER_PAGES[name].read_text(encoding="utf-8")
    violations = _business_read_violations(src)
    assert not violations, f"{name} lit des clés métier brutes : {violations}"


def test_current_run_state_is_single_operator_source():
    # La couche opérateur ne dépend NI du dataset ML NI de l'historique.
    import AgentIndustrial_v1.core.current_run_state as crs_mod
    import run_state_adapter as adapter
    for mod in (crs_mod, adapter):
        src = inspect.getsource(mod)
        assert "dataset_ml" not in src
        assert "history_store" not in src
    # L'adapter expose bien la construction unique de l'état opérateur.
    assert hasattr(adapter, "build")
    assert hasattr(adapter, "build_moteur_inputs_from_current_run_state")


def test_demo_ml_run_is_only_demo_source():
    import demo_ml_run as dm
    src = inspect.getsource(dm)
    # demo_ml_run ne DÉPEND PAS de l'état opérateur (imports/usage, pas la prose).
    assert "import current_run_state" not in src
    assert "from AgentIndustrial_v1.core.current_run_state" not in src
    assert "build_current_run_state" not in src
    assert "build_moteur_inputs" not in src


def test_history_store_does_not_override_current_run_state():
    import AgentIndustrial_v1.core.current_run_state as crs_mod
    import run_state_adapter as adapter
    for mod in (crs_mod, adapter):
        assert "history_store" not in inspect.getsource(mod)
        assert "process_history" not in inspect.getsource(mod)


def test_no_page_reads_dataset_ml_as_operator_input():
    # La couche opérateur + recos ne référence jamais le dataset ML.
    import AgentIndustrial_v1.core.recommendations as reco
    import AgentIndustrial_v1.core.rules as rules
    import AgentIndustrial_v1.core.current_run_state as crs_mod
    import run_state_adapter as adapter
    for mod in (reco, rules, crs_mod, adapter):
        assert "dataset_ml" not in inspect.getsource(mod)


def test_no_page_reads_process_history_as_current_config():
    import AgentIndustrial_v1.core.current_run_state as crs_mod
    import run_state_adapter as adapter
    for mod in (crs_mod, adapter):
        assert "process_history" not in inspect.getsource(mod)


def test_legacy_projection_is_read_only_adapter():
    from AgentIndustrial_v1.core.applied_state import commit
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from run_state_adapter import build, sync_legacy_projection
    from screw_logic import add_elements_atomic, new_empty_configuration

    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    sess = {"screw_config": cfg, "screw_rpm": 150.0, "bulk_density": 0.60,
            "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0}
    commit(sess, state_from_session(sess), label="t")
    crs = sync_legacy_projection(sess)             # canonical -> legacy (sens unique)
    assert sess["screw_rpm"] == crs.process_parameters["screw_rpm"].value
    # Reprojection idempotente : pas de dérive (lecture seule compatible).
    assert build(sess) == crs


# ---------------------------------------------------------------------------
# Import / compile / rendu de toutes les pages
# ---------------------------------------------------------------------------
def test_all_streamlit_pages_import():
    import py_compile
    for path in ALL_PAGES.values():
        py_compile.compile(str(path), doraise=True)


try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("route", list(ALL_PAGES))
def test_all_pages_after_language_switch(route):
    p = ALL_PAGES[route]
    for lang in ("fr", "en"):
        at = AppTest.from_file(str(p))
        at.session_state["ui_lang"] = lang
        at.run(timeout=90)
        assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_streamlit_headless_starts():
    at = AppTest.from_file(str(ALL_PAGES["/"])).run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
