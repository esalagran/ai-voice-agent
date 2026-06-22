import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast

from pipecat.services.llm_service import FunctionCallParams
from pydantic import BaseModel

from agent.ehr_client import EHRClient, EHRClientError
from agent.ehr_tools import EHRToolset
from ehr_service.rpc import (
    RPC_OPERATIONS,
    AppointmentResponse,
    CancelAppointmentRequest,
    CreateAppointmentRequest,
    CreatePatientRequest,
    FindPatientRequest,
    ListAvailabilitySlotsRequest,
    ListPatientAppointmentsRequest,
    PatientResponse,
    RPCOperation,
    SlotResponse,
)

CREATED_AT = datetime(2026, 6, 22, 21, 44, 7, 837214, UTC)


PATIENT = PatientResponse(
    id=1,
    name="Grace Hopper",
    date_of_birth=date(1990, 1, 2),
    phone=None,
    email=None,
    created_at=CREATED_AT,
)
SLOT = SlotResponse(
    id=10,
    start_at=datetime(2030, 1, 15, 9, tzinfo=UTC),
    end_at=datetime(2030, 1, 15, 9, 30, tzinfo=UTC),
    status="available",
)


class FakeEHRClient:
    async def call(self, operation: RPCOperation, request: BaseModel) -> Any:
        return await getattr(self, operation.name)(request)

    async def find_patient(self, request: FindPatientRequest) -> PatientResponse:
        return PATIENT.model_copy(update={"name": request.name})

    async def create_patient(self, request: CreatePatientRequest) -> PatientResponse:
        return PATIENT.model_copy(update={"id": 2, "name": request.name})

    async def list_availability_slots(
        self, request: ListAvailabilitySlotsRequest
    ) -> list[SlotResponse]:
        return [SLOT]

    async def create_appointment(self, request: CreateAppointmentRequest) -> AppointmentResponse:
        return AppointmentResponse(
            id=20,
            status="booked",
            patient=PATIENT.model_copy(update={"id": request.patient_id}),
            slot=SLOT.model_copy(update={"id": request.slot_id}),
            created_at=CREATED_AT,
            cancelled_at=None,
        )

    async def list_patient_appointments(
        self, request: ListPatientAppointmentsRequest
    ) -> list[AppointmentResponse]:
        return [
            AppointmentResponse(
                id=20,
                status=request.status or "booked",
                patient=PATIENT.model_copy(update={"id": request.patient_id}),
                slot=SLOT,
                created_at=CREATED_AT,
                cancelled_at=None,
            )
        ]

    async def cancel_appointment(self, request: CancelAppointmentRequest) -> AppointmentResponse:
        return AppointmentResponse(
            id=request.appointment_id,
            status="cancelled",
            patient=PATIENT,
            slot=SLOT,
            created_at=CREATED_AT,
            cancelled_at=datetime(2026, 6, 22, 21, 45, 7, 837214, UTC),
        )


class ErrorEHRClient(FakeEHRClient):
    async def call(self, operation: RPCOperation, request: BaseModel) -> Any:
        raise EHRClientError("ehr_unavailable", "EHR service is unavailable")


class NoSlotsEHRClient(FakeEHRClient):
    async def list_availability_slots(
        self, request: ListAvailabilitySlotsRequest
    ) -> list[SlotResponse]:
        return []


class FakeLLM:
    def __init__(self):
        self.handlers = {}

    def register_function(self, name: str, handler) -> None:
        self.handlers[name] = handler


async def call_tool(toolset: EHRToolset, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    llm = FakeLLM()
    toolset.register(cast(Any, llm))
    results = []

    async def callback(result: Any, **kwargs) -> None:
        results.append(result)

    params = FunctionCallParams(
        function_name=name,
        tool_call_id="call-1",
        arguments=arguments,
        llm=cast(Any, None),
        context=cast(Any, None),
        result_callback=callback,
    )
    await llm.handlers[name](params)
    return results[0]


def test_toolset_exposes_expected_tools():
    toolset = EHRToolset(cast(EHRClient, FakeEHRClient()))

    assert [tool.name for tool in toolset.tools.standard_tools] == [
        "find_patient",
        "create_patient",
        "list_availability_slots",
        "create_appointment",
        "list_patient_appointments",
        "cancel_appointment",
    ]


def test_tool_schemas_match_rpc_contracts():
    toolset = EHRToolset(cast(EHRClient, FakeEHRClient()))
    tools_by_name = {tool.name: tool for tool in toolset.tools.standard_tools}

    for operation in RPC_OPERATIONS:
        tool = tools_by_name[operation.name]
        assert tool.properties == operation.request_schema["properties"]
        assert tool.required == operation.request_schema["required"]


def test_tool_handler_returns_success_payload():
    result = asyncio.run(
        call_tool(
            EHRToolset(cast(EHRClient, FakeEHRClient())),
            "find_patient",
            {"name": "Grace Hopper", "date_of_birth": "1990-01-02"},
        )
    )

    assert result == {
        "ok": True,
        "data": PATIENT.model_dump(mode="json"),
    }


def test_tool_handler_explains_empty_availability():
    result = asyncio.run(
        call_tool(
            EHRToolset(cast(EHRClient, NoSlotsEHRClient())),
            "list_availability_slots",
            {"from_date": "2025-09-01", "to_date": "2025-09-30"},
        )
    )

    assert result == {
        "ok": True,
        "data": [],
        "message": "There are no available slots for that date range.",
    }


def test_tool_handler_returns_error_payload():
    result = asyncio.run(
        call_tool(
            EHRToolset(cast(EHRClient, ErrorEHRClient())),
            "find_patient",
            {"name": "Grace Hopper", "date_of_birth": "1990-01-02"},
        )
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "ehr_unavailable"


def test_tool_handler_validates_required_arguments():
    result = asyncio.run(
        call_tool(EHRToolset(cast(EHRClient, FakeEHRClient())), "find_patient", {})
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "validation_error"
