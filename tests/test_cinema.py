import pytest
from cinema_booking_service import CinemaBookingService, Request, Result

class DummySeats:
    def __init__(self, count: int = 10):
        self._count = count
    def free_seats(self) -> int:
        return self._count

class DummyStudents:
    def __init__(self, eligible: bool = True):
        self._eligible = eligible
    def is_eligible(self) -> bool:
        return self._eligible

class DummyRepository:
    def save(self, request: Request, result: Result) -> None:
        pass

def test_age_restriction_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(), DummyRepository())
    request = Request(tickets=1, age=10, evening=True, student_claimed=False)
    
    result = service.process(request)
    assert result.status == "Вікове обмеження"

def test_not_enough_seats_serviceState():
    service = CinemaBookingService(DummySeats(2), DummyStudents(), DummyRepository())
    request = Request(tickets=5, age=20, evening=False, student_claimed=False)
    
    result = service.process(request)
    assert result.status == "Недостатньо місць"

def test_child_discount_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(), DummyRepository())
    request = Request(tickets=1, age=10, evening=False, student_claimed=False)
    
    result = service.process(request)
    assert result.status == "Заброньовано"
    assert result.total == 5000

def test_student_discount_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(eligible=True), DummyRepository())
    request = Request(tickets=1, age=20, evening=True, student_claimed=True)
    
    result = service.process(request)
    assert result.status == "Заброньовано"
    assert result.total == 12000

def test_bulk_tickets_discount_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(eligible=False), DummyRepository())
    request = Request(tickets=6, age=25, evening=False, student_claimed=False)
    
    result = service.process(request)
    assert result.status == "Заброньовано"
    assert result.total == 58000

def test_invalid_ticket_range_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(), DummyRepository())
    request = Request(tickets=0, age=20, evening=False, student_claimed=False)
    
    with pytest.raises(ValueError):
        service.process(request)


def test_invalid_request_type_serviceState():
    service = CinemaBookingService(DummySeats(10), DummyStudents(), DummyRepository())
    
    with pytest.raises(ValueError):
        service.process("not_a_request_object")  