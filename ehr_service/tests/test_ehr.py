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

        found_patient = client.get(
            "/rpc/find_patient",
            params={"name": "  grace   hopper  ", "date_of_birth": "1990-01-02"},
        )
        assert found_patient.status_code == 200
        assert found_patient.json()["id"] == patient["id"]

        slots_response = client.get(
            "/rpc/list_availability_slots",
            params={"from_date": "2030-01-15"},
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

        double_booking = client.post(
            "/rpc/create_appointment",
            json={"patient_id": patient["id"], "slot_id": slot_id},
        )
        assert double_booking.status_code == 409

        slots_after_booking = client.get(
            "/rpc/list_availability_slots",
            params={"from_date": "2030-01-15"},
        )
        assert len(slots_after_booking.json()) == 3

        cancelled_response = client.put(
            "/rpc/cancel_appointment",
            json={"appointment_id": appointment["id"]},
        )
        assert cancelled_response.status_code == 200
        cancelled = cancelled_response.json()
        assert cancelled["status"] == "cancelled"

        slots_after_cancel = client.get(
            "/rpc/list_availability_slots",
            params={"from_date": "2030-01-15"},
        )
        assert len(slots_after_cancel.json()) == 4

    recreated_app = create_app(database_url)
    with TestClient(recreated_app) as client:
        persisted_patient = client.get(
            "/rpc/find_patient",
            params={"name": "Grace Hopper", "date_of_birth": "1990-01-02"},
        )
        assert persisted_patient.status_code == 200
        assert persisted_patient.json()["id"] == patient["id"]

        persisted_slots = client.get(
            "/rpc/list_availability_slots",
            params={"from_date": "2030-01-15"},
        )
        assert persisted_slots.status_code == 200
        assert len(persisted_slots.json()) == 4
