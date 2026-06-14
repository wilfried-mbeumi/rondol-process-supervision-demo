"""Diagnostic prod flow — real widget interactions, isolated disk, field diff.

Run: python tests/_diag_prod_flow.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Isolated disk mirrors BEFORE imports that resolve paths lazily (env read at call time).
_tmp = tempfile.mkdtemp(prefix="rondol_diag_")
os.environ["RONDOL_RUN_STATE_PATH"] = str(Path(_tmp) / "current_run_state.json")
os.environ["RONDOL_APPLIED_STATE_PATH"] = str(Path(_tmp) / "applied_state.json")
os.environ["RONDOL_HISTORY_PATH"] = str(Path(_tmp) / "process_history.json")

from streamlit.testing.v1 import AppTest

SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
MOTEUR = str(APP / "pages" / "5_Process_Engine.py")
SUPERVISION = str(APP / "Supervision.py")


def widget_by_key(at, kind, key):
    for w in getattr(at, kind):
        if w.key == key:
            return w
    return None


print("=== PHASE 1: Settings — set widgets via REAL widget API, click Save ===")
at = AppTest.from_file(SETTINGS, default_timeout=120)
at.run()
assert not at.exception, [str(e.value) for e in at.exception]

# Enable feeder #1 via its checkbox/toggle widget
fd_en = widget_by_key(at, "checkbox", "fd_en_1") or widget_by_key(at, "toggle", "fd_en_1")
print("fd_en_1 widget found:", fd_en is not None)
if fd_en is not None:
    fd_en.set_value(True)
    at.run()

rpm_w = widget_by_key(at, "number_input", "feeder_rpm")
coeff_w = widget_by_key(at, "number_input", "feeder_calib_g_h_per_rpm")
screw_rpm_w = widget_by_key(at, "number_input", "ni_rpm_hmi")
print("widgets:", rpm_w is not None, coeff_w is not None, screw_rpm_w is not None)
if rpm_w: rpm_w.set_value(100.0)
if coeff_w: coeff_w.set_value(2.5)
if screw_rpm_w: screw_rpm_w.set_value(100.0)
at.run()

label_w = widget_by_key(at, "text_input", "apply_label")
if label_w: label_w.set_value("TEST_SYNC_MANAGER_001")

save_btn = widget_by_key(at, "button", "btn_apply_state")
assert save_btn is not None
save_btn.click()
at.run()
assert not at.exception, [str(e.value) for e in at.exception]

from AgentIndustrial_v1.core.applied_state import get_applied, snapshot_to_dict
snap1 = get_applied(at.session_state)
print("snapshot after save:", snap1 is not None, "label:", snap1.label if snap1 else None)
print("  feeders[0]:", snap1.feeders[0] if snap1 and snap1.feeders else None)
print("  screw_rpm:", snap1.screw_rpm if snap1 else None)
print("applied disk exists:", Path(os.environ["RONDOL_APPLIED_STATE_PATH"]).exists())
print("operator disk exists:", Path(os.environ["RONDOL_RUN_STATE_PATH"]).exists())
if Path(os.environ["RONDOL_RUN_STATE_PATH"]).exists():
    import json
    op = json.loads(Path(os.environ["RONDOL_RUN_STATE_PATH"]).read_text(encoding="utf-8"))
    print("  operator store keys subset:", {k: op.get(k) for k in ("feeder_rpm", "feeder_calib_g_h_per_rpm", "screw_rpm", "fd_en_1")})

print()
print("=== PHASE 2: Profile fresh session (navigation w/ purge ≈ new AppTest + shared disk) ===")
p = AppTest.from_file(PROFILE, default_timeout=120)
p.run()
assert not p.exception, [str(e.value) for e in p.exception]
cfg0 = list(p.session_state["screw_config"]) if "screw_config" in p.session_state else []
from screw_logic import count_user_elements
print("profile elements on load:", count_user_elements(cfg0))
plus = widget_by_key(p, "button", "plus1_1")
print("plus1_1 found:", plus is not None)
if plus:
    plus.click(); p.run()
    plus = widget_by_key(p, "button", "plus1_1"); plus.click(); p.run()
print("after +2:", count_user_elements(list(p.session_state["screw_config"])))
psave = widget_by_key(p, "button", "btn_profile_save")
print("profile save found:", psave is not None)
if psave:
    psave.click(); p.run()
snapP = get_applied(p.session_state)
print("snapshot after profile save: elements:", count_user_elements(snapP.screw_config) if snapP else None,
      "label:", snapP.label if snapP else None, "rpm:", snapP.screw_rpm if snapP else None,
      "feeder0 flow:", snapP.feeders[0]["mass_flow_g_per_min"] if snapP and snapP.feeders else None)

print()
print("=== PHASE 3: REFRESH — fresh Settings session, check widget values + unsaved banner ===")
at2 = AppTest.from_file(SETTINGS, default_timeout=120)
at2.run()
assert not at2.exception, [str(e.value) for e in at2.exception]
for key in ("feeder_rpm", "feeder_calib_g_h_per_rpm", "ni_rpm_hmi"):
    w = widget_by_key(at2, "number_input", key)
    print(f"  widget {key}: value={w.value if w else 'WIDGET NOT FOUND'}")
fd_en2 = widget_by_key(at2, "checkbox", "fd_en_1") or widget_by_key(at2, "toggle", "fd_en_1")
print("  fd_en_1:", fd_en2.value if fd_en2 else "NOT FOUND")

from AgentIndustrial_v1.core.editing_state import build_state_from_widgets
from AgentIndustrial_v1.core.applied_state import has_unsaved_changes, take_snapshot
state2 = build_state_from_widgets(at2.session_state)
snap2 = get_applied(at2.session_state)
print("  snapshot restored:", snap2 is not None, "label:", snap2.label if snap2 else None)
print("  unsaved banner would show:", has_unsaved_changes(at2.session_state, state2))
if snap2 is not None:
    a = {k: v for k, v in asdict(snap2).items() if k not in ("timestamp_iso", "label")}
    b = {k: v for k, v in asdict(take_snapshot(state2)).items() if k not in ("timestamp_iso", "label")}
    for k in a:
        if a[k] != b[k]:
            print(f"  DIFF {k}:")
            print(f"    applied: {a[k]}")
            print(f"    widgets: {b[k]}")

print()
print("=== PHASE 4: REFRESH — fresh Moteur session ===")
m = AppTest.from_file(MOTEUR, default_timeout=120)
m.run()
assert not m.exception, [str(e.value) for e in m.exception]
infos = [str(i.value) for i in m.info]
print("  info boxes:", infos[:2])
print("  'No process profile' shown:", any("No process profile" in s or "Aucun profil" in s for s in infos))

print()
print("=== PHASE 5: REFRESH — fresh Supervision session ===")
s = AppTest.from_file(SUPERVISION, default_timeout=120)
s.run()
assert not s.exception, [str(e.value) for e in s.exception]
caps = [str(c.value) for c in s.caption]
runlabels = [c for c in caps if "TEST_SYNC_MANAGER_001" in c or "RUN" in c.upper()]
print("  run label captions:", runlabels[:3])
print()
print("DONE diag tmp:", _tmp)
