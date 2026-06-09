"""feeder_flow.py — étalonnage feeder RPM → débit réel (PUR).

Exigence manager (mail 2026-06-08) : l'opérateur ne saisit pas un débit direct,
mais une **vitesse feeder (RPM)** + un **coefficient d'étalonnage externe**
(g/h par RPM). Le débit réel s'en déduit :

    débit_g_h   = feeder_rpm × coefficient_g_h_per_rpm
    débit_g_min = débit_g_h / 60
    débit_g_s   = débit_g_h / 3600

Exemples :
  - 30 RPM × 17 g/h/RPM = 510 g/h = 8,5 g/min (exemple manager 2026-06-09).
  - 100 RPM × 25 g/h/RPM = 2500 g/h (limite haute machine).

Règles strictes :
  - le coefficient g/h/RPM N'EST PAS une vérité universelle : il doit être
    SAISI. Sans coefficient → débit réel NON calculable (on ne devine pas).
  - la machine est limitée à `MAX_FEEDER_FLOW_G_H` (= 2500 g/h, validation
    manager 2026-06-09 — élargi par rapport à l'ancien plafond 300 g/h). Au-delà
    de cette borne, le débit EFFECTIF (utilisé dans les calculs) est plafonné,
    mais le débit DEMANDÉ est conservé pour l'affichage + un avertissement
    (jamais de plafonnement silencieux).
  - constante centralisée : aucun « 2500 » épars dans le code.

Module PUR : aucune dépendance Streamlit / disque.
"""

from __future__ import annotations

from dataclasses import dataclass

from physics.conversions import (
    g_per_h_to_g_per_min,
    g_per_h_to_g_per_s,
)

# Débit maximum machine validé (g/h) — exigence manager 2026-06-09. Centralisé
# ici. Ancien plafond (300 g/h) levé : le nouvel outil étalonné permet des
# valeurs plus précises ; la limite réelle de la machine est ~2500 g/h.
MAX_FEEDER_FLOW_G_H: float = 2500.0

# Coefficient d'étalonnage d'EXEMPLE/démonstration (g/h par RPM) — exemple
# manager 2026-06-09 (30 RPM × 17 = 510 g/h). N'EST PAS une vérité : sert
# uniquement de valeur de démo pré-remplie quand on l'expose explicitement
# comme « exemple ».
EXAMPLE_CALIBRATION_G_H_PER_RPM: float = 17.0


@dataclass(frozen=True)
class FeederFlow:
    """Résultat d'étalonnage feeder — débit réel + traçabilité.

    Attributs :
      calibrated         : True si un coefficient d'étalonnage exploitable a été
                           fourni (> 0). Sinon le débit réel est inconnu.
      feeder_rpm         : vitesse feeder saisie (RPM).
      calibration_g_h_per_rpm : coefficient g/h par RPM (None si non renseigné).
      requested_g_h      : débit DEMANDÉ = rpm × coeff (None si non calibré).
      effective_g_h      : débit EFFECTIF utilisé en calcul = min(demandé, max
                           machine) (None si non calibré).
      clamped            : True si le demandé dépassait le max machine.
      max_machine_g_h    : plafond machine appliqué.
    """
    calibrated: bool
    feeder_rpm: float
    calibration_g_h_per_rpm: float | None
    requested_g_h: float | None
    effective_g_h: float | None
    clamped: bool
    max_machine_g_h: float = MAX_FEEDER_FLOW_G_H

    # --- Conversions du débit EFFECTIF (None si non calibré) ---
    @property
    def effective_g_min(self) -> float | None:
        if self.effective_g_h is None:
            return None
        return g_per_h_to_g_per_min(self.effective_g_h)

    @property
    def effective_g_s(self) -> float | None:
        if self.effective_g_h is None:
            return None
        return g_per_h_to_g_per_s(self.effective_g_h)

    @property
    def requested_g_min(self) -> float | None:
        if self.requested_g_h is None:
            return None
        return g_per_h_to_g_per_min(self.requested_g_h)


def resolve_feeder_flow(
    feeder_rpm: float,
    calibration_g_h_per_rpm: float | None,
    max_machine_g_h: float = MAX_FEEDER_FLOW_G_H,
) -> FeederFlow:
    """Calcule le débit réel feeder depuis RPM + coefficient d'étalonnage.

    Sans coefficient exploitable (None ou ≤ 0) → `calibrated=False` et tous les
    débits à None (on ne devine JAMAIS le débit réel).

    Avec coefficient → débit demandé = rpm × coeff ; débit effectif = plafonné
    à `max_machine_g_h` (clamp explicite, jamais silencieux : `clamped` le dit).
    """
    rpm = max(0.0, float(feeder_rpm))
    if calibration_g_h_per_rpm is None or float(calibration_g_h_per_rpm) <= 0.0:
        return FeederFlow(
            calibrated=False,
            feeder_rpm=rpm,
            calibration_g_h_per_rpm=None,
            requested_g_h=None,
            effective_g_h=None,
            clamped=False,
            max_machine_g_h=max_machine_g_h,
        )

    coeff = float(calibration_g_h_per_rpm)
    requested = rpm * coeff
    clamped = requested > max_machine_g_h
    effective = min(requested, max_machine_g_h)
    return FeederFlow(
        calibrated=True,
        feeder_rpm=rpm,
        calibration_g_h_per_rpm=coeff,
        requested_g_h=requested,
        effective_g_h=effective,
        clamped=clamped,
        max_machine_g_h=max_machine_g_h,
    )
