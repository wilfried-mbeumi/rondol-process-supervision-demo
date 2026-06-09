"""
process.py — État procédé complet (température, vis, KPIs, V2 placeholders).

ProcessState agrège tout ce que l'agent IA a besoin de raisonner :
- profil thermique (Z1..Z8 + die)
- vitesse vis (rpm)
- bilan feeders (cf. core.feeders)
- KPIs hérités de l'existant Kévin : SME, fill factor, residence time, free volume
- placeholders V2 : torque (% couple) et pressure (bar) — réservés pour la
  boucle de feedback réelle à venir.

Ce module ne *calcule* pas les KPIs vis lui-même : il délègue à
`core.screw_adapter` qui ré-utilise app/screw_logic.py et app/screw_render.py
sans les modifier (conserver l'existant déjà fonctionnel).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .feeders import FeederSpec, new_feeder_bank


# ---------------------------------------------------------------------------
# Cibles métier extrusion bivis SSB (valeurs par défaut — modifiables UI)
# ---------------------------------------------------------------------------
# Sources : pratique compounding pharma/SSB + littérature dry/semi-dry SSB.
DEFAULT_ZONE_TARGETS_C: dict[str, float] = {
    "Z1": 25.0, "Z2": 60.0, "Z3": 80.0, "Z4": 90.0,
    "Z5": 95.0, "Z6": 95.0, "Z7": 90.0, "Z8": 85.0,
    # Filière multi-zones : rampe de refroidissement contrôlé en sortie de
    # vis (calibrage / mise en forme). die = zone die la + proche de la vis.
    "die": 80.0, "die2": 75.0, "die3": 70.0, "die4": 65.0,
}

# Zones procédé chauffées (ordre amont → aval) — base des règles thermiques.
PROCESS_ZONE_ORDER: tuple[str, ...] = (
    "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8",
)

# Filière : 1 à 4 zones die. die = die n°1 (rétro-compatible avec R7).
DIE_KEYS: tuple[str, ...] = ("die", "die2", "die3", "die4")


def active_die_keys(n_die_zones: int) -> list[str]:
    """Clés des zones die réellement actives (0..4).

    Manager 2026-06-09 : 0 zone die autorisé (filière absente). Retourne une
    liste vide dans ce cas — les consommateurs gèrent « pas de filière ».
    """
    n = max(0, min(4, int(n_die_zones)))
    return list(DIE_KEYS[:n])


def default_zone_target(key: str) -> float:
    """Consigne par défaut d'une zone — lecture sécurisée, ne crashe jamais.

    Tolère les clés die manquantes (`die1`/`die2`/...) : repli sur la zone
    `die`, puis 95 °C. Utilisé partout où une clé zone dynamique est lue.
    """
    return float(
        DEFAULT_ZONE_TARGETS_C.get(
            key, DEFAULT_ZONE_TARGETS_C.get("die", 95.0)
        )
    )

# Fill Factor cibles (cf. existant Kévin — Profile.py)
FF_TARGET_LOW: float = 0.30
FF_TARGET_HIGH: float = 0.55

# SME — Specific Mechanical Energy (énergie mécanique spécifique, kWh/kg).
# Seuils PROCÉDÉ configurés (ordre de grandeur compounding fin) : au-delà du
# seuil critique, sollicitation thermomécanique excessive. Ce sont des seuils
# de PROCÉDÉ, PAS un critère lié à une matière/additif particulier (ex. CNT).
SME_WARNING_KWH_PER_KG: float = 0.30
SME_CRITICAL_KWH_PER_KG: float = 0.40

# Residence time — fenêtre acceptable extrusion fine SSB.
RT_MIN_S: float = 5.0
RT_MAX_S: float = 120.0

# Bande de régulation thermique d'une zone fourreau (PID extrudeuse réelle :
# ±2-3 °C autour de la consigne). Ce n'est PAS un réglage opérateur arbitraire
# mais une caractéristique procédé — d'où sa définition en constante métier
# (remplace l'ancien dial « Tolérance température ± » de l'UI Settings).
THERMAL_REG_BAND_C: float = 3.0


@dataclass
class ScrewKPIs:
    """KPIs vis — calculés en délégation à screw_adapter."""
    n_elements: float = 0.0
    free_volume_cm3: float = 0.0
    fill_factor: float = 0.0       # 0..1
    residence_time_s: float = 0.0
    sme_kwh_per_kg: float = 0.0
    zone_residence_s: list[float] = field(default_factory=lambda: [0.0] * 9)
    profile_archetype: str = ""
    profile_summary: str = ""


@dataclass
class V2Feedback:
    """Placeholders V2 — feedback torque/pressure pas encore alimenté en V1.

    En V1, ces champs sont saisis manuellement (ou laissés à None).
    En V2, ils seront alimentés en streaming par l'extrudeuse via OPC-UA / API.
    """
    torque_pct: float | None = None        # 0..100 % couple nominal
    pressure_die_bar: float | None = None  # pression à la filière
    pressure_zone_bar: dict[str, float] = field(default_factory=dict)
    # Hooks pour la future boucle de feedback (V2).
    feedback_enabled: bool = False
    last_update_iso: str = ""


@dataclass
class ProcessState:
    """État procédé courant — source unique consommée par l'agent IA."""
    # Vis
    screw_config: list[int] = field(default_factory=list)  # cf. app/screw_logic.py
    screw_rpm: float = 120.0
    # Thermique
    zone_temps_C: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_ZONE_TARGETS_C)
    )
    # Feeders
    feeders: list[FeederSpec] = field(default_factory=new_feeder_bank)
    # KPIs (remplis par screw_adapter.refresh_kpis)
    kpis: ScrewKPIs = field(default_factory=ScrewKPIs)
    # V2
    v2: V2Feedback = field(default_factory=V2Feedback)
    # Profil thermique extrusion : nombre de zones die actives (1..4).
    # (Le champ historique « cooling_zone_selected » a été retiré : la
    # fonctionnalité « Test de refroidissement » n'existe pas dans le procédé
    # réel — exigence manager 2026-05-20. Le diagnostic thermique cible
    # désormais automatiquement la zone la plus chaude.)
    n_die_zones: int = 1

    @property
    def die_keys(self) -> list[str]:
        """Zones die actives selon n_die_zones."""
        return active_die_keys(self.n_die_zones)

    @property
    def die_temps_C(self) -> list[float]:
        """Consignes des zones die actives (amont → aval)."""
        return [
            float(self.zone_temps_C.get(k, default_zone_target(k)))
            for k in self.die_keys
        ]

    # --------- Helpers ---------
    def temp_at(self, position: str) -> float:
        """T° à une position feeder (Z0..Z7, die). Z0 = aval immédiat zone Z1."""
        if position == "Z0":
            # Z0 = trémie/entrée matière : on prend ambiant Z1 comme proxy
            return self.zone_temps_C.get("Z1", 25.0)
        return self.zone_temps_C.get(position, 25.0)
