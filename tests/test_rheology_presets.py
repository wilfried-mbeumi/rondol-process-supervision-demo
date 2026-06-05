"""Tests Phase 3.2 — materials/rheology_presets.py.

Vérifie la PRÉSENCE et la COHÉRENCE PHYSIQUE des paramètres rhéo nominaux, et la
résolution par nom avec DÉFAUT EXPLICITE (jamais silencieux). Aucune viscosité
n'est calculée ici (le moteur rheology.py n'est même pas sollicité).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from materials.powder import POWDERS, Powder  # noqa: E402
from materials import rheology_presets as rp  # noqa: E402


def test_presets_present_for_all_powders():
    """Chaque matière du catalogue POWDERS a un preset rhéo dédié (par nom)."""
    for key in ("LFP", "LATP", "graphite", "PVDF"):
        powder = POWDERS[key]
        assert powder.name in rp.MELT_RHEOLOGY, key
        preset = rp.MELT_RHEOLOGY[powder.name]
        assert isinstance(preset, rp.MaterialRheology)
        assert preset.name == powder.name


def test_parameters_physically_coherent():
    """Paramètres positifs et plages physiques (shear-thinning, λ>0, Ea≥0)."""
    for preset in rp.MELT_RHEOLOGY.values():
        assert preset.eta_zero_pa_s > 0.0
        assert preset.eta_inf_pa_s >= 0.0
        assert preset.eta_zero_pa_s > preset.eta_inf_pa_s   # plateau bas > haut
        assert preset.relax_time_s > 0.0
        assert 0.0 < preset.flow_index_n <= 1.0             # rhéofluidifiant
        assert preset.yasuda_a > 0.0
        assert preset.activation_energy_j_mol >= 0.0
        assert preset.tref_c == 20.0


def test_lookup_known_material_returns_its_preset():
    """melt_rheology_for(matière connue) → son preset exact (identité)."""
    lfp = POWDERS["LFP"]
    assert rp.melt_rheology_for(lfp) is rp.MELT_RHEOLOGY[lfp.name]


def test_unknown_material_returns_explicit_default_not_silent():
    """Matière inconnue → DEFAULT tracé (name reflète la matière), pas None/erreur."""
    unknown = Powder("Inconnu_XYZ", bulk_density_g_cm3=1.0, true_density_g_cm3=2.0)
    res = rp.melt_rheology_for(unknown)
    assert res is not None
    assert isinstance(res, rp.MaterialRheology)
    # Défaut EXPLICITE et traçable : le nom porte la matière demandée.
    assert "DEFAULT" in res.name
    assert "Inconnu_XYZ" in res.name
    # Valeurs = celles du DEFAULT documenté (hors name).
    assert res.eta_zero_pa_s == rp.DEFAULT_RHEOLOGY.eta_zero_pa_s
    assert res.flow_index_n == rp.DEFAULT_RHEOLOGY.flow_index_n


def test_default_rheology_is_coherent():
    d = rp.DEFAULT_RHEOLOGY
    assert d.eta_zero_pa_s > d.eta_inf_pa_s > 0.0
    assert 0.0 < d.flow_index_n <= 1.0
    assert d.relax_time_s > 0.0


def test_presets_are_data_only_no_computation():
    """Garde de séparation : presets = données figées (frozen), aucun calcul."""
    import dataclasses as dc
    assert dc.is_dataclass(rp.MaterialRheology)
    assert rp.MaterialRheology.__dataclass_params__.frozen


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("rheology_presets: all tests passed")
