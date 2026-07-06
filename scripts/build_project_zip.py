"""
build_project_zip.py — Assemble le livrable MBEUMI_Wilfried_PROJET.zip (exigence guide RNCP).

Contenu (allowlist, sans __pycache__/.git/.venv ni binaires lourds) :
  - code source complet (app, AgentIndustrial_v1, engine, machine, materials,
    physics, src, tests, i18n_messages.py)
  - modèles entraînés (models/*.joblib) — nécessaires pour exécuter l'app
  - données : capteurs bruts (Essais_…/*.csv), features (data/features),
    état applicatif (data/run_state), historique (data/history)
  - dump SQL (database/rondol_state_dump.sql)
  - fichiers de configuration (requirements.txt, runtime.txt, .streamlit/*)
  - README / PDR (PDR_README.md, README.md)
  - rapports ML + benchmark (reports/ml_metrics_*.json, reports/sql_benchmark.json,
    reports/robustness_full_w60.json, feature_importance_*.csv)
  - captures de l'application (reports/memoire_captures/*)
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
    "scripts": {".py"},
    "tests": {".py"},
    "database": {".sql"},
    ".streamlit": {".toml", ".example"},
    "Essais_07-13_Avril_2026": {".csv"},
    "data/features": {".csv", ".json"},
    "data/run_state": {".json"},
    "data/history": {".json"},
    "models": {".joblib"},
    "reports/memoire_captures": {".png"},
}

# Fichiers individuels inclus
SINGLE_FILES = [
    "i18n_messages.py",
    "requirements.txt",
    "runtime.txt",
    "README.md",
    "PDR_README.md",
    "CLAUDE.md",
    "audit_conformite_RNCP_Rondol.md",
    "audit_final_application_Rondol_RNCP.md",
    "reports/ml_metrics_w60.json",
    "reports/ml_metrics_w30.json",
    "reports/ml_metrics_w120.json",
    "reports/ml_metrics_mlp_w60.json",
    "reports/model_comparison_logo_w60.json",
    "reports/augmentation_plan.md",
    "reports/augmentation_report.json",
    "reports/augmentation_eval.json",
    "reports/sql_benchmark.json",
    "reports/robustness_full_w60.json",
    "reports/ml_summary_w60.txt",
    "reports/runs_summary.csv",
    "reports/feature_importance_SVM_w60_threshold80.csv",
    "reports/feature_importance_RandomForest_w60.csv",
    "MBEUMI_Wilfried_THESE.pdf",
    "MBEUMI_Wilfried_PREZ.pdf",
]

EXCLUDE_DIR_PARTS = {"__pycache__", ".git", ".venv", ".pytest_cache", "node_modules"}

LIENS = """Liens du projet Rondol — thèse professionnelle RNCP 37137
========================================================
URL publique (application Streamlit) : [A COMPLETER PAR L'AUTEUR : https://<app>.streamlit.app]
Depot Git (code source)              : https://github.com/wilfried-mbeumi/rondol-process-supervision-demo
Dump SQL                             : database/rondol_state_dump.sql
README / PDR (installation, test, BDD, deploiement) : PDR_README.md

Base de donnees : PostgreSQL (Supabase). Table : rondol_state(key TEXT PRIMARY KEY, payload JSONB).
Identifiants de connexion (URL projet + cle API + mot de passe DB) : fournis separement, non versionnes (securite).
Application mono-utilisateur : aucun identifiant de connexion requis pour la tester (cf. PDR_README.md sec.7-8).
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
    print(f"[OK] {OUT.name} — {added} fichiers, {size_mb:.1f} Mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
