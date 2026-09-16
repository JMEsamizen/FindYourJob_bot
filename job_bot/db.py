from __future__ import annotations

import os
from typing import Any, Iterable

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - PostgreSQL driver is optional until configured.
    psycopg = None  # type: ignore
    Jsonb = lambda value: value  # type: ignore

from config import ANALYSIS_EXEMPT_USER_IDS, ANALYSIS_LIMIT, DATABASE_URL


def is_database_configured() -> bool:
    return bool(DATABASE_URL and psycopg is not None)


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    if psycopg is None:
        raise RuntimeError("psycopg is not installed")
    return psycopg.connect(DATABASE_URL, autocommit=True)


def ensure_database() -> None:
    if not is_database_configured():
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
            for migration_name in sorted(os.listdir(migration_dir)):
                if not migration_name.endswith(".sql"):
                    continue
                with open(os.path.join(migration_dir, migration_name), "r", encoding="utf-8") as migration_file:
                    cur.execute(migration_file.read())


def get_user_profile(user_id: int) -> dict[str, Any] | None:
    if not is_database_configured():
        return None
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                          SELECT user_id, language, experience_level, preferred_roles, work_formats,
                              locations, experience, languages, field, specialization, skills, level,
                              work_format, hours, city, is_active, created_at, updated_at
                    FROM user_profiles WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "user_id": row[0], "language": row[1], "experience_level": row[2],
                    "preferred_roles": row[3], "work_formats": row[4], "locations": row[5],
                    "experience": row[6], "languages": row[7], "field": row[8],
                    "specialization": row[9], "skills": row[10], "level": row[11],
                    "work_format": row[12], "hours": row[13], "city": row[14],
                    "is_active": row[15], "created_at": row[16], "updated_at": row[17],
                }
    except Exception:
        return None


def upsert_user_profile(user_id: int, profile: dict[str, Any]) -> dict[str, Any] | None:
    if not is_database_configured():
        return None
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (
                        user_id, language, experience_level, preferred_roles, work_formats,
                        locations, experience, languages, field, specialization, skills, level,
                        work_format, hours, city, is_active, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        language = EXCLUDED.language,
                        experience_level = EXCLUDED.experience_level,
                        preferred_roles = EXCLUDED.preferred_roles,
                        work_formats = EXCLUDED.work_formats,
                        locations = EXCLUDED.locations,
                        experience = EXCLUDED.experience,
                        languages = EXCLUDED.languages,
                        field = EXCLUDED.field,
                        specialization = EXCLUDED.specialization,
                        skills = EXCLUDED.skills,
                        level = EXCLUDED.level,
                        work_format = EXCLUDED.work_format,
                        hours = EXCLUDED.hours,
                        city = EXCLUDED.city,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                    """,
                    (
                        user_id,
                        profile.get("language", "ru"),
                        profile.get("experience_level"),
                        Jsonb(profile.get("preferred_roles", [])),
                        Jsonb(profile.get("work_formats", [])),
                        Jsonb(profile.get("locations", [])),
                        profile.get("experience"),
                        Jsonb(profile.get("languages", [])),
                        profile.get("field"),
                        profile.get("specialization"),
                        Jsonb(profile.get("skills", [])),
                        profile.get("level"),
                        profile.get("work_format"),
                        profile.get("hours"),
                        profile.get("city"),
                        profile.get("is_active", True),
                    ),
                )
    except Exception:
        return None
    return get_user_profile(user_id)


def get_user_language(user_id: int) -> str | None:
    profile = get_user_profile(user_id)
    return profile.get("language") if profile else None


def set_user_language(user_id: int, language: str) -> str | None:
    if language not in {"ru", "uz", "en"} or not is_database_configured():
        return None
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (user_id, language, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET language = EXCLUDED.language, updated_at = NOW()
                    """,
                    (user_id, language),
                )
    except Exception:
        return None
    return language


def set_user_profile_active(user_id: int, is_active: bool) -> bool:
    if not is_database_configured():
        return False
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (user_id, is_active, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET is_active = EXCLUDED.is_active, updated_at = NOW()
                    """,
                    (user_id, is_active),
                )
                return True
    except Exception:
        return False


def get_recent_vacancies(days: int = 7) -> list[dict[str, Any]]:
    if not is_database_configured():
        return []
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT title, text, date, channel, created_at, url
                    FROM vacancies
                    WHERE created_at >= NOW() - (%s || ' days')::interval
                    ORDER BY created_at DESC
                    """,
                    (str(days),),
                )
                return [
                    {
                        "title": row[0],
                        "text": row[1],
                        "date": row[2],
                        "channel": row[3],
                        "created_at": row[4],
                        "url": row[5],
                    }
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def consume_learning_use(user_id: int, limit: int = 5) -> tuple[bool, int]:
    if not is_database_configured():
        return False, 0
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learning_usage (user_id, uses_count, created_at, updated_at)
                    VALUES (%s, 1, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        uses_count = learning_usage.uses_count + 1,
                        updated_at = NOW()
                    WHERE learning_usage.uses_count < %s
                    RETURNING uses_count
                    """,
                    (user_id, limit),
                )
                row = cur.fetchone()
                return (row is not None, int(row[0]) if row else limit)
    except Exception:
        return False, 0


def upsert_learning_progress(user_id: int, skill: str, status: str = "in_progress", match_percent: int | None = None) -> bool:
    if not is_database_configured():
        return False
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learning_progress (user_id, skill, status, match_percent, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id, skill) DO UPDATE SET
                        status = EXCLUDED.status,
                        match_percent = COALESCE(EXCLUDED.match_percent, learning_progress.match_percent),
                        updated_at = NOW()
                    """,
                    (user_id, skill, status, match_percent),
                )
                return True
    except Exception:
        return False


def get_learning_progress(user_id: int) -> list[dict[str, Any]]:
    if not is_database_configured():
        return []
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT skill, status, match_percent FROM learning_progress WHERE user_id = %s ORDER BY skill",
                    (user_id,),
                )
                return [{"skill": row[0], "status": row[1], "match_percent": row[2]} for row in cur.fetchall()]
    except Exception:
        return []


def get_learning_use_count(user_id: int) -> int:
    if not is_database_configured():
        return 0
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT uses_count FROM learning_usage WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception:
        return 0


def get_learning_materials(skills: list[str], language: str = "ru") -> list[dict[str, str]]:
    if not is_database_configured() or not skills:
        return []
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT skill, title, description, youtube_url, w3_url, language
                    FROM learning_materials
                    WHERE skill = ANY(%s) AND language = %s
                    ORDER BY skill, id
                    """,
                    (skills, language),
                )
                return [
                    {"skill": row[0], "title": row[1], "description": row[2], "url": row[3], "youtube_url": row[3], "w3_url": row[4], "language": row[5]}
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def get_learning_material(skill: str, language: str = "ru") -> dict[str, str] | None:
    materials = get_learning_materials([skill], language)
    return materials[0] if materials else None


def save_vacancies(vacancies: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Upsert vacancies by their stable URL and return a {url: vacancy_id} map.

    Vacancies are stored once and linked to users via user_viewed_vacancies.
    """
    if not is_database_configured():
        return {}
    url_to_id: dict[str, int] = {}
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                for vacancy in vacancies:
                    url = vacancy.get("url", "")
                    if not url:
                        continue
                    cur.execute(
                        """
                        INSERT INTO vacancies (url, title, text, date, channel, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (url) DO UPDATE SET
                            title = EXCLUDED.title,
                            text = EXCLUDED.text,
                            date = EXCLUDED.date,
                            channel = EXCLUDED.channel
                        RETURNING id
                        """,
                        (url, vacancy.get("title", ""), vacancy.get("text", ""),
                         vacancy.get("date", ""), vacancy.get("channel", "")),
                    )
                    row = cur.fetchone()
                    if row:
                        url_to_id[url] = int(row[0])
    except Exception:
        return url_to_id
    return url_to_id


def get_viewed_vacancy_ids(user_id: int) -> set[int]:
    """Return the set of vacancy ids the user has already seen."""
    if not is_database_configured():
        return set()
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT vacancy_id FROM user_viewed_vacancies WHERE user_id = %s",
                    (user_id,),
                )
                return {int(row[0]) for row in cur.fetchall()}
    except Exception:
        return set()


def mark_vacancies_viewed(user_id: int, vacancy_ids: Iterable[int]) -> None:
    """Record that a user has seen a set of vacancies (keeps first viewed_at)."""
    if not is_database_configured():
        return
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                for vacancy_id in set(vacancy_ids):
                    if vacancy_id is None:
                        continue
                    cur.execute(
                        """
                        INSERT INTO user_viewed_vacancies (user_id, vacancy_id, viewed_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (user_id, vacancy_id) DO NOTHING
                        """,
                        (user_id, vacancy_id),
                    )
    except Exception:
        pass


def get_user_viewed_vacancies(user_id: int) -> list[dict[str, Any]]:
    """Return vacancies the user has viewed, newest first (by viewed_at)."""
    if not is_database_configured():
        return []
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT v.url, v.title, v.text, v.date, v.channel, uvv.viewed_at
                    FROM user_viewed_vacancies uvv
                    JOIN vacancies v ON v.id = uvv.vacancy_id
                    WHERE uvv.user_id = %s
                    ORDER BY uvv.viewed_at DESC, v.id DESC
                    """,
                    (user_id,),
                )
                return [
                    {
                        "url": row[0], "title": row[1], "text": row[2],
                        "date": row[3], "channel": row[4], "viewed_at": row[5],
                    }
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def clear_viewed_vacancies(user_id: int) -> None:
    """Delete the user's viewing history.

    After that the previously seen vacancies are offered again on the next search.
    """
    if not is_database_configured():
        return
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_viewed_vacancies WHERE user_id = %s", (user_id,))
    except Exception:
        pass


def consume_analysis_use(user_id: int, limit: int = ANALYSIS_LIMIT) -> tuple[bool, int]:
    """Try to consume one use of 'Анализ вакансии'.

    Returns (allowed, uses_count). allowed is False (without consuming) once the
    user has reached the per-user limit.
    """
    if not is_database_configured():
        return False, 0
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_usage (user_id, uses_count, created_at, updated_at)
                    VALUES (%s, 1, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        uses_count = analysis_usage.uses_count + 1,
                        updated_at = NOW()
                    WHERE analysis_usage.uses_count < %s
                    RETURNING uses_count
                    """,
                    (user_id, limit),
                )
                row = cur.fetchone()
                return (row is not None, int(row[0]) if row else limit)
    except Exception:
        return False, 0


def get_analysis_use_count(user_id: int) -> int:
    if not is_database_configured():
        return 0
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT uses_count FROM analysis_usage WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception:
        return 0


def analysis_limit_allows(user_id: int) -> bool:
    """Centralized gate for the 'Анализ вакансии' limit.

    Exempt accounts bypass the limit entirely; all other users consume one use.
    """
    if user_id in ANALYSIS_EXEMPT_USER_IDS:
        return True
    allowed, _ = consume_analysis_use(user_id, ANALYSIS_LIMIT)
    return allowed
