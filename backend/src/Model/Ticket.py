from datetime import date


class Ticket:
    """Class representing a Ticket: one seat for one person in a booking."""

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
    ):
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

    def __str__(self):
        return (f"Ticket {self.id_ticket} : {self.first_name}"
                f" {self.last_name} - {self.tariff_code} {self.price}€")
