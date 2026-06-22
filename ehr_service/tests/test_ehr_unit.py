from datetime import UTC, date, datetime

import pytest

from ehr_service.database import init_db, make_session_factory
from ehr_service.domain import EHRValidationError, day_bounds, normalize_name
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
