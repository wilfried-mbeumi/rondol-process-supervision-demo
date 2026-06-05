"""element_library.py — physique des éléments de vis (PUR, lecture seule).

Superpose une couche de métadonnées PHYSIQUES (sens de convoyage, malaxage et
angle, intensité de mélange, capacité de mise en pression) au-dessus du
catalogue géométrique de `app/screw_logic.py`.

SOURCE DE VÉRITÉ géométrique = screw_logic (importé en lecture seule) :
  - VOLUME_CM3[type]          → free_volume_cm3()
  - FACTOR_FREE_BY_REV[type]  → free_volume_by_rev_factor()
  - ELEMENT_TYPES[type]       → label / nom / demi-élément
Ce module NE redéfinit AUCUNE de ces valeurs ; il ne fait qu'y déléguer.

Les angles de malaxage proviennent des labels screw_logic (90°/30°/60°/45°).
Les attributs qualitatifs (mixing_intensity, pressure_capacity) sont des
classements relatifs [0..1] destinés au moteur de règles, pas des mesures.
"""

from __future__ import annotations

import machine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from dataclasses import dataclass

from screw_logic import (  # noqa: E402  (module nu — convention canonique, cf. machine/__init__)
    ELEMENT_TYPES,
    FACTOR_FREE_BY_REV,
    N_ELEMENT_TYPES,
    VOLUME_CM3,
)

# Sens de convoyage
CONVEY_FORWARD: int = 1
CONVEY_NEUTRAL: int = 0
CONVEY_REVERSE: int = -1

# ---------------------------------------------------------------------------
# Géométrie machine NOMINALE (micro-extrudeuse Rondol 10,5 mm).
# Utilisée par le cisaillement local γ̇ = πDN/h (manager E1).
# Les vraies profondeurs de chenal PAR ÉLÉMENT seront extraites des plans
# (references/captures_process/*.SLDDRW) en Phase 2+ ; pour l'instant on expose
# un nominal global et un override par élément (channel_depth_mm, None=nominal).
# ---------------------------------------------------------------------------
SCREW_DIAMETER_MM: float = 10.5
NOMINAL_CHANNEL_DEPTH_MM: float = 1.8


@dataclass(frozen=True)
class ElementPhysics:
    """Métadonnées physiques d'un type d'élément (id 1..13).

    Attributs :
      type_id            : id screw_logic (1..13).
      conveying_sign     : +1 forward, 0 neutre (malaxage), −1 reverse.
      is_kneading        : True si bloc malaxeur.
      kneading_angle_deg : angle de décalage des disques (None si non malaxeur).
      mixing_intensity   : intensité de mélange relative [0..1].
      pressure_capacity  : capacité de mise en pression relative [0..1].
      channel_depth_mm   : profondeur de chenal de l'élément (mm). None →
                           utiliser NOMINAL_CHANNEL_DEPTH_MM (valeur globale).
    """
    type_id: int
    conveying_sign: int
    is_kneading: bool
    kneading_angle_deg: float | None
    mixing_intensity: float
    pressure_capacity: float
    channel_depth_mm: float | None = None


# Classement relatif des 13 éléments (ids alignés sur screw_logic.ELEMENT_TYPES).
ELEMENT_PHYSICS: dict[int, ElementPhysics] = {
    1:  ElementPhysics(1,  CONVEY_FORWARD, False, None, 0.10, 0.55),  # Convoyage +
    2:  ElementPhysics(2,  CONVEY_FORWARD, False, None, 0.10, 0.50),  # Convoyage ½
    3:  ElementPhysics(3,  CONVEY_FORWARD, False, None, 0.25, 0.70),  # Pas court
    4:  ElementPhysics(4,  CONVEY_NEUTRAL, True,  90.0, 0.95, 0.20),  # Malaxage 90°
    5:  ElementPhysics(5,  CONVEY_NEUTRAL, True,  30.0, 0.45, 0.45),  # Malaxage 30°
    6:  ElementPhysics(6,  CONVEY_FORWARD, False, None, 0.15, 0.35),  # Grand pas
    7:  ElementPhysics(7,  CONVEY_NEUTRAL, True,  60.0, 0.70, 0.30),  # Malaxage 60°
    8:  ElementPhysics(8,  CONVEY_NEUTRAL, True,  45.0, 0.60, 0.35),  # Malaxage 45°
    9:  ElementPhysics(9,  CONVEY_REVERSE, False, None, 0.55, 0.90),  # Convoyage −
    10: ElementPhysics(10, CONVEY_NEUTRAL, False, None, 0.80, 0.25),  # Chaotique
    11: ElementPhysics(11, CONVEY_NEUTRAL, False, None, 0.65, 0.40),  # Dentelé
    12: ElementPhysics(12, CONVEY_NEUTRAL, False, None, 0.75, 0.30),  # Mélange spécial
    13: ElementPhysics(13, CONVEY_FORWARD, False, None, 0.05, 0.60),  # Pointe + décharge
}


def physics_for(type_id: int) -> ElementPhysics:
    """Métadonnées physiques d'un type. Lève KeyError si type inconnu."""
    return ELEMENT_PHYSICS[type_id]


def conveying_direction(type_id: int) -> int:
    """Sens de convoyage : +1 / 0 / −1."""
    return ELEMENT_PHYSICS[type_id].conveying_sign


def is_kneading(type_id: int) -> bool:
    """True si l'élément est un bloc malaxeur."""
    return ELEMENT_PHYSICS[type_id].is_kneading


def is_conveying(type_id: int) -> bool:
    """True si l'élément a un sens de convoyage net (forward ou reverse)."""
    return ELEMENT_PHYSICS[type_id].conveying_sign != CONVEY_NEUTRAL


def free_volume_cm3(type_id: int) -> float:
    """Volume occupé de l'élément (cm³) — DÉLÈGUE à screw_logic.VOLUME_CM3."""
    return VOLUME_CM3[type_id]


def free_volume_by_rev_factor(type_id: int) -> float:
    """Facteur volume libre/tour — DÉLÈGUE à screw_logic.FACTOR_FREE_BY_REV."""
    return FACTOR_FREE_BY_REV[type_id]


def channel_depth_mm(type_id: int) -> float:
    """Profondeur de chenal de l'élément (mm) pour γ̇ = πDN/h.

    Renvoie l'override par élément s'il est défini, sinon le nominal global
    NOMINAL_CHANNEL_DEPTH_MM. Accesseur stable : remplir les overrides plus tard
    (depuis les plans) ne changera pas l'interface consommée par NodeState.
    """
    override = ELEMENT_PHYSICS[type_id].channel_depth_mm
    return override if override is not None else NOMINAL_CHANNEL_DEPTH_MM


def element_label(type_id: int) -> str:
    """Label HMI — DÉLÈGUE à screw_logic.ELEMENT_TYPES."""
    return ELEMENT_TYPES[type_id].label


def all_physics() -> dict[int, ElementPhysics]:
    """Copie du dictionnaire complet (ids 1..13)."""
    return dict(ELEMENT_PHYSICS)


# Nombre de types réels (hors vide) attendu : screw_logic en déclare 14 (0..13).
N_REAL_ELEMENT_TYPES: int = N_ELEMENT_TYPES - 1  # 13
