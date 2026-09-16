# Telegram Job Search Bot

Минимальный Telegram-бот на Python, который читает публичные web-страницы Telegram-каналов, фильтрует вакансии по категории и навыкам и показывает результаты с пагинацией.

## Installation

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Создай файл `.env` рядом с `main.py` и добавь токен бота:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/findyourjob
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-3.6-flash
```

Для AI-анализа создай API key в OpenRouter и добавь его в `.env` как `OPENROUTER_API_KEY`. Модель можно изменить через `OPENROUTER_MODEL`. Без ключа бот использует rule-based fallback.

После установки зависимостей миграции профиля и обучения применяются автоматически при запуске бота. Их можно проверить отдельно:

```powershell
python ..\migrate.py
```

Запуск:

```powershell
python main.py
```

Автоматические уведомления отключены. Основной сценарий: `/start` → выбор категории и навыков → поиск → анализ вакансии → обучение.

Учебные видео хранятся в PostgreSQL в таблице `learning_materials`. Для добавления видео вставь строку в `job_bot/migrations/004_replace_notifications_with_learning_materials.sql` и выполни `python ..\migrate.py`:

```sql
INSERT INTO learning_materials (skill, title, description, youtube_url, language)
VALUES ('docker', 'Docker для начинающих', 'Базовый курс', 'https://youtube.com/watch?v=...', 'ru')
ON CONFLICT (skill, title, language) DO NOTHING;
```

Парсер использует только публичные HTML-страницы `https://t.me/s/<channel>` и обычную публичную страницу как HTTP fallback. Telegram API credentials и session-файлы не используются.
