"""test_i18n.py — Tests de base de la couche i18n (phase B0).

Vérifie la mécanique de traduction SANS dépendre d'un contexte Streamlit
vivant (les helpers sont tolérants hors ScriptRunContext) :
  - langue par défaut = français ;
  - fallback clé/identifiant brut si traduction absente ;
  - complétude FR/EN des dictionnaires ;
  - parité des placeholders entre FR et EN ;
  - formatage protégé (jamais de KeyError).

Tests PURS : aucun accès disque, aucune écriture d'historique.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import i18n_messages  # noqa: E402
import i18n  # noqa: E402


_PLACEHOLDER = re.compile(r"{(\w+)}")


def _placeholders(s: str) -> set[str]:
    return set(_PLACEHOLDER.findall(s))


# ---------------------------------------------------------------------------
# Langue par défaut
# ---------------------------------------------------------------------------
def test_default_lang_is_french():
    assert i18n.DEFAULT_LANG == "fr"
    assert i18n_messages.DEFAULT_LANG == "fr"


def test_current_lang_defaults_to_fr_without_session():
    # Hors contexte Streamlit, current_lang() doit dégrader vers "fr".
    assert i18n.current_lang() == "fr"


def test_supported_langs_are_fr_en():
    assert set(i18n.SUPPORTED_LANGS) == {"fr", "en"}
    assert set(i18n_messages.SUPPORTED_LANGS) == {"fr", "en"}


# ---------------------------------------------------------------------------
# Fallback chrome (t)
# ---------------------------------------------------------------------------
def test_t_unknown_key_returns_raw_key():
    assert i18n.t("clef.inexistante") == "clef.inexistante"


def test_t_known_key_returns_fr_by_default():
    assert i18n.t("lang.selector_label") == "Langue"


def test_t_format_missing_param_is_safe():
    # Aucune clé n'utilise de placeholder en B0 ; on vérifie juste que passer
    # des kwargs sur une clé sans placeholder ne casse pas.
    assert i18n.t("lang.selector_label", foo=1) == "Langue"


# ---------------------------------------------------------------------------
# Fallback catalogue agent (m)
# ---------------------------------------------------------------------------
def test_m_unknown_id_returns_id():
    assert i18n_messages.m("MSG_INEXISTANT", "fr") == "MSG_INEXISTANT"


def test_m_unsupported_lang_falls_back_to_fr():
    assert i18n_messages.m("_SELFTEST", "de") == i18n_messages.m("_SELFTEST", "fr")


def test_m_returns_str():
    assert isinstance(i18n_messages.m("_SELFTEST", "en"), str)


# ---------------------------------------------------------------------------
# Complétude & parité FR/EN
# ---------------------------------------------------------------------------
def test_chrome_translations_complete_fr_en():
    for key, entry in i18n.TRANSLATIONS.items():
        assert "fr" in entry and "en" in entry, f"clé incomplète : {key}"
        assert entry["fr"] and entry["en"], f"valeur vide : {key}"


def test_agent_messages_complete_fr_en():
    for key, entry in i18n_messages.MESSAGES.items():
        assert "fr" in entry and "en" in entry, f"message incomplet : {key}"


def test_placeholder_parity_chrome():
    for key, entry in i18n.TRANSLATIONS.items():
        assert _placeholders(entry["fr"]) == _placeholders(entry["en"]), key


def test_placeholder_parity_agent():
    for key, entry in i18n_messages.MESSAGES.items():
        assert _placeholders(entry["fr"]) == _placeholders(entry["en"]), key


# ---------------------------------------------------------------------------
# Rendu réel des 4 pages en FR et EN (AppTest) — preuve B1 d'ouverture sans
# exception dans les deux langues. Aucun clic « Enregistrer » → historique
# non pollué.
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

import pytest  # noqa: E402

_PAGES = {
    "home": str(ROOT / "app" / "Supervision.py"),
    "profile": str(ROOT / "app" / "pages" / "1_Profile.py"),
    "settings": str(ROOT / "app" / "pages" / "2_Settings.py"),
    "analyse": str(ROOT / "app" / "pages" / "3_Analyse_run.py"),
}


def _render(path: str, lang: str):
    at = AppTest.from_file(path)
    at.session_state["ui_lang"] = lang
    at.run(timeout=60)
    return at


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("name", list(_PAGES))
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_pages_render_both_languages(name, lang):
    at = _render(_PAGES[name], lang)
    if at.exception:
        excs = "\n".join(str(e.value) for e in at.exception)
        raise AssertionError(f"[{name}/{lang}] exception(s) : {excs}")
    # La langue choisie est bien propagée dans la session.
    assert at.session_state["ui_lang"] == lang
