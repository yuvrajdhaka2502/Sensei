"""Write tool handlers.

Each write tool is split into a `preview()` (deterministic, runs before user
confirms) and `commit()` (only runs after user confirms via inline keyboard).
The conversation manager uses preview() to render the confirmation message,
and commit() to actually persist on user-tap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..vault import io as vault_io
from .context import ToolContext


@dataclass
class Preview:
    summary: str       # text shown to user above confirm buttons
    payload: dict      # original tool args, used by commit


def _preview_save_morning_plan(args: dict[str, Any]) -> Preview:
    tasks = args.get("tasks") or []
    lines = ["**Saving today's plan:**", ""]
    lines += [f"• {t}" for t in tasks]
    return Preview(summary="\n".join(lines), payload={"tasks": tasks})


def _commit_save_morning_plan(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    tasks = payload.get("tasks") or []
    body_lines = [f"- [ ] {t}" for t in tasks]
    vault_io.set_daily_section(
        ctx.vault_path, ctx.today(), vault_io.DAILY_SECTION_MORNING, "\n".join(body_lines)
    )
    vault_io.update_daily_meta(
        ctx.vault_path, ctx.today(),
        {"morning": "done", "tasks_planned": len(tasks)},
    )
    return {"ok": True, "saved": len(tasks)}


def _preview_save_evening_review(args: dict[str, Any]) -> Preview:
    completed = args.get("completed") or []
    skipped = args.get("skipped") or []
    reflection = (args.get("reflection") or "").strip()
    lines = ["**Saving evening review:**", ""]
    if completed:
        lines.append("Completed:")
        lines += [f"• {t}" for t in completed]
    if skipped:
        lines.append("")
        lines.append("Skipped:")
        lines += [f"• {t}" for t in skipped]
    if reflection:
        lines.append("")
        lines.append(f"_{reflection}_")
    return Preview(
        summary="\n".join(lines),
        payload={"completed": completed, "skipped": skipped, "reflection": reflection},
    )


def _commit_save_evening_review(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    completed = payload.get("completed") or []
    skipped = payload.get("skipped") or []
    reflection = payload.get("reflection") or ""

    section_lines: list[str] = []
    for t in completed:
        section_lines.append(f"- [x] {t}")
    for t in skipped:
        section_lines.append(f"- [ ] ~~{t}~~ (skipped)")
    if reflection:
        section_lines.append("")
        section_lines.append("**Reflection**")
        section_lines.append(reflection)

    vault_io.set_daily_section(
        ctx.vault_path, ctx.today(), vault_io.DAILY_SECTION_EVENING, "\n".join(section_lines)
    )
    vault_io.update_daily_meta(
        ctx.vault_path, ctx.today(),
        {
            "evening": "done",
            "tasks_completed": len(completed),
            "tasks_skipped": len(skipped),
        },
    )

    pending = vault_io.read_pending_tasks(ctx.vault_path)
    pending = [p for p in pending if p not in completed and p not in skipped]
    vault_io.write_pending_tasks(ctx.vault_path, pending)

    return {"ok": True, "completed": len(completed), "skipped": len(skipped)}


def _preview_log_checkin(args: dict[str, Any]) -> Preview:
    slot = args.get("slot")
    mood = args.get("mood")
    energy = args.get("energy")
    summary = f"**Logging {slot} check-in:** mood={mood}/3, energy={energy}/3"
    return Preview(summary=summary, payload={"slot": slot, "mood": mood, "energy": energy})


def _commit_log_checkin(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    slot = payload.get("slot")
    mood = payload.get("mood")
    energy = payload.get("energy")
    if slot not in ("morning", "evening"):
        return {"ok": False, "error": "invalid slot"}
    fields = {f"mood_{slot}": mood, f"energy_{slot}": energy}
    vault_io.update_daily_meta(ctx.vault_path, ctx.today(), fields)
    return {"ok": True}


def _preview_finalize_conversation(args: dict[str, Any]) -> Preview:
    return Preview(summary="", payload={})


def _commit_finalize_conversation(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "finalized": True}


def _preview_save_user_info(args: dict[str, Any]) -> Preview:
    content = args.get("content", "").strip()
    preview_lines = content.splitlines()[:8]
    snippet = "\n".join(preview_lines)
    if len(content.splitlines()) > 8:
        snippet += "\n…"
    return Preview(
        summary=f"**Saving your profile to `_user_info.md`:**\n\n{snippet}",
        payload={"content": content},
    )


def _commit_save_user_info(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    content = payload.get("content", "")
    vault_io.write_user_info(ctx.vault_path, content)
    return {"ok": True}


PREVIEW_FNS = {
    "save_morning_plan": _preview_save_morning_plan,
    "save_evening_review": _preview_save_evening_review,
    "save_user_info": _preview_save_user_info,
    "log_checkin": _preview_log_checkin,
    "finalize_conversation": _preview_finalize_conversation,
}

COMMIT_FNS = {
    "save_morning_plan": _commit_save_morning_plan,
    "save_evening_review": _commit_save_evening_review,
    "save_user_info": _commit_save_user_info,
    "log_checkin": _commit_log_checkin,
    "finalize_conversation": _commit_finalize_conversation,
}

# Tools that don't need a user-visible preview confirmation (auto-confirmed).
AUTO_CONFIRM = {"finalize_conversation"}
