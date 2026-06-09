"""tests/test_phase_s1_profile_readonly.py

Phase S1 stabilisation produit (manager 2026-06-09).

Contrat S1 :
  - Profile NE saisit PLUS les widgets RPM / débit / densité (`sb_rpm`,
    `sb_feed`, `sb_dens`). Profile affiche ces valeurs en LECTURE SEULE
    (st.metric) avec un libellé « Pilotée depuis Settings ».
  - Profile reste la page d'édition du PROFIL DE VIS uniquement
    (boutons +1/+4/−1 sur les éléments).
  - Settings devient la SEULE source d'édition pour RPM / coefficient
    feeder / densité bulk.

Bénéfice mesurable : plus de double écriture concurrente sur
`screw_rpm` / `feeder_g_per_min` / `bulk_density`. Plus de désynchronisation
silencieuse après navigation. Édition vis post-sauvegarde reste fonctionnelle
(propriété déjà testée — vérifiée ici sans régression).
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


def _ss(at, key, default=None):
    return at.session_state[key] if key in at.session_state else default


# ---------------------------------------------------------------------------
# 1 — Profile ne crée plus de widget sb_rpm / sb_feed / sb_dens
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_no_longer_creates_sb_rpm_widget():
    """Profile n'écrit plus dans `screw_rpm` via un widget sb_rpm.
    Les valeurs viennent de Settings (clé widget `ni_rpm_hmi`)."""
    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    # Aucun widget number_input n'a la clé sb_rpm.
    for widget in at.number_input:
        assert widget.key != "sb_rpm", (
            "Profile contient encore le widget sb_rpm — la double saisie "
            "RPM (Profile + Settings) doit être supprimée par la phase S1."
        )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_no_longer_creates_sb_feed_widget():
    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    assert not at.exception
    for widget in at.number_input:
        assert widget.key != "sb_feed", (
            "Profile contient encore le widget sb_feed — l'étalonnage feeder "
            "doit se faire exclusivement dans Settings."
        )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_no_longer_creates_sb_dens_widget():
    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    assert not at.exception
    for widget in at.number_input:
        assert widget.key != "sb_dens", (
            "Profile contient encore le widget sb_dens — la saisie de la "
            "densité bulk doit se faire exclusivement dans Settings."
        )


# ---------------------------------------------------------------------------
# 2 — Lecture seule cohérente avec les valeurs Settings
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_displays_calibrated_flow_when_settings_calibrated():
    """Scénario manager : Settings RPM=100, coeff=2.5 → Profile affiche
    4,17 g/min (pas « Non calculable », pas une autre valeur)."""
    at = AppTest.from_file(PROFILE)
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.session_state["fd_en_1"] = True
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    # feeder_g_per_min est hydraté par sync_legacy_projection au boot.
    feed = _ss(at, "feeder_g_per_min")
    assert feed is not None
    assert abs(feed - 250.0 / 60.0) < 0.01, (
        f"Profile feeder_g_per_min = {feed} (attendu ≈ 4,17)"
    )


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_displays_not_computable_when_no_flow(tmp_path, monkeypatch):
    """Vraie session vierge (aucun mirror disque pollué par d'autres tests
    AppTest) : sans débit, Profile affiche 'Non calculable', jamais un faux 0.

    Le miroir disque opérateur peut contenir des résidus d'une session
    précédente — on l'isole via RONDOL_RUN_STATE_PATH pour ce test."""
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "isolated.json"))
    at = AppTest.from_file(PROFILE)
    at.session_state["feeder_rpm"] = 30.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 0.0
    at.session_state["feeder_g_per_min"] = 0.0   # session explicitement vide
    at.run(timeout=90)
    assert not at.exception
    metric_values = [str(getattr(m, "value", "")) for m in at.metric]
    has_not_computable = any(
        "Non calculable" in v or "Not computable" in v
        for v in metric_values
    )
    assert has_not_computable, (
        "Profile sans débit doit afficher 'Non calculable' pour le débit, "
        f"pas un faux 0. Métriques vues : {metric_values}"
    )


# ---------------------------------------------------------------------------
# 3 — Édition vis reste fonctionnelle (Pb #2 non régressé)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_plus1_still_works_after_s1():
    """Phase S1 ne casse pas l'édition vis. Bouton +1 Convoyage augmente
    bien le compteur d'éléments."""
    from screw_logic import count_user_elements

    at = AppTest.from_file(PROFILE)
    at.run(timeout=90)
    assert not at.exception
    n0 = count_user_elements(_ss(at, "screw_config", []))
    plus = next((b for b in at.button if b.key == "plus1_1"), None)
    assert plus is not None, "bouton +1 Convoyage introuvable"
    plus.click()
    at.run(timeout=90)
    n1 = count_user_elements(_ss(at, "screw_config", []))
    assert n1 == n0 + 1, f"S1 a cassé +1 : {n0} → {n1}"


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_profile_plus1_works_after_settings_calibration():
    """Scénario manager complet : calibration Settings + bouton +1 Profile
    doit toujours fonctionner. Aucun crash StreamlitValueBelowMinError."""
    from screw_logic import count_user_elements

    at = AppTest.from_file(PROFILE)
    at.session_state["feeder_rpm"] = 100.0
    at.session_state["feeder_calib_g_h_per_rpm"] = 2.5
    at.session_state["fd_en_1"] = True
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    n0 = count_user_elements(_ss(at, "screw_config", []))
    plus = next((b for b in at.button if b.key == "plus1_1"), None)
    assert plus is not None
    plus.click()
    at.run(timeout=90)
    assert not at.exception, [str(e.value) for e in at.exception]
    n1 = count_user_elements(_ss(at, "screw_config", []))
    assert n1 == n0 + 1


# ---------------------------------------------------------------------------
# 4 — Profile ne crashe pas sur valeurs limites (StreamlitValueBelowMinError)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("screw_rpm,bulk_density,feeder_g_per_min", [
    (0.0, 0.0, 0.0),    # tout à zéro
    (0.5, 0.05, 0.0),   # juste en-dessous des anciens min_value
    (3500.0, 6.0, 999.0),  # au-dessus des anciens max_value
])
def test_profile_no_crash_on_extreme_session_values(
    screw_rpm, bulk_density, feeder_g_per_min,
):
    """Avec les widgets sb_* supprimés, Profile ne devrait plus crasher sur
    des valeurs session aberrantes (avant S1, st.number_input(value=...)
    levait StreamlitValueBelowMinError si value < min_value)."""
    at = AppTest.from_file(PROFILE)
    at.session_state["screw_rpm"] = screw_rpm
    at.session_state["bulk_density"] = bulk_density
    at.session_state["feeder_g_per_min"] = feeder_g_per_min
    at.run(timeout=90)
    assert not at.exception, (
        f"Profile crash avec screw_rpm={screw_rpm}, "
        f"bulk_density={bulk_density}, feeder_g_per_min={feeder_g_per_min} : "
        f"{[str(e.value) for e in at.exception]}"
    )


# ---------------------------------------------------------------------------
# 5 — Lecture seule libellée correctement en FR et EN
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
@pytest.mark.parametrize("lang,expected_token", [
    ("fr", "pilotées depuis"),
    ("en", "piloted from"),
])
def test_profile_sidebar_lecture_seule_libelle(lang, expected_token):
    """Profile sidebar affiche bien le libellé « Pilotée depuis Settings »
    dans la bonne langue."""
    at = AppTest.from_file(PROFILE)
    at.session_state["ui_lang"] = lang
    at.run(timeout=90)
    assert not at.exception
    captions = " ".join(str(getattr(c, "value", "")) for c in at.caption).lower()
    assert expected_token in captions, (
        f"Libellé « pilotée depuis Settings » absent en mode {lang}. "
        f"Captions vues : {captions[:300]}"
    )
