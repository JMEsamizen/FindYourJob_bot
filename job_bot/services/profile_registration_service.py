from __future__ import annotations

from typing import Any

from db import upsert_user_profile

EDUCATION_LEVELS = {
    "school": "Среднее образование",
    "college": "Среднее специальное",
    "higher": "Высшее",
    "master": "Магистратура",
    "phd": "Докторантура",
}

EMPLOYMENT_STATUSES = {
    "full_time": "Полная занятость",
    "part_time": "Частичная занятость",
    "project": "Проектная работа",
    "internship": "Стажировка",
    "freelance": "Фриланс",
}

EXPERIENCE_LEVELS = {
    "intern": "Стажер / Junior",
    "junior": "Junior",
    "middle": "Middle",
    "senior": "Senior",
    "lead": "Lead",
}

PREFERRED_LANGUAGES = {"ru": "Русский", "uz": "O‘zbek", "en": "English"}

POSITION_ALIASES = {
    "backend_developer": "backend",
    "frontend_developer": "frontend",
    "fullstack_developer": "fullstack",
    "python_developer": "backend",
    "data_analyst": "data",
    "qa_engineer": "qa",
    "devops_engineer": "devops",
    "product_manager": "other",
    "designer": "design",
    "marketing_specialist": "marketing",
    "support_specialist": "other",
    "project_manager": "other",
}

REGISTRATION_FIELDS = [
    "full_name",
    "age",
    "city",
    "education_level",
    "employment_status",
    "desired_position",
    "experience_level",
    "skills",
    "preferred_language",
    "expected_salary",
]


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            text = _string(item)
            if text:
                result.append(text)
        return result
    return [_string(value)]


def normalize_registration_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            if key == "age":
                normalized[key] = None
            continue
        if key == "full_name":
            normalized[key] = _string(value)
        elif key == "age":
            if _string(value).lower() in {"", "skip", "пропустить", "none", "нет"}:
                normalized[key] = None
                continue
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = value
        elif key == "city":
            normalized[key] = _string(value)
        elif key == "education_level":
            normalized[key] = _string(value)
        elif key == "employment_status":
            normalized[key] = _string(value)
        elif key == "desired_position":
            normalized[key] = _string(value)
        elif key == "experience_level":
            normalized[key] = _string(value)
        elif key == "skills":
            normalized[key] = _as_list(value)
        elif key == "preferred_language":
            normalized[key] = _string(value)
        elif key == "expected_salary":
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = value
        else:
            normalized[key] = value
    return normalized


def validate_registration_step(step: str, value: Any) -> str | None:
    if step == "full_name":
        name = _string(value)
        if not name:
            return "Укажите ваше имя."
        if len(name) < 2:
            return "Имя должно содержать минимум 2 символа."
        return None
    if step == "age":
        if value in (None, "", "skip", "пропустить", "none", "нет") or _string(value).lower() in {"", "skip", "пропустить", "none", "нет"}:
            return None
        try:
            age = int(value)
        except (TypeError, ValueError):
            return "Возраст должен быть числом, например: 29."
        return None
    if step == "city":
        city = _string(value)
        if not city:
            return "Укажите ваш город."
        return None
    if step == "education_level":
        if _string(value) not in EDUCATION_LEVELS:
            return "Выберите уровень образования из списка."
        return None
    if step == "employment_status":
        if _string(value) not in EMPLOYMENT_STATUSES:
            return "Выберите тип занятости из списка."
        return None
    if step == "desired_position":
        if not _string(value):
            return "Укажите желаемую должность."
        return None
    if step == "experience_level":
        if _string(value) not in EXPERIENCE_LEVELS:
            return "Выберите уровень опыта."
        return None
    if step == "skills":
        skills = _as_list(value)
        if not skills:
            return "Укажите хотя бы один навык."
        return None
    if step == "preferred_language":
        if _string(value) not in PREFERRED_LANGUAGES:
            return "Выберите предпочитаемый язык общения."
        return None
    if step == "expected_salary":
        if value in (None, "", "skip"):
            return None
        try:
            salary = int(value)
        except (TypeError, ValueError):
            return "Ожидаемая зарплата должна быть числом."
        if salary < 0:
            return "Зарплата не может быть отрицательной."
        return None
    return None


def build_profile_document(data: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_registration_payload(data)
    required = [
        "full_name",
        "city",
        "education_level",
        "employment_status",
        "desired_position",
        "experience_level",
        "skills",
        "preferred_language",
    ]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"Missing required profile fields: {', '.join(missing)}")

    age_value = payload.get("age")
    if age_value in (None, "", "skip", "пропустить", "none", "нет"):
        age = None
    else:
        age = int(age_value)

    skills = _as_list(payload.get("skills", []))
    desired_position = _string(payload.get("desired_position"))
    alias = POSITION_ALIASES.get(desired_position, desired_position)
    document = {
        "full_name": _string(payload.get("full_name")),
        "age": age,
        "city": _string(payload.get("city")),
        "education_level": _string(payload.get("education_level")),
        "employment_status": _string(payload.get("employment_status")),
        "desired_position": desired_position,
        "experience_level": _string(payload.get("experience_level")),
        "skills": skills,
        "preferred_language": _string(payload.get("preferred_language")),
        "expected_salary": None if payload.get("expected_salary") in (None, "", "skip") else int(payload.get("expected_salary")),
        "language": _string(payload.get("language") or payload.get("lang") or "ru"),
        "is_active": True,
        "preferred_roles": [alias] if alias else [],
        "work_formats": [],
        "languages": [_string(payload.get("preferred_language"))],
    }
    return document


def save_registration_profile(user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    try:
        profile = build_profile_document(data)
    except ValueError:
        return None
    return upsert_user_profile(user_id, profile)
