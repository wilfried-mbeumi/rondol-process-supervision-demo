"""tests/test_agent_feeder_overflow.py

Non-régression F1 (audit 2026-08-16) : l'agent IA ignorait le débordement du
feeder principal.

Cause racine : le backbone Network 7 calcule bien `overflow_main_feeder`
(FF local ≥ 1.0 au point d'injection), mais `screw_adapter.refresh_kpis`
n'appelait que `fill_factor_average()` — qui ne renvoie QUE le FF moyen. Or le
FF moyen sature bien en deçà de 1.0 (≈ 0,44) : une vis gavée à la trémie
restait donc invisible pour l'agent, et la page Supervision affichait
« STABLE 100/100 » sans aucune alerte, dès 30 g/min (valeur par défaut du
feeder).

Correctif : `ScrewKPIs` porte désormais `overflow_main_feeder` /
`overflow_side_feeder`, peuplés par `refresh_kpis` depuis le backbone, et la
règle `_rule_overflow` émet une alerte CRITICAL quand le flag est vrai.

Ce test verrouille : (1) le flag remonte, (2) l'alerte se déclenche au-delà du
seuil, (3) la démo C1 (20 g/min) reste indemne — pas de faux positif.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from AgentIndustrial_v1.core import screw_adapter as SA  # noqa: E402
from AgentIndustrial_v1.core.process import (  # noqa: E402
    FeederSpec,
    ProcessState,
)
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402

# Profil peuplé réaliste (convoyage + malaxage + convoyage), tip conservé.
_PATTERN = [
    1, 101, 1, 101, 1, 101, 1, 101, 4, 101, 4, 101, 1, 101, 1, 101,
    7, 101, 7, 101, 1, 101, 1, 101, 1, 101, 4, 101, 1, 101, 1, 101,
    1, 101, 1, 101,
]


def _state(flow_g_per_min: float) -> ProcessState:
    cfg = SA.new_empty_configuration()
    for i, v in enumerate(_PATTERN):
        if i < len(cfg) - 1:
            cfg[i] = v
    st = ProcessState(
        screw_config=cfg,
        screw_rpm=150.0,
        zone_temps_C={
            "Z1": 60, "Z2": 90, "Z3": 120, "Z4": 150,
            "Z5": 160, "Z6": 160, "Z7": 150, "Z8": 140, "die": 145,
        },
        feeders=[FeederSpec(
            feeder_id=1, enabled=True, label="LFP", position="Z0",
            speed_rpm=120.0, mass_flow_g_per_min=flow_g_per_min,
            density_g_per_cm3=0.55,
        )],
    )
    SA.refresh_kpis(st)
    return st


def _has_overflow_alert(report) -> bool:
    return any(a.code.startswith("FEEDER_OVERFLOW") for a in report.alerts)


def test_overflow_flag_populated_when_flooded():
    """Le flag backbone remonte jusqu'aux KPIs de l'agent quand la vis est gavée."""
    st = _state(160.0)
    assert st.kpis.overflow_main_feeder is True


def test_overflow_flag_false_at_nominal_feed():
    """Cas de référence C1 (20 g/min = 1,2 kg/h) : pas de débordement."""
    st = _state(20.0)
    assert st.kpis.overflow_main_feeder is False


def test_agent_emits_critical_overflow_alert_when_flooded():
    """Une vis gavée déclenche une alerte CRITICAL — plus jamais STABLE muet."""
    st = _state(160.0)
    report = evaluate(st)
    assert _has_overflow_alert(report), (
        "Le débordement feeder doit produire une alerte FEEDER_OVERFLOW_*"
    )
    overflow = next(
        a for a in report.alerts if a.code.startswith("FEEDER_OVERFLOW")
    )
    assert overflow.severity == "critical"
    # Régression du bug : l'état ne doit JAMAIS rester STABLE quand ça déborde.
    assert report.state != "STABLE"


def test_no_false_overflow_alert_at_nominal_feed():
    """La démo C1 ne doit pas régresser en faux positif."""
    st = _state(20.0)
    report = evaluate(st)
    assert not _has_overflow_alert(report)


def test_overflow_alert_is_bilingual():
    """Titre/preuve doivent exister en FR et EN (exigence i18n du projet)."""
    st = _state(160.0)
    fr = evaluate(st, lang="fr")
    en = evaluate(st, lang="en")
    a_fr = next(a for a in fr.alerts if a.code == "FEEDER_OVERFLOW_MAIN")
    a_en = next(a for a in en.alerts if a.code == "FEEDER_OVERFLOW_MAIN")
    assert a_fr.title != a_en.title
    assert "principal" in a_fr.title.lower()
    assert "main" in a_en.title.lower()
