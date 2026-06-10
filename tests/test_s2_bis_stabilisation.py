"""Tests Phase S2-bis — stabilisation manager (retours prod 2026-06-10).

Couvre :
  A. i18n EN — Historique (titres/colonnes/filtres) et Supervision (états,
     diagnostic, blocs décision) rendus sans français en mode English.
  C. Zone 8 / LFP — les NOUVEAUX records ne persistent plus le label matière
     nominal moteur en mode client (make_record(mask_nominal_materials=True)).
  D. Synchronisation — navigation réelle Settings → Profile → Supervision →
     Analyse → Historique → Moteur Procédé via le miroir disque opérateur :
     100 RPM × 2,5 g/h/RPM = 250 g/h = 4,17 g/min partout, jamais 30 ni 5.
  E. Agent IA / lecture profil — le scénario manager (convoyage dominant +
     Kneading 60° uniquement) ne produit AUCUNE mention 90°/45°, y compris
     les formes « Malaxage (90° dispersif + 30/45° distributif) » qui
     échappaient aux tokens composés (cause racine du retour prod).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import history_store  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

PAGES = {
    "supervision": str(ROOT / "app" / "Supervision.py"),
    "profile": str(ROOT / "app" / "pages" / "1_Profile.py"),
    "settings": str(ROOT / "app" / "pages" / "2_Settings.py"),
    "analyse": str(ROOT / "app" / "pages" / "3_Analyse_run.py"),
    "historique": str(ROOT / "app" / "pages" / "4_Historique.py"),
    "moteur": str(ROOT / "app" / "pages" / "5_Moteur_Procede.py"),
}

RPM, COEFF = 100.0, 2.5
EXPECTED_GMIN = 250.0 / 60.0  # 4.1667
TOL = 0.01


def _rendered_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success", "metric"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
                chunks.append(str(getattr(el, "label", "")))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    try:
        for el in at.get("arrow_data_frame"):
            chunks.append(str(getattr(el, "value", "")))
    except Exception:
        pass
    try:
        for el in at.get("expander"):
            chunks.append(str(getattr(el, "label", "")))
    except Exception:
        pass
    return "\n".join(chunks)


# ===========================================================================
# A — i18n EN
# ===========================================================================
def _historique_record() -> dict:
    return {
        "schema_version": 1, "id": "run_20260610_090000_beef",
        "timestamp_iso": "2026-06-10T09:00:00", "label": "run s2bis",
        "source": "manual", "status": "actif", "fingerprint": "beef",
        "config": {"screw_rpm": 100.0, "n_elements": 10.0, "feeders_actifs": 1,
                   "debit_principal_g_min": 4.17, "matiere_principale": "granules",
                   "feeders_composition": [], "zones_die": 1, "temps_consigne_C": {}},
        "engine_kpis": {"couple_total_nm": 0.5, "sme_kwh_kg": 0.05,
                        "residence_s": 30.0, "fill_moyen": 0.4, "fill_crete": 0.6,
                        "cisaillement_max_s": 100.0, "debit_massique_kg_h": 0.25,
                        "debit_sortie_pointe_cm3_s": 0.1},
        "zones": [{"zone": z, "fill_moyen": 0.4, "fill_crete": 0.6,
                   "residence_s": 3.0, "matiere_dominante": None}
                  for z in range(9)],
        "agent": None,
    }


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_historique_english_no_french_chrome(tmp_path, monkeypatch):
    hist = tmp_path / "h.json"
    hist.write_text(json.dumps([_historique_record()]), encoding="utf-8")
    monkeypatch.setenv(history_store.HISTORY_PATH_ENV, str(hist))
    at = AppTest.from_file(PAGES["historique"])
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    at = at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    assert "Process history" in text
    for fr in ("Historique des procédés", "Procédés enregistrés",
               "Dernier enregistrement", "Voir le détail",
               "Agrégats par zone (figés au commit)",
               "Configurations enregistrées", "Matière dominante",
               "Débit princ.", "Essais d'entraînement ML"):
        assert fr not in text, f"texte FR visible en anglais (Historique) : {fr}"


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_supervision_english_no_french_state_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "rs.json"))
    at = AppTest.from_file(PAGES["supervision"])
    at.session_state["ui_lang"] = "en"
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _rendered_text(at)
    for fr in ("PROCÉDÉ STABLE", "À SURVEILLER", "INSTABLE CRITIQUE",
               "Maintenir les consignes thermiques",
               "CONFIG VIS RECOMMANDÉE", "ACTION PRIORITAIRE",
               "RECO PRINCIPALE", "aucune autre alerte",
               "Toutes les zones thermiques sont dans les tolérances",
               "présente la variabilité la plus élevée"):
        assert fr not in text, f"texte FR visible en anglais (Supervision) : {fr}"


# ===========================================================================
# C — Zone 8 / LFP : commit client ne persiste plus le label nominal
# ===========================================================================
class _FakeZone:
    def __init__(self, zone):
        self.zone = zone
        self.mean_fill_factor = 0.4
        self.max_fill_factor = 0.6
        self.residence_time_s = 3.0
        self.dominant_material = "LiFePO4 (LFP)"  # label NOMINAL moteur


class _FakeReport:
    zones = tuple(_FakeZone(z) for z in range(9))
    total_torque_nm = 0.5
    total_sme_kwh_per_kg = 0.05
    residence_time_total_s = 30.0
    fill_factor_average = 0.4
    peak_fill_factor = 0.6
    max_shear_rate_s = 100.0
    mass_flow_kg_per_h = 0.25
    output_vol_flow_cm3_s = 0.1


class _FakeSnap:
    screw_config = [0] * 81
    screw_rpm = 100.0
    feeders = [{"feeder_id": 1, "enabled": True, "label": "", "position": "Z0",
                "material_id": "granules", "polymer_name": "",
                "mass_flow_g_per_min": 4.17, "density_g_per_cm3": 0.55}]
    zone_temps_C: dict = {}
    n_die_zones = 1
    timestamp_iso = "2026-06-10T09:00:00"
    label = ""


def test_make_record_client_mode_masks_nominal_material():
    """Mode client : aucun label matière nominal moteur persisté en zones."""
    rec = history_store.make_record(
        _FakeSnap(), _FakeReport(), mask_nominal_materials=True,
    )
    assert all(z["matiere_dominante"] is None for z in rec["zones"])
    assert "LiFePO4" not in json.dumps(rec, ensure_ascii=False)


def test_make_record_demo_mode_keeps_nominal_material():
    """Mode démonstration : le label nominal reste traçable (assumé)."""
    rec = history_store.make_record(
        _FakeSnap(), _FakeReport(), mask_nominal_materials=False,
    )
    assert rec["zones"][8]["matiere_dominante"] == "LiFePO4 (LFP)"


# ===========================================================================
# D — Navigation réelle inter-pages : 100 × 2,5 = 4,17 g/min partout
# ===========================================================================
@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_calibrated_flow_survives_full_navigation(tmp_path, monkeypatch):
    """Settings (étalonnage 100×2,5 saisi) puis CHAQUE page ouverte comme une
    session de navigation (miroir disque opérateur partagé) : le débit legacy
    vaut partout 4,17 g/min — jamais 30 (défaut) ni 5 (résiduel)."""
    monkeypatch.setenv("RONDOL_RUN_STATE_PATH", str(tmp_path / "rs.json"))
    monkeypatch.setenv(history_store.HISTORY_PATH_ENV, str(tmp_path / "h.json"))

    # 1. Settings : l'opérateur saisit l'étalonnage feeder #1.
    at = AppTest.from_file(PAGES["settings"])
    at.session_state["feeder_rpm"] = RPM
    at.session_state["feeder_calib_g_h_per_rpm"] = COEFF
    at.session_state["fd_en_1"] = True
    # Valeur ancienne parasite volontaire (cas réel : restaurée d'une vieille session).
    at.session_state["feeder_g_per_min"] = 5.0
    at = at.run(timeout=180)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.session_state["feeder_g_per_min"] == pytest.approx(EXPECTED_GMIN, abs=TOL)

    # 2. Navigation : chaque page repart d'une session neuve + miroir disque.
    for name in ("profile", "supervision", "analyse", "historique", "moteur"):
        at_page = AppTest.from_file(PAGES[name])
        at_page = at_page.run(timeout=180)
        assert not at_page.exception, (name, [str(e.value) for e in at_page.exception])
        feed = (
            at_page.session_state["feeder_g_per_min"]
            if "feeder_g_per_min" in at_page.session_state else None
        )
        if feed is not None:
            # 4,1667 exigé — exclut de fait le défaut 30 et le résiduel 5.
            assert feed == pytest.approx(EXPECTED_GMIN, abs=TOL), (
                f"{name} : feeder_g_per_min={feed} ≠ 4,17 (retour valeur ancienne)"
            )


# ===========================================================================
# E — lecture profil / recos rendu vis : scénario manager convoyage + K60
# ===========================================================================
def _manager_cfg():
    from screw_logic import add_elements_atomic, new_empty_configuration
    cfg = new_empty_configuration()
    add_elements_atomic(cfg, 1, 16)  # convoyage dominant
    add_elements_atomic(cfg, 7, 2)   # Kneading 60° uniquement
    return cfg


def test_screw_render_recos_never_cite_90_45_with_only_k60():
    """Repro prod : ratio convoyage/mélange > 4 déclenche la reco « densifier
    le mélange » — elle ne doit plus citer 90°/45°/30° (types absents),
    y compris sous la forme « (90° dispersif + 30/45° distributif) »."""
    from screw_logic import (
        MAIN_FEEDER_POSITION, N_POSITIONS, TIP_PART1_POS,
        base_type, fill_factor_average, is_part2, position_to_zone,
    )
    from screw_render import compute_recommendations

    recs = compute_recommendations(
        _manager_cfg(), rpm=120.0, feed=4.17, dens=0.55,
        base_type_fn=base_type, is_part2_fn=is_part2,
        position_to_zone_fn=position_to_zone,
        fill_factor_fn=fill_factor_average,
        n_positions=N_POSITIONS,
        main_feeder_pos=MAIN_FEEDER_POSITION,
        tip_part1_pos=TIP_PART1_POS,
    )
    assert recs, "au moins une reco (ou le repli générique) attendue"
    for r in recs:
        blob = " ".join(
            str(r.get(k, "")) for k in
            ("physics", "impact", "action", "title", "detail", "evidence")
        ).lower()
        for tok in ("kneading 90", "kneading 45", "malaxage 90", "malaxage 45",
                    "90°", "45°", "30°"):
            assert tok not in blob, (
                f"Reco rendu vis cite « {tok} » avec un profil convoyage+K60 : {r}"
            )


def test_screw_render_can_cite_60_when_present():
    """Mentionner 60° reste autorisé (type 7 présent) — la garde ne sur-filtre
    pas les éléments réellement posés."""
    from screw_logic import recommendation_cites_absent_element
    cfg = _manager_cfg()
    assert recommendation_cites_absent_element(
        "Réduire les Kneading 60° à 1 seul bloc.", cfg) is False
