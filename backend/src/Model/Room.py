class Room:
    """Class representing a Room."""

    def __init__(
        self,
        room_type: str,
        number: str,
        capacity: int,
        id_room: int | None = None
            ):
        self.id_room = id_room
        self.room_type = room_type
        self.number = number
        self.capacity = capacity

    def __str__(self):
        return f"Room {self.id_room} : {self.room_type} n°{self.number} ({self.capacity} places)"
