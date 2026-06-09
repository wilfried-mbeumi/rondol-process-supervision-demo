"""
2_Settings.py — Paramétrage Agent IA (HMI Rondol fusionné AgentIndustrial_v1).

Fusion réelle : la page Settings existante reçoit les capacités du moteur
AgentIndustrial_v1 (feeders 1..5, règles explicables, recommandations
chiffrées) tout en conservant la navigation, le moteur SVM w60 retenu et les
clés session_state partagées avec Profile / Home (screw_rpm, feeder_g_per_min,
bulk_density, side_feeder_zone, ff_target_low/high, target_screw_count,
screw_config, monitored_zones, th_stable, th_critical).

Couches d'état (refonte 2026-05-20, exigence manager) :
  - **edit** : valeurs vivantes des widgets (clés session_state habituelles).
  - **applied** : snapshot validé (`applied_state.commit`) — source unique
    consommée par Supervision et l'agent IA. Modifier les widgets de Settings
    n'altère pas ce snapshot tant que l'opérateur ne clique pas « Enregistrer ».
  - **history** : liste des snapshots validés (jamais effacée par une édition).

Cooling Test retiré : la fonctionnalité n'existe pas dans le procédé réel.
Le diagnostic thermique cible automatiquement la zone la plus chaude calculée
par le modèle (cf. AgentIndustrial_v1/core/cooling.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
APP = Path(__file__).resolve().parent.parent
for p in (ROOT, APP):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# Existant Kévin — inchangé
from screw_logic import (  # noqa: E402
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    SIDE_FEEDER_DISABLED_ZONE,
    TIP_PART1_POS,
)

# Fusion AgentIndustrial_v1 — réutilisation directe du moteur
from AgentIndustrial_v1.core.feeders import (  # noqa: E402
    FEEDER_POSITIONS,
    MATERIAL_TYPES,
    FeederSpec,
    active_feeders,
    mass_flow_by_phase,
    total_mass_flow,
)
from AgentIndustrial_v1.core.cooling import compute_cooling  # noqa: E402
from AgentIndustrial_v1.core.process import (  # noqa: E402
    DEFAULT_ZONE_TARGETS_C,
    ProcessState,
    THERMAL_REG_BAND_C,
    default_zone_target,
)
from AgentIndustrial_v1.core.recommendations import Recommendation, build_recommendations  # noqa: E402
from AgentIndustrial_v1.core.rules import Alert, AgentReport, evaluate  # noqa: E402
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402
    commit as applied_commit,
    get_applied,
    get_history,
    has_unsaved_changes,
)
from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    feeder_calibrated_g_per_min,
    feeder_is_calibrated,
    project_shared_keys,
    seed_editing_keys,
)
from AgentIndustrial_v1.core.coercion import safe_int  # noqa: E402

# P3.2 : source de vérité current_run_state + projection legacy (sens unique).
from run_state_adapter import sync_legacy_projection  # noqa: E402
# Étalonnage multi-feeder (RPM × coeff → débit) — bloc Settings.
from feeder_ui import render_multi_feeder_calibration  # noqa: E402
# Store opérateur central persistant (survie navigation / langue / refresh).
from operator_store import capture_operator_state, restore_operator_state  # noqa: E402

# i18n — sélecteur de langue + traduction du chrome (B1).
from rondol_i18n import language_selector, t  # noqa: E402

# Historique procédé PERSISTANT (disque) — figement des KPIs moteur au commit.
# Le rapport moteur est construit via le helper PARTAGÉ (mêmes valeurs que la
# page Moteur Procédé) ; le store ne fait que persister/mettre en forme.
import history_store  # noqa: E402
from engine.report_params import build_report_from_flat_params  # noqa: E402


# ===========================================================================
# Chemins / page config
# ===========================================================================
METRICS_PATH = ROOT / "reports" / "ml_metrics_w60.json"
THRESHOLD_PATH = ROOT / "reports" / "threshold_calibration_w60.csv"
FEAT_IMP_PATH = ROOT / "reports" / "feature_importance_SVM_w60_threshold80.csv"

st.set_page_config(page_title=t("page.settings.title"), layout="wide")

RONDOL_GREEN = "#4CAF50"
BG = "#0B0F14"
PANEL = "#1A1F26"
BORDER = "#2C333D"
TEXT = "#E5E7EB"
SUB = "#9CA3AF"
SLOT = "#374151"
LCD = "#0F1419"
ACC = "#10B981"
WARN = "#F59E0B"
CRIT = "#EF4444"


# ===========================================================================
# CSS HMI — blocs compacts machine industrielle
# ===========================================================================
st.html(f"""
<style>
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{background-color:{BG}!important;}}
.block-container{{padding-top:0.4rem!important;padding-left:1rem!important;padding-right:1rem!important;max-width:100%!important;}}
header[data-testid="stHeader"]{{background:transparent!important;height:0!important;}}
[data-testid="stSidebar"]{{background-color:#0D1117!important;border-right:1px solid #1F2937!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label,[data-testid="stSidebar"] div{{color:#9CA3AF!important;}}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:#0D1117}}
::-webkit-scrollbar-thumb{{background:#374151;border-radius:3px}}

/* Widgets compacts pour mode HMI */
.stNumberInput, .stSelectbox, .stTextInput {{ margin-bottom: 0.15rem !important; }}
.stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextInput input {{
    background:{LCD}!important; color:{TEXT}!important; border:1px solid {BORDER}!important;
    font-family: 'Consolas', monospace !important; font-size: 0.82rem !important;
    text-align: center !important;
}}
.stNumberInput label, .stSelectbox label, .stTextInput label {{
    color: {SUB} !important; font-size: 0.68rem !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.04em;
}}
button[kind="secondary"] {{
    background:{SLOT}!important; border:1px solid {BORDER}!important;
    color:{TEXT}!important; font-size:0.78rem!important;
}}
button[kind="primary"] {{
    background:{ACC}!important; border:1px solid {ACC}!important;
    color:#06210f!important; font-size:0.78rem!important; font-weight:700!important;
    box-shadow:0 0 8px rgba(16,185,129,0.55)!important;
}}
/* Boutons compacts (alertes, actions Enregistrer) */
[data-testid="column"] .stButton {{ margin-bottom:0.18rem!important; }}
[data-testid="column"] .stButton button {{
    font-family:Consolas,monospace!important; letter-spacing:0.02em;
    padding:0.3rem 0.4rem!important;
}}
.stExpander {{ border:1px solid {BORDER}!important; background:{PANEL}!important; border-radius:0.25rem!important; }}
</style>
""")

# i18n (B0) — sélecteur de langue (sidebar). Aucun contenu métier traduit ici.
language_selector()


# ===========================================================================
# Session defaults — clés partagées avec Profile / Home (à NE PAS casser)
# ===========================================================================
# Restaure la config opérateur centrale AVANT les défauts/widgets (survie
# navigation multipage + refresh) — n'écrase jamais une valeur déjà présente.
restore_operator_state(st.session_state)

st.session_state.setdefault("th_stable", 80)
st.session_state.setdefault("th_critical", 65)
st.session_state.setdefault("th_proba_stable", 0.70)
st.session_state.setdefault("th_proba_critical", 0.40)
st.session_state.setdefault("analysis_hz", 2.0)
st.session_state.setdefault(
    "monitored_zones",
    ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8", "DIE", "CastFilmBody"],
)
st.session_state.setdefault("screw_rpm", 120.0)
st.session_state.setdefault("feeder_g_per_min", 30.0)
st.session_state.setdefault("bulk_density", 0.55)
st.session_state.setdefault("side_feeder_zone", SIDE_FEEDER_DISABLED_ZONE)
st.session_state.setdefault("ff_target_low", 30)
st.session_state.setdefault("ff_target_high", 55)
# Défaut Rondol validé manager : 40 éléments (choix 25/30/40 conservé).
st.session_state.setdefault("target_screw_count", 40)

# ===========================================================================
# COUCHE D'ÉDITION — propriété unique : les clés widget session_state.
# ===========================================================================
# Reconception 2026-05-21 (cf. AgentIndustrial_v1/core/editing_state.py).
#
# Plus d'objet `agent_state` mutable conservé en session : la source de vérité
# pendant l'édition est exclusivement constituée des clés widget
# (`th_Z1`..`th_die4`, `n_die_zones`, `fd_*`, `ni_rpm_hmi`, `ni_tq_v2`,
# `ni_pr_v2`). Streamlit garantit qu'elles contiennent la valeur courante du
# widget dès le DÉBUT du rerun → l'état peut être reconstruit n'importe où,
# indépendamment de l'ordre du layout.
#
#   seed_editing_keys()  : hydrate les clés manquantes (snapshot > legacy >
#                          défauts), idempotent → règle 1er boot ET purge de
#                          navigation en un seul endroit, sans écraser une
#                          édition en cours.
#   build_state_from_widgets() : lecteur PUR → ProcessState dérivé, ne mute rien.
seed_editing_keys(st.session_state)
state: ProcessState = build_state_from_widgets(st.session_state)

# Garde anti-crash widget : certains widgets sont restreints à une liste
# d'options (selectbox n_die_zones ∈ {0..4}). Si la session contient une valeur
# polluée/mal typée (ex. "2.0", libellé traduit) héritée d'une version antérieure,
# Streamlit lèverait « is not in list » À LA CRÉATION du widget — avant même nos
# lectures coercées. On normalise donc la clé widget dans son domaine valide ici,
# une fois, avant tout rendu de widget (cf. crash « changement de langue »).
# Manager 2026-06-09 : 0 zone die (filière absente) autorisé en plus de 1..4.
st.session_state["n_die_zones"] = safe_int(
    st.session_state.get("n_die_zones", 1), 1, 0, 4
)


# ===========================================================================
# Header HMI vert (cf. photo référence)
# ===========================================================================
_alarm_count_preview = 0  # complété après évaluation, en pied de page
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.6rem;">'
    f'<span>{t("settings.banner.left")}</span>'
    f'<span style="font-size:0.82rem;opacity:0.95;">{t("settings.banner.right")}</span>'
    f'</div>'
)

# ===========================================================================
# Barre persistance — Enregistrer / Statut snapshot / Historique
# ===========================================================================
# Cf. AgentIndustrial_v1/core/applied_state.py — exigence manager 2026-05-20 :
# Settings édite librement, Supervision lit le snapshot validé (jamais
# écrasé tant que l'opérateur n'a pas cliqué « Enregistrer »).
#
_save_col, _label_col, _info_col = st.columns([1.2, 2.2, 4.5])
with _save_col:
    if st.button(
        t("settings.save.btn"),
        type="primary", use_container_width=True, key="btn_apply_state",
        help=t("settings.save.help"),
    ):
        # Le commit lit l'état reconstruit depuis les clés widget. Streamlit a
        # déjà publié la valeur fraîche de chaque widget dans session_state au
        # début de ce rerun → `state` (build_state_from_widgets ci-dessus)
        # reflète exactement ce qui est à l'écran, quel que soit l'emplacement
        # du bouton. Plus de couplage à l'ordre du layout (ancien bug Maël).
        _snap = applied_commit(
            st.session_state, state,
            label=st.session_state.get("apply_label", "").strip(),
        )
        # P3.2 : le snapshot validé EST désormais current_run_state. On projette
        # l'état canonique vers les clés legacy partagées (sens unique). Garde
        # best-effort : ne doit jamais casser l'enregistrement.
        try:
            sync_legacy_projection(st.session_state)
        except Exception:  # noqa: BLE001
            pass
        st.toast("Configuration enregistrée — Supervision mise à jour.", icon="✅")
        # Persistance historique procédé (disque) + KPIs moteur FIGÉS au commit.
        # try/except : un échec de persistance ne doit JAMAIS casser l'enregistrement
        # session (la couche `applied`/Supervision est déjà validée ci-dessus).
        try:
            _fp = history_store.flat_params_from_snapshot(_snap)
            _report = build_report_from_flat_params(
                config=_fp["config"],
                screw_rpm=_fp["screw_rpm"],
                feed_g_per_min=_fp["feed_g_per_min"],
                bulk_density=_fp["bulk_density"],
                side_feeder_zone=_fp["side_feeder_zone"],
            )
            _record = history_store.make_record(_snap, _report)
            if history_store.append_run(_record):
                st.toast("Historique procédé mis à jour (persistant).", icon="🗂️")
            else:
                st.toast("Configuration identique au dernier enregistrement — pas de doublon.", icon="ℹ️")
        except Exception as _exc:  # noqa: BLE001 — persistance best-effort
            st.toast(f"Historique persistant indisponible : {_exc}", icon="⚠️")
with _label_col:
    st.text_input(
        t("settings.save.label"), value="", key="apply_label",
        placeholder=t("settings.save.placeholder"),
        label_visibility="collapsed",
    )
with _info_col:
    # `state` est déjà l'état reconstruit depuis les clés widget courantes :
    # le diff « modifications non enregistrées » est donc exact sans capture.
    _applied = get_applied(st.session_state)
    _history = get_history(st.session_state)
    _unsaved = has_unsaved_changes(st.session_state, state)
    _status_color = WARN if _unsaved else ACC
    _status_text = (
        t("settings.status.unsaved")
        if _unsaved and _applied
        else (t("settings.status.none")
              if _applied is None
              else t("settings.status.uptodate"))
    )
    _last_iso = _applied.timestamp_iso if _applied else "—"
    _last_label = (_applied.label if _applied and _applied.label else t("settings.status.no_label")) if _applied else ""
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};'
        f'border-left:4px solid {_status_color};border-radius:0.25rem;'
        f'padding:0.35rem 0.6rem;font-family:Consolas,monospace;'
        f'display:flex;gap:0.7rem;align-items:center;">'
        f'<span style="color:{_status_color};font-size:0.72rem;font-weight:700;'
        f'letter-spacing:0.06em;">{_status_text}</span>'
        f'<span style="color:{SUB};font-size:0.7rem;">'
        f'{t("settings.status.meta", iso=_last_iso, label=_last_label, n=len(_history))}</span>'
        f'</div>'
    )


# ===========================================================================
# Helpers HMI — tuiles compactes
# ===========================================================================
def hmi_tile_open(title: str) -> None:
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:0.3rem;'
        f'padding:0.45rem 0.7rem 0.6rem 0.7rem;margin-bottom:0.45rem;">'
        f'<div style="text-align:center;color:{SUB};font-size:0.66rem;'
        f'font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
        f'border-bottom:1px solid {BORDER};padding-bottom:0.2rem;margin-bottom:0.4rem;">'
        f'{title}</div></div>'
    )


def hmi_kv(label: str, value: str, unit: str = "", color: str = TEXT) -> str:
    """Mini bloc clé/valeur HMI (lecture)."""
    return (
        f'<div style="display:flex;align-items:baseline;gap:0.35rem;padding:0.2rem 0.4rem;'
        f'background:{LCD};border:1px solid {BORDER};border-radius:0.2rem;'
        f'font-family:Consolas,monospace;">'
        f'<span style="color:{SUB};font-size:0.66rem;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.04em;">{label}</span>'
        f'<span style="flex:1;text-align:right;color:{color};font-size:0.86rem;'
        f'font-weight:700;">{value}</span>'
        f'<span style="color:{SUB};font-size:0.7rem;">{unit}</span>'
        f'</div>'
    )


# ===========================================================================
# Synchronisation widgets édités → moteur AgentIndustrial (preview live)
# ===========================================================================
# NB : `state` est l'état dérivé des clés widget (build_state_from_widgets) et
# ne touche JAMAIS le snapshot validé. Il alimente l'aperçu agent IA (alertes,
# recos, score, cooling) sur les valeurs en cours d'édition.
cooling_model = compute_cooling(state)

_STATUS_DOT = {"ok": "🟢", "watch": "🟠", "overheat": "🔴"}
_STATUS_COLOR = {"ok": ACC, "watch": WARN, "overheat": CRIT}


# ===========================================================================
# Layout principal : pleine largeur (le Cooling Test opérateur a été retiré,
# fonctionnalité inexistante côté procédé réel — exigence manager 2026-05-20)
# ===========================================================================
col_left = st.container()

with col_left:
    # ─── Gouvernance thermique DÉRIVÉE — diagnostic auto zone la + chaude ─
    # Plus de « Pression alarme / Tolérance T° / T max avant froid » et plus
    # de zone sélectionnée opérateur : le diagnostic cible automatiquement
    # la zone calculée comme la plus chaude par le modèle thermique
    # (T = Tset + SME/Cp + kτ + corrections profil vis + cisaillement +
    # mixage/convoyage + viscosité matière).
    _gz = cooling_model.zones[cooling_model.hottest_zone]
    _lim_c = CRIT if _gz.status == "overheat" else (
        WARN if _gz.status == "watch" else ACC
    )
    st.html(
        f'<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.4rem;">'
        + hmi_kv(t("settings.kv.reg_band"), f"±{THERMAL_REG_BAND_C:.0f}", "°C")
        + hmi_kv(t("settings.kv.thermal_peak"), f"{_gz.zone}", "", _lim_c)
        + hmi_kv(t("settings.kv.ceiling"), f"{_gz.t_limit_C:.0f}", "°C", _lim_c)
        + hmi_kv(t("settings.kv.ceiling_src"),
                 _gz.limit_source.upper() if _gz.limit_source else "PROCÉDÉ", "")
        + hmi_kv(t("settings.kv.t_real"), f"{_gz.t_est_C:.0f}", "°C", _lim_c)
        + hmi_kv(t("settings.kv.dt_dissip"), f"+{_gz.dT_C:.0f}", "°C")
        + hmi_kv(t("settings.kv.instability"), f"{cooling_model.instability_index:.2f}", "",
                 ACC if cooling_model.instability_index < 0.5
                 else (WARN if cooling_model.instability_index < 0.7 else CRIT))
        + hmi_kv(t("settings.kv.torque"), f"{cooling_model.torque_load * 100:.0f}", "%",
                 ACC if cooling_model.torque_load < 0.85 else CRIT)
        + hmi_kv(t("settings.kv.model"), "T=Tset+SME/Cp+kτ + profil vis", "")
        + '</div>'
    )

    # ─── Bloc 1bis : PROFIL THERMIQUE EXTRUSION (Z1..Z8 + die) ───────────
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:0.3rem;'
        f'padding:0.45rem 0.7rem 0.2rem 0.7rem;margin-top:0.4rem;">'
        f'<div style="text-align:center;color:{SUB};font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid {BORDER};'
        f'padding-bottom:0.2rem;margin-bottom:0.35rem;">'
        f'{t("settings.block.thermal")}'
        f'</div></div>'
    )

    _PZ = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
    _t_cols = st.columns(8)
    for _zk, _c in zip(_PZ, _t_cols):
        with _c:
            st.number_input(
                _zk, min_value=0.0, max_value=400.0, step=5.0,
                key=f"th_{_zk}",
            )
    # État visuel + validation gradient (lecture cohérente du moteur R9/R10)
    _seq = [
        float(st.session_state.get(f"th_{z}", default_zone_target(z)))
        for z in _PZ
    ]
    _stat_cols = st.columns(8)
    for _i, (_zk, _c) in enumerate(zip(_PZ, _stat_cols)):
        zt = cooling_model.zones[_zk]
        dot = _STATUS_DOT[zt.status]
        _grad = _seq[_i] - _seq[_i - 1] if _i > 0 else 0.0
        _gcol = CRIT if _grad > 70 else (WARN if _grad > 45 else SUB)
        _gtxt = f"Δ{_grad:+.0f}" if _i > 0 else "entrée"
        with _c:
            # Manager 2026-06-09 : ces valeurs sont des estimations théoriques
            # avant compensation cooling, PAS des températures mesurées capteur.
            # Wording explicite « estimé » / « estimated » + tooltip.
            _t_lbl = t("settings.t_estimated_short")
            st.html(
                f'<div style="text-align:center;font-family:Consolas,monospace;'
                f'font-size:0.62rem;line-height:1.25;" '
                f'title="{t("settings.t_estimated_tooltip")}">'
                f'<div>{dot} <span style="color:{_STATUS_COLOR[zt.status]};">'
                f'{zt.t_est_C:.0f}°C {_t_lbl}</span></div>'
                f'<div style="color:{_gcol};">{_gtxt}</div></div>'
            )

    # Nombre de zones die + consignes die dynamiques.
    # Manager 2026-06-09 : 0 = filière absente (aucun champ DIE requis,
    # calculs filière-dépendants → « Non applicable »).
    _d1, _d2 = st.columns([1.1, 3.0])
    with _d1:
        st.selectbox(
            t("settings.n_die_zones"), options=[0, 1, 2, 3, 4],
            format_func=lambda n: (
                t("settings.die_zone_fmt_zero") if n == 0
                else (t("settings.die_zone_fmt_plural", n=n) if n > 1
                      else t("settings.die_zone_fmt", n=n))
            ),
            key="n_die_zones",
        )
    _ndie = safe_int(st.session_state.get("n_die_zones", 1), 1, 0, 4)
    _die_keys = ["die", "die2", "die3", "die4"][:_ndie]
    with _d2:
        _die_cols = st.columns(4)
        for _j in range(4):
            with _die_cols[_j]:
                if _j < _ndie:
                    st.number_input(
                        f"DIE {_j + 1}", min_value=0.0, max_value=400.0, step=5.0,
                        key=f"th_{_die_keys[_j]}",
                    )
                else:
                    st.html(
                        f'<div style="color:{SLOT};font-size:0.62rem;'
                        f'text-align:center;padding-top:1.4rem;">die {_j + 1}<br>—</div>'
                    )
    if _ndie == 0:
        # Pas de filière → aucun champ DIE actif, aucune validation gradient.
        st.html(
            f'<div style="font-family:Consolas,monospace;font-size:0.66rem;'
            f'color:{SUB};padding:0.15rem 0.3rem;">'
            f'{t("settings.die_zone_absent")}'
            f'</div>'
        )
    else:
        _die_vals = [
            float(st.session_state.get(f"th_{k}", default_zone_target(k)))
            for k in _die_keys
        ]
        _die_ok = all(
            _die_vals[i + 1] <= _die_vals[i] + 5.0 for i in range(len(_die_vals) - 1)
        )
        _die_c = ACC if _die_ok else WARN
        st.html(
            f'<div style="font-family:Consolas,monospace;font-size:0.66rem;'
            f'color:{_die_c};padding:0.15rem 0.3rem;">'
            f'Filière {_ndie} zone(s) · '
            + " → ".join(f"{v:.0f}°C" for v in _die_vals)
            + (' · ✓ rampe décroissante' if _die_ok
               else ' · ⚠ profil die non décroissant (cf. alertes IA)')
            + '</div>'
        )

    # ─── Bloc 2 : Feeders Material (1..5) — type, ρ, α, position ──────────
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:0.3rem;'
        f'padding:0.45rem 0.7rem 0.2rem 0.7rem;margin-top:0.2rem;">'
        f'<div style="text-align:center;color:{SUB};font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid {BORDER};'
        f'padding-bottom:0.2rem;margin-bottom:0.35rem;">'
        f'{t("settings.block.feeders")}'
        f'</div></div>'
    )

    # Grille 5 feeders × 5 colonnes (id + 4 réglages).
    # Widgets en KEY-ONLY : aucune valeur/index passé → Streamlit pilote chaque
    # widget par sa clé session_state (hydratée par seed_editing_keys). `state`
    # n'est jamais muté ici, il sert seulement à connaître l'état actif courant
    # (disabled). Les clés partagées sont projetées en fin de page.
    _mat_keys = list(MATERIAL_TYPES.keys())
    _mat_labels = {k: MATERIAL_TYPES[k].label_fr for k in _mat_keys}
    for f in state.feeders:
        fid = f.feeder_id
        _enabled = bool(st.session_state[f"fd_en_{fid}"])
        en_col, lbl_col, mat_col, dens_col, alpha_col, pos_col = st.columns(
            [0.6, 1.3, 1.4, 1.1, 1.2, 1.0]
        )
        with en_col:
            st.toggle(
                f"#{fid}", key=f"fd_en_{fid}",
                help=t("settings.feeder.toggle_help", fid=fid),
            )
        with lbl_col:
            st.text_input(
                t("settings.feeder.label"), key=f"fd_lbl_{fid}",
                placeholder=f"Feeder {fid}", label_visibility="collapsed",
            )
        with mat_col:
            st.selectbox(
                t("settings.feeder.type"), options=_mat_keys,
                format_func=lambda k: _mat_labels[k],
                key=f"fd_mat_{fid}",
                disabled=not _enabled, label_visibility="collapsed",
            )
        with dens_col:
            # Label visible avec unité (manager 2026-06-09 : pas seulement tooltip).
            st.number_input(
                t("settings.feeder.dens_label"),
                min_value=0.0001, max_value=10.0,
                step=0.05, format="%.3f",
                key=f"fd_dens_{fid}",
                disabled=not _enabled,
                help=t("settings.feeder.dens_help"),
            )
        with alpha_col:
            st.number_input(
                t("settings.feeder.alpha_label"),
                min_value=0.0, max_value=1.0e-1,
                step=1.0e-5, format="%.6f",
                key=f"fd_alpha_{fid}",
                disabled=not _enabled,
                help=t("settings.feeder.alpha_help"),
            )
        with pos_col:
            st.selectbox(
                t("settings.feeder.pos"), options=list(FEEDER_POSITIONS),
                key=f"fd_pos_{fid}", disabled=not _enabled,
                label_visibility="collapsed",
            )

    # ─── Bloc 2bis : ÉTALONNAGE FEEDERS (multi-feeder : RPM × coeff → débit) ──
    with st.expander(t("settings.expander.feedcal"), expanded=False):
        render_multi_feeder_calibration(st, state.feeders)

    # ─── Bloc 3 : SME / Mass Flow par feeder + global ─────────────────────
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:0.3rem;'
        f'padding:0.45rem 0.7rem 0.2rem 0.7rem;margin-top:0.5rem;">'
        f'<div style="text-align:center;color:{SUB};font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid {BORDER};'
        f'padding-bottom:0.2rem;margin-bottom:0.35rem;">'
        f'{t("settings.block.sme")}'
        f'</div></div>'
    )
    flow_cols = st.columns(6)
    for i, f in enumerate(state.feeders):
        with flow_cols[i]:
            _fid = f.feeder_id
            _fid_enabled = bool(st.session_state[f"fd_en_{_fid}"])
            # Manager 2026-06-09 : si l'étalonnage feeder #fid est renseigné,
            # le widget SME est VERROUILLÉ — une seule source de vérité pour le
            # débit (l'étalonnage prime, cf. editing_state.build_state_from_widgets).
            # L'opérateur voit la valeur étalonnée sous le widget (lecture seule).
            _fid_calibrated = feeder_is_calibrated(st.session_state, _fid)
            st.number_input(
                f"#{_fid} {t('settings.feeder.flow_unit')}",
                min_value=0.0, max_value=2000.0,
                step=1.0, key=f"fd_flow_{_fid}",
                disabled=(not _fid_enabled) or _fid_calibrated,
                help=(
                    t("settings.feeder.flow_locked_by_calibration")
                    if _fid_calibrated else None
                ),
            )
            if _fid_calibrated and _fid_enabled:
                _calib_g_min = feeder_calibrated_g_per_min(
                    st.session_state, _fid,
                ) or 0.0
                st.caption(t(
                    "settings.feeder.flow_from_calibration",
                    v=f"{_calib_g_min:.2f}",
                ))

    # ─── Bloc 3bis : PROPRIÉTÉS MATIÈRE ÉTENDUES par feeder ──────────────
    # (Exigence manager 2026-05-20 — l'IA doit avoir les données polymère,
    # T° dégradation, ATG/TGA, viscosité, thermomécanique pour produire des
    # recommandations pertinentes.)
    with st.expander(t("settings.expander.matprops"), expanded=False):
        st.caption(t("settings.matprops.caption"))
        for f in state.feeders:
            if not f.enabled:
                continue
            fid = f.feeder_id
            st.markdown(f"**Feeder #{fid} — {f.display_name()}**")
            p1, p2, p3, p4, p5, p6 = st.columns(6)
            # Widgets key-only : pilotés par session_state, jamais par `value=`.
            # `f` (issu de build_state_from_widgets) reflète déjà ces clés et
            # sert uniquement aux libellés/lectures effectives ci-dessous.
            with p1:
                st.text_input(
                    t("settings.mat.polymer"), key=f"fd_poly_{fid}",
                    placeholder="PVDF, PEO, LFP…",
                )
            with p2:
                st.number_input(
                    t("settings.mat.tdeg"),
                    min_value=0.0, max_value=600.0,
                    step=5.0, key=f"fd_tdeg_{fid}",
                    help=t("settings.mat.tdeg_help"),
                )
            with p3:
                st.number_input(
                    t("settings.mat.tga"),
                    min_value=0.0, max_value=600.0,
                    step=5.0, key=f"fd_tga_{fid}",
                    help=t("settings.mat.tga_help"),
                )
            with p4:
                st.number_input(
                    t("settings.mat.visc"),
                    min_value=0.0, max_value=1e6,
                    step=10.0, key=f"fd_visc_{fid}",
                    help=t("settings.mat.visc_help"),
                )
            with p5:
                st.number_input(
                    t("settings.mat.tmelt"),
                    min_value=0.0, max_value=600.0,
                    step=5.0, key=f"fd_tmelt_{fid}",
                )
            with p6:
                st.number_input(
                    t("settings.mat.tglass"),
                    min_value=-200.0, max_value=600.0,
                    step=5.0, key=f"fd_tglass_{fid}",
                )
            # Lecture effective utilisée par l'IA (traçabilité).
            _tmax_eff = f.effective_t_max_C()
            st.caption(
                f"→ Borne haute effective IA : **{_tmax_eff:.0f} °C** "
                f"(source : "
                + ("T° dégradation opérateur"
                   if f.t_degradation_C and f.t_degradation_C > 0
                   else ("ATG onset" if f.tga_onset_C and f.tga_onset_C > 0
                         else f"famille matière « {f.material.label_fr} »"))
                + f") · facteur viscosité ×{f.viscosity_factor():.2f}"
            )

    # Vitesse vis + torque + pressure (V2 placeholders) — widgets key-only.
    with flow_cols[5]:
        st.number_input(
            t("settings.vis_rpm"), min_value=1.0, max_value=3000.0,
            step=10.0, key="ni_rpm_hmi",
        )

    tq_cols = st.columns([1, 1, 2])
    with tq_cols[0]:
        st.number_input(
            t("settings.torque_pct"), min_value=0.0, max_value=100.0,
            step=1.0, key="ni_tq_v2",
            help=t("settings.torque_help"),
        )
    with tq_cols[1]:
        st.number_input(
            t("settings.pdie"), min_value=0.0, max_value=400.0,
            step=1.0, key="ni_pr_v2",
            help=t("settings.pdie_help"),
        )
    with tq_cols[2]:
        # Bilan flux compact (live)
        _phase_flows = mass_flow_by_phase(state.feeders)
        _total = sum(_phase_flows.values())
        st.html(
            f'<div style="display:flex;gap:0.3rem;flex-wrap:wrap;">'
            + hmi_kv(t("settings.kv.total"), f"{_total:.0f}", "g/min", ACC)
            + hmi_kv(t("settings.kv.solid"), f"{_phase_flows['solid']:.0f}", "g/min")
            + hmi_kv(t("settings.kv.liquid"), f"{_phase_flows['liquid']:.0f}", "g/min")
            + hmi_kv(t("settings.kv.gas"), f"{_phase_flows['gas']:.0f}", "g/min")
            + '</div>'
        )


# ===========================================================================
# Évaluation Agent IA (rule-based explicable)
# ===========================================================================
# `state` reflète déjà toutes les clés widget (consignes Z*, feeders, rpm…) :
# le rapport et les recos portent sur les valeurs HMI courantes.
report: AgentReport = evaluate(state)
recos: list[Recommendation] = build_recommendations(state, report.alerts)

# KPI strip global (FF, RT, SME, n_alert, score)
k = state.kpis
_state_color = {"STABLE": ACC, "SURVEILLER": WARN, "CRITIQUE": CRIT}.get(report.state, ACC)

st.html(
    f'<div style="display:flex;gap:0.4rem;margin-top:0.5rem;flex-wrap:wrap;">'
    + hmi_kv(t("settings.kv.fill_factor"), f"{k.fill_factor*100:.1f}", "%",
             ACC if 0.30 <= k.fill_factor <= 0.55 else WARN)
    + hmi_kv(t("settings.kv.residence"), f"{k.residence_time_s:.1f}", "s")
    + hmi_kv("SME", f"{k.sme_kwh_per_kg:.2f}", "kWh/kg",
             ACC if k.sme_kwh_per_kg < 0.30 else WARN)
    + hmi_kv(t("settings.kv.free_vol"), f"{k.free_volume_cm3:.1f}", "cm³")
    + hmi_kv(t("settings.kv.elements"), f"{k.n_elements:.0f}", "")
    + hmi_kv(t("settings.kv.archetype"), k.profile_archetype or "—", "")
    + hmi_kv(t("settings.kv.alerts"), f"{len(report.alerts)}", "",
             ACC if not report.alerts else (WARN if len(report.alerts) < 3 else CRIT))
    + hmi_kv(t("settings.kv.score"), f"{report.risk_score}", "/100", _state_color)
    + hmi_kv(t("settings.kv.state"), report.state, "", _state_color)
    + '</div>'
)


# ===========================================================================
# Alertes + Recommandations format opérateur (4 lignes)
# ===========================================================================
def _short_cause(alert: Alert) -> str:
    """Réduit la description de l'alerte à une cause courte (1 phrase max)."""
    if not alert.description:
        return alert.evidence
    first = alert.description.split(". ")[0].strip(" .")
    if len(first) > 110:
        first = first[:107] + "…"
    return first


def _pair_alert_reco(
    alerts: list[Alert], recs: list[Recommendation],
) -> list[tuple[Alert, Recommendation | None]]:
    """Associe chaque alerte à sa première reco liée (ordre sévérité)."""
    sev_order = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    sorted_alerts = sorted(alerts, key=lambda a: sev_order.get(a.severity, 9))
    by_code: dict[str, list[Recommendation]] = {}
    for r in recs:
        by_code.setdefault(r.linked_alert_code, []).append(r)
    out: list[tuple[Alert, Recommendation | None]] = []
    for a in sorted_alerts:
        bucket = by_code.get(a.code, [])
        out.append((a, bucket[0] if bucket else None))
    return out


def _op_card_html(alert: Alert, reco: Recommendation | None) -> str:
    """Carte opérateur 4 lignes : ALERTE / CAUSE / ACTION / IMPACT."""
    sev = alert.severity
    border = {"critical": CRIT, "warning": WARN, "info": "#3B82F6"}.get(sev, SUB)
    chip_bg = {"critical": "#3b1212", "warning": "#3b2c0a", "info": "#0f1d3b"}.get(sev, "#1f2937")
    target = alert.target or "—"
    cause = _short_cause(alert)
    action = reco.action if reco else "—"
    impact = reco.delta_label if reco else "—"
    return (
        f'<div style="background:{PANEL};border:1px solid {BORDER};'
        f'border-left:4px solid {border};border-radius:0.3rem;'
        f'padding:0.55rem 0.8rem;margin-bottom:0.5rem;font-family:Consolas,monospace;">'
        # Ligne 1 — ALERTE
        f'<div style="display:flex;align-items:center;gap:0.5rem;">'
        f'<span style="background:{border};color:#0B0F14;font-weight:700;font-size:0.66rem;'
        f'padding:0.1rem 0.5rem;border-radius:0.2rem;letter-spacing:0.06em;">'
        f'{sev.upper()}</span>'
        f'<span style="background:{chip_bg};color:{border};font-size:0.66rem;'
        f'border:1px solid {border};padding:0.1rem 0.45rem;border-radius:0.2rem;'
        f'font-weight:600;">{target}</span>'
        f'</div>'
        # Lignes 2-5 — clé : valeur
        f'<table style="width:100%;margin-top:0.45rem;border-collapse:collapse;">'
        f'<tr><td style="color:{border};font-size:0.66rem;font-weight:700;letter-spacing:0.06em;'
        f'padding:0.1rem 0.5rem 0.1rem 0;width:5.5rem;vertical-align:top;">ALERTE</td>'
        f'<td style="color:{TEXT};font-size:0.86rem;font-weight:600;padding:0.1rem 0;">'
        f'{alert.title}</td></tr>'
        f'<tr><td style="color:{SUB};font-size:0.66rem;font-weight:700;letter-spacing:0.06em;'
        f'padding:0.1rem 0.5rem 0.1rem 0;vertical-align:top;">CAUSE</td>'
        f'<td style="color:{TEXT};font-size:0.8rem;line-height:1.4;padding:0.1rem 0;">'
        f'{cause}</td></tr>'
        f'<tr><td style="color:{ACC};font-size:0.66rem;font-weight:700;letter-spacing:0.06em;'
        f'padding:0.1rem 0.5rem 0.1rem 0;vertical-align:top;">ACTION</td>'
        f'<td style="color:{TEXT};font-size:0.82rem;font-weight:600;padding:0.1rem 0;">'
        f'{action}</td></tr>'
        f'<tr><td style="color:{ACC};font-size:0.66rem;font-weight:700;letter-spacing:0.06em;'
        f'padding:0.1rem 0.5rem 0.1rem 0;vertical-align:top;">IMPACT</td>'
        f'<td style="color:#bbf7d0;font-size:0.82rem;font-weight:700;'
        f'font-family:Consolas,monospace;padding:0.1rem 0;">{impact}</td></tr>'
        f'</table>'
        f'<div style="text-align:right;color:{SUB};font-size:0.66rem;margin-top:0.25rem;">'
        f'evidence · {alert.evidence}</div>'
        f'</div>'
    )


# Section alertes / recommandations
st.html(
    f'<div style="margin-top:0.7rem;display:flex;align-items:center;gap:0.5rem;">'
    f'<div style="background:{_state_color};color:#0B0F14;font-weight:700;'
    f'font-size:0.74rem;padding:0.2rem 0.6rem;border-radius:0.2rem;'
    f'letter-spacing:0.06em;">AGENT IA · {report.state}</div>'
    f'<div style="color:{SUB};font-size:0.78rem;">{report.diagnostic}</div>'
    f'</div>'
)

pairs = _pair_alert_reco(report.alerts, recos)
if not pairs:
    st.html(
        f'<div style="background:{PANEL};border:1px solid {BORDER};border-left:4px solid {ACC};'
        f'border-radius:0.3rem;padding:0.6rem 0.9rem;margin-top:0.4rem;color:#bbf7d0;'
        f'font-family:Consolas,monospace;font-size:0.9rem;">'
        f'{t("settings.alerts.none")}</div>'
    )
else:
    # 2 colonnes opérateur (carte compacte)
    cards_html = "".join(_op_card_html(a, r) for a, r in pairs)
    st.html(
        f'<div style="column-count:2;column-gap:0.6rem;margin-top:0.4rem;">{cards_html}</div>'
    )


# ===========================================================================
# Réglages IA détaillés — repliés (préservés mais non intrusifs)
# ===========================================================================
with st.expander(t("settings.expander.advanced"), expanded=False):
    st.markdown(f"**{t('settings.adv.thresholds')}**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.session_state["th_stable"] = st.slider(
            t("settings.adv.th_stable"), 50, 100, int(st.session_state["th_stable"]), key="sl_th_stable",
        )
    with c2:
        st.session_state["th_critical"] = st.slider(
            t("settings.adv.th_critical"), 0, 99, int(st.session_state["th_critical"]), key="sl_th_crit",
        )
    with c3:
        st.session_state["th_proba_stable"] = st.slider(
            t("settings.adv.th_pstable"), 0.0, 1.0,
            float(st.session_state["th_proba_stable"]), 0.05, key="sl_th_pstab",
        )
    with c4:
        st.session_state["th_proba_critical"] = st.slider(
            t("settings.adv.th_pcritical"), 0.0, 1.0,
            float(st.session_state["th_proba_critical"]), 0.05, key="sl_th_pcrit",
        )
    if st.session_state["th_critical"] >= st.session_state["th_stable"]:
        st.warning(t("settings.adv.warn_stable"))
    if st.session_state["th_proba_critical"] >= st.session_state["th_proba_stable"]:
        st.warning(t("settings.adv.warn_pstable"))

    st.divider()
    st.markdown(f"**{t('settings.adv.monitored')}**")
    ALL_SENSORS = [
        "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
        "DIE", "CastFilmBody", "CastFilmP1", "CastFilmP2",
    ]
    m1, m2 = st.columns([3, 1])
    with m1:
        st.session_state["monitored_zones"] = st.multiselect(
            t("settings.adv.sensors"),
            options=ALL_SENSORS,
            default=list(st.session_state["monitored_zones"]),
            key="ms_zones",
        )
    with m2:
        st.session_state["analysis_hz"] = st.number_input(
            t("settings.adv.hz"), 0.1, 10.0,
            float(st.session_state["analysis_hz"]), 0.1, key="ni_hz",
        )

    st.divider()
    st.markdown(f"**{t('settings.adv.targets')}**")
    q1, q2, q3 = st.columns(3)
    with q1:
        _ff_low = int(st.session_state["ff_target_low"])
        _ff_high = int(st.session_state["ff_target_high"])
        st.session_state["ff_target_low"], st.session_state["ff_target_high"] = st.slider(
            t("settings.adv.ff_target"), 0, 100, (_ff_low, _ff_high), 5, key="sl_ff_target",
        )
    with q2:
        _curr_count = safe_int(st.session_state.get("target_screw_count", 40), 40)
        if _curr_count not in (25, 30, 40):
            _curr_count = 40  # défaut Rondol
        st.session_state["target_screw_count"] = st.radio(
            t("settings.adv.screw_target"), [25, 30, 40],
            index=[25, 30, 40].index(_curr_count),
            format_func=lambda v: t("settings.adv.elements_fmt", v=v),
            key="rd_target_count", horizontal=True,
        )
    with q3:
        # Side feeder zone : source UNIQUE = feeder #2 (toggle + position dans
        # la grille Feeders ci-dessus). Plus de sélecteur concurrent ici — on
        # affiche en lecture seule la zone dérivée, pour éviter une seconde
        # propriété de la même donnée (reconception state 2026-05-21).
        _sf2 = state.feeders[1] if len(state.feeders) > 1 else None
        _sf_txt = (
            f"Z{_sf2.position[1:]}"
            if _sf2 and _sf2.enabled and _sf2.position.startswith("Z")
            else "Désactivé"
        )
        st.markdown(f"**{t('settings.adv.sf_zone')}**")
        st.caption(t("settings.adv.sf_caption", z=_sf_txt))


with st.expander(t("settings.expander.svm"), expanded=False):
    @st.cache_data(show_spinner=False)
    def load_metrics():
        if METRICS_PATH.exists():
            with open(METRICS_PATH) as f:
                return json.load(f)
        return None

    @st.cache_data(show_spinner=False)
    def load_threshold_df():
        if THRESHOLD_PATH.exists():
            return pd.read_csv(THRESHOLD_PATH)
        return pd.DataFrame()

    @st.cache_data(show_spinner=False)
    def load_feat_imp():
        if FEAT_IMP_PATH.exists():
            df = pd.read_csv(FEAT_IMP_PATH)
            if "Unnamed: 0" in df.columns:
                df = df.rename(columns={"Unnamed: 0": "feature"})
            return df
        return None

    metrics = load_metrics()
    thresh_df = load_threshold_df()
    feat_imp = load_feat_imp()

    if metrics is not None:
        svm_test = metrics["test"].get("SVM", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(t("settings.svm.algo"), "SVM (RBF)")
        c2.metric(t("settings.svm.window"), "60 s")
        c3.metric(t("settings.svm.threshold"), "80 / 100")
        c4.metric("AUC-ROC (test)", f"{svm_test.get('roc_auc', 0):.3f}")
        c5.metric("F1 macro (test)", f"{svm_test.get('f1_macro', 0):.3f}")
        st.caption(
            f"Train : {metrics.get('n_train', 0)} fenêtres ({metrics.get('n_runs_train', 0)} runs) · "
            f"Test : {metrics.get('n_test', 0)} fenêtres ({metrics.get('n_runs_test', 0)} runs) · "
            f"Split : {metrics.get('split_method', 'N/A')}"
        )
        rows = []
        for m in metrics.get("cv", []):
            name = m["model"]
            test = metrics["test"].get(name, {})
            rows.append({
                "Modèle": name,
                "CV F1 macro": f"{m.get('cv_f1_macro_mean', 0):.3f} ± {m.get('cv_f1_macro_std', 0):.3f}",
                "CV AUC":      f"{m.get('cv_roc_auc_mean', 0):.3f} ± {m.get('cv_roc_auc_std', 0):.3f}",
                "Test F1":     f"{test.get('f1_macro', 0):.3f}",
                "Test AUC":    f"{test.get('roc_auc', 0):.3f}",
            })
        if rows:
            comp_df = pd.DataFrame(rows)

            def _highlight_svm(row):
                if row["Modèle"] == "SVM":
                    return ["background-color: #d4edda"] * len(row)
                return [""] * len(row)

            st.dataframe(
                comp_df.style.apply(_highlight_svm, axis=1),
                use_container_width=True, hide_index=True,
            )
    else:
        st.info(t("settings.svm.metrics_na"))

    if not thresh_df.empty:
        st.markdown(f"**{t('settings.svm.calibration')}**")
        disp_cols = [c for c in ["threshold", "cv_f1_unstable_mean",
                                  "cv_precision_unstable_mean", "cv_recall_unstable_mean",
                                  "cv_roc_auc_mean", "pct_stable"] if c in thresh_df.columns]
        if disp_cols:
            thresh_disp = thresh_df[disp_cols].copy().round(3)
            st.dataframe(thresh_disp, use_container_width=True, hide_index=True)

    if feat_imp is not None and "feature" in feat_imp.columns and "importance" in feat_imp.columns:
        st.markdown(f"**{t('settings.svm.top15')}**")
        top15 = feat_imp.nlargest(15, "importance")[["feature", "importance"]].copy()
        top15["importance"] = top15["importance"].round(4)
        top15.columns = ["Feature", "Importance"]
        st.dataframe(top15, use_container_width=True, hide_index=True)

    st.markdown(f"**{t('settings.svm.pipeline')}**")
    st.code(
        """Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler',  StandardScaler()),
    ('clf',     SVC(kernel='rbf', C=1.0, gamma='scale',
                    class_weight='balanced',
                    probability=True, random_state=42)),
])

Fenêtre : 60 s · Pas : 30 s · Features : 87
Split entraînement : GroupShuffleSplit(run_id)
Cible métier : détection instabilité thermique procédé SSB""",
        language="python",
    )


# ===========================================================================
# Pied de page HMI — projection vers les clés legacy partagées
# ===========================================================================
# Projection (lecture seule pour les consommateurs legacy) de l'état édité vers
# screw_rpm / feeder_g_per_min / bulk_density / side_feeder_zone. Ce ne sont PAS
# des sources concurrentes : elles dérivent de `state` (clés widget). Lues par
# Profile et par le panneau de recommandation vis de Supervision (hors snapshot).
project_shared_keys(st.session_state, state)

# Sauvegarde centrale persistante de la config opérateur (session + disque) —
# relue par toutes les pages, survit à la navigation et au refresh navigateur.
try:
    capture_operator_state(st.session_state)
except Exception:  # noqa: BLE001 — la persistance ne doit jamais casser l'UI
    pass
