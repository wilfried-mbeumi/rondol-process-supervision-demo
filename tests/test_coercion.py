"""Tests coercion.py — convertisseurs session→métier qui ne lèvent jamais."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core.coercion import safe_choice, safe_float, safe_int  # noqa: E402


# ---------------------------------------------------------------------------
# safe_int — cœur du fix « crash langue / n_die_zones »
# ---------------------------------------------------------------------------
def test_safe_int_never_raises_on_garbage():
    for bad in ("", None, "abc", [], {}, "Nombre de zones", object()):
        assert safe_int(bad, 1) == 1  # défaut, jamais d'exception


def test_safe_int_accepts_decimal_string_and_float():
    assert safe_int("2.0", 1) == 2
    assert safe_int(2.7, 1) == 2          # troncature
    assert safe_int("3", 1) == 3
    assert safe_int(float("nan"), 1) == 1
    assert safe_int(float("inf"), 1) == 1


def test_safe_int_clamps():
    assert safe_int(9, 1, 1, 4) == 4
    assert safe_int(0, 1, 1, 4) == 1
    assert safe_int("99", 1, 1, 4) == 4


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------
def test_safe_float_never_raises_on_garbage():
    for bad in ("", None, "n/a", [], {}):
        assert safe_float(bad, 120.0) == 120.0


def test_safe_float_rejects_nan_inf():
    assert safe_float(float("nan"), 0.55) == 0.55
    assert safe_float(float("-inf"), 0.55) == 0.55


def test_safe_float_clamps():
    assert safe_float(5000.0, 120.0, 1.0, 3000.0) == 3000.0
    assert safe_float(-1.0, 0.55, 0.0001, 10.0) == 0.0001


# ---------------------------------------------------------------------------
# safe_choice — valeur d'UI traduite ne devient jamais métier
# ---------------------------------------------------------------------------
def test_safe_choice():
    assert safe_choice("fr", ("fr", "en"), "fr") == "fr"
    assert safe_choice("Language", ("fr", "en"), "fr") == "fr"  # libellé UI rejeté
    assert safe_choice(None, ("fr", "en"), "fr") == "fr"
    assert safe_choice(3, (1, 2, 3, 4), 1) == 3
