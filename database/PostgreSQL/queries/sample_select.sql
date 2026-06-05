-- Sample SELECT queries for screen-level checks.

-- 기록 열람실: 괴담 목록
SELECT id, title, region, category, preview
FROM horror_stories
ORDER BY id
LIMIT 20;

-- 기록 열람실: 괴이 존재 목록
SELECT id, name, origin, source_site
FROM myth_entities
ORDER BY id
LIMIT 20;

-- 금기 자료실: 미신/금기 문장 목록
SELECT id, content, category, region
FROM superstitions
ORDER BY id
LIMIT 20;

-- 열린 게시판: 최신 게시글
SELECT id, user_id, board_type, title, region, view_count, created_at
FROM posts
ORDER BY created_at DESC NULLS LAST, id DESC
LIMIT 20;

-- 나의 보관함: 사용자가 저장한 생성 괴담
SELECT b.id AS bookmark_id, b.user_id, s.id AS story_id, s.title, b.created_at
FROM generated_story_bookmarks b
JOIN generated_stories s ON s.id = b.generated_story_id
WHERE b.user_id = 1
ORDER BY b.created_at DESC NULLS LAST, b.id DESC;

-- 나의 보관함: 사용자가 저장한 게시글
SELECT b.id AS bookmark_id, b.user_id, p.id AS post_id, p.title, b.created_at
FROM post_bookmarks b
JOIN posts p ON p.id = b.post_id
WHERE b.user_id = 1
ORDER BY b.created_at DESC NULLS LAST, b.id DESC;
