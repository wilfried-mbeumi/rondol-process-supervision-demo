"""
6_Account.py — Compte & historique de connexion.

Page protégée (comme les autres) : elle exige une session authentifiée, affiche
l'utilisateur connecté, un bouton de déconnexion, et le journal des connexions
lu depuis la base durable (Supabase en production, repli fichier en local).

Elle démontre l'interaction réelle de l'application avec sa base de données :
la table `login_history` est alimentée à chaque tentative (cf. app/auth.py) et
relue ici.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP = Path(__file__).resolve().parent.parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import auth  # noqa: E402
from rondol_i18n import current_lang, language_selector  # noqa: E402

# Libellés bilingues locaux (respecte ui_lang — pas de français en mode EN).
# Repli délégué à rondol_i18n.current_lang() : une seule source de vérité pour
# la langue par défaut (DEFAULT_LANG), sinon cette page divergeait des six
# autres tant que le sélecteur n'avait pas encore été rendu.
_LANG = current_lang()
_TX = {
    "fr": {
        "title": "Compte & accès",
        "page_title": "Compte — Rondol",
        "connected": "Connecté en tant que",
        "logout": "Se déconnecter",
        "backend": "Base de persistance",
        "history_h": "Historique des connexions",
        "history_help": "Journal des tentatives (succès et échecs), lu depuis la base durable.",
        "empty": "Aucune connexion enregistrée pour l'instant.",
        "col_email": "Email",
        "col_status": "Statut",
        "col_source": "Source",
        "col_ts": "Horodatage",
        "ok": "Succès",
        "ko": "Échec",
    },
    "en": {
        "title": "Account & access",
        "page_title": "Account — Rondol",
        "connected": "Signed in as",
        "logout": "Sign out",
        "backend": "Persistence backend",
        "history_h": "Login history",
        "history_help": "Log of attempts (success and failure), read from the durable store.",
        "empty": "No login recorded yet.",
        "col_email": "Email",
        "col_status": "Status",
        "col_source": "Source",
        "col_ts": "Timestamp",
        "ok": "Success",
        "ko": "Failed",
    },
}
_T = _TX.get(_LANG, _TX["en"])

st.set_page_config(page_title=_T["page_title"], layout="wide")
from auth import require_login  # noqa: E402
require_login(st)

# Sélecteur FR/EN — appelé comme sur les six autres pages (cf. docstring de
# rondol_i18n.language_selector : chaque page rend le widget, toutes lisent la
# même clé de session). Placé après set_page_config, qui doit rester le premier
# appel Streamlit de la page.
language_selector()

st.markdown(f"## 👤 {_T['title']}")

user = auth.current_user(st) or "—"
col_a, col_b = st.columns([3, 1])
with col_a:
    # Espace insécable avant « : » en français uniquement ; l'anglais colle le
    # deux-points au mot (sinon fuite typographique FR en mode EN).
    _sep = " :" if _LANG == "fr" else ":"
    st.markdown(f"**{_T['connected']}{_sep}** `{user}`")
    st.caption(f"{_T['backend']}{_sep} `{auth.backend_name()}`")
with col_b:
    if st.button(_T["logout"], key="btn_logout", use_container_width=True):
        auth.logout(st)
        st.rerun()

st.divider()
st.markdown(f"### {_T['history_h']}")
st.caption(_T["history_help"])

rows = []
try:
    rows = auth.get_login_history(limit=50)
except Exception:
    rows = []

if not rows:
    st.info(_T["empty"])
else:
    table = []
    for r in rows:
        table.append({
            _T["col_email"]: r.get("email", "—"),
            _T["col_status"]: _T["ok"] if r.get("success") else _T["ko"],
            _T["col_source"]: r.get("source", "app"),
            _T["col_ts"]: r.get("ts", r.get("seq", "")),
        })
    st.dataframe(table, use_container_width=True, hide_index=True)

st.caption("Rondol Industrie · access log")
