# Dossier de soutenance — Wilfried Galtier MBEUMI

**Mastère 2 Data & Intelligence Artificielle — RNCP 37137 (niveau 7)**
Pré-soutenance : **25 août 2026** · Soutenance : **9 septembre 2026**
Sujet : plateforme prédictive d'aide à la décision — extrusion bivis SSB, Rondol Industrie

---

## L'épreuve fait 90 minutes, pas 30

C'est le point que ce dossier existe pour corriger. La présentation ne pèse qu'un tiers de l'épreuve.

| Bloc | Durée | Fichier | Ce qui est évalué |
|------|-------|---------|-------------------|
| 1. Présentation sans interruption | 30 min | `01_PRESENTATION_30MIN.md` | Maîtrise du sujet, points essentiels, respect du temps |
| 2. Questions / réponses | 15 min | `02_QUESTIONS_REPONSES_15MIN.md` | Solidité technique, honnêteté méthodologique |
| 3. Entretien professionnel | 15 min | `03_ENTRETIEN_PRO_15MIN.md` | Posture, parcours, projection professionnelle |
| 4. Jeu de rôle | 30 min | `04_JEU_DE_ROLE_30MIN.md` | Argumentation client, objections, réclamations |

**Le jeu de rôle est aussi long que la présentation.** C'est le bloc le moins intuitif et celui où l'on perd le plus de points sans s'en rendre compte.

### Le jury

- **1 professionnel du domaine d'activité, externe** — il connaît l'industrie, pas forcément l'IA. C'est probablement lui qui jouera le client au bloc 4.
- **1 intervenant de la formation, non connu de toi** — il connaît l'IA, pas Rondol. C'est lui qui creusera le protocole, la fuite, la validation.

Cette asymétrie est ton meilleur repère : **quand tu parles procédé, adresse-toi au professionnel ; quand tu parles modèle, adresse-toi au formateur.**

---

## Les autres fichiers

| Fichier | Quand l'utiliser |
|---------|------------------|
| `05_ANTISECHE_A4.md` | Le jour J. C'est la seule feuille que tu emportes. |
| `06_CHECKLIST_JOUR_J.md` | La veille et 30 min avant d'entrer. |

---

## Ton fil rouge, à savoir par cœur

> « J'ai conçu et déployé une plateforme qui rend un procédé d'extrusion bivis lisible, comparable et prédictible — sans jamais faire passer une valeur non calibrée pour une mesure. »

Si tu ne devais retenir qu'une phrase de tout ce dossier, c'est celle-là. Elle contient à la fois ce que tu as fait et la limite que tu assumes. Les deux comptent.

---

## Ton meilleur atout, et comment ne pas le gâcher

**Tu as trouvé une fuite de données dans ton propre résultat et tu l'as publiée.**

Le 0,918 était présentable. Personne ne l'aurait vérifié. Tu as régénéré le pool synthétique dans chaque pli, constaté que le gain disparaissait, et écrit les deux chiffres côte à côte dans le mémoire.

C'est rare, et c'est exactement ce qu'un référentiel de niveau 7 cherche à certifier. **Amène-le toi-même** au bloc 1 (slide 15) — n'attends pas qu'on te le demande. Un candidat qui expose sa propre erreur méthodologique prend le contrôle du récit ; un candidat à qui on l'extrait subit.

**Le piège** : présenter ça comme un échec. Ce n'est pas le modèle qui a échoué, c'est l'audit qui a réussi. Ton ton doit être celui de quelqu'un qui raconte une décision, pas une faute.

---

## Les trois questions qui vont revenir, quoi qu'il arrive

Elles sont traitées en détail dans `02_QUESTIONS_REPONSES_15MIN.md`, mais retiens la posture :

1. **« Seulement 8 essais ? »** → Oui. C'est pour ça que j'ai choisi LOGO plutôt qu'une partition aléatoire, et voilà les 15 points d'écart que ça révèle.
2. **« Vous n'atteignez pas votre cible de 0,85. »** → Non. 0,809 est la valeur vraie après correction de la fuite. Le 0,918 aurait atteint la cible et aurait été faux.
3. **« Votre physique n'est pas calibrée. »** → Exact, et l'interface l'affiche. E5, E6 et E7 renvoient « À venir » plutôt qu'un nombre invérifiable.

Dans les trois cas : **tu confirmes, tu expliques la décision, tu ne t'excuses pas.**

---

## Ce que tu ne dois jamais dire

Ces phrases coûtent cher, en soutenance comme en jeu de rôle :

- « Mon modèle prédit les pannes » → il estime une **probabilité de stabilité** sur une fenêtre de 60 s
- « C'est fiable à 95 % » → l'accuracy de 0,950 n'est pas une garantie terrain ; la valeur qui compte est **0,809 de F1-macro**
- « L'outil optimise le procédé » → il **aide à la décision**, l'opérateur décide
- « C'est prêt pour la production » → c'est un **prototype démontrable**, validé sur 8 essais
- « Les températures calculées sont exactes » → elles sont **nominales, non calibrées industriellement**

---

## Plan de révision — du 18 au 25 août

| Quand | Quoi | Durée |
|-------|------|-------|
| J-7 (18/08) | Lire `01` en entier, à voix haute, sans chrono | 1 h |
| J-6 (19/08) | `01` avec chrono, viser 24 min hors démo | 45 min |
| J-5 (20/08) | Lire `04` (jeu de rôle) et `03` (entretien pro) | 1 h |
| J-4 (21/08) | Entraînement jeu de rôle — scénarios 1 et 2 | 45 min |
| J-3 (22/08) | Entraînement jeu de rôle — scénarios 3 et 4 | 45 min |
| J-2 (23/08) | `01` complet avec la démo live intégrée, chronométré | 45 min |
| J-1 (24/08) | `05_ANTISECHE` + `06_CHECKLIST`, puis on s'arrête | 30 min |
| **J (25/08)** | **Pré-soutenance** | — |

**Après le 25** : remplis la grille de capture à la fin de `00` (ci-dessous) pendant que c'est frais. C'est le vrai matériau pour le 9 septembre.

---

## Grille de capture — à remplir juste après la pré-soutenance du 25

La pré-soutenance a une valeur que la vraie n'aura pas : **tu peux te tromper gratuitement.** Sa seule utilité est de te révéler les objections que ce dossier n'a pas anticipées. Ne cherche pas à être parfait le 25 ; cherche à te faire démonter.

### Questions posées que je n'avais pas prévues

| # | Question exacte (mot pour mot) | Qui l'a posée | Ce que j'ai répondu | Ce que j'aurais dû répondre |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

### Moments où j'ai bafouillé, hésité, ou perdu le fil

| Slide / bloc | Ce qui s'est passé | Correction à apporter |
|---|---|---|
| | | |
| | | |
| | | |

### Timing réel

| Bloc | Temps prévu | Temps réel | Écart |
|------|-------------|------------|-------|
| Présentation | 30 min | | |
| dont démo live | 5 min | | |

### Ce qui a bien fonctionné (à ne surtout pas changer)

-
-
-

### Remarques du jury sur la forme

> Débit, posture, regard, tics de langage, gestion du support :

-
-
