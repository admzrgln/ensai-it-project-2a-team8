import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.src.Controller.JWTBearer import require_admin
from backend.src.Model.Movie import Movie
from backend.src.Service.MovieService import MovieService
from backend.src.Service.OmdbClient import OmdbError

movie_router = APIRouter(prefix="/movies")
movie_service = MovieService()


class MovieModel(BaseModel):
    """Body of the requests creating or updating a movie."""

    id_movie: int | None = None
    title: str
    duration: int
    genre: str
    external_id: str
    poster_url: str


@movie_router.get("/", tags=["Movies"], response_model=None)
async def find_all_movies() -> list[Movie]:
    """List all the movies.

    Returns
    -------
    list of Movie
        All the movies, ordered by title.
    """
    logging.info("List all movies")
    movies_list = movie_service.find_all()
    return movies_list


@movie_router.get("/search/{title}", tags=["Movies"], response_model=None)
async def movie_by_title(title: str) -> Movie:
    """Find a movie by a part of its title.

    Parameters
    ----------
    title : str
        Part of the title (case-insensitive).

    Returns
    -------
    Movie
        The first movie found (error 404 if there is none).
    """
    logging.info(f"Find a movie by title: {title}")
    movie = movie_service.find_by_title(title)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@movie_router.get("/{id_movie}", tags=["Movies"], response_model=None)
async def movie_by_id(id_movie: int) -> Movie:
    """Find a movie by its identifier.

    Parameters
    ----------
    id_movie : int
        Identifier of the movie.

    Returns
    -------
    Movie
        The movie (error 404 if it does not exist).
    """
    logging.info(f"Find a movie by id: {id_movie}")
    movie = movie_service.find_by_id(id_movie)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return movie


@movie_router.post("/", tags=["Movies"], status_code=201, dependencies=[Depends(require_admin)], response_model=None)
async def create_movie(movie_data: MovieModel) -> Movie:
    """Create a new movie (administrators only).

    Parameters
    ----------
    movie_data : MovieModel
        The movie to create.

    Returns
    -------
    Movie
        The movie created, with its identifier (error 400 if the creation failed).
    """
    logging.info(f"Create a new movie: {movie_data.title}")

    # Convert the Pydantic model into a Movie
    new_movie = Movie(
        id_movie=None,
        title=movie_data.title,
        duration=movie_data.duration,
        genre=movie_data.genre,
        external_id=movie_data.external_id,
        poster_url=movie_data.poster_url,
    )

    is_created = movie_service.create_movie(new_movie)
    if not is_created:
        raise HTTPException(status_code=400, detail="Invalid data or creation failed")

    # Return the movie with the id given by the database
    return new_movie


@movie_router.put("/{id_movie}", tags=["Movies"], dependencies=[Depends(require_admin)], response_model=None)
async def update_movie(id_movie: int, movie_data: MovieModel) -> dict[str, Any]:
    """Update a movie (administrators only).

    Parameters
    ----------
    id_movie : int
        Identifier of the movie.
    movie_data : MovieModel
        New values of the movie.

    Returns
    -------
    dict
        Confirmation message and the movie (error 404 if the update failed).
    """
    logging.info(f"Update movie id: {id_movie}")

    # The id of the URL wins over the body
    updated_movie = Movie(
        id_movie=id_movie,
        title=movie_data.title,
        duration=movie_data.duration,
        genre=movie_data.genre,
        external_id=movie_data.external_id,
        poster_url=movie_data.poster_url,
    )

    is_updated = movie_service.update_movie(updated_movie)
    if not is_updated:
        raise HTTPException(status_code=404, detail="Movie not found or update failed")

    return {"message": "Movie updated successfully", "movie": updated_movie}


@movie_router.delete("/{id_movie}", tags=["Movies"], dependencies=[Depends(require_admin)], response_model=None)
async def delete_movie(id_movie: int) -> dict[str, str]:
    """Delete a movie (administrators only).

    Parameters
    ----------
    id_movie : int
        Identifier of the movie.

    Returns
    -------
    dict
        Confirmation message (error 404 if the movie does not exist).
    """
    logging.info(f"Delete movie id: {id_movie}")

    is_deleted = movie_service.delete_movie(id_movie)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {"message": f"Movie {id_movie} deleted successfully"}


@movie_router.get("/omdb/search/{title}", tags=["Movies"], dependencies=[Depends(require_admin)], response_model=None)
async def search_omdb(title: str) -> list[dict[str, Any]]:
    """Search movies on OMDb, without saving anything (administrators only).

    Parameters
    ----------
    title : str
        Words of the title.

    Returns
    -------
    list of dict
        The movies found (error 502 if OMDb does not answer).
    """
    try:
        return movie_service.search_omdb(title)
    except OmdbError as error:
        raise HTTPException(status_code=502, detail="OMDb service error") from error


@movie_router.post(
    "/omdb/import/{imdb_id}",
    tags=["Movies"],
    status_code=201,
    dependencies=[Depends(require_admin)],
    response_model=None,
)
async def import_from_omdb(imdb_id: str) -> Movie:
    """Import a movie from OMDb into the database (administrators only).

    Parameters
    ----------
    imdb_id : str
        IMDb identifier of the movie, e.g. "tt1375666".

    Returns
    -------
    Movie
        The movie saved (errors 404 unknown on OMDb, 502 OMDb unreachable, 400 refused by the database).
    """
    try:
        return movie_service.import_from_omdb(imdb_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Movie not found on OMDb") from error
    except OmdbError as error:
        raise HTTPException(status_code=502, detail="OMDb service error") from error
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail="Import failed") from error
