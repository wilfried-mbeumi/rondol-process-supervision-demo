"""test_persistence_durable.py — persistance DURABLE du snapshot validé (P0).

Preuve de la source de vérité : chaque test ÉCRIT via les pages réelles puis
DÉTRUIT les fichiers locaux éphémères (simulation reboot/redeploy Streamlit
Cloud) avant de relire dans une session neuve. Si les données reviennent,
elles ne peuvent provenir QUE du backend durable — jamais de session_state ni
du JSON local.

Backends testés :
  - external-file (env RONDOL_EXTERNAL_STORE_PATH) — stand-in durable réel ;
  - supabase (REST) — transport HTTP mocké (aucun réseau en CI).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
SUPERVISION = str(APP / "Supervision.py")
PROCESS_ENGINE = str(APP / "pages" / "5_Process_Engine.py")
HISTORY = str(APP / "pages" / "4_History.py")

RUN_LABEL = "TEST_SYNC_MANAGER_001"


@pytest.fixture()
def _disk(tmp_path, monkeypatch):
    """Disque éphémère isolé + backend durable external-file isolé."""
    local = tmp_path / "ephemeral"
    local.mkdir()
    durable = tmp_path / "durable_store.json"
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(local / "current_run_state.json"))
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(local / "applied_state.json"))
    monkeypatch.setenv("RONDOL_HISTORY_PATH", str(local / "history.json"))
    monkeypatch.setenv("RONDOL_EXTERNAL_STORE_PATH", str(durable))
    return {"local": local, "durable": durable}


def _w(at, kind, key):
    for el in getattr(at, kind):
        if el.key == key:
            return el
    return None


def _save_settings_with_widgets(at):
    fd_en = _w(at, "toggle", "fd_en_1") or _w(at, "checkbox", "fd_en_1")
    fd_en.set_value(True)
    at.run()
    for key, val in (("feeder_rpm", 100.0),
                     ("feeder_calib_g_h_per_rpm", 2.5),
                     ("ni_rpm_hmi", 100.0)):
        _w(at, "number_input", key).set_value(val)
    at.run()
    _w(at, "text_input", "apply_label").set_value(RUN_LABEL)
    _w(at, "button", "btn_apply_state").click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]


def _fill_profile_and_save(p):
    from screw_logic import MAX_USER_ELEMENTS, count_user_elements
    for _ in range(50):
        n = count_user_elements(list(p.session_state["screw_config"]))
        if n >= MAX_USER_ELEMENTS:
            break
        key = "plus4_1" if MAX_USER_ELEMENTS - n >= 4 else "plus1_1"
        b = _w(p, "button", key)
        if b is None or b.disabled:
            break
        b.click()
        p.run()
    _w(p, "button", "btn_profile_save").click()
    p.run()
    assert not p.exception


def _simulate_reboot(disk):
    """Reboot/redeploy Streamlit Cloud = disque éphémère VIDÉ. Seul le backend
    durable survit."""
    for f in disk["local"].glob("*"):
        f.unlink()
    assert not (disk["local"] / "applied_state.json").exists()
    assert not (disk["local"] / "current_run_state.json").exists()
    assert disk["durable"].exists(), "durable backend must hold the snapshot"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_reboot_survival_full_e2e(_disk):
    """E2E manager : Save Settings → Save Profile → REBOOT (disque local vidé)
    → toutes les pages relisent l'état depuis la persistance DURABLE."""
    from AgentIndustrial_v1.core.applied_state import get_applied
    from screw_logic import MAX_USER_ELEMENTS, count_total_elements, count_user_elements

    # 1-2. Save Settings + Save Profile (vrais widgets)
    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    _save_settings_with_widgets(at)
    p = AppTest.from_file(PROFILE, default_timeout=120)
    p.run()
    _fill_profile_and_save(p)

    # Le backend durable contient bien le snapshot complet
    payload = json.loads(_disk["durable"].read_text(encoding="utf-8"))
    assert payload["label"] == RUN_LABEL
    assert payload["screw_rpm"] == 100.0
    assert payload["feeder_calibrations"]["1"] == {"rpm": 100.0, "coeff": 2.5}

    # 3. REBOOT — disque éphémère vidé, sessions neuves
    _simulate_reboot(_disk)

    # 4. Settings relit RPM/coeff/feeder depuis la persistance durable
    at2 = AppTest.from_file(SETTINGS, default_timeout=120)
    at2.run()
    assert not at2.exception, [str(e.value) for e in at2.exception]
    assert _w(at2, "number_input", "feeder_rpm").value == 100.0
    assert _w(at2, "number_input", "feeder_calib_g_h_per_rpm").value == 2.5
    assert _w(at2, "number_input", "ni_rpm_hmi").value == 100.0
    fd = _w(at2, "toggle", "fd_en_1") or _w(at2, "checkbox", "fd_en_1")
    assert bool(fd.value), "feeder #1 must come back active after reboot"

    # 5. Profile relit les 40/40 (39 utilisateur + tip)
    p2 = AppTest.from_file(PROFILE, default_timeout=120)
    p2.run()
    assert not p2.exception
    cfg = list(p2.session_state["screw_config"])
    assert count_user_elements(cfg) == MAX_USER_ELEMENTS
    assert count_total_elements(cfg) == 40.0

    # 6. Supervision : label TEST_SYNC_MANAGER_001 revenu
    s = AppTest.from_file(SUPERVISION, default_timeout=120)
    s.run()
    assert not s.exception
    assert RUN_LABEL in "\n".join(str(c.value) for c in s.caption)

    # 7. Process Engine : jamais « No process profile configured »
    m = AppTest.from_file(PROCESS_ENGINE, default_timeout=120)
    m.run()
    assert not m.exception
    infos = "\n".join(str(i.value) for i in m.info)
    assert "No process profile" not in infos and "Aucun profil" not in infos

    # 8. History : même snapshot
    h = AppTest.from_file(HISTORY, default_timeout=120)
    h.run()
    assert not h.exception
    snap_h = get_applied(h.session_state)
    assert snap_h is not None and snap_h.label == RUN_LABEL
    assert count_user_elements(snap_h.screw_config) == MAX_USER_ELEMENTS


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_kpis_identical_on_all_pages_after_reboot(_disk):
    """RPM 100, coeff 2.5, feed 4.17 g/min, éléments 40, SME identiques partout
    après reboot — relus depuis la persistance durable."""
    from AgentIndustrial_v1.core.current_run_state import CALCULATED, build_current_run_state

    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    _save_settings_with_widgets(at)
    p = AppTest.from_file(PROFILE, default_timeout=120)
    p.run()
    _fill_profile_and_save(p)
    _simulate_reboot(_disk)

    sme_values = set()
    for page in (SUPERVISION, PROCESS_ENGINE, SETTINGS, PROFILE, HISTORY):
        a = AppTest.from_file(page, default_timeout=120)
        a.run()
        assert not a.exception, f"{page}: {[str(e.value) for e in a.exception]}"
        crs = build_current_run_state(a.session_state)
        assert crs.feed_rate.source == CALCULATED, f"{page}: feed must be CALCULATED"
        assert float(crs.feed_rate.value) / 60.0 == pytest.approx(250.0 / 60.0, abs=0.01)
        assert float(crs.process_parameters["screw_rpm"].value) == 100.0
        assert float(crs.calculated_outputs["n_elements"].value) == 40.0
        sme_values.add(round(float(crs.calculated_outputs["sme"].value), 6))
    assert len(sme_values) == 1, f"SME must be identical on every page: {sme_values}"


def test_load_without_any_session(_disk):
    """Absence totale de session_state : la persistance seule reconstruit
    l'état complet (preuve que la source de vérité n'est PAS la session)."""
    import persistence
    from AgentIndustrial_v1.core.applied_state import snapshot_from_dict, snapshot_to_dict, take_snapshot
    from AgentIndustrial_v1.core.state_sync import state_from_session
    from screw_logic import add_elements_atomic, new_empty_configuration

    # Écrire directement via l'API persistence (aucune session impliquée)
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)
    state = state_from_session({})  # défauts purs
    state.screw_config = cfg
    state.screw_rpm = 100.0
    snap_dict = snapshot_to_dict(take_snapshot(state, label=RUN_LABEL))
    snap_dict["feeder_calibrations"] = {"1": {"rpm": 100.0, "coeff": 2.5}}
    backend = persistence.save_applied_state(snap_dict)
    assert backend == "external-file"
    assert persistence.has_applied_state()

    # Reboot : local vidé
    _simulate_reboot(_disk)

    # Relecture SANS session : load → snapshot complet
    data = persistence.load_applied_state()
    assert data is not None
    snap = snapshot_from_dict(data)
    assert snap.label == RUN_LABEL
    assert snap.screw_rpm == 100.0
    assert snap.feeder_calibrations["1"]["coeff"] == 2.5

    # Et la chaîne pages (session VIDE) : state_from_session relit la durable
    session: dict = {}
    st2 = state_from_session(session)
    assert st2.screw_rpm == 100.0
    assert list(st2.screw_config) == list(cfg)


def test_supabase_backend_mocked(monkeypatch, tmp_path):
    """Backend Supabase : upsert + relecture via REST (transport HTTP mocké)."""
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(tmp_path / "applied.json"))
    monkeypatch.delenv("RONDOL_EXTERNAL_STORE_PATH", raising=False)
    monkeypatch.setenv("RONDOL_SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("RONDOL_SUPABASE_KEY", "fake-key")

    import persistence

    store: dict = {}
    calls: list = []

    class _Resp:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload
        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(("POST", url, headers, json))
        assert url == "https://fake.supabase.co/rest/v1/rondol_state"
        assert headers["apikey"] == "fake-key"
        assert headers["Prefer"] == "resolution=merge-duplicates"
        store["payload"] = json[0]["payload"]
        return _Resp(201)

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(("GET", url, headers, params))
        assert params == {"key": "eq.applied_state", "select": "payload"}
        if "payload" not in store:
            return _Resp(200, [])
        return _Resp(200, [{"payload": store["payload"]}])

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    assert persistence.backend_name() == "supabase"
    assert persistence.is_durable()

    payload = {"label": RUN_LABEL, "screw_config": [0] * 81, "screw_rpm": 100.0}
    assert persistence.save_applied_state(payload) == "supabase"

    # Reboot : JSON local supprimé → la relecture vient du backend mocké
    (tmp_path / "applied.json").unlink()
    data = persistence.load_applied_state()
    assert data is not None and data["label"] == RUN_LABEL
    assert any(c[0] == "GET" for c in calls)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_warning_when_no_durable_backend(tmp_path, monkeypatch):
    """Sans backend durable : avertissement explicite sur Settings (anglais)."""
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "crs.json"))
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(tmp_path / "applied.json"))
    monkeypatch.setenv("RONDOL_HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.delenv("RONDOL_EXTERNAL_STORE_PATH", raising=False)
    monkeypatch.delenv("RONDOL_SUPABASE_URL", raising=False)
    monkeypatch.delenv("RONDOL_SUPABASE_KEY", raising=False)

    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    warnings = "\n".join(str(w.value) for w in at.warning)
    assert "Persistent storage not configured" in warnings, \
        "Settings must warn when only the local fallback is available"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_no_warning_when_durable_backend_active(_disk):
    """Avec backend durable : pas d'avertissement, mention du backend actif."""
    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    assert not at.exception
    warnings = "\n".join(str(w.value) for w in at.warning)
    assert "Persistent storage not configured" not in warnings
    caps = "\n".join(str(c.value) for c in at.caption)
    assert "external-file" in caps, "active durable backend must be displayed"
