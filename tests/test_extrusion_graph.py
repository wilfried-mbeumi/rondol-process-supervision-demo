"""Tests Phase 2 — engine/extrusion_graph.py.

Vérifie : 81 nœuds ordonnés, Network 7 appelé UNE SEULE FOIS (anti-2e-moteur),
nœuds enveloppant le MÊME ProcessState, accès par zone/port cohérents.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402
from engine import extrusion_graph as eg  # noqa: E402
from engine.extrusion_graph import build_graph, N_ZONES  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _cfg_params():
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 5)
    sl.add_elements_atomic(cfg, 4, 3)
    params = sl.ProcessParams(
        screw_rpm=120.0,
        feeder1_flow_rate_g_per_s=0.6, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.3, feeder2_bulk_density=1.0,
        side_feeder_zone=4,
        temp_z=(20.0, 50.0, 70.0, 90.0, 110.0, 130.0, 150.0, 170.0, 190.0),
    )
    return cfg, params


def test_graph_has_81_ordered_nodes():
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    assert len(g) == sl.N_POSITIONS == 81
    for pos, node in enumerate(g):
        assert node.position == pos
    assert g[0].position == 0
    assert g.node_at(sl.TIP_PART1_POS).port_kind == "die"


def test_network7_called_exactly_once(monkeypatch):
    """build_graph n'exécute Network 7 qu'une fois (pas de 2e moteur)."""
    calls = {"n": 0}
    real = sl.compute_process_state

    def counting(cfg, params):
        calls["n"] += 1
        return real(cfg, params)

    monkeypatch.setattr(eg, "compute_process_state", counting)
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    assert calls["n"] == 1
    # Les 81 nœuds partagent le ProcessState unique exposé par le graph.
    for node in g:
        assert node.fill_factor == g.process_state.fill_factor_local[node.position]


def test_nodes_wrap_same_process_state():
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    st = g.process_state
    for n in g:
        i = n.position
        assert n.vol_flow_cm3_s == st.vol_flow_cm3_s[i]
        assert n.residence_time_s == st.residence_time_local[i]
        assert n.local_free_volume_cm3 == st.local_free_volume_cm3[i]


def test_zone_partition_is_complete_and_consistent():
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    seen = 0
    for z in range(N_ZONES):
        zone_nodes = g.nodes_in_zone(z)
        for n in zone_nodes:
            assert n.zone == z == sl.position_to_zone(n.position)
        seen += len(zone_nodes)
    assert seen == sl.N_POSITIONS  # partition complète des 81 positions


def test_ports_present():
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    kinds = {n.port_kind for n in g.ports()}
    assert "main_feed" in kinds
    assert "die" in kinds
    assert "side_feed" in kinds  # side_feeder_zone=4 actif


def test_first_parts_excludes_part2():
    cfg, params = _cfg_params()
    g = build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    assert all(not n.is_part2 for n in g.first_parts())
    # Au moins un élément entier → au moins une part2 exclue.
    assert len(g.first_parts()) < len(g)


def test_build_graph_pure():
    cfg, params = _cfg_params()
    snap = list(cfg)
    build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])
    assert cfg == snap


if __name__ == "__main__":
    # Exécution directe sans pytest : monkeypatch indisponible → on saute ce test.
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn) and "monkeypatch" not in fn.__code__.co_varnames:
            fn()
            print(f"OK {name}")
    print("extrusion_graph: direct tests passed (monkeypatch test via pytest)")
