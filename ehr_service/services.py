from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ehr_service.domain import (
    APPOINTMENT_BOOKED,
    APPOINTMENT_CANCELLED,
    SLOT_AVAILABLE,
    SLOT_BOOKED,
    EHRConflictError,
    EHRNotFoundError,
    day_bounds,
    normalize_name,
    utc_now,
)
from ehr_service.models import Appointment, AvailabilitySlot, Patient
from ehr_service.repository import EHRRepository


class EHRService:
    def __init__(self, session: Session):
        self.repository = EHRRepository(session)

    def create_patient(
        self,
        name: str,
        date_of_birth: date,
        phone: str | None,
        email: str | None,
    ) -> Patient:
        normalized_name = normalize_name(name)
        patient = self.repository.find_patient(normalized_name, date_of_birth)
        if patient is not None:
            return patient

        patient = Patient(
            name=name.strip(),
            normalized_name=normalized_name,
            date_of_birth=date_of_birth,
            phone=phone,
            email=email,
        )
        self.repository.add_patient(patient)
        try:
            self.repository.commit()
        except IntegrityError:
            self.repository.rollback()
            existing = self.repository.find_patient(normalized_name, date_of_birth)
            if existing is None:
                raise
            return existing
        return patient

    def find_patient(self, name: str, date_of_birth: date) -> Patient | None:
        return self.repository.find_patient(normalize_name(name), date_of_birth)

    def list_availability_slots(
        self, from_date: date, to_date: date | None
    ) -> list[AvailabilitySlot]:
        start_at, end_at = day_bounds(from_date, to_date)
        return self.repository.list_available_slots(start_at, end_at)

    def create_appointment(self, patient_id: int, slot_id: int) -> Appointment:
        patient = self.repository.get_patient(patient_id)
        if patient is None:
            raise EHRNotFoundError("patient not found")

        slot = self.repository.get_slot_for_update(slot_id)
        if slot is None:
            raise EHRNotFoundError("slot not found")
        if slot.status != SLOT_AVAILABLE:
            raise EHRConflictError("slot is not available")

        appointment = Appointment(patient=patient, slot=slot, status=APPOINTMENT_BOOKED)
        slot.status = SLOT_BOOKED
        self.repository.add_appointment(appointment)
        self.repository.commit()
        return appointment

    def list_patient_appointments(
        self, patient_id: int, status: str | None = APPOINTMENT_BOOKED
    ) -> list[Appointment]:
        if self.repository.get_patient(patient_id) is None:
            raise EHRNotFoundError("patient not found")
        return self.repository.list_patient_appointments(patient_id, status)

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        appointment = self.repository.get_appointment_for_update(appointment_id)
        if appointment is None:
            raise EHRNotFoundError("appointment not found")

        if appointment.status != APPOINTMENT_CANCELLED:
            appointment.status = APPOINTMENT_CANCELLED
            appointment.cancelled_at = utc_now()
            appointment.slot.status = SLOT_AVAILABLE
            self.repository.commit()

        return appointment
