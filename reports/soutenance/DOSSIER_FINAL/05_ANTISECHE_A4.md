# ANTISÈCHE — 9 septembre 2026

> **La seule feuille que tu emportes.** Recto-verso, imprimée. Rien d'autre.
> Sous stress, on ne lit pas 40 pages — on lit une page.

---

# RECTO

## Fil rouge — à dire au mot près

> « Rendre un procédé d'extrusion bivis **lisible, comparable et prédictible** — sans jamais faire passer une valeur non calibrée pour une mesure. »

## Les 12 chiffres à ne pas rater

| | |
|---|---|
| Positions de vis / types d'éléments / zones | **81 · 13 · 8** |
| Règles de l'agent | **11** |
| Essais exploitables / relevés bruts | **8 · 310 782** |
| Fenêtres (60 s) / variables | **627 · 87** |
| LOGO vs aléatoire | **0,79 vs 0,92** (15 pts) |
| F1-macro retenu (± écart-type) | **0,809 ± 0,126** |
| Exactitude / AUC | **0,950 · 0,976** |
| Le chiffre fuité | **0,918** → artefact |
| Validation externe | **AUC 0,753** · 3 479 fen. · 62 % |
| Base simulée | **100 800 lignes** |
| Tests / fichiers | **725 / 76** |
| Cas C1→C2→C3→C5 | **65 → 82 → 46 → +32** |

## Marche des 30 minutes — points de contrôle

| Cumul | Tu dois être à |
|---|---|
| **9:00** | Fin physique (diapo 10) |
| **14:50** | Fin de la fuite (diapo 15) |
| **17:50** | **Lancer la démo** (diapo 19) |
| **25:05** | Fin des 5 cas (diapo 21) |
| **29:00** | Merci (diapo 27) |

**Si en retard, coupe dans cet ordre :** 6 (SWOT) → 24 (Budget) → 23 (Veille) → 5 (Concurrence) → 20 (Profil).
**Ne coupe jamais :** 7 · 13 · 15 · 16 · 26 · la démo.

## Démo live — 4 temps, 5 minutes

1. **Supervision** (1:15) — état, score, alertes · *« les deux blocs sont étiquetés sur leur source »*
2. **Profil de vis** (1:15) — modifier un élément, KPI recalculés
3. **Défaut zone 5** (1:30) — 65 → 46, proba 0,30, alerte rouge ← *le moment qui convainc*
4. **Correction** (1:00) — +32 pts, alerte levée · *sensibilité · détectabilité · réversibilité*

**Si ça plante** → captures des diapos 19-20-21, *« je vous montre le même parcours en images »*. Pas d'excuse, pas de débogage.

---

# VERSO

## Les 3 questions certaines

**« Seulement 8 essais ? »**
> Oui, limite principale. C'est pour ça que j'ai pris LOGO plutôt qu'une partition aléatoire : 15 points de moins, mais le seul chiffre honnête.

**« Vous n'atteignez pas 0,85. »**
> Non. 0,809 est la valeur vraie après correction de la fuite. Le 0,918 aurait atteint la cible et aurait été faux.

**« Votre physique n'est pas calibrée. »**
> Exact, et l'interface l'affiche. E5, E6, E7 renvoient « À venir » plutôt qu'un nombre invérifiable.

**Dans les trois cas : je confirme, j'explique la décision, je ne m'excuse pas.**

## Le piège du tableau corrigé

**« Le SVM fait 0,824, la forêt 0,809. Pourquoi la moins bonne ? »**
> Sélection faite sans augmentation (0,809 vs 0,805) · écart de 0,015 **très inférieur** à ± 0,126, donc indiscernables · la forêt donne l'importance des variables · le SVM reste intégré comme challenger.

## Lignes rouges — jeu de rôle

| Jamais | À la place |
|---|---|
| Valeurs calibrées | « Nominales. Calibrer = campagne dédiée. » |
| Perf > 0,809 garantie | « 0,809 ± 0,126 sur 8 essais. » |
| Clé en main | « Prototype. L'industrialisation est un projet distinct. » |
| Garantie procédé | « L'outil aide à décider, il n'exécute rien. » |
| Temps réel | « Fenêtres 60 s, hors ligne. » |
| Un prix / une date | « Je réponds après avoir vu vos données. » |

## Méthode objection · réclamation

**Objection** : accuse réception → **reformule** → une seule preuve → « ça répond à votre point ? »

**Réclamation** : impact d'abord → **pas de "oui mais"** → établir les faits ensemble → assumer / délimiter → action datée

## Phrases de secours

> « Je préfère vous dire non maintenant plutôt que de vous décevoir dans six mois. »
> « Je ne l'ai pas mesuré. Voici comment je m'y prendrais. »
> « Avant de répondre, est-ce que je peux vous poser une question sur votre contexte ? »

## Ne dis jamais

~~« mon modèle prédit les pannes »~~ → estime une probabilité de stabilité
~~« fiable à 95 % »~~ → 0,809 de F1-macro
~~« l'outil optimise »~~ → il aide à décider
~~« prêt pour la production »~~ → prototype démontrable

---

## Avant d'entrer

☐ Application **réveillée** (elle met 20 s à démarrer)
☐ Onglet démo ouvert, page Supervision affichée
☐ PDF de la présentation ouvert en plein écran
☐ Téléphone en mode avion
☐ Eau
☐ Respire. Tu connais ce projet mieux que quiconque dans la salle.
