from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db import get_user_language, get_user_profile, set_user_profile_active
from i18n import t
from keyboards import login_keyboard, profile_create_keyboard, profile_menu_keyboard
from profile import display_profile, load_profile, profile_complete
from states import SearchStates

router = Router()


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
        has_real_profile = bool(existing) and any(existing.get(key) for key in ("field", "specialization", "skills", "preferred_roles", "experience_level"))
        if has_real_profile:
            await callback.message.edit_text(t("login_required", lang), reply_markup=login_keyboard(lang))
        else:
            await callback.message.edit_text(t("no_active_profile", lang), reply_markup=profile_create_keyboard(lang))
        return
    await callback.message.edit_text(display_profile(profile), reply_markup=profile_menu_keyboard(lang=lang))
