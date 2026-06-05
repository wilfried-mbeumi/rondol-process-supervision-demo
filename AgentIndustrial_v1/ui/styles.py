"""
styles.py — Palette + CSS cohérent avec l'existant Kévin (Supervision.py).
"""

from __future__ import annotations

# Palette Rondol — reprend les couleurs HMI existantes
RONDOL_GREEN = "#4CAF50"
BG = "#0B0F14"
CARD = "#111827"
BORDER = "#1F2937"
TEXT = "#F9FAFB"
SUB = "#9CA3AF"
MUTED = "#374151"
CYAN = "#06B6D4"

SEV_COLORS: dict[str, tuple[str, str, str]] = {
    "critical": ("#3b1212", "#fecaca", "#EF4444"),
    "warning":  ("#3b2c0a", "#fde68a", "#F59E0B"),
    "info":     ("#0f1d3b", "#bfdbfe", "#3B82F6"),
    "ok":       ("#0f2b1d", "#bbf7d0", "#10B981"),
}

GLOBAL_CSS = """
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
</style>
"""


def header_banner_html(subtitle: str) -> str:
    return (
        f'<div style="background:{RONDOL_GREEN};padding:0.55rem 1rem;'
        f'border-radius:0.3rem;display:flex;justify-content:space-between;'
        f'align-items:center;color:white;font-weight:600;font-size:1rem;'
        f'margin-bottom:0.5rem;">'
        f'<span>● Rondol · AgentIndustrial V1</span>'
        f'<span style="font-size:0.85rem;opacity:0.9;">{subtitle}</span>'
        f'</div>'
    )
