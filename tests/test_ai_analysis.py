import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
JOB_BOT_DIR = os.path.join(PROJECT_ROOT, "job_bot")
for _path in (PROJECT_ROOT, JOB_BOT_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("OPENROUTER_API_KEY", "")

import ai_analysis  # noqa: E402


class VacancyAnalysisTest(unittest.TestCase):
    def test_openrouter_compares_profile_with_vacancy_requirements(self) -> None:
        expected = {
            "match_percent": 75,
            "matched_skills": ["Python", "Backend", "SQL"],
            "missing_skills": ["Docker", "FastAPI"],
            "strengths": ["Python", "Backend", "SQL"],
            "weaknesses": ["Docker", "FastAPI"],
            "recommendation": "Подходит, но стоит изучить Docker и FastAPI.",
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(expected, ensure_ascii=False)}}]
        }
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.post = AsyncMock(return_value=response)
        profile = {
            "preferred_roles": ["Python", "Backend", "SQL"],
            "experience_level": "junior",
            "experience": "0_6",
            "languages": ["en"],
            "work_formats": ["remote"],
            "locations": ["any"],
        }
        vacancy = {
            "title": "Python Backend Developer",
            "text": "Requirements: Python, Backend, SQL, Docker, FastAPI.",
            "channel": "testjobs4224",
            "url": "https://t.me/testjobs4224/1",
        }

        with patch.object(ai_analysis, "OPENROUTER_API_KEY", "test-key"), patch.object(
            ai_analysis.httpx, "AsyncClient", return_value=client
        ):
            result = asyncio.run(ai_analysis.analyze_vacancy(profile, vacancy))

        request = client.post.call_args
        request_body = request.kwargs["json"]
        user_payload = json.loads(request_body["messages"][1]["content"])
        self.assertEqual(request_body["model"], ai_analysis.OPENROUTER_MODEL)
        self.assertEqual(user_payload["profile"]["preferred_roles"], profile["preferred_roles"])
        self.assertEqual(user_payload["vacancy"]["title"], vacancy["title"])
        self.assertEqual(user_payload["vacancy"]["text"], vacancy["text"])
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
