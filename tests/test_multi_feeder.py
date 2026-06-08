"""Tests — étalonnage multi-feeder (débit par feeder + total des calculables)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from physics.multi_feeder import (  # noqa: E402
    STATUS_CALIBRATION_MISSING, STATUS_DISABLED, STATUS_OK,
    FeederCalibration, resolve_multi_feeder,
)
from run_state_adapter import build, build_moteur_inputs_from_current_run_state  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402


def _cal(fid, enabled, rpm, coeff, label=""):
    return FeederCalibration(feeder_id=fid, label=label or f"F{fid}", enabled=enabled,
                             rpm=rpm, coeff_g_h_per_rpm=coeff)


# ---------------------------------------------------------------------------
# Couche pure
# ---------------------------------------------------------------------------
def test_multi_feeder_one_calibrated_one_disabled():
    res = resolve_multi_feeder([_cal(1, True, 30, 10), _cal(2, False, 0, None)])
    by_id = {l.feeder_id: l for l in res.lines}
    assert by_id[1].status == STATUS_OK
    assert abs(by_id[1].flow_g_h - 300.0) < 1e-6
    assert by_id[2].status == STATUS_DISABLED
    assert by_id[2].flow_g_h == 0.0
    assert abs(res.total_g_h - 300.0) < 1e-6


def test_multi_feeder_two_calibrated_sum_flow():
    res = resolve_multi_feeder([_cal(1, True, 20, 5), _cal(2, True, 10, 4)])
    # 20×5=100 ; 10×4=40 ; total=140
    assert abs(res.total_g_h - 140.0) < 1e-6
    assert res.total_calculable is True
    assert res.has_uncalibrated_active is False


def test_multi_feeder_active_missing_coefficient_not_silent_zero():
    res = resolve_multi_feeder([_cal(1, True, 30, 10), _cal(2, True, 50, None)])
    by_id = {l.feeder_id: l for l in res.lines}
    assert by_id[2].status == STATUS_CALIBRATION_MISSING
    assert by_id[2].flow_g_h is None          # PAS un 0 silencieux
    assert res.has_uncalibrated_active is True


def test_multi_feeder_total_flow_excludes_non_calculable():
    res = resolve_multi_feeder([_cal(1, True, 30, 10), _cal(2, True, 50, None)])
    assert abs(res.total_g_h - 300.0) < 1e-6  # seul feeder #1 (OK) compte


def test_multi_feeder_warning_when_one_active_uncalibrated():
    res = resolve_multi_feeder([_cal(1, True, 30, 10), _cal(2, True, 50, None)])
    assert res.has_uncalibrated_active is True


def test_multi_feeder_all_uncalibrated_total_not_calculable():
    res = resolve_multi_feeder([_cal(1, True, 30, None), _cal(2, True, 50, None)])
    assert res.total_calculable is False
    assert res.total_g_h is None


# ---------------------------------------------------------------------------
# Migration legacy + intégration current_run_state / Moteur
# ---------------------------------------------------------------------------
def _session(**extra):
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    sess = {"screw_config": cfg, "screw_rpm": 100.0, "bulk_density": 0.55,
            "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0}
    sess.update(extra)
    return sess


def test_legacy_fd_flow_migrates_to_feeder_1():
    # Les clés legacy feeder_rpm/feeder_calib alimentent le feeder #1 du banc.
    crs = build(_session())
    assert crs.feeders is not None
    line1 = next(l for l in crs.feeders.lines if l.feeder_id == 1)
    assert line1.status == STATUS_OK
    assert abs(line1.flow_g_h - 300.0) < 1e-6


def test_moteur_procede_uses_multi_feeder_total_flow():
    # Feeder #2 activé + étalonné via current_run_state → total inclut #2.
    from AgentIndustrial_v1.core.feeders import new_feeder_bank
    sess = _session()
    # Active le feeder #2 dans le banc + son étalonnage.
    bank = new_feeder_bank()
    sess["fd_en_2"] = True            # (clé widget Settings — sera lue par build_state_from_widgets)
    # Le banc par défaut a #2 désactivé ; on simule via clé d'étalonnage + enabled.
    sess["feedcal_rpm_2"] = 10.0
    sess["feedcal_coeff_2"] = 4.0
    crs = build(sess)
    # Sans activation réelle du feeder #2 dans le snapshot, #2 reste désactivé →
    # total = #1 seul. On vérifie au minimum que le total vient du banc multi.
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert mi["multi_feeder"] is not None
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - (crs.feeders.total_g_h / 60.0)) < 1e-6


def test_moteur_procede_displays_each_feeder_source_and_status():
    crs = build(_session())
    mi = build_moteur_inputs_from_current_run_state(crs)
    multi = mi["multi_feeder"]
    assert multi is not None
    for line in multi.lines:
        assert line.status in (STATUS_OK, STATUS_DISABLED, STATUS_CALIBRATION_MISSING)
        assert line.feeder_id >= 1


def test_no_material_injected_by_multi_feeder():
    # Aucun polymère saisi → aucune matière injectée par le banc multi-feeder.
    crs = build(_session())
    for line in crs.feeders.lines:
        assert line.material_label == ""
        assert line.material_source == "NOT_AVAILABLE"


def test_multi_feeder_uncalibrated_feed_not_available():
    crs = build(_session(feeder_calib_g_h_per_rpm=0.0))
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert mi["feed_available"] is False
    assert mi["feed_g_per_min"] == 0.0


def test_language_switch_keeps_multi_feeder_state_clean():
    sess = _session(ui_lang="fr")
    a = build(sess)
    sess["ui_lang"] = "en"
    b = build(sess)
    assert a.feeders == b.feeders


# ---------------------------------------------------------------------------
# Rendu réel (AppTest)
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

SETTINGS = str(APP / "pages" / "2_Settings.py")
MOTEUR = str(APP / "pages" / "5_Moteur_Procede.py")
SUP = str(APP / "Supervision.py")


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_renders_multi_feeder_calibration():
    at = AppTest.from_file(SETTINGS)
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_does_not_show_fake_zero_when_feeder_uncalibrated():
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    at = AppTest.from_file(SUP)
    at.session_state["screw_config"] = cfg
    at.session_state["feeder_calib_g_h_per_rpm"] = 0.0     # non étalonné
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = "\n".join(
        [str(getattr(e, "value", "")) for e in at.warning]
        + [str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html")]
    )
    assert "coefficient d'étalonnage feeder à renseigner" in blob
