# content/intro_dialogs.py

INTRO_STEPS = [
    "intro.step_dark",
    "intro.step_choose",   # Перк + профессия на одном этапе
    "intro.step_gift",
]

# Внутренние шаги (не в INTRO_STEPS, но нужны для логики)
INTERNAL_STEPS = [
    "step_choose_perk",    # выбор перка
    "step_choose_prof",    # выбор профессии (после перка)
]


# Инвентарь, который даёт Ньют
STARTER_INVENTORY = {
    "knife": 1,
    "ration": 3,
    "water_flask": 2,
    "torch": 2,
    "rope": 1,
}
