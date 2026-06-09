"""aggregate.py — agrégation position → zone → machine (Phase 2).

Replie les `NodeState` d'un `ExtrusionGraph` en états de ZONE puis de MACHINE.

RÈGLE ANTI-DIVERGENCE — RÉUTILISER LES TOTAUX ProcessState :
  Les agrégats procédé DÉJÀ produits par Network 7 sont RÉUTILISÉS tels quels,
  jamais re-sommés depuis les nœuds (ce qui risquerait un double comptage des
  demi-éléments part2 ou une divergence d'arrondi) :
    - ZoneState.residence_time_s   ← ProcessState.residence_time_zone[z]
    - MachineState.residence_total ← ProcessState.residence_time_total
    - MachineState.fill_factor_avg ← ProcessState.fill_factor_average
    - MachineState.overflow_*      ← ProcessState.overflow_main/side_feeder
  Seuls les agrégats ABSENTS de ProcessState sont calculés ici (cisaillement
  max/moyen, remplissage crête, température crête, matière dominante).

Les agrégats nouveaux passent par `materials.limits` pour rester FINIS (anti
inf/nan) avant toute consommation par la couche décision.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

import math
from dataclasses import dataclass

from screw_logic import TIP_PART1_POS  # noqa: E402  (module nu)
from materials.limits import clamp, clamp_volume_fraction  # noqa: E402
from engine.extrusion_graph import ExtrusionGraph, N_ZONES  # noqa: E402
from engine.node_state import NodeState  # noqa: E402


def _finite_max(values: list[float]) -> float:
    """Max fini d'une liste (0.0 si vide), nan neutralisé via limits.clamp."""
    if not values:
        return 0.0
    return clamp(max(values), 0.0, math.inf)


def _finite_mean(values: list[float]) -> float:
    """Moyenne finie d'une liste (0.0 si vide), nan neutralisé."""
    if not values:
        return 0.0
    return clamp(sum(values) / len(values), 0.0, math.inf)


def _dominant_material_label(nodes: list[NodeState]) -> str | None:
    """Label matière le plus fréquent parmi les nœuds NON vides (None si aucun)."""
    counts: dict[str, int] = {}
    for n in nodes:
        if n.is_empty:
            continue
        counts[n.material.label] = counts.get(n.material.label, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


@dataclass(frozen=True)
class ZoneState:
    """Agrégat d'une zone procédé (0=Feed, 1..8).

    Champs RÉUTILISÉS de ProcessState :
      residence_time_s : ProcessState.residence_time_zone[zone] (NON re-sommé).

    Champs CALCULÉS ici (absents de ProcessState) :
      n_nodes              : nombre de positions dans la zone.
      mean_fill_factor     : remplissage moyen des nœuds de la zone ∈ [0, 1].
      max_fill_factor      : remplissage crête de la zone ∈ [0, 1].
      max_shear_rate_s     : cisaillement local max (s⁻¹).
      mean_shear_rate_s    : cisaillement local moyen (s⁻¹).
      max_temperature_c    : température de consigne max de la zone.
      dominant_material    : label matière dominant (None si zone vide).
    """
    zone: int
    n_nodes: int
    residence_time_s: float
    mean_fill_factor: float
    max_fill_factor: float
    max_shear_rate_s: float
    mean_shear_rate_s: float
    max_temperature_c: float
    dominant_material: str | None


@dataclass(frozen=True)
class MachineState:
    """Agrégat machine global.

    Champs RÉUTILISÉS de ProcessState (jamais recalculés) :
      residence_time_total_s : ProcessState.residence_time_total.
      fill_factor_average    : ProcessState.fill_factor_average.
      overflow_main_feeder   : ProcessState.overflow_main_feeder.
      overflow_side_feeder   : ProcessState.overflow_side_feeder.

    Champs CALCULÉS ici :
      output_vol_flow_cm3_s  : débit volumique à la pointe (lecture position tip).
      max_shear_rate_s       : cisaillement local max sur toute la vis.
      peak_fill_factor       : remplissage crête global ∈ [0, 1].
      peak_fill_position     : position du remplissage crête.
      zones                  : tuple des ZoneState (index = zone 0..8).
    """
    residence_time_total_s: float
    fill_factor_average: float
    overflow_main_feeder: bool
    overflow_side_feeder: bool
    output_vol_flow_cm3_s: float
    max_shear_rate_s: float
    peak_fill_factor: float
    peak_fill_position: int
    zones: tuple[ZoneState, ...]


def _rpm_correction(screw_rpm: float) -> float:
    """Facteur correctif manager rpm_ref/screw_rpm appliqué aux temps de séjour.

    Source : `screw_logic.residence_time` (manager 2026-06-09). On le réimporte
    ici pour conserver la cohérence des valeurs entre Profile / Moteur Procédé /
    Historique — toute valeur de temps de séjour exposée à l'UI passe par
    cette correction.
    """
    from screw_logic import _residence_rpm_correction  # noqa: PLC0415
    return _residence_rpm_correction(screw_rpm)


def aggregate_zone(graph: ExtrusionGraph, zone: int) -> ZoneState:
    """Agrège les nœuds d'une zone. residence_time_s RÉUTILISÉ de ProcessState.

    Le temps de séjour de zone est ensuite multiplié par le facteur RPM
    manager (rpm_ref/screw_rpm) pour rester cohérent avec les wrappers UI.
    """
    nodes = graph.nodes_in_zone(zone)
    fills = [n.fill_factor for n in nodes]
    shears = [n.shear_rate_s for n in nodes]
    temps = [n.temperature_c for n in nodes]
    base_rt = graph.process_state.residence_time_zone[zone]
    factor = _rpm_correction(graph.params.screw_rpm)
    return ZoneState(
        zone=zone,
        n_nodes=len(nodes),
        # RÉUTILISATION stricte du total de zone Network 7 + correction RPM
        # manager 2026-06-09 (rpm_ref/screw_rpm). Si rpm<=0 → facteur 0.0.
        residence_time_s=base_rt * factor,
        mean_fill_factor=clamp_volume_fraction(_finite_mean(fills)),
        max_fill_factor=clamp_volume_fraction(_finite_max(fills)),
        max_shear_rate_s=_finite_max(shears),
        mean_shear_rate_s=_finite_mean(shears),
        max_temperature_c=_finite_max(temps),
        dominant_material=_dominant_material_label(nodes),
    )


def aggregate_machine(graph: ExtrusionGraph) -> MachineState:
    """Agrège le graph en MachineState. Totaux procédé RÉUTILISÉS de ProcessState.

    Le temps de séjour TOTAL reçoit la même correction manager rpm_ref/screw_rpm
    que les zones — garantit la cohérence Profile/Moteur/Historique.
    """
    st = graph.process_state
    zones = tuple(aggregate_zone(graph, z) for z in range(N_ZONES))

    # Remplissage crête global + sa position (agrégat nouveau).
    peak_ff, peak_pos = 0.0, 0
    for n in graph:
        if n.fill_factor > peak_ff:
            peak_ff, peak_pos = n.fill_factor, n.position

    max_shear = _finite_max([n.shear_rate_s for n in graph])
    factor = _rpm_correction(graph.params.screw_rpm)

    return MachineState(
        # --- RÉUTILISATION ProcessState (anti-divergence) ---
        # Correction RPM manager appliquée au TOTAL (cohérence wrappers UI).
        residence_time_total_s=st.residence_time_total * factor,
        fill_factor_average=st.fill_factor_average,
        overflow_main_feeder=st.overflow_main_feeder,
        overflow_side_feeder=st.overflow_side_feeder,
        # --- Agrégats nouveaux ---
        output_vol_flow_cm3_s=st.vol_flow_cm3_s[TIP_PART1_POS],
        max_shear_rate_s=max_shear,
        peak_fill_factor=clamp_volume_fraction(peak_ff),
        peak_fill_position=peak_pos,
        zones=zones,
    )
