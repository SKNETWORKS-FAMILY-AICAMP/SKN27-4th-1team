-- pgvector schema for semantic search.
-- Embedding model: nlpai-lab/KURE-v1 via Hugging Face sentence-transformers
-- Vector dimension: 1024
-- Run from project root:
-- Get-Content database\PostgreSQL\pgvector\schema_pgvector.sql | docker compose exec -T postgres psql -U postgres -d goei_sillok

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS record_embeddings (
    id BIGSERIAL PRIMARY KEY,
    source_table VARCHAR(100) NOT NULL,
    source_id BIGINT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_record_embeddings_source_chunk
        UNIQUE (source_table, source_id, chunk_index),
    CONSTRAINT ck_record_embeddings_chunk_index
        CHECK (chunk_index >= 0)
);

CREATE INDEX IF NOT EXISTS idx_record_embeddings_source
    ON record_embeddings (source_table, source_id);

CREATE INDEX IF NOT EXISTS idx_record_embeddings_metadata
    ON record_embeddings USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_record_embeddings_embedding_hnsw
    ON record_embeddings USING hnsw (embedding vector_cosine_ops);
