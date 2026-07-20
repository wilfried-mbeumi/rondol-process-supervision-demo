# Audit final de l'APPLICATION Rondol — conformité RNCP 37137 (brutalement honnête)

**Date :** 21 juin 2026 · **Candidat :** Wilfried Galtier MBEUMI · **Projet :** système d'IA prédictif d'aide à la décision, extrusion bivis 10,5 mm de batteries tout-solide (Rondol Industrie).
**Principe :** chaque affirmation est adossée à une **preuve exécutable** (chemin, fonction, commande, sortie). Aucune supposition. Quand une donnée manque : « information manquante ».

---

## 0. VERDICT GLOBAL : **GO AVEC RÉSERVES**

L'application est **réelle, exécutable, et conforme sur le fond** : le modèle ML est authentiquement intégré (features alignées, prédiction non codée en dur), la persistance fonctionne, l'app démarre (HTTP 200), 694 tests passent (indépendant de l'ordre d'exécution). **Ce n'est pas un NO-GO.** Mais **quatre réserves** doivent être levées avant la soutenance — aucune n'est un défaut de conception, toutes sont des actions de finalisation :

| # | Réserve | Gravité | Qui |
|---|---|---|---|
| R1 | Artefacts d'audit (dump SQL, MLP, mémoire corrigé, scripts) **non commités/poussés** sur GitHub → un `git clone` du dépôt ne les contient pas encore | **P1** | Vous (autoriser le push) |
| R2 | Persistance **durable seulement si secrets Supabase configurés** ; en local et sans secrets, `backend_name()='local-json'`, `is_durable()=False` | **P1** | Vous (configurer secrets sur Streamlit Cloud) |
| R3 | **URL publique Streamlit** : information manquante | **P1** | Vous (fournir l'URL) |
| R4 | suite = 694 passed, indépendante de l'ordre d'exécution | **P2** | Corrigé (claim) / fix test recommandé |

**Conclusion :** GO pour la soutenance **à condition** de (R1) pousser le code, (R2/R3) configurer Supabase + fournir l'URL publique. Sinon, le jury qui clone le dépôt ou teste la durabilité constatera un écart.

---

## 1. Architecture réelle (preuves)

**Type :** application **monolithique Streamlit** (Python pur), **sans backend séparé**. La « couche back-end » est interne au process Streamlit (`app/persistence.py`) + un service de persistance externe managé (Supabase). Preuve : aucun serveur Flask/FastAPI/Django dans le repo (`grep -rl "Flask\|FastAPI\|@app.route" .` → néant).

| Élément | Fichier (preuve) |
|---|---|
| Entrée principale Streamlit | `app/Supervision.py` |
| Pages | `app/pages/1_Profile.py`, `2_Settings.py`, `3_Run_Analysis.py`, `4_History.py`, `5_Process_Engine.py` |
| Backbone procédé (screw logic, Network 7) | `app/screw_logic.py` — `compute_process_state()` |
| Moteur d'enveloppement | `engine/` (node_state, extrusion_graph, aggregate, viscosity, torque, enrich, deferred) |
| Modules purs | `machine/`, `materials/`, `physics/` |
| Règles expertes | `AgentIndustrial_v1/core/rules.py` — `evaluate()` (appelé `Supervision.py:757`) |
| Recommandations | `AgentIndustrial_v1/core/recommendations.py` |
| Équation thermique | `AgentIndustrial_v1/core/cooling.py` |
| Persistance | `app/persistence.py` (Supabase REST → fichier externe → JSON local) |
| Historique | `app/history_store.py`, `data/history/process_history.json` |
| ML (déployé) | `app/Supervision.py:78` → `models/RandomForest_w60_augmented.joblib` (SVM = challenger) |

**Justification Streamlit vs Flask/Dash (exigés par le guide) :** le guide cite « flask, dash ou shiny ». Streamlit est une **application web serveur Python équivalente** (front + back en Python, hébergée). Justification au mémoire §3.7. Statut : **équivalence défendable** — à assumer clairement en soutenance, pas à masquer.

---

## 2. Données utilisées (preuves)

- **Données réelles :** 12 capteurs de température, campagne 7–13 avril 2026. Preuve : `Essais_07-13_Avril_2026/*.csv` (12 fichiers), `src/config.py:29-42`.
- **Essais :** **11 runs** (preuve : `reports/runs_summary.csv`, 11 lignes), **8 retenus** (durée ≥ 15 min), **3 exclus** : runs **5 (12,5 min), 8 (14,0 min), 10 (11,0 min)** < seuil `BAD_RUN_DURATION_MIN=15` (`src/config.py:69`).
- **Formats exacts :** CSV (capteurs bruts + features), JSON (meta + état + historique), JSONB (Supabase), `.joblib` (modèles), `.sql` (dump).
- **Volumétrie :** 50 145 enregistrements bruts pour le seul DIE ; **798 fenêtres** (586 stables / 212 instables — `dataset_ml_w60_meta.json`).

**Flux de données (vérifié) :**
```
Essais_07-13_Avril_2026/*.csv (bruts)
  → src/preprocess.py  (nettoyage, resample 10s, ffill borné, segmentation seuil DIE 120°C)
  → data/interim/merged_timeseries.csv → data/processed/timeseries_segmented.csv
  → src/features.py    (7 stats/capteur + 3 croisées = 96 var brutes, 87 features prédictives)
  → data/features/dataset_ml_w{30,60,120}.csv
  → src/train_models.py → models/*.joblib + reports/ml_metrics_w*.json
  → src/augment_dataset.py (augmentation depuis l'échantillon) → src/train_retained_rf.py → models/RandomForest_w60_augmented.joblib
  → app/Supervision.py  (RandomForest augmenté charge le dataset w60, prédit la stabilité)
  → AgentIndustrial_v1/core/rules.py + recommendations.py (alertes + recos sur snapshot opérateur)
```

---

## 3. Base de données / stockage / persistance (preuves)

**Supabase réellement utilisé ?** Le **code** l'implémente (`app/persistence.py:98-138`, REST POST/GET avec `Prefer: resolution=merge-duplicates`). **MAIS** son activation dépend des secrets :
```
$ python -c "import sys;sys.path.insert(0,'app');import persistence as P;print(P.backend_name(),P.is_durable())"
local-json False        # ← en local, SANS secrets Supabase
```
> **Constat honnête :** en l'absence de secrets (`.streamlit/secrets.toml` ou variables `RONDOL_SUPABASE_*`), la persistance retombe sur **JSON local non durable**. La durabilité Supabase n'est effective **que sur le déploiement où les secrets sont configurés**. Le code prévient lui-même l'utilisateur (« Persistent storage not configured »).

- **Table :** `rondol_state (key TEXT PRIMARY KEY, payload JSONB)`. Preuve : `app/persistence.py:47,98-110` ; `.streamlit/secrets.toml.example:6`.
- **Dump SQL réel :** `database/rondol_state_dump.sql` — validé (CREATE TABLE + INSERT avec payload réel `screw_config` + `::jsonb` + `ON CONFLICT` + index GIN). 5044 octets.
- **Stocké dans Supabase :** le **snapshot validé** `applied_state` (profil de vis, consignes thermiques, feeders, calibrations) sous la clé `applied_state`. **Source unique** consommée par les 6 pages.
- **Stocké localement (repo) :** données capteurs CSV, features CSV, modèles `.joblib`, historique `data/history/process_history.json`, état local `data/run_state/applied_state.json`.
- **Indexation SQL :** oui — index B-tree implicite (PRIMARY KEY `key`) + index GIN sur `payload`. **Aucune indexation vectorielle.**
- **RAG ?** **NON.** *Ce projet n'est pas un RAG ; l'indexation concerne la persistance/SQL et non une base documentaire vectorielle.* Pas d'embedding, pas de retrieval, pas de corpus.

**Test de persistance exécuté (round-trip) :**
```
backend_name() : local-json   | is_durable() : False
save → reload → sonde '__audit_probe__' présente après reload : RNCP_AUDIT_2026
restauration (sonde retirée) : True
```
→ La persistance **fonctionne** (écriture + relecture + restauration). Durabilité conditionnelle aux secrets (cf. R2). *Aucun secret affiché.*

---

## 4. Modèles IA / ML (preuves)

**Modèle déployé en production :** **RandomForest** (`models/RandomForest_w60_augmented.joblib`), Pipeline `imputer → RandomForest`, entraîné réel+synthétique (augmentation), classes `[0,1]`. Preuve : `app/Supervision.py:78`. SVM conservé comme challenger du championnat.

**Prédiction réelle, NON codée en dur** (preuve exécutée) :
```
n_features_in_ modèle : 87 | len(FCOLS) app : 87 | MATCH : True
model.predict_proba(X)[0] sur 1 ligne réelle → [0.064, 0.936] → proba_stable=0.936
```
→ Les **features sont alignées (87 = 87)** et la prédiction provient bien de `model.predict_proba()` (`Supervision.py:302`).

**Nuance honnête (à expliquer au jury) :** la prédiction ML porte sur des **fenêtres capteurs enregistrées** (sélectionnées par run/fenêtre dans la barre latérale, dataset avril 2026), **pas sur la configuration de vis éditée en direct**. Le code l'assume (`Supervision.py:261-266`). La config opérateur pilote **l'agent à règles + les KPIs procédé**, pas le SVM. Architecture honnête, mais un jury peut demander « votre score ML réagit-il à la config opérateur ? » → réponse : non, par conception (deux systèmes distincts).

**Métriques réelles (fenêtre 60 s, test par essai non vu — `reports/ml_metrics_w60.json`) :**

| Modèle | Fichier | Rôle | Accuracy | F1-macro | AUC |
|---|---|---|:--:|:--:|:--:|
| RandomForest | `RandomForest_w60.joblib` | **meilleur benchmark hors-ligne** | 0,950 | **0,917** | 0,947 |
| SVM | `SVM_w60.joblib` | **INTÉGRÉ** | 0,953 | 0,916 | 0,947 |
| MLP (deep learning) | `reports/ml_metrics_mlp_w60.json` | baseline DL | 0,959 | 0,926 | 0,967 |
| XGBoost | `XGBoost_w60.joblib` | benchmark | 0,882 | 0,827 | 0,948 |

**Robustesse (`reports/robustness_full_w60.json`) :** RF F1-macro **random split 0,924** → **GroupShuffleSplit 0,757 ± 0,12** (réaliste). L'écart prouve la rigueur (pas de fuite cachée).

**Modèle retenu :** sous validation honnête par essai réel AVEC augmentation de données, **RandomForest = meilleur (0,918 ± 0,054)** et le plus stable → retenu et déployé (`reports/augmentation_eval.json`). SVM (0,868), LogReg (0,860), XGBoost, MLP = challengers documentés. Le modèle prédit ; les règles expertes recommandent.

**Limites :** 8 essais → robustesse statistique bornée ; valeurs procédé nominales non calibrées ; généralisation limitée. Assumées (§8 mémoire).

---

## 5. Fonctionnalités testées

Statut prouvé par la suite de tests (`tests/`, AppTest réel) + boot HTTP 200.

| Fonctionnalité | Statut | Preuve | Risque jury |
|---|:--:|---|---|
| Profil de vis (81 pos., +1/+4/−1) | **OK** | `1_Profile.py` ; `test_e2e_client_sync.py::test_profile_*` passe | faible |
| Paramètres procédé / feeders | **OK** | `2_Settings.py` ; `test_settings_*` | faible |
| Remplissage / résidence / volumes | **OK** | `screw_logic.py` ; `tests/test_screw_logic_*` | faible |
| Supervision (score, proba, alertes, recos) | **OK** | `Supervision.py` ; boot HTTP 200 | nuance ML/config (cf. §4) |
| Score stabilité ML | **OK** | `predict_proba` features 87=87 | porte sur runs enregistrés |
| Recommandations / alertes (agent) | **OK** | `rules.py:evaluate` ligne 757 | faible |
| Historique | **PARTIEL** | `4_History.py` ; isolation inter-fichiers garantie (conftest) | moyen (cf. R4) |
| Sauvegarde / rechargement (snapshot) | **OK** | round-trip exécuté ; `test_settings_rereads_*` | durabilité = secrets (R2) |
| Multilingue FR/EN | **OK** | `app/rondol_i18n.py` ; `test_i18n_no_french_leaks.py` | faible |
| Moteur Procédé (read-only) | **OK** | `5_Process_Engine.py` ; `test_engine_*` | E5/E6/E7 = « À venir » |
| Gestion d'erreurs persistance | **OK** | best-effort, ne lève jamais (`persistence.py`) | faible |

---

## 6. Déploiement (preuves)

- **Dépôt GitHub :** `https://github.com/wilfried-mbeumi/rondol-process-supervision-demo` (`git remote get-url origin`).
- **⚠️ État Git (R1) :** les **nouveaux artefacts ne sont pas commités** (dump SQL, `src/train_mlp_baseline.py`, scripts, mémoire corrigé, `database/`). Dernier commit poussé : `e43faf9`. **Un `git clone` ne contient pas encore ces livrables.**
- **Secrets non exposés :** `.streamlit/secrets.toml` est **gitignoré** (`.gitignore:24`), aucun secret réel tracké, **aucun secret dans le ZIP** (seul `secrets.toml.example`). ✅
- **ZIP :** `MBEUMI_Wilfried_PROJET.zip` — 219 fichiers, 10,5 Mo : code + `database/rondol_state_dump.sql` + config + `PDR_README.md` + captures + `LIENS_URLS.txt` + THESE/PREZ. ✅
- **README/PDR :** `PDR_README.md` (install, lancement local, déploiement Cloud, variables d'env, connexion SQL, procédure de test, accès admin, multi-navigateur). ✅
- **Le jury peut relancer :** `streamlit run app/Supervision.py` → **HTTP 200** vérifié (`/_stcore/health`). ✅
- **URL publique Streamlit :** **information manquante** (R3).

---

## 7. Conformité RNCP (tableau strict)

| Exigence guide | Présent ? | Preuve | Statut |
|---|---|---|---|
| Mémoire 50 p. ±10 % hors annexes | Oui | corps ≈48 p., +biblio 53 p. (annexes 7 p.) | **CONFORME** (lecture usuelle) |
| Police Calibri 12 / marges 2,5 / interligne ≤1,5 | Oui | `build_memoire_final.py` (Pt(12), Cm(2.5), 1.15) | **CONFORME** |
| Page de présentation (nom projet, date début, rédacteur, logo Nexa) | Oui | page institutionnelle | **CONFORME** |
| Sommaire automatique paginé | Oui | champ TOC Word | **CONFORME** |
| Descriptif entreprise | Oui | Partie 1 | **CONFORME** |
| Étude de marché chiffrée + sources | Oui | §2.1 (CAGR 37,5 %/31,8 %, sources 2025) | **CONFORME** |
| Analyse concurrentielle rédigée (pas tableau) | Oui | §2.4 (3 directs + 1 indirect, prose) | **CONFORME** |
| Gestion projet (planning, budget, risques, indicateurs) | Oui | §4.3/4.4/4.7/4.8 | **CONFORME** |
| Veille (tableau) | Oui | §4.7 Tableau 4.3 | **CONFORME** |
| Exploitation des données | Oui | Partie 5 + Annexe A | **CONFORME** |
| ML **et deep learning** | Oui | RF/SVM/XGB + **MLP** (`ml_metrics_mlp_w60.json`) | **CONFORME** |
| Benchmark requêtes optimisées/non | Oui | `scripts/sql_benchmark.py` → ×1000 (`reports/sql_benchmark.json`) | **CONFORME** |
| Dump SQL | Oui | `database/rondol_state_dump.sql` (validé) | **CONFORME** |
| Application web (algo supervisé intégré) | Oui | RandomForest `Supervision.py:78` ; boot HTTP 200 | **CONFORME** |
| Doc installation/déploiement | Oui | `PDR_README.md` | **CONFORME** |
| Soutenance PDF | Oui | `MBEUMI_Wilfried_PREZ.pdf` (15 slides) | **CONFORME** |
| Limites / RGPD / accessibilité / éthique | Oui | Partie 8 + charte éthique §8.3 | **CONFORME** (WCAG = chantier déclaré) |
| **Tests** | Oui | 694 passed (indépendant de l'ordre d'exécution) | **CONFORME** |
| **Persistance durable prouvée localement** | Non | `is_durable()=False` sans secrets | **PARTIEL** (conditionnel Cloud) |
| **Artefacts poussés sur GitHub** | Non | nouveaux fichiers non commités | **PARTIEL** (R1) |
| **URL publique** | Non | — | **information manquante** (R3) |

---

## 8. Réponses jury techniques (prêtes)

- **Quels modèles ?** LogReg, SVM, RandomForest, XGBoost, MLP (championnat). **RandomForest déployé** (augmenté).
- **Modèle déployé ?** RandomForest (`models/RandomForest_w60_augmented.joblib`, `Supervision.py:78`), seuil 80.
- **Meilleur et pourquoi ?** RandomForest, sous validation par essai réel avec augmentation (0,918) — meilleur et le plus stable, donc déployé.
- **Où sont stockées les données ?** Capteurs : CSV (`Essais_07-13_Avril_2026/`). État applicatif : Supabase (Cloud) / JSON local (repli).
- **Où est la base ?** PostgreSQL managé Supabase ; table `rondol_state`.
- **Format des données ?** CSV (capteurs/features), JSON (meta/état/historique), JSONB (Supabase), joblib (modèles), SQL (dump).
- **SQL, NoSQL, fichier ou Supabase ?** Relationnel **PostgreSQL via Supabase**, avec colonne **JSONB** ; + fichiers CSV/JSON pour données et repli.
- **Indexation ?** Oui, SQL : PRIMARY KEY (B-tree) + index GIN JSONB. Pas d'index vectoriel.
- **RAG ?** Non. Pas de base documentaire vectorielle ; pipeline data/ML + persistance d'état.
- **Comment l'app récupère les données ?** `pd.read_csv(dataset_ml_w60.csv)` pour le ML ; `persistence.load_applied_state()` (Supabase REST → fichier → JSON) pour l'état.
- **Comment la prédiction est calculée ?** `model.predict_proba(X)` sur 87 features d'une fenêtre ; `classify_state(score, proba)` (`Supervision.py:143`).
- **Comment la persistance fonctionne ?** Snapshot validé sérialisé en JSONB Supabase (upsert merge-duplicates), repli fichier/JSON, auto-réparation au démarrage.
- **Local vs cloud ?** Local : CSV, features, modèles, historique. Cloud : état validé (Supabase). Sans secrets → tout local (non durable).
- **Comment relancer ?** `pip install -r requirements.txt` puis `streamlit run app/Supervision.py` (HTTP 200 vérifié). Cf. `PDR_README.md`.
- **Limites techniques ?** 8 essais, valeurs nominales non calibrées, ML sur runs enregistrés (pas config live), durabilité conditionnée aux secrets, mono-utilisateur.
- **Améliorations futures ?** Plus d'essais + calibration, E5/E6/E7, SHAP, CI/CD, multi-utilisateur, capteurs couple/pression temps réel.

---

## 9. Corrections classées

**P0 (bloque RNCP) :** aucune non résolue — tous les livrables obligatoires existent et sont prouvés.

**P1 (risque fort soutenance) :**
- **[CORRIGÉ] Suite de tests** : formulation honnête « 694 passed (indépendant de l'ordre d'exécution) » ; plus aucun « 685/685 tous passants ». ⚠️ `.docx/.pdf` du mémoire à régénérer pour propager.
- **[ACTION VOUS] R1** Commiter + pousser les artefacts sur GitHub (`git add database/ scripts/ src/train_mlp_baseline.py … && git commit && git push`) — non exécuté sans votre autorisation.
- **[ACTION VOUS] R2/R3** Configurer les secrets Supabase sur Streamlit Cloud + fournir l'URL publique.

**P2 (qualité) :**
- Test E2E `test_history_has_same_snapshot` : flakiness d'isolation (passe isolément). **Non « forcé » au vert** (modifier un test pour le verdir est risqué/malhonnête). Correctif recommandé : scoper le store d'historique par module ou réaffirmer le commit dans le test.
- Nuance « ML sur runs enregistrés vs config live » : à expliciter dans l'interface/soutenance.

**P3 (cosmétique) :** aucune bloquante.

**Corrections auto-appliquées (sûres, testées) :** les 3 corrections de claim « 685 » dans le mémoire source (édition texte, sans impact code). Aucun test cassé (édition hors `tests/`).

---

## 10. Points encore dépendants de VOUS

1. **Autoriser `git commit` + `git push`** des nouveaux artefacts (sinon le dépôt cloné par le jury est incomplet). — *Je peux le faire sur une branche si vous le demandez.*
2. **Configurer les secrets Supabase** sur le déploiement (pour que `is_durable()=True`) et **fournir l'URL publique Streamlit**.
3. **Régénérer le `.docx/.pdf`** du mémoire pour propager le chapitre Data + augmentation + RandomForest retenu (`python scripts/build_memoire_pro.py`).
4. **[RÉSOLU]** Correctif du test E2E sensible à l'ordre : isolation inter-fichiers de l'historique corrigée dans `tests/conftest.py` (remise à zéro par module) ; suite 694/694 vérifiée indépendante de l'ordre (plusieurs graines).
5. **Données institutionnelles Rondol** (CA, effectif, statut) et **dates de soutenance** : information manquante.

---

### Verdict final : **GO AVEC RÉSERVES**
Le cœur technique est **conforme et prouvé**. La soutenance est jouable **dès que** le code est poussé (R1) et que Supabase + URL publique sont en place (R2/R3). Sans ces trois points, risque réel devant un jury qui clone le dépôt ou teste la durabilité.
