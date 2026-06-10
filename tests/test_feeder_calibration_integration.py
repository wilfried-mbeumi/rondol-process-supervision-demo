"""Tests Phase B/C — étalonnage feeder câblé dans la chaîne + audit + défaut 40.

Couvre :
  - fill factor / résidence utilisent le débit EFFECTIF étalonné ;
  - pas de débit réel sans étalonnage ;
  - défaut nombre d'éléments = 40, choix 25/30/40 conservé ;
  - panneau audit + pages se rendent sans exception (AppTest).
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

from physics.feeder_flow import resolve_feeder_flow  # noqa: E402
from feeder_ui import current_feeder_flow, feeder_audit_rows  # noqa: E402
from screw_logic import (  # noqa: E402
    fill_factor_average,
    residence_time,
    new_empty_configuration,
    add_elements_atomic,
)

RHO = 0.55


def _cfg():
    c = new_empty_configuration()
    add_elements_atomic(c, 1, 39)
    return c


# ---------------------------------------------------------------------------
# Débit effectif étalonné utilisé dans fill factor / résidence
# ---------------------------------------------------------------------------
def test_effective_flow_used_in_fill_factor():
    cfg = _cfg()
    ff = resolve_feeder_flow(30.0, 10.0)        # 300 g/h = 5 g/min
    fill_calib = fill_factor_average(cfg, 100.0, ff.effective_g_min, RHO)
    fill_direct = fill_factor_average(cfg, 100.0, 5.0, RHO)
    assert abs(fill_calib - fill_direct) < 1e-9   # 5 g/min des deux côtés


def test_effective_flow_used_in_residence_time():
    cfg = _cfg()
    ff = resolve_feeder_flow(30.0, 10.0)
    rt = residence_time(cfg, 100.0, ff.effective_g_min, RHO)
    assert rt > 0.0


def test_clamped_flow_used_above_machine_max():
    from physics.feeder_flow import MAX_FEEDER_FLOW_G_H
    cfg = _cfg()
    # 300 RPM × 10 = 3000 g/h demandé > 2500 g/h → effectif plafonné à
    # MAX_FEEDER_FLOW_G_H (manager 2026-06-09).
    ff = resolve_feeder_flow(300.0, 10.0)
    assert ff.clamped is True
    fill_effective = fill_factor_average(cfg, 100.0, ff.effective_g_min, RHO)
    fill_at_max = fill_factor_average(cfg, 100.0, MAX_FEEDER_FLOW_G_H / 60.0, RHO)
    assert abs(fill_effective - fill_at_max) < 1e-9  # calcul borné


def test_manager_scenario_300gh_100rpm_40elements():
    """Scénario manager complet : 300 g/h (30 RPM × 10), vis 100 rpm, ρ=0.55.

    Vérifie la chaîne entrée→sortie + provenance, sans imposer un FF « joli ».
    """
    ff = resolve_feeder_flow(30.0, 10.0)
    # Débit : 300 g/h = 5 g/min = 0.0833 g/s.
    assert abs(ff.effective_g_h - 300.0) < 1e-6
    assert abs(ff.effective_g_min - 5.0) < 1e-6
    assert abs(ff.effective_g_s - 0.083333) < 1e-5

    # Q_vol = débit / densité (cm³/s).
    rho = 0.55
    qvol = ff.effective_g_s / rho
    assert abs(qvol - 0.1515) < 1e-3

    # FF & résidence cohérents (finis, positifs, FF ∈ [0,1]).
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 39)  # vis pleine (max user = 39 ; cible 40)
    fillv = fill_factor_average(cfg, 100.0, ff.effective_g_min, rho)
    rt = residence_time(cfg, 100.0, ff.effective_g_min, rho)
    assert 0.0 < fillv <= 1.0
    assert rt > 0.0 and rt == rt  # fini, positif
    # Toute sortie a une provenance (audit feeder).
    rows = feeder_audit_rows(ff, rho)
    assert all(r.get("provenance") for r in rows)


def test_residence_time_is_finite_and_positive():
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 39)
    ff = resolve_feeder_flow(30.0, 10.0)
    rt = residence_time(cfg, 100.0, ff.effective_g_min, 0.55)
    import math
    assert math.isfinite(rt) and rt > 0.0


def test_no_real_mass_flow_without_calibration_in_session():
    ff = current_feeder_flow({"feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 0.0})
    assert ff.calibrated is False
    rows = feeder_audit_rows(ff, RHO)
    blob = " ".join(r["valeur"] for r in rows)
    assert "Not computable" in blob


def test_audit_rows_show_calibrated_breakdown():
    ff = current_feeder_flow({"feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": 10.0})
    rows = feeder_audit_rows(ff, RHO)
    blob = " ".join(f"{r['grandeur']} {r['valeur']}" for r in rows)
    assert "300.0 g/h" in blob       # débit demandé
    assert "5.000 g/min" in blob     # converti
    assert "CALCULATED" in " ".join(r["provenance"] for r in rows)


# ---------------------------------------------------------------------------
# AppTest : pages rendues sans exception + défaut 40
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

PROFILE = str(ROOT / "app" / "pages" / "1_Profile.py")
SETTINGS = str(ROOT / "app" / "pages" / "2_Settings.py")
MP = str(ROOT / "app" / "pages" / "5_Moteur_Procede.py")


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_default_element_count_is_40():
    at = AppTest.from_file(SETTINGS).run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.session_state["target_screw_count"] == 40


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_user_can_still_select_25_30_40_elements():
    # Choix piloté par le widget radio (clé rd_target_count) — AppTest neuf par
    # choix pour éviter les artefacts de re-run de Streamlit.
    for choice in (25, 30, 40):
        at = AppTest.from_file(SETTINGS)
        at.session_state["rd_target_count"] = choice
        at.run(timeout=60)
        assert not at.exception, [str(e.value) for e in at.exception]
        assert at.session_state["target_screw_count"] == choice


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_renders_with_calibration_block():
    at = AppTest.from_file(PROFILE)
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    # Étalonné → feeder_g_per_min = 5 g/min (300 g/h).
    assert abs(at.session_state["feeder_g_per_min"] - 5.0) < 1e-6


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_displays_calculation_audit():
    from screw_logic import new_empty_configuration, add_elements_atomic
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 6)
    at = AppTest.from_file(MP)
    at.session_state["screw_config"] = cfg
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 10.0
    at.run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = "\n".join(str(getattr(e, "value", "")) for e in at.markdown)
    for kind in ("info", "warning", "caption"):
        try:
            blob += "\n".join(str(getattr(e, "value", "")) for e in getattr(at, kind))
        except Exception:
            pass
    blob += "\n".join(str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html"))
    # En-tête panneau (st.html), explication chiffrée (st.info), provenance PLC (st.caption).
    assert "Process calculation audit" in blob
    assert "Network 7" in blob
