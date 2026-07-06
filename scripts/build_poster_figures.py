"""Genere les figures scientifiques du poster (15 mai 2026).

Lit les artefacts existants dans `reports/` et produit des PNG haute resolution
dans `reports/poster_abstract/figures/generated/`.

Figures produites :
  fig03 — Performance ML (matrices de confusion RF/XGB/SVM, fenetre 60 s)
  fig04 — Top-10 feature importance Random Forest 60 s
  fig05 — Comparaison KPI avant/apres recommandation (C3 -> C5)
  fig06 — Comparaison CV des 3 fenetres (30/60/120 s)

Convention couleurs (handoff §4.5) :
  vert Rondol  #1B7A3D
  bleu Rondol  #005B96
  rouge alerte #C0392B
  gris texte   #333333
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
OUT = REPORTS / "poster_abstract" / "figures" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

GREEN = "#1B7A3D"
BLUE = "#005B96"
RED = "#C0392B"
GREY = "#333333"
LIGHT_GREEN = "#E8F5E9"
LIGHT_GREY = "#F2F4F7"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.edgecolor": GREY,
    "axes.labelcolor": GREY,
    "xtick.color": GREY,
    "ytick.color": GREY,
    "text.color": GREY,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def fig01_pipeline(out: Path) -> None:
    """Pipeline de l'agent IA : formulation -> procede -> vis -> risques -> reco."""
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")

    steps = [
        ("FORMULATION",    "LFP / PVDF / Super P\nLATP / LiTFSI",                BLUE),
        ("PARAMETRES\nPROCEDE", "T zones Z1-Z8\nrpm  /  debit\nL/D 40:1",        BLUE),
        ("PROFIL DE VIS",  "conveying / kneading\ncompression / tip\nKPI : fill, RT, SME", BLUE),
        ("RISQUES",        "score formulation\nclassif. ML stabilite\nalertes par zone", RED),
        ("RECOMMANDATION", "actions hierarchisees\nformulation + vis\n+ procede",         GREEN),
    ]
    n = len(steps)
    box_w, box_h = 16.5, 14
    gap = (100 - n * box_w) / (n + 1)
    y_top = 22

    boxes = []
    for i, (title, body, color) in enumerate(steps):
        x0 = gap + i * (box_w + gap)
        box = FancyBboxPatch((x0, y_top - box_h), box_w, box_h,
                             boxstyle="round,pad=0.4,rounding_size=1.5",
                             linewidth=2, edgecolor=color, facecolor="white")
        ax.add_patch(box)
        ax.text(x0 + box_w/2, y_top - 2.6, title, ha="center", va="top",
                fontsize=12, fontweight="bold", color=color)
        ax.text(x0 + box_w/2, y_top - box_h/2 - 0.5, body, ha="center", va="center",
                fontsize=9.5, color=GREY)
        boxes.append((x0, x0 + box_w))

    for i in range(n - 1):
        x_start = boxes[i][1]; x_end = boxes[i+1][0]
        arrow = FancyArrowPatch((x_start, y_top - box_h/2),
                                (x_end,   y_top - box_h/2),
                                arrowstyle="-|>", mutation_scale=20,
                                color=GREY, linewidth=1.8)
        ax.add_patch(arrow)

    ax.text(50, 27, "Pipeline de l'agent IA — extrusion HME pour batteries Li / SSB",
            ha="center", fontsize=15, fontweight="bold", color=GREY)
    ax.text(50, 3.2,
            "Donnees source : 11 runs industriels (avril 2026, n=2194 points) "
            "| Modeles : RandomForest / XGBoost / SVM, fenetre 60 s | F1-macro 0.917 (RF test)",
            ha="center", fontsize=10, color=GREY, style="italic")
    fig.savefig(out / "fig01_pipeline_overview.png")
    plt.close(fig)


def fig03_ml_performance(metrics_path: Path, out: Path) -> None:
    """3 matrices de confusion cote-a-cote + bandeau metriques."""
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    models = ["RandomForest", "XGBoost", "SVM"]
    titles = ["Random Forest (production)", "XGBoost", "SVM (RBF)"]
    fig = plt.figure(figsize=(15, 7))
    gs = fig.add_gridspec(2, 3, height_ratios=[5, 1], hspace=0.35, wspace=0.25)

    for i, (m, t) in enumerate(zip(models, titles)):
        ax = fig.add_subplot(gs[0, i])
        cm = np.array(data["test"][m]["confusion_matrix"])
        cm_norm = cm / cm.sum(axis=1, keepdims=True)
        cmap = "Greens" if m == "RandomForest" else "Blues"
        im = ax.imshow(cm_norm, cmap=cmap, vmin=0, vmax=1)
        ax.set_title(t, color=GREEN if m == "RandomForest" else GREY)
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["instable", "stable"])
        ax.set_yticklabels(["instable", "stable"])
        ax.set_xlabel("predit"); ax.set_ylabel("reel")
        for (y, x), v in np.ndenumerate(cm):
            color = "white" if cm_norm[y, x] > 0.5 else GREY
            ax.text(x, y, f"{int(v)}\n({cm_norm[y, x]*100:.1f}%)",
                    ha="center", va="center", color=color, fontsize=11, fontweight="bold")
        acc = data["test"][m]["accuracy"]
        f1 = data["test"][m]["f1_macro"]
        auc = data["test"][m]["roc_auc"]
        ax.text(0.5, -0.32,
                f"accuracy {acc:.3f}  |  F1-macro {f1:.3f}  |  ROC-AUC {auc:.3f}",
                transform=ax.transAxes, ha="center", fontsize=10,
                color=GREEN if m == "RandomForest" else GREY,
                fontweight="bold" if m == "RandomForest" else "normal")

    ax_legend = fig.add_subplot(gs[1, :])
    ax_legend.axis("off")
    ax_legend.text(
        0.5, 0.85,
        f"Phase 4 ML — fenetre 60 s — n_train={data['n_train']}  n_test={data['n_test']}  "
        f"({data['n_runs_train']} runs train / {data['n_runs_test']} runs test)  "
        f"— split = {data['split_method']}",
        transform=ax_legend.transAxes, ha="center", fontsize=10, color=GREY,
    )
    ax_legend.text(
        0.5, 0.30,
        "Modele de production retenu : Random Forest "
        "(equilibre performance / interpretabilite / vitesse d'inference)",
        transform=ax_legend.transAxes, ha="center", fontsize=11, color=GREEN, fontweight="bold",
    )
    fig.suptitle("Performance des modeles ML — classification stabilite (test set)",
                 fontsize=15, color=GREY, fontweight="bold", y=0.99)
    fig.savefig(out / "fig03_ml_performance_w60.png")
    plt.close(fig)


def fig04_feature_importance(csv_path: Path, out: Path, top_n: int = 10) -> None:
    """Barplot horizontal top-N feature importance."""
    df = pd.read_csv(csv_path).sort_values("importance", ascending=False).head(top_n)
    df = df.iloc[::-1]
    labels = df["feature"].tolist()
    values = df["importance"].values

    def _family(name: str) -> str:
        if name.startswith("CastFilm"): return "downstream"
        if name.startswith("DIE"):       return "die"
        if name.startswith("Z") or name.startswith("grad_"): return "screw_zone"
        return "other"

    family_color = {"downstream": BLUE, "die": RED, "screw_zone": GREEN, "other": GREY}
    colors = [family_color[_family(n)] for n in labels]

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.8)
    for b, v in zip(bars, values):
        ax.text(v + max(values) * 0.01, b.get_y() + b.get_height()/2,
                f"{v:.3f}", va="center", fontsize=10, color=GREY)
    ax.set_xlabel("Importance (Gini)")
    ax.set_title(f"Top-{top_n} variables — Random Forest (fenetre 60 s)",
                 color=GREY, pad=14)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=LIGHT_GREY)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    handles = [plt.Rectangle((0,0),1,1, color=family_color[k]) for k in ["downstream", "die", "screw_zone"]]
    labels_legend = ["capteurs film (P1/P2/Body)", "DIE (tete d'extrusion)", "zones vis Z1-Z8 + gradients"]
    ax.legend(handles, labels_legend, loc="lower right", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "fig04_feature_importance_RF_w60.png")
    plt.close(fig)


def fig05_before_after(out: Path) -> None:
    """4 KPI groupes : C3 (avant reco) vs C5 (apres reco)."""
    kpis = ["Score\ncompatibilite\n/100", "Probabilite\nstable", "Fill factor Z5", "Couple\ntheorique %"]
    c3 = [46, 0.35, 0.97, 84]
    c5 = [78, 0.87, 0.72, 62]
    norm = [100, 1.0, 1.0, 100]
    c3n = [a / b for a, b in zip(c3, norm)]
    c5n = [a / b for a, b in zip(c5, norm)]

    x = np.arange(len(kpis)); width = 0.35
    fig, ax = plt.subplots(figsize=(13, 7))
    b1 = ax.bar(x - width/2, c3n, width, label="C3 — avant reco (instable)",
                color=RED, edgecolor="white", linewidth=1.2)
    b2 = ax.bar(x + width/2, c5n, width, label="C5 — apres reco (stable)",
                color=GREEN, edgecolor="white", linewidth=1.2)

    for bar, raw, n in zip(b1, c3, norm):
        label = f"{raw:.2f}" if n == 1.0 else f"{int(raw)}"
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, label,
                ha="center", fontsize=11, color=RED, fontweight="bold")
    for bar, raw, n in zip(b2, c5, norm):
        label = f"{raw:.2f}" if n == 1.0 else f"{int(raw)}"
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, label,
                ha="center", fontsize=11, color=GREEN, fontweight="bold")

    for i, (a, b) in enumerate(zip(c3, c5)):
        if i == 0:
            delta = f"+{b - a}"
        elif i in (1,):
            delta = f"+{b - a:.2f}"
        elif i == 2:
            delta = f"{b - a:.2f}"
        else:
            delta = f"{b - a}"
        ax.annotate(
            f"Δ {delta}",
            xy=(i, max(c3n[i], c5n[i]) + 0.10),
            ha="center", fontsize=11, color=BLUE, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc=LIGHT_GREEN, ec=BLUE, lw=1),
        )

    ax.set_xticks(x); ax.set_xticklabels(kpis, fontsize=10)
    ax.set_ylim(0, 1.4)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0.25", "0.50", "0.75", "1.0  (=100 % / score 100)"])
    ax.set_ylabel("Valeur normalisee (1.0 = max)")
    ax.set_title("Effet de la recommandation IA — KPI avant (C3) vs apres (C5)",
                 color=GREY, pad=14)
    ax.legend(loc="upper right", frameon=False, fontsize=11)
    ax.set_axisbelow(True); ax.yaxis.grid(True, color=LIGHT_GREY)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig05_before_after_recommendation.png")
    plt.close(fig)


def fig06_window_comparison(reports_dir: Path, out: Path) -> None:
    """Compare F1-macro CV des 3 fenetres (30/60/120) pour les 3 modeles."""
    windows = [30, 60, 120]
    series = {"RandomForest": [], "XGBoost": [], "SVM": []}
    err = {"RandomForest": [], "XGBoost": [], "SVM": []}
    for w in windows:
        data = json.loads((reports_dir / f"ml_metrics_w{w}.json").read_text(encoding="utf-8"))
        for entry in data["cv"]:
            series[entry["model"]].append(entry["cv_f1_macro_mean"])
            err[entry["model"]].append(entry["cv_f1_macro_std"])

    x = np.arange(len(windows)); width = 0.27
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = {"RandomForest": GREEN, "XGBoost": BLUE, "SVM": GREY}
    for i, (m, vals) in enumerate(series.items()):
        ax.bar(x + (i - 1) * width, vals, width,
               yerr=err[m], capsize=5, color=colors[m], label=m,
               edgecolor="white", linewidth=1.0,
               error_kw={"elinewidth": 1.2, "ecolor": GREY})
        for j, v in enumerate(vals):
            ax.text(x[j] + (i - 1) * width, v + err[m][j] + 0.012, f"{v:.3f}",
                    ha="center", fontsize=9, color=colors[m], fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([f"{w} s" for w in windows])
    ax.set_xlabel("Taille de fenetre temporelle")
    ax.set_ylabel("F1-macro CV (5-fold)")
    ax.set_ylim(0.80, 1.0)
    ax.set_title("Comparaison des fenetres temporelles — F1-macro 5-fold CV",
                 color=GREY, pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.set_axisbelow(True); ax.yaxis.grid(True, color=LIGHT_GREY)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig06_window_comparison.png")
    plt.close(fig)


def main() -> None:
    fig01_pipeline(OUT)
    fig03_ml_performance(REPORTS / "ml_metrics_w60.json", OUT)
    fig04_feature_importance(REPORTS / "feature_importance_RandomForest_w60.csv", OUT)
    fig05_before_after(OUT)
    fig06_window_comparison(REPORTS, OUT)
    print(f"[OK] figures generated in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
