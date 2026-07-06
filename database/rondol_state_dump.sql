-- =====================================================================
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
  ('applied_state', '{"timestamp_iso": "2026-06-11T08:32:53", "label": "test", "screw_config": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 7, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "screw_rpm": 120.0, "zone_temps_C": {"Z1": 25.0, "Z2": 60.0, "Z3": 80.0, "Z4": 90.0, "Z5": 95.0, "Z6": 95.0, "Z7": 90.0, "Z8": 85.0, "die": 80.0, "die2": 75.0, "die3": 70.0, "die4": 65.0}, "n_die_zones": 1, "feeders": [{"feeder_id": 1, "enabled": true, "label": "Main", "material_id": "granules", "position": "Z0", "speed_rpm": 120.0, "mass_flow_g_per_min": 30.0, "density_g_per_cm3": 0.55, "thermal_expansion_per_K": 7e-05, "polymer_name": "", "t_degradation_C": null, "tga_onset_C": null, "viscosity_pa_s": null, "t_melt_C": null, "t_glass_C": null}, {"feeder_id": 2, "enabled": false, "label": "", "material_id": "powder", "position": "Z3", "speed_rpm": 0.0, "mass_flow_g_per_min": 0.0, "density_g_per_cm3": 0.3, "thermal_expansion_per_K": 5e-05, "polymer_name": "", "t_degradation_C": null, "tga_onset_C": null, "viscosity_pa_s": null, "t_melt_C": null, "t_glass_C": null}, {"feeder_id": 3, "enabled": false, "label": "", "material_id": "powder", "position": "Z3", "speed_rpm": 0.0, "mass_flow_g_per_min": 0.0, "density_g_per_cm3": 0.3, "thermal_expansion_per_K": 5e-05, "polymer_name": "", "t_degradation_C": null, "tga_onset_C": null, "viscosity_pa_s": null, "t_melt_C": null, "t_glass_C": null}, {"feeder_id": 4, "enabled": false, "label": "", "material_id": "powder", "position": "Z3", "speed_rpm": 0.0, "mass_flow_g_per_min": 0.0, "density_g_per_cm3": 0.3, "thermal_expansion_per_K": 5e-05, "polymer_name": "", "t_degradation_C": null, "tga_onset_C": null, "viscosity_pa_s": null, "t_melt_C": null, "t_glass_C": null}, {"feeder_id": 5, "enabled": false, "label": "", "material_id": "powder", "position": "Z3", "speed_rpm": 0.0, "mass_flow_g_per_min": 0.0, "density_g_per_cm3": 0.3, "thermal_expansion_per_K": 5e-05, "polymer_name": "", "t_degradation_C": null, "tga_onset_C": null, "viscosity_pa_s": null, "t_melt_C": null, "t_glass_C": null}], "torque_pct": null, "pressure_die_bar": null, "feeder_calibrations": {}}'::jsonb)
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
