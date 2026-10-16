# config.py — файл конфигурации бота

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")

DB_PATH = "data/game.db"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ["en", "ru"]

ADMIN_IDS = [
    1988518954,
]