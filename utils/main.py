from dotenv import load_dotenv
from backend.src.Model.Movie import Movie
from backend.src.DAO.MovieDAO import MovieDao

load_dotenv() 

def main():
    print("🎬 --- Démarrage du Sandbox Movie --- 🎬")

    # 1. On crée un faux film (sans ID, la base de données va le générer)
    nouveau_film = Movie(
        title="Inception",
        duration=148,
        genre="Sci-Fi",
        external_id="tt1375666",
        poster_url="https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@.jpg"
    )
    
    # 2. On utilise le DAO pour l'insérer
    movie_dao = MovieDao()
    creation_reussie = movie_dao.create(nouveau_film)

    # 3. On vérifie si ça a bien fonctionné
    if creation_reussie:
        print(f"✅ Film sauvegardé avec l'ID : {nouveau_film.id}")
        
        # 4. On relit la base de données pour vérifier qu'on peut récupérer l'info
        film_depuis_db = movie_dao.find_by_id(nouveau_film.id)
        if film_depuis_db:
            print(f"✅ Récupération réussie depuis PostgreSQL : {film_depuis_db.title}")
    else:
        print("❌ Échec de la création.")

# C'est ce bloc qui ordonne à Python d'exécuter la fonction ci-dessus
if __name__ == "__main__":
    main()