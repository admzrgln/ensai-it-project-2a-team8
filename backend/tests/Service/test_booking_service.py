from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from backend.src.Model.Booking import Booking
from backend.src.Model.Customer import Customer
from backend.src.Model.Screening import Screening
from backend.src.Model.Tariff import Tariff
from backend.src.Model.Ticket import Ticket
from backend.src.Service.BookingService import BookingError, BookingService, NotEnoughSeatsError

BASE_PRICE = 9.0


def make_screening(**overrides) -> Screening:
    data = dict(id_screening=1, id_room=1, id_movie=1, id_admin=1,
                date_time=datetime.now() + timedelta(days=7), base_price=BASE_PRICE, available_seats=50)
    data.update(overrides)
    return Screening(**data)


def make_customer(**overrides) -> Customer:
    data = dict(id_user=10, first_name="Louise", last_name="F", email="l@mail.fr",
                password="x", date_of_birth=date(2004, 3, 1), is_ensai_student=False)
    data.update(overrides)
    return Customer(**data)


def guest(**overrides) -> Ticket:
    data = dict(first_name="Guest", last_name="G", date_of_birth=date(1980, 1, 1))
    data.update(overrides)
    return Ticket(**data)


@pytest.fixture
def service():
    """BookingService avec les DAO mockés ; par défaut tout est valide."""
    s = BookingService()
    s.booking_dao = MagicMock()
    s.screening_dao = MagicMock()
    s.user_dao = MagicMock()
    s.user_dao.find_by_id.return_value = make_customer()
    s.screening_dao.find_by_id.return_value = make_screening()
    s.booking_dao.insert_booking.return_value = True
    s.tariff_service.tariff_dao = MagicMock()
    s.tariff_service.tariff_dao.find_all.return_value = [
        Tariff("child", "Moins de 14 ans", 4.50, max_age=13),
        Tariff("ensai", "Élève ENSAI", 4.00, requires_ensai=True),
        Tariff("student", "Étudiant·e", 6.00, requires_student=True),
        Tariff("full", "Plein tarif", None),
    ]
    return s


def test_book_myself_and_guests(service):
    booking = service.book(10, 1, include_myself=True, customer_is_student=True,
                           guests=[guest(), guest(date_of_birth=date(2018, 1, 1))])

    assert booking.seat_count == 3
    assert [t.tariff_code for t in booking.tickets] == ["student", "full", "child"]
    assert booking.tickets[0].is_holder is True
    assert booking.tickets[0].date_of_birth == date(2004, 3, 1)  # reprise du profil
    assert booking.total_price == round(sum(t.price for t in booking.tickets), 2)
    service.booking_dao.insert_booking.assert_called_once_with(booking)


def test_ensai_status_comes_from_account(service):
    service.user_dao.find_by_id.return_value = make_customer(is_ensai_student=True)
    booking = service.book(10, 1, True, False, [])
    assert booking.tickets[0].tariff_code == "ensai"


def test_book_only_for_guests(service):
    booking = service.book(10, 1, include_myself=False, customer_is_student=False, guests=[guest()])
    assert booking.seat_count == 1
    assert booking.tickets[0].is_holder is False


def test_quote_does_not_write(service):
    service.quote(10, 1, True, False, [guest()])
    service.booking_dao.insert_booking.assert_not_called()


def test_admin_cannot_book(service):
    service.user_dao.find_by_id.return_value = MagicMock(role="admin")
    with pytest.raises(BookingError):
        service.book(10, 1, True, False, [])


def test_empty_booking_refused(service):
    with pytest.raises(BookingError):
        service.book(10, 1, include_myself=False, customer_is_student=False, guests=[])


def test_past_screening_refused(service):
    service.screening_dao.find_by_id.return_value = make_screening(date_time=datetime.now() - timedelta(hours=1))
    with pytest.raises(BookingError):
        service.book(10, 1, True, False, [])


def test_not_enough_seats_before_insert(service):
    service.screening_dao.find_by_id.return_value = make_screening(available_seats=1)
    with pytest.raises(NotEnoughSeatsError):
        service.book(10, 1, True, False, [guest()])
    service.booking_dao.insert_booking.assert_not_called()


def test_not_enough_seats_race_condition(service):
    """La BDD refuse l'UPDATE car quelqu'un a pris les places entre-temps."""
    service.booking_dao.insert_booking.return_value = False
    with pytest.raises(NotEnoughSeatsError):
        service.book(10, 1, True, False, [])


def test_guest_born_after_screening_refused(service):
    with pytest.raises(BookingError):
        service.book(10, 1, False, False, [guest(date_of_birth=date.today() + timedelta(days=30))])


def test_cancel_other_customer_booking_refused(service):
    service.booking_dao.find_by_id.return_value = Booking(id_customer=99, id_screening=1, id_booking=5)
    with pytest.raises(BookingError):
        service.cancel(5, id_customer=10)
    service.booking_dao.cancel_booking.assert_not_called()


def test_cancel_ok(service):
    service.booking_dao.find_by_id.return_value = Booking(id_customer=10, id_screening=1, id_booking=5)
    service.booking_dao.cancel_booking.return_value = True
    assert service.cancel(5, id_customer=10) is True


# --- Cas d'erreur supplémentaires (coverage 100 %) ---------------------------------
def test_unknown_screening_refused(service):
    service.screening_dao.find_by_id.return_value = None
    with pytest.raises(BookingError, match="Screening not found"):
        service.book(10, 999, True, False, [])


def test_customer_without_date_of_birth_refused(service):
    service.user_dao.find_by_id.return_value = make_customer(date_of_birth=None)
    with pytest.raises(BookingError, match="date of birth is missing"):
        service.book(10, 1, include_myself=True, customer_is_student=False, guests=[])


def test_customer_without_date_of_birth_can_book_for_guests_only(service):
    service.user_dao.find_by_id.return_value = make_customer(date_of_birth=None)
    booking = service.book(10, 1, include_myself=False, customer_is_student=False, guests=[guest()])
    assert booking.seat_count == 1


def test_guest_without_date_of_birth_refused(service):
    with pytest.raises(BookingError, match="Date of birth is required"):
        service.book(10, 1, False, False, [guest(date_of_birth=None)])


def test_more_than_max_tickets_refused(service):
    guests = [guest() for _ in range(10)]  # + le client = 11 billets
    with pytest.raises(BookingError, match="limited to 10 tickets"):
        service.book(10, 1, True, False, guests)
    service.booking_dao.insert_booking.assert_not_called()


def test_find_by_id_delegates_to_dao(service):
    booking = Booking(id_customer=10, id_screening=1, id_booking=5)
    service.booking_dao.find_by_id.return_value = booking
    assert service.find_by_id(5) is booking
    service.booking_dao.find_by_id.assert_called_once_with(5)


def test_find_by_customer_delegates_to_dao(service):
    bookings = [Booking(id_customer=10, id_screening=1, id_booking=5)]
    service.booking_dao.find_by_customer.return_value = bookings
    assert service.find_by_customer(10) == bookings
    service.booking_dao.find_by_customer.assert_called_once_with(10)


def test_cancel_already_cancelled_booking_refused(service):
    service.booking_dao.find_by_id.return_value = Booking(id_customer=10, id_screening=1, id_booking=5,
                                                          status="cancelled")
    with pytest.raises(BookingError, match="already cancelled"):
        service.cancel(5, id_customer=10)
    service.booking_dao.cancel_booking.assert_not_called()


def test_cancel_started_screening_refused(service):
    service.booking_dao.find_by_id.return_value = Booking(id_customer=10, id_screening=1, id_booking=5)
    service.screening_dao.find_by_id.return_value = make_screening(date_time=datetime.now() - timedelta(hours=1))
    with pytest.raises(BookingError, match="already started"):
        service.cancel(5, id_customer=10)
    service.booking_dao.cancel_booking.assert_not_called()


def test_list_tariffs_uses_screening_base_price(service):
    tariffs = service.list_tariffs(1)
    assert {"code": "full", "label": "Plein tarif", "price": BASE_PRICE} in tariffs
    assert {"code": "student", "label": "Étudiant·e", "price": 6.0} in tariffs


def test_list_tariffs_unknown_screening(service):
    service.screening_dao.find_by_id.return_value = None
    with pytest.raises(BookingError, match="Screening not found"):
        service.list_tariffs(999)
