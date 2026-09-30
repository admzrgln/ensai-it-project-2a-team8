from backend.src.Model.Movie import Movie
from backend.src.DAO.DBConnector import DBConnector
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class MovieDao(metaclass=Singleton):
    """Class containing methods to access Movies in the database."""

    @log
    def find_all(self) -> list[Movie]:
        """List all movies in the database.
        Returns:
            list[Movie]
        """
        try:
            # On utilise directement la méthode sql_query du DBConnector
            query = "SELECT * FROM public.movie ORDER BY title;"
            # return_type="all" remplace l'ancien cursor.fetchall()
            res = DBConnector().sql_query(query, return_type="all")
            
        except Exception as e:
            logger.error(e)
            raise

        movies_list = []

        if res:
            for row in res:
                movie = Movie(
                    id_movie=row["id_movie"],
                    title=row["title"],
                    duration=row["duration"],
                    genre=row["genre"],
                    external_id=row["external_id"],
                    poster_url=row["poster_url"]
                )
                movies_list.append(movie)

        return movies_list

    @log
    def find_by_id(self, movie_id: int) -> Movie:
        """Find a movie by its id."""
        try:
            query = "SELECT * FROM public.movie WHERE id_movie = %(id)s;"
            res = DBConnector().sql_query(query, data={"id": movie_id}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        movie = None
        if res:
            movie = Movie(
                id_movie=res["id_movie"],
                title=res["title"],
                duration=res["duration"],
                genre=res["genre"],
                external_id=res["external_id"],
                poster_url=res["poster_url"]
            )

        return movie
        