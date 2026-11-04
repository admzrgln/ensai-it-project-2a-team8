class Tariff:
    """Class representing a Tariff of the price grid."""

    def __init__(
        self,
        code: str,
        label: str,
        price: float | None = None,  # None = prix de base de la séance
        min_age: int | None = None,
        max_age: int | None = None,
        requires_ensai: bool = False,
        requires_student: bool = False,
        is_active: bool = True,
    ):
        self.code = code
        self.label = label
        self.price = price
        self.min_age = min_age
        self.max_age = max_age
        self.requires_ensai = requires_ensai
        self.requires_student = requires_student
        self.is_active = is_active

    def is_eligible(self, age: int, is_ensai_student: bool, is_student: bool) -> bool:
        """La personne remplit-elle toutes les conditions de ce tarif ?"""
        if self.min_age is not None and age < self.min_age:
            return False
        if self.max_age is not None and age > self.max_age:
            return False
        if self.requires_ensai and not is_ensai_student:
            return False
        # un·e élève ENSAI est aussi étudiant·e
        if self.requires_student and not (is_student or is_ensai_student):
            return False
        return True

    def price_for(self, base_price: float) -> float:
        """Prix réel pour une séance : jamais plus cher que le prix de base."""
        return base_price if self.price is None else min(self.price, base_price)

    def __str__(self):
        return f"Tariff {self.code} : {self.label} ({self.price if self.price is not None else 'prix de base'})"
