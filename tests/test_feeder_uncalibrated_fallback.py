"""Tests — repli feeder non étalonné : « Non calculable » au lieu d'un 0 trompeur.

Sans coefficient d'étalonnage feeder, débit / fill factor / résidence ne sont
PAS présentés comme une vérité procédé (pas de 0 affiché comme réel), et un
avertissement clair apparaît. Le cas étalonné reste inchangé.
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

from run_state_adapter import build, build_moteur_inputs_from_current_run_state  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402

MOTEUR = str(APP / "pages" / "5_Process_Engine.py")
SUP = str(APP / "Supervision.py")


def _cfg():
    c = new_empty_configuration()
    add_elements_atomic(c, 1, 39)
    return c


def _session(calib):
    return {
        "screw_config": _cfg(), "screw_rpm": 100.0, "bulk_density": 0.55,
        "feeder_rpm": 30.0, "feeder_calib_g_h_per_rpm": calib,
    }


# ---------------------------------------------------------------------------
# Couche adapter : débit non disponible sans étalonnage, OK avec étalonnage
# ---------------------------------------------------------------------------
def test_calibrated_feeder_still_computes_300_g_h():
    mi = build_moteur_inputs_from_current_run_state(build(_session(10.0)))
    assert mi["feed_available"] is True
    assert abs(mi["feeder_flow"].effective_g_h - 300.0) < 1e-6
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6


@pytest.mark.parametrize("calib", [0.0, None])
def test_feed_not_available_without_calibration(calib):
    mi = build_moteur_inputs_from_current_run_state(build(_session(calib)))
    assert mi["feed_available"] is False
    assert mi["feed_g_per_min"] == 0.0     # pas de débit inventé


# ---------------------------------------------------------------------------
# Rendu réel (AppTest)
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False


def _load(path, calib):
    at = AppTest.from_file(path)
    at.session_state["screw_config"] = _cfg()
    at.session_state["screw_rpm"] = 100.0
    at.session_state["bulk_density"] = 0.55
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = calib
    at.session_state["demo_mode"] = False
    return at.run(timeout=90)


def _metric_values(at):
    try:
        return [str(getattr(m, "value", "")) for m in at.metric]
    except Exception:
        return []


def _blob(at):
    chunks = []
    for kind in ("markdown", "caption", "info", "warning"):
        try:
            chunks += [str(getattr(e, "value", "")) for e in getattr(at, kind)]
        except Exception:
            pass
    try:
        chunks += [str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html")]
    except Exception:
        pass
    return "\n".join(chunks)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_no_zero_presented_as_real_flow_when_feeder_uncalibrated():
    at = _load(MOTEUR, 0.0)
    assert not at.exception, [str(e.value) for e in at.exception]
    vals = _metric_values(at)
    # Le débit massique ne doit PAS afficher « 0.00 kg/h » comme réel.
    assert "0.00 kg/h" not in vals
    assert "Not computable" in vals


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_ff_not_calculable_when_feeder_uncalibrated():
    at = _load(MOTEUR, 0.0)
    vals = _metric_values(at)
    assert "0 %" not in vals                  # pas de remplissage 0 % présenté comme réel
    assert "Not computable" in vals


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_residence_not_calculable_when_flow_missing():
    at = _load(MOTEUR, 0.0)
    vals = _metric_values(at)
    assert "0.0 s" not in vals


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_warning_displayed_when_feeder_calibration_missing():
    at = _load(MOTEUR, 0.0)
    blob = _blob(at)
    assert "feeder calibration coefficient" in blob.lower()


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_uncalibrated_feeder_does_not_show_real_zero():
    at = _load(MOTEUR, 0.0)
    vals = _metric_values(at)
    for bad in ("0.000 N·m", "0.000 kWh/kg", "0.0 s", "0 %", "0.00 kg/h"):
        assert bad not in vals, f"valeur 0 présentée comme réelle : {bad}"
    # …et le cas étalonné montre bien des valeurs calculées.
    at_ok = _load(MOTEUR, 10.0)
    assert "Not computable" not in _metric_values(at_ok)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_uncalibrated_feeder_does_not_show_real_zero():
    at = _load(SUP, 0.0)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = _blob(at)
    assert "feeder calibration coefficient" in blob.lower()
