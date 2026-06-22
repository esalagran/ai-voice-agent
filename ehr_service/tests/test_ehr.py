from fastapi.testclient import TestClient

from ehr_service.api import create_app
from ehr_service.seed import seed_demo_data


def test_ehr_patient_appointment_flow_persists(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'ehr-test.db'}"
    app = create_app(database_url)

    with TestClient(app) as client:
        seed_demo_data(app.state.SessionLocal)

        created_patient = client.post(
            "/rpc/create_patient",
            json={
                "name": "Grace Hopper",
                "date_of_birth": "1990-01-02",
                "phone": "+1-555-0101",
                "email": "grace@example.com",
            },
        )
        assert created_patient.status_code == 200
        patient = created_patient.json()
        assert patient["name"] == "Grace Hopper"

        found_patient = client.post(
            "/rpc/find_patient",
            json={"name": "  grace   hopper  ", "date_of_birth": "1990-01-02"},
        )
        assert found_patient.status_code == 200
        assert found_patient.json()["id"] == patient["id"]

        slots_response = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-15"},
        )
        assert slots_response.status_code == 200
        slots = slots_response.json()
        assert len(slots) == 4
        slot_id = slots[0]["id"]

        appointment_response = client.post(
            "/rpc/create_appointment",
            json={"patient_id": patient["id"], "slot_id": slot_id},
        )
        assert appointment_response.status_code == 200
        appointment = appointment_response.json()
        assert appointment["status"] == "booked"
        assert appointment["patient"]["id"] == patient["id"]
        assert appointment["slot"]["id"] == slot_id

        patient_appointments = client.post(
            "/rpc/list_patient_appointments",
            json={"patient_id": patient["id"]},
        )
        assert patient_appointments.status_code == 200
        assert patient_appointments.json()[0]["id"] == appointment["id"]

        double_booking = client.post(
            "/rpc/create_appointment",
            json={"patient_id": patient["id"], "slot_id": slot_id},
        )
        assert double_booking.status_code == 409

        slots_after_booking = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-15"},
        )
        assert len(slots_after_booking.json()) == 3

        cancelled_response = client.post(
            "/rpc/cancel_appointment",
            json={"appointment_id": appointment["id"]},
        )
        assert cancelled_response.status_code == 200
        cancelled = cancelled_response.json()
        assert cancelled["status"] == "cancelled"

        booked_after_cancel = client.post(
            "/rpc/list_patient_appointments",
            json={"patient_id": patient["id"]},
        )
        assert booked_after_cancel.status_code == 200
        assert booked_after_cancel.json() == []

        cancelled_appointments = client.post(
            "/rpc/list_patient_appointments",
            json={"patient_id": patient["id"], "status": "cancelled"},
        )
        assert cancelled_appointments.status_code == 200
        assert cancelled_appointments.json()[0]["id"] == appointment["id"]

        slots_after_cancel = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-15"},
        )
        assert len(slots_after_cancel.json()) == 4

    recreated_app = create_app(database_url)
    with TestClient(recreated_app) as client:
        persisted_patient = client.post(
            "/rpc/find_patient",
            json={"name": "Grace Hopper", "date_of_birth": "1990-01-02"},
        )
        assert persisted_patient.status_code == 200
        assert persisted_patient.json()["id"] == patient["id"]

        persisted_slots = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-15"},
        )
        assert persisted_slots.status_code == 200
        assert len(persisted_slots.json()) == 4


def test_ehr_patient_lookup_and_validation_use_cases(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'ehr-test.db'}"
    app = create_app(database_url)

    with TestClient(app) as client:
        missing_patient = client.post(
            "/rpc/find_patient",
            json={"name": "Missing Patient", "date_of_birth": "1990-01-02"},
        )
        assert missing_patient.status_code == 200
        assert missing_patient.json() is None

        invalid_patient = client.post(
            "/rpc/create_patient",
            json={"name": "", "date_of_birth": "1990-01-02"},
        )
        assert invalid_patient.status_code == 422

        invalid_range = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-16", "to_date": "2030-01-15"},
        )
        assert invalid_range.status_code == 400

        missing_patient_booking = client.post(
            "/rpc/create_appointment",
            json={"patient_id": 999, "slot_id": 999},
        )
        assert missing_patient_booking.status_code == 404

        missing_appointment_cancel = client.post(
            "/rpc/cancel_appointment",
            json={"appointment_id": 999},
        )
        assert missing_appointment_cancel.status_code == 404

        missing_patient_appointments = client.post(
            "/rpc/list_patient_appointments",
            json={"patient_id": 999},
        )
        assert missing_patient_appointments.status_code == 404


def test_ehr_reuses_patients_and_lists_date_ranges(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'ehr-test.db'}"
    app = create_app(database_url)

    with TestClient(app) as client:
        seed_demo_data(app.state.SessionLocal)

        patient_response = client.post(
            "/rpc/create_patient",
            json={"name": "Ada Lovelace", "date_of_birth": "1985-12-10"},
        )
        assert patient_response.status_code == 200
        patient = patient_response.json()

        duplicate_response = client.post(
            "/rpc/create_patient",
            json={"name": "  ada   lovelace  ", "date_of_birth": "1985-12-10"},
        )
        assert duplicate_response.status_code == 200
        assert duplicate_response.json()["id"] == patient["id"]

        range_response = client.post(
            "/rpc/list_availability_slots",
            json={"from_date": "2030-01-15", "to_date": "2030-01-16"},
        )
        assert range_response.status_code == 200
        assert len(range_response.json()) == 4
