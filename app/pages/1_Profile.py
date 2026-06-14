"""
1_Profile.py — Configuration vis (procédé extrusion SSB).

Inspiré de l'écran Profile du HMI Rondol :
- 81 positions de vis (0..80) organisées en 9 zones (Feed + Z1..Z8)
- 13 types d'éléments de vis avec boutons +/-
- KPIs temps réel : nombre d'éléments, volume, fill factor, résidence
- Agent IA : recommandations basées sur la configuration
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP = Path(__file__).resolve().parent.parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

# Dossier images éléments de vis (validé Étape 5IA)
SCREW_IMG_DIR = ROOT / "references" / "screw_elements"

from screw_logic import (  # noqa: E402
    ELEMENT_TYPES,
    MAIN_FEEDER_POSITION,
    MAX_USER_ELEMENTS,
    N_POSITIONS,
    PART2_OFFSET,
    SIDE_FEEDER_DISABLED_POSITION,
    SIDE_FEEDER_DISABLED_ZONE,
    SIDE_FEEDER_MAX_ZONE,
    START_ELMT_ZONE,
    TIP_PART1_POS,
    TOTAL_FREE_VOL,
    add_element,
    add_elements_atomic,
    base_type,
    count_elements,
    enforce_tip_constraint,
    fill_factor_average,
    is_part2,
    free_volume,
    new_empty_configuration,
    occupied_volume_per_screw,
    occupied_volume_total,
    place_element_at,
    position_to_zone,
    remaining_slots,
    remove_at,
    residence_time,
    side_feeder_position,
    total_volume_used,
    zone_residence_times,
)
from screw_render import (  # noqa: E402
    analyze_profile,
    analyze_systemic,
    build_decision_html,
    build_decision_summary_html,
    build_screw_assembly_html,
    build_systemic_html,
    compute_recommendations,
    list_placed_elements,
    recommend_element_count,
)

# i18n — sélecteur de langue + traduction du chrome (B1).
from rondol_i18n import current_lang, language_selector, t  # noqa: E402

# Phase S1 : Profile ne saisit plus l'étalonnage feeder (édition centralisée
# dans Settings). L'import render_feeder_calibration est retiré pour qu'aucun
# widget concurrent ne réécrive `feeder_g_per_min`.

# P3.2 : source de vérité current_run_state + projection legacy (sens unique).
from run_state_adapter import sync_legacy_projection  # noqa: E402

# Store opérateur central persistant (survie navigation / langue / refresh).
from operator_store import capture_operator_state, restore_operator_state  # noqa: E402

# Commit profil → snapshot validé (survie cross-page, lu par Supervision/Agent).
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402
    commit as applied_commit,
    get_applied as applied_get,
    hydrate_session_from_applied,
)
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
from AgentIndustrial_v1.core.screw_adapter import refresh_kpis  # noqa: E402

st.set_page_config(page_title=t("page.profile.title"), layout="wide")

# PRIORITÉ SNAPSHOT : le profil vis sauvegardé (applied_state.json) hydrate la
# session AVANT le store opérateur. Une édition vivante (screw_config présent
# en session) n'est jamais écrasée — setdefault-only.
hydrate_session_from_applied(st.session_state)
# Restaure les valeurs métier saisies (depuis le store central / disque) AVANT
# d'instancier les widgets — survie navigation multipage + refresh navigateur.
restore_operator_state(st.session_state)

# ---------------------------------------------------------------------------
# CSS global stable (st.html, pas de unsafe_allow_html)
# ---------------------------------------------------------------------------
st.html("""
<style>
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background-color:#0B0F14!important;}
.block-container{padding-top:0.5rem!important;padding-left:1.4rem!important;padding-right:1.4rem!important;max-width:100%!important;}
header[data-testid="stHeader"]{background:transparent!important;height:0!important;}
[data-testid="stSidebar"]{background-color:#0D1117!important;border-right:1px solid #1F2937!important;}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label,[data-testid="stSidebar"] div{color:#9CA3AF!important;}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0D1117}
::-webkit-scrollbar-thumb{background:#374151;border-radius:3px}
/* Hauteur fixe des thumbnails d'éléments — alignement vertical des cartes */
[data-testid="stImage"] img{max-height:90px!important;object-fit:contain!important;}
</style>
""")

# Couleurs Rondol (vert HMI + sombre)
RONDOL_GREEN = "#4CAF50"
BG_CARD = "#111827"
BORDER = "#1F2937"

# ---------------------------------------------------------------------------
# État (session) — configuration vis
# ---------------------------------------------------------------------------
def _init_default_config() -> list[int]:
    """Configuration par défaut démo (utilise l'API screw_logic).

    Convoyage main feeder → kneading blocks → convoyage → tip (forcé Étape 1).
    """
    cfg = new_empty_configuration()  # tip déjà placé en 79-80
    # Convoyage avant : 6 éléments entiers (positions 4,6,8,10,12,14)
    add_element(cfg, 1, count=6)
    # 2 malaxages 90° (positions 16,18)
    add_element(cfg, 4, count=2)
    # 2 malaxages 60° (positions 20,22)
    add_element(cfg, 7, count=2)
    # Convoyage : 5 éléments entiers
    add_element(cfg, 1, count=5)
    # 1 malaxage 45° + 1 malaxage 30°
    add_element(cfg, 8, count=1)
    add_element(cfg, 5, count=1)
    # Convoyage final : 6 éléments entiers
    add_element(cfg, 1, count=6)
    return cfg


if "screw_config" not in st.session_state:
    st.session_state["screw_config"] = _init_default_config()

# Defaults for process params (shared with Settings)
st.session_state.setdefault("screw_rpm", 120.0)
st.session_state.setdefault("feeder_g_per_min", 30.0)
st.session_state.setdefault("bulk_density", 0.55)
st.session_state.setdefault("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE)  # 0=off, 1..8

cfg: list[int] = st.session_state["screw_config"]

# ---------------------------------------------------------------------------
# Header HMI — style Rondol (bandeau vert)
# ---------------------------------------------------------------------------
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>{t("profile.banner.left")}</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">{t("profile.banner.right")}</span>'
    f'</div>'
)

# ---------------------------------------------------------------------------
# Sidebar : paramètres procédé
# ---------------------------------------------------------------------------
# Phase S1 stabilisation (manager 2026-06-09) : Profile est désormais la page
# d'édition du PROFIL DE VIS uniquement (boutons +1/+4/−1 sur les éléments).
# RPM / débit feeder / densité bulk sont LECTURE SEULE ici — leur édition se
# fait exclusivement dans la page **Settings**. Avant ce correctif, Profile
# avait ses propres widgets (sb_rpm / sb_feed / sb_dens) qui écrivaient
# directement les clés legacy `screw_rpm` / `feeder_g_per_min` / `bulk_density`
# en parallèle des widgets Settings (`ni_rpm_hmi` / étalonnage / `fd_dens_1`).
# Cette duplication de source de vérité causait des désynchronisations
# silencieuses après navigation. UNE source = Settings.
with st.sidebar:
    language_selector()
    st.divider()
    st.markdown(f"**{t('profile.sidebar.params')}**")
    st.caption(t("profile.sidebar.params_caption_ro"))

    # Lecture seule des valeurs pilotées depuis Settings. Hydratation garantie
    # par restore_operator_state + project_to_legacy (cf. ligne 89 + ligne 1149).
    _rpm_ro = float(st.session_state.get("screw_rpm", 120.0))
    _dens_ro = float(st.session_state.get("bulk_density", 0.55))
    _feed_ro = float(st.session_state.get("feeder_g_per_min", 0.0))

    st.metric(t("profile.sidebar.rpm"), f"{_rpm_ro:.0f} rpm")

    # Débit feeder : si l'étalonnage est exploitable, on l'affiche en clair
    # avec le rappel de la formule. Sinon, « Non calculable » (aucun débit par
    # défaut inventé — cohérent avec Moteur Procédé).
    _feed_rpm = float(st.session_state.get("feeder_rpm", 0.0))
    _feed_coeff = float(st.session_state.get("feeder_calib_g_h_per_rpm", 0.0))
    if _feed_ro > 0.0 and _feed_coeff > 0.0:
        st.metric(t("profile.sidebar.feed"), f"{_feed_ro:.2f} g/min")
        st.caption(t(
            "profile.sidebar.feed_calibrated_hint",
            rpm=f"{_feed_rpm:.0f}", coeff=f"{_feed_coeff:.2f}",
        ))
    elif _feed_ro > 0.0:
        st.metric(t("profile.sidebar.feed"), f"{_feed_ro:.2f} g/min")
    else:
        st.metric(t("profile.sidebar.feed"), t("profile.sidebar.feed_not_calculable"))

    st.metric(t("profile.sidebar.dens"), f"{_dens_ro:.3f} g/cm³")
    st.caption(t("profile.sidebar.piloted_by_settings"))
    st.markdown(f"**{t('profile.sidebar.dosage')}**")
    st.caption(t("profile.sidebar.sf_caption"))
    _sf_zone_now = int(st.session_state.get("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE))
    if not (SIDE_FEEDER_DISABLED_ZONE <= _sf_zone_now <= SIDE_FEEDER_MAX_ZONE):
        _sf_zone_now = SIDE_FEEDER_DISABLED_ZONE
    st.session_state["side_feeder_zone"] = st.selectbox(
        t("profile.sidebar.sf_zone"),
        options=list(range(SIDE_FEEDER_DISABLED_ZONE, SIDE_FEEDER_MAX_ZONE + 1)),
        index=_sf_zone_now,
        format_func=lambda z: t("profile.sidebar.sf_disabled") if z == 0 else f"Z{z}",
        key="sb_sf_zone",
    )
    _sf_zone = int(st.session_state["side_feeder_zone"])
    _sf_pos_preview = side_feeder_position(cfg, _sf_zone)
    if _sf_zone == SIDE_FEEDER_DISABLED_ZONE:
        st.caption(t("profile.sidebar.sf_off"))
    else:
        st.caption(t("profile.sidebar.sf_pos", z=_sf_zone, pos=f"{_sf_pos_preview:02d}"))
    st.divider()
    if st.button(t("profile.btn.reset"), use_container_width=True, key="btn_reset"):
        st.session_state["screw_config"] = new_empty_configuration()
        st.session_state["last_action_msg"] = ("info", t("profile.msg.reset"))
        st.rerun()
    if st.button(t("profile.btn.demo"), use_container_width=True, key="btn_demo"):
        st.session_state["screw_config"] = _init_default_config()
        st.session_state["last_action_msg"] = ("success", t("profile.msg.demo_loaded"))
        st.rerun()
    if st.button(t("profile.btn.demo_chaotic"), use_container_width=True, key="btn_demo_chaotic"):
        cfg_chaotic = new_empty_configuration()
        add_element(cfg_chaotic, 1, count=4)    # forward
        add_element(cfg_chaotic, 10, count=6)   # chaotic → effet losange
        add_element(cfg_chaotic, 1, count=4)    # forward
        add_element(cfg_chaotic, 4, count=2)    # kneading 90°
        add_element(cfg_chaotic, 1, count=3)    # forward final
        st.session_state["screw_config"] = cfg_chaotic
        st.session_state["last_action_msg"] = (
            "success", t("profile.msg.demo_chaotic")
        )
        st.rerun()
    st.divider()
    st.caption(t("profile.sidebar.freevol"))
    st.caption(t("profile.sidebar.layout"))

# ---------------------------------------------------------------------------
# Ligne zones / positions — visualisation vis (Plotly)
# ---------------------------------------------------------------------------
# Palette par type d'élément (14 entrées — index 0 = vide)
ELEMENT_COLORS: list[str] = [
    "#1F2937",  # 0 vide
    "#06B6D4",  # 1 Forward conveying      (cyan)
    "#0891B2",  # 2 Forward half           (cyan foncé)
    "#3B82F6",  # 3 Short-pitch            (bleu)
    "#A855F7",  # 4 Kneading 90°           (violet)
    "#EC4899",  # 5 Kneading 30°           (rose)
    "#10B981",  # 6 Large pitch            (vert)
    "#8B5CF6",  # 7 Kneading 60°           (violet clair)
    "#F472B6",  # 8 Kneading 45°           (rose clair)
    "#EF4444",  # 9 Reverse                (rouge)
    "#F59E0B",  # 10 Chaotic               (orange)
    "#FBBF24",  # 11 Toothed               (jaune)
    "#F97316",  # 12 Special mixing        (orange foncé)
    "#64748B",  # 13 Screw tip             (gris)
]

# Chemins des PNG pour les thumbnails des cartes (boutons +1/+4)
_RAW_IMAGE_MAP: dict[int, str] = {
    1:  "Forward conveying.png",
    2:  "Forward conveying half.png",
    3:  "Short-pitch elements.png",
    4:  "Kneading element 90°.png",
    5:  "Kneading element 30°.png",
    6:  "Large pitch elements.png",
    7:  "Kneading element 60°.png",
    8:  "Kneading element 45°.png",
    9:  "Reverse conveying.png",
    10: "Chaotic element.png",
    11: "Toothed element.png",
    12: "Special mixing element.png",
    13: "screw tip.png",
}
ELEMENT_IMAGES: dict[int, Path] = {
    t: (SCREW_IMG_DIR / fname)
    for t, fname in _RAW_IMAGE_MAP.items()
    if (SCREW_IMG_DIR / fname).exists()
}

# ---------------------------------------------------------------------------
# Rendu vis : délégué à app/screw_render.py (architecture validée — base
# procédurale CSS continue + signatures PNG pour les blocs uniquement).
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.assembly"))
st.caption(t("profile.cap.assembly"))

# --- Labels Rondol (Feed + Z1..Z8) + sous-ligne résidence par zone -----------
_zone_labels = ["Feed"] + [f"Z{i}" for i in range(1, 9)]
_zone_rt = zone_residence_times(
    cfg,
    float(st.session_state["screw_rpm"]),
    float(st.session_state["feeder_g_per_min"]),
    float(st.session_state["bulk_density"]),
)


def _fmt_zone_rt(v: float) -> str:
    """Formatage compact style HMI Rondol "Plug" : '0,8 s' / '12 s' / '—'."""
    if v <= 0.0:
        return "—"
    if v >= 10.0:
        return f"{v:.0f} s"
    return f"{v:.1f}".replace(".", ",") + " s"


_zone_subvalues = [_fmt_zone_rt(_zone_rt[i]) for i in range(9)]

# --- Marqueurs feeders (Main + Side si activé) -------------------------------
_feeder_markers: list[dict] = [
    {"pos": MAIN_FEEDER_POSITION, "label": "MAIN", "color": "#10B981"},
]
_sf_zone = int(st.session_state.get("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE))
if SIDE_FEEDER_DISABLED_ZONE < _sf_zone <= SIDE_FEEDER_MAX_ZONE:
    _sf_pos = side_feeder_position(cfg, _sf_zone)
    if 0 <= _sf_pos < N_POSITIONS - 1:  # exclut sentinelle 81 + tip
        _feeder_markers.append({
            "pos": _sf_pos,
            "label": f"SIDE Z{_sf_zone}",
            "color": "#06B6D4",
        })

# Vérification de l'invariant pointe de vis avant rendu — évite tout
# affichage incohérent si la session a accumulé des doublons.
_tip_state = enforce_tip_constraint(cfg)
if _tip_state.cleaned != cfg:
    # Restaure l'invariant en place dans la session (pas de re-allocation,
    # même référence pour ne pas casser st.session_state["screw_config"]).
    for _i, _v in enumerate(_tip_state.cleaned):
        cfg[_i] = _v

st.html(build_screw_assembly_html(
    cfg, N_POSITIONS,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    element_full_name_fn=lambda t: ELEMENT_TYPES[t].full_name,
    show_zones=True,
    zone_starts=list(START_ELMT_ZONE)[:9],
    zone_labels=_zone_labels,
    zone_subvalues=_zone_subvalues,
    feeder_markers=_feeder_markers,
    tip_part1_pos=TIP_PART1_POS,
    tip_status=_tip_state.status,
))
st.divider()

# ---------------------------------------------------------------------------
# Lecture métier + Synthèse par zone
# UN SEUL st.html() — DOM stable quel que soit l'état (vide ou rempli).
# Évite l'erreur React `removeChild` causée par variation du nombre de
# composants Streamlit entre rerenders (même contrainte que le banner d'état).
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.metier"))
placed = list_placed_elements(
    cfg, N_POSITIONS,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    position_to_zone_fn=position_to_zone,
    element_label_fn=lambda t: (ELEMENT_TYPES[t].full_name
                                if current_lang() == "en"
                                else ELEMENT_TYPES[t].label),
)


def _build_metier_html(placed_list) -> str:
    user_elements = [p for p in placed_list if p.type_id != 13]

    # 1. Tableau (toujours présent ; "no rows" cell si vide)
    if user_elements:
        rows_html = "".join(
            f'<tr>'
            f'<td style="padding:0.25rem 0.6rem;color:#9CA3AF;font-variant-numeric:tabular-nums;">'
            f'<b style="color:#F9FAFB;">{p.zone_name}</b></td>'
            f'<td style="padding:0.25rem 0.6rem;color:#D1D5DB;font-variant-numeric:tabular-nums;">'
            f'pos {p.pos:02d}</td>'
            f'<td style="padding:0.25rem 0.6rem;">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
            f'background:{ELEMENT_COLORS[p.type_id]};vertical-align:middle;margin-right:0.5rem;"></span>'
            f'<span style="color:#F9FAFB;font-weight:500;">{p.label}</span></td>'
            f'<td style="padding:0.25rem 0.6rem;color:#9CA3AF;font-style:italic;">{p.role}</td>'
            f"</tr>"
            for p in user_elements
        )
    else:
        rows_html = (
            '<tr><td colspan="4" '
            'style="padding:1rem 0.6rem;text-align:center;color:#6B7280;font-style:italic;">'
            + t("profile.tbl.empty")
            + "</td></tr>"
        )

    table_html = (
        '<div style="border:1px solid #1F2937;border-radius:0.3rem;background:#111827;'
        'overflow-x:auto;max-height:240px;overflow-y:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
        '<thead style="position:sticky;top:0;background:#0F1419;">'
        '<tr style="border-bottom:1px solid #1F2937;">'
        '<th style="text-align:left;padding:0.4rem 0.6rem;color:#6B7280;font-weight:600;font-size:0.75rem;letter-spacing:0.05em;">' + t("profile.tbl.zone") + '</th>'
        '<th style="text-align:left;padding:0.4rem 0.6rem;color:#6B7280;font-weight:600;font-size:0.75rem;letter-spacing:0.05em;">' + t("profile.tbl.position") + '</th>'
        '<th style="text-align:left;padding:0.4rem 0.6rem;color:#6B7280;font-weight:600;font-size:0.75rem;letter-spacing:0.05em;">' + t("profile.tbl.element") + '</th>'
        '<th style="text-align:left;padding:0.4rem 0.6rem;color:#6B7280;font-weight:600;font-size:0.75rem;letter-spacing:0.05em;">' + t("profile.tbl.role") + '</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
    )

    # 2. Synthèse par zone (toujours 9 cartes — vides ou remplies)
    zone_cells = []
    for z in range(9):
        z_elts = [p for p in user_elements if p.zone == z]
        n = len(z_elts)
        if n == 0:
            content = ('<span style="color:#4B5563;font-style:italic;">'
                       + t("profile.tbl.cell_empty") + '</span>')
            border = "#1F2937"
        else:
            role_counts: dict[str, int] = {}
            for p in z_elts:
                k = p.role.split(" ")[0]
                role_counts[k] = role_counts.get(k, 0) + 1
            dominant = max(role_counts, key=role_counts.get)
            content = (
                f'<span style="color:#F9FAFB;font-weight:600;">{n}</span>'
                f'<span style="color:#9CA3AF;font-size:0.72rem;display:block;'
                f'margin-top:0.1rem;">{dominant}</span>'
            )
            border = "#10B981" if n <= 5 else "#F59E0B"
        zone_cells.append(
            f'<div style="flex:1 1 0;min-width:60px;padding:0.4rem 0.3rem;'
            f'background:#0F1419;border:1px solid {border};border-radius:0.25rem;'
            f'text-align:center;">'
            f'<div style="color:#6B7280;font-size:0.68rem;font-weight:600;'
            f'letter-spacing:0.05em;margin-bottom:0.15rem;">Z{z}</div>'
            f"{content}</div>"
        )
    synthesis_html = (
        '<div style="margin-top:0.9rem;color:#D1D5DB;font-weight:600;font-size:0.92rem;">'
        + t("profile.tbl.synthesis") + "</div>"
        '<div style="display:flex;gap:0.3rem;margin-top:0.3rem;">'
        + "".join(zone_cells) + "</div>"
    )

    return table_html + synthesis_html


st.html(_build_metier_html(placed))
st.divider()

# ---------------------------------------------------------------------------
# KPIs procédé — labels explicites + tooltips ingénieur
# ---------------------------------------------------------------------------
# Compteur VISIBLE tip inclus (capacité totale 40 = 39 utilisateur + tip,
# exigence manager 2026-06-12). La limite de placement reste 39 (géométrie).
from screw_logic import TOTAL_ELEMENT_CAPACITY, count_total_elements  # noqa: E402,PLC0415
n_added = count_total_elements(cfg)
n_remaining = remaining_slots(cfg)
# Bivis : occupé par vis, occupé total (2 vis), libre = TOTAL − occupé total.
occ_per_screw = occupied_volume_per_screw(cfg)
occ_total = occupied_volume_total(cfg)
vol_free = max(0.0, free_volume(cfg))
rpm = float(st.session_state["screw_rpm"])
feed = float(st.session_state["feeder_g_per_min"])
dens = float(st.session_state["bulk_density"])
ff = fill_factor_average(cfg, rpm, feed, dens)
rt = residence_time(cfg, rpm, feed, dens)


def _fmt_count(x: float) -> str:
    """39.0 → '39' ; 12.5 → '12,5' (entiers sans décimale, demi-éléments avec)."""
    return f"{int(x)}" if x == int(x) else f"{x:.1f}".replace(".", ",")


st.markdown("##### " + t("profile.sec.kpis"))
st.caption(t("profile.cap.kpis", rpm=f"{rpm:.0f}", feed=f"{feed:.1f}", dens=f"{dens:.2f}"))

kcol1, kcol2, kcol3, kcol4, kcol5, kcol6 = st.columns(6)
kcol1.metric(
    t("profile.kpi.added"),
    f"{_fmt_count(n_added)} / {_fmt_count(TOTAL_ELEMENT_CAPACITY)}",
    help=t("profile.kpi.added_help"),
)
kcol2.metric(
    t("profile.kpi.slots"),
    _fmt_count(n_remaining),
    help=t("profile.kpi.slots_help"),
)
kcol3.metric(
    t("profile.kpi.vol_used"),
    f"{occ_per_screw:.2f} cm³",
    help=t("profile.kpi.vol_used_help"),
)
kcol4.metric(
    t("profile.kpi.vol_free"),
    f"{vol_free:.2f} cm³",
    help=t("profile.kpi.vol_free_help", maxv=f"{TOTAL_FREE_VOL:.2f}"),
)
kcol5.metric(
    t("profile.kpi.ff"),
    f"{ff * 100:.1f} %",
    help=t("profile.kpi.ff_help"),
)
kcol6.metric(
    t("profile.kpi.rt"),
    f"{rt:.1f} s",
    help=t("profile.kpi.rt_help"),
)

# Bivis : explicite les 3 volumes (par vis / total 2 vis / libre utile).
st.caption(t(
    "profile.cap.volumes",
    per=f"{occ_per_screw:.2f}",
    total=f"{occ_total:.2f}",
    free=f"{vol_free:.2f}",
))

st.divider()

# ---------------------------------------------------------------------------
# Construction du profil — 13 types d'éléments avec −1 / +1 / +4
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.build"))
st.caption(t("profile.cap.build"))

# ----- Bandeau d'état : structure DOM strictement stable -------------------
# Règle Streamlit (cf. Supervision.py) : "même nombre de composants à chaque
# render, quels que soient l'état..." Une variation 0/1/2 composants entre
# renders provoque l'erreur `removeChild` lors de la réconciliation React.
# Solution : 1 seul st.html() toujours appelé. Son contenu interne est opaque
# pour React (dangerouslySetInnerHTML) → mise à jour atomique sans reconcile.
_BANNER_STYLES: dict[str, tuple[str, str, str]] = {
    "success": ("#d1fae5", "#065f46", "#10B981"),
    "info":    ("#dbeafe", "#1e3a8a", "#3B82F6"),
    "warning": ("#fef3c7", "#92400e", "#F59E0B"),
    "error":   ("#fee2e2", "#991b1b", "#EF4444"),
}


def _banner_line(kind: str, html_content: str) -> str:
    bg, fg, acc = _BANNER_STYLES[kind]
    return (
        f'<div style="background:{bg};color:{fg};border-left:4px solid {acc};'
        f'padding:0.5rem 0.85rem;border-radius:0.25rem;font-size:0.9rem;'
        f'margin-bottom:0.45rem;line-height:1.35;">{html_content}</div>'
    )


def _build_status_banner_html(
    action_msg: tuple[str, str] | None,
    n_added_v: float,
    n_remaining_v: float,
) -> str:
    """2 lignes fixes (action + capacité), affichées ou masquées sans changer
    le nombre de composants Streamlit (1 seul st.html en sortie)."""
    parts: list[str] = []

    # Ligne 1 : dernier message d'action (toujours présente, repliée si vide)
    if action_msg is None:
        parts.append('<div style="height:0;overflow:hidden;margin:0;"></div>')
    else:
        kind, txt = action_msg
        if kind not in _BANNER_STYLES:
            kind = "info"
        parts.append(_banner_line(kind, txt))

    # Ligne 2 : statut capacité (toujours présente) — i18n FR/EN (Phase S2).
    if n_added_v <= 0:
        parts.append(_banner_line("info", t("profile.banner.empty")))
    elif n_remaining_v <= 0:
        parts.append(_banner_line(
            "warning",
            t("profile.banner.full",
              n=_fmt_count(n_added_v), max=_fmt_count(MAX_USER_ELEMENTS)),
        ))
    elif n_remaining_v < 4:
        parts.append(_banner_line(
            "info",
            t("profile.banner.almost_full", n=_fmt_count(n_remaining_v)),
        ))
    else:
        # État nominal : ligne minimale (présence DOM préservée, hauteur nulle)
        parts.append('<div style="height:0;overflow:hidden;margin:0;"></div>')

    return "".join(parts)


_action_msg = st.session_state.pop("last_action_msg", None)
st.html(_build_status_banner_html(_action_msg, n_added, n_remaining))


def _add_element(type_id: int, count: int = 1) -> int:
    """Ajoute `count` éléments via l'API screw_logic. Retourne le nb posés."""
    c = st.session_state["screw_config"]
    return add_element(c, type_id, count=count)


def _add_elements_atomic(type_id: int, count: int) -> bool:
    """Ajout atomique (tout ou rien) — pour bouton +N."""
    c = st.session_state["screw_config"]
    return add_elements_atomic(c, type_id, count)


def _remove_last_of_type(type_id: int) -> bool:
    """Retire l'occurrence la plus aval de ce type (1ère partie uniquement)."""
    c = st.session_state["screw_config"]
    # On scanne en partant du tip vers le main feeder, on cible la 1ère partie
    # (les 2èmes parties sont retirées automatiquement par remove_at).
    for i in range(TIP_PART1_POS - 1, MAIN_FEEDER_POSITION - 1, -1):
        if c[i] == type_id and not is_part2(c[i]):
            return remove_at(c, i)
    return False


# Grille 4 colonnes × 4 rangées (13 types + 3 vides pour structure stable)
SLOT_LAYOUT: list[list[int]] = [
    [1, 2, 3, 4],       # rangée 1
    [5, 6, 7, 8],       # rangée 2
    [9, 10, 11, 12],    # rangée 3
    [13, 0, 0, 0],      # rangée 4 (3 placeholders pour structure fixe)
]

for row_idx, row in enumerate(SLOT_LAYOUT):
    cols = st.columns(4)
    for col_idx, type_id in enumerate(row):
        with cols[col_idx]:
            if type_id == 0:
                # Placeholder invisible — maintient la structure DOM stable
                with st.container(border=False, key=f"slot_empty_{row_idx}_{col_idx}"):
                    st.markdown("\u00a0")
                    st.markdown("\u00a0")
                    st.markdown("\u00a0")
                continue
            et = ELEMENT_TYPES[type_id]
            count_here = sum(1 for e in cfg if e == type_id)
            color = ELEMENT_COLORS[type_id]
            # Pointe de vis (type 13) : élément physique unique, structurel,
            # non déplaçable, non duplicable — on désactive tous les boutons
            # et on affiche un badge 🔒 « fin de vis ».
            is_tip = (type_id == 13)
            with st.container(border=True, key=f"slot_{type_id}"):
                header_right = (
                    f'<span style="background:{color};color:#0B0F14;'
                    f'font-weight:700;font-size:0.65rem;letter-spacing:0.04em;'
                    f'padding:0.1rem 0.45rem;border-radius:0.25rem;">'
                    f'🔒 {t("profile.tip_lock")}</span>'
                ) if is_tip else (
                    f'<span style="background:#0B0F14;color:#F9FAFB;'
                    f'border:1px solid {BORDER};padding:0.1rem 0.5rem;'
                    f'border-radius:0.25rem;font-weight:700;font-size:0.9rem;">'
                    f'{count_here}</span>'
                )
                st.html(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="color:{color};font-weight:600;font-size:0.85rem;">● '
                    f'{et.full_name if current_lang() == "en" else et.label}</span>'
                    f'{header_right}'
                    f'</div>'
                )
                img_path = ELEMENT_IMAGES.get(type_id)
                if img_path is not None:
                    st.image(str(img_path), use_container_width=True)
                st.caption(et.full_name)
                # +4 atomique réservé aux éléments entiers (consomme 1 slot ADD)
                # type 2 = demi-élément → on garde +1 / −1 uniquement
                # type 13 = pointe → tous boutons désactivés (élément physique
                # unique, posé en fin de vis, non duplicable, non retirable).
                bcol_m, bcol_p1, bcol_p4 = st.columns(3)
                slot_cost = 0.5 if type_id == 2 else 1.0
                # Gating sur le compteur UTILISATEUR (tip exclu) : la limite de
                # placement reste 39 — l'affichage 40 inclut le tip déjà monté.
                _n_user = count_elements(cfg)
                disable_p1 = is_tip or (_n_user + slot_cost > MAX_USER_ELEMENTS + 1e-9)
                disable_p4 = is_tip or (type_id == 2) or (
                    _n_user + 4 * slot_cost > MAX_USER_ELEMENTS + 1e-9
                )
                disable_m = is_tip or (count_here == 0)
                if bcol_m.button("−1", key=f"minus_{type_id}", use_container_width=True, disabled=disable_m):
                    if _remove_last_of_type(type_id):
                        st.session_state["last_action_msg"] = (
                            "info", t("profile.msg.removed_one", lbl=et.label)
                        )
                    st.rerun()
                if bcol_p1.button("+1", key=f"plus1_{type_id}", use_container_width=True, disabled=disable_p1):
                    placed = _add_element(type_id, count=1)
                    if placed > 0:
                        st.session_state["last_action_msg"] = (
                            "success", t("profile.msg.added_one", lbl=et.label)
                        )
                    else:
                        st.session_state["last_action_msg"] = (
                            "warning",
                            t("profile.msg.add_impossible", lbl=et.label),
                        )
                    st.rerun()
                if bcol_p4.button("+4", key=f"plus4_{type_id}", use_container_width=True, disabled=disable_p4):
                    if _add_elements_atomic(type_id, 4):
                        st.session_state["last_action_msg"] = (
                            "success", t("profile.msg.added_four", lbl=et.label)
                        )
                    else:
                        st.session_state["last_action_msg"] = (
                            "warning",
                            t("profile.msg.add4_blocked", lbl=et.label),
                        )
                    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Recommandations Agent IA — UN SEUL st.html() (DOM atomique).
#
# Pourquoi un seul st.html : la version précédente itérait avec
#   `with st.container(...): st.html(...) | st.markdown(...)`
# Selon que la reco avait un titre ou non, le 1er enfant du container
# changeait de TYPE (HTML iframe vs Markdown). Streamlit/React réconcilient
# par type au même slot DOM → quand le nombre/contenu des recos varie entre
# rerenders (ajout d'un élément, reset…), le diff React échoue avec
# `NotFoundError: Failed to execute 'removeChild'`.
# Solution stable : sérialiser tout le panneau en HTML brut, mise à jour
# atomique via dangerouslySetInnerHTML — aucune réconciliation par
# composant. Même pattern que _build_metier_html / _build_status_banner_html.
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.reading"))
st.caption(t("profile.cap.reading"))
profile_reading = analyze_profile(
    cfg, rpm, feed, dens,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    position_to_zone_fn=position_to_zone,
    fill_factor_fn=fill_factor_average,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
)
_PROFILE_SEV_ACCENT = {
    "critique": ("#3b1212", "#fecaca", "#EF4444"),
    "warning":  ("#3b2c0a", "#fde68a", "#F59E0B"),
    "info":     ("#0f1d3b", "#bfdbfe", "#3B82F6"),
    "ok":       ("#0f2b1d", "#bbf7d0", "#10B981"),
}
_pbg, _pfg, _pacc = _PROFILE_SEV_ACCENT.get(
    profile_reading.archetype_severity, _PROFILE_SEV_ACCENT["info"]
)
_risks_html = ""
if profile_reading.risks:
    _risks_html = (
        '<div style="margin-top:0.4rem;display:flex;gap:0.35rem;flex-wrap:wrap;">'
        + "".join(
            f'<span style="background:rgba(239,68,68,0.15);color:#fecaca;'
            f'border:1px solid #EF4444;border-radius:0.2rem;'
            f'padding:0.1rem 0.45rem;font-size:0.7rem;font-weight:600;">⚠ {r}</span>'
            for r in profile_reading.risks
        )
        + "</div>"
    )
st.html(
    f'<div style="background:{_pbg};border-left:4px solid {_pacc};'
    f'border-radius:0.25rem;padding:0.7rem 0.95rem;margin-bottom:0.6rem;">'
    f'<div style="display:flex;gap:0.5rem;align-items:baseline;flex-wrap:wrap;">'
    f'<span style="color:{_pacc};font-weight:700;font-size:0.7rem;'
    f'letter-spacing:0.06em;">{t("profile.band.reading")}</span>'
    f'<span style="color:{_pfg};font-weight:600;font-size:1rem;">'
    f'{profile_reading.archetype}</span>'
    f'<span style="color:#9CA3AF;font-size:0.78rem;">·</span>'
    f'<span style="color:#9CA3AF;font-weight:500;font-size:0.85rem;">'
    f'{profile_reading.regime}</span>'
    f'</div>'
    f'<div style="color:{_pfg};opacity:0.9;font-size:0.85rem;line-height:1.5;'
    f'margin-top:0.35rem;">{profile_reading.summary}</div>'
    f'<div style="color:#9CA3AF;font-size:0.78rem;line-height:1.4;'
    f'margin-top:0.3rem;font-style:italic;">→ {profile_reading.regime_summary}</div>'
    f'{_risks_html}'
    f'</div>'
)

st.markdown("##### " + t("profile.sec.recos"))
st.caption(t("profile.cap.recos"))
recs = compute_recommendations(
    cfg, rpm, feed, dens,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    position_to_zone_fn=position_to_zone,
    fill_factor_fn=fill_factor_average,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
)

# Sévérité → (bg sombre, texte clair, accent, label badge).
# Mapping : critique → DANGER (rouge), warning → WARNING (orange),
# ok → OK (vert), info → INFO (bleu).
_REC_STYLE: dict[str, tuple[str, str, str, str]] = {
    "critique": ("#3b1212", "#fecaca", "#EF4444", "DANGER"),
    "warning":  ("#3b2c0a", "#fde68a", "#F59E0B", "WARNING"),
    "info":     ("#0f1d3b", "#bfdbfe", "#3B82F6", "INFO"),
    "ok":       ("#0f2b1d", "#bbf7d0", "#10B981", "OK"),
}


def _build_recs_html(recs_list: list[dict]) -> str:
    """Sérialise toutes les recos en un bloc HTML unique (DOM atomique).

    Format reco enrichi (depuis l'agent IA niveau ingénieur) :
      - badge sévérité + chip zone (Z3, Feed, Global…)
      - "Phénomène physique" (cisaillement, transport, chauffe…)
      - "Impact procédé" (homogénéité, dégradation, surcouple…)
      - "Action recommandée" — chiffrée, sensible aux paramètres Settings
      - mesure (FF %, ratios, n_éléments…) en bas à droite
    """
    if not recs_list:
        return (
            '<div style="padding:0.9rem;background:#111827;border:1px solid #1F2937;'
            'border-radius:0.3rem;color:#9CA3AF;font-style:italic;text-align:center;'
            'font-size:0.88rem;">'
            + t("profile.recos.none")
            + "</div>"
        )
    items: list[str] = []
    for r in recs_list:
        sev = r.get("severity", "info")
        bg, fg, acc, label = _REC_STYLE.get(sev, _REC_STYLE["info"])
        zone = r.get("zone", "—") or "—"
        physics = r.get("physics", r.get("title", ""))
        impact = r.get("impact", "")
        action = r.get("action", r.get("detail", ""))
        evidence = r.get("evidence", "")

        # Header : badge sévérité + chip zone + phénomène physique
        header = (
            f'<div style="display:flex;align-items:center;gap:0.55rem;'
            f'flex-wrap:wrap;margin-bottom:0.35rem;">'
            f'<span style="background:{acc};color:#0B0F14;font-weight:700;'
            f'font-size:0.68rem;padding:0.12rem 0.5rem;border-radius:0.2rem;'
            f'letter-spacing:0.06em;">{label}</span>'
            f'<span style="background:rgba(255,255,255,0.05);color:{fg};'
            f'border:1px solid {acc};font-weight:700;font-size:0.7rem;'
            f'padding:0.1rem 0.45rem;border-radius:0.2rem;letter-spacing:0.04em;">'
            f'{zone}</span>'
            f'<span style="color:{fg};font-weight:600;font-size:0.92rem;">'
            f'{physics}</span></div>'
        )

        # Corps 2-lignes : impact procédé + action
        impact_html = (
            f'<div style="color:{fg};opacity:0.85;font-size:0.78rem;'
            f'line-height:1.4;margin-bottom:0.25rem;">'
            f'<span style="color:#9CA3AF;font-weight:600;font-size:0.68rem;'
            f'letter-spacing:0.04em;text-transform:uppercase;margin-right:0.35rem;">'
            f'Impact</span>{impact}</div>'
            if impact else ""
        )
        action_html = (
            f'<div style="color:{fg};opacity:0.95;font-size:0.83rem;'
            f'line-height:1.5;">'
            f'<span style="color:{acc};font-weight:600;font-size:0.68rem;'
            f'letter-spacing:0.04em;text-transform:uppercase;margin-right:0.35rem;">'
            f'Action</span>{action}</div>'
        )
        ev_html = (
            f'<div style="text-align:right;color:#6B7280;font-size:0.7rem;'
            f'font-variant-numeric:tabular-nums;margin-top:0.3rem;">'
            f'{evidence}</div>'
            if evidence else ""
        )

        items.append(
            f'<div style="background:{bg};border-left:4px solid {acc};'
            f'border-radius:0.25rem;padding:0.55rem 0.85rem;margin-bottom:0.5rem;">'
            f'{header}{impact_html}{action_html}{ev_html}</div>'
        )
    return (
        '<div style="background:#0B0F14;border:1px solid #1F2937;'
        'border-radius:0.3rem;padding:0.55rem;">'
        + "".join(items) +
        '</div>'
    )


st.html(_build_recs_html(recs))
st.divider()

# ---------------------------------------------------------------------------
# Décision : combien d'éléments choisir ? (25 · 30 · 40)
#
# Règle métier portée par screw_render.recommend_element_count :
#   - taux de remplissage estimé (Fill Factor moyen)
#   - répartition convoyage / mélange dans la config courante
#   - objectif déduit (transport / mélange standard / dispersion poussée)
#   - paramètres procédé (rpm, débit feeder)
# Affichage en un seul st.html → pas d'instabilité React (même contrainte
# que la section Recommandations ci-dessus).
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.count"))
st.caption(t("profile.cap.count"))

count_rec = recommend_element_count(
    cfg, rpm, feed, dens,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    fill_factor_fn=fill_factor_average,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
    position_to_zone_fn=position_to_zone,
    zone_residence_fn=zone_residence_times,
)

# Confiance → couleur du badge (libellé visible, pas de chiffre) — i18n.
_CONF_STYLE: dict[str, tuple[str, str]] = {
    "high":   ("#10B981", t("profile.conf.high")),
    "medium": ("#3B82F6", t("profile.conf.medium")),
    "low":    ("#F59E0B", t("profile.conf.low")),
}


def _build_count_rec_html(cr, why_optimal_override: str = "") -> str:
    """Carte décisionnelle : décision → synthèse → raisons → warning → alts.

    `why_optimal_override` permet d'injecter la version enrichie (4e phrase de
    compromis issue de analyze_systemic). Vide → fallback sur cr.why_optimal.
    """
    suggested = cr.suggested
    conf_color, conf_label = _CONF_STYLE.get(cr.confidence, _CONF_STYLE["medium"])

    contributing = [c for c in cr.criteria if c.scores.get(suggested, 0) > 0]
    contributing.sort(key=lambda c: c.scores.get(suggested, 0), reverse=True)
    if not contributing:
        contributing = sorted(
            cr.criteria, key=lambda c: c.scores.get(suggested, 0), reverse=True,
        )
    top_criteria = contributing[:3]

    # Décision + synthèse
    tagline_value = getattr(cr, "tagline", "") or ""
    tagline_html = (
        f'<div style="color:#9CA3AF;font-size:0.9rem;line-height:1.3;'
        f'margin-top:0.3rem;">{tagline_value}</div>'
        if tagline_value else ""
    )
    why_optimal = why_optimal_override or getattr(cr, "why_optimal", "") or cr.rationale
    archetype_chip = ""
    archetype_str = getattr(cr, "archetype", "")
    regime_str = getattr(cr, "regime", "")
    if archetype_str or regime_str:
        archetype_chip = (
            f'<div style="margin-top:0.45rem;display:flex;gap:0.35rem;'
            f'flex-wrap:wrap;">'
            + (
                f'<span style="background:rgba(16,185,129,0.12);color:#bbf7d0;'
                f'border:1px solid #10B981;font-weight:600;font-size:0.7rem;'
                f'padding:0.1rem 0.45rem;border-radius:0.2rem;letter-spacing:0.04em;">'
                f'{archetype_str}</span>' if archetype_str else ""
            )
            + (
                f'<span style="background:rgba(59,130,246,0.12);color:#bfdbfe;'
                f'border:1px solid #3B82F6;font-weight:600;font-size:0.7rem;'
                f'padding:0.1rem 0.45rem;border-radius:0.2rem;letter-spacing:0.04em;">'
                f'{regime_str}</span>' if regime_str else ""
            )
            + "</div>"
        )

    hero = (
        f'<div style="background:#0B0F14;border:1px solid #10B981;'
        f'border-radius:0.3rem;padding:0.9rem 1.1rem;margin-bottom:0.9rem;">'
        f'<div style="display:flex;align-items:baseline;gap:0.55rem;'
        f'flex-wrap:wrap;">'
        f'<span style="font-size:3rem;font-weight:700;color:#10B981;'
        f'line-height:1;">{suggested}</span>'
        f'<span style="font-size:1.25rem;font-weight:600;color:#10B981;'
        f'line-height:1;">{t("profile.reco.elements_recommended")}</span>'
        f'</div>'
        f'{tagline_html}'
        f'{archetype_chip}'
        f'<div style="color:{conf_color};font-size:0.8rem;'
        f'margin-top:0.35rem;">{t("profile.reco.confidence")} {conf_label.lower()}</div>'
        f'<div style="color:#9CA3AF;font-size:0.7rem;font-weight:600;'
        f'letter-spacing:0.04em;text-transform:uppercase;margin-top:0.6rem;">'
        f'{t("profile.reco.why_optimal")}</div>'
        f'<div style="color:#D1D5DB;font-size:0.88rem;line-height:1.55;'
        f'margin-top:0.2rem;">{why_optimal}</div>'
        f'</div>'
    )

    # Raisons (3 max)
    reason_rows = "".join(
        f'<div style="display:flex;gap:0.5rem;padding:0.18rem 0;'
        f'font-size:0.86rem;color:#F9FAFB;">'
        f'<span style="color:#10B981;">•</span>'
        f'<span style="flex:1;">{c.summary}</span>'
        f'<span style="color:#6B7280;font-variant-numeric:tabular-nums;">'
        f'{c.measured}</span>'
        f'</div>'
        for c in top_criteria
    )
    reasons_block = (
        f'<div style="margin-bottom:0.8rem;">'
        f'<div style="color:#9CA3AF;font-size:0.78rem;font-weight:600;'
        f'margin-bottom:0.25rem;">{t("profile.reco.why_choice")}</div>'
        f'{reason_rows}'
        f'</div>'
    )

    # Warning (1 max)
    warning_html = ""
    if cr.risks:
        warning_html = (
            f'<div style="color:#F59E0B;font-size:0.85rem;line-height:1.45;'
            f'border-left:2px solid #F59E0B;padding:0.3rem 0.7rem;'
            f'margin-bottom:0.8rem;">⚠ {cr.risks[0]}</div>'
        )

    # Actions priorisées (1 main + 0-2 secondary + 1 option)
    # Format tolérant : accepte ActionStep ou string brut (rétrocompat).
    raw_steps = getattr(cr, "action_steps", ()) or ()
    grouped: dict[str, list[str]] = {"main": [], "secondary": [], "option": []}
    for step in raw_steps:
        prio = getattr(step, "priority", "main")
        body = getattr(step, "body", str(step))
        if prio not in grouped:
            prio = "main"
        grouped[prio].append(body)

    def _render_section(label: str, items: list[str], accent: str) -> str:
        if not items:
            return ""
        rows = "".join(
            f'<div style="display:flex;gap:0.55rem;padding:0.18rem 0;'
            f'font-size:0.86rem;color:#F9FAFB;line-height:1.5;">'
            f'<span style="color:{accent};font-weight:600;'
            f'min-width:0.9rem;">→</span>'
            f'<span style="flex:1;">{body}</span>'
            f'</div>'
            for body in items
        )
        return (
            f'<div style="margin-bottom:0.45rem;">'
            f'<div style="color:{accent};font-size:0.72rem;font-weight:600;'
            f'letter-spacing:0.04em;text-transform:uppercase;'
            f'margin-bottom:0.15rem;">{label}</div>'
            f'{rows}'
            f'</div>'
        )

    actions_block = ""
    if any(grouped.values()):
        sections_html = (
            _render_section(t("profile.reco.section.main"), grouped["main"], "#10B981")
            + _render_section(
                t("profile.reco.section.secondary"), grouped["secondary"], "#3B82F6"
            )
            + _render_section(t("profile.reco.section.option"), grouped["option"], "#9CA3AF")
        )
        actions_block = (
            f'<div style="background:rgba(16,185,129,0.04);'
            f'border-left:2px solid #10B981;'
            f'padding:0.55rem 0.8rem 0.4rem;margin-bottom:0.8rem;'
            f'border-radius:0 0.2rem 0.2rem 0;">'
            f'<div style="color:#10B981;font-size:0.78rem;font-weight:600;'
            f'margin-bottom:0.45rem;letter-spacing:0.02em;">'
            f'{t("profile.reco.do_now")}</div>'
            f'{sections_html}'
            f'</div>'
        )

    # Alternatives
    alt_rows = "".join(
        f'<div style="display:flex;gap:0.6rem;padding:0.18rem 0;'
        f'font-size:0.82rem;color:#9CA3AF;">'
        f'<span style="color:#D1D5DB;font-weight:600;min-width:28px;'
        f'font-variant-numeric:tabular-nums;">{a.count}</span>'
        f'<span style="color:#D1D5DB;">{a.summary}</span>'
        f'<span style="flex:1;">— {a.sentence}</span>'
        f'</div>'
        for a in cr.alternatives[:2]
    )
    alts_block = (
        f'<div style="border-top:1px solid #1F2937;padding-top:0.55rem;">'
        f'<div style="color:#9CA3AF;font-size:0.78rem;font-weight:600;'
        f'margin-bottom:0.25rem;">{t("profile.reco.adjust")}</div>'
        f'{alt_rows}'
        f'</div>'
    )

    return hero + reasons_block + actions_block + warning_html + alts_block


# Couche systémique calculée AVANT le rendu de la carte décisionnelle :
# son champ why_optimal_enriched (4e phrase « compromis assumé ») est injecté
# dans l'encart « POURQUOI CE CHOIX EST OPTIMAL ». Le rendu visuel du bloc
# systémique reste plus bas (section dédiée).
systemic = analyze_systemic(
    cfg, rpm, feed, dens,
    base_type_fn=base_type,
    is_part2_fn=is_part2,
    position_to_zone_fn=position_to_zone,
    fill_factor_fn=fill_factor_average,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
    profile_reading=profile_reading,
    count_rec=count_rec,
    recs=recs,
    zone_residence_fn=zone_residence_times,
    tip_constraint_fn=enforce_tip_constraint,
)

# Bloc DÉCISION AGENT en header au-dessus des cartes :
# en premier la lecture opérateur 3-lignes (3 secondes), puis la version
# technique (action prioritaire + badge confiance + prochaine étape).
st.html(build_decision_summary_html(systemic))
st.html(build_decision_html(systemic))

st.html(_build_count_rec_html(
    count_rec,
    why_optimal_override=getattr(systemic, "why_optimal_enriched", ""),
))

st.divider()

# ---------------------------------------------------------------------------
# Raisonnement global procédé — couche systémique (analyze_systemic).
# `systemic` est déjà calculé plus haut (pour alimenter why_optimal_enriched)
# — on ne fait ici que l'afficher.
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.systemic"))
st.caption(t("profile.cap.systemic"))
st.html(build_systemic_html(systemic))

st.divider()

# ---------------------------------------------------------------------------
# Résidence par zone
# ---------------------------------------------------------------------------
st.markdown("##### " + t("profile.sec.residence"))
zrt = zone_residence_times(cfg, rpm, feed, dens)
zone_names = ["Feed", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]

fig_zones = go.Figure()
fig_zones.add_trace(go.Bar(
    x=zone_names,
    y=zrt,
    marker_color="#06B6D4",
    hovertemplate="%{x}<br>" + t("profile.chart.residence_axis") + ": %{y:.2f} s<extra></extra>",
))
fig_zones.update_layout(
    paper_bgcolor=BG_CARD, plot_bgcolor=BG_CARD,
    height=220, margin=dict(l=0, r=0, t=5, b=0),
    xaxis=dict(showgrid=False, color="#9CA3AF", tickfont=dict(size=11)),
    yaxis=dict(showgrid=True, gridcolor="#1F2937", color="#9CA3AF",
               title=dict(text=t("profile.chart.residence_axis"), font=dict(color="#9CA3AF"))),
    hoverlabel=dict(bgcolor="#1F2937", font_color="#F9FAFB"),
)
st.plotly_chart(fig_zones, use_container_width=True, key="zone_rt_chart")

st.caption(t("profile.cap.residence", rpm=f"{rpm:.0f}", feed=f"{feed:.1f}",
              dens=f"{dens:.2f}", maxv=f"{TOTAL_FREE_VOL:.2f}"))

# ─── Save button — commit screw profile to the applied snapshot ──────────────
# The applied snapshot is the ONLY source consumed by Supervision and the AI
# Agent. Without this commit, Profile changes to screw_config are invisible to
# all other pages. The commit preserves all Settings data (feeders, zone temps,
# RPM) — only screw_config is updated from the live session.
st.divider()
# Transparence persistance : avertissement explicite si seul le fallback JSON
# local (disque éphémère en cloud) est disponible.
try:
    from persistence import is_durable as _persist_is_durable  # noqa: PLC0415
    if not _persist_is_durable():
        st.warning(t("persist.warning"), icon="⚠️")
except Exception:  # noqa: BLE001
    pass
if st.button(
    t("profile.btn.save"),
    type="primary", use_container_width=False, key="btn_profile_save",
    help=t("profile.save.help"),
):
    try:
        _prev_snap = applied_get(st.session_state)
        _prev_label = _prev_snap.label if _prev_snap else ""
        _pstate = state_from_session(st.session_state)
        # Lecture proxy-safe (st.session_state.get n'est pas garanti en prod).
        if "screw_config" in st.session_state:
            _pstate.screw_config = list(st.session_state["screw_config"])
        refresh_kpis(_pstate)
        applied_commit(st.session_state, _pstate, label=_prev_label)
        st.toast(t("profile.toast.saved"), icon="✅")
    except Exception as _exc:  # noqa: BLE001 — JAMAIS d'échec silencieux (exigence manager)
        st.error(t("profile.save.error", err=_exc))

# ─── P3.2 : formaliser le flux à sens unique current_run_state → clés legacy ──
try:
    sync_legacy_projection(st.session_state)
except Exception:  # noqa: BLE001
    pass

try:
    capture_operator_state(st.session_state)
except Exception:  # noqa: BLE001
    pass
