"""Tests SME — wording procédé (P4) + suppression du seuil critique 0.40 (S2).

Exigence manager 2026-06-08 (P4) : l'alerte SME est une alerte PROCÉDÉ, jamais
« matière » (pas de carbon nanotubes / cathode dans le texte).

Exigence manager 2026-06-10 (S2) : la limite critique fixe 0.40 kWh/kg est
SUPPRIMÉE. SME > 0.40 ne déclenche PLUS d'alerte critique automatique si rien
d'autre ne le justifie. Le seuil de vigilance (warning, 0.30) reste actif. Le
seuil critique redevient actif uniquement si SME_CRITICAL_KWH_PER_KG est
configuré (float) dans AgentIndustrial_v1/core/process.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core import process as process_mod  # noqa: E402
from AgentIndustrial_v1.core.process import (  # noqa: E402
    ProcessState,
    ScrewKPIs,
    SME_CRITICAL_KWH_PER_KG,
    SME_WARNING_KWH_PER_KG,
)
from AgentIndustrial_v1.core import rules as rules_mod  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402

_FORBIDDEN = ("carbon nanotube", "nanotube", "cnt", "cathode", "anode",
              "lifepo4", "lfp", "latp", "matière dégrad")


def _sme_alert_blob(state: ProcessState) -> str:
    """Texte des SEULES alertes SME."""
    report = evaluate(state)
    return " ".join(
        f"{a.title} {a.description} {a.evidence}"
        for a in report.alerts if a.code.startswith("SME_")
    ).lower()


def _state_with_sme(sme: float) -> ProcessState:
    state = ProcessState(screw_config=[], screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=sme)
    return state


def test_sme_critical_threshold_removed_by_default():
    """S2 — par défaut le seuil critique est désactivé (None)."""
    assert SME_CRITICAL_KWH_PER_KG is None


def test_sme_above_040_no_automatic_critical():
    """S2 — SME > 0.40 kWh/kg ne déclenche plus de critique automatique."""
    state = _state_with_sme(0.55)
    codes = {a.code for a in evaluate(state).alerts}
    assert "SME_CRITICAL" not in codes
    # Le seuil de vigilance reste actif (information, pas critique).
    assert "SME_WARNING" in codes


def test_sme_warning_still_active_above_030():
    state = _state_with_sme(SME_WARNING_KWH_PER_KG + 0.05)
    codes = {a.code for a in evaluate(state).alerts}
    assert "SME_WARNING" in codes
    assert "SME_CRITICAL" not in codes


def test_sme_warning_without_material_words():
    """P4 — l'alerte SME ne cite jamais de matière / CNT / cathode."""
    state = _state_with_sme(0.55)
    blob = _sme_alert_blob(state)
    assert blob, "une alerte SME (warning) est attendue"
    for token in _FORBIDDEN:
        assert token not in blob, f"« {token} » présent dans l'alerte SME : {blob}"


def test_sme_critical_reactivable_via_configured_threshold(monkeypatch):
    """S2 — le seuil critique redevient actif s'il est explicitement configuré."""
    monkeypatch.setattr(process_mod, "SME_CRITICAL_KWH_PER_KG", 0.80)
    monkeypatch.setattr(rules_mod, "SME_CRITICAL_KWH_PER_KG", 0.80)
    state = _state_with_sme(0.90)
    report = evaluate(state)
    crit = [a for a in report.alerts if a.code == "SME_CRITICAL"]
    assert crit, "SME_CRITICAL attendu quand un seuil configuré est dépassé"
    # Evidence traçable : valeur lue + seuil + source.
    ev = crit[0].evidence.lower()
    assert "sme=0.90" in ev and "0.80" in ev and "source" in ev


def test_sme_below_threshold_no_alert():
    state = _state_with_sme(0.10)
    codes = {a.code for a in evaluate(state).alerts}
    assert "SME_CRITICAL" not in codes
    assert "SME_WARNING" not in codes
