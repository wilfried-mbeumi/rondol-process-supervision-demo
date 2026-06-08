"""
rules.py — Moteur de règles explicable (Agent IA V1, rule-based).

Pas de LLM, pas de réseau de neurones marketing. Chaque alerte de l'agent est :
  - traçable à une règle écrite ici
  - justifiée par des nombres mesurés (FF=72 %, RT=8.4 s, ...)
  - associée à une recommandation actionnable (cf. recommendations.py)

Les seuils proviennent de :
  - core.process (FF, SME, RT cibles compounding SSB)
  - core.feeders (MaterialType.safe_temperature_C, allowed_positions)
  - paramètres opérateur (UI Settings)

Ce module est PUR : il ne consomme que ProcessState, il ne mute rien.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cooling import compute_cooling, zone_index
from .feeders import (
    POSITION_TO_LEGACY_ZONE,
    FeederSpec,
    active_feeders,
    mass_flow_by_phase,
)
from .process import (
    DEFAULT_ZONE_TARGETS_C,
    FF_TARGET_HIGH,
    FF_TARGET_LOW,
    PROCESS_ZONE_ORDER,
    ProcessState,
    RT_MAX_S,
    RT_MIN_S,
    SME_CRITICAL_KWH_PER_KG,
    SME_WARNING_KWH_PER_KG,
    THERMAL_REG_BAND_C,
)


# ---------------------------------------------------------------------------
# Modèle de sortie
# ---------------------------------------------------------------------------
SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
SEVERITY_OK = "ok"

# Sévérité → poids dans le score (start 100, on retranche)
_SEVERITY_WEIGHTS: dict[str, int] = {
    SEVERITY_CRITICAL: 22,
    SEVERITY_WARNING: 8,
    SEVERITY_INFO: 2,
    SEVERITY_OK: 0,
}

# Score → état (ressemble à la grille existante Supervision.py)
STATE_STABLE = "STABLE"
STATE_WATCH = "SURVEILLER"
STATE_CRITICAL = "CRITIQUE"


@dataclass(frozen=True)
class Alert:
    """Alerte agent — traçable à une règle, chiffrée, actionnable."""
    code: str
    severity: str
    title: str
    description: str   # explication lisible (1-2 phrases)
    evidence: str      # nombres mesurés ("FF=72 %", "RT=8.4 s")
    target: str = ""   # zone / feeder / "global" — pour le bandeau UI


@dataclass
class AgentReport:
    """Rapport complet de l'agent pour un cycle d'analyse."""
    risk_score: int = 100
    state: str = STATE_STABLE
    alerts: list[Alert] = field(default_factory=list)
    diagnostic: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f} %"


def _feeder_label(f: FeederSpec) -> str:
    return f"#{f.feeder_id} {f.display_name()}"


# ---------------------------------------------------------------------------
# Règles
# ---------------------------------------------------------------------------
def _rule_feeder_position(state: ProcessState) -> list[Alert]:
    """R1 — Emplacement feeder cohérent avec la matière.

    Un gaz/scCO₂ ne s'injecte pas avant la zone de fusion. Une poudre solide
    ne va pas à la filière. Vérifie chaque feeder actif contre
    MaterialType.allowed_positions.
    """
    out: list[Alert] = []
    for f in active_feeders(state.feeders):
        allowed = f.material.allowed_positions
        if f.position not in allowed:
            allowed_str = " · ".join(allowed)
            out.append(Alert(
                code="FEEDER_LOCATION_BAD",
                severity=SEVERITY_CRITICAL,
                title=f"Feeder {_feeder_label(f)} mal positionné",
                description=(
                    f"Matière « {f.material.label_fr} » injectée en {f.position} : "
                    f"physiquement incorrect. Positions valides pour cette phase "
                    f"({f.material.phase}) : {allowed_str}."
                ),
                evidence=f"position={f.position} · phase={f.material.phase}",
                target=f"Feeder #{f.feeder_id}",
            ))
    return out


def _rule_thermal_compat(state: ProcessState) -> list[Alert]:
    """R2 — Incompatibilité thermique matière × zone d'injection.

    Pour chaque feeder actif, on compare T_zone aux bornes effectives
    (FeederSpec.effective_t_max_C / effective_t_min_C — priorité aux données
    opérateur t_degradation_C / tga_onset_C si renseignées).
    """
    out: list[Alert] = []
    for f in active_feeders(state.feeders):
        t_zone = state.temp_at(f.position)
        t_min = f.effective_t_min_C()
        t_max = f.effective_t_max_C()
        if t_zone > t_max:
            out.append(Alert(
                code="THERMAL_INCOMPAT_HIGH",
                severity=SEVERITY_CRITICAL,
                title=f"Surchauffe matière au feeder {_feeder_label(f)}",
                description=(
                    f"T_{f.position} = {t_zone:.0f} °C dépasse la borne haute "
                    f"sûre de la matière « {f.material.label_fr} » "
                    f"({t_max:.0f} °C). Risque de dégradation thermique / "
                    f"flash boiling (liquides) / décomposition de la matière."
                ),
                evidence=f"T={t_zone:.0f} °C · T_max={t_max:.0f} °C",
                target=f"Feeder #{f.feeder_id}",
            ))
        elif t_zone < t_min:
            out.append(Alert(
                code="THERMAL_INCOMPAT_LOW",
                severity=SEVERITY_WARNING,
                title=f"Température trop basse au feeder {_feeder_label(f)}",
                description=(
                    f"T_{f.position} = {t_zone:.0f} °C inférieure à la borne "
                    f"basse opérationnelle ({t_min:.0f} °C). "
                    f"Risque condensation (gaz/scCO₂) ou matière non fluide."
                ),
                evidence=f"T={t_zone:.0f} °C · T_min={t_min:.0f} °C",
                target=f"Feeder #{f.feeder_id}",
            ))
    return out


def _rule_powder_overload(state: ProcessState) -> list[Alert]:
    """R3 — Surcharge poudre vs capacité estimée.

    Capacité poudre = ρ_bulk × V_free × rpm/60 × η_remplissage_max
    où η_remplissage_max ≈ 0.70 (au-delà → surcouple garanti).

    On signale dès qu'on dépasse 80 % de la capacité estimée.
    """
    out: list[Alert] = []
    flows = mass_flow_by_phase(state.feeders)
    powder_flow = flows.get("solid", 0.0)
    if powder_flow <= 0.0:
        return out

    rpm = max(1.0, state.screw_rpm)
    v_free = max(0.01, state.kpis.free_volume_cm3)
    # Estimation capacité en g/min (proxy compounding bivis).
    # ṁ_max ≈ ρ × V_free × N × η_max ; on convertit cm³·rpm·g/cm³ → g/min.
    rho_eq = max(0.05, sum(
        f.density_g_per_cm3 * f.mass_flow_g_per_min
        for f in active_feeders(state.feeders) if f.is_solid
    ) / max(1e-6, powder_flow))
    eta_max = 0.70
    capacity_g_per_min = rho_eq * v_free * rpm * eta_max
    if capacity_g_per_min <= 0.0:
        return out

    load_pct = powder_flow / capacity_g_per_min

    if load_pct > 1.0:
        out.append(Alert(
            code="POWDER_OVERLOAD",
            severity=SEVERITY_CRITICAL,
            title="Surcharge poudre — capacité vis dépassée",
            description=(
                f"Débit poudre cumulé {powder_flow:.0f} g/min > capacité estimée "
                f"{capacity_g_per_min:.0f} g/min (charge {load_pct * 100:.0f} %). "
                f"Surcouple imminent et risque de bouchage en zone de mélange."
            ),
            evidence=f"ṁ={powder_flow:.0f} g/min · cap={capacity_g_per_min:.0f} g/min",
            target="Global feeders",
        ))
    elif load_pct > 0.80:
        out.append(Alert(
            code="POWDER_HIGH_LOAD",
            severity=SEVERITY_WARNING,
            title="Chargement poudre élevé",
            description=(
                f"Charge solide à {load_pct * 100:.0f} % de la capacité estimée. "
                f"Marge réduite face aux fluctuations de débit."
            ),
            evidence=f"charge={load_pct * 100:.0f} % de capacité",
            target="Global feeders",
        ))
    return out


def _rule_fill_factor(state: ProcessState) -> list[Alert]:
    """R4 — Fill Factor hors cibles compounding SSB."""
    ff = state.kpis.fill_factor
    if ff <= 0.0:
        return [Alert(
            code="FF_ZERO",
            severity=SEVERITY_WARNING,
            title="Fill Factor nul",
            description=(
                "Aucune matière calculée dans la vis. Vérifier qu'un feeder "
                "solide est actif et que sa position est Z0."
            ),
            evidence="FF=0 %",
            target="Global vis",
        )]
    out: list[Alert] = []
    if ff > 0.65:
        out.append(Alert(
            code="FF_SATURATION",
            severity=SEVERITY_CRITICAL,
            title="Fill Factor en saturation",
            description=(
                f"FF={_fmt_pct(ff)} > 65 % — la vis travaille en régime gavé. "
                f"Surcouple, échauffement et pulsations de pression attendus."
            ),
            evidence=f"FF={_fmt_pct(ff)} · cible {FF_TARGET_LOW*100:.0f}-{FF_TARGET_HIGH*100:.0f} %",
            target="Global vis",
        ))
    elif ff > FF_TARGET_HIGH:
        out.append(Alert(
            code="FF_HIGH",
            severity=SEVERITY_WARNING,
            title="Fill Factor au-dessus de la cible",
            description=(
                f"FF={_fmt_pct(ff)} > cible haute ({_fmt_pct(FF_TARGET_HIGH)}). "
                f"Mélange devient majoritairement convectif, dispersion fine "
                f"compromise."
            ),
            evidence=f"FF={_fmt_pct(ff)}",
            target="Global vis",
        ))
    elif ff < 0.10:
        out.append(Alert(
            code="FF_STARVATION",
            severity=SEVERITY_CRITICAL,
            title="Vis sous-alimentée",
            description=(
                f"FF={_fmt_pct(ff)} < 10 % — régime de famine. Transport "
                f"erratique, mélange aléatoire, résidus en fond de vis."
            ),
            evidence=f"FF={_fmt_pct(ff)}",
            target="Global vis",
        ))
    elif ff < FF_TARGET_LOW:
        out.append(Alert(
            code="FF_LOW",
            severity=SEVERITY_WARNING,
            title="Fill Factor sous la cible",
            description=(
                f"FF={_fmt_pct(ff)} < cible basse ({_fmt_pct(FF_TARGET_LOW)}). "
                f"Cisaillement local élevé, possible dégradation produit."
            ),
            evidence=f"FF={_fmt_pct(ff)}",
            target="Global vis",
        ))
    return out


def _rule_sme(state: ProcessState) -> list[Alert]:
    """R5 — Specific Mechanical Energy trop élevé (seuil procédé)."""
    sme = state.kpis.sme_kwh_per_kg
    if sme <= 0.0:
        return []
    if sme > SME_CRITICAL_KWH_PER_KG:
        return [Alert(
            code="SME_CRITICAL",
            severity=SEVERITY_CRITICAL,
            title="SME au-delà du seuil procédé",
            description=(
                f"SME élevée : énergie mécanique spécifique {sme:.2f} kWh/kg "
                f"supérieure au seuil procédé configuré "
                f"({SME_CRITICAL_KWH_PER_KG:.2f} kWh/kg). Sollicitation "
                f"thermomécanique excessive de la matière transformée."
            ),
            evidence=f"SME={sme:.2f} kWh/kg",
            target="Global vis",
        )]
    if sme > SME_WARNING_KWH_PER_KG:
        return [Alert(
            code="SME_WARNING",
            severity=SEVERITY_WARNING,
            title="SME élevé",
            description=(
                f"SME élevée : énergie mécanique spécifique {sme:.2f} kWh/kg "
                f"supérieure au seuil de vigilance "
                f"{SME_WARNING_KWH_PER_KG:.2f} kWh/kg. Surveiller la stabilité "
                f"thermique et la dispersion en sortie."
            ),
            evidence=f"SME={sme:.2f} kWh/kg",
            target="Global vis",
        )]
    return []


def _rule_residence_time(state: ProcessState) -> list[Alert]:
    """R6 — Résidence cohérente avec le procédé (5-120 s typique compounding)."""
    rt = state.kpis.residence_time_s
    if rt <= 0.0:
        return []
    if rt < RT_MIN_S:
        return [Alert(
            code="RT_TOO_SHORT",
            severity=SEVERITY_WARNING,
            title="Temps de résidence trop court",
            description=(
                f"RT={rt:.1f} s < {RT_MIN_S:.0f} s. Mélange insuffisant — "
                f"homogénéité produit non garantie."
            ),
            evidence=f"RT={rt:.1f} s",
            target="Global vis",
        )]
    if rt > RT_MAX_S:
        return [Alert(
            code="RT_TOO_LONG",
            severity=SEVERITY_WARNING,
            title="Temps de résidence trop long",
            description=(
                f"RT={rt:.1f} s > {RT_MAX_S:.0f} s. Sur-cisaillement et "
                f"sur-chauffe possibles, notamment pour les matières thermosensibles."
            ),
            evidence=f"RT={rt:.1f} s",
            target="Global vis",
        )]
    return []


def _rule_die_temp_monotony(state: ProcessState) -> list[Alert]:
    """R7 — Profil thermique cohérent : la filière ne doit pas être plus
    chaude que le plateau de mélange (Z5/Z6) en compounding standard."""
    t_die = state.zone_temps_C.get("die", None)
    t_z5 = state.zone_temps_C.get("Z5", None)
    if t_die is None or t_z5 is None:
        return []
    if t_die > t_z5 + 15.0:
        return [Alert(
            code="THERMAL_PROFILE_INVERTED",
            severity=SEVERITY_WARNING,
            title="Profil thermique inversé en filière",
            description=(
                f"T_die={t_die:.0f} °C > T_Z5={t_z5:.0f} °C de plus de 15 °C. "
                f"Inhabituel en compounding — vérifier la consigne filière."
            ),
            evidence=f"T_die={t_die:.0f} °C · T_Z5={t_z5:.0f} °C",
            target="Die",
        )]
    return []


def _rule_duplicate_position(state: ProcessState) -> list[Alert]:
    """R8 — 2+ feeders solides à la même position = surcharge locale.

    Cas légitime : 1 solide + 1 liquide à la même position (lubrification).
    Cas problématique : 2 solides au même point (poudres LFP + LATP au Z0
    par exemple — il vaut mieux les répartir).
    """
    out: list[Alert] = []
    by_pos: dict[str, list[FeederSpec]] = {}
    for f in active_feeders(state.feeders):
        by_pos.setdefault(f.position, []).append(f)
    for pos, group in by_pos.items():
        solids = [f for f in group if f.is_solid]
        if len(solids) >= 2:
            labels = " + ".join(f"#{f.feeder_id}" for f in solids)
            out.append(Alert(
                code="DUPLICATE_SOLID_POSITION",
                severity=SEVERITY_WARNING,
                title=f"Plusieurs solides en {pos}",
                description=(
                    f"Feeders {labels} injectent tous des solides en {pos}. "
                    f"Risque d'agglomération à l'entrée — envisager de "
                    f"décaler l'un d'eux en aval (Z2 ou Z3) pour ménager "
                    f"une étape de fluidification avant ajout du second."
                ),
                evidence=f"position={pos} · n_solides={len(solids)}",
                target=f"Position {pos}",
            ))
    return out


def _rule_cooling(state: ProcessState) -> list[Alert]:
    """R9 — Diagnostic thermique procédé (modèle T_real par zone).

    S'appuie sur core.cooling (échauffement viscoélastique réel calculé
    depuis rpm, FF, SME, couple, débits/α/viscosité feeders, profil de
    cisaillement issu de la configuration vis réelle).

    Le « test de refroidissement » opérateur n'existe pas : le diagnostic
    cible automatiquement la zone la plus chaude calculée par le modèle
    (ou Z5 par défaut pour le canari du plateau de malaxage).
    """
    m = compute_cooling(state)
    out: list[Alert] = []

    # --- Global : surcharge zone la plus chaude (souvent Z5) --------------
    hot_name = m.hottest_zone
    hot = m.zones.get(hot_name)
    if hot is not None:
        if hot.status == "overheat":
            out.append(Alert(
                code="HOTTEST_ZONE_OVERLOAD",
                severity=SEVERITY_CRITICAL,
                title=f"Surcharge thermique {hot_name}",
                description=(
                    f"{hot_name} = zone la plus chaude du fourreau. T estimée "
                    f"{hot.t_est_C:.0f} °C (consigne {hot.t_target_C:.0f} °C, "
                    f"+{hot.dT_C:.0f} °C par dissipation visqueuse). Besoin de "
                    f"refroidissement {hot.cooling_demand_pct:.0f} %. Risque de "
                    f"dégradation thermique de la matière et de bouchage en sortie "
                    f"de plateau de mélange."
                ),
                evidence=f"T_{hot_name}≈{hot.t_est_C:.0f} °C · ΔT=+{hot.dT_C:.0f} °C",
                target=f"Zone {hot_name}",
            ))
        elif hot.status == "watch" and hot.dT_C > 18.0:
            out.append(Alert(
                code="HOTTEST_ZONE_HEAT_RISING",
                severity=SEVERITY_WARNING,
                title=f"Échauffement {hot_name} en montée",
                description=(
                    f"{hot_name} +{hot.dT_C:.0f} °C au-dessus de la consigne — "
                    f"marge thermique réduite sur la zone la plus sollicitée."
                ),
                evidence=f"ΔT_{hot_name}=+{hot.dT_C:.0f} °C · froid={hot.cooling_demand_pct:.0f} %",
                target=f"Zone {hot_name}",
            ))

    # --- Global : couple excessif -----------------------------------------
    if (m.torque_measured and m.torque_load > 0.85) or m.torque_load > 0.92:
        sev = SEVERITY_CRITICAL if m.torque_load > 0.97 else SEVERITY_WARNING
        src = "mesuré" if m.torque_measured else "estimé"
        out.append(Alert(
            code="TORQUE_EXCESS",
            severity=sev,
            title="Couple vis excessif",
            description=(
                f"Charge couple {src} à {m.torque_load * 100:.0f} % du nominal. "
                f"Couple élevé ⇒ dissipation thermique accrue dans tout le "
                f"fourreau et risque de déclenchement sécurité moteur."
            ),
            evidence=f"torque={m.torque_load * 100:.0f} % ({src})",
            target="Global vis",
        ))

    # --- Global : risque d'instabilité thermique --------------------------
    if m.instability_index >= 0.70:
        out.append(Alert(
            code="INSTABILITY_RISK",
            severity=SEVERITY_CRITICAL,
            title="Risque d'instabilité thermique élevé",
            description=(
                f"Index instabilité {m.instability_index:.2f} (≥0,70) — "
                f"combinaison SME/Fill Factor/échauffement/couple en zone de "
                f"basculement. Procédé non répétable : pulsations de pression "
                f"et dérive thermique attendues."
            ),
            evidence=f"idx_instab={m.instability_index:.2f} · zone chaude={m.hottest_zone}",
            target="Global procédé",
        ))
    elif m.instability_index >= 0.50:
        out.append(Alert(
            code="INSTABILITY_WATCH",
            severity=SEVERITY_WARNING,
            title="Surveillance instabilité thermique",
            description=(
                f"Index instabilité {m.instability_index:.2f} (≥0,50). "
                f"Zone la plus chaude : {m.hottest_zone}. Stabiliser avant "
                f"montée en cadence."
            ),
            evidence=f"idx_instab={m.instability_index:.2f}",
            target="Global procédé",
        ))

    # --- Incompatibilité poudre / T_réelle sur tout le trajet -------------
    # Pour chaque poudre solide, on vérifie que toute zone aval Z_k transitée
    # reste sous sa borne haute effective (t_degradation_C / tga_onset_C).
    if hot is not None:
        for f in active_feeders(state.feeders):
            if not f.is_solid:
                continue
            start = POSITION_TO_LEGACY_ZONE.get(f.position, 0)
            t_max = f.effective_t_max_C()
            worst_zone = ""
            worst_t = -1.0
            for zk in ZONES_LIST:
                if zone_index(zk) < start:
                    continue
                zt = m.zones.get(zk)
                if zt is None:
                    continue
                if zt.t_est_C > t_max and zt.t_est_C > worst_t:
                    worst_t = zt.t_est_C
                    worst_zone = zk
            if worst_zone:
                tga_note = ""
                if f.tga_onset_C is not None and f.tga_onset_C > 0:
                    tga_note = f" · ATG onset {f.tga_onset_C:.0f} °C"
                out.append(Alert(
                    code="POWDER_THERMAL_INCOMPAT_TRAJ",
                    severity=SEVERITY_CRITICAL,
                    title=f"Poudre #{f.feeder_id} surchauffée sur trajet",
                    description=(
                        f"La matière « {f.material.label_fr} » (feeder #{f.feeder_id}, "
                        f"injectée en {f.position}) traverse {worst_zone} où T "
                        f"estimée ≈ {worst_t:.0f} °C > borne effective "
                        f"{t_max:.0f} °C{tga_note}. Dégradation de la matière "
                        f"probable — l'échauffement procédé réel "
                        f"dépasse la limite matière, pas seulement la consigne."
                    ),
                    evidence=f"T_{worst_zone}≈{worst_t:.0f} °C · T_max={t_max:.0f} °C",
                    target=f"Zone {worst_zone}",
                ))
    return out


# Constante locale pour itération (évite import circulaire avec cooling).
ZONES_LIST: tuple[str, ...] = ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8")


def _rule_thermal_profile(state: ProcessState) -> list[Alert]:
    """R10 — Cohérence du profil thermique extrusion (consignes Z1..Z8 + die).

    Évalue la FORME du profil de consigne saisi par l'opérateur (≠ R9 qui
    calcule l'échauffement réel). Branché sur SME, feeders, débits, matière
    et nombre de zones die.
    """
    out: list[Alert] = []
    zt = state.zone_temps_C
    seq = [
        float(zt.get(z, DEFAULT_ZONE_TARGETS_C[z])) for z in PROCESS_ZONE_ORDER
    ]
    deltas = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    sme = state.kpis.sme_kwh_per_kg

    # --- Montée thermique trop brutale -----------------------------------
    max_jump = max(deltas) if deltas else 0.0
    if max_jump > 0:
        j = deltas.index(max_jump)
        za, zb = PROCESS_ZONE_ORDER[j], PROCESS_ZONE_ORDER[j + 1]
        if max_jump > 70.0:
            out.append(Alert(
                code="THERMAL_GRADIENT_STEEP",
                severity=SEVERITY_CRITICAL,
                title=f"Montée thermique brutale {za}→{zb}",
                description=(
                    f"Saut de consigne +{max_jump:.0f} °C entre {za} et {zb}. "
                    f"Choc thermique sur la matière : dégradation locale, "
                    f"contraintes mécaniques et instabilité de débit."
                ),
                evidence=f"Δ{za}→{zb}=+{max_jump:.0f} °C",
                target=f"Zone {zb}",
            ))
        elif max_jump > 45.0:
            out.append(Alert(
                code="THERMAL_GRADIENT_WARN",
                severity=SEVERITY_WARNING,
                title=f"Gradient thermique élevé {za}→{zb}",
                description=(
                    f"+{max_jump:.0f} °C entre {za} et {zb} — préférer une "
                    f"montée plus progressive (≤ 40 °C par zone)."
                ),
                evidence=f"Δ{za}→{zb}=+{max_jump:.0f} °C",
                target=f"Zone {zb}",
            ))

    # --- Profil instable (oscillant) -------------------------------------
    signs = [1 if d > 2.0 else (-1 if d < -2.0 else 0) for d in deltas]
    nz = [s for s in signs if s != 0]
    flips = sum(1 for i in range(len(nz) - 1) if nz[i] != nz[i + 1])
    if flips >= 2:
        sev = SEVERITY_CRITICAL if (flips >= 3 and sme > SME_WARNING_KWH_PER_KG) else SEVERITY_WARNING
        out.append(Alert(
            code="THERMAL_PROFILE_UNSTABLE",
            severity=sev,
            title="Profil thermique instable (oscillant)",
            description=(
                f"{flips} inversions chaud/froid le long de Z1→Z8 — profil en "
                f"dents de scie. Régulation instable, points chauds/froids "
                f"alternés"
                + (f" amplifiés par un SME élevé ({sme:.2f} kWh/kg)."
                   if sme > SME_WARNING_KWH_PER_KG else
                   ". Lisser le profil en une rampe monotone.")
            ),
            evidence=f"inversions={flips} · SME={sme:.2f} kWh/kg",
            target="Profil thermique",
        ))

    # --- Refroidissement prématuré (avant fin du plateau de fusion) ------
    # Forte baisse de consigne avant Z6 alors que la fusion/dispersion n'est
    # pas terminée.
    idx_z6 = PROCESS_ZONE_ORDER.index("Z6")
    early = [
        (PROCESS_ZONE_ORDER[i], PROCESS_ZONE_ORDER[i + 1], deltas[i])
        for i in range(idx_z6)
        if deltas[i] < -25.0
    ]
    if early:
        za, zb, d = min(early, key=lambda e: e[2])
        out.append(Alert(
            code="THERMAL_EARLY_COOLING",
            severity=SEVERITY_WARNING,
            title=f"Refroidissement prématuré {za}→{zb}",
            description=(
                f"Chute de {d:.0f} °C entre {za} et {zb}, avant la fin du "
                f"plateau de fusion (Z6). Risque de fusion incomplète, de "
                f"figeage et de bouchage en aval."
            ),
            evidence=f"Δ{za}→{zb}={d:.0f} °C (avant Z6)",
            target=f"Zone {zb}",
        ))

    # --- Filière trop froide ---------------------------------------------
    die_t = state.die_temps_C
    die_mean = sum(die_t) / len(die_t)
    t_z8 = seq[-1]
    if die_mean < t_z8 - 40.0:
        out.append(Alert(
            code="DIE_TOO_COLD",
            severity=SEVERITY_CRITICAL,
            title="Filière trop froide",
            description=(
                f"T_die moyenne {die_mean:.0f} °C < T_Z8 {t_z8:.0f} °C "
                f"− 40 °C. Figeage en tête de filière : pic de pression, "
                f"surcouple et arrêt sécurité probables."
            ),
            evidence=f"T_die≈{die_mean:.0f} °C · T_Z8={t_z8:.0f} °C",
            target="Die",
        ))

    # --- Profil die incohérent (rampe non décroissante) ------------------
    if state.n_die_zones >= 2:
        for i in range(len(die_t) - 1):
            if die_t[i + 1] > die_t[i] + 5.0:
                out.append(Alert(
                    code="DIE_PROFILE_INCOHERENT",
                    severity=SEVERITY_WARNING,
                    title="Profil die non décroissant",
                    description=(
                        f"Zone die {i + 2} ({die_t[i + 1]:.0f} °C) plus chaude "
                        f"que la zone die {i + 1} ({die_t[i]:.0f} °C). Le "
                        f"refroidissement de mise en forme doit être monotone "
                        f"décroissant vers la sortie."
                    ),
                    evidence=f"die{i + 1}={die_t[i]:.0f} → die{i + 2}={die_t[i + 1]:.0f} °C",
                    target="Die",
                ))
                break

    # --- Consigne incompatible avec la matière le long du trajet ---------
    transit_zones = list(PROCESS_ZONE_ORDER) + state.die_keys
    for f in active_feeders(state.feeders):
        start = POSITION_TO_LEGACY_ZONE.get(f.position, 0)
        t_max = f.effective_t_max_C()
        worst_zone = ""
        worst_t = -1.0
        for zk in transit_zones:
            zi = POSITION_TO_LEGACY_ZONE.get(zk, 99) if zk in POSITION_TO_LEGACY_ZONE else 99
            in_path = (zk.startswith("die")) or (zi >= start)
            if not in_path:
                continue
            tval = float(zt.get(zk, DEFAULT_ZONE_TARGETS_C.get(zk, 0.0)))
            if tval > t_max and tval > worst_t:
                worst_t = tval
                worst_zone = zk
        if worst_zone:
            out.append(Alert(
                code="ZONE_MATERIAL_INCOMPAT",
                severity=SEVERITY_CRITICAL,
                title=f"Consigne incompatible matière feeder {_feeder_label(f)}",
                description=(
                    f"La matière « {f.material.label_fr} » (injectée en "
                    f"{f.position}) transite par {worst_zone} dont la consigne "
                    f"{worst_t:.0f} °C dépasse sa borne sûre {t_max:.0f} °C. "
                    f"Dégradation thermique programmée par le profil lui-même."
                ),
                evidence=f"{worst_zone}={worst_t:.0f} °C · T_max={t_max:.0f} °C",
                target=f"Feeder #{f.feeder_id}",
            ))
    return out


# Toutes les règles, dans l'ordre d'exécution.
_ALL_RULES = (
    _rule_feeder_position,
    _rule_thermal_compat,
    _rule_powder_overload,
    _rule_fill_factor,
    _rule_sme,
    _rule_residence_time,
    _rule_die_temp_monotony,
    _rule_duplicate_position,
    _rule_cooling,
    _rule_thermal_profile,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def evaluate(state: ProcessState) -> AgentReport:
    """Évalue toutes les règles, agrège le score et l'état, produit le diagnostic."""
    alerts: list[Alert] = []
    for rule_fn in _ALL_RULES:
        alerts.extend(rule_fn(state))

    # Score : on retranche les poids cumulés.
    score = 100
    for a in alerts:
        score -= _SEVERITY_WEIGHTS.get(a.severity, 0)
    score = max(0, min(100, score))

    if score >= 80:
        st = STATE_STABLE
    elif score >= 60:
        st = STATE_WATCH
    else:
        st = STATE_CRITICAL

    diag = _build_diagnostic(state, alerts, st, score)

    # Tri : critique d'abord, puis warning, puis info.
    sev_order = {
        SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1,
        SEVERITY_INFO: 2, SEVERITY_OK: 3,
    }
    alerts.sort(key=lambda a: sev_order.get(a.severity, 99))

    return AgentReport(
        risk_score=score, state=st, alerts=alerts, diagnostic=diag,
    )


def _build_diagnostic(
    state: ProcessState, alerts: list[Alert], st: str, score: int,
) -> str:
    n_crit = sum(1 for a in alerts if a.severity == SEVERITY_CRITICAL)
    n_warn = sum(1 for a in alerts if a.severity == SEVERITY_WARNING)
    n_act = len(active_feeders(state.feeders))
    ff = state.kpis.fill_factor
    rt = state.kpis.residence_time_s
    sme = state.kpis.sme_kwh_per_kg

    if st == STATE_STABLE:
        return (
            f"Procédé nominal : {n_act} feeder(s) actif(s), FF={_fmt_pct(ff)}, "
            f"RT={rt:.1f} s, SME={sme:.2f} kWh/kg. Aucune alerte critique."
        )
    if st == STATE_WATCH:
        return (
            f"Surveillance renforcée : {n_warn} avertissement(s) et "
            f"{n_crit} alerte(s) critique(s). Vérifier les recommandations "
            f"agent avant de poursuivre."
        )
    return (
        f"État critique (score {score}/100) : {n_crit} alerte(s) critique(s) "
        f"+ {n_warn} avertissement(s). Application des recommandations "
        f"agent IA prioritaire avant production."
    )
