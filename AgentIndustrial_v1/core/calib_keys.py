"""
calib_keys.py — Clés d'étalonnage feeder partagées (source unique des conventions).

Cause racine prod 2026-06-12 : l'étalonnage feeder (RPM × coefficient g/h/RPM)
ne vivait QUE dans les clés de session / le store opérateur — jamais dans le
snapshot validé (`applied_state`). Après un refresh navigateur, le débit réel
4.17 g/min dépendait d'une 2e source de persistance (current_run_state.json) qui
pouvait diverger du snapshot → Settings revenait à 0, le bandeau « UNSAVED
CHANGES » s'affichait, Moteur Procédé perdait le débit.

Ce module centralise les conventions de clés (jusqu'ici dupliquées entre
`app/feeder_ui.py` et `core/editing_state.py`) et fournit :
  - `collect_calibrations(session)` : sérialise l'étalonnage courant pour le
    snapshot validé (commit) ;
  - `seed_calibrations(session, cals)` : re-sème les clés de session depuis le
    snapshot restauré (setdefault-only — n'écrase JAMAIS une saisie vivante).

Module PUR : aucune dépendance Streamlit ni disque.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from .coercion import safe_float

# Feeder #1 = clés legacy historiques ; feeders #2..#5 = feedcal_{rpm,coeff}_{id}.
FEEDER1_RPM_KEY = "feeder_rpm"
FEEDER1_COEFF_KEY = "feeder_calib_g_h_per_rpm"
PERSIST_SUFFIX = "__persist"
FEEDER_IDS: tuple[int, ...] = (1, 2, 3, 4, 5)


def feedcal_rpm_key(feeder_id: int) -> str:
    return FEEDER1_RPM_KEY if int(feeder_id) == 1 else f"feedcal_rpm_{int(feeder_id)}"


def feedcal_coeff_key(feeder_id: int) -> str:
    return FEEDER1_COEFF_KEY if int(feeder_id) == 1 else f"feedcal_coeff_{int(feeder_id)}"


def _read_raw(session: Mapping[str, Any], key: str) -> Any:
    """Lecture nav-safe : clé widget, sinon miroir persistant, sinon None."""
    try:
        if key in session:
            return session[key]
        pk = key + PERSIST_SUFFIX
        if pk in session:
            return session[pk]
    except Exception:  # pragma: no cover - proxy hors contexte
        pass
    return None


def calib_read(session: Mapping[str, Any], key: str, default: float) -> float:
    v = _read_raw(session, key)
    return safe_float(v, default, 0.0, 100000.0) if v is not None else default


def collect_calibrations(session: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """Sérialise l'étalonnage feeder courant (pour le snapshot validé).

    Ne capture que les feeders dont au moins une clé est réellement présente
    en session — jamais de valeur inventée.
    """
    out: dict[str, dict[str, float]] = {}
    for fid in FEEDER_IDS:
        rpm_raw = _read_raw(session, feedcal_rpm_key(fid))
        coeff_raw = _read_raw(session, feedcal_coeff_key(fid))
        if rpm_raw is None and coeff_raw is None:
            continue
        out[str(fid)] = {
            "rpm": safe_float(rpm_raw, 0.0, 0.0, 100000.0) if rpm_raw is not None else 0.0,
            "coeff": safe_float(coeff_raw, 0.0, 0.0, 100000.0) if coeff_raw is not None else 0.0,
        }
    return out


def seed_calibrations(
    session: MutableMapping[str, Any], cals: Mapping[str, Mapping[str, Any]],
) -> None:
    """Re-sème les clés d'étalonnage depuis un snapshot restauré.

    setdefault-only : ne touche JAMAIS une clé déjà présente (édition vivante).
    Sème aussi le miroir persistant (survie navigation multipage).
    """
    if not cals:
        return
    for fid_str, vals in cals.items():
        try:
            fid = int(fid_str)
        except (TypeError, ValueError):
            continue
        for kind, key in (("rpm", feedcal_rpm_key(fid)), ("coeff", feedcal_coeff_key(fid))):
            try:
                val = safe_float(vals.get(kind, 0.0), 0.0, 0.0, 100000.0)
            except Exception:
                continue
            try:
                if key not in session:
                    session[key] = val
                if key + PERSIST_SUFFIX not in session:
                    session[key + PERSIST_SUFFIX] = val
            except Exception:  # pragma: no cover - proxy hors contexte
                continue
