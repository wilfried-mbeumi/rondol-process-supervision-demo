# -*- coding: utf-8 -*-
"""
block2_model_augmentation.py — BLOC 2 : comparaison des modèles et effet de
l'augmentation, en validation Leave-One-Group-Out.

Cinq modèles : logistic regression, SVM (RBF), Random Forest, XGBoost,
réseau de neurones (MLP). Le test est TOUJOURS un essai réel jamais vu ;
aucune fenêtre synthétique n'entre jamais dans un fold de test.

TROIS conditions d'entraînement sont évaluées, et non deux
--------------------------------------------------------
  `none`          entraînement sur les fenêtres réelles des autres essais.

  `pooled_global` protocole HISTORIQUE du projet (celui qui a produit
                  reports/augmentation_eval.json) : on ajoute le pool
                  synthétique publié, généré UNE FOIS à partir de la totalité
                  des essais réels. L'essai laissé de côté a donc servi
                  d'ancre et a contribué aux écarts-types de classe utilisés
                  pour le jitter. => la garantie « le run exclu n'a pas servi
                  de point d'ancrage » N'EST PAS satisfaite. Cette condition
                  est conservée pour la traçabilité des chiffres déjà cités,
                  et étiquetée comme optimiste.

  `fold_aware`    protocole CORRIGÉ : à chaque fold, le pool synthétique est
                  REGÉNÉRÉ à partir des seuls essais d'entraînement (même
                  algorithme, même volume de 800 fenêtres, même graine).
                  Les cinq garanties demandées sont alors satisfaites.

Sorties (reports/AI_thesis_results/block_2_model_augmentation/) :
  - model_metrics_by_fold.csv       une ligne par modèle × condition × fold
  - model_comparison_summary.csv    agrégats + Δ macro-F1
  - model_augmentation_figure.png/.svg
  - methodological_checks.json      réponse point par point à la checklist

Usage : python -m scripts.thesis_results.block2_model_augmentation
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd

from . import common, fold_augment

N_PER_CLASS = 400        # → 800 fenêtres synthétiques, volume du pool publié
SEED = 42

CONDITIONS = ["none", "pooled_global", "fold_aware"]
CONDITION_LABELS = {
    "none": "Sans augmentation",
    "pooled_global": "Augmentation globale\n(protocole historique)",
    "fold_aware": "Augmentation limitée\nau fold d'entraînement",
}


def run() -> dict:
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

    common.apply_style()
    out_dir = common.OUT_ROOT / "block_2_model_augmentation"
    out_dir.mkdir(parents=True, exist_ok=True)

    real, feats = common.load_real_windows()
    syn_pool = common.load_synthetic_pool()
    models = common.make_models()
    runs = sorted(real["run_id"].unique().tolist())

    # Preuve que le générateur fold-aware est bien le générateur publié,
    # au seul support d'ancrage près.
    selftest_ok, selftest_msg = fold_augment.selftest_reproduces_published_pool(
        real, syn_pool, feats)

    fold_rows, pred_rows = [], []

    for fold_id, r in enumerate(runs):
        te_mask = real["run_id"] == r
        te = real[te_mask]
        tr_real = real[~te_mask]
        y_te = te["is_stable"].to_numpy().astype(int)
        single_class = len(np.unique(y_te)) < 2

        # Pool fold-aware : ancres = essais d'entraînement UNIQUEMENT.
        syn_fold = fold_augment.generate_synthetic(
            tr_real, n_per_class=N_PER_CLASS, seed=SEED)

        train_sets = {
            "none": tr_real,
            "pooled_global": pd.concat([tr_real, syn_pool], ignore_index=True),
            "fold_aware": pd.concat([tr_real, syn_fold], ignore_index=True),
        }

        for cond in CONDITIONS:
            tr = train_sets[cond]
            X_tr, y_tr = tr[feats], tr["is_stable"].to_numpy().astype(int)
            X_te = te[feats]

            for name in common.MODEL_ORDER:
                y_pred, proba_stable = common.fit_predict(
                    models[name], X_tr, y_tr, X_te)
                m = common.compute_metrics(y_te, y_pred, proba_stable)

                fold_rows.append({
                    "model": name,
                    "augmentation": cond,
                    "fold_id": fold_id,
                    "test_run_id": int(r),
                    "n_train_windows": int(len(tr)),
                    "n_train_real": int(len(tr_real)),
                    "n_train_synthetic": int(len(tr) - len(tr_real)),
                    "number_of_test_windows": int(len(te)),
                    "test_pct_stable": round(100 * float(y_te.mean()), 2),
                    "test_single_class": bool(single_class),
                    "macro_f1": m["macro_f1"],
                    "stable_f1": m["stable_f1"],
                    "unstable_f1": m["unstable_f1"],
                    "unstable_precision": m["unstable_precision"],
                    "unstable_recall": m["unstable_recall"],
                    "accuracy": m["accuracy"],
                    "balanced_accuracy": m["balanced_accuracy"],
                    "roc_auc": m["roc_auc"],
                    "tp_unstable_detected": m["tp_unstable_detected"],
                    "fn_unstable_missed": m["fn_unstable_missed"],
                    "fp_false_alarm": m["fp_false_alarm"],
                    "tn_stable_ok": m["tn_stable_ok"],
                })

                for j, wid in enumerate(te["window_id"].tolist()):
                    pred_rows.append({
                        "model": name,
                        "augmentation": cond,
                        "fold_id": fold_id,
                        "test_run_id": int(r),
                        "window_id": wid,
                        "y_true": int(y_te[j]),
                        "y_pred": int(y_pred[j]),
                        "probability_stable": float(proba_stable[j]),
                        "probability_unstable": float(1.0 - proba_stable[j]),
                    })

        print(f"  fold {fold_id} (essai {r}, {len(te)} fenêtres, "
              f"{'MONO-CLASSE' if single_class else 'bi-classe'}) terminé")

    df_folds = pd.DataFrame(fold_rows)
    df_preds = pd.DataFrame(pred_rows)

    # ---- Agrégats -----------------------------------------------------
    # Les essais mono-classe (32 et 42, 100 % stables) ne permettent ni
    # macro-F1 interprétable ni ROC-AUC : ils sont exclus de l'agrégat,
    # exactement comme dans src/evaluate_augmentation.py (n_folds = 6).
    scorable = df_folds[~df_folds["test_single_class"]]

    summary_rows = []
    for (model, cond), grp in scorable.groupby(["model", "augmentation"]):
        agg = common.aggregate(grp.to_dict("records"), common.METRIC_KEYS)
        summary_rows.append({
            "model": model, "augmentation": cond,
            "n_folds_scorable": int(len(grp)),
            "n_folds_total": int(len(runs)),
            **agg,
        })
    df_summary = pd.DataFrame(summary_rows)

    # ---- Tableau final demandé (une ligne par modèle) -----------------
    piv = df_summary.set_index(["model", "augmentation"])
    table_rows = []
    for name in common.MODEL_ORDER:
        row = {"model": common.MODEL_LABELS[name]}
        for cond in CONDITIONS:
            row[f"macro_f1_{cond}"] = piv.loc[(name, cond), "macro_f1_mean"]
            row[f"macro_f1_{cond}_std"] = piv.loc[(name, cond), "macro_f1_std"]
            row[f"roc_auc_{cond}"] = piv.loc[(name, cond), "roc_auc_mean"]
            row[f"roc_auc_{cond}_std"] = piv.loc[(name, cond), "roc_auc_std"]
        row["delta_macro_f1_pooled_global"] = (
            row["macro_f1_pooled_global"] - row["macro_f1_none"])
        row["delta_macro_f1_fold_aware"] = (
            row["macro_f1_fold_aware"] - row["macro_f1_none"])
        row["leakage_inflation"] = (
            row["macro_f1_pooled_global"] - row["macro_f1_fold_aware"])
        table_rows.append(row)
    df_table = pd.DataFrame(table_rows)

    common.write_csv(df_folds, out_dir / "model_metrics_by_fold.csv")
    common.write_csv(df_summary, out_dir / "model_comparison_summary.csv")
    common.write_csv(df_table, out_dir / "model_comparison_table.csv")
    common.write_csv(df_preds, out_dir / "model_predictions_by_fold.csv")

    checks = _methodological_checks(real, runs, selftest_ok, selftest_msg,
                                    df_folds)
    (out_dir / "methodological_checks.json").write_text(
        json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")

    _figure(df_folds, df_summary, out_dir)
    return {"folds": df_folds, "summary": df_summary, "table": df_table,
            "checks": checks}


def _methodological_checks(real, runs, selftest_ok, selftest_msg, df_folds) -> dict:
    """Réponse explicite, point par point, à la checklist de l'encadrant."""
    n_syn = int(df_folds.loc[df_folds["augmentation"] == "fold_aware",
                             "n_train_synthetic"].max())
    return {
        "protocole": "LeaveOneGroupOut sur les 8 essais réels, fenêtre 60 s",
        "n_essais_reels": len(runs),
        "n_fenetres_reelles": int(len(real)),
        "n_fenetres_synthetiques_par_fold": n_syn,
        "essais_mono_classe_exclus_des_agregats": [32, 42],
        "generateur_fold_aware_identique_au_generateur_publie": {
            "verifie": bool(selftest_ok),
            "detail": selftest_msg,
            "methode": "regénération avec le support d'ancrage complet et la "
                       "graine 42, puis comparaison bit-à-bit des 87 features "
                       "au pool publié dans dataset_ml_w60_augmented.csv",
        },
        "garanties": [
            {
                "point": "le run réel exclu n'a jamais été utilisé pour entraîner le modèle",
                "pooled_global": "SATISFAIT",
                "fold_aware": "SATISFAIT",
                "preuve": "le fold de test est sélectionné par run_id ; "
                          "l'entraînement porte sur real[run_id != r]",
            },
            {
                "point": "il n'a pas été utilisé pour calculer les paramètres de prétraitement",
                "pooled_global": "SATISFAIT",
                "fold_aware": "SATISFAIT",
                "preuve": "imputation médiane et standardisation sont des étapes "
                          "internes du Pipeline sklearn, refittées sur le seul "
                          "fold d'entraînement à chaque appel de fit()",
            },
            {
                "point": "il n'a pas été utilisé comme point d'ancrage pour générer les fenêtres synthétiques",
                "pooled_global": "NON SATISFAIT",
                "fold_aware": "SATISFAIT",
                "preuve": "pooled_global réutilise le pool publié, généré une "
                          "fois sur les 8 essais ; fold_aware appelle "
                          "generate_synthetic(real[run_id != r]) à chaque fold",
            },
            {
                "point": "les données synthétiques ont été générées exclusivement à partir des observations du fold d'entraînement",
                "pooled_global": "NON SATISFAIT",
                "fold_aware": "SATISFAIT",
                "preuve": "les taux de valeurs manquantes par capteur et les "
                          "écarts-types de classe qui pilotent le jitter sont "
                          "estimés sur le seul fold d'entraînement",
            },
            {
                "point": "aucune donnée synthétique n'a été ajoutée au fold de test",
                "pooled_global": "SATISFAIT",
                "fold_aware": "SATISFAIT",
                "preuve": "le fold de test est extrait de real (synthetic == 0) ; "
                          "les run_id synthétiques (900-909) sont disjoints des "
                          "run_id réels",
            },
        ],
        "conclusion": "Le protocole historique (pooled_global) viole deux des "
                      "cinq garanties. Les chiffres publiés dans "
                      "reports/augmentation_eval.json en sont issus et sont donc "
                      "optimistes. La condition fold_aware satisfait les cinq "
                      "garanties et constitue le résultat à retenir pour la thèse.",
    }


def _figure(df_folds: pd.DataFrame, df_summary: pd.DataFrame, out_dir) -> None:
    """Panneau A : macro-F1 par modèle et condition. Panneau B : Δ macro-F1."""
    import matplotlib.pyplot as plt

    piv = df_summary.set_index(["model", "augmentation"])
    scorable = df_folds[~df_folds["test_single_class"]]
    xs = np.arange(len(common.MODEL_ORDER))
    width = 0.26
    colors = {"none": common.PALETTE["neutral"],
              "pooled_global": common.PALETTE["secondary"],
              "fold_aware": common.PALETTE["primary"]}

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6),
                             gridspec_kw={"width_ratios": [1.55, 1]})

    # --- Panneau A : macro-F1 -----------------------------------------
    ax = axes[0]
    rng = np.random.default_rng(11)
    for ci, cond in enumerate(CONDITIONS):
        off = (ci - 1) * width
        means = [piv.loc[(m, cond), "macro_f1_mean"] for m in common.MODEL_ORDER]
        stds = [piv.loc[(m, cond), "macro_f1_std"] for m in common.MODEL_ORDER]
        ax.bar(xs + off, means, width, yerr=stds, color=colors[cond],
               edgecolor="#303030", linewidth=0.6,
               label=CONDITION_LABELS[cond].replace("\n", " "),
               error_kw={"ecolor": "#303030", "capsize": 3, "lw": 0.9}, zorder=2)
        # résultats individuels des folds évaluables
        for mi, m in enumerate(common.MODEL_ORDER):
            v = scorable.loc[(scorable["model"] == m)
                             & (scorable["augmentation"] == cond), "macro_f1"]
            v = v[np.isfinite(v)]
            ax.scatter(xs[mi] + off + rng.uniform(-0.07, 0.07, len(v)), v,
                       s=11, color="#1a1a1a", alpha=0.5, zorder=3,
                       edgecolor="none")

    ax.set_xticks(xs)
    ax.set_xticklabels([common.MODEL_LABELS[m].replace(" (", "\n(")
                        for m in common.MODEL_ORDER], fontsize=8)
    ax.set_ylabel("Macro-F1")
    # Marge haute suffisante pour que la légende sur une ligne ne recouvre
    # ni les barres ni leurs barres d'erreur.
    ax.set_ylim(0, 1.34)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_title("A — Macro-F1 en validation Leave-One-Group-Out "
                 "(6 essais évaluables sur 8)", loc="left")
    ax.legend(fontsize=7.5, loc="upper left", ncol=3,
              columnspacing=1.2, handlelength=1.4)
    ax.set_axisbelow(True)
    ax.xaxis.grid(False)

    # --- Panneau B : Δ macro-F1 ---------------------------------------
    ax = axes[1]
    d_pool = [piv.loc[(m, "pooled_global"), "macro_f1_mean"]
              - piv.loc[(m, "none"), "macro_f1_mean"] for m in common.MODEL_ORDER]
    d_fold = [piv.loc[(m, "fold_aware"), "macro_f1_mean"]
              - piv.loc[(m, "none"), "macro_f1_mean"] for m in common.MODEL_ORDER]
    ax.bar(xs - width / 2, d_pool, width, color=colors["pooled_global"],
           edgecolor="#303030", linewidth=0.6,
           label="Augmentation globale (historique)", zorder=2)
    ax.bar(xs + width / 2, d_fold, width, color=colors["fold_aware"],
           edgecolor="#303030", linewidth=0.6,
           label="Augmentation fold-aware", zorder=2)
    ax.axhline(0, color="#303030", lw=0.9, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([common.MODEL_LABELS[m].replace(" (", "\n(")
                        for m in common.MODEL_ORDER], fontsize=8)
    ax.set_ylabel(r"$\Delta$ Macro-F1 vs sans augmentation")
    ax.set_title(r"B — Gain apporté par l'augmentation", loc="left")
    ax.legend(fontsize=7.5)
    ax.set_axisbelow(True)
    ax.xaxis.grid(False)

    fig.suptitle("Comparaison des modèles et effet de l'augmentation — "
                 "validation Leave-One-Group-Out sur essais réels",
                 fontsize=10.5, fontweight="bold", y=1.02)
    fig.text(0.5, -0.06,
             "L'écart entre les barres orange et bleues mesure l'optimisme introduit par un pool synthétique "
             "généré à partir de l'essai de test.\nSeule la condition fold-aware satisfait les cinq garanties "
             "méthodologiques. Points noirs : folds individuels.",
             ha="center", fontsize=7.5, color="#404040")

    fig.tight_layout()
    common.save_figure(fig, out_dir, "model_augmentation_figure")
    plt.close(fig)


if __name__ == "__main__":
    res = run()
    print()
    print(res["table"].to_string(index=False))
