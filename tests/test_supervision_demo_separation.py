"""Tests P3 (partiel) — Supervision : pas de « temps de run » non validé en tête,
et marquage DEMO explicite des indicateurs issus du dataset ML d'essais.

Exigences manager :
  - le temps (ex. 26.5 min) du dataset ML ne doit plus être affiché comme un
    temps de run réel dans l'UI principale ;
  - les indicateurs ML de démonstration doivent porter un marquage DEMO.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest  # type: ignore
    _HAS_APPTEST = True
except Exception:  # pragma: no cover
    _HAS_APPTEST = False

HOME = str(ROOT / "app" / "Supervision.py")


def _run():
    at = AppTest.from_file(HOME).run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _html_blob(at) -> str:
    chunks = []
    try:
        for el in at.get("html"):
            chunks.append(str(getattr(el, "body", getattr(el, "value", ""))))
    except Exception:
        pass
    return "\n".join(chunks)


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_26_5_min_not_displayed_as_real_run_time():
    at = _run()
    # Aucune métrique « Durée / Duration » ne doit subsister en tête de page.
    labels = []
    try:
        labels = [str(getattr(m, "label", "")) for m in at.metric]
    except Exception:
        pass
    for lab in labels:
        assert lab not in ("Durée", "Duration"), f"métrique durée encore présente : {labels}"
    # Et aucun libellé de métrique ne se termine par « min » (temps de run).
    values = []
    try:
        values = [str(getattr(m, "value", "")) for m in at.metric]
    except Exception:
        pass
    assert not any(v.strip().endswith("min") for v in values), values


@pytest.mark.skipif(not _HAS_APPTEST, reason="streamlit.testing indisponible")
def test_ml_demo_indicators_marked_demo():
    at = _run()
    blob = _html_blob(at)
    assert "DEMO" in blob
    assert "dataset ML" in blob
