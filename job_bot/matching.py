from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROLE_TERMS = {
    "backend": ("backend", "бекенд", "server-side"),
    "frontend": ("frontend", "front-end", "фронтенд"),
    "python": ("python", "питон"),
    "ai_ml": ("ai", "machine learning", "ml", "нейросет"),
    "mobile": ("mobile", "android", "ios", "flutter", "мобиль"),
    "data": ("data analyst", "data science", "analytics", "аналитик", "данн"),
    "design": ("design", "designer", "дизайн", "figma", "ui/ux"),
    "qa": ("qa", "tester", "testing", "тестиров"),
    "marketing": ("smm", "marketing", "маркетинг", "seo", "контент"),
    "devops": ("devops", "docker", "kubernetes", "девопс"),
}
LEVEL_TERMS = {
    "no_experience": ("без опыта", "no experience", "без опыта работы", "стажер", "intern"),
    "junior": ("junior", "джун", "начинающ"),
    "middle": ("middle", "мидл"),
    "senior": ("senior", "сеньор", "lead", "ведущ"),
}
FORMAT_TERMS = {"remote": ("remote", "удален", "удалён", "дистанцион"), "office": ("office", "офис"), "hybrid": ("hybrid", "гибрид")}
LOCATION_TERMS = {"tashkent": ("ташкент", "tashkent"), "uzbekistan": ("узбекистан", "uzbekistan", "uz"), "worldwide": ("worldwide", "по всему миру", "anywhere")}
LANGUAGE_TERMS = {"uz": ("uzbek", "узбек"), "ru": ("russian", "русск"), "en": ("english", "английск")}


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    score: int
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]


def _text(vacancy: Any) -> str:
    if isinstance(vacancy, dict):
        return f"{vacancy.get('title', '')} {vacancy.get('text', '')}".lower()
    return f"{getattr(vacancy, 'title', '')} {getattr(vacancy, 'text', '')}".lower()


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def match_vacancy(vacancy: Any, profile: dict[str, Any]) -> MatchResult:
    text = _text(vacancy)
    roles = list(profile.get("preferred_roles", []))
    detected_roles = {role for role, terms in ROLE_TERMS.items() if _contains(text, terms)}
    role_match = not detected_roles or bool(detected_roles.intersection(roles)) or "other" in roles

    selected_level = profile.get("experience_level")
    detected_levels = {level for level, terms in LEVEL_TERMS.items() if _contains(text, terms)}
    level_match = not detected_levels or selected_level in detected_levels

    formats = list(profile.get("work_formats", []))
    detected_formats = {item for item, terms in FORMAT_TERMS.items() if _contains(text, terms)}
    format_match = "any" in formats or not detected_formats or bool(detected_formats.intersection(formats))

    locations = list(profile.get("locations", []))
    detected_locations = {item for item, terms in LOCATION_TERMS.items() if _contains(text, terms)}
    location_match = "any" in locations or not detected_locations or bool(detected_locations.intersection(locations))

    languages = list(profile.get("languages", []))
    detected_languages = {item for item, terms in LANGUAGE_TERMS.items() if _contains(text, terms)}
    language_match = not detected_languages or bool(detected_languages.intersection(languages))

    matched_skills = tuple(sorted(detected_roles.intersection(roles)))
    missing_skills = tuple(sorted(set(roles) - detected_roles))
    score = round(sum((role_match, level_match, format_match, location_match, language_match)) * 100 / 5)
    return MatchResult(role_match and level_match and format_match and location_match and language_match, score, matched_skills, missing_skills)
