from datetime import date, datetime

from backend.src.Model.Booking import Booking
from backend.src.Model.Ticket import Ticket


def make_ticket(price: float | None, **overrides) -> Ticket:
    data = dict(first_name="A", last_name="B", date_of_birth=date(1990, 1, 1), tariff_code="full", price=price)
    data.update(overrides)
    return Ticket(**data)


def test_booking_constructor_defaults():
    b = Booking(id_customer=10, id_screening=1)
    assert (b.id_customer, b.id_screening) == (10, 1)
    assert b.tickets == []
    assert b.status == "confirmed"
    assert b.booking_date is None
    assert b.id_booking is None


def test_empty_booking_has_no_seat_and_costs_nothing():
    b = Booking(10, 1)
    assert b.seat_count == 0
    assert b.total_price == 0


def test_seat_count_is_number_of_tickets():
    b = Booking(10, 1, tickets=[make_ticket(9.0), make_ticket(4.5), make_ticket(6.0)])
    assert b.seat_count == 3


def test_total_price_is_rounded_sum():
    # 0.1 + 0.2 = 0.30000000000000004 en flottants : on doit obtenir 0.3
    b = Booking(10, 1, tickets=[make_ticket(0.1), make_ticket(0.2)])
    assert b.total_price == 0.3


def test_total_price_ignores_unpriced_tickets():
    b = Booking(10, 1, tickets=[make_ticket(9.0), make_ticket(None)])
    assert b.total_price == 9.0


def test_to_dict_contains_computed_fields_and_tickets():
    booked_at = datetime(2026, 11, 4, 10, 0)
    b = Booking(10, 1, tickets=[make_ticket(9.0, first_name="Louise"), make_ticket(4.5)],
                booking_date=booked_at, id_booking=5)
    d = b.to_dict()
    assert d["id_booking"] == 5
    assert d["id_customer"] == 10
    assert d["id_screening"] == 1
    assert d["booking_date"] == booked_at
    assert d["status"] == "confirmed"
    assert d["seat_count"] == 2
    assert d["total_price"] == 13.5
    assert len(d["tickets"]) == 2
    assert d["tickets"][0]["first_name"] == "Louise"
    assert d["tickets"][0]["price"] == 9.0


def test_booking_str():
    b = Booking(10, 1, tickets=[make_ticket(9.0)], id_booking=5)
    assert str(b) == "Booking 5 : séance 1, 1 place(s), total 9.0€ (confirmed)"
