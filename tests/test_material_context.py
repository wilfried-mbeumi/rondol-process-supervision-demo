"""Tests Phase 2 — engine/material_context.py.

Vérifie le mapping nominal amont/aval du side feeder et la DÉLÉGATION des
grandeurs de mélange à materials.mixing_rules (aucun recalcul local).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine  # noqa: E402,F401  (bootstrap sys.path)
from engine.material_context import (  # noqa: E402
    FeedContext,
    MaterialPresence,
    SIDE_FEEDER_DISABLED_POSITION,
)
from materials.powder import POWDERS  # noqa: E402
from materials import mixing_rules as mr  # noqa: E402
from materials import rheology_presets as rp  # noqa: E402


LFP = POWDERS["LFP"]
LATP = POWDERS["LATP"]


def test_single_feeder_is_pure_everywhere():
    """Sans side feeder : feeder1 pur partout, jamais de mélange."""
    fc = FeedContext(feeder1_powder=LFP,
                     side_feeder_position=SIDE_FEEDER_DISABLED_POSITION)
    for pos in (4, 20, 40, 78):
        pres = fc.presence_at(pos)
        assert isinstance(pres, MaterialPresence)
        assert pres.is_blend is False
        assert pres.powders == (LFP,)
        assert pres.volume_fractions == (1.0,)
        assert pres.density_g_cm3 == LFP.bulk_density_g_cm3
        assert pres.cp_j_per_g_k == LFP.cp_j_per_g_k


def test_upstream_pure_downstream_blend():
    """Amont du port = feeder1 pur ; aval = mélange feeder1+feeder2."""
    side_pos = 21
    fc = FeedContext(
        feeder1_powder=LFP, feeder1_qvol_cm3_s=2.0,
        feeder2_powder=LATP, feeder2_qvol_cm3_s=1.0,
        side_feeder_position=side_pos,
    )
    up = fc.presence_at(side_pos - 1)
    assert up.is_blend is False and up.powders == (LFP,)
    # Le port lui-même compte comme amont (matière latérale pas encore convoyée).
    assert fc.presence_at(side_pos).is_blend is False
    down = fc.presence_at(side_pos + 1)
    assert down.is_blend is True
    assert down.powders == (LFP, LATP)


def test_blend_fractions_and_props_delegate_to_mixing_rules():
    """Prorata volumique = qvol ; densité/Cp == valeurs mixing_rules."""
    fc = FeedContext(
        feeder1_powder=LFP, feeder1_qvol_cm3_s=3.0,
        feeder2_powder=LATP, feeder2_qvol_cm3_s=1.0,
        side_feeder_position=10,
    )
    down = fc.presence_at(50)
    # Prorata volumique attendu = 3/4 et 1/4.
    assert abs(down.volume_fractions[0] - 0.75) < 1e-12
    assert abs(down.volume_fractions[1] - 0.25) < 1e-12
    # Densité = mixture_density volume basis (délégation stricte).
    vol = [0.75, 0.25]
    dens = [LFP.bulk_density_g_cm3, LATP.bulk_density_g_cm3]
    assert abs(down.density_g_cm3 - mr.mixture_density(vol, dens, basis="volume")) < 1e-12
    # Cp = mixture_specific_heat sur fractions MASSIQUES dérivées.
    mass = mr.volume_to_mass_fractions(vol, dens)
    cps = [LFP.cp_j_per_g_k, LATP.cp_j_per_g_k]
    assert abs(down.cp_j_per_g_k - mr.mixture_specific_heat(mass, cps)) < 1e-12


def test_blend_falls_back_when_no_feeder2_flow():
    """Side feeder déclaré mais débit total nul → matière amont (pas de NaN)."""
    fc = FeedContext(
        feeder1_powder=LFP, feeder1_qvol_cm3_s=0.0,
        feeder2_powder=LATP, feeder2_qvol_cm3_s=0.0,
        side_feeder_position=10,
    )
    down = fc.presence_at(50)
    assert down.is_blend is False
    assert down.powders == (LFP,)


# ---------------------------------------------------------------------------
# Bloc 3.2 — rheologies attachées (par constituant, non pré-combinées)
# ---------------------------------------------------------------------------
def test_rheologies_aligned_single_constituent():
    """Mono-constituant : rheologies a EXACTEMENT 1 entrée, alignée sur powders."""
    fc = FeedContext(feeder1_powder=LFP,
                     side_feeder_position=SIDE_FEEDER_DISABLED_POSITION)
    pres = fc.presence_at(20)
    assert len(pres.rheologies) == 1
    assert len(pres.rheologies) == len(pres.powders)
    # Résolution par nom = preset LFP exact.
    assert pres.rheologies[0] is rp.melt_rheology_for(LFP)
    assert pres.rheologies[0].name == LFP.name


def test_rheologies_blend_has_n_entries_not_precombined():
    """Mélange : N entrées (1 par constituant), NON pré-combinées."""
    fc = FeedContext(
        feeder1_powder=LFP, feeder1_qvol_cm3_s=2.0,
        feeder2_powder=LATP, feeder2_qvol_cm3_s=1.0,
        side_feeder_position=10,
    )
    down = fc.presence_at(50)
    assert down.is_blend is True
    assert len(down.rheologies) == 2 == len(down.powders)
    # Chaque entrée correspond à SON constituant (pas une moyenne).
    assert down.rheologies[0] is rp.melt_rheology_for(LFP)
    assert down.rheologies[1] is rp.melt_rheology_for(LATP)
    # Aucune entrée "DEFAULT"/combinée parasite.
    assert {r.name for r in down.rheologies} == {LFP.name, LATP.name}


def test_density_and_cp_unchanged_by_3_2():
    """Non-régression : density/cp identiques à la délégation mixing_rules d'avant."""
    fc = FeedContext(
        feeder1_powder=LFP, feeder1_qvol_cm3_s=3.0,
        feeder2_powder=LATP, feeder2_qvol_cm3_s=1.0,
        side_feeder_position=10,
    )
    up = fc.presence_at(5)
    assert up.density_g_cm3 == LFP.bulk_density_g_cm3
    assert up.cp_j_per_g_k == LFP.cp_j_per_g_k
    down = fc.presence_at(50)
    vol = [0.75, 0.25]
    dens = [LFP.bulk_density_g_cm3, LATP.bulk_density_g_cm3]
    mass = mr.volume_to_mass_fractions(vol, dens)
    cps = [LFP.cp_j_per_g_k, LATP.cp_j_per_g_k]
    assert down.density_g_cm3 == mr.mixture_density(vol, dens, basis="volume")
    assert down.cp_j_per_g_k == mr.mixture_specific_heat(mass, cps)


def test_unknown_material_carries_explicit_default_rheology():
    """Matière inconnue dans une présence → rhéo DEFAULT explicite, pas None."""
    from materials.powder import Powder
    unknown = Powder("MatX", bulk_density_g_cm3=1.0, true_density_g_cm3=2.0,
                     cp_j_per_g_k=0.9)
    fc = FeedContext(feeder1_powder=unknown,
                     side_feeder_position=SIDE_FEEDER_DISABLED_POSITION)
    pres = fc.presence_at(20)
    assert len(pres.rheologies) == 1
    assert "DEFAULT" in pres.rheologies[0].name
    assert "MatX" in pres.rheologies[0].name


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("material_context: all tests passed")
