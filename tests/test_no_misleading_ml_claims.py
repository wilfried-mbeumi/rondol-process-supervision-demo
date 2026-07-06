"""
test_no_misleading_ml_claims.py — Garde-fou sémantique (honnêteté jury).

Empêche l'app d'introduire un discours trompeur sur le ML, et prouve que les
règles métier ne consomment pas la sortie du modèle (séparation ML / règles).
"""
from __future__ import annotations

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_FILES = [
    ROOT / "app" / "rondol_i18n.py",
    ROOT / "app" / "Supervision.py",
    *(ROOT / "app" / "pages").glob("*.py"),
]

# Formulations interdites dans l'INTERFACE (sur-promesse / mensonge).
FORBIDDEN = [
    "prédiction fiable", "reliable prediction",
    "optimisation automatique", "automatic optimization",
    "supabase actif", "supabase active", "supabase est actif",
    "prédit la configuration", "predicts the configuration",
    # sur-affirmation de garantie de stabilité par un moteur non calibré (red-team P2)
    "garantit la stabilité", "guarantees overall process stability",
    # mention Supabase codée en dur dans un message rendu aussi en local-json (red-team P2)
    "synchronisé (supabase)", "synchronized (supabase)",
    "resynchronisé (supabase)", "resynchronized (supabase)",
    "prédiction industrielle certifiée d'une nouvelle",  # ne doit apparaître QUE nié
]


def test_ui_has_no_misleading_phrases():
    for f in UI_FILES:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8").lower()
        for bad in FORBIDDEN:
            if bad == "prédiction industrielle certifiée d'une nouvelle":
                # autorisé uniquement précédé d'une négation ("non une ...")
                idx = text.find(bad)
                if idx != -1:
                    ctx = text[max(0, idx - 12):idx]
                    assert "non" in ctx or "pas" in ctx, (
                        f"{f.name}: « {bad} » doit être nié dans le disclaimer")
                continue
            assert bad not in text, f"{f.name}: formulation trompeuse interdite « {bad} »"


def test_ml_disclaimer_present_and_explicit():
    cat = (ROOT / "app" / "rondol_i18n.py").read_text(encoding="utf-8")
    i = cat.find('"demo.ml.banner_default"')
    assert i != -1, "clé disclaimer ML absente"
    block = cat[i:i + 900].lower()
    assert "expérimental" in block
    assert "métier" in block            # logique/règles métier
    assert "enregistr" in block         # fenêtres d'essais enregistrés
    assert "ne réagit pas directement" in block  # contraste ML vs config live


def test_rules_do_not_consume_model_output():
    """La fonction evaluate() (règles) ne prend ni proba ni modèle en entrée."""
    from AgentIndustrial_v1.core.rules import evaluate
    params = list(inspect.signature(evaluate).parameters)
    for p in params:
        assert "proba" not in p.lower() and "model" not in p.lower() and "svm" not in p.lower(), (
            f"evaluate() ne doit pas dépendre du ML, paramètre suspect: {p}")
