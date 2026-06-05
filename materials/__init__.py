"""materials — descripteurs matière et lois constitutives PURES.

Phase 1 : `powder` (poudres/bulk), `rheology` (viscosité), `mixing_rules`
(mélanges multi-constituants). Dépendance unique : `physics.conversions`.
Aucun état procédé, aucun couplage à NodeState (différé).

Les presets matière sont NOMINAUX et destinés à être recalibrés sur les essais
réels (cf. references/manager_requirements/, Essais_07-13_Avril_2026/).
"""
