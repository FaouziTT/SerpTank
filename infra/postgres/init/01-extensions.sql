-- Runs once, on first initialisation of the dev/CI database volume.
-- Roles (separate owner vs. app role for Row-Level Security) arrive in Module 2
-- together with the new baseline migration.
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
