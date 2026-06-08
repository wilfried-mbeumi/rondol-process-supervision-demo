"""Tests robustesse session_state — reproduction + non-régression du crash
« changement de langue → Settings → ValueError n_die_zones ».

Approche : couche PURE (dict en lieu et place de st.session_state). On exerce
exactement la chaîne qui plantait :
    seed_editing_keys(session) -> state_from_session -> _legacy_state_from_session
    -> int(session["n_die_zones"])   # ← ValueError historique
et la reconstruction build_state_from_widgets. Aucun Streamlit requis.
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

from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    seed_editing_keys,
)
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402


# Valeurs « polluées » qui faisaient lever int()/float() sur session_state.
_BAD_NUMERIC = ["", None, "2.0", 2.0, "abc", "Nombre de zones die", [], {}]


# ---------------------------------------------------------------------------
# 1 — n_die_zones tous types : plus jamais de crash, valeur bornée 1..4
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", _BAD_NUMERIC)
def test_n_die_zones_empty_none_string_float_int(bad):
    session: dict = {"n_die_zones": bad}
    # Ne doit PAS lever (chaîne historique du crash).
    state = state_from_session(session)
    assert 1 <= state.n_die_zones <= 4
    seed_editing_keys(session)            # 2e point de crash (Settings ligne 194)
    rebuilt = build_state_from_widgets(session)
    assert 1 <= rebuilt.n_die_zones <= 4


def test_n_die_zones_safe_cast_valid_values():
    for v, expected in [(1, 1), (2, 2), (4, 4), ("3", 3), (3.0, 3), (9, 4), (0, 1)]:
        state = state_from_session({"n_die_zones": v})
        assert state.n_die_zones == expected, (v, state.n_die_zones)


# ---------------------------------------------------------------------------
# 2 — tous les champs numériques de session sont coercés sans lever
# ---------------------------------------------------------------------------
def test_numeric_session_values_are_safely_cast():
    session = {
        "screw_rpm": "fast",          # non numérique
        "feeder_g_per_min": None,
        "bulk_density": "",
        "side_feeder_zone": "Z3",      # libellé, pas un entier
        "n_die_zones": "deux",
        "th_Z1": "chaud",
        "th_Z5": None,
    }
    state = state_from_session(session)             # ne lève pas
    assert state.screw_rpm == 120.0                 # repli défaut
    assert state.zone_temps_C["Z1"] >= 0.0
    assert 1 <= state.n_die_zones <= 4
    # side_feeder_zone illisible → feeder #2 désactivé (pas de crash, pas Z?).
    assert state.feeders[1].enabled is False


# ---------------------------------------------------------------------------
# 3 — un changement de langue ne mute pas l'état métier
# ---------------------------------------------------------------------------
def test_language_switch_does_not_mutate_business_state():
    """L'état métier reconstruit est identique quelle que soit `ui_lang`.

    On simule l'effet d'un switch de langue : seule la clé `ui_lang` change ;
    aucune clé métier n'est touchée. build_state_from_widgets doit produire le
    même ProcessState avant/après.
    """
    base = {
        "n_die_zones": 3,
        "screw_rpm": 150.0,
        "feeder_g_per_min": 42.0,
        "bulk_density": 0.6,
        "th_Z1": 30.0,
        "ui_lang": "fr",
    }
    seed_editing_keys(base)
    before = build_state_from_widgets(base)

    base["ui_lang"] = "en"             # ← le switch de langue, et rien d'autre
    after = build_state_from_widgets(base)

    assert before.n_die_zones == after.n_die_zones == 3
    assert before.screw_rpm == after.screw_rpm == 150.0
    assert before.zone_temps_C == after.zone_temps_C
    assert before.feeders[0].mass_flow_g_per_min == after.feeders[0].mass_flow_g_per_min


# ---------------------------------------------------------------------------
# 4 — une valeur traduite/UI n'entre jamais dans l'état métier
# ---------------------------------------------------------------------------
def test_ui_translated_values_never_enter_business_state():
    # n_die_zones contient par erreur le LIBELLÉ traduit du widget.
    session = {"n_die_zones": "NUMBER OF DIE ZONES", "side_feeder_zone": "Side feeder"}
    state = state_from_session(session)
    assert isinstance(state.n_die_zones, int) and 1 <= state.n_die_zones <= 4
    assert state.feeders[1].enabled is False
