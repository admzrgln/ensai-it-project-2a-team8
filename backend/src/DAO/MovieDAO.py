from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Movie import Movie
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class MovieDao(metaclass=Singleton):
    """Class containing methods to access Movies in the database."""

    @log
    def create(self, movie: Movie) -> bool:
        """
        Inserts a new movie record.
        Args:
            movie (Movie): The movie object to persist.
        Returns:
            bool: True if insertion is successful, False otherwise.
        """
        res = None

        try:
            with DBConnector().connection as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO movie (title, duration, genre, external_id, poster_url) "
                        "VALUES (%(title)s, %(duration)s, %(genre)s, %(external_id)s, %(poster_url)s) "
                        "RETURNING id;",
                        {
                            "title": movie.title,
                            "duration": movie.duration,
                            "genre": movie.genre,
                            "external_id": movie.external_id,
                            "poster_url": movie.poster_url,
                        },
                    )
                    res = cursor.fetchone()
        except Exception as e:
            logger.error(f"Error creating movie: {e}")
            raise

        created = False
        if res:
            movie.id = res["id"]
            created = True

        return created

    @log
    def find_by_id(self, id_movie: int) -> Movie | None:
        """
        Retrieves a specific movie and converts the database row into a Movie object.
        Args:
            id_movie (int): The ID of the movie to find.
        Returns:
            Movie: The movie object if found, otherwise None.
        """
        res = None

        try:
            with DBConnector().connection as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        " SELECT *                                  "
                        "   FROM movie                              "
                        " WHERE id = %(id_movie)                    ",
                        {"id_movie": id_movie},
                    )
                    res = cursor.fetchone()
        except Exception as e:
            logger.error(e)
            raise

        movie = None

        if res:
            movie = Movie(
                id=res["id"],
                title=res["title"],
                duration=res["duration"],
                genre=res["genre"],
                external_id=res["external_id"],
                poster_url=res["poster_url"],
            )

        return movie

    @log
    def find_all(self) -> list[Movie]:
        """
        Returns all movies currently in the database.
        Returns:
            list[Movie]: A list of Movie objects.
        """
        rows = []

        try:
            with DBConnector().connection as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT *
                          FROM movie
                         ORDER BY id ASC;
                        """
                    )
                    rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error finding all movies: {e}")
            raise

        movies = []
        for row in rows:
            movies.append(
                Movie(
                    id=row["id"],
                    title=row["title"],
                    duration=row["duration"],
                    genre=row["genre"],
                    external_id=row["external_id"],
                    poster_url=row["poster_url"],
                )
            )

        return movies
