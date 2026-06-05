"""material_context.py — liaison feeder → matière le long de la vis (Phase 2).

Network 7 (`screw_logic.compute_process_state`) propage des DÉBITS et un facteur
thermique pondéré (prorata feeder1/feeder2), mais ne suit PAS la *composition*
matière position par position. Ce module fournit cette information manquante sous
une forme NOMINALE et explicitement documentée, sans rien recalculer du procédé.

Modèle nominal (Phase 2) :
  - en AMONT du port side feeder (position ≤ side_feeder_position) : seule la
    matière du feeder principal est présente → `upstream`.
  - en AVAL du port side feeder : mélange feeder1 + feeder2 au prorata des débits
    VOLUMIQUES (cohérent avec le `feeder_prorata` de screw_logic L598) → `blend`.

Les grandeurs de mélange (densité, Cp) sont DÉLÉGUÉES à `materials.mixing_rules`
(aucune formule réimplémentée ici). Le mapping amont/aval est une SIMPLIFICATION
nominale destinée à être raffinée (suivi de composition réel) en phase ultérieure.
"""

from __future__ import annotations

import engine  # noqa: F401  (déclenche le bootstrap sys.path du package)

from dataclasses import dataclass

from materials.powder import Powder
from materials.mixing_rules import (
    mixture_density,
    mixture_specific_heat,
    volume_to_mass_fractions,
)
from materials.rheology_presets import MaterialRheology, melt_rheology_for

# Sentinelle screw_logic : side feeder désactivé → position 81 (hors vis).
# Recopiée localement pour rester lisible ; la valeur de vérité reste
# screw_logic.SIDE_FEEDER_DISABLED_POSITION (cf. side_feeder_position).
SIDE_FEEDER_DISABLED_POSITION: int = 81


@dataclass(frozen=True)
class MaterialPresence:
    """Matière présente à une position : un constituant ou un mélange nominal.

    Attributs :
      label              : identifiant lisible ("LFP" ou "LFP+LATP", …).
      powders            : constituants présents (1 en amont, ≥1 en mélange).
      volume_fractions   : fractions VOLUMIQUES (somment à 1) alignées sur
                           `powders`. [1.0] pour un constituant unique.
      rheologies         : paramètres rhéo NOMINAUX par constituant, ALIGNÉS sur
                           `powders` (bloc 3.2). DONNÉES uniquement — résolus par
                           nom via melt_rheology_for. JAMAIS pré-combinés pour un
                           mélange : la combinaison de viscosité (log-additive)
                           est différée au bloc 3.3/E4. Aucune viscosité calculée.
      density_g_cm3      : densité du mélange — DÉLÈGUE à mixing_rules.
      cp_j_per_g_k       : Cp massique du mélange — DÉLÈGUE à mixing_rules
                           (requis par l'équation thermique manager E6).
      is_blend           : True si ≥2 constituants (aval side feeder).
    """
    label: str
    powders: tuple[Powder, ...]
    volume_fractions: tuple[float, ...]
    rheologies: tuple[MaterialRheology, ...]
    density_g_cm3: float
    cp_j_per_g_k: float
    is_blend: bool


@dataclass(frozen=True)
class FeedContext:
    """Contexte d'alimentation : matières feeder1 (principal) + feeder2 (latéral).

    Attributs :
      feeder1_powder    : poudre du feeder principal (toujours présente).
      feeder1_qvol_cm3_s: débit volumique feeder1 (cm³/s) — sert au prorata.
      feeder2_powder    : poudre du side feeder (None si pas de side feeder).
      feeder2_qvol_cm3_s: débit volumique feeder2 (cm³/s).
      side_feeder_position : position structurée du side feeder (sentinelle 81
                          si désactivé) — DÉLÈGue à screw_logic via l'appelant.

    Les débits volumiques sont fournis par l'appelant (ils proviennent de
    `ProcessState`/Network 7) : ce module ne les recalcule pas.
    """
    feeder1_powder: Powder
    feeder1_qvol_cm3_s: float = 0.0
    feeder2_powder: Powder | None = None
    feeder2_qvol_cm3_s: float = 0.0
    side_feeder_position: int = SIDE_FEEDER_DISABLED_POSITION

    def _upstream_presence(self) -> MaterialPresence:
        """Matière en amont du side feeder : feeder1 pur."""
        p = self.feeder1_powder
        return MaterialPresence(
            label=p.name,
            powders=(p,),
            volume_fractions=(1.0,),
            rheologies=(melt_rheology_for(p),),
            density_g_cm3=p.bulk_density_g_cm3,
            cp_j_per_g_k=p.cp_j_per_g_k,
            is_blend=False,
        )

    def _blend_presence(self) -> MaterialPresence:
        """Matière en aval du side feeder : mélange prorata débit volumique.

        Si pas de feeder2 (ou débit total nul) → identique à l'amont (feeder1).
        Fractions VOLUMIQUES = prorata des débits volumiques, en cohérence avec
        le `feeder_prorata` de screw_logic (qvol1 / (qvol1 + qvol2)).
        """
        p1 = self.feeder1_powder
        q1 = self.feeder1_qvol_cm3_s
        if self.feeder2_powder is None:
            return self._upstream_presence()
        p2 = self.feeder2_powder
        q2 = self.feeder2_qvol_cm3_s
        total = q1 + q2
        if total <= 0.0:
            return self._upstream_presence()
        v1, v2 = q1 / total, q2 / total
        vol_fracs = [v1, v2]
        densities = [p1.bulk_density_g_cm3, p2.bulk_density_g_cm3]
        cps = [p1.cp_j_per_g_k, p2.cp_j_per_g_k]
        # Cp massique se mélange par fraction MASSIQUE (cf. mixing_rules) :
        # on convertit d'abord les fractions volumiques en massiques.
        mass_fracs = volume_to_mass_fractions(vol_fracs, densities)
        return MaterialPresence(
            label=f"{p1.name}+{p2.name}",
            powders=(p1, p2),
            volume_fractions=(v1, v2),
            # Rhéo PAR CONSTITUANT, non pré-combinée (combinaison différée 3.3/E4).
            rheologies=(melt_rheology_for(p1), melt_rheology_for(p2)),
            density_g_cm3=mixture_density(vol_fracs, densities, basis="volume"),
            cp_j_per_g_k=mixture_specific_heat(mass_fracs, cps),
            is_blend=True,
        )

    def presence_at(self, position: int) -> MaterialPresence:
        """Matière nominale présente à `position` (amont pur vs aval mélange).

        Règle (nominale, documentée) : amont du port side feeder = feeder1 pur ;
        aval = mélange prorata débit. Le port lui-même (position == side_pos)
        est compté comme amont (la matière latérale n'est pas encore convoyée).
        """
        if position <= self.side_feeder_position:
            return self._upstream_presence()
        return self._blend_presence()
