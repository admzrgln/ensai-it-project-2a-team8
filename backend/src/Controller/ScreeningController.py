import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Model.Screening import Screening
from backend.src.Service.ScreeningService import ScreeningService

screening_router = APIRouter(prefix="/screenings")
screening_service = ScreeningService()


class ScreeningModel(BaseModel):
    """Define a Pydantic model for Screenings"""
    id_screening: int | None = None
    id_room: int
    id_movie: int
    id_admin: int  # = id_user d'un utilisateur admin (plus tard : pris dans le JWT)
    date_time: datetime
    base_price: float
    available_seats: int


@screening_router.get("/", tags=["Screenings"])
async def find_all_screenings():
    """List all screenings"""
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
async def create_screening(data: ScreeningModel):
    """Create a new screening"""
    logging.info(f"Create a screening for movie {data.id_movie}")
    new_screening = Screening(
        id_screening=None,
        id_room=data.id_room,
        id_movie=data.id_movie,
        id_admin=data.id_admin,
        date_time=data.date_time,
        base_price=data.base_price,
        available_seats=data.available_seats,
    )
    if not screening_service.create_screening(new_screening):
        raise HTTPException(status_code=400, detail="Invalid data or creation failed")
    return new_screening


@screening_router.put("/{id_screening}", tags=["Screenings"])
async def update_screening(id_screening: int, data: ScreeningModel):
    """Update an existing screening"""
    logging.info(f"Update screening id: {id_screening}")
    updated = Screening(
        id_screening=id_screening,
        id_room=data.id_room,
        id_movie=data.id_movie,
        id_admin=data.id_admin,
        date_time=data.date_time,
        base_price=data.base_price,
        available_seats=data.available_seats,
    )
    if not screening_service.update_screening(updated):
        raise HTTPException(status_code=404, detail="Screening not found or update failed")
    return {"message": "Screening updated successfully", "screening": updated}


@screening_router.delete("/{id_screening}", tags=["Screenings"])
async def delete_screening(id_screening: int):
    """Delete a screening by id"""
    logging.info(f"Delete screening id: {id_screening}")
    if not screening_service.delete_screening(id_screening):
        raise HTTPException(status_code=404, detail="Screening not found")
    return {"message": f"Screening {id_screening} deleted successfully"}
