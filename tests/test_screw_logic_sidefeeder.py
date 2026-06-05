"""
Tests Étape 3 — Side Feeder (positions structurées).

Exécution directe : python tests/test_screw_logic_sidefeeder.py

Vérifie :
- tableau SideFeeder_StartElmtZ conforme spec ([4, 12, 21, 30, 39, 48, 57, 66])
- zone 0 → sentinelle 81 (désactivé)
- zones 1..8 → positions correctes
- collision avec 2ème partie (>100) → recul de 1
- invariants : aucune modif volume / ADD / config après appel
- stabilité : même résultat après ajout / reset

Les tests des Étapes 1 (volume) et 2 (user) ne sont PAS dupliqués ici.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.screw_logic import (  # noqa: E402
    MAX_USER_ELEMENTS,
    PART2_OFFSET,
    SIDE_FEEDER_DISABLED_POSITION,
    SIDE_FEEDER_DISABLED_ZONE,
    SIDE_FEEDER_MAX_ZONE,
    SIDE_FEEDER_START_ELMT_Z,
    add_elements_atomic,
    count_user_elements,
    free_volume,
    new_empty_configuration,
    place_element_at,
    reset_configuration,
    side_feeder_position,
    total_volume_used,
)

TOL = 1e-5


def approx(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# S1 — Constantes conformes à la spec
# ---------------------------------------------------------------------------
def test_S1_constants():
    assert SIDE_FEEDER_START_ELMT_Z == [4, 12, 21, 30, 39, 48, 57, 66]
    assert len(SIDE_FEEDER_START_ELMT_Z) == 8
    assert SIDE_FEEDER_DISABLED_POSITION == 81
    assert SIDE_FEEDER_DISABLED_ZONE == 0
    assert SIDE_FEEDER_MAX_ZONE == 8


# ---------------------------------------------------------------------------
# S2 — zone 0 → désactivé (sentinelle 81)
# ---------------------------------------------------------------------------
def test_S2_zone_zero_disabled():
    cfg = new_empty_configuration()
    assert side_feeder_position(cfg, 0) == SIDE_FEEDER_DISABLED_POSITION
    # Sentinelle indépendante de la config
    add_elements_atomic(cfg, 1, 10)
    assert side_feeder_position(cfg, 0) == SIDE_FEEDER_DISABLED_POSITION


# ---------------------------------------------------------------------------
# S3 — zones valides sur config vide → positions nominales
# ---------------------------------------------------------------------------
def test_S3_valid_zones_empty_config():
    cfg = new_empty_configuration()
    expected = [4, 12, 21, 30, 39, 48, 57, 66]
    for zone, pos in enumerate(expected, start=1):
        assert side_feeder_position(cfg, zone) == pos, (
            f"zone {zone} : attendu {pos}, obtenu {side_feeder_position(cfg, zone)}"
        )


# ---------------------------------------------------------------------------
# S4 — Collision avec 2ème partie → recule de 1
# ---------------------------------------------------------------------------
def test_S4_collision_with_part2():
    cfg = new_empty_configuration()
    # Place un élément entier type 1 aux positions [11, 12].
    # 12 devient 2ème partie (101). La zone 2 (candidate = 12) doit reculer à 11.
    assert place_element_at(cfg, 11, 1)
    assert cfg[12] == 1 + PART2_OFFSET
    assert side_feeder_position(cfg, 2) == 11

    # Même test en zone 3 (candidate = 21) : place à [20, 21]
    cfg = new_empty_configuration()
    assert place_element_at(cfg, 20, 1)
    assert cfg[21] == 1 + PART2_OFFSET
    assert side_feeder_position(cfg, 3) == 20


# ---------------------------------------------------------------------------
# S5 — Pas de collision si 1ère partie ou vide → position inchangée
# ---------------------------------------------------------------------------
def test_S5_no_collision_keeps_position():
    cfg = new_empty_configuration()
    # Zone 2 sur config vide
    assert side_feeder_position(cfg, 2) == 12
    # Placer un entier à [12, 13] (1ère partie = 12) ne doit pas faire reculer
    assert place_element_at(cfg, 12, 1)
    assert cfg[12] == 1 and cfg[13] == 1 + PART2_OFFSET
    assert side_feeder_position(cfg, 2) == 12
    # Zone 3 (candidate = 21) : demi-convoyage en 21 → pas de part2
    cfg = new_empty_configuration()
    assert place_element_at(cfg, 21, 2)
    assert cfg[21] == 2
    assert side_feeder_position(cfg, 3) == 21


# ---------------------------------------------------------------------------
# S6 — Invariants : aucun effet sur volume, ADD, ou config
# ---------------------------------------------------------------------------
def test_S6_no_side_effect():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 4)
    add_elements_atomic(cfg, 2, 2)
    snapshot = list(cfg)
    vol_before = total_volume_used(cfg)
    add_before = count_user_elements(cfg)
    free_before = free_volume(cfg)

    for zone in range(0, SIDE_FEEDER_MAX_ZONE + 1):
        _ = side_feeder_position(cfg, zone)

    assert cfg == snapshot, "config modifiée par side_feeder_position"
    assert approx(total_volume_used(cfg), vol_before), "volume modifié"
    assert count_user_elements(cfg) == add_before, "ADD modifié"
    assert approx(free_volume(cfg), free_before), "volume libre modifié"


# ---------------------------------------------------------------------------
# S7 — Stabilité après ajout puis reset
# ---------------------------------------------------------------------------
def test_S7_stability_across_add_reset():
    cfg = new_empty_configuration()
    # Référence : toutes les zones sur config vide
    baseline = [side_feeder_position(cfg, z) for z in range(0, SIDE_FEEDER_MAX_ZONE + 1)]
    assert baseline == [81, 4, 12, 21, 30, 39, 48, 57, 66]

    # Ajout d'éléments : 5 entiers type 1 aux positions (1,2)..(9,10).
    # Position 4 devient 2ème partie (101) → zone 1 recule à 3.
    add_elements_atomic(cfg, 1, 5)
    assert cfg[4] == 1 + PART2_OFFSET
    assert side_feeder_position(cfg, 1) == 3
    # Zones hors de la plage modifiée inchangées
    assert side_feeder_position(cfg, 2) == 12
    assert side_feeder_position(cfg, 8) == 66

    # Reset → positions baseline strictement identiques
    cfg = reset_configuration()
    after_reset = [side_feeder_position(cfg, z) for z in range(0, SIDE_FEEDER_MAX_ZONE + 1)]
    assert after_reset == baseline, "positions instables après reset"


# ---------------------------------------------------------------------------
# S8 — Zone hors plage → ValueError
# ---------------------------------------------------------------------------
def test_S8_invalid_zone_raises():
    cfg = new_empty_configuration()
    for bad in (-1, 9, 10, 100):
        try:
            side_feeder_position(cfg, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"zone {bad} aurait dû lever ValueError")


# ---------------------------------------------------------------------------
# S9 — Déterminisme : appels répétés → même résultat
# ---------------------------------------------------------------------------
def test_S9_deterministic():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 8)
    for zone in range(0, SIDE_FEEDER_MAX_ZONE + 1):
        p1 = side_feeder_position(cfg, zone)
        p2 = side_feeder_position(cfg, zone)
        p3 = side_feeder_position(cfg, zone)
        assert p1 == p2 == p3, f"zone {zone} non déterministe"


# ---------------------------------------------------------------------------
# Runner CLI
# ---------------------------------------------------------------------------
TESTS = [
    ("S1  constantes spec", test_S1_constants),
    ("S2  zone 0 désactivé", test_S2_zone_zero_disabled),
    ("S3  zones valides (vide)", test_S3_valid_zones_empty_config),
    ("S4  collision part2 -> recul", test_S4_collision_with_part2),
    ("S5  pas de collision -> position inchangee", test_S5_no_collision_keeps_position),
    ("S6  aucun effet de bord", test_S6_no_side_effect),
    ("S7  stabilite add/reset", test_S7_stability_across_add_reset),
    ("S8  zone invalide -> ValueError", test_S8_invalid_zone_raises),
    ("S9  déterminisme", test_S9_deterministic),
]


def main() -> int:
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}  :: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}  :: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS  {name}")
    print()
    if failed == 0:
        print(f"Etape 3 side feeder : {len(TESTS)}/{len(TESTS)} tests PASS")
        return 0
    print(f"Etape 3 side feeder : {failed}/{len(TESTS)} tests FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
