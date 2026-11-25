from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from backend.src.Model.Ticket import Ticket


class Booking:
    """Booking made by a customer for one screening (one ticket per person).

    Parameters
    ----------
    id_customer : int
        Identifier of the customer who booked.
    id_screening : int
        Identifier of the screening.
    tickets : list of Ticket or None, optional
        Tickets of the booking (empty list by default).
    status : str, optional
        "confirmed" (default) or "cancelled".
    booking_date : datetime or None, optional
        When the booking was made (filled by the database).
    id_booking : int or None, optional
        Identifier in the database (None before insertion).
    """

    def __init__(
        self,
        id_customer: int,
        id_screening: int,
        tickets: list[Ticket] | None = None,
        status: str = "confirmed",
        booking_date: datetime | None = None,
        id_booking: int | None = None,
    ) -> None:
        self.id_booking = id_booking
        self.id_customer = id_customer
        self.id_screening = id_screening
        self.tickets = tickets or []
        self.status = status
        self.booking_date = booking_date

    @property
    def seat_count(self) -> int:
        """Number of seats of the booking.

        Returns
        -------
        int
            The number of tickets.
        """
        return len(self.tickets)

    @property
    def total_price(self) -> float:
        """Amount to pay for the booking.

        Returns
        -------
        float
            Sum of the prices of the tickets, in euros, rounded to the cent.
        """
        return round(sum(t.price or 0 for t in self.tickets), 2)

    def to_dict(self) -> dict[str, Any]:
        """Convert the booking for a JSON response (properties are not exported automatically).

        Returns
        -------
        dict
            The attributes of the booking, its seat count, total price and tickets.
        """
        return {
            "id_booking": self.id_booking,
            "id_customer": self.id_customer,
            "id_screening": self.id_screening,
            "booking_date": self.booking_date,
            "status": self.status,
            "seat_count": self.seat_count,
            "total_price": self.total_price,
            "tickets": [vars(t) for t in self.tickets],
        }

    def __str__(self) -> str:
        return (
            f"Booking {self.id_booking} : séance {self.id_screening}, "
            f"{self.seat_count} place(s), total {self.total_price}€ ({self.status})"
        )
