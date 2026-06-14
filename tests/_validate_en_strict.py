"""Strict English validation — renders all 6 pages, checks for French leaks
AND raw i18n keys. NOT a pytest file — run directly for a full report."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from streamlit.testing.v1 import AppTest  # type: ignore

PAGES = {
    "Supervision": str(APP / "Supervision.py"),
    "Profile": str(APP / "pages" / "1_Profile.py"),
    "Settings": str(APP / "pages" / "2_Settings.py"),
    "Analyse_run": str(APP / "pages" / "3_Run_Analysis.py"),
    "Historique": str(APP / "pages" / "4_History.py"),
    "Moteur_Procede": str(APP / "pages" / "5_Process_Engine.py"),
}

FORBIDDEN_FR = [
    "Vis vide", "Aucun élément", "Configurer la vis", "Prochaine étape",
    "Pourquoi", "Régime", "Aucune analyse possible",
    "Placer quelques éléments", "Extrudeuse", "Non renseigné",
    "Capacité maximale atteinte", "Retirez un élément", "Lecture opérateur",
    "Décision", "Paramètres procédé", "Vitesse vis", "Débit feeder",
    "Densité bulk", "Moteur Procédé", "Historique", "Analyse run",
    "Malaxage", "Convoyage", "recommandé", "priorité",
    "alerte", "Composition matière", "Agrégats par zone",
    "figée au commit", "Analyse indicative", "Aucun profil enregistré",
    "aucune analyse possible", "Procédé",
    "LECTURE OPÉRATEUR", "DÉCISION", "POURQUOI", "ACTION",
    "Aucun élément n'est posé",
    "Non calculable", "Non disponible", "Débit massique", "Débit sortie",
    "Puissance mécanique", "Audit calcul procédé",
    "Formule PLC utilisée", "coefficient d'étalonnage",
    "Étalonnage feeder", "Débit réel non calculable",
    "Couple total", "SME totale", "Résidence totale",
    "Remplissage moyen", "Cisaillement max",
]

# Raw i18n key patterns — a dot-separated lowercase token like sr.xxx.yyy
import re
RAW_KEY_RE = re.compile(
    r'\b(?:sr|profile|settings|supervision|history|moteur|agent|i18n|demo|nav)'
    r'\.[a-z_]+(?:\.[a-z_]+)+\b'
)


def _rendered_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(str(getattr(el, "value", "")))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    try:
        for m in at.metric:
            chunks.append(str(getattr(m, "label", "")))
            chunks.append(str(getattr(m, "value", "")))
    except Exception:
        pass
    return "\n".join(chunks)


def _load_en(path: str):
    at = AppTest.from_file(path)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at.run(timeout=120)


def main():
    all_ok = True
    for name, path in PAGES.items():
        print(f"\n{'='*60}")
        print(f"  PAGE: {name}")
        print(f"{'='*60}")
        at = _load_en(path)
        if at.exception:
            print(f"  [EXCEPTION] {[str(e.value) for e in at.exception]}")
            all_ok = False
            continue

        text = _rendered_text(at)

        # Check French leaks
        fr_found = []
        for fr in FORBIDDEN_FR:
            if fr in text:
                fr_found.append(fr)
        if fr_found:
            print(f"  [FRENCH LEAKS] {fr_found}")
            all_ok = False
        else:
            print(f"  [FR] OK — no forbidden French strings")

        # Check raw i18n keys
        raw_keys = RAW_KEY_RE.findall(text)
        if raw_keys:
            unique = sorted(set(raw_keys))
            print(f"  [RAW KEYS] {unique}")
            all_ok = False
        else:
            print(f"  [KEYS] OK — no raw i18n keys visible")

    print(f"\n{'='*60}")
    if all_ok:
        print("  ALL PAGES CLEAN")
    else:
        print("  ISSUES FOUND — see above")
    print(f"{'='*60}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
