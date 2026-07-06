"""
verify_supabase.py — Vérifie que la persistance DURABLE Supabase est réellement
                     active et fonctionnelle (round-trip écriture/lecture réel).

À lancer APRÈS avoir configuré les secrets (en local `.streamlit/secrets.toml`
section [supabase], ou variables d'env `RONDOL_SUPABASE_URL`/`RONDOL_SUPABASE_KEY`,
ou dans Streamlit Cloud > Settings > Secrets).

Objectif de preuve RNCP :
  backend_name() == 'supabase'  ET  is_durable() == True  ET  round-trip OK.

Le script :
  1. lit la config via app/persistence.py (jamais d'affichage du secret) ;
  2. écrit une clé de TEST dédiée ('__healthcheck__') — n'altère PAS applied_state ;
  3. relit la valeur écrite ;
  4. supprime la clé de test (nettoyage) ;
  5. imprime un verdict clair. La clé API n'est JAMAIS affichée (masquée).

Usage : python scripts/verify_supabase.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import persistence as P  # noqa: E402

TEST_KEY = "__healthcheck__"


def _mask(s: str) -> str:
    if not s:
        return "(vide)"
    return (s[:4] + "…" + s[-2:]) if len(s) > 8 else "***"


def main() -> int:
    print("=== Vérification persistance ===")
    print("backend_name() :", P.backend_name())
    print("is_durable()   :", P.is_durable())

    cfg = P._supabase_config()  # type: ignore[attr-defined]
    if cfg is None:
        print("\n[RÉSULTAT] Secrets Supabase NON configurés → backend local-json (non durable).")
        print("Configurez les secrets puis relancez (voir secrets.toml.example).")
        return 1

    print("Supabase URL   :", cfg["url"])
    print("Supabase key   :", _mask(cfg["key"]), "(masquée)")
    print("Table          :", cfg["table"])

    import requests  # noqa: PLC0415
    base = f"{cfg['url']}/rest/v1/{cfg['table']}"
    headers = {
        "apikey": cfg["key"],
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    probe = "PROBE-RNCP-VERIFY"
    try:
        w = requests.post(base, headers=headers,
                          json=[{"key": TEST_KEY, "payload": {"probe": probe}}], timeout=6)
        ok_w = 200 <= w.status_code < 300
        r = requests.get(base, headers={"apikey": cfg["key"],
                         "Authorization": f"Bearer {cfg['key']}"},
                         params={"key": f"eq.{TEST_KEY}", "select": "payload"}, timeout=6)
        read_val = None
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            read_val = r.json()[0].get("payload", {}).get("probe")
        # nettoyage
        requests.delete(base, headers={"apikey": cfg["key"],
                        "Authorization": f"Bearer {cfg['key']}"},
                        params={"key": f"eq.{TEST_KEY}"}, timeout=6)
    except Exception as exc:
        print(f"\n[ERREUR] Appel Supabase échoué : {exc}")
        print("Vérifiez l'URL, la clé, et que la table existe (database/rondol_state_dump.sql).")
        return 2

    print("\n--- Round-trip ---")
    print("écriture HTTP 2xx :", ok_w)
    print("valeur relue      :", read_val, "| attendue :", probe)
    success = ok_w and read_val == probe and P.is_durable() and P.backend_name() == "supabase"
    print("\n[RÉSULTAT]", "✅ PERSISTANCE SUPABASE DURABLE CONFIRMÉE" if success
          else "❌ ÉCHEC — voir messages ci-dessus")
    return 0 if success else 3


if __name__ == "__main__":
    raise SystemExit(main())
