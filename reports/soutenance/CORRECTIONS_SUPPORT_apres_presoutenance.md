# Corrections du support — après la pré-soutenance

**Périmètre : le support de présentation uniquement.** Le mémoire n'est pas modifié,
conformément à la consigne. Une réserve à connaître est signalée au point 5.

---

## 1. Diapositive 14 — remplacer la figure du championnat (PRIORITAIRE)

**Le problème** : la figure actuelle affiche Random Forest à **0,796**, en troisième
position derrière le SVM. Le texte de la même diapositive annonce **0,809**. Le
graphique contredit donc le commentaire, à l'écran, en grand — et un jury qui le
remarque en conclut que le modèle retenu n'est pas le meilleur.

Origine : la figure était générée depuis une campagne de mesure du 7 juillet, alors
que le mémoire publie celle du 31 juillet (fold-aware).

**Action** : remplacer l'image par le fichier régénéré

```
figures_memoire/fig_championnat_modeles.png
```

Random Forest y est premier à 0,809, comme dans le Tableau 8 du mémoire.

---

## 2. Supprimer les images génératives décoratives

Elles n'apportent aucune information et se repèrent immédiatement.

| Diapositive | Ce qu'il faut retirer | Pourquoi |
|---|---|---|
| **14** | L'image de droite | Elle affiche en gros `CHAMPIANISHIP`, `NE LEARNING MODELSTOMPE`, `MCDLIY`, `Aia Sctence` — du charabia lisible à cinq mètres |
| **6** | La photo de gauche | Un homme devant un tableau SWOT **en anglais**, qui fait doublon avec ta vraie figure juste à côté |

Vérifie aussi les diapositives 8, 11, 18, 20 : partout où une image de fond passe
sous du texte ou sous une figure, elle nuit à la lecture sans rien ajouter.

**Règle simple** : une image reste si elle porte de l'information (une figure, une
capture de l'application). Sinon elle part.

---

## 3. Ajouter une diapositive « Augmentation de données »

À insérer **juste après la diapositive 16** (Le vrai résultat).

C'est la réponse directe à la remarque « le dataset est trop petit » — et elle
retourne complètement la critique.

> ### L'augmentation de données : testée, mesurée, sans effet
>
> Base synthétique de **100 800 lignes** générée à partir des huit essais réels.

| Modèle | Sans augmentation | Avec augmentation (par pli) | Gain |
|---|---|---|---|
| **Random Forest** | 0,809 | **0,809** | −0,001 |
| SVM (RBF) | 0,805 | 0,824 | +0,018 |
| Régression logistique | 0,799 | 0,809 | +0,010 |
| XGBoost | 0,757 | 0,801 | +0,044 |
| Réseau de neurones (MLP) | 0,778 | 0,781 | +0,004 |

> Le synthétique **ne crée pas d'information absente des données réelles**.
> Mon premier protocole annonçait +0,109 : le pool était généré une seule fois sur
> les huit essais, donc l'essai de test alimentait indirectement l'entraînement.
> Régénéré dans chaque pli, le gain disparaît.

**Ce que tu dis (45 s)**

> « On me demande souvent pourquoi je ne compense pas le faible volume par des
> données synthétiques. Je l'ai fait : 100 800 lignes générées depuis mes huit
> essais, employées de deux façons — en validation externe, où le modèle conserve
> 0,753 d'AUC, et en augmentation d'entraînement sur les cinq modèles.
>
> Le gain va de +0,001 à +0,044 selon le modèle, et il est nul pour celui que je
> retiens. La conclusion est nette : le synthétique ne remplace pas des essais
> réels, il ne fait que redistribuer l'information déjà présente. »

---

## 4. Ajouter une diapositive « Pourquoi ces cinq modèles »

À insérer **juste avant la diapositive 14** (Championnat).

Question annoncée comme récurrente par la référente.

> ### Cinq familles, pas cinq algorithmes au hasard

| Modèle | Ce qu'il teste | Pourquoi lui |
|---|---|---|
| Régression logistique | Séparabilité linéaire | Référence basse, entièrement interprétable |
| SVM (RBF) | Frontières non linéaires | Robuste quand les échantillons sont peu nombreux |
| Random Forest | Ensemble par *bagging* | Donne l'importance des variables — exigence d'explicabilité |
| XGBoost | Ensemble par *boosting* | Référence sur données tabulaires |
| Réseau de neurones (MLP) | Non-linéarité profonde | Vérifie qu'un modèle plus expressif n'apporte rien ici |

> **Écartés volontairement** : l'apprentissage profond (huit essais, il mémoriserait
> les essais au lieu du procédé) et les modèles séquentiels type LSTM (les fenêtres
> de 60 s sont déjà agrégées en 87 descripteurs, la dimension temporelle fine a
> disparu).

**Ce que tu dis (30 s)**

> « Ces cinq modèles ne sont pas un échantillon arbitraire : ils couvrent l'espace
> des hypothèses. Un linéaire pour la référence, un à marges pour les frontières
> non linéaires, deux ensembles — un par bagging, un par boosting — et un réseau
> pour vérifier qu'une plus grande expressivité n'apporte rien. Le fait qu'ils
> finissent tous entre 0,78 et 0,82 est en soi un résultat : à ce volume de
> données, le choix de l'algorithme n'est pas le levier. »

---

## 5. Réserve à connaître — ne pas la découvrir devant le jury

Après ces corrections, **le support sera cohérent** (graphique, texte et Tableau 8
du mémoire diront tous 0,809).

Mais la **Figure 11 du mémoire déposé** continuera d'afficher 0,796 et de placer le
Random Forest en troisième position, en contradiction avec son propre Tableau 8.
Le mémoire n'est pas modifié, c'est un choix assumé : le régénérer pour trois
décimales ferait courir plus de risques qu'il n'en éviterait.

**Si la question tombe :**

> « Vous avez raison, la Figure 11 et le Tableau 8 de mon mémoire divergent. Ils
> proviennent de deux campagnes de mesure : la figure d'un premier passage
> Leave-One-Group-Out en juillet, le tableau de la campagne finale fold-aware. Le
> chiffre de référence est celui du tableau — 0,809. La figure aurait dû être
> régénérée, c'est une erreur de ma part que j'ai corrigée depuis sur le support. »

Un jury pardonne une erreur assumée. Il ne pardonne pas une contradiction qu'on
n'avait pas vue.

---

## 6. Garder 27 diapositives : deux fusions

Ajouter deux diapositives sans en retirer ferait 29, donc plus de 30 minutes.

| Fusionner | En |
|---|---|
| **23** (Veille) + **24** (Budget) | Une seule diapositive « Veille & budget » — elles n'avaient été séparées que pour contourner une limite de Gamma |
| **19** (HMI Supervision) + **20** (Profil & Moteur) | Une seule « L'application » — la démonstration live montre déjà les deux pages |

---

## 7. Ce que je ne recommande pas

**Fabriquer trois cas d'utilisation supplémentaires.** Tu en as déjà cinq (C1 à C5).
Avant d'en produire d'autres, il faut savoir ce que la référente visait :

- soit elle **ne les a pas vus** — alors le problème est qu'ils ne sont pas joués en
  direct, pas qu'ils manquent ;
- soit elle parle de **cas d'usage métier** (un opérateur en prise de poste, un
  ingénieur R&D qui compare deux configurations, un responsable qui audite un lot
  raté), ce qui n'est pas la même chose que des cas de test.

Mon interprétation : la seconde. Tes C1–C5 prouvent que l'outil *réagit* ; elle veut
savoir à quoi il *sert*, et pour qui. À clarifier avec elle avant de produire quoi
que ce soit.

---

## Récapitulatif

| # | Action | Temps | Risque |
|---|---|---|---|
| 1 | Remplacer la figure du championnat | 2 min | nul |
| 2 | Supprimer les images génératives (6, 14, puis vérifier 8, 11, 18, 20) | 10 min | nul |
| 3 | Ajouter « Augmentation de données » | 15 min | nul |
| 4 | Ajouter « Pourquoi ces cinq modèles » | 15 min | nul |
| 6 | Fusionner 23+24 et 19+20 | 10 min | faible |

Puis réexporter en PDF sous le nom `MBEUMI_Wilfried_PREZ.pdf`.
