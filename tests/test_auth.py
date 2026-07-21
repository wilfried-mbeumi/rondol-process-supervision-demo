# -*- coding: utf-8 -*-
"""Tests de l'authentification (app/auth.py) — mécanisme réel, backend fichier.

Ces tests n'utilisent PAS le bypass RONDOL_DISABLE_AUTH (ils exercent la vraie
garde). Ils forcent le backend fichier via des chemins temporaires isolés et
s'assurent qu'aucune configuration Supabase n'est active.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture()
def auth(monkeypatch, tmp_path):
    """Module auth rechargé avec un backend fichier isolé (pas de Supabase)."""
    monkeypatch.delenv("RONDOL_SUPABASE_URL", raising=False)
    monkeypatch.delenv("RONDOL_SUPABASE_KEY", raising=False)
    monkeypatch.setenv("RONDOL_AUTH_USERS_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("RONDOL_AUTH_HISTORY_PATH", str(tmp_path / "history.json"))
    import auth as _auth
    importlib.reload(_auth)
    return _auth


# --------------------------------------------------------------------------
# Hachage
# --------------------------------------------------------------------------
def test_hash_is_salted_and_verifies(auth):
    salt1, h1 = auth.hash_password("0000")
    salt2, h2 = auth.hash_password("0000")
    assert salt1 != salt2, "le sel doit être aléatoire par appel"
    assert h1 != h2, "deux hachages du même mot de passe diffèrent (sel)"
    assert auth.verify_password("0000", salt1, h1) is True
    assert auth.verify_password("mauvais", salt1, h1) is False


def test_password_never_stored_plaintext(auth):
    auth.upsert_user("demo@rondol.local", "0000")
    raw = (Path(auth._users_path())).read_text(encoding="utf-8")
    assert "0000" not in raw, "le mot de passe en clair ne doit jamais être écrit"


# --------------------------------------------------------------------------
# Identifiants
# --------------------------------------------------------------------------
def test_backend_is_file_without_supabase(auth):
    assert auth.backend_name() == "file"


def test_verify_credentials(auth):
    auth.upsert_user("demo@rondol.local", "0000")
    assert auth.verify_credentials("demo@rondol.local", "0000") is True
    assert auth.verify_credentials("DEMO@RONDOL.LOCAL", "0000") is True  # insensible à la casse
    assert auth.verify_credentials("demo@rondol.local", "bad") is False
    assert auth.verify_credentials("inconnu@x.com", "0000") is False


# --------------------------------------------------------------------------
# Historique
# --------------------------------------------------------------------------
def test_login_history_records_success_and_failure(auth):
    auth.record_login("demo@rondol.local", True)
    auth.record_login("intrus@x.com", False)
    hist = auth.get_login_history()
    assert len(hist) == 2
    # le plus récent en premier
    assert hist[0]["email"] == "intrus@x.com" and hist[0]["success"] is False
    assert hist[1]["email"] == "demo@rondol.local" and hist[1]["success"] is True


def test_record_login_never_raises(auth):
    # même avec un email vide, la journalisation ne doit pas casser la connexion
    auth.record_login("", False)
    assert isinstance(auth.get_login_history(), list)


# --------------------------------------------------------------------------
# Garde d'accès (require_login)
# --------------------------------------------------------------------------
class _FakeStop(Exception):
    pass


class _FakeSt:
    def __init__(self):
        self.session_state = {}

    def stop(self):
        raise _FakeStop()


def test_require_login_noop_when_disabled(auth, monkeypatch):
    monkeypatch.setenv("RONDOL_DISABLE_AUTH", "1")
    st = _FakeSt()
    # ne doit pas lever, ne doit pas rendre de formulaire
    auth.require_login(st)


def test_require_login_noop_when_authenticated(auth, monkeypatch):
    monkeypatch.delenv("RONDOL_DISABLE_AUTH", raising=False)
    st = _FakeSt()
    st.session_state["auth_email"] = "demo@rondol.local"
    auth.require_login(st)  # déjà connecté → pas de st.stop()


def test_require_login_blocks_when_unauthenticated(auth, monkeypatch):
    monkeypatch.delenv("RONDOL_DISABLE_AUTH", raising=False)
    # neutraliser le rendu Streamlit du formulaire
    monkeypatch.setattr(auth, "_render_login", lambda st: None)
    st = _FakeSt()
    with pytest.raises(_FakeStop):
        auth.require_login(st)


def test_local_default_user_auto_provisioned(auth):
    """Démarrage local frais (backend fichier, pas de Supabase) : le compte de
    démonstration doit être auto-créé pour que le login fonctionne sans seed."""
    assert auth.backend_name() == "file"
    assert auth._file_read(auth._users_path()) is None  # aucun utilisateur au départ
    auth._ensure_local_default_user()
    assert auth.verify_credentials("demo@rondol.local", "0000") is True
    # idempotent : un 2e appel n'écrase pas / ne duplique pas
    auth._ensure_local_default_user()
    assert auth.verify_credentials("demo@rondol.local", "0000") is True


def test_current_user_and_logout(auth):
    st = _FakeSt()
    assert auth.current_user(st) is None
    st.session_state["auth_email"] = "demo@rondol.local"
    assert auth.current_user(st) == "demo@rondol.local"
    auth.logout(st)
    assert auth.current_user(st) is None
