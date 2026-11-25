from __future__ import annotations

from typing import Any

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Tariff import Tariff
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class TariffDao(metaclass=Singleton):
    """Access to the price grid (tariff table) in the database."""

    @staticmethod
    def _to_tariff(row: dict[str, Any]) -> Tariff:
        """Convert a row of the tariff table into a Tariff.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        Tariff
            The corresponding tariff (price converted from Decimal to float).
        """
        return Tariff(
            code=row["code"],
            label=row["label"],
            price=float(row["price"]),
            min_age=row["min_age"],
            max_age=row["max_age"],
            requires_ensai=row["requires_ensai"],
            requires_student=row["requires_student"],
            is_active=row["is_active"],
            weekday=row.get("weekday"),
            time_from=row.get("time_from"),
            time_until=row.get("time_until"),
        )

    @staticmethod
    def _to_data(tariff: Tariff) -> dict[str, Any]:
        """Convert a Tariff into the values of the placeholders of the SQL queries.

        Parameters
        ----------
        tariff : Tariff
            The tariff to convert.

        Returns
        -------
        dict
            One entry per column of the tariff table.
        """
        return {
            "code": tariff.code,
            "label": tariff.label,
            "price": tariff.price,
            "min_age": tariff.min_age,
            "max_age": tariff.max_age,
            "requires_ensai": tariff.requires_ensai,
            "requires_student": tariff.requires_student,
            "is_active": tariff.is_active,
            "weekday": tariff.weekday,
            "time_from": tariff.time_from,
            "time_until": tariff.time_until,
        }

    # GET
    @log
    def find_all(self, only_active: bool = True) -> list[Tariff]:
        """List the tariffs, from the cheapest to the most expensive.

        Parameters
        ----------
        only_active : bool, optional
            If True (default), the deactivated tariffs are left out.

        Returns
        -------
        list of Tariff
            The tariffs (empty list if there is none).
        """
        query = "SELECT * FROM public.tariff"
        if only_active:
            query += " WHERE is_active"
        query += " ORDER BY price, code;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_tariff(r) for r in (res or [])]

    @log
    def find_by_code(self, code: str) -> Tariff | None:
        """Find a tariff by its code, active or not.

        Parameters
        ----------
        code : str
            Code of the tariff.

        Returns
        -------
        Tariff or None
            The tariff, or None if it does not exist.
        """
        query = "SELECT * FROM public.tariff WHERE code = %(code)s;"
        try:
            res = DBConnector().sql_query(query, data={"code": code}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_tariff(res) if res else None

    # POST
    @log
    def insert_tariff(self, tariff: Tariff) -> bool:
        """Insert a new tariff.

        Parameters
        ----------
        tariff : Tariff
            The tariff to insert.

        Returns
        -------
        bool
            True if the tariff was inserted, False otherwise (e.g. code already used).
        """
        query = """
            INSERT INTO public.tariff
                (code, label, price, min_age, max_age, requires_ensai, requires_student, is_active,
                 weekday, time_from, time_until)
            VALUES
                (%(code)s, %(label)s, %(price)s, %(min_age)s, %(max_age)s,
                 %(requires_ensai)s, %(requires_student)s, %(is_active)s,
                 %(weekday)s, %(time_from)s, %(time_until)s)
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data=self._to_data(tariff), return_type="one"))
        except Exception as e:
            logger.error(f"Error while inserting the tariff: {e}")
        return False

    # UPDATE
    @log
    def update_tariff(self, tariff: Tariff) -> bool:
        """Update a tariff, found by its code.

        Parameters
        ----------
        tariff : Tariff
            The tariff with its new values.

        Returns
        -------
        bool
            True if the tariff was updated, False otherwise.
        """
        query = """
            UPDATE public.tariff
            SET label = %(label)s, price = %(price)s, min_age = %(min_age)s, max_age = %(max_age)s,
                requires_ensai = %(requires_ensai)s, requires_student = %(requires_student)s,
                is_active = %(is_active)s,
                weekday = %(weekday)s, time_from = %(time_from)s, time_until = %(time_until)s
            WHERE code = %(code)s
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data=self._to_data(tariff), return_type="one"))
        except Exception as e:
            logger.error(f"Error while updating the tariff: {e}")
        return False

    @log
    def deactivate_tariff(self, code: str) -> bool:
        """Deactivate a tariff (it is kept for the tickets already sold).

        Parameters
        ----------
        code : str
            Code of the tariff.

        Returns
        -------
        bool
            True if the tariff was deactivated, False if it does not exist or is already inactive.
        """
        query = """
            UPDATE public.tariff SET is_active = FALSE
            WHERE code = %(code)s AND is_active
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data={"code": code}, return_type="one"))
        except Exception as e:
            logger.error(f"Error while deactivating the tariff: {e}")
        return False
