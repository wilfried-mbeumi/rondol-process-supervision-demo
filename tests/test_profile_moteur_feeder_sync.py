"""Test de non-régression — synchro Profile → Moteur_Procede de l'étalonnage feeder.

Reproduit le bug prod : RPM 30 + coeff 10 saisis sur /Profile n'étaient pas lus
par /Moteur_Procede (clés widget purgées en navigation multipage). On vérifie
la persistance via le miroir nav-safe, au niveau pur ET en AppTest réel.
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

from feeder_ui import (  # noqa: E402
    FEEDER_CALIB_KEY, FEEDER_RPM_KEY, calib_read, mirror_calibration_to_persistent,
)
from run_state_adapter import build, build_moteur_inputs_from_current_run_state  # noqa: E402
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402


def _cfg():
    c = new_empty_configuration(); add_elements_atomic(c, 1, 39); return c


# ---------------------------------------------------------------------------
# Pur : le miroir persistant survit à la disparition des clés widget
# ---------------------------------------------------------------------------
def test_calibration_persists_when_widget_keys_dropped():
    sess = {"screw_config": _cfg(), "screw_rpm": 100.0, "bulk_density": 0.55,
            FEEDER_RPM_KEY: 30.0, FEEDER_CALIB_KEY: 10.0}
    # Profile : miroir des clés widget vers persistant.
    mirror_calibration_to_persistent(sess, [1])
    # Navigation : Streamlit purge les clés WIDGET non montées.
    del sess[FEEDER_RPM_KEY]
    del sess[FEEDER_CALIB_KEY]
    # Lecture nav-safe : retombe sur le miroir persistant.
    assert calib_read(sess, FEEDER_RPM_KEY, 0.0) == 30.0
    assert calib_read(sess, FEEDER_CALIB_KEY, 0.0) == 10.0


def test_moteur_reads_calibration_after_widget_keys_dropped():
    sess = {"screw_config": _cfg(), "screw_rpm": 100.0, "bulk_density": 0.55,
            FEEDER_RPM_KEY: 30.0, FEEDER_CALIB_KEY: 10.0}
    mirror_calibration_to_persistent(sess, [1])
    del sess[FEEDER_RPM_KEY]; del sess[FEEDER_CALIB_KEY]   # navigation
    mi = build_moteur_inputs_from_current_run_state(build(sess))
    assert mi["feed_available"] is True
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6          # 300 g/h
    line1 = next(l for l in mi["multi_feeder"].lines if l.feeder_id == 1)
    assert line1.status == "OK"
    assert abs(line1.flow_g_h - 300.0) < 1e-6


def test_uncalibrated_still_not_calculable_after_navigation():
    sess = {"screw_config": _cfg(), FEEDER_RPM_KEY: 30.0, FEEDER_CALIB_KEY: 0.0}
    mirror_calibration_to_persistent(sess, [1])
    del sess[FEEDER_RPM_KEY]; del sess[FEEDER_CALIB_KEY]
    mi = build_moteur_inputs_from_current_run_state(build(sess))
    assert mi["feed_available"] is False
    assert mi["feed_g_per_min"] == 0.0


# ---------------------------------------------------------------------------
# AppTest réel : Profile (sidebar) saisit, Moteur (run séparé, mêmes clés
# persistantes) lit 300 g/h et n'affiche plus « Non renseigné ».
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

PROFILE = str(APP / "pages" / "1_Profile.py")
MOTEUR = str(APP / "pages" / "5_Process_Engine.py")
SETTINGS = str(APP / "pages" / "2_Settings.py")


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_to_moteur_feeder_sync_end_to_end():
    # Phase S1 stabilisation 2026-06-09 : l'étalonnage feeder n'est plus saisi
    # dans Profile (lecture seule). La source d'édition est Settings — qui
    # crée le miroir persistant via `mirror_calibration_to_persistent`
    # appelé par `render_multi_feeder_calibration`.
    # 1) Settings : saisie RPM 30 + coeff 10 → persiste le miroir.
    at = AppTest.from_file(SETTINGS)
    at.session_state[FEEDER_RPM_KEY] = 30.0
    at.session_state[FEEDER_CALIB_KEY] = 10.0
    at.session_state["fd_en_1"] = True
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    ss = at.session_state
    # Le miroir persistant doit exister (créé par Settings désormais).
    assert ss[FEEDER_RPM_KEY + "__persist"] == 30.0
    assert ss[FEEDER_CALIB_KEY + "__persist"] == 10.0

    # 2) Navigation simulée vers Moteur : on transporte l'état de session SANS
    #    les clés widget (purgées par Streamlit), seul le miroir survit.
    cfg = _cfg()
    at2 = AppTest.from_file(MOTEUR)
    at2.session_state["screw_config"] = cfg
    at2.session_state[FEEDER_RPM_KEY + "__persist"] = 30.0
    at2.session_state[FEEDER_CALIB_KEY + "__persist"] = 10.0
    at2.session_state["demo_mode"] = False
    at2.run(timeout=90)
    assert not at2.exception, [str(e.value) for e in at2.exception]

    blob = "\n".join(
        [str(getattr(e, "value", "")) for e in at2.metric]
        + [str(getattr(e, "body", getattr(e, "value", ""))) for e in at2.get("html")]
    )
    # Le débit redevient calculable : plus de « Non calculable » massif ; le chip
    # feeder n'est plus « Non renseigné » côté débit (matière reste Non renseigné).
    metric_vals = [str(getattr(e, "value", "")) for e in at2.metric]
    assert "Non calculable" not in metric_vals     # KPIs flux redeviennent calculables
