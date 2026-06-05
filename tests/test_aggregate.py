"""Tests Phase 2 — engine/aggregate.py.

Test CLÉ anti-divergence : Σ ZoneState.residence == MachineState.residence_total
== ProcessState.residence_time_total (réutilisation, pas re-somme). Vérifie aussi
la réutilisation des overflow/fill_average et la finitude des agrégats nouveaux.
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
from engine.extrusion_graph import build_graph, N_ZONES  # noqa: E402
from engine.aggregate import aggregate_machine, aggregate_zone  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _graph():
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 6)
    sl.add_elements_atomic(cfg, 4, 3)
    sl.add_elements_atomic(cfg, 9, 1)
    params = sl.ProcessParams(
        screw_rpm=140.0,
        feeder1_flow_rate_g_per_s=0.7, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.3, feeder2_bulk_density=1.0,
        side_feeder_zone=3,
        temp_z=(20.0, 50.0, 70.0, 90.0, 110.0, 130.0, 150.0, 170.0, 190.0),
    )
    return build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])


def test_residence_sum_matches_process_state():
    """Σ zones == total machine == ProcessState.residence_time_total."""
    g = _graph()
    m = aggregate_machine(g)
    sum_zones = sum(z.residence_time_s for z in m.zones)
    assert abs(sum_zones - m.residence_time_total_s) < 1e-9
    assert abs(m.residence_time_total_s - g.process_state.residence_time_total) < 1e-12
    # Et chaque zone est littéralement le total de zone Network 7.
    for z in range(N_ZONES):
        assert m.zones[z].residence_time_s == g.process_state.residence_time_zone[z]


def test_machine_reuses_process_state_scalars():
    """fill_average / overflow réutilisés verbatim de ProcessState."""
    g = _graph()
    m = aggregate_machine(g)
    st = g.process_state
    assert m.fill_factor_average == st.fill_factor_average
    assert m.overflow_main_feeder == st.overflow_main_feeder
    assert m.overflow_side_feeder == st.overflow_side_feeder
    assert m.output_vol_flow_cm3_s == st.vol_flow_cm3_s[sl.TIP_PART1_POS]


def test_new_aggregates_are_finite_and_bounded():
    """Cisaillement/remplissage agrégés : finis, fill ∈ [0,1]."""
    g = _graph()
    m = aggregate_machine(g)
    assert math.isfinite(m.max_shear_rate_s) and m.max_shear_rate_s >= 0.0
    assert 0.0 <= m.peak_fill_factor <= 1.0
    assert 0 <= m.peak_fill_position < sl.N_POSITIONS
    for z in m.zones:
        assert math.isfinite(z.max_shear_rate_s)
        assert math.isfinite(z.mean_shear_rate_s)
        assert 0.0 <= z.mean_fill_factor <= 1.0
        assert 0.0 <= z.max_fill_factor <= 1.0


def test_zone_partition_counts_cover_all_positions():
    g = _graph()
    total = sum(aggregate_zone(g, z).n_nodes for z in range(N_ZONES))
    assert total == sl.N_POSITIONS


def test_dominant_material_reflects_blend_downstream():
    """Une zone en aval du side feeder porte un mélange dominant."""
    g = _graph()
    side_zone = g.params.side_feeder_zone
    downstream = aggregate_zone(g, side_zone + 1)
    if downstream.n_nodes and downstream.dominant_material is not None:
        assert "+" in downstream.dominant_material  # label de mélange "A+B"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("aggregate: all tests passed")
