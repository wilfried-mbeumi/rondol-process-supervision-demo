"""
preprocess.py — Étapes 1 à 4 du pipeline.

1) Chargement de chaque CSV capteur
2) Parsing du timestamp JavaScript (`Tue Apr 07 2026 17:09:23 GMT+0000 …`)
3) Resampling à pas fixe + fusion des 12 capteurs sur une timeline commune
4) Segmentation en "runs" (essais) via la température de la filière
"""

from __future__ import annotations

import re
import pandas as pd

from . import config


# Format du timestamp généré par JavaScript `Date.toString()`.
# On retire avant parsing la partie " (Greenwich Mean Time)" qui gêne strptime.
_JS_DATE_FMT = "%a %b %d %Y %H:%M:%S GMT%z"
_TZ_SUFFIX_RE = re.compile(r"\s*\(.*\)\s*$")


def load_sensor(name: str) -> pd.DataFrame:
    """Charge un capteur et renvoie un DataFrame [timestamp, <name>].

    - Timestamp converti en datetime UTC
    - Valeurs dédupliquées (en cas de même instant enregistré deux fois)
    - Tri chronologique
    """
    fpath = config.DATA_RAW / config.SENSOR_FILES[name]
    df = pd.read_csv(fpath)

    ts_clean = df["Timestamp"].str.replace(_TZ_SUFFIX_RE, "", regex=True)
    df["timestamp"] = pd.to_datetime(
        ts_clean, format=_JS_DATE_FMT, utc=True, errors="coerce"
    )

    # On ne garde que les lignes au timestamp parsable
    df = df.dropna(subset=["timestamp"])

    # On renomme la colonne "Value" par le nom du capteur
    df = df[["timestamp", "Value"]].rename(columns={"Value": name})

    # Tri + déduplication
    df = (
        df.sort_values("timestamp")
          .drop_duplicates("timestamp", keep="last")
          .reset_index(drop=True)
    )
    return df


def resample_and_merge() -> pd.DataFrame:
    """Charge tous les capteurs, les resample et les fusionne.

    Retourne un DataFrame indexé par timestamp, avec une colonne par capteur.
    """
    frames = []
    for name in config.SENSORS:
        df = load_sensor(name).set_index("timestamp")

        # Resampling : on prend la dernière valeur dans chaque bin de 10 s.
        # Puis forward-fill dans la limite fixée (évite de propager une vieille
        # valeur sur plus d'une minute si le capteur est tombé en panne).
        df_rs = (
            df.resample(config.RESAMPLE_PERIOD)
              .last()
              .ffill(limit=config.FFILL_LIMIT)
        )
        frames.append(df_rs)

    merged = pd.concat(frames, axis=1)
    merged = merged.sort_index()
    return merged


def segment_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Identifie les runs (essais) et attribue un `run_id` à chaque ligne.

    Règle : on considère que la machine est en production dès que la
    filière (DIE) dépasse `DIE_PRODUCTION_THRESHOLD_C`. À chaque transition
    "hors production → production" on ouvre un nouveau run.

    IMPORTANT : les runs courts ne sont PAS supprimés. Ils sont conservés
    avec leur `run_id` et pourront être marqués `bad_run` en aval.
    """
    die = df[config.DIE_SENSOR]
    is_on = die > config.DIE_PRODUCTION_THRESHOLD_C

    # Transition off→on : indique le début d'un nouveau run
    starts = is_on & (~is_on.shift(fill_value=False))
    run_id = starts.cumsum().where(is_on, 0).astype(int)

    df = df.copy()
    df["run_id"] = run_id
    return df


def build_run_duration_map(df: pd.DataFrame) -> dict:
    """Retourne un dict {run_id: duration_min} pour chaque run > 0."""
    durations = {}
    for rid, g in df[df["run_id"] > 0].groupby("run_id"):
        durations[int(rid)] = (g.index.max() - g.index.min()).total_seconds() / 60
    return durations


def summarize_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Renvoie un tableau récapitulatif des runs détectés."""
    runs = []
    for rid, g in df[df["run_id"] > 0].groupby("run_id"):
        runs.append({
            "run_id": rid,
            "start": g.index.min(),
            "end": g.index.max(),
            "duration_min": round(
                (g.index.max() - g.index.min()).total_seconds() / 60, 1
            ),
            "n_samples": len(g),
            "DIE_mean_C": round(g[config.DIE_SENSOR].mean(), 1),
            "DIE_std_C":  round(g[config.DIE_SENSOR].std(), 2),
        })
    return pd.DataFrame(runs)
