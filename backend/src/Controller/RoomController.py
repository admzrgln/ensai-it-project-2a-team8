import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Model.Room import Room
from backend.src.Service.RoomService import RoomService

room_router = APIRouter(prefix="/rooms")
room_service = RoomService()


class RoomModel(BaseModel):
    """Define a Pydantic model for Rooms"""
    id_room: int | None = None
    room_type: str
    number: str
    capacity: int


@room_router.get("/", tags=["Rooms"])
async def find_all_rooms():
    """List all rooms"""
    logging.info("List all rooms")
    return room_service.find_all()


# Cette route doit être AVANT /{id_room}, sinon "type" serait interprété comme un id
@room_router.get("/type/{room_type}", tags=["Rooms"])
async def rooms_by_type(room_type: str):
    """Find rooms by type"""
    logging.info(f"Find rooms by type: {room_type}")
    return room_service.find_by_type(room_type)


@room_router.get("/{id_room}", tags=["Rooms"])
async def room_by_id(id_room: int):
    """Find a room by id"""
    logging.info(f"Find a room by id: {id_room}")
    room = room_service.find_by_id(id_room)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@room_router.post("/", tags=["Rooms"], status_code=201)
async def create_room(room_data: RoomModel):
    """Create a new room"""
    logging.info(f"Create a new room: {room_data.room_type} {room_data.number}")
    new_room = Room(
        id_room=None,
        room_type=room_data.room_type,
        number=room_data.number,
        capacity=room_data.capacity,
    )
    if not room_service.create_room(new_room):
        raise HTTPException(status_code=400, detail="Invalid data or creation failed")
    return new_room


@room_router.put("/{id_room}", tags=["Rooms"])
async def update_room(id_room: int, room_data: RoomModel):
    """Update an existing room"""
    logging.info(f"Update room id: {id_room}")
    updated_room = Room(
        id_room=id_room,
        room_type=room_data.room_type,
        number=room_data.number,
        capacity=room_data.capacity,
    )
    if not room_service.update_room(updated_room):
        raise HTTPException(status_code=404, detail="Room not found or update failed")
    return {"message": "Room updated successfully", "room": updated_room}


@room_router.delete("/{id_room}", tags=["Rooms"])
async def delete_room(id_room: int):
    """Delete a room by id"""
    logging.info(f"Delete room id: {id_room}")
    if not room_service.delete_room(id_room):
        raise HTTPException(status_code=404, detail="Room not found")
    return {"message": f"Room {id_room} deleted successfully"}