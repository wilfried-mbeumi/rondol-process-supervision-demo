"""
Analyse_run.py — Analyse temporelle d'un run de production.

Corrections appliquées :
- st.line_chart() → st.plotly_chart() : élimine Vega-Lite/D3 → zéro removeChild
- applymap() → map() : FutureWarning pandas 2.3 supprimé
- classify_state() vectorisée via numpy : plus de iterrows() lent
- show_spinner=False sur tous les caches
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP = Path(__file__).resolve().parent.parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

# i18n — sélecteur de langue + traduction du chrome (B1).
from rondol_i18n import language_selector, t  # noqa: E402

MODEL_PATH   = ROOT / "models" / "SVM_w60.joblib"
DATASET_PATH = ROOT / "data" / "features" / "dataset_ml_w60.csv"
THRESHOLD    = 80

st.set_page_config(page_title=t("page.analyse.title"), layout="wide")
language_selector()
st.markdown(t("analyse.header"))

# ── Bandeau DEMO : TOUTE cette page analyse un run du dataset ML d'ESSAI ──────
# (run #, durée run_duration_min, % stable/critique, scores, profil thermique
# proviennent de dataset_ml_w60.csv). Ces valeurs ne sont PAS un run opérateur
# live — exigence manager 2026-06-08 (ne jamais présenter une durée demo comme
# durée réelle). Marquage explicite, cohérent avec le bandeau de Supervision.
st.html(
    '<div style="display:flex;align-items:center;gap:0.5rem;background:rgba(124,58,237,0.10);'
    'border:1px solid rgba(124,58,237,0.35);border-radius:0.4rem;padding:0.4rem 0.7rem;'
    'margin:0.3rem 0 0.5rem;color:#C4B5FD;font-size:0.84rem;">'
    '<span style="background:#7C3AED;color:#fff;font-weight:700;font-size:0.6rem;'
    'letter-spacing:0.06em;padding:0.05rem 0.4rem;border-radius:0.25rem;">DEMO</span>'
    "<span>Analyse d'un run du <b>dataset ML d'essai (avril 2026)</b> — durée, "
    "scores et profils sont des <b>données de démonstration</b>, "
    "<b>non un run opérateur live</b>.</span>"
    '</div>'
)
st.divider()


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


def classify_states_vec(scores: np.ndarray, probas: np.ndarray) -> list[str]:
    """Vectorisée — pas d'iterrows(). Même logique que Supervision.py."""
    result = np.where(
        (scores >= THRESHOLD) & (probas >= 0.70), "STABLE",
        np.where(
            (scores < 65) | (probas < 0.40), "CRITIQUE",
            "SURVEILLER"
        )
    )
    return result.tolist()


model        = load_model()
df_all       = load_dataset()
FEATURE_COLS = get_feature_cols(df_all)

good_runs = df_all[df_all["bad_run"] == 0]
run_ids   = sorted(good_runs["run_id"].unique())

# ---------------------------------------------------------------------------
# Sélection run
# ---------------------------------------------------------------------------
selected_run = st.sidebar.selectbox(
    t("analyse.sidebar.run"),
    options=run_ids,
    index=len(run_ids) - 1,
    format_func=lambda r: f"Run #{r}",
    key="analyse_run_sb",
)

run_df = good_runs[good_runs["run_id"] == selected_run].sort_values("window_end").copy()

# ---------------------------------------------------------------------------
# Inférence SVM — vectorisée sur toutes les fenêtres
# ---------------------------------------------------------------------------
X_run  = run_df[FEATURE_COLS]
probas = model.predict_proba(X_run)[:, 1]   # proba_stable
run_df["proba_stable"] = probas
run_df["etat"] = classify_states_vec(
    run_df["stability_score"].to_numpy(),
    run_df["proba_stable"].to_numpy(),
)

# ---------------------------------------------------------------------------
# Stats du run
# ---------------------------------------------------------------------------
dur        = float(run_df["run_duration_min"].iloc[0])
n_win      = len(run_df)
pct_stable = (run_df["etat"] == "STABLE").mean() * 100
pct_crit   = (run_df["etat"] == "CRITIQUE").mean() * 100

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(t("m.run"),              f"#{selected_run}")
col2.metric(
    t("m.duration"), f"{dur:.1f} min",
    help="DEMO — durée du run d'essai (run_duration_min du dataset ML), "
         "pas un temps procédé opérateur validé.",
)
col3.metric(t("analyse.m.windows"),  n_win)
col4.metric(t("analyse.m.pct_stable"),   f"{pct_stable:.0f} %")
col5.metric(t("analyse.m.pct_critical"), f"{pct_crit:.0f} %")

# Marquage explicite : ces indicateurs sont des métadonnées du run de
# démonstration (dataset ML d'essai), jamais un run opérateur live.
st.caption(
    "⚠️ DEMO — durée, % stable/critique et scores ci-dessus sont des "
    "métadonnées du run d'essai (dataset ML), non un run opérateur live."
)

st.divider()

# ---------------------------------------------------------------------------
# Graphique — Plotly (pas de Vega-Lite, pas de D3, zéro removeChild)
# ---------------------------------------------------------------------------
st.markdown("##### " + t("analyse.sec.score"))

_colors = {"STABLE": "#10B981", "SURVEILLER": "#F59E0B", "CRITIQUE": "#EF4444"}

fig = go.Figure()

# Trace score de stabilité
fig.add_trace(go.Scatter(
    x=run_df["window_end"].tolist(),
    y=run_df["stability_score"].tolist(),
    mode="lines",
    name="Score",
    line=dict(color="#06B6D4", width=2),
    hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>",
))

# Trace P(stable)
fig.add_trace(go.Scatter(
    x=run_df["window_end"].tolist(),
    y=(run_df["proba_stable"] * 100).tolist(),
    mode="lines",
    name="P(stable) ×100",
    line=dict(color="#8B5CF6", width=1.5, dash="dot"),
    hovertemplate="<b>%{x}</b><br>P(stable): %{y:.1f}<extra></extra>",
))

# Seuil
fig.add_hline(
    y=THRESHOLD,
    line_dash="dash",
    line_color="#374151",
    annotation_text=f"Seuil {THRESHOLD}",
    annotation_font_color="#4B5563",
    annotation_font_size=10,
)

fig.update_layout(
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    height=260,
    margin=dict(l=0, r=0, t=5, b=0),
    showlegend=True,
    legend=dict(
        font=dict(color="#9CA3AF", size=11),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(showgrid=False, color="#4B5563", tickfont=dict(size=10), zeroline=False),
    yaxis=dict(
        showgrid=True, gridcolor="#1F2937",
        color="#4B5563", tickfont=dict(size=10),
        range=[0, 105], zeroline=False,
    ),
    hoverlabel=dict(bgcolor="#1F2937", font_color="#F9FAFB"),
)

st.plotly_chart(fig, use_container_width=True, key="analyse_score_chart")
st.caption(t("analyse.cap.score", th=THRESHOLD))

st.divider()

# ---------------------------------------------------------------------------
# Tableau des fenêtres — map() remplace applymap() (pandas 2.3)
# ---------------------------------------------------------------------------
st.markdown("##### " + t("analyse.sec.detail"))

display_df = run_df[["window_start", "window_end", "stability_score",
                      "proba_stable", "etat", "n_samples"]].copy()
display_df["window_start"]    = display_df["window_start"].dt.strftime("%H:%M:%S")
display_df["window_end"]      = display_df["window_end"].dt.strftime("%H:%M:%S")
display_df["stability_score"] = display_df["stability_score"].round(1)
display_df["proba_stable"]    = display_df["proba_stable"].round(3)
_col_state = t("analyse.tbl.state")
display_df.columns = [t("analyse.tbl.start"), t("analyse.tbl.end"), t("analyse.tbl.score"),
                      t("analyse.tbl.pstable"), _col_state, t("analyse.tbl.samples")]


def color_etat(val: str) -> str:
    colors = {"STABLE": "#d4edda", "SURVEILLER": "#fff3cd", "CRITIQUE": "#f8d7da"}
    return f"background-color: {colors.get(val, 'white')}"


# map() — API correcte pandas 2.x (applymap deprecated)
st.dataframe(
    display_df.style.map(color_etat, subset=[_col_state]),
    use_container_width=True,
    height=400,
)

# ---------------------------------------------------------------------------
# Profil thermique moyen du run
# ---------------------------------------------------------------------------
st.divider()
st.markdown("##### " + t("analyse.sec.thermal"))

sensors   = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
             "DIE", "CastFilmBody", "CastFilmP1", "CastFilmP2"]
mean_cols = [f"{s}_mean" for s in sensors if f"{s}_mean" in run_df.columns]
std_cols  = [f"{s}_std"  for s in sensors if f"{s}_std"  in run_df.columns]

profile_mean = run_df[mean_cols].mean().rename(lambda c: c.replace("_mean", ""))
profile_std  = run_df[std_cols].mean().rename(lambda c: c.replace("_std", ""))

profile_df = pd.DataFrame({
    t("analyse.tbl.t_mean"):     profile_mean,
    t("analyse.tbl.sigma_mean"): profile_std,
}).round(2)

st.dataframe(profile_df, use_container_width=True)
