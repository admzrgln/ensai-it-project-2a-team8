from __future__ import annotations

from typing import Any, cast

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.PriceRevision import PriceRevision
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class PriceRevisionDao(metaclass=Singleton):
    """Access to the yearly price revisions in the database."""

    @staticmethod
    def _to_revision(row: dict[str, Any]) -> PriceRevision:
        """Convert a row of the price_revision table into a PriceRevision.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        PriceRevision
            The corresponding revision (rate converted from Decimal to float).
        """
        return PriceRevision(
            year=row["year"],
            rate_percent=float(row["rate_percent"]),  # NUMERIC is read as Decimal
            applied_at=row["applied_at"],
        )

    # GET
    @log
    def find_all(self) -> list[PriceRevision]:
        """List the planned and applied revisions, by year.

        Returns
        -------
        list of PriceRevision
            The revisions (empty list if there is none).
        """
        query = "SELECT * FROM public.price_revision ORDER BY year;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_revision(r) for r in (res or [])]

    # POST / UPDATE: create or replace a revision, as long as it is not applied
    @log
    def upsert_planned(self, revision: PriceRevision) -> bool:
        """Plan a revision, or change its rate if it is not applied yet.

        Parameters
        ----------
        revision : PriceRevision
            The revision (year and rate) to plan.

        Returns
        -------
        bool
            True if the revision was saved, False if this year's revision was already applied.
        """
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
        """Cancel a revision that has not been applied yet.

        Parameters
        ----------
        year : int
            Year of the revision.

        Returns
        -------
        bool
            True if the revision was cancelled, False if it does not exist or was already applied.
        """
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

    # APPLY
    @log
    def apply_due(self, up_to_year: int) -> list[int]:
        """Apply, in ONE transaction, every planned revision whose year is <= up_to_year.

        Prices are multiplied by (1 + rate / 100) and rounded to 0.10 EUR. The rows are locked
        (FOR UPDATE) and re-checked on applied_at, so two app instances starting at the same time
        can't apply the same revision twice.

        Parameters
        ----------
        up_to_year : int
            Last year whose revision must be applied (usually the current year).

        Returns
        -------
        list of int
            The years of the revisions applied, in order (empty if there was none).
        """
        conn = DBConnector().get_connection()
        applied: list[int] = []
        try:
            with conn:  # COMMIT at the end, ROLLBACK if an exception is raised
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
                    # RealDictCursor: each row is a dict (the psycopg2 stubs say tuple)
                    for row in cast("list[dict[str, Any]]", cur.fetchall()):
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
            logger.error(f"Error while applying the price revisions: {e}")
            raise
        finally:
            conn.close()
