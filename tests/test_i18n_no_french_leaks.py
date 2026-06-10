"""test_i18n_no_french_leaks.py — verify ZERO French when English is selected.

Scans all 6 Streamlit pages rendered in English mode for a list of forbidden
French strings that must NEVER appear.
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

FORBIDDEN_FR = [
    "Non renseigné",
    "Vis vide",
    "Configurer la vis",
    "Pourquoi",
    "Prochaine étape",
    "Couple total",
    "SME totale",
    "Résidence totale",
    "Remplissage moyen",
    "Cisaillement max",
    "Non calculable",
    "Non disponible",
    "Débit massique",
    "Débit sortie",
    "Puissance mécanique",
    "Agrégats par zone",
    "Audit calcul procédé",
    "Formule PLC utilisée",
    "coefficient d'étalonnage",
    "Capacité maximale",
    "Retirez un élément",
    "Configuration réinitialisée",
    "Étalonnage feeder",
    "Débit réel non calculable",
]

PAGES = {
    "Supervision": str(APP / "Supervision.py"),
    "Profile": str(APP / "pages" / "1_Profile.py"),
    "Settings": str(APP / "pages" / "2_Settings.py"),
    "Analyse_run": str(APP / "pages" / "3_Analyse_run.py"),
    "Historique": str(APP / "pages" / "4_Historique.py"),
    "Moteur_Procede": str(APP / "pages" / "5_Moteur_Procede.py"),
}


def _rendered_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    try:
        for m in at.metric:
            chunks.append(str(getattr(m, "label", "")))
            chunks.append(str(getattr(m, "value", "")))
    except Exception:
        pass
    return "\n".join(chunks)


def _load_en(path: str):
    at = AppTest.from_file(path)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at.run(timeout=120)


import re

RAW_KEY_PATTERN = re.compile(
    r"\bsr\.(arch|rec|comp|trade|axis|check|regime)\.[a-z_]+(\.[a-z_]+)*\b"
)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("name", list(PAGES))
def test_no_forbidden_french_in_english_mode(name):
    at = _load_en(PAGES[name])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr_string in FORBIDDEN_FR:
        assert fr_string not in text, (
            f"[{name}] forbidden French string found in English mode: "
            f"'{fr_string}'"
        )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("name", list(PAGES))
def test_no_raw_i18n_keys_in_english_mode(name):
    """No raw i18n key like sr.arch.*, sr.comp.*, sr.trade.* in rendered UI."""
    at = _load_en(PAGES[name])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    matches = RAW_KEY_PATTERN.findall(text)
    raw_keys = RAW_KEY_PATTERN.findall(text)
    assert not raw_keys, (
        f"[{name}] raw i18n keys found in rendered UI: "
        f"{[m.group() for m in RAW_KEY_PATTERN.finditer(text)]}"
    )
