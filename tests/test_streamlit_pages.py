"""
test_streamlit_pages.py — exécution réelle des pages Streamlit avec AppTest.

Vérifie que Home / Profile / Settings se rendent sans exception runtime, et
joue le scénario demandé :
  - Profile : reset configuration / Configuration démo / Demo chaotic
  - Profile : modification side_feeder_zone
  - Settings : modification rpm / feed / bulk / target_count
  - Home : avec config vide puis avec config démo (via session_state)

Utilise streamlit.testing.v1.AppTest (officiel, depuis Streamlit 1.30).
Capture toute AttributeError / NotFoundError / autre exception.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Streamlit AppTest API
try:
    from streamlit.testing.v1 import AppTest  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"SKIP : streamlit.testing.v1 indisponible ({exc})")
    sys.exit(0)


HOME_PATH = str(ROOT / "app" / "Supervision.py")
PROFILE_PATH = str(ROOT / "app" / "pages" / "1_Profile.py")
SETTINGS_PATH = str(ROOT / "app" / "pages" / "2_Settings.py")


def _check_no_exception(at: AppTest, scenario: str) -> None:
    if at.exception:
        excs = "\n".join(str(e.value) for e in at.exception)
        raise AssertionError(f"[{scenario}] {len(at.exception)} exception(s) : {excs}")


def test_T1_home_renders_clean():
    at = AppTest.from_file(HOME_PATH).run(timeout=30)
    _check_no_exception(at, "Home initial")


def test_T2_profile_renders_clean():
    at = AppTest.from_file(PROFILE_PATH).run(timeout=30)
    _check_no_exception(at, "Profile initial")


def test_T3_settings_renders_clean():
    at = AppTest.from_file(SETTINGS_PATH).run(timeout=30)
    _check_no_exception(at, "Settings initial")


def _try_click(at: AppTest, key: str, scenario: str) -> AppTest:
    """Clique le bouton ayant cette clé s'il existe (sidebar OU main),
    relance l'app et vérifie l'absence d'exception. Retourne le nouvel
    AppTest (chainable). No-op si le bouton n'existe pas."""
    for container in (at.sidebar, at):
        try:
            btn = container.button(key=key)
        except Exception:
            continue
        # AppTest>=1.30 : .button(key=...) retourne directement le widget
        # (pas une liste).
        if btn is None:
            continue
        new_at = btn.click().run(timeout=30)
        _check_no_exception(new_at, scenario)
        return new_at
    return at


def _try_set(at: AppTest, widget_kind: str, key: str, value, scenario: str) -> AppTest:
    """Idem _try_click pour un widget réglable (selectbox/number_input/radio)."""
    for container in (at.sidebar, at):
        try:
            getter = getattr(container, widget_kind)
            w = getter(key=key)
        except Exception:
            continue
        if w is None:
            continue
        new_at = w.set_value(value).run(timeout=30)
        _check_no_exception(new_at, scenario)
        return new_at
    return at


def test_T4_profile_reset_demo_chaotic():
    """Joue : reset → démo → chaotic → reset, sur la page Profile."""
    at = AppTest.from_file(PROFILE_PATH).run(timeout=30)
    _check_no_exception(at, "Profile load")

    at = _try_click(at, "btn_reset", "Profile after reset")
    at = _try_click(at, "btn_demo", "Profile after demo")
    at = _try_click(at, "btn_demo_chaotic", "Profile after demo chaotic")
    at = _try_click(at, "btn_reset", "Profile re-reset")


def test_T5_profile_side_feeder_zone_changes():
    """Change side_feeder_zone via le selectbox → render doit rester clean."""
    at = AppTest.from_file(PROFILE_PATH).run(timeout=30)
    _check_no_exception(at, "Profile load")

    for zone in (0, 1, 4, 8):
        at = _try_set(at, "selectbox", "sb_sf_zone", zone,
                      f"Profile side feeder zone={zone}")


def test_T6_settings_change_process_params():
    """Modifie rpm / feed / bulk / target_count → pas d'exception."""
    at = AppTest.from_file(SETTINGS_PATH).run(timeout=30)
    _check_no_exception(at, "Settings load")

    at = _try_set(at, "number_input", "ni_screw_rpm", 180.0, "Settings rpm=180")
    at = _try_set(at, "number_input", "ni_feeder", 45.0, "Settings feed=45")
    at = _try_set(at, "number_input", "ni_bulk", 0.80, "Settings bulk=0.80")
    for count in (25, 40, 30):
        at = _try_set(at, "radio", "rd_target_count", count,
                      f"Settings target_count={count}")
    at = _try_set(at, "selectbox", "sl_sf_zone", 4, "Settings side feeder zone=4")


def test_T7_home_with_demo_config_via_state():
    """Home doit gérer correctement le cas où screw_config existe (set par Profile)."""
    at = AppTest.from_file(HOME_PATH)
    # Pré-remplir session state comme si Profile avait été visité
    at.session_state["screw_rpm"] = 150.0
    at.session_state["feeder_g_per_min"] = 40.0
    at.session_state["bulk_density"] = 0.65
    at.run(timeout=30)
    _check_no_exception(at, "Home with custom session state")


TESTS = [
    ("T1 Home renders clean", test_T1_home_renders_clean),
    ("T2 Profile renders clean", test_T2_profile_renders_clean),
    ("T3 Settings renders clean", test_T3_settings_renders_clean),
    ("T4 Profile reset/demo/chaotic", test_T4_profile_reset_demo_chaotic),
    ("T5 Profile side feeder change", test_T5_profile_side_feeder_zone_changes),
    ("T6 Settings change params", test_T6_settings_change_process_params),
    ("T7 Home with custom state", test_T7_home_with_demo_config_via_state),
]


def main() -> int:
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}\n      :: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}\n      :: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS  {name}")
    print()
    if failed == 0:
        print(f"Streamlit pages : {len(TESTS)}/{len(TESTS)} tests PASS")
        return 0
    print(f"Streamlit pages : {failed}/{len(TESTS)} tests FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
