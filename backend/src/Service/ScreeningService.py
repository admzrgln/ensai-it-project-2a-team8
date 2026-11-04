from datetime import datetime, timedelta

from backend.src.DAO.MovieDAO import MovieDao
from backend.src.DAO.RoomDAO import RoomDao
from backend.src.DAO.ScreeningDAO import ScreeningDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Screening import Screening  # noqa: TC001
from utils.log_utils import log


class ScreeningError(Exception):
    """Règle métier non respectée (le message est renvoyé tel quel au client)."""


class ScreeningNotFoundError(ScreeningError):
    """La séance à modifier n'existe pas."""


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

    # ------------------------------------------------------------------
    # Règles métier : chaque méthode lève une ScreeningError avec un message clair
    # ------------------------------------------------------------------
    @staticmethod
    def _check_values(screening: Screening) -> None:
        if screening.base_price < 0:
            raise ScreeningError("The price can't be negative")
        if screening.available_seats < 0:
            raise ScreeningError("The number of available seats can't be negative")
        now = datetime.now()
        if screening.date_time <= now:
            raise ScreeningError(
                f"The screening must be in the future (server time: {now:%Y-%m-%d %H:%M})"
            )

    def _check_room(self, screening: Screening) -> None:
        room = self.room_dao.find_by_id(screening.id_room)
        if room is None:
            raise ScreeningError(f"Room {screening.id_room} not found")
        if screening.available_seats > room.capacity:
            raise ScreeningError(
                f"Room {screening.id_room} has only {room.capacity} seats "
                f"({screening.available_seats} requested)"
            )

    def _check_movie(self, screening: Screening) -> int:
        """Renvoie la durée du film (utile pour vérifier les chevauchements)."""
        movie = self.movie_dao.find_by_id(screening.id_movie)
        if movie is None:
            raise ScreeningError(f"Movie {screening.id_movie} not found")
        if not movie.duration:
            raise ScreeningError(f"Movie {screening.id_movie} has no duration")
        return movie.duration

    def _check_admin(self, screening: Screening) -> None:
        user = self.user_dao.find_by_id(screening.id_admin)
        if user is None:
            raise ScreeningError(f"User {screening.id_admin} not found")
        if user.role != "admin":
            raise ScreeningError(f"User {screening.id_admin} is not an administrator")

    def _check_overlap(self, screening: Screening, duration: int) -> None:
        overlapping = self.screening_dao.find_overlapping(
            id_room=screening.id_room,
            start=screening.date_time,
            end=screening.date_time + timedelta(minutes=duration),
            exclude_id=screening.id_screening,  # None à la création
        )
        if overlapping:
            ids = ", ".join(str(o.id_screening) for o in overlapping)
            raise ScreeningError(
                f"Room {screening.id_room} is already used at this time (screening {ids})"
            )

    def _validate(self, screening: Screening) -> None:
        """Règles communes à la création et à la modification, vérifiées dans cet ordre."""
        self._check_values(screening)
        self._check_room(screening)
        duration = self._check_movie(screening)
        self._check_admin(screening)
        self._check_overlap(screening, duration)

    @log
    def create_screening(self, screening: Screening) -> bool:
        """Crée la séance. Lève ScreeningError si une règle n'est pas respectée."""
        self._validate(screening)
        if not self.screening_dao.insert_screening(screening):
            raise ScreeningError("Creation failed (database error)")
        return True

    @log
    def update_screening(self, screening: Screening) -> bool:
        """Modifie la séance.
        Lève ScreeningNotFoundError si elle n'existe pas, ScreeningError sinon."""
        if screening.id_screening is None:
            raise ScreeningError("id_screening is required")
        self._validate(screening)
        if not self.screening_dao.update_screening(screening):
            raise ScreeningNotFoundError(f"Screening {screening.id_screening} not found")
        return True

    @log
    def delete_screening(self, id_screening: int) -> bool:
        return self.screening_dao.screening_delete(id_screening)
