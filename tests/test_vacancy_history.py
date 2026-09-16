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
from job_bot import db  # noqa: E402
from job_bot.i18n import t  # noqa: E402
from job_bot.keyboards import profile_menu_keyboard, results_keyboard  # noqa: E402
from job_bot.parser import Vacancy  # noqa: E402


class FindMoreVisibilityTest(unittest.TestCase):
    def test_hidden_when_not_end_of_full_batch(self) -> None:
        self.assertFalse(bot.find_more_visible(0, 40))
        self.assertFalse(bot.find_more_visible(13, 40))

    def test_hidden_when_no_vacancies_remaining_after_full_batch(self) -> None:
        # The 15th post is shown and there is nothing new left.
        self.assertFalse(bot.find_more_visible(14, 15))
        self.assertFalse(bot.find_more_visible(29, 30))
        self.assertFalse(bot.find_more_visible(44, 45))

    def test_shown_after_full_batch_when_some_vacancies_remain(self) -> None:
        # Even 1 remaining post is enough to offer "Найти ещё".
        self.assertTrue(bot.find_more_visible(14, 16))
        self.assertTrue(bot.find_more_visible(14, 20))
        self.assertTrue(bot.find_more_visible(14, 29))
        self.assertTrue(bot.find_more_visible(14, 30))
        self.assertTrue(bot.find_more_visible(29, 31))
        self.assertTrue(bot.find_more_visible(29, 45))


class BatchIdTest(unittest.TestCase):
    def test_batch_ids_cover_page_window(self) -> None:
        vacancies = [{"db_id": index + 1} for index in range(40)]
        self.assertEqual(bot._batch_vacancy_ids(0, vacancies), list(range(1, 16)))
        self.assertEqual(bot._batch_vacancy_ids(14, vacancies), list(range(1, 16)))
        self.assertEqual(bot._batch_vacancy_ids(15, vacancies), list(range(16, 31)))
        self.assertEqual(bot._batch_vacancy_ids(35, vacancies), list(range(31, 41)))

    def test_batch_ids_ignore_missing_db_id(self) -> None:
        vacancies = [{"db_id": 1}, {"url": "x"}, {"db_id": 3}]
        self.assertEqual(bot._batch_vacancy_ids(0, vacancies), [1, 3])


class ConsumeAnalysisUseTest(unittest.TestCase):
    """Verifies the SQL-driven per-user limit semantics through the connection API."""

    class FakeCursor:
        def __init__(self, state: dict, limit: int) -> None:
            self._state = state
            self._limit = limit
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, query: str, params: tuple) -> None:
            user_id = params[0]
            count = self._state.get(user_id, 0)
            if count < self._limit:
                count += 1
                self._state[user_id] = count
                self._row = (count,)
            else:
                self._row = None

        def fetchone(self):
            return self._row

    class FakeConnection:
        def __init__(self, state: dict, limit: int) -> None:
            self._state = state
            self._limit = limit

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return ConsumeAnalysisUseTest.FakeCursor(self._state, self._limit)

    @patch("job_bot.db.is_database_configured", return_value=True)
    @patch("job_bot.db._connect")
    def test_two_uses_allowed_third_blocked_without_consuming(
        self, connect, _configured
    ) -> None:
        state: dict = {}
        connect.return_value = self.FakeConnection(state, 2)

        first = db.consume_analysis_use(11)
        second = db.consume_analysis_use(11)
        third = db.consume_analysis_use(11)

        self.assertEqual(first, (True, 1))
        self.assertEqual(second, (True, 2))
        # Third attempt is rejected and does not consume an extra use.
        self.assertEqual(third, (False, 2))
        self.assertEqual(state[11], 2)


class AnalysisLimitGateTest(unittest.TestCase):
    @patch("job_bot.db.consume_analysis_use", return_value=(True, 1))
    def test_regular_user_consumes_one_use(self, consume) -> None:
        self.assertTrue(db.analysis_limit_allows(123))
        consume.assert_called_once_with(123, db.ANALYSIS_LIMIT)

    @patch("job_bot.db.consume_analysis_use", return_value=(False, 2))
    def test_regular_user_blocked_after_limit(self, consume) -> None:
        self.assertFalse(db.analysis_limit_allows(123))

    @patch("job_bot.db.consume_analysis_use")
    def test_exempt_user_is_not_limited(self, consume) -> None:
        self.assertTrue(db.analysis_limit_allows(1480030770))
        consume.assert_not_called()
class SearchHistoryTest(unittest.TestCase):
    def _vacancies(self, count: int = 3) -> list[Vacancy]:
        return [
            Vacancy(title=f"title {i}", text=f"text {i}", date="d", url=f"u{i}", channel="c")
            for i in range(1, count + 1)
        ]

    def _run_search(self, vacancies: list[Vacancy], viewed: set[int]):
        id_map = {item.url: index + 1 for index, item in enumerate(vacancies)}
        callback = Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "ru", "category": "smm", "skills": []})
        with (
            patch.object(bot, "fetch_all_vacancies", AsyncMock(return_value=vacancies)),
            patch.object(bot, "filter_vacancies", side_effect=lambda *a, **k: vacancies),
            patch.object(bot, "save_vacancies", return_value=id_map),
            patch.object(bot, "get_viewed_vacancy_ids", return_value=viewed),
            patch.object(bot, "mark_vacancies_viewed") as mark,
        ):
            asyncio.run(bot.search_handler(callback, state))
        return callback, state, mark

    def test_search_saves_first_batch_and_marks_it_viewed(self) -> None:
        vacancies = self._vacancies(3)
        callback, state, mark = self._run_search(vacancies, viewed=set())

        state.update_data.assert_called_once()
        stored = state.update_data.call_args.kwargs["vacancies"]
        self.assertEqual([item["url"] for item in stored], ["u1", "u2", "u3"])
        self.assertEqual([item["db_id"] for item in stored], [1, 2, 3])
        mark.assert_called_once_with(123, [1, 2, 3])
        self.assertEqual([item["db_id"] for item in stored], [1, 2, 3])
        mark.assert_called_once_with(123, [1, 2, 3])
        self.assertIn("text 1", callback.message.edit_text.call_args.args[0])

    def test_search_caps_batch_to_15_posts(self) -> None:
        # Even if many vacancies match, only a 15-post batch is stored/shown.
        vacancies = self._vacancies(40)
        callback, state, mark = self._run_search(vacancies, viewed=set())

        stored = state.update_data.call_args.kwargs["vacancies"]
        self.assertEqual(len(stored), 15)
        self.assertEqual(state.update_data.call_args.kwargs["total_new"], 40)
        self.assertEqual([item["db_id"] for item in stored], list(range(1, 16)))
        mark.assert_called_once_with(123, list(range(1, 16)))

    def test_repeat_search_excludes_already_viewed(self) -> None:
        vacancies = self._vacancies(3)
        callback, state, mark = self._run_search(vacancies, viewed={1, 2})

        stored = state.update_data.call_args.kwargs["vacancies"]
        self.assertEqual([item["url"] for item in stored], ["u3"])
        self.assertEqual([item["db_id"] for item in stored], [3])
        mark.assert_called_once_with(123, [3])
        self.assertIn("text 3", callback.message.edit_text.call_args.args[0])

    def test_search_with_nothing_new_shows_no_results(self) -> None:
        vacancies = self._vacancies(2)
        callback, state, mark = self._run_search(vacancies, viewed={1, 2})
        self.assertEqual(callback.message.edit_text.call_args.args[0], t("no_results", "ru"))


class FindMoreFlowTest(unittest.TestCase):
    def _run_find_more(self, candidate_count: int, viewed_ids: list[int]):
        candidates = [
            Vacancy(title=f"title {i}", text=f"text {i}", date="d", url=f"u{i}", channel="c")
            for i in range(1, candidate_count + 1)
        ]
        id_map = {f"u{i}": i for i in range(1, candidate_count + 1)}
        callback = Mock()
        callback.from_user.id = 1
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "ru", "category": "smm", "skills": []})
        with (
            patch.object(bot, "fetch_all_vacancies", AsyncMock(return_value=candidates)),
            patch.object(bot, "filter_vacancies", side_effect=lambda *a, **k: candidates),
            patch.object(bot, "save_vacancies", return_value=id_map),
            patch.object(bot, "get_viewed_vacancy_ids", return_value=set(viewed_ids)),
            patch.object(bot, "mark_vacancies_viewed") as mark,
        ):
            asyncio.run(bot.find_more_handler(callback, state))
        return callback, state, mark

    def test_find_more_advances_to_next_batch_and_records_it(self) -> None:
        # 30 new candidates exist; the first 15 were already shown. Find more
        # must re-fetch, drop the previous batch, and show posts 16-30.
        callback, state, mark = self._run_find_more(30, viewed_ids=list(range(1, 16)))

        stored = state.update_data.call_args.kwargs["vacancies"]
        self.assertEqual(len(stored), 15)
        self.assertEqual([item["url"] for item in stored], [f"u{i}" for i in range(16, 31)])
        self.assertEqual([item["db_id"] for item in stored], list(range(16, 31)))
        mark.assert_called_once_with(1, list(range(16, 31)))
        self.assertIn("text 16", callback.message.edit_text.call_args.args[0])

    def test_find_more_with_only_partial_new_batch(self) -> None:
        # Only 5 unseen candidates remain (since 15 of 20 were already viewed).
        # Find more opens them as a short batch; the button is hidden for the next step.
        callback, state, mark = self._run_find_more(20, viewed_ids=list(range(1, 16)))

        stored = state.update_data.call_args.kwargs["vacancies"]
        self.assertEqual([item["url"] for item in stored], [f"u{i}" for i in range(16, 21)])
        mark.assert_called_once_with(1, list(range(16, 21)))
        self.assertIn("text 16", callback.message.edit_text.call_args.args[0])


class UserViewedHistoryReadTest(unittest.TestCase):
    """get_user_viewed_vacancies returns full vacancy dicts in newest-first order."""

    @patch("job_bot.db.is_database_configured", return_value=True)
    @patch("job_bot.db._connect")
    def test_builds_vacancy_dicts_preserving_newest_first(self, connect, _configured) -> None:
        conn = unittest.mock.MagicMock()
        cur = unittest.mock.MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur
        cur.fetchall.return_value = [
            ("uA", "tA", "txtA", "dA", "chA", "ts-1"),
            ("uB", "tB", "txtB", "dB", "chB", "ts-2"),
        ]
        connect.return_value = conn

        result = db.get_user_viewed_vacancies(123)

        self.assertEqual([item["url"] for item in result], ["uA", "uB"])
        required = {"url", "title", "text", "date", "channel", "viewed_at"}
        for item in result:
            self.assertTrue(required <= set(item))
        self.assertEqual(result[0]["title"], "tA")
        self.assertEqual(result[1]["channel"], "chB")


class HistoryViewFlowTest(unittest.TestCase):
    def _context(self):
        callback = unittest.mock.Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = unittest.mock.Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "uz"})
        return callback, state

    def test_empty_history_shows_localized_empty_message(self) -> None:
        callback, state = self._context()
        with (
            patch.object(bot, "get_user_viewed_vacancies", return_value=[]),
            patch.object(bot, "empty_results_keyboard"),
        ):
            asyncio.run(bot.history_view_handler(callback, state))
        self.assertEqual(callback.message.edit_text.call_args.args[0], t("history_empty", "uz"))

    def test_nonempty_history_enters_viewing_state_and_shows_first(self) -> None:
        callback, state = self._context()
        items = [{"url": "u1", "title": "t1", "text": "text 1", "date": "d", "channel": "c"}]
        with (
            patch.object(bot, "get_user_viewed_vacancies", return_value=items),
            patch.object(bot, "render_history_result") as render,
        ):
            asyncio.run(bot.history_view_handler(callback, state))
        state.set_state.assert_called_once_with(bot.SearchStates.viewing_history)
        self.assertEqual(state.update_data.call_args.kwargs["history_vacancies"], items)
        render.assert_called_once_with(callback, state, 0)


class HistoryPaginationFlowTest(unittest.TestCase):
    def _render_context(self, total: int, page: int):
        vacancies = [
            {"url": f"u{i}", "title": f"t{i}", "text": f"text {i}", "date": "d", "channel": "c"}
            for i in range(1, total + 1)
        ]
        callback = unittest.mock.Mock()
        callback.answer = AsyncMock()
        callback.message = unittest.mock.Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "ru", "history_vacancies": vacancies, "current_page": page})
        return callback, state

    def test_next_advances_to_following_item(self) -> None:
        callback, state = self._render_context(5, 0)
        callback.data = "hp:next"
        with patch.object(bot, "render_history_result") as render:
            asyncio.run(bot.history_pagination_handler(callback, state))
        render.assert_called_once_with(callback, state, 1)

    def test_prev_goes_back_to_previous_item(self) -> None:
        callback, state = self._render_context(5, 1)
        callback.data = "hp:prev"
        with patch.object(bot, "render_history_result") as render:
            asyncio.run(bot.history_pagination_handler(callback, state))
        render.assert_called_once_with(callback, state, 0)

    def test_next_on_last_page_is_noop(self) -> None:
        callback, state = self._render_context(5, 4)
        callback.data = "hp:next"
        with patch.object(bot, "render_history_result") as render:
            asyncio.run(bot.history_pagination_handler(callback, state))
        render.assert_not_called()


class HistoryRenderTest(unittest.TestCase):
    def _context(self, total: int, lang: str = "ru"):
        vacancies = [
            {"url": f"u{i}", "title": f"t{i}", "text": f"text {i}", "date": "d", "channel": "c"}
            for i in range(1, total + 1)
        ]
        callback = unittest.mock.Mock()
        callback.from_user.id = 1
        callback.answer = AsyncMock()
        callback.message = unittest.mock.Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": lang, "history_vacancies": vacancies, "current_page": 0})
        return callback, state

    def test_last_item_appends_localized_end_footer(self) -> None:
        callback, state = self._context(2)
        asyncio.run(bot.render_history_result(callback, state, 1))
        text = callback.message.edit_text.call_args.args[0]
        self.assertIn(t("history_end", "ru"), text)

    def test_middle_item_has_no_end_footer(self) -> None:
        callback, state = self._context(3)
        asyncio.run(bot.render_history_result(callback, state, 1))
        text = callback.message.edit_text.call_args.args[0]
        self.assertNotIn(t("history_end", "ru"), text)


class HistoryKeyboardTest(unittest.TestCase):
    def test_history_navigation_uses_hp_prefix(self) -> None:
        kb = results_keyboard(1, 5, "url", "ru", prefix="hp")
        callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
        self.assertIn("hp:prev", callbacks)
        self.assertIn("hp:current", callbacks)
        self.assertIn("hp:next", callbacks)

    def test_last_history_page_has_no_next_button(self) -> None:
        kb = results_keyboard(4, 5, "url", "ru", prefix="hp")
        callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
        self.assertIn("hp:prev", callbacks)
        self.assertIn("hp:current", callbacks)
        self.assertNotIn("hp:next", callbacks)

    def test_search_keyboard_keeps_default_page_prefix(self) -> None:
        kb = results_keyboard(1, 5, "url", "ru")
        callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
        self.assertIn("page:next", callbacks)
        self.assertNotIn("hp:next", callbacks)

    def test_profile_menu_history_button_is_localized(self) -> None:
        for lang in ("ru", "uz", "en"):
            texts = [b.text for row in profile_menu_keyboard(lang).inline_keyboard for b in row]
            self.assertIn(t("history_view", lang), texts)


class SearchHistoryRenderTest(unittest.TestCase):
    def test_search_last_batch_page_shows_find_more_and_no_next(self) -> None:
        # Within a 15-post batch, the 15th post must not expose a Next button;
        # the only way onward is the "Найти ещё" button (when 15+ more remain).
        callback = Mock()
        callback.from_user.id = 1
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        batch = [
            {"url": f"u{i}", "db_id": i, "title": f"t{i}", "text": f"text {i}", "date": "d", "channel": "c"}
            for i in range(1, 16)
        ]
        state.get_data = AsyncMock(return_value={"lang": "ru", "vacancies": batch, "total_new": 40, "current_page": 14})

        with patch.object(bot, "mark_vacancies_viewed"):
            asyncio.run(bot.render_search_result(callback, state, 14))

        buttons = callback.message.edit_text.call_args.kwargs["reply_markup"].inline_keyboard
        callbacks = {b.callback_data for row in buttons for b in row}
        self.assertIn("find_more", callbacks)
        self.assertNotIn("page:next", callbacks)

    def test_search_last_batch_page_shows_find_more_with_single_remaining(self) -> None:
        # Even if just 1 new post remains after the current 15, "Найти ещё" shows.
        callback = Mock()
        callback.from_user.id = 1
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        batch = [
            {"url": f"u{i}", "db_id": i, "title": f"t{i}", "text": f"text {i}", "date": "d", "channel": "c"}
            for i in range(1, 16)
        ]
        state.get_data = AsyncMock(return_value={"lang": "ru", "vacancies": batch, "total_new": 16, "current_page": 14})

        with patch.object(bot, "mark_vacancies_viewed"):
            asyncio.run(bot.render_search_result(callback, state, 14))

        callbacks = {
            b.callback_data for row in callback.message.edit_text.call_args.kwargs["reply_markup"].inline_keyboard for b in row
        }
        self.assertIn("find_more", callbacks)
        self.assertNotIn("page:next", callbacks)

    def test_search_last_batch_page_hides_find_more_when_nothing_remains(self) -> None:
        # If exactly 15 new posts exist, the 15th post offers no "Найти ещё".
        callback = Mock()
        callback.from_user.id = 1
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        batch = [
            {"url": f"u{i}", "db_id": i, "title": f"t{i}", "text": f"text {i}", "date": "d", "channel": "c"}
            for i in range(1, 16)
        ]
        state.get_data = AsyncMock(return_value={"lang": "ru", "vacancies": batch, "total_new": 15, "current_page": 14})

        with patch.object(bot, "mark_vacancies_viewed"):
            asyncio.run(bot.render_search_result(callback, state, 14))

        callbacks = {
            b.callback_data for row in callback.message.edit_text.call_args.kwargs["reply_markup"].inline_keyboard for b in row
        }
        self.assertNotIn("find_more", callbacks)


class ClearHistoryFlowTest(unittest.TestCase):
    def test_history_clear_handler_clears_and_returns_to_categories(self) -> None:
        callback = Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "en"})

        with patch.object(bot, "clear_viewed_vacancies", return_value=None) as clear:
            asyncio.run(bot.history_clear_handler(callback, state))

        clear.assert_called_once_with(123)
        self.assertEqual(callback.message.edit_text.call_args.args[0], t("history_cleared", "en"))
        state.set_state.assert_called_once_with(bot.SearchStates.choosing_category)

    @patch("job_bot.db.is_database_configured", return_value=True)
    @patch("job_bot.db._connect")
    def test_clear_runs_delete_for_the_user(self, connect, _configured) -> None:
        conn = unittest.mock.MagicMock()
        cur = unittest.mock.MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cur
        connect.return_value = conn

        db.clear_viewed_vacancies(123)

        executed = [call.args[0] for call in cur.execute.call_args_list]
        self.assertTrue(any("DELETE FROM user_viewed_vacancies" in q for q in executed))
        self.assertTrue(any("123" in str(call.args[1]) for call in cur.execute.call_args_list))


class ProfileLogoutFlowTest(unittest.TestCase):
    def test_profile_logout_keeps_data_and_shows_login_buttons(self) -> None:
        callback = Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "en"})

        with patch.object(bot, "set_user_profile_active", return_value=True) as deactivate:
            asyncio.run(bot.profile_logout_handler(callback, state))

        deactivate.assert_called_once_with(123, False)
        state.clear.assert_called_once()
        state.update_data.assert_called_once_with(lang="en")
        state.set_state.assert_called_once_with(bot.SearchStates.choosing_category)
        self.assertEqual(callback.message.edit_text.call_args.args[0], t("logout_confirmed", "en"))
        logout_markup = callback.message.edit_text.call_args.kwargs["reply_markup"]
        callbacks = {b.callback_data for row in logout_markup.inline_keyboard for b in row}
        self.assertIn("profile_login", callbacks)
        self.assertIn("profile_create", callbacks)

    def test_profile_login_restores_saved_profile(self) -> None:
        callback = Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "en"})

        saved_profile = {
            "field": "programming", "specialization": "backend",
            "skills": ["python"], "level": "junior", "work_format": "remote",
            "experience": "1_3", "hours": "5_6", "city": "tashkent", "language": "en",
        }
        with patch.object(bot, "get_user_profile", side_effect=[saved_profile, saved_profile]), patch.object(
            bot, "set_user_profile_active", return_value=True
        ) as activate:
            asyncio.run(bot.profile_login_handler(callback, state))
            activate.assert_called_once_with(123, True)

        edited = callback.message.edit_text.call_args.args[0]
        self.assertIn(t("login_success", "en"), edited)
        self.assertIn("Профиль", edited)  # display_profile was rendered
        menu = callback.message.edit_text.call_args.kwargs["reply_markup"]
        callbacks = {b.callback_data for row in menu.inline_keyboard for b in row}
        self.assertIn("profile_edit", callbacks)

    def test_profile_login_without_saved_profile(self) -> None:
        callback = Mock()
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = Mock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"lang": "en"})

        with patch.object(bot, "get_user_profile", return_value=None):
            asyncio.run(bot.profile_login_handler(callback, state))

        self.assertEqual(callback.message.edit_text.call_args.args[0], t("need_profile_first", "en"))

    def test_profile_menu_contains_logout_button(self) -> None:
        for lang in ("ru", "uz", "en"):
            kb = profile_menu_keyboard(lang)
            callbacks = {b.callback_data for row in kb.inline_keyboard for b in row}
            self.assertIn("profile_logout", callbacks)


if __name__ == "__main__":
    unittest.main()