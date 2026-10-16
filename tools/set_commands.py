# tools/set_commands.py

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from aiogram.types import BotCommand

from config import BOT_TOKEN
from core.i18n import load_locales, t, get_all_translations


COMMANDS = [
    "start", "help", "look", "go", "who",
    "where", "language", "stats", "sleep", "wake",
    "work", "eat", "inventory", "use",
]


def clean_desc(desc: str) -> str:
    desc = desc.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    for sep in (" — ", " - ", " – "):
        if sep in desc:
            desc = desc.split(sep, 1)[1]
            break
    return desc.strip()[:256]


def build_commands(all_langs: dict, lang: str) -> list[BotCommand]:
    """
    Команды всегда латиницей (всегда en-алиасы).
    Описания — на выбранном языке.
    """
    result = []
    for key in COMMANDS:
        # Всегда берём английский алиас — BotCommand не поддерживает кириллицу
        en_aliases = all_langs.get("en", {}).get(f"commands.{key}")
        if isinstance(en_aliases, str):
            en_aliases = [en_aliases]
        if not en_aliases:
            continue
        alias = en_aliases[0]

        # Описание — на нужном языке
        desc = clean_desc(t(f"help.{key}", lang))
        result.append(BotCommand(command=alias, description=desc))
    return result


async def main():
    load_locales()
    all_langs = get_all_translations()

    bot = Bot(token=BOT_TOKEN)

    en_cmds = build_commands(all_langs, "en")
    await bot.set_my_commands(en_cmds)
    print(f"✅ Default: {len(en_cmds)} commands")

    ru_cmds = build_commands(all_langs, "ru")
    await bot.set_my_commands(ru_cmds, language_code="ru")
    print(f"✅ RU: {len(ru_cmds)} commands")

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())