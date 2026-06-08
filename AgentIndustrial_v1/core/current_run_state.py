"""current_run_state.py — source de vérité STRUCTURÉE du run opérateur (P3.1).

Couche PURE et ADDITIVE (aucune dépendance Streamlit, aucune écriture session).
Elle ENVELOPPE l'état opérateur déjà calculé par l'existant — elle ne recalcule
RIEN et ne modifie aucune formule/constante métier :

  - état procédé : `state_sync.state_from_session` (snapshot validé `applied`
    prioritaire, sinon pont legacy) → fournit profil vis, rpm, densité, zones,
    feeders et KPIs (fill factor / résidence / SME / volume libre) déjà calculés ;
  - étalonnage feeder : socle pur `physics.feeder_flow.resolve_feeder_flow`.

Chaque grandeur est enveloppée dans un `Field` portant :
    value · unit · source · validation_status · comment

Règles (exigence manager) :
  - champ absent → `NOT_AVAILABLE`, jamais inventé ;
  - valeurs calculées → `CALCULATED`, statut `CALCULATED_WITH_ASSUMPTIONS` tant
    que les constantes DB automate (DataScrewElmt) et la correction bivis ×2
    (hors PLC) ne sont pas validées Rondol — JAMAIS `CONFIRMED` ;
  - `current_run_state` ≠ `demo_ml_run` : cette couche ne contient AUCUNE donnée
    du dataset ML de démonstration (score de stabilité, durée d'essai, capteurs).

À ce stade (P3.1) AUCUNE page n'est branchée dessus : fondation testable seule.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

# Bootstrap sys.path : racine repo (pour `physics`) — même convention que
# screw_adapter. Aucun effet de bord métier.
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from physics.feeder_flow import FeederFlow, resolve_feeder_flow  # noqa: E402
from physics.multi_feeder import (  # noqa: E402
    FeederCalibration,
    MultiFeederResult,
    resolve_multi_feeder,
)

from .applied_state import get_applied
from .coercion import safe_float, safe_int
from .process import ProcessState
from .state_sync import state_from_session


# ---------------------------------------------------------------------------
# Taxonomies (foyer canonique — réutilisées par les couches app en P3.2+)
# ---------------------------------------------------------------------------
# Provenance d'une donnée.
USER_INPUT = "USER_INPUT"
UPLOADED_DATA = "UPLOADED_DATA"
DEMO_DATA = "DEMO_DATA"
DEFAULT_CONFIG = "DEFAULT_CONFIG"
CALCULATED = "CALCULATED"
NOT_AVAILABLE = "NOT_AVAILABLE"

SOURCE_TYPES = (
    USER_INPUT, UPLOADED_DATA, DEMO_DATA, DEFAULT_CONFIG, CALCULATED, NOT_AVAILABLE,
)

# Statut de validation d'un RÉSULTAT.
CALCULATED_CONFIRMED = "CALCULATED_CONFIRMED"
CALCULATED_WITH_ASSUMPTIONS = "CALCULATED_WITH_ASSUMPTIONS"
NOT_VALIDATED = "NOT_VALIDATED"
NOT_APPLICABLE = "NOT_APPLICABLE"

# État de confiance des constantes de la chaîne fill factor (cf. audit PLC) :
# valeurs par élément issues du DB automate (DataScrewElmt) NON re-vérifiées, et
# correction bivis ×2 absente du PLC → les sorties FF/résidence restent « avec
# hypothèses ». Centralisé ici pour P3 (miroir de app/calc_audit).
DB_CONSTANTS_CONFIRMED: bool = False
BIVIS_CORRECTION_IS_MANAGER: bool = True

# Clés session (contrat partagé avec app/feeder_ui & app/app_mode — recopiées
# ici pour ne PAS créer de dépendance core → app).
_FEEDER_RPM_KEY = "feeder_rpm"
_FEEDER_CALIB_KEY = "feeder_calib_g_h_per_rpm"
_DEMO_MODE_KEY = "demo_mode"
_TARGET_COUNT_KEY = "target_screw_count"

# Défauts TECHNIQUES (provenance DEFAULT_CONFIG tant que la valeur ne s'en écarte
# pas). Exigence : un défaut ne doit jamais être étiqueté USER_INPUT.
_DEFAULT_SCREW_RPM = 120.0
_DEFAULT_BULK_DENSITY = 0.55
_DEFAULT_N_DIE = 1
_DEFAULT_TARGET_COUNT = 40   # standard Rondol validé manager


def _param_provenance(value: Any, default: Any) -> str:
    """USER_INPUT si la valeur diffère du défaut technique, sinon DEFAULT_CONFIG."""
    return USER_INPUT if value != default else DEFAULT_CONFIG


@dataclass(frozen=True)
class Field:
    """Une grandeur tracée : valeur + unité + provenance + statut + commentaire."""
    value: Any
    unit: str = ""
    source: str = NOT_AVAILABLE
    validation_status: str = NOT_APPLICABLE
    comment: str = ""

    @property
    def available(self) -> bool:
        return self.source != NOT_AVAILABLE


@dataclass(frozen=True)
class CurrentRunState:
    """État du run opérateur courant — source de vérité unique (config opérateur).

    NE contient PAS les données du dataset ML de démonstration (`demo_ml_run`).
    """
    run_id: Field
    source_type: str
    screw_profile: Field
    feeder_calibration: Field
    feed_rate: Field
    material_context: Field
    process_parameters: dict[str, Field] = field(default_factory=dict)
    calculated_outputs: dict[str, Field] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    validation_status: str = NOT_VALIDATED
    demo_flags: dict[str, bool] = field(default_factory=dict)
    # Banc multi-feeder résolu (débit par feeder + total) — None si non construit.
    feeders: MultiFeederResult | None = None


# ---------------------------------------------------------------------------
# Lecture défensive (dict ou proxy Streamlit) — lecture seule, aucune écriture
# ---------------------------------------------------------------------------
def _get(session: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        if key in session:
            return session[key]
    except Exception:  # pragma: no cover - proxy hors contexte
        pass
    return default


def _outputs_status() -> str:
    """Statut des sorties de la chaîne fill factor selon l'état des constantes."""
    if DB_CONSTANTS_CONFIRMED and not BIVIS_CORRECTION_IS_MANAGER:
        return CALCULATED_CONFIRMED
    return CALCULATED_WITH_ASSUMPTIONS


def _assumptions() -> tuple[str, ...]:
    out: list[str] = []
    if not DB_CONSTANTS_CONFIRMED:
        out.append("Constantes vis (DB automate DataScrewElmt) non confirmées.")
    if BIVIS_CORRECTION_IS_MANAGER:
        out.append("Correction bivis ×2 (volume) validée manager, hors PLC d'origine.")
    return tuple(out)


def _material_field(state: ProcessState) -> Field:
    """Matière = polymères réellement saisis (Settings) ; sinon « Non renseigné ».

    Aucune chimie inventée : si aucun feeder actif ne porte de `polymer_name`
    saisi, la matière est NOT_AVAILABLE.
    """
    names: list[str] = []
    for f in state.feeders:
        if getattr(f, "enabled", False):
            poly = (getattr(f, "polymer_name", "") or "").strip()
            if poly:
                names.append(poly)
    if names:
        return Field(
            value=" + ".join(names), unit="", source=USER_INPUT,
            validation_status=NOT_APPLICABLE,
            comment="Polymère(s) saisi(s) côté feeders.",
        )
    return Field(
        value="Non renseigné", unit="", source=NOT_AVAILABLE,
        validation_status=NOT_APPLICABLE,
        comment="Aucune saisie matière (polymère) — saisir dans Settings.",
    )


def _feeder_calibrations(session: Mapping[str, Any], state: ProcessState) -> list[FeederCalibration]:
    """Construit les entrées d'étalonnage MULTI-feeder depuis session + feeders.

    Migration legacy : le feeder #1 réutilise les clés historiques
    (`feeder_rpm` / `feeder_calib_g_h_per_rpm`). Les feeders #2..N utilisent
    `feedcal_rpm_{id}` / `feedcal_coeff_{id}`. enabled / label / matière saisie
    proviennent du banc FeederSpec (Settings). Aucune matière inventée.
    """
    cals: list[FeederCalibration] = []
    for f in state.feeders:
        fid = int(f.feeder_id)
        if fid == 1:
            rpm = safe_float(_get(session, _FEEDER_RPM_KEY, 30.0), 30.0, 0.0, 100000.0)
            coeff_raw = safe_float(_get(session, _FEEDER_CALIB_KEY, 0.0), 0.0, 0.0, 100000.0)
        else:
            rpm = safe_float(_get(session, f"feedcal_rpm_{fid}", 0.0), 0.0, 0.0, 100000.0)
            coeff_raw = safe_float(_get(session, f"feedcal_coeff_{fid}", 0.0), 0.0, 0.0, 100000.0)
        poly = (getattr(f, "polymer_name", "") or "").strip()
        cals.append(FeederCalibration(
            feeder_id=fid,
            label=(f.label or f"Feeder {fid}"),
            enabled=bool(getattr(f, "enabled", False)),
            rpm=rpm,
            coeff_g_h_per_rpm=(coeff_raw if coeff_raw > 0.0 else None),
            material_label=poly,
            material_source=(USER_INPUT if poly else NOT_AVAILABLE),
        ))
    return cals


def _feeder_fields(session: Mapping[str, Any], state: ProcessState
                   ) -> tuple[Field, Field, MultiFeederResult]:
    """(feeder_calibration[feeder #1, compat], feed_rate[TOTAL multi], banc).

    feed_rate = débit TOTAL des feeders calculables (somme des OK). Non
    calculable si aucun feeder OK. feeder_calibration reste le feeder #1 (compat
    avec l'étalonnage simple Profile).
    """
    multi = resolve_multi_feeder(_feeder_calibrations(session, state))

    # Feeder #1 (compat affichage étalonnage simple).
    line1 = next((l for l in multi.lines if l.feeder_id == 1), None)
    ff1: FeederFlow = line1.flow if line1 is not None else resolve_feeder_flow(0.0, None)
    if ff1.calibrated:
        calib_field = Field(value=ff1, unit="g/h/RPM", source=USER_INPUT,
                            validation_status=NOT_APPLICABLE,
                            comment="Étalonnage externe feeder #1 (RPM × coefficient).")
    else:
        calib_field = Field(value=ff1, unit="g/h/RPM", source=NOT_AVAILABLE,
                            validation_status=NOT_VALIDATED,
                            comment="Coefficient d'étalonnage feeder #1 non renseigné.")

    # Débit TOTAL (somme des feeders OK).
    if multi.total_calculable:
        note = (" Total incomplet : un feeder actif n'est pas étalonné."
                if multi.has_uncalibrated_active else "")
        feed_field = Field(value=multi.total_g_h, unit="g/h", source=CALCULATED,
                           validation_status=CALCULATED_WITH_ASSUMPTIONS,
                           comment="Débit total = somme des feeders étalonnés." + note)
    else:
        feed_field = Field(value=None, unit="g/h", source=NOT_AVAILABLE,
                           validation_status=NOT_VALIDATED,
                           comment="Débit total non calculable : aucun feeder étalonné.")
    return calib_field, feed_field, multi


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------
def build_current_run_state(session: Mapping[str, Any]) -> CurrentRunState:
    """Construit le `CurrentRunState` (PUR, lecture seule, idempotent).

    Enveloppe l'état opérateur existant — ne recalcule rien, ne mute pas la
    session. Deux appels avec la même session renvoient un état égal.
    """
    state = state_from_session(session)              # ne mute pas la session
    snap = get_applied(session)
    run_id_src = USER_INPUT if snap is not None else DEFAULT_CONFIG
    run_id_value = snap.timestamp_iso if (snap and snap.timestamp_iso) else "no-snapshot"

    kpis = state.kpis
    profile_known = (kpis.n_elements or 0.0) > 0.0
    profile_src = USER_INPUT if profile_known else DEFAULT_CONFIG

    calib_field, feed_field, multi_feeders = _feeder_fields(session, state)

    out_status = _outputs_status()
    calculated_outputs: dict[str, Field] = {
        "fill_factor": Field(
            value=round(float(kpis.fill_factor) * 100.0, 2), unit="%",
            source=CALCULATED, validation_status=out_status,
            comment="FF = Q_vol / capacité (Network 7).",
        ),
        "residence_time": Field(
            value=round(float(kpis.residence_time_s), 2), unit="s",
            source=CALCULATED, validation_status=out_status,
            comment="Σ V_libre / VolFlow (Network 7).",
        ),
        "free_volume": Field(
            value=round(float(kpis.free_volume_cm3), 2), unit="cm³",
            source=CALCULATED, validation_status=out_status,
            comment="Volume libre utile 2 vis (correction manager).",
        ),
        "sme": Field(
            value=round(float(kpis.sme_kwh_per_kg), 4), unit="kWh/kg",
            source=CALCULATED, validation_status=CALCULATED_WITH_ASSUMPTIONS,
            comment="Estimation V1 (proxy), non calibrée.",
        ),
        "n_elements": Field(
            value=round(float(kpis.n_elements), 1), unit="",
            source=CALCULATED, validation_status=NOT_APPLICABLE,
            comment="Nombre d'éléments placés (tip exclu).",
        ),
    }

    _rpm = float(state.screw_rpm)
    _dens = float(state.feeders[0].density_g_per_cm3) if state.feeders else 0.0
    _ndie = int(state.n_die_zones)
    _target = safe_int(_get(session, _TARGET_COUNT_KEY, _DEFAULT_TARGET_COUNT),
                       _DEFAULT_TARGET_COUNT, 1, 200)
    _sf_en = bool(state.feeders[1].enabled) if len(state.feeders) > 1 else False
    # Zone side feeder (entier 0=désactivé, 1..8) dérivée de la position feeder #2.
    _sf_zone = 0
    if _sf_en and len(state.feeders) > 1:
        _pos = str(getattr(state.feeders[1], "position", "") or "")
        if _pos.startswith("Z") and _pos[1:].isdigit():
            _sf_zone = int(_pos[1:])

    process_parameters: dict[str, Field] = {
        "screw_rpm": Field(_rpm, "tr/min",
                           _param_provenance(_rpm, _DEFAULT_SCREW_RPM), NOT_APPLICABLE),
        "bulk_density": Field(_dens, "g/cm³",
                              _param_provenance(_dens, _DEFAULT_BULK_DENSITY), NOT_APPLICABLE),
        "n_die_zones": Field(_ndie, "",
                             _param_provenance(_ndie, _DEFAULT_N_DIE), NOT_APPLICABLE),
        "target_element_count": Field(_target, "",
                                      _param_provenance(_target, _DEFAULT_TARGET_COUNT), NOT_APPLICABLE),
        "side_feeder_enabled": Field(_sf_en, "",
                                     USER_INPUT if _sf_en else DEFAULT_CONFIG, NOT_APPLICABLE),
        "side_feeder_zone": Field(_sf_zone, "",
                                  USER_INPUT if _sf_zone > 0 else DEFAULT_CONFIG, NOT_APPLICABLE),
    }

    demo_flags = {"demo_mode": bool(_get(session, _DEMO_MODE_KEY, False))}

    # Source DOMINANTE : USER_INPUT dès qu'un signal opérateur réel existe
    # (snapshot validé, profil construit, étalonnage, ou un paramètre ≠ défaut).
    _user_signal = (
        snap is not None or profile_known or calib_field.source == USER_INPUT
        or any(f.source == USER_INPUT for f in process_parameters.values())
    )
    source_type = USER_INPUT if _user_signal else DEFAULT_CONFIG

    return CurrentRunState(
        run_id=Field(run_id_value, "", run_id_src, NOT_APPLICABLE),
        source_type=source_type,
        screw_profile=Field(
            list(state.screw_config), "", profile_src, NOT_APPLICABLE,
            "Profil de vis (81 positions).",
        ),
        feeder_calibration=calib_field,
        feed_rate=feed_field,
        material_context=_material_field(state),
        process_parameters=process_parameters,
        calculated_outputs=calculated_outputs,
        assumptions=_assumptions(),
        validation_status=out_status,
        demo_flags=demo_flags,
        feeders=multi_feeders,
    )


# ---------------------------------------------------------------------------
# Accès / prédicats (API publique P3.1)
# ---------------------------------------------------------------------------
def get_field(crs: CurrentRunState, name: str) -> Field | None:
    """Récupère un `Field` par nom (top-level, process_parameters, outputs)."""
    top = getattr(crs, name, None)
    if isinstance(top, Field):
        return top
    if name in crs.process_parameters:
        return crs.process_parameters[name]
    if name in crs.calculated_outputs:
        return crs.calculated_outputs[name]
    return None


def is_demo_state(crs: CurrentRunState) -> bool:
    """True si le mode démonstration est actif (flag config, pas dataset ML)."""
    return bool(crs.demo_flags.get("demo_mode", False))


def has_material(crs: CurrentRunState) -> bool:
    """True si une matière (polymère) a été réellement saisie."""
    return crs.material_context.source == USER_INPUT


def has_feeder_calibration(crs: CurrentRunState) -> bool:
    """True si l'étalonnage feeder est exploitable."""
    return crs.feeder_calibration.source == USER_INPUT


def calculated_values_have_provenance(crs: CurrentRunState) -> bool:
    """True si toutes les sorties calculées portent source + unité + statut."""
    for f in crs.calculated_outputs.values():
        if f.source not in SOURCE_TYPES or not f.validation_status:
            return False
        # une sortie calculée doit être marquée CALCULATED (ou dérivés)
        if f.source != CALCULATED:
            return False
    return True
