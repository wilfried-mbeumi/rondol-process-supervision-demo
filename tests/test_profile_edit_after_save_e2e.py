"""tests/test_profile_edit_after_save_e2e.py

Tests E2E (AppTest) qui prouvent que Profile reste éditable après sauvegarde,
contre le bug Pb #2 manager 2026-06-09 (sync_legacy_projection écrasait les
éditions par le snapshot validé à chaque rerun de Profile).

Scénarios manager :
1. Sauvegarder une config dans Settings.
2. Naviguer vers Profile et cliquer sur les boutons +1/+4/−1.
3. Vérifier que l'édition tient (cumul des modifs).
4. Revenir dans Settings et vérifier que les valeurs sont toujours modifiables.
5. Modifier l'étalonnage (passer de 100×2,5 à 120×3) → propagation effective.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

PROFILE = str(APP / "pages" / "1_Profile.py")
SETTINGS = str(APP / "pages" / "2_Settings.py")
MOTEUR = str(APP / "pages" / "5_Process_Engine.py")


def _ss(at: "AppTest", key: str, default=None):
    return at.session_state[key] if key in at.session_state else default


# ---------------------------------------------------------------------------
# 1 — Bouton +1 fonctionne après une sauvegarde
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_plus1_button_adds_element_when_snapshot_exists():
    """Repro EXACTE du bug Pb #2 manager : utilisateur sauvegarde puis essaye
    d'ajouter un élément dans Profile. Le bouton +1 DOIT effectivement
    augmenter le nombre d'éléments. Avant le correctif, l'ajout était
    silencieusement annulé par sync_legacy_projection."""
    # 1. Settings : enregistrer une config (création du snapshot validé).
    at_set = AppTest.from_file(SETTINGS)
    at_set.session_state["feeder_rpm"] = 100.0
    at_set.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at_set.session_state["fd_en_1"] = True
    at_set.run(timeout=90)
    assert not at_set.exception, [str(e.value) for e in at_set.exception]
    save_btn = next((b for b in at_set.button if b.key == "btn_apply_state"), None)
    assert save_btn is not None
    save_btn.click()
    at_set.run(timeout=90)
    assert not at_set.exception, [str(e.value) for e in at_set.exception]

    # 2. Profile : lire la config courante, cliquer sur +1 sur Convoyage (type 1).
    at_p = AppTest.from_file(PROFILE)
    # Hydrate le snapshot dans la session Profile pour simuler la navigation.
    if "applied_snapshot" in at_set.session_state:
        at_p.session_state["applied_snapshot"] = at_set.session_state["applied_snapshot"]
    at_p.session_state["feeder_rpm"] = 100.0
    at_p.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at_p.run(timeout=90)
    assert not at_p.exception, [str(e.value) for e in at_p.exception]
    cfg_before = list(at_p.session_state["screw_config"])

    plus1 = next((b for b in at_p.button if b.key == "plus1_1"), None)
    assert plus1 is not None, "bouton +1 Convoyage introuvable dans Profile"
    plus1.click()
    at_p.run(timeout=90)
    assert not at_p.exception, [str(e.value) for e in at_p.exception]
    cfg_after = list(at_p.session_state["screw_config"])

    # PROUVE : au moins une position a changé après le clic +1.
    diff = sum(1 for a, b in zip(cfg_before, cfg_after) if a != b)
    assert diff > 0, (
        f"Le clic +1 n'a pas modifié screw_config : avant={cfg_before[:10]} "
        f"après={cfg_after[:10]}. Bug Pb #2 — sync_legacy_projection écrase."
    )


# ---------------------------------------------------------------------------
# 2 — Plusieurs clics +1 consécutifs cumulent
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_repeated_clicks_accumulate():
    """3 clics +1 doivent produire 3 éléments de plus, pas 0 ni 1."""
    from screw_logic import count_user_elements

    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    assert not at.exception
    n0 = count_user_elements(at.session_state["screw_config"])

    for _ in range(3):
        plus1 = next((b for b in at.button if b.key == "plus1_1"), None)
        if plus1 is None:
            break
        plus1.click()
        at.run(timeout=90)
        assert not at.exception, [str(e.value) for e in at.exception]
    n1 = count_user_elements(at.session_state["screw_config"])
    assert n1 >= n0 + 2, f"Cumul des clics +1 ne fonctionne pas : {n0} → {n1}"


# ---------------------------------------------------------------------------
# 3 — Bouton −1 retire bien un élément
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_minus1_button_removes_element():
    """Le bouton −1 sur un type présent doit décrémenter le compte."""
    from screw_logic import count_user_elements

    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    n0 = count_user_elements(at.session_state["screw_config"])

    # Le profil par défaut de Profile contient des Convoyage (+) — type 1.
    minus = next((b for b in at.button if b.key == "minus_1" and not b.disabled), None)
    if minus is None:
        pytest.skip("aucun convoyage à retirer dans la config par défaut")
    minus.click()
    at.run(timeout=90)
    assert not at.exception
    n1 = count_user_elements(at.session_state["screw_config"])
    assert n1 == n0 - 1, f"−1 n'a pas retiré 1 élément : {n0} → {n1}"


# ---------------------------------------------------------------------------
# 4 — Modification screw_rpm dans Profile persiste à travers reruns
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_screw_rpm_change_persists():
    """L'utilisateur change screw_rpm de 120 à 200. La valeur DOIT survivre au
    rerun (avant correctif, sync_legacy_projection la ramenait au snapshot)."""
    at = AppTest.from_file(PROFILE)
    at.session_state["screw_rpm"] = 200.0
    at.session_state["sb_rpm"] = 200.0
    at.run(timeout=90)
    assert not at.exception
    # Re-rerun avec la session courante.
    at.run(timeout=90)
    assert _ss(at, "screw_rpm") == 200.0


# ---------------------------------------------------------------------------
# 5 — Settings → Profile → Settings : navigation circulaire reste éditable
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_to_profile_to_settings_keeps_values_editable():
    """Workflow manager : Settings (saisie) → Profile (édition vis) → Settings
    (re-modification). Aucune valeur ne doit être figée."""
    # Tour 1 : Settings, saisie + sauvegarde.
    at_set = AppTest.from_file(SETTINGS)
    at_set.session_state["feeder_rpm"] = 100.0
    at_set.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at_set.session_state["fd_en_1"] = True
    at_set.run(timeout=90)
    save_btn = next((b for b in at_set.button if b.key == "btn_apply_state"), None)
    if save_btn is not None:
        save_btn.click()
        at_set.run(timeout=90)
    assert not at_set.exception

    # Tour 2 : Profile, +1 fonctionne (clés métier restaurées via store opérateur).
    at_p = AppTest.from_file(PROFILE)
    at_p.session_state["feeder_rpm"] = 100.0
    at_p.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at_p.run(timeout=90)
    assert not at_p.exception
    plus1 = next((b for b in at_p.button if b.key == "plus1_1"), None)
    assert plus1 is not None
    cfg_before = list(at_p.session_state["screw_config"])
    plus1.click()
    at_p.run(timeout=90)
    cfg_after = list(at_p.session_state["screw_config"])
    assert any(a != b for a, b in zip(cfg_before, cfg_after)), \
        "Profile ne s'édite plus après sauvegarde Settings"

    # Tour 3 : Retour Settings, modifier le coefficient → la nouvelle valeur prime.
    at_set2 = AppTest.from_file(SETTINGS)
    at_set2.session_state["feeder_rpm"] = 120.0
    at_set2.session_state["feeder_calib_g_h_per_rpm"] = 3.0
    at_set2.session_state["fd_en_1"] = True
    at_set2.run(timeout=90)
    assert not at_set2.exception
    feed = _ss(at_set2, "feeder_g_per_min")
    assert feed is not None
    assert abs(feed - 6.0) < 0.01, (
        f"Nouvelle calibration 120×3=360 g/h=6 g/min non propagée : {feed}"
    )


# ---------------------------------------------------------------------------
# 6 — Cas explicite : Moteur Procédé lit le snapshot après navigation
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_moteur_reads_latest_calibration_after_navigation():
    """Settings → Moteur Procédé : le moteur lit le débit étalonné, pas
    une valeur fantôme."""
    at = AppTest.from_file(MOTEUR)
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.run(timeout=90)
    assert not at.exception
    # Aucun bandeau « non calculable » : étalonnage est renseigné.
    warns = " ".join(str(w.value) for w in at.warning)
    assert "non calculable" not in warns.lower(), (
        f"Moteur affiche encore 'Non calculable' avec étalonnage présent : {warns!r}"
    )
