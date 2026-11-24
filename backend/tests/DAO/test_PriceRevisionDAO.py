from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from backend.src.DAO.PriceRevisionDAO import PriceRevisionDao
from backend.src.Model.PriceRevision import PriceRevision

APPLIED_AT = datetime(2027, 1, 1, 0, 0, 5)


@pytest.fixture
def connector():
    """Remplace DBConnector dans PriceRevisionDAO : renvoie l'instance mockée."""
    with patch("backend.src.DAO.PriceRevisionDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value


@pytest.fixture
def sql_query(connector):
    return connector.sql_query


@pytest.fixture
def cursor(connector):
    """Curseur utilisé dans `with conn.cursor() as cur:` (apply_due)."""
    conn = MagicMock()
    connector.get_connection.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchall.return_value = []
    return cur


@pytest.fixture
def dao():
    return PriceRevisionDao()


def revision_row(**overrides) -> dict:
    """Ligne SQL telle que renvoyée par RealDictCursor (NUMERIC -> Decimal)."""
    row = {"year": 2028, "rate_percent": Decimal("2.50"), "applied_at": None}
    row.update(overrides)
    return row


def test_to_revision_converts_decimal_to_float():
    revision = PriceRevisionDao._to_revision(revision_row())

    assert isinstance(revision, PriceRevision)
    assert revision.year == 2028
    assert revision.rate_percent == 2.5
    assert isinstance(revision.rate_percent, float)
    assert revision.applied_at is None


def test_to_revision_keeps_applied_at():
    revision = PriceRevisionDao._to_revision(revision_row(year=2027, applied_at=APPLIED_AT))

    assert revision.applied_at == APPLIED_AT


def test_find_all_maps_rows(dao, sql_query):
    sql_query.return_value = [revision_row(year=2027,
                              applied_at=APPLIED_AT), revision_row(year=2028)]

    revisions = dao.find_all()

    assert [r.year for r in revisions] == [2027, 2028]
    assert "ORDER BY year" in sql_query.call_args.args[0]
    assert sql_query.call_args.kwargs["return_type"] == "all"


@pytest.mark.parametrize("empty", [[], None])
def test_find_all_empty(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_all() == []


def test_find_all_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_all()


def test_upsert_planned_success(dao, sql_query):
    sql_query.return_value = {"year": 2028}

    assert dao.upsert_planned(PriceRevision(2028, 2.5)) is True
    assert sql_query.call_args.kwargs["data"] == {"year": 2028, "rate": 2.5}
    assert sql_query.call_args.kwargs["return_type"] == "one"


def test_upsert_planned_does_not_change_an_applied_revision(dao, sql_query):
    """Si la révision est déjà appliquée, l'UPDATE ne renvoie aucune ligne : on renvoie False."""
    sql_query.return_value = None

    assert dao.upsert_planned(PriceRevision(2027, 5.0)) is False
    assert "applied_at IS NULL" in sql_query.call_args.args[0]


def test_upsert_planned_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.upsert_planned(PriceRevision(2028, 2.5))


def test_delete_planned_success(dao, sql_query):
    sql_query.return_value = {"year": 2028}

    assert dao.delete_planned(2028) is True
    assert sql_query.call_args.kwargs["data"] == {"year": 2028}


def test_delete_planned_not_found_or_already_applied(dao, sql_query):
    sql_query.return_value = None

    assert dao.delete_planned(2027) is False
    assert "applied_at IS NULL" in sql_query.call_args.args[0]


def test_delete_planned_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.delete_planned(2028)


def test_apply_due_nothing_to_apply(dao, connector, cursor):
    assert dao.apply_due(2027) == []

    assert cursor.execute.call_count == 1
    assert cursor.execute.call_args.args[1] == {"year": 2027}
    connector.get_connection.return_value.close.assert_called_once()


def test_apply_due_applies_revisions_in_order(dao, cursor):
    cursor.fetchall.return_value = [
        {"year": 2027, "rate_percent": Decimal("2.00")},
        {"year": 2028, "rate_percent": Decimal("3.00")},
    ]

    assert dao.apply_due(2028) == [2027, 2028]

    queries = [c.args[0] for c in cursor.execute.call_args_list]
    params = [c.args[1] for c in cursor.execute.call_args_list]
    assert len(queries) == 5
    assert "UPDATE public.tariff" in queries[1] and params[1] == {"rate": Decimal("2.00")}
    assert "UPDATE public.price_revision" in queries[2] and params[2] == {"year": 2027}
    assert "UPDATE public.tariff" in queries[3] and params[3] == {"rate": Decimal("3.00")}
    assert "UPDATE public.price_revision" in queries[4] and params[4] == {"year": 2028}


def test_apply_due_locks_rows_and_skips_applied_revisions(dao, cursor):
    """FOR UPDATE + applied_at IS NULL : deux instances ne peuvent pas appliquer
     deux fois la même révision."""
    dao.apply_due(2028)

    select = cursor.execute.call_args_list[0].args[0]
    assert "FOR UPDATE" in select
    assert "applied_at IS NULL" in select
    assert "year <= %(year)s" in select


def test_apply_due_prices_are_rounded_to_10_cents(dao, cursor):
    cursor.fetchall.return_value = [{"year": 2027, "rate_percent": Decimal("2.00")}]

    dao.apply_due(2027)

    update_prices = cursor.execute.call_args_list[1].args[0]
    assert "ROUND(price * (1 + %(rate)s / 100.0) * 10) / 10" in update_prices


def test_apply_due_runs_in_one_transaction(dao, connector, cursor):
    """`with conn:` -> COMMIT si tout va bien (le mock enregistre l'entrée et la sortie du bloc)."""
    dao.apply_due(2027)

    conn = connector.get_connection.return_value
    conn.__enter__.assert_called_once()
    conn.__exit__.assert_called_once()


def test_apply_due_error_is_reraised_and_connection_closed(dao, connector, cursor):
    cursor.fetchall.return_value = [{"year": 2027, "rate_percent": Decimal("2.00")}]
    cursor.execute.side_effect = [None, Exception("db down")]

    with pytest.raises(Exception, match="db down"):
        dao.apply_due(2027)

    conn = connector.get_connection.return_value
    exc_type = conn.__exit__.call_args.args[0]
    assert exc_type is Exception
    conn.close.assert_called_once()
