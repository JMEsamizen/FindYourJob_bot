CREATE TABLE IF NOT EXISTS learning_usage (
    user_id BIGINT PRIMARY KEY,
    uses_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_progress (
    user_id BIGINT NOT NULL,
    skill TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress',
    match_percent INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, skill)
);

CREATE INDEX IF NOT EXISTS idx_learning_progress_user ON learning_progress (user_id, status);
