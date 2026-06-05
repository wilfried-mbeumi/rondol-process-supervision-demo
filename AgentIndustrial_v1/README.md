# AgentIndustrial V1 — Pilote IA extrusion bivis SSB

Application Streamlit d'assistance procédé pour extrusion bivis Rondol
(compounding SSB dry / semi-dry). Pas un SaaS marketing — un outil
d'ingénierie industrielle crédible, rule-based, explicable.

## Lancement

Depuis la racine du projet `rondol-ia-project/` :

```bash
streamlit run AgentIndustrial_v1/app_industrial.py
```

## Architecture

```
AgentIndustrial_v1/
├── app_industrial.py        # entry point Streamlit
├── core/
│   ├── feeders.py           # FeederSpec, 6 phases matière, 9 positions
│   ├── process.py           # ProcessState (zones T°, rpm, KPIs, V2)
│   ├── screw_adapter.py     # pont vers app/screw_logic.py (Kévin) inchangé
│   ├── rules.py             # moteur de règles explicable
│   └── recommendations.py   # actions chiffrées par alerte
└── ui/
    ├── styles.py            # palette + CSS (cohérence existant)
    ├── feeders_panel.py     # banc 5 feeders
    ├── process_panel.py     # zones T° + vitesse vis + KPIs + V2
    └── ai_panel.py          # bandeau agent + alertes + recos
```

## Ce qui est conservé de l'existant Kévin

L'agent V1 **ré-utilise sans modification** :

- `app/screw_logic.py` — volume, fill factor, résidence, contraintes Network 7
- `app/screw_render.py` — `analyze_profile`, `recommend_element_count`,
  `build_screw_assembly_html`
- la palette HMI et les conventions DOM (st.html atomique) pour éviter
  les erreurs React `removeChild` documentées dans `app/Supervision.py`

## Ce que la V1 apporte de nouveau

### 1. Gestion avancée des feeders

- **1 à 5 feeders** simultanés, on/off par feeder
- **6 types de matière** : granulés, poudres, liquide, semi-liquide, gaz,
  supercritique (scCO₂)
- **9 positions** d'injection : Z0 → Z7 + die
- **Caractéristiques physiques par feeder** : vitesse, débit massique, densité,
  dilatation thermique (α)
- **Bornes matière** : `safe_temperature_C` + `allowed_positions` consommées
  par le moteur de règles

### 2. Couche IA explicable (rule-based)

8 règles documentées dans `core/rules.py` :

| Code | Sévérité | Vérifie |
|---|---|---|
| `FEEDER_LOCATION_BAD` | critique | matière injectée à une position physiquement invalide |
| `THERMAL_INCOMPAT_HIGH` | critique | T° zone > borne haute matière (dégradation) |
| `THERMAL_INCOMPAT_LOW` | warning | T° zone < borne basse (condensation, matière inerte) |
| `POWDER_OVERLOAD` | critique | débit poudre > capacité vis estimée |
| `POWDER_HIGH_LOAD` | warning | charge poudre > 80 % capacité |
| `FF_SATURATION` / `FF_HIGH` / `FF_LOW` / `FF_STARVATION` | warn/crit | Fill Factor hors cibles compounding |
| `SME_WARNING` / `SME_CRITICAL` | warn/crit | énergie spécifique > seuils dégradation |
| `RT_TOO_SHORT` / `RT_TOO_LONG` | warning | résidence hors plage 5-120 s |
| `THERMAL_PROFILE_INVERTED` | warning | T_die >> T_Z5 (inhabituel compounding) |
| `DUPLICATE_SOLID_POSITION` | warning | 2+ solides à la même position |

Chaque alerte produit :
- un **code** traçable à la règle
- une **description** lisible
- un **evidence** chiffré (les nombres mesurés)
- une **target** (zone / feeder / global)

### 3. Recommandations actionnables

5 catégories d'actions dans `core/recommendations.py` :

- `feeder_move` — déplacement feeder
- `flow_reduce` — réduction (ou augmentation) débit
- `temperature` — ajustement consigne T°
- `screw_profile` — modification profil vis (substitution kneading, etc.)
- `screw_speed` — changement vitesse vis

Chaque recommandation porte un **delta chiffré** (avant → après) :
> `Réduire T_Z3` :: `95 °C → 70 °C`

### 4. Préparation V2 (feedback réel)

- Champs **torque (%)** et **pressure (bar)** dans `ProcessState.v2`
- Toggle « Activer feedback V2 » dans l'UI
- Si torque renseigné, le SME est recalculé avec la formule directe
  `P_eff / ṁ` au lieu de l'estimation heuristique V1
- Hooks `feedback_enabled` et `last_update_iso` réservés pour la future
  boucle OPC-UA / API streaming

## Scénario de démonstration

Bouton sidebar **« Cas LFP + LATP + Li (poster 15 mai) »** :
- 2 poudres actives (cathode + électrolyte solide) au Z0/Z2
- 1 précurseur Li semi-liquide au Z3
- profil vis standard (convoyage + 4 kneading + convoyage)
- 150 rpm

L'agent doit produire un état **STABLE** ou **SURVEILLER** avec recommandations
pédagogiques. En modifiant manuellement les paramètres (T°, débits, positions),
l'opérateur déclenche les règles et observe les recommandations correspondantes
— démo crédible devant manager.

## SME estimé V1 vs V2

V1 (pas de torque mesuré) :
```
torque_load_proxy = clip(0.20 + 0.55·FF + 0.20·(rpm/rpm_max), 0..1)
SME_est = P_nominal · η · torque_load_proxy / ṁ
```

V2 (avec lecture torque réelle) :
```
SME_real = P_nominal · η · (torque_pct/100) / ṁ
```

La formule est identique — seul change la source du `torque_load`.
La transition V1 → V2 est donc directe : brancher la lecture streaming et
basculer `state.v2.feedback_enabled = True`.

## Tests rapides

```bash
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path += ['.', './app']
from AgentIndustrial_v1.core.feeders import new_feeder_bank
from AgentIndustrial_v1.core.process import ProcessState
from AgentIndustrial_v1.core.screw_adapter import refresh_kpis, default_screw_config
from AgentIndustrial_v1.core.rules import evaluate
from AgentIndustrial_v1.core.recommendations import build_recommendations

s = ProcessState(screw_config=default_screw_config(), feeders=new_feeder_bank())
refresh_kpis(s)
r = evaluate(s); recs = build_recommendations(s, r.alerts)
print(f'{r.state} score={r.risk_score} alerts={len(r.alerts)} recos={len(recs)}')
"
```
