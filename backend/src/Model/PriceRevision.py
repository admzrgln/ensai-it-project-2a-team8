from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class PriceRevision:
    """Yearly increase of every tariff, applied on January 1st of `year`.

    Parameters
    ----------
    year : int
        Year from which the new prices apply.
    rate_percent : float
        Increase in percent (2.0 means +2 %).
    applied_at : datetime or None, optional
        When the revision was applied (None while it is only planned).
    """

    def __init__(self, year: int, rate_percent: float, applied_at: datetime | None = None) -> None:
        self.year = year
        self.rate_percent = rate_percent
        self.applied_at = applied_at

    def __str__(self) -> str:
        state = "appliquée" if self.applied_at else "planifiée"
        return f"Révision {self.year} : +{self.rate_percent:.2f} % ({state})"
