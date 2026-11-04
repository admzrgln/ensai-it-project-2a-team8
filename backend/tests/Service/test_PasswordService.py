from unittest.mock import MagicMock

import pytest

from backend.src.Model.Customer import Customer
from backend.src.Service.PasswordService import (
    check_password_strength,
    create_salt,
    hash_password,
    validate_username_password,
)

# Valeurs de référence : SHA-256 de "soleil1234" et de "jambon" + "soleil1234"
HASH_NO_SALT = "a88c648411492422ee9a1f4b03d3f5b71705499786f4415a59b51b255611ba50"
HASH_WITH_SALT = "56d25b0190eb6fcdab76f20550aa3e85a37ee48d520ac70385ae3615deb7d53a"


# --- hash_password -------------------------------------------------------------------
def test_hash_password():
    assert hash_password("soleil1234") == HASH_NO_SALT


def test_hash_password_with_salt():
    assert hash_password("soleil1234", "jambon") == HASH_WITH_SALT


def test_hash_password_salt_changes_the_hash():
    assert hash_password("soleil1234", "sel1") != hash_password("soleil1234", "sel2")


def test_hash_password_is_deterministic():
    assert hash_password("soleil1234", "jambon") == hash_password("soleil1234", "jambon")


# --- create_salt ---------------------------------------------------------------------
def test_create_salt_length():
    assert len(create_salt()) == 256  # 128 octets écrits en hexadécimal


def test_create_salt_is_random():
    assert create_salt() != create_salt()


# --- check_password_strength ---------------------------------------------------------
def test_strong_enough_password():
    check_password_strength("12345678")  # 8 caractères : accepté, aucune exception


def test_password_too_short():
    with pytest.raises(Exception, match="at least 8 characters"):
        check_password_strength("1234567")


# --- validate_username_password ------------------------------------------------------
@pytest.fixture
def user_repo():
    janjak = Customer(4, "Jean", "Jacques", "janjak@mail.fr", HASH_WITH_SALT, None, salt="jambon")
    repo = MagicMock()
    repo.get_by_username.side_effect = lambda username: janjak if username == "janjak" else None
    return repo


def test_validate_username_password_is_ok(user_repo):
    assert validate_username_password("janjak", "soleil1234", user_repo).id_user == 4


def test_validate_username_password_unknown_user(user_repo):
    with pytest.raises(Exception, match="user with username Jean-Jacques not found"):
        validate_username_password("Jean-Jacques", "soleil1234", user_repo)


def test_validate_username_password_incorrect_password(user_repo):
    with pytest.raises(Exception, match="Incorrect password"):
        validate_username_password("janjak", "wrongpassword", user_repo)
