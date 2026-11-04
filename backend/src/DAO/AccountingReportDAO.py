from datetime import date, timedelta

from backend.src.DAO.DBConnector import DBConnector
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
                   SUM(bl.quantity * bl.unit_price) AS revenue,
                   SUM(bl.quantity)                 AS tickets_sold
            FROM payment p
            JOIN booking      b  ON b.id_payment   = p.id_payment
            JOIN booking_line bl ON bl.id_booking  = b.id_booking
            JOIN screening    s  ON s.id_screening = b.id_screening
            JOIN movie        m  ON m.id_movie     = s.id_movie
            WHERE p.status = 'paid'
              AND p.payment_date >= %(start)s
              AND p.payment_date <  %(end_exclusive)s
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
