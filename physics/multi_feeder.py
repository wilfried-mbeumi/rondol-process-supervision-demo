"""multi_feeder.py — étalonnage MULTI-feeder (PUR), au-dessus de feeder_flow.

Une machine réelle peut avoir plusieurs feeders. Chacun a son RPM + coefficient
d'étalonnage (g/h/RPM) → son débit propre. Ce module compose les débits :

  - feeder désactivé            → débit 0, statut DISABLED (exclu du total) ;
  - feeder actif sans coeff/≤0  → débit NON calculable, statut CALIBRATION_MISSING
                                  (exclu du total, jamais remplacé par 0 en silence) ;
  - feeder actif + coeff valide → débit = resolve_feeder_flow(rpm, coeff), statut OK.

  débit_total = somme des SEULS feeders OK. Si AUCUN feeder OK → total non
  calculable (None). Si ≥1 feeder actif est non étalonné → `has_uncalibrated_active`
  (l'appelant doit avertir : le total est incomplet).

Module PUR : aucune dépendance Streamlit / disque. Réutilise feeder_flow (aucune
nouvelle formule de débit, aucune constante PLC touchée).
"""

from __future__ import annotations

from dataclasses import dataclass

from physics.feeder_flow import (
    MAX_FEEDER_FLOW_G_H,
    FeederFlow,
    resolve_feeder_flow,
)

# Statuts d'un feeder dans le banc.
STATUS_OK = "OK"
STATUS_CALIBRATION_MISSING = "CALIBRATION_MISSING"
STATUS_DISABLED = "DISABLED"


@dataclass(frozen=True)
class FeederCalibration:
    """Entrée d'étalonnage d'un feeder (saisie opérateur)."""
    feeder_id: int
    label: str = ""
    enabled: bool = False
    rpm: float = 0.0
    coeff_g_h_per_rpm: float | None = None      # None/≤0 = non renseigné
    material_label: str = ""                     # optionnel (USER_INPUT), jamais inventé
    material_source: str = "NOT_AVAILABLE"


@dataclass(frozen=True)
class FeederLine:
    """Débit résolu d'un feeder + statut + traçabilité."""
    feeder_id: int
    label: str
    enabled: bool
    status: str
    flow: FeederFlow
    material_label: str
    material_source: str

    @property
    def flow_g_h(self) -> float | None:
        """Débit g/h : 0 si désactivé, None si non calculable, valeur si OK."""
        if self.status == STATUS_DISABLED:
            return 0.0
        if self.status == STATUS_OK:
            return self.flow.effective_g_h
        return None  # CALIBRATION_MISSING

    @property
    def flow_g_min(self) -> float | None:
        v = self.flow_g_h
        return None if v is None else v / 60.0

    @property
    def flow_g_s(self) -> float | None:
        v = self.flow_g_h
        return None if v is None else v / 3600.0


@dataclass(frozen=True)
class MultiFeederResult:
    """Banc feeder résolu : lignes + total des feeders calculables."""
    lines: tuple[FeederLine, ...]
    total_g_h: float | None          # somme des OK ; None si aucun feeder OK
    total_calculable: bool           # True si ≥1 feeder OK
    has_uncalibrated_active: bool     # ≥1 feeder actif sans étalonnage

    @property
    def total_g_min(self) -> float | None:
        return None if self.total_g_h is None else self.total_g_h / 60.0

    @property
    def total_g_s(self) -> float | None:
        return None if self.total_g_h is None else self.total_g_h / 3600.0

    @property
    def ok_lines(self) -> tuple[FeederLine, ...]:
        return tuple(l for l in self.lines if l.status == STATUS_OK)


def _resolve_one(cal: FeederCalibration,
                 max_machine_g_h: float = MAX_FEEDER_FLOW_G_H) -> FeederLine:
    if not cal.enabled:
        status = STATUS_DISABLED
        flow = resolve_feeder_flow(cal.rpm, None, max_machine_g_h)
    elif cal.coeff_g_h_per_rpm is None or float(cal.coeff_g_h_per_rpm) <= 0.0:
        status = STATUS_CALIBRATION_MISSING
        flow = resolve_feeder_flow(cal.rpm, None, max_machine_g_h)
    else:
        status = STATUS_OK
        flow = resolve_feeder_flow(cal.rpm, cal.coeff_g_h_per_rpm, max_machine_g_h)
    return FeederLine(
        feeder_id=cal.feeder_id, label=cal.label, enabled=cal.enabled,
        status=status, flow=flow,
        material_label=cal.material_label, material_source=cal.material_source,
    )


def resolve_multi_feeder(
    calibrations: list[FeederCalibration] | tuple[FeederCalibration, ...],
    max_machine_g_h: float = MAX_FEEDER_FLOW_G_H,
) -> MultiFeederResult:
    """Résout le banc feeder : un FeederLine par feeder + total des OK.

    Le total n'additionne QUE les feeders OK ; il est None si aucun feeder OK
    (débit non calculable). `has_uncalibrated_active` signale un feeder actif non
    étalonné (total incomplet → l'appelant avertit).
    """
    lines = tuple(_resolve_one(c, max_machine_g_h) for c in calibrations)
    ok = [l for l in lines if l.status == STATUS_OK]
    total = sum((l.flow.effective_g_h or 0.0) for l in ok) if ok else None
    has_uncalibrated_active = any(l.status == STATUS_CALIBRATION_MISSING for l in lines)
    return MultiFeederResult(
        lines=lines,
        total_g_h=total,
        total_calculable=bool(ok),
        has_uncalibrated_active=has_uncalibrated_active,
    )
