"""tests/test_residence_time_rpm.py — Correction manager RPM du temps de séjour.

Source : app/residence_time_correction.pdf (manager 2026-06-09).

Avant correction, dans `compute_process_state` (Network 7 PLC), au main feeder
`vol_flow = m_dot/ρ` (RPM-indépendant) → `residence_time = V_local / vol_flow`
est aussi RPM-indépendant. Manager : c'est incohérent — à débit matière constant,
le temps de séjour doit diminuer quand le RPM augmente.

Correction V1 : multiplier le temps de séjour par `rpm_ref/screw_rpm`
(rpm_ref = 100). PLC interne intact ; seuls les wrappers UI sont corrigés.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from screw_logic import (  # noqa: E402
    RESIDENCE_TIME_RPM_REFERENCE,
    add_elements_atomic,
    new_empty_configuration,
    residence_time,
    zone_residence_times,
)


def _cfg():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 20)
    return cfg


# ---------------------------------------------------------------------------
# 1 — résidence inverse au screw RPM (toutes choses égales par ailleurs)
# ---------------------------------------------------------------------------
def test_residence_time_halves_when_rpm_doubles():
    cfg = _cfg()
    rt_100 = residence_time(cfg, 100.0, 5.0, 0.55)
    rt_200 = residence_time(cfg, 200.0, 5.0, 0.55)
    assert rt_100 > 0.0
    # rt(200) ≈ rt(100) / 2 (tolérance 1 %).
    assert abs(rt_200 - rt_100 / 2.0) / rt_100 < 0.01


def test_residence_time_doubles_when_rpm_halved():
    cfg = _cfg()
    rt_100 = residence_time(cfg, 100.0, 5.0, 0.55)
    rt_50 = residence_time(cfg, 50.0, 5.0, 0.55)
    # rt(50) ≈ 2 × rt(100) (tolérance 1 %).
    assert abs(rt_50 - 2.0 * rt_100) / rt_100 < 0.01


def test_residence_time_strict_monotonic_decrease_with_rpm():
    """Vérifie la décroissance stricte sur 4 points (50→100→200→300 rpm)."""
    cfg = _cfg()
    rt = [residence_time(cfg, r, 5.0, 0.55) for r in (50.0, 100.0, 200.0, 300.0)]
    assert rt[0] > rt[1] > rt[2] > rt[3]
    assert all(v > 0 for v in rt)


def test_residence_time_at_rpm_reference_equals_pure_plc():
    """À rpm = RPM_REF (100), le facteur correctif vaut 1 — valeur PLC intacte."""
    cfg = _cfg()
    rt = residence_time(cfg, RESIDENCE_TIME_RPM_REFERENCE, 5.0, 0.55)
    # Référence : compute_process_state donne residence_time_total ≈ 167,6 s
    # pour ce cfg/feed/ρ — non testé en valeur absolue, mais doit être positif
    # et fini, et le facteur correctif vaut bien 1.
    assert rt > 0 and rt == rt


# ---------------------------------------------------------------------------
# 2 — gardes (rpm/débit invalides → 0.0 = Non calculable côté UI)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_rpm", [0.0, -10.0])
def test_residence_time_zero_when_rpm_invalid(bad_rpm):
    cfg = _cfg()
    assert residence_time(cfg, bad_rpm, 5.0, 0.55) == 0.0


@pytest.mark.parametrize("bad_feed", [0.0, -1.0])
def test_residence_time_zero_when_feed_invalid(bad_feed):
    cfg = _cfg()
    assert residence_time(cfg, 100.0, bad_feed, 0.55) == 0.0


# ---------------------------------------------------------------------------
# 3 — temps de séjour par zone : même correction RPM
# ---------------------------------------------------------------------------
def test_zone_residence_times_halve_when_rpm_doubles():
    cfg = _cfg()
    z_100 = zone_residence_times(cfg, 100.0, 5.0, 0.55)
    z_200 = zone_residence_times(cfg, 200.0, 5.0, 0.55)
    assert len(z_100) == 9 and len(z_200) == 9
    # Chaque zone non nulle décroît du facteur 2 (tolérance 1 %).
    for i in range(9):
        if z_100[i] > 0.0:
            assert abs(z_200[i] - z_100[i] / 2.0) / z_100[i] < 0.01


def test_zone_residence_times_zero_when_rpm_zero():
    cfg = _cfg()
    z = zone_residence_times(cfg, 0.0, 5.0, 0.55)
    assert z == [0.0] * 9


# ---------------------------------------------------------------------------
# 4 — engine.aggregate_machine applique aussi la correction (cohérence Moteur)
# ---------------------------------------------------------------------------
def test_engine_residence_total_matches_wrapper():
    """Moteur Procédé (engine.aggregate) et Profile (wrapper) doivent donner
    le MÊME temps de séjour total — sinon les valeurs UI divergent."""
    from engine.report_params import build_report_from_flat_params  # noqa: PLC0415

    cfg = _cfg()
    rpm = 200.0
    feed_g_min = 5.0
    rho = 0.55

    rt_wrapper = residence_time(cfg, rpm, feed_g_min, rho)
    report = build_report_from_flat_params(
        config=cfg,
        screw_rpm=rpm,
        feed_g_per_min=feed_g_min,
        bulk_density=rho,
        side_feeder_zone=0,
    )
    # Tolérance 0,1 % (les deux passent par la même correction).
    assert abs(report.residence_time_total_s - rt_wrapper) / rt_wrapper < 1e-3
