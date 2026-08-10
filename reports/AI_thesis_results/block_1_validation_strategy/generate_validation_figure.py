# -*- coding: utf-8 -*-
"""
block1_validation_strategy.py — BLOC 1 : effet de la stratégie de validation.

Compare trois stratégies sur les mêmes 627 fenêtres réelles (8 essais) :

  1. random_split       — split aléatoire stratifié 70/30 des FENÊTRES, sans
                          tenir compte de l'essai d'origine. Des fenêtres
                          voisines (recouvrement 50 %) du même essai se
                          retrouvent des deux côtés → estimation OPTIMISTE,
                          exposée à la fuite par autocorrélation temporelle.
                          Ce n'est PAS la performance retenue du modèle.
  2. group_shuffle      — GroupShuffleSplit 70/30 sur run_id : aucun essai
                          partagé entre entraînement et test.
  3. logo               — LeaveOneGroupOut : un essai réel entièrement exclu
                          à chaque itération (8 folds).

Sorties (reports/AI_thesis_results/block_1_validation_strategy/) :
  - validation_metrics_by_fold.csv   métriques par stratégie × modèle × fold
  - validation_summary.csv           moyenne/écart-type/min/max agrégés
  - validation_predictions.csv       prédictions individuelles (fenêtre par fenêtre)
  - validation_strategy_figure.png/.svg

Usage : python -m scripts.thesis_results.block1_validation_strategy
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import (GroupShuffleSplit, LeaveOneGroupOut,
                                     train_test_split)

import common

N_REPEATS = 10          # répétitions pour random_split et group_shuffle
TEST_SIZE = 0.30
BASE_SEED = 42
FIGURE_MODEL = "RandomForest"   # modèle retenu — support de la figure

STRATEGY_LABELS = {
    "random_split": "Random split\n(window-level)",
    "group_shuffle": "GroupShuffleSplit\n(run-level)",
    "logo": "Leave-One-Group-Out\n(run-level)",
}


def _iter_folds(real: pd.DataFrame, y: np.ndarray, groups: np.ndarray):
    """Produit (strategy, fold_id, seed, train_idx, test_idx) pour les 3 stratégies."""
    idx = np.arange(len(real))

    # 1. Split aléatoire stratifié des fenêtres — ignore délibérément run_id.
    #    fold_id 0 utilise la seed 42 : c'est le split publié historiquement.
    for i in range(N_REPEATS):
        seed = BASE_SEED + i
        tr, te = train_test_split(idx, test_size=TEST_SIZE, stratify=y,
                                  random_state=seed)
        yield "random_split", i, seed, tr, te

    # 2. GroupShuffleSplit — aucun essai partagé entre entraînement et test.
    #    On reproduit le tirage de src/robustness_check.py : 10 graines tirées
    #    par RandomState(42), chacune donnant un GroupShuffleSplit indépendant.
    #    Les partitions sont donc identiques à celles de
    #    reports/robustness_full_w60.json, ce qui rend les chiffres comparables.
    seeds = np.random.RandomState(BASE_SEED).randint(0, 100000, size=N_REPEATS)
    for i, s in enumerate(seeds):
        gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE,
                                random_state=int(s))
        tr, te = next(gss.split(idx, y, groups=groups))
        yield "group_shuffle", i, int(s), tr, te

    # 3. LeaveOneGroupOut — un essai réel entièrement exclu par fold.
    logo = LeaveOneGroupOut()
    for i, (tr, te) in enumerate(logo.split(idx, y, groups=groups)):
        yield "logo", i, BASE_SEED, tr, te


def run() -> dict:
    # Les essais mono-classe déclenchent des avertissements sklearn attendus
    # (une seule classe présente dans y_true) ; ils sont tracés explicitement
    # via la colonne test_single_class.
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

    common.apply_style()
    out_dir = common.OUT_ROOT / "block_1_validation_strategy"
    out_dir.mkdir(parents=True, exist_ok=True)

    real, feats = common.load_real_windows()
    X = real[feats]
    y = real["is_stable"].to_numpy().astype(int)
    groups = real["run_id"].to_numpy()
    models = common.make_models()

    fold_rows, pred_rows = [], []

    for strategy, fold_id, seed, tr, te in _iter_folds(real, y, groups):
        X_tr, X_te = X.iloc[tr], X.iloc[te]
        y_tr, y_te = y[tr], y[te]
        test_runs = sorted(set(groups[te].tolist()))
        train_runs = sorted(set(groups[tr].tolist()))
        # Identifiant lisible du test : un essai pour LOGO, une liste sinon.
        test_run_id = (str(test_runs[0]) if len(test_runs) == 1
                       else "|".join(str(r) for r in test_runs))

        for name in common.MODEL_ORDER:
            if len(np.unique(y_tr)) < 2:
                continue
            y_pred, proba_stable = common.fit_predict(
                models[name], X_tr, y_tr, X_te)
            m = common.compute_metrics(y_te, y_pred, proba_stable)

            fold_rows.append({
                "validation_strategy": strategy,
                "model": name,
                "fold_id": fold_id,
                "seed": seed,
                "test_run_id": test_run_id,
                "n_train_runs": len(train_runs),
                "n_test_runs": len(test_runs),
                "n_train_windows": int(len(tr)),
                "n_test_windows": int(len(te)),
                "train_pct_stable": round(100 * float(y_tr.mean()), 2),
                "test_pct_stable": round(100 * float(y_te.mean()), 2),
                "test_single_class": bool(len(np.unique(y_te)) < 2),
                **m,
            })

            for j, w in enumerate(te):
                pred_rows.append({
                    "validation_strategy": strategy,
                    "model": name,
                    "fold_id": fold_id,
                    "test_run_id": int(groups[w]),
                    "window_id": real["window_id"].iloc[w],
                    "y_true": int(y_te[j]),
                    "y_pred": int(y_pred[j]),
                    "y_true_label": "stable" if y_te[j] == 1 else "unstable",
                    "y_pred_label": "stable" if y_pred[j] == 1 else "unstable",
                    "probability_stable": float(proba_stable[j]),
                    "probability_unstable": float(1.0 - proba_stable[j]),
                })

    df_folds = pd.DataFrame(fold_rows)
    df_preds = pd.DataFrame(pred_rows)

    # ---- Agrégats par stratégie × modèle -----------------------------
    # Deux périmètres sont publiés côte à côte :
    #   scope = "all_folds"      → tous les folds, y compris les essais réels
    #                              mono-classe (32 et 42, 100 % stables). Sur
    #                              ces essais le macro-F1 vaut mécaniquement 1
    #                              si le modèle ne lève aucune alerte, et le
    #                              ROC-AUC est indéfini : la moyenne est
    #                              artificiellement tirée vers le haut.
    #   scope = "scorable_folds" → uniquement les folds dont le test contient
    #                              les deux classes. C'est le périmètre à
    #                              retenir, et celui du bloc 2 (6 folds sur 8).
    # Pour random_split et group_shuffle les deux périmètres coïncident.
    summary_rows = []
    for (strategy, model), grp in df_folds.groupby(["validation_strategy", "model"]):
        for scope, sub in (("all_folds", grp),
                           ("scorable_folds", grp[~grp["test_single_class"]])):
            if len(sub) == 0:
                continue
            agg = common.aggregate(sub.to_dict("records"), common.METRIC_KEYS)
            summary_rows.append({
                "validation_strategy": strategy,
                "model": model,
                "scope": scope,
                "n_evaluations": int(len(sub)),
                "n_evaluations_single_class": int(sub["test_single_class"].sum()),
                "n_test_windows_total": int(sub["n_test_windows"].sum()),
                "n_train_windows_mean": float(sub["n_train_windows"].mean()),
                **agg,
            })
    df_summary = pd.DataFrame(summary_rows)
    s_order = {s: i for i, s in enumerate(STRATEGY_LABELS)}
    m_order = {m: i for i, m in enumerate(common.MODEL_ORDER)}
    df_summary["_s"] = df_summary["validation_strategy"].map(s_order)
    df_summary["_m"] = df_summary["model"].map(m_order)
    df_summary = (df_summary.sort_values(["_s", "_m", "scope"])
                  .drop(columns=["_s", "_m"]).reset_index(drop=True))

    common.write_csv(df_folds, out_dir / "validation_metrics_by_fold.csv")
    common.write_csv(df_summary, out_dir / "validation_summary.csv")
    common.write_csv(df_preds, out_dir / "validation_predictions.csv")

    _figure(df_folds, df_summary, out_dir)
    return {"folds": df_folds, "summary": df_summary, "predictions": df_preds}


def _figure(df_folds: pd.DataFrame, df_summary: pd.DataFrame, out_dir) -> None:
    """Panneau A : macro-F1 moyen ± écart-type. Panneau B : ROC-AUC. Folds superposés."""
    import matplotlib.pyplot as plt

    strategies = list(STRATEGY_LABELS)
    # Périmètre "scorable" : les essais mono-classe sont écartés, sinon la
    # moyenne LOGO est gonflée par des macro-F1 de 1 mécaniques.
    sub_sum = df_summary[(df_summary["model"] == FIGURE_MODEL)
                         & (df_summary["scope"] == "scorable_folds")
                         ].set_index("validation_strategy")
    sub_fold = df_folds[(df_folds["model"] == FIGURE_MODEL)
                        & (~df_folds["test_single_class"])]

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
    panels = [("macro_f1", "Macro-F1", "A"), ("roc_auc", "ROC-AUC", "B")]

    for ax, (metric, ylabel, tag) in zip(axes, panels):
        means = [sub_sum.loc[s, f"{metric}_mean"] for s in strategies]
        stds = [sub_sum.loc[s, f"{metric}_std"] for s in strategies]
        xs = np.arange(len(strategies))

        # Le split aléatoire est mis en évidence comme estimation biaisée.
        colors = [common.PALETTE["secondary"]] + [common.PALETTE["primary"]] * 2
        ax.bar(xs, means, yerr=stds, width=0.55, color=colors,
               edgecolor="#303030", linewidth=0.7,
               error_kw={"ecolor": "#303030", "capsize": 5, "lw": 1.0}, zorder=2)

        # Résultats individuels des folds superposés (jitter horizontal léger).
        rng = np.random.default_rng(7)
        for xi, s in enumerate(strategies):
            vals = sub_fold.loc[sub_fold["validation_strategy"] == s, metric]
            vals = vals[np.isfinite(vals)]
            ax.scatter(xi + rng.uniform(-0.14, 0.14, len(vals)), vals,
                       s=16, color="#1a1a1a", alpha=0.55, zorder=3,
                       edgecolor="none")

        for xi, (m, sd) in enumerate(zip(means, stds)):
            ax.text(xi, min(1.0, m + sd) + 0.03, f"{m:.3f}\n± {sd:.3f}",
                    ha="center", va="bottom", fontsize=8)

        ax.set_xticks(xs)
        ax.set_xticklabels([STRATEGY_LABELS[s] for s in strategies], fontsize=8)
        ax.set_ylim(0, 1.18)
        ax.set_yticks(np.arange(0, 1.01, 0.2))
        ax.set_ylabel(ylabel)
        ax.set_title(f"{tag} — {ylabel} par stratégie de validation", loc="left")
        ax.set_axisbelow(True)
        ax.xaxis.grid(False)

    fig.suptitle(
        f"Effet de la stratégie de validation — {common.MODEL_LABELS[FIGURE_MODEL]}, "
        f"fenêtre {common.WINDOW_SEC} s, 8 essais réels",
        fontsize=10.5, fontweight="bold", y=1.02)
    fig.text(0.5, -0.05,
             "Le split aléatoire (orange) partage des fenêtres voisines du même essai entre entraînement et test : "
             "estimation optimiste exposée à la fuite\npar autocorrélation temporelle. Elle n'est pas la performance "
             "retenue du modèle. Les points noirs sont les folds individuels.",
             ha="center", fontsize=7.5, color="#404040")

    fig.tight_layout()
    common.save_figure(fig, out_dir, "validation_strategy_figure")
    plt.close(fig)


if __name__ == "__main__":
    res = run()
    print(res["summary"].to_string(index=False))
