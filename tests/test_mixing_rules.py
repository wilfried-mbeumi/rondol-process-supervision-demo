"""Tests Phase 1 — materials/mixing_rules.py."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from materials import mixing_rules as mx  # noqa: E402

TOL = 1e-9


def test_mass_volume_roundtrip():
    densities = [3.6, 1.78, 2.26]
    mass = [0.5, 0.3, 0.2]
    vol = mx.mass_to_volume_fractions(mass, densities)
    assert abs(sum(vol) - 1.0) < TOL
    back = mx.volume_to_mass_fractions(vol, densities)
    for a, b in zip(mass, back):
        assert abs(a - b) < 1e-9


def test_mixture_density_single_component():
    assert abs(mx.mixture_density([1.0], [2.5], basis="mass") - 2.5) < TOL
    assert abs(mx.mixture_density([1.0], [2.5], basis="volume") - 2.5) < TOL


def test_mixture_density_basis():
    # 50/50 volume de 1 et 3 → 2.0
    assert abs(mx.mixture_density([0.5, 0.5], [1.0, 3.0], basis="volume") - 2.0) < TOL
    # mass basis : 1/ρ = 0.5/1 + 0.5/3
    expected = 1.0 / (0.5 / 1.0 + 0.5 / 3.0)
    assert abs(mx.mixture_density([0.5, 0.5], [1.0, 3.0], basis="mass") - expected) < TOL


def test_log_additive_identity():
    # viscosités identiques → la même
    assert abs(mx.log_additive_viscosity([50.0, 50.0], [0.4, 0.6]) - 50.0) < 1e-9
    # produit pondéré
    val = mx.log_additive_viscosity([10.0, 1000.0], [0.5, 0.5])
    assert abs(val - math.sqrt(10.0 * 1000.0)) < 1e-6


def test_mixture_specific_heat():
    # Moyenne massique : 50/50 de Cp 1.0 et 2.0 → 1.5
    assert abs(mx.mixture_specific_heat([0.5, 0.5], [1.0, 2.0]) - 1.5) < TOL
    # mono-composant → son Cp
    assert abs(mx.mixture_specific_heat([1.0], [0.71]) - 0.71) < TOL
    # longueurs incohérentes → ValueError
    try:
        mx.mixture_specific_heat([1.0], [1.0, 2.0])
        assert False, "ValueError attendue"
    except ValueError:
        pass


def test_einstein_dilute():
    assert abs(mx.einstein_viscosity(1.0, 0.0) - 1.0) < TOL
    assert abs(mx.einstein_viscosity(1.0, 0.01) - 1.025) < TOL


def test_krieger_dougherty():
    # φ=0 → η_medium
    assert abs(mx.krieger_dougherty_viscosity(1.0, 0.0, 0.64) - 1.0) < TOL
    # monotone croissant
    a = mx.krieger_dougherty_viscosity(1.0, 0.2, 0.64)
    b = mx.krieger_dougherty_viscosity(1.0, 0.5, 0.64)
    assert b > a > 1.0
    # diverge à φ → φmax
    assert mx.krieger_dougherty_viscosity(1.0, 0.64, 0.64) == math.inf


def test_errors():
    for fn in (mx.mass_to_volume_fractions, mx.volume_to_mass_fractions):
        try:
            fn([1.0], [1.0, 2.0])
            assert False, "ValueError attendue"
        except ValueError:
            pass
    try:
        mx.mixture_density([1.0], [1.0], basis="bogus")
        assert False, "ValueError attendue"
    except ValueError:
        pass
    try:
        mx.krieger_dougherty_viscosity(1.0, 0.2, 0.0)
        assert False, "ValueError attendue"
    except ValueError:
        pass


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("mixing_rules: all tests passed")
