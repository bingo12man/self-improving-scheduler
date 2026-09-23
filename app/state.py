from dataclasses import dataclass, field


@dataclass
class ConversationState:
    patient_id: str
    transcript: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    last_interaction_id: str | None = None
    user_turns: int = 0

    def record_user(self, text: str) -> None:
        self.user_turns += 1
        self.transcript.append({"role": "user", "content": text})

    def record_assistant(self, text: str) -> None:
        self.transcript.append({"role": "assistant", "content": text})

    def record_tool(self, name: str, arguments: dict, result: dict) -> None:
        self.tool_calls.append(
            {
                "turn": self.user_turns,
                "name": name,
                "arguments": arguments,
                "result": result,
            }
        )
