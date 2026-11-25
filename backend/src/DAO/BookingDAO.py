from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Booking import Booking
from backend.src.Model.BookingStatus import BookingStatus
from backend.src.Model.Ticket import Ticket
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

if TYPE_CHECKING:
    from psycopg2.extensions import cursor

logger = get_logger(__name__)


def _fetch_row(cur: cursor) -> dict[str, Any] | None:
    """Fetch the next row of a cursor of a DBConnector connection.

    Parameters
    ----------
    cur : cursor
        A cursor of a connection opened by DBConnector.get_connection.

    Returns
    -------
    dict or None
        The row as a dict (RealDictCursor; the psycopg2 stubs say tuple), or None if there is no row.
    """
    return cast("dict[str, Any] | None", cur.fetchone())


class BookingDao(metaclass=Singleton):
    """Access to the bookings and their tickets in the database."""

    @staticmethod
    def _to_ticket(row: dict[str, Any]) -> Ticket:
        """Convert a row of the ticket table into a Ticket.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        Ticket
            The corresponding ticket (price converted from Decimal to float).
        """
        return Ticket(
            id_ticket=row["id_ticket"],
            id_booking=row["id_booking"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            date_of_birth=row["date_of_birth"],
            is_holder=row["is_holder"],
            is_ensai_student=row["is_ensai_student"],
            is_student=row["is_student"],
            tariff_code=row["tariff_code"],
            price=float(row["price"]),  # NUMERIC is read as Decimal
        )

    @staticmethod
    def _to_booking(row: dict[str, Any], tickets: list[Ticket]) -> Booking:
        """Convert a row of the booking table, and its tickets, into a Booking.

        Parameters
        ----------
        row : dict
            Row returned by the database.
        tickets : list of Ticket
            Tickets of the booking.

        Returns
        -------
        Booking
            The corresponding booking.
        """
        return Booking(
            id_booking=row["id_booking"],
            id_customer=row["id_customer"],
            id_screening=row["id_screening"],
            booking_date=row["booking_date"],
            status=BookingStatus(row["status"]),
            tickets=tickets,
        )

    def _find_tickets(self, id_booking: int) -> list[Ticket]:
        """List the tickets of a booking.

        Parameters
        ----------
        id_booking : int
            Identifier of the booking.

        Returns
        -------
        list of Ticket
            The tickets, in the order they were created.
        """
        query = "SELECT * FROM public.ticket WHERE id_booking = %(id)s ORDER BY id_ticket;"
        res = DBConnector().sql_query(query, data={"id": id_booking}, return_type="all")
        return [self._to_ticket(r) for r in (res or [])]

    # GET
    @log
    def find_by_id(self, id_booking: int) -> Booking | None:
        """Find a booking, with its tickets, by its identifier.

        Parameters
        ----------
        id_booking : int
            Identifier of the booking.

        Returns
        -------
        Booking or None
            The booking, or None if it does not exist.
        """
        query = "SELECT * FROM public.booking WHERE id_booking = %(id)s;"
        try:
            row = DBConnector().sql_query(query, data={"id": id_booking}, return_type="one")
            if not row:
                return None
            return self._to_booking(row, self._find_tickets(id_booking))
        except Exception as e:
            logger.error(e)
            raise

    @log
    def find_by_customer(self, id_customer: int) -> list[Booking]:
        """List the bookings of a customer, from the most recent.

        Parameters
        ----------
        id_customer : int
            Identifier of the customer.

        Returns
        -------
        list of Booking
            The bookings, with their tickets (empty list if there is none).
        """
        query = """
            SELECT * FROM public.booking
            WHERE id_customer = %(id)s
            ORDER BY booking_date DESC;
        """
        try:
            rows = DBConnector().sql_query(query, data={"id": id_customer}, return_type="all")
            return [self._to_booking(r, self._find_tickets(r["id_booking"])) for r in (rows or [])]
        except Exception as e:
            logger.error(e)
            raise

    @log
    def count_booked_seats(self, id_screening: int) -> int:
        """Count the seats booked for a screening (confirmed bookings only).

        Parameters
        ----------
        id_screening : int
            Identifier of the screening.

        Returns
        -------
        int
            Number of seats booked (0 if there is no booking).
        """
        query = """
            SELECT COALESCE(SUM(seat_count), 0) AS booked
            FROM public.booking
            WHERE id_screening = %(id)s AND status = 'confirmed';
        """
        try:
            res = DBConnector().sql_query(query, data={"id": id_screening}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return int(res["booked"]) if res else 0

    # POST
    @log
    def insert_booking(self, booking: Booking) -> bool:
        """Insert a booking and its tickets AND decrease the available seats, in one transaction.

        The condition `available_seats >= n` is checked by PostgreSQL itself in the UPDATE,
        so two customers booking the last seats at the same time can't both succeed.
        On success, the ids of the booking and of its tickets are filled.

        Parameters
        ----------
        booking : Booking
            The booking to save, with its priced tickets.

        Returns
        -------
        bool
            True if the booking was saved, False if there are not enough seats left
            (nothing is written in that case).
        """
        conn = DBConnector().get_connection()
        try:
            with conn:  # COMMIT at the end, ROLLBACK if an exception is raised
                with conn.cursor() as cur:
                    # 1. Take the seats (nothing happens if there are not enough left)
                    cur.execute(
                        """
                        UPDATE public.screening
                        SET available_seats = available_seats - %(n)s
                        WHERE id_screening = %(id_screening)s
                          AND available_seats >= %(n)s
                        RETURNING available_seats;
                        """,
                        {"n": booking.seat_count, "id_screening": booking.id_screening},
                    )
                    if _fetch_row(cur) is None:
                        conn.rollback()
                        return False

                    # 2. Create the booking
                    cur.execute(
                        """
                        INSERT INTO public.booking
                            (id_customer, id_screening, status, seat_count, total_price)
                        VALUES (%(id_customer)s, %(id_screening)s, %(status)s, %(seat_count)s, %(total)s)
                        RETURNING id_booking, booking_date;
                        """,
                        {
                            "id_customer": booking.id_customer,
                            "id_screening": booking.id_screening,
                            "status": booking.status,
                            "seat_count": booking.seat_count,
                            "total": booking.total_price,
                        },
                    )
                    row = _fetch_row(cur)
                    if row is None:  # impossible: INSERT ... RETURNING always returns a row
                        raise RuntimeError("The booking was not created")
                    booking.id_booking = row["id_booking"]
                    booking.booking_date = row["booking_date"]

                    # 3. Create one ticket per person
                    for t in booking.tickets:
                        cur.execute(
                            """
                            INSERT INTO public.ticket
                                (id_booking, first_name, last_name, date_of_birth, is_holder,
                                 is_ensai_student, is_student, tariff_code, price)
                            VALUES
                                (%(id_booking)s, %(first_name)s, %(last_name)s, %(date_of_birth)s, %(is_holder)s,
                                 %(is_ensai_student)s, %(is_student)s, %(tariff_code)s, %(price)s)
                            RETURNING id_ticket;
                            """,
                            {
                                "id_booking": booking.id_booking,
                                "first_name": t.first_name,
                                "last_name": t.last_name,
                                "date_of_birth": t.date_of_birth,
                                "is_holder": t.is_holder,
                                "is_ensai_student": t.is_ensai_student,
                                "is_student": t.is_student,
                                "tariff_code": t.tariff_code,
                                "price": t.price,
                            },
                        )
                        ticket_row = _fetch_row(cur)
                        if ticket_row is None:  # impossible: INSERT ... RETURNING always returns a row
                            raise RuntimeError("The ticket was not created")
                        t.id_ticket = ticket_row["id_ticket"]
                        t.id_booking = booking.id_booking
            return True
        except Exception as e:
            logger.error(f"Error while inserting the booking: {e}")
            raise
        finally:
            conn.close()

    # UPDATE (cancellation)
    @log
    def cancel_booking(self, id_booking: int) -> bool:
        """Mark a booking as cancelled and give its seats back to the screening (one transaction).

        Parameters
        ----------
        id_booking : int
            Identifier of the booking.

        Returns
        -------
        bool
            True if the booking was cancelled, False if it does not exist or is already cancelled.
        """
        conn = DBConnector().get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE public.booking SET status = 'cancelled'
                        WHERE id_booking = %(id)s AND status = 'confirmed'
                        RETURNING id_screening, seat_count;
                        """,
                        {"id": id_booking},
                    )
                    row = _fetch_row(cur)
                    if row is None:
                        return False
                    cur.execute(
                        """
                        UPDATE public.screening
                        SET available_seats = available_seats + %(n)s
                        WHERE id_screening = %(id_screening)s;
                        """,
                        {"n": row["seat_count"], "id_screening": row["id_screening"]},
                    )
            return True
        except Exception as e:
            logger.error(f"Error while cancelling the booking: {e}")
            raise
        finally:
            conn.close()
