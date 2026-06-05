"""Tests E4a — engine/torque.py.

Vérifie le modèle uniforme transparent M = η·γ̇²·V_filled/(2π·N) :
calcul manuel local, décomposition P = η·γ̇²·V_filled puis M = P/(2π·N),
cas nuls (fill/shear/rpm/volume = 0), finitude (pas d'inf/nan), monotonies
(η↑→M↑, fill↑→M↑, V↑→M↑), total = somme des contributions locales, et invariances
(E4–E7 restent None sur les 81 nœuds ; NodeState garde 21 champs, pas de
torque_nm matérialisé).
"""

from __future__ import annotations

import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402
from engine.extrusion_graph import build_graph  # noqa: E402
from engine.node_state import NodeState  # noqa: E402
from engine.viscosity import compute_local_viscosity  # noqa: E402
from engine.torque import (  # noqa: E402
    local_power_dissipation,
    local_torque_contribution,
    total_torque,
    total_torque_from_nodes,
)
from physics.conversions import cm3_to_m3, rpm_to_rps  # noqa: E402
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


def _stub(material, *, shear, fill, free_volume_cm3, temperature_c):
    """Nœud minimal duck-typé : seuls les champs lus par torque/viscosity.

    Permet de faire varier η (via temperature_c), fill et volume INDÉPENDAMMENT
    pour les tests de formule et de monotonie, sans muter de vrai NodeState.
    """
    return types.SimpleNamespace(
        material=material,
        shear_rate_s=shear,
        fill_factor=fill,
        local_free_volume_cm3=free_volume_cm3,
        temperature_c=temperature_c,
    )


def _real_material():
    """Une MaterialPresence réelle (mono-constituant amont feeder1 = LFP)."""
    g = _graph()
    n = g.node_at(g.process_state.side_feeder_position - 2)
    assert n.material.is_blend is False
    return n.material


# --- Formule locale : calcul manuel ------------------------------------------

def test_local_formula_matches_manual_computation():
    """M_node == η·γ̇²·V_filled/(2π·N), recalculé à la main, à l'identique."""
    mat = _real_material()
    node = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.5,
                 temperature_c=100.0)
    rpm = 150.0

    eta = compute_local_viscosity(node)
    v_filled_m3 = cm3_to_m3(1.5 * 0.6)
    power_expected = eta * 50.0 * 50.0 * v_filled_m3
    torque_expected = power_expected / (2.0 * math.pi * rpm_to_rps(rpm))

    assert local_torque_contribution(node, rpm) == torque_expected


def test_power_equals_eta_shear2_vfilled():
    """P == η·γ̇²·V_filled (décomposition de la puissance dissipée)."""
    mat = _real_material()
    node = _stub(mat, shear=40.0, fill=0.5, free_volume_cm3=2.0,
                 temperature_c=80.0)
    eta = compute_local_viscosity(node)
    v_filled_m3 = cm3_to_m3(2.0 * 0.5)
    assert local_power_dissipation(node) == eta * 40.0 * 40.0 * v_filled_m3


def test_torque_equals_power_over_2pi_n():
    """M == P/(2π·N) (lien couple↔puissance, N en tours/s)."""
    mat = _real_material()
    node = _stub(mat, shear=60.0, fill=0.7, free_volume_cm3=1.2,
                 temperature_c=120.0)
    rpm = 200.0
    power = local_power_dissipation(node)
    expected = power / (2.0 * math.pi * rpm_to_rps(rpm))
    assert local_torque_contribution(node, rpm) == expected
    assert power > 0.0  # le cas test est bien dans le régime non trivial


# --- Cas nuls ----------------------------------------------------------------

def test_zero_fill_gives_zero():
    mat = _real_material()
    node = _stub(mat, shear=50.0, fill=0.0, free_volume_cm3=1.5,
                 temperature_c=100.0)
    assert local_power_dissipation(node) == 0.0
    assert local_torque_contribution(node, 150.0) == 0.0


def test_zero_shear_gives_zero():
    mat = _real_material()
    node = _stub(mat, shear=0.0, fill=0.6, free_volume_cm3=1.5,
                 temperature_c=100.0)
    assert local_power_dissipation(node) == 0.0
    assert local_torque_contribution(node, 150.0) == 0.0


def test_zero_volume_gives_zero():
    mat = _real_material()
    node = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=0.0,
                 temperature_c=100.0)
    assert local_power_dissipation(node) == 0.0
    assert local_torque_contribution(node, 150.0) == 0.0


def test_zero_or_invalid_rpm_gives_zero():
    """N ≤ 0 / None / non fini ⇒ couple 0 proprement (puissance reste calculable)."""
    mat = _real_material()
    node = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.5,
                 temperature_c=100.0)
    assert local_power_dissipation(node) > 0.0  # dissipation non nulle...
    for rpm in (0.0, -10.0, None, float("nan"), float("inf")):
        assert local_torque_contribution(node, rpm) == 0.0  # ...mais couple = 0


# --- Finitude ----------------------------------------------------------------

def test_always_finite_no_inf_nan():
    """Sortie finie ≥ 0 sur tout le profil réel + entrées extrêmes."""
    g = _graph()
    rpm = g.params.screw_rpm
    for n in g:
        p = local_power_dissipation(n)
        m = local_torque_contribution(n, rpm)
        assert math.isfinite(p) and p >= 0.0
        assert math.isfinite(m) and m >= 0.0

    mat = _real_material()
    extremes = [
        _stub(mat, shear=1e12, fill=1.0, free_volume_cm3=1e9, temperature_c=-50.0),
        _stub(mat, shear=1e-12, fill=1e-12, free_volume_cm3=1e-12,
              temperature_c=5000.0),
    ]
    for node in extremes:
        m = local_torque_contribution(node, 150.0)
        assert math.isfinite(m) and m >= 0.0


# --- Monotonies --------------------------------------------------------------

def test_monotonic_in_viscosity():
    """η↑ ⇒ M↑ : à γ̇/fill/V fixés, T plus basse → η plus haute (Arrhenius Ea>0)."""
    mat = _real_material()
    cold = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.5,
                 temperature_c=40.0)
    hot = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.5,
                temperature_c=160.0)
    assert compute_local_viscosity(cold) > compute_local_viscosity(hot)
    assert local_torque_contribution(cold, 150.0) > local_torque_contribution(
        hot, 150.0)


def test_monotonic_in_fill():
    """fill↑ ⇒ M↑ (tout le reste fixé)."""
    mat = _real_material()
    low = _stub(mat, shear=50.0, fill=0.3, free_volume_cm3=1.5,
                temperature_c=100.0)
    high = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.5,
                 temperature_c=100.0)
    assert local_torque_contribution(high, 150.0) > local_torque_contribution(
        low, 150.0)


def test_monotonic_in_volume():
    """V↑ ⇒ M↑ (tout le reste fixé)."""
    mat = _real_material()
    small = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=1.0,
                  temperature_c=100.0)
    big = _stub(mat, shear=50.0, fill=0.6, free_volume_cm3=2.0,
                temperature_c=100.0)
    assert local_torque_contribution(big, 150.0) > local_torque_contribution(
        small, 150.0)


# --- Total = somme des contributions locales ---------------------------------

def test_total_equals_sum_of_local_contributions():
    g = _graph()
    rpm = g.params.screw_rpm
    manual = sum(local_torque_contribution(n, rpm) for n in g.nodes)
    assert total_torque(g) == manual
    assert total_torque_from_nodes(g.nodes, rpm) == manual
    assert manual > 0.0  # le profil teste un cas non dégénéré


def test_total_uses_graph_screw_rpm():
    """total_torque lit bien graph.params.screw_rpm (une seule source de N)."""
    g = _graph(rpm=120.0)
    assert total_torque(g) == total_torque_from_nodes(g.nodes, 120.0)


# --- Invariances de périmètre E4a --------------------------------------------

def test_e4_e7_remain_none_on_all_nodes():
    """E4–E7 inchangés : None sur les 81 nœuds, même après calcul du couple."""
    g = _graph()
    assert len(g.nodes) == 81
    rpm = g.params.screw_rpm
    for n in g:
        _ = local_torque_contribution(n, rpm)  # le calcul ne touche pas le nœud
        assert n.torque_nm is None
        assert n.sme_kwh_per_kg is None
        assert n.t_real_c is None
        assert n.pressure_bar is None


def test_nodestate_structure_unchanged_no_materialized_torque():
    """NodeState garde 21 champs ; torque_nm reste un champ deferred (None), pas
    une grandeur matérialisée par E4a."""
    import dataclasses as dc
    names = [f.name for f in dc.fields(NodeState)]
    assert len(names) == 21
    # torque_nm existe comme champ DIFFÉRÉ (déclaré Phase 2), défaut None.
    assert "torque_nm" in names
    g = _graph()
    for n in g:
        assert n.torque_nm is None


def test_functions_are_pure_no_mutation():
    """Les fonctions ne mutent pas le nœud (frozen + lecture seule)."""
    g = _graph()
    n = g.node_at(20)
    before = (n.shear_rate_s, n.fill_factor, n.local_free_volume_cm3,
              n.temperature_c, n.torque_nm)
    local_power_dissipation(n)
    local_torque_contribution(n, g.params.screw_rpm)
    total_torque(g)
    after = (n.shear_rate_s, n.fill_factor, n.local_free_volume_cm3,
             n.temperature_c, n.torque_nm)
    assert before == after


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("torque: all tests passed")
