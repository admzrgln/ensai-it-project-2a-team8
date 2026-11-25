import pytest

from backend.src.Service.PasswordService import check_password_strength, create_salt, hash_password

HASH_NO_SALT = "a88c648411492422ee9a1f4b03d3f5b71705499786f4415a59b51b255611ba50"
HASH_WITH_SALT = "56d25b0190eb6fcdab76f20550aa3e85a37ee48d520ac70385ae3615deb7d53a"


def test_hash_password():
    assert hash_password("soleil1234") == HASH_NO_SALT


def test_hash_password_with_salt():
    assert hash_password("soleil1234", "jambon") == HASH_WITH_SALT


def test_hash_password_salt_changes_the_hash():
    assert hash_password("soleil1234", "sel1") != hash_password("soleil1234", "sel2")


def test_hash_password_is_deterministic():
    assert hash_password("soleil1234", "jambon") == hash_password("soleil1234", "jambon")


def test_create_salt_length():
    assert len(create_salt()) == 256


def test_create_salt_is_random():
    assert create_salt() != create_salt()


def test_strong_enough_password():
    check_password_strength("12345678")


def test_password_too_short():
    with pytest.raises(Exception, match="at least 8 characters"):
        check_password_strength("1234567")
