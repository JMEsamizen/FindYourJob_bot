from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db import get_user_profile
from keyboards import categories_keyboard
from services.profile_registration_service import (
    EDUCATION_LEVELS,
    EMPLOYMENT_STATUSES,
    EXPERIENCE_LEVELS,
    PREFERRED_LANGUAGES,
    build_profile_document,
    save_registration_profile,
    validate_registration_step,
)
from states import ProfileRegistrationStates

router = Router()

REGISTRATION_STEP_TEXT = {
    "full_name": "Введите ваше полное имя.",
    "age": "Укажите ваш возраст (или нажмите 'Пропустить').",
    "city": "Укажите ваш город.",
    "education_level": "Выберите уровень образования:",
    "employment_status": "Выберите тип занятости:",
    "desired_position": "Напишите желаемую должность.",
    "experience_level": "Выберите уровень опыта:",
    "skills": "Введите ваши ключевые навыки через запятую.",
    "preferred_language": "Выберите язык общения:",
    "expected_salary": "Укажите ожидаемую зарплату или напишите 'skip'.",
}


async def _start_registration(callback: CallbackQuery, state: FSMContext, *, edit_mode: bool = False) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.clear()
    await state.update_data(lang=data.get("lang", "ru"), edit_mode=edit_mode, registration={})
    await state.set_state(ProfileRegistrationStates.full_name)
    await callback.message.edit_text(REGISTRATION_STEP_TEXT["full_name"])


async def _advance_registration(message: Message, state: FSMContext, field: str, value: object) -> None:
    validation_error = validate_registration_step(field, value)
    if validation_error:
        await message.answer(validation_error)
        return

    data = await state.get_data()
    reg = dict(data.get("registration", {}))
    reg[field] = value
    await state.update_data(registration=reg)

    next_step = {
        "full_name": "age",
        "age": "city",
        "city": "education_level",
        "education_level": "employment_status",
        "employment_status": "desired_position",
        "desired_position": "experience_level",
        "experience_level": "skills",
        "skills": "preferred_language",
        "preferred_language": "expected_salary",
        "expected_salary": "review",
    }.get(field)

    if not next_step:
        return

    if next_step == "review":
        profile = build_profile_document(reg)
        await state.update_data(registration=profile)
        await state.set_state(ProfileRegistrationStates.review)
        age_text = profile['age'] if profile.get('age') is not None else 'не указан'
        summary = (
            "Проверьте данные профиля:\n\n"
            f"Имя: {profile['full_name']}\n"
            f"Возраст: {age_text}\n"
            f"Город: {profile['city']}\n"
            f"Образование: {profile['education_level']}\n"
            f"Занятость: {profile['employment_status']}\n"
            f"Желаемая должность: {profile['desired_position']}\n"
            f"Опыт: {profile['experience_level']}\n"
            f"Навыки: {', '.join(profile['skills'])}\n"
            f"Язык: {profile['preferred_language']}\n"
            f"Желаемая зарплата: {profile['expected_salary'] or 'не указана'}\n\n"
            "Нажмите /confirm_profile, чтобы сохранить профиль, или /cancel_registration — чтобы начать заново."
        )
        await message.answer(summary)
        return

    await state.set_state(getattr(ProfileRegistrationStates, next_step))
    await message.answer(REGISTRATION_STEP_TEXT[next_step])


@router.callback_query(F.data.in_({"profile_create", "profile_edit"}))
async def profile_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    edit_mode = callback.data == "profile_edit"
    if edit_mode and get_user_profile(callback.from_user.id) is None:
        await callback.answer("Сначала создайте профиль.", show_alert=True)
        return
    await _start_registration(callback, state, edit_mode=edit_mode)


@router.callback_query(ProfileRegistrationStates.education_level, F.data.startswith("profile:select:education_level:"))
async def education_level_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.rsplit(":", 1)[1]
    await callback.answer()
    await _advance_registration(callback.message, state, "education_level", value)


@router.callback_query(ProfileRegistrationStates.employment_status, F.data.startswith("profile:select:employment_status:"))
async def employment_status_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.rsplit(":", 1)[1]
    await callback.answer()
    await _advance_registration(callback.message, state, "employment_status", value)


@router.callback_query(ProfileRegistrationStates.experience_level, F.data.startswith("profile:select:experience_level:"))
async def experience_level_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.rsplit(":", 1)[1]
    await callback.answer()
    await _advance_registration(callback.message, state, "experience_level", value)


@router.callback_query(ProfileRegistrationStates.preferred_language, F.data.startswith("profile:select:preferred_language:"))
async def preferred_language_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.rsplit(":", 1)[1]
    await callback.answer()
    await _advance_registration(callback.message, state, "preferred_language", value)


@router.message(ProfileRegistrationStates.full_name)
async def registration_full_name_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "full_name", message.text)


@router.message(ProfileRegistrationStates.age)
async def registration_age_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "age", message.text)


@router.message(ProfileRegistrationStates.city)
async def registration_city_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "city", message.text)


@router.message(ProfileRegistrationStates.desired_position)
async def registration_desired_position_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "desired_position", message.text)


@router.message(ProfileRegistrationStates.skills)
async def registration_skills_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "skills", message.text)


@router.message(ProfileRegistrationStates.expected_salary)
async def registration_expected_salary_handler(message: Message, state: FSMContext) -> None:
    raw = message.text or ""
    value = "skip" if raw.strip().lower() in {"skip", "пропустить", "none", "нет"} else raw
    await _advance_registration(message, state, "expected_salary", value)


@router.message(ProfileRegistrationStates.review)
async def registration_review_handler(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text in {"/confirm_profile", "confirm", "сохранить", "save"}:
        data = await state.get_data()
        payload = dict(data.get("registration", {}))
        saved = save_registration_profile(message.from_user.id, payload)
        if saved is None:
            await message.answer("Не удалось сохранить профиль. Проверьте введённые данные.")
            return
        await state.clear()
        await state.update_data(lang=data.get("lang", "ru"))
        await state.set_state(None)
        await message.answer("Профиль успешно создан. Вы можете продолжить поиск.", reply_markup=categories_keyboard(data.get("lang", "ru")))
        return
    if text in {"/cancel_registration", "cancel", "restart", "сбросить", "начать заново"}:
        await state.clear()
        await state.update_data(lang=data.get("lang", "ru"))
        await message.answer("Регистрация отменена. Можно начать заново.", reply_markup=categories_keyboard(data.get("lang", "ru")))
        return
    await message.answer("Нажмите /confirm_profile, чтобы сохранить профиль, или /cancel_registration — чтобы начать заново.")


@router.callback_query(F.data == "profile_cancel")
async def profile_cancel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    await state.update_data(lang=lang)
    await callback.answer()
    await callback.message.edit_text("Регистрация отменена. Можно начать заново.", reply_markup=categories_keyboard(lang))


@router.message(Command("cancel_registration"))
async def command_cancel_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(lang=(await state.get_data()).get("lang", "ru"))
    await message.answer("Регистрация отменена. Можно начать заново.")


@router.message(Command("confirm_profile"))
async def command_confirm_profile(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    payload = dict(data.get("registration", {}))
    saved = save_registration_profile(message.from_user.id, payload)
    if saved is None:
        await message.answer("Не удалось сохранить профиль. Проверьте введённые данные.")
        return
    await state.clear()
    await state.update_data(lang=data.get("lang", "ru"))
    await message.answer("Профиль успешно создан.", reply_markup=categories_keyboard(data.get("lang", "ru")))


def _selection_keyboard(title: str, options: dict[str, str]) -> list[list[str]]:
    rows = []
    for key, label in options.items():
        rows.append([f"{title}:{key}"])
    return rows


@router.callback_query(F.data == "profile_choices_education")
async def profile_education_choice_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ProfileRegistrationStates.education_level)
    keyboard = []
    for key, label in EDUCATION_LEVELS.items():
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"profile:select:education_level:{key}")])
    await callback.message.edit_text(REGISTRATION_STEP_TEXT["education_level"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == "profile_choices_employment")
async def profile_employment_choice_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ProfileRegistrationStates.employment_status)
    keyboard = []
    for key, label in EMPLOYMENT_STATUSES.items():
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"profile:select:employment_status:{key}")])
    await callback.message.edit_text(REGISTRATION_STEP_TEXT["employment_status"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == "profile_choices_experience")
async def profile_experience_choice_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ProfileRegistrationStates.experience_level)
    keyboard = []
    for key, label in EXPERIENCE_LEVELS.items():
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"profile:select:experience_level:{key}")])
    await callback.message.edit_text(REGISTRATION_STEP_TEXT["experience_level"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == "profile_choices_language")
async def profile_language_choice_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ProfileRegistrationStates.preferred_language)
    keyboard = []
    for key, label in PREFERRED_LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"profile:select:preferred_language:{key}")])
    await callback.message.edit_text(REGISTRATION_STEP_TEXT["preferred_language"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.message(ProfileRegistrationStates.education_level)
async def registration_education_level_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "education_level", (message.text or "").strip())


@router.message(ProfileRegistrationStates.employment_status)
async def registration_employment_status_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "employment_status", (message.text or "").strip())


@router.message(ProfileRegistrationStates.experience_level)
async def registration_experience_level_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "experience_level", (message.text or "").strip())


@router.message(ProfileRegistrationStates.preferred_language)
async def registration_preferred_language_handler(message: Message, state: FSMContext) -> None:
    await _advance_registration(message, state, "preferred_language", (message.text or "").strip())


__all__ = ["router"]
