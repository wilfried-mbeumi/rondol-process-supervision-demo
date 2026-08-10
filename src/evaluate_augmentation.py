"""
evaluate_augmentation.py — L'augmentation aide-t-elle VRAIMENT ? (test honnête)

Protocole anti-triche : validation LeaveOneGroupOut sur les ESSAIS RÉELS.
Pour chaque essai réel r laissé de côté (test) :
  - baseline  : entraîne sur les AUTRES essais réels ;
  - augmenté  : entraîne sur les autres essais réels + TOUT le synthétique.
Le test est TOUJOURS un essai réel non vu. Le synthétique n'est JAMAIS en test.

Sortie : reports/augmentation_eval.json  (+ tableau imprimé)
Usage   : python -m src.evaluate_augmentation

AVERTISSEMENT — protocole superseded (juillet 2026)
---------------------------------------------------
Le protocole implémenté ici comporte une FUITE PAR ANCRAGE. Le pool synthétique
lu depuis dataset_ml_w60_augmented.csv a été généré une seule fois à partir des
HUIT essais réels ; l'injecter dans chaque fold d'entraînement fait entrer dans
l'entraînement des fenêtres ancrées sur l'essai de test, et des écarts-types de
classe calculés en partie sur lui. Les chiffres de reports/augmentation_eval.json
(notamment RandomForest 0,918) sont donc optimistes.

Ce module est conservé INCHANGÉ comme trace d'audit des valeurs historiquement
publiées. Le protocole de référence est désormais la condition `fold_aware` de
scripts/thesis_results/block2_model_augmentation.py, qui régénère le pool à
chaque fold à partir des seuls essais d'entraînement. Voir
reports/AI_thesis_results/block_2_model_augmentation/methodological_checks.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import config

META = {"run_id", "window_start", "window_end", "n_samples", "stability_score",
        "is_stable", "target_horizon_sec", "run_duration_min", "bad_run", "synthetic"}


def _pipe(clf):
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()), ("clf", clf)])


def _models():
    return {
        "LogisticRegression": lambda: _pipe(LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=42)),
        "SVM_RBF": lambda: _pipe(SVC(kernel="rbf", gamma="scale",
            class_weight="balanced", random_state=42)),
        "RandomForest": lambda: _pipe(RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            n_jobs=-1, random_state=42)),
    }


def main() -> int:
    df = pd.read_csv(config.DATA_FEATURES / "dataset_ml_w60_augmented.csv")
    feats = [c for c in df.columns if c not in META]
    real = df[df["synthetic"] == 0]
    syn = df[df["synthetic"] == 1]
    real_runs = sorted(real["run_id"].unique())
    print(f"Réel : {len(real)} fenêtres / {len(real_runs)} essais · "
          f"Synthétique : {len(syn)} fenêtres (jamais en test)\n")

    results = {}
    for name, make in _models().items():
        base_f1, aug_f1 = [], []
        for r in real_runs:
            te = real[real["run_id"] == r]
            tr_real = real[real["run_id"] != r]
            if te["is_stable"].nunique() < 2:
                continue
            # baseline
            m = make(); m.fit(tr_real[feats], tr_real["is_stable"])
            base_f1.append(f1_score(te["is_stable"], m.predict(te[feats]), average="macro"))
            # augmenté (réel autres essais + tout le synthétique)
            tr_aug = pd.concat([tr_real, syn], ignore_index=True)
            m2 = make(); m2.fit(tr_aug[feats], tr_aug["is_stable"])
            aug_f1.append(f1_score(te["is_stable"], m2.predict(te[feats]), average="macro"))
        results[name] = {
            "baseline_f1_macro_mean": round(float(np.mean(base_f1)), 3),
            "baseline_f1_macro_std": round(float(np.std(base_f1)), 3),
            "augmented_f1_macro_mean": round(float(np.mean(aug_f1)), 3),
            "augmented_f1_macro_std": round(float(np.std(aug_f1)), 3),
            "delta": round(float(np.mean(aug_f1) - np.mean(base_f1)), 3),
            "n_folds": len(base_f1),
        }
        r = results[name]
        print(f"{name:18} baseline={r['baseline_f1_macro_mean']:.3f}±{r['baseline_f1_macro_std']:.3f}"
              f"  →  augmenté={r['augmented_f1_macro_mean']:.3f}±{r['augmented_f1_macro_std']:.3f}"
              f"  (Δ={r['delta']:+.3f})")

    out = {"validation": "LeaveOneGroupOut sur essais RÉELS ; synthétique en TRAIN uniquement",
           "n_real": int(len(real)), "n_synthetic": int(len(syn)),
           "n_real_runs": len(real_runs), "models": results}
    (config.REPORTS_DIR / "augmentation_eval.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n[OK] écrit reports/augmentation_eval.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
