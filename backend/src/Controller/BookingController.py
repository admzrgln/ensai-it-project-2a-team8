import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import require_customer
from backend.src.Model.Ticket import Ticket
from backend.src.Service.BookingService import BookingError, BookingService, NotEnoughSeatsError

booking_router = APIRouter(prefix="/bookings")
booking_service = BookingService()


class GuestModel(BaseModel):
    """Une personne pour qui le client réserve (autre que lui-même)."""
    first_name: str
    last_name: str
    date_of_birth: date
    is_ensai_student: bool = False
    is_student: bool = False


class BookingRequestModel(BaseModel):
    """Panier envoyé par le client. L'id du client est lu dans le JWT, pas dans le body."""
    id_screening: int
    include_myself: bool = True  # le client prend-il une place pour lui ?
    customer_is_student: bool = False  # étudiant (hors ENSAI) ? l'ENSAI est déduite du compte
    guests: list[GuestModel] = Field(default_factory=list)


def _to_tickets(guests: list[GuestModel]) -> list[Ticket]:
    return [Ticket(**g.model_dump()) for g in guests]


def _call(fn, *args):
    """Traduit les erreurs métier en erreurs HTTP."""
    try:
        return fn(*args)
    except NotEnoughSeatsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except BookingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@booking_router.post("/quote", tags=["Bookings"])
async def quote_booking(data: BookingRequestModel, user: dict = Depends(require_customer)):
    """Show the price of each ticket and the total to pay, WITHOUT booking"""
    logging.info(f"Quote for customer {user['user_id']} on screening {data.id_screening}")
    booking = _call(booking_service.quote, user["user_id"], data.id_screening,
                    data.include_myself, data.customer_is_student, _to_tickets(data.guests))
    return booking.to_dict()


@booking_router.post("/", tags=["Bookings"], status_code=201)
async def create_booking(data: BookingRequestModel, user: dict = Depends(require_customer)):
    """Book a screening (customers only). Returns the tickets and the total to pay"""
    logging.info(f"Booking for customer {user['user_id']} on screening {data.id_screening}")
    booking = _call(booking_service.book, user["user_id"], data.id_screening,
                    data.include_myself, data.customer_is_student, _to_tickets(data.guests))
    return booking.to_dict()


@booking_router.get("/me", tags=["Bookings"])
async def my_bookings(user: dict = Depends(require_customer)):
    """List the bookings of the logged-in customer"""
    return [b.to_dict() for b in booking_service.find_by_customer(user["user_id"])]


@booking_router.get("/{id_booking}", tags=["Bookings"])
async def booking_by_id(id_booking: int, user: dict = Depends(require_customer)):
    """Find one of my bookings by id"""
    booking = booking_service.find_by_id(id_booking)
    if booking is None or booking.id_customer != user["user_id"]:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking.to_dict()


@booking_router.delete("/{id_booking}", tags=["Bookings"])
async def cancel_booking(id_booking: int, user: dict = Depends(require_customer)):
    """Cancel one of my bookings (seats are given back to the screening)"""
    _call(booking_service.cancel, id_booking, user["user_id"])
    return {"message": f"Booking {id_booking} cancelled"}
