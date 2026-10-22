# services/clans.py

import re

from core.maze_current import get_current_season
from db.clans import (
    create_clan, get_clan, get_clan_by_name, get_player_clan, get_player_role,
    get_clan_members, count_clan_members, update_clan_role,
    remove_from_clan, set_clan_motto, set_clan_treasury, disband_clan,
    create_invite, get_pending_invites, get_invite, delete_invite,
    add_clan_message, get_clan_messages,
    add_section_to_clan_map, get_clan_map_sections, count_clan_map_sections,
)
from db.players import get_player, update_player_fields


class ClanError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


NAME_MIN = 2
NAME_MAX = 20
MOTTO_MAX = 60

MAX_MEMBERS = 25
MIN_MEMBERS_TO_CREATE = 5  # фиктивно — можно создать одному
CREATE_COST = 100


# ============ Валидация ============

def validate_name(name: str) -> str | None:
    name = name.strip()
    if len(name) < NAME_MIN:
        return "clan.err.name_short"
    if len(name) > NAME_MAX:
        return "clan.err.name_long"
    if not re.match(r"^[\w\s\-'«»\.]+$", name, re.UNICODE):
        return "clan.err.name_invalid"
    return None


# ============ Создание ============

def create(user_id: int, name: str) -> int:
    """Создать клан."""
    player = get_player(user_id)
    if not player:
        raise ClanError("start.need_start")

    if get_player_clan(user_id):
        raise ClanError("clan.err.already_in_clan")

    err = validate_name(name)
    if err:
        raise ClanError(err)

    if get_clan_by_name(name):
        raise ClanError("clan.err.name_taken")

    if player.get("tokens", 0) < CREATE_COST:
        raise ClanError("clan.err.not_enough_tokens", cost=CREATE_COST)

    # Списываем жетоны
    update_player_fields(user_id, {
        "tokens": player["tokens"] - CREATE_COST,
    })

    clan_id = create_clan(user_id, name.strip())
    set_clan_treasury(clan_id, CREATE_COST)

    return clan_id


# ============ Приглашения ============

def invite(clan_id: int, from_id: int, to_user_id: int) -> None:
    """Пригласить игрока."""
    from db.players import get_player

    if count_clan_members(clan_id) >= MAX_MEMBERS:
        raise ClanError("clan.err.max_members", max=MAX_MEMBERS)

    target = get_player(to_user_id)
    if not target:
        raise ClanError("clan.err.player_not_found")

    if get_player_clan(to_user_id):
        raise ClanError("clan.err.player_already_in_clan")

    # Уже есть приглашение?
    invites = get_pending_invites(to_user_id)
    for inv in invites:
        if inv["clan_id"] == clan_id:
            raise ClanError("clan.err.already_invited")

    create_invite(clan_id, from_id, to_user_id)


def accept_invite(user_id: int, invite_id: int) -> int:
    """Принять приглашение."""
    invite = get_invite(invite_id)
    if not invite or invite["to_id"] != user_id:
        raise ClanError("clan.err.invite_not_found")

    if get_player_clan(user_id):
        raise ClanError("clan.err.already_in_clan")

    clan_id = invite["clan_id"]
    clan = get_clan(clan_id)
    if not clan:
        raise ClanError("clan.err.clan_not_found")

    if count_clan_members(clan_id) >= MAX_MEMBERS:
        raise ClanError("clan.err.max_members", max=MAX_MEMBERS)

    from db.connection import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clan_members (clan_id, user_id, role)
        VALUES (?, ?, 'recruit')
    """, (clan_id, user_id))
    conn.commit()
    conn.close()

    delete_invite(invite_id)
    return clan_id


# ============ Роли ============

VALID_ROLES = ["advisor", "treasurer", "warrior", "scout", "recruit"]


def set_role(clan_id: int, from_user_id: int, to_user_id: int, role: str):
    """Изменить роль."""
    from_role = get_player_role(from_user_id)
    if from_role != "leader":
        raise ClanError("clan.err.only_leader")

    if role not in VALID_ROLES:
        raise ClanError("clan.err.invalid_role")

    target_clan = get_player_clan(to_user_id)
    if not target_clan or target_clan["clan_id"] != clan_id:
        raise ClanError("clan.err.not_in_clan")

    update_clan_role(clan_id, to_user_id, role)


# ============ Выход ============

def leave(user_id: int):
    """Выйти из клана."""
    clan = get_player_clan(user_id)
    if not clan:
        raise ClanError("clan.err.not_in_clan")

    role = get_player_role(user_id)
    if role == "leader":
        # Лидер не может выйти просто так
        raise ClanError("clan.err.leader_cant_leave")

    remove_from_clan(user_id)


def kick(clan_id: int, from_user_id: int, to_user_id: int):
    """Исключить игрока."""
    from_role = get_player_role(from_user_id)
    if from_role not in ("leader", "advisor"):
        raise ClanError("clan.err.no_permission")

    target_role = get_player_role(to_user_id)
    if target_role == "leader":
        raise ClanError("clan.err.cant_kick_leader")

    target_clan = get_player_clan(to_user_id)
    if not target_clan or target_clan["clan_id"] != clan_id:
        raise ClanError("clan.err.not_in_clan")

    remove_from_clan(to_user_id)


# ============ Казна ============

def donate(user_id: int, amount: int):
    """Внести в казну."""
    clan = get_player_clan(user_id)
    if not clan:
        raise ClanError("clan.err.not_in_clan")

    if amount <= 0:
        raise ClanError("clan.err.invalid_amount")

    player = get_player(user_id)
    if player.get("tokens", 0) < amount:
        raise ClanError("clan.err.not_enough_tokens", cost=amount)

    update_player_fields(user_id, {
        "tokens": player["tokens"] - amount,
    })
    set_clan_treasury(clan["clan_id"], clan["treasury"] + amount)


# ============ Чат ============

def send_clan_message(user_id: int, text: str) -> dict:
    """Отправить сообщение в клан."""
    clan = get_player_clan(user_id)
    if not clan:
        raise ClanError("clan.err.not_in_clan")

    player = get_player(user_id)
    display_name = player["display_name"] or player["username"]

    add_clan_message(clan["clan_id"], user_id, display_name, text)

    # Кто получит
    members = get_clan_members(clan["clan_id"])
    recipients = [m["user_id"] for m in members if m["user_id"] != user_id]

    return {
        "clan_id": clan["clan_id"],
        "clan_name": clan["name"],
        "display_name": display_name,
        "text": text,
        "recipients": recipients,
    }


# ============ Клановая карта ============

def sync_map_from_player(user_id: int) -> int:
    """
    Внести личную карту игрока в клановую.
    Возвращает количество новых секций.
    """
    clan = get_player_clan(user_id)
    if not clan:
        raise ClanError("clan.err.not_in_clan")

    from db.map_items import get_personal_map, get_map_sections

    personal = get_personal_map(user_id)
    if not personal:
        return 0

    season = get_current_season()
    layer = 1
    sections = get_map_sections(personal["id"], season, layer)

    added = 0
    for s in sections:
        if add_section_to_clan_map(
            clan["clan_id"], season, layer, s["section_id"],
            contributed_by=user_id,
            custom_name=s.get("custom_name"),
            note=s.get("note"),
        ):
            added += 1

    return added


def get_clan_map(clan_id: int, layer: int = 1) -> dict:
    """Клановая карта."""
    season = get_current_season()
    sections = get_clan_map_sections(clan_id, season, layer)
    return {
        "sections": sections,
        "count": len(sections),
    }


# ============ Апгрейды Глэййда (v1.1) ============

def upgrade_clan(clan_id: int, upgrade_key: str) -> dict:
    """
    Повысить уровень апгрейда.
    Списывает ресурсы со склада + жетоны из treasury.
    Возвращает {'upgrade_key': str, 'new_level': int}.
    """
    from content.clan_upgrades import get_upgrade, get_next_level
    from db.clans import (
        get_clan, get_upgrade_level, set_upgrade_level,
        get_storage_item, remove_from_storage, set_clan_treasury,
    )

    upgrade = get_upgrade(upgrade_key)
    if not upgrade:
        raise ClanError("upgrade.unknown")

    current_level = get_upgrade_level(clan_id, upgrade_key)
    next_level = get_next_level(upgrade_key, current_level)

    if next_level is None:
        raise ClanError("upgrade.max_level")

    cost = upgrade["costs"][next_level]
    tokens_cost = cost.get("tokens", 0)

    clan = get_clan(clan_id)
    if not clan:
        raise ClanError("clan.err.clan_not_found")

    # Проверка ресурсов на складе
    for item_key, qty in cost.items():
        if item_key == "tokens":
            continue
        have = get_storage_item(clan_id, item_key)
        if have < qty:
            raise ClanError(
                "upgrade.not_enough",
                item=item_key, need=qty, have=have,
            )

    # Проверка жетонов
    if clan["treasury"] < tokens_cost:
        raise ClanError(
            "upgrade.not_enough_tokens",
            need=tokens_cost, have=clan["treasury"],
        )

    # Списание
    for item_key, qty in cost.items():
        if item_key == "tokens":
            continue
        remove_from_storage(clan_id, item_key, qty)

    if tokens_cost > 0:
        set_clan_treasury(clan_id, clan["treasury"] - tokens_cost)

    # Повышение
    set_upgrade_level(clan_id, upgrade_key, next_level)

    return {"upgrade_key": upgrade_key, "new_level": next_level}


def get_clan_bonuses(clan_id: int) -> dict:
    """
    Сумма бонусов от всех апгрейдов клана.
    """
    from content.clan_upgrades import CLAN_UPGRADES
    from db.clans import get_all_upgrades

    levels = get_all_upgrades(clan_id)
    bonuses = {}

    for key, level in levels.items():
        if level <= 0:
            continue
        upgrade = CLAN_UPGRADES.get(key)
        if not upgrade:
            continue
        bonus = upgrade["bonus"].get(level, {})
        for bkey, bvalue in bonus.items():
            if bkey in bonuses:
                bonuses[bkey] = max(bonuses[bkey], bvalue)
            else:
                bonuses[bkey] = bvalue

    return bonuses

def join_open_clan(user_id: int, clan_id: int) -> dict:
    """Вступить в открытый клан без приглашения."""
    from db.clans import (
        get_clan, get_player_clan, count_clan_members, join_clan,
        set_clan_open,
    )
    # MAX_MEMBERS в db/clans нет — он в services
    from services.clans import MAX_MEMBERS

    if get_player_clan(user_id):
        raise ClanError("clan.err.already_in_clan")

    clan = get_clan(clan_id)
    if not clan:
        raise ClanError("clan.err.clan_not_found")

    if not clan.get("is_open"):
        raise ClanError("clan.err.not_open")

    if count_clan_members(clan_id) >= MAX_MEMBERS:
        raise ClanError("clan.err.max_members", max=MAX_MEMBERS)

    join_clan(clan_id, user_id, role="recruit")

    # Записать в журнал нового участника
    try:
        from core.i18n import t
        from services.event_log import add_event, cleanup_old_events
        from db.players import get_player
        p = get_player(user_id)
        if p:
            add_event(user_id, "clan_joined",
                      t("clan.joined", p["language"], name=clan["name"]),
                      severity="important")
            cleanup_old_events(user_id)
    except Exception:
        pass

    return {"clan_id": clan_id, "clan_name": clan["name"]}


def set_open(user_id: int, is_open: bool) -> bool:
    """Лидер включает/выключает открытость клана."""
    from db.clans import get_player_clan, get_player_role, set_clan_open

    clan = get_player_clan(user_id)
    if not clan:
        raise ClanError("clan.err.not_in_clan")

    role = get_player_role(user_id)
    if role != "leader":
        raise ClanError("clan.err.only_leader")

    set_clan_open(clan["clan_id"], 1 if is_open else 0)
    return is_open

