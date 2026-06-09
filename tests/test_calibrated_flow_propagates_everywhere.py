"""tests/test_calibrated_flow_propagates_everywhere.py

BUG 1 manager 2026-06-09 — propagation du débit étalonné dans TOUTE l'app.

Scénario manager imposé : RPM #1 = 100, coefficient #1 = 2,5 g/h/RPM
  → débit total = 250 g/h = 4,17 g/min.

Cette valeur DOIT être lue partout :
  - Settings (multi-feeder total)
  - Profile (legacy feeder_g_per_min)
  - Supervision (legacy)
  - Moteur Procédé (crs.feed_rate via build_moteur_inputs)
  - Analyse run (via current_run_state)
  - Historique (via current_run_state au commit)
  - Agent IA (via state.feeders[0].mass_flow_g_per_min)

Aucune ancienne valeur `fd_flow_1` ni `feeder_g_per_min` traînant en session
(par exemple restaurée du miroir disque opérateur) ne doit écraser le débit
étalonné courant.

Régression antérieure (commit b9195f8) : project_to_legacy était devenu
setdefault-only pour TOUTES les clés, ce qui bloquait la propagation du débit
étalonné quand une valeur ancienne traînait en session. Correctif chirurgical
(ce commit) : asymétrie — saisies utilisateur restent setdefault-only mais
`feeder_g_per_min` étalonné écrase TOUJOURS.
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

from AgentIndustrial_v1.core.applied_state import commit as applied_commit  # noqa: E402
from AgentIndustrial_v1.core.current_run_state import build_current_run_state  # noqa: E402
from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    project_shared_keys,
    seed_editing_keys,
)
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
from AgentIndustrial_v1.core.recommendations import build_recommendations  # noqa: E402
from run_state_adapter import (  # noqa: E402
    build,
    build_moteur_inputs_from_current_run_state,
    sync_legacy_projection,
)
from history_store import flat_params_from_snapshot, make_record  # noqa: E402

# ---------------------------------------------------------------------------
# Scénario manager
# ---------------------------------------------------------------------------
RPM = 100.0
COEFF = 2.5            # 100 × 2.5 = 250 g/h
EXPECTED_GH = 250.0
EXPECTED_GMIN = 250.0 / 60.0   # 4.1667
TOL = 0.01


def _fresh_session_with_calibration(legacy_residual: float | None = None):
    """Session simulant un boot d'app : étalonnage calibré, optionnellement
    avec une valeur `feeder_g_per_min` ancienne résiduelle (cas réel : valeur
    restaurée depuis le miroir disque opérateur après une session précédente)."""
    sess: dict = {
        "feeder_rpm": RPM,
        "feeder_calib_g_h_per_rpm": COEFF,
        "fd_en_1": True,
    }
    seed_editing_keys(sess)
    sess["feeder_rpm"] = RPM
    sess["feeder_calib_g_h_per_rpm"] = COEFF
    if legacy_residual is not None:
        sess["feeder_g_per_min"] = legacy_residual
    return sess


# ---------------------------------------------------------------------------
# 1 — Settings : Débit total multi-feeder = 250 g/h
# ---------------------------------------------------------------------------
def test_settings_total_flow_is_250_gh():
    """Le total multi-feeder vu par Settings (`crs.feed_rate`) = 250 g/h."""
    sess = _fresh_session_with_calibration()
    crs = build_current_run_state(sess)
    assert crs.feed_rate.value is not None
    assert abs(crs.feed_rate.value - EXPECTED_GH) < TOL


# ---------------------------------------------------------------------------
# 2 — Profile : feeder_g_per_min = 4,17 g/min
# ---------------------------------------------------------------------------
def test_profile_feeder_g_per_min_is_calibrated_value():
    """Profile lit `feeder_g_per_min` via sync_legacy_projection au boot."""
    sess = _fresh_session_with_calibration()
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - EXPECTED_GMIN) < TOL


def test_profile_feeder_g_per_min_overrides_legacy_residual():
    """CŒUR DE BUG 1 : une valeur résiduelle ancienne (30 g/min restaurée du
    miroir disque) ne doit PAS bloquer la propagation du débit étalonné."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - EXPECTED_GMIN) < TOL


@pytest.mark.parametrize("residual", [0.0, 1.0, 30.0, 99.0, 500.0])
def test_profile_feeder_g_per_min_overrides_any_residual(residual):
    """Robustesse : quelle que soit la valeur ancienne, la nouvelle calibration
    écrase systématiquement."""
    sess = _fresh_session_with_calibration(legacy_residual=residual)
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - EXPECTED_GMIN) < TOL


# ---------------------------------------------------------------------------
# 3 — Supervision : même flux que Profile (legacy feeder_g_per_min)
# ---------------------------------------------------------------------------
def test_supervision_feeder_g_per_min_propagated():
    """Supervision lit `feeder_g_per_min` legacy après son propre boot."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - EXPECTED_GMIN) < TOL


# ---------------------------------------------------------------------------
# 4 — Moteur Procédé : crs.feed_rate (TOTAL multi-feeder)
# ---------------------------------------------------------------------------
def test_moteur_procede_feed_g_per_min_is_calibrated():
    """Moteur Procédé lit `feed_g_per_min` via build_moteur_inputs."""
    sess = _fresh_session_with_calibration()
    crs = build_current_run_state(sess)
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - EXPECTED_GMIN) < TOL


# ---------------------------------------------------------------------------
# 5 — Analyse run : utilise current_run_state (via Supervision)
# ---------------------------------------------------------------------------
def test_analyse_run_sees_calibrated_total():
    """Analyse run construit ses indicateurs depuis le même current_run_state."""
    sess = _fresh_session_with_calibration()
    crs = build_current_run_state(sess)
    assert abs(crs.feed_rate.value - EXPECTED_GH) < TOL


# ---------------------------------------------------------------------------
# 6 — Historique : commit du snapshot capture le débit étalonné
# ---------------------------------------------------------------------------
def test_historique_snapshot_captures_calibrated_flow():
    """Au commit, l'historique fige le débit étalonné (pas une valeur SME
    ancienne)."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    # 1. État dérivé via build_state_from_widgets (calibration prime sur SME).
    state = build_state_from_widgets(sess)
    # 2. project_shared_keys propage vers les clés legacy.
    project_shared_keys(sess, state)
    # 3. Snapshot capturé.
    snap = applied_commit(sess, state, label="manager")
    # 4. flat_params pour history_store.
    fp = flat_params_from_snapshot(snap)
    assert abs(fp["feed_g_per_min"] - EXPECTED_GMIN) < TOL


# ---------------------------------------------------------------------------
# 7 — Agent IA : state.feeders[0].mass_flow_g_per_min = débit étalonné
# ---------------------------------------------------------------------------
def test_agent_ia_uses_calibrated_flow_in_state():
    """L'Agent IA consomme `state.feeders[0].mass_flow_g_per_min`. Cette valeur
    DOIT être le débit étalonné, pas la saisie SME résiduelle."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    # Saisie SME résiduelle parasite : fd_flow_1=30 (défaut historique).
    sess["fd_flow_1"] = 30.0
    state = build_state_from_widgets(sess)
    assert abs(state.feeders[0].mass_flow_g_per_min - EXPECTED_GMIN) < TOL


def test_agent_ia_recommendations_use_current_flow():
    """Les recos AgentIndustrial doivent refléter le débit étalonné courant
    (et pas un débit résiduel ancien). Test par contraposée : avec 4,17 g/min
    on a une FF_STARVATION (sous-alimentation) ; avec une valeur plus haute
    on n'aurait pas la même alerte."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    sess["fd_flow_1"] = 30.0
    state = build_state_from_widgets(sess)
    # Le débit utilisé par l'IA est bien 4,17, pas 30.
    assert abs(state.feeders[0].mass_flow_g_per_min - EXPECTED_GMIN) < TOL
    # Et evaluate() produit ses alertes sur ce débit (pas sur 30).
    report = evaluate(state)
    recos = build_recommendations(state, report.alerts)
    # Au moins une reco doit exister (le scénario manager est en sous-débit).
    assert len(recos) > 0


# ---------------------------------------------------------------------------
# 8 — Bouclage : modification de calibration se propage instantanément
# ---------------------------------------------------------------------------
def test_calibration_change_propagates_instantly():
    """Manager : 100×2,5 → 120×3 = 360 g/h = 6 g/min. La nouvelle valeur DOIT
    être lue partout au prochain rerun."""
    sess = _fresh_session_with_calibration(legacy_residual=30.0)
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - EXPECTED_GMIN) < TOL

    # L'utilisateur change la calibration.
    sess["feeder_rpm"] = 120.0
    sess["feeder_calib_g_h_per_rpm"] = 3.0
    crs = build_current_run_state(sess)
    sync_legacy_projection(sess)
    assert abs(sess["feeder_g_per_min"] - 6.0) < TOL
    assert abs(crs.feed_rate.value - 360.0) < TOL


# ---------------------------------------------------------------------------
# 9 — Non-régression Pb #2 (saisies utilisateur restent setdefault-only)
# ---------------------------------------------------------------------------
def test_screw_config_still_not_overwritten_pb2():
    """Pb #2 (édition vis annulée) ne doit pas réapparaître."""
    from screw_logic import (
        add_elements_atomic, count_user_elements, new_empty_configuration,
    )
    sess: dict = {}
    seed_editing_keys(sess)
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 5)
    sess["screw_config"] = cfg
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap_pb2")
    add_elements_atomic(sess["screw_config"], 7, 2)
    sync_legacy_projection(sess)
    assert count_user_elements(sess["screw_config"]) == 7.0


@pytest.mark.parametrize("key,initial,edited", [
    ("screw_rpm", 120.0, 200.0),
    ("bulk_density", 0.55, 0.80),
])
def test_user_inputs_still_setdefault_only(key, initial, edited):
    """screw_rpm et bulk_density restent protégées de l'écrasement par snapshot."""
    sess: dict = {"fd_en_1": True, "fd_flow_1": 30.0, key: initial}
    seed_editing_keys(sess)
    sess[key] = initial
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap")
    sess[key] = edited
    sync_legacy_projection(sess)
    assert sess[key] == edited
