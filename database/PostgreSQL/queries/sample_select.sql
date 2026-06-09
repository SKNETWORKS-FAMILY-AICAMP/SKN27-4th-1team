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

-- DCInside 수집 게시글: 목격담/창작담 초기 데이터
SELECT id, category, region, LEFT(content, 120) AS content_preview, created_at
FROM dcinside_posts
WHERE is_active = true
ORDER BY id DESC
LIMIT 20;

-- 열린 게시판: 최신 게시글
SELECT id, author_id, category, title, region, views, likes, created_at
FROM post_post
ORDER BY created_at DESC NULLS LAST, id DESC
LIMIT 20;

-- 열린 게시판: 좋아요 기록
SELECT id, user_id, post_id, created_at
FROM post_like
ORDER BY created_at DESC NULLS LAST, id DESC
LIMIT 20;

-- 나의 보관함: 외부/Neo4j 괴담 자료
SELECT id, user_id, horror_id, horror_title, horror_type, created_at
FROM accounts_bookmark
ORDER BY created_at DESC NULLS LAST, id DESC
LIMIT 20;

-- 나의 보관함: 사용자가 저장한 AI 생성 괴담
SELECT b.id AS bookmark_id, b.user_id, s.id AS story_id, s.title, b.created_at
FROM generated_story_bookmarks b
JOIN generated_stories s ON s.id = b.generated_story_id
WHERE b.user_id = 1
ORDER BY b.created_at DESC NULLS LAST, b.id DESC;

-- 나의 보관함: 사용자가 저장한 게시글
SELECT b.id AS bookmark_id, b.user_id, p.id AS post_id, p.title, b.created_at
FROM post_bookmarks b
JOIN post_post p ON p.id = b.post_id
WHERE b.user_id = 1
ORDER BY b.created_at DESC NULLS LAST, b.id DESC;
