"""run_state_adapter.py — pont app ↔ current_run_state (P3.2).

Rôle : exposer aux pages Streamlit la source de vérité `current_run_state`
(couche pure core) et garantir que les anciennes clés « legacy » partagées
(`screw_rpm`, `feeder_g_per_min`, `bulk_density`, `screw_config`) restent une
**PROJECTION en lecture seule** dérivée de l'état canonique — jamais une source
concurrente.

Sens UNIQUE autorisé :
    current_run_state  ──►  clés legacy (projection compatibilité)
Le sens inverse (legacy → métier) reste géré, sous contrôle, par
`state_sync.state_from_session` (pont legacy historique) lu PAR le builder.

Ce module appartient à la couche app et peut importer le core (app → core OK).
Il n'introduit aucun calcul ni constante métier : il ne fait que lire/écrire.
"""

from __future__ import annotations

from typing import Any, MutableMapping

from AgentIndustrial_v1.core.current_run_state import (
    CALCULATED,
    CurrentRunState,
    build_current_run_state,
)


def build(session: MutableMapping[str, Any]) -> CurrentRunState:
    """Construit le `CurrentRunState` depuis la session (délègue au core, pur)."""
    return build_current_run_state(session)


def project_to_legacy(crs: CurrentRunState, session: MutableMapping[str, Any]) -> None:
    """Projette l'état canonique vers les clés legacy partagées (sens UNIQUE).

    Écrit uniquement des valeurs DISPONIBLES (jamais NOT_AVAILABLE → on ne
    remplace pas une valeur legacy par du None). Idempotent : si la session est
    déjà cohérente, n'introduit aucun changement de valeur.
    """
    pp = crs.process_parameters

    if "screw_rpm" in pp and pp["screw_rpm"].value is not None:
        session["screw_rpm"] = float(pp["screw_rpm"].value)

    if "bulk_density" in pp and pp["bulk_density"].value is not None:
        session["bulk_density"] = float(pp["bulk_density"].value)

    if crs.screw_profile.value is not None:
        session["screw_config"] = list(crs.screw_profile.value)

    # Débit legacy (g/min) UNIQUEMENT si le débit réel est calculable
    # (étalonnage feeder présent) ; sinon on ne touche pas la valeur existante.
    if crs.feeder_calibration.source == CALCULATED:  # défensif (jamais le cas)
        pass
    ff = crs.feeder_calibration.value
    if (crs.feed_rate.source == CALCULATED and ff is not None
            and getattr(ff, "effective_g_min", None) is not None):
        session["feeder_g_per_min"] = float(ff.effective_g_min)


def sync_legacy_projection(session: MutableMapping[str, Any]) -> CurrentRunState:
    """Construit l'état canonique ET projette les clés legacy. Retourne l'état.

    À appeler par les pages de SAISIE (Profile, et Settings APRÈS commit) pour
    formaliser le flux à sens unique. Idempotent et sans effet visible si la
    session est déjà cohérente.
    """
    crs = build(session)
    project_to_legacy(crs, session)
    return crs
