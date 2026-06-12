"""Tests — aucune alerte ne cite une chimie absente (cathode/Li/liant) quand
aucune matière n'est saisie. Les alertes restent en langage procédé générique ;
la matière saisie (USER_INPUT, via le label feeder) peut apparaître.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from AgentIndustrial_v1.core.process import ProcessState, ScrewKPIs  # noqa: E402
from AgentIndustrial_v1.core.feeders import new_feeder_bank  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402

# Termes chimie interdits SANS matière saisie.
_CHEM = ("cathode", "lithium", "cnt", "nanotube")
_CHEM_WORD = re.compile(r"\bliant\b", re.IGNORECASE)
_LI_WORD = re.compile(r"\bLi\b")


def _alert_blob(state: ProcessState) -> str:
    rep = evaluate(state)
    return " ".join(f"{a.title} {a.description} {a.evidence}" for a in rep.alerts)


def _harsh_state() -> ProcessState:
    """État qui déclenche de nombreuses alertes thermiques/SME (sans matière saisie).

    Feeders par défaut (label « Main », famille générique) ; profil thermique
    agressif + SME élevé + RT long pour activer cooling / RT / SME / thermal.
    """
    state = ProcessState(screw_config=[1, 101] * 5, screw_rpm=250.0)
    state.feeders = new_feeder_bank()           # aucun polymer_name saisi
    # Profil thermique très chaud (déclenche overheat / incompat / RT).
    for z in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"):
        state.zone_temps_C[z] = 300.0
    state.kpis = ScrewKPIs(fill_factor=0.7, residence_time_s=200.0,
                           sme_kwh_per_kg=0.9, free_volume_cm3=20.0, n_elements=10)
    return state


# ---------------------------------------------------------------------------
# Sans matière : aucune chimie citée, mais alertes génériques présentes
# ---------------------------------------------------------------------------
def test_no_cathode_alert_without_material():
    assert "cathode" not in _alert_blob(_harsh_state()).lower()


def test_no_li_alert_without_material():
    blob = _alert_blob(_harsh_state())
    assert not _LI_WORD.search(blob), "« Li » cité sans matière saisie"
    assert "lithium" not in blob.lower()


def test_no_binder_alert_without_binder_input():
    assert not _CHEM_WORD.search(_alert_blob(_harsh_state()))


def test_no_chemistry_wording_without_material_context():
    blob = _alert_blob(_harsh_state()).lower()
    for term in _CHEM:
        assert term not in blob, f"chimie « {term} » citée sans matière saisie"


def test_generic_process_alert_still_displayed_without_material():
    rep = evaluate(_harsh_state())
    assert len(rep.alerts) > 0
    blob = _alert_blob(_harsh_state()).lower()
    assert ("matière" in blob or "thermique" in blob or "sme" in blob
            or "material" in blob or "thermal" in blob)


# ---------------------------------------------------------------------------
# Avec matière saisie (USER_INPUT via label feeder) : citation autorisée
# ---------------------------------------------------------------------------
def test_material_specific_alert_allowed_when_material_user_input():
    state = _harsh_state()
    # L'opérateur a saisi une matière sur le feeder principal (label).
    state.feeders[0].label = "PVDF-LFP"
    blob = _alert_blob(state)
    # Une alerte feeder cite la matière SAISIE (via display_name/label).
    assert "PVDF-LFP" in blob


def test_recommendations_do_not_cite_absent_material():
    from AgentIndustrial_v1.core.recommendations import build_recommendations
    state = _harsh_state()
    rep = evaluate(state)
    recos = build_recommendations(state, rep.alerts)
    blob = " ".join(f"{r.title} {r.rationale} {r.action}" for r in recos).lower()
    for term in _CHEM:
        assert term not in blob, f"reco cite une chimie absente : {term}"


def test_demo_ml_does_not_inject_material_alerts():
    # Les alertes ne dépendent QUE de ProcessState (jamais du dataset ML).
    import inspect
    import AgentIndustrial_v1.core.rules as rules
    src = inspect.getsource(rules)
    assert "dataset_ml" not in src and "stability_score" not in src


# ---------------------------------------------------------------------------
# Rendu réel (AppTest) — Supervision + Moteur Procédé sans chimie en client
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402


def _blob(at) -> str:
    chunks = []
    for kind in ("markdown", "caption", "info", "warning", "error"):
        try:
            chunks += [str(getattr(e, "value", "")) for e in getattr(at, kind)]
        except Exception:
            pass
    try:
        chunks += [str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html")]
    except Exception:
        pass
    return "\n".join(chunks)


def _assert_no_chem(blob: str):
    low = blob.lower()
    for term in _CHEM:
        assert term not in low, f"chimie « {term} » affichée en mode client"
    assert not _CHEM_WORD.search(blob), "« liant » affiché en mode client"
    assert not _LI_WORD.search(blob), "« Li » affiché en mode client"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_no_cathode_li_without_material():
    at = AppTest.from_file(str(APP / "Supervision.py"))
    at.session_state["demo_mode"] = False
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    _assert_no_chem(_blob(at))


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_no_cathode_li_without_material():
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    at = AppTest.from_file(str(APP / "pages" / "5_Process_Engine.py"))
    at.session_state["screw_config"] = cfg
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.session_state["demo_mode"] = False
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    _assert_no_chem(_blob(at))
