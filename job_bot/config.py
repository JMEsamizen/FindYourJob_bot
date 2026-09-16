import os

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DEFAULT_CHANNELS = [
    "kasbim_uz",
    "job_react",
    "ayti_jobs",
    "smmprtashkent",
    "testjobs4224",
]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash").strip()

# Number of times a regular user may use "Анализ вакансии".
ANALYSIS_LIMIT = 2
# Accounts that are exempt from the analysis limit.
ANALYSIS_EXEMPT_USER_IDS = (1480030770,)
ANALYSIS_EXEMPT_USERNAMES = ("JMedotcom",)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and add your bot token.")
