from typing import Optional, List
from src.Model.Movie import Movie # Assurez-vous d'avoir créé le modèle Pydantic Movie !
from .DBConnector import DBConnector


class MovieRepo:
    def __init__(self, db_connector: DBConnector):
        self.db_connector = db_connector

    def get_all_movies(self) -> List[Movie]:
        # Récupère tous les films de la base
        raw_movies = self.db_connector.sql_query("SELECT * FROM movie", return_type="all")
        if not raw_movies:
            return []
        
        # Transforme chaque ligne de résultat (dictionnaire) en un objet Pydantic Movie
        return [Movie(**movie) for movie in raw_movies]

    def get_by_id(self, movie_id: int) -> Optional[Movie]:
        # Récupère un film spécifique
        raw_movie = self.db_connector.sql_query(
            "SELECT * FROM movie WHERE id=%s", 
            (movie_id,), 
            "one"
        )
        if raw_movie is None:
            return None
        return Movie(**raw_movie)