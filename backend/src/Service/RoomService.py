from backend.src.DAO.RoomDAO import RoomDao
from backend.src.Model.Room import Room
from utils.log_utils import log


class RoomService:
    """Class containing Room service methods (Business Logic Layer)"""

    def __init__(self):
        self.room_dao = RoomDao()

    @log
    def find_all(self) -> list[Room]:
        """List all rooms"""
        return self.room_dao.find_all()

    @log
    def find_by_id(self, id_room: int) -> Room | None:
        """Find a room by its id"""
        return self.room_dao.find_by_id(id_room)

    @log
    def find_by_type(self, room_type: str) -> list[Room]:
        """Find rooms by type (partial match supported)"""
        # Même principe que MovieService.find_by_title : jokers % pour une recherche partielle
        return self.room_dao.find_by_type(f"%{room_type}%")

    def _is_valid(self, room: Room) -> bool:
        """Règles métier communes à la création et à la modification."""
        if not room.room_type or not room.room_type.strip():
            return False
        if not room.number or not room.number.strip():
            return False
        if room.capacity <= 0:
            return False
        return True

    @log
    def create_room(self, room: Room) -> bool:
        """Validate and create a new room"""
        if not self._is_valid(room):
            return False
        return self.room_dao.insert_room(room)

    @log
    def update_room(self, room: Room) -> bool:
        """Validate and update an existing room"""
        if room.id_room is None or not self._is_valid(room):
            return False
        return self.room_dao.update_room(room)

    @log
    def delete_room(self, id_room: int) -> bool:
        """Delete a room by its id"""
        # À ajouter plus tard : refuser la suppression si la salle a des séances à venir
        return self.room_dao.delete_room(id_room)