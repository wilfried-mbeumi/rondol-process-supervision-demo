"""Tests correction métier — bivis (volume) + recommandations sans élément inventé.

Couvre les 4 exigences manager :
  1. test_free_volume_two_screws       — free = 76.18 − 2 × occupé/vis (ex. 24.42 → 27.34)
  2. test_occupied_total_is_twice_per_screw
  3. test_reco_no_invented_element     — config Conveying seul ⇒ aucune reco Kneading/Malaxage
  4. test_history_independence         — recos du run courant indépendantes de l'historique
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app.screw_logic import (  # noqa: E402
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    N_SCREWS,
    TIP_PART1_POS,
    TOTAL_FREE_VOL,
    add_element,
    base_type,
    fill_factor_average,
    free_volume,
    free_volume_for_occupied_per_screw,
    is_part2,
    new_empty_configuration,
    occupied_volume_per_screw,
    occupied_volume_total,
    position_to_zone,
    present_element_types,
    recommendation_cites_absent_element,
)
from app.screw_render import compute_recommendations  # noqa: E402

TOL = 0.02


def _saturated_conveying() -> list[int]:
    """Vis saturée : 39 convoyages entiers (positions 1..78) — cas exemple manager."""
    cfg = new_empty_configuration()
    for k in range(39):
        pos = 1 + 2 * k
        cfg[pos] = 1
        cfg[pos + 1] = 101
    return cfg


def _conveying_only(n: int = 10) -> list[int]:
    """Config avec UNIQUEMENT du convoyage (type 1) après le main feeder."""
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=n)
    return cfg


def _recos(cfg: list[int]):
    return compute_recommendations(
        cfg, 120.0, 30.0, 0.55,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )


# ---------------------------------------------------------------------------
# 1 — Volume libre bivis
# ---------------------------------------------------------------------------
def test_free_volume_two_screws():
    assert N_SCREWS == 2
    # Formule métier validée directe : 76.18 − 2 × 24.42 ≈ 27.34.
    assert abs(free_volume_for_occupied_per_screw(24.42) - 27.34) < TOL

    # Sur une vis saturée (39 convoyages) : occupé/vis ≈ 24.42, libre ≈ 27.34.
    cfg = _saturated_conveying()
    per_screw = occupied_volume_per_screw(cfg)
    free = free_volume(cfg)
    assert abs(per_screw - 24.42) < 0.05, per_screw
    assert abs(free - 27.34) < 0.05, free
    # Invariant central : libre = TOTAL − 2 × occupé/vis.
    assert abs(free - (TOTAL_FREE_VOL - N_SCREWS * per_screw)) < 1e-6


# ---------------------------------------------------------------------------
# 2 — Occupé total = 2 × occupé par vis
# ---------------------------------------------------------------------------
def test_occupied_total_is_twice_per_screw():
    for cfg in (_saturated_conveying(), _conveying_only(6), new_empty_configuration()):
        assert abs(occupied_volume_total(cfg) - 2 * occupied_volume_per_screw(cfg)) < 1e-9


# ---------------------------------------------------------------------------
# 3 — Aucune recommandation n'invente un élément absent
# ---------------------------------------------------------------------------
_FORBIDDEN = ("kneading", "malaxage", "malaxeur")


def test_present_element_types_conveying_only():
    cfg = _conveying_only(8)
    present = present_element_types(cfg)
    assert present == {1}  # uniquement du convoyage
    assert present.isdisjoint({4, 5, 7, 8})  # aucun malaxage


def test_guard_flags_absent_element():
    cfg = _conveying_only(8)
    assert recommendation_cites_absent_element("Substituer 2 × Kneading 90° par 45°", cfg)
    assert recommendation_cites_absent_element("Adoucir le profil de malaxage", cfg)
    # Une reco sur le convoyage présent n'est PAS bloquée.
    assert not recommendation_cites_absent_element("Augmenter le convoyage", cfg)
    # Recos élément-agnostiques jamais bloquées.
    assert not recommendation_cites_absent_element("Réduire la vitesse vis à 100 rpm", cfg)


def test_reco_no_invented_element_screw_render():
    cfg = _conveying_only(10)
    recs = _recos(cfg)
    for r in recs:
        blob = " ".join(
            str(r.get(k, "")) for k in
            ("physics", "impact", "action", "title", "detail", "evidence")
        ).lower()
        for token in _FORBIDDEN:
            assert token not in blob, f"reco cite un élément absent : {r}"


def test_reco_no_invented_element_agent():
    """L'agent (rules-based) ne doit pas conserver une reco « substituer Kneading »
    quand la config ne contient pas de malaxage."""
    from AgentIndustrial_v1.core.process import ProcessState, ScrewKPIs
    from AgentIndustrial_v1.core.rules import Alert
    from AgentIndustrial_v1.core.recommendations import build_recommendations

    cfg = _conveying_only(10)
    state = ProcessState(screw_config=cfg, screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=0.5)  # déclenche le contenu SME (kneading)
    alert = Alert(
        code="SME_WARNING", severity="warning",
        title="SME élevé", description="", evidence="SME=0.50 kWh/kg",
        target="Global vis",
    )
    recos = build_recommendations(state, [alert])
    blob = " ".join(
        f"{r.title} {r.rationale} {r.action} {r.delta_label}" for r in recos
    ).lower()
    for token in _FORBIDDEN:
        assert token not in blob, f"agent cite un élément absent : {blob}"
    # Le repli élément-agnostique (baisser rpm) subsiste.
    assert any(r.code == "REC_REDUCE_RPM_SME" for r in recos)


# ---------------------------------------------------------------------------
# 4 — Indépendance vis-à-vis de l'historique
# ---------------------------------------------------------------------------
def test_history_independence(tmp_path, monkeypatch):
    cfg = _conveying_only(12)
    add_element(cfg, 4, count=2)  # un peu de malaxage pour des recos riches

    before = _recos(cfg)

    # On pointe l'historique vers un fichier rempli de fausses entrées.
    fake = tmp_path / "process_history.json"
    fake.write_text(json.dumps([
        {"schema_version": 1, "id": "fake1", "config": {"screw_rpm": 999.0}},
        {"schema_version": 1, "id": "fake2", "config": {"screw_rpm": 1.0}},
    ]), encoding="utf-8")
    monkeypatch.setenv("RONDOL_HISTORY_PATH", str(fake))

    after = _recos(cfg)
    assert before == after, "les recommandations ont changé avec l'historique"


def test_reco_modules_do_not_import_history():
    """Garde statique : les modules de recommandation ne lisent jamais l'historique."""
    import app.screw_render as sr
    import AgentIndustrial_v1.core.recommendations as ar
    assert "history_store" not in inspect.getsource(sr)
    assert "history_store" not in inspect.getsource(ar)
