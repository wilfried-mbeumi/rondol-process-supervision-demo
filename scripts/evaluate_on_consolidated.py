# -*- coding: utf-8 -*-
"""Évaluation externe du modèle retenu sur la base consolidée simulée.

Fait passer data/consolidated/dataset_consolide_rondol.csv dans le MÊME
pipeline que les données réelles (fenêtrage 60 s, features, cible de
stabilité src.target) puis évalue le RandomForest déployé, sans aucun
réentraînement. Rôle : validation externe de la génération simulée
(chapitres Data et ML du mémoire).

Sortie : reports/eval_consolidated_w60.json
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix

from src import config, features, target

ROOT = Path(__file__).resolve().parents[1]
WINDOW = 60


def main() -> None:
    df = pd.read_csv(ROOT / "data/consolidated/dataset_consolide_rondol.csv",
                     parse_dates=["timestamp"])
    # mise au format du pipeline réel : timestamp + capteurs
    sensors = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
               "DIE", "CastFilmBody", "CastFilmP1", "CastFilmP2"]
    ts = df[["timestamp"] + sensors].copy()
    # neutraliser le code d'erreur thermocouple comme le fait le preprocess réel
    for c in sensors:
        ts.loc[ts[c] > 1000, c] = np.nan

    # runs = épisodes d'extrusion de la base consolidée (phase == run)
    run_change = (df["phase"] != df["phase"].shift()).cumsum()
    ts["run_id"] = np.where(df["phase"] == "run", run_change, 0)
    ts = ts[ts["run_id"] > 0]
    # garder les runs assez longs pour produire des fenêtres
    sizes = ts.groupby("run_id").size()
    ts = ts[ts["run_id"].isin(sizes[sizes >= WINDOW // 10 * 3].index)]
    ts = ts.set_index("timestamp")
    print(f"{ts.run_id.nunique()} runs simulés, {len(ts)} lignes")

    feats = features.windowize(ts, window_sec=WINDOW, step_sec=WINDOW // 2)
    df_t = target.add_forecast_target(feats, window_sec=WINDOW, step_sec=WINDOW // 2)
    df_t = df_t.dropna(subset=["is_stable", "stability_score"])
    df_t["is_stable"] = df_t["is_stable"].astype(int)
    print(f"{len(df_t)} fenêtres labellisées | % stable = {100*df_t.is_stable.mean():.1f}")

    model = joblib.load(ROOT / "models/RandomForest_w60_augmented.joblib")
    drop = [c for c in ("is_stable", "stability_score", "run_id", "t_start", "t_end",
                        "window_start", "window_end", "bad_run") if c in df_t.columns]
    X = df_t.drop(columns=drop)
    # aligner sur les features attendues par le modèle
    if hasattr(model, "feature_names_in_"):
        X = X.reindex(columns=list(model.feature_names_in_), fill_value=np.nan)
    y = df_t["is_stable"].to_numpy()

    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    res = {
        "n_windows": int(len(y)),
        "n_runs": int(df_t["run_id"].nunique()) if "run_id" in df_t else None,
        "pct_stable": round(float(100 * y.mean()), 1),
        "accuracy": round(float(accuracy_score(y, pred)), 3),
        "f1_macro": round(float(f1_score(y, pred, average="macro")), 3),
        "roc_auc": round(float(roc_auc_score(y, proba)), 3) if len(set(y)) > 1 else None,
        "confusion_matrix": confusion_matrix(y, pred).tolist(),
        "note": "Validation externe : modèle RandomForest_w60_augmented évalué tel quel "
                "sur la base consolidée simulée (aucun réentraînement).",
    }
    out = ROOT / "reports/eval_consolidated_w60.json"
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
