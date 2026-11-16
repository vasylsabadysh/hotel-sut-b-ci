import pytest
from fastapi.testclient import TestClient
from hotel.api import app, get_booking_service, CANCELLED_BOOKINGS
from hotel.service import BookingService
from hotel.repositories import PostgresBookingRepository, PostgresRoomRepository
from hotel.http_booking_policy import HttpBookingPolicy


@pytest.fixture
def client(setup_database, wiremock_container):
    CANCELLED_BOOKINGS.clear()
    conn_url = setup_database.replace("postgresql+psycopg2://", "postgresql://")

    def override_get_service():
        rooms_repo = PostgresRoomRepository(conn_url)
        bookings_repo = PostgresBookingRepository(conn_url)
        policy = HttpBookingPolicy(wiremock_container)
        try:
            return BookingService(rooms_repo, bookings_repo, policy)
        except TypeError:
            return BookingService(bookings_repo, policy)

    app.dependency_overrides[get_booking_service] = override_get_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    CANCELLED_BOOKINGS.clear()


@pytest.fixture
def created_room(setup_database):
    conn_url = setup_database.replace("postgresql+psycopg2://", "postgresql://")
    rooms_repo = PostgresRoomRepository(conn_url)
    try:
        room = rooms_repo.add("API-ROOM-101", 10000, 4)
        return getattr(room, "id", 1)
    except Exception:
        return 1


def test_create_booking_success(client, created_room):
    payload = {
        "reference": "REF-001",
        "room_id": created_room,
        "check_in": "2026-12-01",
        "check_out": "2026-12-05",
        "guests": 2,
        "regular": False
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code in [201, 200], f"Response error: {response.text}"
    data = response.json()
    assert "id" in data or "booking_id" in data or "reference" in data


def test_get_booking_by_id(client, created_room):
    create_res = client.post("/bookings", json={
        "reference": "REF-002",
        "room_id": created_room,
        "check_in": "2026-12-10",
        "check_out": "2026-12-12",
        "guests": 1,
        "regular": False
    })
    assert create_res.status_code in [201, 200], f"Create failed: {create_res.text}"
    data = create_res.json()
    booking_id = data.get("id") or data.get("booking_id")

    get_res = client.get(f"/bookings/{booking_id}")
    assert get_res.status_code == 200


def test_get_nonexistent_booking_404(client):
    response = client.get("/bookings/999999")
    assert response.status_code == 404


def test_action_cancel_booking_success(client, created_room):
    create_res = client.post("/bookings", json={
        "reference": "REF-003",
        "room_id": created_room,
        "check_in": "2026-12-15",
        "check_out": "2026-12-18",
        "guests": 2,
        "regular": False
    })
    data = create_res.json()
    booking_id = data.get("id") or data.get("booking_id")

    action_res = client.post(f"/bookings/{booking_id}/cancel")
    assert action_res.status_code in [200, 204]


def test_action_cancel_already_cancelled_409(client, created_room):
    create_res = client.post("/bookings", json={
        "reference": "REF-004",
        "room_id": created_room,
        "check_in": "2026-12-20",
        "check_out": "2026-12-22",
        "guests": 2,
        "regular": False
    })
    data = create_res.json()
    booking_id = data.get("id") or data.get("booking_id")

    client.post(f"/bookings/{booking_id}/cancel")
    second_action = client.post(f"/bookings/{booking_id}/cancel")
    assert second_action.status_code in [409, 400]


def test_state_remains_unchanged_after_409(client, created_room):
    create_res = client.post("/bookings", json={
        "reference": "REF-005",
        "room_id": created_room,
        "check_in": "2026-12-25",
        "check_out": "2026-12-28",
        "guests": 2,
        "regular": False
    })
    data = create_res.json()
    booking_id = data.get("id") or data.get("booking_id")

    client.post(f"/bookings/{booking_id}/cancel")
    client.post(f"/bookings/{booking_id}/cancel")

    get_res = client.get(f"/bookings/{booking_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "CANCELLED"


@pytest.mark.parametrize("check_in, check_out, expected_status", [
    ("2026-11-01", "2026-11-05", 201),
    ("2026-11-05", "2026-11-01", 400),
])
def test_business_rule_date_validation(client, created_room, check_in, check_out, expected_status):
    payload = {
        "reference": f"REF-RULE-{check_in}",
        "room_id": created_room,
        "check_in": check_in,
        "check_out": check_out,
        "guests": 1,
        "regular": False
    }
    response = client.post("/bookings", json=payload)
    if expected_status == 201:
        assert response.status_code in [201, 200], f"Failed: {response.text}"
    else:
        assert response.status_code in [400, 422, 409], f"Failed: {response.text}"


def test_full_booking_workflow(client, created_room):
    post_res = client.post("/bookings", json={
        "reference": "REF-WORKFLOW",
        "room_id": created_room,
        "check_in": "2026-12-01",
        "check_out": "2026-12-10",
        "guests": 2,
        "regular": False
    })
    assert post_res.status_code in [201, 200], f"POST failed: {post_res.text}"
    data = post_res.json()
    booking_id = data.get("id") or data.get("booking_id")

    get_res1 = client.get(f"/bookings/{booking_id}")
    assert get_res1.status_code == 200

    action_res = client.post(f"/bookings/{booking_id}/cancel")
    assert action_res.status_code in [200, 204]

    get_res2 = client.get(f"/bookings/{booking_id}")
    assert get_res2.status_code == 200
    assert get_res2.json()["status"] == "CANCELLED"