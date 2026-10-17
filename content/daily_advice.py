# content/daily_advice.py
#
# Пул советов дня. Раз в сутки (утром) выбирается один.
#
# Типы:
#   static  — простая фраза
#   context — генерируется по контексту (см. get_context_advice)


STATIC_ADVICE = [
    # day keys для i18n
    "advice.day.fragments",
    "advice.day.keys",
    "advice.day.explore",
    "advice.day.return_alive",
    "advice.day.griever",
    "advice.day.clan",
    "advice.day.food",
    "advice.day.north",
    "advice.day.south",
    "advice.day.center",
]


def get_static_advice() -> list[str]:
    return STATIC_ADVICE


def get_context_advice(context: dict) -> str | None:
    """
    Возвращает ключ контекстного совета или None.
    
    context:
      - day: номер дня сезона
      - keys_found: сколько ключей найдено сегодня
      - active_runs: сколько игроков сейчас в вылазке
    """
    day = context.get("day", 1)
    keys = context.get("keys_found", 0)
    runs = context.get("active_runs", 0)

    if day >= 70 and keys < 5:
        return "advice.context.keys_final"
    if day <= 5:
        return "advice.context.beginning"
    if runs >= 3:
        return "advice.context.many_runners"

    return None
