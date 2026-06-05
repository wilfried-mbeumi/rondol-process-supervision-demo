"""test_report_params.py — le helper partagé reproduit À L'IDENTIQUE l'ancienne
construction `_build_report` de la page Moteur Procédé.

Garantit qu'après la factorisation, la page Moteur Procédé et le figement de
l'historique procédé produisent EXACTEMENT les mêmes KPIs pour une configuration
connue. On compare le `EngineReport` du helper à un report construit avec la
construction ORIGINALE recopiée ici (oracle indépendant).
"""

from __future__ import annotations

from dataclasses import astuple

import engine  # noqa: F401  (bootstrap sys.path)

from screw_logic import (  # noqa: E402
    ProcessParams,
    add_elements_atomic,
    new_empty_configuration,
)
from physics.conversions import g_per_min_to_g_per_s  # noqa: E402
from materials.powder import POWDERS  # noqa: E402
from engine.app_report import build_engine_report  # noqa: E402
from engine.report_params import (  # noqa: E402
    NOMINAL_SIDE_FEEDER_G_PER_MIN,
    NOMINAL_TEMP_PROFILE_C,
    build_report_from_flat_params,
)


def _demo_config() -> list[int]:
    """Profil de démonstration non trivial (convoyage + malaxages + convoyage)."""
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)
    add_elements_atomic(cfg, 4, 2)
    add_elements_atomic(cfg, 7, 2)
    add_elements_atomic(cfg, 1, 5)
    return cfg


def _oracle_report(config, screw_rpm, feed_g_per_min, bulk_density, side_feeder_zone):
    """Construction ORIGINALE recopiée depuis l'ancien _build_report (oracle)."""
    side_active = side_feeder_zone > 0  # SIDE_FEEDER_DISABLED_ZONE == 0
    params = ProcessParams(
        screw_rpm=screw_rpm,
        feeder1_flow_rate_g_per_s=g_per_min_to_g_per_s(feed_g_per_min),
        feeder1_bulk_density=bulk_density,
        feeder2_flow_rate_g_per_s=(
            g_per_min_to_g_per_s(NOMINAL_SIDE_FEEDER_G_PER_MIN) if side_active else 0.0
        ),
        feeder2_bulk_density=bulk_density if side_active else 0.0,
        side_feeder_zone=side_feeder_zone,
        temp_z=NOMINAL_TEMP_PROFILE_C,
    )
    feeder1_powder = POWDERS["LFP"]
    feeder2_powder = POWDERS["LATP"] if side_active else None
    return build_engine_report(config, params, feeder1_powder, feeder2_powder)


# Cas couverts : sans / avec side feeder, débits/densités/rpm variés.
_CASES = [
    (_demo_config(), 120.0, 30.0, 0.55, 0),    # mono-feeder
    (_demo_config(), 180.0, 45.0, 0.62, 3),    # side feeder zone 3
    (_demo_config(), 90.0, 12.0, 0.40, 5),     # side feeder zone 5
]


def test_helper_matches_legacy_construction():
    """Le helper et l'oracle produisent des EngineReport identiques (champ à champ)."""
    for config, rpm, feed, dens, sfz in _CASES:
        got = build_report_from_flat_params(config, rpm, feed, dens, sfz)
        ref = _oracle_report(config, rpm, feed, dens, sfz)
        assert astuple(got) == astuple(ref), f"divergence pour rpm={rpm}, sfz={sfz}"


def test_helper_kpis_are_finite_and_nonnegative():
    """KPIs principaux : finis et ≥ 0 (sanité, pas une nouvelle physique)."""
    r = build_report_from_flat_params(_demo_config(), 120.0, 30.0, 0.55, 0)
    for val in (
        r.total_torque_nm, r.total_sme_kwh_per_kg, r.residence_time_total_s,
        r.fill_factor_average, r.peak_fill_factor, r.max_shear_rate_s,
        r.mass_flow_kg_per_h, r.output_vol_flow_cm3_s,
    ):
        assert val == val  # not NaN
        assert val >= 0.0


def test_side_feeder_off_uses_lfp_only():
    """Sans side feeder : feeder2_material reste None (pas de LATP injecté)."""
    r = build_report_from_flat_params(_demo_config(), 120.0, 30.0, 0.55, 0)
    assert r.feeder1_material == POWDERS["LFP"].name
    assert r.feeder2_material is None


def test_side_feeder_on_adds_latp():
    """Avec side feeder : feeder2_material = LATP."""
    r = build_report_from_flat_params(_demo_config(), 120.0, 30.0, 0.55, 3)
    assert r.feeder2_material == POWDERS["LATP"].name
