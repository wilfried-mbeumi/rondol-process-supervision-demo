"""build_figures_support_sombre.py — Recompose les figures du support en palette sombre.

Les figures du mémoire sont dessinées sur fond blanc : c'est correct pour
l'impression, mais projetées sur le fond vert foncé du support elles créent des
rectangles blancs qui déchirent la page. C'est le défaut de contraste relevé en
pré-soutenance.

Ce script produit une seconde version, sur le fond du support (#123331), à
n'utiliser QUE dans la présentation. Les figures du mémoire ne sont pas touchées :
figures_memoire/ reste la version papier, figures_support/ la version projetée.

Sorties : figures_support/*.png (format 16:9 ou proche, 150 dpi)

Usage : python scripts/build_figures_support_sombre.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures_support"
TABLE = (ROOT / "reports" / "AI_thesis_results" / "block_2_model_augmentation"
         / "table_for_thesis.csv")

FOND = "#123331"
CREME = "#F5EFE3"
TEXTE = "#DCE6E3"
TEAL = "#2FB39B"
GRIS = "#93A8A3"
AMBRE = "#E8A33D"
ROUGE = "#E06B60"
BLEU = "#6FA8D6"
VERT = "#6FBF8F"
TRAIT = "#2A4A45"


def figure(w=13.333, h=6.2):
    fig = plt.figure(figsize=(w, h), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(0, h)
    ax.axis("off"); ax.set_facecolor(FOND)
    return fig, ax


def carte(ax, x, y, w, h, couleur, alpha=0.13, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=couleur, alpha=alpha,
                                edgecolor=couleur, linewidth=lw))


def enregistrer(fig, nom: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / nom
    fig.savefig(p, facecolor=FOND)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ SWOT
def swot() -> Path:
    fig, ax = figure(13.333, 6.4)
    cases = [
        ("FORCES (internes)", VERT, 0.5, 3.35, [
            "Précision et miniaturisation (10,5 mm)",
            "Brevets configuration verticale (EU/US)",
            "Héritage pharmaceutique (Prix Galien 2020, 2023)",
            "Partenariats scientifiques (IJL, Chicago)"]),
        ("FAIBLESSES (internes)", AMBRE, 6.85, 3.35, [
            "Ressources limitées face aux concurrents",
            "Données d'essais peu nombreuses (huit)",
            "Outil non calibré industriellement",
            "Développement mono-acteur"]),
        ("OPPORTUNITÉS (externes)", BLEU, 0.5, 0.35, [
            "Marché tout-solide en forte croissance",
            "Pression anti-solvant (PFAS / ECHA)",
            "Différenciation par l'IA explicable",
            "Écosystème académique (IJL / ARTEM)"]),
        ("MENACES (externes)", ROUGE, 6.85, 0.35, [
            "Concurrents mieux dotés (Coperion)",
            "Rareté des données d'essais",
            "Marché tout-solide encore pré-industriel",
            "Risque de perception (prototype non calibré)"]),
    ]
    for titre, coul, x, y, points in cases:
        carte(ax, x, y, 5.95, 2.7, coul, 0.11)
        ax.text(x + 0.3, y + 2.32, titre, color=coul, fontsize=13.5,
                family="serif", weight="bold", va="center")
        for i, pt in enumerate(points):
            ax.text(x + 0.3, y + 1.78 - i * 0.42, "•  " + pt, color=TEXTE,
                    fontsize=11.5, family="serif", va="center")
    return enregistrer(fig, "fig_swot.png")


# ---------------------------------------------------------- architecture
def architecture() -> Path:
    fig, ax = figure(13.333, 6.2)
    couches = [
        ("INTERFACE", "Streamlit — sept pages, persistance en trois couches", TEAL),
        ("AGENT", "Onze règles explicables  +  modèle Random Forest", AMBRE),
        ("MOTEUR", "engine — NodeState enveloppe l'état, un seul appel", BLEU),
        ("CATALOGUES", "machine · materials · physics — modules purs", VERT),
        ("SOCLE MÉTIER", "screw_logic — géométrie réelle, calcul « Network 7 »", CREME),
    ]
    h, gap = 0.92, 0.22
    y = 5.05
    for i, (nom, desc, coul) in enumerate(couches):
        carte(ax, 1.6, y, 10.1, h, coul, 0.14 if i else 0.20)
        ax.text(2.0, y + h / 2 + 0.16, nom, color=coul, fontsize=13,
                family="serif", weight="bold", va="center")
        ax.text(2.0, y + h / 2 - 0.24, desc, color=TEXTE, fontsize=11.5,
                family="serif", va="center")
        if i < len(couches) - 1:
            ax.add_patch(FancyArrowPatch((6.65, y), (6.65, y - gap),
                                         arrowstyle="-|>", mutation_scale=13,
                                         color=GRIS, linewidth=1.1))
        y -= h + gap
    ax.text(6.65, 0.28, "Principe fondateur : envelopper, ne pas recalculer",
            color=TEAL, fontsize=13, family="serif", style="italic",
            ha="center", va="center")
    return enregistrer(fig, "fig_architecture.png")


# ------------------------------------------------------- deux niveaux IA
def two_level() -> Path:
    fig, ax = figure(13.333, 6.0)
    blocs = [
        ("NIVEAU 1 — MODÈLE", TEAL, 0.6, [
            "Random Forest · fenêtre 60 s · 87 variables",
            "Estime une probabilité de stabilité",
            "Donne le QUOI"]),
        ("NIVEAU 2 — RÈGLES", AMBRE, 4.75, [
            "Onze règles explicites, traçables",
            "Quel paramètre, dans quel sens, de combien",
            "Donne le POURQUOI et le COMMENT"]),
        ("DÉCISION", CREME, 8.9, [
            "L'opérateur arbitre",
            "L'outil n'exécute rien",
            "Aucune commande sur la machine"]),
    ]
    for titre, coul, x, points in blocs:
        carte(ax, x, 1.65, 3.8, 3.15, coul, 0.13)
        ax.text(x + 0.3, 4.42, titre, color=coul, fontsize=12.5,
                family="serif", weight="bold", va="center")
        ax.plot([x + 0.3, x + 3.5], [4.15, 4.15], color=coul, linewidth=1.1, alpha=0.5)
        for i, pt in enumerate(points):
            ax.text(x + 0.3, 3.72 - i * 0.62, pt, color=TEXTE, fontsize=11.5,
                    family="serif", va="center", wrap=True)
    for x in (4.55, 8.7):
        ax.add_patch(FancyArrowPatch((x, 3.2), (x + 0.28, 3.2),
                                     arrowstyle="-|>", mutation_scale=15,
                                     color=GRIS, linewidth=1.3))
    ax.text(6.67, 0.75,
            "Le modèle prédit.  Les règles expliquent.  L'humain décide.",
            color=CREME, fontsize=15, family="serif", ha="center", va="center")
    return enregistrer(fig, "fig_two_level_ai.png")


# --------------------------------------------------------- championnat
def championnat() -> Path:
    lignes = []
    with TABLE.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m = re.search(r"([\d.]+)\s*±\s*([\d.]+)",
                          row["Macro-F1 without augmentation"])
            if m:
                lignes.append((row["Model"].strip(),
                               float(m.group(1)), float(m.group(2))))
    lignes.sort(key=lambda t: t[1], reverse=True)
    noms = {"Logistic regression": "Régression\nlogistique",
            "Random Forest": "Random\nForest", "SVM (RBF)": "SVM (RBF)",
            "XGBoost": "XGBoost", "Neural network (MLP)": "Réseau de\nneurones (MLP)"}

    fig = plt.figure(figsize=(13.333, 6.0), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0.07, 0.16, 0.88, 0.72])
    ax.set_facecolor(FOND)

    x = range(len(lignes))
    moy = [m for _, m, _ in lignes]
    ect = [e for _, _, e in lignes]
    coul = [TEAL if n == "Random Forest" else "#3E6B64" for n, _, _ in lignes]
    ax.bar(x, moy, yerr=ect, capsize=6, color=coul, width=0.6,
           edgecolor=TEAL, linewidth=1.0,
           error_kw={"ecolor": GRIS, "elinewidth": 1.2})

    for xi, (m, e) in enumerate(zip(moy, ect)):
        ax.text(xi, m + e + 0.03, f"{m:.3f}".replace(".", ","), ha="center",
                va="bottom", fontsize=14, color=CREME, family="serif", weight="bold")
        ax.text(xi, m / 2, f"± {e:.3f}".replace(".", ","), ha="center",
                va="center", fontsize=10.5, color=TEXTE, family="serif")

    ax.set_xticks(list(x))
    ax.set_xticklabels([noms.get(n, n) for n, _, _ in lignes],
                       fontsize=12, color=TEXTE, family="serif")
    ax.set_ylabel("F1-macro (essai non vu)", fontsize=12, color=TEXTE, family="serif")
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0", "0,2", "0,4", "0,6", "0,8", "1,0"],
                       fontsize=10.5, color=GRIS, family="serif")
    ax.tick_params(colors=GRIS, length=0)
    ax.yaxis.grid(True, color=TRAIT, linewidth=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_title("Validation Leave-One-Group-Out — un essai entier écarté à chaque pli",
                 fontsize=13, color=CREME, family="serif", pad=16, loc="left")
    fig.text(0.07, 0.045,
             "Moustaches : écart-type inter-essais. Leur ampleur (0,16–0,22) traduit "
             "le faible nombre d'essais — c'est cette variabilité, non le classement, "
             "qui limite la portée du résultat.",
             fontsize=10, color=GRIS, family="serif")
    return enregistrer(fig, "fig_championnat_modeles.png")


# ------------------------------------------------------ pipeline données
def data_pipeline() -> Path:
    fig, ax = figure(13.333, 5.4)
    etapes = [
        ("CAPTEURS", "12 voies\n7–13 avril 2026", TEAL),
        ("NETTOYAGE", "valeurs aberrantes\ntrous, doublons", BLEU),
        ("FENÊTRAGE", "fenêtres de 60 s\nchevauchantes", VERT),
        ("DESCRIPTEURS", "87 variables\npar fenêtre", AMBRE),
        ("VALIDATION", "Leave-One-Group-Out\n8 essais", CREME),
    ]
    w, gap = 2.18, 0.42
    x = 0.65
    for i, (titre, desc, coul) in enumerate(etapes):
        carte(ax, x, 1.75, w, 2.05, coul, 0.14)
        ax.text(x + w / 2, 3.32, titre, color=coul, fontsize=11.5,
                family="serif", weight="bold", ha="center", va="center")
        ax.text(x + w / 2, 2.55, desc, color=TEXTE, fontsize=10.5,
                family="serif", ha="center", va="center", linespacing=1.6)
        if i < len(etapes) - 1:
            ax.add_patch(FancyArrowPatch((x + w, 2.78), (x + w + gap - 0.06, 2.78),
                                         arrowstyle="-|>", mutation_scale=14,
                                         color=GRIS, linewidth=1.2))
        x += w + gap
    volumes = [("310 782", "relevés bruts"), ("627", "fenêtres"),
               ("87", "variables"), ("8", "essais exploitables")]
    for i, (v, lbl) in enumerate(volumes):
        cx = 2.0 + i * 3.15
        ax.text(cx, 1.0, v, color=CREME, fontsize=19, family="serif",
                weight="bold", ha="center", va="center")
        ax.text(cx, 0.52, lbl, color=GRIS, fontsize=10.5, family="serif",
                ha="center", va="center")
    ax.text(6.67, 4.35, "Du capteur brut à la fenêtre validée",
            color=CREME, fontsize=14, family="serif", ha="center", va="center")
    return enregistrer(fig, "fig_data_pipeline.png")


# ------------------------------------------------------ validation externe
def validation() -> Path:
    fig = plt.figure(figsize=(13.333, 5.4), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0.09, 0.19, 0.85, 0.62])
    ax.set_facecolor(FOND)
    protocoles = ["Partition\naléatoire", "Leave-One-\nGroup-Out", "Base externe\nsimulée"]
    valeurs = [0.92, 0.79, 0.753]
    coul = ["#3E6B64", TEAL, AMBRE]
    x = range(len(valeurs))
    ax.bar(x, valeurs, color=coul, width=0.52, edgecolor=TEAL, linewidth=1.0)
    for xi, v in enumerate(valeurs):
        ax.text(xi, v + 0.035, f"{v:.3f}".replace(".", ",").rstrip("0").rstrip(","),
                ha="center", va="bottom", fontsize=17, color=CREME,
                family="serif", weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(protocoles, fontsize=12, color=TEXTE, family="serif")
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0,25", "0,50", "0,75", "1,0"],
                       fontsize=10.5, color=GRIS, family="serif")
    ax.tick_params(colors=GRIS, length=0)
    ax.yaxis.grid(True, color=TRAIT, linewidth=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_title("Plus le protocole est sévère, plus la performance baisse",
                 fontsize=13.5, color=CREME, family="serif", pad=18, loc="left")
    fig.text(0.09, 0.06,
             "Base externe : 100 800 lignes simulées, 3 479 fenêtres évaluées, "
             "sans réentraînement — 62 % des instabilités détectées.",
             fontsize=10.5, color=GRIS, family="serif")
    return enregistrer(fig, "fig_validation.png")


# ---------------------------------------------------------------- Gantt
def gantt() -> Path:
    fig = plt.figure(figsize=(13.333, 5.6), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax = fig.add_axes([0.30, 0.13, 0.66, 0.76])
    ax.set_facecolor(FOND)
    taches = [
        ("Cadrage & problématique", 0, 1.6, BLEU),
        ("État de l'art scientifique", 0.6, 2.0, BLEU),
        ("Campagne d'essais", 3.2, 0.5, TEAL),
        ("Préparation des données", 3.4, 1.0, BLEU),
        ("Moteur procédé", 1.8, 1.8, BLEU),
        ("Modélisation ML", 3.6, 1.4, TEAL),
        ("Interface Streamlit", 4.2, 1.6, BLEU),
        ("Persistance & auth.", 5.0, 1.2, BLEU),
        ("Tests & stabilisation", 4.6, 1.5, TEAL),
        ("Démonstration client", 5.5, 0.4, AMBRE),
        ("Rédaction & dépôt", 5.6, 1.9, BLEU),
    ]
    for i, (nom, deb, duree, coul) in enumerate(taches):
        y = len(taches) - i - 1
        ax.barh(y, duree, left=deb, height=0.52, color=coul, alpha=0.85,
                edgecolor=coul, linewidth=1.0)
        ax.text(-0.18, y, nom, ha="right", va="center", fontsize=10.5,
                color=TEXTE, family="serif")
    for pos, lbl in [(3.2, "Campagne\n7–13 avr."), (5.5, "Démo client\n16 juin")]:
        ax.axvline(pos, color=AMBRE, linestyle="--", linewidth=1.1, alpha=0.7)
        ax.text(pos, -1.25, lbl, color=AMBRE, fontsize=9.5, family="serif",
                ha="center", va="center")
    ax.set_xlim(-0.1, 7.7)
    ax.set_ylim(-1.8, len(taches) - 0.3)
    ax.set_xticks(range(8))
    ax.set_xticklabels(["Jan.", "Fév.", "Mars", "Avril", "Mai", "Juin",
                        "Juil.", "Août"], fontsize=10.5, color=GRIS, family="serif")
    ax.set_yticks([])
    ax.tick_params(colors=GRIS, length=0)
    ax.xaxis.grid(True, color=TRAIT, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_title("Rétroplanning du projet — janvier à août 2026",
                 fontsize=13, color=CREME, family="serif", pad=16, loc="left")
    return enregistrer(fig, "fig_gantt.png")


# ------------------------------------------------------------ tests
def tests() -> Path:
    fig, ax = figure(13.333, 5.2)
    familles = [
        ("Unitaires purs", "moteur, géométrie,\nrègles de l'agent", TEAL),
        ("Interface", "les sept pages\nStreamlit", BLEU),
        ("Persistance", "les trois couches,\nauto-réparation", VERT),
        ("Non-régression", "chaque incident\ndevenu un test", AMBRE),
        ("Internationalisation", "aucune fuite\nd'anglais visible", CREME),
        ("Accessibilité", "contrastes,\nWCAG 2.1 AA", ROUGE),
    ]
    w, h = 3.85, 1.55
    for i, (titre, desc, coul) in enumerate(familles):
        x = 0.75 + (i % 3) * (w + 0.5)
        y = 2.35 - (i // 3) * (h + 0.42)
        carte(ax, x, y, w, h, coul, 0.13)
        ax.text(x + 0.28, y + h - 0.42, titre, color=coul, fontsize=12,
                family="serif", weight="bold", va="center")
        ax.text(x + 0.28, y + 0.5, desc, color=TEXTE, fontsize=10.5,
                family="serif", va="center", linespacing=1.5)
    ax.text(6.67, 4.62, "725 tests automatisés sur 76 fichiers — tous passants",
            color=CREME, fontsize=16, family="serif", ha="center", va="center",
            weight="bold")
    ax.text(6.67, 4.15,
            "Indépendants de l'ordre d'exécution · rejouables sur un poste vierge",
            color=GRIS, fontsize=11, family="serif", ha="center", va="center")
    return enregistrer(fig, "fig_tests.png")


if __name__ == "__main__":
    for f in (swot(), architecture(), two_level(), championnat(),
              data_pipeline(), validation(), gantt(), tests()):
        print(f"[OK] {f.name} — {f.stat().st_size / 1024:.0f} Ko")
