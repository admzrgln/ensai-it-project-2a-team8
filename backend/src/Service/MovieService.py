from backend.src.DAO.MovieDAO import MovieDao  # noqa: N999
from backend.src.Model.Movie import Movie
from utils.log_utils import log


class MovieService:
    """Class containing Movie service methods (Business Logic Layer)"""

    def __init__(self):
        # On instancie le DAO une seule fois pour toute la classe
        self.movie_dao = MovieDao()

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
