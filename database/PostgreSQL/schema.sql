-- PostgreSQL schema reference for Goei Sillok MVP.
-- In the Django project, models.py and migrations should create the actual tables.
-- This file is for ERDCloud import, documentation, and implementation reference.

CREATE TABLE auth_user (
    id BIGINT PRIMARY KEY,
    username VARCHAR(150) NOT NULL,
    email VARCHAR(254)
);

CREATE TABLE horror_stories (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    source_ref_id VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    language VARCHAR(20) DEFAULT 'ko',
    region VARCHAR(100),
    url TEXT,
    preview TEXT,
    content TEXT NOT NULL,
    category VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE (source, source_ref_id)
);

CREATE TABLE myth_entities (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'ultimate_global_mythology_1000',
    source_ref_id VARCHAR(100) NOT NULL,
    name TEXT NOT NULL,
    origin VARCHAR(255),
    description TEXT,
    behavior TEXT,
    weakness TEXT,
    history TEXT,
    signs TEXT,
    survival_rules JSONB DEFAULT '[]'::jsonb,
    source_site VARCHAR(100),
    source_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE (source, source_ref_id)
);

CREATE TABLE superstitions (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'misin',
    source_ref_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    region VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE (source, source_ref_id)
);

CREATE TABLE dcinside_posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'dcinside_gongpow',
    source_ref_id VARCHAR(100) NOT NULL,
    category VARCHAR(15) NOT NULL,
    title VARCHAR(200) NOT NULL,
    region VARCHAR(100) DEFAULT '한국',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    UNIQUE (source, source_ref_id)
);

CREATE TABLE generated_stories (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    region VARCHAR(100),
    place TEXT,
    entity_type VARCHAR(100),
    taboo_text TEXT,
    event_time VARCHAR(100),
    condition TEXT,
    ending TEXT,
    title TEXT,
    content TEXT,
    status VARCHAR(30),
    visibility VARCHAR(30),
    prompt_payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE post_post (
    id BIGSERIAL PRIMARY KEY,
    author_id BIGINT REFERENCES auth_user(id),
    category VARCHAR(15) NOT NULL DEFAULT 'WITNESS',
    title VARCHAR(200) NOT NULL,
    region VARCHAR(100) DEFAULT '지역 미상',
    body TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ
);

CREATE TABLE post_like (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    post_id BIGINT NOT NULL REFERENCES post_post(id),
    created_at TIMESTAMPTZ,
    UNIQUE (user_id, post_id)
);

CREATE TABLE accounts_bookmark (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    horror_id VARCHAR(100) NOT NULL,
    horror_title VARCHAR(255) NOT NULL,
    horror_type VARCHAR(50) DEFAULT 'Story',
    created_at TIMESTAMPTZ,
    UNIQUE (user_id, horror_id)
);

CREATE TABLE generated_story_bookmarks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    generated_story_id BIGINT NOT NULL REFERENCES generated_stories(id),
    memo TEXT,
    created_at TIMESTAMPTZ,
    UNIQUE (user_id, generated_story_id)
);

CREATE TABLE post_bookmarks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    post_id BIGINT NOT NULL REFERENCES post_post(id),
    memo TEXT,
    created_at TIMESTAMPTZ,
    UNIQUE (user_id, post_id)
);
