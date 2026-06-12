"""Tests stabilisation GLOBALE (retours prod manager + opérateur 2026-06-10).

Cause racine principale corrigée : le snapshot validé (« Enregistrer ») ne
vivait QUE dans st.session_state → tout refresh navigateur / redéploiement
Streamlit Cloud le perdait. Supervision repassait « profil vide / analyse
indicative », l'Agent IA retombait sur les défauts, Settings re-seedait ses
widgets — alors que l'Historique (sur disque) gardait la trace du commit.
Correctif : miroir disque volatile du snapshot (applied_state.json, .gitignoré,
restauration setdefault-only — n'écrase jamais une session vivante).

Couvre les scénarios obligatoires :
  1/10. persistance après navigation + non-écrasement session (calibration,
        snapshot vs valeurs utilisateur vivantes) ;
  3.    Moteur Procédé lit le profil sauvegardé (pas de « vis vide ») ;
  4.    Agent IA lit l'état sauvegardé après refresh (pas de défauts) ;
  5/6.  English sans français visible / Français sans anglais parasite.
(2. Profile editable après save → tests/test_profile_edit_after_save_e2e.py ;
 7. SME → test_sme_alert_wording.py ; 8. zone 8 → test_s2_stabilisation /
 test_moteur_procede_material ; 9. agrégats → test_s2_stabilisation.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core import applied_state  # noqa: E402
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402
    APPLIED_KEY,
    AppliedSnapshot,
    commit as applied_commit,
    get_applied,
    restore_applied,
)
from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    seed_editing_keys,
)
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
from operator_store import capture_operator_state  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

PAGES = {
    "supervision": str(ROOT / "app" / "Supervision.py"),
    "profile": str(ROOT / "app" / "pages" / "1_Profile.py"),
    "settings": str(ROOT / "app" / "pages" / "2_Settings.py"),
    "analyse": str(ROOT / "app" / "pages" / "3_Run_Analysis.py"),
    "historique": str(ROOT / "app" / "pages" / "4_History.py"),
    "moteur": str(ROOT / "app" / "pages" / "5_Process_Engine.py"),
}

EXPECTED_GMIN = 250.0 / 60.0  # 100 RPM × 2.5 g/h/RPM


def _manager_cfg() -> list[int]:
    """Profil manager : convoyage + Kneading 60° uniquement."""
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 10)
    add_elements_atomic(cfg, 7, 2)
    return cfg


def _commit_calibrated_session() -> dict:
    """Simule l'opérateur : étalonnage 100×2,5 + profil vis, puis Enregistrer.
    Retourne la session « avant refresh ». Écrit les miroirs disque (isolés
    par conftest)."""
    sess: dict = {
        "screw_config": _manager_cfg(),
        "feeder_rpm": 100.0,
        "feeder_calib_g_h_per_rpm": 2.5,
        "fd_en_1": True,
        "ni_rpm_hmi": 120.0,
    }
    seed_editing_keys(sess)
    sess["feeder_rpm"], sess["feeder_calib_g_h_per_rpm"] = 100.0, 2.5
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="stab globale")
    capture_operator_state(sess)
    return sess


def _rendered_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success", "metric", "button",
                 "toggle", "selectbox"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
                chunks.append(str(getattr(el, "label", "")))
                chunks.append(str(getattr(el, "help", "")))
        except Exception:
            pass
    for getter in ("html", "arrow_data_frame", "expander"):
        try:
            for el in at.get(getter):
                chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
                chunks.append(str(getattr(el, "label", "")))
        except Exception:
            pass
    return "\n".join(chunks)


# ===========================================================================
# 1 — Le snapshot validé survit à un « refresh navigateur » (session neuve)
# ===========================================================================
def test_applied_snapshot_survives_browser_refresh():
    before = _commit_calibrated_session()
    snap_before = get_applied(before)
    assert snap_before is not None

    fresh: dict = {}  # session neuve = refresh navigateur / nouvel onglet
    snap_after = get_applied(fresh)
    assert snap_after is not None, "snapshot perdu après refresh (miroir disque KO)"
    assert snap_after.screw_config == snap_before.screw_config
    assert snap_after.feeders[0]["mass_flow_g_per_min"] == pytest.approx(
        EXPECTED_GMIN, abs=0.01
    )


def test_state_from_session_after_refresh_uses_saved_profile():
    _commit_calibrated_session()
    fresh: dict = {}
    state = state_from_session(fresh)
    # Le profil vis sauvegardé est revu — PAS une vis vide ni un défaut.
    assert sum(1 for v in state.screw_config if v not in (0,)) > 4
    assert state.feeders[0].mass_flow_g_per_min == pytest.approx(
        EXPECTED_GMIN, abs=0.01
    )


def test_restore_applied_never_overwrites_live_session():
    """Règle absolue 2/10 : le miroir disque n'écrase JAMAIS un commit vivant."""
    _commit_calibrated_session()  # écrit un snapshot « ancien » sur disque

    live: dict = {}
    live_snap = AppliedSnapshot(screw_config=[9] * 81, screw_rpm=333.0)
    live[APPLIED_KEY] = live_snap
    out = restore_applied(live)
    assert out is live_snap
    assert live[APPLIED_KEY] is live_snap  # pas remplacé par le disque
    assert get_applied(live) is live_snap


def test_corrupt_disk_mirror_never_crashes(tmp_path, monkeypatch):
    monkeypatch.setenv("RONDOL_APPLIED_STATE_PATH", str(tmp_path / "bad.json"))
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert get_applied({}) is None  # illisible → None, jamais d'exception


# ===========================================================================
# 3 — Moteur Procédé lit le profil sauvegardé (jamais « vis vide » à tort)
# ===========================================================================
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_moteur_procede_reads_saved_profile():
    _commit_calibrated_session()
    at = AppTest.from_file(PAGES["moteur"])
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    assert "Aucun profil procédé configuré" not in text, (
        "Moteur Procédé considère la vis vide alors qu'un profil est sauvegardé"
    )
    # Débit calibré 4,17 g/min lu par le moteur → aucun indicateur
    # « Non calculable » (qui n'apparaît que sans étalonnage).
    assert "Non calculable" not in text and "non calculable" not in text
    if "feeder_g_per_min" in at.session_state:
        assert at.session_state["feeder_g_per_min"] == pytest.approx(
            EXPECTED_GMIN, abs=0.01
        )


# ===========================================================================
# 4 — Agent IA lit l'état sauvegardé après refresh (pas de défauts)
# ===========================================================================
def test_agent_reads_saved_profile_after_refresh_no_default_recos():
    _commit_calibrated_session()
    fresh: dict = {}
    state = state_from_session(fresh)
    report = evaluate(state)
    codes = {a.code for a in report.alerts}
    # Vis configurée + débit calibré → l'agent ne doit PAS dire « vis vide ».
    assert "FF_ZERO" not in codes, (
        "Agent IA évalue un Fill Factor nul alors que le profil sauvegardé "
        "contient des éléments et un débit calibré"
    )
    # Et aucune mention d'éléments absents (profil = convoyage + K60).
    blob = " ".join(
        f"{a.title} {a.description}" for a in report.alerts
    ).lower()
    for tok in ("kneading 90", "kneading 45", "malaxage 90", "malaxage 45"):
        assert tok not in blob


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_supervision_after_refresh_not_indicative_not_empty():
    """Supervision sur session neuve (refresh) : la lecture profil ne doit pas
    afficher « analyse indicative / aucun profil enregistré » ni « Vis vide »."""
    _commit_calibrated_session()
    at = AppTest.from_file(PAGES["supervision"])
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    assert "Analyse indicative" not in text
    assert "Aucun profil enregistré" not in text
    assert "Vis vide" not in text


# ===========================================================================
# 5 — English : aucun des textes FR signalés visible, toutes pages
# ===========================================================================
# « Action » / « Impact » sont identiques en anglais → non testables par
# absence. « Aucun élément » couvert via « Aucun élément placé » (archétype).
_FR_FORBIDDEN = (
    "Vis vide", "Aucun élément placé", "Configurer la vis", "Prochaine étape",
    "PROCHAINE ÉTAPE", "Pourquoi", "Régime", "Aucune analyse possible",
    "placez quelques éléments", "Extrudeuse", "Non renseigné",
    "Capacité maximale atteinte", "Retirez un élément",
)


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("page", ["supervision", "profile", "moteur",
                                  "historique", "analyse"])
def test_full_app_english_no_french_visible(page):
    _commit_calibrated_session()
    at = AppTest.from_file(PAGES[page])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    at = at.run(timeout=180)
    assert not at.exception, (page, [str(e.value) for e in at.exception])
    text = _rendered_text(at)
    for fr in _FR_FORBIDDEN:
        assert fr not in text, f"[{page}] texte FR visible en anglais : « {fr} »"


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_profile_english_empty_screw_states_translated():
    """Variante vis VIDE en anglais : les états vides (bannière + lecture IA)
    sont traduits — aucun des libellés FR signalés."""
    at = AppTest.from_file(PAGES["profile"])
    at.session_state["ui_lang"] = "en"
    at.session_state["screw_config"] = new_empty_configuration()
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in ("Vis vide", "Aucun élément placé", "Aucune analyse possible",
               "placez quelques éléments", "Configurer la vis"):
        assert fr not in text, f"texte FR visible en anglais (vis vide) : {fr}"
    assert "Empty screw" in text


# ===========================================================================
# 6 — Français : pas d'anglais parasite sur les libellés principaux
# ===========================================================================
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_full_app_french_no_unwanted_english():
    _commit_calibrated_session()
    at = AppTest.from_file(PAGES["historique"])
    at.session_state["ui_lang"] = "fr"
    at = at.run(timeout=180)
    assert not at.exception
    text = _rendered_text(at)
    assert "Historique des procédés" in text
    assert "Process history" not in text

    at2 = AppTest.from_file(PAGES["profile"])
    at2.session_state["ui_lang"] = "fr"
    at2.session_state["screw_config"] = new_empty_configuration()
    at2 = at2.run(timeout=180)
    assert not at2.exception
    text2 = _rendered_text(at2)
    assert "Vis vide" in text2          # libellé métier FR attendu
    assert "Empty screw" not in text2


# ===========================================================================
# 1-bis — Settings : les champs ne retombent pas à zéro après navigation
# ===========================================================================
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_settings_fields_do_not_reset_after_navigation():
    """Settings (saisie + save simulé) → navigation (sessions neuves) → retour
    Settings : RPM 100 / coeff 2,5 / débit 4,17 revus, jamais 0/30/5."""
    _commit_calibrated_session()
    # « Retour Settings » : session neuve, le seed doit revoir le snapshot.
    at = AppTest.from_file(PAGES["settings"])
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    ss = at.session_state
    assert float(ss["feeder_rpm"]) == pytest.approx(100.0, abs=0.01)
    assert float(ss["feeder_calib_g_h_per_rpm"]) == pytest.approx(2.5, abs=0.001)
    assert float(ss["feeder_g_per_min"]) == pytest.approx(EXPECTED_GMIN, abs=0.01)
    # Le profil vis sauvegardé est aussi revu (pas de vis remise à vide).
    cfg = list(ss["screw_config"])
    assert sum(1 for v in cfg if v != 0) > 4
