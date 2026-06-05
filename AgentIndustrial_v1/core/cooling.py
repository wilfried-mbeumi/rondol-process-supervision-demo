"""
cooling.py — Modèle thermique procédé (T réelle par zone).

Équation manager (Maël Gallas, references/manager_requirements/Gmail_modele_thermique.pdf) :

    T_real,i = T_set,i + (2πN·M)/(ṁ·Cp) + k·τ

où :
  - (2πN·M)/ṁ = SME (Specific Mechanical Energy) — estimé par
    core.screw_adapter à partir de rpm, couple et débit ;
  - (2πN·M)/(ṁ·Cp) = SME/Cp = élévation adiabatique théorique du fondu ;
  - k·τ = terme correctif de cisaillement (couple → échauffement local) ;
  - une fraction de rétention η ramène l'élévation à des ordres de grandeur
    réels HME (+15 à +55 °C au pic de malaxage).

Facteurs de correction LOCAUX (exigence manager 2026-05-20 — la T réelle
ne doit pas dépendre uniquement de la matière, mais aussi de la mécanique
d'extrusion réelle) :
  - profil de cisaillement par zone reconstruit depuis la configuration vis :
    densité réelle d'éléments de malaxage (kneading 30/45/60/90°, mélange
    spécial, dentelé, pas court, reverse) vs convoyage (forward, grand pas)
    sur les positions de chaque zone ;
  - fill ratio (matière cisaillée en volume) ;
  - résidence par zone (efficacité de mélange / accumulation locale) ;
  - dilatation thermique α et viscosité η des matières feeders (friction
    pariétale + dissipation visqueuse).

Le « test de refroidissement » opérateur n'existe pas — fonctionnalité retirée
en 2026-05-20. Le diagnostic thermique cible automatiquement la zone la plus
chaude calculée par le modèle.

Sortie consommée par `core.rules` (alertes) et `core.recommendations`
(actions chiffrées). Module PUR : lit ProcessState (KPIs déjà rafraîchis),
ne mute rien.

Sources : Gmail_modele_thermique.pdf (Maël Gallas, 19/05/2026), pratique
compounding bivis (Coperion/Leistritz), littérature SSB (Schubert 2023,
Klemens 2024).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .feeders import POSITION_TO_LEGACY_ZONE, active_feeders
from .process import (
    DEFAULT_ZONE_TARGETS_C,
    ProcessState,
    SME_CRITICAL_KWH_PER_KG,
    THERMAL_REG_BAND_C,
)

# Zones procédé pilotables côté refroidissement (la filière est gérée par R7).
ZONES: tuple[str, ...] = ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8")

# Profil de cisaillement par défaut — fallback quand la configuration vis
# est vide ou trop peu informative. Sert de seed avant pondération par les
# éléments réellement placés. Override dynamique par _shear_profile_from_config.
SHEAR_PROFILE_DEFAULT: dict[str, float] = {
    "Z1": 0.15, "Z2": 0.35, "Z3": 0.60, "Z4": 0.85,
    "Z5": 1.00, "Z6": 0.90, "Z7": 0.55, "Z8": 0.38,
}

# Intensité de cisaillement par type d'élément (cf. ELEMENT_TYPES de
# app/screw_logic.py). Ordre de grandeur basé sur la pratique compounding
# bivis : convoyage doux ≈ 0,15 → kneading 90° ≈ 1,0 → reverse ≈ 1,1.
# Les éléments mixage spécial / dentelé / chaotique génèrent un cisaillement
# intense et localisé (pic d'échauffement).
_ELEMENT_SHEAR_INTENSITY: dict[int, float] = {
    0:  0.05,   # vide
    1:  0.15,   # Forward conveying (transport)
    2:  0.12,   # Forward half (transport)
    3:  0.55,   # Short-pitch (compression, début cisaillement)
    4:  1.00,   # Kneading 90° (pic dispersif)
    5:  0.60,   # Kneading 30° (mélange distributif doux)
    6:  0.10,   # Large pitch (décompression, faible cisaillement)
    7:  0.80,   # Kneading 60° (dispersif modéré)
    8:  0.70,   # Kneading 45° (équilibre dispersif/distributif)
    9:  1.10,   # Reverse conveying (sur-cisaillement → pic local)
    10: 0.95,   # Chaotique
    11: 0.85,   # Dentelé
    12: 0.90,   # Mélange spécial
    13: 0.20,   # Pointe + décharge (sortie)
}

# Mapping zone Z1..Z8 → plage de positions correspondante dans la vis
# (cohérent avec START_ELMT_ZONE de screw_logic : 0-8 Feed, 9-17 Z1, etc.).
# Hardcodé ici pour ne pas dépendre de screw_logic au moment du calcul (le
# module reste pur et ne crée pas de cycle d'import).
_ZONE_POSITION_RANGES: dict[str, tuple[int, int]] = {
    "Z1": (9, 17),   "Z2": (18, 26),  "Z3": (27, 35),  "Z4": (36, 44),
    "Z5": (45, 53),  "Z6": (54, 62),  "Z7": (63, 71),  "Z8": (72, 80),
}

# Cohérent avec core.screw_adapter.RPM_NOMINAL_MAX (micro-bivis 10,5 mm).
RPM_NOMINAL_MAX: float = 300.0

# --- Paramètres de l'équation manager T_real = T_set + SME/Cp + k·τ --------
# Cp fondu polymère/compound SSB chargé : ordre de grandeur HME classique
# 1,8-2,4 kJ/(kg·K). 2000 J/(kg·K) retenu (valeur de travail, ajustable si
# une mesure DSC est fournie).
CP_MELT_J_PER_KG_K: float = 2000.0

# Fraction de l'élévation adiabatique SME/Cp qui se manifeste réellement
# comme élévation sensible LOCALE du fondu au-dessus de la consigne fourreau.
# Le complément part en échange thermique fourreau, enthalpie de fusion et
# pertes. Calée pour reproduire les ordres de grandeur HME mesurés
# (+15 à +55 °C au plateau de malaxage en régime intensif).
HEAT_RETENTION_FRACTION: float = 0.085

# k du terme correctif k·τ : °C d'échauffement local supplémentaire par
# unité de charge couple normalisée et de poids de cisaillement de zone.
K_TAU: float = 14.0

# Contribution friction matière (dilatation thermique α des feeders solides).
K_FEED: float = 7.0
DT_VISC_CAP: float = 130.0
DT_FEED_CAP: float = 22.0

# Marge procédé au-dessus de la consigne quand aucune contrainte matière ne
# fixe le plafond de la zone (poudre active = contrainte prioritaire sinon).
DEGRAD_HEADROOM_C: float = 35.0

# Référence α : poudre active SSB ~ 5e-5 /K (cf. core.feeders).
ALPHA_REF: float = 5.0e-5


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class ZoneThermal:
    """Bilan thermique d'une zone procédé."""
    zone: str
    t_target_C: float
    t_est_C: float
    dT_C: float                 # élévation au-dessus de la consigne
    cooling_demand_pct: float   # 0..100 — besoin de refroidissement
    status: str                 # "ok" | "watch" | "overheat"
    t_limit_C: float = 0.0      # plafond métier (contrainte matière/procédé)
    limit_source: str = ""      # "matière #k" | "procédé" — traçabilité


@dataclass
class CoolingModel:
    """Vue thermique complète + index global d'instabilité."""
    zones: dict[str, ZoneThermal] = field(default_factory=dict)
    hottest_zone: str = "Z5"
    instability_index: float = 0.0   # 0..1
    torque_load: float = 0.0         # 0..1 (mesuré ou estimé)
    torque_measured: bool = False
    # Diagnostic profil vis — utile pour traçabilité IA (T réelle ne dépend
    # pas que de la matière mais aussi de la mécanique d'extrusion).
    kneading_density: dict[str, float] = field(default_factory=dict)
    conveying_density: dict[str, float] = field(default_factory=dict)


def die_back_pressure(state: ProcessState) -> float:
    """Surcouple normalisé induit par la filière (0..~0.27).

    Une filière froide vs le plateau de malaxage augmente la viscosité du
    fondu → contre-pression en tête → couple plus élevé. Davantage de zones
    die = restriction d'écoulement supplémentaire. C'est par ce terme que le
    profil thermique die influence couple / SME / instabilité.
    """
    plateau = sum(
        float(state.zone_temps_C.get(z, DEFAULT_ZONE_TARGETS_C[z]))
        for z in ("Z4", "Z5", "Z6")
    ) / 3.0
    die_t = state.die_temps_C
    die_mean = sum(die_t) / len(die_t) if die_t else plateau
    # Au-delà de 20 °C d'écart plateau→die, la contre-pression monte.
    back = _clamp((plateau - die_mean - 20.0) / 130.0, 0.0, 0.22)
    back += 0.02 * (len(die_t) - 1)  # +restriction par zone die additionnelle
    return _clamp(back, 0.0, 0.27)


def _torque_load(state: ProcessState) -> tuple[float, bool]:
    """Charge couple normalisée 0..1. Mesurée (V2) sinon proxy FF/rpm + die.

    Aligné sur core.screw_adapter.estimate_sme_kwh_per_kg pour la cohérence
    du raisonnement agent, augmenté de la contre-pression filière (le profil
    thermique die agit donc réellement sur le couple estimé).
    """
    t = state.v2.torque_pct
    if t is not None:
        return _clamp(t / 100.0, 0.0, 1.0), True
    ff = _clamp(state.kpis.fill_factor, 0.0, 1.0)
    rpm_n = _clamp(state.screw_rpm / RPM_NOMINAL_MAX, 0.0, 1.0)
    base = 0.20 + 0.55 * ff + 0.20 * rpm_n
    return _clamp(base + die_back_pressure(state), 0.05, 1.0), False


def _archetype_multiplier(state: ProcessState) -> float:
    """Modulation globale du cisaillement par l'archétype profil (couche IA Kévin)."""
    a = (state.kpis.profile_archetype or "").lower()
    if any(k in a for k in ("dispers", "intens", "malax", "knead", "cisaill", "shear")):
        return 1.15
    if any(k in a for k in ("convoy", "transport", "doux", "soft", "feed")):
        return 0.90
    return 1.0


def _base_type(v: int) -> int:
    """Décodage interne (évite l'import de screw_logic pour rester pur)."""
    return v - 100 if v >= 100 else v


def _shear_profile_from_config(
    screw_config: list[int],
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Construit le profil de cisaillement réel à partir de la config vis.

    Calcule pour chaque zone Z1..Z8 :
      - densité de cisaillement (poids 0..~1) basée sur l'intensité moyenne
        des éléments présents (kneading > convoyage). Mixage local + intensité
        process déduits du mix d'éléments réellement placés ;
      - part d'éléments de malaxage (kneading + dispersifs + reverse) ;
      - part d'éléments de convoyage (forward + grand pas).

    Si la config est vide / non informative, on retombe sur SHEAR_PROFILE_DEFAULT.
    """
    if not screw_config:
        return (
            dict(SHEAR_PROFILE_DEFAULT),
            {z: 0.0 for z in ZONES},
            {z: 0.0 for z in ZONES},
        )

    shear: dict[str, float] = {}
    knead_dens: dict[str, float] = {}
    conv_dens: dict[str, float] = {}
    kneading_ids = (3, 4, 5, 7, 8, 9, 10, 11, 12)
    forward_ids = (1, 2, 6)

    for zone, (start, end) in _ZONE_POSITION_RANGES.items():
        intensities: list[float] = []
        n_k = 0
        n_c = 0
        n_total = 0
        for pos in range(start, min(end + 1, len(screw_config))):
            v = _base_type(screw_config[pos])
            if v == 0:
                continue
            intensities.append(_ELEMENT_SHEAR_INTENSITY.get(v, 0.5))
            n_total += 1
            if v in kneading_ids:
                n_k += 1
            elif v in forward_ids:
                n_c += 1
        if intensities:
            mean_int = sum(intensities) / len(intensities)
            # Pondération supplémentaire : un nombre élevé d'éléments de
            # malaxage concentrés sur une zone amplifie le pic local.
            density_boost = 1.0 + 0.15 * (n_k / max(1, n_total))
            shear[zone] = max(0.0, min(1.2, mean_int * density_boost))
        else:
            shear[zone] = SHEAR_PROFILE_DEFAULT.get(zone, 0.5)
        knead_dens[zone] = (n_k / n_total) if n_total else 0.0
        conv_dens[zone] = (n_c / n_total) if n_total else 0.0
    return shear, knead_dens, conv_dens


def _viscosity_multiplier(state: ProcessState) -> float:
    """Modulation globale par la viscosité des feeders actifs (rhéologie).

    Moyenne pondérée du facteur viscosité de chaque feeder par son débit
    massique. Si aucun feeder n'a de viscosité renseignée → 1.0 (neutre).
    """
    total_flow = 0.0
    weighted = 0.0
    has_data = False
    for f in active_feeders(state.feeders):
        if f.viscosity_pa_s is None or f.viscosity_pa_s <= 0:
            continue
        has_data = True
        total_flow += f.mass_flow_g_per_min
        weighted += f.mass_flow_g_per_min * f.viscosity_factor()
    if not has_data or total_flow <= 0:
        return 1.0
    return max(0.7, min(1.8, weighted / total_flow))


def _residence_norm(state: ProcessState) -> dict[str, float]:
    """Résidence par zone normalisée 0..1 (index 0=Feed, 1..8=Z1..Z8)."""
    rz = state.kpis.zone_residence_s or []
    vals = [rz[i] if i < len(rz) else 0.0 for i in range(1, 9)]
    mx = max(vals) if vals else 0.0
    if mx <= 0.0:
        return {z: 0.5 for z in ZONES}
    return {ZONES[i]: _clamp(vals[i] / mx, 0.0, 1.0) for i in range(8)}


def _upstream_solid(state: ProcessState) -> tuple[dict[str, float], dict[str, float]]:
    """Pour chaque zone : fraction du débit solide ayant déjà transité + α équivalent.

    Un feeder injecté en position p « alimente » toutes les zones d'index ≥ p.
    Plus une zone est en aval d'une grosse charge solide, plus la friction
    pariétale (et donc l'échauffement) y est élevée.
    """
    solids = [f for f in active_feeders(state.feeders) if f.is_solid]
    total = sum(f.mass_flow_g_per_min for f in solids)
    frac: dict[str, float] = {}
    alpha_eq: dict[str, float] = {}
    for k, zone in enumerate(ZONES, start=1):
        if total <= 0.0:
            frac[zone] = 0.0
            alpha_eq[zone] = ALPHA_REF
            continue
        flow = 0.0
        weighted_a = 0.0
        for f in solids:
            if POSITION_TO_LEGACY_ZONE.get(f.position, 0) <= k:
                flow += f.mass_flow_g_per_min
                weighted_a += f.mass_flow_g_per_min * f.thermal_expansion_per_K
        frac[zone] = _clamp(flow / total, 0.0, 1.0)
        alpha_eq[zone] = (weighted_a / flow) if flow > 0 else ALPHA_REF
    return frac, alpha_eq


def _zone_thermal_limit(
    state: ProcessState, zone: str, t_target: float,
) -> tuple[float, str]:
    """Plafond thermique métier d'une zone (T au-delà de laquelle il FAUT
    refroidir), dérivé du procédé — plus aucun dial opérateur.

    Priorité à la contrainte matière : toute poudre solide injectée en amont
    et transitant cette zone impose sa borne haute effective
    (FeederSpec.effective_t_max_C — t_degradation_C > tga_onset_C > défaut
    famille matière).
    À défaut, plafond = consigne + marge procédé DEGRAD_HEADROOM_C.
    """
    zi = zone_index(zone)  # 1..8
    strict_t = float("inf")
    src = ""
    for f in active_feeders(state.feeders):
        if not f.is_solid:
            continue
        if POSITION_TO_LEGACY_ZONE.get(f.position, 99) > zi:
            continue  # injectée en aval : ne transite pas cette zone
        t_max = f.effective_t_max_C()
        if t_max < strict_t:
            strict_t = t_max
            src = f"matière #{f.feeder_id}"
    proc_limit = t_target + DEGRAD_HEADROOM_C
    if strict_t == float("inf") or proc_limit < strict_t:
        return proc_limit, (src and "procédé" or "procédé")
    return strict_t, src


def _status(t_est: float, t_target: float, t_limit: float) -> str:
    """Statut zone — indexé sur le plafond métier dérivé et la bande de
    régulation procédé THERMAL_REG_BAND_C (aucun réglage opérateur).
    """
    band = t_target + THERMAL_REG_BAND_C
    if t_est >= t_limit:
        return "overheat"
    span = max(1.0, t_limit - band)
    demand = 100.0 * (t_est - band) / span
    if demand >= 70.0:
        return "overheat"
    if demand >= 25.0 or t_est > band:
        return "watch"
    return "ok"


def compute_cooling(state: ProcessState) -> CoolingModel:
    """Construit le modèle thermique complet depuis l'état procédé réel.

    Pré-condition : state.kpis doit avoir été rafraîchi (screw_adapter).
    """
    ff = _clamp(state.kpis.fill_factor, 0.0, 1.0)
    sme = max(0.0, state.kpis.sme_kwh_per_kg)
    tload, t_measured = _torque_load(state)
    arch_mult = _archetype_multiplier(state)
    res_norm = _residence_norm(state)
    frac, alpha_eq = _upstream_solid(state)
    # Profil de cisaillement réel reconstruit depuis la config vis
    # (mixage / convoyage / pas court / reverse / intensité process).
    shear_profile, knead_dens, conv_dens = _shear_profile_from_config(state.screw_config)
    # Rhéologie : viscosité moyenne pondérée des matières → amplificateur
    # global de dissipation visqueuse.
    visc_mult = _viscosity_multiplier(state)

    # Élévation adiabatique théorique du fondu : SME/Cp (équation manager).
    # SME [kWh/kg] → J/kg (×3,6e6), divisé par Cp [J/(kg·K)] → ΔT [K].
    dT_adiabatic = (sme * 3.6e6) / CP_MELT_J_PER_KG_K
    # Fill ratio correction factor (matière cisaillée en volume).
    fill_corr = 0.35 + 0.65 * ff

    zones: dict[str, ZoneThermal] = {}
    max_dT = 0.0
    hottest = "Z5"

    for zone in ZONES:
        t_target = float(
            state.zone_temps_C.get(zone, DEFAULT_ZONE_TARGETS_C[zone])
        )
        # Poids de cisaillement local : profil zone (issu des éléments vis
        # réellement placés) × archétype global × efficacité mélange / accu.
        shear_w = shear_profile.get(zone, SHEAR_PROFILE_DEFAULT[zone]) \
            * arch_mult * (0.6 + 0.4 * res_norm[zone])

        # Terme (2πN·M)/(ṁ·Cp) = SME/Cp, fraction retenue localement,
        # pondéré par les facteurs de correction + viscosité matière.
        dT_visc = _clamp(
            HEAT_RETENTION_FRACTION * dT_adiabatic * shear_w * fill_corr * visc_mult,
            0.0, DT_VISC_CAP,
        )
        # Terme correctif de cisaillement k·τ (couple → échauffement local).
        # Multiplié par viscosité matière : matière plus visqueuse dissipe plus
        # d'énergie mécanique en chaleur à couple égal.
        dT_shear = K_TAU * tload * shear_w * visc_mult
        # Friction matière (dilatation thermique α des feeders solides).
        dT_feed = _clamp(
            K_FEED * frac[zone] * (alpha_eq[zone] / ALPHA_REF),
            0.0, DT_FEED_CAP,
        )

        dT = dT_visc + dT_shear + dT_feed
        t_est = t_target + dT

        t_limit, limit_src = _zone_thermal_limit(state, zone, t_target)
        band = t_target + THERMAL_REG_BAND_C
        span = max(1.0, t_limit - band)
        cooling_demand = (
            _clamp(100.0 * (t_est - band) / span, 0.0, 100.0)
            if t_est > band else 0.0
        )

        zones[zone] = ZoneThermal(
            zone=zone,
            t_target_C=t_target,
            t_est_C=t_est,
            dT_C=dT,
            cooling_demand_pct=cooling_demand,
            status=_status(t_est, t_target, t_limit),
            t_limit_C=t_limit,
            limit_source=limit_src,
        )
        if dT > max_dT:
            max_dT = dT
            hottest = zone

    instability = (
        0.30 * _clamp(sme / SME_CRITICAL_KWH_PER_KG, 0.0, 1.0)
        + 0.25 * _clamp(ff / 0.65, 0.0, 1.0)
        + 0.25 * _clamp(max_dT / 45.0, 0.0, 1.0)
        + 0.20 * tload
    )

    return CoolingModel(
        zones=zones,
        hottest_zone=hottest,
        instability_index=_clamp(instability, 0.0, 1.0),
        torque_load=tload,
        torque_measured=t_measured,
        kneading_density=knead_dens,
        conveying_density=conv_dens,
    )


def zone_index(zone: str) -> int:
    """Index 1..8 d'une zone Zk (utilitaire 'refroidissement trop tardif')."""
    try:
        return ZONES.index(zone) + 1
    except ValueError:
        return 0
