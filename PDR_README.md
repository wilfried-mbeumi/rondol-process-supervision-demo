# PDR / README technique — Projet Rondol (thèse professionnelle RNCP 37137)

**Auteur :** Wilfried Galtier MBEUMI — Nexa Digital School (Mastère Data & IA)
**Entreprise :** Rondol Industrie · **Tuteur industriel :** M. Maël Gallas · **Référent école :** M. Moussa NDIAYE
**Projet :** Plateforme prédictive d'aide à la décision — extrusion bivis de composants de batteries tout-solide.

Ce document décrit les prérequis, l'installation, le lancement local, le déploiement
distant, les variables d'environnement, la connexion à la base de données, la procédure
de test et l'accès d'administration. Il accompagne le livrable `MBEUMI_Wilfried_PROJET.zip`.

---

## 1. Liens du projet

| Élément | Lien |
|---|---|
| **URL publique de l'application** (Streamlit Cloud) | `https://rondol-process-supervision-demo.streamlit.app` (vérifier que le partage est réglé sur « public » dans Streamlit Cloud avant le dépôt) |
| **Dépôt Git** (code source) | https://github.com/wilfried-mbeumi/rondol-process-supervision-demo |
| **Dump SQL** | `database/rondol_state_dump.sql` (inclus dans le ZIP) |

> La table de connexion à la base et les identifiants ne sont pas versionnés (sécurité).
> Voir §5 et §6 pour la configuration.

---

## 2. Prérequis d'installation

- **Python 3.13** (cf. `runtime.txt`).
- **pip** et un environnement virtuel (`venv`).
- Système : Windows 10/11, macOS ou Linux.
- Accès Internet pour l'installation des dépendances et (optionnel) la persistance Supabase.
- Dépendances applicatives : `streamlit`, `plotly`, `altair`, `Pillow`, `requests`, plus les
  dépendances ML de `requirements.txt` (`pandas`, `numpy`, `scipy`, `scikit-learn`, `xgboost`, `joblib`).

## 3. Étapes d'installation (local)

**Windows / PowerShell :**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install streamlit plotly altair Pillow requests
```

**macOS / Linux :**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install streamlit plotly altair Pillow requests
```

## 4. Lancement local

```bash
streamlit run app/Supervision.py
```

L'application s'ouvre sur **http://localhost:8501**. La page d'accueil est *Supervision* ;
les pages `app/pages/*` se montent automatiquement dans la barre latérale.

Lancement « headless » (vérification) :
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m streamlit run app/Supervision.py --server.headless=true --server.port=8765
# Santé : http://localhost:8765/_stcore/health
```

## 5. Déploiement distant (Streamlit Cloud)

1. Connecter le dépôt GitHub à **share.streamlit.io**.
2. Fichier principal : `app/Supervision.py`. Version Python : `runtime.txt` (3.13).
3. Renseigner les **secrets** (Settings ▸ Secrets) — voir §6.
4. L'application est servie sur une URL publique `https://<app>.streamlit.app`.

> **Disque éphémère :** Streamlit Cloud ne conserve pas les fichiers entre redémarrages.
> La persistance durable de l'état est donc déléguée à Supabase (§6), avec auto-réparation
> au démarrage (`app/persistence.py`).

## 6. Variables d'environnement et identifiants de connexion à la base

La persistance durable (PostgreSQL géré par **Supabase**) se configure via les secrets
Streamlit (`.streamlit/secrets.toml`) **ou** des variables d'environnement. Modèle fourni :
`.streamlit/secrets.toml.example`.

```toml
[supabase]
url   = "https://YOUR-PROJECT.supabase.co"   # URL du projet Supabase
key   = "YOUR-SERVICE-OR-ANON-KEY"           # clé d'API (identifiant de connexion REST)
# table = "rondol_state"                      # optionnel (défaut : rondol_state)
```

Équivalents par variables d'environnement :
```
RONDOL_SUPABASE_URL=...        RONDOL_SUPABASE_KEY=...        RONDOL_SUPABASE_TABLE=rondol_state
# Alternative hors cloud (store fichier durable) :
RONDOL_EXTERNAL_STORE_PATH=/mnt/data/rondol_applied_state.json
```

**Connexion / identifiants de la base SQL :**
- Moteur : **PostgreSQL** (service géré Supabase).
- Table : `rondol_state (key TEXT PRIMARY KEY, payload JSONB)`.
- Accès applicatif : **API REST Supabase** (clé `apikey` + `Authorization: Bearer <key>`).
- Accès SQL direct (psql) : chaîne `DATABASE_URL` du projet Supabase
  (`postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres`).
- Rejouer le dump : `psql "$DATABASE_URL" -f database/rondol_state_dump.sql`.

> Les valeurs réelles (URL projet, clés, mot de passe DB) sont **secrètes** et ne sont pas
> versionnées. Elles sont fournies séparément au jury si une connexion live est requise :
> `[À COMPLÉTER PAR L'AUTEUR — uniquement dans la copie de ce fichier incluse dans le ZIP de dépôt : url + clé anon Supabase du projet de démonstration. Ne jamais committer ces valeurs dans le dépôt public ; les révoquer après la soutenance.]`.

## 7. Procédure de test / identifiants de test

L'application est **mono-utilisateur** et **ne requiert pas d'authentification** (pas de
compte ni de mot de passe utilisateur) : aucun identifiant de connexion n'est nécessaire
pour la tester. Parcours de test (5 min) — cf. `docs/DEMO_MANAGER.md` :

1. Lancer `streamlit run app/Supervision.py`.
2. *Supervision* : lire l'état machine, le score de stabilité (RandomForest augmenté), la probabilité de
   dérive, les alertes et recommandations ; changer de run/fenêtre dans la barre latérale.
3. Basculer la langue **FR / EN**.
4. *Configuration procédé* : charger une configuration, ajouter des éléments (+1/+4),
   observer les indicateurs (remplissage, résidence, volumes).
5. *Paramètres IA & feeders* : ajuster une consigne, **Enregistrer**, puis vérifier la
   persistance dans *Historique* et *Moteur Procédé*.

**Tests automatisés** (~695 tests collectés) :
```powershell
python -m pytest tests/ -q
# sous-ensemble rapide (moteur pur) :
python -m pytest tests/ -q --ignore=tests/test_streamlit_pages.py --ignore=tests/test_render_smoke.py
```
> **Note d'honnêteté (test sensible à l'ordre d'exécution)** : sur une exécution complète, la suite donne
> **694 passed**. Un test E2E de redémarrage/synchronisation reste **sensible à l'ordre d'exécution**
> en suite complète (**fragilité d'isolation/timing de la couche E2E Streamlit `AppTest`** — état disque
> partagé au niveau session + rendu lourd sous charge), **pas un défaut applicatif** : le test
> **passe systématiquement en isolation et en réexécution** :
> ```powershell
> python -m pytest tests/test_e2e_client_sync.py::test_history_has_same_snapshot -q   # 1 passed
> ```

## 8. Accès administrateur / back-office

Le prototype **ne comporte pas de back-office applicatif** : il s'agit d'un outil
d'aide à la décision mono-poste, sans gestion d'utilisateurs ni rôles. Cette absence est
un **choix assumé** cohérent avec le périmètre de démonstration (un opérateur à la fois).

Le rôle d'« administration des données » est tenu par la **console Supabase**
(dashboard PostgreSQL : éditeur de table, requêtes SQL, logs), qui fait office de
back-office de données. L'accès y est protégé par le compte propriétaire du projet
Supabase : `[À COMPLÉTER : accès console Supabase de démonstration si fourni au jury]`.

## 9. Compatibilité multi-navigateur

L'interface est rendue par Streamlit (HTML/CSS standard) et a été utilisée sur navigateurs
récents (Chrome, Edge, Firefox). Les panneaux de l'agent sont conçus *DOM-stable* pour
éviter les erreurs de re-rendu (`removeChild`) connues de Streamlit. Aucune dépendance à
une extension navigateur n'est requise.

## 10. Fichiers de configuration inclus

| Fichier | Rôle |
|---|---|
| `requirements.txt` | Dépendances ML du pipeline |
| `runtime.txt` | Version Python (déploiement) |
| `.streamlit/config.toml` | Thème et options Streamlit |
| `.streamlit/secrets.toml.example` | Modèle de configuration de la persistance (à dupliquer, non versionné en réel) |
| `src/config.py` | Paramètres du pipeline data/ML (capteurs, fenêtres, seuils) |
| `database/rondol_state_dump.sql` | Dump SQL réel de la base de persistance |

## 11. Limites connues et réserves (transparence)

- **Persistance durable conditionnée aux secrets Supabase.** Sans secrets configurés,
  l'application fonctionne mais retombe sur un fichier JSON local **non durable**
  (`backend_name()='local-json'`, `is_durable()=False`) : l'état peut être perdu après un
  reboot/redeploy Cloud. Avec les secrets (`[supabase]` ou variables `RONDOL_SUPABASE_*`),
  la persistance devient durable (`backend_name()='supabase'`, `is_durable()=True`).
  **Preuve** : `python scripts/verify_supabase.py` (round-trip réel, clé API masquée).
- **URL publique Streamlit** : à renseigner par l'auteur dans `LIENS_URLS.txt` et §1.
- **Score ML** : calculé sur des **fenêtres capteurs enregistrées** (campagne avril 2026),
  pas sur la configuration de vis éditée en direct (qui pilote l'agent à règles + les KPIs).
- **Test E2E flaky** : cf. §7 (isolation/timing, non bloquant).
- **Dépôt Git « vitrine »** : `.gitignore` exclut `src/`, `scripts/`, `*.pdf/*.docx/*.zip` ;
  le **code source complet** (pipeline ML + scripts) est livré dans `MBEUMI_Wilfried_PROJET.zip`.
