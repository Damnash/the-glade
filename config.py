# config.py — файл конфигурации бота

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")

# Путь к БД. По умолчанию — data/game.db (живая).
# Переопределяется через переменную окружения GLADE_DB.
# Пример: GLADE_DB=data/game_test.db python bot.py
DB_PATH = os.getenv("GLADE_DB", "data/game.db")

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ["en", "ru"]

ADMIN_IDS = [
    1988518954,
]
