# Bloc 1 — Présentation sans interruption (30 minutes)

**Support** : `MBEUMI_Wilfried_PREZ.pdf` — 27 diapositives
**Budget** : 24 min de diapositives + 5 min de démonstration live + 1 min de marge

> ⚠️ Ce script est calé sur les **27 diapositives réelles** du support déposé.
> L'ancien `GUIDE_ORAL_SOUTENANCE.md` était calé sur 21 diapositives et présentait
> un décalage de +3 à +6 : ne l'utilise plus pour le minutage.

---

## Tableau de marche — à mémoriser

| # | Diapositive | Durée | Cumul |
|---|-------------|-------|-------|
| 1 | Titre | 0:30 | 0:30 |
| 2 | Déroulé | 0:20 | 0:50 |
| 3 | Rondol Industrie | 1:00 | 1:50 |
| 4 | Marché batteries tout-solide | 1:00 | 2:50 |
| 5 | Analyse concurrentielle | 0:35 | 3:25 |
| 6 | Analyse SWOT | 0:35 | 4:00 |
| 7 | Une question, trois exigences | 1:15 | 5:15 |
| 8 | Architecture en couches | 1:15 | 6:30 |
| 9 | La vis, objet calculable | 1:15 | 7:45 |
| 10 | Physique embarquée | 1:15 | 9:00 |
| 11 | Le modèle prédit, les règles expliquent | 1:15 | 10:15 |
| 12 | Campagne réelle — 8 essais | 1:15 | 11:30 |
| 13 | La séparation par essai | 1:15 | 12:45 |
| 14 | Championnat de cinq modèles | 0:45 | 13:30 |
| 15 | **Le résultat semblait décisif** | 1:20 | 14:50 |
| 16 | Le vrai résultat | 1:15 | 16:05 |
| 17 | Dire la vérité | 0:45 | 16:50 |
| 18 | Validation externe | 1:00 | 17:50 |
| 19 | HMI Supervision → **DÉMO LIVE** | 0:30 + 5:00 | 23:20 |
| 20 | Profil de vis & Moteur | 0:30 | 23:50 |
| 21 | Cinq cas | 1:15 | 25:05 |
| 22 | Piloté par validation | 0:45 | 25:50 |
| 23 | Veille structurée | 0:35 | 26:25 |
| 24 | Budget | 0:20 | 26:45 |
| 25 | Indicateurs & qualité | 0:45 | 27:30 |
| 26 | Conclusion | 1:15 | 28:45 |
| 27 | Merci | 0:15 | 29:00 |

**Trois points de contrôle** — si tu dérives de plus d'une minute, coupe dans les diapositives 5, 6, 22, 23, 24 :

- **À 9:00** tu dois finir la physique (diapo 10)
- **À 17:50** tu dois lancer la démo (diapo 19)
- **À 25:05** tu dois avoir fini les cinq cas (diapo 21)

---

## 1 — Titre · 0:30

**Ce que tu dis**

> Bonjour. Je m'appelle Wilfried MBEUMI, je présente le travail réalisé chez Rondol Industrie, à Nancy, sous l'encadrement de Maël Gallas.
>
> Le sujet : concevoir et déployer un système d'intelligence artificielle prédictif d'aide à la décision pour l'extrusion bivis de composants de batteries tout-solide.
>
> En une phrase : rendre un procédé industriel lisible, comparable et prédictible — sans jamais faire passer une valeur non calibrée pour une mesure.

*Ne lis pas la diapositive. Regarde le jury. Cette phrase donne le ton de toute la soutenance.*

---

## 2 — Déroulé · 0:20

> Huit parties : le contexte et le marché, la problématique, la solution technique, les données et la modélisation, les résultats — dont un audit qui a changé mes conclusions —, l'application avec une démonstration en direct, la gestion de projet, et la conclusion.

*Enchaîne vite. Personne ne retient un sommaire.*

---

## 3 — Rondol Industrie · 1:00

> Rondol est une PME deeptech française fondée en 2012, spécialisée dans l'extrusion bivis de laboratoire et de pré-série. Des extrudeuses de 10,5 et 21 millimètres de diamètre, en configuration horizontale et verticale.
>
> C'est une niche : là où Coperion ou Thermo Fisher font de la production, Rondol fait de la R&D. Double nomination au Prix Galien, en 2020 et 2023, et des brevets sur les configurations de vis modulaires.
>
> Trois valeurs structurent leur offre — et elles ont structuré mon projet : la précision de la géométrie, la reproductibilité entre configurations, et l'accessibilité pour la recherche.

**Chiffres** : 2012 · Ø 10,5 et 21 mm · Prix Galien 2020 et 2023

---

## 4 — Marché des batteries tout-solide · 1:00

> Le marché qui tire le projet, c'est la batterie tout-solide. 0,26 milliard de dollars en 2025, 1,77 milliard attendu en 2031 selon MarketsandMarkets, soit une croissance annuelle de 37,5 %. Grand View Research projette 15,65 milliards à l'horizon 2030 sur un périmètre plus large.
>
> Aujourd'hui, la voie dominante est humide : elle utilise un solvant, la NMP, toxique, et impose un séchage énergivore. Elle est sous pression réglementaire avec la restriction PFAS portée par l'ECHA.
>
> Rondol travaille la voie sèche : procédé continu, sans solvant. Le problème, c'est que ces formulations céramiques sont abrasives et très peu documentées. Chaque essai coûte cher en matière active.

**Chiffres** : 0,26 → 1,77 Md$ · CAGR 37,5 % · 15,65 Md$ horizon 2030

**Piège** — *« D'où viennent ces chiffres ? »* → Deux cabinets distincts, MarketsandMarkets et Grand View Research, sur des périmètres différents. Je cite les deux plutôt que de choisir le plus flatteur.

---

## 5 — Analyse concurrentielle · 0:35

> Deux concurrents directs : Coperion, leader mondial, très forte capacité, mais pas d'offre laboratoire miniaturisée ni de jumeau numérique. Thermo Fisher, présent sur le segment labo, mais avec une approche générique, sans personnalisation de la géométrie de vis.
>
> En indirect, Leistritz et ENTEK, plutôt sur la production.
>
> Le positionnement de Rondol, c'est la miniaturisation à 10,5 millimètres, les brevets, et — avec ce projet — un jumeau numérique qu'aucun de ces acteurs ne propose sur ce segment.

*Diapositive à débit rapide. Le tableau se lit tout seul.*

---

## 6 — Analyse SWOT · 0:35

> En synthèse : les forces sont la précision, les brevets et l'héritage pharmaceutique. Les faiblesses, une structure PME et peu de données terrain. Les opportunités, la croissance du tout-solide et la pression anti-solvant. Les menaces, des concurrents mieux dotés et une adoption encore lente de l'IA en milieu industriel.

*Ne détaille aucune case. Le jury lit plus vite que tu ne parles.*

---

## 7 — Une question, trois exigences · 1:15

> Ma problématique : **comment concevoir un système d'aide à la décision qui rende un procédé d'extrusion bivis lisible, comparable et prédictible ?**
>
> Je l'ai déclinée en trois exigences que je me suis imposées, et qui ont arbitré toutes mes décisions techniques.
>
> **Traçable** : toute valeur affichée doit être explicable à un ingénieur procédé. Pas de boîte noire qui sort un nombre.
>
> **Honnête** : ce qui n'est pas calibré doit être annoncé comme tel. C'est l'exigence qui m'a coûté le plus cher, et j'y reviendrai.
>
> **Démontrable** : l'outil doit être utilisable devant un client, pas une maquette de démonstration.

*Marque un temps après « prédictible ». C'est la charnière de la présentation.*

---

## 8 — Architecture en couches · 1:15

> L'architecture repose sur un principe fondateur : **envelopper, ne pas recalculer.**
>
> À la base, `screw_logic`, le module métier qui modélise la géométrie réelle de la vis Rondol — 81 positions — et exécute le calcul procédé appelé Network 7. C'est la seule source de vérité pour le remplissage, le débit et le temps de séjour.
>
> Au-dessus, des couches pures — machine, matériaux, physique — qui importent ce socle sans jamais redéfinir ses constantes. Puis le moteur, qui enveloppe l'état calculé position par position. Puis l'agent, et enfin l'interface.
>
> Le point clé : Network 7 est appelé **une seule fois**. Tout le reste réutilise son résultat. C'est ce qui garantit qu'un chiffre affiché sur une page est le même que sur une autre.

**Chiffres** : 81 positions · 1 seul appel Network 7 · 5 couches

**Piège** — *« Pourquoi cette contrainte ? »* → Parce que recalculer, c'est dupliquer une hypothèse. Deux calculs indépendants divergent toujours à un moment, et l'utilisateur ne sait plus lequel croire.

---

## 9 — La vis devient un objet calculable · 1:15

> La vis n'est pas un modèle générique : c'est la géométrie réelle Rondol, 10,5 millimètres.
>
> 81 positions, 13 types d'éléments, 8 zones thermiques. Chaque configuration se lit comme une séquence — convoyage, malaxage, cisaillement, restriction, filière.
>
> À partir de cette géométrie, le moteur dérive le taux de remplissage, le temps de séjour, le volume occupé et le volume libre, agrégés par zone.
>
> C'est ce qui rend deux configurations **comparables** : on ne compare plus des impressions d'opérateur, on compare des volumes et des temps.

**Chiffres** : 81 positions · 13 types d'éléments · 8 zones thermiques

---

## 10 — Physique embarquée · 1:15

> Trois blocs de physique, et je vais être précis sur leur statut.
>
> La viscosité locale, avec un modèle de Carreau-Yasuda couplé à une loi d'Arrhenius pour la dépendance en température.
>
> Le couple local, nœud par nœud : viscosité fois taux de cisaillement au carré fois volume rempli, sur deux pi N.
>
> Et l'équation thermique, imposée par l'encadrement industriel : la température réelle vaut la consigne, plus le terme de dissipation mécanique, plus un terme de temps de séjour.
>
> **Ces valeurs sont nominales et non calibrées industriellement.** Trois équations — pression en filière, température réelle mesurée, énergie par nœud — sont volontairement différées. L'interface affiche « À venir » plutôt qu'un nombre invérifiable.

*C'est ici que se joue ta crédibilité. Dis « nominales, non calibrées » sans baisser la voix.*

---

## 11 — Le modèle prédit, les règles expliquent · 1:15

> L'intelligence du système fonctionne à deux niveaux, et c'est un choix, pas une contrainte technique.
>
> Premier niveau, un modèle d'apprentissage — une forêt aléatoire sur des fenêtres de 60 secondes et 87 variables — qui estime une probabilité de stabilité du procédé.
>
> Deuxième niveau, un agent à règles explicites : **onze règles**, chacune traçable. Quand une alerte se déclenche, l'opérateur voit quel paramètre est en cause, dans quel sens il doit bouger, et de combien.
>
> Le modèle donne le **quoi**. Les règles donnent le **pourquoi** et le **comment**. L'humain décide.
>
> Un exemple concret : la onzième règle détecte le débordement au point d'injection. Le remplissage moyen sature autour de 0,44 — une vis gavée à la trémie restait donc invisible. Il a fallu remonter le drapeau local du moteur pour la voir.

**Chiffres** : 11 règles · fenêtre 60 s · 87 variables

**Piège** — *« Pourquoi pas un modèle plus profond ? »* → 8 essais. Un réseau profond aurait mémorisé les essais au lieu d'apprendre le procédé. Voir `02`, question 1.

---

## 12 — Campagne réelle, 8 essais exploitables · 1:15

> Les données viennent d'une campagne réelle menée du 7 au 13 avril 2026 chez Rondol : 12 fichiers de capteurs de température, 310 782 relevés bruts.
>
> Après nettoyage et fenêtrage à 60 secondes, j'obtiens 627 fenêtres décrites par 87 variables — statistiques de position, de dispersion, de tendance et de dynamique sur chaque voie.
>
> Mais le chiffre qui compte, c'est celui-ci : **8 essais exploitables.** C'est peu. Toute la suite de mon protocole découle de cette contrainte.

**Chiffres** : 310 782 relevés · 627 fenêtres · 87 variables · **8 essais**

*Annonce « 8 essais » toi-même, avec aplomb. Si tu ne le dis pas, on te le sortira comme une objection.*

---

## 13 — La séparation par essai change la vérité · 1:15

> Avec 8 essais et des mesures autocorrélées, la façon de découper les données décide du résultat.
>
> Si je partitionne au hasard, des fenêtres du même essai se retrouvent en apprentissage et en test. Le modèle reconnaît l'essai, pas le phénomène. J'obtiens 0,92 de F1-macro.
>
> Si j'écarte un **essai entier** à chaque pli — c'est le Leave-One-Group-Out —, le modèle affronte une situation qu'il n'a jamais vue. J'obtiens 0,79.
>
> **Quinze points d'écart.** Le premier chiffre est flatteur et faux, le second est la vraie mesure de ce que vaut le modèle face à un essai inconnu. J'ai retenu le second.

**Chiffres** : 0,92 aléatoire vs 0,79 LOGO · 15 points

---

## 14 — Championnat de cinq modèles · 0:45

> J'ai comparé cinq familles sous le même protocole : forêt aléatoire, SVM à noyau gaussien, régression logistique, XGBoost et un perceptron multicouche.
>
> La forêt aléatoire est retenue : 0,809 de F1-macro, 0,950 d'exactitude, 0,976 d'aire sous la courbe. Le SVM est conservé comme challenger documenté dans l'application.

**Chiffres** : RF 0,809 / 0,950 / 0,976

---

## 15 — Le résultat semblait décisif · 1:20

> Voici le moment le plus important de ma présentation.
>
> Pour compenser le faible volume de données, j'ai généré des échantillons synthétiques. Le résultat était spectaculaire : le F1-macro passait de 0,809 à **0,918**. Plus de dix points. J'avais de quoi conclure que l'augmentation de données résolvait mon problème de volume.
>
> En auditant le protocole, j'ai trouvé une **fuite par ancrage**. Le pool synthétique était généré une seule fois, à partir des huit essais réels — donc y compris l'essai qui servait de test. Les points d'ancrage du tirage et les écarts-types de classe portaient l'information de l'essai exclu. Cet essai contribuait indirectement à l'entraînement.
>
> Le 0,918 était un artefact. Le protocole correct consiste à régénérer le pool **dans chaque pli**, à partir des seuls essais d'entraînement.

*Ralentis. Ne survole pas. C'est ce passage qu'on retiendra de toi.*

**Chiffres** : 0,809 → 0,918 (fuité)

---

## 16 — Le vrai résultat · 1:15

> Après correction, le gain disparaît.
>
> La forêt aléatoire revient exactement à 0,809 — un delta réel de moins un millième. Les cinq modèles se retrouvent entre 0,78 et 0,82, statistiquement indiscernables compte tenu de l'écart-type de ± 0,126 entre les plis.
>
> Autrement dit : **l'augmentation de données n'apportait rien.** Le gain de plus de dix points que j'avais mesuré n'existait pas.
>
> J'ai gardé l'ancien fichier de résultats dans le dépôt, marqué comme périmé, avec la raison de son invalidation. La traçabilité de l'erreur fait partie du livrable.

**Chiffres** : 0,809 corrigé · ± 0,126 · cinq modèles entre 0,78 et 0,82

---

## 17 — Dire la vérité renforce le projet · 0:45

> Pourquoi avoir publié ça plutôt que de garder le chiffre flatteur ?
>
> Trois raisons. **Déontologique** : je ne peux pas promettre à Rondol une performance qui ne tiendrait pas en production. **Méthodologique** : ce résultat démontre que la performance dépend autant du protocole que de l'algorithme — c'est le vrai enseignement du projet. **Reproductible** : les prédictions, les métriques et le générateur corrigé sont livrés.
>
> J'aurais pu livrer 0,918. Personne ne l'aurait vérifié. Ce n'est pas l'échec du modèle, c'est la réussite de l'audit.

---

## 18 — Validation externe · 1:00

> Dernière épreuve : confronter le modèle retenu à une base qu'il n'a jamais vue — 100 800 lignes simulées en continu, sans aucun réentraînement.
>
> Sur 3 479 fenêtres évaluées, l'aire sous la courbe tombe à 0,753, et le modèle détecte 62 % des instabilités.
>
> Je présente ce résultat pour ce qu'il est : **une épreuve de transférabilité, pas une validation externe au sens strict.** La base est simulée. La vraie validation viendra de nouvelles campagnes d'essais.

**Chiffres** : 100 800 lignes · 3 479 fenêtres · AUC 0,753 · 62 %

---

## 19 — HMI Supervision · 0:30 puis DÉMONSTRATION LIVE · 5:00

**Ce que tu dis avant de basculer**

> Tout ce que je viens de décrire vit dans une application déployée : sept pages, une persistance en trois couches, bilingue, authentifiée, et conforme au niveau AA du référentiel d'accessibilité. Je vous la montre en direct.

**→ Bascule sur le navigateur. L'application doit déjà être ouverte et réveillée.**

### Déroulé de la démonstration — 5 minutes, quatre temps

**Temps 1 — Supervision (1 min 15)**
Montre l'état machine, le score de stabilité, la probabilité issue du modèle, et les alertes de l'agent.
> « Voici l'écran qu'un opérateur a sous les yeux. Le bandeau du haut rejoue un essai enregistré ; ce bloc-ci évalue la configuration courante. Les deux sont étiquetés sur leur source — c'est une correction que j'ai apportée après une démonstration où la différence prêtait à confusion. »

**Temps 2 — Profil de vis (1 min 15)**
Va sur la page Profil, modifie un élément de la vis.
> « Je change la configuration de la vis ici. Le taux de remplissage, le temps de séjour et les volumes se recalculent — c'est Network 7 qui tourne. »

**Temps 3 — Provoquer un défaut (1 min 30)** ← *le moment qui convainc*
Reprends le cas C3 : dégrade la zone 5.
> « Je provoque volontairement un défaut en zone 5. Le score chute de 65 à 46, la probabilité de stabilité tombe à 0,30, et l'agent lève une alerte rouge. Surtout, il me dit quel paramètre corriger, dans quel sens, et de combien. »

**Temps 4 — Corriger et refermer (1 min)**
Applique la recommandation.
> « J'applique la recommandation : le score remonte de 32 points, l'alerte se lève. Sensibilité, détectabilité, réversibilité — les trois propriétés qu'on attend d'un jumeau numérique. »

**→ Retour au support.**

### Règles de survie de la démo

- **Ne jamais improviser un clic.** Suis ces quatre temps, rien d'autre.
- **Si l'application rame** : continue de parler par-dessus. Le silence dure plus longtemps que le chargement.
- **Si l'application plante** : bascule immédiatement sur les captures des diapositives 19-20-21 et dis simplement *« je vous montre le même parcours en images »*. Ne t'excuse pas, ne débogue pas devant le jury.
- **Ne montre pas** la page Settings ni la page Compte — sans intérêt pour le jury et coûteuses en temps.

---

## 20 — Profil de vis & Moteur Procédé · 0:30

> Vous venez de voir ces deux pages en action. La page Moteur Procédé est en lecture seule : elle expose le calcul complet, le couple par nœud et l'agrégation par zone, sans permettre de le modifier. La séparation entre ce qu'on édite et ce qu'on consulte est volontaire.

*Diapositive rapide : la démo a déjà fait le travail.*

---

## 21 — Cinq cas · 1:15

> J'ai formalisé cinq cas de démonstration qui structurent la recette de l'outil.
>
> Le cas 1 pose une référence LFP à 65 sur 100. Le cas 2 optimise la configuration et monte à 82 : **l'outil est sensible** à une amélioration réelle.
>
> Le cas 3 provoque un défaut en zone 5 : chute à 46, alerte rouge, probabilité à 0,30 — **il est détectable**.
>
> Le cas 4 est la recommandation de l'agent. Le cas 5 applique la correction : plus 32 points, alerte levée — **il est réversible**.
>
> Sensibilité, détectabilité, réversibilité. Un outil qui affiche toujours « tout va bien » ne sert à rien ; celui-ci réagit dans les deux sens.

**Chiffres** : 65 → 82 → 46 → +32

---

## 22 — Piloté par validation · 0:45

> Le projet a été conduit en Kanban avec une limite d'un sujet en cours à la fois : proposition, validation de l'encadrant, développement, tests, démonstration.
>
> Janvier, le cadrage. Mars, les données. Avril, la campagne d'essais. Mai, l'application. Juin, la démonstration client, tenue au 16 juin.
>
> Le fait d'être seul développeur imposait cette discipline : aucune fonctionnalité n'était lancée sans que l'encadrant industriel ait validé le besoin.

---

## 23 — Veille structurée · 0:35

> Quatre types de veille : technologique sur les revues scientifiques — 38 références dans le mémoire ; concurrentielle sur Coperion et Thermo Fisher ; sectorielle sur les cabinets d'études ; et réglementaire, en particulier le dossier PFAS de l'ECHA, qui justifie l'intérêt de la voie sèche.

---

## 24 — Budget · 0:20

> Le budget tient en une ligne : zéro euro de licence. Tout est open source, l'hébergement et la persistance sont en palier gratuit, et les données d'essais sont une ressource Rondol. La ressource centrale du projet, c'est le temps-homme — quatre mois.

---

## 25 — Indicateurs & qualité logicielle · 0:45

> Sur les indicateurs que je m'étais fixés : **725 tests automatisés, tous passants**, répartis sur 76 fichiers. Sept pages livrées sur sept. Contraste d'accessibilité à 6,38 pour 1, au-dessus du seuil AA. Démonstration client tenue au 16 juin.
>
> Un indicateur n'est pas atteint : le F1-macro visé était 0,85, je suis à 0,809. Je l'assume — c'est la valeur vraie après correction de la fuite. Le prochain gain viendra de nouvelles campagnes d'essais, pas d'un modèle plus sophistiqué.

**Chiffres** : 725 tests / 76 fichiers · 7 pages · 6,38:1 · 0,809 vs cible 0,85

---

## 26 — Conclusion · 1:15

> Pour répondre à ma problématique : **oui, le procédé devient lisible, comparable et prédictible. Mais pas autonome.**
>
> Ce qui est acquis : un jumeau numérique cohérent, un agent explicable, une interface démontrable, et un modèle validé sous un protocole strict.
>
> Ce que j'assume : une physique nominale, huit essais, et trois équations différées. Le cadre est explicite, et l'interface le dit à l'utilisateur.
>
> Ce que j'ai appris, et qui dépasse ce projet : **la rigueur du protocole vaut davantage qu'un score flatteur.** J'ai passé plus de temps à invalider mon meilleur résultat qu'à l'obtenir, et c'est ce travail-là qui rend l'outil défendable devant un client.
>
> La suite, ce sont de nouvelles campagnes d'essais pour calibrer la physique et élargir la base d'apprentissage.

*Marque un silence de deux secondes avant de passer à la dernière diapositive.*

---

## 27 — Merci · 0:15

> Je vous remercie. L'application est en ligne, le code et le mémoire sont dans les livrables. Je suis à votre disposition pour vos questions.

*Reste debout, tourné vers le jury. Ne range rien.*

---

## Si tu es en retard — l'ordre des coupes

Coupe dans cet ordre, jamais autre chose :

1. Diapositive 6 (SWOT) — dis une phrase, enchaîne
2. Diapositive 24 (Budget) — « zéro euro de licence, la ressource c'est le temps-homme »
3. Diapositive 23 (Veille) — cite deux types sur quatre
4. Diapositive 5 (Concurrence) — « deux directs, un indirect, notre différence c'est le jumeau numérique »
5. Diapositive 20 (Profil/Moteur) — déjà couverte par la démo

**Ne coupe jamais** : 7 (problématique), 13 (LOGO), 15 (la fuite), 16 (le vrai résultat), 26 (conclusion), ni la démo.
