from datetime import date

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Booking import Booking
from backend.src.Model.Ticket import Ticket
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class BookingDao(metaclass=Singleton):
    """Class containing methods to access Bookings and Tickets in the database."""

    @staticmethod
    def _to_ticket(row: dict) -> Ticket:
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
            price=float(row["price"]),  # NUMERIC revient en Decimal
        )

    @staticmethod
    def _to_booking(row: dict, tickets: list[Ticket]) -> Booking:
        return Booking(
            id_booking=row["id_booking"],
            id_customer=row["id_customer"],
            id_screening=row["id_screening"],
            booking_date=row["booking_date"],
            status=row["status"],
            tickets=tickets,
        )

    def _find_tickets(self, id_booking: int) -> list[Ticket]:
        query = "SELECT * FROM public.ticket WHERE id_booking = %(id)s ORDER BY id_ticket;"
        res = DBConnector().sql_query(query, data={"id": id_booking}, return_type="all")
        return [self._to_ticket(r) for r in (res or [])]

    # GET
    @log
    def find_by_id(self, id_booking: int) -> Booking | None:
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
        """Nombre de places réservées (réservations confirmées) pour une séance."""
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

        Returns False if there are not enough seats left (nothing is written in that case).
        The condition `available_seats >= n` is checked by PostgreSQL itself in the UPDATE,
        so two customers booking the last seats at the same time can't both succeed.
        """
        conn = DBConnector().get_connection()
        try:
            with conn:  # COMMIT à la fin si tout va bien, ROLLBACK si une exception est levée
                with conn.cursor() as cur:
                    # 1. Réserver les places (échoue proprement s'il n'en reste pas assez)
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
                    if cur.fetchone() is None:
                        conn.rollback()
                        return False

                    # 2. Créer la réservation
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
                    row = cur.fetchone()
                    booking.id_booking = row["id_booking"]
                    booking.booking_date = row["booking_date"]

                    # 3. Créer un billet par personne
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
                        t.id_ticket = cur.fetchone()["id_ticket"]
                        t.id_booking = booking.id_booking
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion de la réservation : {e}")
            raise
        finally:
            conn.close()

    # UPDATE (annulation)
    @log
    def cancel_booking(self, id_booking: int) -> bool:
        """Mark a booking as cancelled and give its seats back to the screening (one transaction)."""
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
                    row = cur.fetchone()
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
            logger.error(f"Erreur lors de l'annulation de la réservation : {e}")
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # COMPTABILITÉ (F3) : à appeler depuis AccountingReportService
    # Période = date de la réservation (date de la vente), bornes incluses.
    # Seules les réservations 'confirmed' sont comptées.
    # ------------------------------------------------------------------
    @log
    def revenue_by_movie(self, period_start: date, period_end: date) -> list[dict]:
        """[{id_movie, title, tickets_sold, revenue}, ...] sur la période."""
        query = """
            SELECT m.id_movie, m.title,
                   COUNT(t.id_ticket)          AS tickets_sold,
                   COALESCE(SUM(t.price), 0)   AS revenue
            FROM public.booking b
            JOIN public.ticket t    ON t.id_booking = b.id_booking
            JOIN public.screening s ON s.id_screening = b.id_screening
            JOIN public.movie m     ON m.id_movie = s.id_movie
            WHERE b.status = 'confirmed'
              AND b.booking_date >= %(start)s
              AND b.booking_date <  %(end)s::date + 1
            GROUP BY m.id_movie, m.title
            ORDER BY revenue DESC;
        """
        try:
            rows = DBConnector().sql_query(
                query, data={"start": period_start, "end": period_end}, return_type="all"
            )
        except Exception as e:
            logger.error(e)
            raise
        return [
            {"id_movie": r["id_movie"], "title": r["title"],
             "tickets_sold": r["tickets_sold"], "revenue": float(r["revenue"])}
            for r in (rows or [])
        ]

    @log
    def revenue_by_tariff(self, period_start: date, period_end: date) -> list[dict]:
        """[{tariff_code, tickets_sold, revenue}, ...] sur la période."""
        query = """
            SELECT t.tariff_code,
                   COUNT(t.id_ticket)        AS tickets_sold,
                   COALESCE(SUM(t.price), 0) AS revenue
            FROM public.booking b
            JOIN public.ticket t ON t.id_booking = b.id_booking
            WHERE b.status = 'confirmed'
              AND b.booking_date >= %(start)s
              AND b.booking_date <  %(end)s::date + 1
            GROUP BY t.tariff_code
            ORDER BY revenue DESC;
        """
        try:
            rows = DBConnector().sql_query(
                query, data={"start": period_start, "end": period_end}, return_type="all"
            )
        except Exception as e:
            logger.error(e)
            raise
        return [
            {"tariff_code": r["tariff_code"], "tickets_sold": r["tickets_sold"], "revenue": float(r["revenue"])}
            for r in (rows or [])
        ]
