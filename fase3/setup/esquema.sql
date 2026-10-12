-- El esquema de la fase 3. Se aplica una sola vez:
--
--     psql "$DATABASE_URL" -f setup/esquema.sql
--
-- Es idempotente: correrlo dos veces no rompe nada ni borra datos.

CREATE TABLE IF NOT EXISTS conversacion (
  id        BIGSERIAL   PRIMARY KEY,
  titulo    TEXT        NOT NULL,
  modelo    TEXT        NOT NULL,
  creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mensaje (
  id              BIGSERIAL   PRIMARY KEY,
  conversacion_id BIGINT      NOT NULL REFERENCES conversacion(id) ON DELETE CASCADE,
  rol             TEXT        NOT NULL CHECK (rol IN ('user', 'assistant')),
  contenido       TEXT        NOT NULL,
  tokens          INTEGER,
  creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mensaje_por_conversacion ON mensaje (conversacion_id, id);
