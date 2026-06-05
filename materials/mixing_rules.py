"""mixing_rules.py — règles de mélange multi-constituants (PURES).

Conversions de fractions, densité de mélange, et lois de viscosité de mélange
(log-additive de Kendall-Monroe) et de suspension chargée (Einstein dilué,
Krieger-Dougherty concentré).

Toutes les fonctions sont paramétrées : aucune matière codée en dur. Les listes
`fractions` ne sont pas re-normalisées silencieusement — l'appelant est
responsable de fournir des fractions sommant à 1 (sauf indication contraire).
"""

from __future__ import annotations

import math

# Viscosité intrinsèque des sphères dures (Einstein) — défaut Krieger-Dougherty.
EINSTEIN_INTRINSIC_VISCOSITY: float = 2.5


def mass_to_volume_fractions(
    mass_fractions: list[float], densities_g_cm3: list[float]
) -> list[float]:
    """Fractions massiques → fractions volumiques.

        v_i = (w_i / ρ_i) / Σ_j (w_j / ρ_j)

    Lève ValueError si les longueurs diffèrent. Renvoie une liste sommant à 1.
    """
    if len(mass_fractions) != len(densities_g_cm3):
        raise ValueError("mass_fractions et densities_g_cm3 de longueurs différentes")
    volumes = [w / rho if rho > 0.0 else 0.0
               for w, rho in zip(mass_fractions, densities_g_cm3)]
    total = sum(volumes)
    if total <= 0.0:
        return [0.0] * len(volumes)
    return [v / total for v in volumes]


def volume_to_mass_fractions(
    volume_fractions: list[float], densities_g_cm3: list[float]
) -> list[float]:
    """Fractions volumiques → fractions massiques.

        w_i = (v_i · ρ_i) / Σ_j (v_j · ρ_j)
    """
    if len(volume_fractions) != len(densities_g_cm3):
        raise ValueError("volume_fractions et densities_g_cm3 de longueurs différentes")
    masses = [v * rho for v, rho in zip(volume_fractions, densities_g_cm3)]
    total = sum(masses)
    if total <= 0.0:
        return [0.0] * len(masses)
    return [m / total for m in masses]


def mixture_density(
    fractions: list[float], densities_g_cm3: list[float], basis: str = "mass"
) -> float:
    """Densité d'un mélange.

    - basis="volume" : ρ = Σ v_i · ρ_i (moyenne volumique, exacte).
    - basis="mass"   : 1/ρ = Σ w_i / ρ_i (volumes additifs).
    Lève ValueError si longueurs incohérentes ou basis inconnue.
    """
    if len(fractions) != len(densities_g_cm3):
        raise ValueError("fractions et densities_g_cm3 de longueurs différentes")
    if basis == "volume":
        return sum(v * rho for v, rho in zip(fractions, densities_g_cm3))
    if basis == "mass":
        inv = sum(w / rho for w, rho in zip(fractions, densities_g_cm3) if rho > 0.0)
        return 1.0 / inv if inv > 0.0 else 0.0
    raise ValueError(f"basis inconnue : {basis!r} (attendu 'mass' ou 'volume')")


def log_additive_viscosity(
    viscosities: list[float], volume_fractions: list[float]
) -> float:
    """Viscosité de mélange log-additive (Kendall-Monroe / Arrhenius) :

        ln η = Σ_i v_i · ln η_i   →   η = Π_i η_i^{v_i}

    Lève ValueError si longueurs incohérentes. Les viscosités ≤ 0 sont ignorées
    (terme non défini en log) au prorata des fractions restantes.
    """
    if len(viscosities) != len(volume_fractions):
        raise ValueError("viscosities et volume_fractions de longueurs différentes")
    acc = 0.0
    weight = 0.0
    for eta, v in zip(viscosities, volume_fractions):
        if eta > 0.0 and v > 0.0:
            acc += v * math.log(eta)
            weight += v
    if weight <= 0.0:
        return 0.0
    return math.exp(acc / weight)


def mixture_specific_heat(
    mass_fractions: list[float], cps_j_per_g_k: list[float]
) -> float:
    """Chaleur spécifique d'un mélange (moyenne MASSIQUE) : Cp = Σ w_i · Cp_i.

    Le Cp massique se mélange additivement par fraction massique (et non
    volumique) — c'est la forme utilisée par l'équation thermique manager E6
    (T_real ∝ 1/(ṁ·Cp)). Lève ValueError si longueurs incohérentes.
    """
    if len(mass_fractions) != len(cps_j_per_g_k):
        raise ValueError("mass_fractions et cps_j_per_g_k de longueurs différentes")
    return sum(w * cp for w, cp in zip(mass_fractions, cps_j_per_g_k))


def einstein_viscosity(medium_viscosity: float, volume_fraction: float) -> float:
    """Suspension diluée (Einstein) : η = η_m · (1 + 2.5·φ).

    Valable pour φ faible (< ~0.05). Au-delà, préférer Krieger-Dougherty.
    """
    return medium_viscosity * (1.0 + EINSTEIN_INTRINSIC_VISCOSITY * volume_fraction)


def krieger_dougherty_viscosity(
    medium_viscosity: float,
    volume_fraction: float,
    max_packing_fraction: float,
    intrinsic_viscosity: float = EINSTEIN_INTRINSIC_VISCOSITY,
) -> float:
    """Suspension concentrée (Krieger-Dougherty) :

        η = η_m · (1 − φ/φ_max)^(−[η]·φ_max)

    - φ → 0       : η → η_m (à l'ordre 1, retrouve Einstein).
    - φ → φ_max   : η → +∞ (blocage / packing maximal).
    Lève ValueError si φ_max ≤ 0. Renvoie +inf si φ ≥ φ_max.
    """
    if max_packing_fraction <= 0.0:
        raise ValueError("max_packing_fraction doit être > 0")
    if volume_fraction >= max_packing_fraction:
        return math.inf
    base = 1.0 - volume_fraction / max_packing_fraction
    return medium_viscosity * base ** (-intrinsic_viscosity * max_packing_fraction)
