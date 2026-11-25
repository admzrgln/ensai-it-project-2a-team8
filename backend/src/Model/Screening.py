from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class Screening:
    """Screening of a movie in a room, planned by an administrator.

    Parameters
    ----------
    id_room : int
        Identifier of the room.
    id_movie : int
        Identifier of the movie.
    id_admin : int
        Identifier of the administrator who planned the screening.
    date_time : datetime
        Start of the screening.
    available_seats : int or None, optional
        Seats still available. Not chosen by the administrator: computed by ScreeningService
        (capacity of the room minus the seats already booked), then decreased by each booking.
    id_screening : int or None, optional
        Identifier in the database (None before insertion).
    """

    def __init__(
        self,
        id_room: int,
        id_movie: int,
        id_admin: int,
        date_time: datetime,
        available_seats: int | None = None,
        id_screening: int | None = None,
    ) -> None:
        self.id_screening = id_screening
        self.id_room = id_room
        self.id_movie = id_movie
        self.id_admin = id_admin
        self.date_time = date_time
        self.available_seats = available_seats

    def __str__(self) -> str:
        return (
            f"Screening {self.id_screening} : film {self.id_movie}, "
            f"salle {self.id_room}, {self.date_time}, {self.available_seats} places libres"
        )
