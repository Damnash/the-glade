# services/maps.py

import re

from core.maze_current import get_current_season
from db.map_items import (
    create_map, get_map, get_player_maps, get_personal_map,
    rename_map, delete_map, count_player_maps, get_map_limit,
    is_map_full, get_map_sections, add_section_to_map,
    count_map_sections,
)


class MapError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


NAME_MIN = 2
NAME_MAX = 30
NAME_PATTERN = re.compile(r"^[\w\s\-'«»\.]+$", re.UNICODE)


def validate_name(name: str) -> str | None:
    """Проверить имя карты. Возвращает ключ ошибки или None."""
    name = name.strip()

    if len(name) < NAME_MIN:
        return "map.err.name_short"
    if len(name) > NAME_MAX:
        return "map.err.name_long"
    if not NAME_PATTERN.match(name):
        return "map.err.name_invalid"

    return None


def create_personal_map(user_id: int, display_name: str) -> int:
    """Создать личную карту при старте."""
    name = f"Карта {display_name}"
    return create_map(
        creator_id=user_id,
        name=name,
        is_personal=True,
        owner_id=user_id,
    )


def ensure_personal_map(user_id: int, display_name: str) -> dict:
    """Убедиться, что у игрока есть личная карта."""
    existing = get_personal_map(user_id)
    if existing:
        return existing
    map_id = create_personal_map(user_id, display_name)
    return get_map(map_id)


def create_new_map(user_id: int, name: str) -> int:
    """Создать новую карту игрока."""
    err = validate_name(name)
    if err:
        raise MapError(err)

    if is_map_full(user_id):
        limit = get_map_limit(user_id)
        raise MapError("map.err.limit", limit=limit)

    # Проверяем, нет ли карты с таким именем
    maps = get_player_maps(user_id)
    for m in maps:
        if m["name"].lower() == name.lower().strip():
            raise MapError("map.err.name_duplicate")

    return create_map(creator_id=user_id, name=name.strip())


def rename_player_map(user_id: int, map_id: int, new_name: str):
    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    err = validate_name(new_name)
    if err:
        raise MapError(err)

    # Проверка дубликата имени
    maps = get_player_maps(user_id)
    for other in maps:
        if other["id"] != map_id and other["name"].lower() == new_name.lower().strip():
            raise MapError("map.err.name_duplicate")

    rename_map(map_id, new_name.strip())


def delete_player_map(user_id: int, map_id: int):
    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    if m["is_personal"]:
        raise MapError("map.err.cannot_delete_personal")

    delete_map(map_id)


def draw_section(user_id: int, map_id: int, section_id: str, layer: int,
                 custom_name: str | None = None) -> bool:
    """
    Нарисовать секцию на карте.
    Возвращает True, если добавлено, False если уже было.
    """
    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    season = get_current_season()
    return add_section_to_map(map_id, season, layer, section_id, custom_name)


def get_map_view(map_id: int, user_id: int, layer: int) -> dict:
    """Данные для отображения карты."""
    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    season = get_current_season()
    sections = get_map_sections(map_id, season, layer)

    return {
        "map": m,
        "sections": sections,
        "count": len(sections),
    }


NOTE_MAX = 100


def validate_note(note: str) -> str | None:
    """Проверить заметку."""
    note = note.strip()
    if len(note) > NOTE_MAX:
        return "map.err.note_long"
    return None


def update_section(map_id: int, user_id: int, section_id: str, layer: int,
                   custom_name: str | None = None,
                   note: str | None = None) -> dict:
    """Обновить секцию на карте. Возвращает обновлённую."""
    from db.map_items import get_section_on_map, update_section_name, update_section_note
    from core.maze_current import get_current_season

    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    season = get_current_season()

    sec = get_section_on_map(map_id, season, layer, section_id)
    if not sec:
        raise MapError("map.err.section_not_found")

    if custom_name is not None:
        err = validate_name(custom_name)
        if err:
            raise MapError(err)
        update_section_name(map_id, season, layer, section_id, custom_name.strip())

    if note is not None:
        err = validate_note(note)
        if err:
            raise MapError(err)
        update_section_note(map_id, season, layer, section_id, note.strip() or None)

    return get_section_on_map(map_id, season, layer, section_id)


def remove_section(map_id: int, user_id: int, section_id: str, layer: int):
    """Удалить секцию с карты."""
    from db.map_items import remove_section_from_map
    from core.maze_current import get_current_season

    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    season = get_current_season()
    remove_section_from_map(map_id, season, layer, section_id)



# ============ Показ карт другим ============

def share_map(map_id: int, from_id: int, to_nick: str) -> dict:
    """Поделиться картой с другим игроком."""
    from db.players import find_by_name
    from db.map_items import create_share, get_map, count_map_sections
    from core.maze_current import get_current_season

    m = get_map(map_id)
    if not m or m["owner_id"] != from_id:
        raise MapError("map.err.not_yours")

    target = find_by_name(to_nick)
    if not target:
        raise MapError("map.err.player_not_found")

    if target["user_id"] == from_id:
        raise MapError("map.err.cant_share_self")

    share_id = create_share(map_id, from_id, target["user_id"])

    # Считаем секции
    season = get_current_season()
    count = count_map_sections(map_id, season, 1)

    return {
        "share_id": share_id,
        "to_id": target["user_id"],
        "to_name": target["display_name"] or target["username"],
        "map_name": m["name"],
        "sections_count": count,
    }


def get_shared_view(share_id: int, user_id: int, layer: int = 1) -> dict:
    """Просмотр показанной карты."""
    from db.map_items import get_share, get_map, get_map_sections
    from core.maze_current import get_current_season

    share = get_share(share_id)
    if not share:
        raise MapError("map.err.share_not_found")

    if share["to_id"] != user_id:
        raise MapError("map.err.share_not_yours")

    if share["expires_at"]:
        from datetime import datetime
        exp = share["expires_at"]
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if exp <= datetime.utcnow():
            raise MapError("map.err.share_expired")

    m = get_map(share["map_id"])
    if not m:
        raise MapError("map.err.share_not_found")

    season = get_current_season()
    sections = get_map_sections(share["map_id"], season, layer)

    # Инфа об отправителе
    from db.players import get_player
    sender = get_player(share["from_id"])
    sender_name = "?" if not sender else (sender["display_name"] or sender["username"])

    return {
        "share": share,
        "map": m,
        "sections": sections,
        "sender_name": sender_name,
    }


def copy_from_share(share_id: int, user_id: int, target_map_id: int, layer: int = 1) -> int:
    """
    Скопировать секции из показанной карты в свою.
    Возвращает количество новых секций.
    """
    from db.map_items import (
        get_share, get_map, get_map_sections,
        add_section_to_map, mark_share_copied,
    )
    from core.maze_current import get_current_season

    share = get_share(share_id)
    if not share or share["to_id"] != user_id:
        raise MapError("map.err.share_not_yours")

    target_map = get_map(target_map_id)
    if not target_map or target_map["owner_id"] != user_id:
        raise MapError("map.err.not_yours")

    season = get_current_season()
    source_sections = get_map_sections(share["map_id"], season, layer)

    added = 0
    for s in source_sections:
        ok = add_section_to_map(
            target_map_id, season, layer, s["section_id"],
            custom_name=s["custom_name"], note=s["note"],
        )
        if ok:
            added += 1

    mark_share_copied(share_id)
    return added

