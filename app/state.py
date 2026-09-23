from dataclasses import dataclass, field


@dataclass
class ConversationState:
    patient_id: str
    transcript: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    last_interaction_id: str | None = None
