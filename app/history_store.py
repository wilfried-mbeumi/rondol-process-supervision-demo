"""history_store.py — Historique procédé PERSISTANT (disque, JSON).

Stockage durable des configurations procédé enregistrées par l'opérateur, avec
les KPIs moteur FIGÉS au moment du clic « Enregistrer ». Survit au redémarrage
de l'application (contrairement à `applied_history` qui reste en session).

Périmètre / garanties :
  - PAS de dépendance Streamlit, PAS de dépendance `engine/` : ce module ne fait
    que la PERSISTANCE et la MISE EN FORME d'un record. Le rapport moteur
    (`EngineReport`) est construit en amont (call-site Settings) via le helper
    partagé `engine.report_params` et passé à `make_record`. → un seul chemin de
    calcul, zéro divergence avec la page Moteur Procédé.
  - LECTURE SEULE à l'affichage : aucun KPI n'est recalculé ici. On fige au
    commit, on relit tel quel.
  - Robustesse : fichier absent/vide → liste vide ; fichier corrompu → liste
    vide + drapeau d'erreur (jamais de crash) ; record illisible → ignoré.
  - Anti-doublon : `append_run` IGNORE un record dont l'empreinte est identique à
    celle du dernier record persistant (re-clic « Enregistrer » sans changement).
  - Écriture atomique (fichier temporaire + os.replace).

Ce module N'écrit RIEN de None déguisé en valeur : un KPI/agrégat absent reste
explicitement `None` dans le record.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

# Bootstrap sys.path : racine projet + app/ (screw_logic en module nu).
_APP = Path(__file__).resolve().parent
_ROOT = _APP.parent
for _p in (_ROOT, _APP):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from screw_logic import count_user_elements  # type: ignore  # noqa: E402

# Emplacement par défaut du stockage persistant (créé à la 1re écriture).
DEFAULT_HISTORY_PATH: Path = _ROOT / "data" / "history" / "process_history.json"
# Variable d'environnement d'override (isolation tests / CI / déploiement) :
# si définie, elle remplace le chemin par défaut. Évite que la suite de tests
# (qui exerce le vrai commit) ne pollue le fichier d'historique de production.
HISTORY_PATH_ENV = "RONDOL_HISTORY_PATH"

SCHEMA_VERSION = 1
SOURCE_MANUAL = "manual"
SOURCE_DEMO = "demonstration"
STATUS_ACTIVE = "actif"
STATUS_ARCHIVED = "archivé"


# ===========================================================================
#  Résultat de lecture (robustesse : distingue vide / corrompu)
# ===========================================================================
@dataclass(frozen=True)
class LoadResult:
    """Lecture défensive du stockage : runs valides + état d'erreur éventuel."""
    runs: list[dict[str, Any]]
    corrupt: bool = False  # le fichier existe mais est illisible (JSON cassé)
    skipped: int = 0       # nombre de records individuels ignorés (malformés)
    error: str | None = None


# ===========================================================================
#  Empreinte & identifiant
# ===========================================================================
def compute_fingerprint(
    screw_config: list[int],
    screw_rpm: float,
    feeders: list[Mapping[str, Any]],
    zone_temps_C: Mapping[str, Any] | None,
) -> str:
    """Empreinte de contenu déterministe (SHA1) — base de l'anti-doublon.

    Couvre la configuration *métier* (vis, vitesse, feeders, consignes), PAS le
    timestamp ni le label : deux enregistrements identiques au libellé près
    partagent la même empreinte.
    """
    payload = {
        "config": list(screw_config or []),
        "rpm": round(float(screw_rpm), 6),
        "feeders": [
            {
                "material_id": f.get("material_id"),
                "enabled": bool(f.get("enabled")),
                "position": f.get("position"),
                "mass_flow_g_per_min": round(float(f.get("mass_flow_g_per_min") or 0.0), 6),
                "density_g_per_cm3": round(float(f.get("density_g_per_cm3") or 0.0), 6),
            }
            for f in (feeders or [])
        ],
        "temps": {k: round(float(v), 6) for k, v in dict(zone_temps_C or {}).items()},
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _make_id(timestamp_iso: str, fingerprint: str) -> str:
    """Identifiant lisible : run_YYYYMMDD_HHMMSS_<4 hex empreinte>."""
    try:
        stamp = datetime.fromisoformat(timestamp_iso).strftime("%Y%m%d_%H%M%S")
    except (ValueError, TypeError):
        stamp = "00000000_000000"
    return f"run_{stamp}_{fingerprint[:4]}"


# ===========================================================================
#  Construction d'un record (mise en forme — aucun calcul moteur ici)
# ===========================================================================
def flat_params_from_snapshot(snapshot: Any) -> dict[str, Any]:
    """Dérive les paramètres « plats » (consommés par le helper moteur partagé)
    depuis un AppliedSnapshot, EXACTEMENT comme `project_shared_keys` :

      - feeder1 (main)  → débit g/min + densité bulk ;
      - feeder2 (side)  → zone si activé et positionné sur « Z.. », sinon 0.

    Duck-typing : on lit les attributs du snapshot sans importer son type
    (aucune modification d'AgentIndustrial_v1/).
    """
    feeders = list(getattr(snapshot, "feeders", []) or [])
    main = feeders[0] if feeders else {}
    feed_g_per_min = float(main.get("mass_flow_g_per_min", 0.0)) if main else 0.0
    bulk_density = float(main.get("density_g_per_cm3", 0.55)) if main else 0.55

    side_feeder_zone = 0  # SIDE_FEEDER_DISABLED_ZONE
    if len(feeders) > 1:
        sf = feeders[1]
        pos = str(sf.get("position", ""))
        if sf.get("enabled") and pos.startswith("Z"):
            try:
                side_feeder_zone = int(pos[1:])
            except ValueError:
                side_feeder_zone = 0
    return {
        "config": list(getattr(snapshot, "screw_config", []) or []),
        "screw_rpm": float(getattr(snapshot, "screw_rpm", 0.0)),
        "feed_g_per_min": feed_g_per_min,
        "bulk_density": bulk_density,
        "side_feeder_zone": side_feeder_zone,
    }


def _feeder_composition_block(feeders: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Capture la composition matière par feeder (Phase 9 manager 2026-06-09).

    Pour chaque feeder ACTIVÉ (enabled=True) du banc, on stocke :
      - feeder_id, label, position, material_id (identifiant matière physique
        sérialisé dans AppliedSnapshot) ;
      - composition CHIMIQUE renseignée par l'opérateur (`polymer_name`) ;
      - propriétés thermiques étendues si saisies (T_dég, TGA, viscosité, Tm, Tg) ;
      - débit + densité bulk au moment du commit.

    Règles strictes (manager 2026-06-09 / review adversariale) :
      - si `polymer_name` est vide : composition = None (pas de chaîne en dur
        type « Non renseigné » ; l'UI traduit None via i18n). L'historique
        reflète ce que l'opérateur a réellement saisi — jamais « LFP » par défaut.
      - aucun champ « state » fantôme : `state`/phase matière n'est PAS sérialisé
        dans AppliedSnapshot._feeder_to_dict. L'utiliser ici renverrait toujours
        une valeur démo par défaut, ce qui violerait « aucune valeur démo/défaut
        injectée silencieusement » (review adversariale 2026-06-09 — corrigé).
    """
    out: list[dict[str, Any]] = []
    for f in feeders or []:
        if not f.get("enabled"):
            continue
        poly = str(f.get("polymer_name", "") or "").strip()
        out.append({
            "feeder_id": int(f.get("feeder_id", 0) or 0),
            "label": str(f.get("label", "") or ""),
            "position": str(f.get("position", "") or ""),
            "material_id": f.get("material_id"),
            "composition": poly if poly else None,
            "composition_source": ("USER_INPUT" if poly else "NOT_AVAILABLE"),
            "mass_flow_g_per_min": float(f.get("mass_flow_g_per_min") or 0.0),
            "bulk_density_g_per_cm3": float(f.get("density_g_per_cm3") or 0.0),
            "thermal_expansion_per_K": float(f.get("thermal_expansion_per_K") or 0.0),
            "t_degradation_C": f.get("t_degradation_C"),
            "tga_onset_C": f.get("tga_onset_C"),
            "viscosity_pa_s": f.get("viscosity_pa_s"),
            "t_melt_C": f.get("t_melt_C"),
            "t_glass_C": f.get("t_glass_C"),
        })
    return out


def _config_block(snapshot: Any) -> dict[str, Any]:
    """Bloc « config utile » lisible — uniquement des champs réellement stockés.

    Phase 9 manager 2026-06-09 : ajoute la composition par feeder activée
    (`feeders_composition`), pour qu'un run LFP/LATP/PVDF mixé soit traçable
    à l'audit. Aucune matière n'est inventée si vide.
    """
    feeders = list(getattr(snapshot, "feeders", []) or [])
    main = feeders[0] if feeders else {}
    enabled = [f for f in feeders if f.get("enabled")]
    try:
        n_elements = float(count_user_elements(list(getattr(snapshot, "screw_config", []) or [])))
    except Exception:
        n_elements = None
    return {
        "screw_rpm": float(getattr(snapshot, "screw_rpm", 0.0)),
        "n_elements": n_elements,
        "feeders_actifs": len(enabled),
        "debit_principal_g_min": (
            float(main.get("mass_flow_g_per_min", 0.0)) if main else None
        ),
        "matiere_principale": (main.get("material_id") if main else None),
        # Phase 9 : composition complète par feeder activé (jamais inventée).
        "feeders_composition": _feeder_composition_block(feeders),
        "zones_die": int(getattr(snapshot, "n_die_zones", 0) or 0),
        "temps_consigne_C": {
            k: float(v) for k, v in dict(getattr(snapshot, "zone_temps_C", {}) or {}).items()
        },
    }


def _engine_kpis_block(report: Any) -> dict[str, Any]:
    """KPIs moteur FIGÉS depuis l'EngineReport. Aucun recalcul, aucune invention.

    Si `report` est None (cas dégénéré : impossible de construire le rapport), le
    bloc reste vide (KPIs = None), jamais inventé.
    """
    if report is None:
        keys = (
            "couple_total_nm", "sme_kwh_kg", "residence_s", "fill_moyen",
            "fill_crete", "cisaillement_max_s", "debit_massique_kg_h",
            "debit_sortie_pointe_cm3_s",
        )
        return {k: None for k in keys}
    return {
        "couple_total_nm": float(report.total_torque_nm),
        "sme_kwh_kg": float(report.total_sme_kwh_per_kg),
        "residence_s": float(report.residence_time_total_s),
        "fill_moyen": float(report.fill_factor_average),
        "fill_crete": float(report.peak_fill_factor),
        "cisaillement_max_s": float(report.max_shear_rate_s),
        "debit_massique_kg_h": float(report.mass_flow_kg_per_h),
        "debit_sortie_pointe_cm3_s": float(report.output_vol_flow_cm3_s),
    }


def _zones_block(report: Any) -> list[dict[str, Any]] | None:
    """Agrégats par zone figés depuis EngineReport.zones (None si indisponible)."""
    if report is None or not getattr(report, "zones", None):
        return None
    return [
        {
            "zone": int(z.zone),
            "fill_moyen": float(z.mean_fill_factor),
            "fill_crete": float(z.max_fill_factor),
            "residence_s": float(z.residence_time_s),
            "matiere_dominante": z.dominant_material,
        }
        for z in report.zones
    ]


def make_record(
    snapshot: Any,
    report: Any,
    source: str = SOURCE_MANUAL,
    agent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit le record persistant complet depuis un snapshot + EngineReport.

    `agent` reste `None` par défaut : le statut agent (décision/score/alertes)
    n'est PAS disponible au moment du commit — on ne l'invente pas.
    """
    feeders = list(getattr(snapshot, "feeders", []) or [])
    timestamp_iso = str(getattr(snapshot, "timestamp_iso", "") or "")
    fingerprint = compute_fingerprint(
        list(getattr(snapshot, "screw_config", []) or []),
        float(getattr(snapshot, "screw_rpm", 0.0)),
        feeders,
        dict(getattr(snapshot, "zone_temps_C", {}) or {}),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "id": _make_id(timestamp_iso, fingerprint),
        "timestamp_iso": timestamp_iso,
        "label": str(getattr(snapshot, "label", "") or ""),
        "source": source if source in (SOURCE_MANUAL, SOURCE_DEMO) else SOURCE_MANUAL,
        "status": STATUS_ACTIVE,  # normalisé à la lecture (dernier = actif)
        "fingerprint": fingerprint,
        "config": _config_block(snapshot),
        "engine_kpis": _engine_kpis_block(report),
        "zones": _zones_block(report),
        "agent": dict(agent) if agent else None,
    }


# ===========================================================================
#  Lecture / écriture disque (défensives)
# ===========================================================================
def _resolve(path: Path | str | None) -> Path:
    """Chemin effectif : argument explicite > variable d'env > défaut.

    L'override d'env est lu dynamiquement (pas figé à l'import) pour permettre
    aux tests/CI d'isoler le stockage sans modifier le code appelant.
    """
    if path is not None:
        return Path(path)
    env = os.environ.get(HISTORY_PATH_ENV)
    return Path(env) if env else DEFAULT_HISTORY_PATH


def _is_valid_record(rec: Any) -> bool:
    return isinstance(rec, dict) and "fingerprint" in rec and "timestamp_iso" in rec


def read_runs(path: Path | str | None = None) -> LoadResult:
    """Lecture défensive complète du stockage.

    - fichier absent/vide   → runs=[] (corrupt=False) ;
    - JSON cassé            → runs=[], corrupt=True, error renseigné ;
    - records malformés     → ignorés et comptés dans `skipped` ;
    - statut NORMALISÉ      → dernier record = actif, les autres = archivé.
    """
    p = _resolve(path)
    if not p.exists():
        return LoadResult(runs=[])
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return LoadResult(runs=[], corrupt=True, error=f"Lecture impossible : {exc}")
    if not raw:
        return LoadResult(runs=[])
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return LoadResult(runs=[], corrupt=True, error=f"JSON illisible : {exc}")
    if not isinstance(data, list):
        return LoadResult(runs=[], corrupt=True, error="Format inattendu (liste attendue).")

    valid = [r for r in data if _is_valid_record(r)]
    skipped = len(data) - len(valid)
    # Normalisation du statut : seul le dernier (le plus récent) est actif.
    for i, rec in enumerate(valid):
        rec["status"] = STATUS_ACTIVE if i == len(valid) - 1 else STATUS_ARCHIVED
    return LoadResult(runs=valid, skipped=skipped)


def load_runs(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Raccourci : liste des runs valides (statut normalisé). Jamais d'exception."""
    return read_runs(path).runs


def _atomic_write(p: Path, data: list[dict[str, Any]]) -> None:
    """Écriture atomique : fichier temporaire dans le même dossier + os.replace."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, p)


def append_run(record: Mapping[str, Any], path: Path | str | None = None) -> bool:
    """Ajoute un record au stockage persistant.

    Anti-doublon (Skip) : si l'empreinte du record est IDENTIQUE à celle du
    dernier record déjà persistant, on N'AJOUTE RIEN et on renvoie False.
    Renvoie True si le record a été ajouté.
    """
    p = _resolve(path)
    existing = read_runs(p).runs  # repart d'une base saine (records valides)
    fp = record.get("fingerprint")
    if existing and fp is not None and existing[-1].get("fingerprint") == fp:
        return False  # doublon exact du dernier enregistrement → skip
    existing.append(dict(record))
    _atomic_write(p, existing)
    return True
