class Tariff:
    """Class representing a Tariff of the price grid."""

    def __init__(
        self,
        code: str,
        label: str,
        price: float,
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

    @property
    def has_conditions(self) -> bool:
        return (self.min_age is not None or self.max_age is not None
                or self.requires_ensai or self.requires_student)

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

    def __str__(self):
        price = "no price" if self.price is None else f"{self.price:.2f}€"
        return f"Tariff {self.code} : {self.label} ({price})"
