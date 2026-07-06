"""
config.py — Paramètres centraux du pipeline.

Tout ce qui est chemin, seuil, ou nom de capteur est ici pour faciliter
les ajustements sans toucher au code métier.
"""

from pathlib import Path

# ----------------------------------------------------------------------
# CHEMINS
# ----------------------------------------------------------------------
# Racine = dossier parent de src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Les CSV bruts restent à leur emplacement historique (on ne déplace rien).
DATA_RAW = PROJECT_ROOT / "Essais_07-13_Avril_2026"

# Sorties du pipeline
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_FEATURES = PROJECT_ROOT / "data" / "features"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ----------------------------------------------------------------------
# CAPTEURS
# ----------------------------------------------------------------------
# Correspondance nom court (colonne) → fichier CSV d'origine
SENSOR_FILES = {
    "Z1":           "TEMP_Z1_All_13_04_2026.csv",
    "Z2":           "TEMP_Z2_All_13_04_2026.csv",
    "Z3":           "TEMP_Z3_All_13_04_2026.csv",
    "Z4":           "TEMP_Z4_All_13_04_2026.csv",
    "Z5":           "TEMP_Z5_All_13_04_2026.csv",
    "Z6":           "TEMP_Z6_All_13_04_2026.csv",
    "Z7":           "TEMP_Z7_All_13_04_2026.csv",
    "Z8":           "TEMP_Z8_All_13_04_2026.csv",
    "DIE":          "TEMP_DIE_All_13_04_2026.csv",
    "CastFilmBody": "TEMP_CastFilmBody_All_13_04_2026.csv",
    "CastFilmP1":   "TEMP_CastFilmP1_All_13_04_2026.csv",
    "CastFilmP2":   "TEMP_CastFilmP2_All_13_04_2026.csv",
}
SENSORS = list(SENSOR_FILES.keys())

# Groupes sémantiques utiles pour features cross-capteurs
BARREL_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
DIE_SENSOR = "DIE"
CASTFILM_SENSORS = ["CastFilmBody", "CastFilmP1", "CastFilmP2"]

# ----------------------------------------------------------------------
# PREPROCESSING
# ----------------------------------------------------------------------
# Pas de temps de resampling (la sonde échantillonne 1-15 s → on uniformise)
RESAMPLE_PERIOD = "10s"        # 10 secondes
FFILL_LIMIT = 6                # combien de périodes on tolère en forward-fill (60 s)

# ----------------------------------------------------------------------
# SEGMENTATION DES ESSAIS
# ----------------------------------------------------------------------
# Critère "machine en production" : la filière est chaude.
# 120 °C choisi car :
#   - température de fusion typique des polymères extrudés (PVDF ~170, PEO ~65)
#   - au-dessus de 120 °C on est en régime de fonctionnement,
#     en dessous on est en chauffe ou refroidissement (hors production).
DIE_PRODUCTION_THRESHOLD_C = 120.0

# Durée en-dessous de laquelle un run est étiqueté "bad_run" (au lieu d'être
# supprimé). Il reste dans le dataset mais sera exclu du training principal.
BAD_RUN_DURATION_MIN = 15

# ----------------------------------------------------------------------
# FENÊTRAGE POUR EXTRACTION FEATURES
# ----------------------------------------------------------------------
WINDOW_SEC = 60    # durée d'une fenêtre d'analyse (s)
STEP_SEC = 30      # pas de décalage entre fenêtres (s) → 50 % d'overlap

# Tailles testées en comparaison (script compare_windows.py)
WINDOW_CANDIDATES = [30, 60, 120]

# ----------------------------------------------------------------------
# CIBLE DE STABILITÉ
# ----------------------------------------------------------------------
# Écart-type maximal toléré sur une fenêtre pour qu'un capteur soit "stable".
# 1,5 °C est une valeur conforme aux tolérances typiques des extrudeuses
# bivis de précision (±1-2 °C sur les zones régulées).
STABILITY_STD_MAX_C = 1.5

# Dérive (|slope| en °C/s) au-delà de laquelle on considère qu'un capteur
# est en train de dériver. 0,05 °C/s = 3 °C/min, correspond à une rampe
# de chauffe/refroidissement, pas à un régime stable.
STABILITY_SLOPE_MAX = 0.05

# Score global (0-100) au-dessus duquel la fenêtre est étiquetée "stable".
# Seuil 70 : doit dépasser 70 % du score parfait,
# compatible avec une exploitation industrielle "acceptable".
STABILITY_SCORE_THRESHOLD = 70.0
