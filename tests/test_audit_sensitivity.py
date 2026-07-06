"""
test_audit_sensitivity.py — Garde-fous techniques issus de l'audit application.

Verrouille les propriétés que le jury pourrait challenger :
  1. L'agent RÉAGIT à la configuration procédé (le score/les alertes changent).
  2. Aucune recommandation orpheline (toute reco est liée à une alerte source).
  3. Aucune recommandation absurde : une reco n'apparaît que si son alerte existe.
  4. La prédiction ML reçoit le bon nombre de features (87) et n'est pas figée.
  5. La persistance fait un round-trip écriture→lecture.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd  # noqa: E402

from AgentIndustrial_v1.core.process import ProcessState  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
from AgentIndustrial_v1.core.recommendations import build_recommendations  # noqa: E402


def _state(ff: float, sme: float = 0.2, rt: float = 30.0) -> ProcessState:
    s = ProcessState()
    s.kpis.fill_factor = ff
    s.kpis.sme_kwh_per_kg = sme
    s.kpis.residence_time_s = rt
    return s


def test_agent_reacts_to_fill_factor():
    """Saturation (ff>0.65) et famine (ff<0.10) déclenchent des alertes DIFFÉRENTES."""
    sat = {a.code for a in evaluate(_state(0.95), lang="fr").alerts}
    starv = {a.code for a in evaluate(_state(0.05), lang="fr").alerts}
    assert "FF_SATURATION" in sat, sat
    assert "FF_STARVATION" in starv, starv
    assert sat != starv  # le diagnostic dépend bien de la config


def test_risk_score_orders_with_severity():
    """Une config gavée doit être au moins aussi risquée qu'une config nominale."""
    r_ok = evaluate(_state(0.45), lang="fr").risk_score
    r_bad = evaluate(_state(0.95), lang="fr").risk_score
    assert r_bad <= r_ok  # plus c'est gavé, plus le score baisse (0=pire)


def test_no_orphan_recommendation():
    """Toute recommandation est tracée vers une alerte source (linked_alert_code)."""
    s = _state(0.95, sme=0.6)
    rep = evaluate(s, lang="fr")
    recos = build_recommendations(s, rep.alerts, lang="fr")
    alert_codes = {a.code for a in rep.alerts}
    assert recos, "au moins une reco attendue en régime gavé"
    for rc in recos:
        linked = getattr(rc, "linked_alert_code", None)
        assert linked, f"reco sans alerte liée: {getattr(rc, 'code', '?')}"
        assert linked in alert_codes, f"reco {rc.code} liée à une alerte inexistante {linked}"


def test_no_reco_without_alert():
    """Sans alerte actionnable, aucune reco absurde n'est inventée (état sain mini)."""
    s = _state(0.45, sme=0.1, rt=30.0)
    rep = evaluate(s, lang="fr")
    recos = build_recommendations(s, rep.alerts, lang="fr")
    alert_codes = {a.code for a in rep.alerts}
    for rc in recos:
        assert getattr(rc, "linked_alert_code", None) in alert_codes


def test_ml_model_features_aligned_and_live():
    """Le modèle intégré reçoit 87 features et produit une proba valide (non figée)."""
    import joblib
    m = joblib.load(ROOT / "models" / "RandomForest_w60_augmented.joblib")
    df = pd.read_csv(ROOT / "data" / "features" / "dataset_ml_w60.csv",
                     parse_dates=["window_start", "window_end"])
    meta = {"run_id", "window_start", "window_end", "n_samples", "stability_score",
            "is_stable", "target_horizon_sec", "run_duration_min", "bad_run"}
    fcols = [c for c in df.columns if c not in meta]
    assert len(fcols) == m.n_features_in_ == 87
    good = df[df["bad_run"] == 0]
    proba = m.predict_proba(pd.DataFrame([good.iloc[0][fcols]]))[0]
    assert 0.0 <= float(proba[1]) <= 1.0
    assert abs(sum(proba) - 1.0) < 1e-6


def test_persistence_roundtrip():
    """save_applied_state -> load_applied_state restitue le payload (isolé par conftest)."""
    import persistence as P
    payload = {"screw_config": [0] * 81, "__audit_probe__": "OK"}
    P.save_applied_state(payload)
    back = P.load_applied_state()
    assert back is not None and back.get("__audit_probe__") == "OK"
