from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Ticket:
    """One seat for one person in a booking.

    Parameters
    ----------
    first_name : str
        First name of the person.
    last_name : str
        Last name of the person.
    date_of_birth : date
        Date of birth, used to compute the age on the day of the screening.
    is_holder : bool, optional
        True if this is the ticket of the customer who booked.
    is_ensai_student : bool, optional
        True if the person is an ENSAI student.
    is_student : bool, optional
        True if the person is a student.
    tariff_code : str or None, optional
        Code of the tariff applied (filled by TariffService).
    price : float or None, optional
        Price paid, in euros (filled by TariffService).
    id_booking : int or None, optional
        Identifier of the booking.
    id_ticket : int or None, optional
        Identifier in the database (None before insertion).
    """

    def __init__(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        is_holder: bool = False,
        is_ensai_student: bool = False,
        is_student: bool = False,
        tariff_code: str | None = None,
        price: float | None = None,
        id_booking: int | None = None,
        id_ticket: int | None = None,
    ) -> None:
        self.id_ticket = id_ticket
        self.id_booking = id_booking
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.is_holder = is_holder
        self.is_ensai_student = is_ensai_student
        self.is_student = is_student
        self.tariff_code = tariff_code
        self.price = price

    def __str__(self) -> str:
        return f"Ticket {self.id_ticket} : {self.first_name} {self.last_name} - {self.tariff_code} {self.price}€"
