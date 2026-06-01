# Sensei — Progress Tracker

## Phase 1 — Local single-user core loop ✅ DONE

| Area | What was built | Status |
|---|---|---|
| **Project scaffold** | `pyproject.toml`, `.env.example`, `.gitignore`, package dirs | ✅ |
| **Config** | `src/sensei/config.py` — pydantic-settings, `Settings`, `get_settings()` | ✅ |
| **Vault I/O** | `src/sensei/vault/io.py` — MD + frontmatter read/write, section editing | ✅ |
| **Vault paths** | `src/sensei/vault/paths.py` — layout helpers (daily/, weekly/, etc.) | ✅ |
| **SQLite cache** | `src/sensei/db/cache.py` — `checkin_state` schema, `init_db()` | ✅ |
| **LLM client** | `src/sensei/llm/gemini.py` — google-genai async, function-call support | ✅ |
| **Tool schemas** | `src/sensei/tools/schemas.py` — Gemini function declarations (P1 set) | ✅ |
| **Read tools** | `src/sensei/tools/read_tools.py` — `get_user_profile`, `get_pending_tasks`, `get_day` | ✅ |
| **Write tools** | `src/sensei/tools/write_tools.py` — `save_morning_plan`, `save_evening_review`, `log_checkin`, `finalize_conversation` with preview/commit split | ✅ |
| **System prompt** | `src/sensei/prompts/system.py` — anti-hallucination contract, tool usage rules | ✅ |
| **Flow prompts** | `src/sensei/prompts/flows.py` — deterministic morning/evening openers | ✅ |
| **Conversation manager** | `src/sensei/conversation/manager.py` — tool loop, preview-before-persist, confirm handling | ✅ |
| **Telegram bot** | `src/sensei/bot.py` — `/start` onboarding (3 Qs), `/morning`, `/evening`, `/forgetme` stub, confirm callbacks | ✅ |
| **Scheduler** | `src/sensei/scheduler.py` — APScheduler cron triggers in user's timezone | ✅ |
| **Entry point** | `src/sensei/main.py` — wires all components, `post_init`/`post_shutdown` hooks | ✅ |

| **`_user_info.md`** | New vault file: who the user is, what they're working toward, challenges | ✅ |
| **`get_user_info` tool** | Read tool — returns `_user_info.md`; read at start of every session | ✅ |
| **`save_user_info` tool** | Write tool (with preview/confirm) — used during onboarding and on-demand | ✅ |
| **Sensei system prompt** | Full rewrite: pattern recognition, honest feedback, Socratic questioning, warm mentor tone | ✅ |
| **Onboarding system prompt** | Separate prompt for intro session — curious, unhurried, pushes for concrete goals | ✅ |
| **LLM-driven intro session** | After 3-question setup, Sensei runs a real getting-to-know-you conversation (4–6 exchanges) then saves `_user_info.md` | ✅ |
| **Pre-session briefing** | Manager pre-loads user_info + pending + yesterday/today into history before first LLM call — no round-trip needed | ✅ |

**P1 is runnable.** To start: copy `.env.example` → `.env`, fill in `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY`, then `pip install -e . && sensei`.

---

## Phase 2 — Snooze ladder, resilience, weekly review, tests ❌ NOT STARTED

| Feature | Description | Status |
|---|---|---|
| **Snooze ladder** | Bot resends at +30min intervals × 3, then "do now / skip?" buttons, then marks `missed` at quiet hours | ❌ |
| **Skip / missed tracking** | `morning: skipped\|missed` in daily frontmatter, properly recorded | ❌ |
| **`/forgetme` fully implemented** | Deletes vault + SQLite + cancels scheduled jobs | ❌ |
| **Weekly review generation** | Sunday morning: deterministic stats pass (completion %, mood avg, streaks), writes `weekly/YYYY-Www.md` | ❌ |
| **Weekly coaching chat** | Short chat after stats file is written; sets next week's focus | ❌ |
| **`get_weekly_review` tool** | Returns cached weekly MD so LLM can reference it | ❌ |
| **`defer_task` tool** | Moves a task to `_pending_tasks.md` with an optional target date | ❌ |
| **Prompt snapshot tests** | `pytest` + `syrupy` snapshots for all prompt templates | ❌ |
| **Tool unit tests** | `tests/test_vault_io.py`, `tests/test_tools.py` against real MD in `tmp_path` | ❌ |
| **E2E happy-path test** | Stub LLM returning scripted tool calls, full morning → evening → file-check | ❌ |
| **Obsidian mtime conflict resolution** | Compare bot's last-write hash (stored in SQLite) against current file mtime before writing | ❌ |
| **`get_analytics` tool** | Named queries: `mood_stats_30d`, `completion_rate_30d`, `streak(habit)`, `recurring_themes_30d` | ❌ |
| **`search_notes` tool** | Keyword search over last 60 days of vault MD (ripgrep subprocess) | ❌ |

---

## Phase 3 — Google Drive sync + Obsidian roundtrip ❌ NOT STARTED

| Feature | Description | Status |
|---|---|---|
| **Google Drive sync** | rclone mount or Drive API — bot writes locally, synced to Drive, Obsidian reads from Drive folder | ❌ |
| **Obsidian edit roundtrip** | Full verify: edit file on phone in Obsidian → bot reads updated frontmatter on next write | ❌ |

---

## Phase 4 — Multi-user + friends ❌ NOT STARTED

| Feature | Description | Status |
|---|---|---|
| **Docker containerization** | `Dockerfile` for the bot process | ❌ |
| **Bot-per-user pattern** | Each friend creates their own bot via BotFather; separate container per person | ❌ |
| **Per-user vault isolation** | Each container has its own `VAULT_PATH` and `DB_PATH` | ❌ |
| **Deploy docs / compose file** | `docker-compose.yml` for running multiple containers | ❌ |

---

## Architecture decisions (locked)

| Decision | Choice |
|---|---|
| LLM memory | None — model has no persistent memory; all context via tools |
| Source of truth | Markdown frontmatter; SQLite is a rebuildable cache |
| LLM interaction | Function-calling (tool-use), not text-in/text-out |
| Write confirmation | Preview shown to user before any disk write; user must tap ✓ |
| Mood/energy scale | 1–3 (low / medium / high) |
| AI notes file | Removed — no subjective AI-written coaching memory |
| Sync (P3) | Google Drive (rclone or API) |
| Multi-user (P4) | Bot-per-user containers; each friend creates their own Telegram bot |
| Project name | **Sensei** |
