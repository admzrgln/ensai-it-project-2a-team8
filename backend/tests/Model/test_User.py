from datetime import date

import pytest
from pydantic import ValidationError

from backend.src.Model.Administrator import Administrator
from backend.src.Model.APIUser import APIUser
from backend.src.Model.Customer import Customer
from backend.src.Model.User import User

BIRTH = date(2004, 3, 1)


# --- User ----------------------------------------------------------------------------
def test_user_constructor():
    u = User(1, "Louise", "F", "l@mail.fr", "hash", BIRTH, role="customer", salt="abc")
    assert (u.id_user, u.first_name, u.last_name, u.email) == (1, "Louise", "F", "l@mail.fr")
    assert (u.password, u.date_of_birth, u.role, u.salt) == ("hash", BIRTH, "customer", "abc")


def test_user_salt_defaults_to_none():
    assert User(1, "A", "B", "a@b.fr", "pw", None, role="customer").salt is None


def test_user_str_contains_main_information():
    text = str(User(1, "Louise", "F", "l@mail.fr", "pw", BIRTH, role="customer"))
    for part in ("1", "Louise", "F", "2004-03-01", "customer", "l@mail.fr"):
        assert part in text


# --- Customer --------------------------------------------------------------------------
def test_customer_role_is_forced():
    c = Customer(2, "Louise", "F", "l@mail.fr", "pw", BIRTH)
    assert c.role == "customer"
    assert isinstance(c, User)


def test_customer_defaults():
    c = Customer(None, "Louise", "F", "l@mail.fr", "pw", BIRTH)
    assert c.id_user is None
    assert c.is_ensai_student is False
    assert c.salt is None


def test_customer_ensai_student_and_salt():
    c = Customer(2, "Louise", "F", "l@ensai.fr", "pw", BIRTH, is_ensai_student=True, salt="abc")
    assert c.is_ensai_student is True
    assert c.salt == "abc"


def test_customer_str():
    text = str(Customer(2, "Louise", "F", "l@mail.fr", "pw", BIRTH))
    assert "Louise F" in text and "customer" in text and "l@mail.fr" in text


# --- Administrator ---------------------------------------------------------------------
def test_administrator_role_is_forced():
    a = Administrator(1, "Ad", "Min", "admin@mail.fr", "pw", BIRTH, salt="abc")
    assert a.role == "admin"
    assert a.salt == "abc"
    assert isinstance(a, User)
    assert not hasattr(a, "is_ensai_student")


def test_administrator_str():
    text = str(Administrator(1, "Ad", "Min", "admin@mail.fr", "pw", BIRTH))
    assert "Ad Min" in text and "admin" in text and "admin@mail.fr" in text


# --- APIUser ---------------------------------------------------------------------------
def test_api_user_ok():
    u = APIUser(id=3, username="louise")
    assert (u.id, u.username) == (3, "louise")


def test_api_user_invalid_id():
    with pytest.raises(ValidationError):
        APIUser(id="trois", username="louise")
