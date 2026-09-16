import re
from collections.abc import Iterable

from parser import Vacancy

# Characters treated as "part of a word" for boundary matching. Includes
# Latin, Cyrillic, digits and underscore so that short terms like "ml", "ai",
# "qa" never match inside longer words ("html", "email").
_WORD_CHARS = r"A-Za-zА-Яа-яЁё0-9_"
_HASHTAG_RE = re.compile(r"#([A-Za-zА-Яа-яЁё0-9_]+)")
_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _keyword_pattern(keyword: str) -> re.Pattern:
    """Compile (and cache) a whole-word pattern for a technical keyword."""
    pattern = _PATTERN_CACHE.get(keyword)
    if pattern is None:
        escaped = re.escape(keyword)
        pattern = re.compile(rf"(?<![{_WORD_CHARS}]){escaped}(?![{_WORD_CHARS}])")
        _PATTERN_CACHE[keyword] = pattern
    return pattern


def _count_hashtags(text: str, keywords: list[str] | tuple[str, ...]) -> int:
    """Count profile hashtags (#backend, #python, ...) that match the keywords."""
    count = 0
    for tag in _HASHTAG_RE.findall(text):
        tag_lower = tag.lower()
        if any(tag_lower == keyword.lower() or tag_lower.startswith(keyword.lower()) for keyword in keywords):
            count += 1
    return count

CATEGORY_KEYWORDS = {
    "backend": ["backend", "back-end", "python", "django", "fastapi", "flask", "node.js", "nodejs", "golang", "go developer", "php", "java backend", "c++", "c#"],
    "frontend": ["frontend", "front-end", "javascript", "typescript", "react", "vue", "angular", "next.js", "html", "css", "web developer"],
    "design": ["designer", "design", "ui/ux", "ui ux", "ux/ui", "figma", "photoshop", "illustrator", "graphic designer", "web designer", "product designer"],
    "qa": ["quality assurance", "manual qa", "manual tester", "manual testing", "tester", "testing", "test engineer", "automation qa", "automation tester", "qa engineer"],
    "devops": ["devops", "dev ops", "docker", "kubernetes", "linux", "aws", "azure", "gcp", "cloud engineer", "system administrator", "sysadmin"],
    "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "data scientist", "computer vision", "nlp", "нейросети", "нейросеть", "машинное обучение", "обучение моделей", "ml engineer", "ai engineer", "machine learning engineer"],
    "mobile": ["android", "ios", "flutter", "react native", "mobile developer", "kotlin", "swift"],
    "data": ["data analyst", "data scientist", "data engineer", "analytics", "sql", "power bi", "tableau", "bi analyst", "аналитик данных"],
    "marketing": ["marketing", "smm", "seo", "content manager", "targetolog", "маркетолог"],
    "smm": [
        "smm", "смм", "smm специалист", "smm-специалист", "смм специалист", "смм-специалист", "smm specialist", "smm manager", "social media",
        "social media manager", "social media specialist", "social media marketing",
        "контент менеджер", "контент-менеджер", "content manager", "content creator",
        "контент мейкер", "контент-мейкер", "content maker", "маркетолог",
        "marketing specialist", "digital marketing", "digital marketer", "instagram manager",
        "таргетолог", "таргет", "targetologist", "meta ads", "facebook ads", "instagram",
        "tiktok", "telegram", "reels", "stories", "контент-план", "контент план", "content plan",
        "smm mutaxassisi", "smm menejer", "marketing mutaxassisi", "ijtimoiy tarmoqlar",
        "kontent", "kontent reja", "target", "reklama",
    ],
    "other": (),
}

SKILL_KEYWORDS = {
    "python": ["python"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "react.js", "reactjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular"],
    "next.js": ["next.js", "nextjs"],
    "nextjs": ["next.js", "nextjs"],
    "c++": ["c++", "cpp"],
    "cpp": ["c++", "cpp"],
    "c#": ["c#", "csharp"],
    "csharp": ["c#", "csharp"],
    "nodejs": ["node.js", "nodejs"],
    "manual qa": ["manual qa", "manualqa", "manual testing"],
    "manual testing": ["manual testing", "manual qa", "manualqa"],
    "figma": ["figma"],
    "ui/ux": ["ui/ux", "ui ux", "ux/ui", "ux designer"],
    "ui_ux": ["ui/ux", "ui ux", "ux/ui", "ux designer"],
    "graphic_design": ["graphic design", "graphic designer"],
    "motion_design": ["motion design", "motion designer"],
    "machine_learning": ["machine learning", "ml"],
    "deep_learning": ["deep learning"],
    "computer_vision": ["computer vision"],
    "react_native": ["react native"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "linux": ["linux"],
    "flutter": ["flutter"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "sql": ["sql"],
    "power bi": ["power bi", "powerbi"],
    "power_bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "cicd": ["ci/cd", "cicd"],
    "project_manager": ["project manager", "project management"],
    "product_manager": ["product manager", "product management"],
    "content_creation": [
        "content creator", "content creation", "контент мейкер", "контент-мейкер",
        "создание контента", "создавать контент", "контент", "kontent",
    ],
    "reels": ["reels", "рилс", "reel"],
    "analytics": ["analytics", "аналитика", "анализ статистики", "reach", "engagement", "er", "ctr"],
    "target_ads": ["target", "targetologist", "таргет", "таргетолог", "meta ads", "facebook ads", "advertising", "реклама"],
    "instagram": ["instagram", "инстаграм"],
    "tiktok": ["tiktok", "тик ток", "тикток"],
    "copywriting": ["copywriter", "copywriting", "копирайтинг", "тексты", "написание текстов", "сценарий"],
    "canva": ["canva"],
    "capcut": ["capcut", "капкат"],
    "premiere_pro": ["premiere pro", "adobe premiere"],
    "smm": ["smm"],
    "seo": ["seo"],
}


def _matches(text: str, keywords: list[str] | tuple[str, ...]) -> int:
    """Count keywords found as whole words / valid technical terms.

    Uses word boundaries, so "ml" does not match "html" and "ai" does not
    match "email", while technical tokens like "#c#", "#c++", "node.js" etc.
    still match as standalone terms. Matching is case-insensitive.
    """
    text = text.lower()
    return sum(bool(_keyword_pattern(keyword.lower()).search(text)) for keyword in keywords)


def filter_vacancies(
    vacancies: Iterable[Vacancy], category: str, skills: list[str], limit: int | None = 15
) -> list[Vacancy]:
    matched = []
    category_terms = CATEGORY_KEYWORDS.get(category, [])
    for vacancy in vacancies:
        text = vacancy.text.lower()
        category_matches = _matches(text, category_terms)
        skill_matches = sum(
            _matches(text, SKILL_KEYWORDS.get(skill.lower(), [skill.lower()]))
            for skill in skills
        )

        # Category is the primary filter. A vacancy must belong to the chosen
        # category; skills only refine ranking inside it and can never bypass
        # the category (e.g. SMM + skill Python must not return a Python job).
        if category_terms and category_matches == 0:
            continue
        if not category_terms and skill_matches == 0:
            # "other" has no category terms, so skills are the only signal.
            continue

        hashtag_bonus = _count_hashtags(text, category_terms)
        hashtag_bonus += sum(
            _count_hashtags(text, SKILL_KEYWORDS.get(skill.lower(), [skill.lower()]))
            for skill in skills
        )

        # Category match dominates, skills refine, hashtags are a bonus.
        score = category_matches * 5 + skill_matches + hashtag_bonus
        matched.append((score, vacancy.date, vacancy))
    matched.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in matched[:limit]]


def matched_keywords(vacancy: Vacancy, keywords: list[str]) -> list[str]:
    text = vacancy.text.lower()
    return [keyword for keyword in keywords if keyword.lower() in text]


def filter_posts_by_keywords(vacancies: Iterable[Vacancy], keywords: list[str], limit: int = 15) -> list[Vacancy]:
    matched = []
    for vacancy in vacancies:
        matches = matched_keywords(vacancy, keywords)
        if matches:
            matched.append((len(matches), vacancy.date, vacancy))
    matched.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in matched[:limit]]
