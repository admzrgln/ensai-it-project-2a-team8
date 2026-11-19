from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.PriceRevision import PriceRevision
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class PriceRevisionDao(metaclass=Singleton):
    """Class containing methods to access the yearly price revisions in the database."""

    @staticmethod
    def _to_revision(row: dict) -> PriceRevision:
        return PriceRevision(
            year=row["year"],
            rate_percent=float(row["rate_percent"]),  # NUMERIC revient en Decimal
            applied_at=row["applied_at"],
        )

    # GET
    @log
    def find_all(self) -> list[PriceRevision]:
        query = "SELECT * FROM public.price_revision ORDER BY year;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_revision(r) for r in (res or [])]

    # POST / UPDATE : on crée ou on remplace une révision, tant qu'elle n'est pas appliquée
    @log
    def upsert_planned(self, revision: PriceRevision) -> bool:
        """Plan (or change the rate of) a revision. Returns False if it was already applied."""
        query = """
            INSERT INTO public.price_revision (year, rate_percent)
            VALUES (%(year)s, %(rate)s)
            ON CONFLICT (year) DO UPDATE SET rate_percent = EXCLUDED.rate_percent
            WHERE public.price_revision.applied_at IS NULL
            RETURNING year;
        """
        try:
            res = DBConnector().sql_query(
                query, data={"year": revision.year, "rate": revision.rate_percent}, return_type="one"
            )
        except Exception as e:
            logger.error(e)
            raise
        return res is not None

    # DELETE
    @log
    def delete_planned(self, year: int) -> bool:
        """Cancel a revision that has not been applied yet."""
        query = """
            DELETE FROM public.price_revision
            WHERE year = %(year)s AND applied_at IS NULL
            RETURNING year;
        """
        try:
            res = DBConnector().sql_query(query, data={"year": year}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return res is not None

    # APPLICATION
    @log
    def apply_due(self, up_to_year: int) -> list[int]:
        """Apply, in ONE transaction, every planned revision whose year is <= up_to_year.

        Prices are multiplied by (1 + rate / 100) and rounded to 0.10 EUR. The rows are locked
        (FOR UPDATE) and re-checked on applied_at, so two app instances starting at the same time
        can't apply the same revision twice. Returns the list of applied years (in order).
        """
        conn = DBConnector().get_connection()
        applied: list[int] = []
        try:
            with conn:  # COMMIT à la fin, ROLLBACK si une exception est levée
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT year, rate_percent FROM public.price_revision
                        WHERE applied_at IS NULL AND year <= %(year)s
                        ORDER BY year
                        FOR UPDATE;
                        """,
                        {"year": up_to_year},
                    )
                    for row in cur.fetchall():
                        cur.execute(
                            "UPDATE public.tariff SET price = ROUND(price * (1 + %(rate)s / 100.0) * 10) / 10;",
                            {"rate": row["rate_percent"]},
                        )
                        cur.execute(
                            "UPDATE public.price_revision SET applied_at = LOCALTIMESTAMP WHERE year = %(year)s;",
                            {"year": row["year"]},
                        )
                        applied.append(row["year"])
            return applied
        except Exception as e:
            logger.error(f"Erreur lors de l'application des révisions de prix : {e}")
            raise
        finally:
            conn.close()