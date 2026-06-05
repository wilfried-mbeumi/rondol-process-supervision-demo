"""
test_render_smoke.py — smoke tests rendu vis (post Étape rendu V2).

Vérifie que :
- build_screw_assembly_html accepte les nouveaux paramètres
  (zone_labels, zone_subvalues, feeder_markers) sans erreur
- compute_recommendations / recommend_element_count tournent sur
  des configs représentatives (vide / démo / chaotic) sans exception
- les recos générées contiennent bien des références zone-localisées
  ("Z2", "Z6", etc.) — preuve que le renforcement actions localisées
  est actif

Pas de Streamlit ici : pur Python sur les fonctions pures de screw_render.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.screw_logic import (  # noqa: E402
    ELEMENT_TYPES,
    MAIN_FEEDER_POSITION,
    N_POSITIONS,
    START_ELMT_ZONE,
    TIP_PART1_POS,
    add_element,
    base_type,
    fill_factor_average,
    is_part2,
    new_empty_configuration,
    position_to_zone,
    side_feeder_position,
    zone_residence_times,
)
from app.screw_render import (  # noqa: E402
    analyze_profile,
    build_screw_assembly_html,
    compute_recommendations,
    list_placed_elements,
    recommend_element_count,
)


def _demo_cfg():
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=6)
    add_element(cfg, 4, count=2)
    add_element(cfg, 7, count=2)
    add_element(cfg, 1, count=5)
    add_element(cfg, 8, count=1)
    add_element(cfg, 5, count=1)
    add_element(cfg, 1, count=6)
    return cfg


def _chaotic_cfg():
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=4)
    add_element(cfg, 10, count=6)
    add_element(cfg, 1, count=4)
    add_element(cfg, 4, count=2)
    add_element(cfg, 1, count=3)
    return cfg


def _empty_intermediate_cfg():
    """Config qui laisse au moins une zone intermédiaire vide entre deux
    zones occupées → reco localisée par zone (Z5/Z6/Z7 selon flow)."""
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=20)   # convoyage Z1..Z4
    add_element(cfg, 4, count=4)    # mélange Z4-Z5
    add_element(cfg, 1, count=4)    # convoyage final qui retombe ~Z6
    return cfg


# ---------------------------------------------------------------------------
# R1 — render accepte les nouveaux paramètres
# ---------------------------------------------------------------------------
def test_R1_render_with_new_params():
    cfg = _demo_cfg()
    zone_labels = ["Feed", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
    zone_subvalues = [f"{i*0.5:.1f} s".replace(".", ",") for i in range(9)]
    markers = [
        {"pos": MAIN_FEEDER_POSITION, "label": "MAIN", "color": "#10B981"},
        {"pos": 30, "label": "SIDE Z4", "color": "#06B6D4"},
    ]
    html = build_screw_assembly_html(
        cfg, N_POSITIONS,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        element_full_name_fn=lambda t: ELEMENT_TYPES[t].full_name,
        show_zones=True,
        zone_starts=list(START_ELMT_ZONE)[:9],
        zone_labels=zone_labels,
        zone_subvalues=zone_subvalues,
        feeder_markers=markers,
    )
    assert "Feed" in html
    assert "Z8" in html
    assert "MAIN" in html
    assert "SIDE Z4" in html
    # Sous-ligne résidence présente
    assert "rs-zone-sub" in html
    # Marqueurs présents
    assert "rs-feeder-marker" in html


# ---------------------------------------------------------------------------
# R2 — render rétrocompatible (sans nouveaux paramètres)
# ---------------------------------------------------------------------------
def test_R2_render_backward_compat():
    cfg = new_empty_configuration()
    html = build_screw_assembly_html(
        cfg, N_POSITIONS,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        element_full_name_fn=lambda t: ELEMENT_TYPES[t].full_name,
        show_zones=True,
        zone_starts=list(START_ELMT_ZONE)[:9],
    )
    # Fallback labels Z0..Z8
    assert "Z0" in html
    assert "Z8" in html
    # Pas d'éléments DOM sous-ligne ni marqueurs (les classes CSS restent
    # définies mais aucune instance n'est rendue)
    assert '<div class="rs-zone-sub">' not in html
    assert '<div class="rs-feeder-marker"' not in html


# ---------------------------------------------------------------------------
# R3 — recos vis vide
# ---------------------------------------------------------------------------
def test_R3_recs_empty_screw():
    cfg = new_empty_configuration()
    recs = compute_recommendations(
        cfg, rpm=120.0, feed=30.0, dens=0.55,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    assert len(recs) >= 1
    assert any("vide" in r["title"].lower() for r in recs)


# ---------------------------------------------------------------------------
# R4 — recos config démo (doit citer au moins une zone)
# ---------------------------------------------------------------------------
def test_R4_recs_demo_cites_zones():
    cfg = _demo_cfg()
    recs = compute_recommendations(
        cfg, rpm=120.0, feed=30.0, dens=0.55,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    assert len(recs) >= 1
    # Au moins une reco doit citer une zone Z[0-8] dans son détail ou titre
    all_text = " ".join(r["title"] + " " + r["detail"] for r in recs)
    has_zone = any(f"Z{z}" in all_text for z in range(9))
    assert has_zone, f"Aucune reco ne cite de zone : {all_text[:200]}"


# ---------------------------------------------------------------------------
# R5 — recos config Z6 vide → mention explicite "Z6" dans une reco
# ---------------------------------------------------------------------------
def test_R5_recs_localizes_empty_zone():
    cfg = _empty_intermediate_cfg()
    recs = compute_recommendations(
        cfg, rpm=120.0, feed=30.0, dens=0.55,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    # Au moins une reco doit cibler explicitement une zone Z5/Z6/Z7 vide.
    # On cherche la zone et la mention "0 élément" / "vide" / "transport interrompu" / etc.
    # dans n'importe quel champ structuré (title, action, physics, impact, evidence, zone).
    def _full(r):
        return " ".join(str(r.get(k, "")) for k in
                        ("title", "detail", "physics", "impact", "action",
                         "evidence", "zone"))
    has_localized = any(
        any(f"Z{z}" in r.get("zone", "") for z in (5, 6, 7))
        and ("0 élément" in _full(r) or "transport" in _full(r).lower()
             or "vide" in _full(r).lower())
        for r in recs
    )
    assert has_localized, (
        "Pas de reco zone-localisée trouvée : "
        + str([(r.get("zone"), r.get("title")) for r in recs])
    )


# ---------------------------------------------------------------------------
# R6 — recommend_element_count sur 3 configs → suggested ∈ {25,30,40}
# ---------------------------------------------------------------------------
def test_R6_recommend_count_returns_valid():
    for cfg_fn in (new_empty_configuration, _demo_cfg, _chaotic_cfg):
        cfg = cfg_fn()
        cr = recommend_element_count(
            cfg, rpm=120.0, feed=30.0, dens=0.55,
            base_type_fn=base_type,
            is_part2_fn=is_part2,
            fill_factor_fn=fill_factor_average,
            n_positions=N_POSITIONS,
            main_feeder_pos=MAIN_FEEDER_POSITION,
            tip_part1_pos=TIP_PART1_POS,
            position_to_zone_fn=position_to_zone,
            zone_residence_fn=zone_residence_times,
        )
        assert cr.suggested in (25, 30, 40)
        assert cr.confidence in ("high", "medium", "low")
        assert cr.tagline  # non-vide
        assert len(cr.action_steps) >= 1


# ---------------------------------------------------------------------------
# R7 — list_placed_elements + side_feeder_position cohérents
# ---------------------------------------------------------------------------
def test_R7_placed_and_sidefeeder_coherent():
    cfg = _demo_cfg()
    placed = list_placed_elements(
        cfg, N_POSITIONS,
        base_type_fn=base_type,
        is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        element_label_fn=lambda t: ELEMENT_TYPES[t].label,
    )
    # Tous les éléments placés ont une zone valide 0..8
    for p in placed:
        assert 0 <= p.zone <= 8
    # Side feeder Z4 → position structurée valide
    sf_pos = side_feeder_position(cfg, 4)
    assert 0 <= sf_pos < N_POSITIONS


# ---------------------------------------------------------------------------
# Agent IA — niveau ingénieur procédé (V2)
# ---------------------------------------------------------------------------
def _analyze(cfg, rpm=120.0, feed=30.0, dens=0.55):
    return analyze_profile(
        cfg, rpm, feed, dens,
        base_type_fn=base_type, is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )


# A1 — vis vide → archetype "vide", regime classifié
def test_A1_archetype_empty():
    p = _analyze(new_empty_configuration())
    assert p.archetype_short == "vide"
    assert p.archetype_severity == "info"
    assert p.regime_short in ("rapide", "modéré", "lent",
                               "saturé", "sous-alimenté")
    assert "Aucun" in p.summary or "vide" in p.summary.lower()


# A2 — config démo équilibrée → archetype "équilibré" ou variations
def test_A2_archetype_demo_reasonable():
    p = _analyze(_demo_cfg())
    # Démo : 19 forward + 4 kneading + 1 chaotic 0 + reverse 0 → balanced/distrib
    assert p.archetype_short in (
        "équilibré", "convectif", "distributif", "chaotique",
        "minimaliste", "sous-utilisé", "déséquilibré",
    )
    assert p.metrics["n_filled"] > 0


# A3 — config 100% kneading → "dispersif intense"
def test_A3_archetype_dispersive():
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=2)        # un peu de transport
    add_element(cfg, 4, count=10)       # malaxage 90° dispersif dominant
    p = _analyze(cfg)
    assert p.archetype_short in ("dispersif", "déséquilibré"), p.archetype


# A4 — convoyage seul → "convectif dominant"
def test_A4_archetype_convective():
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=12)
    p = _analyze(cfg)
    assert p.archetype_short == "convectif", p.archetype


# A5 — régime rapide modulé par rpm × feed
def test_A5_regime_responds_to_params():
    cfg = _demo_cfg()
    slow = _analyze(cfg, rpm=60.0, feed=10.0)
    fast = _analyze(cfg, rpm=240.0, feed=80.0)
    assert slow.regime_short != fast.regime_short, (
        f"régime non sensible : slow={slow.regime}, fast={fast.regime}"
    )


# A6 — densité élevée → mention céramiques dans summary
def test_A6_high_density_mentioned():
    cfg = new_empty_configuration()
    add_element(cfg, 1, count=8)
    add_element(cfg, 4, count=2)
    p = _analyze(cfg, dens=2.5)  # NMC811 / LFP densité élevée
    assert "céramique" in p.summary.lower() or "ρ=2.5" in p.summary or \
        "abrasion" in p.summary.lower(), p.summary


# A7 — recos ont les 6 champs structurés (severity + zone + physics + impact + action + evidence)
def test_A7_recs_have_structured_fields():
    cfg = _demo_cfg()
    recs = compute_recommendations(
        cfg, rpm=120.0, feed=30.0, dens=0.55,
        base_type_fn=base_type, is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    assert len(recs) >= 1
    for r in recs:
        # Tous les champs structurés présents
        for k in ("severity", "zone", "physics", "impact", "action", "evidence",
                  "title", "detail"):
            assert k in r, f"reco sans champ {k} : {r}"
        # Action non-vide (sauf cas particuliers ok-only)
        assert r["action"], f"action vide : {r}"


# A8 — recos modulées par rpm élevé (mentionnent rpm dans action)
def test_A8_recs_modulated_by_rpm():
    cfg = _empty_intermediate_cfg()
    recs_high = compute_recommendations(
        cfg, rpm=240.0, feed=30.0, dens=0.55,
        base_type_fn=base_type, is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    # Au moins une reco doit citer "240" dans son action ou mentionner le régime
    full_text = " ".join(r["action"] + " " + r["impact"] for r in recs_high)
    assert "240" in full_text or "rpm" in full_text.lower()


# A9 — recommend_element_count expose why_optimal + archetype + regime
def test_A9_count_rec_exposes_engineering_fields():
    cfg = _demo_cfg()
    cr = recommend_element_count(
        cfg, rpm=140.0, feed=35.0, dens=0.65,
        base_type_fn=base_type, is_part2_fn=is_part2,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
        position_to_zone_fn=position_to_zone,
    )
    assert hasattr(cr, "why_optimal")
    assert hasattr(cr, "archetype")
    assert hasattr(cr, "regime")
    assert cr.why_optimal, "why_optimal vide"
    assert cr.archetype, "archetype vide"
    assert cr.regime, "regime vide"
    # why_optimal doit contenir au moins une référence aux paramètres
    assert any(token in cr.why_optimal
               for token in ("140", "35", "0.65", "rpm", "g/min"))


TESTS = [
    ("R1 render new params", test_R1_render_with_new_params),
    ("R2 render backward compat", test_R2_render_backward_compat),
    ("R3 recs empty screw", test_R3_recs_empty_screw),
    ("R4 recs demo cite zones", test_R4_recs_demo_cites_zones),
    ("R5 recs localize empty zone", test_R5_recs_localizes_empty_zone),
    ("R6 recommend_count valid", test_R6_recommend_count_returns_valid),
    ("R7 placed + side feeder coherent", test_R7_placed_and_sidefeeder_coherent),
    ("A1 archetype empty", test_A1_archetype_empty),
    ("A2 archetype demo reasonable", test_A2_archetype_demo_reasonable),
    ("A3 archetype dispersive", test_A3_archetype_dispersive),
    ("A4 archetype convective", test_A4_archetype_convective),
    ("A5 regime responds to params", test_A5_regime_responds_to_params),
    ("A6 high density mentioned", test_A6_high_density_mentioned),
    ("A7 recs have structured fields", test_A7_recs_have_structured_fields),
    ("A8 recs modulated by rpm", test_A8_recs_modulated_by_rpm),
    ("A9 count rec engineering fields", test_A9_count_rec_exposes_engineering_fields),
]


def main() -> int:
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}  :: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}  :: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS  {name}")
    print()
    if failed == 0:
        print(f"Render smoke : {len(TESTS)}/{len(TESTS)} tests PASS")
        return 0
    print(f"Render smoke : {failed}/{len(TESTS)} tests FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
