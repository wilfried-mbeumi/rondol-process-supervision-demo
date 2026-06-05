"""
Tests Étape 2 — gestion utilisateur (ADD, +1, +4 atomique, reset, invariants).

Exécution directe : python tests/test_screw_logic_user.py
Les tests de volume de l'Étape 1 ne sont PAS dupliqués ici (voir test_screw_logic_volume.py).
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
    TIP_PART1_POS,
    TIP_PART2_POS,
    TIP_TYPE,
    add_element,
    add_elements_atomic,
    count_user_elements,
    free_volume,
    new_empty_configuration,
    place_element_at,
    remaining_slots,
    remove_at,
    reset_configuration,
    total_volume_used,
)

TOL = 1e-5


def approx(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def invariant_add_remaining(cfg: list[int]) -> None:
    """ADD + remaining == 39 à tout instant."""
    assert approx(count_user_elements(cfg) + remaining_slots(cfg),
                  MAX_USER_ELEMENTS), "invariant ADD + remaining = 39 violé"


# ---------------------------------------------------------------------------
# U1 — +1 ajout simple (type 1 entier)
# ---------------------------------------------------------------------------
def test_U1_plus_one_full():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 1, 1)
    assert count_user_elements(cfg) == 1.0
    assert remaining_slots(cfg) == 38.0
    # 1er emplacement libre utilisateur = position 1 (pos 0 réservée)
    assert cfg[1] == 1 and cfg[2] == 101
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U2 — +1 demi-convoyage (type 2)
# ---------------------------------------------------------------------------
def test_U2_plus_one_half():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 2, 1)
    assert count_user_elements(cfg) == 0.5
    assert remaining_slots(cfg) == 38.5
    assert cfg[1] == 2 and cfg[2] == 0
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U3 — +4 ajout atomique sur config vide (type 1)
# ---------------------------------------------------------------------------
def test_U3_plus_four_empty():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 1, 4)
    assert count_user_elements(cfg) == 4.0
    assert remaining_slots(cfg) == 35.0
    # 4 éléments consécutifs aux positions 1,3,5,7 (1ère parties)
    for k in range(4):
        pos = 1 + 2 * k
        assert cfg[pos] == 1, f"pos {pos} devrait être type 1"
        assert cfg[pos + 1] == 101, f"pos {pos+1} devrait être 2ème partie"
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U4 — +4 atomicité : échec → rollback complet
# ---------------------------------------------------------------------------
def test_U4_plus_four_rollback():
    cfg = new_empty_configuration()
    # Remplir jusqu'à ADD = 37 (laisse 2 slots libres)
    assert add_elements_atomic(cfg, 1, 37)
    assert count_user_elements(cfg) == 37.0
    snapshot = list(cfg)
    # Tenter +4 → doit échouer et ne rien modifier
    assert not add_elements_atomic(cfg, 1, 4)
    assert count_user_elements(cfg) == 37.0
    assert cfg == snapshot, "rollback incomplet"
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U5 — Limite ADD = 39 : +1 au-delà refusé
# ---------------------------------------------------------------------------
def test_U5_limit_39():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 1, 39)
    assert count_user_elements(cfg) == 39.0
    assert remaining_slots(cfg) == 0.0
    # +1 supplémentaire doit échouer
    assert not add_elements_atomic(cfg, 1, 1)
    assert count_user_elements(cfg) == 39.0
    # +1 demi aussi refusé
    assert not add_elements_atomic(cfg, 2, 1)
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U6 — Reset préserve tip et remet ADD à 0
# ---------------------------------------------------------------------------
def test_U6_reset():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 10)
    add_elements_atomic(cfg, 2, 2)
    assert count_user_elements(cfg) == 11.0
    cfg = reset_configuration()
    assert count_user_elements(cfg) == 0.0
    assert remaining_slots(cfg) == 39.0
    assert cfg[TIP_PART1_POS] == TIP_TYPE
    assert cfg[TIP_PART2_POS] == TIP_TYPE + PART2_OFFSET
    assert approx(total_volume_used(cfg), 0.61060)
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U7 — Retrait cohérent (remove_at)
# ---------------------------------------------------------------------------
def test_U7_remove():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 3)  # 3 entiers aux pos 1,3,5
    assert count_user_elements(cfg) == 3.0
    # retrait sur 1ère partie (pos 3)
    assert remove_at(cfg, 3)
    assert count_user_elements(cfg) == 2.0
    assert cfg[3] == 0 and cfg[4] == 0
    invariant_add_remaining(cfg)
    # retrait sur 2ème partie (pos 2, qui est 101) → efface la 1ère aussi
    assert remove_at(cfg, 2)
    assert count_user_elements(cfg) == 1.0
    assert cfg[1] == 0 and cfg[2] == 0
    invariant_add_remaining(cfg)
    # retrait position vide refusé
    assert not remove_at(cfg, 10)
    # retrait tip refusé
    assert not remove_at(cfg, TIP_PART1_POS)
    assert not remove_at(cfg, TIP_PART2_POS)
    assert cfg[TIP_PART1_POS] == TIP_TYPE
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U8 — Invariant volume après plusieurs ajouts/retraits
# ---------------------------------------------------------------------------
def test_U8_volume_invariant():
    cfg = new_empty_configuration()
    # séquence mixte
    add_elements_atomic(cfg, 1, 4)   # 4 entiers
    add_elements_atomic(cfg, 2, 2)   # 2 demis
    add_elements_atomic(cfg, 5, 1)   # 1 K30
    # Volume attendu :
    # 4 × 0.61060 (type 1) = 2.44240
    # 2 × 0.30328 (type 2) = 0.60656
    # 1 × 0.61058 (type 5) = 0.61058
    # 1 × 0.61060 (tip)    = 0.61060
    #                      = 4.27014
    assert approx(total_volume_used(cfg), 4.27014), total_volume_used(cfg)
    # ADD = 4 entiers + 2×0.5 demis + 1 K30 entier = 6.0
    assert count_user_elements(cfg) == 6.0, count_user_elements(cfg)
    invariant_add_remaining(cfg)
    # retrait 1 entier (Forward à pos 1) → ADD = 5
    assert remove_at(cfg, 1)
    assert approx(total_volume_used(cfg), 4.27014 - 0.61060), total_volume_used(cfg)
    assert count_user_elements(cfg) == 5.0, count_user_elements(cfg)
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U9 — +4 type 2 (demis) = 2 éléments ADD
# ---------------------------------------------------------------------------
def test_U9_plus_four_halves():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 2, 4)
    assert count_user_elements(cfg) == 2.0  # 4 × 0.5
    assert remaining_slots(cfg) == 37.0
    for k in range(4):
        assert cfg[1 + k] == 2
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# U10 — +4 à la limite exacte (ADD=35, +4 possible)
# ---------------------------------------------------------------------------
def test_U10_plus_four_boundary():
    cfg = new_empty_configuration()
    assert add_elements_atomic(cfg, 1, 35)
    assert count_user_elements(cfg) == 35.0
    assert add_elements_atomic(cfg, 1, 4)
    assert count_user_elements(cfg) == 39.0
    assert remaining_slots(cfg) == 0.0
    invariant_add_remaining(cfg)


# ---------------------------------------------------------------------------
# Runner CLI
# ---------------------------------------------------------------------------
TESTS = [
    ("U1  +1 entier", test_U1_plus_one_full),
    ("U2  +1 demi", test_U2_plus_one_half),
    ("U3  +4 atomique OK", test_U3_plus_four_empty),
    ("U4  +4 rollback", test_U4_plus_four_rollback),
    ("U5  limite 39", test_U5_limit_39),
    ("U6  reset + tip", test_U6_reset),
    ("U7  retrait", test_U7_remove),
    ("U8  volume invariant", test_U8_volume_invariant),
    ("U9  +4 demis", test_U9_plus_four_halves),
    ("U10 +4 limite exacte", test_U10_plus_four_boundary),
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
        print(f"Etape 2 user : {len(TESTS)}/{len(TESTS)} tests PASS")
        return 0
    print(f"Etape 2 user : {failed}/{len(TESTS)} tests FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
