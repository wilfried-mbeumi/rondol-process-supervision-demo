"""Detailed leak finder — shows context around each match."""
from __future__ import annotations
import sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from streamlit.testing.v1 import AppTest

PAGES = {
    "Supervision": str(APP / "Supervision.py"),
    "Profile": str(APP / "pages" / "1_Profile.py"),
    "Settings": str(APP / "pages" / "2_Settings.py"),
}

CHECK = ["alerte", "Procédé", "ACTION"]

def _rendered_text(at):
    chunks = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except: pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except: pass
    try:
        for m in at.metric:
            chunks.append(str(getattr(m, "label", "")))
            chunks.append(str(getattr(m, "value", "")))
    except: pass
    return chunks

def _load_en(path):
    at = AppTest.from_file(path)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at.run(timeout=120)

for name, path in PAGES.items():
    at = _load_en(path)
    if at.exception:
        print(f"{name}: EXCEPTION")
        continue
    chunks = _rendered_text(at)
    for word in CHECK:
        for i, chunk in enumerate(chunks):
            if word in chunk:
                ctx = chunk[:200].replace('\n', ' ')
                print(f"[{name}] '{word}' in chunk#{i}: ...{ctx}...")
