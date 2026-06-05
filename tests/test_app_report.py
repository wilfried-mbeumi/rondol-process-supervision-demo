"""Tests portage app — engine/app_report.py (builder PUR, hors Streamlit).

Vérifie que le vue-modèle EngineReport :
  - expose les KPIs machine + couple total + SME totale ;
  - matérialise torque_nm (float ≥ 0) sur les 81 positions ;
  - garde E6/E7 (t_real_c / pressure_bar) à None ;
  - reste cohérent avec les briques sous-jacentes (Σ torque_nm ≈ total_torque,
    SME == P/ṁ, agrégats == aggregate_machine) ;
  - gère les gardes (rpm=0, ṁ=0 → couple/SME nuls) ;
  - n'introduit pas de dépendance Streamlit (import pur).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402
from engine.extrusion_graph import build_graph  # noqa: E402
from engine.enrich import enrich_graph  # noqa: E402
from engine.aggregate import aggregate_machine  # noqa: E402
from engine.torque import total_torque  # noqa: E402
from engine.app_report import (  # noqa: E402
    EngineReport,
    PositionRow,
    ZoneRow,
    build_engine_report,
    total_power_w,
    total_sme_kwh_per_kg,
    mass_flow_kg_per_h,
)
from physics.conversions import rpm_to_rps, g_per_s_to_kg_per_h  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _params(rpm: float = 150.0, f2: float = 0.2):
    return sl.ProcessParams(
        screw_rpm=rpm,
        feeder1_flow_rate_g_per_s=0.5, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=f2, feeder2_bulk_density=1.0,
        side_feeder_zone=3,
        temp_z=(20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0),
    )


def _config():
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 4)
    sl.add_elements_atomic(cfg, 4, 2)
    sl.add_elements_atomic(cfg, 9, 1)
    return cfg


def _report(rpm: float = 150.0, f2: float = 0.2):
    return build_engine_report(
        _config(), _params(rpm=rpm, f2=f2),
        POWDERS["LFP"], POWDERS["LATP"],
    )


def test_report_is_engine_report_with_expected_shape():
    r = _report()
    assert isinstance(r, EngineReport)
    assert len(r.positions) == 81
    assert all(isinstance(p, PositionRow) for p in r.positions)
    assert len(r.zones) == 9
    assert all(isinstance(z, ZoneRow) for z in r.zones)
    assert r.feeder1_material == POWDERS["LFP"].name
    assert r.feeder2_material == POWDERS["LATP"].name


def test_torque_materialized_on_all_positions():
    """torque_nm non-None, float, fini, ≥ 0 sur les 81 positions."""
    r = _report()
    for p in r.positions:
        assert isinstance(p.torque_nm, float)
        assert math.isfinite(p.torque_nm)
        assert p.torque_nm >= 0.0


def test_e6_e7_remain_none():
    """E6 (T_real) et E7 (pression) non calculés → None (statut « à venir »)."""
    r = _report()
    assert r.t_real_c is None
    assert r.pressure_bar is None


def test_totals_positive_and_finite():
    r = _report()
    for v in (r.total_torque_nm, r.total_power_w, r.total_sme_kwh_per_kg,
              r.mass_flow_kg_per_h):
        assert math.isfinite(v) and v > 0.0


def test_sum_torque_matches_total_torque():
    """Σ torque_nm (positions) ≈ total_torque_nm (à tolérance flottante)."""
    r = _report()
    s = sum(p.torque_nm for p in r.positions)
    assert math.isclose(s, r.total_torque_nm, rel_tol=1e-12, abs_tol=1e-15)


def test_sme_equals_power_over_mass_flow():
    """SME totale == (P/1000) / ṁ_kg_h (définition, pas de nouvelle physique)."""
    r = _report()
    expected = (r.total_power_w / 1000.0) / r.mass_flow_kg_per_h
    assert math.isclose(r.total_sme_kwh_per_kg, expected, rel_tol=1e-12)


def test_power_equals_2pi_n_torque():
    """P_total == 2π·N · couple_total (réutilise E4, pas de recalcul)."""
    r = _report()
    n_rps = rpm_to_rps(r.screw_rpm)
    expected = 2.0 * math.pi * n_rps * r.total_torque_nm
    assert math.isclose(r.total_power_w, expected, rel_tol=1e-12)


def test_mass_flow_matches_feeder_sum():
    p = _params(f2=0.2)
    expected = g_per_s_to_kg_per_h(0.5 + 0.2)
    assert math.isclose(mass_flow_kg_per_h(p), expected, rel_tol=1e-12)


def test_aggregates_consistent_with_machine_state():
    """Les ZoneRow/KPIs reflètent aggregate_machine du graph enrichi (pas de divergence)."""
    cfg = _config()
    params = _params()
    enriched = enrich_graph(build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"]))
    machine = aggregate_machine(enriched)
    r = build_engine_report(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    assert r.fill_factor_average == machine.fill_factor_average
    assert r.residence_time_total_s == machine.residence_time_total_s
    assert r.max_shear_rate_s == machine.max_shear_rate_s
    assert r.peak_fill_position == machine.peak_fill_position
    assert r.total_torque_nm == total_torque(enriched)
    for zr, zs in zip(r.zones, machine.zones):
        assert zr.zone == zs.zone
        assert zr.mean_fill_factor == zs.mean_fill_factor
        assert zr.max_shear_rate_s == zs.max_shear_rate_s
        assert zr.dominant_material == zs.dominant_material


def test_zero_rpm_gives_zero_torque_and_sme():
    """rpm = 0 → couple et SME nuls (gardes), report toujours bien formé."""
    r = _report(rpm=0.0)
    assert r.total_torque_nm == 0.0
    assert r.total_power_w == 0.0
    assert r.total_sme_kwh_per_kg == 0.0
    assert all(p.torque_nm == 0.0 for p in r.positions)


def test_zero_mass_flow_gives_zero_sme():
    """ṁ = 0 → SME = 0.0 (pas de division par zéro)."""
    cfg = _config()
    params = sl.ProcessParams(
        screw_rpm=150.0,
        feeder1_flow_rate_g_per_s=0.0, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.0, feeder2_bulk_density=1.0,
        side_feeder_zone=0,
        temp_z=(20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0),
    )
    r = build_engine_report(cfg, params, POWDERS["LFP"])
    assert r.mass_flow_kg_per_h == 0.0
    assert r.total_sme_kwh_per_kg == 0.0


def test_single_feeder_report_has_no_feeder2_material():
    cfg = _config()
    params = sl.ProcessParams(
        screw_rpm=120.0, feeder1_flow_rate_g_per_s=0.5,
        feeder1_bulk_density=1.0,
    )
    r = build_engine_report(cfg, params, POWDERS["LFP"])
    assert r.feeder1_material == POWDERS["LFP"].name
    assert r.feeder2_material is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("app_report: all tests passed")
