"""Tests P2 — la page Moteur Procédé n'invente JAMAIS de matière en mode client.

Deux niveaux :
  1. Pur (app_mode.material_label / demo flag) — contrat anti-invention.
  2. AppTest réel — la page rendue ne contient aucun nom de chimie (LFP /
     LiFePO4 / LATP) tant que demo_mode=False, et affiche « Non renseigné ».
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from app_mode import (  # noqa: E402
    NOT_PROVIDED,
    is_demo_mode,
    material_label,
    set_demo_mode,
)


# ---------------------------------------------------------------------------
# 1 — contrat pur
# ---------------------------------------------------------------------------
def test_demo_mode_defaults_to_client_false():
    assert is_demo_mode({}) is False
    s: dict = {}
    set_demo_mode(s, True)
    assert is_demo_mode(s) is True


def test_material_label_client_mode_never_chemistry():
    # Quelle que soit la matière nominale moteur, mode client = « Non renseigné ».
    for name in ("LiFePO4 (LFP)", "Li1.3Al0.3Ti1.7(PO4)3 (LATP)", "LFP+LATP", None, ""):
        assert material_label(name, demo_mode=False) == NOT_PROVIDED


def test_material_label_demo_mode_shows_real_name():
    assert material_label("LiFePO4 (LFP)", demo_mode=True) == "LiFePO4 (LFP)"
    assert material_label(None, demo_mode=True) == NOT_PROVIDED  # vide → non renseigné


# ---------------------------------------------------------------------------
# 2 — page réelle (AppTest)
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

MP_PATH = str(ROOT / "app" / "pages" / "5_Moteur_Procede.py")
_FORBIDDEN_CHEMISTRY = ("LiFePO4", "LFP", "LATP", "carbon nanotube", "CNT", "cathode")


def _rendered_text(at) -> str:
    """Concatène tout le texte rendu accessible (markdown + html + captions)."""
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text", "info",
                 "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except Exception:
            pass
    # st.html : exposé comme élément 'html' selon la version Streamlit.
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    return "\n".join(chunks)


def _load_with_profile(demo_mode: bool):
    """Charge la page avec un profil non vide (sinon garde « profil vide »)."""
    from screw_logic import add_elements_atomic, new_empty_configuration
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)   # un peu de convoyage → profil non vide
    at = AppTest.from_file(MP_PATH)
    at.session_state["screw_config"] = cfg
    at.session_state["demo_mode"] = demo_mode
    return at.run(timeout=60)


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_no_lifepo4_displayed_without_user_input():
    at = _load_with_profile(demo_mode=False)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    assert "Not entered" in text or "Non renseigné" in text
    for token in ("LiFePO4", "LFP", "LATP", "cathode", "nanotube", "CNT"):
        assert token not in text, f"« {token} » présent en mode client : {text[:400]}"


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_client_mode_renders_clean():
    at = _load_with_profile(demo_mode=False)
    assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_demo_mode_renders_clean_and_shows_material():
    at = _load_with_profile(demo_mode=True)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    assert "LiFePO4" in text  # en démo, la matière nominale réapparaît (avec DEMO)
