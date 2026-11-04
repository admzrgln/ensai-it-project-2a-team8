from datetime import date
from unittest.mock import patch

import pytest

from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer

BIRTH = date(2004, 3, 1)


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans UserDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.UserDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return UserDao()


def user_row(**overrides) -> dict:
    row = {"id_user": 2, "first_name": "Louise", "last_name": "F", "email": "l@ensai.fr",
           "password": "hash", "salt": "abc", "date_of_birth": BIRTH, "role": "customer",
           "is_ensai_student": True}
    row.update(overrides)
    return row


def admin_row(**overrides) -> dict:
    return user_row(id_user=1, first_name="Ad", last_name="Min", email="admin@mail.fr",
                    role="admin", is_ensai_student=False, **overrides)


def make_customer() -> Customer:
    return Customer(None, "Louise", "F", "l@ensai.fr", "hash", BIRTH, is_ensai_student=True, salt="abc")


def make_admin() -> Administrator:
    return Administrator(None, "Ad", "Min", "admin@mail.fr", "hash", BIRTH, salt="abc")


# --- _to_user --------------------------------------------------------------------------
def test_to_user_customer():
    u = UserDao._to_user(user_row())
    assert isinstance(u, Customer)
    assert (u.id_user, u.first_name, u.email, u.password, u.salt) == (2, "Louise", "l@ensai.fr", "hash", "abc")
    assert u.date_of_birth == BIRTH
    assert u.is_ensai_student is True


def test_to_user_admin():
    u = UserDao._to_user(admin_row())
    assert isinstance(u, Administrator)
    assert u.role == "admin"
    assert u.salt == "abc"


def test_to_user_without_optional_columns():
    """Anciennes lignes sans salt ni is_ensai_student : valeurs par défaut."""
    row = user_row()
    del row["salt"], row["is_ensai_student"]
    u = UserDao._to_user(row)
    assert u.salt is None
    assert u.is_ensai_student is False


# --- GET -------------------------------------------------------------------------------
def test_find_all_user(dao, sql_query):
    sql_query.return_value = [admin_row(), user_row()]

    users = dao.find_all_user()

    assert [type(u) for u in users] == [Administrator, Customer]
    assert sql_query.call_args.kwargs["return_type"] == "all"


def test_find_all_user_empty(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_all_user() == []


def test_find_by_id_found(dao, sql_query):
    sql_query.return_value = user_row()
    assert dao.find_by_id(2).email == "l@ensai.fr"
    assert sql_query.call_args.kwargs["data"] == {"id_user": 2}


def test_find_by_id_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_by_id(999) is None


def test_find_user_by_email_found(dao, sql_query):
    sql_query.return_value = user_row()
    assert dao.find_user_by_email("l@ensai.fr").id_user == 2
    assert sql_query.call_args.kwargs["data"] == {"email": "l@ensai.fr"}


def test_find_user_by_email_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.find_user_by_email("nobody@mail.fr") is None


@pytest.mark.parametrize("call", [
    lambda d: d.find_all_user(),
    lambda d: d.find_by_id(2),
    lambda d: d.find_user_by_email("l@ensai.fr"),
])
def test_get_methods_propagate_db_error(dao, sql_query, call):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        call(dao)


# --- POST ------------------------------------------------------------------------------
def test_insert_customer(dao, sql_query):
    sql_query.return_value = user_row()

    created = dao.insert_user(make_customer())

    assert isinstance(created, Customer)
    assert created.id_user == 2
    data = sql_query.call_args.kwargs["data"]
    assert (data["role"], data["is_ensai_student"], data["salt"]) == ("customer", True, "abc")


def test_insert_admin_has_no_ensai_status(dao, sql_query):
    """Un Administrator n'a pas d'attribut is_ensai_student : on envoie False."""
    sql_query.return_value = admin_row()

    created = dao.insert_user(make_admin())

    assert isinstance(created, Administrator)
    data = sql_query.call_args.kwargs["data"]
    assert (data["role"], data["is_ensai_student"]) == ("admin", False)


def test_insert_user_nothing_returned(dao, sql_query):
    sql_query.return_value = None
    assert dao.insert_user(make_customer()) is None


def test_insert_user_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("duplicate key value violates unique constraint")
    with pytest.raises(Exception, match="duplicate key"):
        dao.insert_user(make_customer())


# --- UPDATE ----------------------------------------------------------------------------
def test_update_user(dao, sql_query):
    sql_query.return_value = user_row(first_name="Lou")
    customer = make_customer()
    customer.first_name = "Lou"

    updated = dao.update_user(2, customer)

    assert updated.first_name == "Lou"
    data = sql_query.call_args.kwargs["data"]
    assert data["id_user"] == 2
    assert data["first_name"] == "Lou"


def test_update_admin_has_no_ensai_status(dao, sql_query):
    sql_query.return_value = admin_row()
    dao.update_user(1, make_admin())
    assert sql_query.call_args.kwargs["data"]["is_ensai_student"] is False


def test_update_user_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.update_user(999, make_customer()) is None


def test_update_user_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.update_user(2, make_customer())


# --- DELETE ----------------------------------------------------------------------------
def test_delete_user(dao, sql_query):
    sql_query.return_value = {"id_user": 2}
    assert dao.delete_user(2) is True
    assert sql_query.call_args.kwargs["data"] == {"id_user": 2}


def test_delete_user_not_found(dao, sql_query):
    sql_query.return_value = None
    assert dao.delete_user(999) is False


def test_delete_user_propagates_db_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    with pytest.raises(Exception, match="db down"):
        dao.delete_user(2)
