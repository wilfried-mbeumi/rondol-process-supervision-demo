"""
5_Process_Engine.py — Moteur Procédé (couche engine : graph + couple + SME).

Page READ-ONLY : elle lit les paramètres déjà saisis (profil vis, vitesse,
feeder, densité, side feeder) depuis `session_state` — partagés avec Profile /
Settings — construit un `EngineReport` PUR via `engine.app_report`, puis affiche :
  - KPIs principaux (couple total, SME totale, résidence, remplissage, cisaillement) ;
  - état machine / graph ;
  - couple local par position ;
  - agrégats par zone ;
  - statut E6 (T_real) / E7 (pression) = « À venir / non calculé » ;
  - encart hypothèses (valeurs nominales, modèle non calibré, prototype).

Aucune équation n'est calculée ici : tout vient du builder pur. La page ne MODIFIE
rien (lecture seule de session_state, juste des `setdefault` défensifs comme les
autres pages).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP = Path(__file__).resolve().parent.parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from screw_logic import (  # noqa: E402
    add_elements_atomic,
    count_user_elements,
    new_empty_configuration,
)
from engine.report_params import (  # noqa: E402
    NOMINAL_SIDE_FEEDER_G_PER_MIN,
    NOMINAL_TEMP_PROFILE_C,
    build_report_from_flat_params,
)
from app_mode import (  # noqa: E402
    NOT_PROVIDED,
    demo_badge_html,
    demo_mode_toggle,
    material_label,
)
# i18n FR/EN (stabilisation globale 2026-06-10) — uniquement pour le libellé
# « Non renseigné » : en anglais, l'écran doit afficher « Not entered ».
# Modification STRICTEMENT textuelle (aucune logique moteur touchée).
from rondol_i18n import language_selector as _language_selector, t as _t  # noqa: E402


def _material_label_i18n(name, demo_mode_flag):
    """material_label + traduction du libellé « Non renseigné » selon la langue."""
    lbl = material_label(name, demo_mode_flag)
    return _t("historique.comp_not_entered") if lbl == NOT_PROVIDED else lbl
from calc_audit import (  # noqa: E402
    MACHINE_MAX_CAPACITY_KEY,
    fill_factor_validation_status,
    flow_taxonomy_rows,
    formula_status_label,
)
from screw_logic import (  # noqa: E402
    MAIN_FEEDER_POSITION as _MAIN_POS,
    _params_from_hmi,
    compute_process_state as _compute_ps,
    free_volume as _free_volume,
)
from AgentIndustrial_v1.core.coercion import safe_float  # noqa: E402
# P3.3 : Moteur Procédé lit la source de vérité current_run_state (jamais les
# clés legacy plates directement).
from run_state_adapter import (  # noqa: E402
    build as build_crs,
    build_moteur_inputs_from_current_run_state,
)
from operator_store import restore_operator_state  # noqa: E402

st.set_page_config(page_title=_t("moteur.page_title"), layout="wide")

# ---------------------------------------------------------------------------
# CSS global (cohérent avec les autres pages — bloc statique immuable)
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

/* ── Premium light (présentation client) — additif, aucun impact fonctionnel ── */
/* En-têtes de section : filet vert Rondol + libellé hiérarchisé */
.mp-sec{display:flex;align-items:center;gap:.55rem;margin:.55rem 0 .4rem;font-size:.72rem;
  font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#9CA3AF;}
.mp-sec .bar{width:3px;height:15px;background:#4CAF50;border-radius:2px;flex:0 0 auto;}
.mp-sec .sub{font-weight:500;letter-spacing:.01em;text-transform:none;color:#6B7280;}
/* Badges d'état (remplissage / prototype / à venir) */
.mp-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.26rem .7rem;border-radius:999px;
  font-size:.82rem;font-weight:600;border:1px solid;line-height:1;white-space:nowrap;}
.mp-badge.ok{color:#4ADE80;background:rgba(74,222,128,.10);border-color:rgba(74,222,128,.35);}
.mp-badge.warn{color:#FBBF24;background:rgba(251,191,36,.10);border-color:rgba(251,191,36,.35);}
.mp-badge.crit{color:#F87171;background:rgba(248,113,113,.10);border-color:rgba(248,113,113,.35);}
.mp-badge.neutral{color:#9CA3AF;background:rgba(156,163,175,.08);border-color:rgba(156,163,175,.30);}
/* Bandeau prototype compact */
.mp-proto{display:flex;align-items:center;gap:.7rem;background:rgba(251,191,36,.06);
  border:1px solid rgba(251,191,36,.28);border-radius:.5rem;padding:.55rem .8rem;
  color:#CBD5E1;font-size:.86rem;margin:.15rem 0 .2rem;}
.mp-proto b{color:#E5E7EB;}
/* Chips inline (état machine) */
.mp-chips{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.7rem;}
.mp-chip{font-size:.78rem;color:#9CA3AF;background:#11181F;border:1px solid #1F2937;
  border-radius:.45rem;padding:.22rem .6rem;}
.mp-chip b{color:#E5E7EB;font-weight:600;}
.mp-chip.warn{color:#FBBF24;border-color:rgba(251,191,36,.4);}
.mp-chip.warn b{color:#FBBF24;}
/* Cartes "équations à venir" */
.mp-defer{background:#0E141B;border:1px solid #1F2937;border-radius:.6rem;padding:.85rem 1rem;height:100%;}
.mp-defer h4{margin:0 0 .45rem;font-size:.92rem;color:#E5E7EB;display:flex;align-items:center;
  gap:.5rem;flex-wrap:wrap;}
.mp-defer p{margin:.32rem 0 0;font-size:.82rem;color:#9CA3AF;line-height:1.45;}
.mp-defer code{background:#1F2937;color:#D1D5DB;padding:.05rem .3rem;border-radius:.25rem;font-size:.78rem;}
/* Conteneurs bordés Streamlit → cartes sombres premium */
[data-testid="stVerticalBlockBorderWrapper"]{background:#0E141B;border-radius:.65rem;}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#1F2937!important;border-radius:.65rem;}
/* Valeurs KPI : taille resserrée pour éviter la troncature (ex. « kWh/kg ») */
[data-testid="stMetricValue"]{font-size:1.55rem;}
[data-testid="stMetricValue"]>div{overflow:visible;}
</style>
""")

_language_selector()

RONDOL_GREEN = "#4CAF50"
ACC = "#4ADE80"   # vert (confirmé)
WARN = "#FBBF24"  # ambre (avec hypothèses)
CRIT = "#F87171"  # rouge (non validé)


# ---------------------------------------------------------------------------
# Helpers de PRÉSENTATION (rendu only — aucune donnée ni calcul ici)
# ---------------------------------------------------------------------------
def _section(title: str, subtitle: str = "") -> None:
    """En-tête de section : filet vert Rondol + libellé (+ sous-titre optionnel)."""
    sub = f'<span class="sub">· {subtitle}</span>' if subtitle else ""
    st.html(f'<div class="mp-sec"><span class="bar"></span>{title}{sub}</div>')


def _badge(text: str, kind: str = "neutral") -> str:
    """Pastille d'état colorée (kind ∈ ok|warn|crit|neutral). Retourne du HTML."""
    return f'<span class="mp-badge {kind}">{text}</span>'


def _chip(label: str, value: str, warn: bool = False) -> str:
    """Chip inline « libellé : valeur » (optionnellement en alerte). HTML."""
    cls = "mp-chip warn" if warn else "mp-chip"
    return f'<span class="{cls}">{label} <b>{value}</b></span>'


# (badge kind now returned directly by _fill_assessment — no dict needed)

# ---------------------------------------------------------------------------
# Hypothèses NOMINALES (documentées, non calibrées) — profil thermique + débit
# side feeder. Désormais définies UNE seule fois dans `engine.report_params`
# (importées ci-dessus) pour garantir des KPIs identiques entre cette page et le
# figement de l'historique procédé. Valeurs inchangées.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lecture session_state (read-only + setdefault défensifs, comme les autres pages)
# ---------------------------------------------------------------------------
def _default_config() -> list[int]:
    """Profil de démonstration minimal si l'utilisateur n'a pas visité Profile.

    Convoyage → malaxages → convoyage (tip déjà placé par new_empty_configuration).
    """
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)   # convoyage avant
    add_elements_atomic(cfg, 4, 2)   # malaxage 90°
    add_elements_atomic(cfg, 7, 2)   # malaxage 60°
    add_elements_atomic(cfg, 1, 5)   # convoyage
    return cfg


# PRIORITÉ SNAPSHOT : hydrate la session depuis le snapshot validé (profil vis +
# étalonnage feeder) AVANT le store opérateur — le moteur lit le même état
# sauvegardé que Profile/Supervision après un refresh navigateur.
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402
    hydrate_session_from_applied,
    migrate_and_restore,
)
# Migration/réparation déterministe AVANT tout : un snapshot durable dégénéré
# (ancien build) est réparé + réécrit dans Supabase avant hydratation.
migrate_and_restore(st.session_state)
hydrate_session_from_applied(st.session_state)
# Restaure la config opérateur centrale (store/disque) AVANT toute lecture —
# survie navigation Profile→Moteur + refresh navigateur.
restore_operator_state(st.session_state)

# Flag PAGE-LOCAL (préfixe mp_) : ne touche PAS l'état partagé screw_config.
st.session_state.setdefault("mp_demo_profile", False)

# ── Mode démonstration : contrôle UI (le toggle écrit la clé session) ────────
with st.sidebar:
    demo_mode_toggle(st)

# ===========================================================================
# SOURCE DE VÉRITÉ UNIQUE — current_run_state (P3.3)
# ===========================================================================
# La page NE lit plus AUCUNE valeur métier directement depuis st.session_state
# brut ni depuis les clés legacy plates. Tout vient d'un CurrentRunState validé,
# puis des paramètres plats DÉRIVÉS (adapter), consommés par le moteur enveloppé.
_crs = build_crs(st.session_state)
_mi = build_moteur_inputs_from_current_run_state(_crs)

shared_config: list[int] = _mi["config"]
screw_rpm = _mi["screw_rpm"]
bulk_density = _mi["bulk_density"]
side_feeder_zone = _mi["side_feeder_zone"]
feeder_flow = _mi["feeder_flow"]
feed_g_per_min = _mi["feed_g_per_min"]      # 0.0 si débit réel non calculable
feed_available = _mi["feed_available"]
demo_mode = _mi["demo_mode"]

# État dérivé : profil procédé vide (tip exclu) ? démo page-local active ?
profile_empty = count_user_elements(shared_config) == 0.0
demo_active = bool(st.session_state["mp_demo_profile"]) and profile_empty


def _build_report(config: list[int]):
    """Construit le rapport moteur PUR à partir de la config choisie.

    Délègue au helper PARTAGÉ `engine.report_params.build_report_from_flat_params`
    (source unique de la construction params + powders nominales). Comportement et
    valeurs strictement identiques à l'ancienne construction locale. La pile reste :
    build_engine_report → build_graph → enrich_graph → aggregate_machine.
    """
    return build_report_from_flat_params(
        config=config,
        screw_rpm=screw_rpm,
        feed_g_per_min=feed_g_per_min,
        bulk_density=bulk_density,
        side_feeder_zone=side_feeder_zone,
    )


def _fill_assessment(report) -> tuple[str, str, str, str]:
    """Évaluation INDICATIVE du remplissage — pure LECTURE du fill_factor déjà
    calculé (aucune nouvelle équation). Retourne (libellé, sévérité, message, badge_kind).
    """
    avg = report.fill_factor_average
    overflow = report.overflow_main_feeder or report.overflow_side_feeder
    if overflow:
        return (_t("moteur.fill.overflow"), "warning", _t("moteur.fill.overflow_msg"), "crit")
    if avg >= 0.75:
        return (_t("moteur.fill.high"), "warning", _t("moteur.fill.high_msg"), "warn")
    if avg >= 0.30:
        return (_t("moteur.fill.nominal"), "info", _t("moteur.fill.nominal_msg"), "ok")
    return (_t("moteur.fill.low"), "info", _t("moteur.fill.low_msg"), "neutral")


# ===========================================================================
#  RENDU
# ===========================================================================
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>{_t("moteur.banner.left")}</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">{_t("moteur.banner.right")}</span>'
    f'</div>'
)

st.markdown(f"## {_t('moteur.header')}")
st.caption(_t("moteur.caption"))

# ── État vide explicite : aucun profil procédé chargé ────────────────────────
# Exigence manager : ne JAMAIS afficher des KPIs à 0 sans explication, ni charger
# un profil par défaut en silence. On affiche un message clair + un bouton de
# démonstration explicite, puis on stoppe le rendu (pas de KPIs trompeurs).
if profile_empty and not demo_active:
    st.info(_t("moteur.no_profile.info"), icon="ℹ️")
    if st.button(_t("moteur.no_profile.btn"), type="primary", use_container_width=False):
        st.session_state["mp_demo_profile"] = True
        st.rerun()
    st.caption(_t("moteur.no_profile.footer"))
    st.stop()

# Choix de la config rendue : démo page-local si demandée ET profil partagé vide,
# sinon le profil partagé réel. L'état partagé n'est JAMAIS modifié ici.
config: list[int] = _default_config() if demo_active else shared_config
report = _build_report(config)

# ── Bandeau profil de démonstration (uniquement en mode démo) ────────────────
if demo_active:
    dcol1, dcol2 = st.columns([4, 1])
    with dcol1:
        st.warning(_t("moteur.demo.warning"), icon="⚙️")
    with dcol2:
        if st.button(_t("moteur.demo.unload"), use_container_width=True):
            st.session_state["mp_demo_profile"] = False
            st.rerun()

# ── Bandeau prototype (toujours visible) ─────────────────────────────────────
st.html(
    '<div class="mp-proto">'
    + _badge("⚠ Prototype", "warn")
    + f"<span>{_t('moteur.proto.banner')}</span>"
    + "</div>"
)

# ── Avertissement : débit NON calculable si feeder non étalonné ──────────────
# Exigence manager : ne JAMAIS présenter « 0 » comme une vérité procédé quand le
# coefficient d'étalonnage feeder est absent. Les indicateurs dépendant du débit
# affichent « Non calculable » (aucun débit par défaut inventé).
if not feed_available:
    st.warning(_t("moteur.flow_warning"), icon="⚠️")


def _nc(s: str) -> str:
    """Valeur affichée si le débit est calculable, sinon « Non calculable ».

    Empêche d'afficher un « 0 » trompeur comme vérité procédé quand le feeder
    n'est pas étalonné (le débit réel est inconnu, pas nul).
    """
    return s if feed_available else _t("common.not_computable")


# ── KPIs principaux (carte) ──────────────────────────────────────────────────
_section(_t("moteur.sec.kpis"), _t("moteur.sec.kpis_sub"))
with st.container(border=True):
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        _t("moteur.kpi.torque"), _nc(f"{report.total_torque_nm:.3f} N·m"),
        help=_t("moteur.kpi.torque_help"),
    )
    k2.metric(
        _t("moteur.kpi.sme"), _nc(f"{report.total_sme_kwh_per_kg:.3f} kWh/kg"),
        help=_t("moteur.kpi.sme_help"),
    )
    k3.metric(
        _t("moteur.kpi.residence"), _nc(f"{report.residence_time_total_s:.1f} s"),
        help=_t("moteur.kpi.residence_help"),
    )
    k4.metric(
        _t("moteur.kpi.fill"), _nc(f"{report.fill_factor_average * 100:.0f} %"),
        help=_t("moteur.kpi.fill_help"),
    )
    k5.metric(
        _t("moteur.kpi.shear"), f"{report.max_shear_rate_s:.0f} s⁻¹",
        help=_t("moteur.kpi.shear_help"),
    )

# ── État machine / graph (carte + chips) ─────────────────────────────────────
_section(_t("moteur.sec.machine"))
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(_t("moteur.kpi.power"), _nc(f"{report.total_power_w:.1f} W"))
    m2.metric(_t("moteur.kpi.mass_flow"), _nc(f"{report.mass_flow_kg_per_h:.2f} kg/h"))
    m3.metric(_t("moteur.kpi.output_flow"), _nc(f"{report.output_vol_flow_cm3_s:.2f} cm³/s"))
    m4.metric(
        _t("moteur.kpi.peak_fill"),
        _nc(f"{report.peak_fill_factor * 100:.0f} %"),
        (f"position #{report.peak_fill_position:02d}" if feed_available else None),
    )
    _chips = [
        _chip(_t("moteur.chip.screw_speed"), f"{report.screw_rpm:.0f} {_t('moteur.chip.rpm_unit')}"),
        _chip(_t("moteur.chip.overflow_main"),
              _t("common.yes") if report.overflow_main_feeder else _t("common.no"),
              warn=report.overflow_main_feeder),
        _chip(_t("moteur.chip.overflow_side"),
              _t("common.yes") if report.overflow_side_feeder else _t("common.no"),
              warn=report.overflow_side_feeder),
        # Matière : « Non renseigné » en mode client (aucune saisie matière
        # réelle n'existe encore) ; nom chimique nominal + badge DEMO en démo.
        _chip("Feeder 1",
              f"{_material_label_i18n(report.feeder1_material, demo_mode)} {demo_badge_html()}"
              if demo_mode else _material_label_i18n(report.feeder1_material, demo_mode)),
    ]
    if demo_mode and report.feeder2_material:
        _chips.append(_chip("Feeder 2", f"{report.feeder2_material} {demo_badge_html()}"))
    st.html(f'<div class="mp-chips">{"".join(_chips)}</div>')

# ── Évaluation indicative du remplissage (lecture du fill_factor, FR-11) ──────
# AUCUNE nouvelle équation : simple interprétation par paliers du fill_factor
# déjà calculé par la couche moteur. Wording volontairement prudent.
_section(_t("moteur.sec.fill_eval"), _t("moteur.sec.fill_eval_sub"))
if not feed_available:
    st.info(_t("moteur.fill.not_computable"), icon="ℹ️")
else:
    _fill_label, _fill_sev, _fill_msg, _fill_bk = _fill_assessment(report)
    st.html(_badge(f"● {_fill_label}", _fill_bk))
    _banner = st.warning if _fill_sev == "warning" else st.info
    _banner(
        f"**{_fill_label}** — {_fill_msg}\n\n"
        + _t("moteur.fill.eval_footer",
             avg=f"{report.fill_factor_average * 100:.0f}",
             peak=f"{report.peak_fill_factor * 100:.0f}"),
        icon="🟢" if _fill_sev == "info" else "🟠",
    )

# ── Statut équations différées E6 / E7 (cartes + badge « À venir ») ───────────
_section(_t("moteur.sec.equations"), _t("moteur.sec.equations_sub"))
e1, e2 = st.columns(2)
with e1:
    st.html(
        '<div class="mp-defer">'
        f'<h4>{_t("moteur.eq.e6_title")} {_badge(_t("moteur.upcoming"), "neutral")}</h4>'
        f'<p>{_t("moteur.eq.e6_body")}</p>'
        f'<p><b style="color:#CBD5E1;">{_t("moteur.eq.status")}</b> {_t("moteur.eq.status_na")}</p>'
        '</div>'
    )
with e2:
    st.html(
        '<div class="mp-defer">'
        f'<h4>{_t("moteur.eq.e7_title")} {_badge(_t("moteur.upcoming"), "neutral")}</h4>'
        f'<p>{_t("moteur.eq.e7_body")}</p>'
        f'<p><b style="color:#CBD5E1;">{_t("moteur.eq.status")}</b> {_t("moteur.eq.status_na")}</p>'
        '</div>'
    )

# ── Agrégats par zone ────────────────────────────────────────────────────────
_section(_t("moteur.sec.zones"), "Feed + Z1..Z8")
_zone_labels = ["Feed", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
_zone_rows = []
for z in report.zones:
    label = _zone_labels[z.zone] if 0 <= z.zone < len(_zone_labels) else f"Z{z.zone}"
    _zone_rows.append({
        _t("moteur.col.zone"): label,
        _t("moteur.col.positions"): z.n_nodes,
        _t("moteur.col.fill_mean"): z.mean_fill_factor * 100.0,
        _t("moteur.col.fill_peak"): z.max_fill_factor * 100.0,
        _t("moteur.col.shear_mean"): z.mean_shear_rate_s,
        _t("moteur.col.shear_max"): z.max_shear_rate_s,
        _t("moteur.col.t_max"): z.max_temperature_c,
        _t("moteur.col.material"): _material_label_i18n(z.dominant_material, demo_mode),
        _t("moteur.col.residence"): z.residence_time_s,
    })
st.dataframe(
    pd.DataFrame(_zone_rows), use_container_width=True, hide_index=True,
    column_config={
        _t("moteur.col.positions"): st.column_config.NumberColumn(_t("moteur.col.positions"), format="%d"),
        _t("moteur.col.fill_mean"): st.column_config.ProgressColumn(
            _t("moteur.col.fill_mean"), min_value=0, max_value=100, format="%.0f%%"),
        _t("moteur.col.fill_peak"): st.column_config.ProgressColumn(
            _t("moteur.col.fill_peak"), min_value=0, max_value=100, format="%.0f%%"),
        _t("moteur.col.shear_mean"): st.column_config.NumberColumn(_t("moteur.col.shear_mean") + " (s⁻¹)", format="%.0f"),
        _t("moteur.col.shear_max"): st.column_config.NumberColumn(_t("moteur.col.shear_max") + " (s⁻¹)", format="%.0f"),
        _t("moteur.col.t_max"): st.column_config.NumberColumn(_t("moteur.col.t_max_label"), format="%.0f"),
        _t("moteur.col.residence"): st.column_config.NumberColumn(_t("moteur.col.residence_label"), format="%.1f"),
    },
)

# ── Détail par position ──────────────────────────────────────────────────────
_section(_t("moteur.sec.positions"), "0..80")
_hide_empty = st.checkbox(_t("moteur.chk.hide_empty"), value=True)
_pos_rows = []
for p in report.positions:
    if _hide_empty and p.is_empty:
        continue
    _pos_rows.append({
        "Pos.": p.position,
        _t("moteur.col.zone"): _zone_labels[p.zone] if 0 <= p.zone < len(_zone_labels) else str(p.zone),
        _t("moteur.col.element"): p.element_label,
        "Port": p.port_kind or "—",
        _t("moteur.col.fill"): p.fill_factor * 100.0,
        "γ̇": p.shear_rate_s,
        _t("moteur.col.torque_local"): p.torque_nm,
    })
if _pos_rows:
    st.dataframe(
        pd.DataFrame(_pos_rows), use_container_width=True, hide_index=True, height=380,
        column_config={
            "Pos.": st.column_config.NumberColumn("Pos.", format="%d"),
            _t("moteur.col.fill"): st.column_config.ProgressColumn(
                _t("moteur.col.fill"), min_value=0, max_value=100, format="%.0f%%"),
            "γ̇": st.column_config.NumberColumn("γ̇ (s⁻¹)", format="%.0f"),
            _t("moteur.col.torque_local"): st.column_config.NumberColumn(
                _t("moteur.col.torque_local_label"), format="%.4f"),
        },
    )
else:
    st.caption(_t("moteur.no_positions"))

# ── Audit calcul procédé (transparence entrée → sortie, provenance + statut) ──
# Exigence manager : MONTRER chaque variable machine, son unité, sa source, sa
# formule et son STATUT (validé PLC / correction manager / à valider). Formules
# vérifiées sur la source PLC Rondol (references/logique_metier/2-CALCULS.pdf,
# Network 7). Aucune valeur sans provenance.
_section(_t("moteur.sec.audit"), _t("moteur.sec.audit_sub"))
with st.container(border=True):
    # ProcessState dédié à l'audit (mêmes paramètres plats que la chaîne) — sert
    # à exposer capacité et FF AU MAIN FEEDER (point déterminant, pédagogique).
    _ps_audit = _compute_ps(shared_config, _params_from_hmi(screw_rpm, feed_g_per_min, bulk_density))
    _n_rps = screw_rpm / 60.0
    _v_byrev_main = _ps_audit.local_free_volume_by_rev[_MAIN_POS]
    _cap_main = _n_rps * _v_byrev_main
    _ff_main = _ps_audit.fill_factor_local[_MAIN_POS]
    _qvol = (feed_g_per_min / 60.0) / bulk_density if bulk_density > 0 else 0.0
    _free_vol_2screws = _free_volume(shared_config)
    # Compteur visible tip inclus (capacité totale 40) — cohérent Profile/Settings.
    from screw_logic import count_total_elements as _count_total  # noqa: PLC0415
    _n_elem = _count_total(shared_config)
    _rpm_full = screw_rpm * _ff_main if _ff_main > 0 else 0.0  # rpm où FF≈100 %

    # Statuts honnêtes : la chaîne FF (capacité, V_libre/tour, FF) dépend de
    # valeurs DB automate non confirmées ET de la correction manager ×2 → on
    # n'écrit PAS « validé PLC » sur ces lignes.
    _PLC = _t("calc.formula.plc_validated")
    _PLC_ASSUM = formula_status_label()
    _PLC_DB = _t("moteur.audit.status.pdb")
    _MGR = _t("moteur.audit.status.mgr")
    _MGR_LIM = _t("moteur.audit.status.mgr_lim")
    _IN = _t("moteur.audit.status.input")
    _CALC = _t("moteur.audit.status.calc")
    _ff_status = fill_factor_validation_status(feed_known=feeder_flow.calibrated)

    if feeder_flow.calibrated:
        _dem = f"{feeder_flow.requested_g_h:.1f}"
        _eff_gh = f"{feeder_flow.effective_g_h:.1f}"
        _eff_gmin = f"{feeder_flow.effective_g_min:.3f}"
        _eff_gs = f"{feeder_flow.effective_g_s:.5f}"
        _coeff = f"{feeder_flow.calibration_g_h_per_rpm:.3f}"
        _coeff_src, _coeff_stat = "USER_INPUT", _t("moteur.audit.status.calib_ext")
    else:
        _dem = _eff_gh = _eff_gmin = _eff_gs = _t("common.not_computable")
        _coeff = _t("common.not_entered")
        _coeff_src, _coeff_stat = "NOT_AVAILABLE", _t("moteur.audit.status.calib_req")

    _rows = [
        (_t("moteur.audit.row.rpm_feeder"), f"{feeder_flow.feeder_rpm:.0f}", "RPM", "USER_INPUT", "—", _IN),
        (_t("moteur.audit.row.calib_coeff"), _coeff, "g/h/RPM", _coeff_src, "= Mass_flow_rate (PLC L0018)", _coeff_stat),
        (_t("moteur.audit.row.flow_requested"), _dem, "g/h", "CALCULATED", "RPM × coeff", _CALC),
        (_t("moteur.audit.row.flow_max"), f"{feeder_flow.max_machine_g_h:.0f}", "g/h", "DEFAULT_CONFIG", "—", _MGR_LIM),
        (_t("moteur.audit.row.flow_effective"), _eff_gh, "g/h", "CALCULATED", "min(demandé, max)", _CALC),
        (_t("moteur.audit.row.flow_eff_gmin"), _eff_gmin, "g/min", "CALCULATED", "g/h ÷ 60", _CALC),
        (_t("moteur.audit.row.flow_eff_gmin"), _eff_gs, "g/s", "CALCULATED", "g/h ÷ 3600", _CALC),
        (_t("moteur.audit.row.density"), f"{bulk_density:.3f}", "g/cm³", "USER_INPUT", "—", _IN),
        (_t("moteur.audit.row.vol_flow"), f"{_qvol:.4f}", "cm³/s", "CALCULATED", "ṁ ÷ ρ (PLC L0056)", _PLC),
        (_t("moteur.audit.row.rpm_screw"), f"{screw_rpm:.0f}", _t("moteur.chip.rpm_unit"), "USER_INPUT", "—", _IN),
        (_t("moteur.audit.row.n_screw"), f"{_n_rps:.3f}", "tr/s", "CALCULATED", "rpm ÷ 60 (PLC L0015)", _PLC),
        (_t("moteur.audit.row.vol_per_rev"), f"{_v_byrev_main:.4f}", "cm³/tour", "CALCULATED",
         "V_libre × Factor_FreeByRev (PLC L0033)", _PLC_DB),
        (_t("moteur.audit.row.vol_cap"), f"{_cap_main:.4f}", "cm³/s", "CALCULATED",
         "N × V_libre/tour (PLC L0057)", _PLC_ASSUM),
        (_t("moteur.audit.row.free_vol"), f"{_free_vol_2screws:.2f}", "cm³", "CALCULATED",
         "76.1756 − 2×occupé/vis", _MGR),
        (_t("moteur.audit.row.n_elements"), f"{_n_elem:.0f}", "—", "USER_INPUT", "—", _IN),
        ("Fill factor (main)", f"{_ff_main * 100:.1f}", "%", "CALCULATED",
         "Q_vol ÷ capacité (PLC L0060)", _PLC_ASSUM),
        (_t("moteur.audit.row.ff_mean"), f"{report.fill_factor_average * 100:.1f}", "%", "CALCULATED",
         "moyenne FF (PLC L0153)", _PLC_ASSUM),
        (_t("moteur.audit.row.residence"), f"{report.residence_time_total_s:.1f}", "s", "CALCULATED",
         "Σ V_libre/VolFlow (PLC L0144)", _PLC_ASSUM),
    ]
    st.dataframe(
        pd.DataFrame(_rows, columns=[
            _t("moteur.audit.col.variable"), _t("moteur.audit.col.value"),
            _t("moteur.audit.col.unit"), _t("moteur.audit.col.source"),
            _t("moteur.audit.col.formula"), _t("moteur.audit.col.status")]),
        use_container_width=True, hide_index=True,
    )

    # Statut HONNÊTE du résultat FF + clarification du périmètre du débit.
    _status_color = {"CALCULATED_CONFIRMED": ACC,
                     "CALCULATED_WITH_ASSUMPTIONS": WARN,
                     "NOT_VALIDATED": CRIT}.get(_ff_status, WARN)
    st.html(
        f'<div style="background:rgba(251,191,36,.08);border:1px solid {_status_color};'
        f'border-radius:.4rem;padding:.4rem .7rem;margin:.3rem 0;font-size:.84rem;color:#E5E7EB;">'
        f'<b style="color:{_status_color};">{_t("moteur.audit.ff_status", status=_ff_status)}</b> — '
        f'{_t("moteur.audit.ff_explanation")}'
        f'</div>'
    )

    if feeder_flow.calibrated and _cap_main > 0:
        st.info(
            _t("moteur.audit.why_ff_body",
               title=_t("moteur.kpi.fill"),
               flow=f"{feeder_flow.effective_g_h:.0f}",
               dens=f"{bulk_density:.2f}",
               rpm=f"{screw_rpm:.0f}",
               qvol=f"{_qvol:.3f}",
               cap=f"{_cap_main:.3f}",
               ff=f"{_ff_main * 100:.0f}",
               rpm_full=f"{_rpm_full:.0f}"),
            icon="🧮",
        )
    elif not feeder_flow.calibrated:
        st.warning(_t("moteur.audit.flow_not_calibrated"), icon="⚠️")

    # ── Distinction explicite des débits (jamais confondus) ──────────────────
    st.markdown(_t("moteur.audit.flows_title"))
    _mach_cap = safe_float(st.session_state.get(MACHINE_MAX_CAPACITY_KEY, 0.0), 0.0, 0.0, 1e6)
    st.number_input(
        _t("moteur.audit.machine_cap"),
        min_value=0.0, max_value=100000.0, step=50.0, key=MACHINE_MAX_CAPACITY_KEY,
        help=_t("moteur.audit.machine_cap_help"),
    )
    _output_g_h = report.output_vol_flow_cm3_s * bulk_density * 3600.0
    _flow_rows = flow_taxonomy_rows(
        feed_effective_g_h=(feeder_flow.effective_g_h if feeder_flow.calibrated else None),
        machine_max_capacity_g_h=(_mach_cap if _mach_cap > 0 else None),
        output_flow_g_h=_output_g_h,
    )
    st.dataframe(
        pd.DataFrame(_flow_rows, columns=["variable", "valeur", "unite", "source",
                                          "statut", "used_in_ff", "commentaire"])
        .rename(columns={
            "variable": _t("moteur.audit.col.variable"),
            "valeur": _t("moteur.audit.col.value"),
            "unite": _t("moteur.audit.col.unit"),
            "source": _t("moteur.audit.col.source"),
            "statut": _t("moteur.audit.col.status"),
            "used_in_ff": _t("moteur.flow.col.used_in_ff"),
            "commentaire": _t("moteur.flow.col.comment")}),
        use_container_width=True, hide_index=True,
    )

    # ── Détail PAR FEEDER (multi-feeder) : débit + statut + contribution ──────
    _multi = _mi.get("multi_feeder")
    if _multi is not None and _multi.lines:
        st.markdown(_t("moteur.audit.feeder_detail"))
        _total = _multi.total_g_h or 0.0
        _STAT_I18N = {"OK": _t("moteur.feeder.status.ok"),
                      "CALIBRATION_MISSING": _t("moteur.feeder.status.not_calibrated"),
                      "DISABLED": _t("moteur.feeder.status.disabled")}
        _feeder_rows = []
        for _ln in _multi.lines:
            _gh = _ln.flow_g_h
            _val = _t("common.not_computable") if _gh is None else f"{_gh:.0f}"
            if _ln.status == "OK" and _total > 0:
                _contrib = f"{100.0 * (_gh or 0.0) / _total:.0f} %"
            elif _ln.status == "DISABLED":
                _contrib = "—"
            else:
                _contrib = _t("moteur.feeder.excluded")
            _feeder_rows.append({
                "Feeder": f"#{_ln.feeder_id}",
                "Label": _ln.label,
                _t("moteur.feeder.col.status"): _STAT_I18N.get(_ln.status, _ln.status),
                _t("moteur.feeder.col.flow"): _val,
                _t("moteur.feeder.col.contrib"): _contrib,
            })
        st.dataframe(
            pd.DataFrame(_feeder_rows), use_container_width=True, hide_index=True,
        )
        if _multi.total_calculable:
            _tot_msg = _t("moteur.audit.total_flow",
                          gh=f"{_multi.total_g_h:.0f}", gmin=f"{_multi.total_g_min:.2f}")
            if _multi.has_uncalibrated_active:
                st.warning(_tot_msg + _t("moteur.audit.total_incomplete"), icon="⚠️")
            else:
                st.caption(_tot_msg)
        else:
            st.warning(_t("moteur.audit.total_not_computable"), icon="⚠️")

    st.caption(_t("moteur.audit.status_legend"))

# ── Encart hypothèses ────────────────────────────────────────────────────────
st.divider()
with st.expander(_t("moteur.hypo.title"), expanded=True):
    if demo_mode:
        _mat_section = _t(
            "moteur.hypo.mat_demo",
            f1=report.feeder1_material,
            f2=report.feeder2_material or "—",
        )
    else:
        _mat_section = _t(
            "moteur.hypo.mat_client",
            not_entered=_t("historique.comp_not_entered"),
        )
    _temps = ", ".join(f"{tv:.0f}" for tv in NOMINAL_TEMP_PROFILE_C)
    st.markdown(
        f"{_mat_section}\n\n"
        f"{_t('moteur.hypo.torque_model')}\n\n"
        f"{_t('moteur.hypo.sme')}\n\n"
        f"{_t('moteur.hypo.thermal', temps=_temps)}\n\n"
        f"{_t('moteur.hypo.deferred')}\n\n"
        f"{_t('moteur.hypo.interp')}"
    )

st.caption(_t("moteur.footer"))
