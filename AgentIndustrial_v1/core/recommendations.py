"""
recommendations.py — Recommandations actionnables (V1 rule-based).

À chaque alerte du moteur de règles correspond une (ou plusieurs)
recommandation concrète :
  - déplacement feeder (move_feeder)
  - réduction débit  (reduce_flow)
  - ajustement température (adjust_temperature)
  - modification profil vis (modify_screw_profile)
  - changement vitesse vis (change_screw_speed)

Chaque reco contient une **delta** (avant → après) pour que l'opérateur sache
exactement quoi faire au pupitre.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cooling import compute_cooling, zone_index
from .feeders import FEEDER_POSITIONS, FeederSpec
from .process import (
    DEFAULT_ZONE_TARGETS_C,
    FF_TARGET_HIGH,
    FF_TARGET_LOW,
    PROCESS_ZONE_ORDER,
    ProcessState,
    SME_WARNING_KWH_PER_KG,
    THERMAL_REG_BAND_C,
)
from . import rules as _rules_mod
from .rules import Alert, _b

# Garde « pas d'élément inventé » (règle manager) — source canonique pure dans
# screw_logic. Bootstrap sys.path (app/) identique à screw_adapter pour import nu.
import sys as _sys
from pathlib import Path as _Path

_APP_DIR = _Path(__file__).resolve().parent.parent.parent / "app"
if str(_APP_DIR) not in _sys.path:
    _sys.path.insert(0, str(_APP_DIR))
try:  # pragma: no cover - dépend du bootstrap sys.path
    from screw_logic import recommendation_cites_absent_element as _cites_absent
except Exception:  # pragma: no cover
    _cites_absent = None


# ---------------------------------------------------------------------------
# Catégories — utilisées pour le grouping UI
# ---------------------------------------------------------------------------
CAT_FEEDER_MOVE = "feeder_move"
CAT_FLOW = "flow_reduce"
CAT_TEMPERATURE = "temperature"
CAT_SCREW_PROFILE = "screw_profile"
CAT_SCREW_SPEED = "screw_speed"
CAT_OTHER = "other"

_CAT_LABELS_FR: dict[str, str] = {
    CAT_FEEDER_MOVE: "Déplacement feeder",
    CAT_FLOW: "Ajustement débit",
    CAT_TEMPERATURE: "Ajustement température",
    CAT_SCREW_PROFILE: "Modification profil vis",
    CAT_SCREW_SPEED: "Vitesse vis",
    CAT_OTHER: "Autre",
}
_CAT_LABELS_EN: dict[str, str] = {
    CAT_FEEDER_MOVE: "Feeder move",
    CAT_FLOW: "Flow adjustment",
    CAT_TEMPERATURE: "Temperature adjustment",
    CAT_SCREW_PROFILE: "Screw profile modification",
    CAT_SCREW_SPEED: "Screw speed",
    CAT_OTHER: "Other",
}
_CAT_LABELS = _CAT_LABELS_EN

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


@dataclass(frozen=True)
class Recommendation:
    """Action recommandée par l'agent — toujours chiffrée."""
    code: str
    category: str
    severity: str               # hérite de l'alerte source
    title: str
    rationale: str              # pourquoi cette action résout le problème
    action: str                 # imperative ("Réduire feeder #1 de ...")
    delta_label: str            # "30 g/min → 22 g/min"
    confidence: str = CONFIDENCE_MEDIUM
    linked_alert_code: str = ""

    @property
    def category_label(self) -> str:
        labels = _CAT_LABELS_EN if _rules_mod._LANG == "en" else _CAT_LABELS_FR
        return labels.get(self.category, self.category)


# ---------------------------------------------------------------------------
# Générateurs par code d'alerte
# ---------------------------------------------------------------------------
def _find_feeder(state: ProcessState, hint_target: str) -> FeederSpec | None:
    """Retrouve le feeder ciblé par une alerte (target ressemble à 'Feeder #2')."""
    for f in state.feeders:
        if f"#{f.feeder_id}" in hint_target:
            return f
    return None


def _next_allowed_position(f: FeederSpec) -> str:
    """1ère position autorisée par la matière du feeder (ordre FEEDER_POSITIONS)."""
    allowed = set(f.material.allowed_positions)
    for p in FEEDER_POSITIONS:
        if p in allowed:
            return p
    return "Z3"  # fallback raisonnable


def _from_feeder_location(state: ProcessState, alert: Alert) -> list[Recommendation]:
    f = _find_feeder(state, alert.target)
    if f is None:
        return []
    target_pos = _next_allowed_position(f)
    return [Recommendation(
        code="REC_MOVE_FEEDER",
        category=CAT_FEEDER_MOVE,
        severity=alert.severity,
        title=_b(
            f"Déplacer feeder #{f.feeder_id} → {target_pos}",
            f"Move feeder #{f.feeder_id} → {target_pos}",
        ),
        rationale=_b(
            f"La phase {f.material.phase} ne peut être injectée en "
            f"{f.position} (avant fusion / zone inadaptée). "
            f"{target_pos} est la 1ère position physiquement valide.",
            f"Phase {f.material.phase} cannot be injected at "
            f"{f.position} (before melting / unsuitable zone). "
            f"{target_pos} is the first physically valid position.",
        ),
        action=_b(
            f"Déplacer le point d'injection du feeder #{f.feeder_id} "
            f"({f.material.label_fr}) vers la position {target_pos}.",
            f"Move the injection point of feeder #{f.feeder_id} "
            f"({f.material.label_fr}) to position {target_pos}.",
        ),
        delta_label=f"{f.position} → {target_pos}",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


def _from_thermal_high(state: ProcessState, alert: Alert) -> list[Recommendation]:
    f = _find_feeder(state, alert.target)
    if f is None:
        return []
    t_now = state.temp_at(f.position)
    t_max = f.effective_t_max_C()
    t_target = max(0.0, t_max - 10.0)
    out: list[Recommendation] = []
    # Option 1 : baisser la zone
    if f.position != "Z0":
        out.append(Recommendation(
            code="REC_REDUCE_T",
            category=CAT_TEMPERATURE,
            severity=alert.severity,
            title=_b(
                f"Réduire T_{f.position}",
                f"Reduce T_{f.position}",
            ),
            rationale=_b(
                f"Borne haute matière {f.material.label_fr} = {t_max:.0f} °C. "
                f"Cible 10 °C de marge sous la borne pour absorber les "
                f"variations de procédé.",
                f"Material upper limit {f.material.label_fr} = {t_max:.0f} °C. "
                f"Target 10 °C margin below the limit to absorb "
                f"process variations.",
            ),
            action=_b(
                f"Abaisser la consigne {f.position} jusqu'à environ {t_target:.0f} °C.",
                f"Lower the {f.position} setpoint to approximately {t_target:.0f} °C.",
            ),
            delta_label=f"{t_now:.0f} °C → {t_target:.0f} °C",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ))
    # Option 2 : déplacer le feeder vers une zone plus froide
    cooler = _coolest_allowed_position(state, f)
    if cooler and cooler != f.position:
        out.append(Recommendation(
            code="REC_MOVE_FEEDER_THERMAL",
            category=CAT_FEEDER_MOVE,
            severity=alert.severity,
            title=_b(
                f"Déplacer feeder #{f.feeder_id} vers zone plus froide",
                f"Move feeder #{f.feeder_id} to cooler zone",
            ),
            rationale=_b(
                f"Position {cooler} = T plus basse, compatible avec la borne "
                f"effective {t_max:.0f} °C.",
                f"Position {cooler} = lower T, compatible with the effective "
                f"limit {t_max:.0f} °C.",
            ),
            action=_b(
                f"Déplacer feeder #{f.feeder_id} de {f.position} vers {cooler} "
                f"si la chimie le permet.",
                f"Move feeder #{f.feeder_id} from {f.position} to {cooler} "
                f"if chemistry allows.",
            ),
            delta_label=f"{f.position} → {cooler}",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ))
    return out


def _coolest_allowed_position(state: ProcessState, f: FeederSpec) -> str | None:
    allowed = f.material.allowed_positions
    if not allowed:
        return None
    return min(allowed, key=lambda p: state.temp_at(p))


def _from_thermal_low(state: ProcessState, alert: Alert) -> list[Recommendation]:
    f = _find_feeder(state, alert.target)
    if f is None:
        return []
    t_now = state.temp_at(f.position)
    t_min = f.effective_t_min_C()
    t_target = t_min + 10.0
    return [Recommendation(
        code="REC_RAISE_T",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            f"Augmenter T_{f.position}",
            f"Increase T_{f.position}",
        ),
        rationale=_b(
            f"Sous la borne basse opérationnelle ({t_min:.0f} °C) — "
            f"risque condensation / matière inerte.",
            f"Below the operational lower bound ({t_min:.0f} °C) — "
            f"risk of condensation / inert material.",
        ),
        action=_b(
            f"Remonter la consigne {f.position} à au moins {t_target:.0f} °C.",
            f"Raise the {f.position} setpoint to at least {t_target:.0f} °C.",
        ),
        delta_label=f"{t_now:.0f} °C → {t_target:.0f} °C",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


def _from_powder_overload(state: ProcessState, alert: Alert) -> list[Recommendation]:
    # Trouve le plus gros feeder solide à réduire.
    solids = [f for f in state.feeders if f.enabled and f.is_solid]
    if not solids:
        return []
    biggest = max(solids, key=lambda f: f.mass_flow_g_per_min)
    new_flow = biggest.mass_flow_g_per_min * 0.80
    new_rpm = state.screw_rpm * 1.20
    return [
        Recommendation(
            code="REC_REDUCE_FLOW",
            category=CAT_FLOW,
            severity=alert.severity,
            title=_b(
                f"Réduire débit feeder #{biggest.feeder_id}",
                f"Reduce feeder #{biggest.feeder_id} flow",
            ),
            rationale=_b(
                "Surcharge solide → ramener à 80 % du débit pour rétablir une "
                "marge de capacité et éviter le surcouple.",
                "Solid overload → bring back to 80 % of flow to restore "
                "capacity margin and avoid over-torque.",
            ),
            action=_b(
                f"Réduire le débit du feeder #{biggest.feeder_id} "
                f"({biggest.material.label_fr}) de 20 %.",
                f"Reduce feeder #{biggest.feeder_id} "
                f"({biggest.material.label_fr}) flow by 20 %.",
            ),
            delta_label=(
                f"{biggest.mass_flow_g_per_min:.0f} → {new_flow:.0f} g/min"
            ),
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_INCREASE_RPM",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b(
                "Augmenter la vitesse vis",
                "Increase screw speed",
            ),
            rationale=_b(
                "À débit constant, une vitesse vis plus élevée diminue le "
                "Fill Factor et restaure de la capacité de transport.",
                "At constant flow, a higher screw speed reduces the "
                "Fill Factor and restores transport capacity.",
            ),
            action=_b(
                f"Monter la vitesse vis à {new_rpm:.0f} rpm si le procédé le permet.",
                f"Raise screw speed to {new_rpm:.0f} rpm if the process allows.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {new_rpm:.0f} rpm",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
    ]


def _from_ff_high(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 1.15
    return [
        Recommendation(
            code="REC_REDUCE_FLOW_FF",
            category=CAT_FLOW,
            severity=alert.severity,
            title=_b("Réduire le débit cumulé", "Reduce cumulative flow"),
            rationale=_b(
                f"FF visé : {FF_TARGET_LOW * 100:.0f}-{FF_TARGET_HIGH * 100:.0f} %. "
                f"Baisser le débit global de 15 % pour ramener FF dans la cible.",
                f"Target FF: {FF_TARGET_LOW * 100:.0f}-{FF_TARGET_HIGH * 100:.0f} %. "
                f"Reduce overall flow by 15 % to bring FF back to target.",
            ),
            action=_b(
                "Réduire de 15 % le feeder solide principal.",
                "Reduce the main solid feeder by 15 %.",
            ),
            delta_label=f"FF {state.kpis.fill_factor * 100:.0f} % → ~{(state.kpis.fill_factor * 0.85) * 100:.0f} %",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_RPM_UP_FF",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b("Augmenter la vitesse vis", "Increase screw speed"),
            rationale=_b(
                "FF diminue ~ linéairement avec rpm à débit constant.",
                "FF decreases approximately linearly with rpm at constant flow.",
            ),
            action=_b(
                f"Passer à {rpm_new:.0f} rpm pour soulager la vis.",
                f"Switch to {rpm_new:.0f} rpm to relieve the screw.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
    ]


def _from_ff_low(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 0.85
    return [
        Recommendation(
            code="REC_RPM_DOWN_FF",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b("Réduire la vitesse vis", "Reduce screw speed"),
            rationale=_b(
                "Vis trop rapide / sous-alimentée — réduire rpm augmente FF.",
                "Screw too fast / starved — reducing rpm increases FF.",
            ),
            action=_b(
                f"Descendre à {rpm_new:.0f} rpm.",
                f"Lower to {rpm_new:.0f} rpm.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_INCREASE_FLOW",
            category=CAT_FLOW,
            severity=alert.severity,
            title=_b("Augmenter le débit solide", "Increase solid flow"),
            rationale=_b(
                "Augmenter le débit feeder principal pour ramener FF dans la "
                "cible compounding.",
                "Increase main feeder flow to bring FF back to the "
                "compounding target.",
            ),
            action=_b(
                "Monter le feeder principal de 15-20 %.",
                "Increase the main feeder by 15-20 %.",
            ),
            delta_label=f"FF {state.kpis.fill_factor * 100:.0f} % → cible {FF_TARGET_LOW * 100:.0f}-{FF_TARGET_HIGH * 100:.0f} %",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
    ]


def _from_sme_high(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 0.85
    return [
        Recommendation(
            code="REC_SOFTEN_PROFILE",
            category=CAT_SCREW_PROFILE,
            severity=alert.severity,
            title=_b("Adoucir le profil de mélange", "Soften mixing profile"),
            rationale=_b(
                "SME élevé = cisaillement excessif. Remplacer une partie des "
                "kneading 90° par 45° ou 30° réduit l'énergie spécifique sans "
                "détériorer la dispersion.",
                "High SME = excessive shearing. Replacing some "
                "kneading 90° with 45° or 30° reduces specific energy without "
                "deteriorating dispersion.",
            ),
            action=_b(
                "Substituer 2 × Kneading 90° par 2 × Kneading 45° en zone "
                "centrale (Z3-Z4).",
                "Replace 2 × Kneading 90° with 2 × Kneading 45° in central "
                "zone (Z3-Z4).",
            ),
            delta_label="Kneading 90° (×2) → Kneading 45° (×2)",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_REDUCE_RPM_SME",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b("Réduire la vitesse vis", "Reduce screw speed"),
            rationale=_b(
                "SME ∝ rpm. Une baisse de 15 % de rpm donne ~15 % de baisse SME.",
                "SME ∝ rpm. A 15 % rpm reduction gives ~15 % SME reduction.",
            ),
            action=_b(
                f"Réduire la vitesse vis à {rpm_new:.0f} rpm.",
                f"Reduce screw speed to {rpm_new:.0f} rpm.",
            ),
            delta_label=f"SME {state.kpis.sme_kwh_per_kg:.2f} → ~{state.kpis.sme_kwh_per_kg * 0.85:.2f} kWh/kg",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
    ]


def _from_rt_short(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 0.80
    return [
        Recommendation(
            code="REC_LONGER_SCREW",
            category=CAT_SCREW_PROFILE,
            severity=alert.severity,
            title=_b("Allonger le profil vis", "Extend screw profile"),
            rationale=_b(
                "RT < 5 s = mélange insuffisant. Ajouter des éléments augmente la résidence.",
                "RT < 5 s = insufficient mixing. Adding elements increases residence.",
            ),
            action=_b(
                "Passer à une config 30 ou 40 éléments selon disponibilité.",
                "Switch to a 30 or 40 element config depending on availability.",
            ),
            delta_label=f"RT {state.kpis.residence_time_s:.1f} s → +50 % (cible)",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_REDUCE_RPM_RT",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b("Réduire la vitesse vis", "Reduce screw speed"),
            rationale=_b(
                "rpm bas = RT plus long (à débit constant).",
                "Lower rpm = longer RT (at constant flow).",
            ),
            action=_b(
                f"Descendre à {rpm_new:.0f} rpm.",
                f"Lower to {rpm_new:.0f} rpm.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
    ]


def _from_rt_long(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 1.20
    return [Recommendation(
        code="REC_INCREASE_RPM_RT",
        category=CAT_SCREW_SPEED,
        severity=alert.severity,
        title=_b("Augmenter la vitesse vis", "Increase screw speed"),
        rationale=_b(
            "RT trop long = matière sur-cisaillée. rpm plus haut = RT plus court.",
            "RT too long = over-sheared material. Higher rpm = shorter RT.",
        ),
        action=_b(
            f"Monter à {rpm_new:.0f} rpm.",
            f"Raise to {rpm_new:.0f} rpm.",
        ),
        delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


def _from_thermal_inverted(state: ProcessState, alert: Alert) -> list[Recommendation]:
    t_z5 = state.zone_temps_C.get("Z5", 95.0)
    t_target = t_z5
    t_die = state.zone_temps_C.get("die", 110.0)
    return [Recommendation(
        code="REC_DIE_T_ALIGN",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b("Aligner la consigne filière", "Align die setpoint"),
        rationale=_b(
            "En compounding standard, T_die ≤ T_Z5 + 15 °C.",
            "In standard compounding, T_die ≤ T_Z5 + 15 °C.",
        ),
        action=_b(
            f"Régler la filière à environ {t_target:.0f} °C.",
            f"Set die to approximately {t_target:.0f} °C.",
        ),
        delta_label=f"{t_die:.0f} °C → {t_target:.0f} °C",
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_duplicate_position(state: ProcessState, alert: Alert) -> list[Recommendation]:
    # Cible la 2e feeder solide à la même position.
    pos = alert.target.replace("Position ", "").strip()
    solids_here = [
        f for f in state.feeders
        if f.enabled and f.is_solid and f.position == pos
    ]
    if len(solids_here) < 2:
        return []
    candidate = solids_here[1]  # le second à déplacer
    new_pos = "Z3" if pos == "Z0" else "Z2"
    return [Recommendation(
        code="REC_SPLIT_FEEDERS",
        category=CAT_FEEDER_MOVE,
        severity=alert.severity,
        title=_b(
            f"Espacer feeder #{candidate.feeder_id}",
            f"Space out feeder #{candidate.feeder_id}",
        ),
        rationale=_b(
            "Deux solides au même point provoquent agglomération. "
            "Décaler permet une fluidification intermédiaire.",
            "Two solids at the same point cause agglomeration. "
            "Shifting allows intermediate fluidization.",
        ),
        action=_b(
            f"Déplacer feeder #{candidate.feeder_id} en aval.",
            f"Move feeder #{candidate.feeder_id} downstream.",
        ),
        delta_label=f"{pos} → {new_pos}",
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_zone_overheat(state: ProcessState, alert: Alert) -> list[Recommendation]:
    """Surcharge thermique d'une zone (Z5 ou zone testée) — actions chiffrées."""
    m = compute_cooling(state)
    zname = alert.target.replace("Zone ", "").strip()
    zt = m.zones.get(zname)
    if zt is None:
        return []
    tol = THERMAL_REG_BAND_C
    # Consigne à viser : ramener T_est dans la bande → baisser la consigne du
    # surplus (ΔT_dissipation) moins une marge de tolérance.
    drop = max(5.0, zt.dT_C - tol)
    t_new = max(0.0, zt.t_target_C - drop)
    rpm_new = state.screw_rpm * 0.85
    out = [
        Recommendation(
            code="REC_COOL_SETPOINT",
            category=CAT_TEMPERATURE,
            severity=alert.severity,
            title=_b(
                f"Abaisser la consigne {zname}",
                f"Lower {zname} setpoint",
            ),
            rationale=_b(
                f"L'échauffement viscoélastique ajoute +{zt.dT_C:.0f} °C à "
                f"{zname}. Baisser la consigne compense la dissipation pour "
                f"ramener la T réelle dans la bande ±{tol:.0f} °C.",
                f"Viscoelastic heating adds +{zt.dT_C:.0f} °C to "
                f"{zname}. Lowering the setpoint compensates dissipation to "
                f"bring actual T within the ±{tol:.0f} °C band.",
            ),
            action=_b(
                f"Régler la consigne {zname} vers {t_new:.0f} °C (régulation froid).",
                f"Set {zname} setpoint to {t_new:.0f} °C (cooling regulation).",
            ),
            delta_label=f"{zt.t_target_C:.0f} °C → {t_new:.0f} °C",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_RPM_DOWN_THERMAL",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b("Réduire la vitesse vis", "Reduce screw speed"),
            rationale=_b(
                "La dissipation visqueuse ≈ couple × N. −15 % rpm réduit "
                "proportionnellement l'échauffement de la zone.",
                "Viscous dissipation ≈ torque × N. −15 % rpm proportionally "
                "reduces zone heating.",
            ),
            action=_b(
                f"Descendre la vis à {rpm_new:.0f} rpm.",
                f"Lower screw to {rpm_new:.0f} rpm.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm · ΔT −~15 %",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
    ]
    if zname in ("Z4", "Z5", "Z6"):
        out.append(Recommendation(
            code="REC_INSERT_COOLING_ELEMENT",
            category=CAT_SCREW_PROFILE,
            severity=alert.severity,
            title=_b(
                f"Intercaler du convoyage avant {zname}",
                f"Insert conveying before {zname}",
            ),
            rationale=_b(
                "Insérer un bloc de convoyage (forward) entre les éléments de "
                "malaxage crée une fenêtre de refroidissement et casse "
                "l'accumulation thermique du plateau.",
                "Inserting a conveying block (forward) between kneading "
                "elements creates a cooling window and breaks "
                "the thermal buildup of the plateau.",
            ),
            action=_b(
                f"Ajouter 1-2 éléments de convoyage juste en amont de {zname}.",
                f"Add 1-2 conveying elements just upstream of {zname}.",
            ),
            delta_label=_b(
                "Kneading continu → Kneading + convoyage refroid.",
                "Continuous kneading → Kneading + cooling conveying",
            ),
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ))
    return out


def _from_torque_excess(state: ProcessState, alert: Alert) -> list[Recommendation]:
    rpm_new = state.screw_rpm * 0.85
    solids = [f for f in state.feeders if f.enabled and f.is_solid]
    out = [Recommendation(
        code="REC_RPM_DOWN_TORQUE",
        category=CAT_SCREW_SPEED,
        severity=alert.severity,
        title=_b(
            "Réduire la vitesse vis (décharge couple)",
            "Reduce screw speed (torque relief)",
        ),
        rationale=_b(
            "Le couple chute avec la vitesse à débit constant — sécurise le moteur.",
            "Torque drops with speed at constant flow — secures the motor.",
        ),
        action=_b(
            f"Descendre la vis à {rpm_new:.0f} rpm.",
            f"Lower screw to {rpm_new:.0f} rpm.",
        ),
        delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]
    if solids:
        biggest = max(solids, key=lambda f: f.mass_flow_g_per_min)
        new_flow = biggest.mass_flow_g_per_min * 0.85
        out.append(Recommendation(
            code="REC_REDUCE_FLOW_TORQUE",
            category=CAT_FLOW,
            severity=alert.severity,
            title=_b(
                f"Réduire débit feeder #{biggest.feeder_id}",
                f"Reduce feeder #{biggest.feeder_id} flow",
            ),
            rationale=_b(
                "Moins de matière cisaillée ⇒ couple et échauffement réduits.",
                "Less sheared material ⇒ reduced torque and heating.",
            ),
            action=_b(
                f"Réduire le feeder #{biggest.feeder_id} de 15 %.",
                f"Reduce feeder #{biggest.feeder_id} by 15 %.",
            ),
            delta_label=f"{biggest.mass_flow_g_per_min:.0f} → {new_flow:.0f} g/min",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ))
    return out


def _from_instability(state: ProcessState, alert: Alert) -> list[Recommendation]:
    m = compute_cooling(state)
    rpm_new = state.screw_rpm * 0.85
    return [
        Recommendation(
            code="REC_STABILIZE_RPM",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title=_b(
                "Réduire la vitesse pour stabiliser",
                "Reduce speed to stabilize",
            ),
            rationale=_b(
                f"Index instabilité {m.instability_index:.2f} tiré par "
                f"SME/FF/échauffement/couple. Baisser rpm agit sur les quatre "
                f"contributions simultanément.",
                f"Instability index {m.instability_index:.2f} driven by "
                f"SME/FF/heating/torque. Lowering rpm acts on all four "
                f"contributions simultaneously.",
            ),
            action=_b(
                f"Descendre la vis à {rpm_new:.0f} rpm puis ré-évaluer.",
                f"Lower screw to {rpm_new:.0f} rpm then re-evaluate.",
            ),
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_STABILIZE_PROFILE",
            category=CAT_SCREW_PROFILE,
            severity=alert.severity,
            title=_b(
                "Adoucir le profil de malaxage",
                "Soften mixing profile",
            ),
            rationale=_b(
                "Remplacer une partie des kneading agressifs (90°) par 45°/30° "
                "réduit le SME et l'échauffement sans casser la dispersion.",
                "Replacing some aggressive kneading (90°) with 45°/30° "
                "reduces SME and heating without breaking dispersion.",
            ),
            action=_b(
                "Substituer 2 × Kneading 90° par 2 × Kneading 45° (zone centrale).",
                "Replace 2 × Kneading 90° with 2 × Kneading 45° (central zone).",
            ),
            delta_label="Kneading 90° (×2) → Kneading 45° (×2)",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
    ]


def _from_powder_thermal_traj(state: ProcessState, alert: Alert) -> list[Recommendation]:
    """Reco générique pour POWDER_THERMAL_INCOMPAT_TRAJ — abaisse la consigne
    de la zone la plus chaude transitée par la poudre la plus sensible."""
    m = compute_cooling(state)
    zname = alert.target.replace("Zone ", "").strip()
    zt = m.zones.get(zname)
    if zt is None:
        return []
    sel_idx = zone_index(zname)
    candidates = [
        f for f in state.feeders
        if f.enabled and f.is_solid
        and zone_index(f.position) <= sel_idx
        and zt.t_est_C > f.effective_t_max_C()
    ]
    if not candidates:
        return []
    f = min(candidates, key=lambda x: x.effective_t_max_C())
    t_max = f.effective_t_max_C()
    t_new = max(0.0, t_max - 10.0)
    return [Recommendation(
        code="REC_PROTECT_POWDER",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            f"Protéger la poudre #{f.feeder_id} en {zname}",
            f"Protect powder #{f.feeder_id} in {zname}",
        ),
        rationale=_b(
            f"« {f.material.label_fr} » (borne effective {t_max:.0f} °C). "
            f"T procédé estimée en {zname} ≈ {zt.t_est_C:.0f} °C. Abaisser la "
            f"consigne sous la borne avec 10 °C de marge.",
            f"\"{f.material.label_fr}\" (effective limit {t_max:.0f} °C). "
            f"Estimated process T in {zname} ≈ {zt.t_est_C:.0f} °C. Lower the "
            f"setpoint below the limit with 10 °C margin.",
        ),
        action=_b(
            f"Baisser la consigne {zname} vers {t_new:.0f} °C et/ou réduire rpm "
            f"jusqu'à T_{zname} < {t_max:.0f} °C.",
            f"Lower {zname} setpoint to {t_new:.0f} °C and/or reduce rpm "
            f"until T_{zname} < {t_max:.0f} °C.",
        ),
        delta_label=f"{zt.t_target_C:.0f} °C → {t_new:.0f} °C (T_max {t_max:.0f} °C)",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


def _profile_seq(state: ProcessState) -> list[float]:
    return [
        float(state.zone_temps_C.get(z, DEFAULT_ZONE_TARGETS_C[z]))
        for z in PROCESS_ZONE_ORDER
    ]


def _from_thermal_gradient(state: ProcessState, alert: Alert) -> list[Recommendation]:
    seq = _profile_seq(state)
    deltas = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    if not deltas:
        return []
    j = deltas.index(max(deltas))
    za, zb = PROCESS_ZONE_ORDER[j], PROCESS_ZONE_ORDER[j + 1]
    # Cible : lisser via une consigne intermédiaire (moyenne) sur zb.
    smoothed = seq[j] + min(40.0, (seq[j + 1] - seq[j]) * 0.6)
    return [Recommendation(
        code="REC_SMOOTH_RAMP",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            f"Lisser la rampe {za}→{zb}",
            f"Smooth ramp {za}→{zb}",
        ),
        rationale=_b(
            "Une montée ≤ 40 °C/zone évite le choc thermique et stabilise "
            "le débit. Étaler la chauffe sur les zones intermédiaires.",
            "A ramp ≤ 40 °C/zone avoids thermal shock and stabilizes "
            "flow. Spread heating over intermediate zones.",
        ),
        action=_b(
            f"Abaisser {zb} (ou remonter {za}) pour un pas ≤ 40 °C/zone.",
            f"Lower {zb} (or raise {za}) for a step ≤ 40 °C/zone.",
        ),
        delta_label=f"{zb} {seq[j + 1]:.0f} °C → {smoothed:.0f} °C",
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_profile_unstable(state: ProcessState, alert: Alert) -> list[Recommendation]:
    seq = _profile_seq(state)
    lo, hi = seq[0], max(seq)
    ramp = [lo + (hi - lo) * i / (len(seq) - 1) for i in range(len(seq))]
    target = " · ".join(
        f"{z}{ramp[i]:.0f}" for i, z in enumerate(PROCESS_ZONE_ORDER)
    )
    return [Recommendation(
        code="REC_MONOTONE_PROFILE",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            "Imposer une rampe thermique monotone",
            "Impose monotonic thermal ramp",
        ),
        rationale=_b(
            "Un profil en dents de scie déstabilise la régulation et crée "
            "des points chauds/froids alternés. Une rampe croissante puis "
            "plateau est répétable.",
            "A sawtooth profile destabilizes regulation and creates "
            "alternating hot/cold spots. A rising then plateau ramp "
            "is repeatable.",
        ),
        action=_b(
            f"Reprofiler vers une rampe monotone : {target} °C.",
            f"Reprofile to a monotonic ramp: {target} °C.",
        ),
        delta_label=_b("Profil oscillant → rampe monotone", "Oscillating profile → monotonic ramp"),
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_early_cooling(state: ProcessState, alert: Alert) -> list[Recommendation]:
    zb = alert.target.replace("Zone ", "").strip()
    t_now = float(state.zone_temps_C.get(zb, DEFAULT_ZONE_TARGETS_C.get(zb, 90.0)))
    t_z6 = float(state.zone_temps_C.get("Z6", DEFAULT_ZONE_TARGETS_C["Z6"]))
    t_target = max(t_now, t_z6 - 5.0)
    return [Recommendation(
        code="REC_DELAY_COOLING",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            f"Repousser le refroidissement après Z6",
            f"Delay cooling past Z6",
        ),
        rationale=_b(
            "Refroidir avant la fin du plateau de fusion (Z6) fige une "
            "matière non homogénéisée. Maintenir la T jusqu'à dispersion "
            "complète.",
            "Cooling before the end of the melting plateau (Z6) freezes "
            "non-homogenized material. Maintain T until dispersion "
            "is complete.",
        ),
        action=_b(
            f"Remonter {zb} au niveau du plateau jusqu'à Z6.",
            f"Raise {zb} to plateau level up to Z6.",
        ),
        delta_label=f"{zb} {t_now:.0f} °C → {t_target:.0f} °C",
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_die_too_cold(state: ProcessState, alert: Alert) -> list[Recommendation]:
    t_z8 = float(state.zone_temps_C.get("Z8", DEFAULT_ZONE_TARGETS_C["Z8"]))
    die_t = state.die_temps_C
    die_mean = sum(die_t) / len(die_t)
    t_target = t_z8 - 20.0
    return [Recommendation(
        code="REC_RAISE_DIE",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b("Réchauffer la filière", "Reheat die"),
        rationale=_b(
            "Une filière trop froide fige le fondu en tête (pic de pression "
            "/ surcouple). Viser T_die ≈ T_Z8 − 20 °C.",
            "A die too cold freezes the melt at the head (pressure spike "
            "/ over-torque). Target T_die ≈ T_Z8 − 20 °C.",
        ),
        action=_b(
            f"Remonter la consigne die (moyenne) vers {t_target:.0f} °C.",
            f"Raise die setpoint (average) to {t_target:.0f} °C.",
        ),
        delta_label=f"T_die {die_mean:.0f} °C → {t_target:.0f} °C",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


def _from_die_incoherent(state: ProcessState, alert: Alert) -> list[Recommendation]:
    die_t = state.die_temps_C
    keys = state.die_keys
    decreasing = []
    cur = die_t[0]
    for v in die_t:
        cur = min(cur, v)
        decreasing.append(cur)
    target = " · ".join(
        f"die{idx + 1}={decreasing[idx]:.0f}" for idx in range(len(keys))
    )
    return [Recommendation(
        code="REC_DIE_MONOTONE",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            "Rendre le profil die décroissant",
            "Make die profile decreasing",
        ),
        rationale=_b(
            "Le refroidissement de mise en forme doit être monotone "
            "décroissant vers la sortie pour un calibrage stable.",
            "Forming cooling must be monotonically "
            "decreasing toward the exit for stable calibration.",
        ),
        action=_b(
            f"Régler les zones die en rampe décroissante : {target} °C.",
            f"Set die zones in decreasing ramp: {target} °C.",
        ),
        delta_label=_b("Die non monotone → die décroissant", "Non-monotonic die → decreasing die"),
        confidence=CONFIDENCE_MEDIUM,
        linked_alert_code=alert.code,
    )]


def _from_zone_material_incompat(state: ProcessState, alert: Alert) -> list[Recommendation]:
    f = _find_feeder(state, alert.target)
    if f is None:
        return []
    t_max = f.effective_t_max_C()
    t_target = max(0.0, t_max - 10.0)
    return [Recommendation(
        code="REC_CLAMP_PROFILE_MAT",
        category=CAT_TEMPERATURE,
        severity=alert.severity,
        title=_b(
            f"Plafonner le profil sous {t_max:.0f} °C (feeder #{f.feeder_id})",
            f"Cap profile below {t_max:.0f} °C (feeder #{f.feeder_id})",
        ),
        rationale=_b(
            f"« {f.material.label_fr} » dégrade au-delà de {t_max:.0f} °C. "
            f"Toutes les zones traversées doivent rester ≤ {t_target:.0f} °C "
            f"(10 °C de marge).",
            f"\"{f.material.label_fr}\" degrades above {t_max:.0f} °C. "
            f"All traversed zones must remain ≤ {t_target:.0f} °C "
            f"(10 °C margin).",
        ),
        action=_b(
            f"Abaisser les consignes des zones en aval de {f.position} sous "
            f"{t_target:.0f} °C, ou déplacer le feeder vers une zone plus froide.",
            f"Lower setpoints of zones downstream of {f.position} below "
            f"{t_target:.0f} °C, or move the feeder to a cooler zone.",
        ),
        delta_label=f"profil ≤ {t_target:.0f} °C (T_max {t_max:.0f} °C)",
        confidence=CONFIDENCE_HIGH,
        linked_alert_code=alert.code,
    )]


_DISPATCH = {
    "THERMAL_GRADIENT_STEEP": _from_thermal_gradient,
    "THERMAL_GRADIENT_WARN": _from_thermal_gradient,
    "THERMAL_PROFILE_UNSTABLE": _from_profile_unstable,
    "THERMAL_EARLY_COOLING": _from_early_cooling,
    "DIE_TOO_COLD": _from_die_too_cold,
    "DIE_PROFILE_INCOHERENT": _from_die_incoherent,
    "ZONE_MATERIAL_INCOMPAT": _from_zone_material_incompat,
    # Surcharge zone la plus chaude (modèle thermique auto, plus de focus opérateur)
    "HOTTEST_ZONE_OVERLOAD": _from_zone_overheat,
    "HOTTEST_ZONE_HEAT_RISING": _from_zone_overheat,
    "TORQUE_EXCESS": _from_torque_excess,
    "INSTABILITY_RISK": _from_instability,
    "INSTABILITY_WATCH": _from_instability,
    "POWDER_THERMAL_INCOMPAT_TRAJ": _from_powder_thermal_traj,
    "FEEDER_LOCATION_BAD": _from_feeder_location,
    "THERMAL_INCOMPAT_HIGH": _from_thermal_high,
    "THERMAL_INCOMPAT_LOW": _from_thermal_low,
    "POWDER_OVERLOAD": _from_powder_overload,
    "POWDER_HIGH_LOAD": _from_powder_overload,
    "FF_SATURATION": _from_ff_high,
    "FF_HIGH": _from_ff_high,
    "FF_LOW": _from_ff_low,
    "FF_STARVATION": _from_ff_low,
    "SME_CRITICAL": _from_sme_high,
    "SME_WARNING": _from_sme_high,
    "RT_TOO_SHORT": _from_rt_short,
    "RT_TOO_LONG": _from_rt_long,
    "THERMAL_PROFILE_INVERTED": _from_thermal_inverted,
    "DUPLICATE_SOLID_POSITION": _from_duplicate_position,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_recommendations(
    state: ProcessState, alerts: list[Alert], *, lang: str = "en",
) -> list[Recommendation]:
    """À partir des alertes du moteur de règles, génère les recos actionnables.

    Déduplique par code de reco — si deux alertes pointent vers la même
    action concrète, on ne la propose qu'une fois (la plus sévère).
    """
    _rules_mod._LANG = lang

    seen: dict[str, Recommendation] = {}
    sev_order = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    for alert in alerts:
        gen = _DISPATCH.get(alert.code)
        if gen is None:
            continue
        for rec in gen(state, alert):
            prev = seen.get(rec.code)
            if prev is None or sev_order.get(rec.severity, 99) < sev_order.get(prev.severity, 99):
                seen[rec.code] = rec

    recos = list(seen.values())

    # Garde stricte : retirer toute reco qui cite un type d'élément ABSENT de la
    # configuration courante (ex. « substituer Kneading 90° » sans malaxage).
    # Les recos élément-agnostiques (baisser rpm, ajuster T°, réduire débit)
    # subsistent → repli garanti.
    # Manager 2026-06-10 : la garde s'applique AUSSI quand la config est vide
    # ou inconnue — une vis vide ne contient aucun kneading, et une config non
    # vérifiable ne justifie jamais de citer un élément précis.
    config = list(getattr(state, "screw_config", []) or [])
    if _cites_absent is not None:
        def _reco_text(r: Recommendation) -> str:
            return " ".join((r.title, r.rationale, r.action, r.delta_label))
        recos = [r for r in recos if not _cites_absent(_reco_text(r), config)]

    return recos
