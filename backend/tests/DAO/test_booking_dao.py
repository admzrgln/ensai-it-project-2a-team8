from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from backend.src.DAO.BookingDAO import BookingDao
from backend.src.Model.Booking import Booking
from backend.src.Model.Ticket import Ticket

BOOKED_AT = datetime(2026, 11, 4, 10, 0)


@pytest.fixture
def connector():
    """Remplace DBConnector dans BookingDAO : renvoie le mock de l'instance DBConnector()."""
    with patch("backend.src.DAO.BookingDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value


@pytest.fixture
def sql_query(connector):
    return connector.sql_query


@pytest.fixture
def cursor(connector):
    """Faux curseur pour les méthodes en transaction (get_connection)."""
    conn = MagicMock()
    conn.__exit__.return_value = False
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False
    connector.get_connection.return_value = conn
    cur.conn = conn
    return cur


@pytest.fixture
def dao():
    return BookingDao()


def booking_row(**overrides) -> dict:
    row = {
        "id_booking": 5,
        "id_customer": 10,
        "id_screening": 1,
        "booking_date": BOOKED_AT,
        "status": "confirmed",
        "seat_count": 2,
        "total_price": Decimal("13.50"),
    }
    row.update(overrides)
    return row


def ticket_row(**overrides) -> dict:
    row = {
        "id_ticket": 7,
        "id_booking": 5,
        "first_name": "Thomas",
        "last_name": "E",
        "date_of_birth": date(2004, 3, 1),
        "is_holder": True,
        "is_ensai_student": True,
        "is_student": False,
        "tariff_code": "ensai",
        "price": Decimal("4.00"),
    }
    row.update(overrides)
    return row


def make_booking() -> Booking:
    return Booking(
        id_customer=10,
        id_screening=1,
        tickets=[
            Ticket(
                "Thomas", "E", date(2004, 3, 1), is_holder=True, is_ensai_student=True, tariff_code="ensai", price=4.0
            ),
            Ticket("Kid", "F", date(2018, 1, 1), tariff_code="child", price=4.5),
        ],
    )


def test_to_ticket_maps_columns_and_converts_decimal_to_float():
    t = BookingDao._to_ticket(ticket_row())
    assert (t.id_ticket, t.id_booking, t.first_name, t.last_name) == (7, 5, "Thomas", "E")
    assert t.date_of_birth == date(2004, 3, 1)
    assert t.is_holder is True and t.is_ensai_student is True and t.is_student is False
    assert t.tariff_code == "ensai"
    assert t.price == 4.0 and isinstance(t.price, float)


def test_to_booking_maps_columns():
    tickets = [BookingDao._to_ticket(ticket_row())]
    b = BookingDao._to_booking(booking_row(), tickets)
    assert (b.id_booking, b.id_customer, b.id_screening) == (5, 10, 1)
    assert b.booking_date == BOOKED_AT
    assert b.status == "confirmed"
    assert b.tickets == tickets


def test_find_by_id_found_loads_tickets(dao, sql_query):
    sql_query.side_effect = [booking_row(), [ticket_row(), ticket_row(id_ticket=8, first_name="Kid")]]

    b = dao.find_by_id(5)

    assert b.id_booking == 5
    assert [t.first_name for t in b.tickets] == ["Thomas", "Kid"]
    assert sql_query.call_count == 2


def test_find_by_id_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_by_id(999) is None
    sql_query.assert_called_once()


def test_find_by_id_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.find_by_id(5)


def test_find_by_customer(dao, sql_query):
    sql_query.side_effect = [
        [booking_row(id_booking=5), booking_row(id_booking=6)],
        [ticket_row(id_booking=5)],
        [ticket_row(id_booking=6), ticket_row(id_booking=6, id_ticket=9)],
    ]

    bookings = dao.find_by_customer(10)

    assert [b.id_booking for b in bookings] == [5, 6]
    assert [b.seat_count for b in bookings] == [1, 2]
    assert sql_query.call_args_list[0].kwargs["data"] == {"id": 10}


def test_find_by_customer_without_booking(dao, sql_query):
    sql_query.return_value = []
    assert dao.find_by_customer(10) == []


def test_insert_booking_ok(dao, cursor):
    cursor.fetchone.side_effect = [
        {"available_seats": 48},
        {"id_booking": 5, "booking_date": BOOKED_AT},
        {"id_ticket": 7},
        {"id_ticket": 8},
    ]
    booking = make_booking()

    assert dao.insert_booking(booking) is True

    assert booking.id_booking == 5
    assert booking.booking_date == BOOKED_AT
    assert [t.id_ticket for t in booking.tickets] == [7, 8]
    assert all(t.id_booking == 5 for t in booking.tickets)
    assert cursor.execute.call_count == 4
    cursor.conn.close.assert_called_once()


def test_insert_booking_decreases_seats_by_number_of_tickets(dao, cursor):
    cursor.fetchone.side_effect = [
        {"available_seats": 48},
        {"id_booking": 5, "booking_date": BOOKED_AT},
        {"id_ticket": 7},
        {"id_ticket": 8},
    ]
    dao.insert_booking(make_booking())

    query, params = cursor.execute.call_args_list[0].args
    assert "UPDATE public.screening" in query
    assert "available_seats >= %(n)s" in query
    assert params == {"n": 2, "id_screening": 1}


def test_insert_booking_saves_total_and_ticket_prices(dao, cursor):
    cursor.fetchone.side_effect = [
        {"available_seats": 48},
        {"id_booking": 5, "booking_date": BOOKED_AT},
        {"id_ticket": 7},
        {"id_ticket": 8},
    ]
    dao.insert_booking(make_booking())

    booking_params = cursor.execute.call_args_list[1].args[1]
    assert booking_params["total"] == 8.5
    assert booking_params["seat_count"] == 2
    ticket_params = cursor.execute.call_args_list[3].args[1]
    assert (ticket_params["first_name"], ticket_params["tariff_code"], ticket_params["price"]) == ("Kid", "child", 4.5)


def test_insert_booking_not_enough_seats_writes_nothing(dao, cursor):
    cursor.fetchone.return_value = None

    booking = make_booking()
    assert dao.insert_booking(booking) is False

    assert cursor.execute.call_count == 1
    cursor.conn.rollback.assert_called_once()
    cursor.conn.close.assert_called_once()
    assert booking.id_booking is None


def test_insert_booking_db_error_is_raised_and_connection_closed(dao, cursor):
    cursor.execute.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.insert_booking(make_booking())
    cursor.conn.close.assert_called_once()


def test_insert_booking_without_returned_booking_row_is_an_error(dao, cursor):
    cursor.fetchone.side_effect = [{"available_seats": 48}, None]
    with pytest.raises(RuntimeError, match="booking was not created"):
        dao.insert_booking(make_booking())
    cursor.conn.close.assert_called_once()


def test_insert_booking_without_returned_ticket_row_is_an_error(dao, cursor):
    cursor.fetchone.side_effect = [{"available_seats": 48}, {"id_booking": 5, "booking_date": BOOKED_AT}, None]
    with pytest.raises(RuntimeError, match="ticket was not created"):
        dao.insert_booking(make_booking())
    cursor.conn.close.assert_called_once()


def test_cancel_booking_gives_seats_back(dao, cursor):
    cursor.fetchone.return_value = {"id_screening": 1, "seat_count": 3}

    assert dao.cancel_booking(5) is True

    assert cursor.execute.call_count == 2
    query, params = cursor.execute.call_args_list[1].args
    assert "available_seats + %(n)s" in query
    assert params == {"n": 3, "id_screening": 1}
    cursor.conn.close.assert_called_once()


def test_cancel_booking_not_found_or_already_cancelled(dao, cursor):
    cursor.fetchone.return_value = None
    assert dao.cancel_booking(5) is False
    assert cursor.execute.call_count == 1
    cursor.conn.close.assert_called_once()


def test_cancel_booking_db_error_is_raised(dao, cursor):
    cursor.execute.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.cancel_booking(5)
    cursor.conn.close.assert_called_once()


def test_find_by_customer_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.find_by_customer(10)


def test_count_booked_seats(sql_query):
    """SUM renvoie un Decimal avec psycopg2 : on le convertit en int."""
    sql_query.return_value = {"booked": Decimal("12")}

    assert BookingDao().count_booked_seats(3) == 12
    assert sql_query.call_args.kwargs["data"] == {"id": 3}
    assert sql_query.call_args.kwargs["return_type"] == "one"


def test_count_booked_seats_ignores_cancelled_bookings(sql_query):
    sql_query.return_value = {"booked": 0}

    BookingDao().count_booked_seats(3)

    assert "status = 'confirmed'" in sql_query.call_args.args[0]


def test_count_booked_seats_no_row_gives_zero(sql_query):
    sql_query.return_value = None

    assert BookingDao().count_booked_seats(3) == 0


def test_count_booked_seats_reraises_database_error(sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        BookingDao().count_booked_seats(3)
