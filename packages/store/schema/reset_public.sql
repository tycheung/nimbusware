-- Wipe all objects in the public schema so greenfield postgres.sql can re-apply cleanly.
-- Requires privileges to drop/create schema public on the target database.
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO public;
