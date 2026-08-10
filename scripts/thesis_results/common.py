# -*- coding: utf-8 -*-
"""
common.py — Socle partagé des trois blocs de résultats demandés par l'encadrant.

Centralise ce qui doit être IDENTIQUE entre les blocs pour que les chiffres
soient comparables :
  - chargement du dataset fenêtré 60 s (essais réels, bad_run exclus) ;
  - liste des 87 features prédictives ;
  - les 5 modèles comparés, tous dotés de predict_proba (ROC-AUC exigé) ;
  - la convention de classe : INSTABLE = classe positive (choix de l'encadrant) ;
  - le calcul de métriques et la mise en forme des figures.

Convention de codage de la cible dans tout le projet :
    is_stable = 1  → fenêtre STABLE
    is_stable = 0  → fenêtre INSTABLE
L'encadrant demande la classe INSTABLE comme classe positive. On ne réencode
donc PAS y : on dérive les compteurs TP/FN/FP/TN avec labels=[1, 0], ce qui
produit directement la matrice attendue (lignes Actual stable→unstable,
colonnes Predicted stable→unstable).

Usage : importé par block1/block2/block3. Pur calcul, aucun état global.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

def _find_root() -> Path:
    """Racine du dépôt = premier parent contenant data/features et src/.

    Cette recherche ascendante rend le module utilisable aussi bien depuis
    scripts/thesis_results/ que depuis les copies autonomes déposées dans
    chaque dossier de bloc du livrable.
    """
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / "data" / "features").is_dir() and (cand / "src").is_dir():
            return cand
    raise RuntimeError(
        "Racine du dépôt introuvable depuis " + str(here) + ". Ce script doit "
        "être exécuté à l'intérieur du dépôt rondol-ia-project (il lit "
        "data/features/ et src/).")


ROOT = _find_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_ROOT = ROOT / "reports" / "AI_thesis_results"
WINDOW_SEC = 60
SEED = 42

# Colonnes méta = tout ce qui n'est pas une feature prédictive.
META_COLS = {
    "run_id", "window_start", "window_end", "n_samples", "stability_score",
    "is_stable", "target_horizon_sec", "run_duration_min", "bad_run",
    "synthetic",
}

MODEL_ORDER = ["LogisticRegression", "SVM_RBF", "RandomForest", "XGBoost",
               "MLP_NeuralNet"]

MODEL_LABELS = {
    "LogisticRegression": "Logistic regression",
    "SVM_RBF": "SVM (RBF)",
    "RandomForest": "Random Forest",
    "XGBoost": "XGBoost",
    "MLP_NeuralNet": "Neural network (MLP)",
}


# ----------------------------------------------------------------------
# DONNÉES
# ----------------------------------------------------------------------
def load_real_windows() -> tuple[pd.DataFrame, list[str]]:
    """Charge les fenêtres RÉELLES 60 s (bad_run exclus), + la liste des features.

    On lit le fichier augmenté car il porte la colonne `synthetic` qui sépare
    proprement réel / généré ; les lignes réelles y sont strictement celles de
    dataset_ml_w60.csv filtrées bad_run == 0.
    """
    path = ROOT / "data" / "features" / f"dataset_ml_w{WINDOW_SEC}_augmented.csv"
    df = pd.read_csv(path)
    feats = [c for c in df.columns if c not in META_COLS]
    real = df[df["synthetic"] == 0].reset_index(drop=True)
    real["window_id"] = [f"W{i:04d}" for i in range(len(real))]
    return real, feats


def load_synthetic_pool() -> pd.DataFrame:
    """Le pool synthétique publié (généré une fois sur TOUS les essais réels).

    Sert à reproduire à l'identique le protocole historique du projet
    (reports/augmentation_eval.json), qui est comparé au protocole corrigé.
    """
    path = ROOT / "data" / "features" / f"dataset_ml_w{WINDOW_SEC}_augmented.csv"
    df = pd.read_csv(path)
    return df[df["synthetic"] == 1].reset_index(drop=True)


# ----------------------------------------------------------------------
# MODÈLES — tous avec predict_proba (ROC-AUC / PR-AUC exigés)
# ----------------------------------------------------------------------
def _scaled(clf) -> Pipeline:
    """Imputation médiane + standardisation, puis le classifieur.

    Les paramètres d'imputation/scaling sont appris DANS le pipeline, donc
    refittés sur le seul fold d'entraînement à chaque appel de fit().
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", clf),
    ])


def _raw(clf) -> Pipeline:
    """Classifieur seul : ni imputation ni standardisation.

    Réservé aux modèles à arbres (Random Forest, XGBoost) : ils gèrent
    nativement les valeurs manquantes et sont invariants aux changements
    d'échelle monotones. C'est la convention de src/ml_utils.py, qui a produit
    reports/robustness_full_w60.json.
    """
    return Pipeline([("clf", clf)])


def make_models(seed: int = SEED, scale_trees: bool = False) -> dict[str, callable]:
    """Fabriques de modèles (lambda → instance neuve à chaque fold).

    Le prétraitement est choisi PAR ALGORITHME, pas uniformément :
      - régression logistique, SVM, MLP → imputation médiane + standardisation
        (obligatoire : ces modèles sont sensibles à l'échelle et n'acceptent
        pas les NaN) ;
      - Random Forest, XGBoost → aucun prétraitement (gestion native des NaN,
        invariance d'échelle).

    `scale_trees=True` force l'imputation + standardisation aussi sur les
    arbres : c'est la configuration utilisée par src/evaluate_augmentation.py.
    Elle n'est activée que par le script de réconciliation, pour reproduire à
    l'identique les chiffres déjà publiés.
    """
    wrap_tree = _scaled if scale_trees else _raw
    return {
        "LogisticRegression": lambda: _scaled(LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=seed)),
        "SVM_RBF": lambda: _scaled(SVC(
            kernel="rbf", gamma="scale", class_weight="balanced",
            probability=True, random_state=seed)),
        "RandomForest": lambda: wrap_tree(RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            n_jobs=-1, random_state=seed)),
        "XGBoost": lambda: wrap_tree(XGBClassifier(
            n_estimators=400, max_depth=5, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
            n_jobs=-1, random_state=seed, tree_method="hist")),
        "MLP_NeuralNet": lambda: _scaled(MLPClassifier(
            hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
            alpha=1e-3, batch_size=32, learning_rate_init=1e-3,
            max_iter=800, early_stopping=True, n_iter_no_change=25,
            validation_fraction=0.15, random_state=seed)),
    }


def fit_predict(make, X_tr, y_tr, X_te):
    """Entraîne un modèle neuf et retourne (y_pred, proba_stable).

    proba_stable = P(is_stable = 1). La probabilité d'instabilité en est le
    complément : proba_unstable = 1 - proba_stable.
    """
    model = make()
    model.fit(X_tr, y_tr)
    proba_stable = model.predict_proba(X_te)[:, 1]
    y_pred = model.predict(X_te)
    return np.asarray(y_pred), np.asarray(proba_stable)


# ----------------------------------------------------------------------
# MÉTRIQUES — classe positive = INSTABLE (is_stable == 0)
# ----------------------------------------------------------------------
def _nan_safe(fn, *a, **kw):
    try:
        v = float(fn(*a, **kw))
        return v if np.isfinite(v) else np.nan
    except (ValueError, ZeroDivisionError):
        return np.nan


def compute_metrics(y_true, y_pred, proba_stable=None) -> dict:
    """Jeu complet de métriques, classe positive = instable.

    La matrice est calculée avec labels=[1, 0] :
        [[TN, FP],
         [FN, TP]]
    soit lignes  = Actual stable, Actual unstable
         colonnes = Predicted stable, Predicted unstable
    ce qui est exactement le tableau demandé par l'encadrant.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[1, 0])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    out = {
        "n_windows": int(len(y_true)),
        "n_stable": int((y_true == 1).sum()),
        "n_unstable": int((y_true == 0).sum()),
        "tp_unstable_detected": tp,
        "fn_unstable_missed": fn,
        "fp_false_alarm": fp,
        "tn_stable_ok": tn,
        "accuracy": _nan_safe(accuracy_score, y_true, y_pred),
        "balanced_accuracy": _nan_safe(balanced_accuracy_score, y_true, y_pred),
        "macro_f1": _nan_safe(f1_score, y_true, y_pred, average="macro"),
        "stable_f1": _nan_safe(f1_score, y_true, y_pred, pos_label=1,
                               zero_division=0),
        "unstable_f1": _nan_safe(f1_score, y_true, y_pred, pos_label=0,
                                 zero_division=0),
        "unstable_precision": _nan_safe(precision_score, y_true, y_pred,
                                        pos_label=0, zero_division=0),
        "unstable_recall": _nan_safe(recall_score, y_true, y_pred,
                                     pos_label=0, zero_division=0),
        # spécificité = rappel de la classe stable ; VPN = précision stable
        "specificity": _nan_safe(recall_score, y_true, y_pred, pos_label=1,
                                 zero_division=0),
        "negative_predictive_value": _nan_safe(precision_score, y_true, y_pred,
                                               pos_label=1, zero_division=0),
    }

    if proba_stable is not None and len(np.unique(y_true)) > 1:
        proba_stable = np.asarray(proba_stable, dtype=float)
        # ROC-AUC est symétrique : identique que la positive soit stable ou instable.
        out["roc_auc"] = _nan_safe(roc_auc_score, y_true, proba_stable)
        # PR-AUC dépend de la classe positive → instable explicitement.
        out["pr_auc_unstable"] = _nan_safe(
            average_precision_score, 1 - y_true, 1.0 - proba_stable)
    else:
        out["roc_auc"] = np.nan
        out["pr_auc_unstable"] = np.nan
    return out


def aggregate(rows: list[dict], keys: list[str]) -> dict:
    """Moyenne / écart-type / min / max sur une liste de dicts de métriques.

    Écart-type de population (ddof=0), cohérent avec np.std utilisé dans
    src/evaluate_augmentation.py — indispensable pour que les chiffres
    republiés coïncident avec ceux déjà cités dans le mémoire.
    """
    out = {}
    for k in keys:
        vals = np.array([r[k] for r in rows if r.get(k) is not None], dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            out[f"{k}_mean"] = out[f"{k}_std"] = np.nan
            out[f"{k}_min"] = out[f"{k}_max"] = np.nan
            continue
        out[f"{k}_mean"] = float(np.mean(vals))
        out[f"{k}_std"] = float(np.std(vals, ddof=0))
        out[f"{k}_min"] = float(np.min(vals))
        out[f"{k}_max"] = float(np.max(vals))
        out[f"{k}_n"] = int(len(vals))
    return out


METRIC_KEYS = ["macro_f1", "stable_f1", "unstable_f1", "unstable_precision",
               "unstable_recall", "accuracy", "balanced_accuracy", "roc_auc"]


# ----------------------------------------------------------------------
# FIGURES — palette sobre, identique entre les blocs
# ----------------------------------------------------------------------
PALETTE = {
    "primary": "#1f4e79",     # bleu profond
    "secondary": "#c55a11",   # orange brûlé
    "neutral": "#7f7f7f",
    "light": "#d6e4f0",
    "grid": "#d9d9d9",
}


def apply_style() -> None:
    """Style matplotlib sobre et homogène (publication mémoire)."""
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "axes.edgecolor": "#404040",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.6,
        "grid.alpha": 0.8,
        "legend.frameon": False,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })


def save_figure(fig, out_dir: Path, stem: str) -> list[Path]:
    """Écrit la figure en PNG (300 dpi) + SVG vectoriel."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "svg"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, format=ext)
        paths.append(p)
    return paths


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    """CSV UTF-8-BOM (ouverture directe sous Excel FR) avec 6 décimales."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.6f")
    return path
