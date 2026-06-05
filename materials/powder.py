"""powder.py — descripteurs de poudres / lits granulaires (PUR).

Modélise les grandeurs bulk utilisées par le Network 7 (densité apparente,
correction thermique) et quelques grandeurs de tassement utiles à la rhéologie
des suspensions chargées (mixing_rules.krieger_dougherty_viscosity).

Correction thermique de densité — IDENTIQUE à screw_logic L530-532 :
    ρ(T) = ρ₀ / (1 + α·(T − Tref))
où α = coefficient de dilatation thermique apparent (thermal_exp), Tref = 20 °C.

Les presets POWDERS sont NOMINAUX (ordres de grandeur littérature batterie
LFP/LATP) et doivent être recalibrés sur les fiches matière / essais réels.
"""

from __future__ import annotations

from dataclasses import dataclass

# Température de référence (°C) — alignée sur screw_logic.TREF.
TREF_C: float = 20.0


@dataclass(frozen=True)
class Powder:
    """Descripteur d'une poudre.

    Attributs :
      name              : identifiant lisible.
      bulk_density_g_cm3 : densité apparente (tassée/versée) à Tref.
      true_density_g_cm3 : densité vraie (squelette solide).
      thermal_exp_per_k  : coefficient de dilatation thermique apparent (1/K)
                           utilisé dans la correction screw_logic L530.
      cp_j_per_g_k      : chaleur spécifique massique (J·g⁻¹·K⁻¹). Requise par
                           l'équation thermique manager E6 (T_real ∝ 1/(ṁ·Cp)).
                           NOMINAL, à recalibrer. 0.0 = inconnu.
      d50_um            : diamètre médian (µm), optionnel (None si inconnu).
    """
    name: str
    bulk_density_g_cm3: float
    true_density_g_cm3: float
    thermal_exp_per_k: float = 0.0
    cp_j_per_g_k: float = 0.0
    d50_um: float | None = None


def bulk_density_at_temp(
    powder: Powder, temp_c: float, tref_c: float = TREF_C
) -> float:
    """Densité apparente corrigée en température : ρ₀ / (1 + α·(T − Tref)).

    Reproduit screw_logic L530-532. À T = Tref, renvoie exactement la densité
    apparente nominale. Un dénominateur ≤ 0 (cas non physique) est ramené à la
    densité nominale pour rester défensif.
    """
    denom = 1.0 + powder.thermal_exp_per_k * (temp_c - tref_c)
    if denom <= 0.0:
        return powder.bulk_density_g_cm3
    return powder.bulk_density_g_cm3 / denom


def packing_fraction(powder: Powder) -> float:
    """Fraction volumique solide du lit : φ = ρ_bulk / ρ_true ∈ (0, 1].

    Renvoie 0.0 si la densité vraie est nulle (garde anti-division).
    """
    if powder.true_density_g_cm3 <= 0.0:
        return 0.0
    return powder.bulk_density_g_cm3 / powder.true_density_g_cm3


def void_fraction(powder: Powder) -> float:
    """Fraction de vide du lit : 1 − φ."""
    return 1.0 - packing_fraction(powder)


# ---------------------------------------------------------------------------
# Presets NOMINAUX — recette batterie (poster 15 mai 2026 : LFP/LATP Li)
# Valeurs littérature, ordre de grandeur. À RECALIBRER sur fiches matière.
# ---------------------------------------------------------------------------
POWDERS: dict[str, Powder] = {
    "LFP": Powder("LiFePO4 (LFP)", bulk_density_g_cm3=1.20,
                  true_density_g_cm3=3.60, thermal_exp_per_k=2.0e-5,
                  cp_j_per_g_k=1.00, d50_um=3.0),
    "LATP": Powder("Li1.3Al0.3Ti1.7(PO4)3 (LATP)", bulk_density_g_cm3=1.00,
                   true_density_g_cm3=2.95, thermal_exp_per_k=2.0e-5,
                   cp_j_per_g_k=0.80, d50_um=2.0),
    "graphite": Powder("Graphite", bulk_density_g_cm3=0.70,
                       true_density_g_cm3=2.26, thermal_exp_per_k=3.0e-5,
                       cp_j_per_g_k=0.71, d50_um=15.0),
    "PVDF": Powder("PVDF (liant)", bulk_density_g_cm3=0.45,
                   true_density_g_cm3=1.78, thermal_exp_per_k=8.0e-5,
                   cp_j_per_g_k=1.30, d50_um=0.5),
}
