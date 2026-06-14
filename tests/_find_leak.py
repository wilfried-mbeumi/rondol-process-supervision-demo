"""Locate exact lines containing 'alerte'/'ACTION' in EN-rendered pages."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _validate_en_strict import PAGES, _load_en, _rendered_text  # type: ignore

for name in ("Supervision", "Profile", "Settings"):
    at = _load_en(PAGES[name])
    text = _rendered_text(at)
    print(f"=== {name} ===")
    for line in text.splitlines():
        if "alerte" in line or "ACTION" in line:
            print("   >>", line.strip()[:220])
