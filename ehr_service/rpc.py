from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ehr_service.domain import APPOINTMENT_BOOKED


class CreatePatientRequest(BaseModel):
    name: str = Field(min_length=1)
    date_of_birth: date
    phone: str | None = None
    email: str | None = None


class FindPatientRequest(BaseModel):
    name: str = Field(min_length=1)
    date_of_birth: date


class ListAvailabilitySlotsRequest(BaseModel):
    from_date: date
    to_date: date | None = None


class CreateAppointmentRequest(BaseModel):
    patient_id: int
    slot_id: int


class ListPatientAppointmentsRequest(BaseModel):
    patient_id: int
    status: str | None = APPOINTMENT_BOOKED


class CancelAppointmentRequest(BaseModel):
    appointment_id: int


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    phone: str | None
    email: str | None
    created_at: datetime


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_at: datetime
    end_at: datetime
    status: str


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    patient: PatientResponse
    slot: SlotResponse
    created_at: datetime
    cancelled_at: datetime | None


@dataclass(frozen=True)
class RPCOperation:
    name: str
    description: str
    request_model: type[BaseModel]
    response_model: type[BaseModel]
    returns_list: bool = False
    returns_none: bool = False

    @property
    def path(self) -> str:
        return f"/rpc/{self.name}"

    @property
    def request_schema(self) -> dict[str, Any]:
        schema = self.request_model.model_json_schema()
        return {
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }


FIND_PATIENT = RPCOperation(
    name="find_patient",
    description="Find an existing patient by full name and date of birth.",
    request_model=FindPatientRequest,
    response_model=PatientResponse,
    returns_none=True,
)
CREATE_PATIENT = RPCOperation(
    name="create_patient",
    description="Register a new patient after collecting contact details.",
    request_model=CreatePatientRequest,
    response_model=PatientResponse,
)
LIST_AVAILABILITY_SLOTS = RPCOperation(
    name="list_availability_slots",
    description="List available appointment slots for a date or date range.",
    request_model=ListAvailabilitySlotsRequest,
    response_model=SlotResponse,
    returns_list=True,
)
CREATE_APPOINTMENT = RPCOperation(
    name="create_appointment",
    description="Book a selected appointment slot for a patient.",
    request_model=CreateAppointmentRequest,
    response_model=AppointmentResponse,
)
LIST_PATIENT_APPOINTMENTS = RPCOperation(
    name="list_patient_appointments",
    description="List a patient's appointments so the caller can choose one.",
    request_model=ListPatientAppointmentsRequest,
    response_model=AppointmentResponse,
    returns_list=True,
)
CANCEL_APPOINTMENT = RPCOperation(
    name="cancel_appointment",
    description="Cancel an appointment after the caller confirms.",
    request_model=CancelAppointmentRequest,
    response_model=AppointmentResponse,
)

RPC_OPERATIONS = (
    FIND_PATIENT,
    CREATE_PATIENT,
    LIST_AVAILABILITY_SLOTS,
    CREATE_APPOINTMENT,
    LIST_PATIENT_APPOINTMENTS,
    CANCEL_APPOINTMENT,
)
