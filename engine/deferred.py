"""deferred.py — équations E4/E5/E6/E7 DIFFÉRÉES (Phase 2 : stubs None).

Numérotation CANONIQUE (alignée Phase 3) :
    E4 = couple · E5 = SME · E6 = T_real · E7 = pression.

Cette brique PRÉPARE les bases de couple (E4), SME (E5), température réelle T_real
(E6) et pression filière (E7) SANS les coder : chaque fonction est une signature
stable qui renvoie `None` et DOCUMENTE ses dépendances manquantes. Aucune valeur
nominale n'est exposée tant que les dépendances ne sont pas prêtes (décision
utilisateur Phase 2 : « stubs None documentés »).

Ces fonctions sont volontairement PURES et SANS effet : tant qu'elles renvoient
`None`, les champs `NodeState.torque_nm / sme_kwh_per_kg / t_real_c /
pressure_bar` restent `None` et aucune couche aval ne consomme de grandeur
fictive.

INTERDICTION d'import : ne JAMAIS importer `AgentIndustrial_v1/core/cooling.py`
ni quoi que ce soit de `app/` ici. Les constantes manager (K_TAU,
HEAT_RETENTION_FRACTION, CP_MELT) seront ré-exposées côté `physics`/`materials`
en phase ultérieure, pas pontées depuis le runtime.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from engine.node_state import NodeState  # noqa: E402

# Identifiants des équations différées (pour manifestes/tests).
# Ordre canonique E4 → E5 → E6 → E7 (couple, SME, T_real, pression).
E4_TORQUE: str = "E4_torque"
E5_SME: str = "E5_sme"
E6_T_REAL: str = "E6_t_real"
E7_PRESSURE: str = "E7_pressure"

DEFERRED_EQUATIONS: tuple[str, ...] = (E4_TORQUE, E5_SME, E6_T_REAL, E7_PRESSURE)


def compute_local_torque(node: NodeState) -> None:
    """E4 — couple local (N·m). DIFFÉRÉ → None.

    Dépendances manquantes avant de pouvoir coder :
      - viscosité locale η(γ̇, T) du fondu : nécessite des paramètres rhéologiques
        CALIBRÉS par matière (materials.rheology est prêt, mais les coefficients
        k/n/λ/Ea des recettes LFP/LATP sont nominaux, à recaler sur essais réels).
      - géométrie de chenal PAR ÉLÉMENT (profondeur h, largeur) extraite des plans
        references/captures_process/*.SLDDRW (aujourd'hui : nominal global seul).
      - modèle drag/pressure-flow par type d'élément (convoyage vs malaxage).
    Forme cible : M_local ∝ η(γ̇,T) · γ̇ · V_chenal / h. `node.shear_rate_s` (E1)
    est déjà disponible comme entrée.
    """
    return None


def compute_local_sme(node: NodeState, throughput_kg_per_h: float | None = None) -> None:
    """E5 — énergie mécanique spécifique locale (kWh/kg). DIFFÉRÉ → None.

    Dépendances manquantes :
      - couple/puissance locale (E4, lui-même différé).
      - débit massique ṁ effectif (kg/h) : convertible depuis ProcessState +
        densité matière, mais la répartition locale de la puissance n'est pas
        définie tant que E4 n'existe pas.
    Forme cible (manager) : SME = P / ṁ, agrégée le long de la vis ; unités kWh/kg
    (cf. poster 15 mai — pilier ML RF). `throughput_kg_per_h` réservé pour la
    future signature, ignoré tant que E4 est différé.
    """
    return None


def compute_t_real(
    node: NodeState,
    screw_rpm: float | None = None,
    torque_nm: float | None = None,
    mass_flow_kg_per_h: float | None = None,
) -> None:
    """E6 — température réelle du fondu T_real (°C). DIFFÉRÉ → None.

    Équation IMPOSÉE par le manager (Maël) :
        T_real = T_set + (2π·N·M)/(ṁ·Cp) + k·τ
    (élévation adiabatique SME/Cp + terme couple k·τ + friction).

    Dépendances manquantes avant codage :
      - vitesse vis N (`screw_rpm`) → terme (2π·N·M). N N'EST PAS porté par le
        NodeState (décision D4 : pas de nouveau champ) ; il sera THREADÉ depuis
        `graph.params.screw_rpm` par la future couche d'enrichissement Phase 3 et
        passé en argument ici. Paramètre présent dès maintenant pour figer la
        signature, ignoré tant que la fonction est un stub.
      - couple M (E4, différé) → terme (2π·N·M)/(ṁ·Cp).
      - débit massique ṁ (kg/h) effectif local.
      - Cp matière : `node.material.cp_j_per_g_k` est DÉJÀ disponible
        (material_context délègue à mixing_rules) — seule entrée prête.
      - constantes manager K_TAU / HEAT_RETENTION_FRACTION à ré-exposer côté
        physics/materials (NE PAS importer depuis AgentIndustrial_v1/cooling.py).
    `node.temperature_c` fournit T_set ; `screw_rpm`/`torque_nm`/
    `mass_flow_kg_per_h` sont les futures entrées (ignorées tant que None).
    """
    return None


def compute_die_pressure(node: NodeState, die=None) -> None:
    """E7 — pression / contre-pression filière (bar). DIFFÉRÉ → None.

    Dépendances manquantes :
      - viscosité du fondu en sortie (matière calibrée, cf. E4).
      - loi ΔP filière (Hagen-Poiseuille + correction Rabinowitsch non
        newtonienne) au-dessus de machine.die_library (géométrie prête :
        total_open_area, aspect_ratio_l_d, apparent_wall_shear_rate).
      - couplage débit↔pression le long de la vis (pression de tête).
    Forme cible : ΔP = f(Q_filière, η, géométrie trous). `die` (machine.die_library
    .Die) réservé pour la future signature.
    """
    return None
