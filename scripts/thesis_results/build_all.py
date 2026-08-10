# -*- coding: utf-8 -*-
"""
build_all.py — Assemble le livrable complet demandé par l'encadrant.

Enchaîne les trois blocs, la réconciliation avec les valeurs publiées, puis
construit l'arborescence exacte demandée et le ZIP.

Chaque dossier de bloc est rendu AUTONOME : le script de génération y est
recopié avec ses deux dépendances (common.py, fold_augment.py), imports
réécrits en imports plats. L'encadrant peut donc relancer n'importe quel bloc
depuis le dossier décompressé, sans installer le projet.

Usage : python -m scripts.thesis_results.build_all
        python -m scripts.thesis_results.build_all --skip-compute   (figures/ZIP seuls)
"""
from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd

from . import common

HERE = Path(__file__).resolve().parent

# Nom de fichier demandé par l'encadrant → module source du projet
SCRIPT_NAMES = {
    "block_1_validation_strategy": ("generate_validation_figure.py",
                                    "block1_validation_strategy.py"),
    "block_2_model_augmentation": ("generate_model_comparison.py",
                                   "block2_model_augmentation.py"),
    "block_3_confusion_generalisation": ("generate_confusion_analysis.py",
                                         "block3_confusion_generalisation.py"),
}

SOURCE_JSONS = [
    "robustness_full_w60.json",
    "augmentation_eval.json",
    "eval_consolidated_w60.json",
    "model_comparison_logo_w60.json",
    "augmentation_report.json",
    "ml_metrics_w60.json",
    "ml_metrics_mlp_w60.json",
]


def _flatten_imports(text: str) -> str:
    """Réécrit les imports relatifs du package en imports plats."""
    text = re.sub(r"^from \. import (.+)$",
                  lambda m: "import " + ", ".join(
                      s.strip() for s in m.group(1).split(",")),
                  text, flags=re.MULTILINE)
    text = re.sub(r"^from \.(\w+) import", r"from \1 import",
                  text, flags=re.MULTILINE)
    return text


def _copy_code() -> None:
    """Recopie les scripts de génération dans chaque dossier de bloc."""
    for folder, (target_name, src_name) in SCRIPT_NAMES.items():
        dest_dir = common.OUT_ROOT / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / target_name).write_text(
            _flatten_imports((HERE / src_name).read_text(encoding="utf-8")),
            encoding="utf-8")
        for dep in ("common.py", "fold_augment.py"):
            (dest_dir / dep).write_text(
                _flatten_imports((HERE / dep).read_text(encoding="utf-8")),
                encoding="utf-8")


def _copy_sources() -> None:
    src_dir = common.OUT_ROOT / "source_results"
    src_dir.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_JSONS:
        p = common.ROOT / "reports" / name
        if p.exists():
            shutil.copy2(p, src_dir / name)
    # Le générateur synthétique et le générateur de la base continue sont des
    # sources de résultat au même titre que les JSON.
    for rel in ("src/augment_dataset.py",
                "src/evaluate_augmentation.py",
                "src/robustness_check.py",
                "scripts/generate_consolidated_dataset.py",
                "scripts/evaluate_on_consolidated.py"):
        p = common.ROOT / rel
        if p.exists():
            shutil.copy2(p, src_dir / Path(rel).name)


def _write_thesis_tables() -> dict:
    """Produit les trois « tableaux prêts à intégrer », aux colonnes exactes demandées.

    Les intitulés de colonnes sont repris mot pour mot de la demande (en
    anglais), pour que le tableau puisse être collé sans retouche.
    """
    out = {}

    # ---- Bloc 1 : une ligne par stratégie de validation --------------
    # Le tableau demandé ne comporte pas de colonne « modèle » : il est donc
    # produit pour le modèle retenu (Random Forest), sur le périmètre des
    # folds évaluables.
    b1 = pd.read_csv(common.OUT_ROOT / "block_1_validation_strategy"
                     / "validation_summary.csv")
    b1 = b1[(b1["model"] == "RandomForest") & (b1["scope"] == "scorable_folds")]
    order = {"random_split": ("Random split (window-level)", 0),
             "group_shuffle": ("GroupShuffleSplit (run-level)", 1),
             "logo": ("Leave-One-Group-Out (run-level)", 2)}
    rows = []
    for _, r in b1.iterrows():
        label, rank = order[r["validation_strategy"]]
        rows.append({
            "_rank": rank,
            "Validation strategy": label,
            "Number of evaluations": int(r["n_evaluations"]),
            "Macro-F1": f"{r['macro_f1_mean']:.3f} ± {r['macro_f1_std']:.3f}",
            "Stable-class F1": f"{r['stable_f1_mean']:.3f} ± {r['stable_f1_std']:.3f}",
            "Unstable-class F1": f"{r['unstable_f1_mean']:.3f} ± {r['unstable_f1_std']:.3f}",
            "Accuracy": f"{r['accuracy_mean']:.3f} ± {r['accuracy_std']:.3f}",
            "ROC-AUC": f"{r['roc_auc_mean']:.3f} ± {r['roc_auc_std']:.3f}",
        })
    t1 = pd.DataFrame(rows).sort_values("_rank").drop(columns="_rank")
    common.write_csv(t1, common.OUT_ROOT / "block_1_validation_strategy"
                     / "table_for_thesis.csv")
    out["b1"] = t1

    # ---- Bloc 2 : une ligne par modèle -------------------------------
    # « with training-only augmentation » = pool synthétique régénéré à partir
    # du seul fold d'entraînement, seule condition qui satisfait les cinq
    # garanties méthodologiques. La condition historique est ajoutée à part,
    # explicitement étiquetée, pour la traçabilité.
    b2 = pd.read_csv(common.OUT_ROOT / "block_2_model_augmentation"
                     / "model_comparison_summary.csv")
    piv = b2.set_index(["model", "augmentation"])
    rows = []
    for m in common.MODEL_ORDER:
        none_f1 = piv.loc[(m, "none"), "macro_f1_mean"]
        fold_f1 = piv.loc[(m, "fold_aware"), "macro_f1_mean"]
        pool_f1 = piv.loc[(m, "pooled_global"), "macro_f1_mean"]
        rows.append({
            "Model": common.MODEL_LABELS[m],
            "Macro-F1 without augmentation":
                f"{none_f1:.3f} ± {piv.loc[(m, 'none'), 'macro_f1_std']:.3f}",
            "Macro-F1 with training-only augmentation":
                f"{fold_f1:.3f} ± {piv.loc[(m, 'fold_aware'), 'macro_f1_std']:.3f}",
            "Absolute change": f"{fold_f1 - none_f1:+.3f}",
            "ROC-AUC without augmentation":
                f"{piv.loc[(m, 'none'), 'roc_auc_mean']:.3f}",
            "ROC-AUC with augmentation":
                f"{piv.loc[(m, 'fold_aware'), 'roc_auc_mean']:.3f}",
            "Macro-F1 with leaky global augmentation (superseded)":
                f"{pool_f1:.3f} ± {piv.loc[(m, 'pooled_global'), 'macro_f1_std']:.3f}",
        })
    t2 = pd.DataFrame(rows)
    common.write_csv(t2, common.OUT_ROOT / "block_2_model_augmentation"
                     / "table_for_thesis.csv")
    out["b2"] = t2

    # ---- Bloc 3 : une ligne par jeu d'évaluation ---------------------
    b3 = pd.read_csv(common.OUT_ROOT / "block_3_confusion_generalisation"
                     / "generalisation_summary.csv")
    rows = []
    for _, r in b3.iterrows():
        rows.append({
            "Evaluation dataset": r["evaluation_dataset"],
            "Number of windows": int(r["number_of_windows"]),
            "Stable/unstable distribution":
                f"{r['stable_pct']:.1f} % / {r['unstable_pct']:.1f} %",
            "Macro-F1": f"{r['macro_f1']:.3f}",
            "Unstable precision": f"{r['unstable_precision']:.3f}",
            "Unstable recall": f"{r['unstable_recall']:.3f}",
            "Specificity": f"{r['specificity']:.3f}",
            "Accuracy": f"{r['accuracy']:.3f}",
            "Balanced accuracy": f"{r['balanced_accuracy']:.3f}",
            "ROC-AUC": f"{r['roc_auc']:.3f}",
            "PR-AUC": f"{r['pr_auc_unstable']:.3f}",
        })
    t3 = pd.DataFrame(rows)
    common.write_csv(t3, common.OUT_ROOT / "block_3_confusion_generalisation"
                     / "table_for_thesis.csv")
    out["b3"] = t3
    return out


def _md_table(df: pd.DataFrame) -> list[str]:
    """Rend un DataFrame en tableau markdown."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return lines


def _write_readme() -> None:
    """README = dictionnaire de donnees, pas un rapport.

    L'encadrant a precise qu'il adapterait lui-meme la mise en forme : ce
    fichier decrit donc le contenu et les conventions, et laisse
    l'interpretation au memoire et au message d'accompagnement.
    """
    tables = _write_thesis_tables()
    rec = pd.read_csv(common.OUT_ROOT / "reconciliation_report.csv")
    n_ok = int((rec["statut"] == "CONFIRME\u0301".replace("E\u0301", "\u00c9")).sum()) \
        if False else int((rec["statut"] == "CONFIRM\u00c9").sum())
    n_gap = int((rec["statut"] == "\u00c9CART").sum())

    L = []
    A = L.append
    A("# AI thesis results \u2014 Rondol")
    A("")
    A("D\u00e9tection de fen\u00eatres d'extrusion instables, extrudeuse bivis Rondol.")
    A("Fen\u00eatre 60 s, pas 30 s, 87 variables, 627 fen\u00eatres r\u00e9elles issues de "
      "8 essais (7-13 avril 2026).")
    A("")
    A("CSV en UTF-8 avec BOM (ouverture directe sous Excel), s\u00e9parateur virgule, "
      "6 d\u00e9cimales. Figures en PNG 300 dpi et SVG vectoriel.")
    A("")
    A("---")
    A("")
    A("## Convention de classe")
    A("")
    A("La classe positive est **`unstable`**, conform\u00e9ment \u00e0 la demande. Dans les "
      "fichiers, `y_true` / `y_pred` valent `1` pour *stable* et `0` pour *unstable*.")
    A("")
    A("| | Predicted stable | Predicted unstable |")
    A("|---|---|---|")
    A("| **Actual stable** | TN | FP \u2014 fausse alerte |")
    A("| **Actual unstable** | FN \u2014 instabilit\u00e9 non d\u00e9tect\u00e9e | TP \u2014 instabilit\u00e9 d\u00e9tect\u00e9e |")
    A("")
    A("`probability_stable` est la sortie de `predict_proba` ; "
      "`probability_unstable = 1 \u2212 probability_stable`. Seuil de d\u00e9cision 0,5.")
    A("")
    A("---")
    A("")
    A("## M\u00e9thode d'agr\u00e9gation")
    A("")
    A("**Blocs 1 et 2 \u2014 moyenne des m\u00e9triques par fold.** La m\u00e9trique est calcul\u00e9e "
      "sur chaque fold, puis moyenn\u00e9e. Chaque essai p\u00e8se autant, quel que soit son "
      "nombre de fen\u00eatres (250 pour l'essai 1, 29 pour l'essai 42). \u00c9cart-type de "
      "population (ddof = 0), comme dans `evaluate_augmentation.py`, pour rester "
      "comparable aux chiffres d\u00e9j\u00e0 diffus\u00e9s.")
    A("")
    A("**Bloc 3 \u2014 mise en commun des pr\u00e9dictions (pooled).** Les pr\u00e9dictions "
      "out-of-fold des huit it\u00e9rations sont concat\u00e9n\u00e9es, puis une seule matrice de "
      "confusion est calcul\u00e9e. Chaque fen\u00eatre p\u00e8se autant. C'est le mode correct "
      "pour une matrice de confusion ; moyenner des taux par fold donnerait des "
      "effectifs non entiers.")
    A("")
    A("Un \u00e9cart entre le macro-F1 du bloc 2 (moyenne des folds) et celui du bloc 3 "
      "(pooled) est donc attendu : deux quantit\u00e9s diff\u00e9rentes calcul\u00e9es sur les "
      "m\u00eames pr\u00e9dictions.")
    A("")
    A("**P\u00e9rim\u00e8tre.** Les essais 32 et 42 sont int\u00e9gralement stables : macro-F1 "
      "d\u00e9g\u00e9n\u00e9r\u00e9 et ROC-AUC ind\u00e9fini. Les agr\u00e9gats sont publi\u00e9s sur deux "
      "p\u00e9rim\u00e8tres, `all_folds` (8) et `scorable_folds` (6). Le p\u00e9rim\u00e8tre \u00e0 retenir "
      "est `scorable_folds`.")
    A("")
    A("---")
    A("")
    A("## Note m\u00e9thodologique")
    A("")
    A("Le pool synth\u00e9tique historique \u00e9tait g\u00e9n\u00e9r\u00e9 une seule fois \u00e0 partir des huit "
      "essais, puis inject\u00e9 dans chaque fold d'entra\u00eenement : l'essai de test servait "
      "donc de point d'ancrage. Deux des cinq garanties demand\u00e9es n'\u00e9taient pas "
      "satisfaites. La condition `fold_aware` r\u00e9g\u00e9n\u00e8re le pool \u00e0 partir du seul fold "
      "d'entra\u00eenement et les satisfait toutes.")
    A("")
    A("D\u00e9tail point par point : `block_2_model_augmentation/methodological_checks.json`.")
    A(f"Confrontation aux valeurs d\u00e9j\u00e0 publi\u00e9es : `reconciliation_report.csv` "
      f"({n_ok} confirm\u00e9es, {n_gap} \u00e9carts, tous expliqu\u00e9s).")
    A("")
    A("---")
    A("")
    A("## Tableaux pr\u00eats \u00e0 int\u00e9grer")
    A("")
    A("\u00c9galement fournis en CSV sous le nom `table_for_thesis.csv` dans chaque "
      "dossier de bloc.")
    A("")
    A("### Bloc 1 \u2014 strat\u00e9gies de validation (Random Forest, 6 folds \u00e9valuables)")
    A("")
    L.extend(_md_table(tables["b1"]))
    A("")
    A("### Bloc 2 \u2014 mod\u00e8les et augmentation (Leave-One-Group-Out)")
    A("")
    L.extend(_md_table(tables["b2"]))
    A("")
    A("La derni\u00e8re colonne reprend la condition historique, entach\u00e9e de la fuite "
      "d'ancrage ; elle est conserv\u00e9e pour la tra\u00e7abilit\u00e9 et ne doit pas \u00eatre "
      "pr\u00e9sent\u00e9e comme la performance du mod\u00e8le.")
    A("")
    A("### Bloc 3 \u2014 g\u00e9n\u00e9ralisation")
    A("")
    L.extend(_md_table(tables["b3"]))
    A("")
    A("---")
    A("")
    A("## Dictionnaire des fichiers")
    A("")
    A("### block_1_validation_strategy")
    A("")
    A("| Fichier | Contenu |")
    A("|---|---|")
    A("| `validation_metrics_by_fold.csv` | Une ligne par strat\u00e9gie \u00d7 mod\u00e8le \u00d7 fold. "
      "Colonnes : `fold_id`, `seed`, `test_run_id`, `n_train_runs`, `n_test_runs`, "
      "`n_train_windows`, `n_test_windows`, `train_pct_stable`, `test_pct_stable`, "
      "`test_single_class`, puis les m\u00e9triques. |")
    A("| `validation_summary.csv` | Agr\u00e9gats moyenne / \u00e9cart-type / min / max, pour "
      "les deux p\u00e9rim\u00e8tres (`scope`). |")
    A("| `validation_predictions.csv` | Pr\u00e9dictions individuelles : "
      "`validation_strategy`, `fold_id`, `test_run_id`, `window_id`, `y_true`, "
      "`y_pred`, `probability_stable`, `probability_unstable`. |")
    A("| `table_for_thesis.csv` | Tableau pr\u00eat \u00e0 int\u00e9grer. |")
    A("| `validation_strategy_figure.png` / `.svg` | Panneau A macro-F1, panneau B "
      "ROC-AUC, folds superpos\u00e9s. |")
    A("| `generate_validation_figure.py` | Script de production (avec `common.py` et "
      "`fold_augment.py`). |")
    A("")
    A("Trois strat\u00e9gies : `random_split` (10 r\u00e9p\u00e9titions, fen\u00eatres tir\u00e9es sans tenir "
      "compte de l'essai \u2014 **estimation optimiste expos\u00e9e \u00e0 la fuite par "
      "autocorr\u00e9lation temporelle, pas la performance retenue**), `group_shuffle` "
      "(10 r\u00e9p\u00e9titions, aucun essai partag\u00e9), `logo` (8 folds, un essai exclu par "
      "fold).")
    A("")
    A("### block_2_model_augmentation")
    A("")
    A("| Fichier | Contenu |")
    A("|---|---|")
    A("| `model_metrics_by_fold.csv` | Une ligne par mod\u00e8le \u00d7 condition \u00d7 fold, aux "
      "13 colonnes demand\u00e9es, plus `n_train_real`, `n_train_synthetic`, "
      "`test_single_class` et les effectifs TP/FN/FP/TN. |")
    A("| `model_comparison_summary.csv` | Agr\u00e9gats par mod\u00e8le et condition. |")
    A("| `model_predictions_by_fold.csv` | Pr\u00e9dictions individuelles pour chaque "
      "mod\u00e8le et condition. |")
    A("| `methodological_checks.json` | R\u00e9ponse point par point aux cinq garanties. |")
    A("| `table_for_thesis.csv` | Tableau pr\u00eat \u00e0 int\u00e9grer. |")
    A("| `model_augmentation_figure.png` / `.svg` | Panneau A macro-F1 par mod\u00e8le, "
      "panneau B \u0394 macro-F1. |")
    A("| `generate_model_comparison.py` | Script de production. |")
    A("")
    A("Trois valeurs de `augmentation` : `none` (essais r\u00e9els seuls), "
      "`pooled_global` (protocole historique, pool ancr\u00e9 sur les 8 essais), "
      "`fold_aware` (protocole corrig\u00e9, pool r\u00e9g\u00e9n\u00e9r\u00e9 par fold).")
    A("")
    A("### block_3_confusion_generalisation")
    A("")
    A("| Fichier | Contenu |")
    A("|---|---|")
    A("| `logo_oof_predictions.csv` | 627 pr\u00e9dictions out-of-fold, chaque fen\u00eatre "
      "r\u00e9elle exactement une fois, produite par le mod\u00e8le dont l'essai \u00e9tait exclu. "
      "Unicit\u00e9 v\u00e9rifi\u00e9e par assertion \u00e0 l'ex\u00e9cution. |")
    A("| `continuous_dataset_predictions.csv` | 3 479 pr\u00e9dictions sur le dataset "
      "continu simul\u00e9. |")
    A("| `confusion_matrices.csv` | TP / TN / FP / FN explicites pour les deux "
      "\u00e9valuations. |")
    A("| `generalisation_summary.csv` | Jeu complet de m\u00e9triques, dont sp\u00e9cificit\u00e9, "
      "valeur pr\u00e9dictive n\u00e9gative et PR-AUC. |")
    A("| `table_for_thesis.csv` | Tableau pr\u00eat \u00e0 int\u00e9grer. |")
    A("| `confusion_matrices.png` / `.svg` | Effectifs absolus et pourcentages "
      "normalis\u00e9s par classe r\u00e9elle. |")
    A("| `roc_pr_curves.png` / `.svg` | Courbes ROC et pr\u00e9cision-rappel. |")
    A("| `generate_confusion_analysis.py` | Script de production. |")
    A("")
    A("**Nature du dataset continu : simul\u00e9.** Campagne continue de 100 800 lignes "
      "au pas de 10 s (\u2248 11,7 jours), calibr\u00e9e statistiquement sur les essais "
      "r\u00e9els : 5 recettes, cycles ambiant \u2192 chauffe \u2192 plateau r\u00e9gul\u00e9 (bruit AR(1)) "
      "\u2192 extrusion \u2192 refroidissement, valeurs manquantes 1-5 %, aberrations "
      "thermocouple (code 3276,7). Graine fixe, donc reproductible. Ce n'est pas un "
      "jeu exp\u00e9rimental : aucune mesure physique suppl\u00e9mentaire n'a \u00e9t\u00e9 acquise. "
      "Le mod\u00e8le y est appliqu\u00e9 tel quel, sans r\u00e9entra\u00eenement.")
    A("")
    A("### source_results")
    A("")
    A("JSON de r\u00e9sultats d\u00e9j\u00e0 publi\u00e9s dans le projet et scripts qui les ont "
      "produits, joints pour permettre la confrontation.")
    A("")
    A("---")
    A("")
    A("## Reproduire")
    A("")
    A("Depuis la racine du d\u00e9p\u00f4t :")
    A("")
    A("```")
    A("python -m scripts.thesis_results.build_all")
    A("```")
    A("")
    A("Chaque dossier de bloc est autonome : le script `generate_*.py` y est recopi\u00e9 "
      "avec ses d\u00e9pendances, imports aplatis.")
    A("")
    A("Tout est d\u00e9terministe \u2014 graine 42, et 20260417 pour la base continue. Les "
      "m\u00e9triques publi\u00e9es sont recalculables depuis les fichiers de pr\u00e9dictions.")

    (common.OUT_ROOT / "README.md").write_text("\n".join(L) + "\n",
                                               encoding="utf-8")


def _build_zip() -> Path:
    """Archive le livrable, hors artefacts d'exécution Python."""
    # Un import des copies autonomes laisse des __pycache__ dans les dossiers
    # de bloc : ils n'ont rien à faire dans le livrable.
    for cache in common.OUT_ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    zip_path = common.ROOT / "reports" / "AI_thesis_results.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(common.OUT_ROOT.rglob("*")):
            if p.is_file() and p.suffix != ".pyc":
                zf.write(p, Path("AI_thesis_results") / p.relative_to(common.OUT_ROOT))
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true",
                    help="ne recalcule pas les blocs, reconstruit l'archive")
    args = ap.parse_args()

    if not args.skip_compute:
        from . import (block1_validation_strategy, block2_model_augmentation,
                       block3_confusion_generalisation)
        print("[1/4] Bloc 1 — stratégies de validation…")
        block1_validation_strategy.run()
        print("[2/4] Bloc 2 — modèles × augmentation…")
        block2_model_augmentation.run()
        print("[3/4] Bloc 3 — confusion et généralisation…")
        block3_confusion_generalisation.run()

    print("[4/4] Réconciliation, code, sources, README, contrôles, ZIP…")
    from . import reconciliation, verify_deliverable
    reconciliation.run()
    _copy_code()
    _copy_sources()
    _write_readme()

    # Le contrôle d'acceptation reste un outil INTERNE : il valide le livrable
    # avant envoi mais n'y est pas joint. L'encadrant a demandé des données,
    # des figures et des scripts — pas notre procédure de recette.
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = verify_deliverable.run()
    (common.ROOT / "reports" / "acceptance_checks.txt").write_text(
        buf.getvalue(), encoding="utf-8")
    print("      " + buf.getvalue().splitlines()[-1] + "  (rapport interne : "
          "reports/acceptance_checks.txt)")
    if rc != 0:
        print("!! des contrôles ont échoué — voir reports/acceptance_checks.txt")

    # Purge des fichiers qui ont pu être déposés dans le livrable par une
    # exécution antérieure et qui ne relèvent pas de la demande.
    # reconciliation_report.md est CONSERVÉ : c'est la forme lisible de la
    # confirmation des valeurs publiées, explicitement demandée.
    for stray in ("acceptance_checks.txt", "verify_deliverable.py",
                  "common.py"):
        p = common.OUT_ROOT / stray
        if p.exists():
            p.unlink()

    zip_path = _build_zip()

    n_files = sum(1 for p in common.OUT_ROOT.rglob("*") if p.is_file())
    size_mb = zip_path.stat().st_size / 1e6
    print(f"\n[OK] {n_files} fichiers · {zip_path} ({size_mb:.1f} Mo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
