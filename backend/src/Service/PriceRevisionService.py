from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from backend.src.DAO.PriceRevisionDAO import PriceRevisionDao
from backend.src.Model.PriceRevision import PriceRevision
from utils.log_utils import log

if TYPE_CHECKING:
    from datetime import date

# The server may run in UTC: "midnight on January 1st" is the one of the cinema (Bruz).
# On Windows, ZoneInfo needs the `tzdata` package (pdm add tzdata).
CINEMA_TZ = ZoneInfo("Europe/Paris")

MAX_RATE_PERCENT = 10.0


class PriceRevisionError(Exception):
    """A business rule on the price revisions is not respected (the message is sent to the client)."""


class PriceRevisionService:
    """Yearly price increase: the admin plans a rate, it is applied on January 1st at midnight.

    Parameters
    ----------
    revision_dao : PriceRevisionDao or None, optional
        DAO of the revisions (can be replaced by a fake DAO in unit tests).
    """

    def __init__(self, revision_dao: PriceRevisionDao | None = None) -> None:
        self.revision_dao: PriceRevisionDao = revision_dao or PriceRevisionDao()

    @staticmethod
    def today() -> date:
        """Today's date in the time zone of the cinema (the server may run in UTC).

        Returns
        -------
        date
            Today's date in Europe/Paris.
        """
        return datetime.now(CINEMA_TZ).date()

    @log
    def find_all(self) -> list[PriceRevision]:
        """List the planned and applied revisions.

        Returns
        -------
        list of PriceRevision
            The revisions, by year.
        """
        return self.revision_dao.find_all()

    @log
    def plan_revision(self, year: int, rate_percent: float, today: date | None = None) -> PriceRevision:
        """Plan (or change) the increase of a FUTURE year.

        Parameters
        ----------
        year : int
            Year of the increase (must be after the current year).
        rate_percent : float
            Increase in percent, between 0 and MAX_RATE_PERCENT.
        today : date or None, optional
            Today's date (useful in tests); today in Europe/Paris if None.

        Returns
        -------
        PriceRevision
            The planned revision.

        Raises
        ------
        PriceRevisionError
            If the year is not in the future, the rate is out of bounds,
            or this year's revision was already applied.
        """
        today = today or self.today()
        if year <= today.year:
            raise PriceRevisionError(f"A revision can only be planned for a future year (current year: {today.year})")
        if not 0 <= rate_percent <= MAX_RATE_PERCENT:
            raise PriceRevisionError(f"The rate must be between 0 and {MAX_RATE_PERCENT:g} %")
        revision = PriceRevision(year, round(rate_percent, 2))
        if not self.revision_dao.upsert_planned(revision):
            raise PriceRevisionError(f"The {year} revision has already been applied")
        return revision

    @log
    def cancel_revision(self, year: int) -> bool:
        """Cancel a revision that has not been applied yet.

        Parameters
        ----------
        year : int
            Year of the revision.

        Returns
        -------
        bool
            True when the revision is cancelled.

        Raises
        ------
        PriceRevisionError
            If the revision does not exist or was already applied.
        """
        if not self.revision_dao.delete_planned(year):
            raise PriceRevisionError(f"Revision {year} not found or already applied")
        return True

    @log
    def apply_due_revisions(self, today: date | None = None) -> list[int]:
        """Apply every planned revision whose year has started.

        Safe to call as often as wanted: an applied revision is never applied again,
        and a missed January 1st is caught up.

        Parameters
        ----------
        today : date or None, optional
            Today's date (useful in tests); today in Europe/Paris if None.

        Returns
        -------
        list of int
            The years of the revisions applied now.
        """
        today = today or self.today()
        return self.revision_dao.apply_due(today.year)
