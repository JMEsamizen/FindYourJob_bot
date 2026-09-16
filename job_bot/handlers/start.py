import asyncio

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import get_user_language, set_user_language
from i18n import t
from keyboards import categories_keyboard, language_keyboard
from services.search_service import categories_text, custom_channel_prompt, custom_post_text, parse_custom_keywords, skills_text
from states import SearchStates

router = Router()


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


@router.callback_query(F.data == "language")
async def change_language_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(t("language_prompt"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("language:"))
async def language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", 1)[1]
    set_user_language(callback.from_user.id, lang)
    data = await state.get_data()
    await state.update_data(lang=lang)
    current_state = await state.get_state()
    await callback.answer()
    if current_state == SearchStates.showing_results.state and (data.get("vacancies") or data.get("custom_results")):
        page = int(data.get("current_page", 0))
        vacancies = data.get("custom_results") if data.get("custom_mode") else data.get("vacancies", [])
        vacancy = vacancies[page]
        if data.get("custom_mode"):
            await callback.message.edit_text(
                custom_post_text(vacancy, data.get("custom_keywords", []), lang),
                reply_markup=None,
            )
        else:
            await callback.message.edit_text(vacancy["text"], reply_markup=None)
    elif current_state == SearchStates.choosing_skills.state:
        category = data.get("category", "other")
        skills = list(data.get("skills", []))
        await callback.message.edit_text(skills_text(category, skills, lang), reply_markup=None)
    elif current_state == SearchStates.choosing_custom_keywords.state:
        await callback.message.edit_text(t("custom_keywords_prompt", lang, channel=data.get("custom_channel", "")))
    elif current_state == SearchStates.choosing_custom_channel.state:
        await callback.message.edit_text(custom_channel_prompt(lang))
    else:
        await state.set_state(SearchStates.choosing_category)
        await callback.message.edit_text(categories_text(lang), reply_markup=categories_keyboard(lang))
