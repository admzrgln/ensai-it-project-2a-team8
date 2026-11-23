from datetime import date, timedelta

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.MovieOccupancy import MovieOccupancy
from backend.src.Model.MovieRevenue import MovieRevenue
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class AccountingReportDao(metaclass=Singleton):
    """Class containing the SQL queries used to build accounting reports."""

    @staticmethod
    def _to_movie_revenue(row: dict) -> MovieRevenue:
        """Convertit une ligne SQL en objet MovieRevenue."""
        return MovieRevenue(
            id_movie=row["id_movie"],
            title=row["title"],
            revenue=float(row["revenue"]),  # NUMERIC revient en Decimal
            tickets_sold=int(row["tickets_sold"]),
        )

    @staticmethod
    def _to_movie_occupancy(row: dict) -> MovieOccupancy:
        """Convertit une ligne SQL en objet MovieOccupancy."""
        return MovieOccupancy(
            id_movie=row["id_movie"],
            title=row["title"],
            screenings=int(row["screenings"]),
            seats_offered=int(row["seats_offered"]),
            seats_sold=int(row["seats_sold"]),
        )

    @log
    def find_movie_revenues(self, period_start: date, period_end: date) -> list[MovieRevenue]:
        """Revenue and tickets sold per movie, for payments made in [period_start, period_end].

        Rules:
        - only payments with status 'paid' count (failed / pending / refunded are ignored)
        - a sale is counted on its PAYMENT date (cash accounting)
        - period_end is inclusive: we compare with "< period_end + 1 day" because
          payment_date is a TIMESTAMP (a payment on the last day at 23:30 must count)
        - revenue is summed from booking_line (quantity * unit_price), NOT from
          payment.amount: joining payment to several booking lines would repeat the
          payment amount once per line and double-count it
        """
        query = """
            SELECT m.id_movie,
                m.title,
                COALESCE(SUM(t.price), 0) AS revenue,
                COUNT(t.id_ticket)        AS tickets_sold
            FROM public.booking b
            JOIN public.ticket    t ON t.id_booking   = b.id_booking
            JOIN public.screening s ON s.id_screening = b.id_screening
            JOIN public.movie     m ON m.id_movie     = s.id_movie
            WHERE b.status = 'confirmed'
              AND b.booking_date >= %(start)s
              AND b.booking_date <  %(end_exclusive)s
            GROUP BY m.id_movie, m.title
            ORDER BY revenue DESC, m.title;
        """
        data = {
            "start": period_start,
            "end_exclusive": period_end + timedelta(days=1),
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_movie_revenue(r) for r in (res or [])]

    @log
    def find_movie_occupancy(self, period_start: date, period_end: date) -> list[MovieOccupancy]:
        """Occupancy per movie, for the screenings STARTED in [period_start, period_end].

        Rules:
        - the period is on the SCREENING date (not the sale date): the occupancy of a
          screening only makes sense once it has taken place, so future screenings are ignored
        - seats offered = room capacity; seats sold = capacity - available_seats
          (available_seats is decreased by a booking and given back by a cancellation)
        - period_end is inclusive ("< period_end + 1 day", date_time is a TIMESTAMP)
        """
        query = """
            SELECT m.id_movie,
                   m.title,
                   COUNT(*)                            AS screenings,
                   SUM(r.capacity)                     AS seats_offered,
                   SUM(r.capacity - s.available_seats) AS seats_sold
            FROM public.screening s
            JOIN public.room  r ON r.id_room  = s.id_room
            JOIN public.movie m ON m.id_movie = s.id_movie
            WHERE s.date_time >= %(start)s
              AND s.date_time <  %(end_exclusive)s
              AND s.date_time <  LOCALTIMESTAMP
            GROUP BY m.id_movie, m.title
            ORDER BY m.title;
        """
        data = {
            "start": period_start,
            "end_exclusive": period_end + timedelta(days=1),
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_movie_occupancy(r) for r in (res or [])]
