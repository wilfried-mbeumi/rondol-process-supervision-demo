"""Tests Phase 1 — physics/conversions.py (conversions pures)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from physics import conversions as cv  # noqa: E402

TOL = 1e-9


def test_rpm_rps_literal():
    assert cv.rpm_to_rps(120.0) == 2.0
    assert cv.rps_to_rpm(2.0) == 120.0


def test_flow_literals():
    assert cv.g_per_min_to_g_per_s(60.0) == 1.0
    assert cv.g_per_s_to_g_per_min(1.0) == 60.0
    assert cv.g_per_h_to_g_per_s(3600.0) == 1.0
    assert cv.g_per_s_to_kg_per_h(1.0) == 3.6
    assert abs(cv.kg_per_h_to_g_per_s(3.6) - 1.0) < TOL


def test_roundtrips():
    for f in (12.3, 0.0, 999.9):
        assert abs(cv.rps_to_rpm(cv.rpm_to_rps(f)) - f) < TOL
        assert abs(cv.g_per_s_to_g_per_min(cv.g_per_min_to_g_per_s(f)) - f) < TOL
        assert abs(cv.kelvin_to_celsius(cv.celsius_to_kelvin(f)) - f) < TOL
        assert abs(cv.m3_to_cm3(cv.cm3_to_m3(f)) - f) < TOL
        assert abs(cv.pa_to_bar(cv.bar_to_pa(f)) - f) < TOL


def test_temperature_literals():
    assert abs(cv.celsius_to_kelvin(0.0) - 273.15) < TOL
    assert abs(cv.celsius_to_kelvin(20.0) - 293.15) < TOL
    assert abs(cv.kelvin_to_celsius(273.15)) < TOL


def test_volumetric_flow():
    # ṁ = 2 g/s, ρ = 1 g/cm³ → Q = 2 cm³/s
    assert abs(cv.volumetric_flow_cm3_s(2.0, 1.0) - 2.0) < TOL
    # densité nulle → garde anti-division
    assert cv.volumetric_flow_cm3_s(2.0, 0.0) == 0.0


def test_apparent_shear_rate():
    # γ̇ = π·D·N/h ; D=10, N=1 tr/s (60 rpm), h=1 → π·10
    g = cv.apparent_shear_rate_s(60.0, 10.0, 1.0)
    assert abs(g - math.pi * 10.0) < 1e-6
    # h=0 → garde
    assert cv.apparent_shear_rate_s(60.0, 10.0, 0.0) == 0.0
    # croît avec rpm
    assert cv.apparent_shear_rate_s(120.0, 10.0, 1.0) > g


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("conversions: all tests passed")
