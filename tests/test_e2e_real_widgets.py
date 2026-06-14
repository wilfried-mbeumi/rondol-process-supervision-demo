"""test_e2e_real_widgets.py — E2E manager 24 étapes avec de VRAIS widgets.

Différence clé avec test_e2e_sync.py : aucune injection directe de
session_state pour les saisies opérateur. Les valeurs passent par l'API widget
AppTest (`number_input.set_value`, `button.click`, `toggle.set_value`) — le
même chemin que la prod. Chaque « refresh navigateur » = nouvelle session
AppTest, seuls les miroirs disque survivent (applied_state.json +
current_run_state.json isolés par test via les variables d'environnement).

Scénario manager (P0 2026-06-12) :
  1-8   Settings : English défaut, run TEST_SYNC_MANAGER_001, feeder #1 actif,
        RPM=100, coeff=2.5, débit 250 g/h = 4.17 g/min, Save.
  9-11  Profile : remplir la vis jusqu'à la capacité (40 affiché tip inclus),
        Save Profile.
  12-15 Supervision : label run visible, débit 4.17, profil lu.
  16-18 Process Engine : PAS de « No process profile configured », même profil.
  19-20 History : snapshot identique.
  21-24 Refresh (sessions neuves) : Settings/Profile/Supervision/Process Engine
        relisent les mêmes valeurs.
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


@pytest.fixture(autouse=True)
def _isolate_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "crs.json"))
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(tmp_path / "applied.json"))
    monkeypatch.setenv("RONDOL_HISTORY_PATH", str(tmp_path / "history.json"))


def _w(at, kind, key):
    for el in getattr(at, kind):
        if el.key == key:
            return el
    return None


def _configure_and_save_settings(at):
    """Steps 3-8: real widget interactions on Settings, then Save click."""
    fd_en = _w(at, "toggle", "fd_en_1") or _w(at, "checkbox", "fd_en_1")
    assert fd_en is not None, "fd_en_1 toggle must exist"
    fd_en.set_value(True)
    at.run()

    for key, val in (("feeder_rpm", 100.0),
                     ("feeder_calib_g_h_per_rpm", 2.5),
                     ("ni_rpm_hmi", 100.0)):
        w = _w(at, "number_input", key)
        assert w is not None, f"widget {key} must exist"
        w.set_value(val)
    at.run()

    label_w = _w(at, "text_input", "apply_label")
    assert label_w is not None
    label_w.set_value(RUN_LABEL)
    save = _w(at, "button", "btn_apply_state")
    assert save is not None
    save.click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_manager_24_steps_real_widgets():
    from AgentIndustrial_v1.core.applied_state import get_applied
    from screw_logic import (
        MAX_USER_ELEMENTS,
        TOTAL_ELEMENT_CAPACITY,
        count_total_elements,
        count_user_elements,
    )

    # ── Steps 1-2 : nouvelle session, direct /Settings ──
    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    # ── Step 3 : English actif par défaut ──
    assert at.session_state["ui_lang"] == "en"

    # ── Steps 4-8 : config réelle + Save ──
    at = _configure_and_save_settings(at)

    snap = get_applied(at.session_state)
    assert snap is not None and snap.label == RUN_LABEL
    assert snap.screw_rpm == 100.0
    # Débit étalonné : 100 RPM × 2.5 g/h/RPM = 250 g/h = 4.1667 g/min
    assert snap.feeders[0]["mass_flow_g_per_min"] == pytest.approx(250.0 / 60.0, abs=0.01)
    # Étalonnage DANS le snapshot (source de vérité unique après refresh)
    assert snap.feeder_calibrations.get("1", {}).get("rpm") == 100.0
    assert snap.feeder_calibrations.get("1", {}).get("coeff") == 2.5

    # ── Steps 9-10 : Profile (session neuve = navigation pire-cas), +éléments
    #     jusqu'à saturation → compteur affiché = capacité totale 40 ──
    p = AppTest.from_file(PROFILE, default_timeout=120)
    p.run()
    assert not p.exception, [str(e.value) for e in p.exception]
    # +4 convoyage tant que ≥4 slots restent, puis +1 jusqu'à saturation (39)
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
    cfg = list(p.session_state["screw_config"])
    assert count_user_elements(cfg) == MAX_USER_ELEMENTS, \
        f"screw must be full: {count_user_elements(cfg)}/{MAX_USER_ELEMENTS}"
    # Capacité TOTALE affichée = 40 (39 utilisateur + tip)
    assert count_total_elements(cfg) == TOTAL_ELEMENT_CAPACITY == 40.0

    # ── Step 11 : Save Profile (clic réel) ──
    psave = _w(p, "button", "btn_profile_save")
    assert psave is not None, "Profile Save button must exist"
    psave.click()
    p.run()
    assert not p.exception
    snap2 = get_applied(p.session_state)
    assert snap2 is not None
    assert count_user_elements(snap2.screw_config) == MAX_USER_ELEMENTS
    assert snap2.label == RUN_LABEL, "Profile save must preserve the run label"
    assert snap2.screw_rpm == 100.0, "Profile save must preserve Settings RPM"
    assert snap2.feeder_calibrations.get("1", {}).get("coeff") == 2.5, \
        "Profile save must preserve feeder calibration"

    # ── Steps 12-15 : Supervision (session neuve) ──
    s = AppTest.from_file(SUPERVISION, default_timeout=120)
    s.run()
    assert not s.exception, [str(e.value) for e in s.exception]
    # Le label opérateur est désormais rendu dans le bandeau ÉTAT OPÉRATEUR
    # ACTIF (st.html), plus seulement en caption — on cherche dans les deux.
    caps = "\n".join(str(c.value) for c in s.caption) + "\n" + "\n".join(
        str(getattr(h, "body", getattr(h, "value", ""))) for h in s.get("html")
    )
    assert RUN_LABEL in caps, "Run label must be visible on Supervision"
    snap_s = get_applied(s.session_state)
    assert count_user_elements(snap_s.screw_config) == MAX_USER_ELEMENTS
    assert snap_s.feeders[0]["mass_flow_g_per_min"] == pytest.approx(250.0 / 60.0, abs=0.01)

    # ── Steps 16-18 : Process Engine (session neuve) ──
    m = AppTest.from_file(PROCESS_ENGINE, default_timeout=120)
    m.run()
    assert not m.exception, [str(e.value) for e in m.exception]
    infos = "\n".join(str(i.value) for i in m.info)
    assert "No process profile" not in infos and "Aucun profil" not in infos, \
        "Process Engine must NOT show the empty-profile message after save"
    assert count_user_elements(list(m.session_state["screw_config"])) == MAX_USER_ELEMENTS

    # ── Steps 19-20 : History (session neuve) — même snapshot ──
    h = AppTest.from_file(HISTORY, default_timeout=120)
    h.run()
    assert not h.exception, [str(e.value) for e in h.exception]
    snap_h = get_applied(h.session_state)
    assert snap_h is not None and snap_h.label == RUN_LABEL
    assert count_user_elements(snap_h.screw_config) == MAX_USER_ELEMENTS

    # ── Steps 21-23 : REFRESH → Settings relit les valeurs sauvegardées ──
    at2 = AppTest.from_file(SETTINGS, default_timeout=120)
    at2.run()
    assert not at2.exception, [str(e.value) for e in at2.exception]
    rpm_w = _w(at2, "number_input", "feeder_rpm")
    coeff_w = _w(at2, "number_input", "feeder_calib_g_h_per_rpm")
    screw_rpm_w = _w(at2, "number_input", "ni_rpm_hmi")
    fd_en2 = _w(at2, "toggle", "fd_en_1") or _w(at2, "checkbox", "fd_en_1")
    assert rpm_w is not None and rpm_w.value == 100.0, "feeder RPM 100 must survive refresh"
    assert coeff_w is not None and coeff_w.value == 2.5, "coeff 2.5 must survive refresh"
    assert screw_rpm_w is not None and screw_rpm_w.value == 100.0
    assert fd_en2 is not None and bool(fd_en2.value), "feeder #1 must stay active"
    # Le bandeau « UNSAVED CHANGES » ne doit PAS s'afficher après un refresh
    from AgentIndustrial_v1.core.applied_state import has_unsaved_changes
    from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
    assert not has_unsaved_changes(
        at2.session_state, build_state_from_widgets(at2.session_state)
    ), "Settings must come back clean (no unsaved-changes banner) after refresh"

    # ── Step 24 : Profile / Supervision / Process Engine après refresh ──
    p2 = AppTest.from_file(PROFILE, default_timeout=120)
    p2.run()
    assert not p2.exception
    assert count_user_elements(list(p2.session_state["screw_config"])) == MAX_USER_ELEMENTS, \
        "Profile elements must survive refresh"

    s2 = AppTest.from_file(SUPERVISION, default_timeout=120)
    s2.run()
    assert not s2.exception
    _s2_text = "\n".join(str(c.value) for c in s2.caption) + "\n" + "\n".join(
        str(getattr(h, "body", getattr(h, "value", ""))) for h in s2.get("html")
    )
    assert RUN_LABEL in _s2_text

    m2 = AppTest.from_file(PROCESS_ENGINE, default_timeout=120)
    m2.run()
    assert not m2.exception
    infos2 = "\n".join(str(i.value) for i in m2.info)
    assert "No process profile" not in infos2 and "Aucun profil" not in infos2


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_after_refresh_shows_saved_not_stale_store():
    """Un store opérateur DIVERGENT du snapshot ne doit JAMAIS gagner après
    refresh : le snapshot validé (applied_state.json) est prioritaire."""
    import json
    import os

    from AgentIndustrial_v1.core.applied_state import get_applied

    # 1. Config réelle + save
    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    _configure_and_save_settings(at)

    # 2. Corrompre le store opérateur disque (simule un store périmé/divergent)
    crs_path = Path(os.environ["RONDOL_RUN_STATE_PATH"])
    store = json.loads(crs_path.read_text(encoding="utf-8"))
    store["feeder_rpm"] = 0.0
    store["feeder_calib_g_h_per_rpm"] = 0.0
    store["screw_config"] = []
    crs_path.write_text(json.dumps(store), encoding="utf-8")

    # 3. Refresh → le snapshot doit gagner sur le store corrompu
    at2 = AppTest.from_file(SETTINGS, default_timeout=120)
    at2.run()
    assert not at2.exception, [str(e.value) for e in at2.exception]
    rpm_w = _w(at2, "number_input", "feeder_rpm")
    coeff_w = _w(at2, "number_input", "feeder_calib_g_h_per_rpm")
    assert rpm_w.value == 100.0, "snapshot calibration must beat stale store"
    assert coeff_w.value == 2.5, "snapshot calibration must beat stale store"
    snap = get_applied(at2.session_state)
    assert snap is not None and snap.feeder_calibrations["1"]["coeff"] == 2.5


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_kpi_coherence_across_pages_after_save():
    """Mêmes KPIs partout : feed 4.17 g/min, RPM 100, éléments 40 (tip incl.)."""
    from AgentIndustrial_v1.core.current_run_state import CALCULATED, build_current_run_state
    from screw_logic import MAX_USER_ELEMENTS, count_user_elements

    at = AppTest.from_file(SETTINGS, default_timeout=120)
    at.run()
    _configure_and_save_settings(at)

    # Profil plein + save (vrais clics)
    p = AppTest.from_file(PROFILE, default_timeout=120)
    p.run()
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

    # Chaque page (session neuve) construit le même CurrentRunState
    expected_feed_g_min = 250.0 / 60.0
    for page in (SUPERVISION, PROCESS_ENGINE, SETTINGS, PROFILE):
        a = AppTest.from_file(page, default_timeout=120)
        a.run()
        assert not a.exception, f"{page}: {[str(e.value) for e in a.exception]}"
        crs = build_current_run_state(a.session_state)
        assert crs.feed_rate.source == CALCULATED, f"{page}: feed must be CALCULATED"
        assert float(crs.feed_rate.value) / 60.0 == pytest.approx(expected_feed_g_min, abs=0.01), \
            f"{page}: feed rate mismatch"
        assert float(crs.process_parameters["screw_rpm"].value) == 100.0, f"{page}: RPM mismatch"
        assert float(crs.calculated_outputs["n_elements"].value) == 40.0, \
            f"{page}: elements count must read 40 (tip incl.)"
