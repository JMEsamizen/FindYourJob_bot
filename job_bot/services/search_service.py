import re

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db import get_user_viewed_vacancies, save_vacancies, get_viewed_vacancy_ids, mark_vacancies_viewed, clear_viewed_vacancies
from i18n import category_label, skill_label, t
from parser import Vacancy, fetch_all_vacancies
from vacancy_filter import filter_posts_by_keywords, filter_vacancies

CHANNEL_USERNAME_RE = re.compile(r"^(?:@|https://t\.me/)([A-Za-z0-9_]{5,32})/?$", re.IGNORECASE)
RESULTS_PAGE_SIZE = 15


def find_more_visible(page: int, total: int) -> bool:
    if total <= 0:
        return False
    return (page + 1) % RESULTS_PAGE_SIZE == 0 and page + 1 < total


def _batch_vacancy_ids(page: int, vacancies: list[dict]) -> list[int]:
    start = page - (page % RESULTS_PAGE_SIZE)
    end = min(start + RESULTS_PAGE_SIZE, len(vacancies))
    return [item.get("db_id") for item in vacancies[start:end] if item.get("db_id") is not None]


def build_new_vacancy_dicts(all_vacancies: list[Vacancy], category: str, skills: list[str], user_id: int) -> list[dict]:
    matching = filter_vacancies(all_vacancies, category, skills, limit=None)
    id_by_url = save_vacancies([vacancy.to_dict() for vacancy in matching])
    viewed_ids = get_viewed_vacancy_ids(user_id)
    new = []
    for vacancy in matching:
        item = vacancy.to_dict()
        db_id = id_by_url.get(item["url"])
        if db_id is not None and db_id in viewed_ids:
            continue
        item["db_id"] = db_id
        new.append(item)
    return new


def categories_text(lang: str) -> str:
    return t("welcome", lang)


def skills_text(category: str, skills: list[str], lang: str) -> str:
    selected = "\n".join(f"✅ {skill_label(skill, lang)}" for skill in skills) or t("nothing_selected", lang)
    return f"{category_label(category, lang)}\n\n{t('choose_skills', lang)}\n\n{t('selected', lang)}\n{selected}"


def vacancy_text(vacancy: dict, lang: str) -> str:
    text = vacancy.get("text", "").strip()
    if len(text) > 2500:
        text = text[:2500].rstrip() + "..."
    return (
        f"💼 {vacancy.get('title', t('vacancy_unknown', lang))}\n\n"
        f"📢 {t('source', lang)}: @{vacancy.get('channel', '')}\n"
        f"📅 {vacancy.get('date', t('date_unknown', lang))}\n\n{text}"
    )


def custom_post_text(post: dict, keywords: list[str], lang: str) -> str:
    text = post.get("text", "").strip()
    if len(text) > 3000:
        text = text[:3000].rstrip() + "..."
    matches = [keyword for keyword in keywords if keyword.lower() in text.lower()]
    match_text = ", ".join(matches)
    return (f"📢 @{post.get('channel', '')}\n\n"
            f"📅 {post.get('date', t('date_unknown', lang))}\n\n"
            f"{text}\n\n"
            f"{t('match', lang)}: {match_text}")


def normalize_channel_username(value: str) -> str | None:
    match = CHANNEL_USERNAME_RE.fullmatch(value.strip())
    return f"@{match.group(1)}" if match else None


def parse_custom_keywords(value: str) -> list[str]:
    keywords = []
    for line in value.splitlines():
        cleaned = re.sub(r"^\s*\d+\s*[-.)]\s*", "", line).strip()
        if cleaned:
            keywords.append(cleaned)
    return list(dict.fromkeys(keywords))


def custom_channel_prompt(lang: str) -> str:
    return t("custom_channel_prompt", lang)


async def render_search_result(callback: CallbackQuery, state: FSMContext, page: int) -> None:
    from services.search_service import _batch_vacancy_ids as batch_ids  # noqa: F401
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    total_new = data.get("total_new", len(vacancies))
    ok = await _render_vacancy_message(callback, state, vacancies, page, show_find_more=find_more_visible(page, total_new))
    if ok:
        mark_vacancies_viewed(callback.from_user.id, _batch_vacancy_ids(page, vacancies))


async def render_history_result(callback: CallbackQuery, state: FSMContext, page: int) -> None:
    data = await state.get_data()
    vacancies = data.get("history_vacancies", [])
    if not vacancies or not 0 <= page < len(vacancies):
        await callback.answer()
        return
    lang = data.get("lang", "ru")
    footer = t("history_end", lang) if page == len(vacancies) - 1 else ""
    vacancy = vacancies[page]
    text = vacancy_text(vacancy, lang)
    if footer:
        text = f"{text}\n\n{footer}"
    await state.update_data(current_page=page)
    try:
        await callback.message.edit_text(text, reply_markup=None)
    except Exception:
        pass


async def _render_vacancy_message(callback: CallbackQuery, state: FSMContext, vacancies: list[dict], page: int, *, show_find_more: bool, prefix: str = "page", footer: str = "") -> bool:
    from keyboards import results_keyboard

    lang = (await state.get_data()).get("lang", "ru")
    if not vacancies or not 0 <= page < len(vacancies):
        await callback.answer()
        return False
    await state.update_data(current_page=page)
    vacancy = vacancies[page]
    text = vacancy_text(vacancy, lang)
    if footer:
        text = f"{text}\n\n{footer}"
    await callback.answer()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=results_keyboard(page, len(vacancies), vacancy["url"], lang, show_find_more=show_find_more, prefix=prefix),
        )
    except Exception:
        return False
    return True


__all__ = [
    "RESULTS_PAGE_SIZE",
    "find_more_visible",
    "_batch_vacancy_ids",
    "build_new_vacancy_dicts",
    "categories_text",
    "skills_text",
    "vacancy_text",
    "custom_post_text",
    "normalize_channel_username",
    "parse_custom_keywords",
    "custom_channel_prompt",
    "render_search_result",
    "render_history_result",
]
