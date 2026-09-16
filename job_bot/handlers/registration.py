from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from i18n import t
from keyboards import profile_experience_keyboard, profile_field_keyboard, profile_hours_keyboard, profile_level_choice_keyboard, profile_specialization_keyboard, profile_skill_keyboard, profile_work_format_keyboard
from profile import PROFILE_FIELDS, load_profile, save_profile
from states import SearchStates

router = Router()


async def begin_profile_onboarding(callback: CallbackQuery, state: FSMContext, *, edit_mode: bool = False) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    await state.update_data(
        lang=lang,
        edit_mode=edit_mode,
        field=None,
        specialization=None,
        skills=[],
        level=None,
        work_format=None,
        experience=None,
        hours=None,
        city=None,
        preferred_roles=[],
        work_formats=[],
        locations=[],
        languages=[],
    )
    if edit_mode:
        existing = load_profile(callback.from_user.id) or {}
        await state.update_data(**existing)
    await state.set_state(SearchStates.profile_field)
    await callback.message.edit_text(t("profile_field_prompt", lang), reply_markup=profile_field_keyboard(lang))


async def finish_profile_field(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("work_format") == "online":
        data["city"] = "online"
    profile = save_profile(callback.from_user.id, data)
    await state.clear()
    if profile is None:
        await callback.answer(t("profile_save_failed", data.get("lang", "ru")), show_alert=True)
        return
    lang = data.get("lang", "ru")
    await state.update_data(lang=lang)
    await state.set_state(SearchStates.choosing_category)
    await callback.answer()
    await callback.message.edit_text(t("profile_saved", lang), reply_markup=None)


@router.callback_query(F.data.in_({"profile_create", "profile_edit"}))
async def profile_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.data == "profile_edit":
        profile = load_profile(callback.from_user.id)
        if profile is None:
            await callback.answer("Сначала создайте профиль.", show_alert=True)
            return
        await begin_profile_onboarding(callback, state, edit_mode=True)
        return
    await begin_profile_onboarding(callback, state)


@router.callback_query(SearchStates.profile_field, F.data.startswith("profile:field:"))
async def profile_field_handler(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.rsplit(":", 1)[1]
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(field=field, specialization=None, skills=[])
    await callback.answer()
    await state.set_state(SearchStates.profile_specialization)
    await callback.message.edit_text(
        t("profile_specialization_prompt", lang, label=PROFILE_FIELDS.get(field, PROFILE_FIELDS["other"])["label"]),
        reply_markup=profile_specialization_keyboard(field, None),
    )


@router.callback_query(SearchStates.profile_specialization, F.data.startswith("profile:specialization:"))
async def profile_specialization_handler(callback: CallbackQuery, state: FSMContext) -> None:
    specialization = callback.data.rsplit(":", 1)[1]
    data = await state.get_data()
    await state.update_data(specialization=specialization)
    field = data.get("field") or "other"
    skills = PROFILE_FIELDS.get(field, PROFILE_FIELDS["other"])["skills"].get(specialization, [])
    await state.set_state(SearchStates.profile_skills)
    await callback.answer()
    await callback.message.edit_text(
        t("profile_skills_prompt", data.get("lang", "ru")),
        reply_markup=profile_skill_keyboard(field, specialization, data.get("skills", [])),
    )


@router.callback_query(SearchStates.profile_skills, F.data.startswith("profile:skill:"))
async def profile_skills_handler(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.rsplit(":", 1)[1]
    data = await state.get_data()
    field = data.get("field") or "other"
    specialization = data.get("specialization") or "other"
    selected = list(data.get("skills", []))
    if key == "done":
        if not selected:
            await callback.answer(t("profile_skills_required", data.get("lang", "ru")), show_alert=True)
            return
        await state.set_state(SearchStates.profile_level)
        await callback.answer()
        await callback.message.edit_text(t("profile_level_prompt", data.get("lang", "ru")), reply_markup=profile_level_choice_keyboard())
        return
    if key in selected:
        selected.remove(key)
    else:
        selected.append(key)
    await state.update_data(skills=selected)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=profile_skill_keyboard(field, specialization, selected))


@router.callback_query(SearchStates.profile_level, F.data.startswith("profile:level:"))
async def profile_level_choice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.rsplit(":", 1)[1]
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(level=level)
    await state.set_state(SearchStates.profile_work_format)
    await callback.answer()
    await callback.message.edit_text(t("profile_work_format_prompt", lang), reply_markup=profile_work_format_keyboard())


@router.callback_query(SearchStates.profile_work_format, F.data.startswith("profile:work_format:"))
async def profile_work_format_handler(callback: CallbackQuery, state: FSMContext) -> None:
    work_format = callback.data.rsplit(":", 1)[1]
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(work_format=work_format)
    await state.set_state(SearchStates.profile_experience)
    await callback.answer()
    await callback.message.edit_text(t("profile_experience_prompt", lang), reply_markup=profile_experience_keyboard())


@router.callback_query(SearchStates.profile_experience, F.data.startswith("profile:experience:"))
async def profile_experience_handler(callback: CallbackQuery, state: FSMContext) -> None:
    experience = callback.data.rsplit(":", 1)[1]
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(experience=experience)
    await state.set_state(SearchStates.profile_hours)
    await callback.answer()
    await callback.message.edit_text(t("profile_hours_prompt", lang), reply_markup=profile_hours_keyboard())


@router.callback_query(SearchStates.profile_hours, F.data.startswith("profile:hours:"))
async def profile_hours_handler(callback: CallbackQuery, state: FSMContext) -> None:
    hours = callback.data.rsplit(":", 1)[1]
    await state.update_data(hours=hours)
    await callback.answer()
    await finish_profile_field(callback, state)
