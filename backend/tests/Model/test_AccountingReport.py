"""Unit tests of the Model layer of AccountingReport.
"""
from datetime import date

import pytest

from backend.src.Model.AccountingReport import AccountingReport
from backend.src.Model.MovieRevenue import MovieRevenue

OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)


def october_lines() -> list[MovieRevenue]:
    return [
        MovieRevenue(id_movie=2, title="Oppenheimer", revenue=44.40, tickets_sold=4),
        MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36.00, tickets_sold=4),
    ]


def test_movie_revenue_constructor():
    line = MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36.0, tickets_sold=4)

    assert (line.id_movie, line.title, line.revenue, line.tickets_sold) == (1, "Dune: Part Two", 36.0, 4)


def test_movie_revenue_str_shows_two_decimals():
    line = MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36, tickets_sold=4)

    assert str(line) == "Dune: Part Two : 36.00€ (4 tickets)"


def test_report_totals_are_computed_from_the_lines():
    report = AccountingReport(OCT_START, OCT_END, october_lines())

    assert report.total_amount == pytest.approx(80.40)
    assert report.tickets_sold == 8
    assert report.average_ticket_price == pytest.approx(10.05)


def test_average_is_weighted_by_tickets_not_by_movies():
    """1 ticket at 4 € + 3 tickets at 8 € -> 28 / 4 = 7 € (not (4 + 8) / 2 = 6 €)."""
    lines = [
        MovieRevenue(1, "A", revenue=4.0, tickets_sold=1),
        MovieRevenue(2, "B", revenue=24.0, tickets_sold=3),
    ]

    assert AccountingReport(OCT_START, OCT_END, lines).average_ticket_price == pytest.approx(7.0)


def test_report_without_sales_has_zero_totals_and_no_division_by_zero():
    report = AccountingReport(OCT_START, OCT_END, [])

    assert report.total_amount == 0
    assert report.tickets_sold == 0
    assert report.average_ticket_price == 0.0
    assert report.movie_revenues == []


def test_free_tickets_only_give_a_zero_average():
    """Invitations: tickets were sold for 0 € -> average 0, still no division error."""
    report = AccountingReport(OCT_START, OCT_END, [MovieRevenue(1, "A", revenue=0.0, tickets_sold=5)])

    assert report.tickets_sold == 5
    assert report.average_ticket_price == 0.0


def test_float_sums_are_compared_with_approx():
    """0.1 + 0.2 != 0.3 in floating point: tests on money must use pytest.approx."""
    lines = [MovieRevenue(1, "A", 0.1, 1), MovieRevenue(2, "B", 0.2, 1)]

    assert AccountingReport(OCT_START, OCT_END, lines).total_amount == pytest.approx(0.3)


def test_lines_keep_the_order_given_by_the_dao():
    report = AccountingReport(OCT_START, OCT_END, october_lines())

    assert [m.title for m in report.movie_revenues] == ["Oppenheimer", "Dune: Part Two"]


def test_optional_ids_default_to_none():
    report = AccountingReport(OCT_START, OCT_END, [])

    assert report.id_report is None
    assert report.id_admin is None
    assert (report.period_start, report.period_end) == (OCT_START, OCT_END)


def test_ids_are_stored_when_given():
    report = AccountingReport(OCT_START, OCT_END, [], id_admin=1, id_report=7)

    assert (report.id_admin, report.id_report) == (1, 7)


def test_report_str_contains_period_and_totals():
    text = str(AccountingReport(OCT_START, OCT_END, october_lines()))

    assert "2026-10-01" in text and "2026-10-31" in text
    assert "80.40 euros" in text
    assert "8 tickets" in text
    assert "10.05 euros" in text
