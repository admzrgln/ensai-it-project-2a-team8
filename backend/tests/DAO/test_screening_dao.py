from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from backend.src.DAO.ScreeningDAO import ScreeningDao
from backend.src.Model.Screening import Screening

SHOW_TIME = datetime(2027, 3, 12, 20, 30)


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans ScreeningDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.ScreeningDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return ScreeningDao()


def screening_row(**overrides) -> dict:
    """Ligne SQL telle que renvoyée par RealDictCursor (base_price est un Decimal avec psycopg2)."""
    row = {
        "id_screening": 1,
        "id_room": 2,
        "id_movie": 3,
        "id_admin": 4,
        "date_time": SHOW_TIME,
        "base_price": Decimal("8.50"),
        "available_seats": 100,
    }
    row.update(overrides)
    return row


def make_screening(**overrides) -> Screening:
    data = dict(
        id_room=2,
        id_movie=3,
        id_admin=4,
        date_time=SHOW_TIME,
        base_price=8.5,
        available_seats=100,
        id_screening=None,
    )
    data.update(overrides)
    return Screening(**data)


def sent_values(sql_query) -> list:
    """Valeurs envoyées à la requête (indépendant du nom des clés du dict `data`)."""
    return list(sql_query.call_args.kwargs["data"].values())


def test_to_screening_maps_columns_and_converts_decimal_to_float():
    screening = ScreeningDao._to_screening(screening_row())

    assert screening.id_screening == 1
    assert screening.id_room == 2
    assert screening.id_movie == 3
    assert screening.id_admin == 4
    assert screening.date_time == SHOW_TIME
    assert screening.available_seats == 100
    assert screening.base_price == 8.5
    assert isinstance(screening.base_price, float)  # Decimal -> float


def test_find_all_maps_rows_to_screenings(dao, sql_query):
    sql_query.return_value = [screening_row(id_screening=1), screening_row(id_screening=2)]

    screenings = dao.find_all()

    assert [s.id_screening for s in screenings] == [1, 2]
    assert all(isinstance(s, Screening) for s in screenings)
    assert sql_query.call_args.kwargs["return_type"] == "all"


@pytest.mark.parametrize("empty", [[], None])
def test_find_all_empty_returns_empty_list(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_all() == []


def test_find_all_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_all()


def test_find_by_id_found(dao, sql_query):
    sql_query.return_value = screening_row(id_screening=7)

    screening = dao.find_by_id(7)

    assert isinstance(screening, Screening)
    assert screening.id_screening == 7
    assert sent_values(sql_query) == [7]
    assert sql_query.call_args.kwargs["return_type"] == "one"


def test_find_by_id_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_by_id(999) is None


def test_find_by_id_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_id(1)


def test_find_by_movie_maps_rows_to_screenings(dao, sql_query):
    sql_query.return_value = [screening_row(id_screening=1), screening_row(id_screening=2)]

    screenings = dao.find_by_movie(3)

    assert [s.id_screening for s in screenings] == [1, 2]
    assert sent_values(sql_query) == [3]
    assert sql_query.call_args.kwargs["return_type"] == "all"


@pytest.mark.parametrize("empty", [[], None])
def test_find_by_movie_no_result(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_by_movie(999) == []


def test_find_by_movie_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_movie(3)


def test_find_overlapping_returns_conflicting_screenings(dao, sql_query):
    sql_query.return_value = [screening_row(id_screening=10)]
    start = SHOW_TIME
    end = SHOW_TIME + timedelta(minutes=120)

    result = dao.find_overlapping(id_room=2, start=start, end=end, exclude_id=None)

    assert [s.id_screening for s in result] == [10]
    values = sent_values(sql_query)
    assert 2 in values
    assert start in values
    assert end in values
    assert sql_query.call_args.kwargs["return_type"] == "all"


def test_find_overlapping_none_returns_empty_list(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_overlapping(2, SHOW_TIME, SHOW_TIME + timedelta(minutes=90), None) == []


def test_find_overlapping_passes_excluded_id(dao, sql_query):
    """Utilisé à la modification : la séance ne doit pas être en conflit avec elle-même."""
    sql_query.return_value = []

    dao.find_overlapping(2, SHOW_TIME, SHOW_TIME + timedelta(minutes=90), exclude_id=5)

    assert 5 in sent_values(sql_query)


def test_find_overlapping_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_overlapping(2, SHOW_TIME, SHOW_TIME + timedelta(minutes=90), None)


def test_insert_screening_success_sets_generated_id(dao, sql_query):
    sql_query.return_value = {"id_screening": 21}
    screening = make_screening()

    assert dao.insert_screening(screening) is True
    assert screening.id_screening == 21

    values = sent_values(sql_query)
    for expected in (2, 3, 4, SHOW_TIME, 8.5, 100):
        assert expected in values


def test_insert_screening_no_row_returned(dao, sql_query):
    sql_query.return_value = None
    screening = make_screening()

    assert dao.insert_screening(screening) is False
    assert screening.id_screening is None


def test_insert_screening_database_error_returns_false(dao, sql_query):
    """Par exemple : id_room ou id_movie inexistant (clé étrangère)."""
    sql_query.side_effect = Exception("foreign key violation")
    screening = make_screening()

    assert dao.insert_screening(screening) is False
    assert screening.id_screening is None


# ---------------------------------------------------------------------------
# update_screening
# ---------------------------------------------------------------------------
def test_update_screening_success(dao, sql_query):
    sql_query.return_value = {"id_screening": 7}
    screening = make_screening(id_screening=7, base_price=9.0, available_seats=80)

    assert dao.update_screening(screening) is True

    values = sent_values(sql_query)
    for expected in (7, 9.0, 80):
        assert expected in values


def test_update_screening_without_id_does_not_query(dao, sql_query):
    assert dao.update_screening(make_screening(id_screening=None)) is False
    sql_query.assert_not_called()


def test_update_screening_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.update_screening(make_screening(id_screening=999)) is False


def test_update_screening_database_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    assert dao.update_screening(make_screening(id_screening=7)) is False


# ---------------------------------------------------------------------------
# screening_delete
# ---------------------------------------------------------------------------
def test_screening_delete_success(dao, sql_query):
    sql_query.return_value = {"id_screening": 7}

    assert dao.screening_delete(7) is True
    assert sent_values(sql_query) == [7]


def test_screening_delete_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.screening_delete(999) is False


def test_screening_delete_database_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    assert dao.screening_delete(7) is False
