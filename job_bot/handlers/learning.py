from aiogram import F, Router
from aiogram.types import CallbackQuery

from db import consume_learning_use, get_learning_progress, upsert_learning_progress
from keyboards import learning_keyboard, learning_skills_keyboard, learning_video_keyboard, premium_keyboard
from learning import learning_skills, material_for, materials_for
from profile import load_profile

router = Router()


@router.callback_query((F.data == "learn") | F.data.startswith("learn:"))
async def learning_handler(callback: CallbackQuery, state) -> None:
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
