class Room:
    """Room of the cinema.

    Parameters
    ----------
    number : str
        Number of the room, as displayed in the cinema.
    capacity : int
        Number of seats.
    id_room : int or None, optional
        Identifier in the database (None before insertion).
    """

    def __init__(self, number: str, capacity: int, id_room: int | None = None) -> None:
        self.id_room = id_room
        self.number = number
        self.capacity = capacity

    def __str__(self) -> str:
        return f"Room {self.id_room} : n°{self.number} ({self.capacity} places)"
