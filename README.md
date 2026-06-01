# Sensei

An AI accountability companion that runs as a Telegram bot — checking in with you every morning and evening, remembering your goals, and tracking your progress in plain markdown files you can read in Obsidian.

## How it works

Sensei messages you twice a day. In the morning it helps you plan; in the evening it reviews what happened. After each conversation it writes a structured markdown file — your entire history lives in your vault, not inside any AI's memory. The bot is stateless between sessions: it reads the files, reasons over them, and writes back. No hallucinations from stale context.

```
Morning check-in  →  "What are you working on today?"
                  →  Saves plan to vault/daily/YYYY-MM-DD.md

Evening check-in  →  "You planned 4 things. What happened?"
                  →  Updates the same file, carries over incomplete tasks
```

All vault files are Obsidian-compatible markdown with YAML frontmatter.

## Features

- **Structured check-ins** — morning planning + evening review via Telegram
- **Persistent vault** — one markdown file per day, plus a user profile and pending-tasks file; Obsidian-ready
- **Anti-hallucination design** — LLM has no memory of its own; every claim traces to a file
- **Preview before write** — the bot shows you what it's about to save and asks you to confirm before touching any file
- **Tool-calling architecture** — Gemini uses function calls to read/write vault files; no text-parsing fragility
- **Timezone-aware scheduler** — check-ins fire at your local time; configure per user
- **Onboarding + intro session** — `/start` walks you through setup, then Sensei runs a getting-to-know-you conversation before your first check-in
- **Completely free to run** — Gemini 2.0 Flash free tier handles ~30,000 tokens/day (2 check-ins uses ~3%)

## Prerequisites

- Python 3.11+
- A Telegram bot token — create one via [@BotFather](https://t.me/BotFather)
- A Gemini API key — get one at [Google AI Studio](https://aistudio.google.com/apikey) (free)

## Setup

```bash
git clone https://github.com/your-username/sensei.git
cd sensei
cp .env.example .env
```

Edit `.env` with your credentials:

```env
TELEGRAM_BOT_TOKEN=your_token_here
GEMINI_API_KEY=your_key_here
VAULT_PATH=./vault          # where markdown files are written
TIMEZONE=Asia/Kolkata       # your local timezone
```

Install and run:

```bash
pip install -e .
sensei
```

## Telegram commands

| Command | What it does |
|---------|-------------|
| `/start` | First-time setup (name, timezone, check-in times) → intro session |
| `/morning` | Manually start a morning check-in |
| `/evening` | Manually start an evening check-in |

After setup, check-ins also fire automatically at your configured times.

## Vault structure

```
vault/
├── _user_profile.md        # your name, timezone, check-in schedule
├── _user_info.md           # goals and context Sensei learns during onboarding
├── _pending_tasks.md       # tasks carried over from previous days
├── daily/
│   ├── 2026-06-01.md       # morning plan + evening review
│   └── ...
└── weekly/                 # (Phase 2) weekly review summaries
```

Each daily file has YAML frontmatter (`mood`, `energy`, `tasks_planned`, `tasks_completed`) so you can query across days in Obsidian's Dataview plugin.

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Required. From BotFather. |
| `GEMINI_API_KEY` | — | Required. From Google AI Studio. |
| `VAULT_PATH` | `./vault` | Where markdown files are written |
| `DB_PATH` | `./state.sqlite` | SQLite file for scheduler state |
| `TIMEZONE` | `Asia/Kolkata` | Default timezone (overridden per user during onboarding) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Telegram | `python-telegram-bot` |
| LLM | Google Gemini 2.0 Flash (`google-genai`) |
| Scheduler | APScheduler |
| Database | SQLite (`aiosqlite` + `sqlalchemy`) |
| Config | `pydantic-settings` |
| Vault | Plain markdown + YAML frontmatter (`python-frontmatter`) |

## Roadmap

- **Phase 1** (done) — Single-user core loop: onboarding, morning/evening check-ins, vault I/O, scheduler
- **Phase 2** — Snooze ladder, skip/missed tracking, weekly reviews, `/forgetme`, test suite
- **Phase 3** — Google Drive sync for Obsidian on mobile
- **Phase 4** — Multi-user via Docker (one container per friend, each with their own bot token)

## License

MIT
