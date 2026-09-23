from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolRequest:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelTurn:
    text: str = ""
    tool_requests: list[ToolRequest] = field(default_factory=list)
    interaction_id: str | None = None


class LLMProvider(Protocol):
    def start(self, *, system_prompt: str, user_text: str, tools: list[dict[str, Any]]) -> ModelTurn:
        ...

    def continue_with_tools(
        self,
        *,
        previous_interaction_id: str,
        tool_results: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        ...

    def continue_with_user(
        self,
        *,
        previous_interaction_id: str,
        user_text: str,
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        ...


class GeminiProvider:
    """Thin adapter over Gemini's Interactions API.

    Keeping the provider behind this interface makes the scheduling domain and
    evaluation harness independent from any one model vendor.
    """

    def __init__(self, model: str | None = None):
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - setup error path
            raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc

        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    @staticmethod
    def _to_turn(interaction: Any) -> ModelTurn:
        calls: list[ToolRequest] = []
        for step in getattr(interaction, "steps", []) or []:
            if getattr(step, "type", None) == "function_call":
                calls.append(
                    ToolRequest(
                        call_id=str(step.id),
                        name=step.name,
                        arguments=dict(step.arguments or {}),
                    )
                )

        return ModelTurn(
            text=(getattr(interaction, "output_text", "") or "").strip(),
            tool_requests=calls,
            interaction_id=str(interaction.id),
        )

    def start(self, *, system_prompt: str, user_text: str, tools: list[dict[str, Any]]) -> ModelTurn:
        interaction = self.client.interactions.create(
            model=self.model,
            system_instruction=system_prompt,
            input=user_text,
            tools=tools,
        )
        return self._to_turn(interaction)

    def continue_with_user(
        self,
        *,
        previous_interaction_id: str,
        user_text: str,
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        interaction = self.client.interactions.create(
            model=self.model,
            previous_interaction_id=previous_interaction_id,
            input=user_text,
            tools=tools,
        )
        return self._to_turn(interaction)

    def continue_with_tools(
        self,
        *,
        previous_interaction_id: str,
        tool_results: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        interaction = self.client.interactions.create(
            model=self.model,
            previous_interaction_id=previous_interaction_id,
            tools=tools,
            input=[
                {
                    "type": "function_result",
                    "name": item["name"],
                    "call_id": item["call_id"],
                    "result": [{"type": "text", "text": item["result_json"]}],
                }
                for item in tool_results
            ],
        )
        return self._to_turn(interaction)
