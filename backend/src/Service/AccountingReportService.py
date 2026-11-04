from datetime import date

from backend.src.DAO.AccountingReportDAO import AccountingReportDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.AccountingReport import AccountingReport
from utils.log_utils import log


class AccountingReportService:
    """Class containing AccountingReport service methods (Business Logic Layer)"""

    def __init__(self, report_dao=None, user_dao=None):
        # DAOs can be injected: in unit tests we pass fake DAOs instead of
        # the real ones, so the tests never touch PostgreSQL.
        self.report_dao = report_dao or AccountingReportDao()
        self.user_dao = user_dao or UserDao()

    def _check_admin(self, id_admin: int) -> None:
        """Only an administrator can see the accounting (F3)."""
        user = self.user_dao.find_by_id(id_admin)
        if user is None:
            raise LookupError(f"User {id_admin} not found")
        if user.role != "admin":
            raise PermissionError("Only an administrator can generate an accounting report")

    @staticmethod
    def _check_period(period_start: date, period_end: date) -> None:
        if period_start > period_end:
            raise ValueError("period_start must be before or equal to period_end")

    @log
    def generate_report(self, period_start: date, period_end: date, id_admin: int) -> AccountingReport:
        """Build the accounting report of a period (both bounds inclusive).

        Raises
        ------
        ValueError       if the period is invalid
        LookupError      if the user does not exist
        PermissionError  if the user is not an administrator
        """
        self._check_period(period_start, period_end)
        self._check_admin(id_admin)

        movie_revenues = self.report_dao.find_movie_revenues(period_start, period_end)

        return AccountingReport(
            period_start=period_start,
            period_end=period_end,
            movie_revenues=movie_revenues,
            id_admin=id_admin,
        )
