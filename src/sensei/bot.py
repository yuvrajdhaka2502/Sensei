from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings
from .conversation.manager import ConversationManager, OutMsg, Session
from .vault import io as vault_io

log = logging.getLogger(__name__)


CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✓ Confirm", callback_data="confirm"),
      InlineKeyboardButton("✏️ Reword", callback_data="cancel")]]
)


def _kb_for(msg: OutMsg) -> InlineKeyboardMarkup | None:
    return CONFIRM_KEYBOARD if msg.confirm_keyboard else None


def _today_for(settings: Settings) -> tuple[str, str]:
    now = datetime.now(ZoneInfo(settings.timezone))
    return now.date().isoformat(), now.strftime("%H:%M")


# ---------- handlers ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if vault_io.profile_exists(settings.vault_path):
        await update.message.reply_text(
            "You're already set up. I'll see you at your next check-in. "
            "Use /morning or /evening to start one now."
        )
        return
    context.chat_data["onboarding_step"] = "name"
    context.chat_data["onboarding_chat_id"] = update.effective_chat.id
    await update.message.reply_text(
        "Hi! Let's get you set up — 3 quick questions.\n\nWhat should I call you?"
    )


async def _continue_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    step = context.chat_data.get("onboarding_step")
    if not step:
        return False

    settings: Settings = context.bot_data["settings"]
    text = (update.message.text or "").strip()

    if step == "name":
        context.chat_data["onboarding_name"] = text
        context.chat_data["onboarding_step"] = "timezone"
        await update.message.reply_text(
            f"Nice to meet you, {text}.\n\n"
            f"What's your timezone? (e.g. `Asia/Kolkata`, `Europe/London`). "
            f"Default is `{settings.timezone}` — reply with `default` to accept.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if step == "timezone":
        tz = settings.timezone if text.lower() == "default" else text
        try:
            ZoneInfo(tz)
        except Exception:
            await update.message.reply_text("That timezone didn't parse — try again (e.g. `Asia/Kolkata`).")
            return True
        context.chat_data["onboarding_tz"] = tz
        context.chat_data["onboarding_step"] = "times"
        await update.message.reply_text(
            "What times should I check in? Reply with two times like `07:00 22:00` "
            "(morning then evening, 24h)."
        )
        return True

    if step == "times":
        parts = text.split()
        if len(parts) != 2 or not all(":" in p for p in parts):
            await update.message.reply_text("Send two times like `07:00 22:00`.")
            return True
        morning, evening = parts
        tz = context.chat_data["onboarding_tz"]
        vault_io.write_profile(
            settings.vault_path,
            metadata={
                "name": context.chat_data["onboarding_name"],
                "timezone": tz,
                "morning_checkin": morning,
                "evening_checkin": evening,
                "telegram_chat_id": context.chat_data["onboarding_chat_id"],
            },
        )
        for key in ("onboarding_step", "onboarding_name", "onboarding_tz", "onboarding_chat_id"):
            context.chat_data.pop(key, None)

        scheduler_install = context.bot_data.get("scheduler_install")
        if scheduler_install is not None:
            await scheduler_install(morning, evening, tz)

        await update.message.reply_text(
            f"Got it — I'll check in at {morning} and {evening}.\n\n"
            "One more thing before we start the daily routine."
        )

        # Kick off the intro session so Sensei learns who the user is.
        manager: ConversationManager = context.bot_data["manager"]
        today_iso, local_time = _today_for(settings)
        from datetime import date as Date
        intro_session, intro_msgs = manager.open_session("intro", Date.fromisoformat(today_iso), local_time)
        context.chat_data["session"] = intro_session
        await _send(update, intro_msgs)
        return True

    return False


async def _send(update: Update, msgs: list[OutMsg]) -> None:
    for m in msgs:
        if not m.text:
            continue
        kb = _kb_for(m)
        if update.message:
            await update.message.reply_text(m.text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.message.reply_text(m.text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


def _check_authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings: Settings = context.bot_data["settings"]
    profile = vault_io.read_profile(settings.vault_path)
    allowed = profile.metadata.get("telegram_chat_id")
    if allowed is None:
        return True  # onboarding hasn't bound a chat yet
    return update.effective_chat.id == allowed


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_authorized(update, context):
        return
    if await _continue_onboarding(update, context):
        return

    settings: Settings = context.bot_data["settings"]
    if not vault_io.profile_exists(settings.vault_path):
        await update.message.reply_text("Run /start first to set up.")
        return

    manager: ConversationManager = context.bot_data["manager"]
    session: Session | None = context.chat_data.get("session")
    if session is None:
        today_iso, local_time = _today_for(settings)
        from datetime import date as Date
        session, opener_msgs = manager.open_session("ad_hoc", Date.fromisoformat(today_iso), local_time)
        context.chat_data["session"] = session
        # don't send opener for ad-hoc; just process user text below

    msgs = await manager.on_user_text(session, update.message.text or "")
    await _send(update, msgs)
    if session.finalized:
        context.chat_data.pop("session", None)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_authorized(update, context):
        return
    query = update.callback_query
    await query.answer()
    manager: ConversationManager = context.bot_data["manager"]
    session: Session | None = context.chat_data.get("session")
    if session is None:
        await query.message.reply_text("(no active session)")
        return

    if query.data == "confirm":
        msgs = await manager.on_confirm(session)
        await _send(update, msgs)
        if session.finalized:
            context.chat_data.pop("session", None)
    elif query.data == "cancel":
        session.pending = None
        await query.message.reply_text("OK — tell me what to change.")


async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manual trigger — useful for testing without waiting for the scheduler."""
    await _open_scheduled(update, context, "morning")


async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_scheduled(update, context, "evening")


async def _open_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE, slot: str) -> None:
    if not _check_authorized(update, context):
        return
    settings: Settings = context.bot_data["settings"]
    if not vault_io.profile_exists(settings.vault_path):
        await update.message.reply_text("Run /start first.")
        return
    manager: ConversationManager = context.bot_data["manager"]
    today_iso, local_time = _today_for(settings)
    from datetime import date as Date
    session, opener_msgs = manager.open_session(slot, Date.fromisoformat(today_iso), local_time)  # type: ignore[arg-type]
    context.chat_data["session"] = session
    await _send(update, opener_msgs)


async def cmd_forgetme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # P2 stub — currently informational.
    await update.message.reply_text("`/forgetme` is not implemented in this build (P2).")


def build_application(
    settings: Settings,
    manager: ConversationManager,
    post_init=None,
    post_shutdown=None,
) -> Application:
    builder = Application.builder().token(settings.telegram_bot_token)
    if post_init is not None:
        builder = builder.post_init(post_init)
    if post_shutdown is not None:
        builder = builder.post_shutdown(post_shutdown)
    app = builder.build()
    app.bot_data["settings"] = settings
    app.bot_data["manager"] = manager

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("morning", cmd_morning))
    app.add_handler(CommandHandler("evening", cmd_evening))
    app.add_handler(CommandHandler("forgetme", cmd_forgetme))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


async def send_scheduled_opener(app: Application, slot: str) -> None:
    """Called by the scheduler when a check-in fires."""
    settings: Settings = app.bot_data["settings"]
    profile = vault_io.read_profile(settings.vault_path)
    chat_id = profile.metadata.get("telegram_chat_id")
    if chat_id is None:
        log.warning("scheduled %s fired but no telegram_chat_id in profile", slot)
        return
    manager: ConversationManager = app.bot_data["manager"]
    today_iso, local_time = _today_for(settings)
    from datetime import date as Date
    session, msgs = manager.open_session(slot, Date.fromisoformat(today_iso), local_time)  # type: ignore[arg-type]
    chat_data = app.chat_data.setdefault(chat_id, {})
    chat_data["session"] = session
    for m in msgs:
        if not m.text:
            continue
        kb = _kb_for(m)
        await app.bot.send_message(chat_id=chat_id, text=m.text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
