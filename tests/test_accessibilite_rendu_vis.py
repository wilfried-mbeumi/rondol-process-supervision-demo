# -*- coding: utf-8 -*-
"""Accessibilité du schéma de vis — WCAG 1.1.1 (contenu non textuel).

Le rendu de vis est dessiné en HTML/CSS : sans nom accessible, il est muet pour
un lecteur d'écran. On vérifie ici que le conteneur est exposé comme une image
unique porteuse d'un résumé, dans les deux langues, et que le résumé reflète
réellement le profil (nombre d'éléments placés, de positions et de zones).

Vérifie aussi que les contrastes du thème sombre respectent WCAG AA (4,5:1).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import screw_logic as SL  # noqa: E402
from screw_render import build_screw_assembly_html  # noqa: E402

ZONE_STARTS = [0, 9, 18, 27, 36, 45, 54, 63, 72]
ZONE_LABELS = ["Feed"] + [f"Z{i}" for i in range(1, 9)]


def _build(cfg: list[int]) -> str:
    return build_screw_assembly_html(
        cfg, SL.N_POSITIONS,
        base_type_fn=SL.base_type,
        is_part2_fn=SL.is_part2,
        element_full_name_fn=lambda t: f"element {t}",
        show_zones=True,
        zone_starts=ZONE_STARTS,
        zone_labels=ZONE_LABELS,
    )


def _container_tag(html: str) -> str:
    m = re.search(r'<div class="rs-container"[^>]*>', html)
    assert m is not None, "conteneur rs-container introuvable dans le rendu"
    return m.group(0)


def _empty_cfg() -> list[int]:
    return [0] * (SL.N_POSITIONS + 1)


def test_conteneur_expose_comme_image_avec_nom_accessible():
    """Le schéma porte role="img" ET un aria-label non vide."""
    tag = _container_tag(_build(_empty_cfg()))
    assert 'role="img"' in tag
    m = re.search(r'aria-label="([^"]+)"', tag)
    assert m is not None, "aria-label absent du conteneur"
    assert len(m.group(1).strip()) > 20, "nom accessible trop pauvre"


def test_resume_reflete_le_profil_reel():
    """Le nom accessible compte les éléments réellement placés."""
    cfg = _empty_cfg()
    placed_positions = [0, 3, 6, 12, 20]
    for i in placed_positions:
        cfg[i] = 1
    tag = _container_tag(_build(cfg))
    alt = re.search(r'aria-label="([^"]+)"', tag).group(1)
    assert str(len(placed_positions)) in alt, f"nombre d'éléments absent : {alt}"
    assert str(SL.N_POSITIONS) in alt, f"nombre de positions absent : {alt}"
    assert str(len(ZONE_STARTS)) in alt, f"nombre de zones absent : {alt}"


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_nom_accessible_dans_les_deux_langues(lang, monkeypatch):
    """Le résumé est traduit — pas de français figé en mode anglais."""
    import rondol_i18n

    monkeypatch.setattr(rondol_i18n, "current_lang", lambda: lang)
    tag = _container_tag(_build(_empty_cfg()))
    alt = re.search(r'aria-label="([^"]+)"', tag).group(1)
    if lang == "fr":
        assert "vis" in alt.lower()
    else:
        assert "screw" in alt.lower()


def test_aria_label_ne_casse_pas_le_html():
    """Aucun guillemet double non échappé dans l'attribut."""
    tag = _container_tag(_build(_empty_cfg()))
    inner = re.search(r'aria-label="([^"]*)"', tag).group(1)
    assert '"' not in inner


def test_decoratif_reste_masque_aux_lecteurs_decran():
    """Les éléments purement visuels gardent aria-hidden (WCAG : pas de bruit)."""
    html = _build(_empty_cfg())
    assert 'aria-hidden="true"' in html


def test_positions_vides_masquees_aux_lecteurs_decran():
    """Chaque position sans élément est aria-hidden.

    Sans cela, un lecteur d'écran énoncerait « arbre nu » des dizaines de fois :
    du bruit pur, l'information utile étant portée par le résumé du conteneur et
    le tableau des éléments placés.
    """
    html = _build(_empty_cfg())
    slots = re.findall(r'<div class="rs-slot rs-empty"[^>]*>', html)
    assert slots, "aucune position vide rendue"
    masques = [s for s in slots if 'aria-hidden="true"' in s]
    assert len(masques) == len(slots), (
        f"{len(slots) - len(masques)} position(s) vide(s) encore exposée(s)")


@pytest.mark.parametrize(("lang", "attendu"), [("fr", "arbre nu"), ("en", "bare shaft")])
def test_infobulles_positions_vides_traduites(lang, attendu, monkeypatch):
    """« arbre nu » était figé en français et fuitait en mode anglais."""
    import rondol_i18n

    monkeypatch.setattr(rondol_i18n, "current_lang", lambda: lang)
    html = _build(_empty_cfg())
    assert attendu in html
    interdit = "bare shaft" if lang == "fr" else "arbre nu"
    assert interdit not in html, f"fuite linguistique : « {interdit} » en mode {lang}"


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_infobulle_pointe_traduite(lang, monkeypatch):
    """L'infobulle de la pointe était elle aussi figée en français."""
    import rondol_i18n

    monkeypatch.setattr(rondol_i18n, "current_lang", lambda: lang)
    cfg = _empty_cfg()
    cfg[0] = 1
    html = _build(cfg)
    if lang == "fr":
        assert "non duplicable" in html
        assert "cannot be moved" not in html
    else:
        assert "cannot be moved" in html
        assert "non duplicable" not in html


# --------------------------------------------------------------------------
# Contrastes du thème sombre (.streamlit/config.toml) — WCAG AA = 4,5:1
# --------------------------------------------------------------------------
def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
           for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


BACKGROUND = "#0B0F14"
BACKGROUND_2 = "#111827"
TEXT = "#F9FAFB"
PRIMARY = "#4CAF50"


@pytest.mark.parametrize(("fg", "bg", "nom"), [
    (TEXT, BACKGROUND, "texte / fond"),
    (TEXT, BACKGROUND_2, "texte / fond secondaire"),
    (PRIMARY, BACKGROUND, "vert primaire / fond"),
    (PRIMARY, BACKGROUND_2, "vert primaire / fond secondaire"),
])
def test_contraste_wcag_aa(fg, bg, nom):
    ratio = _contrast(fg, bg)
    assert ratio >= 4.5, f"{nom} : {ratio:.2f}:1 < 4,5:1 (WCAG AA)"
