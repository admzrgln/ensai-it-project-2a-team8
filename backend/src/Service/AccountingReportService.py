from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.DAO.AccountingReportDAO import AccountingReportDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.AccountingReport import AccountingReport
from utils.log_utils import log

if TYPE_CHECKING:
    from datetime import date


class AccountingReportService:
    """Business rules of the accounting reports (F3).

    Parameters
    ----------
    report_dao : AccountingReportDao or None, optional
        DAO of the accounting queries. Can be replaced by a fake DAO in unit tests,
        so that the tests never touch PostgreSQL.
    user_dao : UserDao or None, optional
        DAO of the users (same remark).
    """

    def __init__(self, report_dao: AccountingReportDao | None = None, user_dao: UserDao | None = None) -> None:
        self.report_dao: AccountingReportDao = report_dao or AccountingReportDao()
        self.user_dao: UserDao = user_dao or UserDao()

    def _check_admin(self, id_admin: int) -> None:
        """Check that the user is an administrator (only them can see the accounting).

        Parameters
        ----------
        id_admin : int
            Identifier of the user asking for the report.

        Raises
        ------
        LookupError
            If the user does not exist.
        PermissionError
            If the user is not an administrator.
        """
        user = self.user_dao.find_by_id(id_admin)
        if user is None:
            raise LookupError(f"User {id_admin} not found")
        if user.role != "admin":
            raise PermissionError("Only an administrator can generate an accounting report")

    @staticmethod
    def _check_period(period_start: date, period_end: date) -> None:
        """Check that the period is valid.

        Parameters
        ----------
        period_start : date
            First day of the period.
        period_end : date
            Last day of the period.

        Raises
        ------
        ValueError
            If period_start is after period_end.
        """
        if period_start > period_end:
            raise ValueError("period_start must be before or equal to period_end")

    @log
    def generate_report(self, period_start: date, period_end: date, id_admin: int) -> AccountingReport:
        """Build the accounting report of a period (both bounds inclusive): revenue and occupancy.

        Parameters
        ----------
        period_start : date
            First day of the period.
        period_end : date
            Last day of the period.
        id_admin : int
            Identifier of the administrator asking for the report.

        Returns
        -------
        AccountingReport
            The report, with its totals.

        Raises
        ------
        ValueError
            If the period is invalid.
        LookupError
            If the user does not exist.
        PermissionError
            If the user is not an administrator.
        """
        self._check_period(period_start, period_end)
        self._check_admin(id_admin)

        movie_revenues = self.report_dao.find_movie_revenues(period_start, period_end)
        movie_occupancies = self.report_dao.find_movie_occupancy(period_start, period_end)

        return AccountingReport(
            period_start=period_start,
            period_end=period_end,
            movie_revenues=movie_revenues,
            id_admin=id_admin,
            movie_occupancies=movie_occupancies,
        )
