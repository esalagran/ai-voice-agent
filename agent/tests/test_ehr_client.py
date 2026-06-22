import asyncio
from datetime import date
from typing import cast

import httpx
import pytest

from agent.ehr_client import EHRClient, EHRClientError
from ehr_service.rpc import (
    CREATE_APPOINTMENT,
    FIND_PATIENT,
    LIST_AVAILABILITY_SLOTS,
    CreateAppointmentRequest,
    FindPatientRequest,
    ListAvailabilitySlotsRequest,
    PatientResponse,
)


def run(coro):
    return asyncio.run(coro)


def test_ehr_client_calls_find_patient():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rpc/find_patient"
        assert request.method == "POST"
        assert request.read() == b'{"name":"Grace Hopper","date_of_birth":"1990-01-02"}'
        return httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Grace Hopper",
                "date_of_birth": "1990-01-02",
                "phone": None,
                "email": None,
                "created_at": "2026-06-22T21:44:07.837214Z",
            },
        )

    client = EHRClient(
        client=httpx.AsyncClient(base_url="http://ehr", transport=httpx.MockTransport(handler))
    )

    patient = run(
        client.call(
            FIND_PATIENT,
            FindPatientRequest(name="Grace Hopper", date_of_birth=date(1990, 1, 2)),
        )
    )

    assert patient is not None
    assert cast(PatientResponse, patient).id == 1


def test_ehr_client_checks_health():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    client = EHRClient(
        client=httpx.AsyncClient(base_url="http://ehr", transport=httpx.MockTransport(handler))
    )

    run(client.check_health())


def test_ehr_client_maps_http_errors():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(409, json={"detail": "slot is not available"})
    )
    client = EHRClient(client=httpx.AsyncClient(base_url="http://ehr", transport=transport))

    with pytest.raises(EHRClientError) as error:
        run(client.call(CREATE_APPOINTMENT, CreateAppointmentRequest(patient_id=1, slot_id=2)))

    assert error.value.code == "conflict"
    assert error.value.message == "slot is not available"


def test_ehr_client_maps_connection_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = EHRClient(
        client=httpx.AsyncClient(base_url="http://ehr", transport=httpx.MockTransport(handler))
    )

    with pytest.raises(EHRClientError) as error:
        run(
            client.call(
                LIST_AVAILABILITY_SLOTS,
                ListAvailabilitySlotsRequest(from_date=date(2030, 1, 15)),
            )
        )

    assert error.value.code == "ehr_unavailable"
