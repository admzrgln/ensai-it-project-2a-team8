from datetime import date

from backend.src.DAO.TariffDAO import TariffDao
from backend.src.Model.Ticket import Ticket
from backend.src.Model.Tariff import Tariff
from utils.log_utils import log

# Plein tarif : sans condition et impossible à désactiver, donc toujours applicable
FULL_TARIFF_CODE = "full"


class TariffError(Exception):
    """Règle métier non respectée sur la grille tarifaire."""


def compute_age(date_of_birth: date, on_date: date) -> int:
    """Âge révolu à une date donnée (on retire 1 si l'anniversaire n'est pas encore passé)."""
    age = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


class TariffService:
    """Price grid management (admins) and ticket pricing (bookings)."""

    def __init__(self):
        self.tariff_dao = TariffDao()

    def price_ticket(self, ticket: Ticket, screening_date: date,
                     tariffs: list[Tariff] | None = None) -> Ticket:
        """Fill ticket.tariff_code and ticket.price with the cheapest tariff the person is entitled to.

        tariffs : grille déjà chargée (évite de relire la base pour chaque billet).
        L'âge est calculé le jour de la séance.
        """
        if tariffs is None:
            tariffs = self.tariff_dao.find_all(only_active=True)
        age = compute_age(ticket.date_of_birth, screening_date)

        eligible = [t for t in tariffs if t.is_eligible(age, ticket.is_ensai_student, ticket.is_student)]
        if not eligible:
            raise TariffError(f"No tariff applies: the '{FULL_TARIFF_CODE}' tariff is missing from the grid")
        best = min(eligible, key=lambda t: t.price)

        ticket.tariff_code = best.code
        ticket.price = round(best.price, 2)
        return ticket

    def _check(self, tariff: Tariff) -> None:
        if not tariff.code or not tariff.label:
            raise TariffError("Code and label are required")
        if tariff.price is None or tariff.price < 0:
            raise TariffError("Price must be positive")
        for age in (tariff.min_age, tariff.max_age):
            if age is not None and age < 0:
                raise TariffError("Ages must be positive")
        if tariff.min_age is not None and tariff.max_age is not None and tariff.min_age > tariff.max_age:
            raise TariffError("min_age must be lower than max_age")
        if tariff.code == FULL_TARIFF_CODE and not tariff.is_active:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff can't be deactivated")
        if tariff.code == FULL_TARIFF_CODE and tariff.has_conditions:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff must apply to everyone (no condition)")

    @log
    def find_all(self, only_active: bool = True) -> list[Tariff]:
        return self.tariff_dao.find_all(only_active)

    @log
    def find_by_code(self, code: str) -> Tariff | None:
        return self.tariff_dao.find_by_code(code)

    @log
    def create_tariff(self, tariff: Tariff) -> Tariff:
        self._check(tariff)
        if self.tariff_dao.find_by_code(tariff.code) is not None:
            raise TariffError(f"Tariff '{tariff.code}' already exists")
        if not self.tariff_dao.insert_tariff(tariff):
            raise TariffError("Creation failed")
        return tariff

    @log
    def update_tariff(self, tariff: Tariff) -> Tariff:
        """Le nouveau prix s'applique aux PROCHAINES réservations ; les billets déjà vendus gardent leur prix."""
        self._check(tariff)
        if self.tariff_dao.find_by_code(tariff.code) is None:
            raise TariffError("Tariff not found")
        if not self.tariff_dao.update_tariff(tariff):
            raise TariffError("Update failed")
        return tariff

    @log
    def deactivate_tariff(self, code: str) -> bool:
        if code == FULL_TARIFF_CODE:
            raise TariffError(f"The '{FULL_TARIFF_CODE}' tariff can't be deactivated")
        if not self.tariff_dao.deactivate_tariff(code):
            raise TariffError("Tariff not found or already inactive")
        return True
