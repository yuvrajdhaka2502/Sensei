from __future__ import annotations

import uuid
from typing import Any

from google import genai
from google.genai import types

from .client import LLMResponse, ToolCall


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(
        self,
        history: list[types.Content],
        system_instruction: str,
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=tools)] if tools else None,
        )
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=history,
            config=config,
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        model_content = resp.candidates[0].content if resp.candidates else None
        if model_content and model_content.parts:
            for part in model_content.parts:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    tool_calls.append(
                        ToolCall(
                            name=fc.name,
                            args=dict(fc.args or {}),
                            call_id=getattr(fc, "id", "") or uuid.uuid4().hex[:8],
                        )
                    )

        return LLMResponse(
            text="".join(text_parts).strip(),
            tool_calls=tool_calls,
            raw=model_content,
        )

    def make_user_message(self, text: str) -> types.Content:
        return types.Content(role="user", parts=[types.Part.from_text(text=text)])

    def make_tool_result_message(
        self, results: list[tuple[ToolCall, Any]]
    ) -> types.Content:
        parts = [
            types.Part.from_function_response(name=call.name, response={"result": result})
            for call, result in results
        ]
        return types.Content(role="user", parts=parts)
