DROP TABLE IF EXISTS notification_delivery;
DROP TABLE IF EXISTS notification_settings;

CREATE TABLE IF NOT EXISTS learning_materials (
    id BIGSERIAL PRIMARY KEY,
    skill TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    youtube_url TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'ru',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (skill, title, language)
);

CREATE INDEX IF NOT EXISTS idx_learning_materials_skill_language
    ON learning_materials (skill, language);

DELETE FROM learning_materials
WHERE youtube_url IN (
    'https://www.youtube.com/results?search_query=docker+basics',
    'https://www.youtube.com/results?search_query=docker+containers',
    'https://www.youtube.com/results?search_query=docker+compose',
    'https://www.youtube.com/results?search_query=python+basics',
    'https://www.youtube.com/results?search_query=rest+api+basics',
    'https://www.youtube.com/results?search_query=postgresql+basics'
);

INSERT INTO learning_materials (skill, title, description, youtube_url, language)
VALUES
    ('python', 'Python for Beginners — Full Course', '', 'https://www.youtube.com/watch?v=eWRfhZUzrAc', 'ru'),
    ('javascript', 'Learn JavaScript — Full Course for Beginners', '', 'https://www.youtube.com/watch?v=PkZNo7MFNFg', 'ru'),
    ('html', 'HTML Full Course — Build a Website Tutorial', '', 'https://www.youtube.com/watch?v=pQN-pnXPaVg', 'ru'),
    ('css', 'CSS Tutorial — Full Course for Beginners', '', 'https://www.youtube.com/watch?v=OXGznpKZ_sA', 'ru'),
    ('sql', 'SQL Tutorial — Full Database Course for Beginners', '', 'https://www.youtube.com/watch?v=HXV3zeQKqGY', 'ru'),
    ('git', 'Git & GitHub Crash Course for Beginners', '', 'https://www.youtube.com/watch?v=mAFoROnOfHs', 'ru'),
    ('docker', 'Docker Tutorial for Beginners — Full DevOps Course', '', 'https://www.youtube.com/watch?v=fqMOX6JJhGo', 'ru'),
    ('data_structures', 'Data Structures Full Course', '', 'https://www.youtube.com/watch?v=B31LgI4Y4DQ', 'ru'),
    ('django', 'Django Tutorial for Beginners', '', 'https://www.youtube.com/watch?v=rHux0gMZ3Eg', 'ru'),
    ('react', 'React Course — Beginner''s Tutorial', '', 'https://www.youtube.com/watch?v=bMknfKXIFA8', 'ru'),
    ('nodejs', 'Node.js and Express.js — Full Course', '', 'https://www.youtube.com/watch?v=Oe421EPjeBE', 'ru'),
    ('postgresql', 'PostgreSQL Tutorial for Beginners', '', 'https://www.youtube.com/watch?v=qw--VYLpxG4', 'ru'),
    ('linux', 'Linux for Beginners — Full Course', '', 'https://www.youtube.com/watch?v=sWbUDq4S6Y8', 'ru'),
    ('rest_api', 'REST API Tutorial — Full Course for Beginners', '', 'https://www.youtube.com/watch?v=WXsD0ZgxjRw', 'ru'),
    ('html_css', 'Web Development with HTML & CSS — Full Course', '', 'https://www.youtube.com/watch?v=dX8396ZmSPk', 'ru')
ON CONFLICT (skill, title, language) DO NOTHING;