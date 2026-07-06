"""
threshold_calibration.py — Analyse de sensibilité du seuil STABILITY_SCORE_THRESHOLD.

Pour chaque seuil candidat, on :
  1. Redéfinit la cible binaire (is_stable = stability_score >= threshold)
  2. Mesure l'équilibre de classes résultant
  3. Évalue en CV GroupKFold (par run_id) un RandomForest par défaut
     → F1 macro, F1 unstable, precision/recall unstable, ROC-AUC
     → cohérent avec le split train/test principal (GroupShuffleSplit par run_id)
     → aucune fenêtre d'un même run ne contamine plusieurs folds

Le test set final n'est PAS utilisé pour la calibration (anti-contamination).

Deux recommandations de seuil sont produites :
  A) Seuil optimal par F1 unstable (priorité à la détection d'instabilité)
  B) Seuil optimal par équilibre précision/recall (|P - R| minimal)

Usage :
  python -m src.threshold_calibration
  python -m src.threshold_calibration --window 60 --thresholds 50,55,60,65,70,75,80
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import GroupKFold, cross_validate
from sklearn.pipeline import Pipeline as SkPipeline

from . import config, ml_utils

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# Scorers orientés sur la classe unstable (pos_label=0)
_SCORING = {
    "f1_macro":           "f1_macro",
    "f1_unstable":        make_scorer(f1_score,        pos_label=0, zero_division=0),
    "precision_unstable": make_scorer(precision_score, pos_label=0, zero_division=0),
    "recall_unstable":    make_scorer(recall_score,    pos_label=0, zero_division=0),
    "roc_auc":            "roc_auc",
}


def run_calibration(X_train: pd.DataFrame,
                    y_score_train: pd.Series,
                    groups_train: pd.Series,
                    thresholds: list[float],
                    random_state: int = 42) -> pd.DataFrame:
    """Parcourt les seuils et renvoie un tableau de métriques CV (GroupKFold).

    La CV interne utilise GroupKFold(groups=run_id) pour rester cohérente
    avec le split train/test principal (GroupShuffleSplit). Ainsi :
    aucune fenêtre d'un run donné n'apparaît à la fois dans le fold train
    et dans le fold validation → estimation honnête de la généralisation.
    """
    base_pipe = ml_utils.make_rf(random_state=random_state)
    # Ajout imputer pour compatibilité NaN (RF sklearn 1.7 refuse les NaN)
    base_pipe = SkPipeline([("imputer", SimpleImputer(strategy="median"))]
                           + list(base_pipe.steps))

    n_groups = groups_train.nunique()
    n_splits = min(5, n_groups)
    cv = GroupKFold(n_splits=n_splits)

    rows = []
    for t in thresholds:
        y = (y_score_train >= t).astype(int)
        n1 = int((y == 1).sum())
        n0 = int((y == 0).sum())
        pct = float(y.mean())
        # Cas dégénéré : classe trop rare pour un GroupKFold équilibré
        if n0 < n_splits or n1 < n_splits:
            rows.append({
                "threshold": t, "pct_stable": round(100 * pct, 1),
                "n_stable": n1, "n_unstable": n0,
                "cv_f1_macro_mean": np.nan, "cv_f1_macro_std": np.nan,
                "cv_f1_unstable_mean": np.nan, "cv_f1_unstable_std": np.nan,
                "cv_precision_unstable_mean": np.nan,
                "cv_recall_unstable_mean": np.nan,
                "cv_pr_abs_diff": np.nan,
                "cv_roc_auc_mean":  np.nan, "cv_roc_auc_std":  np.nan,
                "note": "classe trop rare",
            })
            continue

        p = clone(base_pipe)
        cvr = cross_validate(p, X_train, y, cv=cv, scoring=_SCORING,
                             groups=groups_train, n_jobs=-1,
                             error_score=np.nan)
        p_mean = float(np.nanmean(cvr["test_precision_unstable"]))
        r_mean = float(np.nanmean(cvr["test_recall_unstable"]))
        rows.append({
            "threshold": t,
            "pct_stable": round(100 * pct, 1),
            "n_stable": n1,
            "n_unstable": n0,
            "cv_f1_macro_mean":            round(float(np.nanmean(cvr["test_f1_macro"])), 4),
            "cv_f1_macro_std":             round(float(np.nanstd(cvr["test_f1_macro"])), 4),
            "cv_f1_unstable_mean":         round(float(np.nanmean(cvr["test_f1_unstable"])), 4),
            "cv_f1_unstable_std":          round(float(np.nanstd(cvr["test_f1_unstable"])), 4),
            "cv_precision_unstable_mean":  round(p_mean, 4),
            "cv_recall_unstable_mean":     round(r_mean, 4),
            "cv_pr_abs_diff":              round(abs(p_mean - r_mean), 4),
            "cv_roc_auc_mean":             round(float(np.nanmean(cvr["test_roc_auc"])), 4),
            "cv_roc_auc_std":              round(float(np.nanstd(cvr["test_roc_auc"])), 4),
            "note": "",
        })
    return pd.DataFrame(rows)


def _row_to_rec(row: pd.Series) -> dict:
    """Extrait les champs utiles d'une ligne de recommandation."""
    return {
        "threshold":            float(row["threshold"]),
        "pct_stable":           float(row["pct_stable"]),
        "n_stable":             int(row["n_stable"]),
        "n_unstable":           int(row["n_unstable"]),
        "cv_f1_macro_mean":     float(row["cv_f1_macro_mean"]),
        "cv_f1_unstable_mean":  float(row["cv_f1_unstable_mean"]),
        "cv_precision_unstable_mean": float(row["cv_precision_unstable_mean"]),
        "cv_recall_unstable_mean":    float(row["cv_recall_unstable_mean"]),
        "cv_pr_abs_diff":       float(row["cv_pr_abs_diff"]),
        "cv_roc_auc_mean":      float(row["cv_roc_auc_mean"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--thresholds", type=str,
                    default="50,55,60,65,70,75,80,85")
    ap.add_argument("--random-state", type=int, default=42)
    args = ap.parse_args()

    thresholds = [float(t.strip()) for t in args.thresholds.split(",")]

    print("=" * 78)
    print(f"CALIBRATION DU SEUIL — fenêtre = {args.window}s (GroupKFold par run_id)")
    print("=" * 78)

    # Chargement + split identique au train pour ne PAS fuiter le test set
    # (GroupShuffleSplit par run_id avec même random_state → même partition)
    X, y_bin, y_score, df_full = ml_utils.load_training_dataset(
        window_sec=args.window, only_good_runs=True
    )
    groups = df_full["run_id"].astype(int)
    X_train, X_test, y_train, y_test, g_train, g_test = ml_utils.group_split(
        X, y_bin, groups, test_size=0.30, random_state=args.random_state
    )
    # On récupère le même score continu ALIGNÉ sur X_train par index
    y_score_train = y_score.loc[X_train.index]

    print(f"Training set pour la calibration : {len(X_train)} lignes, "
          f"{g_train.nunique()} runs {sorted(g_train.unique().tolist())}")
    print(f"Seuils testés : {thresholds}\n")

    df = run_calibration(X_train, y_score_train, g_train, thresholds,
                         random_state=args.random_state)
    print(df.to_string(index=False))

    out_csv = config.REPORTS_DIR / f"threshold_calibration_w{args.window}.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n→ {out_csv}")

    # Recommandations : deux critères distincts
    valid = df.dropna(subset=["cv_f1_unstable_mean"])
    recommendations = {}
    if not valid.empty:
        best_f1u = valid.sort_values("cv_f1_unstable_mean", ascending=False).iloc[0]
        # P/R balance : on exclut les cas dégénérés (P≈0 ET R≈0 — le classifieur
        # prédit "tout stable", P/R triviaux à 0 qui se "balancent" artificiellement).
        # Seuil minimum : P>=0.3 ET R>=0.3 pour qualifier un point d'équilibre réel.
        nondeg = valid[(valid["cv_precision_unstable_mean"] >= 0.3)
                       & (valid["cv_recall_unstable_mean"]    >= 0.3)]
        if not nondeg.empty:
            best_pr = nondeg.sort_values("cv_pr_abs_diff", ascending=True).iloc[0]
        else:
            # Fallback : si aucun seuil n'atteint P/R >= 0.3, on prend le moins
            # mauvais (avec un avertissement dans le champ "note" de la reco).
            best_pr = valid.sort_values("cv_pr_abs_diff", ascending=True).iloc[0]
        recommendations = {
            "by_f1_unstable":        _row_to_rec(best_f1u),
            "by_precision_recall_balance": _row_to_rec(best_pr),
        }
        if nondeg.empty:
            recommendations["by_precision_recall_balance"]["warning"] = (
                "aucun seuil n'atteint P>=0.3 et R>=0.3 — recommandation peu fiable"
            )

        print("\n" + "-" * 78)
        print("RECOMMANDATIONS")
        print("-" * 78)
        print(f"A) Meilleur seuil par F1 unstable        : "
              f"{best_f1u['threshold']:.0f}  "
              f"(F1u={best_f1u['cv_f1_unstable_mean']:.3f}, "
              f"P={best_f1u['cv_precision_unstable_mean']:.3f}, "
              f"R={best_f1u['cv_recall_unstable_mean']:.3f}, "
              f"{best_f1u['pct_stable']:.1f}% stables)")
        print(f"B) Meilleur seuil par P/R balance        : "
              f"{best_pr['threshold']:.0f}  "
              f"(|P-R|={best_pr['cv_pr_abs_diff']:.3f}, "
              f"P={best_pr['cv_precision_unstable_mean']:.3f}, "
              f"R={best_pr['cv_recall_unstable_mean']:.3f}, "
              f"F1u={best_pr['cv_f1_unstable_mean']:.3f}, "
              f"{best_pr['pct_stable']:.1f}% stables)")
        # Ligne business : seuil 70 (référence métier)
        biz = valid[valid["threshold"] == 70.0]
        if not biz.empty:
            b = biz.iloc[0]
            print(f"   (Référence métier seuil 70        : "
                  f"F1u={b['cv_f1_unstable_mean']:.3f}, "
                  f"P={b['cv_precision_unstable_mean']:.3f}, "
                  f"R={b['cv_recall_unstable_mean']:.3f}, "
                  f"{b['pct_stable']:.1f}% stables)")

    # Sauvegarde JSON avec recommandations
    out_json = config.REPORTS_DIR / f"threshold_calibration_w{args.window}.json"
    out_json.write_text(json.dumps({
        "window_sec":       args.window,
        "cv_protocol":      f"GroupKFold(n_splits={min(5, g_train.nunique())}, groups=run_id)",
        "train_size":       int(len(X_train)),
        "train_runs":       sorted(g_train.unique().tolist()),
        "thresholds_tested": thresholds,
        "sweep":            df.to_dict(orient="records"),
        "recommendations":  recommendations,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"→ {out_json}")


if __name__ == "__main__":
    main()
