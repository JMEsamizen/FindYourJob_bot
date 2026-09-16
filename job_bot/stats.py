from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from i18n import category_label, skill_label, t
from vacancy_filter import CATEGORY_KEYWORDS, SKILL_KEYWORDS


def _normalize_skill_name(skill: str) -> str:
    value = skill.strip().lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_./+-]+", "", value)


def _extract_skill_hits(text: str) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(re.search(rf"(?<![A-Za-zА-Яа-яЁё0-9_]){re.escape(keyword.lower())}(?![A-Za-zА-Яа-яЁё0-9_])", lowered) for keyword in keywords):
            matches.append(skill)
    return matches


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for candidate in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, candidate)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def summarize_market(vacancies: list[dict[str, Any]], days: int = 7) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    recent = []
    for vacancy in vacancies:
        published = _to_datetime(vacancy.get("created_at") or vacancy.get("date"))
        if published and published >= cutoff:
            recent.append(vacancy)

    if not recent:
        return {
            "total_vacancies": 0,
            "top_fields": [],
            "top_skills": [],
            "changes": [],
            "most_in_demand_field": None,
            "most_in_demand_skill": None,
        }

    field_counter: Counter[str] = Counter()
    skill_counter: Counter[str] = Counter()
    for vacancy in recent:
        title = str(vacancy.get("title", "")).lower()
        text = str(vacancy.get("text", "")).lower()
        content = f"{title} {text}"
        matched_field = None
        for field, keywords in CATEGORY_KEYWORDS.items():
            if field == "other":
                continue
            if any(re.search(rf"(?<![A-Za-zА-Яа-яЁё0-9_]){re.escape(keyword.lower())}(?![A-Za-zА-Яа-яЁё0-9_])", content) for keyword in keywords):
                matched_field = field
                break
        if matched_field:
            field_counter[matched_field] += 1
        for skill in _extract_skill_hits(content):
            skill_counter[skill] += 1

    top_fields = field_counter.most_common(5)
    top_skills = skill_counter.most_common(10)
    most_demanded_field = top_fields[0][0] if top_fields else None
    most_demanded_skill = top_skills[0][0] if top_skills else None

    return {
        "total_vacancies": len(recent),
        "top_fields": [(field, count) for field, count in top_fields],
        "top_skills": [(skill, count) for skill, count in top_skills],
        "most_in_demand_field": most_demanded_field,
        "most_in_demand_skill": most_demanded_skill,
        "changes": _count_skill_changes(vacancies, days),
    }


def _count_skill_changes(vacancies: list[dict[str, Any]], days: int) -> list[tuple[str, str, int, int]]:
    """Compare skill mentions in the last `days` against the previous `days`."""
    now = datetime.now(timezone.utc)
    current_cutoff = now - timedelta(days=days)
    previous_cutoff = now - timedelta(days=days * 2)

    def count_for(window_start: datetime, window_end: datetime) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for vacancy in vacancies:
            published = _to_datetime(vacancy.get("created_at") or vacancy.get("date"))
            if published is None:
                continue
            if window_start <= published < window_end:
                content = f"{vacancy.get('title','')} {vacancy.get('text','')}".lower()
                candidates = [
                    skill for skill, keywords in SKILL_KEYWORDS.items()
                    if any(re.search(rf"(?<![A-Za-zА-Яа-яЁё0-9_]){re.escape(keyword.lower())}(?![A-Za-zА-Яа-яЁё0-9_])", content) for keyword in keywords)
                ]
                for item in set(candidates):
                    counts[item] += 1
        return dict(counts)

    current_counts = count_for(current_cutoff, now)
    previous_counts = count_for(previous_cutoff, current_cutoff)
    changes: list[tuple[str, str, int, int]] = []
    for skill, current_count in sorted(current_counts.items(), key=lambda item: item[1], reverse=True)[:6]:
        previous_count = previous_counts.get(skill, 0)
        if previous_count == 0:
            changes.append((skill, "new", current_count, previous_count))
            continue
        delta = round(((current_count - previous_count) / previous_count) * 100)
        if delta == 0:
            continue
        direction = "up" if delta > 0 else "down"
        changes.append((skill, direction, current_count, previous_count))
    return changes


def market_changes(vacancies: list[dict[str, Any]], days: int = 7) -> list[tuple[str, str, int, int]]:
    """Backwards-compatible wrapper around the skill-change counter."""
    return _count_skill_changes(vacancies, days)


def _rank_in(pairs: list[tuple[str, int]], key: str) -> int | None:
    for index, (item, _count) in enumerate(pairs, start=1):
        if item == key:
            return index
    return None


def _count_of(pairs: list[tuple[str, int]], key: str) -> int:
    for item, count in pairs:
        if item == key:
            return count
    return 0


def _format_changes(changes: list[tuple[str, str, int, int]], lang: str) -> str:
    if not changes:
        return t("stats_no_changes", lang)
    lines: list[str] = []
    for skill, direction, current, previous in changes[:3]:
        label = skill_label(skill, lang)
        if direction == "new":
            lines.append(t("stats_change_new", lang, label=label, count=current))
            continue
        if previous == 0:
            continue
        percent = round(abs((current - previous) / previous) * 100)
        if direction == "up":
            lines.append(t("stats_change_up", lang, label=label, percent=percent, current=current, previous=previous))
        else:
            lines.append(t("stats_change_down", lang, label=label, percent=percent, current=current, previous=previous))
    return "\n".join(lines) if lines else t("stats_no_changes", lang)


def _field_label(field: str) -> str:
    return field.replace("_", " ").title()


def _personalize(summary: dict[str, Any], profile: dict[str, Any] | None, lang: str) -> str:
    if not profile:
        return ""
    field = profile.get("field") or ""
    specialization = profile.get("specialization") or ""
    skills = profile.get("skills") or []
    top_fields = dict(summary["top_fields"])
    top_skills = dict(summary["top_skills"])
    lines: list[str] = []

    field_rank = _rank_in(summary["top_fields"], field) if field else None
    if field_rank:
        lines.append(t("stats_personal_field", lang, field=_field_label(field), rank=field_rank, count=top_fields.get(field, 0)))

    spec_rank = _rank_in(summary["top_fields"], specialization) if specialization else None
    if spec_rank:
        lines.append(t("stats_personal_spec", lang, specialization=category_label(specialization, lang), rank=spec_rank, count=top_fields.get(specialization, 0)))

    for skill in skills[:2]:
        rank = _rank_in(summary["top_skills"], skill)
        if rank:
            lines.append(t("stats_personal_skill", lang, skill=skill_label(skill, lang), rank=rank, count=top_skills.get(skill, 0)))

    if not lines:
        return ""
    return f"\n\n{t('stats_personal_title', lang)}\n" + "\n".join(lines)


def build_market_stats_message(
    vacancies: list[dict[str, Any]], lang: str = "ru", profile: dict[str, Any] | None = None, days: int = 7
) -> dict[str, Any]:
    """Build a localized weekly-market message: returns {'text': str, 'learn_skill': key|None}."""
    summary = summarize_market(vacancies, days)
    most_skill = summary["most_in_demand_skill"]
    if not summary["total_vacancies"]:
        return {"text": t("stats_empty", lang, days=days), "learn_skill": None}

    top_fields = summary["top_fields"]
    top_skills = summary["top_skills"]
    lines = [t("stats_title", lang), ""]
    lines.append(t("stats_total", lang, count=summary["total_vacancies"]))

    most_field = summary["most_in_demand_field"]
    if most_field:
        lines.append(t("stats_top_field", lang, label=category_label(most_field, lang), count=_count_of(top_fields, most_field)))
    if most_skill:
        lines.append(t("stats_top_skill", lang, label=skill_label(most_skill, lang), count=_count_of(top_skills, most_skill)))
    lines.append("")

    if top_fields:
        lines.append(t("stats_top_fields", lang))
        lines.extend(f"{index}. {category_label(item, lang)} — {count}" for index, (item, count) in enumerate(top_fields[:5], start=1))
        lines.append("")
    if top_skills:
        lines.append(t("stats_top_skills", lang))
        lines.extend(f"{index}. {skill_label(item, lang)} — {count}" for index, (item, count) in enumerate(top_skills[:5], start=1))
        lines.append("")

    lines.append(t("stats_changes_title", lang))
    lines.append(_format_changes(summary["changes"], lang))

    personalization = _personalize(summary, profile, lang)
    if personalization:
        lines.append(personalization)

    return {"text": "\n".join(lines), "learn_skill": most_skill}
