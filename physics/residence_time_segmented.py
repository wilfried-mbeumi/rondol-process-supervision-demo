"""residence_time_segmented.py — Modèle V2 segment-par-segment (PUR).

Source : `app/specification_residence_time_extrudeur.pdf` (spec manager travail).

Implémentation des formules de l'annexe « Formules finales à implémenter » :
  - q_vol,i = (mass_flow_i / bulk_density_i) / 3600                 (cm³/s)
  - Q_vol_total,segment = somme des q_vol,i pour feeders avec
                          entry_zone <= segment.start_zone
  - Q_capacity,segment = Q_capacity_ref × RPM_screw / RPM_ref × K_capacity
  - FF_segment = min(Q_vol_total / Q_capacity, 1.0)
  - t_segment = V_free × FF × K_screw × K_material × K_die / Q_vol_total
  - t_feeder,i = somme des t_segment depuis l'entrée du feeder i
  - t_global = somme(t_feeder,i × mass_flow_i) / somme(mass_flow_i)

Module PUR : aucune dépendance Streamlit / disque / autre couche métier.
**NON branché dans l'UI** au premier jet (choix manager 2026-06-09) — sert de
socle testable pour une version 2 à valider expérimentalement (test traceur).

Limitations V2 :
  - le côté filière (K_die appliqué aux segments aval uniquement) n'est PAS
    différencié dans ce module — l'appelant doit composer K_die uniquement
    sur les segments aval s'il veut respecter §8 de la spec.
  - aucune correction matière fine (compaction, fusion PVDF, glissement) :
    K_material est un coefficient unique par segment, à régler par l'appelant
    selon §9 de la spec.
  - aucune gestion de la RTD (distribution) : on calcule UNE moyenne estimée
    par feeder. La queue de distribution / le back-mixing nécessitent un test
    traceur (§13 de la spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# RPM de référence pour la capacité de convoyage (manager 2026-06-09 :
# rpm_ref = 100 rpm). Si une spec PLC différente est confirmée, modifier ici.
DEFAULT_RPM_REFERENCE: float = 100.0


# ---------------------------------------------------------------------------
# Types d'entrée
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FeederInput:
    """Feeder du modèle : nom, zone d'entrée, débit, densité bulk.

    Attributs :
      name           : libellé (Feeder #1, Side feeder Z3…), pour affichage.
      entry_zone     : zone d'entrée dans la vis (0 = Feed, 1..8 = Z1..Z8).
                       Détermine quels segments AVAL sont parcourus.
      mass_flow_g_h  : débit massique calibré (g/h). 0 → feeder désactivé.
      bulk_density_g_cm3 : densité apparente (g/cm³). > 0 obligatoire si actif.
      state          : état matière indicatif (« powder », « pate », « melt »…).
                       Utilisable par l'appelant pour choisir K_material.
    """
    name: str
    entry_zone: int
    mass_flow_g_h: float
    bulk_density_g_cm3: float
    state: str = "powder"


@dataclass(frozen=True)
class SegmentInput:
    """Segment de vis : volume libre + coefficients.

    Attributs :
      name             : libellé pour affichage (Z0→Z1, Kneading 90° pos 18…).
      start_zone       : zone de début (utilisée pour décider qui alimente).
      end_zone         : zone de fin (purement informatif, géré par ordre).
      free_volume_cm3  : volume libre du segment (cm³).
      capacity_ref_cm3_s : capacité volumique de convoyage à rpm_ref (cm³/s).
      k_screw          : coefficient profil vis (1.0 = convoyage référence,
                         >1 = mélange/rétention, voir §7 de la spec).
      k_material       : coefficient matière (1.0 = poudre fluide, voir §9).
      k_die            : coefficient filière (1.0 = pas de filière, voir §8 —
                         l'appelant n'applique k_die qu'aux segments aval).
      k_capacity       : modulateur de capacité spécifique au type d'élément
                         (1.0 par défaut ; voir §4.2 de la spec).
    """
    name: str
    start_zone: int
    end_zone: int
    free_volume_cm3: float
    capacity_ref_cm3_s: float
    k_screw: float = 1.0
    k_material: float = 1.0
    k_die: float = 1.0
    k_capacity: float = 1.0


# ---------------------------------------------------------------------------
# Types de sortie
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SegmentResult:
    """Résultat de calcul pour un segment."""
    name: str
    start_zone: int
    q_total_cm3_s: float
    capacity_cm3_s: float
    fill_factor: float
    residence_time_s: float


@dataclass(frozen=True)
class FeederResult:
    """Temps de séjour par feeder (somme des segments aval depuis son entrée)."""
    name: str
    entry_zone: int
    mass_flow_g_h: float
    residence_time_s: float


@dataclass(frozen=True)
class SegmentedReport:
    """Rapport V2 complet : segments + feeders + global pondéré."""
    segments: tuple[SegmentResult, ...]
    feeders: tuple[FeederResult, ...]
    global_residence_time_s: float | None      # None si débit total nul
    total_mass_flow_g_h: float
    rpm_screw: float
    rpm_reference: float


# ---------------------------------------------------------------------------
# Briques pures (testables individuellement)
# ---------------------------------------------------------------------------
def compute_feeder_volumetric_flow(
    mass_flow_g_h: float, bulk_density_g_cm3: float,
) -> float:
    """q_vol = (mass_flow_g_h / bulk_density) / 3600   en cm³/s.

    Retourne 0.0 si l'un des deux est ≤ 0 (feeder désactivé / non renseigné),
    jamais d'inf/nan : c'est un débit, pas un signal d'erreur.
    """
    m = float(mass_flow_g_h)
    rho = float(bulk_density_g_cm3)
    if m <= 0.0 or rho <= 0.0:
        return 0.0
    return (m / rho) / 3600.0


def compute_segment_capacity(
    capacity_ref_cm3_s: float, rpm_screw: float,
    rpm_reference: float = DEFAULT_RPM_REFERENCE,
    k_capacity: float = 1.0,
) -> float:
    """Q_capacity = Q_ref × RPM/RPM_ref × K_capacity   en cm³/s.

    Si RPM ≤ 0 ou capacity_ref ≤ 0, retourne 0.0 (pas de convoyage).
    """
    cap_ref = float(capacity_ref_cm3_s)
    rpm = float(rpm_screw)
    rpm_ref = float(rpm_reference)
    if cap_ref <= 0.0 or rpm <= 0.0 or rpm_ref <= 0.0:
        return 0.0
    return cap_ref * (rpm / rpm_ref) * float(k_capacity)


def compute_segment_fill_factor(
    q_total_cm3_s: float, capacity_cm3_s: float, ff_max: float = 1.0,
) -> float:
    """FF = min(Q_total / Capacity, ff_max). 0.0 si capacité ou débit nul."""
    q = float(q_total_cm3_s)
    cap = float(capacity_cm3_s)
    if q <= 0.0 or cap <= 0.0:
        return 0.0
    return min(q / cap, float(ff_max))


def compute_segment_residence_time(
    free_volume_cm3: float, fill_factor: float, q_total_cm3_s: float,
    k_screw: float = 1.0, k_material: float = 1.0, k_die: float = 1.0,
) -> float:
    """t_segment = V × FF × K_screw × K_material × K_die / Q_total   en s.

    0.0 si le débit total est nul (segment non alimenté).
    """
    q = float(q_total_cm3_s)
    if q <= 0.0:
        return 0.0
    return (
        float(free_volume_cm3) * float(fill_factor)
        * float(k_screw) * float(k_material) * float(k_die)
    ) / q


def compute_feeder_residence_time(
    feeder: FeederInput, segment_results: tuple[SegmentResult, ...],
) -> float:
    """Somme des temps de séjour des segments AVAL de l'entrée du feeder.

    Règle fondamentale §3 : un feeder entré en Zk ne cumule que les segments
    avec start_zone >= entry_zone.
    """
    return sum(
        seg.residence_time_s for seg in segment_results
        if seg.start_zone >= int(feeder.entry_zone)
    )


def compute_global_weighted_residence_time(
    feeder_results: tuple[FeederResult, ...],
) -> float | None:
    """Moyenne pondérée par débit massique : Σ(t_i × ṁ_i) / Σ(ṁ_i).

    Retourne None si Σ(ṁ_i) = 0 (aucun feeder actif), JAMAIS 0.0 qui serait
    interprété comme « résidence nulle » côté UI.
    """
    total_mass = sum(f.mass_flow_g_h for f in feeder_results)
    if total_mass <= 0.0:
        return None
    weighted = sum(f.residence_time_s * f.mass_flow_g_h for f in feeder_results)
    return weighted / total_mass


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_segmented_report(
    feeders: list[FeederInput] | tuple[FeederInput, ...],
    segments: list[SegmentInput] | tuple[SegmentInput, ...],
    rpm_screw: float,
    rpm_reference: float = DEFAULT_RPM_REFERENCE,
) -> SegmentedReport:
    """Construit le rapport segmenté complet.

    Algorithme (cf. §11 de la spec, pseudocode adapté en Python pur) :
      1. q_vol par feeder.
      2. Pour chaque segment : q_total = somme des q_vol_i avec
         entry_zone_i <= segment.start_zone (feeders déjà entrés).
      3. capacity = Q_ref × rpm / rpm_ref × K_capacity.
      4. FF = min(q_total / capacity, 1.0).
      5. t_segment = V × FF × K_screw × K_material × K_die / q_total.
      6. t_feeder = somme des t_segment aval de son entrée.
      7. t_global = moyenne pondérée par ṁ.

    Tous les segments avec q_total = 0 ont FF = 0 et t = 0 (jamais d'erreur).
    """
    feeders_t = tuple(feeders)
    segments_t = tuple(segments)

    # 1) Débits volumiques par feeder.
    qvol_by_feeder: dict[str, float] = {
        f.name: compute_feeder_volumetric_flow(f.mass_flow_g_h, f.bulk_density_g_cm3)
        for f in feeders_t
    }

    # 2-5) Calcul segment par segment.
    seg_results: list[SegmentResult] = []
    for seg in segments_t:
        # q_total = somme des q_vol des feeders dont entry_zone <= start_zone.
        q_total = sum(
            qvol_by_feeder[f.name] for f in feeders_t
            if int(f.entry_zone) <= int(seg.start_zone)
        )
        capacity = compute_segment_capacity(
            seg.capacity_ref_cm3_s, rpm_screw, rpm_reference, seg.k_capacity,
        )
        ff = compute_segment_fill_factor(q_total, capacity)
        t_seg = compute_segment_residence_time(
            seg.free_volume_cm3, ff, q_total,
            seg.k_screw, seg.k_material, seg.k_die,
        )
        seg_results.append(SegmentResult(
            name=seg.name, start_zone=seg.start_zone,
            q_total_cm3_s=q_total, capacity_cm3_s=capacity,
            fill_factor=ff, residence_time_s=t_seg,
        ))
    seg_results_t = tuple(seg_results)

    # 6) Temps de séjour par feeder.
    feeder_results: list[FeederResult] = []
    for f in feeders_t:
        t_f = compute_feeder_residence_time(f, seg_results_t)
        feeder_results.append(FeederResult(
            name=f.name, entry_zone=f.entry_zone,
            mass_flow_g_h=f.mass_flow_g_h, residence_time_s=t_f,
        ))
    feeder_results_t = tuple(feeder_results)

    # 7) Moyenne pondérée globale.
    t_global = compute_global_weighted_residence_time(feeder_results_t)
    total_mass = sum(f.mass_flow_g_h for f in feeders_t)

    return SegmentedReport(
        segments=seg_results_t,
        feeders=feeder_results_t,
        global_residence_time_s=t_global,
        total_mass_flow_g_h=total_mass,
        rpm_screw=float(rpm_screw),
        rpm_reference=float(rpm_reference),
    )
