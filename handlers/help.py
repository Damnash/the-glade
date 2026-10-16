# handlers/help.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from core.i18n import t
from db.players import get_lang
from keyboards.help import help_main_keyboard, help_cat_keyboard, HELP_CATEGORIES


# Список ключей команд для каждой категории
CATEGORY_KEYS = {
    "movement": ["help.go", "help.look", "help.who", "help.where"],
    "actions": ["help.work", "help.sleep", "help.wake", "help.eat", "help.inventory", "help.use"],
    "maze": ["help.raid", "help.return", "help.keys", "help.time"],
    "communication": ["help.say", "help.whisper", "help.radio", "help.walkie", "help.talk"],
    "clan": ["help.clan", "help.clan_create", "help.clan_invite", "help.clan_chat"],
    "maps": ["help.maps", "help.map_create", "help.map_rename", "help.draw",
             "help.section_rename", "help.section_note", "help.pickup_maps", "help.shares"],
    "pvp": ["help.steal", "help.attack", "help.duel"],
    "progress": ["help.achievements", "help.top", "help.hall", "help.gates"],
    "info": ["help.stats", "help.language", "help.help"],
}


def render_main(lang: str) -> str:
    return (
        f"📜 <b>{t('help.title', lang)}</b>\n\n"
        f"{t('help.choose_category', lang)}"
    )


def render_category(lang: str, cat: str) -> str:
    cat_title = t(f"help.cat.{cat}", lang)
    keys = CATEGORY_KEYS.get(cat, [])

    lines = [cat_title, ""]

    for key in keys:
        line = t(key, lang)
        if line != key:
            lines.append(f"  {line}")

    if len(lines) == 2:
        lines.append(t("help.empty_category", lang))

    return "\n".join(lines)


# ============ Команда ============

async def cmd_help(message: Message):
    lang = get_lang(message.from_user.id)
    text = render_main(lang)
    kb = help_main_keyboard(lang)
    await message.answer(text, reply_markup=kb)


# ============ Callbacks ============

async def on_help_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    text = render_main(lang)
    kb = help_main_keyboard(lang)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


async def on_help_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    cat = callback.data.split(":")[2]  # help:cat:movement

    text = render_category(lang, cat)
    kb = help_cat_keyboard(lang)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()
