"""
Reproduction du bug fonctionnel signalé par Maël (2026-05-20) :

Scénario réel utilisateur :
  1. Z1 affiche 25 (défaut).
  2. L'opérateur tape 40 dans le widget Z1.
  3. L'opérateur clique « Enregistrer » SANS attendre un rerun intermédiaire
     (en pratique : Streamlit fusionne le commit de la valeur du number_input
     et le clic bouton dans un SEUL rerun).
  4. Bug : applied_state.zone_temps_C['Z1'] reste à 25 au lieu de 40.

Pourquoi ce test échoue (avant fix) :
  Dans le script Settings, le bouton « Enregistrer » est rendu AVANT la
  synchronisation `state.zone_temps_C[...] = st.session_state['th_*']`
  (lignes 218 vs 299-304). Au moment du clic dans le même rerun où la valeur
  Z1=40 vient d'être committée à session_state, `state.zone_temps_C['Z1']`
  contient encore 25 (héritage de la run précédente).
  → `applied_commit(state)` sérialise donc l'ANCIENNE valeur.

Le test précédent (test_settings_e2e.py) ne reproduisait pas le bug parce
qu'il appelait `at.run()` ENTRE la modification de session_state et le clic,
ce qui exécutait la sync intermédiaire. Ici on enchaîne directement, comme
le ferait l'opérateur en clavier-souris.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# UNIQUEMENT en exécution directe : sous pytest, remplacer le `.buffer` de
# l'objet de capture le fermerait au teardown (« I/O operation on closed file »).
if sys.platform == "win32" and __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from streamlit.testing.v1 import AppTest

SETTINGS_PATH = ROOT / "app" / "pages" / "2_Settings.py"
SUPERVISION_PATH = ROOT / "app" / "Supervision.py"


def _ss_get(at, key, default=None):
    if key in at.session_state:
        return at.session_state[key]
    return default


def _check_no_exception(at, label):
    if at.exception:
        for e in at.exception:
            print(f"  ! {label} EXCEPTION : {e.value}")
        raise AssertionError(f"{label} a produit une exception Streamlit")


def test_z1_modifie_puis_save_meme_rerun() -> None:
    """Z1=25 → tape 40 → clique Enregistrer (même rerun)
       → applied_state doit contenir Z1=40."""
    print("\n[REPRO] Z1 modifié puis Save dans le même rerun")
    at = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at.run()
    _check_no_exception(at, "Initial")

    # Vérifier que Z1 démarre à 25 (défaut).
    z1_init = _ss_get(at, "th_Z1")
    print(f"  Z1 initial = {z1_init}")
    assert abs(z1_init - 25.0) < 0.01, f"Z1 par défaut attendu 25, vu {z1_init}"

    # ----- L'opérateur tape 40 dans le number_input Z1, ET clique Enregistrer
    # sans rerun intermédiaire. On simule ça en mettant la valeur dans
    # session_state PUIS en cliquant directement (un seul .run()).
    at.session_state["th_Z1"] = 40.0
    btn = next((b for b in at.button if b.key == "btn_apply_state"), None)
    assert btn is not None, "Bouton Enregistrer introuvable"
    btn.click().run()
    _check_no_exception(at, "Post-click")

    snap = _ss_get(at, "applied_state")
    assert snap is not None, "applied_state non écrit"
    z1_saved = snap.zone_temps_C.get("Z1")
    print(f"  snapshot.Z1 = {z1_saved}")

    assert abs(z1_saved - 40.0) < 0.01, (
        f"BUG REPRODUIT : Z1 modifié à 40 mais snapshot contient {z1_saved}. "
        "La sync widget→state se fait APRÈS le bouton dans le script ; il faut "
        "lire les valeurs widget COURANTES de session_state au moment du clic."
    )
    print("  OK — Z1=40 correctement sauvegardé")


def test_scenario_complet_manager() -> None:
    """Scénario E2E exact demandé par le manager :

       1. Z1=25 initial
       2. Z1 → 40, click Enregistrer
       3. Vérifier Z1=40 après rerun
       4. Supervision lit Z1=40
       5. Z1 → 60 SANS enregistrer
       6. Supervision reste à 40
       7. Click Enregistrer
       8. Supervision passe à 60
    """
    print("\n[SCÉNARIO MANAGER] E2E complet")
    at = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at.run()
    _check_no_exception(at, "Init")

    # 1) état initial Z1=25
    assert abs(_ss_get(at, "th_Z1") - 25.0) < 0.01
    print("  [1] Z1=25 (défaut) — OK")

    # 2) modifier Z1=40 puis Save (même rerun)
    at.session_state["th_Z1"] = 40.0
    btn = next((b for b in at.button if b.key == "btn_apply_state"), None)
    btn.click().run()
    _check_no_exception(at, "Save#1")
    snap_v1 = _ss_get(at, "applied_state")
    assert snap_v1 is not None
    assert abs(snap_v1.zone_temps_C["Z1"] - 40.0) < 0.01, (
        f"[2] snapshot.Z1={snap_v1.zone_temps_C['Z1']} != 40"
    )
    print("  [2-3] Z1=40 enregistré dans applied_state — OK")

    # 3) après rerun, Settings doit afficher 40
    z1_after = _ss_get(at, "th_Z1")
    assert abs(z1_after - 40.0) < 0.01, f"[3] Settings affiche Z1={z1_after} (attendu 40)"
    print(f"  [3] Settings affiche Z1={z1_after} après rerun — OK")

    # 4) Supervision lit le snapshot Z1=40
    at_sup = AppTest.from_file(str(SUPERVISION_PATH), default_timeout=30)
    at_sup.session_state["applied_state"] = snap_v1
    at_sup.session_state["applied_history"] = _ss_get(at, "applied_history", [])
    at_sup.run()
    _check_no_exception(at_sup, "Supervision#1")
    from AgentIndustrial_v1.core.state_sync import state_from_session
    s = state_from_session(at_sup.session_state)
    assert abs(s.zone_temps_C["Z1"] - 40.0) < 0.01, (
        f"[4] Supervision lit Z1={s.zone_temps_C['Z1']} (attendu 40)"
    )
    print(f"  [4] Supervision lit Z1={s.zone_temps_C['Z1']} — OK")

    # 5) modifier Z1=60 SANS enregistrer
    at.session_state["th_Z1"] = 60.0
    at.run()
    _check_no_exception(at, "Edit#2 sans save")
    # 6) Supervision doit toujours lire 40 (snapshot pas modifié)
    snap_after_edit = _ss_get(at, "applied_state")
    assert abs(snap_after_edit.zone_temps_C["Z1"] - 40.0) < 0.01, (
        f"[6] Snapshot écrasé par édition non validée : "
        f"Z1={snap_after_edit.zone_temps_C['Z1']} (attendu 40)"
    )
    print("  [5-6] Edit Z1=60 SANS save : snapshot reste à 40 — OK")

    # 7) Cliquer Enregistrer
    btn = next((b for b in at.button if b.key == "btn_apply_state"), None)
    btn.click().run()
    _check_no_exception(at, "Save#2")
    snap_v2 = _ss_get(at, "applied_state")
    assert abs(snap_v2.zone_temps_C["Z1"] - 60.0) < 0.01, (
        f"[7] Save Z1=60 : snapshot contient Z1={snap_v2.zone_temps_C['Z1']}"
    )
    print(f"  [7] Save : snapshot.Z1 = {snap_v2.zone_temps_C['Z1']} — OK")

    # 8) Supervision passe à 60
    at_sup2 = AppTest.from_file(str(SUPERVISION_PATH), default_timeout=30)
    at_sup2.session_state["applied_state"] = snap_v2
    at_sup2.session_state["applied_history"] = _ss_get(at, "applied_history", [])
    at_sup2.run()
    _check_no_exception(at_sup2, "Supervision#2")
    s2 = state_from_session(at_sup2.session_state)
    assert abs(s2.zone_temps_C["Z1"] - 60.0) < 0.01, (
        f"[8] Supervision lit Z1={s2.zone_temps_C['Z1']} (attendu 60)"
    )
    print(f"  [8] Supervision lit Z1={s2.zone_temps_C['Z1']} — OK")
    print("\n=== SCÉNARIO MANAGER COMPLET — PASS ===")


def test_navigation_purge_widget_keys_then_back() -> None:
    """Régression : navigation Settings → autre page → Settings doit faire
    réapparaître le widget Z1 à la valeur ENREGISTRÉE (snapshot), pas au
    défaut statique (25 °C).

    Streamlit purge les clés session_state des widgets quand la page n'est
    plus rendue. Sans précaution, `setdefault('th_Z1', default_zone_target(...))`
    re-initialise Z1 à 25 même si le snapshot validé contient 40.

    On simule la purge en construisant une nouvelle AppTest avec un snapshot
    pré-injecté mais SANS les clés widget — équivalent au retour de navigation.
    """
    print("\n[NAV] Settings → purge widget keys → retour Settings")
    # 1) Premier passage : commit d'un snapshot avec Z1=40.
    at1 = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at1.run()
    at1.session_state["th_Z1"] = 40.0
    btn = next(b for b in at1.button if b.key == "btn_apply_state")
    btn.click().run()
    snap = _ss_get(at1, "applied_state")
    assert snap is not None and abs(snap.zone_temps_C["Z1"] - 40.0) < 0.01

    # 2) Nouvelle AppTest avec UNIQUEMENT le snapshot (pas les clés widget) :
    #    simulent l'état session_state après que Streamlit ait purgé les
    #    widgets de Settings sur navigation.
    at2 = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at2.session_state["applied_state"] = snap
    at2.session_state["applied_history"] = _ss_get(at1, "applied_history", [])
    at2.run()
    _check_no_exception(at2, "Retour Settings")
    z1 = _ss_get(at2, "th_Z1")
    print(f"  th_Z1 après retour = {z1}")
    assert abs(z1 - 40.0) < 0.01, (
        f"Bug navigation : th_Z1={z1} après retour, attendu 40 depuis snapshot. "
        "setdefault doit prioriser applied_state sur le défaut statique."
    )
    print("  OK — widget Z1 ré-initialisé depuis le snapshot, pas le défaut")


if __name__ == "__main__":
    test_z1_modifie_puis_save_meme_rerun()
    test_scenario_complet_manager()
    test_navigation_purge_widget_keys_then_back()
    print("\nOK — bug reproduit/validé selon état du code.")
