import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import AdminPayload
from backend.src.Model.Room import Room
from backend.src.Service.RoomService import RoomService

room_router = APIRouter(prefix="/rooms")
room_service = RoomService()


class RoomModel(BaseModel):
    """Body of the request updating a room (the id is read in the URL)."""

    number: str = Field(pattern=r"\S", description="Number of the room, e.g. 3")
    capacity: int = Field(gt=0, description="Number of seats of the room")


@room_router.get("/", tags=["Rooms"], response_model=None)
async def find_all_rooms() -> list[Room]:
    """List all the rooms.

    Returns
    -------
    list of Room
        All the rooms, ordered by number.
    """
    logging.info("List all rooms")
    return room_service.find_all()


@room_router.get("/{id_room}", tags=["Rooms"], response_model=None)
async def room_by_id(id_room: int) -> Room:
    """Find a room by its identifier.

    Parameters
    ----------
    id_room : int
        Identifier of the room.

    Returns
    -------
    Room
        The room (404 error if it does not exist).
    """
    logging.info(f"Find a room by id: {id_room}")
    room = room_service.find_by_id(id_room)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@room_router.put("/{id_room}", tags=["Rooms"], response_model=None)
async def update_room(id_room: int, room_data: RoomModel, admin: AdminPayload) -> Room:
    """Update the number and the capacity of a room (administrators only).

    Parameters
    ----------
    id_room : int
        Identifier of the room.
    room_data : RoomModel
        New number and capacity of the room.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    Room
        The updated room (error 422 if the values are invalid, 404 if the room does not exist).
    """
    logging.info(f"Admin {admin['user_id']} updates room {id_room}")
    room = Room(number=room_data.number, capacity=room_data.capacity, id_room=id_room)
    if not room_service.update_room(room):
        raise HTTPException(status_code=404, detail="Room not found")
    return room
