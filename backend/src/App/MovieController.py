import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Service.MovieService import MovieService

# Le nom doit être movie_router pour correspondre à l'import dans API.py
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

@movie_router.get("/{id_movie}", tags=["Movies"])
async def movie_by_id(id_movie: int):
    """Find a movie by id"""
    logging.info("Find a movie by id")
    movie = movie_service.find_by_id(id_movie)
    
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    return movie
