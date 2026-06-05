"""Tests Phase 1 — machine/port_map.py.

Vérifie que les ports délèguent fidèlement aux positions/zones screw_logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from machine import port_map as pm  # noqa: E402  (déclenche le bootstrap sys.path)
import screw_logic as sl  # noqa: E402  (module nu — MÊME objet que celui de port_map)


def _empty():
    return sl.new_empty_configuration()


def test_main_feed_port():
    p = pm.main_feed_port()
    assert p.kind == pm.PORT_MAIN_FEED
    assert p.position == sl.MAIN_FEEDER_POSITION
    assert p.zone == sl.position_to_zone(sl.MAIN_FEEDER_POSITION)


def test_side_feed_nominal_positions():
    for zone in range(1, 9):
        assert pm.side_feed_nominal_position(zone) == sl.SIDE_FEEDER_START_ELMT_Z[zone - 1]
    # zone 0 → sentinelle désactivée
    assert pm.side_feed_nominal_position(0) == sl.SIDE_FEEDER_DISABLED_POSITION


def test_side_feed_nominal_out_of_range():
    for bad in (-1, 9, 100):
        try:
            pm.side_feed_nominal_position(bad)
            assert False, "ValueError attendue"
        except ValueError:
            pass


def test_side_feed_port_delegates():
    cfg = _empty()
    for zone in range(0, 9):
        port = pm.side_feed_port(cfg, zone)
        assert port.position == sl.side_feeder_position(cfg, zone)
        assert port.kind == pm.PORT_SIDE_FEED


def test_die_port():
    p = pm.die_port()
    assert p.kind == pm.PORT_DIE
    assert p.position == sl.TIP_PART1_POS


def test_all_ports():
    cfg = _empty()
    # sans side feeder
    kinds = [p.kind for p in pm.all_ports(cfg, side_feeder_zone=0)]
    assert kinds == [pm.PORT_MAIN_FEED, pm.PORT_DIE]
    # avec side feeder zone 3
    kinds3 = [p.kind for p in pm.all_ports(cfg, side_feeder_zone=3)]
    assert kinds3 == [pm.PORT_MAIN_FEED, pm.PORT_SIDE_FEED, pm.PORT_DIE]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("port_map: all tests passed")
