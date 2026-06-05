"""viscosity.py — viscosité locale du fondu η(γ̇, T) par nœud (bloc 3.3).

Premier CALCUL CONSTITUTIF de la couche engine. Il n'invente AUCUNE formule :
il orchestre des briques déjà écrites et testées :
  - `materials.rheology.carreau_yasuda_viscosity`   (forme manager E3)
  - `materials.rheology.arrhenius_temperature_factor` + `apply_temperature_shift`
  - `materials.mixing_rules.log_additive_viscosity`   (combinaison de mélange)
  - `materials.limits.clamp_viscosity`                (anti inf/nan à la frontière)

PÉRIMÈTRE STRICT (bloc 3.3) :
  - ENTRÉES lues sur le nœud uniquement : shear_rate_s, temperature_c,
    material.rheologies, material.volume_fractions.
  - SORTIE : une viscosité (Pa·s) FINIE. Fonction PURE — ne mute rien, ne stocke
    rien sur le nœud (pas de champ NodeState : décision validée).
  - NE calcule NI couple (E4), NI SME (E5), NI T_real (E6), NI pression (E7).
    Ces champs restent `None` : ce module ne les touche pas.

⚠️ NOMINAL : la viscosité hérite du caractère nominal des presets rhéo (3.2) et
des bornes de `limits`. Aucune calibration essais réels ici. Rien dans l'app ne
consomme cette fonction aujourd'hui (réservée aux tests et au futur bloc E4).

Note température : `temperature_c` est la CONSIGNE de zone (pas T_real, E6 non
codé). Le couplage viscosité↔T_real est une décision FUTURE (bloc E6), hors 3.3.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from materials.rheology import (  # noqa: E402
    apply_temperature_shift,
    arrhenius_temperature_factor,
    carreau_yasuda_viscosity,
)
from materials.mixing_rules import log_additive_viscosity  # noqa: E402
from materials.limits import clamp_viscosity, VISCOSITY_FLOOR_PA_S  # noqa: E402


def constituent_viscosity(
    rheology, shear_rate_s: float, temperature_c: float
) -> float:
    """η d'UN constituant : Carreau-Yasuda × Arrhenius, puis clamp (Pa·s).

    `rheology` : un `materials.rheology_presets.MaterialRheology`.
    PUR. Sortie FINIE garantie (clamp_viscosity neutralise +inf/nan).
    """
    eta_iso = carreau_yasuda_viscosity(
        shear_rate_s,
        rheology.eta_zero_pa_s,
        rheology.eta_inf_pa_s,
        rheology.relax_time_s,
        rheology.flow_index_n,
        rheology.yasuda_a,
    )
    a_t = arrhenius_temperature_factor(
        temperature_c,
        rheology.activation_energy_j_mol,
        rheology.tref_c,
    )
    eta = apply_temperature_shift(eta_iso, a_t)
    return clamp_viscosity(eta)


def viscosity_at(
    shear_rate_s: float,
    temperature_c: float,
    rheologies,
    volume_fractions,
) -> float:
    """Viscosité locale (Pa·s) — primitif découplé de NodeState.

    - mono-constituant (1 rhéo)  : `constituent_viscosity` directe.
    - mélange (≥2 rhéos)         : η de CHAQUE constituant au MÊME γ̇/T, puis
      combinaison `log_additive_viscosity` sur les VISCOSITÉS (jamais sur les
      paramètres), pondérée par `volume_fractions` (alignées sur `rheologies`,
      invariant 3.2). Résultat re-clampé.

    Défensif : `rheologies` vide → plancher documenté (ne devrait jamais arriver,
    ≥1 garanti par material_context). Sortie FINIE garantie.
    """
    n = len(rheologies)
    if n == 0:
        return VISCOSITY_FLOOR_PA_S

    if n == 1:
        return constituent_viscosity(rheologies[0], shear_rate_s, temperature_c)

    viscosities = [
        constituent_viscosity(r, shear_rate_s, temperature_c) for r in rheologies
    ]
    blended = log_additive_viscosity(viscosities, list(volume_fractions))
    return clamp_viscosity(blended)


def compute_local_viscosity(node) -> float:
    """Viscosité locale (Pa·s) du fondu au nœud — adaptateur lecture seule.

    Lit UNIQUEMENT : node.shear_rate_s, node.temperature_c,
    node.material.rheologies, node.material.volume_fractions.
    Ne mute pas le nœud, ne stocke rien (pas de champ NodeState). Ne calcule ni
    couple, ni SME, ni T_real, ni pression — ces champs restent `None`.
    """
    return viscosity_at(
        node.shear_rate_s,
        node.temperature_c,
        node.material.rheologies,
        node.material.volume_fractions,
    )
