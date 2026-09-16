import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import clear_viewed_vacancies, get_recent_vacancies, get_user_viewed_vacancies, get_user_profile, get_viewed_vacancy_ids, mark_vacancies_viewed
from i18n import t
from keyboards import categories_keyboard, custom_empty_results_keyboard, custom_results_keyboard, empty_results_keyboard, history_results_keyboard, results_keyboard, skills_keyboard
from parser import Vacancy, fetch_all_vacancies, fetch_channel_posts
from services.search_service import (
    RESULTS_PAGE_SIZE,
    build_new_vacancy_dicts,
    categories_text,
    custom_channel_prompt,
    custom_post_text,
    find_more_visible,
    normalize_channel_username,
    parse_custom_keywords,
    skills_text,
    vacancy_text,
    _batch_vacancy_ids,
)
from states import SearchStates
from vacancy_filter import filter_posts_by_keywords

router = Router()


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
    try:
        await callback.message.edit_text(
            text,
            reply_markup=history_results_keyboard(page, len(vacancies), vacancy["url"], lang),
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "history_clear")
async def history_clear_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = (await state.get_data()).get("lang", "ru")
    clear_viewed_vacancies(callback.from_user.id)
    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(SearchStates.choosing_category)
    await callback.answer()
    await callback.message.edit_text(t("history_cleared", lang), reply_markup=categories_keyboard(lang))


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
    lang = data.get("lang") or "ru"
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
