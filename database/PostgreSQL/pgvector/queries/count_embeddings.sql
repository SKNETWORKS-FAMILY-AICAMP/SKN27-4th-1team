SELECT
    source_table,
    COUNT(*) AS chunk_count,
    COUNT(DISTINCT source_id) AS source_count
FROM record_embeddings
GROUP BY source_table
ORDER BY source_table;

SELECT COUNT(*) AS total_embedding_chunks
FROM record_embeddings;

