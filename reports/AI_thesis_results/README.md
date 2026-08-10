# AI thesis results — Rondol

Détection de fenêtres d'extrusion instables, extrudeuse bivis Rondol.
Fenêtre 60 s, pas 30 s, 87 variables, 627 fenêtres réelles issues de 8 essais (7-13 avril 2026).

CSV en UTF-8 avec BOM (ouverture directe sous Excel), séparateur virgule, 6 décimales. Figures en PNG 300 dpi et SVG vectoriel.

---

## Convention de classe

La classe positive est **`unstable`**, conformément à la demande. Dans les fichiers, `y_true` / `y_pred` valent `1` pour *stable* et `0` pour *unstable*.

| | Predicted stable | Predicted unstable |
|---|---|---|
| **Actual stable** | TN | FP — fausse alerte |
| **Actual unstable** | FN — instabilité non détectée | TP — instabilité détectée |

`probability_stable` est la sortie de `predict_proba` ; `probability_unstable = 1 − probability_stable`. Seuil de décision 0,5.

---

## Méthode d'agrégation

**Blocs 1 et 2 — moyenne des métriques par fold.** La métrique est calculée sur chaque fold, puis moyennée. Chaque essai pèse autant, quel que soit son nombre de fenêtres (250 pour l'essai 1, 29 pour l'essai 42). Écart-type de population (ddof = 0), comme dans `evaluate_augmentation.py`, pour rester comparable aux chiffres déjà diffusés.

**Bloc 3 — mise en commun des prédictions (pooled).** Les prédictions out-of-fold des huit itérations sont concaténées, puis une seule matrice de confusion est calculée. Chaque fenêtre pèse autant. C'est le mode correct pour une matrice de confusion ; moyenner des taux par fold donnerait des effectifs non entiers.

Un écart entre le macro-F1 du bloc 2 (moyenne des folds) et celui du bloc 3 (pooled) est donc attendu : deux quantités différentes calculées sur les mêmes prédictions.

**Périmètre.** Les essais 32 et 42 sont intégralement stables : macro-F1 dégénéré et ROC-AUC indéfini. Les agrégats sont publiés sur deux périmètres, `all_folds` (8) et `scorable_folds` (6). Le périmètre à retenir est `scorable_folds`.

---

## Note méthodologique

Le pool synthétique historique était généré une seule fois à partir des huit essais, puis injecté dans chaque fold d'entraînement : l'essai de test servait donc de point d'ancrage. Deux des cinq garanties demandées n'étaient pas satisfaites. La condition `fold_aware` régénère le pool à partir du seul fold d'entraînement et les satisfait toutes.

Détail point par point : `block_2_model_augmentation/methodological_checks.json`.
Confrontation aux valeurs déjà publiées : `reconciliation_report.csv` (16 confirmées, 12 écarts, tous expliqués).

---

## Tableaux prêts à intégrer

Également fournis en CSV sous le nom `table_for_thesis.csv` dans chaque dossier de bloc.

### Bloc 1 — stratégies de validation (Random Forest, 6 folds évaluables)

| Validation strategy | Number of evaluations | Macro-F1 | Stable-class F1 | Unstable-class F1 | Accuracy | ROC-AUC |
|---|---|---|---|---|---|---|
| Random split (window-level) | 10 | 0.932 ± 0.015 | 0.961 ± 0.009 | 0.903 ± 0.021 | 0.944 ± 0.012 | 0.976 ± 0.014 |
| GroupShuffleSplit (run-level) | 10 | 0.752 ± 0.116 | 0.821 ± 0.106 | 0.684 ± 0.139 | 0.781 ± 0.124 | 0.928 ± 0.034 |
| Leave-One-Group-Out (run-level) | 6 | 0.809 ± 0.176 | 0.894 ± 0.138 | 0.724 ± 0.333 | 0.902 ± 0.085 | 0.925 ± 0.056 |

### Bloc 2 — modèles et augmentation (Leave-One-Group-Out)

| Model | Macro-F1 without augmentation | Macro-F1 with training-only augmentation | Absolute change | ROC-AUC without augmentation | ROC-AUC with augmentation | Macro-F1 with leaky global augmentation (superseded) |
|---|---|---|---|---|---|---|
| Logistic regression | 0.799 ± 0.163 | 0.809 ± 0.173 | +0.010 | 0.893 | 0.905 | 0.860 ± 0.111 |
| SVM (RBF) | 0.805 ± 0.171 | 0.824 ± 0.139 | +0.018 | 0.904 | 0.908 | 0.868 ± 0.089 |
| Random Forest | 0.809 ± 0.176 | 0.809 ± 0.126 | -0.001 | 0.925 | 0.913 | 0.918 ± 0.054 |
| XGBoost | 0.757 ± 0.213 | 0.801 ± 0.159 | +0.044 | 0.897 | 0.922 | 0.900 ± 0.073 |
| Neural network (MLP) | 0.778 ± 0.217 | 0.781 ± 0.164 | +0.004 | 0.849 | 0.828 | 0.862 ± 0.118 |

La dernière colonne reprend la condition historique, entachée de la fuite d'ancrage ; elle est conservée pour la traçabilité et ne doit pas être présentée comme la performance du modèle.

### Bloc 3 — généralisation

| Evaluation dataset | Number of windows | Stable/unstable distribution | Macro-F1 | Unstable precision | Unstable recall | Specificity | Accuracy | Balanced accuracy | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| A — Leave-One-Group-Out, 8 essais réels | 627 | 71.6 % / 28.4 % | 0.821 | 0.815 | 0.669 | 0.940 | 0.863 | 0.804 | 0.941 | 0.879 |
| B — Dataset continu simulé (validation externe) | 3479 | 88.5 % / 11.5 % | 0.598 | 0.251 | 0.625 | 0.757 | 0.742 | 0.691 | 0.753 | 0.284 |

---

## Dictionnaire des fichiers

### block_1_validation_strategy

| Fichier | Contenu |
|---|---|
| `validation_metrics_by_fold.csv` | Une ligne par stratégie × modèle × fold. Colonnes : `fold_id`, `seed`, `test_run_id`, `n_train_runs`, `n_test_runs`, `n_train_windows`, `n_test_windows`, `train_pct_stable`, `test_pct_stable`, `test_single_class`, puis les métriques. |
| `validation_summary.csv` | Agrégats moyenne / écart-type / min / max, pour les deux périmètres (`scope`). |
| `validation_predictions.csv` | Prédictions individuelles : `validation_strategy`, `fold_id`, `test_run_id`, `window_id`, `y_true`, `y_pred`, `probability_stable`, `probability_unstable`. |
| `table_for_thesis.csv` | Tableau prêt à intégrer. |
| `validation_strategy_figure.png` / `.svg` | Panneau A macro-F1, panneau B ROC-AUC, folds superposés. |
| `generate_validation_figure.py` | Script de production (avec `common.py` et `fold_augment.py`). |

Trois stratégies : `random_split` (10 répétitions, fenêtres tirées sans tenir compte de l'essai — **estimation optimiste exposée à la fuite par autocorrélation temporelle, pas la performance retenue**), `group_shuffle` (10 répétitions, aucun essai partagé), `logo` (8 folds, un essai exclu par fold).

### block_2_model_augmentation

| Fichier | Contenu |
|---|---|
| `model_metrics_by_fold.csv` | Une ligne par modèle × condition × fold, aux 13 colonnes demandées, plus `n_train_real`, `n_train_synthetic`, `test_single_class` et les effectifs TP/FN/FP/TN. |
| `model_comparison_summary.csv` | Agrégats par modèle et condition. |
| `model_predictions_by_fold.csv` | Prédictions individuelles pour chaque modèle et condition. |
| `methodological_checks.json` | Réponse point par point aux cinq garanties. |
| `table_for_thesis.csv` | Tableau prêt à intégrer. |
| `model_augmentation_figure.png` / `.svg` | Panneau A macro-F1 par modèle, panneau B Δ macro-F1. |
| `generate_model_comparison.py` | Script de production. |

Trois valeurs de `augmentation` : `none` (essais réels seuls), `pooled_global` (protocole historique, pool ancré sur les 8 essais), `fold_aware` (protocole corrigé, pool régénéré par fold).

### block_3_confusion_generalisation

| Fichier | Contenu |
|---|---|
| `logo_oof_predictions.csv` | 627 prédictions out-of-fold, chaque fenêtre réelle exactement une fois, produite par le modèle dont l'essai était exclu. Unicité vérifiée par assertion à l'exécution. |
| `continuous_dataset_predictions.csv` | 3 479 prédictions sur le dataset continu simulé. |
| `confusion_matrices.csv` | TP / TN / FP / FN explicites pour les deux évaluations. |
| `generalisation_summary.csv` | Jeu complet de métriques, dont spécificité, valeur prédictive négative et PR-AUC. |
| `table_for_thesis.csv` | Tableau prêt à intégrer. |
| `confusion_matrices.png` / `.svg` | Effectifs absolus et pourcentages normalisés par classe réelle. |
| `roc_pr_curves.png` / `.svg` | Courbes ROC et précision-rappel. |
| `generate_confusion_analysis.py` | Script de production. |

**Nature du dataset continu : simulé.** Campagne continue de 100 800 lignes au pas de 10 s (≈ 11,7 jours), calibrée statistiquement sur les essais réels : 5 recettes, cycles ambiant → chauffe → plateau régulé (bruit AR(1)) → extrusion → refroidissement, valeurs manquantes 1-5 %, aberrations thermocouple (code 3276,7). Graine fixe, donc reproductible. Ce n'est pas un jeu expérimental : aucune mesure physique supplémentaire n'a été acquise. Le modèle y est appliqué tel quel, sans réentraînement.

### source_results

JSON de résultats déjà publiés dans le projet et scripts qui les ont produits, joints pour permettre la confrontation.

---

## Reproduire

Depuis la racine du dépôt :

```
python -m scripts.thesis_results.build_all
```

Chaque dossier de bloc est autonome : le script `generate_*.py` y est recopié avec ses dépendances, imports aplatis.

Tout est déterministe — graine 42, et 20260417 pour la base continue. Les métriques publiées sont recalculables depuis les fichiers de prédictions.
