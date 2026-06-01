from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    call_id: str = ""


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # provider-specific content; appended verbatim to history


class LLMClient(Protocol):
    async def generate(
        self,
        history: list[Any],
        system_instruction: str,
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...

    def make_user_message(self, text: str) -> Any: ...

    def make_tool_result_message(self, results: list[tuple[ToolCall, Any]]) -> Any: ...
