from __future__ import annotations

from app.state import ConversationState


MUTATION_SUCCESS_WORDS = {
    "book_appointment": ("booked", "confirmed"),
    "cancel_appointment": ("cancelled", "canceled"),
    "reschedule_appointment": ("rescheduled", "moved"),
}


def boundary_response(user_text: str) -> str | None:
    text = user_text.lower()
    injection_markers = (
        "ignore previous instructions",
        "ignore your instructions",
        "reveal system prompt",
        "show system prompt",
        "developer message",
    )
    if any(marker in text for marker in injection_markers):
        return "I can only help with clinic appointment scheduling. I can show availability, book, reschedule, cancel, or list appointments."

    medical_markers = (
        "diagnose",
        "what medicine",
        "which medicine",
        "what medication",
        "prescribe",
        "what is this rash",
        "what treatment",
    )
    scheduling_markers = ("book", "appointment", "schedule", "reschedule", "cancel", "availability", "slot")
    if any(marker in text for marker in medical_markers) and not any(marker in text for marker in scheduling_markers):
        return "I can’t diagnose conditions or recommend treatment. I can help you schedule an appointment with an appropriate clinician."
    return None


def authorize_tool(state: ConversationState, name: str, arguments: dict) -> tuple[bool, dict | None]:
    if name == "book_appointment":
        slot_id = arguments.get("slot_id")
        if slot_id not in state.offered_slot_ids():
            return False, {"ok": False, "error": "slot_not_verified", "slot_id": slot_id}

    if name == "reschedule_appointment":
        slot_id = arguments.get("new_slot_id")
        if slot_id not in state.offered_slot_ids():
            return False, {"ok": False, "error": "slot_not_verified", "slot_id": slot_id}

    if name == "cancel_appointment":
        appointment_id = arguments.get("appointment_id")
        expected = {"action": "cancel_appointment", "appointment_id": appointment_id}
        if state.confirmed_action != expected:
            state.pending_confirmation = expected
            return False, {
                "ok": False,
                "error": "confirmation_required",
                "appointment_id": appointment_id,
                "message": "Ask the patient to explicitly confirm this cancellation before retrying.",
            }
        state.pending_confirmation = None
        state.confirmed_action = None

    return True, None


def safe_assistant_text(text: str, state: ConversationState) -> str:
    if not state.tool_calls:
        return text

    last_call = state.tool_calls[-1]
    if last_call["turn"] != state.user_turns:
        return text
    if last_call["result"].get("ok", False):
        return text

    lowered = text.lower()
    success_words = MUTATION_SUCCESS_WORDS.get(last_call["name"], ())
    if success_words and any(word in lowered for word in success_words):
        error = last_call["result"].get("error", "tool_failure")
        if error == "confirmation_required":
            appointment_id = last_call["arguments"].get("appointment_id", "that appointment")
            return f"Before I cancel {appointment_id}, please explicitly confirm by replying ‘yes’ or ‘confirm’."
        if error == "slot_not_verified":
            return "I can’t complete that change because the requested slot was not verified from current clinic availability. I can check available slots first."
        return "I couldn’t complete that scheduling change because the clinic tool returned an error. No successful change was made."
    return text
