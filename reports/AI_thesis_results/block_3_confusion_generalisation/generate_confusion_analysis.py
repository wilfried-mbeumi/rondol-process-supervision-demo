# -*- coding: utf-8 -*-
"""
block3_confusion_generalisation.py — BLOC 3 : matrices de confusion et
généralisation du Random Forest retenu.

Deux évaluations, même modèle, même convention (INSTABLE = classe positive) :

  A. Leave-One-Group-Out sur les 8 essais RÉELS
     Prédictions out-of-fold strictes : chaque fenêtre réelle apparaît UNE
     SEULE FOIS, prédite par le modèle pour lequel son essai complet était
     exclu de l'entraînement. Aucune prédiction issue d'un modèle ayant vu le
     même essai n'est incluse. Les prédictions sont reprises telles quelles du
     bloc 2 (condition `fold_aware`), ce qui garantit qu'un seul et même calcul
     alimente les deux blocs.

  B. Dataset continu séparé
     Nature exacte : SIMULÉ. `scripts/generate_consolidated_dataset.py` génère
     une campagne d'acquisition continue de 100 800 lignes au pas de 10 s
     (≈ 11,7 jours), statistiquement calibrée sur les essais réels du
     7-13 avril 2026 : 5 recettes, cycles ambiant → chauffe → plateau régulé
     (bruit AR(1)) → extrusion → refroidissement, valeurs manquantes 1-5 %,
     aberrations thermocouple (code 3276,7) ~0,8 %. Graine fixe (20260417) donc
     reproductible. Ce n'est PAS un jeu expérimental : c'est un test de
     généralisation hors distribution d'entraînement, sur des conditions
     procédé jamais vues.

Sorties (reports/AI_thesis_results/block_3_confusion_generalisation/) :
  - logo_oof_predictions.csv
  - continuous_dataset_predictions.csv
  - confusion_matrices.csv
  - generalisation_summary.csv
  - confusion_matrices.png/.svg
  - roc_pr_curves.png/.svg

Usage : python -m scripts.thesis_results.block3_confusion_generalisation
        (exécuter le bloc 2 au préalable — il produit les prédictions OOF)
"""
from __future__ import annotations

import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

import common

RETAINED_MODEL = "RandomForest"
RETAINED_CONDITION = "fold_aware"
DEPLOYED_MODEL_PATH = common.ROOT / "models" / "RandomForest_w60_augmented.joblib"
CONSOLIDATED_CSV = (common.ROOT / "data" / "consolidated"
                    / "dataset_consolide_rondol.csv")

CONTINUOUS_DATASET_NATURE = {
    "nature": "simulé",
    "n_rows_source": 100800,
    "step_sec": 10,
    "duration_days": 11.7,
    "seed": 20260417,
    "calibration": "statistiquement calibré sur les essais réels du 07-13 avril 2026 "
                   "(data/interim/merged_timeseries.csv)",
    "contenu": "5 recettes, cycles ambiant → chauffe (rampe exponentielle) → "
               "plateau de consigne régulé (bruit AR(1)) → extrusion → "
               "refroidissement ; 12 capteurs de température + RPM vis, débit "
               "doseur, couple",
    "imperfections": "valeurs manquantes 1-5 % par colonne (aléatoires et en "
                     "blocs), aberrations thermocouple code 3276,7 (~0,8 %)",
    "role": "validation externe : le modèle est appliqué tel quel, sans aucun "
            "réentraînement, à des conditions procédé absentes des 8 essais réels",
    "n_est_pas": "un jeu de données expérimental — aucune mesure physique "
                 "supplémentaire n'a été acquise",
}


# ----------------------------------------------------------------------
# A — prédictions out-of-fold Leave-One-Group-Out sur les essais réels
# ----------------------------------------------------------------------
def load_logo_oof() -> pd.DataFrame:
    """Reprend les prédictions OOF du bloc 2 pour le modèle retenu."""
    path = (common.OUT_ROOT / "block_2_model_augmentation"
            / "model_predictions_by_fold.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"{path} absent — exécuter d'abord "
            "python -m scripts.thesis_results.block2_model_augmentation")
    df = pd.read_csv(path)
    oof = df[(df["model"] == RETAINED_MODEL)
             & (df["augmentation"] == RETAINED_CONDITION)].copy()

    # Garantie explicite : une fenêtre réelle = une seule prédiction.
    dup = oof["window_id"].duplicated().sum()
    if dup:
        raise AssertionError(f"{dup} fenêtres dupliquées dans les prédictions OOF")

    real, _ = common.load_real_windows()
    stamps = real.set_index("window_id")["window_start"]
    oof["timestamp"] = oof["window_id"].map(stamps)
    oof = oof.rename(columns={"test_run_id": "run_id"})
    cols = ["run_id", "window_id", "timestamp", "y_true", "y_pred",
            "probability_stable", "probability_unstable", "fold_id"]
    return oof[cols].sort_values(["run_id", "window_id"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# B — dataset continu simulé
# ----------------------------------------------------------------------
def predict_continuous() -> pd.DataFrame:
    """Applique le modèle déployé au dataset continu, sans réentraînement.

    Reproduit exactement le pipeline de scripts/evaluate_on_consolidated.py :
    même fenêtrage 60 s / pas 30 s, mêmes features, même cible de stabilité.
    """
    from src import features, target

    df = pd.read_csv(CONSOLIDATED_CSV, parse_dates=["timestamp"])
    sensors = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
               "DIE", "CastFilmBody", "CastFilmP1", "CastFilmP2"]
    ts = df[["timestamp"] + sensors].copy()
    # Neutralise le code d'erreur thermocouple, comme le preprocess réel.
    for c in sensors:
        ts.loc[ts[c] > 1000, c] = np.nan

    run_change = (df["phase"] != df["phase"].shift()).cumsum()
    ts["run_id"] = np.where(df["phase"] == "run", run_change, 0)
    ts = ts[ts["run_id"] > 0]
    sizes = ts.groupby("run_id").size()
    ts = ts[ts["run_id"].isin(sizes[sizes >= common.WINDOW_SEC // 10 * 3].index)]
    ts = ts.set_index("timestamp")

    feats = features.windowize(ts, window_sec=common.WINDOW_SEC,
                              step_sec=common.WINDOW_SEC // 2)
    df_t = target.add_forecast_target(feats, window_sec=common.WINDOW_SEC,
                                      step_sec=common.WINDOW_SEC // 2)
    df_t = df_t.dropna(subset=["is_stable", "stability_score"]).reset_index(drop=True)
    df_t["is_stable"] = df_t["is_stable"].astype(int)

    model = joblib.load(DEPLOYED_MODEL_PATH)
    drop = [c for c in ("is_stable", "stability_score", "run_id", "t_start",
                        "t_end", "window_start", "window_end", "bad_run")
            if c in df_t.columns]
    X = df_t.drop(columns=drop)
    if hasattr(model, "feature_names_in_"):
        X = X.reindex(columns=list(model.feature_names_in_), fill_value=np.nan)

    proba_stable = model.predict_proba(X)[:, 1]
    y_pred = (proba_stable >= 0.5).astype(int)

    ts_col = next((c for c in ("window_start", "t_start") if c in df_t.columns), None)
    out = pd.DataFrame({
        "run_id": df_t["run_id"] if "run_id" in df_t.columns else -1,
        "window_id": [f"C{i:05d}" for i in range(len(df_t))],
        "timestamp": df_t[ts_col] if ts_col else pd.NaT,
        "y_true": df_t["is_stable"].to_numpy(),
        "y_pred": y_pred,
        "probability_stable": proba_stable,
        "probability_unstable": 1.0 - proba_stable,
    })
    return out


# ----------------------------------------------------------------------
def run() -> dict:
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
    common.apply_style()
    out_dir = common.OUT_ROOT / "block_3_confusion_generalisation"
    out_dir.mkdir(parents=True, exist_ok=True)

    oof = load_logo_oof()
    cont = predict_continuous()

    common.write_csv(oof, out_dir / "logo_oof_predictions.csv")
    common.write_csv(cont, out_dir / "continuous_dataset_predictions.csv")

    evals = {
        "logo_real_runs": ("A — Leave-One-Group-Out, 8 essais réels", oof),
        "continuous_simulated": ("B — Dataset continu simulé (validation externe)", cont),
    }

    cm_rows, sum_rows = [], []
    for key, (label, df) in evals.items():
        m = common.compute_metrics(df["y_true"], df["y_pred"],
                                   df["probability_stable"])
        n = m["n_windows"]
        cm_rows.append({
            "evaluation": key, "label": label,
            "actual_stable_predicted_stable_TN": m["tn_stable_ok"],
            "actual_stable_predicted_unstable_FP": m["fp_false_alarm"],
            "actual_unstable_predicted_stable_FN": m["fn_unstable_missed"],
            "actual_unstable_predicted_unstable_TP": m["tp_unstable_detected"],
            "n_windows": n,
            "n_stable": m["n_stable"], "n_unstable": m["n_unstable"],
        })
        sum_rows.append({
            "evaluation_dataset": label,
            "number_of_windows": n,
            "stable_pct": round(100 * m["n_stable"] / n, 2),
            "unstable_pct": round(100 * m["n_unstable"] / n, 2),
            "macro_f1": m["macro_f1"],
            "stable_f1": m["stable_f1"],
            "unstable_f1": m["unstable_f1"],
            "unstable_precision": m["unstable_precision"],
            "unstable_recall": m["unstable_recall"],
            "specificity": m["specificity"],
            "negative_predictive_value": m["negative_predictive_value"],
            "accuracy": m["accuracy"],
            "balanced_accuracy": m["balanced_accuracy"],
            "roc_auc": m["roc_auc"],
            "pr_auc_unstable": m["pr_auc_unstable"],
            "tp_unstable_detected": m["tp_unstable_detected"],
            "fn_unstable_missed": m["fn_unstable_missed"],
            "fp_false_alarm": m["fp_false_alarm"],
            "tn_stable_ok": m["tn_stable_ok"],
            "dominant_error": ("fausses alertes"
                               if m["fp_false_alarm"] > m["fn_unstable_missed"]
                               else "instabilités non détectées"),
        })

    df_cm = pd.DataFrame(cm_rows)
    df_sum = pd.DataFrame(sum_rows)
    common.write_csv(df_cm, out_dir / "confusion_matrices.csv")
    common.write_csv(df_sum, out_dir / "generalisation_summary.csv")

    _figure_confusion(evals, out_dir)
    _figure_roc_pr(evals, out_dir)
    return {"oof": oof, "continuous": cont, "confusion": df_cm, "summary": df_sum}


def _figure_confusion(evals: dict, out_dir) -> None:
    """Deux panneaux : effectifs absolus + % normalisés par classe RÉELLE."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list(
        "rondol", ["#ffffff", common.PALETTE["light"], common.PALETTE["primary"]])
    classes = ["Stable", "Unstable"]

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    for ax, (key, (label, df)) in zip(axes, evals.items()):
        m = common.compute_metrics(df["y_true"], df["y_pred"],
                                   df["probability_stable"])
        # Ordre imposé : Stable puis Unstable, en ligne comme en colonne.
        cm = np.array([[m["tn_stable_ok"], m["fp_false_alarm"]],
                       [m["fn_unstable_missed"], m["tp_unstable_detected"]]])
        row_tot = cm.sum(axis=1, keepdims=True)
        pct = np.divide(cm, row_tot, where=row_tot != 0) * 100

        ax.imshow(pct, cmap=cmap, vmin=0, vmax=100)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i, j]:,}".replace(",", " ") +
                        f"\n({pct[i, j]:.1f} %)",
                        ha="center", va="center", fontsize=11,
                        fontweight="bold" if i == j else "normal",
                        color="white" if pct[i, j] > 55 else "#1a1a1a")
        ax.set_xticks([0, 1], classes)
        ax.set_yticks([0, 1], classes)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("Actual class")
        ax.set_title(f"{label}\nn = {m['n_windows']:,}".replace(",", " ")
                     + f" fenêtres · macro-F1 = {m['macro_f1']:.3f}",
                     loc="left", fontsize=9)
        ax.grid(False)
        ax.set_xticks(np.arange(-.5, 2, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
        ax.grid(which="minor", color="#404040", linewidth=0.8)
        ax.tick_params(which="minor", length=0)

    fig.suptitle("Matrices de confusion — Random Forest retenu · "
                 "classe positive = Unstable · pourcentages normalisés par classe réelle",
                 fontsize=10, fontweight="bold", y=1.03)
    fig.tight_layout()
    common.save_figure(fig, out_dir, "confusion_matrices")
    plt.close(fig)


def _figure_roc_pr(evals: dict, out_dir) -> None:
    """Courbes ROC et précision-rappel pour les deux évaluations."""
    import matplotlib.pyplot as plt

    colors = [common.PALETTE["primary"], common.PALETTE["secondary"]]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4))

    for (key, (label, df)), col in zip(evals.items(), colors):
        y_unstable = 1 - df["y_true"].to_numpy()
        p_unstable = df["probability_unstable"].to_numpy()
        m = common.compute_metrics(df["y_true"], df["y_pred"],
                                   df["probability_stable"])
        short = label.split(" — ")[1] if " — " in label else label

        fpr, tpr, _ = roc_curve(y_unstable, p_unstable)
        axes[0].plot(fpr, tpr, color=col, lw=1.8,
                     label=f"{short}\nROC-AUC = {m['roc_auc']:.3f}")

        prec, rec, _ = precision_recall_curve(y_unstable, p_unstable)
        axes[1].plot(rec, prec, color=col, lw=1.8,
                     label=f"{short}\nPR-AUC = {m['pr_auc_unstable']:.3f}")
        # Ligne de base d'un classifieur aléatoire = prévalence de l'instable.
        axes[1].axhline(y_unstable.mean(), color=col, lw=0.8, ls=":", alpha=0.7)

    axes[0].plot([0, 1], [0, 1], color=common.PALETTE["neutral"], lw=0.8, ls="--")
    axes[0].set_xlabel("Taux de faux positifs (fausses alertes)")
    axes[0].set_ylabel("Taux de vrais positifs (rappel instable)")
    axes[0].set_title("A — Courbe ROC", loc="left")
    axes[1].set_xlabel("Rappel — classe instable")
    axes[1].set_ylabel("Précision — classe instable")
    axes[1].set_title("B — Courbe précision-rappel", loc="left")
    for ax in axes:
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.legend(fontsize=7.5, loc="lower left" if ax is axes[0] else "lower right")
        ax.set_axisbelow(True)

    fig.suptitle("Courbes ROC et précision-rappel — classe positive = Unstable",
                 fontsize=10, fontweight="bold", y=1.02)
    fig.text(0.5, -0.04,
             "Pointillés : prévalence de la classe instable, soit la précision d'un classifieur aléatoire.",
             ha="center", fontsize=7.5, color="#404040")
    fig.tight_layout()
    common.save_figure(fig, out_dir, "roc_pr_curves")
    plt.close(fig)


if __name__ == "__main__":
    res = run()
    print(res["summary"].to_string(index=False))
