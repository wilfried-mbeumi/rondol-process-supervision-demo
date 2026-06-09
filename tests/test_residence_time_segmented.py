"""tests/test_residence_time_segmented.py — Module pur résidence V2.

Source : `app/specification_residence_time_extrudeur.pdf` (manager).

Tests PURS, sans Streamlit, sans I/O, sans accès au reste du projet.
Le module V2 n'est PAS branché dans l'UI au premier jet (manager 2026-06-09) —
ces tests servent de socle d'acceptation pour une intégration ultérieure après
validation par test traceur (§13 de la spec).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from physics.residence_time_segmented import (  # noqa: E402
    DEFAULT_RPM_REFERENCE,
    FeederInput,
    SegmentInput,
    build_segmented_report,
    compute_feeder_volumetric_flow,
    compute_global_weighted_residence_time,
    compute_segment_capacity,
    compute_segment_fill_factor,
    compute_segment_residence_time,
)


# ---------------------------------------------------------------------------
# Briques pures
# ---------------------------------------------------------------------------
def test_feeder_volumetric_flow_graphite_pvdf_example():
    """Exemple §10 spec : 200 g/h ÷ 0.53 g/cm³ ÷ 3600 ≈ 0.1048 cm³/s."""
    q = compute_feeder_volumetric_flow(200.0, 0.53)
    assert abs(q - 0.10482) < 1e-4


@pytest.mark.parametrize("m,rho", [(0.0, 0.55), (-1.0, 0.55), (200.0, 0.0), (200.0, -0.5)])
def test_feeder_volumetric_flow_returns_zero_when_inactive(m, rho):
    assert compute_feeder_volumetric_flow(m, rho) == 0.0


def test_segment_capacity_scales_linearly_with_rpm():
    """Spec §4.2 : si RPM double, capacité double (k_capacity=1)."""
    cap_100 = compute_segment_capacity(0.569, 100.0, rpm_reference=100.0)
    cap_200 = compute_segment_capacity(0.569, 200.0, rpm_reference=100.0)
    assert abs(cap_200 - 2.0 * cap_100) < 1e-9


def test_segment_capacity_zero_when_rpm_invalid():
    assert compute_segment_capacity(0.569, 0.0) == 0.0
    assert compute_segment_capacity(0.569, -10.0) == 0.0
    assert compute_segment_capacity(0.0, 100.0) == 0.0


def test_segment_fill_factor_clamped_to_1():
    """Spec §4.3 : FF = min(q/cap, 1.0)."""
    assert compute_segment_fill_factor(2.0, 1.0) == 1.0
    assert abs(compute_segment_fill_factor(0.5, 1.0) - 0.5) < 1e-9
    assert compute_segment_fill_factor(0.0, 1.0) == 0.0
    assert compute_segment_fill_factor(1.0, 0.0) == 0.0


def test_segment_residence_time_basic():
    """t = V × FF × Kscrew × Kmaterial × Kdie / q. Avec V=27, FF=0.185, q=0.105,
    K=1 → 27×0.185/0.105 ≈ 47.6 s (exemple §10 spec)."""
    t = compute_segment_residence_time(
        free_volume_cm3=27.0, fill_factor=0.185, q_total_cm3_s=0.105,
    )
    assert abs(t - 47.57) < 0.5  # tolérance 0,5 s


def test_segment_residence_time_zero_when_no_flow():
    assert compute_segment_residence_time(27.0, 0.185, 0.0) == 0.0


def test_segment_residence_time_with_screw_and_material_factors():
    """K_screw=2, K_material=1.5 → temps multiplié par 3."""
    base = compute_segment_residence_time(27.0, 0.185, 0.105)
    enriched = compute_segment_residence_time(
        27.0, 0.185, 0.105, k_screw=2.0, k_material=1.5,
    )
    assert abs(enriched - 3.0 * base) < 1e-6


# ---------------------------------------------------------------------------
# Moyenne pondérée globale
# ---------------------------------------------------------------------------
def test_global_weighted_residence_returns_none_when_no_mass_flow():
    from physics.residence_time_segmented import FeederResult
    fr = (
        FeederResult(name="F1", entry_zone=0, mass_flow_g_h=0.0, residence_time_s=100.0),
    )
    assert compute_global_weighted_residence_time(fr) is None


def test_global_weighted_residence_with_two_feeders():
    """Spec §11 : t_global = Σ(t_i × ṁ_i) / Σ(ṁ_i)."""
    from physics.residence_time_segmented import FeederResult
    fr = (
        FeederResult(name="F1", entry_zone=0, mass_flow_g_h=200.0, residence_time_s=100.0),
        FeederResult(name="F2", entry_zone=3, mass_flow_g_h=100.0, residence_time_s=40.0),
    )
    t_global = compute_global_weighted_residence_time(fr)
    # (200×100 + 100×40) / 300 = 24000/300 = 80.
    assert abs(t_global - 80.0) < 1e-9


# ---------------------------------------------------------------------------
# Orchestration build_segmented_report
# ---------------------------------------------------------------------------
def _example_segments():
    """Vis simplifiée à 3 segments (Z0→Z2, Z2→Z5, Z5→filière)."""
    return [
        SegmentInput("Z0→Z2", 0, 2, free_volume_cm3=10.0,
                     capacity_ref_cm3_s=0.20),
        SegmentInput("Z2→Z5", 2, 5, free_volume_cm3=15.0,
                     capacity_ref_cm3_s=0.25),
        SegmentInput("Z5→DIE", 5, 9, free_volume_cm3=10.0,
                     capacity_ref_cm3_s=0.15),
    ]


def test_single_feeder_residence_decreases_with_rpm():
    """Spec critique : t doit DIMINUER quand le RPM augmente (à débit constant)."""
    feeders = [FeederInput("F1", entry_zone=0, mass_flow_g_h=200.0,
                            bulk_density_g_cm3=0.55)]
    segs = _example_segments()
    rpt_100 = build_segmented_report(feeders, segs, rpm_screw=100.0)
    rpt_200 = build_segmented_report(feeders, segs, rpm_screw=200.0)
    rpt_50 = build_segmented_report(feeders, segs, rpm_screw=50.0)
    t_100 = rpt_100.feeders[0].residence_time_s
    t_200 = rpt_200.feeders[0].residence_time_s
    t_50 = rpt_50.feeders[0].residence_time_s
    # Pas forcément exactement /2 (le FF peut saturer), mais STRICTEMENT
    # décroissant : t(50) > t(100) > t(200) > 0.
    assert t_50 > t_100 > t_200 > 0.0


def test_two_feeders_side_feeder_shorter_residence():
    """Spec §6 : un feeder entré en Z3 a une résidence plus courte que le main."""
    feeders = [
        FeederInput("Main", entry_zone=0, mass_flow_g_h=200.0,
                    bulk_density_g_cm3=0.55),
        FeederInput("Side", entry_zone=3, mass_flow_g_h=50.0,
                    bulk_density_g_cm3=0.50),
    ]
    segs = _example_segments()
    rpt = build_segmented_report(feeders, segs, rpm_screw=100.0)
    t_main = next(f.residence_time_s for f in rpt.feeders if f.name == "Main")
    t_side = next(f.residence_time_s for f in rpt.feeders if f.name == "Side")
    assert t_side < t_main
    assert t_side > 0.0


def test_segmented_no_feeder_returns_none_global():
    """Aucun feeder actif → global non calculable (None, jamais 0)."""
    feeders = [FeederInput("F1", entry_zone=0, mass_flow_g_h=0.0,
                            bulk_density_g_cm3=0.55)]
    segs = _example_segments()
    rpt = build_segmented_report(feeders, segs, rpm_screw=100.0)
    assert rpt.global_residence_time_s is None
    assert all(s.residence_time_s == 0.0 for s in rpt.segments)


def test_segmented_zero_rpm_returns_zero_capacity_zero_residence():
    """rpm=0 → capacité=0 → t=0 partout, global None."""
    feeders = [FeederInput("F1", entry_zone=0, mass_flow_g_h=200.0,
                            bulk_density_g_cm3=0.55)]
    segs = _example_segments()
    rpt = build_segmented_report(feeders, segs, rpm_screw=0.0)
    assert all(s.capacity_cm3_s == 0.0 for s in rpt.segments)
    assert all(s.residence_time_s == 0.0 for s in rpt.segments)


def test_segmented_kneading_segment_doubles_residence():
    """Spec §7 : K_screw plus élevé dans un kneading 90° → t plus grand."""
    feeders = [FeederInput("F1", entry_zone=0, mass_flow_g_h=200.0,
                            bulk_density_g_cm3=0.55)]
    base = _example_segments()
    enriched = [
        SegmentInput("Z0→Z2", 0, 2, 10.0, 0.20),
        SegmentInput("Z2→Z5 kneading", 2, 5, 15.0, 0.25, k_screw=2.5),  # +rétention
        SegmentInput("Z5→DIE", 5, 9, 10.0, 0.15),
    ]
    rpt_base = build_segmented_report(feeders, base, 100.0)
    rpt_enr = build_segmented_report(feeders, enriched, 100.0)
    assert rpt_enr.feeders[0].residence_time_s > rpt_base.feeders[0].residence_time_s


def test_default_rpm_reference_is_100():
    """rpm_ref par défaut = 100, conformément à la correction manager V1."""
    assert DEFAULT_RPM_REFERENCE == 100.0
