"""Tests E4b — engine/enrich.py.

Vérifie la matérialisation du couple local dans `NodeState.torque_nm` via
`dataclasses.replace`, SANS muter l'original, SANS recalculer le procédé ni les
agrégats, et avec E5/E6/E7 toujours None.

Invariants couverts :
  - 81 nœuds enrichis : torque_nm non-None, float, fini, ≥ 0.
  - nœuds originaux inchangés (torque_nm None) ; enriched is not graph ;
    enriched.nodes[i] is not graph.nodes[i].
  - enriched.process_state is graph.process_state ; enriched.params is graph.params
    (pas de 2e moteur, pas de re-propagation).
  - E5/E6/E7 restent None ; NodeState garde 21 champs.
  - agrégats Phase 2 identiques (enrichi vs original).
  - sum(torque_nm) == total_torque(enriched) == total_torque(graph) (tolérance).
  - enrich_node/enrich_graph déterministes ; screw_rpm=0 → torque_nm=0.0 partout.
"""

from __future__ import annotations

import dataclasses as dc
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402
from engine.extrusion_graph import build_graph  # noqa: E402
from engine.node_state import NodeState  # noqa: E402
from engine.torque import total_torque  # noqa: E402
from engine.aggregate import aggregate_machine, aggregate_zone  # noqa: E402
from engine.enrich import enrich_node, enrich_nodes, enrich_graph  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _graph(rpm: float = 150.0):
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 4)
    sl.add_elements_atomic(cfg, 4, 2)
    sl.add_elements_atomic(cfg, 9, 1)
    params = sl.ProcessParams(
        screw_rpm=rpm,
        feeder1_flow_rate_g_per_s=0.5, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.2, feeder2_bulk_density=1.0,
        side_feeder_zone=3,
        temp_z=(20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0),
    )
    return build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])


# --- torque_nm matérialisé sur les 81 nœuds ----------------------------------

def test_torque_materialized_on_all_nodes():
    """Les 81 nœuds enrichis ont torque_nm non-None, float, fini, ≥ 0."""
    g = _graph()
    e = enrich_graph(g)
    assert len(e.nodes) == 81
    for n in e:
        assert n.torque_nm is not None
        assert isinstance(n.torque_nm, float)
        assert math.isfinite(n.torque_nm)
        assert n.torque_nm >= 0.0


# --- Originaux inchangés / nouvelles instances -------------------------------

def test_originals_unchanged_torque_none():
    """Les nœuds du graph d'origine gardent torque_nm None après enrichissement."""
    g = _graph()
    _ = enrich_graph(g)
    for n in g:
        assert n.torque_nm is None


def test_enriched_is_new_graph_and_new_nodes():
    """enriched is not graph ; chaque nœud enrichi est une nouvelle instance."""
    g = _graph()
    e = enrich_graph(g)
    assert e is not g
    for i in range(len(g.nodes)):
        assert e.nodes[i] is not g.nodes[i]


# --- Pas de 2e moteur : références partagées ---------------------------------

def test_process_state_and_params_shared_by_reference():
    """enriched réutilise process_state/params/feed_context PAR RÉFÉRENCE."""
    g = _graph()
    e = enrich_graph(g)
    assert e.process_state is g.process_state
    assert e.params is g.params
    assert e.feed_context is g.feed_context


# --- E5/E6/E7 intacts, structure NodeState inchangée -------------------------

def test_e5_e6_e7_remain_none():
    """E5/E6/E7 restent None sur les nœuds enrichis (seul E4 est matérialisé)."""
    g = _graph()
    e = enrich_graph(g)
    for n in e:
        assert n.sme_kwh_per_kg is None
        assert n.t_real_c is None
        assert n.pressure_bar is None


def test_nodestate_structure_unchanged():
    """NodeState garde 21 champs (aucun champ ajouté/retiré par E4b)."""
    names = [f.name for f in dc.fields(NodeState)]
    assert len(names) == 21
    assert "torque_nm" in names


# --- Agrégats Phase 2 inchangés ----------------------------------------------

def test_aggregates_identical_after_enrichment():
    """aggregate_machine/zone identiques sur enrichi vs original (pas de divergence)."""
    g = _graph()
    e = enrich_graph(g)
    assert aggregate_machine(e) == aggregate_machine(g)
    for z in range(9):
        assert aggregate_zone(e, z) == aggregate_zone(g, z)


# --- Cohérence du total ------------------------------------------------------

def test_total_torque_consistency():
    """sum(torque_nm) == total_torque(enriched) == total_torque(graph), à tolérance."""
    g = _graph()
    e = enrich_graph(g)
    materialized_sum = sum(n.torque_nm for n in e)
    assert math.isclose(materialized_sum, total_torque(e), rel_tol=1e-12,
                        abs_tol=1e-15)
    assert math.isclose(total_torque(e), total_torque(g), rel_tol=1e-12,
                        abs_tol=1e-15)
    assert materialized_sum > 0.0  # cas non dégénéré


# --- Déterminisme ------------------------------------------------------------

def test_enrich_is_deterministic():
    """enrich_node/enrich_graph rejoués → mêmes torque_nm."""
    g = _graph()
    rpm = g.params.screw_rpm
    n = g.node_at(20)
    assert enrich_node(n, rpm).torque_nm == enrich_node(n, rpm).torque_nm
    e1 = enrich_graph(g)
    e2 = enrich_graph(g)
    assert [x.torque_nm for x in e1] == [x.torque_nm for x in e2]


def test_enrich_node_is_pure():
    """enrich_node ne mute pas le nœud d'entrée (frozen + replace)."""
    g = _graph()
    n = g.node_at(20)
    _ = enrich_node(n, g.params.screw_rpm)
    assert n.torque_nm is None


def test_enrich_nodes_list_matches_per_node():
    """enrich_nodes(liste) == enrich_node élément par élément."""
    g = _graph()
    rpm = g.params.screw_rpm
    out = enrich_nodes(g.nodes, rpm)
    assert len(out) == len(g.nodes)
    for original, enriched in zip(g.nodes, out):
        assert enriched.torque_nm == enrich_node(original, rpm).torque_nm


# --- Garde rpm = 0 -----------------------------------------------------------

def test_zero_rpm_materializes_zero_everywhere():
    """screw_rpm = 0 → torque_nm = 0.0 (float, pas None) sur les 81 nœuds."""
    g = _graph(rpm=0.0)
    e = enrich_graph(g)
    for n in e:
        assert n.torque_nm == 0.0
        assert n.torque_nm is not None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("enrich: all tests passed")
