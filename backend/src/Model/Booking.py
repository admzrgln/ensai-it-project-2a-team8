from datetime import datetime

from backend.src.Model.Ticket import Ticket


class Booking:
    """Class representing a Booking made by a customer for one screening."""

    def __init__(
        self,
        id_customer: int,
        id_screening: int,
        tickets: list[Ticket] | None = None,
        status: str = "confirmed",
        booking_date: datetime | None = None,
        id_booking: int | None = None,
    ):
        self.id_booking = id_booking
        self.id_customer = id_customer
        self.id_screening = id_screening
        self.tickets = tickets or []
        self.status = status
        self.booking_date = booking_date

    @property
    def seat_count(self) -> int:
        return len(self.tickets)

    @property
    def total_price(self) -> float:
        return round(sum(t.price or 0 for t in self.tickets), 2)

    def to_dict(self) -> dict:
        """Version JSON-friendly (les @property ne sont pas exportées automatiquement)."""
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

    def __str__(self):
        return (f"Booking {self.id_booking} : séance {self.id_screening}, "
                f"{self.seat_count} place(s), total {self.total_price}€ ({self.status})")
