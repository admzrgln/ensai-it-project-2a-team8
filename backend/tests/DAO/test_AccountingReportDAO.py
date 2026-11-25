from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from backend.src.DAO.AccountingReportDAO import AccountingReportDao
from backend.src.Model.MovieOccupancy import MovieOccupancy
from backend.src.Model.MovieRevenue import MovieRevenue

OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans AccountingReportDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.AccountingReportDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return AccountingReportDao()


def revenue_row(**overrides) -> dict:
    """Ligne SQL telle que renvoyée par RealDictCursor (SUM -> Decimal, COUNT -> int)."""
    row = {"id_movie": 2, "title": "Oppenheimer", "revenue": Decimal("44.40"), "tickets_sold": 4}
    row.update(overrides)
    return row


def occupancy_row(**overrides) -> dict:
    row = {
        "id_movie": 1,
        "title": "Dune: Part Two",
        "screenings": 2,
        "seats_offered": Decimal("200"),
        "seats_sold": Decimal("50"),
    }
    row.update(overrides)
    return row


def test_to_movie_revenue_converts_decimal_to_float():
    line = AccountingReportDao._to_movie_revenue(revenue_row())

    assert isinstance(line, MovieRevenue)
    assert (line.id_movie, line.title, line.tickets_sold) == (2, "Oppenheimer", 4)
    assert line.revenue == 44.40
    assert isinstance(line.revenue, float)


def test_to_movie_occupancy_converts_sums_to_int():
    line = AccountingReportDao._to_movie_occupancy(occupancy_row())

    assert isinstance(line, MovieOccupancy)
    assert (line.id_movie, line.title, line.screenings) == (1, "Dune: Part Two", 2)
    assert (line.seats_offered, line.seats_sold) == (200, 50)
    assert isinstance(line.seats_sold, int)


def test_find_movie_revenues_maps_rows(dao, sql_query):
    sql_query.return_value = [revenue_row(), revenue_row(id_movie=1, title="Dune: Part Two", revenue=Decimal("36.00"))]

    lines = dao.find_movie_revenues(OCT_START, OCT_END)

    assert [m.title for m in lines] == ["Oppenheimer", "Dune: Part Two"]
    assert sql_query.call_args.kwargs["return_type"] == "all"


def test_find_movie_revenues_end_date_is_inclusive(dao, sql_query):
    """La borne de fin est incluse :
    on envoie "< 1er novembre" pour garder le 31 octobre à 23h30."""
    sql_query.return_value = []

    dao.find_movie_revenues(OCT_START, OCT_END)

    assert sql_query.call_args.kwargs["data"] == {"start": OCT_START, "end_exclusive": date(2026, 11, 1)}


def test_find_movie_revenues_counts_only_confirmed_bookings(dao, sql_query):
    """Les réservations annulées ne doivent pas compter dans les recettes."""
    sql_query.return_value = []

    dao.find_movie_revenues(OCT_START, OCT_END)

    assert "b.status = 'confirmed'" in sql_query.call_args.args[0]


def test_find_movie_revenues_uses_booking_date(dao, sql_query):
    """Décision de l'équipe : les recettes sont comptées à la date de réservation."""
    sql_query.return_value = []

    dao.find_movie_revenues(OCT_START, OCT_END)

    assert "b.booking_date" in sql_query.call_args.args[0]


@pytest.mark.parametrize("empty", [[], None])
def test_find_movie_revenues_no_sale(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_movie_revenues(OCT_START, OCT_END) == []


def test_find_movie_revenues_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_movie_revenues(OCT_START, OCT_END)


def test_find_movie_occupancy_maps_rows(dao, sql_query):
    sql_query.return_value = [occupancy_row(), occupancy_row(id_movie=2, title="Oppenheimer", screenings=1)]

    lines = dao.find_movie_occupancy(OCT_START, OCT_END)

    assert [o.title for o in lines] == ["Dune: Part Two", "Oppenheimer"]
    assert lines[0].occupancy_rate == 25.0


def test_find_movie_occupancy_end_date_is_inclusive(dao, sql_query):
    sql_query.return_value = []

    dao.find_movie_occupancy(OCT_START, OCT_END)

    assert sql_query.call_args.kwargs["data"] == {"start": OCT_START, "end_exclusive": date(2026, 11, 1)}


def test_find_movie_occupancy_ignores_future_screenings(dao, sql_query):
    """Le taux de remplissage n'a de sens qu'une fois la séance commencée."""
    sql_query.return_value = []

    dao.find_movie_occupancy(OCT_START, OCT_END)

    assert "LOCALTIMESTAMP" in sql_query.call_args.args[0]


@pytest.mark.parametrize("empty", [[], None])
def test_find_movie_occupancy_no_screening(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_movie_occupancy(OCT_START, OCT_END) == []


def test_find_movie_occupancy_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_movie_occupancy(OCT_START, OCT_END)
