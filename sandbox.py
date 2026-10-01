import os
from backend.src.Model.Movie import Movie
from backend.src.DAO.MovieDAO import MovieDao
from backend.src.Service.MovieService import MovieService

# Si tes variables de connexion sont dans le fichier .env vu sur ta capture,
# décommente les deux lignes suivantes pour les charger automatiquement :
from dotenv import load_dotenv
load_dotenv()


def run_sandbox():
    print("Initialisation du MovieDAO...")
    # Grâce au pattern Singleton, on l'instancie simplement comme ceci
    dao = MovieDao()
    
    print("Récupération des films via find_all()...")
    movies = dao.find_all()
    
    print(f"\nSuccès ! {len(movies)} films ont été trouvés dans la base de données :")
    for movie in movies:
        print(f" - {movie.title} ({movie.duration} min) [{movie.genre}]")

    print("\n--- Test de find_by_id() ---")
    id_test = 1
    movie = dao.find_by_id(id_test)
    
    if movie:
        print("Succès ! Voici le film trouvé :")
        print(movie) 
    else:
        print(f"Échec : Aucun film avec l'id_movie {id_test}.")


def run_insert_movie():
    movie = Movie(
        title="A",
        duration=135,
        genre="Horreur, Crime",
        external_id="1",
        poster_url="https://example2.com/poster.jpg",
        id_movie=None
    )

    is_created = MovieDao().insert_movie(movie)

    print(f"L'insertion a fonctionné : {is_created}")
    print(f"L'ID généré pour ce film est : {movie.id_movie}")


def run_update_movie():
    movie = Movie(
        title="B",
        duration=1,
        genre="Crime",
        external_id="1",
        poster_url="https://example2.com/poster.jpg",
        id_movie=8
    )

    is_created = MovieDao().update_movie(movie)

    print(f"La modification a fonctionné : {is_created}")


def run_delete_movie():
    id_movie = 7

    is_delete = MovieDao().movie_delete(id_movie)

    print(f"La suppression a fonctionné : {is_delete}")


def run_find_title():
    title = "B"

    movie = MovieDao().find_by_title(title)
    print(movie)

# SERVICE


def test_movie_service():
    # On instancie uniquement le Service
    service = MovieService()

    # --- TEST 1 : Recherche (Read) ---
    print("--- Test de find_by_id ---")
    # Mets un ID que tu sais être présent dans ta base (ex: 8)
    movie_found = service.find_by_id(8) 
    
    if movie_found:
        print(f"Succès : Film trouvé -> {movie_found.title}")
    else:
        print("Échec : Film introuvable.")

    # --- TEST 2 : Création (Create) ---
    print("\n--- Test de create_movie ---")
    new_movie = Movie(
        title="Dune: Part Two",
        duration=166,
        genre="Sci-Fi",
        external_id="tt15239678",
        poster_url="https://example.com/dune2.jpg"
    )
    
    is_created = service.create_movie(new_movie)
    print(f"Insertion réussie : {is_created}")
    if is_created:
        print(f"L'ID généré par PostgreSQL et récupéré par le Service est : {new_movie.id_movie}")




if __name__ == "__main__":
    test_movie_service()
