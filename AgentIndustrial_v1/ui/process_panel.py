"""
process_panel.py — Profil thermique, vitesse vis, KPIs hérités.

Reprend les variables déjà gérées dans l'existant Kévin :
  - températures Z1..Z8 + die
  - vitesse vis (rpm)
  - KPIs : FF, RT, free volume, SME (estimé V1)
"""

from __future__ import annotations

import streamlit as st

from ..core.process import DEFAULT_ZONE_TARGETS_C, ProcessState
from .styles import BORDER, CARD, SUB


_ZONE_ORDER = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8", "die"]


def render_temperature(state: ProcessState) -> dict[str, float]:
    """Rend les inputs de température zone par zone. Retourne le dict mis à jour."""
    st.markdown("##### Profil thermique zones")
    st.caption(
        "Consignes T° par zone — affichage compact horizontal. "
        "Les bornes par défaut suivent la pratique compounding bivis SSB."
    )
    cols = st.columns(len(_ZONE_ORDER))
    new_temps: dict[str, float] = {}
    for c, zone in zip(cols, _ZONE_ORDER):
        with c:
            new_temps[zone] = st.number_input(
                zone,
                min_value=0.0, max_value=400.0,
                value=float(state.zone_temps_C.get(zone, DEFAULT_ZONE_TARGETS_C[zone])),
                step=5.0,
                key=f"zone_t_{zone}",
            )
    return new_temps


def render_screw_speed(state: ProcessState) -> float:
    """Rend l'input vitesse vis. Retourne la nouvelle valeur."""
    return st.number_input(
        "Vitesse vis (rpm)",
        min_value=1.0, max_value=3000.0,
        value=float(state.screw_rpm), step=10.0,
        key="screw_rpm_main",
        help="Vitesse de rotation de la vis. Influence directement Fill Factor, "
             "Résidence et SME estimé.",
    )


def render_kpis(state: ProcessState) -> None:
    """Affiche les KPIs vis hérités + SME estimé V1."""
    k = state.kpis
    cols = st.columns(6)
    cols[0].metric(
        "Éléments", f"{k.n_elements:.0f}",
        help="Nombre d'éléments utilisateurs sur la vis (tip exclu).",
    )
    cols[1].metric(
        "Volume libre", f"{k.free_volume_cm3:.2f} cm³",
        help="Volume libre restant — hérité du calcul Network 7 (Kévin).",
    )
    cols[2].metric(
        "Fill Factor", f"{k.fill_factor * 100:.1f} %",
        help="Taux de remplissage moyen — cible 30-55 % en compounding standard.",
    )
    cols[3].metric(
        "Résidence", f"{k.residence_time_s:.1f} s",
        help="Temps de séjour total de la matière dans la vis.",
    )
    cols[4].metric(
        "SME estimé", f"{k.sme_kwh_per_kg:.2f} kWh/kg",
        help="Estimation V1 (proxy heuristique, sera remplacée par lecture "
             "torque réelle en V2). Seuil critique typique SSB : 0.40 kWh/kg.",
    )
    cols[5].metric(
        "Profil", k.profile_archetype or "—",
        help="Archétype profil détecté par la couche IA existante.",
    )


# ---------------------------------------------------------------------------
# Bandeau V2 — placeholders torque/pressure (non implémenté en V1)
# ---------------------------------------------------------------------------
def render_v2_placeholder(state: ProcessState) -> tuple[float | None, float | None]:
    """Panneau « FEEDBACK V2 » — saisie manuelle ou lecture future."""
    st.markdown("##### Feedback réel — placeholders V2")
    st.caption(
        "Champs réservés à la future boucle de feedback streaming "
        "(OPC-UA / API extrudeuse). En V1 : saisie manuelle facultative — "
        "si renseignés, l'agent les utilise pour calibrer le SME réel."
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        enable_v2 = st.toggle(
            "Activer feedback V2",
            value=state.v2.feedback_enabled,
            key="v2_enable",
        )
    with c2:
        torque = st.number_input(
            "Couple (%)",
            min_value=0.0, max_value=100.0,
            value=float(state.v2.torque_pct if state.v2.torque_pct is not None else 0.0),
            step=1.0,
            key="v2_torque",
            disabled=not enable_v2,
            help="% du couple nominal vis. Si renseigné, le SME est recalculé.",
        )
    with c3:
        pressure = st.number_input(
            "Pression filière (bar)",
            min_value=0.0, max_value=400.0,
            value=float(state.v2.pressure_die_bar if state.v2.pressure_die_bar is not None else 0.0),
            step=1.0,
            key="v2_pressure",
            disabled=not enable_v2,
            help="Pression mesurée à la filière. Servira à la fermeture de "
                 "boucle V2 (correction profil thermique automatique).",
        )

    state.v2.feedback_enabled = enable_v2
    if not enable_v2:
        return None, None
    return (torque if torque > 0 else None, pressure if pressure > 0 else None)
