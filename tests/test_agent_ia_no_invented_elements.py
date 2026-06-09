"""tests/test_agent_ia_no_invented_elements.py

Cause racine #2 manager 2026-06-09 : l'Agent IA produisait des recommandations
templées du type « Substituer 2 × Kneading 90° par 2 × Kneading 45° » SANS
inspecter `state.screw_config`. Si l'opérateur avait placé uniquement
convoyage + Kneading 60°, la reco proposait de remplacer un élément ABSENT.

Plainte manager : « j'ai mis que des éléments convoyage et 60° et il parle
de Kneading 90°/45° ».

Correctif architectural : filtre `recommendation_cites_absent_element` étendu
avec des tokens d'angle spécifique (kneading 30/45/60/90 → types 5/8/7/4) pour
distinguer chaque angle. Avant le correctif, le token collectif "kneading"
couvrait {4,5,7,8} ensemble et laissait passer une reco mentionnant un angle
absent du moment qu'UN type kneading était présent.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from screw_logic import (  # noqa: E402
    ELEMENT_MENTION_TOKENS,
    add_elements_atomic,
    new_empty_configuration,
    recommendation_cites_absent_element,
)


def _cfg_conveying_and_kneading60():
    """Profil manager : convoyage + Kneading 60° UNIQUEMENT.
    Types présents : 1 (convoyage), 7 (Kneading 60°). Types ABSENTS : 4, 5, 8."""
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)   # convoyage (type 1)
    add_elements_atomic(cfg, 7, 4)   # Kneading 60° (type 7)
    return cfg


def _cfg_conveying_only():
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 10)
    return cfg


# ---------------------------------------------------------------------------
# 1 — Cas reproduisant exactement la plainte manager
# ---------------------------------------------------------------------------
def test_manager_scenario_kneading90_blocked_when_only_60():
    """Le scénario EXACT vu en prod : profil convoyage + Kneading 60°,
    reco qui cite « Kneading 90° » → DOIT être bloquée."""
    cfg = _cfg_conveying_and_kneading60()
    txt = "Substituer 2 × Kneading 90° par 2 × Kneading 45° (zone centrale)."
    assert recommendation_cites_absent_element(txt, cfg) is True


def test_manager_scenario_kneading45_also_blocked():
    """Même profil : la reco mentionne aussi Kneading 45° (type 8 absent)."""
    cfg = _cfg_conveying_and_kneading60()
    txt = "Substituer 2 × Kneading 90° par 2 × Kneading 45°."
    assert recommendation_cites_absent_element(txt, cfg) is True


def test_kneading30_also_blocked_when_absent():
    """Reco qui propose d'ajouter Kneading 30° alors que type 5 absent."""
    cfg = _cfg_conveying_and_kneading60()
    txt = "Ajouter 2 × Kneading 30° pour distributif."
    assert recommendation_cites_absent_element(txt, cfg) is True


def test_kneading60_not_blocked_when_present():
    """Le profil contient Kneading 60° → mentionner « Kneading 60° » est OK."""
    cfg = _cfg_conveying_and_kneading60()
    txt = "Maintenir les Kneading 60° en place pour homogénéité."
    assert recommendation_cites_absent_element(txt, cfg) is False


# ---------------------------------------------------------------------------
# 2 — Avant correctif : token collectif "kneading" laissait passer
# ---------------------------------------------------------------------------
def test_collective_kneading_still_works_when_any_kneading_present():
    """Une reco générique « ajouter du kneading » DOIT passer si AU MOINS un
    angle kneading est présent (token collectif). Le token spécifique est
    additionnel, pas substitutif."""
    cfg = _cfg_conveying_and_kneading60()      # contient type 7 (kneading)
    txt = "Réduire le kneading global pour limiter le cisaillement."
    assert recommendation_cites_absent_element(txt, cfg) is False


def test_collective_kneading_blocked_when_no_kneading_at_all():
    """Profil convoyage SEUL : aucune mention « kneading » ne doit passer."""
    cfg = _cfg_conveying_only()
    txt = "Ajouter du kneading pour mélanger."
    assert recommendation_cites_absent_element(txt, cfg) is True


# ---------------------------------------------------------------------------
# 3 — Couverture exhaustive : chaque angle de kneading filtré séparément
# ---------------------------------------------------------------------------
def test_each_kneading_angle_blocked_when_its_type_absent():
    """Profil sans aucun kneading : 90/45/30/60 doivent TOUS être bloqués."""
    cfg = _cfg_conveying_only()
    for angle in ("90", "45", "30", "60"):
        txt = f"Ajouter 2 × Kneading {angle}°."
        assert recommendation_cites_absent_element(txt, cfg) is True, angle


def test_kneading90_authorized_when_present():
    """Si Kneading 90° (type 4) est présent, la reco l'utilisant passe."""
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)
    add_elements_atomic(cfg, 4, 2)   # Kneading 90°
    txt = "Réduire les Kneading 90° à 1 unique."
    assert recommendation_cites_absent_element(txt, cfg) is False


def test_kneading_collision_french_english_tokens():
    """Le filtre est insensible à la langue : « malaxage 90° » FR équivalent EN."""
    cfg = _cfg_conveying_and_kneading60()
    assert recommendation_cites_absent_element(
        "Substituer 2 × Malaxage 90° par...", cfg,
    ) is True
    assert recommendation_cites_absent_element(
        "Substituer 2 × kneading 90° par...", cfg,
    ) is True


# ---------------------------------------------------------------------------
# 4 — Table de tokens : invariants
# ---------------------------------------------------------------------------
def test_specific_kneading_tokens_present_in_table():
    """Les 8 tokens d'angle (4 angles × 2 langues) doivent exister dans la
    table. Sinon le filtre redevient trop laxiste."""
    tokens = {tok for tok, _ in ELEMENT_MENTION_TOKENS}
    required = {
        "kneading 90", "kneading 45", "kneading 60", "kneading 30",
        "malaxage 90", "malaxage 45", "malaxage 60", "malaxage 30",
    }
    missing = required - tokens
    assert not missing, f"Tokens d'angle manquants dans ELEMENT_MENTION_TOKENS : {missing}"


def test_collective_kneading_tokens_still_present():
    """Les tokens collectifs (kneading/malaxage seul) doivent rester pour
    couvrir les recos génériques."""
    tokens = {tok for tok, _ in ELEMENT_MENTION_TOKENS}
    assert "kneading" in tokens
    assert "malaxage" in tokens


# ---------------------------------------------------------------------------
# 5 — Intégration : screw_render.compute_recommendations filtre correctement
# ---------------------------------------------------------------------------
def test_compute_recommendations_no_invented_kneading():
    """Test E2E sur la chaîne réelle Profile/Supervision (commentaire haut-gauche).
    Profil manager (convoyage + Kneading 60°) — aucune reco produite ne doit
    citer Kneading 90° ou Kneading 45° (types absents)."""
    from screw_logic import (
        MAIN_FEEDER_POSITION,
        N_POSITIONS,
        TIP_PART1_POS,
        base_type,
        is_part2,
        position_to_zone,
        fill_factor_average,
    )
    from screw_render import compute_recommendations

    cfg = _cfg_conveying_and_kneading60()
    recs = compute_recommendations(
        cfg, rpm=120.0, feed=8.5, dens=0.55,
        base_type_fn=base_type, is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    forbidden_substrings = ("kneading 90", "kneading 45", "malaxage 90", "malaxage 45")
    for r in recs:
        blob = " ".join(
            str(r.get(k, "")) for k in ("physics", "impact", "action", "title", "detail")
        ).lower()
        for token in forbidden_substrings:
            assert token not in blob, (
                f"Reco cite « {token} » alors qu'aucun élément de cet angle "
                f"n'est dans le profil : {r}"
            )


def test_agent_recommendations_no_invented_kneading():
    """Même garantie côté AgentIndustrial_v1.core.recommendations.evaluate."""
    from AgentIndustrial_v1.core.process import ProcessState
    from AgentIndustrial_v1.core.recommendations import build_recommendations
    from AgentIndustrial_v1.core.rules import evaluate

    cfg = _cfg_conveying_and_kneading60()
    state = ProcessState(screw_config=cfg, screw_rpm=240.0)   # rpm élevé → SME high
    # Pousser les conditions qui déclenchent REC_SOFTEN_PROFILE.
    for z in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"):
        state.zone_temps_C[z] = 200.0
    report = evaluate(state)
    recos = build_recommendations(state, report.alerts)
    forbidden = ("kneading 90", "kneading 45", "malaxage 90", "malaxage 45")
    for r in recos:
        blob = " ".join((r.title, r.rationale, r.action, r.delta_label)).lower()
        for tok in forbidden:
            assert tok not in blob, (
                f"Agent IA cite « {tok} » alors qu'aucun élément de cet angle "
                f"n'est dans le profil opérateur : {r.code} → {r.action}"
            )
