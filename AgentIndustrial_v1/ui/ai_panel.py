"""
ai_panel.py — Rendu agent IA : score, alertes, recommandations actionnables.

Pas de chatbot, pas de marketing. Affichage industriel : bandeau état, liste
d'alertes avec sévérité + evidence, liste de recommandations avec delta
chiffré « avant → après ».
"""

from __future__ import annotations

import streamlit as st

from ..core.recommendations import Recommendation
from ..core.rules import AgentReport, Alert
from .styles import SEV_COLORS


_STATE_STYLE: dict[str, tuple[str, str]] = {
    "STABLE":     ("#10B981", "✦ Procédé nominal"),
    "SURVEILLER": ("#F59E0B", "▲ Surveillance renforcée"),
    "CRITIQUE":   ("#EF4444", "■ Intervention requise"),
}


def render_header(report: AgentReport) -> None:
    """Bandeau état + score (toujours rendu, structure DOM stable)."""
    color, label = _STATE_STYLE.get(report.state, ("#3B82F6", report.state))
    st.html(
        f'<div style="background:#0B0F14;border:1px solid {color};'
        f'border-left:4px solid {color};border-radius:0.3rem;'
        f'padding:0.65rem 1rem;display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:0.4rem;">'
        f'<div>'
        f'<div style="color:{color};font-weight:700;font-size:1.05rem;">'
        f'{label} — {report.state}</div>'
        f'<div style="color:#9CA3AF;font-size:0.85rem;margin-top:0.15rem;">'
        f'{report.diagnostic}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="color:#6B7280;font-size:0.65rem;font-weight:600;'
        f'letter-spacing:0.06em;">SCORE RISQUE</div>'
        f'<div style="color:{color};font-size:2rem;font-weight:700;'
        f'line-height:1;">{report.risk_score}<span style="color:#6B7280;'
        f'font-size:0.95rem;font-weight:500;"> /100</span></div>'
        f'</div>'
        f'</div>'
    )


def _alert_card_html(a: Alert) -> str:
    bg, fg, acc = SEV_COLORS.get(a.severity, SEV_COLORS["info"])
    target_chip = ""
    if a.target:
        target_chip = (
            f'<span style="background:rgba(255,255,255,0.04);color:{fg};'
            f'border:1px solid {acc};border-radius:0.2rem;'
            f'padding:0.1rem 0.45rem;font-size:0.7rem;font-weight:600;'
            f'letter-spacing:0.04em;">{a.target}</span>'
        )
    return (
        f'<div style="background:{bg};border-left:4px solid {acc};'
        f'border-radius:0.25rem;padding:0.55rem 0.85rem;margin-bottom:0.45rem;">'
        f'<div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;">'
        f'<span style="background:{acc};color:#0B0F14;font-weight:700;'
        f'font-size:0.66rem;padding:0.1rem 0.45rem;border-radius:0.2rem;'
        f'letter-spacing:0.06em;">{a.severity.upper()}</span>'
        f'{target_chip}'
        f'<span style="color:{fg};font-weight:600;font-size:0.92rem;">'
        f'{a.title}</span>'
        f'</div>'
        f'<div style="color:{fg};opacity:0.9;font-size:0.82rem;line-height:1.45;'
        f'margin-top:0.3rem;">{a.description}</div>'
        f'<div style="color:#6B7280;font-size:0.72rem;text-align:right;'
        f'margin-top:0.25rem;font-variant-numeric:tabular-nums;">'
        f'evidence · {a.evidence}</div>'
        f'</div>'
    )


def render_alerts(report: AgentReport) -> None:
    st.markdown("##### Alertes procédé")
    if not report.alerts:
        st.html(
            '<div style="background:#0f2b1d;border-left:4px solid #10B981;'
            'border-radius:0.25rem;padding:0.55rem 0.85rem;color:#bbf7d0;'
            'font-size:0.9rem;">✦ Aucune alerte — procédé nominal sur '
            "l'ensemble des règles évaluées.</div>"
        )
        return
    cards = "".join(_alert_card_html(a) for a in report.alerts)
    st.html(
        '<div style="background:#0B0F14;border:1px solid #1F2937;'
        'border-radius:0.3rem;padding:0.5rem;">' + cards + "</div>"
    )


_CAT_ACCENTS: dict[str, str] = {
    "feeder_move":   "#06B6D4",
    "flow_reduce":   "#F59E0B",
    "temperature":   "#EF4444",
    "screw_profile": "#A855F7",
    "screw_speed":   "#10B981",
    "other":         "#6B7280",
}


def _reco_card_html(r: Recommendation) -> str:
    acc = _CAT_ACCENTS.get(r.category, "#6B7280")
    sev_bg, sev_fg, sev_acc = SEV_COLORS.get(r.severity, SEV_COLORS["info"])
    return (
        f'<div style="background:#111827;border-left:4px solid {acc};'
        f'border-radius:0.25rem;padding:0.55rem 0.85rem;margin-bottom:0.5rem;">'
        f'<div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;">'
        f'<span style="background:{acc};color:#0B0F14;font-weight:700;'
        f'font-size:0.66rem;padding:0.1rem 0.45rem;border-radius:0.2rem;'
        f'letter-spacing:0.06em;">{r.category_label.upper()}</span>'
        f'<span style="background:rgba(255,255,255,0.04);color:{sev_fg};'
        f'border:1px solid {sev_acc};border-radius:0.2rem;'
        f'padding:0.1rem 0.4rem;font-size:0.68rem;font-weight:600;">'
        f'{r.severity.upper()}</span>'
        f'<span style="color:#F9FAFB;font-weight:600;font-size:0.93rem;">'
        f'{r.title}</span>'
        f'</div>'
        f'<div style="color:#D1D5DB;font-size:0.8rem;line-height:1.45;'
        f'margin-top:0.3rem;">'
        f'<span style="color:#6B7280;font-weight:600;font-size:0.66rem;'
        f'letter-spacing:0.04em;text-transform:uppercase;margin-right:0.3rem;">'
        f'Pourquoi</span>{r.rationale}</div>'
        f'<div style="color:#F9FAFB;font-size:0.85rem;line-height:1.5;'
        f'margin-top:0.3rem;">'
        f'<span style="color:{acc};font-weight:600;font-size:0.66rem;'
        f'letter-spacing:0.04em;text-transform:uppercase;margin-right:0.3rem;">'
        f'Action</span>{r.action}</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'margin-top:0.4rem;">'
        f'<span style="background:rgba(16,185,129,0.10);color:#bbf7d0;'
        f'border:1px solid #10B981;border-radius:0.2rem;'
        f'padding:0.1rem 0.45rem;font-size:0.74rem;font-weight:600;'
        f'font-variant-numeric:tabular-nums;">Δ {r.delta_label}</span>'
        f'<span style="color:#6B7280;font-size:0.7rem;">'
        f'confiance · {r.confidence}</span>'
        f'</div>'
        f'</div>'
    )


def render_recommendations(recs: list[Recommendation]) -> None:
    st.markdown("##### Recommandations actionnables")
    st.caption(
        "Une recommandation = une action chiffrée (delta avant → après). "
        "Catégories : déplacement feeder · ajustement débit · ajustement "
        "température · modification profil vis · vitesse vis."
    )
    if not recs:
        st.html(
            '<div style="background:#111827;border:1px solid #1F2937;'
            'border-radius:0.3rem;padding:0.55rem 0.85rem;color:#9CA3AF;'
            'font-style:italic;font-size:0.88rem;">'
            "Aucune recommandation — l'état actuel est sain.</div>"
        )
        return
    # Priorité : critical d'abord
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    recs_sorted = sorted(recs, key=lambda r: (sev_order.get(r.severity, 9), r.category))
    cards = "".join(_reco_card_html(r) for r in recs_sorted)
    st.html(
        '<div style="background:#0B0F14;border:1px solid #1F2937;'
        'border-radius:0.3rem;padding:0.5rem;">' + cards + "</div>"
    )
