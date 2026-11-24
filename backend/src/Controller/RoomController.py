import logging

from fastapi import APIRouter, HTTPException

from backend.src.Service.RoomService import RoomService

room_router = APIRouter(prefix="/rooms")
room_service = RoomService()


@room_router.get("/", tags=["Rooms"])
async def find_all_rooms():
    """List all rooms"""
    logging.info("List all rooms")
    return room_service.find_all()


@room_router.get("/{id_room}", tags=["Rooms"])
async def room_by_id(id_room: int):
    """Find a room by id"""
    logging.info(f"Find a room by id: {id_room}")
    room = room_service.find_by_id(id_room)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room
