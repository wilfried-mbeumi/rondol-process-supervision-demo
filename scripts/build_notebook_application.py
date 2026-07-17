# -*- coding: utf-8 -*-
"""Construit et exécute le notebook explicatif de l'application Rondol.

Sortie : notebooks/notebook_application_rondol.ipynb (cellules exécutées).
"""
import nbformat as nbf
from nbclient import NotebookClient
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md = lambda s: nb.cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: nb.cells.append(nbf.v4.new_code_cell(s))

md("""# Plateforme prédictive Rondol — notebook d'accompagnement

Ce notebook documente, de façon exécutable, les trois piliers du prototype développé
pendant le stage chez Rondol : le **moteur procédé** (géométrie de vis et physique
nominale), les **données machine** (campagne d'essais d'avril 2026 puis base
consolidée), et le **modèle de Machine Learning** intégré à la supervision.

Chaque section s'appuie sur le code réellement déployé dans l'application
(`app/`, `engine/`, `src/`) — rien n'est recalculé « à part » : ce que montre ce
notebook est ce que montre l'application.

*Rappel de cadrage : les grandeurs physiques sont nominales, non calibrées
industriellement. L'outil sert à comparer des configurations, pas à produire des
valeurs certifiées.*""")

md("""## 1. Le moteur procédé : de la géométrie de vis aux indicateurs

La vis est décrite par 81 positions (13 types d'éléments : convoyage, malaxage,
restriction…). Le module `screw_logic` est l'unique source de vérité géométrique ;
il calcule le taux de remplissage, le débit volumique et le temps de résidence.""")

code("""import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT / "app")]

import screw_logic

# Configuration de démonstration : vis remplie d'éléments de convoyage entiers
# (type 1 sur deux positions), tip+discharge imposé en fin de vis.
config = screw_logic.new_empty_configuration()
for i in range(1, 79, 2):
    if config[i] == 0 and i + 1 < 79:
        config[i], config[i + 1] = 1, 101

params = screw_logic.ProcessParams(
    screw_rpm=200.0,
    feeder1_flow_rate_g_per_s=0.33,   # ≈ 1,2 kg/h
    feeder1_bulk_density=0.55,        # densité apparente poudre LFP semi-sèche
)
state = screw_logic.compute_process_state(config, params)
vf = [v for v in state.vol_flow_cm3_s if v]
print("Débit volumique (moyen sur positions actives) :", round(sum(vf)/len(vf), 3), "cm³/s")
print("Résidence totale  :", round(state.residence_time_total, 1), "s")
print("Remplissage moyen :", round(state.fill_factor_average, 3))""")

md("""Au-dessus de ce socle, la couche `engine/` enrichit chaque position : viscosité
locale (Carreau-Yasuda + Arrhenius), couple élémentaire, agrégats par zone. Le
principe d'architecture est d'**envelopper sans recalculer** : le réseau
géométrique n'est exécuté qu'une seule fois par configuration.""")

md("""## 2. Les données : de la campagne d'essais à la base consolidée

La campagne du 07 au 13 avril 2026 a produit 52 064 lignes brutes (12 capteurs de
température, pas de 10 s) avec une couverture fragmentée. Deux jeux en sont
dérivés : le dataset fenêtré (798 fenêtres de 60 s, 87 variables) qui a servi à
l'entraînement, et la base consolidée continue (100 800 lignes) construite en
calibrant chaque distribution sur les mesures réelles.""")

code("""import pandas as pd
df = pd.read_csv(ROOT / "data/consolidated/dataset_consolide_rondol.csv", parse_dates=["timestamp"])
print(df.shape)
df[["timestamp","Z4","Z8","DIE","screw_rpm","feed_rate_gph","torque_pct","phase","recipe"]].sample(6, random_state=7)""")

code("""%matplotlib inline
import matplotlib.pyplot as plt

day = df[(df.timestamp >= "2026-04-08") & (df.timestamp < "2026-04-09")]
fig, axes = plt.subplots(2, 1, figsize=(11, 5.5), sharex=True)
for z in ["Z2","Z4","Z6","Z8"]:
    axes[0].plot(day.timestamp, day[z].where(day[z] < 400), lw=0.8, label=z)
axes[0].set_ylabel("Température (°C)"); axes[0].legend(ncol=4, fontsize=8); axes[0].set_title("Journée d'essais du 8 avril — zones de chauffe")
axes[1].plot(day.timestamp, day.screw_rpm, lw=0.8, color="teal")
axes[1].set_ylabel("Vis (tr/min)")
plt.tight_layout(); plt.show()""")

code("""run = df[df.phase == "run"]
num = run[["screw_rpm","feed_rate_gph","torque_pct","Z6","Z7","Z8"]]
num = num[num < 3000]  # exclure le code d'erreur thermocouple 3276,7
num.corr().round(2)""")

md("""On retrouve les corrélations physiques attendues : le couple croît avec le débit
d'alimentation et décroît quand la température de fusion monte (la viscosité
chute), et les zones adjacentes sont fortement corrélées — exactement comme dans
les mesures brutes de la campagne.""")

md("""## 3. Le modèle de Machine Learning intégré à la supervision

Trois familles de modèles ont été comparées (RandomForest, XGBoost, SVM) sur les
fenêtres de 60 s, avec une validation stricte **par run d'essai**
(GroupShuffleSplit) : un run vu à l'entraînement ne peut pas servir au test.
Le RandomForest entraîné sur données augmentées est le modèle retenu et déployé.""")

code("""import json
metrics = json.load(open(ROOT / "reports/ml_metrics_w60.json"))
pd.DataFrame(metrics["test"]).T[["accuracy","f1_macro","f1_unstable","roc_auc"]].round(3)""")

code("""import joblib
model = joblib.load(ROOT / "models/RandomForest_w60_augmented.joblib")
est = model.named_steps.get("clf", model) if hasattr(model, "named_steps") else model
feat = pd.read_csv(ROOT / "data/features/dataset_ml_w60.csv", nrows=1)
cols = [c for c in feat.columns if c not in ("label","run_id","t_start","t_end")]
try:
    imp = pd.Series(est.feature_importances_, index=cols[:len(est.feature_importances_)]).sort_values(ascending=False)[:12]
    ax = imp[::-1].plot.barh(figsize=(8,4.5), color="teal", title="RandomForest retenu — 12 variables les plus importantes")
    ax.set_xlabel("Importance"); plt.tight_layout(); plt.show()
except Exception as e:
    print("Importances non disponibles pour ce pipeline :", type(est).__name__, e)""")

md("""Les variables dominantes sont des mesures de dispersion et de pente sur les zones
aval — cohérent avec l'intuition procédé : une dérive s'annonce par une
instabilité thermique près de la filière avant de se voir sur les moyennes.

### Validation externe sur la base simulée

La base consolidée a été passée dans le même pipeline de fenêtrage et de
labellisation que les données réelles, puis le modèle déployé a été évalué
dessus **sans réentraînement** (`scripts/evaluate_on_consolidated.py`). Le
résultat n'a volontairement pas été optimisé : l'écart avec les performances
sur essais réels documente honnêtement la sensibilité au changement de
distribution.""")

code("""ext = json.load(open(ROOT / "reports/eval_consolidated_w60.json"))
pd.Series(ext).drop("confusion_matrix").to_frame("validation externe (base simulée)")""")

md("""## 4. Ce que fait l'application avec tout cela

- **Supervision** : le modèle produit un score de stabilité et une probabilité de
  dérive ; l'agent à règles expliquant chaque alerte reste décisionnaire.
- **Configuration** : chaque profil de vis est recalculé par le moteur et ses KPIs
  sont figés à l'enregistrement (persistance à trois couches : édition → validé →
  historique).
- **Analyse de run / Historique** : relecture des productions passées avec les
  mêmes calculs que le direct.

Pour lancer l'application : `streamlit run app/Supervision.py`.""")

out = ROOT / "notebooks" / "notebook_application_rondol.ipynb"
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
client = NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(ROOT / "notebooks")}})
client.execute()
nbf.write(nb, out)
print("OK", out)
