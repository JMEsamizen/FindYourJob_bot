from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    choosing_category = State()
    choosing_skills = State()
    showing_results = State()
    choosing_custom_channel = State()
    choosing_custom_keywords = State()
    viewing_history = State()


class ProfileRegistrationStates(StatesGroup):
    start = State()
    full_name = State()
    age = State()
    city = State()
    education_level = State()
    employment_status = State()
    desired_position = State()
    experience_level = State()
    skills = State()
    preferred_language = State()
    expected_salary = State()
    review = State()
    completed = State()
