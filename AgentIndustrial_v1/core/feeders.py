"""
feeders.py — Modèle métier feeders avancé (V1 AgentIndustrial).

Caractéristiques :
- 1 à 5 feeders simultanés (typique en compounding bivis SSB)
- 6 types de matière : granulés, poudres, liquide, semi-liquide, gaz, supercritique
- 9 positions d'injection : Z0 (main feed) → Z7 + die (post-die)
- Pour chaque feeder : type matière, position, vitesse, débit massique,
  densité, dilatation thermique.

Source d'inspiration : pratiques compounding industriel (Coperion, Leistritz,
Thermo Fisher) et littérature SSB (Schubert 2023, Klemens 2024).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable


# ---------------------------------------------------------------------------
# Types de matière
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MaterialType:
    """Caractéristiques d'une famille de matière injectable.

    typical_density_range  : g/cm³ (bulk pour solides, vrai ρ pour fluides)
    feeder_tech            : technologie feeder par défaut adaptée à la matière
    typical_thermal_alpha  : coefficient de dilatation thermique typique (1/K)
    safe_temperature_C     : (T_min, T_max) — bornes au-delà desquelles la
                             matière dégrade / change d'état / pose un risque
                             procédé. Sert au check incompatibilité thermique.
    allowed_positions      : positions d'injection physiquement valides.
                             Ex. un gaz/scCO₂ ne s'injecte pas au Z0 (avant
                             fusion) — il doit aller en zone fondue.
    """
    id: str
    label_fr: str
    phase: str  # "solid" | "liquid" | "gas" | "supercritical"
    typical_density_range: tuple[float, float]
    feeder_tech: str
    typical_thermal_alpha: float
    safe_temperature_C: tuple[float, float]
    allowed_positions: tuple[str, ...]
    label_en: str = ""  # libellé EN (i18n) — vide ⇒ retombe sur label_fr

    def label_i18n(self, lang: str = "fr") -> str:
        """Libellé matière selon la langue UI (texte uniquement, zéro logique)."""
        return (self.label_en or self.label_fr) if lang == "en" else self.label_fr


# Valeurs typiques industrie compounding (compactes mais réalistes).
# Les ρ et α sont des ordres de grandeur — l'opérateur les ajuste par feeder.
# Note SSB : les bornes thermiques sont volontairement basses pour les
# matériaux actifs (cathode/anode) — la majorité des cathodes Li dégradent
# au-delà de 100-120 °C en présence d'humidité ou de solvants résiduels.
MATERIAL_TYPES: dict[str, MaterialType] = {
    "granules": MaterialType(
        id="granules", label_fr="Granulés", label_en="Granules",
        phase="solid", typical_density_range=(0.50, 0.95),
        feeder_tech="gravimetric loss-in-weight",
        typical_thermal_alpha=7.0e-5,
        safe_temperature_C=(0.0, 250.0),
        allowed_positions=("Z0",),
    ),
    "powder": MaterialType(
        id="powder", label_fr="Poudres", label_en="Powders",
        phase="solid", typical_density_range=(0.15, 1.20),
        feeder_tech="twin-screw loss-in-weight",
        typical_thermal_alpha=5.0e-5,
        # Bornes basses : matériaux actifs SSB sensibles thermiquement.
        safe_temperature_C=(0.0, 120.0),
        # Une poudre peut entrer en main feed (Z0) ou en side-feed Z2..Z4.
        allowed_positions=("Z0", "Z2", "Z3", "Z4"),
    ),
    "liquid": MaterialType(
        id="liquid", label_fr="Liquide", label_en="Liquid",
        phase="liquid", typical_density_range=(0.70, 1.50),
        feeder_tech="piston / gear pump",
        typical_thermal_alpha=8.0e-4,
        # Solvants/électrolytes Li : dégradation au-delà de ~80°C.
        safe_temperature_C=(0.0, 80.0),
        # Injection typique en zone fondue (post-melt), pas au Z0.
        allowed_positions=("Z3", "Z4", "Z5", "Z6"),
    ),
    "semi_liquid": MaterialType(
        id="semi_liquid", label_fr="Semi-liquide", label_en="Semi-liquid",
        phase="liquid", typical_density_range=(0.90, 1.40),
        feeder_tech="positive-displacement pump",
        typical_thermal_alpha=6.0e-4,
        safe_temperature_C=(0.0, 150.0),
        allowed_positions=("Z2", "Z3", "Z4", "Z5"),
    ),
    "gas": MaterialType(
        id="gas", label_fr="Gaz", label_en="Gas",
        phase="gas", typical_density_range=(0.0010, 0.0050),
        feeder_tech="mass-flow controller",
        typical_thermal_alpha=3.4e-3,
        safe_temperature_C=(-50.0, 300.0),
        # Gaz : injection uniquement en zone fondue (sinon fuite vers entrée).
        allowed_positions=("Z4", "Z5", "Z6"),
    ),
    "supercritical": MaterialType(
        id="supercritical", label_fr="Supercritique (scCO₂)", label_en="Supercritical (scCO₂)",
        phase="supercritical", typical_density_range=(0.20, 0.95),
        feeder_tech="high-pressure metering pump",
        typical_thermal_alpha=2.0e-3,
        # scCO₂ : Tc=31°C, état supercritique au-dessus.
        safe_temperature_C=(31.0, 100.0),
        allowed_positions=("Z4", "Z5", "Z6"),
    ),
}


# ---------------------------------------------------------------------------
# Positions d'injection (extrusion bivis Rondol)
# ---------------------------------------------------------------------------
# Convention V1 : Z0 = entrée matière (main feeder), Z1..Z7 = zones procédé,
# die = injection post-vis (rare mais possible : liquide ou gaz).
FEEDER_POSITIONS: tuple[str, ...] = ("Z0", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "die")

# Mapping logique vers l'index de zone existante app/screw_logic.py.
# Feed=0, Z1=1, ..., Z8=8. On reste cohérent avec la base Kévin.
POSITION_TO_LEGACY_ZONE: dict[str, int] = {
    "Z0": 0, "Z1": 1, "Z2": 2, "Z3": 3, "Z4": 4,
    "Z5": 5, "Z6": 6, "Z7": 7, "die": 8,
}


# ---------------------------------------------------------------------------
# FeederSpec
# ---------------------------------------------------------------------------
@dataclass
class FeederSpec:
    """Spécification d'un feeder.

    feeder_id            : 1..5 (5 feeders max par extrudeuse)
    enabled              : si False → ignoré par l'agent IA et les bilans
    label                : libellé libre opérateur ("LFP", "PVDF", "LiTFSI")
    material_id          : clé MATERIAL_TYPES
    position             : clé FEEDER_POSITIONS
    speed_rpm            : vitesse rotation feeder (gravimetric/loss-in-weight).
                           None si matière fluide (pas pertinent).
    mass_flow_g_per_min  : débit massique cible
    density_g_per_cm3    : ρ effective (bulk pour solides, vrai ρ pour fluides)
    thermal_expansion_per_K : α (1/K) — sert au check incompatibilité thermique

    --- Champs matière étendus (exigence manager 2026-05-20) ---
    polymer_name         : nom du polymère ou mélange (PVDF, PEO, LFP+PVDF…)
    t_degradation_C      : T° de dégradation chimique du polymère/mélange.
                           Si renseignée, prend le pas sur MaterialType.safe_T[1]
                           dans les checks rules/cooling.
    tga_onset_C          : ATG/TGA — T° d'onset de perte massique. Sert d'alerte
                           anticipée avant dégradation chimique.
    viscosity_pa_s       : viscosité de référence (Pa·s) à T procédé typique.
                           Module l'échauffement par cisaillement dans cooling.
    t_melt_C             : T° de fusion (thermomécanique, polymère semi-cristallin).
    t_glass_C            : T° de transition vitreuse Tg (amorphe).
    """
    feeder_id: int
    enabled: bool = True
    label: str = ""
    material_id: str = "granules"
    position: str = "Z0"
    speed_rpm: float | None = 120.0
    mass_flow_g_per_min: float = 30.0
    density_g_per_cm3: float = 0.55
    thermal_expansion_per_K: float = 7.0e-5
    # Champs matière étendus (optionnels — None = utiliser défaut MaterialType)
    polymer_name: str = ""
    t_degradation_C: float | None = None
    tga_onset_C: float | None = None
    viscosity_pa_s: float | None = None
    t_melt_C: float | None = None
    t_glass_C: float | None = None

    # --------- API ergonomique ---------
    @property
    def material(self) -> MaterialType:
        return MATERIAL_TYPES[self.material_id]

    @property
    def phase(self) -> str:
        return self.material.phase

    @property
    def is_solid(self) -> bool:
        return self.phase == "solid"

    @property
    def is_fluid(self) -> bool:
        return self.phase in ("liquid", "gas", "supercritical")

    def display_name(self, lang: str = "fr") -> str:
        base = self.label.strip() or f"Feeder #{self.feeder_id}"
        return f"{base} · {self.material.label_i18n(lang)}"

    # --------- Bornes thermiques effectives (rules + cooling) ---------
    def effective_t_max_C(self) -> float:
        """Borne haute sûre — priorité aux données opérateur si renseignées.

        Ordre : t_degradation_C (saisie experte) > tga_onset_C (mesure ATG)
        > MaterialType.safe_temperature_C[1] (défaut famille matière).
        """
        if self.t_degradation_C is not None and self.t_degradation_C > 0:
            return float(self.t_degradation_C)
        if self.tga_onset_C is not None and self.tga_onset_C > 0:
            return float(self.tga_onset_C)
        return float(self.material.safe_temperature_C[1])

    def effective_t_min_C(self) -> float:
        """Borne basse opérationnelle (héritée de la famille matière)."""
        return float(self.material.safe_temperature_C[0])

    def viscosity_factor(self) -> float:
        """Multiplicateur de dissipation visqueuse 0,7..1,8 selon viscosité.

        Référence implicite ≈ 1000 Pa·s (compounding standard). Une matière
        beaucoup plus visqueuse (PVDF chargé, gélifiant…) génère plus de chaleur
        à débit/rpm égal.
        """
        if self.viscosity_pa_s is None or self.viscosity_pa_s <= 0:
            return 1.0
        import math
        return max(0.7, min(1.8, 1.0 + 0.18 * math.log10(self.viscosity_pa_s / 1000.0)))


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------
def default_main_feeder() -> FeederSpec:
    """Feeder principal par défaut — granulés au Z0 (cas démo standard)."""
    return FeederSpec(
        feeder_id=1, enabled=True, label="Main",
        material_id="granules", position="Z0",
        speed_rpm=120.0, mass_flow_g_per_min=30.0,
        density_g_per_cm3=0.55, thermal_expansion_per_K=7.0e-5,
    )


def empty_feeder(feeder_id: int) -> FeederSpec:
    """Feeder désactivé (slot vide)."""
    return FeederSpec(
        feeder_id=feeder_id, enabled=False, label="",
        material_id="powder", position="Z3",
        speed_rpm=0.0, mass_flow_g_per_min=0.0,
        density_g_per_cm3=0.30, thermal_expansion_per_K=5.0e-5,
    )


def new_feeder_bank() -> list[FeederSpec]:
    """Banc initial : 1 main feeder actif + 4 slots désactivés (5 max)."""
    bank = [default_main_feeder()]
    bank.extend(empty_feeder(i) for i in range(2, 6))
    return bank


def update_feeder(bank: list[FeederSpec], feeder_id: int, **kwargs) -> list[FeederSpec]:
    """Retourne une nouvelle banque avec le feeder mis à jour (immutable-friendly)."""
    return [
        replace(f, **kwargs) if f.feeder_id == feeder_id else f
        for f in bank
    ]


# ---------------------------------------------------------------------------
# Bilans
# ---------------------------------------------------------------------------
def active_feeders(bank: Iterable[FeederSpec]) -> list[FeederSpec]:
    return [f for f in bank if f.enabled]


def total_mass_flow(bank: Iterable[FeederSpec]) -> float:
    """Somme des débits massiques (g/min) des feeders actifs."""
    return sum(f.mass_flow_g_per_min for f in active_feeders(bank))


def mass_flow_by_phase(bank: Iterable[FeederSpec]) -> dict[str, float]:
    """Débit massique total par phase (solid/liquid/gas/supercritical)."""
    out: dict[str, float] = {"solid": 0.0, "liquid": 0.0, "gas": 0.0, "supercritical": 0.0}
    for f in active_feeders(bank):
        out[f.phase] = out.get(f.phase, 0.0) + f.mass_flow_g_per_min
    return out


def solid_loading_pct(bank: Iterable[FeederSpec]) -> float:
    """% massique solide dans le mélange (proxy chargement vis)."""
    flows = mass_flow_by_phase(bank)
    total = sum(flows.values())
    if total <= 0.0:
        return 0.0
    return 100.0 * flows["solid"] / total


def equivalent_main_density(bank: Iterable[FeederSpec]) -> float:
    """ρ équivalente pondérée masse — utilisée pour les calculs FF/résidence.

    Limité aux phases solides (les liquides/gaz n'occupent pas le volume bulk
    de la même façon ; cf. analyse compounding Schubert 2023).
    """
    flows = 0.0
    weighted = 0.0
    for f in active_feeders(bank):
        if not f.is_solid:
            continue
        flows += f.mass_flow_g_per_min
        weighted += f.mass_flow_g_per_min * f.density_g_per_cm3
    if flows <= 0.0:
        return 0.55  # défaut bulk générique
    return weighted / flows
