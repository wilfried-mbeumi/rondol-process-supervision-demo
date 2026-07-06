"""
target.py — Construction de la variable cible SANS data leakage.

=======================
PROBLÈME DE DATA LEAKAGE
=======================
La cible est dérivée de la STABILITÉ THERMIQUE. Celle-ci dépend de σ (écart-
type) et de la pente β de chaque capteur. Or σ et β sont AUSSI présents
dans les features. Si l'on apprenait à prédire la cible à partir des
features DE LA MÊME FENÊTRE, le modèle aurait accès à sa propre réponse
→ fuite directe, F1 proche de 1, mais ZÉRO utilité prédictive.

Solution adoptée : FORECASTING
==============================
On décale la cible d'une fenêtre vers le futur.
  features_i ← statistiques de la fenêtre i      (temps [t_i, t_i+W))
  target_i   ← stabilité de la fenêtre i+k       (temps [t_i+W, t_i+2W))

Avec k = ceil(W / step) pour garantir que la fenêtre-cible ne chevauche
PAS la fenêtre-features. Le modèle apprend donc à répondre :
  « Au vu de l'état thermique actuel, le régime va-t-il rester stable
    dans la PROCHAINE fenêtre du même run ? »

Cette formulation est :
- sans leakage direct (features et target = intervalles disjoints)
- métier-cohérente (alerte anticipée pour l'opérateur)
- auto-corrélée (σ_i est corrélé à σ_{i+1}) mais c'est un signal légitime

=======================
JUSTIFICATION MÉTIER
=======================
En TSE (Twin-Screw Extrusion) dry/semi-dry pour SSB :
- la dispersion thermique = dispersion rhéologique = dispersion qualité
- une variance σ > 1,5 °C sur les zones régulées = dérive du chauffage ou
  perturbation d'entrée (débit instable, matière inhomogène, usure vis)
- une dérive |β| > 0,05 °C/s (3 °C/min) = rampe, pas un régime établi
La stabilité thermique est donc un proxy légitime de la qualité procédé,
en attendant l'instrumentation de la qualité produit (épaisseur, porosité).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config


# ----------------------------------------------------------------------
# Scoring élémentaire (par capteur, sur 1 fenêtre)
# ----------------------------------------------------------------------
def _score_std(std_value: float,
               std_max: float = config.STABILITY_STD_MAX_C) -> float:
    """0-100 : 100 si σ=0, 0 si σ ≥ std_max (linéaire)."""
    if pd.isna(std_value):
        return np.nan
    return float(max(0.0, min(1.0, 1.0 - std_value / std_max)) * 100.0)


def _score_slope(slope_value: float,
                 slope_max: float = config.STABILITY_SLOPE_MAX) -> float:
    """0-100 : 100 si |β|=0, 0 si |β| ≥ slope_max (linéaire)."""
    if pd.isna(slope_value):
        return np.nan
    return float(max(0.0, min(1.0, 1.0 - abs(slope_value) / slope_max)) * 100.0)


# ----------------------------------------------------------------------
# Étape 1 : score "actuel" (sur la fenêtre elle-même)
# Il sert uniquement à être DÉCALÉ ensuite. Ne pas utiliser en ML direct.
# ----------------------------------------------------------------------
def _compute_current_stability(features_df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le score de stabilité sur CHAQUE fenêtre (sera décalé après).

    NE PAS utiliser ces colonnes comme cible ML telle quelle → leakage.
    """
    df = features_df.copy()
    per_sensor = []
    for sensor in config.SENSORS:
        std_col = f"{sensor}_std"
        slope_col = f"{sensor}_slope"
        if std_col not in df.columns or slope_col not in df.columns:
            continue
        s_std = df[std_col].apply(_score_std)
        s_slope = df[slope_col].apply(_score_slope)
        sensor_score = (s_std + s_slope) / 2.0
        per_sensor.append(sensor_score.rename(sensor))

    scores_df = pd.concat(per_sensor, axis=1)
    df["_stab_score_current"] = scores_df.mean(axis=1)
    df["_is_stable_current"] = (
        df["_stab_score_current"] >= config.STABILITY_SCORE_THRESHOLD
    ).astype("Int64")
    return df


# ----------------------------------------------------------------------
# Étape 2 : décalage temporel → cible = fenêtre suivante
# ----------------------------------------------------------------------
def _compute_shift_k(window_sec: int, step_sec: int) -> int:
    """Nombre de fenêtres à décaler pour que la cible ne chevauche pas."""
    return max(1, math.ceil(window_sec / step_sec))


def add_forecast_target(features_df: pd.DataFrame,
                        window_sec: int,
                        step_sec: int) -> pd.DataFrame:
    """Ajoute `stability_score` et `is_stable` (cible = fenêtre future).

    Les features de la ligne i restent celles de la fenêtre i ;
    la cible de la ligne i est la stabilité de la fenêtre i+k (dans le
    même run), de sorte que les deux intervalles temporels ne se
    chevauchent pas.

    Les lignes en fin de run qui n'ont pas de successeur (→ NaN target)
    sont CONSERVÉES avec NaN : on les supprimera dans build_dataset.
    """
    df = _compute_current_stability(features_df)

    # Tri chrono par run pour que shift() soit correct
    df = df.sort_values(["run_id", "window_start"]).reset_index(drop=True)

    k = _compute_shift_k(window_sec, step_sec)
    df["_shift_k"] = k

    # Décalage intra-run uniquement
    grp = df.groupby("run_id", group_keys=False)
    df["stability_score"] = grp["_stab_score_current"].shift(-k)
    df["is_stable"] = grp["_is_stable_current"].shift(-k)

    # Info : horizon temporel couvert par la cible (exprimé en secondes)
    df["target_horizon_sec"] = k * step_sec

    # Conversion is_stable en Int64 (nullable) pour conserver les NaN
    df["is_stable"] = df["is_stable"].astype("Int64")

    return df
