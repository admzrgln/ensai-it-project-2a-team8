from backend.src.DAO.MovieDAO import MovieDao  # noqa: N999
from backend.src.Model.Movie import Movie
from utils.log_utils import log


class MovieService:
    """Class containing Movie service methods"""

    @log
    def find_all(self) -> list[Movie]:
        """List all movies available in the database"""
        return MovieDao().find_all()

    @log
    def find_by_id(self, id_movie: int) -> Movie:
        """Find a specific movie by its id"""
        return MovieDao().find_by_id(id_movie)
