"""Test singleton screw_logic vu depuis le package engine/ (Phase 2).

Étend l'invariant de tests/test_import_singleton.py à la nouvelle couche
`engine` : importer `engine` (qui fait son propre bootstrap sys.path) ne doit
JAMAIS créer un second objet-module `app.screw_logic`, et l'engine partage le
MÊME objet `screw_logic` que la couche machine/*.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_engine_import_shares_single_screw_logic():
    """`import engine` + machine/* + `import screw_logic` → même objet-module."""
    import engine  # noqa: F401  (déclenche le bootstrap sys.path engine/)
    from machine import element_library as el
    import screw_logic as sl

    assert sys.modules["screw_logic"] is sl
    assert el.VOLUME_CM3 is sl.VOLUME_CM3


def test_engine_no_duplicate_app_screw_logic_isolated():
    """Process neuf n'important que `engine` : pas de `app.screw_logic`."""
    code = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})
        import engine
        import screw_logic as sl

        assert "screw_logic" in sys.modules, "screw_logic absent"
        assert "app.screw_logic" not in sys.modules, (
            "app.screw_logic dupliqué : double import détecté via engine"
        )
        assert sys.modules["screw_logic"] is sl
        print("ENGINE_SINGLETON_OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"sous-process échoué\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
    )
    assert "ENGINE_SINGLETON_OK" in result.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("engine_singleton: all tests passed")
