# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this project is

Rondol extrusion **predictive AI platform / digital twin** — a Streamlit app simulating an industrial HMI for a Rondol twin-screw extruder, targeted at lithium / solid-state-battery (SSB) dry/semi-dry component extrusion. It combines real screw-geometry business logic, a layered process-physics engine, and an explainable rule-based AI agent (alerts + recommendations).

It is **not** a generic data dashboard. The standing goal is a credible, demonstrable, client-ready industrial R&D tool (manager: Maël Gallas). See `README_CLAUDE_DIRECTIVE.txt` and `NOTES_HANDOFF_CLAUDE_CODE.md` for the full product/scientific brief and the academic thesis context.

## Current priority (read before coding)

The priority is **not** to add new scientific equations. It is to make the existing app coherent, professional, demonstrable, and client-ready. Quality of integration and UX over new physics.

### Protected areas — do NOT modify without explicit user approval
- `app/screw_logic.py` — the geometric/process backbone (Network 7). Single source of truth for volume/fill/residence.
- `AgentIndustrial_v1/` — the AI agent core + UI panels.
- Existing scientific calculations / equations.
- The validated **Moteur Procédé** page (`app/pages/5_Process_Engine.py`).
- Do **not** code equations E5/E6/E7 (SME-per-node, T_real, die pressure). They are intentionally deferred stubs returning `None`.
- Do **not** silently inject demo/default values; empty state must stay explicit.
- Do **not** do large redesigns without a plan.

### Working rule — propose before coding
Before writing code, always provide: (1) files touched; (2) behavior before/after; (3) risks; (4) tests planned; (5) exact acceptance criteria. Do not code until the user validates the plan. The user runs a "rival mode": challenge weak assumptions with rational counter-arguments rather than validating blindly.

## Commands

This is a Windows / PowerShell environment. Python 3.13. There is no `requirements.txt` covering the full app — `requirements.txt` only lists the ML-pipeline deps (pandas, numpy, scipy, scikit-learn, xgboost, joblib). The Streamlit app additionally needs `streamlit`, `plotly`, `altair`, `Pillow` (already installed in the user's env).

### Run the app
```powershell
# Main app — "Supervision" is the Home page; app/pages/* auto-mount as sidebar pages
streamlit run app/Supervision.py

# Separate standalone agent prototype (own entry point, reuses screw_logic unchanged)
streamlit run AgentIndustrial_v1/app_industrial.py
```
Headless run used for verification (note `PYTHONIOENCODING=utf-8` matters on Windows for the French strings):
```powershell
$env:PYTHONIOENCODING="utf-8"; python -m streamlit run app/Supervision.py --server.headless=true --server.port=8765 --browser.gatherUsageStats=false
# health check: curl http://localhost:8765/_stcore/health
```

### Tests (pytest)
```powershell
python -m pytest tests/ -q                       # full suite
python -m pytest tests/test_torque.py -q         # a single test module
python -m pytest tests/test_torque.py::test_name -q   # a single test

# The Streamlit page tests use streamlit.testing.v1.AppTest and are heavier;
# the pure-engine subset runs fast and is the usual inner loop:
python -m pytest tests/ -q --ignore=tests/test_streamlit_pages.py --ignore=tests/test_render_smoke.py --ignore=tests/test_settings_e2e.py --ignore=tests/test_save_button_bug_repro.py
```
Some `test_screw_logic_*` files are also runnable directly: `python tests/test_screw_logic_volume.py`.

### Syntax-check before claiming a fix
Streamlit scripts aren't imported by pytest, so guard them explicitly:
```powershell
python -m py_compile app/Supervision.py app/pages/2_Settings.py app/pages/5_Process_Engine.py
```

### ML pipeline (separate from the app)
The `src/` package builds a dataset from raw sensor CSVs and trains models. Run as modules from the repo root:
```powershell
python -m src.build_dataset
python -m src.train_models --window 60          # also: --window 30 / 120
python -m src.threshold_calibration --window 60
python -m src.robustness_check --window 60 --n-seeds 10
```
Paths and sensor mapping live in `src/config.py`. Raw data: `Essais_07-13_Avril_2026/`; outputs: `data/{interim,processed,features}/`, `models/*.joblib`, `reports/ml_metrics_w*.json`. The Supervision page consumes the retained model (RandomForest window 60 trained on augmented data — `models/RandomForest_w60_augmented.joblib`, threshold 80; SVM kept as documented challenger). `scripts/generate_consolidated_dataset.py` builds the simulated continuous base (`data/consolidated/`, CSV git-ignored, fixed seed) and `scripts/evaluate_on_consolidated.py` runs the external validation of the deployed model on it (`reports/eval_consolidated_w60.json`).

## Architecture

The system is layered. Lower layers are pure (no Streamlit, no session/disk); UI only renders.

### 1. Backbone — `app/screw_logic.py` (protected)
Source of truth for screw geometry and the **Network 7** process computation (`compute_process_state(config, ProcessParams) -> ProcessState`). The screw is `config[0..80]`, a list of 81 ints encoding elements/half-elements/empty positions (see the module docstring for the encoding). It is the **only** producer of fill_factor / vol_flow / residence_time / volumes. Spec: `references/logique_metier/2-CALCULS.pdf`.

### 2. Pure Phase-1 packages — `machine/`, `materials/`, `physics/`
Read-only catalogs and formulas built *on top of* `screw_logic` as the geometric source of truth (they import it, never redefine its constants):
- `machine/` — `element_library` (13 element types), `port_map` (feeders/vents/die), `die_library`.
- `materials/` — `powder`, `rheology` (Carreau-Yasuda + Arrhenius), `mixing_rules`, `rheology_presets`, `limits` (anti inf/nan clamps).
- `physics/` — `conversions` (units: rpm↔rps, g/s↔kg/h, volumetric flow).

### 3. Process engine — `engine/`
Wraps Phase-1 + the backbone into a position→zone→machine state model. **Founding principle: ENVELOP, do not recalculate.** Network 7 is called **exactly once** (`engine/extrusion_graph.build_graph`); everything downstream reuses its `ProcessState` rather than re-deriving it.
- `node_state.py` — `NodeState`: frozen per-position state wrapping `ProcessState[i]`, adding classification, material, local shear rate. E4/E5/E6/E7 fields exist but are `None`.
- `extrusion_graph.py` — `ExtrusionGraph`: ordered nodes + `FeedContext` (nominal material per position).
- `material_context.py` — nominal upstream/blend material mapping around the side feeder.
- `viscosity.py` — local melt viscosity η(γ̇, T) (block 3.3). Pure, orchestrates `materials.rheology`.
- `torque.py` — local torque M_node = η·γ̇²·V_filled / (2πN) (block E4a). Pure, read-only.
- `enrich.py` — materializes torque onto a **copy** of each node via `dataclasses.replace` (frozen, never mutated). After enrichment `torque_nm` is always a float ≥ 0.
- `aggregate.py` — folds nodes into zone/machine states; **reuses** `ProcessState` totals (residence, fill avg, overflow) instead of re-summing.
- `deferred.py` — E4/E5/E6/E7 documented stubs returning `None`. **Never import `app/` or `AgentIndustrial_v1/cooling.py` here.**
- `app_report.py` — pure view-model `EngineReport` for the page (KPIs + torque + total SME). SME total = P/ṁ is a unit identity, **not** new physics. E6/E7 stay `None`.

The **critical import invariant** (see `engine/__init__.py`, `machine/__init__.py`, `tests/test_import_singleton.py`, `tests/test_engine_singleton.py`): always `import screw_logic` as a **bare module**, never `import app.screw_logic`. The packages bootstrap `sys.path` to add both repo root and `app/`. Importing it both ways creates two distinct module objects with duplicated constants/dataclasses → type-identity breaks.

### 4. AI agent — `AgentIndustrial_v1/` (protected)
- `core/` — `process` (ProcessState for the agent), `feeders`, `screw_adapter` (bridges to `screw_logic`), `rules` + `recommendations` (explainable rule-based alerts/recos), `cooling` (manager thermal equation `T_real,i = T_set,i + (2πN·M)/(ṁ·Cp) + k·τ`).
- `ui/` — stacked panels (DOM-stable to avoid Streamlit `removeChild` issues).

### 5. Streamlit UI — `app/`
- `Supervision.py` — Home: machine status, stability score, drift probability, alerts, AI recos, KPIs (fill factor / residence / volume), screw synthesis.
- `pages/1_Profile.py` — screw configuration (zones, elements, +/- counters, KPIs).
- `pages/2_Settings.py` — AI thresholds + watched variables; imports `AgentIndustrial_v1.core`.
- `pages/3_Run_Analysis.py`, `pages/4_History.py`, `pages/5_Process_Engine.py` (engine view-model, read-only).
- `screw_render.py` — HTML/CSS screw visualization (a UX support, no longer the project's center of gravity).

### State / persistence (3 layers — manager requirement, see `AgentIndustrial_v1/core/`)
1. **editing** — live widget keys in `st.session_state` (`th_Z1`…, `fd_*`, `ni_*`); the only source of truth while the operator edits. Reconstructed by `editing_state.build_state_from_widgets` (key-only pattern, no `value=`).
2. **applied** — validated snapshot committed on "Enregistrer" (`applied_state.commit`). The **only** source consumed by Supervision and the AI agent.
3. **history** — chronological list of validated snapshots.

`state_sync.py` rebuilds a usable `ProcessState` from the applied snapshot (falling back to legacy keys). Editing widgets does **not** change Supervision until the operator saves.

## Conventions and gotchas
- Code, comments, UI strings, and docstrings are in **French** (Rondol wording). Match it.
- All nominal physics is explicitly labeled nominal / non-industrially-calibrated. Keep that framing in UI ("modèle non calibré", "À venir" for E6/E7) — don't present nominal numbers as industrial values.
- UI must be functional, not decorative: every HMI block should drive the engine (alert/score/reco). No flashy startup/Power-BI styling — dark, structured, industrial.
- Pure engine/materials modules must stay free of Streamlit and disk/session access.
- `.Codex/launch.json` defines VS Code launch configs for the Streamlit ports; `.Codex/settings.local.json` holds a large pre-approved command allowlist.
- `scripts/` builds the poster/abstract DOCX/PDF deliverables (`reports/poster_abstract/`); `notebooks/` and the many `debug_tile_*.png` / `preview_*.html` at the root are screw-render experiments — not part of the app runtime.
