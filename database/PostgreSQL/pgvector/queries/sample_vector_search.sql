-- This sample uses the first saved embedding as a temporary query vector.
-- After search_vectors.py is created, use that script for real query text search.

WITH query_vector AS (
    SELECT embedding AS query_embedding
    FROM record_embeddings
    LIMIT 1
)
SELECT
    record_embeddings.source_table,
    record_embeddings.source_id,
    record_embeddings.chunk_index,
    record_embeddings.title,
    LEFT(record_embeddings.content, 160) AS content_preview,
    1 - (record_embeddings.embedding <=> query_vector.query_embedding) AS similarity
FROM record_embeddings, query_vector
ORDER BY record_embeddings.embedding <=> query_vector.query_embedding
LIMIT 10;
