"""
features.py — Étape 5 : extraction de features par fenêtre glissante.

Chaque fenêtre (60 s) devient une ligne du dataset ML.
Pour chaque capteur on extrait 7 features :
  - mean, std, min, max, range (stabilité locale)
  - slope (dérive temporelle via régression linéaire sur t)
  - iqr (écart interquartile : robustesse aux outliers)
Features cross-capteurs :
  - gradient longitudinal Z8 − Z1 (gradient du fourreau)
  - saut DIE − Z8 (saut thermique filière)
  - saut CastFilmBody − DIE (cohérence filière / casting)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config


def _window_features_one_sensor(series: pd.Series, prefix: str) -> dict:
    """Features pour une série 1D (1 capteur, 1 fenêtre)."""
    s = series.dropna()
    if len(s) < 3:
        # Fenêtre trop courte : on renvoie des NaN pour toutes les features
        keys = ["mean", "std", "min", "max", "range", "slope", "iqr"]
        return {f"{prefix}_{k}": np.nan for k in keys}

    # Statistiques classiques
    mean_ = float(s.mean())
    std_ = float(s.std(ddof=0))
    min_ = float(s.min())
    max_ = float(s.max())
    q1, q3 = s.quantile([0.25, 0.75])

    # Pente temporelle : régression linéaire sur t (secondes) vs valeur
    t_sec = (s.index - s.index[0]).total_seconds().to_numpy()
    try:
        lr = stats.linregress(t_sec, s.to_numpy())
        slope = float(lr.slope)
    except ValueError:
        slope = np.nan

    return {
        f"{prefix}_mean":  mean_,
        f"{prefix}_std":   std_,
        f"{prefix}_min":   min_,
        f"{prefix}_max":   max_,
        f"{prefix}_range": max_ - min_,
        f"{prefix}_slope": slope,
        f"{prefix}_iqr":   float(q3 - q1),
    }


def _extract_window_features(window: pd.DataFrame) -> dict:
    """Pour une fenêtre multi-capteurs → dictionnaire de features."""
    feats: dict = {}
    for sensor in config.SENSORS:
        if sensor in window.columns:
            feats.update(_window_features_one_sensor(window[sensor], sensor))

    # Cross-capteurs : gradients spatiaux (moyens) — indicateurs métier
    if not np.isnan(feats.get("Z8_mean", np.nan)) and not np.isnan(feats.get("Z1_mean", np.nan)):
        feats["grad_Z8_minus_Z1"] = feats["Z8_mean"] - feats["Z1_mean"]
    else:
        feats["grad_Z8_minus_Z1"] = np.nan

    if not np.isnan(feats.get("DIE_mean", np.nan)) and not np.isnan(feats.get("Z8_mean", np.nan)):
        feats["grad_DIE_minus_Z8"] = feats["DIE_mean"] - feats["Z8_mean"]
    else:
        feats["grad_DIE_minus_Z8"] = np.nan

    if not np.isnan(feats.get("CastFilmBody_mean", np.nan)) and not np.isnan(feats.get("DIE_mean", np.nan)):
        feats["grad_CastFilm_minus_DIE"] = feats["CastFilmBody_mean"] - feats["DIE_mean"]
    else:
        feats["grad_CastFilm_minus_DIE"] = np.nan

    return feats


def windowize(df_segmented: pd.DataFrame,
              window_sec: int | None = None,
              step_sec: int | None = None) -> pd.DataFrame:
    """Applique l'extraction de features sur toutes les fenêtres de tous les runs.

    - Ne traite que les runs productifs (run_id > 0)
    - Fenêtres glissantes paramétrables (défaut : `config.WINDOW_SEC` / `STEP_SEC`)
    """
    if window_sec is None:
        window_sec = config.WINDOW_SEC
    if step_sec is None:
        step_sec = config.STEP_SEC
    window = pd.Timedelta(seconds=window_sec)
    step = pd.Timedelta(seconds=step_sec)

    records = []
    for run_id, g in df_segmented[df_segmented["run_id"] > 0].groupby("run_id"):
        g = g.sort_index()
        # Colonnes utiles uniquement
        cols = [c for c in config.SENSORS if c in g.columns]
        gg = g[cols]

        t_start = gg.index[0]
        t_end = gg.index[-1]
        t = t_start
        while t + window <= t_end:
            sub = gg.loc[t : t + window]
            if len(sub) >= 3:
                feats = _extract_window_features(sub)
                feats["run_id"] = int(run_id)
                feats["window_start"] = t
                feats["window_end"] = t + window
                feats["n_samples"] = len(sub)
                records.append(feats)
            t += step

    return pd.DataFrame(records)
