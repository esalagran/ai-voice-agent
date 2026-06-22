from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePatientRequest(BaseModel):
    name: str = Field(min_length=1)
    date_of_birth: date
    phone: str | None = None
    email: str | None = None


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


class CreateAppointmentRequest(BaseModel):
    patient_id: int
    slot_id: int


class CancelAppointmentRequest(BaseModel):
    appointment_id: int


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    patient: PatientResponse
    slot: SlotResponse
    created_at: datetime
    cancelled_at: datetime | None
