from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db import get_recent_vacancies, get_user_profile
from i18n import t
from keyboards import stats_keyboard, stats_materials_keyboard
from learning import material_for
from stats import build_market_stats_message

router = Router()


@router.callback_query(F.data == "market_stats")
async def market_stats_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    lang = (await state.get_data()).get("lang") or "ru"
    vacancies = get_recent_vacancies(14)
    profile = get_user_profile(callback.from_user.id) or {}
    result = build_market_stats_message(vacancies, lang=lang, profile=profile, days=7)
    await callback.message.edit_text(result["text"], reply_markup=stats_keyboard(lang, result["learn_skill"]))


@router.callback_query(F.data.startswith("stats_learn:"))
async def stats_learn_handler(callback: CallbackQuery) -> None:
    skill = callback.data.split(":", 1)[1]
    lang = "ru"
    material = material_for(skill)
    await callback.answer()
    if material is None:
        await callback.message.answer(t("stats_learn_none", lang, skill=skill), reply_markup=stats_keyboard(lang))
        return
    await callback.message.answer(t("stats_learn_intro", lang, skill=material.skill), reply_markup=stats_materials_keyboard(material, lang))
