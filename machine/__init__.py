"""machine — catalogue géométrique de la machine (PUR, lecture seule).

Phase 1 : `element_library` (physique des 13 éléments), `port_map` (ports
d'alimentation/dégazage/filière), `die_library` (géométrie filière).

`element_library` et `port_map` s'appuient sur `app/screw_logic.py` comme
SOURCE DE VÉRITÉ géométrique (volumes, facteurs, positions feeder/zones) :
ils l'IMPORTENT en lecture seule et ne redéfinissent jamais ses constantes.

Bootstrap sys.path centralisé ici. CONVENTION D'IMPORT CANONIQUE = idiome
runtime `import screw_logic` (module nu), identique à app/, AgentIndustrial_v1
et screw_adapter. On ajoute donc à la fois la racine projet (pour importer les
packages `machine`/`materials`/`physics`) ET `app/` (pour résoudre `screw_logic`
en module nu). Ne JAMAIS importer `app.screw_logic` : cela créerait un second
objet-module distinct de `screw_logic` (constantes/dataclasses dédoublées).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP = _ROOT / "app"
for _p in (_ROOT, _APP):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
