"""
train_mlp_baseline.py — Baseline deep learning (réseau de neurones MLP).

Exigence guide RNCP : « apprentissage supervisé de machine learning ET deep
learning ». Ce script AJOUTE une baseline réseau de neurones (MLPClassifier,
scikit-learn) au comparatif RF / SVM / XGBoost, SANS modifier le pipeline
validé (src/train_models.py) ni écraser reports/ml_metrics_w60.json.

Protocole identique au reste du projet : fenêtre 60 s, split PAR ESSAI
(GroupShuffleSplit 70/30 sur run_id) pour éviter toute fuite par
autocorrélation temporelle, imputation médiane + standardisation (un réseau de
neurones exige des entrées normalisées).

Sortie : reports/ml_metrics_mlp_w60.json

Usage : python -m src.train_mlp_baseline
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config, ml_utils


def make_mlp(random_state: int = 42) -> Pipeline:
    """Perceptron multicouche (2 couches cachées) — baseline deep learning."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-3,                # régularisation L2 (petit dataset)
            batch_size=32,
            learning_rate_init=1e-3,
            max_iter=800,
            early_stopping=True,
            n_iter_no_change=25,
            validation_fraction=0.15,
            random_state=random_state,
        )),
    ])


def main() -> int:
    window = 60
    X, y, _score, df = ml_utils.load_training_dataset(window_sec=window, only_good_runs=True)
    groups = df["run_id"]

    Xtr, Xte, ytr, yte, gtr, gte = ml_utils.group_split(
        X, y, groups, test_size=0.30, random_state=42)

    pipe = make_mlp(random_state=42)
    pipe.fit(Xtr, ytr)
    y_pred = pipe.predict(Xte)
    try:
        y_proba = pipe.predict_proba(Xte)[:, 1]
    except Exception:
        y_proba = None

    metrics = ml_utils.compute_metrics(yte, y_pred, y_proba)

    out = {
        "model": "MLPClassifier (réseau de neurones, baseline deep learning)",
        "window_sec": window,
        "architecture": "hidden_layer_sizes=(64,32), relu, adam, early_stopping",
        "split_method": "GroupShuffleSplit(groups=run_id) 70/30",
        "n_train": int(len(ytr)),
        "n_test": int(len(yte)),
        "n_runs_train": int(gtr.nunique()),
        "n_runs_test": int(gte.nunique()),
        "accuracy": round(float(metrics["accuracy"]), 4),
        "f1_macro": round(float(metrics["f1_macro"]), 4),
        "f1_unstable": round(float(metrics["f1_unstable"]), 4),
        "f1_stable": round(float(metrics["f1_stable"]), 4),
        "roc_auc": (round(float(metrics["roc_auc"]), 4)
                    if metrics.get("roc_auc") is not None
                    and not (isinstance(metrics.get("roc_auc"), float) and np.isnan(metrics["roc_auc"]))
                    else None),
        "confusion_matrix": metrics["confusion_matrix"],
    }
    out_path = config.REPORTS_DIR / "ml_metrics_mlp_w60.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[OK] écrit : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
