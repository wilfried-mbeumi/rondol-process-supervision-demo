-- =====================================================================
-- Authentification & traçabilité des connexions — schéma SQL
-- Moteur : PostgreSQL (Supabase, service géré)
-- Tables : app_users (utilisateurs) · login_history (journal des connexions)
-- Cf. app/auth.py — hash PBKDF2, jamais de mot de passe en clair.
-- Rejouable : psql "$DATABASE_URL" -f database/auth_tables.sql
-- =====================================================================

BEGIN;

-- --------------------------------------------------------------------
-- 1. Utilisateurs — mot de passe stocké UNIQUEMENT sous forme de hash
--    PBKDF2-HMAC-SHA256 (200 000 itérations) + sel aléatoire par compte.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_users (
    email      TEXT PRIMARY KEY,                 -- identifiant de connexion
    salt       TEXT NOT NULL,                    -- sel hexadécimal (par compte)
    pw_hash    TEXT NOT NULL,                    -- PBKDF2(pw, salt) hexadécimal
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  app_users         IS 'Comptes autorisés de la plateforme Rondol (mots de passe hashés, jamais en clair).';
COMMENT ON COLUMN app_users.pw_hash IS 'PBKDF2-HMAC-SHA256, 200000 itérations — cf. app/auth.py.';

-- --------------------------------------------------------------------
-- 2. Journal des connexions — une ligne par tentative (succès ou échec).
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_history (
    id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email   TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    source  TEXT DEFAULT 'app',
    ts      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE login_history IS 'Historique des tentatives de connexion (traçabilité des accès).';

CREATE INDEX IF NOT EXISTS idx_login_history_ts ON login_history (ts DESC);

-- --------------------------------------------------------------------
-- 3. Politiques d'accès (Row Level Security).
--    Supabase active la RLS par défaut : sans politique, toute écriture
--    de la clé publiable est refusée (erreur 401 / 42501). L'application
--    (client REST avec la clé publiable) doit pouvoir :
--      - LIRE app_users     (vérification du mot de passe, hash PBKDF2),
--      - LIRE/INSÉRER app_users (seed du compte),
--      - INSÉRER + LIRE login_history (journalisation + page Compte).
--    Périmètre : démonstration mono-profil ; règles permissives assumées.
--    Note de sécurité : la lecture d'app_users expose les condensats
--    PBKDF2 (non réversibles), jamais de mot de passe en clair.
-- --------------------------------------------------------------------
ALTER TABLE app_users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_users_all     ON app_users;
DROP POLICY IF EXISTS history_insert    ON login_history;
DROP POLICY IF EXISTS history_read      ON login_history;

CREATE POLICY app_users_all   ON app_users     FOR ALL    USING (true) WITH CHECK (true);
CREATE POLICY history_insert  ON login_history FOR INSERT WITH CHECK (true);
CREATE POLICY history_read    ON login_history FOR SELECT USING (true);

COMMIT;

-- --------------------------------------------------------------------
-- 4. Vérification
-- --------------------------------------------------------------------
--   SELECT email, created_at FROM app_users;
--   SELECT email, success, ts FROM login_history ORDER BY ts DESC LIMIT 20;
