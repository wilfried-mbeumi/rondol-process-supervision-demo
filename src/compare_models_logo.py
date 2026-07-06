"""
compare_models_logo.py — Comparaison HONNÊTE des modèles en validation par essai.

Objectif : choisir le modèle le plus DÉFENDABLE (pas le meilleur en accuracy
artificielle de split aléatoire). Validation LeaveOneGroupOut (un essai entier en
test à chaque pli) = pas de fuite par autocorrélation temporelle intra-essai.

Modèles comparés (tous avec imputation médiane + standardisation) :
  LogisticRegression, RandomForest, SVM (RBF), XGBoost, MLP (réseau de neurones).

Sorties :
  - F1-macro par essai (moyenne ± écart-type, min/max) ;
  - métriques globales en prédictions hors-pli (pooled) : accuracy, precision,
    recall, F1 sur la classe « instable », matrice de confusion ;
  - écrit reports/model_comparison_logo_w60.json.

Usage : python -m src.compare_models_logo
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from xgboost import XGBClassifier

from . import config, ml_utils

RANDOM_STATE = 42


def _pipe(clf):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", clf),
    ])


def _models():
    return {
        "LogisticRegression": _pipe(LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE)),
        "RandomForest": _pipe(RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            n_jobs=-1, random_state=RANDOM_STATE)),
        "SVM_RBF": _pipe(SVC(
            C=1.0, kernel="rbf", gamma="scale", class_weight="balanced",
            probability=False, random_state=RANDOM_STATE)),
        "XGBoost": _pipe(XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, eval_metric="logloss", n_jobs=-1,
            random_state=RANDOM_STATE, tree_method="hist")),
        "MLP": _pipe(MLPClassifier(
            hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
            alpha=1e-3, max_iter=800, early_stopping=True, n_iter_no_change=25,
            random_state=RANDOM_STATE)),
    }


def main() -> int:
    window = 60
    X, y, _score, df = ml_utils.load_training_dataset(window_sec=window, only_good_runs=True)
    groups = df["run_id"].to_numpy()
    logo = LeaveOneGroupOut()
    n_runs = len(np.unique(groups))
    print(f"Dataset w{window} : {len(y)} fenêtres · {n_runs} essais · "
          f"classe instable={int((y == 0).sum())} / stable={int((y == 1).sum())}")
    print(f"Validation : LeaveOneGroupOut ({n_runs} plis, un essai en test par pli)\n")

    results = {}
    for name, model in _models().items():
        per_fold_f1 = []
        y_true_all, y_pred_all = [], []
        for tr, te in logo.split(X, y, groups):
            model.fit(X.iloc[tr], y.iloc[tr])
            pred = model.predict(X.iloc[te])
            yt = y.iloc[te].to_numpy()
            # F1-macro défini seulement si le pli contient les 2 classes
            if len(np.unique(yt)) > 1:
                per_fold_f1.append(f1_score(yt, pred, average="macro"))
            y_true_all.extend(yt.tolist())
            y_pred_all.extend(pred.tolist())

        yt = np.array(y_true_all); yp = np.array(y_pred_all)
        cm = confusion_matrix(yt, yp, labels=[0, 1]).tolist()
        results[name] = {
            "logo_f1_macro_mean": round(float(np.mean(per_fold_f1)), 3),
            "logo_f1_macro_std": round(float(np.std(per_fold_f1)), 3),
            "logo_f1_macro_min": round(float(np.min(per_fold_f1)), 3),
            "logo_f1_macro_max": round(float(np.max(per_fold_f1)), 3),
            "pooled_accuracy": round(float(accuracy_score(yt, yp)), 3),
            "pooled_unstable_precision": round(float(precision_score(yt, yp, pos_label=0, zero_division=0)), 3),
            "pooled_unstable_recall": round(float(recall_score(yt, yp, pos_label=0, zero_division=0)), 3),
            "pooled_unstable_f1": round(float(f1_score(yt, yp, pos_label=0, zero_division=0)), 3),
            "pooled_confusion_matrix": cm,
        }
        r = results[name]
        print(f"{name:18} F1-macro(LOGO)={r['logo_f1_macro_mean']:.3f}±{r['logo_f1_macro_std']:.3f} "
              f"[{r['logo_f1_macro_min']:.2f}–{r['logo_f1_macro_max']:.2f}] | "
              f"instable: P={r['pooled_unstable_precision']:.2f} R={r['pooled_unstable_recall']:.2f} "
              f"F1={r['pooled_unstable_f1']:.2f} | acc={r['pooled_accuracy']:.2f}")

    best = max(results, key=lambda k: results[k]["logo_f1_macro_mean"])
    out = {"window_sec": window, "validation": "LeaveOneGroupOut", "n_runs": int(n_runs),
           "models": results, "best_logo_f1_macro": best}
    (config.REPORTS_DIR / "model_comparison_logo_w60.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMeilleur F1-macro LOGO : {best}")
    print(f"[OK] écrit reports/model_comparison_logo_w60.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
