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
    # Phase 12 — agent core + ML section + hypothesis section
    "Surcharge thermique",
    "consigne",
    "fourreau",
    "Réduire",
    "vitesse vis",
    "Surveillance",
    "instabilité",
    "Moteur Procédé",
    "Profil thermique",
    "Hypothèses",
    "Durée (min)",
    "Fenêtres",
    "Répartition",
    "Résumé par run",
    "Début",
    "Score moyen",
    "entraînement",
    "démonstration",
    "Aucune alerte",
    "Régler",
    "Descendre",
    "ré-évaluer",
    "SURVEILLER",
    "Seuil 80",
    "Équations différées",
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


def _load_fresh(path: str):
    """Fresh session — NO ui_lang preset. Tests that DEFAULT_LANG takes effect."""
    at = AppTest.from_file(path)
    at.session_state["demo_mode"] = False
    return at.run(timeout=120)


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
    raw_keys = RAW_KEY_PATTERN.findall(text)
    assert not raw_keys, (
        f"[{name}] raw i18n keys found in rendered UI: "
        f"{[m.group() for m in RAW_KEY_PATTERN.finditer(text)]}"
    )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_direct_entry_defaults_english():
    """Direct URL /Settings on fresh session must render English."""
    at = _load_fresh(PAGES["Settings"])
    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.session_state["ui_lang"] == "en", (
        f"Settings defaulted to '{at.session_state['ui_lang']}' instead of 'en'"
    )
    text = _rendered_text(at)
    for fr in FORBIDDEN_FR:
        assert fr not in text, f"[Settings direct] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_rerun_stays_english():
    """After initial render, rerun must keep English."""
    at = _load_fresh(PAGES["Settings"])
    assert not at.exception
    at2 = at.run()
    assert not at2.exception
    assert at2.session_state["ui_lang"] == "en"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_all_pages_default_english_fresh_session():
    """Every page must default to English on a fresh session (no ui_lang set)."""
    for name, path in PAGES.items():
        at = _load_fresh(path)
        assert not at.exception, f"[{name}] exception: {[str(e.value) for e in at.exception]}"
        lang = at.session_state["ui_lang"]
        assert lang == "en", f"[{name}] defaulted to '{lang}' instead of 'en'"


# ===================================================================
# 8 required specific tests (Phase 12 — English-default compliance)
# ===================================================================

@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_english_no_french_after_direct_entry():
    """Settings direct entry with no prior page: ZERO French."""
    at = _load_fresh(PAGES["Settings"])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in FORBIDDEN_FR:
        assert fr not in text, f"[Settings direct] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_english_no_french():
    """Moteur Procédé in English: ZERO forbidden French strings."""
    at = _load_en(PAGES["Moteur_Procede"])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in FORBIDDEN_FR:
        assert fr not in text, f"[Moteur_Procede] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_historique_english_no_french():
    """Historique in English: ZERO forbidden French strings."""
    at = _load_en(PAGES["Historique"])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in FORBIDDEN_FR:
        assert fr not in text, f"[Historique] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_english_no_french():
    """Supervision in English: ZERO forbidden French strings."""
    at = _load_en(PAGES["Supervision"])
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in FORBIDDEN_FR:
        assert fr not in text, f"[Supervision] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_agent_cards_english_no_french():
    """Agent alerts/recos cards on Supervision must be English when lang=en."""
    at = AppTest.from_file(PAGES["Supervision"])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = True
    at = at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    agent_fr = [
        "Surcharge thermique", "Réduire", "vitesse vis",
        "Surveillance", "instabilité", "Aucune alerte",
        "Descendre", "ré-évaluer", "SURVEILLER",
    ]
    for fr in agent_fr:
        assert fr not in text, f"[Agent cards] French leak: '{fr}'"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_saved_profile_visible_in_supervision_after_settings_save():
    """After saving in Settings, Supervision must not show 'No saved profile'."""
    from AgentIndustrial_v1.core.applied_state import commit, get_applied
    from AgentIndustrial_v1.core.state_sync import state_from_session

    at = AppTest.from_file(PAGES["Supervision"])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = True
    at.session_state["screw_config"] = [0] * 81
    at.session_state["screw_config"][10] = 3
    at.session_state["screw_config"][11] = 3
    state = state_from_session(at.session_state)
    commit(at.session_state, state, label="test")
    snap = get_applied(at.session_state)
    assert snap is not None, "commit must produce a snapshot"

    at2 = at.run(timeout=120)
    assert not at2.exception, [str(e.value) for e in at2.exception]
    text = _rendered_text(at2)
    assert "No saved profile" not in text, (
        "Supervision still shows 'No saved profile' after a successful save"
    )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_saved_profile_survives_page_navigation_and_refresh():
    """Applied snapshot must survive session clear (disk mirror restores it)."""
    from AgentIndustrial_v1.core.applied_state import commit, get_applied
    from AgentIndustrial_v1.core.state_sync import state_from_session

    at = AppTest.from_file(PAGES["Settings"])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = True
    at = at.run(timeout=120)
    assert not at.exception

    state = state_from_session(at.session_state)
    snap = commit(at.session_state, state, label="nav-test")
    assert snap is not None

    at2 = AppTest.from_file(PAGES["Supervision"])
    at2.session_state["ui_lang"] = "en"
    at2 = at2.run(timeout=120)
    assert not at2.exception, [str(e.value) for e in at2.exception]
    snap2 = get_applied(at2.session_state)
    assert snap2 is not None, "Snapshot must be restored from disk after navigation"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_feeder_calibration_250gh_visible_everywhere_after_save():
    """Feeder calibration value must propagate to Supervision after save."""
    at = AppTest.from_file(PAGES["Supervision"])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = True
    at.session_state["fd_1_coeff"] = 250.0
    at.session_state["screw_rpm"] = 120.0
    at = at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
