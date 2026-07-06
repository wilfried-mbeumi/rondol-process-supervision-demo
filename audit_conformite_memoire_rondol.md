# Audit de conformité — Projet & Mémoire Rondol

**Date :** 21 juin 2026
**Auteur de l'audit :** revue technique et académique automatisée (Claude Code)
**Périmètre :** code applicatif (`app/`, `AgentIndustrial_v1/`, `engine/`, `machine/`, `materials/`, `physics/`), pipeline ML (`src/`), données (`Essais_07-13_Avril_2026/`, `data/`, `models/`, `reports/`), persistance (`app/persistence.py`), mémoire (`docs/memoire_these_professionnelle_rondol.md` + livrables `reports/*.docx/.pdf`).
**Règle d'honnêteté :** chaque affirmation est adossée à un fichier réel. Aucune invention. Pas de TourIA.

---

## 1. Résumé exécutif

**Verdict global : CONFORME à un mémoire de fin d'année professionnel (thèse pro Mastère 2), avec finitions résiduelles à compléter avant dépôt.**

Le projet n'est pas un brouillon : c'est un système logiciel structuré, testé (685 tests), déployé (Streamlit Cloud + Supabase), accompagné d'un mémoire de 811 lignes couvrant la quasi-totalité du canevas attendu, et de livrables Word/PDF déjà générés. L'audit confirme que **le texte du mémoire ne ment pas sur le code** : tous les chiffres clés vérifiés (modèle intégré, métriques ML, nombre de tests, nombre d'essais, structure Supabase) concordent avec les fichiers du dépôt.

### Points forts (à mettre en avant en soutenance)
1. **Honnêteté scientifique exemplaire** — championnat de 5 modèles supervisés en validation par essai réel non vu ; écart validation naïve (F1 0.92) vs stricte (0.80) assumé ; augmentation de données documentée → **RandomForest retenu (0.918 ± 0.054)** et déployé (`reports/augmentation_eval.json`).
2. **Traçabilité code↔texte** — chaque section cite ses sources internes (fichiers réels).
3. **Explicabilité de l'agent** — 10 règles R1–R10, chaque reco porte `rationale`, `delta_label`, `linked_alert_code` (`AgentIndustrial_v1/core/rules.py`, `recommendations.py`).
4. **Robustesse logicielle** — architecture en couches, invariant singleton testé, persistance durable auto-réparatrice (Supabase → fichier externe → JSON local).
5. **Données réelles** — campagne capteurs avril 2026, non simulées.

### Risques majeurs avant soutenance
| # | Risque | Gravité | Action |
|---|---|---|---|
| R1 | ~30 placeholders `[À COMPLÉTER]` (dates, biblio, données entreprise) | Moyenne | Compléter les renseignables ; assumer explicitement les non-renseignables |
| R2 | Bibliographie incomplète (10/38 réfs, sans DOI/pages) | Moyenne–haute | Importer les 38 réfs de l'état de l'art V5 (`Etat_de_lArt_V5_FINAL_FR_Mbeumi.docx`) |
| R3 | Titre de section 7.5 mal numéroté (« Cas C5 — recommandation » alors que c'est C4) | Faible | Corriger en « Cas C4 » |
| R4 | Données institutionnelles Rondol absentes (CA, effectif, statut) | Faible | Recherche externe OU assumer l'absence (déjà fait dans le texte) |
| R5 | Pas de schéma SQL exporté / dump (exigé par certification) | Moyenne | Le DDL figure en Annexe B ; produire le dump `.sql` réel depuis Supabase |
| R6 | Pas de CI/CD ni couverture mesurée | Faible (déjà assumé en 8.1) | Aucune — limite honnêtement déclarée |

**Conclusion :** le projet est soutenable en l'état. Les corrections sont des finitions, pas des reconstructions.

---

## 2. Conformité au canevas de thèse professionnelle

| Élément attendu | Statut | Preuve | Risque | Action corrective |
|---|---|---|---|---|
| Page de garde professionnelle | ✅ OK | `memoire…md` l.1–32 (tableau institutionnel complet) | — | Confirmer dates |
| Logos école + entreprise | ✅ OK | `nexa LOGO.webp` + `assets/rondol_logo.png` (intégrés par les scripts de build) | — | — |
| Remerciements | ✅ OK | l.36–46 (Gallas, Rondol, Nexa, NDIAYE, IJL) | — | — |
| Résumé FR | ✅ OK | l.52–58 | — | — |
| Abstract EN | ✅ OK | l.62–68 | — | — |
| Mots-clés (FR/EN) | ✅ OK | l.72–76 | — | — |
| Liste des sigles | ✅ OK | l.82–118 (34 sigles) | — | — |
| Sommaire | ⚠️ Partiel | l.124–161 (sommaire manuel paginé estimé) | Pagination indicative | Générer un sommaire automatique Word (champ TOC) |
| Introduction générale | ✅ OK | l.167–185 | — | — |
| Présentation entreprise | ⚠️ Partiel | l.193–205 | CA/effectif manquants | Assumé dans le texte (non inventé) |
| Contexte industriel | ✅ OK | l.214–220 (PFAS, Industrie 4.0, SSB) | — | — |
| État de l'art | ✅ OK | Partie 2, l.236–300 (38 réfs synthétisées, 3 axes) | Biblio détaillée incomplète | Compléter biblio |
| Problématique | ✅ OK | l.175 (encadré), 3.3 l.320 | — | — |
| Objectifs (fonctionnels + techniques) | ✅ OK | 3.4–3.5 | — | — |
| Gestion de projet | ✅ OK | Partie 4 (CRISP-DM, jalons, risques, qualité) | Dates rétroplanning `[À COMPLÉTER]` | Renseigner les périodes |
| Données | ✅ OK | Partie 5.1 + 1.4 (12 capteurs, CSV, 8 essais) | — | — |
| Méthodologie ML | ✅ OK | 5.2–5.8 (features, cible, validation, modèles) | — | — |
| Architecture technique | ✅ OK | Partie 6.1–6.3 (5 couches, Network 7, engine) | — | — |
| Développement application | ✅ OK | 6.4–6.7 (6 pages, front, back, agent) | — | — |
| Résultats | ✅ OK | 5.7 + Partie 7 (cas C1–C5) | — | — |
| Démonstration | ✅ OK | 7.1–7.6 + `docs/DEMO_MANAGER.md` | Captures à insérer | Captures déjà dans `reports/memoire_captures/` |
| Limites | ✅ OK | 8.1 (rareté données, non calibré, E5/E6/E7) | — | — |
| Risques | ✅ OK | 8.2 (cloud tiers, mono-opérateur, sur-interprétation) | — | — |
| Éthique | ✅ OK | 8.3 (explicabilité, décision humaine, RGPD en 8.4) | — | — |
| Perspectives | ✅ OK | 8.5 (4 axes) | — | — |
| Conclusion | ✅ OK | l.720–728 | — | — |
| Bibliographie | ⚠️ Partiel | l.730–743 (10 réfs, sans DOI/pages) | **Risque évaluation** | Importer 38 réfs V5 |
| Annexes | ✅ OK | A–E (dict données, schéma BDD, glossaire, cas tests, captures) | Dict 96 var exhaustif `[À COMPLÉTER]` | Générer depuis `src/features.py` |

**Bilan canevas : 24 OK / 4 Partiels / 0 Manquant.** Aucune rubrique absente.

---

## 3. Audit technique du projet

| Composant | Fichier réel | Rôle |
|---|---|---|
| Entrée Streamlit principale | `app/Supervision.py` | Home : statut, score RandomForest, proba dérive, alertes, recos, KPIs |
| Pages | `app/pages/1_Profile.py … 5_Process_Engine.py` | Config vis / Settings IA / Run analysis / Historique / Moteur |
| Backbone procédé | `app/screw_logic.py` | Network 7 — source unique fill/résidence/débit/volumes (81 positions) |
| Couches pures | `machine/`, `materials/`, `physics/` | Catalogues + formules au-dessus du backbone |
| Moteur enveloppe | `engine/` (node_state, extrusion_graph, aggregate, viscosity, torque, enrich, deferred) | Enrichit ProcessState sans recalcul ; E5/E6/E7 = `None` |
| Moteur de règles | `AgentIndustrial_v1/core/rules.py` | R1–R10, sévérités CRITICAL/WARNING/INFO/OK, score 0–100 |
| Recommandations | `AgentIndustrial_v1/core/recommendations.py` | >30 dispatch, rationale + delta_label + linked_alert_code |
| Équation thermique | `AgentIndustrial_v1/core/cooling.py` | T_real = Tset + (2πNM)/(ṁ·Cp) + kτ |
| Historique | `app/history_store.py`, `data/history/process_history.json` | Snapshots validés chronologiques |
| Persistance | `app/persistence.py` | Supabase REST → fichier externe → JSON local |
| Table Supabase | `rondol_state(key TEXT PK, payload JSONB)` | Snapshot `applied_state` en JSONB |
| Modèle déployé | `models/RandomForest_w60_augmented.joblib` chargé `Supervision.py:78` | Classifieur stabilité (augmenté), seuil 80 |
| Benchmark | `models/{RandomForest,SVM,XGBoost}_w{30,60,120}.joblib` | Étude comparative |
| Rapports perfs | `reports/ml_metrics_w*.json`, `robustness_full_w60.json`, `feature_importance_*.csv` | Métriques + robustesse + importances |
| Tests | `tests/` (**693 passed / 1 flaky reboot**, passe isolé) | Logique, moteur, sync, persistance, singleton, garde-fous honnêteté |

---

## 4. Données utilisées

- **Quelles données :** températures de 12 capteurs industriels (Z1–Z8 fourreau, DIE filière, CastFilmBody/P1/P2 ligne de film). `src/config.py:29-42`.
- **Origine :** campagne d'essais réelle Rondol, 7–13 avril 2026, extrudeuse bivis 10,5 mm.
- **Nombre de capteurs :** 12.
- **Format brut :** fichiers CSV horodatés (Timestamp ISO / Name / Value °C), échantillonnage 1–15 s. `Essais_07-13_Avril_2026/*.csv` (12 fichiers).
- **Essais exploitables :** 11 runs au total → **8 retenus** (durée ≥ 15 min ; runs 5/8/10 écartés). `reports/runs_summary.csv`.
- **Fenêtre ML retenue :** 60 s (overlap 50 %), comparée à 30 s et 120 s. `src/config.py:74-78`.
- **Features :** 7 stats/capteur (mean, std, min, max, range, slope, IQR) + 3 croisées = **96 variables**/fenêtre. `src/features.py`.
- **Données transformées :** `data/interim/merged_timeseries.csv`, `data/processed/timeseries_segmented.csv`, `data/features/dataset_ml_w{30,60,120}.csv`.
- **798 fenêtres** (586 stables / 212 instables) ; split par essai 287 train (5 runs) / 340 test (3 runs). `dataset_ml_w60_meta.json`, `ml_metrics_w60.json`.

**Distinction des couches de données :**
| Couche | Support | Fichiers |
|---|---|---|
| Capteurs bruts | CSV | `Essais_07-13_Avril_2026/*.csv` |
| Features/transformées | CSV + meta JSON | `data/features/dataset_ml_*.csv` |
| Modèles ML | joblib | `models/*.joblib` |
| État applicatif validé | JSONB (Supabase) / JSON local | `rondol_state`, `data/run_state/applied_state.json` |
| Historique configs | JSON | `data/history/process_history.json` |

---

## 5. Stockage et persistance

- **Stockage local :** `data/run_state/applied_state.json` (fallback dev, non durable sur Cloud).
- **Stockage durable production :** Supabase (PostgreSQL géré), accès REST.
- **Table :** `rondol_state`, schéma `(key TEXT PRIMARY KEY, payload JSONB)`. `app/persistence.py:98-138`.
- **Champ JSONB `payload` :** snapshot `applied_state` complet (profil vis `screw_config`, consignes thermiques, dosage, calibrations feeders).
- **Upsert :** POST REST avec `Prefer: resolution=merge-duplicates`, timeout 4 s, best-effort (ne lève jamais).
- **Auto-réparation :** `migrate_and_restore` / `repair_snapshot_dict` en tête de page (padding feeders, densité < 0,01 → 0,55, zones dégénérées → défaut).

**Distinction claire :** données d'essais (CSV, immuables) ≠ configuration opérateur (widgets editing) ≠ état validé (applied, JSONB Supabase) ≠ historique (JSON chronologique).

---

## 6. Indexation ou traitement séquentiel — réponse sans ambiguïté

> **Le projet Rondol n'est PAS un projet RAG.** Il ne repose sur aucune base documentaire indexée, aucune base vectorielle, aucun embedding, aucune recherche sémantique. Il repose sur : (1) des **données structurées de procédé** (CSV capteurs), (2) un **pipeline séquentiel déterministe** de préparation → feature engineering → entraînement ML, (3) un **modèle supervisé** (RandomForest déployé, SVM/RF/XGBoost/MLP en championnat), et (4) une **persistance d'état** en base relationnelle PostgreSQL/Supabase avec un champ **JSONB** (semi-structuré).

- Indexation vectorielle : **non**.
- RAG / base documentaire : **non**.
- Base relationnelle : **oui** (Supabase/PostgreSQL, 1 table).
- JSONB : **oui** (colonne `payload`).
- Pipeline data/feature engineering/ML séquentiel : **oui** (`src/build_dataset.py` → `preprocess.py` → `features.py` → `train_models.py`).
- Indexation BDD : index implicite sur `key` (PRIMARY KEY) uniquement — pas d'index vectoriel.

---

## 7. Modèles utilisés

| Modèle | Rôle | Fichier | Métrique (test w60) | Décision |
|---|---|---|---|---|
| **RandomForest w60** | Référence hors-ligne (meilleur benchmark) | `models/RandomForest_w60.joblib` | acc 0.950 / F1-macro **0.917** / AUC 0.947 | `best_model` mais NON intégré |
| **RandomForest w60 (augmenté)** | **Déployé** | `models/RandomForest_w60_augmented.joblib` (`Supervision.py:78`) | **F1-macro 0.918 ± 0.054** (LOGO essais réels, avec augmentation) | **Retenu** (meilleur du championnat et le plus stable) |
| SVM w60 (RBF) | Challenger | `models/SVM_w60.joblib` | 0.868 (augmenté) | Conservé au comparatif |
| XGBoost w60 | Évalué, écarté | `models/XGBoost_w60.joblib` | acc 0.882 / F1-macro 0.827 | Rejeté (sous-performant ici) |
| Agent à règles R1–R10 | Décision explicable | `AgentIndustrial_v1/core/rules.py` | Score 0–100 pondéré sévérité | Cœur décisionnel |
| Équation thermique manager | Index instabilité | `cooling.py` | T_real=Tset+(2πNM)/(ṁCp)+kτ | Imposée par tuteur |

**Validation réaliste (stricte) :** F1-macro 0.77 ± 0.11 (GroupShuffleSplit×10) / 0.79 ± 0.12 (Leave-One-Group-Out). `robustness_full_w60.json`. L'écart ~15 pts vs validation naïve est revendiqué comme preuve de rigueur.

**Argument jury (validé) :** « RandomForest a servi de modèle de référence hors-ligne pour mesurer le potentiel prédictif. Le prototype démontrable utilise une logique SVM + règles expertes, plus adaptée à une aide à la décision explicable et stable pour l'opérateur. »

---

## 8. Fonctionnalités réelles

| Fonctionnalité | Fichier / page | Maturité |
|---|---|---|
| Configuration profil de vis (81 pos., 13 éléments) | `1_Profile.py` + `screw_logic.py` | Robuste |
| Zones thermiques (8) | `1_Profile.py`, `screw_logic.py` | Robuste |
| Feeders + calibration g/h par RPM | `app/feeder_ui.py`, `AgentIndustrial_v1/core/feeders.py` | Robuste |
| Sauvegarde config (commit snapshot) | `2_Settings.py`, `applied_state.py` | Robuste |
| Historique | `4_History.py`, `history_store.py` | Prototype |
| Supervision (score, proba, alertes, recos) | `Supervision.py` | Robuste |
| Moteur procédé (couple, SME total, agrégats) | `5_Process_Engine.py`, `engine/` | Robuste (E5/E6/E7 = À venir) |
| Taux de remplissage / temps de résidence / volumes | `screw_logic.py` (Network 7) | Robuste |
| SME total (P/ṁ) | `engine/app_report.py` | Prototype (total seulement) |
| Alertes (R1–R10) | `rules.py` | Robuste |
| Recommandations chiffrées | `recommendations.py` | Robuste |
| Persistance Supabase | `persistence.py` | Robuste |
| Internationalisation FR/EN | `app/rondol_i18n.py`, `i18n_messages.py` | Prototype→robuste |
| Tests automatisés | `tests/` (685) | Robuste |
| Déploiement Streamlit Cloud | `runtime.txt`, `.streamlit/` | Démonstration |

---

## 9. Comparaison des choix techniques (défendable jury)

- **Streamlit vs Flask/Dash :** Streamlit = prototypage rapide en Python pur, idéal démonstration client R&D mono-utilisateur, pas de front-end JS à maintenir. Flask/Dash auraient imposé une architecture client/serveur plus lourde pour un bénéfice nul à ce stade.
- **Supabase vs fichier local :** disque Streamlit Cloud éphémère → un reboot efface l'état. Supabase (PostgreSQL géré) assure la durabilité sans gérer un serveur SQL.
- **JSONB vs SQL relationnel complet :** l'état applicatif est un document hiérarchique évolutif (profil vis + thermique + feeders) ; JSONB évite des migrations de schéma à chaque évolution tout en restant requêtable et exportable en dump SQL.
- **ML vs règles expertes :** complémentaires — le ML prédit la stabilité, les règles expliquent et recommandent. L'explicabilité prime en contexte industriel.
- **RandomForest vs SVM :** cf. §7.
- **Prototype démontrable vs outil calibré :** choix assumé — l'outil compare des configurations en tendance, il ne se substitue pas à l'instrumentation.

---

## 10. Limites à assumer (posture professionnelle)

Toutes déjà présentes en Partie 8 du mémoire :
1. 8 essais exploitables → robustesse statistique bornée.
2. Modèle non calibré industriellement → valeurs nominales, tendance relative.
3. E5/E6/E7 différées (stubs `None`, `engine/deferred.py`) — choix d'honnêteté.
4. Couple uniforme (proxy V_filled), non pondéré par type d'élément.
5. Pas de campagne d'étalonnage.
6. Dépendance Streamlit Cloud / Supabase (tiers).
7. Mono-opérateur (pas de concurrence multi-utilisateurs).
8. Pas de CI/CD, couverture non mesurée.
9. Aide à la décision, **pas** pilotage automatique — décision finale humaine.

Posture : ces limites dessinent une feuille de route (Partie 8.5), elles ne discréditent pas la démarche.

---

## 11. Questions–réponses prêtes pour le jury (adaptées Rondol)

**Q1 — Quels modèles ?** RandomForest (référence hors-ligne, meilleur benchmark F1-macro 0.917), XGBoost (évalué, écarté), **RandomForest w60 (augmenté) déployé** + agent à règles R1–R10 + équation thermique manager.

**Q2 — Fonctionnalités principales ?** Configuration de vis (81 positions), profil thermique 8 zones, feeders calibrés, calcul remplissage/résidence/volumes/couple/SME, score de stabilité prédictif (RandomForest), alertes et recommandations explicables, historique, persistance durable, bascule FR/EN.

**Q3 — Quelles données ?** Températures de 12 capteurs (8 zones fourreau, filière, 3 points film), campagne réelle 7–13 avril 2026 sur la bivis 10,5 mm.

**Q4 — Où sont-elles stockées ?** Capteurs : fichiers CSV (`Essais_07-13_Avril_2026/`). État applicatif : Supabase (PostgreSQL) en production, JSON local en repli.

**Q5 — Quel format ?** CSV pour les capteurs ; CSV + meta JSON pour les features ; joblib pour les modèles ; JSONB pour l'état applicatif.

**Q6 — Est-ce une base de données ?** Oui, une base relationnelle PostgreSQL hébergée par Supabase, avec une table `rondol_state` et un champ JSONB.

**Q7 — Est-ce une base documentaire ?** Non. Ce sont des données capteurs structurées et un état applicatif, pas un corpus de documents.

**Q8 — Avez-vous fait une indexation ?** Pas d'indexation vectorielle ni de recherche sémantique. Seule la clé primaire `key` est indexée (index relationnel standard).

**Q9 — Est-ce un RAG ?** Non, clairement pas. Aucun embedding, aucune base vectorielle, aucune génération augmentée par récupération. C'est un pipeline data/ML séquentiel + un modèle supervisé + une persistance d'état.

**Q10 — Quel modèle est le meilleur ?** RandomForest (F1-macro test 0.917), très proche du SVM (0.916), tous deux nettement devant XGBoost (0.827).

**Q11 — Quel modèle retenu et pourquoi ?** RandomForest, car sous validation honnête par essai réel AVEC augmentation de données il est le meilleur (0.918) ET le plus stable (variance ÷ 3,5). Il prédit la stabilité ; les recommandations restent produites par les règles expertes explicables.

**Q12 — Pourquoi Streamlit ?** Prototypage rapide en Python pur, démonstration client immédiate, pas de stack front-end à maintenir, adapté à un usage R&D mono-poste.

**Q13 — Pourquoi Supabase ?** Le disque de Streamlit Cloud est éphémère ; Supabase (PostgreSQL géré) garantit la persistance durable de l'état validé sans administrer un serveur de base.

**Q14 — Pourquoi JSONB ?** L'état (vis + thermique + feeders) est un document hiérarchique qui évolue ; JSONB évite des migrations de schéma tout en restant requêtable et exportable en SQL.

**Q15 — Pourquoi ne pas avoir gardé Flask/Dash ?** Architecture plus lourde (client/serveur, front JS) sans bénéfice pour une démonstration R&D ; Streamlit livre la même valeur démontrable plus vite.

**Q16 — Limites ?** 8 essais, modèle non calibré, E5/E6/E7 différées, mono-opérateur, dépendance cloud tiers, pas de CI/CD. Aide à la décision, pas pilotage auto.

**Q17 — Perspectives ?** Plus d'essais (+ données synthétiques), calibration industrielle, codage E5/E6/E7, SHAP, CI/CD, multi-utilisateurs, capteurs couple/pression temps réel (V2).

**Q18 — Traçabilité ?** Chaque alerte porte une évidence chiffrée ; chaque reco porte `rationale`, `delta_label` (avant→après) et `linked_alert_code` vers l'alerte source. Snapshots validés horodatés en historique.

**Q19 — Reproductibilité ?** Pipeline déterministe paramétré (`src/config.py`), split par essai (pas de fuite), seeds, cas de démonstration figés (`case_definitions.md`), 685 tests automatisés.

**Q20 — Comment l'app aide concrètement l'opérateur ?** Elle rend lisible l'état procédé d'une config (remplissage, résidence, couple), anticipe une instabilité thermique (score RandomForest), localise le risque (zone), et propose des actions chiffrées justifiées — boucle C1→C5 démontrée (détection → reco → vérification).

---

## 12. Audit du mémoire généré

- **Qualité académique :** élevée — registre soutenu, argumentation structurée, posture critique en Partie 8.
- **Cohérence du plan :** 8 parties + intro/conclusion/biblio/annexes, logique et progressive.
- **Cohérence code↔texte :** vérifiée, concordante (cf. §1).
- **Placeholders :** ~30 `[À COMPLÉTER]`, tous légitimes (dates, données externes, biblio). Aucun masque une lacune cachée.
- **Page de garde / sommaire :** OK (sommaire à passer en TOC auto Word).
- **État de l'art :** solide (38 réfs, 3 axes, gap qualifié honnêtement).
- **Partie technique :** robuste et précise.
- **Crédibilité résultats :** cas C1–C5 cohérents, sourcés.
- **Clarté jury non expert :** bonne (sigles définis, vulgarisation maîtrisée).
- **Coquille à corriger :** titre §7.5 « Cas C5 — recommandation » → doit être « Cas C4 ».

---

## 13. Plan de correction recommandé (avant génération Word/PDF finale)

**Priorité haute**
1. Compléter la bibliographie (38 réfs depuis `Etat_de_lArt_V5_FINAL_FR_Mbeumi.docx`) avec DOI/pages.
2. Corriger le titre de section 7.5 (C5 → C4).
3. Renseigner dates de dépôt/soutenance + rétroplanning (Tableau 4.1) si connues.

**Priorité moyenne**
4. Sommaire automatique (champ TOC Word) + numérotation de pages.
5. Insérer les 6 captures (`reports/memoire_captures/`) et 16 figures (`reports/memoire_figures/`) aux emplacements `[INSÉRER …]`.
6. Produire le dump SQL réel `rondol_state` (Annexe B) pour la certification.
7. Compléter métriques manquantes (AUC SVM, F1 par classe XGBoost — disponibles dans `ml_metrics_w60.json`).

**Priorité basse / à assumer**
8. Données institutionnelles Rondol (ou maintenir l'absence assumée).
9. Dictionnaire exhaustif des 96 variables (générable depuis `src/features.py`).

**Livrable final visé :** `memoire_rondol_professionnel.docx` + `.pdf` (mise en page A4 premium, page de garde 2 logos, styles Titre 1/2/3, en-têtes/pieds, tableaux + figures légendés), via adaptation du script `scripts/generate_memoire_docx_pdf.py` déjà fonctionnel.
