"""
generate_sql_dump.py — Génère un dump SQL RÉEL de la base de persistance.

Exigence guide RNCP : « Le fichier SQL d'export (dump) ». La persistance durable
de l'application repose sur Supabase (PostgreSQL géré), table `rondol_state`
(schéma réel : voir app/persistence.py). Ce script sérialise l'état applicatif
validé (data/run_state/applied_state.json) en un dump PostgreSQL fidèle au
schéma de production, prêt à être rejoué (`psql -f database/rondol_state_dump.sql`).

Sortie : database/rondol_state_dump.sql

Usage : python scripts/generate_sql_dump.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "run_state" / "applied_state.json"
OUT = ROOT / "database" / "rondol_state_dump.sql"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(STATE.read_text(encoding="utf-8"))
    # Échappement SQL standard : ' -> ''
    payload_json = json.dumps(payload, ensure_ascii=False).replace("'", "''")

    sql = f"""-- =====================================================================
-- Dump SQL — base de persistance de l'application Rondol
-- Moteur : PostgreSQL (Supabase, service géré)
-- Table  : rondol_state  (schéma réel — cf. app/persistence.py)
-- Rôle   : persistance durable du snapshot validé `applied_state`
--          (source unique consommée par toutes les pages de l'app).
-- Le payload applicatif est stocké en JSONB sous la clé 'applied_state'.
-- Rejouable : psql "$DATABASE_URL" -f database/rondol_state_dump.sql
-- =====================================================================

BEGIN;

-- --------------------------------------------------------------------
-- 1. Schéma
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS rondol_state;

CREATE TABLE rondol_state (
    key     TEXT  PRIMARY KEY,          -- clé logique ('applied_state')
    payload JSONB NOT NULL              -- document d'état (semi-structuré)
);

COMMENT ON TABLE  rondol_state          IS 'Persistance durable du snapshot procédé validé (jumeau numérique Rondol).';
COMMENT ON COLUMN rondol_state.key      IS 'Clé logique du document (PRIMARY KEY -> index B-tree implicite).';
COMMENT ON COLUMN rondol_state.payload  IS 'Profil de vis, consignes thermiques, feeders, calibrations — format JSONB.';

-- --------------------------------------------------------------------
-- 2. Données (état applicatif validé réel, exporté de l'application)
--    Upsert idempotent : rejouable sans doublon (cf. Prefer=merge-duplicates).
-- --------------------------------------------------------------------
INSERT INTO rondol_state (key, payload) VALUES
  ('applied_state', '{payload_json}'::jsonb)
ON CONFLICT (key) DO UPDATE SET payload = EXCLUDED.payload;

-- --------------------------------------------------------------------
-- 3. Indexation
--    - PRIMARY KEY(key) : index B-tree implicite servant les lectures
--      par clé (`WHERE key = 'applied_state'`), motif d'accès réel de l'app.
--    - Index GIN JSONB : accélère d'éventuelles requêtes sur le contenu
--      du document (ex. recherche par champ du payload).
-- --------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_rondol_state_payload_gin
    ON rondol_state USING GIN (payload);

COMMIT;

-- --------------------------------------------------------------------
-- 4. Requêtes de vérification (lecture réelle de l'application)
-- --------------------------------------------------------------------
-- Lecture du snapshot validé (motif exact de app/persistence.py::_supabase_load) :
--   SELECT payload FROM rondol_state WHERE key = 'applied_state';
-- Exemple d'accès à un champ JSONB :
--   SELECT payload->'screw_rpm' AS rpm FROM rondol_state WHERE key = 'applied_state';
"""
    OUT.write_text(sql, encoding="utf-8")
    print(f"[OK] dump écrit : {OUT}  ({len(sql)} octets)")
    print(f"     payload sérialisé : {len(payload_json)} caractères JSONB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
