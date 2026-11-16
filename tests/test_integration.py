import pytest
import requests
from hotel.service import BookingService
from hotel.repositories import PostgresBookingRepository, PostgresRoomRepository
from hotel.http_booking_policy import HttpBookingPolicy

def clear_wiremock(wiremock_url):
    try:
        requests.delete(f"{wiremock_url}/__admin/mappings", timeout=5)
    except Exception:
        pass

def set_wiremock_stub(wiremock_url, status, body):
    stub = {
        "request": {
            "method": "POST",
            "url": "/check"
        },
        "response": {
            "status": status,
            "jsonBody": body,
            "headers": {
                "Content-Type": "application/json"
            }
        }
    }
    requests.post(f"{wiremock_url}/__admin/mappings", json=stub, timeout=5)

def test_successful_booking_integration(setup_database, wiremock_container):
    clear_wiremock(wiremock_container)
    set_wiremock_stub(wiremock_container, 200, {"allowed": True})

    room_repo = PostgresRoomRepository(setup_database)
    repo = PostgresBookingRepository(setup_database)
    policy = HttpBookingPolicy(base_url=wiremock_container)
    
    service = BookingService(rooms=room_repo, bookings=repo, policy=policy)
    
    # Додайте сюди виклик методів тестування сервісу, якщо потрібно

def test_external_rejection_integration(setup_database, wiremock_container):
    clear_wiremock(wiremock_container)
    set_wiremock_stub(wiremock_container, 200, {"allowed": False, "reason": "No funds"})

    room_repo = PostgresRoomRepository(setup_database)
    repo = PostgresBookingRepository(setup_database)
    policy = HttpBookingPolicy(base_url=wiremock_container)
    
    service = BookingService(rooms=room_repo, bookings=repo, policy=policy)

def test_service_unavailable_integration(setup_database, wiremock_container):
    clear_wiremock(wiremock_container)
    set_wiremock_stub(wiremock_container, 503, {})

    room_repo = PostgresRoomRepository(setup_database)
    repo = PostgresBookingRepository(setup_database)
    policy = HttpBookingPolicy(base_url=wiremock_container)
    
    service = BookingService(rooms=room_repo, bookings=repo, policy=policy)

def test_local_rejection_integration(setup_database, wiremock_container):
    clear_wiremock(wiremock_container)

    room_repo = PostgresRoomRepository(setup_database)
    repo = PostgresBookingRepository(setup_database)
    policy = HttpBookingPolicy(base_url=wiremock_container)
    
    service = BookingService(rooms=room_repo, bookings=repo, policy=policy)