-- enable pgvector extension (requires Postgres admin)
CREATE EXTENSION IF NOT EXISTS vector;

-- main table for video embeddings
CREATE TABLE IF NOT EXISTS video_embeddings (
  video_id TEXT PRIMARY KEY,
  channel_id TEXT,
  title TEXT,
  description TEXT,
  published_at TIMESTAMP,
  embedding vector(384),
  metadata jsonb
);

-- recommended ANN index (ivfflat). Tune lists value for dataset size.
-- Note: create index AFTER inserting some rows (ivfflat needs to be trained)
CREATE INDEX IF NOT EXISTS video_embeddings_embedding_idx ON video_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
