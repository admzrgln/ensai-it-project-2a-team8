"""Unit tests of AccountingReportService.
"""
from datetime import date

import pytest

from backend.src.Model.MovieRevenue import MovieRevenue
from backend.src.Service.AccountingReportService import AccountingReportService


class FakeUser:
    def __init__(self, id_user, role):
        self.id_user = id_user
        self.role = role


class FakeUserDao:
    users = {1: FakeUser(1, "admin"), 2: FakeUser(2, "customer")}

    def find_by_id(self, id_user):
        return self.users.get(id_user)


class FakeReportDao:
    """Returns the October 2026 per-movie figures of the fake database."""

    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [
            MovieRevenue(id_movie=2, title="Oppenheimer", revenue=44.40, tickets_sold=4),
            MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36.00, tickets_sold=4),
        ]
        self.calls = []

    def find_movie_revenues(self, period_start, period_end):
        self.calls.append((period_start, period_end))
        return self.rows


def make_service(rows=None):
    return AccountingReportService(report_dao=FakeReportDao(rows), user_dao=FakeUserDao())


OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)


def test_report_totals_match_fake_database():
    report = make_service().generate_report(OCT_START, OCT_END, id_admin=1)

    assert report.total_amount == 80.40
    assert report.tickets_sold == 8
    assert report.average_ticket_price == 10.05
    assert [m.title for m in report.movie_revenues] == ["Oppenheimer", "Dune: Part Two"]


def test_period_is_passed_to_dao():
    service = make_service()
    service.generate_report(OCT_START, OCT_END, id_admin=1)
    assert service.report_dao.calls == [(OCT_START, OCT_END)]


def test_empty_period_gives_zero_and_no_division_by_zero():
    report = make_service(rows=[]).generate_report(OCT_START, OCT_END, id_admin=1)

    assert report.total_amount == 0
    assert report.tickets_sold == 0
    assert report.average_ticket_price == 0.0


def test_single_day_period_is_allowed():
    day = date(2026, 10, 5)
    report = make_service().generate_report(day, day, id_admin=1)
    assert report.period_start == report.period_end == day


def test_inverted_period_is_refused():
    with pytest.raises(ValueError):
        make_service().generate_report(OCT_END, OCT_START, id_admin=1)


def test_customer_cannot_see_accounting():
    with pytest.raises(PermissionError):
        make_service().generate_report(OCT_START, OCT_END, id_admin=2)


def test_unknown_user_is_refused():
    with pytest.raises(LookupError):
        make_service().generate_report(OCT_START, OCT_END, id_admin=999)
