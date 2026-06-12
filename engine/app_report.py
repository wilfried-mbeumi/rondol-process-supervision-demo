"""app_report.py — vue-modèle PURE pour l'UI (portage app, lecture seule).

Assemble en UN objet présentable (`EngineReport`) tout ce que la couche moteur
sait déjà calculer, SANS introduire de nouvelle physique :
  - graph d'extrusion (Phase 2)          → `engine.extrusion_graph.build_graph`
  - couple local matérialisé (E4a/E4b)   → `engine.enrich.enrich_graph`
  - agrégats machine/zone (Phase 2)      → `engine.aggregate`
  - couple total (E4a)                   → `engine.torque.total_torque`
  - SME totale (dérivée d'E4, voir ci-dessous)

⚠️ SME — PAS une nouvelle équation : la SME totale est la simple définition
    SME [kWh/kg] = P_dissipée [kW] / ṁ [kg/h], où la puissance totale RÉUTILISE le
    couple E4 déjà calculé : P = 2π·N · couple_total (W). Aucun coefficient
    physique nouveau, aucune calibration. `node.sme_kwh_per_kg` N'EST PAS
    matérialisé ici (E5b non codé) ; seule la SME TOTALE est exposée.

⚠️ NOMINAL : tout repose sur des presets matière nominaux et le proxy V_filled
    d'E4a — résultats à interpréter en TENDANCE, pas en valeur industrielle.

E6 (T_real) et E7 (pression) ne sont PAS calculés : `t_real_c` / `pressure_bar`
restent `None` (statut « à venir »).

Ce module est PUR : aucune dépendance Streamlit, aucune lecture session/disque.
La page `app/pages/5_Process_Engine.py` se contente de RENDRE le `EngineReport`.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

import math  # noqa: E402
from dataclasses import dataclass  # noqa: E402

from screw_logic import ProcessParams  # noqa: E402  (module nu — convention canonique)
from physics.conversions import rpm_to_rps, g_per_s_to_kg_per_h  # noqa: E402
from materials.limits import clamp  # noqa: E402
from materials.powder import Powder  # noqa: E402
from engine.extrusion_graph import build_graph  # noqa: E402
from engine.enrich import enrich_graph  # noqa: E402
from engine.aggregate import aggregate_machine  # noqa: E402
from engine.torque import total_torque  # noqa: E402


@dataclass(frozen=True)
class PositionRow:
    """Ligne « par position » prête à afficher (lecture seule)."""
    position: int
    zone: int
    element_label: str
    is_empty: bool
    port_kind: str | None
    fill_factor: float
    shear_rate_s: float
    torque_nm: float  # matérialisé par enrich_graph (float ≥ 0)


@dataclass(frozen=True)
class ZoneRow:
    """Ligne « par zone » prête à afficher (miroir lisible de ZoneState)."""
    zone: int
    n_nodes: int
    residence_time_s: float
    mean_fill_factor: float
    max_fill_factor: float
    mean_shear_rate_s: float
    max_shear_rate_s: float
    max_temperature_c: float
    dominant_material: str | None


@dataclass(frozen=True)
class EngineReport:
    """Vue-modèle complète pour la page « Moteur Procédé ».

    KPIs machine + couple/SME + détails par zone/position + statut des équations
    différées (E6/E7 = None). Frozen : un instantané immuable du calcul.
    """
    # --- KPIs principaux ---
    total_torque_nm: float
    total_power_w: float
    total_sme_kwh_per_kg: float
    mass_flow_kg_per_h: float
    screw_rpm: float
    residence_time_total_s: float
    fill_factor_average: float
    max_shear_rate_s: float
    output_vol_flow_cm3_s: float
    peak_fill_factor: float
    peak_fill_position: int
    overflow_main_feeder: bool
    overflow_side_feeder: bool

    # --- détails ---
    zones: tuple[ZoneRow, ...]
    positions: tuple[PositionRow, ...]

    # --- équations différées (statut) ---
    t_real_c: float | None  # E6 — toujours None (à venir)
    pressure_bar: float | None  # E7 — toujours None (à venir)

    # --- méta / hypothèses ---
    feeder1_material: str
    feeder2_material: str | None


def total_power_w(graph) -> float:
    """Puissance mécanique dissipée totale (W) = 2π·N · couple_total.

    RÉUTILISE le couple E4 (`total_torque`) — équivalent à Σ des puissances
    locales (puisque M_node = P_node/(2πN)). Sortie finie ≥ 0.
    """
    n_rev_s = rpm_to_rps(graph.params.screw_rpm)
    if not math.isfinite(n_rev_s) or n_rev_s <= 0.0:
        return 0.0
    power = 2.0 * math.pi * n_rev_s * total_torque(graph)
    return clamp(power, 0.0, math.inf)


def total_sme_kwh_per_kg(graph) -> float:
    """SME totale (kWh/kg) = P_dissipée [kW] / ṁ [kg/h].

    ṁ = débit massique d'alimentation total feeder1 + feeder2 (hypothèse régime
    permanent : feed = sortie). Identité d'unités : kW / (kg/h) = kWh/kg (les
    heures s'annulent). Garde ṁ ≤ 0 → 0.0. Sortie finie ≥ 0.
    """
    mass_flow_kg_h = mass_flow_kg_per_h(graph.params)
    if mass_flow_kg_h <= 0.0:
        return 0.0
    power_kw = total_power_w(graph) / 1000.0
    return clamp(power_kw / mass_flow_kg_h, 0.0, math.inf)


def mass_flow_kg_per_h(params: ProcessParams) -> float:
    """Débit massique total d'alimentation (kg/h) = (feeder1 + feeder2) g/s → kg/h."""
    total_g_s = params.feeder1_flow_rate_g_per_s + params.feeder2_flow_rate_g_per_s
    return g_per_s_to_kg_per_h(total_g_s)


def build_engine_report(
    config: list[int],
    params: ProcessParams,
    feeder1_powder: Powder,
    feeder2_powder: Powder | None = None,
) -> EngineReport:
    """Construit le `EngineReport` (PUR).

    Enchaîne build_graph (1 appel Network 7) → enrich_graph (matérialise le couple)
    → aggregate_machine, puis dérive couple/SME totaux. Ne recalcule NI la
    propagation ProcessState NI les agrégats. E6/E7 restent None.
    """
    graph = build_graph(config, params, feeder1_powder, feeder2_powder)
    enriched = enrich_graph(graph)
    machine = aggregate_machine(enriched)

    zones = tuple(
        ZoneRow(
            zone=z.zone,
            n_nodes=z.n_nodes,
            residence_time_s=z.residence_time_s,
            mean_fill_factor=z.mean_fill_factor,
            max_fill_factor=z.max_fill_factor,
            mean_shear_rate_s=z.mean_shear_rate_s,
            max_shear_rate_s=z.max_shear_rate_s,
            max_temperature_c=z.max_temperature_c,
            dominant_material=z.dominant_material,
        )
        for z in machine.zones
    )

    positions = tuple(
        PositionRow(
            position=n.position,
            zone=n.zone,
            element_label=n.element_label,
            is_empty=n.is_empty,
            port_kind=n.port_kind,
            fill_factor=n.fill_factor,
            shear_rate_s=n.shear_rate_s,
            torque_nm=n.torque_nm if n.torque_nm is not None else 0.0,
        )
        for n in enriched
    )

    return EngineReport(
        total_torque_nm=total_torque(enriched),
        total_power_w=total_power_w(enriched),
        total_sme_kwh_per_kg=total_sme_kwh_per_kg(enriched),
        mass_flow_kg_per_h=mass_flow_kg_per_h(params),
        screw_rpm=params.screw_rpm,
        residence_time_total_s=machine.residence_time_total_s,
        fill_factor_average=machine.fill_factor_average,
        max_shear_rate_s=machine.max_shear_rate_s,
        output_vol_flow_cm3_s=machine.output_vol_flow_cm3_s,
        peak_fill_factor=machine.peak_fill_factor,
        peak_fill_position=machine.peak_fill_position,
        overflow_main_feeder=machine.overflow_main_feeder,
        overflow_side_feeder=machine.overflow_side_feeder,
        zones=zones,
        positions=positions,
        # E6/E7 non calculés — statut « à venir ».
        t_real_c=None,
        pressure_bar=None,
        feeder1_material=feeder1_powder.name,
        feeder2_material=feeder2_powder.name if feeder2_powder is not None else None,
    )
