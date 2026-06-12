"""
screw_logic.py — Logique métier Rondol (extrusion bivis).

Source de vérité : references/logique_metier/2-CALCULS.pdf (Network 7).

ÉTAPE 1 — VOLUME UNIQUEMENT
Les fonctions fill_factor / résidence / recommandations IA sont volontairement
réduites à des stubs (Étape 4).

Représentation interne :
  config[0..80] : liste de 81 entiers.
    0                       = case vide
    1..13 (sauf 2)          = 1ère partie d'un élément entier (occupe pos et pos+1)
    2                       = demi-élément de convoyage (1 seule position)
    101..113                = 2ème partie d'un élément entier (type + 100)
  Position 0     : marqueur début, non modifiable (exclue de la sommation volume).
  Positions 79-80: tip+discharge (type 13) forcé, immuable.

Compteur utilisateur (ADD) :
  élément entier = 1.0 ; demi-convoyage = 0.5 ; tip non compté.
  Capacité max utilisateur = 39.0 (78 positions libres ÷ 2).

Capacité TOTALE affichée (exigence manager 2026-06-12) :
  la vis complète inclut le tip+décharge (type 13, toujours monté) →
  TOTAL_ELEMENT_CAPACITY = 40.0 (39 utilisateur + 1 tip). Les compteurs
  visibles utilisent `count_total_elements` (tip inclus) ; la validation de
  placement reste sur MAX_USER_ELEMENTS (limite géométrique inchangée).

Règle volume (PDF Network 7 lignes 22-38) :
  Local_Free[i] = BASE - Volume_cm3[2]        si config[i] == 2
                = BASE - Volume_cm3[type]/2   si 1 ≤ config[i] ≤ 13, ≠ 2
                = Local_Free[i-1]             si config[i] ≥ 101 (recopie)
                = BASE                        si config[i] == 0
  Volume_occupé = TOTAL_FREE − Σ Local_Free[i=1..80]
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constantes PDF
# ---------------------------------------------------------------------------
N_POSITIONS: int = 81
BASE_FREE_VOL_PER_POS: float = 0.952195
TOTAL_FREE_VOL: float = 76.1756
MAIN_FEEDER_POSITION: int = 4
MAX_USER_ELEMENTS: float = 39.0
# Capacité TOTALE de la vis assemblée, tip+décharge inclus (toujours monté).
# 39 éléments utilisateur + 1 tip = 40 — alignée sur le défaut Rondol
# target_screw_count=40 (validé manager). Affichage uniquement : la limite de
# placement utilisateur reste MAX_USER_ELEMENTS (géométrie 78 positions ÷ 2).
TIP_ELEMENT_COUNT: float = 1.0
TOTAL_ELEMENT_CAPACITY: float = MAX_USER_ELEMENTS + TIP_ELEMENT_COUNT  # 40.0

# Correction métier (validée manager) : l'extrudeuse est une BIVIS.
# Le volume occupé par les éléments doit être compté pour les DEUX vis :
#   volume_occupé_total = N_SCREWS × volume_occupé_par_vis
#   volume_libre        = TOTAL_FREE_VOL − volume_occupé_total
# Exemple validé : 76.1756 − 2 × 24.424 = 27.3276 cm³.
# Les VOLUME_CM3[] du PDF Network 7 sont PAR VIS → on applique le facteur ici,
# au point unique de calcul (local_free_volumes + compute_process_state), ce qui
# propage automatiquement à fill factor, résidence, capacités feeders, overflow.
N_SCREWS: int = 2

TIP_TYPE: int = 13
TIP_PART1_POS: int = 79
TIP_PART2_POS: int = 80
PART2_OFFSET: int = 100
N_ELEMENT_TYPES: int = 14

VOLUME_CM3: list[float] = [
    0.00000, 0.61060, 0.30328, 0.61070, 0.61058, 0.61058, 0.64073,
    0.60158, 0.60158, 0.61198, 0.62133, 0.58770, 0.58770, 0.61060,
]

FACTOR_FREE_BY_REV: list[float] = [
    0.0, 1.0, 1.0, 0.5, 0.9, 0.4, 1.1, 0.7, 0.55, 1.0, 0.3, 0.5, 0.5, 1.0,
]

START_ELMT_ZONE: list[int] = [0, 9, 18, 27, 36, 45, 54, 63, 72, 81]

# ---------------------------------------------------------------------------
# Étape 3 — Side Feeder (positions structurées)
# ---------------------------------------------------------------------------
# 8 positions candidates indexées via SideFeeder_Zone ∈ {1..8}.
# SideFeeder_Zone = 0 → désactivé (sentinelle = 81, ignorée en aval).
SIDE_FEEDER_START_ELMT_Z: list[int] = [4, 12, 21, 30, 39, 48, 57, 66]
SIDE_FEEDER_DISABLED_POSITION: int = 81
SIDE_FEEDER_DISABLED_ZONE: int = 0
SIDE_FEEDER_MAX_ZONE: int = 8


@dataclass(frozen=True)
class ElementType:
    id: int
    label: str
    full_name: str
    half: bool


ELEMENT_TYPES: list[ElementType] = [
    ElementType(0,  "Vide",             "Position libre",           False),
    ElementType(1,  "Convoyage +",      "Forward conveying",        False),
    ElementType(2,  "Convoyage ½",      "Forward conveying half",   True),
    ElementType(3,  "Pas court",        "Short-pitch element",      False),
    ElementType(4,  "Malaxage 90°",     "Kneading element 90°",     False),
    ElementType(5,  "Malaxage 30°",     "Kneading element 30°",     False),
    ElementType(6,  "Grand pas",        "Large pitch element",      False),
    ElementType(7,  "Malaxage 60°",     "Kneading element 60°",     False),
    ElementType(8,  "Malaxage 45°",     "Kneading element 45°",     False),
    ElementType(9,  "Convoyage -",      "Reverse conveying",        False),
    ElementType(10, "Chaotique",        "Chaotic element",          False),
    ElementType(11, "Dentelé",          "Toothed element",          False),
    ElementType(12, "Mélange spécial",  "Special mixing element",   False),
    ElementType(13, "Pointe + décharge","Screw tip + discharge",    False),
]


# ---------------------------------------------------------------------------
# Encodage +100 (1ère / 2ème partie)
# ---------------------------------------------------------------------------
def is_part2(value: int) -> bool:
    return value >= PART2_OFFSET


def base_type(value: int) -> int:
    return value - PART2_OFFSET if value >= PART2_OFFSET else value


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def new_empty_configuration() -> list[int]:
    """Config vide avec tip+discharge forcé aux positions 79-80."""
    cfg = [0] * N_POSITIONS
    cfg[TIP_PART1_POS] = TIP_TYPE
    cfg[TIP_PART2_POS] = TIP_TYPE + PART2_OFFSET
    return cfg


def reset_configuration() -> list[int]:
    return new_empty_configuration()


# ---------------------------------------------------------------------------
# Règle volume (PDF Network 7)
# ---------------------------------------------------------------------------
def local_free_volumes(config: list[int]) -> list[float]:
    """Retourne Local_Free_Volume_cm3[0..80] conforme PDF."""
    lf = [0.0] * N_POSITIONS
    for i in range(N_POSITIONS):
        v = config[i]
        if v == 0:
            lf[i] = BASE_FREE_VOL_PER_POS
        elif v == 2:
            lf[i] = BASE_FREE_VOL_PER_POS - N_SCREWS * VOLUME_CM3[2]
        elif is_part2(v):
            lf[i] = lf[i - 1] if i > 0 else BASE_FREE_VOL_PER_POS
        else:
            lf[i] = BASE_FREE_VOL_PER_POS - N_SCREWS * VOLUME_CM3[v] / 2.0
    return lf


def total_volume_used(config: list[int]) -> float:
    """Volume occupé TOTAL (cm³) pour les 2 vis = TOTAL_FREE − Σ Local_Free[1..80].

    Bivis : la règle volume retire N_SCREWS × le volume par vis (cf. N_SCREWS).
    """
    lf = local_free_volumes(config)
    return TOTAL_FREE_VOL - sum(lf[1:N_POSITIONS])


def occupied_volume_per_screw(config: list[int]) -> float:
    """Volume occupé par UNE vis (cm³)."""
    return total_volume_used(config) / N_SCREWS


def occupied_volume_total(config: list[int]) -> float:
    """Volume occupé par les DEUX vis (cm³) = N_SCREWS × par vis."""
    return total_volume_used(config)


def free_volume(config: list[int]) -> float:
    """Volume libre utile (cm³) = TOTAL_FREE − volume occupé total (2 vis)."""
    return TOTAL_FREE_VOL - total_volume_used(config)


def free_volume_for_occupied_per_screw(occupied_per_screw: float) -> float:
    """Formule métier validée : libre = TOTAL_FREE − N_SCREWS × occupé_par_vis.

    Exemple : free_volume_for_occupied_per_screw(24.42) ≈ 27.3356 cm³.
    """
    return TOTAL_FREE_VOL - N_SCREWS * occupied_per_screw


# ---------------------------------------------------------------------------
# Garde « pas d'élément inventé » (règle manager) — l'IA ne doit jamais
# recommander, substituer, réduire ou commenter un type d'élément ABSENT de la
# configuration courante. Source unique, pure, partagée par screw_render et
# AgentIndustrial_v1/core/recommendations.
# ---------------------------------------------------------------------------
def present_element_types(config: list[int]) -> set[int]:
    """Types d'éléments réellement présents (base types 1..12 ; tip/vide exclus)."""
    out: set[int] = set()
    for v in config:
        if v == 0 or v >= PART2_OFFSET:
            continue
        bt = base_type(v)
        if bt in (0, TIP_TYPE):
            continue
        out.add(bt)
    return out


# Tokens textuels (FR/EN, minuscule) → familles de types d'éléments concernées.
# Si un token apparaît dans le texte d'une reco mais qu'AUCUN de ses types n'est
# présent dans la config, la reco cite un élément absent → interdite.
#
# Manager 2026-06-09 : les tokens d'ANGLE SPÉCIFIQUE (kneading 30/45/60/90) sont
# évalués en plus des tokens collectifs (kneading/malaxage). Cela bloque le cas
# vu en prod : profil avec uniquement Kneading 60° (type 7), reco qui cite
# « Kneading 90° » (type 4 absent). Avant ce correctif, le filtre laissait
# passer parce que le token collectif « kneading » matchait via le type 7
# présent ; désormais le token spécifique « kneading 90 » détecte l'absence
# du type 4 et la reco est supprimée.
_KNEADING_TYPES: frozenset[int] = frozenset({4, 5, 7, 8})
_CONVEYING_TYPES: frozenset[int] = frozenset({1, 2, 9})
ELEMENT_MENTION_TOKENS: tuple[tuple[str, frozenset[int]], ...] = (
    # Tokens collectifs (mélange en général).
    ("kneading", _KNEADING_TYPES),
    ("malaxage", _KNEADING_TYPES),
    ("malaxeur", _KNEADING_TYPES),
    ("convoyage", _CONVEYING_TYPES),
    ("conveying", _CONVEYING_TYPES),
    ("short-pitch", frozenset({3})),
    ("pas court", frozenset({3})),
    ("large pitch", frozenset({6})),
    ("grand pas", frozenset({6})),
    ("chaotic", frozenset({10})),
    ("chaotique", frozenset({10})),
    ("toothed", frozenset({11})),
    ("dentelé", frozenset({11})),
    ("special mixing", frozenset({12})),
    ("mélange spécial", frozenset({12})),
    ("reverse", frozenset({9})),
    # Tokens d'angle SPÉCIFIQUE (manager 2026-06-09) — types Kneading individuels :
    #   4 = Kneading 90° (dispersif)
    #   5 = Kneading 30° (distributif)
    #   7 = Kneading 60° (intermédiaire)
    #   8 = Kneading 45° (distributif)
    ("kneading 90", frozenset({4})),
    ("malaxage 90", frozenset({4})),
    ("kneading 30", frozenset({5})),
    ("malaxage 30", frozenset({5})),
    ("kneading 60", frozenset({7})),
    ("malaxage 60", frozenset({7})),
    ("kneading 45", frozenset({8})),
    ("malaxage 45", frozenset({8})),
)


def recommendation_cites_absent_element(text: str, config: list[int]) -> bool:
    """True si `text` mentionne un type d'élément ABSENT de `config`.

    Pur, insensible à la casse. Utilisé pour filtrer toute recommandation qui
    inventerait un élément non présent dans le run courant.
    """
    if not text:
        return False
    present = present_element_types(config)
    low = text.lower()
    for token, types in ELEMENT_MENTION_TOKENS:
        if token in low and present.isdisjoint(types):
            return True
    return False


# ---------------------------------------------------------------------------
# Compteur utilisateur (ADD)
# ---------------------------------------------------------------------------
def count_user_elements(config: list[int]) -> float:
    """ADD : entier=1.0, demi=0.5, tip exclu, 2ème partie non comptée."""
    total = 0.0
    for i in range(N_POSITIONS):
        if i == TIP_PART1_POS or i == TIP_PART2_POS:
            continue
        v = config[i]
        if v == 0 or is_part2(v):
            continue
        total += 0.5 if v == 2 else 1.0
    return total


def count_elements(config: list[int]) -> float:
    """Alias HMI (demi=0.5, tip exclu)."""
    return count_user_elements(config)


def count_total_elements(config: list[int]) -> float:
    """Compteur VISIBLE : éléments utilisateur + tip+décharge s'il est monté.

    Capacité totale affichée = TOTAL_ELEMENT_CAPACITY (40 = 39 + tip). Le tip
    n'est compté que s'il est réellement présent dans la configuration (une
    config vide [] ou tronquée compte 0 — l'état vide reste explicite).
    """
    if not config:
        return 0.0
    tip = (
        TIP_ELEMENT_COUNT
        if len(config) > TIP_PART1_POS and config[TIP_PART1_POS] == TIP_TYPE
        else 0.0
    )
    return count_user_elements(config) + tip


def remaining_slots(config: list[int]) -> float:
    return MAX_USER_ELEMENTS - count_user_elements(config)


# ---------------------------------------------------------------------------
# Placement / retrait
# ---------------------------------------------------------------------------
def can_place(config: list[int], pos: int, type_id: int) -> bool:
    if not (1 <= type_id <= 13):
        return False
    if pos <= 0 or pos >= TIP_PART1_POS:
        return False
    if config[pos] != 0:
        return False
    if type_id != 2:
        if pos + 1 >= TIP_PART1_POS or config[pos + 1] != 0:
            return False
    extra = 0.5 if type_id == 2 else 1.0
    if count_user_elements(config) + extra > MAX_USER_ELEMENTS + 1e-9:
        return False
    return True


def place_element_at(config: list[int], pos: int, type_id: int) -> bool:
    if not can_place(config, pos, type_id):
        return False
    config[pos] = type_id
    if type_id != 2:
        config[pos + 1] = type_id + PART2_OFFSET
    return True


def first_free_position(config: list[int], type_id: int) -> int:
    for i in range(1, TIP_PART1_POS):
        if can_place(config, i, type_id):
            return i
    return -1


def add_element(config: list[int], type_id: int, count: int = 1) -> int:
    """Ajoute jusqu'à `count` éléments de type donné. Retourne le nombre posé."""
    placed = 0
    for _ in range(count):
        pos = first_free_position(config, type_id)
        if pos < 0:
            break
        if not place_element_at(config, pos, type_id):
            break
        placed += 1
    return placed


def add_elements_atomic(config: list[int], type_id: int, count: int) -> bool:
    """Ajout atomique : pose les `count` éléments OU ne modifie rien.

    Utilisé pour le bouton +4 du HMI — comportement tout-ou-rien."""
    if count <= 0:
        return True
    snapshot = list(config)
    for _ in range(count):
        pos = first_free_position(config, type_id)
        if pos < 0 or not place_element_at(config, pos, type_id):
            for i in range(N_POSITIONS):
                config[i] = snapshot[i]
            return False
    return True


def remove_at(config: list[int], pos: int) -> bool:
    """Retire l'élément à la position donnée (2 cases si entier). Tip protégé."""
    if pos <= 0 or pos == TIP_PART1_POS or pos == TIP_PART2_POS:
        return False
    v = config[pos]
    if v == 0:
        return False
    if v == 2:
        config[pos] = 0
    elif is_part2(v):
        if pos - 1 >= 0:
            config[pos - 1] = 0
        config[pos] = 0
    else:
        config[pos] = 0
        if pos + 1 < N_POSITIONS and config[pos + 1] == v + PART2_OFFSET:
            config[pos + 1] = 0
    return True


# ---------------------------------------------------------------------------
# Contrainte métier : pointe de vis (tip+discharge, type 13)
# ---------------------------------------------------------------------------
# Règles industrielles non contournables :
#   - 1 seule pointe par profil (l'élément physique est unique)
#   - toujours en fin de vis (positions TIP_PART1_POS / TIP_PART2_POS)
#   - orientation gauche → droite (sortie matière = côté droit)
#   - non déplaçable (case-position structurelle, pas un slot libre)
#   - non duplicable (toute occurrence en amont est un artéfact à nettoyer)
#
# `can_place` / `remove_at` empêchent déjà les opérations interactives qui
# violeraient ces règles (cf. screw_logic L182-260). `enforce_tip_constraint`
# est la garde *défensive* qui :
#   - vérifie l'invariant à chaque cycle d'analyse (pas de tip orphelin) ;
#   - dédoublonne silencieusement si une importation/désérialisation a
#     introduit un type 13 ailleurs qu'aux positions structurelles ;
#   - expose un état machine-readable (`tip_status`) pour la couche décision.
#
# La fonction est PURE : elle renvoie un statut + une copie nettoyée du cfg.
# ---------------------------------------------------------------------------
TIP_STATUS_VALID: str = "valid"
TIP_STATUS_MISSING: str = "missing"
TIP_STATUS_DEDUPLICATED: str = "deduplicated"


@dataclass(frozen=True)
class TipStatus:
    """État de la pointe de vis après vérification de l'invariant.

    Attributs:
      status   : "valid" (pointe en place et unique)
                 | "missing" (pointe absente — config corrompue/incomplète)
                 | "deduplicated" (doublons en amont nettoyés)
      stray_positions : positions amont où des occurrences parasites ont été
                        détectées (vide si aucune).
      cleaned : copie du cfg avec invariant restauré (tip aux positions
                structurelles, doublons amont effacés).
    """
    status: str
    stray_positions: tuple[int, ...]
    cleaned: list[int]


def enforce_tip_constraint(elements: list[int]) -> TipStatus:
    """Vérifie et restaure l'invariant pointe de vis sur une configuration.

    `elements` : liste d'entiers de longueur N_POSITIONS (l'API publique parle
    d'« elements » pour rester cohérente avec la sémantique métier — chaque
    case représente la trace d'un élément physique sur la vis).

    Comportement :
      - parcourt toutes les positions amont et efface tout type 13 (et toute
        2ème partie 113 = TIP_TYPE + PART2_OFFSET) trouvé hors des positions
        structurelles → renvoie status="deduplicated" et la liste des
        positions nettoyées dans `stray_positions`.
      - si après nettoyage les positions structurelles ne portent pas la
        pointe attendue → status="missing" (cleaned restaure quand même
        la pointe pour préserver l'invariant côté HMI).
      - sinon → status="valid".

    La règle d'orientation (gauche → droite) est implicite à la représentation
    interne : l'index croît vers la sortie, donc la pointe en TIP_PART1_POS /
    TIP_PART2_POS est par construction « tournée » vers la sortie matière.
    """
    cleaned = list(elements)
    stray: list[int] = []
    tip_part2 = TIP_TYPE + PART2_OFFSET

    # 1) Dédoublonnage — toute occurrence du tip ailleurs qu'aux positions
    #    structurelles est nettoyée. On scanne l'intégralité (y compris pos 0
    #    qui est marqueur de début, jamais une pointe valide).
    for i in range(len(cleaned)):
        if i == TIP_PART1_POS or i == TIP_PART2_POS:
            continue
        if cleaned[i] == TIP_TYPE or cleaned[i] == tip_part2:
            stray.append(i)
            cleaned[i] = 0

    # 2) Vérification invariant aux positions structurelles.
    has_tip = (
        len(cleaned) > TIP_PART2_POS
        and cleaned[TIP_PART1_POS] == TIP_TYPE
        and cleaned[TIP_PART2_POS] == tip_part2
    )
    if not has_tip:
        # Restauration défensive — on n'expose jamais à l'aval une config
        # sans pointe (fill_factor / résidence supposent l'invariant).
        if len(cleaned) > TIP_PART2_POS:
            cleaned[TIP_PART1_POS] = TIP_TYPE
            cleaned[TIP_PART2_POS] = tip_part2
        return TipStatus(
            status=TIP_STATUS_MISSING,
            stray_positions=tuple(stray),
            cleaned=cleaned,
        )

    if stray:
        return TipStatus(
            status=TIP_STATUS_DEDUPLICATED,
            stray_positions=tuple(stray),
            cleaned=cleaned,
        )
    return TipStatus(
        status=TIP_STATUS_VALID, stray_positions=(), cleaned=cleaned,
    )


# ---------------------------------------------------------------------------
# Utilitaire zone
# ---------------------------------------------------------------------------
def position_to_zone(pos: int) -> int:
    """Retourne la zone (0=Feed, 1..8) pour une position 0..80."""
    for z in range(len(START_ELMT_ZONE) - 1, -1, -1):
        if pos >= START_ELMT_ZONE[z]:
            return max(0, z)
    return 0


# ---------------------------------------------------------------------------
# Étape 3 — Side Feeder : position structurée (pas d'effet sur volume/ADD)
# ---------------------------------------------------------------------------
def side_feeder_position(config: list[int], zone: int) -> int:
    """Retourne la position structurée du side feeder.

    - zone = 0                          → SIDE_FEEDER_DISABLED_POSITION (81, sentinelle)
    - zone ∈ {1..8}                     → SIDE_FEEDER_START_ELMT_Z[zone-1]
      Si la position candidate tombe sur une 2ème partie d'élément entier
      (config[pos] ≥ 100), recule de 1 pour se placer sur la 1ère partie.
    - zone hors plage                   → ValueError

    Pur : ne modifie ni `config`, ni le volume, ni l'ADD.
    """
    if zone == SIDE_FEEDER_DISABLED_ZONE:
        return SIDE_FEEDER_DISABLED_POSITION
    if not (1 <= zone <= SIDE_FEEDER_MAX_ZONE):
        raise ValueError(f"SideFeeder_Zone invalide : {zone} (attendu 0..8)")
    pos = SIDE_FEEDER_START_ELMT_Z[zone - 1]
    if 0 <= pos < N_POSITIONS and is_part2(config[pos]):
        pos -= 1
    return pos


# ---------------------------------------------------------------------------
# Étape 4A — Fill Factor + Residence Time (PDF Network 7, REPRODUCTION BRUTE)
# ---------------------------------------------------------------------------
# Reproduction STRICTEMENT FIDÈLE du pseudo-code SCL "Network 7" (2-CALCULS.pdf
# lignes 0001-0170). Aucune correction, aucune simplification, aucune
# interprétation. Les bugs identifiés du PDF sont reproduits tels quels :
#
#   [PDF L0099-0105] FOR z:=0 TO 8 DO IF i >= Start_ElmtZone[z] THEN Zone:=z;
#                    EXIT — Zone vaut toujours 0 (Start_ElmtZone[0]=0).
#   [PDF L0108-0113] Pas de branche ELSE pour ThermalFactor → conserve sa
#                    valeur de l'itération précédente (Temp Real, défaut 0.0).
#   [PDF L0120]      ConvFactor calculé mais jamais utilisé.
#   [PDF L0142-0150] Si VolFlow[i] = 0 : reset FillFactor_Average := 0 et
#                    ResidenceTime_Total := 0 (destruction des cumuls).
#   [PDF L0079]      Side feeder : pas de garde N_rps > 0 (BulkDensity seul).
#   [PDF L0054]      MIN(20.0, Temp_Z[1]) — littéral 20.0, pas Tref.
#   [PDF L0106]      Temp_Z[Zone] - 20.0 — littéral 20.0, pas Tref.
#
# Les corrections documentées seront appliquées en Étape 4B.

THERMAL_FACTOR_MIN: float = 0.85
THERMAL_FACTOR_MAX: float = 1.25
TREF: float = 20.0           # PDF Constant : Tref Real 20.0
N_ZONES_TEMP: int = 9        # Temp_Z indexé 0..8 (Feed + Z1..Z8)


@dataclass(frozen=True)
class ProcessParams:
    """Paramètres procédé pour le Network 7 (correspondance HMI/SCL).

    Valeurs par défaut : pas de thermique, pas de side feeder, feeders inactifs.
    """
    screw_rpm: float = 120.0
    # Main feeder (HMI : VITESSE FEEDER1, BulkDensityFeeder1, ThermalExp_Feeder1)
    feeder1_flow_rate_g_per_s: float = 0.0
    feeder1_bulk_density: float = 0.0
    feeder1_thermal_exp: float = 0.0
    # Side feeder
    feeder2_flow_rate_g_per_s: float = 0.0
    feeder2_bulk_density: float = 0.0
    feeder2_thermal_exp: float = 0.0
    side_feeder_zone: int = 0
    # Profil thermique zones 0..8 (HMI : Temp_Z[0..8])
    temp_z: tuple[float, ...] = (TREF,) * N_ZONES_TEMP
    tref: float = TREF


@dataclass(frozen=True)
class ProcessState:
    """Résultat complet du Network 7 : agrégats + profils position par position."""
    side_feeder_position: int
    local_free_volume_cm3: list[float]       # [0..80] cm³
    local_free_volume_by_rev: list[float]    # [0..80] cm³/tour
    fill_factor_local: list[float]           # [0..80] sans unité, ∈ [0, 1]
    vol_flow_cm3_s: list[float]              # [0..80] cm³/s
    residence_time_local: list[float]        # [0..80] s
    fill_factor_average: float               # moyenne sur (81 − MainFeeder_Position)
    residence_time_total: float              # s
    residence_time_zone: list[float]         # [0..8] s
    overflow_main_feeder: bool
    overflow_side_feeder: bool


def _scl_limit(value: float, lo: float, hi: float) -> float:
    """SCL : LIMIT(MN := lo, IN := value, MX := hi)."""
    return max(lo, min(hi, value))


def compute_process_state(config: list[int], params: ProcessParams) -> ProcessState:
    """Reproduction BRUTE du Network 7 (PDF 2-CALCULS, lignes 0001-0170).

    Aucune correction des bugs identifiés du pseudo-code source.
    Pur : ne modifie ni `config` ni `params` (copie locale en interne).
    """
    N = N_POSITIONS
    cfg = config  # Correction C8 : pas de mutation, invariant tip garanti par Étape 1

    # ----- 1) SideFeeder_Position (PDF L0001-0011) -----
    side_feeder_pos = side_feeder_position(cfg, params.side_feeder_zone)

    # ----- 2) Vitesse vis en tr/s (PDF L0015) -----
    n_rps = params.screw_rpm / 60.0

    # ----- 3) Débit feeder en g/s (PDF L0018-0019) -----
    flow_rate_g_s_feeder1 = params.feeder1_flow_rate_g_per_s
    flow_rate_g_s_feeder2 = params.feeder2_flow_rate_g_per_s

    # ----- 4) Local_Free_Volume + ByRev (PDF L0025-0039) -----
    local_free_volume_cm3: list[float] = [0.0] * N
    local_free_volume_cm3_by_rev: list[float] = [0.0] * N
    for i in range(N):
        v = cfg[i]
        if v < PART2_OFFSET:                         # 1ère partie
            if v == 2:                               # PDF L0028 (× N_SCREWS bivis)
                local_free_volume_cm3[i] = BASE_FREE_VOL_PER_POS - N_SCREWS * VOLUME_CM3[2]
            else:                                    # PDF L0030 (× N_SCREWS bivis)
                local_free_volume_cm3[i] = BASE_FREE_VOL_PER_POS - N_SCREWS * VOLUME_CM3[v] / 2.0
            local_free_volume_cm3_by_rev[i] = local_free_volume_cm3[i] * FACTOR_FREE_BY_REV[v]
        else:                                        # 2ème partie : recopie i-1
            local_free_volume_cm3_by_rev[i] = local_free_volume_cm3_by_rev[i - 1]
            local_free_volume_cm3[i] = local_free_volume_cm3[i - 1]

    # ----- 5) Init FF, VolFlow, Overflow (PDF L0043-0049) -----
    fill_factor_local: list[float] = [0.0] * N
    vol_flow_cm3_s: list[float] = [0.0] * N
    residence_time_local: list[float] = [0.0] * N
    overflow_cm3_s: float = 0.0
    overflow_main_feeder: bool = False
    overflow_side_feeder: bool = False

    # Variables Temp SCL (défaut Real = 0.0)
    qvol_feeder1_cm3_s: float = 0.0
    qvol_feeder2_cm3_s: float = 0.0
    capacity_cm3_s: float = 0.0
    bulk_density: float = 0.0
    t_local: float = 0.0
    delta_t: float = 0.0
    feeder_prorata: float = 0.0
    thermal_factor: float = 0.0   # PDF : pas d'init explicite, défaut SCL = 0.0
    fill_factor_average: float = 0.0
    residence_time_total: float = 0.0

    # ----- 6) Fill factor au Main feeder (PDF L0053-0075) -----
    if params.feeder1_bulk_density > 0.0 and n_rps > 0.0:
        t_local = min(params.tref, params.temp_z[1])  # Correction C6 : Tref au lieu de littéral 20.0
        bulk_density = params.feeder1_bulk_density / (
            1.0 + params.feeder1_thermal_exp * (t_local - params.tref)
        )
        qvol_feeder1_cm3_s = flow_rate_g_s_feeder1 / bulk_density
        capacity_cm3_s = n_rps * local_free_volume_cm3_by_rev[MAIN_FEEDER_POSITION]

        if capacity_cm3_s > 0.0:
            fill_factor_local[MAIN_FEEDER_POSITION] = _scl_limit(
                qvol_feeder1_cm3_s / capacity_cm3_s, 0.0, 1.0
            )
            fill_factor_average = fill_factor_local[MAIN_FEEDER_POSITION]

        if fill_factor_local[MAIN_FEEDER_POSITION] >= 1.0:
            overflow_main_feeder = True

        vol_flow_cm3_s[MAIN_FEEDER_POSITION] = (
            fill_factor_local[MAIN_FEEDER_POSITION] * capacity_cm3_s
        )

        if vol_flow_cm3_s[MAIN_FEEDER_POSITION] > 0.0:
            residence_time_local[MAIN_FEEDER_POSITION] = (
                local_free_volume_cm3[MAIN_FEEDER_POSITION]
                / vol_flow_cm3_s[MAIN_FEEDER_POSITION]
            )
        else:
            residence_time_local[MAIN_FEEDER_POSITION] = 0.0

        residence_time_total = residence_time_local[MAIN_FEEDER_POSITION]

    # ----- 7) Fill factor au Side feeder (PDF L0079-0089) -----
    # Correction C5 : ajout garde n_rps > 0 (symétrie avec main feeder L0053).
    if side_feeder_pos < TIP_PART2_POS and params.feeder2_bulk_density > 0.0 and n_rps > 0.0:
        bulk_density = params.feeder2_bulk_density / (
            1.0 + params.feeder2_thermal_exp
            * (params.temp_z[params.side_feeder_zone] - params.tref)
        )
        qvol_feeder2_cm3_s = flow_rate_g_s_feeder2 / bulk_density
        capacity_cm3_s = n_rps * local_free_volume_cm3_by_rev[side_feeder_pos]

        if capacity_cm3_s > 0.0:
            fill_factor_local[side_feeder_pos] = _scl_limit(
                qvol_feeder2_cm3_s / capacity_cm3_s, 0.0, 1.0
            )

        vol_flow_cm3_s[side_feeder_pos] = (
            fill_factor_local[side_feeder_pos] * capacity_cm3_s
        )

    # ----- 8) Propagation MainFeeder+1 → 80 (PDF L0094-0153) -----
    for i in range(MAIN_FEEDER_POSITION + 1, N):
        v = cfg[i]
        if v < PART2_OFFSET:                         # PDF L0096 : 1ère partie

            # PDF L0099-0105 — Correction C1 : sens de parcours inversé pour
            # trouver le PLUS GRAND z tel que i ≥ Start_ElmtZone[z] (zone réelle).
            zone = 0
            for z in range(8, -1, -1):
                if i >= START_ELMT_ZONE[z]:
                    zone = z
                    break

            delta_t = params.temp_z[zone] - params.tref  # Correction C7 : Tref au lieu de littéral 20.0

            # PDF L0108-0113 — Correction C2 : branche else explicite à 1.0
            # (en absence de matière, pas de correction thermique = facteur neutre).
            if i <= side_feeder_pos:
                thermal_factor = 1.0 + params.feeder1_thermal_exp * delta_t
            elif (qvol_feeder1_cm3_s + qvol_feeder2_cm3_s) > 0:
                feeder_prorata = qvol_feeder1_cm3_s / (
                    qvol_feeder1_cm3_s + qvol_feeder2_cm3_s
                )
                thermal_factor = (
                    feeder_prorata
                    * (1.0 + params.feeder1_thermal_exp * delta_t)
                    + (1.0 - feeder_prorata)
                    * (1.0 + params.feeder2_thermal_exp * delta_t)
                )
            else:
                thermal_factor = 1.0

            thermal_factor = _scl_limit(
                thermal_factor, THERMAL_FACTOR_MIN, THERMAL_FACTOR_MAX
            )

            # PDF L0117 : capacité corrigée température
            capacity_cm3_s = n_rps * local_free_volume_cm3_by_rev[i] * thermal_factor

            # Correction C3 : ligne ConvFactor (PDF L0120) supprimée — code mort.

            # PDF L0123-0130 : propagation + overflow
            vol_flow_cm3_s_incoming = (
                vol_flow_cm3_s[i] + vol_flow_cm3_s[i - 1] + overflow_cm3_s
            )
            if vol_flow_cm3_s_incoming > capacity_cm3_s:
                vol_flow_cm3_s[i] = capacity_cm3_s
                overflow_cm3_s = vol_flow_cm3_s_incoming - capacity_cm3_s
            else:
                vol_flow_cm3_s[i] = vol_flow_cm3_s_incoming
                overflow_cm3_s = 0.0

            # PDF L0132-0136 : fill factor local
            if capacity_cm3_s > 0.0:
                fill_factor_local[i] = _scl_limit(
                    vol_flow_cm3_s[i] / capacity_cm3_s, 0.0, 1.0
                )
            else:
                fill_factor_local[i] = 0.0

        else:                                        # PDF L0138-0140 : 2ème partie
            fill_factor_local[i] = fill_factor_local[i - 1]
            vol_flow_cm3_s[i] = vol_flow_cm3_s[i - 1]

        # PDF L0142-0150 — Correction C4 : pas de reset des cumuls si VolFlow=0.
        # Une moyenne/somme cumulative ne s'invalide pas sur un point local nul.
        if vol_flow_cm3_s[i] > 0.0:
            fill_factor_average = fill_factor_average + fill_factor_local[i]
            residence_time_local[i] = local_free_volume_cm3[i] / vol_flow_cm3_s[i]
            residence_time_total = residence_time_total + residence_time_local[i]
        else:
            residence_time_local[i] = 0.0

    # PDF L0153 : moyenne FF
    fill_factor_average = fill_factor_average / (N - MAIN_FEEDER_POSITION)  # 81 - 4 = 77

    # PDF L0156-0160 : overflow side feeder
    if side_feeder_pos < TIP_PART2_POS:
        if fill_factor_local[side_feeder_pos] >= 1.0:
            overflow_side_feeder = True

    # ----- 9) Résidence par zone (PDF L0162-0170) -----
    residence_time_zone: list[float] = [0.0] * (len(START_ELMT_ZONE) - 1)
    for z in range(0, 9):                            # FOR #Zone := 0 TO 8
        for i in range(START_ELMT_ZONE[z], START_ELMT_ZONE[z + 1]):
            residence_time_zone[z] = residence_time_zone[z] + residence_time_local[i]

    return ProcessState(
        side_feeder_position=side_feeder_pos,
        local_free_volume_cm3=local_free_volume_cm3,
        local_free_volume_by_rev=local_free_volume_cm3_by_rev,
        fill_factor_local=fill_factor_local,
        vol_flow_cm3_s=vol_flow_cm3_s,
        residence_time_local=residence_time_local,
        fill_factor_average=fill_factor_average,
        residence_time_total=residence_time_total,
        residence_time_zone=residence_time_zone,
        overflow_main_feeder=overflow_main_feeder,
        overflow_side_feeder=overflow_side_feeder,
    )


# ---------------------------------------------------------------------------
# Wrappers simples — compatibilité HMI (1_Profile.py)
# ---------------------------------------------------------------------------
def _params_from_hmi(rpm: float, feed_g_per_min: float, bulk_density: float) -> ProcessParams:
    """Convertit les 3 paramètres exposés par l'UI Streamlit en ProcessParams.
    Pas de side feeder, pas de thermique (Temp_Z = Tref partout)."""
    return ProcessParams(
        screw_rpm=rpm,
        feeder1_flow_rate_g_per_s=feed_g_per_min / 60.0,
        feeder1_bulk_density=bulk_density,
    )


def fill_factor_average(
    config: list[int], rpm: float, feed_g_per_min: float, bulk_density: float
) -> float:
    return compute_process_state(config, _params_from_hmi(rpm, feed_g_per_min, bulk_density)).fill_factor_average


# ---------------------------------------------------------------------------
# Correction manager — residence time : dépendance explicite au screw RPM
# ---------------------------------------------------------------------------
# Source : app/residence_time_correction.pdf (manager 2026-06-09).
#
# Constat : dans `compute_process_state` (Network 7 PLC), au main feeder
# `vol_flow = qvol_feeder = m_dot / ρ`, qui est INDÉPENDANT de la vitesse vis ;
# `residence_time_local = V_local / vol_flow` est donc lui aussi RPM-indépendant
# (≈ 167,6 s constant quel que soit le RPM). Manager : c'est incohérent — à
# débit matière constant, si la vitesse vis augmente, le temps de séjour doit
# diminuer (et approximativement par moitié quand le RPM double).
#
# Correction V1 (exigence manager) : appliquer un facteur `rpm_ref / screw_rpm`
# (rpm_ref = 100 rpm) au temps de séjour calculé par Network 7. La couche PLC
# reste INTOUCHÉE (CLAUDE.md « do NOT modify compute_process_state ») ; seule
# la valeur exposée à l'UI via les wrappers est corrigée.
#
# Garde dur : si screw_rpm <= 0 ou feed_g_per_min <= 0, on retourne 0.0 — les
# consommateurs (Profile / Moteur Procédé) interprètent 0 comme « Non calculable »
# (jamais affiché comme une vérité procédé).
RESIDENCE_TIME_RPM_REFERENCE: float = 100.0


def _residence_rpm_correction(screw_rpm: float) -> float:
    """Facteur correctif manager rpm_ref/screw_rpm (≥0). 0 si rpm invalide."""
    rpm = float(screw_rpm)
    if rpm <= 0.0:
        return 0.0
    return RESIDENCE_TIME_RPM_REFERENCE / rpm


def residence_time(
    config: list[int], rpm: float, feed_g_per_min: float, bulk_density: float
) -> float:
    """Temps de séjour total (s) — Network 7 ajusté du facteur RPM manager.

    Retourne 0.0 (« Non calculable » côté UI) si rpm<=0 ou débit<=0.
    """
    if rpm <= 0.0 or feed_g_per_min <= 0.0:
        return 0.0
    base = compute_process_state(
        config, _params_from_hmi(rpm, feed_g_per_min, bulk_density)
    ).residence_time_total
    return base * _residence_rpm_correction(rpm)


def zone_residence_times(
    config: list[int], rpm: float, feed_g_per_min: float, bulk_density: float
) -> list[float]:
    """Temps de séjour par zone (Feed + Z1..Z8) — ajusté du facteur RPM manager.

    Liste de 9 zéros si rpm<=0 ou débit<=0 (consommateurs affichent « — »).
    """
    if rpm <= 0.0 or feed_g_per_min <= 0.0:
        return [0.0] * 9
    base = compute_process_state(
        config, _params_from_hmi(rpm, feed_g_per_min, bulk_density)
    ).residence_time_zone
    factor = _residence_rpm_correction(rpm)
    return [v * factor for v in base]


# ---------------------------------------------------------------------------
# Stub conservé — recommandations IA (Étape 5)
# ---------------------------------------------------------------------------
def ai_recommendations(*_args, **_kwargs) -> list[dict]:
    """TODO Étape 5 : règles IA sur FF / résidence / overflow."""
    return []
