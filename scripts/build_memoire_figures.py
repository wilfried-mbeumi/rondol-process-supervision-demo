# -*- coding: utf-8 -*-
"""
Génère toutes les figures techniques du mémoire Rondol (matplotlib).

Refonte esthétique 2026-08-17 :
- Palette plus subtile : bleu pétrole atténué, aplats désaturés (surface-2 style),
  neutres à teinte fine plutôt que gris pur.
- Typographie hiérarchisée : Segoe UI (Windows natif) → Calibri → Arial en
  fallback ; eyebrow small-caps, titre semi-bold, sous-titre italic gris,
  captions right-align, aucune répétition de gras.
- Espacement généreux : plus de blanc entre les boîtes, marges élargies,
  divider horizontal fin sous le titre pour l'ancrage visuel.
- Éléments d'accent : border-left coloré + fond ultra-clair (au lieu de
  bordure pleine + fond saturé), ombre discrète en option.

Palette / helpers restent compatibles avec l'API existante — toutes les
fonctions fig_*() héritent automatiquement du nouveau look.
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from matplotlib.lines import Line2D
import matplotlib.font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "memoire_figures"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Palette — refonte 2026-08-17
# Bleu pétrole plus profond, teintes claires ULTRA légères (moins de
# saturation → aspect plus premium, moins « PowerPoint »).
# ------------------------------------------------------------------
BLUE   = "#1E4F73"   # bleu pétrole (accent principal)
BLUE2  = "#3A78A4"   # bleu médium
BLUELT = "#EEF3F7"   # bleu ultra-clair (fond subtil)
GREEN  = "#2A6E48"   # vert Rondol (accent secondaire)
GREENLT= "#E4EFE8"   # vert ultra-clair
GREY   = "#4E5561"   # neutre foncé (labels)
GREYLT = "#F3F4F6"   # neutre ultra-clair
GREYMD = "#8891A0"   # neutre moyen (captions)
RED    = "#9B2C1F"   # rouge sobre (alerte)
REDLT  = "#F2E1DE"   # rouge ultra-clair
AMBER  = "#8A6410"   # ambre sobre (warning)
AMBERLT= "#F5EED8"   # ambre ultra-clair
INK    = "#1A1E24"   # texte principal (quasi-noir, teinte froide)
RULE   = "#D8DDE3"   # ligne fine (dividers)
WHITE  = "#FFFFFF"

# ------------------------------------------------------------------
# Typographie — famille pro avec fallback (Windows natif prioritaire)
# ------------------------------------------------------------------
_installed = {f.name for f in fm.fontManager.ttflist}
FONT_STACK = next((n for n in ["Segoe UI", "Calibri", "Arial", "DejaVu Sans"]
                   if n in _installed), "DejaVu Sans")
FONT_SERIF = next((n for n in ["Georgia", "Palatino Linotype", "DejaVu Serif"]
                   if n in _installed), "DejaVu Serif")

plt.rcParams.update({
    "font.family": FONT_STACK,
    "font.size": 10.5,
    "axes.edgecolor": RULE,
    "axes.labelcolor": GREY,
    "xtick.color": GREY,
    "ytick.color": GREY,
    "figure.dpi": 220,
    "savefig.dpi": 220,
    "patch.linewidth": 0.9,
})

DPI = 220


def _ax(w=11, h=6.2):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=BLUELT, ec=BLUE, tc=INK, fs=10.5, bold=False,
        rad=0.025, lw=0.9, ha="center", title=None, title_fc=None):
    """Boîte à border-left coloré + fond ultra-clair (style plus premium).
    Compatible API existante : fc/ec/text/title conservés.
    """
    # Fond principal (léger, sans bordure épaisse)
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0.3,rounding_size={rad*100}",
                       linewidth=lw, edgecolor=RULE, facecolor=fc,
                       mutation_aspect=1)
    ax.add_patch(p)
    # Rail d'accent à gauche (2.2 unités de large)
    rail = Rectangle((x, y + 0.4), 1.2, h - 0.8, facecolor=ec, edgecolor="none")
    ax.add_patch(rail)
    if title:
        ax.text(x + w / 2, y + h - 4.2, title, ha="center", va="center",
                fontsize=fs - 0.5, fontweight="semibold", color=title_fc or ec)
        ax.text(x + w / 2, y + (h - 8) / 2, text, ha="center", va="center",
                fontsize=fs - 1.5, color=tc, wrap=True)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha=ha,
                va="center", fontsize=fs, fontweight="semibold" if bold else "normal",
                color=tc, wrap=True)
    return p


def arrow(ax, x1, y1, x2, y2, color=None, lw=1.4, style="-|>", ls="-"):
    """Flèche épurée, plus fine par défaut."""
    if color is None:
        color = GREYMD
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                        linewidth=lw, color=color, linestyle=ls,
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def title(ax, t, sub=None):
    """Titre semi-bold + divider fin + sous-titre italic — hiérarchie propre."""
    ax.text(50, 97.5, t, ha="center", va="top",
            fontsize=13, fontweight="semibold", color=INK)
    # Divider fin horizontal centré (largeur ~14 unités)
    ax.add_line(Line2D([43, 57], [93.6, 93.6], color=RULE, lw=0.9,
                       solid_capstyle="round"))
    if sub:
        ax.text(50, 91, sub, ha="center", va="top",
                fontsize=9.5, color=GREYMD, style="italic")


def save(fig, name):
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight",
                facecolor=WHITE, pad_inches=0.25)
    plt.close(fig)
    print(f"[OK] {name}")


# --------------------------------------------------------------------------- #
# 1. Architecture en couches
# --------------------------------------------------------------------------- #
def fig_architecture():
    fig, ax = _ax(11, 7)
    title(ax, "Architecture logicielle en couches de la plateforme Rondol",
          "Dépendances strictement descendantes — chaque couche ignore les couches supérieures")
    layers = [
        ("Couche UI — app/ (6 pages Streamlit)", "Supervision · Profile · Settings · Run Analysis · History · Process Engine", BLUELT, BLUE),
        ("Couche persistance — app/persistence.py", "Supabase / PostgreSQL  →  store fichier externe  →  JSON local  ·  auto-réparation", GREENLT, GREEN),
        ("Couche 2 — engine/ (enveloppement)", "NodeState · viscosité η(γ̇,T) · couple E4a · agrégats zone/machine  (ENVELOPPE, ne recalcule pas)", BLUELT, BLUE2),
        ("Couche 1 — packages purs", "machine/ (éléments, ports, filières)   ·   materials/ (poudre, rhéologie)   ·   physics/ (conversions)", GREYLT, GREY),
        ("Couche 0 — backbone  app/screw_logic.py", "« Network 7 » · 81 positions · source unique : remplissage / résidence / volumes", "#1F4E79", "#13314F"),
    ]
    n = len(layers)
    x, w = 8, 84
    h = 12
    gap = 3.2
    y0 = 8
    for i, (t, sub, fc, ec) in enumerate(layers):
        y = y0 + (n - 1 - i) * (h + gap)
        tc = WHITE if i == n - 1 else INK
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=2",
                           linewidth=1.8, edgecolor=ec, facecolor=fc)
        ax.add_patch(b)
        ax.text(x + 2.5, y + h - 3.4, t, ha="left", va="center", fontsize=11.5,
                fontweight="bold", color=WHITE if i == n - 1 else ec)
        ax.text(x + 2.5, y + 3.6, sub, ha="left", va="center", fontsize=9.2,
                color=tc)
    # Flèche dépendances
    arrow(ax, 96, y0 + (n - 1) * (h + gap) + h - 2, 96, y0 + 2, color=RED, lw=2.2)
    ax.text(98.5, 50, "sens des dépendances", rotation=90, ha="center", va="center",
            fontsize=9, color=RED, style="italic")
    # Agent transversal
    ax.text(4.5, 50, "Agent  AgentIndustrial_v1/  (transversal : alertes + recommandations)",
            rotation=90, ha="center", va="center", fontsize=9, color=GREEN, style="italic")
    save(fig, "fig_architecture.png")


# --------------------------------------------------------------------------- #
# 2. Pipeline de données
# --------------------------------------------------------------------------- #
def fig_data_pipeline():
    fig, ax = _ax(12, 6.4)
    title(ax, "Flux de données : du capteur brut à la recommandation",
          "Campagne d'essais Rondol 7–13 avril 2026 · 12 capteurs de température")
    # Deux rangées de quatre : sur une seule rangée de sept, « Recommandations »
    # et « Timestamp/Name/Value » débordaient de leur cadre et se chevauchaient.
    # 87 variables = 12 capteurs x 7 statistiques + 3 gradients croisés ; c'est
    # bien le nombre attendu par le modèle déployé (n_features_in_ = 87).
    steps = [
        ("CSV capteurs", "12 voies\nTimestamp · Name · Value", BLUELT, BLUE),
        ("Nettoyage", "déduplication · resample 10 s\nforward-fill ≤ 60 s", BLUELT, BLUE),
        ("Fenêtrage", "30 / 60 / 120 s\nrecouvrement 50 %", BLUELT, BLUE),
        ("Variables", "87 variables\n12 × 7 stats + 3 croisées", GREENLT, GREEN),
        ("Modèle ML", "RandomForest\n(augmenté, retenu)", GREENLT, GREEN),
        ("Agent à règles", "alertes + actions\nexplicables", BLUELT, BLUE),
        ("Interface", "Streamlit\npage Supervision", BLUELT, BLUE),
    ]
    COLS, MARGE, GAP = 4, 4, 4
    w = (100 - 2 * MARGE - (COLS - 1) * GAP) / COLS      # = 20 : titres au large
    h = 21
    lignes_y = (52, 18)
    for i, (t, sub, fc, ec) in enumerate(steps):
        col, row = i % COLS, i // COLS
        xi, yi = MARGE + col * (w + GAP), lignes_y[row]
        ax.add_patch(FancyBboxPatch((xi, yi), w, h,
                                    boxstyle="round,pad=0.3,rounding_size=1.6",
                                    linewidth=1.6, edgecolor=ec, facecolor=fc))
        ax.text(xi + w / 2, yi + h - 5, t, ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=ec)
        ax.text(xi + w / 2, yi + (h - 9) / 2, sub, ha="center", va="center",
                fontsize=8.6, color=INK, linespacing=1.5)
        if col < COLS - 1 and i < len(steps) - 1:
            arrow(ax, xi + w, yi + h / 2, xi + w + GAP, yi + h / 2, color=GREY, lw=1.8)
    # Liaison rangée 1 -> rangée 2 : coude à angles droits dans l'entre-deux,
    # plutôt qu'une diagonale qui barrerait toute la figure.
    x_fin = MARGE + (COLS - 1) * (w + GAP) + w / 2
    x_deb = MARGE + w / 2
    y_mid = lignes_y[1] + h + (lignes_y[0] - lignes_y[1] - h) / 2
    ax.plot([x_fin, x_fin], [lignes_y[0], y_mid], color=GREY, lw=1.8,
            solid_capstyle="round", zorder=1)
    ax.plot([x_fin, x_deb], [y_mid, y_mid], color=GREY, lw=1.8,
            solid_capstyle="round", zorder=1)
    arrow(ax, x_deb, y_mid, x_deb, lignes_y[1] + h, color=GREY, lw=1.8)
    ax.text(50, 8, "Cible décalée d'une fenêtre (prévision de l'état futur) · séparation par essai (anti-fuite)",
            ha="center", va="center", fontsize=9.2, color=GREY, style="italic")
    save(fig, "fig_data_pipeline.png")


# --------------------------------------------------------------------------- #
# 3. Persistance Supabase
# --------------------------------------------------------------------------- #
def fig_persistence():
    fig, ax = _ax(11, 6.4)
    title(ax, "Persistance durable et auto-réparation de l'état validé",
          "save_applied_state / migrate_and_restore · disque Streamlit Cloud éphémère")
    box(ax, 6, 70, 26, 16, "Opérateur\nvalide (« Enregistrer »)", fc=BLUELT, ec=BLUE, fs=10.5, bold=True)
    box(ax, 38, 70, 26, 16, "Snapshot JSON\napplied_state", fc=GREENLT, ec=GREEN, fs=10.5, bold=True)
    arrow(ax, 32, 78, 38, 78, color=GREY)
    # 3 backends
    backs = [
        ("1 · Supabase / PostgreSQL", "table rondol_state(key, payload JSONB)\nupsert merge-duplicates · timeout 4 s", GREEN),
        ("2 · Store fichier externe", "hors disque éphémère", BLUE2),
        ("3 · JSON local", "repli développement", GREY),
    ]
    for i, (t, sub, ec) in enumerate(backs):
        y = 47 - i * 13.5
        b = FancyBboxPatch((38, y), 50, 11, boxstyle="round,pad=0.3,rounding_size=1.4",
                           linewidth=1.6, edgecolor=ec, facecolor=WHITE)
        ax.add_patch(b)
        ax.text(40, y + 7.6, t, ha="left", va="center", fontsize=10, fontweight="bold", color=ec)
        ax.text(40, y + 3.0, sub, ha="left", va="center", fontsize=8.4, color=INK)
        arrow(ax, 50, 70, 50, y + 11, color=ec, lw=1.4, ls="--" if i else "-")
    # Auto-réparation
    b = FancyBboxPatch((6, 8), 26, 50, boxstyle="round,pad=0.3,rounding_size=1.6",
                       linewidth=1.8, edgecolor=AMBER, facecolor=AMBERLT)
    ax.add_patch(b)
    ax.text(19, 53, "Auto-réparation\nrepair_snapshot_dict", ha="center", va="center",
            fontsize=10, fontweight="bold", color=AMBER)
    ax.text(19, 33, "• banc feeders → 5\n• densité < 0,01\n  → 0,55 g/cm³\n• zones dégénérées\n  → cibles par défaut\n\nidempotente, en tête\nde page (avant widgets)",
            ha="center", va="center", fontsize=8.4, color=INK)
    arrow(ax, 38, 33, 32, 33, color=AMBER, lw=1.6)
    ax.text(35, 62, "Au redémarrage : charge · valide · répare · réécrit · hydrate la session",
            ha="center", va="center", fontsize=8.6, color=GREY, style="italic")
    save(fig, "fig_persistence.png")


# --------------------------------------------------------------------------- #
# 4. Logique du moteur procédé
# --------------------------------------------------------------------------- #
def fig_engine_logic():
    fig, ax = _ax(12, 4.8)
    title(ax, "Logique du moteur procédé : de la géométrie aux alertes",
          "Network 7 appelé exactement une fois · grandeurs consommées, jamais recalculées")
    steps = [
        ("Profil de vis", "81 positions\n40 éléments utiles", BLUE),
        ("Zones", "8 zones fourreau\n+ filière (DIE)", BLUE),
        ("Remplissage", "fill_factor\npar position", GREEN),
        ("Résidence", "temps de séjour\n∝ 100 / rpm", GREEN),
        ("Volumes", "occupé / libre\n76,18 cm³ réf.", GREEN),
        ("Alertes", "score 0–100\n+ recommandations", RED),
    ]
    n = len(steps)
    w = 13.5
    gap = (100 - 6 - n * w) / (n - 1)
    y, h, x = 40, 24, 3
    for i, (t, sub, ec) in enumerate(steps):
        xi = x + i * (w + gap)
        fc = REDLT if i == n - 1 else (GREENLT if 2 <= i <= 4 else BLUELT)
        b = FancyBboxPatch((xi, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.6",
                           linewidth=1.7, edgecolor=ec, facecolor=fc)
        ax.add_patch(b)
        ax.text(xi + w / 2, y + h - 4.5, t, ha="center", va="center", fontsize=10.5,
                fontweight="bold", color=ec)
        ax.text(xi + w / 2, y + (h - 9) / 2 + 1, sub, ha="center", va="center",
                fontsize=8.6, color=INK)
        if i < n - 1:
            arrow(ax, xi + w, y + h / 2, xi + w + gap, y + h / 2, color=GREY, lw=1.8)
    save(fig, "fig_engine_logic.png")


# --------------------------------------------------------------------------- #
# 5. Deux niveaux d'IA
# --------------------------------------------------------------------------- #
def fig_two_level_ai():
    fig, ax = _ax(11, 6.2)
    title(ax, "Deux niveaux d'intelligence artificielle, délibérément distingués",
          "Le meilleur modèle expérimental n'est pas nécessairement celui qui est intégré")
    # Colonne gauche
    b = FancyBboxPatch((5, 14), 42, 70, boxstyle="round,pad=0.3,rounding_size=2",
                       linewidth=1.8, edgecolor=BLUE, facecolor=BLUELT)
    ax.add_patch(b)
    ax.text(26, 78, "Niveau 1 — Référence hors-ligne", ha="center", fontsize=11.5,
            fontweight="bold", color=BLUE)
    ax.text(26, 71, "Random Forest (fenêtre 60 s)", ha="center", fontsize=10.5,
            fontweight="bold", color=INK)
    ax.text(26, 44,
            "• Exactitude 0,950 · F1-macro 0,917\n• AUC-ROC 0,947\n• F1-macro réaliste 0,77 ± 0,11\n  (validation stricte LOGO/GSS)\n\n→ établit le POTENTIEL prédictif\n   de l'approche",
            ha="center", va="center", fontsize=9.4, color=INK)
    # Colonne droite
    b = FancyBboxPatch((53, 14), 42, 70, boxstyle="round,pad=0.3,rounding_size=2",
                       linewidth=1.8, edgecolor=GREEN, facecolor=GREENLT)
    ax.add_patch(b)
    ax.text(74, 78, "Niveau 2 — Intégré au prototype", ha="center", fontsize=11.5,
            fontweight="bold", color=GREEN)
    ax.text(74, 71, "SVM (RBF) + règles expertes", ha="center", fontsize=10.5,
            fontweight="bold", color=INK)
    ax.text(74, 44,
            "• Précision élevée classe « instable »\n  (moins de fausses alertes)\n• Explicabilité par les règles\n• Score + justification pour l'opérateur\n\n→ retenu pour l'AIDE À LA DÉCISION\n   en démonstration",
            ha="center", va="center", fontsize=9.4, color=INK)
    arrow(ax, 47, 49, 53, 49, color=GREY, lw=2.0)
    ax.text(50, 8, "Random Forest · XGBoost · SVM comparés sur 8 essais réels (jeu fenêtre 60 s)",
            ha="center", fontsize=9, color=GREY, style="italic")
    save(fig, "fig_two_level_ai.png")


# --------------------------------------------------------------------------- #
# 6. Comparatif des piles technologiques
# --------------------------------------------------------------------------- #
def fig_stack_comparison():
    crit = ["Rapidité de prototypage", "Démonstration client", "Simplicité de déploiement",
            "Persistance des données", "Contrôle fin de l'UX", "Livrable SQL"]
    flask = ["Modérée (front/back séparés)", "À construire", "Serveur à administrer",
             "SQLite/PostgreSQL local", "Élevé (sur mesure)", "Dump SQL direct"]
    stl = ["Élevée (Python unique)", "HMI crédible immédiate", "GitHub + Streamlit Cloud",
           "Supabase/PostgreSQL géré", "Plus grossier (assumé)", "Dump SQL (Postgres)"]
    verdict = ["+", "+", "+", "+", "–", "="]
    fig, ax = plt.subplots(figsize=(11, 5.0))
    ax.axis("off")
    ax.set_title("Comparatif des piles technologiques : Flask/Dash vs Streamlit/Supabase",
                 fontsize=13.5, fontweight="bold", color=BLUE, pad=14)
    rows = len(crit) + 1
    cols = [0.0, 0.30, 0.63, 0.96]
    rowh = 1.0 / rows
    headers = ["Critère", "Flask / Dash + PostgreSQL", "Streamlit / Supabase (retenu)"]
    for j, htext in enumerate(headers):
        ax.add_patch(Rectangle((cols[j], 1 - rowh), cols[j + 1] - cols[j], rowh,
                               transform=ax.transAxes, facecolor=BLUE, edgecolor=WHITE, lw=1.5))
        ax.text((cols[j] + cols[j + 1]) / 2, 1 - rowh / 2, htext, transform=ax.transAxes,
                ha="center", va="center", color=WHITE, fontsize=9.6, fontweight="bold")
    for i in range(len(crit)):
        y = 1 - (i + 2) * rowh
        bg = GREYLT if i % 2 else WHITE
        for j in range(3):
            ax.add_patch(Rectangle((cols[j], y), cols[j + 1] - cols[j], rowh,
                                   transform=ax.transAxes, facecolor=bg, edgecolor="#D9D9D9", lw=1))
        ax.text(cols[0] + 0.01, y + rowh / 2, crit[i], transform=ax.transAxes,
                ha="left", va="center", fontsize=9, fontweight="bold", color=INK)
        ax.text((cols[1] + cols[2]) / 2, y + rowh / 2, flask[i], transform=ax.transAxes,
                ha="center", va="center", fontsize=8.6, color=GREY)
        col = GREEN if verdict[i] == "+" else (RED if verdict[i] == "–" else AMBER)
        ax.text((cols[2] + cols[3]) / 2, y + rowh / 2, stl[i], transform=ax.transAxes,
                ha="center", va="center", fontsize=8.6, color=col, fontweight="bold")
    save(fig, "fig_stack_comparison.png")


# --------------------------------------------------------------------------- #
# 7. SWOT
# --------------------------------------------------------------------------- #
def fig_swot():
    fig, ax = _ax(11, 6.6)
    ax.text(50, 97, "Analyse SWOT de Rondol Industrie au regard du projet", ha="center",
            va="top", fontsize=13.5, fontweight="bold", color=BLUE)
    quads = [
        (6, 50, "FORCES (internes)", GREEN, GREENLT,
         "• Précision & miniaturisation (10,5 mm)\n• Brevets configuration verticale (EU/US)\n• Héritage pharma (Prix Galien 2020, 2023)\n• Partenariats scientifiques (IJL, Chicago…)"),
        (52, 50, "FAIBLESSES (internes)", AMBER, AMBERLT,
         "• Ressources limitées vs concurrents\n• Données d'essais peu nombreuses (8)\n• Outil non calibré industriellement\n• Développement mono-acteur"),
        (6, 8, "OPPORTUNITÉS (externes)", BLUE, BLUELT,
         "• Marché SSB en forte croissance\n• Pression anti-solvant (PFAS / ECHA)\n• Différenciation par l'IA explicable\n• Écosystème académique (IJL / ARTEM)"),
        (52, 8, "MENACES (externes)", RED, REDLT,
         "• Concurrents mieux dotés (Coperion…)\n• Rareté des données d'essais\n• Marché SSB encore pré-industriel\n• Risque de perception (prototype non calibré)"),
    ]
    for x, y, t, ec, fc, body in quads:
        b = FancyBboxPatch((x, y), 42, 38, boxstyle="round,pad=0.3,rounding_size=2",
                           linewidth=1.9, edgecolor=ec, facecolor=fc)
        ax.add_patch(b)
        ax.text(x + 2.5, y + 33, t, ha="left", va="center", fontsize=11, fontweight="bold", color=ec)
        ax.text(x + 2.5, y + 15, body, ha="left", va="center", fontsize=9.0, color=INK)
    save(fig, "fig_swot.png")


# --------------------------------------------------------------------------- #
# 8. CRISP-DM
# --------------------------------------------------------------------------- #
def fig_crispdm():
    import numpy as np
    fig, ax = _ax(8.6, 7.4)
    title(ax, "Démarche CRISP-DM adaptée au projet",
          "Six phases · itérations entre préparation des données et modélisation")
    phases = ["Compréhension\nmétier", "Compréhension\ndes données", "Préparation\ndes données",
              "Modélisation", "Évaluation", "Déploiement"]
    cx, cy, r = 50, 46, 30
    angles = np.linspace(90, 90 - 360, len(phases) + 1)[:-1]
    pts = []
    for a in angles:
        rad = a * 3.14159 / 180
        x = cx + r * np.cos(rad)
        y = cy + r * np.sin(rad)
        pts.append((x, y))
    for i, (x, y) in enumerate(pts):
        ec = GREEN if i in (2, 3) else BLUE
        fc = GREENLT if i in (2, 3) else BLUELT
        c = FancyBboxPatch((x - 11, y - 6.5), 22, 13, boxstyle="round,pad=0.3,rounding_size=2",
                           linewidth=1.7, edgecolor=ec, facecolor=fc)
        ax.add_patch(c)
        ax.text(x, y, phases[i], ha="center", va="center", fontsize=9.2,
                fontweight="bold", color=ec)
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        arrow(ax, x1 + (x2 - x1) * 0.22, y1 + (y2 - y1) * 0.22,
              x1 + (x2 - x1) * 0.78, y1 + (y2 - y1) * 0.78, color=GREY, lw=1.6)
    save(fig, "fig_crispdm.png")


# --------------------------------------------------------------------------- #
# 9. Gantt (chronologie relative + jalons certains)
# --------------------------------------------------------------------------- #
def fig_gantt():
    fig, ax = plt.subplots(figsize=(11, 5.6))
    phases = [
        ("Cadrage & problématique", 0, 2),
        ("État de l'art scientifique", 1, 3),
        ("Campagne d'essais (données)", 3, 1),
        ("Préparation des données", 3.6, 1.6),
        ("Moteur procédé (screw_logic + engine)", 4, 3),
        ("Modélisation ML (RF / XGB / SVM)", 5, 2.4),
        ("Interface Streamlit (6 pages)", 6, 3),
        ("Persistance Supabase", 7.5, 1.8),
        ("Tests & stabilisation (725)", 7.8, 1.7),
        ("Démonstration client", 9.5, 0.5),
        ("Rédaction & dépôt du mémoire", 8.5, 2),
    ]
    colors = [BLUE2] * 2 + [GREEN] + [GREEN] + [BLUE] * 1 + [GREEN] + [BLUE] * 3 + [GREEN]
    for i, (name, start, dur) in enumerate(phases):
        ax.barh(len(phases) - i, dur, left=start, height=0.55,
                color=colors[i % len(colors)], edgecolor=WHITE)
        ax.text(start, len(phases) - i + 0.5, "  " + name, va="center", ha="left",
                fontsize=8.8, color=INK)
    # Jalons certains
    ax.axvline(3.5, color=RED, lw=1.4, ls="--")
    ax.text(3.5, 0.2, "Campagne 7–13 avr. 2026", color=RED, fontsize=8, ha="center")
    ax.axvline(9.7, color=RED, lw=1.4, ls="--")
    ax.text(9.7, 0.2, "Démo client 16 juin 2026", color=RED, fontsize=8, ha="center")
    ax.set_xlim(0, 11)
    ax.set_ylim(0, len(phases) + 1.3)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("Rétroplanning indicatif du projet (chronologie relative)",
                 fontsize=13, fontweight="bold", color=BLUE, pad=12)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    save(fig, "fig_gantt.png")


# --------------------------------------------------------------------------- #
# 10. Familles de tests
# --------------------------------------------------------------------------- #
def fig_tests():
    # Grille 3 x 2 : sur une seule rangée de six, les intitulés les plus longs
    # (« Internationalisation », « Redémarrage E2E ») débordaient de leur cadre.
    fig, ax = _ax(11, 6.0)
    title(ax, "Stratégie de tests : 725 tests automatisés sur 76 fichiers",
          "Tous passants · exécution ≈ 2 min · chaque incident de production figé en test")
    fams = [
        ("Unitaires purs", "logique métier\n& moteur procédé", BLUE),
        ("Interface Streamlit", "≈ 30 tests AppTest\n(widgets réels)", BLUE2),
        ("Persistance", "survie au\nredémarrage simulé", GREEN),
        ("Non-régression", "chaque bug de\nproduction figé", GREY),
        ("Internationalisation", "> 70 chaînes FR\ninterdites en anglais", AMBER),
        ("Accessibilité", "nom accessible,\ncontrastes WCAG", RED),
    ]
    COLS, MARGE, GAP = 3, 5, 5
    w = (100 - 2 * MARGE - (COLS - 1) * GAP) / COLS      # ≈ 26,7 : place pour les titres
    h, y_haut, y_bas = 29, 47, 10
    for i, (t, sub, ec) in enumerate(fams):
        col, row = i % COLS, i // COLS
        xi = MARGE + col * (w + GAP)
        yi = y_haut if row == 0 else y_bas
        ax.add_patch(FancyBboxPatch((xi, yi), w, h,
                                    boxstyle="round,pad=0.3,rounding_size=1.6",
                                    linewidth=1.7, edgecolor=ec, facecolor=WHITE))
        ax.text(xi + w / 2, yi + h - 7, t, ha="center", va="center",
                fontsize=11, fontweight="bold", color=ec)
        ax.text(xi + w / 2, yi + h / 2 - 4, sub, ha="center", va="center",
                fontsize=9.2, color=INK, linespacing=1.5)
    save(fig, "fig_tests.png")


# --------------------------------------------------------------------------- #
# 11. Comparaison des protocoles de validation
# --------------------------------------------------------------------------- #
def fig_validation():
    import numpy as np
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    protos = ["Split aléatoire\n(optimiste)", "GroupShuffleSplit\n(réaliste)", "Leave-One-Group-Out\n(réaliste)"]
    f1 = [0.92, 0.77, 0.79]
    f1err = [0.0, 0.11, 0.12]
    auc = [0.98, 0.92, 0.90]
    aucerr = [0.0, 0.05, 0.08]
    x = np.arange(len(protos))
    w = 0.36
    b1 = ax.bar(x - w / 2, f1, w, yerr=f1err, capsize=5, label="F1-macro",
                color=BLUE2, edgecolor=BLUE)
    b2 = ax.bar(x + w / 2, auc, w, yerr=aucerr, capsize=5, label="AUC-ROC",
                color=GREEN, edgecolor="#125C2C")
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012,
                f"{b.get_height():.2f}", ha="center", fontsize=8.6, color=INK)
    ax.axvspan(-0.5, 0.5, color=REDLT, alpha=0.5, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels(protos, fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.set_title("Performances selon le protocole de validation (modèle de référence, fenêtre 60 s)",
                 fontsize=12.5, fontweight="bold", color=BLUE, pad=12)
    ax.legend(loc="lower left", fontsize=9)
    ax.text(0, 0.05, "contaminé par\nl'autocorrélation", ha="center", fontsize=7.8,
            color=RED, style="italic")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig_validation.png")


# --------------------------------------------------------------------------- #
# 12. Statut des équations du moteur
# --------------------------------------------------------------------------- #
def fig_equations():
    fig, ax = _ax(11, 4.6)
    title(ax, "Statut des équations du moteur procédé",
          "Honnêteté scientifique : les équations non validées renvoient None, sans valeur trompeuse")
    eqs = [
        ("E4 — Couple local", "M = η·γ̇²·V_filled / (2πN)", "Implémentée", GREEN, GREENLT),
        ("E5 — SME local (par nœud)", "énergie mécanique spécifique", "Différée → None", GREY, GREYLT),
        ("E6 — Température réelle avancée", "T_real,i par nœud", "Différée → None", GREY, GREYLT),
        ("E7 — Pression filière", "Hagen-Poiseuille non-newtonien", "Différée → None", GREY, GREYLT),
    ]
    y, h = 60, 13
    for i, (t, sub, st, ec, fc) in enumerate(eqs):
        yi = y - i * (h + 2.5)
        b = FancyBboxPatch((6, yi), 70, h, boxstyle="round,pad=0.3,rounding_size=1.4",
                           linewidth=1.6, edgecolor=ec, facecolor=fc)
        ax.add_patch(b)
        ax.text(9, yi + h - 4, t, ha="left", va="center", fontsize=10, fontweight="bold", color=ec)
        ax.text(9, yi + 4, sub, ha="left", va="center", fontsize=8.6, color=INK, style="italic")
        bb = FancyBboxPatch((80, yi + 2), 16, h - 4, boxstyle="round,pad=0.2,rounding_size=1.2",
                            linewidth=1.4, edgecolor=ec, facecolor=WHITE)
        ax.add_patch(bb)
        ax.text(88, yi + h / 2, st, ha="center", va="center", fontsize=8.6,
                fontweight="bold", color=ec)
    save(fig, "fig_equations.png")


# --------------------------------------------------------------------------- #
# 13. Feuille de route
# --------------------------------------------------------------------------- #
def fig_roadmap():
    fig, ax = _ax(11, 5.4)
    title(ax, "Feuille de route : quatre axes d'évolution",
          "Chaque limite identifiée appelle une évolution ciblée")
    # Intitulés raccourcis : « 1 · Données & calibration » débordait de son
    # bandeau. Le jalon « Dump SQL certification » a disparu de l'axe 4 : le
    # dump est livré (cf. Annexe B), ce n'est plus une perspective.
    axes = [
        ("1 · Données", "• Multiplier les essais\n• Données synthétiques\n• Calibration industrielle", BLUE),
        ("2 · Équations & ML", "• Coder E5 / E6 / E7\n• Interprétabilité SHAP\n• Pression filière", GREEN),
        ("3 · Industrialisation", "• Chaîne CI/CD\n• Couverture mesurée\n• Plan de tests formel", BLUE2),
        ("4 · Périmètre & V2", "• Multi-utilisateur\n• Capteurs temps réel\n  (couple, pression)\n• Calibration V2", AMBER),
    ]
    n = len(axes)
    w = 21
    gap = (100 - 6 - n * w) / (n - 1)
    y, h, x = 22, 46, 3
    for i, (t, sub, ec) in enumerate(axes):
        xi = x + i * (w + gap)
        b = FancyBboxPatch((xi, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.8",
                           linewidth=1.8, edgecolor=ec, facecolor=WHITE)
        ax.add_patch(b)
        ax.add_patch(FancyBboxPatch((xi, y + h - 9), w, 9,
                     boxstyle="round,pad=0.3,rounding_size=1.8", linewidth=0, facecolor=ec))
        ax.text(xi + w / 2, y + h - 4.5, t, ha="center", va="center", fontsize=9.6,
                fontweight="bold", color=WHITE)
        ax.text(xi + 2.5, y + (h - 9) / 2, sub, ha="left", va="center", fontsize=8.6, color=INK)
        if i < n - 1:
            arrow(ax, xi + w, y + h / 2, xi + w + gap, y + h / 2, color=GREY, lw=1.6)
    save(fig, "fig_roadmap.png")


# --------------------------------------------------------------------------- #
# 14. Schéma ER rondol_state
# --------------------------------------------------------------------------- #
def fig_er_schema():
    fig, ax = _ax(10.5, 5.2)
    title(ax, "Schéma de persistance : table rondol_state et document JSONB",
          "Supabase / PostgreSQL · compatible avec le dump SQL exigé par la certification")
    # Table
    b = FancyBboxPatch((8, 30), 34, 42, boxstyle="round,pad=0.3,rounding_size=1.6",
                       linewidth=1.8, edgecolor=BLUE, facecolor=WHITE)
    ax.add_patch(b)
    ax.add_patch(Rectangle((8, 64), 34, 8, facecolor=BLUE, edgecolor=BLUE))
    ax.text(25, 68, "rondol_state", ha="center", va="center", color=WHITE,
            fontsize=11, fontweight="bold")
    ax.text(11, 56, "key      TEXT  PRIMARY KEY", ha="left", fontsize=9.4, color=INK, family="monospace")
    ax.text(11, 47, "payload  JSONB", ha="left", fontsize=9.4, color=INK, family="monospace")
    ax.text(11, 38, "clé = 'applied_state'", ha="left", fontsize=8.6, color=GREY, style="italic")
    # JSONB
    # Cadre ajusté au contenu : il descendait jusqu'à y=18 pour un document qui
    # s'arrête bien plus haut, d'où un grand vide. Le bloc JSON est aligné en
    # haut, sous l'en-tête, au lieu d'être centré — ce qui le faisait remonter
    # jusqu'à chevaucher le titre.
    b2 = FancyBboxPatch((54, 30), 40, 52, boxstyle="round,pad=0.3,rounding_size=1.6",
                        linewidth=1.8, edgecolor=GREEN, facecolor=GREENLT)
    ax.add_patch(b2)
    ax.text(74, 77.5, "payload : applied_state (JSONB)", ha="center", va="center",
            fontsize=10, fontweight="bold", color=GREEN)
    ax.text(57, 71,
            "{\n  \"screw_config\": [81 entiers],\n  \"thermal_targets\": {Z1…Z8, DIE},\n  \"feeders\": [...],\n  \"feeder_calibrations\": {...},\n  \"dosing\": {...},\n  \"meta\": {...}\n}",
            ha="left", va="top", fontsize=8.8, color=INK, family="monospace",
            linespacing=1.45)
    arrow(ax, 42, 50, 54, 50, color=GREY, lw=1.8)
    save(fig, "fig_er_schema.png")


# --------------------------------------------------------------------------- #
# 15. Intersection des domaines
# --------------------------------------------------------------------------- #
def fig_domain_intersection():
    fig, ax = _ax(9.6, 6.4)
    title(ax, "Positionnement scientifique : une intersection peu couverte",
          "Extrusion bivis · apprentissage automatique · batteries tout-solide")
    circles = [
        (38, 58, "Extrusion\nbivis (TSE/HME)", BLUE2),
        (62, 58, "Batteries\ntout-solide (SSB)", GREEN),
        (50, 38, "Apprentissage\nautomatique", AMBER),
    ]
    for x, y, t, c in circles:
        ax.add_patch(Circle((x, y), 20, facecolor=c, edgecolor=c, alpha=0.18, lw=2))
        ax.add_patch(Circle((x, y), 20, facecolor="none", edgecolor=c, lw=2))
    ax.text(30, 64, "Extrusion bivis\n(TSE / HME)", ha="center", fontsize=9.6, color=BLUE, fontweight="bold")
    ax.text(70, 64, "Batteries\ntout-solide (SSB)", ha="center", fontsize=9.6, color=GREEN, fontweight="bold")
    ax.text(50, 26, "Apprentissage\nautomatique", ha="center", fontsize=9.6, color=AMBER, fontweight="bold")
    ax.text(50, 50, "Gap : peu\nd'études\nintégrées", ha="center", va="center",
            fontsize=9.2, color=RED, fontweight="bold")
    ax.text(50, 8,
            "Haarmann (2021) · Seeba (2024) · Kim (2023)  |  Drakopoulos (2021) · Daoudi (2024) · Kassab (2024)  |  Wang (2025) · Maia (2025)",
            ha="center", fontsize=7.6, color=GREY, style="italic")
    save(fig, "fig_domain_intersection.png")


# --------------------------------------------------------------------------- #
# 16. Extrait CSV capteur
# --------------------------------------------------------------------------- #
def fig_csv_extract():
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    ax.axis("off")
    ax.set_title("Extrait d'un fichier CSV brut de capteur (filière — TEMP_DIE)",
                 fontsize=12.5, fontweight="bold", color=BLUE, pad=10)
    data = [
        ["Timestamp", "Name", "Value"],
        ["2026-04-13T08:12:01.120Z", "DIE", "158.4"],
        ["2026-04-13T08:12:06.480Z", "DIE", "158.9"],
        ["2026-04-13T08:12:13.005Z", "DIE", "159.1"],
        ["2026-04-13T08:12:21.760Z", "DIE", "159.0"],
        ["2026-04-13T08:12:28.310Z", "DIE", "158.7"],
        ["…", "…", "…"],
    ]
    cols = [0.0, 0.55, 0.78, 1.0]
    rows = len(data)
    rowh = 1.0 / rows
    for i, row in enumerate(data):
        y = 1 - (i + 1) * rowh
        head = i == 0
        for j, val in enumerate(row):
            fc = BLUE if head else (GREYLT if i % 2 else WHITE)
            ax.add_patch(Rectangle((cols[j], y), cols[j + 1] - cols[j], rowh,
                         transform=ax.transAxes, facecolor=fc, edgecolor="#D9D9D9", lw=1))
            ax.text((cols[j] + cols[j + 1]) / 2, y + rowh / 2, val, transform=ax.transAxes,
                    ha="center", va="center", fontsize=9.2,
                    color=WHITE if head else INK, fontweight="bold" if head else "normal",
                    family="monospace" if not head else "DejaVu Sans")
    ax.text(0.0, -0.04, "≈ 50 145 enregistrements sur la période · échantillonnage irrégulier 1–15 s",
            transform=ax.transAxes, fontsize=8.4, color=GREY, style="italic")
    save(fig, "fig_csv_extract.png")


if __name__ == "__main__":
    fig_architecture()
    fig_data_pipeline()
    fig_persistence()
    fig_engine_logic()
    fig_two_level_ai()
    fig_stack_comparison()
    fig_swot()
    fig_crispdm()
    fig_gantt()
    fig_tests()
    fig_validation()
    fig_equations()
    fig_roadmap()
    fig_er_schema()
    fig_domain_intersection()
    fig_csv_extract()
    print("\nToutes les figures sont générées dans", OUT)
