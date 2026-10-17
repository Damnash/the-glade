# 🌀 The Glade

**Text survival game in a living maze. Telegram bot.**

A 90-day seasonal roguelike inspired by *The Maze Runner*.
Survive in the Glade. Explore the Maze. Find 5 keys. Open the Gates.

---

## 🎯 What is it

- **Glade** — safe zone: work, sleep, trade, clan life.
- **Maze** — dangerous: Grievers, shifting walls, 10-minute runs.
- **Goal** — 5 keys → Gates → escape before day 90.
- **Season** — 90 days, then reset. New season, new stories.

## 🛠 Tech Stack

- Python 3.14
- aiogram 3.x
- SQLite (WAL mode)
- ~70 modules, 9 content files

## 🚀 Quick Start

1. Setup: cp .env.example .env — add BOT_TOKEN to .env
2. Install: pip install -r requirements.txt
3. Run (test DB): GLADE_DB=data/game_test.db python3 bot.py
4. Run (live DB): python3 bot.py

Bot Manager:
  ./glade.sh start | stop | restart | status | logs
  Logs: /var/log/glade.log

## 📁 Structure

content/      — data (locations, NPCs, monsters, quests, items)
core/         — game logic (player state, maze, i18n, daycycle)
db/           — SQLite layer (players, clans, keys, maps, story)
services/     — business logic (maze runs, survival, daily quests)
handlers/     — Telegram handlers (commands, callbacks)
keyboards/    — inline keyboards
locales/      — translations (en, ru)
tools/        — dev utilities (dump commands, end season)
utils/        — decorators, helpers

## 🎮 Gameplay

Glade:
- 20 locations (center, farms, forge, medbay, huts, gates, etc.)
- 10 NPCs with dialogs and actions
- Work, sleep, eat, craft, trade
- Clans: storage, upgrades, bonuses
- Daily quests, council advice, morning/evening broadcasts

Maze:
- 4 wings (N/S/W/E) + center
- Instant transitions, 10-minute run timer
- Survival: food/water/sanity/energy per move
- Grievers: young/adult/ancient
- Keys: 5 keys with rumor, respawn, wing hint
- Wallshift: walls shift weekly (every 7 days)

PvP:
- Flag-based (opt-in before day 80)
- Mandatory from day 80
- Only in PvP zones (Maze, Center)
- Glade is always safe

Season:
- 90 days
- Morning (06:00) / Evening (22:00) UTC
- Gates close at night
- Gates open: 5 keys + players in center
- Hall of Fame, achievements, leaderboards

## 🌍 Localization

English (en), Russian (ru). All texts via locales/*.json.

## 🐛 Feedback

Found a bug? Have an idea?
Contact: @AdmPenalty

## 📦 Versions

See CHANGELOG.md. Current: v1.2-mvp

## ⚖️ Disclaimer

Fan-made, non-commercial project. Inspired by *The Maze Runner* by James Dashner.
All original characters and story belong to their respective owners.
