from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Service.PasswordService import hash_password
from backend.src.Service.UserService import UserService

BIRTH = date(2004, 3, 1)
PASSWORD = "motdepasse123"


@pytest.fixture
def service():
    """UserService avec le DAO remplacé par un mock ; par défaut l'email est libre."""
    s = UserService()
    s.user_dao = MagicMock()
    s.user_dao.find_user_by_email.return_value = None
    s.user_dao.insert_user.side_effect = lambda user: user  # renvoie l'utilisateur inséré
    s.user_dao.update_user.side_effect = lambda id_user, user: user
    return s


def make_customer(**overrides) -> Customer:
    data = dict(id_user=None, first_name="Louise", last_name="F", email="l@mail.fr",
                password=PASSWORD, date_of_birth=BIRTH)
    data.update(overrides)
    return Customer(**data)


def stored_user(password: str = PASSWORD, salt: str | None = "sel") -> Customer:
    """Utilisateur tel qu'il est en base : mot de passe haché avec son sel."""
    return Customer(2, "Louise", "F", "l@mail.fr", hash_password(password, salt), BIRTH, salt=salt)


# --- Lecture (délégation au DAO) ----------------------------------------------------------
def test_find_all(service):
    users = [make_customer(id_user=1)]
    service.user_dao.find_all_user.return_value = users
    assert service.find_all() == users


def test_find_by_id(service):
    user = make_customer(id_user=2)
    service.user_dao.find_by_id.return_value = user
    assert service.find_by_id(2) is user
    service.user_dao.find_by_id.assert_called_once_with(2)


def test_find_by_email(service):
    user = make_customer()
    service.user_dao.find_user_by_email.return_value = user
    assert service.find_by_email("l@mail.fr") is user


# --- create_user -------------------------------------------------------------------------
def test_create_user_hashes_password_with_a_new_salt(service):
    created = service.create_user(make_customer())

    assert created.salt is not None and len(created.salt) == 256
    assert created.password != PASSWORD  # jamais stocké en clair
    assert created.password == hash_password(PASSWORD, created.salt)
    service.user_dao.insert_user.assert_called_once()


def test_two_users_with_same_password_get_different_hashes(service):
    a = service.create_user(make_customer(email="a@mail.fr"))
    b = service.create_user(make_customer(email="b@mail.fr"))
    assert a.password != b.password


def test_create_user_existing_email_refused(service):
    service.user_dao.find_user_by_email.return_value = make_customer(id_user=1)

    assert service.create_user(make_customer()) is None
    service.user_dao.insert_user.assert_not_called()


def test_create_user_weak_password_refused(service):
    assert service.create_user(make_customer(password="court")) is None
    service.user_dao.insert_user.assert_not_called()


@pytest.mark.parametrize("email", ["louise@ensai.fr", "Louise.F@ENSAI.FR"])
def test_ensai_email_makes_customer_an_ensai_student(service, email):
    created = service.create_user(make_customer(email=email))
    assert created.is_ensai_student is True


def test_other_email_keeps_declared_status(service):
    assert service.create_user(make_customer(email="l@gmail.com")).is_ensai_student is False


def test_create_admin_with_ensai_email_has_no_student_status(service):
    admin = Administrator(None, "Ad", "Min", "admin@ensai.fr", PASSWORD, BIRTH)
    created = service.create_user(admin)
    assert not hasattr(created, "is_ensai_student")
    assert created.password == hash_password(PASSWORD, created.salt)


def test_create_user_dao_returns_none(service):
    service.user_dao.insert_user.side_effect = None
    service.user_dao.insert_user.return_value = None
    assert service.create_user(make_customer()) is None


# --- update_user -------------------------------------------------------------------------
def test_update_user_rehashes_password(service):
    updated = service.update_user(2, make_customer(id_user=2))

    assert updated.password == hash_password(PASSWORD, updated.salt)
    service.user_dao.update_user.assert_called_once()
    assert service.user_dao.update_user.call_args.args[0] == 2


def test_update_user_without_id_refused(service):
    assert service.update_user(None, make_customer()) is None
    service.user_dao.update_user.assert_not_called()


def test_update_user_weak_password_refused(service):
    assert service.update_user(2, make_customer(password="court")) is None
    service.user_dao.update_user.assert_not_called()


def test_update_user_ensai_email(service):
    assert service.update_user(2, make_customer(email="l@ensai.fr")).is_ensai_student is True


def test_update_user_not_found(service):
    service.user_dao.update_user.side_effect = None
    service.user_dao.update_user.return_value = None
    assert service.update_user(999, make_customer()) is None


# --- delete_user -------------------------------------------------------------------------
@pytest.mark.parametrize("result", [True, False])
def test_delete_user(service, result):
    service.user_dao.delete_user.return_value = result
    assert service.delete_user(2) is result
    service.user_dao.delete_user.assert_called_once_with(2)


# --- authenticate ------------------------------------------------------------------------
def test_authenticate_ok(service):
    user = stored_user()
    service.user_dao.find_user_by_email.return_value = user
    assert service.authenticate("l@mail.fr", PASSWORD) is user


def test_authenticate_wrong_password(service):
    service.user_dao.find_user_by_email.return_value = stored_user()
    assert service.authenticate("l@mail.fr", "mauvais-mot-de-passe") is None


def test_authenticate_unknown_email(service):
    assert service.authenticate("nobody@mail.fr", PASSWORD) is None


def test_authenticate_user_without_salt_refused(service):
    """Compte créé avant le hachage (pas de sel) : la connexion est refusée."""
    service.user_dao.find_user_by_email.return_value = stored_user(salt=None)
    assert service.authenticate("l@mail.fr", PASSWORD) is None
