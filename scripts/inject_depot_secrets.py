# -*- coding: utf-8 -*-
"""Injecte les secrets Supabase dans la copie PDR du ZIP de dépôt — sans jamais
les committer ni les exposer.

FLUX (tes valeurs ne passent que par TON disque) :
  1. Crée le fichier local `.streamlit/secrets_depot.txt` (git-ignoré) :

         url = https://TON-PROJET.supabase.co
         key = TA-CLE-ANON
         console = https://supabase.com/dashboard/project/xxxx   (optionnel)

  2. Lance :  python scripts/inject_depot_secrets.py

Le script :
  - lit ces valeurs depuis le fichier local,
  - régénère d'abord le ZIP propre (sans secret) via build_project_zip,
  - remplace, DANS LE ZIP uniquement, le PDR_README.md par une version où les
    emplacements « [À COMPLÉTER…] » sont remplis avec tes valeurs.

Le dépôt (MBEUMI_Wilfried_PROJET.zip) contient alors les secrets ; le dépôt
Git, lui, garde le PDR avec les placeholders. Après la soutenance : révoque la
clé anon dans la console Supabase (Settings > API).
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / ".streamlit" / "secrets_depot.txt"
ZIP = ROOT / "MBEUMI_Wilfried_PROJET.zip"
PDR_NAME = "PDR_README.md"


def _read_secrets() -> dict[str, str]:
    if not SECRETS.exists():
        sys.exit(
            f"Fichier introuvable : {SECRETS}\n"
            "Crée-le avec les lignes :\n"
            "  url = https://TON-PROJET.supabase.co\n"
            "  key = TA-CLE-ANON\n"
            "  console = ...   (optionnel)"
        )
    vals: dict[str, str] = {}
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip().lower()] = v.strip()
    if not vals.get("url") or not vals.get("key"):
        sys.exit("Le fichier doit contenir au moins 'url = ...' et 'key = ...'.")
    return vals


def _fill_pdr(pdr_text: str, s: dict[str, str]) -> str:
    # Bloc §6 (connexion base)
    bloc6 = (
        "```toml\n[supabase]\n"
        f'url = "{s["url"]}"\n'
        f'key = "{s["key"]}"\n'
        "```\n"
        "> Ces valeurs sont fournies pour la seule évaluation ; la clé anon sera "
        "révoquée après la soutenance."
    )
    pdr_text = re.sub(
        r"> `\[À COMPLÉTER PAR L'AUTEUR[^`]*`\]?\.?",
        bloc6.replace("\\", r"\\"),
        pdr_text,
    )
    # §8 console (optionnel)
    console = s.get("console", "").strip()
    repl8 = console if console else "Accès console fourni sur demande lors de la soutenance."
    pdr_text = re.sub(
        r"`\[À COMPLÉTER : accès console Supabase[^`]*`",
        f"`{repl8}`",
        pdr_text,
    )
    return pdr_text


def main() -> None:
    s = _read_secrets()

    # 1. ZIP propre (sans secret) régénéré à neuf.
    print("[1/3] Régénération du ZIP propre…")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_project_zip.py")],
                   check=True, cwd=str(ROOT))

    if not ZIP.exists():
        sys.exit("ZIP introuvable après build_project_zip.")

    # 2. Localiser et remplir le PDR à l'intérieur du ZIP.
    print("[2/3] Injection des secrets dans la copie PDR du ZIP…")
    src = zipfile.ZipFile(ZIP, "r")
    member = next((n for n in src.namelist() if n.endswith(PDR_NAME)), None)
    if member is None:
        sys.exit(f"{PDR_NAME} absent du ZIP.")
    filled = _fill_pdr(src.read(member).decode("utf-8"), s)

    # 3. Réécrire le ZIP en remplaçant ce seul membre.
    print("[3/3] Réécriture du ZIP…")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            data = filled.encode("utf-8") if item.filename == member else src.read(item.filename)
            out.writestr(item, data)
    src.close()
    ZIP.write_bytes(buf.getvalue())

    # Contrôle : plus de placeholder, secret présent.
    check = zipfile.ZipFile(ZIP, "r").read(member).decode("utf-8")
    assert "À COMPLÉTER PAR L'AUTEUR" not in check, "placeholder §6 non remplacé"
    assert s["url"] in check, "url absente après injection"
    print(f"\nOK — {ZIP.name} contient désormais les secrets dans {PDR_NAME}.")
    print("Rappel : ne PAS committer ce ZIP ; révoquer la clé anon après la soutenance.")


if __name__ == "__main__":
    main()
