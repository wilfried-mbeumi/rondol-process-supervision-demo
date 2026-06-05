"""Tests Phase 1 — materials/powder.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from materials import powder as pw  # noqa: E402

TOL = 1e-9


def test_density_at_tref_is_nominal():
    p = pw.Powder("x", bulk_density_g_cm3=1.2, true_density_g_cm3=3.6,
                  thermal_exp_per_k=2.0e-5)
    assert abs(pw.bulk_density_at_temp(p, pw.TREF_C) - 1.2) < TOL


def test_density_decreases_when_heated():
    p = pw.Powder("x", bulk_density_g_cm3=1.2, true_density_g_cm3=3.6,
                  thermal_exp_per_k=2.0e-5)
    hot = pw.bulk_density_at_temp(p, 200.0)
    assert hot < 1.2
    # alpha = 0 → invariant en température
    p0 = pw.Powder("y", 1.2, 3.6, thermal_exp_per_k=0.0)
    assert abs(pw.bulk_density_at_temp(p0, 200.0) - 1.2) < TOL


def test_packing_and_void():
    p = pw.Powder("x", bulk_density_g_cm3=1.8, true_density_g_cm3=3.6)
    assert abs(pw.packing_fraction(p) - 0.5) < TOL
    assert abs(pw.void_fraction(p) - 0.5) < TOL
    # densité vraie nulle → garde
    assert pw.packing_fraction(pw.Powder("z", 1.0, 0.0)) == 0.0


def test_presets_are_physical():
    assert set(pw.POWDERS) >= {"LFP", "LATP", "graphite", "PVDF"}
    for name, p in pw.POWDERS.items():
        assert 0.0 < p.bulk_density_g_cm3 < p.true_density_g_cm3, name
        assert 0.0 < pw.packing_fraction(p) < 1.0, name


def test_cp_field():
    # Champ Cp rétro-compatible (défaut 0.0) et présent/physique dans les presets.
    assert pw.Powder("x", 1.0, 2.0).cp_j_per_g_k == 0.0
    for name, p in pw.POWDERS.items():
        assert 0.0 < p.cp_j_per_g_k < 5.0, name  # J/g/K, ordre de grandeur


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("powder: all tests passed")
