from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Screening import Screening
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class ScreeningDao(metaclass=Singleton):
    """Class containing methods to access Screenings in the database."""

    @staticmethod
    def _to_screening(row: dict) -> Screening:
        """Convertit une ligne SQL en objet Screening (évite de répéter le code)."""
        return Screening(
            id_screening=row["id_screening"],
            id_room=row["id_room"],
            id_movie=row["id_movie"],
            id_admin=row["id_admin"],
            date_time=row["date_time"],
            base_price=float(row["base_price"]),  # NUMERIC revient en Decimal
            available_seats=row["available_seats"],
        )

    # GET
    @log
    def find_all(self) -> list[Screening]:
        query = "SELECT * FROM public.screening ORDER BY date_time;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_screening(r) for r in (res or [])]

    @log
    def find_by_id(self, id_screening: int) -> Screening | None:
        query = "SELECT * FROM public.screening WHERE id_screening = %(id)s;"
        try:
            res = DBConnector().sql_query(query, data={"id": id_screening}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_screening(res) if res else None

    @log
    def find_by_movie(self, id_movie: int) -> list[Screening]:
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
    def find_overlapping(self, id_room: int, start, end,
                         exclude_id: int | None = None) -> list[Screening]:
        """List the screenings of a room that overlap the interval [start, end).

        exclude_id : id d'une séance à ignorer (utile pour la modification,
        sinon une séance serait en conflit avec elle-même).
        """
        query = """
            SELECT s.*
            FROM public.screening s
            JOIN public.movie m ON m.id_movie = s.id_movie
            WHERE s.id_room = %(id_room)s
              AND s.date_time < %(end)s
              AND s.date_time + (m.duration * INTERVAL '1 minute') > %(start)s
              AND (%(exclude_id)s::int IS NULL OR s.id_screening <> %(exclude_id)s);
        """
        data = {"id_room": id_room, "start": start, "end": end, "exclude_id": exclude_id}
        try:
            res = DBConnector().sql_query(query, data=data, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_screening(r) for r in (res or [])]

    # POST
    @log
    def insert_screening(self, screening: Screening) -> bool:
        query = """
            INSERT INTO public.screening
                (id_room, id_movie, id_admin, date_time, base_price, available_seats)
            VALUES
                (%(id_room)s, %(id_movie)s, %(id_admin)s, %(date_time)s,
                 %(base_price)s, %(available_seats)s)
            RETURNING id_screening;
        """
        data = {
            "id_room": screening.id_room,
            "id_movie": screening.id_movie,
            "id_admin": screening.id_admin,
            "date_time": screening.date_time,
            "base_price": screening.base_price,
            "available_seats": screening.available_seats,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            if res:
                screening.id_screening = res["id_screening"]
                return True
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion de la séance : {e}")
        return False

    # UPDATE
    @log
    def update_screening(self, screening: Screening) -> bool:
        if screening.id_screening is None:
            logger.error("Impossible de mettre à jour : id_screening est None.")
            return False
        query = """
            UPDATE public.screening
            SET id_room = %(id_room)s, id_movie = %(id_movie)s, id_admin = %(id_admin)s,
                date_time = %(date_time)s, base_price = %(base_price)s,
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
            "base_price": screening.base_price,
            "available_seats": screening.available_seats,
        }
        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la séance : {e}")
        return False

    # DELETE
    @log
    def screening_delete(self, id_screening: int) -> bool:
        query = """
            DELETE FROM public.screening
            WHERE id_screening = %(id)s
            RETURNING id_screening;
        """
        try:
            res = DBConnector().sql_query(query, data={"id": id_screening}, return_type="one")
            return bool(res)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la séance : {e}")
        return False
