# -*- coding: utf-8 -*-
"""Assemble les parties 6-8 + clôture (sortie workflow) dans le Markdown source."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "memoire_these_professionnelle_rondol.md"
OUT = Path(
    r"C:\Users\wilfr\AppData\Local\Temp\claude\C--Users-wilfr-OneDrive-rondol-ia-project"
    r"\30957764-ba58-4ae5-aaed-09c17f03ca9c\tasks\wps2u0aio.output"
)


def clean(txt: str) -> str:
    t = (txt or "").strip()
    t = t.replace("```markdown", "").replace("```", "")
    # supprime tout préambule avant le premier titre de niveau 1
    if not t.startswith("# "):
        idx = t.find("\n# ")
        if idx != -1:
            t = t[idx + 1:]
    return t.strip()


def main() -> None:
    data = json.loads(OUT.read_text(encoding="utf-8"))
    res = data.get("result", data)
    parts = [clean(res[k]) for k in ("part6", "part7", "part8", "closing")]

    for p in parts:
        print("----", p[:90].replace("\n", " "), "...")

    md = MD.read_text(encoding="utf-8")
    cut = md.find("*Fin du contenu")
    if cut != -1:
        md = md[:cut]
    lines = md.split("\n")
    while lines and lines[-1].strip() in ("", "---", "[SAUT DE PAGE]"):
        lines.pop()
    md = "\n".join(lines)

    for p in parts:
        md += "\n\n[SAUT DE PAGE]\n\n" + p
    md += "\n"

    MD.write_text(md, encoding="utf-8")
    print(f"\nMarkdown assemblé : {MD} ({len(md)} caractères)")


if __name__ == "__main__":
    main()
