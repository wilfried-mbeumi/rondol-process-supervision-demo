"""Tests — statut de validation honnête + distinction des débits (calc_audit)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from calc_audit import (  # noqa: E402
    CALCULATED_CONFIRMED,
    CALCULATED_WITH_ASSUMPTIONS,
    NOT_VALIDATED,
    fill_factor_validation_status,
    flow_taxonomy_rows,
    formula_status_label,
)


# ---------------------------------------------------------------------------
# Statut du fill factor
# ---------------------------------------------------------------------------
def test_fill_factor_status_is_assumption_when_db_constants_unconfirmed():
    # DB non confirmée → jamais CONFIRMED, même si débit connu.
    s = fill_factor_validation_status(feed_known=True, db_constants_confirmed=False,
                                      manager_correction_active=False)
    assert s == CALCULATED_WITH_ASSUMPTIONS


def test_fill_factor_status_is_assumption_when_manager_correction_active():
    s = fill_factor_validation_status(feed_known=True, db_constants_confirmed=True,
                                      manager_correction_active=True)
    assert s == CALCULATED_WITH_ASSUMPTIONS


def test_fill_factor_status_confirmed_only_when_all_validated():
    s = fill_factor_validation_status(feed_known=True, db_constants_confirmed=True,
                                      manager_correction_active=False)
    assert s == CALCULATED_CONFIRMED


def test_fill_factor_status_not_validated_without_feed():
    s = fill_factor_validation_status(feed_known=False)
    assert s == NOT_VALIDATED


def test_current_default_status_is_with_assumptions():
    # État courant du dépôt : DB non confirmée + ×2 manager actif → hypothèses.
    assert fill_factor_validation_status(feed_known=True) == CALCULATED_WITH_ASSUMPTIONS


def test_no_unvalidated_result_labeled_as_validated():
    # Le libellé de formule ne doit PAS dire « validée » tant que DB/manager non OK.
    label = formula_status_label()
    assert "validée" not in label.lower() or "utilisée" in label.lower()
    assert "à confirmer" in label.lower()


# ---------------------------------------------------------------------------
# Distinction des débits
# ---------------------------------------------------------------------------
def test_audit_panel_distinguishes_feed_machine_output_polymer_flow():
    rows = flow_taxonomy_rows(feed_effective_g_h=300.0, machine_max_capacity_g_h=1000.0,
                              output_flow_g_h=300.0)
    variables = [r["variable"] for r in rows]
    assert any("feeder utilisé" in v for v in variables)
    assert any("machine maximal" in v for v in variables)
    assert any("sortie filière" in v for v in variables)
    assert any("polymère sec" in v for v in variables)
    assert any("humidité" in v.lower() for v in variables)


def test_machine_capacity_not_confused_with_feeder_flow():
    rows = flow_taxonomy_rows(300.0, 1000.0, 300.0)
    feed = next(r for r in rows if "feeder utilisé" in r["variable"])
    mach = next(r for r in rows if "machine maximal" in r["variable"])
    assert feed["used_in_ff"] == "Oui"
    assert mach["used_in_ff"] == "Non"           # capacité machine PAS dans le FF
    assert "300" in feed["valeur"] and "1000" in mach["valeur"]


def test_output_flow_not_confused_with_input_feed():
    rows = flow_taxonomy_rows(300.0, None, 300.0)
    out = next(r for r in rows if "sortie filière" in r["variable"])
    assert out["used_in_ff"] == "Non"
    assert "régime permanent" in out["commentaire"].lower()


def test_1kg_h_capacity_does_not_override_300g_h_feed():
    # Capacité 1 kg/h fournie : le débit feeder utilisé reste 300 g/h.
    rows = flow_taxonomy_rows(feed_effective_g_h=300.0, machine_max_capacity_g_h=1000.0,
                              output_flow_g_h=300.0)
    feed = next(r for r in rows if "feeder utilisé" in r["variable"])
    assert "300" in feed["valeur"] and "1000" not in feed["valeur"]
    mach = next(r for r in rows if "machine maximal" in r["variable"])
    assert "n'écrase pas" in mach["commentaire"].lower()


def test_polymer_and_humidity_not_available():
    rows = flow_taxonomy_rows(300.0, None, 300.0)
    poly = next(r for r in rows if "polymère sec" in r["variable"])
    hum = next(r for r in rows if "humidité" in r["variable"].lower())
    assert poly["valeur"] == "Non disponible"
    assert hum["valeur"] == "Non disponible"
