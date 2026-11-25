from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.Model.User import User

if TYPE_CHECKING:
    from datetime import date


class Customer(User):
    """Customer of the cinema: books screenings for themselves and for other people.

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
        Date of birth, used to choose the tariff of their own ticket.
    is_ensai_student : bool, optional
        True if the customer is an ENSAI student (ENSAI email address).
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
        is_ensai_student: bool = False,
        salt: str | None = None,
    ) -> None:
        # The role is always "customer"
        super().__init__(id_user, first_name, last_name, email, password, date_of_birth, role="customer", salt=salt)
        self.is_ensai_student = is_ensai_student

    def __str__(self) -> str:
        ensai = " (ENSAI)" if self.is_ensai_student else ""
        return (
            f"User {self.id_user} : {self.first_name} {self.last_name} {self.date_of_birth} {self.role}{ensai}"
            f" - {self.email}"
        )
