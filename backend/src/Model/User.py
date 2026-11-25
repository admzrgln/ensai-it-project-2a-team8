from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from backend.src.Model.Role import Role


class User(ABC):
    """Abstract user of the application (an Administrator or a Customer).

    Parameters
    ----------
    id_user : int or None
        Identifier in the database (None before insertion).
    first_name : str
        First name.
    last_name : str
        Last name.
    email : str
        Email address, used to log in (unique).
    password : str
        Password: in clear text when the account is created, then its hash.
    date_of_birth : date or None
        Date of birth.
    role : Role
        Role.ADMIN or Role.CUSTOMER.
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
        role: Role,
        salt: str | None = None,
    ) -> None:
        self.id_user = id_user
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.date_of_birth = date_of_birth
        self.role = role
        self.salt = salt

    @abstractmethod
    def __str__(self) -> str:
        return (
            f"User {self.id_user} : {self.first_name} {self.last_name} {self.date_of_birth} {self.role} - {self.email}"
        )
