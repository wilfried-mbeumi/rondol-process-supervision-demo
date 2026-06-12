"""report_params.py — construction PARTAGÉE du rapport moteur (helper pur).

Source UNIQUE de la construction `ProcessParams` + powders nominales utilisée
pour produire un `EngineReport`. Avant ce module, cette logique vivait dans
`app/pages/5_Process_Engine.py::_build_report`. Elle est factorisée ici pour que
DEUX consommateurs produisent STRICTEMENT les mêmes KPIs :

  1. la page « Moteur Procédé » (rendu temps réel) ;
  2. le figement de l'historique procédé au moment du clic « Enregistrer »
     (`app/history_store.py`).

⚠️ AUCUN changement de comportement vs l'ancien `_build_report` : mêmes
    hypothèses nominales (profil thermique, side feeder), mêmes powders
    (LFP / LATP), même mapping débit/densité. Ce module est PUR : aucune
    dépendance Streamlit, aucune lecture session/disque.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from screw_logic import (  # noqa: E402  (module nu — convention canonique)
    SIDE_FEEDER_DISABLED_ZONE,
    ProcessParams,
)
from physics.conversions import g_per_min_to_g_per_s  # noqa: E402
from materials.powder import POWDERS  # noqa: E402
from engine.app_report import EngineReport, build_engine_report  # noqa: E402


# ---------------------------------------------------------------------------
# Hypothèses NOMINALES (documentées, non calibrées) — IDENTIQUES à l'ancien
# _build_report de la page Moteur Procédé. Utilisées seulement quand
# l'information n'est pas portée par les clés partagées (profil thermique,
# débit side feeder).
# ---------------------------------------------------------------------------
# temp_z (Feed + Z1..Z8) : profil de consigne nominal de démonstration.
NOMINAL_TEMP_PROFILE_C: tuple[float, ...] = (
    40.0, 60.0, 90.0, 120.0, 150.0, 170.0, 180.0, 175.0, 165.0,
)
# Débit nominal du side feeder (g/min) quand il est activé (feeder2 = LATP).
NOMINAL_SIDE_FEEDER_G_PER_MIN: float = 10.0


def build_report_from_flat_params(
    config: list[int],
    screw_rpm: float,
    feed_g_per_min: float,
    bulk_density: float,
    side_feeder_zone: int,
) -> EngineReport:
    """Construit le `EngineReport` PUR depuis les paramètres « plats » partagés.

    Réutilise toute la pile existante : build_engine_report → build_graph
    (NodeState/ExtrusionGraph) → enrich_graph (viscosité + couple + torque_nm)
    → aggregate_machine (KPIs). Aucune nouvelle équation.

    Reproduit À L'IDENTIQUE l'ancien `_build_report` :
      - feeder1 = main (débit converti g/min→g/s, densité bulk partagée) ;
      - feeder2 = side LATP au débit nominal si `side_feeder_zone` actif ;
      - profil thermique nominal ; powders LFP / LATP.
    """
    side_active = side_feeder_zone > SIDE_FEEDER_DISABLED_ZONE
    params = ProcessParams(
        screw_rpm=screw_rpm,
        feeder1_flow_rate_g_per_s=g_per_min_to_g_per_s(feed_g_per_min),
        feeder1_bulk_density=bulk_density,
        feeder2_flow_rate_g_per_s=(
            g_per_min_to_g_per_s(NOMINAL_SIDE_FEEDER_G_PER_MIN) if side_active else 0.0
        ),
        feeder2_bulk_density=bulk_density if side_active else 0.0,
        side_feeder_zone=side_feeder_zone,
        temp_z=NOMINAL_TEMP_PROFILE_C,
    )
    feeder1_powder = POWDERS["LFP"]
    feeder2_powder = POWDERS["LATP"] if side_active else None
    return build_engine_report(config, params, feeder1_powder, feeder2_powder)
