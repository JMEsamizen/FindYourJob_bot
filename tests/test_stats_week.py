import asyncio
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

from job_bot import bot  # noqa: E402
from job_bot.keyboards import (  # noqa: E402
    categories_keyboard, login_keyboard, stats_keyboard, stats_materials_keyboard,
)
from job_bot.learning import LearningMaterial  # noqa: E402


def make_youtube(skill: str, w3_url: str | None) -> LearningMaterial:
    return LearningMaterial(
        skill=skill,
        title=f"{skill} Course",
        description="",
        url=f"https://www.youtube.com/watch?v={skill}",
        w3_url=w3_url,
    )


class LoginKeyboardTest(unittest.TestCase):
    def test_login_keyboard_offers_login_and_register(self):
        for lang in ("ru", "uz", "en"):
            kb = login_keyboard(lang)
            callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
            self.assertIn("profile_login", callbacks)
            self.assertIn("profile_create", callbacks)
            self.assertIn("market_stats", callbacks)

    def test_categories_keyboard_has_stats_and_profile_buttons(self):
        for lang in ("ru", "uz", "en"):
            kb = categories_keyboard(lang)
            callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
            self.assertIn("market_stats", callbacks)
            self.assertIn("profile_menu", callbacks)


class StatsKeyboardsTest(unittest.TestCase):
    def test_stats_keyboard_learn_button_only_when_learn_available(self):
        # Without a configured database materials_for() resolves to [].
        kb = stats_keyboard("ru", learn_skill="python")
        callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
        self.assertNotIn("stats_learn:python", callbacks)
        kb_plain = stats_keyboard("ru", learn_skill=None)
        callbacks_plain = {b.callback_data for row in kb_plain.inline_keyboard for b in row}
        self.assertIn("profile_menu", callbacks_plain)

    def test_stats_materials_keyboard_shows_youtube_and_w3schools(self):
        material = make_youtube("python", "https://www.w3schools.com/python/")
        kb = stats_materials_keyboard(material, "ru")
        urls = [b.url for row in kb.inline_keyboard for b in row if b.url]
        self.assertIn("https://www.youtube.com/watch?v=python", urls)
        self.assertIn("https://www.w3schools.com/python/", urls)

    def test_stats_materials_keyboard_hides_w3_when_missing(self):
        material = make_youtube("sql", None)
        kb = stats_materials_keyboard(material, "ru")
        urls = [b.url for row in kb.inline_keyboard for b in row if b.url]
        self.assertNotIn("https://www.w3schools.com/", urls)
        self.assertIn("https://www.youtube.com/watch?v=sql", urls)


class StatsLearnHandlerTest(unittest.TestCase):
    def test_stats_learn_shows_materials_message(self):
        callback = Mock()
        callback.from_user.id = 123
        callback.data = "stats_learn:python"
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.answer = AsyncMock()

        material = make_youtube("python", "https://www.w3schools.com/python/")
        with patch.object(bot, "material_for", return_value=material), patch.object(
            bot, "get_user_language", return_value="ru"
        ):
            asyncio.run(bot.stats_learn_handler(callback))

        callback.message.answer.assert_called_once()
        markup = callback.message.answer.call_args.kwargs["reply_markup"]
        urls = [b.url for row in markup.inline_keyboard for b in row if b.url]
        self.assertIn("https://www.youtube.com/watch?v=python", urls)
        self.assertIn("https://www.w3schools.com/python/", urls)


if __name__ == "__main__":
    unittest.main()