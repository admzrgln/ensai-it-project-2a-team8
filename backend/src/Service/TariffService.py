from datetime import date

from backend.src.Model.Ticket import Ticket

# ---------------------------------------------------------------------------
# GRILLE TARIFAIRE  -->  C'EST ICI QU'IL FAUDRA METTRE LES VRAIS TARIFS
# ---------------------------------------------------------------------------
# Chaque tarif a :
#   - un libellé
#   - un prix fixe en euros, ou None = prix de base de la séance (plein tarif)
#   - une condition d'éligibilité (fonction qui reçoit l'âge et le billet)
#
# Pour chaque personne, on prend le tarif LE MOINS CHER auquel elle a droit,
# et jamais plus cher que le prix de base de la séance.
# Les prix ci-dessous sont PROVISOIRES.
TARIFFS = {
    "child": {
        "label": "Moins de 14 ans",
        "price": 4.50,
        "eligible": lambda age, ticket: age < 14,
    },
    "ensai": {
        "label": "Élève ENSAI",
        "price": 4.00,
        "eligible": lambda age, ticket: ticket.is_ensai_student,
    },
    "student": {
        "label": "Étudiant·e",
        "price": 6.00,
        "eligible": lambda age, ticket: ticket.is_student or ticket.is_ensai_student,
    },
    "full": {
        "label": "Plein tarif",
        "price": None,  # None = base_price de la séance
        "eligible": lambda age, ticket: True,
    },
}


def compute_age(date_of_birth: date, on_date: date) -> int:
    """Âge révolu à une date donnée (on retire 1 si l'anniversaire n'est pas encore passé)."""
    age = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


class TariffService:
    """Choose the tariff and the price of each ticket."""

    def __init__(self, tariffs: dict | None = None):
        self.tariffs = tariffs if tariffs is not None else TARIFFS

    def price_ticket(self, ticket: Ticket, base_price: float, screening_date: date) -> Ticket:
        """Fill ticket.tariff_code and ticket.price. The age is computed on the day of the screening."""
        age = compute_age(ticket.date_of_birth, screening_date)

        best_code, best_price = None, None
        for code, tariff in self.tariffs.items():
            if not tariff["eligible"](age, ticket):
                continue
            price = base_price if tariff["price"] is None else min(tariff["price"], base_price)
            if best_price is None or price < best_price:
                best_code, best_price = code, price

        ticket.tariff_code = best_code
        ticket.price = round(best_price, 2)
        return ticket

    def list_tariffs(self, base_price: float) -> list[dict]:
        """Grille affichable au client pour une séance donnée."""
        return [
            {"code": code, "label": t["label"], "price": base_price if t["price"] is None else min(t["price"], base_price)}
            for code, t in self.tariffs.items()
        ]
