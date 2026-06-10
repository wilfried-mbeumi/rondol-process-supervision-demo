"""app_mode.py — séparation explicite « mode client » vs « mode démonstration ».

Exigence manager (2026-06-08) : aucune donnée fictive (matière chimique LFP/LATP,
run ML d'essai, score de stabilité de démonstration, temps d'essai) ne doit être
présentée comme une vérité procédé en mode client. Les données de démonstration
ne sont visibles QUE si l'opérateur a explicitement activé le mode démonstration,
et alors elles portent un marquage DEMO visible.

Contrat :
  - `is_demo_mode(session)` : True si l'opérateur a activé la démo (défaut False).
  - `set_demo_mode(session, on)` : positionne le flag.
  - `demo_mode_toggle(...)` : widget Streamlit (sidebar) pilotant le flag.
  - `NOT_PROVIDED` : libellé canonique « Non renseigné » (jamais une valeur
    inventée). `demo_badge_html()` : pastille DEMO réutilisable.

Module léger : seul `demo_mode_toggle` touche Streamlit ; les helpers purs
(`is_demo_mode`, `set_demo_mode`, `NOT_PROVIDED`) sont testables sur un dict.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

# Clé session_state du flag mode démonstration (défaut : client = False).
DEMO_MODE_KEY = "demo_mode"

# Libellé canonique d'une donnée non saisie — JAMAIS une valeur inventée.
NOT_PROVIDED = "Non renseigné"


def is_demo_mode(session: Mapping[str, Any]) -> bool:
    """True si le mode démonstration est explicitement activé (défaut False)."""
    try:
        return bool(session[DEMO_MODE_KEY]) if DEMO_MODE_KEY in session else False
    except Exception:  # pragma: no cover - proxy session hors contexte
        return False


def set_demo_mode(session: MutableMapping[str, Any], on: bool) -> None:
    """Active/désactive le mode démonstration."""
    session[DEMO_MODE_KEY] = bool(on)


def material_label(name: str | None, demo_mode: bool) -> str:
    """Libellé matière à AFFICHER selon le mode.

    Contrat anti-invention (exigence manager) :
      - mode client (`demo_mode=False`) : TOUJOURS « Non renseigné », quelle que
        soit la matière nominale calculée par le moteur. Aucun nom de chimie
        (LFP, LiFePO4, LATP, additif…) ne doit transparaître.
      - mode démonstration (`demo_mode=True`) : le nom nominal réel, ou
        « Non renseigné » s'il est vide.

    Le marquage DEMO visuel est ajouté séparément par l'appelant (HTML).
    """
    if not demo_mode:
        return NOT_PROVIDED
    return name if name else NOT_PROVIDED


def demo_badge_html() -> str:
    """Pastille DEMO inline (HTML) — à coller près de toute valeur fictive."""
    return (
        '<span style="background:#7C3AED;color:#fff;font-weight:700;'
        'font-size:0.6rem;letter-spacing:0.06em;padding:0.05rem 0.4rem;'
        'border-radius:0.25rem;vertical-align:middle;">DEMO</span>'
    )


def demo_mode_toggle(st_module, *, location=None) -> bool:
    """Affiche le sélecteur Client / Démonstration et retourne l'état démo.

    Pattern clé-only : piloté par `session_state[DEMO_MODE_KEY]`. Placé en
    sidebar par défaut. Sans dépendance d'import dur à Streamlit (passé en
    argument) pour garder le module testable.
    """
    container = location if location is not None else st_module.sidebar
    if DEMO_MODE_KEY not in st_module.session_state:
        st_module.session_state[DEMO_MODE_KEY] = False
    # i18n FR/EN (stabilisation globale 2026-06-10) — import défensif : le
    # module reste testable sur un dict sans Streamlit (repli FR).
    try:
        from rondol_i18n import t as _t
        _label, _help = _t("app_mode.toggle"), _t("app_mode.toggle_help")
    except Exception:  # pragma: no cover
        _label = "Mode démonstration"
        _help = (
            "OFF = mode client : seules les données réellement saisies sont "
            "affichées (sinon « Non renseigné »). ON = données fictives de "
            "démonstration, marquées DEMO."
        )
    container.toggle(_label, key=DEMO_MODE_KEY, help=_help)
    return is_demo_mode(st_module.session_state)
