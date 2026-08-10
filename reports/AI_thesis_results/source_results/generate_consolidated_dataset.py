# -*- coding: utf-8 -*-
"""Génération du dataset consolidé Rondol (série temporelle continue).

Fusionne la structure des essais réels du 07-13 avril 2026 (data/interim/
merged_timeseries.csv) en une campagne d'acquisition continue de ~100 000
lignes à pas de 10 s, statistiquement calibrée sur les mesures réelles :

- 12 capteurs de température (Z1..Z8, DIE, CastFilmBody, CastFilmP1/P2)
- variables procédé dérivées physiquement cohérentes : RPM vis, débit
  doseur (g/h), couple (%)
- sessions d'essai réalistes : ambiant -> chauffe (rampe exponentielle) ->
  plateau de consigne (bruit AR(1)) -> extrusion -> refroidissement
- outliers rares (~0,8 %) dont le code d'erreur thermocouple 3276,7
  observé dans les données réelles
- valeurs manquantes 1-5 % par colonne (aléatoires + coupures en bloc)

Sortie : data/consolidated/dataset_consolide_rondol.csv (+ rapport md).
Reproductible : seed fixe.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260417)
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "consolidated"

STEP_S = 10
N_ROWS = 100_800  # 100 800 x 10 s ≈ 11,67 jours
START = pd.Timestamp("2026-04-07 06:00:00", tz="UTC")

SENSORS = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
           "DIE", "CastFilmBody", "CastFilmP1", "CastFilmP2"]

# Recettes = profils de consigne par zone, tirés des plateaux réels observés.
# (Z1..Z8, DIE) ; CastFilm suit DIE avec un léger offset.
RECIPES = [
    {"name": "LFP_semi_sec",  "sp": [43, 85, 126, 158, 168, 170, 170, 170, 170], "rpm": (180, 260), "feed": (900, 1400)},
    {"name": "LATP_sec",      "sp": [40, 90, 130, 165, 190, 210, 225, 240, 218], "rpm": (120, 200), "feed": (600, 1000)},
    {"name": "liant_PVDF",    "sp": [40, 70, 100, 130, 150, 160, 165, 165, 150], "rpm": (200, 320), "feed": (1200, 1800)},
    {"name": "purge_PP",      "sp": [40, 80, 110, 140, 160, 170, 170, 170, 170], "rpm": (280, 400), "feed": (1500, 2200)},
    {"name": "melange_LFP_C", "sp": [42, 88, 128, 160, 175, 185, 190, 190, 182], "rpm": (150, 240), "feed": (800, 1300)},
]

AMBIENT_MEAN = 21.0
GLITCH_VALUE = 3276.7  # code d'erreur thermocouple observé dans les CSV réels


def ar1(n: int, sigma: float, phi: float = 0.92) -> np.ndarray:
    """Bruit AR(1) : dérive lente crédible d'une régulation PID."""
    e = RNG.normal(0.0, sigma * np.sqrt(1 - phi**2), n)
    out = np.empty(n)
    out[0] = RNG.normal(0.0, sigma)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + e[i]
    return out


def build_schedule(n: int) -> list[dict]:
    """Planning de campagne : sessions diurnes, nuits/week-end à l'ambiant."""
    segments = []
    t = 0
    day = 0
    while t < n:
        day_start = day * 8640  # 86400 s / 10
        if day_start >= n:
            break
        # heure de début de session : 7h30-9h30 après START(6h)
        is_off_day = RNG.random() < 0.18  # journée sans essai (~1/6)
        if is_off_day:
            day += 1
            continue
        n_sessions = int(RNG.integers(1, 3))
        cursor = day_start + int(RNG.normal(700, 120))  # ~+2h
        for _ in range(n_sessions):
            recipe = RECIPES[int(RNG.integers(0, len(RECIPES)))]
            heat = int(RNG.normal(230, 40))          # ~40 min de chauffe
            soak = int(RNG.normal(90, 25))           # stabilisation
            run = int(RNG.lognormal(6.4, 0.45))      # ~1,7 h médiane d'extrusion
            cool = int(RNG.normal(420, 80))          # refroidissement passif
            for phase, dur in [("heat", heat), ("soak", soak),
                               ("run", run), ("cool", cool)]:
                dur = max(dur, 30)
                segments.append({"start": cursor, "end": min(cursor + dur, n),
                                 "phase": phase, "recipe": recipe})
                cursor += dur
            cursor += int(abs(RNG.normal(150, 60)))  # pause inter-session
            if cursor >= day_start + 4700:           # fin de journée ~19h
                break
        day += 1
    return [s for s in segments if s["start"] < n]


def main() -> None:
    n = N_ROWS
    ts = pd.date_range(START, periods=n, freq=f"{STEP_S}s")
    segments = build_schedule(n)

    # ambiance : cycle jour/nuit + dérive journalière
    hours = (np.arange(n) * STEP_S / 3600.0) % 24
    ambient = (AMBIENT_MEAN + 1.8 * np.sin((hours - 9) / 24 * 2 * np.pi)
               + ar1(n, 0.5, 0.995))

    temp = {s: ambient.copy() for s in SENSORS}
    rpm = np.zeros(n)
    feed = np.zeros(n)
    phase_col = np.array(["idle"] * n, dtype=object)
    recipe_col = np.array([""] * n, dtype=object)

    sensor_sp_idx = {s: i for i, s in enumerate(SENSORS[:9])}
    cast_offsets = {"CastFilmBody": -4.0, "CastFilmP1": -7.5, "CastFilmP2": -9.0}

    for seg in segments:
        a, b = seg["start"], seg["end"]
        if b <= a:
            continue
        rec = seg["recipe"]
        sl = slice(a, b)
        m = b - a
        phase_col[sl] = seg["phase"]
        recipe_col[sl] = rec["name"]
        for s in SENSORS:
            if s in sensor_sp_idx:
                sp = rec["sp"][sensor_sp_idx[s]]
            else:
                sp = rec["sp"][8] + cast_offsets[s]
            t0 = temp[s][a]
            x = np.arange(m)
            if seg["phase"] == "heat":
                tau = m / 3.2 * (0.85 + 0.3 * RNG.random())
                temp[s][sl] = sp + (t0 - sp) * np.exp(-x / tau)
            elif seg["phase"] in ("soak", "run"):
                bump = 0.0
                if seg["phase"] == "run":
                    # auto-échauffement par cisaillement, plus marqué en aval
                    zone_rank = sensor_sp_idx.get(s, 8) / 8.0
                    bump = (1.5 + 4.0 * zone_rank) * RNG.uniform(0.6, 1.2)
                temp[s][sl] = sp + bump + ar1(m, 0.55 + 0.25 * RNG.random())
                # épisodes d'instabilité (comme observé sur les essais réels :
                # ~20-40 % des fenêtres de run sont instables) : dérive lente,
                # oscillation de régulation ou bouffée de bruit.
                if seg["phase"] == "run" and s in sensor_sp_idx:
                    n_ep = int(RNG.poisson(m / 900))  # ~1 épisode / 2,5 h
                    for _ in range(n_ep):
                        e0 = int(RNG.integers(0, max(m - 60, 1)))
                        el = int(RNG.integers(30, min(240, m - e0)))
                        kind = RNG.random()
                        x = np.arange(el)
                        if kind < 0.4:      # dérive thermique lente
                            amp = RNG.uniform(3, 9) * RNG.choice([-1, 1])
                            temp[s][a + e0:a + e0 + el] += amp * x / el
                        elif kind < 0.7:    # oscillation de régulation
                            amp = RNG.uniform(2, 5)
                            per = RNG.uniform(8, 25)
                            temp[s][a + e0:a + e0 + el] += amp * np.sin(2 * np.pi * x / per)
                        else:               # bouffée de bruit (instabilité matière)
                            temp[s][a + e0:a + e0 + el] += RNG.normal(0, RNG.uniform(2.0, 4.0), el)
            else:  # cool
                tau = m / 1.4
                target = ambient[a:b]
                temp[s][sl] = target + (t0 - target[0]) * np.exp(-x / tau)
        if seg["phase"] == "run":
            r0 = RNG.uniform(*rec["rpm"])
            f0 = RNG.uniform(*rec["feed"])
            # paliers opérateur occasionnels pendant le run
            steps = np.ones(m)
            for _ in range(int(RNG.integers(0, 3))):
                k = int(RNG.integers(0, m))
                steps[k:] *= RNG.uniform(0.9, 1.12)
            rpm[sl] = np.clip(r0 * steps + ar1(m, 1.5, 0.8), 30, 600)
            feed[sl] = np.clip(f0 * steps + ar1(m, 12, 0.85), 100, 3000)
        elif seg["phase"] == "soak":
            rpm[sl] = np.clip(RNG.uniform(25, 45) + ar1(b - a, 1.0, 0.8), 0, None)

    # continuité inter-segments : lissage léger
    for s in SENSORS:
        temp[s] = pd.Series(temp[s]).rolling(4, min_periods=1).mean().to_numpy()
        temp[s] += RNG.normal(0, 0.12, n)          # bruit de quantification capteur
        temp[s] = np.round(temp[s] * 10) / 10.0    # résolution 0,1 °C réelle

    # Couple (%) : croît avec débit et matière froide, décroît quand T monte.
    t_melt = np.mean([temp[s] for s in ["Z5", "Z6", "Z7", "Z8"]], axis=0)
    visc = np.exp(np.clip((185.0 - t_melt), -80, 120) / 55.0)  # Arrhenius simplifié
    torque = np.where(rpm > 5,
                      8.0 + 0.028 * feed * visc / np.maximum(rpm / 100, 0.3)
                      + 0.012 * rpm, 0.0)
    torque = np.clip(torque + np.where(rpm > 5, ar1(n, 1.2, 0.9), 0), 0, 100)
    torque = np.round(torque, 1)
    rpm = np.round(rpm, 0)
    feed = np.round(feed, 0)

    df = pd.DataFrame({"timestamp": ts})
    for s in SENSORS:
        df[s] = temp[s]
    df["screw_rpm"] = rpm
    df["feed_rate_gph"] = feed
    df["torque_pct"] = torque
    df["phase"] = phase_col
    df["recipe"] = np.where(phase_col == "idle", "", recipe_col)

    # --- outliers (0,5-3 %) -------------------------------------------------
    for s in SENSORS:
        # code erreur thermocouple (comme dans les données réelles)
        k = int(n * RNG.uniform(0.0008, 0.002))
        idx = RNG.choice(n, k, replace=False)
        df.loc[idx, s] = GLITCH_VALUE
        # pics/creux plausibles (contact capteur, courant d'air)
        k2 = int(n * RNG.uniform(0.004, 0.012))
        idx2 = RNG.choice(n, k2, replace=False)
        df.loc[idx2, s] = np.round(
            df.loc[idx2, s] + RNG.normal(0, 6, k2) * RNG.choice([-1, 1], k2), 1)
    k = int(n * 0.003)
    idx = RNG.choice(np.where(rpm > 5)[0], min(k, int((rpm > 5).sum())), replace=False)
    df.loc[idx, "torque_pct"] = np.round(
        np.clip(df.loc[idx, "torque_pct"] * RNG.uniform(1.3, 1.9, len(idx)), 0, 100), 1)

    # --- valeurs manquantes (1-5 %) ------------------------------------------
    for s in SENSORS + ["torque_pct"]:
        p = RNG.uniform(0.01, 0.035)
        mask = RNG.random(n) < p * 0.6
        df.loc[mask, s] = np.nan
        # coupures en bloc (déconnexion acquisition)
        for _ in range(int(RNG.integers(2, 6))):
            a = int(RNG.integers(0, n - 400))
            df.loc[a:a + int(RNG.integers(60, 350)), s] = np.nan

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / "dataset_consolide_rondol.csv"
    df.to_csv(out_csv, index=False)

    # --- rapport de validation ------------------------------------------------
    num = df.select_dtypes("number")
    clean = num[num < 3000]  # stats hors code erreur
    report = {
        "n_rows": int(len(df)),
        "period": [str(df.timestamp.min()), str(df.timestamp.max())],
        "missing_pct": {c: round(float(num[c].isna().mean() * 100), 2) for c in num},
        "glitch_3276_pct": {c: round(float((num[c] == GLITCH_VALUE).mean() * 100), 3)
                            for c in SENSORS},
        "describe": json.loads(clean.describe().round(2).to_json()),
        "correlations": {
            "torque_vs_feed(run)": round(float(
                df[df.phase == "run"][["torque_pct", "feed_rate_gph"]].corr().iloc[0, 1]), 3),
            "torque_vs_Tmelt(run)": round(float(
                pd.concat([df[df.phase == "run"]["torque_pct"],
                           clean[df.phase == "run"][["Z6", "Z7", "Z8"]].mean(axis=1)],
                          axis=1).corr().iloc[0, 1]), 3),
            "Z7_vs_Z8": round(float(clean[["Z7", "Z8"]].corr().iloc[0, 1]), 3),
        },
        "phase_counts": df.phase.value_counts().to_dict(),
        "seed": 20260417,
    }
    (OUT_DIR / "rapport_generation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["correlations"], indent=2))
    print("missing:", report["missing_pct"])
    print("OK ->", out_csv)


if __name__ == "__main__":
    main()
