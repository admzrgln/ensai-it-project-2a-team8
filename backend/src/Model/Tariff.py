from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime, time


class Tariff:
    """Tariff of the price grid: a price and the conditions to be entitled to it.

    All the conditions must be met: age, student / ENSAI status, and day and time of the
    screening (compared with the START time of the screening).

    Parameters
    ----------
    code : str
        Unique code of the tariff, e.g. "child".
    label : str
        Name displayed to the customers.
    price : float
        Price of a ticket, in euros.
    min_age : int or None, optional
        Minimum age on the day of the screening (inclusive, None = no minimum).
    max_age : int or None, optional
        Maximum age on the day of the screening (inclusive, None = no maximum).
    requires_ensai : bool, optional
        True if only ENSAI students are entitled to it.
    requires_student : bool, optional
        True if only students are entitled to it (ENSAI students count as students).
    is_active : bool, optional
        False if the tariff has been deactivated.
    weekday : int or None, optional
        Day of the screening (0 = Monday ... 6 = Sunday, None = any day).
    time_from : time or None, optional
        Earliest start time of the screening (inclusive).
    time_until : time or None, optional
        Latest start time of the screening (exclusive).
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
    ) -> None:
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
        """Whether the tariff depends on the day or time of the screening.

        Returns
        -------
        bool
            True if weekday, time_from or time_until is set.
        """
        return self.weekday is not None or self.time_from is not None or self.time_until is not None

    @property
    def has_conditions(self) -> bool:
        """Whether the tariff has at least one condition.

        Returns
        -------
        bool
            True if the tariff has a condition on the age, the status or the schedule.
        """
        return (
            self.min_age is not None
            or self.max_age is not None
            or self.requires_ensai
            or self.requires_student
            or self.has_schedule_condition
        )

    def matches_schedule(self, screening_dt: datetime | None) -> bool:
        """Check the day and time conditions of the tariff for a screening.

        Parameters
        ----------
        screening_dt : datetime or None
            Start of the screening (None if unknown).

        Returns
        -------
        bool
            True if the screening matches the day and time conditions (False if screening_dt is None).
        """
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

    def is_eligible(
        self, age: int, is_ensai_student: bool, is_student: bool, screening_dt: datetime | None = None
    ) -> bool:
        """Check whether a person, for a given screening, is entitled to the tariff.

        Parameters
        ----------
        age : int
            Age of the person on the day of the screening.
        is_ensai_student : bool
            True if the person is an ENSAI student.
        is_student : bool
            True if the person is a student.
        screening_dt : datetime or None, optional
            Start of the screening, needed for the tariffs with a schedule condition.

        Returns
        -------
        bool
            True if all the conditions of the tariff are met.
        """
        if self.min_age is not None and age < self.min_age:
            return False
        if self.max_age is not None and age > self.max_age:
            return False
        if self.requires_ensai and not is_ensai_student:
            return False
        if self.requires_student and not (is_student or is_ensai_student):
            return False
        if self.has_schedule_condition and not self.matches_schedule(screening_dt):
            return False
        return True

    def __str__(self) -> str:
        price = "no price" if self.price is None else f"{self.price:.2f}€"
        return f"Tariff {self.code} : {self.label} ({price})"
