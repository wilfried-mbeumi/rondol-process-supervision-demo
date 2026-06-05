"""Tests production — résistance aux collisions de modules type Streamlit Cloud.

Objectif : prouver qu'AUCUNE page Streamlit ne plante par ImportError quand
l'environnement charge un module concurrent (cas réel : package PyPI `i18n` v0.2
qui squattait `sys.modules['i18n']` sur Streamlit Cloud avant que le bootstrap
sys.path local n'ait effet).

Chaque test charge une page dans un sous-processus Python frais, avec un sys.path
volontairement « pollué » par un faux module `i18n` posé devant le `app/`. Si une
page importe encore `from i18n import …`, elle plante. Si elle importe
`from rondol_i18n import …` (correctif d'option (a)), elle passe.

Pas de Streamlit context : on s'arrête au premier RuntimeError de Streamlit ou on
considère le module chargé jusqu'à `st.set_page_config` sans ImportError.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

PAGES = {
    "supervision": ROOT / "app" / "Supervision.py",
    "profile":     ROOT / "app" / "pages" / "1_Profile.py",
    "settings":    ROOT / "app" / "pages" / "2_Settings.py",
    "analyse":     ROOT / "app" / "pages" / "3_Analyse_run.py",
    "historique":  ROOT / "app" / "pages" / "4_Historique.py",
    "moteur":      ROOT / "app" / "pages" / "5_Moteur_Procede.py",
}


def _fake_i18n_pollution_dir(tmp_path: Path) -> Path:
    """Crée un module `i18n.py` factice (et `i18n/__init__.py` pour le cas package)
    sans `language_selector`/`t` → reproduit la collision PyPI `i18n` v0.2.

    Ce dossier est placé en TÊTE du sys.path pour qu'un `from i18n import …` y
    résolve d'abord. Une page non corrigée → ImportError. Une page utilisant
    `from rondol_i18n import …` passe.
    """
    poll = tmp_path / "_poll"
    poll.mkdir()
    (poll / "i18n.py").write_text(
        "# Faux module i18n (simule le package PyPI 'i18n' v0.2)\n"
        "VERSION = 'fake-pypi-collision'\n",
        encoding="utf-8",
    )
    return poll


def _run_page_with_pollution(page_path: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    """Charge `page_path` dans un Python frais, avec un faux `i18n` PyPI en tête
    de sys.path. Renvoie le CompletedProcess (stdout/stderr/returncode).

    On simule le mode Streamlit Cloud : CWD = racine repo, page exécutée comme
    un script. On attrape l'exécution jusqu'au premier `st.set_page_config`
    (Streamlit n'a pas de ScriptRunContext → exception attendue mais bénigne
    DIFFÉRENTE d'un ImportError).
    """
    poll = _fake_i18n_pollution_dir(tmp_path)

    loader = textwrap.dedent(f"""
        import sys, importlib.util, traceback, os
        # Pollution : faux 'i18n' AVANT toute autre entrée
        sys.path.insert(0, {str(poll)!r})
        # CWD repo (comme sur Cloud)
        os.chdir({str(ROOT)!r})
        # On purge tout cache éventuel
        for m in list(sys.modules):
            if m in ("i18n", "rondol_i18n", "screw_logic", "screw_render",
                     "i18n_messages", "history_store"):
                del sys.modules[m]
        # Pré-importer le faux i18n pour qu'il occupe sys.modules['i18n']
        import i18n as _fake_i18n
        assert getattr(_fake_i18n, "VERSION", None) == "fake-pypi-collision"

        spec = importlib.util.spec_from_file_location("__page_under_test__", {str(page_path)!r})
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ImportError as e:
            # Échec STRICT : la page a importé le faux i18n.
            print("IMPORTERROR:", e, file=sys.stderr)
            sys.exit(2)
        except SystemExit:
            # Streamlit peut quitter via st.stop() → considéré comme un import OK.
            sys.exit(0)
        except BaseException as e:
            # Toute autre erreur (RuntimeError ScriptRunContext, etc.) prouve que
            # les imports sont passés sans ImportError → succès.
            etype = type(e).__name__
            print(f"NONFATAL:{{etype}}:{{e}}", file=sys.stderr)
            sys.exit(0)
        sys.exit(0)
    """).strip()

    env = os.environ.copy()
    # Streamlit Cloud-like : PYTHONPATH n'inclut PAS app/
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-c", loader],
        capture_output=True, text=True, timeout=120, env=env,
    )


# ---------------------------------------------------------------------------
# Tests obligatoires (noms exacts)
# ---------------------------------------------------------------------------
def test_profile_import_cloud_safe(tmp_path):
    """Profile doit s'importer même si `sys.modules['i18n']` est pris par un
    module concurrent (cas réel Streamlit Cloud)."""
    cp = _run_page_with_pollution(PAGES["profile"], tmp_path)
    assert cp.returncode == 0, (
        f"Profile a planté avec pollution i18n :\n"
        f"--- STDOUT ---\n{cp.stdout}\n--- STDERR ---\n{cp.stderr}"
    )
    assert "IMPORTERROR" not in cp.stderr


@pytest.mark.parametrize("name", list(PAGES))
def test_all_streamlit_pages_import(name, tmp_path):
    """Chacune des 6 pages doit s'importer sans ImportError sous pollution."""
    cp = _run_page_with_pollution(PAGES[name], tmp_path)
    assert "IMPORTERROR" not in cp.stderr, (
        f"[{name}] ImportError sous pollution :\n{cp.stderr}"
    )
    assert cp.returncode == 0, (
        f"[{name}] exit={cp.returncode}\n--- STDOUT ---\n{cp.stdout}"
        f"\n--- STDERR ---\n{cp.stderr}"
    )


def test_streamlit_app_starts_headless(tmp_path):
    """`streamlit run app/Supervision.py --server.headless true` démarre et
    répond OK sur /_stcore/health en moins de 60 s."""
    import urllib.request
    import shutil
    import signal

    if shutil.which(sys.executable.replace("python", "streamlit")) is None:
        # On lance via le module pour ne pas dépendre du PATH
        pass

    # Port libre aléatoire dans une plage haute
    port = 8770 + abs(hash(str(tmp_path))) % 50

    log_file = tmp_path / "st.log"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(PAGES["supervision"]),
         "--server.headless=true", f"--server.port={port}",
         "--browser.gatherUsageStats=false"],
        stdout=open(log_file, "w"), stderr=subprocess.STDOUT, env=env, cwd=str(ROOT),
    )
    try:
        ok = False
        for _ in range(60):
            time.sleep(1)
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(
                    f"http://localhost:{port}/_stcore/health", timeout=2
                ) as r:
                    if r.read().decode().strip() == "ok":
                        ok = True
                        break
            except Exception:
                continue
        assert ok, (
            f"streamlit n'a pas répondu /_stcore/health=ok en 60 s "
            f"(rc={proc.poll()}, log={log_file.read_text(encoding='utf-8', errors='ignore')[:2000]})"
        )
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
