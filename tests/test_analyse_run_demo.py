"""Tests — /Analyse_run : les métriques du dataset demo (dont la durée) sont
marquées DEMO, jamais présentées comme un run opérateur réel.
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
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False

ANALYSE = str(ROOT / "app" / "pages" / "3_Run_Analysis.py")


def _rendered(at) -> str:
    chunks = []
    for kind in ("markdown", "caption"):
        try:
            chunks += [str(getattr(e, "value", "")) for e in getattr(at, kind)]
        except Exception:
            pass
    try:
        chunks += [str(getattr(e, "body", getattr(e, "value", ""))) for e in at.get("html")]
    except Exception:
        pass
    return "\n".join(chunks)


def _metric_labels_values(at):
    labels, values = [], []
    try:
        for m in at.metric:
            labels.append(str(getattr(m, "label", "")))
            values.append(str(getattr(m, "value", "")))
    except Exception:
        pass
    return labels, values


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_analyse_run_duration_is_marked_demo_or_hidden():
    at = AppTest.from_file(ANALYSE).run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    labels, values = _metric_labels_values(at)
    has_duration = any(v.strip().endswith("min") for v in values)
    blob = _rendered(at)
    if has_duration:
        # Si la durée reste affichée, elle DOIT être marquée DEMO sur la page.
        assert "DEMO" in blob, "durée affichée sans marquage DEMO"
    # Sinon (durée masquée), c'est acceptable aussi.


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_analyse_run_does_not_present_demo_metrics_as_operator_truth():
    at = AppTest.from_file(ANALYSE).run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
    blob = _rendered(at)
    assert "DEMO" in blob or "demonstration" in blob.lower()
    assert "ML trial dataset" in blob or "dataset ML" in blob
    assert "not a live operator run" in blob or "non un run opérateur live" in blob


@pytest.mark.skipif(not _HAS, reason="streamlit.testing indisponible")
def test_analyse_run_loads_in_english():
    at = AppTest.from_file(ANALYSE)
    at.session_state["ui_lang"] = "en"
    at.run(timeout=60)
    assert not at.exception, [str(e.value) for e in at.exception]
