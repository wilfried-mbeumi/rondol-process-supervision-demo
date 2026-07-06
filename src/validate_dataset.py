"""
validate_dataset.py — Rapport de validation AVANT passage au ML.

Vérifie :
  1. Taille du dataset et présence de la cible
  2. Distribution de la cible binaire (biais de classe)
  3. Distribution du score continu
  4. Répartition par run + bad_run
  5. Taux de NaN / duplicats
  6. DATA LEAKAGE : corrélation entre chaque feature et la cible
     → signale les features trop fortement corrélées (>= 0.95)

Exécution :
  python -m src.validate_dataset
  python -m src.validate_dataset --window 60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# Colonnes non-features à exclure de l'analyse de corrélation
NON_FEATURES = {
    "run_id", "window_start", "window_end", "n_samples",
    "run_duration_min", "bad_run", "target_horizon_sec",
    "stability_score", "is_stable",
}


def load_dataset(window_sec: int) -> pd.DataFrame:
    path = config.DATA_FEATURES / f"dataset_ml_w{window_sec}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} introuvable — lancer d'abord `python -m src.build_dataset --window {window_sec}`."
        )
    df = pd.read_csv(path, parse_dates=["window_start", "window_end"])
    return df


def section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def report_size(df: pd.DataFrame):
    section("1) TAILLE ET STRUCTURE")
    print(f"Lignes (fenêtres)       : {len(df):,}")
    print(f"Colonnes totales        : {df.shape[1]}")
    n_feat = len([c for c in df.columns if c not in NON_FEATURES])
    print(f"Features prédictives    : {n_feat}")
    print(f"Cibles                  : stability_score (continue), is_stable (0/1)")
    print(f"Runs distincts          : {df['run_id'].nunique()}")
    print(f"bad_run=1 (short runs)  : {(df['bad_run'] == 1).sum()}  "
          f"({100 * (df['bad_run'] == 1).mean():.1f}%)")


def _print_class_counts(s: pd.Series):
    counts = s.value_counts().sort_index()
    shares = (100 * s.value_counts(normalize=True)).sort_index()
    for k in counts.index:
        label = "stable" if int(k) == 1 else "instable"
        print(f"    {label:9s} : {int(counts[k]):6d}  ({shares[k]:5.1f} %)")


def report_target(df: pd.DataFrame):
    section("2) DISTRIBUTION DE LA CIBLE")
    good = df[df["bad_run"] == 0]
    print("— is_stable (tout dataset) :")
    _print_class_counts(df["is_stable"])
    print("— is_stable (runs OK uniquement) :")
    _print_class_counts(good["is_stable"])

    print("\n— stability_score (runs OK uniquement) :")
    print(good["stability_score"].describe().round(1).to_string())

    # Diagnostic biais
    counts_good = good["is_stable"].value_counts()
    minority = counts_good.min() / counts_good.sum()
    print(f"\nClasse minoritaire (runs OK) : {100 * minority:.1f} %")
    if minority >= 0.3:
        print("→ Équilibre correct (≥ 30 %). Pas de rééquilibrage nécessaire.")
    elif minority >= 0.15:
        print("→ Déséquilibre modéré. Stratified split suffisant, class_weight='balanced' conseillé.")
    else:
        print("→ Déséquilibre fort (< 15 %). SMOTE ou class_weight ou seuil à revoir.")


def report_per_run(df: pd.DataFrame):
    section("3) RÉPARTITION PAR RUN")
    stats = (
        df.groupby("run_id")
          .agg(n=("is_stable", "size"),
               n_stable=("is_stable", "sum"),
               mean_score=("stability_score", "mean"),
               bad_run=("bad_run", "max"),
               duration_min=("run_duration_min", "first"))
          .assign(pct_stable=lambda x: (100 * x["n_stable"] / x["n"]).round(1))
          .round(1)
    )
    print(stats.to_string())


def report_missing(df: pd.DataFrame):
    section("4) QUALITÉ — NaN & duplicats")
    n_dup = df.duplicated(subset=["run_id", "window_start"]).sum()
    print(f"Duplicats (run_id + window_start) : {n_dup}")
    na = df.isna().sum()
    na = na[na > 0]
    if na.empty:
        print("Aucune valeur manquante dans le dataset.")
    else:
        print("Valeurs manquantes :")
        print(na.to_string())


def report_leakage(df: pd.DataFrame, threshold: float = 0.95):
    section("5) CHECK DATA LEAKAGE — corr(features, is_stable)")
    # On travaille sur les runs OK pour être représentatif
    df_ = df[df["bad_run"] == 0].copy()
    feature_cols = [c for c in df_.columns
                    if c not in NON_FEATURES
                    and pd.api.types.is_numeric_dtype(df_[c])]
    target = df_["is_stable"].astype(float)

    corrs = {}
    for c in feature_cols:
        try:
            corr = df_[c].corr(target)
        except Exception:
            corr = np.nan
        corrs[c] = corr
    s = pd.Series(corrs).dropna().abs().sort_values(ascending=False)

    print(f"Top 10 features les plus corrélées avec is_stable (|pearson|) :")
    print(s.head(10).round(3).to_string())

    leaky = s[s >= threshold]
    if leaky.empty:
        print(f"\n✓ Aucune feature au-dessus du seuil de leakage {threshold:.2f}. "
              f"Pas de fuite directe détectée.")
    else:
        print(f"\n⚠ {len(leaky)} feature(s) avec |corr| ≥ {threshold} → "
              f"à investiguer :")
        print(leaky.round(3).to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=config.WINDOW_SEC)
    args = ap.parse_args()

    df = load_dataset(args.window)
    print(f"\nDataset : dataset_ml_w{args.window}.csv  —  {len(df)} lignes × {df.shape[1]} colonnes")

    report_size(df)
    report_target(df)
    report_per_run(df)
    report_missing(df)
    report_leakage(df)

    print("\n" + "=" * 70)
    print("Validation terminée.")
    print("=" * 70)


if __name__ == "__main__":
    main()
