# Réconciliation des valeurs publiées

- Valeurs **confirmées** (écart ≤ 0.005) : **16**
- Valeurs présentant un **écart expliqué** : **12**
- Valeurs **nouvelles** (protocole corrigé, sans équivalent publié) : **3**

Aucun écart n'est inexpliqué. Les causes sont détaillées dans l'en-tête de `scripts/thesis_results/reconciliation.py` et reportées colonne `cause`.

| Bloc | Modèle | Condition | Métrique | Publié | Recalculé | Écart | Statut |
|---|---|---|---|---|---|---|---|
| 1 — stratégie de validation | RandomForest | random_split | macro_f1 | 0.9239 | 0.9322 | +0.0083 | ÉCART |
| 1 — stratégie de validation | RandomForest | random_split | roc_auc | 0.9834 | 0.9759 | -0.0075 | ÉCART |
| 1 — stratégie de validation | RandomForest | group_shuffle | macro_f1 | 0.7572 | 0.7524 | -0.0048 | CONFIRMÉ |
| 1 — stratégie de validation | RandomForest | group_shuffle | roc_auc | 0.9298 | 0.9282 | -0.0016 | CONFIRMÉ |
| 1 — stratégie de validation | RandomForest | logo | macro_f1 | 0.7928 | 0.8093 | +0.0165 | ÉCART |
| 1 — stratégie de validation | RandomForest | logo | roc_auc | 0.9204 | 0.9248 | +0.0044 | CONFIRMÉ |
| 1 — stratégie de validation | XGBoost | random_split | macro_f1 | 0.9498 | 0.9381 | -0.0117 | ÉCART |
| 1 — stratégie de validation | XGBoost | random_split | roc_auc | 0.9826 | 0.9767 | -0.0059 | ÉCART |
| 1 — stratégie de validation | XGBoost | group_shuffle | macro_f1 | 0.7739 | 0.6965 | -0.0774 | ÉCART |
| 1 — stratégie de validation | XGBoost | group_shuffle | roc_auc | 0.8815 | 0.8714 | -0.0101 | ÉCART |
| 1 — stratégie de validation | XGBoost | logo | macro_f1 | 0.7350 | 0.7573 | +0.0223 | ÉCART |
| 1 — stratégie de validation | XGBoost | logo | roc_auc | 0.9095 | 0.8971 | -0.0124 | ÉCART |
| 1 — stratégie de validation | SVM_RBF | random_split | macro_f1 | 0.9129 | 0.8972 | -0.0157 | ÉCART |
| 1 — stratégie de validation | SVM_RBF | random_split | roc_auc | 0.9752 | 0.9697 | -0.0055 | ÉCART |
| 1 — stratégie de validation | SVM_RBF | group_shuffle | macro_f1 | 0.7944 | 0.7944 | -0.0000 | CONFIRMÉ |
| 1 — stratégie de validation | SVM_RBF | group_shuffle | roc_auc | 0.9012 | 0.9012 | +0.0000 | CONFIRMÉ |
| 1 — stratégie de validation | SVM_RBF | logo | macro_f1 | 0.8052 | 0.8052 | +0.0000 | CONFIRMÉ |
| 1 — stratégie de validation | SVM_RBF | logo | roc_auc | 0.9041 | 0.9041 | +0.0000 | CONFIRMÉ |
| 2 — modèles × augmentation | LogisticRegression | none | macro_f1 | 0.7990 | 0.7990 | -0.0000 | CONFIRMÉ |
| 2 — modèles × augmentation | LogisticRegression | pooled_global | macro_f1 | 0.8600 | 0.8596 | -0.0004 | CONFIRMÉ |
| 2 — modèles × augmentation | LogisticRegression | fold_aware | macro_f1 | — | 0.8088 | — | NOUVEAU |
| 2 — modèles × augmentation | SVM_RBF | none | macro_f1 | 0.8050 | 0.8052 | +0.0002 | CONFIRMÉ |
| 2 — modèles × augmentation | SVM_RBF | pooled_global | macro_f1 | 0.8680 | 0.8681 | +0.0001 | CONFIRMÉ |
| 2 — modèles × augmentation | SVM_RBF | fold_aware | macro_f1 | — | 0.8236 | — | NOUVEAU |
| 2 — modèles × augmentation | RandomForest | none | macro_f1 | 0.7960 | 0.8093 | +0.0133 | ÉCART |
| 2 — modèles × augmentation | RandomForest | pooled_global | macro_f1 | 0.9180 | 0.9181 | +0.0001 | CONFIRMÉ |
| 2 — modèles × augmentation | RandomForest | fold_aware | macro_f1 | — | 0.8085 | — | NOUVEAU |
| 3 — généralisation | RandomForest_w60_augmented (déployé) | dataset continu simulé | roc_auc | 0.7530 | 0.7535 | +0.0005 | CONFIRMÉ |
| 3 — généralisation | RandomForest_w60_augmented (déployé) | dataset continu simulé | accuracy | 0.7420 | 0.7422 | +0.0002 | CONFIRMÉ |
| 3 — généralisation | RandomForest_w60_augmented (déployé) | dataset continu simulé | macro_f1 | 0.5980 | 0.5983 | +0.0003 | CONFIRMÉ |
| 3 — généralisation | RandomForest_w60_augmented (déployé) | dataset continu simulé | unstable_recall | 0.6250 | 0.6250 | +0.0000 | CONFIRMÉ |
