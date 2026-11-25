from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.MovieOccupancy import MovieOccupancy
from backend.src.Model.MovieRevenue import MovieRevenue
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

if TYPE_CHECKING:
    from datetime import date

logger = get_logger(__name__)


class AccountingReportDao(metaclass=Singleton):
    """SQL queries used to build the accounting reports."""

    @staticmethod
    def _to_movie_revenue(row: dict[str, Any]) -> MovieRevenue:
        """Convert a row of the revenue query into a MovieRevenue.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        MovieRevenue
            The revenue of the movie (Decimal converted to float).
        """
        return MovieRevenue(
            id_movie=row["id_movie"],
            title=row["title"],
            revenue=float(row["revenue"]),  # NUMERIC is read as Decimal
            tickets_sold=int(row["tickets_sold"]),
        )

    @staticmethod
    def _to_movie_occupancy(row: dict[str, Any]) -> MovieOccupancy:
        """Convert a row of the occupancy query into a MovieOccupancy.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        MovieOccupancy
            The occupancy of the movie.
        """
        return MovieOccupancy(
            id_movie=row["id_movie"],
            title=row["title"],
            screenings=int(row["screenings"]),
            seats_offered=int(row["seats_offered"]),
            seats_sold=int(row["seats_sold"]),
        )

    @log
    def find_movie_revenues(self, period_start: date, period_end: date) -> list[MovieRevenue]:
        """Revenue and tickets sold per movie, for the tickets SOLD in [period_start, period_end].

        Rules:
        - one row of `ticket` = one seat sold; ticket.price is the price actually paid
          (it does not change if an administrator modifies the price grid afterwards)
        - only 'confirmed' bookings count (cancelled bookings are ignored)
        - a sale is counted on the BOOKING date: that is when the cinema gets the money
          (occupancy, on the contrary, is counted on the screening date: see find_movie_occupancy)
        - period_end is inclusive: "< period_end + 1 day" because booking_date is a TIMESTAMP

        Parameters
        ----------
        period_start : date
            First day of the period (inclusive).
        period_end : date
            Last day of the period (inclusive).

        Returns
        -------
        list of MovieRevenue
            One line per movie with at least one ticket sold, from the highest revenue.
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

        Parameters
        ----------
        period_start : date
            First day of the period (inclusive).
        period_end : date
            Last day of the period (inclusive).

        Returns
        -------
        list of MovieOccupancy
            One line per movie with at least one screening already started, by title.
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
