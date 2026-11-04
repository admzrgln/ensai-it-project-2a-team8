"""Unit tests of AccountingReportService.

The DAOs are replaced by fakes, so these tests run without PostgreSQL.
The fake rows reproduce what fake_accounting_db.sql should return for
October 2026, so the same expected numbers are checked here and in the database.

What we test here is the business logic only:
- the checks (valid period, user exists, user is an admin) and their ORDER
- that the DAO is called with the right period, and only when the checks pass
- that the report is built from what the DAO returns
"""
from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.src.Model.AccountingReport import AccountingReport
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Model.MovieRevenue import MovieRevenue
from backend.src.Service.AccountingReportService import AccountingReportService

OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)
ADMIN_ID, CUSTOMER_ID, UNKNOWN_ID = 1, 2, 999


class FakeUserDao:
    """Uses the real model classes, so `role` is set exactly as UserDao would set it."""

    users = {
        ADMIN_ID: Administrator(ADMIN_ID, "Ada", "Admin", "admin@cine.fr", "x", date(1990, 1, 1)),
        CUSTOMER_ID: Customer(CUSTOMER_ID, "Carl", "Client", "carl@mail.fr", "x", date(2000, 1, 1)),
    }

    def find_by_id(self, id_user):
        return self.users.get(id_user)


class FakeReportDao:
    """Returns the October 2026 per-movie figures of the fake database and records its calls."""

    def __init__(self, rows=None):
        self.rows = (
            rows
            if rows is not None
            else [
                MovieRevenue(id_movie=2, title="Oppenheimer", revenue=44.40, tickets_sold=4),
                MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36.00, tickets_sold=4),
            ]
        )
        self.calls = []

    def find_movie_revenues(self, period_start, period_end):
        self.calls.append((period_start, period_end))
        return self.rows


def make_service(rows=None) -> AccountingReportService:
    return AccountingReportService(report_dao=FakeReportDao(rows), user_dao=FakeUserDao())


def test_report_totals_match_fake_database():
    report = make_service().generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)

    assert isinstance(report, AccountingReport)
    assert report.total_amount == pytest.approx(80.40)
    assert report.tickets_sold == 8
    assert report.average_ticket_price == pytest.approx(10.05)
    assert [m.title for m in report.movie_revenues] == ["Oppenheimer", "Dune: Part Two"]


def test_report_keeps_period_and_admin():
    report = make_service().generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)

    assert (report.period_start, report.period_end) == (OCT_START, OCT_END)
    assert report.id_admin == ADMIN_ID
    assert report.id_report is None  # computed on demand, not saved


def test_period_is_passed_to_dao_once():
    service = make_service()

    service.generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)

    assert service.report_dao.calls == [(OCT_START, OCT_END)]


def test_empty_period_gives_zero_and_no_division_by_zero():
    report = make_service(rows=[]).generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)

    assert report.total_amount == 0
    assert report.tickets_sold == 0
    assert report.average_ticket_price == 0.0


def test_single_day_period_is_allowed():
    day = date(2026, 10, 5)

    report = make_service().generate_report(day, day, id_admin=ADMIN_ID)

    assert report.period_start == report.period_end == day


def test_inverted_period_is_refused():
    with pytest.raises(ValueError, match="period_start"):
        make_service().generate_report(OCT_END, OCT_START, id_admin=ADMIN_ID)


def test_customer_cannot_see_accounting():
    with pytest.raises(PermissionError):
        make_service().generate_report(OCT_START, OCT_END, id_admin=CUSTOMER_ID)


def test_unknown_user_is_refused():
    with pytest.raises(LookupError, match=str(UNKNOWN_ID)):
        make_service().generate_report(OCT_START, OCT_END, id_admin=UNKNOWN_ID)


@pytest.mark.parametrize(
    "start, end, id_admin",
    [
        pytest.param(OCT_END, OCT_START, ADMIN_ID, id="bad-period"),
        pytest.param(OCT_START, OCT_END, CUSTOMER_ID, id="not-admin"),
        pytest.param(OCT_START, OCT_END, UNKNOWN_ID, id="unknown-user"),
    ],
)
def test_no_sql_query_when_the_request_is_refused(start, end, id_admin):
    """The accounting data must never be read for a refused request."""
    service = make_service()

    with pytest.raises((ValueError, PermissionError, LookupError)):
        service.generate_report(start, end, id_admin=id_admin)

    assert service.report_dao.calls == []


def test_period_is_checked_before_the_user():
    """Cheap check first: an invalid period is refused without querying app_user."""
    user_dao = MagicMock()
    service = AccountingReportService(report_dao=FakeReportDao(), user_dao=user_dao)

    with pytest.raises(ValueError):
        service.generate_report(OCT_END, OCT_START, id_admin=ADMIN_ID)

    user_dao.find_by_id.assert_not_called()


def test_user_is_looked_up_with_the_given_id():
    user_dao = MagicMock()
    user_dao.find_by_id.return_value = FakeUserDao.users[ADMIN_ID]
    service = AccountingReportService(report_dao=FakeReportDao(), user_dao=user_dao)

    service.generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)

    user_dao.find_by_id.assert_called_once_with(ADMIN_ID)


def test_database_error_is_not_hidden():
    report_dao = MagicMock()
    report_dao.find_movie_revenues.side_effect = Exception("db down")
    service = AccountingReportService(report_dao=report_dao, user_dao=FakeUserDao())

    with pytest.raises(Exception, match="db down"):
        service.generate_report(OCT_START, OCT_END, id_admin=ADMIN_ID)
