"""tests/test_n_die_zones_zero.py — Option « 0 zone filière » (manager 2026-06-09).

Vérifie que n_die_zones=0 (filière absente) :
  - est accepté par la couche d'état (domaine [0,4]) ;
  - donne une liste de clés die VIDE (active_die_keys) ;
  - ne fait PAS crasher l'évaluation des règles (pas de division par zéro
    sur die_temps_C vide) ;
  - NE supprime PAS les règles NON-die — en particulier la règle critique
    de compatibilité matière `ZONE_MATERIAL_INCOMPAT` doit continuer à
    s'émettre quand une matière transite par une zone trop chaude
    (régression silencieuse détectée à la revue finale).
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
    active_die_keys,
)
from AgentIndustrial_v1.core.feeders import FeederSpec  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402


# ---------------------------------------------------------------------------
# active_die_keys : 0 → liste vide, 1..4 → 1..4 clés, borné
# ---------------------------------------------------------------------------
def test_active_die_keys_zero_returns_empty():
    assert active_die_keys(0) == []


def test_active_die_keys_one_to_four():
    assert active_die_keys(1) == ["die"]
    assert active_die_keys(2) == ["die", "die2"]
    assert active_die_keys(4) == ["die", "die2", "die3", "die4"]


def test_active_die_keys_clamped():
    assert active_die_keys(-3) == []     # borné bas à 0
    assert active_die_keys(9) == ["die", "die2", "die3", "die4"]  # borné haut


# ---------------------------------------------------------------------------
# die_temps_C vide quand 0 zone, et evaluate() ne crashe pas
# ---------------------------------------------------------------------------
def test_die_temps_empty_when_zero_zones():
    st = ProcessState(screw_rpm=120.0)
    st.n_die_zones = 0
    assert st.die_temps_C == []


def test_evaluate_does_not_crash_with_zero_die_zones():
    st = ProcessState(screw_rpm=120.0)
    st.n_die_zones = 0
    report = evaluate(st)               # ne doit PAS lever (div par zéro die)
    assert report is not None
    assert isinstance(report.alerts, list)
    # Aucune alerte spécifiquement die ne doit apparaître (pas de filière).
    die_codes = {"DIE_TOO_COLD", "DIE_PROFILE_INCOHERENT"}
    assert not any(a.code in die_codes for a in report.alerts)


# ---------------------------------------------------------------------------
# RÉGRESSION CRITIQUE : la règle matière NON-die doit survivre à 0 zone filière
# ---------------------------------------------------------------------------
def _hot_profile_state(n_die: int) -> ProcessState:
    """État avec un feeder matière fragile injecté en Z0 + profil très chaud,
    de sorte que ZONE_MATERIAL_INCOMPAT DOIT se déclencher (indépendamment
    de la filière)."""
    # PVDF : borne dégradation typiquement < 280 °C ; on force un T_dég bas
    # et un profil zone bien au-dessus pour garantir l'incompatibilité.
    feeder = FeederSpec(
        feeder_id=1, enabled=True, material_id="powder", position="Z0",
        mass_flow_g_per_min=30.0, density_g_per_cm3=0.55,
        polymer_name="PVDF", t_degradation_C=150.0,
    )
    st = ProcessState(screw_rpm=120.0, feeders=[feeder])
    st.n_die_zones = n_die
    # Profil thermique nettement au-dessus de la borne matière (150 °C).
    for z in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"):
        st.zone_temps_C[z] = 250.0
    for d in ("die", "die2", "die3", "die4"):
        st.zone_temps_C[d] = 200.0
    return st


def test_material_incompat_alert_fires_with_one_die_zone():
    """Référence : avec filière (1 zone), l'alerte matière doit exister."""
    st = _hot_profile_state(n_die=1)
    report = evaluate(st)
    assert any(a.code == "ZONE_MATERIAL_INCOMPAT" for a in report.alerts), \
        [a.code for a in report.alerts]


def test_material_incompat_alert_still_fires_with_zero_die_zones():
    """RÉGRESSION : sans filière (0 zone), l'alerte matière NON-die doit
    TOUJOURS s'émettre — elle ne dépend pas de la présence d'une filière.

    (Avant correction, un `return out` anticipé sur die_temps_C vide la
    supprimait silencieusement.)"""
    st = _hot_profile_state(n_die=0)
    report = evaluate(st)
    assert any(a.code == "ZONE_MATERIAL_INCOMPAT" for a in report.alerts), \
        [a.code for a in report.alerts]
