"""
Supervision.py — Supervision procédé Rondol — Version finale stable.

Modèle : RandomForest w60 (augmenté)  |  Seuil : 80  |  Données : Essais Avril 2026
Lancement : streamlit run app/Supervision.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Module logique vis (ne pas modifier — uniquement consommé pour la
# recommandation de longueur 25/30/40 affichée sur Home).
ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))
APP_FOR_IMPORTS = Path(__file__).resolve().parent
if str(APP_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(APP_FOR_IMPORTS))

from screw_logic import (  # noqa: E402
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    TIP_PART1_POS,
    base_type as screw_base_type,
    enforce_tip_constraint as screw_enforce_tip,
    fill_factor_average as screw_ff_avg,
    is_part2 as screw_is_part2,
    new_empty_configuration as screw_new_empty,
    position_to_zone as screw_pos_to_zone,
    zone_residence_times as screw_zone_rt,
)
from screw_render import (  # noqa: E402
    analyze_profile as screw_analyze_profile,
    analyze_systemic as screw_analyze_systemic,
    build_decision_html as screw_build_decision_html,
    build_decision_summary_html as screw_build_decision_summary_html,
    build_systemic_html as screw_build_systemic_html,
    compute_recommendations as screw_compute_recommendations,
    recommend_element_count as screw_recommend_count,
)

# Moteur AgentIndustrial_v1 — même état procédé que Settings (synchronisé via
# session_state) : Supervision affiche les recos IA / score / alertes /
# cooling pilotés par la page Settings, pas un second moteur divergent.
from AgentIndustrial_v1.core.state_sync import state_from_session  # noqa: E402
# P3.4 : config opérateur via current_run_state (jamais via le dataset ML demo).
from run_state_adapter import (  # noqa: E402
    build as build_crs,
    build_moteur_inputs_from_current_run_state,
)
from operator_store import restore_operator_state  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate as agent_evaluate  # noqa: E402
from AgentIndustrial_v1.core.recommendations import (  # noqa: E402
    build_recommendations as agent_build_recos,
)
from AgentIndustrial_v1.core.cooling import (  # noqa: E402
    compute_cooling as agent_compute_cooling,
)

# i18n — sélecteur de langue + traduction du chrome (B1).
from rondol_i18n import current_lang, language_selector, t  # noqa: E402

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH   = ROOT / "models" / "RandomForest_w60_augmented.joblib"
DATASET_PATH = ROOT / "data" / "features" / "dataset_ml_w60.csv"
LOGO_PATH    = Path(__file__).resolve().parent / "assets" / "rondol_logo.png"
# Évalué une seule fois au chargement du module — jamais réévalué entre renders
_LOGO_EXISTS = LOGO_PATH.exists()

THRESHOLD = 80

# ---------------------------------------------------------------------------
# Configuration page  (AVANT tout autre appel Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=t("page.home.title"),
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Couleur d'accent Rondol (bandeau HMI vert)
RONDOL_GREEN = "#4CAF50"

# ---------------------------------------------------------------------------
# CSS global — st.html() : aucun unsafe_allow_html, bloc statique immuable
# ---------------------------------------------------------------------------
st.html("""
<style>
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:#0B0F14!important; }
.block-container
    { padding-top:0.5rem!important; padding-left:1.4rem!important;
      padding-right:1.4rem!important; max-width:100%!important; }
header[data-testid="stHeader"]
    { background:transparent!important; height:0!important; }
[data-testid="stSidebar"]
    { background-color:#0D1117!important; border-right:1px solid #1F2937!important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div
    { color:#9CA3AF!important; }
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0D1117}
::-webkit-scrollbar-thumb{background:#374151;border-radius:3px}
[data-testid="stVegaLiteChart"]>div
    { background:transparent!important; }
</style>
""")

# ---------------------------------------------------------------------------
# Palette constantes
# ---------------------------------------------------------------------------
BG    = "#0B0F14"
CARD  = "#111827"
BORD  = "#1F2937"
TEXT  = "#F9FAFB"
SUB   = "#9CA3AF"
MUTED = "#374151"
CYAN  = "#06B6D4"

# Nombre fixe de slots recommandations — NE PAS MODIFIER
_N_RECOS = 5

# ---------------------------------------------------------------------------
# Logique métier — INCHANGÉE
# ---------------------------------------------------------------------------
def classify_state(score: float, proba_stable: float) -> str:
    if score >= THRESHOLD and proba_stable >= 0.70:
        return "STABLE"
    if score < 65 or proba_stable < 0.40:
        return "CRITIQUE"
    return "SURVEILLER"


# Chaque état a exactement _N_RECOS=5 tuples.
# Les tuples ("", "") sont des placeholders invisibles.
# Règle : NE JAMAIS changer ce nombre — cela rendrait la structure DOM instable.
# i18n S2-bis : libellés/sous-titres/impacts via les clés home.state.* déjà
# présentes dans rondol_i18n ; recos opérateur par état via home.reco.<état>.<i>.
# Structure inchangée : exactement 5 tuples par état (DOM stable).
def _state_cfg() -> dict:
    def _recos(state_key: str, n_filled: int) -> list[tuple[str, str]]:
        out = [
            (t(f"home.reco.{state_key}.{i}.t"), t(f"home.reco.{state_key}.{i}.d"))
            for i in range(1, n_filled + 1)
        ]
        while len(out) < _N_RECOS:
            out.append(("", ""))
        return out

    return {
        "STABLE": {
            "label": t("home.state.STABLE.label"),
            "sub": t("home.state.STABLE.sub"),
            "impact": t("home.state.STABLE.impact"),
            "icon": "✦", "acc": "#10B981",
            "recos": _recos("STABLE", 3),
        },
        "SURVEILLER": {
            "label": t("home.state.SURVEILLER.label"),
            "sub": t("home.state.SURVEILLER.sub"),
            "impact": t("home.state.SURVEILLER.impact"),
            "icon": "▲", "acc": "#F59E0B",
            "recos": _recos("SURVEILLER", 4),
        },
        "CRITIQUE": {
            "label": t("home.state.CRITIQUE.label"),
            "sub": t("home.state.CRITIQUE.sub"),
            "impact": t("home.state.CRITIQUE.impact"),
            "icon": "■", "acc": "#EF4444",
            "recos": _recos("CRITIQUE", 4),
        },
    }


STATE_CFG = _state_cfg()

# ---------------------------------------------------------------------------
# Fonctions d'analyse — INCHANGÉES
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data(show_spinner=False)
def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    meta = {"run_id", "window_start", "window_end", "n_samples",
            "stability_score", "is_stable", "target_horizon_sec",
            "run_duration_min", "bad_run"}
    return [c for c in df.columns if c not in meta]


def top_unstable_sensors(row: pd.Series, fcols: list[str], n: int = 5) -> list[dict]:
    s = {}
    for col in fcols:
        if col.endswith("_std"):
            v = row.get(col, np.nan)
            if not np.isnan(v):
                s[col[:-4]] = v
    out = []
    for sensor, std in sorted(s.items(), key=lambda x: x[1], reverse=True)[:n]:
        out.append({"sensor": sensor, "std": std,
                    "slope": row.get(f"{sensor}_slope", np.nan)})
    # Toujours exactement n éléments — structure DOM stable
    while len(out) < n:
        out.append({"sensor": "—", "std": 0.0, "slope": np.nan})
    return out


def _badge_sen(std: float) -> str:
    if std < 0.5:
        return "OK"
    if std < 1.5:
        return "WATCH"
    return "ALERT"


# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------
model     = load_model()
df_all    = load_dataset()
FCOLS     = get_feature_cols(df_all)
good_runs = df_all[df_all["bad_run"] == 0]
run_ids   = sorted(good_runs["run_id"].unique())

# ---------------------------------------------------------------------------
# Sidebar — composants natifs, zéro unsafe_allow_html
# ---------------------------------------------------------------------------
with st.sidebar:
    language_selector()
    st.divider()
    if _LOGO_EXISTS:
        st.image(str(LOGO_PATH), width=145)
    else:
        st.markdown("**RONDOL**")
    st.caption(t("common.extruder"))
    st.divider()

    # Section CLAIREMENT étiquetée : dataset ML de référence (essais avril,
    # modèle de dérive/stabilité) — PAS la configuration opérateur en service.
    # L'état opérateur vivant = snapshot validé (bandeau ÉTAT OPÉRATEUR ACTIF en
    # haut de page), source de vérité des KPIs procédé / recos agent.
    st.markdown("##### " + t("home.sidebar.ml_section"))
    st.caption(t("home.sidebar.run_is_ml_ref"))
    selected_run = st.selectbox(
        t("home.sidebar.run"),
        options=run_ids,
        index=len(run_ids) - 1,
        format_func=lambda r: f"Run #{r}",
        key="sb_run",
    )
    run_df    = good_runs[good_runs["run_id"] == selected_run].sort_values("window_end")
    n_windows = len(run_df)

    # Garde session-state : si le run change vers un run plus court,
    # la valeur stockée peut dépasser le nouveau max → ValueError Streamlit.
    # On clamp AVANT la création du widget. `value=` et `key=` ensemble lèvent
    # un warning quand session_state existe → on initialise via session_state.
    if "sl_win" not in st.session_state:
        st.session_state["sl_win"] = n_windows
    elif st.session_state["sl_win"] > n_windows:
        st.session_state["sl_win"] = n_windows

    win_idx = st.slider(
        t("home.sidebar.window"),
        min_value=1,
        max_value=n_windows,
        format=t("home.sidebar.window_fmt"),
        key="sl_win",
    )
    st.divider()
    st.caption(t("home.sidebar.model", th=THRESHOLD))
    st.caption(t("home.sidebar.trials"))

# ---------------------------------------------------------------------------
# Inférence — INCHANGÉE
# ---------------------------------------------------------------------------
current_row  = run_df.iloc[win_idx - 1]
X            = pd.DataFrame([current_row[FCOLS]])
proba        = model.predict_proba(X)[0]
proba_stable = float(proba[1])
score        = float(current_row["stability_score"])
state        = classify_state(score, proba_stable)
cfg          = STATE_CFG[state]

run_start = run_df["window_start"].min()
run_dur   = float(current_row["run_duration_min"])
win_end   = current_row["window_end"]
win_str   = win_end.strftime("%H:%M:%S") if hasattr(win_end, "strftime") else str(win_end)
run_str   = run_start.strftime("%d/%m %H:%M") if hasattr(run_start, "strftime") else str(run_start)

unstable   = top_unstable_sensors(current_row, FCOLS, n=5)
top_sensor = unstable[0]["sensor"]
top_std    = unstable[0]["std"]

delta     = score - THRESHOLD
delta_str = f"{delta:+.1f} {t('home.kpi.vs_threshold')}"
p_col     = "#10B981" if proba_stable >= 0.70 else ("#EF4444" if proba_stable < 0.40 else SUB)

# ---------------------------------------------------------------------------
# Texte diagnostic — markdown pur, sans HTML ni unsafe_allow_html
# ---------------------------------------------------------------------------
# i18n S2-bis : diagnostic par état via home.expl.<état> (FR/EN).
expl = t(
    f"home.expl.{state}",
    sensor=top_sensor, std=f"{top_std:.3f}",
    score=f"{score:.1f}", th=THRESHOLD,
)

# ===========================================================================
#  RENDU — Streamlit natif uniquement
#  Règle absolue : même nombre de composants à chaque render, quels que soient
#  l'état (STABLE/SURVEILLER/CRITIQUE), le run et la fenêtre sélectionnés.
# ===========================================================================

# ── Bandeau vert HMI Rondol ───────────────────────────────────────────────────
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>{t("home.banner.left")}</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">{t("home.banner.right")}</span>'
    f'</div>'
)

# ── ÉTAT OPÉRATEUR ACTIF — source de vérité unique = snapshot Supabase réparé ─
# Migration/réparation déterministe AVANT toute lecture de l'état opérateur : un
# snapshot durable dégénéré (ancien build) est réparé + réécrit dans Supabase,
# puis posé en session. Le bandeau ci-dessous rend VISUELLEMENT ÉVIDENT que
# l'état actif est le snapshot opérateur sauvegardé (pas le run ML #46).
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402,PLC0415
    get_applied as _get_applied_banner,
    migrate_and_restore as _migrate_banner,
    state_was_repaired as _state_repaired_banner,
)
_migrate_banner(st.session_state)
_snap_banner = _get_applied_banner(st.session_state)
try:
    from persistence import backend_name as _persist_backend_name  # noqa: PLC0415
    _src = {"supabase": "Supabase (PostgreSQL)", "external-file": "fichier durable externe",
            "local-json": "JSON local (Supabase activable par secrets)"}.get(
                _persist_backend_name(), "JSON local")
except Exception:
    _src = "durable store"
if _snap_banner is not None and _snap_banner.label:
    st.html(
        f'<div style="background:linear-gradient(90deg,#064e3b,#065f46);'
        f'border:1px solid #10B981;border-left:4px solid #10B981;'
        f'border-radius:0.3rem;padding:0.5rem 0.9rem;margin-bottom:0.5rem;'
        f'display:flex;gap:0.6rem;align-items:baseline;flex-wrap:wrap;">'
        f'<span style="color:#6EE7B7;font-weight:700;font-size:0.72rem;'
        f'letter-spacing:0.06em;">{t("home.active_operator_state.tag")}</span>'
        f'<span style="color:#F9FAFB;font-weight:700;font-size:0.95rem;">'
        f'{_snap_banner.label}</span>'
        f'<span style="color:#9CA3AF;font-size:0.78rem;">'
        f'{t("home.active_operator_state.meta", src=_src, iso=_snap_banner.timestamp_iso)}'
        f'</span></div>'
    )
    if _state_repaired_banner(st.session_state):
        st.caption(t("home.state_repaired"))
elif _snap_banner is not None:
    st.caption(t("home.run_label", label="—", iso=_snap_banner.timestamp_iso))
else:
    st.caption(t("home.run_label.none"))

# ── En-tête : 5 colonnes fixes ────────────────────────────────────────────────
# La « durée de run » (ex. 26.5 min) a été RETIRÉE : c'était une métadonnée du
# dataset ML de démonstration (run_duration_min), pas un temps procédé validé
# recalculé depuis la configuration opérateur (exigence manager 2026-06-08).
col_logo, col_title, col_r1, col_r3, col_r4 = st.columns([1, 3, 1, 1, 1])
with col_logo:
    if _LOGO_EXISTS:
        st.image(str(LOGO_PATH), width=90)
    else:
        st.markdown("**RONDOL**")
with col_title:
    st.markdown(f"**{t('home.header.title')}**")
    st.caption(t("home.header.caption"))
col_r1.metric(t("m.run"), f"#{selected_run}")
col_r3.metric(t("m.window"), f"{win_idx}/{n_windows}")
col_r4.metric(t("m.time"), win_str)

# ── Bandeau provenance : ces indicateurs viennent du dataset ML d'essais ───────
# (score stabilité, P(stable), capteurs) — DONNÉE DE DÉMONSTRATION, pas un run
# opérateur live. Marquage explicite exigé (séparation demo / config opérateur).
st.html(
    '<div style="display:flex;align-items:center;gap:0.5rem;background:rgba(124,58,237,0.10);'
    'border:1px solid rgba(124,58,237,0.35);border-radius:0.4rem;padding:0.4rem 0.7rem;'
    'margin:0.3rem 0;color:#C4B5FD;font-size:0.82rem;">'
    '<span style="background:#7C3AED;color:#fff;font-weight:700;font-size:0.6rem;'
    'letter-spacing:0.06em;padding:0.05rem 0.4rem;border-radius:0.25rem;">DEMO</span>'
    f'<span>{t("demo.ml.banner_default")}</span>'
    '</div>'
)

# ── Statut procédé ────────────────────────────────────────────────────────────
# st.html() : composant React identique à chaque render, React ne reconcilie
# jamais les internals (dangerouslySetInnerHTML) → zéro removeChild possible
_STATE_STYLE = {
    "STABLE":     ("background:#d1fae5;color:#065f46;border-left:4px solid #10B981;"),
    "SURVEILLER": ("background:#fef3c7;color:#92400e;border-left:4px solid #F59E0B;"),
    "CRITIQUE":   ("background:#fee2e2;color:#991b1b;border-left:4px solid #EF4444;"),
}
_badge_style = _STATE_STYLE[state]
st.divider()
st.html(
    f'<div style="{_badge_style}padding:0.6rem 1rem;border-radius:0.25rem;'
    f'font-size:0.95rem;font-weight:600;">'
    f'{cfg["icon"]} {t(f"home.state.{state}.label")} — {t(f"home.state.{state}.sub")}</div>'
)
st.markdown(f"*→ {t(f'home.state.{state}.impact')}*")

# ── Bandeau zones critiques (Feed + Z1..Z8) ─────────────────────────────────
# Lecture du σ courant pour chaque zone thermique. Cellule colorée :
#   vert  σ < 0.5 °C  · orange  σ < 1.5 °C  · rouge  σ ≥ 1.5 °C.
# Cohérent avec _badge_sen() ci-dessus → même grille de décision.
_ZONE_BAR_LABELS = ["Feed", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
_ZONE_SENSOR_COLS = [None, "Z1_std", "Z2_std", "Z3_std", "Z4_std",
                     "Z5_std", "Z6_std", "Z7_std", "Z8_std"]


def _zone_color(std: float | None) -> tuple[str, str, str]:
    """Retourne (bg, fg, label_short) pour σ donné. None → grisé neutre."""
    if std is None or (isinstance(std, float) and np.isnan(std)):
        return ("#1F2937", "#6B7280", "—")
    if std < 0.5:
        return ("#0f2b1d", "#10B981", "OK")
    if std < 1.5:
        return ("#3b2c0a", "#F59E0B", "WATCH")
    return ("#3b1212", "#EF4444", "ALERT")


_zone_cells_html: list[str] = []
_critical_zones: list[str] = []
for label, col in zip(_ZONE_BAR_LABELS, _ZONE_SENSOR_COLS):
    if col is None or col not in current_row.index:
        std_val = None
        sigma_txt = "—"
    else:
        v = current_row.get(col, np.nan)
        std_val = float(v) if not (isinstance(v, float) and np.isnan(v)) else None
        sigma_txt = f"σ {std_val:.2f}" if std_val is not None else "—"
    bg, fg, status = _zone_color(std_val)
    if status == "ALERT":
        _critical_zones.append(label)
    _zone_cells_html.append(
        f'<div style="flex:1 1 0;min-width:60px;background:{bg};'
        f'border:1px solid {fg};border-radius:0.25rem;padding:0.35rem 0.2rem;'
        f'text-align:center;">'
        f'<div style="color:{fg};font-size:0.72rem;font-weight:700;'
        f'letter-spacing:0.05em;">{label}</div>'
        f'<div style="color:{fg};font-size:0.62rem;font-weight:600;'
        f'margin-top:0.1rem;">{status}</div>'
        f'<div style="color:#9CA3AF;font-size:0.62rem;font-variant-numeric:tabular-nums;'
        f'margin-top:0.1rem;">{sigma_txt}</div>'
        f'</div>'
    )

st.html(
    '<div style="display:flex;gap:0.3rem;margin-top:0.6rem;">'
    + "".join(_zone_cells_html) + "</div>"
)
if _critical_zones:
    st.caption(t("home.zones.alert", zones=", ".join(_critical_zones)))
else:
    st.caption(t("home.zones.ok"))

# ── Reco config vis (25/30/40) + action prioritaire ─────────────────────────
# Lit la configuration vis depuis session_state (partagée avec Profile).
# Si absente (utilisateur n'a pas encore visité Profile), on initialise à vide
# pour garder un comportement déterministe et un DOM stable.
# PRIORITÉ SNAPSHOT : hydrate la session depuis le snapshot validé (source de
# vérité officielle, applied_state.json) AVANT le store opérateur — setdefault-
# only, jamais d'écrasement d'une valeur vivante.
from AgentIndustrial_v1.core.applied_state import hydrate_session_from_applied  # noqa: E402
hydrate_session_from_applied(st.session_state)
# Restaure la config opérateur centrale (store/disque) avant lecture.
restore_operator_state(st.session_state)

if "screw_config" not in st.session_state:
    st.session_state["screw_config"] = screw_new_empty()

# P3.4 : la configuration OPÉRATEUR (profil vis, rpm, débit, densité) vient
# EXCLUSIVEMENT de current_run_state — jamais du dataset ML de démonstration ni
# d'une lecture legacy plate. Le débit suit l'étalonnage feeder (0 si non
# calculable, cohérent avec Moteur Procédé).
_op_crs = build_crs(st.session_state)
_op_mi = build_moteur_inputs_from_current_run_state(_op_crs)
_screw_cfg = _op_mi["config"]
_screw_rpm = _op_mi["screw_rpm"]
_screw_feed = _op_mi["feed_g_per_min"]
_screw_dens = _op_mi["bulk_density"]

# Repli feeder non étalonné : ne pas présenter un débit/FF à 0 comme une vérité
# procédé. On avertit explicitement (aucun débit par défaut inventé).
if not _op_mi["feed_available"]:
    st.warning(t("home.flow_not_computable"), icon="⚠️")

_count_rec = screw_recommend_count(
    _screw_cfg, _screw_rpm, _screw_feed, _screw_dens,
    base_type_fn=screw_base_type,
    is_part2_fn=screw_is_part2,
    fill_factor_fn=screw_ff_avg,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
    position_to_zone_fn=screw_pos_to_zone,
    zone_residence_fn=screw_zone_rt,
)
_recs_screw = screw_compute_recommendations(
    _screw_cfg, _screw_rpm, _screw_feed, _screw_dens,
    base_type_fn=screw_base_type,
    is_part2_fn=screw_is_part2,
    position_to_zone_fn=screw_pos_to_zone,
    fill_factor_fn=screw_ff_avg,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
)
_profile_reading = screw_analyze_profile(
    _screw_cfg, _screw_rpm, _screw_feed, _screw_dens,
    base_type_fn=screw_base_type,
    is_part2_fn=screw_is_part2,
    position_to_zone_fn=screw_pos_to_zone,
    fill_factor_fn=screw_ff_avg,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
)

# Couche systémique calculée tôt : alimente à la fois le bloc DÉCISION
# AGENT (haut de la section opérationnelle), le why_optimal_enriched, et le
# bloc RAISONNEMENT GLOBAL plus bas.
_systemic = screw_analyze_systemic(
    _screw_cfg, _screw_rpm, _screw_feed, _screw_dens,
    base_type_fn=screw_base_type,
    is_part2_fn=screw_is_part2,
    position_to_zone_fn=screw_pos_to_zone,
    fill_factor_fn=screw_ff_avg,
    n_positions=N_POSITIONS,
    main_feeder_pos=MAIN_FEEDER_POSITION,
    tip_part1_pos=TIP_PART1_POS,
    profile_reading=_profile_reading,
    count_rec=_count_rec,
    recs=_recs_screw,
    zone_residence_fn=screw_zone_rt,
    tip_constraint_fn=screw_enforce_tip,
)

# Reco principale = 1re reco par sévérité (déjà triée).
_main_reco = _recs_screw[0] if _recs_screw else None
# Action prioritaire = 1re ActionStep "main" du count_rec.
_main_action = ""
for _step in getattr(_count_rec, "action_steps", ()) or ():
    if getattr(_step, "priority", "main") == "main":
        _main_action = getattr(_step, "body", "")
        break

_SEV_ACCENT = {
    "critique": "#EF4444", "warning": "#F59E0B",
    "info": "#3B82F6", "ok": "#10B981",
}

# ── Bandeau LECTURE PROFIL (archetype + régime) ─────────────────────────────
# Phase 10 manager 2026-06-09 : si aucun snapshot n'a été validé ou si le profil
# vis est vide, la lecture profil ne peut pas être affirmative — on signale
# explicitement « analyse indicative ». Ne change pas le contenu généré, ajoute
# juste un préfixe honnête sur la fiabilité.
from AgentIndustrial_v1.core.applied_state import get_applied as _get_applied  # noqa: E402,PLC0415
from screw_logic import count_user_elements as _count_user_elements  # noqa: E402,PLC0415

_applied_snap = _get_applied(st.session_state)
_n_user_el = float(_count_user_elements(list(_screw_cfg or [])))
_profile_is_indicative = (_applied_snap is None) or (_n_user_el <= 0.0)

_arch_acc = _SEV_ACCENT.get(_profile_reading.archetype_severity, "#3B82F6")
st.divider()
st.caption(t("home.sec.profile_reading"))
if _profile_is_indicative:
    if _applied_snap is None and _n_user_el <= 0.0:
        _indic_body = t("home.profile_indicative.body")
    elif _applied_snap is None:
        _indic_body = t("home.profile_indicative.no_snapshot")
    else:
        _indic_body = t("home.profile_indicative.no_elements")
    st.info(
        f"{t('home.profile_indicative.title')} {_indic_body}",
        icon="ℹ️",
    )
_risks_chips = ""
if _profile_reading.risks:
    _risks_chips = "".join(
        f'<span style="background:rgba(239,68,68,0.15);color:#fecaca;'
        f'border:1px solid #EF4444;border-radius:0.2rem;'
        f'padding:0.1rem 0.45rem;font-size:0.7rem;font-weight:600;">⚠ {r}</span>'
        for r in _profile_reading.risks
    )
st.html(
    f'<div style="background:#111827;border-left:4px solid {_arch_acc};'
    f'border-radius:0.25rem;padding:0.6rem 0.9rem;">'
    f'<div style="display:flex;gap:0.5rem;align-items:baseline;flex-wrap:wrap;">'
    f'<span style="color:{_arch_acc};font-weight:700;font-size:1rem;">'
    f'{_profile_reading.archetype}</span>'
    f'<span style="color:#9CA3AF;">·</span>'
    f'<span style="color:#D1D5DB;font-weight:500;font-size:0.88rem;">'
    f'{_profile_reading.regime}</span>'
    f'</div>'
    f'<div style="color:#D1D5DB;font-size:0.85rem;line-height:1.5;'
    f'margin-top:0.3rem;">{_profile_reading.summary}</div>'
    f'<div style="color:#9CA3AF;font-size:0.78rem;line-height:1.4;'
    f'margin-top:0.25rem;font-style:italic;">→ {_profile_reading.regime_summary}</div>'
    + (
        f'<div style="margin-top:0.4rem;display:flex;gap:0.35rem;flex-wrap:wrap;">{_risks_chips}</div>'
        if _risks_chips else ""
    )
    + "</div>"
)

# ── Décision opérationnelle ──────────────────────────────────────────────────
# Bloc décision agent en tête : action prioritaire + badge confiance +
# prochaine étape — synthèse opérateur de la couche systémique.
st.caption(t("home.sec.decision"))
st.html(screw_build_decision_html(_systemic))
# Lecture opérateur 3-lignes — synthèse simple sous la version technique.
st.html(screw_build_decision_summary_html(_systemic))

_dec_col1, _dec_col2 = st.columns([1, 2])
with _dec_col1:
    st.html(
        f'<div style="background:#0B0F14;border:1px solid #10B981;'
        f'border-radius:0.3rem;padding:0.7rem 0.9rem;text-align:center;">'
        f'<div style="color:#9CA3AF;font-size:0.72rem;font-weight:600;'
        f'letter-spacing:0.05em;">{t("home.rec_config.title")}</div>'
        f'<div style="color:#10B981;font-size:2.2rem;font-weight:700;'
        f'line-height:1.05;margin:0.25rem 0;">{_count_rec.suggested}</div>'
        f'<div style="color:#9CA3AF;font-size:0.78rem;">'
        f'{t("home.rec_config.elements")} · {_count_rec.tagline}</div>'
        f'</div>'
    )
with _dec_col2:
    # Reco principale 4-champs (zone + physics + impact + action).
    if _main_reco is not None:
        sev = _main_reco.get("severity", "info")
        accent = _SEV_ACCENT.get(sev, "#3B82F6")
        zone = _main_reco.get("zone", "—") or "—"
        physics = _main_reco.get("physics", _main_reco.get("title", ""))
        impact = _main_reco.get("impact", "")
        action = _main_reco.get("action", _main_reco.get("detail", ""))
        evidence = _main_reco.get("evidence", "")
        impact_html = (
            f'<div style="color:#D1D5DB;font-size:0.78rem;line-height:1.4;'
            f'margin-top:0.25rem;"><span style="color:#9CA3AF;font-weight:600;'
            f'font-size:0.66rem;letter-spacing:0.04em;text-transform:uppercase;'
            f'margin-right:0.3rem;">{t("common.impact")}</span>{impact}</div>'
            if impact else ""
        )
        ev_html = (
            f'<div style="color:#6B7280;font-size:0.7rem;text-align:right;'
            f'margin-top:0.25rem;">{evidence}</div>'
            if evidence else ""
        )
        st.html(
            f'<div style="background:#111827;border-left:4px solid {accent};'
            f'border-radius:0.25rem;padding:0.55rem 0.85rem;">'
            f'<div style="display:flex;gap:0.5rem;align-items:center;'
            f'flex-wrap:wrap;">'
            f'<span style="color:{accent};font-size:0.7rem;font-weight:700;'
            f'letter-spacing:0.05em;">{t("home.main_reco")} · {sev.upper()}</span>'
            f'<span style="background:rgba(255,255,255,0.05);color:#D1D5DB;'
            f'border:1px solid {accent};font-weight:700;font-size:0.7rem;'
            f'padding:0.1rem 0.45rem;border-radius:0.2rem;">{zone}</span>'
            f'<span style="color:#F9FAFB;font-weight:600;font-size:0.9rem;">'
            f'{physics}</span></div>'
            f'{impact_html}'
            f'<div style="color:#F9FAFB;font-size:0.83rem;line-height:1.45;'
            f'margin-top:0.3rem;">'
            f'<span style="color:{accent};font-weight:600;font-size:0.66rem;'
            f'letter-spacing:0.04em;text-transform:uppercase;margin-right:0.3rem;">'
            f'{t("common.action")}</span>{action}</div>'
            f'{ev_html}'
            f'</div>'
        )
    else:
        st.html(
            '<div style="background:#111827;border-left:4px solid #3B82F6;'
            'border-radius:0.25rem;padding:0.55rem 0.85rem;color:#9CA3AF;">'
            + t("home.no_screw_reco")
            + "</div>"
        )

# Pourquoi 25/30/40 est optimal (toujours présent → DOM stable).
# Priorité : enrichi (avec compromis) > brut > rationale.
_why_optimal = (
    getattr(_systemic, "why_optimal_enriched", "")
    or getattr(_count_rec, "why_optimal", "")
    or _count_rec.rationale
)
st.html(
    f'<div style="background:rgba(16,185,129,0.04);border-left:2px solid #10B981;'
    f'border-radius:0 0.2rem 0.2rem 0;padding:0.5rem 0.85rem;margin-top:0.5rem;">'
    f'<div style="color:#10B981;font-size:0.7rem;font-weight:700;'
    f'letter-spacing:0.04em;">{t("home.why_optimal", n=_count_rec.suggested)}</div>'
    f'<div style="color:#D1D5DB;font-size:0.84rem;line-height:1.5;'
    f'margin-top:0.2rem;">{_why_optimal}</div>'
    f'</div>'
)

if _main_action:
    st.html(
        f'<div style="background:rgba(16,185,129,0.06);border-left:2px solid #10B981;'
        f'border-radius:0 0.2rem 0.2rem 0;padding:0.5rem 0.85rem;margin-top:0.5rem;">'
        f'<div style="color:#10B981;font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.04em;">{t("home.priority_action")}</div>'
        f'<div style="color:#F9FAFB;font-size:0.86rem;line-height:1.45;'
        f'margin-top:0.2rem;">→ {_main_action}</div>'
        f'</div>'
    )
else:
    # Slot maintenu (DOM stable) avec hauteur 0 → pas d'erreur removeChild.
    st.html('<div style="height:0;overflow:hidden;margin:0;"></div>')

# ── Raisonnement global procédé (couche systémique) ─────────────────────────
# Bloc unique, atomique : compensations + checks + trade-offs + synthèse.
# `_systemic` a été calculé plus haut (pour alimenter why_optimal_enriched) —
# on ne fait ici que l'afficher.
st.divider()
st.caption(t("home.sec.global_reasoning"))
st.html(screw_build_systemic_html(_systemic))

# ── Agent IA procédé (synchronisé Settings) ─────────────────────────────────
# Reconstruit le ProcessState depuis l'état partagé (édité dans Settings :
# feeders, consignes Z1..Z8/die, vitesse vis, zone cooling) puis ré-évalue
# règles + recos + thermique. Modifier Settings change visiblement ce bloc.
# DOM stable : exactement 1 st.caption + 1 st.html à chaque render.
_agent_state = state_from_session(st.session_state)
_agent_report = agent_evaluate(_agent_state, lang=current_lang())
_agent_recos = agent_build_recos(_agent_state, _agent_report.alerts, lang=current_lang())
_agent_cm = agent_compute_cooling(_agent_state)

_AG_STATE_C = {"STABLE": "#10B981", "SURVEILLER": "#F59E0B", "CRITIQUE": "#EF4444"}
_ag_c = _AG_STATE_C.get(_agent_report.state, "#10B981")


def _translate_agent_state(state: str) -> str:
    return t(f"home.agent.state.{state}")


def _translate_agent_diagnostic(diag: str, report) -> str:
    if current_lang() == "fr":
        return diag
    _n_crit = sum(1 for a in report.alerts if a.severity == "critical")
    _n_warn = sum(1 for a in report.alerts if a.severity == "warning")
    _kpis = _agent_state.kpis if hasattr(_agent_state, 'kpis') else None
    if report.state == "STABLE" and _kpis:
        return t("home.agent.diag.stable",
                 n_act=sum(1 for f in getattr(_agent_state, 'feeders', []) if getattr(f, 'active', False)),
                 ff=f"{_kpis.fill_factor*100:.1f} %",
                 rt=f"{_kpis.residence_time_s:.1f}",
                 sme=f"{_kpis.sme_kwh_per_kg:.2f}")
    elif report.state == "SURVEILLER":
        return t("home.agent.diag.watch", n_warn=_n_warn, n_crit=_n_crit)
    elif report.state == "CRITIQUE":
        return t("home.agent.diag.critical",
                 score=report.risk_score, n_crit=_n_crit, n_warn=_n_warn)
    return diag
_AG_SEV_C = {"critical": "#EF4444", "warning": "#F59E0B", "info": "#3B82F6", "ok": "#10B981"}

_reco_by_code: dict[str, object] = {}
for _r in _agent_recos:
    _reco_by_code.setdefault(_r.linked_alert_code, _r)

_rows_html: list[str] = []
for _a in _agent_report.alerts[:3]:
    _sc = _AG_SEV_C.get(_a.severity, "#9CA3AF")
    _rc = _reco_by_code.get(_a.code)
    _act = _rc.action if _rc is not None else "—"
    _imp = _rc.delta_label if _rc is not None else "—"
    _rows_html.append(
        f'<div style="border-left:3px solid {_sc};padding:0.3rem 0.6rem;'
        f'margin-top:0.3rem;background:#0B0F14;border-radius:0.2rem;">'
        f'<div style="color:{_sc};font-size:0.72rem;font-weight:700;">'
        f'{_a.severity.upper()} · {_a.target or "—"} — {_a.title}</div>'
        f'<div style="color:#D1D5DB;font-size:0.76rem;margin-top:0.15rem;">'
        f'<span style="color:#10B981;font-weight:600;">{t("settings.card.action")}</span> {_act} '
        f'<span style="color:#6B7280;">· {_imp}</span></div></div>'
    )
# Toujours 3 lignes (DOM stable même si moins d'alertes — bloc html unique).
while len(_rows_html) < 3:
    _rows_html.append(
        '<div style="border-left:3px solid #1F2937;padding:0.3rem 0.6rem;'
        'margin-top:0.3rem;background:#0B0F14;border-radius:0.2rem;'
        f'color:#374151;font-size:0.76rem;">{t("home.no_other_alert")}</div>'
    )

# Le « Cooling Test » opérateur a été retiré : on lit la zone la plus chaude
# calculée automatiquement par le modèle thermique (T = Tset + SME/Cp + kτ
# + corrections profil vis / cisaillement / mixage / viscosité matière).
_sel_z = _agent_cm.hottest_zone
_selz = _agent_cm.zones.get(_sel_z) or _agent_cm.zones["Z5"]

st.divider()
st.caption(t("home.sec.agent_sync"))
st.html(
    f'<div style="background:#111827;border:1px solid #1F2937;'
    f'border-left:4px solid {_ag_c};border-radius:0.3rem;padding:0.7rem 0.9rem;">'
    f'<div style="display:flex;gap:0.4rem;flex-wrap:wrap;align-items:center;">'
    f'<span style="background:{_ag_c};color:#0B0F14;font-weight:700;'
    f'font-size:0.74rem;padding:0.15rem 0.6rem;border-radius:0.2rem;">'
    f'{_translate_agent_state(_agent_report.state)} · {_agent_report.risk_score}/100</span>'
    f'<span style="color:#9CA3AF;font-size:0.76rem;">'
    f'{len(_agent_report.alerts)} {t("home.agent.alerts_label")} · {len(_agent_recos)} {t("home.agent.recos_label")} · '
    f'{t("home.agent.thermal_peak")} {_agent_cm.hottest_zone} · {t("home.agent.torque")} '
    f'{_agent_cm.torque_load * 100:.0f} %</span>'
    f'<span style="margin-left:auto;color:#6B7280;font-size:0.7rem;">'
    f'T={_selz.zone} {_selz.t_est_C:.0f}°C ({t("home.agent.setpoint")} {_selz.t_target_C:.0f} '
    f'· {t("home.agent.ceiling")} {_selz.t_limit_C:.0f}) · {t("home.agent.model")} T=Tset+SME/Cp+kτ</span>'
    f'</div>'
    f'<div style="color:#9CA3AF;font-size:0.78rem;margin-top:0.35rem;">'
    f'{_translate_agent_diagnostic(_agent_report.diagnostic, _agent_report)}</div>'
    + "".join(_rows_html)
    + '</div>'
)

# ── KPIs : 3 colonnes fixes ───────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric(t("home.kpi.stability"), f"{score:.1f}/100", delta_str)
k2.metric(t("home.kpi.threshold"), f"{THRESHOLD}/100", t("home.kpi.threshold_delta"))
k3.metric(t("home.kpi.pstable"), f"{proba_stable:.2f}", t("home.kpi.pstable_delta"))

# ── Top 5 capteurs : 5 colonnes fixes, toujours exactement 5 métriques ────────
st.divider()
st.caption(t("home.sec.top5"))
s1, s2, s3, s4, s5 = st.columns(5)
sensor_cols = [s1, s2, s3, s4, s5]
for i, info in enumerate(unstable):  # top_unstable_sensors() garantit exactement 5
    # is_real détermine le contenu mais PAS la structure :
    # delta est TOUJOURS passé → st.metric génère toujours la même structure DOM
    # (sans delta → React retire l'élément flèche → removeChild)
    badge   = _badge_sen(info["std"])
    is_real = info["sensor"] != "—"
    slope_s = (
        f"{info['slope']:+.5f} °C/s"
        if (is_real and not np.isnan(info["slope"]))
        else "—"
    )
    sensor_cols[i].metric(
        label=f"{info['sensor']} · {badge}" if is_real else "—",
        value=f"{info['std']:.3f} °C" if is_real else "—",
        delta=slope_s,  # toujours présent → structure DOM identique pour tous les 5 slots
    )

# ── Analyse diagnostique ──────────────────────────────────────────────────────
with st.container(key="diag_container"):
    st.caption(t("home.sec.auto_analysis", win=win_idx, n=n_windows))
    st.markdown(expl)

# ── Recommandations : exactement _N_RECOS=5 slots, structure identique ────────
# Chaque slot = 1 st.container(border=...) + 1 st.markdown + 1 st.caption
# → même type de composant React à chaque position, seuls les props changent
# → zéro removeChild quelle que soit la transition d'état
st.divider()
st.caption(t("home.sec.recos"))
for i in range(_N_RECOS):
    action, detail = cfg["recos"][i]
    with st.container(border=True, key=f"reco_{i}"):
        st.markdown(f"**{i + 1:02d}. {action}**" if action else "\u00a0")
        st.caption(detail if detail else "\u00a0")

# ── Graphique — Évolution du score ────────────────────────────────────────────
st.divider()
st.caption(t("home.sec.score_evo"))
_fig = go.Figure()
_fig.add_trace(go.Scatter(
    x=run_df["window_end"].tolist(),
    y=run_df["stability_score"].tolist(),
    mode="lines",
    line=dict(color=CYAN, width=2),
    fill="tozeroy",
    fillcolor="rgba(6,182,212,0.08)",
    name="Score",
    hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>",
))
_fig.add_hline(
    y=THRESHOLD,
    line_dash="dash",
    line_color="#374151",
    annotation_text=f"{t('home.chart.threshold')} {THRESHOLD}",
    annotation_font_color="#4B5563",
    annotation_font_size=10,
)
_fig.update_layout(
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    height=200,
    margin=dict(l=0, r=0, t=5, b=0),
    showlegend=False,
    xaxis=dict(showgrid=False, color="#4B5563", tickfont=dict(size=10), zeroline=False),
    yaxis=dict(
        showgrid=True, gridcolor="#1F2937",
        color="#4B5563", tickfont=dict(size=10),
        range=[0, 105], zeroline=False,
    ),
    hoverlabel=dict(bgcolor="#1F2937", font_color="#F9FAFB"),
)
st.plotly_chart(_fig, use_container_width=True, key="score_chart")

# ── KPIs résumé run : 4 colonnes fixes ───────────────────────────────────────
pct_stable_run = float(run_df["is_stable"].mean()) * 100
score_mean     = run_df["stability_score"].mean()
score_min      = run_df["stability_score"].min()

r1, r2, r3, r4 = st.columns(4)
r1.metric(t("home.kpi.score_mean"), f"{score_mean:.1f}")
r2.metric(t("home.kpi.score_min"), f"{score_min:.1f}")
r3.metric(t("home.kpi.windows_stable"), f"{pct_stable_run:.0f} %")
r4.metric(t("home.kpi.windows_total"), str(n_windows))

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(t("home.footer", run=selected_run, run_str=run_str, n=n_windows, th=THRESHOLD))
