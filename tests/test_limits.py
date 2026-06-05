"""Tests Phase 1.5 — materials/limits.py (helpers de clamp purs)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from materials import limits as lm  # noqa: E402

TOL = 1e-12


def test_clamp_basic():
    assert lm.clamp(5.0, 0.0, 10.0) == 5.0
    assert lm.clamp(-1.0, 0.0, 10.0) == 0.0
    assert lm.clamp(11.0, 0.0, 10.0) == 10.0
    assert lm.clamp(math.nan, 0.0, 10.0) == 0.0


def test_clamp_viscosity_non_finite():
    lo, hi = lm.VISCOSITY_FLOOR_PA_S, lm.VISCOSITY_CEILING_PA_S
    assert lm.clamp_viscosity(math.inf) == hi
    assert lm.clamp_viscosity(-math.inf) == lo
    assert lm.clamp_viscosity(math.nan) == lo
    # valeur finie dans les bornes inchangée
    assert lm.clamp_viscosity(100.0) == 100.0
    # toujours fini
    for v in (math.inf, -math.inf, math.nan, 1e30, -5.0):
        assert math.isfinite(lm.clamp_viscosity(v))


def test_clamp_viscosity_custom_bounds():
    assert lm.clamp_viscosity(5.0, lo=10.0, hi=100.0) == 10.0
    assert lm.clamp_viscosity(500.0, lo=10.0, hi=100.0) == 100.0


def test_clamp_volume_fraction():
    assert lm.clamp_volume_fraction(0.3) == 0.3
    assert lm.clamp_volume_fraction(-0.2) == 0.0
    assert lm.clamp_volume_fraction(1.5) == 1.0
    assert lm.clamp_volume_fraction(math.nan) == 0.0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("limits: all tests passed")
