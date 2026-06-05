"""port_map.py — cartographie des ports machine (PUR, lecture seule).

Abstraction des points d'accès le long de la vis (alimentation principale,
alimentation latérale 1..8, filière) au-dessus de `app/screw_logic.py`.

SOURCE DE VÉRITÉ des positions/zones = screw_logic (importé en lecture seule) :
  - MAIN_FEEDER_POSITION                  → port d'alimentation principale
  - SIDE_FEEDER_START_ELMT_Z / side_feeder_position → ports latéraux
  - TIP_PART1_POS                         → port filière (pointe + décharge)
  - position_to_zone                      → zone d'un port
Ce module NE recalcule aucune position : il délègue ou recopie les constantes.
"""

from __future__ import annotations

import machine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from dataclasses import dataclass

from screw_logic import (  # noqa: E402  (module nu — convention canonique, cf. machine/__init__)
    MAIN_FEEDER_POSITION,
    SIDE_FEEDER_DISABLED_POSITION,
    SIDE_FEEDER_DISABLED_ZONE,
    SIDE_FEEDER_MAX_ZONE,
    SIDE_FEEDER_START_ELMT_Z,
    TIP_PART1_POS,
    position_to_zone,
    side_feeder_position,
)

# Types de port
PORT_MAIN_FEED: str = "main_feed"
PORT_SIDE_FEED: str = "side_feed"
PORT_DIE: str = "die"


@dataclass(frozen=True)
class Port:
    """Port machine localisé sur la vis.

    Attributs :
      name     : identifiant lisible.
      kind     : PORT_MAIN_FEED | PORT_SIDE_FEED | PORT_DIE.
      position : index position screw_logic (0..80) ; sentinelle si désactivé.
      zone     : zone procédé (0=Feed, 1..8) du port.
    """
    name: str
    kind: str
    position: int
    zone: int


def main_feed_port() -> Port:
    """Port d'alimentation principale (screw_logic.MAIN_FEEDER_POSITION)."""
    pos = MAIN_FEEDER_POSITION
    return Port("Main feeder", PORT_MAIN_FEED, pos, position_to_zone(pos))


def side_feed_nominal_position(zone: int) -> int:
    """Position NOMINALE du side feeder pour une zone 1..8 (sans config).

    Recopie screw_logic.SIDE_FEEDER_START_ELMT_Z sans recul part2 (qui dépend
    de la config). zone=0 → sentinelle désactivée. Hors plage → ValueError.
    """
    if zone == SIDE_FEEDER_DISABLED_ZONE:
        return SIDE_FEEDER_DISABLED_POSITION
    if not (1 <= zone <= SIDE_FEEDER_MAX_ZONE):
        raise ValueError(f"zone side feeder invalide : {zone} (attendu 0..8)")
    return SIDE_FEEDER_START_ELMT_Z[zone - 1]


def side_feed_port(config: list[int], zone: int) -> Port:
    """Port d'alimentation latérale RÉSOLU sur une config donnée.

    DÉLÈGUE à screw_logic.side_feeder_position (gère le recul part2 et la
    sentinelle zone=0). La zone affichée reste la zone demandée.
    """
    pos = side_feeder_position(config, zone)
    return Port(f"Side feeder Z{zone}", PORT_SIDE_FEED, pos, zone)


def die_port() -> Port:
    """Port filière (pointe + décharge, screw_logic.TIP_PART1_POS)."""
    pos = TIP_PART1_POS
    return Port("Die / discharge", PORT_DIE, pos, position_to_zone(pos))


def port_zone(position: int) -> int:
    """Zone procédé d'une position — DÉLÈGUE à screw_logic.position_to_zone."""
    return position_to_zone(position)


def all_ports(config: list[int], side_feeder_zone: int = SIDE_FEEDER_DISABLED_ZONE) -> list[Port]:
    """Liste des ports actifs pour une config : main + (side si activé) + die."""
    ports = [main_feed_port()]
    if side_feeder_zone != SIDE_FEEDER_DISABLED_ZONE:
        ports.append(side_feed_port(config, side_feeder_zone))
    ports.append(die_port())
    return ports
