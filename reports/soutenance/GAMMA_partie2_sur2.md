# Premier résultat : ce que je croyais avoir obtenu

Huit essais, c'est trop peu. J'ai donc généré **800 fenêtres synthétiques** à partir de l'échantillon réel — bootstrap conditionné par classe, jitter borné, imperfections des capteurs reproduites — injectées à l'entraînement uniquement.

Le gain paraissait net :

**Random Forest : 0,809 → 0,918** de F1-macro
**Écart-type divisé par plus de trois** (0,176 → 0,054)

J'ai présenté ce résultat comme l'aboutissement du volet prédictif.

*Il était faux.*

---

# L'audit : une fuite par ancrage

En auditant mon propre pipeline à la demande de l'encadrement industriel, j'ai trouvé le défaut.

Le pool synthétique était généré **une seule fois, à partir des huit essais réels** — puis réutilisé dans chaque pli.

L'essai censé être exclu avait donc contribué **indirectement** à l'entraînement : ses fenêtres servaient de **points d'ancrage** au bootstrap, ses valeurs alimentaient les écarts-types pilotant le jitter.

Le pli de test ne contenait aucune fenêtre synthétique. **La fuite était invisible à la lecture du code.**

**La correction :** régénérer le pool à chaque pli, à partir des seuls essais d'entraînement — même algorithme, même volume, même graine.

---

# Le vrai résultat : le gain disparaît

| Modèle | Sans augmentation | Augmentation globale *(fuitée)* | **Augmentation par pli** |
|---|---|---|---|
| SVM (RBF) | 0,805 | 0,868 | **0,824** |
| Régression logistique | 0,799 | 0,860 | **0,809** |
| **Random Forest** | 0,809 | **0,918** | **0,809** |
| XGBoost | 0,757 | 0,900 | **0,801** |
| Réseau de neurones | 0,778 | 0,862 | **0,781** |

Sur le Random Forest, le gain passe de **+0,109 à −0,001**.

Aucun modèle n'atteint 0,85. Les cinq restent groupés entre 0,78 et 0,82, pour des écarts-types de 0,13 à 0,17 : **statistiquement indiscernables**.

---

# Pourquoi je le dis plutôt que de le taire

**Déontologique** — annoncer 0,918 à Rondol aurait été une promesse que le modèle n'aurait pas tenue en production.

**Méthodologique** — cette fuite illustre mieux que n'importe quel développement réussi le point central de mon travail : *la performance est une propriété du protocole d'évaluation autant que de l'algorithme.*

**Pratique** — prédictions par pli, métriques et générateur corrigé sont livrés dans le dépôt. Chaque chiffre est recalculable et contestable.

> **Le modèle retenu reste le Random Forest — non pour son score, mais pour son interprétabilité, sa tolérance aux capteurs manquants et sa stabilité inter-essais (l'écart-type le plus faible des cinq).**

---

# Épreuve de transférabilité : validation externe

Pour tester la généralisation sans attendre une nouvelle campagne, j'ai généré une base continue de 100 800 lignes à partir de l'échantillon réel, puis soumis le modèle **sans réentraînement**.

**3 479** fenêtres · **15** runs simulés

**AUC 0,753** — le pouvoir discriminant subsiste

**62 %** des fenêtres instables détectées, avec des erreurs majoritairement **conservatrices** : fausses alertes plutôt que dérives manquées

*La génération n'a volontairement pas été ajustée pour flatter ces chiffres. L'écart avec les essais réels mesure la sensibilité au changement de distribution — et confirme le statut de l'outil : indicateur d'aide à la décision, pas détecteur certifié.*

---

# L'application : une HMI industrielle, pas un tableau de bord

**7 pages** — Supervision · Profil de vis · Paramètres IA · Analyse de run · Historique · Moteur procédé · Compte

**Persistance en trois couches** — édition → état validé → historique. L'opérateur ne perd jamais son travail, même après un redémarrage du serveur.

**Bilingue** FR / EN · **accès protégé** (mots de passe hachés PBKDF2, jamais en clair)

**Accessible** — contrastes mesurés de 6,38:1 à 18,39:1, tous conformes WCAG 2.1 AA ; schéma de vis doté d'une alternative textuelle

**En ligne** — rondol-process-supervision-demo.streamlit.app

---

# Cinq cas pour prouver que l'outil réagit juste

**C1 — référence** formulation lithiée LFP 65 % / PVDF 8 % / Super P 5 % / LATP 17 % / LiTFSI 5 % → **65/100**

**C2 — configuration optimisée** → **82/100** · *l'outil est sensible*

**C3 — défaut provoqué** → **46/100**, probabilité de stabilité 0,35, alerte rouge localisée en Z5 · *l'outil détecte*

**C4 — recommandation chiffrée de l'agent** : quel paramètre, de combien

**C5 — après correction** → **+32 points**, +0,52 de probabilité, alerte levée · *l'outil est réversible, et sa projection se vérifie*

*Sensibilité, détectabilité, réversibilité : les trois propriétés attendues d'un jumeau numérique d'aide à la décision.*

---

# Piloter le projet comme un chef de projet

**Kanban à encours limité (WIP = 1)** — proposition → validation encadrant → développement → tests → démonstration. Aucune brique entamée avant validation de la précédente.

**Jalons tenus** — campagne d'essais du 7 au 13 avril 2026, démonstration client du 16 juin 2026

**Veille structurée** — sources scientifiques, concurrentielles et réglementaires, avec fréquences et impacts documentés

**Risques cartographiés** — qualité et sécurité des données, éthique, enjeux environnementaux, charte formalisée

**Douze incidents de production** tracés, résolus et figés en tests de non-régression

---

# Un prototype vérifié comme un produit

**720** tests automatisés sur 75 fichiers · **100 % au vert** · indépendants de l'ordre d'exécution

Six familles : unitaires purs · interface Streamlit · persistance · non-régression · internationalisation · accessibilité

**×1030** d'accélération mesurée entre table indexée et non indexée

**Chaque incident de production est devenu un test.** C'est ce qui empêche un bug corrigé de revenir.

*La qualité logicielle n'est pas ici un supplément d'âme : c'est ce qui rend le résultat scientifique crédible.*

---

# Ce que je retiens

**Ce qui est acquis** — un jumeau numérique ancré dans la géométrie réelle de la machine, un agent explicable qui recommande sans décider, un modèle validé sous protocole strict, un outil démontrable devant le client.

**Ce qui est assumé** — physique nominale non calibrée industriellement, huit essais d'une seule campagne, pression filière non modélisée.

**Ce que j'ai vraiment appris** — j'ai cru avoir débloqué la situation par l'augmentation de données. C'est en auditant mon propre protocole que j'ai découvert que le gain était un artefact. J'aurais pu livrer 0,918 : personne ne l'aurait vu.

> **Le facteur limitant n'est ni l'algorithme ni la méthode : c'est le nombre d'essais. Passer d'un indicateur expérimental à un prédicteur industriel exigera de nouvelles campagnes — pas un modèle plus sophistiqué.**
