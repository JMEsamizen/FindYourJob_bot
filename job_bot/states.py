from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    choosing_category = State()
    choosing_skills = State()
    showing_results = State()
    choosing_custom_channel = State()
    choosing_custom_keywords = State()
    viewing_history = State()
    profile_field = State()
    profile_specialization = State()
    profile_skills = State()
    profile_level = State()
    profile_work_format = State()
    profile_experience = State()
    profile_hours = State()
    profile_city = State()
    profile_experience_level = State()
    profile_roles = State()
    profile_work_formats = State()
    profile_locations = State()
    profile_languages = State()
