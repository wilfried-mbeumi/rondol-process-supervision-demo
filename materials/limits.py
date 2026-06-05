"""limits.py — helpers de borne/assainissement PURS (Phase 1.5).

Primitives finies pour empêcher la propagation de `inf`/`nan` lors de
l'agrégation à venir (NodeState additionne viscosités/résidences le long de la
vis ; un seul `inf` issu de power_law(0, n<1) ou krieger_dougherty(φ≥φmax)
empoisonnerait les cumuls).

PÉRIMÈTRE Phase 1.5 : UNIQUEMENT les primitives pures + des défauts défendables.
La POLITIQUE (quels seuils exacts, à quel point de l'agrégation appliquer) est
une décision Phase 2 (NodeState) — ces fonctions sont les briques, pas la
politique. Les lois constitutives de rheology/mixing restent volontairement
non bornées (mathématiquement honnêtes) ; le clamp s'applique À LA FRONTIÈRE.
"""

from __future__ import annotations

import math

# Bornes NOMINALES par défaut (Pa·s). Ordres de grandeur d'un fondu polymère.
# Surclassables par l'appelant ; la valeur définitive est un choix Phase 2.
VISCOSITY_FLOOR_PA_S: float = 1.0e-3
VISCOSITY_CEILING_PA_S: float = 1.0e9


def clamp(value: float, lo: float, hi: float) -> float:
    """Borne générique sur [lo, hi]. `nan` → lo (choix sûr/déterministe)."""
    if math.isnan(value):
        return lo
    return max(lo, min(hi, value))


def clamp_viscosity(
    viscosity: float,
    lo: float = VISCOSITY_FLOOR_PA_S,
    hi: float = VISCOSITY_CEILING_PA_S,
) -> float:
    """Borne une viscosité sur [lo, hi], en neutralisant les non-finis.

    +inf → hi (ex. power_law(γ̇=0, n<1), krieger_dougherty(φ≥φmax)) ;
    -inf → lo ; nan → lo. Garantit une sortie FINIE dans [lo, hi].
    """
    if math.isnan(viscosity):
        return lo
    if math.isinf(viscosity):
        return hi if viscosity > 0 else lo
    return max(lo, min(hi, viscosity))


def clamp_volume_fraction(phi: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Borne une fraction volumique sur [lo, hi] (défaut [0, 1]). nan → lo."""
    if math.isnan(phi):
        return lo
    return max(lo, min(hi, phi))
