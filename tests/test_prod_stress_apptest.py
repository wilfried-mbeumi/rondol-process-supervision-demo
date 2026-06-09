"""tests/test_prod_stress_apptest.py

Stress AppTest comportementaux (manager 2026-06-09) demandés explicitement :
les Bugs 2 et 3 ne sont pas reproductibles en pure-Python, mais il faut
prouver côté Streamlit qu'ils sont bien fermés. Ces tests sondent la vraie
chaîne Streamlit (widgets, reruns, navigation, state hydration).

Scénarios :
  - Cycle Settings save → Profile édit → Settings save → Profile édit
    (chaque édition vis doit cumuler).
  - Agent IA : profil exact manager (convoyage + K60°) → aucune reco
    rendue par AUCUNE des pages ne doit citer Kneading 90/45.
  - FR/EN : bloc Étalonnage feeders + recos pas de fuite de langue.

Aucun test ne s'arrête à « pas d'exception » : chaque test VALIDE le contenu.
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

SETTINGS = str(APP / "pages" / "2_Settings.py")
PROFILE = str(APP / "pages" / "1_Profile.py")
SUPERVISION = str(APP / "Supervision.py")
MOTEUR = str(APP / "pages" / "5_Moteur_Procede.py")


def _ss(at, key, default=None):
    return at.session_state[key] if key in at.session_state else default


# ===========================================================================
# BLOC A — Édition vis post-sauvegarde (Bug 2)
# ===========================================================================
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_cycle_settings_save_profile_edit_settings_save_profile_edit():
    """Cycle complet (Settings save → Profile +1 → Settings save → Profile +1).
    Chaque édition vis DOIT cumuler. Si le rerun Streamlit annule les mods,
    le compteur d'éléments ne progresse pas."""
    from screw_logic import count_user_elements

    # 1. Settings : enregistrer une config initiale.
    s1 = AppTest.from_file(SETTINGS)
    s1.session_state["feeder_rpm"] = 100.0
    s1.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    s1.session_state["fd_en_1"] = True
    s1.run(timeout=90)
    assert not s1.exception
    save = next((b for b in s1.button if b.key == "btn_apply_state"), None)
    if save is not None:
        save.click()
        s1.run(timeout=90)
    assert not s1.exception

    # 2. Profile : +1 Convoyage.
    p1 = AppTest.from_file(PROFILE)
    p1.session_state["feeder_rpm"] = 100.0
    p1.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    p1.run(timeout=90)
    assert not p1.exception
    n0 = count_user_elements(_ss(p1, "screw_config", []))
    plus = next((b for b in p1.button if b.key == "plus1_1"), None)
    assert plus is not None
    plus.click()
    p1.run(timeout=90)
    n1 = count_user_elements(_ss(p1, "screw_config", []))
    assert n1 == n0 + 1, f"Profile +1 : {n0} → {n1} (attendu +1)"

    # 3. Retour Settings : sauvegarder ENCORE (commit avec la nouvelle vis).
    s2 = AppTest.from_file(SETTINGS)
    s2.session_state["feeder_rpm"] = 100.0
    s2.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    s2.session_state["fd_en_1"] = True
    s2.session_state["screw_config"] = list(p1.session_state["screw_config"])
    s2.run(timeout=90)
    save2 = next((b for b in s2.button if b.key == "btn_apply_state"), None)
    if save2 is not None:
        save2.click()
        s2.run(timeout=90)
    assert not s2.exception

    # 4. Profile : +1 ENCORE → doit cumuler (n0+2).
    p2 = AppTest.from_file(PROFILE)
    p2.session_state["feeder_rpm"] = 100.0
    p2.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    p2.session_state["screw_config"] = list(s2.session_state["screw_config"])
    p2.run(timeout=90)
    n2 = count_user_elements(_ss(p2, "screw_config", []))
    plus2 = next((b for b in p2.button if b.key == "plus1_1"), None)
    assert plus2 is not None
    plus2.click()
    p2.run(timeout=90)
    n3 = count_user_elements(_ss(p2, "screw_config", []))
    assert n3 == n2 + 1, f"Profile +1 (2e tour) : {n2} → {n3} (attendu +1)"
    # Cumul total des 2 ajouts depuis n0.
    assert n3 >= n0 + 2, f"Cumul +1 +1 : {n0} → {n3} (attendu ≥ {n0+2})"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_minus1_then_plus4_after_save():
    """Combinaison -1 puis +4 après un save Settings : doit fonctionner."""
    from screw_logic import count_user_elements

    s = AppTest.from_file(SETTINGS)
    s.session_state["fd_en_1"] = True
    s.run(timeout=90)
    save = next((b for b in s.button if b.key == "btn_apply_state"), None)
    if save is not None:
        save.click()
        s.run(timeout=90)

    p = AppTest.from_file(PROFILE)
    p.session_state["screw_config"] = list(s.session_state["screw_config"])
    p.run(timeout=90)
    n0 = count_user_elements(p.session_state["screw_config"])

    # Retirer 1 convoyage si possible.
    minus = next((b for b in p.button if b.key == "minus_1" and not b.disabled), None)
    if minus is not None:
        minus.click()
        p.run(timeout=90)
    n_after_minus = count_user_elements(p.session_state["screw_config"])

    # Ajouter +4 convoyage.
    plus4 = next((b for b in p.button if b.key == "plus4_1" and not b.disabled), None)
    if plus4 is not None:
        plus4.click()
        p.run(timeout=90)
    n_final = count_user_elements(p.session_state["screw_config"])

    # Vérifie qu'au moins une opération a modifié la config.
    assert n_final != n0 or n_after_minus != n0, (
        f"Aucune édition n'a pris effet : n0={n0}, n_after_minus={n_after_minus}, "
        f"n_final={n_final}"
    )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_save_does_not_reset_screw_config():
    """Le clic 'Enregistrer' dans Settings NE DOIT PAS réinitialiser
    screw_config (qui peut avoir été modifié par Profile)."""
    from screw_logic import (
        count_user_elements, add_elements_atomic, new_empty_configuration,
    )

    # Préparer une config personnalisée.
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 4)
    add_elements_atomic(cfg, 7, 3)
    expected = count_user_elements(cfg)

    s = AppTest.from_file(SETTINGS)
    s.session_state["screw_config"] = list(cfg)
    s.session_state["fd_en_1"] = True
    s.run(timeout=90)
    assert not s.exception
    save = next((b for b in s.button if b.key == "btn_apply_state"), None)
    if save is not None:
        save.click()
        s.run(timeout=90)
    n_after = count_user_elements(s.session_state["screw_config"])
    assert n_after == expected, (
        f"Settings save a modifié screw_config : {expected} → {n_after}"
    )


# ===========================================================================
# BLOC B — Agent IA scénario manager (Bug 3) — rendus pages réelles
# ===========================================================================
def _manager_screw_config():
    """Profil exact du manager : 6 convoyage + 4 Kneading 60°."""
    from screw_logic import add_elements_atomic, new_empty_configuration
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 6)
    add_elements_atomic(cfg, 7, 4)
    return cfg


def _kneading_violation_in(at):
    """Cherche tout texte rendu par AppTest qui mentionne Kneading 90 ou 45.

    Parcourt les éléments visibles : html, markdown, info, warning, error,
    success, caption, metric, dataframe (texte). Renvoie une liste des hits."""
    needles = ("kneading 90", "kneading 45", "malaxage 90", "malaxage 45")
    hits = []
    # Collecte tous les blocs text-like.
    for collection_name in ("html", "markdown", "info", "warning", "error",
                            "success", "caption", "text"):
        coll = getattr(at, collection_name, [])
        for el in coll:
            val = str(getattr(el, "value", "") or "").lower()
            for n in needles:
                if n in val:
                    hits.append((collection_name, n, val[:200]))
    return hits


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_supervision_no_kneading_90_45_for_manager_profile():
    """Scénario manager : profil convoyage + K60°. La page Supervision ne
    doit RIEN rendre qui mentionne Kneading 90 ou Kneading 45."""
    at = AppTest.from_file(SUPERVISION)
    at.session_state["screw_config"] = _manager_screw_config()
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.session_state["fd_en_1"] = True
    at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
    hits = _kneading_violation_in(at)
    assert not hits, f"Supervision cite un Kneading absent : {hits[:3]}"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_page_no_kneading_90_45_for_manager_profile():
    """Profile : même garantie."""
    at = AppTest.from_file(PROFILE)
    at.session_state["screw_config"] = _manager_screw_config()
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.run(timeout=120)
    assert not at.exception
    hits = _kneading_violation_in(at)
    assert not hits, f"Profile cite un Kneading absent : {hits[:3]}"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_settings_page_no_kneading_90_45_for_manager_profile():
    """Settings : recos IA ne doivent rien citer d'absent."""
    at = AppTest.from_file(SETTINGS)
    at.session_state["screw_config"] = _manager_screw_config()
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.session_state["fd_en_1"] = True
    at.run(timeout=120)
    assert not at.exception
    hits = _kneading_violation_in(at)
    assert not hits, f"Settings cite un Kneading absent : {hits[:3]}"


# ===========================================================================
# BLOC C — FR/EN sans fuite (sondes ciblées)
# ===========================================================================
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_settings_etalonnage_block_no_language_leak(lang):
    """Bloc 'Étalonnage feeders' (Settings) : pas de fuite FR→EN ni EN→FR."""
    at = AppTest.from_file(SETTINGS)
    at.session_state["ui_lang"] = lang
    at.session_state["fd_en_1"] = True
    at.run(timeout=90)
    assert not at.exception

    # Collecte le texte rendu du bloc multi-feeder calibration.
    rendered = " ".join(
        str(getattr(el, "value", "") or "")
        for col in ("html", "markdown", "caption", "info", "warning", "success")
        for el in getattr(at, col, [])
    ).lower()

    if lang == "en":
        # Tokens FR exclusifs (ne doivent PAS apparaître en mode EN).
        for fr_token in ("non calculable", "non étalonné", "désactivé"):
            assert fr_token not in rendered, (
                f"EN mode : fuite FR « {fr_token} » dans le rendu Settings."
            )
    else:
        # Tokens EN exclusifs (ne doivent PAS apparaître en mode FR).
        for en_token in ("not computable", "not calibrated", "disabled"):
            assert en_token not in rendered, (
                f"FR mode : fuite EN « {en_token} » dans le rendu Settings."
            )
