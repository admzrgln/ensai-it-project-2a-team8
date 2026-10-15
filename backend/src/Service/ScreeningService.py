from datetime import datetime, timedelta

from backend.src.DAO.MovieDAO import MovieDao
from backend.src.DAO.RoomDAO import RoomDao
from backend.src.DAO.ScreeningDAO import ScreeningDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Screening import Screening
from utils.log_utils import log


class ScreeningService:
    """Class containing Screening service methods (Business Logic Layer)"""

    def __init__(self):
        self.screening_dao = ScreeningDao()
        self.room_dao = RoomDao()
        self.movie_dao = MovieDao()
        self.user_dao = UserDao()

    @log
    def find_all(self) -> list[Screening]:
        return self.screening_dao.find_all()

    @log
    def find_by_id(self, id_screening: int) -> Screening | None:
        return self.screening_dao.find_by_id(id_screening)

    @log
    def find_by_movie(self, id_movie: int) -> list[Screening]:
        return self.screening_dao.find_by_movie(id_movie)

    def _is_valid(self, screening: Screening) -> bool:
        """Règles métier communes à la création et à la modification."""
        # 1. Valeurs de base
        if screening.base_price < 0 or screening.available_seats < 0:
            return False

        # 2. La séance doit être dans le futur
        if screening.date_time <= datetime.now():
            return False

        # 3. La salle existe et est assez grande
        room = self.room_dao.find_by_id(screening.id_room)
        if room is None or screening.available_seats > room.capacity:
            return False

        # 4. Le film existe et a une durée connue
        movie = self.movie_dao.find_by_id(screening.id_movie)
        if movie is None or not movie.duration:
            return False

        # 5. L'organisateur existe et est administrateur
        user = self.user_dao.find_by_id(screening.id_admin)
        if user is None or user.role != "admin":
            return False

        # 6. Pas de chevauchement avec une autre séance de la même salle
        end = screening.date_time + timedelta(minutes=movie.duration)
        overlapping = self.screening_dao.find_overlapping(
            id_room=screening.id_room,
            start=screening.date_time,
            end=end,
            exclude_id=screening.id_screening,  # None à la création
        )
        if overlapping:
            return False

        return True

    @log
    def create_screening(self, screening: Screening) -> bool:
        if not self._is_valid(screening):
            return False
        return self.screening_dao.insert_screening(screening)

    @log
    def update_screening(self, screening: Screening) -> bool:
        if screening.id_screening is None or not self._is_valid(screening):
            return False
        return self.screening_dao.update_screening(screening)

    @log
    def delete_screening(self, id_screening: int) -> bool:
        return self.screening_dao.screening_delete(id_screening)