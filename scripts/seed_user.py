# -*- coding: utf-8 -*-
"""Crée (ou met à jour) un utilisateur autorisé de la plateforme Rondol.

Le mot de passe en clair ne transite QUE par ce script, au moment du seed :
il est immédiatement haché (PBKDF2) avant écriture. Rien n'est committé.

Sources des valeurs (par ordre de priorité) :
  1. arguments CLI :  --email demo@rondol.local --password 0000
  2. fichier local `.streamlit/secrets_depot.txt` (git-ignoré), clés :
         auth_email = demo@rondol.local
         auth_password = 0000
         url = https://xxxx.supabase.co     # (déjà présent pour le dépôt)
         key = sb_publishable_...            # (idem)

Si `url` et `key` Supabase sont disponibles, l'utilisateur est écrit dans la
table `app_users` de Supabase (production). Sinon, repli fichier local
(`data/auth/users.json`) pour le dev.

Prérequis Supabase : avoir créé les tables via database/auth_tables.sql.

Usage :
    python scripts/seed_user.py
    python scripts/seed_user.py --email demo@rondol.local --password 0000
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
SECRETS = ROOT / ".streamlit" / "secrets_depot.txt"


def _read_secrets_file() -> dict[str, str]:
    vals: dict[str, str] = {}
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            # tolère les guillemets éventuels autour de la valeur (style TOML)
            vals[k.strip().lower()] = v.strip().strip('"').strip("'")
    return vals


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed d'un utilisateur autorisé Rondol.")
    ap.add_argument("--email")
    ap.add_argument("--password")
    args = ap.parse_args()

    fromfile = _read_secrets_file()
    email = args.email or fromfile.get("auth_email") or "demo@rondol.local"
    password = args.password or fromfile.get("auth_password")
    if not password:
        sys.exit(
            "Mot de passe manquant. Fournis --password, ou ajoute\n"
            "  auth_password = ...\n"
            f"dans {SECRETS}."
        )

    # Cibler Supabase si les identifiants du projet sont dans le fichier local.
    if fromfile.get("url") and fromfile.get("key"):
        os.environ.setdefault("RONDOL_SUPABASE_URL", fromfile["url"])
        os.environ.setdefault("RONDOL_SUPABASE_KEY", fromfile["key"])

    import auth  # noqa: E402  (après ajout du chemin app/)

    backend = auth.upsert_user(email, password)
    print(f"Utilisateur « {email} » enregistré (backend : {backend}).")
    if backend == "supabase":
        print("→ Vérifie côté Supabase : SELECT email, created_at FROM app_users;")
    else:
        print(f"→ Fichier local : {ROOT / 'data' / 'auth' / 'users.json'}")
    # Contrôle immédiat.
    ok = auth.verify_credentials(email, password)
    print("Vérification des identifiants :", "OK" if ok else "ÉCHEC")
    if not ok:
        sys.exit("Le contrôle post-seed a échoué — vérifie les tables Supabase / la clé.")


if __name__ == "__main__":
    main()
