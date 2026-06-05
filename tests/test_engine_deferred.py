"""Tests Phase 2 — engine/deferred.py.

Garantit que E4–E7 sont des STUBS NEUTRES (renvoient None, aucune valeur
fictive) et que deferred.py n'importe rien de app/ ni AgentIndustrial_v1/
(pas de pont runtime).
"""

from __future__ import annotations

import inspect
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
import screw_logic as sl  # noqa: E402
from engine.extrusion_graph import build_graph  # noqa: E402
from engine import deferred  # noqa: E402
from materials.powder import POWDERS  # noqa: E402


def _node():
    cfg = sl.new_empty_configuration()
    sl.add_elements_atomic(cfg, 4, 2)
    params = sl.ProcessParams(
        screw_rpm=120.0, feeder1_flow_rate_g_per_s=0.5, feeder1_bulk_density=1.2
    )
    g = build_graph(cfg, params, POWDERS["LFP"])
    return g.node_at(sl.MAIN_FEEDER_POSITION)


def test_all_deferred_return_none():
    n = _node()
    assert deferred.compute_local_torque(n) is None
    assert deferred.compute_local_sme(n) is None
    assert deferred.compute_local_sme(n, throughput_kg_per_h=1.0) is None
    assert deferred.compute_die_pressure(n) is None
    assert deferred.compute_t_real(n) is None
    assert deferred.compute_t_real(n, screw_rpm=120.0) is None
    assert deferred.compute_t_real(
        n, screw_rpm=120.0, torque_nm=2.0, mass_flow_kg_per_h=1.0
    ) is None


def test_deferred_manifest():
    """Numérotation canonique E4, E5, E6, E7 dans l'ordre."""
    assert deferred.DEFERRED_EQUATIONS == (
        "E4_torque", "E5_sme", "E6_t_real", "E7_pressure",
    )


def test_numbering_alignment():
    """D5 — E6 = T_real, E7 = pression (anti-régression de numérotation)."""
    assert deferred.E4_TORQUE == "E4_torque"
    assert deferred.E5_SME == "E5_sme"
    assert deferred.E6_T_REAL == "E6_t_real"
    assert deferred.E7_PRESSURE == "E7_pressure"
    # L'ordre du manifeste est strictement E4→E5→E6→E7.
    assert deferred.DEFERRED_EQUATIONS == (
        deferred.E4_TORQUE, deferred.E5_SME, deferred.E6_T_REAL, deferred.E7_PRESSURE,
    )
    # Anciennes constantes mal numérotées supprimées (pas de rechute).
    assert not hasattr(deferred, "E6_PRESSURE")
    assert not hasattr(deferred, "E7_T_REAL")


def test_compute_t_real_accepts_rpm_but_returns_none():
    """D4 — compute_t_real expose screw_rpm mais reste un stub None."""
    n = _node()
    params = inspect.signature(deferred.compute_t_real).parameters
    assert "screw_rpm" in params  # accès rpm préparé pour E6/T_real
    # screw_rpm placé juste après node (avant torque/mass_flow).
    order = list(params)
    assert order[:2] == ["node", "screw_rpm"]
    assert deferred.compute_t_real(n, screw_rpm=150.0) is None


def test_die_pressure_is_e7_and_none():
    """compute_die_pressure reste E7 (docstring) et renvoie None."""
    n = _node()
    assert deferred.compute_die_pressure(n) is None
    assert deferred.compute_die_pressure(n, die=None) is None
    assert "E7" in (deferred.compute_die_pressure.__doc__ or "")


def test_no_runtime_bridge_imports():
    """deferred.py n'IMPORTE ni app/ ni AgentIndustrial_v1/ (pas de pont runtime).

    On inspecte les lignes d'`import` réelles (pas les docstrings, qui citent
    légitimement cooling.py comme garde « ne pas importer »).
    """
    src = inspect.getsource(deferred)
    import_lines = [
        ln.strip() for ln in src.splitlines()
        if ln.strip().startswith(("import ", "from "))
    ]
    for ln in import_lines:
        assert "AgentIndustrial" not in ln, ln
        assert "cooling" not in ln, ln
        assert not ln.startswith("from app"), ln


def test_import_deferred_does_not_load_cooling():
    """Importer `engine.deferred` ne charge PAS cooling/AgentIndustrial à lui seul.

    Vérifié dans un interpréteur FRAIS (sous-processus) : robuste à l'ordre
    d'exécution pytest. Un autre test (test_streamlit_pages) qui charge les
    pages Supervision/Settings laisse cooling dans le `sys.modules` global ;
    on isole donc l'effet du seul import d'`engine.deferred`.
    """
    code = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})
        import engine.deferred  # noqa: F401
        loaded = [m for m in sys.modules
                  if "AgentIndustrial" in m or m.endswith(".cooling")]
        assert not loaded, loaded
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "import engine.deferred a chargé un module runtime "
        f"(cooling/AgentIndustrial):\n{result.stdout}\n{result.stderr}"
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("engine_deferred: all tests passed")
