"""
Historique.py — Historique des procédés (persistant) + essais d'entraînement ML.

Deux niveaux distincts, volontairement non confondus :

1. « Historique des procédés » (section principale)
   - Source UNIQUE : le stockage PERSISTANT disque
     (`data/history/process_history.json`) via `app/history_store.py`. Survit au
     redémarrage de l'application (l'ancien affichage session est remplacé ; la
     couche `applied_history` garde son rôle interne 3-couches, sans être ici la
     source d'affichage).
   - LECTURE SEULE : on n'affiche que ce qui a été FIGÉ au moment du commit
     (métadonnées, config utile, KPIs moteur figés, agrégats zones). Aucun KPI
     n'est recalculé ici ; un champ absent reste « — » (jamais inventé). Le
     statut agent n'est pas figé au commit → affiché « non disponible ».
   - Robustesse : fichier absent/vide → état vide propre ; corrompu → message
     discret, pas de crash.

2. « Essais d'entraînement ML » (section secondaire, expander replié)
   - Récapitulatif des runs du dataset d'entraînement (`dataset_ml_w60.csv`).
   - Contenu historique du modèle — clairement séparé de l'historique procédé
     opérateur.

Périmètre : ce fichier UNIQUEMENT. Ne modifie pas Moteur Procédé, engine/,
screw_logic.py ni AgentIndustrial_v1/ (imports en lecture seule).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Bootstrap sys.path : racine projet (packages) + app/ (screw_logic en module nu).
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP = Path(__file__).resolve().parent.parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

# Lecture seule du stockage procédé PERSISTANT (disque). Aucun recalcul ici :
# chaque record a été figé au moment du clic « Enregistrer » (KPIs moteur inclus).
import history_store  # noqa: E402
# P3.4 : marquage DEMO ML (séparation essais ML / historique procédé réel).
from demo_ml_run import demo_ml_banner_html  # noqa: E402
# Store opérateur central (cohérence inter-pages).
from operator_store import restore_operator_state  # noqa: E402
# i18n FR/EN (Phase 6 manager 2026-06-09) — Historique doit aussi être traduit.
from rondol_i18n import language_selector, t  # noqa: E402
# Mode client vs démonstration (Phase S2) : aucune chimie nominale (LFP/LATP)
# ne doit s'afficher en mode client — même convention que Moteur Procédé.
from app_mode import is_demo_mode  # noqa: E402

# PRIORITÉ SNAPSHOT : la session est hydratée depuis le snapshot validé AVANT
# le store opérateur (setdefault-only) — toutes les pages lisent le même état.
from AgentIndustrial_v1.core.applied_state import (  # noqa: E402
    hydrate_session_from_applied,
    migrate_and_restore,
)
migrate_and_restore(st.session_state)
hydrate_session_from_applied(st.session_state)
restore_operator_state(st.session_state)

DATASET_PATH = ROOT / "data" / "features" / "dataset_ml_w60.csv"
THRESHOLD = 80

st.set_page_config(page_title=t("page.historique.title"), layout="wide")
from auth import require_login  # noqa: E402
require_login(st)

# ---------------------------------------------------------------------------
# Thème sombre Rondol (cohérent avec Supervision / Moteur Procédé) — bloc statique
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
[data-testid="stVerticalBlockBorderWrapper"]{background:#0E141B;border-radius:.65rem;}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#1F2937!important;border-radius:.65rem;}
</style>
""")

language_selector()

RONDOL_GREEN = "#4CAF50"


# ---------------------------------------------------------------------------
# Helpers de PRÉSENTATION (lecture/format seulement — aucun calcul procédé)
# ---------------------------------------------------------------------------
def _fmt_timestamp(iso: str) -> str:
    """ISO → « JJ/MM HH:MM:SS ». Fallback brut si non parsable."""
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m %H:%M:%S")
    except (ValueError, TypeError):
        return str(iso)


def _fmt_num(value, decimals: int = 1, suffix: str = "") -> str:
    """Formate un nombre stocké ; « — » si None/absent (jamais inventé)."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except (ValueError, TypeError):
        return "—"


def _source_label(source: str) -> str:
    """Libellé i18n d'une source de record (défaut : manuel)."""
    return (
        t("historique.source.demo") if source == "demonstration"
        else t("historique.source.manual")
    )


def _record_to_row(rec: dict) -> dict[str, str]:
    """Sérialise un record persistant en ligne de tableau.

    LECTURE SEULE : on lit les champs figés au commit (config + KPIs moteur).
    Aucun recalcul ; un KPI absent → « — ».
    """
    cfg = rec.get("config", {}) or {}
    kpi = rec.get("engine_kpis", {}) or {}
    n_el = cfg.get("n_elements")
    n_el_str = (
        "—" if n_el is None
        else (f"{float(n_el):.0f}" if float(n_el).is_integer() else f"{float(n_el):.1f}")
    )
    status = rec.get("status", "archivé")
    return {
        t("historique.col.status"): (
            "● " + t("historique.status.active") if status == "actif"
            else t("historique.status.archived")
        ),
        t("historique.col.datetime"): _fmt_timestamp(rec.get("timestamp_iso", "")),
        t("historique.col.label"): rec.get("label") or "—",
        t("historique.col.source"): _source_label(rec.get("source", "")),
        t("historique.col.rpm"): _fmt_num(cfg.get("screw_rpm"), 0),
        t("historique.col.flow"): _fmt_num(cfg.get("debit_principal_g_min"), 1),
        t("historique.col.material"): cfg.get("matiere_principale") or "—",
        t("historique.col.die_zones"): str(int(cfg.get("zones_die", 0) or 0)),
        t("historique.col.elements"): n_el_str,
        t("historique.col.torque"): _fmt_num(kpi.get("couple_total_nm"), 3),
        t("historique.col.sme"): _fmt_num(kpi.get("sme_kwh_kg"), 4),
        t("historique.col.residence"): _fmt_num(kpi.get("residence_s"), 1),
        t("historique.col.fill_mean"): _fmt_num(kpi.get("fill_moyen"), 2),
        t("historique.col.fill_peak"): _fmt_num(kpi.get("fill_crete"), 2),
        t("historique.col.shear"): _fmt_num(kpi.get("cisaillement_max_s"), 0),
    }


def _status_style(val: str) -> str:
    """Couleur de la cellule Statut (vert = actif, gris = archivé).

    Repère la puce « ● » (préfixe du statut actif) — indépendant de la langue.
    """
    if "●" in val:
        return "color:#10B981;font-weight:600"
    return "color:#9CA3AF"


# ===========================================================================
#  RENDU
# ===========================================================================
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>{t("historique.banner.left")}</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">{t("historique.banner.right")}</span>'
    f'</div>'
)

st.markdown("## " + t("historique.header"))
st.caption(t("historique.header.caption"))

# ---------------------------------------------------------------------------
# Section principale — historique procédé PERSISTANT (data/history/*.json)
# ---------------------------------------------------------------------------
_load = history_store.read_runs()
_runs = _load.runs

if _load.corrupt:
    # Robustesse : fichier illisible → message discret, pas de crash.
    st.warning(t("historique.corrupt"), icon="⚠️")

if not _runs:
    st.info(t("historique.empty"), icon="ℹ️")
else:
    # Métriques d'en-tête (comptages — pas de calcul procédé).
    _active = next((r for r in _runs if r.get("status") == "actif"), _runs[-1])
    _active_label = _active.get("label") or _fmt_timestamp(_active.get("timestamp_iso", ""))
    h1, h2, h3 = st.columns(3)
    h1.metric(t("historique.m.count"), str(len(_runs)))
    h2.metric(t("historique.m.last"), _fmt_timestamp(_runs[-1].get("timestamp_iso", "")))
    h3.metric(t("historique.m.active"), _active_label)

    # Filtres simples (statut / source / date) — sur les records, pas de recalcul.
    # Valeurs INTERNES stables (indépendantes de la langue) + format_func i18n :
    # un changement de langue ne casse jamais la valeur stockée du widget.
    _dates = sorted(
        {(r.get("timestamp_iso", "") or "")[:10] for r in _runs if r.get("timestamp_iso")},
        reverse=True,
    )
    _STATUS_FMT = {
        "all": "historique.f.all_m",
        "active": "historique.status.active",
        "archived": "historique.status.archived",
    }
    _SOURCE_FMT = {
        "all": "historique.f.all_f",
        "manual": "historique.source.manual",
        "demonstration": "historique.source.demo",
    }
    f1, f2, f3 = st.columns(3)
    _f_status = f1.selectbox(
        t("historique.f.status"), ["all", "active", "archived"],
        format_func=lambda v: t(_STATUS_FMT[v]), key="hist_f_status",
    )
    _f_source = f2.selectbox(
        t("historique.f.source"), ["all", "manual", "demonstration"],
        format_func=lambda v: t(_SOURCE_FMT[v]), key="hist_f_source",
    )
    _f_date = f3.selectbox(
        t("historique.f.date"), ["all"] + _dates,
        format_func=lambda v: t("historique.f.all_f") if v == "all" else v,
        key="hist_f_date",
    )

    def _keep(r: dict) -> bool:
        if _f_status == "active" and r.get("status") != "actif":
            return False
        if _f_status == "archived" and r.get("status") == "actif":
            return False
        _src = "demonstration" if r.get("source") == "demonstration" else "manual"
        if _f_source != "all" and _src != _f_source:
            return False
        if _f_date != "all" and (r.get("timestamp_iso", "") or "")[:10] != _f_date:
            return False
        return True

    _filtered = [r for r in _runs if _keep(r)]

    if not _filtered:
        st.caption(t("historique.no_filter_match"))
    else:
        # Tableau — plus récent en haut.
        _rows = [_record_to_row(r) for r in reversed(_filtered)]
        _df = pd.DataFrame(_rows)
        with st.container(border=True):
            st.dataframe(
                _df.style.map(_status_style, subset=[t("historique.col.status")]),
                width="stretch",
                hide_index=True,
            )

        # ---- Détail d'un procédé (agrégats zones + statut agent) -------------
        def _run_caption(r: dict) -> str:
            ts = _fmt_timestamp(r.get("timestamp_iso", ""))
            lbl = r.get("label") or t("historique.no_label")
            return f"{ts} · {lbl}"

        _options = list(reversed(_filtered))
        _idx = st.selectbox(
            t("historique.detail_select"),
            range(len(_options)),
            format_func=lambda i: _run_caption(_options[i]),
            key="hist_detail_sel",
        )
        _sel = _options[_idx]
        with st.container(border=True):
            # Phase 9 manager 2026-06-09 — Composition matière par feeder
            # capturée au commit. Si vide → « Non renseigné » (jamais inventé).
            # i18n FR/EN (toutes les chaînes passent par rondol_i18n).
            # Colonne « État » retirée : le champ `state` n'est PAS sérialisé
            # dans AppliedSnapshot._feeder_to_dict (review adversariale 2026-06-09)
            # → afficher une valeur fantôme par défaut violerait la règle
            # « aucune valeur démo/défaut injectée silencieusement ».
            _comp = (_sel.get("config", {}) or {}).get("feeders_composition") or []
            if _comp:
                st.markdown("##### " + t("historique.comp_title"))
                _not_entered = t("historique.comp_not_entered")
                _cdf = pd.DataFrame([
                    {
                        t("historique.comp_col.feeder"): f"#{c.get('feeder_id', '?')}",
                        t("historique.comp_col.label"): c.get("label") or "—",
                        t("historique.comp_col.position"): c.get("position") or "—",
                        t("historique.comp_col.composition"):
                            c.get("composition") or _not_entered,
                        t("historique.comp_col.flow"):
                            _fmt_num(c.get("mass_flow_g_per_min"), 2),
                        t("historique.comp_col.density"):
                            _fmt_num(c.get("bulk_density_g_per_cm3"), 3),
                        t("historique.comp_col.tdeg"):
                            _fmt_num(c.get("t_degradation_C"), 0),
                    }
                    for c in _comp
                ])
                st.dataframe(_cdf, width="stretch", hide_index=True)
            else:
                st.caption(t("historique.comp_absent"))

            _zones = _sel.get("zones")
            # Phase S2 manager 2026-06-10 :
            #  - des agrégats TOUS à zéro (vis vide / débit nul au commit) ne
            #    sont PAS des résultats physiques → statut clair, pas de table
            #    de 0 trompeuse ;
            #  - la matière dominante est un label NOMINAL moteur (powder de
            #    démonstration) : en mode client elle est masquée via
            #    material_label (« Non renseigné ») — jamais de LFP inventé.
            _demo = is_demo_mode(st.session_state)

            def _zones_all_zero(zones: list) -> bool:
                """True si aucun agrégat n'est significatif (fill et résidence
                nuls sur toutes les zones)."""
                try:
                    return all(
                        float(z.get("fill_crete") or 0.0) <= 0.0
                        and float(z.get("residence_s") or 0.0) <= 0.0
                        for z in zones
                    )
                except (TypeError, ValueError):
                    return False

            if _zones and not _zones_all_zero(_zones):
                st.markdown("##### " + t("historique.zones_title"))
                _zdf = pd.DataFrame([
                    {
                        t("historique.zones_col.zone"): z.get("zone"),
                        t("historique.zones_col.fill_mean"): _fmt_num(z.get("fill_moyen"), 2),
                        t("historique.zones_col.fill_peak"): _fmt_num(z.get("fill_crete"), 2),
                        t("historique.zones_col.residence"): _fmt_num(z.get("residence_s"), 1),
                        t("historique.zones_col.material"): (
                            "—" if not z.get("matiere_dominante")
                            else (
                                z.get("matiere_dominante") if _demo
                                else t("historique.comp_not_entered")
                            )
                        ),
                    }
                    for z in _zones
                ])
                st.dataframe(_zdf, width="stretch", hide_index=True)
            elif _zones:
                st.caption(t("historique.zones_not_significant"))
            else:
                st.caption(t("historique.zones_absent"))

            # Statut agent : non figé au commit → affiché honnêtement comme absent.
            if _sel.get("agent"):
                st.markdown("##### " + t("historique.agent_title"))
                st.json(_sel["agent"])
            else:
                st.caption(t("historique.agent_absent"))

    if _load.skipped:
        st.caption(t("historique.skipped_note", n=_load.skipped))

# ---------------------------------------------------------------------------
# Section secondaire — essais d'entraînement ML (contenu existant, séparé)
# ---------------------------------------------------------------------------
st.divider()


@st.cache_data(show_spinner=False)
def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])


with st.expander(t("historique.ml.expander"), expanded=False):
    st.html(demo_ml_banner_html(t("historique.ml.banner")))
    st.caption(t("historique.ml.caption"))

    df_all = load_dataset()
    good = df_all[df_all["bad_run"] == 0].copy()

    summary = good.groupby("run_id").agg(
        debut=("window_start", "min"),
        fin=("window_end", "max"),
        duree_min=("run_duration_min", "first"),
        n_fenetres=("window_start", "count"),
        score_moyen=("stability_score", "mean"),
        score_min=("stability_score", "min"),
        score_max=("stability_score", "max"),
        pct_stable=("is_stable", "mean"),
    ).reset_index()

    summary["debut"]      = pd.to_datetime(summary["debut"]).dt.strftime("%Y-%m-%d %H:%M")
    summary["fin"]        = pd.to_datetime(summary["fin"]).dt.strftime("%H:%M")
    summary["pct_stable"]  = (summary["pct_stable"] * 100).round(0).astype(int)
    summary["score_moyen"] = summary["score_moyen"].round(1)
    summary["score_min"]   = summary["score_min"].round(1)
    summary["score_max"]   = summary["score_max"].round(1)

    _col_run = t("historique.ml.col.run")
    _col_start = t("historique.ml.col.start")
    _col_end = t("historique.ml.col.end")
    _col_dur = t("historique.ml.col.duration")
    _col_win = t("historique.ml.col.windows")
    _col_smean = t("historique.ml.col.score_mean")
    _col_smin = t("historique.ml.col.score_min")
    _col_smax = t("historique.ml.col.score_max")
    _col_pct = t("historique.ml.col.pct_stable")
    summary.columns = [_col_run, _col_start, _col_end, _col_dur,
                       _col_win, _col_smean, _col_smin,
                       _col_smax, _col_pct]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("historique.ml.m.runs"),   len(summary))
    col2.metric(t("historique.ml.m.duration"),    f"{good['run_duration_min'].drop_duplicates().sum():.0f} min")
    col3.metric(t("historique.ml.m.score"), f"{good['stability_score'].mean():.1f}")
    col4.metric(t("historique.ml.m.pct_stable"), f"{good['is_stable'].mean()*100:.0f} %")

    st.markdown(f"##### {t('historique.ml.summary_title')}")

    def color_score(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v >= THRESHOLD:
            return "background-color: #d4edda"
        if v >= 65:
            return "background-color: #fff3cd"
        return "background-color: #f8d7da"

    st.dataframe(
        summary.style.map(color_score, subset=[_col_smean, _col_smin]),
        width="stretch",
        hide_index=True,
    )

    st.markdown(f"##### {t('historique.ml.chart_title')}")
    chart_df = summary.set_index(_col_run)[[_col_smean]].copy()

    _bar_fig = go.Figure(go.Bar(
        x=[f"#{r}" for r in chart_df.index.tolist()],
        y=chart_df[_col_smean].tolist(),
        marker_color="#06B6D4",
        hovertemplate="<b>Run %{x}</b><br>Score: %{y:.1f}<extra></extra>",
    ))
    _bar_fig.add_hline(
        y=80, line_dash="dash", line_color="#374151",
        annotation_text=t("historique.ml.threshold"), annotation_font_color="#4B5563",
        annotation_font_size=10,
    )
    _bar_fig.update_layout(
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        height=250, margin=dict(l=0, r=0, t=5, b=0),
        showlegend=False,
        xaxis=dict(showgrid=False, color="#4B5563", tickfont=dict(size=10), zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#1F2937", color="#4B5563",
                   tickfont=dict(size=10), range=[0, 105], zeroline=False),
        hoverlabel=dict(bgcolor="#1F2937", font_color="#F9FAFB"),
    )
    st.plotly_chart(_bar_fig, width="stretch", key="hist_bar_chart")

    st.markdown(f"##### {t('historique.ml.states_title')}")

    def classify(score):
        if score >= THRESHOLD:
            return "STABLE"
        if score >= 65:
            return "WATCH"
        return "CRITICAL"

    good["etat"] = good["stability_score"].apply(classify)
    _col_state = t("historique.ml.col.state")
    _col_state_win = t("historique.ml.col.state_windows")
    counts = good["etat"].value_counts().rename_axis(_col_state).reset_index(name=_col_state_win)
    st.dataframe(counts, width="stretch", hide_index=True)

    st.caption(t("historique.ml.source_caption", n=len(good), th=THRESHOLD))

st.caption(t("historique.footer"))
