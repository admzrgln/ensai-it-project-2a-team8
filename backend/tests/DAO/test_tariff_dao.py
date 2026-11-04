from decimal import Decimal
from unittest.mock import patch

import pytest

from backend.src.DAO.TariffDAO import TariffDao
from backend.src.Model.Tariff import Tariff


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans TariffDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.TariffDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return TariffDao()


def tariff_row(**overrides) -> dict:
    row = {"code": "child", "label": "Moins de 14 ans", "price": Decimal("4.50"), "min_age": None,
           "max_age": 13, "requires_ensai": False, "requires_student": False, "is_active": True}
    row.update(overrides)
    return row


# --- Conversions -------------------------------------------------------------
def test_to_tariff_maps_columns_and_converts_decimal_to_float():
    t = TariffDao._to_tariff(tariff_row())
    assert (t.code, t.label, t.min_age, t.max_age) == ("child", "Moins de 14 ans", None, 13)
    assert t.price == 4.5 and isinstance(t.price, float)
    assert t.requires_ensai is False and t.requires_student is False and t.is_active is True


def test_to_tariff_keeps_null_price():
    """price NULL en base = prix de base de la séance : doit rester None, pas 0."""
    assert TariffDao._to_tariff(tariff_row(code="full", price=None)).price is None


def test_to_data_contains_all_columns():
    t = Tariff("senior", "65 ans et +", 5.0, min_age=65)
    assert TariffDao._to_data(t) == {
        "code": "senior", "label": "65 ans et +", "price": 5.0, "min_age": 65, "max_age": None,
        "requires_ensai": False, "requires_student": False, "is_active": True,
    }


# --- GET ---------------------------------------------------------------------
def test_find_all_active_only_by_default(dao, sql_query):
    sql_query.return_value = [tariff_row(), tariff_row(code="full", label="Plein tarif", price=None, max_age=None)]

    tariffs = dao.find_all()

    assert [t.code for t in tariffs] == ["child", "full"]
    assert "WHERE is_active" in sql_query.call_args.args[0]


def test_find_all_including_inactive(dao, sql_query):
    sql_query.return_value = [tariff_row(is_active=False)]

    tariffs = dao.find_all(only_active=False)

    assert tariffs[0].is_active is False
    assert "WHERE is_active" not in sql_query.call_args.args[0]


def test_find_all_empty(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_all() == []


def test_find_all_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.find_all()


def test_find_by_code_found(dao, sql_query):
    sql_query.return_value = tariff_row()
    assert dao.find_by_code("child").label == "Moins de 14 ans"
    assert sql_query.call_args.kwargs["data"] == {"code": "child"}


def test_find_by_code_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_by_code("nope") is None


def test_find_by_code_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.find_by_code("child")


# --- POST / UPDATE / "DELETE" ------------------------------------------------
def test_insert_tariff_ok(dao, sql_query):
    sql_query.return_value = {"code": "senior"}
    t = Tariff("senior", "65 ans et +", 5.0, min_age=65)

    assert dao.insert_tariff(t) is True
    assert sql_query.call_args.kwargs["data"] == TariffDao._to_data(t)
    assert "INSERT INTO public.tariff" in sql_query.call_args.args[0]


def test_insert_tariff_db_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("duplicate key")
    assert dao.insert_tariff(Tariff("child", "Doublon", 1.0)) is False


def test_update_tariff_ok(dao, sql_query):
    sql_query.return_value = {"code": "child"}
    t = Tariff("child", "Moins de 14 ans", 3.5, max_age=13)

    assert dao.update_tariff(t) is True
    assert sql_query.call_args.kwargs["data"]["price"] == 3.5
    assert "WHERE code = %(code)s" in sql_query.call_args.args[0]


def test_update_tariff_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.update_tariff(Tariff("nope", "Nope", 1.0)) is False


def test_update_tariff_db_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    assert dao.update_tariff(Tariff("child", "X", 1.0)) is False


def test_deactivate_tariff_ok(dao, sql_query):
    sql_query.return_value = {"code": "child"}

    assert dao.deactivate_tariff("child") is True
    query = sql_query.call_args.args[0]
    assert "SET is_active = FALSE" in query
    assert "DELETE" not in query  # on ne supprime jamais vraiment un tarif


def test_deactivate_tariff_not_found_or_already_inactive(dao, sql_query):
    sql_query.return_value = None
    assert dao.deactivate_tariff("child") is False


def test_deactivate_tariff_db_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    assert dao.deactivate_tariff("child") is False
