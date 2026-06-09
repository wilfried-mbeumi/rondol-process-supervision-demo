"""operator_store.py — source de vérité opérateur CENTRALE et PERSISTANTE.

Problème résolu : les saisies opérateur vivaient dans des clés de widget /
clés de session non fiables. Streamlit purge les clés de widget non montées en
navigation multipage, et un refresh navigateur réinitialise toute la session →
les valeurs saisies sur /Profile étaient perdues sur /Moteur_Procede.

Solution : UN store central, en deux niveaux, indépendant des widgets :
  1. `st.session_state["current_run_persist"]` : dict NON lié à un widget →
     survit à la navigation multipage et au changement de langue.
  2. Miroir DISQUE (JSON) → survit au refresh navigateur / nouvelle session.
     Chemin via env `RONDOL_RUN_STATE_PATH` (isolé en test), sinon défaut data/.

Contrat (exigence manager) :
  - chaque page de SAISIE écrit ses valeurs dans le store (`capture_operator_state`) ;
  - chaque page RESTAURE les clés métier depuis le store en tête de script
    (`restore_operator_state`) AVANT d'instancier ses widgets ;
  - les pages métier lisent ensuite ces clés via current_run_state / adapter ;
  - jamais d'écrasement d'une valeur présente par un défaut silencieux
    (restore n'écrit QUE les clés absentes).

Module app (peut être lu par les pages). Aucune formule métier, aucune constante
PLC : ne fait que sauvegarder / restaurer des valeurs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, MutableMapping

# Clé session du store central (NON liée à un widget).
STORE_KEY = "current_run_persist"

# Champs métier opérateur suivis (clés canoniques de session).
_BASE_KEYS = (
    "screw_config", "screw_rpm", "bulk_density", "feeder_g_per_min",
    "side_feeder_zone", "n_die_zones", "target_screw_count",
    "feeder_rpm", "feeder_calib_g_h_per_rpm",
)
# Étalonnage feeders #2..#5 (multi-feeder).
_MULTI_KEYS = tuple(
    f"feedcal_{kind}_{fid}" for fid in range(2, 6) for kind in ("rpm", "coeff")
)
# Consignes thermiques Z1..Z8 + jusqu'à 4 zones DIE (n_die_zones ∈ [0..4]).
_THERMAL_KEYS = (
    "th_Z1", "th_Z2", "th_Z3", "th_Z4", "th_Z5", "th_Z6", "th_Z7", "th_Z8",
    "th_die", "th_die2", "th_die3", "th_die4",
)
# Banc feeders Settings #1..#5 : activation, label, matière, ρ, α, position,
# débit g/min, composition (polymère + T° dégradation / TGA / viscosité / Tm / Tg).
# Capturer ces clés permet à la composition matière par feeder de survivre à la
# navigation et au refresh (exigence Phase 9).
_FEEDER_SETTINGS_KEYS = tuple(
    f"fd_{kind}_{fid}"
    for fid in range(1, 6)
    for kind in ("en", "lbl", "mat", "dens", "alpha", "pos", "flow",
                 "poly", "tdeg", "tga", "visc", "tmelt", "tglass")
)
OPERATOR_KEYS: tuple[str, ...] = (
    _BASE_KEYS + _MULTI_KEYS + _THERMAL_KEYS + _FEEDER_SETTINGS_KEYS
)

_ENV_PATH = "RONDOL_RUN_STATE_PATH"
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "run_state" / "current_run_state.json"


# ---------------------------------------------------------------------------
# Accès store session (proxy-safe)
# ---------------------------------------------------------------------------
def _store(session: MutableMapping[str, Any]) -> dict[str, Any]:
    """Retourne le dict store central (créé si absent)."""
    try:
        existing = session[STORE_KEY] if STORE_KEY in session else None
    except Exception:  # pragma: no cover
        existing = None
    if not isinstance(existing, dict):
        existing = {}
        session[STORE_KEY] = existing
    return existing


def _disk_path() -> Path:
    raw = os.environ.get(_ENV_PATH)
    return Path(raw) if raw else _DEFAULT_PATH


def _disk_save(store: Mapping[str, Any]) -> None:
    """Sauvegarde best-effort sur disque (ne lève jamais)."""
    try:
        p = _disk_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(store)), encoding="utf-8")
    except Exception:  # pragma: no cover - persistance best-effort
        pass


def _disk_load() -> dict[str, Any]:
    """Charge le store disque (dict vide si absent/illisible)."""
    try:
        p = _disk_path()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:  # pragma: no cover
        pass
    return {}


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def update_current_run_field(session: MutableMapping[str, Any], field: str, value: Any) -> None:
    """Écrit immédiatement une valeur opérateur dans le store (session + disque)."""
    store = _store(session)
    store[field] = value
    _disk_save(store)


def get_current_run_field(session: Mapping[str, Any], field: str, default: Any = None) -> Any:
    """Lit une valeur du store (session, sinon disque, sinon défaut)."""
    try:
        store = session[STORE_KEY] if STORE_KEY in session else None
    except Exception:  # pragma: no cover
        store = None
    if isinstance(store, dict) and field in store:
        return store[field]
    disk = _disk_load()
    return disk.get(field, default)


def capture_operator_state(session: MutableMapping[str, Any]) -> dict[str, Any]:
    """Capture les clés métier présentes en session → store (session + disque).

    Appelé par les pages de SAISIE (Profile, Settings) APRÈS le rendu des widgets.
    Ne capture que les clés réellement présentes (jamais de défaut inventé).
    """
    store = _store(session)
    for key in OPERATOR_KEYS:
        try:
            if key in session:
                store[key] = session[key]
        except Exception:  # pragma: no cover
            continue
    _disk_save(store)
    return store


def save_current_run_state(session: MutableMapping[str, Any]) -> dict[str, Any]:
    """Alias explicite de capture (sauvegarde complète de l'état opérateur)."""
    return capture_operator_state(session)


def load_current_run_state(session: Mapping[str, Any]) -> dict[str, Any]:
    """Retourne l'état opérateur central (session prioritaire, sinon disque)."""
    try:
        store = session[STORE_KEY] if STORE_KEY in session else None
    except Exception:  # pragma: no cover
        store = None
    if isinstance(store, dict) and store:
        return dict(store)
    return _disk_load()


def restore_operator_state(session: MutableMapping[str, Any]) -> None:
    """Restaure les clés métier ABSENTES de la session depuis le store/disque.

    À appeler en TÊTE de chaque page, avant l'instanciation des widgets, pour
    que les valeurs saisies survivent à : navigation multipage, changement de
    langue, purge des clés de widget, refresh navigateur (via le miroir disque).

    Règle stricte : n'écrit QUE les clés absentes (ne JAMAIS écraser une valeur
    déjà présente en session par le store).
    """
    # Hydrate le store session depuis le disque si la session est neuve (refresh).
    store = _store(session)
    if not store:
        disk = _disk_load()
        if disk:
            store.update(disk)

    for key, value in store.items():
        try:
            if key not in session:
                session[key] = value
        except Exception:  # pragma: no cover
            continue
