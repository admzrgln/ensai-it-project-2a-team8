from datetime import datetime, time


class Tariff:
    """Class representing a Tariff of the price grid.

    Conditions possibles (toutes doivent être remplies) : âge, statut étudiant / ENSAI,
    et jour/horaire de la séance (weekday : 0 = lundi ... 6 = dimanche ; time_from inclus,
    time_until exclu, comparés à l'heure de DÉBUT de la séance).
    """

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
        weekday: int | None = None,
        time_from: time | None = None,
        time_until: time | None = None,
    ):
        self.code = code
        self.label = label
        self.price = price
        self.min_age = min_age
        self.max_age = max_age
        self.requires_ensai = requires_ensai
        self.requires_student = requires_student
        self.is_active = is_active
        self.weekday = weekday
        self.time_from = time_from
        self.time_until = time_until

    @property
    def has_schedule_condition(self) -> bool:
        return self.weekday is not None or self.time_from is not None or self.time_until is not None

    @property
    def has_conditions(self) -> bool:
        return (self.min_age is not None or self.max_age is not None
                or self.requires_ensai or self.requires_student
                or self.has_schedule_condition)

    def matches_schedule(self, screening_dt: datetime | None) -> bool:
        if screening_dt is None:
            return False
        if self.weekday is not None and screening_dt.weekday() != self.weekday:
            return False
        start = screening_dt.time()
        if self.time_from is not None and start < self.time_from:
            return False
        if self.time_until is not None and start >= self.time_until:
            return False
        return True

    def is_eligible(self, age: int, is_ensai_student: bool, is_student: bool,
                    screening_dt: datetime | None = None) -> bool:
        """La personne et la séance remplissent-elles toutes les conditions de ce tarif ?"""
        if self.min_age is not None and age < self.min_age:
            return False
        if self.max_age is not None and age > self.max_age:
            return False
        if self.requires_ensai and not is_ensai_student:
            return False
        if self.requires_student and not (is_student or is_ensai_student):
            return False
        if self.has_schedule_condition and not self._matches_schedule(screening_dt):
            return False
        return True

    def __str__(self):
        price = "no price" if self.price is None else f"{self.price:.2f}€"
        return f"Tariff {self.code} : {self.label} ({price})"