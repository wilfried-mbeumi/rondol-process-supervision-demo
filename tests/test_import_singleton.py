"""Test singleton screw_logic (Phase 1.5 — correctif double import BLOQUANT).

Garantit qu'il n'existe qu'UN SEUL objet-module `screw_logic` partagé par la
couche engine (machine/*) et le runtime, et qu'aucun second objet-module
`app.screw_logic` n'est créé côté engine.

Deux niveaux de vérification :
  1. Intra-process : les constantes/dataclasses référencées par machine/* sont
     le MÊME objet (identité `is`) que celles de `import screw_logic`.
  2. Sous-process isolé : dans un interpréteur neuf n'important que l'engine,
     `app.screw_logic` n'apparaît jamais dans sys.modules (robuste, indépendant
     de l'ordre d'exécution des autres tests de la suite).
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_engine_shares_single_screw_logic_object():
    """machine/* et `import screw_logic` pointent le MÊME objet-module."""
    from machine import element_library as el  # bootstrap sys.path
    from machine import port_map as pm
    import screw_logic as sl

    # Identité d'objets (pas juste égalité de valeurs) → preuve d'un module unique.
    assert el.VOLUME_CM3 is sl.VOLUME_CM3
    assert el.FACTOR_FREE_BY_REV is sl.FACTOR_FREE_BY_REV
    assert el.ELEMENT_TYPES is sl.ELEMENT_TYPES
    assert pm.SIDE_FEEDER_START_ELMT_Z is sl.SIDE_FEEDER_START_ELMT_Z
    # La fonction déléguée est littéralement celle de screw_logic.
    assert pm.side_feeder_position is sl.side_feeder_position


def test_no_duplicate_app_screw_logic_in_isolated_process():
    """Dans un process neuf, l'engine ne crée jamais `app.screw_logic`."""
    code = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})
        from machine import element_library as el
        from machine import port_map as pm
        import screw_logic as sl

        # Un seul objet-module canonique.
        assert "screw_logic" in sys.modules, "screw_logic absent"
        assert "app.screw_logic" not in sys.modules, (
            "app.screw_logic dupliqué : double import détecté"
        )
        assert sys.modules["screw_logic"] is sl
        assert el.VOLUME_CM3 is sl.VOLUME_CM3
        print("SINGLETON_OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"sous-process échoué\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
    )
    assert "SINGLETON_OK" in result.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("import_singleton: all tests passed")
