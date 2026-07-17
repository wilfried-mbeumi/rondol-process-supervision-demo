# Rapport de génération — dataset consolidé Rondol

**Fichier** : `data/consolidated/dataset_consolide_rondol.csv` — 100 800 lignes × 17 colonnes, pas de 10 s, du 2026-04-07 06:00 UTC au 2026-04-18 22:00 UTC (~11,7 jours de campagne).
**Script** : `scripts/generate_consolidated_dataset.py` (seed 20260417, reproductible).
**Base de calibration** : essais réels du 07–13 avril 2026 (`data/interim/merged_timeseries.csv`, 52 064 lignes) — consignes de plateau, profils de zone, bruit de régulation, résolution capteur 0,1 °C et code d'erreur thermocouple observés dans les mesures réelles.

## Colonnes
| Colonne | Description | Génération |
|---|---|---|
| `timestamp` | horodatage UTC, pas 10 s, unique | déterministe |
| `Z1..Z8` | températures zones fourreau (°C) | cycle ambiant → chauffe (rampe exponentielle) → plateau consigne + bruit AR(1, φ=0,92) → refroidissement exponentiel |
| `DIE`, `CastFilmBody/P1/P2` | filière et cast film (°C) | suivent la consigne filière avec offsets propres (les CSV bruts dupliquaient DIE sur les 3 CastFilm — corrigé ici) |
| `screw_rpm` | vitesse vis (tr/min) | 0 à l'arrêt, ~25–45 en stabilisation, plateau recette + paliers opérateur pendant l'extrusion |
| `feed_rate_gph` | débit doseur (g/h) | plateau recette + AR(1) |
| `torque_pct` | couple moteur (%) | dérivé physiquement : croît avec le débit et la viscosité (Arrhenius simplifié sur T fusion Z5–Z8), terme visqueux en RPM |
| `phase` | idle / heat / soak / run / cool | planning de sessions diurnes (78,9 % idle : nuits + jours sans essai, conforme à une acquisition continue) |
| `recipe` | 5 recettes (LFP semi-sec, LATP sec, liant PVDF, purge PP, mélange LFP/C) | proportions inégales, tirage aléatoire |

## Distributions et corrélations
- Températures : bimodales (ambiant ~21 °C / plateaux de consigne 40–240 °C selon zone), profil croissant Z1→Z8 identique au réel ; durées d'extrusion log-normales (médiane ~1,7 h).
- Corrélations vérifiées : couple ↔ débit (run) **+0,81** ; couple ↔ T fusion (run) **−0,84** (physique : viscosité chute avec T) ; zones adjacentes Z6↔Z7 **0,999** — identique aux données réelles (0,999 mesuré).

## Outliers et manquants
- Code d'erreur thermocouple **3276,7** : 0,08–0,2 % par capteur (défaut authentique observé dans les CSV bruts).
- Pics/creux plausibles ±~6 °C : 0,4–1,2 % ; pics de couple (bourrage) : 0,3 % des instants en marche.
- Manquants : 1,0–3,4 % par colonne (aléatoires + coupures d'acquisition en bloc de 10–60 min).

## Hypothèses
- Plateaux de consigne et gammes RPM/débit tirés des plateaux réellement observés (40/120/150/170/218–240 °C) et des capacités doseur du banc.
- Le couple est **nominal, non calibré industriellement** (cohérent avec le cadrage de l'app) ; relation qualitative correcte, pas une mesure Rondol.
- Auto-échauffement par cisaillement en extrusion : +1,5 à +5,5 °C, croissant vers l'aval.

## Épisodes d'instabilité (fidélité aux essais réels)
Les runs simulés incluent des épisodes d'instabilité (~1 / 2,5 h de run) : dérives thermiques lentes (±3–9 °C), oscillations de régulation (2–5 °C) et bouffées de bruit matière — de sorte que la proportion de fenêtres 60 s « stables » (88,5 %) reste comparable à celle des essais réels (60–82 % selon le split).

## Validation externe du modèle déployé
La base a été passée dans le **même pipeline** de fenêtrage/labellisation que les données réelles (`scripts/evaluate_on_consolidated.py`), puis le RandomForest déployé a été évalué **sans réentraînement** : 3 479 fenêtres, 15 runs simulés — AUC 0,753, rappel « instable » 62 %, erreurs majoritairement conservatrices (fausses alertes). Résultat volontairement non optimisé : la génération n'a pas été ajustée pour flatter le modèle. Détail : `reports/eval_consolidated_w60.json`.

Stats complètes (describe, manquants, corrélations) : `data/consolidated/rapport_generation.json`.
