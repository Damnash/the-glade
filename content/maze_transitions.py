# content/maze_transitions.py

TRANSITIONS = {
    "ru": [
        "Ты идёшь по узкому коридору. Стены медленно движутся — или это обман зрения. Камень под ногами холодный, покрытый пылью.",
        "Шаги отдаются эхом дважды — будто идёт кто-то ещё. Ты оборачиваешься — никого.",
        "Из стены сочится что-то тёмное. Ты стараешься не касаться. Пахнет железом и старой землёй.",
        "Коридор петляет. Ты теряешь счёт поворотам. Где-то вдалеке — кап. Кап. Кап.",
        "Стены покрыты плющом — сухим, мёртвым. Он хрустит под ногами. Ты замечаешь, что плющ тянется в одну сторону — будто его что-то тащило.",
        "Тёмный проход. Свет от факела дрожит. В воздухе — пыль, которая не двигается. Ты проходишь сквозь неё.",
        "Что-то шепчет за стеной. Слова не разобрать, но интонация — знакомая. Ты ускоряешь шаг.",
        "Коридор прямой, как стрела. Слишком прямой. Ты чувствуешь, что за тобой наблюдают. Оборачиваешься — никого.",
        "Пахнет сыростью и гнилью. Под ногами — вода, тонким слоем. Ты стараешься ступать тише.",
        "Кто-то прошёл здесь до тебя. Видны следы. Ты идёшь по ним.",
        "Стены дрожат. Ты прижимаешься к ним — чувствуешь вибрацию. Что-то двигается глубоко под Лабиринтом.",
        "В темноте блеснуло что-то металлическое. Ты подходишь — обломок. Давно забытый.",
        "Холодный воздух бьёт в лицо. Ты застёгиваешь куртку. Здесь никогда не бывает тепла.",
        "Ты слышишь шаги — не свои. Ты останавливаешься. Шаги тоже. Идёшь — идут. Это эхо. Наверное.",
        "На стене — царапины. Много. Кто-то считал дни. Потом перестал.",
        "Проход расширяется. Становится светлее. Ты почти у цели — или так кажется.",
        "Гул усиливается. Ты чувствуешь его в груди. Стены будто сжимаются.",
        "Ты идёшь долго. Слишком долго для такого короткого пути. Время здесь течёт иначе.",
        "Из темноты вылетает мошка. Потом ещё одна. Потом рой. Ты отмахиваешься и идёшь дальше.",
        "Ты наступаешь на что-то. Смотришь — старая кость. Чья-то. Ты идёшь дальше, не оглядываясь.",
    ],
    "en": [
        "You walk down a narrow corridor. The walls move slowly — or is it an illusion. The stone underfoot is cold, covered in dust.",
        "Your footsteps echo twice — as if someone else is walking. You turn — no one.",
        "Something dark seeps from the wall. You try not to touch it. It smells of iron and old earth.",
        "The corridor winds. You lose count of turns. Somewhere far off — drip. Drip. Drip.",
        "The walls are covered in ivy — dry, dead. It crunches underfoot. You notice the ivy trails in one direction — as if something dragged it.",
        "A dark passage. The torchlight flickers. In the air — dust that does not move. You pass through it.",
        "Something whispers behind the wall. The words are indistinct, but the tone is familiar. You quicken your step.",
        "The corridor is straight as an arrow. Too straight. You feel watched. You turn — no one.",
        "It smells of damp and rot. Under your feet — water, a thin layer. You try to step quieter.",
        "Someone passed here before you. Tracks visible. You follow them.",
        "The walls tremble. You press against them — feel the vibration. Something moves deep beneath the Maze.",
        "Something metallic gleamed in the darkness. You approach — a fragment. Long forgotten.",
        "Cold air hits your face. You button your jacket. There is never warmth here.",
        "You hear footsteps — not your own. You stop. They stop too. You walk — they walk. It's an echo. Probably.",
        "Scratches on the wall. Many. Someone counted days. Then stopped.",
        "The passage widens. It gets lighter. You're almost there — or so it seems.",
        "The hum intensifies. You feel it in your chest. The walls seem to close in.",
        "You walk for a long time. Too long for such a short path. Time flows differently here.",
        "A fly darts out of the darkness. Then another. Then a swarm. You wave them off and keep walking.",
        "You step on something. You look — an old bone. Someone's. You keep walking without looking back.",
    ],
}


def get_transition_text(lang: str, index: int) -> str:
    """Описание перехода по индексу."""
    pool = TRANSITIONS.get(lang, TRANSITIONS["ru"])
    return pool[index % len(pool)]
