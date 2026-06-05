"""
Tests Étape 1 — règle de volume conforme PDF 2-CALCULS (Network 7).

Exécution directe : python tests/test_screw_logic_volume.py
Tolerance : 1e-5 cm³ (toutes les valeurs attendues sont calculées
analytiquement depuis Volume_cm3[] du PDF).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.screw_logic import (  # noqa: E402
    MAX_USER_ELEMENTS,
    TIP_PART1_POS,
    TIP_PART2_POS,
    TIP_TYPE,
    PART2_OFFSET,
    count_user_elements,
    free_volume,
    new_empty_configuration,
    place_element_at,
    remaining_slots,
    reset_configuration,
    total_volume_used,
)

TOL = 1e-5


def approx(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# T1 — Configuration initiale (tip seul)
# ---------------------------------------------------------------------------
def test_T1_tip_only():
    cfg = new_empty_configuration()
    assert cfg[TIP_PART1_POS] == TIP_TYPE
    assert cfg[TIP_PART2_POS] == TIP_TYPE + PART2_OFFSET
    assert approx(total_volume_used(cfg), 1.22120), total_volume_used(cfg)  # 2 vis × 0.61060
    assert approx(free_volume(cfg), 74.95440), free_volume(cfg)
    assert count_user_elements(cfg) == 0.0
    assert remaining_slots(cfg) == 39.0


# ---------------------------------------------------------------------------
# T2 — 1 × Forward conveying entier aux positions [4, 5]
# ---------------------------------------------------------------------------
def test_T2_one_full_forward():
    cfg = new_empty_configuration()
    assert place_element_at(cfg, 4, 1)
    assert cfg[4] == 1 and cfg[5] == 101
    assert approx(total_volume_used(cfg), 2.44240), total_volume_used(cfg)  # 2 vis × 1.22120
    assert approx(free_volume(cfg), 73.73320), free_volume(cfg)
    assert count_user_elements(cfg) == 1.0
    assert remaining_slots(cfg) == 38.0


# ---------------------------------------------------------------------------
# T3 — 1 × Forward conveying half à la position [4]
# ---------------------------------------------------------------------------
def test_T3_one_half():
    cfg = new_empty_configuration()
    assert place_element_at(cfg, 4, 2)
    assert cfg[4] == 2 and cfg[5] == 0
    assert approx(total_volume_used(cfg), 1.82776), total_volume_used(cfg)  # 2 vis × 0.91388
    assert approx(free_volume(cfg), 74.34784), free_volume(cfg)
    assert count_user_elements(cfg) == 0.5
    assert remaining_slots(cfg) == 38.5


# ---------------------------------------------------------------------------
# T4 — Configuration complexe (6.5 éléments utilisateur + tip)
# ---------------------------------------------------------------------------
def test_T4_mixed_config():
    cfg = new_empty_configuration()
    for p in (4, 6, 8, 10):
        assert place_element_at(cfg, p, 1), f"pose Forward à pos {p}"
    assert place_element_at(cfg, 12, 2)
    assert place_element_at(cfg, 13, 5)
    assert place_element_at(cfg, 15, 4)
    assert approx(total_volume_used(cfg), 9.15488), total_volume_used(cfg)  # 2 vis × 4.57744
    assert approx(free_volume(cfg), 67.02072), free_volume(cfg)
    assert count_user_elements(cfg) == 6.5
    assert remaining_slots(cfg) == 32.5


# ---------------------------------------------------------------------------
# T5 — Saturation par demi-convoyages (78 × type 2)
# ---------------------------------------------------------------------------
def test_T5_saturation_halves():
    cfg = new_empty_configuration()
    for i in range(1, 79):
        cfg[i] = 2
    assert count_user_elements(cfg) == 39.0
    assert remaining_slots(cfg) == 0.0
    assert approx(total_volume_used(cfg), 48.53288), total_volume_used(cfg)  # 2 vis × 24.26644


# ---------------------------------------------------------------------------
# T6 — Saturation par 39 éléments entiers type 1 (positions 1..78)
# ---------------------------------------------------------------------------
def test_T6_saturation_full_type1():
    cfg = new_empty_configuration()
    for k in range(39):
        pos = 1 + 2 * k
        cfg[pos] = 1
        cfg[pos + 1] = 101
    assert count_user_elements(cfg) == 39.0
    assert remaining_slots(cfg) == 0.0
    # Vis saturée 39 convoyages : 24.42400 par vis → 48.84800 pour 2 vis.
    # Volume libre correspondant = 76.1756 − 48.848 = 27.3276 cm³ (exemple manager).
    assert approx(total_volume_used(cfg), 48.84800), total_volume_used(cfg)
    assert approx(free_volume(cfg), 27.32760), free_volume(cfg)


# ---------------------------------------------------------------------------
# T7 — Mix maximum (39 × type 6 Large pitch, le plus volumineux)
# ---------------------------------------------------------------------------
def test_T7_max_volume():
    cfg = new_empty_configuration()
    for k in range(39):
        pos = 1 + 2 * k
        cfg[pos] = 6
        cfg[pos + 1] = 106
    assert approx(total_volume_used(cfg), 51.19814), total_volume_used(cfg)  # 2 vis × 25.59907
    assert total_volume_used(cfg) < 76.17560, "jamais > TOTAL_FREE"


# ---------------------------------------------------------------------------
# T8 — Reset préserve le tip
# ---------------------------------------------------------------------------
def test_T8_reset_preserves_tip():
    cfg = new_empty_configuration()
    for p in (4, 6, 8, 10):
        place_element_at(cfg, p, 1)
    place_element_at(cfg, 12, 2)
    place_element_at(cfg, 13, 5)
    place_element_at(cfg, 15, 4)
    assert count_user_elements(cfg) == 6.5
    cfg = reset_configuration()
    assert cfg[TIP_PART1_POS] == TIP_TYPE
    assert cfg[TIP_PART2_POS] == TIP_TYPE + PART2_OFFSET
    assert approx(total_volume_used(cfg), 1.22120), total_volume_used(cfg)  # 2 vis × 0.61060
    assert count_user_elements(cfg) == 0.0
    assert remaining_slots(cfg) == 39.0


# ---------------------------------------------------------------------------
# Runner CLI
# ---------------------------------------------------------------------------
TESTS = [
    ("T1 — tip seul", test_T1_tip_only),
    ("T2 — 1 Forward entier", test_T2_one_full_forward),
    ("T3 — 1 demi", test_T3_one_half),
    ("T4 — mix 6.5 éléments", test_T4_mixed_config),
    ("T5 — 78 demis", test_T5_saturation_halves),
    ("T6 — 39 entiers type 1", test_T6_saturation_full_type1),
    ("T7 — 39 type 6 (max)", test_T7_max_volume),
    ("T8 — reset préserve tip", test_T8_reset_preserves_tip),
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
        print(f"Etape 1 volume : {len(TESTS)}/{len(TESTS)} tests PASS")
        return 0
    print(f"Etape 1 volume : {failed}/{len(TESTS)} tests FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
