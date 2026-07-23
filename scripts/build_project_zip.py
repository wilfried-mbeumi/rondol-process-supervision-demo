"""
build_project_zip.py — Assemble le livrable MBEUMI_Wilfried_PROJET.zip (exigence guide RNCP).

Périmètre STRICT : uniquement ce qui sert à créer, exécuter, comprendre ou
redéployer l'application (per guide « Partie 1.viii — Développement d'une
application » + « URL, code source complet, dump SQL, config, README/PDR »).

Le mémoire (PDF), le support de soutenance (PPTX), le guide de révision et le
notebook d'analyse sont des livrables DISTINCTS, déposés séparément sur Teams
(NOM_PRENOM_THESE.pdf, NOM_PRENOM_PREZ.pdf) — ils n'ont pas leur place dans un
ZIP de code source, et n'y figurent donc plus.

Contenu (allowlist, sans __pycache__/.git/.venv ni binaires lourds) :
  - code source complet (app, AgentIndustrial_v1, engine, machine, materials,
    physics, src, tests, i18n_messages.py, scripts d'exploitation courants)
  - modèles entraînés (models/*.joblib) — nécessaires pour exécuter l'app
  - données runtime : capteurs bruts, features ML, état applicatif, historique
  - dump SQL (database/*.sql — état procédé + tables d'authentification)
  - fichiers de configuration (requirements.txt, runtime.txt, .streamlit/*)
  - README / PDR (PDR_README.md, README.md)
  - les 3 rapports effectivement LUS par l'app au runtime (app/pages/2_Settings.py) :
    ml_metrics_w60.json, threshold_calibration_w60.csv, feature_importance_RandomForest_w60.csv
  - LIENS_URLS.txt (URL publique + URL Git)

Usage : python scripts/build_project_zip.py
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "MBEUMI_Wilfried_PROJET.zip"

# Dossiers de code/données inclus récursivement (extensions filtrées)
DIR_RULES = {
    "app": {".py", ".toml"},
    "AgentIndustrial_v1": {".py"},
    "engine": {".py"},
    "machine": {".py"},
    "materials": {".py"},
    "physics": {".py"},
    "src": {".py"},
    "tests": {".py"},
    "database": {".sql"},
    ".streamlit": {".toml", ".example"},
    "Essais_07-13_Avril_2026": {".csv"},
    "data/features": {".csv", ".json"},
    "data/run_state": {".json"},
    "data/history": {".json"},
    "models": {".joblib"},
}

# Scripts d'exploitation courants (setup, dépôt) — hors générateurs de
# livrables mémoire/soutenance (build_memoire_*, build_notebook_*,
# capture_memoire_*, build_deck_*, check_sync_livrables, etc., qui restent
# dans scripts/ pour le dépôt Git mais ne sont pas requis pour l'app).
SCRIPT_FILES = [
    "scripts/seed_user.py",
    "scripts/seed_demo_state.py",
    "scripts/verify_supabase.py",
    "scripts/generate_sql_dump.py",
    "scripts/build_project_zip.py",
    "scripts/inject_depot_secrets.py",
]

# Fichiers individuels inclus
SINGLE_FILES = [
    "i18n_messages.py",
    "requirements.txt",
    "runtime.txt",
    "README.md",
    "PDR_README.md",
    # Les 3 seuls rapports effectivement lus par l'app au runtime
    # (app/pages/2_Settings.py) — le reste de reports/ documente le mémoire
    # et le notebook, hors périmètre de ce ZIP.
    "reports/ml_metrics_w60.json",
    "reports/threshold_calibration_w60.csv",
    "reports/feature_importance_RandomForest_w60.csv",
] + SCRIPT_FILES

EXCLUDE_DIR_PARTS = {"__pycache__", ".git", ".venv", ".pytest_cache", "node_modules"}

LIENS = """Liens du projet Rondol — these professionnelle RNCP 37137
========================================================
URL publique (application Streamlit) : https://rondol-process-supervision-demo.streamlit.app
Depot Git (code source)              : https://github.com/wilfried-mbeumi/rondol-process-supervision-demo
Dump SQL                             : database/rondol_state_dump.sql (etat procede) + database/auth_tables.sql (authentification)
README / PDR (installation, test, BDD, deploiement) : PDR_README.md

Base de donnees : PostgreSQL (Supabase).
  - Table rondol_state(key TEXT PRIMARY KEY, payload JSONB) : etat procede validé.
  - Tables app_users / login_history : authentification (mot de passe hache PBKDF2, jamais en clair).
Identifiants de connexion (URL projet + cle API) : fournis separement, non versionnes (securite).
Identifiants de test de l'application : voir PDR_README.md section 7 (email/mot de passe demo).
"""


def _excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIR_PARTS for part in path.parts)


def main() -> int:
    added = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        # LIENS_URLS.txt — préférer le fichier racine (complété) sinon l'embarqué
        root_liens = ROOT / "LIENS_URLS.txt"
        if root_liens.exists():
            z.write(root_liens, "LIENS_URLS.txt")
        else:
            z.writestr("LIENS_URLS.txt", LIENS)
        added += 1

        for rel, exts in DIR_RULES.items():
            base = ROOT / rel
            if not base.exists():
                print(f"[WARN] absent : {rel}")
                continue
            for f in base.rglob("*"):
                if f.is_file() and not _excluded(f) and f.suffix.lower() in exts:
                    z.write(f, f.relative_to(ROOT).as_posix())
                    added += 1

        for rel in SINGLE_FILES:
            f = ROOT / rel
            if f.exists():
                z.write(f, f.relative_to(ROOT).as_posix())
                added += 1
            else:
                print(f"[WARN] fichier absent : {rel}")

    size_mb = OUT.stat().st_size / 1e6
    print(f"[OK] {OUT.name} — {added} fichiers, {size_mb:.1f} Mo (perimetre : code + config, hors memoire/soutenance/notebook)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
