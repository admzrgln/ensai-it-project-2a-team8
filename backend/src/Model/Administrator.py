from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.Model.Role import Role
from backend.src.Model.User import User

if TYPE_CHECKING:
    from datetime import date


class Administrator(User):
    """Administrator of the cinema: plans screenings, manages movies, tariffs and accounting.

    Parameters
    ----------
    id_user : int or None
        Identifier in the database (None before insertion).
    first_name : str
        First name.
    last_name : str
        Last name.
    email : str
        Email address, used to log in.
    password : str
        Password: in clear text when the account is created, then its hash.
    date_of_birth : date or None
        Date of birth.
    salt : str or None, optional
        Random salt used to hash the password.
    """

    def __init__(
        self,
        id_user: int | None,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        date_of_birth: date | None,
        salt: str | None = None,
    ) -> None:
        super().__init__(id_user, first_name, last_name, email, password, date_of_birth, role=Role.ADMIN, salt=salt)

    def __str__(self) -> str:
        return (
            f"Admin {self.id_user} : {self.first_name} {self.last_name} {self.date_of_birth} {self.role} - {self.email}"
        )
