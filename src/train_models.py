"""
train_models.py — Phase 4 : entraînement et comparaison de 3 modèles ML.

Pipeline :
  1. chargement du dataset (w=60 par défaut, bad_run exclus)
  2. split 70 / 30 par groupe (run_id) via GroupShuffleSplit
     → aucun run partagé entre train et test (évite la fuite par
       autocorrélation temporelle entre fenêtres voisines d'un même run)
  3. cross-validation 5-fold sur le training set (comparaison robuste)
  4. entraînement final sur le training set complet
  5. évaluation sur le test set (accuracy, F1, ROC-AUC, matrice de confusion)
  6. sélection du meilleur modèle (F1 macro sur test)
  7. sauvegarde du meilleur modèle (joblib) + rapports

Usage :
  python -m src.train_models                 # défaut : w=60
  python -m src.train_models --window 30
  python -m src.train_models --window 120
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_score

from . import config, ml_utils

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


MODELS_DIR = config.PROJECT_ROOT / "models"
REPORTS_DIR = config.REPORTS_DIR


def cross_validate_models(X_train, y_train, random_state: int = 42) -> pd.DataFrame:
    """CV 5-fold stratifiée sur le training set — retourne un DataFrame de scores."""
    models = ml_utils.make_all_models(random_state=random_state)
    spw = ml_utils.pos_weight_from_y(y_train)

    # Pour XGBoost on doit gérer les NaN car le pipeline sklearn CV le testera tel quel.
    # Or on choisit de laisser NaN pour RF/XGBoost : RF 1.7+ refuse les NaN par défaut.
    # Solution : on impute le NaN pour la CV uniquement sur RF/XGBoost (impute=mediane),
    # afin que tous les modèles soient comparables sur les mêmes folds.
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline as SkPipeline

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)

    rows = []
    for name, pipe in models.items():
        # On clone et on configure
        p = clone(pipe)
        if name == "XGBoost":
            p.named_steps["clf"].set_params(scale_pos_weight=spw)

        # Ajout d'un imputer en tête si le pipeline n'en a pas (RF/XGB)
        if "imputer" not in p.named_steps:
            p = SkPipeline([("imputer", SimpleImputer(strategy="median"))]
                          + list(p.steps))

        f1_scores = cross_val_score(p, X_train, y_train, cv=cv,
                                    scoring="f1_macro", n_jobs=-1)
        acc_scores = cross_val_score(p, X_train, y_train, cv=cv,
                                     scoring="accuracy", n_jobs=-1)
        auc_scores = cross_val_score(p, X_train, y_train, cv=cv,
                                     scoring="roc_auc", n_jobs=-1)
        rows.append({
            "model": name,
            "cv_f1_macro_mean": round(f1_scores.mean(), 4),
            "cv_f1_macro_std":  round(f1_scores.std(), 4),
            "cv_accuracy_mean": round(acc_scores.mean(), 4),
            "cv_accuracy_std":  round(acc_scores.std(), 4),
            "cv_roc_auc_mean":  round(auc_scores.mean(), 4),
            "cv_roc_auc_std":   round(auc_scores.std(), 4),
        })
    return pd.DataFrame(rows)


def train_and_evaluate(X_train, y_train, X_test, y_test,
                       random_state: int = 42) -> dict:
    """Entraîne chaque modèle sur train, évalue sur test. Retourne dict complet."""
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline as SkPipeline

    models = ml_utils.make_all_models(random_state=random_state)
    spw = ml_utils.pos_weight_from_y(y_train)

    results = {}
    for name, pipe in models.items():
        t0 = time.time()
        p = clone(pipe)
        if name == "XGBoost":
            p.named_steps["clf"].set_params(scale_pos_weight=spw)
        if "imputer" not in p.named_steps:
            p = SkPipeline([("imputer", SimpleImputer(strategy="median"))]
                          + list(p.steps))

        p.fit(X_train, y_train)
        y_pred = p.predict(X_test)
        y_proba = p.predict_proba(X_test)[:, 1] if hasattr(p, "predict_proba") else None

        metrics = ml_utils.compute_metrics(y_test, y_pred, y_proba)
        results[name] = {
            "pipeline": p,
            "metrics": metrics,
            "fit_time_s": round(time.time() - t0, 2),
        }
        print(f"  {name:12s}  "
              f"acc={metrics['accuracy']:.3f}  "
              f"f1_macro={metrics['f1_macro']:.3f}  "
              f"f1_unstable={metrics['f1_unstable']:.3f}  "
              f"roc_auc={metrics.get('roc_auc', float('nan')):.3f}  "
              f"({results[name]['fit_time_s']}s)")
    return results


def feature_importance_table(pipeline, X: pd.DataFrame) -> pd.DataFrame | None:
    """Importance des features pour RF / XGBoost. None sinon."""
    clf = pipeline.named_steps.get("clf")
    if not hasattr(clf, "feature_importances_"):
        return None
    imp = clf.feature_importances_
    s = pd.Series(imp, index=X.columns).sort_values(ascending=False)
    return s.reset_index().rename(columns={"index": "feature", 0: "importance"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--random-state", type=int, default=42)
    args = ap.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"PHASE 4 — ENTRAÎNEMENT ML   (fenêtre = {args.window}s)")
    print("=" * 70)

    # 1) Chargement
    X, y_bin, y_score, df_full = ml_utils.load_training_dataset(
        window_sec=args.window, only_good_runs=True
    )
    groups = df_full["run_id"].astype(int)
    print(f"Dataset : {X.shape[0]} fenêtres × {X.shape[1]} features")
    print(f"Runs    : {groups.nunique()} runs distincts")
    print(f"Classes : stable={(y_bin==1).sum()}, instable={(y_bin==0).sum()} "
          f"({100*y_bin.mean():.1f}% stables)")

    # 2) Split 70/30 par GROUPE (run_id) — GroupShuffleSplit
    #    Garantit qu'aucun run n'est partagé entre train et test
    #    → évite la fuite par autocorrélation intra-run entre fenêtres voisines
    X_train, X_test, y_train, y_test, g_train, g_test = ml_utils.group_split(
        X, y_bin, groups, test_size=0.30, random_state=args.random_state
    )
    print(f"Split   : train={len(X_train)} ({g_train.nunique()} runs), "
          f"test={len(X_test)} ({g_test.nunique()} runs) "
          f"(train stable={100*y_train.mean():.1f}%, "
          f"test stable={100*y_test.mean():.1f}%)")

    # 3) Cross-validation 5-fold sur train
    print("\n[CV 5-fold sur training set]")
    cv_df = cross_validate_models(X_train, y_train, random_state=args.random_state)
    print(cv_df.to_string(index=False))

    # 4) Entraînement final + évaluation test
    print("\n[Évaluation sur test set 30 %]")
    results = train_and_evaluate(X_train, y_train, X_test, y_test,
                                 random_state=args.random_state)

    # 5) Matrice de confusion et classification report pour chaque modèle
    print("\n[Détail par modèle]")
    summary_lines = []
    for name, res in results.items():
        cm = res["metrics"]["confusion_matrix"]
        print(f"\n— {name} —")
        print("Confusion matrix (rows=truth, cols=pred) : [instable, stable]")
        print(f"    instable → [{cm[0][0]:4d}, {cm[0][1]:4d}]")
        print(f"    stable   → [{cm[1][0]:4d}, {cm[1][1]:4d}]")
        print(res["metrics"]["classification_report"])
        summary_lines.append(f"--- {name} ---")
        summary_lines.append(f"CM: {cm}")
        summary_lines.append(res["metrics"]["classification_report"])

    # 6) Sélection du meilleur modèle (F1 macro test)
    best_name = max(results.keys(),
                    key=lambda n: results[n]["metrics"]["f1_macro"])
    print(f"\n→ Meilleur modèle : {best_name} "
          f"(f1_macro = {results[best_name]['metrics']['f1_macro']:.3f})")

    # 7) Sauvegarde
    suffix = f"w{args.window}"
    for name, res in results.items():
        joblib.dump(res["pipeline"], MODELS_DIR / f"{name}_{suffix}.joblib")
    joblib.dump(results[best_name]["pipeline"], MODELS_DIR / f"best_{suffix}.joblib")

    # Feature importance (RF + XGBoost si présents)
    fi_all = {}
    for name in ("RandomForest", "XGBoost"):
        if name in results:
            fi = feature_importance_table(results[name]["pipeline"], X_train)
            if fi is not None:
                fi.columns = ["feature", "importance"]
                fi_all[name] = fi
                fi.to_csv(REPORTS_DIR / f"feature_importance_{name}_{suffix}.csv",
                          index=False)

    # Rapport JSON
    metrics_out = {
        "window_sec": args.window,
        "split_method": "GroupShuffleSplit(groups=run_id)",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_runs_train": int(g_train.nunique()),
        "n_runs_test": int(g_test.nunique()),
        "class_balance_train_pct_stable": round(100 * y_train.mean(), 2),
        "class_balance_test_pct_stable": round(100 * y_test.mean(), 2),
        "cv": cv_df.to_dict(orient="records"),
        "test": {
            name: {k: v for k, v in res["metrics"].items()
                   if k != "classification_report"}
            for name, res in results.items()
        },
        "best_model": best_name,
    }
    (REPORTS_DIR / f"ml_metrics_{suffix}.json").write_text(
        json.dumps(metrics_out, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # Rapport texte lisible
    txt_path = REPORTS_DIR / f"ml_summary_{suffix}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Phase 4 — ML — Window {args.window}s\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Dataset : {X.shape}\n")
        f.write(f"Split method : GroupShuffleSplit(groups=run_id)\n")
        f.write(f"Train / Test : {len(X_train)} / {len(X_test)} fenêtres "
                f"— {g_train.nunique()} / {g_test.nunique()} runs\n")
        f.write(f"Classes train : {y_train.value_counts().to_dict()}\n")
        f.write(f"Classes test  : {y_test.value_counts().to_dict()}\n\n")
        f.write("CV 5-fold sur training set :\n")
        f.write(cv_df.to_string(index=False) + "\n\n")
        f.write("Évaluation sur test set :\n\n")
        f.write("\n".join(summary_lines) + "\n\n")
        f.write(f"Meilleur modèle : {best_name}\n")

    print(f"\nModèles sauvés :      {MODELS_DIR}")
    print(f"Best model :          models/best_{suffix}.joblib")
    print(f"Rapport texte :       {txt_path}")
    print(f"Rapport JSON :        reports/ml_metrics_{suffix}.json")


if __name__ == "__main__":
    main()
