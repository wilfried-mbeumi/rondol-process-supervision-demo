"""engine — couche d'intégration état-procédé (Phase 2).

Au-dessus des modules PURS de Phase 1 (`machine`, `materials`, `physics`) et du
backbone géométrique `app/screw_logic.py`, ce package assemble l'**état local
par position de vis** (`NodeState`), le **graph d'extrusion** ordonné
(`ExtrusionGraph`) et les **agrégats** position → zone → machine (`aggregate`).

PRINCIPE FONDATEUR — ENVELOPPER, NE PAS RECALCULER :
  `screw_logic.compute_process_state()` (Network 7) reste l'UNIQUE producteur des
  profils fill_factor / vol_flow / residence_time / volumes. `NodeState`
  *enveloppe* `ProcessState[i]` ; il n'en reproduit jamais le calcul. Les
  agrégats machine RÉUTILISENT les totaux déjà fournis par `ProcessState`
  (residence_time_total / residence_time_zone) plutôt que de les re-sommer.

BOOTSTRAP sys.path — identique à `machine/__init__` : on ajoute la racine projet
(pour les packages `machine`/`materials`/`physics`/`engine`) ET `app/` (pour
résoudre `screw_logic` en MODULE NU). NE JAMAIS importer `app.screw_logic` :
cela créerait un second objet-module distinct de `screw_logic` (constantes et
dataclasses dédoublées → ruptures d'identité des types). Cf. machine/__init__.py
et tests/test_import_singleton.py.
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
