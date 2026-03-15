import json
import uuid
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path("history.json")


def _read() -> list:
    """Read all records from disk."""
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(records: list):
    """Write all records to disk."""
    HISTORY_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def save_result(result: dict, user_id: str) -> dict:
    """Append a completed quiz result linked to a user."""
    records = _read()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": datetime.utcnow().isoformat(),
        **result,
    }
    records.insert(0, record)        # newest first
    _write(records[:200])            # keep max 200 records total
    return record


def load_history(user_id: str) -> list:
    """Return all records for a specific user."""
    return [r for r in _read() if r.get("user_id") == user_id]


def get_record(record_id: str, user_id: str) -> dict | None:
    """Return a single record by ID, only if it belongs to the user."""
    for r in _read():
        if r["id"] == record_id and r.get("user_id") == user_id:
            return r
    return None


def delete_record(record_id: str, user_id: str) -> bool:
    """Delete one record. Returns True if deleted, False if not found."""
    records = _read()
    filtered = [r for r in records if not (r["id"] == record_id and r.get("user_id") == user_id)]
    if len(filtered) == len(records):
        return False
    _write(filtered)
    return True


def clear_history(user_id: str):
    """Delete all records for a user."""
    records = [r for r in _read() if r.get("user_id") != user_id]
    _write(records)