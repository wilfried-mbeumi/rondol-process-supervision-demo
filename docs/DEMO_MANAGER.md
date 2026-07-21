# Guide de démonstration — Manager (5 minutes)

Ce guide permet de tester l'application **Rondol — Extrusion Digital Twin
Prototype** sans connaissance technique préalable.

> Rappel : prototype d'**aide à la décision**. Les valeurs sont **nominales /
> non calibrées industriellement** — on lit des **tendances** et on **compare**
> des configurations, pas des valeurs absolues.

---

## Option A — Test en local (recommandé)

### Pré-requis
- Python **3.13** installé.

### Installation et lancement (Windows / PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/Supervision.py
```
macOS / Linux :
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Supervision.py
```
L'application s'ouvre sur **http://localhost:8501**.

---

## Option B — Lien web (Streamlit Cloud)

Un lien de démonstration est déployé :
`https://rondol-process-supervision-demo.streamlit.app` — il suffit de l'ouvrir
dans un navigateur, aucune installation requise.

> **Si l'application « dort »** (mise en veille automatique après inactivité),
> cliquer sur *« Yes, get this app back up! »* et patienter ~1 minute.

---

## Connexion (accès protégé)

L'application demande une **connexion** au premier accès (le mot de passe est
haché, jamais stocké en clair). Identifiants de démonstration :

| Champ | Valeur |
|---|---|
| **Email** | `demo@rondol.local` |
| **Mot de passe** | `0000` |

Après connexion, la page **Compte** affiche l'historique des connexions
(lu depuis la base Supabase) — une illustration concrète de l'interaction de
l'application avec sa base de données.

---

## Parcours guidé (≈ 5 minutes)

### 1. Supervision procédé (page d'accueil) — 90 s
- En haut de la **barre latérale**, basculer la langue **Français / English**.
- Choisir un **run de production** et déplacer le curseur **fenêtre active**.
- Observer : **état procédé** (STABLE / À surveiller / Critique), **score de
  stabilité**, bandeau des **zones thermiques**, **recommandations** et le
  **graphique d'évolution** du score.

### 2. Configuration procédé — 90 s
- Barre latérale → bouton **« Configuration démo »** pour charger un profil.
- Ajouter des éléments avec **+1 / +4**, en retirer avec **−1**.
- Observer en temps réel : **taux de remplissage moyen**, **temps de résidence**,
  **volume occupé / libre**, et la **lecture métier** par zone.

### 3. Paramètres IA & feeders — 90 s
- Ajuster une **consigne de température** (Z1…Z8) ou un **débit feeder**.
- Observer la mise à jour des **alertes** et du **score IA**.
- Cliquer **« Enregistrer la configuration »** : la configuration devient la
  version active de Supervision et entre dans l'historique.

### 4. Historique des procédés & Moteur Procédé — 60 s
- **Historique des procédés** : retrouver la configuration enregistrée avec ses
  **KPIs figés** au moment de l'enregistrement.
- **Moteur Procédé** : vue read-only du moteur de physique-procédé (couple,
  viscosité, agrégats par zone).

---

## Données de démonstration

- L'historique affiché provient du fichier **runtime**
  `data/history/process_history.json` (non versionné).
- Un **seed anonymisé** est fourni :
  `data/history/demo_process_history.json`.
- Pour pré-remplir l'historique avant la démo (optionnel) :

  **Windows / PowerShell**
  ```powershell
  Copy-Item data\history\demo_process_history.json data\history\process_history.json
  ```
  **macOS / Linux**
  ```bash
  cp data/history/demo_process_history.json data/history/process_history.json
  ```
  Alternativement, sans copie : définir la variable d'environnement
  `RONDOL_HISTORY_PATH` vers le fichier seed avant de lancer l'app.
- Sans aucune de ces étapes, la page **Historique** affiche simplement un état
  vide (« Aucun historique procédé enregistré »), puis se remplit dès le premier
  **Enregistrer** dans *Paramètres IA & feeders*.

---

## En cas de souci

| Symptôme | Action |
|----------|--------|
| `ModuleNotFoundError` | Vérifier que l'environnement virtuel est activé et `pip install -r requirements.txt` exécuté. |
| Le navigateur ne s'ouvre pas | Ouvrir manuellement `http://localhost:8501`. |
| Port occupé | `streamlit run app/Supervision.py --server.port 8502`. |
| Page Historique vide | Normal au premier lancement — voir « Données de démonstration » ci-dessus. |
