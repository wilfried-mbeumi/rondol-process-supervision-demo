# -*- coding: utf-8 -*-
"""Authentification de la plateforme Rondol — garde de connexion + traçabilité.

Objectif : exiger une connexion avant l'accès aux pages, et journaliser chaque
tentative (succès/échec) dans une base durable — pour démontrer l'interaction
réelle de l'application avec sa base de données (exigence guide école).

Sécurité :
  - Le mot de passe n'est JAMAIS stocké ni journalisé en clair. On conserve un
    hash PBKDF2-HMAC-SHA256 (200 000 itérations) avec sel aléatoire par
    utilisateur, dans la table `app_users`.
  - Les identifiants de test sont documentés hors dépôt public (PDR du ZIP).

Backends (même principe que app/persistence.py) :
  1. Supabase / PostgreSQL (REST) — production. Tables `app_users`,
     `login_history`. Configuré via secrets `[supabase]` / variables
     RONDOL_SUPABASE_*.
  2. Repli fichier local (`data/auth/…json`) — dev local sans Supabase.

Bypass de test : si la variable d'environnement RONDOL_DISABLE_AUTH == "1",
`require_login` est un no-op — les tests d'intégration des pages (AppTest)
ne sont pas affectés et pilotent les pages comme avant.

API publique :
  - hash_password(pw, salt=None) -> (salt_hex, hash_hex)
  - verify_password(pw, salt_hex, hash_hex) -> bool
  - verify_credentials(email, pw) -> bool
  - record_login(email, success, source="app") -> None
  - get_login_history(limit=50) -> list[dict]
  - upsert_user(email, pw) -> str   (backend écrit ; utilisé par le seed)
  - require_login(st) -> None       (garde ; rend le formulaire et st.stop())
  - logout(st) -> None
  - current_user(st) -> str | None
  - backend_name() -> "supabase" | "file"
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets as _secrets
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_ITERATIONS = 200_000
_ALGO = "sha256"
_HTTP_TIMEOUT_S = 6.0
_USERS_TABLE = "app_users"
_HISTORY_TABLE = "login_history"

_SESSION_KEY = "auth_email"
_ENV_DISABLE = "RONDOL_DISABLE_AUTH"
_ENV_USERS_PATH = "RONDOL_AUTH_USERS_PATH"
_ENV_HISTORY_PATH = "RONDOL_AUTH_HISTORY_PATH"


# ---------------------------------------------------------------------------
# Hachage (PBKDF2, stdlib — aucune dépendance externe)
# ---------------------------------------------------------------------------
def hash_password(pw: str, salt: str | None = None) -> tuple[str, str]:
    """Retourne (salt_hex, hash_hex). Génère un sel aléatoire si absent."""
    if salt is None:
        salt = _secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(_ALGO, pw.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return salt, dk.hex()


def verify_password(pw: str, salt_hex: str, hash_hex: str) -> bool:
    """Comparaison en temps constant du hash recalculé."""
    try:
        _, computed = hash_password(pw, salt_hex)
    except Exception:
        return False
    return _secrets.compare_digest(computed, hash_hex)


# ---------------------------------------------------------------------------
# Configuration Supabase (lecture des mêmes secrets que persistence.py)
# ---------------------------------------------------------------------------
def _streamlit_secret(section: str, name: str) -> str | None:
    # Lecture alignée sur app/persistence.py (pattern éprouvé en production).
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
    # SOURCE UNIQUE : réutiliser exactement la résolution de la persistance
    # procédé, pour que l'authentification voie Supabase quand — et seulement
    # quand — la persistance le voit (évite toute divergence env/secrets).
    try:
        import persistence  # noqa: PLC0415
        cfg = persistence._supabase_config()
        if cfg and cfg.get("url") and cfg.get("key"):
            return {"url": cfg["url"].rstrip("/"), "key": cfg["key"]}
    except Exception:
        pass
    # Repli direct (dev local sans le module persistence sur le chemin).
    url = os.environ.get("RONDOL_SUPABASE_URL") or _streamlit_secret("supabase", "url")
    key = os.environ.get("RONDOL_SUPABASE_KEY") or _streamlit_secret("supabase", "key")
    if not url or not key:
        return None
    return {"url": url.rstrip("/"), "key": key}


def backend_name() -> str:
    return "supabase" if _supabase_config() else "file"


def _headers(cfg: Mapping[str, str], write: bool = False) -> dict[str, str]:
    h = {"apikey": cfg["key"], "Authorization": f"Bearer {cfg['key']}"}
    if write:
        h["Content-Type"] = "application/json"
        h["Prefer"] = "resolution=merge-duplicates"
    return h


# ---------------------------------------------------------------------------
# Repli fichier local
# ---------------------------------------------------------------------------
def _users_path() -> Path:
    p = os.environ.get(_ENV_USERS_PATH)
    base = Path(p) if p else Path(__file__).resolve().parent.parent / "data" / "auth" / "users.json"
    base.parent.mkdir(parents=True, exist_ok=True)
    return base


def _history_path() -> Path:
    p = os.environ.get(_ENV_HISTORY_PATH)
    base = Path(p) if p else Path(__file__).resolve().parent.parent / "data" / "auth" / "login_history.json"
    base.parent.mkdir(parents=True, exist_ok=True)
    return base


def _file_read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _file_write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------
def upsert_user(email: str, pw: str) -> str:
    """Crée/met à jour un utilisateur. Retourne le backend écrit."""
    email = email.strip().lower()
    salt, h = hash_password(pw)
    cfg = _supabase_config()
    if cfg:
        import requests  # noqa: PLC0415
        resp = requests.post(
            f"{cfg['url']}/rest/v1/{_USERS_TABLE}",
            headers=_headers(cfg, write=True),
            json=[{"email": email, "salt": salt, "pw_hash": h}],
            timeout=_HTTP_TIMEOUT_S,
        )
        if not (200 <= resp.status_code < 300):
            hint = ""
            if resp.status_code == 404 or "PGRST205" in resp.text:
                hint = (
                    "\n→ La table 'app_users' n'existe pas encore. Crée les tables "
                    "d'abord : exécute database/auth_tables.sql dans le SQL Editor Supabase."
                )
            raise RuntimeError(
                f"Supabase upsert user a échoué ({resp.status_code}) : {resp.text[:200]}{hint}"
            )
        return "supabase"
    users = _file_read(_users_path()) or {}
    users[email] = {"salt": salt, "pw_hash": h}
    _file_write(_users_path(), users)
    return "file"


def _get_user(email: str) -> dict[str, str] | None:
    email = email.strip().lower()
    cfg = _supabase_config()
    if cfg:
        import requests  # noqa: PLC0415
        try:
            resp = requests.get(
                f"{cfg['url']}/rest/v1/{_USERS_TABLE}",
                headers=_headers(cfg),
                params={"email": f"eq.{email}", "select": "email,salt,pw_hash", "limit": 1},
                timeout=_HTTP_TIMEOUT_S,
            )
            if 200 <= resp.status_code < 300:
                rows = resp.json()
                return rows[0] if rows else None
        except Exception:
            return None
        return None
    users = _file_read(_users_path()) or {}
    return users.get(email)


def verify_credentials(email: str, pw: str) -> bool:
    u = _get_user(email)
    if not u:
        return False
    return verify_password(pw, u.get("salt", ""), u.get("pw_hash", ""))


# ---------------------------------------------------------------------------
# Historique de connexion
# ---------------------------------------------------------------------------
def record_login(email: str, success: bool, source: str = "app") -> None:
    """Journalise une tentative. Ne lève jamais — la traçabilité ne doit pas
    bloquer la connexion en cas d'indisponibilité de la base."""
    email = (email or "").strip().lower()
    cfg = _supabase_config()
    if cfg:
        try:
            import requests  # noqa: PLC0415
            requests.post(
                f"{cfg['url']}/rest/v1/{_HISTORY_TABLE}",
                headers={k: v for k, v in _headers(cfg, write=True).items() if k != "Prefer"},
                json=[{"email": email, "success": success, "source": source}],
                timeout=_HTTP_TIMEOUT_S,
            )
        except Exception:
            pass
        return
    hist = _file_read(_history_path()) or []
    # horodatage sans dépendance à une horloge non déterministe côté tests :
    # en repli fichier on stocke un compteur monotone + le flag.
    hist.append({"email": email, "success": success, "source": source, "seq": len(hist) + 1})
    _file_write(_history_path(), hist)


def get_login_history(limit: int = 50) -> list[dict[str, Any]]:
    cfg = _supabase_config()
    if cfg:
        try:
            import requests  # noqa: PLC0415
            resp = requests.get(
                f"{cfg['url']}/rest/v1/{_HISTORY_TABLE}",
                headers=_headers(cfg),
                params={"select": "email,success,source,ts", "order": "ts.desc", "limit": limit},
                timeout=_HTTP_TIMEOUT_S,
            )
            if 200 <= resp.status_code < 300:
                return list(resp.json())
        except Exception:
            return []
        return []
    hist = _file_read(_history_path()) or []
    return list(reversed(hist))[:limit]


# ---------------------------------------------------------------------------
# Garde d'accès (Streamlit)
# ---------------------------------------------------------------------------
def current_user(st) -> str | None:
    return st.session_state.get(_SESSION_KEY)


def logout(st) -> None:
    st.session_state.pop(_SESSION_KEY, None)


def _render_login(st) -> None:
    st.markdown("## 🔒 Rondol · Connexion")
    st.caption(
        "Plateforme prédictive d'aide à la décision — accès réservé. "
        "Identifiants de test fournis dans le PDR de dépôt."
    )
    # --- Diagnostic temporaire (à retirer une fois l'auth confirmée) ----------
    try:
        _cfg = _supabase_config()
        _diag = f"diag · backend={backend_name()} · supabase_cfg={'oui' if _cfg else 'non'}"
        if _cfg:
            _diag += f" · url_ok={_cfg.get('url','')[:24]}… · key_prefix={_cfg.get('key','')[:12]}…"
    except Exception as _e:  # noqa: BLE001
        _diag = f"diag · erreur config: {type(_e).__name__}"
    st.caption(_diag)
    # -------------------------------------------------------------------------
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", key="login_email", placeholder="demo@rondol.local")
        pw = st.text_input("Mot de passe", key="login_pw", type="password")
        submitted = st.form_submit_button("Se connecter")
    if submitted:
        if verify_credentials(email, pw):
            record_login(email, True)
            st.session_state[_SESSION_KEY] = email.strip().lower()
            st.rerun()
        else:
            record_login(email, False)
            st.error("Identifiants invalides. Tentative enregistrée.")


def require_login(st) -> None:
    """Garde à placer en tête de chaque page (après set_page_config).

    - No-op si RONDOL_DISABLE_AUTH == "1" (tests).
    - No-op si déjà authentifié dans la session.
    - Sinon : rend le formulaire de connexion et arrête le rendu de la page.
    """
    if os.environ.get(_ENV_DISABLE) == "1":
        return
    if st.session_state.get(_SESSION_KEY):
        return
    _render_login(st)
    st.stop()
