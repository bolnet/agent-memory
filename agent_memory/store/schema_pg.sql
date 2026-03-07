-- pgvector schema for Memwright vector search

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_vectors (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mv_memory_id ON memory_vectors(memory_id);

-- IVFFlat index for fast approximate nearest-neighbor search
-- Created separately after initial data load for best quality
-- CREATE INDEX IF NOT EXISTS idx_mv_embedding ON memory_vectors
--     USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
