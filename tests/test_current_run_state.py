"""Tests P3.1 — couche current_run_state (pure, additive, provenance par champ)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core.applied_state import commit  # noqa: E402
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
from AgentIndustrial_v1.core.current_run_state import (  # noqa: E402
    CALCULATED,
    CALCULATED_CONFIRMED,
    CALCULATED_WITH_ASSUMPTIONS,
    DEMO_DATA,
    Field,
    NOT_AVAILABLE,
    SOURCE_TYPES,
    USER_INPUT,
    build_current_run_state,
    calculated_values_have_provenance,
    get_field,
    has_feeder_calibration,
    has_material,
    is_demo_state,
)

_DIM_OUTPUTS = ("fill_factor", "residence_time", "free_volume", "sme")


def _session_with_snapshot(**extra):
    """Session avec un snapshot validé (état USER_INPUT) + clés optionnelles."""
    sess: dict = {}
    state = state_from_session(sess)
    commit(sess, state, label="test")
    sess.update(extra)
    return sess


# ---------------------------------------------------------------------------
# Création / provenance
# ---------------------------------------------------------------------------
def test_current_run_state_created_from_user_input():
    crs = build_current_run_state(_session_with_snapshot())
    assert crs.source_type == USER_INPUT
    assert crs.run_id.source == USER_INPUT
    assert crs.screw_profile.source in (USER_INPUT,)  # snapshot présent


def test_current_run_state_tracks_provenance_per_field():
    crs = build_current_run_state(_session_with_snapshot())
    fields = [crs.run_id, crs.screw_profile, crs.feeder_calibration,
              crs.feed_rate, crs.material_context]
    fields += list(crs.process_parameters.values())
    fields += list(crs.calculated_outputs.values())
    for f in fields:
        assert isinstance(f, Field)
        assert f.source in SOURCE_TYPES, f
        assert f.validation_status, f          # statut toujours renseigné


def test_missing_field_is_not_available():
    # Session vide : ni étalonnage, ni matière → NOT_AVAILABLE (jamais inventé).
    crs = build_current_run_state({})
    assert crs.feeder_calibration.source == NOT_AVAILABLE
    assert crs.feed_rate.source == NOT_AVAILABLE
    assert crs.material_context.source == NOT_AVAILABLE
    assert get_field(crs, "feed_rate").source == NOT_AVAILABLE
    assert has_material(crs) is False
    assert has_feeder_calibration(crs) is False


def test_calculated_values_have_source_and_units():
    crs = build_current_run_state(_session_with_snapshot())
    assert calculated_values_have_provenance(crs) is True
    for key in _DIM_OUTPUTS:
        f = crs.calculated_outputs[key]
        assert f.source == CALCULATED
        assert f.unit != "", key            # grandeurs dimensionnelles ont une unité
        assert f.validation_status


# ---------------------------------------------------------------------------
# Séparation demo / hypothèses
# ---------------------------------------------------------------------------
def test_demo_ml_run_is_separate_object_from_current_run_state():
    crs = build_current_run_state(_session_with_snapshot())
    # Aucune métrique du dataset ML ne doit figurer dans current_run_state.
    assert set(crs.calculated_outputs) == {
        "fill_factor", "residence_time", "free_volume", "sme", "n_elements"}
    for ml in ("stability_score", "proba_stable", "run_duration_min", "is_stable"):
        assert ml not in crs.calculated_outputs
        assert not hasattr(crs, ml)


def test_field_status_never_confirmed_when_db_unconfirmed():
    crs = build_current_run_state(_session_with_snapshot())
    ff = crs.calculated_outputs["fill_factor"]
    assert ff.validation_status == CALCULATED_WITH_ASSUMPTIONS
    assert ff.validation_status != CALCULATED_CONFIRMED
    assert crs.validation_status != CALCULATED_CONFIRMED


def test_no_demo_data_in_client_current_run_state():
    crs = build_current_run_state(_session_with_snapshot())  # demo_mode absent → client
    assert is_demo_state(crs) is False
    all_fields = [crs.run_id, crs.screw_profile, crs.feeder_calibration,
                  crs.feed_rate, crs.material_context]
    all_fields += list(crs.process_parameters.values())
    all_fields += list(crs.calculated_outputs.values())
    for f in all_fields:
        assert f.source != DEMO_DATA


# ---------------------------------------------------------------------------
# Pureté : pas de mutation, idempotence
# ---------------------------------------------------------------------------
def test_current_run_state_does_not_mutate_session_state():
    sess = _session_with_snapshot(feeder_rpm=30.0, feeder_calib_g_h_per_rpm=10.0)
    before = dict(sess)
    build_current_run_state(sess)
    assert dict(sess) == before            # aucune clé ajoutée/modifiée


def test_current_run_state_builder_is_idempotent():
    sess = _session_with_snapshot(feeder_rpm=30.0, feeder_calib_g_h_per_rpm=10.0)
    a = build_current_run_state(sess)
    b = build_current_run_state(sess)
    assert a == b


# ---------------------------------------------------------------------------
# Étalonnage feeder : provenance préservée
# ---------------------------------------------------------------------------
def test_current_run_state_preserves_feeder_calibration_provenance():
    sess = _session_with_snapshot(feeder_rpm=30.0, feeder_calib_g_h_per_rpm=10.0)
    crs = build_current_run_state(sess)
    assert has_feeder_calibration(crs) is True
    assert crs.feeder_calibration.source == USER_INPUT
    ff = crs.feeder_calibration.value
    assert ff.calibrated is True
    assert abs(ff.effective_g_h - 300.0) < 1e-6
    # feed_rate dérivé = 300 g/h, CALCULATED (avec hypothèses, jamais confirmé).
    assert crs.feed_rate.source == CALCULATED
    assert abs(crs.feed_rate.value - 300.0) < 1e-6
    assert crs.feed_rate.validation_status == CALCULATED_WITH_ASSUMPTIONS
