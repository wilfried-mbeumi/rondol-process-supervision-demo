"""rheology.py — lois de viscosité (PURES, paramétrées).

Trois briques constitutives indépendantes de tout état procédé :
  - loi puissance (Ostwald-de Waele)      : η = k·γ̇^(n−1)
  - modèle de Cross                        : plateau η₀ → η∞ avec γ̇
  - décalage thermique d'Arrhenius         : facteur a_T multiplicatif

Aucune valeur matière codée en dur : tous les paramètres sont passés par
l'appelant (les presets matière vivent dans powder.py / mixing_rules.py).
Les modèles sont volontairement séparés des dataclasses-bundle pour rester
composables (on combine viscosité × a_T explicitement côté appelant).
"""

from __future__ import annotations

import math

# Constante des gaz parfaits (J·mol⁻¹·K⁻¹) — facteur d'Arrhenius.
GAS_CONSTANT_J_MOL_K: float = 8.314462618


def power_law_viscosity(shear_rate_s: float, consistency_k: float, flow_index_n: float) -> float:
    """Loi puissance : η = k · γ̇^(n−1).

    - n = 1  → fluide newtonien (η = k, indépendant de γ̇).
    - n < 1  → rhéofluidifiant (shear-thinning) : η décroît avec γ̇.
    - n > 1  → rhéoépaississant.
    À γ̇ = 0 avec n < 1 la loi diverge ; on renvoie alors +inf (comportement
    mathématique exact, l'écrêtage éventuel relève de l'appelant).
    """
    if shear_rate_s <= 0.0:
        if flow_index_n < 1.0:
            return math.inf
        if flow_index_n > 1.0:
            return 0.0
        return consistency_k
    return consistency_k * shear_rate_s ** (flow_index_n - 1.0)


def cross_viscosity(
    shear_rate_s: float,
    eta_zero: float,
    eta_inf: float,
    relax_time_s: float,
    exponent_m: float,
) -> float:
    """Modèle de Cross : η = η∞ + (η₀ − η∞) / (1 + (λ·γ̇)^m).

    - γ̇ → 0   : η → η₀ (plateau newtonien bas cisaillement).
    - γ̇ → ∞   : η → η∞ (plateau haut cisaillement).
    """
    denom = 1.0 + (relax_time_s * shear_rate_s) ** exponent_m
    return eta_inf + (eta_zero - eta_inf) / denom


def carreau_yasuda_viscosity(
    shear_rate_s: float,
    eta_zero: float,
    eta_inf: float = 0.0,
    relax_time_s: float = 1.0,
    flow_index_n: float = 1.0,
    yasuda_a: float = 2.0,
) -> float:
    """Modèle de Carreau-Yasuda : η = η∞ + (η₀ − η∞)·[1 + (λγ̇)^a]^((n−1)/a).

    Forme générale ; les défauts (η∞ = 0, a = 2) reproduisent EXACTEMENT
    l'équation imposée par le manager (Gmail_modele_thermique.pdf §4) :
        η(γ̇) = η₀·[1 + (λγ̇)²]^((n−1)/2)

    - γ̇ → 0   : η → η₀ (plateau newtonien bas cisaillement).
    - γ̇ → ∞   : η → η∞ (plateau haut cisaillement, 0 par défaut).
    - n < 1    : rhéofluidifiant. a règle la netteté de la transition (Yasuda).
    Fonction PURE et finie pour tout γ̇ ≥ 0 (contrairement à la loi puissance).
    """
    factor = (1.0 + (relax_time_s * shear_rate_s) ** yasuda_a) ** (
        (flow_index_n - 1.0) / yasuda_a
    )
    return eta_inf + (eta_zero - eta_inf) * factor


def arrhenius_temperature_factor(
    temp_c: float, activation_energy_j_mol: float, tref_c: float = 20.0
) -> float:
    """Facteur de décalage thermique a_T (Arrhenius).

        a_T = exp( (Ea/R) · (1/T − 1/Tref) )    avec T, Tref en kelvin.

    - a_T = 1 à T = Tref.
    - Ea > 0 et T > Tref → a_T < 1 (la viscosité diminue quand on chauffe).
    """
    t_k = temp_c + 273.15
    tref_k = tref_c + 273.15
    return math.exp(
        (activation_energy_j_mol / GAS_CONSTANT_J_MOL_K) * (1.0 / t_k - 1.0 / tref_k)
    )


def apply_temperature_shift(viscosity: float, temperature_factor: float) -> float:
    """Applique le décalage thermique : η(T) = a_T · η(Tref)."""
    return viscosity * temperature_factor
