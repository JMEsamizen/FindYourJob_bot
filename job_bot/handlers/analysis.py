import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from ai_analysis import analysis_url, analyze_vacancy, format_analysis
from db import analysis_limit_allows
from i18n import t
from keyboards import learning_keyboard, learning_skills_keyboard, learning_video_keyboard, premium_keyboard, stats_keyboard, stats_materials_keyboard
from learning import learning_skills, material_for, materials_for
from parser import fetch_all_vacancies
from profile import load_profile
from states import SearchStates

router = Router()


@router.callback_query(F.data.startswith("analyze:"))
async def analyze_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = (await state.get_data()).get("lang") or "ru"
    profile = load_profile(callback.from_user.id)
    if profile is None:
        await callback.answer(t("profile_needed", lang), show_alert=True)
        return
    if not analysis_limit_allows(callback.from_user.id):
        await callback.answer("🔒 Лимит «Анализ вакансии» исчерпан.", show_alert=True)
        return
    try:
        target_url = analysis_url(callback.data)
        vacancies = await asyncio.wait_for(fetch_all_vacancies(), timeout=65)
        vacancy = next((item for item in vacancies if item.url == target_url), None)
        if vacancy is None:
            await callback.answer("Вакансия больше недоступна.", show_alert=True)
            return
        await callback.answer("Анализ готовится...")
        result = await analyze_vacancy(profile, vacancy)
        missing_skills = list(dict.fromkeys(result["missing_skills"]))[:6]
        available_skills = [material.skill for material in materials_for(missing_skills)]
        await state.update_data(learning_skills=available_skills)
        reply_markup = learning_keyboard(available_skills) if available_skills else None
        await callback.message.answer(format_analysis(result), reply_markup=reply_markup)
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
    used, count = consume_learning_use(callback.from_user.id)
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
        upsert_learning_progress(callback.from_user.id, skill)
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
    upsert_learning_progress(callback.from_user.id, skill, "completed")
    await callback.answer("Навык отмечен как изученный")


@router.callback_query(F.data == "progress_menu")
async def progress_menu_handler(callback: CallbackQuery) -> None:
    profile = load_profile(callback.from_user.id)
    if profile is None:
        await callback.answer("У вас пока нет персонального профиля.", show_alert=True)
        return
    progress = get_learning_progress(callback.from_user.id)
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
    await callback.message.edit_text(text, reply_markup=None)


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
    lang = get_user_language(callback.from_user.id) or "ru"
    material = material_for(skill)
    await callback.answer()
    if material is None:
        await callback.message.answer(t("stats_learn_none", lang, skill=skill), reply_markup=stats_keyboard(lang))
        return
    await callback.message.answer(t("stats_learn_intro", lang, skill=material.skill), reply_markup=stats_materials_keyboard(material, lang))
