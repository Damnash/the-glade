# handlers/admin.py

from aiogram.filters import Command
from aiogram.types import Message

from utils.decorators import admin_only
from services.admin import (
    get_all_players, get_online_players, get_players_in_location,
    get_server_stats, admin_give_item, admin_set_field,
)
from db.players import find_by_name


def fmt_player(p: dict, short: bool = False) -> str:
    name = p.get("display_name") or p.get("username") or f"id{p['user_id']}"
    if short:
        return f"• {name} — {p['location']} ({p['status']})"
    return (
        f"👤 <b>{name}</b> (id {p['user_id']})\n"
        f"   📍 {p['location']}   💤 {p['status']}\n"
        f"   ❤️ {p['hp']}/100   ⚡ {p['energy']}/100\n"
        f"   🍞 {p['food']}   💧 {p['water']}   🪙 {p['tokens']}\n"
        f"   🌐 {p['language']}   🕐 {p.get('last_seen', '?')}"
    )


@admin_only
async def cmd_admin(message: Message):
    await message.answer(
        "🛠️ <b>Admin commands</b>\n\n"
        "/admin players — all players\n"
        "/admin online — online (24h)\n"
        "/admin player &lt;ник&gt; — one player\n"
        "/admin location &lt;loc&gt; — who is in location\n"
        "/admin stats — server stats\n"
        "/admin give &lt;ник&gt; &lt;item&gt; &lt;кол&gt; — give item\n"
        "/admin set &lt;ник&gt; &lt;field&gt; &lt;value&gt; — set field"
    )


@admin_only
async def cmd_admin_players(message: Message):
    players = get_all_players(limit=50)
    if not players:
        await message.answer("No players.")
        return

    lines = [f"👥 <b>All players</b> ({len(players)}):", ""]
    for p in players:
        lines.append(fmt_player(p, short=True))
    await message.answer("\n".join(lines))


@admin_only
async def cmd_admin_online(message: Message):
    players = get_online_players(hours=24)
    if not players:
        await message.answer("No one online in 24h.")
        return

    lines = [f"🟢 <b>Online (24h)</b> ({len(players)}):", ""]
    for p in players:
        lines.append(fmt_player(p, short=True))
    await message.answer("\n".join(lines))


@admin_only
async def cmd_admin_player(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /admin player &lt;ник&gt;")
        return

    target = find_by_name(args[2])
    if not target:
        await message.answer("Player not found.")
        return

    await message.answer(fmt_player(target))


@admin_only
async def cmd_admin_location(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /admin location &lt;loc&gt;")
        return

    loc = args[2].strip().lower()
    players = get_players_in_location(loc)
    if not players:
        await message.answer(f"No players in {loc}.")
        return

    lines = [f"📍 <b>{loc}</b> ({len(players)}):", ""]
    for p in players:
        lines.append(fmt_player(p, short=True))
    await message.answer("\n".join(lines))


@admin_only
async def cmd_admin_stats(message: Message):
    s = get_server_stats()
    await message.answer(
        f"📊 <b>Server stats</b>\n\n"
        f"👥 Total players: {s['total']}\n"
        f"🟢 Active 7d: {s['active_7d']}\n"
        f"🕐 Online 24h: {s['online_24h']}\n"
        f"💤 Sleeping: {s['sleeping']}"
    )


@admin_only
async def cmd_admin_give(message: Message):
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.answer("Usage: /admin give &lt;ник&gt; &lt;item&gt; &lt;кол&gt;")
        return

    target = find_by_name(args[2])
    if not target:
        await message.answer("Player not found.")
        return

    try:
        qty = int(args[4])
    except ValueError:
        await message.answer("Quantity must be a number.")
        return

    admin_give_item(target["user_id"], args[3], qty)
    await message.answer(
        f"✅ Gave {qty}× {args[3]} to {target['display_name']}"
    )


@admin_only
async def cmd_admin_set(message: Message):
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.answer("Usage: /admin set &lt;ник&gt; &lt;field&gt; &lt;value&gt;")
        return

    target = find_by_name(args[2])
    if not target:
        await message.answer("Player not found.")
        return

    field, value = args[3], args[4]

    # Пытаемся преобразовать value в число, если поле числовое
    NUMERIC = {"hp", "energy", "food", "water", "tokens"}
    if field in NUMERIC:
        try:
            value = int(value)
        except ValueError:
            await message.answer("Value must be a number.")
            return

    try:
        admin_set_field(target["user_id"], field, value)
    except ValueError as e:
        await message.answer(str(e))
        return

    await message.answer(
        f"✅ {target['display_name']}: {field} = {value}"
    )

@admin_only
async def cmd_admin_router(message: Message):
    parts = message.text.split(maxsplit=2)

    # /admin — показать справку
    if len(parts) < 2:
        await cmd_admin(message)
        return

    sub = parts[1].lower()

    handlers = {
        "players":  cmd_admin_players,
        "online":   cmd_admin_online,
        "player":   cmd_admin_player,
        "location": cmd_admin_location,
        "stats":    cmd_admin_stats,
        "give":     cmd_admin_give,
        "set":      cmd_admin_set,
    }

    fn = handlers.get(sub)
    if not fn:
        await message.answer(
            f"❌ Unknown subcommand: <code>{sub}</code>\n"
            f"Try /admin for the list."
        )
        return

    await fn(message)