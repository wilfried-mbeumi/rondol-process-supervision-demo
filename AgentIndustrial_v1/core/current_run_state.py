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

from .applied_state import get_applied
from .coercion import safe_float
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


def _feeder_fields(session: Mapping[str, Any]) -> tuple[Field, Field]:
    """(feeder_calibration, feed_rate) — délègue au socle pur feeder_flow."""
    rpm = safe_float(_get(session, _FEEDER_RPM_KEY, 30.0), 30.0, 0.0, 100000.0)
    calib_raw = safe_float(_get(session, _FEEDER_CALIB_KEY, 0.0), 0.0, 0.0, 100000.0)
    ff: FeederFlow = resolve_feeder_flow(rpm, calib_raw if calib_raw > 0.0 else None)

    if not ff.calibrated:
        calib_field = Field(
            value=None, unit="g/h/RPM", source=NOT_AVAILABLE,
            validation_status=NOT_VALIDATED,
            comment="Coefficient d'étalonnage feeder non renseigné.",
        )
        feed_field = Field(
            value=None, unit="g/h", source=NOT_AVAILABLE,
            validation_status=NOT_VALIDATED,
            comment="Débit réel non calculable sans étalonnage.",
        )
        return calib_field, feed_field

    calib_field = Field(
        value=ff, unit="g/h/RPM", source=USER_INPUT,
        validation_status=NOT_APPLICABLE,
        comment="Étalonnage externe (RPM × coefficient).",
    )
    feed_comment = (
        "Débit effectif plafonné au max machine." if ff.clamped
        else "Débit effectif (RPM × coefficient)."
    )
    feed_field = Field(
        value=ff.effective_g_h, unit="g/h", source=CALCULATED,
        validation_status=CALCULATED_WITH_ASSUMPTIONS,
        comment=feed_comment + " Dépend du coefficient d'étalonnage externe.",
    )
    return calib_field, feed_field


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
    src = USER_INPUT if snap is not None else DEFAULT_CONFIG
    run_id_value = snap.timestamp_iso if (snap and snap.timestamp_iso) else "no-snapshot"

    kpis = state.kpis
    profile_known = (kpis.n_elements or 0.0) > 0.0
    profile_src = USER_INPUT if (snap is not None or profile_known) else DEFAULT_CONFIG

    calib_field, feed_field = _feeder_fields(session)

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

    process_parameters: dict[str, Field] = {
        "screw_rpm": Field(float(state.screw_rpm), "tr/min", src, NOT_APPLICABLE),
        "bulk_density": Field(
            float(state.feeders[0].density_g_per_cm3) if state.feeders else 0.0,
            "g/cm³", src, NOT_APPLICABLE),
        "n_die_zones": Field(int(state.n_die_zones), "", src, NOT_APPLICABLE),
        "side_feeder_enabled": Field(
            bool(state.feeders[1].enabled) if len(state.feeders) > 1 else False,
            "", src, NOT_APPLICABLE),
    }

    demo_flags = {"demo_mode": bool(_get(session, _DEMO_MODE_KEY, False))}

    return CurrentRunState(
        run_id=Field(run_id_value, "", src, NOT_APPLICABLE),
        source_type=src,
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
