"""
state_sync.py — Source unique d'état procédé partagée entre les pages.

Architecture 2026-05-20 (exigence manager) :

  Settings page édite librement des widgets dans `st.session_state`. Quand
  l'opérateur clique « Enregistrer », un *snapshot* validé est créé via
  `applied_state.commit(...)`. Supervision lit UNIQUEMENT depuis ce snapshot.

  → Modifier une valeur dans Settings ne modifie PAS Supervision tant que
    l'opérateur ne valide pas. Les données enregistrées (snapshot + history)
    survivent à toute édition.

Ce module reconstruit donc un `ProcessState` exploitable par l'agent IA
depuis :
  1. Le snapshot validé (`applied_state.get_applied`) → priorité.
  2. À défaut (1er run, aucun snapshot encore), les anciennes clés partagées
     (rétro-compat avec Profile/Home écrits avant la refonte snapshot).

Module PUR côté moteur (ne touche pas à l'UI).
"""

from __future__ import annotations

from typing import Any, Mapping

from .applied_state import APPLIED_KEY, AppliedSnapshot, _safe_get, hydrate_state
from .feeders import new_feeder_bank
from .process import ProcessState, default_zone_target
from .screw_adapter import default_screw_config, refresh_kpis

_ZONE_KEYS = ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
              "die", "die2", "die3", "die4")


def _legacy_state_from_session(session: Mapping[str, Any]) -> ProcessState:
    """Fallback : construit l'état depuis les anciennes clés partagées
    (Profile/Home écrivent encore `screw_rpm`, `feeder_g_per_min`, etc.).

    N'est utilisé que tant qu'aucun snapshot n'a été commité.
    """
    state = ProcessState(
        screw_config=_safe_get(session, "screw_config") or default_screw_config(),
        screw_rpm=float(_safe_get(session, "screw_rpm", 120.0)),
        feeders=new_feeder_bank(),
    )
    # Feeder #1 = main (reflète feeder_g_per_min / bulk_density partagés).
    if state.feeders:
        if "feeder_g_per_min" in session:
            state.feeders[0].mass_flow_g_per_min = float(
                session["feeder_g_per_min"]
            )
        if "bulk_density" in session:
            state.feeders[0].density_g_per_cm3 = float(session["bulk_density"])
    # Feeder #2 = side feeder selon side_feeder_zone partagé.
    if len(state.feeders) > 1 and "side_feeder_zone" in session:
        try:
            sf = int(session["side_feeder_zone"])
        except (TypeError, ValueError):
            sf = 0
        state.feeders[1].enabled = sf > 0
        if sf > 0:
            state.feeders[1].position = f"Z{sf}"

    # Consignes thermiques Z1..Z8 + die (clés th_*), nb zones die.
    for zk in _ZONE_KEYS:
        state.zone_temps_C[zk] = float(
            _safe_get(session, f"th_{zk}", default_zone_target(zk))
        )
    state.n_die_zones = int(_safe_get(session, "n_die_zones", state.n_die_zones))
    return state


def state_from_session(session: Mapping[str, Any]) -> ProcessState:
    """Retourne le ProcessState courant pour les pages consommatrices.

    Priorité au snapshot validé (`applied_state`). À défaut, fallback rétro-compat.
    Les KPIs sont rafraîchis avant retour.
    """
    snap = _safe_get(session, APPLIED_KEY)
    if isinstance(snap, AppliedSnapshot):
        state = hydrate_state(snap)
    else:
        state = _legacy_state_from_session(session)
    refresh_kpis(state)
    return state
