from datetime import date
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.BookingController import booking_router
from backend.src.Model.Booking import Booking
from backend.src.Model.Ticket import Ticket
from backend.src.Service.BookingService import BookingError, NotEnoughSeatsError
from backend.src.Service.JWTService import JwtService

app = FastAPI()
app.include_router(booking_router)
client = TestClient(app)

BASE_URL = "/bookings"
SERVICE = "backend.src.Controller.BookingController.booking_service"

jwt = JwtService()
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}

booking_request = {
    "id_screening": 1,
    "include_myself": True,
    "customer_is_student": True,
    "guests": [{"first_name": "Kid", "last_name": "F", "date_of_birth": "2018-01-01"}],
}


def make_booking(id_customer: int = 10, id_booking: int | None = 5) -> Booking:
    return Booking(id_customer=id_customer, id_screening=1, id_booking=id_booking, tickets=[
        Ticket("Louise", "F", date(2004, 3, 1), is_holder=True, tariff_code="student", price=6.0),
        Ticket("Kid", "F", date(2018, 1, 1), tariff_code="child", price=4.5),
    ])


# --- Authentification ----------------------------------------------------------
def test_booking_without_token_is_refused():
    response = client.post(f"{BASE_URL}/", json=booking_request)
    assert response.status_code in (401, 403)


def test_booking_with_invalid_token_is_refused():
    response = client.post(f"{BASE_URL}/", json=booking_request, headers={"Authorization": "Bearer abc"})
    assert response.status_code == 403


@patch(SERVICE)
def test_admin_cannot_book(mock_service):
    response = client.post(f"{BASE_URL}/", json=booking_request, headers=ADMIN)
    assert response.status_code == 403
    mock_service.book.assert_not_called()


# --- GET /bookings/tariffs/{id_screening} -----------------------------------------
@patch(SERVICE)
def test_tariffs_for_screening_is_public(mock_service):
    mock_service.list_tariffs.return_value = [{"code": "full", "label": "Plein tarif", "price": 9.0}]

    response = client.get(f"{BASE_URL}/tariffs/1")

    assert response.status_code == 200
    assert response.json()[0]["code"] == "full"
    mock_service.list_tariffs.assert_called_once_with(1)


@patch(SERVICE)
def test_tariffs_for_unknown_screening(mock_service):
    mock_service.list_tariffs.side_effect = BookingError("Screening not found")
    response = client.get(f"{BASE_URL}/tariffs/999")
    assert response.status_code == 400
    assert response.json()["detail"] == "Screening not found"


# --- POST /bookings/quote ---------------------------------------------------------
@patch(SERVICE)
def test_quote_returns_total_without_booking(mock_service):
    mock_service.quote.return_value = make_booking(id_booking=None)

    response = client.post(f"{BASE_URL}/quote", json=booking_request, headers=CUSTOMER)

    assert response.status_code == 200
    assert response.json()["total_price"] == 10.5
    assert response.json()["id_booking"] is None
    mock_service.book.assert_not_called()


# --- POST /bookings/ --------------------------------------------------------------
@patch(SERVICE)
def test_create_booking(mock_service):
    mock_service.book.return_value = make_booking()

    response = client.post(f"{BASE_URL}/", json=booking_request, headers=CUSTOMER)

    assert response.status_code == 201
    body = response.json()
    assert body["id_booking"] == 5
    assert body["seat_count"] == 2
    assert body["total_price"] == 10.5
    assert [t["tariff_code"] for t in body["tickets"]] == ["student", "child"]


@patch(SERVICE)
def test_create_booking_passes_jwt_user_and_guests_to_service(mock_service):
    mock_service.book.return_value = make_booking()

    client.post(f"{BASE_URL}/", json=booking_request, headers=CUSTOMER)

    id_customer, id_screening, include_myself, customer_is_student, guests = mock_service.book.call_args.args
    assert id_customer == 10  # lu dans le token, pas dans le body
    assert (id_screening, include_myself, customer_is_student) == (1, True, True)
    assert len(guests) == 1
    assert isinstance(guests[0], Ticket)
    assert guests[0].date_of_birth == date(2018, 1, 1)


@patch(SERVICE)
def test_create_booking_business_error_gives_400(mock_service):
    mock_service.book.side_effect = BookingError("This screening has already started")

    response = client.post(f"{BASE_URL}/", json=booking_request, headers=CUSTOMER)

    assert response.status_code == 400
    assert response.json()["detail"] == "This screening has already started"


@patch(SERVICE)
def test_create_booking_not_enough_seats_gives_409(mock_service):
    mock_service.book.side_effect = NotEnoughSeatsError("Only 1 seat(s) left for this screening")

    response = client.post(f"{BASE_URL}/", json=booking_request, headers=CUSTOMER)

    assert response.status_code == 409


@patch(SERVICE)
def test_create_booking_invalid_body_gives_422(mock_service):
    bad = {**booking_request, "guests": [{"first_name": "Kid", "last_name": "F", "date_of_birth": "pas une date"}]}
    response = client.post(f"{BASE_URL}/", json=bad, headers=CUSTOMER)
    assert response.status_code == 422
    mock_service.book.assert_not_called()


# --- GET /bookings/me et /bookings/{id} ---------------------------------------------
@patch(SERVICE)
def test_my_bookings(mock_service):
    mock_service.find_by_customer.return_value = [make_booking(id_booking=5), make_booking(id_booking=6)]

    response = client.get(f"{BASE_URL}/me", headers=CUSTOMER)

    assert response.status_code == 200
    assert [b["id_booking"] for b in response.json()] == [5, 6]
    mock_service.find_by_customer.assert_called_once_with(10)


@patch(SERVICE)
def test_booking_by_id(mock_service):
    mock_service.find_by_id.return_value = make_booking()

    response = client.get(f"{BASE_URL}/5", headers=CUSTOMER)

    assert response.status_code == 200
    assert response.json()["id_booking"] == 5


@patch(SERVICE)
def test_booking_of_another_customer_is_hidden(mock_service):
    mock_service.find_by_id.return_value = make_booking(id_customer=99)
    response = client.get(f"{BASE_URL}/5", headers=CUSTOMER)
    assert response.status_code == 404


@patch(SERVICE)
def test_booking_by_id_not_found(mock_service):
    mock_service.find_by_id.return_value = None
    response = client.get(f"{BASE_URL}/999", headers=CUSTOMER)
    assert response.status_code == 404


# --- DELETE /bookings/{id} ------------------------------------------------------------
@patch(SERVICE)
def test_cancel_booking(mock_service):
    mock_service.cancel.return_value = True

    response = client.delete(f"{BASE_URL}/5", headers=CUSTOMER)

    assert response.status_code == 200
    mock_service.cancel.assert_called_once_with(5, 10)


@patch(SERVICE)
def test_cancel_booking_error(mock_service):
    mock_service.cancel.side_effect = BookingError("Booking not found")
    response = client.delete(f"{BASE_URL}/5", headers=CUSTOMER)
    assert response.status_code == 400
