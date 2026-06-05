"""
End-to-end test : Settings → Enregistrer → Supervision conserve la config.

Reproduit le scénario validé par Maël (2026-05-20) :
  1. ouvrir Settings
  2. cliquer "Enregistrer la configuration"
  3. vérifier zéro erreur
  4. naviguer vers Supervision
  5. vérifier que la configuration enregistrée est conservée

Lance via :
    python -m pytest tests/test_settings_e2e.py -v
    ou directement : python tests/test_settings_e2e.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr (Windows console défaut = cp1252 → emoji ✓ casse).
# UNIQUEMENT en exécution directe : sous pytest, `sys.stdout` est l'objet de
# capture ; remplacer son `.buffer` fermerait ce dernier au teardown global
# (« I/O operation on closed file ») et casserait toute la session.
if sys.platform == "win32" and __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from streamlit.testing.v1 import AppTest

SETTINGS_PATH = ROOT / "app" / "pages" / "2_Settings.py"
SUPERVISION_PATH = ROOT / "app" / "Supervision.py"


def _check_no_exception(at: AppTest, label: str) -> None:
    if at.exception:
        for e in at.exception:
            print(f"  ! {label} EXCEPTION : {e.value}")
        raise AssertionError(f"{label} a produit une exception Streamlit")
    if at.error:
        for e in at.error:
            print(f"  ! {label} ERROR : {e.value}")
        raise AssertionError(f"{label} a produit un st.error")


def test_settings_renders_without_exception() -> None:
    """Étape 1 : ouvrir Settings → 0 erreur rouge."""
    print("\n[1] Render initial /Settings")
    at = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at.run()
    _check_no_exception(at, "Render Settings")
    # Vérifie qu'au moins le bouton Enregistrer est présent → page rendue.
    has_button = any(b.key == "btn_apply_state" for b in at.button)
    assert has_button, "Bouton 'Enregistrer la configuration' absent — page incomplète"
    print("    OK — page Settings rendue sans erreur, bouton Enregistrer présent")


def _ss_get(at: AppTest, key: str, default=None):
    """Streamlit SafeSessionStateProxy n'expose pas `.get()` — wrapper sûr."""
    if key in at.session_state:
        return at.session_state[key]
    return default


def test_settings_click_enregistrer_writes_snapshot() -> None:
    """Étapes 2-3 : cliquer 'Enregistrer la configuration' → snapshot écrit, 0 erreur."""
    print("\n[2-3] Click 'Enregistrer la configuration'")
    at = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at.run()
    _check_no_exception(at, "Pre-click Settings")

    # Trouver le bouton "Enregistrer la configuration" par sa key.
    btn = None
    for b in at.button:
        if b.key == "btn_apply_state":
            btn = b
            break
    assert btn is not None, "Bouton 'Enregistrer la configuration' introuvable"
    print(f"    bouton trouvé : '{btn.label}'")

    btn.click().run()
    _check_no_exception(at, "Post-click Settings")

    # Le snapshot doit maintenant exister dans session_state.
    snap = _ss_get(at, "applied_state")
    assert snap is not None, "applied_state non écrit après clic Enregistrer"
    print(f"    OK — snapshot écrit (label='{snap.label}', timestamp='{snap.timestamp_iso}')")

    history = _ss_get(at, "applied_history", [])
    assert len(history) >= 1, "Historique vide après commit"
    print(f"    OK — historique contient {len(history)} snapshot(s)")
    return snap


def test_supervision_reads_snapshot() -> None:
    """Étapes 4-5 : Supervision reflète bien le snapshot enregistré dans Settings."""
    print("\n[4-5] Settings (modifs + Enregistrer) puis Supervision")
    # On commence par Settings, on modifie la consigne Z5, on enregistre.
    at1 = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at1.run()
    _check_no_exception(at1, "Pre-modif Settings")

    # Modifier la consigne Z5 via session_state direct (Streamlit AppTest).
    at1.session_state["th_Z5"] = 132.0  # consigne distincte du défaut (95.0)
    at1.run()
    _check_no_exception(at1, "Apres modif Z5")

    # Enregistrer.
    btn = next((b for b in at1.button if b.key == "btn_apply_state"), None)
    assert btn is not None
    btn.click().run()
    _check_no_exception(at1, "Apres click Enregistrer")

    snap = _ss_get(at1, "applied_state")
    assert snap is not None, "applied_state absent"
    assert abs(snap.zone_temps_C.get("Z5", 0) - 132.0) < 0.01, \
        f"Z5 du snapshot != 132 °C ({snap.zone_temps_C.get('Z5')})"
    print(f"    OK — snapshot inclut Z5={snap.zone_temps_C['Z5']:.1f} °C")

    # On simule la navigation vers Supervision en passant le session_state.
    at2 = AppTest.from_file(str(SUPERVISION_PATH), default_timeout=30)
    # Transférer le snapshot (st.session_state est partagé entre pages dans
    # l'app réelle ; AppTest isole chaque AppTest, donc on injecte).
    at2.session_state["applied_state"] = snap
    at2.session_state["applied_history"] = _ss_get(at1, "applied_history", [])
    at2.run()
    _check_no_exception(at2, "Supervision")

    # Vérifier que state_from_session lit bien le snapshot : on regarde le
    # ProcessState reconstruit par state_sync.
    from AgentIndustrial_v1.core.state_sync import state_from_session
    s = state_from_session(at2.session_state)
    assert abs(s.zone_temps_C.get("Z5", 0) - 132.0) < 0.01, \
        f"Supervision lit Z5={s.zone_temps_C.get('Z5')} (attendu 132)"
    print(f"    OK — Supervision lit Z5={s.zone_temps_C['Z5']:.1f} °C depuis le snapshot")
    print("    OK — la configuration enregistrée est CONSERVÉE entre les pages")


def test_settings_editing_does_not_erase_supervision() -> None:
    """Vérification anti-régression : modifier Settings APRÈS Enregistrer
    ne doit PAS modifier ce que voit Supervision tant qu'on n'a pas re-cliqué Enregistrer."""
    print("\n[anti-régression] Edition post-Enregistrer ne casse pas Supervision")
    at = AppTest.from_file(str(SETTINGS_PATH), default_timeout=30)
    at.run()
    at.session_state["th_Z5"] = 110.0
    at.run()
    # Enregistrer à 110.
    btn = next((b for b in at.button if b.key == "btn_apply_state"), None)
    btn.click().run()
    snap_v1 = at.session_state["applied_state"]
    assert snap_v1.zone_temps_C["Z5"] == 110.0

    # Modifier la consigne SANS cliquer Enregistrer.
    at.session_state["th_Z5"] = 200.0
    at.run()
    _check_no_exception(at, "Apres edit sans enregistrer")

    snap_v2 = at.session_state["applied_state"]
    assert snap_v2.zone_temps_C["Z5"] == 110.0, \
        f"Le snapshot a été corrompu par une édition non validée ! ({snap_v2.zone_temps_C['Z5']})"
    print("    OK — le snapshot enregistré n'est PAS écrasé par une édition non validée")

    # Et le state Supervision lit bien la version 110.
    from AgentIndustrial_v1.core.state_sync import state_from_session
    s = state_from_session(at.session_state)
    assert s.zone_temps_C["Z5"] == 110.0
    print("    OK — Supervision continue de lire la valeur enregistrée (110), pas l'édition (200)")


if __name__ == "__main__":
    test_settings_renders_without_exception()
    test_settings_click_enregistrer_writes_snapshot()
    test_supervision_reads_snapshot()
    test_settings_editing_does_not_erase_supervision()
    print("\n=== TOUS LES TESTS E2E PASSENT ===")
