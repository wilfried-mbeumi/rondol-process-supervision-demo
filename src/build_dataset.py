"""
build_dataset.py — Orchestrateur du pipeline dataset ML.

Exécution :
  python -m src.build_dataset              # fenêtre par défaut
  python -m src.build_dataset --window 120 # autre fenêtre

Étapes enchaînées :
  1. Load + resample + merge (12 capteurs)
  2. Segmentation en runs (DIE > 120 °C)
  3. Extraction de features par fenêtre glissante
  4. Calcul de la cible de stabilité sur la fenêtre SUIVANTE (anti-leakage)
  5. Tag `bad_run` pour les runs courts (non supprimés)
  6. Sauvegarde du dataset ML final (avec suffixe de fenêtre)
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd

from . import config, preprocess, features, target

# Windows cp1252 → UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def build_dataset(window_sec: int = config.WINDOW_SEC,
                  step_sec: int | None = None,
                  cache_merged: pd.DataFrame | None = None,
                  cache_segmented: pd.DataFrame | None = None,
                  save: bool = True) -> dict:
    """Construit le dataset ML pour une taille de fenêtre donnée.

    Retourne un dict de stats utiles pour les comparaisons (compare_windows).
    """
    t0 = time.time()

    # Pas par défaut = fenêtre/2 → 50 % d'overlap
    if step_sec is None:
        step_sec = window_sec // 2

    suffix = f"w{window_sec}"

    # Dossiers de sortie
    for d in (config.DATA_INTERIM, config.DATA_PROCESSED,
              config.DATA_FEATURES, config.REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # ---------- Étapes 1 & 2 (peuvent être mutualisées entre fenêtres) ----------
    if cache_merged is None:
        print(f"[w={window_sec}s][1/6] Chargement + resampling + fusion…")
        merged = preprocess.resample_and_merge()
    else:
        merged = cache_merged
    print(f"       → {len(merged):,} échantillons × {merged.shape[1]} capteurs")

    if cache_segmented is None:
        print(f"[w={window_sec}s][2/6] Segmentation en runs…")
        segmented = preprocess.segment_runs(merged)
    else:
        segmented = cache_segmented
    run_durations = preprocess.build_run_duration_map(segmented)
    print(f"       → {len(run_durations)} run(s) détecté(s)")

    # ---------- 3) Fenêtrage ----------
    print(f"[w={window_sec}s][3/6] Fenêtrage ({window_sec}s, pas {step_sec}s)…")
    feats = features.windowize(segmented, window_sec=window_sec, step_sec=step_sec)
    print(f"       → {len(feats):,} fenêtres × {feats.shape[1]} colonnes (brutes)")

    # ---------- 4) Cible de forecasting (anti-leakage) ----------
    print(f"[w={window_sec}s][4/6] Cible de stabilité (fenêtre suivante)…")
    df = target.add_forecast_target(feats, window_sec=window_sec, step_sec=step_sec)
    k = df["_shift_k"].iloc[0] if len(df) else None
    print(f"       → shift_k={k} fenêtre(s) (horizon cible = {df['target_horizon_sec'].iloc[0] if len(df) else '?'} s)")

    # ---------- 5) Tag bad_run + drop NaN target ----------
    print(f"[w={window_sec}s][5/6] Tag bad_run + nettoyage…")
    df["run_duration_min"] = df["run_id"].map(run_durations).astype(float)
    df["bad_run"] = (df["run_duration_min"] < config.BAD_RUN_DURATION_MIN).astype(int)

    n_before = len(df)
    df = df.dropna(subset=["is_stable", "stability_score"])
    n_after = len(df)
    print(f"       → {n_before - n_after} fenêtres sans cible supprimées (fin de run)")
    print(f"       → bad_run=1 : {(df['bad_run'] == 1).sum()} fenêtres ({'%.1f' % (100*(df['bad_run']==1).mean())}%)")

    # Conversion finale cibles en int/float
    df["is_stable"] = df["is_stable"].astype(int)
    df["stability_score"] = df["stability_score"].astype(float)

    # Nettoyage colonnes techniques (prefix _ = interne)
    internal = [c for c in df.columns if c.startswith("_")]
    df = df.drop(columns=internal)

    # ---------- 6) Sauvegarde ----------
    if save:
        out = config.DATA_FEATURES / f"dataset_ml_{suffix}.csv"
        df.to_csv(out, index=False)
        meta = {
            "window_sec": window_sec,
            "step_sec": step_sec,
            "shift_k_to_target": int(k) if k is not None else None,
            "target_horizon_sec": int(df["target_horizon_sec"].iloc[0]) if len(df) else None,
            "n_rows_total": len(df),
            "n_rows_good_runs": int((df["bad_run"] == 0).sum()),
            "n_rows_bad_runs": int((df["bad_run"] == 1).sum()),
            "n_features_raw": df.shape[1],
            "class_balance": {
                "is_stable=1": int((df["is_stable"] == 1).sum()),
                "is_stable=0": int((df["is_stable"] == 0).sum()),
            },
            "thresholds": {
                "stability_std_max_C": config.STABILITY_STD_MAX_C,
                "stability_slope_max_Cps": config.STABILITY_SLOPE_MAX,
                "stability_score_threshold": config.STABILITY_SCORE_THRESHOLD,
                "die_production_threshold_C": config.DIE_PRODUCTION_THRESHOLD_C,
                "bad_run_duration_min": config.BAD_RUN_DURATION_MIN,
            },
        }
        (config.DATA_FEATURES / f"dataset_ml_{suffix}_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[w={window_sec}s][6/6] → {out.name}")

    print(f"[w={window_sec}s] terminé en {time.time() - t0:.1f}s.\n")

    return {
        "window_sec": window_sec,
        "step_sec": step_sec,
        "n_rows": len(df),
        "n_rows_good": int((df["bad_run"] == 0).sum()),
        "n_rows_bad":  int((df["bad_run"] == 1).sum()),
        "n_features": df.shape[1],
        "pct_stable": float(100 * df["is_stable"].mean()),
        "dataset": df,
        "merged": merged,
        "segmented": segmented,
    }


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=config.WINDOW_SEC,
                    help="Taille de fenêtre en secondes (défaut: 60)")
    ap.add_argument("--step", type=int, default=None,
                    help="Pas entre fenêtres en secondes (défaut: window/2)")
    return ap.parse_args()


def main():
    args = parse_args()
    build_dataset(window_sec=args.window, step_sec=args.step)


if __name__ == "__main__":
    main()
