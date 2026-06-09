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
    is_demo_state,
)


def build(session: MutableMapping[str, Any]) -> CurrentRunState:
    """Construit le `CurrentRunState` depuis la session (délègue au core, pur)."""
    return build_current_run_state(session)


def project_to_legacy(crs: CurrentRunState, session: MutableMapping[str, Any]) -> None:
    """Initialise les clés legacy depuis l'état canonique (sens UNIQUE).

    RÈGLE INVARIANTE manager 2026-06-09 (correctif Pb #2) :
    **n'écrit JAMAIS une clé déjà présente en session**.

    Avant ce correctif, project_to_legacy écrasait `screw_config`, `screw_rpm`,
    `bulk_density` et `feeder_g_per_min` à chaque rerun. Comme Profile appelle
    `sync_legacy_projection` à la fin de chaque rerun, toute édition de la vis
    (boutons +1/+4/−1) était systématiquement annulée par le snapshot
    précédent au rerun suivant — l'utilisateur croyait ne plus pouvoir
    modifier après une sauvegarde. Repro pure-Python : snapshot=5 éléments,
    +2 par l'utilisateur → session=7 → project_to_legacy → session=5.

    Sémantique correcte : project_to_legacy initialise les clés ABSENTES
    (premier boot / refresh navigateur / session purgée par navigation
    multipage). Les pages de SAISIE (Profile, Settings) gardent l'exclusivité
    sur les écritures de leurs clés (via leurs widgets et `project_shared_keys`
    côté Settings après commit).

    Cohérent avec `restore_operator_state` (même règle d'idempotence) et avec
    `seed_editing_keys` (même règle : ne touche pas les clés présentes).
    """
    pp = crs.process_parameters

    if ("screw_rpm" not in session
            and "screw_rpm" in pp and pp["screw_rpm"].value is not None):
        session["screw_rpm"] = float(pp["screw_rpm"].value)

    if ("bulk_density" not in session
            and "bulk_density" in pp and pp["bulk_density"].value is not None):
        session["bulk_density"] = float(pp["bulk_density"].value)

    if "screw_config" not in session and crs.screw_profile.value is not None:
        session["screw_config"] = list(crs.screw_profile.value)

    # Débit legacy (g/min) UNIQUEMENT si la clé est absente ET si le débit
    # réel est calculable (étalonnage feeder présent). Sinon on ne touche pas.
    if "feeder_g_per_min" not in session:
        ff = crs.feeder_calibration.value
        if (crs.feed_rate.source == CALCULATED and ff is not None
                and getattr(ff, "effective_g_min", None) is not None):
            session["feeder_g_per_min"] = float(ff.effective_g_min)


def build_moteur_inputs_from_current_run_state(crs: CurrentRunState) -> dict[str, Any]:
    """Dérive les paramètres « plats » du Moteur Procédé depuis current_run_state.

    Le moteur (`build_report_from_flat_params`) reste un MOTEUR ENVELOPPÉ : il
    reçoit des paramètres plats, mais ceux-ci proviennent EXCLUSIVEMENT de
    current_run_state (jamais d'une lecture legacy directe côté page).

    Règle métier (manager P3.3, cas 5) : sans étalonnage feeder exploitable, le
    débit réel est NON calculable → `feed_available=False` et `feed_g_per_min=0`
    (on n'invente pas de débit ; la page affiche « coefficient à renseigner »).
    """
    pp = crs.process_parameters
    feeder_flow = crs.feeder_calibration.value  # FeederFlow (même si non étalonné)
    feed_available = crs.feed_rate.source == CALCULATED and crs.feed_rate.value is not None
    feed_g_per_min = (float(crs.feed_rate.value) / 60.0) if feed_available else 0.0

    return {
        "config": list(crs.screw_profile.value or []),
        "screw_rpm": float(pp["screw_rpm"].value),
        "bulk_density": float(pp["bulk_density"].value),
        "side_feeder_zone": int(pp["side_feeder_zone"].value),
        "feed_g_per_min": feed_g_per_min,
        "feed_available": feed_available,
        "feeder_flow": feeder_flow,
        "demo_mode": is_demo_state(crs),
        # Banc multi-feeder (débit par feeder + total) pour l'audit Moteur.
        "multi_feeder": crs.feeders,
    }


def sync_legacy_projection(session: MutableMapping[str, Any]) -> CurrentRunState:
    """Construit l'état canonique ET projette les clés legacy. Retourne l'état.

    À appeler par les pages de SAISIE (Profile, et Settings APRÈS commit) pour
    formaliser le flux à sens unique. Idempotent et sans effet visible si la
    session est déjà cohérente.
    """
    crs = build(session)
    project_to_legacy(crs, session)
    return crs
