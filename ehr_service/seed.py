from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select

from ehr_service.database import SessionFactory
from ehr_service.domain import SLOT_AVAILABLE, normalize_name
from ehr_service.models import AvailabilitySlot, Patient


def seed_demo_data(session_factory: SessionFactory) -> None:
    with session_factory() as session:
        existing_patient = session.scalar(
            select(Patient).where(
                Patient.normalized_name == normalize_name("Ada Lovelace"),
                Patient.date_of_birth == date(1985, 12, 10),
            )
        )
        if existing_patient is None:
            session.add(
                Patient(
                    name="Ada Lovelace",
                    normalized_name=normalize_name("Ada Lovelace"),
                    date_of_birth=date(1985, 12, 10),
                    phone="+1-555-0100",
                    email="ada@example.com",
                )
            )

        slot_day = date(2030, 1, 15)
        starts = [
            datetime.combine(slot_day, time(hour=9), UTC),
            datetime.combine(slot_day, time(hour=10), UTC),
            datetime.combine(slot_day, time(hour=11), UTC),
            datetime.combine(slot_day, time(hour=14), UTC),
        ]
        for start_at in starts:
            end_at = start_at + timedelta(minutes=30)
            existing_slot = session.scalar(
                select(AvailabilitySlot).where(
                    AvailabilitySlot.start_at == start_at,
                    AvailabilitySlot.end_at == end_at,
                )
            )
            if existing_slot is None:
                session.add(
                    AvailabilitySlot(
                        start_at=start_at,
                        end_at=end_at,
                        status=SLOT_AVAILABLE,
                    )
                )

        session.commit()
