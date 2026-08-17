# Rendre un procédé d'extrusion lisible, comparable et prédictible

**Jumeau numérique et IA explicable pour l'extrusion bivis de composants de batteries tout-solide**

Wilfried Galtier MBEUMI · Mastère 2 Data & Intelligence Artificielle · Nexa Digital School
Encadrement industriel : Maël Gallas — Rondol Industrie · Année 2025–2026

---

# La chimie progresse. La mise en forme reste le verrou.

Batteries tout-solide : extrusion sèche / semi-sèche

**Voie humide** — Solvant NMP toxique pour la reproduction, séchage énergivore. Dominante mais contrainte.

**Extrusion sèche** — Procédé continu, sans solvant. Savoir-faire historique de Rondol.

**Verrou actuel** — Formulations céramiques abrasives, très peu documentées. Espace combinatoire énorme.

| Indicateur | Valeur |
|---|---|
| Marché aval 2025 | 0,26 Md USD |
| Marché aval 2031 | 1,77 Md USD |
| TCAC | 37,5 % |

Secteur pré-industriel : l'écart entre les estimations dit tout.

---

# Chez Rondol, le problème est concret

Extrudeuse bivis Ø 10,5 mm · campagne d'essais avril 2026

| Chiffre | Détail |
|---|---|
| **81** | positions de vis à configurer |
| **13** | types d'éléments disponibles |
| **12** | capteurs de température — surveillance uniquement |
| **8** | essais exploitables — une seule campagne |

L'opérateur règle par expérience. Rien ne compare deux configurations. Rien n'anticipe une dérive.

---

# Une question, trois exigences non négociables

> **Comment concevoir un système d'aide à la décision qui rende un procédé d'extrusion bivis lisible, comparable et prédictible — sans jamais devenir une boîte noire ?**

**TRAÇABLE** — Toute valeur affichée doit pouvoir être expliquée à un ingénieur procédé.

**HONNÊTE** — Ce qui n'est pas calibré industriellement est annoncé comme tel.

**DÉMONTRABLE** — Un outil réellement utilisable devant le client, pas une maquette.

---

# Une architecture en couches : envelopper, ne pas recalculer

Le calcul procédé est appelé **une seule fois**. Tout le reste réutilise son résultat.

**Couche 0 — Backbone** · `screw_logic.py` · Network 7 sur 81 positions. Source unique du remplissage, du temps de séjour et des volumes.

**Couche 1 — Packages purs** · `machine/` `materials/` `physics/` — catalogues et formules bâtis sur le backbone, jamais en concurrence.

**Couche 2 — Moteur** · `engine/` — état local position par position : viscosité, couple, agrégats par zone.

**Couche 3 — Agent IA** · règles métier explicables → alertes et recommandations chiffrées.

**Couche 4 — Interface** · 7 pages Streamlit, bilingue, persistance en trois couches.

*Principe fondateur : aucun chiffre affiché ne peut contredire un autre.*

---

# La vis devient un objet calculable et comparable

Géométrie réelle Rondol Ø 10,5 mm · 81 positions

Ce n'est pas un modèle générique : c'est la géométrie de l'extrudeuse de Rondol, élément par élément.

**Profil fonctionnel :**
Convoyage → Malaxage / cisaillement → Restriction → Pompage filière

**Grandeurs dérivées par le moteur :**
- Taux de remplissage
- Temps de séjour
- Volume occupé / libre
- Agrégation par zone thermique

Network 7 appelé exactement une fois — grandeurs consommées, jamais recalculées.

---

# La physique embarquée — nominale, et annoncée comme telle

| Brique | Formule | Détail |
|---|---|---|
| Viscosité locale | η(γ̇, T) | Carreau-Yasuda + Arrhénius · Presets par matière (LFP, LATP, liants fluorés) |
| Couple local | M = η·γ̇²·V / 2πN | Calcul nœud par nœud puis agrégation par zone |
| Équation thermique | T = Tc + (2πNM)/(ṁCp) + kτ | Imposée par l'encadrement industriel |

**Ce qui n'est pas fait est écrit** — E5 / E6 / E7 restent différées : l'interface affiche « À venir » plutôt qu'une valeur plausible.

---

# Le modèle prédit. Les règles expliquent. L'humain décide.

**Deux niveaux d'intelligence distincts :**

| Niveau | Rôle | Usage |
|---|---|---|
| Random Forest | Potentiel prédictif | Référence hors ligne |
| SVM + règles expertes | Aide à la décision | Démonstration client |

**Flux de décision :**
État procédé → Règles métier → Alertes chiffrées → Recommandations actionnables

**Exemple d'alerte :**
> SME = 0,60 kWh/kg · seuil de vigilance = 0,30 · source : KPIs vis (état appliqué)

Chaque recommandation précise : **quel paramètre, dans quel sens, de combien.**

La décision n'est jamais confiée au modèle statistique. Le modèle prédit, les règles recommandent, l'humain tranche.

---

# Les données : une campagne réelle, et son revers

7–13 avril 2026 · 12 fichiers CSV · capteurs de température

| Indicateur | Valeur |
|---|---|
| Relevés bruts | 310 782 |
| Capteurs | 12 |
| Couverture par capteur | 10–16 % |
| Fenêtres de 60 s après nettoyage | 627 |
| Variables | 87 (12 × 7 stats + 3 gradients) |

**Pipeline :** 12 CSV bruts → Nettoyage → Fenêtrage 60 s → 87 variables → Modèle ML

> **8 essais seulement — limite structurelle du projet, pas un détail à contourner.**

---

# La séparation par essai change la vérité du modèle

Leave-One-Group-Out : un essai entier écarté à chaque pli. 87,5 % des fenêtres en entraînement. Aucun essai simultanément dans train et test.

| Protocole | F1-macro |
|---|---|
| Partition aléatoire naïve | **0,92** |
| Séparation stricte par essai (LOGO) | **0,79** |
| **Écart** | **15 points** |

**15 points d'écart. Ce n'est pas un défaut à cacher : c'est la mesure de ce que vaut vraiment le modèle.**

---

# Premier résultat : ce que je croyais avoir obtenu

Augmentation globale : 800 fenêtres synthétiques injectées à l'entraînement uniquement. Bootstrap conditionné par classe, jitter borné, imperfections capteurs reproduites.

| Métrique | Sans augmentation | Avec augmentation |
|---|---|---|
| F1-macro (RF) | 0,809 | **0,918** |
| Écart-type | 0,176 | 0,054 |

Variance inter-essais divisée par plus de trois.

J'ai présenté ce résultat comme l'aboutissement du volet prédictif.

**Il était faux.**

---

# L'audit : une fuite par ancrage

En auditant mon propre pipeline à la demande de l'encadrement industriel, j'ai trouvé le défaut.

**Le mécanisme de la fuite :**

1. Le pool synthétique était généré **une seule fois**, à partir des **8 essais réels**
2. Ce pool était réutilisé dans **chaque pli** de la validation croisée
3. L'essai censé être exclu avait contribué **indirectement** à l'entraînement
4. Ses fenêtres servaient de **points d'ancrage** au bootstrap, ses valeurs alimentaient le jitter

Le pli de test ne contenait aucune fenêtre synthétique. **La fuite était invisible à la lecture du code.**

**Correction :** régénérer le pool dans chaque pli, uniquement depuis les essais d'entraînement. Même algorithme, même volume, même graine.

---

# Le vrai résultat : le gain disparaît

F1-macro Leave-One-Group-Out — comparaison des trois protocoles :

| Modèle | Sans augm. | Globale (fuitée) | Par pli (corrigée) | Δ réel |
|---|---|---|---|---|
| **Random Forest ★** | **0,809** | **0,918** | **0,809** | **−0,001** |
| SVM (RBF) | 0,805 | 0,868 | 0,824 | +0,019 |
| Régression logistique | 0,799 | 0,860 | 0,809 | +0,010 |
| XGBoost | 0,757 | 0,900 | 0,801 | +0,044 |
| Réseau de neurones | 0,778 | 0,862 | 0,781 | +0,003 |

Sur le Random Forest, le gain passe de **+0,109 à −0,001**. Le 0,918 était un artefact.

Aucun modèle n'atteint 0,85. Les cinq restent groupés entre 0,78 et 0,82 : **statistiquement indiscernables**.

---

# Pourquoi je le dis plutôt que de le taire

Le résultat corrigé vaut davantage qu'un score flatteur.

**DÉONTOLOGIQUE** — Ne pas promettre à Rondol une performance qui ne tiendrait pas en production.

**MÉTHODOLOGIQUE** — Montrer que la performance dépend autant du protocole que de l'algorithme.

**REPRODUCTIBLE** — Livrer prédictions, métriques et générateur corrigé afin que chaque chiffre soit contestable.

> **Ce n'est pas l'échec du modèle : c'est la réussite de l'audit.**

---

# Validation externe : le modèle conserve un signal

Validation sur base simulée de 100 800 lignes, sans réentraînement.

| Métrique | Valeur |
|---|---|
| Fenêtres évaluées | 3 479 |
| Runs simulés | 15 |
| AUC | **0,753** |
| Instabilités détectées | **62 %** |
| Type d'erreurs | Majoritairement conservatrices (fausses alertes > dérives manquées) |

L'écart mesure la sensibilité au changement de distribution.

**Le modèle reste un indicateur d'aide à la décision — pas un détecteur certifié.**

---

# L'application : une HMI industrielle, pas un tableau de bord

7 pages Streamlit : Supervision · Profil de vis · Paramètres IA · Analyse de run · Historique · Moteur procédé · Compte

| Fonctionnalité | Détail |
|---|---|
| Persistance | 3 couches : édition → état validé → historique |
| Sécurité | Mots de passe hachés PBKDF2, jamais en clair |
| Internationalisation | Bilingue FR / EN |
| Accessibilité | Contrastes 6,38:1 à 18,39:1 — conformes WCAG 2.1 AA |
| Déploiement | En ligne : rondol-process-supervision-demo.streamlit.app |

L'opérateur ne perd jamais son travail, même après un redémarrage du serveur.

---

# Cinq cas prouvent que l'outil réagit juste

Sensibilité · Détectabilité · Réversibilité

| Cas | Scénario | Score | Résultat |
|---|---|---|---|
| C1 | Référence LFP | 65/100 | Baseline établie |
| C2 | Configuration optimisée | 82/100 | L'outil est sensible |
| C3 | Défaut provoqué zone 5 | 46/100 | Alerte rouge, P(stabilité) = 0,35 |
| C4 | Recommandation de l'agent | — | Quel paramètre, quel sens, combien |
| C5 | Après correction | +32 pts | Alerte levée, +0,52 de probabilité |

C3 → C5 : +32 points, +0,52 de probabilité, alerte levée — la projection de C4 se vérifie.

**Sensibilité, détectabilité, réversibilité : les trois propriétés attendues d'un jumeau numérique d'aide à la décision.**

---

# Le projet piloté par validation, pas par accumulation

Kanban à encours limité (WIP = 1)

| Étape | Contenu |
|---|---|
| Proposition | Architecture en couches · Pipeline ML · Équation thermique |
| Validation encadrant | Audit fuite augmentation · Persistance 3 couches |
| Développement | Agent IA v1 · Moteur engine/ · Viscosité · Couple |
| Tests | 720 tests automatisés · 100 % vert |
| Démonstration | Client — 16 juin 2026 |

**Aucune brique entamée avant validation de la précédente.**

**Veille structurée** — Sources scientifiques, concurrentielles et réglementaires.

**Risques cartographiés** — Qualité et sécurité des données, éthique, enjeux environnementaux.

**12 incidents de production** tracés, résolus et figés en tests de non-régression.

**Jalons tenus** — Campagne d'essais 7–13 avril 2026. Démonstration client 16 juin 2026.

---

# La qualité logicielle protège la crédibilité scientifique

| Indicateur | Valeur |
|---|---|
| Tests automatisés | 720 |
| Fichiers de test | 75 |
| Taux de réussite | 100 % |
| Accélération indexée | ×1030 |
| Incidents figés en tests | 12 |

**Six familles :** unitaires purs · interface Streamlit · persistance · non-régression · internationalisation · accessibilité

**Chaque incident de production est devenu un test.** C'est ce qui empêche un bug corrigé de revenir.

> **Un résultat scientifique n'est crédible que si le logiciel qui le produit est reproductible, testable et observable.**

---

# Ce que je retiens

**Réponse à la problématique :** Oui — le procédé devient lisible, comparable et prédictible. Mais pas autonome.

| Dimension | Contenu |
|---|---|
| **ACQUIS** | Jumeau numérique cohérent, agent explicable, HMI démontrable, modèle validé sous protocole strict |
| **ASSUMÉ** | Physique nominale, huit essais, pression filière différée. Le cadre est explicite |
| **APPRIS** | La rigueur du protocole vaut davantage qu'un score flatteur. Le gain était un artefact |

> **« J'aurais pu livrer 0,918 : personne ne l'aurait vu. »**

Le prochain gain viendra de nouvelles campagnes — pas d'un modèle plus sophistiqué.

---

# Merci. Questions et échanges.

Wilfried Galtier MBEUMI
mbeumigautier@gmail.com

**Démo en ligne :** rondol-process-supervision-demo.streamlit.app
