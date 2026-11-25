import logging

from fastapi import APIRouter, HTTPException

from backend.src.Model.Room import Room
from backend.src.Service.RoomService import RoomService

room_router = APIRouter(prefix="/rooms")
room_service = RoomService()


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
