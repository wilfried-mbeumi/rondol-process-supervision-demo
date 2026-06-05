"""Tests Phase 1 — machine/die_library.py."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from machine import die_library as dl  # noqa: E402

TOL = 1e-9


def test_single_and_total_area():
    die = dl.Die("t", n_holes=3, hole_diameter_mm=2.0, land_length_mm=4.0)
    single = math.pi * 1.0 * 1.0  # r=1
    assert abs(dl.single_hole_area_mm2(die) - single) < TOL
    assert abs(dl.total_open_area_mm2(die) - 3 * single) < TOL


def test_aspect_ratio():
    die = dl.Die("t", n_holes=1, hole_diameter_mm=2.0, land_length_mm=6.0)
    assert abs(dl.aspect_ratio_l_d(die) - 3.0) < TOL
    # diamètre nul → garde
    assert dl.aspect_ratio_l_d(dl.Die("z", 1, 0.0, 1.0)) == 0.0


def test_wall_shear_rate():
    die = dl.Die("t", n_holes=1, hole_diameter_mm=2.0, land_length_mm=4.0)
    # Q = π mm³/s, R=1 → γ̇ = 4Q/(πR³) = 4
    g = dl.apparent_wall_shear_rate(die, math.pi)
    assert abs(g - 4.0) < 1e-6
    # proportionnel à Q
    assert abs(dl.apparent_wall_shear_rate(die, 2 * math.pi) - 2 * g) < 1e-6
    # Q=0 → 0
    assert dl.apparent_wall_shear_rate(die, 0.0) == 0.0
    # répartition sur les trous : 2 trous → moitié du cisaillement à Q égal
    twin = dl.Die("twin", n_holes=2, hole_diameter_mm=2.0, land_length_mm=4.0)
    assert abs(dl.apparent_wall_shear_rate(twin, math.pi) - g / 2.0) < 1e-6


def test_presets_physical():
    assert set(dl.DIES) >= {"strand_1mm", "strand_2mm", "twin_2x1mm"}
    for name, die in dl.DIES.items():
        assert die.n_holes >= 1, name
        assert die.hole_diameter_mm > 0.0, name
        assert die.land_length_mm > 0.0, name
        assert dl.total_open_area_mm2(die) > 0.0, name


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("die_library: all tests passed")
