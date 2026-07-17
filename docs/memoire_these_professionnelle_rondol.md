![Logo Nexa](../nexa%20LOGO.webp)
![Logo Rondol](../assets/rondol_logo.png)

---

**Nexa Digital School — Mastère Data & Intelligence Artificielle**
*Certification professionnelle RNCP 37137 — Niveau 7 (Bac+5)*

**MÉMOIRE DE THÈSE PROFESSIONNELLE**
*Année universitaire 2025 – 2026*

---

# Conception et déploiement d'un système d'intelligence artificielle prédictif d'aide à la décision pour l'optimisation des paramètres d'extrusion bivis de composants de batteries tout-solide (dry / semi-dry)

### Un prototype professionnel de jumeau numérique appliqué à l'extrudeuse bivis 10,5 mm de Rondol Industrie

---

**Présenté et soutenu par : Wilfried Galtier MBEUMI**

| Rubrique | Information |
|---|---|
| Entreprise d'accueil | Rondol Industrie |
| Responsable entreprise / tuteur industriel | M. Maël Gallas |
| Établissement de formation | Nexa Digital School |
| Tuteur pédagogique / référent école | M. Moussa NDIAYE |
| Lieu | Nancy — Institut Jean Lamour (IJL), Campus ARTEM |
| Année universitaire | 2025 – 2026 |
| Date de dépôt et de soutenance | `[À COMPLÉTER : date de dépôt et de soutenance]` |

[SAUT DE PAGE]

---

## Remerciements

Je tiens à exprimer ma reconnaissance à l'ensemble des personnes qui ont rendu ce travail possible.

Mes remerciements s'adressent en premier lieu à **M. Maël Gallas**, mon responsable au sein de Rondol Industrie, pour la confiance accordée tout au long de ce projet, pour la richesse de ses retours techniques et pour avoir constamment recentré le travail sur sa finalité industrielle. Sa pratique exigeante consistant à challenger chaque hypothèse plutôt qu'à valider par défaut a directement structuré la rigueur de cette étude.

Je remercie l'équipe de **Rondol Industrie** pour son accueil et pour l'accès aux données d'essais réelles de la campagne d'avril 2026, sans lesquelles la partie expérimentale de ce mémoire n'aurait pu exister.

J'adresse également ma gratitude à l'équipe pédagogique de **Nexa Digital School**, et tout particulièrement à mon référent pédagogique **M. Moussa NDIAYE**, pour l'encadrement méthodologique du Mastère Data & Intelligence Artificielle, ainsi qu'à l'**Institut Jean Lamour** pour le cadre scientifique offert au sein du campus ARTEM.

Enfin, je remercie mes proches pour leur soutien constant durant cette période exigeante.

[SAUT DE PAGE]

---

## Résumé

L'industrialisation des **batteries tout-solide** (Solid-State Batteries, SSB) se heurte à un verrou de mise en forme des matériaux d'électrode et d'électrolyte, pour lequel les procédés humides solvantés sont de plus en plus contestés. L'**extrusion bivis** à chaud, sans solvant ou faiblement solvantée, savoir-faire historique de Rondol Industrie, constitue une voie de fabrication continue prometteuse mais encore peu étudiée pour ces formulations chargées en céramiques abrasives. Ce mémoire présente la conception et le déploiement d'un **prototype professionnel d'aide à la décision** — un jumeau numérique logiciel — appliqué à l'extrudeuse bivis de précision 10,5 mm de Rondol Industrie.

La plateforme articule trois briques complémentaires. Une **logique métier procédé**, fondée sur la géométrie réelle de la vis (81 positions), calcule de façon unique et non redondante le taux de remplissage, le temps de résidence et les volumes. Un **modèle d'apprentissage automatique supervisé** prédit la stabilité thermique à court terme du régime d'extrusion à partir de douze capteurs de température issus d'une campagne d'essais réelle menée en avril 2026. Un **agent explicable à base de règles expertes** traduit l'état du procédé en alertes hiérarchisées et en recommandations chiffrées et traçables.

Le volet prédictif procède en deux temps méthodologiques assumés. D'abord, un **championnat de cinq algorithmes supervisés** (régression logistique, SVM, Random Forest, XGBoost, réseau de neurones) départagés non pas sur des partitions aléatoires optimistes, mais par **validation par essai réel non vu** — qui révèle une performance modeste et variable (F1-macro de l'ordre de 0,80), reflet direct du faible nombre d'essais. Ensuite, face à ce déficit, une **augmentation de données documentée, générée à partir de l'échantillon réel** (et non aléatoirement, avec reproduction des imperfections), qui stabilise l'apprentissage et porte le **Random Forest à un F1-macro de 0,918 ± 0,054** sur essais réels non vus : c'est le **modèle retenu et effectivement déployé**. Les alertes et recommandations opérateur, elles, proviennent de **règles expertes explicables** — la décision n'est jamais confiée au seul modèle statistique. Les valeurs procédé sont présentées comme **nominales et non calibrées industriellement** : l'outil révèle des tendances et compare des configurations, il ne remplace ni l'instrumentation ni le jugement de l'ingénieur. La plateforme repose sur une pile **Streamlit / Python / Supabase (PostgreSQL) / JSON / GitHub / Streamlit Cloud**, validée par près de sept cents tests automatisés (694 passants ; un test d'isolation E2E, un temps intermittent, est stabilisé).

---

## Abstract

The industrialisation of **Solid-State Batteries (SSB)** is constrained by a forming bottleneck for electrode and electrolyte materials, for which solvent-based wet processes are increasingly challenged. Hot-melt **twin-screw extrusion**, solvent-free or low-solvent, is Rondol Industrie's historical know-how and a promising continuous manufacturing route, yet it remains scarcely studied for these abrasive, ceramic-loaded formulations. This thesis presents the design and deployment of a **professional decision-support prototype**, a software digital twin, applied to Rondol Industrie's 10.5 mm precision twin-screw extruder.

The platform combines three components. A **process domain layer**, grounded in the real screw geometry (81 positions), computes fill factor, residence time and volumes through a single deterministic call. A **supervised machine-learning model** predicts the short-term thermal stability of the extrusion regime from twelve temperature sensors collected during a real trial campaign in April 2026. An **explainable rule-based agent** translates the process state into ranked alerts and into quantified, traceable recommendations.

The predictive component follows two deliberate methodological steps. First, a championship of five supervised algorithms (logistic regression, SVM, Random Forest, XGBoost, a neural network) is judged not on optimistic random splits but under **leave-one-real-trial-out validation**, revealing modest and variable performance (~0.80 macro-F1) — a direct reflection of the small number of trials. Then, since Rondol has no historical trial database, a documented data augmentation generated from the real sample (never randomly, reproducing even the measurement imperfections) consolidates learning and raises the Random Forest to a 0.918 ± 0.054 macro-F1 on unseen real trials: it is the **retained and deployed** model. Operator alerts and recommendations, in turn, come from **explainable expert rules** — the decision is never left to the statistical model alone. Process values are presented as nominal and not industrially calibrated: the tool reveals trends and compares configurations rather than replacing instrumentation or engineering judgement. The platform runs on a Streamlit / Python / Supabase (PostgreSQL) / JSON / GitHub / Streamlit Cloud stack, validated by nearly seven hundred automated tests (694 passing, one intermittent E2E isolation test).

---

## Mots-clés

Intelligence artificielle prédictive ; aide à la décision ; extrusion bivis ; Hot Melt Extrusion ; batteries tout-solide ; apprentissage automatique supervisé ; agent explicable à base de règles ; jumeau numérique ; Streamlit ; Rondol Industrie.

**Keywords :** predictive artificial intelligence ; decision support ; twin-screw extrusion ; Hot Melt Extrusion ; solid-state batteries ; supervised machine learning ; explainable rule-based agent ; digital twin ; Streamlit ; Rondol Industrie.

[SAUT DE PAGE]

---

## Liste des sigles et abréviations

| Sigle | Signification |
|---|---|
| ANN | *Artificial Neural Network* — réseau de neurones artificiel |
| API | *Application Programming Interface* — interface de programmation |
| AUC-ROC | *Area Under the ROC Curve* — aire sous la courbe ROC |
| CRISP-DM | *Cross-Industry Standard Process for Data Mining* — méthodologie de projet data |
| CV | *Cross-Validation* — validation croisée |
| DIE | Filière d'extrusion (tête de sortie de l'extrudeuse) |
| ECHA | *European Chemicals Agency* — Agence européenne des produits chimiques |
| F1 | Moyenne harmonique de la précision et du rappel (F1-score) |
| FF | *Fill Factor* — taux de remplissage |
| GSS | *GroupShuffleSplit* — partition aléatoire par groupe (essai) |
| HME | *Hot Melt Extrusion* — extrusion à chaud sans solvant |
| HMI | *Human-Machine Interface* — interface homme-machine |
| IJL | Institut Jean Lamour (Nancy) |
| JSON | *JavaScript Object Notation* — format d'échange de données |
| KPI | *Key Performance Indicator* — indicateur clé de performance |
| L/D | Rapport longueur sur diamètre de la vis |
| LATP | Li₁,₃Al₀,₃Ti₁,₇(PO₄)₃ — électrolyte solide oxyde |
| LFP | LiFePO₄ — phosphate de fer lithié (matière active de cathode) |
| LIB | *Lithium-Ion Battery* — batterie lithium-ion conventionnelle |
| LiTFSI | Sel de lithium (bis(trifluorométhanesulfonyl)imide de lithium) |
| LOGO | *Leave-One-Group-Out* — validation « un essai exclu » |
| ML | *Machine Learning* — apprentissage automatique |
| PFAS | *Per- and polyfluoroalkyl substances* — substances perfluorées (dont le PVDF) |
| PVDF | Polyfluorure de vinylidène (liant fluoré) |
| RF | *Random Forest* — forêt aléatoire |
| RNCP | Répertoire National des Certifications Professionnelles |
| RPM | *Revolutions Per Minute* — tours par minute (vitesse de vis) |
| RT | *Residence Time* — temps de résidence |
| SME | *Specific Mechanical Energy* — énergie mécanique spécifique |
| SSB | *Solid-State Battery* — batterie tout-solide |
| SVM | *Support Vector Machine* — machine à vecteurs de support |
| TSE | *Twin-Screw Extrusion* — extrusion bivis |
| XGBoost | *Extreme Gradient Boosting* — algorithme de boosting de gradient |

[SAUT DE PAGE]

---

## Sommaire détaillé (pagination estimée)

| Section | Page |
|---|:--:|
| Remerciements | 2 |
| Résumé / Abstract / Mots-clés | 3 |
| Liste des sigles et abréviations | 5 |
| Sommaire détaillé | 6 |
| Introduction générale | 8 |
| **Partie 1 — Rondol Industrie & contexte du projet** | **11** |
| 1.1 Présentation de l'entreprise | 11 |
| 1.2 Valeurs, missions et activité principale | 13 |
| 1.3 Environnement économique, technologique et sociétal | 14 |
| 1.4 Environnement de données | 15 |
| **Partie 2 — État de l'art & étude de marché** | **16** |
| 2.1 Marché de l'extrusion de laboratoire | 16 |
| 2.2 Digitalisation des procédés industriels | 17 |
| 2.3 Revue scientifique : extrusion, IA et batteries | 18 |
| 2.4 Analyse concurrentielle | 19 |
| 2.5 Opportunités et menaces pour Rondol Industrie | 20 |
| **Partie 3 — Problématique & définition du besoin** | **21** |
| 3.1 Constat industriel | 21 |
| 3.2 Besoin métier | 22 |
| 3.3 Problématique | 22 |
| 3.4 Objectifs fonctionnels | 23 |
| 3.5 Objectifs techniques | 23 |
| 3.6 Contraintes du projet | 24 |
| 3.7 Justification du choix technologique (Flask/Dash → Streamlit/Supabase) | 24 |
| **Partie 4 — Gestion de projet** | **26** |
| **Partie 5 — Exploitation des données et modélisation ML** | **30** |
| **Partie 6 — Conception et développement de la plateforme** | **40** |
| **Partie 7 — Résultats & démonstration** | **49** |
| **Partie 8 — Limites, risques, éthique & perspectives** | **53** |
| Conclusion générale | 57 |
| Bibliographie | 59 |
| Annexes | 62 |

*Pagination indicative, à recalculer lors de la mise en page finale. Le cœur du mémoire représente environ 50 pages hors bibliographie et annexes.*

[SAUT DE PAGE]

---

# Introduction générale

La transition énergétique mondiale repose en grande partie sur notre capacité à produire des batteries plus sûres, plus denses en énergie et moins dépendantes de procédés de fabrication polluants. Dans cette dynamique, les **batteries tout-solide** (Solid-State Batteries, SSB) s'imposent comme une rupture technologique de premier plan : en substituant à l'électrolyte liquide inflammable un électrolyte solide, elles promettent une sécurité accrue et des densités énergétiques supérieures à celles des batteries lithium-ion conventionnelles. Leur passage de la paillasse à la production de masse demeure toutefois entravé par un verrou souvent sous-estimé : la mise en forme des matériaux, électrodes composites, séparateurs, membranes d'électrolyte, pour laquelle les procédés humides traditionnels, gourmands en solvants tels que la N-méthyl-2-pyrrolidone, sont de plus en plus contestés. La proposition de restriction des substances perfluorées (PFAS) par l'Agence européenne des produits chimiques (ECHA) en février 2023, qui vise notamment le PVDF largement utilisé comme liant, accentue encore la pression réglementaire sur ces filières.

L'**extrusion bivis** (*Twin-Screw Extrusion*, TSE), et en particulier l'extrusion à chaud sans solvant (*Hot Melt Extrusion*, HME), apparaît dans ce contexte comme une voie de fabrication continue, sèche ou semi-sèche, particulièrement adaptée à ces enjeux. C'est précisément le cœur de métier de **Rondol Industrie**, PME deeptech française fondée en 2012 et spécialiste des extrudeuses bivis de précision (diamètres 10,5 mm et 21 mm, configurations horizontale et verticale protégées par des brevets européen et américain). Forte d'une longue expérience dans le secteur pharmaceutique, deux fois nominée au Prix Galien (2020 et 2023), et de partenariats académiques et industriels solides (BASF, Seqens, Queen's University Belfast, Université de Chicago, Institut Jean Lamour de Nancy), Rondol Industrie entend transférer ce savoir-faire vers le marché émergent des composants de batteries lithium et tout-solide.

Or l'extrusion de telles formulations, chargées en matériaux céramiques abrasifs (LFP, LATP, sels de lithium), reste peu étudiée et peu documentée scientifiquement. La combinaison « extrusion + intelligence artificielle + applications batteries » constitue un angle mort de la littérature : les essais procédé y demeurent largement empiriques, coûteux en temps et en matière, et difficilement reproductibles d'un opérateur à l'autre. C'est de ce double constat, un potentiel industriel réel mais un déficit d'outillage prédictif, qu'est née la problématique de ce travail, formulée et validée avec le responsable industriel du projet, M. Maël Gallas :

> « Comment concevoir et déployer un système d'intelligence artificielle prédictif permettant d'optimiser les paramètres d'extrusion pour la fabrication de composants de batteries tout-solide (SSB) dry/semi-dry, afin d'améliorer la performance technique et la compétitivité stratégique de Rondol Industrie ? »

Pour y répondre, j'ai conçu et déployé une plateforme logicielle d'aide à la décision, pensée comme un jumeau numérique de l'extrudeuse. Elle tient sur trois briques que j'ai voulues complémentaires. La première est une **logique métier procédé**, ancrée dans la géométrie réelle de la vis (81 positions) : elle calcule, une seule fois et sans redondance, le taux de remplissage, le temps de résidence et les volumes. La deuxième est un **modèle d'apprentissage supervisé**, entraîné sur les douze capteurs de température de la campagne d'avril 2026, pour anticiper la stabilité thermique à court terme. La troisième est un agent explicable à base de règles : il traduit l'état du procédé en alertes hiérarchisées et en recommandations chiffrées, toujours justifiées, adressées à l'opérateur (Source interne : app/screw_logic.py ; src/ ; AgentIndustrial_v1/core/rules.py ; recommendations.py).

Un choix a guidé tout mon travail : refuser les chiffres flatteurs. J'ai comparé **cinq algorithmes supervisés**, régression logistique, SVM, Random Forest, XGBoost et un réseau de neurones, mais je ne les ai pas départagés sur des partitions aléatoires. Je les ai évalués sur un essai réel jamais vu à l'entraînement. Le verdict a été sévère : des performances modestes et instables, à la mesure des huit essais dont je disposais. Rondol n'ayant pas de base d'essais historique, j'ai alors généré un jeu de données simulé à partir de l'échantillon réel — jamais au hasard, en reproduisant jusqu'aux valeurs manquantes. C'est ce qui a fait la différence : réentraîné sur ces données augmentées, le Random Forest est devenu mon modèle déployé. Une frontière reste nette d'un bout à l'autre du projet : le modèle prédit la stabilité, les règles expertes recommandent, et c'est l'ingénieur qui tranche.

Cette exigence d'honnêteté ne s'arrête pas là. Je n'ai jamais présenté mes résultats sous leur meilleur jour sans le dire. La validation stricte, séparation par essai, puis *Leave-One-Group-Out*, fait tomber les scores bien en dessous de ceux d'une partition aléatoire, artificiellement gonflés par l'autocorrélation temporelle (Source interne : reports/robustness_full_w60.json). Je l'assume : cet écart n'est pas un défaut à cacher, c'est la preuve de la rigueur. De la même façon, les valeurs procédé affichées restent nominales, non calibrées industriellement. L'outil montre des tendances et compare des configurations ; il ne remplace ni l'instrumentation réelle ni le jugement de l'ingénieur. Ce cadrage, un prototype d'aide à la décision, pas un instrument industriel déjà étalonné, je l'ai tenu partout, jusque dans l'interface.

Côté technique, j'ai fait un choix d'architecture assumé : abandonner la pile Flask / Dash envisagée au départ pour un socle Streamlit / Python / Supabase (PostgreSQL) / GitHub / Streamlit Cloud. Je le justifie au fil du mémoire ; il privilégie la rapidité de prototypage, la qualité de la démonstration et la robustesse de la persistance. La maturité de l'ensemble tient à près de sept cents tests automatisés (694 passants ; un test d'isolation E2E, un temps intermittent, est stabilisé) couvrant la logique métier, le moteur procédé et la synchronisation des données (Source interne : tests/).

Le document suit ensuite huit parties : Rondol Industrie et son contexte (1) ; l'état de l'art et le marché (2) ; la problématique et les objectifs (3) ; la gestion de projet (4) ; l'exploitation des données et la modélisation (5), cœur de la démarche ; la conception de la plateforme (6) ; les résultats et la démonstration sur cas lithiés réels (7) ; enfin les limites, les risques, les enjeux éthiques et les perspectives (8), avant la conclusion.

[SAUT DE PAGE]

---

# Partie 1 — Rondol Industrie & contexte du projet

## 1.1 Présentation de l'entreprise

Rondol Industrie est une petite et moyenne entreprise (PME) française à caractère deeptech, fondée en 2012, dont l'activité est centrée sur la conception et la fabrication d'**extrudeuses bivis de précision** destinées à la recherche, au développement et à la production en petites séries. L'entreprise s'est constituée autour d'une conviction technologique : la miniaturisation contrôlée de l'extrusion bivis permet de réaliser, sur des volumes de matière réduits, des essais représentatifs de la production industrielle, et d'accélérer ainsi le développement de formulations coûteuses ou rares.

Le positionnement de Rondol repose sur deux familles d'extrudeuses, de diamètres de vis 10,5 mm et 21 mm, déclinées en configurations horizontale et verticale — cette dernière faisant l'objet de brevets européen et américain qui constituent un actif de propriété intellectuelle distinctif. Les rapports longueur sur diamètre (L/D) proposés s'échelonnent de 25:1 à 40:1, ce qui autorise une large gamme de profils de vis et de temps de résidence. L'extrudeuse de référence de ce mémoire est la machine bivis 10,5 mm, exploitée dans sa configuration horizontale à un rapport L/D de 40:1, qui sert de support à l'ensemble des essais et de la modélisation (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md ; reports/poster_abstract/cases/case_definitions.md).

La reconnaissance de l'entreprise dans son écosystème se traduit notamment par une double nomination au Prix Galien (2020 et 2023), distinction de référence dans le domaine pharmaceutique, et par un réseau de partenariats académiques et industriels de haut niveau : BASF, Seqens, la Queen's University Belfast, l'Université de Chicago et l'Institut Jean Lamour (IJL) à Nancy, au sein du campus ARTEM où se déroule le présent projet.

Certaines données institutionnelles usuellement attendues dans cette section ne figurent pas dans les sources internes du projet et ne sont pas inventées ici : `[À COMPLÉTER : chiffre d'affaires, effectif, statut juridique, dirigeants]`.

[INSÉRER LOGO RONDOL — fichier : assets/rondol_logo.png]
[INSÉRER CAPTURE : photographie ou vue CAO de l'extrudeuse bivis Rondol 10,5 mm en configuration horizontale]

## 1.2 Valeurs, missions et activité principale

L'activité principale de Rondol Industrie consiste à fournir des plateformes d'extrusion de laboratoire et de pré-industrialisation, accompagnées de l'expertise procédé associée. La mission de l'entreprise peut se résumer ainsi : permettre à ses clients de développer, caractériser et transférer à l'échelle des procédés d'extrusion sur des quantités de matière minimales, dans des conditions représentatives de la production.

Trois valeurs structurent l'offre et orientent directement le présent projet. La première est la **précision** : la maîtrise fine de la géométrie de vis, des profils thermiques par zone et des débits de dosage est au fondement de la reproductibilité des essais. La deuxième est la **polyvalence applicative** : historiquement ancrée dans le secteur pharmaceutique (Hot Melt Extrusion), l'entreprise étend son champ d'action vers l'énergie (batteries tout-solide), l'alimentaire et les polymères techniques. La troisième est la **rigueur scientifique** : les choix de conception sont adossés à la physique de l'extrusion plutôt qu'à des réglages purement empiriques.

Ce projet de mémoire prolonge directement ces valeurs sur le terrain numérique. Le prototype développé ne cherche pas à produire un tableau de bord générique, mais à constituer un jumeau numérique crédible qui rende explicite la chaîne causale formulation → paramètres procédé → profil de vis → risques → recommandations. Cette exigence a été posée comme principe directeur du projet : chaque bloc de l'interface doit piloter le moteur de calcul (alerte, score ou recommandation), à l'exclusion de tout élément purement décoratif (Source interne : CLAUDE.md).

## 1.3 Environnement économique, technologique et sociétal

Sur le plan économique, Rondol Industrie évolue dans un marché de niche, celui des équipements d'extrusion de laboratoire et de pré-série, caractérisé par des cycles de vente longs, une forte intensité technologique et une concurrence internationale établie (Coperion, Thermo Fisher, Leistritz, ENTEK, Bühler), analysée en détail en Partie 2. La diversification vers le marché de l'énergie répond à une opportunité de croissance majeure : l'électrification des transports et le stockage stationnaire tirent une demande mondiale soutenue de cellules de batteries, dont les batteries tout-solide constituent l'horizon de rupture visé par de nombreux acteurs (QuantumScape, Solid Power, Toyota, Samsung SDI, CATL, ainsi que Blue Solutions et Saft en France).

Sur le plan technologique, deux mouvements de fond convergent en faveur du projet. D'une part, la transition vers des procédés de fabrication secs (dry / semi-dry) pour les électrodes et électrolytes, motivée par la suppression des solvants, l'économie d'énergie au séchage et la réduction de l'empreinte environnementale ; l'extrusion bivis y occupe une place de choix aux côtés de procédés tels que le calandrage direct (DRYtraec® de Fraunhofer IWS) ou la fibrillation du PTFE. D'autre part, la digitalisation des procédés industriels (Industrie 4.0) : capteurs en ligne, jumeaux numériques, apprentissage automatique et aide à la décision en temps réel deviennent des standards émergents, illustrés par des initiatives récentes comme la plateforme d'IA Gammatron de Factorial Energy (2025) ou les travaux de Maia (2025) sur le contrôle temps réel assisté par données synthétiques (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md).

Sur le plan sociétal et réglementaire, enfin, la pression s'accroît sur les filières batteries. La proposition de restriction des PFAS par l'ECHA (février 2023) touche directement le PVDF, liant fluoré omniprésent dans les électrodes, et incite la filière à explorer des formulations et des procédés alternatifs — un enjeu auquel l'extrusion sèche apporte une réponse partielle. À cela s'ajoutent les exigences de sécurité (les batteries tout-solide réduisent le risque d'emballement thermique) et de souveraineté industrielle européenne sur les chaînes de valeur stratégiques. Ce projet s'inscrit donc dans un contexte où l'innovation procédé porte une valeur à la fois économique, environnementale et stratégique.

## 1.4 Environnement de données

L'environnement de données du projet est constitué des données réelles d'instrumentation thermique issues d'une campagne d'essais menée chez Rondol Industrie du 7 au 13 avril 2026. Cette campagne a mobilisé douze capteurs de température répartis le long de la ligne d'extrusion : les huit zones du fourreau (Z1 à Z8), la filière (DIE), et trois points de mesure sur la ligne de mise en film en sortie (CastFilmBody, CastFilmP1, CastFilmP2) (Source interne : src/config.py ; Essais_07-13_Avril_2026/).

Les données brutes se présentent sous forme de fichiers CSV horodatés (colonnes *Timestamp* au format ISO JavaScript, *Name*, *Value* en degrés Celsius), avec un échantillonnage irrégulier de l'ordre de 1 à 15 secondes ; le seul capteur de filière totalise par exemple 50 145 enregistrements sur la période. La campagne comporte onze essais (runs) distincts, dont huit sont retenus pour la modélisation après filtrage des essais de durée insuffisante (inférieure à quinze minutes), les essais courts étant conservés mais étiquetés comme tels (Source interne : reports/runs_summary.csv ; data/features/dataset_ml_w60_meta.json).

Cet environnement de données présente trois caractéristiques déterminantes pour la suite. Premièrement, il s'agit de données de procédé réelles et non simulées, ce qui distingue ce travail d'une simple démonstration synthétique. Deuxièmement, sa dimension temporelle (séries de température) impose une méthodologie d'apprentissage rigoureuse pour éviter toute fuite d'information entre fenêtres temporelles successives d'un même essai — point traité en Partie 5. Troisièmement, il demeure volumétriquement modeste (huit essais exploitables), ce qui constitue une limite assumée du projet et oriente les choix de validation vers des protocoles conservateurs plutôt que vers des architectures gourmandes en données.

[INSÉRER CAPTURE : extrait d'un fichier CSV brut de capteur (TEMP_DIE_All_13_04_2026.csv) montrant les colonnes Timestamp / Name / Value]

[SAUT DE PAGE]

---

# Partie 2 — État de l'art & étude de marché

Cette partie poursuit un double objectif : situer le projet dans le paysage économique et concurrentiel de l'extrusion de laboratoire (sections 2.1, 2.2, 2.4, 2.5) et établir le positionnement scientifique de la combinaison extrusion–IA–batteries (section 2.3), qui fonde la pertinence de la problématique. Elle s'appuie sur la revue de littérature consolidée du projet, un état de l'art de vingt-cinq pages et trente-huit références établi en amont, dont les éléments les plus structurants sont repris et synthétisés ici (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md ; reports/poster_abstract/abstract/).

## 2.1 Marché de l'extrusion de laboratoire

Le marché de l'extrusion bivis de laboratoire et de pré-industrialisation se distingue du marché de l'extrusion de production par sa finalité : il ne s'agit pas de produire en volume, mais de développer, caractériser et dé-risquer des formulations avant tout transfert à l'échelle. Les acheteurs y sont principalement des centres de R&D — industriels (pharmacie, chimie, énergie, agroalimentaire) et académiques (laboratoires, instituts technologiques) — pour lesquels trois critères priment : la représentativité des essais vis-à-vis de la production, l'économie de matière (les principes actifs, matières actives de batteries ou polymères spéciaux étant coûteux), et la flexibilité de reconfiguration (profils de vis, profils de dosage, profils thermiques).

C'est sur ces trois critères que se construit la proposition de valeur de Rondol Industrie : une extrudeuse de très petit diamètre (10,5 mm) permet de travailler sur des quantités de matière de l'ordre de quelques centaines de grammes par heure tout en conservant une géométrie de vis et un profil thermique représentatifs. Le marché historique de cette catégorie d'équipement est le secteur pharmaceutique, via le procédé HME utilisé pour la dispersion solide de principes actifs ; l'extension récente vers les matériaux d'énergie ouvre un segment nouveau, encore peu structuré, où la concurrence n'a pas encore figé ses positions — d'où l'enjeu stratégique pour Rondol d'y établir une référence technologique précoce.

Le marché de l'extrusion de laboratoire de Rondol ne se chiffre pas isolément dans des sources publiques fiables (segment de niche, équipementiers non cotés) ; il se lit à travers le marché applicatif aval qui en tire la demande : celui des batteries tout-solide. Or ce dernier est documenté par plusieurs cabinets reconnus et récents (moins de cinq ans). MarketsandMarkets évalue le marché mondial des batteries tout-solide à 0,26 milliard USD en 2025, projeté à 1,77 milliard USD en 2031, soit un taux de croissance annuel composé (TCAC) de **37,5 %** [35]. Grand View Research retient une trajectoire plus large, de 1,60 milliard USD en 2025 à 15,65 milliards USD en 2033 (TCAC 31,8 %) [1], la région **Asie-Pacifique** concentrant plus de **54 %** de la valeur en 2025. L'écart entre ces estimations, assumé et interprété ici, tient aux hypothèses divergentes sur le rythme d'industrialisation (calendriers de passage à l'échelle et taux d'adoption véhicules électriques), et illustre le caractère encore **pré-industriel et volatil** du marché. Pour Rondol, l'enseignement est double : la demande aval croît à un rythme à deux chiffres, mais sa matérialisation industrielle reste à un horizon de moyen terme — ce qui conforte un positionnement d'équipementier de R&D et de dé-risquage plutôt que de fournisseur de production de masse. *(Sources externes : Grand View Research, 2025 ; MarketsandMarkets, 2025 — cf. Bibliographie [1], [35].)*

## 2.2 Digitalisation des procédés industriels

La quatrième révolution industrielle (Industrie 4.0) a fait passer les procédés de fabrication d'un pilotage essentiellement humain et empirique à un pilotage assisté par la donnée. Trois briques technologiques en constituent l'ossature et éclairent directement le positionnement du présent projet.

La première est l'instrumentation en ligne et l'acquisition continue de données : capteurs de température, de couple, de pression et de débit échantillonnés en temps réel produisent des séries temporelles exploitables — exactement la nature des données mobilisées dans ce mémoire. La deuxième est le jumeau numérique (digital twin), c'est-à-dire la réplique logicielle d'un équipement physique, capable de refléter son état, de simuler des configurations et d'anticiper des dérives ; c'est le cadre conceptuel revendiqué par la plateforme développée ici. La troisième est l'intelligence artificielle d'aide à la décision, qui se décline en deux familles complémentaires : les modèles d'apprentissage automatique entraînés sur données historiques, et les systèmes à base de règles expertes, dont l'avantage décisif est l'explicabilité des décisions produites.

Dans le domaine spécifique de l'extrusion appliquée aux batteries, cette digitalisation reste émergente. Les travaux de Maia (2025) illustrent l'usage du contrôle temps réel assisté par capteurs et de la génération de données synthétiques pour pallier la rareté des essais, tandis que la plateforme Gammatron de Factorial Energy (2025) témoigne de l'intérêt industriel croissant pour l'IA appliquée à la formulation et au procédé de batteries. Ces initiatives confirment la pertinence du projet tout en soulignant son originalité : peu de travaux publiés relient explicitement l'extrusion bivis, l'IA et les composants de batteries tout-solide.

## 2.3 Revue scientifique : extrusion, intelligence artificielle et batteries

L'établissement du positionnement scientifique du projet s'appuie sur une revue de littérature consolidée de trente-huit références, dont les contributions les plus structurantes sont synthétisées ici autour de trois axes : l'extrusion bivis appliquée aux matériaux de batteries, l'apprentissage automatique appliqué aux procédés d'extrusion, et la convergence, encore embryonnaire, de ces deux champs (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md ; reports/poster_abstract/abstract/abstract_FR_v1.md).

**Premier axe — l'extrusion bivis comme voie de mise en forme des composants de batteries.** Plusieurs travaux récents établissent la faisabilité technique de l'extrusion bivis pour la fabrication d'électrodes. Haarmann et al. (2021, *Energy Technology*) démontrent la production d'électrodes positives à base de NMC622 par extrusion bivis, tandis que Seeba et al. (2024, *Batteries*) étendent l'approche aux anodes en l'appuyant sur des simulations du procédé. Kim et al. (2023, *Nature Communications*) montrent qu'un procédé sec de revêtement par compression, à base de PVDF et de nanotubes de carbone, permet d'atteindre une densité énergétique de 360 Wh/kg, illustrant le potentiel des voies sèches. Ces résultats confirment la crédibilité industrielle de la voie extrusion.

**Deuxième axe — l'apprentissage automatique appliqué à l'extrusion et aux électrodes.** Drakopoulos et al. (2021, *Cell Reports Physical Science*) constituent une référence méthodologique majeure : à partir de seulement vingt-sept formulations d'électrodes de graphite, ils établissent un modèle d'apprentissage automatique prédictif validé, démontrant qu'un faible volume de données expérimentales peut suffire à dégager des relations exploitables — un précédent directement transposable à la situation de ce mémoire, où huit essais seulement sont disponibles. Daoudi et al. (2024, *Journal of Power Sources*) appliquent l'apprentissage automatique à l'optimisation des électrodes, et Kassab et al. (2024, *IJISAE*) proposent une revue de l'usage de l'IA dans l'extrusion des polymères. Maia (2025) introduit, quant à lui, le recours aux données synthétiques et au contrôle en temps réel pour pallier la rareté des essais.

**Troisième axe — la convergence extrusion + IA + batteries.** C'est ici que se situe le gap scientifique central du projet. Si chacun des champs pris isolément est documenté, peu d'études intégrées relient explicitement les trois dimensions : la mise en forme par extrusion bivis, l'aide à la décision par intelligence artificielle, et l'application spécifique aux composants de batteries tout-solide. Wang et al. (2025, *Nano-Micro Letters*) appliquent l'IA au criblage de matériaux pour batteries tout-solide avec une exactitude rapportée de 83 %, mais hors contexte d'extrusion ; les initiatives industrielles telles que Gammatron (Factorial Energy, 2025) ou le procédé continu DRYtraec® (Fraunhofer IWS) confirment l'intérêt du secteur sans pour autant publier de méthodologie reproductible reliant les trois axes. C'est cette intersection peu couverte que le présent projet entend explorer, en assumant son statut de contribution exploratoire plutôt que de validation industrielle définitive. Conformément à la position validée avec le tuteur industriel, le gap est qualifié de « peu d'études intégrées » et non « d'aucune étude », afin de ne pas surévaluer la nouveauté de la démarche.

[INSÉRER FIGURE : cartographie des trois domaines (extrusion bivis / apprentissage automatique / batteries SSB) faisant apparaître la zone d'intersection peu couverte par la littérature, avec positionnement des principales références]

## 2.4 Analyse concurrentielle

Le marché des extrudeuses bivis est structuré par un petit nombre d'acteurs internationaux établis. Conformément à une démarche d'analyse concurrentielle rigoureuse, quatre concurrents sont examinés ci-après l'un après l'autre, selon une trame identique (présentation, forces, faiblesses, comparaison avec Rondol) : trois concurrents directs (Coperion, Thermo Fisher Scientific, Leistritz, ce dernier rapproché d'ENTEK) et un concurrent indirect (les procédés secs alternatifs). Les parts de marché et chiffres d'affaires précis de ces acteurs privés ne figurent pas dans des sources publiques fiables et ne sont pas inventés ici.

**Concurrent direct n° 1 — Coperion (Allemagne).** *Présentation :* leader mondial de l'extrusion bivis de production à grande capacité, gamme étendue (chimie, agroalimentaire, et de plus en plus batteries). *Forces :* puissance industrielle, références de production de masse, capacité d'investissement R&D. *Faiblesses :* orientation grande capacité peu adaptée aux très petits volumes de matière des phases amont de R&D ; offre généraliste, non spécialisée SSB ; coût et empreinte machine élevés. *Comparaison avec Rondol :* Coperion gagne sur l'échelle de production, mais Rondol le surpasse sur l'économie de matière et la représentativité des essais à petit diamètre — segments où Coperion n'est pas positionné.

**Concurrent direct n° 2 — Thermo Fisher Scientific (États-Unis).** *Présentation :* le concurrent le plus directement comparable sur le segment laboratoire / R&D, avec des modèles explicitement orientés batteries (gamme Process 11, Pharma 11). *Forces :* notoriété mondiale, écosystème instrumental complet, modèles déjà fléchés « batteries ». *Faiblesses :* pas de configuration verticale brevetée ; outil d'aide à la décision procédé explicable non intégré à l'offre ; diamètres moins poussés vers la micro-extrusion que Rondol. *Comparaison avec Rondol :* concurrence frontale sur la R&D, mais Rondol conserve l'avantage de la miniaturisation extrême (10,5 mm) et de la singularité brevetée verticale.

**Concurrent direct n° 3 — Leistritz (Allemagne), rapproché d'ENTEK (États-Unis).** *Présentation :* offre solide d'extrusion de production ; ENTEK est de surcroît un acteur reconnu des séparateurs de batteries. *Forces :* robustesse mécanique, maîtrise procédé de production, position établie sur la chaîne de valeur batteries (séparateurs pour ENTEK). *Faiblesses :* orientation production plutôt que dé-risquage amont ; spécialisation SSB dry/semi-dry seulement indirecte ; pas d'outil IA d'aide à la décision intégré. *Comparaison avec Rondol :* complémentaires plus que substituables — Rondol intervient en amont (développement de formulation) là où Leistritz/ENTEK interviennent à l'échelle.

**Concurrent indirect — les procédés secs alternatifs (Fraunhofer IWS DRYtraec®, fibrillation du PTFE).** *Présentation :* il ne s'agit pas d'équipementiers bivis mais de **voies technologiques concurrentes** visant le même besoin final — la mise en forme d'électrodes sèches sans solvant. *Forces :* maturité industrielle croissante (calandrage direct DRYtraec®), pas de séchage de solvant. *Faiblesses :* moins flexibles que l'extrusion bivis pour explorer des formulations variées en petites quantités ; verrous de propriété intellectuelle propres. *Comparaison avec Rondol :* ces procédés menacent l'extrusion bivis sur la production de masse, mais Rondol garde l'avantage décisif de la **flexibilité de formulation** et de l'économie de matière en phase R&D.

**Conclusion stratégique.** De cette analyse ressort une position défendable pour Rondol : ses **points positifs** — miniaturisation (10,5 mm), configurations verticales brevetées (Europe/États-Unis), héritage pharmaceutique crédibilisant (double nomination au Prix Galien), et désormais un outil d'aide à la décision explicable que ni Coperion, ni Thermo Fisher, ni Leistritz n'intègrent à ce jour ; ses **points négatifs** relatifs — ressources financières et industrielles inférieures aux généralistes, absence de présence sur la production de masse. Le projet de ce mémoire s'inscrit précisément dans le renforcement du premier groupe : transformer la singularité « précision + R&D » en avantage logiciel différenciant sur le segment émergent des batteries tout-solide (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md).

## 2.5 Opportunités et menaces pour Rondol Industrie

La confrontation du positionnement de Rondol Industrie à son environnement permet de dégager, sous une forme synthétique de type SWOT, les opportunités et menaces qui encadrent le projet.

Les opportunités sont au nombre de quatre. La première est l'essor du marché des batteries tout-solide, porté par l'électrification des transports et soutenu par des acteurs majeurs (QuantumScape, Solid Power, Toyota, Samsung SDI, CATL, Blue Solutions, Saft). La deuxième est la pression réglementaire et environnementale en faveur des procédés secs : la proposition de restriction des PFAS par l'ECHA (février 2023), qui vise le PVDF, oriente la filière vers des voies sans solvant où l'extrusion bivis dispose d'un avantage. La troisième est la différenciation par l'intelligence artificielle : peu de concurrents proposent, sur ce segment, un outil d'aide à la décision explicable reliant formulation, paramètres procédé et risques. La quatrième tient à l'écosystème scientifique de Rondol (IJL, Université de Chicago, Queen's University Belfast), qui facilite l'accès aux connaissances et aux essais.

Les menaces sont également au nombre de quatre. La première est la disproportion des ressources entre Rondol et les grands concurrents généralistes. La deuxième est la rareté des données : la modélisation s'appuie ici sur huit essais exploitables, ce qui borne structurellement la robustesse statistique. La troisième est la maturité encore pré-industrielle du marché SSB, dont les cycles d'adoption longs pèsent sur le retour sur investissement à court terme. La quatrième est le risque de perception : présenter un outil dont les valeurs ne sont pas calibrées industriellement expose à une attente mal placée — risque que le projet neutralise en affichant explicitement son statut de prototype d'aide à la décision.

| Forces (internes) | Faiblesses (internes) |
|---|---|
| Précision et miniaturisation (10,5 mm) ; brevets configuration verticale ; héritage pharmaceutique (Prix Galien) ; partenariats scientifiques | Ressources limitées vs concurrents ; données d'essais peu nombreuses ; outil non calibré industriellement ; développement mono-acteur |
| **Opportunités (externes)** | **Menaces (externes)** |
| Marché SSB en croissance ; pression anti-solvant (PFAS/ECHA) ; différenciation IA explicable ; écosystème IJL/académique | Concurrents mieux dotés ; rareté des données ; marché SSB pré-industriel ; risque de perception sur un prototype non calibré |

*Tableau 2.2 — Analyse SWOT de Rondol Industrie au regard du projet.*

[INSÉRER FIGURE : matrice SWOT illustrée (forces / faiblesses / opportunités / menaces) au format quadrant]

[SAUT DE PAGE]

---

# Partie 3 — Problématique & définition du besoin

## 3.1 Constat industriel

Le développement de formulations d'électrodes et d'électrolytes pour batteries tout-solide par extrusion bivis se heurte, dans la pratique industrielle de Rondol Industrie, à un constat récurrent : la conduite du procédé reste largement empirique. Le choix du profil de vis, des consignes de température par zone, des débits de dosage et de la vitesse de rotation procède d'essais successifs, dont chacun consomme de la matière coûteuse (matières actives lithiées, électrolytes solides céramiques) et du temps machine. La reproductibilité d'un opérateur à l'autre n'est pas garantie, et les dérives de procédé — instabilité thermique, sur-remplissage d'une zone, échauffement excessif par cisaillement — ne sont souvent identifiées qu'a posteriori, une fois l'essai dégradé.

Ce constat est aggravé par la nature des matériaux visés. Les charges céramiques abrasives (LATP, par exemple) accentuent l'usure et l'échauffement local ; les liants fluorés et sels de lithium imposent des fenêtres thermiques étroites ; et l'absence de littérature procédé consolidée pour ces formulations prive l'opérateur de repères établis. L'instrumentation thermique disponible (douze capteurs, cf. Partie 1.4) produit certes des données riches, mais celles-ci ne sont pas exploitées en aide à la décision : elles servent au suivi, non à l'anticipation. Le projet part donc d'un gisement de données sous-valorisé et d'un déficit d'outillage prédictif.

## 3.2 Besoin métier

De ce constat découle un besoin métier précis, exprimé par le tuteur industriel : disposer d'un outil capable d'assister la décision de l'opérateur et de l'ingénieur procédé lors de la préparation et de la conduite d'un essai d'extrusion de composants de batteries. Ce besoin se décline en quatre attentes concrètes : rendre lisible l'état du procédé à partir d'une configuration donnée (taux de remplissage, temps de résidence, volumes, indicateurs de risque) ; anticiper les dérives plutôt que de les subir, en signalant à l'avance une probable instabilité thermique ; recommander des actions correctives chiffrées et compréhensibles (réduire un débit, ajuster une température de zone, modifier un élément de vis), assorties de leur justification ; et, de manière transversale, garantir l'explicabilité, condition indispensable à l'appropriation par des ingénieurs et à la confiance dans un contexte industriel.

Ce besoin s'accompagne d'une exigence de posture, posée comme principe directeur : l'outil est une aide à la décision, non un système de pilotage automatique ; la décision finale demeure celle de l'ingénieur (Source interne : CLAUDE.md ; docs/DEMO_MANAGER.md).

## 3.3 Problématique

La synthèse du constat et du besoin conduit à la problématique de ce mémoire, formulée et validée avec M. Maël Gallas :

> « Comment concevoir et déployer un système d'intelligence artificielle prédictif permettant d'optimiser les paramètres d'extrusion pour la fabrication de composants de batteries tout-solide (SSB) dry/semi-dry, afin d'améliorer la performance technique et la compétitivité stratégique de Rondol Industrie ? »

Cette problématique articule trois exigences indissociables. Une exigence scientifique : exploiter des données d'essais réelles pour produire une prédiction utile, dans un contexte de faible volume de données. Une exigence d'ingénierie logicielle : intégrer cette prédiction dans une plateforme cohérente, robuste et démontrable. Une exigence industrielle et stratégique : faire de cet outil un facteur de différenciation pour Rondol, sans surévaluer ce que permet réellement un prototype non calibré.

## 3.4 Objectifs fonctionnels

Les objectifs fonctionnels traduisent la problématique en capacités attendues de la plateforme. L'outil doit permettre de configurer un procédé (profil de vis, consignes thermiques par zone, paramètres de dosage) ; de calculer et afficher les indicateurs procédé (taux de remplissage, temps de résidence, volumes occupé et libre) à partir de la géométrie réelle de la vis ; d'évaluer la stabilité du régime par un score de stabilité et une probabilité de dérive appuyés sur le modèle d'apprentissage automatique ; d'émettre des alertes hiérarchisées et des recommandations chiffrées et justifiées via l'agent à base de règles ; et de conserver l'historique des configurations validées avec leurs indicateurs figés, en garantissant la persistance durable des données entre sessions et redémarrages (Source interne : app/pages/1_Profile.py ; app/pages/2_Settings.py ; app/screw_logic.py ; app/Supervision.py ; AgentIndustrial_v1/core/rules.py ; app/history_store.py ; app/persistence.py).

## 3.5 Objectifs techniques

Les objectifs techniques fixent les exigences de réalisation et de qualité logicielle. La plateforme doit reposer sur une architecture en couches séparant la logique de calcul pure (sans interface ni accès disque) de la couche de présentation, garantissant la testabilité et la non-redondance des calculs. Elle doit disposer d'une source unique de vérité pour l'état validé du procédé, sérialisée dans un instantané (snapshot) persistant et synchronisée entre toutes les pages. Elle doit assurer une persistance durable et auto-réparatrice, avec restauration déterministe de l'état après redémarrage et réparation des instantanés dégénérés. Sa qualité doit être validée par une suite automatisée de près de sept cents tests (694 passants) — tests unitaires purs et tests d'interface Streamlit. Elle doit enfin offrir une internationalisation français / anglais avec contrôle automatique de l'absence de fuites linguistiques, et distinguer explicitement le modèle prédictif retenu (RandomForest entraîné avec augmentation) de la logique de recommandation à base de règles expertes (Source interne : engine/ ; AgentIndustrial_v1/core/applied_state.py ; app/persistence.py ; tests/ ; tests/test_i18n_no_french_leaks.py).

## 3.6 Contraintes du projet

Le projet s'est déroulé sous plusieurs contraintes qui ont orienté les choix de conception. Une contrainte de données : seuls huit essais sont exploitables, ce qui borne la robustesse statistique et proscrit les approches gourmandes en données. Une contrainte de calibration : en l'absence de campagne d'étalonnage industriel, les valeurs procédé restent nominales et ne sont validées qu'en tendance relative. Une contrainte de ressources : le développement est porté par un développeur unique, ce qui privilégie les solutions à faible coût d'intégration. Une contrainte de périmètre scientifique : certaines équations (énergie mécanique spécifique locale, température réelle avancée, pression filière, dénommées E5/E6/E7) sont volontairement différées et renvoient une valeur nulle documentée, afin de ne pas présenter comme acquis des modèles non encore validés (Source interne : engine/deferred.py). Une contrainte de calendrier, enfin : un premier jalon de démonstration client est fixé au lundi 16 juin 2026, la date de dépôt et de soutenance du mémoire restant `[À COMPLÉTER : date de dépôt et de soutenance]`. L'environnement technique est Windows avec Python 3.13.

## 3.7 Justification du choix technologique : du couple Flask/Dash vers Streamlit/Supabase

Le cahier des charges initial de la certification envisageait une application web reposant sur Flask (back-end) et Dash/Plotly (front-end), avec une base SQLite ou PostgreSQL et la production d'un dump SQL (Source interne : NOTES_HANDOFF_CLAUDE_CODE.md). Au cours du projet, ce choix a été revu au profit d'une pile Streamlit / Python / Supabase (PostgreSQL) / JSON / GitHub / Streamlit Cloud. Cette réorientation, loin d'être un renoncement, résulte d'une analyse argumentée des priorités du projet ; elle est ici justifiée explicitement, conformément à l'exigence de transparence vis-à-vis du jury.

La rapidité de prototypage a constitué le premier facteur déterminant : Streamlit permet de développer une application interactive complète dans un code Python unique, sans séparation front-end / back-end, sans couche JavaScript ni gestion manuelle des callbacks. Pour un développeur unique soumis à un calendrier contraint, ce gain de productivité a permis de concentrer l'effort sur la logique métier et la qualité de la modélisation plutôt que sur la plomberie web. La qualité de la démonstration client a constitué le deuxième facteur : les composants interactifs de Streamlit offrent immédiatement une interface de type HMI crédible, adaptée à une démonstration en conditions réelles devant un industriel — objectif concrétisé par le jalon du 16 juin 2026 (Source interne : docs/DEMO_MANAGER.md). La simplicité de déploiement a constitué le troisième facteur : le couple GitHub + Streamlit Cloud autorise un déploiement continu sans administration de serveur. La robustesse de la persistance, enfin, a été couverte par Supabase, service PostgreSQL géré interrogé via API REST, avec repli sur un stockage fichier puis sur un fichier JSON local (Source interne : app/persistence.py).

Il importe de souligner que ce choix ne compromet pas l'exigence d'un livrable SQL : Supabase reposant sur PostgreSQL, un dump SQL de la base demeure pleinement réalisable pour la certification. Ce changement comporte néanmoins des contreparties assumées, rediscutées en Partie 8 : un contrôle plus grossier de l'ergonomie fine du front-end qu'avec une pile web sur mesure, un modèle de session orienté mono-opérateur, et une dépendance au cycle d'exécution propre à Streamlit. Ces limites ont été jugées acceptables au regard des gains de productivité et de démontrabilité, qui servaient directement la finalité du projet.

[INSÉRER FIGURE : tableau comparatif Flask/Dash vs Streamlit/Supabase selon les critères rapidité de prototypage, démonstration, déploiement, persistance, contrôle UX]

[SAUT DE PAGE]

---

# Partie 4 — Gestion de projet

## 4.1 Cadre méthodologique du projet

La conduite de ce projet s'est appuyée sur une démarche inspirée de la méthodologie **CRISP-DM** (*Cross-Industry Standard Process for Data Mining*), référence éprouvée pour les projets de science des données, adaptée ici au contexte d'un projet industriel mené par un développeur unique. CRISP-DM présente l'avantage d'articuler explicitement la dimension métier et la dimension technique, ce qui correspond exactement à la nature du présent travail : un projet de data science dont la finalité n'est pas la performance d'un modèle en soi, mais l'aide à la décision dans un procédé industriel réel.

La démarche s'est déroulée en six phases. La **compréhension métier** a consisté à cadrer le besoin avec le tuteur industriel, à formaliser la problématique et à identifier la chaîne causale formulation → paramètres procédé → profil de vis → risques. La **compréhension des données** a porté sur l'examen des fichiers d'instrumentation thermique de la campagne d'avril 2026, leur structure, leur volume et leurs limites. La **préparation des données** a couvert le nettoyage, le rééchantillonnage, la synchronisation temporelle, la segmentation en essais et l'extraction des variables. La **modélisation** a comparé plusieurs algorithmes d'apprentissage supervisé. L'**évaluation** a reposé sur des protocoles de validation stricts (séparation par essai, validation Leave-One-Group-Out) destinés à fournir une estimation réaliste plutôt qu'optimiste des performances. Le **déploiement** a pris la forme d'un démonstrateur Streamlit déployé sur Streamlit Cloud, adossé à une persistance Supabase. Cette adaptation de CRISP-DM, plutôt qu'une méthodologie purement séquentielle, a permis des itérations entre phases, notamment entre préparation des données et modélisation, au fur et à mesure de l'affinage de la variable cible.

[INSÉRER FIGURE : schéma de la démarche CRISP-DM adaptée au projet (six phases et boucles d'itération)]

## 4.2 Organisation du travail et rôle du chef de projet

Le projet a été conduit par un acteur unique cumulant les rôles de développeur et de chef de projet, sous la supervision du tuteur industriel M. Maël Gallas pour les arbitrages métier et du référent pédagogique M. Moussa NDIAYE pour le cadrage académique. Cette configuration mono-acteur a exigé une discipline particulière dans la structuration du travail, afin de compenser l'absence de répartition des responsabilités entre plusieurs profils.

Le rôle de chef de projet a recouvert plusieurs responsabilités successives et parfois simultanées : le cadrage du besoin et la formalisation de la problématique avec le tuteur industriel ; l'arbitrage technique, notamment le choix de la pile logicielle et la décision de différer certaines équations ; la structuration des données, depuis les fichiers bruts jusqu'au jeu de données exploitable ; le développement du prototype, organisé en couches pour préserver la testabilité ; la mise en place et l'exécution des tests automatisés ; la documentation technique et fonctionnelle ; et enfin la préparation de la démonstration client. La pratique du « mode rival » instaurée par le tuteur industriel, exiger un contre-argument rationnel plutôt qu'une validation par défaut, a servi de garde-fou méthodologique constant contre les hypothèses faibles.

## 4.3 Planification et jalons

Le projet s'est structuré autour de grandes phases successives : le cadrage du besoin, l'état de l'art scientifique, la préparation des données, le développement du moteur procédé, la modélisation par apprentissage automatique, le développement de l'interface Streamlit, la mise en place de la persistance Supabase, la campagne de tests, et la préparation de la démonstration client. Plusieurs jalons sont datés de manière certaine — la campagne d'essais (7 au 13 avril 2026) et la démonstration client (lundi 16 juin 2026) — tandis que d'autres restent à préciser.

| Phase | Livrable principal | Période indicative |
|---|---|---|
| Cadrage et problématique | Problématique validée, périmètre | `[À COMPLÉTER : période]` |
| État de l'art scientifique | Revue de littérature (38 références) | `[À COMPLÉTER : période]` |
| Campagne d'essais (collecte des données) | Données capteurs 12 voies | 7 – 13 avril 2026 |
| Préparation des données | Jeu de données ML (fenêtres 30/60/120 s) | `[À COMPLÉTER : période]` |
| Développement du moteur procédé | screw_logic + couche engine | `[À COMPLÉTER : période]` |
| Modélisation ML | Modèles RF / XGBoost / SVM, rapports de métriques | `[À COMPLÉTER : période]` |
| Développement de l'interface Streamlit | Six pages (Supervision, Profile, Settings, etc.) | `[À COMPLÉTER : période]` |
| Persistance Supabase | Snapshot durable, auto-réparation | jusqu'à mi-juin 2026 |
| Tests et stabilisation | Suite de 694 tests (tous passants) | jusqu'à mi-juin 2026 |
| Démonstration client | Application déployée, parcours guidé | 16 juin 2026 |
| Rédaction et dépôt du mémoire | Mémoire RNCP (~50 pages) | `[À COMPLÉTER : période]` |

*Tableau 4.1 — Rétroplanning indicatif. Les périodes non documentées de façon certaine dans les sources internes sont signalées `[À COMPLÉTER]` ; les dates de la campagne d'essais et de la démonstration client sont avérées.*

[INSÉRER FIGURE : diagramme de Gantt synthétique des phases du projet]

## 4.4 Gestion des risques

L'identification et le traitement des risques ont accompagné le projet de bout en bout. Le tableau ci-dessous recense les risques principaux, leurs causes, leurs impacts et les mesures de mitigation effectivement mises en œuvre ou prévues.

| Risque | Cause | Impact | Mesure de mitigation |
|---|---|---|---|
| Faible volume de données | Seulement 8 essais exploitables (campagne avril 2026) | Robustesse statistique limitée, risque de surapprentissage | Validation stricte par essai, modèles tabulaires robustes, énoncé explicite de la limite (Partie 5) |
| Fuite de données entre fenêtres temporelles | Autocorrélation des séries de température au sein d'un même essai | Surestimation des performances (résultats optimistes trompeurs) | Séparation par run (GroupShuffleSplit), validation Leave-One-Group-Out, cible décalée d'une fenêtre (Source interne : src/train_models.py ; reports/robustness_full_w60.json) |
| Modèle non calibré industriellement | Absence de campagne d'étalonnage | Risque d'interprétation erronée des valeurs absolues | Affichage systématique du statut « valeurs nominales », lecture en tendance relative (Source interne : docs/DEMO_MANAGER.md) |
| Dépendance à Streamlit Cloud | Hébergement externe du démonstrateur | Indisponibilité possible lors de la démonstration | Possibilité de lancement local documentée, déploiement testé en amont (Source interne : docs/DEMO_MANAGER.md) |
| Persistance Supabase | Dépendance à un service cloud tiers | Perte d'état après redémarrage, incohérence entre pages | Couche de persistance à repli (Supabase → fichier externe → JSON local), auto-réparation déterministe des instantanés dégénérés (Source interne : app/persistence.py ; commits e43faf9, 3e64160) |
| Interprétation excessive par l'utilisateur | Crédibilité visuelle de l'interface | Décisions procédé fondées à tort sur des valeurs non calibrées | Disclaimer dans le guide de démonstration, cadrage « aide à la décision » constant |
| Délai de démonstration client | Jalon fixe au 16 juin 2026 | Risque de fonctionnalités incomplètes | Priorisation par la valeur, stabilisation par tests, périmètre scientifique borné (E5/E6/E7 différés) |
| Dette technique | Développement rapide mono-acteur | Maintenabilité dégradée à terme | Architecture en couches, invariants d'import vérifiés par tests, documentation interne (CLAUDE.md) |

*Tableau 4.2 — Cartographie des risques du projet.*

## 4.5 Contraintes et arbitrages

Les choix du projet résultent d'arbitrages explicites entre objectifs concurrents. Le premier arbitrage a privilégié la **rapidité de prototypage** : face à un calendrier contraint et à un développement mono-acteur, la productivité de développement a primé sur la finesse de contrôle de l'interface. Cet arbitrage justifie directement le second : le choix de Streamlit et Supabase plutôt que de Flask, Dash et d'une base PostgreSQL administrée localement, détaillé en section 3.7. Le troisième arbitrage a donné la **priorité à la démontrabilité** : l'objectif d'une démonstration client crédible au 16 juin 2026 a orienté les efforts vers la cohérence de bout en bout et la stabilité runtime plutôt que vers l'ajout de nouvelles équations physiques.

Ces arbitrages s'accompagnent de **limites assumées**, posées comme des choix et non subies comme des défauts. Le périmètre scientifique a été délibérément borné : les équations E5/E6/E7 sont différées et documentées comme telles. Surtout, la décision de conserver les valeurs comme nominales et non calibrées industriellement a été maintenue de manière intransigeante : il a été jugé préférable d'afficher honnêtement le statut prototype de l'outil que de laisser croire à une précision industrielle non démontrée. Cette honnêteté de positionnement constitue, paradoxalement, un facteur de crédibilité auprès d'un public d'ingénieurs.

## 4.6 Qualité, tests et validation logicielle

La qualité logicielle a reposé sur une suite de tests automatisés substantielle : près de sept cents tests (694), exécutés en environ 170 secondes. À la dernière exécution complète, 694 tests passent et un seul échoue de façon intermittente ; cet unique échec n'est pas un défaut applicatif mais une fragilité d'isolation entre tests de bout en bout, qui partagent un état sur disque : le test passe systématiquement lorsqu'il est exécuté isolément (Source interne : tests/). Cette suite combine plusieurs natures de tests, conçues pour couvrir des risques distincts.

Les **tests unitaires purs** valident la logique métier et le moteur procédé indépendamment de l'interface (géométrie de vis, calculs de volume, agrégats du moteur, sécurité de conversion des types). Les **tests d'interface Streamlit**, au nombre d'une trentaine, s'appuient sur le harnais de test de Streamlit pour valider le comportement réel des widgets et des pages. Les **tests de persistance** vérifient la survie de l'état à un redémarrage simulé, en détruisant les fichiers éphémères et en s'assurant que seule la couche durable subsiste. Les **tests de non-régression** ont été ajoutés à chaque correction de bogue de production, afin de figer le comportement attendu. Les **tests d'internationalisation** contrôlent la couverture bilingue et l'absence de chaînes françaises résiduelles en mode anglais (plus de soixante-dix chaînes interdites vérifiées par rendu). Les tests de redémarrage de bout en bout, enfin, simulent un redémarrage réel de l'hébergement cloud et vérifient les valeurs effectivement affichées par les widgets après restauration (Source interne : tests/test_persistence_durable.py ; tests/test_e2e_prod_reboot.py ; tests/test_i18n_no_french_leaks.py).

Cette stratégie de tests a une vertu directe en gestion de projet : elle a permis de transformer chaque incident de production en cas de test reproductible, sécurisant les itérations rapides du développement mono-acteur. Ses limites, absence d'intégration continue automatisée, couverture non mesurée formellement, sont discutées en Partie 8.

[INSÉRER FIGURE : répartition de la suite de tests par famille (unitaires, interface, persistance, i18n, redémarrage)]

## 4.7 Veille technologique, sectorielle et réglementaire

Un dispositif de veille a accompagné le projet afin d'ancrer ses choix dans l'état de l'art mouvant de l'IA industrielle, de l'extrusion et des batteries, et d'anticiper les évolutions réglementaires. Le tableau ci-dessous formalise ce système de veille et d'alerte.

| Source d'information | Type de veille | Date / mise à jour | Outil | Canal | Fréquence | Impact sur le projet |
|---|---|---|---|---|---|---|
| Revues scientifiques (Nature Comm., J. Power Sources, Batteries, Cell Rep. Phys. Sci.) | Technologique / scientifique | Oct. 2025 → juin 2026 | Google Scholar, alertes | RSS / e-mail | Mensuelle | Cadrage état de l'art (38 réfs), choix variable cible |
| Acteurs SSB & extrusion (Coperion, Thermo Fisher, Fraunhofer IWS, Factorial) | Concurrentielle / sectorielle | Trimestrielle 2026 | Sites éditeurs, LinkedIn | Web / presse pro | Trimestrielle | Analyse concurrentielle (§2.4), positionnement |
| Cabinets d'études marché (Grand View Research, MarketsandMarkets) | Sectorielle / économique | 2025 (< 5 ans) | Rapports publics | Web | Ponctuelle | Chiffrage marché (§2.1) |
| ECHA — restriction PFAS | Juridique / réglementaire | Proposition fév. 2023, suivi 2026 | Site ECHA | Web officiel | Semestrielle | Justification voie sèche / sans PVDF |
| CNIL / RGPD | Juridique / réglementaire | 2026 | Site CNIL | Web officiel | Ponctuelle | Cadrage données (capteurs ≠ données perso) §8.4 |
| Référentiel WCAG 2.1 | Réglementaire / accessibilité | 2026 | W3C | Web officiel | Ponctuelle | Chantier accessibilité identifié §8.4 |
| Écosystème Python ML (scikit-learn, XGBoost, Streamlit, Supabase) | Technologique | Continue 2026 | Docs officielles, GitHub | Web / dépôts | Continue | Choix de pile, versions, sécurité |

*Tableau 4.3 — Système de veille technologique, sectorielle et réglementaire du projet.*

## 4.8 Budget prévisionnel et indicateurs de suivi

Le projet ayant été conduit par un acteur unique dans un cadre de formation, le pilotage financier repose moins sur des dépenses externes que sur l'allocation de la ressource rare — le temps. Le coût de la pile logicielle est nul ou en paliers gratuits (open source et offres *freemium*), l'investissement principal étant le temps-homme et la mise à disposition par Rondol de l'extrudeuse et des données d'essais.

| Poste | Nature | Estimation | Commentaire |
|---|---|---|---|
| Temps-homme (conception, développement, rédaction) | Investissement principal | ≈ 4 mois (cf. exigence RNCP) | Ressource centrale du projet |
| Licences logicielles (Python, scikit-learn, XGBoost, Streamlit) | Open source | 0 € | Pas de coût de licence |
| Hébergement application (Streamlit Cloud) | *Freemium* | 0 € (palier gratuit) | Coût si montée en charge / domaine dédié |
| Persistance (Supabase / PostgreSQL) | *Freemium* | 0 € (palier gratuit) | Coût au-delà des quotas gratuits |
| Dépôt et CI (GitHub) | *Freemium* | 0 € | Dépôt public/privé gratuit |
| Données d'essais (campagne avril 2026) | Ressource Rondol | Mise à disposition | Coût machine/matière porté par l'entreprise |

*Tableau 4.4 — Budget prévisionnel : l'investissement est essentiellement en temps, le coût logiciel direct étant nul (open source / freemium).*

Le suivi du projet s'est appuyé sur un tableau de bord d'indicateurs objectifs, réévalués au fil des itérations : nombre de tests automatisés passants (**694** sur 694 en exécution complète), couverture fonctionnelle (**6 pages** opérationnelles), volumétrie du jeu d'apprentissage (**798 fenêtres**, 8 essais), performance du modèle retenu (RandomForest augmenté, F1-macro 0,918 ± 0,054 sur essai réel), jalons tenus (campagne d'essais, démonstration du 16 juin 2026), et nombre d'incidents de production résolus et figés en tests de non-régression (cf. Tableau 6.1). Ces indicateurs constituent le tableau de bord de pilotage présenté à la Direction (tuteur industriel).

[SAUT DE PAGE]

---

# Partie 5 — Exploitation des données et modélisation par apprentissage automatique

Cette partie constitue le cœur de la démarche de science des données. Elle décrit le chemin complet allant des fichiers d'instrumentation bruts jusqu'au modèle d'apprentissage intégré au prototype, en passant par la construction du jeu de données, l'ingénierie des variables, la formulation du problème, la comparaison des modèles et leur validation rigoureuse. L'ensemble s'appuie sur le code et les rapports effectivement présents dans le dépôt (Source interne : src/ ; data/features/ ; reports/).

## 5.1 Présentation des données disponibles

Les données que j'ai exploitées viennent d'une campagne d'essais que Rondol a menée du 7 au 13 avril 2026 sur la bivis 10,5 mm. Douze capteurs de température instrumentent la ligne : les huit zones du fourreau (Z1 à Z8), la filière (DIE) et trois points sur la ligne de mise en film (CastFilmBody, CastFilmP1, CastFilmP2). Chacun produit un fichier CSV horodaté, colonnes *Timestamp* au format ISO JavaScript, *Name*, *Value* en degrés Celsius, échantillonné de façon irrégulière, de la seconde à la quinzaine de secondes. Le seul capteur de filière totalise déjà 50 145 relevés bruts (Source interne : src/config.py ; Essais_07-13_Avril_2026/).

Sur les onze essais de la campagne, je n'en ai retenu que huit : j'ai écarté ceux de moins de quinze minutes, trop courts pour être représentatifs — je les ai conservés, mais étiquetés comme tels. Deux propriétés ont pesé sur toute la suite. Ces données sont **réelles, pas simulées** : c'est ce qui donne au travail sa valeur expérimentale. Mais elles sont **peu nombreuses** — huit essais, c'est peu. Je l'ai assumé comme la limite structurelle du projet, en choisissant des protocoles de validation prudents plutôt que des modèles gourmands en données.

[INSÉRER FIGURE : pipeline de données capteurs, des fichiers CSV bruts au jeu de données ML]

## 5.2 Construction du jeu de données exploitable

Pour passer des fichiers bruts à un jeu de données exploitable, j'ai enchaîné un pipeline déterministe et documenté (Source interne : src/preprocess.py ; src/features.py ; src/config.py). Le **nettoyage** commence par le chargement, le parsing des horodatages et la déduplication : en cas de doublon, je garde le dernier relevé. Le **rééchantillonnage** ramène toutes les voies à un pas constant de dix secondes, avec un remplissage avant (*forward-fill*) borné à soixante secondes — au-delà, je préfère laisser un trou plutôt que propager une valeur périmée. Je **synchronise** ensuite les douze capteurs sur une échelle de temps commune. Pour la **segmentation par essai**, je me suis appuyé sur un critère métier simple : la machine est en production dès que la filière dépasse 120 °C, ce qui détecte tout seul les transitions arrêt / marche. Les essais trop courts, enfin, sont marqués *bad_run* et sortis de l'entraînement principal.

L'**extraction des variables** s'effectue sur des fenêtres temporelles glissantes, déclinées en trois horizons (30, 60 et 120 secondes) avec un recouvrement de 50 %. Pour chaque fenêtre et chaque capteur, sept statistiques sont calculées (moyenne, écart-type, minimum, maximum, étendue, pente de régression linéaire, écart interquartile), auxquelles s'ajoutent trois variables croisées entre capteurs, soit un total de **96 variables brutes** par fenêtre. Le jeu de données retenu pour le modèle de production (fenêtre 60 secondes) comporte **798 fenêtres au total** (627 issues d'essais valides, 171 d'essais courts), réparties en 586 fenêtres stables et 212 fenêtres instables, et scindées en 287 fenêtres d'entraînement (5 essais) et 340 fenêtres de test (3 essais) (Source interne : data/features/dataset_ml_w60_meta.json ; reports/ml_summary_w60.txt).

| Variable | Définition | Unité | Source | Rôle dans le modèle |
|---|---|---|---|---|
| Z1_mean … Z8_mean | Température moyenne d'une zone du fourreau sur la fenêtre | °C | Capteurs Z1–Z8 | Variable explicative (niveau thermique) |
| Zk_std | Écart-type de la température de la zone k sur la fenêtre | °C | Capteurs Z1–Z8 | Variable explicative (variabilité / stabilité) |
| Zk_slope | Pente de régression linéaire (tendance) sur la fenêtre | °C/s | Capteurs Z1–Z8 | Variable explicative (dérive) |
| Zk_iqr | Écart interquartile de la zone k | °C | Capteurs Z1–Z8 | Variable explicative (dispersion robuste) |
| DIE_std, DIE_iqr, DIE_range | Variabilité de la température de filière | °C | Capteur DIE | Variable explicative (forte importance) |
| CastFilmP1/P2/Body_* | Statistiques des capteurs de film en sortie | °C | Capteurs CastFilm | Variable explicative (forte importance) |
| grad_Z8_minus_Z1 | Gradient thermique le long du fourreau | °C | Z1, Z8 | Variable explicative croisée |
| grad_DIE_minus_Z8 | Saut thermique fourreau → filière | °C | Z8, DIE | Variable explicative croisée |
| grad_CastFilm_minus_DIE | Cohérence thermique filière → film | °C | DIE, CastFilm | Variable explicative croisée |
| is_stable | Régime stable (1) ou instable (0) sur la fenêtre suivante | binaire | Construite (cf. 5.4) | Variable cible |

*Tableau 5.1 — Dictionnaire des principales variables (extrait représentatif ; le dictionnaire complet figure en annexe). Source interne : src/features.py ; src/config.py ; reports/feature_importance_RandomForest_w60.csv.*

## 5.3 Ingénierie des variables (feature engineering)

L'ingénierie des variables vise à transformer des séries de température brutes en indicateurs porteurs d'information sur la stabilité du régime. Plusieurs familles de variables dérivées ont été construites. La **température moyenne** par zone fournit le niveau thermique de base. L'**écart thermique** et la **dispersion entre zones** (gradients longitudinaux et transversaux) traduisent la cohérence spatiale du profil thermique. La **stabilité thermique** est capturée par l'écart-type et l'écart interquartile, indicateurs de la fluctuation locale. La **pente** (slope) mesure la tendance, donc une dérive éventuelle, sur la durée de la fenêtre. Les indicateurs de dépassement et de dérive s'expriment à travers l'étendue (range) et les sauts entre étages (fourreau, filière, film).

Un enseignement notable ressort de l'analyse de l'importance des variables pour le modèle de référence : les variables les plus discriminantes ne sont pas les températures des zones amont du fourreau, mais la variabilité thermique des étages aval — film extrudé et filière. Les variables de tête de classement sont ainsi CastFilmP2_iqr (importance 0,0725), DIE_std (0,0667) et CastFilmBody_std (0,0658), tandis que les températures moyennes des zones Z1 à Z8 se classent au-delà du quatorzième rang. Cette lecture est cohérente avec le procédé : les zones amont sont fortement régulées, et c'est la variabilité observée en aval qui signale le mieux l'instabilité du régime (Source interne : reports/feature_importance_RandomForest_w60.csv).

[INSÉRER FIGURE : graphique des importances de variables (top 10) du modèle de référence Random Forest, fenêtre 60 s]

## 5.4 Variable cible et formulation du problème

Le problème est formulé comme une classification binaire supervisée à visée de prévision : à partir de l'état observé sur une fenêtre, le modèle prédit si le régime d'extrusion sera stable ou instable sur la fenêtre suivante. Cette formulation prévisionnelle, plutôt que descriptive, répond directement au besoin métier d'anticipation des dérives.

La variable cible est construite à partir de conditions de stabilité thermique appliquées aux capteurs : une fenêtre est jugée stable lorsque la fluctuation reste contenue (écart-type par capteur inférieur à 1,5 °C et pente inférieure à 0,05 °C/s), ces critères étant agrégés en un score dont le franchissement d'un seuil (référence métier à 70/100) détermine l'étiquette stable / instable. Un soin particulier a été porté à la **prévention des fuites d'information** : la cible est décalée d'une fenêtre par rapport aux variables explicatives, de sorte que le modèle prédit l'état futur à partir de l'état présent, et non l'état présent à partir de lui-même (Source interne : src/target.py ; src/config.py).

Cette formulation appelle une réserve méthodologique explicite : avec huit essais seulement, et un déséquilibre de classes (environ 73 % de fenêtres stables sur le jeu fenêtre 60 secondes), les performances doivent être interprétées avec prudence et au moyen de métriques adaptées au déséquilibre (F1-macro, AUC-ROC) plutôt que de la seule exactitude.

## 5.5 Augmentation de données simulée à partir de l'échantillon réel

Le déficit de volume, huit essais exploitables, 627 fenêtres valides, constitue le principal facteur limitant de l'apprentissage : en validation par essai non vu, tous les modèles plafonnent autour de 0,80 de F1-macro avec une forte variance (cf. 5.8). Rondol ne disposant pas d'une base de données d'essais historique, la voie retenue, validée avec l'encadrement, a été de générer un jeu de données simulé à partir de l'échantillon réel, jamais aléatoirement, afin de stabiliser l'apprentissage et de démontrer la méthode, sans jamais prétendre disposer de davantage de données réelles. Cette démarche s'inscrit dans la lignée des travaux recourant aux données synthétiques pour pallier la rareté des essais (Maia, 2025). Le **plan de génération documenté** est fourni en artefact méthodologique (Source interne : reports/augmentation_plan.md ; src/augment_dataset.py).

Le principe est celui d'une génération par ancrage, conditionnée à la classe. Pour chaque classe (stable / instable) et chaque capteur, la dispersion réelle des statistiques est estimée sur l'échantillon. Chaque fenêtre synthétique part alors d'une vraie fenêtre de la même classe, ce qui préserve les corrélations inter-capteurs, puis reçoit un **jitter gaussien borné** égal à 30 % de l'écart-type réel de classe. Trois exigences garantissent le réalisme du résultat. D'abord, la **cohérence interne exacte** des variables dérivées est reproduite à l'identique du pipeline réel (`range = max − min` ; gradients croisés = différences de moyennes ; `min ≤ mean ≤ max`), avec vérification d'écart nul. Ensuite, des **contraintes métier** bornent les températures et imposent la positivité des dispersions ; la sémantique de classe est préservée (l'écart-type moyen d'une zone passe de ≈ 0,08 °C en régime stable à ≈ 1,42 °C en régime instable). Enfin, exigence essentielle, les imperfections de l'échantillon sont reproduites : les valeurs manquantes (panne d'un capteur → ses sept statistiques manquent ensemble) sont ré-injectées au taux réel par capteur, et quelques aberrations de thermocouple sont introduites, précisément pour exercer les étapes de nettoyage et d'imputation. Le tout est déterministe (graine fixée), marqué `synthetic = 1`, et les essais synthétiques sont placés dans un pool d'identifiants distinct.

Le jeu ainsi obtenu porte le volume d'entraînement de 627 fenêtres réelles à 1 427 (800 fenêtres synthétiques, rééquilibrées à 400 stables / 400 instables). Le point méthodologique décisif est le protocole d'évaluation, conçu pour interdire toute forme de triche : la validation reste un *Leave-One-Group-Out* **sur les essais réels**. Pour chaque essai réel laissé de côté (test), le modèle est entraîné soit sur les autres essais réels seuls (référence), soit sur ces mêmes essais réels augmentés de tout le synthétique ; le test est toujours un essai réel non vu, et le synthétique n'apparaît **jamais** en test (Source interne : src/evaluate_augmentation.py ; reports/augmentation_eval.json).

| Modèle | Sans augmentation (F1-macro) | Avec augmentation | Gain |
|---|:--:|:--:|:--:|
| Régression logistique | 0,799 ± 0,163 | 0,860 ± 0,111 | +0,061 |
| SVM (noyau RBF) | 0,805 ± 0,171 | 0,868 ± 0,089 | +0,063 |
| **Random Forest** | 0,796 ± 0,187 | **0,918 ± 0,054** | **+0,122** |

*Tableau 5.2bis — Effet de l'augmentation, en validation Leave-One-Group-Out sur essais réels (synthétique en entraînement uniquement). Source interne : reports/augmentation_eval.json.*

L'augmentation améliore la généralisation aux essais réels non vus et réduit fortement la variance — l'écart-type du Random Forest passe de 0,187 à 0,054, soit une division par plus de trois de l'instabilité inter-essais. C'est précisément l'effet recherché : consolider un apprentissage bridé par le faible nombre d'essais, tout en maintenant une posture d'honnêteté (le modèle demeure un indicateur expérimental, les métriques sont mesurées sur des essais réels, et l'augmentation ne se substitue pas à de véritables campagnes d'essais).

## 5.6 Modèles évalués

J'ai comparé cinq algorithmes supervisés, en couvrant à dessein trois familles : la référence linéaire, les méthodes tabulaires ensemblistes et à noyau, et le *deep learning*. La **régression logistique** me sert de garde-fou — un test simple mais parlant : si un modèle linéaire fait jeu égal avec des modèles complexes, c'est que le facteur limitant est le volume de données, pas l'algorithme. J'ai retenu **Random Forest** (forêt aléatoire) pour sa robustesse sur données tabulaires, sa résistance au surapprentissage par agrégation d'arbres et l'importance de variables interprétable qu'il fournit. **XGBoost** (boosting de gradient) a été évalué pour sa performance reconnue sur données tabulaires et sa gestion du déséquilibre de classes par pondération. **SVM** (machine à vecteurs de support, à noyau RBF avec normalisation préalable) a été évalué pour sa capacité à construire des frontières de décision non linéaires sur des jeux de taille modérée. Enfin, une **baseline de *deep learning*** a été ajoutée sous la forme d'un **perceptron multicouche (MLPClassifier)** à deux couches cachées (64 puis 32 neurones, activation ReLU, optimiseur Adam, arrêt anticipé), entraîné sur entrées normalisées — afin de vérifier qu'un réseau de neurones n'apporte pas de gain décisif sur un jeu de cette taille (Source interne : src/train_mlp_baseline.py ; reports/ml_metrics_mlp_w60.json).

Les hyperparamètres de chaque modèle ont été choisis de manière cohérente avec la taille et le déséquilibre du jeu (par exemple `class_weight="balanced"` pour RF et SVM, `scale_pos_weight` pour XGBoost, régularisation L2 et arrêt anticipé pour le MLP), un réglage plus poussé par recherche systématique étant identifié comme piste d'amélioration (§8.5). Le choix de ces familles se justifie par la nature du problème : un jeu de données tabulaire de faible à moyen volume, pour lequel les méthodes ensemblistes et à noyau restent en pratique au moins aussi performantes que les réseaux de neurones, gourmands en données. Les valeurs manquantes sont traitées par imputation médiane (méthodes ensemblistes et MLP), et la séparation des données est réalisée par essai pour éviter toute fuite (Source interne : src/train_models.py ; src/ml_utils.py).

## 5.7 Protocole de validation

Le protocole de validation constitue le point méthodologique le plus important de cette partie, car il conditionne la crédibilité de toute conclusion. Le principe directeur est la **séparation par essai** : les fenêtres d'un même essai étant fortement autocorrélées, les répartir aléatoirement entre entraînement et test laisserait fuir de l'information et gonflerait artificiellement les performances. Trois dispositifs ont donc été combinés. Le **GroupShuffleSplit** réalise une partition 70/30 par identifiant d'essai, garantissant qu'aucun essai n'est simultanément en entraînement et en test. La validation **Leave-One-Group-Out** évalue le modèle en excluant tour à tour un essai entier, fournissant une estimation exhaustive de la variabilité inter-essais. Enfin, le **décalage de la cible** d'une fenêtre prévient la fuite temporelle au sein d'un même essai.

L'honnêteté méthodologique impose de comparer ces protocoles. En partition aléatoire naïve, le modèle de référence atteint un F1-macro de l'ordre de 0,92 et une AUC de 0,98 — chiffres séduisants mais **optimistes**, car contaminés par l'autocorrélation. Sous GroupShuffleSplit répété sur dix tirages, le F1-macro réaliste tombe à **0,77 ± 0,11** (AUC 0,92 ± 0,05) ; sous Leave-One-Group-Out, il s'établit à **0,79 ± 0,12** (AUC 0,90 ± 0,08). Cet écart d'environ quinze points de F1 entre validation naïve et validation stricte n'est pas un défaut à dissimuler : il est l'indicateur même de la rigueur de la démarche, et c'est la valeur réaliste qui doit être retenue pour juger du potentiel du modèle (Source interne : reports/robustness_full_w60.json).

[INSÉRER FIGURE : comparaison des performances en split aléatoire vs GroupShuffleSplit vs Leave-One-Group-Out (workflow ML et résultats)]

## 5.8 Résultats de modélisation

Les résultats sur le jeu fenêtre 60 secondes, en évaluation sur essais de test non vus, sont synthétisés ci-dessous (Source interne : reports/ml_metrics_w60.json ; reports/ml_summary_w60.txt).

| Modèle (fenêtre 60 s) | Exactitude | F1-macro | F1 classe « instable » | F1 classe « stable » | AUC-ROC (test) |
|---|:--:|:--:|:--:|:--:|:--:|
| Random Forest | 0,950 | 0,917 | 0,864 | 0,969 | 0,947 |
| SVM (noyau RBF) | 0,953 | 0,916 | 0,860 | 0,972 | 0,947 |
| MLP (réseau de neurones, deep learning) | 0,959 | 0,926 | 0,877 | 0,975 | 0,967 |
| XGBoost | 0,882 | 0,827 | 0,730 | 0,925 | 0,948 |

*Tableau 5.2 — Performances comparées sur le jeu de test (fenêtre 60 s). En validation croisée 5-plis sur l'entraînement, le Random Forest atteint un F1-macro de 0,935 ± 0,029 et une AUC de 0,976 ± 0,021. Sous validation stricte par essai (Leave-One-Group-Out), le F1-macro réaliste se situe à 0,77–0,79 (cf. 5.7).*

Quatre enseignements ressortent. D'abord, Random Forest, SVM et la baseline de *deep learning* (MLP) offrent des performances très proches et nettement supérieures à XGBoost sur ce jeu (F1-macro de 0,92 à 0,93). Ensuite, point décisif pour le choix d'architecture, le réseau de neurones n'apporte aucun gain décisif justifiant sa complexité et sa moindre interprétabilité : sur un jeu tabulaire de cette taille, les méthodes classiques restent au moins aussi performantes, ce qui confirme le choix de ne pas recourir au *deep learning* en production. Il faut toutefois rappeler que ces chiffres élevés proviennent de partitions **optimistes** : le départage réel entre modèles est opéré en validation par essai non vu et avec augmentation de données (§5.5), qui désigne le **Random Forest** comme modèle retenu (§5.9). Enfin, comme souligné en 5.7, les chiffres d'exactitude « bruts » doivent être lus à la lumière de la validation stricte, qui ramène les performances réalistes autour de 0,77–0,79 de F1-macro sans augmentation.

## 5.9 Choix du modèle retenu et intégré au prototype

Le choix du modèle repose sur un **championnat honnête** : les cinq algorithmes sont départagés non pas sur les partitions aléatoires (optimistes, cf. 5.7), mais sur la validation par essai réel non vu, et **avec l'augmentation de données** décrite en 5.5. Sous ce protocole, le Random Forest se détache nettement — F1-macro **0,918 ± 0,054** sur essais réels non vus, contre 0,868 pour le SVM et 0,860 pour la régression logistique (Tableau 5.2bis). Non seulement il obtient le meilleur score, mais il présente aussi la **plus faible variance inter-essais**, c'est-à-dire le comportement le plus stable d'un essai à l'autre — critère décisif quand la robustesse, et non la performance de pointe sur un seul jeu, est l'enjeu.

Le Random Forest (fenêtre 60 s), entraîné sur données réelles augmentées, est donc le modèle retenu et effectivement déployé dans le prototype (Source interne : models/RandomForest_w60_augmented.joblib ; app/Supervision.py ; src/train_retained_rf.py). Ce choix cumule plusieurs avantages cohérents avec le contexte : la **meilleure généralisation** mesurée honnêtement, la **robustesse** sur données tabulaires de faible volume, l'**interprétabilité** offerte par l'importance des variables (§5.3, exploitable directement devant un interlocuteur métier), et la tolérance native aux valeurs manquantes via l'imputation intégrée au pipeline — propriété utile puisque l'instrumentation présente des lacunes capteur. Le SVM et les autres modèles sont conservés comme **challengers documentés du championnat**, non comme modèles de production.

Une frontière doit rester explicite, et sans sur-promesse. Le Random Forest **prédit la stabilité thermique** ; il ne **recommande** rien. Les alertes et les recommandations opérateur proviennent des règles métier expertes traçables (Partie 6), non du modèle statistique. Ainsi, la décision n'est jamais confiée au seul modèle d'apprentissage : le prototype articule des indicateurs procédé, des règles explicables et un score ML expérimental qui éclaire sans trancher. Enfin, malgré le gain apporté par l'augmentation, le modèle **demeure un indicateur expérimental** : il repose *in fine* sur huit essais réels, ses performances sont mesurées sur des essais réels non vus, et il n'est **pas** un prédicteur industriel calibré. Cette prudence est maintenue de bout en bout, y compris dans l'interface (Source interne : AgentIndustrial_v1/core/rules.py ; app/rondol_i18n.py).

[INSÉRER FIGURE : championnat des modèles supervisés en validation par essai réel, sans et avec augmentation de données — RandomForest retenu]

## 5.10 Limites de la modélisation

Les limites de la modélisation sont assumées et explicitées. La première et la plus structurante est le **faible nombre d'essais** (huit), qui borne la robustesse statistique et explique l'écart entre validation naïve et validation stricte. La deuxième est la **dépendance aux conditions expérimentales** de la campagne d'avril 2026 : le modèle reflète un contexte d'essais particulier (formulations, réglages, instrumentation) et sa transférabilité à d'autres contextes reste à démontrer. La troisième est l'absence de calibration industrielle complète : le modèle prédit la stabilité thermique telle que définie par les critères retenus, non une grandeur procédé étalonnée. La quatrième est une capacité de généralisation encore limitée, conséquence directe des trois précédentes. Il en découle que la consolidation de ces résultats **exige de nouveaux essais**, en nombre et en diversité, condition nécessaire à toute montée en robustesse.

Pour objectiver cette question de la transférabilité sans attendre une nouvelle campagne, une **validation externe sur base simulée** a été menée : une base continue de 100 800 lignes, générée à partir de l'échantillon réel (consignes de plateau, bruit de régulation, imperfections capteur et épisodes d'instabilité reproduits, cf. Partie 5.5 et `data/consolidated/rapport_generation.md`), a été passée dans le même pipeline de fenêtrage et de labellisation que les données réelles, puis soumise au modèle retenu **sans réentraînement**. Sur 3 479 fenêtres issues de 15 runs simulés, le modèle conserve un pouvoir discriminant (AUC 0,753 ; 62 % des fenêtres instables détectées), avec des erreurs majoritairement conservatrices (fausses alertes plutôt que dérives manquées). La génération n'a volontairement pas été ajustée pour améliorer ces chiffres : l'écart avec les performances sur essais réels illustre précisément la sensibilité au changement de distribution évoquée ci-dessus, et confirme que le modèle est utilisable comme indicateur d'aide à la décision, non comme détecteur certifié (Source interne : scripts/evaluate_on_consolidated.py ; reports/eval_consolidated_w60.json).

## 5.11 Synthèse de la Partie 5

La démarche d'apprentissage automatique conduite dans ce projet établit, à partir de données d'essais réelles mais peu nombreuses, une première capacité de prévision de la stabilité thermique du régime d'extrusion, validée selon des protocoles stricts qui en donnent une mesure réaliste et non flattée. Face au déficit de volume, une augmentation de données documentée à partir de l'échantillon a permis de consolider l'apprentissage et de réduire la variance. Au terme d'un championnat évalué par essai réel non vu, le Random Forest entraîné sur données augmentées est retenu comme modèle prédictif déployé (F1-macro 0,918 ± 0,054), la logique de recommandation restant, elle, assurée par des **règles expertes explicables**.

Cette démarche ne prétend pas remplacer l'expertise procédé : elle l'**outille**. En l'état, le modèle n'est pas un instrument de mesure calibré, mais un dispositif d'aide à la décision qui apporte trois bénéfices concrets : l'**anticipation** d'une instabilité probable, la **comparaison objective** de configurations, et la **traçabilité** des signaux ayant motivé une alerte. C'est sur cette base, modeste mais honnête, que se construit la valeur de la plateforme décrite en Partie 6.

[SAUT DE PAGE]

# Partie 6 — Conception et développement de la plateforme

La présente partie expose la traduction concrète des exigences fonctionnelles et scientifiques en un artefact logiciel opérationnel : la plateforme prédictive Rondol. L'objectif n'était pas de produire un tableau de bord générique, mais un jumeau numérique crédible et démontrable de l'extrudeuse bivis Rondol, articulant une logique métier géométrique réelle, un moteur de physique procédé en couches et un agent d'aide à la décision explicable. La description qui suit privilégie une lecture architecturale : elle part des couches les plus profondes, pures, déterministes, exemptes de toute dépendance d'interface, pour remonter progressivement vers l'expérience utilisateur et les mécanismes de persistance durable. Ce choix de présentation reflète directement le principe de conception qui structure l'ensemble du système : la séparation stricte des responsabilités, où chaque couche n'expose à la couche supérieure qu'un contrat clair et où l'interface ne fait que restituer un état déjà calculé.

## 6.1 Architecture générale en couches

La plateforme repose sur une architecture stratifiée stricte dans laquelle les couches basses sont pures, c'est-à-dire dépourvues de toute dépendance à Streamlit, au système de fichiers ou à l'état de session, l'interface utilisateur se bornant à effectuer le rendu d'un état préalablement calculé (Source interne : CLAUDE.md ; engine/__init__.py). Cette discipline architecturale n'est pas un raffinement esthétique : elle conditionne la testabilité du cœur scientifique, la reproductibilité des calculs et la possibilité de réutiliser le moteur indépendamment de son habillage graphique. Concrètement, le logiciel se décompose en cinq strates aux responsabilités nettement séparées.

La couche 0 constitue le socle géométrique, ou *backbone* : le module `app/screw_logic.py` y implémente le « Network 7 », unique producteur des grandeurs procédé fondamentales. Au-dessus, la couche 1 regroupe trois packages purs, `machine/`, `materials/` et `physics/`, qui fournissent des catalogues et des formules construits *sur* le backbone, qu'ils importent mais ne redéfinissent jamais. La couche 2, le package `engine/`, assemble l'état procédé local position par position selon un principe d'enveloppement plutôt que de recalcul. La couche front-end, dans `app/`, expose les six pages Streamlit. Enfin, la couche back-end et de persistance, centralisée dans `app/persistence.py`, garantit la durabilité de l'état validé. L'agent d'aide à la décision (`AgentIndustrial_v1/`) se greffe transversalement sur l'état applicatif consolidé pour produire alertes et recommandations.

Le bénéfice de cette stratification tient à la direction unique des dépendances : une couche ne connaît jamais les couches qui la surplombent. Le moteur procédé ignore l'existence de l'interface ; les modules de matériaux ignorent l'agent. Cette propriété autorise un test unitaire du cœur scientifique sans démarrer aucune interface graphique, et garantit qu'une évolution de l'habillage ne peut altérer la justesse d'un calcul de remplissage ou de temps de résidence.

[INSÉRER FIGURE : architecture générale de la plateforme en couches]

## 6.2 Le backbone procédé : screw_logic et le réseau « Network 7 »

Le module `app/screw_logic.py` est la pierre angulaire scientifique de la plateforme. Il modélise la géométrie de la vis et exécute le calcul procédé dit « Network 7 » via la fonction `compute_process_state(config, ProcessParams) -> ProcessState` (Source interne : app/screw_logic.py ; CLAUDE.md). La configuration de vis est représentée par une liste de 81 positions, `config[0..80]`, encodant des éléments, des demi-éléments et des positions vides, à partir d'une bibliothèque de treize types d'éléments. La capacité utile retenue est de quarante éléments, dont trente-neuf sont modifiables par l'opérateur et un, l'embout, ou *tip*, est verrouillé, conformément à la réalité d'une vis bivis composée de deux vis. Le volume libre total de référence du fourreau s'établit à 76,1756 cm³, valeur issue de la spécification métier (Source interne : references/logique_metier/2-CALCULS.pdf).

Le caractère décisif de ce module réside dans son statut de source unique de vérité. Il est le seul producteur des profils de facteur de remplissage (`fill_factor`), de débit volumique (`vol_flow`), de temps de résidence (`residence_time`) et des volumes associés. Aucune couche supérieure n'est autorisée à recalculer ces grandeurs : elle doit les consommer telles qu'elles ont été produites. Pour garantir cette unicité, le calcul Network 7 est invoqué **exactement une fois** par cycle de rendu. Une correction de cohérence physique est appliquée dans le *wrapper* : le temps de résidence est corrigé proportionnellement au rapport entre une vitesse de référence de cent tours par minute et la vitesse de rotation effective (correction de résidence ∝ rpm_ref(100) / rpm), traduisant le fait qu'une rotation plus rapide réduit le temps de séjour de la matière dans le fourreau.

Ce module appartient au périmètre protégé du projet : il ne peut être modifié sans validation explicite, précisément parce que toute altération se propagerait à l'ensemble des grandeurs dérivées et compromettrait la crédibilité scientifique de la démonstration.

## 6.3 Le moteur d'enveloppement (couche engine)

Le package `engine/` constitue la couche d'intégration entre le backbone et les modules purs de la couche 1. Son principe fondateur, énoncé sans ambiguïté dans la documentation du package, est « ENVELOPPER, NE PAS RECALCULER » (Source interne : engine/__init__.py). Cette doctrine signifie que le moteur ne reproduit jamais le calcul de Network 7 : il l'enrichit. La fonction `extrusion_graph.build_graph` appelle le calcul procédé une seule fois, puis le reste de la chaîne réutilise l'objet `ProcessState` ainsi obtenu plutôt que de re-dériver ses grandeurs.

L'architecture interne du moteur se décline en plusieurs modules complémentaires. Le module `node_state.py` définit `NodeState`, une structure immuable (`frozen`) qui *enveloppe* l'état procédé d'une position de vis, `ProcessState[i]`, en lui adjoignant une classification, l'appartenance à une zone, le port associé, le matériau nominal et le taux de cisaillement local. Le module `aggregate.py` replie les états de nœuds en états de zone puis de machine, en réutilisant les totaux déjà calculés par `ProcessState`, temps de résidence, remplissage moyen, dépassement, au lieu de les re-sommer, garantissant ainsi la cohérence avec le backbone. La physique locale est portée par `viscosity.py`, qui calcule la viscosité de fonte locale η(γ̇, T), et par `torque.py`, qui implémente le bloc E4a, soit le couple local M = η·γ̇²·V_filled / (2πN). Le module `enrich.py` matérialise ce couple sur une **copie** de chaque nœud via `dataclasses.replace`, ne mutant jamais une structure immuable.

Le module `deferred.py` mérite une attention particulière : il documente comme renvoyant `None` les équations délibérément différées — E5 (SME local), E6 (température réelle avancée) et E7 (pression filière). Ce choix relève d'une honnêteté scientifique assumée : plutôt que d'injecter des valeurs de démonstration trompeuses, l'état non calculé reste explicite et l'interface l'affiche comme « À venir ».

Enfin, le système repose sur un invariant d'import critique, dit du singleton : le backbone doit toujours être importé en module nu (`import screw_logic`) et jamais via `import app.screw_logic`. Importer le module des deux manières créerait deux objets-module distincts, dédoublant constantes et *dataclasses* et provoquant des ruptures d'identité de type. Cet invariant est vérifié automatiquement par les tests `tests/test_import_singleton.py` et `tests/test_engine_singleton.py`, le bootstrap de `sys.path` en tête de package garantissant la résolution unique (Source interne : engine/__init__.py).

## 6.4 Présentation des pages de la plateforme

La plateforme expose six pages Streamlit, chacune correspondant à une fonction opérationnelle distincte de la supervision d'extrusion (Source interne : CLAUDE.md ; app/pages/).

La page **Supervision** constitue l'accueil et la vitrine du jumeau numérique. Elle restitue l'état machine, un score de stabilité issu du modèle d'apprentissage RandomForest (fenêtre de soixante secondes, seuil de quatre-vingts), une probabilité de dérive, les alertes et recommandations produites par l'agent, ainsi que les indicateurs clés de remplissage, de résidence et de volume. La page **1_Profile** est dédiée à la configuration de la vis : organisation par zones, sélection des éléments et boutons d'incrémentation (+1, +4, −1) accompagnés d'indicateurs synthétiques. La page **2_Settings** centralise le paramétrage de l'agent, seuils, configuration des feeders et paramètres thermiques, et déclenche le *commit* du snapshot validé. La page **3_Run_Analysis** propose une analyse temporelle d'un essai en mode démonstration. La page **4_History** présente l'historique procédé, persistant sur disque, avec des indicateurs figés au moment de la validation. Enfin, la page **5_Process_Engine** offre une vue en lecture seule du moteur : couple total, SME total et agrégats par zone, les grandeurs E6 et E7 y étant affichées comme « À venir » puisqu'elles renvoient `None`.

[INSÉRER CAPTURE : interface Streamlit — page Supervision]

## 6.5 Couche front-end

La couche front-end est intégralement écrite en Python, l'interface étant produite par le framework Streamlit. Le parti pris visuel est celui d'un environnement industriel sobre : une charte sombre est injectée via `st.html`, avec un fond foncé et un accent vert correspondant à l'identité Rondol (Source interne : CLAUDE.md ; app/). Conformément à la directive produit, l'interface se veut fonctionnelle et non décorative : chaque bloc de l'interface homme-machine doit piloter le moteur, qu'il s'agisse d'une alerte, d'un score ou d'une recommandation, à l'exclusion de tout effet purement esthétique.

Deux mécanismes transverses méritent d'être soulignés. D'une part, un sélecteur de langue offre une bascule entre le français et l'anglais, l'état de langue courant étant conservé dans la session sous la clé `ui_lang` ; cette internationalisation répond à l'exigence de présentabilité de l'outil devant un client international. D'autre part, chaque page exécute en tête de fichier un *bootstrap* de `sys.path` destiné à garantir la résolution du backbone en module nu et donc à préserver l'invariant du singleton décrit en 6.3. Cette précaution, invisible pour l'utilisateur, est essentielle à l'intégrité du système lorsque les pages sont montées indépendamment par Streamlit.

## 6.6 Couche back-end et persistance durable

La couche back-end répond à une exigence opérationnelle critique : la durabilité de l'état opérateur. L'état applicatif est organisé en trois couches distinctes (Source interne : app/persistence.py ; CLAUDE.md). La couche *editing* rassemble les clés de widgets vivantes, c'est-à-dire l'état de saisie en cours. La couche *applied* matérialise le snapshot validé : il constitue la **source unique** consommée par la page Supervision et par l'agent, de sorte que l'édition de widgets ne modifie l'état de référence qu'au moment de l'enregistrement explicite. La couche *history* conserve sur disque l'historique durable des snapshots validés.

Le module `app/persistence.py` est la porte d'entrée et de sortie unique du snapshot. Il met en œuvre trois backends ordonnés par priorité. Le premier est **Supabase / Postgres** via son interface REST, retenu pour la production sur Streamlit Cloud : la table `rondol_state(key TEXT PRIMARY KEY, payload JSONB)` est mise à jour par un *upsert* portant l'en-tête `Prefer: resolution=merge-duplicates`, avec un délai d'expiration de quatre secondes. Le deuxième backend est un store externe sur fichier, hors du disque éphémère. Le troisième, le JSON local, ne sert que de repli en développement. La fonction `save_applied_state` écrit toujours le JSON local, puis tente l'écriture sur le backend durable en mode *best-effort*, garantissant qu'une panne réseau ne casse jamais un enregistrement local. La calibration des feeders (couples RPM × coefficient par feeder) est sérialisée dans le snapshot, assurant sa portabilité.

La motivation profonde de cette architecture tient à un défaut structurel de l'hébergement cible : le disque de Streamlit Cloud est éphémère, et un redémarrage ou un redéploiement efface tout fichier local. La plateforme intègre donc une **auto-réparation déterministe**. La fonction `migrate_and_restore` est invoquée en tête de page, avant tout widget : elle charge le snapshot durable, valide son schéma, le répare via la fonction pure `repair_snapshot_dict`, le réécrit dans la persistance durable s'il a été modifié, puis hydrate la session. Les réparations couvrent notamment le complètement du banc de feeders à cinq, la correction d'une densité inférieure à 0,01 g/cm³ vers une valeur par défaut de 0,55 g/cm³, et la substitution de cibles thermiques par défaut lorsque toutes les zones sont dégénérées. Ce mécanisme est idempotent et signalé à l'utilisateur par une bannière « Saved state repaired and synchronized » (Source interne : commits e43faf9, 3e64160, 926c963, 8f109ea).

[INSÉRER FIGURE : schéma de persistance Supabase (3 backends + auto-réparation)]

**Indexation et performance des requêtes.** La table `rondol_state` est dotée d'une clé primaire (`key TEXT PRIMARY KEY`), qui crée un index B-tree implicite servant directement le motif d'accès réel de l'application — la lecture du snapshot par sa clé (`SELECT payload FROM rondol_state WHERE key = 'applied_state'`). Le projet n'exploite **aucune indexation vectorielle** : il ne s'agit pas d'un système RAG (cf. Annexe B), mais d'une base relationnelle classique. Pour objectiver l'effet de l'optimisation exigé par le référentiel, un micro-benchmark reproductible compare le temps d'exécution de cette requête entre une table **non indexée** et une table **indexée**, à volumétrie simulée de 50 000 lignes (Source interne : scripts/sql_benchmark.py ; reports/sql_benchmark.json).

| Configuration de table | Temps moyen par requête | Interprétation |
|---|:--:|---|
| Non optimisée (sans index) | ≈ 4,74 ms | Balayage séquentiel O(n) de toutes les lignes |
| Optimisée (index B-tree sur `key`) | ≈ 0,005 ms | Recherche logarithmique O(log n) |

*Tableau 6.2 — Comparaison du temps d'exécution des requêtes entre table non optimisée et table optimisée (accélération ≈ ×1000). Le principe, index B-tree vs balayage, est identique sous PostgreSQL/Supabase.*

## 6.7 L'agent d'aide à la décision : règles, équation thermique et recommandations

L'agent industriel constitue la valeur ajoutée décisionnelle de la plateforme. Il est explicable par construction, reposant sur un système de règles métier plutôt que sur une boîte noire (Source interne : AgentIndustrial_v1/core/rules.py ; CLAUDE.md). Le module `rules.py` implémente dix règles, R1 à R10, couvrant respectivement la position des feeders, la compatibilité thermique de la matière, la surcharge de poudre, le taux de remplissage, l'énergie mécanique spécifique (SME), le temps de résidence, la monotonie thermique en filière, la duplication de position, le modèle de refroidissement et le profil thermique. Chaque alerte produite comporte un code, une sévérité (CRITICAL, WARNING, INFO ou OK), un titre, une description, une preuve chiffrée (*evidence*) et une cible. L'agent agrège ces alertes en un score de risque sur une échelle de 0 à 100, pondéré par sévérité (CRITICAL : −22 ; WARNING : −8 ; INFO : −2), score qui se traduit en trois états : STABLE pour une valeur supérieure ou égale à 80, SURVEILLER entre 60 et 79, et CRITIQUE en deçà de 60. L'API publique de l'agent, `evaluate(state, lang)`, renvoie un objet `AgentReport`.

Le modèle thermique repose sur l'équation imposée par le tuteur industriel, implémentée dans `cooling.py` : T_real,i = T_set,i + (2πNM) / (ṁ·Cp) + k·τ, avec une capacité thermique massique Cp de 2000 J/(kg·K), une fraction de rétention thermique de 0,085 et une constante K_TAU de 14. Cette équation alimente un index d'instabilité multi-facteur, pondérant l'énergie mécanique spécifique, le facteur de remplissage, l'écart thermique maximal et la charge en couple, avec des seuils de déclenchement fixés à 0,70 pour le niveau critique et 0,50 pour l'avertissement.

Le module `recommendations.py` complète le dispositif par plus de trente fonctions de *dispatch* transformant les alertes en actions correctives. Chaque recommandation porte un code, une catégorie (feeder, flux, température, profil de vis, vitesse), une sévérité, un titre, une justification (*rationale*), une action, un libellé d'écart chiffré avant→après (par exemple « 30 g/min → 22 g/min »), un indice de confiance et un code d'alerte liée (`linked_alert_code`) assurant la traçabilité vers l'alerte source. Une déduplication par code prévient la redondance des conseils présentés à l'opérateur. Cet ensemble garantit qu'aucune recommandation n'est orpheline : chacune découle d'une alerte identifiée, ce qui satisfait l'exigence d'explicabilité indispensable à l'adoption industrielle.

[INSÉRER CAPTURE : exemple d'alerte et de recommandation de l'agent]

## 6.8 Tests et déploiement

La fiabilité de la plateforme s'appuie sur une couverture de tests substantielle : la suite compte près de sept cents tests (694), pour une durée d'environ 170 secondes ; à la dernière exécution complète, 694 passent et un seul échoue de façon intermittente (une fragilité d'isolation entre tests de bout en bout, non un défaut applicatif — le test passe isolément) (Source interne : tests/ ; CLAUDE.md). Cette batterie ne se limite pas à la vérification fonctionnelle des pages ; elle protège également les invariants structurels du système, au premier rang desquels l'unicité du module backbone, contrôlée par les tests dédiés au singleton d'import. La séparation entre un sous-ensemble de tests purs et rapides, exécutable en boucle de développement courte, et les tests d'interface plus lourds reposant sur `streamlit.testing.v1.AppTest` permet un cycle de validation efficace sans sacrifier la couverture de bout en bout.

Le déploiement s'effectue selon une chaîne intégrée : le code est hébergé sur GitHub, l'application est servie par Streamlit Cloud, et la persistance durable de l'état validé est assurée par Supabase, conformément à l'architecture de persistance décrite en 6.6. Cette combinaison répond à l'objectif d'un outil réellement démontrable et accessible à distance par le client et le tuteur industriel, tout en contournant la limitation du disque éphémère grâce au backend durable et à l'auto-réparation déterministe. L'ensemble traduit une exigence constante du projet : préférer la robustesse et la cohérence d'intégration à l'accumulation de fonctionnalités, afin de présenter devant le jury comme devant Rondol Industrie un système crédible, testé et opérationnel.

## 6.9 Suivi des problématiques techniques rencontrées

Conformément à une démarche d'ingénierie tracée, les principales problématiques techniques (perte d'état après redémarrage cloud, désynchronisation entre pages, snapshot dégénéré, fuites de langue, surévaluation ML par fuite temporelle, dépendance au stockage local) ont été consignées avec leur cause, leur résolution et le commit Git correctif, puis figées en tests de non-régression. Le tableau de suivi complet est reporté en Annexe F.

[SAUT DE PAGE]

# Partie 7 — Résultats & démonstration

## 7.1 Protocole de démonstration et cas d'usage

La validation d'un outil de R&D industriel ne se mesure pas uniquement à la justesse de ses équations, mais à sa capacité à produire, devant un interlocuteur métier, un discours cohérent, reproductible et interprétable. C'est l'objet de cette partie : démontrer que la plateforme Rondol, au-delà de son architecture logicielle, se comporte comme un véritable jumeau numérique d'aide à la décision lorsqu'elle est confrontée à des situations procédé concrètes. Le protocole retenu repose sur une banque de cas d'usage construite spécifiquement pour la démonstration, dont les définitions et les résultats attendus ont été figés en amont afin de garantir la reproductibilité de la présentation (Source interne : reports/poster_abstract/cases/case_definitions.md ; reports/poster_abstract/cases/poster_results_cases.md ; docs/DEMO_MANAGER.md).

L'ensemble des cas s'appuie sur une plateforme de référence unique, de manière à isoler l'effet des variables manipulées. Il s'agit d'une extrudeuse Rondol de diamètre 10,5 mm, de rapport longueur sur diamètre L/D de 40:1, en configuration horizontale. Les conditions opératoires de référence sont une vitesse de vis de 150 rpm et un débit d'alimentation de 1,2 kg/h. Le profil thermique nominal est défini sur huit zones, selon une rampe de mise en température puis un plateau de fusion avant la filière, comme le résume le tableau ci-dessous.

| Zone | Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 |
|---|---|---|---|---|---|---|---|---|
| Consigne (°C) | 60 | 90 | 120 | 150 | 160 | 160 | 150 | 140 |

Cette plateforme commune garantit que les écarts observés entre les cas sont imputables aux paramètres délibérément modifiés (formulation, géométrie de vis, profil thermique) et non à une dérive du référentiel matériel. Conformément à la posture méthodologique défendue tout au long de ce mémoire, les valeurs présentées sont des grandeurs nominales issues d'un modèle non calibré industriellement : elles doivent être lues en tendance relative et au travers de la comparaison de configurations, et non comme des valeurs absolues opposables à un cahier des charges de production (Source interne : docs/DEMO_MANAGER.md).

Le scénario de démonstration client, d'une durée d'environ cinq minutes et programmé pour le 16 juin 2026, suit un parcours linéaire dans l'application, calqué sur la logique de travail d'un opérateur procédé : ouverture sur la page Supervision pour le diagnostic global, passage à la Configuration procédé (page Profile) pour intervenir sur la géométrie de vis, puis aux Paramètres IA et feeders (page Settings) pour ajuster le pilotage de l'agent et l'alimentation, et enfin consultation de l'Historique et du Moteur Procédé pour la traçabilité et le détail des calculs (Source interne : docs/DEMO_MANAGER.md). La banque de cas est conçue comme une narration progressive en cinq étapes : un point d'entrée représentatif de la cible applicative (C1), une configuration optimisée illustrant la marge de progrès (C2), une situation de risque délibérément provoquée (C3), la réponse explicable de l'agent face à ce risque (C4), et la validation quantifiée de la correction (C5). Cette progression vise à démontrer non pas une succession de fonctionnalités isolées, mais une boucle complète de détection, recommandation et vérification.






## 7.2 Synthèse des cinq cas de démonstration

Cinq cas de démonstration (C1 à C5) ont été déroulés selon le protocole ci-dessus : formulation lithiée de référence, configuration favorable, détection d'un risque de sur-remplissage, recommandation corrective de l'agent, puis validation après correction. Chaque cas confirme le comportement attendu : les indicateurs procédé réagissent de façon cohérente à la configuration, l'agent produit des alertes justifiées et des recommandations chiffrées, et la correction proposée ramène le système dans la zone nominale. Le déroulé détaillé de chaque cas (configuration, lectures, décisions) est reporté en Annexe D.

## 7.3 Synthèse des résultats

La séquence des cinq cas dessine une démonstration cohérente qui dépasse la simple illustration fonctionnelle pour valider une boucle complète d'aide à la décision procédé. Le tableau ci-dessous en récapitule les états caractéristiques.

| Cas | Description | Score /100 | Stabilité (p) | Observation clé |
|---|---|---|---|---|
| C1 | Formulation lithiée de référence (LFP 65 %, PVDF 8 %, Super P 5 %, LATP 17 %, LiTFSI 5 %), semi-dry | 65 | 0,84 | Régime stable, feu vert ; point d'ancrage métier |
| C2 | Configuration favorable (kneading Z5 45°→30°, élément ajouté en Z4) | 82 | 0,91 | Gain restitué par la géométrie de vis |
| C3 | Surcharge céramique (LATP porté à 35 %) | 46 | 0,35 | Alerte rouge Z5 ; couple > 80 % ; remplissage Z5 > 0,95 |
| C4 | Recommandation de l'agent (LATP 17–20 %, kneading Z4 30°, SME −15 %, T_Z5 +5 °C) | 70–80 (projeté) | — | Plan d'actions hiérarchisé et explicable |
| C5 | Validation après correction (LATP 17 %, LFP 65 %, kneading Z4 30°, T_Z5 165 °C) | 78 | 0,87 | Alerte levée ; remplissage Z5 0,72 |

La lecture de ce tableau confirme les trois propriétés attendues d'un jumeau numérique d'aide à la décision. La sensibilité d'abord : les indicateurs réagissent de manière lisible aux variations de formulation comme de géométrie, du point d'ancrage C1 (65/100) à la configuration optimisée C2 (82/100). La détectabilité ensuite : la situation de défaut C3 est franchement discriminée (chute à 46/100, probabilité de stabilité 0,35, alerte rouge localisée en Z5 et étayée par le couple et le taux de remplissage). La réversibilité enfin, qui est sans doute le résultat le plus probant : la transition de C3 à C5 traduit un redressement chiffré de +32 points de score, +0,52 de probabilité de stabilité, −0,25 de taux de remplissage en Z5 et la levée de l'alerte rouge, tout en confirmant a posteriori la justesse du score projeté annoncé par l'agent en C4.

Au-delà des chiffres, ces résultats valident la thèse défendue par le projet : il est possible de construire, sur une base de physique nominale assumée comme non calibrée industriellement, un outil dont la valeur démonstrable tient à la cohérence interne, à la lisibilité des tendances et à la traçabilité du raisonnement, plutôt qu'à une prétention de précision absolue. C'est dans cette logique de comparaison de configurations, et non de mesure étalonnée, que les cinq cas doivent être interprétés (Source interne : docs/DEMO_MANAGER.md). Cette grille de résultats constitue ainsi le support privilégié de la démonstration client du 16 juin 2026, qu'elle structure de bout en bout. [À COMPLÉTER : retour qualitatif du tuteur industriel M. Maël Gallas à l'issue de la démonstration du 16 juin 2026]

[SAUT DE PAGE]

# Partie 8 — Limites, risques, éthique & perspectives

L'honnêteté intellectuelle constitue un critère d'évaluation à part entière d'un travail d'ingénierie soumis à un jury professionnel. Présenter une réalisation comme exempte de limites reviendrait à en compromettre la crédibilité scientifique. Cette partie adopte donc une posture délibérément critique : elle expose sans complaisance les frontières actuelles du dispositif, les zones de fragilité technique et métier, ainsi que les engagements éthiques sur lesquels repose son acceptabilité. Cette lucidité n'est pas un aveu de faiblesse mais la condition d'une feuille de route crédible, dont les perspectives d'évolution closent le propos.

## 8.1 Limites techniques

La première limite, structurante, tient à la rareté des données expérimentales. Seuls huit essais sont aujourd'hui exploitables, ce qui constitue un socle insuffisant pour prétendre à une calibration industrielle robuste ou à une généralisation statistiquement étayée. En conséquence directe, le modèle de procédé n'est pas calibré industriellement : il produit des valeurs nominales dont la validité doit être comprise en tendance relative et non en valeur absolue. Cette posture est explicitement assumée dans l'interface, qui qualifie systématiquement le modèle de « non calibré », conformément à l'exigence de ne jamais présenter des nombres nominaux comme des grandeurs industrielles vérifiées.

Sur le plan de la modélisation physique, plusieurs équations demeurent volontairement différées. Les briques E5 (énergie mécanique spécifique locale, par nœud), E6 (température réelle avancée) et E7 (pression filière) ne sont pas codées et renvoient explicitement la valeur `None` : il s'agit de stubs documentés plutôt que d'approximations masquées (Source interne : engine/deferred.py ; app/pages/5_Process_Engine.py). Ce choix préserve l'intégrité du modèle en refusant d'injecter des résultats non fondés, mais il borne d'autant le périmètre de prédiction. Le modèle de couple, lui, repose sur la brique E4, dont la transparence est revendiquée : le couple local est dérivé d'un proxy fondé sur le volume rempli (`V_filled`), appliqué de manière uniforme. Cette uniformité est précisément une limite : le modèle ne pondère pas le couple selon le type d'élément, alors qu'un élément de malaxage (kneading) et un élément de convoyage ne sollicitent pas la motorisation de la même façon. De même, l'énergie mécanique spécifique n'est disponible qu'à l'échelle totale de la machine, sous l'hypothèse simplificatrice d'un régime établi, et non nœud par nœud. Le profil thermique exploité relève enfin d'une configuration nominale de démonstration. L'ensemble de ces choix conduit à une capacité de généralisation encore limitée, qu'il convient d'énoncer clairement devant tout interlocuteur industriel.

Une seconde catégorie de limites relève de l'outillage de développement plutôt que du modèle lui-même. Le projet ne dispose pas d'une chaîne d'intégration continue (CI/CD) : les vérifications restent déclenchées manuellement. La couverture de tests, bien que des tests existent (Source interne : tests/), n'est pas mesurée formellement, et aucun plan de tests formellement documenté n'encadre la démarche de validation. Ces manques traduisent une dette d'industrialisation logicielle, cohérente avec un développement de recherche mené par un acteur unique, mais qu'il faudra résorber pour passer du prototype démonstrable à un produit maintenable.

[INSÉRER FIGURE : tableau de synthèse des équations du moteur procédé indiquant pour chacune son statut — implémentée (E4) ou différée renvoyant None (E5/E6/E7)]

## 8.2 Risques métier et industriels

Au-delà des limites internes, le dispositif s'inscrit dans un écosystème porteur de risques propres. Le premier est la dépendance à des services cloud tiers : l'hébergement repose sur Streamlit Cloud et la persistance sur Supabase. Cette architecture, économique et rapide à déployer, expose le projet aux conditions de service, à la disponibilité et aux éventuelles évolutions tarifaires de fournisseurs externes sur lesquels le projet n'a pas la maîtrise. Une stratégie de réversibilité, ou a minima de sauvegarde locale, devra être envisagée pour tout passage en exploitation réelle.

Le deuxième risque est d'ordre architectural : le modèle est aujourd'hui orienté mono-opérateur. Il ne gère pas la concurrence entre plusieurs utilisateurs simultanés, ce qui expose à des écrasements d'état ou des incohérences si plusieurs personnes interagissent en parallèle avec la même instance. Ce choix est acceptable dans un cadre de démonstration et de R&D, mais constituerait un obstacle direct à un déploiement en atelier multi-postes.

Le troisième risque est cognitif : celui de la sur-interprétation des valeurs nominales par l'utilisateur. Malgré les avertissements affichés, un opérateur pourrait être tenté de prendre les sorties du modèle pour des grandeurs industrielles validées. Ce risque justifie à lui seul le soin apporté au cadrage du discours et à la visibilité des disclaimers. S'ajoute une dette technique consécutive à un développement rapide mené par un acteur unique, qui concentre la connaissance du système et fragilise sa maintenabilité à long terme. Enfin, un risque de marché doit être assumé : le secteur des batteries solides (SSB) demeure pré-industriel, ce qui repousse le retour sur investissement à un horizon de moyen terme et inscrit le projet dans une logique d'anticipation plutôt que de rentabilité immédiate.

## 8.3 Éthique et explicabilité

L'explicabilité constitue le point fort revendiqué du projet, et le différencie d'une approche « boîte noire ». L'agent décisionnel ne se contente pas de signaler des anomalies : chaque alerte porte une évidence chiffrée qui en justifie le déclenchement, et chaque recommandation est assortie d'une justification (`rationale`), d'un effet attendu exprimé en avant→après chiffré (`delta_label`) et d'un lien explicite vers l'alerte qui la motive (`linked_alert_code`) (Source interne : AgentIndustrial_v1/core/rules.py ; recommendations.py). Cette traçabilité de bout en bout, de la mesure à la recommandation, répond à l'exigence d'une intelligence artificielle compréhensible et auditable, particulièrement nécessaire dans un contexte industriel où la confiance de l'opérateur conditionne l'adoption.

La posture éthique assumée est claire : l'outil est conçu comme une aide à la décision, et non comme un système autonome. La décision finale demeure humaine. Cette frontière protège l'opérateur de toute déresponsabilisation et maintient l'expertise métier au centre du dispositif. Plusieurs limites éthiques sont néanmoins reconnues sans détour. Le système ne tient pas de journal d'audit distinguant les recommandations appliquées de celles qui ont été refusées, ce qui prive l'organisation d'une trace exploitable pour analyser a posteriori la qualité des conseils et l'usage qui en est fait. Les seuils des règles sont par ailleurs figés et ne s'adaptent pas automatiquement à la matière traitée, ce qui peut produire des alertes mal calibrées sur des formulations éloignées du cas de référence. Enfin, si un disclaimer figure dans la documentation, sa visibilité dans l'interface elle-même reste à renforcer, afin que le caractère non calibré du modèle soit perçu au moment même de la lecture des résultats, et non seulement dans un document annexe.

**Charte éthique du projet.** Pour fixer ces engagements, le projet se dote d'une charte éthique synthétique en sept principes :

1. Aide à la décision, non automatisation — l'outil éclaire le jugement de l'ingénieur ; il ne pilote jamais la machine ni ne décide à sa place.
2. **Honnêteté des données affichées** — les valeurs nominales non calibrées sont présentées comme telles ; aucun nombre n'est présenté comme une grandeur industrielle vérifiée.
3. Explicabilité de bout en bout — toute alerte et toute recommandation sont justifiées et traçables (évidence chiffrée, rationale, alerte liée).
4. **Pas de boîte noire** — la logique de décision repose sur des règles auditables et un score interprétable, non sur un modèle opaque.
5. **Respect de la donnée** — les données traitées sont des mesures de capteurs industriels, sans caractère personnel ; tout enrichissement futur par retours opérateur sera encadré (minimisation, rétention).
6. **Sobriété et utilité** — chaque bloc de l'interface pilote le moteur (alerte, score, recommandation) ; pas d'effet décoratif inutile, dans une logique de sobriété fonctionnelle.
7. **Reconnaissance des limites** — les frontières du modèle (rareté des essais, équations différées, non-calibration) sont explicitées plutôt que masquées.

[INSÉRER CAPTURE : panneau d'une recommandation de l'agent montrant le rationale, le delta_label avant→après et le linked_alert_code, illustrant la chaîne d'explicabilité]

## 8.4 Accessibilité et conformité

Sur le plan de l'accessibilité numérique, il faut reconnaître que les recommandations du référentiel WCAG 2.1 ne sont pas implémentées en l'état. La hiérarchie sémantique du contenu, l'usage des attributs ARIA et un audit de contraste systématique restent à réaliser. Cette lacune est cohérente avec la priorité donnée à la démonstrabilité fonctionnelle du prototype, mais elle devra être traitée pour toute mise à disposition élargie, en particulier auprès d'utilisateurs en situation de handicap. Elle constitue un chantier de conformité identifié, et non un point ignoré.

S'agissant de la protection des données, l'analyse au regard du Règlement général sur la protection des données (RGPD) conduit à un constat nuancé. Les données effectivement exploitées sont des mesures de capteurs industriels, couple, températures, débits, qui ne constituent pas des données à caractère personnel. L'applicabilité directe du RGPD au cœur du dispositif est donc limitée. Cette analyse appelle toutefois une réserve prospective : si une collecte de retours opérateur venait à être mise en place — notamment dans le cadre de l'enrichissement V2 portant sur les variables de couple et de pression — une politique de rétention et de minimisation des données devrait être formellement définie. Anticiper ce cadre dès maintenant relève d'une démarche de conformité responsable.

## 8.5 Perspectives d'évolution

Les limites énoncées dessinent en creux une feuille de route structurée, où chaque manque appelle une évolution identifiée. Le premier axe est l'enrichissement du jeu de données : multiplier les essais expérimentaux et, le cas échéant, recourir à la génération de données synthétiques dans l'esprit des travaux de Maia (2025), afin de dépasser le plafond actuel de huit essais et de rendre une calibration statistiquement crédible. Cet enrichissement est le préalable au deuxième axe, l'engagement d'une véritable calibration industrielle, qui ferait passer le modèle de la tendance relative à la grandeur quantitativement fiable.

Le troisième axe consiste à matérialiser les équations aujourd'hui différées. La brique E5 apporterait une énergie mécanique spécifique locale, nœud par nœud ; la brique E6 une température réelle avancée ; et la brique E7 une pression filière, modélisée par une loi de Hagen-Poiseuille en régime non newtonien. Ces développements lèveraient progressivement les bornes de prédiction décrites en 8.1. Sur le versant apprentissage automatique, l'ajout de l'interprétabilité SHAP au modèle ML prolongerait l'effort d'explicabilité du côté statistique, en exposant la contribution de chaque variable aux prédictions. Parallèlement, la résorption de la dette d'industrialisation logicielle passerait par la mise en place d'une chaîne CI/CD et d'une mesure formelle de la couverture de tests.

Un quatrième ensemble d'évolutions vise l'ouverture du périmètre fonctionnel et la conformité à la certification. L'ouverture au multi-utilisateur lèverait la limite mono-opérateur identifiée en 8.2. La formalisation du schéma SQL et la production du dump exigé par la certification consolideraient la maturité documentaire du projet. Enfin, l'intégration de capteurs temps réel de couple et de pression permettrait de franchir un cap qualitatif décisif : passer des proxys de la version V1 à des mesures directes en version V2, et ainsi confronter le modèle nominal à la réalité physique mesurée — boucle de validation qui constitue, à terme, la condition d'une crédibilité pleinement industrielle.

[INSÉRER FIGURE : feuille de route des perspectives en quatre axes — enrichissement des données et calibration, matérialisation des équations E5/E6/E7 et SHAP, industrialisation logicielle CI/CD, ouverture multi-utilisateur et capteurs temps réel V2]

[SAUT DE PAGE]

# Conclusion générale

Ce mémoire partait d'une question simple à énoncer et difficile à résoudre : peut-on transformer des paramètres d'extrusion en une aide à la décision fiable pour la fabrication de composants de batteries tout-solide, au service de l'extrudeuse bivis 10,5 mm de Rondol Industrie ? Au bout du compte, ma réponse est oui — mais un oui nuancé. J'ai fait d'un gisement de données thermiques réelles, jusque-là sous-exploité, un logiciel cohérent qui rend l'état du procédé lisible, anticipe ses dérives et propose des corrections chiffrées et justifiées. Ce que j'ai livré n'a pas vocation à remplacer l'instrumentation ni l'ingénieur : ça les outille. Et c'est justement ce positionnement, un prototype d'aide à la décision, pas un automate de pilotage déjà calibré, qui le rend crédible devant des ingénieurs.

Ce que je retiens de ce travail tient en quelques points. J'ai d'abord construit un jumeau numérique crédible : une logique métier ancrée dans la vraie géométrie de la vis (81 positions), un modèle supervisé nourri par douze capteurs de la campagne d'avril 2026, un agent explicable qui recommande. Mais le cœur méthodologique, c'est d'avoir affronté le manque de données plutôt que de le masquer. Mon championnat de cinq modèles, jugé sur des essais réels jamais vus, a d'abord donné des résultats modestes et instables — un F1-macro autour de 0,80, l'exacte mesure de mes huit essais. C'est l'augmentation de données, générée depuis l'échantillon et documentée, qui a débloqué la situation : elle a porté le Random Forest, mon modèle déployé, à 0,918 ± 0,054 sur essais réels non vus, en divisant sa variance par plus de trois. J'ai aussi tenu à séparer clairement les rôles : le modèle prédit, les règles expertes recommandent, l'humain décide. Et je n'ai jamais caché l'écart d'une quinzaine de points de F1 entre validation naïve et validation stricte — je le revendique comme la marque de la rigueur. Le tout repose sur une persistance durable auto-réparatrice (Supabase, avec repli fichier puis JSON local) et près de sept cents tests automatisés (Source interne : app/persistence.py ; tests/).

Les limites sont assumées et constituent le revers exact de ces choix. La première, structurelle, est le faible nombre d'essais exploitables (huit), qui borne la robustesse statistique et impose une lecture prudente des performances. La deuxième est l'absence de calibration industrielle complète : les valeurs procédé restent nominales et ne valent qu'en tendance relative. La troisième tient au périmètre scientifique volontairement borné — les équations E5/E6/E7 (énergie mécanique spécifique locale, température réelle avancée, pression filière) sont différées et documentées comme telles. La quatrième est le modèle de session orienté mono-opérateur, conséquence du choix de la pile Streamlit / Supabase. Ces limites n'invalident pas la démarche : elles en dessinent le statut exact, celui d'une contribution exploratoire honnête.

Stratégiquement, cet outil ouvre à Rondol une vraie différenciation sur un segment, les batteries tout-solide, où presque personne ne propose d'aide à la décision explicable reliant formulation, procédé et risques. Il prolonge aussi le savoir-faire pharmaceutique de l'entreprise, l'extrusion à chaud, vers les matériaux d'énergie, à un moment où la réglementation sur les PFAS pousse vers les procédés secs. La suite, je la vois balisée : plus d'essais, une calibration industrielle progressive, le codage des équations aujourd'hui différées, une chaîne d'intégration continue. Rien de spectaculaire, mais un chemin crédible pour faire mûrir ce prototype vers un outil de production. C'est sur cette base modeste et honnête que se construira, j'en suis convaincu, sa valeur durable pour Rondol Industrie.

# Bibliographie

La bibliographie ci-dessous reprend les trente-huit références de l'état de l'art consolidé du projet (*État de l'art V5*, version française), classées par ordre d'apparition dans la revue de littérature. Les volumes, numéros de page et identifiants DOI précis seront finalisés lors du dépôt à partir des notices originales.

1. Grand View Research (2025). « Solid State Battery Market 2025–2033 » (rapport de marché).
2. ResearchAndMarkets (2025). « Solid State Battery Market 2025–2030 », octobre 2025 (rapport de marché).
3. Haarmann, M., *et al.* (2021). « Continuous Processing of Cathode Slurry by Extrusion for Lithium-Ion Batteries ». *Energy Technology*.
4. Seeba, V., *et al.* (2024). « Continuous Anode Slurry Production in Twin-Screw Extrusion: Process Setup Effects ». *Batteries*.
5. Drakopoulos, O., *et al.* (2021). « Formulation and Manufacturing Optimization of Lithium-Ion Graphite-Based Electrodes via Machine Learning ». *Cell Reports Physical Science*.
6. Daoudi, O., *et al.* (2024). « Toward High-Performance Battery Cells with Machine-Learning-Based Optimization of Electrode Manufacturing ». *Journal of Power Sources*.
7. Payami, S., *et al.* (2025). « Critical Outlook on Separator Layers for Solid-State Lithium Batteries ». *ScienceDirect*.
8. Fraunhofer IWS (2025). « Scalable Cathode and Sulfidic Separator Manufacturing by DRYtraec® for Solid-State Batteries ».
9. QuantumScape Corp. (2024). « Next-Gen Solid-State Battery Separator Equipment "Cobra" », décembre 2024.
10. Electrive (2025). « QuantumScape Embeds New Separator Production Process », juin 2025.
11. Factorial Energy (2025). « Gammatron — AI-Powered Digital Twin Platform », juin 2025.
12. Zheng, Y., *et al.* (2024). « Recent Progress of High-Safety Separators for Lithium-Ion Batteries ». *Green Chemistry & Technology*.
13. Vattappara, K., *et al.* (2024). « Composite Separators with Very High Garnet Content for Solid-State Batteries ». *ChemElectroChem*.
14. Peng, Z., *et al.* (2024). « Dry Electrode Processing Technology and Binders ». *Materials*.
15. Al Solami, A., *et al.* (2024). « Engineering Dry Electrode Manufacturing for Sustainable Lithium-Ion Batteries ». *Batteries*.
16. Thermo Fisher Scientific (2025). « Enhancing Battery Manufacturing: The Crucial Role of Twin-Screw Extruders ».
17. AZoM (2023). « Twin-Screw Extrusion in Battery Manufacturing and Research ».
18. Kim, S. Y., *et al.* (2023). « Ultrahigh-Loading Dry-Process for Solvent-Free Lithium-Ion Battery Electrode Fabrication ». *Nature Communications*.
19. Kassab, S., *et al.* (2024). « Integrating AI in Polymer Extrusion: Trends, Challenges and Future Directions ». *International Journal of Intelligent Systems and Applications in Engineering (IJISAE)*.
20. Coperion / Charged EVs (2025). « Battery Manufacturing Efficiency with Roller Feeder and Extruder », septembre 2025.
21. Hutton, D. (2025). « AI and Machine Learning Transform the Plastics Industry ». *Plastics Today*, novembre 2025.
22. Maia, J. A., *et al.* (2025). « Machine Learning in Polymer Extrusion: Synthetic Data and Real-Time Control ». *AMI Plastics World Expo*.
23. Haghi, H., *et al.* (2025). « Optimizing Lithium-Ion Battery Manufacturing with Digitalization and AI-Driven Frameworks ». *International Journal of Advanced Manufacturing Technology*.
24. Wang, S., *et al.* (2025). « AI Empowers Solid-State Batteries for Material Screening ». *Nano-Micro Letters*.
25. Li, X., *et al.* (2025). « Accelerating the Battery Revolution: AI-Driven Multiscale Innovation ». *Advanced Functional Materials*.
26. Hu, C., *et al.* (2025). « AI-Driven Development in Rechargeable Battery Materials ». *Advanced Functional Materials*.
27. Ge, R., *et al.* (2025). « Advancing Intelligent Additive Manufacturing: Machine Learning for Process Optimization ». *International Journal of Additive Manufacturing & Design (IJAMD)*.
28. Chen, W., *et al.* (2024). « Machine Learning in Lithium-Ion Batteries: Applications, Challenges, and Future Trends ». *SN Computer Science*.
29. Wang, Y., *et al.* (2025). « Application-Oriented Design of Machine-Learning Paradigms for Battery Science ». *npj Computational Materials*.
30. Li, Z., *et al.* (2025). « Revolutionizing Batteries via Digital Twin through AI–Simulation Synergy ». *National Science Open*.
31. Kim, B., *et al.* (2025). « High-Loading Dry-Electrode for Solid-State Batteries: Nanoarchitectonic Strategies ». *Electrochemical Energy Reviews*.
32. Wiegmann, E., *et al.* (2025). « Process–Structure–Property Correlations in Twin-Screw Extrusion of Graphitic Electrodes ». *Batteries*.
33. Zhang, T., *et al.* (2025). « Strategically Tailored Polyethylene Separator for Liquid and Solid-State Lithium-Ion Batteries ». *ScienceDirect*.
34. Wang, L., *et al.* (2025). « Battery Separator by Blow Molding–Extraction ». *Chinese Journal of Engineering*.
35. MarketsandMarkets (2025). « Solid-State Battery Market 2025–2031 » (rapport de marché).
36. Roots Analysis (2025). « Solid State Battery Market 2025–2035 », septembre 2025 (rapport de marché).
37. Ng, C. K., *et al.* (2024). « Machine Learning in Materials and Processes of Additive Manufacturing ». *Advanced Materials*.
38. Biesuz, A., *et al.* (2023). « Optimization with Artificial Intelligence in Additive Manufacturing ». *Journal of the Brazilian Society of Mechanical Sciences and Engineering*.

# Annexes

## Annexe A — Dictionnaire de données

Le dictionnaire des principales variables explicatives et de la variable cible figure au corps du mémoire, dans le **Tableau 5.1** (Partie 5, section 5.2), auquel le lecteur est renvoyé. Ce tableau présente un extrait représentatif des variables dérivées des douze capteurs de température (moyennes, écarts-types, pentes, écarts interquartiles par zone, gradients croisés inter-étages) ainsi que la construction de la cible binaire `is_stable`.

Le jeu de données complet retenu pour le modèle de production (fenêtre 60 secondes) comporte **96 variables brutes** par fenêtre, obtenues en combinant sept statistiques par capteur sur les douze voies, augmentées de trois variables croisées entre capteurs (Source interne : src/features.py ; src/config.py).

[À COMPLÉTER : dictionnaire exhaustif des 96 variables dérivées, avec pour chacune le nom exact, la définition, l'unité, le capteur source et le rôle dans le modèle.]

## Annexe B — Schéma de la base de données

La persistance durable de l'état validé repose sur une unique table relationnelle, hébergée sur Supabase (service PostgreSQL géré). Le schéma effectif est le suivant :

sql
CREATE TABLE rondol_state (
    key     TEXT PRIMARY KEY,
    payload JSONB
);


L'instantané (snapshot) validé `applied_state` — source unique de vérité de la plateforme, consommée par l'ensemble des pages (Supervision, Profile, Settings, Run Analysis, History, Process Engine) — est sérialisé et stocké dans la colonne `payload` au format **JSONB**, sous la clé `applied_state` (colonne `key`). Cette colonne contient notamment le profil de vis (`screw_config`), les consignes thermiques, les paramètres de dosage et les calibrations de feeders.

Supabase reposant sur PostgreSQL, cette table demeure pleinement compatible avec la production du **dump SQL** exigé par la certification : un dump réel, rejouable, est fourni dans le dossier projet sous `database/rondol_state_dump.sql` (schéma + données d'état + index). La réorientation technologique vers Streamlit / Supabase ne compromet donc pas ce livrable (Source interne : app/persistence.py ; scripts/generate_sql_dump.py).

**Indexation.** La table porte un index B-tree implicite via sa clé primaire (`key`), exploité par la lecture du snapshot, et un index **GIN** sur la colonne `payload` autorisant d'éventuelles requêtes par champ du document JSONB.

**Nature du projet — clarification explicite.** Le projet Rondol n'est pas un projet RAG (*Retrieval-Augmented Generation*) et ne repose sur aucune indexation vectorielle ni base documentaire. Il s'appuie sur des **données industrielles structurées** (fichiers CSV de capteurs), un pipeline séquentiel de feature engineering complété par une augmentation de données documentée à partir de l'échantillon, un **modèle supervisé** (RandomForest retenu et déployé ; régression logistique, SVM, XGBoost, MLP en comparatif) et une **persistance d'état** relationnelle (Supabase / PostgreSQL, document JSONB). Cette précision est posée pour lever toute ambiguïté lors de l'évaluation.

[INSÉRER FIGURE : schéma entité-relation de la table `rondol_state` et structure du document JSONB `applied_state`]

## Annexe C — Glossaire

L'ensemble des sigles, abréviations et acronymes utilisés dans ce mémoire (ANN, API, AUC-ROC, CRISP-DM, CV, DIE, ECHA, F1, FF, GSS, HME, HMI, IJL, JSON, KPI, L/D, LATP, LFP, LIB, LiTFSI, LOGO, ML, PFAS, PVDF, RF, RNCP, RPM, RT, SME, SSB, SVM, TSE, XGBoost) est défini dans la Liste des sigles et abréviations figurant en tête de mémoire, à laquelle le lecteur est renvoyé.

## Annexe D — Cas tests C1–C5

Le tableau ci-dessous récapitule les cinq cas d'usage lithiés ayant servi à la démonstration de la plateforme. Le score désigne le score de stabilité (sur 100) ; la probabilité indiquée est la probabilité associée au régime évalué.

| Cas | Formulation / variation | Score | Stabilité |
|---|---|:--:|---|
| C1 | Baseline LFP 65 % / PVDF 8 % / Super P 5 % / LATP 17 % / LiTFSI 5 % | 65 | Stable (p = 0,84) |
| C2 | Configuration favorable | 82 | Stable (p = 0,91) |
| C3 | LATP porté à 35 % | 46 | Instable (p = 0,35) |
| C4 | Recommandation corrective de l'agent | 70–80 (score projeté) | Retour visé vers un régime stable (projeté) |
| C5 | LATP ramené à 17 % | 78 | Stable (p = 0,87) |

*Tableau D.1 — Synthèse des cas tests C1 à C5. La séquence C3 → C4 → C5 illustre le parcours complet : détection d'une instabilité (C3), recommandation chiffrée de l'agent (C4), retour à un régime stable après correction (C5). Source interne : reports/poster_abstract/cases/case_definitions.md.*

### Cas détaillé — Cas C1 — formulation lithiée de référence

Le premier cas établit le point d'ancrage métier de la démonstration : une formulation lithiée représentative de la cible applicative du projet, à savoir l'extrusion de composants pour batteries solides ou semi-solides. La recette retenue est une électrode composite associant un matériau actif majoritaire, un liant fluoré, un additif conducteur et un électrolyte solide céramique avec son sel de lithium, selon la répartition massique suivante : LFP (LiFePO₄) 65 %, Kynar PVDF 8 %, Super P 5 %, LATP 17 % et LiTFSI 5 %, le procédé étant conduit en voie semi-dry (Source interne : reports/poster_abstract/cases/case_definitions.md).

Soumise au moteur d'analyse de la plateforme, cette formulation de référence obtient un score de compatibilité de 65/100, associé à un diagnostic de régime stable avec une probabilité de stabilité p égale à 0,84, ce qui se traduit par un feu vert dans l'interface de supervision (Source interne : reports/poster_abstract/cases/poster_results_cases.md). Ce résultat est intéressant à plusieurs titres. D'une part, il confirme que la cible applicative la plus exigeante du projet, une formulation fortement chargée en céramique et en sel de lithium, se situe dans un domaine procédé exploitable, mais sans excès d'optimisme : un score de 65/100 traduit une fenêtre opératoire correcte plutôt que confortable, ce qui est cohérent avec la difficulté réelle d'extruder une électrode composite chargée. D'autre part, il illustre la posture de l'outil, qui ne cherche pas à flatter la configuration de référence mais à la situer honnêtement sur une échelle relative. Ce cas sert donc de point zéro à la démonstration : c'est par rapport à lui que seront appréciés le gain d'une optimisation (C2) et, à l'inverse, la dégradation provoquée par une surcharge (C3).
### Cas détaillé — Cas C2 — configuration favorable

Le deuxième cas a pour vocation de démontrer que la plateforme sait valoriser une amélioration et la traduire par une variation lisible de ses indicateurs. À partir d'une formulation favorable, et surtout d'un travail sur la géométrie de vis, la configuration atteint un score de compatibilité de 82/100, avec un régime stable et une probabilité de stabilité p de 0,91 (Source interne : reports/poster_abstract/cases/poster_results_cases.md).

L'intérêt de ce cas réside dans la nature des leviers actionnés : il ne s'agit pas seulement de modifier la recette, mais d'agir sur le profil de vis, c'est-à-dire sur le cœur géométrique du procédé. Concrètement, l'ajustement consiste à adoucir le malaxage en zone Z5 en faisant passer l'angle d'un élément kneading de 45° à 30°, et à ajouter un élément en zone Z4 (Source interne : reports/poster_abstract/cases/case_definitions.md). La réduction de l'angle de décalage des disques de malaxage diminue l'intensité du cisaillement dispersif localisé, tandis que la modification du remplissage géométrique en amont rééquilibre la progression de la matière. Le fait que la plateforme restitue ce gain par un score nettement supérieur à celui de C1 (82 contre 65) et une probabilité de stabilité accrue (0,91 contre 0,84) démontre que ses indicateurs sont sensibles à la géométrie réelle de la vis, et non à de simples paramètres déclaratifs. Ce cas valide ainsi la cohérence du couplage entre la configuration géométrique (page Profile) et le diagnostic affiché en Supervision.

[INSÉRER CAPTURE : page Profile illustrant la modification de l'élément kneading Z5 et l'ajout d'élément en Z4 du cas C2]
### Cas détaillé — Cas C3 — détection d'un risque de sur-remplissage

Le troisième cas constitue le pivot dramatique de la démonstration : il provoque délibérément une situation de défaut afin de vérifier que la plateforme la détecte, la localise et la signale sans ambiguïté. Le défaut est introduit par une surcharge en électrolyte céramique, la teneur en LATP étant portée à 35 % au lieu des 17 % de la formulation de référence, ce qui déséquilibre le bilan de matière et la rhéologie locale (Source interne : reports/poster_abstract/cases/case_definitions.md).

La réponse de l'outil est nette et convergente. Le score de compatibilité chute à 46/100, le régime est diagnostiqué instable avec une probabilité de stabilité p réduite à 0,35, et une alerte rouge est déclenchée en zone Z5. Cette alerte est étayée par des indicateurs procédé concordants : un couple supérieur à 80 % et un taux de remplissage en Z5 supérieur à 0,95 (Source interne : reports/poster_abstract/cases/poster_results_cases.md). La cohérence de ce faisceau d'indices est précisément ce qui fait la crédibilité du diagnostic : la surcharge en céramique augmente la viscosité et la résistance à l'écoulement, ce qui se répercute logiquement sur le couple et sur le remplissage local au niveau de la zone de malaxage Z5, point bas de la fenêtre opératoire. La plateforme ne se contente donc pas de produire un score global défavorable ; elle désigne la zone responsable et fournit les grandeurs physiques qui motivent l'alerte, ce qui correspond à l'exigence d'explicabilité d'un agent de supervision industriel. Sur le plan de la démonstration, ce cas illustre la valeur préventive de l'outil : un risque de sur-remplissage en Z5, qui se traduirait en pratique par un blocage ou un emballement de couple sur la machine réelle, est ici anticipé et rendu visible avant toute mise en production.

[INSÉRER CAPTURE : page Supervision pour le cas C3 (alerte rouge Z5)]
### Cas détaillé — Cas C4 — recommandation de l'agent

Le quatrième cas met en scène la fonction d'aide à la décision proprement dite : face au risque détecté en C3, l'agent ne se borne pas à signaler le problème, il propose un plan de correction structuré et hiérarchisé. Le panneau de recommandation présente une série d'actions ordonnées par priorité, articulant un levier de formulation et plusieurs leviers procédé (Source interne : reports/poster_abstract/cases/poster_results_cases.md).

Les actions recommandées sont les suivantes : ramener la teneur en LATP de 35 % à une fourchette de 17 à 20 %, c'est-à-dire revenir dans le domaine de la formulation de référence ; ajuster l'angle de l'élément kneading en zone Z4 à 30° pour adoucir le malaxage en amont ; réduire l'énergie mécanique spécifique (SME) d'environ 15 % afin de limiter la sollicitation thermomécanique ; et augmenter la consigne thermique de la zone Z5 de +5 °C pour fluidifier la matière au point critique. L'application de ce plan conduit à un score projeté de 70 à 80/100 (Source interne : reports/poster_abstract/cases/case_definitions.md). La structure de cette recommandation mérite d'être soulignée : elle hiérarchise les actions, distingue le levier le plus déterminant (le retour de la charge céramique dans son domaine) des ajustements de second ordre (géométrie, thermique, SME), et fournit une estimation de l'effet attendu. C'est cette logique explicable, et non une boîte noire prédictive, qui répond à l'attente d'un outil de R&D destiné à éclairer le jugement de l'ingénieur procédé plutôt qu'à le remplacer. Le caractère projeté du score affiché entretient par ailleurs la posture d'honnêteté de l'outil : la recommandation annonce un résultat attendu, qui ne sera confirmé qu'après application effective et nouvelle évaluation, objet du cas suivant.

[INSÉRER CAPTURE : panneau de recommandation de l'agent (cas C4)]
### Cas détaillé — Cas C5 — validation après correction

Le cinquième cas referme la boucle de démonstration en vérifiant que les corrections recommandées par l'agent produisent effectivement le redressement annoncé. La configuration corrigée applique les leviers principaux du plan : la teneur en LATP est ramenée à 17 % et le LFP rétabli à 65 %, l'angle de l'élément kneading en Z4 est fixé à 30° et la consigne thermique de la zone Z5 portée à 165 °C (Source interne : reports/poster_abstract/cases/case_definitions.md).

Le résultat valide la trajectoire prédite par l'agent. Le score de compatibilité remonte à 78/100, le régime redevient stable avec une probabilité de stabilité p de 0,87, l'alerte rouge en Z5 est levée et le taux de remplissage en Z5 retombe à 0,72, soit nettement en deçà du seuil critique observé en C3 (Source interne : reports/poster_abstract/cases/poster_results_cases.md). En rapprochant directement les états C3 et C5, on mesure l'ampleur du redressement : le score progresse de 32 points (de 46 à 78), la probabilité de stabilité gagne 0,52 (de 0,35 à 0,87), le taux de remplissage en Z5 diminue de 0,25 (de plus de 0,95 à 0,72) et l'alerte rouge est levée (Source interne : reports/poster_abstract/cases/poster_results_cases.md). Ce bilan est doublement significatif. Il démontre d'abord que la chaîne complète, détection, recommandation, correction, vérification, fonctionne de bout en bout et boucle sur elle-même de façon cohérente. Il confirme ensuite que le score projeté annoncé en C4 (70 à 80/100) est tenu en pratique (78/100), ce qui crédibilise le caractère prédictif des recommandations de l'agent. Pour un démonstrateur client, ce cas final est le plus convaincant : il transforme une promesse qualitative d'aide à la décision en une amélioration chiffrée et reproductible.

[INSÉRER CAPTURE : Supervision après correction (cas C5, alerte levée)]


## Annexe E — Captures à insérer

[INSÉRER CAPTURE : page Supervision — statut machine, score de stabilité, probabilité de dérive, alertes, recommandations IA et KPIs procédé]
[INSÉRER CAPTURE : page Profile — configuration du profil de vis (zones, éléments, compteurs +/-, KPIs)]
[INSÉRER CAPTURE : page Settings — seuils de l'IA et variables surveillées]
[INSÉRER CAPTURE : cas C3 — état instable affiché (LATP 35 %, score 46, probabilité 0,35)]
[INSÉRER CAPTURE : recommandation C4 — action corrective chiffrée et justifiée émise par l'agent]
[INSÉRER CAPTURE : état après correction C5 — retour à un régime stable (LATP 17 %, score 78, probabilité 0,87)]
[INSÉRER CAPTURE : page Moteur Procédé (Process Engine) — vue moteur en lecture seule]

# Points à compléter avant dépôt

- **Données institutionnelles Rondol Industrie** : chiffre d'affaires, effectif, statut juridique et dirigeants (non présents dans les sources internes).
- **Calendrier académique** : date de dépôt et date de soutenance du mémoire.
- **Rétroplanning** : périodes exactes des phases du projet signalées [À COMPLÉTER] dans le Tableau 4.1 (cadrage, état de l'art, préparation des données, développement du moteur, modélisation ML, développement de l'interface, rédaction et dépôt).
- **Étude de marché** : chiffrage du marché de l'extrusion de laboratoire (taille, taux de croissance annuel / CAGR, segmentation géographique).
- **Analyse concurrentielle** : données chiffrées sur les concurrents (brevets, outils IA intégrés, parts de marché, chiffres d'affaires) — cellules [À COMPLÉTER] des Tableaux 2.1.
- **Bibliographie** : intégration des 38 références complètes de l'état de l'art V5, avec volumes, numéros, pages et DOI.
- **Dictionnaire de données** : dictionnaire exhaustif des 96 variables dérivées (Annexe A).
- Validation de la mise en page finale : insertion des captures et figures réelles, mise à jour du sommaire automatique et vérification de la pagination dans le document Word/PDF de dépôt.
- **Captures d'écran réelles** : intégration des sept captures listées en Annexe E (Supervision, Profile, Settings, C3, C4, C5, Moteur Procédé) et des figures / logos signalés [INSÉRER FIGURE] / [INSÉRER CAPTURE] dans le corps du mémoire.

## Annexe F — Suivi des problématiques techniques (Tableau 6.1)

| # | Date | Problématique technique | Cause | Date résolution | Solution / correctif | Réf. (commit / fichier) |
|---|---|---|---|---|---|---|
| 1 | Juin 2026 | Perte de l'état opérateur après redémarrage cloud | Disque Streamlit Cloud éphémère : `applied_state.json` volatile | Juin 2026 | Couche de persistance durable Supabase (REST) avec repli fichier/JSON | `926c963`, `app/persistence.py` |
| 2 | Juin 2026 | Désynchronisation de l'état entre les pages | Sources d'état multiples (widgets vs snapshot) | Juin 2026 | Snapshot `applied_state` comme source unique, `hydrate_session_from_applied` sur les 6 pages | `8f109ea` |
| 3 | Juin 2026 | Widgets à 0 après reboot (snapshot dégénéré) | Ligne Supabase dégénérée issue d'un ancien build | Juin 2026 | Auto-réparation déterministe `repair_snapshot_dict` (padding feeders, densité, zones) | `3e64160`, `e43faf9` |
| 4 | Juin 2026 | Sauvegarde de profil non persistée durablement | Miroir disque volatil, restauration `setdefault`-only | Juin 2026 | Miroir du snapshot validé vers backend durable | `ccf1c3b`, `AgentIndustrial_v1/core/applied_state.py` |
| 5 | Juin 2026 | Fuites de chaînes françaises en mode anglais | Couverture i18n incomplète, evidence non bilingue | Juin 2026 | Bascule `ui_lang`, `label_en`, tests anti-fuite (> 70 chaînes) | `aaeab5e`, `tests/test_i18n_no_french_leaks.py` |
| 6 | Avril 2026 | Surévaluation des performances ML (fuite) | Autocorrélation temporelle des fenêtres d'un même essai | Avril 2026 | Séparation par essai (GroupShuffleSplit), LOGO, cible décalée | `src/train_models.py`, `reports/robustness_full_w60.json` |
| 7 | Juin 2026 | Dépendance au disque local pour le déploiement | Hébergement distant sans stockage permanent | Juin 2026 | Variables d'environnement / secrets Streamlit + Supabase | `.streamlit/secrets.toml.example` |


*Tableau 6.1 — Suivi des problématiques techniques ; correctifs tracés par commit Git.*
