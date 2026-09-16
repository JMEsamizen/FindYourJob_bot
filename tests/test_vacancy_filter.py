import os
import sys
import unittest

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
JOB_BOT_DIR = os.path.join(PROJECT_ROOT, "job_bot")
for _path in (PROJECT_ROOT, JOB_BOT_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "")

from job_bot import vacancy_filter as vf  # noqa: E402
from job_bot.parser import Vacancy  # noqa: E402


def make_vacancy(
    text: str, title: str = "Vacancy", channel: str = "c",
    url: str = "https://t.me/c/1", date: str = "d",
) -> Vacancy:
    return Vacancy(title=title, text=text, date=date, url=url, channel=channel)


class WordBoundaryTest(unittest.TestCase):
    def test_short_terms_do_not_match_inside_words(self) -> None:
        self.assertEqual(vf._matches("html css email", ["ml", "ai"]), 0)

    def test_email_does_not_match_ai(self) -> None:
        self.assertEqual(vf._matches("please send to email", ["ai"]), 0)

    def test_html_does_not_match_ml(self) -> None:
        self.assertEqual(vf._matches("i write html", ["ml"]), 0)

    def test_standalone_ai_ml_still_match(self) -> None:
        self.assertEqual(vf._matches("ML and AI engineer", ["ai", "ml"]), 2)
        self.assertEqual(vf._matches("expert in AI", ["ai"]), 1)

    def test_technical_terms_with_special_chars_match(self) -> None:
        self.assertEqual(vf._matches("c++ developer", ["c++"]), 1)
        self.assertEqual(vf._matches("works with c#", ["c#"]), 1)
        self.assertEqual(vf._matches("node.js in stack", ["node.js"]), 1)

    def test_multiword_terms_match(self) -> None:
        self.assertEqual(vf._matches("we need machine learning", ["machine learning"]), 1)

    def test_qa_does_not_match_in_plain_words(self) -> None:
        self.assertEqual(vf._matches("quality assurance", ["qa"]), 0)


class HashtagBonusTest(unittest.TestCase):
    def test_hashtag_matches_profile_keyword(self) -> None:
        self.assertEqual(vf._count_hashtags("#backend developer", ["backend"]), 1)
        self.assertEqual(vf._count_hashtags("#SMM #reels", ["smm", "reels"]), 2)


class CategoryPrimaryFilterTest(unittest.TestCase):
    def test_smm_plus_python_skill_does_not_return_python_dev(self) -> None:
        python_dev = make_vacancy(
            "Python Backend Developer, Django, FastAPI, REST API, PostgreSQL",
            title="Python Developer", url="https://t.me/c/py",
        )
        smm_job = make_vacancy(
            "SMM manager, Telegram, instagram, реклама, таргетолог",
            title="SMM", url="https://t.me/c/smm",
        )
        result = vf.filter_vacancies([python_dev, smm_job], category="smm", skills=["python"])
        self.assertEqual([v.url for v in result], [smm_job.url])

    def test_content_manager_is_not_backend(self) -> None:
        content = make_vacancy(
            "Требуется контент-менеджер: наполнение сайта, CMS, техническое сопровождение, публикации",
            title="КОНТЕНТ-МЕНЕДЖЕР", url="https://t.me/c/content",
        )
        backend = make_vacancy(
            "Backend Python Developer, Django, FastAPI, PostgreSQL",
            title="Backend Developer", url="https://t.me/c/backend",
        )
        result = vf.filter_vacancies([content, backend], category="backend", skills=[])
        self.assertNotIn(content.url, [v.url for v in result])
        self.assertIn(backend.url, [v.url for v in result])

    def test_python_dev_passes_backend_by_tech_signal(self) -> None:
        py = make_vacancy("Python developer, SQL, REST")
        result = vf.filter_vacancies([py], category="backend", skills=[])
        self.assertEqual([v.url for v in result], [py.url])
class CategoryStillWorksTest(unittest.TestCase):
    def test_backend_still_found(self) -> None:
        job = make_vacancy("Backend Java/C#/Go, REST API, PostgreSQL")
        result = vf.filter_vacancies([job], category="backend", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_frontend_still_found(self) -> None:
        fe = make_vacancy("Frontend developer, React, TypeScript, HTML, CSS")
        result = vf.filter_vacancies([fe], category="frontend", skills=[])
        self.assertEqual([v.url for v in result], [fe.url])

    def test_design_still_found(self) -> None:
        de = make_vacancy("Designer, Figma, Photoshop, UI/UX, illustrator")
        result = vf.filter_vacancies([de], category="design", skills=[])
        self.assertEqual([v.url for v in result], [de.url])

    def test_smm_skill_does_not_pull_plain_python_dev(self) -> None:
        smm = make_vacancy("SMM, Telegram, контент-план, таргетолог", title="SMM")
        py_dev = make_vacancy("Python, Django, FastAPI", title="Python")
        result = vf.filter_vacancies([smm, py_dev], category="smm", skills=["python"])
        self.assertEqual([v.url for v in result], [smm.url])


class SkillRefinementTest(unittest.TestCase):
    def test_python_skill_boosts_backend_relevance(self) -> None:
        generic = make_vacancy(
            "Backend developer, server architecture", title="Backend", url="https://t.me/c/generic",
        )
        python_job = make_vacancy(
            "Backend developer with Python, Django, PostgreSQL",
            title="Python Backend", url="https://t.me/c/python",
        )
        result = vf.filter_vacancies([generic, python_job], category="backend", skills=["python"])
        self.assertEqual([v.url for v in result][0], python_job.url)

    def test_django_skill_refines_backend(self) -> None:
        django = make_vacancy(
            "Backend разработчик: Django, PostgreSQL, настройка серверов",
            title="Django", url="https://t.me/c/django",
        )
        generic = make_vacancy("Backend engineer general", title="Backend", url="https://t.me/c/generic")
        result = vf.filter_vacancies([generic, django], category="backend", skills=["django"])
        self.assertEqual([v.url for v in result][0], django.url)


if __name__ == "__main__":
    unittest.main()
class SynonymMatchTest(unittest.TestCase):
    def test_manual_tester_passes_qa(self) -> None:
        job = make_vacancy("Manual Tester, test cases, regression", title="Manual Tester")
        result = vf.filter_vacancies([job], category="qa", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_automation_tester_passes_qa(self) -> None:
        job = make_vacancy("Automation Tester, Selenium, pytest", title="Automation Tester")
        result = vf.filter_vacancies([job], category="qa", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_test_engineer_passes_qa(self) -> None:
        job = make_vacancy("Test Engineer, quality, test automation", title="Test Engineer")
        result = vf.filter_vacancies([job], category="qa", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_qa_engineer_passes_qa(self) -> None:
        job = make_vacancy("QA Engineer, manual and automation testing", title="QA Engineer")
        result = vf.filter_vacancies([job], category="qa", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_machine_learning_engineer_passes_ai_ml(self) -> None:
        job = make_vacancy("Machine Learning Engineer, model training", title="ML Engineer")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_ml_engineer_passes_ai_ml(self) -> None:
        job = make_vacancy("ML Engineer, нейронные сети, обучение", title="ML Engineer")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_neuro_networks_passes_ai_ml(self) -> None:
        job = make_vacancy("Разработка нейросетей, машинное обучение", title="AI инженер")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_machine_learning_phrase_passes_ai_ml(self) -> None:
        job = make_vacancy("машинное обучение, обучение моделей, python", title="ML")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_bi_analyst_passes_data(self) -> None:
        job = make_vacancy("BI Analyst, dashboards, power bi, sql", title="BI Analyst")
        result = vf.filter_vacancies([job], category="data", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_data_analyst_passes_data(self) -> None:
        job = make_vacancy("Data Analyst, аналитика, excel, sql", title="Data Analyst")
        result = vf.filter_vacancies([job], category="data", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_analitik_dannyh_passes_data(self) -> None:
        job = make_vacancy("Аналитик данных, sql, дашборды", title="Аналитик данных")
        result = vf.filter_vacancies([job], category="data", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_html_does_not_pass_ai_ml_via_ml(self) -> None:
        job = make_vacancy("HTML верстка, css, сайты", title="Верстальщик")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [])

    def test_email_does_not_pass_ai_ml_via_ai(self) -> None:
        job = make_vacancy("работа с email рассылками, контент", title="Маркетолог")
        result = vf.filter_vacancies([job], category="ai_ml", skills=[])
        self.assertEqual([v.url for v in result], [])

    def test_qa_short_word_alone_still_passes(self) -> None:
        # Одиночное "QA" не является категорийным сигналом; для QA нужен
        # составной термин (qa engineer / manual qa / automation tester).
        job = make_vacancy("QA Engineer, manage qa processes", title="QA Lead")
        result = vf.filter_vacancies([job], category="qa", skills=[])
        self.assertEqual([v.url for v in result], [job.url])


class HashtagRulesTest(unittest.TestCase):
    def test_backend_with_hashtag_passes(self) -> None:
        job = make_vacancy("#backend #python Backend Developer", title="Backend")
        result = vf.filter_vacancies([job], category="backend", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_backend_without_hashtag_passes(self) -> None:
        job = make_vacancy("Backend Developer", title="Backend")
        result = vf.filter_vacancies([job], category="backend", skills=[])
        self.assertEqual([v.url for v in result], [job.url])

    def test_python_hashtag_boosts_backend_but_not_smm(self) -> None:
        backend_job = make_vacancy("#python Backend Developer", title="Backend", url="https://t.me/c/b")
        smm_job = make_vacancy("#python SMM manager, telegram", title="SMM", url="https://t.me/c/s")
        result = vf.filter_vacancies([backend_job, smm_job], category="smm", skills=["python"])
        # SMM + skill python must NOT return the Backend vacancy.
        self.assertEqual([v.url for v in result], [smm_job.url])


if __name__ == "__main__":
    unittest.main()