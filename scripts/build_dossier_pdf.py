"""build_dossier_pdf.py — Rend le dossier de soutenance en PDF composés.

Source : reports/soutenance/DOSSIER_FINAL/_source/*.md
Sortie : reports/soutenance/DOSSIER_FINAL/*.pdf

Chaîne : Markdown -> HTML + CSS print -> PDF via Chrome/Edge headless.
Passer par le CSS plutôt que par Word donne le contrôle typographique réel :
grille de page, hiérarchie, tableaux composés, et surtout un traitement distinct
pour les répliques à dire à voix haute — c'est ce que le candidat lit en
situation, ça ne doit pas ressembler au reste du texte.

Ce script met en page. Il ne réécrit aucun contenu et ne recalcule aucun chiffre.

Usage : python scripts/build_dossier_pdf.py
"""
from __future__ import annotations

import html as _html
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "reports" / "soutenance" / "DOSSIER_FINAL"
SRC = DEST / "_source"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]

# (source, pdf, numéro de bloc affiché, titre de couverture, sous-titre)
DOCS = [
    ("00_LIRE_DABORD.md", "0 - Lire d'abord.pdf",
     "00", "Lire d'abord", "Vue d'ensemble des 90 minutes · plan de révision · grille de capture"),
    ("01_PRESENTATION_30MIN.md", "1 - Presentation 30 min.pdf",
     "01", "Présentation", "30 minutes sans interruption · 27 diapositives · démonstration live"),
    ("02_QUESTIONS_REPONSES_15MIN.md", "2 - Questions du jury 15 min.pdf",
     "02", "Questions du jury", "15 minutes · dix-huit questions préparées"),
    ("03_ENTRETIEN_PRO_15MIN.md", "3 - Entretien professionnel 15 min.pdf",
     "03", "Entretien professionnel", "15 minutes · parcours, posture, projection"),
    ("04_JEU_DE_ROLE_30MIN.md", "4 - Jeu de role 30 min.pdf",
     "04", "Jeu de rôle", "30 minutes · six scénarios client · objections et réclamations"),
    ("05_ANTISECHE_A4.md", "5 - Antiseche a imprimer.pdf",
     "05", "Antisèche", "La seule feuille à emporter · recto-verso"),
    ("06_CHECKLIST_JOUR_J.md", "6 - Checklist jour J.pdf",
     "06", "Checklist jour J", "La veille · 30 minutes avant · pendant l'épreuve"),
]

CANDIDATE = "Wilfried Galtier MBEUMI"
EVENT = "Soutenance · 9 septembre 2026"

# ---------------------------------------------------------------- CSS

CSS = r"""
@page {
  size: A4;
  margin: 17mm 15mm 16mm 15mm;
}
@page :first { margin: 0; }

:root {
  --ink:      #14202E;
  --ink-soft: #46525F;
  --muted:    #77828E;
  --rule:     #DFE4E8;
  --teal:     #0D9488;
  --teal-pale:#EAF4F2;
  --amber:    #B45309;
  --amber-pale:#FDF4E7;
  --red:      #B0201C;
  --red-pale: #FBEDEC;
}

* { box-sizing: border-box; }

html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }

body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 10.2pt;
  line-height: 1.55;
  color: var(--ink);
  text-rendering: geometricPrecision;
}

/* ---------------- couverture ---------------- */
.cover {
  height: 297mm;
  padding: 42mm 22mm 22mm;
  page-break-after: always;
  position: relative;
  background: #FBFCFC;
}
.cover-rule {
  position: absolute; top: 0; left: 0; right: 0; height: 7mm;
  background: var(--teal);
}
.cover-num {
  font-family: "Segoe UI", sans-serif;
  font-size: 76pt;
  font-weight: 200;
  color: var(--teal);
  line-height: 0.9;
  letter-spacing: -2pt;
}
.cover-kicker {
  font-family: "Segoe UI", sans-serif;
  font-size: 8.5pt;
  font-weight: 600;
  letter-spacing: 2.4pt;
  text-transform: uppercase;
  color: var(--muted);
  margin: 14mm 0 3mm;
}
.cover h1 {
  font-family: "Segoe UI", sans-serif;
  font-size: 31pt;
  font-weight: 600;
  line-height: 1.1;
  color: var(--ink);
  margin: 0 0 5mm;
  letter-spacing: -0.4pt;
}
.cover-sub {
  font-size: 12pt;
  color: var(--ink-soft);
  font-style: italic;
  max-width: 118mm;
  margin: 0;
}
.cover-foot {
  position: absolute;
  left: 22mm; right: 22mm; bottom: 22mm;
  padding-top: 4mm;
  border-top: 0.6pt solid var(--rule);
  font-family: "Segoe UI", sans-serif;
  font-size: 9pt;
  color: var(--muted);
  display: flex;
  justify-content: space-between;
}
.cover-foot strong { color: var(--ink); font-weight: 600; }

/* ---------------- titres ---------------- */
h1, h2, h3, h4 {
  font-family: "Segoe UI", sans-serif;
  color: var(--ink);
  page-break-after: avoid;
  break-after: avoid;
}
h1 {
  font-size: 17pt; font-weight: 600;
  margin: 0 0 5mm; padding-bottom: 2.5mm;
  border-bottom: 1.6pt solid var(--teal);
  letter-spacing: -0.2pt;
}
h1 + * { margin-top: 0; }
h2 {
  font-size: 13pt; font-weight: 600;
  margin: 8mm 0 3mm;
  color: var(--teal);
  letter-spacing: -0.1pt;
}
h3 {
  font-size: 11pt; font-weight: 600;
  margin: 6mm 0 2mm;
}
h4 {
  font-size: 10pt; font-weight: 600;
  margin: 4.5mm 0 1.5mm; color: var(--ink-soft);
}

p { margin: 0 0 2.6mm; orphans: 2; widows: 2; }
strong { font-weight: 700; }
em { font-style: italic; color: var(--ink-soft); }
del { color: var(--muted); }

code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.87em;
  background: #F2F5F6;
  padding: 0.4mm 1.1mm;
  border-radius: 1mm;
}

hr {
  border: 0; border-top: 0.6pt solid var(--rule);
  margin: 6mm 0;
}

ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.2mm; padding-left: 0.6mm; }
li::marker { color: var(--teal); }

/* ---------------- réplique à dire ---------------- */
blockquote {
  margin: 3mm 0 3.6mm;
  padding: 3mm 4mm 3mm 5mm;
  border-left: 2.2pt solid var(--teal);
  background: var(--teal-pale);
  font-size: 10.6pt;
  line-height: 1.6;
  page-break-inside: avoid;
}
blockquote p { margin: 0 0 1.8mm; }
blockquote p:last-child { margin-bottom: 0; }

/* variantes sémantiques */
blockquote.warn { border-left-color: var(--amber); background: var(--amber-pale); }
blockquote.alert { border-left-color: var(--red); background: var(--red-pale); }

.callout {
  margin: 3mm 0;
  padding: 2.6mm 3.4mm;
  border-left: 2.2pt solid var(--amber);
  background: var(--amber-pale);
  font-family: "Segoe UI", sans-serif;
  font-size: 9.4pt;
  page-break-inside: avoid;
}
.callout.danger { border-left-color: var(--red); background: var(--red-pale); }
.callout.info   { border-left-color: var(--teal); background: var(--teal-pale); }

/* ---------------- tableaux ---------------- */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4.5mm;
  font-family: "Segoe UI", sans-serif;
  font-size: 8.9pt;
  font-variant-numeric: tabular-nums;
  page-break-inside: avoid;
}
thead th {
  text-align: left;
  font-weight: 600;
  font-size: 7.8pt;
  letter-spacing: 0.7pt;
  text-transform: uppercase;
  color: var(--muted);
  background: #F4F7F7;
  padding: 2mm 2.4mm;
  border-bottom: 1.1pt solid var(--teal);
}
tbody td {
  padding: 1.9mm 2.4mm;
  border-bottom: 0.5pt solid var(--rule);
  vertical-align: top;
  line-height: 1.42;
}
tbody tr:nth-child(even) td { background: #FAFBFB; }
table.noheader tbody tr:first-child td { border-top: 1.1pt solid var(--teal); }
tbody tr:last-child td { border-bottom: 0.9pt solid var(--rule); }

/* ---------------- cases à cocher ---------------- */
.check {
  margin: 0 0 1.5mm;
  padding-left: 6.5mm;
  text-indent: -6.5mm;
  font-family: "Segoe UI", sans-serif;
  font-size: 9.6pt;
}
.check .box {
  display: inline-block;
  width: 3.1mm; height: 3.1mm;
  border: 0.8pt solid var(--muted);
  border-radius: 0.5mm;
  margin-right: 2.4mm;
  vertical-align: -0.3mm;
}

/* ---------------- antisèche : dense, doit tenir sur un recto-verso ----------
   C'est la seule feuille emportée le jour J : si elle déborde sur une 3e page,
   elle perd sa fonction. D'où la grille resserrée et le corps réduit.        */
@page dense { margin: 9mm 9mm 9mm 9mm; }
body.dense { font-size: 7.5pt; line-height: 1.34; page: dense; }
body.dense h1 {
  font-size: 12pt; margin: 0 0 2mm; padding-bottom: 1.4mm; border-bottom-width: 1.2pt;
}
body.dense h2 { font-size: 9pt; margin: 3mm 0 1.4mm; }
body.dense h3 { font-size: 8pt; margin: 2mm 0 0.8mm; }
body.dense h4 { font-size: 7.6pt; margin: 1.6mm 0 0.6mm; }
body.dense p  { margin-bottom: 1.1mm; }
body.dense table { font-size: 6.9pt; margin: 1.2mm 0 2mm; }
body.dense thead th { padding: 0.9mm 1.3mm; font-size: 6.2pt; letter-spacing: 0.4pt; }
body.dense tbody td { padding: 0.8mm 1.3mm; line-height: 1.24; }
body.dense blockquote {
  margin: 1.2mm 0; padding: 1.3mm 1.8mm 1.3mm 2.4mm;
  font-size: 7.7pt; line-height: 1.34; border-left-width: 1.8pt;
}
body.dense blockquote p { margin-bottom: 0.9mm; }
body.dense ul, body.dense ol { padding-left: 4.2mm; margin-bottom: 1.4mm; }
body.dense li { margin-bottom: 0.35mm; }
body.dense hr { margin: 2.4mm 0; }
body.dense .check { font-size: 7.4pt; margin-bottom: 0.7mm; padding-left: 5mm; text-indent: -5mm; }
body.dense .check .box { width: 2.5mm; height: 2.5mm; margin-right: 1.8mm; }

.page-break { page-break-before: always; }
"""

# ---------------------------------------------------------------- markdown

_INLINE_RE = [
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"~~([^~]+)~~"), r"<del>\1</del>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])"), r"<em>\1</em>"),
]


def inline(text: str) -> str:
    out = _html.escape(text, quote=False)
    for pattern, repl in _INLINE_RE:
        out = pattern.sub(repl, out)
    return out


def _quote_class(buffer: list[str]) -> str:
    """Choisit la couleur du bloc cité selon ce qu'il contient."""
    joined = " ".join(buffer)
    if "⚠️" in joined or "jamais" in joined.lower():
        return " class=\"warn\""
    return ""


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    quote: list[str] = []
    list_mode: str | None = None

    def close_list():
        nonlocal list_mode
        if list_mode:
            out.append(f"</{list_mode}>")
            list_mode = None

    def flush_quote():
        if quote:
            out.append(f"<blockquote{_quote_class(quote)}>")
            out.extend(f"<p>{inline(q)}</p>" for q in quote)
            out.append("</blockquote>")
            quote.clear()

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()

        # citation (peut couvrir plusieurs lignes)
        if s.startswith(">"):
            close_list()
            quote.append(s.lstrip(">").strip())
            i += 1
            continue
        flush_quote()

        if not s:
            close_list()
            i += 1
            continue

        # tableau
        if s.startswith("|"):
            close_list()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                # Un séparateur contient au moins un tiret : sans ce test, une
                # ligne d'en-tête vide « | | | » passerait pour un séparateur et
                # la première ligne de données serait promue en-tête.
                is_sep = (any("-" in c for c in cells)
                          and all(set(c) <= set("-: ") for c in cells))
                if not is_sep:
                    rows.append(cells)
                i += 1
            if rows:
                ncols = max(len(r) for r in rows)
                header = rows[0] if any(c.strip() for c in rows[0]) else None
                body_rows = rows[1:] if header is not None else rows[1:]
                out.append("<table>" if header is not None else '<table class="noheader">')
                if header is not None:
                    out.append("<thead><tr>")
                    for ci in range(ncols):
                        out.append(f"<th>{inline(header[ci]) if ci < len(header) else ''}</th>")
                    out.append("</tr></thead>")
                out.append("<tbody>")
                for row in body_rows:
                    out.append("<tr>")
                    for ci in range(ncols):
                        out.append(f"<td>{inline(row[ci]) if ci < len(row) else ''}</td>")
                    out.append("</tr>")
                out.append("</tbody></table>")
            continue

        if s in ("---", "***", "___"):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if re.match(r"^-\s*\[\s*\]", s):
            close_list()
            label = re.sub(r"^-\s*\[\s*\]\s*", "", s)
            out.append(f'<p class="check"><span class="box"></span>{inline(label)}</p>')
            i += 1
            continue

        if s.startswith(("- ", "* ")):
            if list_mode != "ul":
                close_list()
                out.append("<ul>")
                list_mode = "ul"
            out.append(f"<li>{inline(s[2:])}</li>")
            i += 1
            continue

        if re.match(r"^\d+\.\s", s):
            if list_mode != "ol":
                close_list()
                out.append("<ol>")
                list_mode = "ol"
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', s))}</li>")
            i += 1
            continue

        close_list()
        cls = ""
        if s.startswith("⚠️"):
            cls = ' class="callout danger"'
        elif s.startswith("⚡"):
            cls = ' class="callout"'
        out.append(f"<p{cls}>{inline(s)}</p>" if cls else f"<p>{inline(s)}</p>")
        i += 1

    flush_quote()
    close_list()
    return "\n".join(out)


def cover_html(num: str, title: str, subtitle: str) -> str:
    return f"""<div class="cover">
  <div class="cover-rule"></div>
  <div class="cover-num">{num}</div>
  <div class="cover-kicker">Dossier de soutenance</div>
  <h1>{_html.escape(title)}</h1>
  <p class="cover-sub">{_html.escape(subtitle)}</p>
  <div class="cover-foot">
    <span><strong>{CANDIDATE}</strong> · Mastère 2 Data &amp; IA — RNCP 37137</span>
    <span>{EVENT}</span>
  </div>
</div>"""


def page_html(num: str, title: str, subtitle: str, body: str, dense: bool) -> str:
    cover = "" if dense else cover_html(num, title, subtitle)
    cls = ' class="dense"' if dense else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>{_html.escape(title)} — {CANDIDATE}</title>
<style>{CSS}</style></head>
<body{cls}>
{cover}
{body}
</body></html>"""


def find_browser() -> Path:
    for path in CHROME_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("Chrome ou Edge introuvable — impossible de composer les PDF.")


def render(browser: Path, html_path: Path, pdf_path: Path) -> None:
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run(
        [str(browser), "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
         "--virtual-time-budget=6000",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True, timeout=180,
    )


def paginate(pdf_path: Path, label: str, *, skip_first: bool) -> int:
    """Ajoute un pied de page composé (filet, libellé, folio) sur chaque page.

    Chrome ne sait pas rendre les boîtes de marge de CSS Paged Media : la
    pagination se pose donc après coup, sur le PDF déjà composé.
    """
    import fitz

    doc = fitz.open(pdf_path)
    total = doc.page_count
    first = 1 if skip_first else 0
    teal = (0.051, 0.580, 0.533)
    grey = (0.467, 0.510, 0.557)
    rule = (0.874, 0.894, 0.910)

    for idx in range(first, total):
        page = doc[idx]
        w, h = page.rect.width, page.rect.height
        y = h - 30
        page.draw_line(fitz.Point(42, y), fitz.Point(w - 42, y),
                       color=rule, width=0.5)
        page.insert_text(fitz.Point(42, y + 12), label,
                         fontname="helv", fontsize=7.5, color=grey)
        folio = f"{idx + 1 - first} / {total - first}"
        tw = fitz.get_text_length(folio, fontname="helv", fontsize=7.5)
        page.insert_text(fitz.Point(w - 42 - tw, y + 12), folio,
                         fontname="helv", fontsize=7.5, color=teal)

    tmp = pdf_path.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    pdf_path.unlink()
    tmp.rename(pdf_path)
    return total


def main() -> int:
    browser = find_browser()
    tmp = DEST / "_html"
    tmp.mkdir(exist_ok=True)
    print(f"Moteur de rendu : {browser.name}\n")

    for md_name, pdf_name, num, title, subtitle in DOCS:
        src = SRC / md_name
        if not src.exists():
            print(f"  [!] source absente : {md_name}")
            continue
        dense = md_name.startswith("05_")
        body = md_to_html(src.read_text(encoding="utf-8"))
        html_file = tmp / (pdf_name.replace(".pdf", ".html"))
        html_file.write_text(page_html(num, title, subtitle, body, dense), encoding="utf-8")
        pdf_file = DEST / pdf_name
        render(browser, html_file, pdf_file)
        # L'antisèche se lit d'un coup d'œil, sans couverture ni folio.
        if not dense:
            pages = paginate(pdf_file, f"{CANDIDATE} · Bloc {int(num)} — {title}",
                             skip_first=True)
        else:
            import fitz
            with fitz.open(pdf_file) as d:
                pages = d.page_count
        print(f"  [OK] {pdf_name:38s} {pages:3d} p.  ({pdf_file.stat().st_size / 1024:.0f} Ko)")

    # dossier complet : couvertures + tous les blocs à la suite
    parts = [cover_html("", "Dossier de soutenance",
                        "Préparation aux quatre blocs de l'épreuve · 90 minutes")]
    for md_name, _, num, title, subtitle in DOCS:
        src = SRC / md_name
        if not src.exists():
            continue
        parts.append(f'<div class="page-break"></div>')
        parts.append(f'<h1>{_html.escape(title)}</h1>')
        parts.append(f'<p><em>{_html.escape(subtitle)}</em></p>')
        parts.append(md_to_html(src.read_text(encoding="utf-8")))
    full_html = tmp / "DOSSIER_SOUTENANCE_MBEUMI.html"
    full_html.write_text(
        f'<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        f'<title>Dossier de soutenance — {CANDIDATE}</title><style>{CSS}</style></head>'
        f'<body>{"".join(parts)}</body></html>', encoding="utf-8")
    full_pdf = DEST / "DOSSIER_SOUTENANCE_MBEUMI.pdf"
    render(browser, full_html, full_pdf)
    pages = paginate(full_pdf, f"{CANDIDATE} · Dossier de soutenance", skip_first=True)
    print(f"  [OK] {full_pdf.name:38s} {pages:3d} p.  ({full_pdf.stat().st_size / 1024:.0f} Ko)")

    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
