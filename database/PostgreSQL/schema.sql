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

CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth_user(id),
    board_type VARCHAR(30),
    title TEXT NOT NULL,
    region VARCHAR(100),
    content TEXT NOT NULL,
    view_count INTEGER DEFAULT 0,
    visibility VARCHAR(30),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
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
    post_id BIGINT NOT NULL REFERENCES posts(id),
    memo TEXT,
    created_at TIMESTAMPTZ,
    UNIQUE (user_id, post_id)
);
