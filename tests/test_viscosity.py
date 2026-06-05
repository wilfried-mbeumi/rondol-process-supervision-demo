"""Tests Phase 3.3 — engine/viscosity.py.

Vérifie : η mono = Carreau-Yasuda × Arrhenius × clamp ; η mélange = log-additive
des viscosités par constituant ; finitude (pas d'inf/nan) ; monotonies (T↑→η↓,
γ̇↑→η↓) ; matière inconnue/DEFAULT OK ; E4–E7 toujours None ; NodeState inchangé.
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
from engine.viscosity import (  # noqa: E402
    compute_local_viscosity,
    constituent_viscosity,
    viscosity_at,
)
from engine.node_state import NodeState  # noqa: E402
from materials.powder import POWDERS, Powder  # noqa: E402
from materials import rheology_presets as rp  # noqa: E402
from materials.rheology import (  # noqa: E402
    apply_temperature_shift,
    arrhenius_temperature_factor,
    carreau_yasuda_viscosity,
)
from materials.mixing_rules import log_additive_viscosity  # noqa: E402
from materials.limits import (  # noqa: E402
    clamp_viscosity,
    VISCOSITY_FLOOR_PA_S,
    VISCOSITY_CEILING_PA_S,
)


def _graph():
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 4)
    sl.add_elements_atomic(cfg, 4, 2)
    sl.add_elements_atomic(cfg, 9, 1)
    params = sl.ProcessParams(
        screw_rpm=150.0,
        feeder1_flow_rate_g_per_s=0.5, feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.2, feeder2_bulk_density=1.0,
        side_feeder_zone=3,
        temp_z=(20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0),
    )
    return build_graph(cfg, params, POWDERS["LFP"], POWDERS["LATP"])


def _expected_single(rheo, shear, temp):
    eta_iso = carreau_yasuda_viscosity(
        shear, rheo.eta_zero_pa_s, rheo.eta_inf_pa_s,
        rheo.relax_time_s, rheo.flow_index_n, rheo.yasuda_a)
    a_t = arrhenius_temperature_factor(
        temp, rheo.activation_energy_j_mol, rheo.tref_c)
    return clamp_viscosity(apply_temperature_shift(eta_iso, a_t))


def test_mono_constituent_matches_carreau_arrhenius_clamp():
    """η mono == Carreau-Yasuda × Arrhenius × clamp (calcul manuel identique)."""
    g = _graph()
    # Nœud amont (feeder1 pur = LFP).
    n = g.node_at(g.process_state.side_feeder_position - 2)
    assert n.material.is_blend is False
    rheo = n.material.rheologies[0]
    expected = _expected_single(rheo, n.shear_rate_s, n.temperature_c)
    assert compute_local_viscosity(n) == expected
    assert constituent_viscosity(rheo, n.shear_rate_s, n.temperature_c) == expected


def test_blend_matches_log_additive_of_constituents():
    """η mélange == log_additive des η de chaque constituant (au même γ̇/T)."""
    g = _graph()
    n = g.node_at(min(sl.TIP_PART1_POS - 1,
                      g.process_state.side_feeder_position + 3))
    assert n.material.is_blend is True
    per = [_expected_single(r, n.shear_rate_s, n.temperature_c)
           for r in n.material.rheologies]
    expected = clamp_viscosity(
        log_additive_viscosity(per, list(n.material.volume_fractions)))
    assert compute_local_viscosity(n) == expected
    # Combinaison sur VISCOSITÉS, pas sur params : N viscosités intermédiaires.
    assert len(per) == len(n.material.rheologies) == len(n.material.volume_fractions)


def test_always_finite_no_inf_nan():
    """Sortie toujours finie ∈ [floor, ceiling] sur tout le profil + cas extrêmes."""
    g = _graph()
    for n in g:
        eta = compute_local_viscosity(n)
        assert math.isfinite(eta)
        assert VISCOSITY_FLOOR_PA_S <= eta <= VISCOSITY_CEILING_PA_S
    rheo = rp.MELT_RHEOLOGY[POWDERS["LFP"].name]
    rh = (rheo,)
    vf = (1.0,)
    for shear, temp in [(0.0, 20.0), (1e9, 20.0), (50.0, -50.0), (50.0, 5000.0)]:
        eta = viscosity_at(shear, temp, rh, vf)
        assert math.isfinite(eta)
        assert VISCOSITY_FLOOR_PA_S <= eta <= VISCOSITY_CEILING_PA_S


def test_temperature_monotonicity():
    """T↑ ⇒ η↓ (Arrhenius, Ea>0), à γ̇ fixé."""
    rheo = rp.MELT_RHEOLOGY[POWDERS["LFP"].name]
    rh, vf = (rheo,), (1.0,)
    eta_cold = viscosity_at(50.0, 40.0, rh, vf)
    eta_hot = viscosity_at(50.0, 160.0, rh, vf)
    assert eta_hot < eta_cold


def test_shear_monotonicity():
    """γ̇↑ ⇒ η↓ (rhéofluidifiant n<1), à T fixée."""
    rheo = rp.MELT_RHEOLOGY[POWDERS["LFP"].name]
    rh, vf = (rheo,), (1.0,)
    eta_low = viscosity_at(1.0, 100.0, rh, vf)
    eta_high = viscosity_at(1000.0, 100.0, rh, vf)
    assert eta_high < eta_low


def test_unknown_material_default_does_not_break():
    """Matière inconnue (rhéo DEFAULT explicite) → viscosité finie, pas d'erreur."""
    unknown = Powder("MatX", bulk_density_g_cm3=1.0, true_density_g_cm3=2.0,
                     cp_j_per_g_k=0.9)
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 4, 2)
    params = sl.ProcessParams(screw_rpm=120.0, feeder1_flow_rate_g_per_s=0.5,
                              feeder1_bulk_density=1.0)
    g = build_graph(cfg, params, unknown)
    n = g.node_at(sl.MAIN_FEEDER_POSITION)
    assert "DEFAULT" in n.material.rheologies[0].name
    eta = compute_local_viscosity(n)
    assert math.isfinite(eta) and eta > 0.0


def test_empty_rheologies_returns_floor():
    """Garde défensive : aucun constituant → plancher (jamais d'erreur)."""
    assert viscosity_at(50.0, 100.0, (), ()) == VISCOSITY_FLOOR_PA_S


def test_e4_e7_remain_none_on_all_nodes():
    """E4–E7 inchangés : None sur les 81 nœuds, même après calcul de viscosité."""
    g = _graph()
    for n in g:
        _ = compute_local_viscosity(n)  # le calcul ne touche pas le nœud
        assert n.torque_nm is None
        assert n.sme_kwh_per_kg is None
        assert n.t_real_c is None
        assert n.pressure_bar is None


def test_nodestate_structure_unchanged_no_viscosity_field():
    """NodeState garde ses champs ; aucun viscosity_pa_s / rheologies ajouté."""
    import dataclasses as dc
    names = [f.name for f in dc.fields(NodeState)]
    assert "viscosity_pa_s" not in names
    assert "rheologies" not in names
    # 21 champs (Phase 2 + channel_depth_mm de 3.1), inchangé par 3.3.
    assert len(names) == 21


def test_compute_local_viscosity_is_pure():
    """compute_local_viscosity ne mute pas le nœud (frozen + lecture seule)."""
    g = _graph()
    n = g.node_at(20)
    before = (n.shear_rate_s, n.temperature_c, n.material)
    compute_local_viscosity(n)
    assert (n.shear_rate_s, n.temperature_c, n.material) == before


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("viscosity: all tests passed")
