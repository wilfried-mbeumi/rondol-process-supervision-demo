"""calc_audit.py — statut de validation des calculs + taxonomie des débits (PUR).

Exigence manager (mode rival) : ne JAMAIS présenter un résultat comme « validé »
si une partie de la chaîne dépend d'une constante DB automate non confirmée ou
d'une correction manager hors PLC. Et distinguer explicitement les différents
débits (feeder entrant ≠ capacité machine ≠ sortie filière ≠ polymère sec).

Ce module ne calcule PAS la physique : il qualifie la confiance et organise la
provenance. Pur, testable sur des littéraux.
"""

from __future__ import annotations

from typing import Any

# --- Statuts de validation d'un RÉSULTAT calculé ---------------------------
CALCULATED_CONFIRMED = "CALCULATED_CONFIRMED"            # toutes constantes validées
CALCULATED_WITH_ASSUMPTIONS = "CALCULATED_WITH_ASSUMPTIONS"  # DB/PLC à confirmer ou correction manager
NOT_VALIDATED = "NOT_VALIDATED"                          # une donnée clé manque

# --- Provenance d'une VARIABLE d'entrée ------------------------------------
USER_INPUT = "USER_INPUT"
DEFAULT_CONFIG = "DEFAULT_CONFIG"
CALCULATED = "CALCULATED"
NOT_AVAILABLE = "NOT_AVAILABLE"

# --- État de confiance des constantes géométriques de la chaîne FF ----------
# Les valeurs par élément (VOLUME_CM3, FACTOR_FREE_BY_REV) proviennent d'un bloc
# de données automate (DataScrewElmt) NON re-vérifié ici → non confirmées.
DB_CONSTANTS_CONFIRMED: bool = False
# Le facteur bivis ×2 (N_SCREWS) est une correction manager absente du PLC.
BIVIS_CORRECTION_IS_MANAGER: bool = True

# Clé session : capacité machine déclarée (g/h) — RÉFÉRENCE, n'écrase jamais le
# débit feeder. 0 = non renseignée (le manager évoque ~1 kg/h = 1000 g/h).
MACHINE_MAX_CAPACITY_KEY = "machine_max_capacity_g_h"


def fill_factor_validation_status(
    feed_known: bool,
    db_constants_confirmed: bool = DB_CONSTANTS_CONFIRMED,
    manager_correction_active: bool = BIVIS_CORRECTION_IS_MANAGER,
) -> str:
    """Statut du fill factor selon l'état des entrées et constantes.

    - donnée clé (débit) manquante → NOT_VALIDATED ;
    - sinon, si une constante DB est à confirmer OU si une correction manager
      hors PLC est active → CALCULATED_WITH_ASSUMPTIONS ;
    - sinon → CALCULATED_CONFIRMED.
    """
    if not feed_known:
        return NOT_VALIDATED
    if (not db_constants_confirmed) or manager_correction_active:
        return CALCULATED_WITH_ASSUMPTIONS
    return CALCULATED_CONFIRMED


def formula_status_label() -> str:
    """Libellé honnête pour les lignes dont la formule est PLC mais les
    constantes partiellement à confirmer."""
    if DB_CONSTANTS_CONFIRMED and not BIVIS_CORRECTION_IS_MANAGER:
        return "Formule PLC validée (Network 7)"
    return "Formule PLC utilisée — constantes partiellement à confirmer"


def _fmt(value: float | None, unit: str) -> str:
    return f"{value:.1f} {unit}" if value is not None else "Non disponible"


def flow_taxonomy_rows(
    feed_effective_g_h: float | None,
    machine_max_capacity_g_h: float | None,
    output_flow_g_h: float | None,
) -> list[dict[str, Any]]:
    """Lignes distinguant les débits (jamais confondus). PUR.

    Chaque ligne : variable, valeur, unité, source, statut, used_in_ff, commentaire.
    """
    feed_src = CALCULATED if feed_effective_g_h is not None else NOT_AVAILABLE
    feed_stat = CALCULATED_WITH_ASSUMPTIONS if feed_effective_g_h is not None else NOT_VALIDATED
    mach_src = USER_INPUT if machine_max_capacity_g_h else NOT_AVAILABLE
    out_src = CALCULATED if output_flow_g_h is not None else NOT_AVAILABLE

    return [
        {
            "variable": "Débit feeder utilisé (calcul FF)",
            "valeur": _fmt(feed_effective_g_h, "g/h"), "unite": "g/h",
            "source": feed_src, "statut": feed_stat, "used_in_ff": "Oui",
            "commentaire": "Débit effectif étalonné, plafonné max machine — SEUL débit entrant dans le fill factor.",
        },
        {
            "variable": "Débit machine maximal déclaré",
            "valeur": _fmt(machine_max_capacity_g_h, "g/h"), "unite": "g/h",
            "source": mach_src, "statut": NOT_VALIDATED, "used_in_ff": "Non",
            "commentaire": "Contrainte/référence machine (≈ 1 kg/h évoqué) — N'ÉCRASE PAS le débit feeder.",
        },
        {
            "variable": "Débit sortie filière estimé",
            "valeur": _fmt(output_flow_g_h, "g/h"), "unite": "g/h",
            "source": out_src, "statut": CALCULATED_WITH_ASSUMPTIONS, "used_in_ff": "Non",
            "commentaire": "Hypothèse régime permanent (sortie ≈ entrée) — pas une mesure.",
        },
        {
            "variable": "Débit polymère sec estimé",
            "valeur": "Non disponible", "unite": "g/h",
            "source": NOT_AVAILABLE, "statut": NOT_VALIDATED, "used_in_ff": "Non",
            "commentaire": "Nécessite taux solide / humidité — non renseigné.",
        },
        {
            "variable": "Pertes / humidité",
            "valeur": "Non disponible", "unite": "%",
            "source": NOT_AVAILABLE, "statut": NOT_VALIDATED, "used_in_ff": "Non",
            "commentaire": "À renseigner (séchage, pertes procédé).",
        },
    ]
