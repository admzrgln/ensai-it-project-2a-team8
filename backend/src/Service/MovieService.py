from typing import Any

from backend.src.DAO.MovieDAO import MovieDao
from backend.src.Model.Movie import Movie
from backend.src.Service.OmdbClient import OmdbClient
from utils.log_utils import log


def _parse_runtime(runtime: str) -> int:
    """Convert the runtime given by OMDb into minutes ("136 min" -> 136, "N/A" -> 0).

    Parameters
    ----------
    runtime : str
        Runtime as written by OMDb.

    Returns
    -------
    int
        Number of minutes, or 0 if unknown.
    """
    try:
        return int(runtime.split()[0])
    except (ValueError, IndexError, AttributeError):
        return 0


def _first_genre(genres: str) -> str | None:
    """Keep the first genre given by OMDb ("Action, Sci-Fi" -> "Action").

    Parameters
    ----------
    genres : str
        Genres as written by OMDb, separated by commas.

    Returns
    -------
    str or None
        The first genre, or None if OMDb does not know it ("N/A" or empty).
    """
    first = genres.split(",")[0].strip() if genres else ""
    return None if first in ("", "N/A") else first


class MovieService:
    """Business rules on the movies, and import from OMDb."""

    def __init__(self) -> None:
        self.movie_dao: MovieDao = MovieDao()
        self.omdb_client = OmdbClient()

    @log
    def find_all(self) -> list[Movie]:
        """List all the movies.

        Returns
        -------
        list of Movie
            All the movies, ordered by title.
        """
        return self.movie_dao.find_all()

    @log
    def find_by_id(self, id_movie: int) -> Movie | None:
        """Find a movie by its identifier.

        Parameters
        ----------
        id_movie : int
            Identifier of the movie.

        Returns
        -------
        Movie or None
            The movie, or None if it does not exist.
        """
        return self.movie_dao.find_by_id(id_movie)

    @log
    def find_by_title(self, title: str) -> Movie | None:
        """Find a movie by a part of its title (case-insensitive).

        Parameters
        ----------
        title : str
            Part of the title.

        Returns
        -------
        Movie or None
            The first movie found, or None.
        """
        search_term = f"%{title}%"
        return self.movie_dao.find_by_title(search_term)

    @log
    def create_movie(self, movie: Movie) -> bool:
        """Create a new movie.

        Parameters
        ----------
        movie : Movie
            The movie to create.

        Returns
        -------
        bool
            True if the movie was created, False otherwise.
        """
        return self.movie_dao.insert_movie(movie)

    @log
    def update_movie(self, movie: Movie) -> bool:
        """Update an existing movie.

        Parameters
        ----------
        movie : Movie
            The movie with its new values (id_movie required).

        Returns
        -------
        bool
            True if the movie was updated, False otherwise.
        """
        if movie.id_movie is None:
            return False

        return self.movie_dao.update_movie(movie)

    @log
    def delete_movie(self, id_movie: int) -> bool:
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
        return self.movie_dao.movie_delete(id_movie)

    @log
    def search_omdb(self, title: str) -> list[dict[str, Any]]:
        """Search movies on OMDb by keyword.

        Parameters
        ----------
        title : str
            Words of the title.

        Returns
        -------
        list of dict
            Light description of each movie found (title, year, imdbID, poster).
        """
        return self.omdb_client.search(title)

    @log
    def import_from_omdb(self, imdb_id: str) -> Movie:
        """Import a movie from OMDb (or return it if it is already in the database).

        Parameters
        ----------
        imdb_id : str
            IMDb identifier of the movie, e.g. "tt1375666".

        Returns
        -------
        Movie
            The movie saved in the database.

        Raises
        ------
        LookupError
            If OMDb does not know the movie.
        RuntimeError
            If the database refuses the movie (e.g. unknown genre or duration).
        """
        existing = self.movie_dao.find_by_external_id(imdb_id)
        if existing:
            return existing

        data = self.omdb_client.get_by_imdb_id(imdb_id)
        if data is None:
            raise LookupError("Movie not found on OMDb")

        poster = data.get("Poster", "")
        movie = Movie(
            title=data["Title"],
            duration=_parse_runtime(data.get("Runtime", "")),
            genre=_first_genre(data.get("Genre", "")),
            external_id=data["imdbID"],
            poster_url="" if poster == "N/A" else poster,
        )
        if not self.movie_dao.insert_movie(movie):
            raise RuntimeError("Insertion failed")
        return movie
