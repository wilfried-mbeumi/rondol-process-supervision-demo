"""extrusion_graph.py — graph d'extrusion ordonné (Phase 2).

`ExtrusionGraph` assemble la séquence ordonnée des `NodeState` (positions 0..80)
au-dessus d'UN UNIQUE appel à `screw_logic.compute_process_state` (Network 7).

INVARIANT « PAS DE 2e MOTEUR » :
  Network 7 est appelé EXACTEMENT UNE FOIS dans `build_graph`. Tous les nœuds
  enveloppent le même `ProcessState`. Le graph n'introduit aucune nouvelle
  propagation de débit/remplissage/résidence — il structure et expose l'existant.

Le graph dérive aussi le `FeedContext` (matière nominale par position) à partir
des paramètres feeder : les débits VOLUMIQUES feeder1/feeder2 servant au prorata
de mélange sont des grandeurs d'ENTRÉE feeder (Q = ṁ/ρ, cf. conversions), pas une
ré-exécution du procédé.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from dataclasses import dataclass

from screw_logic import (  # noqa: E402  (module nu — convention canonique)
    N_POSITIONS,
    START_ELMT_ZONE,
    ProcessParams,
    ProcessState,
    compute_process_state,
)
from physics.conversions import volumetric_flow_cm3_s  # noqa: E402
from materials.powder import Powder  # noqa: E402
from engine.material_context import FeedContext  # noqa: E402
from engine.node_state import NodeState, build_node  # noqa: E402

# Nombre de zones procédé (Feed + Z1..Z8) = len(START_ELMT_ZONE) - 1 = 9.
N_ZONES: int = len(START_ELMT_ZONE) - 1


def _feed_context_from(
    params: ProcessParams,
    process_state: ProcessState,
    feeder1_powder: Powder,
    feeder2_powder: Powder | None,
) -> FeedContext:
    """Construit le FeedContext pour le graph.

    Les débits volumiques feeder = Q = ṁ/ρ (conversions.volumetric_flow_cm3_s,
    miroir de screw_logic L533) — grandeur d'ENTRÉE feeder, utilisée seulement
    pour le prorata de mélange. La densité utilisée est la densité apparente
    NOMINALE des paramètres (la correction thermique se simplifie dans un ratio).
    """
    q1 = volumetric_flow_cm3_s(
        params.feeder1_flow_rate_g_per_s, params.feeder1_bulk_density
    )
    q2 = volumetric_flow_cm3_s(
        params.feeder2_flow_rate_g_per_s, params.feeder2_bulk_density
    )
    return FeedContext(
        feeder1_powder=feeder1_powder,
        feeder1_qvol_cm3_s=q1,
        feeder2_powder=feeder2_powder,
        feeder2_qvol_cm3_s=q2,
        side_feeder_position=process_state.side_feeder_position,
    )


@dataclass(frozen=True)
class ExtrusionGraph:
    """Séquence ordonnée des NodeState + le ProcessState enveloppé.

    Attributs :
      nodes         : tuple ordonné des NodeState (index = position 0..80).
      process_state : le ProcessState UNIQUE produit par Network 7.
      params        : ProcessParams utilisés.
      feed_context  : contexte matière dérivé.
    """
    nodes: tuple[NodeState, ...]
    process_state: ProcessState
    params: ProcessParams
    feed_context: FeedContext

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self):
        return iter(self.nodes)

    def __getitem__(self, position: int) -> NodeState:
        return self.nodes[position]

    def node_at(self, position: int) -> NodeState:
        """NodeState à une position (0..80). Lève IndexError hors plage."""
        return self.nodes[position]

    def nodes_in_zone(self, zone: int) -> list[NodeState]:
        """Tous les NodeState d'une zone procédé (0..8), dans l'ordre."""
        return [n for n in self.nodes if n.zone == zone]

    def first_parts(self) -> list[NodeState]:
        """Nœuds « 1ère partie » uniquement (exclut les demi-éléments part2).

        Utile pour des agrégats qui ne doivent pas double-compter un élément
        entier occupant 2 positions. NE concerne PAS les agrégats procédé qui,
        eux, réutilisent les totaux ProcessState (lesquels somment déjà part2).
        """
        return [n for n in self.nodes if not n.is_part2]

    def ports(self) -> list[NodeState]:
        """Nœuds portant un port machine (main_feed / side_feed / die)."""
        return [n for n in self.nodes if n.port_kind is not None]


def build_graph(
    config: list[int],
    params: ProcessParams,
    feeder1_powder: Powder,
    feeder2_powder: Powder | None = None,
) -> ExtrusionGraph:
    """Construit l'ExtrusionGraph en appelant Network 7 UNE SEULE FOIS.

    Pur : ne modifie pas `config`. `compute_process_state` est invoqué une seule
    fois ; chaque NodeState enveloppe l'index correspondant de ce ProcessState.
    """
    process_state = compute_process_state(config, params)
    feed_context = _feed_context_from(
        params, process_state, feeder1_powder, feeder2_powder
    )
    nodes = tuple(
        build_node(pos, config, process_state, params, feed_context)
        for pos in range(N_POSITIONS)
    )
    return ExtrusionGraph(
        nodes=nodes,
        process_state=process_state,
        params=params,
        feed_context=feed_context,
    )
