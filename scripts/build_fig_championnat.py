# -*- coding: utf-8 -*-
"""Figure « championnat des modèles supervisés » pour le mémoire.

Représente le F1-macro moyen ± écart-type de chaque modèle en validation
Leave-One-Group-Out (un essai laissé de côté à chaque pli, 8 essais), c'est-à-
dire la mesure honnête : aucun modèle n'est évalué sur un essai qu'il a vu.

Sortie : figures_memoire/fig_championnat_modeles.png
Source : reports/model_comparison_logo_w60.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "model_comparison_logo_w60.json"
# Le pipeline du mémoire lit les figures dans reports/memoire_figures/ ;
# figures_memoire/ est la copie livrable (alimentée par build_memoire_pro.py).
OUT = ROOT / "reports" / "memoire_figures" / "fig_championnat_modeles.png"

# Palette sobre, cohérente avec la charte du mémoire (bleu institutionnel).
BLEU = "#1F4E79"
BLEU_CLAIR = "#8FAFCB"
ACCENT = "#0E7C6B"
GRIS = "#5A6675"
GRILLE = "#DDE3EA"

LABELS = {
    "LogisticRegression": "Régression\nlogistique",
    "RandomForest": "Random\nForest",
    "SVM_RBF": "SVM (RBF)",
    "XGBoost": "XGBoost",
    "MLP": "Réseau de\nneurones (MLP)",
}


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    models = data["models"]
    # Tri décroissant par F1-macro moyen
    items = sorted(models.items(), key=lambda kv: kv[1]["logo_f1_macro_mean"], reverse=True)
    noms = [LABELS.get(k, k) for k, _ in items]
    moy = [v["logo_f1_macro_mean"] for _, v in items]
    ect = [v["logo_f1_macro_std"] for _, v in items]

    fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = range(len(noms))
    # Le modèle retenu (Random Forest) est mis en avant.
    couleurs = [ACCENT if "Random" in n else BLEU_CLAIR for n in noms]
    bars = ax.bar(x, moy, yerr=ect, capsize=5, color=couleurs,
                  edgecolor=BLEU, linewidth=0.8, width=0.62,
                  error_kw={"ecolor": GRIS, "elinewidth": 1.1, "alpha": 0.9})

    for xi, (m, e) in enumerate(zip(moy, ect)):
        ax.text(xi, m + e + 0.022, f"{m:.3f}".replace(".", ","),
                ha="center", va="bottom", fontsize=10.5, color=BLEU, fontweight="bold")
        ax.text(xi, m / 2, f"± {e:.3f}".replace(".", ","),
                ha="center", va="center", fontsize=8.5, color="white")

    ax.set_xticks(list(x))
    ax.set_xticklabels(noms, fontsize=10, color="#1A2330")
    ax.set_ylabel("F1-macro (validation par essai non vu)", fontsize=10.5, color="#1A2330")
    ax.set_ylim(0, 1.06)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0", "0,2", "0,4", "0,6", "0,8", "1,0"], fontsize=9.5, color=GRIS)
    ax.yaxis.grid(True, color=GRILLE, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRILLE)
    ax.spines["bottom"].set_color(GRILLE)

    ax.set_title(
        "Championnat des modèles supervisés — validation Leave-One-Group-Out (8 essais)",
        fontsize=11.5, color=BLEU, fontweight="bold", pad=14, loc="left")

    # Note méthodologique : l'écart-type élevé traduit le faible nombre d'essais.
    fig.text(0.008, -0.02,
             "Barres : moyenne sur les 8 plis ; moustaches : écart-type inter-essais. "
             "Les écarts-types élevés (0,16–0,21) traduisent le faible nombre d'essais disponibles — "
             "c'est cette variabilité, et non le classement brut, qui motive l'augmentation de données.",
             fontsize=8, color=GRIS, ha="left", va="top", wrap=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print(f"OK → {OUT}")
    print("Classement :", ", ".join(f"{n.replace(chr(10),' ')} {m:.3f}" for n, m in zip(noms, moy)))


if __name__ == "__main__":
    main()
