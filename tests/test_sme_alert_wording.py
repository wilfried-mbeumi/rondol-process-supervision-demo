"""Tests P4 — l'alerte seuil 0.40 est une alerte SME procédé, jamais « matière ».

Exigence manager : le manager a cru que le seuil 0.40 concernait des carbon
nanotubes / une matière. Le texte ne doit RIEN laisser croire de tel. Le seuil
0.40 reste un seuil SME procédé.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core.process import (  # noqa: E402
    ProcessState,
    ScrewKPIs,
    SME_CRITICAL_KWH_PER_KG,
)
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402

_FORBIDDEN = ("carbon nanotube", "nanotube", "cnt", "cathode", "anode",
              "lifepo4", "lfp", "latp", "matière dégrad")


def _sme_alert_blob(state: ProcessState) -> str:
    """Texte des SEULES alertes SME (le sujet du seuil 0.40)."""
    report = evaluate(state)
    return " ".join(
        f"{a.title} {a.description} {a.evidence}"
        for a in report.alerts if a.code.startswith("SME_")
    ).lower()


def test_sme_critical_above_threshold_triggers_without_material_words():
    # Aucune matière saisie ; SME au-delà de 0.40 → l'alerte SME doit exister…
    state = ProcessState(screw_config=[], screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=SME_CRITICAL_KWH_PER_KG + 0.10)
    report = evaluate(state)
    codes = {a.code for a in report.alerts}
    assert "SME_CRITICAL" in codes
    # …mais l'alerte SME elle-même ne doit citer AUCUNE matière / CNT / cathode.
    blob = _sme_alert_blob(state)
    for token in _FORBIDDEN:
        assert token not in blob, f"« {token} » présent dans l'alerte SME : {blob}"


def test_sme_alert_mentions_process_threshold():
    state = ProcessState(screw_config=[], screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=SME_CRITICAL_KWH_PER_KG + 0.10)
    blob = _sme_alert_blob(state)
    assert "seuil procédé" in blob and "énergie mécanique spécifique" in blob


def test_sme_below_threshold_no_critical():
    state = ProcessState(screw_config=[], screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=0.10)  # sous tous les seuils
    codes = {a.code for a in evaluate(state).alerts}
    assert "SME_CRITICAL" not in codes
    assert "SME_WARNING" not in codes
