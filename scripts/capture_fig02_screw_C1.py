"""Genere fig02 — profil de vis pour la recette LFP baseline (cas C1).

Reutilise l'infra de rendu existante (app/screw_render.py) SANS modification.
Construit la configuration de vis correspondant au cas C1 :
    Z1 feed   : Large pitch        x3
    Z2 conv.  : Short-pitch        x2
    Z3 mix    : Kneading 30        x4
    Z4 conv.  : Short-pitch        x2
    Z5 mix    : Kneading 45        x3
    Z6 conv.  : Short-pitch        x2
    Z7 compr. : Short-pitch (proxy)x2
    Z8 tip    : automatique (pos. 79-80)

Sortie : reports/poster_abstract/figures/generated/fig02_screw_li_profile.png
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from playwright.sync_api import sync_playwright  # noqa: E402

from screw_logic import (  # noqa: E402
    ELEMENT_TYPES,
    N_POSITIONS,
    add_element,
    base_type,
    is_part2,
    new_empty_configuration,
)
from screw_render import build_screw_assembly_html  # noqa: E402


# Mapping zone -> sequence d'elements (id, count). Convention C1 :
# 1 forward / 3 short-pitch / 5 kneading 30 / 6 large-pitch / 8 kneading 45 / 13 tip.
C1_PROFILE: list[tuple[str, list[tuple[int, int]]]] = [
    ("Z1 feed",       [(6, 3)]),
    ("Z2 conveying",  [(3, 2)]),
    ("Z3 kneading 30",[(5, 4)]),
    ("Z4 conveying",  [(3, 2)]),
    ("Z5 kneading 45",[(8, 3)]),
    ("Z6 conveying",  [(3, 2)]),
    ("Z7 compression",[(3, 2)]),
]


def element_full_name(t: int) -> str:
    return ELEMENT_TYPES[t].full_name if 0 <= t < len(ELEMENT_TYPES) else f"type {t}"


def build_c1_config() -> list[int]:
    cfg = new_empty_configuration()
    for _zone, items in C1_PROFILE:
        for t, n in items:
            add_element(cfg, t, count=n)
    return cfg


HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>fig02 — vis C1</title>
<style>
  *{{box-sizing:border-box}}
  body{{
    background:#FFFFFF;color:#333333;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:24px;margin:0;
  }}
  .title{{font-size:1.15rem;font-weight:700;color:#1B7A3D;margin:0 0 4px 0}}
  .sub{{color:#666666;font-size:.78rem;margin:0 0 18px 0;font-family:ui-monospace,Menlo,monospace}}
  .frame{{width:3240px;background:linear-gradient(180deg,#1A1A1F 0%,#0A0A0E 100%);padding:24px;border-radius:6px;}}
  .legend{{margin-top:18px;color:#333333;font-size:.85rem;display:flex;gap:24px;flex-wrap:wrap;}}
  .legend span{{display:inline-flex;align-items:center;gap:6px;}}
  .swatch{{display:inline-block;width:14px;height:14px;border-radius:2px;border:1px solid #2a2a35;}}
</style></head>
<body>
  <div class="title">fig02 — Profil de vis pour la recette LFP baseline (cas C1)</div>
  <div class="sub">Rondol Ø 10,5 mm · L/D 40:1 · 18 elements + tip · zones Z1 a Z8</div>
  <div class="frame">{rendered}</div>
  <div class="legend">
    <span><span class="swatch" style="background:#3a3e46"></span> base universelle (forward +72°)</span>
    <span><span class="swatch" style="background:#1B7A3D"></span> conveying (Z1 large-pitch / Z2 Z4 Z6 Z7 short-pitch)</span>
    <span><span class="swatch" style="background:#005B96"></span> kneading Z3 (30°) et Z5 (45°)</span>
    <span><span class="swatch" style="background:#b8bdc7"></span> pointe + decharge (Z8)</span>
  </div>
</body></html>
"""


def main() -> None:
    out_dir = ROOT / "reports" / "poster_abstract" / "figures" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = build_c1_config()
    rendered = build_screw_assembly_html(
        cfg, N_POSITIONS,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        element_full_name_fn=element_full_name,
        show_zones=False,
        zone_starts=None,
    )
    html = HTML_TEMPLATE.format(rendered=rendered)
    tmp = ROOT / "_tmp_fig02.html"
    tmp.write_text(html, encoding="utf-8")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 3320, "height": 600},
                                  device_scale_factor=1.0)
        page = ctx.new_page()
        page.goto(f"file:///{tmp.as_posix()}")
        page.wait_for_load_state("networkidle")
        out = out_dir / "fig02_screw_li_profile.png"
        page.screenshot(path=str(out), full_page=True)
        browser.close()

    tmp.unlink()
    print(f"[OK] {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
