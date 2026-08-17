"""
app_industrial.py — Agent IA industriel d'extrusion (V1).

Lancement :
    streamlit run AgentIndustrial_v1/app_industrial.py

Objectif V1 :
    - Réutiliser l'existant Kévin (screw_logic, screw_render) sans le modifier.
    - Ajouter la gestion avancée multi-feeders (1..5, 6 phases matière).
    - Ajouter une couche IA explicable (rule-based) avec alertes + recos
      actionnables.
    - Préparer les placeholders V2 (torque, pressure) pour la future boucle
      de feedback réelle.

Architecture : monopage, sections empilées, DOM stable (cf. notes
removeChild dans app/Supervision.py — même contrainte respectée).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Bootstrap sys.path (script Streamlit, pas un module)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent  # rondol-ia-project/
for p in (_ROOT, _ROOT / "app"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# Imports package (absolus)
from AgentIndustrial_v1.core.feeders import (  # noqa: E402
    FEEDER_POSITIONS,
    equivalent_main_density,
    new_feeder_bank,
)
from AgentIndustrial_v1.core.process import ProcessState  # noqa: E402
from AgentIndustrial_v1.core.recommendations import build_recommendations  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
from AgentIndustrial_v1.core.screw_adapter import (  # noqa: E402
    default_screw_config,
    refresh_kpis,
)

# Import existant Kévin (sans modification)
from screw_logic import (  # noqa: E402
    ELEMENT_TYPES,
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    START_ELMT_ZONE,
    TIP_PART1_POS,
    add_element,
    base_type as legacy_base_type,
    enforce_tip_constraint,
    is_part2 as legacy_is_part2,
    new_empty_configuration,
    zone_residence_times,
)
from screw_render import build_screw_assembly_html  # noqa: E402

from AgentIndustrial_v1.ui.ai_panel import (  # noqa: E402
    render_alerts,
    render_header,
    render_recommendations,
)
from AgentIndustrial_v1.ui.feeders_panel import render as render_feeders  # noqa: E402
from AgentIndustrial_v1.ui.process_panel import (  # noqa: E402
    render_kpis,
    render_screw_speed,
    render_temperature,
    render_v2_placeholder,
)
from AgentIndustrial_v1.ui.styles import GLOBAL_CSS, header_banner_html  # noqa: E402


# ---------------------------------------------------------------------------
# Configuration page (DOIT être 1er appel Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AgentIndustrial V1 — Rondol",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.html(GLOBAL_CSS)


# ---------------------------------------------------------------------------
# Profils démo
# ---------------------------------------------------------------------------
def _demo_screw_profile() -> list[int]:
    """Config démo standard : convoyage → kneading → convoyage → kneading → conv."""
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=6)   # Forward conveying
    add_element(cfg, 4, count=2)   # Kneading 90°
    add_element(cfg, 7, count=2)   # Kneading 60°
    add_element(cfg, 1, count=5)   # Forward
    add_element(cfg, 8, count=1)   # Kneading 45°
    add_element(cfg, 5, count=1)   # Kneading 30°
    add_element(cfg, 1, count=6)   # Forward
    return cfg


def _demo_state_lfp_latp_li() -> ProcessState:
    """État démo SSB : LFP poudre + LATP poudre + Li semi-liquide.

    Cas pilote du poster scientifique 15 mai 2026 — démonstration crédible
    devant un manager industriel familier du process SSB.
    """
    from AgentIndustrial_v1.core.feeders import FeederSpec
    feeders = [
        FeederSpec(
            feeder_id=1, enabled=True, label="LFP cathode",
            material_id="powder", position="Z0",
            speed_rpm=80.0, mass_flow_g_per_min=25.0,
            density_g_per_cm3=1.10, thermal_expansion_per_K=5.0e-5,
        ),
        FeederSpec(
            feeder_id=2, enabled=True, label="LATP électrolyte",
            material_id="powder", position="Z2",
            speed_rpm=60.0, mass_flow_g_per_min=10.0,
            density_g_per_cm3=0.85, thermal_expansion_per_K=5.0e-5,
        ),
        FeederSpec(
            feeder_id=3, enabled=True, label="Li précurseur",
            material_id="semi_liquid", position="Z3",
            speed_rpm=None, mass_flow_g_per_min=4.0,
            density_g_per_cm3=1.20, thermal_expansion_per_K=6.0e-4,
        ),
        FeederSpec(
            feeder_id=4, enabled=False, label="",
            material_id="liquid", position="Z4",
            speed_rpm=None, mass_flow_g_per_min=0.0,
            density_g_per_cm3=1.00, thermal_expansion_per_K=8.0e-4,
        ),
        FeederSpec(
            feeder_id=5, enabled=False, label="",
            material_id="gas", position="Z5",
            speed_rpm=None, mass_flow_g_per_min=0.0,
            density_g_per_cm3=0.002, thermal_expansion_per_K=3.4e-3,
        ),
    ]
    state = ProcessState(
        screw_config=_demo_screw_profile(),
        screw_rpm=150.0,
        feeders=feeders,
    )
    return state


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "ai_state" not in st.session_state:
    s = ProcessState(screw_config=default_screw_config(), feeders=new_feeder_bank())
    s.screw_config = _demo_screw_profile()  # démo immédiate à l'ouverture
    st.session_state["ai_state"] = s

state: ProcessState = st.session_state["ai_state"]


# ---------------------------------------------------------------------------
# Sidebar — actions globales + scénarios démo
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("**AGENT INDUSTRIAL V1**")
    st.caption("Extrudeuse bivis 10,5 mm · SSB compounding")
    st.divider()

    st.markdown("**Scénarios démo**")
    if st.button("⊕ Cas LFP + LATP + Li (poster 15 mai)",
                 width="stretch", key="btn_demo_lfp"):
        st.session_state["ai_state"] = _demo_state_lfp_latp_li()
        st.rerun()
    if st.button("⊕ Cas par défaut (1 feeder granulés)",
                 width="stretch", key="btn_demo_default"):
        st.session_state["ai_state"] = ProcessState(
            screw_config=_demo_screw_profile(),
            feeders=new_feeder_bank(),
        )
        st.rerun()
    if st.button("⟲ Reset vis (config vide)",
                 width="stretch", key="btn_reset_screw"):
        state.screw_config = new_empty_configuration()
        st.rerun()
    if st.button("⊕ Charger profil démo standard",
                 width="stretch", key="btn_load_demo_screw"):
        state.screw_config = _demo_screw_profile()
        st.rerun()
    st.divider()

    st.markdown("**Architecture V1**")
    st.caption(
        "• Logique métier vis : module `screw_logic` (Kévin) — inchangé.\n"
        "• Multi-feeders : `core.feeders` (V1, nouveau).\n"
        "• Couche IA : `core.rules` + `core.recommendations` (rule-based, "
        "explicable, traçable).\n"
        "• V2 (à venir) : feedback torque + pression streaming."
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.html(header_banner_html("Agent IA explicable — extrusion bivis SSB"))

st.markdown("### Agent Industriel V1 — pilote extrusion bivis")
st.caption(
    "Outil de pilotage et conseil procédé. Conserve l'existant Kévin "
    "(profil vis, FF, résidence) et ajoute : gestion multi-feeders 5 voies, "
    "moteur de règles explicable, recommandations actionnables chiffrées."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Procédé : températures + vitesse vis
# ---------------------------------------------------------------------------
with st.container():
    st.markdown("#### 1. Procédé")
    c_left, c_right = st.columns([3, 1])
    with c_left:
        new_temps = render_temperature(state)
    with c_right:
        st.markdown("##### Vitesse vis")
        new_rpm = render_screw_speed(state)
        st.metric(
            "Δ rpm",
            f"{new_rpm:.0f}",
            f"{new_rpm - state.screw_rpm:+.0f} rpm",
            help="Variation par rapport à la valeur précédente du widget.",
        )
state.zone_temps_C = new_temps
state.screw_rpm = new_rpm

st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Feeders
# ---------------------------------------------------------------------------
with st.container():
    st.markdown("#### 2. Banc feeders")
    state.feeders = render_feeders(state.feeders)

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Profil vis (visualisation héritée Kévin)
# ---------------------------------------------------------------------------
with st.container():
    st.markdown("#### 3. Profil vis (visualisation héritée)")
    st.caption(
        "Affichage et logique inchangés depuis l'application Kévin — "
        "l'agent V1 consomme le profil tel quel. Pour modifier finement le "
        "profil, utiliser la page Profile de l'application Supervision."
    )
    _solid_flow = sum(
        f.mass_flow_g_per_min for f in state.feeders if f.enabled and f.is_solid
    )
    _density = equivalent_main_density(state.feeders)
    _zone_rt = zone_residence_times(
        state.screw_config, float(state.screw_rpm), _solid_flow, _density,
    )
    _zone_labels = ["Feed"] + [f"Z{i}" for i in range(1, 9)]

    def _fmt_rt(v: float) -> str:
        if v <= 0:
            return "—"
        if v >= 10:
            return f"{v:.0f} s"
        return f"{v:.1f}".replace(".", ",") + " s"

    _zone_subvalues = [_fmt_rt(_zone_rt[i]) for i in range(9)]
    _tip = enforce_tip_constraint(state.screw_config)
    if _tip.cleaned != state.screw_config:
        for i, v in enumerate(_tip.cleaned):
            state.screw_config[i] = v

    st.html(build_screw_assembly_html(
        state.screw_config, N_POSITIONS,
        base_type_fn=legacy_base_type,
        is_part2_fn=legacy_is_part2,
        element_full_name_fn=lambda t: ELEMENT_TYPES[t].full_name,
        show_zones=True,
        zone_starts=list(START_ELMT_ZONE)[:9],
        zone_labels=_zone_labels,
        zone_subvalues=_zone_subvalues,
        feeder_markers=[
            {"pos": MAIN_FEEDER_POSITION, "label": "MAIN", "color": "#10B981"},
        ],
        tip_part1_pos=TIP_PART1_POS,
        tip_status=_tip.status,
    ))

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — KPIs (recalculés après les modifs procédé/feeders)
# ---------------------------------------------------------------------------
refresh_kpis(state)
with st.container():
    st.markdown("#### 4. Indicateurs procédé")
    render_kpis(state)

st.divider()

# ---------------------------------------------------------------------------
# Section 5 — Feedback V2 (placeholder)
# ---------------------------------------------------------------------------
with st.container():
    st.markdown("#### 5. Feedback procédé — V2 (préparation)")
    torque, pressure = render_v2_placeholder(state)
    if torque is not None:
        state.v2.torque_pct = torque
    if pressure is not None:
        state.v2.pressure_die_bar = pressure
    # Si torque vient d'être renseigné, recalculer SME basé sur torque réel.
    if torque is not None:
        refresh_kpis(state)

st.divider()

# ---------------------------------------------------------------------------
# Section 6 — Agent IA (le cœur du delta vs existant)
# ---------------------------------------------------------------------------
with st.container():
    st.markdown("#### 6. Agent IA — analyse + recommandations")
    st.caption(
        "Moteur rule-based explicable : chaque alerte est traçable à une règle "
        "définie dans `core/rules.py`. Pas de LLM, pas de chatbot — uniquement "
        "des règles physiques et procédé documentées, avec evidence chiffrée."
    )

    report = evaluate(state)
    recommendations = build_recommendations(state, report.alerts)

    render_header(report)
    a_col, r_col = st.columns([1, 1])
    with a_col:
        render_alerts(report)
    with r_col:
        render_recommendations(recommendations)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.caption(
    "AgentIndustrial V1 · règle-based · "
    f"{len(report.alerts)} alerte(s) · {len(recommendations)} reco(s) · "
    f"score {report.risk_score}/100 · "
    "extension V2 prévue (boucle torque/pressure streaming)"
)
