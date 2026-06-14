"""EN visible-text leak finder — POPULATED client snapshot, HTML/CSS stripped.

Unlike _validate_en_strict (which scans raw HTML bodies incl. <style> blocks and
CSS comments → false positives like 'alerte'/'ACTION'), this strips <style>…</style>
and all tags, leaving only what the operator actually SEES. It commits a realistic
client snapshot to an isolated durable store first, so material/agent/process content
renders (empty state hides most leaks).

Run: python tests/_en_visible_leaks.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
for _p in (ROOT, APP):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_tmp = tempfile.mkdtemp(prefix="rondol_enleak_")
os.environ["RONDOL_RUN_STATE_PATH"] = str(Path(_tmp) / "current_run_state.json")
os.environ["RONDOL_APPLIED_STATE_PATH"] = str(Path(_tmp) / "applied_state.json")
os.environ["RONDOL_HISTORY_PATH"] = str(Path(_tmp) / "process_history.json")
os.environ["RONDOL_EXTERNAL_STORE_PATH"] = str(Path(_tmp) / "durable_store.json")

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = {
    "Supervision": str(APP / "Supervision.py"),
    "Profile": str(APP / "pages" / "1_Profile.py"),
    "Settings": str(APP / "pages" / "2_Settings.py"),
    "Run_Analysis": str(APP / "pages" / "3_Run_Analysis.py"),
    "History": str(APP / "pages" / "4_History.py"),
    "Process_Engine": str(APP / "pages" / "5_Process_Engine.py"),
}

# Accented FR letters are the most reliable signal of an untranslated string.
FR_ACCENTS = re.compile(r"[àâäéèêëîïôöùûüçœ]", re.IGNORECASE)
# Specific FR words the operator reported / common offenders.
# Whole-word match only (\b) — avoids substring false positives like
# 'alerte'⊂"alerted", 'vide'⊂"provides". 'granules' is INTENTIONALLY absent:
# it is the correct English label_en for material id 'granules'.
FR_WORDS = [
    "granulés", "poudres", "poudre", "liquide",
    "matière", "procédé", "débit", "vitesse", "densité",
    "entrée", "couple", "résidence", "remplissage", "cisaillement",
    "alerte", "alertes", "régime", "convoyage", "malaxage",
    "aucune", "aucun", "élément", "éléments", "puissance",
    "principale", "secondaire", "secondaires", "vide", "vidée",
]
_FR_WORD_RE = {w: re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
               for w in FR_WORDS}


def _strip_html(s: str) -> str:
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)            # drop tags
    s = re.sub(r"\s+", " ", s)
    return s


def _visible_text(at) -> str:
    chunks: list[str] = []
    for kind in ("markdown", "caption", "header", "subheader", "text",
                 "info", "warning", "error", "success"):
        try:
            for el in getattr(at, kind):
                chunks.append(_strip_html(str(getattr(el, "value", ""))))
        except Exception:
            pass
    try:
        for el in at.get("html"):
            chunks.append(_strip_html(str(getattr(el, "body", getattr(el, "value", "")))))
    except Exception:
        pass
    try:
        for m in at.metric:
            chunks.append(str(getattr(m, "label", "")))
            chunks.append(_strip_html(str(getattr(m, "value", ""))))
    except Exception:
        pass
    return "\n".join(chunks)


def _commit_client_snapshot() -> None:
    """Realistic client config: feeder #1 granules enabled, 100 rpm, 6 elements."""
    from AgentIndustrial_v1.core.process import ProcessState
    from AgentIndustrial_v1.core.feeders import new_feeder_bank
    from AgentIndustrial_v1.core.applied_state import commit
    import screw_logic

    cfg = list(screw_logic.new_empty_configuration())
    # place a handful of conveying + mixing elements
    placed = 0
    for i in range(2, len(cfg)):
        if placed >= 6:
            break
        cfg[i] = 1
        placed += 1

    feeders = new_feeder_bank()
    feeders[0].enabled = True
    feeders[0].material_id = "granules"
    feeders[0].mass_flow_g_per_min = 4.1667
    feeders[0].density_g_per_cm3 = 0.55

    st = ProcessState(screw_config=cfg, screw_rpm=100.0, feeders=feeders)
    session: dict = {
        "feeder_rpm": 100.0, "feeder_calib_g_h_per_rpm": 2.5,
        "fd_en_1": True, "ni_rpm_hmi": 100.0,
    }
    commit(session, st, label="TEST_CLIENT_SYNC_001")


def _load_en(path: str):
    at = AppTest.from_file(path)
    at.session_state["ui_lang"] = "en"
    at.session_state["demo_mode"] = False
    return at.run(timeout=120)


def main() -> int:
    _commit_client_snapshot()
    all_ok = True
    for name, path in PAGES.items():
        at = _load_en(path)
        print(f"\n{'='*64}\n  PAGE: {name}\n{'='*64}")
        if at.exception:
            print(f"  [EXCEPTION] {[str(e.value) for e in at.exception]}")
            all_ok = False
            continue
        text = _visible_text(at)
        low = text.lower()

        hits: dict[str, list[str]] = {}
        for line in text.split("\n"):
            ll = line.lower()
            matched = [w for w in FR_WORDS if _FR_WORD_RE[w].search(ll)]
            if FR_ACCENTS.search(line):
                # collect the accented tokens
                toks = [tok for tok in re.findall(r"\b[\wàâäéèêëîïôöùûüçœ'-]+\b", line)
                        if FR_ACCENTS.search(tok)]
                matched += [f"~{t}" for t in toks]
            for m in matched:
                hits.setdefault(m, []).append(line.strip()[:140])

        if not hits:
            print("  [OK] no visible French")
            continue
        all_ok = False
        for word, lines in sorted(hits.items()):
            print(f"  [FR] {word!r}  ({len(lines)}x)")
            print(f"        e.g. {lines[0]}")
    print(f"\n{'='*64}")
    print("  CLEAN" if all_ok else "  LEAKS FOUND")
    print(f"  tmp: {_tmp}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
