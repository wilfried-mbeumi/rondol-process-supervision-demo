"""Tests Phase 2 — engine/node_state.py.

Test PIVOT : NodeState ENVELOPPE ProcessState (égalité stricte des champs
procédé) et n'en recalcule aucun. Vérifie aussi classification, cisaillement
E1, température locale et champs E4–E7 à None.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402  (module nu)
from machine import element_library as el  # noqa: E402
from physics.conversions import apparent_shear_rate_s  # noqa: E402
from engine.material_context import FeedContext  # noqa: E402
from engine.node_state import build_node, EMPTY_TYPE  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _make_state():
    """Config réaliste : quelques éléments + side feeder + thermique non triviale."""
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 1, 4)   # convoyage
    sl.add_elements_atomic(cfg, 4, 2)   # malaxage 90°
    sl.add_elements_atomic(cfg, 9, 1)   # convoyage inverse
    params = sl.ProcessParams(
        screw_rpm=150.0,
        feeder1_flow_rate_g_per_s=0.5,
        feeder1_bulk_density=1.2,
        feeder2_flow_rate_g_per_s=0.2,
        feeder2_bulk_density=1.0,
        side_feeder_zone=3,
        temp_z=(20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0),
    )
    state = sl.compute_process_state(cfg, params)
    fc = FeedContext(
        feeder1_powder=POWDERS["LFP"], feeder1_qvol_cm3_s=0.4,
        feeder2_powder=POWDERS["LATP"], feeder2_qvol_cm3_s=0.2,
        side_feeder_position=state.side_feeder_position,
    )
    return cfg, params, state, fc


def test_node_envelopes_process_state_verbatim():
    """PIVOT : chaque champ procédé == ProcessState[i] (aucun recalcul)."""
    cfg, params, state, fc = _make_state()
    for pos in range(sl.N_POSITIONS):
        n = build_node(pos, cfg, state, params, fc)
        assert n.local_free_volume_cm3 == state.local_free_volume_cm3[pos]
        assert n.local_free_volume_by_rev == state.local_free_volume_by_rev[pos]
        assert n.fill_factor == state.fill_factor_local[pos]
        assert n.vol_flow_cm3_s == state.vol_flow_cm3_s[pos]
        assert n.residence_time_s == state.residence_time_local[pos]


def test_classification_fields():
    """type_id / is_part2 / zone / ports cohérents avec screw_logic."""
    cfg, params, state, fc = _make_state()
    # Position 4 = main feeder.
    n4 = build_node(sl.MAIN_FEEDER_POSITION, cfg, state, params, fc)
    assert n4.port_kind == "main_feed"
    assert n4.zone == sl.position_to_zone(sl.MAIN_FEEDER_POSITION)
    # Position tip = die.
    ntip = build_node(sl.TIP_PART1_POS, cfg, state, params, fc)
    assert ntip.port_kind == "die"
    assert ntip.type_id == sl.TIP_TYPE
    # Side feeder port résolu via ProcessState.
    nside = build_node(state.side_feeder_position, cfg, state, params, fc)
    assert nside.port_kind == "side_feed"
    # is_part2 / base_type cohérents sur tout le profil.
    for pos in range(sl.N_POSITIONS):
        n = build_node(pos, cfg, state, params, fc)
        assert n.raw_value == cfg[pos]
        assert n.type_id == sl.base_type(cfg[pos])
        assert n.is_part2 == sl.is_part2(cfg[pos])
        assert n.is_empty == (n.type_id == EMPTY_TYPE)


def test_shear_rate_matches_conversions_E1():
    """γ̇ local = apparent_shear_rate_s(rpm, D, channel_depth) (E1, pas un stub)."""
    cfg, params, state, fc = _make_state()
    # Une position portant un malaxage (type 4) : profondeur élément.
    pos4 = next(p for p in range(sl.N_POSITIONS) if sl.base_type(cfg[p]) == 4)
    n = build_node(pos4, cfg, state, params, fc)
    expected = apparent_shear_rate_s(
        params.screw_rpm, el.SCREW_DIAMETER_MM, el.channel_depth_mm(4)
    )
    assert n.shear_rate_s == expected
    assert n.shear_rate_s > 0.0
    # Une case vide utilise la profondeur nominale (γ̇ fini, non nul).
    pos_empty = next(p for p in range(1, sl.TIP_PART1_POS) if cfg[p] == 0)
    ne = build_node(pos_empty, cfg, state, params, fc)
    exp_empty = apparent_shear_rate_s(
        params.screw_rpm, el.SCREW_DIAMETER_MM, el.NOMINAL_CHANNEL_DEPTH_MM
    )
    assert ne.shear_rate_s == exp_empty


def test_temperature_is_zone_setpoint():
    """temperature_c == params.temp_z[zone] pour chaque position."""
    cfg, params, state, fc = _make_state()
    for pos in range(sl.N_POSITIONS):
        n = build_node(pos, cfg, state, params, fc)
        assert n.temperature_c == params.temp_z[n.zone]


def test_e4_e7_are_none():
    """E4–E7 restent None en Phase 2 (préparation, pas calcul brut)."""
    cfg, params, state, fc = _make_state()
    for pos in (4, 20, 50, sl.TIP_PART1_POS):
        n = build_node(pos, cfg, state, params, fc)
        assert n.torque_nm is None
        assert n.sme_kwh_per_kg is None
        assert n.t_real_c is None
        assert n.pressure_bar is None


def test_material_present_upstream_vs_downstream():
    """Matière : amont side feeder = feeder1 pur ; aval = mélange."""
    cfg, params, state, fc = _make_state()
    side_pos = state.side_feeder_position
    up = build_node(max(1, side_pos - 2), cfg, state, params, fc)
    assert up.material.is_blend is False
    down = build_node(min(sl.TIP_PART1_POS - 1, side_pos + 2), cfg, state, params, fc)
    assert down.material.is_blend is True


def test_build_node_is_pure():
    """build_node ne mute ni config ni params."""
    cfg, params, state, fc = _make_state()
    snapshot = list(cfg)
    build_node(20, cfg, state, params, fc)
    assert cfg == snapshot


# ---------------------------------------------------------------------------
# Bloc 3.1 — attachement de h (channel_depth_mm)
# ---------------------------------------------------------------------------
def test_channel_depth_attached():
    """Un nœud d'élément porte h == element_library.channel_depth_mm(type)."""
    cfg, params, state, fc = _make_state()
    pos4 = next(p for p in range(sl.N_POSITIONS) if sl.base_type(cfg[p]) == 4)
    n = build_node(pos4, cfg, state, params, fc)
    assert n.channel_depth_mm == el.channel_depth_mm(4)
    # Aucun override SLDDRW aujourd'hui → nominal global.
    assert n.channel_depth_mm == el.NOMINAL_CHANNEL_DEPTH_MM
    assert n.channel_depth_mm > 0.0


def test_channel_depth_empty_uses_nominal():
    """Case vide (type 0, hors ELEMENT_PHYSICS) → profondeur nominale."""
    cfg, params, state, fc = _make_state()
    pos_empty = next(p for p in range(1, sl.TIP_PART1_POS) if cfg[p] == 0)
    n = build_node(pos_empty, cfg, state, params, fc)
    assert n.type_id == EMPTY_TYPE
    assert n.channel_depth_mm == el.NOMINAL_CHANNEL_DEPTH_MM


def test_channel_depth_part2_uses_base_type():
    """Un demi-élément part2 porte la profondeur de son TYPE DE BASE (= part1)."""
    cfg, params, state, fc = _make_state()
    pos_p2 = next(p for p in range(sl.N_POSITIONS) if sl.is_part2(cfg[p]))
    n = build_node(pos_p2, cfg, state, params, fc)
    assert n.is_part2 is True
    base = sl.base_type(cfg[pos_p2])
    assert n.type_id == base
    assert n.channel_depth_mm == el.channel_depth_mm(base)
    # Cohérence avec la 1ère partie (position précédente, même élément).
    n_prev = build_node(pos_p2 - 1, cfg, state, params, fc)
    assert n.channel_depth_mm == n_prev.channel_depth_mm


def test_shear_consistent_with_channel_depth():
    """γ̇ stocké == apparent_shear_rate_s(rpm, D, h stocké) sur tout le profil.

    Preuve que le h exposé est EXACTEMENT celui utilisé pour le cisaillement
    (une seule source, pas de divergence).
    """
    cfg, params, state, fc = _make_state()
    for pos in range(sl.N_POSITIONS):
        n = build_node(pos, cfg, state, params, fc)
        expected = apparent_shear_rate_s(
            params.screw_rpm, el.SCREW_DIAMETER_MM, n.channel_depth_mm
        )
        assert n.shear_rate_s == expected


def test_rheologies_accessible_via_material_readonly():
    """Bloc 3.2 (lecture seule) : la rhéo voyage sur node.material, PAS sur NodeState.

    Aucun champ rhéo/viscosité n'est ajouté à NodeState ; le nœud accède aux
    paramètres via node.material.rheologies, alignés sur node.material.powders.
    """
    cfg, params, state, fc = _make_state()
    n = build_node(20, cfg, state, params, fc)
    assert hasattr(n.material, "rheologies")
    assert len(n.material.rheologies) == len(n.material.powders)
    # NodeState n'a PAS gagné de champ rhéo/viscosité en 3.2.
    node_fields = {f for f in n.__dataclass_fields__}
    assert "rheologies" not in node_fields
    assert "viscosity_pa_s" not in node_fields


def test_channel_depth_override_flows_through(monkeypatch):
    """Une future valeur SLDDRW (override) se propage à h ET à γ̇ sans toucher NodeState.

    Simule un override par élément en patchant ELEMENT_PHYSICS ; vérifie que
    NodeState.channel_depth_mm et shear_rate_s en tiennent compte automatiquement.
    """
    cfg, params, state, fc = _make_state()
    pos4 = next(p for p in range(sl.N_POSITIONS) if sl.base_type(cfg[p]) == 4)

    OVERRIDE = 2.5
    patched = replace(el.ELEMENT_PHYSICS[4], channel_depth_mm=OVERRIDE)
    monkeypatch.setitem(el.ELEMENT_PHYSICS, 4, patched)

    n = build_node(pos4, cfg, state, params, fc)
    assert n.channel_depth_mm == OVERRIDE
    assert n.shear_rate_s == apparent_shear_rate_s(
        params.screw_rpm, el.SCREW_DIAMETER_MM, OVERRIDE
    )
    # Le champ NodeState n'a pas changé de structure : toujours un float exposé.
    assert isinstance(n.channel_depth_mm, float)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if (name.startswith("test_") and callable(fn)
                and "monkeypatch" not in fn.__code__.co_varnames):
            fn()
            print(f"OK {name}")
    print("node_state: direct tests passed (monkeypatch test via pytest)")
