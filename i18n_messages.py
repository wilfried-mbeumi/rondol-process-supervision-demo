"""i18n_messages.py — Catalogue PUR des messages agent (FR/EN).

Module volontairement SANS Streamlit, sans disque, sans session : il est
importable en *bare module* (comme ``screw_logic``) aussi bien par les pages
``app/`` que, plus tard (phase B2), par ``AgentIndustrial_v1/core``. Il porte
uniquement les gabarits de texte des messages générés par l'agent
(alertes, recommandations, diagnostics) — jamais de logique de calcul.

Contrat (B0 — squelette) :
  - ``MESSAGES[msg_id] = {"fr": "...", "en": "..."}`` ;
  - ``m(msg_id, lang, **params)`` formate le gabarit ;
  - fallback : langue inconnue/absente → FR → ``msg_id`` brut ;
  - jamais de ``KeyError`` (paramètre manquant → texte non formaté renvoyé).

Les identifiants réels (``ALERT_*`` / ``REC_*`` / ``DIAG_*``) seront ajoutés
en phase B2, en déplaçant les littéraux de ``core/rules.py`` et
``core/recommendations.py`` SANS toucher aux nombres ni aux codes.
"""

from __future__ import annotations

DEFAULT_LANG = "fr"
SUPPORTED_LANGS: tuple[str, ...] = ("fr", "en")

# B0 : catalogue volontairement quasi vide (un seul message d'auto-test pour
# valider la mécanique de fallback/format). Rempli en B2.
MESSAGES: dict[str, dict[str, str]] = {
    "_SELFTEST": {"fr": "ok", "en": "ok"},
}


def m(msg_id: str, lang: str = DEFAULT_LANG, /, **params: object) -> str:
    """Retourne le message localisé pour ``msg_id``.

    Fallback en cascade : langue demandée → FR → identifiant brut.
    Le formatage des paramètres est protégé : un placeholder manquant ne lève
    jamais d'exception, le gabarit non formaté est renvoyé tel quel.
    """
    entry = MESSAGES.get(msg_id)
    if entry is None:
        return msg_id
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or msg_id
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text
