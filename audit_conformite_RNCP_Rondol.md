# Audit de conformité STRICT — Projet Rondol vs Guide officiel thèse professionnelle RNCP 37137

**Référentiel :** `2025-2026_Guide_THESE PROFESSIONNELLE_Mastere2_DIA_PARIS.pdf` + `2025_2026_Guide_evaluations_certificatives these_Mastere2_DIA.pdf`
**Date :** 21 juin 2026 · **Candidat :** Wilfried Galtier MBEUMI · **Certification :** Chef de projet Data & IA (RNCP 37137, niveau 7)
**Méthode :** comparaison exigence par exigence, preuve fichier/section/repo, sans complaisance. Aucune donnée inventée.

## Légende des statuts
**OK** = exigence satisfaite et prouvée · **PARTIEL** = présent mais à confirmer/compléter par l'auteur · **MANQUANT** = à produire.

---

## A. Format du rendu écrit (PDF)

| Exigence guide | Statut | Preuve | Risque jury | Correction appliquée | Reste à faire |
|---|---|---|---|---|---|
| PDF ~50 pages ±10 % **hors annexes** | **OK** (lecture usuelle) | `MBEUMI_Wilfried_THESE.pdf` : corps Intro→Conclusion ≈ **48 p.**, +bibliographie = **53 p.** hors annexes ; annexes 7 p. ; front matter 10 p. | Si l'école compte le front matter : 63 p. hors annexes (> 55) | Figures compressées (largeur 11 cm) pour contenir la pagination | Si l'école compte la page de garde/sommaire : condenser (réduction proposée §plan) |
| Police TNR 12 / Arial 11 / **Calibri 12** | **OK** | `scripts/build_memoire_final.py` : `Normal.font.size = Pt(12)`, Calibri | — | Police passée de Calibri 11 → **Calibri 12** | — |
| Marges 2,5 cm | **OK** | `configure_page` : top/bottom/left/right = `Cm(2.5)` | — | Marges 2,3 → **2,5 cm** | — |
| Interligne 1,5 maximum | **OK** | `line_spacing = 1.15` (≤ 1,5) | — | — | — |
| Pagination | **OK** | Pied de page « Page N » (champ Word) sur tout le corps | — | — | — |

## B. Fichier ZIP (livrable obligatoire)

| Élément exigé | Statut | Preuve / emplacement | Reste à faire |
|---|---|---|---|
| URL publique | **PARTIEL** | `PDR_README.md` §1 (placeholder) | **Auteur** : coller l'URL Streamlit réelle |
| URL dépôt Git (facultatif) | **OK** | https://github.com/wilfried-mbeumi/rondol-process-supervision-demo | — |
| Code source complet | **OK** | `app/`, `AgentIndustrial_v1/`, `engine/`, `machine/`, `materials/`, `physics/`, `src/`, `tests/` | — |
| Dump SQL (export) | **OK** | `database/rondol_state_dump.sql` (généré, rejouable) | — |
| Fichiers de configuration | **OK** | `requirements.txt`, `runtime.txt`, `.streamlit/config.toml`, `.streamlit/secrets.toml.example`, `src/config.py` | — |
| README / PDR (install, identifiants test, connexion SQL, accès admin, multi-navigateur) | **OK** | `PDR_README.md` (10 sections, couvre tous les points) | Renseigner identifiants Supabase si connexion live demandée |
| Accès administrateur / back-office | **OK (justifié)** | `PDR_README.md` §8 : pas de back-office (mono-poste assumé) ; console Supabase = back-office données | — |
| Captures principales | **OK** | `reports/memoire_captures/` (6) + `figures_memoire/` | — |
| **ZIP assemblé** | **OK** | `MBEUMI_Wilfried_PROJET.zip` (script `scripts/build_project_zip.py`) | — |

## C. i. Page de présentation

| Exigence | Statut | Preuve |
|---|---|---|
| Nom du projet | **OK** | Page institutionnelle : « Plateforme prédictive d'aide à la décision — extrusion bivis SSB » |
| Date de début de projet | **OK** | Page institutionnelle : « Janvier 2026 » (ajouté) |
| Nom du rédacteur | **OK** | « Wilfried Galtier MBEUMI » |
| Logo Nexa Digital School | **OK** | `nexa LOGO.webp` intégré (garde + pied) |
| Logo Rondol (bonus) | **OK** | `assets/rondol_logo.png` intégré |
| Tuteur industriel M. Maël Gallas | **OK** | tableau institutionnel |
| Référent école M. Moussa NDIAYE | **OK** | tableau institutionnel |
| Année universitaire | **OK** | « 2025 – 2026 » |
| Date dépôt/soutenance | **PARTIEL** | « À confirmer (dépôt au plus tard le 17 août 2026) » | 

## D. ii. Sommaire

| Exigence | Statut | Preuve |
|---|---|---|
| Sommaire automatique | **OK** | Champ TOC Word, mis à jour à la conversion PDF (Word COM) |
| Pagination correcte | **OK** | TOC avec numéros de page renseignés |
| Cohérence titres/sous-titres | **OK** | Styles Titre 1/2/3 homogènes (Parties 1–8, sous-sections numérotées) |

## E. iii. Descriptif de l'entreprise

| Exigence | Statut | Preuve (section mémoire) |
|---|---|---|
| Storytelling | **OK** | 1.1 (fondation 2012, brevets, Prix Galien) |
| Valeurs et missions | **OK** | 1.2 |
| Activité principale | **OK** | 1.2 |
| Environnement économique et sociétal | **OK** | 1.3 |
| Environnement technologique | **OK** | 1.3 |
| Environnement de données | **OK** | 1.4 |
| Données institutionnelles (CA, effectif, statut, dirigeants) | **PARTIEL** | absentes des sources internes — section « à confirmer » assumée (non inventées) |

## F. iv. Étude de marché et analyse concurrentielle *(point critique)*

| Exigence | Statut | Preuve |
|---|---|---|
| Analyse de marché chiffrée | **OK** | 2.1 : marché SSB chiffré (MarketsandMarkets 0,26→1,77 Md$ CAGR 37,5 % ; Grand View Research 1,60→15,65 Md$ CAGR 31,8 %) |
| Sources fiables < 5 ans + citations | **OK** | sources 2025 citées (cabinets reconnus), renvois numérotés à la bibliographie [1], [35] |
| 3 concurrents min (≥2 directs + 1 indirect) | **OK** | 2.4 : Coperion, Thermo Fisher, Leistritz/ENTEK (directs) + procédés secs alternatifs (indirect) |
| Rédigé concurrent par concurrent, **pas en tableau** | **OK** | 2.4 réécrit en prose, trame identique (présentation/forces/faiblesses/comparaison) ; **le tableau a été supprimé** |
| Conclusion stratégique pour Rondol | **OK** | 2.4 « Conclusion stratégique » (points positifs/négatifs vs Rondol) |
| Notes de bas de page | **PARTIEL** | citations en **renvois numérotés à la bibliographie** (équivalent académique) plutôt que footnotes Word | 

## G. v. Problématique et définition du besoin

| Exigence | Statut | Preuve |
|---|---|---|
| Genèse de la solution | **OK** | Intro + 3.1–3.3 |
| Solution optimale issue de la recherche | **OK** | 3.7 (justification du choix techno), 5.8 (choix du modèle) |
| Description fonctionnelle (apport à l'entreprise) | **OK** | 3.4 objectifs fonctionnels, 6.4 pages |

## H. vi. Gestion de projet

| Exigence | Statut | Preuve |
|---|---|---|
| Choix de méthode (Lean/Scrum/Kanban) | **OK** | 4.1 CRISP-DM adapté (justifié) |
| Rétroplanning (livrables + échéances) | **OK** | 4.3 Tableau 4.1 |
| Outil Gantt/Pert | **OK** | figure Gantt (`fig_gantt.png`) en 4.3 |
| Tableaux de bord et indicateurs de suivi | **OK** | **4.8 ajouté** (KPIs : 685 tests, 6 pages, 798 fenêtres, F1, jalons) |
| Estimation du budget | **OK** | **4.8 ajouté** Tableau 4.4 (temps-homme + coûts open source/freemium) |
| Veille techno/sectorielle/réglementaire (tableau) | **OK** | **4.7 ajouté** Tableau 4.3 (sources, type, date, outil, canal, fréquence, impact) |
| Cartographie des risques | **OK** | 4.4 Tableau 4.2 (qualité/sécurité données, cloud, etc.) |
| Charte éthique | **OK** | **8.3 ajoutée** (charte en 7 principes) |
| Enjeux environnementaux et sociétaux | **OK** | 1.3, 8.2 |

## I. vii. Exploitation des données

| Exigence | Statut | Preuve |
|---|---|---|
| Sources de données (csv/xlsx/json ≥1) | **OK** | 12 CSV capteurs `Essais_07-13_Avril_2026/` ; `src/config.py` |
| Volumétrie | **OK** | 5.1 (50 145 enr. DIE ; 11 essais → 8 ; 798 fenêtres) |
| Typologie des données | **OK** | 5.1 (séries temporelles °C) |
| Dictionnaire de données | **OK** | Tableau 5.1 + Annexe A (96 variables) |
| Valeurs manquantes / incohérences | **OK** | 5.2 (ffill borné, dédup, segmentation seuil 120 °C) |
| Sécurité / réglementation / traçabilité | **OK** | 8.4 (RGPD : capteurs ≠ données perso) ; commits tracés |
| ML **et deep learning** supervisé, train ≥70 % | **OK** | 5.5–5.7 : RF/SVM/XGBoost + **MLP (deep learning) ajouté** ; split 70/30 par essai |
| Comparaison temps requêtes optimisées/non | **OK** | **6.6 ajouté** Tableau 6.2 (benchmark ×1000) ; `scripts/sql_benchmark.py` |
| Métrique classification (Accuracy) | **OK** | 5.7 Tableau 5.2 (Accuracy + F1 + AUC) |
| Doc technique du modèle | **OK** | 5.5–5.8 |
| Mesures d'éthique | **OK** | 8.3 charte |
| Tableau de suivi des problématiques techniques | **OK** | **6.9 ajouté** Tableau 6.1 (index, date, problème, cause, résolution, solution, commit) |

## J. viii. Application web (algorithme supervisé)

| Exigence | Statut | Preuve |
|---|---|---|
| URL d'une appli (flask/dash/shiny) local ou distant | **OK (équivalent justifié)** | Streamlit (appli web serveur Python) ; URL publique à coller (PDR §1) ; lancement local documenté |
| Front (visuel) | **OK** | `app/` Streamlit, 6 pages |
| Back intégrant l'algorithme supervisé | **OK** | `app/Supervision.py:78` charge `models/RandomForest_w60_augmented.joblib` |
| Test et déploiement (serveur local/distant) | **OK** | 685 tests ; Streamlit Cloud ; `runtime.txt` |
| RGPD / données personnelles | **OK** | 8.4 (aucune donnée perso) |
| Accessibilité (handicap) | **PARTIEL** | 8.4 : WCAG 2.1 non implémenté, chantier identifié (honnête) |

## K. ix. Conclusion + soutenance

| Exigence | Statut | Preuve |
|---|---|---|
| Bilan contraintes/risques/enjeux | **OK** | Conclusion générale + Partie 8 |
| Évolution possible | **OK** | 8.5 (4 axes) |
| Support de présentation (PREZ) | **OK** | `MBEUMI_Wilfried_PREZ.pdf` (généré) |
| Présentation de l'application finale | **OK** | parcours démo `docs/DEMO_MANAGER.md`, cas C1–C5 (Partie 7) |

## L. Indexation / RAG (clarification exigée)

**OK.** Énoncé explicite en Annexe B et §6.6 :
> « Le projet Rondol n'est pas un projet RAG et ne repose sur aucune indexation vectorielle ni base documentaire. Il s'appuie sur des données industrielles structurées (CSV), un pipeline de feature engineering, un modèle supervisé et une persistance d'état Supabase/PostgreSQL (JSONB). »

---

## Synthèse

| Bloc | OK | Partiel | Manquant |
|---|:--:|:--:|:--:|
| A. Format PDF | 5 | 0 | 0 |
| B. ZIP | 7 | 2 | 0 |
| C. Page présentation | 8 | 1 | 0 |
| D. Sommaire | 3 | 0 | 0 |
| E. Entreprise | 6 | 1 | 0 |
| F. Marché/concurrence | 5 | 1 | 0 |
| G. Problématique | 3 | 0 | 0 |
| H. Gestion projet | 9 | 0 | 0 |
| I. Données | 12 | 0 | 0 |
| J. Application | 5 | 1 | 0 |
| K. Conclusion/soutenance | 4 | 0 | 0 |
| L. RAG | 1 | 0 | 0 |

**Aucune exigence MANQUANTE.** Les « PARTIEL » relèvent tous d'informations que **seul l'auteur peut fournir** (URL publique réelle, identifiants Supabase, dates de soutenance, données institutionnelles Rondol) ou d'un choix d'équivalence académique assumé (renvois numérotés vs footnotes ; accessibilité WCAG en chantier).

## Reste à faire (par l'auteur, avant dépôt du 17 août 2026)
1. Coller l'**URL publique Streamlit** réelle dans `PDR_README.md` §1 et sur la page application.
2. Fournir (séparément, non versionné) les **identifiants Supabase** de démonstration si une connexion live est demandée.
3. Confirmer **dates de dépôt et de soutenance**.
4. Compléter (ou assumer) les **données institutionnelles Rondol** (CA, effectif, statut, dirigeants).
5. Décider du traitement des **footnotes** (laisser les renvois numérotés, conformes académiquement, ou demander une conversion en notes de bas de page Word).
6. Si l'école compte le front matter dans les « 50 pages », demander une **réduction** (condensation des sections 7.x cas et de certains paragraphes — réalisable sans perte d'exigence).
