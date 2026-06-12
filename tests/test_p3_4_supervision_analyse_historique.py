"""Tests P3.4 — Supervision / Analyse_run / Historique : séparation stricte
current_run_state (opérateur) vs demo_ml_run (dataset ML de démonstration).
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

from run_state_adapter import build, build_moteur_inputs_from_current_run_state  # noqa: E402
from demo_ml_run import DEMO_ML_METRIC_COLUMNS, is_demo_ml_metric  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402

PAGES = {
    "/": APP / "Supervision.py",
    "/Profile": APP / "pages" / "1_Profile.py",
    "/Settings": APP / "pages" / "2_Settings.py",
    "/Analyse_run": APP / "pages" / "3_Run_Analysis.py",
    "/Historique": APP / "pages" / "4_History.py",
    "/Moteur_Procede": APP / "pages" / "5_Process_Engine.py",
}

SUP = APP / "Supervision.py"
ANALYSE = APP / "pages" / "3_Run_Analysis.py"
HISTO = APP / "pages" / "4_History.py"


def _op_session(**extra):
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 39)
    sess = {"screw_config": cfg, "screw_rpm": 100.0, "bulk_density": 0.55,
            "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0}
    sess.update(extra)
    return sess


# ---------------------------------------------------------------------------
# Séparation demo_ml_run ⟂ current_run_state
# ---------------------------------------------------------------------------
def test_supervision_uses_current_run_state_for_operator_config():
    # La page source construit current_run_state pour la config opérateur.
    src = SUP.read_text(encoding="utf-8")
    assert "build_moteur_inputs_from_current_run_state" in src
    # et n'utilise plus les lectures legacy plates pour la config opérateur.
    for pat in (r'float\(\s*st\.session_state\[\s*["\']screw_rpm["\']',
                r'float\(\s*st\.session_state\[\s*["\']feeder_g_per_min["\']',
                r'float\(\s*st\.session_state\[\s*["\']bulk_density["\']'):
        assert not re.search(pat, src), f"lecture legacy directe restante: {pat}"


def test_demo_ml_run_does_not_override_current_run_state():
    # Une session qui contiendrait des métriques ML ne les fait pas entrer dans crs.
    sess = _op_session(stability_score=99.0, run_duration_min=26.5, proba_stable=0.9)
    crs = build(sess)
    for ml in DEMO_ML_METRIC_COLUMNS:
        assert ml not in crs.calculated_outputs
        assert not hasattr(crs, ml)
    # La config opérateur reste intacte.
    assert build_moteur_inputs_from_current_run_state(crs)["screw_rpm"] == 100.0


def test_recommendations_do_not_use_demo_ml_as_real_input():
    # Le moteur de recommandations ne lit JAMAIS le dataset ML.
    import AgentIndustrial_v1.core.recommendations as reco
    import AgentIndustrial_v1.core.rules as rules
    for mod in (reco, rules):
        src = inspect.getsource(mod)
        assert "dataset_ml" not in src
        assert "stability_score" not in src
        assert "run_duration_min" not in src


def test_is_demo_ml_metric():
    assert is_demo_ml_metric("stability_score") is True
    assert is_demo_ml_metric("run_duration_min") is True
    assert is_demo_ml_metric("screw_rpm") is False


# ---------------------------------------------------------------------------
# Garde statique import / compile de toutes les pages
# ---------------------------------------------------------------------------
def test_all_streamlit_pages_import():
    import py_compile
    for path in PAGES.values():
        py_compile.compile(str(path), doraise=True)


# ---------------------------------------------------------------------------
# Rendu réel (AppTest)
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False


def _run(path, lang="fr"):
    at = AppTest.from_file(str(path))
    at.session_state["ui_lang"] = lang
    return at.run(timeout=90)


def _blob(at) -> str:
    chunks = []
    for kind in ("markdown", "caption", "info", "warning"):
        try:
            chunks += [str(getattr(e, "value", "")) for e in getattr(at, kind)]
        except Exception:
            pass
    try:
        chunks += [str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html")]
    except Exception:
        pass
    return "\n".join(chunks)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_demo_ml_is_marked_demo():
    at = _run(SUP)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = _blob(at)
    assert "DEMO" in blob and "dataset ML" in blob


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_does_not_present_ml_run_as_operator_truth():
    at = _run(SUP)
    blob = _blob(at)
    # Le bandeau marque les indicateurs ML comme non représentatifs d'un run live.
    assert "run opérateur live" in blob


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_analyse_run_demo_metrics_are_marked_demo():
    at = _run(ANALYSE)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = _blob(at)
    assert "DEMO" in blob and "dataset ML" in blob


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_historique_separates_process_history_and_ml_trials():
    at = _run(HISTO)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = _blob(at)
    assert "DEMO" in blob                       # section ML badgée
    assert "historique procédé" in blob.lower() or "procédé" in blob.lower()


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("route", list(PAGES))
def test_all_pages_after_language_switch(route):
    # Chargement FR puis EN (neufs) — aucune page ne crash au changement de langue.
    p = PAGES[route]
    at_fr = _run(p, "fr")
    assert not at_fr.exception, [str(e.value) for e in at_fr.exception]
    at_en = _run(p, "en")
    assert not at_en.exception, [str(e.value) for e in at_en.exception]


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_streamlit_headless_starts():
    # Proxy contrôlable d'un démarrage headless : la page d'accueil se rend
    # sans exception via le moteur d'exécution réel de Streamlit (AppTest).
    at = _run(SUP)
    assert not at.exception, [str(e.value) for e in at.exception]
