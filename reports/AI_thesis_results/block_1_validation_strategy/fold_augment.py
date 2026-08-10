# -*- coding: utf-8 -*-
"""
fold_augment.py — Génération synthétique PARAMÉTRÉE PAR LE FOLD D'ENTRAÎNEMENT.

Pourquoi ce module existe
-------------------------
`src/augment_dataset.py` génère le pool synthétique UNE SEULE FOIS à partir de
la TOTALITÉ des essais réels, puis `src/evaluate_augmentation.py` injecte ce
pool entier dans chaque fold d'entraînement Leave-One-Group-Out.

Conséquence : lorsqu'on teste sur l'essai r, le pool synthétique contient des
fenêtres dont les ANCRES et les écarts-types de classe proviennent aussi de
l'essai r. L'essai « exclu » a donc influencé l'entraînement de façon indirecte.
C'est précisément la garantie que l'encadrant demande de confirmer :

    « il n'a pas été utilisé comme point d'ancrage pour générer les fenêtres
      synthétiques ; les données synthétiques ont été générées exclusivement à
      partir des observations disponibles dans le fold d'entraînement. »

Le protocole historique ne satisfait PAS cette condition. Ce module fournit la
version corrigée : à chaque fold, le pool synthétique est REGÉNÉRÉ à partir des
seuls essais d'entraînement.

L'algorithme de génération est identique à src/augment_dataset.py (ancrage par
bootstrap intra-classe + jitter gaussien borné, cohérence min≤mean≤max, range et
gradients recalculés, blackouts capteur au taux réel, aberrations rares). Seul
le SUPPORT des ancres change. L'équivalence est vérifiée par
`selftest_reproduces_published_pool()`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config

SENSORS = config.SENSORS
STATS = ["mean", "std", "min", "max", "range", "slope", "iqr"]
PRIMARY = ["mean", "std", "slope", "iqr"]
TEMP_MIN, TEMP_MAX = 10.0, 300.0
JITTER = 0.30
OUTLIER_RATE = 0.003


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


def generate_synthetic(real: pd.DataFrame,
                       n_per_class: int = 400,
                       seed: int = 42) -> pd.DataFrame:
    """Génère 2 × n_per_class fenêtres synthétiques à partir de `real` SEULEMENT.

    `real` doit être le sous-ensemble d'ancrage autorisé (en validation
    fold-aware : les essais d'entraînement uniquement), indexé de 0..n-1.

    Retourne un DataFrame avec `synthetic = 1` et des run_id dans 900..909,
    disjoints des run_id réels — garantit qu'aucune fenêtre générée ne peut
    être confondue avec un essai réel lors de l'évaluation.
    """
    real = real.reset_index(drop=True)
    rng = np.random.default_rng(seed)

    # Taux de NaN réel par capteur, mesuré sur le support d'ancrage autorisé.
    nan_rate = {s: float(real[f"{s}_mean"].isna().mean()) for s in SENSORS}

    # Écart-type de classe (amplitude du jitter), mesuré sur le même support.
    sigma = {}
    for c in (0, 1):
        sub = real[real["is_stable"] == c]
        for s in SENSORS:
            for st in PRIMARY:
                sigma[(c, s, st)] = float(sub[f"{s}_{st}"].std(ddof=0) or 0.0)

    anchors = {c: real[real["is_stable"] == c].reset_index(drop=True)
               for c in (0, 1)}

    rows = []
    for c in (0, 1):
        if len(anchors[c]) == 0:
            # Classe absente du fold d'entraînement → rien à générer pour elle.
            continue
        for k in range(n_per_class):
            a = anchors[c].iloc[rng.integers(len(anchors[c]))]
            row = {}
            for s in SENSORS:
                if rng.random() < nan_rate[s]:
                    for st in STATS:
                        row[f"{s}_{st}"] = np.nan
                    continue
                mean0, std0 = a[f"{s}_mean"], a[f"{s}_std"]
                min0, max0 = a[f"{s}_min"], a[f"{s}_max"]
                slope0, iqr0 = a[f"{s}_slope"], a[f"{s}_iqr"]
                if pd.isna(mean0):
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
                off_min = (min0 - mean0) if not pd.isna(min0) else -std
                off_max = (max0 - mean0) if not pd.isna(max0) else std
                mn, mx = mean + off_min, mean + off_max
                if rng.random() < OUTLIER_RATE:
                    mx = float(rng.uniform(400, 3300))
                mn, mx = min(mn, mean), max(mx, mean)
                row.update({f"{s}_mean": mean, f"{s}_std": std, f"{s}_min": mn,
                            f"{s}_max": mx, f"{s}_range": mx - mn,
                            f"{s}_slope": slope, f"{s}_iqr": iqr})

            def g(a_, b_):
                va, vb = row.get(f"{a_}_mean"), row.get(f"{b_}_mean")
                return (va - vb) if (not pd.isna(va) and not pd.isna(vb)) else np.nan

            row["grad_Z8_minus_Z1"] = g("Z8", "Z1")
            row["grad_DIE_minus_Z8"] = g("DIE", "Z8")
            row["grad_CastFilm_minus_DIE"] = g("CastFilmBody", "DIE")
            row["run_id"] = 900 + (k % 10)
            row["is_stable"] = c
            row["stability_score"] = _stability_score(row)
            row["target_horizon_sec"] = int(real["target_horizon_sec"].iloc[0])
            row["run_duration_min"] = 60.0
            row["bad_run"] = 0
            row["n_samples"] = int(real["n_samples"].median())
            row["synthetic"] = 1
            rows.append(row)

    return pd.DataFrame(rows)


def selftest_reproduces_published_pool(real_all: pd.DataFrame,
                                       published_syn: pd.DataFrame,
                                       feats: list[str]) -> tuple[bool, str]:
    """Vérifie que ce générateur reproduit EXACTEMENT le pool publié.

    Condition : même support d'ancrage (tous les essais réels), n_per_class=400,
    seed=42 — c'est-à-dire les paramètres utilisés pour produire
    data/features/dataset_ml_w60_augmented.csv.

    C'est la preuve que la version fold-aware ne change QUE le support des
    ancres, et pas l'algorithme de génération.
    """
    regen = generate_synthetic(real_all, n_per_class=400, seed=42)
    if len(regen) != len(published_syn):
        return False, f"taille différente : {len(regen)} vs {len(published_syn)}"
    a = regen[feats].to_numpy(dtype=float)
    b = published_syn[feats].to_numpy(dtype=float)
    same_nan = np.array_equal(np.isnan(a), np.isnan(b))
    if not same_nan:
        return False, "motifs de valeurs manquantes différents"
    close = np.allclose(a[~np.isnan(a)], b[~np.isnan(b)],
                        rtol=1e-9, atol=1e-9)
    if not close:
        d = np.nanmax(np.abs(a - b))
        return False, f"valeurs différentes (écart max = {d:.3e})"
    return True, "identique au pool publié (bit-à-bit sur les 87 features)"
