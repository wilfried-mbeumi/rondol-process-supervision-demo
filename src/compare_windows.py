"""
compare_windows.py — Compare plusieurs tailles de fenêtre (30/60/120 s).

Produit un tableau récapitulatif pour choisir la fenêtre optimale AVANT ML.
Mutualise les étapes 1-2 du pipeline (load+merge+segment = une seule fois).
"""

from __future__ import annotations

import sys

import pandas as pd

from . import config, build_dataset

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    print("=" * 70)
    print("COMPARAISON DE TAILLES DE FENÊTRE")
    print("=" * 70)

    # On exécute une fois les étapes 1-2 et on réutilise
    first = build_dataset.build_dataset(
        window_sec=config.WINDOW_CANDIDATES[0], save=True
    )
    merged_cache = first["merged"]
    segmented_cache = first["segmented"]

    rows = [{
        "window_sec": first["window_sec"],
        "step_sec": first["step_sec"],
        "n_rows": first["n_rows"],
        "n_rows_good": first["n_rows_good"],
        "n_rows_bad": first["n_rows_bad"],
        "n_features": first["n_features"],
        "pct_stable": round(first["pct_stable"], 1),
    }]

    # Autres fenêtres
    for w in config.WINDOW_CANDIDATES[1:]:
        r = build_dataset.build_dataset(
            window_sec=w,
            cache_merged=merged_cache,
            cache_segmented=segmented_cache,
            save=True,
        )
        rows.append({
            "window_sec": r["window_sec"],
            "step_sec": r["step_sec"],
            "n_rows": r["n_rows"],
            "n_rows_good": r["n_rows_good"],
            "n_rows_bad": r["n_rows_bad"],
            "n_features": r["n_features"],
            "pct_stable": round(r["pct_stable"], 1),
        })

    compare_df = pd.DataFrame(rows)

    # Stabilité des features : écart-type moyen de chaque feature sur les bons runs.
    # Plus il est stable (faible), plus les features sont reproductibles.
    print("\nStabilité des features (std moyen des features par fenêtre, runs OK) :")
    stab_rows = []
    for w in config.WINDOW_CANDIDATES:
        df = pd.read_csv(config.DATA_FEATURES / f"dataset_ml_w{w}.csv")
        df = df[df["bad_run"] == 0]
        # On ne regarde que les features numériques « _mean » et « _std »
        mean_cols = [c for c in df.columns if c.endswith("_mean")]
        std_cols = [c for c in df.columns if c.endswith("_std")]
        stab_rows.append({
            "window_sec": w,
            "features_mean_avg": round(df[mean_cols].std().mean(), 3),
            "features_std_avg":  round(df[std_cols].mean().mean(),  3),
        })
    stab_df = pd.DataFrame(stab_rows)

    print("\n" + compare_df.to_string(index=False))
    print("\n" + stab_df.to_string(index=False))

    # Export comparatif
    out = config.REPORTS_DIR / "window_comparison.csv"
    compare_df.merge(stab_df, on="window_sec").to_csv(out, index=False)
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
