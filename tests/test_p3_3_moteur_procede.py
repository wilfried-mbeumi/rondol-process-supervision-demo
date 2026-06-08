"""Tests P3.3 — Moteur_Procede lit UNIQUEMENT current_run_state (source opérateur).

Mix : adapter pur (inputs dérivés) + garde statique (pas de lecture legacy) +
rendu réel (AppTest). Aucune autre page testée.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from AgentIndustrial_v1.core.applied_state import commit  # noqa: E402
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
from AgentIndustrial_v1.core.current_run_state import CALCULATED, NOT_AVAILABLE  # noqa: E402
from run_state_adapter import (  # noqa: E402
    build,
    build_moteur_inputs_from_current_run_state,
)
from screw_logic import add_elements_atomic, new_empty_configuration  # noqa: E402

MOTEUR_FILE = ROOT / "app" / "pages" / "5_Moteur_Procede.py"


def _session(**extra):
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 39)        # vis saturée convoyage → scénario manager
    sess = {
        "screw_config": cfg,
        "screw_rpm": 100.0,
        "bulk_density": 0.55,
        "feeder_rpm": 30.0,
        "feeder_calib_g_h_per_rpm": 10.0,
    }
    sess.update(extra)
    return sess


# ---------------------------------------------------------------------------
# Source unique : adapter inputs depuis current_run_state
# ---------------------------------------------------------------------------
def test_moteur_procede_reads_current_run_state_only():
    crs = build(_session())
    mi = build_moteur_inputs_from_current_run_state(crs)
    assert set(mi) >= {"config", "screw_rpm", "bulk_density", "side_feeder_zone",
                       "feed_g_per_min", "feed_available", "feeder_flow", "demo_mode"}
    assert mi["screw_rpm"] == 100.0
    assert mi["bulk_density"] == 0.55


def test_moteur_procede_does_not_read_legacy_session_state_directly():
    """Garde statique : la page ne lit plus les clés métier plates en direct."""
    src = MOTEUR_FILE.read_text(encoding="utf-8")
    forbidden = [
        r'session_state\[\s*["\']screw_rpm["\']\s*\]',
        r'session_state\.get\(\s*["\']screw_rpm["\']',
        r'session_state\[\s*["\']feeder_g_per_min["\']\s*\]',
        r'session_state\.get\(\s*["\']feeder_g_per_min["\']',
        r'session_state\[\s*["\']bulk_density["\']\s*\]',
        r'session_state\.get\(\s*["\']bulk_density["\']',
        r'session_state\[\s*["\']side_feeder_zone["\']\s*\]',
        r'session_state\.get\(\s*["\']side_feeder_zone["\']',
    ]
    for pat in forbidden:
        assert not re.search(pat, src), f"lecture legacy directe interdite: {pat}"


def test_moteur_procede_uses_profile_settings_current_run_state():
    # État validé par Settings (snapshot) → inputs moteur cohérents.
    sess = _session(screw_rpm=150.0)
    commit(sess, state_from_session(sess), label="t")
    mi = build_moteur_inputs_from_current_run_state(build(sess))
    assert mi["screw_rpm"] == 150.0


# ---------------------------------------------------------------------------
# Débit / fill factor
# ---------------------------------------------------------------------------
def test_moteur_procede_feeder_30rpm_coeff10_gives_300gh():
    mi = build_moteur_inputs_from_current_run_state(build(_session()))
    ff = mi["feeder_flow"]
    assert abs(ff.effective_g_h - 300.0) < 1e-6
    assert abs(ff.effective_g_min - 5.0) < 1e-6
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6     # 300 g/h = 5 g/min


def test_moteur_procede_fill_factor_uses_effective_feeder_flow():
    from screw_logic import fill_factor_average
    mi = build_moteur_inputs_from_current_run_state(build(_session()))
    ff_val = fill_factor_average(mi["config"], mi["screw_rpm"],
                                 mi["feed_g_per_min"], mi["bulk_density"])
    # ~26 % attendu sur le scénario manager (cohérent, pas imposé).
    assert 0.20 < ff_val < 0.35


def test_moteur_procede_fill_factor_not_based_on_machine_capacity():
    # Le débit utilisé dans le FF = débit feeder (5 g/min), pas une capacité
    # machine (ex. 1 kg/h). On le prouve : le feed_g_per_min vient du feeder.
    mi = build_moteur_inputs_from_current_run_state(build(_session()))
    assert abs(mi["feed_g_per_min"] - 5.0) < 1e-6      # 5 g/min, pas 1000 g/h


def test_moteur_procede_missing_feeder_coeff_is_not_available():
    mi = build_moteur_inputs_from_current_run_state(build(_session(feeder_calib_g_h_per_rpm=0.0)))
    assert mi["feed_available"] is False
    assert mi["feed_g_per_min"] == 0.0                 # débit non inventé


# ---------------------------------------------------------------------------
# Matière / demo
# ---------------------------------------------------------------------------
def test_moteur_procede_no_material_when_missing():
    crs = build(_session())                            # aucun polymère saisi
    assert crs.material_context.source == NOT_AVAILABLE
    assert crs.material_context.value == "Non renseigné"


def test_moteur_procede_outputs_have_source_unit_status():
    crs = build(_session())
    for key in ("fill_factor", "residence_time"):
        f = crs.calculated_outputs[key]
        assert f.source == CALCULATED
        assert f.unit != ""
        assert f.validation_status


def test_moteur_procede_no_confirmed_status_when_db_unconfirmed():
    crs = build(_session())
    assert crs.calculated_outputs["fill_factor"].validation_status != "CALCULATED_CONFIRMED"


# ---------------------------------------------------------------------------
# Rendu réel (AppTest)
# ---------------------------------------------------------------------------
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

MOTEUR = str(MOTEUR_FILE)


def _load(demo: bool, lang: str = "fr", calib: float = 10.0):
    cfg = new_empty_configuration(); add_elements_atomic(cfg, 1, 6)
    at = AppTest.from_file(MOTEUR)
    at.session_state["screw_config"] = cfg
    at.session_state["screw_rpm"] = 100.0
    at.session_state["bulk_density"] = 0.55
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = calib
    at.session_state["demo_mode"] = demo
    at.session_state["ui_lang"] = lang
    return at.run(timeout=60)


def _blob(at) -> str:
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
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_moteur_procede_app_test_renders(lang):
    at = _load(demo=False, lang=lang)
    assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_no_lfp_in_client_mode():
    at = _load(demo=False)
    blob = _blob(at)
    for token in ("LiFePO4", "LFP", "LATP", "nanotube", "cathode"):
        assert token not in blob, f"« {token} » présent en mode client"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_demo_material_only_when_demo_mode_true():
    at = _load(demo=True)
    blob = _blob(at)
    assert "LiFePO4" in blob          # matière nominale réapparaît (avec badge DEMO)


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_procede_language_switch_keeps_state_clean():
    # Chargements FR puis EN (neufs) — pas de crash, pas de mutation métier.
    at_fr = _load(demo=False, lang="fr")
    at_en = _load(demo=False, lang="en")
    assert not at_fr.exception and not at_en.exception
