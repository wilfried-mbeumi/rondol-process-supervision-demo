"""tests/test_settings_to_pages_flow_sync.py

Tests E2E (AppTest) de propagation du débit feeder étalonné de Settings vers
Moteur Procédé, Supervision, Historique. Vérifie qu'aucune page consommatrice
ne « reste » sur un ancien débit après navigation, et qu'aucun « Non calculable »
fantôme n'apparaît quand l'étalonnage est bien renseigné.

Scénario manager :
  - 100 RPM × 2,5 g/h/RPM = 250 g/h = 4,17 g/min
  - Toutes les pages doivent lire cette valeur, en FR ET en EN
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
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False


SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
MOTEUR = str(APP / "pages" / "5_Process_Engine.py")
SUPERVISION = str(APP / "Supervision.py")
HISTORIQUE = str(APP / "pages" / "4_History.py")
ANALYSE_RUN = str(APP / "pages" / "3_Run_Analysis.py")


# Scénario manager 2026-06-09.
SCENARIO_RPM = 100.0
SCENARIO_COEFF = 2.5         # 100 × 2.5 = 250 g/h
SCENARIO_G_MIN = 250.0 / 60.0   # 4.1667 g/min
TOL = 0.01


def _seed_calibration(at: "AppTest") -> None:
    """Sème l'étalonnage feeder #1 en session AVANT le run."""
    at.session_state["feeder_rpm"] = SCENARIO_RPM
    at.session_state["feeder_calib_g_h_per_rpm"] = SCENARIO_COEFF
    # Le miroir persistant est utilisé en repli — on le sème aussi (cohérent
    # avec ce que mirror_calibration_to_persistent fait à chaque rerun).
    at.session_state["feeder_rpm__persist"] = SCENARIO_RPM
    at.session_state["feeder_calib_g_h_per_rpm__persist"] = SCENARIO_COEFF
    at.session_state["fd_en_1"] = True


def _ss(at: "AppTest", key: str, default=None):
    return at.session_state[key] if key in at.session_state else default


# ---------------------------------------------------------------------------
# 1 — Settings : l'étalonnage prend bien le contrôle de feeder_g_per_min
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_settings_propagates_calibrated_flow_to_legacy_key():
    """Après run de Settings avec étalonnage 100×2.5, la clé legacy
    `feeder_g_per_min` doit valoir 4,17 g/min (et NON pas la valeur SME défaut 30)."""
    at = AppTest.from_file(SETTINGS)
    _seed_calibration(at)
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    feed = _ss(at, "feeder_g_per_min")
    assert feed is not None
    assert abs(feed - SCENARIO_G_MIN) < TOL, (
        f"Settings n'a pas propagé le débit étalonné : "
        f"feeder_g_per_min={feed} (attendu {SCENARIO_G_MIN:.4f})"
    )


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_settings_calibrated_flow_survives_in_english():
    """Le changement FR → EN ne doit pas casser la propagation."""
    at = AppTest.from_file(SETTINGS)
    _seed_calibration(at)
    at.session_state["ui_lang"] = "en"
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    feed = _ss(at, "feeder_g_per_min")
    assert feed is not None and abs(feed - SCENARIO_G_MIN) < TOL


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_settings_fd_flow_1_disabled_when_calibrated():
    """UX manager : le widget SME `fd_flow_1` doit être DISABLED quand
    l'étalonnage feeder #1 est renseigné (une seule saisie pour le débit)."""
    at = AppTest.from_file(SETTINGS)
    _seed_calibration(at)
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    # Cherche le widget fd_flow_1 dans la liste des number_input.
    fd_flow_widgets = [w for w in at.number_input if w.key == "fd_flow_1"]
    assert fd_flow_widgets, "widget fd_flow_1 introuvable"
    assert fd_flow_widgets[0].disabled is True


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_settings_fd_flow_1_enabled_when_not_calibrated():
    """Repli : pas d'étalonnage → le widget SME `fd_flow_1` est activé (mode
    hors étalonnage), comme avant le correctif."""
    at = AppTest.from_file(SETTINGS)
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 0.0   # NON calibré
    at.session_state["fd_en_1"] = True
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    fd_flow_widgets = [w for w in at.number_input if w.key == "fd_flow_1"]
    assert fd_flow_widgets
    assert fd_flow_widgets[0].disabled is False


# ---------------------------------------------------------------------------
# 2 — Chaîne canonique current_run_state → Moteur / Supervision
# ---------------------------------------------------------------------------
def test_current_run_state_feed_rate_uses_calibrated_total():
    """Test au NIVEAU de la chaîne canonique (sans Streamlit) : la source
    de vérité partagée par Moteur Procédé, Supervision et tous les
    consommateurs `crs.feed_rate` reflète bien l'étalonnage.

    C'est le contrat fort. L'AppTest ci-dessous ne fait que confirmer que
    les pages traversent cette chaîne sans exception."""
    from AgentIndustrial_v1.core.current_run_state import build_current_run_state
    from AgentIndustrial_v1.core.editing_state import seed_editing_keys
    sess: dict = {
        "feeder_rpm": SCENARIO_RPM,
        "feeder_calib_g_h_per_rpm": SCENARIO_COEFF,
        "fd_en_1": True,
    }
    seed_editing_keys(sess)
    sess["feeder_rpm"] = SCENARIO_RPM
    sess["feeder_calib_g_h_per_rpm"] = SCENARIO_COEFF
    crs = build_current_run_state(sess)
    # crs.feed_rate est le TOTAL multi-feeder (en g/h).
    assert crs.feed_rate.value is not None
    assert abs(crs.feed_rate.value - SCENARIO_RPM * SCENARIO_COEFF) < TOL


def test_build_moteur_inputs_passes_calibrated_flow():
    """Le helper que Moteur Procédé utilise traduit bien feed_rate (g/h) en
    feed_g_per_min cohérent."""
    from AgentIndustrial_v1.core.current_run_state import build_current_run_state
    from AgentIndustrial_v1.core.editing_state import seed_editing_keys
    from run_state_adapter import build_moteur_inputs_from_current_run_state
    sess: dict = {
        "feeder_rpm": SCENARIO_RPM,
        "feeder_calib_g_h_per_rpm": SCENARIO_COEFF,
        "fd_en_1": True,
    }
    seed_editing_keys(sess)
    sess["feeder_rpm"] = SCENARIO_RPM
    sess["feeder_calib_g_h_per_rpm"] = SCENARIO_COEFF
    crs = build_current_run_state(sess)
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - SCENARIO_G_MIN) < TOL


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_moteur_procede_no_non_calculable_when_calibrated():
    """Si l'étalonnage est renseigné, Moteur Procédé NE DOIT PAS afficher de
    bandeau « débit non calculable » (le warning warn() s'appelle seulement
    quand feed_available=False)."""
    at = AppTest.from_file(MOTEUR)
    _seed_calibration(at)
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    warns = " ".join(str(w.value) for w in at.warning)
    assert "non calculable" not in warns.lower(), (
        f"Moteur Procédé affiche encore « Non calculable » alors que "
        f"l'étalonnage est renseigné : {warns!r}"
    )


# ---------------------------------------------------------------------------
# 3 — Supervision : non-crash + pas de « Non calculable » fantôme
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_supervision_renders_with_calibration():
    """Supervision charge la session étalonnée sans exception."""
    at = AppTest.from_file(SUPERVISION)
    _seed_calibration(at)
    at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
    # Et la chaîne canonique vue par Supervision donne bien le bon débit.
    feed = _ss(at, "feeder_g_per_min")
    if feed is not None:
        # Note : Supervision ne sème PAS toujours cette clé selon le chemin
        # de hydration (`restore_operator_state` n'écrit que les clés absentes).
        # Si elle est présente, elle DOIT être cohérente.
        assert abs(feed - SCENARIO_G_MIN) < TOL


# ---------------------------------------------------------------------------
# 4 — Historique / Analyse run ne crashent pas avec l'étalonnage présent
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("page", [HISTORIQUE, ANALYSE_RUN])
def test_pages_render_with_calibration(page):
    at = AppTest.from_file(page)
    _seed_calibration(at)
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]


# ---------------------------------------------------------------------------
# 5 — Modification d'étalonnage : la nouvelle valeur se propage (chaîne pure)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rpm,coeff,expected_gh,expected_gmin", [
    (100.0, 2.5, 250.0, 250.0 / 60.0),    # scénario manager initial
    (120.0, 3.0, 360.0, 6.0),             # après modification opérateur
    (30.0, 17.0, 510.0, 8.5),             # autre cas manager
    (50.0, 5.0, 250.0, 250.0 / 60.0),     # même débit, paramètres différents
])
def test_calibration_change_propagates_in_canonical_chain(
    rpm, coeff, expected_gh, expected_gmin,
):
    """Le passage d'un étalonnage à un autre se propage immédiatement dans
    la chaîne canonique (current_run_state.feed_rate + build_moteur_inputs).
    Aucune dépendance Streamlit — c'est le contrat fort."""
    from AgentIndustrial_v1.core.current_run_state import build_current_run_state
    from AgentIndustrial_v1.core.editing_state import seed_editing_keys
    from run_state_adapter import build_moteur_inputs_from_current_run_state
    sess: dict = {
        "feeder_rpm": rpm, "feeder_calib_g_h_per_rpm": coeff,
        "fd_en_1": True,
    }
    seed_editing_keys(sess)
    sess["feeder_rpm"] = rpm
    sess["feeder_calib_g_h_per_rpm"] = coeff
    crs = build_current_run_state(sess)
    assert abs(crs.feed_rate.value - expected_gh) < 1.0
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert abs(mi["feed_g_per_min"] - expected_gmin) < TOL
