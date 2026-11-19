-- Enable vector search (pgvector) and trigram similarity (pg_trgm)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create a read-only role for the Guarded Text-to-SQL Ask-Data Agent
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'readonly_agent') THEN
      CREATE ROLE readonly_agent WITH LOGIN PASSWORD 'readonly_secret_password';
   END IF;
END
$do$;

-- Revoke all default permissions from readonly_agent
REVOKE ALL ON SCHEMA public FROM readonly_agent;
GRANT USAGE ON SCHEMA public TO readonly_agent;
