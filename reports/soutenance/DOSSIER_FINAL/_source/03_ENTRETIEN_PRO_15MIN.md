# Bloc 3 — Entretien professionnel (15 minutes)

**Ce qui est évalué ici n'est pas ton projet, c'est toi.** Ta posture, ta lucidité sur ton parcours, ta capacité à te projeter comme professionnel de la data et de l'IA.

> ⚠️ Les passages notés **[À TOI]** doivent être remplis avec tes éléments personnels.
> Je ne connais pas ton parcours avant ce projet — ne récite pas une réponse générique,
> le jury le sent immédiatement.

---

## La règle : répondre en STAR

Pour toute question comportementale (« racontez-moi une fois où… »), structure :

- **S**ituation — le contexte en une phrase
- **T**âche — ce dont tu étais responsable
- **A**ction — ce que **tu** as fait (dis « j'ai », pas « on a »)
- **R**ésultat — l'issue, avec un chiffre si possible

90 secondes maximum. Au-delà, on décroche.

---

## Ton stock d'histoires — trois situations à connaître par cœur

Tu peux répondre à presque toutes les questions comportementales avec ces trois-là. Apprends-les, pas comme un texte, mais comme des souvenirs structurés.

### Histoire 1 — « J'ai invalidé mon propre meilleur résultat »

> **S** — En juillet, mon modèle augmenté atteignait 0,918 de F1-macro contre 0,809 sans augmentation. Plus de dix points de gain : de quoi conclure le projet sur un succès.
> **T** — J'étais seul responsable de la validité de ce chiffre. Personne dans l'entreprise n'avait les moyens de le vérifier.
> **A** — Le gain m'a paru trop élevé pour ce type de méthode. J'ai remonté le code de génération et découvert que le pool synthétique était construit une fois sur les huit essais, y compris celui servant de test. J'ai déplacé la génération dans chaque pli de validation, puis tout réexécuté.
> **R** — Le gain a disparu : 0,809, delta réel de moins un millième. J'ai publié les deux chiffres dans le mémoire et conservé l'ancien fichier marqué comme périmé, avec la raison de son invalidation.

**Ce que ça dit de toi** : intégrité, capacité d'audit, courage de contredire son propre travail.
**Questions où l'utiliser** : points forts · difficulté rencontrée · fierté · éthique · rigueur · erreur.

### Histoire 2 — « J'ai supprimé une fonctionnalité que j'avais construite »

> **S** — J'avais développé un module de test de refroidissement qui me semblait pertinent d'un point de vue logiciel.
> **T** — Le valider auprès de Maël Gallas avant de l'intégrer à la démonstration.
> **A** — Il m'a expliqué que cette fonction ne correspondait à aucune réalité du procédé : ce n'est pas ainsi qu'on manipule le refroidissement sur une extrudeuse. J'ai retiré le module et remplacé la logique par un diagnostic automatique sur la zone la plus chaude, qui correspond, lui, à un geste métier réel.
> **R** — La fonctionnalité livrée est utilisée dans le parcours de démonstration. Celle que j'avais imaginée aurait été ignorée.

**Ce que ça dit de toi** : écoute du métier, absence d'ego technique, capacité à jeter son propre travail.
**Questions où l'utiliser** : désaccord avec un manager · retour difficile · travail en équipe · relation client.

### Histoire 3 — « J'ai tenu un jalon client en arbitrant le périmètre »

> **S** — Une démonstration client était fixée au 16 juin, date non négociable, et plusieurs fonctionnalités n'étaient pas prêtes.
> **T** — Livrer un outil démontrable de bout en bout à cette date.
> **A** — J'ai travaillé en Kanban avec un seul sujet en cours à la fois, priorisé par la valeur de démonstration, et différé explicitement trois équations de physique plutôt que de livrer des valeurs non calibrées. L'interface affiche « À venir » à ces endroits.
> **R** — La démonstration a eu lieu à la date prévue, avec un parcours complet en cinq cas. Les équations différées sont documentées comme telles dans le mémoire.

**Ce que ça dit de toi** : gestion de priorités, tenue d'un engagement, arbitrage assumé.
**Questions où l'utiliser** : gestion du temps · pression · priorisation · dire non.

---

# Les questions et comment y répondre

## 1. « Présentez-vous en deux minutes. »

*La question la plus prévisible, et celle que l'on rate le plus. Écris-la, apprends-la, chronomètre-la.*

**Structure** : d'où tu viens (20 s) → ce qui t'a amené à la data (30 s) → ce que tu viens de faire (40 s) → où tu vas (30 s).

> **[À TOI]** — formation initiale, parcours avant le Mastère, ce qui t'a orienté vers la data et l'IA.
>
> Puis : « Cette année, j'ai conduit seul, chez Rondol Industrie, la conception et le déploiement d'une plateforme prédictive d'aide à la décision pour l'extrusion bivis de composants de batteries tout-solide. J'ai couvert toute la chaîne : la collecte sur une campagne d'essais réelle, la modélisation, l'application déployée, et la validation méthodologique.
>
> Ce que j'en retiens, c'est un positionnement : je veux travailler à l'endroit où la donnée rencontre un procédé physique réel — l'industrie, pas le marketing. »

**Ne dis pas** : ton âge, ta situation familiale, « je suis passionné par l'IA » (tout le monde le dit).

## 2. « Pourquoi la data et l'IA ? »

*Le piège est de répondre « parce que c'est l'avenir ». Ancre sur une expérience concrète.*

> **[À TOI]** — l'élément déclencheur réel.
>
> Complète avec ce que ce projet a confirmé : « Ce projet a précisé quelque chose. Ce qui m'intéresse, ce n'est pas l'algorithme — les cinq modèles que j'ai comparés se tiennent tous entre 0,78 et 0,82. C'est le protocole : savoir si un chiffre veut dire quelque chose. Le travail qui m'a le plus appris cette année, c'est celui qui a détruit mon meilleur résultat. »

## 3. « Quels sont vos points forts ? »

*Trois maximum, chacun adossé à une preuve.*

> **La rigueur méthodologique.** → Histoire 1.
> **L'autonomie de bout en bout.** J'ai couvert seul la collecte, la modélisation, le développement et le déploiement. 725 tests automatisés, une application en ligne, un mémoire de 79 pages.
> **La capacité à traduire.** Je travaille avec des ingénieurs procédé qui ne font pas de data, et je dois leur rendre un modèle compréhensible. C'est pour ça que l'agent a onze règles explicites en plus du modèle : le modèle donne le quoi, les règles donnent le pourquoi.

## 4. « Vos points faibles ? »

*Ne joue pas au malin avec un faux défaut (« je suis perfectionniste »). Donne un vrai, et surtout ce que tu en fais.*

> **Je vais trop loin seul avant de solliciter un avis.** Le module de refroidissement, je l'ai construit entièrement avant de le montrer — et il est parti à la poubelle. La correction que j'ai mise en place, c'est le Kanban avec un seul sujet en cours et une validation de l'encadrant avant développement. Ça a limité la casse sur la suite du projet, mais c'est une discipline que je dois m'imposer, pas un réflexe naturel.
>
> **Je n'ai jamais travaillé en équipe de développement.** J'ai structuré le code en couches et écrit des tests pour compenser, mais je n'ai jamais eu à arbitrer un désaccord technique entre deux personnes. C'est ce que je cherche dans mon prochain poste.

## 5. « Racontez-moi une difficulté que vous avez rencontrée. »

→ **Histoire 1** si l'accent est technique, **Histoire 2** si l'accent est relationnel.

## 6. « Comment avez-vous réagi quand votre encadrant a rejeté votre travail ? »

→ **Histoire 2**, puis ajoute :

> Sur le moment, c'est désagréable — j'avais passé du temps dessus. Mais il avait raison, et il avait une information que je n'avais pas : la réalité du geste métier. Mon rôle n'est pas d'avoir raison sur le procédé, c'est de le modéliser correctement. Depuis, je fais valider le besoin avant de construire.

## 7. « Où vous voyez-vous dans trois ans ? »

*Sois concret et cohérent avec ton projet. Une réponse floue coûte cher.*

> **[À TOI]** — le type de poste et de structure que tu vises.
>
> Cadre suggéré, à adapter : « Chef de projet data en environnement industriel ou deeptech. Ce qui m'intéresse, c'est la position d'interface : comprendre assez le métier pour poser la bonne question, et assez la technique pour savoir si la réponse tient. Cette année m'a montré que c'est là que je suis utile — le moment où j'ai apporté le plus de valeur à Rondol, ce n'est pas quand j'ai entraîné le modèle, c'est quand j'ai dit que son résultat était faux. »

## 8. « Pourquoi devrions-nous vous recruter comme chef de projet data ? »

> Parce que j'ai déjà fait le travail en entier, seul, avec une contrainte de livraison réelle.
>
> J'ai cadré une problématique avec un industriel, mené une campagne de collecte, construit et validé un modèle, développé et déployé une application, et tenu un jalon client à date. Je sais aussi ce que je ne sais pas faire, et je le dis — c'est ce qui a fait la valeur de mon mémoire.
>
> Ce que j'apporte à une équipe, ce n'est pas seulement de savoir entraîner un modèle. C'est de savoir **si le chiffre qu'on présente au client est vrai**.

## 9. « Comment expliqueriez-vous votre projet à quelqu'un qui n'y connaît rien ? »

*Test fréquent. Prépare-la, elle doit sortir sans effort.*

> Une extrudeuse, c'est une grosse vis dans un tube chauffé qui mélange de la poudre pour fabriquer des composants de batterie. Quand ça se dérègle, on perd la matière — et cette matière coûte cher.
>
> J'ai construit un tableau de bord qui fait deux choses. Il calcule ce qui se passe à l'intérieur de la vis à partir de sa géométrie réelle. Et il apprend, sur des essais passés, à reconnaître les signes d'un procédé qui part en vrille — puis il dit à l'opérateur quoi corriger, dans quel sens, et de combien.
>
> Il ne décide pas à sa place. Il rend visible ce qui ne l'était pas.

## 10. « Comment vous tenez-vous à jour ? »

> Quatre canaux, et ils sont formalisés dans le mémoire. Les revues scientifiques pour l'état de l'art — 38 références sur l'extrusion et le tout-solide. Les acteurs du secteur, Coperion et Thermo Fisher, pour le positionnement. Les cabinets d'études pour le marché. Et la veille réglementaire, en particulier le dossier PFAS de l'ECHA, qui conditionne l'intérêt de la voie sèche.
>
> Côté technique, la documentation officielle des bibliothèques que j'utilise, et les dépôts eux-mêmes quand la documentation ne suffit pas.

## 11. « Quelles sont vos prétentions salariales ? »

*Ne réponds jamais par un chiffre isolé. Donne une fourchette et un fondement.*

> **[À TOI]** — renseigne-toi avant : un chef de projet data junior en région se situe généralement entre **X et Y** k€ bruts. Cite une fourchette, pas un point.
>
> Formulation : « Sur la base de ce qui se pratique pour un profil junior en gestion de projet data, je me situe entre X et Y. Mais ce qui compte le plus pour moi à ce stade, c'est la nature du sujet et l'encadrement — je cherche un environnement où je peux continuer à apprendre le métier en même temps que la technique. »

## 12. « Êtes-vous mobile ? Disponible quand ? »

> **[À TOI]** — réponds franchement. Une contrainte assumée passe toujours mieux qu'une disponibilité floue.

---

## Cinq réflexes pour ce bloc

1. **Dis « j'ai », pas « on a ».** Tu étais seul sur ce projet — l'assumer n'est pas de l'arrogance.
2. **Un chiffre par réponse, pas cinq.** Ce bloc évalue ta posture, pas ta mémoire.
3. **Ne dénigre jamais** Rondol, Nexa, ni un encadrant. Même une frustration réelle se formule comme une contrainte de projet.
4. **Accepte les silences.** Deux secondes de réflexion valent mieux qu'un « euh » de trois secondes.
5. **Prépare deux questions à poser au jury.** On te demandera presque certainement si tu en as. « Non » est une mauvaise réponse.
   - « Sur les projets data en environnement industriel que vous voyez passer, qu'est-ce qui fait le plus souvent échouer le passage du prototype à la production ? »
   - « Dans une équipe data, qu'est-ce qui distingue selon vous un bon chef de projet junior d'un bon ingénieur junior ? »
