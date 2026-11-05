import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.src.Controller.JWTBearer import require_admin
from backend.src.Model.Screening import Screening
from backend.src.Service.ScreeningService import ScreeningError, ScreeningNotFoundError, ScreeningService

screening_router = APIRouter(prefix="/screenings")
screening_service = ScreeningService()


class ScreeningModel(BaseModel):
    """Define a Pydantic model for Screenings.

    Pas d'id_screening (généré par la base, ou lu dans l'URL pour une modification),
    pas de prix (les prix viennent de la grille /tariffs), pas de nombre de places
    (calculé à partir de la capacité de la salle et des réservations),
    pas d'id_admin (lu dans le JWT : on ne peut pas planifier au nom d'un autre admin).
    """
    id_room: int
    id_movie: int
    date_time: datetime


@screening_router.get("/", tags=["Screenings"])
async def find_all_screenings():
    """List all screenings (public: customers browse the schedule before booking)"""
    logging.info("List all screenings")
    return screening_service.find_all()


# Cette route doit être AVANT /{id_screening}, sinon "movie" serait lu comme un id
@screening_router.get("/movie/{id_movie}", tags=["Screenings"])
async def screenings_by_movie(id_movie: int):
    """List the screenings of a movie"""
    logging.info(f"Find screenings of movie: {id_movie}")
    return screening_service.find_by_movie(id_movie)


@screening_router.get("/{id_screening}", tags=["Screenings"])
async def screening_by_id(id_screening: int):
    """Find a screening by id"""
    logging.info(f"Find a screening by id: {id_screening}")
    screening = screening_service.find_by_id(id_screening)
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
    return screening


@screening_router.post("/", tags=["Screenings"], status_code=201)
async def create_screening(data: ScreeningModel, admin: dict = Depends(require_admin)):
    """Create a new screening (admin only)"""
    logging.info(f"Admin {admin['user_id']} creates a screening for movie {data.id_movie}")
    new_screening = Screening(
        id_screening=None,
        id_room=data.id_room,
        id_movie=data.id_movie,
        id_admin=admin["user_id"],
        date_time=data.date_time,
    )
    try:
        screening_service.create_screening(new_screening)
    except ScreeningError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return new_screening


@screening_router.put("/{id_screening}", tags=["Screenings"])
async def update_screening(id_screening: int, data: ScreeningModel, admin: dict = Depends(require_admin)):
    """Update an existing screening (admin only). The admin who modifies it becomes its planner"""
    logging.info(f"Admin {admin['user_id']} updates screening id: {id_screening}")
    updated = Screening(
        id_screening=id_screening,
        id_room=data.id_room,
        id_movie=data.id_movie,
        id_admin=admin["user_id"],
        date_time=data.date_time,
    )
    try:
        screening_service.update_screening(updated)
    except ScreeningNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ScreeningError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"message": "Screening updated successfully", "screening": updated}


@screening_router.delete("/{id_screening}", tags=["Screenings"])
async def delete_screening(id_screening: int, admin: dict = Depends(require_admin)):
    """Delete a screening by id (admin only)"""
    logging.info(f"Admin {admin['user_id']} deletes screening id: {id_screening}")
    if not screening_service.delete_screening(id_screening):
        raise HTTPException(status_code=404, detail="Screening not found")
    return {"message": f"Screening {id_screening} deleted successfully"}