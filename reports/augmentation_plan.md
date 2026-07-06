# Plan de génération du dataset simulé — projet Rondol

**Statut :** artefact méthodologique **hors rapport** (à présenter au référent).
**Principe validé :** l'échantillon d'essais réels de Rondol est insuffisant (8 essais,
627 fenêtres valides). On **génère des données simulées À PARTIR de l'échantillon
réel** — jamais aléatoirement — pour stabiliser l'apprentissage et démontrer la
méthode. Le modèle est **évalué exclusivement sur les essais réels** (aucune triche).

Implémentation : `src/augment_dataset.py` · Évaluation : `src/evaluate_augmentation.py`
Sorties : `data/features/dataset_ml_w60_augmented.csv`, `reports/augmentation_report.json`,
`reports/augmentation_eval.json`.

---

## 1. Source : le dataset de base (échantillon réel)
- 12 capteurs de température (Z1–Z8, DIE, CastFilmBody, CastFilmP1, CastFilmP2).
- Chaque fenêtre = 87 variables : **7 statistiques × 12 capteurs** (mean, std, min,
  max, range, slope, iqr) + **3 gradients croisés** (Z8−Z1, DIE−Z8, CastFilm−DIE).
- Cible `is_stable` (0/1) = stabilité thermique de la fenêtre suivante (prévision).
- **Imperfections réelles observées** (à reproduire) : 44 colonnes avec valeurs
  manquantes (blackout d'un capteur → ses 7 statistiques manquent **ensemble**) ;
  aberrations thermocouple (max ≈ 3 277 °C).

## 2. « Prompt » de génération (règles appliquées)
> Génère de nouvelles fenêtres capteurs **inspirées de l'échantillon réel**, classe
> par classe, en respectant les statistiques réelles et les contraintes métier
> d'extrusion, et en **reproduisant les imperfections** de l'échantillon.

1. **Estimation conditionnelle à la classe.** Pour chaque classe (stable / instable)
   et chaque capteur, estimer la dispersion réelle (écart-type de classe) de chaque
   statistique primaire (mean, std, slope, iqr).
2. **Génération par ancrage (bootstrap).** Chaque fenêtre synthétique **part d'une
   vraie fenêtre de la même classe** (conserve les corrélations inter-capteurs),
   puis reçoit un **jitter gaussien borné** = 30 % de l'écart-type réel de classe.
   → ni copie, ni tirage uniforme : une variation contrôlée autour du réel.
3. **Cohérence interne exacte** (identique à `src/features.py`, vérifiée écart = 0) :
   `range = max − min` ; `min ≤ mean ≤ max` ; gradients = **différences des moyennes**
   générées (`grad_Z8_minus_Z1 = Z8_mean − Z1_mean`, etc.).
4. **Contraintes métier (garde-fous physiques).** Températures bornées à [10, 300] °C
   (hors aberrations) ; std, iqr, range ≥ 0. La sémantique de classe est préservée :
   après génération, `Z5_std ≈ 0,08 °C` en **stable** vs `≈ 1,42 °C` en **instable**
   (le synthétique capture bien ce qui *définit* l'instabilité).
5. **Reproduction des imperfections** (exigence explicite du référent — « pas des
   données parfaites ») : blackout d'un capteur (ses 7 statistiques → NaN ensemble)
   au **taux réel par capteur** (ex. Z6 2,1 %, Z5/Z7 1,4 %) ; injection d'aberrations
   thermocouple rares (0,3 %) → matière à **nettoyer/imputer** dans le pipeline.
6. **Traçabilité & anti-fuite.** Marquage `synthetic=1` ; graine fixée (42) ;
   essais synthétiques dans un **pool de run_id distinct (900–909)** → **jamais**
   mélangés aux essais réels en test.

## 3. Volume généré
- **627 fenêtres réelles** (449 stable / 178 instable — déséquilibré)
  **+ 800 synthétiques** (400 / 400 — **rééquilibrage**) = **1 427 fenêtres**.
- 78 valeurs manquantes reproduites (blackouts capteurs).

## 4. Évaluation HONNÊTE (le point qui évite la triche)
Validation **LeaveOneGroupOut sur les essais RÉELS** : pour chaque essai réel laissé
de côté (test), on entraîne (a) sur les autres essais réels seuls, puis (b) sur les
autres essais réels **+ tout le synthétique**. Le test est **toujours un essai réel
non vu** ; le synthétique n'est **jamais** en test.

| Modèle | Sans augmentation (réel) | Avec augmentation | Gain |
|---|:--:|:--:|:--:|
| LogisticRegression | 0,799 ± 0,163 | 0,860 ± 0,111 | **+0,061** |
| SVM (RBF) | 0,805 ± 0,171 | 0,868 ± 0,089 | **+0,063** |
| **RandomForest** | 0,796 ± 0,187 | **0,918 ± 0,054** | **+0,122** |

**Lecture :** l'augmentation documentée **améliore la généralisation** aux essais
réels non vus **et réduit fortement la variance** (RandomForest : σ 0,187 → 0,054).
C'est l'effet recherché : stabiliser un apprentissage limité par 8 essais, sans
prétendre disposer de plus de données réelles.

## 5. Garde-fous d'honnêteté (à tenir devant le jury)
- Les données synthétiques **augmentent** l'échantillon, elles ne le **remplacent** pas.
- Le modèle reste un **indicateur expérimental** ; l'augmentation ne le rend pas
  « calibré industriellement ».
- Toutes les métriques rapportées sont mesurées **sur des essais réels non vus**.
- Le plan est reproductible (graine fixée) et le code est fourni (`src/augment_dataset.py`).
