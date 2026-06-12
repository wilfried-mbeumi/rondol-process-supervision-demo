"""Tests — source de vérité opérateur CENTRALE persistante (operator_store).

Vérifie que les saisies survivent à : navigation multipage, changement de langue,
refresh (perte totale de session → reload disque). Tests end-to-end AppTest
inclus (Profile → Moteur via le store central).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from operator_store import (  # noqa: E402
    STORE_KEY, capture_operator_state, get_current_run_field,
    load_current_run_state, restore_operator_state, save_current_run_state,
    update_current_run_field,
)
from run_state_adapter import build, build_moteur_inputs_from_current_run_state  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402


# ---------------------------------------------------------------------------
# Couche store pure
# ---------------------------------------------------------------------------
def test_update_and_get_current_run_field():
    sess: dict = {}
    update_current_run_field(sess, "screw_rpm", 150.0)
    assert get_current_run_field(sess, "screw_rpm") == 150.0
    assert sess[STORE_KEY]["screw_rpm"] == 150.0


def test_capture_then_restore_after_session_loss():
    # Saisie + capture.
    sess = {"screw_rpm": 150.0, "bulk_density": 0.6,
            "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0}
    save_current_run_state(sess)
    # « Refresh » : session totalement neuve (perte des clés widget + store session).
    fresh: dict = {}
    restore_operator_state(fresh)             # recharge depuis le disque
    assert fresh["screw_rpm"] == 150.0
    assert fresh["feeder_calib_g_h_per_rpm"] == 10.0


def test_restore_never_overwrites_present_value():
    sess = {"screw_rpm": 150.0}
    save_current_run_state(sess)
    other = {"screw_rpm": 200.0}              # valeur déjà présente
    restore_operator_state(other)
    assert other["screw_rpm"] == 200.0        # NON écrasée


# ---------------------------------------------------------------------------
# Navigation Profile → Moteur via le store (clés widget perdues)
# ---------------------------------------------------------------------------
def _profile_session():
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    return {"screw_config": cfg, "screw_rpm": 100.0, "bulk_density": 0.55,
            "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0}


def test_profile_values_persist_after_navigation():
    sess = _profile_session()
    capture_operator_state(sess)              # fin de Profile
    # Navigation : Streamlit purge TOUTES les clés widget.
    for k in ("feeder_rpm", "feeder_calib_g_h_per_rpm", "screw_rpm", "bulk_density"):
        del sess[k]
    restore_operator_state(sess)              # tête de Moteur
    mi = build_moteur_inputs_from_current_run_state(build(sess))
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6     # 300 g/h
    assert mi["screw_rpm"] == 100.0
    assert mi["bulk_density"] == 0.55


def test_refresh_restores_current_run_state():
    sess = _profile_session()
    capture_operator_state(sess)
    fresh: dict = {}                          # refresh complet
    restore_operator_state(fresh)
    mi = build_moteur_inputs_from_current_run_state(build(fresh))
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6


def test_language_switch_preserves_current_run_state():
    sess = _profile_session()
    sess["ui_lang"] = "fr"
    capture_operator_state(sess)
    before = load_current_run_state(sess)
    sess["ui_lang"] = "en"
    capture_operator_state(sess)
    after = load_current_run_state(sess)
    assert before == after                    # langue n'affecte pas l'état métier


def test_settings_values_persist_after_navigation():
    sess = {"n_die_zones": 3, "target_screw_count": 25, "screw_rpm": 180.0,
            "bulk_density": 0.7}
    capture_operator_state(sess)
    for k in ("n_die_zones", "target_screw_count", "screw_rpm", "bulk_density"):
        del sess[k]
    restore_operator_state(sess)
    crs = build(sess)
    assert crs.process_parameters["n_die_zones"].value == 3
    assert crs.process_parameters["target_element_count"].value == 25
    assert crs.process_parameters["screw_rpm"].value == 180.0


# ---------------------------------------------------------------------------
# End-to-end AppTest : Profile écrit → Moteur (session neuve) lit via disque
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

PROFILE = str(APP / "pages" / "1_Profile.py")
MOTEUR = str(APP / "pages" / "5_Process_Engine.py")


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_to_moteur_via_central_store_end_to_end():
    # 1) Profile : saisie RPM 30 + coeff 10 → capture (session + disque).
    at = AppTest.from_file(PROFILE)
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]

    # 2) Moteur : SESSION TOTALEMENT NEUVE (refresh) → restore depuis le disque.
    at2 = AppTest.from_file(MOTEUR)
    at2.session_state["demo_mode"] = False
    at2.run(timeout=90)
    assert not at2.exception, [str(e.value) for e in at2.exception]
    metric_vals = [str(getattr(m, "value", "")) for m in at2.metric]
    # Le débit est calculable (les valeurs Profile ont survécu via le store).
    assert "Non calculable" not in metric_vals
