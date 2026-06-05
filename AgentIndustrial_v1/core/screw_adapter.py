"""
screw_adapter.py — Pont vers l'existant Kévin (app/screw_logic.py, screw_render.py).

L'agent V1 ré-utilise SANS MODIFIER la logique vis déjà validée :
- screw_logic : volume, FF, résidence, contraintes (Network 7)
- screw_render : analyze_profile, analyze_systemic, recommend_element_count

L'adaptateur assure 3 fonctions :
  1. Ajoute le dossier `app/` au sys.path (import propre)
  2. Mappe FeederBank → paramètres mono-feeder attendus par screw_logic
  3. Calcule un SME estimé pour la V1 (en attendant le torque V2)
"""

from __future__ import annotations

import sys
from pathlib import Path

from .feeders import (
    FeederSpec,
    active_feeders,
    equivalent_main_density,
    mass_flow_by_phase,
)
from .process import ProcessState, ScrewKPIs

# ---------------------------------------------------------------------------
# Path bootstrap — importer l'existant sans le déplacer
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent.parent  # rondol-ia-project/
_APP = _ROOT / "app"
for p in (_ROOT, _APP):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# Imports différés (post sys.path) — pas de side-effect à l'import du package.
from screw_logic import (  # type: ignore  # noqa: E402
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    TIP_PART1_POS,
    TOTAL_FREE_VOL,
    base_type,
    count_elements,
    fill_factor_average,
    free_volume,
    is_part2,
    new_empty_configuration,
    position_to_zone,
    residence_time,
    zone_residence_times,
)
from screw_render import (  # type: ignore  # noqa: E402
    analyze_profile,
    recommend_element_count,
)

# Ré-exports utiles pour les autres modules
__all__ = [
    "default_screw_config",
    "refresh_kpis",
    "analyze_profile_for_state",
    "recommend_count_for_state",
    "MAIN_FEEDER_POSITION",
    "N_POSITIONS",
    "TIP_PART1_POS",
    "TOTAL_FREE_VOL",
]


# ---------------------------------------------------------------------------
# Constantes pour SME estimé
# ---------------------------------------------------------------------------
# Rondol micro-extrudeuse 10.5 mm — puissance moteur nominale typique (ordre).
# Cette valeur sera remplacée par lecture torque réel en V2.
P_MOTOR_NOMINAL_KW: float = 1.0
RPM_NOMINAL_MAX: float = 300.0  # rpm max nominale pour normalisation
MOTOR_EFFICIENCY: float = 0.85


def default_screw_config() -> list[int]:
    """Config vide (tip seulement) — point de départ propre."""
    return new_empty_configuration()


# ---------------------------------------------------------------------------
# Agrégation feeders → paramètres mono-feeder attendus par screw_logic
# ---------------------------------------------------------------------------
def _aggregated_solid_flow(feeders: list[FeederSpec]) -> float:
    """Somme des débits SOLIDES uniquement (g/min) — base FF/résidence.

    Les liquides/gaz n'occupent pas le volume bulk de la même façon ; ils sont
    traités séparément par le rule engine (incompatibilité thermique, etc.).
    """
    return sum(
        f.mass_flow_g_per_min for f in active_feeders(feeders) if f.is_solid
    )


# ---------------------------------------------------------------------------
# SME estimé V1 — proxy honnête, sera remplacé par mesure torque V2
# ---------------------------------------------------------------------------
def estimate_sme_kwh_per_kg(
    screw_rpm: float,
    mass_flow_g_per_min: float,
    fill_factor: float,
    torque_pct: float | None = None,
) -> float:
    """Estimation SME (Specific Mechanical Energy) en kWh/kg.

    Deux modes :
      1. Si torque_pct est fourni (V2 feedback) → calcul direct :
            P_eff = P_nominal · η · torque/100
            SME = P_eff [kW] / ṁ [kg/h]
      2. Sinon (V1 sans feedback) → proxy heuristique :
            torque_load_proxy = clip( 0.20 + 0.55·FF + 0.20·(rpm/rpm_max), 0..1 )
            puis même formule.

    La valeur V1 est clairement labellisée "estimation" dans l'UI. L'objectif
    est d'avoir un nombre cohérent pour les règles, pas une vérité physique.
    """
    if mass_flow_g_per_min <= 0.0:
        return 0.0
    if torque_pct is not None:
        torque_load = max(0.0, min(1.0, torque_pct / 100.0))
    else:
        torque_load = 0.20 + 0.55 * max(0.0, min(1.0, fill_factor)) \
                      + 0.20 * max(0.0, min(1.0, screw_rpm / RPM_NOMINAL_MAX))
        torque_load = max(0.05, min(1.0, torque_load))

    p_eff_kw = P_MOTOR_NOMINAL_KW * MOTOR_EFFICIENCY * torque_load
    mass_flow_kg_h = (mass_flow_g_per_min / 1000.0) * 60.0
    return p_eff_kw / mass_flow_kg_h


# ---------------------------------------------------------------------------
# API principale : refresh des KPIs depuis l'état complet
# ---------------------------------------------------------------------------
def refresh_kpis(state: ProcessState) -> ScrewKPIs:
    """Re-calcule l'ensemble des KPIs vis depuis ProcessState.

    Met à jour state.kpis et retourne la même référence.
    """
    cfg = state.screw_config
    rpm = float(state.screw_rpm)
    solid_flow = _aggregated_solid_flow(state.feeders)
    density = equivalent_main_density(state.feeders)

    if not cfg:
        state.kpis = ScrewKPIs()
        return state.kpis

    ff = fill_factor_average(cfg, rpm, solid_flow, density)
    rt_total = residence_time(cfg, rpm, solid_flow, density)
    rt_zone = zone_residence_times(cfg, rpm, solid_flow, density)
    n_el = count_elements(cfg)
    vol_free = free_volume(cfg)

    # Profil archetype (couche IA Kévin) — utile pour le diagnostic agent.
    profile = analyze_profile(
        cfg, rpm, solid_flow, density,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )

    sme = estimate_sme_kwh_per_kg(
        rpm, solid_flow, ff, torque_pct=state.v2.torque_pct,
    )

    state.kpis = ScrewKPIs(
        n_elements=n_el,
        free_volume_cm3=vol_free,
        fill_factor=ff,
        residence_time_s=rt_total,
        sme_kwh_per_kg=sme,
        zone_residence_s=list(rt_zone),
        profile_archetype=profile.archetype,
        profile_summary=profile.summary,
    )
    return state.kpis


def analyze_profile_for_state(state: ProcessState):
    """Délègue à screw_render.analyze_profile avec les bons paramètres."""
    cfg = state.screw_config
    solid_flow = _aggregated_solid_flow(state.feeders)
    density = equivalent_main_density(state.feeders)
    return analyze_profile(
        cfg, float(state.screw_rpm), solid_flow, density,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )


def recommend_count_for_state(state: ProcessState):
    """Délègue à screw_render.recommend_element_count."""
    cfg = state.screw_config
    solid_flow = _aggregated_solid_flow(state.feeders)
    density = equivalent_main_density(state.feeders)
    return recommend_element_count(
        cfg, float(state.screw_rpm), solid_flow, density,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
        position_to_zone_fn=position_to_zone,
        zone_residence_fn=zone_residence_times,
    )
