from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.DAO.RoomDAO import RoomDao
from utils.log_utils import log

if TYPE_CHECKING:
    from backend.src.Model.Room import Room


class RoomService:
    """Business rules on the rooms."""

    def __init__(self) -> None:
        self.room_dao: RoomDao = RoomDao()

    @log
    def find_all(self) -> list[Room]:
        """List all the rooms.

        Returns
        -------
        list of Room
            All the rooms, ordered by number.
        """
        return self.room_dao.find_all()

    @log
    def find_by_id(self, id_room: int) -> Room | None:
        """Find a room by its identifier.

        Parameters
        ----------
        id_room : int
            Identifier of the room.

        Returns
        -------
        Room or None
            The room, or None if it does not exist.
        """
        return self.room_dao.find_by_id(id_room)

    def _is_valid(self, room: Room) -> bool:
        """Check the rules common to creation and modification.

        Parameters
        ----------
        room : Room
            The room to check.

        Returns
        -------
        bool
            True if the room has a number and a positive capacity.
        """
        if not room.number or not room.number.strip():
            return False
        if room.capacity <= 0:
            return False
        return True

    @log
    def create_room(self, room: Room) -> bool:
        """Check and create a new room.

        Parameters
        ----------
        room : Room
            The room to create.

        Returns
        -------
        bool
            True if the room was created, False if it is invalid or the insertion failed.
        """
        if not self._is_valid(room):
            return False
        return self.room_dao.insert_room(room)

    @log
    def update_room(self, room: Room) -> bool:
        """Check and update an existing room.

        Parameters
        ----------
        room : Room
            The room with its new values.

        Returns
        -------
        bool
            True if the room was updated, False otherwise.
        """
        if room.id_room is None or not self._is_valid(room):
            return False
        return self.room_dao.update_room(room)

    @log
    def delete_room(self, id_room: int) -> bool:
        """Delete a room by its identifier.

        Parameters
        ----------
        id_room : int
            Identifier of the room.

        Returns
        -------
        bool
            True if the room was deleted, False otherwise.
        """
        return self.room_dao.delete_room(id_room)
