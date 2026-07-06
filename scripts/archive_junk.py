"""
archive_junk.py — Déplace (sans supprimer) les fichiers de travail non nécessaires
                  au livrable vers archive/. Réversible.

Tous ces fichiers sont DÉJÀ gitignorés et absents du ZIP : ce nettoyage ne change
pas le livrable, il range seulement le dossier de travail local.

  python scripts/archive_junk.py          # DRY-RUN : liste seulement
  python scripts/archive_junk.py --apply  # déplace réellement vers archive/
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive"

# Motifs racine sûrs (expériences de rendu vis, previews, captures) — cf. CLAUDE.md
GLOBS = [
    "debug_*.png", "debug_tile*.png",
    "preview_*.html", "preview_screw_new.py",
    "build_preview_screw.py", "build_preview_tests.py",
    "capture_test_screenshots.py",
]
# Anciens livrables mémoire/soutenance (remplacés par MBEUMI_Wilfried_THESE.*)
GLOBS_REPORTS = ["reports/Memoire_Rondol_*", "reports/Soutenance_Rondol_*",
                 "reports/Script_Soutenance_*"]

NEVER_MOVE = {"i18n_messages.py"}  # fichier applicatif tracké — ne jamais déplacer


def collect() -> list[Path]:
    out: list[Path] = []
    for g in GLOBS:
        out += [p for p in ROOT.glob(g) if p.is_file() and p.name not in NEVER_MOVE]
    for g in GLOBS_REPORTS:
        out += [p for p in ROOT.glob(g) if p.is_file()]
    return sorted(set(out))


def main() -> int:
    apply = "--apply" in sys.argv
    files = collect()
    print(f"{'APPLIQUE' if apply else 'DRY-RUN'} — {len(files)} fichiers candidats vers archive/\n")
    for p in files:
        print("  ", p.relative_to(ROOT).as_posix())
    if not apply:
        print("\n(DRY-RUN : rien déplacé. Relancer avec --apply pour exécuter.)")
        return 0
    ARCHIVE.mkdir(exist_ok=True)
    for p in files:
        dest = ARCHIVE / p.name
        p.rename(dest)
    print(f"\n[OK] {len(files)} fichiers déplacés vers {ARCHIVE} (réversible).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
