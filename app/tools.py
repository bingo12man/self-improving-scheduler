from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class ClinicStore:
    def __init__(self, seed_path: str = "data/clinic_seed.json"):
        self.seed_path = Path(seed_path)
        self.reset()

    def reset(self) -> None:
        self.data = json.loads(self.seed_path.read_text())

    def get_available_slots(self, specialty: str, date: str | None = None) -> dict:
        doctors = {
            d["id"]: d for d in self.data["doctors"]
            if d["specialty"].lower() == specialty.lower()
        }
        slots = []
        for slot in self.data["slots"]:
            if slot["doctor_id"] not in doctors or not slot["available"]:
                continue
            if date and slot["date"] != date:
                continue
            slots.append({**deepcopy(slot), "doctor_name": doctors[slot["doctor_id"]]["name"]})
        return {"ok": True, "slots": slots}

    def get_patient_appointments(self, patient_id: str) -> dict:
        rows = [a for a in self.data["appointments"] if a["patient_id"] == patient_id and a["status"] == "booked"]
        return {"ok": True, "appointments": deepcopy(rows)}

    def book_appointment(self, patient_id: str, slot_id: str) -> dict:
        slot = next((s for s in self.data["slots"] if s["slot_id"] == slot_id), None)
        if not slot:
            return {"ok": False, "error": "slot_not_found"}
        if not slot["available"]:
            return {"ok": False, "error": "slot_unavailable"}
        duplicate = next(
            (a for a in self.data["appointments"]
             if a["patient_id"] == patient_id and a["slot_id"] == slot_id and a["status"] == "booked"),
            None,
        )
        if duplicate:
            return {"ok": False, "error": "duplicate_booking", "appointment_id": duplicate["appointment_id"]}

        appt_id = f"appt_{len(self.data['appointments']) + 1}"
        appointment = {
            "appointment_id": appt_id,
            "patient_id": patient_id,
            "slot_id": slot_id,
            "doctor_id": slot["doctor_id"],
            "date": slot["date"],
            "time": slot["time"],
            "status": "booked",
        }
        self.data["appointments"].append(appointment)
        slot["available"] = False
        return {"ok": True, "appointment": deepcopy(appointment)}

    def cancel_appointment(self, patient_id: str, appointment_id: str) -> dict:
        appt = next(
            (a for a in self.data["appointments"] if a["appointment_id"] == appointment_id and a["patient_id"] == patient_id),
            None,
        )
        if not appt:
            return {"ok": False, "error": "appointment_not_found"}
        if appt["status"] != "booked":
            return {"ok": False, "error": "appointment_not_active"}
        appt["status"] = "cancelled"
        slot = next((s for s in self.data["slots"] if s["slot_id"] == appt["slot_id"]), None)
        if slot:
            slot["available"] = True
        return {"ok": True, "appointment": deepcopy(appt)}

    def reschedule_appointment(self, patient_id: str, appointment_id: str, new_slot_id: str) -> dict:
        old = next(
            (a for a in self.data["appointments"] if a["appointment_id"] == appointment_id and a["patient_id"] == patient_id),
            None,
        )
        if not old or old["status"] != "booked":
            return {"ok": False, "error": "appointment_not_found_or_inactive"}

        new_slot = next((s for s in self.data["slots"] if s["slot_id"] == new_slot_id), None)
        if not new_slot or not new_slot["available"]:
            return {"ok": False, "error": "new_slot_unavailable"}

        old_slot = next((s for s in self.data["slots"] if s["slot_id"] == old["slot_id"]), None)
        if old_slot:
            old_slot["available"] = True

        new_slot["available"] = False
        old.update({
            "slot_id": new_slot_id,
            "doctor_id": new_slot["doctor_id"],
            "date": new_slot["date"],
            "time": new_slot["time"],
        })
        return {"ok": True, "appointment": deepcopy(old)}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "get_available_slots",
        "description": "List currently available appointment slots for a medical specialty, optionally on a specific date.",
        "parameters": {
            "type": "object",
            "properties": {
                "specialty": {"type": "string"},
                "date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD or null"},
            },
            "required": ["specialty", "date"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "book_appointment",
        "description": "Book an available slot for the current patient.",
        "parameters": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_patient_appointments",
        "description": "Return the current patient's active appointments.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "cancel_appointment",
        "description": "Cancel one of the current patient's appointments after explicit confirmation.",
        "parameters": {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}},
            "required": ["appointment_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "reschedule_appointment",
        "description": "Move an existing appointment to a new available slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string"},
                "new_slot_id": {"type": "string"},
            },
            "required": ["appointment_id", "new_slot_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def call_tool(store: ClinicStore, patient_id: str, name: str, args: dict[str, Any]) -> dict:
    if name == "get_available_slots":
        return store.get_available_slots(**args)
    if name == "book_appointment":
        return store.book_appointment(patient_id=patient_id, **args)
    if name == "get_patient_appointments":
        return store.get_patient_appointments(patient_id=patient_id)
    if name == "cancel_appointment":
        return store.cancel_appointment(patient_id=patient_id, **args)
    if name == "reschedule_appointment":
        return store.reschedule_appointment(patient_id=patient_id, **args)
    return {"ok": False, "error": f"unknown_tool:{name}"}
