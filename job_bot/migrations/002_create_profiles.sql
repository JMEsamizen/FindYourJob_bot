CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'ru',
    experience_level TEXT,
    preferred_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    work_formats JSONB NOT NULL DEFAULT '[]'::jsonb,
    locations JSONB NOT NULL DEFAULT '[]'::jsonb,
    experience TEXT,
    languages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_roles ON user_profiles USING GIN (preferred_roles);