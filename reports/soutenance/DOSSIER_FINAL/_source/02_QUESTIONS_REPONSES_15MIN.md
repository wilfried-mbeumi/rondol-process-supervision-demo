# Bloc 2 — Questions / réponses (15 minutes)

**Format** : le jury t'interroge librement. Environ 8 à 12 questions.

---

## Méthode de réponse — les quatre temps

Sous stress, on répond trop vite et trop long. Applique cette structure :

1. **Accuse réception** — « Oui, c'est la limite principale du travail. »
2. **Réponds en une phrase** — la réponse courte, d'abord.
3. **Étaye avec un chiffre ou une décision** — un seul, le plus parlant.
4. **Arrête-toi.** Si le jury veut plus, il relance.

**Quatre règles absolues**

- Si tu ne sais pas : **« Je ne l'ai pas mesuré. Voici comment je m'y prendrais. »** Jamais d'invention. Un jury sanctionne bien plus une réponse bricolée qu'un « je ne sais pas » assumé.
- Ne réponds jamais plus de 60 secondes sur une question.
- Ne dis jamais « en fait » ni « comme je l'ai dit » — ça sonne défensif.
- Une question hostile n'est pas une attaque : c'est un test de solidité. Reste posé.

---

## Qui te pose quoi

| Membre du jury | Ce qu'il va creuser |
|---|---|
| **Professionnel du domaine, externe** | L'usage réel, l'adoption, la responsabilité, le coût, la valeur pour Rondol |
| **Intervenant formation, non connu** | Le protocole, la fuite, la validation, les choix d'algorithmes, la reproductibilité |

---

# A. Protocole et données

### A1. « Huit essais, ce n'est pas statistiquement significatif. Comment pouvez-vous conclure quoi que ce soit ? »

> C'est la limite principale du travail, et je ne la contourne pas. Huit essais interdisent toute prétention à la généralisation.
>
> C'est précisément pour ça que j'ai choisi le Leave-One-Group-Out plutôt qu'une partition aléatoire : c'est le protocole le plus sévère disponible à ce volume. Il m'a coûté 15 points de F1-macro — 0,92 en aléatoire contre 0,79 en séparation par essai — mais le second chiffre est le seul honnête.
>
> Ce que je revendique, ce n'est pas un modèle généralisable : c'est une **chaîne complète, mesurée sous protocole strict, prête à être réentraînée** dès que Rondol produira de nouvelles campagnes.

### A2. « Comment avez-vous découvert la fuite ? »

*Question de vérification : si ta réponse est vague, on doutera que tu l'aies vraiment trouvée. Sois précis.*

> Le résultat était trop beau. Passer de 0,809 à 0,918 avec 800 échantillons synthétiques, c'est un gain de plus de dix points, alors que l'augmentation de données donne typiquement quelques points sur ce type de problème.
>
> J'ai remonté le code de génération. Le pool synthétique était construit **une fois**, en amont de la boucle de validation, à partir des huit essais réels. Or le tirage s'appuie sur des points d'ancrage issus des données et sur les écarts-types par classe. Ces deux quantités portaient l'information de l'essai que la boucle excluait ensuite.
>
> Autrement dit, l'essai de test alimentait indirectement l'entraînement. J'ai déplacé la génération **à l'intérieur de chaque pli**, avec les seuls essais d'entraînement. Le gain a disparu : delta réel de moins un millième.

### A3. « Votre écart-type est de ± 0,126 pour un F1 de 0,809. Votre modèle n'est-il pas simplement du bruit ? »

> L'écart-type est effectivement large, et il traduit une réalité : les huit essais ne se ressemblent pas. Certains plis sont faciles, d'autres beaucoup moins.
>
> Ce que je peux affirmer : le modèle est **systématiquement au-dessus du hasard** sur tous les plis, et il conserve 0,753 d'aire sous la courbe sur une base externe qu'il n'a jamais vue.
>
> Ce que je ne peux pas affirmer : que 0,809 soit une performance stable en production. C'est une estimation avec une incertitude large, et c'est exactement pour ça que je refuse de la présenter comme une garantie.

### A4. « Pourquoi une fenêtre de 60 secondes ? »

> J'ai testé trois largeurs — 30, 60 et 120 secondes — sous le même protocole.
>
> 30 secondes capture mal les dérives lentes de température. 120 secondes lisse trop et réduit le nombre de fenêtres exploitables, ce qui est problématique avec huit essais. 60 secondes est le meilleur compromis mesuré, et c'est aussi l'ordre de grandeur du temps de séjour dans la vis, donc il a un sens physique.

### A5. « 87 variables pour 627 fenêtres — n'est-ce pas du surapprentissage garanti ? »

> Le rapport est effectivement défavorable, et c'est un vrai risque que j'ai traité de deux façons.
>
> D'abord, les 87 variables ne sont pas arbitraires : ce sont des descripteurs statistiques — position, dispersion, tendance, dynamique — calculés systématiquement sur chaque voie de capteur. Il n'y a pas eu de sélection opportuniste à partir des performances de test, ce qui aurait été une autre forme de fuite.
>
> Ensuite, la forêt aléatoire échantillonne les variables à chaque nœud, ce qui la rend nettement plus tolérante que des modèles linéaires à ce régime.
>
> Cela dit, avec plus de données, une réduction de dimension serait le premier chantier.

### A6. « Vos données sont-elles concernées par le RGPD ? »

> Non. Ce sont des mesures physiques de procédé — températures, vitesses, débits. Aucune donnée à caractère personnel.
>
> En revanche, l'application intègre une authentification, et là il y a des identifiants. Les mots de passe sont hachés en PBKDF2-HMAC avec sel, jamais stockés en clair. La veille réglementaire du mémoire couvre ce point.

---

# B. Le modèle

### B1. ⚠️ « Dans votre tableau corrigé, le SVM fait 0,824 et la forêt aléatoire 0,809. Pourquoi avoir retenu la moins bonne ? »

*C'est la question la plus dangereuse du dossier, parce que le chiffre est dans ton mémoire et qu'un jury attentif le verra. Prépare-la mot pour mot.*

> Vous avez raison sur le chiffre, et c'est une lecture attentive du tableau.
>
> Trois éléments. D'abord, la sélection du modèle s'est faite sur le protocole **sans augmentation** — celui que je retiens comme référence — où la forêt donne 0,809 contre 0,805 pour le SVM, avec 0,950 d'exactitude et 0,976 d'aire sous la courbe.
>
> Ensuite, l'écart de 0,015 en faveur du SVM après correction est **très inférieur à l'écart-type de ± 0,126**. Statistiquement, ces deux modèles sont indiscernables — c'est d'ailleurs la conclusion de toute la section : les cinq modèles tiennent entre 0,78 et 0,82.
>
> Enfin, la forêt apporte l'importance des variables, ce qui compte pour un outil dont l'exigence est l'explicabilité.
>
> Cela dit, si Rondol produisait de nouvelles campagnes et que l'écart se confirmait, il n'y aurait aucune raison de garder la forêt. C'est pour ça que le SVM reste intégré dans l'application comme challenger documenté, et pas seulement cité dans un rapport.

### B2. « Pourquoi pas un réseau de neurones profond ? »

> Avec huit essais, un réseau profond aurait mémorisé les essais plutôt qu'appris le phénomène. Je l'ai vérifié : le perceptron multicouche que j'ai testé est le moins bon des cinq à 0,781.
>
> Il y a aussi une raison d'usage : l'outil doit expliquer ses alertes à un ingénieur procédé. Une forêt donne l'importance des variables ; un réseau profond aurait exigé une couche d'explication supplémentaire pour un gain nul.

### B3. « Comment gérez-vous la dérive du modèle dans le temps ? »

> Aujourd'hui, je ne la gère pas — et c'est une limite que je dois énoncer clairement.
>
> Ce que j'ai mis en place, c'est ce qui la rend gérable : le pipeline est reproductible de bout en bout, les seuils sont calibrés dans un fichier versionné, et l'évaluation sur base externe fournit un point de comparaison.
>
> Le dispositif manquant, c'est une surveillance en production : suivre la distribution des variables d'entrée et déclencher un réentraînement quand elle s'éloigne. Ça suppose que l'outil tourne en continu chez Rondol, ce qui n'est pas encore le cas.

### B4. « Votre validation externe est sur des données simulées. Est-ce vraiment une validation ? »

> Non, et je l'ai écrit comme tel dans le mémoire.
>
> C'est une épreuve de transférabilité : elle mesure la sensibilité du modèle à un changement de distribution, sur 3 479 fenêtres issues d'une base de 100 800 lignes générée avec une graine fixe. L'aire sous la courbe passe de 0,976 à 0,753 — cette chute est l'information utile.
>
> Une vraie validation externe demanderait des campagnes réelles indépendantes. C'est la première chose que je demanderais si le projet continuait.

---

# C. Ingénierie et produit

### C1. « Pourquoi 725 tests pour un prototype ? N'est-ce pas disproportionné ? »

> Ils ne viennent pas d'une exigence de couverture, mais de l'usage. Chaque incident rencontré en démonstration est devenu un test de non-régression.
>
> Quand on présente un outil à un client, un défaut qui réapparaît coûte plus cher qu'une fonctionnalité absente.
>
> Et il y a une raison scientifique : si le logiciel n'est pas reproductible, les résultats qu'il produit ne le sont pas non plus. Les tests garantissent notamment qu'un chiffre affiché sur une page est le même que sur une autre — c'est ce qui rend le mémoire vérifiable.

### C2. « Pourquoi Streamlit et pas une vraie stack web ? »

> Parce que la contrainte du projet, c'était de livrer un outil démontrable en quatre mois, seul, à un public d'ingénieurs procédé — pas de construire un produit industriel.
>
> Streamlit m'a permis de concentrer l'effort sur le moteur, l'agent et le protocole de validation, c'est-à-dire sur ce qui fait la valeur.
>
> Sa limite, je la connais : le modèle de réexécution complète à chaque interaction impose une architecture de persistance en trois couches pour éviter que l'état ne se perde. C'est la partie la plus délicate du développement. Pour un passage en production multi-utilisateur, une API et un front séparés seraient le bon choix.

### C3. « Comment savez-vous que votre outil sert vraiment à Rondol ? »

> Je ne peux pas revendiquer une adoption en production : le projet s'est arrêté à la démonstration du 16 juin.
>
> Ce que je peux dire, c'est que l'outil a été conçu par validations successives avec Maël Gallas — l'équation thermique qu'il contient est celle qu'il a imposée, pas un modèle que j'aurais choisi. La calibration des doseurs en grammes par heure et par tour vient également de ses exigences.
>
> La mesure d'adoption honnête n'existe pas encore. Elle viendrait d'un usage sur plusieurs campagnes.

### C4. « Si votre outil se trompe et qu'un lot est perdu, qui est responsable ? »

*Question de professionnel. C'est un test de posture, pas de technique.*

> L'opérateur, et c'est un choix de conception, pas une échappatoire.
>
> L'outil n'exécute rien : il n'a aucune commande sur la machine. Il affiche un score, une probabilité et une recommandation explicite — quel paramètre, dans quel sens, de combien. La décision reste humaine.
>
> C'est aussi pour ça que je refuse d'afficher des valeurs non calibrées : un opérateur qui croit lire une température mesurée alors qu'elle est nominale prendrait une décision fondée sur une illusion. Trois équations sont différées pour cette raison précise, et l'interface affiche « À venir » plutôt qu'un nombre.

---

# D. Projet et posture

### D1. « Comment avez-vous géré la relation avec votre encadrant industriel ? »

> En Kanban, avec une limite d'un sujet à la fois. Aucune fonctionnalité n'était développée sans que Maël Gallas ait validé le besoin en amont.
>
> Concrètement, ça m'a évité de construire des choses inutiles. Un exemple : j'avais développé un module de test de refroidissement qui me semblait pertinent ; il m'a expliqué que ça ne correspondait à aucune réalité du procédé. Je l'ai retiré.
>
> Le point difficile, c'était d'arbitrer entre ses demandes procédé et les exigences du référentiel. Quand les deux divergeaient, je traitais d'abord le besoin industriel et je documentais l'écart dans le mémoire.

### D2. « Que feriez-vous différemment si vous recommenciez ? »

*Ne réponds pas « rien ». C'est le pire signal possible.*

> Trois choses.
>
> D'abord, j'auditerais le protocole de validation **avant** de produire les résultats, pas après. J'ai trouvé la fuite par ancrage tard ; la chercher dès la conception m'aurait fait gagner plusieurs semaines.
>
> Ensuite, je négocierais le volume d'essais en amont. Huit essais, c'était subi, pas choisi — j'aurais dû poser cette contrainte comme un prérequis dès janvier.
>
> Enfin, j'introduirais l'authentification et la persistance durable dès le début plutôt qu'en fin de projet. Les avoir ajoutées tard a créé des bugs d'état qui m'ont coûté du temps.

### D3. « Vous étiez seul. Comment le prouvez-vous, et comment travailleriez-vous en équipe ? »

> Le dépôt Git porte l'historique complet : chaque décision technique est tracée dans un commit avec sa justification.
>
> Travailler seul m'a imposé une discipline que je garderais en équipe : l'architecture en couches, avec des modules purs sans dépendance à l'interface, existe précisément pour que plusieurs personnes puissent travailler sans se marcher dessus. Les 725 tests jouent le même rôle qu'une revue de code quand on n'a personne pour la faire.
>
> Ce qui me manque et que je sais : je n'ai jamais eu à arbitrer un désaccord technique entre deux développeurs.

---

# E. Les trois questions qui font mal

### E1. « Au fond, votre modèle ne vaut pas mieux qu'un opérateur expérimenté. »

> Sur un procédé qu'il connaît, probablement pas — et je ne prétends pas le remplacer.
>
> Ce que l'outil apporte, c'est autre chose : la **comparabilité**. Un opérateur expérimenté sait qu'une configuration marche mieux qu'une autre ; il ne peut pas dire de combien, ni pourquoi, ni transmettre ce savoir à un collègue.
>
> Ici, deux configurations se comparent sur des volumes, des temps de séjour et un score. Et quand l'opérateur part à la retraite, la connaissance reste dans l'outil.

### E2. « Vous n'avez pas atteint votre objectif de 0,85. C'est un échec. »

> L'indicateur n'est pas atteint, c'est écrit dans le mémoire.
>
> Mais regardons ce qui se serait passé si je m'étais arrêté au chiffre précédent : j'avais 0,918, donc au-dessus de la cible. J'aurais pu clôturer le projet en annonçant l'objectif dépassé.
>
> J'ai audité, trouvé la fuite, et publié 0,809. Le projet a perdu son indicateur au vert et gagné une conclusion vraie. Si le critère est la conformité à un objectif fixé en janvier, c'est un échec. Si le critère est la fiabilité de ce que je livre à Rondol, non.

### E3. « Votre physique n'est pas calibrée, votre modèle repose sur huit essais. Qu'est-ce qui est solide, exactement ? »

> Trois choses le sont, et je les distingue nettement du reste.
>
> **La géométrie** : les 81 positions, les volumes et les temps de séjour sortent de la géométrie réelle Rondol et du calcul métier validé par l'entreprise. Ce ne sont pas des estimations.
>
> **Le protocole** : la mesure de performance est faite sous Leave-One-Group-Out, avec une fuite identifiée et corrigée. Le chiffre est incertain mais sa méthode d'obtention est solide.
>
> **La chaîne** : 725 tests garantissent que le système est reproductible et cohérent d'une page à l'autre.
>
> Ce qui n'est pas solide : les valeurs absolues de température et de couple, qui sont nominales — et c'est pour ça que l'interface le signale à l'utilisateur au lieu de les présenter comme des mesures.

---

## Ta phrase de repli universelle

Si une question te prend totalement au dépourvu :

> « C'est un point que je n'ai pas traité. Ce que je peux vous dire, c'est comment je m'y prendrais : [une phrase]. Et voici la limite que ça poserait : [une phrase]. »

Un jury retient qu'un candidat sait où s'arrête son travail. C'est une force, pas un aveu.
