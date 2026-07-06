"""
seed_demo_state.py — Enregistre une CONFIGURATION DE DÉMONSTRATION crédible
                     comme snapshot validé (corrige l'état sauvegardé sous-peuplé).

Problème corrigé : le snapshot persistant (`applied_state`) ne contenait que
6 éléments et aucun feeder solide réellement défini → fill_factor ≈ 0 (vis quasi
vide), KPIs non crédibles pour une démonstration.

Ce script construit, via les builders RÉELS de l'application :
  - une vis peuplée (≈23 éléments : convoyage + malaxages + convoyage) ;
  - un feeder solide actif (granulés LFP/LATP, 30 g/min, ρ 0,55) ;
  - un profil thermique SSB nominal ;
puis l'enregistre via la couche de persistance (même chemin que l'app).

Usage : python scripts/seed_demo_state.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import screw_logic as scl  # noqa: E402  (import nu — invariant singleton)
from AgentIndustrial_v1.core.process import ProcessState  # noqa: E402
from AgentIndustrial_v1.core.feeders import FeederSpec  # noqa: E402
from AgentIndustrial_v1.core.screw_adapter import refresh_kpis  # noqa: E402
from AgentIndustrial_v1.core.applied_state import take_snapshot, snapshot_to_dict  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
import persistence as P  # noqa: E402

LABEL = "DEMO_RONDOL_LFP_LATP"


def _demo_config() -> list[int]:
    """Vis peuplée représentative (réplique de la config démo Profile, ≈23 élts)."""
    cfg = scl.new_empty_configuration()
    scl.add_element(cfg, 1, count=6)   # convoyage avant
    scl.add_element(cfg, 4, count=2)   # malaxage 90°
    scl.add_element(cfg, 7, count=2)   # malaxage 60°
    scl.add_element(cfg, 1, count=5)   # convoyage
    scl.add_element(cfg, 8, count=1)   # malaxage 45°
    scl.add_element(cfg, 5, count=1)   # malaxage 30°
    scl.add_element(cfg, 1, count=6)   # convoyage final
    return cfg


def _demo_feeders() -> list[FeederSpec]:
    # Matière LFP/LATP : thermiquement robuste (dégradation ≈ 260 °C) — le profil
    # SSB chaud est donc légitime, pas une incompatibilité.
    return [
        FeederSpec(feeder_id=1, enabled=True, label="LFP/LATP (démo)",
                   material_id="powder", position="Z0",
                   mass_flow_g_per_min=20.0, density_g_per_cm3=0.55,
                   polymer_name="LFP+LATP", t_degradation_C=260.0, tga_onset_C=320.0),
        *[FeederSpec(feeder_id=i, enabled=False) for i in range(2, 6)],
    ]


def main() -> int:
    # Point de fonctionnement = conditions de référence documentées (mémoire 7.1) :
    # 150 rpm, 1,2 kg/h ≈ 20 g/min. Profil thermique SSB nominal.
    cfg = _demo_config()
    zone_temps = {"Z1": 60.0, "Z2": 90.0, "Z3": 120.0, "Z4": 150.0, "Z5": 160.0,
                  "Z6": 160.0, "Z7": 150.0, "Z8": 140.0,
                  "die": 140.0, "die2": 135.0, "die3": 130.0, "die4": 125.0}
    state = ProcessState(screw_config=cfg, screw_rpm=150.0,
                         zone_temps_C=zone_temps, feeders=_demo_feeders(),
                         n_die_zones=1)
    state.kpis = refresh_kpis(state)

    print(f"éléments vis        : {scl.count_user_elements(cfg):.0f}")
    print(f"fill_factor moyen   : {state.kpis.fill_factor:.4f}")
    print(f"résidence (s)       : {state.kpis.residence_time_s:.1f}")
    print(f"SME (kWh/kg)        : {state.kpis.sme_kwh_per_kg:.3f}")
    rep = evaluate(state, lang="fr")
    print(f"agent: état={rep.state} risk={rep.risk_score} "
          f"alertes={[a.code for a in rep.alerts]}")

    snap = take_snapshot(state, label=LABEL)
    backend = P.save_applied_state(snapshot_to_dict(snap))
    print(f"\n[OK] snapshot démo enregistré (backend: {backend}, label: {LABEL})")

    # Vérification round-trip
    back = P.load_applied_state()
    n_back = scl.count_user_elements(back.get("screw_config", []))
    print(f"[VÉRIF] relu : {n_back:.0f} éléments, label={back.get('label')}")
    ok = n_back >= 20 and back.get("label") == LABEL
    print("[RÉSULTAT]", "✅ config démo crédible persistée" if ok else "❌ échec")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
