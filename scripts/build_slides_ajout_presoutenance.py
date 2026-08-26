"""build_slides_ajout_presoutenance.py — Compose les deux diapositives ajoutées après la pré-soutenance.

Sorties (format 16:9, prêtes à insérer dans le support) :
  reports/soutenance/slide_augmentation.png
  reports/soutenance/slide_choix_modeles.png

1. « Augmentation de données » répond à la remarque du jury sur le faible volume :
   le synthétique a été produit et mesuré, le gain est nul pour le modèle retenu.
2. « Pourquoi ces cinq modèles » répond à une question annoncée comme récurrente.

La charte reprend celle du support (fond #123331, crème, accent teal) pour que les
diapositives s'insèrent sans rupture visuelle.

Usage : python scripts/build_slides_ajout_presoutenance.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "soutenance"

FOND = "#123331"
CREME = "#F5EFE3"
TEAL = "#2FB39B"
GRIS = "#9FB3AE"
BLANC = "#FFFFFF"
AMBRE = "#E8A33D"

W, H = 13.333, 7.5   # 16:9


def base(titre: str, eyebrow: str):
    fig = plt.figure(figsize=(W, H), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.axis("off"); ax.set_facecolor(FOND)

    # étiquette de partie
    ax.add_patch(Rectangle((0.8, H - 0.95), 3.05, 0.42,
                           facecolor="none", edgecolor=CREME, linewidth=0.9))
    ax.text(0.95, H - 0.74, eyebrow, color=CREME, fontsize=10.5,
            va="center", family="serif")
    ax.text(0.8, H - 1.62, titre, color=CREME, fontsize=27,
            va="center", family="serif")
    return fig, ax


def carte(ax, x, y, w, h, couleur=TEAL, alpha=0.10):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.10",
                                facecolor=couleur, alpha=alpha,
                                edgecolor=couleur, linewidth=1.0))


# ------------------------------------------------------- slide 1
def slide_augmentation() -> Path:
    fig, ax = base("L'augmentation de données : testée, mesurée",
                   "04 — DONNÉES & MODÉLISATION")

    ax.text(0.8, 5.45,
            "Base synthétique de 100 800 lignes générée à partir des huit essais réels",
            color=GRIS, fontsize=13, va="center", family="serif", style="italic")

    lignes = [
        ("Random Forest",           "0,809", "0,809", "−0,001", True),
        ("SVM (RBF)",               "0,805", "0,824", "+0,018", False),
        ("Régression logistique",   "0,799", "0,809", "+0,010", False),
        ("XGBoost",                 "0,757", "0,801", "+0,044", False),
        ("Réseau de neurones (MLP)", "0,778", "0,781", "+0,004", False),
    ]
    cols = [1.0, 5.6, 7.9, 10.3]
    y0 = 4.95

    for lbl, x in zip(["MODÈLE", "SANS AUGM.", "AVEC AUGM.", "GAIN"], cols):
        ax.text(x, y0, lbl, color=GRIS, fontsize=9.5, va="center",
                family="sans-serif", weight="bold")
    ax.plot([0.9, 12.5], [y0 - 0.24, y0 - 0.24], color=TEAL, linewidth=1.6)

    for i, (nom, sans, avec, gain, retenu) in enumerate(lignes):
        y = y0 - 0.72 - i * 0.60
        if retenu:
            carte(ax, 0.9, y - 0.25, 11.6, 0.52, TEAL, 0.16)
        c = CREME if retenu else "#D8E2DF"
        p = "bold" if retenu else "normal"
        ax.text(cols[0], y, nom, color=c, fontsize=13, va="center",
                family="serif", weight=p)
        ax.text(cols[1], y, sans, color=c, fontsize=13, va="center", family="serif")
        ax.text(cols[2], y, avec, color=TEAL if retenu else c, fontsize=13,
                va="center", family="serif", weight=p)
        ax.text(cols[3], y, gain, color=AMBRE if retenu else GRIS,
                fontsize=13, va="center", family="serif", weight=p)
        ax.plot([0.9, 12.5], [y - 0.31, y - 0.31], color="#2A4A45", linewidth=0.6)

    carte(ax, 0.8, 0.32, 11.75, 0.96, TEAL, 0.14)
    ax.text(1.05, 0.98,
            "Le synthétique ne crée pas d'information absente des données réelles.",
            color=CREME, fontsize=13.5, va="center", family="serif", weight="bold")
    ax.text(1.05, 0.62,
            "Le protocole initial annonçait +0,109 : le pool était généré une seule fois "
            "sur les huit essais, donc l'essai de test alimentait l'entraînement.",
            color=GRIS, fontsize=11, va="center", family="serif")

    out = OUT / "slide_augmentation.png"
    fig.savefig(out, facecolor=FOND, bbox_inches=None)
    plt.close(fig)
    return out


# ------------------------------------------------------- slide 2
def slide_choix_modeles() -> Path:
    fig, ax = base("Cinq familles, pas cinq algorithmes au hasard",
                   "04 — DONNÉES & MODÉLISATION")

    lignes = [
        ("Régression logistique",    "Séparabilité linéaire",  "Référence basse, entièrement interprétable"),
        ("SVM (noyau RBF)",          "Frontières non linéaires", "Robuste quand les échantillons sont peu nombreux"),
        ("Random Forest",            "Ensemble par bagging",   "Donne l'importance des variables — explicabilité"),
        ("XGBoost",                  "Ensemble par boosting",  "Référence sur données tabulaires"),
        ("Réseau de neurones (MLP)", "Non-linéarité profonde", "Vérifie qu'un modèle plus expressif n'apporte rien"),
    ]
    cols = [1.05, 4.75, 7.85]
    y0 = 5.35

    for lbl, x in zip(["MODÈLE", "CE QU'IL TESTE", "POURQUOI LUI"], cols):
        ax.text(x, y0, lbl, color=GRIS, fontsize=9.5, va="center",
                family="sans-serif", weight="bold")
    ax.plot([0.9, 12.5], [y0 - 0.24, y0 - 0.24], color=TEAL, linewidth=1.6)

    for i, (nom, teste, pourquoi) in enumerate(lignes):
        y = y0 - 0.78 - i * 0.68
        retenu = nom.startswith("Random")
        if retenu:
            carte(ax, 0.9, y - 0.28, 11.6, 0.58, TEAL, 0.16)
        c = CREME if retenu else "#D8E2DF"
        ax.text(cols[0], y, nom, color=c, fontsize=12.5, va="center",
                family="serif", weight="bold" if retenu else "normal")
        ax.text(cols[1], y, teste, color=GRIS, fontsize=11.5, va="center", family="serif")
        ax.text(cols[2], y, pourquoi, color=c, fontsize=11.5, va="center", family="serif")
        ax.plot([0.9, 12.5], [y - 0.34, y - 0.34], color="#2A4A45", linewidth=0.6)

    carte(ax, 0.8, 0.45, 11.75, 1.15, AMBRE, 0.12)
    ax.text(1.05, 1.28, "Écartés volontairement", color=AMBRE, fontsize=12.5,
            va="center", family="serif", weight="bold")
    ax.text(1.05, 0.92,
            "L'apprentissage profond — huit essais, il mémoriserait les essais plutôt que le procédé.",
            color="#D8E2DF", fontsize=11, va="center", family="serif")
    ax.text(1.05, 0.62,
            "Les modèles séquentiels — les fenêtres de 60 s sont déjà agrégées en 87 descripteurs.",
            color="#D8E2DF", fontsize=11, va="center", family="serif")

    out = OUT / "slide_choix_modeles.png"
    fig.savefig(out, facecolor=FOND, bbox_inches=None)
    plt.close(fig)
    return out


if __name__ == "__main__":
    for f in (slide_augmentation(), slide_choix_modeles()):
        print(f"[OK] {f.name} — {f.stat().st_size / 1024:.0f} Ko")
