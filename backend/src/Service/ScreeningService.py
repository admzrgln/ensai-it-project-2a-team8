from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from backend.src.DAO.BookingDAO import BookingDao
from backend.src.DAO.MovieDAO import MovieDao
from backend.src.DAO.RoomDAO import RoomDao
from backend.src.DAO.ScreeningDAO import CLEANING_BUFFER_MINUTES, ScreeningDao
from backend.src.DAO.UserDAO import UserDao
from utils.log_utils import log

if TYPE_CHECKING:
    from backend.src.Model.Screening import Screening


class ScreeningError(Exception):
    """A screening rule is not respected (the message is sent to the client as is)."""


class ScreeningNotFoundError(ScreeningError):
    """The screening to modify does not exist."""


class ScreeningService:
    """Business rules of the screenings (F1): planning by the administrators."""

    def __init__(self) -> None:
        self.screening_dao: ScreeningDao = ScreeningDao()
        self.room_dao: RoomDao = RoomDao()
        self.movie_dao: MovieDao = MovieDao()
        self.user_dao: UserDao = UserDao()
        self.booking_dao: BookingDao = BookingDao()

    @log
    def find_all(self) -> list[Screening]:
        """List all the screenings.

        Returns
        -------
        list of Screening
            All the screenings, by date.
        """
        return self.screening_dao.find_all()

    @log
    def find_by_id(self, id_screening: int) -> Screening | None:
        """Find a screening by its identifier.

        Parameters
        ----------
        id_screening : int
            Identifier of the screening.

        Returns
        -------
        Screening or None
            The screening, or None if it does not exist.
        """
        return self.screening_dao.find_by_id(id_screening)

    @log
    def find_by_movie(self, id_movie: int) -> list[Screening]:
        """List the screenings of a movie.

        Parameters
        ----------
        id_movie : int
            Identifier of the movie.

        Returns
        -------
        list of Screening
            The screenings of the movie, by date.
        """
        return self.screening_dao.find_by_movie(id_movie)

    @staticmethod
    def _normalize_date(screening: Screening) -> None:
        """Convert a date with a time zone ("...Z" or "+01:00") into the server time, without time zone.

        Like datetime.now() and the TIMESTAMP column of the database; otherwise the
        comparison with datetime.now() fails.

        Parameters
        ----------
        screening : Screening
            The screening to check.
        """
        if screening.date_time.tzinfo is not None:
            screening.date_time = screening.date_time.astimezone().replace(tzinfo=None)

    @staticmethod
    def _check_date(screening: Screening) -> None:
        """Check that the screening is in the future.

        Parameters
        ----------
        screening : Screening
            The screening to check.

        Raises
        ------
        ScreeningError
            If the screening is not in the future.
        """
        now = datetime.now()
        if screening.date_time <= now:
            raise ScreeningError(f"The screening must be in the future (server time: {now:%Y-%m-%d %H:%M})")

    def _check_room(self, screening: Screening, booked_seats: int = 0) -> int:
        """Check the room and compute the available seats (capacity - seats already booked).

        Parameters
        ----------
        screening : Screening
            The screening to check.
        booked_seats : int, optional
            Seats already booked for this screening (0 for a new screening).

        Returns
        -------
        int
            Number of seats still available.

        Raises
        ------
        ScreeningError
            If the room does not exist or is too small for the seats already booked.
        """
        room = self.room_dao.find_by_id(screening.id_room)
        if room is None:
            raise ScreeningError(f"Room {screening.id_room} not found")
        if room.capacity < booked_seats:
            raise ScreeningError(
                f"Room {screening.id_room} has only {room.capacity} seats "
                f"but {booked_seats} seats are already booked for this screening"
            )
        return room.capacity - booked_seats

    def _check_movie(self, screening: Screening) -> int:
        """Check the movie of the screening.

        Parameters
        ----------
        screening : Screening
            The screening to check.

        Returns
        -------
        int
            Duration of the movie in minutes (used to check the overlaps).

        Raises
        ------
        ScreeningError
            If the movie does not exist or has no duration.
        """
        movie = self.movie_dao.find_by_id(screening.id_movie)
        if movie is None:
            raise ScreeningError(f"Movie {screening.id_movie} not found")
        if not movie.duration:
            raise ScreeningError(f"Movie {screening.id_movie} has no duration")
        return movie.duration

    def _check_admin(self, screening: Screening) -> None:
        """Check that the planner of the screening is an administrator.

        Parameters
        ----------
        screening : Screening
            The screening to check.

        Raises
        ------
        ScreeningError
            If the user does not exist or is not an administrator.
        """
        user = self.user_dao.find_by_id(screening.id_admin)
        if user is None:
            raise ScreeningError(f"User {screening.id_admin} not found")
        if user.role != "admin":
            raise ScreeningError(f"User {screening.id_admin} is not an administrator")

    def _check_overlap(self, screening: Screening, duration: int) -> None:
        """Check that the room is free, cleaning time included.

        Parameters
        ----------
        screening : Screening
            The screening to check.
        duration : int
            Duration of the movie in minutes.

        Raises
        ------
        ScreeningError
            If another screening uses the room at this time.
        """
        overlapping = self.screening_dao.find_overlapping(
            id_room=screening.id_room,
            start=screening.date_time,
            end=screening.date_time + timedelta(minutes=duration),
            exclude_id=screening.id_screening,  # None for a new screening
        )
        if overlapping:
            ids = ", ".join(str(o.id_screening) for o in overlapping)
            raise ScreeningError(
                f"Room {screening.id_room} is already used at this time (screening {ids}); "
                f"{CLEANING_BUFFER_MINUTES} minutes are required between two screenings"
            )

    def _validate(self, screening: Screening, booked_seats: int = 0) -> None:
        """Check the rules common to creation and modification, in this order.

        Also fills screening.available_seats: it is not asked to the administrator.

        Parameters
        ----------
        screening : Screening
            The screening to check.
        booked_seats : int, optional
            Seats already booked for this screening (0 for a new screening).

        Raises
        ------
        ScreeningError
            If a rule is not respected.
        """
        self._normalize_date(screening)
        self._check_date(screening)
        screening.available_seats = self._check_room(screening, booked_seats)
        duration = self._check_movie(screening)
        self._check_admin(screening)
        self._check_overlap(screening, duration)

    @log
    def create_screening(self, screening: Screening) -> bool:
        """Create a screening, with all the seats of the room available.

        Parameters
        ----------
        screening : Screening
            The screening to create.

        Returns
        -------
        bool
            True when the screening is created.

        Raises
        ------
        ScreeningError
            If a rule is not respected or the insertion failed.
        """
        self._validate(screening)
        if not self.screening_dao.insert_screening(screening):
            raise ScreeningError("Creation failed (database error)")
        return True

    @log
    def update_screening(self, screening: Screening) -> bool:
        """Update a screening without losing the bookings already made.

        Available seats = capacity of the (possibly new) room - seats already booked.

        Parameters
        ----------
        screening : Screening
            The screening with its new values (id_screening required).

        Returns
        -------
        bool
            True when the screening is updated.

        Raises
        ------
        ScreeningNotFoundError
            If the screening does not exist.
        ScreeningError
            If a rule is not respected.
        """
        if screening.id_screening is None:
            raise ScreeningError("id_screening is required")
        if self.screening_dao.find_by_id(screening.id_screening) is None:
            raise ScreeningNotFoundError(f"Screening {screening.id_screening} not found")
        booked_seats = self.booking_dao.count_booked_seats(screening.id_screening)
        self._validate(screening, booked_seats)
        if not self.screening_dao.update_screening(screening):
            raise ScreeningNotFoundError(f"Screening {screening.id_screening} not found")
        return True

    @log
    def delete_screening(self, id_screening: int) -> bool:
        """Delete a screening by its identifier.

        Parameters
        ----------
        id_screening : int
            Identifier of the screening.

        Returns
        -------
        bool
            True if the screening was deleted, False otherwise.
        """
        return self.screening_dao.screening_delete(id_screening)
