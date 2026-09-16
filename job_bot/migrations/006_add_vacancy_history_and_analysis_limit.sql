-- Store fetched vacancies once, keyed by their stable public URL.
CREATE TABLE IF NOT EXISTS vacancies (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Links a user to vacancies they have already received/seen.
CREATE TABLE IF NOT EXISTS user_viewed_vacancies (
    user_id BIGINT NOT NULL,
    vacancy_id BIGINT NOT NULL REFERENCES vacancies (id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, vacancy_id)
);

CREATE INDEX IF NOT EXISTS idx_user_viewed_vacancies_user
    ON user_viewed_vacancies (user_id, viewed_at);

-- Per-user analysis usage counter.
CREATE TABLE IF NOT EXISTS analysis_usage (
    user_id BIGINT PRIMARY KEY,
    uses_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);