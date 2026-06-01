from __future__ import annotations

from datetime import date as Date, timedelta
from typing import Any

from ..vault import io as vault_io
from .context import ToolContext


def _parse_date(s: str, today: Date) -> Date:
    s = s.strip().lower()
    if s == "today":
        return today
    if s == "yesterday":
        return today - timedelta(days=1)
    return Date.fromisoformat(s)


def get_user_profile(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    doc = vault_io.read_profile(ctx.vault_path)
    if not doc.metadata and not doc.body:
        return {"exists": False}
    return {"exists": True, "frontmatter": doc.metadata, "body": doc.body}


def get_user_info(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    doc = vault_io.read_user_info(ctx.vault_path)
    if not doc.body.strip():
        return {"exists": False, "note": "user has not completed their intro yet"}
    return {"exists": True, "body": doc.body}


def get_pending_tasks(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return {"tasks": vault_io.read_pending_tasks(ctx.vault_path)}


def get_day(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    date_str = args.get("date", "today")
    try:
        d = _parse_date(date_str, ctx.today())
    except ValueError:
        return {"error": f"invalid date: {date_str!r}"}
    doc = vault_io.read_daily(ctx.vault_path, d)
    if not doc.metadata and not doc.body:
        return {"date": d.isoformat(), "exists": False}
    return {
        "date": d.isoformat(),
        "exists": True,
        "frontmatter": doc.metadata,
        "body": doc.body,
    }


READ_HANDLERS = {
    "get_user_profile": get_user_profile,
    "get_user_info": get_user_info,
    "get_pending_tasks": get_pending_tasks,
    "get_day": get_day,
}
