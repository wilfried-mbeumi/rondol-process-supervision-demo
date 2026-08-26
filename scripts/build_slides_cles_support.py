"""build_slides_cles_support.py — Recompose les diapositives d'ouverture du support.

Trois pages portent l'essentiel du premier regard du jury et n'étaient pas au
niveau du reste : la couverture (première impression), le sommaire (laissé
déséquilibré par le retrait d'un bandeau) et la problématique — qui énonce la
question centrale du mémoire en petits caractères, alors qu'elle devrait
dominer la page.

Elles sont recomposées dans la charte du support, en 16:9, prêtes à substituer.

Sorties : reports/soutenance/slide_couverture.png
          reports/soutenance/slide_sommaire.png
          reports/soutenance/slide_problematique.png

Usage : python scripts/build_slides_cles_support.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "soutenance"
NEXA = ROOT / "reports" / "assets" / "nexa_logo.png"
RONDOL = ROOT / "assets" / "rondol_logo.png"

FOND = "#123331"
FONCE = "#0C2422"
CREME = "#F5EFE3"
TEXTE = "#DCE6E3"
TEAL = "#2FB39B"
GRIS = "#93A8A3"
AMBRE = "#E8A33D"
BLEU = "#6FA8D6"

W, H = 13.333, 7.5


def page():
    fig = plt.figure(figsize=(W, H), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.axis("off"); ax.set_facecolor(FOND)
    return fig, ax


def carte(ax, x, y, w, h, couleur, alpha=0.13, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=couleur, alpha=alpha,
                                edgecolor=couleur, linewidth=lw))


def poser_logo(fig, chemin: Path, x, y, largeur_pouces):
    """Place un logo en coordonnées figure, hauteur déduite du ratio.

    Les logos fournis sont sur fond blanc opaque : posés tels quels sur le vert
    foncé, ils y découpent un rectangle blanc. Le blanc est donc rendu
    transparent avant placement.
    """
    if not chemin.exists():
        return
    import numpy as np

    img = mpimg.imread(chemin)
    if img.dtype != np.float32 and img.max() > 1:
        img = img.astype(float) / 255.0
    if img.ndim == 3 and img.shape[2] == 3:                 # RGB -> RGBA
        img = np.dstack([img, np.ones(img.shape[:2])])
    if img.ndim == 3 and img.shape[2] == 4:
        blanc = (img[..., 0] > 0.88) & (img[..., 1] > 0.88) & (img[..., 2] > 0.88)
        img = img.copy()
        img[blanc, 3] = 0.0

    ratio = img.shape[0] / img.shape[1]
    axl = fig.add_axes([x / W, y / H, largeur_pouces / W,
                        largeur_pouces * ratio / H])
    axl.imshow(img)
    axl.axis("off")
    axl.patch.set_alpha(0)


def enregistrer(fig, nom: str) -> Path:
    p = OUT / nom
    fig.savefig(p, facecolor=FOND)
    plt.close(fig)
    return p


# ------------------------------------------------------------- couverture
def couverture() -> Path:
    fig, ax = page()
    # Bande d'accent verticale : ancre le regard à gauche sans surcharger.
    ax.add_patch(Rectangle((0, 0), 0.20, H, facecolor=TEAL))
    ax.add_patch(Rectangle((0.20, 0), 0.06, H, facecolor=AMBRE, alpha=0.55))

    ax.text(1.15, 6.82, "MÉMOIRE DE FIN D'ÉTUDES", color=TEAL, fontsize=12.5,
            family="serif", va="center")
    ax.text(1.15, 6.42, "Mastère 2 Data & Intelligence Artificielle  ·  RNCP 37137 — niveau 7",
            color=GRIS, fontsize=12, family="serif", va="center")

    ax.plot([1.15, 12.4], [6.05, 6.05], color=TEAL, linewidth=1.4, alpha=0.6)

    ax.text(1.15, 5.42,
            "Conception et déploiement d'un système\n"
            "d'intelligence artificielle prédictif",
            color=CREME, fontsize=30, family="serif", va="center", linespacing=1.32)
    ax.text(1.15, 3.88,
            "d'aide à la décision pour l'optimisation des paramètres d'extrusion\n"
            "bivis de composants de batteries tout-solide (voie sèche)",
            color=TEXTE, fontsize=15, family="serif", va="center", linespacing=1.5)

    carte(ax, 1.15, 2.48, 11.25, 0.86, TEAL, 0.12)
    ax.text(1.5, 2.91,
            "Un jumeau numérique et une IA explicable pour l'extrudeuse bivis "
            "10,5 mm de Rondol Industrie",
            color=CREME, fontsize=13.5, family="serif", style="italic", va="center")

    ax.text(1.15, 1.92, "Wilfried Galtier MBEUMI", color=CREME, fontsize=17,
            family="serif", weight="bold", va="center")
    ax.text(1.15, 1.50, "Nexa Digital School  ·  Année universitaire 2025 – 2026",
            color=TEXTE, fontsize=12, family="serif", va="center")
    ax.text(1.15, 1.14,
            "Encadrement industriel : M. Maël Gallas — Rondol Industrie      "
            "Tuteur pédagogique : M. Moussa NDIAYE",
            color=GRIS, fontsize=11, family="serif", va="center")

    ax.plot([1.15, 12.4], [0.78, 0.78], color=TEAL, linewidth=0.9, alpha=0.35)
    ax.text(12.4, 0.42, "Soutenance — 9 septembre 2026", color=GRIS, fontsize=11,
            family="serif", ha="right", va="center")

    poser_logo(fig, RONDOL, 1.15, 0.22, 1.85)
    poser_logo(fig, NEXA, 3.45, 0.20, 1.55)
    return enregistrer(fig, "slide_couverture.png")


# --------------------------------------------------------------- sommaire
def sommaire() -> Path:
    fig, ax = page()
    ax.add_patch(Rectangle((0, 0), 0.20, H, facecolor=TEAL))

    ax.text(1.1, 6.72, "PLAN", color=TEAL, fontsize=12, family="serif", va="center")
    ax.text(1.1, 6.05, "Déroulé de la présentation", color=CREME, fontsize=27,
            family="serif", va="center")

    sections = [
        ("01", "Contexte & marché", "Rondol · batteries tout-solide · concurrence · SWOT", TEAL),
        ("02", "Problématique", "Trois exigences non négociables", TEAL),
        ("03", "Solution technique", "Architecture · vis · physique · agent explicable", TEAL),
        ("04", "Données & modélisation", "Campagne réelle · protocole · championnat", BLEU),
        ("05", "Résultats & intégrité", "Fuite identifiée · modèle corrigé · validation", AMBRE),
        ("06", "Application & jumeau", "HMI industrielle · démonstration · cinq cas", BLEU),
        ("07", "Gestion de projet", "Kanban · veille · budget · qualité logicielle", TEAL),
        ("08", "Conclusion", "Acquis · limites assumées · perspectives", CREME),
    ]
    for i, (num, titre, desc, coul) in enumerate(sections):
        col, rang = i // 4, i % 4
        x = 1.1 + col * 5.75
        y = 4.55 - rang * 1.18
        carte(ax, x, y, 5.35, 0.98, coul, 0.10)
        ax.text(x + 0.34, y + 0.49, num, color=coul, fontsize=20,
                family="serif", weight="bold", va="center")
        ax.text(x + 1.15, y + 0.66, titre, color=CREME, fontsize=13.5,
                family="serif", weight="bold", va="center")
        ax.text(x + 1.15, y + 0.28, desc, color=GRIS, fontsize=10.5,
                family="serif", va="center")

    carte(ax, 1.1, 0.32, 11.1, 0.62, TEAL, 0.14)
    ax.text(1.45, 0.63,
            "Fil conducteur : rendre un procédé d'extrusion lisible, comparable "
            "et prédictible — sans présenter une valeur non calibrée comme une mesure.",
            color=CREME, fontsize=12.5, family="serif", style="italic", va="center")
    return enregistrer(fig, "slide_sommaire.png")


# ---------------------------------------------------------- problématique
def problematique() -> Path:
    fig, ax = page()
    ax.add_patch(Rectangle((0, 0), 0.20, H, facecolor=AMBRE))

    ax.text(1.1, 6.85, "02 — PROBLÉMATIQUE", color=AMBRE, fontsize=12,
            family="serif", va="center")

    # La question centrale occupe le haut de page : c'est elle qu'on doit lire.
    ax.text(1.1, 5.62,
            "Comment concevoir un système d'aide à la décision\n"
            "qui rende un procédé d'extrusion bivis\n"
            "lisible, comparable et prédictible ?",
            color=CREME, fontsize=27, family="serif", va="center", linespacing=1.42)

    ax.plot([1.1, 12.25], [4.12, 4.12], color=AMBRE, linewidth=1.3, alpha=0.7)
    ax.text(1.1, 3.72,
            "Trois exigences que je me suis imposées, et qui ont arbitré chaque décision technique",
            color=GRIS, fontsize=12.5, family="serif", style="italic", va="center")

    exigences = [
        ("TRAÇABLE", TEAL,
         "Toute valeur affichée doit\ns'expliquer à un ingénieur\nprocédé.",
         "Pas de boîte noire qui sort un nombre."),
        ("HONNÊTE", AMBRE,
         "Ce qui n'est pas calibré est\nannoncé comme tel.",
         "C'est l'exigence qui m'a coûté le plus cher."),
        ("DÉMONTRABLE", BLEU,
         "Utilisable devant un client,\npas une maquette.",
         "Déployé, testé, rejouable."),
    ]
    for i, (titre, coul, corps, note) in enumerate(exigences):
        x = 1.1 + i * 3.78
        carte(ax, x, 0.72, 3.5, 2.72, coul, 0.13)
        ax.text(x + 0.32, 2.98, titre, color=coul, fontsize=15,
                family="serif", weight="bold", va="center")
        ax.plot([x + 0.32, x + 1.5], [2.68, 2.68], color=coul, linewidth=1.2, alpha=0.7)
        ax.text(x + 0.32, 2.02, corps, color=TEXTE, fontsize=12,
                family="serif", va="center", linespacing=1.55)
        ax.text(x + 0.32, 1.08, note, color=GRIS, fontsize=10.5,
                family="serif", style="italic", va="center")
    return enregistrer(fig, "slide_problematique.png")


if __name__ == "__main__":
    for f in (couverture(), sommaire(), problematique()):
        print(f"[OK] {f.name} — {f.stat().st_size / 1024:.0f} Ko")
