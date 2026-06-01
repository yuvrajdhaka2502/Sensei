from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date as Date, timedelta
from typing import Any, Literal

from ..llm.client import LLMClient, ToolCall
from ..prompts.flows import EVENING_OPENER, INTRO_OPENER, MORNING_OPENER, intro_context, session_context
from ..prompts.system import build_onboarding_instruction, build_system_instruction
from ..tools import read_tools, write_tools
from ..tools.context import ToolContext
from ..tools.schemas import READ_TOOL_NAMES, declarations, onboarding_declarations

log = logging.getLogger(__name__)

Slot = Literal["morning", "evening", "ad_hoc", "intro"]


@dataclass
class PendingTool:
    call: ToolCall
    preview: write_tools.Preview


@dataclass
class OutMsg:
    text: str
    confirm_keyboard: bool = False


@dataclass
class Session:
    slot: Slot
    date: Date
    history: list[Any] = field(default_factory=list)
    pending: PendingTool | None = None
    finalized: bool = False


class ConversationManager:
    def __init__(self, llm: LLMClient, ctx: ToolContext) -> None:
        self.llm = llm
        self.ctx = ctx
        self._tools = declarations()
        self._onboarding_tools = onboarding_declarations()

    def open_session(self, slot: Slot, d: Date, local_time: str) -> tuple[Session, list[OutMsg]]:
        session = Session(slot=slot, date=d)

        if slot == "intro":
            opener_text = INTRO_OPENER
            seed_msg = intro_context()
        elif slot == "morning":
            opener_text = MORNING_OPENER
            seed_msg = session_context(slot, local_time)
        elif slot == "evening":
            opener_text = EVENING_OPENER
            seed_msg = session_context(slot, local_time)
        else:
            opener_text = ""
            seed_msg = session_context("ad_hoc", local_time)

        session.history.append(self.llm.make_user_message(seed_msg))

        # Pre-load key context as a briefing so the LLM has rich context
        # before the user's first reply — no extra round-trip needed for basics.
        if slot != "intro":
            briefing = self._build_briefing(slot, d)
            if briefing:
                session.history.append(self.llm.make_user_message(briefing))

        return session, [OutMsg(text=opener_text)] if opener_text else []

    def _build_briefing(self, slot: Slot, d: Date) -> str:
        """Pre-load user_info + pending + relevant day into session history."""
        parts: list[str] = ["[Pre-session briefing — use this context before responding]\n"]

        user_info = read_tools.get_user_info(self.ctx, {})
        if user_info.get("exists"):
            parts.append("## Who this person is\n" + user_info["body"])

        pending = read_tools.get_pending_tasks(self.ctx, {})
        tasks = pending.get("tasks", [])
        if tasks:
            task_lines = "\n".join(f"- {t}" for t in tasks)
            parts.append(f"## Pending tasks from previous days\n{task_lines}")

        if slot == "morning":
            yesterday = d - timedelta(days=1)
            yesterday_data = read_tools.get_day(self.ctx, {"date": yesterday.isoformat()})
            if yesterday_data.get("exists"):
                fm = yesterday_data.get("frontmatter", {})
                body = yesterday_data.get("body", "")
                parts.append(
                    f"## Yesterday ({yesterday.isoformat()})\n"
                    f"Planned: {fm.get('tasks_planned', '?')}  "
                    f"Completed: {fm.get('tasks_completed', '?')}  "
                    f"Evening mood: {fm.get('mood_evening', '?')}/3\n\n{body}"
                )
        elif slot == "evening":
            today_data = read_tools.get_day(self.ctx, {"date": "today"})
            if today_data.get("exists"):
                parts.append(f"## Today's morning plan\n{today_data.get('body', '')}")

        return "\n\n".join(parts) if len(parts) > 1 else ""

    async def on_user_text(self, session: Session, text: str) -> list[OutMsg]:
        if session.pending is not None:
            session.pending = None
        session.history.append(self.llm.make_user_message(text))
        return await self._run_until_pause(session)

    async def on_confirm(self, session: Session) -> list[OutMsg]:
        if session.pending is None:
            return [OutMsg(text="(nothing pending)")]
        pending = session.pending
        session.pending = None
        commit_fn = write_tools.COMMIT_FNS.get(pending.call.name)
        if commit_fn is None:
            return [OutMsg(text=f"(unknown tool: {pending.call.name})")]
        result = commit_fn(self.ctx, pending.preview.payload)
        log.info("committed %s -> %s", pending.call.name, result)
        session.history.append(
            self.llm.make_user_message(f"[User confirmed. {pending.call.name} saved successfully.]")
        )
        return await self._run_until_pause(session)

    def _tools_for(self, session: Session) -> list[Any]:
        return self._onboarding_tools if session.slot == "intro" else self._tools

    def _system_for(self, session: Session) -> str:
        if session.slot == "intro":
            return build_onboarding_instruction()
        slot_label = session.slot if session.slot != "ad_hoc" else ""
        return build_system_instruction(slot=slot_label)

    async def _run_until_pause(self, session: Session, max_turns: int = 8) -> list[OutMsg]:
        outgoing: list[OutMsg] = []
        for _ in range(max_turns):
            resp = await self.llm.generate(
                history=session.history,
                system_instruction=self._system_for(session),
                tools=self._tools_for(session),
            )
            if resp.raw is not None:
                session.history.append(resp.raw)

            if resp.text:
                outgoing.append(OutMsg(text=resp.text))

            if not resp.tool_calls:
                return outgoing

            tool_results: list[tuple[ToolCall, Any]] = []
            pending_write: ToolCall | None = None

            for tc in resp.tool_calls:
                if tc.name in READ_TOOL_NAMES:
                    handler = read_tools.READ_HANDLERS.get(tc.name)
                    result = handler(self.ctx, tc.args) if handler else {"error": "unknown"}
                    tool_results.append((tc, result))
                elif tc.name in write_tools.AUTO_CONFIRM:
                    result = write_tools.COMMIT_FNS[tc.name](self.ctx, tc.args)
                    tool_results.append((tc, result))
                    if tc.name == "finalize_conversation":
                        session.finalized = True
                elif tc.name in write_tools.COMMIT_FNS:
                    tool_results.append(
                        (tc, {"status": "preview_shown_to_user_for_confirmation"})
                    )
                    if pending_write is None:
                        pending_write = tc
                else:
                    tool_results.append((tc, {"error": f"unknown tool {tc.name}"}))

            if tool_results:
                session.history.append(self.llm.make_tool_result_message(tool_results))

            if pending_write is not None:
                preview = write_tools.PREVIEW_FNS[pending_write.name](pending_write.args)
                session.pending = PendingTool(call=pending_write, preview=preview)
                outgoing.append(OutMsg(text=preview.summary, confirm_keyboard=True))
                return outgoing

            if session.finalized:
                return outgoing

        log.warning("conversation hit max_turns without finalize (slot=%s)", session.slot)
        return outgoing
