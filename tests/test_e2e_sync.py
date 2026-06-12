"""test_e2e_sync.py — E2E state synchronisation across pages.

Manager scenario (24 steps):
  New session → Settings (configure + save TEST_SYNC_MANAGER_001) →
  Profile (add elements + save) → Supervision (verify all) →
  Moteur Procédé (verify) → Historique (verify) → refresh →
  Supervision (verify restored) → Settings (verify not reset) →
  Profile (verify elements present).

Priority 2 from manager stabilisation brief (2026-06-11).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from streamlit.testing.v1 import AppTest
    _HAS = True
except Exception:
    _HAS = False

PAGES = {
    "Supervision": str(APP / "Supervision.py"),
    "Profile": str(APP / "pages" / "1_Profile.py"),
    "Settings": str(APP / "pages" / "2_Settings.py"),
    "Historique": str(APP / "pages" / "4_History.py"),
    "Moteur_Procede": str(APP / "pages" / "5_Process_Engine.py"),
}


@pytest.fixture(autouse=True)
def _isolate_disk(tmp_path, monkeypatch):
    """Each test gets isolated disk state files — no cross-test contamination."""
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "crs.json"))
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(tmp_path / "applied.json"))
    monkeypatch.setenv("RONDOL_HISTORY_PATH", str(tmp_path / "history.json"))


def _seed_settings_state(session):
    """Seed session with a configured Settings state: RPM=100, feeder #1 active,
    coeff=2.5, zone temps set."""
    session["ui_lang"] = "en"
    session["demo_mode"] = False

    # RPM widget key (Settings owns this)
    session["ni_rpm_hmi"] = 100.0
    session["screw_rpm"] = 100.0

    # Feeder #1 calibration: RPM=100, coeff=2.5 → 250 g/h = 4.17 g/min
    session["feeder_rpm"] = 100.0
    session["feeder_calib_g_h_per_rpm"] = 2.5
    session["feeder_rpm__persist"] = 100.0
    session["feeder_calib_g_h_per_rpm__persist"] = 2.5

    # Feeder #1 enabled with full spec
    session["fd_en_1"] = True
    session["fd_lbl_1"] = "Main"
    session["fd_mat_1"] = "granules"
    session["fd_dens_1"] = 0.55
    session["fd_alpha_1"] = 5e-5
    session["fd_pos_1"] = "Z0"
    session["fd_flow_1"] = 30.0
    session["fd_poly_1"] = "PVDF"
    session["fd_tdeg_1"] = 280.0
    session["fd_tga_1"] = 0.0
    session["fd_visc_1"] = 0.0
    session["fd_tmelt_1"] = 170.0
    session["fd_tglass_1"] = 0.0

    # Zone temps
    session["th_Z1"] = 160.0
    session["th_Z2"] = 170.0
    session["th_Z3"] = 180.0
    session["th_Z4"] = 185.0
    session["th_Z5"] = 190.0
    session["th_Z6"] = 185.0
    session["th_Z7"] = 180.0
    session["th_Z8"] = 175.0
    session["th_die"] = 170.0
    session["n_die_zones"] = 1

    session["bulk_density"] = 0.55
    session["side_feeder_zone"] = 0


def _make_screw_with_elements():
    """Conveying + Kneading 60° (manager scenario step 10)."""
    from screw_logic import new_empty_configuration, add_element
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=4)   # 4 conveying
    add_element(cfg, 7, count=2)   # 2 kneading 60°
    add_element(cfg, 1, count=3)   # 3 conveying
    return cfg


def _rendered_text(at) -> str:
    """Extract all visible text from a rendered AppTest."""
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    try:
        for m in at.metric:
            chunks.append(str(getattr(m, "label", "")))
            chunks.append(str(getattr(m, "value", "")))
    except Exception:
        pass
    return "\n".join(chunks)


# =========================================================================
# MANAGER SCENARIO — 24-step E2E test
# =========================================================================

@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_manager_e2e_24_steps():
    """Full 24-step manager scenario:
    Settings (configure + save) → Profile (add elements + save) →
    Supervision → Moteur → Historique → refresh → verify all.

    Each step maps to the manager's numbered requirement.
    """
    from AgentIndustrial_v1.core.applied_state import commit, get_applied, hydrate_state
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    from AgentIndustrial_v1.core.screw_adapter import refresh_kpis
    from AgentIndustrial_v1.core.current_run_state import build_current_run_state, CALCULATED
    from AgentIndustrial_v1.core.rules import evaluate as agent_evaluate
    from AgentIndustrial_v1.core.recommendations import build_recommendations
    from screw_logic import count_user_elements

    # ── Step 1: New clean session ──
    # ── Step 2: Go to Settings ──
    at = AppTest.from_file(PAGES["Settings"])

    # ── Step 3: Set run name TEST_SYNC_MANAGER_001 ──
    _seed_settings_state(at.session_state)
    at.session_state["apply_label"] = "TEST_SYNC_MANAGER_001"

    # ── Step 4: Activate feeder #1 ── (done in _seed_settings_state: fd_en_1=True)
    # ── Step 5: RPM = 100 ── (done: ni_rpm_hmi=100, screw_rpm=100)
    # ── Step 6: Coefficient = 2.5 ── (done: feeder_calib_g_h_per_rpm=2.5)
    at = at.run(timeout=120)
    assert not at.exception, f"Settings page error: {[str(e.value) for e in at.exception]}"

    # ── Step 7: Verify debit = 250 g/h = 4.17 g/min ──
    from physics.feeder_flow import resolve_feeder_flow
    ff = resolve_feeder_flow(100.0, 2.5)
    assert ff.calibrated, "Feeder must be calibrated with coeff=2.5"
    assert ff.effective_g_h == pytest.approx(250.0, abs=0.01), \
        f"250 g/h expected, got {ff.effective_g_h}"
    assert ff.effective_g_min == pytest.approx(250.0 / 60.0, abs=0.01), \
        f"4.17 g/min expected, got {ff.effective_g_min}"

    # ── Step 8: Save Settings ──
    state_settings = build_state_from_widgets(at.session_state)
    snap_settings = commit(at.session_state, state_settings, label="TEST_SYNC_MANAGER_001")
    assert snap_settings is not None, "Settings commit must produce a snapshot"
    assert snap_settings.label == "TEST_SYNC_MANAGER_001"
    assert snap_settings.screw_rpm == 100.0

    # ── Step 9: Go to Profile ──
    # ── Step 10: Add conveying + kneading 60° ──
    cfg = _make_screw_with_elements()
    at.session_state["screw_config"] = cfg
    n_elements = count_user_elements(cfg)
    assert n_elements > 0, "Must have placed elements"

    # ── Step 11: Save Profile ──
    # Profile save: reads snapshot state (preserves Settings data), overrides screw_config
    _prev_snap = get_applied(at.session_state)
    state_profile = state_from_session(at.session_state)
    state_profile.screw_config = list(cfg)
    refresh_kpis(state_profile)
    snap_profile = commit(at.session_state, state_profile, label=_prev_snap.label)
    assert snap_profile is not None, "Profile commit must produce a snapshot"
    assert snap_profile.label == "TEST_SYNC_MANAGER_001", \
        "Profile save must preserve Settings run label"
    assert snap_profile.screw_config == cfg, "Profile save must include new elements"
    assert snap_profile.screw_rpm == 100.0, "Profile save must preserve RPM=100"
    assert len(snap_profile.feeders) >= 1, "Profile save must preserve feeders"

    # ── Step 12: Go to Supervision ──
    at_sup = AppTest.from_file(PAGES["Supervision"])
    at_sup.session_state["ui_lang"] = "en"
    at_sup.session_state["demo_mode"] = False
    at_sup = at_sup.run(timeout=120)
    assert not at_sup.exception, \
        f"Supervision error: {[str(e.value) for e in at_sup.exception]}"

    # ── Step 13: Verify Supervision reads correct state ──
    snap_sup = get_applied(at_sup.session_state)
    assert snap_sup is not None, "Supervision must restore snapshot from disk"
    assert snap_sup.label == "TEST_SYNC_MANAGER_001", \
        f"Supervision label mismatch: {snap_sup.label}"
    assert snap_sup.screw_rpm == 100.0, "Supervision RPM must be 100"
    assert snap_sup.screw_config == cfg, "Supervision must show Profile elements"

    # 13a: Run label visible in rendered text
    text_sup = _rendered_text(at_sup)
    assert "TEST_SYNC_MANAGER_001" in text_sup, \
        "Run label must be visible in Supervision rendered output"

    # 13b: Feeder #1 active and calibration in CRS
    crs_sup = build_current_run_state(at_sup.session_state)
    assert crs_sup.feed_rate.source == CALCULATED, \
        "Feed rate must be CALCULATED from calibration"
    assert crs_sup.feed_rate.value is not None, "Feed rate value must exist"
    assert crs_sup.feed_rate.value == pytest.approx(250.0, abs=1.0), \
        f"Feed rate must be ~250 g/h, got {crs_sup.feed_rate.value}"

    # 13c: screw_config has elements
    state_sup = state_from_session(at_sup.session_state)
    assert count_user_elements(state_sup.screw_config) > 0, \
        "Supervision state must contain placed screw elements"

    # 13d: Agent IA uses the saved state (not defaults)
    agent_report = agent_evaluate(state_sup, lang="en")
    assert agent_report is not None, "Agent must produce a report"
    agent_recos = build_recommendations(state_sup, agent_report.alerts, lang="en")
    assert agent_recos is not None, "Agent must produce recommendations"

    # ── Step 14: Go to Process Engine (Moteur Procédé) ──
    at_mot = AppTest.from_file(PAGES["Moteur_Procede"])
    at_mot.session_state["ui_lang"] = "en"
    at_mot.session_state["demo_mode"] = False
    at_mot = at_mot.run(timeout=120)
    assert not at_mot.exception, \
        f"Moteur error: {[str(e.value) for e in at_mot.exception]}"

    # ── Step 15: Verify Process Engine reads same values ──
    snap_mot = get_applied(at_mot.session_state)
    assert snap_mot is not None, "Moteur must restore snapshot"
    assert snap_mot.screw_rpm == 100.0, "Moteur RPM must be 100"
    assert snap_mot.screw_config == cfg, "Moteur must show Profile elements"
    assert snap_mot.label == "TEST_SYNC_MANAGER_001"
    crs_mot = build_current_run_state(at_mot.session_state)
    assert crs_mot.feed_rate.source == CALCULATED, "Moteur feed rate must be CALCULATED"

    # ── Step 16: Go to History ──
    at_hist = AppTest.from_file(PAGES["Historique"])
    at_hist.session_state["ui_lang"] = "en"
    at_hist.session_state["demo_mode"] = False
    at_hist = at_hist.run(timeout=120)
    assert not at_hist.exception, \
        f"Historique error: {[str(e.value) for e in at_hist.exception]}"

    # ── Step 17: Verify History has the same state ──
    snap_hist = get_applied(at_hist.session_state)
    assert snap_hist is not None, "History must have access to the snapshot"
    assert snap_hist.label == "TEST_SYNC_MANAGER_001"
    assert snap_hist.screw_config == cfg

    # ── Step 18: Simulate refresh / new session ──
    # (new AppTest = fresh session, only disk state survives)

    # ── Step 19: Return to Supervision ──
    at_sup2 = AppTest.from_file(PAGES["Supervision"])
    at_sup2.session_state["ui_lang"] = "en"
    at_sup2.session_state["demo_mode"] = False
    at_sup2 = at_sup2.run(timeout=120)
    assert not at_sup2.exception

    # ── Step 20: Verify same state restored from applied_state.json ──
    snap_sup2 = get_applied(at_sup2.session_state)
    assert snap_sup2 is not None, "Snapshot must survive refresh (disk mirror)"
    assert snap_sup2.label == "TEST_SYNC_MANAGER_001", \
        f"Label after refresh: {snap_sup2.label}"
    assert snap_sup2.screw_rpm == 100.0, "RPM must survive refresh"
    assert snap_sup2.screw_config == cfg, "Screw config must survive refresh"
    text_sup2 = _rendered_text(at_sup2)
    assert "TEST_SYNC_MANAGER_001" in text_sup2, \
        "Run label must be visible after refresh"

    # ── Step 21: Return to Settings ──
    at_set2 = AppTest.from_file(PAGES["Settings"])
    at_set2.session_state["ui_lang"] = "en"
    at_set2.session_state["demo_mode"] = False
    at_set2 = at_set2.run(timeout=120)
    assert not at_set2.exception, \
        f"Settings after refresh error: {[str(e.value) for e in at_set2.exception]}"

    # ── Step 22: Verify Settings data NOT reset ──
    snap_set2 = get_applied(at_set2.session_state)
    assert snap_set2 is not None, "Settings must restore snapshot"
    assert snap_set2.screw_rpm == 100.0, "RPM must not be reset to default"
    assert snap_set2.label == "TEST_SYNC_MANAGER_001"
    assert len(snap_set2.feeders) >= 1, "Feeders must survive"

    # ── Step 23: Return to Profile ──
    at_prof2 = AppTest.from_file(PAGES["Profile"])
    at_prof2.session_state["ui_lang"] = "en"
    at_prof2.session_state["demo_mode"] = False
    at_prof2 = at_prof2.run(timeout=120)
    assert not at_prof2.exception, \
        f"Profile after refresh error: {[str(e.value) for e in at_prof2.exception]}"

    # ── Step 24: Verify screw elements still present ──
    snap_prof2 = get_applied(at_prof2.session_state)
    assert snap_prof2 is not None, "Profile must restore snapshot"
    assert snap_prof2.screw_config == cfg, \
        "Screw elements must survive full cycle"
    assert count_user_elements(snap_prof2.screw_config) > 0, \
        "User elements must still be placed"


# =========================================================================
# Focused tests — one concern each
# =========================================================================

@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_profile_save_preserves_settings_data():
    """Profile save must NOT erase Settings data (feeders, zone temps, RPM)."""
    from AgentIndustrial_v1.core.applied_state import commit
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    from AgentIndustrial_v1.core.screw_adapter import refresh_kpis

    at = AppTest.from_file(PAGES["Settings"])
    _seed_settings_state(at.session_state)
    at = at.run(timeout=120)
    assert not at.exception

    state = build_state_from_widgets(at.session_state)
    snap1 = commit(at.session_state, state, label="SETTINGS_FIRST")
    assert snap1.feeders[0].get("polymer_name") == "PVDF"

    cfg = _make_screw_with_elements()
    state2 = state_from_session(at.session_state)
    state2.screw_config = list(cfg)
    refresh_kpis(state2)
    snap2 = commit(at.session_state, state2, label="SETTINGS_FIRST")

    assert snap2.screw_rpm == 100.0, "RPM lost"
    assert snap2.zone_temps_C.get("Z1") == 160.0, "Z1 temp lost"
    assert snap2.zone_temps_C.get("Z5") == 190.0, "Z5 temp lost"
    assert snap2.n_die_zones == 1, "n_die_zones lost"
    assert snap2.feeders[0].get("enabled") is True, "Feeder #1 enable lost"
    assert snap2.feeders[0].get("polymer_name") == "PVDF", "Polymer lost"
    assert snap2.screw_config == cfg, "Profile elements not saved"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_settings_save_preserves_profile_elements():
    """Settings save must NOT erase Profile screw elements.

    Simulates: Settings save → Profile save (adds elements) → browser refresh →
    Settings re-load → Settings re-save with RPM=150 → elements still there.
    """
    from AgentIndustrial_v1.core.applied_state import commit, get_applied
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    from AgentIndustrial_v1.core.screw_adapter import refresh_kpis

    # Phase 1: Initial Settings save
    at = AppTest.from_file(PAGES["Settings"])
    _seed_settings_state(at.session_state)
    at = at.run(timeout=120)
    assert not at.exception

    # Phase 2: Profile adds elements and commits (preserving Settings data)
    # Also sync operator store — the real Profile page calls capture_operator_state
    # at the end of every rerun (line 1198 of 1_Profile.py).
    from operator_store import capture_operator_state
    cfg = _make_screw_with_elements()
    at.session_state["screw_config"] = list(cfg)
    state = state_from_session(at.session_state)
    state.screw_config = list(cfg)
    refresh_kpis(state)
    commit(at.session_state, state, label="WITH_PROFILE")
    capture_operator_state(at.session_state)

    # Phase 3: Simulate browser refresh → fresh Settings page load
    # New AppTest = new session. Only disk state survives.
    at2 = AppTest.from_file(PAGES["Settings"])
    at2.session_state["ui_lang"] = "en"
    at2.session_state["demo_mode"] = False
    at2 = at2.run(timeout=120)
    assert not at2.exception, [str(e.value) for e in at2.exception]

    # seed_editing_keys must have re-seeded screw_config from disk snapshot
    snap_check = get_applied(at2.session_state)
    assert snap_check is not None, "Snapshot must be restored from disk"
    assert snap_check.screw_config == cfg, "Snapshot must have Profile elements"

    # Phase 4: Settings re-save with RPM=150
    at2.session_state["ni_rpm_hmi"] = 150.0
    state2 = build_state_from_widgets(at2.session_state)
    snap2 = commit(at2.session_state, state2, label="WITH_PROFILE")

    assert snap2.screw_rpm == 150.0, "RPM must be updated to 150"
    assert snap2.screw_config == cfg, "Profile elements must survive Settings re-save"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_agent_uses_applied_state_not_defaults():
    """Agent IA must use saved profile state, not empty defaults."""
    from AgentIndustrial_v1.core.applied_state import commit
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    from AgentIndustrial_v1.core.screw_adapter import refresh_kpis
    from AgentIndustrial_v1.core.rules import evaluate

    at = AppTest.from_file(PAGES["Settings"])
    _seed_settings_state(at.session_state)
    cfg = _make_screw_with_elements()
    at.session_state["screw_config"] = cfg
    at = at.run(timeout=120)
    assert not at.exception

    state = build_state_from_widgets(at.session_state)
    state.screw_config = list(cfg)
    refresh_kpis(state)
    commit(at.session_state, state, label="AGENT_TEST")

    # Fresh session — agent reads from disk
    at2 = AppTest.from_file(PAGES["Supervision"])
    at2.session_state["ui_lang"] = "en"
    at2.session_state["demo_mode"] = False
    at2 = at2.run(timeout=120)
    assert not at2.exception

    state_fresh = state_from_session(at2.session_state)
    assert state_fresh.screw_rpm == 100.0, \
        f"Agent state RPM must be 100, got {state_fresh.screw_rpm}"
    from screw_logic import count_user_elements
    assert count_user_elements(state_fresh.screw_config) > 0, \
        "Agent state must have screw elements, not empty defaults"
    report = evaluate(state_fresh, lang="en")
    assert report is not None


@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_run_label_visible_in_supervision():
    """Run label TEST_SYNC_MANAGER_001 must appear in Supervision."""
    from AgentIndustrial_v1.core.applied_state import commit
    from AgentIndustrial_v1.core.state_sync import state_from_session

    at = AppTest.from_file(PAGES["Settings"])
    _seed_settings_state(at.session_state)
    at = at.run(timeout=120)
    assert not at.exception

    state = state_from_session(at.session_state)
    commit(at.session_state, state, label="TEST_SYNC_MANAGER_001")

    at2 = AppTest.from_file(PAGES["Supervision"])
    at2.session_state["ui_lang"] = "en"
    at2.session_state["demo_mode"] = False
    at2 = at2.run(timeout=120)
    assert not at2.exception

    text = _rendered_text(at2)
    assert "TEST_SYNC_MANAGER_001" in text, \
        f"Label not visible. Rendered text starts with:\n{text[:500]}"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_snapshot_survives_refresh():
    """Applied snapshot must survive browser refresh (disk mirror)."""
    from AgentIndustrial_v1.core.applied_state import commit, get_applied
    from AgentIndustrial_v1.core.state_sync import state_from_session

    at = AppTest.from_file(PAGES["Settings"])
    _seed_settings_state(at.session_state)
    at = at.run(timeout=120)
    assert not at.exception

    state = state_from_session(at.session_state)
    commit(at.session_state, state, label="REFRESH_TEST")

    at2 = AppTest.from_file(PAGES["Supervision"])
    at2.session_state["ui_lang"] = "en"
    at2.session_state["demo_mode"] = False
    at2 = at2.run(timeout=120)
    assert not at2.exception

    snap = get_applied(at2.session_state)
    assert snap is not None, "Snapshot lost after refresh"
    assert snap.label == "REFRESH_TEST"
    assert snap.screw_rpm == 100.0


@pytest.mark.skipif(not _HAS, reason="streamlit.testing unavailable")
def test_feeder_calibration_250gh():
    """Feeder RPM=100, coeff=2.5 must yield exactly 250 g/h = 4.17 g/min."""
    from physics.feeder_flow import resolve_feeder_flow
    ff = resolve_feeder_flow(100.0, 2.5)
    assert ff.calibrated
    assert ff.effective_g_h == pytest.approx(250.0, abs=0.01)
    assert ff.effective_g_min == pytest.approx(250.0 / 60.0, abs=0.01)
