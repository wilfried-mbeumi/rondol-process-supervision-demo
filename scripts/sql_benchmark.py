"""
sql_benchmark.py — Comparaison du temps d'exécution des requêtes
                   entre table NON optimisée et table optimisée (indexée).

Exigence guide RNCP : « comparaison temps d'exécution des requêtes entre les
tables optimisées et non-optimisées ». La table de production `rondol_state` ne
contient qu'une ligne (clé 'applied_state') ; l'effet d'un index n'y est pas
mesurable. Ce micro-benchmark REPRODUCTIBLE reproduit fidèlement le schéma et le
motif d'accès réel (`SELECT payload WHERE key = ?`) à plus grande échelle, sur
SQLite (moteur SQL embarqué, sans dépendance), afin de DÉMONTRER l'effet de
l'indexation — le principe (B-tree vs scan séquentiel) est identique sous
PostgreSQL/Supabase.

Sortie : reports/sql_benchmark.json (+ tableau imprimé)

Usage : python scripts/sql_benchmark.py
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "sql_benchmark.json"

N_ROWS = 50_000        # volumétrie simulée (montée en charge réaliste)
N_QUERIES = 2_000      # nombre de lectures chronométrées
TARGET_KEY = "applied_state"


def build_table(con, indexed: bool):
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS rondol_state")
    cur.execute("CREATE TABLE rondol_state (key TEXT, payload TEXT)")
    rows = [(f"snapshot_{i:06d}", f'{{"i": {i}}}') for i in range(N_ROWS)]
    # La clé réellement lue par l'application
    rows.append((TARGET_KEY, '{"screw_rpm": 150, "real": true}'))
    cur.executemany("INSERT INTO rondol_state (key, payload) VALUES (?, ?)", rows)
    if indexed:
        # Optimisée : index B-tree sur la clé lue (équivaut au PRIMARY KEY Postgres)
        cur.execute("CREATE INDEX idx_key ON rondol_state(key)")
    con.commit()


def time_lookups(con) -> float:
    cur = con.cursor()
    t0 = time.perf_counter()
    for _ in range(N_QUERIES):
        cur.execute("SELECT payload FROM rondol_state WHERE key = ?", (TARGET_KEY,))
        cur.fetchone()
    return (time.perf_counter() - t0) * 1000.0  # ms total


def bench(indexed: bool) -> dict:
    con = sqlite3.connect(":memory:")
    build_table(con, indexed=indexed)
    # chauffe
    time_lookups(con)
    total_ms = time_lookups(con)
    con.close()
    return {
        "indexed": indexed,
        "n_rows": N_ROWS + 1,
        "n_queries": N_QUERIES,
        "total_ms": round(total_ms, 2),
        "avg_query_ms": round(total_ms / N_QUERIES, 5),
    }


def main() -> int:
    raw = bench(indexed=False)
    opt = bench(indexed=True)
    speedup = (raw["avg_query_ms"] / opt["avg_query_ms"]) if opt["avg_query_ms"] else None
    result = {
        "engine": "SQLite (in-memory) — schéma et motif d'accès de rondol_state",
        "query": "SELECT payload FROM rondol_state WHERE key = 'applied_state'",
        "non_optimisee": raw,
        "optimisee_index_btree": opt,
        "speedup_x": round(speedup, 1) if speedup else None,
        "interpretation": (
            "Sans index, le moteur effectue un balayage séquentiel (O(n)) des "
            f"{raw['n_rows']} lignes à chaque lecture. Avec un index B-tree sur "
            "la clé (équivalent du PRIMARY KEY PostgreSQL utilisé en production), "
            "la lecture devient logarithmique (O(log n)). Le motif d'accès réel "
            "de l'application est une lecture par clé unique : il bénéficie "
            "directement de cette optimisation."
        ),
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n[OK] écrit : {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
