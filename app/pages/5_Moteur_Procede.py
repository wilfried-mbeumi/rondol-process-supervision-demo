"""
5_Moteur_Procede.py — Moteur Procédé (couche engine : graph + couple + SME).

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
    demo_badge_html,
    demo_mode_toggle,
    material_label,
)
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

st.set_page_config(page_title="Moteur Procédé — Rondol", layout="wide")

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


# Sévérité d'évaluation remplissage → couleur de badge.
_FILL_BADGE_KIND = {
    "Sur-rempli": "crit",
    "Remplissage élevé": "warn",
    "Acceptable": "ok",
    "Sous-rempli": "neutral",
}

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


def _fill_assessment(report) -> tuple[str, str, str]:
    """Évaluation INDICATIVE du remplissage — pure LECTURE du fill_factor déjà
    calculé (aucune nouvelle équation). Retourne (libellé, sévérité, message).

    Sévérité ∈ {info, warning} pour un rendu cohérent (cf. UI severity levels).
    Les bornes sont des repères de présentation, pas des seuils industriels.
    """
    # On classe sur l'occupation MOYENNE (fill global). Une crête locale à 100 %
    # est normale sur un bloc de malaxage et ne signifie PAS un sur-remplissage :
    # « Sur-rempli » n'est réservé qu'à un vrai débordement feeder (overflow_*).
    avg = report.fill_factor_average
    overflow = report.overflow_main_feeder or report.overflow_side_feeder
    if overflow:
        return (
            "Sur-rempli",
            "warning",
            "Débordement détecté à un feeder. Risque indicatif de bourrage / montée "
            "de pression — réduire le débit ou augmenter la vitesse vis (à confirmer).",
        )
    if avg >= 0.75:
        return (
            "Remplissage élevé",
            "warning",
            "Occupation élevée. Surveiller couple et pression ; marge de procédé réduite.",
        )
    if avg >= 0.30:
        return (
            "Acceptable",
            "info",
            "Niveau de remplissage compatible avec un fonctionnement stable (indicatif).",
        )
    return (
        "Sous-rempli",
        "info",
        "Occupation faible. Convoyage/mélange potentiellement insuffisants — "
        "envisager plus de débit ou moins de vitesse vis.",
    )


# ===========================================================================
#  RENDU
# ===========================================================================
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>● Rondol · Moteur Procédé</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">Couche engine — couple local · SME · état machine</span>'
    f'</div>'
)

st.markdown("## Moteur Procédé")
st.caption(
    "Résultats calculés par la couche moteur (graph d'extrusion + couple E4 + SME) "
    "à partir de la configuration et des paramètres saisis dans Profile / Settings. "
    "Page en lecture seule."
)

# ── État vide explicite : aucun profil procédé chargé ────────────────────────
# Exigence manager : ne JAMAIS afficher des KPIs à 0 sans explication, ni charger
# un profil par défaut en silence. On affiche un message clair + un bouton de
# démonstration explicite, puis on stoppe le rendu (pas de KPIs trompeurs).
if profile_empty and not demo_active:
    st.info(
        "**Aucun profil procédé configuré.** Les valeurs affichées resteraient "
        "nulles tant qu'un profil de vis n'est pas chargé.\n\n"
        "→ Configurez un profil dans la page **Profile**, ou chargez ci-dessous un "
        "**profil de démonstration** (configuration nominale, non calibrée "
        "industriellement) pour visualiser la page.",
        icon="ℹ️",
    )
    if st.button(
        "▶  Charger un profil de démonstration",
        type="primary",
        use_container_width=False,
    ):
        st.session_state["mp_demo_profile"] = True
        st.rerun()
    st.caption("Rondol Industrie · Couche moteur procédé (engine) · Prototype")
    st.stop()

# Choix de la config rendue : démo page-local si demandée ET profil partagé vide,
# sinon le profil partagé réel. L'état partagé n'est JAMAIS modifié ici.
config: list[int] = _default_config() if demo_active else shared_config
report = _build_report(config)

# ── Bandeau profil de démonstration (uniquement en mode démo) ────────────────
if demo_active:
    dcol1, dcol2 = st.columns([4, 1])
    with dcol1:
        st.warning(
            "**⚙️ Profil de DÉMONSTRATION chargé.** Configuration nominale "
            "(convoyage → malaxages → convoyage), **non calibrée industriellement** — "
            "destinée à illustrer la page, pas à représenter un run réel.",
            icon="⚙️",
        )
    with dcol2:
        if st.button("✕  Décharger", use_container_width=True):
            st.session_state["mp_demo_profile"] = False
            st.rerun()

# ── Bandeau prototype (toujours visible) ─────────────────────────────────────
st.html(
    '<div class="mp-proto">'
    + _badge("⚠ Prototype", "warn")
    + "<span>Valeurs <b>nominales, non calibrées industriellement</b> — à "
      "interpréter en tendance, pas comme une vérité procédé finale. "
      "Détails dans « Hypothèses » en bas de page.</span>"
    + "</div>"
)

# ── Avertissement : débit NON calculable si feeder non étalonné ──────────────
# Exigence manager : ne JAMAIS présenter « 0 » comme une vérité procédé quand le
# coefficient d'étalonnage feeder est absent. Les indicateurs dépendant du débit
# affichent « Non calculable » (aucun débit par défaut inventé).
if not feed_available:
    st.warning(
        "**Débit réel non calculable : coefficient d'étalonnage feeder à "
        "renseigner.** Les indicateurs dépendant du débit (couple, SME, "
        "résidence, remplissage, débit massique, débit sortie) sont affichés "
        "« Non calculable » — aucun débit par défaut n'est inventé. Renseignez "
        "RPM feeder + coefficient g/h/RPM dans **Profile**.",
        icon="⚠️",
    )


def _nc(s: str) -> str:
    """Valeur affichée si le débit est calculable, sinon « Non calculable ».

    Empêche d'afficher un « 0 » trompeur comme vérité procédé quand le feeder
    n'est pas étalonné (le débit réel est inconnu, pas nul).
    """
    return s if feed_available else "Non calculable"


# ── KPIs principaux (carte) ──────────────────────────────────────────────────
_section("Indicateurs principaux", "valeurs estimées · modèle nominal (non calibré)")
with st.container(border=True):
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Couple total", _nc(f"{report.total_torque_nm:.3f} N·m"),
        help="Estimé (modèle E4) : M = η·γ̇²·V_rempli / (2π·N), sommé sur la vis. "
             "Confiance : nominale (presets matière non calibrés).",
    )
    k2.metric(
        "SME totale", _nc(f"{report.total_sme_kwh_per_kg:.3f} kWh/kg"),
        help="Énergie mécanique spécifique estimée : P_dissipée / débit massique, "
             "avec P = 2π·N·couple. Confiance : nominale.",
    )
    k3.metric(
        "Résidence totale", _nc(f"{report.residence_time_total_s:.1f} s"),
        help="Temps de séjour moyen estimé (volume vis rempli / débit). Indicatif.",
    )
    k4.metric(
        "Remplissage moyen", _nc(f"{report.fill_factor_average * 100:.0f} %"),
        help="Taux de remplissage moyen des positions de vis (fill factor calculé).",
    )
    k5.metric(
        "Cisaillement max", f"{report.max_shear_rate_s:.0f} s⁻¹",
        help="Taux de cisaillement maximal estimé (rpm × géométrie, indépendant du débit).",
    )

# ── État machine / graph (carte + chips) ─────────────────────────────────────
_section("État machine / graph")
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Puissance dissipée", _nc(f"{report.total_power_w:.1f} W"))
    m2.metric("Débit massique", _nc(f"{report.mass_flow_kg_per_h:.2f} kg/h"))
    m3.metric("Débit sortie (pointe)", _nc(f"{report.output_vol_flow_cm3_s:.2f} cm³/s"))
    m4.metric(
        "Remplissage crête",
        _nc(f"{report.peak_fill_factor * 100:.0f} %"),
        (f"position #{report.peak_fill_position:02d}" if feed_available else None),
    )
    _chips = [
        _chip("Vitesse vis", f"{report.screw_rpm:.0f} tr/min"),
        _chip("Overflow main", "oui" if report.overflow_main_feeder else "non",
              warn=report.overflow_main_feeder),
        _chip("Overflow side", "oui" if report.overflow_side_feeder else "non",
              warn=report.overflow_side_feeder),
        # Matière : « Non renseigné » en mode client (aucune saisie matière
        # réelle n'existe encore) ; nom chimique nominal + badge DEMO en démo.
        _chip("Feeder 1",
              f"{material_label(report.feeder1_material, demo_mode)} {demo_badge_html()}"
              if demo_mode else material_label(report.feeder1_material, demo_mode)),
    ]
    if demo_mode and report.feeder2_material:
        _chips.append(_chip("Feeder 2", f"{report.feeder2_material} {demo_badge_html()}"))
    st.html(f'<div class="mp-chips">{"".join(_chips)}</div>')

# ── Évaluation indicative du remplissage (lecture du fill_factor, FR-11) ──────
# AUCUNE nouvelle équation : simple interprétation par paliers du fill_factor
# déjà calculé par la couche moteur. Wording volontairement prudent.
_section("Évaluation du remplissage", "indicative — lecture du fill_factor calculé")
if not feed_available:
    # Pas de débit étalonné → le fill factor n'est pas calculable : on n'émet
    # AUCUN verdict (« Sous-rempli » sur un 0 serait trompeur).
    st.info(
        "Remplissage **non calculable** — coefficient d'étalonnage feeder à "
        "renseigner (le fill factor dépend du débit réel).",
        icon="ℹ️",
    )
else:
    _fill_label, _fill_sev, _fill_msg = _fill_assessment(report)
    st.html(_badge(f"● {_fill_label}", _FILL_BADGE_KIND.get(_fill_label, "neutral")))
    _banner = st.warning if _fill_sev == "warning" else st.info
    _banner(
        f"**{_fill_label}** — {_fill_msg}\n\n"
        f"*Évaluation indicative, basée sur le fill_factor calculé "
        f"(moyen {report.fill_factor_average * 100:.0f} %, crête "
        f"{report.peak_fill_factor * 100:.0f} %) — à confirmer sur essai réel.*",
        icon="🟢" if _fill_sev == "info" else "🟠",
    )

# ── Statut équations différées E6 / E7 (cartes + badge « À venir ») ───────────
_section("Équations à venir", "non calculées")
e1, e2 = st.columns(2)
with e1:
    st.html(
        '<div class="mp-defer">'
        f'<h4>🕒 E6 — Température réelle du fondu (T_real) {_badge("À venir", "neutral")}</h4>'
        '<p>Équation manager imposée '
        '<code>T_real = T_set + (2π·N·M)/(ṁ·Cp) + k·τ</code> — nécessite des '
        'constantes thermiques à recaler.</p>'
        '<p><b style="color:#CBD5E1;">Statut :</b> non disponible.</p>'
        '</div>'
    )
with e2:
    st.html(
        '<div class="mp-defer">'
        f'<h4>🕒 E7 — Pression / contre-pression filière {_badge("À venir", "neutral")}</h4>'
        '<p>Nécessite une loi ΔP filière (Hagen-Poiseuille + correction non '
        'newtonienne) au-dessus de la géométrie de filière.</p>'
        '<p><b style="color:#CBD5E1;">Statut :</b> non disponible.</p>'
        '</div>'
    )

# ── Agrégats par zone ────────────────────────────────────────────────────────
_section("Agrégats par zone", "Feed + Z1..Z8")
_zone_labels = ["Feed", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
_zone_rows = []
for z in report.zones:
    label = _zone_labels[z.zone] if 0 <= z.zone < len(_zone_labels) else f"Z{z.zone}"
    _zone_rows.append({
        "Zone": label,
        "Positions": z.n_nodes,
        "Remplissage moyen": z.mean_fill_factor * 100.0,
        "Remplissage crête": z.max_fill_factor * 100.0,
        "γ̇ moyen": z.mean_shear_rate_s,
        "γ̇ max": z.max_shear_rate_s,
        "T max": z.max_temperature_c,
        # Mode client : pas de matière chimique inventée → « Non renseigné ».
        "Matière dominante": material_label(z.dominant_material, demo_mode),
        "Résidence": z.residence_time_s,
    })
st.dataframe(
    pd.DataFrame(_zone_rows), use_container_width=True, hide_index=True,
    column_config={
        "Positions": st.column_config.NumberColumn("Positions", format="%d"),
        "Remplissage moyen": st.column_config.ProgressColumn(
            "Remplissage moyen", min_value=0, max_value=100, format="%.0f%%"),
        "Remplissage crête": st.column_config.ProgressColumn(
            "Remplissage crête", min_value=0, max_value=100, format="%.0f%%"),
        "γ̇ moyen": st.column_config.NumberColumn("γ̇ moyen (s⁻¹)", format="%.0f"),
        "γ̇ max": st.column_config.NumberColumn("γ̇ max (s⁻¹)", format="%.0f"),
        "T max": st.column_config.NumberColumn("T consigne max (°C)", format="%.0f"),
        "Résidence": st.column_config.NumberColumn("Résidence (s)", format="%.1f"),
    },
)

# ── Détail par position ──────────────────────────────────────────────────────
_section("Propriétés locales par position de vis", "0..80")
_hide_empty = st.checkbox("Masquer les positions vides", value=True)
_pos_rows = []
for p in report.positions:
    if _hide_empty and p.is_empty:
        continue
    _pos_rows.append({
        "Pos.": p.position,
        "Zone": _zone_labels[p.zone] if 0 <= p.zone < len(_zone_labels) else str(p.zone),
        "Élément": p.element_label,
        "Port": p.port_kind or "—",
        "Remplissage": p.fill_factor * 100.0,
        "γ̇": p.shear_rate_s,
        "Couple local": p.torque_nm,
    })
if _pos_rows:
    st.dataframe(
        pd.DataFrame(_pos_rows), use_container_width=True, hide_index=True, height=380,
        column_config={
            "Pos.": st.column_config.NumberColumn("Pos.", format="%d"),
            "Remplissage": st.column_config.ProgressColumn(
                "Remplissage", min_value=0, max_value=100, format="%.0f%%"),
            "γ̇": st.column_config.NumberColumn("γ̇ (s⁻¹)", format="%.0f"),
            "Couple local": st.column_config.NumberColumn(
                "Couple local (N·m)", format="%.4f"),
        },
    )
else:
    st.caption("Aucune position à afficher (profil vide).")

# ── Audit calcul procédé (transparence entrée → sortie, provenance + statut) ──
# Exigence manager : MONTRER chaque variable machine, son unité, sa source, sa
# formule et son STATUT (validé PLC / correction manager / à valider). Formules
# vérifiées sur la source PLC Rondol (references/logique_metier/2-CALCULS.pdf,
# Network 7). Aucune valeur sans provenance.
_section("Audit calcul procédé", "débit · capacité · remplissage · résidence — source PLC Network 7")
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
    _n_elem = count_user_elements(shared_config)
    _rpm_full = screw_rpm * _ff_main if _ff_main > 0 else 0.0  # rpm où FF≈100 %

    # Statuts honnêtes : la chaîne FF (capacité, V_libre/tour, FF) dépend de
    # valeurs DB automate non confirmées ET de la correction manager ×2 → on
    # n'écrit PAS « validé PLC » sur ces lignes.
    _PLC = "Formule PLC validée (Network 7)"          # formule PURE sans constante à confirmer
    _PLC_ASSUM = formula_status_label()                # formule PLC + constantes à confirmer
    _PLC_DB = "Constante PLC — valeurs DB à confirmer"
    _MGR = "Correction manager (hors PLC d'origine)"
    _MGR_LIM = "Limite manager — à valider"
    _IN = "Saisie"
    _CALC = "Calculé"
    _ff_status = fill_factor_validation_status(feed_known=feeder_flow.calibrated)

    if feeder_flow.calibrated:
        _dem = f"{feeder_flow.requested_g_h:.1f}"
        _eff_gh = f"{feeder_flow.effective_g_h:.1f}"
        _eff_gmin = f"{feeder_flow.effective_g_min:.3f}"
        _eff_gs = f"{feeder_flow.effective_g_s:.5f}"
        _coeff = f"{feeder_flow.calibration_g_h_per_rpm:.3f}"
        _coeff_src, _coeff_stat = "USER_INPUT", "Étalonnage externe (= Mass_flow_rate PLC, g/tour×60)"
    else:
        _dem = _eff_gh = _eff_gmin = _eff_gs = "Non calculable"
        _coeff = "Non renseigné"
        _coeff_src, _coeff_stat = "NOT_AVAILABLE", "Étalonnage requis"

    _rows = [
        ("RPM feeder", f"{feeder_flow.feeder_rpm:.0f}", "RPM", "USER_INPUT", "—", _IN),
        ("Coefficient étalonnage", _coeff, "g/h/RPM", _coeff_src, "= Mass_flow_rate (PLC L0018)", _coeff_stat),
        ("Débit demandé", _dem, "g/h", "CALCULATED", "RPM × coeff", _CALC),
        ("Débit max machine", f"{feeder_flow.max_machine_g_h:.0f}", "g/h", "DEFAULT_CONFIG", "—", _MGR_LIM),
        ("Débit effectif (calcul)", _eff_gh, "g/h", "CALCULATED", "min(demandé, max)", _CALC),
        ("Débit effectif", _eff_gmin, "g/min", "CALCULATED", "g/h ÷ 60", _CALC),
        ("Débit effectif", _eff_gs, "g/s", "CALCULATED", "g/h ÷ 3600", _CALC),
        ("Densité apparente ρ", f"{bulk_density:.3f}", "g/cm³", "USER_INPUT", "—", _IN),
        ("Débit volumique Q_vol", f"{_qvol:.4f}", "cm³/s", "CALCULATED", "ṁ ÷ ρ (PLC L0056)", _PLC),
        ("RPM vis", f"{screw_rpm:.0f}", "tr/min", "USER_INPUT", "—", _IN),
        ("N (vis)", f"{_n_rps:.3f}", "tr/s", "CALCULATED", "rpm ÷ 60 (PLC L0015)", _PLC),
        ("V libre / tour (main)", f"{_v_byrev_main:.4f}", "cm³/tour", "CALCULATED",
         "V_libre × Factor_FreeByRev (PLC L0033)", _PLC_DB),
        ("Capacité volumique (main)", f"{_cap_main:.4f}", "cm³/s", "CALCULATED",
         "N × V_libre/tour (PLC L0057)", _PLC_ASSUM),
        ("Volume libre utile (2 vis)", f"{_free_vol_2screws:.2f}", "cm³", "CALCULATED",
         "76.1756 − 2×occupé/vis", _MGR),
        ("Nombre d'éléments", f"{_n_elem:.0f}", "—", "USER_INPUT", "—", _IN),
        ("Fill factor (main)", f"{_ff_main * 100:.1f}", "%", "CALCULATED",
         "Q_vol ÷ capacité (PLC L0060)", _PLC_ASSUM),
        ("Remplissage moyen (rapport)", f"{report.fill_factor_average * 100:.1f}", "%", "CALCULATED",
         "moyenne FF (PLC L0153)", _PLC_ASSUM),
        ("Temps de résidence total", f"{report.residence_time_total_s:.1f}", "s", "CALCULATED",
         "Σ V_libre/VolFlow (PLC L0144)", _PLC_ASSUM),
    ]
    st.dataframe(
        pd.DataFrame(_rows, columns=["Variable", "Valeur", "Unité", "Source", "Formule", "Statut"]),
        use_container_width=True, hide_index=True,
    )

    # Statut HONNÊTE du résultat FF + clarification du périmètre du débit.
    _status_color = {"CALCULATED_CONFIRMED": ACC,
                     "CALCULATED_WITH_ASSUMPTIONS": WARN,
                     "NOT_VALIDATED": CRIT}.get(_ff_status, WARN)
    st.html(
        f'<div style="background:rgba(251,191,36,.08);border:1px solid {_status_color};'
        f'border-radius:.4rem;padding:.4rem .7rem;margin:.3rem 0;font-size:.84rem;color:#E5E7EB;">'
        f'<b style="color:{_status_color};">Statut du résultat fill factor : {_ff_status}</b> — '
        f'le fill factor affiché est calculé sur le <b>débit feeder effectif utilisé par le '
        f'modèle</b>, <b>pas</b> sur la capacité machine globale ni sur le débit sortie filière.'
        f'</div>'
    )

    # Explication chiffrée du « pourquoi 26 % » (présentée comme cohérente avec
    # les hypothèses, PAS comme vérité métier définitive) + condition FF→100 %.
    if feeder_flow.calibrated and _cap_main > 0:
        st.info(
            f"**Pourquoi FF = {_ff_main * 100:.0f} % ?** *Résultat cohérent avec les "
            f"paramètres actuels (débit {feeder_flow.effective_g_h:.0f} g/h, densité "
            f"{bulk_density:.2f}, {screw_rpm:.0f} rpm, capacité vis issue PLC/DB à "
            f"confirmer).* Au main feeder, `Q_vol = {_qvol:.3f} cm³/s` alimenté contre "
            f"une `capacité = {_cap_main:.3f} cm³/s` → `FF = {_ff_main * 100:.0f} %`. "
            f"Cohérent avec une bivis *starve-fed* (capacité > débit). **FF → 100 %** si "
            f"la capacité descend au niveau du débit : baisser la vis vers "
            f"**≈ {_rpm_full:.0f} tr/min**, augmenter le débit, ou augmenter la densité. "
            f"⚠️ Tant que les constantes DB vis / le ×2 bivis ne sont pas validés Rondol, "
            f"ce % reste **calculé avec hypothèses**, non une vérité procédé définitive.",
            icon="🧮",
        )
    elif not feeder_flow.calibrated:
        st.warning(
            "Débit réel **non calculable** (coefficient d'étalonnage feeder non "
            "renseigné). Les valeurs procédé ci-dessus reposent sur la **saisie "
            "directe** de débit (hors étalonnage) — renseignez le coefficient "
            "g/h/RPM dans **Profile** pour un débit réel tracé.",
            icon="⚠️",
        )

    # ── Distinction explicite des débits (jamais confondus) ──────────────────
    st.markdown("**Débits — ne pas confondre :**")
    _mach_cap = safe_float(st.session_state.get(MACHINE_MAX_CAPACITY_KEY, 0.0), 0.0, 0.0, 1e6)
    st.number_input(
        "Capacité machine déclarée (g/h) — référence, n'écrase PAS le débit feeder",
        min_value=0.0, max_value=100000.0, step=50.0, key=MACHINE_MAX_CAPACITY_KEY,
        help="Optionnel. Le manager évoque ≈ 1 kg/h (1000 g/h). 0 = non renseigné. "
             "Sert de référence/contrainte, jamais de débit de calcul.",
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
        .rename(columns={"variable": "Variable", "valeur": "Valeur", "unite": "Unité",
                         "source": "Source", "statut": "Statut validation",
                         "used_in_ff": "Utilisée dans FF ?", "commentaire": "Commentaire métier"}),
        use_container_width=True, hide_index=True,
    )

    st.caption(
        "Statuts : *Formule PLC validée* = vérifiée sur la source automate Rondol "
        "(2-CALCULS.pdf, Network 7), sans constante à confirmer. *Formule PLC "
        "utilisée — constantes partiellement à confirmer* = formule PLC mais "
        "dépend de valeurs DB automate (DataScrewElmt) et/ou de la correction "
        "manager ×2 (bivis, hors PLC d'origine). *CALCULATED_WITH_ASSUMPTIONS* = "
        "résultat cohérent mais soumis à ces hypothèses. *Limite manager — à valider* "
        "= plafond 300 g/h indiqué manager, à confirmer Rondol."
    )

# ── Encart hypothèses ────────────────────────────────────────────────────────
st.divider()
with st.expander("ℹ️ Hypothèses, limites et statut du modèle", expanded=True):
    if demo_mode:
        _mat_section = (
            f"**Matières (DÉMONSTRATION — nominales, non calibrées)**\n"
            f"- Feeder 1 = `{report.feeder1_material}` ; feeder 2 = "
            f"`{report.feeder2_material or '—'}` (side feeder uniquement si activé).\n"
            f"- ⚠️ Valeurs de **démonstration** : presets nominaux, pas la matière "
            f"d'un run réel. Désactivez le mode démonstration pour le mode client."
        )
    else:
        _mat_section = (
            "**Matière**\n"
            "- **Non renseigné** : aucune saisie matière dédiée n'existe encore "
            "dans l'interface. Le couple / la SME / le remplissage sont calculés à "
            "partir de la **géométrie de vis** et des **paramètres procédé** "
            "(vitesse, débit, densité bulk), sans hypothèse de chimie spécifique.\n"
            "- Aucun nom de matière n'est affiché tant qu'aucune saisie matière "
            "réelle n'a été effectuée."
        )
    st.markdown(
        f"""
{_mat_section}

**Modèle de couple (E4)**
- `M_node = η · γ̇² · V_filled / (2π·N)` — modèle **uniforme transparent**.
- `V_filled` = volume libre local × remplissage : **proxy provisoire** du volume cisaillé.
- Pas de pondération par type d'élément (malaxage vs convoyage) en v1.
- Effets pression-flow / fuites **hors périmètre**.

**SME (totale uniquement)**
- `SME = P_dissipée / ṁ` avec `P = 2π·N · couple_total` (dérivée du couple E4) ;
  ṁ = débit d'alimentation total (**hypothèse régime permanent** feed = sortie).
- La SME **par position** n'est pas encore matérialisée.

**Profil thermique**
- Consignes de zone **nominales de démonstration** : {", ".join(f"{t:.0f}" for t in NOMINAL_TEMP_PROFILE_C)} °C
  (le profil thermique réel n'est pas partagé via `session_state`).

**Équations différées**
- **E6 (T_real)** et **E7 (pression)** : *non calculées* — affichées « À venir ».

> **Interprétation** : ce moteur est un **prototype d'aide à la décision**. Les valeurs
> sont cohérentes en **relatif/tendance** (comparer deux profils, voir l'effet du
> régime/feeder), mais ne constituent **pas** une vérité industrielle calibrée.
        """
    )

st.caption("Rondol Industrie · Couche moteur procédé (engine) · Prototype")
