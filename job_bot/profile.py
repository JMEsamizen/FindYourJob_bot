from __future__ import annotations

from typing import Any

from db import get_user_profile, upsert_user_profile


LEVELS = {
    "not_known": "🌱 Не знаю",
    "intern": "Intern",
    "junior": "🟡 Junior",
    "middle": "🟠 Middle",
    "senior": "🔴 Senior",
}
ROLES = {"backend": "💻 Backend", "frontend": "🌐 Frontend", "fullstack": "🧩 Fullstack", "mobile": "📱 Mobile", "data": "📊 Data", "software": "🧠 Software", "ai_ml": "🤖 AI / ML", "ui_ux": "🎨 UI/UX", "graphic": "🖌 Graphic", "motion": "🎬 Motion", "3d": "🧊 3D", "brand": "🏷 Brand", "smm": "📢 SMM", "instagram": "📸 Instagram", "telegram": "💬 Telegram", "tiktok": "🎵 TikTok", "content": "📝 Content", "target": "🎯 Target", "community": "👥 Community", "qa": "🧪 QA", "devops": "⚙️ DevOps", "marketing": "📣 Marketing", "other": "📝 Other"}
WORK_FORMATS = {"online": "💻 Online", "offline": "🏢 Offline", "hybrid": "🔄 Hybrid", "any": "🌍 Не важно"}
LOCATIONS = {"tashkent": "📍 Ташкент", "samarkand": "📍 Самарканд", "andijan": "📍 Андижан", "bukhara": "📍 Бухара", "other": "🌆 Другой город", "online": "💻 Online only", "any": "🌍 Любой"}
EXPERIENCE = {"none": "Нет опыта", "0_1": "До 1 года", "1_3": "1–3 года", "3_5": "3–5 лет", "5_plus": "5+ лет"}
HOURS = {"1_2": "1–2", "3_4": "3–4", "5_6": "5–6", "7_8": "7–8", "fulltime": "Full-time", "any": "Не важно"}
LANGUAGES = {"uz": "🇺🇿 Uzbek", "ru": "🇷🇺 Russian", "en": "🇬🇧 English"}

PROFILE_FIELDS = {
    "programming": {
        "label": "Programming",
        "specializations": {
            "backend": "Backend",
            "frontend": "Frontend",
            "fullstack": "Fullstack",
            "mobile": "Mobile",
            "data": "Data",
            "software": "Software",
            "ai_ml": "AI/ML",
        },
        "skills": {
            "backend": ["python", "django", "fastapi", "sql", "postgresql", "java", "go", "php", "nodejs"],
            "frontend": ["javascript", "typescript", "react", "nextjs", "html", "css", "vue"],
            "fullstack": ["javascript", "typescript", "react", "nodejs", "python", "sql", "django", "fastapi"],
            "mobile": ["flutter", "kotlin", "swift", "react_native", "android", "ios"],
            "data": ["python", "sql", "pandas", "excel", "power_bi", "tableau", "analytics"],
            "software": ["python", "java", "cpp", "csharp", "linux", "docker", "git"],
            "ai_ml": ["python", "machine_learning", "deep_learning", "tensorflow", "pytorch", "nlp", "computer_vision"],
        },
    },
    "design": {
        "label": "Design",
        "specializations": {
            "ui_ux": "UI/UX",
            "graphic": "Graphic",
            "motion": "Motion",
            "3d": "3D",
            "brand": "Brand",
            "other": "Other",
        },
        "skills": {
            "ui_ux": ["ui_ux", "figma", "user_research", "wireframing"],
            "graphic": ["figma", "photoshop", "illustrator", "graphic_design"],
            "motion": ["after_effects", "premiere_pro", "motion_design", "animation"],
            "3d": ["blender", "3d_modeling", "maya", "zbrush"],
            "brand": ["branding", "figma", "photoshop", "copywriting"],
            "other": ["figma", "photoshop", "illustrator"],
        },
    },
    "smm": {
        "label": "SMM",
        "specializations": {
            "instagram": "Instagram",
            "telegram": "Telegram",
            "tiktok": "TikTok",
            "content": "Content",
            "target": "Target",
            "community": "Community",
            "other": "All at once",
        },
        "skills": {
            "instagram": ["instagram", "content_creation", "reels", "smm", "analytics"],
            "telegram": ["telegram", "copywriting", "community", "content_creation", "smm"],
            "tiktok": ["tiktok", "reels", "content_creation", "capcut", "analytics"],
            "content": ["content_creation", "copywriting", "canva", "premiere_pro", "smm"],
            "target": ["target_ads", "analytics", "copywriting", "instagram", "tiktok"],
            "community": ["community", "smm", "copywriting", "analytics", "content_creation"],
            "other": ["smm", "content_creation", "analytics", "copywriting", "target_ads"],
        },
    },
    "marketing": {
        "label": "Marketing",
        "specializations": {
            "seo": "SEO",
            "brand": "Brand",
            "performance": "Performance",
            "content": "Content",
            "analytics": "Analytics",
            "other": "Other",
        },
        "skills": {
            "seo": ["seo", "analytics", "content_creation", "copywriting"],
            "brand": ["branding", "content_creation", "copywriting", "analytics"],
            "performance": ["target_ads", "analytics", "google_analytics", "copywriting"],
            "content": ["content_creation", "copywriting", "canva", "seo"],
            "analytics": ["analytics", "excel", "power_bi", "seo"],
            "other": ["analytics", "seo", "copywriting", "content_creation"],
        },
    },
    "qa": {
        "label": "QA",
        "specializations": {
            "manual": "Manual QA",
            "automation": "Automation",
            "api": "API QA",
            "security": "Security QA",
            "other": "Other",
        },
        "skills": {
            "manual": ["manual_qa", "manual_testing", "test_cases", "bug_reports"],
            "automation": ["automation", "selenium", "postman", "java", "python"],
            "api": ["api_testing", "postman", "sql", "manual_qa"],
            "security": ["security_testing", "manual_qa", "api_testing", "sql"],
            "other": ["manual_qa", "automation", "postman", "api_testing"],
        },
    },
    "devops": {
        "label": "DevOps",
        "specializations": {
            "cloud": "Cloud",
            "infra": "Infrastructure",
            "linux": "Linux",
            "security": "Security",
            "other": "Other",
        },
        "skills": {
            "cloud": ["aws", "azure", "docker", "kubernetes", "terraform"],
            "infra": ["docker", "kubernetes", "linux", "terraform", "git"],
            "linux": ["linux", "bash", "docker", "git"],
            "security": ["linux", "docker", "aws", "security"],
            "other": ["docker", "linux", "kubernetes", "git"],
        },
    },
    "data": {
        "label": "Data",
        "specializations": {
            "analytics": "Analytics",
            "science": "Data Science",
            "bi": "BI / Reporting",
            "engineer": "Data Engineering",
            "other": "Other",
        },
        "skills": {
            "analytics": ["sql", "python", "excel", "power_bi", "analytics"],
            "science": ["python", "pandas", "machine_learning", "sql", "analytics"],
            "bi": ["sql", "power_bi", "tableau", "excel", "analytics"],
            "engineer": ["sql", "python", "postgresql", "docker", "airflow"],
            "other": ["sql", "python", "excel", "analytics"],
        },
    },
    "content": {
        "label": "Content",
        "specializations": {
            "copywriting": "Copywriting",
            "video": "Video",
            "writing": "Writing",
            "seo": "SEO",
            "other": "Other",
        },
        "skills": {
            "copywriting": ["copywriting", "seo", "content_creation", "canva"],
            "video": ["capcut", "premiere_pro", "content_creation", "canva"],
            "writing": ["copywriting", "content_creation", "seo"],
            "seo": ["seo", "content_creation", "copywriting", "analytics"],
            "other": ["copywriting", "content_creation", "seo", "canva"],
        },
    },
    "mobile": {
        "label": "Mobile",
        "specializations": {
            "android": "Android",
            "ios": "iOS",
            "cross": "Cross-platform",
            "other": "Other",
        },
        "skills": {
            "android": ["kotlin", "android", "flutter"],
            "ios": ["swift", "ios", "flutter"],
            "cross": ["flutter", "react_native", "kotlin", "swift"],
            "other": ["flutter", "react_native", "kotlin", "swift"],
        },
    },
    "ai_ml": {
        "label": "AI / ML",
        "specializations": {
            "ml": "ML",
            "nlp": "NLP",
            "vision": "Computer Vision",
            "data": "Data / AI",
            "other": "Other",
        },
        "skills": {
            "ml": ["python", "machine_learning", "deep_learning", "pytorch", "tensorflow"],
            "nlp": ["python", "nlp", "machine_learning", "pandas"],
            "vision": ["python", "computer_vision", "pytorch", "opencv"],
            "data": ["python", "machine_learning", "sql", "pandas"],
            "other": ["python", "machine_learning", "pytorch", "tensorflow"],
        },
    },
    "other": {
        "label": "Other",
        "specializations": {"other": "Other"},
        "skills": {"other": ["support", "sales", "project_manager", "hr"]},
    },
}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def profile_complete(data: dict[str, Any]) -> bool:
    if any(key in data for key in ("field", "specialization", "skills")):
        return bool(
            data.get("field")
            and data.get("specialization")
            and data.get("skills")
            and data.get("level")
            and data.get("work_format")
            and data.get("experience")
            and data.get("hours")
        )
    return all(data.get(key) for key in ("experience_level", "preferred_roles", "work_formats", "locations", "experience", "languages"))


def display_profile(profile: dict[str, Any]) -> str:
    def labels(values: list[str], source: dict[str, str]) -> str:
        if not values:
            return "—"
        return ", ".join(source.get(value, value) for value in values)

    if profile.get("field") or profile.get("specialization"):
        field = profile.get("field") or "other"
        specialization = profile.get("specialization") or "other"
        skills = _as_list(profile.get("skills", []))
        work_format = profile.get("work_format") or profile.get("work_formats", ["any"])[0]
        city = profile.get("city") or (profile.get("locations") or ["any"])[0]
        return (
            "👤 Профиль\n\n"
            f"🔹 Сфера: {PROFILE_FIELDS.get(field, {}).get('label', field)}\n"
            f"🎯 Специализация: {PROFILE_FIELDS.get(field, {}).get('specializations', {}).get(specialization, specialization)}\n"
            f"💡 Навыки: {', '.join(skills) if skills else '—'}\n"
            f"📊 Уровень: {LEVELS.get(profile.get('level'), profile.get('level', 'Не знаю'))}\n"
            f"💼 Формат: {WORK_FORMATS.get(work_format, work_format)}\n"
            f"⏳ Опыт: {EXPERIENCE.get(profile.get('experience'), profile.get('experience'))}\n"
            f"🕒 Часы: {HOURS.get(profile.get('hours'), profile.get('hours'))}\n"
            f"📍 Город: {LOCATIONS.get(city, city) if city else '—'}"
        )

    preferred_roles = _as_list(profile.get("preferred_roles", []))
    work_formats = _as_list(profile.get("work_formats", []))
    locations = _as_list(profile.get("locations", []))
    languages = _as_list(profile.get("languages", []))
    return (
        "👤 Мой профиль\n\n"
        f"🎯 Направления: {labels(preferred_roles, ROLES)}\n"
        f"💻 Навыки: {labels(preferred_roles, ROLES)}\n"
        f"📊 Уровень: {LEVELS.get(profile.get('experience_level'), profile.get('experience_level'))}\n"
        f"💼 Опыт: {EXPERIENCE.get(profile.get('experience'), profile.get('experience'))}\n"
        f"🌍 Языки: {labels(languages, LANGUAGES)}\n"
        f"🏠 Формат: {labels(work_formats, WORK_FORMATS)}\n"
        f"📍 Локация: {labels(locations, LOCATIONS)}"
    )


def save_profile(user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    profile = dict(data)
    profile["language"] = profile.get("language", profile.get("lang", "ru"))
    if profile.get("field") or profile.get("specialization") or profile.get("skills"):
        profile["is_active"] = True
        if not profile.get("preferred_roles") and profile.get("specialization"):
            profile["preferred_roles"] = [profile["specialization"]]
        if not profile.get("work_formats") and profile.get("work_format"):
            profile["work_formats"] = [profile["work_format"]]
        if not profile.get("locations") and profile.get("city"):
            profile["locations"] = [profile["city"]]
        if not profile.get("experience_level") and profile.get("level"):
            profile["experience_level"] = profile["level"]
        if not profile.get("languages") and profile.get("language"):
            profile["languages"] = [profile["language"]]
    return upsert_user_profile(user_id, profile)


def load_profile(user_id: int) -> dict[str, Any] | None:
    profile = get_user_profile(user_id)
    if profile and profile.get("is_active") is False:
        return None
    return profile