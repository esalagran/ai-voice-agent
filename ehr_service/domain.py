from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

SLOT_AVAILABLE = "available"
SLOT_BOOKED = "booked"
APPOINTMENT_BOOKED = "booked"
APPOINTMENT_CANCELLED = "cancelled"


class EHRNotFoundError(Exception):
    pass


class EHRConflictError(Exception):
    pass


class EHRValidationError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def day_bounds(from_date: date, to_date: date | None) -> tuple[datetime, datetime]:
    end_date = to_date or from_date
    if end_date < from_date:
        raise EHRValidationError("to_date must be on or after from_date")

    start_at = datetime.combine(from_date, time.min, UTC)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min, UTC)
    return start_at, end_at
