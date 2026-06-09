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
from rondol_i18n import t  # noqa: E402

restore_operator_state(st.session_state)

DATASET_PATH = ROOT / "data" / "features" / "dataset_ml_w60.csv"
THRESHOLD = 80

st.set_page_config(page_title="Historique des procédés — Rondol", layout="wide")

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


_SOURCE_LABELS = {
    "manual": "Manuel",
    "demonstration": "Démonstration",
}


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
        "Statut": "● Actif" if status == "actif" else "Archivé",
        "Date / heure": _fmt_timestamp(rec.get("timestamp_iso", "")),
        "Label": rec.get("label") or "—",
        "Source": _SOURCE_LABELS.get(rec.get("source", ""), "Manuel"),
        "Vis (tr/min)": _fmt_num(cfg.get("screw_rpm"), 0),
        "Débit princ. (g/min)": _fmt_num(cfg.get("debit_principal_g_min"), 1),
        "Matière": cfg.get("matiere_principale") or "—",
        "Zones die": str(int(cfg.get("zones_die", 0) or 0)),
        "Éléments": n_el_str,
        "Couple (N·m)": _fmt_num(kpi.get("couple_total_nm"), 3),
        "SME (kWh/kg)": _fmt_num(kpi.get("sme_kwh_kg"), 4),
        "Résidence (s)": _fmt_num(kpi.get("residence_s"), 1),
        "Fill moy.": _fmt_num(kpi.get("fill_moyen"), 2),
        "Fill crête": _fmt_num(kpi.get("fill_crete"), 2),
        "Cisaill. max (1/s)": _fmt_num(kpi.get("cisaillement_max_s"), 0),
    }


def _status_style(val: str) -> str:
    """Couleur de la cellule Statut (vert = actif, gris = archivé)."""
    if "Actif" in val:
        return "color:#10B981;font-weight:600"
    return "color:#9CA3AF"


# ===========================================================================
#  RENDU
# ===========================================================================
st.html(
    f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;border-radius:0.3rem;'
    f'display:flex;justify-content:space-between;align-items:center;color:white;'
    f'font-weight:600;font-size:1rem;margin-bottom:0.5rem;">'
    f'<span>● Rondol · Historique des procédés</span>'
    f'<span style="font-size:0.85rem;opacity:0.9;">Configurations enregistrées (persistant)</span>'
    f'</div>'
)

st.markdown("## Historique des procédés")
st.caption(
    "Configurations validées (« Enregistrer » dans Paramètres IA & feeders), "
    "conservées sur disque et restaurées au redémarrage. Lecture seule — KPIs "
    "moteur figés au moment de l'enregistrement, aucune valeur recalculée."
)

# ---------------------------------------------------------------------------
# Section principale — historique procédé PERSISTANT (data/history/*.json)
# ---------------------------------------------------------------------------
_load = history_store.read_runs()
_runs = _load.runs

if _load.corrupt:
    # Robustesse : fichier illisible → message discret, pas de crash.
    st.warning(
        "Fichier d'historique illisible — affichage ignoré pour cette lecture. "
        "Les prochains enregistrements repartiront sur une base saine.",
        icon="⚠️",
    )

if not _runs:
    st.info(
        "**Aucun historique procédé enregistré.** "
        "L'historique se remplira après l'enregistrement d'une configuration "
        "(page **Paramètres IA & feeders → Enregistrer**) et sera conservé même "
        "après redémarrage de l'application.",
        icon="ℹ️",
    )
else:
    # Métriques d'en-tête (comptages — pas de calcul procédé).
    _active = next((r for r in _runs if r.get("status") == "actif"), _runs[-1])
    _active_label = _active.get("label") or _fmt_timestamp(_active.get("timestamp_iso", ""))
    h1, h2, h3 = st.columns(3)
    h1.metric("Procédés enregistrés", str(len(_runs)))
    h2.metric("Dernier enregistrement", _fmt_timestamp(_runs[-1].get("timestamp_iso", "")))
    h3.metric("Procédé actif", _active_label)

    # Filtres simples (statut / source / date) — sur les records, pas de recalcul.
    _dates = sorted(
        {(r.get("timestamp_iso", "") or "")[:10] for r in _runs if r.get("timestamp_iso")},
        reverse=True,
    )
    f1, f2, f3 = st.columns(3)
    _f_status = f1.selectbox("Statut", ["Tous", "Actif", "Archivé"], key="hist_f_status")
    _f_source = f2.selectbox("Source", ["Toutes", "Manuel", "Démonstration"], key="hist_f_source")
    _f_date = f3.selectbox("Date", ["Toutes"] + _dates, key="hist_f_date")

    def _keep(r: dict) -> bool:
        if _f_status == "Actif" and r.get("status") != "actif":
            return False
        if _f_status == "Archivé" and r.get("status") == "actif":
            return False
        if _f_source != "Toutes" and _SOURCE_LABELS.get(r.get("source", ""), "Manuel") != _f_source:
            return False
        if _f_date != "Toutes" and (r.get("timestamp_iso", "") or "")[:10] != _f_date:
            return False
        return True

    _filtered = [r for r in _runs if _keep(r)]

    if not _filtered:
        st.caption("Aucun procédé ne correspond aux filtres sélectionnés.")
    else:
        # Tableau — plus récent en haut.
        _rows = [_record_to_row(r) for r in reversed(_filtered)]
        _df = pd.DataFrame(_rows)
        with st.container(border=True):
            st.dataframe(
                _df.style.map(_status_style, subset=["Statut"]),
                use_container_width=True,
                hide_index=True,
            )

        # ---- Détail d'un procédé (agrégats zones + statut agent) -------------
        def _run_caption(r: dict) -> str:
            ts = _fmt_timestamp(r.get("timestamp_iso", ""))
            lbl = r.get("label") or "(sans libellé)"
            return f"{ts} · {lbl}"

        _options = list(reversed(_filtered))
        _idx = st.selectbox(
            "Voir le détail d'un procédé",
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
                st.dataframe(_cdf, use_container_width=True, hide_index=True)
            else:
                st.caption(t("historique.comp_absent"))

            _zones = _sel.get("zones")
            if _zones:
                st.markdown("##### Agrégats par zone (figés au commit)")
                _zdf = pd.DataFrame([
                    {
                        "Zone": z.get("zone"),
                        "Fill moyen": _fmt_num(z.get("fill_moyen"), 2),
                        "Fill crête": _fmt_num(z.get("fill_crete"), 2),
                        "Résidence (s)": _fmt_num(z.get("residence_s"), 1),
                        "Matière dominante": z.get("matiere_dominante") or "—",
                    }
                    for z in _zones
                ])
                st.dataframe(_zdf, use_container_width=True, hide_index=True)
            else:
                st.caption("Agrégats par zone non disponibles pour ce procédé.")

            # Statut agent : non figé au commit → affiché honnêtement comme absent.
            if _sel.get("agent"):
                st.markdown("##### Statut agent (figé)")
                st.json(_sel["agent"])
            else:
                st.caption(
                    "Statut agent (décision / score / alertes) : non disponible — "
                    "non figé au moment de l'enregistrement."
                )

    if _load.skipped:
        st.caption(f"Note : {_load.skipped} entrée(s) illisible(s) ignorée(s).")

# ---------------------------------------------------------------------------
# Section secondaire — essais d'entraînement ML (contenu existant, séparé)
# ---------------------------------------------------------------------------
st.divider()


@st.cache_data(show_spinner=False)
def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])


with st.expander("Essais d'entraînement ML — données historiques modèle", expanded=False):
    st.html(demo_ml_banner_html(
        "Runs du jeu d'entraînement ML (SVM w60, essais avril 2026) — "
        "<b>démonstration</b>, strictement distincts de l'historique procédé opérateur."
    ))
    st.caption(
        "Runs du jeu de données d'entraînement (modèle SVM w60, essais Avril 2026). "
        "Données historiques du modèle — distinctes de l'historique procédé opérateur."
    )

    df_all = load_dataset()
    good = df_all[df_all["bad_run"] == 0].copy()

    # Résumé par run
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

    summary.columns = ["Run", "Début", "Fin", "Durée (min)",
                       "Fenêtres", "Score moyen", "Score min",
                       "Score max", "% Stable"]

    # Métriques globales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Runs analysés",   len(summary))
    col2.metric("Durée totale",    f"{good['run_duration_min'].drop_duplicates().sum():.0f} min")
    col3.metric("Score global moy.", f"{good['stability_score'].mean():.1f}")
    col4.metric("% fenêtres stables", f"{good['is_stable'].mean()*100:.0f} %")

    st.markdown("##### Résumé par run d'entraînement")

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
        summary.style.map(color_score, subset=["Score moyen", "Score min"]),
        use_container_width=True,
        hide_index=True,
    )

    # Graphique comparatif
    st.markdown("##### Score moyen par run")
    chart_df = summary.set_index("Run")[["Score moyen"]].copy()

    _bar_fig = go.Figure(go.Bar(
        x=[f"#{r}" for r in chart_df.index.tolist()],
        y=chart_df["Score moyen"].tolist(),
        marker_color="#06B6D4",
        hovertemplate="<b>Run %{x}</b><br>Score: %{y:.1f}<extra></extra>",
    ))
    _bar_fig.add_hline(
        y=80, line_dash="dash", line_color="#374151",
        annotation_text="Seuil 80", annotation_font_color="#4B5563",
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
    st.plotly_chart(_bar_fig, use_container_width=True, key="hist_bar_chart")

    # Répartition des états
    st.markdown("##### Répartition des états sur l'ensemble des runs")

    def classify(score):
        if score >= THRESHOLD:
            return "STABLE"
        if score >= 65:
            return "SURVEILLER"
        return "CRITIQUE"

    good["etat"] = good["stability_score"].apply(classify)
    counts = good["etat"].value_counts().rename_axis("État").reset_index(name="Fenêtres")
    st.dataframe(counts, use_container_width=True, hide_index=True)

    st.caption(
        f"Source : dataset_ml_w60.csv · {len(good)} fenêtres · "
        f"Seuil stable = {THRESHOLD}/100 · Seuil critique = 65/100"
    )

st.caption("Rondol Industrie · Historique des procédés (persistant) · Prototype")
