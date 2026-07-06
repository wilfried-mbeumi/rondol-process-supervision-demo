"""
ml_utils.py — Utilitaires ML partagés.

Centralise :
- chargement du dataset (avec filtrage bad_run)
- sélection des features prédictives (exclut méta + cibles)
- split train/test stratifié 70/30
- construction des pipelines sklearn (RF, XGBoost, SVM)
- scoring standardisé (accuracy, F1, ROC-AUC)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, roc_auc_score)
from sklearn.model_selection import (GroupShuffleSplit, LeaveOneGroupOut,
                                     train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from xgboost import XGBClassifier

from . import config


# Colonnes qui ne sont PAS des features prédictives
NON_FEATURE_COLS = {
    "run_id", "window_start", "window_end", "n_samples",
    "run_duration_min", "bad_run", "target_horizon_sec",
    "stability_score", "is_stable",
}


def load_training_dataset(window_sec: int = 60,
                          only_good_runs: bool = True) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
    """Charge le dataset, filtre les runs, retourne (X, y_bin, y_score, df_full).

    - window_sec  : 30, 60 ou 120
    - only_good_runs : True → exclusion des bad_run (training principal)
    """
    path = config.DATA_FEATURES / f"dataset_ml_w{window_sec}.csv"
    df = pd.read_csv(path, parse_dates=["window_start", "window_end"])
    if only_good_runs:
        df = df[df["bad_run"] == 0].reset_index(drop=True)

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS
                    and pd.api.types.is_numeric_dtype(df[c])]
    X = df[feature_cols].copy()
    y_bin = df["is_stable"].astype(int).copy()
    y_score = df["stability_score"].astype(float).copy()
    return X, y_bin, y_score, df


def stratified_split(X: pd.DataFrame, y: pd.Series,
                     test_size: float = 0.30,
                     random_state: int = 42):
    """Split stratifié 70/30 — reproductible via random_state."""
    return train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )


def group_split(X: pd.DataFrame, y: pd.Series, groups: pd.Series,
                test_size: float = 0.30,
                random_state: int = 42):
    """Split 70/30 par GROUPE (run_id) — aucun run partagé entre train et test.

    Évite la fuite par autocorrélation temporelle entre fenêtres voisines
    issues du même run.
    """
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size,
                            random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))
    return (X.iloc[train_idx], X.iloc[test_idx],
            y.iloc[train_idx], y.iloc[test_idx],
            groups.iloc[train_idx], groups.iloc[test_idx])


def iter_group_splits(X: pd.DataFrame, y: pd.Series, groups: pd.Series,
                      n_splits: int = 10,
                      test_size: float = 0.30,
                      random_state: int = 42):
    """Itère sur N splits par groupe (seeds différentes) — pour moyenner."""
    gss = GroupShuffleSplit(n_splits=n_splits, test_size=test_size,
                            random_state=random_state)
    return gss.split(X, y, groups=groups)


def iter_leave_one_group_out(X: pd.DataFrame, y: pd.Series, groups: pd.Series):
    """LeaveOneGroupOut : un run par fold, en test."""
    logo = LeaveOneGroupOut()
    return logo.split(X, y, groups=groups)


# ----------------------------------------------------------------------
# PIPELINES
# ----------------------------------------------------------------------
# RF et XGBoost tolèrent NaN et échelles hétérogènes → pas de prétraitement.
# SVM nécessite imputation + scaling.

def make_rf(random_state: int = 42) -> Pipeline:
    """RandomForest avec class_weight équilibré."""
    return Pipeline([
        ("clf", RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=random_state,
        ))
    ])


def make_xgb(random_state: int = 42) -> Pipeline:
    """XGBoost — scale_pos_weight pour compenser le déséquilibre."""
    return Pipeline([
        ("clf", XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            # scale_pos_weight fixé dynamiquement à l'entraînement (voir train_models)
            eval_metric="logloss",
            n_jobs=-1,
            random_state=random_state,
            tree_method="hist",
        ))
    ])


def make_svm(random_state: int = 42) -> Pipeline:
    """SVM (RBF) avec imputation médiane + standardisation + class_weight balanced."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", SVC(
            C=1.0,
            kernel="rbf",
            gamma="scale",
            class_weight="balanced",
            probability=True,
            random_state=random_state,
        )),
    ])


def make_all_models(random_state: int = 42) -> dict[str, Pipeline]:
    return {
        "RandomForest": make_rf(random_state),
        "XGBoost":      make_xgb(random_state),
        "SVM":          make_svm(random_state),
    }


# ----------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------
def compute_metrics(y_true: pd.Series, y_pred: np.ndarray,
                    y_proba: np.ndarray | None = None) -> dict[str, Any]:
    """Accuracy, F1 (binary sur classe 0 = instable + macro), ROC-AUC."""
    out = {
        "accuracy":         accuracy_score(y_true, y_pred),
        "f1_macro":         f1_score(y_true, y_pred, average="macro"),
        "f1_weighted":      f1_score(y_true, y_pred, average="weighted"),
        "f1_unstable":      f1_score(y_true, y_pred, pos_label=0),
        "f1_stable":        f1_score(y_true, y_pred, pos_label=1),
    }
    if y_proba is not None:
        try:
            out["roc_auc"] = roc_auc_score(y_true, y_proba)
        except ValueError:
            out["roc_auc"] = np.nan
    out["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    out["classification_report"] = classification_report(
        y_true, y_pred,
        target_names=["instable", "stable"],
        digits=3,
        zero_division=0,
    )
    return out


def pos_weight_from_y(y: pd.Series) -> float:
    """Rapport (classe 0) / (classe 1) — utilisé par XGBoost scale_pos_weight."""
    n0 = (y == 0).sum()
    n1 = (y == 1).sum()
    return float(n0 / max(n1, 1))
