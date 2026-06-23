from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ehr_service.domain import SLOT_AVAILABLE
from ehr_service.models import Appointment, AvailabilitySlot, Patient


class EHRRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_patient(self, normalized_name: str, date_of_birth: date) -> Patient | None:
        return self.session.scalar(
            select(Patient).where(
                Patient.normalized_name == normalized_name,
                Patient.date_of_birth == date_of_birth,
            )
        )

    def add_patient(self, patient: Patient) -> Patient:
        self.session.add(patient)
        return patient

    def get_patient(self, patient_id: int) -> Patient | None:
        return self.session.get(Patient, patient_id)

    def list_available_slots(self, start_at: datetime, end_at: datetime) -> list[AvailabilitySlot]:
        return list(
            self.session.scalars(
                select(AvailabilitySlot)
                .where(
                    AvailabilitySlot.status == SLOT_AVAILABLE,
                    AvailabilitySlot.start_at >= start_at,
                    AvailabilitySlot.start_at < end_at,
                )
                .order_by(AvailabilitySlot.start_at)
            )
        )

    def get_slot_for_update(self, slot_id: int) -> AvailabilitySlot | None:
        return self.session.scalar(
            select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id).with_for_update()
        )

    def add_appointment(self, appointment: Appointment) -> Appointment:
        self.session.add(appointment)
        return appointment

    def list_patient_appointments(
        self, patient_id: int, status: str | None
    ) -> list[Appointment]:
        query = (
            select(Appointment)
            .join(Appointment.slot)
            .options(selectinload(Appointment.patient), selectinload(Appointment.slot))
            .where(Appointment.patient_id == patient_id)
            .order_by(AvailabilitySlot.start_at)
        )
        if status:
            query = query.where(Appointment.status == status)
        return list(self.session.scalars(query))

    def get_appointment_for_update(self, appointment_id: int) -> Appointment | None:
        return self.session.scalar(
            select(Appointment).where(Appointment.id == appointment_id).with_for_update()
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
