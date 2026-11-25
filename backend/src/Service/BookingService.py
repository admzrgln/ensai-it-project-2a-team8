from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from backend.src.DAO.BookingDAO import BookingDao
from backend.src.DAO.ScreeningDAO import ScreeningDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Booking import Booking
from backend.src.Model.Customer import Customer
from backend.src.Model.Ticket import Ticket
from backend.src.Service.PriceRevisionService import PriceRevisionService
from backend.src.Service.TariffService import TariffError, TariffService
from utils.log_utils import log

if TYPE_CHECKING:
    from backend.src.Model.Screening import Screening

MAX_TICKETS_PER_BOOKING = 10


class BookingError(Exception):
    """A booking rule is not respected (the message is sent to the client as is)."""


class NotEnoughSeatsError(BookingError):
    """Not enough seats left in the screening."""


class BookingService:
    """Business rules of the bookings (F2): only customers book, one ticket per person."""

    def __init__(self) -> None:
        self.booking_dao: BookingDao = BookingDao()
        self.screening_dao: ScreeningDao = ScreeningDao()
        self.user_dao: UserDao = UserDao()
        self.tariff_service = TariffService()
        self.price_revision_service = PriceRevisionService()

    # ------------------------------------------------------------------
    # Steps of the construction of a booking
    # ------------------------------------------------------------------
    def _get_customer(self, id_customer: int) -> Customer:
        """Find the customer who books.

        Parameters
        ----------
        id_customer : int
            Identifier of the user who books.

        Returns
        -------
        Customer
            The customer.

        Raises
        ------
        BookingError
            If the user does not exist or is not a customer.
        """
        customer = self.user_dao.find_by_id(id_customer)
        if customer is None or customer.role != "customer" or not isinstance(customer, Customer):
            raise BookingError("Only customers can book a screening")
        return customer

    def _get_future_screening(self, id_screening: int) -> Screening:
        """Find the screening, which must not have started yet.

        Parameters
        ----------
        id_screening : int
            Identifier of the screening.

        Returns
        -------
        Screening
            The screening.

        Raises
        ------
        BookingError
            If the screening does not exist or has already started.
        """
        screening = self.screening_dao.find_by_id(id_screening)
        if screening is None:
            raise BookingError("Screening not found")
        if screening.date_time <= datetime.now():
            raise BookingError("This screening has already started")
        return screening

    @staticmethod
    def _make_tickets(
        customer: Customer,
        screening: Screening,
        include_myself: bool,
        customer_is_student: bool,
        guests: list[Ticket],
    ) -> list[Ticket]:
        """Build the list of tickets: the customer (if they come) then the guests.

        Parameters
        ----------
        customer : Customer
            The customer who books.
        screening : Screening
            The screening booked.
        include_myself : bool
            True if the customer takes a seat for themselves.
        customer_is_student : bool
            True if the customer declares being a student (the ENSAI status comes from the account).
        guests : list of Ticket
            The other people (date of birth required).

        Returns
        -------
        list of Ticket
            The tickets, not priced yet.

        Raises
        ------
        BookingError
            If a date of birth is missing or after the screening.
        """
        tickets: list[Ticket] = []
        if include_myself:
            if customer.date_of_birth is None:
                raise BookingError("Your date of birth is missing from your profile")
            tickets.append(
                Ticket(
                    first_name=customer.first_name,
                    last_name=customer.last_name,
                    date_of_birth=customer.date_of_birth,  # already known from the registration
                    is_holder=True,
                    is_ensai_student=customer.is_ensai_student,
                    is_student=customer_is_student,
                )
            )
        for guest in guests:
            if guest.date_of_birth is None:
                raise BookingError(f"Date of birth is required for {guest.first_name} {guest.last_name}")
            if guest.date_of_birth > screening.date_time.date():
                raise BookingError(f"Invalid date of birth for {guest.first_name} {guest.last_name}")
            guest.is_holder = False
            tickets.append(guest)
        return tickets

    @staticmethod
    def _check_ticket_count(tickets: list[Ticket], screening: Screening) -> None:
        """Check the number of tickets of the booking.

        Parameters
        ----------
        tickets : list of Ticket
            The tickets of the booking.
        screening : Screening
            The screening booked.

        Raises
        ------
        BookingError
            If there is no ticket or more than MAX_TICKETS_PER_BOOKING.
        NotEnoughSeatsError
            If there are not enough seats left.
        """
        if not tickets:
            raise BookingError("A booking must contain at least one ticket")
        if len(tickets) > MAX_TICKETS_PER_BOOKING:
            raise BookingError(f"A booking is limited to {MAX_TICKETS_PER_BOOKING} tickets")
        available = screening.available_seats or 0
        if len(tickets) > available:
            raise NotEnoughSeatsError(f"Only {available} seat(s) left for this screening")

    def _price_tickets(self, tickets: list[Ticket], screening: Screening) -> None:
        """Give each ticket the cheapest tariff of the current grid.

        Parameters
        ----------
        tickets : list of Ticket
            The tickets to price.
        screening : Screening
            The screening booked (its date gives the age, its time the schedule tariffs).

        Raises
        ------
        BookingError
            If no tariff applies.
        """
        self.price_revision_service.apply_due_revisions()
        grid = self.tariff_service.find_all(only_active=True)  # read once for all the tickets
        try:
            for t in tickets:
                self.tariff_service.price_ticket(t, screening.date_time, grid)
        except TariffError as e:
            raise BookingError(str(e)) from e

    def _build_booking(
        self,
        id_customer: int,
        id_screening: int,
        include_myself: bool,
        customer_is_student: bool,
        guests: list[Ticket],
    ) -> Booking:
        """Build and price a booking, without saving anything.

        Parameters
        ----------
        id_customer : int
            Identifier of the customer who books.
        id_screening : int
            Identifier of the screening.
        include_myself : bool
            True if the customer takes a seat for themselves.
        customer_is_student : bool
            True if the customer declares being a student.
        guests : list of Ticket
            The other people.

        Returns
        -------
        Booking
            The booking with its priced tickets.

        Raises
        ------
        BookingError
            If a booking rule is not respected.
        NotEnoughSeatsError
            If there are not enough seats left.
        """
        customer = self._get_customer(id_customer)
        screening = self._get_future_screening(id_screening)
        tickets = self._make_tickets(customer, screening, include_myself, customer_is_student, guests)
        self._check_ticket_count(tickets, screening)
        self._price_tickets(tickets, screening)
        return Booking(id_customer=id_customer, id_screening=id_screening, tickets=tickets)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    @log
    def quote(
        self, id_customer: int, id_screening: int, include_myself: bool, customer_is_student: bool, guests: list[Ticket]
    ) -> Booking:
        """Show the price of each ticket and the total to pay, WITHOUT booking.

        Parameters
        ----------
        id_customer : int
            Identifier of the customer.
        id_screening : int
            Identifier of the screening.
        include_myself : bool
            True if the customer takes a seat for themselves.
        customer_is_student : bool
            True if the customer declares being a student.
        guests : list of Ticket
            The other people.

        Returns
        -------
        Booking
            The booking that would be made (not saved).

        Raises
        ------
        BookingError
            If a booking rule is not respected.
        """
        return self._build_booking(id_customer, id_screening, include_myself, customer_is_student, guests)

    @log
    def book(
        self, id_customer: int, id_screening: int, include_myself: bool, customer_is_student: bool, guests: list[Ticket]
    ) -> Booking:
        """Book: save the booking and its tickets, and decrease the available seats.

        Parameters
        ----------
        id_customer : int
            Identifier of the customer.
        id_screening : int
            Identifier of the screening.
        include_myself : bool
            True if the customer takes a seat for themselves.
        customer_is_student : bool
            True if the customer declares being a student.
        guests : list of Ticket
            The other people.

        Returns
        -------
        Booking
            The booking saved, with its identifiers.

        Raises
        ------
        BookingError
            If a booking rule is not respected.
        NotEnoughSeatsError
            If there are not enough seats left (possibly taken by someone else at the same time).
        """
        booking = self._build_booking(id_customer, id_screening, include_myself, customer_is_student, guests)
        if not self.booking_dao.insert_booking(booking):
            # Someone took the last seats between the check and the insertion
            raise NotEnoughSeatsError("Not enough seats left for this screening")
        return booking

    @log
    def find_by_id(self, id_booking: int) -> Booking | None:
        """Find a booking by its identifier.

        Parameters
        ----------
        id_booking : int
            Identifier of the booking.

        Returns
        -------
        Booking or None
            The booking with its tickets, or None if it does not exist.
        """
        return self.booking_dao.find_by_id(id_booking)

    @log
    def find_by_customer(self, id_customer: int) -> list[Booking]:
        """List the bookings of a customer.

        Parameters
        ----------
        id_customer : int
            Identifier of the customer.

        Returns
        -------
        list of Booking
            The bookings, from the most recent.
        """
        return self.booking_dao.find_by_customer(id_customer)

    @log
    def cancel(self, id_booking: int, id_customer: int) -> bool:
        """Cancel a booking of the customer (before the screening) and give the seats back.

        Parameters
        ----------
        id_booking : int
            Identifier of the booking.
        id_customer : int
            Identifier of the customer asking for the cancellation.

        Returns
        -------
        bool
            True if the booking was cancelled.

        Raises
        ------
        BookingError
            If the booking does not belong to the customer, is already cancelled,
            or its screening has already started.
        """
        booking = self.booking_dao.find_by_id(id_booking)
        if booking is None or booking.id_customer != id_customer:
            raise BookingError("Booking not found")
        if booking.status != "confirmed":
            raise BookingError("This booking is already cancelled")
        screening = self.screening_dao.find_by_id(booking.id_screening)
        if screening is not None and screening.date_time <= datetime.now():
            raise BookingError("Cannot cancel a booking for a screening that has already started")
        return self.booking_dao.cancel_booking(id_booking)
