"""Tests P3.2 — Profile + Settings alimentent current_run_state proprement.

Couche pure (builder + adapter) + rendu réel (AppTest). Aucune autre page testée.
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

from AgentIndustrial_v1.core.applied_state import commit  # noqa: E402
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
from AgentIndustrial_v1.core.current_run_state import (  # noqa: E402
    CALCULATED, DEFAULT_CONFIG, DEMO_DATA, NOT_AVAILABLE, USER_INPUT,
)
from run_state_adapter import build, project_to_legacy, sync_legacy_projection  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402


def _profile_session(**extra):
    """Session telle que Profile l'écrit (widgets) : profil + rpm + étalonnage."""
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)
    sess = {
        "screw_config": cfg,
        "screw_rpm": 150.0,            # ≠ défaut 120 → USER_INPUT
        "bulk_density": 0.60,          # ≠ défaut 0.55 → USER_INPUT
        "feeder_rpm": 30.0,
        "feeder_calib_g_h_per_rpm": 10.0,
    }
    sess.update(extra)
    return sess


def _settings_committed_session(**extra):
    sess = _profile_session(**extra)
    state = state_from_session(sess)
    commit(sess, state, label="t")
    return sess


# ---------------------------------------------------------------------------
# Saisie → current_run_state (USER_INPUT)
# ---------------------------------------------------------------------------
def test_profile_writes_user_input_to_current_run_state():
    crs = build(_profile_session())
    assert crs.source_type == USER_INPUT
    assert crs.screw_profile.source == USER_INPUT
    assert crs.process_parameters["screw_rpm"].source == USER_INPUT
    assert crs.process_parameters["bulk_density"].source == USER_INPUT
    assert crs.feeder_calibration.source == USER_INPUT


def test_settings_writes_user_input_to_current_run_state():
    crs = build(_settings_committed_session())
    assert crs.source_type == USER_INPUT
    assert crs.run_id.source == USER_INPUT             # snapshot validé
    assert crs.process_parameters["screw_rpm"].value == 150.0
    assert crs.process_parameters["screw_rpm"].source == USER_INPUT


def test_profile_and_settings_share_same_current_run_state():
    sess = _profile_session()
    crs_profile = build(sess)
    # Settings valide le même état → snapshot.
    commit(sess, state_from_session(sess), label="t")
    crs_settings = build(sess)
    # Mêmes valeurs métier des deux côtés (run_id/source peuvent différer).
    assert crs_profile.process_parameters["screw_rpm"].value == \
        crs_settings.process_parameters["screw_rpm"].value == 150.0
    assert crs_profile.screw_profile.value == crs_settings.screw_profile.value
    assert crs_profile.feeder_calibration.value.effective_g_h == \
        crs_settings.feeder_calibration.value.effective_g_h


# ---------------------------------------------------------------------------
# Langue : aucun impact sur l'état métier
# ---------------------------------------------------------------------------
def test_language_switch_preserves_current_run_state():
    sess = _settings_committed_session(ui_lang="fr")
    a = build(sess)
    sess["ui_lang"] = "en"
    b = build(sess)
    sess["ui_lang"] = "fr"
    c = build(sess)
    assert a == b == c


def test_language_switch_does_not_mutate_business_values():
    sess = _settings_committed_session(ui_lang="fr")
    before = {k: f.value for k, f in build(sess).process_parameters.items()}
    sess["ui_lang"] = "en"
    after = {k: f.value for k, f in build(sess).process_parameters.items()}
    assert before == after


# ---------------------------------------------------------------------------
# Projection legacy : sens unique, lecture-seule compatible
# ---------------------------------------------------------------------------
def test_legacy_projection_is_read_only_compatible():
    sess = _settings_committed_session()
    crs = sync_legacy_projection(sess)
    assert sess["screw_rpm"] == crs.process_parameters["screw_rpm"].value == 150.0
    assert sess["bulk_density"] == crs.process_parameters["bulk_density"].value
    # Débit legacy = débit effectif étalonné (300 g/h → 5 g/min).
    assert abs(sess["feeder_g_per_min"] - 5.0) < 1e-6
    # Stable : reprojection idempotente (pas de dérive).
    crs2 = build(sess)
    assert crs2 == crs


# ---------------------------------------------------------------------------
# Étalonnage feeder
# ---------------------------------------------------------------------------
def test_missing_feeder_coefficient_is_not_available():
    sess = _profile_session(feeder_calib_g_h_per_rpm=0.0)
    crs = build(sess)
    assert crs.feeder_calibration.source == NOT_AVAILABLE
    assert crs.feed_rate.source == NOT_AVAILABLE


def test_feeder_calibration_has_user_input_provenance():
    crs = build(_profile_session())
    assert crs.feeder_calibration.source == USER_INPUT
    assert crs.feed_rate.source == CALCULATED
    assert abs(crs.feed_rate.value - 300.0) < 1e-6


# ---------------------------------------------------------------------------
# Défaut éléments / n_die_zones / demo / labels
# ---------------------------------------------------------------------------
def test_default_element_count_is_40():
    crs = build(_profile_session())          # target_screw_count absent → défaut
    tgt = crs.process_parameters["target_element_count"]
    assert tgt.value == 40
    assert tgt.source == DEFAULT_CONFIG
    # L'opérateur choisit 25 → USER_INPUT, valeur respectée.
    crs25 = build(_profile_session(target_screw_count=25))
    assert crs25.process_parameters["target_element_count"].value == 25
    assert crs25.process_parameters["target_element_count"].source == USER_INPUT


def test_n_die_zones_remains_safe_after_language_switch():
    sess = _profile_session(n_die_zones="2.0", ui_lang="fr")  # valeur polluée
    a = build(sess)
    sess["ui_lang"] = "en"
    b = build(sess)
    for crs in (a, b):
        v = crs.process_parameters["n_die_zones"].value
        assert isinstance(v, int) and 1 <= v <= 4


def test_no_demo_ml_data_in_profile_settings_state():
    crs = build(_settings_committed_session())
    for ml in ("stability_score", "proba_stable", "run_duration_min"):
        assert ml not in crs.calculated_outputs
    all_fields = [crs.run_id, crs.screw_profile, crs.feeder_calibration,
                  crs.feed_rate, crs.material_context]
    all_fields += list(crs.process_parameters.values())
    all_fields += list(crs.calculated_outputs.values())
    assert all(f.source != DEMO_DATA for f in all_fields)


def test_no_translated_label_enters_business_state():
    # Un libellé traduit injecté dans une clé métier ne devient jamais la valeur.
    sess = _profile_session(screw_rpm="VITESSE VIS", bulk_density="DENSITÉ")
    crs = build(sess)
    assert isinstance(crs.process_parameters["screw_rpm"].value, float)
    assert isinstance(crs.process_parameters["bulk_density"].value, float)
    # Valeurs retombées sur défaut sûr (coercition), pas le label.
    assert crs.process_parameters["screw_rpm"].value == 120.0


# ---------------------------------------------------------------------------
# Rendu réel (AppTest) — pages se chargent, FR et EN
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

PROFILE = str(ROOT / "app" / "pages" / "1_Profile.py")
SETTINGS = str(ROOT / "app" / "pages" / "2_Settings.py")


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_profile_renders_with_adapter(lang):
    at = AppTest.from_file(PROFILE)
    at.session_state["ui_lang"] = lang
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_settings_renders_with_adapter(lang):
    at = AppTest.from_file(SETTINGS)
    at.session_state["ui_lang"] = lang
    at.run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
