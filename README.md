# The Glade

Text survival game in a living maze. Telegram bot.

A 90-day seasonal roguelike inspired by The Maze Runner. Survive in the Glade. Explore the Maze. Find 5 keys. Open the Gates.

## What is it

- Glade — safe zone: work, sleep, trade, clan life.
- Maze — dangerous: Grievers, shifting walls, 10-minute runs.
- Goal — 5 keys → Gates → escape before day 90.
- Season — 90 days, then reset. New season, new stories.

## Tech Stack

- Python 3.14
- aiogram 3.x
- SQLite (WAL mode)
- ~70 modules, 9 content files

## Quick Start

1. Setup:
   cp .env.example .env
   Add BOT_TOKEN to .env (from @BotFather).

2. Install:
   pip install -r requirements.txt

3. Run (test DB):
   GLADE_DB=data/game_test.db python3 bot.py

4. Run (live DB):
   python3 bot.py

## Bot Manager

Use glade.sh for background management:

- ./glade.sh start    - start in background
- ./glade.sh stop     - stop
- ./glade.sh restart  - restart
- ./glade.sh status   - check status
- ./glade.sh logs     - tail logs (Ctrl+C to exit)

Logs: /var/log/glade.log

## Project Structure

- content/  — data: locations, NPCs, monsters, quests, items, upgrades
- core/     — game logic: player state, maze generator, i18n, daycycle
- db/       — SQLite layer: players, clans, keys, maps, story, achievements
- services/ — business logic: maze runs, survival, daily quests, wallshift
- handlers/ — Telegram handlers: commands, callbacks, UI
- keyboards/— inline keyboard layouts
- locales/  — translations: en.json, ru.json
- tools/    — dev utilities: dump_commands, set_commands, end_season
- utils/    — decorators and helpers

## Gameplay

### Glade

- 20 locations: center, farms, forge, medbay, huts, gates, kitchen, council, watchtower, etc.
- 10 NPCs: Newt, Alby, Minho, Teresa, Frypan, Clint, Jeff, Chuck, Winston, Gally
- Work, sleep, eat, craft, trade
- Clans: shared storage, 3 upgrades (forge, farm, medbay), passive bonuses
- Daily quests (7 types, auto-issue, progress, reward)
- Council advice (morning broadcast)
- Morning/evening notifications

### Maze

- 4 wings (N/S/W/E) + center
- Instant transitions, 10-minute run timer
- Survival: food/water/sanity/energy spent per move
- Grievers: young, adult, ancient
- Keys: 5 keys with daily rumor, 1-day lifetime, respawn, wing hint
- Wallshift: walls shift every 7 days (connectivity preserved)
- Depth via BFS, return cost

### PvP

- Flag-based: opt-in before day 80 (24h flag)
- Mandatory from day 80
- Only in PvP zones (Maze, Center)
- Glade is always safe

### Season

- 90 days
- Morning 06:00 UTC / Evening 22:00 UTC
- Gates close at night (22:00-06:00 UTC)
- Gates open: 5 keys + required players in center
- Hall of Fame, achievements, leaderboards
- Automatic season end + reset

## Localization

- English (en)
- Russian (ru)

All texts via locales/*.json. Add new language by creating locales/xx.json.

## Feedback

Found a bug? Have an idea? Want to suggest something?

Contact: @AdmPenalty

## Versions

See CHANGELOG.md.

Current: v1.2-mvp

## License & Disclaimer

Fan-made, non-commercial project.

Inspired by The Maze Runner series by James Dashner.
All original characters, settings, and story elements belong to their respective owners.

This project is not affiliated with 20th Century Studios or James Dashner.
