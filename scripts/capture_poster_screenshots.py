"""Capture automatisee des screenshots pour le poster scientifique du 15 mai 2026.

Capture 10 vues :
  01-05  pages de l'app Streamlit (Supervision / Profile / Settings / Analyse_run / Historique)
  06-10  cas tests C1 a C5 (etat charge depuis reports/poster_abstract/cases/states/*.json)

PRE-REQUIS (a executer dans un terminal separe avant de lancer ce script) :
    streamlit run app/Supervision.py --server.port 8501 --server.headless true

Le pre-remplissage de st.session_state depuis un JSON requiert que l'app Streamlit
expose un endpoint dedie OU que le user charge manuellement le JSON via une UI
de debug. Tant que ce mecanisme n'est pas en place, ce script ne capture que les
5 vues statiques (S1-S5) — les 5 cas (C1-C5) sont marques TODO.

Sortie : reports/poster_abstract/screenshots/{NN}_<slug>.png (1920x1080 par defaut).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
SCREEN_DIR = ROOT / "reports" / "poster_abstract" / "screenshots"
CASES_DIR = ROOT / "reports" / "poster_abstract" / "cases" / "states"

VIEWS_STATIC = [
    # (slug, path Streamlit, attente reseau)
    ("01_home_supervision",  "/",                   "Vue Supervision (Home) — agent IA + KPI temps reel"),
    ("02_profile_screw",     "/Profile",            "Configuration du profil de vis pour recette LFP/LATP"),
    ("03_settings_agent",    "/Settings",           "Parametrage seuils + variables surveillees"),
    ("04_analyse_run",       "/Analyse_run",        "Analyse d'un run industriel (avril 2026)"),
    ("05_historique",        "/Historique",         "Historique consolide des runs (duree, T, derive)"),
]

CASES = [
    ("06_case_lithium_baseline",  "case_C1_lithium_baseline.json",      "Cas C1 — baseline lithium, score 65, stable"),
    ("07_case_favorable",          "case_C2_favorable.json",             "Cas C2 — profil optimise, score 82, p_stable=0.91"),
    ("08_case_at_risk",            "case_C3_at_risk.json",               "Cas C3 — surcharge LATP 35 %, alerte Z5 rouge"),
    ("09_case_recommendation",     "case_C4_pre_recommendation.json",    "Cas C4 — recommandation IA hierarchisee"),
    ("10_case_improved",           "case_C5_post_recommendation.json",   "Cas C5 — apres recommandation, score 78, alerte levee"),
]


def capture_view(page, base_url: str, path: str, out_path: Path) -> None:
    page.goto(f"{base_url.rstrip('/')}{path}")
    page.wait_for_load_state("networkidle")
    time.sleep(0.8)  # laisse le temps a Streamlit de finir son rendu reactif
    page.screenshot(path=str(out_path), full_page=True)
    print(f"[OK] {out_path.relative_to(ROOT)}")


def capture_case(page, base_url: str, case_path: Path, slug: str, out_dir: Path) -> None:
    """Charge un cas via query string (necessite que l'app supporte ?case=<id>).
    Cf. ai_tool_architecture.md §2 : a implementer cote Streamlit."""
    case = json.loads(case_path.read_text(encoding="utf-8"))
    query = urlencode({"case": case["case_id"]})
    page.goto(f"{base_url.rstrip('/')}/?{query}")
    page.wait_for_load_state("networkidle")
    time.sleep(1.2)
    page.screenshot(path=str(out_dir / f"{slug}.png"), full_page=True)
    print(f"[OK] {slug}.png  ({case['case_id']})")


def main() -> None:
    p = argparse.ArgumentParser(description="Capture screenshots du poster.")
    p.add_argument("--base-url", default="http://localhost:8501",
                   help="URL de base de l'app Streamlit (default localhost:8501).")
    p.add_argument("--width",  type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--skip-cases", action="store_true",
                   help="Ne capture que les 5 pages statiques (S1-S5).")
    p.add_argument("--out-dir", type=Path, default=SCREEN_DIR)
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERR] playwright requis. pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": args.width, "height": args.height},
                                  device_scale_factor=1.0)
        page = ctx.new_page()

        for slug, path, _caption in VIEWS_STATIC:
            try:
                capture_view(page, args.base_url, path, args.out_dir / f"{slug}.png")
            except Exception as e:
                print(f"[WARN] {slug}: {e}")

        if not args.skip_cases:
            for slug, case_file, _caption in CASES:
                case_path = CASES_DIR / case_file
                if not case_path.exists():
                    print(f"[WARN] manquant : {case_path.name}")
                    continue
                try:
                    capture_case(page, args.base_url, case_path, slug, args.out_dir)
                except Exception as e:
                    print(f"[WARN] {slug}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
