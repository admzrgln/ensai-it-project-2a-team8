from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Screening import Screening
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

if TYPE_CHECKING:
    from datetime import datetime

logger = get_logger(__name__)
CLEANING_BUFFER_MINUTES = 30


class ScreeningDao(metaclass=Singleton):
    """Access to the screenings in the database."""

    @staticmethod
    def _to_screening(row: dict[str, Any]) -> Screening:
        """Convert a row of the screening table into a Screening.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        Screening
            The corresponding screening.
        """
        return Screening(
            id_screening=row["id_screening"],
            id_room=row["id_room"],
            id_movie=row["id_movie"],
            id_admin=row["id_admin"],
            date_time=row["date_time"],
            available_seats=row["available_seats"],
        )

    # GET
    @log
    def find_all(self) -> list[Screening]:
        """List all the screenings, by date.

        Returns
        -------
        list of Screening
            All the screenings (empty list if there is none).
        """
        query = "SELECT * FROM public.screening ORDER BY date_time;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_screening(r) for r in (res or [])]

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
        query = "SELECT * FROM public.screening WHERE id_screening = %(id)s;"
        try:
            res = DBConnector().sql_query(query, data={"id": id_screening}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_screening(res) if res else None

    @log
    def find_by_movie(self, id_movie: int) -> list[Screening]:
        """List the screenings of a movie, by date.

        Parameters
        ----------
        id_movie : int
            Identifier of the movie.

        Returns
        -------
        list of Screening
            The screenings of the movie (empty list if there is none).
        """
        query = """
            SELECT * FROM public.screening
            WHERE id_movie = %(id_movie)s
            ORDER BY date_time;
        """
        try:
            res = DBConnector().sql_query(query, data={"id_movie": id_movie}, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_screening(r) for r in (res or [])]

    @log
    def find_overlapping(
        self,
        id_room: int,
        start: datetime,
        end: datetime,
        exclude_id: int | None = None,
        buffer_minutes: int = CLEANING_BUFFER_MINUTES,
    ) -> list[Screening]:
        """List the screenings of a room that overlap [start, end), with a cleaning gap on both sides.

        Two screenings are in conflict if less than `buffer_minutes` separate the end of one
        from the start of the other.

        Parameters
        ----------
        id_room : int
            Identifier of the room.
        start : datetime
            Start of the new screening.
        end : datetime
            End of the new screening (start + duration of the movie).
        exclude_id : int or None, optional
            Screening to ignore (the screening itself when it is modified).
        buffer_minutes : int, optional
            Minimum gap between two screenings, to clean the room.

        Returns
        -------
        list of Screening
            The screenings in conflict (empty list if the room is free).
        """
        query = """
            SELECT s.*
            FROM public.screening s
            JOIN public.movie m ON m.id_movie = s.id_movie
            WHERE s.id_room = %(id_room)s
              AND s.date_time < %(end)s + (%(buffer)s * INTERVAL '1 minute')
              AND s.date_time + ((m.duration + %(buffer)s) * INTERVAL '1 minute') > %(start)s
              AND (%(exclude_id)s::int IS NULL OR s.id_screening <> %(exclude_id)s);
        """
        data = {"id_room": id_room, "start": start, "end": end, "exclude_id": exclude_id, "buffer": buffer_minutes}
        try:
            res = DBConnector().sql_query(query, data=data, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_screening(r) for r in (res or [])]

    # POST
    @log
    def insert_screening(self, screening: Screening) -> bool:
        """Insert a new screening; its id_screening is filled on success.

        Parameters
        ----------
        screening : Screening
            The screening to insert.

        Returns
        -------
        bool
            True if the screening was inserted, False otherwise.
        """
        query = """
            INSERT INTO public.screening
                (id_room, id_movie, id_admin, date_time, available_seats)
            VALUES
                (%(id_room)s, %(id_movie)s, %(id_admin)s, %(date_time)s,
                 %(available_seats)s)
            RETURNING id_screening;
        """
        data = {
            "id_room": screening.id_room,
            "id_movie": screening.id_movie,
            "id_admin": screening.id_admin,
            "date_time": screening.date_time,
            "available_seats": screening.available_seats,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            if res:
                screening.id_screening = res["id_screening"]
                return True
        except Exception as e:
            logger.error(f"Error while inserting the screening: {e}")
        return False

    # UPDATE
    @log
    def update_screening(self, screening: Screening) -> bool:
        """Update a screening, found by its id_screening.

        Parameters
        ----------
        screening : Screening
            The screening with its new values.

        Returns
        -------
        bool
            True if the screening was updated, False otherwise.
        """
        if screening.id_screening is None:
            logger.error("Cannot update: id_screening is None.")
            return False
        query = """
            UPDATE public.screening
            SET id_room = %(id_room)s, id_movie = %(id_movie)s, id_admin = %(id_admin)s,
                date_time = %(date_time)s,
                available_seats = %(available_seats)s
            WHERE id_screening = %(id_screening)s
            RETURNING id_screening;
        """
        data = {
            "id_screening": screening.id_screening,
            "id_room": screening.id_room,
            "id_movie": screening.id_movie,
            "id_admin": screening.id_admin,
            "date_time": screening.date_time,
            "available_seats": screening.available_seats,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Error while updating the screening: {e}")
        return False

    # DELETE
    @log
    def screening_delete(self, id_screening: int) -> bool:
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
        query = """
            DELETE FROM public.screening
            WHERE id_screening = %(id)s
            RETURNING id_screening;
        """
        try:
            res = DBConnector().sql_query(query, data={"id": id_screening}, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Error while deleting the screening: {e}")
        return False
