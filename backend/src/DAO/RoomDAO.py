from __future__ import annotations

from typing import Any

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Room import Room
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class RoomDao(metaclass=Singleton):
    """Access to the rooms in the database."""

    @staticmethod
    def _to_room(row: dict[str, Any]) -> Room:
        """Convert a row of the room table into a Room.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        Room
            The corresponding room.
        """
        return Room(
            id_room=row["id_room"],
            number=row["number"],
            capacity=row["capacity"],
        )

    # GET
    @log
    def find_all(self) -> list[Room]:
        """List all the rooms, ordered by number.

        Returns
        -------
        list of Room
            All the rooms (empty list if there is none).
        """
        query = "SELECT * FROM public.room ORDER BY number;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_room(r) for r in (res or [])]

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
        query = "SELECT * FROM public.room WHERE id_room = %(id_room)s;"
        try:
            res = DBConnector().sql_query(query, data={"id_room": id_room}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_room(res) if res else None

    # POST
    @log
    def insert_room(self, room: Room) -> bool:
        """Insert a new room; its id_room is filled on success.

        Parameters
        ----------
        room : Room
            The room to insert.

        Returns
        -------
        bool
            True if the room was inserted, False otherwise.
        """
        query = """
            INSERT INTO public.room (number, capacity)
            VALUES (%(number)s, %(capacity)s)
            RETURNING id_room;
        """
        data = {"number": room.number, "capacity": room.capacity}
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            if res:
                room.id_room = res["id_room"]
                return True
        except Exception as e:
            logger.error(f"Error while inserting the room: {e}")
        return False

    # UPDATE
    @log
    def update_room(self, room: Room) -> bool:
        """Update a room, found by its id_room.

        Parameters
        ----------
        room : Room
            The room with its new values.

        Returns
        -------
        bool
            True if the room was updated, False otherwise (unknown room, no id or database error).
        """
        if room.id_room is None:
            logger.error("Cannot update: id_room is None.")
            return False
        query = """
            UPDATE public.room
            SET number = %(number)s, capacity = %(capacity)s
            WHERE id_room = %(id_room)s
            RETURNING id_room;
        """
        data = {
            "id_room": room.id_room,
            "number": room.number,
            "capacity": room.capacity,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Error while updating the room: {e}")
        return False

    # DELETE
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
        query = """
            DELETE FROM public.room
            WHERE id_room = %(id_room)s
            RETURNING id_room;
        """
        try:
            res = DBConnector().sql_query(query, data={"id_room": id_room}, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Error while deleting the room: {e}")
        return False
