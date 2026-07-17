# Rondol — Extrusion Digital Twin Prototype

Prototype de **jumeau numérique / moteur procédé** pour une extrudeuse bivis
Rondol (Ø 10,5 mm), appliqué à l'extrusion de composants de **batteries
tout-solide (SSB)** en voie sèche / semi-sèche (lithium, LFP/LATP).

Il combine une **logique géométrique réelle de vis**, un **moteur de
physique-procédé en couches**, et un **agent IA explicable** (alertes +
recommandations chiffrées, rule-based, sans boîte noire), le tout présenté dans
une interface type HMI industriel (Streamlit).

## Objectif manager / client

Disposer d'un **outil R&D crédible et démontrable** permettant de :
- visualiser l'état procédé et un **score de stabilité** (modèle ML RandomForest, entraîné avec augmentation de données) ;
- configurer un **profil de vis** (81 positions, 13 types d'éléments) et lire
  ses indicateurs (taux de remplissage, résidence, volumes) ;
- paramétrer l'**IA & les feeders** et obtenir des recommandations
  actionnables ;
- **comparer** des configurations procédé (raisonnement relatif), pas produire
  des valeurs industrielles absolues.

> Outil d'**aide à la décision** : démonstration et **comparaison relative** de
> configurations, **pas** un logiciel de pilotage industriel.

## Fonctionnalités principales

| Page | Rôle |
|------|------|
| **Supervision procédé** (accueil) | État machine, score de stabilité, probabilité de dérive, alertes, recommandations IA, KPIs |
| **Configuration procédé** | Construction du profil de vis, indicateurs temps réel, lecture métier |
| **Paramètres IA & feeders** | Seuils IA, feeders/matières, profil thermique, enregistrement de configuration |
| **Analyse du run** | Analyse temporelle d'un run de production (score, fenêtres, profil thermique) |
| **Historique des procédés** | Historique persistant des configurations enregistrées (KPIs figés au commit) |
| **Moteur Procédé** | Vue read-only du moteur de physique-procédé (couche `engine/`) |
| **Sélecteur de langue FR / EN** | Bascule de l'interface (chrome) entre français et anglais professionnels |

## Données et validation du modèle

- **Campagne réelle** : essais du 07 au 13 avril 2026 (12 capteurs, 52 064 lignes brutes) → 798 fenêtres de 60 s (87 variables) pour l'entraînement.
- **Base consolidée simulée** : 100 800 lignes générées à partir de l'échantillon réel (plateaux, bruit de régulation, manquants et codes d'erreur reproduits, épisodes d'instabilité) — plan de génération : `data/consolidated/rapport_generation.md`, script reproductible `scripts/generate_consolidated_dataset.py` (seed fixe ; CSV non versionné, régénérable).
- **Validation externe** : le modèle déployé, évalué **sans réentraînement** sur cette base (`scripts/evaluate_on_consolidated.py`), conserve un pouvoir discriminant (AUC 0,753, erreurs majoritairement conservatrices) — `reports/eval_consolidated_w60.json`.
- **Notebook d'accompagnement** : `notebooks/notebook_application_rondol.ipynb` (moteur procédé, EDA, ML — exécuté sans erreur).

## Lancement

```bash
streamlit run app/Supervision.py
```

## Installation (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/Supervision.py
```

macOS / Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Supervision.py
```

L'application s'ouvre sur `http://localhost:8501`. Python **3.13** recommandé.

## Avertissement honnête

Ce dépôt est un **prototype d'aide à la décision**. Les grandeurs physiques sont
**nominales et non calibrées industriellement** : elles servent à la
**démonstration** et à la **comparaison relative** de configurations, et ne
doivent **pas** être interprétées comme des valeurs procédé absolues. L'interface
conserve volontairement ce cadrage (« modèle non calibré », « À venir » pour les
équations différées).

## Pages / briques validées

- **Moteur Procédé** — vue moteur procédé (`engine/`), validée et démontrable.
- **Historique des procédés** — persistance disque validée (KPIs figés au commit).
- **Scaffolding i18n (B0)** + **harmonisation des libellés (B1)** — sélecteur
  FR/EN et traduction du chrome des pages principales.

## Limites connues

- **Calibration industrielle non finalisée** : valeurs nominales, comparaison
  relative uniquement.
- **Équations E6/E7** (pression filière, T° réelle avancée) : **à venir**
  (stubs documentés retournant `None`).
- **Traductions progressives** : le *chrome* (titres, sections, boutons, labels)
  est traduit (B1) ; les **contenus générés par l'agent IA** (alertes,
  recommandations, diagnostics) et les pages Moteur/Historique sont traduits
  dans les phases suivantes (B2/B3/B4) et peuvent rester partiellement en
  français.

## Guide de test manager (5 minutes)

Voir **[docs/DEMO_MANAGER.md](docs/DEMO_MANAGER.md)** pour un parcours guidé :

1. Lancer `streamlit run app/Supervision.py`.
2. Sur **Supervision procédé** : lire l'état, le score de stabilité, les alertes
   et recommandations ; changer de run / fenêtre dans la barre latérale.
3. Basculer la langue **FR / English** (haut de la barre latérale).
4. Aller dans **Configuration procédé** : charger « Configuration démo », ajouter
   des éléments (+1/+4), observer les indicateurs.
5. Aller dans **Paramètres IA & feeders**, ajuster une consigne, **Enregistrer**,
   puis consulter **Historique des procédés** et **Moteur Procédé**.

## Structure (vue d'ensemble)

```
app/                Application Streamlit (Supervision + pages)
  i18n.py           Couche de traduction FR/EN (chrome)
engine/             Moteur de physique-procédé (read-only, pur)
machine/ materials/ physics/   Catalogues & formules (purs)
AgentIndustrial_v1/ Agent IA explicable (règles + recommandations)
i18n_messages.py    Catalogue pur des messages agent (FR/EN)
models/             Modèle ML déployé : RandomForest_w60_augmented.joblib (SVM_w60.joblib = challenger)
data/features/      Jeux de données : dataset_ml_w60.csv (réel) + dataset_ml_w60_augmented.csv (réel+synthétique)
src/                Pipeline ML hors-ligne (optionnel, non requis pour l'app)
tests/              Tests (moteur, pages, i18n)
```
