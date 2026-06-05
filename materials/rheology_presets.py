"""rheology_presets.py — paramètres rhéologiques NOMINAUX par matière (DONNÉES).

SÉPARATION DE RESPONSABILITÉ :
  - `materials/rheology.py` = MOTEUR de formules PUR (Carreau-Yasuda, power-law,
    Cross, Arrhenius) — aucune constante matière codée en dur.
  - CE fichier = jeu de PARAMÈTRES (données) à passer à ces formules. Il ne
    calcule AUCUNE viscosité : il ne fait que stocker les coefficients par
    matière et les résoudre par nom.

Le calcul effectif η(γ̇, T) — `carreau_yasuda_viscosity(...) × arrhenius(...)` —
est DIFFÉRÉ au bloc 3.3. Ici, on prépare uniquement les données d'entrée.

⚠️ VALEURS NOMINALES (ordre de grandeur littérature, fondu chargé batterie
LFP/LATP). À RECALIBRER sur essais réels (Essais_07-13_Avril_2026,
references/manager_requirements). Tant que le bloc 3.3/E4 n'est pas codé, RIEN
ne consomme ces nombres — ils ne modifient aucun comportement Phase 1/1.5/2.

Forme cible (manager E3, cf. rheology.carreau_yasuda_viscosity) :
    η(γ̇) = η∞ + (η₀ − η∞)·[1 + (λγ̇)^a]^((n−1)/a)
puis décalage thermique Arrhenius a_T = exp((Ea/R)·(1/T − 1/Tref)).
"""

from __future__ import annotations

from dataclasses import dataclass

from materials.powder import Powder


@dataclass(frozen=True)
class MaterialRheology:
    """Paramètres rhéologiques d'UNE matière (entrées du moteur rheology.py).

    Tous NOMINAUX, à recalibrer. Aucune viscosité n'est stockée ici — seulement
    les coefficients passés aux lois de `materials.rheology`.

    Attributs (forme Carreau-Yasuda manager + Arrhenius) :
      name                     : identifiant lisible (= Powder.name attendu).
      eta_zero_pa_s            : viscosité plateau bas cisaillement η₀ (Pa·s).
      eta_inf_pa_s             : viscosité plateau haut cisaillement η∞ (Pa·s).
      relax_time_s             : temps de relaxation λ (s) — coude rhéofluidifiant.
      flow_index_n             : indice d'écoulement n (∈ (0, 1] = shear-thinning).
      yasuda_a                 : exposant de transition a (défaut 2 = Carreau).
      activation_energy_j_mol  : énergie d'activation Ea (J/mol) pour a_T Arrhenius.
      tref_c                   : température de référence (°C) du décalage thermique.
    """
    name: str
    eta_zero_pa_s: float
    eta_inf_pa_s: float
    relax_time_s: float
    flow_index_n: float
    yasuda_a: float
    activation_energy_j_mol: float
    tref_c: float = 20.0


# ---------------------------------------------------------------------------
# Defaut explicite documente — matiere SANS preset rheo dedie.
# NON silencieux : `melt_rheology_for` renvoie CE preset (avec un name refletant
# la matiere demandee) plutot que de lever ou de retourner None en douce.
# Valeurs neutres/prudentes (newtonien doux), a remplacer des qu'un preset existe.
# ---------------------------------------------------------------------------
DEFAULT_RHEOLOGY: MaterialRheology = MaterialRheology(
    name="DEFAULT",
    eta_zero_pa_s=1.0e3,
    eta_inf_pa_s=1.0e1,
    relax_time_s=0.1,
    flow_index_n=0.5,
    yasuda_a=2.0,
    activation_energy_j_mol=3.0e4,
    tref_c=20.0,
)


# ---------------------------------------------------------------------------
# Presets NOMINAUX par matiere — clefs alignees sur materials.powder.POWDERS.
# A RECALIBRER. Aucune consommation tant que 3.3/E4 ne sont pas codes.
# ---------------------------------------------------------------------------
MELT_RHEOLOGY: dict[str, MaterialRheology] = {
    "LiFePO4 (LFP)": MaterialRheology(
        name="LiFePO4 (LFP)", eta_zero_pa_s=4.0e3, eta_inf_pa_s=2.0e1,
        relax_time_s=0.20, flow_index_n=0.45, yasuda_a=2.0,
        activation_energy_j_mol=3.5e4, tref_c=20.0),
    "Li1.3Al0.3Ti1.7(PO4)3 (LATP)": MaterialRheology(
        name="Li1.3Al0.3Ti1.7(PO4)3 (LATP)", eta_zero_pa_s=3.5e3, eta_inf_pa_s=1.8e1,
        relax_time_s=0.18, flow_index_n=0.48, yasuda_a=2.0,
        activation_energy_j_mol=3.3e4, tref_c=20.0),
    "Graphite": MaterialRheology(
        name="Graphite", eta_zero_pa_s=2.5e3, eta_inf_pa_s=1.5e1,
        relax_time_s=0.15, flow_index_n=0.55, yasuda_a=2.0,
        activation_energy_j_mol=2.8e4, tref_c=20.0),
    "PVDF (liant)": MaterialRheology(
        name="PVDF (liant)", eta_zero_pa_s=6.0e3, eta_inf_pa_s=3.0e1,
        relax_time_s=0.30, flow_index_n=0.40, yasuda_a=2.0,
        activation_energy_j_mol=4.0e4, tref_c=20.0),
}


def melt_rheology_for(powder: Powder) -> MaterialRheology:
    """Résout les paramètres rhéo d'une poudre par LOOKUP DE NOM.

    - matière connue (`powder.name` dans MELT_RHEOLOGY) → son preset nominal.
    - matière inconnue → `DEFAULT_RHEOLOGY` mais avec `name` reflétant la matière
      demandée (défaut EXPLICITE, traçable, jamais silencieux ni None).

    PUR : ne calcule aucune viscosité, ne mute rien.
    """
    preset = MELT_RHEOLOGY.get(powder.name)
    if preset is not None:
        return preset
    # Defaut explicite : on clone le DEFAULT en marquant la matiere demandee.
    from dataclasses import replace
    return replace(DEFAULT_RHEOLOGY, name=f"DEFAULT({powder.name})")
