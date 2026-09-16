from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, unquote

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from matching import match_vacancy


REQUIRED_FIELDS = ("match_percent", "matched_skills", "missing_skills", "strengths", "weaknesses", "recommendation")
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

AI_SYSTEM_PROMPT = """You analyze a job vacancy against a user's profile.
Use only facts explicitly present in the profile and vacancy. Do not invent skills,
requirements, experience, languages, or preferences. Missing information is neutral:
do not treat an absent vacancy detail as a mismatch. A skill is matched only when it
is present in the user's profile and explicitly supported by the vacancy text/title.
Put a skill in missing_skills only when it is explicitly required by the vacancy and
is absent from the user's profile. Never invent profile skills or vacancy requirements.
Return only the requested JSON object, with no markdown or extra keys.
"""

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "match_percent": {"type": "integer", "minimum": 0, "maximum": 100},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string"},
    },
    "required": list(REQUIRED_FIELDS),
}


def _fallback(profile: dict[str, Any], vacancy: Any) -> dict[str, Any]:
    result = match_vacancy(vacancy, profile)
    return {
        "match_percent": result.score,
        "matched_skills": list(result.matched_skills),
        "missing_skills": list(result.missing_skills),
        "strengths": list(result.matched_skills),
        "weaknesses": list(result.missing_skills),
        "recommendation": "Вакансия соответствует выбранным параметрам." if result.matched else "Вакансия не полностью соответствует выбранным параметрам.",
    }


def _vacancy_value(vacancy: Any, key: str) -> str:
    if isinstance(vacancy, dict):
        return str(vacancy.get(key, ""))
    return str(getattr(vacancy, key, ""))


def _valid_result(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or any(field not in value for field in REQUIRED_FIELDS):
        return None
    percent = value["match_percent"]
    if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
        return None
    result = dict(value)
    for field in REQUIRED_FIELDS[1:5]:
        if not isinstance(result[field], list) or not all(isinstance(item, str) for item in result[field]):
            return None
    if not isinstance(result["recommendation"], str):
        return None
    return result


async def analyze_vacancy(profile: dict[str, Any], vacancy: Any) -> dict[str, Any]:
    fallback = _fallback(profile, vacancy)
    if not OPENROUTER_API_KEY:
        return fallback
    user_input = {
        "profile": {
            "experience_level": profile.get("experience_level"),
            "experience": profile.get("experience"),
            "preferred_roles": profile.get("preferred_roles", []),
            "languages": profile.get("languages", []),
            "work_formats": profile.get("work_formats", []),
            "locations": profile.get("locations", []),
        },
        "vacancy": {
            "title": _vacancy_value(vacancy, "title"),
            "text": _vacancy_value(vacancy, "text"),
        },
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "vacancy_match_analysis", "strict": True, "schema": ANALYSIS_SCHEMA},
        },
        "temperature": 0,
        "max_tokens": 12000,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(OPENROUTER_CHAT_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        if isinstance(data, dict) and "choices" in data:
            content = data["choices"][0]["message"]["content"]
            data = json.loads(content) if isinstance(content, str) else content
        return _valid_result(data) or fallback
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return fallback


def analysis_callback_data(post_url: str) -> str:
    return f"analyze:{quote(post_url, safe='')}"


def analysis_url(callback_data: str) -> str:
    return unquote(callback_data.split(":", 1)[1])


def format_analysis(result: dict[str, Any]) -> str:
    matched = "\n".join(f"• {item}" for item in result["matched_skills"]) or "• Нет данных"
    missing = "\n".join(f"• {item}" for item in result["missing_skills"]) or "• Нет данных"
    return (
        f"🎯 Совпадение: {result['match_percent']}%\n\n"
        f"✅ У вас есть:\n{matched}\n\n"
        f"❌ Не хватает:\n{missing}\n\n"
        f"💡 Рекомендация:\n{result['recommendation']}"
    )
