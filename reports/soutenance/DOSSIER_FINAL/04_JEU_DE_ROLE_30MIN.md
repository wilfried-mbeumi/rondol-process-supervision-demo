# Bloc 4 — Jeu de rôle (30 minutes)

**Ce que le guide RNCP exige, mot pour mot :**

> simulation d'entretien avec un client (membre du jury) **qui fera évoluer la situation par un changement d'environnement** · conduite des entretiens avec **différents types d'interlocuteurs** · argumentation en tenant compte de la situation présentée et de ses interlocuteurs, **réponse aux objections et gestion des réclamations**

C'est le bloc le plus long de l'épreuve — aussi long que ta présentation. Ce n'est **pas** un examen technique : le jury joue un client, et il changera les règles en cours de route pour voir comment tu réagis.

**L'erreur qui coûte le plus cher : sur-promettre pour faire plaisir.** Un candidat qui dit « oui, c'est possible » à tout perd immédiatement sa crédibilité. Le jury cherche quelqu'un qui sait dire non en gardant le client.

---

# 1. Tes lignes rouges — à ne franchir sous aucune pression

Apprends-les. Quand la pression monte, c'est la seule chose qui te tiendra.

| Ne promets JAMAIS | Dis à la place |
|---|---|
| Des températures ou couples calibrés | « Ces valeurs sont nominales. Les calibrer demande une campagne d'étalonnage dédiée. » |
| Une performance garantie au-delà de 0,809 | « 0,809 de F1-macro avec un écart-type de ± 0,126, mesuré sur huit essais. Je ne peux pas garantir mieux sans nouvelles données. » |
| Un déploiement clé en main | « C'est un prototype démontrable. L'industrialisation est un projet distinct, à chiffrer. » |
| Une garantie de résultat procédé | « L'outil aide à décider. Il n'exécute rien et ne remplace pas l'opérateur. » |
| Du temps réel sur la machine | « Aujourd'hui, l'analyse se fait sur des fenêtres de 60 secondes, hors ligne. Le temps réel suppose une intégration automate. » |
| Une date sans avoir chiffré | « Je ne vous donne pas une date maintenant. Je vous la donne après avoir vu vos données. » |

**La formule qui te sauve, à connaître par cœur :**

> « Je peux vous le dire honnêtement : **ça, je sais le faire. Ça, je ne sais pas encore. Et voilà ce qu'il faudrait pour y arriver.** »

---

# 2. Les quatre interlocuteurs, et ce qu'ils veulent vraiment

Le jury changera de casquette. Reconnaître le profil en une phrase te fait gagner l'échange.

| Profil | Sa vraie question | Ton angle | Ne lui parle jamais de |
|---|---|---|---|
| **Directeur R&D / technique** | « Est-ce que c'est scientifiquement solide ? » | Protocole, LOGO, la fuite corrigée, les limites assumées | Prix, planning |
| **Acheteur / direction financière** | « Qu'est-ce que ça me rapporte ? » | Matière économisée, essais évités, zéro licence | Carreau-Yasuda, F1-macro |
| **Responsable production / opérateur** | « Est-ce que ça va me compliquer la vie ? » | L'outil ne décide pas, onze règles explicites, il garde la main | « L'IA optimise votre procédé » |
| **Dirigeant de PME** | « Quel est mon risque ? » | Progressivité, prototype, pas de dépendance, open source | Détails d'implémentation |

**Réflexe** : si tu ne sais pas à qui tu parles, demande. *« Pour vous répondre utilement — vous regardez ça sous l'angle technique ou sous l'angle industrialisation ? »* Poser la question est un signe de professionnalisme, pas de faiblesse.

---

# 3. La méthode — quatre temps, dans l'ordre

## Face à une objection

1. **Accuse réception, sans te défendre.** « C'est une bonne question. » / « Vous avez raison de le soulever. »
2. **Reformule pour vérifier.** « Si je comprends bien, votre inquiétude porte sur X. »
3. **Réponds avec une preuve, une seule.** Un chiffre, une décision, un fait.
4. **Vérifie que c'est traité.** « Est-ce que ça répond à votre point ? »

> ⚠️ Le temps 2 est celui qu'on saute sous stress, et c'est le plus important. Reformuler te donne trois secondes de réflexion et montre que tu écoutes.

## Face à une réclamation

L'ordre compte. Si tu inverses, tu passes pour quelqu'un qui se défend.

1. **Accuse réception de l'impact, pas du reproche.** « Vous avez perdu un lot, je comprends que ce soit un problème sérieux. »
2. **Ne te justifie pas tout de suite.** Aucun « oui mais » dans les vingt premières secondes.
3. **Établis les faits, ensemble.** « Est-ce qu'on peut regarder ce que l'outil affichait à ce moment-là ? »
4. **Assume ce qui relève de toi, délimite ce qui n'en relève pas.**
5. **Propose une action concrète et datée.**
6. **Reviens sur le fond.** Ce que ça change dans le produit.

---

# 4. Les six scénarios — entraîne-toi dessus

## SCÉNARIO 1 — Le client veut acheter (directeur R&D)

**Situation** : un fabricant de composants de batteries a vu la démonstration. Il est intéressé.

> **Client** : « C'est convaincant. Concrètement, si je vous l'achète, dans combien de temps c'est opérationnel chez moi, et ça me coûte combien ? »

**Le piège** : donner un délai et un prix. Tu n'as ni l'un ni l'autre, et tout chiffre lâché ici te suivra pendant les 25 minutes restantes.

> **Toi** : « Je vais être direct avec vous : je ne peux pas vous donner une date aujourd'hui, et si je vous en donnais une elle serait fausse.
>
> Ce que je peux vous dire précisément, c'est ce qui existe. L'outil tourne, il est déployé, il calcule la géométrie de vis, il détecte les instabilités et il explique ses alertes. Ça, c'est fait et démontrable.
>
> Ce qui n'existe pas encore pour **votre** cas : le modèle a été entraîné sur huit essais de Rondol, sur des formulations LFP. Chez vous, sur votre machine et vos matières, il faudra le réentraîner.
>
> Avant de parler délai, j'aurais besoin de savoir : quelles données d'essais avez-vous déjà, et sur quelles formulations ? »

**→ Tu as repris la main en posant une question.** C'est le bon réflexe : un consultant qui chiffre avant d'avoir qualifié se disqualifie.

### ⚡ Changement d'environnement probable

> **Client** : « Nous, on ne fait pas de LFP. On travaille sur électrolyte sulfure, et c'est sensible à l'humidité — tout se passe en boîte à gants. »

> **Toi** : « Ça change deux choses, et une seule est un vrai problème.
>
> Ce qui ne change pas : le moteur géométrique. Les 81 positions, les volumes, les temps de séjour sont de la géométrie de vis — ils sont indépendants de la matière. Ça reste valable.
>
> Ce qui change : le modèle prédictif a appris sur des signatures thermiques de formulations LFP. Sur un sulfure, il faut le réentraîner, et je ne peux pas vous dire aujourd'hui quelle performance il atteindra.
>
> Le vrai point d'attention, c'est la boîte à gants. Si vos capteurs sont différents ou moins nombreux, mes 87 variables ne se calculent pas de la même façon. Il faudrait qu'on regarde votre instrumentation avant toute chose.
>
> Ce que je vous proposerais : une phase de qualification sur vos données existantes, avant tout engagement. Si le signal n'y est pas, autant le savoir tout de suite. »

**Ce que tu démontres** : tu distingues ce qui transfère de ce qui ne transfère pas, et tu proposes une étape de dérisquage plutôt qu'un contrat.

---

## SCÉNARIO 2 — Le budget est divisé par deux (acheteur)

> **Client** : « La direction a coupé. J'ai la moitié du budget. Qu'est-ce que vous enlevez ? »

**Le piège** : accepter de tout faire pour moitié prix, ou refuser sèchement.

> **Toi** : « Je ne vais pas vous proposer la même chose moins cher — ce serait vous mentir sur la qualité que je peux tenir.
>
> Je vous propose plutôt de découper. Le projet a deux moitiés qui ont des valeurs très différentes.
>
> La première, c'est le moteur géométrique et l'agent à règles : la lecture de la vis, les volumes, les temps de séjour, les onze règles explicites. Elle ne demande **aucune donnée d'essai** — elle marche dès l'installation. C'est là que se trouve la valeur immédiate.
>
> La seconde, c'est le modèle prédictif. Elle exige une campagne d'essais, donc de la matière et du temps machine. C'est la partie coûteuse, et c'est aussi la moins certaine.
>
> Avec la moitié du budget, je fais la première proprement. Vous avez un outil qui rend vos configurations comparables, tout de suite. La partie prédictive, vous la déclenchez plus tard, quand vous aurez accumulé des essais — et à ce moment-là, ils vous auront coûté moins cher parce que l'outil vous aura évité d'en rater. »

**Ce que tu démontres** : tu sais découper une offre par la valeur, pas par le volume.

---

## SCÉNARIO 3 — L'incident (réclamation, responsable production)

> **Client, tendu** : « Votre outil affichait STABLE. On a perdu un lot complet. Vous vous rendez compte de ce que ça coûte ? »

**Le piège** : te justifier dans les cinq premières secondes. Ne le fais pas.

> **Toi** : « Un lot complet, c'est une perte importante, et je comprends que vous m'appeliez. Avant toute chose : est-ce que la ligne tourne à nouveau, ou vous êtes encore à l'arrêt ? »

*(→ tu traites l'urgence avant ta défense. C'est ce qui distingue un professionnel.)*

> « Ce que je vous propose : qu'on regarde ensemble ce que l'outil affichait au moment de l'incident. L'application garde l'historique des états validés, donc on peut reconstituer.
>
> Il y a trois cas possibles, et ils n'appellent pas la même réponse.
>
> **Premier cas** : l'outil affichait un score correct alors que le procédé dérivait. C'est un faux négatif. Mon modèle détecte 62 % des instabilités sur base externe — donc il en manque, structurellement, et c'est écrit dans la documentation. Si c'est ça, la question devient : est-ce que ce type de dérive était présent dans mes données d'entraînement ? Si non, c'est un cas à intégrer.
>
> **Deuxième cas** : une alerte a été levée mais elle n'a pas été vue, ou pas comprise. Alors c'est un problème d'interface ou de formation, et c'est de ma responsabilité aussi.
>
> **Troisième cas** : la cause est hors du périmètre — une matière hors spécification, un capteur défaillant. L'outil ne voit que ce que les capteurs lui donnent.
>
> Dans les trois cas, l'incident devient un cas de test. C'est comme ça que j'ai travaillé tout le projet : chaque défaut rencontré est devenu un test de non-régression, il y en a 725. »

### ⚡ Il pousse

> **Client** : « Donc vous me dites que c'est de ma faute ? »

> **Toi** : « Non, et je ne cherche pas un responsable — je cherche la cause, ce n'est pas pareil.
>
> Ce que je vous dis, c'est ce que l'outil ne fait pas, et que j'ai toujours dit : il n'exécute rien, il n'a aucune commande sur la machine, et il ne garantit pas la détection de toutes les instabilités. Il affiche une probabilité assortie d'une incertitude que je documente.
>
> Ce qui relève de moi : si l'outil a manqué un signal qu'il aurait dû voir, je dois le corriger et vous dire quand. Ce que je vous propose concrètement : je récupère les données de ce lot, je les passe dans le modèle, et je vous dis sous une semaine si c'est un cas rattrapable par réentraînement ou une limite de fond. Si c'est une limite de fond, je vous le dirai aussi. »

**Ce que tu démontres** : sang-froid, absence de fuite, distinction entre responsabilité et causalité, engagement daté.

---

## SCÉNARIO 4 — Le concurrent moins cher (acheteur / dirigeant)

> **Client** : « Coperion nous propose une supervision intégrée. Ils sont bien plus gros que vous. Pourquoi je prendrais votre solution ? »

**Le piège** : dénigrer Coperion. Tu perdrais immédiatement.

> **Toi** : « Coperion est un excellent constructeur, et sur une ligne de production leur offre est probablement plus adaptée que la mienne. Je ne vais pas vous dire le contraire.
>
> La question, c'est ce que vous cherchez. Si vous équipez une ligne de production continue, allez chez eux.
>
> Si votre besoin est en R&D — comparer des configurations de vis, comprendre pourquoi une formulation passe et pas une autre, sur des petites quantités de matière coûteuse — alors le sujet est différent. Leur supervision surveille une machine qui tourne. Ce que j'ai construit **explique** ce qui se passe dans la vis, position par position, à partir de sa géométrie réelle.
>
> Et il y a un point que je vous demande de vérifier chez eux : est-ce que leur système vous dit **pourquoi** il alerte, ou seulement qu'il alerte ? Chez moi, chaque alerte donne le paramètre, le sens et l'amplitude de la correction. Ce sont onze règles explicites, pas une boîte noire.
>
> En R&D, une alerte sans explication ne vous fait pas avancer. »

**Ce que tu démontres** : tu ne dénigres pas, tu segmentes le marché et tu ramènes sur ton différenciant réel.

---

## SCÉNARIO 5 — La montée en charge (DSI / directeur industriel)

> **Client** : « Si ça marche, on veut le déployer sur cinq lignes, avec vingt utilisateurs, connecté à nos automates. C'est faisable ? »

**Le piège** : dire oui. La réponse honnête est non — en l'état.

> **Toi** : « En l'état, non. Et je préfère vous le dire maintenant plutôt qu'au moment de la facture.
>
> Ce que j'ai construit est un prototype démontrable, mono-utilisateur, avec une interface qui réexécute son script à chaque interaction. C'était le bon choix pour livrer en quatre mois, seul. Ce n'est pas le bon choix pour vingt utilisateurs simultanés.
>
> Ce qui est réutilisable tel quel, et c'est l'essentiel : tout le cœur. Le moteur géométrique, les onze règles, le modèle, la validation — ce sont des modules purs, sans dépendance à l'interface. L'architecture en couches a été construite pour ça, et 725 tests garantissent qu'on peut les déplacer sans les casser.
>
> Ce qu'il faudrait ajouter : une interface de programmation entre le cœur et le front, une vraie base multi-utilisateur, et pour les automates un connecteur temps réel qui n'existe pas — aujourd'hui je travaille sur des fenêtres de 60 secondes, hors ligne.
>
> Ce sont des chantiers connus, pas des inconnues. Mais ce sont des chantiers, et il faut les chiffrer. »

**Ce que tu démontres** : tu dis non sans fermer la porte, et tu distingues le réutilisable du jetable.

---

## SCÉNARIO 6 — L'opérateur méfiant

> **Opérateur** : « Ça fait quinze ans que je fais tourner cette machine. Vous croyez qu'un ordinateur va m'apprendre mon métier ? »

**Le piège** : le défendre techniquement. Ce n'est pas une objection technique, c'est une inquiétude sur sa place.

> **Toi** : « Non, et l'outil n'est pas fait pour ça. Il n'a aucune commande sur la machine — il ne peut pas changer une consigne, il ne peut rien lancer. C'est vous qui décidez, toujours.
>
> Ce qu'il fait, c'est deux choses que vous ne pouvez pas faire, non pas parce que vous ne savez pas, mais parce que personne ne peut.
>
> La première : il regarde douze voies de capteurs en continu et calcule des tendances sur une minute glissante. Vous, vous regardez l'écran quand vous passez.
>
> La seconde, et c'est la plus utile : il rend vos réglages **comparables**. Vous savez qu'une configuration marche mieux qu'une autre. Vous ne pouvez pas dire de combien, ni le transmettre à quelqu'un qui débute. Là, ça devient un chiffre et une explication.
>
> Et si l'outil se trompe, il vous dit sur quoi il se fonde — quel paramètre, quelle zone. Vous pouvez le contredire. C'est même comme ça qu'on l'améliore : chez Rondol, une fonctionnalité que j'avais développée a été supprimée parce que l'ingénieur procédé m'a dit qu'elle ne correspondait à aucun geste réel. Il avait raison. »

**Ce que tu démontres** : écoute, humilité, et compréhension que l'adoption est un enjeu humain avant d'être technique.

---

# 5. Les phrases qui te sauvent

À placer quand tu es acculé :

> « Je préfère vous dire non maintenant plutôt que de vous décevoir dans six mois. »

> « Ce que je sais faire, ce que je ne sais pas encore, et ce qu'il faudrait pour y arriver — je vous dis les trois. »

> « Avant de vous répondre, est-ce que je peux vous poser une question sur votre contexte ? »

> « Vous avez raison de le soulever, c'est la limite principale du travail. »

> « Je ne l'ai pas mesuré. Voici comment je m'y prendrais pour le savoir. »

---

# 6. Les cinq fautes qui coûtent le plus

| Faute | Pourquoi c'est grave | Le réflexe correct |
|---|---|---|
| Dire oui à tout | Le jury teste précisément ça | Découpe : ce qui est fait / à faire / hors périmètre |
| Se justifier avant d'écouter | Tu passes pour défensif | Accuse réception, reformule, **puis** réponds |
| Dénigrer un concurrent | Signal d'amateurisme | Segmente le marché, ramène sur ton différenciant |
| Noyer sous la technique | Tu perds un acheteur en dix secondes | Une seule preuve, adaptée au profil |
| Donner un prix ou une date sans qualifier | Le chiffre te poursuit toute la séance | « J'ai besoin de voir vos données avant de vous répondre » |

---

# 7. S'entraîner avant le 25

Un fichier ne remplace pas la répétition — ce bloc évalue ta réaction à l'imprévu, et l'imprévu ne se lit pas.

**Entraîne-toi avec moi.** Dis simplement *« scénario 3 »* ou *« joue un acheteur qui trouve ça trop cher »*, et je tiens le rôle : je pousse, je change l'environnement en cours de route, et je te dis ensuite où tu as cédé trop vite, sur-promis, ou lâché un chiffre trop tôt.

Les trois premiers scénarios à travailler, par ordre de risque :

1. **Scénario 3 (l'incident)** — le plus dur émotionnellement, et celui où l'ordre des étapes compte le plus
2. **Scénario 1 (le changement de matière)** — le cas le plus probable de « changement d'environnement »
3. **Scénario 5 (la montée en charge)** — celui où la tentation de dire oui est la plus forte
