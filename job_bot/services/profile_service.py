from __future__ import annotations

from typing import Any

from profile import LOCATIONS, PROFILE_FIELDS, WORK_FORMATS, LEVELS, EXPERIENCE, HOURS, LANGUAGES, ROLES
from repositories.profile_repository import get_user_profile, upsert_user_profile


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def profile_complete(data: dict[str, Any]) -> bool:
    if any(key in data for key in ("field", "specialization", "skills")):
        return bool(
            data.get("field")
            and data.get("specialization")
            and data.get("skills")
            and data.get("level")
            and data.get("work_format")
            and data.get("experience")
            and data.get("hours")
        )
    return all(data.get(key) for key in ("experience_level", "preferred_roles", "work_formats", "locations", "experience", "languages"))


def display_profile(profile: dict[str, Any]) -> str:
    def labels(values: list[str], source: dict[str, str]) -> str:
        if not values:
            return "—"
        return ", ".join(source.get(value, value) for value in values)

    if profile.get("field") or profile.get("specialization"):
        field = profile.get("field") or "other"
        specialization = profile.get("specialization") or "other"
        skills = _as_list(profile.get("skills", []))
        work_format = profile.get("work_format") or profile.get("work_formats", ["any"])[0]
        city = profile.get("city") or (profile.get("locations") or ["any"])[0]
        return (
            "👤 Профиль\n\n"
            f"🔹 Сфера: {PROFILE_FIELDS.get(field, {}).get('label', field)}\n"
            f"🎯 Специализация: {PROFILE_FIELDS.get(field, {}).get('specializations', {}).get(specialization, specialization)}\n"
            f"💡 Навыки: {', '.join(skills) if skills else '—'}\n"
            f"📊 Уровень: {LEVELS.get(profile.get('level'), profile.get('level', 'Не знаю'))}\n"
            f"💼 Формат: {WORK_FORMATS.get(work_format, work_format)}\n"
            f"⏳ Опыт: {EXPERIENCE.get(profile.get('experience'), profile.get('experience'))}\n"
            f"🕒 Часы: {HOURS.get(profile.get('hours'), profile.get('hours'))}\n"
            f"📍 Город: {LOCATIONS.get(city, city) if city else '—'}"
        )

    preferred_roles = _as_list(profile.get("preferred_roles", []))
    work_formats = _as_list(profile.get("work_formats", []))
    locations = _as_list(profile.get("locations", []))
    languages = _as_list(profile.get("languages", []))
    return (
        "👤 Мой профиль\n\n"
        f"🎯 Направления: {labels(preferred_roles, ROLES)}\n"
        f"💻 Навыки: {labels(preferred_roles, ROLES)}\n"
        f"📊 Уровень: {LEVELS.get(profile.get('experience_level'), profile.get('experience_level'))}\n"
        f"💼 Опыт: {EXPERIENCE.get(profile.get('experience'), profile.get('experience'))}\n"
        f"🌍 Языки: {labels(languages, LANGUAGES)}\n"
        f"🏠 Формат: {labels(work_formats, WORK_FORMATS)}\n"
        f"📍 Локация: {labels(locations, LOCATIONS)}"
    )


def save_profile(user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    profile = dict(data)
    profile["language"] = profile.get("language", profile.get("lang", "ru"))
    if profile.get("field") or profile.get("specialization") or profile.get("skills"):
        profile["is_active"] = True
        if not profile.get("preferred_roles") and profile.get("specialization"):
            profile["preferred_roles"] = [profile["specialization"]]
        if not profile.get("work_formats") and profile.get("work_format"):
            profile["work_formats"] = [profile["work_format"]]
        if not profile.get("locations") and profile.get("city"):
            profile["locations"] = [profile["city"]]
        if not profile.get("experience_level") and profile.get("level"):
            profile["experience_level"] = profile["level"]
        if not profile.get("languages") and profile.get("language"):
            profile["languages"] = [profile["language"]]
    return upsert_user_profile(user_id, profile)


def load_profile(user_id: int) -> dict[str, Any] | None:
    profile = get_user_profile(user_id)
    if profile and profile.get("is_active") is False:
        return None
    return profile


def __all__ = [
    "profile_complete",
    "display_profile",
    "save_profile",
    "load_profile",
]
