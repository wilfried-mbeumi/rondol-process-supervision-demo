"""
robustness_check.py — Validation de robustesse Phase 4.

Compare 3 protocoles de validation pour démasquer une éventuelle inflation
des scores due à l'autocorrélation temporelle entre fenêtres d'un même run :

  A) Split aléatoire stratifié 70/30 (baseline — voir train_models.py)
     → des fenêtres voisines temporellement peuvent finir en train ET test
     → optimiste

  B) GroupShuffleSplit 70/30 par run_id × 10 seeds
     → aucun run partagé entre train et test
     → réaliste (test sur runs jamais vus)

  C) LeaveOneGroupOut (8 folds = 8 runs OK)
     → chaque run devient test une fois, on observe la variabilité inter-runs
     → exhaustif

Vérifie aussi la distribution des classes dans chaque train/test pour
détecter les splits dégénérés (run de test 100 % stable, etc.).

Usage :
  python -m src.robustness_check
  python -m src.robustness_check --window 60 --n-seeds 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline as SkPipeline

from . import config, ml_utils

# Filtre les warnings sklearn liés aux groupes ou classes manquantes
warnings.filterwarnings("ignore", category=UserWarning)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _make_pipelines(spw: float, random_state: int) -> dict:
    """Construit les pipelines, avec imputer en tête pour RF/XGB (NaN)."""
    pipes = ml_utils.make_all_models(random_state=random_state)
    out = {}
    for name, p in pipes.items():
        p = clone(p)
        if name == "XGBoost":
            p.named_steps["clf"].set_params(scale_pos_weight=spw)
        if "imputer" not in p.named_steps:
            p = SkPipeline([("imputer", SimpleImputer(strategy="median"))]
                          + list(p.steps))
        out[name] = p
    return out


def _eval_one_split(X_tr, y_tr, X_te, y_te, random_state: int) -> dict:
    """Train/eval RF, XGB, SVM sur un split donné."""
    spw = ml_utils.pos_weight_from_y(y_tr)
    pipes = _make_pipelines(spw, random_state)
    out = {}
    for name, p in pipes.items():
        try:
            p.fit(X_tr, y_tr)
            y_pred = p.predict(X_te)
            y_proba = (p.predict_proba(X_te)[:, 1]
                       if hasattr(p, "predict_proba") else None)
            m = ml_utils.compute_metrics(y_te, y_pred, y_proba)
            out[name] = {
                "accuracy": m["accuracy"],
                "f1_macro": m["f1_macro"],
                "f1_unstable": m["f1_unstable"],
                "f1_stable": m["f1_stable"],
                "roc_auc": m.get("roc_auc", np.nan),
            }
        except Exception as e:
            out[name] = {"error": str(e)}
    return out


def random_split_baseline(X, y_bin, random_state: int) -> dict:
    """Split aléatoire stratifié 70/30 (référence)."""
    X_tr, X_te, y_tr, y_te = ml_utils.stratified_split(
        X, y_bin, test_size=0.30, random_state=random_state
    )
    return {
        "train_size": len(X_tr),
        "test_size": len(X_te),
        "train_pct_stable": round(100 * y_tr.mean(), 1),
        "test_pct_stable":  round(100 * y_te.mean(), 1),
        "scores": _eval_one_split(X_tr, y_tr, X_te, y_te, random_state),
    }


def group_shuffle_protocol(X, y_bin, groups, n_seeds: int,
                           random_state: int) -> dict:
    """N GroupShuffleSplit 70/30 — moyenne et écart-type des scores."""
    per_seed = []
    rng = np.random.RandomState(random_state)
    seeds = rng.randint(0, 100000, size=n_seeds)
    for s in seeds:
        X_tr, X_te, y_tr, y_te, g_tr, g_te = ml_utils.group_split(
            X, y_bin, groups, test_size=0.30, random_state=int(s)
        )
        scores = _eval_one_split(X_tr, y_tr, X_te, y_te, random_state)
        per_seed.append({
            "seed": int(s),
            "train_runs": sorted(g_tr.unique().tolist()),
            "test_runs":  sorted(g_te.unique().tolist()),
            "train_size": len(X_tr),
            "test_size":  len(X_te),
            "train_pct_stable": round(100 * y_tr.mean(), 1),
            "test_pct_stable":  round(100 * y_te.mean(), 1),
            "scores": scores,
        })
    # Agrégation
    agg = {}
    for model in ("RandomForest", "XGBoost", "SVM"):
        for metric in ("accuracy", "f1_macro", "f1_unstable", "f1_stable", "roc_auc"):
            vals = [r["scores"][model].get(metric) for r in per_seed
                    if "error" not in r["scores"][model]]
            vals = [v for v in vals if v is not None and not pd.isna(v)]
            if vals:
                agg.setdefault(model, {})[metric + "_mean"] = round(float(np.mean(vals)), 4)
                agg[model][metric + "_std"] = round(float(np.std(vals)), 4)
    return {"per_seed": per_seed, "aggregate": agg}


def leave_one_group_out_protocol(X, y_bin, groups, random_state: int) -> dict:
    """LeaveOneGroupOut : 1 fold par run. F1 par run + moyenne."""
    rows = []
    for train_idx, test_idx in ml_utils.iter_leave_one_group_out(X, y_bin, groups):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y_bin.iloc[train_idx], y_bin.iloc[test_idx]
        g_te = groups.iloc[test_idx]
        test_run = int(g_te.iloc[0])
        scores = _eval_one_split(X_tr, y_tr, X_te, y_te, random_state)
        rows.append({
            "test_run": test_run,
            "n_test": len(X_te),
            "test_pct_stable": round(100 * y_te.mean(), 1),
            "scores": scores,
        })

    # Agrégation
    agg = {}
    for model in ("RandomForest", "XGBoost", "SVM"):
        for metric in ("accuracy", "f1_macro", "f1_unstable", "f1_stable", "roc_auc"):
            vals = []
            for r in rows:
                v = r["scores"][model].get(metric)
                if v is not None and not pd.isna(v):
                    vals.append(v)
            if vals:
                agg.setdefault(model, {})[metric + "_mean"] = round(float(np.mean(vals)), 4)
                agg[model][metric + "_std"] = round(float(np.std(vals)), 4)
    return {"per_run": rows, "aggregate": agg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--n-seeds", type=int, default=10)
    ap.add_argument("--random-state", type=int, default=42)
    args = ap.parse_args()

    print("=" * 78)
    print(f"ROBUSTESSE — fenêtre {args.window}s")
    print("=" * 78)

    # Chargement
    X, y_bin, y_score, df = ml_utils.load_training_dataset(
        window_sec=args.window, only_good_runs=True
    )
    groups = df["run_id"].astype(int)
    print(f"Dataset : {X.shape[0]} fenêtres × {X.shape[1]} features")
    print(f"Runs distincts : {sorted(groups.unique().tolist())}")
    print(f"Distribution stable globale : {100 * y_bin.mean():.1f} %")
    print(f"Distribution par run :")
    per_run = pd.DataFrame({
        "run_id": groups,
        "is_stable": y_bin
    }).groupby("run_id").agg(n=("is_stable", "size"),
                              pct_stable=("is_stable", lambda s: round(100 * s.mean(), 1)))
    print(per_run.to_string())

    # ----- A) Random split baseline -----
    print("\n" + "-" * 78)
    print("A) RANDOM SPLIT (stratifié 70/30) — baseline")
    print("-" * 78)
    t0 = time.time()
    rnd = random_split_baseline(X, y_bin, args.random_state)
    print(f"train={rnd['train_size']} ({rnd['train_pct_stable']}% stables) | "
          f"test={rnd['test_size']} ({rnd['test_pct_stable']}% stables)")
    rnd_df = pd.DataFrame(rnd["scores"]).T.round(4)
    print(rnd_df.to_string())
    print(f"({time.time() - t0:.1f}s)")

    # ----- B) GroupShuffleSplit -----
    print("\n" + "-" * 78)
    print(f"B) GROUPSHUFFLESPLIT 70/30 par run_id × {args.n_seeds} seeds")
    print("-" * 78)
    t0 = time.time()
    gss = group_shuffle_protocol(X, y_bin, groups, n_seeds=args.n_seeds,
                                 random_state=args.random_state)
    seeds_df = pd.DataFrame([{
        "seed": r["seed"],
        "train_runs": r["train_runs"],
        "test_runs":  r["test_runs"],
        "train_size": r["train_size"],
        "test_size":  r["test_size"],
        "test_%stab": r["test_pct_stable"],
        "f1m_RF":  r["scores"]["RandomForest"].get("f1_macro"),
        "f1m_XGB": r["scores"]["XGBoost"].get("f1_macro"),
        "f1m_SVM": r["scores"]["SVM"].get("f1_macro"),
    } for r in gss["per_seed"]])
    print(seeds_df.to_string(index=False))
    print("\nAgrégat (moyenne ± std sur les seeds) :")
    agg_df = pd.DataFrame(gss["aggregate"]).T.round(4)
    cols_show = ["accuracy_mean", "accuracy_std",
                 "f1_macro_mean", "f1_macro_std",
                 "f1_unstable_mean", "f1_unstable_std",
                 "roc_auc_mean", "roc_auc_std"]
    cols_show = [c for c in cols_show if c in agg_df.columns]
    print(agg_df[cols_show].to_string())
    print(f"({time.time() - t0:.1f}s)")

    # ----- C) LeaveOneGroupOut -----
    print("\n" + "-" * 78)
    print("C) LEAVE-ONE-GROUP-OUT (1 run de test par fold)")
    print("-" * 78)
    t0 = time.time()
    logo = leave_one_group_out_protocol(X, y_bin, groups, args.random_state)
    logo_df = pd.DataFrame([{
        "test_run":      r["test_run"],
        "n_test":        r["n_test"],
        "test_%stab":    r["test_pct_stable"],
        "f1m_RF":  r["scores"]["RandomForest"].get("f1_macro"),
        "f1m_XGB": r["scores"]["XGBoost"].get("f1_macro"),
        "f1m_SVM": r["scores"]["SVM"].get("f1_macro"),
        "f1u_XGB": r["scores"]["XGBoost"].get("f1_unstable"),
        "auc_XGB": r["scores"]["XGBoost"].get("roc_auc"),
    } for r in logo["per_run"]]).round(3)
    print(logo_df.to_string(index=False))
    print("\nMoyennes par modèle (sur les 8 runs) :")
    logo_agg = pd.DataFrame(logo["aggregate"]).T.round(4)
    cols_show2 = [c for c in cols_show if c in logo_agg.columns]
    print(logo_agg[cols_show2].to_string())
    print(f"({time.time() - t0:.1f}s)")

    # ----- Synthèse comparative -----
    print("\n" + "=" * 78)
    print("SYNTHÈSE COMPARATIVE (F1 macro / ROC-AUC)")
    print("=" * 78)
    rows = []
    for model in ("RandomForest", "XGBoost", "SVM"):
        rows.append({
            "model": model,
            "RandomSplit_F1m": round(rnd["scores"][model]["f1_macro"], 4),
            "RandomSplit_AUC": round(rnd["scores"][model].get("roc_auc", np.nan), 4),
            "GroupSplit_F1m_mean":  gss["aggregate"][model].get("f1_macro_mean"),
            "GroupSplit_F1m_std":   gss["aggregate"][model].get("f1_macro_std"),
            "GroupSplit_AUC_mean":  gss["aggregate"][model].get("roc_auc_mean"),
            "LOGO_F1m_mean":        logo["aggregate"][model].get("f1_macro_mean"),
            "LOGO_F1m_std":         logo["aggregate"][model].get("f1_macro_std"),
            "LOGO_AUC_mean":        logo["aggregate"][model].get("roc_auc_mean"),
        })
    syn = pd.DataFrame(rows)
    print(syn.to_string(index=False))

    # Sauvegardes
    out_csv = config.REPORTS_DIR / f"robustness_summary_w{args.window}.csv"
    syn.to_csv(out_csv, index=False)
    out_json = config.REPORTS_DIR / f"robustness_full_w{args.window}.json"
    out_json.write_text(json.dumps({
        "random_split": rnd,
        "group_shuffle": gss,
        "logo": logo,
        "summary": syn.to_dict(orient="records"),
    }, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(f"\n→ {out_csv}")
    print(f"→ {out_json}")


if __name__ == "__main__":
    main()
