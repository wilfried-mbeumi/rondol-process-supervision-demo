"""E2E PROD REBOOT — the exact client scenario, asserted on ACTUAL widget values.

Why this exists: the previous E2E (test_e2e_client_sync) asserted on snapshot
OBJECTS and session_state, and let the ephemeral operator store mask the real
bug. This test instead:

  * drives the REAL widgets on the REAL pages,
  * simulates a true Streamlit Cloud REBOOT — wipes BOTH ephemeral files
    (current_run_state.json AND applied_state.json); ONLY the durable store
    (Supabase stand-in = external store) survives,
  * asserts the ACTUAL rendered widget VALUES after reboot (density 0.55 — NOT
    0.000, feeder ON, thermal > 0, RPM 100, screw elements present),
  * proves a DEGENERATE/partial snapshot (old build) self-heals instead of
    crashing Settings (KeyError) or showing 0.000 / 0.00.

These tests FAIL on the pre-fix behaviour (blank widgets / crash) and pass only
when every page is truly hydrated from the durable snapshot.

Only RONDOL_EXTERNAL_STORE_PATH is ours (module-scoped). conftest owns
RONDOL_{HISTORY,RUN_STATE,APPLIED}_PATH and clears the ephemeral mirrors before
each test — exactly the reboot condition we want.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_TMP = tempfile.mkdtemp(prefix="rondol_e2e_reboot_")
_DURABLE = str(Path(_TMP) / "durable_store.json")   # Supabase stand-in (survives reboot)
_EXT_ENV = "RONDOL_EXTERNAL_STORE_PATH"

from streamlit.testing.v1 import AppTest  # noqa: E402
import screw_logic as _sl  # noqa: E402

LABEL = "TEST_FINAL_001"
SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
SUPERVISION = str(APP / "Supervision.py")
ENGINE = str(APP / "pages" / "5_Process_Engine.py")
HISTORY = str(APP / "pages" / "4_History.py")

RPM, COEFF, DENS = 100.0, 2.5, 0.55
FLOW = RPM * COEFF / 60.0   # 4.1667 g/min
N_EL = 4


@pytest.fixture(autouse=True)
def _durable_env():
    prev = os.environ.get(_EXT_ENV)
    os.environ[_EXT_ENV] = _DURABLE
    try:
        Path(_DURABLE).unlink()
    except Exception:
        pass
    yield
    if prev is None:
        os.environ.pop(_EXT_ENV, None)
    else:
        os.environ[_EXT_ENV] = prev


def _reboot():
    """Wipe the ephemeral disk (operator store + local applied mirror). The
    durable external store (Supabase stand-in) survives — exactly prod reboot."""
    for env in ("RONDOL_RUN_STATE_PATH", "RONDOL_APPLIED_STATE_PATH"):
        p = os.environ.get(env)
        if p:
            try:
                Path(p).unlink()
            except Exception:
                pass


def _w(at, kind, key):
    for w in getattr(at, kind):
        if w.key == key:
            return w
    return None


def _num(at, key):
    w = _w(at, "number_input", key)
    return w.value if w is not None else None


def _new(path):
    at = AppTest.from_file(path, default_timeout=120)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at


def _visible(at) -> str:
    out = []
    for kind in ("markdown", "caption", "header", "subheader", "info", "warning", "success", "error"):
        for el in getattr(at, kind):
            out.append(re.sub(r"<[^>]+>", " ", str(getattr(el, "value", ""))))
    try:
        for el in at.get("html"):
            out.append(re.sub(r"<[^>]+>", " ", str(getattr(el, "body", getattr(el, "value", "")))))
    except Exception:
        pass
    for m in at.metric:
        out.append(f"{getattr(m,'label','')}={getattr(m,'value','')}")
    return " | ".join(out)


def _save_client_config_via_real_widgets():
    """Steps 2-9: Settings real widgets + Save, asserting widgets stay set."""
    at = _new(SETTINGS); at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    fd = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    fd.set_value(True); at.run()
    _w(at, "number_input", "feeder_rpm").set_value(RPM)
    _w(at, "number_input", "feeder_calib_g_h_per_rpm").set_value(COEFF)
    _w(at, "number_input", "ni_rpm_hmi").set_value(RPM)
    _w(at, "number_input", "fd_dens_1").set_value(DENS)
    at.run()
    _w(at, "text_input", "apply_label").set_value(LABEL)
    _w(at, "button", "btn_apply_state").click(); at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    # Step 9: widgets STILL show the saved values right after Save.
    assert _num(at, "feeder_rpm") == RPM
    assert _num(at, "feeder_calib_g_h_per_rpm") == COEFF
    assert _num(at, "fd_dens_1") == DENS
    fd2 = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    assert fd2.value is True


def _save_profile_via_top_button():
    """Steps 10-13: Profile add elements + click the NEW save button NEAR the
    screw controls (btn_profile_save_top), assert elements present."""
    p = _new(PROFILE); p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    for _ in range(N_EL):
        _w(p, "button", "plus1_1").click(); p.run()
    btn = _w(p, "button", "btn_profile_save_top")
    assert btn is not None, "NEW save button near screw controls is missing"
    btn.click(); p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    assert _sl.count_user_elements(list(p.session_state["screw_config"])) == N_EL


def test_profile_has_save_button_near_screw_controls():
    """Step 5/12: a visible 'Save profile' button exists near the screw controls."""
    p = _new(PROFILE); p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    assert _w(p, "button", "btn_profile_save_top") is not None


def test_full_client_flow_survives_reboot():
    """The exact 25-step scenario: save → reboot → every page hydrated from
    the durable snapshot, asserted on ACTUAL widget values."""
    _save_client_config_via_real_widgets()
    _save_profile_via_top_button()

    # The durable snapshot is complete BEFORE reboot.
    d = json.loads(Path(_DURABLE).read_text(encoding="utf-8"))
    assert d["label"] == LABEL
    assert d["feeders"][0]["enabled"] is True
    assert abs(d["feeders"][0]["density_g_per_cm3"] - DENS) < 1e-6

    _reboot()  # wipe ephemeral; only Supabase stand-in survives

    # Step 21: fresh Settings — ACTUAL widget values (NOT 0.000 / OFF / 0.00).
    at = _new(SETTINGS); at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert _num(at, "feeder_rpm") == RPM
    assert _num(at, "feeder_calib_g_h_per_rpm") == COEFF
    assert _num(at, "ni_rpm_hmi") == RPM
    assert _num(at, "fd_dens_1") == DENS, "density widget reset after reboot (P0 bug)"
    fd = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    assert fd.value is True, "feeder toggle reset OFF after reboot (P0 bug)"
    assert _num(at, "th_Z1") and _num(at, "th_Z1") > 0.0, "thermal reset to 0 after reboot"

    # Step 22: fresh Profile — elements still present.
    p = _new(PROFILE); p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    assert _sl.count_user_elements(list(p.session_state["screw_config"])) == N_EL

    # Step 23: fresh Supervision — operator state (label + RPM), not blank.
    s = _new(SUPERVISION); s.run()
    assert not s.exception, [str(e.value) for e in s.exception]
    stext = _visible(s)
    assert LABEL in stext, "operator label not shown on Supervision after reboot"
    assert "100" in stext, "operator RPM not used on Supervision after reboot"

    # Step 24: fresh Process Engine — same saved state, not empty.
    e = _new(ENGINE); e.run()
    assert not e.exception, [str(e.value) for e in e.exception]
    etext = _visible(e)
    assert "No process profile" not in etext and "Aucun profil" not in etext

    # Step 25: fresh History — same snapshot label.
    h = _new(HISTORY); h.run()
    assert not h.exception, [str(e.value) for e in h.exception]
    assert LABEL in _visible(h)


def _write_degenerate_snapshot():
    """A snapshot saved by an OLDER buggy build: density 0, zone temps 0, only
    feeder #1 present. This is the real prod row that blanked the widgets."""
    cfg = list(_sl.new_empty_configuration())
    for i in range(2, 8):
        cfg[i] = 1
    snap = {
        "timestamp_iso": "2026-06-13T10:00:00", "label": LABEL,
        "screw_config": cfg, "screw_rpm": 100.0,
        "zone_temps_C": {z: 0.0 for z in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8")},
        "n_die_zones": 1,
        "feeders": [{
            "feeder_id": 1, "enabled": True, "label": "Main", "material_id": "granules",
            "position": "Z0", "speed_rpm": 120.0, "mass_flow_g_per_min": 0.0,
            "density_g_per_cm3": 0.0, "thermal_expansion_per_K": 7e-05, "polymer_name": "",
            "t_degradation_C": None, "tga_onset_C": None, "viscosity_pa_s": None,
            "t_melt_C": None, "t_glass_C": None,
        }],
        "torque_pct": None, "pressure_die_bar": None,
        "feeder_calibrations": {"1": {"rpm": 100.0, "coeff": 2.5}},
    }
    Path(_DURABLE).write_text(json.dumps(snap), encoding="utf-8")


def test_degenerate_snapshot_self_heals_without_crash():
    """A degenerate/partial Supabase row must NOT crash Settings and must heal
    non-physical density/thermal to sensible defaults (never 0.000 / 0.00)."""
    _write_degenerate_snapshot()
    _reboot()  # ephemeral empty — only the degenerate durable row exists

    at = _new(SETTINGS); at.run()
    # Pre-fix this raised KeyError 'fd_en_2' (snapshot had < 5 feeders).
    assert not at.exception, ["Settings crashed on degenerate snapshot"] + \
        [str(e.value) for e in at.exception]
    # density 0 -> healed to 0.55 (was clamped to 0.0001 -> "0.000").
    assert _num(at, "fd_dens_1") == DENS, "degenerate density not healed (shows 0.000)"
    # zone temp 0 -> healed to a positive default (was "0.00").
    assert _num(at, "th_Z1") and _num(at, "th_Z1") > 0.0, "degenerate thermal not healed"
    # feeder still ON, feeder bank padded (no missing fd_en_2..5).
    fd = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    assert fd.value is True


def test_engine_reads_healed_degenerate_snapshot():
    """Process Engine must also render (not 'No process profile') from a
    degenerate durable snapshot after reboot."""
    _write_degenerate_snapshot()
    _reboot()
    e = _new(ENGINE); e.run()
    assert not e.exception, [str(ex.value) for ex in e.exception]
    assert "No process profile" not in _visible(e)
