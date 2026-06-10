"""Tests Phase S2 — stabilisation produit (retours manager 2026-06-10).

Couvre :
  1. i18n EN/FR — les blocs Profile signalés en prod (« Capacité maximale
     atteinte », « Retirez un élément… ») passent par rondol_i18n ; en anglais
     aucun texte français ne subsiste dans ces blocs.
  2. SME 0.4 — couvert par tests/test_sme_alert_wording.py (S2).
  3. Zone 8 / LFP — aucune chimie nominale (LiFePO4/LFP) affichée dans
     Historique en mode client ; jamais de LFP injecté par défaut au commit.
  4. Agrégats Historique — une table de zones toutes à zéro n'est pas affichée
     comme un résultat physique ; statut clair à la place.
  5. Agent IA — aucune recommandation ne cite un élément absent du profil réel,
     y compris quand la configuration vis est vide.
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

from rondol_i18n import TRANSLATIONS  # noqa: E402
from AgentIndustrial_v1.core.process import ProcessState, ScrewKPIs  # noqa: E402
from AgentIndustrial_v1.core.rules import evaluate  # noqa: E402
from AgentIndustrial_v1.core.recommendations import build_recommendations  # noqa: E402
import history_store  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

PROFILE_PATH = str(ROOT / "app" / "pages" / "1_Profile.py")
HISTORIQUE_PATH = str(ROOT / "app" / "pages" / "4_Historique.py")


# ---------------------------------------------------------------------------
# 1 — i18n EN/FR
# ---------------------------------------------------------------------------
_S2_KEYS = (
    "profile.banner.empty", "profile.banner.full", "profile.banner.almost_full",
    "profile.msg.reset", "profile.msg.demo_loaded", "profile.msg.demo_chaotic",
    "profile.msg.removed_one", "profile.msg.added_one", "profile.msg.added_four",
    "profile.msg.add_impossible", "profile.msg.add4_blocked",
    "historique.zones_title", "historique.zones_absent",
    "historique.zones_not_significant",
    "historique.zones_col.zone", "historique.zones_col.fill_mean",
    "historique.zones_col.fill_peak", "historique.zones_col.residence",
    "historique.zones_col.material",
    "historique.agent_title", "historique.agent_absent",
)

# Marqueurs français qui ne doivent PAS apparaître dans les textes anglais.
_FR_MARKERS = ("Capacité", "Retirez", "atteinte", "éléments", "vis vide",
               "Aucun", "figés", "renseigné", "Résidence", "Matière")


def test_s2_keys_exist_in_both_languages():
    for key in _S2_KEYS:
        entry = TRANSLATIONS.get(key)
        assert entry is not None, f"clé i18n manquante : {key}"
        assert entry.get("fr"), f"variante FR vide : {key}"
        assert entry.get("en"), f"variante EN vide : {key}"


def test_s2_english_texts_contain_no_french():
    for key in _S2_KEYS:
        en = TRANSLATIONS[key]["en"]
        for marker in _FR_MARKERS:
            assert marker.lower() not in en.lower(), (
                f"texte EN de {key} contient du français « {marker} » : {en}"
            )


def test_profile_source_no_longer_hardcodes_capacity_strings():
    """Les chaînes vues en prod ne sont plus codées en dur dans la page."""
    src = Path(PROFILE_PATH).read_text(encoding="utf-8")
    for literal in (
        '"<b>Capacité maximale atteinte</b>',
        'f"<b>Capacité maximale atteinte</b>',
        '"Retirez un élément avec',
        '"Configuration réinitialisée — vis vide."',
        '"Configuration démo chargée."',
    ):
        assert literal not in src, f"chaîne FR codée en dur restante : {literal}"


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_profile_english_empty_screw_banner_has_no_french():
    """Profile en anglais, vis vide → bannière en anglais, zéro français."""
    from screw_logic import new_empty_configuration
    at = AppTest.from_file(PROFILE_PATH)
    at.session_state["ui_lang"] = "en"
    at.session_state["screw_config"] = new_empty_configuration()
    at = at.run(timeout=120)
    assert not at.exception, [str(e.value) for e in at.exception]
    html = "\n".join(
        str(getattr(el, "body", getattr(el, "value", "")))
        for el in at.get("html")
    )
    assert "Empty screw" in html
    # Blocs corrigés en S2 (bannière capacité/état vis). NB : les textes du
    # rendu vis (screw_render.py — archétypes, lecture IA) relèvent de la
    # phase i18n B3 et ne sont pas couverts ici.
    for fr in ("Vis vide.</b>", "Aucun élément après le main feeder",
               "Capacité maximale", "Retirez un élément",
               "Ajoutez des éléments via <b>+1"):
        assert fr not in html, f"texte FR visible en anglais : {fr}"


# ---------------------------------------------------------------------------
# 3 + 4 — Historique : zone 8 / LFP + agrégats tous à zéro
# ---------------------------------------------------------------------------
def _zero_record_with_lfp_zone8() -> dict:
    """Record persistant reproduisant le cas prod : zones 0..8 toutes à zéro,
    matière nominale LFP figée en zone 8 (label moteur, pas une saisie)."""
    zones = [
        {"zone": z, "fill_moyen": 0.0, "fill_crete": 0.0,
         "residence_s": 0.0, "matiere_dominante": None}
        for z in range(8)
    ]
    zones.append({"zone": 8, "fill_moyen": 0.0, "fill_crete": 0.0,
                  "residence_s": 0.0, "matiere_dominante": "LiFePO4 (LFP)"})
    return {
        "schema_version": 1,
        "id": "run_20260610_080000_dead",
        "timestamp_iso": "2026-06-10T08:00:00",
        "label": "cas prod S2",
        "source": "manual",
        "status": "actif",
        "fingerprint": "deadbeef",
        "config": {
            "screw_rpm": 100.0, "n_elements": 0.0, "feeders_actifs": 1,
            "debit_principal_g_min": 0.75, "matiere_principale": "granules",
            "feeders_composition": [{
                "feeder_id": 1, "label": "", "position": "Z0",
                "material_id": "granules", "composition": None,
                "composition_source": "NOT_AVAILABLE",
                "mass_flow_g_per_min": 0.75, "bulk_density_g_per_cm3": 0.45,
                "thermal_expansion_per_K": 0.0, "t_degradation_C": None,
                "tga_onset_C": None, "viscosity_pa_s": None,
                "t_melt_C": None, "t_glass_C": None,
            }],
            "zones_die": 1, "temps_consigne_C": {},
        },
        "engine_kpis": {
            "couple_total_nm": 0.0, "sme_kwh_kg": 0.0, "residence_s": 0.0,
            "fill_moyen": 0.0, "fill_crete": 0.0, "cisaillement_max_s": 0.0,
            "debit_massique_kg_h": 0.045, "debit_sortie_pointe_cm3_s": 0.0,
        },
        "zones": zones,
        "agent": None,
    }


def _run_historique(tmp_path, monkeypatch, record: dict):
    hist = tmp_path / "history_s2.json"
    hist.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv(history_store.HISTORY_PATH_ENV, str(hist))
    at = AppTest.from_file(HISTORIQUE_PATH)
    at.session_state["demo_mode"] = False  # mode client
    return at.run(timeout=120)


def _all_rendered_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    # Dataframes (tables zones / composition / runs).
    try:
        for el in at.get("arrow_data_frame"):
            chunks.append(str(getattr(el, "value", "")))
    except Exception:
        pass
    return "\n".join(chunks)


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_historique_zone8_lfp_not_displayed_in_client_mode(tmp_path, monkeypatch):
    at = _run_historique(tmp_path, monkeypatch, _zero_record_with_lfp_zone8())
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _all_rendered_text(at)
    assert "LiFePO4" not in text, "chimie nominale LFP visible en mode client"


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_historique_all_zero_aggregates_show_status_not_table(tmp_path, monkeypatch):
    at = _run_historique(tmp_path, monkeypatch, _zero_record_with_lfp_zone8())
    assert not at.exception, [str(e.value) for e in at.exception]
    text = _all_rendered_text(at)
    assert ("Per-zone aggregates not available" in text
            or "Agrégats par zone non disponibles" in text)
    assert "Per-zone aggregates (frozen at commit)" not in text


def test_history_store_never_invents_lfp_composition():
    """Commit : composition vide → None (jamais « LFP » par défaut)."""
    class _Snap:
        screw_config = [0] * 81
        screw_rpm = 100.0
        feeders = [{
            "feeder_id": 1, "enabled": True, "label": "", "position": "Z0",
            "material_id": "granules", "polymer_name": "",
            "mass_flow_g_per_min": 0.75, "density_g_per_cm3": 0.45,
        }]
        zone_temps_C: dict = {}
        n_die_zones = 1
        timestamp_iso = "2026-06-10T08:00:00"
        label = ""

    rec = history_store.make_record(_Snap(), report=None)
    comp = rec["config"]["feeders_composition"]
    assert comp and comp[0]["composition"] is None
    blob = json.dumps(rec, ensure_ascii=False)
    assert "LiFePO4" not in blob and "LFP" not in blob


# ---------------------------------------------------------------------------
# 5 — Agent IA : aucun élément absent cité (y compris config vide)
# ---------------------------------------------------------------------------
def _recos_text(recos) -> str:
    return " ".join(
        f"{r.title} {r.rationale} {r.action} {r.delta_label}" for r in recos
    ).lower()


def test_agent_no_kneading_reco_on_empty_screw():
    """Vis vide + SME au-dessus du seuil de vigilance → la reco « substituer
    Kneading 90° par 45° » ne doit PAS apparaître (aucun kneading présent)."""
    state = ProcessState(screw_config=[0] * 81, screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=0.55)
    report = evaluate(state)
    recos = build_recommendations(state, report.alerts)
    blob = _recos_text(recos)
    assert "kneading" not in blob and "malaxage" not in blob


def test_agent_guard_applies_even_with_unknown_config():
    """Config vis inconnue (liste vide) → la garde filtre quand même : aucun
    élément précis ne peut être cité s'il n'est pas vérifiable."""
    state = ProcessState(screw_config=[], screw_rpm=120.0)
    state.kpis = ScrewKPIs(sme_kwh_per_kg=0.55)
    report = evaluate(state)
    recos = build_recommendations(state, report.alerts)
    blob = _recos_text(recos)
    assert "kneading" not in blob and "malaxage" not in blob
    # Les recos élément-agnostiques (rpm) restent disponibles en repli.
    assert any(r.category == "screw_speed" for r in recos)
