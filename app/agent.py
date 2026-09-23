from __future__ import annotations

import json

from app.llm import GeminiProvider, LLMProvider, ModelTurn
from app.prompts import build_system_prompt
from app.state import ConversationState
from app.tools import ClinicStore, TOOL_SCHEMAS, call_tool


class SchedulingAgent:
    def __init__(
        self,
        patient_id: str,
        store: ClinicStore | None = None,
        provider: LLMProvider | None = None,
    ):
        self.provider = provider or GeminiProvider()
        self.store = store or ClinicStore()
        self.state = ConversationState(patient_id=patient_id)
        self.system_prompt = build_system_prompt()

    def _first_or_continued_user_turn(self, user_text: str) -> ModelTurn:
        if self.state.last_interaction_id:
            return self.provider.continue_with_user(
                previous_interaction_id=self.state.last_interaction_id,
                user_text=user_text,
                tools=TOOL_SCHEMAS,
            )
        return self.provider.start(
            system_prompt=self.system_prompt,
            user_text=user_text,
            tools=TOOL_SCHEMAS,
        )

    def send(self, user_text: str) -> str:
        self.state.transcript.append({"role": "user", "content": user_text})
        turn = self._first_or_continued_user_turn(user_text)

        for _ in range(6):
            if not turn.interaction_id:
                raise RuntimeError("Model provider returned no interaction id")
            self.state.last_interaction_id = turn.interaction_id

            if not turn.tool_requests:
                text = turn.text.strip()
                self.state.transcript.append({"role": "assistant", "content": text})
                return text

            tool_results = []
            for request in turn.tool_requests:
                result = call_tool(
                    self.store,
                    self.state.patient_id,
                    request.name,
                    request.arguments,
                )
                self.state.tool_calls.append(
                    {
                        "name": request.name,
                        "arguments": request.arguments,
                        "result": result,
                    }
                )
                tool_results.append(
                    {
                        "call_id": request.call_id,
                        "name": request.name,
                        "result_json": json.dumps(result),
                    }
                )

            turn = self.provider.continue_with_tools(
                previous_interaction_id=self.state.last_interaction_id,
                tool_results=tool_results,
                tools=TOOL_SCHEMAS,
            )

        raise RuntimeError("Agent exceeded tool-call loop limit")
