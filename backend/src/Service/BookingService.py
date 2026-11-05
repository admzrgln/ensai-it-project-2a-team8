from datetime import datetime

from backend.src.DAO.BookingDAO import BookingDao
from backend.src.DAO.ScreeningDAO import ScreeningDao
from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Booking import Booking
from backend.src.Model.Ticket import Ticket
from backend.src.Service.TariffService import TariffError, TariffService
from utils.log_utils import log

MAX_TICKETS_PER_BOOKING = 10


class BookingError(Exception):
    """Règle métier non respectée (le message est renvoyé tel quel au client)."""


class NotEnoughSeatsError(BookingError):
    """Plus assez de places dans la séance."""


class BookingService:
    """Class containing Booking service methods (Business Logic Layer)"""

    def __init__(self):
        self.booking_dao = BookingDao()
        self.screening_dao = ScreeningDao()
        self.user_dao = UserDao()
        self.tariff_service = TariffService()

    def _build_booking(
        self,
        id_customer: int,
        id_screening: int,
        include_myself: bool,
        customer_is_student: bool,
        guests: list[Ticket],
    ) -> Booking:
        # 1. Le client existe et est bien un customer
        customer = self.user_dao.find_by_id(id_customer)
        if customer is None or customer.role != "customer":
            raise BookingError("Only customers can book a screening")

        # 2. La séance existe et n'a pas encore commencé
        screening = self.screening_dao.find_by_id(id_screening)
        if screening is None:
            raise BookingError("Screening not found")
        if screening.date_time <= datetime.now():
            raise BookingError("This screening has already started")

        # 3. Construire la liste des billets
        tickets: list[Ticket] = []
        if include_myself:
            if customer.date_of_birth is None:
                raise BookingError("Your date of birth is missing from your profile")
            tickets.append(Ticket(
                first_name=customer.first_name,
                last_name=customer.last_name,
                date_of_birth=customer.date_of_birth,  # déjà connue depuis l'inscription
                is_holder=True,
                is_ensai_student=customer.is_ensai_student,
                is_student=customer_is_student,
            ))
        for guest in guests:
            if guest.date_of_birth is None:
                raise BookingError(f"Date of birth is required for {guest.first_name} {guest.last_name}")
            if guest.date_of_birth > screening.date_time.date():
                raise BookingError(f"Invalid date of birth for {guest.first_name} {guest.last_name}")
            guest.is_holder = False
            tickets.append(guest)

        if not tickets:
            raise BookingError("A booking must contain at least one ticket")
        if len(tickets) > MAX_TICKETS_PER_BOOKING:
            raise BookingError(f"A booking is limited to {MAX_TICKETS_PER_BOOKING} tickets")
        if len(tickets) > screening.available_seats:
            raise NotEnoughSeatsError(f"Only {screening.available_seats} seat(s) left for this screening")

        grid = self.tariff_service.find_all(only_active=True)
        try:
            for t in tickets:
                self.tariff_service.price_ticket(t, screening.date_time.date(), grid)
        except TariffError as e:
            raise BookingError(str(e)) from e

        return Booking(id_customer=id_customer, id_screening=id_screening, tickets=tickets)

    @log
    def quote(self, id_customer: int, id_screening: int, include_myself: bool,
              customer_is_student: bool, guests: list[Ticket]) -> Booking:
        """Affiche le détail et le total à régler, SANS réserver."""
        return self._build_booking(id_customer, id_screening, include_myself, customer_is_student, guests)

    @log
    def book(self, id_customer: int, id_screening: int, include_myself: bool,
             customer_is_student: bool, guests: list[Ticket]) -> Booking:
        """Réserve : enregistre la réservation, les billets et décrémente les places disponibles."""
        booking = self._build_booking(id_customer, id_screening, include_myself, customer_is_student, guests)
        if not self.booking_dao.insert_booking(booking):
            # Quelqu'un a pris les dernières places entre la vérification et l'insertion
            raise NotEnoughSeatsError("Not enough seats left for this screening")
        return booking

    @log
    def find_by_id(self, id_booking: int) -> Booking | None:
        return self.booking_dao.find_by_id(id_booking)

    @log
    def find_by_customer(self, id_customer: int) -> list[Booking]:
        return self.booking_dao.find_by_customer(id_customer)

    @log
    def cancel(self, id_booking: int, id_customer: int) -> bool:
        """Annule une réservation du client (avant le début de la séance) et rend les places."""
        booking = self.booking_dao.find_by_id(id_booking)
        if booking is None or booking.id_customer != id_customer:
            raise BookingError("Booking not found")
        if booking.status != "confirmed":
            raise BookingError("This booking is already cancelled")
        screening = self.screening_dao.find_by_id(booking.id_screening)
        if screening is not None and screening.date_time <= datetime.now():
            raise BookingError("Cannot cancel a booking for a screening that has already started")
        return self.booking_dao.cancel_booking(id_booking)
