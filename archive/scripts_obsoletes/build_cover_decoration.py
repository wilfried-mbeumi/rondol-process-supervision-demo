# -*- coding: utf-8 -*-
"""Génère les lignes graphiques fines (courbes élégantes) de la page de garde.
Sortie : reports/assets/cover_curves.png (fond transparent)."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "assets" / "cover_curves.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

BLUE = "#1F4E79"
BLUE2 = "#2E75B6"
GREEN = "#1B7A3D"
GREY = "#9DA9B3"

fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# Faisceau de courbes fines partant du bas-gauche et s'élançant vers le haut-droite
x = np.linspace(0, 100, 400)
specs = [
    (-8, 0.0070, BLUE, 2.0, 1.0),
    (-2, 0.0062, BLUE2, 1.4, 0.9),
    (4, 0.0055, GREY, 1.1, 0.8),
    (10, 0.0048, GREEN, 1.2, 0.75),
    (16, 0.0042, GREY, 0.9, 0.6),
]
for base, k, color, lw, alpha in specs:
    y = base + k * (x ** 2)
    ax.plot(x, y, color=color, lw=lw, alpha=alpha, solid_capstyle="round")

fig.savefig(OUT, dpi=200, bbox_inches="tight", transparent=True)
plt.close(fig)
print("[OK]", OUT)
