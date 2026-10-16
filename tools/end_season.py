# tools/end_season.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.i18n import load_locales
from db.connection import init_db
from services.season_manager import get_season_info, end_season


def main():
    load_locales()
    init_db()

    info = get_season_info()
    print(f"Текущий сезон: {info['season_id']}, день {info['day']}")

    confirm = input(f"Завершить сезон {info['season_id']}? (yes/no): ")
    if confirm.lower() != "yes":
        print("Отменено")
        return

    result = end_season(info["season_id"])

    print(f"\nOK: Сезон {result['old_season']} завершён")
    print(f"     Новый сезон: {result['new_season']}")

    if result["winners"]:
        print("\nПобедители:")
        for w in result["winners"]:
            print(f"   {w['place']}. {w['name']} — {w['score']} очков")
    else:
        print("\nПобедителей нет (никто не набрал очков)")


if __name__ == "__main__":
    main()
