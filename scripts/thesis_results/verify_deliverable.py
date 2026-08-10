# -*- coding: utf-8 -*-
"""
verify_deliverable.py — Contrôle d'acceptation du livrable.

Reprend point par point la demande de l'encadrant et vérifie que le contenu
produit y répond. Sort en code 1 si un contrôle échoue.

Usage : python -m scripts.thesis_results.verify_deliverable
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import common

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, bool(ok), detail))


def _cols(df: pd.DataFrame, required: list[str]) -> tuple[bool, str]:
    missing = [c for c in required if c not in df.columns]
    return (not missing), ("toutes présentes" if not missing
                           else f"MANQUANT : {missing}")


def run() -> int:
    b1_dir = common.OUT_ROOT / "block_1_validation_strategy"
    b2_dir = common.OUT_ROOT / "block_2_model_augmentation"
    b3_dir = common.OUT_ROOT / "block_3_confusion_generalisation"

    # ---------------- BLOC 1 -------------------------------------------
    f1 = pd.read_csv(b1_dir / "validation_metrics_by_fold.csv")
    s1 = pd.read_csv(b1_dir / "validation_summary.csv")
    p1 = pd.read_csv(b1_dir / "validation_predictions.csv")

    check("B1 · les 3 stratégies sont présentes",
          set(f1["validation_strategy"]) == {"random_split", "group_shuffle", "logo"},
          str(sorted(set(f1["validation_strategy"]))))
    ok, d = _cols(f1, ["fold_id", "test_run_id", "n_train_windows",
                       "n_test_windows", "n_train_runs", "n_test_runs",
                       "macro_f1", "stable_f1", "unstable_f1",
                       "unstable_precision", "unstable_recall", "accuracy",
                       "balanced_accuracy", "roc_auc"])
    check("B1 · métriques par fold demandées", ok, d)
    check("B1 · agrégats moyenne/écart-type/min/max",
          all(f"macro_f1_{s}" in s1.columns for s in ("mean", "std", "min", "max")),
          "mean/std/min/max présents")
    ok, d = _cols(p1, ["validation_strategy", "fold_id", "test_run_id",
                       "window_id", "y_true", "y_pred", "probability_stable",
                       "probability_unstable"])
    check("B1 · colonnes des prédictions individuelles", ok, d)
    check("B1 · probabilités complémentaires",
          np.allclose(p1["probability_stable"] + p1["probability_unstable"], 1.0),
          "P(stable) + P(unstable) = 1")
    for stem in ("validation_strategy_figure.png", "validation_strategy_figure.svg"):
        check(f"B1 · figure {stem.rsplit('.', 1)[1].upper()}",
              (b1_dir / stem).exists(), stem)

    # ---------------- BLOC 2 -------------------------------------------
    f2 = pd.read_csv(b2_dir / "model_metrics_by_fold.csv")
    t2 = pd.read_csv(b2_dir / "model_comparison_table.csv")
    checks2 = json.loads((b2_dir / "methodological_checks.json").read_text("utf-8"))

    check("B2 · les 5 modèles sont évalués",
          set(f2["model"]) == set(common.MODEL_ORDER),
          str(sorted(set(f2["model"]))))
    check("B2 · XGBoost et réseau de neurones inclus (absents du JSON publié)",
          {"XGBoost", "MLP_NeuralNet"} <= set(f2["model"]), "ajoutés")
    check("B2 · les 8 essais réels sont couverts",
          f2["test_run_id"].nunique() == 8,
          f"{f2['test_run_id'].nunique()} essais")
    ok, d = _cols(f2, ["model", "augmentation", "fold_id", "test_run_id",
                       "macro_f1", "stable_f1", "unstable_f1",
                       "unstable_precision", "unstable_recall", "accuracy",
                       "balanced_accuracy", "roc_auc", "number_of_test_windows"])
    check("B2 · colonnes exactes demandées", ok, d)
    check("B2 · aucune fenêtre synthétique dans un fold de test",
          bool((f2["number_of_test_windows"] <= 627).all()
               and f2["test_run_id"].max() < 900),
          "run_id de test tous réels (< 900)")
    check("B2 · générateur fold-aware prouvé identique au générateur publié",
          checks2["generateur_fold_aware_identique_au_generateur_publie"]["verifie"],
          checks2["generateur_fold_aware_identique_au_generateur_publie"]["detail"])
    check("B2 · les 5 garanties sont satisfaites en fold_aware",
          all(g["fold_aware"] == "SATISFAIT" for g in checks2["garanties"]),
          "5/5")
    check("B2 · le protocole historique est signalé comme non conforme",
          sum(g["pooled_global"] == "NON SATISFAIT" for g in checks2["garanties"]) == 2,
          "2 garanties sur 5 non satisfaites")
    check("B2 · colonne d'optimisme dû à la fuite",
          "leakage_inflation" in t2.columns, "leakage_inflation")

    # ---------------- BLOC 3 -------------------------------------------
    oof = pd.read_csv(b3_dir / "logo_oof_predictions.csv")
    cont = pd.read_csv(b3_dir / "continuous_dataset_predictions.csv")
    s3 = pd.read_csv(b3_dir / "generalisation_summary.csv")
    cm3 = pd.read_csv(b3_dir / "confusion_matrices.csv")

    real, _ = common.load_real_windows()
    check("B3 · chaque fenêtre réelle apparaît exactement une fois",
          len(oof) == len(real) and oof["window_id"].is_unique,
          f"{len(oof)} prédictions pour {len(real)} fenêtres, sans doublon")
    check("B3 · les 8 essais sont représentés dans les prédictions OOF",
          oof["run_id"].nunique() == 8, f"{oof['run_id'].nunique()} essais")
    for name, df in (("OOF", oof), ("continu", cont)):
        ok, d = _cols(df, ["run_id", "window_id", "timestamp", "y_true",
                           "y_pred", "probability_stable", "probability_unstable"])
        check(f"B3 · colonnes des prédictions ({name})", ok, d)
    ok, d = _cols(s3, ["number_of_windows", "macro_f1", "unstable_precision",
                       "unstable_recall", "specificity", "accuracy",
                       "balanced_accuracy", "roc_auc", "pr_auc_unstable",
                       "negative_predictive_value", "stable_f1", "unstable_f1"])
    check("B3 · toutes les métriques demandées", ok, d)
    ok, d = _cols(cm3, ["actual_stable_predicted_stable_TN",
                        "actual_stable_predicted_unstable_FP",
                        "actual_unstable_predicted_stable_FN",
                        "actual_unstable_predicted_unstable_TP"])
    check("B3 · TP/TN/FP/FN explicites, instable en classe positive", ok, d)
    check("B3 · les deux évaluations sont présentes", len(s3) == 2,
          "LOGO réel + dataset continu")
    for stem in ("confusion_matrices.png", "confusion_matrices.svg",
                 "roc_pr_curves.png", "roc_pr_curves.svg"):
        check(f"B3 · figure {stem}", (b3_dir / stem).exists(), stem)

    # cohérence matrice / effectifs
    for _, r in cm3.iterrows():
        tot = (r["actual_stable_predicted_stable_TN"]
               + r["actual_stable_predicted_unstable_FP"]
               + r["actual_unstable_predicted_stable_FN"]
               + r["actual_unstable_predicted_unstable_TP"])
        check(f"B3 · matrice cohérente ({r['evaluation']})",
              tot == r["n_windows"], f"{tot} = {r['n_windows']}")

    # ---------------- valeurs citées par l'encadrant -------------------
    cons = json.loads((common.ROOT / "reports" / "eval_consolidated_w60.json")
                      .read_text("utf-8"))
    rb = s3[s3["evaluation_dataset"].str.startswith("B")].iloc[0]
    check("Encadrant · « ROC-AUC = 0,753 » sur le dataset continu",
          abs(rb["roc_auc"] - 0.753) < 0.005, f"recalculé {rb['roc_auc']:.4f}")
    check("Encadrant · « rappel classe instable = 0,62 »",
          abs(rb["unstable_recall"] - 0.62) < 0.01,
          f"recalculé {rb['unstable_recall']:.4f}")
    check("Encadrant · « majorité des erreurs = fausses alertes » (dataset continu)",
          rb["fp_false_alarm"] > rb["fn_unstable_missed"],
          f"{int(rb['fp_false_alarm'])} FP contre {int(rb['fn_unstable_missed'])} FN")
    ra = s3[s3["evaluation_dataset"].str.startswith("A")].iloc[0]
    check("Nuance · sur les essais RÉELS l'erreur dominante s'inverse",
          ra["fn_unstable_missed"] > ra["fp_false_alarm"],
          f"{int(ra['fn_unstable_missed'])} FN contre {int(ra['fp_false_alarm'])} FP "
          "— l'affirmation « majorité de fausses alertes » ne vaut PAS ici")
    check("Traçabilité · réconciliation produite",
          (common.OUT_ROOT / "reconciliation_report.md").exists(),
          "reconciliation_report.md")
    check("Livraison · archive ZIP construite",
          (common.ROOT / "reports" / "AI_thesis_results.zip").exists(),
          "reports/AI_thesis_results.zip")

    # ---------------- restitution --------------------------------------
    width = max(len(c[0]) for c in CHECKS) + 2
    n_ok = sum(1 for _, ok, _ in CHECKS if ok)
    print("=" * (width + 34))
    print("CONTRÔLE D'ACCEPTATION DU LIVRABLE")
    print("=" * (width + 34))
    for label, ok, detail in CHECKS:
        print(f"[{'OK ' if ok else 'ECHEC'}] {label:<{width}} {detail}")
    print("-" * (width + 34))
    print(f"{n_ok}/{len(CHECKS)} contrôles passés")
    return 0 if n_ok == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(run())
