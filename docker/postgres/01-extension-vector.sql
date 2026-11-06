-- Se ejecuta una sola vez al crear el volumen de PostgreSQL de desarrollo.
-- A partir de T04 la extension tambien la declara la migracion inicial de Alembic.
CREATE EXTENSION IF NOT EXISTS vector;
