# Changelog

All notable changes to The Glade.

## [v1.2-mvp] — 2026-10-17

### Fixed
- command_reply: uses make_bot() (HTML parse_mode) — no visible <b> tags
- cmd_help: uses command_reply (single main message, no duplicate)
- add_score: score floor 0 — deaths no longer drop below zero
- daily_quest: removed duplicate 📋 in header

### Added
- Feedback contact @AdmPenalty in /help → Info and after intro
- glade.sh — bot manager script

### Infrastructure
- GitHub: https://github.com/Damnash/the-glade
- Tags: v0.2-pre-refactor, v1.0-mvp, v1.1-mvp, v1.2-mvp

## [v1.1-mvp] — 2026-10-17

### Added
- Fix 9: NPC quests — bring_meat (Frypan), bring_water (Winston)
- Fix 8: Wallshift — walls shift every 7 days, connectivity preserved
- Fix 7: Keys model — daily spawn, rumor, 1-day lifetime, respawn, broadcast
- Fix 6.4–6.5: PvP flag (/pvp_flag, UI, mandatory day 80+)

## [v1.0-mvp] — 2026-10-16

### Added
- Fix 1: Player state — removed time-based food/water/sanity tick
- Fix 2: Survival — resources spent per maze move
- Fix 3: Maze runs — 10-min timer, instant transitions, BFS depth
- Fix 4: Daycycle — gates close at night, morning/evening broadcasts
- Fix 5: Daily quests + session protection everywhere
- Fix 6: Clan base — storage, 3 upgrades, passive bonuses

### Infrastructure
- WAL mode for SQLite (no more "database is locked")
- edit_main always delete + send
- GLADE_DB env for test DB

## [v0.2-pre-refactor] — 2026-10-16

Snapshot before tech-debt refactor. Baseline for v1 development.
