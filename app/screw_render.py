"""screw_render.py — Rendu visuel de la vis Rondol (HMI Profile + preview).

Source unique de vérité pour le rendu vis (validé Wilfried) :

  ÉTAPE A — pré-traitement PNG par type
    - trim global (bords blancs/transparents)
    - flood-fill du fond blanc vers alpha=0 (silhouette propre)
    - HÉLICOÏDAUX : crop à zone stable + N×pitch FFT phase-aligné
    - BLOCS       : crop à zone stable (sans cap)
    - TIP         : crop moitié droite (pointe)
    Résultat : tile RGBA, fond transparent, scaled à HELIX_HEIGHT_PX en hauteur.

  ÉTAPE B — composition HTML (architecture base + overlays)
    - BASE  : pattern forward conveying à +72° posé en CONTINU sur l'étendue
              placée (rs-helix-base, full span). C'est la VIS PRINCIPALE,
              constante, qui donne la lecture mécanique dominante. Tous les
              autres types se posent par-dessus comme perturbations locales.
    - FORWARD (1) : aucun overlay — la base EST déjà du forward.
    - HÉLICOÏDAUX SPÉCIALISÉS (half, short-pitch, large, reverse, chaotic) :
              overlay rs-helix-overlay posé sur la base avec opacity 0.68 +
              mix-blend-mode soft-light + edge-mask 14px. La base reste
              visible sous l'overlay → modulation locale (densification pour
              short-pitch, contre-sens pour reverse, croisement losange pour
              chaotic) au lieu de remplacement complet.
    - BLOCS (kneading 90/30/60/45, toothed, special mixing) :
              overlay rs-block-overlay (opacity 0.58, soft-light, edge-mask
              18px) — modules discrets posés DANS la matière de la vis,
              transitions douces vers les voisins.
    - TIP (13) : étend la base jusqu'à l'apex ; clip-path conique de
              rs-screw-area effile la matière naturellement.
    - EMPTY : pas d'élément, mais N'INTERROMPT PAS la base (la vis reste
              continue mécaniquement, l'arbre est juste sans paddle ajouté).

  ÉTAPE C — overlays métier
    - Zones (Feed, Z1..Z8) en bandeau au-dessus de la vis.
    - Lecture métier : tableau "position · zone · type · rôle".
    - Recommandations IA : convoyage / mélange / vide / remplissage.

Aucune dépendance Streamlit ici → réutilisable depuis tout contexte (HMI, preview,
batch, tests). Streamlit n'importe que les fonctions pures.
"""
from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import sys as _sys

import numpy as np
from PIL import Image
from scipy import ndimage

# Garantir app/ sur sys.path pour l'import bare de rondol_i18n.
_APP_DIR = str(Path(__file__).resolve().parent)
if _APP_DIR not in _sys.path:
    _sys.path.insert(0, _APP_DIR)

# i18n FR/EN : import défensif — hors Streamlit (tests, batch), le fallback
# résout les traductions EN depuis TRANSLATIONS sans session_state.
try:  # pragma: no cover
    from rondol_i18n import t as _t
except Exception:  # pragma: no cover
    try:
        from rondol_i18n import TRANSLATIONS as _TRANSLATIONS
    except Exception:
        _TRANSLATIONS = {}

    def _t(key: str, **kwargs: object) -> str:  # type: ignore[misc]
        entry = _TRANSLATIONS.get(key)
        if entry is None:
            return key
        text = entry.get("en") or entry.get("fr") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text

# ---------------------------------------------------------------------------
# Paramètres visuels (utilisés par 1_Profile.py et build_preview_screw.py)
# ---------------------------------------------------------------------------
CONTAINER_HEIGHT_PX = 100
SHAFT_HEIGHT_PX = 28
HELIX_HEIGHT_PX = 56
POS_UNIT_PX = 40
STRIPE_HEIGHT_PX = 2
STRIPE_OPACITY = 0.30
TIP_FADE_PCT = 30
ZONE_STRIP_HEIGHT_PX = 18
ZONE_STRIP_GAP_PX = 4
# Bandeau de flux matière (Entrée → Sortie) au-dessus du tracé.
# Le statut de pointe est intégré ici (label "Sortie" coloré) — pas de
# callout flottant séparé : un seul élément de châssis porte la direction
# du flux ET l'état de la pointe.
FLOW_BANNER_HEIGHT_PX = 24
FLOW_BANNER_GAP_PX = 4

ROOT = Path(__file__).resolve().parent.parent
SCREW_IMG_DIR = ROOT / "references" / "screw_elements"

HELICAL_TYPES = frozenset({1, 2, 3, 6, 9, 10})
BLOCK_TYPES = frozenset({4, 5, 7, 8, 11, 12})
TIP_TYPES = frozenset({13})

SOURCE_FILES: dict[int, str] = {
    1:  "Forward conveying.png",
    2:  "Forward conveying.png",
    3:  "Short-pitch elements.png",
    4:  "Kneading element 90°.png",
    5:  "Kneading element 30°.png",
    6:  "Large pitch elements.png",
    7:  "Kneading element 60°.png",
    8:  "Kneading element 45°.png",
    9:  "Reverse conveying.png",
    10: "Chaotic element.png",
    11: "Toothed element.png",
    12: "Special mixing element.png",
    13: "screw tip.png",
}

# Couleurs des stripes par type (palette HMI Rondol)
ELEMENT_COLORS: list[str] = [
    "#1F2937", "#06B6D4", "#0891B2", "#3B82F6", "#A855F7", "#EC4899",
    "#10B981", "#8B5CF6", "#F472B6", "#EF4444", "#F59E0B", "#FBBF24",
    "#F97316", "#64748B",
]

# Architecture rendu (validée Wilfried 2026-05-10) :
#
#   COUCHE 1 — base universelle (rs-helix-base)
#     Pattern de la VIS PRINCIPALE (forward conveying à +72°) + shading
#     cylindrique. Couvre toute la longueur de la vis sans interruption.
#     Donne la lecture mécanique dominante : c'est une vis d'extrudeuse
#     continue, pas un assemblage de modules indépendants.
#
#   COUCHE 2 — perturbations locales (rs-helix-overlay, rs-block-overlay)
#     Patterns spécialisés (densité, angle, sens) posés UNIQUEMENT là où
#     un type non-forward est placé, en mix-blend-mode soft-light avec
#     opacité réduite (0.55-0.70) et edge-mask en fondu (12-18px). La base
#     reste lisible sous chaque perturbation → l'élément spécialisé MODULE
#     la matière, ne la REMPLACE pas. Transitions latérales douces.
#
# Conséquence visuelle : ajouter UN élément (kneading, short-pitch, ...) ne
# change pas le caractère global de la vis ; on perçoit une compression /
# une zone de mélange / un contre-couple LOCAL, dans une architecture
# mécanique continue cohérente.
_HELIX_SHADING = (
    "linear-gradient(180deg,"
    "rgba(0,0,0,0.62) 0%,rgba(0,0,0,0.20) 14%,"
    "rgba(255,255,255,0.06) 36%,rgba(255,255,255,0.40) 50%,"
    "rgba(255,255,255,0.06) 64%,rgba(0,0,0,0.20) 86%,"
    "rgba(0,0,0,0.62) 100%)"
)

# Pattern de base — forward conveying à +72°, palette métallique pleine.
# Sert de référence visuelle constante sur toute la vis. NE PAS modifier
# sans réviser l'équilibre de tous les overlays (ils sont calibrés contre
# cette densité et cette palette).
_HELIX_BASE_LAYER_PATTERN = (
    "repeating-linear-gradient(72deg,"
    "#3a3e46 0px,#4d5159 4px,#6d717a 9px,#9aa0aa 14px,"
    "#b8bdc7 17px,#9aa0aa 20px,#6d717a 25px,#4d5159 30px,"
    "#3a3e46 28px)"
)

# Patterns d'overlay — pleine palette métallique pour signature géométrique
# bold. Chaque type DOIT avoir une lecture mécanique distincte (pitch, angle,
# direction, profil paddle, dent, bloc distributif). La continuité globale
# est portée par la BASE (en-dessous) et par les EDGE MASKS en pourcentage
# (sur .rs-helix-overlay / .rs-block-overlay) qui fondent les bords. Pas de
# washed-out ici : la géométrie doit être lue comme du métal usiné réel.
_OVERLAY_PATTERNS: dict[int, str] = {
    # Half-pitch (2) — pas réduit (~×0.6) : flights plus rapprochés à +72°.
    2: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(72deg,"
        "#3a3e46 0px,#4d5159 2.5px,#6d717a 5.5px,#9aa0aa 8.5px,"
        "#b8bdc7 10.5px,#9aa0aa 12.5px,#6d717a 15px,#4d5159 18px,"
        "#3a3e46 17px)"),
    # Short-pitch (3) — pas le plus court : compression visible des flights.
    3: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(72deg,"
        "#3a3e46 0px,#4d5159 2px,#6d717a 4.5px,#9aa0aa 7px,"
        "#b8bdc7 8.5px,#9aa0aa 10px,#6d717a 12.5px,#4d5159 14px,"
        "#3a3e46 13.5px)"),
    # Large-pitch (6) — pas étendu (~×1.5) : flights espacés clairement.
    6: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(72deg,"
        "#3a3e46 0px,#4d5159 6px,#6d717a 13.5px,#9aa0aa 21px,"
        "#b8bdc7 25.5px,#9aa0aa 30px,#6d717a 37.5px,#4d5159 45px,"
        "#3a3e46 42px)"),
    # Reverse (9) — sens INVERSÉ (-72°), pleine matière métallique. La
    # direction opposée est un changement mécanique RÉEL (contre-couple),
    # doit être immédiatement lisible.
    9: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(-72deg,"
        "#3a3e46 0px,#4d5159 4px,#6d717a 9px,#9aa0aa 14px,"
        "#b8bdc7 17px,#9aa0aa 20px,#6d717a 25px,#4d5159 30px,"
        "#3a3e46 28px)"),
    # Chaotic (10) — pattern AUTO-PORTANT : forward faible (+72°) ET counter
    # marqué (-72°) dans le MÊME overlay → losange visible standalone,
    # signature claire du mélange chaotique bidirectionnel.
    10: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(72deg,"
        "transparent 0px,transparent 12px,"
        "rgba(20,22,28,0.55) 14px,rgba(180,189,199,0.45) 17px,"
        "rgba(20,22,28,0.55) 20px,transparent 22px,transparent 28px),"
        "repeating-linear-gradient(-72deg,"
        "transparent 0px,transparent 7px,"
        "rgba(15,17,22,0.85) 10px,rgba(220,225,235,0.55) 14px,"
        "rgba(15,17,22,0.85) 18px,transparent 21px,transparent 28px)"),
    # Kneading 90° (4) — disques perpendiculaires : edges TRÈS marqués par
    # gaps d'ombre profonds entre chaque paddle. Le contraste fort lit comme
    # de vrais disques en relief, pas comme une texture.
    4: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(90deg,"
        "#0a0c10 0px,#0a0c10 1.5px,"
        "#3e424a 3px,#7d828b 6px,#b6bcc6 8px,"
        "#7d828b 10px,#3e424a 13px,"
        "#0a0c10 14.5px,#0a0c10 16px)"),
    # Kneading 30° (5) — paddles légèrement décalés (60deg, proche hélice).
    5: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(60deg,"
        "#0a0c10 0px,#0a0c10 1.5px,"
        "#3e424a 3px,#7d828b 7px,#b6bcc6 9px,"
        "#7d828b 11px,#3e424a 15px,"
        "#0a0c10 16.5px,#0a0c10 18px)"),
    # Kneading 60° (7) — paddles presque perpendiculaires (80deg).
    7: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(80deg,"
        "#0a0c10 0px,#0a0c10 1.5px,"
        "#3e424a 3px,#7d828b 6.5px,#b6bcc6 8.5px,"
        "#7d828b 10.5px,#3e424a 14px,"
        "#0a0c10 15.5px,#0a0c10 17px)"),
    # Kneading 45° (8) — décalage médian (70deg).
    8: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(70deg,"
        "#0a0c10 0px,#0a0c10 1.5px,"
        "#3e424a 3px,#7d828b 7px,#b6bcc6 9px,"
        "#7d828b 11px,#3e424a 14.5px,"
        "#0a0c10 16px,#0a0c10 17.5px)"),
    # Toothed (11) — dents très fines très denses. Le PROFIL est slim
    # (height réduit côté CSS via _OVERLAY_HEIGHTS) → suggère le rotor à
    # plus petit diamètre des éléments dentés industriels.
    11: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(90deg,"
        "#0d0f14 0px,#0d0f14 0.8px,"
        "#5d626c 1.5px,#9aa0aa 2.8px,#b8bdc7 3.5px,"
        "#9aa0aa 4.2px,#5d626c 5.5px,"
        "#0d0f14 6.2px,#0d0f14 7px)"),
    # Special mixing (12) — blocs distributifs larges séparés par des
    # COUPES PROFONDES. Chaque bloc est une chambre de mélange distincte.
    12: (f"{_HELIX_SHADING},"
        "repeating-linear-gradient(90deg,"
        "#080a0e 0px,#080a0e 3px,"
        "#4a4e57 5px,#7d828b 9px,#a8aeb8 12px,"
        "#b6bcc6 14px,#a8aeb8 16px,"
        "#7d828b 19px,#4a4e57 23px,"
        "#080a0e 25px,#080a0e 28px)"),
}

# Paramètres de rendu par type : (opacity, blend_mode, height_px).
# Géométrie BOLD locale + transitions douces via edge-mask = continuité
# mécanique avec signatures lisibles.
_OVERLAY_PARAMS: dict[int, tuple[float, str, int]] = {
    # type_id: (opacity, blend, height)
    2:  (0.86, "normal",     56),    # half-pitch — compression modérée
    3:  (0.90, "normal",     56),    # short-pitch — compression nette
    6:  (0.86, "normal",     56),    # large-pitch — extension nette
    9:  (0.92, "normal",     56),    # reverse — direction inversée nette
    10: (0.85, "normal",     56),    # chaotic — losange auto-portant
    4:  (0.95, "normal",     56),    # kneading 90 — paddles très marqués
    5:  (0.92, "normal",     56),    # kneading 30
    7:  (0.94, "normal",     56),    # kneading 60
    8:  (0.93, "normal",     56),    # kneading 45
    11: (0.93, "normal",     42),    # toothed — profil slim (-14px)
    12: (0.92, "normal",     56),    # special mixing — blocs distributifs
}


# Rôle métier par type (utilisé pour la lecture HMI + reco)
def _element_role(etype: int) -> str:
    return _t(f"role.{etype}") if 1 <= etype <= 13 else "—"


ELEMENT_ROLES: dict[int, str] = {
    1: "conveying", 2: "conveying (½)", 3: "compact conveying",
    4: "dispersive mixing", 5: "gentle mixing", 6: "fast conveying",
    7: "dispersive mixing", 8: "dispersive mixing",
    9: "retention / back-pressure", 10: "chaotic mixing",
    11: "distributive mixing", 12: "distributive mixing", 13: "discharge",
}


# ---------------------------------------------------------------------------
# Étape A — pré-traitement
# ---------------------------------------------------------------------------
def _trim_global(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb_mean = arr[:, :, :3].mean(axis=2)
    nonempty = (alpha > 10) & (rgb_mean < 245)
    rows = np.where(nonempty.any(axis=1))[0]
    cols = np.where(nonempty.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return img.convert("RGBA")
    return img.convert("RGBA").crop(
        (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)
    )


def _floodfill_bg_transparent(img: Image.Image, threshold: int = 240,
                               feather_px: int = 2) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3]
    h, w = rgb.shape[:2]
    is_bright = (rgb > threshold).all(axis=2)
    labeled, _ = ndimage.label(is_bright)
    corner_labels = {labeled[0, 0], labeled[0, w - 1],
                     labeled[h - 1, 0], labeled[h - 1, w - 1]}
    corner_labels.discard(0)
    if not corner_labels:
        return img.convert("RGBA")
    bg_mask = np.isin(labeled, list(corner_labels))
    alpha = arr[:, :, 3].astype(np.int32)
    alpha[bg_mask] = 0
    if feather_px > 0:
        dist = ndimage.distance_transform_edt(~bg_mask)
        soft = np.clip(dist / feather_px, 0.0, 1.0)
        alpha = (alpha.astype(np.float64) * soft).astype(np.int32)
    arr[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _silhouette_amplitude(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb_mean = arr[:, :, :3].mean(axis=2)
    nonempty = (alpha > 10) & (rgb_mean < 245)
    return nonempty.sum(axis=0).astype(np.int32)


def _find_stable_zone(amp: np.ndarray, exclude_left_pct: float = 0.40,
                      stability_threshold: float = 0.85) -> tuple[int, int]:
    w = len(amp)
    start_min = int(w * exclude_left_pct)
    if start_min >= w - 5:
        return int(w * 0.45), int(w * 0.95)
    threshold = amp[start_min:].max() * stability_threshold
    in_zone = amp >= threshold
    in_zone[:start_min] = False
    best_start, best_len = start_min, 0
    cur_start, cur_len = -1, 0
    for i, v in enumerate(in_zone):
        if v:
            if cur_start == -1:
                cur_start = i
            cur_len += 1
        else:
            if cur_len > best_len:
                best_start, best_len = cur_start, cur_len
            cur_start, cur_len = -1, 0
    if cur_len > best_len:
        best_start, best_len = cur_start, cur_len
    if best_len < 20:
        return int(w * 0.45), int(w * 0.95)
    return int(best_start), int(best_start + best_len)


def _scale_to_height(img: Image.Image, target_h: int) -> Image.Image:
    w, h = img.size
    if h == 0:
        return img
    new_w = max(1, round(w * target_h / h))
    return img.resize((new_w, target_h), Image.LANCZOS)


def _extract_block_tile(img: Image.Image) -> Image.Image:
    img = _trim_global(img)
    amp = _silhouette_amplitude(img)
    z_start, z_end = _find_stable_zone(amp)
    tile = img.crop((z_start, 0, z_end, img.height))
    return _floodfill_bg_transparent(tile)


def _extract_tip_tile(img: Image.Image) -> Image.Image:
    img = _trim_global(img)
    w, h = img.size
    tile = img.crop((int(w * 0.42), 0, w, h))
    return _floodfill_bg_transparent(tile)


@dataclass(frozen=True)
class TileAsset:
    uri: str
    width: int
    height: int
    kind: str   # "block" | "tip"


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@lru_cache(maxsize=32)
def _load_tile(type_id: int) -> TileAsset | None:
    """Précharge le tile signature pour un type. Cache LRU.

    Hélicoïdaux : pas de tile (porté par la base procédurale).
    Blocs       : tile cropé à zone stable, fond transparent.
    Tip         : tile cropé moitié droite, fond transparent.
    """
    if type_id in HELICAL_TYPES:
        return None
    src_file = SOURCE_FILES.get(type_id)
    if src_file is None:
        return None
    p = SCREW_IMG_DIR / src_file
    if not p.exists():
        return None
    src = Image.open(p)
    if type_id in TIP_TYPES:
        tile = _extract_tip_tile(src)
        kind = "tip"
    elif type_id in BLOCK_TYPES:
        tile = _extract_block_tile(src)
        kind = "block"
    else:
        return None
    tile = _scale_to_height(tile, HELIX_HEIGHT_PX)
    return TileAsset(uri=_to_data_uri(tile), width=tile.width,
                     height=tile.height, kind=kind)


# ---------------------------------------------------------------------------
# Étape B — assembly HTML
# ---------------------------------------------------------------------------
def build_screw_assembly_html(
    cfg: list[int],
    n_positions: int,
    *,
    base_type_fn,
    is_part2_fn,
    element_full_name_fn,
    show_zones: bool = True,
    zone_starts: list[int] | None = None,
    zone_labels: list[str] | None = None,
    zone_subvalues: list[str] | None = None,
    feeder_markers: list[dict] | None = None,
    tip_part1_pos: int | None = None,
    tip_status: str = "valid",
) -> str:
    """Rendu vis assemblée (HTML+CSS auto-contenu).

    Args:
        cfg: liste 0..N_POSITIONS d'entiers (état config).
        n_positions: N_POSITIONS (=81).
        base_type_fn: callable type_value -> base type (= screw_logic.base_type).
        is_part2_fn: callable type_value -> bool (= screw_logic.is_part2).
        element_full_name_fn: callable type_id -> str (label complet).
        show_zones: ajoute le bandeau de zones au-dessus de la vis.
        zone_starts: positions de début de chaque zone (Feed=0, Z1=9, …).
        zone_labels: noms des zones (défaut "Z{i}"). Doit avoir même longueur
            que zone_starts. Pour Rondol : ["Feed", "Z1", ..., "Z8"].
        zone_subvalues: valeurs courtes affichées sous chaque libellé de zone
            (style "Plug" du HMI Rondol — ex. résidence en s, "0,8 s"). Même
            longueur que zone_starts. Vide ou None → pas de sous-ligne.
        feeder_markers: liste de dicts {pos:int, label:str, color:str} pour
            tracer des marqueurs verticaux (Main feeder, Side feeder…). Pos =
            position vis 0..N_POSITIONS-1. Affiché par-dessus la vis.
        tip_part1_pos: position de début de la pointe (défaut n_positions-2).
            Sert à positionner le glyphe triangle + badge 🔒 fin de vis.
        tip_status: "valid" | "missing" | "deduplicated" — pilote la couleur
            du badge (vert / rouge / ambre).
    """
    slots_html: list[str] = []
    # Runs hélice non-forward (start_x, end_x, type_id) — un par séquence
    # contiguë du MÊME type hélicoïdal NON-FORWARD. Forward (type 1) n'est
    # PAS tracké ici : il est porté par la base universelle. Forward+forward
    # = invisible (base). Short+short = 1 run d'overlay short. Short+forward
    # = run d'overlay short qui se termine, puis base seule.
    helix_runs: list[tuple[int, int, int]] = []
    # Runs bloc (start_x, end_x, type_id) — un par élément BLOCK_TYPES placé.
    # Rendu en overlay au-dessus de la base (perturbation locale).
    block_runs: list[tuple[int, int, int]] = []
    # Étendue continue contenant au moins un élément non-empty (start_x, end_x)
    # — sert à dimensionner la base universelle. Un seul span : un trou empty
    # ne coupe pas la base (la vis matérielle est continue, l'arbre nu est
    # juste une absence d'élément, pas une absence de vis).
    base_span_start: int | None = None
    base_span_end: int = 0
    cur_x = 0
    helix_run_start: int | None = None
    helix_run_type: int | None = None

    def close_helix_run(end_x: int) -> None:
        nonlocal helix_run_start, helix_run_type
        if helix_run_start is not None and helix_run_type is not None:
            helix_runs.append((helix_run_start, end_x, helix_run_type))
            helix_run_start = None
            helix_run_type = None

    def mark_base(start_x: int, end_x: int) -> None:
        """Étend la portée de la base universelle pour inclure [start_x, end_x[."""
        nonlocal base_span_start, base_span_end
        if base_span_start is None:
            base_span_start = start_x
        if end_x > base_span_end:
            base_span_end = end_x

    i = 0
    while i < n_positions:
        v = cfg[i]
        if is_part2_fn(v):
            i += 1
            continue
        bt = base_type_fn(v)

        # Position vide : aucun élément placé. Ferme tout run hélice ouvert
        # mais N'INTERROMPT PAS la base universelle : la vis mécanique est
        # continue, un slot empty = juste pas d'élément ajouté à cet endroit.
        if bt == 0:
            close_helix_run(cur_x)
            slots_html.append(
                f'<div class="rs-slot rs-empty" title="Pos {i} · arbre nu" '
                f'style="width:{POS_UNIT_PX}px;"></div>'
            )
            cur_x += POS_UNIT_PX
            i += 1
            continue

        n_pos = 1 if bt == 2 else 2
        slot_w = n_pos * POS_UNIT_PX
        color = ELEMENT_COLORS[bt] if 0 <= bt < len(ELEMENT_COLORS) else "#9CA3AF"
        full_name = element_full_name_fn(bt)
        stripe = f'<div class="rs-stripe" style="background:{color};"></div>'

        # Tip (type 13) : terminaison physique unique, absorbée par le clip-path
        # conique. La base s'étend jusqu'à la pointe (le cône effile la matière
        # naturellement). Slot stripe-only pour tooltip + couleur.
        if bt == 13:
            close_helix_run(cur_x)
            mark_base(cur_x, cur_x + slot_w)
            slots_html.append(
                f'<div class="rs-slot rs-stripe-only" '
                f'title="Pos {i} · {full_name}" '
                f'style="width:{slot_w}px;">{stripe}</div>'
            )
            cur_x += slot_w
            i += n_pos
            continue

        # Élément hélicoïdal. Forward (type 1) = base seule, pas d'overlay
        # (la base universelle EST déjà du forward conveying). Les autres
        # types (half, short, large, reverse, chaotic) ouvrent un run
        # d'overlay typé qui sera posé sur la base avec edge-mask + blend.
        if bt in HELICAL_TYPES:
            mark_base(cur_x, cur_x + slot_w)
            if bt == 1:
                close_helix_run(cur_x)
            elif helix_run_type != bt:
                close_helix_run(cur_x)
                helix_run_start = cur_x
                helix_run_type = bt
            slots_html.append(
                f'<div class="rs-slot rs-stripe-only" '
                f'title="Pos {i} · {full_name}" '
                f'style="width:{slot_w}px;">{stripe}</div>'
            )
            cur_x += slot_w
            i += n_pos
            continue

        # Élément BLOC (kneading, toothed, special mixing) : overlay LOCAL
        # posé sur la base universelle. Edge-mask + opacité réduite pour
        # transition douce avec la matière voisine — l'élément MODULE la vis,
        # ne la remplace pas. Ferme tout run hélice spécialisé ouvert (un
        # bloc rompt la signature hélicoïdale spécialisée mais pas la base).
        if bt in BLOCK_TYPES:
            close_helix_run(cur_x)
            mark_base(cur_x, cur_x + slot_w)
            block_runs.append((cur_x, cur_x + slot_w, bt))
            slots_html.append(
                f'<div class="rs-slot rs-stripe-only" '
                f'title="Pos {i} · {full_name}" '
                f'style="width:{slot_w}px;">{stripe}</div>'
            )
            cur_x += slot_w
            i += n_pos
            continue

        # Type inconnu : traite comme empty (n'étend pas la base).
        close_helix_run(cur_x)
        slots_html.append(
            f'<div class="rs-slot rs-empty" title="Pos {i} · type inconnu" '
            f'style="width:{slot_w}px;"></div>'
        )
        cur_x += slot_w
        i += n_pos

    close_helix_run(cur_x)

    inner_w = n_positions * POS_UNIT_PX

    # Base universelle — pattern forward conveying à +72° posé en continu sur
    # l'étendue [base_span_start, base_span_end[. Si la vis contient au moins
    # un élément, la base s'étend jusqu'à inner_w pour que le clip-path conique
    # de rs-screw-area effile la matière naturellement dans la pointe.
    if base_span_start is not None:
        base_layer_html = (
            f'<div class="rs-helix-base" '
            f'style="left:{base_span_start}px;'
            f'width:{inner_w - base_span_start}px;'
            f'background:{_HELIX_SHADING},{_HELIX_BASE_LAYER_PATTERN};'
            f'background-position:0 0,-{base_span_start}px 0;"></div>'
        )
    else:
        base_layer_html = ""

    def _render_overlay(klass: str, x: int, w: int, t: int) -> str:
        op, blend, h = _OVERLAY_PARAMS.get(t, (0.85, "normal", HELIX_HEIGHT_PX))
        return (
            f'<div class="{klass}" '
            f'style="left:{x}px;width:{w}px;height:{h}px;'
            f'opacity:{op};mix-blend-mode:{blend};'
            f'background:{_OVERLAY_PATTERNS[t]};'
            f'background-position:0 0,-{x}px 0,-{x}px 0;"></div>'
        )

    # Overlays hélice spécialisée (half, short, large, reverse, chaotic) —
    # pleine matière métallique localement, base masquée dans le cœur du
    # run, base réapparaissant via edge-mask en pourcentage aux frontières.
    # Forward (type 1) n'apparaît jamais ici — il EST la base.
    helix_layers = "".join(
        _render_overlay("rs-helix-overlay", s, e - s, t)
        for s, e, t in helix_runs
        if t in _OVERLAY_PATTERNS
    )
    # Overlays bloc (kneading, toothed, special mixing) — même mécanique,
    # géométrie paddle/dent/distributif portée par leur pattern dédié.
    block_layers = "".join(
        _render_overlay("rs-block-overlay", s, e - s, t)
        for s, e, t in block_runs
        if t in _OVERLAY_PATTERNS
    )

    # Bandeau zones — INTÉGRÉ dans le même scroll container que la vis
    # (sinon scroll désynchronisé entre zones et hélice).
    has_subvalues = bool(zone_subvalues) and bool(zone_starts) and \
        len(zone_subvalues) == len(zone_starts)
    zone_strip_h = ZONE_STRIP_HEIGHT_PX + (14 if has_subvalues else 0)

    zones_html = ""
    if show_zones and zone_starts:
        if zone_labels and len(zone_labels) == len(zone_starts):
            zone_names = list(zone_labels)
        else:
            zone_names = [f"Z{i}" for i in range(len(zone_starts))]
        cells = []
        for zi, z_start in enumerate(zone_starts):
            z_end_pos = zone_starts[zi + 1] if zi + 1 < len(zone_starts) else n_positions
            z_x = z_start * POS_UNIT_PX
            z_w = (z_end_pos - z_start) * POS_UNIT_PX
            label = zone_names[zi] if zi < len(zone_names) else f"Z{zi}"
            sub = ""
            if has_subvalues:
                sv = zone_subvalues[zi] if zi < len(zone_subvalues) else ""
                if sv:
                    sub = f'<div class="rs-zone-sub">{sv}</div>'
            cells.append(
                f'<div class="rs-zone-cell" '
                f'style="left:{z_x}px;width:{z_w}px;height:{zone_strip_h}px;">'
                f'<div class="rs-zone-label">{label}</div>{sub}</div>'
            )
        zones_html = (
            f'<div class="rs-zones-bar" style="width:{inner_w}px;height:{zone_strip_h}px;">'
            + "".join(cells) + "</div>"
        )

    # Marqueurs feeder (Main feeder, Side feeder…) — superposés sur la vis.
    # Pas d'effet sur la mise en page : positionnés en absolu dans rs-screw-area.
    markers_html = ""
    if feeder_markers:
        marker_parts: list[str] = []
        for m in feeder_markers:
            try:
                pos = int(m.get("pos", -1))
            except (TypeError, ValueError):
                continue
            if pos < 0 or pos >= n_positions:
                continue
            label = str(m.get("label", ""))
            color = str(m.get("color", "#10B981"))
            x = pos * POS_UNIT_PX + POS_UNIT_PX // 2
            marker_parts.append(
                f'<div class="rs-feeder-marker" '
                f'style="left:{x}px;border-color:{color};">'
                f'<div class="rs-feeder-cap" style="background:{color};"></div>'
                f'<div class="rs-feeder-label" style="background:{color};">{label}</div>'
                f'</div>'
            )
        markers_html = "".join(marker_parts)

    # Pointe de vis (type 13) — terminaison MÉCANIQUE géométriquement intégrée.
    # Plus d'overlay colorisé, plus de sticker UI : la pointe est l'extension
    # physique de la matière, obtenue par
    #   1. un clip-path polygon sur rs-screw-area qui taillade le shaft, l'hélice
    #      et les stripes en cône triangulaire sur les ~140 derniers pixels →
    #      la même matière qui transporte s'effile en pointe, sans rupture,
    #   2. un apex métallique (rs-tip-apex) posé À la fin du cône, colorisé
    #      selon l'invariant (vert verrouillé / ambre restauré / rouge absent),
    #      pulsant si la pointe est absente. C'est la "tête" mécanique de la
    #      pointe, attachée à la vis — pas un badge flottant.
    tip_p1 = tip_part1_pos if tip_part1_pos is not None else n_positions - 2
    tip_x = tip_p1 * POS_UNIT_PX
    tip_color, tip_label_short, tip_pulse = {
        "valid": ("#10B981", _t("tip.valid"), ""),
        "missing": ("#EF4444", _t("tip.missing"), " rs-tip-pulse"),
        "deduplicated": ("#F59E0B", _t("tip.deduplicated"), ""),
    }.get(tip_status, ("#10B981", _t("tip.valid"), ""))

    # Apex de pointe — capuchon métallique colorisé posé exactement à l'apex
    # géométrique du cône. Sibling de rs-screw-area → PAS clippé par le
    # polygon → reste visible au bout du cône comme une tête de pointe. Sa
    # couleur reflète l'état de l'invariant ; pulse si pointe absente.
    apex_size = 10
    tip_apex_html = (
        f'<div class="rs-tip-apex{tip_pulse}" '
        f'style="left:{inner_w - apex_size // 2}px;'
        f'--tip-color:{tip_color};" '
        f'title="Pointe · {tip_label_short} — élément physique unique, '
        f'non déplaçable, non duplicable"></div>'
    )

    # Flux matière : streak chaud qui se déplace gauche → droite à travers
    # la vis. Posé DANS rs-screw-area → soumis au clip conique à la sortie.
    # Tonalité chaude qui suggère la matière chauffée par cisaillement.
    flux_html = '<div class="rs-flux" aria-hidden="true"></div>'

    # Bandeau flux matière — réduit au minimum industriel : ancre Entrée à
    # gauche, rail qui matérialise la direction du convoyage.
    flow_banner_html = (
        f'<div class="rs-flow-banner" style="--tip-color:{tip_color};">'
        '<span class="rs-flow-port rs-flow-in">'
        '<span class="rs-flow-dot"></span>Entrée matière'
        '</span>'
        '<span class="rs-flow-rail" aria-hidden="true"></span>'
        '</div>'
    )

    container_total_h = (
        CONTAINER_HEIGHT_PX
        + FLOW_BANNER_HEIGHT_PX + FLOW_BANNER_GAP_PX
        + (zone_strip_h + ZONE_STRIP_GAP_PX if show_zones and zone_starts else 0)
    )

    css = _ASSEMBLY_CSS.format(
        container_h=CONTAINER_HEIGHT_PX,
        shaft_h=SHAFT_HEIGHT_PX,
        helix_h=HELIX_HEIGHT_PX,
        stripe_h=STRIPE_HEIGHT_PX,
        stripe_op=STRIPE_OPACITY,
        tip_fade_half=TIP_FADE_PCT // 2,
        tip_fade=TIP_FADE_PCT,
        zone_h=ZONE_STRIP_HEIGHT_PX,
        zone_gap=ZONE_STRIP_GAP_PX,
        container_total_h=container_total_h,
        flow_h=FLOW_BANNER_HEIGHT_PX,
        flow_gap=FLOW_BANNER_GAP_PX,
    )

    body = (
        f'<div class="rs-container" style="height:{container_total_h}px;">'
        f'<div class="rs-inner" style="width:{inner_w}px;">'
        + flow_banner_html
        + zones_html
        + f'<div class="rs-screw-area">'
        f'<div class="rs-shaft"></div>'
        + base_layer_html
        + helix_layers
        + block_layers
        + flux_html
        + f'<div class="rs-row">'
        + "".join(slots_html)
        + "</div>"
        + markers_html
        + "</div>"
        + tip_apex_html
        + "</div></div>"
    )
    return f"<style>{css}</style>{body}"


_ASSEMBLY_CSS = """
.rs-container {{
  height:{container_total_h}px;
  background:linear-gradient(180deg,#1A1A1F 0%,#0A0A0E 100%);
  border:1px solid #2A2A35; border-radius:4px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.06),
             inset 0 -2px 4px rgba(0,0,0,0.5);
  overflow-x:auto; overflow-y:hidden;
}}
.rs-inner {{
  position:relative; height:100%;
  display:flex; flex-direction:column;
}}

/* Bandeau flux matière — un seul châssis horizontal qui ancre la direction
   du procédé (Entrée à gauche, Sortie à droite) ET porte le statut de
   pointe (couleur du port "Sortie" = état de l'invariant). Pas de bulle
   flottante détachée : tout est aligné dans le même rail.                  */
.rs-flow-banner {{
  position:relative; flex:0 0 {flow_h}px;
  display:flex; align-items:center; gap:10px;
  padding:0 10px; margin-bottom:{flow_gap}px;
  background:linear-gradient(180deg,#15161B 0%,#0E0F13 100%);
  border-top:1px solid #1F2937;
  border-bottom:1px solid #1F2937;
  font-size:0.66rem; font-weight:700; letter-spacing:0.06em;
  text-transform:uppercase;
}}
.rs-flow-port {{
  display:inline-flex; align-items:center; gap:6px;
  white-space:nowrap; flex:0 0 auto;
}}
.rs-flow-in  {{ color:#10B981; }}
.rs-flow-in  .rs-flow-dot {{
  background:#10B981;
  box-shadow:0 0 6px rgba(16,185,129,0.7);
}}
.rs-flow-dot {{
  width:7px; height:7px; border-radius:50%;
  flex:0 0 auto;
}}
/* Rail métallique fin entre les deux ports : suggère la canalisation de
   l'extrudeuse. Animation de "convoyage" subtile (chevrons qui défilent à
   l'intérieur du rail).                                                     */
.rs-flow-rail {{
  flex:1 1 auto; height:2px; position:relative; overflow:hidden;
  background:linear-gradient(90deg,
    rgba(16,185,129,0.55) 0%,
    rgba(75,85,99,0.45) 18%,
    rgba(75,85,99,0.45) 82%,
    color-mix(in srgb, var(--tip-color) 55%, transparent) 100%);
  border-radius:1px;
}}
.rs-flow-rail::after {{
  content:""; position:absolute; top:0; left:-30%;
  width:30%; height:100%;
  background:linear-gradient(90deg,
    transparent 0%,
    rgba(255,255,255,0.55) 50%,
    transparent 100%);
  animation:rs-flow-rail-shimmer 4.5s linear infinite;
}}
@keyframes rs-flow-rail-shimmer {{
  0%   {{ left:-30%; }}
  100% {{ left:130%; }}
}}

/* Apex de pointe — capuchon métallique colorisé posé À l'apex géométrique
   du cône. rs-screw-area est clippée en triangle, mais .rs-tip-apex est
   son sibling → vit en-dehors du clip et reste visible. C'est la "tête de
   pointe" qui prolonge la vis, PAS un badge UI flottant. */
.rs-tip-apex {{
  position:absolute;
  bottom:calc({container_h}px / 2 - 5px);
  width:10px; height:10px; border-radius:50%;
  background:radial-gradient(circle at 35% 30%,
    color-mix(in srgb, var(--tip-color) 90%, white) 0%,
    var(--tip-color) 55%,
    color-mix(in srgb, var(--tip-color) 70%, black) 100%);
  box-shadow:0 0 8px var(--tip-color),
             0 0 18px color-mix(in srgb, var(--tip-color) 35%, transparent),
             inset 0 -1px 1.5px rgba(0,0,0,0.45),
             inset 0 1px 1px rgba(255,255,255,0.35);
  z-index:8;
  pointer-events:auto;
  cursor:help;
}}
@keyframes rs-tip-pulse {{
  0%, 100% {{ opacity:0.85; }}
  50%      {{ opacity:1.0; }}
}}
.rs-tip-pulse {{ animation:rs-tip-pulse 1.4s ease-in-out infinite; }}

/* Flux matière — streak chaud qui défile gauche → droite à travers la vis,
   suggérant le convoyage physique de la masse. Tonalité chaude (255,225,180)
   qui rappelle la matière chauffée par cisaillement. Soumis au clip-path
   conique de rs-screw-area → s'éteint avec la pointe.                       */
.rs-flux {{
  position:absolute; top:50%; transform:translateY(-50%);
  left:0; right:0; height:{helix_h}px;
  background:linear-gradient(90deg,
    transparent 0%,
    transparent 28%,
    rgba(255,225,180,0.10) 42%,
    rgba(255,240,210,0.32) 49%,
    rgba(255,250,235,0.46) 50%,
    rgba(255,240,210,0.32) 51%,
    rgba(255,225,180,0.10) 58%,
    transparent 72%,
    transparent 100%);
  background-size:200% 100%;
  background-repeat:no-repeat;
  mix-blend-mode:screen;
  pointer-events:none;
  z-index:3;
  animation:rs-flux-shimmer 5s linear infinite;
}}
@keyframes rs-flux-shimmer {{
  0%   {{ background-position:-100% 0; }}
  100% {{ background-position:200% 0; }}
}}

.rs-zones-bar {{
  position:relative; flex:0 0 auto;
  margin-bottom:{zone_gap}px;
}}
.rs-zone-cell {{
  position:absolute; top:0;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  background:#0F1419;
  border-top:1px solid #1F2937;
  border-bottom:1px solid #1F2937;
  border-left:1px solid #1F2937;
  letter-spacing:0.04em; padding:1px 0;
}}
.rs-zone-cell:last-child {{ border-right:1px solid #1F2937; }}
.rs-zone-label {{
  font-size:0.72rem; font-weight:600; color:#9CA3AF;
  line-height:1.1;
}}
.rs-zone-sub {{
  font-size:0.62rem; font-weight:500; color:#6B7280;
  line-height:1.05; margin-top:1px;
  font-variant-numeric:tabular-nums;
}}

/* Marqueurs feeder (Main feeder, Side feeder) — tirets verticaux étiquetés.
   Superposés sur la vis : trait pointillé + petit cap coloré + label en haut.
   z-index 6 → au-dessus de la vis et des stripes (z-index 5).               */
.rs-feeder-marker {{
  position:absolute; top:0; bottom:0; width:0;
  border-left:2px dashed #10B981;
  z-index:6; pointer-events:none;
}}
.rs-feeder-cap {{
  position:absolute; top:50%; left:-4px;
  width:6px; height:6px; border-radius:50%;
  transform:translateY(-50%);
  box-shadow:0 0 0 2px #0B0F14;
}}
.rs-feeder-label {{
  position:absolute; top:-2px; left:4px;
  padding:1px 5px; border-radius:0 0.2rem 0.2rem 0;
  font-size:0.62rem; font-weight:700;
  color:#0B0F14; letter-spacing:0.04em;
  white-space:nowrap;
}}

.rs-screw-area {{
  position:relative; flex:1 1 {container_h}px;
  min-height:{container_h}px;
  /* Pointe conique géométrique : tout le contenu (shaft, hélice, contre-hélice
     chaotic, stripes, flux) est clippé en triangle sur les 140 derniers
     pixels. La pointe N'EST PAS un overlay : c'est l'extension physique de
     la même matière, qui s'effile naturellement en cône comme un vrai screw
     tip mécanique. Pas de fade alpha — une vraie géométrie. */
  clip-path:polygon(
    0% 0%,
    calc(100% - 140px) 0%,
    100% 50%,
    calc(100% - 140px) 100%,
    0% 100%);
  -webkit-clip-path:polygon(
    0% 0%,
    calc(100% - 140px) 0%,
    100% 50%,
    calc(100% - 140px) 100%,
    0% 100%);
}}

.rs-shaft {{
  position:absolute; top:50%; left:0; right:0;
  transform:translateY(-50%);
  height:{shaft_h}px;
  background:linear-gradient(180deg,
    #13131A 0%,#2E2E36 8%,#5A5E68 22%,#9CA0AA 38%,#D2D6E0 50%,
    #9CA0AA 62%,#5A5E68 78%,#2E2E36 92%,#13131A 100%);
  box-shadow:inset 0 1px 1.5px rgba(255,255,255,0.22),
             inset 0 -2.5px 3px rgba(0,0,0,0.55);
  z-index:1; pointer-events:none;
}}

/* Base universelle — pattern de la VIS PRINCIPALE (forward conveying à
   +72°) couvrant toute l'étendue placée. Lecture mécanique dominante :
   c'est UNE vis continue, pas un assemblage de modules. Les overlays
   spécialisés se posent par-dessus et MODULENT cette base sans la
   remplacer. NE PAS toucher à z-index sans révision globale. */
.rs-helix-base {{
  position:absolute; top:50%; transform:translateY(-50%);
  height:{helix_h}px;
  z-index:2; pointer-events:none;
}}

/* Overlays spécialisés (helix non-forward + blocs) — signatures géométriques
   BOLD locales (pleine palette métallique, opacity 0.85-0.95, blend normal)
   posées sur la base universelle. Continuité préservée via :
     1. EDGE-MASK en POURCENTAGE (18%/82%) → fondu latéral qui scale avec la
        largeur du run : 1 slot (40px) = fade 7px, 2 slots (80px) = fade
        14px, run de 5 slots (200px) = fade 36px. Toujours proportionnel.
     2. La base universelle reste visible AVANT et APRÈS le run, donc le run
        est toujours encadré par la vis principale.
     3. opacity / blend / height portés INLINE par run via _OVERLAY_PARAMS
        (chaque type a sa signature mécanique calibrée).
   Le toothed (type 11) utilise `height: 42px` au lieu de 56 pour suggérer
   un rotor à plus petit diamètre — la base apparaît au-dessus/en-dessous,
   créant une vraie variation de profil radial.                            */
.rs-helix-overlay,
.rs-block-overlay {{
  position:absolute; top:50%; transform:translateY(-50%);
  z-index:3; pointer-events:none;
  -webkit-mask-image:linear-gradient(90deg,
    rgba(0,0,0,0) 0%,rgba(0,0,0,1) 18%,
    rgba(0,0,0,1) 82%,rgba(0,0,0,0) 100%);
  mask-image:linear-gradient(90deg,
    rgba(0,0,0,0) 0%,rgba(0,0,0,1) 18%,
    rgba(0,0,0,1) 82%,rgba(0,0,0,0) 100%);
}}

.rs-row {{
  position:relative; z-index:3; height:100%;
  display:flex; align-items:stretch; gap:0; font-size:0;
}}
.rs-slot {{
  height:100%; flex:0 0 auto; position:relative;
  background-color:transparent;
}}
.rs-empty {{ background:transparent; }}
.rs-stripe-only {{ background:transparent; }}

.rs-stripe {{
  position:absolute; top:0; left:0; right:0;
  height:{stripe_h}px; opacity:{stripe_op};
  z-index:5; pointer-events:none;
}}

.rs-screw-area::after {{
  content:""; position:absolute; top:0; left:0;
  height:100%; width:100%;
  background:linear-gradient(180deg,
    rgba(0,0,0,0.30) 0%, rgba(0,0,0,0.05) 18%,
    rgba(0,0,0,0) 35%, rgba(0,0,0,0) 65%,
    rgba(0,0,0,0.05) 82%, rgba(0,0,0,0.30) 100%);
  pointer-events:none; z-index:4;
}}

.rs-container::-webkit-scrollbar {{ height:8px; }}
.rs-container::-webkit-scrollbar-track {{ background:#0D1117; }}
.rs-container::-webkit-scrollbar-thumb {{
  background:#374151; border-radius:4px;
}}
"""


# ---------------------------------------------------------------------------
# Lecture métier — éléments par zone
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PlacedElement:
    pos: int
    zone: int
    zone_name: str
    type_id: int
    label: str
    role: str


def list_placed_elements(
    cfg: list[int],
    n_positions: int,
    *,
    base_type_fn,
    is_part2_fn,
    position_to_zone_fn,
    element_label_fn,
) -> list[PlacedElement]:
    """Parcourt la config et liste tous les éléments placés (1ère partie seulement)."""
    out: list[PlacedElement] = []
    for i in range(n_positions):
        v = cfg[i]
        if is_part2_fn(v):
            continue
        bt = base_type_fn(v)
        if bt == 0:
            continue
        zone = position_to_zone_fn(i)
        zone_name = f"Z{zone}"
        role = _element_role(bt)
        label = element_label_fn(bt)
        out.append(PlacedElement(
            pos=i, zone=zone, zone_name=zone_name,
            type_id=bt, label=label, role=role,
        ))
    return out


# ---------------------------------------------------------------------------
# Lecture globale profil + régime procédé (assistant ingénieur extrusion SSB).
#
# Consommé par Home / Profile / Settings pour afficher en 1 phrase :
#   « Profil dispersif intense × Régime rapide → vous courez 3 risques :
#     dégradation liant, surcouple, hétérogénéité. Voici 25/30/40 et pourquoi. »
#
# La classification combine la STRUCTURE de la vis (proportions conv/mix, zones
# vides, distribution spatiale) et le RÉGIME procédé (rpm, débit, densité bulk).
# Ne touche pas à la logique métier — uniquement à la lecture haut-niveau.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProcessProfile:
    archetype: str             # libellé long : "Profil convectif dominant"
    archetype_short: str       # libellé court : "convectif"
    archetype_severity: str    # info | warning | critique | ok | neutre
    summary: str               # 1-2 phrases ingénieur
    regime: str                # "Régime rapide" | "Régime modéré" | "Régime lent"
    regime_short: str          # "rapide" | "modéré" | "lent"
    regime_summary: str        # implication procédé du régime
    risks: tuple[str, ...]     # 1-3 risques mis en avant par l'agent
    metrics: dict              # comptages bruts pour audit / tests


def _classify_regime(rpm: float, feed: float, dens: float, ff: float) -> tuple[str, str, str]:
    """Régime procédé d'après les paramètres Settings + Fill Factor courant.

    Renvoie (label long, label court, implication métier 1 phrase).
    Les seuils sont alignés sur la pratique TSE diamètre 10,5 mm (Rondol).
    """
    # Règle saturation / sous-alimentation domine sur le couple rpm·débit.
    if ff > 0.70:
        return (
            _t("sr.regime.saturated"), _t("sr.regime.saturated.short"),
            _t("sr.regime.saturated.sum", ff=f"{ff*100:.0f}"),
        )
    if 0 < ff < 0.18:
        return (
            _t("sr.regime.starved"), _t("sr.regime.starved.short"),
            _t("sr.regime.starved.sum", ff=f"{ff*100:.0f}"),
        )
    # Régime nominal : croisement rpm × débit.
    if rpm >= 200 and feed >= 50:
        return (
            _t("sr.regime.fast"), _t("sr.regime.fast.short"),
            _t("sr.regime.fast.sum", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
        )
    if rpm <= 80 and feed <= 15:
        return (
            _t("sr.regime.slow"), _t("sr.regime.slow.short"),
            _t("sr.regime.slow.sum", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
        )
    return (
        _t("sr.regime.moderate"), _t("sr.regime.moderate.short"),
        _t("sr.regime.moderate.sum",
           rpm=f"{rpm:.0f}", feed=f"{feed:.0f}", dens=f"{dens:.2f}"),
    )


def analyze_profile(
    cfg: list[int],
    rpm: float,
    feed: float,
    dens: float,
    *,
    base_type_fn,
    is_part2_fn,
    position_to_zone_fn,
    fill_factor_fn,
    n_positions: int,
    main_feeder_pos: int,
    tip_part1_pos: int,
) -> ProcessProfile:
    """Classifie le profil global + régime procédé pour l'agent IA."""
    n_conv = n_short = n_knead = n_reverse = n_chaotic = n_distrib = 0
    n_filled = 0
    zone_counts: dict[int, int] = {z: 0 for z in range(9)}

    for i in range(main_feeder_pos, tip_part1_pos):
        v = cfg[i]
        if is_part2_fn(v):
            continue
        bt = base_type_fn(v)
        if bt == 0:
            continue
        n_filled += 1
        zone_counts[position_to_zone_fn(i)] += 1
        if bt in (1, 2, 6):
            n_conv += 1
        elif bt == 3:
            n_short += 1
        elif bt in (4, 5, 7, 8):
            n_knead += 1
        elif bt == 9:
            n_reverse += 1
        elif bt == 10:
            n_chaotic += 1
        elif bt in (11, 12):
            n_distrib += 1

    n_mix = n_knead + n_chaotic + n_distrib
    ff = fill_factor_fn(cfg, rpm, feed, dens)
    empty_zones = sum(1 for z in range(1, 8) if zone_counts.get(z, 0) == 0)
    spatial_max = max(zone_counts.values()) if n_filled else 0
    spatial_imbalance = (spatial_max / n_filled) if n_filled > 0 else 0.0

    # Régime procédé (indépendant de l'archetype)
    regime, regime_short, regime_summary = _classify_regime(rpm, feed, dens, ff)

    metrics = {
        "n_filled": n_filled,
        "n_conv": n_conv + n_short,
        "n_knead": n_knead,
        "n_chaotic": n_chaotic,
        "n_distrib": n_distrib,
        "n_reverse": n_reverse,
        "n_mix": n_mix,
        "ff": ff,
        "empty_zones": empty_zones,
        "spatial_imbalance": spatial_imbalance,
        "rpm": rpm,
        "feed": feed,
        "dens": dens,
    }

    # ---- Archetype : prioritisé du plus aigu au plus nominal ----
    if n_filled == 0:
        return ProcessProfile(
            archetype=_t("sr.arch.empty"),
            archetype_short=_t("sr.arch.empty.short"),
            archetype_severity="info",
            summary=_t("sr.arch.empty.sum"),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.empty.risk"),),
            metrics=metrics,
        )

    if n_filled < 8:
        return ProcessProfile(
            archetype=_t("sr.arch.minimal"),
            archetype_short=_t("sr.arch.minimal.short"),
            archetype_severity="warning",
            summary=_t("sr.arch.minimal.sum", n=n_filled),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.minimal.risk1"), _t("sr.arch.minimal.risk2")),
            metrics=metrics,
        )

    # Densité bulk élevée → mention spécifique (charges céramiques)
    bulk_note = (
        _t("sr.bulk_note", dens=f"{dens:.2f}") if dens >= 1.5 else ""
    )

    if spatial_imbalance > 0.60:
        max_zone = max(zone_counts, key=zone_counts.get)
        return ProcessProfile(
            archetype=_t("sr.arch.imbalanced"),
            archetype_short=_t("sr.arch.imbalanced.short"),
            archetype_severity="warning",
            summary=_t("sr.arch.imbalanced.sum",
                       nmax=spatial_max, n=n_filled, z=max_zone,
                       pct=f"{spatial_imbalance*100:.0f}", bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.imbalanced.risk1"), _t("sr.arch.imbalanced.risk2")),
            metrics=metrics,
        )

    if n_chaotic >= 4 and n_chaotic / n_filled >= 0.20:
        return ProcessProfile(
            archetype=_t("sr.arch.chaotic"),
            archetype_short=_t("sr.arch.chaotic.short"),
            archetype_severity="info",
            summary=_t("sr.arch.chaotic.sum",
                       n=n_chaotic, pct=f"{n_chaotic/n_filled*100:.0f}",
                       bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.chaotic.risk1"), _t("sr.arch.chaotic.risk2")),
            metrics=metrics,
        )

    if (n_knead + n_chaotic) / n_filled >= 0.45:
        return ProcessProfile(
            archetype=_t("sr.arch.dispersive"),
            archetype_short=_t("sr.arch.dispersive.short"),
            archetype_severity="critique",
            summary=_t("sr.arch.dispersive.sum",
                       n=n_knead + n_chaotic,
                       pct=f"{(n_knead+n_chaotic)/n_filled*100:.0f}",
                       bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.dispersive.risk1"), _t("sr.arch.dispersive.risk2"),
                   _t("sr.arch.dispersive.risk3")),
            metrics=metrics,
        )

    if (n_conv + n_short) / n_filled >= 0.65 and n_mix / n_filled < 0.20:
        return ProcessProfile(
            archetype=_t("sr.arch.convective"),
            archetype_short=_t("sr.arch.convective.short"),
            archetype_severity="warning",
            summary=_t("sr.arch.convective.sum",
                       n=n_conv + n_short,
                       pct=f"{(n_conv+n_short)/n_filled*100:.0f}",
                       nmix=n_mix, bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.convective.risk1"), _t("sr.arch.convective.risk2")),
            metrics=metrics,
        )

    if (n_distrib + n_chaotic) / n_filled >= 0.30:
        return ProcessProfile(
            archetype=_t("sr.arch.distributive"),
            archetype_short=_t("sr.arch.distributive.short"),
            archetype_severity="info",
            summary=_t("sr.arch.distributive.sum",
                       n=n_distrib + n_chaotic,
                       pct=f"{(n_distrib+n_chaotic)/n_filled*100:.0f}",
                       bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.distributive.risk1"),),
            metrics=metrics,
        )

    if empty_zones >= 3:
        return ProcessProfile(
            archetype=_t("sr.arch.underused"),
            archetype_short=_t("sr.arch.underused.short"),
            archetype_severity="warning",
            summary=_t("sr.arch.underused.sum", n=empty_zones, bulk=bulk_note),
            regime=regime, regime_short=regime_short, regime_summary=regime_summary,
            risks=(_t("sr.arch.underused.risk1"), _t("sr.arch.underused.risk2")),
            metrics=metrics,
        )

    # Aucun motif aigu → équilibré.
    return ProcessProfile(
        archetype=_t("sr.arch.balanced"),
        archetype_short=_t("sr.arch.balanced.short"),
        archetype_severity="ok",
        summary=_t("sr.arch.balanced.sum",
                   nconv=n_conv + n_short, nmix=n_mix, nrev=n_reverse,
                   ff=f"{ff*100:.0f}", bulk=bulk_note),
        regime=regime, regime_short=regime_short, regime_summary=regime_summary,
        risks=(),
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Recommandations IA — règles métier (structure étendue 4 champs)
# ---------------------------------------------------------------------------
# Chaque reco renvoyée par compute_recommendations contient désormais 8 clés :
#
#   severity : "critique" | "warning" | "info" | "ok"
#   zone     : "Z3" | "Feed" | "—"  (zone procédé concernée, "—" si global)
#   physics  : phrase courte 2-5 mots — phénomène physique (cisaillement,
#              transport, rétention, dispersion, chauffe…)
#   impact   : phrase courte 2-5 mots — conséquence procédé/produit
#              (homogénéité, dégradation liant, capacité, surcouple…)
#   action   : phrase complète orientée décision — quoi faire, où, comment.
#              Cite les paramètres procédé (rpm/feed/dens) quand pertinents.
#   evidence : 1 phrase de mesures (chiffres : FF %, n_éléments, ratio…)
#   title    : compatibilité ascendante — synthèse 1 ligne
#   detail   : compatibilité ascendante — phrase action complète
#
# Les anciens consommateurs lisent title/detail. Les nouveaux affichent les
# 4 champs structurés (zone / physics / impact / action) côte à côte.
# ---------------------------------------------------------------------------
def compute_recommendations(
    cfg: list[int],
    rpm: float,
    feed: float,
    dens: float,
    *,
    base_type_fn,
    is_part2_fn,
    position_to_zone_fn,
    fill_factor_fn,
    n_positions: int,
    main_feeder_pos: int,
    tip_part1_pos: int,
) -> list[dict]:
    """Recommandations métier — structure 8 clés (cf. doc module).

    L'agent IA prend en compte rpm / feed / dens pour ajuster sévérité et
    actions chiffrées. La sortie est triée par sévérité décroissante.
    """
    def _rec(severity: str, zone: str, physics: str, impact: str,
             action: str, *, evidence: str = "") -> dict:
        """Produit une reco enrichie + champs title/detail rétrocompat."""
        title = f"{zone} — {physics}" if zone and zone != "—" else physics
        detail = action if not evidence else f"{action} ({evidence})"
        return {
            "severity": severity,
            "zone": zone or "—",
            "physics": physics,
            "impact": impact,
            "action": action,
            "evidence": evidence,
            "title": title,
            "detail": detail,
        }

    # Comptages par catégorie
    n_conv = 0       # convoyage (1, 2, 6)
    n_short = 0      # convoyage compact (3)
    n_knead = 0      # mélange dispersif (4, 5, 7, 8)
    n_reverse = 0    # rétention (9)
    n_chaotic = 0    # mélange chaotique (10)
    n_distrib = 0    # mélange distributif (11, 12)
    n_filled = 0
    zone_counts: dict[int, int] = {z: 0 for z in range(9)}
    zone_mixers: dict[int, int] = {z: 0 for z in range(9)}    # kneading + chaotic + distrib par zone
    first_mixer_zone: int | None = None

    for i in range(main_feeder_pos, tip_part1_pos):
        v = cfg[i]
        if is_part2_fn(v):
            continue
        bt = base_type_fn(v)
        if bt == 0:
            continue
        n_filled += 1
        z = position_to_zone_fn(i)
        zone_counts[z] = zone_counts.get(z, 0) + 1
        if bt in (1, 2, 6):
            n_conv += 1
        elif bt == 3:
            n_short += 1
        elif bt in (4, 5, 7, 8):
            n_knead += 1
            zone_mixers[z] = zone_mixers.get(z, 0) + 1
            if first_mixer_zone is None:
                first_mixer_zone = z
        elif bt == 9:
            n_reverse += 1
        elif bt == 10:
            n_chaotic += 1
            zone_mixers[z] = zone_mixers.get(z, 0) + 1
            if first_mixer_zone is None:
                first_mixer_zone = z
        elif bt in (11, 12):
            n_distrib += 1
            zone_mixers[z] = zone_mixers.get(z, 0) + 1

    ff = fill_factor_fn(cfg, rpm, feed, dens)
    recs: list[dict] = []

    # Modulateurs procédé : majorent la sévérité et chiffrent les actions.
    rpm_intense = rpm >= 200
    rpm_low = rpm <= 80
    feed_high = feed >= 50
    feed_low = feed <= 15
    dens_high = dens >= 1.5  # charges céramiques (LFP, NMC, LLZO…)

    def _esc(severity: str, condition: bool, level: str = "critique") -> str:
        """Escalade la sévérité si la condition procédé l'exige."""
        order = ["ok", "info", "warning", "critique"]
        if condition and order.index(severity) < order.index(level):
            return level
        return severity

    # Vis vide
    if n_filled == 0:
        recs.append(_rec(
            "info", "—", _t("sr.arch.empty"),
            _t("sr.empty.rec_impact"),
            _t("sr.empty.rec_action"),
            evidence=_t("sr.empty.rec_evidence"),
        ))
        return recs

    # Configuration trop courte (mélange insuffisant pour SSB)
    if 0 < n_filled < 8:
        recs.append(_rec(
            "warning", "Global",
            _t("sr.rec.underdense.title"),
            _t("sr.rec.underdense.physics"),
            _t("sr.rec.underdense.action",
               add_min=18 - n_filled, add_max=25 - n_filled,
               rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
            evidence=_t("sr.rec.underdense.evidence", n=n_filled),
        ))

    # Manque de convoyage
    if n_conv + n_short < 3:
        recs.append(_rec(
            "critique", "Global",
            _t("sr.rec.no_conv.title"),
            _t("sr.rec.no_conv.physics"),
            _t("sr.rec.no_conv.action", need=3 - (n_conv+n_short), feed=f"{feed:.0f}"),
            evidence=_t("sr.rec.no_conv.evidence", n=n_conv + n_short),
        ))

    # Ratio convoyage/mélange déséquilibré (trop de conveying)
    n_mix_total = n_knead + n_chaotic + n_distrib
    if n_filled >= 12 and n_mix_total > 0 and (n_conv + n_short) / max(1, n_mix_total) > 4.0:
        ratio = (n_conv + n_short) / max(1, n_mix_total)
        recs.append(_rec(
            _esc("warning", rpm_intense or feed_high, "critique"),
            "Global",
            _t("sr.rec.conv_dominant.title"),
            _t("sr.rec.conv_dominant.physics"),
            _t("sr.rec.conv_dominant.action", rpm=f"{rpm:.0f}"),
            evidence=f"ratio C/M = {ratio:.1f}:1",
        ))

    # Trop de kneading (risque surchauffe / sur-cisaillement)
    if n_knead + n_chaotic >= 8 or (n_filled >= 10 and (n_knead + n_chaotic) / n_filled > 0.45):
        hot_zones = sorted(
            [z for z in range(1, 9) if zone_mixers.get(z, 0) >= 3],
            key=lambda z: zone_mixers.get(z, 0),
            reverse=True,
        )
        target_zone = f"Z{hot_zones[0]}" if hot_zones else "Global"
        loc = (
            _t("sr.rec.excess_knead.loc", z=hot_zones[0], n=zone_mixers[hot_zones[0]])
            if hot_zones else ""
        )
        sev = _esc("critique", rpm_intense or dens_high, "critique")
        abrasion_note = (
            _t("sr.rec.excess_knead.abrasion", dens=f"{dens:.2f}") if dens_high else ""
        )
        _intensity = _t("sr.rec.excess_knead.amplified") if rpm_intense else _t("sr.rec.excess_knead.moderate")
        recs.append(_rec(
            sev, target_zone,
            _t("sr.rec.excess_knead.title"),
            _t("sr.rec.excess_knead.physics"),
            _t("sr.rec.excess_knead.action",
               loc=loc, abrasion=abrasion_note,
               rpm=f"{rpm:.0f}", intensity=_intensity),
            evidence=_t("sr.rec.excess_knead.evidence",
                        n=n_knead+n_chaotic,
                        pct=f"{(n_knead+n_chaotic)/max(1,n_filled)*100:.0f}"),
        ))

    # Aucun mélange
    if n_filled >= 5 and n_knead + n_chaotic + n_distrib == 0:
        recs.append(_rec(
            "warning", "Global",
            _t("sr.rec.no_mix.title"),
            _t("sr.rec.no_mix.physics"),
            _t("sr.rec.no_mix.action", feed=f"{feed:.0f}"),
            evidence=_t("sr.rec.no_mix.evidence"),
        ))

    # Surcharge zone (> 6 éléments dans une seule zone)
    overloaded = [z for z, n in zone_counts.items() if n > 6]
    for z in overloaded:
        neighbors = [zn for zn in (z - 1, z + 1) if 1 <= zn <= 7
                     and zone_counts.get(zn, 0) < 4]
        if not neighbors:
            neighbors = [zn for zn in (z - 1, z + 1) if 1 <= zn <= 7]
        nb_text = (
            _t("sr.rec.overloaded.action_nb",
               zones=" / ".join(f"**Z{zn}**" for zn in neighbors))
            if neighbors else ""
        )
        recs.append(_rec(
            _esc("warning", rpm_intense, "critique"),
            f"Z{z}",
            _t("sr.rec.overloaded.title"),
            _t("sr.rec.overloaded.physics"),
            _t("sr.rec.overloaded.action", nb=nb_text, rpm=f"{rpm:.0f}"),
            evidence=_t("sr.rec.overloaded.evidence", n=zone_counts[z], z=z),
        ))

    # Mélange tardif (premier mixer après Z4)
    if first_mixer_zone is not None and first_mixer_zone >= 5:
        recs.append(_rec(
            "warning", f"Z{first_mixer_zone}",
            _t("sr.rec.late_mix.title"),
            _t("sr.rec.late_mix.physics"),
            _t("sr.rec.late_mix.action", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
            evidence=_t("sr.rec.late_mix.evidence", z=first_mixer_zone),
        ))

    # Aucun mélange dans Z1-Z4 alors que la vis a >= 6 éléments
    if n_filled >= 6 and sum(zone_mixers.get(z, 0) for z in range(1, 5)) == 0 \
            and n_knead + n_chaotic + n_distrib > 0:
        early_filled = [z for z in range(1, 5) if zone_counts.get(z, 0) > 0]
        target_zone = early_filled[0] + 1 if early_filled else 2
        if target_zone > 4:
            target_zone = 4
        recs.append(_rec(
            "info", f"Z{target_zone}",
            _t("sr.rec.no_early.title"),
            _t("sr.rec.no_early.physics"),
            _t("sr.rec.no_early.action", z=target_zone),
            evidence=_t("sr.rec.no_early.evidence"),
        ))

    # Déséquilibre fort (> 60% des éléments dans une seule zone)
    if n_filled >= 8:
        max_zone = max(zone_counts, key=zone_counts.get)
        ratio_max = zone_counts[max_zone] / n_filled
        if ratio_max > 0.60:
            recs.append(_rec(
                "warning", f"Z{max_zone}",
                _t("sr.rec.imbalance.title"),
                _t("sr.rec.imbalance.physics"),
                _t("sr.rec.imbalance.action", pct=f"{ratio_max*100:.0f}"),
                evidence=_t("sr.rec.imbalance.evidence",
                            n=zone_counts[max_zone], total=n_filled, z=max_zone),
            ))

    # Trop de rétention
    if n_reverse > 2:
        recs.append(_rec(
            _esc("warning", rpm_low, "critique"),
            "Global",
            _t("sr.rec.excess_rev.title"),
            _t("sr.rec.excess_rev.physics"),
            _t("sr.rec.excess_rev.action", rpm=f"{rpm:.0f}"),
            evidence=_t("sr.rec.excess_rev.evidence", n=n_reverse),
        ))

    # Zones vides en aval du feeder — UNE reco par zone (action localisée).
    empty_zones_downstream = [
        z for z in range(1, 8)
        if zone_counts.get(z, 0) == 0 and zone_counts.get(z - 1, 0) > 0
    ]
    _bulk_sev = "critique" if len(empty_zones_downstream) >= 3 else "warning"
    for z in empty_zones_downstream[:3]:
        if z <= 3:
            physics = _t("sr.rec.empty_zone.transport")
            impact = _t("sr.rec.empty_zone.transport_impact")
            action = _t("sr.rec.empty_zone.transport_action", z=z, feed=f"{feed:.0f}")
        elif z <= 6:
            target = _t("sr.rec.mix_target_dispersive") if z <= 5 else _t("sr.rec.mix_target_distributive")
            physics = (_t("sr.rec.empty_zone.no_shear")
                       if z <= 5 else _t("sr.rec.empty_zone.no_finish"))
            impact = (_t("sr.rec.empty_zone.no_shear_impact") if z <= 5
                      else _t("sr.rec.empty_zone.no_finish_impact"))
            purpose = (_t("sr.rec.empty_zone.dispersion") if z <= 5
                       else _t("sr.rec.empty_zone.distribution"))
            action = _t("sr.rec.empty_zone.mix_action",
                        target=target, z=z, purpose=purpose)
        else:
            physics = _t("sr.rec.empty_zone.no_transport")
            impact = _t("sr.rec.empty_zone.no_transport_impact")
            action = _t("sr.rec.empty_zone.end_action", z=z)
        recs.append(_rec(
            _bulk_sev, f"Z{z}", physics, impact, action,
            evidence=_t("sr.rec.empty_zone.evidence"),
        ))

    # Remplissage faible — modulé par paramètres procédé
    if 0 < ff < 0.20:
        if feed_low:
            action = _t("sr.rec.starved.action_feed", feed=f"{feed:.0f}")
        elif rpm >= 200:
            action = _t("sr.rec.starved.action_rpm", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}")
        else:
            action = _t("sr.rec.starved.action_default", feed=f"{feed:.0f}")
        recs.append(_rec(
            "warning", "Global",
            _t("sr.rec.starved.title"),
            _t("sr.rec.starved.physics"),
            action,
            evidence=f"FF {ff*100:.1f} %",
        ))

    # Surcharge
    if ff > 0.85:
        recs.append(_rec(
            "critique", "Global",
            _t("sr.rec.saturated.title"),
            _t("sr.rec.saturated.physics"),
            _t("sr.rec.saturated.action",
               feed=f"{feed:.0f}", target_feed=f"{max(5, feed*0.7):.0f}",
               rpm=f"{rpm:.0f}", target_rpm=f"{rpm*1.3:.0f}"),
            evidence=f"FF {ff*100:.1f} %",
        ))

    # Bonne configuration
    if not recs:
        recs.append(_rec(
            "ok", "Global",
            _t("sr.rec.balanced.title"),
            _t("sr.rec.balanced.physics"),
            _t("sr.rec.balanced.action",
               rpm=f"{rpm:.0f}", feed=f"{feed:.0f}", dens=f"{dens:.2f}"),
            evidence=f"Conv {n_conv+n_short} · Mix {n_mix_total} · Rev {n_reverse} · FF {ff*100:.0f} %",
        ))

    # Suggestion finale : distributif terminal localisé Z6-Z7
    if n_knead > 0 and n_distrib == 0 and n_filled < 35:
        candidates = sorted([6, 7], key=lambda z: zone_counts.get(z, 0))
        target_zone = candidates[0]
        recs.append(_rec(
            "info", f"Z{target_zone}",
            _t("sr.rec.no_distrib.title"),
            _t("sr.rec.no_distrib.physics"),
            _t("sr.rec.no_distrib.action", z=target_zone),
            evidence=f"{n_knead} disp · 0 distrib",
        ))

    # -----------------------------------------------------------------------
    # Garde « pas d'élément inventé » (règle manager) : on retire toute reco
    # qui cite un type d'élément ABSENT de la config courante. La version
    # canonique de cette logique est screw_logic.recommendation_cites_absent_element ;
    # on la réplique ici en local pour préserver le découplage de screw_render
    # (qui reçoit base_type_fn / is_part2_fn par injection, sans importer screw_logic).
    # -----------------------------------------------------------------------
    _present: set[int] = set()
    for _v in cfg:
        if _v == 0 or is_part2_fn(_v):
            continue
        _bt = base_type_fn(_v)
        if _bt in (0, 13):
            continue
        _present.add(_bt)
    # IMPORTANT — table dupliquée volontairement (cf. commentaire ci-dessus pour
    # le découplage). DOIT rester synchronisée avec
    # screw_logic.ELEMENT_MENTION_TOKENS (manager 2026-06-09 : ajout des tokens
    # d'angle Kneading 30/45/60/90 pour bloquer les recos qui citent un angle
    # absent du profil — bug observé : profil avec seulement Kneading 60°,
    # reco qui mentionnait « Kneading 90° » passait le filtre collectif).
    _ELEMENT_TOKENS = (
        # Tokens collectifs.
        ("kneading", {4, 5, 7, 8}), ("malaxage", {4, 5, 7, 8}), ("malaxeur", {4, 5, 7, 8}),
        ("convoyage", {1, 2, 9}), ("conveying", {1, 2, 9}),
        ("short-pitch", {3}), ("pas court", {3}),
        ("large pitch", {6}), ("grand pas", {6}),
        ("chaotic", {10}), ("chaotique", {10}),
        ("toothed", {11}), ("dentelé", {11}),
        ("special mixing", {12}), ("mélange spécial", {12}),
        ("reverse", {9}),
        # Tokens d'angle SPÉCIFIQUE (Kneading 30/45/60/90 = types 5/8/7/4).
        ("kneading 90", {4}), ("malaxage 90", {4}),
        ("kneading 30", {5}), ("malaxage 30", {5}),
        ("kneading 60", {7}), ("malaxage 60", {7}),
        ("kneading 45", {8}), ("malaxage 45", {8}),
        # Tokens d'angle NUS (manager 2026-06-10) : bloquent les formes
        # « Malaxage (90° dispersif + 30/45° distributif) » qui échappaient aux
        # tokens composés à cause de la ponctuation. Sans risque côté
        # températures : celles-ci s'écrivent « 200 °C » (espace avant °).
        ("90°", {4}), ("30°", {5}), ("60°", {7}), ("45°", {8}),
    )

    def _cites_absent(r: dict) -> bool:
        txt = " ".join(
            str(r.get(k, "")) for k in
            ("physics", "impact", "action", "title", "detail", "evidence")
        ).lower()
        return any(
            tok in txt and _present.isdisjoint(types)
            for tok, types in _ELEMENT_TOKENS
        )

    recs = [r for r in recs if not _cites_absent(r)]

    # Repli générique élément-agnostique si la garde a tout retiré (config non vide).
    if not recs:
        recs.append(_rec(
            "info", "Global",
            _t("sr.rec.fallback.title"),
            _t("sr.rec.fallback.physics"),
            _t("sr.rec.fallback.action", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
            evidence=_t("sr.rec.fallback.evidence"),
        ))

    # Tri par sévérité décroissante
    sev_order = {"critique": 0, "warning": 1, "info": 2, "ok": 3}
    recs.sort(key=lambda r: sev_order.get(r.get("severity", "info"), 4))
    return recs


# ---------------------------------------------------------------------------
# Décision : combien d'éléments choisir ? (25 · 30 · 40)
#
# MODÈLE DE SCORING — pas une cascade de règles fixes.
#
# Pour chaque candidat L ∈ {25, 30, 40}, on additionne des contributions
# signées issues de 4 critères métier indépendants, chacun mesuré sur la
# config courante :
#
#   1. Taux de remplissage (Fill Factor moyen)
#       → vide / faible / modéré / élevé / saturation
#       → favorise des vis courtes quand la matière transite peu, longues
#         quand la vis sature.
#
#   2. Ratio mélange (n_mélangeurs / n_éléments)
#       → 0 % / léger / standard / dispersif / extrême
#       → favorise 25 pour le transport pur, 40 pour la dispersion poussée.
#
#   3. Ratio kneading / convoyage
#       → mesure l'intensité de cisaillement par rapport au transport.
#       → un kneading dominant pousse vers 40 (intercaler du convoyage de
#         refroidissement entre les blocs de cisaillement).
#
#   4. Zones procédé vides (Z1..Z7)
#       → indique si le profil utilise effectivement la longueur disponible.
#       → beaucoup de zones vides → vis effective courte → 25.
#
# Tie-breaker : 30 (compromis le plus polyvalent). Confiance dérivée de la
# marge entre le top-1 et le top-2 des scores totaux.
# ---------------------------------------------------------------------------
COUNT_CANDIDATES: tuple[int, ...] = (25, 30, 40)


@dataclass(frozen=True)
class CountScoringCriterion:
    """Un critère de scoring.

    `summary` : libellé court métier (3-4 mots, prêt à afficher).
    `measured`: valeur mesurée associée (ex. "45 %", "2 zones vides").
    `reasoning` : phrase longue (audit / debug, pas affichée par défaut).
    `scores` : contribution signée à chaque candidat (interne, pas affiché).
    """
    name: str                      # "Taux de remplissage"
    measured: str                  # "32 %"
    summary: str                   # "Remplissage modéré"
    scores: dict[int, float]       # interne — non affiché
    reasoning: str                 # interne — non affiché par défaut


@dataclass(frozen=True)
class CountAlternative:
    count: int
    score: float                   # interne — non affiché
    summary: str                   # "Plus de capacité"
    sentence: str                  # phrase claire pour l'ingénieur


@dataclass(frozen=True)
class ActionStep:
    """Action priorisée pour l'ingénieur extrusion SSB.

    `priority` ∈ {"main", "secondary", "option"} :
        - "main"      : action principale (1 max, la plus urgente)
        - "secondary" : actions correctives complémentaires (0-2)
        - "option"    : cadrage stratégique selon objectif (toujours 1)
    `body` : phrase complète, doit citer les paramètres (rpm, feed, ff, …)
    qui justifient l'action quand c'est pertinent.
    """
    priority: str
    body: str


@dataclass(frozen=True)
class CountRecommendation:
    suggested: int                              # candidat retenu (25/30/40)
    rationale: str                              # phrase courte (pas de score)
    tagline: str                                # contexte ultra-court (~3 mots)
    severity: str                               # info / warning
    confidence: str                             # high / medium / low
    candidate_scores: dict[int, float]          # interne — pas affiché
    criteria: list[CountScoringCriterion]
    alternatives: list[CountAlternative]
    benefits: list[str]                         # "ce que ça apporte"
    risks: list[str]                            # "points de vigilance"
    action_steps: tuple[ActionStep, ...] = ()   # actions priorisées
    why_optimal: str = ""                       # prose ingénieur 2-3 phrases
    archetype: str = ""                         # archetype profil (analyze_profile)
    regime: str = ""                            # régime procédé (analyze_profile)


# Bénéfices et risques inhérents à chaque longueur de vis.
# Tirés de la pratique TSE : résidence ∝ L/D, capacité ∝ 1/L, dissipation
# thermique ∝ L (séjour long → plus de chaleur cumulée).
def _count_benefits(n: int) -> list[str]:
    return [_t(f"sr.count.benefit.{n}.{i}") for i in (1, 2, 3)]


def _count_tagline(n: int) -> str:
    return _t(f"sr.count.tagline.{n}")


def _count_risks(n: int) -> list[str]:
    if n == 30:
        return [_t(f"sr.count.risk.{n}.{i}") for i in (1, 2)]
    return [_t(f"sr.count.risk.{n}.{i}") for i in (1, 2, 3)]

# Pour chaque transition (suggested → alt) : (titre court, phrase claire).
# Phrasé orienté décision : "ce que je gagne / ce que je perds si je choisis L".
def _count_alt_detail(src: int, dst: int) -> tuple[str, str]:
    key = f"sr.count.alt.{src}_{dst}"
    return (_t(f"{key}.title"), _t(f"{key}.sentence"))


# Chaque _score_* retourne : (scores, measured, summary, reasoning).
# Scores et reasoning servent à l'agrégation/audit ; summary et measured
# sont les seuls champs poussés à l'UI.

def _score_fill_rate(ff: float) -> tuple[dict[int, float], str, str, str]:
    pct = ff * 100
    if ff < 0.15:
        return ({25: +3, 30: +1, 40: -2}, f"{pct:.0f} %",
                _t("sr.score.starved"), _t("sr.score.starved.r"))
    if ff < 0.35:
        return ({25: +1, 30: +3, 40: 0}, f"{pct:.0f} %",
                _t("sr.score.fill_moderate"), _t("sr.score.fill_moderate.r"))
    if ff < 0.55:
        return ({25: -1, 30: +3, 40: +1}, f"{pct:.0f} %",
                _t("sr.score.fill_balanced"), _t("sr.score.fill_balanced.r"))
    if ff < 0.75:
        return ({25: -2, 30: +1, 40: +3}, f"{pct:.0f} %",
                _t("sr.score.fill_high"), _t("sr.score.fill_high.r"))
    return ({25: -3, 30: 0, 40: +3}, f"{pct:.0f} %",
            _t("sr.score.fill_sat"), _t("sr.score.fill_sat.r"))


def _score_mix_ratio(
    n_mix: int, n_filled: int,
) -> tuple[dict[int, float], str, str, str]:
    if n_filled == 0:
        return ({25: 0, 30: 0, 40: 0}, "—",
                _t("sr.score.no_element"), _t("sr.score.no_element.r"))
    ratio = n_mix / n_filled
    pct = ratio * 100
    if n_mix == 0:
        return ({25: +3, 30: 0, 40: -2}, "0 %",
                _t("sr.score.transport_pure"), _t("sr.score.transport_pure.r"))
    if ratio < 0.15:
        return ({25: +2, 30: +2, 40: -1}, f"{pct:.0f} %",
                _t("sr.score.mix_light"), _t("sr.score.mix_light.r", n=n_mix))
    if ratio < 0.35:
        return ({25: -1, 30: +3, 40: +1}, f"{pct:.0f} %",
                _t("sr.score.mix_balanced"), _t("sr.score.mix_balanced.r", n=n_mix, pct=f"{pct:.0f}"))
    if ratio < 0.55:
        return ({25: -2, 30: +1, 40: +3}, f"{pct:.0f} %",
                _t("sr.score.mix_dispersive"), _t("sr.score.mix_dispersive.r", n=n_mix, pct=f"{pct:.0f}"))
    return ({25: -3, 30: -1, 40: +3}, f"{pct:.0f} %",
            _t("sr.score.mix_extreme"), _t("sr.score.mix_extreme.r", pct=f"{pct:.0f}"))


def _score_knead_conv(
    n_knead: int, n_chaotic: int, n_conv: int, n_short: int,
) -> tuple[dict[int, float], str, str, str]:
    n_k = n_knead + n_chaotic
    n_c = n_conv + n_short
    measured = f"{n_k} mix. · {n_c} conv."
    if n_c == 0 and n_k == 0:
        return ({25: 0, 30: 0, 40: 0}, "—",
                _t("sr.score.no_signal"), _t("sr.score.no_signal.r"))
    if n_c == 0:
        return ({25: -3, 30: -1, 40: +3}, measured,
                _t("sr.score.shear_no_conv"), _t("sr.score.shear_no_conv.r"))
    ratio = n_k / n_c
    if n_k == 0:
        return ({25: +2, 30: +1, 40: -1}, measured,
                _t("sr.score.conv_only"), _t("sr.score.conv_only.r"))
    if ratio < 0.30:
        return ({25: +1, 30: +3, 40: 0}, measured,
                _t("sr.score.conv_dominant"), _t("sr.score.conv_dominant.r", ratio=f"{ratio:.2f}"))
    if ratio < 0.70:
        return ({25: -1, 30: +2, 40: +2}, measured,
                _t("sr.score.shear_balanced"), _t("sr.score.shear_balanced.r", ratio=f"{ratio:.2f}"))
    return ({25: -2, 30: 0, 40: +3}, measured,
            _t("sr.score.shear_dominant"), _t("sr.score.shear_dominant.r", ratio=f"{ratio:.2f}"))


def _score_empty_zones(
    zone_counts: dict[int, int],
) -> tuple[dict[int, float], str, str, str]:
    """Critère 4 : nombre de zones procédé vides (Z1..Z7)."""
    empty = [z for z in range(1, 8) if zone_counts.get(z, 0) == 0]
    n = len(empty)
    if n == 0:
        return ({25: 0, 30: +2, 40: +1},
                _t("sr.score.zone_measured_0"),
                _t("sr.score.zones_full"), _t("sr.score.zones_full.r"))
    measured = _t("sr.score.zone_measured_1", n=n) if n == 1 else _t("sr.score.zone_measured_n", n=n)
    zlist = ", ".join(f"Z{z}" for z in empty)
    if n <= 2:
        return ({25: +1, 30: +2, 40: 0}, measured,
                _t("sr.score.zones_compact"),
                _t("sr.score.zones_compact.r", m=measured, zlist=zlist))
    if n <= 4:
        return ({25: +3, 30: 0, 40: -2}, measured,
                _t("sr.score.zones_underused"),
                _t("sr.score.zones_underused.r", m=measured, zlist=zlist))
    return ({25: +3, 30: -1, 40: -3}, measured,
            _t("sr.score.zones_very_underused"),
            _t("sr.score.zones_very_underused.r", m=measured, zlist=zlist))


def _confidence_from_margin(scores: dict[int, float]) -> str:
    sorted_vals = sorted(scores.values(), reverse=True)
    margin = sorted_vals[0] - sorted_vals[1]
    if margin >= 4:
        return "high"
    if margin >= 2:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Actions priorisées : "à faire maintenant sur la vis" — assistant ingénieur
# extrusion SSB (Solid-State Battery) dry / semi-dry.
#
# La recommandation 25/30/40 répond à QUELLE LONGUEUR.
# La fonction ci-dessous répond à QUELLE ACTION et structure 3 niveaux :
#   - main      : 1 action principale (signal le plus critique)
#   - secondary : 0-2 actions correctives complémentaires
#   - option    : 1 cadrage stratégique aligné sur la longueur suggérée
#
# Chaque action référence explicitement les paramètres procédé qui la
# justifient (rpm, débit feeder, densité bulk, fill factor, résidence par
# zone) et, quand c'est pertinent, le risque côté formulation SSB :
#   - dégradation thermique du liant : PVDF se dégrade > 200 °C, PEO > 180 °C
#   - homogénéité poudre active : mélange dispersif insuffisant
#   - stabilité d'alimentation : sous- / sur-alimentation feeder
# ---------------------------------------------------------------------------

# Plages métier (extrusion TSE dry/semi-dry, formulations SSB courantes).
_FF_TARGET = (0.30, 0.55)        # taux de remplissage moyen visé
_FF_HIGH = 0.65                   # au-delà : saturation
_FF_LOW = 0.18                    # en deçà : vis sous-alimentée
_RESIDENCE_ZONE_MAX = 8.0         # s par zone — au-delà : risque cumul thermique

def _length_strategy(n: int) -> str:
    return _t(f"sr.count.strategy.{n}")


def _build_action_steps(
    *,
    suggested: int,
    n_filled: int,
    n_knead: int,
    n_chaotic: int,
    n_distrib: int,
    n_conv: int,
    n_short: int,
    n_reverse: int,
    ff: float,
    rpm: float,
    feed: float,
    dens: float,
    zone_counts: dict[int, int],
    zone_residence: list[float] | None = None,
) -> tuple[ActionStep, ...]:
    """Produit 1 main + 0-2 secondary + 1 option, priorisées et paramétrées.

    `zone_residence` : liste 9 floats (Feed + Z1..Z8) en secondes, optionnelle.
    Quand fournie, alimente les actions liées à la chauffe cumulée et à la
    distribution longitudinale du mélange.
    """
    n_mix = n_knead + n_chaotic + n_distrib

    # ----- Cas vis vide : amorcer + cadrage défaut -----
    if n_filled == 0:
        return (
            ActionStep("main", _t("sr.action.empty_main")),
            ActionStep(
                "option",
                _length_strategy(30),
            ),
        )

    # ----- Calculs dérivés réutilisés par plusieurs règles -----
    # Zone aval avec la plus longue résidence (signal chauffe cumulée).
    max_zone_idx = -1
    max_zone_t = 0.0
    if zone_residence and len(zone_residence) >= 9:
        for i in range(1, 9):                # Z1..Z8 (Feed exclu)
            if zone_residence[i] > max_zone_t:
                max_zone_t = zone_residence[i]
                max_zone_idx = i

    middle_empty = [z for z in (3, 4, 5, 6) if zone_counts.get(z, 0) == 0]
    crowded = [z for z, n in zone_counts.items() if n >= 4 and 1 <= z <= 7]

    # ----- Construction des candidats par priorité -----
    main_candidates: list[ActionStep] = []
    sec_candidates: list[ActionStep] = []

    if n_knead >= 7 and ff > 0.50:
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.thermal_binder",
               ff=f"{ff*100:.0f}", rpm=f"{rpm:.0f}", nk=n_knead),
        ))
    elif n_knead >= 9:
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.excess_shear", nk=n_knead, rpm=f"{rpm:.0f}"),
        ))

    if max_zone_idx >= 0 and max_zone_t > _RESIDENCE_ZONE_MAX and n_knead >= 4:
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.residence_cumul",
               zone=f"Z{max_zone_idx}", t=f"{max_zone_t:.1f}", nk=n_knead),
        ))

    if n_reverse >= 3:
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.reverse_excess", nr=n_reverse, rpm=f"{rpm:.0f}"),
        ))

    if n_mix < 2 and n_filled >= 6:
        missing = max(2, 3 - n_mix)
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.mix_deficit",
               nm=n_mix, feed=f"{feed:.0f}", missing=missing),
        ))

    if ff > 0.75:
        main_candidates.append(ActionStep(
            "main",
            _t("sr.action.saturation",
               ff=f"{ff*100:.0f}", feed=f"{feed:.0f}",
               dens=f"{dens:.2f}", rpm=f"{rpm:.0f}"),
        ))

    # === SECONDARY : améliorations qualité / utilisation longueur ===

    if n_distrib == 0 and n_filled >= 12 and suggested >= 30:
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.no_dispersive"),
        ))

    if len(crowded) == 1 and n_mix >= 4:
        z = crowded[0]
        target = "Z6" if z <= 4 else "Z3"
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.mix_concentrated",
               z=z, count=zone_counts[z], target=target),
        ))

    if len(middle_empty) >= 2 and n_filled >= 12:
        zones_str = _t("sr.action.zones_and").join(f"Z{z}" for z in middle_empty[:2])
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.zones_empty", zones=zones_str),
        ))

    if n_knead >= 7 and n_conv <= 4 and not main_candidates:
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.cooling_needed", nk=n_knead, nc=n_conv),
        ))

    if _FF_HIGH < ff <= 0.75:
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.ff_high",
               ff=f"{ff*100:.0f}", lo=int(_FF_TARGET[0]*100),
               hi=int(_FF_TARGET[1]*100), feed=f"{feed:.0f}",
               dens=f"{dens:.2f}"),
        ))
    elif ff < _FF_LOW and n_filled >= 6:
        sec_candidates.append(ActionStep(
            "secondary",
            _t("sr.action.ff_low",
               ff=f"{ff*100:.0f}", feed=f"{feed:.0f}", dens=f"{dens:.2f}"),
        ))

    # ----- Sélection finale -----
    # Règle : la principale doit refléter l'état réel. Si aucun signal main
    # n'a tiré mais des secondaires existent, on promeut la 1re secondaire
    # en principale (garantit cohérence main / secondary).
    actions: list[ActionStep] = []

    if main_candidates:
        actions.append(main_candidates[0])
        actions.extend(sec_candidates[:2])
    elif sec_candidates:
        promoted = sec_candidates[0]
        actions.append(ActionStep("main", promoted.body))
        actions.extend(sec_candidates[1:3])
    else:
        # Aucun signal : configuration saine, passer à l'essai pilote.
        actions.append(ActionStep(
            "main",
            _t("sr.action.nominal",
               n=n_filled, ff=f"{ff*100:.0f}",
               rpm=f"{rpm:.0f}", feed=f"{feed:.0f}"),
        ))

    actions.append(ActionStep("option", _length_strategy(suggested)))
    return tuple(actions)


def recommend_element_count(
    cfg: list[int],
    rpm: float,
    feed: float,
    dens: float,
    *,
    base_type_fn,
    is_part2_fn,
    fill_factor_fn,
    n_positions: int,
    main_feeder_pos: int,
    tip_part1_pos: int,
    position_to_zone_fn=None,
    zone_residence_fn=None,
) -> CountRecommendation:
    """Recommandation 25/30/40 par scoring multi-critères.

    Args:
        cfg, rpm, feed, dens: état config + paramètres procédé.
        base_type_fn, is_part2_fn: callables d'introspection (screw_logic).
        fill_factor_fn: callable (cfg, rpm, feed, dens) -> float.
        position_to_zone_fn: optionnel, callable position -> zone (pour
            critère "zones vides"). Si absent, déduction par tranches de 9.
        n_positions, main_feeder_pos, tip_part1_pos: bornes du parcours.

    Returns:
        CountRecommendation avec scores détaillés et impact des alternatives.
    """
    # Comptages par catégorie
    n_conv = n_short = n_knead = n_chaotic = n_distrib = n_reverse = 0
    n_filled = 0
    zone_counts: dict[int, int] = {z: 0 for z in range(9)}

    def _fallback_zone(pos: int) -> int:
        # 9 zones de 9 positions (0-8 = Feed, 9-17 = Z1, ...)
        return min(8, max(0, pos // 9))

    zone_fn = position_to_zone_fn or _fallback_zone

    for i in range(main_feeder_pos, tip_part1_pos):
        v = cfg[i]
        if is_part2_fn(v):
            continue
        bt = base_type_fn(v)
        if bt == 0:
            continue
        n_filled += 1
        zone_counts[zone_fn(i)] = zone_counts.get(zone_fn(i), 0) + 1
        if bt in (1, 2, 6):
            n_conv += 1
        elif bt == 3:
            n_short += 1
        elif bt in (4, 5, 7, 8):
            n_knead += 1
        elif bt == 9:
            n_reverse += 1
        elif bt == 10:
            n_chaotic += 1
        elif bt in (11, 12):
            n_distrib += 1

    n_mix = n_knead + n_chaotic + n_distrib
    ff = fill_factor_fn(cfg, rpm, feed, dens)
    zrt = (
        zone_residence_fn(cfg, rpm, feed, dens) if zone_residence_fn else None
    )

    def _build_alts(suggested: int, scores: dict[int, float]) -> list[CountAlternative]:
        alts: list[CountAlternative] = []
        for c in COUNT_CANDIDATES:
            if c == suggested:
                continue
            summary, sentence = _count_alt_detail(suggested, c)
            alts.append(CountAlternative(
                count=c, score=scores.get(c, 0.0),
                summary=summary, sentence=sentence,
            ))
        # Trier par score décroissant : l'alt la plus proche en premier.
        alts.sort(key=lambda a: a.score, reverse=True)
        return alts

    # Cas particulier : vis vide → défaut conservateur (30) avec critères
    # neutres et confiance basse. L'UI affiche "vis vide, à recalculer".
    if n_filled == 0:
        neutral = {25: 0.0, 30: 1.0, 40: 0.0}  # léger biais vers 30
        criteria = [
            CountScoringCriterion(
                name="Configuration",
                measured="—",
                summary=_t("sr.empty.count_summary"),
                scores=neutral,
                reasoning=_t("sr.empty.count_reasoning"),
            )
        ]
        return CountRecommendation(
            suggested=30,
            rationale=_t("sr.empty.count_rationale"),
            tagline=_t("sr.empty.count_tagline"),
            severity="warning",
            confidence="low",
            candidate_scores=neutral,
            criteria=criteria,
            alternatives=_build_alts(30, neutral),
            benefits=_count_benefits(30),
            risks=_count_risks(30),
            action_steps=_build_action_steps(
                suggested=30, n_filled=0,
                n_knead=0, n_chaotic=0, n_distrib=0,
                n_conv=0, n_short=0, n_reverse=0,
                ff=0.0, rpm=rpm, feed=feed, dens=dens,
                zone_counts=zone_counts, zone_residence=zrt,
            ),
        )

    # Construction des critères
    criteria: list[CountScoringCriterion] = []

    s, m, summ, r = _score_fill_rate(ff)
    criteria.append(CountScoringCriterion("Taux de remplissage", m, summ, s, r))

    s, m, summ, r = _score_mix_ratio(n_mix, n_filled)
    criteria.append(CountScoringCriterion("Proportion de mélange", m, summ, s, r))

    s, m, summ, r = _score_knead_conv(n_knead, n_chaotic, n_conv, n_short)
    criteria.append(CountScoringCriterion("Cisaillement vs transport", m, summ, s, r))

    s, m, summ, r = _score_empty_zones(zone_counts)
    criteria.append(CountScoringCriterion("Utilisation de la longueur", m, summ, s, r))

    # Bonus procédé : rpm × débit élevés → biais 25 (transit rapide).
    if rpm >= 200 and feed >= 50:
        process_scores = {25: +2, 30: 0, 40: -1}
        criteria.append(CountScoringCriterion(
            name=_t("sr.lbl.process_regime"),
            measured=f"{rpm:.0f} rpm · {feed:.0f} g/min",
            summary=_t("sr.regime.fast"),
            scores=process_scores,
            reasoning="Vitesse vis et débit élevés — transit rapide, le "
                      "bénéfice d'une vis longue est limité.",
        ))

    # Agrégation
    candidate_scores = {c: 0.0 for c in COUNT_CANDIDATES}
    for crit in criteria:
        for k, v in crit.scores.items():
            candidate_scores[k] += v

    # Choix : score max ; tie-break = préférence 30 puis 25 puis 40
    max_score = max(candidate_scores.values())
    tied = [c for c in COUNT_CANDIDATES if candidate_scores[c] == max_score]
    tie_priority = [30, 25, 40]
    suggested = next(c for c in tie_priority if c in tied)

    confidence = _confidence_from_margin(candidate_scores)

    # Rationale court (1 ligne).
    top = sorted(criteria, key=lambda c: c.scores.get(suggested, 0), reverse=True)
    top_drivers = [c.summary.lower() for c in top[:2]]
    rationale = (
        f"{suggested} éléments recommandés — décision portée par "
        f"{top_drivers[0]} et {top_drivers[1]}."
    )

    # Lecture profil + régime via analyze_profile pour le rationale long.
    if position_to_zone_fn is not None:
        profile = analyze_profile(
            cfg, rpm, feed, dens,
            base_type_fn=base_type_fn, is_part2_fn=is_part2_fn,
            position_to_zone_fn=position_to_zone_fn,
            fill_factor_fn=fill_factor_fn,
            n_positions=n_positions,
            main_feeder_pos=main_feeder_pos,
            tip_part1_pos=tip_part1_pos,
        )
        archetype_str = profile.archetype
        regime_str = profile.regime
        archetype_short = profile.archetype_short
        regime_short = profile.regime_short
    else:
        archetype_str = ""
        regime_str = ""
        archetype_short = "—"
        regime_short = "—"

    # "Pourquoi ce choix est optimal" — prose ingénieur procédé.
    # Construction en 3 phrases : (1) lecture du profil, (2) implication régime,
    # (3) conclusion sur la longueur retenue.
    intro = (
        f"Profil {archetype_short} × {regime_short}"
        if archetype_short != "—" else
        _t("sr.why.intro_config", n=n_filled)
    )

    if suggested == 25:
        why_phrase2 = _t("sr.why.25",
                         rpm=f"{rpm:.0f}", feed=f"{feed:.0f}", dens=f"{dens:.2f}")
    elif suggested == 30:
        why_phrase2 = _t("sr.why.30",
                         n_mix=n_mix, n_conv=n_conv+n_short,
                         ff=f"{ff*100:.0f}", rpm=f"{rpm:.0f}", feed=f"{feed:.0f}")
    else:
        why_phrase2 = _t("sr.why.40",
                         rpm=f"{rpm:.0f}", feed=f"{feed:.0f}", dens=f"{dens:.2f}",
                         n_disp=n_knead+n_chaotic)

    worst_count = min(candidate_scores, key=candidate_scores.get)
    worst_label = _count_tagline(worst_count)
    if worst_count != suggested:
        _alt_sentence = _count_alt_detail(suggested, worst_count)[1]
        why_phrase3 = _t("sr.why.alt",
                         worst=worst_count, label=worst_label,
                         detail=_alt_sentence or "—")
    else:
        why_phrase3 = ""

    why_optimal = (
        f"{intro}. {why_phrase2}"
        + (f" {why_phrase3}." if why_phrase3 else "")
    )

    severity = "info" if confidence != "low" else "warning"
    return CountRecommendation(
        suggested=suggested,
        rationale=rationale,
        tagline=_count_tagline(suggested),
        severity=severity,
        confidence=confidence,
        candidate_scores=candidate_scores,
        criteria=criteria,
        alternatives=_build_alts(suggested, candidate_scores),
        benefits=_count_benefits(suggested),
        risks=_count_risks(suggested),
        action_steps=_build_action_steps(
            suggested=suggested,
            n_filled=n_filled,
            n_knead=n_knead, n_chaotic=n_chaotic, n_distrib=n_distrib,
            n_conv=n_conv, n_short=n_short, n_reverse=n_reverse,
            ff=ff, rpm=rpm, feed=feed, dens=dens,
            zone_counts=zone_counts, zone_residence=zrt,
        ),
        why_optimal=why_optimal,
        archetype=archetype_str,
        regime=regime_str,
    )


# ---------------------------------------------------------------------------
# RAISONNEMENT GLOBAL PROCÉDÉ — couche systémique (assistant ingénieur).
#
# Les fonctions ci-dessus raisonnent par zone (analyze_profile, compute_reco,
# recommend_element_count). analyze_systemic ajoute la dernière couche :
# vision globale de l'équilibre vis × procédé. Pour chaque action poussée par
# le moteur local, on cherche :
#   1. Compensation     — quelle action ailleurs préserve l'équilibre global ?
#   2. Vérification     — la vis reste-t-elle cohérente après application ?
#   3. Trade-off        — qu'est-ce qu'on perd / qu'est-ce qu'on gagne ?
#   4. Synthèse finale  — état des 4 axes : dispersion, thermique, transport,
#                         capacité.
#
# La fonction est PURE (pas de Streamlit). Elle accepte en entrée le triplet
# (profile_reading, count_rec, recs) déjà calculé pour éviter la double
# recomputation, ou les recompute si non fournis.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Compensation:
    """Une compensation : action locale → ajustement ailleurs pour équilibre."""
    trigger: str        # "Réduction kneading Z4" — ce que l'action initiale change
    target_zone: str    # "Z6" — où compenser
    action: str         # phrase impérative chiffrée
    rationale: str      # 1 phrase : pourquoi cette compensation préserve l'équilibre


@dataclass(frozen=True)
class GlobalCheck:
    """Vérification systémique sur la vis dans son ensemble."""
    label: str          # "Cohérence globale du profil"
    status: str         # "ok" | "watch" | "alert"
    summary: str        # 1 phrase explicative


@dataclass(frozen=True)
class SynthesisAxis:
    """Un axe de la synthèse finale."""
    label: str          # "Dispersion"
    status: str         # "ok" | "watch" | "alert"
    detail: str         # "équilibrée" / "insuffisante en Z3" / …


@dataclass(frozen=True)
class DecisionSummary:
    """Version opérateur de la décision agent — 3 lignes lisibles en 3 s.

    Dérivée des mêmes données que `main_decision` (comps + overall + recs)
    avec un langage simplifié (pas de Z1/Z6/FF/kneading bruts). `main_decision`
    reste la version technique pour l'ingénieur procédé.
    """
    decision: str   # verdict simple, 1 phrase
    why: str        # problème principal en clair
    action: str     # action immédiate sans jargon


@dataclass(frozen=True)
class SystemicAnalysis:
    """Résultat de l'analyse systémique."""
    compensations: tuple[Compensation, ...]
    global_checks: tuple[GlobalCheck, ...]
    tradeoffs: tuple[str, ...]
    synthesis: tuple[SynthesisAxis, ...]
    overall_status: str          # "ok" | "watch" | "alert"
    overall_summary: str         # phrase ingénieur résumant l'équilibre global
    # Why_optimal du count_rec enrichi d'une 4e phrase « compromis assumé » :
    # explicite ce qu'on accepte de perdre (Y) et ce qui compense (Z), suivi
    # d'un verdict global. Vide si count_rec absent.
    why_optimal_enriched: str = ""
    # Couche décisionnelle (agent ingénieur) — dérivée de comps + overall +
    # sévérités locales, pas de duplication métier.
    main_decision: str = ""           # 1 phrase opérateur prioritaire (technique)
    decision_confidence: str = "medium"  # "high" | "medium" | "low"
    next_step: str = ""               # action immédiate à enclencher
    # Version opérateur (3 lignes, langage simplifié) de main_decision.
    # Construite à partir des mêmes données — pas de duplication métier.
    decision_summary: DecisionSummary | None = None
    # État de l'invariant pointe de vis (cf. screw_logic.enforce_tip_constraint).
    # "valid" | "missing" | "deduplicated".
    tip_status: str = "valid"
    # Positions amont où des occurrences parasites du type tip ont été
    # détectées (vide si tip_status != "deduplicated").
    tip_stray_positions: tuple[int, ...] = ()


# Sévérités locales → statut systémique
_LOCAL_TO_SYSTEMIC = {"critique": "alert", "warning": "watch", "info": "ok", "ok": "ok"}


def _zone_metrics(
    cfg: list[int],
    *,
    base_type_fn,
    is_part2_fn,
    position_to_zone_fn,
    main_feeder_pos: int,
    tip_part1_pos: int,
) -> dict:
    """Comptages détaillés par zone — réutilisés par toutes les règles."""
    zone_counts: dict[int, int] = {z: 0 for z in range(9)}
    zone_knead: dict[int, int] = {z: 0 for z in range(9)}
    zone_conv: dict[int, int] = {z: 0 for z in range(9)}
    zone_distrib: dict[int, int] = {z: 0 for z in range(9)}
    n_filled = n_knead = n_chaotic = n_distrib = n_conv = n_short = n_reverse = 0
    for i in range(main_feeder_pos, tip_part1_pos):
        v = cfg[i]
        if is_part2_fn(v):
            continue
        bt = base_type_fn(v)
        if bt == 0:
            continue
        z = position_to_zone_fn(i)
        zone_counts[z] += 1
        n_filled += 1
        if bt in (1, 2, 6):
            n_conv += 1
            zone_conv[z] += 1
        elif bt == 3:
            n_short += 1
            zone_conv[z] += 1
        elif bt in (4, 5, 7, 8):
            n_knead += 1
            zone_knead[z] += 1
        elif bt == 9:
            n_reverse += 1
        elif bt == 10:
            n_chaotic += 1
            zone_knead[z] += 1
        elif bt in (11, 12):
            n_distrib += 1
            zone_distrib[z] += 1
    return {
        "zone_counts": zone_counts,
        "zone_knead": zone_knead,
        "zone_conv": zone_conv,
        "zone_distrib": zone_distrib,
        "n_filled": n_filled,
        "n_knead": n_knead, "n_chaotic": n_chaotic, "n_distrib": n_distrib,
        "n_conv": n_conv, "n_short": n_short, "n_reverse": n_reverse,
    }


def _build_compensations(
    metrics: dict, recs: list[dict], ff: float, rpm: float, feed: float,
) -> list[Compensation]:
    """Pour chaque action critique/warning, propose une compensation ailleurs.

    Règles métier (équilibre vis SSB) :
      - réduction cisaillement → restaurer la dispersion via distributif aval
      - ajout d'éléments → vérifier impact FF (cible 30-55 %)
      - réduction débit / hausse rpm → ajuster la répartition mélange amont
      - limitation des reverse → compenser le débit avec convoyage aval
      - étalement spatial → vérifier que la zone d'arrivée n'est pas surchargée
    """
    comps: list[Compensation] = []
    zone_knead = metrics["zone_knead"]
    zone_counts = metrics["zone_counts"]
    n_distrib = metrics["n_distrib"]
    n_filled = metrics["n_filled"]
    n_knead = metrics["n_knead"] + metrics["n_chaotic"]
    n_conv = metrics["n_conv"] + metrics["n_short"]

    # 1) Cisaillement excessif → réduction du kneading + compensation par
    #    distributif terminal (préserve l'homogénéité globale).
    hot_zones = sorted(
        [z for z in range(1, 8) if zone_knead.get(z, 0) >= 3],
        key=lambda z: zone_knead.get(z, 0), reverse=True,
    )
    if hot_zones and (n_knead >= 7 or any(
        r.get("severity") == "critique" and "cisaillement" in r.get("physics", "").lower()
        for r in recs
    )):
        z_hot = hot_zones[0]
        z_target = max(6, z_hot + 2) if z_hot <= 5 else 7
        if z_target > 7:
            z_target = 7
        comps.append(Compensation(
            trigger=_t("sr.comp.knead_trigger_fmt", zone=z_hot, n=zone_knead[z_hot]),
            target_zone=f"Z{z_target}",
            action=_t("sr.comp.knead_action_fmt", target=z_target),
            rationale=_t("sr.comp.knead_rationale_fmt"),
        ))

    if 0 < n_filled < 15 and any(
        "densif" in r.get("action", "").lower() or "ajouter" in r.get("action", "").lower()
        for r in recs[:3]
    ):
        n_add_target = max(2, 18 - n_filled)
        ff_after = ff * (1 + n_add_target / max(1, n_filled))
        in_target = 0.30 <= ff_after <= 0.55
        _vrd = (
            _t("sr.comp.densify_verdict_in") if in_target
            else (_t("sr.comp.densify_verdict_above") if ff_after > 0.55
                  else _t("sr.comp.densify_verdict_below"))
        )
        verdict = _t("sr.comp.densify_ff_change",
                      ff0=f"{ff*100:.0f}", ff1=f"{ff_after*100:.0f}", verdict=_vrd)
        _adj = (
            _t("sr.comp.densify_adjust_free") if in_target
            else _t("sr.comp.densify_adjust_flow", feed=f"{feed:.0f}")
        )
        comps.append(Compensation(
            trigger=_t("sr.comp.densify_trigger_fmt", n=n_add_target),
            target_zone="Global",
            action=_t("sr.comp.densify_action_fmt", n=n_add_target, verdict=verdict, adjust=_adj),
            rationale=_t("sr.comp.densify_rationale_fmt"),
        ))

    if ff > 0.65:
        new_feed = max(5.0, feed * 0.7)
        new_rpm = rpm * 1.3
        comps.append(Compensation(
            trigger=_t("sr.comp.flow_trigger_fmt", feed0=f"{feed:.0f}", feed1=f"{new_feed:.0f}"),
            target_zone="Z2-Z3",
            action=_t("sr.comp.flow_action_fmt", rpm0=f"{rpm:.0f}", rpm1=f"{new_rpm:.0f}"),
            rationale=_t("sr.comp.flow_rationale_fmt"),
        ))

    if metrics["n_reverse"] > 2:
        last_rev_zone = max(
            (z for z in range(7, 0, -1) if zone_counts.get(z, 0) > 0),
            default=6,
        )
        z_target = min(7, last_rev_zone + 1)
        comps.append(Compensation(
            trigger=_t("sr.comp.reverse_trigger_fmt", n=metrics['n_reverse']),
            target_zone=f"Z{z_target}",
            action=_t("sr.comp.reverse_action_fmt", target=z_target, feed=f"{feed:.0f}"),
            rationale=_t("sr.comp.reverse_rationale_fmt"),
        ))

    crowded = [(z, n) for z, n in zone_counts.items() if n > 6 and 1 <= z <= 7]
    if crowded:
        z_src, n_src = crowded[0]
        candidates = [
            (zn, zone_counts.get(zn, 0)) for zn in (z_src - 1, z_src + 1)
            if 1 <= zn <= 7
        ]
        if candidates:
            z_dst, n_dst = min(candidates, key=lambda x: x[1])
            comps.append(Compensation(
                trigger=_t("sr.comp.move_trigger_fmt", zone=z_src, n=n_src),
                target_zone=f"Z{z_dst}",
                action=_t("sr.comp.move_action_fmt", dst=z_dst, n_dst=n_dst,
                           alt=z_dst+1 if z_dst < 7 else z_dst-1),
                rationale=_t("sr.comp.move_rationale_fmt"),
            ))

    if n_distrib == 0 and n_knead >= 5 and n_filled >= 12:
        comps.append(Compensation(
            trigger=_t("sr.comp.nodistrib_trigger"),
            target_zone="Z6-Z7",
            action=_t("sr.comp.nodistrib_action"),
            rationale=_t("sr.comp.nodistrib_rationale"),
        ))

    return comps


def _build_global_checks(
    metrics: dict, ff: float, zone_residence: list[float] | None,
) -> list[GlobalCheck]:
    """Vérifications systémiques sur l'ensemble de la vis."""
    checks: list[GlobalCheck] = []
    n_filled = metrics["n_filled"]
    n_knead = metrics["n_knead"] + metrics["n_chaotic"]
    n_conv = metrics["n_conv"] + metrics["n_short"]
    n_distrib = metrics["n_distrib"]
    zone_counts = metrics["zone_counts"]
    zone_knead = metrics["zone_knead"]

    _coh_lbl = _t("sr.check.coherence.label")
    if n_filled == 0:
        checks.append(GlobalCheck(
            label=_coh_lbl,
            status="watch",
            summary=_t("sr.empty.systemic_check"),
        ))
    else:
        ratio_mt = n_conv / max(1, n_knead) if n_knead else 99.0
        ok_ratio = 1.2 <= ratio_mt <= 5.0
        ok_distrib = (n_knead < 5) or (n_distrib >= 1)
        if ok_ratio and ok_distrib:
            checks.append(GlobalCheck(
                label=_coh_lbl,
                status="ok",
                summary=_t("sr.check.coherence.ok_full", ratio=f"{ratio_mt:.1f}", ndist=n_distrib),
            ))
        elif not ok_ratio:
            verdict = (
                _t("sr.check.coherence.too_much_transport")
                if ratio_mt > 5.0 else _t("sr.check.coherence.shear_dominant")
            )
            checks.append(GlobalCheck(
                label=_coh_lbl,
                status="watch" if 0.5 <= ratio_mt <= 8.0 else "alert",
                summary=_t("sr.check.coherence.watch", ratio=f"{ratio_mt:.1f}", verdict=verdict),
            ))
        else:
            checks.append(GlobalCheck(
                label=_coh_lbl,
                status="watch",
                summary=_t("sr.check.coherence.no_distrib", nk=n_knead),
            ))

    _bal_lbl = _t("sr.check.balance.label")
    if n_filled >= 6:
        pct_disp = (n_knead + n_distrib) / n_filled
        pct_conv = n_conv / n_filled
        diff = abs(pct_disp - pct_conv)
        _pc = f"{pct_conv*100:.0f}"
        _pd = f"{pct_disp*100:.0f}"
        if diff < 0.20:
            checks.append(GlobalCheck(
                label=_bal_lbl, status="ok",
                summary=_t("sr.check.balance.ok", pc=_pc, pd=_pd),
            ))
        elif diff < 0.40:
            checks.append(GlobalCheck(
                label=_bal_lbl, status="watch",
                summary=_t("sr.check.balance.watch", pc=_pc, pd=_pd),
            ))
        else:
            dom = "transport" if pct_conv > pct_disp else "mixing"
            checks.append(GlobalCheck(
                label=_bal_lbl, status="alert",
                summary=_t("sr.check.balance.alert", pc=_pc, pd=_pd, dom=dom),
            ))

    _deg_lbl = _t("sr.check.degrad.label")
    if zone_residence and len(zone_residence) >= 9:
        downstream_rt = max(zone_residence[6], zone_residence[7], zone_residence[8])
        downstream_knead = sum(zone_knead.get(z, 0) for z in (6, 7))
        _rt = f"{downstream_rt:.1f}"
        if downstream_rt > 8.0 and downstream_knead >= 3:
            checks.append(GlobalCheck(
                label=_deg_lbl, status="alert",
                summary=_t("sr.check.degrad.alert_rt", rt=_rt, nk=downstream_knead),
            ))
        elif downstream_rt > 6.0 and downstream_knead >= 2:
            checks.append(GlobalCheck(
                label=_deg_lbl, status="watch",
                summary=_t("sr.check.degrad.watch_rt", rt=_rt, nk=downstream_knead),
            ))
        else:
            checks.append(GlobalCheck(
                label=_deg_lbl, status="ok",
                summary=_t("sr.check.degrad.ok_rt", rt=_rt),
            ))
    else:
        downstream_knead = sum(zone_knead.get(z, 0) for z in (6, 7))
        if downstream_knead >= 4:
            checks.append(GlobalCheck(
                label=_deg_lbl, status="watch",
                summary=_t("sr.check.degrad.watch_no_rt", nk=downstream_knead),
            ))
        else:
            checks.append(GlobalCheck(
                label=_deg_lbl, status="ok",
                summary=_t("sr.check.degrad.ok_no_rt", nk=downstream_knead),
            ))

    _fill_lbl = _t("sr.lbl.fill_regime")
    _ffp = f"{ff*100:.0f}"
    if 0.30 <= ff <= 0.55:
        checks.append(GlobalCheck(
            label=_fill_lbl, status="ok",
            summary=_t("sr.check.fill.ok_target", ff=_ffp),
        ))
    elif ff < 0.18:
        checks.append(GlobalCheck(
            label=_fill_lbl, status="alert",
            summary=_t("sr.check.fill.alert_underfed", ff=_ffp),
        ))
    elif ff > 0.70:
        checks.append(GlobalCheck(
            label=_fill_lbl, status="alert",
            summary=_t("sr.check.fill.alert_saturated", ff=_ffp),
        ))
    else:
        checks.append(GlobalCheck(
            label=_fill_lbl, status="watch",
            summary=_t("sr.check.fill.watch_off", ff=_ffp),
        ))

    return checks


def _build_tradeoffs(
    comps: list[Compensation], recs: list[dict], metrics: dict,
) -> list[str]:
    """Phrases trade-off : pour chaque reco active, ce qu'on perd / ce qu'on gagne.

    Limite à 3 trade-offs (les plus structurants).
    """
    out: list[str] = []
    n_knead = metrics["n_knead"] + metrics["n_chaotic"]

    _knead_comp = next((c for c in comps if "kneading" in c.trigger.lower()), None)
    if _knead_comp:
        out.append(_t("sr.trade.knead", zone=_knead_comp.target_zone, target=_knead_comp.target_zone))

    _dens_comp = next((c for c in comps if "densif" in c.trigger.lower()), None)
    if _dens_comp:
        _det = _dens_comp.action.split(':')[1].strip() if ':' in _dens_comp.action else ''
        out.append(_t("sr.trade.densify", trigger=_dens_comp.trigger, detail=_det))

    if any("reverse" in c.trigger.lower() for c in comps):
        out.append(_t("sr.trade.reverse"))

    if any("feeder" in c.trigger.lower() for c in comps):
        out.append(_t("sr.trade.flow"))

    if not out and n_knead >= 6:
        out.append(_t("sr.trade.latent", nk=n_knead))

    return out[:3]


def _build_synthesis(
    metrics: dict, ff: float, zone_residence: list[float] | None,
) -> list[SynthesisAxis]:
    """Synthèse 4 axes : dispersion / thermique / transport / capacité."""
    n_filled = metrics["n_filled"]
    n_knead = metrics["n_knead"] + metrics["n_chaotic"]
    n_distrib = metrics["n_distrib"]
    n_conv = metrics["n_conv"] + metrics["n_short"]
    zone_knead = metrics["zone_knead"]

    out: list[SynthesisAxis] = []

    # AXE 1 — DISPERSION
    _disp = _t("sr.axis.dispersion")
    if n_filled == 0:
        out.append(SynthesisAxis(_disp, "watch", _t("sr.axis.not_evaluable")))
    else:
        pct_disp = (n_knead + n_distrib) / n_filled
        if pct_disp < 0.10:
            out.append(SynthesisAxis(
                _disp, "alert",
                _t("sr.axis.disp.insufficient", nk=n_knead+n_distrib, n=n_filled)
            ))
        elif pct_disp > 0.55:
            out.append(SynthesisAxis(
                _disp, "watch",
                _t("sr.axis.disp.excessive", pct=f"{pct_disp*100:.0f}")
            ))
        elif n_knead >= 4 and n_distrib == 0:
            out.append(SynthesisAxis(
                _disp, "watch",
                _t("sr.axis.disp.no_distrib")
            ))
        else:
            out.append(SynthesisAxis(
                _disp, "ok",
                _t("sr.axis.disp.balanced", nk=f"{pct_disp*100:.0f} %", ndist=n_distrib)
            ))

    # AXE 2 — THERMIQUE
    _therm = _t("sr.axis.thermal")
    hot_zones = [z for z in range(1, 8) if zone_knead.get(z, 0) >= 4]
    downstream_rt = (
        max(zone_residence[6], zone_residence[7], zone_residence[8])
        if zone_residence and len(zone_residence) >= 9 else 0.0
    )
    if hot_zones and downstream_rt > 8.0:
        out.append(SynthesisAxis(
            _therm, "alert",
            _t("sr.axis.therm.overload_downstream", zone=hot_zones[0], rt=f"{downstream_rt:.1f}")
        ))
    elif n_knead >= 8 or hot_zones:
        _conc = _t("sr.axis.therm.concentrated", zone=hot_zones[0]) if hot_zones else ""
        out.append(SynthesisAxis(
            _therm, "watch",
            _t("sr.axis.therm.cumulative", nk=n_knead) + _conc
        ))
    else:
        out.append(SynthesisAxis(
            _therm, "ok",
            _t("sr.axis.therm.no_overload", nk=n_knead)
        ))

    # AXE 3 — TRANSPORT
    _trans = _t("sr.axis.transport")
    if n_filled == 0:
        out.append(SynthesisAxis(_trans, "watch", _t("sr.axis.not_evaluable")))
    elif n_conv < 3:
        out.append(SynthesisAxis(
            _trans, "alert",
            _t("sr.axis.trans.undersized", nc=n_conv)
        ))
    elif n_conv / max(1, n_knead) < 0.5 and n_knead > 0:
        out.append(SynthesisAxis(
            _trans, "watch",
            _t("sr.axis.trans.deficit_vs", nc=n_conv, nk=n_knead)
        ))
    else:
        out.append(SynthesisAxis(
            _trans, "ok",
            _t("sr.axis.trans.maintained", nc=n_conv)
        ))

    # AXE 4 — CAPACITÉ / DÉBIT
    _cap = _t("sr.axis.capacity")
    _ffp = f"{ff*100:.0f}"
    if 0.30 <= ff <= 0.55:
        out.append(SynthesisAxis(
            _cap, "ok", _t("sr.axis.cap.target", ff=_ffp)
        ))
    elif ff < 0.18:
        out.append(SynthesisAxis(
            _cap, "alert", _t("sr.axis.cap.underfed", ff=_ffp)
        ))
    elif ff > 0.70:
        out.append(SynthesisAxis(
            _cap, "alert", _t("sr.axis.cap.saturated", ff=_ffp)
        ))
    else:
        out.append(SynthesisAxis(
            _cap, "watch", _t("sr.axis.cap.off_target", ff=_ffp)
        ))

    return out


def _systemic_overall(
    checks: list[GlobalCheck], synthesis: list[SynthesisAxis],
) -> tuple[str, str]:
    """Statut + phrase globale (worst-of, biaisé vers le diagnostic métier).

    Retourne (status, summary).
    """
    statuses = [c.status for c in checks] + [a.status for a in synthesis]
    if "alert" in statuses:
        overall = "alert"
    elif "watch" in statuses:
        overall = "watch"
    else:
        overall = "ok"

    parts: list[str] = []
    for axis in synthesis:
        if axis.status == "ok":
            parts.append(_t("sr.axis.ok_join", label=axis.label.lower(), word=axis.detail.split(' ')[0]))
        elif axis.status == "watch":
            parts.append(_t("sr.axis.watch_join", label=axis.label.lower(), detail=axis.detail))
        else:
            parts.append(_t("sr.axis.alert_join", label=axis.label.lower(), detail=axis.detail))

    parts_str = ", ".join(parts)
    if overall == "ok":
        summary = _t("sr.overall.ok", parts=parts_str)
    elif overall == "watch":
        summary = _t("sr.overall.watch", parts=parts_str)
    else:
        summary = _t("sr.overall.alert", parts=parts_str)
    return overall, summary


# Verdict global injecté en fin de phrase compromis selon overall_status.
def _enriched_verdict(status: str) -> str:
    _key = {"ok": "sr.verdict.ok", "watch": "sr.verdict.watch", "alert": "sr.verdict.alert"}
    return _t(_key.get(status, "sr.verdict.fallback"))


def _build_why_enriched(
    base_why: str,
    suggested: int,
    comps: list[Compensation],
    overall_status: str,
) -> str:
    """Enrichit `why_optimal` d'une 4e phrase exprimant le compromis global.

    Format : « Compromis assumé : on choisit N éléments au prix de Y,
    compensé par Z, ce qui [verdict global]. »

    Y et Z sont dérivés de la **compensation dominante** (`comps[0]`),
    déjà construite par `_build_compensations` — pas de duplication métier.
    Si aucune compensation n'est active et que l'équilibre global est OK,
    on appose une phrase de confirmation. Sinon, on retourne `base_why`
    inchangé (pas de trade-off fabulé).
    """
    if not base_why:
        return base_why
    if not comps:
        if overall_status == "ok":
            return f"{base_why} {_t('sr.enrich.no_comp')}"
        return base_why

    main = comps[0]
    trigger_lc = main.trigger.lower()
    target = main.target_zone

    if trigger_lc.startswith("réduction kneading"):
        parts = main.trigger.split()
        z_src = parts[2] if len(parts) >= 3 else "amont"
        cost = _t("sr.enrich.cost.knead", z_src=z_src)
        gain = _t("sr.enrich.gain.knead", target=target)
    elif "ajout de" in trigger_lc and "densification" in trigger_lc:
        cost = _t("sr.enrich.cost.densif")
        gain = _t("sr.enrich.gain.densif")
    elif trigger_lc.startswith("réduction débit"):
        cost = _t("sr.enrich.cost.flow")
        gain = _t("sr.enrich.gain.flow", target=target)
    elif trigger_lc.startswith("limitation des reverse"):
        cost = _t("sr.enrich.cost.reverse")
        gain = _t("sr.enrich.gain.reverse", target=target)
    elif trigger_lc.startswith("déplacement"):
        parts = main.trigger.split()
        z_src = parts[5] if len(parts) >= 6 else "amont"
        cost = _t("sr.enrich.cost.move", z_src=z_src)
        gain = _t("sr.enrich.gain.move", target=target)
    elif "cisaillement dispersif" in trigger_lc:
        cost = _t("sr.enrich.cost.dispersive")
        gain = _t("sr.enrich.gain.dispersive", target=target)
    else:
        return base_why

    verdict = _enriched_verdict(overall_status)
    sentence = _t("sr.enrich.sentence", n=suggested, cost=cost, gain=gain, verdict=verdict)
    return f"{base_why} {sentence}"


# ---------------------------------------------------------------------------
# Couche décisionnelle — agent ingénieur procédé.
#
# Trois sorties dérivées des données systémiques déjà calculées (pas de
# duplication métier) :
#   - main_decision        : 1 phrase opérateur, action prioritaire chiffrée
#   - decision_confidence  : "high" / "medium" / "low" (production / pilote / instable)
#   - next_step            : action immédiate à déclencher
# ---------------------------------------------------------------------------

def _decision_confidence(
    overall_status: str,
    n_comps: int,
    recs: list[dict],
    n_filled: int,
) -> str:
    """Niveau de confiance : combine overall_status, nombre de compensations
    et sévérité des recommandations locales."""
    if n_filled == 0:
        return "low"
    n_critique = sum(1 for r in recs if r.get("severity") == "critique")
    if overall_status == "alert" or n_critique >= 2 or n_comps >= 4:
        return "low"
    if overall_status == "watch" or n_critique >= 1 or n_comps >= 2:
        return "medium"
    return "high"


def _decision_action_phrase(main: Compensation, suggested: int) -> str:
    """Reformule la compensation dominante en directive opérateur (1 phrase).

    Pas de duplication métier : on lit `main.trigger` / `main.target_zone`
    déjà construits par `_build_compensations`.
    """
    trigger_lc = main.trigger.lower()
    target = main.target_zone

    if trigger_lc.startswith("réduction kneading"):
        parts = main.trigger.split()
        z_src = parts[2] if len(parts) >= 3 else "amont"
        return _t("sr.decide.keep_knead", n=suggested, z_src=z_src, target=target)
    if "ajout de" in trigger_lc and "densification" in trigger_lc:
        return _t("sr.decide.densify", n=suggested)
    if trigger_lc.startswith("réduction débit"):
        return _t("sr.decide.reduce_flow", n=suggested, target=target)
    if trigger_lc.startswith("limitation des reverse"):
        return _t("sr.decide.limit_reverse", n=suggested, target=target)
    if trigger_lc.startswith("déplacement"):
        parts = main.trigger.split()
        z_src = parts[5] if len(parts) >= 6 else "amont"
        return _t("sr.decide.spread", n=suggested, z_src=z_src, target=target)
    if "cisaillement dispersif" in trigger_lc:
        return _t("sr.decide.add_dispersive", n=suggested, target=target)
    return _t("sr.decide.generic", n=suggested, target=target)


def _decision_next_step(
    confidence: str, comps: list[Compensation], recs: list[dict],
) -> str:
    """Action immédiate à enclencher selon le niveau de confiance."""
    if confidence == "high":
        return _t("sr.next.pilot")
    if confidence == "medium":
        if comps:
            return _t("sr.next.validate_zone", zone=comps[0].target_zone)
        return _t("sr.next.validate_short")
    critique = next((r for r in recs if r.get("severity") == "critique"), None)
    if critique is not None:
        zone = (critique.get("zone") or "").strip()
        if zone in ("", "Global", "global"):
            return _t("sr.next.stabilize_process")
        return _t("sr.next.stabilize_target", target=zone)
    return _t("sr.next.stabilize_process")


def _build_decision_layer(
    suggested: int,
    comps: list[Compensation],
    recs: list[dict],
    overall_status: str,
    n_filled: int,
) -> tuple[str, str, str]:
    """Construit (main_decision, confidence, next_step)."""
    confidence = _decision_confidence(overall_status, len(comps), recs, n_filled)

    if n_filled == 0:
        decision = _t("sr.empty.decision")
    elif not comps:
        decision = _t("sr.decide.keep_config", n=suggested)
    else:
        decision = _decision_action_phrase(comps[0], suggested)

    next_step = _decision_next_step(confidence, comps, recs)
    return decision, confidence, next_step


# ---------------------------------------------------------------------------
# Couche opérateur — version 3-lignes (decision / why / action) du
# main_decision technique. Dérivée des MÊMES données (comps + overall + recs) :
# pas de duplication métier, juste une reformulation sans jargon Z1/Z6/FF.
# Lecture cible : 3 secondes, terrain.
# ---------------------------------------------------------------------------

def _operator_summary_from_comp(main: Compensation) -> tuple[str, str, str]:
    """Mappe la compensation dominante en (décision, pourquoi, action) opérateur.

    On lit les `trigger` déjà construits par `_build_compensations` — pas de
    re-calcul métier. Les Z1..Z7 sont remplacés par « amont / milieu / aval »
    pour la lisibilité opérateur.
    """
    trigger_lc = main.trigger.lower()

    if trigger_lc.startswith("réduction kneading"):
        return (_t("sr.op.knead.decision"), _t("sr.op.knead.why"), _t("sr.op.knead.action"))
    if "ajout de" in trigger_lc and "densification" in trigger_lc:
        return (_t("sr.op.densify.decision"), _t("sr.op.densify.why"), _t("sr.op.densify.action"))
    if trigger_lc.startswith("réduction débit"):
        return (_t("sr.op.flow.decision"), _t("sr.op.flow.why"), _t("sr.op.flow.action"))
    if trigger_lc.startswith("limitation des reverse"):
        return (_t("sr.op.reverse.decision"), _t("sr.op.reverse.why"), _t("sr.op.reverse.action"))
    if trigger_lc.startswith("déplacement"):
        return (_t("sr.op.spread.decision"), _t("sr.op.spread.why"), _t("sr.op.spread.action"))
    if "cisaillement dispersif" in trigger_lc:
        return (_t("sr.op.dispersive.decision"), _t("sr.op.dispersive.why"), _t("sr.op.dispersive.action"))
    return (_t("sr.op.fallback.decision"), _t("sr.op.fallback.why"), _t("sr.op.fallback.action"))


def _build_decision_summary(
    suggested: int,
    comps: list[Compensation],
    overall_status: str,
    n_filled: int,
    tip_status: str = "valid",
    tip_stray_count: int = 0,
) -> DecisionSummary:
    """Version opérateur 3-lignes — dérivée des mêmes données que la couche
    technique (`_build_decision_layer`), reformulée sans jargon.

    Si l'invariant pointe de vis est rompu (tip absent ou doublons), c'est
    une consigne de sécurité prioritaire — tout autre conseil est bloqué."""
    # Garde de sécurité — pointe absente : l'invariant physique est cassé,
    # rien d'autre ne doit être conseillé tant qu'il n'est pas restauré.
    if tip_status == "missing":
        return DecisionSummary(
            decision=_t("sr.summary.tip_missing.decision"),
            why=_t("sr.summary.tip_missing.why"),
            action=_t("sr.summary.tip_missing.action"),
        )
    if n_filled == 0:
        return DecisionSummary(
            decision=_t("sr.empty.summary_decision"),
            why=_t("sr.empty.summary_why"),
            action=_t("sr.empty.summary_action"),
        )
    if not comps:
        if overall_status == "ok":
            ds = DecisionSummary(
                decision=_t("sr.summary.ok.decision", n=suggested),
                why=_t("sr.summary.ok.why"),
                action=_t("sr.next.pilot"),
            )
        else:
            ds = DecisionSummary(
                decision=_t("sr.summary.watch.decision", n=suggested),
                why=_t("sr.summary.watch.why"),
                action=_t("sr.summary.watch.action"),
            )
    else:
        decision, why, action = _operator_summary_from_comp(comps[0])
        ds = DecisionSummary(decision=decision, why=why, action=action)

    if tip_status == "deduplicated" and tip_stray_count > 0:
        n_word = (_t("sr.summary.dedup_singular") if tip_stray_count == 1
                  else _t("sr.summary.dedup_plural"))
        return DecisionSummary(
            decision=ds.decision, why=ds.why,
            action=_t("sr.summary.dedup", action=ds.action,
                       count=tip_stray_count, word=n_word),
        )
    return ds


def analyze_systemic(
    cfg: list[int],
    rpm: float,
    feed: float,
    dens: float,
    *,
    base_type_fn,
    is_part2_fn,
    position_to_zone_fn,
    fill_factor_fn,
    n_positions: int,
    main_feeder_pos: int,
    tip_part1_pos: int,
    profile_reading=None,        # ProcessProfile (recompute si None)
    count_rec=None,              # CountRecommendation (recompute si None)
    recs: list[dict] | None = None,   # liste de recos (recompute si None)
    zone_residence_fn=None,
    tip_constraint_fn=None,      # callable cfg -> TipStatus (cf. screw_logic)
) -> SystemicAnalysis:
    """Couche de raisonnement global procédé : compensations + checks +
    trade-offs + synthèse finale + why_optimal enrichi + couche décisionnelle.

    Cette fonction est PURE (aucun import Streamlit). Elle accepte les sorties
    déjà calculées de analyze_profile / compute_recommendations /
    recommend_element_count en entrée, ou les recalcule si non fournies, pour
    rester utilisable seule (tests, batch, autre HMI).
    """
    if recs is None:
        recs = compute_recommendations(
            cfg, rpm, feed, dens,
            base_type_fn=base_type_fn,
            is_part2_fn=is_part2_fn,
            position_to_zone_fn=position_to_zone_fn,
            fill_factor_fn=fill_factor_fn,
            n_positions=n_positions,
            main_feeder_pos=main_feeder_pos,
            tip_part1_pos=tip_part1_pos,
        )

    metrics = _zone_metrics(
        cfg,
        base_type_fn=base_type_fn,
        is_part2_fn=is_part2_fn,
        position_to_zone_fn=position_to_zone_fn,
        main_feeder_pos=main_feeder_pos,
        tip_part1_pos=tip_part1_pos,
    )
    ff = fill_factor_fn(cfg, rpm, feed, dens)
    zrt = zone_residence_fn(cfg, rpm, feed, dens) if zone_residence_fn else None

    comps = _build_compensations(metrics, recs, ff, rpm, feed)
    checks = _build_global_checks(metrics, ff, zrt)
    tradeoffs = _build_tradeoffs(comps, recs, metrics)
    synthesis = _build_synthesis(metrics, ff, zrt)
    overall_status, overall_summary = _systemic_overall(checks, synthesis)

    # Enrichissement du why_optimal — basé sur count_rec si fourni.
    base_why = ""
    suggested = 30
    if count_rec is not None:
        base_why = (
            getattr(count_rec, "why_optimal", "")
            or getattr(count_rec, "rationale", "")
        )
        suggested = getattr(count_rec, "suggested", 30)
    why_optimal_enriched = _build_why_enriched(
        base_why, suggested, list(comps), overall_status
    )

    # Couche décisionnelle (action prioritaire + confiance + prochaine étape).
    main_decision, decision_confidence, next_step = _build_decision_layer(
        suggested=suggested,
        comps=list(comps),
        recs=list(recs),
        overall_status=overall_status,
        n_filled=metrics["n_filled"],
    )

    # Contrainte métier pointe de vis — vérifie l'invariant si une fonction
    # est fournie par l'appelant (typiquement screw_logic.enforce_tip_constraint).
    # Si non fourni, on suppose la pointe valide (rétro-compat tests existants).
    tip_status_str = "valid"
    tip_stray: tuple[int, ...] = ()
    if tip_constraint_fn is not None:
        ts = tip_constraint_fn(cfg)
        tip_status_str = getattr(ts, "status", "valid")
        tip_stray = tuple(getattr(ts, "stray_positions", ()))

    # Version opérateur 3-lignes (langage simplifié) — mêmes entrées que la
    # couche technique, juste reformulée. Pas de duplication métier.
    # La pointe de vis est intégrée comme préfixe quand l'invariant est
    # rompu : c'est une consigne de sécurité prioritaire à toute autre.
    decision_summary = _build_decision_summary(
        suggested=suggested,
        comps=list(comps),
        overall_status=overall_status,
        n_filled=metrics["n_filled"],
        tip_status=tip_status_str,
        tip_stray_count=len(tip_stray),
    )

    return SystemicAnalysis(
        compensations=tuple(comps),
        global_checks=tuple(checks),
        tradeoffs=tuple(tradeoffs),
        synthesis=tuple(synthesis),
        overall_status=overall_status,
        overall_summary=overall_summary,
        why_optimal_enriched=why_optimal_enriched,
        main_decision=main_decision,
        decision_confidence=decision_confidence,
        next_step=next_step,
        decision_summary=decision_summary,
        tip_status=tip_status_str,
        tip_stray_positions=tip_stray,
    )


# ---------------------------------------------------------------------------
# Rendu HTML — bloc systémique unique. Pas de Streamlit ici (UI-agnostic).
# Les pages appellent st.html(build_systemic_html(systemic)) — DOM atomique.
# ---------------------------------------------------------------------------
_SYSTEMIC_STATUS_COLORS: dict[str, tuple[str, str, str]] = {
    "ok":    ("#0f2b1d", "#bbf7d0", "#10B981"),
    "watch": ("#3b2c0a", "#fde68a", "#F59E0B"),
    "alert": ("#3b1212", "#fecaca", "#EF4444"),
}

def _systemic_style(status: str) -> tuple[str, str, str, str]:
    bg, fg, acc = _SYSTEMIC_STATUS_COLORS.get(status, _SYSTEMIC_STATUS_COLORS["watch"])
    badge_key = {"ok": "sr.sys.badge_ok", "watch": "sr.sys.badge_watch", "alert": "sr.sys.badge_alert"}
    badge = _t(badge_key.get(status, "sr.sys.badge_watch"))
    return bg, fg, acc, badge

_SYSTEMIC_STATUS_STYLE = _SYSTEMIC_STATUS_COLORS  # keep for color lookups

# Style et clé i18n du libellé du bloc DÉCISION AGENT selon `decision_confidence`.
_DECISION_STYLE: dict[str, tuple[str, str]] = {
    "high":   ("#10B981", "sr.decision.high"),
    "medium": ("#F59E0B", "sr.decision.medium"),
    "low":    ("#EF4444", "sr.decision.low"),
}


def build_decision_html(sa: SystemicAnalysis) -> str:
    """Bloc décision opérateur : action prioritaire + badge confiance +
    prochaine étape. Toujours rendu (DOM stable) ; renvoie un slot vide si
    `main_decision` est absent (cas dégénéré)."""
    if not sa.main_decision:
        # Slot maintenu pour stabilité DOM Streamlit (hauteur 0).
        return '<div style="height:0;overflow:hidden;margin:0;"></div>'
    color, badge_key = _DECISION_STYLE.get(
        sa.decision_confidence, _DECISION_STYLE["medium"]
    )
    return (
        f'<div style="background:#0B0F14;border:1px solid {color};'
        f'border-radius:0.35rem;padding:0.85rem 1.1rem;margin:0.5rem 0;">'
        f'<div style="display:flex;gap:0.55rem;align-items:center;'
        f'flex-wrap:wrap;margin-bottom:0.4rem;">'
        f'<span style="background:{color};color:#0B0F14;font-weight:700;'
        f'font-size:0.7rem;padding:0.15rem 0.55rem;border-radius:0.25rem;'
        f'letter-spacing:0.06em;">{_t("sr.lbl.decision_agent")} · {_t(badge_key)}</span>'
        f'<span style="color:#9CA3AF;font-size:0.72rem;font-weight:500;">'
        f'{_t("sr.lbl.confidence")} {sa.decision_confidence.upper()}</span>'
        f'</div>'
        f'<div style="color:#F9FAFB;font-weight:600;font-size:1.05rem;'
        f'line-height:1.4;">{sa.main_decision}</div>'
        f'<div style="color:#D1D5DB;font-size:0.84rem;line-height:1.45;'
        f'margin-top:0.45rem;">'
        f'<span style="color:{color};font-weight:600;font-size:0.66rem;'
        f'letter-spacing:0.04em;text-transform:uppercase;'
        f'margin-right:0.3rem;">{_t("sr.lbl.next_step")}</span>{sa.next_step}</div>'
        f'</div>'
    )


def build_decision_summary_html(sa: SystemicAnalysis) -> str:
    """Bloc opérateur 3-lignes (Décision / Pourquoi / Action) — lecture en 3 s.

    Toujours rendu (DOM stable). Si `decision_summary` est absent, renvoie un
    slot vide pour éviter les sauts de mise en page Streamlit.
    """
    ds = sa.decision_summary
    if ds is None:
        return '<div style="height:0;overflow:hidden;margin:0;"></div>'
    color, _ = _DECISION_STYLE.get(
        sa.decision_confidence, _DECISION_STYLE["medium"]
    )

    def _row(label: str, body: str, accent: str) -> str:
        return (
            f'<div style="display:flex;gap:0.55rem;align-items:baseline;'
            f'padding:0.32rem 0;border-bottom:1px solid #1F2937;">'
            f'<span style="flex:0 0 5.2rem;color:{accent};font-weight:700;'
            f'font-size:0.68rem;letter-spacing:0.06em;text-transform:uppercase;">'
            f'{label}</span>'
            f'<span style="flex:1;color:#F9FAFB;font-size:0.92rem;'
            f'line-height:1.45;">{body}</span></div>'
        )

    rows = (
        _row(_t("sr.lbl.row_decision"), ds.decision, color)
        + _row(_t("sr.lbl.row_why"), ds.why, "#9CA3AF")
        + _row(_t("sr.lbl.row_action"), ds.action, color)
    )
    return (
        f'<div style="background:#0B0F14;border-left:3px solid {color};'
        f'border-radius:0 0.3rem 0.3rem 0;padding:0.55rem 0.95rem;'
        f'margin:0.4rem 0;">'
        f'<div style="color:{color};font-size:0.66rem;font-weight:700;'
        f'letter-spacing:0.06em;margin-bottom:0.1rem;">'
        f'{_t("sr.lbl.operator_read")}</div>'
        f'{rows}</div>'
    )


def build_systemic_html(sa: SystemicAnalysis) -> str:
    """Rendu compact du bloc systémique (cohérent avec _build_recs_html style)."""
    bg, fg, acc, badge = _systemic_style(sa.overall_status)

    # En-tête : statut global + résumé une phrase
    header = (
        f'<div style="background:{bg};border-left:4px solid {acc};'
        f'border-radius:0.25rem;padding:0.7rem 0.95rem;margin-bottom:0.55rem;">'
        f'<div style="display:flex;align-items:center;gap:0.55rem;flex-wrap:wrap;">'
        f'<span style="background:{acc};color:#0B0F14;font-weight:700;'
        f'font-size:0.68rem;padding:0.12rem 0.5rem;border-radius:0.2rem;'
        f'letter-spacing:0.06em;">{_t("sr.sys.header_prefix")} · {badge}</span>'
        f'<span style="color:{fg};font-weight:600;font-size:0.92rem;">'
        f'{_t("sr.lbl.global_reasoning")}</span>'
        f'</div>'
        f'<div style="color:{fg};opacity:0.9;font-size:0.85rem;line-height:1.5;'
        f'margin-top:0.35rem;">{sa.overall_summary}</div>'
        f'</div>'
    )

    # Compensations : tableau compact (trigger → cible → action).
    if sa.compensations:
        rows = "".join(
            f'<div style="display:flex;gap:0.55rem;padding:0.32rem 0;'
            f'border-bottom:1px solid #1F2937;font-size:0.83rem;">'
            f'<div style="flex:0 0 38%;color:#D1D5DB;">'
            f'<div style="color:#9CA3AF;font-size:0.68rem;font-weight:600;'
            f'letter-spacing:0.04em;">{_t("sr.sys.trigger_label")}</div>{c.trigger}</div>'
            f'<div style="flex:0 0 12%;">'
            f'<span style="background:rgba(59,130,246,0.12);color:#bfdbfe;'
            f'border:1px solid #3B82F6;font-weight:700;font-size:0.7rem;'
            f'padding:0.1rem 0.45rem;border-radius:0.2rem;">{c.target_zone}</span>'
            f'</div>'
            f'<div style="flex:1;color:#F9FAFB;line-height:1.45;">'
            f'<div style="color:#9CA3AF;font-size:0.68rem;font-weight:600;'
            f'letter-spacing:0.04em;">{_t("sr.sys.comp_label")}</div>{c.action}'
            f'<div style="color:#9CA3AF;font-style:italic;font-size:0.74rem;'
            f'margin-top:0.2rem;">{c.rationale}</div></div>'
            f'</div>'
            for c in sa.compensations
        )
        comp_block = (
            f'<div style="background:#0B0F14;border:1px solid #1F2937;'
            f'border-radius:0.3rem;padding:0.55rem 0.85rem;margin-bottom:0.5rem;">'
            f'<div style="color:#D1D5DB;font-weight:600;font-size:0.78rem;'
            f'margin-bottom:0.15rem;">⇄ {_t("sr.sys.comp_title")}'
            f'<span style="color:#6B7280;font-weight:400;font-size:0.72rem;'
            f'margin-left:0.4rem;">— {_t("sr.sys.comp_sub")}</span></div>'
            f'{rows}</div>'
        )
    else:
        comp_block = (
            '<div style="background:#0B0F14;border:1px solid #1F2937;'
            'border-radius:0.3rem;padding:0.5rem 0.85rem;margin-bottom:0.5rem;'
            'color:#9CA3AF;font-size:0.82rem;font-style:italic;">'
            f'{_t("sr.sys.no_comp")}'
            "</div>"
        )

    # Vérifications globales : grille de cartes (1 par check).
    check_cards = "".join(
        (
            lambda cbg, cfg2, cacc, clab: (
                f'<div style="flex:1 1 200px;background:{cbg};'
                f'border-left:3px solid {cacc};border-radius:0.25rem;'
                f'padding:0.45rem 0.7rem;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:baseline;">'
                f'<span style="color:{cfg2};font-weight:600;font-size:0.78rem;">'
                f'{ck.label}</span>'
                f'<span style="color:{cacc};font-size:0.65rem;font-weight:700;'
                f'letter-spacing:0.04em;">{clab}</span></div>'
                f'<div style="color:{cfg2};opacity:0.9;font-size:0.78rem;'
                f'line-height:1.4;margin-top:0.2rem;">{ck.summary}</div>'
                f'</div>'
            )
        )(*_systemic_style(ck.status))
        for ck in sa.global_checks
    )
    checks_block = (
        f'<div style="margin-bottom:0.5rem;">'
        f'<div style="color:#D1D5DB;font-weight:600;font-size:0.78rem;'
        f'margin-bottom:0.3rem;">✓ {_t("sr.sys.checks_title")}'
        f'</div>'
        f'<div style="display:flex;gap:0.4rem;flex-wrap:wrap;">{check_cards}</div>'
        f'</div>'
    )

    # Trade-offs : liste à puces avec accent ambre.
    if sa.tradeoffs:
        trade_rows = "".join(
            f'<div style="display:flex;gap:0.5rem;padding:0.18rem 0;'
            f'font-size:0.83rem;color:#F9FAFB;line-height:1.5;">'
            f'<span style="color:#F59E0B;">⇌</span>'
            f'<span style="flex:1;">{t}</span></div>'
            for t in sa.tradeoffs
        )
        trade_block = (
            f'<div style="background:rgba(245,158,11,0.04);'
            f'border-left:2px solid #F59E0B;border-radius:0 0.2rem 0.2rem 0;'
            f'padding:0.5rem 0.85rem;margin-bottom:0.5rem;">'
            f'<div style="color:#F59E0B;font-size:0.72rem;font-weight:700;'
            f'letter-spacing:0.04em;margin-bottom:0.2rem;">'
            f'{_t("sr.lbl.tradeoffs")}</div>'
            f'{trade_rows}</div>'
        )
    else:
        trade_block = ""

    # Synthèse finale : 4 axes en bandeau (cards larges).
    syn_cards = "".join(
        (
            lambda sbg, sfg, sacc, slab: (
                f'<div style="flex:1 1 0;min-width:140px;background:{sbg};'
                f'border:1px solid {sacc};border-radius:0.25rem;'
                f'padding:0.5rem 0.7rem;text-align:center;">'
                f'<div style="color:{sacc};font-size:0.7rem;font-weight:700;'
                f'letter-spacing:0.06em;">{ax.label.upper()}</div>'
                f'<div style="color:{sfg};font-weight:600;font-size:0.85rem;'
                f'margin-top:0.2rem;">{slab}</div>'
                f'<div style="color:{sfg};opacity:0.85;font-size:0.74rem;'
                f'line-height:1.35;margin-top:0.2rem;">{ax.detail}</div>'
                f'</div>'
            )
        )(*_systemic_style(ax.status))
        for ax in sa.synthesis
    )
    syn_block = (
        f'<div style="background:#0B0F14;border:1px solid {acc};'
        f'border-radius:0.3rem;padding:0.6rem 0.85rem;">'
        f'<div style="color:{acc};font-weight:700;font-size:0.72rem;'
        f'letter-spacing:0.05em;margin-bottom:0.4rem;">{_t("sr.lbl.synthesis")}'
        f'{_t("sr.sys.synthesis_prefix")}</div>'
        f'<div style="display:flex;gap:0.4rem;flex-wrap:wrap;">{syn_cards}</div>'
        f'</div>'
    )

    return header + comp_block + checks_block + trade_block + syn_block
