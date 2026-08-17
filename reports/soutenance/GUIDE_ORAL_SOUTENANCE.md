# Guide oral de soutenance — Wilfried Galtier MBEUMI

**Durée visée : 20–25 minutes de présentation + 10–15 minutes de questions**

> Les notes ci-dessous sont aussi intégrées dans les speaker notes du PPTX (mode Présentateur PowerPoint). Ce document est ta feuille de route complète.

---

## SLIDE 1 — TITRE (30 s)

**Ce que tu dis :**

« Bonjour, je suis Wilfried Galtier Mbeumi, étudiant en Mastère 2 Data et Intelligence Artificielle à Nexa Digital School. Mon alternance s'est déroulée chez Rondol Industrie, sous l'encadrement de Maël Gallas. Le sujet : concevoir un jumeau numérique et un système d'IA explicable pour un procédé d'extrusion bivis de composants de batteries tout-solide. »

**Conseil :** Regarde le jury, pas l'écran. Pose ta voix. Cette première phrase donne le ton.

---

## SLIDE 2 — LE VERROU (1 min)

**Ce que tu dis :**

« Les batteries tout-solide promettent plus de densité d'énergie et moins de risque d'incendie. Le blocage n'est plus chimique — il est *procédé*.

La voie humide domine encore, mais elle impose un solvant classé toxique pour la reproduction — la NMP — et un séchage énergivore.

L'extrusion bivis sèche est une alternative continue et sans solvant. C'est le savoir-faire historique de Rondol. Mais elle est très peu documentée pour ces formulations céramiques abrasives.

Le marché aval croît de 37 % par an. L'écart entre les estimations dit tout du caractère pré-industriel du secteur. »

**À retenir :** Le jury doit comprendre que le sujet est à la fois stratégique (marché) et technique (procédé).

---

## SLIDE 3 — CHEZ RONDOL (1 min)

**Ce que tu dis :**

« Concrètement chez Rondol : 81 positions de vis à configurer — un espace combinatoire qu'aucun opérateur ne peut explorer à la main. 13 types d'éléments, chacun changeant l'écoulement et le cisaillement. 12 capteurs de température qui produisent des données utilisées pour la surveillance, jamais pour l'anticipation. Et seulement 8 essais exploitables.

Aujourd'hui, l'opérateur règle par expérience. Personne ne compare objectivement deux configurations. Personne n'anticipe une dérive. »

**Conseil :** Pointe les chiffres sur l'écran en les énonçant. Le contraste entre 81 positions et 8 essais doit frapper.

---

## SLIDE 4 — PROBLÉMATIQUE (1 min)

**Ce que tu dis :**

« D'où la problématique : comment concevoir un système d'aide à la décision qui rende ce procédé lisible, comparable et prédictible — sans jamais devenir une boîte noire ?

Trois exigences ont été fixées dès le cadrage avec Rondol. Traçable : chaque chiffre affiché doit pouvoir être expliqué à un ingénieur procédé. Honnête : ce qui est nominal est annoncé comme tel. Démontrable : ce n'est pas une maquette, c'est un outil qu'on fait tourner devant le client. »

**À retenir :** Insiste sur « non négociables ». Le jury retient mieux les contraintes que les objectifs.

---

## SLIDE 5 — ARCHITECTURE (1 min 30)

**Ce que tu dis :**

« L'architecture est en couches, avec un principe fondateur : envelopper, ne pas recalculer.

En bas, le backbone — screw_logic — Network 7 sur 81 positions. C'est la source unique du remplissage, du temps de séjour et des volumes. Rien d'autre ne calcule ces grandeurs.

Au-dessus, les packages purs : machine, materials, physics. Ils sont bâtis *sur* le backbone, jamais en concurrence avec lui.

Puis le moteur engine, qui enveloppe ces résultats pour construire un état local position par position.

L'agent IA et l'interface Streamlit sont au sommet.

Le calcul procédé est appelé une seule fois. C'est ce qui garantit qu'aucun chiffre affiché ne peut en contredire un autre. »

**Conseil :** C'est une slide technique. Va vite, le jury voit le schéma. Insiste sur le principe fondateur, pas sur chaque couche.

---

## SLIDE 6 — VIS CALCULABLE (1 min)

**Ce que tu dis :**

« Chaque configuration de vis devient un objet calculable, comparable et historisable. Le moteur dérive le taux de remplissage, le temps de séjour, les volumes occupé et libre, puis les agrège par zone thermique.

Ce n'est pas un modèle générique d'extrusion : c'est la géométrie réelle de l'extrudeuse Ø 10,5 mm de Rondol, élément par élément. »

---

## SLIDE 7 — PHYSIQUE (1 min 30)

**Ce que tu dis :**

« Trois briques de physique sont embarquées.

La viscosité locale, via Carreau-Yasuda couplé à une loi d'Arrhénius, avec des presets rhéologiques par matière : LFP, LATP, liants fluorés.

Le couple local, calculé nœud par nœud puis agrégé par zone.

Et l'équation thermique, imposée par l'encadrement industriel.

Ce qui n'est pas fait est écrit. L'énergie mécanique locale, la température avancée et la pression filière restent des briques différées, affichées "À venir" dans l'interface plutôt que remplies de valeurs plausibles. »

**À retenir :** La phrase « ce qui n'est pas fait est écrit » est clé. Elle répond directement à l'exigence d'honnêteté.

---

## SLIDE 8 — AGENT EXPLICABLE (1 min)

**Ce que tu dis :**

« Deux niveaux d'intelligence sont délibérément distingués.

Le Random Forest établit le potentiel prédictif en référence hors ligne. Le SVM avec les règles expertes est intégré au prototype pour l'aide à la décision en démonstration.

Chaque alerte cite sa preuve chiffrée. Chaque recommandation est actionnable : quel paramètre, dans quel sens, de combien.

La décision n'est jamais confiée au modèle statistique. Le modèle prédit un score de stabilité, les règles recommandent, l'humain tranche. Cette séparation est la garantie d'explicabilité. »

---

## SLIDE 9 — LES DONNÉES (1 min 30)

**Ce que tu dis :**

« La campagne d'essais du 7 au 13 avril 2026 a produit 310 000 relevés bruts sur 12 capteurs. Mais seulement 10 à 16 % de couverture par capteur — acquisition fragmentée, codes d'erreur thermocouple à 3276 degrés, doublons.

Après nettoyage et fenêtrage à 60 secondes, on obtient 627 fenêtres exploitables et 87 variables.

Et puis la contrainte structurante, celle qui a tout conditionné : *huit essais*. C'est peu. Je l'ai traité comme la limite du projet, pas comme un détail à contourner. »

**Conseil :** La phrase « huit essais, c'est peu » doit être dite lentement, avec conviction. C'est la transition vers le bloc ML.

---

## SLIDE 10 — SÉPARATION PAR ESSAI (1 min)

**Ce que tu dis :**

« Les fenêtres d'un même essai sont fortement autocorrélées. Les répartir au hasard entre train et test ferait fuir l'information et gonflerait les scores.

Avec la partition aléatoire naïve, on obtient 0,92 de F1-macro. Avec la séparation stricte par essai — Leave-One-Group-Out — on tombe à 0,79.

Quinze points d'écart. Ce n'est pas un défaut à cacher. C'est la mesure de ce que vaut vraiment le modèle. »

---

## SLIDE 11 — LE RÉSULTAT SEMBLAIT DÉCISIF (1 min)

**Ce que tu dis :**

« Huit essais, c'est trop peu. J'ai donc généré 800 fenêtres synthétiques à partir de l'échantillon réel — bootstrap conditionné par classe, jitter borné, imperfections des capteurs reproduites — injectées à l'entraînement uniquement.

Le gain paraissait net : de 0,809 à 0,918 de F1-macro. La variance inter-essais divisée par plus de trois.

J'ai présenté ce résultat comme l'aboutissement du volet prédictif. »

**[Pause de 2 secondes. Regarde le jury.]**

« Il était faux. »

**Conseil :** C'est LE moment de la soutenance. La pause avant « il était faux » est essentielle. Ne la raccourcis pas.

---

## SLIDE 12 — LA FUITE PAR ANCRAGE (1 min 30)

**Ce que tu dis :**

« En auditant mon propre pipeline à la demande de l'encadrement industriel, j'ai trouvé le défaut.

Le pool synthétique était généré une seule fois, à partir des huit essais réels, puis réutilisé dans chaque pli.

L'essai censé être exclu avait donc contribué indirectement à l'entraînement : ses fenêtres servaient de points d'ancrage au bootstrap, ses valeurs alimentaient les écarts-types pilotant le jitter.

Le pli de test ne contenait aucune fenêtre synthétique. La fuite était invisible à la lecture du code.

La correction : régénérer le pool dans chaque pli, à partir des seuls essais d'entraînement. Même algorithme, même volume, même graine. »

---

## SLIDE 13 — LE VRAI RÉSULTAT (1 min)

**Ce que tu dis :**

« Une fois la fuite retirée, le gain disparaît. Sur le Random Forest, on passe de +0,109 à −0,001. Le 0,918 était un artefact.

Aucun modèle n'atteint 0,85. Les cinq restent groupés entre 0,78 et 0,82, avec des écarts-types de 0,13 à 0,17 : statistiquement indiscernables.

Le modèle retenu reste le Random Forest — non pour son score, mais pour son interprétabilité, sa tolérance aux capteurs manquants et sa stabilité inter-essais. »

---

## SLIDE 14 — DIRE LA VÉRITÉ (1 min)

**Ce que tu dis :**

« Pourquoi est-ce que je le dis plutôt que de le taire ?

Déontologique : annoncer 0,918 à Rondol aurait été une promesse que le modèle n'aurait pas tenue en production.

Méthodologique : cette fuite illustre mieux que n'importe quel développement réussi le point central de mon travail — la performance est une propriété du protocole d'évaluation autant que de l'algorithme.

Reproductible : prédictions par pli, métriques et générateur corrigé sont livrés dans le dépôt. Chaque chiffre est recalculable et contestable.

Ce n'est pas l'échec du modèle. C'est la réussite de l'audit. »

**À retenir :** Cette slide montre ta maturité professionnelle. Le jury notera la démarche plus que le score.

---

## SLIDE 15 — VALIDATION EXTERNE (45 s)

**Ce que tu dis :**

« Pour tester la généralisation sans attendre une nouvelle campagne, j'ai généré une base continue de 100 800 lignes et soumis le modèle sans réentraînement.

AUC 0,753 — le pouvoir discriminant subsiste. 62 % des instabilités détectées, avec des erreurs majoritairement conservatrices : fausses alertes plutôt que dérives manquées.

Le modèle reste un indicateur d'aide à la décision — pas un détecteur certifié. »

---

## SLIDE 16 — HMI INDUSTRIELLE (1 min)

**Ce que tu dis :**

« L'application est une HMI industrielle, pas un tableau de bord générique. 7 pages Streamlit : Supervision, Profil de vis, Paramètres IA, Analyse de run, Historique, Moteur procédé, Compte.

La persistance est en trois couches : édition, état validé, historique. L'opérateur ne perd jamais son travail, même après un redémarrage du serveur.

L'accès est protégé par PBKDF2, bilingue français-anglais, avec des contrastes conformes WCAG 2.1 AA. La démo est en ligne et fonctionnelle. »

**Conseil :** Montre la capture d'écran du doigt. Le jury doit voir que c'est un vrai produit, pas un prototype Jupyter.

---

## SLIDE 17 — 5 CAS (1 min 30)

**Ce que tu dis :**

« Cinq scénarios de démonstration pour prouver que l'outil réagit juste.

C1 : configuration de référence avec formulation lithiée LFP. Score 65 sur 100.

C2 : configuration optimisée. Score 82. L'outil est sensible.

C3 : défaut provoqué. Score 46, probabilité de stabilité 0,35, alerte rouge localisée en zone 5. L'outil détecte.

C4 : recommandation chiffrée de l'agent. Quel paramètre, dans quel sens, de combien.

C5 : après correction. +32 points, +0,52 de probabilité, alerte levée. La projection de C4 se vérifie. L'outil est réversible.

Sensibilité, détectabilité, réversibilité : les trois propriétés attendues d'un jumeau numérique d'aide à la décision. »

---

## SLIDE 18 — GESTION DE PROJET (1 min)

**Ce que tu dis :**

« Le pilotage a suivi un Kanban à encours limité, WIP égal à 1. Proposition, validation encadrant, développement, tests, démonstration. Aucune brique entamée avant validation de la précédente.

Les jalons ont été tenus : campagne d'essais en avril 2026, démonstration client le 16 juin 2026.

La veille est structurée — sources scientifiques, concurrentielles et réglementaires. Les risques sont cartographiés : qualité des données, éthique, enjeux environnementaux.

Douze incidents de production ont été tracés, résolus et figés en tests de non-régression. »

---

## SLIDE 19 — QUALITÉ LOGICIELLE (1 min)

**Ce que tu dis :**

« 720 tests automatisés sur 75 fichiers. 100 % au vert. Indépendants de l'ordre d'exécution.

Six familles de tests : unitaires purs, interface Streamlit, persistance, non-régression, internationalisation, accessibilité.

Un facteur 1030 d'accélération mesuré entre table indexée et non indexée.

Chaque incident de production est devenu un test. C'est ce qui empêche un bug corrigé de revenir.

La qualité logicielle n'est pas un supplément d'âme : c'est ce qui rend le résultat scientifique crédible. »

---

## SLIDE 20 — CONCLUSION (1 min 30)

**Ce que tu dis :**

« Réponse à la problématique : oui, le procédé devient lisible, comparable et prédictible. Mais pas autonome.

Ce qui est acquis : un jumeau numérique ancré dans la géométrie réelle de la machine, un agent explicable qui recommande sans décider, un modèle validé sous protocole strict, un outil démontrable devant le client.

Ce qui est assumé : physique nominale non calibrée industriellement, huit essais d'une seule campagne, pression filière non modélisée.

Ce que j'ai vraiment appris : j'ai cru avoir débloqué la situation par l'augmentation de données. C'est en auditant mon propre protocole que j'ai découvert que le gain était un artefact. J'aurais pu livrer 0,918 : personne ne l'aurait vu. »

**[Pause. Regarde le jury.]**

« Le facteur limitant n'est ni l'algorithme ni la méthode : c'est le nombre d'essais. Passer d'un indicateur expérimental à un prédicteur industriel exigera de nouvelles campagnes — pas un modèle plus sophistiqué. »

**Conseil :** La dernière phrase est ta conclusion. Dis-la fermement, sans précipiter.

---

## SLIDE 21 — MERCI / QUESTIONS (10 s)

**Ce que tu dis :**

« Je vous remercie pour votre attention. L'application est en ligne si vous souhaitez la tester. Je suis à votre disposition pour vos questions. »

---

# ANTICIPER LES QUESTIONS DU JURY

## Questions probables et réponses préparées

### 1. « Pourquoi ne pas avoir utilisé un réseau de neurones plus profond ? »

« Avec 8 essais et 627 fenêtres, un réseau profond surapprendrait. Les cinq modèles testés sont statistiquement indiscernables entre 0,78 et 0,82. Le Random Forest a été retenu pour son interprétabilité et sa tolérance aux données manquantes, pas pour son score. Le facteur limitant est le volume de données, pas la complexité du modèle. »

### 2. « La validation externe sur données synthétiques, est-ce vraiment une validation ? »

« Non, ce n'est pas une validation externe au sens strict. C'est une épreuve de transférabilité qui mesure la sensibilité au changement de distribution. Je l'ai volontairement présentée comme telle. La vraie validation viendra de nouvelles campagnes d'essais. Je ne prétends pas autre chose. »

### 3. « Qu'est-ce qui justifie 720 tests pour un prototype ? »

« Chaque incident de production est devenu un test de non-régression. Quand on fait tourner l'outil devant un client, un bug qui revient est plus dommageable que l'absence d'une fonctionnalité. Les tests sont aussi le garant de la crédibilité scientifique : si le logiciel n'est pas reproductible, les résultats ne le sont pas non plus. »

### 4. « La physique est nominale. Quelle est la valeur ajoutée ? »

« La valeur est dans la cohérence. Le moteur procédé ne prétend pas donner une valeur industrielle : il donne un ordre de grandeur physiquement cohérent, qui permet de comparer deux configurations et de détecter des anomalies. C'est suffisant pour l'aide à la décision. La calibration industrielle viendra avec les campagnes futures. »

### 5. « Comment avez-vous géré la relation avec l'encadrant industriel ? »

« Par un processus Kanban : chaque brique était proposée, validée, puis développée. L'équation thermique, par exemple, a été imposée par l'encadrement — je ne l'ai pas choisie. L'audit du pipeline a également été demandé par l'encadrant. Cette rigueur a produit la découverte de la fuite par ancrage. »

### 6. « Pourquoi Streamlit et pas une vraie stack web ? »

« Le choix est pragmatique. Streamlit permet de prototyper une interface industrielle fonctionnelle en Python, dans le même langage que le pipeline ML et le moteur procédé. L'objectif était un outil démontrable, pas un produit SaaS. Si Rondol passe en production, une migration vers une stack web classique est prévue dans la roadmap. »

### 7. « Que feriez-vous différemment si vous recommenciez ? »

« Je mettrais en place la séparation par essai et l'augmentation par pli dès le début, avant même de comparer les modèles. L'erreur n'était pas technique — c'était de ne pas avoir pensé à la fuite par ancrage dès la conception de l'augmentation. L'audit a posteriori a fonctionné, mais il aurait été préférable de prévenir plutôt que de corriger. »

---

# TEMPO ET RYTHME

| Bloc | Slides | Durée | Ton |
|------|--------|--------|-----|
| Introduction | 1–4 | 3 min 30 | Posé, contexte |
| Architecture + Physique | 5–8 | 5 min | Technique, fluide |
| Données + ML | 9–10 | 2 min 30 | Précis, chiffré |
| **Fuite + Audit** | **11–14** | **5 min** | **Narratif, pauses, impact** |
| Validation + App | 15–17 | 3 min 15 | Démonstratif |
| Projet + Tests + Conclusion | 18–21 | 4 min 45 | Affirmé, conclusif |
| **TOTAL** | **21** | **∼24 min** | |

---

# CONSEILS FINAUX

1. **Répète à voix haute** au moins 3 fois avant le jour J. Chronometre-toi.
2. **Le bloc slides 11–14 est ta force.** C'est là que tu te distingues. Ne le bâcle pas.
3. **Regarde le jury**, pas l'écran. Tu connais tes slides.
4. **Bois de l'eau** avant de commencer.
5. **Si une question te déstabilise :** « C'est une très bonne question. Voici ce que je peux répondre... » Gagne 3 secondes.
6. **Ne t'excuse jamais** de la performance du modèle. Tu l'assumes, tu l'expliques, tu proposes la suite. C'est une force, pas une faiblesse.
