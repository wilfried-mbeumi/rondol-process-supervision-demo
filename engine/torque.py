"""torque.py — couple mécanique local par nœud M_node (bloc E4a).

DEUXIÈME calcul constitutif de la couche engine, au-dessus de `engine/viscosity`.
Il n'introduit AUCUN nouveau moteur procédé : il combine des grandeurs déjà
produites (η, γ̇, V_libre, fill) selon un modèle uniforme TRANSPARENT, validé en
v1 par le cadrage E4a.

MODÈLE UNIFORME (v1) — dissipation visqueuse locale :
    P_node = η · γ̇² · V_filled          (puissance dissipée locale, W)
    M_node = P_node / (2π·N)             (couple local, N·m)
avec :
  - η        = `engine.viscosity.compute_local_viscosity(node)` (Pa·s, fini).
  - γ̇        = node.shear_rate_s (s⁻¹, E1, déjà calculé — jamais recalculé ici).
  - V_filled = node.local_free_volume_cm3 · node.fill_factor, converti cm³→m³.
  - N        = screw_rpm (tr/min) converti en tours/s (2π·N = ω, rad/s).

DOCUMENTATION DES CHOIX (validés E4a) :
  ⚠️ V_filled est un PROXY PROVISOIRE du volume effectivement cisaillé : on prend
     le volume libre local pondéré par le remplissage. Ce n'est pas une géométrie
     de chenal cisaillé exacte — raffinement éventuel hors E4a.
  ⚠️ La pondération par TYPE D'ÉLÉMENT (malaxage vs convoyage vs inverse) est
     VOLONTAIREMENT EXCLUE en v1 : modèle uniforme, η et fill portent seuls la
     localisation. Différenciation par type = décision future, hors E4a.
  ⚠️ Les effets PRESSURE-FLOW / FUITES (débit de pression, contre-pression,
     recirculation inter-filets) sont HORS PÉRIMÈTRE E4a (relèvent de E7).

PÉRIMÈTRE STRICT (E4a) :
  - Fonctions PURES, lecture seule. Ne mutent ni nœud, ni graph. Ne stockent rien
    sur NodeState : `torque_nm` reste `None` (matérialisation deferred, non faite).
  - NE calcule NI SME (E5), NI T_real (E6), NI pression (E7).
  - Sortie FINIE et ≥ 0 garantie (clamp anti inf/nan/négatif).
  - Garde nulle : N ≤ 0, fill ≤ 0, γ̇ ≤ 0 ou V ≤ 0 ⇒ contribution 0 proprement.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

import math  # noqa: E402

from physics.conversions import cm3_to_m3, rpm_to_rps  # noqa: E402
from materials.limits import clamp  # noqa: E402
from engine.viscosity import compute_local_viscosity  # noqa: E402


def local_power_dissipation(node) -> float:
    """Puissance visqueuse dissipée localement P = η·γ̇²·V_filled (W).

    Lit UNIQUEMENT : node.shear_rate_s, node.fill_factor,
    node.local_free_volume_cm3 (+ ce que compute_local_viscosity lit pour η).
    Ne recalcule NI fill, NI volume, NI résidence : il les réutilise verbatim.

    Garde nulle : γ̇ ≤ 0, fill ≤ 0 ou V_libre ≤ 0 ⇒ 0.0 (pas de dissipation).
    Sortie FINIE et ≥ 0 garantie.
    """
    shear = node.shear_rate_s
    fill = node.fill_factor
    free_volume_cm3 = node.local_free_volume_cm3

    if shear <= 0.0 or fill <= 0.0 or free_volume_cm3 <= 0.0:
        return 0.0

    eta = compute_local_viscosity(node)  # Pa·s, fini garanti par le clamp viscosité

    # V_filled = volume libre local pondéré par le remplissage (proxy E4a), en m³.
    v_filled_m3 = cm3_to_m3(free_volume_cm3 * fill)

    power = eta * shear * shear * v_filled_m3
    return clamp(power, 0.0, math.inf)


def local_torque_contribution(node, screw_rpm=None) -> float:
    """Couple local M = P/(2π·N) (N·m) à partir de la puissance dissipée.

    `screw_rpm` (tr/min) est passé EXPLICITEMENT : NodeState ne porte pas le régime
    vis. 2π·N = vitesse angulaire ω (rad/s) avec N en tours/s.

    Garde nulle : screw_rpm None / non fini / ≤ 0 ⇒ 0.0 (pas de rotation, couple
    indéfini → on retourne proprement 0). Puissance nulle ⇒ couple nul.
    Sortie FINIE et ≥ 0 garantie.
    """
    if screw_rpm is None or not math.isfinite(screw_rpm) or screw_rpm <= 0.0:
        return 0.0

    n_rev_s = rpm_to_rps(screw_rpm)  # tours/s
    if n_rev_s <= 0.0:
        return 0.0

    power = local_power_dissipation(node)
    if power <= 0.0:
        return 0.0

    torque = power / (2.0 * math.pi * n_rev_s)
    return clamp(torque, 0.0, math.inf)


def total_torque_from_nodes(nodes, screw_rpm) -> float:
    """Couple total = somme des contributions locales sur une séquence de nœuds.

    Additivité stricte du modèle uniforme : le total est la SOMME des M_node, sans
    pondération ni recombinaison. Sortie FINIE et ≥ 0 garantie.
    """
    total = sum(local_torque_contribution(n, screw_rpm) for n in nodes)
    return clamp(total, 0.0, math.inf)


def total_torque(graph) -> float:
    """Couple total d'un ExtrusionGraph (N·m).

    Lit le régime vis depuis graph.params.screw_rpm (UNE source, pas de recalcul)
    et délègue à `total_torque_from_nodes`. Pur, lecture seule.
    """
    return total_torque_from_nodes(graph.nodes, graph.params.screw_rpm)
