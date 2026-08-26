"""patch_prez_presoutenance.py — Applique au support les corrections demandées après la pré-soutenance.

Deux opérations, chirurgicales, sur « MBEUMI_Wilfried_PREZ new.pptx » :

1. Diapositive 14 — remplacer la figure du championnat. L'ancienne affichait
   Random Forest à 0,796 en troisième position, alors que le commentaire de la
   même diapositive annonce 0,809 : le graphique contredisait le texte à l'écran.

2. Diapositives 6, 8 et 14 — retirer les bandeaux d'illustration générés. Ils
   n'apportent aucune information et l'un d'eux affiche du texte incohérent
   (« CHAMPIANISHIP », « MCDLIY ») lisible depuis le fond de la salle.

Les figures utiles, les captures de l'application et le diagramme de Gantt de la
diapositive 22 ne sont pas touchés.

Usage : python scripts/patch_prez_presoutenance.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "soutenance" / "MBEUMI_Wilfried_PREZ new.pptx"
OUT = ROOT / "reports" / "soutenance" / "MBEUMI_Wilfried_PREZ_corrige.pptx"
FIG = ROOT / "figures_memoire" / "fig_championnat_modeles.png"

# Bandeaux d'illustration à retirer, repérés par leur géométrie relative.
# (diapositive, borne gauche %, borne droite %) — hauteur ~100 % de la page.
BANDEAUX = [
    (6, 0.0, 40.0),    # photo « SWOT » en anglais, doublon de la vraie figure
    (8, 60.0, 100.0),  # bandeau droit sous le schéma d'architecture
    (14, 70.0, 100.0),  # bandeau « CHAMPIANISHIP » — texte incohérent
]


def supprimer(shape) -> None:
    shape._element.getparent().remove(shape._element)


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"Support introuvable : {SRC}")
    if not FIG.exists():
        raise SystemExit(f"Figure corrigée introuvable : {FIG}")

    shutil.copy2(SRC, OUT)
    prs = Presentation(str(OUT))
    W, H = prs.slide_width, prs.slide_height
    retires = remplacees = 0

    for num, gauche, droite in BANDEAUX:
        slide = prs.slides[num - 1]
        for shape in list(slide.shapes):
            if shape.shape_type != 13:
                continue
            x = shape.left / W * 100
            haut = shape.height / H * 100
            large = shape.width / W * 100
            # Un bandeau occupe toute la hauteur et moins de la moitié de la largeur.
            if haut >= 80.0 and large <= 45.0 and gauche <= x < droite:
                supprimer(shape)
                retires += 1
                print(f"  diapo {num:2d} — bandeau retiré "
                      f"({large:.0f}% x {haut:.0f}%, x={x:.0f}%)")

    # Diapositive 14 : la figure utile est la plus large restante.
    slide14 = prs.slides[13]
    figures = [s for s in slide14.shapes if s.shape_type == 13]
    if figures:
        cible = max(figures, key=lambda s: s.width)
        pos = (cible.left, cible.top, cible.width, cible.height)
        supprimer(cible)
        slide14.shapes.add_picture(str(FIG), pos[0], pos[1], pos[2], pos[3])
        remplacees += 1
        print(f"  diapo 14 — figure du championnat remplacée "
              f"(Random Forest 1er à 0,809)")

    # Retirer un bandeau laisse la figure décalée et un vide de l'autre côté :
    # on recentre la figure et on ramène les textes sur la même marge gauche.
    recentres = 0
    for num, _, _ in BANDEAUX:
        slide = prs.slides[num - 1]
        figures = [s for s in slide.shapes if s.shape_type == 13]
        if not figures:
            continue
        principale = max(figures, key=lambda s: s.width * s.height)
        if principale.width > W * 0.9:      # déjà pleine largeur
            continue
        nouveau_x = int((W - principale.width) / 2)
        if abs(nouveau_x - principale.left) < Emu(60000):
            continue                        # déjà centrée
        principale.left = nouveau_x

        # Translater le bloc de titre d'un seul tenant : déplacer les seuls
        # cadres porteurs de texte laisserait derrière eux les rectangles de
        # décoration qui les encadrent.
        marge = int(W * 0.06)
        autres = [s for s in slide.shapes if s is not principale
                  and s.shape_type != 13 and s.left is not None]
        if autres:
            delta = marge - min(s.left for s in autres)
            if delta:
                for s in autres:
                    s.left = s.left + delta
        recentres += 1
        print(f"  diapo {num:2d} — figure recentrée, bloc de titre translaté")

    # --- contraste : figures claires -> versions sombres ---------------------
    # Les figures du mémoire sont dessinées sur fond blanc. Projetées sur le vert
    # foncé du support, elles y découpent des rectangles blancs — c'est le défaut
    # de contraste relevé en pré-soutenance. On leur substitue les versions
    # composées sur le fond du support (figures_support/).
    SOMBRES = {6: "fig_swot.png", 8: "fig_architecture.png",
               11: "fig_two_level_ai.png", 14: "fig_championnat_modeles.png"}
    assombries = 0
    for num, nom in SOMBRES.items():
        source = ROOT / "figures_support" / nom
        if not source.exists():
            print(f"  [!] version sombre absente : {nom}")
            continue
        slide = prs.slides[num - 1]
        figures = [s for s in slide.shapes if s.shape_type == 13]
        if not figures:
            continue
        cible = max(figures, key=lambda s: s.width * s.height)
        pos = (cible.left, cible.top, cible.width, cible.height)
        supprimer(cible)
        slide.shapes.add_picture(str(source), *pos)
        assombries += 1
        print(f"  diapo {num:2d} — figure passée en palette sombre ({nom})")

    # --- bandeaux d'illustration restants sur les pages de contenu -----------
    # Conservés sur la couverture et la page de fin, où l'image est un parti pris.
    for num in (2, 12, 25, 26):
        if num > len(prs.slides):
            continue
        slide = prs.slides[num - 1]
        for shape in list(slide.shapes):
            if shape.shape_type != 13 or shape.left is None:
                continue
            if shape.height / H * 100 >= 95 and shape.width / W * 100 <= 40:
                supprimer(shape)
                retires += 1
                print(f"  diapo {num:2d} — bandeau d'illustration retiré")

    # --- diapositives ajoutées après la pré-soutenance -----------------------
    # « Pourquoi ces cinq modèles » précède le championnat ; « Augmentation de
    # données » suit « Le vrai résultat », là où la question du volume se pose.
    ajouts = [
        (ROOT / "reports" / "soutenance" / "slide_choix_modeles.png", 13),
        (ROOT / "reports" / "soutenance" / "slide_augmentation.png", 17),
    ]
    ajoutees = 0
    for image, position in ajouts:
        if not image.exists():
            print(f"  [!] image absente, diapositive non ajoutée : {image.name}")
            continue
        vierge = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
        slide = prs.slides.add_slide(vierge)
        for forme in list(slide.shapes):        # un gabarit peut porter des cadres
            supprimer(forme)
        slide.shapes.add_picture(str(image), 0, 0, W, H)

        # add_slide ajoute en fin de présentation : on replace l'entrée dans
        # la liste ordonnée des diapositives.
        liste = prs.slides._sldIdLst
        entree = liste[-1]
        liste.remove(entree)
        liste.insert(position, entree)
        ajoutees += 1
        print(f"  diapo {position + 1:2d} — ajoutée : {image.stem}")

    prs.save(OUT)
    print(f"\n[OK] {OUT.name} — {retires} bandeau(x) retiré(s), "
          f"{remplacees} figure(s) remplacée(s), {ajoutees} ajoutée(s), "
          f"{len(prs.slides)} diapositives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
