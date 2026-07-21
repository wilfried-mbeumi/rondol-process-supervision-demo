# -*- coding: utf-8 -*-
"""Capture les vues Streamlit du prototype pour le mémoire (Playwright).

Depuis l'ajout de l'authentification (app/auth.py), le script :
  1. capture l'écran de connexion ;
  2. se connecte avec les identifiants de démonstration ;
  3. bascule l'interface en français ;
  4. capture les 7 pages applicatives, dont la page Compte (historique des
     connexions lu depuis la base durable).

Prérequis : application lancée en local sur le port visé.
    $env:PYTHONIOENCODING="utf-8"
    python -m streamlit run app/Supervision.py --server.headless=true --server.port=8765

Usage :
    python scripts/capture_memoire_screens.py [--base http://localhost:8765]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "memoire_captures"
OUT.mkdir(parents=True, exist_ok=True)

DEMO_EMAIL = "demo@rondol.local"
DEMO_PW = "0000"

# IMPORTANT : la navigation se fait en CLIQUANT les liens de la barre latérale.
# Un page.goto() ouvrirait une nouvelle session Streamlit et perdrait
# l'authentification (session_state), ramenant l'écran de connexion.
# Les libellés de la barre latérale viennent des noms de fichiers (anglais),
# indépendamment de la langue d'affichage du contenu.
PAGES = [
    ("Supervision", "cap_supervision.png"),
    ("Profile", "cap_profile.png"),
    ("Settings", "cap_settings.png"),
    ("Run Analysis", "cap_run_analysis.png"),
    ("History", "cap_history.png"),
    ("Process Engine", "cap_process_engine.png"),
    ("Account", "cap_account.png"),
]

# Masque le chrome Streamlit pour des captures dignes d'un document pro.
HIDE_CSS = """
header[data-testid="stHeader"]{display:none!important;}
[data-testid="stToolbar"]{display:none!important;}
[data-testid="stStatusWidget"]{display:none!important;}
[data-testid="stDecoration"]{display:none!important;}
[data-testid="stAppDeployButton"]{display:none!important;}
#MainMenu, footer{display:none!important;}
[data-testid="manage-app-button"]{display:none!important;}
"""


def wait_ready(page, extra: float = 2.5) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    for _ in range(40):
        if not page.query_selector('[data-testid="stStatusWidget"]'):
            break
        time.sleep(0.5)
    time.sleep(extra)


def login(page, base: str) -> bool:
    """Renseigne le formulaire de connexion. True si authentifié à la sortie."""
    pwd = page.query_selector('input[type="password"]')
    if not pwd:
        return True  # pas de garde active
    email_input = None
    for el in page.query_selector_all('input[type="text"]'):
        email_input = el
        break
    if email_input is None:
        return False
    email_input.click(); email_input.fill(DEMO_EMAIL)
    pwd.click(); pwd.fill(DEMO_PW)
    btn = (page.query_selector('button:has-text("Se connecter")')
           or page.query_selector('[data-testid="stFormSubmitButton"] button'))
    if btn:
        btn.click()
    else:
        pwd.press("Enter")
    wait_ready(page, extra=3.0)
    return page.query_selector('input[type="password"]') is None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1500, "height": 1000},
                                  device_scale_factor=2)
        page = ctx.new_page()

        # 1) Écran de connexion
        page.goto(base, wait_until="domcontentloaded")
        wait_ready(page)
        if page.query_selector('input[type="password"]'):
            page.add_style_tag(content=HIDE_CSS)
            time.sleep(0.5)
            page.screenshot(path=str(OUT / "cap_login.png"), full_page=False)
            print("[OK] cap_login.png (écran de connexion)")

        # 2) Authentification
        if not login(page, base):
            print("[ERR] connexion impossible — arrêt")
            browser.close()
            return
        print(f"[OK] connecté ({DEMO_EMAIL})")

        # 3) Langue française (le sélecteur est dans la barre latérale)
        try:
            page.get_by_text("Français", exact=True).first.click(timeout=8000)
            wait_ready(page)
            print("[OK] langue = Français")
        except Exception as exc:
            print(f"[WARN] bascule FR : {str(exc)[:70]}")

        # 4) Pages applicatives — navigation par la barre latérale (session gardée)
        for label, fname in PAGES:
            try:
                link = page.get_by_role("link", name=label, exact=True).first
                link.click(timeout=10000)
            except Exception:
                try:
                    page.get_by_text(label, exact=True).first.click(timeout=8000)
                except Exception as exc:
                    print(f"[ERR] navigation « {label} » : {str(exc)[:70]}")
                    continue
            wait_ready(page)
            # Garde-fou : si l'écran de connexion réapparaît, la session est perdue
            if page.query_selector('input[type="password"]'):
                print(f"[ERR] session perdue sur « {label} » — capture annulée")
                continue
            page.add_style_tag(content=HIDE_CSS)
            time.sleep(1.0)
            try:
                page.screenshot(path=str(OUT / fname), full_page=True)
                print(f"[OK] {fname}")
            except Exception as exc:
                print(f"[ERR] {fname} : {str(exc)[:70]}")

        browser.close()
    print(f"\nCaptures : {OUT}")


if __name__ == "__main__":
    main()
