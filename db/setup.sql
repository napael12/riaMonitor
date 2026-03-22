-- =============================================================
-- RIA Monitor — Database & User Setup
-- Run as postgres superuser:
--   psql -U postgres -h 127.0.0.1 -f db/setup.sql
-- =============================================================

-- Create user if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ria') THEN
    CREATE USER ria WITH PASSWORD 'ria';
    RAISE NOTICE 'User ria created.';
  ELSE
    ALTER USER ria WITH PASSWORD 'ria';
    RAISE NOTICE 'User ria already exists — password updated.';
  END IF;
END
$$;

-- Create database if not exists
SELECT 'CREATE DATABASE ria OWNER ria'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ria') \gexec

-- Transfer ownership (idempotent)
ALTER DATABASE ria OWNER TO ria;

-- Connect to ria database and grant schema privileges
\connect ria

GRANT ALL ON SCHEMA public TO ria;
ALTER SCHEMA public OWNER TO ria;

\echo 'Setup complete. User ria owns database ria with full schema access.'
