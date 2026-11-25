import logging
from collections.abc import Callable
from datetime import date
from typing import Any, ParamSpec, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import CustomerPayload
from backend.src.Model.Ticket import Ticket
from backend.src.Service.BookingService import BookingError, BookingService, NotEnoughSeatsError

booking_router = APIRouter(prefix="/bookings")
booking_service = BookingService()

P = ParamSpec("P")
R = TypeVar("R")


class GuestModel(BaseModel):
    """A person the customer books for (other than themselves)."""

    first_name: str
    last_name: str
    date_of_birth: date
    is_ensai_student: bool = False
    is_student: bool = False


class BookingRequestModel(BaseModel):
    """Booking sent by the customer. The customer is read in the token, not in the body."""

    id_screening: int
    include_myself: bool = True  # does the customer take a seat for themselves?
    customer_is_student: bool = False  # student (outside ENSAI)? The ENSAI status comes from the account
    guests: list[GuestModel] = Field(default_factory=list)


def _to_tickets(guests: list[GuestModel]) -> list[Ticket]:
    """Convert the guests of the request into tickets.

    Parameters
    ----------
    guests : list of GuestModel
        The guests sent by the customer.

    Returns
    -------
    list of Ticket
        One ticket (not priced yet) per guest.
    """
    return [Ticket(**g.model_dump()) for g in guests]


def _call(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Call a service method and turn its business errors into HTTP errors.

    Parameters
    ----------
    fn : Callable
        The service method.
    *args : Any
        Its positional arguments.
    **kwargs : Any
        Its keyword arguments.

    Returns
    -------
    Any
        What the method returns (HTTP error 409 if there are not enough seats, 400 otherwise).
    """
    try:
        return fn(*args, **kwargs)
    except NotEnoughSeatsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except BookingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@booking_router.post("/quote", tags=["Bookings"], response_model=None)
async def quote_booking(data: BookingRequestModel, user: CustomerPayload) -> dict[str, Any]:
    """Show the price of each ticket and the total to pay, WITHOUT booking (customers only).

    Parameters
    ----------
    data : BookingRequestModel
        The screening and the people.
    user : dict
        Token of the logged-in customer.

    Returns
    -------
    dict
        The booking that would be made, with its tickets and total.
    """
    logging.info(f"Quote for customer {user['user_id']} on screening {data.id_screening}")
    booking = _call(
        booking_service.quote,
        user["user_id"],
        data.id_screening,
        data.include_myself,
        data.customer_is_student,
        _to_tickets(data.guests),
    )
    return booking.to_dict()


@booking_router.post("/", tags=["Bookings"], status_code=201, response_model=None)
async def create_booking(data: BookingRequestModel, user: CustomerPayload) -> dict[str, Any]:
    """Book a screening (customers only).

    Parameters
    ----------
    data : BookingRequestModel
        The screening and the people.
    user : dict
        Token of the logged-in customer.

    Returns
    -------
    dict
        The booking saved, with its tickets and the total to pay
        (error 409 if there are not enough seats, 400 if a rule is not respected).
    """
    logging.info(f"Booking for customer {user['user_id']} on screening {data.id_screening}")
    booking = _call(
        booking_service.book,
        user["user_id"],
        data.id_screening,
        data.include_myself,
        data.customer_is_student,
        _to_tickets(data.guests),
    )
    return booking.to_dict()


@booking_router.get("/me", tags=["Bookings"], response_model=None)
async def my_bookings(user: CustomerPayload) -> list[dict[str, Any]]:
    """List the bookings of the logged-in customer.

    Parameters
    ----------
    user : dict
        Token of the logged-in customer.

    Returns
    -------
    list of dict
        The bookings, from the most recent.
    """
    return [b.to_dict() for b in booking_service.find_by_customer(user["user_id"])]


@booking_router.get("/{id_booking}", tags=["Bookings"], response_model=None)
async def booking_by_id(id_booking: int, user: CustomerPayload) -> dict[str, Any]:
    """Find one of the bookings of the logged-in customer.

    Parameters
    ----------
    id_booking : int
        Identifier of the booking.
    user : dict
        Token of the logged-in customer.

    Returns
    -------
    dict
        The booking (error 404 if it does not exist or belongs to someone else).
    """
    booking = booking_service.find_by_id(id_booking)
    if booking is None or booking.id_customer != user["user_id"]:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking.to_dict()


@booking_router.delete("/{id_booking}", tags=["Bookings"], response_model=None)
async def cancel_booking(id_booking: int, user: CustomerPayload) -> dict[str, str]:
    """Cancel one of the bookings of the logged-in customer (the seats are given back).

    Parameters
    ----------
    id_booking : int
        Identifier of the booking.
    user : dict
        Token of the logged-in customer.

    Returns
    -------
    dict
        Confirmation message (error 400 if the booking can't be cancelled).
    """
    _call(booking_service.cancel, id_booking, user["user_id"])
    return {"message": f"Booking {id_booking} cancelled"}
