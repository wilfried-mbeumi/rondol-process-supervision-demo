"""
editing_state.py — Couche d'édition Settings (propriété unique = clés widget).

Reconception 2026-05-21 (refonte du flow de state, exigence stabilité prod).

Modèle de propriété de la donnée
---------------------------------
La page Settings n'a plus qu'UNE source de vérité tant que l'opérateur édite :
les **clés widget** de `st.session_state` (`th_Z1`..`th_die4`, `n_die_zones`,
`fd_en_1`..`fd_tglass_5`, `ni_rpm_hmi`, `ni_tq_v2`, `ni_pr_v2`). Streamlit
garantit que `session_state[key]` contient la valeur courante du widget DÈS le
début du rerun (pattern « key-only », sans `value=`). On peut donc reconstruire
l'état procédé n'importe où dans le script — l'ordre du layout n'a aucune
incidence sur l'exactitude.

Trois fonctions, aucun objet d'état mutable conservé en session :

  1. `seed_editing_keys(session)` — hydrate les clés widget UNE fois en tête de
     script, de façon idempotente. Priorité déterministe :
        a. clé déjà présente  → édition en cours / non purgée → on n'y touche pas
        b. snapshot validé    → on sème depuis `applied_state` (dernière config)
        c. ni l'un ni l'autre → défauts métier / pont legacy (Profile/Home)
     Règle d'un coup le 1er boot ET la purge de navigation Streamlit (les clés
     widget d'une page non montée sont effacées → au retour elles repartent du
     snapshot, pas du défaut usine).

  2. `build_state_from_widgets(session) -> ProcessState` — lecteur PUR. Reconstruit
     un `ProcessState` à partir des clés widget. Ne mute rien. Sert l'aperçu IA,
     le diff « modifications non enregistrées » et le commit.

  3. (commit) — `applied_state.commit(session, build_state_from_widgets(session))`.
     Comme le commit lit les clés widget (déjà à jour dans le même rerun), il est
     totalement indépendant de l'emplacement du bouton dans le script.

Module PUR : aucune dépendance Streamlit (testable en CLI sur un dict).
"""

from __future__ import annotations

from typing import Any, MutableMapping

from .applied_state import _safe_get
from .coercion import safe_float, safe_int
from .feeders import new_feeder_bank
from .process import ProcessState, default_zone_target
from .screw_adapter import refresh_kpis
from .state_sync import state_from_session

# ---------------------------------------------------------------------------
# Inventaire des clés widget possédées par la couche d'édition Settings.
# ---------------------------------------------------------------------------
ZONE_KEYS: tuple[str, ...] = (
    "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
    "die", "die2", "die3", "die4",
)
# Identifiants feeders (1..5) — alignés sur new_feeder_bank().
FEEDER_IDS: tuple[int, ...] = tuple(f.feeder_id for f in new_feeder_bank())

RPM_KEY = "ni_rpm_hmi"
TORQUE_KEY = "ni_tq_v2"
PRESSURE_KEY = "ni_pr_v2"
N_DIE_KEY = "n_die_zones"
SCREW_CONFIG_KEY = "screw_config"


def _setdefault(session: MutableMapping[str, Any], key: str, value: Any) -> None:
    """setdefault défensif (le proxy Streamlit ne garantit pas .setdefault)."""
    if key not in session:
        session[key] = value


def _opt(value: Any) -> float:
    """Champ optionnel (T° dégradation, viscosité…) → 0.0 si absent côté widget.

    Convention HMI : 0.0 dans le widget = « non renseigné » = None côté moteur.
    """
    return float(value) if value is not None else 0.0


# ---------------------------------------------------------------------------
# 1. Hydratation idempotente des clés widget
# ---------------------------------------------------------------------------
def seed_editing_keys(session: MutableMapping[str, Any]) -> ProcessState:
    """Sème les clés widget manquantes depuis la meilleure source disponible.

    Source = `state_from_session` : snapshot validé prioritaire, sinon pont
    legacy (clés partagées Profile/Home) / défauts métier. Idempotent : ne
    réécrit jamais une clé déjà présente (édition en cours préservée).

    Retourne l'état-graine (utile pour debug/tests) — la page n'a pas besoin
    de le conserver, elle relira tout via `build_state_from_widgets`.
    """
    seed = state_from_session(session)

    for zk in ZONE_KEYS:
        _setdefault(session, f"th_{zk}", float(seed.zone_temps_C.get(zk, default_zone_target(zk))))
    _setdefault(session, N_DIE_KEY, int(seed.n_die_zones))
    _setdefault(session, RPM_KEY, float(seed.screw_rpm))
    _setdefault(session, TORQUE_KEY, _opt(seed.v2.torque_pct))
    _setdefault(session, PRESSURE_KEY, _opt(seed.v2.pressure_die_bar))
    _setdefault(session, SCREW_CONFIG_KEY, list(seed.screw_config))

    for f in seed.feeders:
        fid = f.feeder_id
        _setdefault(session, f"fd_en_{fid}", bool(f.enabled))
        _setdefault(session, f"fd_lbl_{fid}", str(f.label))
        _setdefault(session, f"fd_mat_{fid}", str(f.material_id))
        _setdefault(session, f"fd_dens_{fid}", float(f.density_g_per_cm3))
        _setdefault(session, f"fd_alpha_{fid}", float(f.thermal_expansion_per_K))
        _setdefault(session, f"fd_pos_{fid}", str(f.position))
        _setdefault(session, f"fd_flow_{fid}", float(f.mass_flow_g_per_min))
        _setdefault(session, f"fd_poly_{fid}", str(f.polymer_name))
        _setdefault(session, f"fd_tdeg_{fid}", _opt(f.t_degradation_C))
        _setdefault(session, f"fd_tga_{fid}", _opt(f.tga_onset_C))
        _setdefault(session, f"fd_visc_{fid}", _opt(f.viscosity_pa_s))
        _setdefault(session, f"fd_tmelt_{fid}", _opt(f.t_melt_C))
        _setdefault(session, f"fd_tglass_{fid}", _opt(f.t_glass_C))

    return seed


# ---------------------------------------------------------------------------
# 2. Reconstruction pure de l'état depuis les clés widget
# ---------------------------------------------------------------------------
def build_state_from_widgets(session: MutableMapping[str, Any]) -> ProcessState:
    """Reconstruit le ProcessState édité courant — lecteur PUR, ne mute rien.

    À appeler après `seed_editing_keys`. Reflète exactement ce que l'opérateur
    voit/édite à l'écran dans ce rerun, quel que soit l'emplacement de l'appel.
    """
    feeders = new_feeder_bank()
    for f in feeders:
        fid = f.feeder_id
        if f"fd_en_{fid}" in session:
            f.enabled = bool(session[f"fd_en_{fid}"])
        if f"fd_lbl_{fid}" in session:
            f.label = str(session[f"fd_lbl_{fid}"])
        if f"fd_mat_{fid}" in session:
            f.material_id = str(session[f"fd_mat_{fid}"])
        if f"fd_dens_{fid}" in session:
            f.density_g_per_cm3 = safe_float(
                session[f"fd_dens_{fid}"], f.density_g_per_cm3, 0.0001, 10.0
            )
        if f"fd_alpha_{fid}" in session:
            f.thermal_expansion_per_K = safe_float(
                session[f"fd_alpha_{fid}"], f.thermal_expansion_per_K, 0.0, 1.0
            )
        if f"fd_pos_{fid}" in session:
            f.position = str(session[f"fd_pos_{fid}"])
        if f"fd_flow_{fid}" in session:
            f.mass_flow_g_per_min = safe_float(
                session[f"fd_flow_{fid}"], f.mass_flow_g_per_min, 0.0, 2000.0
            )
        if f"fd_poly_{fid}" in session:
            f.polymer_name = str(session[f"fd_poly_{fid}"])
        f.t_degradation_C = _none_if_zero(_safe_get(session, f"fd_tdeg_{fid}"))
        f.tga_onset_C = _none_if_zero(_safe_get(session, f"fd_tga_{fid}"))
        f.viscosity_pa_s = _none_if_zero(_safe_get(session, f"fd_visc_{fid}"))
        f.t_melt_C = _none_if_zero(_safe_get(session, f"fd_tmelt_{fid}"))
        # Tg peut être négatif → seul 0.0 vaut « non renseigné ».
        _tg = _safe_get(session, f"fd_tglass_{fid}")
        if _tg is None:
            f.t_glass_C = None
        else:
            _tg_val = safe_float(_tg, 0.0, -200.0, 600.0)
            f.t_glass_C = _tg_val if _tg_val != 0.0 else None

    rpm = _safe_get(session, RPM_KEY, _safe_get(session, "screw_rpm", 120.0))
    screw_config = list(_safe_get(session, SCREW_CONFIG_KEY) or [])

    state = ProcessState(
        screw_config=screw_config,
        screw_rpm=safe_float(rpm, 120.0, 1.0, 3000.0),
        feeders=feeders,
    )
    for zk in ZONE_KEYS:
        state.zone_temps_C[zk] = safe_float(
            _safe_get(session, f"th_{zk}", default_zone_target(zk)),
            default_zone_target(zk), 0.0, 400.0,
        )
    state.n_die_zones = safe_int(
        _safe_get(session, N_DIE_KEY, state.n_die_zones), state.n_die_zones, 0, 4
    )
    state.v2.torque_pct = _none_if_zero(_safe_get(session, TORQUE_KEY))
    state.v2.pressure_die_bar = _none_if_zero(_safe_get(session, PRESSURE_KEY))

    refresh_kpis(state)
    return state


def _none_if_zero(value: Any) -> float | None:
    """Champ optionnel widget : 0.0/absent/non numérique → None, sinon float."""
    if value is None:
        return None
    v = safe_float(value, 0.0)
    return v if v > 0 else None


# ---------------------------------------------------------------------------
# 3. Projection vers les clés legacy partagées (Profile / Home / panneau vis)
# ---------------------------------------------------------------------------
def project_shared_keys(session: MutableMapping[str, Any], state: ProcessState) -> None:
    """Reflète l'état édité dans les clés partagées historiques.

    Ces clés ne sont PAS une source de vérité concurrente : c'est une projection
    en lecture seule pour les consommateurs legacy (Profile, et le panneau de
    recommandation vis de Supervision qui lit encore `screw_rpm`/`feeder_g_per_min`
    /`bulk_density` directement, hors snapshot).
    """
    # 0 = side feeder désactivé (cf. screw_logic.SIDE_FEEDER_DISABLED_ZONE).
    # Valeur littérale ici pour garder le module pur (sans dépendance app/).
    side_off = 0

    if state.feeders:
        session["screw_rpm"] = float(state.screw_rpm)
        session["feeder_g_per_min"] = float(state.feeders[0].mass_flow_g_per_min)
        session["bulk_density"] = float(state.feeders[0].density_g_per_cm3)
    if len(state.feeders) > 1:
        sf = state.feeders[1]
        if sf.enabled and sf.position.startswith("Z"):
            try:
                session["side_feeder_zone"] = int(sf.position[1:])
            except ValueError:
                session["side_feeder_zone"] = side_off
        else:
            session["side_feeder_zone"] = side_off
