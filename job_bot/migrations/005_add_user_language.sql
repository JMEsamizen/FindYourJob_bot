ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'ru';

ALTER TABLE user_profiles
    ALTER COLUMN experience_level DROP NOT NULL,
    ALTER COLUMN experience DROP NOT NULL;