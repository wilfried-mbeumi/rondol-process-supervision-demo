"""Tests Phase A — étalonnage feeder RPM → débit réel (socle pur)."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from physics.conversions import g_per_h_to_g_per_min, g_per_h_to_g_per_s  # noqa: E402
from physics.feeder_flow import (  # noqa: E402
    MAX_FEEDER_FLOW_G_H,
    FeederFlow,
    resolve_feeder_flow,
)

TOL = 1e-6


# ---------------------------------------------------------------------------
# Conversions d'unités
# ---------------------------------------------------------------------------
def test_feeder_300_g_h_equals_5_g_min():
    assert abs(g_per_h_to_g_per_min(300.0) - 5.0) < TOL


def test_feeder_300_g_h_equals_0_0833_g_s():
    assert abs(g_per_h_to_g_per_s(300.0) - 0.083333) < 1e-5


def test_feeder_flow_unit_conversion_g_min_to_g_h():
    # 5 g/min = 300 g/h ; inverse cohérent.
    assert abs(g_per_h_to_g_per_min(300.0) - 5.0) < TOL
    assert abs(5.0 * 60.0 - 300.0) < TOL


def test_mass_flow_unit_conversion_g_h_g_min_g_s():
    ff = resolve_feeder_flow(30.0, 10.0)  # 300 g/h
    assert abs(ff.effective_g_h - 300.0) < TOL
    assert abs(ff.effective_g_min - 5.0) < TOL
    assert abs(ff.effective_g_s - 0.083333) < 1e-5


# ---------------------------------------------------------------------------
# Étalonnage (exemple Maël)
# ---------------------------------------------------------------------------
def test_feeder_calibration_30_rpm_300_g_h():
    ff = resolve_feeder_flow(30.0, 10.0)
    assert ff.calibrated is True
    assert abs(ff.requested_g_h - 300.0) < TOL
    assert abs(ff.effective_g_h - 300.0) < TOL
    assert ff.clamped is False


def test_feeder_calibration_50_rpm_500_g_h():
    # 50 RPM × 10 = 500 g/h DEMANDÉ, mais machine plafonnée à 300 g/h.
    ff = resolve_feeder_flow(50.0, 10.0)
    assert abs(ff.requested_g_h - 500.0) < TOL          # demandé conservé
    assert abs(ff.effective_g_h - MAX_FEEDER_FLOW_G_H) < TOL  # effectif plafonné
    assert ff.clamped is True


# ---------------------------------------------------------------------------
# Clamp machine (jamais silencieux)
# ---------------------------------------------------------------------------
def test_feeder_flow_clamped_above_300_g_h():
    ff = resolve_feeder_flow(80.0, 10.0)  # 800 g/h demandé
    assert ff.clamped is True
    assert abs(ff.effective_g_h - 300.0) < TOL
    assert abs(ff.effective_g_min - 5.0) < TOL


def test_feeder_flow_not_clamped_below_300_g_h():
    ff = resolve_feeder_flow(18.0, 10.0)  # 180 g/h = 3 g/min
    assert ff.clamped is False
    assert abs(ff.effective_g_h - 180.0) < TOL
    assert abs(ff.effective_g_min - 3.0) < TOL


def test_requested_flow_is_preserved_for_display():
    ff = resolve_feeder_flow(80.0, 10.0)
    assert abs(ff.requested_g_h - 800.0) < TOL  # affichage = valeur demandée
    assert abs(ff.effective_g_h - 300.0) < TOL  # calcul = valeur plafonnée


# ---------------------------------------------------------------------------
# Pas de débit sans étalonnage (on ne devine jamais)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("calib", [None, 0.0, -5.0])
def test_no_real_mass_flow_without_feeder_calibration(calib):
    ff = resolve_feeder_flow(30.0, calib)
    assert ff.calibrated is False
    assert ff.requested_g_h is None
    assert ff.effective_g_h is None
    assert ff.effective_g_min is None
    assert ff.effective_g_s is None


# ---------------------------------------------------------------------------
# Anti-hardcode : 10 g/h/RPM et 300 g/h ne sont pas des vérités épars
# ---------------------------------------------------------------------------
def test_no_hardcoded_10_g_h_per_rpm_as_universal_truth():
    # Le coefficient est un PARAMÈTRE : un autre coefficient donne un autre débit.
    ff7 = resolve_feeder_flow(30.0, 7.0)
    assert abs(ff7.requested_g_h - 210.0) < TOL  # 30 × 7, pas 30 × 10
    # Et la fonction n'impose pas 10 par défaut (None => non calibré).
    assert resolve_feeder_flow(30.0, None).calibrated is False


def test_max_feeder_flow_is_centralized_constant():
    # Le plafond machine est une constante nommée, pas un littéral épars.
    assert MAX_FEEDER_FLOW_G_H == 300.0
    src = inspect.getsource(resolve_feeder_flow)
    assert "300" not in src, "literal 300 dans resolve_feeder_flow — utiliser la constante"
