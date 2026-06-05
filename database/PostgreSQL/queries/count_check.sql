-- PostgreSQL seed result count checks.

SELECT 'horror_stories' AS table_name, COUNT(*) AS row_count
FROM horror_stories
UNION ALL
SELECT 'myth_entities' AS table_name, COUNT(*) AS row_count
FROM myth_entities
UNION ALL
SELECT 'superstitions' AS table_name, COUNT(*) AS row_count
FROM superstitions
UNION ALL
SELECT 'generated_stories' AS table_name, COUNT(*) AS row_count
FROM generated_stories
UNION ALL
SELECT 'post_post' AS table_name, COUNT(*) AS row_count
FROM post_post
UNION ALL
SELECT 'post_like' AS table_name, COUNT(*) AS row_count
FROM post_like
UNION ALL
SELECT 'accounts_bookmark' AS table_name, COUNT(*) AS row_count
FROM accounts_bookmark
UNION ALL
SELECT 'generated_story_bookmarks' AS table_name, COUNT(*) AS row_count
FROM generated_story_bookmarks
UNION ALL
SELECT 'post_bookmarks' AS table_name, COUNT(*) AS row_count
FROM post_bookmarks
ORDER BY table_name;

-- Expected initial seed counts:
-- horror_stories: 224
-- myth_entities: 1016
-- superstitions: 214
