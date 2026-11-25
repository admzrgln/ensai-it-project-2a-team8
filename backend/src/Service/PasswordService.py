from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.src.Model.User import User


def hash_password(password: str, salt: str | None = None) -> str:
    """Hash a password with SHA-256, prefixed by the salt if there is one.

    Parameters
    ----------
    password : str
        The password in clear text.
    salt : str or None, optional
        Random salt of the user.

    Returns
    -------
    str
        The hash, in hexadecimal.
    """
    return hashlib.sha256(((salt or "") + password).encode()).hexdigest()


def create_salt() -> str:
    """Create a new random salt.

    Returns
    -------
    str
        128 random bytes, in hexadecimal (256 characters).
    """
    return secrets.token_hex(128)


def check_password_strength(password: str) -> None:
    """Check that a password is strong enough.

    Parameters
    ----------
    password : str
        The password in clear text.

    Raises
    ------
    Exception
        If the password has less than 8 characters.
    """
    if len(password) < 8:
        raise Exception("Password length must be at least 8 characters")


def validate_username_password(username: str, password: str, user_repo: Any) -> User:
    """Check the credentials of a user (helper of the project template, unused by the API).

    Parameters
    ----------
    username : str
        Name of the user.
    password : str
        Password in clear text.
    user_repo : Any
        Object with a get_by_username(username) method.

    Returns
    -------
    User
        The user, if the password is correct.

    Raises
    ------
    Exception
        If the user does not exist or the password is incorrect.
    """
    user: User | None = user_repo.get_by_username(username)
    if user is None:
        raise Exception(f"user with username {username} not found")

    hashed_input_password = hash_password(password, user.salt)
    if hashed_input_password != user.password:
        raise Exception("Incorrect password")

    return user
