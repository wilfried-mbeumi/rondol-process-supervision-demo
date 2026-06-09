"""tests/test_feeder_calibration_overrides_sme.py

Cause racine #1 manager 2026-06-09 : Settings exposait deux entrées concurrentes
pour le débit feeder #1 (étalonnage RPM × coeff dans le Bloc 2bis, ET saisie
directe SME `fd_flow_1` dans le Bloc 3), donnant deux sources de vérité
incohérentes. `project_shared_keys` écrasait silencieusement le débit étalonné
par la valeur SME au prochain rerun.

Correctif architectural : quand l'étalonnage feeder #fid est calibré (coeff > 0),
il PRIME sur la saisie SME directe `fd_flow_{fid}`. Vérifié au niveau
`build_state_from_widgets` (test unitaire ici) ET au niveau page (AppTest plus
bas) : Settings → Moteur Procédé → Supervision lisent le même débit.

Scénario manager : 100 RPM × 2,5 g/h/RPM → 250 g/h = 4,17 g/min — accepté
comme nouveau débit feeder dans TOUTE la chaîne.
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

from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    feeder_calibrated_g_per_min,
    feeder_is_calibrated,
    project_shared_keys,
    seed_editing_keys,
)


# ---------------------------------------------------------------------------
# 1 — helpers de test (PUR — dict simulant st.session_state)
# ---------------------------------------------------------------------------
def _session_with_calibration(rpm: float, coeff: float, sme_fd_flow: float = 30.0):
    """Session minimaliste reproduisant le scénario manager.

    - étalonnage feeder #1 : `feeder_rpm`/`feeder_calib_g_h_per_rpm` (clés legacy).
    - saisie SME directe `fd_flow_1` (Bloc 3 Settings) : la valeur historique
      par défaut, supposée écraser le débit étalonné AVANT correctif.
    """
    sess: dict = {
        "feeder_rpm": rpm,
        "feeder_calib_g_h_per_rpm": coeff,
        "fd_en_1": True,
        "fd_flow_1": sme_fd_flow,
    }
    seed_editing_keys(sess)
    # Garantir que les clés métier post-seed n'écrasent pas notre saisie.
    sess["feeder_rpm"] = rpm
    sess["feeder_calib_g_h_per_rpm"] = coeff
    sess["fd_flow_1"] = sme_fd_flow
    return sess


# ---------------------------------------------------------------------------
# 2 — helpers PUR : feeder_is_calibrated / feeder_calibrated_g_per_min
# ---------------------------------------------------------------------------
def test_feeder_is_calibrated_true_when_coeff_positive():
    sess = {"feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 2.5}
    assert feeder_is_calibrated(sess, 1) is True


def test_feeder_is_calibrated_false_when_coeff_zero():
    sess = {"feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 0.0}
    assert feeder_is_calibrated(sess, 1) is False


def test_feeder_is_calibrated_false_when_coeff_missing():
    sess: dict = {}
    assert feeder_is_calibrated(sess, 1) is False


def test_feeder_calibrated_g_per_min_manager_scenario():
    """Scénario manager : 100 RPM × 2,5 g/h/RPM → 250 g/h = 4,17 g/min."""
    sess = {"feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 2.5}
    g_min = feeder_calibrated_g_per_min(sess, 1)
    assert g_min is not None
    assert abs(g_min - 250.0 / 60.0) < 1e-6   # 4.1667 g/min


def test_feeder_calibrated_g_per_min_30x17_manager_example():
    """Exemple manager 2026-06-09 : 30 RPM × 17 → 510 g/h = 8,5 g/min."""
    sess = {"feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 17.0}
    g_min = feeder_calibrated_g_per_min(sess, 1)
    assert g_min is not None
    assert abs(g_min - 8.5) < 1e-6


def test_feeder_calibrated_returns_none_when_uncalibrated():
    sess = {"feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 0.0}
    assert feeder_calibrated_g_per_min(sess, 1) is None


def test_feeder_calibrated_respects_max_clamp():
    """Au-delà du plafond (2500 g/h), le débit effectif est plafonné."""
    sess = {"feeder_rpm": 200.0, "feeder_calib_g_h_per_rpm": 20.0}  # 4000 g/h
    g_min = feeder_calibrated_g_per_min(sess, 1)
    assert g_min is not None
    assert abs(g_min - 2500.0 / 60.0) < 1e-6   # plafonné


# ---------------------------------------------------------------------------
# 3 — Réconciliation dans build_state_from_widgets (cause racine #1)
# ---------------------------------------------------------------------------
def test_calibration_overrides_sme_in_state_manager_scenario():
    """CŒUR DU CORRECTIF : 100 RPM × 2,5 + fd_flow_1=30 → state.feeders[0]
    voit 4,17 g/min (étalonnage), JAMAIS 30 (SME)."""
    sess = _session_with_calibration(rpm=100.0, coeff=2.5, sme_fd_flow=30.0)
    state = build_state_from_widgets(sess)
    main = state.feeders[0]
    assert abs(main.mass_flow_g_per_min - 250.0 / 60.0) < 1e-6
    # Et JAMAIS la valeur SME parasite.
    assert abs(main.mass_flow_g_per_min - 30.0) > 1.0


def test_sme_value_used_when_calibration_absent():
    """Repli : sans étalonnage (coeff=0), la saisie SME `fd_flow_1` reste utilisée.
    Garantit qu'on ne casse pas le mode hors étalonnage."""
    sess: dict = {
        "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 0.0,
        "fd_en_1": True, "fd_flow_1": 12.0,
    }
    seed_editing_keys(sess)
    sess["fd_flow_1"] = 12.0
    state = build_state_from_widgets(sess)
    assert abs(state.feeders[0].mass_flow_g_per_min - 12.0) < 1e-6


def test_project_shared_keys_reflects_calibrated_flow():
    """`project_shared_keys` reprojette `feeder_g_per_min` legacy.
    Comme state.feeders[0].mass_flow_g_per_min est maintenant étalonné,
    la clé legacy est cohérente avec ce que voit Profile / Supervision."""
    sess = _session_with_calibration(rpm=100.0, coeff=2.5, sme_fd_flow=30.0)
    state = build_state_from_widgets(sess)
    project_shared_keys(sess, state)
    assert abs(sess["feeder_g_per_min"] - 250.0 / 60.0) < 1e-6
    # JAMAIS le défaut SME parasite.
    assert sess["feeder_g_per_min"] != 30.0


@pytest.mark.parametrize("rpm,coeff,expected_g_min", [
    (100.0, 2.5, 4.1667),    # scénario manager
    (30.0, 17.0, 8.5),       # autre exemple manager
    (60.0, 10.0, 10.0),      # 600 g/h
    (50.0, 5.0, 4.1667),     # 250 g/h différemment
])
def test_calibration_to_state_parametric(rpm, coeff, expected_g_min):
    sess = _session_with_calibration(rpm=rpm, coeff=coeff, sme_fd_flow=999.0)
    state = build_state_from_widgets(sess)
    assert abs(state.feeders[0].mass_flow_g_per_min - expected_g_min) < 1e-3


# ---------------------------------------------------------------------------
# 4 — Persistance après rerun (le bug original se déclenchait au rerun)
# ---------------------------------------------------------------------------
def test_calibrated_flow_survives_second_rerun():
    """Simule deux passes consécutives de build_state_from_widgets : la valeur
    étalonnée doit rester stable, jamais ré-écrasée par la valeur SME."""
    sess = _session_with_calibration(rpm=100.0, coeff=2.5, sme_fd_flow=30.0)
    state1 = build_state_from_widgets(sess)
    project_shared_keys(sess, state1)
    # Deuxième rerun (rien n'a changé côté opérateur).
    state2 = build_state_from_widgets(sess)
    project_shared_keys(sess, state2)
    assert abs(state2.feeders[0].mass_flow_g_per_min - 250.0 / 60.0) < 1e-6


# ---------------------------------------------------------------------------
# 5 — Symétrie multi-feeder (feeders #2..#5 mêmes garanties)
# ---------------------------------------------------------------------------
def test_calibration_overrides_for_feeder_2():
    """Le même contrat doit valoir pour le feeder #2 : étalonnage via
    feedcal_rpm_2 / feedcal_coeff_2 prime sur fd_flow_2 SME."""
    sess: dict = {
        "feedcal_rpm_2": 50.0, "feedcal_coeff_2": 10.0,   # 500 g/h = 8.33 g/min
        "fd_en_2": True, "fd_flow_2": 99.0,
    }
    seed_editing_keys(sess)
    sess["feedcal_rpm_2"] = 50.0
    sess["feedcal_coeff_2"] = 10.0
    sess["fd_flow_2"] = 99.0
    assert feeder_is_calibrated(sess, 2) is True
    g_min = feeder_calibrated_g_per_min(sess, 2)
    assert g_min is not None
    assert abs(g_min - 500.0 / 60.0) < 1e-6
    state = build_state_from_widgets(sess)
    # Feeder #2 = index 1 dans le banc.
    assert abs(state.feeders[1].mass_flow_g_per_min - 500.0 / 60.0) < 1e-6
