from backend.src.DAO.MovieDAO import MovieDao  # noqa: N999
from backend.src.Model.Movie import Movie
from backend.src.Service.OmdbClient import OmdbClient
from utils.log_utils import log


def _parse_runtime(runtime: str) -> int:
    """'136 min' -> 136 ; 'N/A' -> 0"""
    try:
        return int(runtime.split()[0])
    except (ValueError, IndexError, AttributeError):
        return 0


def _first_genre(genres: str) -> str | None:
    """'Action, Sci-Fi' -> 'Action' ; 'N/A' ou vide -> None"""
    first = genres.split(",")[0].strip() if genres else ""
    return None if first in ("", "N/A") else first


class MovieService:
    """Class containing Movie service methods (Business Logic Layer)"""

    def __init__(self):
        # On instancie le DAO une seule fois pour toute la classe
        # On connecte avec Omdb
        self.movie_dao = MovieDao()
        self.omdb_client = OmdbClient()

    @log
    def find_all(self) -> list[Movie]:
        """List all movies available in the database"""
        return self.movie_dao.find_all()

    @log
    def find_by_id(self, id_movie: int) -> Movie:
        """Find a specific movie by its id"""
        return self.movie_dao.find_by_id(id_movie)

    @log
    def find_by_title(self, title: str) -> Movie:
        """Find a movie by its title (partial match supported)"""
        # Pour que le ILIKE du DAO fonctionne comme une vraie recherche, 
        # on ajoute les jokers % autour du titre saisi par l'utilisateur.
        search_term = f"%{title}%"
        return self.movie_dao.find_by_title(search_term)

    @log
    def create_movie(self, movie: Movie) -> bool:
        """Validate and create a new movie"""
        # C'est ici que l'on ajoutera plus tard les vérifications 
        # (ex: if movie.duration < 0: return False)
        return self.movie_dao.insert_movie(movie)

    @log
    def update_movie(self, movie: Movie) -> bool:
        """Validate and update an existing movie"""
        # Clause de garde métier : s'assurer que l'ID est bien présent avant d'appeler le DAO
        if movie.id_movie is None:
            return False
    
        return self.movie_dao.update_movie(movie)

    @log
    def delete_movie(self, id_movie: int) -> bool:
        """Validate and delete a movie by its id"""
        # C'est ici que l'on ajoutera plus tard la vérification des droits Administrateur
        return self.movie_dao.movie_delete(id_movie) 

    @log
    def search_omdb(self, title: str) -> list[dict]:
        return self.omdb_client.search(title)

    @log
    def import_from_omdb(self, imdb_id: str) -> Movie:
        """Importe un film depuis OMDb (ou renvoie celui déjà en base)."""
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
