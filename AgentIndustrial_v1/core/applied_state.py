"""
applied_state.py — Persistance Settings → Supervision (3 couches).

Architecture demandée par Maël Gallas (2026-05-20) — dissocier explicitement :

  1. **Paramètres en cours de modification** (`editing`)
     Les widgets Streamlit lient leurs valeurs aux clés de session
     habituelles (`th_Z1`, `feeder_g_per_min`, `agent_state`, …). Tant que
     l'opérateur édite, Settings affiche ces valeurs vivantes. Aucune autre
     page n'en dépend.

  2. **Données enregistrées** (`applied`)
     Snapshot validé par l'opérateur (bouton « Enregistrer »). C'est la
     source unique consommée par Supervision et par l'agent IA pour le
     raisonnement. Modifier les widgets de Settings ne modifie pas ce
     snapshot tant que l'opérateur ne clique pas « Enregistrer ».

  3. **Historique** (`history`)
     Liste chronologique des snapshots validés. Permet aux pages d'analyse
     run de retrouver la configuration qui était en service à un instant
     donné, sans dépendre du widget courant.

Ce module est PUR : aucune dépendance Streamlit (testable en CLI). Il
travaille sur un `Mapping` (lecture) et un `MutableMapping` (écriture) qui
sera en pratique `st.session_state`.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping, MutableMapping

from .feeders import FeederSpec, new_feeder_bank
from .process import DEFAULT_ZONE_TARGETS_C, ProcessState, default_zone_target


# Clé session_state pour le snapshot validé.
APPLIED_KEY = "applied_state"
# Clé session_state pour l'historique chronologique des snapshots.
HISTORY_KEY = "applied_history"
# Plafond historique pour éviter la croissance illimitée en session longue.
HISTORY_MAX = 30


@dataclass
class AppliedSnapshot:
    """Snapshot d'une configuration procédé validée par l'opérateur.

    Contient un *deep copy* — les modifications ultérieures des widgets
    Settings ne peuvent pas le muter.
    """
    timestamp_iso: str = ""
    label: str = ""  # libellé libre opérateur ("Test #3 LFP", …)
    # Procédé
    screw_config: list[int] = field(default_factory=list)
    screw_rpm: float = 120.0
    zone_temps_C: dict[str, float] = field(default_factory=dict)
    n_die_zones: int = 1
    # Feeders (5 max — état complet sérialisé)
    feeders: list[dict[str, Any]] = field(default_factory=list)
    # V2 (placeholders)
    torque_pct: float | None = None
    pressure_die_bar: float | None = None


def _feeder_to_dict(f: FeederSpec) -> dict[str, Any]:
    return {
        "feeder_id": f.feeder_id,
        "enabled": bool(f.enabled),
        "label": f.label,
        "material_id": f.material_id,
        "position": f.position,
        "speed_rpm": f.speed_rpm,
        "mass_flow_g_per_min": float(f.mass_flow_g_per_min),
        "density_g_per_cm3": float(f.density_g_per_cm3),
        "thermal_expansion_per_K": float(f.thermal_expansion_per_K),
        "polymer_name": f.polymer_name,
        "t_degradation_C": f.t_degradation_C,
        "tga_onset_C": f.tga_onset_C,
        "viscosity_pa_s": f.viscosity_pa_s,
        "t_melt_C": f.t_melt_C,
        "t_glass_C": f.t_glass_C,
    }


def _feeder_from_dict(d: Mapping[str, Any]) -> FeederSpec:
    return FeederSpec(
        feeder_id=int(d["feeder_id"]),
        enabled=bool(d.get("enabled", False)),
        label=str(d.get("label", "")),
        material_id=str(d.get("material_id", "granules")),
        position=str(d.get("position", "Z0")),
        speed_rpm=d.get("speed_rpm"),
        mass_flow_g_per_min=float(d.get("mass_flow_g_per_min", 0.0)),
        density_g_per_cm3=float(d.get("density_g_per_cm3", 0.55)),
        thermal_expansion_per_K=float(d.get("thermal_expansion_per_K", 5e-5)),
        polymer_name=str(d.get("polymer_name", "")),
        t_degradation_C=d.get("t_degradation_C"),
        tga_onset_C=d.get("tga_onset_C"),
        viscosity_pa_s=d.get("viscosity_pa_s"),
        t_melt_C=d.get("t_melt_C"),
        t_glass_C=d.get("t_glass_C"),
    )


def take_snapshot(state: ProcessState, label: str = "") -> AppliedSnapshot:
    """Sérialise l'état courant en snapshot (deep copy)."""
    return AppliedSnapshot(
        timestamp_iso=datetime.now().isoformat(timespec="seconds"),
        label=label,
        screw_config=copy.deepcopy(state.screw_config),
        screw_rpm=float(state.screw_rpm),
        zone_temps_C=dict(state.zone_temps_C),
        n_die_zones=int(state.n_die_zones),
        feeders=[_feeder_to_dict(f) for f in state.feeders],
        torque_pct=state.v2.torque_pct,
        pressure_die_bar=state.v2.pressure_die_bar,
    )


def hydrate_state(snapshot: AppliedSnapshot) -> ProcessState:
    """Reconstruit un ProcessState depuis un snapshot (deep copy garanti)."""
    feeders = (
        [_feeder_from_dict(d) for d in snapshot.feeders]
        if snapshot.feeders else new_feeder_bank()
    )
    state = ProcessState(
        screw_config=copy.deepcopy(snapshot.screw_config),
        screw_rpm=float(snapshot.screw_rpm),
        feeders=feeders,
    )
    if snapshot.zone_temps_C:
        for k, v in snapshot.zone_temps_C.items():
            state.zone_temps_C[k] = float(v)
    # Compléter les zones manquantes (rétro-compat avec anciens snapshots).
    for zk in DEFAULT_ZONE_TARGETS_C:
        state.zone_temps_C.setdefault(zk, default_zone_target(zk))
    state.n_die_zones = int(snapshot.n_die_zones)
    state.v2.torque_pct = snapshot.torque_pct
    state.v2.pressure_die_bar = snapshot.pressure_die_bar
    return state


def _safe_get(session: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Lecture défensive : Streamlit SafeSessionStateProxy n'expose pas `.get()`.

    On utilise `in` (qui marche sur le proxy) + indexation.
    """
    try:
        if key in session:
            return session[key]
    except Exception:
        pass
    return default


def commit(
    session: MutableMapping[str, Any], state: ProcessState, label: str = "",
) -> AppliedSnapshot:
    """Valide l'état édité comme nouveau snapshot.

    Effets :
      - écrit `session[APPLIED_KEY] = snapshot`
      - ajoute le snapshot en fin de `session[HISTORY_KEY]` (plafonné à
        HISTORY_MAX entrées, FIFO).
    """
    snap = take_snapshot(state, label=label)
    session[APPLIED_KEY] = snap
    history = list(_safe_get(session, HISTORY_KEY, []) or [])
    history.append(snap)
    if len(history) > HISTORY_MAX:
        history = history[-HISTORY_MAX:]
    session[HISTORY_KEY] = history
    return snap


def get_applied(session: Mapping[str, Any]) -> AppliedSnapshot | None:
    """Retourne le snapshot validé courant — None si rien n'a encore été commité."""
    snap = _safe_get(session, APPLIED_KEY)
    if isinstance(snap, AppliedSnapshot):
        return snap
    return None


def get_history(session: Mapping[str, Any]) -> list[AppliedSnapshot]:
    """Retourne la liste chronologique des snapshots validés."""
    hist = _safe_get(session, HISTORY_KEY, []) or []
    return [s for s in hist if isinstance(s, AppliedSnapshot)]


def has_unsaved_changes(
    session: Mapping[str, Any], editing_state: ProcessState,
) -> bool:
    """True si l'état édité diverge du snapshot validé (UI hint)."""
    applied = get_applied(session)
    if applied is None:
        return True
    current = take_snapshot(editing_state)
    # On compare uniquement les champs métier (timestamp/label ignorés).
    a = {k: v for k, v in asdict(applied).items() if k not in ("timestamp_iso", "label")}
    b = {k: v for k, v in asdict(current).items() if k not in ("timestamp_iso", "label")}
    return a != b
