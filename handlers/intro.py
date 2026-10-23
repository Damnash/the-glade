# handlers/intro.py

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.locations import START_LOCATION
from content.professions import PROFESSIONS, PERKS
from content.intro_dialogs import STARTER_INVENTORY
from db.players import get_player, update_player_fields
from db.inventory import add_item


def intro_keyboard(lang: str, step: str) -> InlineKeyboardMarkup:
    """Клавиатура для разных шагов."""
    if step == "step_dark":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("intro.btn_open_eyes", lang),
                                  callback_data="intro:next:step_choose_perk")
        ]])

    if step == "step_wake":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("intro.btn_wait", lang),
                                  callback_data="intro:next:step_cage")
        ]])

    if step == "step_cage":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("intro.btn_stand", lang),
                                  callback_data="intro:next:step_arrive")
        ]])

    if step == "step_arrive":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("intro.btn_speak", lang),
                                  callback_data="intro:next:step_q1")
        ]])

    if step in ("step_choose", "step_choose_perk", "step_q1"):
        # Перки
        buttons = []
        for key, perk in PERKS.items():
            buttons.append([
                InlineKeyboardButton(
                    text=f"{perk['icon']} {t(perk['name_key'], lang)}",
                    callback_data=f"intro:perk:{key}",
                )
            ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    if step in ("step_choose_prof", "step_q2"):
        # Профессии
        buttons = []
        for key, prof in PROFESSIONS.items():
            buttons.append([
                InlineKeyboardButton(
                    text=f"{prof['icon']} {t(prof['name_key'], lang)}",
                    callback_data=f"intro:prof:{key}",
                )
            ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    if step == "step_gift":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("intro.btn_look_around", lang),
                                  callback_data="intro:finish")
        ]])

    return InlineKeyboardMarkup(inline_keyboard=[])


def render_intro(lang: str, step: str, player: dict = None) -> str:
    """Рендер экрана вступления."""
    if step == "step_dark":
        return t("intro.step_dark", lang)

    if step == "step_wake":
        return t("intro.step_wake", lang)

    if step == "step_cage":
        return t("intro.step_cage", lang)

    if step == "step_arrive":
        return t("intro.step_arrive", lang)

    if step in ("step_choose", "step_choose_perk", "step_q1"):
        return t("intro.step_choose", lang)

    if step in ("step_choose_prof", "step_q2"):
        return t("intro.step_choose_prof", lang)

    if step == "step_gift":
        lines = [t("intro.step_gift", lang), ""]
        for item_key, qty in STARTER_INVENTORY.items():
            name = t(f"item.{item_key}.name", lang)
            lines.append(f"  • {name} × {qty}")
        return "\n".join(lines)

    return "?"


async def start_intro(bot: Bot, user_id: int, lang: str):
    """Запустить вступление."""
    from core.bot_helpers import edit_main
    text = render_intro(lang, "step_dark")
    kb = intro_keyboard(lang, "step_dark")
    await edit_main(bot, user_id, text, kb)


async def on_intro_next(callback: CallbackQuery, bot: Bot):
    """Переход к следующему шагу."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    # intro:next:step_xxx
    parts = callback.data.split(":")
    step = parts[2] if len(parts) > 2 else "step_dark"

    from core.bot_helpers import edit_main
    text = render_intro(lang, step)
    kb = intro_keyboard(lang, step)
    await edit_main(bot, user_id, text, kb)
    await callback.answer()


async def on_intro_perk(callback: CallbackQuery, bot: Bot):
    """Выбор перка."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    perk_key = callback.data.split(":")[2]

    if perk_key not in PERKS:
        await callback.answer("Unknown perk.", show_alert=True)
        return

    # Применяем бонусы перка сразу (с клипом до max_hp/max_energy)
    from content.professions import PERKS as PERKS_DATA

    perk_spec = PERKS_DATA[perk_key]
    hp_bonus = perk_spec["bonus"].get("max_hp", 0)
    energy_bonus = perk_spec["bonus"].get("max_energy", 0)

    updates = {"perk": perk_key}
    if hp_bonus:
        updates["hp"] = player["hp"] + hp_bonus
    if energy_bonus:
        updates["energy"] = player["energy"] + energy_bonus

    # Клип по новым максимумам (с учётом уже выбранной профессии, если есть)
    from services.bonuses import get_player_bonus
    tmp = dict(player)
    tmp["perk"] = perk_key
    bonus = get_player_bonus(tmp)
    if "hp" in updates:
        updates["hp"] = min(updates["hp"], bonus["max_hp"])
    if "energy" in updates:
        updates["energy"] = min(updates["energy"], bonus["max_energy"])

    update_player_fields(user_id, updates)

    perk = PERKS[perk_key]
    await callback.answer(
        t("intro.perk_chosen", lang, name=t(perk["name_key"], lang)),
        show_alert=True,
    )

    from core.bot_helpers import edit_main
    text = render_intro(lang, "step_choose_prof")
    kb = intro_keyboard(lang, "step_choose_prof")
    await edit_main(bot, user_id, text, kb)



async def on_intro_prof(callback: CallbackQuery, bot: Bot):
    """Выбор профессии."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    prof_key = callback.data.split(":")[2]

    if prof_key not in PROFESSIONS:
        await callback.answer("Unknown profession.", show_alert=True)
        return

    # Применяем бонусы профессии (с клипом до max_hp/max_energy)
    prof = PROFESSIONS[prof_key]
    hp_bonus = prof["bonus"].get("max_hp", 0)
    energy_bonus = prof["bonus"].get("max_energy", 0)

    updates = {"profession": prof_key}
    if hp_bonus:
        updates["hp"] = player["hp"] + hp_bonus
    if energy_bonus:
        updates["energy"] = player["energy"] + energy_bonus

    # Клип по новым максимумам (с учётом уже выбранного перка, если есть)
    from services.bonuses import get_player_bonus
    tmp = dict(player)
    tmp["profession"] = prof_key
    bonus = get_player_bonus(tmp)
    if "hp" in updates:
        updates["hp"] = min(updates["hp"], bonus["max_hp"])
    if "energy" in updates:
        updates["energy"] = min(updates["energy"], bonus["max_energy"])

    update_player_fields(user_id, updates)

    await callback.answer(
        t("intro.prof_chosen", lang, name=t(prof["name_key"], lang)),
        show_alert=True,
    )

    from core.bot_helpers import edit_main
    text = render_intro(lang, "step_gift")
    kb = intro_keyboard(lang, "step_gift")
    await edit_main(bot, user_id, text, kb)



async def on_intro_finish(callback: CallbackQuery, bot: Bot):
    """Завершение вступления."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    # Выдать инвентарь
    for item_key, qty in STARTER_INVENTORY.items():
        add_item(user_id, item_key, qty)

    # Компас для инженера
    if player.get("profession") == "engineer":
        add_item(user_id, "compass", 1)

    # Бинты для медика
    if player.get("profession") == "medic":
        add_item(user_id, "bandage", 3)

    # Отметить intro завершённым
    update_player_fields(user_id, {"intro_done": 1})

    await callback.answer(t("intro.finished", lang))

    # Запустить первый квест
    try:
        from services.starter_quest import start_starter_quest
        start_starter_quest(user_id)
    except Exception:
        pass

    from core.bot_helpers import refresh_main
    await refresh_main(bot, user_id)

