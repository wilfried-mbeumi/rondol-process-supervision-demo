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
    SIDE_FEEDER_DISABLED_ZONE,
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
from feeder_ui import (  # noqa: E402
    current_feeder_flow,
    ensure_feeder_defaults,
    feeder_audit_rows,
)
from screw_logic import free_volume as _free_volume  # noqa: E402
from AgentIndustrial_v1.core.coercion import safe_float, safe_int  # noqa: E402

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


# NB : on N'INJECTE PLUS de profil par défaut en silence. La clé partagée est
# seulement défaultée à une config vide (tip seul) — état neutre, identique aux
# autres pages — et l'éventuel profil de démonstration reste page-local.
st.session_state.setdefault("screw_config", new_empty_configuration())
st.session_state.setdefault("screw_rpm", 120.0)
st.session_state.setdefault("feeder_g_per_min", 30.0)
st.session_state.setdefault("bulk_density", 0.55)
st.session_state.setdefault("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE)
# Flag PAGE-LOCAL (préfixe mp_) : ne touche PAS l'état partagé screw_config.
st.session_state.setdefault("mp_demo_profile", False)

shared_config: list[int] = st.session_state["screw_config"]
screw_rpm = safe_float(st.session_state.get("screw_rpm", 120.0), 120.0, 1.0, 3000.0)
bulk_density = safe_float(st.session_state.get("bulk_density", 0.55), 0.55, 0.0001, 10.0)

# Débit feeder via étalonnage (RPM × coeff). Si étalonné, le débit EFFECTIF
# (plafonné au max machine) est la source de vérité du calcul. Sinon, repli
# sur la valeur directe legacy (clairement signalé dans l'audit ci-dessous).
ensure_feeder_defaults(st.session_state)
feeder_flow = current_feeder_flow(st.session_state)
if feeder_flow.calibrated:
    feed_g_per_min = float(feeder_flow.effective_g_min or 0.0)
else:
    feed_g_per_min = safe_float(st.session_state.get("feeder_g_per_min", 30.0), 30.0, 0.0, 2000.0)
side_feeder_zone = safe_int(st.session_state.get("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE),
                            SIDE_FEEDER_DISABLED_ZONE, 0, 8)

# Mode client (défaut) vs démonstration — pilote l'affichage des matières.
with st.sidebar:
    demo_mode = demo_mode_toggle(st)

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

# ── KPIs principaux (carte) ──────────────────────────────────────────────────
_section("Indicateurs principaux", "valeurs estimées · modèle nominal (non calibré)")
with st.container(border=True):
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Couple total", f"{report.total_torque_nm:.3f} N·m",
        help="Estimé (modèle E4) : M = η·γ̇²·V_rempli / (2π·N), sommé sur la vis. "
             "Confiance : nominale (presets matière non calibrés).",
    )
    k2.metric(
        "SME totale", f"{report.total_sme_kwh_per_kg:.3f} kWh/kg",
        help="Énergie mécanique spécifique estimée : P_dissipée / débit massique, "
             "avec P = 2π·N·couple. Confiance : nominale.",
    )
    k3.metric(
        "Résidence totale", f"{report.residence_time_total_s:.1f} s",
        help="Temps de séjour moyen estimé (volume vis rempli / débit). Indicatif.",
    )
    k4.metric(
        "Remplissage moyen", f"{report.fill_factor_average * 100:.0f} %",
        help="Taux de remplissage moyen des positions de vis (fill factor calculé).",
    )
    k5.metric(
        "Cisaillement max", f"{report.max_shear_rate_s:.0f} s⁻¹",
        help="Taux de cisaillement maximal estimé le long de la vis.",
    )

# ── État machine / graph (carte + chips) ─────────────────────────────────────
_section("État machine / graph")
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Puissance dissipée", f"{report.total_power_w:.1f} W")
    m2.metric("Débit massique", f"{report.mass_flow_kg_per_h:.2f} kg/h")
    m3.metric("Débit sortie (pointe)", f"{report.output_vol_flow_cm3_s:.2f} cm³/s")
    m4.metric(
        "Remplissage crête",
        f"{report.peak_fill_factor * 100:.0f} %",
        f"position #{report.peak_fill_position:02d}",
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

# ── Audit calcul (transparence débit → remplissage → résidence) ──────────────
# Exigence manager : l'app doit MONTRER d'où vient chaque nombre. Aucune valeur
# sans provenance ; toute constante non calibrée est signalée.
_section("Audit calcul", "débit feeder · remplissage · résidence — provenance tracée")
with st.container(border=True):
    _audit_rows = feeder_audit_rows(feeder_flow, bulk_density, density_provenance="USER_INPUT")
    # Grandeurs procédé calculées (lecture du rapport moteur — aucune nouvelle équation).
    _free_vol_2screws = _free_volume(shared_config)
    _n_elem = count_user_elements(shared_config)
    _audit_rows += [
        {"grandeur": "Vitesse vis", "valeur": f"{report.screw_rpm:.0f} tr/min", "provenance": "USER_INPUT"},
        {"grandeur": "Volume libre utile (2 vis)", "valeur": f"{_free_vol_2screws:.2f} cm³", "provenance": "CALCULATED"},
        {"grandeur": "Nombre d'éléments", "valeur": f"{_n_elem:.0f}", "provenance": "USER_INPUT"},
        {"grandeur": "Remplissage moyen (fill factor)", "valeur": f"{report.fill_factor_average * 100:.1f} %", "provenance": "CALCULATED"},
        {"grandeur": "Temps de résidence total", "valeur": f"{report.residence_time_total_s:.1f} s", "provenance": "CALCULATED"},
    ]
    st.dataframe(
        pd.DataFrame(_audit_rows), use_container_width=True, hide_index=True,
        column_config={
            "grandeur": st.column_config.TextColumn("Grandeur"),
            "valeur": st.column_config.TextColumn("Valeur"),
            "provenance": st.column_config.TextColumn("Provenance"),
        },
    )
    st.markdown(
        "**Formules** (constantes géométriques validées Rondol — PDF Network 7 ; "
        "facteurs thermiques/presets = *non calibrés, indicatifs*) :\n"
        "- Débit volumique : `Q_vol = ṁ / ρ` (g/s ÷ g/cm³ → cm³/s)\n"
        "- Capacité conveyage : `capacité = N_tr/s × V_libre/tour` (cm³/s)\n"
        "- **Fill factor** : `FF = Q_vol / capacité` (borné 0–1)\n"
        "- Temps de résidence : `RT = Σ V_libre_local / débit_volumique_local`"
    )
    if not feeder_flow.calibrated:
        st.warning(
            "Débit réel **non calculable** (coefficient d'étalonnage feeder non "
            "renseigné). Les indicateurs ci-dessus reposent sur la **saisie directe** "
            "de débit (hors étalonnage) — renseignez le coefficient g/h/RPM dans "
            "**Profile** pour un débit réel tracé.",
            icon="⚠️",
        )
    else:
        st.caption(
            "ℹ️ Un remplissage faible à haut régime est **normal en bivis "
            "*starve-fed*** : si la capacité de convoyage (N × V_libre/tour) dépasse "
            "le débit volumique alimenté, FF < 100 %. Baisser la vitesse vis "
            "augmente le remplissage à débit constant."
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
