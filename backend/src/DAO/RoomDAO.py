from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Room import Room
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class RoomDao(metaclass=Singleton):
    """Class containing methods to access Rooms in the database."""

    @staticmethod
    def _to_room(row: dict) -> Room:
        """Convertit une ligne SQL en objet Room."""
        return Room(
            id_room=row["id_room"],
            room_type=row["type"],
            number=row["number"],
            capacity=row["capacity"],
        )

    # GET
    @log
    def find_all(self) -> list[Room]:
        query = "SELECT * FROM public.room ORDER BY number;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_room(r) for r in (res or [])]

    @log
    def find_by_id(self, id_room: int) -> Room | None:
        query = "SELECT * FROM public.room WHERE id_room = %(id_room)s;"
        try:
            res = DBConnector().sql_query(query, data={"id_room": id_room}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_room(res) if res else None

    @log
    def find_by_type(self, room_type: str) -> list[Room]:
        """List all rooms of a given type (case-insensitive)."""
        query = """
            SELECT * FROM public.room
            WHERE type ILIKE %(type)s
            ORDER BY number;
        """
        try:
            res = DBConnector().sql_query(query, data={"type": room_type}, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_room(r) for r in (res or [])]

    # POST
    @log
    def insert_room(self, room: Room) -> bool:
        """ Insert a new room in the database. """
        query = """
            INSERT INTO public.room (type, number, capacity)
            VALUES (%(type)s, %(number)s, %(capacity)s)
            RETURNING id_room;
        """
        data = {"type": room.room_type, "number": room.number, "capacity": room.capacity}
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            if res:
                room.id_room = res["id_room"]
                return True
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion de la salle : {e}")
        return False

    # UPDATE
    @log
    def update_room(self, room: Room) -> bool:
        """ Update a room by its id_room. """
        if room.id_room is None:
            logger.error("Impossible de mettre à jour : id_room est None.")
            return False
        query = """
            UPDATE public.room
            SET type = %(type)s, number = %(number)s, capacity = %(capacity)s
            WHERE id_room = %(id_room)s
            RETURNING id_room;
        """
        data = {
            "id_room": room.id_room,
            "type": room.room_type,
            "number": room.number,
            "capacity": room.capacity,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la salle : {e}")
        return False

    # DELETE
    @log
    def delete_room(self, id_room: int) -> bool:
        """ Delete a room by its id_room """
        query = """
            DELETE FROM public.room
            WHERE id_room = %(id_room)s
            RETURNING id_room;
        """
        try:
            res = DBConnector().sql_query(query, data={"id_room": id_room}, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la salle : {e}")
        return False
