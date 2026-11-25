from __future__ import annotations

import hashlib
import secrets


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
