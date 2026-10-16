# handlers/inventory.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from db.players import get_lang
from services.inventory import list_inventory, use_item, InvError


async def cmd_inventory(message: Message):
    lang = get_lang(message.from_user.id)
    items = list_inventory(message.from_user.id)

    if not items:
        await message.answer(t("inv.empty", lang))
        return

    lines = [t("inv.header", lang), ""]
    for item in items:
        name = t(f"item.{item['item_key']}.name", lang)
        lines.append(f"• {name} × {item['quantity']}")
    await message.answer("\n".join(lines))


async def cmd_use(message: Message):
    lang = get_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(t("inv.use_no_args", lang))
        return

    item_key = args[1].strip().lower()

    try:
        result = use_item(message.from_user.id, item_key)
    except InvError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    if result["action"] == "eat":
        await message.answer(t("inv.ate", lang, hp=result["hp"]))
    elif result["action"] == "drink":
        await message.answer(t("inv.drank", lang, water=result["water"]))