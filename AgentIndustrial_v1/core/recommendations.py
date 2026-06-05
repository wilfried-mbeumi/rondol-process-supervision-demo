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
    SME_CRITICAL_KWH_PER_KG,
    SME_WARNING_KWH_PER_KG,
    THERMAL_REG_BAND_C,
)
from .rules import Alert

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

_CAT_LABELS: dict[str, str] = {
    CAT_FEEDER_MOVE: "Déplacement feeder",
    CAT_FLOW: "Ajustement débit",
    CAT_TEMPERATURE: "Ajustement température",
    CAT_SCREW_PROFILE: "Modification profil vis",
    CAT_SCREW_SPEED: "Vitesse vis",
    CAT_OTHER: "Autre",
}

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
        return _CAT_LABELS.get(self.category, self.category)


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
        title=f"Déplacer feeder #{f.feeder_id} → {target_pos}",
        rationale=(
            f"La phase {f.material.phase} ne peut être injectée en "
            f"{f.position} (avant fusion / zone inadaptée). "
            f"{target_pos} est la 1ère position physiquement valide."
        ),
        action=(
            f"Déplacer le point d'injection du feeder #{f.feeder_id} "
            f"({f.material.label_fr}) vers la position {target_pos}."
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
            title=f"Réduire T_{f.position}",
            rationale=(
                f"Borne haute matière {f.material.label_fr} = {t_max:.0f} °C. "
                f"Cible 10 °C de marge sous la borne pour absorber les "
                f"variations de procédé."
            ),
            action=f"Abaisser la consigne {f.position} jusqu'à environ {t_target:.0f} °C.",
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
            title=f"Déplacer feeder #{f.feeder_id} vers zone plus froide",
            rationale=(
                f"Position {cooler} = T plus basse, compatible avec la borne "
                f"effective {t_max:.0f} °C."
            ),
            action=(
                f"Déplacer feeder #{f.feeder_id} de {f.position} vers {cooler} "
                f"si la chimie le permet."
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
        title=f"Augmenter T_{f.position}",
        rationale=(
            f"Sous la borne basse opérationnelle ({t_min:.0f} °C) — "
            f"risque condensation / matière inerte."
        ),
        action=f"Remonter la consigne {f.position} à au moins {t_target:.0f} °C.",
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
            title=f"Réduire débit feeder #{biggest.feeder_id}",
            rationale=(
                "Surcharge solide → ramener à 80 % du débit pour rétablir une "
                "marge de capacité et éviter le surcouple."
            ),
            action=(
                f"Réduire le débit du feeder #{biggest.feeder_id} "
                f"({biggest.material.label_fr}) de 20 %."
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
            title="Augmenter la vitesse vis",
            rationale=(
                "À débit constant, une vitesse vis plus élevée diminue le "
                "Fill Factor et restaure de la capacité de transport."
            ),
            action=f"Monter la vitesse vis à {new_rpm:.0f} rpm si le procédé le permet.",
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
            title="Réduire le débit cumulé",
            rationale=(
                f"FF visé : {FF_TARGET_LOW * 100:.0f}-{FF_TARGET_HIGH * 100:.0f} %. "
                f"Baisser le débit global de 15 % pour ramener FF dans la cible."
            ),
            action="Réduire de 15 % le feeder solide principal.",
            delta_label=f"FF {state.kpis.fill_factor * 100:.0f} % → ~{(state.kpis.fill_factor * 0.85) * 100:.0f} %",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_RPM_UP_FF",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title="Augmenter la vitesse vis",
            rationale="FF diminue ~ linéairement avec rpm à débit constant.",
            action=f"Passer à {rpm_new:.0f} rpm pour soulager la vis.",
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
            title="Réduire la vitesse vis",
            rationale="Vis trop rapide / sous-alimentée — réduire rpm augmente FF.",
            action=f"Descendre à {rpm_new:.0f} rpm.",
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_INCREASE_FLOW",
            category=CAT_FLOW,
            severity=alert.severity,
            title="Augmenter le débit solide",
            rationale=(
                "Augmenter le débit feeder principal pour ramener FF dans la "
                "cible compounding."
            ),
            action="Monter le feeder principal de 15-20 %.",
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
            title="Adoucir le profil de mélange",
            rationale=(
                "SME élevé = cisaillement excessif. Remplacer une partie des "
                "kneading 90° par 45° ou 30° réduit l'énergie spécifique sans "
                "détériorer la dispersion."
            ),
            action=(
                "Substituer 2 × Kneading 90° par 2 × Kneading 45° en zone "
                "centrale (Z3-Z4)."
            ),
            delta_label="Kneading 90° (×2) → Kneading 45° (×2)",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_REDUCE_RPM_SME",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title="Réduire la vitesse vis",
            rationale="SME ∝ rpm. Une baisse de 15 % de rpm donne ~15 % de baisse SME.",
            action=f"Réduire la vitesse vis à {rpm_new:.0f} rpm.",
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
            title="Allonger le profil vis",
            rationale="RT < 5 s = mélange insuffisant. Ajouter des éléments augmente la résidence.",
            action="Passer à une config 30 ou 40 éléments selon disponibilité.",
            delta_label=f"RT {state.kpis.residence_time_s:.1f} s → +50 % (cible)",
            confidence=CONFIDENCE_MEDIUM,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_REDUCE_RPM_RT",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title="Réduire la vitesse vis",
            rationale="rpm bas = RT plus long (à débit constant).",
            action=f"Descendre à {rpm_new:.0f} rpm.",
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
        title="Augmenter la vitesse vis",
        rationale="RT trop long = matière sur-cisaillée. rpm plus haut = RT plus court.",
        action=f"Monter à {rpm_new:.0f} rpm.",
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
        title="Aligner la consigne filière",
        rationale="En compounding standard, T_die ≤ T_Z5 + 15 °C.",
        action=f"Régler la filière à environ {t_target:.0f} °C.",
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
        title=f"Espacer feeder #{candidate.feeder_id}",
        rationale=(
            "Deux solides au même point provoquent agglomération. "
            "Décaler permet une fluidification intermédiaire."
        ),
        action=f"Déplacer feeder #{candidate.feeder_id} en aval.",
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
            title=f"Abaisser la consigne {zname}",
            rationale=(
                f"L'échauffement viscoélastique ajoute +{zt.dT_C:.0f} °C à "
                f"{zname}. Baisser la consigne compense la dissipation pour "
                f"ramener la T réelle dans la bande ±{tol:.0f} °C."
            ),
            action=f"Régler la consigne {zname} vers {t_new:.0f} °C (régulation froid).",
            delta_label=f"{zt.t_target_C:.0f} °C → {t_new:.0f} °C",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_RPM_DOWN_THERMAL",
            category=CAT_SCREW_SPEED,
            severity=alert.severity,
            title="Réduire la vitesse vis",
            rationale=(
                "La dissipation visqueuse ≈ couple × N. −15 % rpm réduit "
                "proportionnellement l'échauffement de la zone."
            ),
            action=f"Descendre la vis à {rpm_new:.0f} rpm.",
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
            title=f"Intercaler du convoyage avant {zname}",
            rationale=(
                "Insérer un bloc de convoyage (forward) entre les éléments de "
                "malaxage crée une fenêtre de refroidissement et casse "
                "l'accumulation thermique du plateau."
            ),
            action=f"Ajouter 1-2 éléments de convoyage juste en amont de {zname}.",
            delta_label="Kneading continu → Kneading + convoyage refroid.",
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
        title="Réduire la vitesse vis (décharge couple)",
        rationale="Le couple chute avec la vitesse à débit constant — sécurise le moteur.",
        action=f"Descendre la vis à {rpm_new:.0f} rpm.",
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
            title=f"Réduire débit feeder #{biggest.feeder_id}",
            rationale="Moins de matière cisaillée ⇒ couple et échauffement réduits.",
            action=f"Réduire le feeder #{biggest.feeder_id} de 15 %.",
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
            title="Réduire la vitesse pour stabiliser",
            rationale=(
                f"Index instabilité {m.instability_index:.2f} tiré par "
                f"SME/FF/échauffement/couple. Baisser rpm agit sur les quatre "
                f"contributions simultanément."
            ),
            action=f"Descendre la vis à {rpm_new:.0f} rpm puis ré-évaluer.",
            delta_label=f"{state.screw_rpm:.0f} → {rpm_new:.0f} rpm",
            confidence=CONFIDENCE_HIGH,
            linked_alert_code=alert.code,
        ),
        Recommendation(
            code="REC_STABILIZE_PROFILE",
            category=CAT_SCREW_PROFILE,
            severity=alert.severity,
            title="Adoucir le profil de malaxage",
            rationale=(
                "Remplacer une partie des kneading agressifs (90°) par 45°/30° "
                "réduit le SME et l'échauffement sans casser la dispersion."
            ),
            action="Substituer 2 × Kneading 90° par 2 × Kneading 45° (zone centrale).",
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
        title=f"Protéger la poudre #{f.feeder_id} en {zname}",
        rationale=(
            f"« {f.material.label_fr} » (borne effective {t_max:.0f} °C). "
            f"T procédé estimée en {zname} ≈ {zt.t_est_C:.0f} °C. Abaisser la "
            f"consigne sous la borne avec 10 °C de marge."
        ),
        action=(
            f"Baisser la consigne {zname} vers {t_new:.0f} °C et/ou réduire rpm "
            f"jusqu'à T_{zname} < {t_max:.0f} °C."
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
        title=f"Lisser la rampe {za}→{zb}",
        rationale=(
            "Une montée ≤ 40 °C/zone évite le choc thermique et stabilise "
            "le débit. Étaler la chauffe sur les zones intermédiaires."
        ),
        action=f"Abaisser {zb} (ou remonter {za}) pour un pas ≤ 40 °C/zone.",
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
        title="Imposer une rampe thermique monotone",
        rationale=(
            "Un profil en dents de scie déstabilise la régulation et crée "
            "des points chauds/froids alternés. Une rampe croissante puis "
            "plateau est répétable."
        ),
        action=f"Reprofiler vers une rampe monotone : {target} °C.",
        delta_label="Profil oscillant → rampe monotone",
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
        title=f"Repousser le refroidissement après Z6",
        rationale=(
            "Refroidir avant la fin du plateau de fusion (Z6) fige une "
            "matière non homogénéisée. Maintenir la T jusqu'à dispersion "
            "complète."
        ),
        action=f"Remonter {zb} au niveau du plateau jusqu'à Z6.",
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
        title="Réchauffer la filière",
        rationale=(
            "Une filière trop froide fige le fondu en tête (pic de pression "
            "/ surcouple). Viser T_die ≈ T_Z8 − 20 °C."
        ),
        action=f"Remonter la consigne die (moyenne) vers {t_target:.0f} °C.",
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
        title="Rendre le profil die décroissant",
        rationale=(
            "Le refroidissement de mise en forme doit être monotone "
            "décroissant vers la sortie pour un calibrage stable."
        ),
        action=f"Régler les zones die en rampe décroissante : {target} °C.",
        delta_label="Die non monotone → die décroissant",
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
        title=f"Plafonner le profil sous {t_max:.0f} °C (feeder #{f.feeder_id})",
        rationale=(
            f"« {f.material.label_fr} » dégrade au-delà de {t_max:.0f} °C. "
            f"Toutes les zones traversées doivent rester ≤ {t_target:.0f} °C "
            f"(10 °C de marge)."
        ),
        action=(
            f"Abaisser les consignes des zones en aval de {f.position} sous "
            f"{t_target:.0f} °C, ou déplacer le feeder vers une zone plus froide."
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
    state: ProcessState, alerts: list[Alert],
) -> list[Recommendation]:
    """À partir des alertes du moteur de règles, génère les recos actionnables.

    Déduplique par code de reco — si deux alertes pointent vers la même
    action concrète, on ne la propose qu'une fois (la plus sévère).
    """
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
    # subsistent → repli garanti. N'agit que si la config est connue.
    config = list(getattr(state, "screw_config", []) or [])
    if _cites_absent is not None and config:
        def _reco_text(r: Recommendation) -> str:
            return " ".join((r.title, r.rationale, r.action, r.delta_label))
        recos = [r for r in recos if not _cites_absent(_reco_text(r), config)]

    return recos
