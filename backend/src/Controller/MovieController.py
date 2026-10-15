import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Service.MovieService import MovieService
from backend.src.Model.Movie import Movie  # Import indispensable pour instancier l'objet métier

movie_router = APIRouter(prefix="/movies")
movie_service = MovieService()


class MovieModel(BaseModel):
    """Define a Pydantic model for Movies"""
    id_movie: int | None = None
    title: str
    duration: int
    genre: str
    external_id: str
    poster_url: str

@movie_router.get("/", tags=["Movies"])
async def find_all_movies():
    """List all movies"""
    logging.info("List all movies")
    movies_list = movie_service.find_all()
    return movies_list

@movie_router.get("/search/{title}", tags=["Movies"])
async def movie_by_title(title: str):
    """Find a movie by title"""
    logging.info(f"Find a movie by title: {title}")
    movie = movie_service.find_by_title(title)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@movie_router.get("/{id_movie}", tags=["Movies"])
async def movie_by_id(id_movie: int):
    """Find a movie by id"""
    logging.info(f"Find a movie by id: {id_movie}")
    movie = movie_service.find_by_id(id_movie)
    
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    return movie

@movie_router.post("/", tags=["Movies"], status_code=201)
async def create_movie(movie_data: MovieModel):
    """Create a new movie"""
    logging.info(f"Create a new movie: {movie_data.title}")
    
    # Conversion du Pydantic Model vers le Modèle Python
    new_movie = Movie(
        id_movie=None,
        title=movie_data.title,
        duration=movie_data.duration,
        genre=movie_data.genre,
        external_id=movie_data.external_id,
        poster_url=movie_data.poster_url
    )
    
    is_created = movie_service.create_movie(new_movie)
    if not is_created:
        raise HTTPException(status_code=400, detail="Invalid data or creation failed")
        
    # On renvoie le film avec son nouvel ID généré
    return new_movie

@movie_router.put("/{id_movie}", tags=["Movies"])
async def update_movie(id_movie: int, movie_data: MovieModel):
    """Update an existing movie"""
    logging.info(f"Update movie id: {id_movie}")
    
    # On force l'ID de l'URL dans l'objet pour la mise à jour
    updated_movie = Movie(
        id_movie=id_movie,
        title=movie_data.title,
        duration=movie_data.duration,
        genre=movie_data.genre,
        external_id=movie_data.external_id,
        poster_url=movie_data.poster_url
    )
    
    is_updated = movie_service.update_movie(updated_movie)
    if not is_updated:
        raise HTTPException(status_code=404, detail="Movie not found or update failed")
        
    return {"message": "Movie updated successfully", "movie": updated_movie}

@movie_router.delete("/{id_movie}", tags=["Movies"])
async def delete_movie(id_movie: int):
    """Delete a movie by id"""
    logging.info(f"Delete movie id: {id_movie}")
    
    is_deleted = movie_service.delete_movie(id_movie)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    return {"message": f"Movie {id_movie} deleted successfully"}