"""tests/test_project_to_legacy_no_overwrite.py

Bug architectural critique (manager 2026-06-09) : `project_to_legacy` écrasait
systématiquement `screw_config`, `screw_rpm`, `bulk_density` et `feeder_g_per_min`
depuis le snapshot validé à CHAQUE appel. Or `sync_legacy_projection` est appelé
en fin de chaque rerun de Profile → toute édition utilisateur (ajout/retrait
d'élément, modification de RPM ou densité) était silencieusement annulée au
rerun suivant. L'opérateur croyait que les boutons +/− et inputs étaient figés
après sauvegarde.

Repro pure-Python : snapshot=5 éléments → +2 par l'utilisateur (session=7) →
sync_legacy_projection → session retombe à 5.

Correctif : `project_to_legacy` devient setdefault-only — n'écrit JAMAIS sur
une clé déjà présente en session. Cohérent avec `restore_operator_state` et
`seed_editing_keys`.

Ces tests VERROUILLENT le contrat : toute régression future qui réintroduirait
l'écrasement sera détectée.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402

from AgentIndustrial_v1.core.applied_state import commit as applied_commit  # noqa: E402
from AgentIndustrial_v1.core.editing_state import (  # noqa: E402
    build_state_from_widgets,
    seed_editing_keys,
)
from screw_logic import (  # noqa: E402
    add_elements_atomic,
    count_user_elements,
    new_empty_configuration,
)
from run_state_adapter import (  # noqa: E402
    build,
    project_to_legacy,
    sync_legacy_projection,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _commit_snapshot(sess: dict, n_elements: int) -> None:
    """Sauvegarde un snapshot validé contenant `n_elements` éléments convoyage."""
    seed_editing_keys(sess)
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, n_elements)
    sess["screw_config"] = cfg
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label=f"snap_{n_elements}")


# ---------------------------------------------------------------------------
# 1 — Contrat : setdefault-only (n'écrit JAMAIS une clé existante)
# ---------------------------------------------------------------------------
def test_project_to_legacy_does_not_overwrite_screw_config():
    """REPRO du bug Pb #2 manager — l'utilisateur édite Profile après une
    sauvegarde, sync_legacy_projection ne doit PAS annuler l'édition."""
    sess: dict = {}
    _commit_snapshot(sess, n_elements=5)
    # Édition utilisateur (boutons +1/+4 → mutation en place de la liste).
    add_elements_atomic(sess["screw_config"], 7, 2)
    n_before = count_user_elements(sess["screw_config"])
    assert n_before == 7.0, "préparation du test : édition non effective"

    # Le coeur du bug : sync_legacy_projection ne doit PAS écraser.
    sync_legacy_projection(sess)
    n_after = count_user_elements(sess["screw_config"])
    assert n_after == 7.0, (
        f"sync_legacy_projection a écrasé l'édition Profile : "
        f"avant={n_before}, après={n_after}, snapshot=5"
    )


def test_project_to_legacy_does_not_overwrite_screw_rpm():
    """Même contrat pour screw_rpm : édition Profile (200) ne doit pas être
    annulée par snapshot (120 par défaut)."""
    sess: dict = {"screw_rpm": 120.0, "fd_en_1": True, "fd_flow_1": 30.0}
    seed_editing_keys(sess)
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap_120")
    # L'utilisateur édite screw_rpm dans Profile.
    sess["screw_rpm"] = 200.0
    sync_legacy_projection(sess)
    assert sess["screw_rpm"] == 200.0, (
        f"sync_legacy_projection a écrasé screw_rpm : 200 → {sess['screw_rpm']}"
    )


def test_project_to_legacy_does_not_overwrite_bulk_density():
    """Même contrat pour bulk_density."""
    sess: dict = {"bulk_density": 0.55, "fd_en_1": True, "fd_flow_1": 30.0}
    seed_editing_keys(sess)
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap_055")
    sess["bulk_density"] = 0.80
    sync_legacy_projection(sess)
    assert sess["bulk_density"] == 0.80


def test_project_to_legacy_does_not_overwrite_feeder_g_per_min_when_calibrated():
    """Même contrat pour feeder_g_per_min, même quand l'étalonnage est
    calibré. C'est `project_shared_keys` (côté Settings après commit) qui
    écrit cette clé depuis l'état édité, JAMAIS project_to_legacy quand la
    clé existe déjà."""
    sess: dict = {
        "feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 2.5,
        "fd_en_1": True, "feeder_g_per_min": 12.0,   # valeur Profile saisie
    }
    seed_editing_keys(sess)
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap_calib")
    sess["feeder_g_per_min"] = 12.0   # l'opérateur force une valeur Profile
    sync_legacy_projection(sess)
    assert sess["feeder_g_per_min"] == 12.0


# ---------------------------------------------------------------------------
# 2 — Comportement préservé : initialise les clés absentes (premier boot)
# ---------------------------------------------------------------------------
def test_project_to_legacy_initializes_when_keys_absent():
    """Cas d'usage légitime : refresh navigateur / session purgée → les clés
    legacy sont absentes → project_to_legacy doit les initialiser depuis le
    snapshot validé."""
    sess: dict = {"fd_en_1": True, "fd_flow_1": 30.0}
    _commit_snapshot(sess, n_elements=5)

    # Simule un refresh navigateur : on retire les clés legacy non-widget.
    for k in ("screw_config", "screw_rpm", "bulk_density", "feeder_g_per_min"):
        sess.pop(k, None)

    # build_current_run_state lit le snapshot, project_to_legacy initialise.
    crs = build(sess)
    project_to_legacy(crs, sess)
    assert "screw_config" in sess
    assert count_user_elements(sess["screw_config"]) == 5.0
    assert "screw_rpm" in sess
    assert sess["screw_rpm"] > 0.0
    assert "bulk_density" in sess
    assert sess["bulk_density"] > 0.0


def test_project_to_legacy_idempotent_when_keys_already_present():
    """Double appel idempotent : les valeurs ne dérivent jamais."""
    sess: dict = {}
    _commit_snapshot(sess, n_elements=5)
    add_elements_atomic(sess["screw_config"], 7, 3)
    sess["screw_rpm"] = 180.0
    sess["bulk_density"] = 0.72

    sync_legacy_projection(sess)
    cfg1 = list(sess["screw_config"])
    rpm1 = sess["screw_rpm"]
    dens1 = sess["bulk_density"]

    sync_legacy_projection(sess)
    sync_legacy_projection(sess)
    assert list(sess["screw_config"]) == cfg1
    assert sess["screw_rpm"] == rpm1
    assert sess["bulk_density"] == dens1


# ---------------------------------------------------------------------------
# 3 — Non-régression : Settings continue à propager après commit
# ---------------------------------------------------------------------------
def test_settings_commit_flow_still_propagates_to_legacy():
    """Settings : project_shared_keys écrit depuis state édité, sync_legacy_projection
    est idempotent ensuite. Le cas après-commit doit donc rester fonctionnel."""
    from AgentIndustrial_v1.core.editing_state import project_shared_keys
    sess: dict = {"fd_en_1": True, "fd_flow_1": 30.0}
    seed_editing_keys(sess)
    # Édition Settings.
    sess["ni_rpm_hmi"] = 180.0
    sess["fd_dens_1"] = 0.72
    state = build_state_from_widgets(sess)
    # 1. project_shared_keys écrit depuis state édité.
    project_shared_keys(sess, state)
    # 2. Settings clique Enregistrer → commit.
    applied_commit(sess, state, label="post-commit")
    # 3. sync_legacy_projection (best-effort, idempotent).
    sync_legacy_projection(sess)
    # Les valeurs sont celles éditées (écrites par project_shared_keys), pas
    # un défaut du snapshot.
    assert abs(sess["screw_rpm"] - 180.0) < 1e-6
    assert abs(sess["bulk_density"] - 0.72) < 1e-6


# ---------------------------------------------------------------------------
# 4 — Repro architecturale : édition Profile à travers N reruns successifs
# ---------------------------------------------------------------------------
def test_profile_edits_survive_repeated_sync_calls():
    """Profile rerun N fois (clic +1 → rerun → +1 → rerun...) : chaque édition
    doit cumuler, jamais être annulée par sync_legacy_projection."""
    sess: dict = {}
    _commit_snapshot(sess, n_elements=3)
    # Simule 5 clics +1 successifs avec rerun (sync_legacy_projection entre chaque).
    for i in range(5):
        add_elements_atomic(sess["screw_config"], 1, 1)
        sync_legacy_projection(sess)
    assert count_user_elements(sess["screw_config"]) == 8.0


# ---------------------------------------------------------------------------
# 5 — Edge case : valeur "vide" en session (None, 0, [])
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("legacy_key", ["screw_rpm", "bulk_density"])
def test_setdefault_logic_respects_explicit_zero(legacy_key):
    """Si l'utilisateur a EXPLICITEMENT mis 0 dans une clé legacy, on ne la
    surcharge pas. Le contrat est strict : clé présente = pas écrasée.
    (L'utilisateur peut volontairement réinitialiser à 0 ; si on le voulait
    différemment, ce serait un autre contrat, à expliciter.)"""
    sess: dict = {"fd_en_1": True, "fd_flow_1": 30.0}
    seed_editing_keys(sess)
    state = build_state_from_widgets(sess)
    applied_commit(sess, state, label="snap")
    sess[legacy_key] = 0.0
    sync_legacy_projection(sess)
    assert sess[legacy_key] == 0.0
