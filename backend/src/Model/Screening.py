from datetime import datetime


class Screening:
    """Class representing a Screening."""

    def __init__(
        self,
        id_room: int,
        id_movie: int,
        id_admin: int,
        date_time: datetime,
        base_price: float,
        available_seats: int,
        id_screening: int | None = None
            ):
        self.id_screening = id_screening
        self.id_room = id_room
        self.id_movie = id_movie
        self.id_admin = id_admin
        self.date_time = date_time
        self.base_price = base_price
        self.available_seats = available_seats

    def __str__(self):
        return (f"Screening {self.id_screening} : film {self.id_movie}, "
                f"salle {self.id_room}, {self.date_time}, {self.base_price}€")
