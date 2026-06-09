"""test_history_store.py — store historique procédé persistant (disque JSON).

Couvre : make_record, écriture/relecture (= redémarrage simulé), anti-doublon
Skip, robustesse (fichier absent, vide, corrompu, record malformé), empreinte,
normalisation du statut, et le fait qu'aucun KPI absent n'est inventé.

Le store est testé EN ISOLATION : faux snapshot (duck-typing) + faux EngineReport,
sans Streamlit ni session. Chemin de stockage = tmp_path.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from history_store import (  # noqa: E402
    SOURCE_DEMO,
    SOURCE_MANUAL,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    append_run,
    compute_fingerprint,
    flat_params_from_snapshot,
    load_runs,
    make_record,
    read_runs,
)


# ---------------------------------------------------------------------------
# Doublures de test (duck-typing — pas d'import AgentIndustrial / engine)
# ---------------------------------------------------------------------------
@dataclass
class FakeSnapshot:
    timestamp_iso: str = "2026-06-05T14:30:12"
    label: str = "Test #1"
    screw_config: list = None
    screw_rpm: float = 120.0
    zone_temps_C: dict = None
    n_die_zones: int = 1
    feeders: list = None

    def __post_init__(self):
        if self.screw_config is None:
            self.screw_config = [1, 1, 4, 7, 0]
        if self.zone_temps_C is None:
            self.zone_temps_C = {"Z1": 40.0, "Z2": 60.0}
        if self.feeders is None:
            self.feeders = [
                {"material_id": "LFP", "enabled": True, "position": "Z0",
                 "mass_flow_g_per_min": 30.0, "density_g_per_cm3": 0.55},
                {"material_id": "LATP", "enabled": False, "position": "Z3",
                 "mass_flow_g_per_min": 10.0, "density_g_per_cm3": 0.55},
            ]


@dataclass
class FakeZone:
    zone: int
    mean_fill_factor: float
    max_fill_factor: float
    residence_time_s: float
    dominant_material: str | None


@dataclass
class FakeReport:
    total_torque_nm: float = 1.23
    total_sme_kwh_per_kg: float = 0.045
    residence_time_total_s: float = 88.0
    fill_factor_average: float = 0.42
    peak_fill_factor: float = 0.91
    max_shear_rate_s: float = 150.0
    mass_flow_kg_per_h: float = 1.8
    output_vol_flow_cm3_s: float = 0.9
    zones: tuple = ()

    def __post_init__(self):
        if not self.zones:
            self.zones = (
                FakeZone(1, 0.40, 0.55, 30.0, "LFP"),
                FakeZone(2, 0.50, 0.91, 58.0, "LFP"),
            )


def _path(tmp_path) -> Path:
    return tmp_path / "process_history.json"


# ---------------------------------------------------------------------------
# make_record
# ---------------------------------------------------------------------------
def test_make_record_freezes_kpis():
    rec = make_record(FakeSnapshot(), FakeReport())
    assert rec["schema_version"] == 1
    assert rec["id"].startswith("run_20260605_143012_")
    assert rec["source"] == SOURCE_MANUAL
    assert rec["engine_kpis"]["couple_total_nm"] == 1.23
    assert rec["engine_kpis"]["fill_crete"] == 0.91
    assert rec["engine_kpis"]["cisaillement_max_s"] == 150.0
    # Agrégats zones figés
    assert len(rec["zones"]) == 2
    assert rec["zones"][1]["matiere_dominante"] == "LFP"
    # Config utile
    assert rec["config"]["debit_principal_g_min"] == 30.0
    assert rec["config"]["matiere_principale"] == "LFP"
    assert rec["config"]["feeders_actifs"] == 1
    # Agent non disponible au commit → None (jamais inventé)
    assert rec["agent"] is None


def test_make_record_no_report_keeps_kpis_none():
    """Cas dégénéré : pas de report → KPIs None, jamais inventés."""
    rec = make_record(FakeSnapshot(), None)
    assert all(v is None for v in rec["engine_kpis"].values())
    assert rec["zones"] is None


def test_make_record_demo_source():
    rec = make_record(FakeSnapshot(), FakeReport(), source=SOURCE_DEMO)
    assert rec["source"] == SOURCE_DEMO


def test_flat_params_from_snapshot_side_feeder():
    """Side feeder activé sur Z3 → side_feeder_zone = 3."""
    snap = FakeSnapshot()
    snap.feeders[1]["enabled"] = True
    params = flat_params_from_snapshot(snap)
    assert params["feed_g_per_min"] == 30.0
    assert params["bulk_density"] == 0.55
    assert params["side_feeder_zone"] == 3


def test_flat_params_side_feeder_off():
    params = flat_params_from_snapshot(FakeSnapshot())
    assert params["side_feeder_zone"] == 0


# ---------------------------------------------------------------------------
# append / read — persistance & redémarrage simulé
# ---------------------------------------------------------------------------
def test_append_and_reload_persists(tmp_path):
    p = _path(tmp_path)
    assert append_run(make_record(FakeSnapshot(), FakeReport()), p) is True
    # « Redémarrage » : nouvelle lecture depuis le disque.
    runs = load_runs(p)
    assert len(runs) == 1
    assert runs[0]["engine_kpis"]["couple_total_nm"] == 1.23


def test_append_multiple_and_status_normalised(tmp_path):
    p = _path(tmp_path)
    append_run(make_record(FakeSnapshot(timestamp_iso="2026-06-05T10:00:00",
                                        screw_rpm=100.0), FakeReport()), p)
    append_run(make_record(FakeSnapshot(timestamp_iso="2026-06-05T11:00:00",
                                        screw_rpm=200.0), FakeReport()), p)
    runs = load_runs(p)
    assert len(runs) == 2
    # Dernier = actif, les autres = archivé.
    assert runs[-1]["status"] == STATUS_ACTIVE
    assert runs[0]["status"] == STATUS_ARCHIVED


# ---------------------------------------------------------------------------
# anti-doublon (Skip)
# ---------------------------------------------------------------------------
def test_duplicate_is_skipped(tmp_path):
    p = _path(tmp_path)
    rec1 = make_record(FakeSnapshot(label="A"), FakeReport())
    # Même config métier, label différent → même empreinte → skip.
    rec2 = make_record(FakeSnapshot(label="B"), FakeReport())
    assert append_run(rec1, p) is True
    assert append_run(rec2, p) is False
    assert len(load_runs(p)) == 1


def test_change_then_append_creates_new(tmp_path):
    p = _path(tmp_path)
    append_run(make_record(FakeSnapshot(screw_rpm=120.0), FakeReport()), p)
    # rpm modifié → empreinte différente → nouvel enregistrement.
    assert append_run(make_record(FakeSnapshot(screw_rpm=180.0), FakeReport()), p) is True
    assert len(load_runs(p)) == 2


def test_fingerprint_ignores_label_and_timestamp():
    fp1 = compute_fingerprint([1, 2, 3], 120.0, [], {"Z1": 40.0})
    fp2 = compute_fingerprint([1, 2, 3], 120.0, [], {"Z1": 40.0})
    fp3 = compute_fingerprint([1, 2, 3], 121.0, [], {"Z1": 40.0})
    assert fp1 == fp2
    assert fp1 != fp3


# ---------------------------------------------------------------------------
# robustesse
# ---------------------------------------------------------------------------
def test_missing_file_returns_empty(tmp_path):
    res = read_runs(tmp_path / "nope.json")
    assert res.runs == []
    assert res.corrupt is False


def test_empty_file_returns_empty(tmp_path):
    p = _path(tmp_path)
    p.write_text("", encoding="utf-8")
    res = read_runs(p)
    assert res.runs == []
    assert res.corrupt is False


def test_corrupt_file_flagged_not_crash(tmp_path):
    p = _path(tmp_path)
    p.write_text("{ this is not json ", encoding="utf-8")
    res = read_runs(p)
    assert res.runs == []
    assert res.corrupt is True
    assert res.error  # message discret disponible pour l'UI


def test_malformed_record_skipped(tmp_path):
    p = _path(tmp_path)
    good = make_record(FakeSnapshot(), FakeReport())
    p.write_text(
        json.dumps([good, {"garbage": 1}, "not-a-dict"], ensure_ascii=False),
        encoding="utf-8",
    )
    res = read_runs(p)
    assert len(res.runs) == 1
    assert res.skipped == 2


def test_append_recovers_from_corrupt(tmp_path):
    """Un fichier corrompu ne bloque pas un nouvel enregistrement."""
    p = _path(tmp_path)
    p.write_text("garbage", encoding="utf-8")
    assert append_run(make_record(FakeSnapshot(), FakeReport()), p) is True
    assert len(load_runs(p)) == 1


# ===========================================================================
#  Phase 9 manager 2026-06-09 — composition matière par feeder
# ===========================================================================
from history_store import _feeder_composition_block  # noqa: E402


def test_feeder_composition_only_enabled():
    """Seuls les feeders activés apparaissent dans la composition (Phase 9)."""
    feeders = [
        {"feeder_id": 1, "enabled": True, "label": "Main",
         "position": "Z0", "polymer_name": "LFP",
         "mass_flow_g_per_min": 30.0, "density_g_per_cm3": 0.55},
        {"feeder_id": 2, "enabled": False, "label": "Side",
         "position": "Z3", "polymer_name": "LATP",
         "mass_flow_g_per_min": 10.0, "density_g_per_cm3": 0.55},
    ]
    comp = _feeder_composition_block(feeders)
    assert len(comp) == 1
    assert comp[0]["feeder_id"] == 1
    assert comp[0]["composition"] == "LFP"
    assert comp[0]["composition_source"] == "USER_INPUT"


def test_feeder_composition_empty_polymer_stores_none_not_string():
    """Polymer non renseigné → composition = None (jamais 'LFP' ni chaîne en
    dur 'Non renseigné' qui violerait l'i18n et la règle anti-démo)."""
    feeders = [{
        "feeder_id": 1, "enabled": True, "label": "Main", "position": "Z0",
        "polymer_name": "",   # vide
        "mass_flow_g_per_min": 30.0, "density_g_per_cm3": 0.55,
    }]
    comp = _feeder_composition_block(feeders)
    assert comp[0]["composition"] is None
    assert comp[0]["composition_source"] == "NOT_AVAILABLE"


def test_feeder_composition_no_phantom_state_field():
    """Régression review adversariale 2026-06-09 : le champ 'state' n'existe
    pas dans AppliedSnapshot._feeder_to_dict — le composition_block NE DOIT
    PAS inventer une valeur démo « powder »."""
    feeders = [{
        "feeder_id": 1, "enabled": True, "label": "Main", "position": "Z0",
        "polymer_name": "PVDF", "mass_flow_g_per_min": 5.0,
        "density_g_per_cm3": 0.55,
    }]
    comp = _feeder_composition_block(feeders)
    # « state » ne doit PAS être présent dans la sortie (aucune valeur par
    # défaut inventée). material_id reste là car réellement sérialisé.
    assert "state" not in comp[0]
    assert "material_id" in comp[0]


def test_feeder_composition_thermal_fields_preserved():
    """Les T° matière étendues (T_dég, TGA, viscosité, Tm, Tg) sont préservées
    telles quelles — None si non saisies."""
    feeders = [{
        "feeder_id": 1, "enabled": True, "label": "PVDF",
        "position": "Z0", "polymer_name": "PVDF",
        "mass_flow_g_per_min": 5.0, "density_g_per_cm3": 1.78,
        "t_degradation_C": 280.0, "tga_onset_C": 380.0,
        "viscosity_pa_s": 1200.0, "t_melt_C": 175.0, "t_glass_C": -35.0,
    }]
    comp = _feeder_composition_block(feeders)[0]
    assert comp["t_degradation_C"] == 280.0
    assert comp["tga_onset_C"] == 380.0
    assert comp["viscosity_pa_s"] == 1200.0
    assert comp["t_melt_C"] == 175.0
    assert comp["t_glass_C"] == -35.0


def test_feeder_composition_thermal_fields_none_if_absent():
    """Aucune valeur thermique inventée si l'opérateur n'a rien saisi."""
    feeders = [{
        "feeder_id": 1, "enabled": True, "position": "Z0",
        "polymer_name": "", "mass_flow_g_per_min": 0.0,
        "density_g_per_cm3": 0.55,
    }]
    comp = _feeder_composition_block(feeders)[0]
    for k in ("t_degradation_C", "tga_onset_C", "viscosity_pa_s",
              "t_melt_C", "t_glass_C"):
        assert comp[k] is None, f"{k} doit rester None (jamais inventé)"


def test_feeder_composition_empty_list_when_no_feeders():
    assert _feeder_composition_block([]) == []
    assert _feeder_composition_block(None) == []


def test_make_record_includes_composition_block():
    """L'intégration make_record doit injecter feeders_composition dans config."""
    rec = make_record(FakeSnapshot(), FakeReport())
    comp = rec["config"]["feeders_composition"]
    # FakeSnapshot a 1 feeder actif (LFP) + 1 inactif (LATP)
    assert len(comp) == 1
    assert comp[0]["material_id"] == "LFP"


def test_fingerprint_stable_regardless_of_composition_block():
    """L'empreinte (anti-doublon) ne doit PAS dépendre du bloc composition
    enrichi : sinon deux clics « Enregistrer » identiques créeraient un
    doublon dès qu'un champ thermique optionnel diffère, ou pire l'anti-
    doublon serait cassé après la Phase 9 (compute_fingerprint inclut
    déjà material_id/enabled/position/débit/densité — c'est suffisant)."""
    snap1 = FakeSnapshot()
    snap2 = FakeSnapshot()
    # Mêmes feeders (mêmes champs métier clés) → même empreinte.
    fp1 = compute_fingerprint(
        snap1.screw_config, snap1.screw_rpm, snap1.feeders, snap1.zone_temps_C,
    )
    fp2 = compute_fingerprint(
        snap2.screw_config, snap2.screw_rpm, snap2.feeders, snap2.zone_temps_C,
    )
    assert fp1 == fp2
