import os
from backend.src.DAO.MovieDAO import MovieDao

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
        # Python appelle désormais automatiquement la méthode __str__
        print(movie) 
    else:
        print(f"Échec : Aucun film avec l'id_movie {id_test}.")

if __name__ == "__main__":
    run_sandbox()
    