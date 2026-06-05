"""enrich.py — matérialisation des champs différés sur NodeState (bloc E4b).

Couche d'ENRICHISSEMENT : prend des nœuds (ou un graph) déjà construits par la
Phase 2 et produit une version ENRICHIE où le couple local E4 est MATÉRIALISÉ
dans `NodeState.torque_nm`. Le calcul lui-même vit dans `engine/torque.py` (E4a) ;
ici on ne fait que le poser sur une COPIE immuable du nœud.

PRINCIPE — `dataclasses.replace`, JAMAIS de mutation :
  NodeState est `frozen`. `replace(node, torque_nm=...)` crée une NOUVELLE
  instance ; le nœud d'origine reste intact (`torque_nm` y demeure `None`). Aucun
  champ n'est ajouté à NodeState — sa structure (21 champs) est inchangée.

SÉMANTIQUE de `torque_nm` (décision utilisateur E4b) :
  - `None`  = non matérialisé / nœud non enrichi.
  - `0.0`   = couple CALCULÉ nul (case vide, fill/γ̇/N ≤ 0).
  Après enrichissement, `torque_nm` est TOUJOURS un `float` ≥ 0 fini sur les 81
  nœuds — jamais `None`.

PÉRIMÈTRE STRICT (E4b) :
  - Matérialise UNIQUEMENT E4 (couple). E5/E6/E7 restent `None` (non touchés).
  - `enrich_graph` retourne un NOUVEL `ExtrusionGraph` via `replace(graph,
    nodes=...)`, en RÉUTILISANT `process_state`, `params` et `feed_context` PAR
    RÉFÉRENCE. AUCUN appel à `compute_process_state` (pas de 2e moteur), AUCUN
    recalcul de fill/volume/résidence ni d'agrégat.
  - `graph.params.screw_rpm` est la SOURCE UNIQUE de N (cohérent avec le γ̇ figé à
    la construction du nœud). Fonctions PURES, lecture seule.
  - N'ajoute NI `torque_total` NI `torque_max` aux agrégats (hors périmètre).
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

import dataclasses  # noqa: E402

from engine.node_state import NodeState  # noqa: E402
from engine.extrusion_graph import ExtrusionGraph  # noqa: E402
from engine.torque import local_torque_contribution  # noqa: E402


def enrich_node(node: NodeState, screw_rpm: float) -> NodeState:
    """Nœud enrichi avec `torque_nm` matérialisé (E4). Brique unitaire pure.

    Retourne une NOUVELLE instance (`replace`) ; le nœud d'origine est inchangé.
    `torque_nm` devient un `float` ≥ 0 fini (0.0 si couple nul). E5/E6/E7 restent
    `None` (non touchés). `screw_rpm` DOIT être le régime ayant servi à figer
    `node.shear_rate_s` (sinon couple incohérent avec γ̇) — `enrich_graph`
    l'impose depuis `graph.params.screw_rpm`.
    """
    torque = local_torque_contribution(node, screw_rpm)
    return dataclasses.replace(node, torque_nm=torque)


def enrich_nodes(nodes, screw_rpm: float) -> tuple[NodeState, ...]:
    """Enrichit une séquence de nœuds (cas « liste »), même N pour tous.

    Pur : ne mute pas la séquence d'entrée ni ses éléments. Retourne un tuple de
    nouvelles instances, dans l'ordre.
    """
    return tuple(enrich_node(n, screw_rpm) for n in nodes)


def enrich_graph(graph: ExtrusionGraph) -> ExtrusionGraph:
    """Graph enrichi : couple matérialisé sur les 81 nœuds. Source unique de N.

    Thread `graph.params.screw_rpm` (source UNIQUE) vers chaque nœud, puis retourne
    un NOUVEL `ExtrusionGraph` via `replace(graph, nodes=...)`. `process_state`,
    `params` et `feed_context` sont RÉUTILISÉS PAR RÉFÉRENCE — aucun recalcul de
    procédé (pas de 2e appel Network 7), aucun recalcul d'agrégat.
    """
    enriched_nodes = enrich_nodes(graph.nodes, graph.params.screw_rpm)
    return dataclasses.replace(graph, nodes=enriched_nodes)
