"""
feeders_panel.py — UI banc feeders (1 à 5 actifs simultanés).

Pour chaque feeder, l'opérateur règle :
  - on/off
  - libellé libre
  - type matière (granulés, poudres, liquide, semi-liquide, gaz, supercritique)
  - position (Z0..Z7, die)
  - vitesse, débit, densité, dilatation thermique
"""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from ..core.feeders import (
    FEEDER_POSITIONS,
    MATERIAL_TYPES,
    FeederSpec,
    active_feeders,
    mass_flow_by_phase,
)


_MATERIAL_OPTIONS = list(MATERIAL_TYPES.keys())
_MATERIAL_LABELS = {k: v.label_fr for k, v in MATERIAL_TYPES.items()}


def _material_default_for(material_id: str) -> tuple[float, float]:
    """Retourne (ρ_default, α_default) pour pré-remplir le formulaire."""
    m = MATERIAL_TYPES[material_id]
    rho = (m.typical_density_range[0] + m.typical_density_range[1]) / 2.0
    return rho, m.typical_thermal_alpha


def _render_one_feeder(f: FeederSpec) -> FeederSpec:
    """Rend les widgets d'un feeder et retourne la FeederSpec mise à jour."""
    fid = f.feeder_id
    with st.container(border=True, key=f"feeder_box_{fid}"):
        head_c1, head_c2, head_c3 = st.columns([1, 3, 1])
        with head_c1:
            enabled = st.toggle(
                "Actif", value=f.enabled, key=f"fd_en_{fid}",
            )
        with head_c2:
            label = st.text_input(
                "Libellé", value=f.label,
                key=f"fd_label_{fid}",
                placeholder=f"Feeder #{fid}",
            )
        with head_c3:
            st.caption(f"**#{fid}**")
            st.caption(f.material.feeder_tech)

        # Si désactivé, on rend les autres widgets en lecture seule (disabled)
        # pour conserver la structure DOM stable.
        c1, c2, c3 = st.columns(3)
        with c1:
            mat_id = st.selectbox(
                "Type matière",
                options=_MATERIAL_OPTIONS,
                index=_MATERIAL_OPTIONS.index(f.material_id),
                format_func=lambda k: _MATERIAL_LABELS[k],
                key=f"fd_mat_{fid}",
                disabled=not enabled,
            )
        with c2:
            pos = st.selectbox(
                "Position",
                options=list(FEEDER_POSITIONS),
                index=FEEDER_POSITIONS.index(f.position),
                key=f"fd_pos_{fid}",
                disabled=not enabled,
            )
        with c3:
            speed = st.number_input(
                "Vitesse (rpm)",
                min_value=0.0, max_value=2000.0,
                value=float(f.speed_rpm or 0.0),
                step=5.0,
                key=f"fd_spd_{fid}",
                disabled=not enabled,
            )

        d1, d2, d3 = st.columns(3)
        with d1:
            flow = st.number_input(
                "Débit (g/min)",
                min_value=0.0, max_value=2000.0,
                value=float(f.mass_flow_g_per_min), step=1.0,
                key=f"fd_flow_{fid}",
                disabled=not enabled,
            )
        with d2:
            rho_def, alpha_def = _material_default_for(mat_id)
            # Reset auto vers défaut matière si l'opérateur change le type.
            rho_val = f.density_g_per_cm3 if mat_id == f.material_id else rho_def
            density = st.number_input(
                "Densité (g/cm³)",
                min_value=0.0001, max_value=10.0,
                value=float(rho_val), step=0.05, format="%.4f",
                key=f"fd_dens_{fid}",
                disabled=not enabled,
            )
        with d3:
            alpha_val = (
                f.thermal_expansion_per_K
                if mat_id == f.material_id else alpha_def
            )
            alpha = st.number_input(
                "Dilat. therm. α (1/K)",
                min_value=0.0, max_value=1.0e-1,
                value=float(alpha_val), step=1.0e-5, format="%.6f",
                key=f"fd_alpha_{fid}",
                disabled=not enabled,
            )

        # Aperçu compact en bas de carte
        if enabled:
            phase_chip = (
                f'<span style="background:rgba(6,182,212,0.15);color:#bfdbfe;'
                f'border:1px solid #06B6D4;border-radius:0.2rem;'
                f'padding:0.1rem 0.4rem;font-size:0.7rem;font-weight:600;">'
                f'{MATERIAL_TYPES[mat_id].phase}</span>'
            )
            tech_chip = (
                f'<span style="background:rgba(255,255,255,0.04);color:#D1D5DB;'
                f'border:1px solid #1F2937;border-radius:0.2rem;'
                f'padding:0.1rem 0.4rem;font-size:0.7rem;font-weight:500;">'
                f'{MATERIAL_TYPES[mat_id].feeder_tech}</span>'
            )
            st.html(
                f'<div style="display:flex;gap:0.4rem;margin-top:0.3rem;'
                f'flex-wrap:wrap;">{phase_chip}{tech_chip}</div>'
            )
        else:
            st.caption("Slot désactivé — n'entre pas dans le bilan ni dans les règles.")

    return replace(
        f,
        enabled=enabled,
        label=label,
        material_id=mat_id,
        position=pos,
        speed_rpm=speed,
        mass_flow_g_per_min=flow,
        density_g_per_cm3=density,
        thermal_expansion_per_K=alpha,
    )


def _bilan_html(feeders: list[FeederSpec]) -> str:
    actives = active_feeders(feeders)
    flows = mass_flow_by_phase(feeders)
    total = sum(flows.values())
    rows = [
        ("Feeders actifs", f"{len(actives)} / 5"),
        ("Débit total", f"{total:.1f} g/min"),
        ("· Solides", f"{flows['solid']:.1f} g/min"),
        ("· Liquides", f"{flows['liquid']:.1f} g/min"),
        ("· Gaz", f"{flows['gas']:.1f} g/min"),
        ("· Supercritique", f"{flows['supercritical']:.1f} g/min"),
    ]
    cells = "".join(
        f'<div style="flex:1 1 0;min-width:120px;padding:0.4rem 0.5rem;'
        f'background:#0F1419;border:1px solid #1F2937;border-radius:0.25rem;">'
        f'<div style="color:#6B7280;font-size:0.68rem;font-weight:600;'
        f'letter-spacing:0.04em;text-transform:uppercase;">{k}</div>'
        f'<div style="color:#F9FAFB;font-size:0.95rem;font-weight:600;'
        f'margin-top:0.15rem;font-variant-numeric:tabular-nums;">{v}</div>'
        f'</div>'
        for k, v in rows
    )
    return (
        '<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.5rem;">'
        + cells + "</div>"
    )


def render(feeders: list[FeederSpec]) -> list[FeederSpec]:
    """Rend la section feeders complète et retourne la nouvelle banque.

    L'appelant doit assigner le retour à st.session_state['feeders'] et faire
    un st.rerun() implicite via les widgets Streamlit.
    """
    st.markdown("##### Gestion feeders — banc 5 voies")
    st.caption(
        "Configuration multi-feeders avec types de matière, positions "
        "d'injection et caractéristiques physiques. L'agent IA analyse la "
        "cohérence physique + thermique de chaque feeder actif."
    )

    # Bilan global au-dessus des cartes
    st.html(_bilan_html(feeders))

    updated: list[FeederSpec] = []
    # 2 colonnes × N lignes (5 feeders → 3 lignes : 2,2,1).
    rows = [(0, 1), (2, 3), (4,)]
    for row in rows:
        cols = st.columns(len(row))
        for col, idx in zip(cols, row):
            with col:
                if idx < len(feeders):
                    updated.append(_render_one_feeder(feeders[idx]))
    # Conserve les éventuels feeders au-delà de l'index 4 (paranoïa)
    if len(updated) < len(feeders):
        updated.extend(feeders[len(updated):])
    return updated
