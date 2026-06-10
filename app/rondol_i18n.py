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
DEFAULT_LANG = "en"
SUPPORTED_LANGS: tuple[str, ...] = ("en", "fr")
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
    "home.agent.state.STABLE": {"fr": "STABLE", "en": "STABLE"},
    "home.agent.state.SURVEILLER": {"fr": "SURVEILLER", "en": "MONITOR"},
    "home.agent.state.CRITIQUE": {"fr": "CRITIQUE", "en": "CRITICAL"},
    "home.agent.diag.stable": {
        "fr": "Procédé nominal : {n_act} feeder(s) actif(s), FF={ff}, RT={rt} s, SME={sme} kWh/kg. Aucune alerte critique.",
        "en": "Nominal process: {n_act} active feeder(s), FF={ff}, RT={rt} s, SME={sme} kWh/kg. No critical alert."},
    "home.agent.diag.watch": {
        "fr": "Surveillance renforcée : {n_warn} avertissement(s) et {n_crit} alerte(s) critique(s). Vérifier les recommandations agent avant de poursuivre.",
        "en": "Enhanced monitoring: {n_warn} warning(s) and {n_crit} critical alert(s). Review agent recommendations before proceeding."},
    "home.agent.diag.critical": {
        "fr": "État critique (score {score}/100) : {n_crit} alerte(s) critique(s) + {n_warn} avertissement(s). Application des recommandations agent IA prioritaire avant production.",
        "en": "Critical state (score {score}/100): {n_crit} critical alert(s) + {n_warn} warning(s). Applying AI agent recommendations is priority before production."},
    "home.agent.alerts_label": {"fr": "alerte(s)", "en": "alert(s)"},
    "home.agent.recos_label": {"fr": "reco(s)", "en": "reco(s)"},
    "home.agent.thermal_peak": {"fr": "pic thermique", "en": "thermal peak"},
    "home.agent.torque": {"fr": "couple", "en": "torque"},
    "home.agent.setpoint": {"fr": "cons.", "en": "set."},
    "home.agent.ceiling": {"fr": "plafond", "en": "ceiling"},
    "home.agent.model": {"fr": "modèle", "en": "model"},
    "home.chart.threshold": {"fr": "Seuil", "en": "Threshold"},
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
    # Phase S1 stabilisation 2026-06-09 : Profile sidebar passe en lecture seule
    # pour RPM/débit/densité (édition centralisée dans Settings).
    "profile.sidebar.params_caption_ro": {
        "fr": "Valeurs pilotées depuis **Settings** — lecture seule ici.",
        "en": "Values piloted from **Settings** — read-only here.",
    },
    "profile.sidebar.piloted_by_settings": {
        "fr": "ℹ️ Pour modifier ces valeurs, allez dans **Paramètres IA & feeders**.",
        "en": "ℹ️ To modify these values, go to **AI & feeders settings**.",
    },
    "profile.sidebar.feed_not_calculable": {
        "fr": "Non calculable",
        "en": "Not computable",
    },
    "profile.sidebar.feed_calibrated_hint": {
        "fr": "Étalonnage : {rpm} RPM × {coeff} g/h/RPM",
        "en": "Calibration: {rpm} RPM × {coeff} g/h/RPM",
    },
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
    "profile.tip_lock": {"fr": "fin de vis", "en": "screw tip"},
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
    "settings.kv.process_fallback": {"fr": "PROCÉDÉ", "en": "PROCESS"},
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
    # Manager 2026-06-09 : option « pas de filière » (calculs filière → N/A).
    "settings.card.alert": {"fr": "ALERTE", "en": "ALERT"},
    "settings.card.action": {"fr": "ACTION", "en": "ACTION"},
    "settings.die.label": {"fr": "Filière", "en": "Die"},
    "settings.die.ramp_ok": {"fr": "rampe décroissante", "en": "decreasing ramp"},
    "settings.die.ramp_nok": {"fr": "profil die non décroissant (cf. alertes IA)", "en": "non-decreasing die profile (see AI alerts)"},
    "settings.die_zone_fmt_zero": {"fr": "0 zone filière", "en": "0 die zone"},
    "settings.die_zone_absent": {
        "fr": "Filière 0 zone · aucune consigne die requise — calculs filière "
              "non applicables (Non applicable / Not applicable).",
        "en": "Die 0 zone · no die setpoint required — die-dependent "
              "calculations not applicable.",
    },
    "settings.feeder.label": {"fr": "Label", "en": "Label"},
    "settings.feeder.type": {"fr": "Type", "en": "Type"},
    "settings.feeder.pos": {"fr": "Pos", "en": "Pos"},
    "settings.feeder.toggle_help": {"fr": "Activer/désactiver feeder {fid}",
                                    "en": "Enable/disable feeder {fid}"},
    "settings.feeder.dens_help": {"fr": "Bulk density g/cm³", "en": "Bulk density g/cm³"},
    "settings.feeder.alpha_help": {"fr": "Thermal expansion 1/K", "en": "Thermal expansion 1/K"},
    # Phase 4 — unités visibles dans les labels (pas seulement tooltip).
    "settings.feeder.dens_label": {
        "fr": "Densité bulk (g/cm³)",
        "en": "Bulk density (g/cm³)",
    },
    "settings.feeder.alpha_label": {
        "fr": "Dilatation thermique (1/K)",
        "en": "Thermal expansion (1/K)",
    },
    "settings.feeder.flow_unit": {"fr": "g/min", "en": "g/min"},
    # Manager 2026-06-09 — saisie SME verrouillée quand l'étalonnage est présent
    # (source de vérité unique pour le débit feeder).
    "settings.feeder.flow_locked_by_calibration": {
        "fr": "Débit calculé via l'étalonnage (RPM × coefficient) — modifier "
              "le coefficient pour changer ce débit.",
        "en": "Flow computed from calibration (RPM × coefficient) — edit "
              "the coefficient to change this flow.",
    },
    "settings.feeder.flow_from_calibration": {
        "fr": "✓ Débit étalonné : {v} g/min (verrouillé)",
        "en": "✓ Calibrated flow: {v} g/min (locked)",
    },
    # Phase 5 — températures rouges : « estimé » au lieu de « réel ».
    "settings.t_estimated_short": {"fr": "estimé", "en": "estimated"},
    "settings.t_estimated_tooltip": {
        "fr": "Température théorique estimée avant compensation cooling machine. "
              "Ce n'est PAS une mesure capteur.",
        "en": "Estimated theoretical temperature before machine cooling "
              "compensation. This is NOT a sensor measurement.",
    },
    # Phase 10 — Bandeau « Analyse indicative » sur Supervision quand aucun
    # snapshot validé n'existe ou que la vis est vide.
    "home.profile_indicative.title": {
        "fr": "**Analyse indicative — données incomplètes.**",
        "en": "**Indicative analysis — incomplete data.**",
    },
    "home.profile_indicative.body": {
        "fr": "Aucun profil enregistré (cliquez **Enregistrer** dans "
              "**Paramètres IA & feeders**) ou aucun élément placé sur la vis "
              "(page **Profile**). Le commentaire ci-dessous reflète les "
              "défauts, pas un profil opérateur validé.",
        "en": "No saved profile (click **Save** in **AI & feeders settings**) "
              "or no element placed on the screw (page **Profile**). The "
              "comment below reflects defaults, not a validated operator profile.",
    },
    # Phase 11 — Historique : sections composition matière par feeder + zones.
    "historique.comp_title": {
        "fr": "Composition matière par feeder (figée au commit)",
        "en": "Per-feeder material composition (frozen at commit)",
    },
    "historique.comp_absent": {
        "fr": "Composition matière par feeder : non renseignée pour ce procédé "
              "(aucun feeder activé avec composition saisie).",
        "en": "Per-feeder material composition: not entered for this run "
              "(no enabled feeder has a composition).",
    },
    "historique.comp_col.feeder": {"fr": "Feeder", "en": "Feeder"},
    "historique.comp_col.label": {"fr": "Label", "en": "Label"},
    "historique.comp_col.position": {"fr": "Position", "en": "Position"},
    "historique.comp_col.composition": {"fr": "Composition", "en": "Composition"},
    "historique.comp_col.flow": {"fr": "Débit (g/min)", "en": "Flow (g/min)"},
    "historique.comp_col.density": {"fr": "ρ (g/cm³)", "en": "ρ (g/cm³)"},
    "historique.comp_col.tdeg": {"fr": "T° dégradation (°C)", "en": "Degradation T° (°C)"},
    "historique.comp_not_entered": {"fr": "Non renseigné", "en": "Not entered"},
    # Phase S2 — Historique : agrégats par zone + statut agent (i18n complet).
    "historique.zones_title": {
        "fr": "Agrégats par zone (figés au commit)",
        "en": "Per-zone aggregates (frozen at commit)",
    },
    # Libellés exacts exigés par le manager (S2-bis 2026-06-10).
    "historique.zones_absent": {
        "fr": "Agrégats par zone non disponibles pour ce procédé.",
        "en": "Per-zone aggregates not available for this process.",
    },
    "historique.zones_not_significant": {
        "fr": "Agrégats par zone non disponibles pour ce procédé. "
              "Valeurs non significatives au moment du commit "
              "(vis vide ou débit nul) — table masquée.",
        "en": "Per-zone aggregates not available for this process. "
              "Values not meaningful at commit time "
              "(empty screw or zero flow) — table hidden.",
    },
    "historique.zones_col.zone": {"fr": "Zone", "en": "Zone"},
    "historique.zones_col.fill_mean": {"fr": "Fill moyen", "en": "Mean fill"},
    "historique.zones_col.fill_peak": {"fr": "Fill crête", "en": "Peak fill"},
    "historique.zones_col.residence": {"fr": "Résidence (s)", "en": "Residence (s)"},
    "historique.zones_col.material": {"fr": "Matière dominante", "en": "Dominant material"},
    "historique.agent_title": {"fr": "Statut agent (figé)", "en": "Agent status (frozen)"},
    "historique.agent_absent": {
        "fr": "Statut agent (décision / score / alertes) : non disponible — "
              "non figé au moment de l'enregistrement.",
        "en": "Agent status (decision / score / alerts): unavailable — "
              "not frozen at save time.",
    },
    # Phase S2 — Profile : bannières capacité + messages d'action (i18n).
    "profile.banner.empty": {
        "fr": "<b>Vis vide.</b> Aucun élément après le main feeder — "
              "les indicateurs Fill Factor et Résidence valent 0. "
              "Ajoutez des éléments via <b>+1 / +4</b> ci-dessous, "
              "ou cliquez <b>⊕ Configuration démo</b> dans la barre latérale.",
        "en": "<b>Empty screw.</b> No element after the main feeder — "
              "the Fill Factor and Residence indicators are 0. "
              "Add elements with <b>+1 / +4</b> below, "
              "or click <b>⊕ Demo configuration</b> in the sidebar.",
    },
    "profile.banner.full": {
        "fr": "<b>Capacité maximale atteinte</b> ({n} / {max} éléments). "
              "Retirez un élément avec <b>−1</b> pour libérer un slot.",
        "en": "<b>Maximum capacity reached</b> ({n} / {max} elements). "
              "Remove an element with <b>−1</b> to free a slot.",
    },
    "profile.banner.almost_full": {
        "fr": "<b>Capacité presque pleine</b> : {n} slot(s) restant(s). "
              "Le bouton <b>+4</b> reste désactivé tant qu'il y a moins de "
              "4 slots libres.",
        "en": "<b>Capacity almost full</b>: {n} slot(s) left. "
              "The <b>+4</b> button stays disabled while fewer than "
              "4 slots are free.",
    },
    "profile.msg.reset": {
        "fr": "Configuration réinitialisée — vis vide.",
        "en": "Configuration reset — empty screw.",
    },
    "profile.msg.demo_loaded": {
        "fr": "Configuration démo chargée.",
        "en": "Demo configuration loaded.",
    },
    "profile.msg.demo_chaotic": {
        "fr": "Demo chaotic — vérifie l'effet losange sur la zone orange.",
        "en": "Chaotic demo — check the diamond effect on the orange zone.",
    },
    "profile.msg.removed_one": {
        "fr": "1 × {lbl} retiré.",
        "en": "1 × {lbl} removed.",
    },
    "profile.msg.added_one": {
        "fr": "1 × {lbl} ajouté.",
        "en": "1 × {lbl} added.",
    },
    "profile.msg.added_four": {
        "fr": "4 × {lbl} ajoutés.",
        "en": "4 × {lbl} added.",
    },
    "profile.msg.add_impossible": {
        "fr": "Ajout impossible — pas de position libre pour {lbl}.",
        "en": "Cannot add — no free position for {lbl}.",
    },
    "profile.msg.add4_blocked": {
        "fr": "+4 bloqué — capacité ou positions insuffisantes pour 4 × {lbl}.",
        "en": "+4 blocked — insufficient capacity or positions for 4 × {lbl}.",
    },
    # Phase S2-bis — Profile : restes visibles (panneau recos / décision).
    "profile.recos.none": {
        "fr": "Aucune recommandation à afficher.",
        "en": "No recommendation to display.",
    },
    "profile.reco.elements_recommended": {
        "fr": "éléments recommandés", "en": "recommended elements",
    },
    "profile.reco.do_now": {"fr": "À FAIRE MAINTENANT", "en": "DO NOW"},
    "profile.reco.confidence": {"fr": "Confiance", "en": "Confidence"},
    "profile.reco.why_choice": {"fr": "Pourquoi ce choix", "en": "Why this choice"},
    "profile.reco.why_optimal": {
        "fr": "POURQUOI CE CHOIX EST OPTIMAL", "en": "WHY THIS CHOICE IS OPTIMAL",
    },
    "profile.chart.residence_axis": {"fr": "Résidence (s)", "en": "Residence (s)"},
    "profile.conf.high": {"fr": "ÉLEVÉE", "en": "HIGH"},
    "profile.conf.medium": {"fr": "MOYENNE", "en": "MEDIUM"},
    "profile.conf.low": {"fr": "FAIBLE", "en": "LOW"},

    # Phase S2-bis — Settings : toasts d'enregistrement.
    "settings.toast.saved": {
        "fr": "Configuration enregistrée — Supervision mise à jour.",
        "en": "Configuration saved — Supervision updated.",
    },
    "settings.toast.history_saved": {
        "fr": "Historique procédé mis à jour (persistant).",
        "en": "Process history updated (persistent).",
    },
    "settings.toast.duplicate": {
        "fr": "Configuration identique au dernier enregistrement — pas de doublon.",
        "en": "Configuration identical to the last save — no duplicate.",
    },
    "settings.toast.history_error": {
        "fr": "Historique persistant indisponible : {err}",
        "en": "Persistent history unavailable: {err}",
    },

    # Phase S2-bis — Supervision : blocs décision/état + avertissement débit.
    "home.flow_not_computable": {
        "fr": "**Débit réel non calculable : coefficient d'étalonnage feeder à "
              "renseigner.** Les indicateurs dépendant du débit ne sont pas une "
              "vérité procédé tant que l'étalonnage (RPM feeder × g/h/RPM) "
              "n'est pas saisi dans **Profile**. Aucun débit par défaut n'est "
              "utilisé.",
        "en": "**Real flow not computable: feeder calibration coefficient "
              "required.** Flow-dependent indicators are not process truth "
              "until the calibration (feeder RPM × g/h/RPM) is entered in "
              "**Profile**. No default flow is used.",
    },
    "home.rec_config.title": {
        "fr": "CONFIG VIS RECOMMANDÉE", "en": "RECOMMENDED SCREW CONFIG",
    },
    "home.rec_config.elements": {"fr": "éléments", "en": "elements"},
    "home.no_screw_reco": {
        "fr": "Aucune recommandation vis active — ouvrez Profile pour analyser.",
        "en": "No active screw recommendation — open Profile to analyse.",
    },
    "home.why_optimal": {
        "fr": "POURQUOI {n} EST OPTIMAL", "en": "WHY {n} IS OPTIMAL",
    },
    "home.priority_action": {"fr": "ACTION PRIORITAIRE", "en": "PRIORITY ACTION"},
    "home.no_other_alert": {
        "fr": "— aucune autre alerte", "en": "— no other alert",
    },
    "home.main_reco": {"fr": "RECO PRINCIPALE", "en": "MAIN RECO"},
    # Recos opérateur par état SVM (slots fixes — DOM stable).
    "home.reco.STABLE.1.t": {"fr": "Maintenir les consignes thermiques actuelles",
                             "en": "Keep the current thermal setpoints"},
    "home.reco.STABLE.1.d": {"fr": "Aucun ajustement nécessaire — zones 1–8 dans les tolérances.",
                             "en": "No adjustment needed — zones 1–8 within tolerance."},
    "home.reco.STABLE.2.t": {"fr": "Contrôle visuel périodique du film suffit",
                             "en": "Periodic visual film check is sufficient"},
    "home.reco.STABLE.2.d": {"fr": "Fréquence standard — pas d'accélération requise.",
                             "en": "Standard frequency — no acceleration required."},
    "home.reco.STABLE.3.t": {"fr": "Pas d'intervention sur le profil de vis",
                             "en": "No intervention on the screw profile"},
    "home.reco.STABLE.3.d": {"fr": "Régime nominal confirmé par le modèle SVM.",
                             "en": "Nominal regime confirmed by the SVM model."},
    "home.reco.SURVEILLER.1.t": {"fr": "Augmenter la fréquence de contrôle qualité film",
                                 "en": "Increase film quality check frequency"},
    "home.reco.SURVEILLER.1.d": {"fr": "Vérifier épaisseur et aspect toutes les 5 min.",
                                 "en": "Check thickness and appearance every 5 min."},
    "home.reco.SURVEILLER.2.t": {"fr": "Inspecter les zones à std élevé ci-dessous",
                                 "en": "Inspect the high-std zones below"},
    "home.reco.SURVEILLER.2.d": {"fr": "Comparer avec les consignes de régulation en place.",
                                 "en": "Compare with the regulation setpoints in place."},
    "home.reco.SURVEILLER.3.t": {"fr": "Anticiper une correction si la dérive persiste",
                                 "en": "Anticipate a correction if the drift persists"},
    "home.reco.SURVEILLER.3.d": {"fr": "Attendre 2 cycles avant d'intervenir.",
                                 "en": "Wait 2 cycles before intervening."},
    "home.reco.SURVEILLER.4.t": {"fr": "Ne pas modifier la vitesse vis sans confirmation",
                                 "en": "Do not change screw speed without confirmation"},
    "home.reco.SURVEILLER.4.d": {"fr": "Risque d'amplification de la dérive thermique.",
                                 "en": "Risk of amplifying the thermal drift."},
    "home.reco.CRITIQUE.1.t": {"fr": "Réduire la vitesse de rotation vis de 10–15 %",
                               "en": "Reduce screw rotation speed by 10–15%"},
    "home.reco.CRITIQUE.1.d": {"fr": "Action prioritaire — effet mesurable en moins de 60 s.",
                               "en": "Priority action — measurable effect within 60 s."},
    "home.reco.CRITIQUE.2.t": {"fr": "Vérifier consigne et régulation des zones instables",
                               "en": "Check setpoint and regulation of unstable zones"},
    "home.reco.CRITIQUE.2.d": {"fr": "Comparer consigne vs mesure en temps réel.",
                               "en": "Compare setpoint vs measurement in real time."},
    "home.reco.CRITIQUE.3.t": {"fr": "Contrôler le film : épaisseur, aspect, homogénéité",
                               "en": "Check the film: thickness, appearance, homogeneity"},
    "home.reco.CRITIQUE.3.d": {"fr": "Écarter les bobines produites durant l'instabilité.",
                               "en": "Set aside reels produced during the instability."},
    "home.reco.CRITIQUE.4.t": {"fr": "Arrêt procédé si instabilité persiste > 2 min",
                               "en": "Stop the process if instability persists > 2 min"},
    "home.reco.CRITIQUE.4.d": {"fr": "Protocole sécurité qualité SSB — non négociable.",
                               "en": "SSB quality safety protocol — non-negotiable."},
    # États procédé : recommandations opérateur par état (5 slots fixes).
    "home.expl.STABLE": {
        "fr": "Toutes les zones thermiques sont dans les tolérances. "
              "Zone la plus variable : **{sensor}** (σ = {std} °C) — sous le "
              "seuil critique de 1,5 °C. Procédé en régime nominal.",
        "en": "All thermal zones are within tolerance. Most variable zone: "
              "**{sensor}** (σ = {std} °C) — below the 1.5 °C critical "
              "threshold. Process in nominal regime.",
    },
    "home.expl.SURVEILLER": {
        "fr": "**{sensor}** présente la variabilité la plus élevée "
              "(σ = {std} °C). Score {score}/100 sous le seuil {th}. Dérive "
              "thermique en cours — surveillance renforcée recommandée.",
        "en": "**{sensor}** shows the highest variability (σ = {std} °C). "
              "Score {score}/100 below the {th} threshold. Thermal drift in "
              "progress — heightened monitoring recommended.",
    },
    "home.expl.CRITIQUE": {
        "fr": "**{sensor}** est la zone la plus instable (σ = {std} °C, "
              "seuil = 1,5 °C). Score {score}/100 critique. Risque de "
              "production non conforme si non corrigé immédiatement.",
        "en": "**{sensor}** is the most unstable zone (σ = {std} °C, "
              "threshold = 1.5 °C). Critical score {score}/100. Risk of "
              "non-conforming production if not corrected immediately.",
    },

    # Phase S2-bis — Analyse run : bandeau + avertissements DEMO.
    "analyse.demo_banner": {
        "fr": "Analyse d'un run du <b>dataset ML d'essai (avril 2026)</b> — "
              "durée, scores et profils sont des <b>données de "
              "démonstration</b>, <b>non un run opérateur live</b>.",
        "en": "Analysis of a run from the <b>ML trial dataset (April 2026)</b> "
              "— duration, scores and profiles are <b>demonstration data</b>, "
              "<b>not a live operator run</b>.",
    },
    "analyse.demo_duration_help": {
        "fr": "DEMO — durée du run d'essai (run_duration_min du dataset ML), "
              "pas un temps procédé opérateur validé.",
        "en": "DEMO — trial run duration (run_duration_min from the ML "
              "dataset), not a validated operator process time.",
    },
    "analyse.demo_caption": {
        "fr": "⚠️ DEMO — durée, % stable/critique et scores ci-dessus sont des "
              "métadonnées du run d'essai (dataset ML), non un run opérateur "
              "live.",
        "en": "⚠️ DEMO — duration, % stable/critical and scores above are "
              "trial-run metadata (ML dataset), not a live operator run.",
    },

    # Phase S2-bis — Historique : chrome section principale.
    "page.historique.title": {
        "fr": "Historique des procédés — Rondol", "en": "Process history — Rondol",
    },
    "historique.banner.left": {
        "fr": "● Rondol · Historique des procédés", "en": "● Rondol · Process history",
    },
    "historique.banner.right": {
        "fr": "Configurations enregistrées (persistant)",
        "en": "Saved configurations (persistent)",
    },
    "historique.header": {"fr": "Historique des procédés", "en": "Process history"},
    "historique.header.caption": {
        "fr": "Configurations validées (« Enregistrer » dans Paramètres IA & "
              "feeders), conservées sur disque et restaurées au redémarrage. "
              "Lecture seule — KPIs moteur figés au moment de "
              "l'enregistrement, aucune valeur recalculée.",
        "en": "Validated configurations (“Save” in AI & feeders settings), "
              "stored on disk and restored at restart. Read-only — engine "
              "KPIs frozen at save time, no value recomputed.",
    },
    "historique.corrupt": {
        "fr": "Fichier d'historique illisible — affichage ignoré pour cette "
              "lecture. Les prochains enregistrements repartiront sur une "
              "base saine.",
        "en": "Unreadable history file — display skipped for this read. "
              "Future saves will restart on a clean basis.",
    },
    "historique.empty": {
        "fr": "**Aucun historique procédé enregistré.** L'historique se "
              "remplira après l'enregistrement d'une configuration (page "
              "**Paramètres IA & feeders → Enregistrer**) et sera conservé "
              "même après redémarrage de l'application.",
        "en": "**No saved process history.** History will fill up after a "
              "configuration is saved (**AI & feeders settings → Save**) and "
              "is kept across application restarts.",
    },
    "historique.m.count": {"fr": "Procédés enregistrés", "en": "Saved runs"},
    "historique.m.last": {"fr": "Dernier enregistrement", "en": "Last save"},
    "historique.m.active": {"fr": "Procédé actif", "en": "Active run"},
    "historique.f.status": {"fr": "Statut", "en": "Status"},
    "historique.f.source": {"fr": "Source", "en": "Source"},
    "historique.f.date": {"fr": "Date", "en": "Date"},
    "historique.f.all_m": {"fr": "Tous", "en": "All"},
    "historique.f.all_f": {"fr": "Toutes", "en": "All"},
    "historique.status.active": {"fr": "Actif", "en": "Active"},
    "historique.status.archived": {"fr": "Archivé", "en": "Archived"},
    "historique.source.manual": {"fr": "Manuel", "en": "Manual"},
    "historique.source.demo": {"fr": "Démonstration", "en": "Demonstration"},
    "historique.no_filter_match": {
        "fr": "Aucun procédé ne correspond aux filtres sélectionnés.",
        "en": "No run matches the selected filters.",
    },
    "historique.detail_select": {
        "fr": "Voir le détail d'un procédé", "en": "View run detail",
    },
    "historique.no_label": {"fr": "(sans libellé)", "en": "(no label)"},
    "historique.skipped_note": {
        "fr": "Note : {n} entrée(s) illisible(s) ignorée(s).",
        "en": "Note: {n} unreadable record(s) skipped.",
    },
    "historique.col.status": {"fr": "Statut", "en": "Status"},
    "historique.col.datetime": {"fr": "Date / heure", "en": "Date / time"},
    "historique.col.label": {"fr": "Label", "en": "Label"},
    "historique.col.source": {"fr": "Source", "en": "Source"},
    "historique.col.rpm": {"fr": "Vis (tr/min)", "en": "Screw (rpm)"},
    "historique.col.flow": {"fr": "Débit princ. (g/min)", "en": "Main flow (g/min)"},
    "historique.col.material": {"fr": "Matière", "en": "Material"},
    "historique.col.die_zones": {"fr": "Zones die", "en": "Die zones"},
    "historique.col.elements": {"fr": "Éléments", "en": "Elements"},
    "historique.col.torque": {"fr": "Couple (N·m)", "en": "Torque (N·m)"},
    "historique.col.sme": {"fr": "SME (kWh/kg)", "en": "SME (kWh/kg)"},
    "historique.col.residence": {"fr": "Résidence (s)", "en": "Residence (s)"},
    "historique.col.fill_mean": {"fr": "Fill moy.", "en": "Mean fill"},
    "historique.col.fill_peak": {"fr": "Fill crête", "en": "Peak fill"},
    "historique.col.shear": {"fr": "Cisaill. max (1/s)", "en": "Max shear (1/s)"},
    "historique.ml.expander": {
        "fr": "Essais d'entraînement ML — données historiques modèle",
        "en": "ML training trials — model history data",
    },
    "historique.footer": {
        "fr": "Rondol Industrie · Historique des procédés (persistant) · Prototype",
        "en": "Rondol Industrie · Process history (persistent) · Prototype",
    },
    # Phase 6 — Étalonnage feeders (Settings expander + bloc Profile sidebar)
    "settings.expander.feedcal": {
        "fr": "⚙️ Étalonnage feeders — RPM × coefficient g/h/RPM → débit réel",
        "en": "⚙️ Feeder calibration — RPM × g/h/RPM coefficient → real flow rate",
    },
    "feedcal.caption": {
        "fr": "Chaque feeder : RPM × coefficient g/h/RPM → débit propre. "
              "Coefficient 0 = non étalonné → débit non calculable (jamais inventé).",
        "en": "Each feeder: RPM × g/h/RPM coefficient → own flow rate. "
              "Coefficient 0 = uncalibrated → flow not computable (never guessed).",
    },
    "feedcal.active": {"fr": "actif", "en": "active"},
    "feedcal.disabled": {"fr": "désactivé", "en": "disabled"},
    "feedcal.rpm_label": {"fr": "RPM #{fid}", "en": "RPM #{fid}"},
    "feedcal.coeff_label": {
        "fr": "Coefficient g/h/RPM #{fid}",
        "en": "Coefficient g/h/RPM #{fid}",
    },
    "feedcal.line_ok": {
        "fr": "#{fid} {lbl} : **{gh} g/h** = {gmin} g/min · statut OK",
        "en": "#{fid} {lbl}: **{gh} g/h** = {gmin} g/min · status OK",
    },
    "feedcal.line_missing": {
        "fr": "#{fid} {lbl} : débit **Non calculable** · statut Non étalonné",
        "en": "#{fid} {lbl}: flow **Not computable** · status Not calibrated",
    },
    "feedcal.total_ok": {
        "fr": "**Débit total : {gh} g/h** ({gmin} g/min)",
        "en": "**Total flow rate: {gh} g/h** ({gmin} g/min)",
    },
    "feedcal.total_incomplete": {
        "fr": "⚠️ total **incomplet** : un feeder actif n'est pas étalonné "
              "(exclu du total).",
        "en": "⚠️ total **incomplete**: an active feeder is not calibrated "
              "(excluded from total).",
    },
    "feedcal.total_none": {
        "fr": "Débit total **non calculable** : aucun feeder étalonné. "
              "Renseignez RPM + coefficient g/h/RPM pour au moins un feeder actif.",
        "en": "Total flow **not computable**: no calibrated feeder. Enter "
              "RPM + g/h/RPM coefficient for at least one active feeder.",
    },
    # Bloc Profile sidebar (feeder #1 seul)
    "feedcal.profile_caption": {
        "fr": "⚙️ Étalonnage feeder — **étalonnage externe requis**",
        "en": "⚙️ Feeder calibration — **external calibration required**",
    },
    "feedcal.rpm_simple": {"fr": "RPM feeder", "en": "Feeder RPM"},
    "feedcal.coeff_simple": {
        "fr": "Coefficient (g/h par RPM)",
        "en": "Coefficient (g/h per RPM)",
    },
    "feedcal.coeff_help": {
        "fr": "À mesurer par étalonnage externe du feeder. Exemple manager "
              "2026-06-09 : {coeff} g/h/RPM (30 RPM → 510 g/h = 8,5 g/min). "
              "Limite haute machine : {max_gh} g/h. 0 = non renseigné → débit "
              "réel non calculable.",
        "en": "Measured by external feeder calibration. Manager example "
              "2026-06-09: {coeff} g/h/RPM (30 RPM → 510 g/h = 8.5 g/min). "
              "Machine upper limit: {max_gh} g/h. 0 = unset → real flow not "
              "computable.",
    },
    "feedcal.not_calibrated": {
        "fr": "Débit réel non calculable — coefficient feeder à renseigner.",
        "en": "Real flow not computable — feeder coefficient required.",
    },
    "feedcal.clamped": {
        "fr": "Débit demandé {req} g/h > max machine {max_gh} g/h : "
              "**plafonné à {eff} g/h** ({eff_min} g/min) pour le calcul.",
        "en": "Requested flow {req} g/h > machine max {max_gh} g/h: "
              "**capped at {eff} g/h** ({eff_min} g/min) for the computation.",
    },
    "feedcal.ok": {
        "fr": "✓ {rpm} RPM × {coeff} g/h/RPM = {req} g/h = {eff_min} g/min "
              "({eff_s} g/s)",
        "en": "✓ {rpm} RPM × {coeff} g/h/RPM = {req} g/h = {eff_min} g/min "
              "({eff_s} g/s)",
    },
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
    "settings.adv.sf_disabled": {"fr": "Désactivé", "en": "Disabled"},
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

    # ===================================================================
    # RENDU VIS / LECTURE IA (screw_render) — stabilisation globale 2026-06-10
    # ===================================================================
    "common.elements_unit": {"fr": "éléments", "en": "elements"},
    "common.extruder": {"fr": "Extrudeuse 10,5 mm", "en": "10.5 mm extruder"},
    "common.impact": {"fr": "Impact", "en": "Impact"},
    "common.action": {"fr": "Action", "en": "Action"},
    # Régimes procédé.
    "sr.regime.saturated": {"fr": "Régime saturé", "en": "Saturated regime"},
    "sr.regime.saturated.short": {"fr": "saturé", "en": "saturated"},
    "sr.regime.saturated.sum": {
        "fr": "Fill Factor {ff} % — vis proche de saturation, risque surcouple "
              "et chauffe par friction. Privilégier 40 ou réduire le débit.",
        "en": "Fill factor {ff}% — screw close to saturation, risk of "
              "overtorque and friction heating. Prefer 40 or reduce the flow."},
    "sr.regime.starved": {"fr": "Régime sous-alimenté", "en": "Starved regime"},
    "sr.regime.starved.short": {"fr": "sous-alimenté", "en": "starved"},
    "sr.regime.starved.sum": {
        "fr": "Fill Factor {ff} % — vis quasi vide, mélange peu efficace. "
              "Augmenter le débit feeder ou réduire la vitesse vis.",
        "en": "Fill factor {ff}% — screw nearly empty, mixing inefficient. "
              "Increase feeder flow or reduce screw speed."},
    "sr.regime.fast": {"fr": "Régime rapide", "en": "Fast regime"},
    "sr.regime.fast.short": {"fr": "rapide", "en": "fast"},
    "sr.regime.fast.sum": {
        "fr": "À {rpm} rpm × {feed} g/min — transit rapide, résidence courte. "
              "L'agent biaisera vers une vis plus courte (25) si le mélange suffit.",
        "en": "At {rpm} rpm × {feed} g/min — fast transit, short residence. "
              "The agent will bias toward a shorter screw (25) if mixing suffices."},
    "sr.regime.slow": {"fr": "Régime lent", "en": "Slow regime"},
    "sr.regime.slow.short": {"fr": "lent", "en": "slow"},
    "sr.regime.slow.sum": {
        "fr": "À {rpm} rpm × {feed} g/min — résidence longue, cumul thermique "
              "possible. Surveiller dégradation liant si beaucoup de kneading.",
        "en": "At {rpm} rpm × {feed} g/min — long residence, possible thermal "
              "build-up. Watch binder degradation with heavy kneading."},
    "sr.regime.moderate": {"fr": "Régime modéré", "en": "Moderate regime"},
    "sr.regime.moderate.short": {"fr": "modéré", "en": "moderate"},
    "sr.regime.moderate.sum": {
        "fr": "À {rpm} rpm × {feed} g/min × ρ={dens} g/cm³ — régime nominal, "
              "l'agent peut arbitrer librement entre 25/30/40.",
        "en": "At {rpm} rpm × {feed} g/min × ρ={dens} g/cm³ — nominal regime, "
              "the agent can freely arbitrate between 25/30/40."},
    # Archétypes de profil.
    "sr.arch.empty": {"fr": "Vis vide", "en": "Empty screw"},
    "sr.arch.empty.short": {"fr": "vide", "en": "empty"},
    "sr.arch.empty.sum": {
        "fr": "Aucun élément placé après le main feeder. Configurez la vis "
              "dans Profile pour activer l'analyse procédé.",
        "en": "No element placed after the main feeder. Configure the screw "
              "in Profile to enable the process analysis."},
    "sr.arch.empty.risk": {"fr": "aucune analyse possible", "en": "no analysis possible"},
    "sr.arch.minimal": {"fr": "Profil minimaliste", "en": "Minimalist profile"},
    "sr.arch.minimal.short": {"fr": "minimaliste", "en": "minimalist"},
    "sr.arch.minimal.sum": {
        "fr": "{n} éléments seulement — vis trop courte pour homogénéiser une "
              "formulation SSB (cible 18-30 éléments). Densifier la "
              "configuration avant tout essai pilote.",
        "en": "Only {n} elements — screw too short to homogenise an SSB "
              "formulation (target 18-30 elements). Densify the configuration "
              "before any pilot trial."},
    "sr.arch.minimal.risk1": {"fr": "mélange insuffisant", "en": "insufficient mixing"},
    "sr.arch.minimal.risk2": {"fr": "résidence trop courte", "en": "residence too short"},
    "sr.arch.imbalanced": {"fr": "Profil déséquilibré spatial", "en": "Spatially imbalanced profile"},
    "sr.arch.imbalanced.short": {"fr": "déséquilibré", "en": "imbalanced"},
    "sr.arch.imbalanced.sum": {
        "fr": "{nmax}/{n} éléments concentrés dans Z{z} ({pct} %). La vis "
              "fonctionne comme une vis courte avec tube vide en amont/aval — "
              "capacité utile gaspillée.{bulk}",
        "en": "{nmax}/{n} elements concentrated in Z{z} ({pct}%). The screw "
              "behaves like a short screw with an empty barrel up/downstream — "
              "useful capacity wasted.{bulk}"},
    "sr.arch.imbalanced.risk1": {"fr": "longueur sous-utilisée", "en": "under-used length"},
    "sr.arch.imbalanced.risk2": {"fr": "pic couple local", "en": "local torque peak"},
    "sr.arch.chaotic": {"fr": "Profil chaotique", "en": "Chaotic profile"},
    "sr.arch.chaotic.short": {"fr": "chaotique", "en": "chaotic"},
    "sr.arch.chaotic.sum": {
        "fr": "{n} éléments chaotiques ({pct} %) — mélange à effet "
              "bidirectionnel (losange) dominant. Adapté aux formulations SSB "
              "nécessitant une dispersion fine + distribution simultanée, mais "
              "coûteux en couple.{bulk}",
        "en": "{n} chaotic elements ({pct}%) — bidirectional (diamond) mixing "
              "dominant. Suited to SSB formulations needing fine dispersion + "
              "simultaneous distribution, but torque-expensive.{bulk}"},
    "sr.arch.chaotic.risk1": {"fr": "couple moteur élevé", "en": "high motor torque"},
    "sr.arch.chaotic.risk2": {"fr": "résidence accrue", "en": "increased residence"},
    "sr.arch.dispersive": {"fr": "Profil dispersif intense", "en": "Intense dispersive profile"},
    "sr.arch.dispersive.short": {"fr": "dispersif", "en": "dispersive"},
    "sr.arch.dispersive.sum": {
        "fr": "{n} mélangeurs dispersifs/chaotiques ({pct} % du profil). "
              "Cisaillement cumulé important → risque dégradation thermique "
              "liant SSB (PVDF > 200 °C, PEO > 180 °C). Intercaler du "
              "convoyage de refroidissement entre les blocs.{bulk}",
        "en": "{n} dispersive/chaotic mixers ({pct}% of the profile). High "
              "cumulated shear → risk of thermal degradation of the SSB binder "
              "(PVDF > 200 °C, PEO > 180 °C). Interleave cooling conveying "
              "between blocks.{bulk}"},
    "sr.arch.dispersive.risk1": {"fr": "dégradation liant", "en": "binder degradation"},
    "sr.arch.dispersive.risk2": {"fr": "surcouple", "en": "overtorque"},
    "sr.arch.dispersive.risk3": {"fr": "chauffe locale", "en": "local heating"},
    "sr.arch.convective": {"fr": "Profil convectif dominant", "en": "Conveying-dominant profile"},
    "sr.arch.convective.short": {"fr": "convectif", "en": "conveying"},
    "sr.arch.convective.sum": {
        "fr": "{n} éléments de transport ({pct} %) pour seulement {nmix} "
              "mélangeur(s). La matière transite trop vite, peu cisaillée — "
              "homogénéité insuffisante pour SSB.{bulk}",
        "en": "{n} transport elements ({pct}%) for only {nmix} mixer(s). "
              "Material transits too fast with little shear — homogeneity "
              "insufficient for SSB.{bulk}"},
    "sr.arch.convective.risk1": {"fr": "homogénéité insuffisante", "en": "insufficient homogeneity"},
    "sr.arch.convective.risk2": {"fr": "dispersion liant médiocre", "en": "poor binder dispersion"},
    "sr.arch.distributive": {"fr": "Profil distributif", "en": "Distributive profile"},
    "sr.arch.distributive.short": {"fr": "distributif", "en": "distributive"},
    "sr.arch.distributive.sum": {
        "fr": "{n} éléments distributifs/chaotiques ({pct} %). Profil orienté "
              "homogénéisation globale plutôt que cisaillement local — adapté "
              "aux mélanges déjà pré-dispersés.{bulk}",
        "en": "{n} distributive/chaotic elements ({pct}%). Profile oriented "
              "toward global homogenisation rather than local shear — suited "
              "to already pre-dispersed blends.{bulk}"},
    "sr.arch.distributive.risk1": {"fr": "dispersion locale faible", "en": "weak local dispersion"},
    "sr.arch.underused": {"fr": "Profil sous-utilisé", "en": "Under-used profile"},
    "sr.arch.underused.short": {"fr": "sous-utilisé", "en": "under-used"},
    "sr.arch.underused.sum": {
        "fr": "{n} zones procédé vides sur 7 — la vis effective est plus "
              "courte que prévu. Étendre la configuration sur l'ensemble "
              "Z1..Z7 pour utiliser tout le volume utile.{bulk}",
        "en": "{n} empty process zones out of 7 — the effective screw is "
              "shorter than intended. Spread the configuration across Z1..Z7 "
              "to use the full working volume.{bulk}"},
    "sr.arch.underused.risk1": {"fr": "longueur effective courte", "en": "short effective length"},
    "sr.arch.underused.risk2": {"fr": "résidence variable", "en": "variable residence"},
    "sr.arch.balanced": {"fr": "Profil équilibré", "en": "Balanced profile"},
    "sr.arch.balanced.short": {"fr": "équilibré", "en": "balanced"},
    "sr.arch.balanced.sum": {
        "fr": "Convoyage : {nconv} · Mélange : {nmix} · Rétention : {nrev} · "
              "Fill {ff} %. Profil cohérent pour HME / SSB dry — passer à "
              "l'essai pilote pour valider l'homogénéité.{bulk}",
        "en": "Conveying: {nconv} · Mixing: {nmix} · Retention: {nrev} · "
              "Fill {ff}%. Profile consistent for HME / dry SSB — move to the "
              "pilot trial to validate homogeneity.{bulk}"},
    "sr.bulk_note": {
        "fr": " Densité ρ={dens} g/cm³ → formulation chargée (céramique "
              "active), vigilance sur l'abrasion des malaxeurs.",
        "en": " Density ρ={dens} g/cm³ → loaded formulation (active ceramic), "
              "watch mixer abrasion."},
    # Vis vide — reco / décision / check systémique.
    "sr.empty.rec_impact": {
        "fr": "Aucune analyse procédé possible", "en": "No process analysis possible"},
    "sr.empty.rec_action": {
        "fr": "Ajoutez des éléments via +1 / +4, ou cliquez « Configuration "
              "démo » dans la barre latérale pour démarrer l'analyse.",
        "en": "Add elements with +1 / +4, or click “Demo configuration” in "
              "the sidebar to start the analysis."},
    "sr.empty.rec_evidence": {"fr": "0 / 39 éléments", "en": "0 / 39 elements"},
    "sr.empty.count_summary": {"fr": "Aucun élément placé", "en": "No element placed"},
    "sr.empty.count_reasoning": {
        "fr": "Aucun élément placé après le feeder : pas de signal métier "
              "exploitable. Par défaut 30 éléments.",
        "en": "No element placed after the feeder: no usable process signal. "
              "Defaulting to 30 elements."},
    "sr.empty.count_rationale": {
        "fr": "Vis vide — placez quelques éléments puis relancez l'analyse "
              "pour une recommandation fondée.",
        "en": "Empty screw — place a few elements then rerun the analysis "
              "for a grounded recommendation."},
    "sr.empty.count_tagline": {"fr": "configuration vide", "en": "empty configuration"},
    "sr.empty.decision": {
        "fr": "Configurer la vis avant analyse : placez quelques éléments "
              "puis relancez l'agent.",
        "en": "Configure the screw before analysis: place a few elements "
              "then rerun the agent.",
    },
    "sr.empty.summary_decision": {
        "fr": "Configurer la vis avant de lancer l'analyse.",
        "en": "Configure the screw before running the analysis.",
    },
    "sr.empty.summary_why": {
        "fr": "Aucun élément n'est posé : l'agent ne peut rien évaluer.",
        "en": "No element is placed: the agent has nothing to assess.",
    },
    "sr.empty.summary_action": {
        "fr": "Placer quelques éléments dans le profil puis relancer l'analyse.",
        "en": "Place a few elements in the profile then rerun the analysis.",
    },
    "sr.empty.systemic_check": {
        "fr": "Vis vide — aucune cohérence à évaluer. Configurer la vis puis "
              "relancer l'analyse.",
        "en": "Empty screw — no consistency to assess. Configure the screw "
              "then rerun the analysis."},
    # Labels de blocs décision / systémique.
    "sr.lbl.decision_agent": {"fr": "DÉCISION AGENT", "en": "AGENT DECISION"},
    "sr.lbl.confidence": {"fr": "Confiance", "en": "Confidence"},
    "sr.lbl.next_step": {"fr": "PROCHAINE ÉTAPE", "en": "NEXT STEP"},
    "sr.lbl.operator_read": {"fr": "LECTURE OPÉRATEUR — 3 SECONDES",
                             "en": "OPERATOR READ — 3 SECONDS"},
    "sr.lbl.row_decision": {"fr": "Décision", "en": "Decision"},
    "sr.lbl.row_why": {"fr": "Pourquoi", "en": "Why"},
    "sr.lbl.row_action": {"fr": "Action", "en": "Action"},
    "sr.lbl.global_reasoning": {"fr": "Raisonnement global procédé",
                                "en": "Global process reasoning"},
    "sr.lbl.tradeoffs": {"fr": "TRADE-OFFS — CE QU'ON GAGNE / CE QU'ON PERD",
                         "en": "TRADE-OFFS — WHAT WE GAIN / WHAT WE LOSE"},
    "sr.lbl.synthesis": {"fr": "SYNTHÈSE FINALE — ", "en": "FINAL SYNTHESIS — "},
    "moteur.why_ff": {"fr": "Pourquoi FF = {ff} % ?", "en": "Why is FF = {ff}%?"},
    "app_mode.toggle": {"fr": "Mode démonstration", "en": "Demonstration mode"},
    "app_mode.toggle_help": {
        "fr": "OFF = mode client : seules les données réellement saisies sont "
              "affichées (sinon « Non renseigné »). ON = données fictives de "
              "démonstration, marquées DEMO.",
        "en": "OFF = client mode: only data actually entered is shown "
              "(otherwise “Not entered”). ON = fictitious demonstration data, "
              "marked DEMO.",
    },
    "sr.lbl.fill_regime": {"fr": "Régime de remplissage", "en": "Fill regime"},
    "sr.lbl.process_regime": {"fr": "Régime procédé", "en": "Process regime"},
    "sr.decision.high": {"fr": "PRODUCTION POSSIBLE", "en": "PRODUCTION POSSIBLE"},
    "sr.decision.medium": {"fr": "TEST PILOTE RECOMMANDÉ", "en": "PILOT TEST RECOMMENDED"},
    "sr.decision.low": {"fr": "CONFIGURATION INSTABLE", "en": "UNSTABLE CONFIGURATION"},

    # ===================================================================
    # COMMON — shared strings
    # ===================================================================
    "common.not_entered": {"fr": "Non renseigné", "en": "Not entered"},
    "common.not_computable": {"fr": "Non calculable", "en": "Not computable"},
    "common.yes": {"fr": "oui", "en": "yes"},
    "common.no": {"fr": "non", "en": "no"},
    "common.not_available": {"fr": "Non disponible", "en": "Not available"},
    "common.clamped": {"fr": "plafonné", "en": "capped"},

    # ===================================================================
    # ELEMENT ROLES (screw_render)
    # ===================================================================
    "role.1": {"fr": "convoyage", "en": "conveying"},
    "role.2": {"fr": "convoyage (½)", "en": "conveying (½)"},
    "role.3": {"fr": "convoyage compact", "en": "compact conveying"},
    "role.4": {"fr": "mélange dispersif", "en": "dispersive mixing"},
    "role.5": {"fr": "mélange doux", "en": "gentle mixing"},
    "role.6": {"fr": "convoyage rapide", "en": "fast conveying"},
    "role.7": {"fr": "mélange dispersif", "en": "dispersive mixing"},
    "role.8": {"fr": "mélange dispersif", "en": "dispersive mixing"},
    "role.9": {"fr": "rétention / contre-pression", "en": "retention / back-pressure"},
    "role.10": {"fr": "mélange chaotique", "en": "chaotic mixing"},
    "role.11": {"fr": "mélange distributif", "en": "distributive mixing"},
    "role.12": {"fr": "mélange distributif", "en": "distributive mixing"},
    "role.13": {"fr": "décharge", "en": "discharge"},
    # Tip status labels
    "tip.valid": {"fr": "pointe verrouillée", "en": "tip locked"},
    "tip.missing": {"fr": "pointe absente", "en": "tip missing"},
    "tip.deduplicated": {"fr": "pointe restaurée", "en": "tip restored"},

    # ===================================================================
    # PAGE — Moteur Procédé
    # ===================================================================
    "moteur.page_title": {"fr": "Moteur Procédé — Rondol", "en": "Process Engine — Rondol"},
    "moteur.banner.left": {"fr": "● Rondol · Moteur Procédé", "en": "● Rondol · Process Engine"},
    "moteur.banner.right": {
        "fr": "Couche engine — couple local · SME · état machine",
        "en": "Engine layer — local torque · SME · machine state"},
    "moteur.header": {"fr": "Moteur Procédé", "en": "Process Engine"},
    "moteur.caption": {
        "fr": "Résultats calculés par la couche moteur (graph d'extrusion + couple E4 + SME) "
              "à partir de la configuration et des paramètres saisis dans Profile / Settings. "
              "Page en lecture seule.",
        "en": "Results computed by the engine layer (extrusion graph + E4 torque + SME) "
              "from the configuration and parameters entered in Profile / Settings. "
              "Read-only page."},
    "moteur.no_profile.info": {
        "fr": "**Aucun profil procédé configuré.** Les valeurs affichées resteraient "
              "nulles tant qu'un profil de vis n'est pas chargé.\n\n"
              "→ Configurez un profil dans la page **Profile**, ou chargez ci-dessous un "
              "**profil de démonstration** (configuration nominale, non calibrée "
              "industriellement) pour visualiser la page.",
        "en": "**No process profile configured.** The displayed values would remain "
              "zero until a screw profile is loaded.\n\n"
              "→ Configure a profile in the **Profile** page, or load a "
              "**demonstration profile** below (nominal configuration, not industrially "
              "calibrated) to see the page."},
    "moteur.no_profile.btn": {
        "fr": "▶  Charger un profil de démonstration",
        "en": "▶  Load a demonstration profile"},
    "moteur.no_profile.footer": {
        "fr": "Rondol Industrie · Couche moteur procédé (engine) · Prototype",
        "en": "Rondol Industrie · Process engine layer · Prototype"},
    "moteur.demo.warning": {
        "fr": "**⚙️ Profil de DÉMONSTRATION chargé.** Configuration nominale "
              "(convoyage → malaxages → convoyage), **non calibrée industriellement** — "
              "destinée à illustrer la page, pas à représenter un run réel.",
        "en": "**⚙️ DEMONSTRATION profile loaded.** Nominal configuration "
              "(conveying → kneading → conveying), **not industrially calibrated** — "
              "intended to illustrate the page, not to represent an actual run."},
    "moteur.demo.unload": {"fr": "✕  Décharger", "en": "✕  Unload"},
    "moteur.proto.banner": {
        "fr": "Valeurs <b>nominales, non calibrées industriellement</b> — à "
              "interpréter en tendance, pas comme une vérité procédé finale. "
              "Détails dans « Hypothèses » en bas de page.",
        "en": "Values are <b>nominal, not industrially calibrated</b> — to be "
              "interpreted as trends, not as final process truth. "
              'Details in “Assumptions” at the bottom of the page.'},
    "moteur.flow_warning": {
        "fr": "**Débit réel non calculable : coefficient d'étalonnage feeder à "
              "renseigner.** Les indicateurs dépendant du débit (couple, SME, "
              "résidence, remplissage, débit massique, débit sortie) sont affichés "
              "« Non calculable » — aucun débit par défaut n'est inventé. Renseignez "
              "RPM feeder + coefficient g/h/RPM dans **Profile**.",
        "en": "**Real flow not computable: feeder calibration coefficient "
              "required.** Flow-dependent indicators (torque, SME, residence, "
              'fill, mass flow, output flow) display "Not computable" — no default '
              "flow is guessed. Enter feeder RPM + g/h/RPM coefficient in **Profile**."},
    "moteur.sec.kpis": {"fr": "Indicateurs principaux", "en": "Key indicators"},
    "moteur.sec.kpis_sub": {
        "fr": "valeurs estimées · modèle nominal (non calibré)",
        "en": "estimated values · nominal model (uncalibrated)"},
    "moteur.kpi.torque": {"fr": "Couple total", "en": "Total torque"},
    "moteur.kpi.torque_help": {
        "fr": "Estimé (modèle E4) : M = η·γ̇²·V_rempli / (2π·N), sommé sur la vis. "
              "Confiance : nominale (presets matière non calibrés).",
        "en": "Estimated (E4 model): M = η·γ̇²·V_filled / (2π·N), summed over the screw. "
              "Confidence: nominal (material presets uncalibrated)."},
    "moteur.kpi.sme": {"fr": "SME totale", "en": "Total SME"},
    "moteur.kpi.sme_help": {
        "fr": "Énergie mécanique spécifique estimée : P_dissipée / débit massique, "
              "avec P = 2π·N·couple. Confiance : nominale.",
        "en": "Estimated specific mechanical energy: P_dissipated / mass flow, "
              "with P = 2π·N·torque. Confidence: nominal."},
    "moteur.kpi.residence": {"fr": "Résidence totale", "en": "Total residence"},
    "moteur.kpi.residence_help": {
        "fr": "Temps de séjour moyen estimé (volume vis rempli / débit). Indicatif.",
        "en": "Estimated mean dwell time (filled screw volume / flow). Indicative."},
    "moteur.kpi.fill": {"fr": "Remplissage moyen", "en": "Mean fill"},
    "moteur.kpi.fill_help": {
        "fr": "Taux de remplissage moyen des positions de vis (fill factor calculé).",
        "en": "Mean fill factor of screw positions (computed fill factor)."},
    "moteur.kpi.shear": {"fr": "Cisaillement max", "en": "Max shear"},
    "moteur.kpi.shear_help": {
        "fr": "Taux de cisaillement maximal estimé (rpm × géométrie, indépendant du débit).",
        "en": "Estimated max shear rate (rpm × geometry, independent of flow)."},
    "moteur.sec.machine": {"fr": "État machine / graph", "en": "Machine state / graph"},
    "moteur.kpi.power": {"fr": "Puissance dissipée", "en": "Dissipated power"},
    "moteur.kpi.mass_flow": {"fr": "Débit massique", "en": "Mass flow"},
    "moteur.kpi.output_flow": {"fr": "Débit sortie (pointe)", "en": "Output flow (tip)"},
    "moteur.kpi.peak_fill": {"fr": "Remplissage crête", "en": "Peak fill"},
    "moteur.chip.screw_speed": {"fr": "Vitesse vis", "en": "Screw speed"},
    "moteur.chip.overflow_main": {"fr": "Overflow main", "en": "Overflow main"},
    "moteur.chip.overflow_side": {"fr": "Overflow side", "en": "Overflow side"},
    "moteur.chip.rpm_unit": {"fr": "tr/min", "en": "rpm"},
    "moteur.sec.fill_eval": {"fr": "Évaluation du remplissage", "en": "Fill assessment"},
    "moteur.sec.fill_eval_sub": {
        "fr": "indicative — lecture du fill_factor calculé",
        "en": "indicative — reading from computed fill_factor"},
    "moteur.fill.not_computable": {
        "fr": "Remplissage **non calculable** — coefficient d'étalonnage feeder à "
              "renseigner (le fill factor dépend du débit réel).",
        "en": "Fill **not computable** — feeder calibration coefficient required "
              "(the fill factor depends on the actual flow)."},
    "moteur.fill.eval_footer": {
        "fr": "*Évaluation indicative, basée sur le fill_factor calculé "
              "(moyen {avg} %, crête {peak} %) — à confirmer sur essai réel.*",
        "en": "*Indicative assessment, based on the computed fill_factor "
              "(mean {avg}%, peak {peak}%) — to be confirmed on actual trial.*"},
    "moteur.sec.equations": {"fr": "Équations à venir", "en": "Upcoming equations"},
    "moteur.sec.equations_sub": {"fr": "non calculées", "en": "not computed"},
    "moteur.eq.e6_title": {
        "fr": "🕒 E6 — Température réelle du fondu (T_real)",
        "en": "🕒 E6 — Real melt temperature (T_real)"},
    "moteur.eq.e6_body": {
        "fr": "Équation manager imposée <code>T_real = T_set + (2π·N·M)/(ṁ·Cp) + k·τ</code> "
              "— nécessite des constantes thermiques à recaler.",
        "en": "Manager-imposed equation <code>T_real = T_set + (2π·N·M)/(ṁ·Cp) + k·τ</code> "
              "— requires thermal constants to be recalibrated."},
    "moteur.eq.e7_title": {
        "fr": "🕒 E7 — Pression / contre-pression filière",
        "en": "🕒 E7 — Die pressure / back-pressure"},
    "moteur.eq.e7_body": {
        "fr": "Nécessite une loi ΔP filière (Hagen-Poiseuille + correction non "
              "newtonienne) au-dessus de la géométrie de filière.",
        "en": "Requires a die ΔP law (Hagen-Poiseuille + non-Newtonian "
              "correction) on top of the die geometry."},
    "moteur.eq.status": {"fr": "Statut :", "en": "Status:"},
    "moteur.eq.status_na": {"fr": "non disponible.", "en": "not available."},
    "moteur.upcoming": {"fr": "À venir", "en": "Upcoming"},
    "moteur.sec.zones": {"fr": "Agrégats par zone", "en": "Per-zone aggregates"},
    "moteur.col.zone": {"fr": "Zone", "en": "Zone"},
    "moteur.col.positions": {"fr": "Positions", "en": "Positions"},
    "moteur.col.fill_mean": {"fr": "Remplissage moyen", "en": "Mean fill"},
    "moteur.col.fill_peak": {"fr": "Remplissage crête", "en": "Peak fill"},
    "moteur.col.shear_mean": {"fr": "γ̇ moyen", "en": "Mean γ̇"},
    "moteur.col.shear_max": {"fr": "γ̇ max", "en": "Max γ̇"},
    "moteur.col.t_max": {"fr": "T max", "en": "T max"},
    "moteur.col.t_max_label": {"fr": "T consigne max (°C)", "en": "Max setpoint T (°C)"},
    "moteur.col.material": {"fr": "Matière dominante", "en": "Dominant material"},
    "moteur.col.residence": {"fr": "Résidence", "en": "Residence"},
    "moteur.col.residence_label": {"fr": "Résidence (s)", "en": "Residence (s)"},
    "moteur.sec.positions": {"fr": "Propriétés locales par position de vis", "en": "Local properties per screw position"},
    "moteur.chk.hide_empty": {"fr": "Masquer les positions vides", "en": "Hide empty positions"},
    "moteur.col.element": {"fr": "Élément", "en": "Element"},
    "moteur.col.fill": {"fr": "Remplissage", "en": "Fill"},
    "moteur.col.torque_local": {"fr": "Couple local", "en": "Local torque"},
    "moteur.col.torque_local_label": {"fr": "Couple local (N·m)", "en": "Local torque (N·m)"},
    "moteur.no_positions": {
        "fr": "Aucune position à afficher (profil vide).",
        "en": "No position to display (empty profile)."},
    "moteur.sec.audit": {"fr": "Audit calcul procédé", "en": "Process calculation audit"},
    "moteur.sec.audit_sub": {
        "fr": "débit · capacité · remplissage · résidence — source PLC Network 7",
        "en": "flow · capacity · fill · residence — PLC Network 7 source"},
    "moteur.audit.ff_status": {
        "fr": "Statut du résultat fill factor : {status}",
        "en": "Fill factor result status: {status}"},
    "moteur.audit.ff_explanation": {
        "fr": "le fill factor affiché est calculé sur le <b>débit feeder effectif utilisé par le "
              "modèle</b>, <b>pas</b> sur la capacité machine globale ni sur le débit sortie filière.",
        "en": "the displayed fill factor is computed from the <b>effective feeder flow used by the "
              "model</b>, <b>not</b> from the overall machine capacity or the die output flow."},
    "moteur.audit.why_ff_body": {
        "fr": "**{title}** *Résultat cohérent avec les paramètres actuels (débit {flow} g/h, "
              "densité {dens}, {rpm} rpm, capacité vis issue PLC/DB à confirmer).* "
              "Au main feeder, `Q_vol = {qvol} cm³/s` alimenté contre une "
              "`capacité = {cap} cm³/s` → `FF = {ff} %`. Cohérent avec une bivis *starve-fed* "
              "(capacité > débit). **FF → 100 %** si la capacité descend au niveau du débit : "
              "baisser la vis vers **≈ {rpm_full} tr/min**, augmenter le débit, ou augmenter la densité. "
              "⚠️ Tant que les constantes DB vis / le ×2 bivis ne sont pas validés Rondol, "
              "ce % reste **calculé avec hypothèses**, non une vérité procédé définitive.",
        "en": "**{title}** *Result consistent with current parameters (flow {flow} g/h, "
              "density {dens}, {rpm} rpm, screw capacity from PLC/DB to be confirmed).* "
              "At the main feeder, `Q_vol = {qvol} cm³/s` fed against a "
              "`capacity = {cap} cm³/s` → `FF = {ff}%`. Consistent with a *starve-fed* "
              "twin-screw (capacity > flow). **FF → 100%** if capacity drops to flow level: "
              "lower the screw to **≈ {rpm_full} rpm**, increase the flow, or increase the density. "
              "⚠️ As long as the screw DB constants / the ×2 twin-screw are not validated by Rondol, "
              "this % remains **computed with assumptions**, not a final process truth."},
    "moteur.audit.flow_not_calibrated": {
        "fr": "Débit réel **non calculable** (coefficient d'étalonnage feeder non "
              "renseigné). Les valeurs procédé ci-dessus reposent sur la **saisie "
              "directe** de débit (hors étalonnage) — renseignez le coefficient "
              "g/h/RPM dans **Profile** pour un débit réel tracé.",
        "en": "Real flow **not computable** (feeder calibration coefficient not "
              "entered). The process values above rely on the **direct flow entry** "
              "(without calibration) — enter the g/h/RPM coefficient in **Profile** "
              "for a traced real flow."},
    "moteur.audit.status_legend": {
        "fr": "Statuts : *Formule PLC validée* = vérifiée sur la source automate Rondol "
              "(2-CALCULS.pdf, Network 7), sans constante à confirmer. *Formule PLC "
              "utilisée — constantes partiellement à confirmer* = formule PLC mais "
              "dépend de valeurs DB automate (DataScrewElmt) et/ou de la correction "
              "manager ×2 (bivis, hors PLC d'origine). *CALCULATED_WITH_ASSUMPTIONS* = "
              "résultat cohérent mais soumis à ces hypothèses. *Limite manager — à valider* "
              "= plafond 2500 g/h (manager 2026-06-09, ancien 300 g/h levé).",
        "en": "Statuses: *PLC formula validated* = verified against the Rondol PLC source "
              "(2-CALCULS.pdf, Network 7), no constant to confirm. *PLC formula used — "
              "constants partially to be confirmed* = PLC formula but depends on PLC DB "
              "values (DataScrewElmt) and/or the manager ×2 correction (twin-screw, not "
              "in original PLC). *CALCULATED_WITH_ASSUMPTIONS* = coherent result subject "
              "to these assumptions. *Manager limit — to be validated* = 2500 g/h ceiling "
              "(manager 2026-06-09, former 300 g/h lifted)."},
    "moteur.audit.flows_title": {"fr": "**Débits — ne pas confondre :**", "en": "**Flows — do not confuse:**"},
    "moteur.audit.machine_cap": {
        "fr": "Capacité machine déclarée (g/h) — référence, n'écrase PAS le débit feeder",
        "en": "Declared machine capacity (g/h) — reference, does NOT override feeder flow"},
    "moteur.audit.machine_cap_help": {
        "fr": "Optionnel. Le manager évoque ≈ 1 kg/h (1000 g/h). 0 = non renseigné. "
              "Sert de référence/contrainte, jamais de débit de calcul.",
        "en": "Optional. Manager mentions ≈ 1 kg/h (1000 g/h). 0 = not entered. "
              "Used as reference/constraint, never as computation flow."},
    "moteur.audit.feeder_detail": {"fr": "**Détail par feeder :**", "en": "**Per-feeder detail:**"},
    "moteur.audit.total_flow": {
        "fr": "Débit total feeders : **{gh} g/h** ({gmin} g/min)",
        "en": "Total feeder flow: **{gh} g/h** ({gmin} g/min)"},
    "moteur.audit.total_incomplete": {
        "fr": " — ⚠️ **incomplet** : un feeder actif n'est pas étalonné (exclu du total).",
        "en": " — ⚠️ **incomplete**: an active feeder is not calibrated (excluded from total)."},
    "moteur.audit.total_not_computable": {
        "fr": "Débit total feeders **non calculable** : aucun feeder étalonné.",
        "en": "Total feeder flow **not computable**: no calibrated feeder."},
    # Fill assessment labels
    "moteur.fill.overflow": {"fr": "Débordement (overflow)", "en": "Overflow"},
    "moteur.fill.overflow_msg": {
        "fr": "Débordement détecté à un feeder. Risque indicatif de bourrage / montée "
              "de pression — réduire le débit ou augmenter la vitesse vis (à confirmer).",
        "en": "Overflow detected at a feeder. Indicative risk of clogging / pressure "
              "rise — reduce the flow or increase the screw speed (to be confirmed)."},
    "moteur.fill.high": {"fr": "Remplissage élevé", "en": "High fill"},
    "moteur.fill.high_msg": {
        "fr": "Occupation élevée. Surveiller couple et pression ; marge de procédé réduite.",
        "en": "High occupancy. Monitor torque and pressure; reduced process margin."},
    "moteur.fill.nominal": {"fr": "Remplissage nominal", "en": "Nominal fill"},
    "moteur.fill.nominal_msg": {
        "fr": "Remplissage dans la plage opérationnelle standard — pas d'alerte.",
        "en": "Fill within the standard operational range — no alert."},
    "moteur.fill.low": {"fr": "Remplissage faible", "en": "Low fill"},
    "moteur.fill.low_msg": {
        "fr": "Occupation faible. Convoyage/mélange potentiellement insuffisants — "
              "envisager plus de débit ou moins de vitesse vis.",
        "en": "Low occupancy. Conveying/mixing potentially insufficient — "
              "consider more flow or less screw speed."},
    # Audit table labels
    "moteur.audit.col.variable": {"fr": "Variable", "en": "Variable"},
    "moteur.audit.col.value": {"fr": "Valeur", "en": "Value"},
    "moteur.audit.col.unit": {"fr": "Unité", "en": "Unit"},
    "moteur.audit.col.source": {"fr": "Source", "en": "Source"},
    "moteur.audit.col.formula": {"fr": "Formule", "en": "Formula"},
    "moteur.audit.col.status": {"fr": "Statut", "en": "Status"},
    "moteur.audit.row.rpm_feeder": {"fr": "RPM feeder", "en": "Feeder RPM"},
    "moteur.audit.row.calib_coeff": {"fr": "Coefficient étalonnage", "en": "Calibration coefficient"},
    "moteur.audit.row.flow_requested": {"fr": "Débit demandé", "en": "Requested flow"},
    "moteur.audit.row.flow_max": {"fr": "Débit max machine", "en": "Machine max flow"},
    "moteur.audit.row.flow_effective": {"fr": "Débit effectif (calcul)", "en": "Effective flow (computation)"},
    "moteur.audit.row.flow_eff_gmin": {"fr": "Débit effectif", "en": "Effective flow"},
    "moteur.audit.row.density": {"fr": "Densité apparente ρ", "en": "Apparent density ρ"},
    "moteur.audit.row.vol_flow": {"fr": "Débit volumique Q_vol", "en": "Volumetric flow Q_vol"},
    "moteur.audit.row.rpm_screw": {"fr": "RPM vis", "en": "Screw RPM"},
    "moteur.audit.row.n_screw": {"fr": "N (vis)", "en": "N (screw)"},
    "moteur.audit.row.vol_per_rev": {"fr": "V libre / tour (main)", "en": "Free V / rev (main)"},
    "moteur.audit.row.vol_cap": {"fr": "Capacité volumique (main)", "en": "Volumetric capacity (main)"},
    "moteur.audit.row.free_vol": {"fr": "Volume libre utile (2 vis)", "en": "Usable free volume (2 screws)"},
    "moteur.audit.row.n_elements": {"fr": "Nombre d'éléments", "en": "Number of elements"},
    "moteur.audit.row.ff_main": {"fr": "Fill factor (main)", "en": "Fill factor (main)"},
    "moteur.audit.row.ff_mean": {"fr": "Remplissage moyen (rapport)", "en": "Mean fill (report)"},
    "moteur.audit.row.residence": {"fr": "Temps de résidence total", "en": "Total residence time"},
    "moteur.audit.status.input": {"fr": "Saisie", "en": "Input"},
    "moteur.audit.status.calc": {"fr": "Calculé", "en": "Computed"},
    "moteur.audit.status.mgr_lim": {"fr": "Limite manager — à valider", "en": "Manager limit — to validate"},
    "moteur.audit.status.calib_ext": {
        "fr": "Étalonnage externe (= Mass_flow_rate PLC, g/tour×60)",
        "en": "External calibration (= PLC Mass_flow_rate, g/rev×60)"},
    "moteur.audit.status.calib_req": {"fr": "Étalonnage requis", "en": "Calibration required"},
    "moteur.audit.status.pdb": {"fr": "Constante PLC — valeurs DB à confirmer", "en": "PLC constant — DB values to confirm"},
    "moteur.audit.status.mgr": {"fr": "Correction manager (hors PLC d'origine)", "en": "Manager correction (not in original PLC)"},
    # Flow taxonomy (calc_audit)
    "moteur.flow.col.used_in_ff": {"fr": "Utilisée dans FF ?", "en": "Used in FF?"},
    "moteur.flow.col.comment": {"fr": "Commentaire métier", "en": "Business comment"},
    # Feeder detail table
    "moteur.feeder.col.status": {"fr": "Statut", "en": "Status"},
    "moteur.feeder.col.flow": {"fr": "Débit (g/h)", "en": "Flow (g/h)"},
    "moteur.feeder.col.contrib": {"fr": "Contribution au total", "en": "Contribution to total"},
    "moteur.feeder.status.ok": {"fr": "OK", "en": "OK"},
    "moteur.feeder.status.not_calibrated": {"fr": "Non étalonné", "en": "Not calibrated"},
    "moteur.feeder.status.disabled": {"fr": "Désactivé", "en": "Disabled"},
    "moteur.feeder.excluded": {"fr": "exclu (non étalonné)", "en": "excluded (not calibrated)"},

    # ===================================================================
    # SCREW_RENDER — recommendations
    # ===================================================================
    "sr.rec.underdense.title": {"fr": "Sous-densification de la vis", "en": "Screw under-densification"},
    "sr.rec.underdense.physics": {
        "fr": "Mélange insuffisant pour homogénéiser une formulation SSB",
        "en": "Insufficient mixing to homogenise an SSB formulation"},
    "sr.rec.underdense.action": {
        "fr": "Densifier la configuration : ajouter {add_min}-{add_max} "
              "éléments (convoyage + 2-4 malaxeurs) avant tout essai pilote. "
              "À {rpm} rpm × {feed} g/min, une vis aussi courte n'a pas "
              "de résidence exploitable.",
        "en": "Densify the configuration: add {add_min}-{add_max} "
              "elements (conveying + 2-4 kneading) before any pilot trial. "
              "At {rpm} rpm × {feed} g/min, such a short screw has no "
              "usable residence time."},
    "sr.rec.underdense.evidence": {"fr": "{n} / 39 éléments", "en": "{n} / 39 elements"},
    "sr.rec.no_conv.title": {"fr": "Transport sous-dimensionné", "en": "Under-sized transport"},
    "sr.rec.no_conv.physics": {
        "fr": "Matière non acheminée jusqu'au tip → bouchage probable",
        "en": "Material not conveyed to the tip → likely clogging"},
    "sr.rec.no_conv.action": {
        "fr": "Ajouter au moins {need} × **Convoyage +** (type 1) "
              "ou **Grand pas** (type 6) entre les zones de mélange. Sans convoyage "
              "suffisant, le débit feeder ({feed} g/min) ne sera pas évacué.",
        "en": "Add at least {need} × **Conveying +** (type 1) "
              "or **Large pitch** (type 6) between mixing zones. Without sufficient "
              "conveying, the feeder flow ({feed} g/min) will not be evacuated."},
    "sr.rec.no_conv.evidence": {"fr": "{n} convoyage(s)", "en": "{n} conveying(s)"},
    "sr.rec.conv_dominant.title": {
        "fr": "Convection dominante / cisaillement insuffisant",
        "en": "Dominant conveying / insufficient shear"},
    "sr.rec.conv_dominant.physics": {
        "fr": "Pâte transite trop vite → homogénéité poudre active compromise",
        "en": "Paste transits too fast → active powder homogeneity compromised"},
    "sr.rec.conv_dominant.action": {
        "fr": "Intercaler 2-3 × malaxeurs supplémentaires entre les zones de "
              "transport (renforcer les types déjà présents sur le profil). "
              "À {rpm} rpm le temps de séjour est court — densifier le "
              "mélange compense.",
        "en": "Interleave 2-3 additional kneading elements between the "
              "transport zones (reinforce types already present on the profile). "
              "At {rpm} rpm the dwell time is short — densifying the "
              "mixing compensates."},
    "sr.rec.excess_knead.title": {
        "fr": "Cisaillement excessif (kneading dense)",
        "en": "Excessive shear (dense kneading)"},
    "sr.rec.excess_knead.physics": {
        "fr": "Dégradation thermique liant SSB (PVDF > 200 °C, PEO > 180 °C)",
        "en": "SSB binder thermal degradation (PVDF > 200 °C, PEO > 180 °C)"},
    "sr.rec.excess_knead.action": {
        "fr": "Réduire à ≤ 5-6 malaxeurs{loc}, ou intercaler 2-3 × Convoyage + "
              "entre les blocs pour refroidir.{abrasion} À {rpm} rpm le "
              "cisaillement est {intensity}.",
        "en": "Reduce to ≤ 5-6 kneading{loc}, or interleave 2-3 × Conveying + "
              "between blocks to cool.{abrasion} At {rpm} rpm the "
              "shear is {intensity}."},
    "sr.rec.excess_knead.evidence": {"fr": "{n} mél. ({pct} %)", "en": "{n} mix. ({pct}%)"},
    "sr.rec.excess_knead.loc": {
        "fr": " en priorité sur **Z{z}** ({n} mélangeurs)",
        "en": " prioritising **Z{z}** ({n} mixers)"},
    "sr.rec.excess_knead.abrasion": {
        "fr": " Densité ρ={dens} g/cm³ (charges céramiques) → abrasion accrue des malaxeurs.",
        "en": " Density ρ={dens} g/cm³ (ceramic fillers) → increased mixer abrasion."},
    "sr.rec.excess_knead.amplified": {"fr": "amplifié", "en": "amplified"},
    "sr.rec.excess_knead.moderate": {"fr": "modéré", "en": "moderate"},
    "sr.rec.no_mix.title": {"fr": "Aucun élément de mélange", "en": "No mixing element"},
    "sr.rec.no_mix.physics": {
        "fr": "Pâte non cisaillée — formulation SSB non homogénéisable",
        "en": "Paste not sheared — SSB formulation cannot be homogenised"},
    "sr.rec.no_mix.action": {
        "fr": "Ajouter 2-4 malaxeurs : 1-2 × **Malaxage 90°** (type 4, dispersif) "
              "+ 1 × **Malaxage 30°** (type 5, distributif) en Z3-Z5. "
              "Sans cisaillement, le débit {feed} g/min ne fait que transporter la poudre.",
        "en": "Add 2-4 kneading: 1-2 × **Kneading 90°** (type 4, dispersive) "
              "+ 1 × **Kneading 30°** (type 5, distributive) in Z3-Z5. "
              "Without shear, the {feed} g/min flow only transports the powder."},
    "sr.rec.no_mix.evidence": {"fr": "0 mélangeur", "en": "0 mixer"},
    "sr.rec.overloaded.title": {"fr": "Concentration locale d'éléments", "en": "Local element concentration"},
    "sr.rec.overloaded.physics": {
        "fr": "Pic couple moteur + échauffement ponctuel, pâte mal homogénéisée en aval",
        "en": "Motor torque peak + local overheating, paste poorly homogenised downstream"},
    "sr.rec.overloaded.action": {
        "fr": "Déplacer 2-3 éléments{nb} pour répartir l'effort. À "
              "{rpm} rpm une zone surchargée crée un pic de couple difficile à absorber.",
        "en": "Move 2-3 elements{nb} to spread the effort. At "
              "{rpm} rpm an overloaded zone creates a torque peak hard to absorb."},
    "sr.rec.overloaded.action_nb": {
        "fr": " vers {zones}",
        "en": " toward {zones}"},
    "sr.rec.overloaded.evidence": {"fr": "{n} éléments en Z{z}", "en": "{n} elements in Z{z}"},
    "sr.rec.late_mix.title": {"fr": "Mélange initié tardivement", "en": "Late mixing start"},
    "sr.rec.late_mix.physics": {
        "fr": "Pâte non dispersée en amont → cisaillement final brutal sur poudre encore sèche",
        "en": "Paste not dispersed upstream → brutal final shear on still-dry powder"},
    "sr.rec.late_mix.action": {
        "fr": "Avancer 1-2 mélangeurs en **Z2-Z4** pour amorcer la dispersion du "
              "liant dans la matière active dès le pré-convoyage. Au régime "
              "{rpm} rpm × {feed} g/min, le temps de pré-mélange est "
              "court — l'amorcer tôt est critique.",
        "en": "Move 1-2 mixers forward to **Z2-Z4** to initiate binder dispersion "
              "in the active material from the pre-conveying stage. At "
              "{rpm} rpm × {feed} g/min, the pre-mixing time is "
              "short — starting it early is critical."},
    "sr.rec.late_mix.evidence": {"fr": "1er mél. en Z{z}", "en": "1st mixer in Z{z}"},
    "sr.rec.no_early.title": {"fr": "Pas de dispersion précoce", "en": "No early dispersion"},
    "sr.rec.no_early.physics": {
        "fr": "Dispersion liant retardée — homogénéité finale moins fine",
        "en": "Delayed binder dispersion — less fine final homogeneity"},
    "sr.rec.no_early.action": {
        "fr": "Ajouter 1-2 × **Malaxage 90°** (type 4) ou **Malaxage 30°** (type 5) "
              "en **Z{z}** pour amorcer la dispersion juste après le pré-convoyage feeder.",
        "en": "Add 1-2 × **Kneading 90°** (type 4) or **Kneading 30°** (type 5) "
              "in **Z{z}** to initiate dispersion right after the feeder pre-conveying."},
    "sr.rec.no_early.evidence": {"fr": "0 mél. Z1-Z4", "en": "0 mixer Z1-Z4"},
    "sr.rec.imbalance.title": {"fr": "Déséquilibre spatial du profil", "en": "Spatial profile imbalance"},
    "sr.rec.imbalance.physics": {
        "fr": "Vis effective courte — capacité utile et résidence gaspillées",
        "en": "Short effective screw — useful capacity and residence wasted"},
    "sr.rec.imbalance.action": {
        "fr": "Étaler la configuration sur Z1..Z7 pour utiliser tout le "
              "volume utile (76,2 cm³). Concentrer {pct} % du "
              "profil sur une zone unique annule le bénéfice d'une vis L/D=40.",
        "en": "Spread the configuration across Z1..Z7 to use the full "
              "working volume (76.2 cm³). Concentrating {pct}% of the "
              "profile on a single zone negates the benefit of an L/D=40 screw."},
    "sr.rec.imbalance.evidence": {"fr": "{n}/{total} en Z{z}", "en": "{n}/{total} in Z{z}"},
    "sr.rec.excess_rev.title": {"fr": "Rétention abusive (reverse multiples)", "en": "Excessive retention (multiple reverse)"},
    "sr.rec.excess_rev.physics": {
        "fr": "Surcouple moteur + cumul thermique par fusion locale",
        "en": "Motor overtorque + thermal build-up from local melting"},
    "sr.rec.excess_rev.action": {
        "fr": "Limiter à 1-2 reverse max, en fin de zone de mélange uniquement. "
              "À {rpm} rpm, multiplier les reverse fait monter le couple "
              "sans bénéfice de mélange supplémentaire.",
        "en": "Limit to 1-2 reverse max, at the end of mixing zones only. "
              "At {rpm} rpm, multiplying reverse elements raises the torque "
              "without additional mixing benefit."},
    "sr.rec.excess_rev.evidence": {"fr": "{n} reverse", "en": "{n} reverse"},
    # Empty zone recommendations
    "sr.rec.empty_zone.transport": {"fr": "Transport interrompu après le feeder", "en": "Transport interrupted after the feeder"},
    "sr.rec.empty_zone.transport_impact": {
        "fr": "Zone gaspillée, débit non acheminé vers le mélange aval",
        "en": "Wasted zone, flow not conveyed to downstream mixing"},
    "sr.rec.empty_zone.transport_action": {
        "fr": "Ajouter 2-3 × **Convoyage +** (type 1) ou 1 × **Grand pas** "
              "(type 6) en **Z{z}**. Sans convoyage ici, le débit "
              "{feed} g/min stagne au feeder.",
        "en": "Add 2-3 × **Conveying +** (type 1) or 1 × **Large pitch** "
              "(type 6) in **Z{z}**. Without conveying here, the "
              "{feed} g/min flow stagnates at the feeder."},
    "sr.rec.empty_zone.no_shear": {"fr": "Pas de cisaillement à mi-vis", "en": "No mid-screw shear"},
    "sr.rec.empty_zone.no_finish": {"fr": "Pas de finition distributive", "en": "No distributive finishing"},
    "sr.rec.empty_zone.no_shear_impact": {
        "fr": "Dispersion poudre/liant insuffisante en zone procédé naturelle",
        "en": "Insufficient powder/binder dispersion in natural process zone"},
    "sr.rec.empty_zone.no_finish_impact": {
        "fr": "Homogénéité finale du mélange compromise",
        "en": "Final mixture homogeneity compromised"},
    "sr.rec.empty_zone.mix_action": {
        "fr": "Ajouter 1-2 × **{target}** en **Z{z}**. C'est la zone procédé "
              "naturelle pour {purpose}.",
        "en": "Add 1-2 × **{target}** in **Z{z}**. This is the natural process zone "
              "for {purpose}."},
    "sr.rec.mix_target_dispersive": {
        "fr": "Malaxage 90° (dispersif)",
        "en": "Kneading 90° (dispersive)"},
    "sr.rec.mix_target_distributive": {
        "fr": "Malaxage 30°/45° (distributif)",
        "en": "Kneading 30°/45° (distributive)"},
    "sr.rec.empty_zone.dispersion": {"fr": "la dispersion", "en": "dispersion"},
    "sr.rec.empty_zone.distribution": {"fr": "la distribution finale", "en": "final distribution"},
    "sr.rec.empty_zone.no_transport": {"fr": "Pas de transport vers le tip", "en": "No transport to the tip"},
    "sr.rec.empty_zone.no_transport_impact": {
        "fr": "Pâte homogénéisée non évacuée → fluctuation débit sortie",
        "en": "Homogenised paste not evacuated → output flow fluctuation"},
    "sr.rec.empty_zone.end_action": {
        "fr": "Ajouter 2-3 × **Convoyage +** (type 1) en **Z{z}** pour "
              "acheminer la pâte sans cisaillement supplémentaire.",
        "en": "Add 2-3 × **Conveying +** (type 1) in **Z{z}** to "
              "convey the paste without additional shear."},
    "sr.rec.empty_zone.evidence": {"fr": "0 élément", "en": "0 element"},
    # Fill factor recommendations
    "sr.rec.starved.title": {"fr": "Vis sous-alimentée", "en": "Starved screw"},
    "sr.rec.starved.physics": {
        "fr": "Mélange peu efficace, qualité poudre active variable",
        "en": "Inefficient mixing, variable active powder quality"},
    "sr.rec.starved.action_feed": {
        "fr": "Augmenter le débit feeder ({feed} → ~30 g/min) pour "
              "remplir la vis. Alternative : passer à 25 éléments si la capacité prime.",
        "en": "Increase feeder flow ({feed} → ~30 g/min) to fill the screw. "
              "Alternative: switch to 25 elements if capacity is the priority."},
    "sr.rec.starved.action_rpm": {
        "fr": "Vitesse vis trop haute ({rpm} rpm) pour le débit "
              "{feed} g/min — descendre à ~120-150 rpm pour augmenter la résidence.",
        "en": "Screw speed too high ({rpm} rpm) for the "
              "{feed} g/min flow — lower to ~120-150 rpm to increase residence."},
    "sr.rec.starved.action_default": {
        "fr": "Augmenter le débit ({feed} g/min → 30+) ou ajouter un "
              "reverse en fin de mélange pour ralentir la pâte.",
        "en": "Increase the flow ({feed} g/min → 30+) or add a "
              "reverse at the end of mixing to slow the paste."},
    "sr.rec.saturated.title": {"fr": "Saturation procédé imminente", "en": "Imminent process saturation"},
    "sr.rec.saturated.physics": {
        "fr": "Blocage matière + pic couple — arrêt qualité produit",
        "en": "Material blockage + torque peak — product quality stop"},
    "sr.rec.saturated.action": {
        "fr": "Réduire le débit feeder ({feed} → ~{target_feed} g/min) "
              "ou augmenter la vitesse vis ({rpm} → ~{target_rpm} rpm). "
              "Alternative : passer à 40 éléments pour étaler la charge.",
        "en": "Reduce feeder flow ({feed} → ~{target_feed} g/min) "
              "or increase screw speed ({rpm} → ~{target_rpm} rpm). "
              "Alternative: switch to 40 elements to spread the load."},
    "sr.rec.balanced.title": {"fr": "Profil équilibré", "en": "Balanced profile"},
    "sr.rec.balanced.physics": {
        "fr": "Configuration cohérente pour un essai pilote SSB",
        "en": "Consistent configuration for an SSB pilot trial"},
    "sr.rec.balanced.action": {
        "fr": "Lancer un essai pilote pour valider l'homogénéité finale du "
              "mélange à {rpm} rpm × {feed} g/min × ρ={dens} g/cm³.",
        "en": "Launch a pilot trial to validate the final homogeneity of the "
              "mixture at {rpm} rpm × {feed} g/min × ρ={dens} g/cm³."},
    "sr.rec.no_distrib.title": {
        "fr": "Manque de mélangeur distributif terminal",
        "en": "Missing terminal distributive mixer"},
    "sr.rec.no_distrib.physics": {
        "fr": "Homogénéité globale insuffisante — cisaillement local sans diffusion",
        "en": "Insufficient global homogeneity — local shear without diffusion"},
    "sr.rec.no_distrib.action": {
        "fr": "Ajouter 1 × **Denté** (type 11) ou **Mélange spécial** (type 12) "
              "en **Z{z}**. Combinaison dispersif + distributif obligatoire pour SSB.",
        "en": "Add 1 × **Toothed** (type 11) or **Special mixing** (type 12) "
              "in **Z{z}**. Dispersive + distributive combination mandatory for SSB."},
    "sr.rec.fallback.title": {"fr": "Configuration cohérente", "en": "Consistent configuration"},
    "sr.rec.fallback.physics": {
        "fr": "Aucune anomalie liée aux éléments présents",
        "en": "No anomaly related to present elements"},
    "sr.rec.fallback.action": {
        "fr": "Ajuster si besoin la vitesse vis ({rpm} rpm), le débit "
              "({feed} g/min) ou la température pour viser le taux de "
              "remplissage cible.",
        "en": "Adjust if needed screw speed ({rpm} rpm), flow "
              "({feed} g/min) or temperature to target the fill factor goal."},
    "sr.rec.fallback.evidence": {
        "fr": "recommandations limitées aux éléments présents",
        "en": "recommendations limited to present elements"},

    # ===================================================================
    # SCREW_RENDER — scoring criteria (25/30/40)
    # ===================================================================
    "sr.score.starved": {"fr": "Vis sous-alimentée", "en": "Starved screw"},
    "sr.score.starved.r": {
        "fr": "Vis sous-alimentée — pas besoin d'allonger : 25 éléments libèrent "
              "de la capacité de production sans pénaliser le mélange.",
        "en": "Starved screw — no need to lengthen: 25 elements free up "
              "production capacity without penalising mixing."},
    "sr.score.fill_moderate": {"fr": "Remplissage modéré", "en": "Moderate fill"},
    "sr.score.fill_moderate.r": {
        "fr": "Remplissage faible-modéré — plage standard, 30 éléments sans surdimensionner.",
        "en": "Low-moderate fill — standard range, 30 elements without oversizing."},
    "sr.score.fill_balanced": {"fr": "Remplissage équilibré", "en": "Balanced fill"},
    "sr.score.fill_balanced.r": {
        "fr": "Remplissage modéré — résidence/capacité bien équilibrées sur 30 ; "
              "40 reste pertinent si du mélange est ajouté.",
        "en": "Moderate fill — residence/capacity well balanced at 30; "
              "40 remains relevant if mixing is added."},
    "sr.score.fill_high": {"fr": "Remplissage élevé", "en": "High fill"},
    "sr.score.fill_high.r": {
        "fr": "Remplissage élevé — 40 éléments allongent la résidence et absorbent les pics de charge.",
        "en": "High fill — 40 elements extend residence and absorb load peaks."},
    "sr.score.fill_sat": {"fr": "Saturation imminente", "en": "Imminent saturation"},
    "sr.score.fill_sat.r": {
        "fr": "Remplissage critique → risque saturation. 40 éléments pour étaler la charge et éviter le pic couple.",
        "en": "Critical fill → saturation risk. 40 elements to spread the load and avoid torque peak."},
    "sr.score.no_element": {"fr": "Aucun élément", "en": "No element"},
    "sr.score.no_element.r": {"fr": "Aucun élément placé : critère neutre.", "en": "No element placed: neutral criterion."},
    "sr.score.transport_pure": {"fr": "Transport pur", "en": "Pure transport"},
    "sr.score.transport_pure.r": {
        "fr": "Profil de transport pur — aucun élément de mélange. Une vis courte (25) suffit, 40 serait sous-utilisée.",
        "en": "Pure transport profile — no mixing element. A short screw (25) suffices, 40 would be under-used."},
    "sr.score.mix_light": {"fr": "Mélange léger", "en": "Light mixing"},
    "sr.score.mix_light.r": {
        "fr": "Mélange léger ({n} mélangeur(s)) — 25 ou 30 selon priorité capacité/résidence.",
        "en": "Light mixing ({n} mixer(s)) — 25 or 30 depending on capacity/residence priority."},
    "sr.score.mix_balanced": {"fr": "Mélange équilibré", "en": "Balanced mixing"},
    "sr.score.mix_balanced.r": {
        "fr": "Mélange standard ({n} mélangeurs, {pct} % du profil) — plage cible pour 30 éléments.",
        "en": "Standard mixing ({n} mixers, {pct}% of the profile) — target range for 30 elements."},
    "sr.score.mix_dispersive": {"fr": "Mélange dispersif important", "en": "Significant dispersive mixing"},
    "sr.score.mix_dispersive.r": {
        "fr": "Mélange dispersif important ({n} mélangeurs, {pct} %) — 40 éléments pour le cisaillement cumulé.",
        "en": "Significant dispersive mixing ({n} mixers, {pct}%) — 40 elements for cumulated shear."},
    "sr.score.mix_extreme": {"fr": "Profil très dispersif", "en": "Highly dispersive profile"},
    "sr.score.mix_extreme.r": {
        "fr": "Profil très dispersif ({pct} % de mélange) — 40 éléments indispensables pour intercaler du convoyage entre les blocs.",
        "en": "Highly dispersive profile ({pct}% mixing) — 40 elements essential to interleave conveying between blocks."},
    "sr.score.no_signal": {"fr": "Pas de signal", "en": "No signal"},
    "sr.score.no_signal.r": {"fr": "Pas de signal cisaillement/transport.", "en": "No shear/transport signal."},
    "sr.score.shear_no_conv": {"fr": "Cisaillement sans transport", "en": "Shear without transport"},
    "sr.score.shear_no_conv.r": {
        "fr": "Profil composé exclusivement de kneading — non viable sans convoyage. 40 éléments pour intercaler du transport.",
        "en": "Profile composed exclusively of kneading — not viable without conveying. 40 elements to interleave transport."},
    "sr.score.conv_only": {"fr": "Convoyage seul", "en": "Conveying only"},
    "sr.score.conv_only.r": {"fr": "Convoyage seul, aucun kneading — vis courte suffisante.", "en": "Conveying only, no kneading — short screw sufficient."},
    "sr.score.conv_dominant": {"fr": "Convoyage dominant", "en": "Dominant conveying"},
    "sr.score.conv_dominant.r": {
        "fr": "Convoyage prédominant (ratio K/C = {ratio}) — 30 éléments couvrent le besoin avec marge.",
        "en": "Predominant conveying (K/C ratio = {ratio}) — 30 elements cover the need with margin."},
    "sr.score.shear_balanced": {"fr": "Cisaillement / transport équilibrés", "en": "Balanced shear / transport"},
    "sr.score.shear_balanced.r": {
        "fr": "Équilibre kneading/convoyage (K/C = {ratio}) — 30 ou 40 selon résidence visée et thermique du liant.",
        "en": "Kneading/conveying balance (K/C = {ratio}) — 30 or 40 depending on target residence and binder thermal behaviour."},
    "sr.score.shear_dominant": {"fr": "Cisaillement dominant", "en": "Dominant shear"},
    "sr.score.shear_dominant.r": {
        "fr": "Kneading dominant (K/C = {ratio}) — risque thermique. 40 éléments pour intercaler du convoyage de refroidissement.",
        "en": "Dominant kneading (K/C = {ratio}) — thermal risk. 40 elements to interleave cooling conveying."},
    "sr.score.zones_full": {"fr": "Vis pleinement utilisée", "en": "Screw fully used"},
    "sr.score.zones_full.r": {
        "fr": "Toutes les zones procédé sont occupées — la vis utilise sa longueur de manière homogène.",
        "en": "All process zones are occupied — the screw uses its length evenly."},
    "sr.score.zones_compact": {"fr": "Profil compact", "en": "Compact profile"},
    "sr.score.zones_compact.r": {
        "fr": "{m} ({zlist}) — profil compact mais cohérent ; 30 éléments restent ajustés.",
        "en": "{m} ({zlist}) — compact but consistent profile; 30 elements remain suitable."},
    "sr.score.zones_underused": {"fr": "Vis sous-utilisée", "en": "Screw under-used"},
    "sr.score.zones_underused.r": {
        "fr": "{m} ({zlist}) — la vis effective est plus courte que prévu, 25 éléments suffiraient sans gaspiller de longueur.",
        "en": "{m} ({zlist}) — the effective screw is shorter than intended, 25 elements would suffice without wasting length."},
    "sr.score.zones_very_underused": {"fr": "Vis très peu utilisée", "en": "Screw very under-used"},
    "sr.score.zones_very_underused.r": {
        "fr": "{m} ({zlist}) — la vis travaille comme une vis très courte. 25 éléments alignés avec l'usage réel.",
        "en": "{m} ({zlist}) — the screw works as a very short screw. 25 elements aligned with actual use."},
    "sr.score.zone_measured_1": {"fr": "{n} zone vide", "en": "{n} empty zone"},
    "sr.score.zone_measured_n": {"fr": "{n} zones vides", "en": "{n} empty zones"},
    "sr.score.zone_measured_0": {"fr": "0 zone vide", "en": "0 empty zone"},

    # Count benefits / risks / alternatives / taglines / length strategy
    "sr.count.benefit.25.1": {"fr": "Capacité de production maximale (transit rapide).", "en": "Maximum production capacity (fast transit)."},
    "sr.count.benefit.25.2": {"fr": "Échauffement minimal — adapté aux liants thermosensibles (PEO, PVDF).", "en": "Minimal heating — suited to thermosensitive binders (PEO, PVDF)."},
    "sr.count.benefit.25.3": {"fr": "Énergie consommée par kg produit plus faible.", "en": "Lower energy consumption per kg produced."},
    "sr.count.benefit.30.1": {"fr": "Bon compromis résidence / capacité — peu de pertes des deux côtés.", "en": "Good residence / capacity trade-off — few losses on either side."},
    "sr.count.benefit.30.2": {"fr": "Polyvalent : accepte transport, mélange standard et formulations courantes.", "en": "Versatile: accepts transport, standard mixing and common formulations."},
    "sr.count.benefit.30.3": {"fr": "Risque thermique modéré sur la plupart des liants.", "en": "Moderate thermal risk on most binders."},
    "sr.count.benefit.40.1": {"fr": "Résidence longue — dispersion poussée possible sur formulations difficiles.", "en": "Long residence — advanced dispersion possible on difficult formulations."},
    "sr.count.benefit.40.2": {"fr": "Cisaillement cumulé élevé pour homogénéiser charges céramiques et liants visqueux.", "en": "High cumulated shear to homogenise ceramic fillers and viscous binders."},
    "sr.count.benefit.40.3": {"fr": "Marge pour intercaler convoyage entre les blocs de mélange (refroidissement).", "en": "Room to interleave conveying between mixing blocks (cooling)."},
    "sr.count.risk.25.1": {"fr": "Limite la marge de mélange et l'homogénéisation possible.", "en": "Limits the mixing margin and achievable homogenisation."},
    "sr.count.risk.25.2": {"fr": "Inadapté aux formulations chargées ou aux liants visqueux.", "en": "Unsuited to loaded formulations or viscous binders."},
    "sr.count.risk.25.3": {"fr": "Temps de séjour court, dispersion difficile.", "en": "Short dwell time, difficult dispersion."},
    "sr.count.risk.30.1": {"fr": "Pas adapté aux dispersions très poussées.", "en": "Not suited to very advanced dispersions."},
    "sr.count.risk.30.2": {"fr": "Capacité légèrement réduite face à une vis plus courte.", "en": "Slightly reduced capacity compared to a shorter screw."},
    "sr.count.risk.40.1": {"fr": "Augmente le risque de chauffe sur les séjours longs.", "en": "Increases the risk of heating during long dwell times."},
    "sr.count.risk.40.2": {"fr": "Réduit la capacité de production.", "en": "Reduces production capacity."},
    "sr.count.risk.40.3": {"fr": "Sollicite davantage le couple moteur.", "en": "Increases motor torque demand."},
    "sr.count.tagline.25": {"fr": "profil capacité", "en": "capacity profile"},
    "sr.count.tagline.30": {"fr": "profil équilibré", "en": "balanced profile"},
    "sr.count.tagline.40": {"fr": "dispersion poussée", "en": "advanced dispersion"},
    "sr.count.alt.25_30.title": {"fr": "Plus de mélange", "en": "More mixing"},
    "sr.count.alt.25_30.sentence": {"fr": "Améliore l'homogénéisation, réduit la capacité de production.", "en": "Improves homogenisation, reduces production capacity."},
    "sr.count.alt.25_40.title": {"fr": "Dispersion poussée", "en": "Advanced dispersion"},
    "sr.count.alt.25_40.sentence": {"fr": "Adapté aux formulations difficiles, baisse fortement la capacité.", "en": "Suited to difficult formulations, greatly reduces capacity."},
    "sr.count.alt.30_25.title": {"fr": "Plus de capacité", "en": "More capacity"},
    "sr.count.alt.30_25.sentence": {"fr": "Augmente la production, réduit le mélange disponible.", "en": "Increases production, reduces available mixing."},
    "sr.count.alt.30_40.title": {"fr": "Plus de cisaillement", "en": "More shear"},
    "sr.count.alt.30_40.sentence": {"fr": "Améliore la dispersion, augmente le risque de chauffe.", "en": "Improves dispersion, increases heating risk."},
    "sr.count.alt.40_25.title": {"fr": "Maximum capacité", "en": "Maximum capacity"},
    "sr.count.alt.40_25.sentence": {"fr": "Production rapide, supprime le cisaillement cumulé.", "en": "Fast production, removes cumulated shear."},
    "sr.count.alt.40_30.title": {"fr": "Compromis polyvalent", "en": "Versatile trade-off"},
    "sr.count.alt.40_30.sentence": {"fr": "Réduit le risque de chauffe, dispersion souvent suffisante.", "en": "Reduces heating risk, dispersion often sufficient."},
    "sr.count.strategy.25": {
        "fr": "Conserver 25 éléments si l'objectif est production rapide et faible "
              "résidence — compatible liants thermosensibles (PVDF, PEO).",
        "en": "Keep 25 elements if the goal is fast production and low "
              "residence — compatible with thermosensitive binders (PVDF, PEO)."},
    "sr.count.strategy.30": {
        "fr": "Passer à 30 éléments pour un compromis stabilité / résidence — "
              "polyvalent sur la majorité des formulations SSB.",
        "en": "Switch to 30 elements for a stability / residence trade-off — "
              "versatile for most SSB formulations."},
    "sr.count.strategy.40": {
        "fr": "Passer à 40 éléments pour une dispersion poussée des charges céramiques "
              "— surveiller la chauffe (dégradation liant > 180-200 °C).",
        "en": "Switch to 40 elements for advanced dispersion of ceramic fillers "
              "— watch for heating (binder degradation > 180-200 °C)."},

    # Action steps (screw_render)
    "sr.action.empty_main": {
        "fr": "Placer au moins 6 à 10 éléments après le feeder pour amorcer "
              "l'analyse procédé (homogénéité poudre active SSB).",
        "en": "Place at least 6 to 10 elements after the feeder to start "
              "the process analysis (active SSB powder homogeneity)."},
    "sr.action.nominal": {
        "fr": "Configuration cohérente ({n} éléments, remplissage "
              "{ff} % à {rpm} rpm, {feed} g/min) — passer à "
              "l'essai pilote pour valider l'homogénéité du mélange solide.",
        "en": "Consistent configuration ({n} elements, fill "
              "{ff}% at {rpm} rpm, {feed} g/min) — proceed to "
              "the pilot trial to validate solid mixture homogeneity."},

    # feeder_ui audit labels
    "feeder.audit.rpm": {"fr": "RPM feeder", "en": "Feeder RPM"},
    "feeder.audit.calib_coeff": {"fr": "Coefficient étalonnage", "en": "Calibration coefficient"},
    "feeder.audit.flow_real": {"fr": "Débit réel", "en": "Real flow"},
    "feeder.audit.flow_real_nc": {
        "fr": "Non calculable — étalonnage externe requis",
        "en": "Not computable — external calibration required"},
    "feeder.audit.density": {"fr": "Densité apparente", "en": "Apparent density"},
    "feeder.audit.vol_flow": {"fr": "Débit volumique", "en": "Volumetric flow"},
    "feeder.audit.flow_requested": {"fr": "Débit demandé", "en": "Requested flow"},
    "feeder.audit.flow_max": {"fr": "Débit max machine", "en": "Machine max flow"},
    "feeder.audit.flow_used": {"fr": "Débit utilisé (calcul)", "en": "Flow used (computation)"},
    "feeder.audit.vol_flow_full": {"fr": "Débit volumique (ṁ/ρ)", "en": "Volumetric flow (ṁ/ρ)"},
    "feeder.status.not_calibrated": {"fr": "Non étalonné", "en": "Not calibrated"},
    "feeder.status.disabled": {"fr": "Désactivé", "en": "Disabled"},

    # calc_audit flow taxonomy
    "calc.flow.feeder": {"fr": "Débit feeder utilisé (calcul FF)", "en": "Feeder flow used (FF computation)"},
    "calc.flow.feeder_comment": {
        "fr": "Débit effectif étalonné, plafonné max machine — SEUL débit entrant dans le fill factor.",
        "en": "Effective calibrated flow, capped at machine max — ONLY flow entering the fill factor."},
    "calc.flow.machine_max": {"fr": "Débit machine maximal déclaré", "en": "Declared machine max flow"},
    "calc.flow.machine_max_comment": {
        "fr": "Contrainte/référence machine (≈ 1 kg/h évoqué) — N'ÉCRASE PAS le débit feeder.",
        "en": "Machine constraint/reference (≈ 1 kg/h mentioned) — does NOT override feeder flow."},
    "calc.flow.output": {"fr": "Débit sortie filière estimé", "en": "Estimated die output flow"},
    "calc.flow.output_comment": {
        "fr": "Hypothèse régime permanent (sortie ≈ entrée) — pas une mesure.",
        "en": "Steady-state assumption (output ≈ input) — not a measurement."},
    "calc.flow.dry_polymer": {"fr": "Débit polymère sec estimé", "en": "Estimated dry polymer flow"},
    "calc.flow.dry_polymer_comment": {
        "fr": "Nécessite taux solide / humidité — non renseigné.",
        "en": "Requires solid content / moisture — not entered."},
    "calc.flow.losses": {"fr": "Pertes / humidité", "en": "Losses / moisture"},
    "calc.flow.losses_comment": {
        "fr": "À renseigner (séchage, pertes procédé).",
        "en": "To be entered (drying, process losses)."},
    "calc.flow.yes": {"fr": "Oui", "en": "Yes"},
    "calc.flow.no": {"fr": "Non", "en": "No"},

    # demo_ml_run banner
    "demo.ml.banner_default": {
        "fr": "Indicateurs issus du <b>dataset ML d'essais (avril 2026)</b> — données de "
              "<b>démonstration</b>, non un run opérateur live.",
        "en": "Indicators from the <b>ML trial dataset (April 2026)</b> — "
              "<b>demonstration</b> data, not a live operator run."},

    # Formula status labels (calc_audit)
    "calc.formula.plc_validated": {
        "fr": "Formule PLC validée (Network 7)",
        "en": "PLC formula validated (Network 7)"},
    "calc.formula.plc_assumptions": {
        "fr": "Formule PLC utilisée — constantes partiellement à confirmer",
        "en": "PLC formula used — constants partially to be confirmed"},

    # _build_action_steps — main/secondary action texts (screw_render.py)
    "sr.action.thermal_binder": {
        "fr": "Remplissage {ff} % à {rpm} rpm avec {nk} éléments de malaxage — risque de "
              "dégradation thermique du liant (PVDF se dégrade > 200 °C, PEO > 180 °C). "
              "Réduire à 5-6 kneading ou intercaler du convoyage de refroidissement.",
        "en": "Fill {ff}% at {rpm} rpm with {nk} kneading elements — risk of thermal "
              "degradation of the binder (PVDF degrades > 200 °C, PEO > 180 °C). "
              "Reduce to 5-6 kneading or insert cooling conveying."},
    "sr.action.excess_shear": {
        "fr": "Cisaillement excessif : {nk} éléments de malaxage à {rpm} rpm — chauffe "
              "locale, risque dégradation liant SSB. Réduire à 5-6 kneading.",
        "en": "Excessive shear: {nk} kneading elements at {rpm} rpm — local heating, "
              "SSB binder degradation risk. Reduce to 5-6 kneading."},
    "sr.action.residence_cumul": {
        "fr": "Résidence {zone} = {t} s avec malaxage dense ({nk} kneading) — cumul "
              "thermique préjudiciable au liant. Répartir le mélange en aval ou intercaler "
              "du convoyage.",
        "en": "Residence {zone} = {t} s with dense kneading ({nk} kneading) — thermal "
              "accumulation detrimental to the binder. Spread mixing downstream or insert "
              "conveying."},
    "sr.action.reverse_excess": {
        "fr": "{nr} éléments à pas inverse — fusion locale et surcouple à {rpm} rpm. "
              "Limiter à 1-2 max.",
        "en": "{nr} reverse-pitch elements — local melting and over-torque at {rpm} rpm. "
              "Limit to 1-2 max."},
    "sr.action.mix_deficit": {
        "fr": "Seulement {nm} élément(s) de mélange à {feed} g/min — homogénéité poudre "
              "active insuffisante pour SSB. Ajouter au moins {missing} kneading ou chaotic "
              "après le feeder.",
        "en": "Only {nm} mixing element(s) at {feed} g/min — insufficient active powder "
              "homogeneity for SSB. Add at least {missing} kneading or chaotic after the "
              "feeder."},
    "sr.action.saturation": {
        "fr": "Remplissage {ff} % à {feed} g/min × densité {dens} g/cm³ — saturation "
              "critique, montée en couple et chauffe par friction. Baisser le débit feeder "
              "ou augmenter {rpm} → ~150 rpm pour redescendre.",
        "en": "Fill {ff}% at {feed} g/min × density {dens} g/cm³ — critical saturation, "
              "torque rise and friction heating. Lower feeder flow or increase {rpm} → "
              "~150 rpm to reduce."},
    "sr.action.no_dispersive": {
        "fr": "Pas d'élément dispersif terminal (toothed / special) — homogénéité finale "
              "du mélange solide compromise. Ajouter 1 à 2 éléments en Z6-Z7 pour finaliser "
              "la dispersion.",
        "en": "No terminal dispersive element (toothed / special) — final solid blend "
              "homogeneity compromised. Add 1-2 elements in Z6-Z7 to finalize dispersion."},
    "sr.action.mix_concentrated": {
        "fr": "Mélange concentré sur Z{z} ({count} éléments) — chauffe locale, gradient "
              "thermique sur le liant. Répartir entre Z{z} et {target}.",
        "en": "Mixing concentrated on Z{z} ({count} elements) — local heating, thermal "
              "gradient on the binder. Spread between Z{z} and {target}."},
    "sr.action.zones_empty": {
        "fr": "{zones} vides : longueur procédé sous-utilisée. Étendre la configuration "
              "pour stabiliser la résidence et la qualité du mélange solide.",
        "en": "{zones} empty: process length underutilized. Extend the configuration to "
              "stabilize residence and solid blend quality."},
    "sr.action.cooling_needed": {
        "fr": "{nk} kneading pour seulement {nc} convoyage — intercaler du convoyage "
              "entre les blocs de malaxage pour refroidir avant cumul thermique sur le liant.",
        "en": "{nk} kneading for only {nc} conveying — insert conveying between kneading "
              "blocks to cool before thermal accumulation on the binder."},
    "sr.action.ff_high": {
        "fr": "Remplissage {ff} % (cible {lo}-{hi} %) à {feed} g/min × densité "
              "{dens} g/cm³ — au-dessus de la plage cible. Baisser le débit feeder "
              "ou augmenter la vitesse vis.",
        "en": "Fill {ff}% (target {lo}-{hi}%) at {feed} g/min × density "
              "{dens} g/cm³ — above target range. Lower feeder flow or increase "
              "screw speed."},
    "sr.action.ff_low": {
        "fr": "Remplissage {ff} % très bas à {feed} g/min — vis sous-alimentée, mélange "
              "peu efficace, qualité poudre active variable. Augmenter le débit ou vérifier "
              "la densité bulk ({dens} g/cm³).",
        "en": "Fill {ff}% very low at {feed} g/min — screw underfed, mixing inefficient, "
              "variable active powder quality. Increase flow or check bulk density "
              "({dens} g/cm³)."},
    "sr.action.zones_and": {"fr": " et ", "en": " and "},

    # _overall_assessment summaries
    "sr.overall.ok": {
        "fr": "Profil optimisé : {parts}. Configuration cohérente, prêt pour essai pilote SSB.",
        "en": "Optimized profile: {parts}. Consistent configuration, ready for SSB pilot trial."},
    "sr.overall.watch": {
        "fr": "Profil acceptable avec points de vigilance : {parts}. Appliquer les compensations avant essai prolongé.",
        "en": "Acceptable profile with watch points: {parts}. Apply compensations before extended trial."},
    "sr.overall.alert": {
        "fr": "Profil déséquilibré : {parts}. Corriger les axes en alerte avant tout essai pilote.",
        "en": "Unbalanced profile: {parts}. Correct alerted axes before any pilot trial."},

    # _ENRICHED_VERDICT
    "sr.verdict.ok": {
        "fr": "garantit la stabilité globale du procédé",
        "en": "guarantees overall process stability"},
    "sr.verdict.watch": {
        "fr": "préserve un équilibre acceptable sous surveillance ciblée",
        "en": "preserves acceptable balance under targeted monitoring"},
    "sr.verdict.alert": {
        "fr": "demande une validation en essai pilote avant production",
        "en": "requires pilot trial validation before production"},
    "sr.verdict.fallback": {
        "fr": "reste à valider en essai pilote",
        "en": "remains to be validated in pilot trial"},

    # _build_why_enriched — cost/gain pairs
    "sr.enrich.no_comp": {
        "fr": "Compromis : aucune action critique à compenser — l'équilibre global est déjà atteint sur cette configuration.",
        "en": "Trade-off: no critical action to compensate — overall balance already reached on this configuration."},
    "sr.enrich.cost.knead": {
        "fr": "un léger excès de cisaillement local en {z_src}",
        "en": "a slight excess of local shear in {z_src}"},
    "sr.enrich.gain.knead": {
        "fr": "un distributif posé en {target} qui restaure l'homogénéité aval sans ajouter de chauffe",
        "en": "a distributive element placed in {target} restoring downstream homogeneity without adding heat"},
    "sr.enrich.cost.densif": {
        "fr": "une hausse du fill factor moyen liée à la densification",
        "en": "an increase in average fill factor due to densification"},
    "sr.enrich.gain.densif": {
        "fr": "l'ajustement débit feeder en parallèle, qui maintient le régime de remplissage dans la cible procédé (30-55 %)",
        "en": "parallel feeder flow adjustment maintaining the fill regime within the process target (30-55%)"},
    "sr.enrich.cost.flow": {
        "fr": "une baisse de la capacité de production",
        "en": "a decrease in production capacity"},
    "sr.enrich.gain.flow": {
        "fr": "le rééquilibrage du mélange en {target}, qui évite un nouveau hotspot lié à la résidence raccourcie",
        "en": "mixing rebalancing in {target}, avoiding a new hotspot from shortened residence"},
    "sr.enrich.cost.reverse": {
        "fr": "une rétention plus courte (mélange un peu moins long)",
        "en": "shorter retention (slightly less mixing time)"},
    "sr.enrich.gain.reverse": {
        "fr": "le convoyage compensateur en {target}, qui stabilise le débit de sortie et baisse le couple",
        "en": "compensating conveying in {target}, stabilizing output flow and reducing torque"},
    "sr.enrich.cost.move": {
        "fr": "la redistribution depuis {z_src}",
        "en": "redistribution from {z_src}"},
    "sr.enrich.gain.move": {
        "fr": "la zone {target} qui absorbe sans dépasser la densité limite, pas de nouveau hotspot créé",
        "en": "zone {target} absorbing without exceeding density limit, no new hotspot created"},
    "sr.enrich.cost.dispersive": {
        "fr": "une dispersion fine qui resterait sinon cantonnée localement",
        "en": "fine dispersion that would otherwise remain locally confined"},
    "sr.enrich.gain.dispersive": {
        "fr": "un toothed/special terminal en {target} qui la diffuse à l'échelle globale, à coût thermique nul",
        "en": "a terminal toothed/special in {target} diffusing it globally at zero thermal cost"},
    "sr.enrich.sentence": {
        "fr": "Compromis assumé : on choisit {n} éléments au prix de {cost}, compensé par {gain}, ce qui {verdict}.",
        "en": "Accepted trade-off: choosing {n} elements at the cost of {cost}, compensated by {gain}, which {verdict}."},

    # _decision_action_phrase
    "sr.decide.keep_knead": {
        "fr": "Conserver {n} éléments, réduire le kneading en {z_src} et poser un distributif en {target} pour stabiliser le cisaillement local.",
        "en": "Keep {n} elements, reduce kneading in {z_src} and place a distributive in {target} to stabilize local shear."},
    "sr.decide.densify": {
        "fr": "Passer à {n} éléments en densifiant la vis et ajuster le débit feeder pour maintenir le fill factor dans la cible 30-55 %.",
        "en": "Move to {n} elements by densifying the screw and adjust feeder flow to maintain fill factor in the 30-55% target."},
    "sr.decide.reduce_flow": {
        "fr": "Conserver {n} éléments et réduire légèrement le débit feeder pour sortir la vis de saturation, en surveillant {target}.",
        "en": "Keep {n} elements and slightly reduce feeder flow to exit screw saturation, monitoring {target}."},
    "sr.decide.limit_reverse": {
        "fr": "Limiter les reverse à 1-2 et compenser avec du convoyage en {target} pour stabiliser le débit ({n} éléments).",
        "en": "Limit reverse to 1-2 and compensate with conveying in {target} to stabilize flow ({n} elements)."},
    "sr.decide.spread": {
        "fr": "Étaler les éléments concentrés depuis {z_src} vers {target} pour casser le hotspot local ({n} éléments).",
        "en": "Spread concentrated elements from {z_src} to {target} to break local hotspot ({n} elements)."},
    "sr.decide.add_dispersive": {
        "fr": "Conserver {n} éléments et ajouter un toothed/special en {target} pour finir la dispersion à l'échelle globale.",
        "en": "Keep {n} elements and add a toothed/special in {target} to finalize dispersion at global scale."},
    "sr.decide.generic": {
        "fr": "Appliquer la compensation prioritaire en {target} sur {n} éléments.",
        "en": "Apply priority compensation in {target} on {n} elements."},

    # _decision_next_step
    "sr.next.pilot": {
        "fr": "Lancer un essai pilote avec cette configuration.",
        "en": "Launch a pilot trial with this configuration."},
    "sr.next.validate_zone": {
        "fr": "Valider la stabilité en {zone} sur un essai pilote court avant montée en production.",
        "en": "Validate stability in {zone} on a short pilot trial before scaling to production."},
    "sr.next.validate_short": {
        "fr": "Valider sur essai pilote court avant montée en production.",
        "en": "Validate on a short pilot trial before scaling to production."},
    "sr.next.stabilize_target": {
        "fr": "Stabiliser {target} en priorité avant tout essai pilote.",
        "en": "Stabilize {target} as priority before any pilot trial."},
    "sr.next.stabilize_process": {
        "fr": "Stabiliser le procédé en priorité avant tout essai pilote.",
        "en": "Stabilize the process as priority before any pilot trial."},

    # _build_decision_layer — keep config
    "sr.decide.keep_config": {
        "fr": "Conserver la configuration {n} éléments — l'équilibre global est validé, aucune compensation requise.",
        "en": "Keep the {n}-element configuration — overall balance validated, no compensation required."},

    # _operator_summary_from_comp
    "sr.op.knead.decision": {
        "fr": "Réduire le mélange en début de vis et finir plus loin.",
        "en": "Reduce mixing at the start of the screw and finish further down."},
    "sr.op.knead.why": {
        "fr": "Trop d'éléments mélangeurs sont concentrés au début — la matière chauffe trop à cet endroit.",
        "en": "Too many mixing elements are concentrated at the start — the material overheats there."},
    "sr.op.knead.action": {
        "fr": "Retirer 1 mélangeur en amont, ajouter 1 élément de finition vers la sortie.",
        "en": "Remove 1 mixer upstream, add 1 finishing element towards the exit."},
    "sr.op.densify.decision": {
        "fr": "Allonger la vis pour mieux travailler la matière.",
        "en": "Lengthen the screw to better process the material."},
    "sr.op.densify.why": {
        "fr": "Le profil est trop court : la matière n'a pas le temps d'être correctement mélangée.",
        "en": "The profile is too short: the material does not have enough time to be properly mixed."},
    "sr.op.densify.action": {
        "fr": "Ajouter quelques éléments et ajuster légèrement le débit pour garder un bon remplissage.",
        "en": "Add a few elements and slightly adjust the flow to maintain good fill."},
    "sr.op.flow.decision": {
        "fr": "Baisser le débit pour sortir la vis de saturation.",
        "en": "Lower the flow to exit screw saturation."},
    "sr.op.flow.why": {
        "fr": "La vis est trop chargée — la matière n'a plus la place de s'écouler correctement.",
        "en": "The screw is overloaded — the material no longer has room to flow properly."},
    "sr.op.flow.action": {
        "fr": "Réduire le débit feeder et monter légèrement les tours/minute.",
        "en": "Reduce feeder flow and slightly increase RPM."},
    "sr.op.reverse.decision": {
        "fr": "Limiter les éléments de rétention et relancer le transport.",
        "en": "Limit retention elements and restore transport."},
    "sr.op.reverse.why": {
        "fr": "Trop d'éléments retiennent la matière — le débit en sortie devient instable.",
        "en": "Too many elements retain the material — outlet flow becomes unstable."},
    "sr.op.reverse.action": {
        "fr": "Garder 1 à 2 reverse maximum et ajouter un élément de transport vers la sortie.",
        "en": "Keep 1-2 reverse max and add a transport element towards the exit."},
    "sr.op.spread.decision": {
        "fr": "Étaler la zone surchargée sur les zones voisines.",
        "en": "Spread the overloaded zone across neighboring zones."},
    "sr.op.spread.why": {
        "fr": "Trop d'éléments sont concentrés au même endroit — la matière chauffe localement.",
        "en": "Too many elements concentrated in the same place — material heats locally."},
    "sr.op.spread.action": {
        "fr": "Déplacer 2 à 3 éléments vers la zone voisine la moins remplie.",
        "en": "Move 2-3 elements to the least filled neighboring zone."},
    "sr.op.dispersive.decision": {
        "fr": "Ajouter une finition de mélange en sortie.",
        "en": "Add a mixing finish at the exit."},
    "sr.op.dispersive.why": {
        "fr": "Le mélange est intense en amont mais rien ne finalise l'homogénéisation avant la sortie.",
        "en": "Mixing is intense upstream but nothing finalizes homogenization before the exit."},
    "sr.op.dispersive.action": {
        "fr": "Poser 1 élément de finition (denté ou mélange spécial) juste avant la sortie.",
        "en": "Place 1 finishing element (toothed or special mix) just before the exit."},
    "sr.op.fallback.decision": {
        "fr": "Appliquer la compensation prioritaire avant tout essai.",
        "en": "Apply the priority compensation before any trial."},
    "sr.op.fallback.why": {
        "fr": "Le profil et les paramètres ne sont pas encore équilibrés.",
        "en": "The profile and parameters are not yet balanced."},
    "sr.op.fallback.action": {
        "fr": "Suivre la première compensation listée plus bas.",
        "en": "Follow the first compensation listed below."},

    # _build_decision_summary
    "sr.summary.tip_missing.decision": {
        "fr": "Restaurer la pointe en fin de vis avant toute analyse.",
        "en": "Restore the tip at the end of the screw before any analysis."},
    "sr.summary.tip_missing.why": {
        "fr": "La pointe de sortie est absente du profil — c'est un élément physique obligatoire, non remplaçable.",
        "en": "The exit tip is missing from the profile — it is a mandatory physical element, not replaceable."},
    "sr.summary.tip_missing.action": {
        "fr": "Recharger une configuration de base : la pointe est automatiquement repositionnée en fin de vis.",
        "en": "Reload a base configuration: the tip is automatically repositioned at the end of the screw."},
    "sr.summary.ok.decision": {
        "fr": "Configuration validée — {n} éléments, vous pouvez lancer.",
        "en": "Configuration validated — {n} elements, you can proceed."},
    "sr.summary.ok.why": {
        "fr": "L'équilibre transport / mélange / chauffe est correct.",
        "en": "The transport / mixing / heating balance is correct."},
    "sr.summary.watch.decision": {
        "fr": "Garder {n} éléments mais surveiller le procédé.",
        "en": "Keep {n} elements but monitor the process."},
    "sr.summary.watch.why": {
        "fr": "Le profil tient, mais des points de vigilance subsistent.",
        "en": "The profile holds, but watch points remain."},
    "sr.summary.watch.action": {
        "fr": "Lancer un essai pilote court et surveiller débit + chauffe.",
        "en": "Launch a short pilot trial and monitor flow + heating."},
    "sr.summary.dedup": {
        "fr": "{action} (note : {count} {word} de pointe détecté(s) en amont, nettoyé(s) automatiquement).",
        "en": "{action} (note: {count} tip {word} detected upstream, cleaned automatically)."},
    "sr.summary.dedup_singular": {"fr": "doublon", "en": "duplicate"},
    "sr.summary.dedup_plural": {"fr": "doublons", "en": "duplicates"},

    # recommend_element_count — "why N is optimal" prose
    "sr.why.25": {
        "fr": "À {rpm} rpm × {feed} g/min × ρ={dens} g/cm³, prolonger la vis n'apporte pas de "
              "bénéfice mélange supplémentaire — la matière transite trop vite ou le profil est déjà "
              "saturé en convoyage. Une vis 25 maximise la capacité de production sans pénaliser "
              "l'homogénéité atteinte.",
        "en": "At {rpm} rpm × {feed} g/min × ρ={dens} g/cm³, extending the screw provides no "
              "additional mixing benefit — the material transits too fast or the profile is already "
              "saturated with conveying. A 25-element screw maximizes production capacity without "
              "penalizing achieved homogeneity."},
    "sr.why.30": {
        "fr": "Le profil courant ({n_mix} mélangeur(s), {n_conv} convoyage, FF {ff} %) à {rpm} rpm × "
              "{feed} g/min équilibre résidence et capacité. 30 éléments couvrent le besoin sans "
              "surdimensionner ni risquer la chauffe cumulée.",
        "en": "The current profile ({n_mix} mixer(s), {n_conv} conveying, FF {ff}%) at {rpm} rpm × "
              "{feed} g/min balances residence and capacity. 30 elements cover the need without "
              "oversizing or risking cumulative heating."},
    "sr.why.40": {
        "fr": "À {rpm} rpm × {feed} g/min × ρ={dens} g/cm³ avec {n_disp} mélangeurs dispersifs, "
              "le cisaillement cumulé sature une vis courte. 40 éléments donnent la marge nécessaire "
              "pour intercaler du convoyage de refroidissement entre les blocs de mélange — sécurise "
              "le liant SSB.",
        "en": "At {rpm} rpm × {feed} g/min × ρ={dens} g/cm³ with {n_disp} dispersive mixers, "
              "cumulative shear saturates a short screw. 40 elements provide the necessary margin "
              "to insert cooling conveying between mixing blocks — secures the SSB binder."},
    "sr.why.alt": {
        "fr": "Choisir {worst} ({label}) ferait perdre l'arbitrage : {detail}",
        "en": "Choosing {worst} ({label}) would lose the trade-off: {detail}"},
    "sr.why.intro_config": {
        "fr": "Configuration {n} éléments",
        "en": "{n}-element configuration"},

    # _build_why_enriched — French elision helper prefix
    "sr.enrich.prefix_de": {"fr": "de ", "en": "of "},
    "sr.enrich.prefix_d": {"fr": "d'", "en": "of "},

    # Systemic analysis rendering chrome
    "sr.sys.badge_ok": {"fr": "OK", "en": "OK"},
    "sr.sys.badge_watch": {"fr": "VIGILANCE", "en": "WATCH"},
    "sr.sys.badge_alert": {"fr": "ALERTE", "en": "ALERT"},
    "sr.sys.header_prefix": {"fr": "SYSTÈME", "en": "SYSTEM"},
    "sr.sys.trigger_label": {"fr": "DÉCLENCHEUR", "en": "TRIGGER"},
    "sr.sys.comp_label": {"fr": "COMPENSATION", "en": "COMPENSATION"},
    "sr.sys.comp_title": {"fr": "Compensations proposées", "en": "Proposed compensations"},
    "sr.sys.comp_sub": {"fr": "rééquilibrage du système", "en": "system rebalancing"},
    "sr.sys.no_comp": {
        "fr": "Aucune compensation requise — actions locales sans impact systémique majeur.",
        "en": "No compensation required — local actions without major systemic impact."},
    "sr.sys.checks_title": {
        "fr": "Vérification globale après recommandations",
        "en": "Global verification after recommendations"},
    "sr.sys.synthesis_prefix": {"fr": "PROFIL OPTIMISÉ", "en": "OPTIMIZED PROFILE"},

    # Axis assessment labels
    "sr.axis.dispersion": {"fr": "Dispersion", "en": "Dispersion"},
    "sr.axis.thermal": {"fr": "Thermique", "en": "Thermal"},
    "sr.axis.transport": {"fr": "Transport", "en": "Transport"},
    "sr.axis.capacity": {"fr": "Capacité", "en": "Capacity"},

    # Axis details
    "sr.axis.disp.balanced": {
        "fr": "équilibrée ({nk} mél., {ndist} distrib.)",
        "en": "balanced ({nk} mix., {ndist} distrib.)"},
    "sr.axis.disp.light": {
        "fr": "légère ({nk} mél. / {n} él.)",
        "en": "light ({nk} mix. / {n} el.)"},
    "sr.axis.disp.insufficient": {
        "fr": "insuffisante ({nk} mél. / {n} él.)",
        "en": "insufficient ({nk} mix. / {n} el.)"},
    "sr.axis.therm.no_overload": {
        "fr": "pas de surcharge ({nk} mél., zones réparties)",
        "en": "no overload ({nk} mix., zones spread)"},
    "sr.axis.therm.moderate": {
        "fr": "modérée ({nk} mél. concentrés)",
        "en": "moderate ({nk} mix. concentrated)"},
    "sr.axis.therm.excess": {
        "fr": "risque élevé ({nk} mél. à {rpm} rpm, max zone {max_t} s)",
        "en": "high risk ({nk} mix. at {rpm} rpm, max zone {max_t} s)"},
    "sr.axis.trans.maintained": {
        "fr": "maintenu ({nc} convoyage)",
        "en": "maintained ({nc} conveying)"},
    "sr.axis.trans.deficit": {
        "fr": "déficit ({nc} convoyage pour {nk} mélange)",
        "en": "deficit ({nc} conveying for {nk} mixing)"},
    "sr.axis.cap.target": {
        "fr": "dans la cible (FF {ff} %)",
        "en": "on target (FF {ff}%)"},
    "sr.axis.cap.saturated": {
        "fr": "saturation (FF {ff} %)",
        "en": "saturation (FF {ff}%)"},
    "sr.axis.cap.underfed": {
        "fr": "sous-alimentée (FF {ff} %)",
        "en": "underfed (FF {ff}%)"},
    "sr.axis.en_alerte": {"fr": "EN ALERTE", "en": "ALERT"},

    # Global checks
    "sr.check.coherence.label": {
        "fr": "Cohérence du profil global",
        "en": "Overall profile coherence"},
    "sr.check.coherence.ok": {
        "fr": "Ratio convoyage/mélange = {ratio}:1, équilibré.",
        "en": "Conveying/mixing ratio = {ratio}:1, balanced."},
    "sr.check.coherence.watch": {
        "fr": "Ratio convoyage/mélange = {ratio}:1 — {verdict}.",
        "en": "Conveying/mixing ratio = {ratio}:1 — {verdict}."},
    "sr.check.coherence.alert": {
        "fr": "Ratio convoyage/mélange = {ratio}:1 — {verdict}.",
        "en": "Conveying/mixing ratio = {ratio}:1 — {verdict}."},
    "sr.check.coherence.too_much_transport": {
        "fr": "trop de transport, mélange noyé",
        "en": "too much transport, mixing diluted"},
    "sr.check.coherence.too_much_mixing": {
        "fr": "trop de mélange, chauffe cumulée risquée",
        "en": "too much mixing, cumulative heating risk"},
    "sr.check.degrad.label": {
        "fr": "Risque dégradation aval",
        "en": "Downstream degradation risk"},
    "sr.check.degrad.ok": {
        "fr": "Résidence aval {t} s, mélange terminal modéré — pas de risque dégradation aval.",
        "en": "Downstream residence {t} s, terminal mixing moderate — no downstream degradation risk."},
    "sr.check.degrad.alert": {
        "fr": "Résidence aval {t} s avec {nk} kneading après {zone} — chauffe terminale risquée.",
        "en": "Downstream residence {t} s with {nk} kneading after {zone} — terminal heating risk."},
    "sr.check.fill.label": {
        "fr": "Fill regime",
        "en": "Fill regime"},
    "sr.check.fill.ok": {
        "fr": "FF {ff} % — remplissage dans la cible procédé.",
        "en": "FF {ff}% — fill within process target."},
    "sr.check.fill.saturated": {
        "fr": "FF {ff} % — vis saturée, risque surcouple.",
        "en": "FF {ff}% — screw saturated, over-torque risk."},
    "sr.check.fill.underfed": {
        "fr": "FF {ff} % — vis sous-alimentée, mélange peu efficace.",
        "en": "FF {ff}% — screw underfed, mixing inefficient."},

    # _build_compensations trigger/action/rationale (French trigger strings are internal keys)
    "sr.comp.knead_trigger": {
        "fr": "Réduction kneading {zone} ({n} mél.)",
        "en": "Reduce kneading {zone} ({n} mix.)"},
    "sr.comp.knead_action": {
        "fr": "Poser 1 distributif (toothed/special) en {target} pour homogénéiser sans ajout de chauffe.",
        "en": "Place 1 distributive (toothed/special) in {target} to homogenize without added heat."},
    "sr.comp.knead_rationale": {
        "fr": "Répartir le cisaillement entre {zone} et {target}, le distributif conserve l'homogénéité tout en restant froid — homogénéité globale maintenue.",
        "en": "Spread shear between {zone} and {target}, the distributive maintains homogeneity while staying cool — global homogeneity maintained."},
    "sr.comp.densify_trigger": {
        "fr": "Ajout de convoyage + densification vis",
        "en": "Add conveying + screw densification"},
    "sr.comp.densify_action": {
        "fr": "Ajouter du convoyage en {target} et ajuster le débit feeder pour maintenir FF dans la cible.",
        "en": "Add conveying in {target} and adjust feeder flow to keep FF within target."},
    "sr.comp.densify_rationale": {
        "fr": "La densification augmente le fill factor moyen ; l'ajustement débit en parallèle maintient le régime dans 30-55 %.",
        "en": "Densification increases average fill factor; parallel flow adjustment keeps the regime within 30-55%."},
    "sr.comp.flow_trigger": {
        "fr": "Réduction débit feeder",
        "en": "Reduce feeder flow"},
    "sr.comp.flow_action": {
        "fr": "Baisser le débit feeder de ~{pct} % et/ou monter la vis à ~{rpm_target} rpm pour rééquilibrer {target}.",
        "en": "Lower feeder flow by ~{pct}% and/or increase screw to ~{rpm_target} rpm to rebalance {target}."},
    "sr.comp.flow_rationale": {
        "fr": "La vis est saturée à FF {ff} % — réduire l'entrée ou accélérer le débit volumique pour redescendre dans la cible.",
        "en": "Screw saturated at FF {ff}% — reduce input or increase volumetric flow to return to target."},
    "sr.comp.reverse_trigger": {
        "fr": "Limitation des reverse à 1-2",
        "en": "Limit reverse to 1-2"},
    "sr.comp.reverse_action": {
        "fr": "Retirer {n_excess} reverse et poser du convoyage en {target} pour compenser la barrière.",
        "en": "Remove {n_excess} reverse and place conveying in {target} to compensate the barrier."},
    "sr.comp.reverse_rationale": {
        "fr": "Les reverse créent une barrière mécanique → surcouple + rétention. La compensation en convoyage restaure le transport sans perte de mélange.",
        "en": "Reverse elements create a mechanical barrier → over-torque + retention. Conveying compensation restores transport without mixing loss."},
    "sr.comp.move_trigger": {
        "fr": "Déplacement de 2-3 éléments depuis {zone} ({n} él.)",
        "en": "Move 2-3 elements from {zone} ({n} el.)"},
    "sr.comp.move_action": {
        "fr": "Étaler 2-3 éléments depuis {zone} vers {target} — pas de concentration > 4 par zone.",
        "en": "Spread 2-3 elements from {zone} to {target} — no concentration > 4 per zone."},
    "sr.comp.move_rationale": {
        "fr": "La concentration en {zone} crée un hotspot local ; la redistribution lisse la chauffe sans perdre de mélange.",
        "en": "Concentration in {zone} creates a local hotspot; redistribution smooths heating without losing mixing."},
    "sr.comp.dispersive_trigger": {
        "fr": "Ajout cisaillement dispersif terminal en {target}",
        "en": "Add terminal dispersive shear in {target}"},
    "sr.comp.dispersive_action": {
        "fr": "Poser 1 toothed/special en {target} pour finaliser la dispersion à l'échelle globale.",
        "en": "Place 1 toothed/special in {target} to finalize dispersion at global scale."},
    "sr.comp.dispersive_rationale": {
        "fr": "Le mélange est intense en amont (kneading) mais rien ne finalise l'homogénéisation avant la sortie.",
        "en": "Mixing is intense upstream (kneading) but nothing finalizes homogenization before the exit."},

    # Axis synthesis — additional detail variants
    "sr.axis.not_evaluable": {"fr": "non évaluable", "en": "not evaluable"},
    "sr.axis.disp.excessive": {
        "fr": "excessive ({pct} % du profil)",
        "en": "excessive ({pct}% of profile)"},
    "sr.axis.disp.no_distrib": {
        "fr": "locale OK mais finition distributive absente",
        "en": "local OK but no distributive finishing"},
    "sr.axis.therm.overload_downstream": {
        "fr": "surcharge Z{zone} + résidence aval {rt} s",
        "en": "overload Z{zone} + downstream residence {rt} s"},
    "sr.axis.therm.cumulative": {
        "fr": "cisaillement cumulé {nk} mél.",
        "en": "cumulative shear {nk} mix."},
    "sr.axis.therm.concentrated": {
        "fr": " — concentré Z{zone}",
        "en": " — concentrated Z{zone}"},
    "sr.axis.trans.undersized": {
        "fr": "sous-dimensionné ({nc} convoyage)",
        "en": "undersized ({nc} conveying)"},
    "sr.axis.trans.deficit_vs": {
        "fr": "déficitaire ({nc} conv. vs {nk} mél.)",
        "en": "deficit ({nc} conv. vs {nk} mix.)"},
    "sr.axis.cap.off_target": {
        "fr": "hors cible (FF {ff} %)",
        "en": "off-target (FF {ff}%)"},

    # Overall joining phrases
    "sr.axis.ok_join": {
        "fr": "{label} {word}",
        "en": "{label} {word}"},
    "sr.axis.watch_join": {
        "fr": "{label} à surveiller ({detail})",
        "en": "{label} to monitor ({detail})"},
    "sr.axis.alert_join": {
        "fr": "{label} EN ALERTE ({detail})",
        "en": "{label} ALERT ({detail})"},

    # Global checks — additional summary variants
    "sr.check.coherence.ok_full": {
        "fr": "Ratio convoyage/mélange = {ratio}:1, {ndist} distributif terminal — profil cohérent.",
        "en": "Conveying/mixing ratio = {ratio}:1, {ndist} terminal distributive — coherent profile."},
    "sr.check.coherence.no_distrib": {
        "fr": "{nk} dispersif sans distributif terminal — ajouter au moins 1 toothed/special en Z6-Z7.",
        "en": "{nk} dispersive without terminal distributive — add at least 1 toothed/special in Z6-Z7."},
    "sr.check.coherence.shear_dominant": {
        "fr": "cisaillement dominant, pas assez de transport",
        "en": "shear dominant, not enough transport"},
    "sr.check.balance.label": {
        "fr": "Équilibre transport / dispersion",
        "en": "Transport / dispersion balance"},
    "sr.check.balance.ok": {
        "fr": "Transport {pc} % vs mélange {pd} % — équilibre cohérent SSB.",
        "en": "Transport {pc}% vs mixing {pd}% — coherent SSB balance."},
    "sr.check.balance.watch": {
        "fr": "Transport {pc} % vs mélange {pd} % — déséquilibre modéré, rééquilibrer si essai pilote non concluant.",
        "en": "Transport {pc}% vs mixing {pd}% — moderate imbalance, rebalance if pilot trial inconclusive."},
    "sr.check.balance.alert": {
        "fr": "Transport {pc} % vs mélange {pd} % — {dom} dominant, profil déséquilibré.",
        "en": "Transport {pc}% vs mixing {pd}% — {dom} dominant, unbalanced profile."},
    "sr.check.degrad.ok_rt": {
        "fr": "Résidence aval {rt} s, mélange terminal modéré — pas de risque dégradation aval.",
        "en": "Downstream residence {rt} s, moderate terminal mixing — no downstream degradation risk."},
    "sr.check.degrad.alert_rt": {
        "fr": "Résidence aval {rt} s × {nk} mélangeurs Z6-Z7 — chauffe cumulée, dégradation liant probable (PVDF/PEO).",
        "en": "Downstream residence {rt} s × {nk} mixers Z6-Z7 — cumulative heating, binder degradation likely (PVDF/PEO)."},
    "sr.check.degrad.watch_rt": {
        "fr": "Résidence aval {rt} s × {nk} mélangeurs Z6-Z7 — surveillance thermique recommandée.",
        "en": "Downstream residence {rt} s × {nk} mixers Z6-Z7 — thermal monitoring recommended."},
    "sr.check.degrad.ok_no_rt": {
        "fr": "Mélange terminal modéré ({nk} él. Z6-Z7) — pas de risque dégradation aval identifié.",
        "en": "Moderate terminal mixing ({nk} el. Z6-Z7) — no downstream degradation risk identified."},
    "sr.check.degrad.watch_no_rt": {
        "fr": "{nk} mélangeurs en Z6-Z7 — surveiller la chauffe terminale (résidence non fournie).",
        "en": "{nk} mixers in Z6-Z7 — monitor terminal heating (residence not provided)."},
    "sr.check.fill.ok_target": {
        "fr": "FF {ff} % dans la cible procédé (30-55 %).",
        "en": "FF {ff}% within process target (30-55%)."},
    "sr.check.fill.alert_underfed": {
        "fr": "FF {ff} % — vis sous-alimentée, mélange peu efficace.",
        "en": "FF {ff}% — screw underfed, mixing inefficient."},
    "sr.check.fill.alert_saturated": {
        "fr": "FF {ff} % — saturation, risque surcouple et chauffe par friction.",
        "en": "FF {ff}% — saturation, over-torque risk and friction heating."},
    "sr.check.fill.watch_off": {
        "fr": "FF {ff} % — hors cible (30-55 %), ajustement débit feeder ou rpm recommandé.",
        "en": "FF {ff}% — off target (30-55%), feeder flow or rpm adjustment recommended."},

    # Compensations — display text (format-ready)
    "sr.comp.knead_trigger_fmt": {
        "fr": "Réduction kneading Z{zone} ({n} mél.)",
        "en": "Reduce kneading Z{zone} ({n} mix.)"},
    "sr.comp.knead_action_fmt": {
        "fr": "Ajouter 1 × **Denté** (type 11) ou **Mélange spécial** (type 12) en **Z{target}** pour récupérer la dispersion perdue sans ajouter de chauffe.",
        "en": "Add 1 × **Toothed** (type 11) or **Special mix** (type 12) in **Z{target}** to recover lost dispersion without added heat."},
    "sr.comp.knead_rationale_fmt": {
        "fr": "Le distributif terminal compense la baisse de cisaillement amont tout en restant froid — homogénéité globale maintenue.",
        "en": "The terminal distributive compensates the upstream shear reduction while staying cool — global homogeneity maintained."},
    "sr.comp.densify_trigger_fmt": {
        "fr": "Ajout de {n} éléments (densification)",
        "en": "Add {n} elements (densification)"},
    "sr.comp.densify_verdict_in": {
        "fr": "dans la cible 30-55 %",
        "en": "within target 30-55%"},
    "sr.comp.densify_verdict_above": {
        "fr": "au-dessus de la cible 30-55 %",
        "en": "above target 30-55%"},
    "sr.comp.densify_verdict_below": {
        "fr": "en-dessous de la cible 30-55 %",
        "en": "below target 30-55%"},
    "sr.comp.densify_ff_change": {
        "fr": "FF passerait de {ff0} % à ~{ff1} % ({verdict}).",
        "en": "FF would go from {ff0}% to ~{ff1}% ({verdict})."},
    "sr.comp.densify_action_fmt": {
        "fr": "Avant d'ajouter {n} éléments : {verdict} {adjust}",
        "en": "Before adding {n} elements: {verdict} {adjust}"},
    "sr.comp.densify_adjust_free": {
        "fr": "Ajustement libre.",
        "en": "Free adjustment."},
    "sr.comp.densify_adjust_flow": {
        "fr": "Ajuster le débit feeder ({feed} g/min) en parallèle pour rester dans la cible.",
        "en": "Adjust feeder flow ({feed} g/min) in parallel to stay within target."},
    "sr.comp.densify_rationale_fmt": {
        "fr": "Ajouter des éléments augmente le FF moyen — vérifier qu'on reste dans la plage cible procédé.",
        "en": "Adding elements increases average FF — verify the process target range is maintained."},
    "sr.comp.flow_trigger_fmt": {
        "fr": "Réduction débit feeder {feed0} → ~{feed1} g/min",
        "en": "Reduce feeder flow {feed0} → ~{feed1} g/min"},
    "sr.comp.flow_action_fmt": {
        "fr": "Vérifier que le mélange amont (Z2-Z3) n'est pas surchargé : avec {rpm0} → ~{rpm1} rpm, la résidence baisse aussi. Si Z2-Z3 contient déjà ≥ 3 mélangeurs, retirer 1 kneading pour éviter la chauffe cumulée.",
        "en": "Verify upstream mixing (Z2-Z3) is not overloaded: with {rpm0} → ~{rpm1} rpm, residence drops too. If Z2-Z3 already has ≥ 3 mixers, remove 1 kneading to avoid cumulative heating."},
    "sr.comp.flow_rationale_fmt": {
        "fr": "Une baisse débit + hausse rpm rééquilibre le FF mais modifie la résidence locale — ajuster le mélange en parallèle évite un nouveau hotspot.",
        "en": "A flow reduction + rpm increase rebalances FF but changes local residence — adjusting mixing in parallel avoids a new hotspot."},
    "sr.comp.reverse_trigger_fmt": {
        "fr": "Limitation des reverse à 1-2 (actuellement {n})",
        "en": "Limit reverse to 1-2 (currently {n})"},
    "sr.comp.reverse_action_fmt": {
        "fr": "Ajouter 1-2 × **Convoyage +** (type 1) en **Z{target}** pour relancer le débit sortie. Sans rétention compensée, le débit ({feed} g/min) peut fluctuer.",
        "en": "Add 1-2 × **Conveying +** (type 1) in **Z{target}** to restore output flow. Without compensated retention, flow ({feed} g/min) may fluctuate."},
    "sr.comp.reverse_rationale_fmt": {
        "fr": "Le reverse retient la matière — en supprimer plusieurs sans ajouter de transport baisse le débit en sortie.",
        "en": "Reverse retains material — removing several without adding transport reduces output flow."},
    "sr.comp.move_trigger_fmt": {
        "fr": "Déplacement de 2-3 éléments depuis Z{zone} ({n} él.)",
        "en": "Move 2-3 elements from Z{zone} ({n} el.)"},
    "sr.comp.move_action_fmt": {
        "fr": "Vérifier que **Z{dst}** ({n_dst} él.) accepte la redistribution sans dépasser 5-6 éléments. Sinon, étaler aussi sur Z{alt}.",
        "en": "Verify **Z{dst}** ({n_dst} el.) accepts redistribution without exceeding 5-6 elements. Otherwise, spread to Z{alt} too."},
    "sr.comp.move_rationale_fmt": {
        "fr": "Le rééquilibrage spatial doit éviter de créer un nouveau hotspot — répartir sur 2 zones si besoin.",
        "en": "Spatial rebalancing must avoid creating a new hotspot — spread across 2 zones if needed."},
    "sr.comp.nodistrib_trigger": {
        "fr": "Cisaillement dispersif important sans finition distributive",
        "en": "High dispersive shear without distributive finishing"},
    "sr.comp.nodistrib_action": {
        "fr": "Ajouter 1 × **Denté** (type 11) en Z6 ou Z7 — sans cela, la dispersion locale n'est pas diffusée à l'échelle globale (homogénéité du film final compromise).",
        "en": "Add 1 × **Toothed** (type 11) in Z6 or Z7 — without this, local dispersion is not spread at global scale (final film homogeneity compromised)."},
    "sr.comp.nodistrib_rationale": {
        "fr": "Dispersif et distributif sont complémentaires — supprimer du dispersif sans poser un distributif aval dégrade l'homogénéité finale.",
        "en": "Dispersive and distributive are complementary — removing dispersive without placing a downstream distributive degrades final homogeneity."},

    # Trade-off prose
    "sr.trade.knead": {
        "fr": "Réduire le kneading {zone} diminue le cisaillement local (dispersion −30 % env.) mais le distributif posé en {target} compense l'homogénéité globale. Compromis acceptable : on perd un peu de dispersion fine pour gagner en sécurité thermique du liant.",
        "en": "Reducing kneading {zone} lowers local shear (dispersion −30% approx.) but the distributive placed in {target} compensates global homogeneity. Acceptable trade-off: some fine dispersion is lost for binder thermal safety."},
    "sr.trade.densify": {
        "fr": "Densifier la vis ({trigger}) améliore le mélange et l'utilisation longueur, mais augmente le FF moyen. {detail} Compromis selon priorité : qualité mélange (densifier) vs capacité production (garder court).",
        "en": "Densifying the screw ({trigger}) improves mixing and length utilization, but increases average FF. {detail} Trade-off by priority: mixing quality (densify) vs production capacity (keep short)."},
    "sr.trade.reverse": {
        "fr": "Limiter les reverse améliore le débit sortie et baisse le couple, mais réduit la rétention donc le temps de séjour utile au mélange. Compromis : on accepte un mélange un peu moins long contre une stabilité débit/qualité, le convoyage aval restaure la stabilité de sortie.",
        "en": "Limiting reverse improves output flow and reduces torque, but lowers retention and thus useful residence time for mixing. Trade-off: slightly shorter mixing is accepted for flow/quality stability, downstream conveying restores output stability."},
    "sr.trade.flow": {
        "fr": "Baisser le débit feeder (et/ou monter la rpm) sort la vis de saturation et protège du surcouple, mais réduit la capacité de production et raccourcit la résidence — vérifier que le mélange amont reste suffisant. Compromis sécurité procédé vs throughput.",
        "en": "Lowering feeder flow (and/or increasing rpm) takes the screw out of saturation and protects against over-torque, but reduces production capacity and shortens residence — verify upstream mixing remains sufficient. Trade-off: process safety vs throughput."},
    "sr.trade.latent": {
        "fr": "{nk} mélangeurs dispersifs offrent une dispersion fine mais concentrent le cisaillement et la chauffe. Surveiller la température liant ; intercaler du convoyage si la résidence longue est confirmée.",
        "en": "{nk} dispersive mixers offer fine dispersion but concentrate shear and heat. Monitor binder temperature; interleave conveying if long residence is confirmed."},
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
