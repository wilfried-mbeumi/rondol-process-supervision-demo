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
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from .calib_keys import collect_calibrations, seed_calibrations
from .coercion import safe_float, safe_int
from .feeders import FeederSpec, new_feeder_bank
from .process import DEFAULT_ZONE_TARGETS_C, ProcessState, default_zone_target


# Clé session_state pour le snapshot validé.
APPLIED_KEY = "applied_state"
# Clé session_state pour l'historique chronologique des snapshots.
HISTORY_KEY = "applied_history"
# Plafond historique pour éviter la croissance illimitée en session longue.
HISTORY_MAX = 30

# ---------------------------------------------------------------------------
# Miroir DISQUE du snapshot validé (stabilisation globale 2026-06-10).
#
# Cause racine prod : le snapshot validé (« Enregistrer ») ne vivait QUE dans
# st.session_state. Tout refresh navigateur / nouvel onglet / redéploiement
# Streamlit Cloud = session neuve → la sauvegarde disparaissait : Supervision
# repassait en « profil vide / analyse indicative », l'Agent IA retombait sur
# les défauts, Settings re-seedait ses widgets sans snapshot — alors que
# l'Historique (déjà sur disque) gardait, lui, la trace du commit.
#
# Le miroir est un état VOLATILE LOCAL (data/run_state/, .gitignoré — même
# famille que operator_store) : il n'écrase JAMAIS une session vivante
# (restauration setdefault-only) et n'est PAS une source de vérité concurrente,
# seulement la survie du dernier commit opérateur.
# ---------------------------------------------------------------------------
_ENV_APPLIED_PATH = "RONDOL_APPLIED_STATE_PATH"
_DEFAULT_APPLIED_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "run_state" / "applied_state.json"
)


def _applied_disk_path() -> Path:
    raw = os.environ.get(_ENV_APPLIED_PATH)
    return Path(raw) if raw else _DEFAULT_APPLIED_PATH


def snapshot_to_dict(snap: AppliedSnapshot) -> dict[str, Any]:
    """Sérialisation JSON-safe du snapshot (dataclass → dict)."""
    return asdict(snap)


def snapshot_from_dict(d: Mapping[str, Any]) -> AppliedSnapshot:
    """Désérialisation défensive d'un snapshot (champs inconnus ignorés,
    champs manquants → défauts du dataclass). Ne lève jamais sur un dict sain."""
    return AppliedSnapshot(
        timestamp_iso=str(d.get("timestamp_iso", "") or ""),
        label=str(d.get("label", "") or ""),
        screw_config=[int(v) for v in (d.get("screw_config") or [])],
        screw_rpm=safe_float(d.get("screw_rpm", 120.0), 120.0, 1.0, 3000.0),
        zone_temps_C={
            str(k): safe_float(v, default_zone_target(str(k)), 0.0, 400.0)
            for k, v in dict(d.get("zone_temps_C") or {}).items()
        },
        n_die_zones=safe_int(d.get("n_die_zones", 1), 1, 0, 4),
        feeders=[dict(f) for f in (d.get("feeders") or []) if isinstance(f, Mapping)],
        torque_pct=d.get("torque_pct"),
        pressure_die_bar=d.get("pressure_die_bar"),
        feeder_calibrations={
            str(k): dict(v)
            for k, v in dict(d.get("feeder_calibrations") or {}).items()
            if isinstance(v, Mapping)
        },
    )


def _persistence_module():
    """Couche de persistance DURABLE `app/persistence.py` (import paresseux).

    P0 manager 2026-06-12 : le JSON local est ÉPHÉMÈRE sur Streamlit Cloud
    (reboot/redeploy = perte). app/persistence.py route vers un backend durable
    (Supabase via secrets, ou store externe via env) avec le JSON local en
    fallback dev. Import paresseux + best-effort : si le module app n'est pas
    sur sys.path (tests core isolés), on retombe sur le miroir local historique.
    """
    try:
        import persistence  # type: ignore  # app/ est bootstrapé dans sys.path
        return persistence
    except Exception:  # pragma: no cover - environnement core isolé
        return None


def _disk_save_applied(snap: AppliedSnapshot) -> None:
    """Sauvegarde best-effort du snapshot validé (ne lève jamais).

    Délègue à la couche durable `app/persistence.py` (Supabase / store externe
    / JSON local). Fallback : écriture JSON locale historique.
    """
    pm = _persistence_module()
    if pm is not None:
        try:
            pm.save_applied_state(snapshot_to_dict(snap))
            return
        except Exception:  # pragma: no cover
            pass
    try:
        p = _applied_disk_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(snapshot_to_dict(snap), ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:  # pragma: no cover - persistance best-effort
        pass


def _disk_load_applied() -> AppliedSnapshot | None:
    """Charge le dernier snapshot validé depuis la persistance (None si absent
    ou illisible — jamais d'exception). Backend durable d'abord, JSON local
    en fallback (via app/persistence.py)."""
    pm = _persistence_module()
    if pm is not None:
        try:
            data = pm.load_applied_state()
            if isinstance(data, dict) and data.get("screw_config") is not None:
                return snapshot_from_dict(data)
            return None
        except Exception:  # pragma: no cover
            pass
    try:
        p = _applied_disk_path()
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("screw_config") is not None:
            return snapshot_from_dict(data)
    except Exception:  # pragma: no cover
        return None
    return None


def restore_applied(session: MutableMapping[str, Any]) -> AppliedSnapshot | None:
    """Restaure le snapshot validé depuis le miroir disque si la session n'en a
    PAS (session neuve / refresh navigateur).

    Règle stricte : setdefault-only — ne remplace JAMAIS un snapshot déjà
    présent en session (un commit vivant prime toujours sur le disque).
    Retourne le snapshot effectif (session ou restauré), None si aucun.
    """
    existing = _safe_get(session, APPLIED_KEY)
    if isinstance(existing, AppliedSnapshot):
        return existing
    snap = _disk_load_applied()
    if snap is None:
        return None
    try:
        session[APPLIED_KEY] = snap
        # L'historique session repart du snapshot restauré (l'historique
        # complet persistant vit dans history_store, sur disque).
        if HISTORY_KEY not in session or not _safe_get(session, HISTORY_KEY):
            session[HISTORY_KEY] = [snap]
    except Exception:  # pragma: no cover - proxy session hors contexte
        return snap
    return snap


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
    # Étalonnage feeders (RPM × coeff g/h/RPM par feeder) — cause racine prod
    # 2026-06-12 : sans lui dans le snapshot, le débit réel ne survivait au
    # refresh que via le store opérateur (2e source de vérité divergente).
    feeder_calibrations: dict[str, dict[str, float]] = field(default_factory=dict)


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
    # Auto-heal d'un snapshot DÉGÉNÉRÉ (cause racine prod 2026-06-14) : un ancien
    # build dont le widget densité valait 0 (pas de `value=`) sauvegardait une
    # densité bulk ~0. Au rechargement, safe_float la clampe à 0.0001 → affichée
    # « 0.000 » et le snapshot blanc se perpétuait à chaque refresh. Une densité
    # bulk quasi nulle est NON PHYSIQUE → on rétablit le défaut 0.55 (jamais une
    # valeur procédé réelle). Idem implicite : feeders manquants padés en aval.
    _dens = safe_float(d.get("density_g_per_cm3", 0.55), 0.55, 0.0001, 10.0)
    if _dens < 0.01:
        _dens = 0.55
    return FeederSpec(
        feeder_id=safe_int(d.get("feeder_id", 1), 1, 1, 5),
        enabled=bool(d.get("enabled", False)),
        label=str(d.get("label", "")),
        material_id=str(d.get("material_id", "granules")),
        position=str(d.get("position", "Z0")),
        speed_rpm=d.get("speed_rpm"),
        mass_flow_g_per_min=safe_float(d.get("mass_flow_g_per_min", 0.0), 0.0, 0.0, 2000.0),
        density_g_per_cm3=_dens,
        thermal_expansion_per_K=safe_float(d.get("thermal_expansion_per_K", 5e-5), 5e-5, 0.0, 1.0),
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
    """Reconstruit un ProcessState depuis un snapshot (deep copy garanti).

    ROBUSTESSE (cause racine prod 2026-06-14) : le banc feeders est TOUJOURS
    complet (5 feeders), même si le snapshot n'en stocke qu'un sous-ensemble
    (ancien build / sauvegarde partielle). Sans ce padding, Settings plantait
    (`KeyError fd_en_2`) dès qu'un snapshot avait < 5 feeders → page blanche,
    état « incohérent ». Les feeders du snapshot écrasent les défauts du banc.
    """
    bank = new_feeder_bank()
    if snapshot.feeders:
        for i, d in enumerate(snapshot.feeders):
            if 0 <= i < len(bank):
                bank[i] = _feeder_from_dict(d)
    feeders = bank
    state = ProcessState(
        screw_config=copy.deepcopy(snapshot.screw_config),
        screw_rpm=safe_float(snapshot.screw_rpm, 120.0, 1.0, 3000.0),
        feeders=feeders,
    )
    if snapshot.zone_temps_C:
        for k, v in snapshot.zone_temps_C.items():
            _tv = safe_float(v, default_zone_target(k), 0.0, 400.0)
            # Auto-heal : une consigne de zone à 0 °C est non-physique pour un
            # fourreau chauffé (snapshot dégénéré d'un ancien build) → cible
            # par défaut, jamais « 0.00 » affiché comme une vérité procédé.
            state.zone_temps_C[k] = _tv if _tv > 0.0 else default_zone_target(k)
    # Compléter les zones manquantes (rétro-compat avec anciens snapshots).
    for zk in DEFAULT_ZONE_TARGETS_C:
        state.zone_temps_C.setdefault(zk, default_zone_target(zk))
    state.n_die_zones = safe_int(snapshot.n_die_zones, 1, 0, 4)
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
    # L'étalonnage feeder fait partie de la configuration validée : il est
    # sérialisé DANS le snapshot (source de vérité unique après refresh).
    snap.feeder_calibrations = collect_calibrations(session)
    session[APPLIED_KEY] = snap
    history = list(_safe_get(session, HISTORY_KEY, []) or [])
    history.append(snap)
    if len(history) > HISTORY_MAX:
        history = history[-HISTORY_MAX:]
    session[HISTORY_KEY] = history
    # Miroir disque : la sauvegarde validée survit au refresh navigateur /
    # nouvelle session (stabilisation globale 2026-06-10). Best-effort.
    _disk_save_applied(snap)
    return snap


def get_applied(session: Mapping[str, Any]) -> AppliedSnapshot | None:
    """Retourne le snapshot validé courant — None si rien n'a encore été commité.

    Session neuve (refresh navigateur / redéploiement) : tente d'abord la
    restauration depuis le miroir disque (setdefault-only via restore_applied)
    pour que TOUS les consommateurs (Supervision, Agent IA, seed Settings)
    revoient la dernière sauvegarde opérateur sans action manuelle.
    """
    snap = _safe_get(session, APPLIED_KEY)
    if isinstance(snap, AppliedSnapshot):
        return snap
    # Session neuve : restauration disque. restore_applied est défensif (toute
    # écriture session est protégée) — fonctionne aussi sur un proxy Streamlit
    # qui n'est pas formellement un MutableMapping.
    return restore_applied(session)  # type: ignore[arg-type]


def hydrate_session_from_applied(
    session: MutableMapping[str, Any],
) -> AppliedSnapshot | None:
    """Hydrate la session depuis le snapshot validé — chokepoint UNIQUE des pages.

    À appeler en TÊTE de chaque page, AVANT `restore_operator_state` : le
    snapshot validé (source de vérité officielle, miroir applied_state.json)
    prime sur le store opérateur. Sème (setdefault-only) :
      - `screw_config` : le profil vis sauvegardé ;
      - les clés d'étalonnage feeder (RPM / coeff, + miroirs persistants).

    Ne touche JAMAIS une clé déjà présente (édition vivante en session). Sans
    snapshot, ne fait rien (les défauts restent du ressort de chaque page).
    """
    snap = get_applied(session)
    if snap is None:
        return None
    try:
        if snap.screw_config and "screw_config" not in session:
            session["screw_config"] = list(snap.screw_config)
    except Exception:  # pragma: no cover - proxy hors contexte
        pass
    seed_calibrations(session, snap.feeder_calibrations)
    return snap


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
    # L'étalonnage courant vient de la session (même source que commit).
    current.feeder_calibrations = collect_calibrations(session)
    # On compare uniquement les champs métier (timestamp/label ignorés).
    a = {k: v for k, v in asdict(applied).items() if k not in ("timestamp_iso", "label")}
    b = {k: v for k, v in asdict(current).items() if k not in ("timestamp_iso", "label")}
    return a != b
