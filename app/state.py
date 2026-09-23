from dataclasses import dataclass, field


@dataclass
class ConversationState:
    patient_id: str
    transcript: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    last_interaction_id: str | None = None
    user_turns: int = 0
    pending_confirmation: dict | None = None
    confirmed_action: dict | None = None

    def record_user(self, text: str) -> None:
        self.user_turns += 1
        self.transcript.append({"role": "user", "content": text})
        self.confirmed_action = None
        if self.pending_confirmation and text.strip().lower() in {
            "yes", "yes please", "confirm", "confirmed", "go ahead", "do it"
        }:
            self.confirmed_action = dict(self.pending_confirmation)

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

    def offered_slot_ids(self) -> set[str]:
        slots: set[str] = set()
        for call in self.tool_calls:
            if call["name"] != "get_available_slots" or not call["result"].get("ok"):
                continue
            for slot in call["result"].get("slots", []):
                if slot.get("slot_id"):
                    slots.add(slot["slot_id"])
        return slots
