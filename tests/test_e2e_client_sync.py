"""E2E client sync — label TEST_CLIENT_SYNC_001 across all pages + refresh.

Reproduces the manager's exact 15-step client scenario with REAL widget
interactions and a DURABLE store (RONDOL_EXTERNAL_STORE_PATH) shared across
fresh AppTest sessions — each `AppTest.from_file` is a new session, the shared
external file emulates Supabase surviving a browser refresh / redeploy.

Asserts the single source of truth (the committed snapshot) drives Settings,
Profile, Supervision, Process Engine and History identically — BEFORE and AFTER
a full refresh. A divergence here is a P0 prod-sync bug.

Env paths are set at import time (modules read them lazily at call time).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Isolated DURABLE store + volatile mirrors — set before any app import that
# resolves paths. The external store stands in for Supabase across sessions.
_TMP = tempfile.mkdtemp(prefix="rondol_e2e_client_")
_DURABLE_STORE = str(Path(_TMP) / "durable_store.json")
_EXT_ENV = "RONDOL_EXTERNAL_STORE_PATH"

from streamlit.testing.v1 import AppTest  # noqa: E402

LABEL = "TEST_CLIENT_SYNC_001"
SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
SUPERVISION = str(APP / "Supervision.py")
ENGINE = str(APP / "pages" / "5_Process_Engine.py")
HISTORY = str(APP / "pages" / "4_History.py")

EXPECTED_RPM = 100.0
EXPECTED_COEFF = 2.5
EXPECTED_DENS = 0.55
EXPECTED_FLOW_G_MIN = 100.0 * 2.5 / 60.0   # rpm × g/h/rpm ÷ 60 = 4.1667 g/min
N_ELEMENTS = 4


@pytest.fixture(scope="module", autouse=True)
def _durable_store_env():
    """Configure the durable external store for THIS module only.

    Set/torn down here (NOT at import) so the durable backend never leaks into
    other test modules — a global env mutation would turn every test's backend
    into 'external-file' and cross-contaminate persistence suites. conftest
    owns RONDOL_{HISTORY,RUN_STATE,APPLIED}_PATH and clears the local applied
    mirror before each test; the external store is ours and survives across the
    fresh AppTest 'sessions', emulating Supabase across a refresh.
    """
    prev = os.environ.get(_EXT_ENV)
    os.environ[_EXT_ENV] = _DURABLE_STORE
    # Ardoise propre au SETUP DU MODULE : le fixture `_committed` (module-scope)
    # s'exécute avant le nettoyage per-fonction du conftest. Sans ce nettoyage
    # explicite, il lit un applied_state/run_state laissé par un module exécuté
    # avant (selon l'ordre aléatoire), d'où des éléments de vis résiduels.
    for _env in (_EXT_ENV, "RONDOL_APPLIED_STATE_PATH", "RONDOL_RUN_STATE_PATH", "RONDOL_HISTORY_PATH"):
        _p = os.environ.get(_env)
        if _p:
            try:
                Path(_p).unlink()
            except Exception:
                pass
    yield
    if prev is None:
        os.environ.pop(_EXT_ENV, None)
    else:
        os.environ[_EXT_ENV] = prev


def _w(at, kind, key):
    for w in getattr(at, kind):
        if w.key == key:
            return w
    return None


def _new(path):
    at = AppTest.from_file(path, default_timeout=120)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at


def _visible(at) -> str:
    import re
    chunks = []
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
            chunks.append(f"{getattr(m, 'label', '')} = {getattr(m, 'value', '')}")
    except Exception:
        pass
    raw = "\n".join(chunks)
    return re.sub(r"<[^>]+>", " ", raw)


@pytest.fixture(scope="module")
def _committed():
    """Steps 2-8: drive Settings (real widgets) + Profile, commit the snapshot."""
    # --- Settings: rpm/coeff/feeder/density/label, Save ---------------------
    at = _new(SETTINGS)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    fd_en = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    assert fd_en is not None, "feeder #1 enable widget missing"
    fd_en.set_value(True)
    at.run()

    _w(at, "number_input", "feeder_rpm").set_value(EXPECTED_RPM)
    _w(at, "number_input", "feeder_calib_g_h_per_rpm").set_value(EXPECTED_COEFF)
    _w(at, "number_input", "ni_rpm_hmi").set_value(EXPECTED_RPM)
    dens_w = _w(at, "number_input", "fd_dens_1")
    assert dens_w is not None, "feeder density widget missing"
    dens_w.set_value(EXPECTED_DENS)
    at.run()

    _w(at, "text_input", "apply_label").set_value(LABEL)
    _w(at, "button", "btn_apply_state").click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    from AgentIndustrial_v1.core.applied_state import get_applied
    snap = get_applied(at.session_state)
    assert snap is not None and snap.label == LABEL
    assert snap.screw_rpm == EXPECTED_RPM
    assert snap.feeders[0]["enabled"] is True
    assert abs(snap.feeders[0]["mass_flow_g_per_min"] - EXPECTED_FLOW_G_MIN) < 1e-2
    assert abs(snap.feeders[0]["density_g_per_cm3"] - EXPECTED_DENS) < 1e-6

    # --- Profile fresh session: add elements, Save --------------------------
    from screw_logic import count_user_elements
    p = _new(PROFILE)
    p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    for _ in range(N_ELEMENTS):
        _w(p, "button", "plus1_1").click()
        p.run()
    assert count_user_elements(list(p.session_state["screw_config"])) == N_ELEMENTS
    _w(p, "button", "btn_profile_save").click()
    p.run()
    snap_p = get_applied(p.session_state)
    assert count_user_elements(snap_p.screw_config) == N_ELEMENTS
    assert snap_p.label == LABEL          # label preserved through Profile save
    assert snap_p.screw_rpm == EXPECTED_RPM
    return snap_p


def test_durable_backend_active():
    """The external store backend is configured & durable (Supabase stand-in)."""
    import persistence
    assert persistence.is_durable() is True
    assert persistence.backend_name() in ("supabase", "external-file")


def test_settings_rereads_widgets_after_refresh(_committed):
    """Step 13: fresh Settings session re-reads rpm/coeff/feeder/density."""
    at = _new(SETTINGS)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert _w(at, "number_input", "feeder_rpm").value == EXPECTED_RPM
    assert _w(at, "number_input", "feeder_calib_g_h_per_rpm").value == EXPECTED_COEFF
    assert _w(at, "number_input", "ni_rpm_hmi").value == EXPECTED_RPM
    fd_en = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
    assert fd_en.value is True
    assert _w(at, "number_input", "fd_dens_1").value == EXPECTED_DENS
    # The unsaved banner must NOT appear (widgets == applied snapshot).
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    from AgentIndustrial_v1.core.applied_state import has_unsaved_changes
    state = build_state_from_widgets(at.session_state)
    assert has_unsaved_changes(at.session_state, state) is False


def test_profile_rereads_elements_after_refresh(_committed):
    """Step 14: fresh Profile session still shows the saved screw elements."""
    from screw_logic import count_user_elements
    p = _new(PROFILE)
    p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    assert count_user_elements(list(p.session_state["screw_config"])) == N_ELEMENTS


def test_supervision_reads_snapshot_after_refresh(_committed):
    """Step 15: Supervision shows label + RPM 100 + flow 4.17 g/min."""
    s = _new(SUPERVISION)
    s.run()
    assert not s.exception, [str(e.value) for e in s.exception]
    text = _visible(s)
    assert LABEL in text, "client label not visible on Supervision"
    assert "100" in text                       # RPM
    assert ("4.17" in text or "4.2" in text), "flow 4.17 g/min not visible"


def test_engine_reads_snapshot_after_refresh(_committed):
    """Step 15: Process Engine reads the saved profile (not empty state)."""
    m = _new(ENGINE)
    m.run()
    assert not m.exception, [str(e.value) for e in m.exception]
    text = _visible(m)
    assert "No process profile" not in text and "Aucun profil" not in text
    assert "100" in text                       # rpm propagated


def test_history_has_same_snapshot(_committed):
    """Step 11: History lists the same labelled run."""
    h = _new(HISTORY)
    h.run()
    assert not h.exception, [str(e.value) for e in h.exception]
    assert LABEL in _visible(h), "client label not in History"
