"""persistence.py — couche de persistance DURABLE de l'état validé (P0 manager).

Problème résolu : `data/run_state/applied_state.json` vit sur le disque
ÉPHÉMÈRE de Streamlit Cloud — un reboot/redeploy efface la sauvegarde
opérateur. Ce module est désormais la SEULE porte d'entrée/sortie de la
persistance du snapshot validé, avec des backends par ordre de priorité :

  1. **Supabase / Postgres (REST)** — production Streamlit Cloud. Configuré
     via les secrets Streamlit (`.streamlit/secrets.toml`) :
         [supabase]
         url = "https://xxxx.supabase.co"
         key = "service-or-anon-key"
         table = "rondol_state"          # optionnel, défaut rondol_state
     ou via env : RONDOL_SUPABASE_URL / RONDOL_SUPABASE_KEY / RONDOL_SUPABASE_TABLE.
     Schéma attendu : table {key text primary key, payload jsonb}.
  2. **Store externe fichier** — env `RONDOL_EXTERNAL_STORE_PATH` : un chemin
     HORS du disque éphémère (volume monté, partage réseau). Sert aussi de
     backend durable simulé pour les tests E2E reboot.
  3. **JSON local** (`applied_state.json`) — fallback dev uniquement. Survit au
     refresh navigateur mais PAS à un reboot/redeploy cloud. Quand c'est le
     seul backend, les pages de saisie affichent un avertissement explicite
     (« Persistent storage not configured… ») — on ne prétend JAMAIS que le
     fallback local est production-ready.

API (exigence manager) :
  - save_applied_state(payload, run_label=None) -> str (nom du backend écrit)
  - load_applied_state() -> dict | None   (backend durable d'abord, sinon local)
  - has_applied_state() -> bool
  - backend_name() / is_durable()

Toutes les opérations sont best-effort (timeout court, jamais d'exception
propagée) : une panne réseau ne doit jamais casser un enregistrement local.
`AgentIndustrial_v1.core.applied_state` délègue son miroir disque à cette
couche (import paresseux) → TOUTES les pages (Settings, Profile, Supervision,
Run Analysis, History, Process Engine) lisent la persistance durable via le
chemin unique commit()/get_applied()/hydrate_session_from_applied().
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

_STATE_KEY = "applied_state"
_DEFAULT_TABLE = "rondol_state"
_HTTP_TIMEOUT_S = 4.0

# Chemin JSON local — MÊME convention que core.applied_state (fallback dev).
_ENV_LOCAL_PATH = "RONDOL_APPLIED_STATE_PATH"
_DEFAULT_LOCAL_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "run_state" / "applied_state.json"
)


def _local_path() -> Path:
    raw = os.environ.get(_ENV_LOCAL_PATH)
    return Path(raw) if raw else _DEFAULT_LOCAL_PATH


# ---------------------------------------------------------------------------
# Lecture configuration (env > secrets Streamlit) — jamais d'exception.
# ---------------------------------------------------------------------------
def _streamlit_secret(section: str, name: str) -> str | None:
    try:
        import streamlit as st  # noqa: PLC0415
        sec = st.secrets.get(section)  # type: ignore[attr-defined]
        if isinstance(sec, Mapping) and name in sec:
            v = str(sec[name]).strip()
            return v or None
    except Exception:
        pass
    return None


def _supabase_config() -> dict[str, str] | None:
    url = os.environ.get("RONDOL_SUPABASE_URL") or _streamlit_secret("supabase", "url")
    key = os.environ.get("RONDOL_SUPABASE_KEY") or _streamlit_secret("supabase", "key")
    if not url or not key:
        return None
    table = (
        os.environ.get("RONDOL_SUPABASE_TABLE")
        or _streamlit_secret("supabase", "table")
        or _DEFAULT_TABLE
    )
    return {"url": url.rstrip("/"), "key": key, "table": table}


def _external_store_path() -> Path | None:
    raw = os.environ.get("RONDOL_EXTERNAL_STORE_PATH")
    return Path(raw) if raw else None


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def _supabase_save(cfg: Mapping[str, str], payload: Mapping[str, Any]) -> bool:
    try:
        import requests  # noqa: PLC0415 — dépendance de Streamlit
        resp = requests.post(
            f"{cfg['url']}/rest/v1/{cfg['table']}",
            headers={
                "apikey": cfg["key"],
                "Authorization": f"Bearer {cfg['key']}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json=[{"key": _STATE_KEY, "payload": dict(payload)}],
            timeout=_HTTP_TIMEOUT_S,
        )
        return 200 <= resp.status_code < 300
    except Exception:
        return False


def _supabase_load(cfg: Mapping[str, str]) -> dict[str, Any] | None:
    try:
        import requests  # noqa: PLC0415
        resp = requests.get(
            f"{cfg['url']}/rest/v1/{cfg['table']}",
            headers={
                "apikey": cfg["key"],
                "Authorization": f"Bearer {cfg['key']}",
            },
            params={"key": f"eq.{_STATE_KEY}", "select": "payload"},
            timeout=_HTTP_TIMEOUT_S,
        )
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            payload = rows[0].get("payload")
            if isinstance(payload, dict):
                return payload
    except Exception:
        return None
    return None


def _file_save(path: Path, payload: Mapping[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(payload), ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _file_load(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("screw_config") is not None:
            return data
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def backend_name() -> str:
    """Backend durable actif : 'supabase' | 'external-file' | 'local-json'."""
    if _supabase_config() is not None:
        return "supabase"
    if _external_store_path() is not None:
        return "external-file"
    return "local-json"


def is_durable() -> bool:
    """True si un backend survivant au reboot/redeploy cloud est configuré."""
    return backend_name() != "local-json"


def save_applied_state(
    payload: Mapping[str, Any], run_label: str | None = None,
) -> str:
    """Persiste le snapshot validé (dict JSON-safe). Retourne le backend écrit.

    Écrit TOUJOURS le JSON local (lecture rapide intra-session / dev) PUIS le
    backend durable s'il est configuré. Best-effort : ne lève jamais.
    """
    data = dict(payload)
    if run_label is not None and not data.get("label"):
        data["label"] = str(run_label)

    _file_save(_local_path(), data)

    cfg = _supabase_config()
    if cfg is not None:
        return "supabase" if _supabase_save(cfg, data) else "local-json"
    ext = _external_store_path()
    if ext is not None:
        return "external-file" if _file_save(ext, data) else "local-json"
    return "local-json"


def load_applied_state() -> dict[str, Any] | None:
    """Relit le snapshot validé : backend durable d'abord, sinon JSON local."""
    cfg = _supabase_config()
    if cfg is not None:
        payload = _supabase_load(cfg)
        if payload is not None:
            return payload
    ext = _external_store_path()
    if ext is not None:
        payload = _file_load(ext)
        if payload is not None:
            return payload
    return _file_load(_local_path())


def has_applied_state() -> bool:
    """True si un snapshot validé existe dans la persistance (durable ou locale)."""
    return load_applied_state() is not None
