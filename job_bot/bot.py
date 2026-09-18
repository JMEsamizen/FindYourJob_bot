from __future__ import annotations

import asyncio
import re
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import (
    clear_viewed_vacancies,
    get_recent_vacancies,
    get_user_language,
    get_user_profile,
    get_user_viewed_vacancies,
    get_viewed_vacancy_ids,
    mark_vacancies_viewed,
    save_vacancies,
    set_user_language,
    set_user_profile_active,
)
from i18n import category_label, skill_label, t
from keyboards import (
    categories_keyboard,
    custom_empty_results_keyboard,
    custom_results_keyboard,
    empty_results_keyboard,
    history_results_keyboard,
    language_keyboard,
    learning_keyboard,
    learning_skills_keyboard,
    learning_video_keyboard,
    login_keyboard,
    materials_keyboard,
    premium_keyboard,
    profile_create_keyboard,
    profile_experience_keyboard,
    profile_field_keyboard,
    profile_hours_keyboard,
    profile_level_choice_keyboard,
    profile_menu_keyboard,
    profile_skill_keyboard,
    profile_specialization_keyboard,
    profile_work_format_keyboard,
    results_keyboard,
    skills_keyboard,
    stats_keyboard,
    stats_materials_keyboard,
)
from handlers.analysis import router as analysis_router
from handlers.learning import router as learning_router
from handlers.profile import router as profile_router
from handlers.registration import router as registration_router
from handlers.start import router as start_router
from handlers.stats import router as stats_router
from handlers.vacancies import router as vacancies_router
from learning import learning_skills, material_for, materials_for
from parser import Vacancy, fetch_all_vacancies, fetch_channel_posts
from profile import PROFILE_FIELDS, display_profile, load_profile, profile_complete, save_profile
from states import SearchStates
from stats import build_market_stats_message
from vacancy_filter import filter_posts_by_keywords, filter_vacancies


router = Router()
router.include_routers(
    analysis_router,
    learning_router,
    profile_router,
    registration_router,
    start_router,
    stats_router,
    vacancies_router,
)

CHANNEL_USERNAME_RE = re.compile(r"^(?:@|https://t\.me/)([A-Za-z0-9_]{5,32})/?$", re.IGNORECASE)
RESULTS_PAGE_SIZE = 15


@router.callback_query(F.data == "profile_logout")
async def profile_logout_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang") or get_user_language(callback.from_user.id) or "ru"
    set_user_profile_active(callback.from_user.id, False)
    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(SearchStates.choosing_category)
    await callback.answer()
    await callback.message.edit_text(t("logout_confirmed", lang), reply_markup=login_keyboard(lang))


@router.callback_query(F.data == "profile_login")
async def profile_login_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = (await state.get_data()).get("lang") or get_user_language(callback.from_user.id) or "ru"
    profile = get_user_profile(callback.from_user.id)
    await callback.answer()
    if profile is None:
        await callback.message.edit_text(t("need_profile_first", lang), reply_markup=login_keyboard(lang))
        return
    set_user_profile_active(callback.from_user.id, True)
    updated = get_user_profile(callback.from_user.id) or profile
    await callback.message.edit_text(
        f"{t('login_success', lang)}\n\n{display_profile(updated)}",
        reply_markup=profile_menu_keyboard(lang=lang),
    )


@router.callback_query(F.data == "profile_menu")
async def profile_menu_handler(callback: CallbackQuery) -> None:
    profile = load_profile(callback.from_user.id)
    lang = get_user_language(callback.from_user.id) or "ru"
    await callback.answer()
    if profile is None or not profile_complete(profile):
        existing = get_user_profile(callback.from_user.id)
        has_real_profile = bool(existing) and any(existing.get(key) for key in ("field", "specialization", "skills", "preferred_roles", "experience_level", "full_name", "desired_position"))
        if has_real_profile:
            await callback.message.edit_text(t("login_required", lang), reply_markup=login_keyboard(lang))
        else:
            await callback.message.edit_text(t("no_active_profile", lang), reply_markup=profile_create_keyboard(lang))
        return
    await callback.message.edit_text(display_profile(profile), reply_markup=profile_menu_keyboard(lang=lang))


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


async def render_search_result(callback: CallbackQuery, state: FSMContext, page: int) -> None:
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    total_new = data.get("total_new", len(vacancies))
    if not vacancies or not 0 <= page < len(vacancies):
        await callback.answer()
        return
    await state.update_data(current_page=page)
    vacancy = vacancies[page]
    text = vacancy_text(vacancy, data.get("lang", "ru"))
    await callback.answer()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=results_keyboard(page, len(vacancies), vacancy["url"], data.get("lang", "ru"), show_find_more=find_more_visible(page, total_new)),
        )
    except Exception:
        pass
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
    await callback.answer()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=history_results_keyboard(page, len(vacancies), vacancy["url"], lang),
        )
    except Exception:
        pass


def custom_post_text(post: dict, keywords: list[str], lang: str) -> str:
    text = post.get("text", "").strip()
    if len(text) > 3000:
        text = text[:3000].rstrip() + "..."
    matches = [keyword for keyword in keywords if keyword.lower() in text.lower()]
    match_text = ", ".join(matches)
    return (
        f"📢 @{post.get('channel', '')}\n\n"
        f"📅 {post.get('date', t('date_unknown', lang))}\n\n"
        f"{text}\n\n"
        f"{t('match', lang)}: {match_text}"
    )


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


async def show_language(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchStates.choosing_category)
    await message.answer(t("language_prompt"), reply_markup=language_keyboard())


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    language = get_user_language(message.from_user.id)
    if language:
        await state.clear()
        await state.update_data(lang=language)
        await state.set_state(SearchStates.choosing_category)
        await message.answer(categories_text(language), reply_markup=categories_keyboard(language))
        return
    await show_language(message, state)


@router.callback_query(F.data == "new_search")
async def new_search_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer()
    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(SearchStates.choosing_category)
    await callback.message.edit_text(categories_text(lang), reply_markup=categories_keyboard(lang))






@router.callback_query(F.data.startswith("analyze:"))
async def analyze_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = (await state.get_data()).get("lang") or get_user_language(callback.from_user.id) or "ru"
    profile = load_profile(callback.from_user.id)
    if profile is None:
        await callback.answer(t("profile_needed", lang), show_alert=True)
        return
    if not any(True for _ in [1]):
        pass
    try:
        target_url = callback.data.split(":", 1)[1]
        vacancies = await asyncio.wait_for(fetch_all_vacancies(), timeout=65)
        vacancy = next((item for item in vacancies if item.url == target_url), None)
        if vacancy is None:
            await callback.answer("Вакансия больше недоступна.", show_alert=True)
            return
        await callback.answer("Анализ готовится...")
        result = await __import__("ai_analysis").analyze_vacancy(profile, vacancy)
        missing_skills = list(dict.fromkeys(result["missing_skills"]))[:6]
        available_skills = [material.skill for material in materials_for(missing_skills)]
        await state.update_data(learning_skills=available_skills)
        reply_markup = learning_keyboard(available_skills) if available_skills else None
        await callback.message.answer(__import__("ai_analysis").format_analysis(result), reply_markup=reply_markup)
        if missing_skills and not available_skills:
            await callback.message.answer("Для навыков из анализа пока нет обучающих материалов в базе.")
    except Exception:
        await callback.answer("Не удалось выполнить анализ.", show_alert=True)


@router.callback_query((F.data == "learn") | F.data.startswith("learn:"))
async def learning_handler(callback: CallbackQuery, state: FSMContext) -> None:
    profile = load_profile(callback.from_user.id)
    if profile is None:
        await callback.answer("Сначала создайте профиль.", show_alert=True)
        return
    used, count = __import__("db").consume_learning_use(callback.from_user.id)
    if not used:
        await callback.answer("🔒 Персональное обучение доступно в Premium.", show_alert=True)
        await callback.message.answer("🔒 Персональное обучение доступно в Premium.", reply_markup=premium_keyboard())
        return
    data = await state.get_data()
    skills = data.get("learning_skills", [])[:6]
    if not skills and callback.data.startswith("learn:"):
        skills = learning_skills(callback.data)
    skills = list(dict.fromkeys(material.skill for material in materials_for(skills)))
    if not skills:
        await callback.answer("Для навыков из анализа пока нет обучающих материалов.", show_alert=True)
        return
    for skill in skills:
        __import__("db").upsert_learning_progress(callback.from_user.id, skill)
    await callback.answer(f"Использование {count} / 5")
    await callback.message.answer("📚 Выберите навык для изучения:", reply_markup=learning_skills_keyboard(skills))


@router.callback_query(F.data.startswith("learn_skill:"))
async def learning_skill_handler(callback: CallbackQuery) -> None:
    skill = callback.data.split(":", 1)[1]
    material = material_for(skill)
    if material is None:
        await callback.answer("Для этого навыка материал не найден.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(f"📚 {material.title}\n\n{material.url}", reply_markup=learning_video_keyboard())


@router.callback_query(F.data.startswith("learned:"))
async def learned_handler(callback: CallbackQuery) -> None:
    skill = callback.data.split(":", 1)[1]
    __import__("db").upsert_learning_progress(callback.from_user.id, skill, "completed")
    await callback.answer("Навык отмечен как изученный")


@router.callback_query(F.data == "progress_menu")
async def progress_menu_handler(callback: CallbackQuery) -> None:
    profile = load_profile(callback.from_user.id)
    if profile is None:
        await callback.answer("У вас пока нет персонального профиля.", show_alert=True)
        return
    progress = __import__("db").get_learning_progress(callback.from_user.id)
    completed = [item["skill"] for item in progress if item["status"] == "completed"]
    active = [item["skill"] for item in progress if item["status"] == "in_progress"]
    recommended = [item for item in profile.get("preferred_roles", []) if item not in completed and item not in active]
    text = (
        "📈 Мой прогресс\n\n"
        f"🎯 Основное направление: {', '.join(profile.get('preferred_roles', []))}\n"
        "📊 Текущий match: rule-based\n"
        f"📚 Изучено навыков: {', '.join(completed) or 'нет'}\n"
        f"🔥 Навыки в процессе: {', '.join(active) or 'нет'}\n"
        f"❌ Рекомендуемые навыки: {', '.join(recommended) or 'нет'}"
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=profile_menu_keyboard(lang=get_user_language(callback.from_user.id) or "ru"))


@router.callback_query(F.data == "market_stats")
async def market_stats_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    lang = (await state.get_data()).get("lang") or get_user_language(callback.from_user.id) or "ru"
    vacancies = get_recent_vacancies(14)
    profile = get_user_profile(callback.from_user.id) or {}
    result = build_market_stats_message(vacancies, lang=lang, profile=profile, days=7)
    await callback.message.edit_text(result["text"], reply_markup=stats_keyboard(lang, result["learn_skill"]))


@router.callback_query(F.data.startswith("stats_learn:"))
async def stats_learn_handler(callback: CallbackQuery) -> None:
    skill = callback.data.split(":", 1)[1]
    lang = get_user_language(callback.from_user.id) or "ru"
    material = material_for(skill)
    await callback.answer()
    if material is None:
        await callback.message.answer(t("stats_learn_none", lang, skill=skill), reply_markup=stats_keyboard(lang))
        return
    await callback.message.answer(t("stats_learn_intro", lang, skill=material.skill), reply_markup=stats_materials_keyboard(material, lang))


@router.callback_query(F.data.startswith("category:"))
async def category_handler(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(category=category, skills=[], lang=lang)
    await state.set_state(SearchStates.choosing_skills)
    await callback.answer()
    await callback.message.edit_text(skills_text(category, [], lang), reply_markup=skills_keyboard(category, [], lang))


@router.callback_query(SearchStates.choosing_category, F.data == "custom_search")
async def custom_search_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(SearchStates.choosing_custom_channel)
    await callback.answer()
    await callback.message.edit_text(custom_channel_prompt(lang))


@router.message(SearchStates.choosing_custom_channel)
async def custom_channel_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    channel = normalize_channel_username(message.text or "")
    if not channel:
        await message.answer(t("invalid_channel", lang))
        return
    try:
        posts = await asyncio.wait_for(fetch_channel_posts(channel[1:]), timeout=65)
        if not posts:
            raise ValueError("public channel returned no posts")
    except Exception:
        await message.answer(t("channel_unavailable", lang))
        return
    await state.update_data(custom_channel=channel, custom_posts=[post.to_dict() for post in posts])
    await state.set_state(SearchStates.choosing_custom_keywords)
    await message.answer(t("custom_keywords_prompt", lang, channel=channel))


@router.message(SearchStates.choosing_custom_keywords)
async def custom_keywords_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    keywords = parse_custom_keywords(message.text or "")
    if not keywords:
        await message.answer(t("custom_keywords_error", lang))
        return
    channel = data.get("custom_channel", "")
    await message.answer(t("custom_searching", lang, channel=channel))
    try:
        posts = [Vacancy(**post) for post in data.get("custom_posts", [])]
        filtered = filter_posts_by_keywords(posts, keywords)
    except Exception:
        await message.answer(t("channel_unavailable", lang))
        return
    await state.update_data(custom_keywords=keywords, custom_results=[post.to_dict() for post in filtered], current_page=0, custom_mode=True)
    if not filtered:
        await message.answer(t("custom_no_results", lang, channel=channel, keywords="\n".join(keywords)), reply_markup=custom_empty_results_keyboard(lang))
        return
    await state.set_state(SearchStates.showing_results)
    posts_data = [post.to_dict() for post in filtered]
    await message.answer(
        t("custom_found", lang, count=len(filtered)) + "\n\n" + custom_post_text(posts_data[0], keywords, lang),
        reply_markup=custom_results_keyboard(0, len(filtered), posts_data[0]["url"], lang),
    )


@router.callback_query(F.data == "edit_custom_keywords")
async def edit_custom_keywords_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(SearchStates.choosing_custom_keywords)
    await callback.answer()
    await callback.message.edit_text(t("custom_keywords_prompt", lang, channel=data.get("custom_channel", "")))


@router.callback_query(F.data.startswith("skill:"))
async def skill_handler(callback: CallbackQuery, state: FSMContext) -> None:
    skill = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    skills = list(data.get("skills", []))
    if skill in skills:
        skills.remove(skill)
    else:
        skills.append(skill)
    await state.update_data(skills=skills)
    await callback.answer(t("skill_added", lang) if skill in skills else t("skill_removed", lang))
    category = data.get("category", "other")
    await callback.message.edit_text(skills_text(category, skills, lang), reply_markup=skills_keyboard(category, skills, lang))


@router.callback_query(F.data == "skills_done")
async def search_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    category = data.get("category", "other")
    skills = list(data.get("skills", []))
    lang = data.get("lang", "ru")
    await callback.message.edit_text(t("searching", lang))
    try:
        all_vacancies = await asyncio.wait_for(fetch_all_vacancies(), timeout=65)
        vacancy_dicts = build_new_vacancy_dicts(all_vacancies, category, skills, callback.from_user.id)
    except Exception:
        await callback.message.edit_text(t("fetch_error", lang), reply_markup=empty_results_keyboard(lang))
        return
    if not vacancy_dicts:
        await callback.message.edit_text(t("no_results", lang), reply_markup=empty_results_keyboard(lang))
        return
    batch = vacancy_dicts[:RESULTS_PAGE_SIZE]
    await state.update_data(vacancies=batch, current_page=0, total_new=len(vacancy_dicts))
    await state.set_state(SearchStates.showing_results)
    mark_vacancies_viewed(callback.from_user.id, _batch_vacancy_ids(0, batch))
    await callback.message.edit_text(f"{t('found', lang, count=len(batch))}\n\n{vacancy_text(batch[0], lang)}", reply_markup=results_keyboard(0, len(batch), batch[0]["url"], lang))


@router.callback_query(SearchStates.showing_results, F.data.startswith("page:"))
async def pagination_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    if not vacancies:
        await callback.answer(t("stale_results", data.get("lang", "ru")), show_alert=True)
        return
    page = int(data.get("current_page", 0))
    action = callback.data.split(":", 1)[1]
    if action == "next" and page < len(vacancies) - 1:
        page += 1
    elif action == "prev" and page > 0:
        page -= 1
    else:
        await callback.answer()
        return
    await render_search_result(callback, state, page)


@router.callback_query(SearchStates.showing_results, F.data == "find_more")
async def find_more_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    category = data.get("category", "other")
    skills = list(data.get("skills", []))
    lang = data.get("lang", "ru")
    await callback.answer()
    try:
        all_vacancies = await asyncio.wait_for(fetch_all_vacancies(), timeout=65)
        vacancy_dicts = build_new_vacancy_dicts(all_vacancies, category, skills, callback.from_user.id)
    except Exception:
        await callback.message.edit_text(t("fetch_error", lang), reply_markup=empty_results_keyboard(lang))
        return
    if not vacancy_dicts:
        await callback.message.edit_text(t("no_results", lang), reply_markup=empty_results_keyboard(lang))
        return
    batch = vacancy_dicts[:RESULTS_PAGE_SIZE]
    await state.update_data(vacancies=batch, current_page=0, total_new=len(vacancy_dicts))
    await state.set_state(SearchStates.showing_results)
    mark_vacancies_viewed(callback.from_user.id, _batch_vacancy_ids(0, batch))
    await callback.message.edit_text(f"{t('found', lang, count=len(batch))}\n\n{vacancy_text(batch[0], lang)}", reply_markup=results_keyboard(0, len(batch), batch[0]["url"], lang))


@router.callback_query(F.data == "history_view")
async def history_view_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang") or get_user_language(callback.from_user.id) or "ru"
    items = get_user_viewed_vacancies(callback.from_user.id)
    if not items:
        await callback.message.edit_text(t("history_empty", lang), reply_markup=empty_results_keyboard(lang))
        return
    await state.clear()
    await state.update_data(lang=lang, history_vacancies=items, current_page=0)
    await state.set_state(SearchStates.viewing_history)
    await render_history_result(callback, state, 0)


@router.callback_query(SearchStates.viewing_history, F.data.startswith("hp:"))
async def history_pagination_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    vacancies = data.get("history_vacancies", [])
    if not vacancies:
        await callback.answer(t("stale_results", data.get("lang", "ru")), show_alert=True)
        return
    page = int(data.get("current_page", 0))
    action = callback.data.split(":", 1)[1]
    if action == "next" and page < len(vacancies) - 1:
        page += 1
    elif action == "prev" and page > 0:
        page -= 1
    else:
        await callback.answer()
        return
    await render_history_result(callback, state, page)


@router.callback_query(SearchStates.showing_results, F.data.startswith("custom_page:"))
async def custom_pagination_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    posts = data.get("custom_results", [])
    if not posts:
        await callback.answer(t("stale_results", lang), show_alert=True)
        return
    page = int(data.get("current_page", 0))
    action = callback.data.split(":", 1)[1]
    if action == "next" and page < len(posts) - 1:
        page += 1
    elif action == "prev" and page > 0:
        page -= 1
    await state.update_data(current_page=page)
    post = posts[page]
    await callback.answer()
    try:
        await callback.message.edit_text(custom_post_text(post, data.get("custom_keywords", []), lang), reply_markup=custom_results_keyboard(page, len(posts), post["url"], lang))
    except Exception:
        pass


@router.callback_query(F.data == "history_clear")
async def history_clear_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = (await state.get_data()).get("lang", "ru")
    clear_viewed_vacancies(callback.from_user.id)
    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(SearchStates.choosing_category)
    await callback.answer()
    await callback.message.edit_text(t("history_cleared", lang), reply_markup=categories_keyboard(lang))



