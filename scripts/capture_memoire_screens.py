# -*- coding: utf-8 -*-
"""Capture les 6 pages Streamlit pour le mémoire (Playwright)."""
from __future__ import annotations
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "memoire_captures"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8765"

PAGES = [
    ("/", "cap_supervision.png"),
    ("/Profile", "cap_profile.png"),
    ("/Settings", "cap_settings.png"),
    ("/Run_Analysis", "cap_run_analysis.png"),
    ("/History", "cap_history.png"),
    ("/Process_Engine", "cap_process_engine.png"),
]

HIDE_CSS = """
header[data-testid="stHeader"]{display:none!important;}
[data-testid="stToolbar"]{display:none!important;}
[data-testid="stStatusWidget"]{display:none!important;}
#MainMenu, footer{display:none!important;}
[data-testid="manage-app-button"]{display:none!important;}
"""

def wait_ready(page):
    page.wait_for_load_state("networkidle")
    # attendre la fin du "running"
    for _ in range(40):
        running = page.query_selector('[data-testid="stStatusWidget"]')
        if not running:
            break
        time.sleep(0.5)
    time.sleep(2.5)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1500, "height": 1000},
                                  device_scale_factor=2)
        page = ctx.new_page()
        # première charge complète
        page.goto(BASE, wait_until="domcontentloaded")
        wait_ready(page)
        # Bascule en Français (état conservé dans la session sur toutes les pages)
        try:
            page.get_by_text("Français", exact=True).click(timeout=5000)
            wait_ready(page)
            print("[OK] langue = Français")
        except Exception as exc:
            print(f"[WARN] bascule FR: {exc}")
        for path, fname in PAGES:
            url = BASE + path
            try:
                page.goto(url, wait_until="domcontentloaded")
            except Exception as exc:
                print(f"[WARN] goto {url}: {exc}")
            wait_ready(page)
            page.add_style_tag(content=HIDE_CSS)
            time.sleep(1.0)
            target = OUT / fname
            try:
                page.screenshot(path=str(target), full_page=True)
                print(f"[OK] {fname}")
            except Exception as exc:
                print(f"[ERR] screenshot {fname}: {exc}")
        browser.close()

if __name__ == "__main__":
    main()
