import logging

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Movie import Movie
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class MovieDao(metaclass=Singleton):
    """Access to the movies in the database."""

    # GET
    @log
    def find_all(self) -> list[Movie]:
        """List all the movies, ordered by title.

        Returns
        -------
        list of Movie
            All the movies (empty list if there is none).
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
    def find_by_id(self, movie_id: int) -> Movie | None:
        """Find a movie by its identifier.

        Parameters
        ----------
        movie_id : int
            Identifier of the movie.

        Returns
        -------
        Movie or None
            The movie, or None if it does not exist.
        """
        try:
            query = "SELECT * FROM public.movie WHERE id_movie = %(id_movie)s;"
            res = DBConnector().sql_query(query, data={"id_movie": movie_id}, return_type="one")
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
    def find_by_title(self, title: str) -> Movie | None:
        """Find a movie by its title (case-insensitive, ILIKE patterns accepted).

        Parameters
        ----------
        title : str
            Title, or ILIKE pattern, of the movie.

        Returns
        -------
        Movie or None
            The first movie found, or None.
        """
        try:
            query = """
            SELECT *
            FROM public.movie
            WHERE title ILIKE %(title)s;
            """
            res = DBConnector().sql_query(query, data={"title": title}, return_type="one")

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

    # POST
    @log
    def insert_movie(self, movie: Movie) -> bool:
        """Insert a new movie; its id_movie is filled on success.

        Parameters
        ----------
        movie : Movie
            The movie to insert.

        Returns
        -------
        bool
            True if the movie was inserted, False otherwise.
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
            logging.error(f"Error while inserting the movie: {e}")

        return False

    # UPDATE
    @log
    def update_movie(self, movie: Movie) -> bool:
        """Update a movie, found by its id_movie.

        Parameters
        ----------
        movie : Movie
            The movie with its new values.

        Returns
        -------
        bool
            True if the movie was updated, False otherwise.
        """

        if movie.id_movie is None:
            logging.error("Cannot update: id_movie is None.")
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
            "id_movie": movie.id_movie,
        }

        try:
            res = DBConnector().sql_query(query, data=data, return_type="one")

            if res:
                movie.id_movie = res["id_movie"]
                return True

        except Exception as e:  # noqa: BLE001
            logging.error(f"Error while inserting the movie: {e}")

        return False

    # DELETE
    def movie_delete(self, id_movie: int) -> bool:
        """Delete a movie by its identifier.

        Parameters
        ----------
        id_movie : int
            Identifier of the movie.

        Returns
        -------
        bool
            True if the movie was deleted, False otherwise.
        """

        try:
            query = """
            DELETE FROM movie WHERE id_movie = %(id_movie)s
            RETURNING id_movie;
            """
            res = DBConnector().sql_query(query, data={"id_movie": id_movie}, return_type="one")

            if res:
                return True

        except Exception as e:  # noqa: BLE001
            logger.error(e)

        return False

    @log
    def find_by_external_id(self, external_id: str) -> Movie | None:
        """Find a movie by its IMDb identifier.

        Parameters
        ----------
        external_id : str
            IMDb identifier, e.g. "tt1375666".

        Returns
        -------
        Movie or None
            The movie, or None if it is not in the database.
        """
        try:
            query = "SELECT * FROM public.movie WHERE external_id = %(external_id)s;"
            res = DBConnector().sql_query(query, data={"external_id": external_id}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        if not res:
            return None
        return Movie(
            id_movie=res["id_movie"],
            title=res["title"],
            duration=res["duration"],
            genre=res["genre"],
            external_id=res["external_id"],
            poster_url=res["poster_url"],
        )
