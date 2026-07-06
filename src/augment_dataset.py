"""
augment_dataset.py — Génération d'un dataset SIMULÉ inspiré de l'échantillon réel.

Contexte : Rondol ne dispose pas d'une base de données ; l'échantillon d'essais
réels est insuffisant (8 essais, 627 fenêtres valides). Ce module GÉNÈRE des
fenêtres synthétiques À PARTIR de l'échantillon réel — surtout PAS aléatoirement.

Principe (plan documenté dans reports/augmentation_plan.md) :
  1. Estimation par CLASSE (is_stable 0/1) des distributions des statistiques
     réelles, par capteur.
  2. Génération par ANCRAGE : chaque fenêtre synthétique part d'une vraie fenêtre
     de la même classe (bootstrap → conserve les corrélations inter-capteurs),
     puis reçoit un JITTER gaussien BORNÉ (fraction de l'écart-type réel de classe).
  3. Cohérence interne EXACTE reproduite : range = max − min ;
     gradients croisés = différences de moyennes (cf. src/features.py).
  4. Contraintes métier : températures bornées, std/iqr/range ≥ 0.
  5. Reproduction des IMPERFECTIONS de l'échantillon : blackout capteur (7 stats
     NaN ensemble) au taux réel par capteur ; quelques aberrations thermocouple.
  6. Marquage `synthetic=1`, graine fixée, essais synthétiques dans un pool de
     run_id distinct → JAMAIS mélangés aux essais réels en évaluation.

Sortie : data/features/dataset_ml_w60_augmented.csv (réel synthetic=0 + généré=1)
         reports/augmentation_report.json

Usage : python -m src.augment_dataset --n-per-class 400 --seed 42
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import config

SENSORS = config.SENSORS
STATS = ["mean", "std", "min", "max", "range", "slope", "iqr"]
PRIMARY = ["mean", "std", "slope", "iqr"]  # tirés ; min/max/range dérivés
META = {"run_id", "window_start", "window_end", "n_samples", "stability_score",
        "is_stable", "target_horizon_sec", "run_duration_min", "bad_run"}
TEMP_MIN, TEMP_MAX = 10.0, 300.0           # bornes métier (hors aberration)
JITTER = 0.30                              # fraction de l'écart-type de classe
OUTLIER_RATE = 0.003                       # aberrations thermocouple (rares)


def _score_std(x):
    if pd.isna(x):
        return np.nan
    return max(0.0, min(1.0, 1.0 - x / config.STABILITY_STD_MAX_C)) * 100.0


def _score_slope(x):
    if pd.isna(x):
        return np.nan
    return max(0.0, min(1.0, 1.0 - abs(x) / config.STABILITY_SLOPE_MAX)) * 100.0


def _stability_score(row) -> float:
    per = []
    for s in SENSORS:
        st, sl = row.get(f"{s}_std"), row.get(f"{s}_slope")
        if not pd.isna(st) and not pd.isna(sl):
            per.append((_score_std(st) + _score_slope(sl)) / 2.0)
    return float(np.mean(per)) if per else np.nan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-class", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--window", type=int, default=60)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    src = pd.read_csv(config.DATA_FEATURES / f"dataset_ml_w{args.window}.csv")
    real = src[(src["bad_run"] == 0) & src["is_stable"].isin([0, 1])].reset_index(drop=True)

    # Taux de NaN réel par capteur (mécanisme d'imperfection à reproduire)
    nan_rate = {s: float(real[f"{s}_mean"].isna().mean()) for s in SENSORS}
    # Écart-type de classe par (capteur, stat primaire) — amplitude du jitter
    sigma = {}
    for c in (0, 1):
        sub = real[real["is_stable"] == c]
        for s in SENSORS:
            for st in PRIMARY:
                sigma[(c, s, st)] = float(sub[f"{s}_{st}"].std(ddof=0) or 0.0)

    anchors = {c: real[real["is_stable"] == c].reset_index(drop=True) for c in (0, 1)}
    rows = []
    for c in (0, 1):
        for k in range(args.n_per_class):
            a = anchors[c].iloc[rng.integers(len(anchors[c]))]
            row = {}
            for s in SENSORS:
                # blackout capteur au taux réel (7 stats NaN ensemble)
                if rng.random() < nan_rate[s]:
                    for st in STATS:
                        row[f"{s}_{st}"] = np.nan
                    continue
                mean0, std0 = a[f"{s}_mean"], a[f"{s}_std"]
                min0, max0 = a[f"{s}_min"], a[f"{s}_max"]
                slope0, iqr0 = a[f"{s}_slope"], a[f"{s}_iqr"]
                if pd.isna(mean0):  # ancre elle-même en blackout → propager
                    for st in STATS:
                        row[f"{s}_{st}"] = np.nan
                    continue
                mean = mean0 + rng.normal(0, JITTER * sigma[(c, s, "mean")])
                mean = float(np.clip(mean, TEMP_MIN, TEMP_MAX))
                std = abs(std0 + rng.normal(0, JITTER * sigma[(c, s, "std")]))
                slope = (slope0 if pd.isna(slope0) else
                         slope0 + rng.normal(0, JITTER * sigma[(c, s, "slope")]))
                iqr = abs((iqr0 if not pd.isna(iqr0) else 0.0)
                          + rng.normal(0, JITTER * sigma[(c, s, "iqr")]))
                # min/max suivent le décalage de mean (conserve la forme d'étalement)
                off_min = (min0 - mean0) if not pd.isna(min0) else -std
                off_max = (max0 - mean0) if not pd.isna(max0) else std
                mn, mx = mean + off_min, mean + off_max
                # aberration thermocouple rare (à nettoyer plus tard)
                if rng.random() < OUTLIER_RATE:
                    mx = float(rng.uniform(400, 3300))
                mn, mx = min(mn, mean), max(mx, mean)  # garantit min≤mean≤max
                row.update({f"{s}_mean": mean, f"{s}_std": std, f"{s}_min": mn,
                            f"{s}_max": mx, f"{s}_range": mx - mn,
                            f"{s}_slope": slope, f"{s}_iqr": iqr})
            # gradients croisés = différences de moyennes (def. exacte features.py)
            def g(a_, b_):
                va, vb = row.get(f"{a_}_mean"), row.get(f"{b_}_mean")
                return (va - vb) if (not pd.isna(va) and not pd.isna(vb)) else np.nan
            row["grad_Z8_minus_Z1"] = g("Z8", "Z1")
            row["grad_DIE_minus_Z8"] = g("DIE", "Z8")
            row["grad_CastFilm_minus_DIE"] = g("CastFilmBody", "DIE")
            # méta
            row["run_id"] = 900 + (k % 10)          # pool synthétique distinct
            row["is_stable"] = c
            row["stability_score"] = _stability_score(row)
            row["target_horizon_sec"] = int(real["target_horizon_sec"].iloc[0])
            row["run_duration_min"] = 60.0
            row["bad_run"] = 0
            row["n_samples"] = int(real["n_samples"].median())
            row["synthetic"] = 1
            rows.append(row)

    syn = pd.DataFrame(rows)
    real2 = real.copy()
    real2["synthetic"] = 0
    out = pd.concat([real2, syn], ignore_index=True, sort=False)
    out_path = config.DATA_FEATURES / f"dataset_ml_w{args.window}_augmented.csv"
    out.to_csv(out_path, index=False)

    report = {
        "window_sec": args.window, "seed": args.seed,
        "n_real": int(len(real)), "n_synthetic": int(len(syn)),
        "n_total": int(len(out)),
        "class_real": real["is_stable"].value_counts().to_dict(),
        "class_synthetic": syn["is_stable"].value_counts().to_dict(),
        "nan_rate_reproduced_per_sensor": {k: round(v, 4) for k, v in nan_rate.items()},
        "synthetic_nan_total": int(syn[[f"{s}_mean" for s in SENSORS]].isna().sum().sum()),
        "jitter_fraction": JITTER, "outlier_rate": OUTLIER_RATE,
        "eval_guardrail": "synthetic run_id in 900..909 — JAMAIS en test ; évaluation sur essais réels uniquement",
    }
    (config.REPORTS_DIR / "augmentation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n[OK] écrit {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
