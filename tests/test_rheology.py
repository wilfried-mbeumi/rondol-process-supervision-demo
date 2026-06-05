"""Tests Phase 1 — materials/rheology.py."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from materials import rheology as rh  # noqa: E402

TOL = 1e-9


def test_power_law_newtonian():
    # n = 1 → η = k quel que soit γ̇
    assert abs(rh.power_law_viscosity(10.0, 100.0, 1.0) - 100.0) < TOL
    assert abs(rh.power_law_viscosity(1000.0, 100.0, 1.0) - 100.0) < TOL


def test_power_law_shear_thinning():
    # n < 1 → η décroît quand γ̇ augmente
    lo = rh.power_law_viscosity(1.0, 100.0, 0.5)
    hi = rh.power_law_viscosity(100.0, 100.0, 0.5)
    assert hi < lo
    # divergence à γ̇=0 pour n<1
    assert rh.power_law_viscosity(0.0, 100.0, 0.5) == math.inf


def test_cross_limits():
    eta0, etainf = 1000.0, 10.0
    # γ̇ → 0 : ≈ η₀
    near_zero = rh.cross_viscosity(1e-9, eta0, etainf, 1.0, 0.8)
    assert abs(near_zero - eta0) < 1.0
    # γ̇ très grand : → η∞
    near_inf = rh.cross_viscosity(1e9, eta0, etainf, 1.0, 0.8)
    assert abs(near_inf - etainf) < 1.0
    # monotone décroissant entre les deux
    assert near_inf < rh.cross_viscosity(1.0, eta0, etainf, 1.0, 0.8) < near_zero


def test_arrhenius_factor():
    # a_T = 1 à Tref
    assert abs(rh.arrhenius_temperature_factor(20.0, 50000.0, 20.0) - 1.0) < TOL
    # Ea>0, T>Tref → a_T < 1 (viscosité baisse en chauffant)
    assert rh.arrhenius_temperature_factor(200.0, 50000.0, 20.0) < 1.0
    # T<Tref → a_T > 1
    assert rh.arrhenius_temperature_factor(0.0, 50000.0, 20.0) > 1.0


def test_carreau_yasuda_manager_form():
    # Défauts (eta_inf=0, a=2) == forme littérale manager η₀[1+(λγ̇)²]^((n-1)/2)
    eta0, lam, n = 1000.0, 1.0, 0.5
    g = 4.0
    expected = eta0 * (1.0 + (lam * g) ** 2) ** ((n - 1.0) / 2.0)
    assert abs(rh.carreau_yasuda_viscosity(g, eta0, relax_time_s=lam, flow_index_n=n) - expected) < 1e-6


def test_carreau_yasuda_limits_and_finite():
    eta0, etainf = 1000.0, 10.0
    # γ̇ → 0 : → η₀
    assert abs(rh.carreau_yasuda_viscosity(1e-12, eta0, etainf, 1.0, 0.5) - eta0) < 1.0
    # γ̇ très grand : → η∞
    assert abs(rh.carreau_yasuda_viscosity(1e9, eta0, etainf, 1.0, 0.5) - etainf) < 1.0
    # FINI à γ̇=0 (contraste avec power_law qui diverge)
    val0 = rh.carreau_yasuda_viscosity(0.0, eta0, etainf, 1.0, 0.5)
    assert math.isfinite(val0) and abs(val0 - eta0) < TOL
    # shear-thinning : décroît avec γ̇
    assert rh.carreau_yasuda_viscosity(100.0, eta0, etainf, 1.0, 0.5) < rh.carreau_yasuda_viscosity(1.0, eta0, etainf, 1.0, 0.5)


def test_apply_shift():
    assert abs(rh.apply_temperature_shift(100.0, 0.5) - 50.0) < TOL


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("rheology: all tests passed")
