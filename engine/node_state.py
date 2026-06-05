"""node_state.py — état local par position de vis / demi-élément (Phase 2).

`NodeState` est l'unité d'état LOCAL de l'agent procédé : une position de la vis
(index 0..80 de screw_logic), avec tout ce qui s'y rapporte.

PRINCIPE — ENVELOPPER `ProcessState`, NE PAS LE RECALCULER :
  Les grandeurs procédé déjà produites par le Network 7
  (`screw_logic.compute_process_state`) sont RECOPIÉES verbatim depuis
  `ProcessState[i]` :
    - local_free_volume_cm3 / local_free_volume_by_rev (remplissage géométrique)
    - fill_factor / vol_flow_cm3_s / residence_time_s (remplissage, débit local,
      résidence)
  `NodeState` n'en reproduit AUCUN calcul. Il ne fait qu'AJOUTER ce que Network 7
  ne porte pas : classification (zone, port, type d'élément), matière présente,
  température locale, et le cisaillement local γ̇ (E1, calculable dès maintenant
  via physics.conversions + machine.element_library).

E4/E5/E6/E7 (couple, SME, T_real, pression) sont des CHAMPS PRÉSENTS mais à
`None` — leur calcul est délégué à `engine/deferred.py` (dépendances non prêtes).
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from dataclasses import dataclass

from screw_logic import (  # noqa: E402  (module nu — convention canonique)
    MAIN_FEEDER_POSITION,
    N_ZONES_TEMP,
    TIP_PART1_POS,
    ProcessParams,
    ProcessState,
    base_type,
    is_part2,
    position_to_zone,
)
from machine import element_library as el  # noqa: E402
from machine.port_map import PORT_DIE, PORT_MAIN_FEED, PORT_SIDE_FEED  # noqa: E402
from physics.conversions import apparent_shear_rate_s  # noqa: E402
from engine.material_context import FeedContext, MaterialPresence  # noqa: E402

# Type d'élément "case vide" (screw_logic : config[i] == 0).
EMPTY_TYPE: int = 0


@dataclass(frozen=True)
class NodeState:
    """État local d'UNE position de vis (0..80).

    Champs de CLASSIFICATION (ajoutés par engine) :
      position        : index screw_logic 0..80.
      raw_value       : valeur brute config[i] (peut être ≥100 pour une 2e partie).
      type_id         : type d'élément effectif (base_type — 0..13).
      is_part2        : True si 2e moitié d'un élément entier (valeur ≥ 100).
      is_empty        : True si position libre (type 0).
      element_label   : libellé HMI de l'élément (délégué à element_library).
      zone            : zone procédé 0..8 (délégué à screw_logic.position_to_zone).
      port_kind       : "main_feed" | "side_feed" | "die" | None.

    Champs ENVELOPPÉS depuis ProcessState[i] (RECOPIE verbatim, jamais recalcul) :
      local_free_volume_cm3     : cm³.
      local_free_volume_by_rev  : cm³/tour.
      fill_factor               : taux de remplissage local ∈ [0, 1].
      vol_flow_cm3_s            : débit volumique local cm³/s.
      residence_time_s          : temps de séjour local s.

    Champs AJOUTÉS par engine (calculables dès Phase 2) :
      temperature_c    : température de consigne de la zone (params.temp_z[zone]).
      channel_depth_mm : profondeur de chenal `h` de l'élément (mm) — DÉLÈGUE à
                         machine.element_library.channel_depth_mm via le wrapper
                         _channel_depth_for (nominal pour case vide/hors plage).
                         C'est l'entrée géométrique de γ̇ (E1) ET du futur couple
                         E4 (M ∝ η·γ̇·V/h) ; exposée ici, jamais recalculée.
      shear_rate_s     : cisaillement local γ̇ ≈ πDN/h (E1) s⁻¹.
      material         : matière nominale présente (engine.material_context).

    Champs DIFFÉRÉS E4–E7 (toujours None en Phase 2 — cf. engine/deferred.py) :
      torque_nm       : couple local (E4).
      sme_kwh_per_kg  : énergie mécanique spécifique locale (E5).
      t_real_c        : température réelle du fondu (E6, équation manager Maël).
      pressure_bar    : pression locale / contre-pression (E7).
    """
    # Classification
    position: int
    raw_value: int
    type_id: int
    is_part2: bool
    is_empty: bool
    element_label: str
    zone: int
    port_kind: str | None

    # Enveloppe ProcessState[i] (verbatim)
    local_free_volume_cm3: float
    local_free_volume_by_rev: float
    fill_factor: float
    vol_flow_cm3_s: float
    residence_time_s: float

    # Ajouts engine (Phase 2 + 3.1)
    temperature_c: float
    channel_depth_mm: float
    shear_rate_s: float
    material: MaterialPresence

    # Différés E4–E7 (None en Phase 2)
    torque_nm: float | None = None
    sme_kwh_per_kg: float | None = None
    t_real_c: float | None = None
    pressure_bar: float | None = None


def _port_kind_for(position: int, side_feeder_position: int) -> str | None:
    """Classifie une position en port machine, sinon None.

    DÉLÈGue les positions de référence à screw_logic / ProcessState :
      - MAIN_FEEDER_POSITION → main_feed
      - side_feeder_position (issu de ProcessState) → side_feed
      - TIP_PART1_POS        → die
    """
    if position == MAIN_FEEDER_POSITION:
        return PORT_MAIN_FEED
    if position == side_feeder_position:
        return PORT_SIDE_FEED
    if position == TIP_PART1_POS:
        return PORT_DIE
    return None


def _channel_depth_for(type_id: int) -> float:
    """Profondeur de chenal pour γ̇ : override élément si type 1..13, sinon nominal.

    Une case vide (type 0) n'a pas d'entrée dans ELEMENT_PHYSICS → on utilise le
    nominal global (γ̇ reste une estimation kinématique finie πDN/h_nominal).
    """
    if 1 <= type_id <= 13:
        return el.channel_depth_mm(type_id)
    return el.NOMINAL_CHANNEL_DEPTH_MM


def build_node(
    position: int,
    config: list[int],
    process_state: ProcessState,
    params: ProcessParams,
    feed_context: FeedContext,
) -> NodeState:
    """Construit le NodeState d'une position en ENVELOPPANT ProcessState[i].

    Pur : ne modifie ni `config`, ni `process_state`, ni `params`. Ne recalcule
    aucune grandeur déjà fournie par ProcessState — il la recopie.
    """
    raw = config[position]
    type_id = base_type(raw)
    part2 = is_part2(raw)
    empty = type_id == EMPTY_TYPE
    zone = position_to_zone(position)

    # Température de consigne de la zone (clamp index défensif sur temp_z).
    zidx = zone if 0 <= zone < N_ZONES_TEMP else 0
    temperature_c = params.temp_z[zidx]

    # Bloc 3.1 — profondeur de chenal `h` (mm) : DÉLÉGUÉE à element_library via
    # _channel_depth_for. Calculée UNE FOIS et réutilisée pour le champ exposé ET
    # pour γ̇ → garantit channel_depth_mm == h utilisé dans le cisaillement.
    depth = _channel_depth_for(type_id)

    # E1 — cisaillement local γ̇ ≈ πDN/h (machine.element_library + conversions).
    shear = apparent_shear_rate_s(
        params.screw_rpm, el.SCREW_DIAMETER_MM, depth
    )

    label = el.element_label(type_id) if 1 <= type_id <= 13 else "Vide"

    return NodeState(
        position=position,
        raw_value=raw,
        type_id=type_id,
        is_part2=part2,
        is_empty=empty,
        element_label=label,
        zone=zone,
        port_kind=_port_kind_for(position, process_state.side_feeder_position),
        # --- Enveloppe ProcessState[i] : RECOPIE, pas de recalcul ---
        local_free_volume_cm3=process_state.local_free_volume_cm3[position],
        local_free_volume_by_rev=process_state.local_free_volume_by_rev[position],
        fill_factor=process_state.fill_factor_local[position],
        vol_flow_cm3_s=process_state.vol_flow_cm3_s[position],
        residence_time_s=process_state.residence_time_local[position],
        # --- Ajouts engine ---
        temperature_c=temperature_c,
        channel_depth_mm=depth,
        shear_rate_s=shear,
        material=feed_context.presence_at(position),
        # --- E4–E7 différés ---
        torque_nm=None,
        sme_kwh_per_kg=None,
        t_real_c=None,
        pressure_bar=None,
    )
