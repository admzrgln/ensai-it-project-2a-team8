from enum import StrEnum


class BookingStatus(StrEnum):
    """Status of a booking.

    A BookingStatus is also a str: BookingStatus.CONFIRMED == "confirmed", so it can be
    saved in the database as plain text.
    """

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
