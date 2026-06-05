"""i18n.py — Couche de traduction FR/EN de l'application (chrome).

Phase B0 (scaffolding) : infrastructure i18n + sélecteur de langue. AUCUN
contenu métier n'est traduit à cette étape — le dictionnaire ``TRANSLATIONS``
ne contient que les clés nécessaires au sélecteur lui-même. Les pages seront
traduites en B1 ; le contenu agent en B2 ; le rendu vis en B3 ; les pages
validées (Moteur Procédé, Historique) en B4.

Conception :
  - langue stockée dans ``st.session_state["ui_lang"]`` (défaut ``"fr"``) ;
  - ``t(key, **kwargs)`` : texte du *chrome* (titres, boutons, sections…) ;
  - ``m(msg_id, **params)`` : wrapper Streamlit du catalogue PUR
    ``i18n_messages`` (messages agent) avec la langue courante ;
  - fallback systématique : langue manquante → FR → clé brute. Jamais de
    ``KeyError`` (placeholder manquant → texte non formaté renvoyé).

Le module ``i18n_messages`` reste PUR (sans Streamlit) pour pouvoir être
importé par ``AgentIndustrial_v1/core`` en B2 sans casser l'invariant de
pureté des modules moteur.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Catalogue pur des messages agent — importé en *bare module* (même
# convention que ``screw_logic``). On garantit la présence de la racine repo
# sur ``sys.path`` avant l'import.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import i18n_messages  # noqa: E402

LANG_KEY = "ui_lang"
DEFAULT_LANG = "fr"
SUPPORTED_LANGS: tuple[str, ...] = ("fr", "en")
_LANG_LABELS: dict[str, str] = {"fr": "Français", "en": "English"}

# ---------------------------------------------------------------------------
# Dictionnaire de traduction du CHROME.
# B0 : strictement limité au sélecteur. Sera étendu en B1 (titres, bannières,
# boutons, sections, aides, libellés de tableaux…).
# ---------------------------------------------------------------------------
TRANSLATIONS: dict[str, dict[str, str]] = {
    "lang.selector_label": {"fr": "Langue", "en": "Language"},

    # ---- Libellés métriques partagés -----------------------------------
    "m.run": {"fr": "Run", "en": "Run"},
    "m.duration": {"fr": "Durée", "en": "Duration"},
    "m.window": {"fr": "Fenêtre", "en": "Window"},
    "m.time": {"fr": "Heure", "en": "Time"},

    # ===================================================================
    # PAGE — Supervision / Accueil
    # ===================================================================
    "page.home.title": {"fr": "Supervision procédé — Rondol",
                        "en": "Process Supervision — Rondol"},
    "home.banner.left": {"fr": "● Rondol · Supervision Procédé",
                         "en": "● Rondol · Process Supervision"},
    "home.banner.right": {"fr": "AGENT IA — Extrusion batteries tout-solide SSB",
                          "en": "AI AGENT — All-solid-state battery (SSB) extrusion"},
    "home.header.title": {"fr": "Supervision procédé", "en": "Process Supervision"},
    "home.header.caption": {
        "fr": "Agent IA SVM w60 · Extrudeuse bivis 10,5 mm · Composants SSB dry/semi-dry",
        "en": "AI agent SVM w60 · 10.5 mm twin-screw extruder · SSB dry/semi-dry components"},
    "home.sidebar.run": {"fr": "Run de production", "en": "Production run"},
    "home.sidebar.window": {"fr": "Fenêtre active", "en": "Active window"},
    "home.sidebar.window_fmt": {"fr": "Fenêtre %d", "en": "Window %d"},
    "home.sidebar.model": {"fr": "Modèle : SVM w60  ·  Seuil : {th}/100",
                           "en": "Model: SVM w60  ·  Threshold: {th}/100"},
    "home.sidebar.trials": {"fr": "Essais Avril 2026 — Rondol Industrie",
                            "en": "April 2026 trials — Rondol Industrie"},
    "home.sec.profile_reading": {"fr": "AGENT IA — LECTURE PROFIL",
                                 "en": "AI AGENT — PROFILE READING"},
    "home.sec.decision": {"fr": "AGENT IA — DÉCISION OPÉRATIONNELLE",
                          "en": "AI AGENT — OPERATIONAL DECISION"},
    "home.sec.global_reasoning": {"fr": "AGENT IA — RAISONNEMENT GLOBAL PROCÉDÉ",
                                  "en": "AI AGENT — GLOBAL PROCESS REASONING"},
    "home.sec.agent_sync": {"fr": "AGENT IA — PROCÉDÉ (SYNCHRONISÉ SETTINGS)",
                            "en": "AI AGENT — PROCESS (SYNCED WITH SETTINGS)"},
    "home.sec.top5": {"fr": "DIAGNOSTIC PROCÉDÉ — TOP 5 CAPTEURS",
                      "en": "PROCESS DIAGNOSTIC — TOP 5 SENSORS"},
    "home.sec.auto_analysis": {"fr": "Analyse automatique — fenêtre {win}/{n}",
                               "en": "Automatic analysis — window {win}/{n}"},
    "home.sec.recos": {"fr": "RECOMMANDATIONS OPÉRATEUR",
                       "en": "OPERATOR RECOMMENDATIONS"},
    "home.sec.score_evo": {"fr": "ÉVOLUTION DU SCORE — RUN COURANT",
                           "en": "SCORE TREND — CURRENT RUN"},
    "home.zones.alert": {
        "fr": "Zones en alerte : {zones} — σ ≥ 1,5 °C (seuil instabilité thermique).",
        "en": "Zones in alert: {zones} — σ ≥ 1.5 °C (thermal instability threshold)."},
    "home.zones.ok": {"fr": "Toutes les zones thermiques sont sous le seuil σ = 1,5 °C.",
                      "en": "All thermal zones are below the σ = 1.5 °C threshold."},
    "home.kpi.stability": {"fr": "Score stabilité", "en": "Stability score"},
    "home.kpi.vs_threshold": {"fr": "vs seuil", "en": "vs threshold"},
    "home.kpi.threshold": {"fr": "Seuil retenu", "en": "Selected threshold"},
    "home.kpi.threshold_delta": {"fr": "SVM w60 · Phase 4", "en": "SVM w60 · Phase 4"},
    "home.kpi.pstable": {"fr": "P(stable) SVM", "en": "P(stable) SVM"},
    "home.kpi.pstable_delta": {"fr": "seuil décision 0.70", "en": "decision threshold 0.70"},
    "home.kpi.score_mean": {"fr": "Score moyen", "en": "Mean score"},
    "home.kpi.score_min": {"fr": "Score min", "en": "Min score"},
    "home.kpi.windows_stable": {"fr": "Fenêtres stables", "en": "Stable windows"},
    "home.kpi.windows_total": {"fr": "Fenêtres totales", "en": "Total windows"},
    "home.footer": {
        "fr": "Run #{run} · {run_str} · {n} fenêtres · SVM w60 · Seuil {th}/100 · Essais Avril 2026 — Rondol Industrie",
        "en": "Run #{run} · {run_str} · {n} windows · SVM w60 · Threshold {th}/100 · April 2026 trials — Rondol Industrie"},
    # États procédé (badge) — label/sub/impact (recos opérateur différées B2)
    "home.state.STABLE.label": {"fr": "PROCÉDÉ STABLE", "en": "PROCESS STABLE"},
    "home.state.STABLE.sub": {"fr": "Fonctionnement nominal", "en": "Nominal operation"},
    "home.state.STABLE.impact": {"fr": "Film conforme — aucun risque qualité identifié",
                                 "en": "Compliant film — no identified quality risk"},
    "home.state.SURVEILLER.label": {"fr": "À SURVEILLER", "en": "TO MONITOR"},
    "home.state.SURVEILLER.sub": {"fr": "Surveillance renforcée", "en": "Heightened monitoring"},
    "home.state.SURVEILLER.impact": {
        "fr": "Instabilité thermique naissante — qualité film à contrôler",
        "en": "Emerging thermal instability — check film quality"},
    "home.state.CRITIQUE.label": {"fr": "INSTABLE CRITIQUE", "en": "CRITICALLY UNSTABLE"},
    "home.state.CRITIQUE.sub": {"fr": "Intervention requise", "en": "Intervention required"},
    "home.state.CRITIQUE.impact": {
        "fr": "Risque film non conforme — correction ou arrêt immédiat",
        "en": "Non-compliant film risk — correct or stop immediately"},

    # ===================================================================
    # PAGE — Configuration procédé (Profile)
    # ===================================================================
    "page.profile.title": {"fr": "Configuration procédé — Rondol",
                           "en": "Process Configuration — Rondol"},
    "profile.banner.left": {"fr": "● Rondol · Configuration procédé",
                            "en": "● Rondol · Process Configuration"},
    "profile.banner.right": {"fr": "AGENT IA — Extrusion SSB dry/semi-dry",
                             "en": "AI AGENT — SSB dry/semi-dry extrusion"},
    "profile.sidebar.params": {"fr": "PARAMÈTRES PROCÉDÉ", "en": "PROCESS PARAMETERS"},
    "profile.sidebar.params_caption": {
        "fr": "Valeurs servant aux calculs Fill / Résidence",
        "en": "Values used for Fill / Residence calculations"},
    "profile.sidebar.rpm": {"fr": "Vitesse vis (rpm)", "en": "Screw speed (rpm)"},
    "profile.sidebar.feed": {"fr": "Débit feeder (g/min)", "en": "Feeder rate (g/min)"},
    "profile.sidebar.dens": {"fr": "Densité bulk (g/cm³)", "en": "Bulk density (g/cm³)"},
    "profile.sidebar.dosage": {"fr": "DOSAGE", "en": "DOSING"},
    "profile.sidebar.sf_caption": {
        "fr": "Side feeder : 0 = désactivé · 1..8 = zone procédé Z1..Z8",
        "en": "Side feeder: 0 = disabled · 1..8 = process zone Z1..Z8"},
    "profile.sidebar.sf_zone": {"fr": "Side feeder zone", "en": "Side feeder zone"},
    "profile.sidebar.sf_disabled": {"fr": "Désactivé", "en": "Disabled"},
    "profile.sidebar.sf_off": {"fr": "Side feeder désactivé.", "en": "Side feeder disabled."},
    "profile.sidebar.sf_pos": {"fr": "Side feeder Z{z} → position vis #{pos}",
                               "en": "Side feeder Z{z} → screw position #{pos}"},
    "profile.btn.reset": {"fr": "⟲ Réinitialiser la configuration",
                          "en": "⟲ Reset configuration"},
    "profile.btn.demo": {"fr": "⊕ Configuration démo", "en": "⊕ Demo configuration"},
    "profile.btn.demo_chaotic": {"fr": "◇ Demo chaotic (losange)",
                                 "en": "◇ Chaotic demo (diamond)"},
    "profile.sidebar.freevol": {"fr": "Volume libre total : 76,18 cm³",
                                "en": "Total free volume: 76.18 cm³"},
    "profile.sidebar.layout": {"fr": "81 positions · 9 zones · Main feeder @ pos 4",
                               "en": "81 positions · 9 zones · Main feeder @ pos 4"},
    "profile.sec.assembly": {"fr": "Profil de vis assemblé", "en": "Assembled screw profile"},
    "profile.cap.assembly": {
        "fr": "Hélice continue de bout en bout (base procédurale). Les blocs (kneading, "
              "toothed, special mixing) apparaissent comme objets 3D centrés au-dessus. "
              "Survolez un élément pour voir sa position. Bandeau supérieur : Feed + Z1..Z8 "
              "avec résidence par zone. Marqueurs : ▼ Main feeder · ▼ Side feeder (si activé).",
        "en": "Continuous helix end to end (procedural base). Blocks (kneading, toothed, "
              "special mixing) appear as 3D objects centred above. Hover an element to see "
              "its position. Top bar: Feed + Z1..Z8 with per-zone residence. "
              "Markers: ▼ Main feeder · ▼ Side feeder (if enabled)."},
    "profile.sec.metier": {"fr": "Lecture métier — éléments placés",
                           "en": "Business reading — placed elements"},
    "profile.tbl.zone": {"fr": "ZONE", "en": "ZONE"},
    "profile.tbl.position": {"fr": "POSITION", "en": "POSITION"},
    "profile.tbl.element": {"fr": "ÉLÉMENT", "en": "ELEMENT"},
    "profile.tbl.role": {"fr": "RÔLE PROCÉDÉ", "en": "PROCESS ROLE"},
    "profile.tbl.empty": {
        "fr": "Aucun élément placé — vis nue (shaft + tip final uniquement).",
        "en": "No element placed — bare screw (shaft + final tip only)."},
    "profile.tbl.synthesis": {"fr": "Synthèse par zone", "en": "Per-zone summary"},
    "profile.tbl.cell_empty": {"fr": "vide", "en": "empty"},
    "profile.sec.kpis": {"fr": "Indicateurs procédé", "en": "Process indicators"},
    "profile.cap.kpis": {
        "fr": "Calculés en temps réel à partir de la configuration vis et des "
              "paramètres procédé courants ({rpm} rpm · {feed} g/min · ρ = {dens} g/cm³).",
        "en": "Computed in real time from the screw configuration and current process "
              "parameters ({rpm} rpm · {feed} g/min · ρ = {dens} g/cm³)."},
    "profile.kpi.added": {"fr": "Éléments ajoutés", "en": "Elements added"},
    "profile.kpi.added_help": {
        "fr": "Nombre d'éléments placés sur la vis (tip exclu). 1 élément entier = 1 unité ; "
              "1 demi-convoyage = 0,5 unité. Capacité max : 39 unités.",
        "en": "Number of elements placed on the screw (tip excluded). 1 full element = 1 unit; "
              "1 half conveying = 0.5 unit. Max capacity: 39 units."},
    "profile.kpi.slots": {"fr": "Slots restants", "en": "Remaining slots"},
    "profile.kpi.slots_help": {
        "fr": "Capacité utilisateur restante avant saturation (39 − ajoutés). "
              "Devient 0 quand la vis est complète.",
        "en": "Remaining user capacity before saturation (39 − added). "
              "Reaches 0 when the screw is full."},
    "profile.kpi.vol_used": {"fr": "Volume occupé / vis", "en": "Occupied volume / screw"},
    "profile.cap.volumes": {
        "fr": "Volume occupé / vis : {per} cm³ · Volume occupé total (2 vis) : {total} cm³ "
              "· Volume libre utile : {free} cm³",
        "en": "Occupied volume / screw: {per} cm³ · Total occupied (2 screws): {total} cm³ "
              "· Usable free volume: {free} cm³"},
    "profile.kpi.vol_used_help": {
        "fr": "Volume de matière solide occupé par les éléments de vis. "
              "Le pourcentage est rapporté au volume libre nominal de la chambre.",
        "en": "Solid volume occupied by the screw elements. "
              "The percentage is relative to the nominal free volume of the chamber."},
    "profile.kpi.vol_free": {"fr": "Volume libre utile", "en": "Usable free volume"},
    "profile.kpi.vol_free_help": {
        "fr": "Volume libre restant pour la matière (max {maxv} cm³ vis vide).",
        "en": "Free volume left for the material (max {maxv} cm³ when screw is empty)."},
    "profile.kpi.ff": {"fr": "Taux de remplissage moyen (%)", "en": "Mean fill factor (%)"},
    "profile.kpi.ff_help": {
        "fr": "Fill Factor moyen — fraction du volume libre effectivement remplie de matière, "
              "moyennée sur l'ensemble de la vis (positions main feeder → tip). "
              "Un FF élevé indique une vis correctement alimentée.",
        "en": "Mean fill factor — fraction of the free volume actually filled with material, "
              "averaged over the whole screw (main feeder → tip positions). "
              "A high FF indicates a properly fed screw."},
    "profile.kpi.rt": {"fr": "Temps de résidence total (s)", "en": "Total residence time (s)"},
    "profile.kpi.rt_help": {
        "fr": "Temps de séjour total de la matière dans la vis, somme des temps de résidence "
              "locaux pondérés par le volume disponible. Plus le RT est long, plus la matière "
              "est cisaillée / mélangée / chauffée.",
        "en": "Total dwell time of the material in the screw, sum of local residence times "
              "weighted by the available volume. The longer the RT, the more the material is "
              "sheared / mixed / heated."},
    "profile.sec.build": {"fr": "Construction du profil de vis", "en": "Screw profile construction"},
    "profile.cap.build": {
        "fr": "Cliquez sur **+1** ou **+4** pour ajouter un type d'élément à la prochaine "
              "position libre après le main feeder. **−1** retire l'élément le plus en aval "
              "de ce type. La pointe (tip) est verrouillée et ne se compte pas.",
        "en": "Click **+1** or **+4** to add an element type at the next free position after "
              "the main feeder. **−1** removes the most downstream element of that type. "
              "The tip is locked and is not counted."},
    "profile.sec.reading": {"fr": "Lecture procédé — Agent IA", "en": "Process reading — AI agent"},
    "profile.cap.reading": {
        "fr": "Analyse haut-niveau du profil de vis × régime procédé courant. "
              "Prend en compte vitesse vis, débit feeder et densité bulk de Settings.",
        "en": "High-level analysis of the screw profile × current process regime. "
              "Accounts for screw speed, feeder rate and bulk density from Settings."},
    "profile.sec.recos": {"fr": "Recommandations Agent IA", "en": "AI agent recommendations"},
    "profile.cap.recos": {
        "fr": "Pour chaque recommandation : **zone** concernée · **problème physique** · "
              "**impact procédé** · **action** chiffrée (sensible aux paramètres Settings).",
        "en": "For each recommendation: **zone** concerned · **physical problem** · "
              "**process impact** · quantified **action** (sensitive to Settings parameters)."},
    "profile.sec.count": {"fr": "Combien d'éléments choisir ? (25 · 30 · 40)",
                          "en": "How many elements? (25 · 30 · 40)"},
    "profile.cap.count": {
        "fr": "Arbitrage automatique entre les 3 longueurs de vis Rondol courantes, "
              "basé sur la config courante (taux de remplissage, ratio convoyage/mélange, "
              "objectif procédé).",
        "en": "Automatic trade-off between the 3 common Rondol screw lengths, based on the "
              "current configuration (fill factor, conveying/mixing ratio, process objective)."},
    "profile.sec.systemic": {"fr": "Raisonnement global procédé — Agent IA système",
                             "en": "Global process reasoning — System AI agent"},
    "profile.cap.systemic": {
        "fr": "Vision systémique : équilibre transport / dispersion / thermique / capacité. "
              "L'agent vérifie la cohérence du profil dans son ensemble, propose des "
              "compensations pour préserver l'équilibre, et expose les trade-offs derrière "
              "chaque recommandation.",
        "en": "Systemic view: transport / dispersion / thermal / capacity balance. "
              "The agent checks the overall consistency of the profile, proposes "
              "compensations to preserve the balance, and exposes the trade-offs behind "
              "each recommendation."},
    "profile.sec.residence": {"fr": "Temps de résidence par zone", "en": "Residence time per zone"},
    "profile.cap.residence": {
        "fr": "Vitesse vis : {rpm} rpm · Débit feeder : {feed} g/min · "
              "Densité : {dens} g/cm³ · Volume libre nominal : {maxv} cm³",
        "en": "Screw speed: {rpm} rpm · Feeder rate: {feed} g/min · "
              "Density: {dens} g/cm³ · Nominal free volume: {maxv} cm³"},

    # ===================================================================
    # PAGE — Paramètres IA & feeders (Settings)
    # ===================================================================
    "page.settings.title": {"fr": "Paramètres IA & feeders — Rondol",
                            "en": "AI & feeders settings — Rondol"},
    "settings.banner.left": {"fr": "● Rondol · Paramètres IA & feeders",
                             "en": "● Rondol · AI & feeders settings"},
    "settings.banner.right": {"fr": "SVM w60 · Bivis 10,5 mm · SSB",
                              "en": "SVM w60 · 10.5 mm twin-screw · SSB"},
    "settings.save.btn": {"fr": "✓ Enregistrer la configuration",
                          "en": "✓ Save configuration"},
    "settings.save.help": {
        "fr": "Valide les paramètres en cours d'édition comme nouvelle configuration "
              "enregistrée. Supervision passe sur cette nouvelle version. "
              "L'historique conserve toutes les versions précédentes.",
        "en": "Commits the parameters being edited as the new saved configuration. "
              "Supervision switches to this new version. "
              "History keeps all previous versions."},
    "settings.save.label": {"fr": "Libellé (optionnel)", "en": "Label (optional)"},
    "settings.save.placeholder": {"fr": "Ex. Test #3 LFP+LATP", "en": "e.g. Test #3 LFP+LATP"},
    "settings.status.unsaved": {
        "fr": "MODIFICATIONS NON ENREGISTRÉES — Supervision affiche l'ancienne version",
        "en": "UNSAVED CHANGES — Supervision shows the previous version"},
    "settings.status.none": {"fr": "AUCUNE CONFIG ENREGISTRÉE — cliquer Enregistrer",
                             "en": "NO SAVED CONFIG — click Save"},
    "settings.status.uptodate": {"fr": "À JOUR — Supervision synchronisée",
                                 "en": "UP TO DATE — Supervision synced"},
    "settings.status.no_label": {"fr": "(sans libellé)", "en": "(no label)"},
    "settings.status.meta": {"fr": "Dernier enreg. : {iso} {label} · historique : {n} snapshot(s)",
                             "en": "Last save: {iso} {label} · history: {n} snapshot(s)"},
    # Libellés HMI (francisés en FR — Décision 2 ; variables/unités inchangées)
    "settings.kv.reg_band": {"fr": "BANDE RÉGUL.", "en": "REG. BAND"},
    "settings.kv.thermal_peak": {"fr": "PIC THERMIQUE", "en": "THERMAL PEAK"},
    "settings.kv.ceiling": {"fr": "PLAFOND", "en": "CEILING"},
    "settings.kv.ceiling_src": {"fr": "SOURCE PLAFOND", "en": "CEILING SOURCE"},
    "settings.kv.t_real": {"fr": "T RÉELLE", "en": "REAL T"},
    "settings.kv.dt_dissip": {"fr": "ΔT DISSIP.", "en": "ΔT DISSIP."},
    "settings.kv.instability": {"fr": "INSTABILITÉ", "en": "INSTABILITY"},
    "settings.kv.torque": {"fr": "COUPLE", "en": "TORQUE"},
    "settings.kv.model": {"fr": "MODÈLE", "en": "MODEL"},
    "settings.kv.fill_factor": {"fr": "TAUX REMPLISSAGE", "en": "FILL FACTOR"},
    "settings.kv.residence": {"fr": "RÉSIDENCE", "en": "RESIDENCE"},
    "settings.kv.free_vol": {"fr": "VOLUME LIBRE", "en": "FREE VOL"},
    "settings.kv.elements": {"fr": "ÉLÉMENTS", "en": "ELEMENTS"},
    "settings.kv.archetype": {"fr": "ARCHÉTYPE", "en": "ARCHETYPE"},
    "settings.kv.alerts": {"fr": "ALERTES", "en": "ALERTS"},
    "settings.kv.score": {"fr": "SCORE IA", "en": "AI SCORE"},
    "settings.kv.state": {"fr": "ÉTAT", "en": "STATE"},
    "settings.kv.total": {"fr": "TOTAL", "en": "TOTAL"},
    "settings.kv.solid": {"fr": "SOLIDE", "en": "SOLID"},
    "settings.kv.liquid": {"fr": "LIQUIDE", "en": "LIQUID"},
    "settings.kv.gas": {"fr": "GAZ", "en": "GAS"},
    "settings.block.thermal": {
        "fr": "PROFIL THERMIQUE EXTRUSION · CONSIGNES Z1→Z8 + FILIÈRE",
        "en": "EXTRUSION THERMAL PROFILE · SETPOINTS Z1→Z8 + DIE"},
    "settings.block.feeders": {
        "fr": "FEEDERS · TYPE · DENSITÉ BULK · DILATATION THERMIQUE · POSITION",
        "en": "FEEDERS · TYPE · BULK DENSITY · THERMAL EXPANSION · POSITION"},
    "settings.block.sme": {"fr": "SME · DÉBIT MASSIQUE · COUPLE · PRESSION",
                           "en": "SME · MASS FLOW RATE · TORQUE · PRESSURE"},
    "settings.n_die_zones": {"fr": "NOMBRE DE ZONES DIE", "en": "NUMBER OF DIE ZONES"},
    "settings.die_zone_fmt": {"fr": "{n} zone die", "en": "{n} die zone"},
    "settings.die_zone_fmt_plural": {"fr": "{n} zones die", "en": "{n} die zones"},
    "settings.feeder.label": {"fr": "Label", "en": "Label"},
    "settings.feeder.type": {"fr": "Type", "en": "Type"},
    "settings.feeder.pos": {"fr": "Pos", "en": "Pos"},
    "settings.feeder.toggle_help": {"fr": "Activer/désactiver feeder {fid}",
                                    "en": "Enable/disable feeder {fid}"},
    "settings.feeder.dens_help": {"fr": "Bulk density g/cm³", "en": "Bulk density g/cm³"},
    "settings.feeder.alpha_help": {"fr": "Thermal expansion 1/K", "en": "Thermal expansion 1/K"},
    "settings.expander.matprops": {
        "fr": "▼ Propriétés matière étendues par feeder "
              "(polymère, T° dégradation, ATG/TGA, viscosité)",
        "en": "▼ Extended material properties per feeder "
              "(polymer, degradation T°, TGA, viscosity)"},
    "settings.matprops.caption": {
        "fr": "Données consommées par l'IA : la borne haute effective devient "
              "min(T° dégradation, ATG onset, défaut famille matière). "
              "Viscosité → module la dissipation visqueuse dans le calcul de T réelle.",
        "en": "Data consumed by the AI: the effective upper bound becomes "
              "min(degradation T°, TGA onset, material-family default). "
              "Viscosity → modulates viscous dissipation in the real-T computation."},
    "settings.mat.polymer": {"fr": "Polymère / mélange", "en": "Polymer / blend"},
    "settings.mat.tdeg": {"fr": "T° dégradation (°C)", "en": "Degradation T° (°C)"},
    "settings.mat.tdeg_help": {"fr": "Si > 0, prend le pas sur la borne famille matière.",
                               "en": "If > 0, overrides the material-family bound."},
    "settings.mat.tga": {"fr": "ATG/TGA onset (°C)", "en": "TGA onset (°C)"},
    "settings.mat.tga_help": {"fr": "Onset perte massique mesurée ATG.",
                              "en": "Measured TGA mass-loss onset."},
    "settings.mat.visc": {"fr": "Viscosité (Pa·s)", "en": "Viscosity (Pa·s)"},
    "settings.mat.visc_help": {"fr": "Viscosité de référence — module l'échauffement par cisaillement.",
                               "en": "Reference viscosity — modulates shear heating."},
    "settings.mat.tmelt": {"fr": "T° fusion Tm (°C)", "en": "Melting T° Tm (°C)"},
    "settings.mat.tglass": {"fr": "T° vitreuse Tg (°C)", "en": "Glass T° Tg (°C)"},
    "settings.vis_rpm": {"fr": "VIS rpm", "en": "SCREW rpm"},
    "settings.torque_pct": {"fr": "TORQUE %", "en": "TORQUE %"},
    "settings.torque_help": {"fr": "V2 — feedback torque réel (sinon estimation auto).",
                             "en": "V2 — real torque feedback (otherwise auto estimate)."},
    "settings.pdie": {"fr": "P-DIE bar", "en": "P-DIE bar"},
    "settings.pdie_help": {"fr": "V2 — pression filière streaming (OPC-UA / API).",
                           "en": "V2 — streaming die pressure (OPC-UA / API)."},
    "settings.alerts.none": {
        "fr": "✦ AUCUNE ALERTE — Procédé nominal sur toutes les règles évaluées.",
        "en": "✦ NO ALERT — Nominal process on all evaluated rules."},
    "settings.expander.advanced": {
        "fr": "⚙ Réglages avancés — seuils IA, variables surveillées, modèle SVM w60",
        "en": "⚙ Advanced settings — AI thresholds, monitored variables, SVM w60 model"},
    "settings.adv.thresholds": {"fr": "Seuils de classification", "en": "Classification thresholds"},
    "settings.adv.th_stable": {"fr": "Score STABLE (≥)", "en": "STABLE score (≥)"},
    "settings.adv.th_critical": {"fr": "Score CRITIQUE (<)", "en": "CRITICAL score (<)"},
    "settings.adv.th_pstable": {"fr": "P(stable) STABLE (≥)", "en": "P(stable) STABLE (≥)"},
    "settings.adv.th_pcritical": {"fr": "P(stable) CRITIQUE (<)", "en": "P(stable) CRITICAL (<)"},
    "settings.adv.warn_stable": {"fr": "⚠ Seuil CRITIQUE doit être strictement < STABLE.",
                                 "en": "⚠ CRITICAL threshold must be strictly < STABLE."},
    "settings.adv.warn_pstable": {
        "fr": "⚠ P(stable) CRITIQUE doit être strictement < P(stable) STABLE.",
        "en": "⚠ P(stable) CRITICAL must be strictly < P(stable) STABLE."},
    "settings.adv.monitored": {"fr": "Variables surveillées & fréquence",
                               "en": "Monitored variables & frequency"},
    "settings.adv.sensors": {"fr": "Capteurs intégrés au modèle IA",
                             "en": "Sensors fed to the AI model"},
    "settings.adv.hz": {"fr": "Fréquence analyse (Hz)", "en": "Analysis frequency (Hz)"},
    "settings.adv.targets": {"fr": "Cibles procédé", "en": "Process targets"},
    "settings.adv.ff_target": {"fr": "Fill Factor cible (%)", "en": "Target fill factor (%)"},
    "settings.adv.screw_target": {"fr": "Config vis cible (L/D)", "en": "Target screw config (L/D)"},
    "settings.adv.elements_fmt": {"fr": "{v} éléments", "en": "{v} elements"},
    "settings.adv.sf_zone": {"fr": "Side feeder zone", "en": "Side feeder zone"},
    "settings.adv.sf_caption": {
        "fr": "{z} — piloté par le Feeder #2 (grille Feeders). "
              "Activez/positionnez le feeder #2 pour changer la zone side feed.",
        "en": "{z} — driven by Feeder #2 (Feeders grid). "
              "Enable/position feeder #2 to change the side-feed zone."},
    "settings.expander.svm": {
        "fr": "📊 Modèle SVM w60 — métriques, calibration, top features, pipeline",
        "en": "📊 SVM w60 model — metrics, calibration, top features, pipeline"},
    "settings.svm.algo": {"fr": "Algorithme", "en": "Algorithm"},
    "settings.svm.window": {"fr": "Fenêtre", "en": "Window"},
    "settings.svm.threshold": {"fr": "Seuil déploiement", "en": "Deployment threshold"},
    "settings.svm.calibration": {"fr": "Sensibilité au seuil (calibration)",
                                 "en": "Threshold sensitivity (calibration)"},
    "settings.svm.top15": {"fr": "Top 15 features", "en": "Top 15 features"},
    "settings.svm.pipeline": {"fr": "Pipeline ML", "en": "ML pipeline"},
    "settings.svm.metrics_na": {
        "fr": "Métriques modèle non disponibles (reports/ml_metrics_w60.json absent).",
        "en": "Model metrics unavailable (reports/ml_metrics_w60.json missing)."},

    # ===================================================================
    # PAGE — Analyse du run
    # ===================================================================
    "page.analyse.title": {"fr": "Analyse du run — Rondol", "en": "Run analysis — Rondol"},
    "analyse.header": {"fr": "#### Rondol · Analyse du run", "en": "#### Rondol · Run analysis"},
    "analyse.sidebar.run": {"fr": "Run de production", "en": "Production run"},
    "analyse.m.windows": {"fr": "Fenêtres", "en": "Windows"},
    "analyse.m.pct_stable": {"fr": "% Stable", "en": "% Stable"},
    "analyse.m.pct_critical": {"fr": "% Critique", "en": "% Critical"},
    "analyse.sec.score": {"fr": "Score de stabilité (toutes fenêtres)",
                          "en": "Stability score (all windows)"},
    "analyse.cap.score": {"fr": "Seuil stable = {th}/100 — P(stable) × 100 affiché en pointillés",
                          "en": "Stable threshold = {th}/100 — P(stable) × 100 shown dotted"},
    "analyse.sec.detail": {"fr": "Détail des fenêtres", "en": "Window detail"},
    "analyse.tbl.start": {"fr": "Début", "en": "Start"},
    "analyse.tbl.end": {"fr": "Fin", "en": "End"},
    "analyse.tbl.score": {"fr": "Score", "en": "Score"},
    "analyse.tbl.pstable": {"fr": "P(stable)", "en": "P(stable)"},
    "analyse.tbl.state": {"fr": "État", "en": "State"},
    "analyse.tbl.samples": {"fr": "Échantillons", "en": "Samples"},
    "analyse.sec.thermal": {"fr": "Profil thermique moyen (T°C moyenne par zone)",
                            "en": "Mean thermal profile (mean T°C per zone)"},
    "analyse.tbl.t_mean": {"fr": "T°C moy.", "en": "Mean T°C"},
    "analyse.tbl.sigma_mean": {"fr": "sigma moy.", "en": "Mean sigma"},
}


# ---------------------------------------------------------------------------
# Langue courante
# ---------------------------------------------------------------------------
def current_lang() -> str:
    """Langue active (``"fr"`` par défaut).

    Tolérant hors contexte Streamlit (tests purs) : si ``session_state`` n'est
    pas accessible, retourne la langue par défaut.
    """
    try:
        lang = st.session_state.get(LANG_KEY, DEFAULT_LANG)
    except Exception:  # pragma: no cover - hors ScriptRunContext
        lang = DEFAULT_LANG
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_lang(lang: str) -> None:
    """Force la langue (validée contre la liste supportée)."""
    st.session_state[LANG_KEY] = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


# ---------------------------------------------------------------------------
# Traduction du chrome
# ---------------------------------------------------------------------------
def t(key: str, /, **kwargs: object) -> str:
    """Retourne le texte de chrome pour ``key`` dans la langue courante.

    Fallback en cascade : langue courante → FR → clé brute. Le formatage est
    protégé (placeholder manquant → gabarit non formaté).
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    lang = current_lang()
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def m(msg_id: str, /, **params: object) -> str:
    """Wrapper Streamlit du catalogue agent pur : injecte la langue courante."""
    return i18n_messages.m(msg_id, current_lang(), **params)


# ---------------------------------------------------------------------------
# Sélecteur de langue (widget sidebar, clé-only)
# ---------------------------------------------------------------------------
def language_selector(location: object | None = None) -> str:
    """Affiche le sélecteur FR/English et retourne la langue active.

    Pattern clé-only : le widget est piloté par ``st.session_state[LANG_KEY]``
    (pas de ``value=``/``index=``), ce qui évite les avertissements Streamlit
    et fait du widget la source de vérité unique de la langue.

    En multipage, la sidebar n'est pas partagée : chaque page appelle ce
    helper, mais toutes lisent la même clé de session → langue cohérente.
    """
    container = location if location is not None else st.sidebar
    if st.session_state.get(LANG_KEY) not in SUPPORTED_LANGS:
        st.session_state[LANG_KEY] = DEFAULT_LANG
    container.radio(
        t("lang.selector_label"),
        options=list(SUPPORTED_LANGS),
        format_func=lambda c: _LANG_LABELS.get(c, c),
        horizontal=True,
        key=LANG_KEY,
    )
    return current_lang()
