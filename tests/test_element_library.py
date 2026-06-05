"""Tests Phase 1 — machine/element_library.py.

Vérifie notamment que la couche physique reste FIDÈLE à screw_logic
(volumes/facteurs délégués, jamais redéfinis).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from machine import element_library as el  # noqa: E402  (déclenche le bootstrap sys.path)
import screw_logic as sl  # noqa: E402  (module nu — MÊME objet que celui d'element_library)


def test_all_13_ids_present():
    assert set(el.ELEMENT_PHYSICS) == set(range(1, 14))
    assert el.N_REAL_ELEMENT_TYPES == 13


def test_free_volume_delegates_to_screw_logic():
    # Source de vérité = screw_logic.VOLUME_CM3 / FACTOR_FREE_BY_REV
    for tid in range(1, 14):
        assert el.free_volume_cm3(tid) == sl.VOLUME_CM3[tid]
        assert el.free_volume_by_rev_factor(tid) == sl.FACTOR_FREE_BY_REV[tid]


def test_conveying_signs():
    assert el.conveying_direction(1) == el.CONVEY_FORWARD   # convoyage +
    assert el.conveying_direction(2) == el.CONVEY_FORWARD   # convoyage ½
    assert el.conveying_direction(9) == el.CONVEY_REVERSE   # convoyage −
    assert el.conveying_direction(4) == el.CONVEY_NEUTRAL   # malaxage 90°


def test_kneading_angles_match_labels():
    # Labels screw_logic : 90°/30°/60°/45° pour ids 4/5/7/8
    angles = {4: 90.0, 5: 30.0, 7: 60.0, 8: 45.0}
    for tid, ang in angles.items():
        assert el.is_kneading(tid)
        assert el.physics_for(tid).kneading_angle_deg == ang
    # un non-malaxeur n'a pas d'angle
    assert el.physics_for(1).kneading_angle_deg is None
    assert not el.is_kneading(1)


def test_intensities_in_range():
    for tid, p in el.ELEMENT_PHYSICS.items():
        assert 0.0 <= p.mixing_intensity <= 1.0, tid
        assert 0.0 <= p.pressure_capacity <= 1.0, tid


def test_labels_delegate():
    for tid in range(1, 14):
        assert el.element_label(tid) == sl.ELEMENT_TYPES[tid].label


def test_channel_depth_nominal_and_override():
    # Tous les éléments renvoient le nominal global (aucun override en Phase 1.5).
    for tid in range(1, 14):
        assert el.channel_depth_mm(tid) == el.NOMINAL_CHANNEL_DEPTH_MM
        assert el.physics_for(tid).channel_depth_mm is None
    assert el.NOMINAL_CHANNEL_DEPTH_MM > 0.0
    assert el.SCREW_DIAMETER_MM == 10.5
    # L'accesseur respecte un override par élément s'il était défini.
    p = el.ElementPhysics(99, el.CONVEY_FORWARD, False, None, 0.1, 0.1, channel_depth_mm=2.5)
    assert p.channel_depth_mm == 2.5


def test_unknown_type_raises():
    try:
        el.physics_for(99)
        assert False, "KeyError attendue"
    except KeyError:
        pass


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("element_library: all tests passed")
