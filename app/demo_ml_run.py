"""demo_ml_run.py — couche « données ML de démonstration » (séparée du run réel).

Le dataset `dataset_ml_w60.csv` (essais avril 2026) sert de DÉMONSTRATION du
pilier ML (score de stabilité, P(stable), capteurs, durée d'essai). Ce N'EST PAS
un run opérateur live. Ce module centralise :
  - le marquage DEMO (badge + bandeau) réutilisable par Supervision / Analyse /
    Historique ;
  - la liste des métriques ML qui ne doivent JAMAIS être présentées comme une
    vérité opérateur ni alimenter une recommandation opérateur réelle.

`demo_ml_run` est STRICTEMENT distinct de `current_run_state` (config opérateur).
Aucune fonction ici ne lit ni ne modifie `current_run_state`.
"""

from __future__ import annotations

# Colonnes du dataset ML qui sont des métriques de démonstration (jamais une
# vérité opérateur). Utilisé par les gardes de séparation/tests.
DEMO_ML_METRIC_COLUMNS = (
    "stability_score", "is_stable", "proba_stable",
    "run_duration_min", "target_horizon_sec", "bad_run",
)

def _banner_default() -> str:
    try:
        from rondol_i18n import t as _t
        return _t("demo.ml.banner_default")
    except Exception:
        return (
            "Indicateurs issus du <b>dataset ML d'essais (avril 2026)</b> — données de "
            "<b>démonstration</b>, non un run opérateur live."
        )


def demo_ml_badge_html() -> str:
    """Pastille « DEMO ML » inline (HTML)."""
    return (
        '<span style="background:#7C3AED;color:#fff;font-weight:700;font-size:0.6rem;'
        'letter-spacing:0.06em;padding:0.05rem 0.4rem;border-radius:0.25rem;">DEMO ML</span>'
    )


def demo_ml_banner_html(text: str | None = None) -> str:
    """Bandeau violet « DEMO ML » — à placer au-dessus de toute donnée ML."""
    body = text or _banner_default()
    return (
        '<div style="display:flex;align-items:center;gap:0.5rem;'
        'background:rgba(124,58,237,0.10);border:1px solid rgba(124,58,237,0.35);'
        'border-radius:0.4rem;padding:0.4rem 0.7rem;margin:0.3rem 0;'
        'color:#C4B5FD;font-size:0.82rem;">'
        + demo_ml_badge_html()
        + f"<span>{body}</span></div>"
    )


def is_demo_ml_metric(name: str) -> bool:
    """True si `name` est une métrique du dataset ML de démonstration."""
    return name in DEMO_ML_METRIC_COLUMNS
