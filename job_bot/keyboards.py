from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ai_analysis import analysis_callback_data
from learning import learning_callback_data, materials_for
from i18n import SKILLS, category_label, skill_label, t
from profile import EXPERIENCE, HOURS, LANGUAGES, LEVELS, LOCATIONS, PROFILE_FIELDS, ROLES, WORK_FORMATS


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="language:ru")],
        [InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="language:uz")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="language:en")],
    ])


def categories_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=category_label(key, lang), callback_data=f"category:{key}") for key in SKILLS]
    rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text=t("custom_search", lang), callback_data="custom_search")])
    rows.append([InlineKeyboardButton(text=t("stats_week", lang), callback_data="market_stats")])
    rows.append([InlineKeyboardButton(text=t("my_profile", lang), callback_data="profile_menu")])
    rows.append([InlineKeyboardButton(text=t("change_language", lang), callback_data="language")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skills_keyboard(category: str, selected: list[str], lang: str) -> InlineKeyboardMarkup:
    skills = SKILLS.get(category, SKILLS["other"])
    rows = []
    for index in range(0, len(skills), 2):
        row = []
        for skill in skills[index:index + 2]:
            mark = "✅" if skill in selected else "⬜"
            row.append(InlineKeyboardButton(text=f"{mark} {skill_label(skill, lang)}", callback_data=f"skill:{skill}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("find", lang), callback_data="skills_done")])
    rows.append([
        InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search"),
        InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu"),
    ])
    rows.append([InlineKeyboardButton(text=t("change_language", lang), callback_data="language")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def results_keyboard(page: int, total: int, url: str, lang: str, show_find_more: bool = False, prefix: str = "page") -> InlineKeyboardMarkup:
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text=t("prev", lang), callback_data=f"{prefix}:prev"))
    navigation.append(InlineKeyboardButton(text=f"{page + 1} / {total}", callback_data=f"{prefix}:current"))
    if page < total - 1:
        navigation.append(InlineKeyboardButton(text=t("next", lang), callback_data=f"{prefix}:next", style="success"))
    rows = [
        [InlineKeyboardButton(text=t("open", lang), url=url)],
        [InlineKeyboardButton(text="🤖 Анализ вакансии", callback_data=analysis_callback_data(url))],
        navigation,
    ]
    if show_find_more:
        rows.append([InlineKeyboardButton(text=t("find_more", lang), callback_data="find_more")])
    rows.extend([
        [
            InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search"),
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu"),
        ],
        [InlineKeyboardButton(text=t("change_language", lang), callback_data="language")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def empty_results_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu")],
        [InlineKeyboardButton(text=t("change_language", lang), callback_data="language")],
    ])


def custom_results_keyboard(page: int, total: int, url: str, lang: str) -> InlineKeyboardMarkup:
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text=t("prev", lang), callback_data="custom_page:prev"))
    navigation.append(InlineKeyboardButton(text=f"{page + 1} / {total}", callback_data="custom_page:current"))
    if page < total - 1:
        navigation.append(InlineKeyboardButton(text=t("next", lang), callback_data="custom_page:next"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("open", lang), url=url)],
        [InlineKeyboardButton(text="🤖 Анализ вакансии", callback_data=analysis_callback_data(url))],
        navigation,
        [InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu")],
        [InlineKeyboardButton(text=t("change_language", lang), callback_data="language")],
    ])


def custom_empty_results_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")],
        [InlineKeyboardButton(text=t("edit_keywords", lang), callback_data="edit_custom_keywords")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu")],
        [InlineKeyboardButton(text=t("change_language", lang), callback_data="language")],
    ])


def history_results_keyboard(page: int, total: int, url: str, lang: str) -> InlineKeyboardMarkup:
    """Keyboard for the viewing-history mode: reuse the vacancy card buttons + clear history."""
    rows = list(results_keyboard(page, total, url, lang, show_find_more=False, prefix="hp").inline_keyboard)
    rows.append([InlineKeyboardButton(text=t("history_clear", lang), callback_data="history_clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="profile_edit")],
        [InlineKeyboardButton(text="📈 Мой прогресс", callback_data="progress_menu")],
        [InlineKeyboardButton(text="📊 Статистика недели", callback_data="market_stats")],
        [InlineKeyboardButton(text=t("history_view", lang), callback_data="history_view")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="language")],
        [InlineKeyboardButton(text=t("logout", lang), callback_data="profile_logout")],
        [InlineKeyboardButton(text="🔄 Новый поиск", callback_data="new_search")],
    ])


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Уровень", callback_data="profile_field:level")],
        [InlineKeyboardButton(text="🎯 Направления", callback_data="profile_field:roles")],
        [InlineKeyboardButton(text="🏠 Формат", callback_data="profile_field:work")],
        [InlineKeyboardButton(text="📍 Локация", callback_data="profile_field:location")],
        [InlineKeyboardButton(text="💼 Опыт", callback_data="profile_field:experience")],
        [InlineKeyboardButton(text="🌍 Языки", callback_data="profile_field:languages")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu")],
    ])


def profile_create_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("create_profile", lang), callback_data="profile_create")],
        [InlineKeyboardButton(text=t("stats_week", lang), callback_data="market_stats")],
        [InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")],
    ])


def login_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚪 {t('login', lang)}", callback_data="profile_login")],
        [InlineKeyboardButton(text=f"✍️ {t('register', lang)}", callback_data="profile_create")],
        [InlineKeyboardButton(text=t("stats_week", lang), callback_data="market_stats")],
        [InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")],
    ])


def stats_keyboard(lang: str = "ru", learn_skill: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if learn_skill and materials_for([learn_skill]):
        rows.append([
            InlineKeyboardButton(
                text=t("stats_learn_btn", lang, skill=skill_label(learn_skill, lang)),
                callback_data=f"stats_learn:{learn_skill}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")])
    rows.append([InlineKeyboardButton(text=t("my_profile", lang), callback_data="profile_menu")])
    rows.append([InlineKeyboardButton(text=t("change_language", lang), callback_data="language")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stats_materials_keyboard(material: object, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    youtube_url = getattr(material, "youtube_url", None) or getattr(material, "url", None)
    if youtube_url:
        rows.append([InlineKeyboardButton(text=t("stats_learn_youtube", lang), url=youtube_url)])
    w3_url = getattr(material, "w3_url", None)
    if w3_url:
        rows.append([InlineKeyboardButton(text=t("stats_learn_w3", lang), url=w3_url)])
    rows.append([InlineKeyboardButton(text=t("back_stats", lang), callback_data="market_stats")])
    rows.append([InlineKeyboardButton(text=t("new_search", lang), callback_data="new_search")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_field_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for key, info in PROFILE_FIELDS.items():
        rows.append([InlineKeyboardButton(text=info["label"], callback_data=f"profile:field:{key}")])
    rows.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_specialization_keyboard(field: str, selected: str | None = None) -> InlineKeyboardMarkup:
    options = PROFILE_FIELDS.get(field, PROFILE_FIELDS["other"])
    rows = []
    for key, label in options["specializations"].items():
        mark = "✅ " if selected == key else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"profile:specialization:{key}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="profile_create")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_skill_keyboard(field: str, specialization: str, selected: list[str]) -> InlineKeyboardMarkup:
    options = PROFILE_FIELDS.get(field, PROFILE_FIELDS["other"])["skills"].get(specialization, [])
    rows = []
    for index in range(0, len(options), 2):
        row = []
        for item in options[index:index + 2]:
            label = item.replace("_", " ").title()
            mark = "✅" if item in selected else "⬜"
            row.append(InlineKeyboardButton(text=f"{mark} {label}", callback_data=f"profile:skill:{item}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✅ Готово", callback_data="profile:skill:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_level_choice_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(LEVELS, "level")


def profile_work_format_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(WORK_FORMATS, "work_format")


def profile_hours_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(HOURS, "hours")


def profile_city_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(LOCATIONS, "city")


def profile_single_choice(items: dict[str, str], prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"profile:{prefix}:{key}")]
        for key, label in items.items()
    ])


def profile_multi_choice(items: dict[str, str], prefix: str, selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for key, label in items.items():
        mark = "✅" if key in selected else "⬜"
        rows.append([InlineKeyboardButton(text=f"{mark} {label}", callback_data=f"profile:{prefix}:{key}")])
    rows.append([InlineKeyboardButton(text="✅ Готово", callback_data=f"profile:{prefix}:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_level_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(LEVELS, "level")


def profile_roles_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    return profile_multi_choice(ROLES, "roles", selected)


def profile_work_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(WORK_FORMATS, "work")


def profile_location_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(LOCATIONS, "location")


def profile_experience_keyboard() -> InlineKeyboardMarkup:
    return profile_single_choice(EXPERIENCE, "experience")


def profile_languages_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    return profile_multi_choice(LANGUAGES, "languages", selected)


def learning_keyboard(skills: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Изучить", callback_data=learning_callback_data(skills))],
    ])


def learning_skills_keyboard(skills: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📚 {skill}", callback_data=f"learn_skill:{skill}")]
        for skill in skills
    ])


def learning_video_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="new_search")],
    ])


def materials_keyboard(materials: list[object]) -> InlineKeyboardMarkup:
    rows = []
    for material in materials:
        rows.append([InlineKeyboardButton(text=f"📚 {material.title}", url=material.url)])
        if getattr(material, "w3_url", None):
            rows.append([InlineKeyboardButton(text="🌐 W3Schools", url=material.w3_url)])
        rows.append([InlineKeyboardButton(text=f"✅ Изучено: {material.skill}", callback_data=f"learned:{material.skill}")])
    rows.append([InlineKeyboardButton(text="📈 Мой прогресс", callback_data="progress_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe_placeholder")],
    ])
