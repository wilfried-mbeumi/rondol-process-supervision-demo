"""die_library.py — géométrie de filière (PUR).

Catalogue de filières et grandeurs dérivées (aire ouverte, élancement L/D,
cisaillement pariétal apparent) pour le calcul de contre-pression / cisaillement
en sortie. Aucune dépendance à screw_logic : géométrie pure, indépendante du
profil de vis.

Cisaillement pariétal apparent (approximation newtonienne, par trou) :
    γ̇_w = 4·Q / (π·R³)
où Q est le débit volumique PAR TROU. La correction de Rabinowitsch (fluide
non newtonien) relève de la rhéologie et n'est pas appliquée ici.

Les presets DIES sont NOMINAUX (micro-extrudeuse Rondol 10.5 mm) et à recaler.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Die:
    """Filière à trous circulaires.

    Attributs :
      name             : identifiant lisible.
      n_holes          : nombre de trous.
      hole_diameter_mm : diamètre d'un trou (mm).
      land_length_mm   : longueur de portée / canal du trou (mm).
    """
    name: str
    n_holes: int
    hole_diameter_mm: float
    land_length_mm: float


def single_hole_area_mm2(die: Die) -> float:
    """Aire d'un trou : π·r²."""
    r = die.hole_diameter_mm / 2.0
    return math.pi * r * r


def total_open_area_mm2(die: Die) -> float:
    """Aire ouverte totale : n_holes · π·r²."""
    return die.n_holes * single_hole_area_mm2(die)


def aspect_ratio_l_d(die: Die) -> float:
    """Élancement L/D d'un trou (portée / diamètre). 0.0 si diamètre nul."""
    if die.hole_diameter_mm <= 0.0:
        return 0.0
    return die.land_length_mm / die.hole_diameter_mm


def apparent_wall_shear_rate(die: Die, volumetric_flow_mm3_s: float) -> float:
    """Cisaillement pariétal apparent γ̇_w = 4·Q_trou / (π·R³) (s⁻¹).

    Le débit total `volumetric_flow_mm3_s` est réparti également sur les trous.
    Renvoie 0.0 si géométrie ou débit nul.
    """
    if die.n_holes <= 0 or die.hole_diameter_mm <= 0.0 or volumetric_flow_mm3_s <= 0.0:
        return 0.0
    q_per_hole = volumetric_flow_mm3_s / die.n_holes
    r = die.hole_diameter_mm / 2.0
    return 4.0 * q_per_hole / (math.pi * r ** 3)


# ---------------------------------------------------------------------------
# Presets NOMINAUX — micro-extrudeuse Rondol 10.5 mm. À RECALIBRER.
# ---------------------------------------------------------------------------
DIES: dict[str, Die] = {
    "strand_1mm": Die("Monobrin 1 mm", n_holes=1, hole_diameter_mm=1.0, land_length_mm=3.0),
    "strand_2mm": Die("Monobrin 2 mm", n_holes=1, hole_diameter_mm=2.0, land_length_mm=4.0),
    "twin_2x1mm": Die("Bibrin 2×1 mm", n_holes=2, hole_diameter_mm=1.0, land_length_mm=3.0),
}
