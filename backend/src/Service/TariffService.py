from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.DAO.TariffDAO import TariffDao
from utils.log_utils import log

if TYPE_CHECKING:
    from datetime import date, datetime

    from backend.src.Model.Tariff import Tariff
    from backend.src.Model.Ticket import Ticket

# Full price: no condition and can't be deactivated, so it always applies
FULL_TARIFF_CODE = "full"


class TariffError(Exception):
    """A business rule on the price grid is not respected (the message is sent to the client)."""


def compute_age(date_of_birth: date, on_date: date) -> int:
    """Compute the age of a person on a given date.

    Parameters
    ----------
    date_of_birth : date
        Date of birth.
    on_date : date
        Date on which the age is computed (the day of the screening).

    Returns
    -------
    int
        Age in completed years (minus 1 if the birthday has not passed yet that year).
    """
    age = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


class TariffService:
    """Price grid management (administrators) and ticket pricing (bookings)."""

    def __init__(self) -> None:
        self.tariff_dao: TariffDao = TariffDao()

    def price_ticket(self, ticket: Ticket, screening_dt: datetime, tariffs: list[Tariff] | None = None) -> Ticket:
        """Fill ticket.tariff_code and ticket.price with the cheapest tariff the person is entitled to.

        Parameters
        ----------
        ticket : Ticket
            The ticket to price.
        screening_dt : datetime
            Date AND time of the screening: the age is computed on the day of the screening,
            and the schedule tariffs (e.g. "Wednesday afternoon") depend on its start time.
        tariffs : list of Tariff or None, optional
            Price grid already loaded (avoids reading the database for each ticket).

        Returns
        -------
        Ticket
            The same ticket, priced.

        Raises
        ------
        TariffError
            If no tariff applies (the full tariff is missing from the grid).
        """
        if tariffs is None:
            tariffs = self.tariff_dao.find_all(only_active=True)
        age = compute_age(ticket.date_of_birth, screening_dt.date())

        eligible = [t for t in tariffs if t.is_eligible(age, ticket.is_ensai_student, ticket.is_student, screening_dt)]
        if not eligible:
            raise TariffError(f"No tariff applies: the '{FULL_TARIFF_CODE}' tariff is missing from the grid")
        best = min(eligible, key=lambda t: t.price)

        ticket.tariff_code = best.code
        ticket.price = round(best.price, 2)
        return ticket

    def _check(self, tariff: Tariff) -> None:
        """Check the rules of a tariff before saving it.

        Parameters
        ----------
        tariff : Tariff
            The tariff to check.

        Raises
        ------
        TariffError
            If a value is invalid (price, ages, day, times) or if the full tariff
            is deactivated or given a condition.
        """
        if not tariff.code or not tariff.label:
            raise TariffError("Code and label are required")
        if tariff.price is None or tariff.price < 0:
            raise TariffError("Price must be positive")
        for age in (tariff.min_age, tariff.max_age):
            if age is not None and age < 0:
                raise TariffError("Ages must be positive")
        if tariff.min_age is not None and tariff.max_age is not None and tariff.min_age > tariff.max_age:
            raise TariffError("min_age must be lower than max_age")
        if tariff.weekday is not None and not 0 <= tariff.weekday <= 6:
            raise TariffError("weekday must be between 0 (Monday) and 6 (Sunday)")
        if tariff.time_from is not None and tariff.time_until is not None and tariff.time_from >= tariff.time_until:
            raise TariffError("time_from must be before time_until")
        if tariff.code == FULL_TARIFF_CODE and not tariff.is_active:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff can't be deactivated")
        if tariff.code == FULL_TARIFF_CODE and tariff.has_conditions:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff must apply to everyone (no condition)")

    @log
    def find_all(self, only_active: bool = True) -> list[Tariff]:
        """List the tariffs, from the cheapest.

        Parameters
        ----------
        only_active : bool, optional
            If True (default), the deactivated tariffs are left out.

        Returns
        -------
        list of Tariff
            The tariffs.
        """
        return self.tariff_dao.find_all(only_active)

    @log
    def find_by_code(self, code: str) -> Tariff | None:
        """Find a tariff by its code.

        Parameters
        ----------
        code : str
            Code of the tariff.

        Returns
        -------
        Tariff or None
            The tariff, or None if it does not exist.
        """
        return self.tariff_dao.find_by_code(code)

    @log
    def create_tariff(self, tariff: Tariff) -> Tariff:
        """Check and create a new tariff.

        Parameters
        ----------
        tariff : Tariff
            The tariff to create.

        Returns
        -------
        Tariff
            The tariff created.

        Raises
        ------
        TariffError
            If the tariff is invalid, its code is already used or the insertion failed.
        """
        self._check(tariff)
        if self.tariff_dao.find_by_code(tariff.code) is not None:
            raise TariffError(f"Tariff '{tariff.code}' already exists")
        if not self.tariff_dao.insert_tariff(tariff):
            raise TariffError("Creation failed")
        return tariff

    @log
    def update_tariff(self, tariff: Tariff) -> Tariff:
        """Check and update a tariff; tickets already sold keep their price.

        Parameters
        ----------
        tariff : Tariff
            The tariff with its new values (found by its code).

        Returns
        -------
        Tariff
            The tariff updated.

        Raises
        ------
        TariffError
            If the tariff is invalid, does not exist or the update failed.
        """
        self._check(tariff)
        if self.tariff_dao.find_by_code(tariff.code) is None:
            raise TariffError("Tariff not found")
        if not self.tariff_dao.update_tariff(tariff):
            raise TariffError("Update failed")
        return tariff

    @log
    def deactivate_tariff(self, code: str) -> bool:
        """Deactivate a tariff (kept for the history of the tickets sold).

        Parameters
        ----------
        code : str
            Code of the tariff.

        Returns
        -------
        bool
            True when the tariff is deactivated.

        Raises
        ------
        TariffError
            If it is the full tariff, or the tariff does not exist or is already inactive.
        """
        if code == FULL_TARIFF_CODE:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff can't be deactivated")
        if not self.tariff_dao.deactivate_tariff(code):
            raise TariffError("Tariff not found or already inactive")
        return True
