
from dotenv import load_dotenv

from backend.src.DAO.MovieDAO import MovieDao
from backend.src.Model.Movie import Movie


load_dotenv()


def main():
    print("Sandbox Movie")

    nouveau_film = Movie(
        title="Inception",
        duration=148,
        genre="Sci-Fi, Action, Thriller",
        external_id="tt1375666",
        poster_url="https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg",
    )
    print(f"Objet instancié en mémoire : {nouveau_film.title}")

    movie_dao = MovieDao()
    creation_reussie = movie_dao.create(nouveau_film)

    if creation_reussie:
        movie_id = nouveau_film.id
        print(f"Film sauvegardé dans la base avec l'ID : {movie_id}")
    else:
        print("Échec de la création en base de données.")
        return

    film_depuis_db = movie_dao.find_by_id(movie_id)

    if film_depuis_db:
        print(
            f"3Récupération depuis PostgreSQL : {film_depuis_db.title} dure {film_depuis_db.duration} minutes."
        )
    else:
        print("Erreur : Impossible de retrouver le film.")


if __name__ == "__main__":
    main()
