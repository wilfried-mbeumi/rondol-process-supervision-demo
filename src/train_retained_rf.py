"""
train_retained_rf.py — Entraîne le modèle RETENU (RandomForest) sur réel+synthétique
                       et le sauvegarde pour l'application.

Choix documenté : sous validation honnête (LeaveOneGroupOut sur essais réels),
RandomForest entraîné avec augmentation atteint 0.918 ± 0.054 (meilleur du
championnat, cf. reports/augmentation_eval.json). Il devient le modèle déployé.

Le pipeline inclut un imputer médian : l'application passe des vecteurs de
features pouvant contenir des NaN (blackout capteur), et RandomForest sklearn
refuse les NaN sans imputation.

Sorties : models/RandomForest_w60_augmented.joblib
          reports/feature_importance_RandomForest_w60.csv (importances du modèle déployé)

Usage : python -m src.train_retained_rf
"""
from __future__ import annotations

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from . import config

META = {"run_id", "window_start", "window_end", "n_samples", "stability_score",
        "is_stable", "target_horizon_sec", "run_duration_min", "bad_run", "synthetic"}


def main() -> int:
    df = pd.read_csv(config.DATA_FEATURES / "dataset_ml_w60_augmented.csv")
    df = df[df["is_stable"].isin([0, 1])].reset_index(drop=True)
    feats = [c for c in df.columns if c not in META]
    X, y = df[feats], df["is_stable"].astype(int)

    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            n_jobs=-1, random_state=42)),
    ])
    pipe.fit(X, y)

    out_model = config.PROJECT_ROOT / "models" / "RandomForest_w60_augmented.joblib"
    joblib.dump(pipe, out_model)

    # Importances du modèle déployé
    imp = pipe.named_steps["clf"].feature_importances_
    fi = pd.DataFrame({"feature": feats, "importance": imp}).sort_values(
        "importance", ascending=False)
    fi.to_csv(config.REPORTS_DIR / "feature_importance_RandomForest_w60.csv", index=False)

    print(f"[OK] modèle : {out_model}")
    print(f"     n_features_in_ = {pipe.n_features_in_} | classes = {list(pipe.classes_)}")
    print(f"     entraîné sur {len(df)} fenêtres (réel+synthétique)")
    print("     top 5 features :")
    for _, r in fi.head(5).iterrows():
        print(f"       {r['feature']:24} {r['importance']:.4f}")
    # sanity : predict_proba sur une ligne réelle
    real = df[df["synthetic"] == 0]
    p = pipe.predict_proba(real[feats].iloc[[0]])[0]
    print(f"     predict_proba (1 ligne réelle) = [{p[0]:.3f}, {p[1]:.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
