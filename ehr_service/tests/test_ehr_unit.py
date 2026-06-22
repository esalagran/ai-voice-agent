from datetime import UTC, date, datetime

import pytest

from ehr_service.database import init_db, make_session_factory
from ehr_service.domain import (
    SLOT_AVAILABLE,
    EHRConflictError,
    EHRNotFoundError,
    EHRValidationError,
    day_bounds,
    normalize_name,
)
from ehr_service.models import AvailabilitySlot
from ehr_service.services import EHRService


def test_normalize_name_collapses_case_and_spaces():
    assert normalize_name("  Grace   Hopper  ") == "grace hopper"


def test_day_bounds_covers_full_utc_date_range():
    assert day_bounds(date(2030, 1, 15), date(2030, 1, 16)) == (
        datetime(2030, 1, 15, tzinfo=UTC),
        datetime(2030, 1, 17, tzinfo=UTC),
    )


def test_day_bounds_rejects_reversed_range():
    with pytest.raises(EHRValidationError):
        day_bounds(date(2030, 1, 16), date(2030, 1, 15))


def test_create_patient_reuses_normalized_match():
    session_factory = make_session_factory("sqlite:///:memory:")
    init_db(session_factory)

    with session_factory() as session:
        service = EHRService(session)
        patient = service.create_patient("Grace Hopper", date(1990, 1, 2), None, None)
        duplicate = service.create_patient("  grace   hopper  ", date(1990, 1, 2), None, None)

    assert duplicate.id == patient.id


def test_create_appointment_rejects_missing_patient():
    session_factory = make_session_factory("sqlite:///:memory:")
    init_db(session_factory)

    with session_factory() as session:
        service = EHRService(session)

        with pytest.raises(EHRNotFoundError, match="patient not found"):
            service.create_appointment(patient_id=999, slot_id=999)


def test_create_appointment_rejects_missing_or_booked_slot():
    session_factory = make_session_factory("sqlite:///:memory:")
    init_db(session_factory)

    with session_factory() as session:
        service = EHRService(session)
        patient = service.create_patient("Grace Hopper", date(1990, 1, 2), None, None)

        with pytest.raises(EHRNotFoundError, match="slot not found"):
            service.create_appointment(patient_id=patient.id, slot_id=999)

        slot = AvailabilitySlot(
            start_at=datetime(2030, 1, 15, 9, tzinfo=UTC),
            end_at=datetime(2030, 1, 15, 9, 30, tzinfo=UTC),
            status=SLOT_AVAILABLE,
        )
        session.add(slot)
        session.commit()

        service.create_appointment(patient_id=patient.id, slot_id=slot.id)

        with pytest.raises(EHRConflictError, match="slot is not available"):
            service.create_appointment(patient_id=patient.id, slot_id=slot.id)


def test_cancel_appointment_releases_slot_and_is_idempotent():
    session_factory = make_session_factory("sqlite:///:memory:")
    init_db(session_factory)

    with session_factory() as session:
        service = EHRService(session)
        patient = service.create_patient("Grace Hopper", date(1990, 1, 2), None, None)
        slot = AvailabilitySlot(
            start_at=datetime(2030, 1, 15, 9, tzinfo=UTC),
            end_at=datetime(2030, 1, 15, 9, 30, tzinfo=UTC),
            status=SLOT_AVAILABLE,
        )
        session.add(slot)
        session.commit()

        appointment = service.create_appointment(patient_id=patient.id, slot_id=slot.id)
        cancelled = service.cancel_appointment(appointment.id)
        cancelled_again = service.cancel_appointment(appointment.id)

    assert cancelled.status == "cancelled"
    assert cancelled_again.id == appointment.id
    assert cancelled.slot.status == "available"


def test_cancel_appointment_rejects_missing_appointment():
    session_factory = make_session_factory("sqlite:///:memory:")
    init_db(session_factory)

    with session_factory() as session:
        service = EHRService(session)

        with pytest.raises(EHRNotFoundError, match="appointment not found"):
            service.cancel_appointment(999)
