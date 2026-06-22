from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from ehr_service.database import SessionFactory, database_url, init_db, make_session_factory
from ehr_service.domain import EHRConflictError, EHRNotFoundError, EHRValidationError
from ehr_service.rpc import (
    AppointmentResponse,
    CancelAppointmentRequest,
    CreateAppointmentRequest,
    CreatePatientRequest,
    FindPatientRequest,
    ListAvailabilitySlotsRequest,
    ListPatientAppointmentsRequest,
    PatientResponse,
    SlotResponse,
)
from ehr_service.services import EHRService


def get_session_dependency(session_factory: SessionFactory):
    def get_session():
        with session_factory() as session:
            yield session

    return get_session


def map_domain_error(error: Exception) -> HTTPException:
    if isinstance(error, EHRNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, EHRConflictError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, EHRValidationError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=500, detail="unexpected EHR error")


def create_app(db_url: str | None = None) -> FastAPI:
    session_factory = make_session_factory(db_url or database_url())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(session_factory)
        yield
        session_factory.kw["bind"].dispose()

    app = FastAPI(
        title="Prosper Challenge EHR",
        description="Small EHR HTTP API for patient lookup and appointment scheduling.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.SessionLocal = session_factory
    get_session = get_session_dependency(session_factory)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/rpc/create_patient", response_model=PatientResponse)
    def create_patient(
        request: CreatePatientRequest,
        session: Session = Depends(get_session),
    ):
        service = EHRService(session)
        return service.create_patient(
            name=request.name,
            date_of_birth=request.date_of_birth,
            phone=request.phone,
            email=request.email,
        )

    @app.post("/rpc/find_patient", response_model=PatientResponse | None)
    def find_patient(
        request: FindPatientRequest,
        session: Session = Depends(get_session),
    ):
        return EHRService(session).find_patient(
            name=request.name,
            date_of_birth=request.date_of_birth,
        )

    @app.post("/rpc/list_availability_slots", response_model=list[SlotResponse])
    def list_availability_slots(
        request: ListAvailabilitySlotsRequest,
        session: Session = Depends(get_session),
    ):
        try:
            return EHRService(session).list_availability_slots(
                from_date=request.from_date,
                to_date=request.to_date,
            )
        except EHRValidationError as error:
            raise map_domain_error(error) from error

    @app.post("/rpc/create_appointment", response_model=AppointmentResponse)
    def create_appointment(
        request: CreateAppointmentRequest,
        session: Session = Depends(get_session),
    ):
        try:
            return EHRService(session).create_appointment(
                patient_id=request.patient_id,
                slot_id=request.slot_id,
            )
        except (EHRNotFoundError, EHRConflictError) as error:
            raise map_domain_error(error) from error

    @app.post("/rpc/list_patient_appointments", response_model=list[AppointmentResponse])
    def list_patient_appointments(
        request: ListPatientAppointmentsRequest,
        session: Session = Depends(get_session),
    ):
        try:
            return EHRService(session).list_patient_appointments(
                patient_id=request.patient_id,
                status=request.status,
            )
        except EHRNotFoundError as error:
            raise map_domain_error(error) from error

    @app.post("/rpc/cancel_appointment", response_model=AppointmentResponse)
    def cancel_appointment(
        request: CancelAppointmentRequest,
        session: Session = Depends(get_session),
    ):
        try:
            return EHRService(session).cancel_appointment(request.appointment_id)
        except EHRNotFoundError as error:
            raise map_domain_error(error) from error

    return app
