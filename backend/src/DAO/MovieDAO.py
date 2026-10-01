import logging

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Movie import Movie
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class MovieDao(metaclass=Singleton):
    """Class containing methods to access Movies in the database."""

    # partie GET
    @log
    def find_all(self) -> list[Movie]:
        """List all movies in the database.
        Returns:
            list[Movie]
        """
        try:
            query = "SELECT * FROM public.movie ORDER BY title;"
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
                    poster_url=row["poster_url"],
                )
                movies_list.append(movie)

        return movies_list

    @log
    def find_by_id(self, movie_id: int) -> Movie:
        """Find a movie by its id."""
        try:
            query = "SELECT * FROM public.movie WHERE id_movie = %(id_movie)s;"
            res = DBConnector().sql_query(
                query, data={"id_movie": movie_id}, return_type="one"
            )
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
                poster_url=res["poster_url"],
            )

        return movie

    @log
    def find_by_title(self, title: str) -> Movie:
        """Find a movie by its id."""
        try:
            query = """
            SELECT *
            FROM public.movie
            WHERE title ILIKE %(title)s;
            """
            res = DBConnector().sql_query(
                query, data={"title": title}, return_type="one"
            ) 
           
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
                poster_url=res["poster_url"],
            )

        return movie

    # partie POST
    @log
    def insert_movie(self, movie: Movie) -> bool:
        """Create a movie in the database

        Parameters
        ----------
        movie : Movie

        Returns
        -------
        created : bool
            True if creation is successful
            False otherwise
        """

        query = """
            INSERT INTO movie (title, duration, genre, external_id, poster_url)
            VALUES (%(title)s, %(duration)s, %(genre)s, %(external_id)s, %(poster_url)s)
            RETURNING id_movie;
        """

        data = {
            "title": movie.title,
            "duration": movie.duration,
            "genre": movie.genre,
            "external_id": movie.external_id,
            "poster_url": movie.poster_url,
        }

        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")

            if res:
                movie.id_movie = res["id_movie"]
                return True

        except Exception as e:  # noqa: BLE001
            logging.error(f"Erreur lors de l'insertion du film : {e}")  # noqa: LOG015

        return False

    # partie UPDATE
    @log
    def update_movie(self, movie: Movie) -> bool:
        """Update a movie in the database

        Parameters
        ----------
        movie : Movie

        Returns
        -------
        created : bool
            True if modification is successful
            False otherwise
        """

        if movie.id_movie is None:
            logging.error("Impossible de mettre à jour : id_movie est None.")  # noqa: LOG015
            return False

        query = """
            UPDATE movie SET title = %(title)s, duration = %(duration)s,
            genre = %(genre)s, external_id = %(external_id)s, poster_url = %(poster_url)s
            WHERE id_movie = %(id_movie)s
            RETURNING id_movie;
        """

        data = {
            "title": movie.title,
            "duration": movie.duration,
            "genre": movie.genre,
            "external_id": movie.external_id,
            "poster_url": movie.poster_url,
            "id_movie": movie.id_movie
        }

        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")

            if res:
                movie.id_movie = res["id_movie"]
                return True

        except Exception as e:  # noqa: BLE001
            logging.error(f"Erreur lors de l'insertion du film : {e}")  # noqa: LOG015

        return False
 
    # partie DELETE
    def movie_delete(self, id_movie: int) -> bool:
        """Update a movie in the database

        Parameters
        ----------
        id_movie : int

        Returns
        -------
        created : bool
            True delete is successful
            False otherwise
        """
    
        try:
            query = """
            DELETE FROM movie WHERE id_movie = %(id_movie)s
            RETURNING id_movie;
            """
            res = DBConnector().sql_query(
                query, data={"id_movie": id_movie}, return_type="one"
            )

            if res:
                return True

        except Exception as e:  # noqa: BLE001
            logger.error(e)

        return False
