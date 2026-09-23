from app.tools import ClinicStore


def test_booking_changes_slot_availability():
    store = ClinicStore()
    result = store.book_appointment("p1", "slot_d2")
    assert result["ok"] is True
    slots = store.get_available_slots("dermatology", "2026-09-25")["slots"]
    assert "slot_d2" not in {s["slot_id"] for s in slots}


def test_duplicate_booking_rejected():
    store = ClinicStore()
    store.book_appointment("p1", "slot_d2")
    result = store.book_appointment("p1", "slot_d2")
    assert result["ok"] is False
