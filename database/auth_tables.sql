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
-- 3. Politiques d'accès (si la Row Level Security est activée sur le
--    projet Supabase). La clé publiable/anon doit pouvoir :
--      - LIRE app_users (vérification du mot de passe côté application),
--      - INSÉRER dans login_history (journalisation),
--      - LIRE login_history (page Compte).
--    Adapter selon ta politique de sécurité ; pour une démonstration
--    mono-utilisateur, des règles permissives suffisent.
-- --------------------------------------------------------------------
-- ALTER TABLE app_users     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE login_history ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY app_users_read   ON app_users     FOR SELECT USING (true);
-- CREATE POLICY history_insert   ON login_history FOR INSERT WITH CHECK (true);
-- CREATE POLICY history_read     ON login_history FOR SELECT USING (true);

COMMIT;

-- --------------------------------------------------------------------
-- 4. Vérification
-- --------------------------------------------------------------------
--   SELECT email, created_at FROM app_users;
--   SELECT email, success, ts FROM login_history ORDER BY ts DESC LIMIT 20;
