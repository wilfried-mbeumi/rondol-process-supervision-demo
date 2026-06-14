"""Faithful PROD REBOOT reproduction with REAL widgets (the exact client flow).

Streamlit Cloud reboot wipes the ephemeral disk: BOTH current_run_state.json
(operator store) AND applied_state.json (local mirror) vanish. ONLY Supabase
survives (emulated by the external store). We drive the REAL widgets exactly as
the operator does, then wipe ephemeral and inspect the durable snapshot + every
page's ACTUAL rendered widget values.

Run: python tests/_repro_prod_reboot.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_TMP = tempfile.mkdtemp(prefix="rondol_reboot_")
_OP = Path(_TMP) / "current_run_state.json"
_LOCAL_APPLIED = Path(_TMP) / "applied_state.json"
_DURABLE = Path(_TMP) / "durable_store.json"
os.environ["RONDOL_RUN_STATE_PATH"] = str(_OP)
os.environ["RONDOL_APPLIED_STATE_PATH"] = str(_LOCAL_APPLIED)
os.environ["RONDOL_EXTERNAL_STORE_PATH"] = str(_DURABLE)
os.environ["RONDOL_HISTORY_PATH"] = str(Path(_TMP) / "history.json")

from streamlit.testing.v1 import AppTest  # noqa: E402
import screw_logic as _sl  # noqa: E402

SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
SUPERVISION = str(APP / "Supervision.py")
ENGINE = str(APP / "pages" / "5_Process_Engine.py")


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


def _vis(at):
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


print("=== STEP A: Settings — REAL widgets, Save ===")
at = _new(SETTINGS); at.run()
fd = _w(at, "checkbox", "fd_en_1") or _w(at, "toggle", "fd_en_1")
fd.set_value(True); at.run()
_w(at, "number_input", "feeder_rpm").set_value(100.0)
_w(at, "number_input", "feeder_calib_g_h_per_rpm").set_value(2.5)
_w(at, "number_input", "ni_rpm_hmi").set_value(100.0)
_w(at, "number_input", "fd_dens_1").set_value(0.55)
at.run()
_w(at, "text_input", "apply_label").set_value("TEST_FINAL_001")
_w(at, "button", "btn_apply_state").click(); at.run()
print("  Settings saved, exception:", bool(at.exception))

print("=== STEP B: Profile — REAL widgets, add 4 elements, Save ===")
p = _new(PROFILE); p.run()
for _ in range(4):
    _w(p, "button", "plus1_1").click(); p.run()
_w(p, "button", "btn_profile_save").click(); p.run()
print("  Profile saved, exception:", bool(p.exception))

print("\n=== Durable (Supabase) snapshot AFTER both saves ===")
d = json.loads(_DURABLE.read_text(encoding="utf-8"))
print("  label:", d.get("label"))
f0 = (d.get("feeders") or [{}])[0]
print("  feeder0 enabled:", f0.get("enabled"), "density:", f0.get("density_g_per_cm3"), "flow:", f0.get("mass_flow_g_per_min"))
print("  screw_rpm:", d.get("screw_rpm"))
print("  zone_temps_C Z1/Z5:", (d.get("zone_temps_C") or {}).get("Z1"), (d.get("zone_temps_C") or {}).get("Z5"))
print("  screw_config user elements:", _sl.count_user_elements(d.get("screw_config") or []))
print("  feeder_calibrations:", d.get("feeder_calibrations"))

# REBOOT: wipe ephemeral disk; only durable survives.
for pth in (_OP, _LOCAL_APPLIED):
    try:
        pth.unlink()
    except Exception:
        pass
print("\n=== REBOOT done (operator store + local mirror wiped) ===")

print("\n=== FRESH Settings after reboot — ACTUAL widget values ===")
at2 = _new(SETTINGS); at2.run()
for key in ("ni_rpm_hmi", "feeder_rpm", "feeder_calib_g_h_per_rpm", "fd_dens_1", "th_Z1", "th_Z5"):
    w = _w(at2, "number_input", key)
    print(f"  {key:26s} = {w.value if w else 'NOT FOUND'}")
fd2 = _w(at2, "checkbox", "fd_en_1") or _w(at2, "toggle", "fd_en_1")
print(f"  fd_en_1 (feeder ON)        = {fd2.value if fd2 else 'NOT FOUND'}")
cfg2 = list((at2.session_state["screw_config"] if "screw_config" in at2.session_state else []))
print(f"  screw elements             = {_sl.count_user_elements(cfg2)}")

print("\n=== FRESH Profile after reboot ===")
p2 = _new(PROFILE); p2.run()
_pc = p2.session_state["screw_config"] if "screw_config" in p2.session_state else []
print(f"  screw elements             = {_sl.count_user_elements(list(_pc))}")

print("\n=== FRESH Supervision after reboot ===")
s2 = _new(SUPERVISION); s2.run()
st2 = _vis(s2)
print("  label TEST_FINAL_001 visible:", "TEST_FINAL_001" in st2)
print("  '4.17' g/min present       :", "4.17" in st2)
print("  '100' rpm present          :", "100" in st2)
print("  Run #46 demo wording       :", "#46" in st2)

print("\n=== FRESH Process Engine after reboot ===")
e2 = _new(ENGINE); e2.run()
et2 = _vis(e2)
print("  'No process profile'       :", "No process profile" in et2 or "Aucun profil" in et2)
print("  '4.17' or '250' flow       :", "4.17" in et2 or "250" in et2)
print("\nDONE tmp:", _TMP)
