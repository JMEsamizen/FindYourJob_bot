import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
JOB_BOT_DIR = os.path.join(PROJECT_ROOT, "job_bot")
for _path in (PROJECT_ROOT, JOB_BOT_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "")

from job_bot import profile  # noqa: E402
from job_bot.stats import build_market_stats_message, summarize_market  # noqa: E402


def days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


class ProfileModelCompatibilityTest(unittest.TestCase):
    def test_new_profile_model_is_complete_when_required_fields_are_present(self):
        data = {
            "field": "programming",
            "specialization": "backend",
            "skills": ["python", "django"],
            "level": "junior",
            "work_format": "remote",
            "experience": "1_3",
            "hours": "5_6",
            "city": "tashkent",
        }
        self.assertTrue(profile.profile_complete(data))

    def test_new_profile_model_does_not_require_city(self):
        data = {
            "field": "programming",
            "specialization": "backend",
            "skills": ["python", "django"],
            "level": "junior",
            "work_format": "remote",
            "experience": "1_3",
            "hours": "5_6",
        }
        self.assertTrue(profile.profile_complete(data))

    def test_old_profile_model_still_works_for_compatibility(self):
        data = {
            "experience_level": "junior",
            "preferred_roles": ["backend"],
            "work_formats": ["remote"],
            "locations": ["tashkent"],
            "experience": "1_3",
            "languages": ["ru"],
        }
        self.assertTrue(profile.profile_complete(data))


class MarketStatsTest(unittest.TestCase):
    def test_summary_counts_real_vacancy_data(self):
        vacancies = [
            {"title": "Python Backend Developer", "text": "python django backend fastapi", "created_at": days_ago(1)},
            {"title": "React Frontend Developer", "text": "react frontend javascript", "created_at": days_ago(2)},
            {"title": "Python Backend Developer", "text": "python backend api", "created_at": days_ago(3)},
            {"title": "SMM Manager", "text": "instagram tiktok smm marketing", "created_at": days_ago(14)},
            {"title": "QA Engineer", "text": "manual qa automation testing", "created_at": days_ago(30)},
        ]
        snapshot = summarize_market(vacancies)
        self.assertEqual(snapshot["total_vacancies"], 3)
        self.assertEqual(snapshot["top_fields"][0][0], "backend")
        self.assertEqual(snapshot["top_skills"][0][0], "python")
        self.assertIn("changes", snapshot)

    def test_empty_market_returns_no_learn_skill(self):
        result = build_market_stats_message([], lang="ru")
        self.assertIsNone(result["learn_skill"])
        self.assertIn("не найдено", result["text"])


class WeeklyStatsMessageTest(unittest.TestCase):
    VACANCIES = [
        {"title": "Python Backend Developer", "text": "python django backend fastapi sql", "created_at": days_ago(1)},
        {"title": "Python Backend Developer", "text": "python django backend", "created_at": days_ago(2)},
        {"title": "React Frontend Developer", "text": "react frontend javascript", "created_at": days_ago(3)},
        {"title": "QA Automation", "text": "python automation selenium qa", "created_at": days_ago(4)},
    ]

    def test_message_reports_total_most_demanded_and_top(self):
        result = build_market_stats_message(self.VACANCIES, lang="ru")
        text = result["text"]
        self.assertIn("Всего вакансий: 4", text)
        self.assertEqual(result["learn_skill"], "python")
        self.assertIn("Backend", text)
        self.assertIn("Топ сфер", text)
        self.assertIn("Топ навыков", text)

    def test_message_is_localized_in_three_languages(self):
        for lang in ("ru", "uz", "en"):
            result = build_market_stats_message(self.VACANCIES, lang=lang, profile={"field": "programming", "specialization": "backend", "skills": ["python"]})
            self.assertTrue(result["text"])
            self.assertTrue(result["learn_skill"])

    def test_personalization_uses_profile_ranking(self):
        profile_data = {"field": "programming", "specialization": "backend", "skills": ["python", "django"]}
        result = build_market_stats_message(self.VACANCIES, lang="ru", profile=profile_data)
        self.assertIn("Backend", result["text"])  # specialization is among top fields
        self.assertIn("Python", result["text"])
        self.assertIn("Персонально для тебя", result["text"])

    def test_personalization_absent_without_profile(self):
        result = build_market_stats_message(self.VACANCIES, lang="ru", profile=None)
        self.assertNotIn("Персонально для тебя", result["text"])


if __name__ == "__main__":
    unittest.main()
