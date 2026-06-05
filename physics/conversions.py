"""conversions.py — conversions d'unités et grandeurs dérivées (PURES).

Socle commun de l'agent procédé. Aucune dépendance, aucun état, aucune lecture
disque. Toutes les fonctions sont des transformations algébriques exactes ;
elles n'imposent pas de validation métier (les bornes/erreurs relèvent des
couches supérieures).

Conventions internes Rondol (cf. app/screw_logic.py) :
  - vitesse vis exprimée en tr/min (rpm) côté HMI, tr/s (rps) côté calcul ;
  - débits feeder en g/min côté HMI, g/s côté calcul (screw_logic L486-489) ;
  - températures en °C côté HMI, Tref = 20 °C (screw_logic.TREF).
"""

from __future__ import annotations

import math

# Zéro absolu (°C) — référence pour les conversions de température.
ABSOLUTE_ZERO_C: float = -273.15


# ---------------------------------------------------------------------------
# Vitesse de rotation
# ---------------------------------------------------------------------------
def rpm_to_rps(rpm: float) -> float:
    """Tours/minute → tours/seconde (screw_logic L486 : n_rps = rpm / 60)."""
    return rpm / 60.0


def rps_to_rpm(rps: float) -> float:
    """Tours/seconde → tours/minute."""
    return rps * 60.0


# ---------------------------------------------------------------------------
# Débits massiques
# ---------------------------------------------------------------------------
def g_per_min_to_g_per_s(flow_g_per_min: float) -> float:
    """g/min → g/s (screw_logic._params_from_hmi : feed/60)."""
    return flow_g_per_min / 60.0


def g_per_s_to_g_per_min(flow_g_per_s: float) -> float:
    """g/s → g/min."""
    return flow_g_per_s * 60.0


def g_per_h_to_g_per_s(flow_g_per_h: float) -> float:
    """g/h → g/s (unité de calibration feeder, references/manager_requirements)."""
    return flow_g_per_h / 3600.0


def g_per_s_to_kg_per_h(flow_g_per_s: float) -> float:
    """g/s → kg/h (base SME : ṁ en kg/h, cf. screw_adapter L132)."""
    return flow_g_per_s * 3.6


def kg_per_h_to_g_per_s(flow_kg_per_h: float) -> float:
    """kg/h → g/s."""
    return flow_kg_per_h / 3.6


# ---------------------------------------------------------------------------
# Température
# ---------------------------------------------------------------------------
def celsius_to_kelvin(temp_c: float) -> float:
    """°C → K."""
    return temp_c - ABSOLUTE_ZERO_C


def kelvin_to_celsius(temp_k: float) -> float:
    """K → °C."""
    return temp_k + ABSOLUTE_ZERO_C


# ---------------------------------------------------------------------------
# Volume / pression
# ---------------------------------------------------------------------------
def cm3_to_m3(volume_cm3: float) -> float:
    """cm³ → m³."""
    return volume_cm3 * 1.0e-6


def m3_to_cm3(volume_m3: float) -> float:
    """m³ → cm³."""
    return volume_m3 * 1.0e6


def bar_to_pa(pressure_bar: float) -> float:
    """bar → Pa."""
    return pressure_bar * 1.0e5


def pa_to_bar(pressure_pa: float) -> float:
    """Pa → bar."""
    return pressure_pa * 1.0e-5


# ---------------------------------------------------------------------------
# Grandeurs dérivées
# ---------------------------------------------------------------------------
def volumetric_flow_cm3_s(mass_flow_g_per_s: float, density_g_per_cm3: float) -> float:
    """Débit volumique Q = ṁ / ρ (g/s ÷ g/cm³ → cm³/s).

    Reproduit la relation screw_logic L533 (qvol = flow_g_s / bulk_density).
    Renvoie 0.0 si la densité est nulle (pas de division par zéro), cohérent
    avec la garde `bulk_density > 0` du Network 7.
    """
    if density_g_per_cm3 <= 0.0:
        return 0.0
    return mass_flow_g_per_s / density_g_per_cm3


def apparent_shear_rate_s(
    rpm: float, diameter_mm: float, channel_depth_mm: float
) -> float:
    """Taux de cisaillement apparent γ̇ ≈ π·D·N / h (s⁻¹).

    Approximation drag-flow classique : vitesse tangentielle en surface de vis
    (π·D·N) divisée par la profondeur de chenal h. D et h en mm (le rapport est
    sans dimension), N en tr/s. Renvoie 0.0 si h ≤ 0.
    """
    if channel_depth_mm <= 0.0:
        return 0.0
    n_rps = rpm_to_rps(rpm)
    tangential_velocity = math.pi * diameter_mm * n_rps  # mm/s
    return tangential_velocity / channel_depth_mm
